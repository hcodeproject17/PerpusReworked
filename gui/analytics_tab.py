"""
gui/analytics_tab.py — Tab analisis data perpustakaan

Layout:
  ┌─────────────┬──────────────────────────────────────┐
  │   Sidebar   │   Panel konten (ganti sesuai pilihan) │
  │  (fixed)    │                                       │
  └─────────────┴──────────────────────────────────────┘

Panel tersedia:
  1. Ringkasan      — stat cards + bar chart hari + top 5 + distribusi jam
  2. Tren kunjungan — grafik batang harian/mingguan
  3. Top anggota    — tabel ranking lengkap
  4. Per jam        — distribusi jam visual + tabel
  5. Tidak aktif    — tabel anggota belum pernah masuk
  6. Export         — export Excel & PDF

Catatan styling:
  Tab ini TIDAK menyetel stylesheet lokal. Semua tampilan (warna, border,
  radius, dst) datang dari QSS global di theme.py — lihat bagian
  "Analytics tab: ..." di stylesheet(). objectName di widget-widget bawah
  ini harus selalu cocok dengan selector yang ada di sana. Kalau menambah
  komponen baru dengan objectName baru, tambahkan juga selector-nya di
  theme.py, jangan setStyleSheet() di sini.
"""

import logging
import os
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Signal as pyqtSignal
from PySide6.QtCore import Qt, QThread, QDate
from PySide6.QtGui import QFont, QTextCursor, QPainter, QColor, QBrush, QPen
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QDateEdit,
    QStackedWidget, QSizePolicy, QFrame, QFileDialog,
    QMessageBox, QScrollArea, QGridLayout, QSpinBox,
    QProgressBar, QTextEdit, QAbstractItemView,
)
from PySide6.QtCharts import (
    QChart, QChartView, QBarSeries, QBarSet, QBarCategoryAxis,
    QValueAxis, QLineSeries, QSplineSeries,
)

from theme import get_palette, log_colors as _log_colors
from gui.widgets import section_label as _section_label

logger = logging.getLogger(__name__)


# ── Warna dari tema aktif ─────────────────────────────────────────────────────
def _p():
    return get_palette()


# ══════════════════════════════════════════════════════════════════════════════
# Worker thread — query berat dijalankan di background
# ══════════════════════════════════════════════════════════════════════════════

class AnalyticsWorker(QThread):
    """Jalankan semua query analitik di background agar GUI tidak freeze."""
    finished = pyqtSignal(dict)
    error    = pyqtSignal(str)

    def __init__(self, start: date, end: date, panel: str):
        super().__init__()
        self.start_date = start
        self.end_date   = end
        self.panel = panel   # panel mana yang sedang ditampilkan

    def run(self):
        try:
            from database.analytics_db import (
                get_summary, get_daily_trend, get_day_of_week_distribution,
                get_hourly_distribution, get_top_visitors, get_inactive_members,
                get_weekly_trend,
            )
            data = {"panel": self.panel, "start": self.start_date, "end": self.end_date}

            if self.panel == "ringkasan":
                data["summary"]   = get_summary(self.start_date, self.end_date)
                data["dow"]       = get_day_of_week_distribution(self.start_date, self.end_date)
                data["top5"]      = get_top_visitors(self.start_date, self.end_date, limit=5)
                data["hourly"]    = get_hourly_distribution(self.start_date, self.end_date)

            elif self.panel == "tren":
                data["daily"]    = get_daily_trend(self.start_date, self.end_date)
                data["weekly"]   = get_weekly_trend(self.start_date, self.end_date)

            elif self.panel == "top":
                data["top"]      = get_top_visitors(self.start_date, self.end_date, limit=50)

            elif self.panel == "jam":
                data["hourly"]   = get_hourly_distribution(self.start_date, self.end_date)

            elif self.panel == "inactive":
                data["inactive"] = get_inactive_members()

            self.finished.emit(data)
        except Exception as exc:
            logger.error("AnalyticsWorker error: %s", exc)
            self.error.emit(str(exc))


class ExportWorker(QThread):
    """Jalankan export di background."""
    finished = pyqtSignal(bool, str)   # (success, path_or_error)

    def __init__(self, mode: str, start: date, end: date, out_path: str):
        super().__init__()
        self.mode     = mode
        self.start_date = start
        self.end_date   = end
        self.out_path = out_path

    def run(self):
        try:
            from database.analytics_db import export_to_excel, export_to_pdf
            if self.mode == "excel":
                export_to_excel(self.start_date, self.end_date, self.out_path)
            else:
                export_to_pdf(self.start_date, self.end_date, self.out_path)
            self.finished.emit(True, self.out_path)
        except Exception as exc:
            self.finished.emit(False, str(exc))


# ══════════════════════════════════════════════════════════════════════════════
# Komponen UI kecil
# ══════════════════════════════════════════════════════════════════════════════

class StatCard(QFrame):
    """Kartu statistik kecil (nilai + label)."""

    def __init__(self, label: str, value: str = "—", accent: bool = False):
        super().__init__()
        self.setObjectName("statCard")
        self.setFrameShape(QFrame.Shape.StyledPanel)

        v = QVBoxLayout(self)
        v.setContentsMargins(14, 12, 14, 12)
        v.setSpacing(4)

        self._lbl_val = QLabel(value)
        self._lbl_val.setObjectName("statCardValue" + ("Acc" if accent else ""))
        self._lbl_val.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))

        self._lbl_label = QLabel(label)
        self._lbl_label.setObjectName("statCardLabel")

        v.addWidget(self._lbl_val)
        v.addWidget(self._lbl_label)

    def set_value(self, value: str):
        self._lbl_val.setText(value)


class MiniBarChart(QWidget):
    """Bar chart sederhana berbasis QPainter (tidak butuh QtCharts).

    Digambar manual lewat paintEvent, jadi warnanya TIDAK bisa datang dari
    QSS (stylesheet tidak menjangkau custom-painted widget). Karena itu
    widget ini mengambil warna langsung dari get_palette() — baik sebagai
    default awal maupun saat set_data() dipanggil — supaya tetap ikut tema
    aktif tanpa perlu stylesheet lokal.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._data: list[dict] = []   # list {"label": str, "value": float}
        p = _p()
        self._color_primary  = f"#{p.p1}"
        self._color_accent   = f"#{p.p4}"
        self._color_bg       = f"#{p.surface}"
        self._color_text     = f"#{p.p2}"
        self.setMinimumHeight(120)

    def set_data(self, data: list[dict],
                 color_primary: str = None,
                 color_accent: str  = None):
        p = _p()
        self._color_primary = f"#{p.p1}"  if color_primary is None else color_primary
        self._color_accent  = f"#{p.p4}"  if color_accent  is None else color_accent
        self._color_bg      = f"#{p.surface}"
        self._color_text    = f"#{p.p2}"
        self._data = data
        self.update()

    def paintEvent(self, event):
        if not self._data:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        W = self.width()
        H = self.height()
        pad_left = 8
        pad_right = 8
        pad_top = 12
        pad_bottom = 24

        values = [d.get("value", d.get("avg", d.get("count", 0))) for d in self._data]
        max_val = max(values) if values else 1
        if max_val == 0:
            max_val = 1

        n = len(self._data)
        avail_w = W - pad_left - pad_right
        bar_w   = max(4, int(avail_w / n) - 2)
        gap     = (avail_w - bar_w * n) / max(n - 1, 1)

        max_idx = values.index(max(values)) if values else -1

        for i, (d, val) in enumerate(zip(self._data, values)):
            x = int(pad_left + i * (bar_w + gap))
            bar_h = int((val / max_val) * (H - pad_top - pad_bottom))
            y = H - pad_bottom - bar_h

            color = QColor(self._color_accent if i == max_idx else self._color_primary)
            painter.fillRect(x, y, bar_w, bar_h, color)

            # Label bawah
            painter.setPen(QColor(self._color_text))
            painter.setFont(QFont("Segoe UI", 8))
            lbl = str(d.get("label", d.get("hari", d.get("jam", ""))))
            painter.drawText(x - 4, H - pad_bottom + 4, bar_w + 8, 16,
                             Qt.AlignmentFlag.AlignCenter, lbl)

            # Nilai atas (hanya jika bar cukup tinggi)
            if bar_h > 16 and val > 0:
                painter.setPen(QColor("#FFFFFF"))
                painter.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
                painter.drawText(x, y + 2, bar_w, 14,
                                 Qt.AlignmentFlag.AlignCenter, str(int(val)))

        painter.end()


# ══════════════════════════════════════════════════════════════════════════════
# Panel konten
# ══════════════════════════════════════════════════════════════════════════════

def _scrollable(widget: QWidget) -> QScrollArea:
    """Bungkus widget dalam QScrollArea."""
    sa = QScrollArea()
    sa.setWidgetResizable(True)
    sa.setFrameShape(QFrame.Shape.NoFrame)
    sa.setWidget(widget)
    sa.setObjectName("analyticsScroll")
    return sa


def _make_table(cols: list[str]) -> QTableWidget:
    t = QTableWidget()
    t.setObjectName("analyticsTable")
    t.setColumnCount(len(cols))
    t.setHorizontalHeaderLabels(cols)
    t.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    t.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    t.setAlternatingRowColors(True)
    t.verticalHeader().setVisible(False)
    t.horizontalHeader().setStretchLastSection(True)
    t.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
    return t


def _fill_table(table: QTableWidget, rows: list[list]):
    table.setRowCount(len(rows))
    for ri, row in enumerate(rows):
        for ci, val in enumerate(row):
            item = QTableWidgetItem(str(val))
            item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
            table.setItem(ri, ci, item)


# ── Panel 1: Ringkasan ────────────────────────────────────────────────────────

class RingkasanPanel(QWidget):
    def __init__(self):
        super().__init__()
        root = QVBoxLayout(self)
        root.setSpacing(14)
        root.setContentsMargins(16, 16, 16, 16)

        # Stat cards
        card_row = QHBoxLayout()
        card_row.setSpacing(10)
        self._card_total   = StatCard("Total kunjungan")
        self._card_unik    = StatCard("Pengunjung unik")
        self._card_avg     = StatCard("Rata-rata / hari")
        self._card_sibuk   = StatCard("Hari tersibuk")
        self._card_inactive = StatCard("Tidak aktif", accent=True)
        for c in [self._card_total, self._card_unik, self._card_avg,
                  self._card_sibuk, self._card_inactive]:
            card_row.addWidget(c)
        root.addLayout(card_row)

        # Baris bawah: bar chart hari + top 5 + distribusi jam
        mid = QHBoxLayout()
        mid.setSpacing(10)

        # Bar chart per hari dalam minggu
        left = QWidget()
        left.setObjectName("analyticsCard")
        lv = QVBoxLayout(left)
        lv.setContentsMargins(12, 12, 12, 12)
        lv.addWidget(_section_label("Rata-rata per hari"))
        self._chart_dow = MiniBarChart()
        self._chart_dow.setMinimumHeight(140)
        lv.addWidget(self._chart_dow, stretch=1)
        mid.addWidget(left, stretch=3)

        # Top 5 anggota
        right = QWidget()
        right.setObjectName("analyticsCard")
        rv = QVBoxLayout(right)
        rv.setContentsMargins(12, 12, 12, 12)
        rv.addWidget(_section_label("Top 5 Anggota"))
        self._tbl_top5 = _make_table(["Nama", "Kunjungan"])
        self._tbl_top5.setMaximumHeight(180)
        rv.addWidget(self._tbl_top5)
        mid.addWidget(right, stretch=2)
        root.addLayout(mid)

        # Bar chart distribusi jam
        bot = QWidget()
        bot.setObjectName("analyticsCard")
        bv = QVBoxLayout(bot)
        bv.setContentsMargins(12, 12, 12, 8)
        bv.addWidget(_section_label("Distribusi kunjungan per jam"))
        self._chart_hour = MiniBarChart()
        self._chart_hour.setMinimumHeight(130)
        bv.addWidget(self._chart_hour, stretch=1)
        root.addWidget(bot)

        root.addStretch()

    def update_data(self, data: dict):
        s = data.get("summary", {})
        self._card_total.set_value(str(s.get("total_visits", 0)))
        self._card_unik.set_value(str(s.get("unique_visitors", 0)))
        self._card_avg.set_value(str(s.get("avg_per_day", 0)))
        self._card_sibuk.set_value(
            f"{s.get('busiest_day','—')}\n({s.get('busiest_count',0)}x)")
        self._card_inactive.set_value(str(
            len(data.get("inactive_count", [])) if isinstance(
                data.get("inactive_count"), list) else s.get("inactive_hint", "—")))

        dow = data.get("dow", [])
        if dow:
            self._chart_dow.set_data([
                {"label": d["hari"][:3], "value": d["avg"]} for d in dow
            ])

        top5 = data.get("top5", [])
        _fill_table(self._tbl_top5,
                    [[r["nama"], r["count"]] for r in top5])
        self._tbl_top5.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch)

        hourly = data.get("hourly", [])
        hour_display = [h for h in hourly if 6 <= h["jam"] <= 20]
        if hour_display:
            self._chart_hour.set_data([
                {"label": f"{h['jam']:02d}", "value": h["count"]}
                for h in hour_display
            ])


# ── Panel 2: Tren kunjungan ───────────────────────────────────────────────────

class TrenPanel(QWidget):
    def __init__(self):
        super().__init__()
        root = QVBoxLayout(self)
        root.setSpacing(12)
        root.setContentsMargins(16, 16, 16, 16)

        root.addWidget(_section_label("Tren kunjungan harian"))
        self._chart_daily = MiniBarChart()
        self._chart_daily.setMinimumHeight(200)
        daily_card = QWidget()
        daily_card.setObjectName("analyticsCard")
        dc = QVBoxLayout(daily_card)
        dc.setContentsMargins(12, 12, 12, 12)
        dc.addWidget(self._chart_daily)
        root.addWidget(daily_card, stretch=2)

        root.addWidget(_section_label("Tren mingguan"))
        self._chart_weekly = MiniBarChart()
        self._chart_weekly.setMinimumHeight(150)
        weekly_card = QWidget()
        weekly_card.setObjectName("analyticsCard")
        wc = QVBoxLayout(weekly_card)
        wc.setContentsMargins(12, 12, 12, 12)
        wc.addWidget(self._chart_weekly)
        root.addWidget(weekly_card, stretch=1)
        root.addStretch()

    def update_data(self, data: dict):
        daily = data.get("daily", [])
        # Tampilkan maks 60 hari agar tidak terlalu padat
        if len(daily) > 60:
            daily = daily[-60:]
        if daily:
            self._chart_daily.set_data([
                {"label": d["label"], "value": d["count"]} for d in daily
            ])

        weekly = data.get("weekly", [])
        if weekly:
            self._chart_weekly.set_data([
                {"label": w["label"], "value": w["count"]} for w in weekly
            ])


# ── Panel 3: Top anggota ──────────────────────────────────────────────────────

class TopPanel(QWidget):
    def __init__(self):
        super().__init__()
        root = QVBoxLayout(self)
        root.setSpacing(10)
        root.setContentsMargins(16, 16, 16, 16)

        root.addWidget(_section_label("Ranking anggota terbanyak berkunjung"))
        self._table = _make_table(["Rank", "Nama", "ID Barcode", "Kunjungan", "% Total"])
        self._table.setColumnWidth(0, 50)
        self._table.setColumnWidth(3, 90)
        self._table.setColumnWidth(4, 80)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        root.addWidget(self._table, stretch=1)

    def update_data(self, data: dict):
        top = data.get("top", [])
        _fill_table(self._table, [
            [r["rank"], r["nama"], r["barcode_id"],
             r["count"], f"{r['pct']}%"]
            for r in top
        ])


# ── Panel 4: Per jam ──────────────────────────────────────────────────────────

class JamPanel(QWidget):
    def __init__(self):
        super().__init__()
        root = QVBoxLayout(self)
        root.setSpacing(12)
        root.setContentsMargins(16, 16, 16, 16)

        root.addWidget(_section_label("Distribusi kunjungan per jam"))
        card = QWidget()
        card.setObjectName("analyticsCard")
        cv = QVBoxLayout(card)
        cv.setContentsMargins(12, 12, 12, 12)
        self._chart = MiniBarChart()
        self._chart.setMinimumHeight(200)
        cv.addWidget(self._chart)
        root.addWidget(card, stretch=2)

        root.addWidget(_section_label("Detail per jam"))
        self._table = _make_table(["Jam", "Jumlah Kunjungan"])
        self._table.setMaximumHeight(280)
        self._table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch)
        root.addWidget(self._table)
        root.addStretch()

    def update_data(self, data: dict):
        hourly = data.get("hourly", [])
        active = [h for h in hourly if h["count"] > 0 or 7 <= h["jam"] <= 18]
        if active:
            self._chart.set_data([
                {"label": f"{h['jam']:02d}", "value": h["count"]}
                for h in active
            ])
        _fill_table(self._table, [
            [h["label"], h["count"]] for h in hourly if h["count"] > 0
        ])


# ── Panel 5: Tidak aktif ──────────────────────────────────────────────────────

class InactivePanel(QWidget):
    def __init__(self):
        super().__init__()
        root = QVBoxLayout(self)
        root.setSpacing(10)
        root.setContentsMargins(16, 16, 16, 16)

        info = QLabel(
            "Anggota terdaftar di anggota.xlsx yang belum pernah tercatat kunjungan.\n"
            "Data ini berguna untuk evaluasi program membaca dan tindak lanjut per kelas."
        )
        info.setObjectName("analyticsInfo")
        info.setWordWrap(True)
        root.addWidget(info)

        self._lbl_count = QLabel("Memuat data...")
        self._lbl_count.setObjectName("analyticsCountLabel")
        root.addWidget(self._lbl_count)

        self._table = _make_table(["No", "Nama", "ID Barcode"])
        self._table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch)
        self._table.setColumnWidth(0, 45)
        self._table.setColumnWidth(2, 130)
        root.addWidget(self._table, stretch=1)

    def update_data(self, data: dict):
        from config import EXCEL_COL_BARCODE, EXCEL_COL_NAME
        inactive = data.get("inactive", [])
        self._lbl_count.setText(
            f"{len(inactive)} anggota belum pernah berkunjung"
            if inactive else "Semua anggota sudah pernah berkunjung ✓"
        )

        # Deteksi kolom dinamis (bisa ada Kelas, NIS, dll)
        if inactive:
            extra_keys = [k for k in inactive[0].keys()
                         if k not in (EXCEL_COL_BARCODE, EXCEL_COL_NAME)]
            all_cols = ["No", "Nama", "ID Barcode"] + extra_keys
            self._table.setColumnCount(len(all_cols))
            self._table.setHorizontalHeaderLabels(all_cols)
            self._table.horizontalHeader().setSectionResizeMode(
                1, QHeaderView.ResizeMode.Stretch)

            rows = []
            for i, m in enumerate(inactive, 1):
                row = [i, m.get(EXCEL_COL_NAME, ""), m.get(EXCEL_COL_BARCODE, "")]
                row += [str(m.get(k, "") or "") for k in extra_keys]
                rows.append(row)
            _fill_table(self._table, rows)
        else:
            self._table.setRowCount(0)


# ── Panel 6: Export ───────────────────────────────────────────────────────────

class ExportPanel(QWidget):
    log_message = pyqtSignal(str, str)   # (message, level)

    def __init__(self):
        super().__init__()
        self._start: Optional[date] = None
        self._end:   Optional[date] = None
        self._worker: Optional[ExportWorker] = None

        root = QVBoxLayout(self)
        root.setSpacing(16)
        root.setContentsMargins(16, 16, 16, 16)

        # Info
        info = QLabel(
            "Export laporan dalam rentang tanggal yang dipilih di filter atas.\n"
            "Excel berisi 6 sheet: Ringkasan, Detail, Top Anggota, Tren, Per Jam, Tidak Aktif.\n"
            "PDF berisi laporan ringkas siap cetak."
        )
        info.setObjectName("analyticsInfo")
        info.setWordWrap(True)
        root.addWidget(info)

        # Tombol export
        card = QWidget()
        card.setObjectName("analyticsCard")
        cv = QGridLayout(card)
        cv.setSpacing(12)
        cv.setContentsMargins(20, 20, 20, 20)

        icon_xlsx = QLabel("📊")
        icon_xlsx.setFont(QFont("Segoe UI", 32))
        icon_xlsx.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cv.addWidget(icon_xlsx, 0, 0)

        lbl_xlsx = QLabel("Export Excel (.xlsx)")
        lbl_xlsx.setObjectName("exportTitle")
        desc_xlsx = QLabel("Semua data dalam beberapa sheet.\nBisa diolah lebih lanjut di Excel.")
        desc_xlsx.setObjectName("analyticsInfo")
        desc_xlsx.setWordWrap(True)
        cv.addWidget(lbl_xlsx, 0, 1)
        cv.addWidget(desc_xlsx, 1, 1)

        self._btn_excel = QPushButton("📥  Export Excel")
        self._btn_excel.setObjectName("btnExportExcel")
        self._btn_excel.clicked.connect(self._export_excel)
        cv.addWidget(self._btn_excel, 0, 2, 2, 1)

        # Garis
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setObjectName("exportDivider")
        cv.addWidget(line, 2, 0, 1, 3)

        icon_pdf = QLabel("📄")
        icon_pdf.setFont(QFont("Segoe UI", 32))
        icon_pdf.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cv.addWidget(icon_pdf, 3, 0)

        lbl_pdf = QLabel("Export PDF Laporan")
        lbl_pdf.setObjectName("exportTitle")
        desc_pdf = QLabel("Laporan ringkas siap cetak.\nButuh: pip install reportlab")
        desc_pdf.setObjectName("analyticsInfo")
        desc_pdf.setWordWrap(True)
        cv.addWidget(lbl_pdf, 3, 1)
        cv.addWidget(desc_pdf, 4, 1)

        self._btn_pdf = QPushButton("🖨️  Export PDF")
        self._btn_pdf.setObjectName("btnExportPdf")
        self._btn_pdf.clicked.connect(self._export_pdf)
        cv.addWidget(self._btn_pdf, 3, 2, 2, 1)

        cv.setColumnStretch(1, 1)
        root.addWidget(card)

        # Progress
        self._progress = QProgressBar()
        self._progress.setObjectName("genProgress")
        self._progress.setRange(0, 0)   # indeterminate
        self._progress.setVisible(False)
        root.addWidget(self._progress)

        self._lbl_status = QLabel("")
        self._lbl_status.setObjectName("analyticsInfo")
        root.addWidget(self._lbl_status)

        root.addStretch()

    def set_date_range(self, start: date, end: date):
        self._start = start
        self._end   = end

    def _export_excel(self):
        if not self._start:
            QMessageBox.warning(self, "Belum Ada Filter", "Pilih rentang tanggal terlebih dahulu.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Simpan Excel", f"laporan_{self._start}_{self._end}.xlsx",
            "Excel Files (*.xlsx)")
        if not path:
            return
        self._run_export("excel", path)

    def _export_pdf(self):
        if not self._start:
            QMessageBox.warning(self, "Belum Ada Filter", "Pilih rentang tanggal terlebih dahulu.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Simpan PDF", f"laporan_{self._start}_{self._end}.pdf",
            "PDF Files (*.pdf)")
        if not path:
            return
        self._run_export("pdf", path)

    def _run_export(self, mode: str, path: str):
        self._btn_excel.setEnabled(False)
        self._btn_pdf.setEnabled(False)
        self._progress.setVisible(True)
        self._lbl_status.setText(f"Memproses export {mode.upper()}...")
        self.log_message.emit(f"Memulai export {mode.upper()}...", "info")

        self._worker = ExportWorker(mode, self._start, self._end, path)
        self._worker.finished.connect(self._on_export_done)
        self._worker.start()

    def _on_export_done(self, success: bool, path_or_err: str):
        self._btn_excel.setEnabled(True)
        self._btn_pdf.setEnabled(True)
        self._progress.setVisible(False)

        if success:
            self._lbl_status.setText(f"✓ Berhasil: {Path(path_or_err).name}")
            self.log_message.emit(f"Export berhasil: {Path(path_or_err).name}", "success")
            reply = QMessageBox.question(
                self, "Selesai",
                f"Export berhasil!\n{path_or_err}\n\nBuka file sekarang?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                os.startfile(path_or_err)
        else:
            self._lbl_status.setText(f"✗ Gagal: {path_or_err}")
            self.log_message.emit(f"Export gagal: {path_or_err}", "error")
            QMessageBox.critical(self, "Export Gagal", path_or_err)


# ══════════════════════════════════════════════════════════════════════════════
# Tab utama
# ══════════════════════════════════════════════════════════════════════════════

_PANELS = [
    ("ringkasan", "Ringkasan"),
    ("tren",      "Tren Kunjungan"),
    ("top",       "Top Anggota"),
    ("jam",       "Per Jam"),
    ("inactive",  "Tidak Aktif"),
    ("export",    "Export"),
]


class AnalyticsTab(QWidget):
    """Tab analisis data — sidebar + konten.

    Tidak memanggil setStyleSheet() sendiri — tampilan sepenuhnya
    mengikuti QSS global dari theme.stylesheet() yang di-set sekali di
    app level (lihat main.py). objectName widget di sini harus selalu
    disamakan dengan selector "Analytics tab: ..." di theme.py.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_panel = "ringkasan"
        self._worker: Optional[AnalyticsWorker] = None
        self._sb_buttons: dict[str, QPushButton] = {}

        self._build_ui()

        # Default: 30 hari terakhir
        today = date.today()
        self._date_start.setDate(QDate(today.year, today.month, today.day).addDays(-30))
        self._date_end.setDate(QDate(today.year, today.month, today.day))

        self._load_panel("ringkasan")

    # ══════════════════════════════════════════════════════════════════════════
    # Build UI
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

        lbl_title = QLabel("ANALISIS")
        lbl_title.setObjectName("sidebarTitle")
        sv.addWidget(lbl_title)
        sv.addSpacing(8)

        for key, label in _PANELS:
            if key == "export":
                # Divider sebelum export
                div = QFrame()
                div.setFrameShape(QFrame.Shape.HLine)
                div.setObjectName("sidebarDivider")
                sv.addSpacing(4)
                sv.addWidget(div)
                sv.addSpacing(4)

            btn = QPushButton(label)
            btn.setObjectName("sidebarBtn")
            btn.setCheckable(True)
            btn.clicked.connect(lambda _, k=key: self._load_panel(k))
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            sv.addWidget(btn)
            self._sb_buttons[key] = btn

        sv.addStretch()

        # Loading indicator
        self._loading_bar = QProgressBar()
        self._loading_bar.setObjectName("loadingBar")
        self._loading_bar.setRange(0, 0)
        self._loading_bar.setFixedHeight(3)
        self._loading_bar.setVisible(False)
        self._loading_bar.setTextVisible(False)
        sv.addWidget(self._loading_bar)

        root.addWidget(sidebar)

        # ── Area kanan ────────────────────────────────────────────────────────
        right = QWidget()
        right.setObjectName("analyticsRight")
        rv = QVBoxLayout(right)
        rv.setContentsMargins(0, 0, 0, 0)
        rv.setSpacing(0)

        # Filter bar
        rv.addWidget(self._make_filter_bar())

        # Stack konten
        self._stack = QStackedWidget()
        self._stack.setObjectName("analyticsStack")

        self._panel_ringkasan = RingkasanPanel()
        self._panel_tren      = TrenPanel()
        self._panel_top       = TopPanel()
        self._panel_jam       = JamPanel()
        self._panel_inactive  = InactivePanel()
        self._panel_export    = ExportPanel()
        self._panel_export.log_message.connect(self._log)

        for panel in [self._panel_ringkasan, self._panel_tren,
                      self._panel_top, self._panel_jam,
                      self._panel_inactive, self._panel_export]:
            self._stack.addWidget(_scrollable(panel))

        rv.addWidget(self._stack, stretch=1)

        # Log bar bawah
        rv.addWidget(self._make_log_bar())

        root.addWidget(right, stretch=1)

    def _make_filter_bar(self) -> QWidget:
        bar = QWidget()
        bar.setObjectName("analyticsFilterBar")
        h = QHBoxLayout(bar)
        h.setContentsMargins(14, 8, 14, 8)
        h.setSpacing(10)

        lbl = QLabel("Periode:")
        lbl.setObjectName("filterLabel")
        h.addWidget(lbl)

        self._date_start = QDateEdit()
        self._date_start.setObjectName("filterDate")
        self._date_start.setCalendarPopup(True)
        self._date_start.setDisplayFormat("dd/MM/yyyy")
        h.addWidget(self._date_start)

        lbl2 = QLabel("—")
        lbl2.setObjectName("filterLabel")
        h.addWidget(lbl2)

        self._date_end = QDateEdit()
        self._date_end.setObjectName("filterDate")
        self._date_end.setCalendarPopup(True)
        self._date_end.setDisplayFormat("dd/MM/yyyy")
        h.addWidget(self._date_end)

        # Shortcut cepat
        for label, days in [("7H", 7), ("30H", 30), ("90H", 90)]:
            btn = QPushButton(label)
            btn.setObjectName("filterShortcut")
            btn.clicked.connect(lambda _, d=days: self._set_quick_range(d))
            h.addWidget(btn)

        h.addStretch()

        self._btn_refresh = QPushButton("↻  Muat Ulang")
        self._btn_refresh.setObjectName("btnRefresh")
        self._btn_refresh.clicked.connect(lambda: self._load_panel(self._current_panel))
        h.addWidget(self._btn_refresh)

        return bar

    def _make_log_bar(self) -> QWidget:
        bar = QWidget()
        bar.setObjectName("analyticsLogBar")
        bar.setFixedHeight(56)
        h = QHBoxLayout(bar)
        h.setContentsMargins(14, 4, 14, 4)

        self._log_console = QTextEdit()
        self._log_console.setObjectName("logConsoleInline")
        self._log_console.setReadOnly(True)
        self._log_console.setFont(QFont("Consolas", 10))
        self._log_console.setFixedHeight(48)
        h.addWidget(self._log_console)

        return bar

    # ══════════════════════════════════════════════════════════════════════════
    # Aksi
    # ══════════════════════════════════════════════════════════════════════════

    def _set_quick_range(self, days: int):
        today = date.today()
        self._date_start.setDate(QDate(*(today - timedelta(days=days)).timetuple()[:3]))
        self._date_end.setDate(QDate(*today.timetuple()[:3]))
        self._load_panel(self._current_panel)

    def _get_date_range(self) -> tuple[date, date]:
        qs = self._date_start.date()
        qe = self._date_end.date()
        return (
            date(qs.year(), qs.month(), qs.day()),
            date(qe.year(), qe.month(), qe.day()),
        )

    def _load_panel(self, key: str):
        self._current_panel = key

        # Update sidebar aktif
        for k, btn in self._sb_buttons.items():
            btn.setChecked(k == key)

        # Switch stack
        idx = [p[0] for p in _PANELS].index(key)
        self._stack.setCurrentIndex(idx)

        if key == "export":
            s, e = self._get_date_range()
            self._panel_export.set_date_range(s, e)
            return

        # Jalankan query di background
        s, e = self._get_date_range()
        self._loading_bar.setVisible(True)
        self._btn_refresh.setEnabled(False)
        self._log(f"Memuat data {dict(_PANELS)[key]} ({s} — {e})...", "info")

        self._worker = AnalyticsWorker(s, e, key)
        self._worker.finished.connect(self._on_data_ready)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_data_ready(self, data: dict):
        self._loading_bar.setVisible(False)
        self._btn_refresh.setEnabled(True)

        panel_key = data.get("panel", "")
        panel_map = {
            "ringkasan": self._panel_ringkasan,
            "tren":      self._panel_tren,
            "top":       self._panel_top,
            "jam":       self._panel_jam,
            "inactive":  self._panel_inactive,
        }
        panel = panel_map.get(panel_key)
        if panel:
            panel.update_data(data)

        self._log(f"Data berhasil dimuat.", "success")

    def _on_error(self, msg: str):
        self._loading_bar.setVisible(False)
        self._btn_refresh.setEnabled(True)
        self._log(f"Error: {msg}", "error")
        QMessageBox.critical(self, "Error", msg)

    # ══════════════════════════════════════════════════════════════════════════
    # Log inline
    # ══════════════════════════════════════════════════════════════════════════

    def _log(self, message: str, level: str = "info"):
        from datetime import datetime
        lc     = _log_colors()
        color  = lc.get(level, lc["info"])
        ts_clr = lc.get("ts", "#888")
        prefix = {"success": "✓", "warning": "⚠", "error": "✗", "info": "i"}.get(level, "i")
        ts     = datetime.now().strftime("%H:%M:%S")
        html   = (f'<span style="color:{ts_clr}">[{ts}]</span> '
                  f'<span style="color:{color}">{prefix} {message}</span>')
        self._log_console.setHtml(html)