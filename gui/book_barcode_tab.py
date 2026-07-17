"""
gui/book_barcode_tab.py — Tab cetak label QR Code buku massal

Layout kolom kiri (fixed 310px) — alur UX:
  ┌─────────────┐
  │ 1. FILTER   │  Semua / per kategori / pilih manual
  ├─────────────┤
  │ 2. KONFIGUR │  Tampilkan pengarang, label per baris
  ├─────────────┤
  │ 3. GENERATE │  Pilih direktori output + tombol Generate
  └─────────────┘

Layout kolom kanan (stretch):
  ┌──────────────────────────────┐
  │   DAFTAR BUKU YANG DIPILIH   │  ← atas
  ├──────────────┬───────────────┤
  │   HASIL      │   LOG PROSES  │  ← bawah
  │   OUTPUT     │               │
  └──────────────┴───────────────┘
"""

import logging
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QThread, Signal as pyqtSignal
from PySide6.QtGui import QFont, QTextCursor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QFileDialog, QProgressBar, QTextEdit,
    QGroupBox, QComboBox, QCheckBox, QSpinBox,
    QSizePolicy, QMessageBox, QAbstractItemView,
)

from theme import log_colors as _log_colors

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# Worker thread
# ══════════════════════════════════════════════════════════════════════════════

class BookBarcodeWorker(QThread):
    progress = pyqtSignal(str, int, int)
    finished = pyqtSignal(dict)
    error    = pyqtSignal(str)

    def __init__(
        self,
        kategori: Optional[str],
        kode_list: Optional[list],
        show_author: bool,
        labels_per_row: int,
        output_dir: Optional[str],
    ):
        super().__init__()
        self.kategori       = kategori
        self.kode_list      = kode_list
        self.show_author    = show_author
        self.labels_per_row = labels_per_row
        self.output_dir     = output_dir

    def run(self) -> None:
        try:
            from core.book_barcode_generator import run_book_barcode_generation
            result = run_book_barcode_generation(
                kategori=self.kategori,
                kode_list=self.kode_list,
                show_author=self.show_author,
                labels_per_row=self.labels_per_row,
                output_dir=self.output_dir,
                on_progress=lambda stage, cur, tot: self.progress.emit(stage, cur, tot),
            )
            self.finished.emit(result)
        except Exception as exc:
            logger.error("Book barcode generation error: %s", exc)
            self.error.emit(str(exc))


# ══════════════════════════════════════════════════════════════════════════════
# Tab widget
# ══════════════════════════════════════════════════════════════════════════════

class BookBarcodeTab(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self._books_preview: list[dict]          = []
        self._worker: Optional[BookBarcodeWorker] = None
        self._result_docx_path: Optional[Path]   = None
        self._result_barcode_dir: Optional[Path] = None
        self._output_dir: Optional[str]          = None

        self._build_ui()
        self._load_categories()

    # ══════════════════════════════════════════════════════════════════════════
    # Build UI
    # ══════════════════════════════════════════════════════════════════════════

    def _build_ui(self) -> None:
        root = QGridLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)
        root.setColumnStretch(0, 0)
        root.setColumnStretch(1, 1)
        root.setRowStretch(0, 3)
        root.setRowStretch(1, 2)

        # Kolom kiri
        left_col = QVBoxLayout()
        left_col.setSpacing(10)
        left_col.setContentsMargins(0, 0, 0, 0)
        left_col.addWidget(self._make_filter_panel())
        left_col.addWidget(self._make_config_panel())
        left_col.addWidget(self._make_generate_panel())
        left_col.addStretch()

        left_wrapper = QWidget()
        left_wrapper.setLayout(left_col)
        left_wrapper.setFixedWidth(310)
        root.addWidget(left_wrapper, 0, 0, 2, 1)

        # Kanan atas: preview tabel buku
        root.addWidget(self._make_preview_panel(), 0, 1)

        # Kanan bawah: hasil + log
        bottom_right = QHBoxLayout()
        bottom_right.setSpacing(10)
        bottom_right.setContentsMargins(0, 0, 0, 0)
        bottom_right.addWidget(self._make_result_panel(), stretch=2)
        bottom_right.addWidget(self._make_log_panel(),    stretch=3)

        bottom_wrapper = QWidget()
        bottom_wrapper.setLayout(bottom_right)
        root.addWidget(bottom_wrapper, 1, 1)

    # ── Panel 1: Filter ───────────────────────────────────────────────────────

    def _make_filter_panel(self) -> QGroupBox:
        grp = QGroupBox("1  ·  FILTER BUKU")
        grp.setObjectName("cardGroup")
        v = QVBoxLayout(grp)
        v.setSpacing(8)

        lbl = QLabel("Pilih buku yang akan dicetak labelnya.")
        lbl.setObjectName("hintText")
        lbl.setWordWrap(True)
        v.addWidget(lbl)

        # Mode filter
        v.addWidget(self._field_label("Mode filter:"))
        self._combo_filter_mode = QComboBox()
        self._combo_filter_mode.setObjectName("configCombo")
        self._combo_filter_mode.addItem("Semua buku",          userData="all")
        self._combo_filter_mode.addItem("Filter per kategori", userData="category")
        self._combo_filter_mode.addItem("Pilih manual",        userData="manual")
        self._combo_filter_mode.currentIndexChanged.connect(self._on_filter_mode_changed)
        v.addWidget(self._combo_filter_mode)

        # Kombo kategori (tampil saat mode=category)
        self._widget_category = QWidget()
        vc = QVBoxLayout(self._widget_category)
        vc.setContentsMargins(0, 0, 0, 0)
        vc.setSpacing(4)
        vc.addWidget(self._field_label("Kategori:"))
        self._combo_category = QComboBox()
        self._combo_category.setObjectName("configCombo")
        vc.addWidget(self._combo_category)
        self._widget_category.setVisible(False)
        v.addWidget(self._widget_category)

        # Hint manual (tampil saat mode=manual)
        self._lbl_manual_hint = QLabel("Pilih baris di tabel kanan\n(Ctrl+klik untuk multi-pilih)")
        self._lbl_manual_hint.setObjectName("hintText")
        self._lbl_manual_hint.setWordWrap(True)
        self._lbl_manual_hint.setVisible(False)
        v.addWidget(self._lbl_manual_hint)

        # Tombol muat preview
        self._btn_load = QPushButton("🔍  Muat Daftar Buku")
        self._btn_load.setObjectName("btnPreview")
        self._btn_load.clicked.connect(self._load_preview)
        v.addWidget(self._btn_load)

        return grp

    # ── Panel 2: Konfigurasi ──────────────────────────────────────────────────

    def _make_config_panel(self) -> QGroupBox:
        grp = QGroupBox("2  ·  KONFIGURASI LABEL")
        grp.setObjectName("cardGroup")
        v = QVBoxLayout(grp)
        v.setSpacing(8)

        # Tampilkan pengarang
        self._chk_author = QCheckBox("Tampilkan nama pengarang")
        self._chk_author.setObjectName("configCheck")
        self._chk_author.setChecked(True)
        v.addWidget(self._chk_author)

        # Label per baris
        v.addWidget(self._field_label("Label per baris (A4):"))
        row_spin = QHBoxLayout()
        self._spin_per_row = QSpinBox()
        self._spin_per_row.setRange(1, 4)
        self._spin_per_row.setValue(3)
        self._spin_per_row.setObjectName("configInput")
        self._spin_per_row.setFixedWidth(70)
        self._spin_per_row.valueChanged.connect(self._update_layout_hint)
        row_spin.addWidget(self._spin_per_row)

        self._lbl_layout_hint = QLabel()
        self._lbl_layout_hint.setObjectName("idFmtLabel")
        self._lbl_layout_hint.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        row_spin.addWidget(self._lbl_layout_hint, stretch=1)
        v.addLayout(row_spin)
        self._update_layout_hint()

        return grp

    # ── Panel 3: Generate ─────────────────────────────────────────────────────

    def _make_generate_panel(self) -> QGroupBox:
        grp = QGroupBox("3  ·  GENERATE LABEL")
        grp.setObjectName("cardGroup")
        v = QVBoxLayout(grp)
        v.setSpacing(8)

        v.addWidget(self._field_label("Simpan hasil ke folder:"))
        dir_row = QHBoxLayout()
        self._input_outdir = QComboBox()
        self._input_outdir.setObjectName("fileInput")
        self._input_outdir.setEditable(True)
        self._input_outdir.lineEdit().setPlaceholderText("Default: folder bawaan aplikasi")
        self._input_outdir.lineEdit().setReadOnly(True)
        dir_row.addWidget(self._input_outdir)

        btn_dir = QPushButton("Pilih")
        btn_dir.setObjectName("btnBrowse")
        btn_dir.setFixedWidth(52)
        btn_dir.clicked.connect(self._browse_output_dir)
        dir_row.addWidget(btn_dir)
        v.addLayout(dir_row)

        self._progress_bar = QProgressBar()
        self._progress_bar.setObjectName("genProgress")
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setVisible(False)
        v.addWidget(self._progress_bar)

        self._lbl_progress = QLabel("")
        self._lbl_progress.setObjectName("progressLabel")
        self._lbl_progress.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lbl_progress.setWordWrap(True)
        self._lbl_progress.setVisible(False)
        v.addWidget(self._lbl_progress)

        self._btn_generate = QPushButton("▶  Generate Label QR Code")
        self._btn_generate.setObjectName("btnGenerate")
        self._btn_generate.setEnabled(False)
        self._btn_generate.clicked.connect(self._start_generation)
        v.addWidget(self._btn_generate)

        return grp

    # ── Panel kanan atas: Tabel preview buku ──────────────────────────────────

    def _make_preview_panel(self) -> QWidget:
        container = QWidget()
        container.setObjectName("previewContainer")
        v = QVBoxLayout(container)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(6)

        hdr = QHBoxLayout()
        lbl = QLabel("DAFTAR BUKU")
        lbl.setObjectName("panelLabel")
        hdr.addWidget(lbl)
        hdr.addStretch()
        self._lbl_count = QLabel("0 buku")
        self._lbl_count.setObjectName("countLabel")
        hdr.addWidget(self._lbl_count)
        v.addLayout(hdr)

        self._table_preview = QTableWidget()
        self._table_preview.setObjectName("previewTable")
        self._table_preview.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table_preview.setAlternatingRowColors(True)
        self._table_preview.verticalHeader().setVisible(False)
        self._table_preview.horizontalHeader().setStretchLastSection(True)
        self._table_preview.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        # Multi-select untuk mode manual
        self._table_preview.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        self._table_preview.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table_preview.itemSelectionChanged.connect(self._on_selection_changed)
        v.addWidget(self._table_preview, stretch=1)

        return container

    # ── Panel kanan bawah kiri: Hasil Output ──────────────────────────────────

    def _make_result_panel(self) -> QWidget:
        container = QWidget()
        container.setObjectName("cardGroup")
        v = QVBoxLayout(container)
        v.setContentsMargins(12, 12, 12, 12)
        v.setSpacing(8)

        hdr = QLabel("HASIL OUTPUT")
        hdr.setObjectName("panelLabel")
        v.addWidget(hdr)

        self._lbl_result = QLabel("Belum ada output.")
        self._lbl_result.setObjectName("resultLabel")
        self._lbl_result.setWordWrap(True)
        v.addWidget(self._lbl_result)
        v.addStretch()

        self._btn_open_label_dir = QPushButton("📁  Buka Folder Label")
        self._btn_open_label_dir.setObjectName("btnOpenFile")
        self._btn_open_label_dir.setEnabled(False)
        self._btn_open_label_dir.setToolTip("Buka folder file Word (.docx) label buku")
        self._btn_open_label_dir.clicked.connect(self._open_label_folder)
        v.addWidget(self._btn_open_label_dir)

        self._btn_open_barcode_dir = QPushButton("🖼  Folder QR Code PNG")
        self._btn_open_barcode_dir.setObjectName("btnOpenFile")
        self._btn_open_barcode_dir.setEnabled(False)
        self._btn_open_barcode_dir.setToolTip("Buka folder gambar QR Code PNG per buku")
        self._btn_open_barcode_dir.clicked.connect(self._open_barcode_dir_action)
        v.addWidget(self._btn_open_barcode_dir)

        return container

    # ── Panel kanan bawah kanan: Log Proses ───────────────────────────────────

    def _make_log_panel(self) -> QWidget:
        container = QWidget()
        v = QVBoxLayout(container)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(6)

        hdr = QHBoxLayout()
        lbl = QLabel("LOG PROSES")
        lbl.setObjectName("panelLabel")
        hdr.addWidget(lbl)
        hdr.addStretch()
        btn_clear = QPushButton("Bersihkan")
        btn_clear.setObjectName("btnClear")
        btn_clear.clicked.connect(self._clear_log)
        hdr.addWidget(btn_clear)
        v.addLayout(hdr)

        self._log_console = QTextEdit()
        self._log_console.setObjectName("logConsole")
        self._log_console.setReadOnly(True)
        self._log_console.setFont(QFont("Consolas", 10))
        self._log_console.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        v.addWidget(self._log_console, stretch=1)

        return container

    # ══════════════════════════════════════════════════════════════════════════
    # Helpers
    # ══════════════════════════════════════════════════════════════════════════

    def _field_label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("fieldLabel")
        return lbl

    def _update_layout_hint(self) -> None:
        n = self._spin_per_row.value()
        lebar = {1: "±18cm", 2: "±9cm", 3: "±6cm", 4: "±4.5cm"}.get(n, "")
        self._lbl_layout_hint.setText(f"{n} kolom  {lebar}/label")

    def _load_categories(self) -> None:
        """Isi combo kategori dari database saat tab pertama kali dibuka."""
        try:
            from core.book_barcode_generator import fetch_all_categories
            cats = fetch_all_categories()
            self._combo_category.clear()
            for cat in cats:
                self._combo_category.addItem(cat)
            if not cats:
                self._combo_category.addItem("(belum ada kategori)")
        except Exception as exc:
            logger.warning("Gagal load kategori: %s", exc)

    def _on_filter_mode_changed(self, index: int) -> None:
        mode = self._combo_filter_mode.currentData()
        self._widget_category.setVisible(mode == "category")
        self._lbl_manual_hint.setVisible(mode == "manual")
        # Reset tabel & tombol generate saat mode berubah
        self._books_preview = []
        self._table_preview.clearContents()
        self._table_preview.setRowCount(0)
        self._lbl_count.setText("0 buku")
        self._btn_generate.setEnabled(False)
        # Aktifkan/nonaktifkan multi-select di tabel
        is_manual = (mode == "manual")
        self._table_preview.setSelectionMode(
            QAbstractItemView.SelectionMode.MultiSelection if is_manual
            else QAbstractItemView.SelectionMode.NoSelection
        )

    def _on_selection_changed(self) -> None:
        """Update tombol generate berdasarkan jumlah baris terpilih (mode manual)."""
        if self._combo_filter_mode.currentData() == "manual":
            n = len(self._table_preview.selectionModel().selectedRows())
            self._btn_generate.setEnabled(n > 0)
            self._lbl_count.setText(f"{n} buku dipilih")

    # ══════════════════════════════════════════════════════════════════════════
    # Aksi
    # ══════════════════════════════════════════════════════════════════════════

    def _load_preview(self) -> None:
        """Muat daftar buku sesuai filter yang dipilih."""
        try:
            from core.book_barcode_generator import fetch_books
            mode = self._combo_filter_mode.currentData()

            if mode == "all":
                books = fetch_books()
            elif mode == "category":
                cat = self._combo_category.currentText()
                books = fetch_books(kategori=cat)
            else:
                # Mode manual: muat semua dulu, user pilih dari tabel
                books = fetch_books()

            self._books_preview = books
            self._populate_table(books)
            self._lbl_count.setText(f"{len(books)} buku")

            if mode != "manual":
                self._btn_generate.setEnabled(len(books) > 0)

            self._log(f"Daftar buku dimuat: {len(books)} buku.", "success")

            if len(books) == 0:
                self._log("Tidak ada buku di database. Tambahkan buku di Tab Buku terlebih dahulu.", "warning")

        except Exception as exc:
            self._log(f"Gagal memuat daftar buku: {exc}", "error")
            QMessageBox.critical(self, "Error", str(exc))

    def _populate_table(self, books: list[dict]) -> None:
        headers = ["Kode Buku", "Judul", "Pengarang", "Kategori"]
        keys    = ["kode_buku", "judul", "pengarang", "kategori"]
        self._table_preview.setColumnCount(len(headers))
        self._table_preview.setHorizontalHeaderLabels(headers)
        self._table_preview.setRowCount(len(books))
        for row_idx, book in enumerate(books):
            for col_idx, key in enumerate(keys):
                val  = str(book.get(key, "") or "")
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
                self._table_preview.setItem(row_idx, col_idx, item)
        self._table_preview.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

    def _browse_output_dir(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self, "Pilih Folder Output Label",
            self._output_dir or str(Path.home())
        )
        if not folder:
            return
        self._output_dir = folder
        self._input_outdir.setCurrentText(folder)
        self._log(f"Folder output: {folder}", "info")

    def _get_selected_kode_list(self) -> Optional[list[str]]:
        """Kembalikan list kode_buku yang dipilih (mode manual), atau None."""
        mode = self._combo_filter_mode.currentData()
        if mode != "manual":
            return None
        selected_rows = self._table_preview.selectionModel().selectedRows()
        if not selected_rows:
            return None
        kode_list = []
        for idx in selected_rows:
            row = idx.row()
            if row < len(self._books_preview):
                kode_list.append(self._books_preview[row]["kode_buku"])
        return kode_list if kode_list else None

    def _start_generation(self) -> None:
        mode = self._combo_filter_mode.currentData()

        # Tentukan parameter
        kategori  = None
        kode_list = None

        if mode == "category":
            kategori = self._combo_category.currentText()
        elif mode == "manual":
            kode_list = self._get_selected_kode_list()
            if not kode_list:
                QMessageBox.warning(self, "Belum Ada Pilihan",
                                    "Pilih minimal satu buku dari tabel terlebih dahulu.")
                return

        # Hitung jumlah buku yang akan diproses
        if mode == "manual" and kode_list:
            n = len(kode_list)
        else:
            n = len(self._books_preview)

        if n == 0:
            QMessageBox.warning(self, "Tidak Ada Buku",
                                "Tidak ada buku yang sesuai filter. Muat daftar buku terlebih dahulu.")
            return

        reply = QMessageBox.question(
            self, "Konfirmasi",
            f"Generate label untuk {n} buku?\n\nProses ini akan membuat file .docx siap cetak.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self._btn_generate.setEnabled(False)
        self._progress_bar.setValue(0)
        self._progress_bar.setVisible(True)
        self._lbl_progress.setVisible(True)

        show_author    = self._chk_author.isChecked()
        labels_per_row = self._spin_per_row.value()

        mode_label = {"all": "semua buku", "category": f"kategori '{kategori}'",
                      "manual": f"{n} buku dipilih"}.get(mode, mode)
        self._log(f"Mulai generate — {mode_label}, {labels_per_row} label/baris.", "info")
        if self._output_dir:
            self._log(f"Output → {self._output_dir}", "info")

        self._worker = BookBarcodeWorker(
            kategori=kategori,
            kode_list=kode_list,
            show_author=show_author,
            labels_per_row=labels_per_row,
            output_dir=self._output_dir,
        )
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_progress(self, stage: str, current: int, total: int) -> None:
        pct = int(current / total * 100) if total else 0
        self._progress_bar.setValue(pct)
        label = {"barcode": "Generate QR Code PNG", "docx": "Menyusun Word"}.get(stage, stage)
        self._lbl_progress.setText(f"{label}  {current}/{total}")

    def _on_finished(self, result: dict) -> None:
        self._btn_generate.setEnabled(True)
        self._progress_bar.setValue(100)
        self._lbl_progress.setVisible(False)
        self._progress_bar.setVisible(False)

        count     = result.get("count", 0)
        docx_path = result.get("docx_path")
        bc_dir    = result.get("barcode_dir")

        for e in result.get("errors", []):
            self._log(e, "error")

        self._log(f"Selesai — {count} label buku dibuat.", "success")

        if docx_path:
            self._result_docx_path = docx_path
            fname = Path(docx_path).name
            self._lbl_result.setText(
                f"✓ {count} label selesai\n\n"
                f"📄 {fname}\n\n"
                f"Klik tombol di bawah untuk membuka folder."
            )
            self._btn_open_label_dir.setEnabled(True)

        if bc_dir:
            self._result_barcode_dir = bc_dir
            self._btn_open_barcode_dir.setEnabled(True)

        QMessageBox.information(
            self, "Selesai",
            f"✅ {count} label buku berhasil dibuat!\n\n"
            f"Buka folder hasil untuk menemukan file Word,\n"
            f"lalu cetak dari Microsoft Word."
        )

    def _on_error(self, message: str) -> None:
        self._btn_generate.setEnabled(True)
        self._progress_bar.setVisible(False)
        self._lbl_progress.setVisible(False)
        self._log(f"ERROR: {message}", "error")
        QMessageBox.critical(self, "Error", message)

    # ── Buka folder ────────────────────────────────────────────────────────────

    def _open_label_folder(self) -> None:
        if not self._result_docx_path:
            QMessageBox.warning(self, "Belum Ada Output", "Belum ada file yang dihasilkan.")
            return
        self._open_in_explorer(str(Path(self._result_docx_path).parent))

    def _open_barcode_dir_action(self) -> None:
        if not self._result_barcode_dir:
            QMessageBox.warning(self, "Belum Ada Output", "Belum ada QR Code yang dihasilkan.")
            return
        self._open_in_explorer(str(self._result_barcode_dir))

    def _open_in_explorer(self, path: str) -> None:
        if not Path(path).exists():
            QMessageBox.warning(self, "Tidak Ditemukan", f"Folder tidak ditemukan:\n{path}")
            return
        try:
            if sys.platform == "win32":
                os.startfile(path)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception as exc:
            logger.error("Gagal buka folder: %s", exc)
            QMessageBox.warning(self, "Gagal", f"Tidak dapat membuka folder:\n{exc}")

    # ── Log ────────────────────────────────────────────────────────────────────

    def _log(self, message: str, level: str = "info") -> None:
        lc     = _log_colors()
        color  = lc.get(level, lc["info"])
        ts_clr = lc.get("ts", "#888888")
        prefix = {"success": "✓", "warning": "⚠", "error": "✗", "info": "i"}.get(level, "i")
        ts     = datetime.now().strftime("%H:%M:%S")
        html   = (
            f'<span style="color:{ts_clr}">[{ts}]</span> '
            f'<span style="color:{color}">{prefix} {message}</span><br>'
        )
        self._log_console.moveCursor(QTextCursor.MoveOperation.End)
        self._log_console.insertHtml(html)
        self._log_console.moveCursor(QTextCursor.MoveOperation.End)

    def _clear_log(self) -> None:
        self._log_console.clear()

    # ══════════════════════════════════════════════════════════════════════════
    # Public: refresh kategori jika tab buku menambah data baru
    # ══════════════════════════════════════════════════════════════════════════

    def refresh_categories(self) -> None:
        """Dipanggil dari main_window saat tab Buku menambah/hapus buku."""
        self._load_categories()