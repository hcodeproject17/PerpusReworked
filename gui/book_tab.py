"""
gui/book_tab.py — Tab Manajemen Buku PerpusReworked

Fitur:
- Tabel daftar buku + search real-time
- Tambah buku manual (form dialog)
- Edit buku yang dipilih
- Hapus buku
- Import massal dari Excel
- Auto-generate kode buku
- Filter per kategori
- Stat card ringkas (total judul, eksemplar, tersedia)
"""

from __future__ import annotations

import logging
import os
import sys
import subprocess
from typing import Optional

from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QFont
from create_book_template import generate_excel_template
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QSplitter, QComboBox, QMessageBox, QFileDialog,
    QDialog, QFormLayout, QSpinBox, QTextEdit, QFrame,
    QScrollArea, QSizePolicy, QAbstractItemView, QProgressBar,
)

from database.book_db import (
    get_all_books, search_books, add_book, update_book, delete_book,
    get_categories, get_book_stats, import_books_from_excel,
    generate_kode_buku,
)

logger = logging.getLogger(__name__)

# ── Kolom tabel utama ─────────────────────────────────────────────────────────
_COLUMNS = [
    ("Kode Buku",    "kode_buku",        120),
    ("Judul",        "judul",            260),
    ("Pengarang",    "pengarang",        160),
    ("Kategori",     "kategori",         110),
    ("Eksemplar",    "jumlah_eksemplar",  80),
    ("Tersedia",     "jumlah_tersedia",   80),
    ("Lokasi Rak",   "lokasi_rak",       100),
    ("ISBN",         "isbn",             130),
    ("Penerbit",     "penerbit",         130),
    ("Thn. Terbit",  "tahun_terbit",      90),
]


# ══════════════════════════════════════════════════════════════════════════════
# Worker thread untuk operasi berat
# ══════════════════════════════════════════════════════════════════════════════

class _LoadWorker(QThread):
    """Load daftar buku di background agar GUI tidak freeze."""
    finished = Signal(list)

    def __init__(self, query: str = "", kategori: str = ""):
        super().__init__()
        self._query    = query
        self._kategori = kategori

    def run(self):
        if self._query:
            books = search_books(self._query)
        else:
            books = get_all_books()

        if self._kategori and self._kategori != "— Semua Kategori —":
            books = [b for b in books if b.get("kategori") == self._kategori]

        self.finished.emit(books)


class _ImportWorker(QThread):
    """Import Excel di background."""
    finished = Signal(int, int, list)   # ok, err, errors

    def __init__(self, path: str):
        super().__init__()
        self._path = path

    def run(self):
        ok, err, errors = import_books_from_excel(self._path)
        self.finished.emit(ok, err, errors)


# ══════════════════════════════════════════════════════════════════════════════
# Dialog: Tambah / Edit Buku
# ══════════════════════════════════════════════════════════════════════════════

class BookFormDialog(QDialog):
    """Dialog form untuk tambah atau edit data buku."""

    def __init__(self, parent=None, book: Optional[dict] = None):
        super().__init__(parent)
        self._is_edit = book is not None
        self._book    = book or {}

        self.setWindowTitle("Edit Buku" if self._is_edit else "Tambah Buku Baru")
        self.setMinimumWidth(500)
        self.setModal(True)

        self._build_ui()
        if self._is_edit:
            self._populate(book)

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(16)
        root.setContentsMargins(24, 20, 24, 20)

        # Judul dialog
        title = QLabel("Edit Buku" if self._is_edit else "Tambah Buku Baru")
        title.setObjectName("dialogTitle")
        root.addWidget(title)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setObjectName("separator")
        root.addWidget(sep)

        # Form
        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        def _line(placeholder="") -> QLineEdit:
            w = QLineEdit()
            w.setObjectName("configInput")
            w.setPlaceholderText(placeholder)
            return w

        # Kode buku (disabled saat edit)
        kode_row = QHBoxLayout()
        self.inp_kode = _line("Contoh: BK-2026-0001")
        if self._is_edit:
            self.inp_kode.setReadOnly(True)
            self.inp_kode.setStyleSheet("color: gray;")
        else:
            btn_gen = QPushButton("Auto")
            btn_gen.setObjectName("btnBrowse")
            btn_gen.setFixedWidth(60)
            btn_gen.setToolTip("Generate kode otomatis")
            btn_gen.clicked.connect(self._auto_kode)
            kode_row.addWidget(self.inp_kode)
            kode_row.addWidget(btn_gen)
        if not self._is_edit:
            form.addRow("Kode Buku *", kode_row)
        else:
            form.addRow("Kode Buku *", self.inp_kode)

        self.inp_judul     = _line("Wajib diisi")
        self.inp_pengarang = _line("Nama pengarang / penulis")
        self.inp_isbn      = _line("13 digit ISBN")
        self.inp_kategori  = _line("Contoh: Fiksi, Sains, Sejarah…")
        self.inp_penerbit  = _line("Nama penerbit")
        self.inp_tahun     = _line("Contoh: 2023")
        self.inp_rak       = _line("Contoh: Rak A-3")
        self.inp_ket       = QTextEdit()
        self.inp_ket.setObjectName("configInput")
        self.inp_ket.setFixedHeight(60)
        self.inp_ket.setPlaceholderText("Catatan tambahan (opsional)")

        self.spn_jml = QSpinBox()
        self.spn_jml.setObjectName("configInput")
        self.spn_jml.setMinimum(1)
        self.spn_jml.setMaximum(9999)
        self.spn_jml.setValue(1)

        form.addRow("Judul *",           self.inp_judul)
        form.addRow("Pengarang",         self.inp_pengarang)
        form.addRow("ISBN",              self.inp_isbn)
        form.addRow("Kategori",          self.inp_kategori)
        form.addRow("Penerbit",          self.inp_penerbit)
        form.addRow("Tahun Terbit",      self.inp_tahun)
        form.addRow("Jumlah Eksemplar",  self.spn_jml)
        form.addRow("Lokasi Rak",        self.inp_rak)
        form.addRow("Keterangan",        self.inp_ket)

        root.addLayout(form)

        # Tombol
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_cancel = QPushButton("Batal")
        btn_cancel.setObjectName("btnCancel")
        btn_cancel.clicked.connect(self.reject)
        btn_save = QPushButton("Simpan")
        btn_save.setObjectName("btnPrimary")
        btn_save.clicked.connect(self._on_save)
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_save)
        root.addLayout(btn_row)

    def _populate(self, book: dict):
        self.inp_kode.setText(book.get("kode_buku", ""))
        self.inp_judul.setText(book.get("judul", ""))
        self.inp_pengarang.setText(book.get("pengarang", ""))
        self.inp_isbn.setText(book.get("isbn", ""))
        self.inp_kategori.setText(book.get("kategori", ""))
        self.inp_penerbit.setText(book.get("penerbit", ""))
        self.inp_tahun.setText(book.get("tahun_terbit", ""))
        self.spn_jml.setValue(book.get("jumlah_eksemplar", 1))
        self.inp_rak.setText(book.get("lokasi_rak", ""))
        self.inp_ket.setPlainText(book.get("keterangan", ""))

    def _auto_kode(self):
        kode = generate_kode_buku()
        self.inp_kode.setText(kode)

    # ── Save ──────────────────────────────────────────────────────────────────

    def _on_save(self):
        data = {
            "kode_buku"        : self.inp_kode.text(),
            "judul"            : self.inp_judul.text(),
            "pengarang"        : self.inp_pengarang.text(),
            "isbn"             : self.inp_isbn.text(),
            "kategori"         : self.inp_kategori.text(),
            "penerbit"         : self.inp_penerbit.text(),
            "tahun_terbit"     : self.inp_tahun.text(),
            "jumlah_eksemplar" : self.spn_jml.value(),
            "lokasi_rak"       : self.inp_rak.text(),
            "keterangan"       : self.inp_ket.toPlainText(),
        }

        if not data["kode_buku"].strip():
            QMessageBox.warning(self, "Validasi", "Kode Buku wajib diisi.")
            return
        if not data["judul"].strip():
            QMessageBox.warning(self, "Validasi", "Judul wajib diisi.")
            return

        if self._is_edit:
            ok, msg = update_book(data["kode_buku"], data)
        else:
            ok, msg = add_book(data)

        if ok:
            self.accept()
        else:
            QMessageBox.critical(self, "Gagal", msg)

    def get_kode(self) -> str:
        return self.inp_kode.text().strip().upper()


# ══════════════════════════════════════════════════════════════════════════════
# Tab utama Manajemen Buku
# ══════════════════════════════════════════════════════════════════════════════

class BookTab(QWidget):
    """
    Tab Manajemen Buku — dipasang sebagai tab ke-4 di MainWindow.

    Cara integrasi di main_window.py:
        from gui.book_tab import BookTab
        self.book_tab = BookTab()
        self.tabs.addTab(self.book_tab, "📚 Buku")
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._books: list[dict] = []
        self._worker: Optional[QThread] = None
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(300)   # debounce 300ms
        self._search_timer.timeout.connect(self._do_load)

        self._build_ui()
        self._do_load()

    # ══════════════════════════════════════════════════════════════════════════
    # UI Builder
    # ══════════════════════════════════════════════════════════════════════════

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Toolbar atas ──────────────────────────────────────────────────────
        toolbar = QWidget()
        toolbar.setObjectName("analyticsFilterBar")
        tb_layout = QHBoxLayout(toolbar)
        tb_layout.setContentsMargins(12, 8, 12, 8)
        tb_layout.setSpacing(8)

        # Search
        self.inp_search = QLineEdit()
        self.inp_search.setObjectName("searchInput")
        self.inp_search.setPlaceholderText("🔍  Cari judul, pengarang, kode, ISBN…")
        self.inp_search.setMinimumWidth(280)
        self.inp_search.textChanged.connect(self._on_search_changed)

        # Filter kategori
        self.cmb_kategori = QComboBox()
        self.cmb_kategori.setObjectName("configCombo")
        self.cmb_kategori.setMinimumWidth(160)
        self.cmb_kategori.addItem("— Semua Kategori —")
        self.cmb_kategori.currentTextChanged.connect(self._on_search_changed)

        # Tombol aksi
        btn_add    = QPushButton("＋  Tambah Buku")
        btn_template = QPushButton("📄 Buat Template")
        btn_import = QPushButton("📥  Import Excel")
        btn_edit   = QPushButton("✏️  Edit")
        btn_delete = QPushButton("🗑  Hapus")
        btn_refresh = QPushButton("↺  Refresh")

        btn_add.setObjectName("btnPrimary")
        btn_template.setObjectName("btnSecondary")
        btn_import.setObjectName("btnSecondary")
        btn_edit.setObjectName("btnSecondary")
        btn_delete.setObjectName("btnCancel")
        btn_refresh.setObjectName("btnSecondary")

        for btn, cb in [
            (btn_add,    self._on_add),
            (btn_template, self._on_create_template),
            (btn_import, self._on_import),
            (btn_edit,   self._on_edit),
            (btn_delete, self._on_delete),
            (btn_refresh, self._do_load),
        ]:
            btn.clicked.connect(cb)

        tb_layout.addWidget(self.inp_search)
        tb_layout.addWidget(self.cmb_kategori)
        tb_layout.addStretch()
        tb_layout.addWidget(btn_refresh)
        tb_layout.addWidget(btn_template)
        tb_layout.addWidget(btn_import)
        tb_layout.addWidget(btn_edit)
        tb_layout.addWidget(btn_delete)
        tb_layout.addWidget(btn_add)

        root.addWidget(toolbar)

        # ── Stat cards ────────────────────────────────────────────────────────
        stats_bar = QWidget()
        stats_bar.setObjectName("analyticsCard")
        stats_layout = QHBoxLayout(stats_bar)
        stats_layout.setContentsMargins(16, 8, 16, 8)
        stats_layout.setSpacing(32)

        self.lbl_total_judul     = self._make_stat("0", "Total Judul")
        self.lbl_total_eksemplar = self._make_stat("0", "Total Eksemplar")
        self.lbl_total_tersedia  = self._make_stat("0", "Tersedia / Dipinjam")

        for widget in (self.lbl_total_judul, self.lbl_total_eksemplar, self.lbl_total_tersedia):
            stats_layout.addWidget(widget)
        stats_layout.addStretch()

        root.addWidget(stats_bar)

        # ── Progress import ───────────────────────────────────────────────────
        self.import_progress = QProgressBar()
        self.import_progress.setObjectName("genProgress")
        self.import_progress.setRange(0, 0)   # indeterminate
        self.import_progress.setFixedHeight(4)
        self.import_progress.hide()
        root.addWidget(self.import_progress)

        # ── Tabel buku ────────────────────────────────────────────────────────
        self.table = QTableWidget()
        self.table.setObjectName("visitorTable")
        self.table.setColumnCount(len(_COLUMNS))
        self.table.setHorizontalHeaderLabels([c[0] for c in _COLUMNS])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)
        self.table.doubleClicked.connect(self._on_edit)

        for idx, (_, _, width) in enumerate(_COLUMNS):
            self.table.setColumnWidth(idx, width)

        root.addWidget(self.table, stretch=1)

        # ── Status bar bawah ──────────────────────────────────────────────────
        status_bar = QWidget()
        status_bar.setObjectName("analyticsLogBar")
        sb_layout = QHBoxLayout(status_bar)
        sb_layout.setContentsMargins(12, 4, 12, 4)
        self.lbl_status = QLabel("Siap")
        self.lbl_status.setObjectName("analyticsLogText")
        self.lbl_count  = QLabel("")
        self.lbl_count.setObjectName("analyticsLogText")
        sb_layout.addWidget(self.lbl_status)
        sb_layout.addStretch()
        sb_layout.addWidget(self.lbl_count)
        root.addWidget(status_bar)

    # ── Helper: stat card ─────────────────────────────────────────────────────

    def _make_stat(self, value: str, label: str) -> QWidget:
        container = QWidget()
        lay = QVBoxLayout(container)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(2)
        val_lbl = QLabel(value)
        val_lbl.setObjectName("statCardValue")
        lbl_lbl = QLabel(label)
        lbl_lbl.setObjectName("statCardLabel")
        lay.addWidget(val_lbl)
        lay.addWidget(lbl_lbl)
        # Simpan referensi ke value label
        container._value_label = val_lbl   # type: ignore[attr-defined]
        return container

    def _set_stat(self, container: QWidget, value: str):
        container._value_label.setText(value)  # type: ignore[attr-defined]

    # ══════════════════════════════════════════════════════════════════════════
    # Data loading
    # ══════════════════════════════════════════════════════════════════════════

    def _on_search_changed(self):
        self._search_timer.start()

    def _do_load(self):
        query    = self.inp_search.text().strip()
        kategori = self.cmb_kategori.currentText()

        self._worker = _LoadWorker(query, kategori)
        self._worker.finished.connect(self._on_loaded)
        self._worker.start()
        self.lbl_status.setText("Memuat data…")

    def _on_loaded(self, books: list[dict]):
        self._books = books
        self._fill_table(books)
        self._refresh_stats()
        self._refresh_kategori_combo()
        self.lbl_count.setText(f"{len(books)} buku ditampilkan")
        self.lbl_status.setText("Siap")

    def _fill_table(self, books: list[dict]):
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(books))
        for row, book in enumerate(books):
            for col, (_, key, _) in enumerate(_COLUMNS):
                val = str(book.get(key, "") or "")
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
                self.table.setItem(row, col, item)
        self.table.setSortingEnabled(True)

    def _refresh_stats(self):
        stats = get_book_stats()
        self._set_stat(self.lbl_total_judul,
                       str(stats["total_judul"]))
        self._set_stat(self.lbl_total_eksemplar,
                       str(stats["total_eksemplar"]))
        dipinjam = stats["total_eksemplar"] - stats["total_tersedia"]
        self._set_stat(self.lbl_total_tersedia,
                       f"{stats['total_tersedia']} / {dipinjam} dipinjam")

    def _refresh_kategori_combo(self):
        current = self.cmb_kategori.currentText()
        self.cmb_kategori.blockSignals(True)
        self.cmb_kategori.clear()
        self.cmb_kategori.addItem("— Semua Kategori —")
        for kat in get_categories():
            self.cmb_kategori.addItem(kat)
        idx = self.cmb_kategori.findText(current)
        if idx >= 0:
            self.cmb_kategori.setCurrentIndex(idx)
        self.cmb_kategori.blockSignals(False)

    # ══════════════════════════════════════════════════════════════════════════
    # Aksi toolbar
    # ══════════════════════════════════════════════════════════════════════════

    def _selected_book(self) -> Optional[dict]:
        """Kembalikan dict buku yang sedang dipilih di tabel, atau None."""
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return None
        row = rows[0].row()
        if row >= len(self._books):
            return None
        # Ambil kode dari tabel (sorting bisa mengacak urutan _books)
        kode_item = self.table.item(row, 0)
        if not kode_item:
            return None
        kode = kode_item.text()
        return next((b for b in self._books if b["kode_buku"] == kode), None)

    def _on_add(self):
        dlg = BookFormDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._do_load()
            self.lbl_status.setText(f"✔ Buku '{dlg.get_kode()}' berhasil ditambahkan.")

    def _on_edit(self):
        book = self._selected_book()
        if not book:
            QMessageBox.information(self, "Edit Buku", "Pilih buku yang ingin diedit terlebih dahulu.")
            return
        dlg = BookFormDialog(self, book=book)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._do_load()
            self.lbl_status.setText(f"✔ Buku '{book['kode_buku']}' berhasil diperbarui.")

    def _on_delete(self):
        book = self._selected_book()
        if not book:
            QMessageBox.information(self, "Hapus Buku", "Pilih buku yang ingin dihapus terlebih dahulu.")
            return

        reply = QMessageBox.question(
            self,
            "Konfirmasi Hapus",
            f"Hapus buku berikut?\n\n"
            f"Kode : {book['kode_buku']}\n"
            f"Judul: {book['judul']}\n\n"
            "Tindakan ini tidak dapat dibatalkan.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        ok, msg = delete_book(book["kode_buku"])
        if ok:
            self._do_load()
            self.lbl_status.setText(f"✔ Buku '{book['kode_buku']}' dihapus.")
        else:
            QMessageBox.critical(self, "Gagal", msg)

    def _on_create_template(self):
        # Minta user memilih lokasi dan nama file untuk disave
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Simpan Template Excel",
            "template_import_buku.xlsx",
            "Excel Files (*.xlsx)"
        )

        if not path:
            return # Dibatalkan oleh user

        self.lbl_status.setText("Membuat template excel...")

        # Panggil fungsi generate
        ok, err = generate_excel_template(path)

        if ok:
            self.lbl_status.setText("✔ Template Excel berhasil dibuat.")

            # Tampilkan pesan sukses dan tanyakan apakah ingin membuka lokasi file
            reply = QMessageBox.information(
                self,
                "Berhasil",
                f"Template berhasil disimpan di:\n{path}\n\nApakah Anda ingin membuka lokasi file ini?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self._reveal_in_explorer(path)
        else:
            QMessageBox.critical(self, "Gagal", f"Terjadi kesalahan saat menyimpan template:\n{err}")
            self.lbl_status.setText("✘ Gagal membuat template.")

    def _reveal_in_explorer(self, path: str):
        """Fungsi helper untuk membuka File Explorer / Finder"""
        try:
            if sys.platform == "win32":
                # Windows: Buka explorer dan otomatis pilih filenya
                path = os.path.normpath(path)
                subprocess.Popen(f'explorer /select,"{path}"')
            elif sys.platform == "darwin":
                # macOS: Buka Finder dan otomatis pilih filenya
                subprocess.Popen(["open", "-R", path])
            else:
                # Linux: Buka folder tempat file tersebut berada
                folder_path = os.path.dirname(path)
                subprocess.Popen(["xdg-open", folder_path])
        except Exception as e:
            logger.error(f"Gagal membuka explorer: {e}")
            self.lbl_status.setText("✘ Gagal membuka File Explorer.")

    def _on_import(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Pilih File Excel Buku",
            "",
            "Excel Files (*.xlsx *.xls)",
        )
        if not path:
            return

        # Tampilkan progress
        self.import_progress.show()
        self.lbl_status.setText("Mengimpor data buku dari Excel…")

        self._import_worker = _ImportWorker(path)
        self._import_worker.finished.connect(self._on_import_done)
        self._import_worker.start()

    def _on_import_done(self, ok: int, err: int, errors: list[str]):
        self.import_progress.hide()
        self._do_load()

        msg = f"Import selesai.\n\n✔ Berhasil : {ok} buku\n✘ Gagal     : {err} buku"
        if errors:
            detail = "\n".join(errors[:20])
            if len(errors) > 20:
                detail += f"\n… dan {len(errors)-20} error lainnya."
            msg += f"\n\nDetail error:\n{detail}"
            QMessageBox.warning(self, "Hasil Import", msg)
        else:
            QMessageBox.information(self, "Hasil Import", msg)

        self.lbl_status.setText(
            f"✔ Import selesai: {ok} berhasil, {err} gagal."
        )
