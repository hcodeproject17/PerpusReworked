"""
gui/loan_tab.py — Tab Peminjaman & Pengembalian Buku PerpusReworked

Layout:
  ┌──────────────┬──────────────────────────────────────────────┐
  │   Sidebar    │   Panel konten (Pinjam / Kembali / Riwayat)  │
  │  + stat card │                                               │
  └──────────────┴──────────────────────────────────────────────┘

Panel:
  1. Pinjam Buku    — scan/cari anggota + scan/cari buku → konfirmasi
  2. Kembalikan     — scan/cari buku aktif → lihat denda → konfirmasi
  3. Sedang Dipinjam— tabel semua transaksi aktif + highlight terlambat
  4. Riwayat        — semua transaksi dengan filter status + search

Scan barcode/QR:
  Kamera global (yang sama dipakai di halaman Kunjungan) tetap aktif
  membaca frame di background lewat ScannerThread. Saat halaman
  Peminjaman ini yang sedang ditampilkan, MainWindow._handle_barcode()
  meneruskan tiap kode terbaca ke LoanTab.handle_scanned_code(), yang
  merutekannya ke panel Pinjam/Kembalikan yang sedang aktif. Lihat
  PinjamPanel.handle_scan() dan KembalikanPanel.handle_scan().
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Optional

from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QFont, QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QSplitter, QComboBox, QMessageBox, QFrame, QSpinBox,
    QDialog, QFormLayout, QTextEdit, QAbstractItemView,
    QStackedWidget, QSizePolicy, QScrollArea, QProgressBar,
    QListWidget, QListWidgetItem,
)

from database.loan_db import (
    borrow_book, return_book,
    get_active_loans, get_overdue_loans,
    search_loans, get_loan_by_id, get_loan_stats,
)
from database.settings_db import get_denda_per_hari, get_durasi_pinjam
from database.book_db import get_book_by_kode, search_books
from database.excel_reader import find_by_barcode, search as search_members
from theme import get_palette
from gui.widgets import section_label as _section_label

logger = logging.getLogger(__name__)

# ── Palet warna ───────────────────────────────────────────────────────────────
def _p():
    return get_palette()


# ══════════════════════════════════════════════════════════════════════════════
# Worker threads
# ══════════════════════════════════════════════════════════════════════════════

class _LoadLoansWorker(QThread):
    finished = Signal(list)

    def __init__(self, mode: str, query: str = "", status: str = "semua"):
        super().__init__()
        self._mode   = mode    # 'active' | 'overdue' | 'search'
        self._query  = query
        self._status = status

    def run(self):
        if self._mode == "active":
            self.finished.emit(get_active_loans())
        elif self._mode == "overdue":
            self.finished.emit(get_overdue_loans())
        else:
            self.finished.emit(search_loans(self._query, self._status))


# ══════════════════════════════════════════════════════════════════════════════
# Komponen kecil
# ══════════════════════════════════════════════════════════════════════════════

def _make_table(cols: list[str], stretch_col: int = 1) -> QTableWidget:
    t = QTableWidget()
    t.setObjectName("analyticsTable")
    t.setColumnCount(len(cols))
    t.setHorizontalHeaderLabels(cols)
    t.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    t.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    t.setAlternatingRowColors(True)
    t.verticalHeader().setVisible(False)
    t.horizontalHeader().setStretchLastSection(False)
    if 0 <= stretch_col < len(cols):
        t.horizontalHeader().setSectionResizeMode(
            stretch_col, QHeaderView.ResizeMode.Stretch)
    t.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
    return t


def _set_row(table: QTableWidget, row: int, values: list, color: Optional[QColor] = None):
    for col, val in enumerate(values):
        item = QTableWidgetItem(str(val))
        item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        if color:
            item.setBackground(color)
        table.setItem(row, col, item)


# ── Widget search anggota + buku (reusable) ───────────────────────────────────

class MemberSearchWidget(QWidget):
    """Search anggota dengan QListWidget dropdown."""
    member_selected = Signal(dict)   # emit dict anggota

    def __init__(self, placeholder="Nama atau ID Barcode anggota…", parent=None):
        super().__init__(parent)
        self._member: Optional[dict] = None

        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(4)

        self.inp = QLineEdit()
        self.inp.setObjectName("searchInput")
        self.inp.setPlaceholderText(placeholder)
        self.inp.textChanged.connect(self._on_text)
        v.addWidget(self.inp)

        self.lst = QListWidget()
        self.lst.setObjectName("searchResults")
        self.lst.setMaximumHeight(100)
        self.lst.setVisible(False)
        self.lst.itemClicked.connect(self._on_pick)
        v.addWidget(self.lst)

        self.lbl_info = QLabel("")
        self.lbl_info.setObjectName("hintLabel")
        v.addWidget(self.lbl_info)

    def _on_text(self, text: str):
        self._member = None
        self.lbl_info.setText("")
        if len(text) < 2:
            self.lst.setVisible(False)
            return
        results = search_members(text)
        self.lst.clear()
        if not results:
            item = QListWidgetItem("Tidak ditemukan")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.lst.addItem(item)
        else:
            for m in results:
                item = QListWidgetItem(f"{m['Nama']}  |  {m['ID Barcode']}")
                item.setData(Qt.ItemDataRole.UserRole, m)
                self.lst.addItem(item)
        self.lst.setVisible(True)

    def _on_pick(self, item: QListWidgetItem):
        m = item.data(Qt.ItemDataRole.UserRole)
        if not m:
            return
        self.select_member(m)

    def select_member(self, m: dict):
        """Pilih anggota langsung dari dict (dipakai juga oleh hasil scan barcode/QR)."""
        self._member = m
        self.inp.setText(f"{m['Nama']}  ({m['ID Barcode']})")
        self.lbl_info.setText(f"✓ Anggota dipilih: {m['Nama']}")
        self.lst.setVisible(False)
        self.member_selected.emit(m)

    def get_member(self) -> Optional[dict]:
        return self._member

    def clear(self):
        self.inp.clear()
        self.lst.clear()
        self.lst.setVisible(False)
        self.lbl_info.setText("")
        self._member = None


class BookSearchWidget(QWidget):
    """Search buku dengan QListWidget dropdown."""
    book_selected = Signal(dict)

    def __init__(self, placeholder="Judul, kode, atau ISBN buku…", parent=None):
        super().__init__(parent)
        self._book: Optional[dict] = None

        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(4)

        self.inp = QLineEdit()
        self.inp.setObjectName("searchInput")
        self.inp.setPlaceholderText(placeholder)
        self.inp.textChanged.connect(self._on_text)
        v.addWidget(self.inp)

        self.lst = QListWidget()
        self.lst.setObjectName("searchResults")
        self.lst.setMaximumHeight(100)
        self.lst.setVisible(False)
        self.lst.itemClicked.connect(self._on_pick)
        v.addWidget(self.lst)

        self.lbl_info = QLabel("")
        self.lbl_info.setObjectName("hintLabel")
        v.addWidget(self.lbl_info)

    def _on_text(self, text: str):
        self._book = None
        self.lbl_info.setText("")
        if len(text) < 2:
            self.lst.setVisible(False)
            return
        results = search_books(text)
        self.lst.clear()
        if not results:
            item = QListWidgetItem("Tidak ditemukan")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.lst.addItem(item)
        else:
            for b in results[:20]:
                tersedia = b.get("jumlah_tersedia", 0)
                label = f"{b['judul']}  [{b['kode_buku']}]  — {tersedia} tersedia"
                item = QListWidgetItem(label)
                item.setData(Qt.ItemDataRole.UserRole, b)
                if tersedia == 0:
                    item.setForeground(QColor("#C0392B"))
                self.lst.addItem(item)
        self.lst.setVisible(True)

    def _on_pick(self, item: QListWidgetItem):
        b = item.data(Qt.ItemDataRole.UserRole)
        if not b:
            return
        self.select_book(b)

    def select_book(self, b: dict):
        """Pilih buku langsung dari dict (dipakai juga oleh hasil scan barcode/QR)."""
        self._book = b
        self.inp.setText(f"{b['judul']}  [{b['kode_buku']}]")
        tersedia = b.get("jumlah_tersedia", 0)
        status_txt = f"✓ {tersedia} eksemplar tersedia" if tersedia > 0 else "✗ Stok habis"
        self.lbl_info.setText(status_txt)
        self.lst.setVisible(False)
        self.book_selected.emit(b)

    def get_book(self) -> Optional[dict]:
        return self._book

    def clear(self):
        self.inp.clear()
        self.lst.clear()
        self.lst.setVisible(False)
        self.lbl_info.setText("")
        self._book = None


# ══════════════════════════════════════════════════════════════════════════════
# Panel 1: Pinjam Buku
# ══════════════════════════════════════════════════════════════════════════════

class PinjamPanel(QWidget):
    status_message = Signal(str, str)   # (pesan, level)
    refresh_needed = Signal()

    def __init__(self):
        super().__init__()
        self._member: Optional[dict] = None
        self._book:   Optional[dict] = None
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(16)
        root.setContentsMargins(20, 20, 20, 20)

        root.addWidget(_section_label("Peminjaman Buku"))

        # Kartu form
        card = QWidget()
        card.setObjectName("analyticsCard")
        cv = QFormLayout(card)
        cv.setSpacing(14)
        cv.setContentsMargins(20, 20, 20, 20)
        cv.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        # Anggota
        self._member_search = MemberSearchWidget()
        self._member_search.member_selected.connect(self._on_member_selected)
        cv.addRow("Anggota :", self._member_search)

        # Buku
        self._book_search = BookSearchWidget()
        self._book_search.book_selected.connect(self._on_book_selected)
        cv.addRow("Buku :", self._book_search)

        # Durasi pinjam
        self._spn_durasi = QSpinBox()
        self._spn_durasi.setObjectName("configInput")
        self._spn_durasi.setRange(1, 60)
        self._spn_durasi.setValue(get_durasi_pinjam())
        self._spn_durasi.setSuffix(" hari")
        self._spn_durasi.setMaximumWidth(120)
        cv.addRow("Durasi :", self._spn_durasi)

        # Petugas
        self._inp_petugas = QLineEdit()
        self._inp_petugas.setObjectName("configInput")
        self._inp_petugas.setPlaceholderText("Nama petugas (opsional)")
        cv.addRow("Petugas :", self._inp_petugas)

        # Catatan
        self._inp_catatan = QLineEdit()
        self._inp_catatan.setObjectName("configInput")
        self._inp_catatan.setPlaceholderText("Catatan tambahan (opsional)")
        cv.addRow("Catatan :", self._inp_catatan)

        root.addWidget(card)

        # Preview info
        self._preview = QWidget()
        self._preview.setObjectName("analyticsCard")
        pv = QVBoxLayout(self._preview)
        pv.setContentsMargins(16, 12, 16, 12)
        self._lbl_preview = QLabel("Pilih anggota dan buku untuk melanjutkan.")
        self._lbl_preview.setObjectName("analyticsInfo")
        self._lbl_preview.setWordWrap(True)
        pv.addWidget(self._lbl_preview)
        self._preview.setVisible(False)
        root.addWidget(self._preview)

        # Tombol
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self._btn_reset = QPushButton("Reset")
        self._btn_reset.setObjectName("btnCancel")
        self._btn_reset.clicked.connect(self._reset)
        self._btn_pinjam = QPushButton("✓  Pinjamkan Buku")
        self._btn_pinjam.setObjectName("btnPrimary")
        self._btn_pinjam.clicked.connect(self._on_pinjam)
        btn_row.addWidget(self._btn_reset)
        btn_row.addWidget(self._btn_pinjam)
        root.addLayout(btn_row)

        root.addStretch()

    def _on_member_selected(self, m: dict):
        self._member = m
        self._update_preview()

    def _on_book_selected(self, b: dict):
        self._book = b
        self._update_preview()

    def _update_preview(self):
        if not self._member and not self._book:
            self._preview.setVisible(False)
            return

        lines = []
        if self._member:
            lines.append(f"<b>Anggota :</b> {self._member['Nama']} ({self._member['ID Barcode']})")
        if self._book:
            lines.append(f"<b>Buku    :</b> {self._book['judul']} [{self._book['kode_buku']}]")
            lines.append(f"<b>Stok    :</b> {self._book.get('jumlah_tersedia', 0)} tersedia")
            due = date.today() + timedelta(days=self._spn_durasi.value())
            lines.append(f"<b>Kembali :</b> {due.strftime('%d %B %Y')}")

        self._lbl_preview.setText("<br>".join(lines))
        self._preview.setVisible(True)

    def _on_pinjam(self):
        if not self._member:
            QMessageBox.warning(self, "Belum Lengkap", "Pilih anggota terlebih dahulu.")
            return
        if not self._book:
            QMessageBox.warning(self, "Belum Lengkap", "Pilih buku terlebih dahulu.")
            return

        durasi = self._spn_durasi.value()
        due    = date.today() + timedelta(days=durasi)

        konfirmasi = QMessageBox.question(
            self, "Konfirmasi Peminjaman",
            f"Pinjamkan buku berikut?\n\n"
            f"Anggota : {self._member['Nama']}\n"
            f"Buku    : {self._book['judul']}\n"
            f"Kembali : {due.strftime('%d %B %Y')} ({durasi} hari)\n",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if konfirmasi != QMessageBox.StandardButton.Yes:
            return

        ok, msg = borrow_book(
            barcode_anggota=self._member["ID Barcode"],
            nama_anggota=self._member["Nama"],
            kode_buku=self._book["kode_buku"],
            durasi_hari=durasi,
            petugas=self._inp_petugas.text().strip(),
            catatan=self._inp_catatan.text().strip(),
        )

        if ok:
            QMessageBox.information(self, "Berhasil",
                f"✓ Buku '{self._book['judul']}' berhasil dipinjamkan.\n"
                f"ID Transaksi: #{msg}\n"
                f"Wajib dikembalikan: {due.strftime('%d %B %Y')}")
            self.status_message.emit(
                f"Peminjaman #{msg}: {self._member['Nama']} → '{self._book['judul']}'", "success")
            self.refresh_needed.emit()
            self._reset()
        else:
            QMessageBox.critical(self, "Gagal", msg)
            self.status_message.emit(f"Gagal pinjam: {msg}", "error")

    def _reset(self):
        self._member = None
        self._book   = None
        self._member_search.clear()
        self._book_search.clear()
        self._inp_petugas.clear()
        self._inp_catatan.clear()
        self._preview.setVisible(False)

    # ── Scan barcode/QR (dari kamera global MainWindow) ─────────────────────────

    def handle_scan(self, code: str) -> None:
        """
        Terima satu kode hasil scan (Code128 label buku ATAU QR kartu anggota).
        Urutan scan bebas — dicocokkan dulu ke anggota, baru ke buku, mengisi
        field mana pun yang masih kosong. Tidak menimpa field yang sudah terisi.
        """
        code = code.strip()
        if not code:
            return

        if self._member is None:
            member = find_by_barcode(code)
            if member:
                self._member_search.select_member(member)
                self.status_message.emit(f"✓ Anggota terdeteksi dari scan: {member['Nama']}", "success")
                return

        if self._book is None:
            book = get_book_by_kode(code)
            if book:
                self._book_search.select_book(book)
                self.status_message.emit(f"✓ Buku terdeteksi dari scan: {book['judul']}", "success")
                return

        if self._member is not None and self._book is not None:
            self.status_message.emit("Anggota & buku sudah terisi — tekan Reset untuk scan transaksi baru.", "warning")
        else:
            self.status_message.emit(f"Kode '{code}' tidak dikenali (bukan anggota/buku terdaftar).", "warning")


# ══════════════════════════════════════════════════════════════════════════════
# Panel 2: Kembalikan Buku
# ══════════════════════════════════════════════════════════════════════════════

class KembalikanPanel(QWidget):
    status_message = Signal(str, str)
    refresh_needed = Signal()

    def __init__(self):
        super().__init__()
        self._loan: Optional[dict] = None
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(14)
        root.setContentsMargins(20, 20, 20, 20)

        root.addWidget(_section_label("Pengembalian Buku"))

        # Cari transaksi
        card_cari = QWidget()
        card_cari.setObjectName("analyticsCard")
        cv = QFormLayout(card_cari)
        cv.setSpacing(12)
        cv.setContentsMargins(20, 16, 20, 16)
        cv.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        # Search by nama anggota / ID / kode buku
        self._inp_cari = QLineEdit()
        self._inp_cari.setObjectName("searchInput")
        self._inp_cari.setPlaceholderText("Nama anggota, ID barcode, atau kode/judul buku…")
        self._inp_cari.textChanged.connect(self._on_search)
        cv.addRow("Cari :", self._inp_cari)

        self._tbl_cari = _make_table(
            ["ID", "Anggota", "Judul Buku", "Tgl Pinjam", "Jatuh Tempo", "Status"],
            stretch_col=2,
        )
        self._tbl_cari.setMaximumHeight(200)
        self._tbl_cari.setColumnWidth(0, 40)
        self._tbl_cari.setColumnWidth(3, 90)
        self._tbl_cari.setColumnWidth(4, 90)
        self._tbl_cari.setColumnWidth(5, 90)
        self._tbl_cari.itemSelectionChanged.connect(self._on_row_selected)
        cv.addRow("Hasil :", self._tbl_cari)

        root.addWidget(card_cari)

        # Detail transaksi yang dipilih
        self._card_detail = QWidget()
        self._card_detail.setObjectName("analyticsCard")
        dv = QVBoxLayout(self._card_detail)
        dv.setContentsMargins(16, 14, 16, 14)
        dv.setSpacing(8)
        self._lbl_detail = QLabel("Pilih transaksi dari hasil pencarian.")
        self._lbl_detail.setObjectName("analyticsInfo")
        self._lbl_detail.setWordWrap(True)
        dv.addWidget(self._lbl_detail)

        self._lbl_denda = QLabel("")
        self._lbl_denda.setObjectName("statCardValue")
        dv.addWidget(self._lbl_denda)

        inp_catatan_row = QHBoxLayout()
        inp_catatan_row.addWidget(QLabel("Catatan:"))
        self._inp_catatan = QLineEdit()
        self._inp_catatan.setObjectName("configInput")
        self._inp_catatan.setPlaceholderText("Opsional")
        inp_catatan_row.addWidget(self._inp_catatan, stretch=1)
        dv.addLayout(inp_catatan_row)

        self._card_detail.setVisible(False)
        root.addWidget(self._card_detail)

        # Tombol
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self._btn_kembali = QPushButton("✓  Konfirmasi Pengembalian")
        self._btn_kembali.setObjectName("btnPrimary")
        self._btn_kembali.setEnabled(False)
        self._btn_kembali.clicked.connect(self._on_kembali)
        btn_row.addWidget(self._btn_kembali)
        root.addLayout(btn_row)

        root.addStretch()

        # Load awal: semua yang sedang dipinjam
        self._load_active()

    # ── Search ────────────────────────────────────────────────────────────────

    def _on_search(self, text: str):
        if len(text) < 2:
            self._load_active()
            return
        loans = search_loans(text, status_filter="dipinjam")
        self._fill_cari(loans)

    def handle_scan(self, code: str) -> None:
        """Terima kode hasil scan (barcode buku atau QR kartu anggota) dan
        cari transaksi peminjaman aktif yang cocok. Auto-pilih jika hasilnya
        persis satu baris, supaya alur scan → konfirmasi jadi satu langkah."""
        code = code.strip()
        if not code:
            return
        self._inp_cari.setText(code)   # textChanged akan memicu _on_search()
        if self._tbl_cari.rowCount() == 1:
            self._tbl_cari.selectRow(0)
        elif self._tbl_cari.rowCount() == 0:
            self.status_message.emit(f"Kode '{code}' tidak cocok dengan transaksi aktif mana pun.", "warning")

    def _load_active(self):
        loans = get_active_loans()
        self._fill_cari(loans)

    def _fill_cari(self, loans: list[dict]):
        today = date.today()
        self._tbl_cari.setRowCount(len(loans))
        overdue_color = QColor("#FFF0ED")

        for row, loan in enumerate(loans):
            due = date.fromisoformat(loan["tanggal_kembali_rencana"])
            terlambat = max(0, (today - due).days)
            status_txt = f"⚠ +{terlambat}h" if terlambat > 0 else "Tepat waktu"
            color = overdue_color if terlambat > 0 else None

            _set_row(self._tbl_cari, row, [
                loan["id"],
                loan["nama_anggota"],
                loan["judul_buku"],
                loan["tanggal_pinjam"],
                loan["tanggal_kembali_rencana"],
                status_txt,
            ], color)
            # Simpan loan_id di UserRole kolom 0
            self._tbl_cari.item(row, 0).setData(
                Qt.ItemDataRole.UserRole, loan["id"])

    def _on_row_selected(self):
        rows = self._tbl_cari.selectionModel().selectedRows()
        if not rows:
            self._loan = None
            self._card_detail.setVisible(False)
            self._btn_kembali.setEnabled(False)
            return

        loan_id = self._tbl_cari.item(rows[0].row(), 0).data(Qt.ItemDataRole.UserRole)
        self._loan = get_loan_by_id(loan_id)
        if not self._loan:
            return

        today = date.today()
        due   = date.fromisoformat(self._loan["tanggal_kembali_rencana"])
        terlambat = max(0, (today - due).days)
        denda     = terlambat * get_denda_per_hari()

        detail_lines = [
            f"<b>ID Transaksi :</b> #{self._loan['id']}",
            f"<b>Anggota      :</b> {self._loan['nama_anggota']} ({self._loan['barcode_anggota']})",
            f"<b>Buku         :</b> {self._loan['judul_buku']} [{self._loan['kode_buku']}]",
            f"<b>Dipinjam     :</b> {self._loan['tanggal_pinjam']}",
            f"<b>Jatuh Tempo  :</b> {self._loan['tanggal_kembali_rencana']}",
        ]
        self._lbl_detail.setText("<br>".join(detail_lines))

        if denda > 0:
            self._lbl_denda.setText(f"⚠ Terlambat {terlambat} hari — Denda: Rp {denda:,}")
            self._lbl_denda.setStyleSheet("color: #C0392B; font-weight: bold;")
        else:
            self._lbl_denda.setText("✓ Tidak ada denda (tepat waktu)")
            self._lbl_denda.setStyleSheet("color: #27AE60; font-weight: bold;")

        self._card_detail.setVisible(True)
        self._btn_kembali.setEnabled(True)

    # ── Konfirmasi pengembalian ────────────────────────────────────────────────

    def _on_kembali(self):
        if not self._loan:
            return

        today = date.today()
        due   = date.fromisoformat(self._loan["tanggal_kembali_rencana"])
        terlambat = max(0, (today - due).days)
        denda     = terlambat * get_denda_per_hari()

        pesan_konfirm = (
            f"Konfirmasi pengembalian buku:\n\n"
            f"Buku    : {self._loan['judul_buku']}\n"
            f"Anggota : {self._loan['nama_anggota']}\n"
        )
        if denda > 0:
            pesan_konfirm += f"\n⚠ Denda keterlambatan: Rp {denda:,}\n({terlambat} hari)"
        else:
            pesan_konfirm += "\n✓ Tidak ada denda."

        reply = QMessageBox.question(
            self, "Konfirmasi Pengembalian", pesan_konfirm,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        ok, pesan, denda_aktual = return_book(
            self._loan["id"],
            catatan=self._inp_catatan.text().strip(),
        )

        if ok:
            QMessageBox.information(self, "Berhasil", pesan)
            self.status_message.emit(
                f"Pengembalian #{self._loan['id']}: {self._loan['nama_anggota']}"
                + (f" — denda Rp {denda_aktual:,}" if denda_aktual else ""), "success")
            self.refresh_needed.emit()
            self._loan = None
            self._card_detail.setVisible(False)
            self._btn_kembali.setEnabled(False)
            self._inp_catatan.clear()
            self._load_active()
        else:
            QMessageBox.critical(self, "Gagal", pesan)
            self.status_message.emit(f"Gagal kembalikan: {pesan}", "error")


# ══════════════════════════════════════════════════════════════════════════════
# Panel 3: Sedang Dipinjam
# ══════════════════════════════════════════════════════════════════════════════

class AktifPanel(QWidget):
    status_message = Signal(str, str)
    refresh_needed = Signal()

    def __init__(self):
        super().__init__()
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(12)
        root.setContentsMargins(16, 16, 16, 16)

        root.addWidget(_section_label("Buku Sedang Dipinjam"))

        info = QLabel(
            "Baris merah = sudah melewati tanggal jatuh tempo.\n"
            f"Denda: Rp {get_denda_per_hari():,} per hari keterlambatan."
        )
        info.setObjectName("analyticsInfo")
        root.addWidget(info)

        self._tbl = _make_table(
            ["ID", "Anggota", "ID Barcode", "Judul Buku", "Tgl Pinjam", "Jatuh Tempo", "Keterlambatan"],
            stretch_col=3,
        )
        self._tbl.setColumnWidth(0, 40)
        self._tbl.setColumnWidth(2, 110)
        self._tbl.setColumnWidth(4, 90)
        self._tbl.setColumnWidth(5, 90)
        self._tbl.setColumnWidth(6, 110)
        root.addWidget(self._tbl, stretch=1)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_refresh = QPushButton("↺  Refresh")
        btn_refresh.setObjectName("btnSecondary")
        btn_refresh.clicked.connect(self.load_data)
        btn_row.addWidget(btn_refresh)
        root.addLayout(btn_row)

    def load_data(self):
        loans = get_active_loans()
        today = date.today()
        overdue_color = QColor("#FFF0ED")

        self._tbl.setRowCount(len(loans))
        for row, loan in enumerate(loans):
            due = date.fromisoformat(loan["tanggal_kembali_rencana"])
            terlambat = max(0, (today - due).days)
            ket = f"⚠ {terlambat} hari (Rp {terlambat*get_denda_per_hari():,})" if terlambat > 0 else "✓ Tepat waktu"
            color = overdue_color if terlambat > 0 else None

            _set_row(self._tbl, row, [
                loan["id"],
                loan["nama_anggota"],
                loan["barcode_anggota"],
                loan["judul_buku"],
                loan["tanggal_pinjam"],
                loan["tanggal_kembali_rencana"],
                ket,
            ], color)


# ══════════════════════════════════════════════════════════════════════════════
# Panel 4: Riwayat
# ══════════════════════════════════════════════════════════════════════════════

class RiwayatPanel(QWidget):
    def __init__(self):
        super().__init__()
        self._build_ui()
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(350)
        self._search_timer.timeout.connect(self._do_search)

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(10)
        root.setContentsMargins(16, 16, 16, 16)

        # Filter bar
        filter_row = QHBoxLayout()
        self._inp_search = QLineEdit()
        self._inp_search.setObjectName("searchInput")
        self._inp_search.setPlaceholderText("Cari nama, ID, judul buku…")
        self._inp_search.textChanged.connect(lambda: self._search_timer.start())

        self._cmb_status = QComboBox()
        self._cmb_status.setObjectName("configCombo")
        for label, val in [("Semua Status", "semua"), ("Dipinjam", "dipinjam"),
                            ("Dikembalikan", "dikembalikan"), ("Terlambat", "terlambat")]:
            self._cmb_status.addItem(label, val)
        self._cmb_status.currentIndexChanged.connect(self._do_search)

        filter_row.addWidget(QLabel("Cari:"))
        filter_row.addWidget(self._inp_search, stretch=1)
        filter_row.addWidget(QLabel("Status:"))
        filter_row.addWidget(self._cmb_status)
        root.addLayout(filter_row)

        self._tbl = _make_table(
            ["ID", "Anggota", "Judul Buku", "Tgl Pinjam", "Jatuh Tempo", "Tgl Kembali", "Status", "Denda"],
            stretch_col=2,
        )
        self._tbl.setColumnWidth(0, 40)
        self._tbl.setColumnWidth(3, 90)
        self._tbl.setColumnWidth(4, 90)
        self._tbl.setColumnWidth(5, 90)
        self._tbl.setColumnWidth(6, 90)
        self._tbl.setColumnWidth(7, 90)
        root.addWidget(self._tbl, stretch=1)

        self._lbl_count = QLabel("")
        self._lbl_count.setObjectName("analyticsCountLabel")
        root.addWidget(self._lbl_count)

        self._do_search()

    def _do_search(self):
        query  = self._inp_search.text().strip()
        status = self._cmb_status.currentData()
        loans  = search_loans(query, status)

        self._tbl.setRowCount(len(loans))
        today = date.today()

        for row, loan in enumerate(loans):
            tgl_kembali = loan.get("tanggal_kembali_aktual") or "—"
            denda_str   = f"Rp {loan['denda']:,}" if loan["denda"] else "—"
            status_str  = loan["status"].capitalize()

            color = None
            if loan["status"] == "terlambat":
                color = QColor("#FFF0ED")
            elif loan["status"] == "dipinjam":
                due = date.fromisoformat(loan["tanggal_kembali_rencana"])
                if today > due:
                    color = QColor("#FFF0ED")

            _set_row(self._tbl, row, [
                loan["id"],
                loan["nama_anggota"],
                loan["judul_buku"],
                loan["tanggal_pinjam"],
                loan["tanggal_kembali_rencana"],
                tgl_kembali,
                status_str,
                denda_str,
            ], color)

        self._lbl_count.setText(f"{len(loans)} transaksi ditampilkan")


# ══════════════════════════════════════════════════════════════════════════════
# Tab utama: LoanTab
# ══════════════════════════════════════════════════════════════════════════════

_PANELS = [
    ("pinjam",    "Pinjam Buku"),
    ("kembali",   "Kembalikan"),
    ("aktif",     "Sedang Dipinjam"),
    ("riwayat",   "Riwayat"),
]


class LoanTab(QWidget):
    """
    Tab Peminjaman — dipasang sebagai tab ke-5 di MainWindow.

    Cara integrasi di main_window.py:
        from gui.loan_tab import LoanTab
        self._loan_tab = LoanTab()
        self._tabs.addTab(self._loan_tab, "📖  Peminjaman")
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._sb_buttons: dict[str, QPushButton] = {}
        self._build_ui()
        self._refresh_stats()

    # ══════════════════════════════════════════════════════════════════════════
    # UI
    # ══════════════════════════════════════════════════════════════════════════

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Sidebar ───────────────────────────────────────────────────────────
        sidebar = QWidget()
        sidebar.setObjectName("analyticsSidebar")
        sidebar.setFixedWidth(168)
        sv = QVBoxLayout(sidebar)
        sv.setContentsMargins(10, 16, 10, 16)
        sv.setSpacing(4)

        lbl_title = QLabel("PEMINJAMAN")
        lbl_title.setObjectName("sidebarTitle")
        sv.addWidget(lbl_title)
        sv.addSpacing(8)

        for key, label in _PANELS:
            btn = QPushButton(label)
            btn.setObjectName("sidebarBtn")
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, k=key: self._switch_panel(k))
            sv.addWidget(btn)
            self._sb_buttons[key] = btn

        sv.addSpacing(12)

        # Divider + stat cards di sidebar
        div = QFrame()
        div.setFrameShape(QFrame.Shape.HLine)
        div.setObjectName("sidebarDivider")
        sv.addWidget(div)
        sv.addSpacing(8)

        self._lbl_aktif    = self._make_sidebar_stat("0", "Sedang dipinjam")
        self._lbl_terlambat = self._make_sidebar_stat("0", "Terlambat")
        self._lbl_denda    = self._make_sidebar_stat("Rp 0", "Total denda")
        sv.addWidget(self._lbl_aktif)
        sv.addWidget(self._lbl_terlambat)
        sv.addWidget(self._lbl_denda)
        sv.addStretch()

        root.addWidget(sidebar)

        # ── Area kanan ────────────────────────────────────────────────────────
        right = QWidget()
        right.setObjectName("analyticsRight")
        rv = QVBoxLayout(right)
        rv.setContentsMargins(0, 0, 0, 0)
        rv.setSpacing(0)

        # Panel stack
        self._stack = QStackedWidget()
        self._stack.setObjectName("analyticsStack")

        self._panel_pinjam   = PinjamPanel()
        self._panel_kembali  = KembalikanPanel()
        self._panel_aktif    = AktifPanel()
        self._panel_riwayat  = RiwayatPanel()

        for panel in [self._panel_pinjam, self._panel_kembali,
                      self._panel_aktif, self._panel_riwayat]:
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QFrame.Shape.NoFrame)
            scroll.setObjectName("analyticsScroll")
            scroll.setWidget(panel)
            self._stack.addWidget(scroll)

        # Sambungkan signal dari panel ke log + refresh
        for panel in [self._panel_pinjam, self._panel_kembali, self._panel_aktif]:
            if hasattr(panel, "status_message"):
                panel.status_message.connect(self._log)
            if hasattr(panel, "refresh_needed"):
                panel.refresh_needed.connect(self._on_refresh_needed)

        rv.addWidget(self._stack, stretch=1)

        # Log bar bawah
        rv.addWidget(self._make_log_bar())
        root.addWidget(right, stretch=1)

        # Set panel default
        self._switch_panel("pinjam")

    def _make_sidebar_stat(self, value: str, label: str) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(4, 4, 4, 0)
        v.setSpacing(0)
        val_lbl = QLabel(value)
        val_lbl.setObjectName("statCardValue")
        val_lbl.setStyleSheet("font-size: 16px; font-weight: bold;")
        lbl_lbl = QLabel(label)
        lbl_lbl.setObjectName("statCardLabel")
        lbl_lbl.setStyleSheet("font-size: 10px;")
        v.addWidget(val_lbl)
        v.addWidget(lbl_lbl)
        w._val = val_lbl   # type: ignore[attr-defined]
        return w

    def _make_log_bar(self) -> QWidget:
        bar = QWidget()
        bar.setObjectName("analyticsLogBar")
        bar.setFixedHeight(36)
        h = QHBoxLayout(bar)
        h.setContentsMargins(14, 4, 14, 4)
        self._log_lbl = QLabel("Siap")
        self._log_lbl.setObjectName("analyticsLogText")
        h.addWidget(self._log_lbl)
        return bar

    # ══════════════════════════════════════════════════════════════════════════
    # Aksi
    # ══════════════════════════════════════════════════════════════════════════

    def _switch_panel(self, key: str):
        for k, btn in self._sb_buttons.items():
            btn.setChecked(k == key)
        idx = [p[0] for p in _PANELS].index(key)
        self._stack.setCurrentIndex(idx)

        # Auto-refresh panel aktif saat dibuka
        if key == "aktif":
            self._panel_aktif.load_data()
        elif key == "riwayat":
            self._panel_riwayat._do_search()

    def handle_scanned_code(self, code: str) -> None:
        """
        Entry point dipanggil MainWindow saat kamera global mendeteksi
        barcode/QR SELAGI tab Peminjaman sedang aktif. Diteruskan ke panel
        yang sedang ditampilkan (Pinjam atau Kembalikan); diabaikan kalau
        panel lain (Aktif/Riwayat) yang sedang dibuka.
        """
        idx = self._stack.currentIndex()
        if idx == 0:
            self._panel_pinjam.handle_scan(code)
        elif idx == 1:
            self._panel_kembali.handle_scan(code)
        else:
            self._log(f"Scan '{code}' diabaikan — buka panel Pinjam/Kembalikan dulu.", "warning")

    def _on_refresh_needed(self):
        self._refresh_stats()
        # Refresh panel aktif jika sedang ditampilkan
        if self._stack.currentIndex() == 2:
            self._panel_aktif.load_data()
        # Refresh kembalikan juga
        self._panel_kembali._load_active()

    def _refresh_stats(self):
        stats = get_loan_stats()
        self._lbl_aktif._val.setText(str(stats["aktif"]))           # type: ignore
        self._lbl_terlambat._val.setText(str(stats["terlambat"]))   # type: ignore
        self._lbl_denda._val.setText(f"Rp {stats['total_denda']:,}") # type: ignore

    def _log(self, pesan: str, level: str = "info"):
        from datetime import datetime
        prefix = {"success": "✓", "warning": "⚠", "error": "✗", "info": "i"}.get(level, "i")
        ts = datetime.now().strftime("%H:%M")
        self._log_lbl.setText(f"[{ts}] {prefix} {pesan}")