"""
gui/settings_dialog.py — Jendela Pengaturan Aplikasi PerpusReworked

Satu jendela konfigurasi terpusat untuk nilai-nilai yang sebelumnya
tersebar sebagai konstanta hardcoded di seluruh kode (denda per hari,
nama sekolah default, durasi pinjam, dst). Nilai disimpan lewat
database/settings_db.py dan langsung berlaku di modul lain tanpa restart
— kecuali perubahan tema warna, yang butuh restart karena stylesheet
di-generate sekali di awal aplikasi (dicatat jelas di UI).

Dipanggil dari gui/main_window.py lewat tombol ⚙ Pengaturan di sidebar.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QWidget,
    QLabel, QLineEdit, QSpinBox, QComboBox, QPushButton,
    QMessageBox,
)

from database import settings_db
import theme as theme_module

APP_THEME_LABELS = {
    "sage_light":    "Sage Light — hijau natural, terang",
    "glowing_moss":  "Glowing Moss — hutan malam, gelap",
    "earthstone":     "Earthstone — hijau bumi, netral",
    "terracotta":     "Terracotta — tanah liat, hangat",
    "riverstone":     "Riverstone — abu kabut, redup",
    "sandstone":     "Sandstone — pasir gurun, gandum",
    "duskstone":     "Duskstone — bunga liar, lembayung senja",
    "ashwood":      "Ashwood — kayu lapuk, kabut hutan",
    "deep_terra":     "Deep Terra — bara api, gelap"
}


class SettingsDialog(QDialog):
    """Jendela konfigurasi: denda, durasi pinjam, batas pinjam, nama sekolah, tema."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("settingsDialog")
        self.setWindowTitle("Pengaturan Aplikasi")
        self.setMinimumWidth(460)
        self.setModal(True)
        self._build_ui()
        self._load_values()

    # ══════════════════════════════════════════════════════════════════════
    # Build UI
    # ══════════════════════════════════════════════════════════════════════

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(14)

        title = QLabel("⚙  Pengaturan Aplikasi")
        title.setObjectName("settingsTitle")
        root.addWidget(title)

        subtitle = QLabel(
            "Nilai di sini dipakai di seluruh aplikasi (Peminjaman, Cetak Kartu, dsb)."
        )
        subtitle.setObjectName("settingsSubtitle")
        subtitle.setWordWrap(True)
        root.addWidget(subtitle)

        # ── Bagian: Peminjaman & Denda ──────────────────────────────────────
        root.addWidget(self._make_loan_section())

        # ── Bagian: Identitas Sekolah ────────────────────────────────────────
        root.addWidget(self._make_school_section())

        # ── Bagian: Tampilan ─────────────────────────────────────────────────
        root.addWidget(self._make_theme_section())

        root.addStretch()

        # ── Badge status tersimpan ───────────────────────────────────────────
        self._lbl_saved = QLabel("")
        self._lbl_saved.setObjectName("settingsSavedBadge")
        root.addWidget(self._lbl_saved)

        # ── Tombol aksi ───────────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self._btn_cancel = QPushButton("Batal")
        self._btn_cancel.setObjectName("btnSettingsCancel")
        self._btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(self._btn_cancel)

        self._btn_save = QPushButton("Simpan Pengaturan")
        self._btn_save.setObjectName("btnSettingsSave")
        self._btn_save.clicked.connect(self._on_save)
        btn_row.addWidget(self._btn_save)

        root.addLayout(btn_row)

    def _section(self, title_text: str) -> tuple[QWidget, QFormLayout]:
        """Bikin panel section dengan judul + form layout, konsisten di semua bagian."""
        box = QWidget()
        box.setObjectName("settingsSection")
        v = QVBoxLayout(box)
        v.setContentsMargins(16, 14, 16, 14)
        v.setSpacing(10)

        lbl = QLabel(title_text)
        lbl.setObjectName("settingsSectionTitle")
        v.addWidget(lbl)

        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        v.addLayout(form)

        return box, form

    def _make_loan_section(self) -> QWidget:
        box, form = self._section("PEMINJAMAN & DENDA")

        self._spn_denda = QSpinBox()
        self._spn_denda.setObjectName("settingsInput")
        self._spn_denda.setRange(0, 1_000_000)
        self._spn_denda.setSingleStep(100)
        self._spn_denda.setSuffix("  / hari")
        self._spn_denda.setPrefix("Rp ")
        self._spn_denda.setGroupSeparatorShown(True)
        form.addRow(self._field_label("Besar denda keterlambatan"), self._spn_denda)

        self._spn_durasi = QSpinBox()
        self._spn_durasi.setObjectName("settingsInput")
        self._spn_durasi.setRange(1, 90)
        self._spn_durasi.setSuffix(" hari")
        form.addRow(self._field_label("Durasi pinjam default"), self._spn_durasi)

        self._spn_max = QSpinBox()
        self._spn_max.setObjectName("settingsInput")
        self._spn_max.setRange(1, 30)
        self._spn_max.setSuffix(" buku")
        form.addRow(self._field_label("Maks. buku per anggota"), self._spn_max)

        return box

    def _make_school_section(self) -> QWidget:
        box, form = self._section("IDENTITAS SEKOLAH")

        self._input_school = QLineEdit()
        self._input_school.setObjectName("settingsInput")
        self._input_school.setPlaceholderText("mis. MTs Negeri 0 Pemancingan")
        form.addRow(self._field_label("Nama sekolah / instansi default"), self._input_school)

        hint = QLabel("Dipakai sebagai nilai awal saat mencetak kartu anggota massal.")
        hint.setObjectName("settingsFieldHint")
        hint.setWordWrap(True)
        form.addRow("", hint)

        return box

    def _make_theme_section(self) -> QWidget:
        box, form = self._section("TAMPILAN")

        self._combo_theme = QComboBox()
        self._combo_theme.setObjectName("settingsInput")
        for key in theme_module._THEMES.keys():
            self._combo_theme.addItem(APP_THEME_LABELS.get(key, key), userData=key)
        form.addRow(self._field_label("Tema warna"), self._combo_theme)

        hint = QLabel("Perubahan tema baru terlihat setelah aplikasi di-restart.")
        hint.setObjectName("settingsFieldHint")
        hint.setWordWrap(True)
        form.addRow("", hint)

        return box

    def _field_label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("settingsFieldLabel")
        lbl.setWordWrap(True)
        return lbl

    # ══════════════════════════════════════════════════════════════════════
    # Load / Save
    # ══════════════════════════════════════════════════════════════════════

    def _load_values(self) -> None:
        self._spn_denda.setValue(settings_db.get_denda_per_hari())
        self._spn_durasi.setValue(settings_db.get_durasi_pinjam())
        self._spn_max.setValue(settings_db.get_max_pinjam())
        self._input_school.setText(settings_db.get_nama_sekolah())

        current_theme = settings_db.get_active_theme() or theme_module.ACTIVE_THEME
        idx = self._combo_theme.findData(current_theme)
        if idx >= 0:
            self._combo_theme.setCurrentIndex(idx)

    def _on_save(self) -> None:
        nama_sekolah = self._input_school.text().strip()
        if not nama_sekolah:
            QMessageBox.warning(
                self, "Nama sekolah kosong",
                "Nama sekolah / instansi tidak boleh kosong."
            )
            return

        theme_before = settings_db.get_active_theme()
        theme_after = self._combo_theme.currentData()

        settings_db.set_many({
            "denda_per_hari": self._spn_denda.value(),
            "durasi_pinjam":  self._spn_durasi.value(),
            "max_pinjam":     self._spn_max.value(),
            "nama_sekolah":   nama_sekolah,
            "active_theme":   theme_after,
        })

        self._lbl_saved.setText("✓ Pengaturan tersimpan.")

        if theme_after != theme_before:
            QMessageBox.information(
                self, "Tema diubah",
                "Tema warna baru akan terlihat setelah aplikasi ditutup dan dibuka kembali."
            )

        self.accept()
