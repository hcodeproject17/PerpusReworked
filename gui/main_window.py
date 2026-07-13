"""
gui/main_window.py — Dashboard utama PerpusReworked
Layout: sidebar navigasi persisten (kiri) + QStackedWidget konten (kanan),
menggantikan tab horizontal lama agar semua menu selalu terlihat sekaligus
dan area kerja tabel data mendapat lebar maksimum.
"""

import logging
from datetime import datetime
from typing import Optional

import cv2
import numpy as np

from PySide6.QtCore import Signal as pyqtSignal
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QImage, QPixmap, QFont, QTextCursor, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QSplitter,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QHeaderView,
    QSizePolicy,
    QMessageBox,
    QListWidget,
    QListWidgetItem,
    QStackedWidget,
    QButtonGroup,
    QFrame,
)

from core.camera_manager import CameraManager, ScannerThread
from database.sqlite_db import (
    init_db,
    record_visit,
    get_today_visitors,
    get_visit_count_today,
)
from gui.book_tab import BookTab
from gui.book_barcode_tab import BookBarcodeTab
from database.excel_reader import (
    load_members,
    find_by_barcode,
    search,
    backup_excel,
    read_source_excel,
)
from gui.card_tab import CardTab
from gui.member_tab import MemberTab
from gui.analytics_tab import AnalyticsTab
from gui.loan_tab import LoanTab
from gui.settings_dialog import SettingsDialog
from theme import log_colors as _log_colors
from config import (
    APP_NAME,
    APP_VERSION,
    WINDOW_MIN_WIDTH,
    WINDOW_MIN_HEIGHT,
)

logger = logging.getLogger(__name__)



class MainWindow(QMainWindow):
    """Dashboard utama aplikasi perpustakaan."""

    # Signal untuk menjembatani ScannerThread → main thread (thread-safe GUI update)
    _barcode_detected = pyqtSignal(str)

    def __init__(
        self,
        camera_index: Optional[int] = None,
        camera_url:   Optional[str] = None,
    ) -> None:
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.setMinimumSize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)

        self._cam_manager    = CameraManager()
        self._scanner_thread: ScannerThread | None = None
        self._camera_index   = camera_index
        self._camera_url     = camera_url

        # QTimer hanya untuk display — ambil frame dari buffer thread kamera
        self._display_timer = QTimer(self)
        self._display_timer.timeout.connect(self._refresh_display)
        self._latest_frame = None
        self._frame_lock   = __import__("threading").Lock()
        # Signal barcode: ScannerThread emit → main thread handle
        self._barcode_detected.connect(self._handle_barcode)

        self._build_ui()
        self._refresh_table()
        self._connect_camera()

    # ══════════════════════════════════════════════════════════════════════════
    # Build UI
    # ══════════════════════════════════════════════════════════════════════════

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Header ────────────────────────────────────────────────────────────
        root.addWidget(self._make_header())

        # ── Baris kerja: sidebar navigasi + area konten ─────────────────────────
        work_row = QHBoxLayout()
        work_row.setContentsMargins(0, 0, 0, 0)
        work_row.setSpacing(0)

        work_row.addWidget(self._make_sidebar())

        self._stack = QStackedWidget()
        self._stack.setObjectName("mainStack")

        # Halaman 1: Pengunjung
        self._tab_visitor = QWidget()
        self._build_visitor_tab(self._tab_visitor)
        self._stack.addWidget(self._tab_visitor)

        # Halaman 2: Kartu Massal
        self._tab_card = CardTab()
        self._stack.addWidget(self._tab_card)

        # Halaman 3: Daftar Anggota
        self._member_tab = MemberTab()
        self._stack.addWidget(self._member_tab)

        # Halaman 4: Barcode Buku
        self._book_barcode_tab = BookBarcodeTab()
        self._stack.addWidget(self._book_barcode_tab)

        # Halaman 5: Analisis
        self._tab_analytics = AnalyticsTab()
        self._stack.addWidget(self._tab_analytics)

        # Halaman 6: Buku
        self._book_tab = BookTab()
        self._stack.addWidget(self._book_tab)

        # Halaman 7: Peminjaman
        self._loan_tab = LoanTab()
        self._stack.addWidget(self._loan_tab)

        work_row.addWidget(self._stack, stretch=1)

        root.addLayout(work_row, stretch=1)

        # ── Status bar ────────────────────────────────────────────────────────
        self._lbl_status = QLabel("Siap")
        self._lbl_status.setObjectName("statusBarLabel")
        self.statusBar().addWidget(self._lbl_status)
        self.statusBar().setObjectName("appStatusBar")

        self._lbl_kunjungan = QLabel("Kunjungan hari ini: 0")
        self._lbl_kunjungan.setObjectName("statusBarLabel")
        self.statusBar().addPermanentWidget(self._lbl_kunjungan)

    # ── Sidebar navigasi ─────────────────────────────────────────────────────

    # (ikon, label, shortcut Ctrl+N) — urutan sama dengan urutan halaman di atas
    _NAV_ITEMS = [
        ("📷", "Kunjungan",     "1"),
        ("📇", "Cetak Kartu",   "2"),
        ("👥", "Anggota",       "3"),
        ("🏷",  "Barcode Buku", "4"),
        ("📊", "Analisis",      "5"),
        ("📘", "Buku",          "6"),
        ("📖", "Peminjaman",    "7"),
    ]

    def _make_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setObjectName("navSidebar")
        sidebar.setFixedWidth(196)
        v = QVBoxLayout(sidebar)
        v.setContentsMargins(12, 16, 12, 12)
        v.setSpacing(4)

        brand = QLabel(f"📚  {APP_NAME}")
        brand.setObjectName("navBrand")
        brand.setWordWrap(True)
        v.addWidget(brand)

        sub = QLabel(f"v{APP_VERSION}")
        sub.setObjectName("navBrandSub")
        v.addWidget(sub)

        v.addSpacing(6)
        divider = QFrame()
        divider.setObjectName("navDivider")
        divider.setFixedHeight(1)
        v.addWidget(divider)
        v.addSpacing(6)

        self._nav_group = QButtonGroup(self)
        self._nav_group.setExclusive(True)
        self._nav_buttons: list[QPushButton] = []

        for index, (icon, label, key) in enumerate(self._NAV_ITEMS):
            btn = self._make_nav_button(icon, label, key, index)
            v.addWidget(btn)
            self._nav_group.addButton(btn, index)
            self._nav_buttons.append(btn)

            # Ctrl+1..6 — navigasi cepat via keyboard tanpa menyentuh mouse
            shortcut = QShortcut(QKeySequence(f"Ctrl+{key}"), self)
            shortcut.activated.connect(lambda i=index: self._go_to_page(i))

        self._nav_buttons[0].setChecked(True)

        v.addStretch()

        btn_settings = QPushButton("⚙  Pengaturan")
        btn_settings.setObjectName("navSettingsBtn")
        btn_settings.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_settings.clicked.connect(self._open_settings_dialog)
        v.addWidget(btn_settings)

        return sidebar

    def _make_nav_button(self, icon: str, label: str, shortcut_key: str, index: int) -> QPushButton:
        btn = QPushButton(f"{icon}   {label}")
        btn.setObjectName("navItem")
        btn.setCheckable(True)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(lambda: self._go_to_page(index))
        return btn

    def _go_to_page(self, index: int) -> None:
        self._stack.setCurrentIndex(index)
        self._nav_buttons[index].setChecked(True)
        self._lbl_section_title.setText(self._NAV_ITEMS[index][1])

    def _open_settings_dialog(self) -> None:
        dialog = SettingsDialog(self)
        dialog.exec()

    # ── Header ────────────────────────────────────────────────────────────────

    def _make_header(self) -> QWidget:
        header = QWidget()
        header.setObjectName("appHeader")
        header.setFixedHeight(56)
        layout = QHBoxLayout(header)
        layout.setContentsMargins(20, 0, 20, 0)

        self._lbl_section_title = QLabel(self._NAV_ITEMS[0][1])
        self._lbl_section_title.setObjectName("headerTitle")
        layout.addWidget(self._lbl_section_title)

        layout.addStretch()

        self._lbl_date = QLabel()
        self._lbl_date.setObjectName("headerDate")
        self._update_date_label()
        layout.addWidget(self._lbl_date)

        self._clock_timer = QTimer(self)
        self._clock_timer.timeout.connect(self._update_date_label)
        self._clock_timer.start(1000)

        return header

    def _update_date_label(self) -> None:
        self._lbl_date.setText(datetime.now().strftime("%A, %d %B %Y  |  %H:%M:%S"))

    # ── Tab Pengunjung ────────────────────────────────────────────────────────

    def _build_visitor_tab(self, parent: QWidget) -> None:
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(2)
        splitter.setObjectName("mainSplitter")

        cam_panel   = self._make_camera_panel()
        right_panel = self._make_right_panel()

        # Panel kanan punya minimum width agar tidak bisa ditekan habis
        right_panel.setMinimumWidth(340)

        splitter.addWidget(cam_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([600, 440])
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)

        layout.addWidget(splitter)

    def _make_camera_panel(self) -> QWidget:
        panel = QWidget()
        panel.setObjectName("cameraPanel")
        # Batasi lebar maksimum panel kamera agar tidak menekan panel kanan
        panel.setMaximumWidth(760)
        panel.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 16, 8, 16)
        layout.setSpacing(10)

        cam_header = QHBoxLayout()
        lbl_cam = QLabel("FEED KAMERA")
        lbl_cam.setObjectName("panelLabel")
        cam_header.addWidget(lbl_cam)
        cam_header.addStretch()

        self._lbl_cam_status = QLabel("● STANDBY")
        self._lbl_cam_status.setObjectName("camStatusStandby")
        cam_header.addWidget(self._lbl_cam_status)
        layout.addLayout(cam_header)

        self._lbl_camera = QLabel()
        self._lbl_camera.setObjectName("cameraDisplay")
        self._lbl_camera.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # Preferred + Expanding: bisa mengecil, tidak memaksa expand horizontal
        self._lbl_camera.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        self._lbl_camera.setMinimumWidth(320)
        self._lbl_camera.setText("Menghubungkan ke kamera...")
        layout.addWidget(self._lbl_camera, stretch=1)

        self._btn_reconnect = QPushButton("🔄  Reconnect Kamera")
        self._btn_reconnect.setObjectName("btnReconnect")
        self._btn_reconnect.clicked.connect(self._connect_camera)
        self._btn_reconnect.setVisible(False)
        layout.addWidget(self._btn_reconnect)

        return panel

    def _make_right_panel(self) -> QWidget:
        panel = QWidget()
        panel.setObjectName("rightPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 16, 16, 16)
        layout.setSpacing(12)

        layout.addWidget(self._make_search_section())
        layout.addWidget(self._make_visitor_table(), stretch=2)
        layout.addWidget(self._make_log_console(), stretch=1)

        return panel

    def _make_search_section(self) -> QWidget:
        container = QWidget()
        container.setObjectName("searchContainer")
        v = QVBoxLayout(container)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(6)

        lbl = QLabel("CARI ANGGOTA")
        lbl.setObjectName("panelLabel")
        v.addWidget(lbl)


        self._input_search = QLineEdit()
        self._input_search.setPlaceholderText("Nama atau ID barcode...")
        self._input_search.setObjectName("searchInput")
        self._input_search.textChanged.connect(self._on_search_changed)
        v.addWidget(self._input_search)


        self._search_results = QListWidget()
        self._search_results.setObjectName("searchResults")
        self._search_results.setMaximumHeight(120)
        self._search_results.setVisible(False)
        self._search_results.itemDoubleClicked.connect(self._on_search_result_selected)
        v.addWidget(self._search_results)

        lbl_hint = QLabel("Double-klik hasil pencarian untuk catat kunjungan manual")
        lbl_hint.setObjectName("hintLabel")
        v.addWidget(lbl_hint)

        return container

    def _make_visitor_table(self) -> QWidget:
        container = QWidget()
        v = QVBoxLayout(container)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(6)

        header_row = QHBoxLayout()
        lbl = QLabel("PENGUNJUNG HARI INI")
        lbl.setObjectName("panelLabel")
        header_row.addWidget(lbl)
        header_row.addStretch()

        self._lbl_count = QLabel("0 orang")
        self._lbl_count.setObjectName("countLabel")
        header_row.addWidget(self._lbl_count)
        v.addLayout(header_row)

        self._table = QTableWidget()
        self._table.setObjectName("visitorTable")
        self._table.setColumnCount(4)
        self._table.setHorizontalHeaderLabels(["No", "Waktu", "ID Barcode", "Nama"])
        self._table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self._table.setColumnWidth(0, 40)
        self._table.setColumnWidth(1, 80)
        self._table.setColumnWidth(2, 120)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        v.addWidget(self._table)

        return container

    def _make_log_console(self) -> QWidget:
        container = QWidget()
        v = QVBoxLayout(container)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(6)

        header_row = QHBoxLayout()
        lbl = QLabel("KONSOL LOG")
        lbl.setObjectName("panelLabel")
        header_row.addWidget(lbl)
        header_row.addStretch()

        btn_clear = QPushButton("Bersihkan")
        btn_clear.setObjectName("btnClear")
        btn_clear.clicked.connect(self._clear_log)
        header_row.addWidget(btn_clear)
        v.addLayout(header_row)

        self._log_console = QTextEdit()
        self._log_console.setObjectName("logConsole")
        self._log_console.setReadOnly(True)
        self._log_console.setFont(QFont("Consolas", 10))
        v.addWidget(self._log_console)

        return container

    # ══════════════════════════════════════════════════════════════════════════
    # Style
    # ══════════════════════════════════════════════════════════════════════════


    # ══════════════════════════════════════════════════════════════════════════
    # Kamera
    # ══════════════════════════════════════════════════════════════════════════

    def _connect_camera(self) -> None:
        # Hentikan thread lama jika ada
        self._stop_scanner_thread()
        self._display_timer.stop()
        self._set_cam_status("standby")
        self._btn_reconnect.setVisible(False)

        if self._camera_url:
            ok = self._cam_manager.connect_ip(self._camera_url)
        elif self._camera_index is not None:
            ok = self._cam_manager.connect(self._camera_index)
        else:
            self._log("Tidak ada sumber kamera.", "error")
            return

        if ok:
            self._set_cam_status("active")
            self._log(f"Kamera terhubung: {self._cam_manager.source}", "success")
            # Mulai scanner thread (baca + decode barcode di background)
            self._scanner_thread = ScannerThread(
                camera=self._cam_manager,
                on_barcode=lambda data: self._barcode_detected.emit(data),
                on_frame_ready=self._receive_frame,
            )
            self._scanner_thread.start()
            # Display timer: 33ms = ~30fps, hanya render frame dari buffer
            self._display_timer.start(33)
        else:
            self._set_cam_status("error")
            self._log("Gagal terhubung ke kamera.", "error")
            self._btn_reconnect.setVisible(True)

    def _stop_scanner_thread(self) -> None:
        if self._scanner_thread is not None:
            self._scanner_thread.stop()
            self._scanner_thread.join(timeout=1.0)
            self._scanner_thread = None

    def _receive_frame(self, frame) -> None:
        """Dipanggil dari ScannerThread — simpan frame terbaru ke buffer."""
        with self._frame_lock:
            self._latest_frame = frame

    def _refresh_display(self) -> None:
        """Dipanggil QTimer di main thread — render frame dari buffer."""
        with self._frame_lock:
            frame = self._latest_frame
        if frame is None:
            # Cek apakah stream putus
            if not self._cam_manager.is_connected:
                self._handle_camera_loss()
            return
        self._display_frame(frame)

    def _display_frame(self, frame: np.ndarray) -> None:
        lbl_w = self._lbl_camera.width()
        lbl_h = self._lbl_camera.height()
        if lbl_w < 10 or lbl_h < 10:
            return

        # Resize ke ukuran display dulu — hemat piksel saat konversi warna
        frame_h, frame_w = frame.shape[:2]
        scale = min(lbl_w / frame_w, lbl_h / frame_h, 1.0)
        if scale < 0.99:
            new_w = int(frame_w * scale)
            new_h = int(frame_h * scale)
            frame = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

        # Grayscale untuk display — 1 channel, lebih ringan dari RGB
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape
        qimg = QImage(gray.data, w, h, w, QImage.Format.Format_Grayscale8)
        self._lbl_camera.setPixmap(QPixmap.fromImage(qimg))

    def _handle_camera_loss(self) -> None:
        self._display_timer.stop()
        self._stop_scanner_thread()
        self._set_cam_status("error")
        self._log("Koneksi kamera terputus.", "error")
        self._btn_reconnect.setVisible(True)
        self._lbl_camera.setText("❌  Koneksi kamera terputus.\nTekan Reconnect untuk mencoba lagi.")

    def _set_cam_status(self, state: str) -> None:
        labels = {
            "standby": ("● STANDBY", "camStatusStandby"),
            "active":  ("● AKTIF",   "camStatusActive"),
            "error":   ("● ERROR",   "camStatusError"),
        }
        text, obj_name = labels.get(state, labels["standby"])
        self._lbl_cam_status.setText(text)
        self._lbl_cam_status.setObjectName(obj_name)
        self._lbl_cam_status.setStyleSheet(self._lbl_cam_status.styleSheet())

    # ══════════════════════════════════════════════════════════════════════════
    # Logika barcode & kunjungan
    # ══════════════════════════════════════════════════════════════════════════

    # Indeks halaman "Peminjaman" di self._stack — harus sinkron dengan urutan
    # penambahan widget di _build_ui() dan urutan _NAV_ITEMS.
    _PAGE_PEMINJAMAN = 6

    def _handle_barcode(self, barcode_id: str) -> None:
        # Kamera scan berjalan terus di background (ScannerThread) terlepas
        # dari halaman yang sedang ditampilkan. Saat pengguna berada di
        # halaman Peminjaman, arahkan hasil scan ke sana (isi field
        # anggota/buku atau cari transaksi pengembalian) alih-alih mencatat
        # kunjungan — supaya satu kamera bisa dipakai baik untuk absensi
        # maupun sirkulasi peminjaman.
        if self._stack.currentIndex() == self._PAGE_PEMINJAMAN:
            self._loan_tab.handle_scanned_code(barcode_id)
            return

        member = find_by_barcode(barcode_id)
        if member is None:
            self._log(f"Barcode tidak terdaftar: {barcode_id}", "error")
            return

        nama = member["Nama"]
        if record_visit(barcode_id, nama):
            self._log(f"[MASUK] {nama}  ({barcode_id})", "success")
            self._refresh_table()
            self._update_status_bar()
        else:
            self._log(f"{nama} sudah tercatat hari ini.", "warning")

    def _record_manual(self, barcode_id: str, nama: str) -> None:
        if record_visit(barcode_id, nama):
            self._log(f"[MANUAL] {nama}  ({barcode_id})", "success")
            self._refresh_table()
            self._update_status_bar()
        else:
            self._log(f"{nama} sudah tercatat hari ini.", "warning")

    # ══════════════════════════════════════════════════════════════════════════
    # Search
    # ══════════════════════════════════════════════════════════════════════════

    def _on_search_changed(self, text: str) -> None:
        if len(text) < 2:
            self._search_results.setVisible(False)
            return
        self._do_search()

    def _do_search(self) -> None:
        query = self._input_search.text().strip()
        if not query:
            return
        results = search(query)
        self._search_results.clear()

        if not results:
            item = QListWidgetItem("Tidak ditemukan")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self._search_results.addItem(item)
        else:
            for m in results:
                item = QListWidgetItem(f"{m['Nama']}  |  {m['ID Barcode']}")
                item.setData(Qt.ItemDataRole.UserRole, m)
                self._search_results.addItem(item)

        self._search_results.setVisible(True)

    def _on_search_result_selected(self, item: QListWidgetItem) -> None:
        member = item.data(Qt.ItemDataRole.UserRole)
        if not member:
            return
        self._record_manual(member["ID Barcode"], member["Nama"])
        self._search_results.setVisible(False)
        self._input_search.clear()

    # ══════════════════════════════════════════════════════════════════════════
    # Tabel & log
    # ══════════════════════════════════════════════════════════════════════════

    def _refresh_table(self) -> None:
        visitors = get_today_visitors()
        self._table.setRowCount(len(visitors))

        for row_idx, v in enumerate(visitors):
            waktu = v["waktu_masuk"][11:19] if len(v["waktu_masuk"]) >= 19 else v["waktu_masuk"]
            for col_idx, text in enumerate([str(row_idx + 1), waktu, v["barcode_id"], v["nama"]]):
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
                self._table.setItem(row_idx, col_idx, item)

        self._lbl_count.setText(f"{len(visitors)} orang")

    def _update_status_bar(self) -> None:
        count = get_visit_count_today()
        self._lbl_kunjungan.setText(f"Kunjungan hari ini: {count}")

    def _log(self, message: str, level: str = "info") -> None:
        lc     = _log_colors()
        color  = lc.get(level, lc["info"])
        ts_clr = lc.get("ts", "#888888")
        prefix = {"success": "✓", "warning": "⚠", "error": "✗", "info": "i"}.get(level, "i")
        ts = datetime.now().strftime("%H:%M:%S")
        html = (
            f'<span style="color:{ts_clr}">[{ts}]</span> '
            f'<span style="color:{color}">{prefix} {message}</span><br>'
        )
        self._log_console.moveCursor(QTextCursor.MoveOperation.End)
        self._log_console.insertHtml(html)
        self._log_console.moveCursor(QTextCursor.MoveOperation.End)

    def _clear_log(self) -> None:
        self._log_console.clear()

    # ══════════════════════════════════════════════════════════════════════════
    # Cleanup
    # ══════════════════════════════════════════════════════════════════════════

    def closeEvent(self, event) -> None:
        self._display_timer.stop()
        self._clock_timer.stop()
        self._stop_scanner_thread()
        self._cam_manager.release()
        logger.info("Aplikasi ditutup.")
        super().closeEvent(event)