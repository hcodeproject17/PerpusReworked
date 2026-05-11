"""
gui/card_tab.py — Tab pembuatan kartu perpustakaan massal

Layout kolom kiri (fixed 310px) — urutan alur UX yang benar:
  ┌─────────────┐
  │ 1. SUMBER   │  Upload file Excel
  ├─────────────┤
  │ 2. KONFIGUR │  Nama sekolah, mode ID, tahun
  ├─────────────┤
  │ 3. GENERATE │  Pilih direktori output + tombol Generate
  └─────────────┘

Layout kolom kanan (stretch):
  ┌──────────────────────────────┐
  │   PREVIEW DATA ANGGOTA       │  ← atas
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

from PySide6.QtCore import Signal as pyqtSignal
from PySide6.QtCore import Qt, QThread
from PySide6.QtGui import QFont, QTextCursor
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QFileDialog,
    QProgressBar,
    QTextEdit,
    QGroupBox,
    QSpinBox,
    QComboBox,
    QSizePolicy,
    QMessageBox,
    QFrame,
)

from theme import log_colors as _log_colors

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
        source_path: str,
        school_name: str,
        year: int,
        output_dir: Optional[str] = None,
        id_column: Optional[str] = None,
    ):
        super().__init__()
        self.source_path = source_path
        self.school_name = school_name
        self.year        = year
        self.output_dir  = output_dir
        self.id_column   = id_column

    def run(self) -> None:
        try:
            from core.card_generator import run_card_generation
            result = run_card_generation(
                source_excel_path=self.source_path,
                school_name=self.school_name,
                year=self.year,
                output_dir=self.output_dir,
                id_column=self.id_column,
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
        self._source_path: Optional[str]         = None
        self._preview_data: list[dict]            = []
        self._worker: Optional[CardGenWorker]     = None
        self._result_docx_path: Optional[Path]    = None
        self._result_barcode_dir: Optional[Path]  = None
        self._output_dir: Optional[str]           = None

        self._build_ui()

    # ══════════════════════════════════════════════════════════════════════════
    # Build UI
    # ══════════════════════════════════════════════════════════════════════════

    def _build_ui(self) -> None:
        """
        Grid 2 kolom × 2 baris:
          col 0 (fixed 310px) : panel kiri (sumber → konfigurasi → generate)
          col 1 (stretch)     : atas=preview, bawah=hasil + log
        """
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

        left_col.addWidget(self._make_source_panel())
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

    # ── Panel 1: Sumber File ──────────────────────────────────────────────────

    def _make_source_panel(self) -> QGroupBox:
        grp = QGroupBox("1  ·  SUMBER DATA")
        grp.setObjectName("cardGroup")
        v = QVBoxLayout(grp)
        v.setSpacing(8)

        lbl = QLabel("File Excel berisi daftar nama.\nKolom wajib: Nama")
        lbl.setObjectName("hintText")
        lbl.setWordWrap(True)
        v.addWidget(lbl)

        row = QHBoxLayout()
        self._input_file = QLineEdit()
        self._input_file.setReadOnly(True)
        self._input_file.setPlaceholderText("Belum ada file…")
        self._input_file.setObjectName("fileInput")
        row.addWidget(self._input_file)

        btn_browse = QPushButton("Pilih")
        btn_browse.setObjectName("btnBrowse")
        btn_browse.setFixedWidth(52)
        btn_browse.clicked.connect(self._browse_source)
        row.addWidget(btn_browse)
        v.addLayout(row)

        self._btn_preview = QPushButton("👁  Preview Data")
        self._btn_preview.setObjectName("btnPreview")
        self._btn_preview.setEnabled(False)
        self._btn_preview.clicked.connect(self._load_preview)
        v.addWidget(self._btn_preview)

        return grp

    # ── Panel 2: Konfigurasi ──────────────────────────────────────────────────

    def _make_config_panel(self) -> QGroupBox:
        grp = QGroupBox("2  ·  KONFIGURASI")
        grp.setObjectName("cardGroup")
        v = QVBoxLayout(grp)
        v.setSpacing(8)

        v.addWidget(self._field_label("Nama Sekolah / Instansi:"))
        self._input_school = QLineEdit("MTs Negeri 12 Cirebon")
        self._input_school.setObjectName("configInput")
        v.addWidget(self._input_school)

        v.addWidget(self._field_label("Sumber ID Barcode:"))
        self._combo_id_mode = QComboBox()
        self._combo_id_mode.setObjectName("configCombo")
        self._combo_id_mode.addItem("Generate otomatis (YYYY-NNNN)", userData=None)
        self._combo_id_mode.setToolTip("Pilih kolom dari file sumber, atau biarkan generate otomatis")
        self._combo_id_mode.currentIndexChanged.connect(self._on_id_mode_changed)
        v.addWidget(self._combo_id_mode)

        # Baris tahun — SpinBox + label format berdampingan, tidak overflow
        self._row_year_widget = QWidget()
        ry = QVBoxLayout(self._row_year_widget)
        ry.setContentsMargins(0, 0, 0, 0)
        ry.setSpacing(4)

        ry.addWidget(self._field_label("Tahun ID Barcode:"))

        yr_row = QHBoxLayout()
        yr_row.setSpacing(8)

        self._spin_year = QSpinBox()
        self._spin_year.setRange(2000, 2099)
        self._spin_year.setValue(datetime.now().year)
        self._spin_year.setObjectName("configInput")
        self._spin_year.setFixedWidth(80)
        yr_row.addWidget(self._spin_year)

        self._lbl_id_fmt = QLabel()
        self._lbl_id_fmt.setObjectName("idFmtLabel")
        self._lbl_id_fmt.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        yr_row.addWidget(self._lbl_id_fmt, stretch=1)

        ry.addLayout(yr_row)
        self._spin_year.valueChanged.connect(self._update_id_format)
        self._update_id_format()

        v.addWidget(self._row_year_widget)

        return grp

    # ── Panel 3: Generate ─────────────────────────────────────────────────────

    def _make_generate_panel(self) -> QGroupBox:
        grp = QGroupBox("3  ·  GENERATE KARTU")
        grp.setObjectName("cardGroup")
        v = QVBoxLayout(grp)
        v.setSpacing(8)

        # Pilih direktori output
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

        # Progress bar (tersembunyi saat idle)
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

        # Tombol utama
        self._btn_generate = QPushButton("▶  Generate Kartu Massal")
        self._btn_generate.setObjectName("btnGenerate")
        self._btn_generate.setEnabled(False)
        self._btn_generate.clicked.connect(self._start_generation)
        v.addWidget(self._btn_generate)

        return grp

    # ── Panel kanan atas: Preview tabel ───────────────────────────────────────

    def _make_preview_panel(self) -> QWidget:
        container = QWidget()
        container.setObjectName("previewContainer")
        v = QVBoxLayout(container)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(6)

        hdr = QHBoxLayout()
        lbl = QLabel("PREVIEW DATA ANGGOTA")
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
        self._table_preview.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
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

        # Buka FOLDER tempat file Word berada (bukan langsung file-nya)
        self._btn_open_docx_dir = QPushButton("📁  Buka Folder Hasil")
        self._btn_open_docx_dir.setObjectName("btnOpenFile")
        self._btn_open_docx_dir.setEnabled(False)
        self._btn_open_docx_dir.setToolTip(
            "Buka folder tempat file Word (.docx) hasil generate disimpan")
        self._btn_open_docx_dir.clicked.connect(self._open_docx_folder)
        v.addWidget(self._btn_open_docx_dir)

        self._btn_open_barcode_dir = QPushButton("🖼  Folder Barcode PNG")
        self._btn_open_barcode_dir.setObjectName("btnOpenFile")
        self._btn_open_barcode_dir.setEnabled(False)
        self._btn_open_barcode_dir.setToolTip(
            "Buka folder gambar barcode PNG per anggota")
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
        self._log_console.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        v.addWidget(self._log_console, stretch=1)

        return container

    # ══════════════════════════════════════════════════════════════════════════
    # Helpers
    # ══════════════════════════════════════════════════════════════════════════

    def _field_label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("fieldLabel")
        return lbl

    def _update_id_format(self) -> None:
        y = self._spin_year.value()
        self._lbl_id_fmt.setText(f"{y}-0001, {y}-0002…")

    def _on_id_mode_changed(self, index: int) -> None:
        is_auto = self._combo_id_mode.currentData() is None
        self._row_year_widget.setVisible(is_auto)

    # ══════════════════════════════════════════════════════════════════════════
    # Aksi
    # ══════════════════════════════════════════════════════════════════════════

    def _browse_source(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Pilih File Excel Sumber", "",
            "Excel Files (*.xlsx *.xls)"
        )
        if not path:
            return
        self._source_path = path
        self._input_file.setText(Path(path).name)
        self._btn_preview.setEnabled(True)
        self._btn_generate.setEnabled(False)
        self._log(f"File dipilih: {Path(path).name}", "info")

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

    def _load_preview(self) -> None:
        if not self._source_path:
            return
        try:
            from database.excel_reader import read_source_excel
            data = read_source_excel(self._source_path)
            self._preview_data = data
            self._populate_table(data)
            self._lbl_count.setText(f"{len(data)} anggota")
            self._btn_generate.setEnabled(len(data) > 0)
            self._log(f"Preview: {len(data)} anggota ditemukan.", "success")
            self._populate_id_column_combo(list(data[0].keys()) if data else [])
        except Exception as exc:
            self._log(f"Gagal baca file: {exc}", "error")
            QMessageBox.critical(self, "Error", str(exc))

    def _populate_id_column_combo(self, headers: list[str]) -> None:
        self._combo_id_mode.blockSignals(True)
        self._combo_id_mode.clear()
        self._combo_id_mode.addItem("Generate otomatis (YYYY-NNNN)", userData=None)
        for col in headers:
            if col.lower() not in ("nama", "name"):
                self._combo_id_mode.addItem(f"Gunakan kolom: {col}", userData=col)
        self._combo_id_mode.blockSignals(False)
        self._on_id_mode_changed(0)

    def _populate_table(self, data: list[dict]) -> None:
        if not data:
            self._table_preview.clear()
            return
        headers = list(data[0].keys())
        self._table_preview.setColumnCount(len(headers))
        self._table_preview.setHorizontalHeaderLabels(headers)
        self._table_preview.setRowCount(len(data))
        for row_idx, member in enumerate(data):
            for col_idx, key in enumerate(headers):
                val  = str(member.get(key, "") or "")
                item = QTableWidgetItem(val)
                item.setTextAlignment(
                    Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
                self._table_preview.setItem(row_idx, col_idx, item)
        self._table_preview.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch)

    def _start_generation(self) -> None:
        school = self._input_school.text().strip()
        if not school:
            QMessageBox.warning(self, "Nama Kosong", "Isi nama sekolah terlebih dahulu.")
            return

        n = len(self._preview_data)
        reply = QMessageBox.question(
            self, "Konfirmasi",
            f"Proses {n} anggota baru?\nData akan ditambahkan ke anggota.xlsx.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self._btn_generate.setEnabled(False)
        self._progress_bar.setValue(0)
        self._progress_bar.setVisible(True)
        self._lbl_progress.setVisible(True)

        id_column  = self._combo_id_mode.currentData()
        mode_label = "otomatis" if id_column is None else f"kolom '{id_column}'"
        self._log(f"Mode ID: {mode_label}", "info")
        if self._output_dir:
            self._log(f"Output → {self._output_dir}", "info")

        self._worker = CardGenWorker(
            source_path=self._source_path,
            school_name=school,
            year=self._spin_year.value(),
            output_dir=self._output_dir,
            id_column=id_column,
        )
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.start()
        self._log("Memulai generate kartu…", "info")

    def _on_progress(self, stage: str, current: int, total: int) -> None:
        pct = int(current / total * 100) if total else 0
        self._progress_bar.setValue(pct)
        label = {"barcode": "Generate barcode", "docx": "Menyusun Word"}.get(stage, stage)
        self._lbl_progress.setText(f"{label}  {current}/{total}")

    def _on_finished(self, result: dict) -> None:
        self._btn_generate.setEnabled(True)
        self._progress_bar.setValue(100)
        self._lbl_progress.setVisible(False)
        self._progress_bar.setVisible(False)

        count     = result.get("count", 0)
        docx_path = result.get("docx_path")
        bc_dir    = result.get("barcode_dir")

        for w in result.get("warnings", []):
            self._log(w, "warning")
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
        """Buka folder tempat file Word hasil generate berada."""
        if not self._result_docx_path:
            QMessageBox.warning(self, "Belum Ada Output",
                                "Belum ada file yang dihasilkan.")
            return
        folder = str(Path(self._result_docx_path).parent)
        self._open_in_explorer(folder)

    def _open_barcode_dir_action(self) -> None:
        """Buka folder barcode PNG."""
        if not self._result_barcode_dir:
            QMessageBox.warning(self, "Belum Ada Output",
                                "Belum ada barcode yang dihasilkan.")
            return
        self._open_in_explorer(str(self._result_barcode_dir))

    def _open_in_explorer(self, path: str) -> None:
        """Buka folder di file manager sistem operasi."""
        if not Path(path).exists():
            QMessageBox.warning(self, "Tidak Ditemukan",
                                f"Folder tidak ditemukan:\n{path}")
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
            QMessageBox.warning(self, "Gagal",
                                f"Tidak dapat membuka folder:\n{exc}")

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