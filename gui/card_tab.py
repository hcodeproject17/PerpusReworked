"""
gui/card_tab.py — Tab cetak kartu perpustakaan (QR Code) untuk anggota
yang sudah terdaftar

Layout kolom kiri (fixed 310px) — urutan alur UX:
  ┌─────────────┐
  │ 1. FILTER   │  Semua / filter per kolom / pilih manual
  ├─────────────┤
  │ 2. KONFIGUR │  Nama sekolah, kartu per baris
  ├─────────────┤
  │ 3. GENERATE │  Pilih direktori output + tombol Generate
  └─────────────┘

Layout kolom kanan (stretch):
  ┌──────────────────────────────┐
  │   DAFTAR ANGGOTA             │  ← atas
  ├──────────────┬───────────────┤
  │   HASIL      │   LOG PROSES  │  ← bawah
  │   OUTPUT     │               │
  └──────────────┴───────────────┘

Anggota baru didaftarkan lewat gui/member_tab.py (manual atau import Excel).
Tab ini murni memilih anggota yang sudah ada untuk dicetak/dicetak ulang
kartunya — tidak pernah menulis ke anggota.xlsx.
"""

import logging
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Signal as pyqtSignal
from PySide6.QtCore import Qt, QThread
from PySide6.QtGui import QFont, QTextCursor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QFileDialog, QProgressBar, QTextEdit,
    QGroupBox, QComboBox, QSpinBox, QLineEdit,
    QSizePolicy, QMessageBox, QAbstractItemView,
)

from theme import log_colors as _log_colors
from database.settings_db import get_nama_sekolah

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# Worker thread
# ══════════════════════════════════════════════════════════════════════════════

class CardGenWorker(QThread):
    progress = pyqtSignal(str, int, int)
    finished = pyqtSignal(dict)
    error    = pyqtSignal(str)

    def __init__(
        self,
        members: list[dict],
        school_name: str,
        cards_per_row: int,
        output_dir: Optional[str] = None,
    ):
        super().__init__()
        self.members       = members
        self.school_name   = school_name
        self.cards_per_row = cards_per_row
        self.output_dir    = output_dir

    def run(self) -> None:
        try:
            from core.card_generator import run_card_generation
            result = run_card_generation(
                members=self.members,
                school_name=self.school_name,
                cards_per_row=self.cards_per_row,
                output_dir=self.output_dir,
                on_progress=lambda stage, cur, tot: self.progress.emit(stage, cur, tot),
            )
            self.finished.emit(result)
        except Exception as exc:
            logger.error("Card generation error: %s", exc)
            self.error.emit(str(exc))


# ══════════════════════════════════════════════════════════════════════════════
# Tab widget
# ══════════════════════════════════════════════════════════════════════════════

class CardTab(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self._members_all: list[dict]             = []
        self._members_preview: list[dict]          = []
        self._worker: Optional[CardGenWorker]      = None
        self._result_docx_path: Optional[Path]     = None
        self._result_barcode_dir: Optional[Path]   = None
        self._output_dir: Optional[str]            = None

        self._build_ui()

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

        # ── Kolom kiri ────────────────────────────────────────────────────────
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

        # ── Kanan atas: preview ───────────────────────────────────────────────
        root.addWidget(self._make_preview_panel(), 0, 1)

        # ── Kanan bawah: hasil + log ──────────────────────────────────────────
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
        grp = QGroupBox("1  ·  FILTER ANGGOTA")
        grp.setObjectName("cardGroup")
        v = QVBoxLayout(grp)
        v.setSpacing(8)

        lbl = QLabel("Pilih anggota yang akan dicetak kartunya.\n"
                      "Anggota baru? Daftarkan dulu di Tab Anggota.")
        lbl.setObjectName("hintText")
        lbl.setWordWrap(True)
        v.addWidget(lbl)

        v.addWidget(self._field_label("Mode filter:"))
        self._combo_filter_mode = QComboBox()
        self._combo_filter_mode.setObjectName("configCombo")
        self._combo_filter_mode.addItem("Semua anggota",     userData="all")
        self._combo_filter_mode.addItem("Filter per kolom",  userData="filter")
        self._combo_filter_mode.addItem("Pilih manual",      userData="manual")
        self._combo_filter_mode.currentIndexChanged.connect(self._on_filter_mode_changed)
        v.addWidget(self._combo_filter_mode)

        # Filter per kolom (tampil saat mode=filter) — mis. "Kelas" = "7A"
        self._widget_filter_col = QWidget()
        vf = QVBoxLayout(self._widget_filter_col)
        vf.setContentsMargins(0, 0, 0, 0)
        vf.setSpacing(4)
        vf.addWidget(self._field_label("Kolom:"))
        self._combo_filter_column = QComboBox()
        self._combo_filter_column.setObjectName("configCombo")
        self._combo_filter_column.currentIndexChanged.connect(self._on_filter_column_changed)
        vf.addWidget(self._combo_filter_column)
        vf.addWidget(self._field_label("Nilai:"))
        self._combo_filter_value = QComboBox()
        self._combo_filter_value.setObjectName("configCombo")
        vf.addWidget(self._combo_filter_value)
        self._widget_filter_col.setVisible(False)
        v.addWidget(self._widget_filter_col)

        # Hint manual (tampil saat mode=manual)
        self._lbl_manual_hint = QLabel("Pilih baris di tabel kanan\n(Ctrl+klik untuk multi-pilih)")
        self._lbl_manual_hint.setObjectName("hintText")
        self._lbl_manual_hint.setWordWrap(True)
        self._lbl_manual_hint.setVisible(False)
        v.addWidget(self._lbl_manual_hint)

        self._btn_load = QPushButton("🔍  Muat Daftar Anggota")
        self._btn_load.setObjectName("btnPreview")
        self._btn_load.clicked.connect(self._load_preview)
        v.addWidget(self._btn_load)

        return grp

    # ── Panel 2: Konfigurasi ──────────────────────────────────────────────────

    def _make_config_panel(self) -> QGroupBox:
        grp = QGroupBox("2  ·  KONFIGURASI KARTU")
        grp.setObjectName("cardGroup")
        v = QVBoxLayout(grp)
        v.setSpacing(8)

        v.addWidget(self._field_label("Nama Sekolah / Instansi:"))
        self._input_school = QLineEdit(get_nama_sekolah())
        self._input_school.setObjectName("configInput")
        v.addWidget(self._input_school)

        v.addWidget(self._field_label("Kartu per baris (A4):"))
        self._spin_per_row = QSpinBox()
        self._spin_per_row.setRange(1, 3)
        self._spin_per_row.setValue(2)
        self._spin_per_row.setObjectName("configInput")
        self._spin_per_row.setFixedWidth(70)
        v.addWidget(self._spin_per_row)

        return grp

    # ── Panel 3: Generate ─────────────────────────────────────────────────────

    def _make_generate_panel(self) -> QGroupBox:
        grp = QGroupBox("3  ·  GENERATE KARTU")
        grp.setObjectName("cardGroup")
        v = QVBoxLayout(grp)
        v.setSpacing(8)

        v.addWidget(self._field_label("Simpan hasil ke folder:"))
        dir_row = QHBoxLayout()
        self._input_outdir = QLineEdit()
        self._input_outdir.setObjectName("fileInput")
        self._input_outdir.setPlaceholderText("Default: folder bawaan aplikasi")
        self._input_outdir.setReadOnly(True)
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

        self._btn_generate = QPushButton("▶  Cetak Kartu Terpilih")
        self._btn_generate.setObjectName("btnGenerate")
        self._btn_generate.setEnabled(False)
        self._btn_generate.clicked.connect(self._start_generation)
        v.addWidget(self._btn_generate)

        return grp

    # ── Panel kanan atas: Tabel preview anggota ───────────────────────────────

    def _make_preview_panel(self) -> QWidget:
        container = QWidget()
        container.setObjectName("previewContainer")
        v = QVBoxLayout(container)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(6)

        hdr = QHBoxLayout()
        lbl = QLabel("DAFTAR ANGGOTA")
        lbl.setObjectName("panelLabel")
        hdr.addWidget(lbl)
        hdr.addStretch()
        self._lbl_count = QLabel("0 anggota")
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

        self._btn_open_docx_dir = QPushButton("📁  Buka Folder Hasil")
        self._btn_open_docx_dir.setObjectName("btnOpenFile")
        self._btn_open_docx_dir.setEnabled(False)
        self._btn_open_docx_dir.setToolTip("Buka folder tempat file Word (.docx) hasil generate disimpan")
        self._btn_open_docx_dir.clicked.connect(self._open_docx_folder)
        v.addWidget(self._btn_open_docx_dir)

        self._btn_open_barcode_dir = QPushButton("🖼  Folder QR Code PNG")
        self._btn_open_barcode_dir.setObjectName("btnOpenFile")
        self._btn_open_barcode_dir.setEnabled(False)
        self._btn_open_barcode_dir.setToolTip("Buka folder gambar QR Code PNG per anggota")
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

    def _on_filter_mode_changed(self, index: int) -> None:
        mode = self._combo_filter_mode.currentData()
        self._widget_filter_col.setVisible(mode == "filter")
        self._lbl_manual_hint.setVisible(mode == "manual")
        # Reset tabel & tombol generate saat mode berubah
        self._members_preview = []
        self._table_preview.clearContents()
        self._table_preview.setRowCount(0)
        self._lbl_count.setText("0 anggota")
        self._btn_generate.setEnabled(False)
        is_manual = (mode == "manual")
        self._table_preview.setSelectionMode(
            QAbstractItemView.SelectionMode.MultiSelection if is_manual
            else QAbstractItemView.SelectionMode.NoSelection
        )

    def _on_filter_column_changed(self, index: int) -> None:
        """Isi ulang combo nilai berdasarkan kolom yang dipilih."""
        col = self._combo_filter_column.currentText()
        self._combo_filter_value.blockSignals(True)
        self._combo_filter_value.clear()
        if col:
            values = sorted({
                str(m.get(col, "") or "") for m in self._members_all
                if str(m.get(col, "") or "").strip()
            })
            for val in values:
                self._combo_filter_value.addItem(val)
        self._combo_filter_value.blockSignals(False)

    def _on_selection_changed(self) -> None:
        """Update tombol generate berdasarkan jumlah baris terpilih (mode manual)."""
        if self._combo_filter_mode.currentData() == "manual":
            n = len(self._table_preview.selectionModel().selectedRows())
            self._btn_generate.setEnabled(n > 0)
            self._lbl_count.setText(f"{n} anggota dipilih")

    # ══════════════════════════════════════════════════════════════════════════
    # Aksi
    # ══════════════════════════════════════════════════════════════════════════

    def _load_preview(self) -> None:
        """Muat daftar anggota sesuai filter yang dipilih."""
        try:
            from core.card_generator import fetch_members
            from database.excel_reader import extra_member_columns

            all_members = fetch_members()
            self._members_all = all_members

            # Isi combo kolom filter dari kolom tambahan yang ada di data
            current_col = self._combo_filter_column.currentText()
            self._combo_filter_column.blockSignals(True)
            self._combo_filter_column.clear()
            extra_cols = extra_member_columns(all_members)
            self._combo_filter_column.addItems(extra_cols)
            idx = self._combo_filter_column.findText(current_col)
            if idx >= 0:
                self._combo_filter_column.setCurrentIndex(idx)
            self._combo_filter_column.blockSignals(False)
            self._on_filter_column_changed(0)

            mode = self._combo_filter_mode.currentData()
            if mode == "all":
                members = all_members
            elif mode == "filter":
                col = self._combo_filter_column.currentText()
                val = self._combo_filter_value.currentText()
                members = [m for m in all_members if str(m.get(col, "") or "") == val] if col else []
            else:
                # Mode manual: muat semua dulu, user pilih dari tabel
                members = all_members

            self._members_preview = members
            self._populate_table(members)
            self._lbl_count.setText(f"{len(members)} anggota")

            if mode != "manual":
                self._btn_generate.setEnabled(len(members) > 0)

            self._log(f"Daftar anggota dimuat: {len(members)} anggota.", "success")

            if len(all_members) == 0:
                self._log("Belum ada anggota di anggota.xlsx. Tambahkan/impor anggota di Tab Anggota terlebih dahulu.", "warning")

        except Exception as exc:
            self._log(f"Gagal memuat daftar anggota: {exc}", "error")
            QMessageBox.critical(self, "Error", str(exc))

    def _populate_table(self, members: list[dict]) -> None:
        if not members:
            self._table_preview.clear()
            self._table_preview.setRowCount(0)
            return
        from config import EXCEL_COL_BARCODE, EXCEL_COL_NAME
        from database.excel_reader import extra_member_columns
        headers = [EXCEL_COL_BARCODE, EXCEL_COL_NAME] + extra_member_columns(members)
        self._table_preview.setColumnCount(len(headers))
        self._table_preview.setHorizontalHeaderLabels(headers)
        self._table_preview.setRowCount(len(members))
        for row_idx, member in enumerate(members):
            for col_idx, key in enumerate(headers):
                val  = str(member.get(key, "") or "")
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
                self._table_preview.setItem(row_idx, col_idx, item)
        self._table_preview.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

    def _browse_output_dir(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self, "Pilih Folder Output Kartu",
            self._output_dir or str(Path.home())
        )
        if not folder:
            return
        self._output_dir = folder
        self._input_outdir.setText(folder)
        self._log(f"Folder output: {folder}", "info")

    def _get_selected_members(self) -> list[dict]:
        """Kembalikan anggota yang dipilih (mode manual) atau seluruh preview."""
        mode = self._combo_filter_mode.currentData()
        if mode != "manual":
            return self._members_preview

        selected_rows = self._table_preview.selectionModel().selectedRows()
        result = []
        for idx in selected_rows:
            row = idx.row()
            if row < len(self._members_preview):
                result.append(self._members_preview[row])
        return result

    def _start_generation(self) -> None:
        school = self._input_school.text().strip()
        if not school:
            QMessageBox.warning(self, "Nama Kosong", "Isi nama sekolah terlebih dahulu.")
            return

        members = self._get_selected_members()
        n = len(members)
        if n == 0:
            QMessageBox.warning(self, "Belum Ada Pilihan",
                                "Pilih minimal satu anggota terlebih dahulu.")
            return

        reply = QMessageBox.question(
            self, "Konfirmasi",
            f"Cetak kartu untuk {n} anggota?\n\nProses ini akan membuat file .docx siap cetak.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self._btn_generate.setEnabled(False)
        self._progress_bar.setValue(0)
        self._progress_bar.setVisible(True)
        self._lbl_progress.setVisible(True)

        if self._output_dir:
            self._log(f"Output → {self._output_dir}", "info")
        self._log(f"Mulai cetak — {n} anggota.", "info")

        self._worker = CardGenWorker(
            members=members,
            school_name=school,
            cards_per_row=self._spin_per_row.value(),
            output_dir=self._output_dir,
        )
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_progress(self, stage: str, current: int, total: int) -> None:
        pct = int(current / total * 100) if total else 0
        self._progress_bar.setValue(pct)
        label = {"barcode": "Generate QR Code", "docx": "Menyusun Word"}.get(stage, stage)
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
        self._log(f"Selesai — {count} kartu dibuat.", "success")

        if docx_path:
            self._result_docx_path = docx_path
            fname = Path(docx_path).name
            self._lbl_result.setText(
                f"✓ {count} kartu selesai\n\n"
                f"📄 {fname}\n\n"
                f"Klik tombol di bawah untuk membuka folder tempat file disimpan."
            )
            self._btn_open_docx_dir.setEnabled(True)

        if bc_dir:
            self._result_barcode_dir = bc_dir
            self._btn_open_barcode_dir.setEnabled(True)

        QMessageBox.information(
            self, "Selesai",
            f"✅ {count} kartu berhasil dibuat!\n\n"
            f"Buka folder hasil untuk menemukan file Word,\n"
            f"lalu cetak dari Microsoft Word."
        )

    def _on_error(self, message: str) -> None:
        self._btn_generate.setEnabled(True)
        self._progress_bar.setVisible(False)
        self._lbl_progress.setVisible(False)
        self._log(f"ERROR: {message}", "error")
        QMessageBox.critical(self, "Error", message)

    # ── Buka folder (bukan langsung file) ─────────────────────────────────────

    def _open_docx_folder(self) -> None:
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

    # ── Log ───────────────────────────────────────────────────────────────────

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