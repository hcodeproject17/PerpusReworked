"""
gui/member_tab.py — Tab Daftar Anggota (CRUD + Import) PerpusReworked

Fitur:
- Tabel daftar anggota + search real-time (nama / ID Barcode)
- Kolom tabel dinamis: selalu ID Barcode + Nama, plus kolom tambahan apa pun
  yang sudah ada di anggota.xlsx (mis. "Kelas", "NISN")
- Tambah anggota manual (ID Barcode bisa di-generate otomatis, format
  YYYY-NNNN)
- Import massal dari Excel — sumber ID Barcode bisa digenerate otomatis
  atau dari kolom yang sudah ada di file sumber (mis. NISN)
- Edit anggota terpilih (termasuk ganti ID Barcode-nya)
- Hapus anggota (satu atau beberapa sekaligus)

Cetak kartu anggota (QR Code) ada di tab terpisah (gui/card_tab.py), yang
memuat anggota yang sudah tersimpan di sini untuk dicetak/dicetak ulang.

Catatan: menghapus/mengganti ID anggota di sini tidak menghapus riwayat
kunjungan atau peminjaman lama miliknya — riwayat itu tersimpan sebagai
snapshot nama+ID di database, bukan tertaut langsung ke anggota.xlsx.
"""

from __future__ import annotations

import logging
from typing import Optional

from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTableWidget, QTableWidgetItem, QMessageBox,
    QDialog, QFormLayout, QFrame, QAbstractItemView,
    QProgressBar, QFileDialog, QComboBox,
)

from database.excel_reader import (
    load_members, search as search_members,
    add_member, update_member, delete_members_bulk,
    generate_next_member_id, extra_member_columns,
    import_members_from_excel, read_source_excel,
)
from config import EXCEL_COL_BARCODE, EXCEL_COL_NAME

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# Worker thread — load/search di background agar GUI tidak freeze
# ══════════════════════════════════════════════════════════════════════════════

class _LoadWorker(QThread):
    finished = Signal(list, str)   # (members, error_message)

    def __init__(self, query: str = ""):
        super().__init__()
        self._query = query

    def run(self):
        try:
            members = search_members(self._query) if self._query else load_members()
            self.finished.emit(members, "")
        except FileNotFoundError:
            self.finished.emit([], "")
        except ValueError as exc:
            self.finished.emit([], str(exc))


class _ImportWorker(QThread):
    """Import massal Excel di background."""
    finished = Signal(int, int, list)   # ok, err, warnings

    def __init__(self, path: str, id_column: Optional[str] = None):
        super().__init__()
        self._path = path
        self._id_column = id_column

    def run(self):
        ok, err, warnings = import_members_from_excel(self._path, id_column=self._id_column)
        self.finished.emit(ok, err, warnings)


# ══════════════════════════════════════════════════════════════════════════════
# Dialog: konfirmasi Import Excel (pilih sumber ID Barcode)
# ══════════════════════════════════════════════════════════════════════════════

class ImportMembersDialog(QDialog):
    """Dialog konfirmasi sebelum import massal: pilih sumber ID Barcode."""

    def __init__(self, parent=None, headers: Optional[list[str]] = None, preview_count: int = 0):
        super().__init__(parent)
        self._headers = headers or []
        self.setWindowTitle("Import Anggota dari Excel")
        self.setMinimumWidth(400)
        self.setModal(True)
        self._build_ui(preview_count)

    def _build_ui(self, preview_count: int) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(14)
        root.setContentsMargins(24, 20, 24, 20)

        title = QLabel("Import Anggota dari Excel")
        title.setObjectName("dialogTitle")
        root.addWidget(title)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setObjectName("separator")
        root.addWidget(sep)

        lbl_count = QLabel(f"{preview_count} anggota ditemukan di file sumber.")
        lbl_count.setObjectName("hintText")
        root.addWidget(lbl_count)

        lbl_field = QLabel("Sumber ID Barcode:")
        root.addWidget(lbl_field)

        self.combo = QComboBox()
        self.combo.setObjectName("configCombo")
        self.combo.addItem("Generate otomatis (YYYY-NNNN)", userData=None)
        for h in self._headers:
            if h.strip().lower() not in ("nama", "name"):
                self.combo.addItem(f"Gunakan kolom: {h}", userData=h)
        root.addWidget(self.combo)

        hint = QLabel(
            "Baris yang kosong di kolom ID terpilih akan tetap diberi ID otomatis "
            "(tidak dilewati). Kolom lain apa pun di file sumber (mis. Kelas, NISN) "
            "tetap ikut disimpan sebagai kolom tambahan."
        )
        hint.setObjectName("hintText")
        hint.setWordWrap(True)
        root.addWidget(hint)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_cancel = QPushButton("Batal")
        btn_cancel.setObjectName("btnCancel")
        btn_cancel.clicked.connect(self.reject)
        btn_ok = QPushButton("Import")
        btn_ok.setObjectName("btnPrimary")
        btn_ok.clicked.connect(self.accept)
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_ok)
        root.addLayout(btn_row)

    def selected_id_column(self) -> Optional[str]:
        return self.combo.currentData()


# ══════════════════════════════════════════════════════════════════════════════
# Dialog: Tambah / Edit Anggota
# ══════════════════════════════════════════════════════════════════════════════

class MemberFormDialog(QDialog):
    """Dialog form untuk tambah atau edit data anggota."""

    def __init__(self, parent=None, member: Optional[dict] = None, extra_headers=None):
        super().__init__(parent)
        self._is_edit = member is not None
        self._member  = member or {}
        self._extra_headers = extra_headers or []
        self._saved_id = ""

        self.setWindowTitle("Edit Anggota" if self._is_edit else "Tambah Anggota Baru")
        self.setMinimumWidth(440)
        self.setModal(True)

        self._build_ui()
        if self._is_edit:
            self._populate(member)

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(16)
        root.setContentsMargins(24, 20, 24, 20)

        title = QLabel("Edit Anggota" if self._is_edit else "Tambah Anggota Baru")
        title.setObjectName("dialogTitle")
        root.addWidget(title)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setObjectName("separator")
        root.addWidget(sep)

        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        def _line(placeholder: str = "") -> QLineEdit:
            w = QLineEdit()
            w.setObjectName("configInput")
            w.setPlaceholderText(placeholder)
            return w

        # ID Barcode — form baru dapat tombol "Auto" (generate ID; QR Code
        # fisiknya dicetak lewat tab Cetak Kartu); saat edit tetap bisa
        # diketik manual kalau memang perlu ganti ID.
        id_row = QHBoxLayout()
        self.inp_id = _line("Contoh: 2026-0001")
        if not self._is_edit:
            btn_gen = QPushButton("Auto")
            btn_gen.setObjectName("btnBrowse")
            btn_gen.setFixedWidth(60)
            btn_gen.setToolTip("Generate ID Barcode otomatis")
            btn_gen.clicked.connect(self._auto_id)
            id_row.addWidget(self.inp_id)
            id_row.addWidget(btn_gen)
            form.addRow("ID Barcode *", id_row)
        else:
            form.addRow("ID Barcode *", self.inp_id)

        self.inp_nama = _line("Wajib diisi")
        form.addRow("Nama *", self.inp_nama)

        # Kolom tambahan dinamis — mengikuti header yang sudah ada di anggota.xlsx
        self._extra_inputs: dict[str, QLineEdit] = {}
        for header in self._extra_headers:
            inp = _line()
            self._extra_inputs[header] = inp
            form.addRow(header, inp)

        root.addLayout(form)

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

    def _auto_id(self):
        self.inp_id.setText(generate_next_member_id())

    def _populate(self, member: dict):
        self.inp_id.setText(str(member.get(EXCEL_COL_BARCODE, "")))
        self.inp_nama.setText(str(member.get(EXCEL_COL_NAME, "")))
        for header, inp in self._extra_inputs.items():
            val = member.get(header, "")
            inp.setText("" if val is None else str(val))

    # ── Save ──────────────────────────────────────────────────────────────────

    def _on_save(self):
        barcode_id = self.inp_id.text().strip()
        nama       = self.inp_nama.text().strip()

        if not barcode_id:
            QMessageBox.warning(self, "Validasi", "ID Barcode wajib diisi.")
            return
        if not nama:
            QMessageBox.warning(self, "Validasi", "Nama wajib diisi.")
            return

        extra = {h: inp.text().strip() for h, inp in self._extra_inputs.items()}

        if self._is_edit:
            original_id = str(self._member.get(EXCEL_COL_BARCODE, ""))
            updates = {EXCEL_COL_NAME: nama, EXCEL_COL_BARCODE: barcode_id, **extra}
            ok, msg = update_member(original_id, updates)
        else:
            ok, msg, _ = add_member(nama, extra=extra, barcode_id=barcode_id)

        if ok:
            self._saved_id = barcode_id
            self.accept()
        else:
            QMessageBox.critical(self, "Gagal", msg)

    def get_barcode_id(self) -> str:
        return self._saved_id


# ══════════════════════════════════════════════════════════════════════════════
# Tab utama Daftar Anggota
# ══════════════════════════════════════════════════════════════════════════════

class MemberTab(QWidget):
    """
    Tab Daftar Anggota — dipasang di sidebar MainWindow.

    Cara integrasi di main_window.py:
        from gui.member_tab import MemberTab
        self._member_tab = MemberTab()
        self._stack.addWidget(self._member_tab)
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._members: list[dict] = []
        self._columns: list[tuple[str, str]] = []   # (label_kolom, key) — dibangun dinamis
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
        tb = QHBoxLayout(toolbar)
        tb.setContentsMargins(12, 8, 12, 8)
        tb.setSpacing(8)

        self.inp_search = QLineEdit()
        self.inp_search.setObjectName("searchInput")
        self.inp_search.setPlaceholderText("🔍  Cari nama atau ID Barcode…")
        self.inp_search.setMinimumWidth(280)
        self.inp_search.textChanged.connect(self._on_search_changed)

        btn_add     = QPushButton("＋  Tambah Anggota")
        btn_import  = QPushButton("📥  Import Excel")
        btn_edit    = QPushButton("✏️  Edit")
        btn_delete  = QPushButton("🗑  Hapus")
        btn_refresh = QPushButton("↺  Refresh")

        btn_add.setObjectName("btnPrimary")
        btn_import.setObjectName("btnSecondary")
        btn_edit.setObjectName("btnSecondary")
        btn_delete.setObjectName("btnCancel")
        btn_refresh.setObjectName("btnSecondary")

        for btn, cb in [
            (btn_add,     self._on_add),
            (btn_import,  self._on_import),
            (btn_edit,    self._on_edit),
            (btn_delete,  self._on_delete),
            (btn_refresh, self._do_load),
        ]:
            btn.clicked.connect(cb)

        tb.addWidget(self.inp_search)
        tb.addStretch()
        tb.addWidget(btn_refresh)
        tb.addWidget(btn_import)
        tb.addWidget(btn_edit)
        tb.addWidget(btn_delete)
        tb.addWidget(btn_add)
        root.addWidget(toolbar)

        # ── Stat ringkas ──────────────────────────────────────────────────────
        stats_bar = QWidget()
        stats_bar.setObjectName("analyticsCard")
        stats_layout = QHBoxLayout(stats_bar)
        stats_layout.setContentsMargins(16, 8, 16, 8)
        self.lbl_total = self._make_stat("0", "Total Anggota")
        stats_layout.addWidget(self.lbl_total)
        stats_layout.addStretch()
        root.addWidget(stats_bar)

        # ── Progress import ───────────────────────────────────────────────────
        self.import_progress = QProgressBar()
        self.import_progress.setObjectName("genProgress")
        self.import_progress.setRange(0, 0)   # indeterminate
        self.import_progress.setFixedHeight(4)
        self.import_progress.hide()
        root.addWidget(self.import_progress)

        # ── Tabel anggota ─────────────────────────────────────────────────────
        self.table = QTableWidget()
        self.table.setObjectName("visitorTable")
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.doubleClicked.connect(self._on_edit)
        root.addWidget(self.table, stretch=1)

        # ── Status bar bawah ──────────────────────────────────────────────────
        status_bar = QWidget()
        status_bar.setObjectName("analyticsLogBar")
        sb = QHBoxLayout(status_bar)
        sb.setContentsMargins(12, 4, 12, 4)
        self.lbl_status = QLabel("Siap")
        self.lbl_status.setObjectName("analyticsLogText")
        self.lbl_count = QLabel("")
        self.lbl_count.setObjectName("analyticsLogText")
        sb.addWidget(self.lbl_status)
        sb.addStretch()
        sb.addWidget(self.lbl_count)
        root.addWidget(status_bar)

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
        container._value_label = val_lbl   # type: ignore[attr-defined]
        return container

    # ══════════════════════════════════════════════════════════════════════════
    # Data loading
    # ══════════════════════════════════════════════════════════════════════════

    def _on_search_changed(self):
        self._search_timer.start()

    def _do_load(self):
        query = self.inp_search.text().strip()
        self._worker = _LoadWorker(query)
        self._worker.finished.connect(self._on_loaded)
        self._worker.start()
        self.lbl_status.setText("Memuat data…")

    def _on_loaded(self, members: list[dict], error: str):
        self._members = members
        self._rebuild_columns(members)
        self._fill_table(members)
        self.lbl_total._value_label.setText(str(len(members)))   # type: ignore[attr-defined]
        self.lbl_count.setText(f"{len(members)} anggota ditampilkan")
        self.lbl_status.setText(f"⚠ {error}" if error else "Siap")

    def _rebuild_columns(self, members: list[dict]) -> None:
        """ID Barcode + Nama selalu di depan; kolom lain (mis. Kelas, NISN)
        mengikuti union header yang muncul di data, urutan kemunculan pertama."""
        extra_keys = extra_member_columns(members)

        self._columns = [
            ("ID Barcode", EXCEL_COL_BARCODE),
            ("Nama", EXCEL_COL_NAME),
        ] + [(k, k) for k in extra_keys]

        self.table.setColumnCount(len(self._columns))
        self.table.setHorizontalHeaderLabels([c[0] for c in self._columns])

    def _fill_table(self, members: list[dict]) -> None:
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(members))
        for row, m in enumerate(members):
            for col, (_, key) in enumerate(self._columns):
                val = m.get(key, "")
                item = QTableWidgetItem("" if val is None else str(val))
                item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
                self.table.setItem(row, col, item)
        self.table.setSortingEnabled(True)

    # ══════════════════════════════════════════════════════════════════════════
    # Aksi toolbar
    # ══════════════════════════════════════════════════════════════════════════

    def _selected_member(self) -> Optional[dict]:
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return None
        row = rows[0].row()
        id_item = self.table.item(row, 0)
        if not id_item:
            return None
        barcode_id = id_item.text()
        return next(
            (m for m in self._members if str(m.get(EXCEL_COL_BARCODE, "")) == barcode_id),
            None,
        )

    def _extra_headers(self) -> list[str]:
        return [k for (_, k) in self._columns if k not in (EXCEL_COL_BARCODE, EXCEL_COL_NAME)]

    def _on_import(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Pilih File Excel Anggota Baru",
            "",
            "Excel Files (*.xlsx *.xls)",
        )
        if not path:
            return

        try:
            preview = read_source_excel(path)
        except Exception as exc:
            QMessageBox.critical(self, "Gagal Baca File", str(exc))
            return

        if not preview:
            QMessageBox.warning(self, "Kosong",
                                "Tidak ada data anggota (kolom 'Nama') di file ini.")
            return

        headers = list(preview[0].keys())
        dlg = ImportMembersDialog(self, headers=headers, preview_count=len(preview))
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        id_column = dlg.selected_id_column()

        self.import_progress.show()
        self.lbl_status.setText("Mengimpor data anggota dari Excel…")

        self._import_worker = _ImportWorker(path, id_column=id_column)
        self._import_worker.finished.connect(self._on_import_done)
        self._import_worker.start()

    def _on_import_done(self, ok: int, err: int, warnings: list[str]):
        self.import_progress.hide()
        self._do_load()

        msg = f"Import selesai.\n\n✔ Berhasil : {ok} anggota\n✘ Dilewati  : {err} anggota"
        if warnings:
            detail = "\n".join(warnings[:20])
            if len(warnings) > 20:
                detail += f"\n… dan {len(warnings)-20} lainnya."
            msg += f"\n\nDetail:\n{detail}"
            QMessageBox.warning(self, "Hasil Import", msg)
        else:
            QMessageBox.information(self, "Hasil Import", msg)

        self.lbl_status.setText(
            f"✔ Import selesai: {ok} berhasil, {err} dilewati."
        )

    def _on_add(self):
        dlg = MemberFormDialog(self, extra_headers=self._extra_headers())
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._do_load()
            self.lbl_status.setText(f"✔ Anggota '{dlg.get_barcode_id()}' berhasil ditambahkan.")

    def _on_edit(self):
        member = self._selected_member()
        if not member:
            QMessageBox.information(self, "Edit Anggota", "Pilih anggota yang ingin diedit terlebih dahulu.")
            return
        dlg = MemberFormDialog(self, member=member, extra_headers=self._extra_headers())
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._do_load()
            self.lbl_status.setText("✔ Data anggota berhasil diperbarui.")

    def _on_delete(self):
        selected_items = self.table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Peringatan", "Pilih minimal satu anggota yang ingin dihapus.")
            return

        selected_rows = set(item.row() for item in selected_items)
        ids_to_delete = []
        for row in selected_rows:
            id_item = self.table.item(row, 0)
            if id_item:
                ids_to_delete.append(id_item.text())

        jumlah = len(ids_to_delete)
        if jumlah == 0:
            return

        reply = QMessageBox.question(
            self, "Konfirmasi Hapus",
            f"Apakah Anda yakin ingin menghapus {jumlah} anggota yang dipilih?\n\n"
            f"Tindakan ini tidak dapat dibatalkan. Riwayat kunjungan/peminjaman\n"
            f"lama anggota ini TIDAK ikut terhapus.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        ok, msg = delete_members_bulk(ids_to_delete)
        if ok:
            self._do_load()
            self.lbl_status.setText(f"✔ {jumlah} anggota berhasil dihapus.")
            QMessageBox.information(self, "Berhasil", f"{jumlah} data anggota telah dihapus.")
        else:
            QMessageBox.critical(self, "Gagal", f"Gagal menghapus data:\n{msg}")