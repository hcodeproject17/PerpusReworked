"""
theme.py — Tema warna terpusat untuk PerpusReworked

Cara mengubah tema:
  1. Edit nilai hex di bagian PALETTE di bawah
  2. Simpan file — semua GUI otomatis pakai warna baru saat restart

Struktur:
  PALETTE      → warna mentah dari color picker
  ROLE         → mapping warna ke peran UI (jangan ubah nama key-nya)
  stylesheet() → fungsi yang menghasilkan QSS string siap pakai
"""

from __future__ import annotations
from dataclasses import dataclass


# ══════════════════════════════════════════════════════════════════════════════
# PALETTE — ubah di sini untuk ganti tema
# Semua nilai adalah hex string tanpa #, contoh: "557153"
# ══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class Palette:
    # ── 4 warna utama dari palet ──────────────────────────────────────────────
    p1: str   # Warna terkuat / paling gelap
    p2: str   # Warna menengah
    p3: str   # Warna muda / muted
    p4: str   # Warna paling terang / cream / accent

    # ── Warna teks ────────────────────────────────────────────────────────────
    text_primary:   str   # Teks utama (harus kontras dengan bg)
    text_secondary: str   # Teks label, hint, muted
    text_on_dark:   str   # Teks di atas warna gelap (biasanya putih/cream)

    # ── Surface & border ──────────────────────────────────────────────────────
    bg:      str   # Background utama window
    surface: str   # Surface panel, sidebar, groupbox
    border:  str   # Border tipis

    # ── Log console (biasanya tetap gelap untuk keterbacaan) ─────────────────
    log_bg:      str   # Background konsol log
    log_text:    str   # Teks default log
    log_success: str   # Warna teks log sukses
    log_warning: str   # Warna teks log warning
    log_error:   str   # Warna teks log error
    log_info:    str   # Warna teks log info


# ── Tema aktif — ganti assignment di sini untuk switch tema ──────────────────

ACTIVE_THEME = "earthstone"   # Pilihan: "sage_light" | "dark_original"

# ── Tema: Sage Light (hijau natural, terang) ──────────────────────────────────
SAGE_LIGHT = Palette(
    # Palet utama
    p1 = "557153",   # #557153 — hijau tua (header, tombol, tab aktif)
    p2 = "7D8F69",   # #7D8F69 — hijau menengah (sidebar, label)
    p3 = "A9AF7E",   # #A9AF7E — sage muda (border, hover, divider)
    p4 = "E6E5A3",   # #E6E5A3 — krem kuning (badge, accent, highlight)

    # Teks
    text_primary   = "2D3820",   # hijau sangat gelap
    text_secondary = "557153",   # hijau tua (sama dengan p1)
    text_on_dark   = "FFFFFF",   # putih untuk teks di atas p1

    # Surface
    bg      = "F5F5E8",   # background utama (krem sangat muda)
    surface = "EEEEDD",   # surface panel
    border  = "C8CC9A",   # border tipis

    # Log (tetap gelap)
    log_bg      = "2D3820",   # background log — hijau sangat tua
    log_text    = "A9AF7E",   # teks default log
    log_success = "E6E5A3",   # sukses — krem kuning
    log_warning = "F5E6A3",   # warning — kuning lebih hangat
    log_error   = "F4A0A0",   # error — merah muda
    log_info    = "7D8F69",   # info — sage menengah
)

# ── Tema: Dark Original (tema gelap dari versi awal) ─────────────────────────
DARK_ORIGINAL = Palette(
    p1 = "4f9cf9",
    p2 = "2a2f3d",
    p3 = "3e4455",
    p4 = "4ade80",

    text_primary   = "e2e4ed",
    text_secondary = "8892aa",
    text_on_dark   = "ffffff",

    bg      = "13161e",
    surface = "181b24",
    border  = "252938",

    log_bg      = "0d0f14",
    log_text    = "8892aa",
    log_success = "4ade80",
    log_warning = "facc15",
    log_error   = "f87171",
    log_info    = "94a3b8",
)

WHITE_FOREST = Palette(
# Palet utama
    p1 = "253D2C",   # #557153 — hijau tua (header, tombol, tab aktif)
    p2 = "245632",   # #7D8F69 — hijau menengah (sidebar, label)
    p3 = "68BA7F",   # #A9AF7E — sage muda (border, hover, divider)
    p4 = "B7E1C4",   # #E6E5A3 — krem kuning (badge, accent, highlight)

    # Teks
    text_primary   = "132A1A",   # hijau sangat gelap
    text_secondary = "3C9054",   # hijau tua (sama dengan p1)
    text_on_dark   = "FFFFFF",   # putih untuk teks di atas p1

    # Surface
    bg      = "CFFFDC",   # background utama (krem sangat muda)
    surface = "E3F2E8",   # surface panel
    border  = "9DD2AD",   # border tipis

    # Log (tetap gelap)
    log_bg      = "101912",   # background log — hijau sangat tua
    log_text    = "ABD8B8",   # teks default log
    log_success = "52B76F",   # sukses — krem kuning
    log_warning = "FCAB64",   # warning — kuning lebih hangat
    log_error   = "F21B3F",   # error — merah muda
    log_info    = "70798C",   # info — sage menengah
)

EARTHSTONE = Palette(
    p1 = "4A5E3A",
    p2 = "6B7F58",
    p3 = "98A87C",
    p4 = "D4C87A",

    text_primary   = "1E2818",
    text_secondary = "4A5E3A",
    text_on_dark   = "F9F6EE",

    bg      = "F2EFE7",
    surface = "E8E3D8",
    border  = "C5B99A",

    log_bg      = "1A2214",
    log_text    = "8FA87C",
    log_success = "C8E6A0",
    log_warning = "F5D080",
    log_error   = "F4A090",
    log_info    = "8FA87C",
)


# ── Registri tema ─────────────────────────────────────────────────────────────
_THEMES: dict[str, Palette] = {
    "sage_light":    SAGE_LIGHT,
    "dark_original": DARK_ORIGINAL,
    "white_forest": WHITE_FOREST,
    "earthstone": EARTHSTONE,
}

def get_palette() -> Palette:
    """Kembalikan Palette yang sedang aktif."""
    return _THEMES.get(ACTIVE_THEME, SAGE_LIGHT)


# ══════════════════════════════════════════════════════════════════════════════
# Stylesheet builder
# ══════════════════════════════════════════════════════════════════════════════

def _c(hex_str: str) -> str:
    """Tambah # ke hex string."""
    return f"#{hex_str}"


def stylesheet() -> str:
    """
    Hasilkan QSS string lengkap berdasarkan tema aktif.
    Dipanggil sekali di QApplication sebelum window pertama dibuka.
    """
    p = get_palette()

    # Shortcut lokal
    P1  = _c(p.p1)
    P2  = _c(p.p2)
    P3  = _c(p.p3)
    P4  = _c(p.p4)
    TP  = _c(p.text_primary)
    TS  = _c(p.text_secondary)
    TOD = _c(p.text_on_dark)
    BG  = _c(p.bg)
    SRF = _c(p.surface)
    BRD = _c(p.border)

    return f"""
/* ── Global ──────────────────────────────────────────────────────────────── */
QMainWindow, QWidget {{
    background-color: {BG};
    color: {TP};
    font-family: 'Segoe UI', sans-serif;
}}

/* ── Header ──────────────────────────────────────────────────────────────── */
QWidget#appHeader {{
    background-color: {BG};
    border-bottom: 1px solid {P2};
}}
QLabel#headerTitle {{
    font-size: 20px;
    font-weight: 700;
    background-color: transparent;
    color: {P1};
    letter-spacing: 0.3px;
}}
QLabel#headerDate {{
    font-size: 16px;
    background-color: transparent;
    color: {P1};
    font-weight: 700;
}}

/* ── Tab widget ──────────────────────────────────────────────────────────── */
QTabWidget#mainTabs::pane {{
    border: none;
    background-color: {BG};
}}
QTabWidget#mainTabs > QTabBar::tab {{
    background-color: {SRF};
    color: {P2};
    margin-top: 1px;
    padding: 10px 24px;
    font-size: 13px;
    font-weight: bold;
    border: none;
    border-bottom: 2px solid transparent;
}}
QTabWidget#mainTabs > QTabBar::tab:selected {{
    color: {P1};
    border-bottom: 2px solid {P1};
    background-color: {BG};
}}
QTabWidget#mainTabs > QTabBar::tab:hover:!selected {{
    color: {TS};
    background-color: {BG};
}}

/* ── Panel labels ────────────────────────────────────────────────────────── */
QLabel#panelLabel {{
    background-color: transparent;
    font-size: 13px;
    font-weight: bold;
    margin: 4px 0px 0px 5px;
    color: {P3};
    letter-spacing: 1.1px;
}}

/* ── Kamera ──────────────────────────────────────────────────────────────── */
QLabel#cameraDisplay {{
    background-color: transparent;
    border: 1px solid {BRD};
    border-radius: 8px;
    color: {P3};
    font-size: 13px;
}}
QLabel#camStatusStandby {{ color: {P3}; font-size: 11px; font-weight: 600; }}
QLabel#camStatusActive  {{ color: {P1}; font-size: 11px; font-weight: 600; }}
QLabel#camStatusError   {{ color: #C0392B; font-size: 11px; font-weight: 600; }}

/* ── Search ──────────────────────────────────────────────────────────────── */
QWidget#searchContainer {{
    background-color: {SRF};
    border: 1px solid {BRD};
    border-radius: 8px;
    padding: 12px;
}}
QLineEdit#searchInput {{
    background-color: {BG};
    border: 1px solid {BRD};
    border-radius: 6px;
    padding: 8px 12px;
    margin: 0px 5px;
    color: {TP};
    font-size: 13px;
}}
QLineEdit#searchInput:focus {{ border-color: {P1}; }}
QListWidget#searchResults {{
    background-color: {BG};
    border: 1px solid {BRD};
    border-radius: 6px;
    color: {TP};
    font-size: 12px;
}}
QListWidget#searchResults::item:hover    {{ background-color: {P4}; color: {TP}; }}
QListWidget#searchResults::item:selected {{ background-color: {P1}; color: {TOD}; }}
QLabel#hintLabel {{ margin: 3px 5px; color: {P3}; font-size: 10px; font-style: italic; background-color: transparent; }}

/* ── Tabel pengunjung ────────────────────────────────────────────────────── */
QTableWidget#visitorTable {{
    background-color: {BG};
    border: 1px solid {BRD};
    border-radius: 8px;
    gridline-color: {BRD};
    color: {TP};
    font-size: 12px;
    alternate-background-color: {SRF};
}}
QTableWidget#visitorTable QHeaderView::section {{
    background-color: {P1};
    color: {TOD};
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1px;
    border: none;
    border-bottom: 1px solid {P2};
    padding: 6px;
}}
QTableWidget#visitorTable::item:selected {{ background-color: {P4}; color: {TP}; }}
QLabel#countLabel {{ font-size: 12px; color: {P1}; font-weight: 600; background-color: transparent; }}

/* ── Log konsol ──────────────────────────────────────────────────────────── */
QTextEdit#logConsole {{
    background-color: {_c(p.log_bg)};
    border: 1px solid {BRD};
    border-radius: 8px;
    color: {_c(p.log_text)};
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 11px;
    padding: 8px;
}}

/* ── Tombol ──────────────────────────────────────────────────────────────── */
QPushButton {{
    border-radius: 6px;
    padding: 6px 14px;
    font-size: 12px;
    font-weight: 600;
}}
QPushButton#btnSearch {{
    background-color: {P1};
    color: {TOD};
    border: none;
    padding: 8px 16px;
}}
QPushButton#btnSearch:hover {{ background-color: {P2}; }}
QPushButton#btnClear {{
    background-color: transparent;
    color: {P2};
    border: 1px solid {BRD};
    padding: 4px 10px;
    font-size: 11px;
}}
QPushButton#btnClear:hover {{ color: {TP}; border-color: {P2}; }}
QPushButton#btnReconnect {{
    background-color: {SRF};
    color: #C0392B;
    border: 1px solid #E8A09A;
    padding: 8px;
}}
QPushButton#btnReconnect:hover {{ background-color: {BRD}; }}

/* ── Status bar ──────────────────────────────────────────────────────────── */
QStatusBar#appStatusBar {{
    background-color: {P1};
    border-top: 1px solid {P2};
}}
QLabel#statusBarLabel {{ color: {P4}; font-size: 11px; padding: 0 8px; background-color: transparent; }}

/* ── Splitter ────────────────────────────────────────────────────────────── */
QSplitter#mainSplitter::handle {{ background-color: {BRD}; }}

/* ── Card tab: Group box ─────────────────────────────────────────────────── */
QGroupBox#cardGroup {{
    background-color: {SRF};
    border: 1px solid {BRD};
    border-radius: 10px;
    margin-top: 14px;
    padding: 10px;
    font-size: 10px;
    font-weight: 700;
    color: {P2};
    letter-spacing: 1.2px;
}}
QGroupBox#cardGroup::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 0 6px;
    background-color: {SRF};
}}

/* ── Card tab: Panel aksi ────────────────────────────────────────────────── */
QWidget#actionPanel {{
    background-color: {P1};
    border: 1px solid {P2};
    border-radius: 10px;
}}
QLabel#actionHint {{
    border-radius: 6px;
    background-color: {BG};
    color: {P2};
    font-size: 14px;
    line-height: 180%;
}}

/* ── Card tab: Input ─────────────────────────────────────────────────────── */
QLineEdit#fileInput {{
    background-color: {BG};
    border: 1px solid {BRD};
    border-radius: 6px;
    padding: 6px 10px;
    color: {P3};
    font-size: 11px;
}}
QLineEdit#configInput {{
    background-color: {BG};
    border: 1px solid {BRD};
    padding: 7px 10px;
    border-radius: 6px;
    color: {TP};
    font-size: 12px;
}}
QLineEdit#configInput:focus {{ border-color: {P1}; }}
QSpinBox#configInput {{
    background-color: transparent;
    border: 1px solid {BRD};
    border-radius: 6px;
    padding: 6px 10px;
    color: {TP};
    font-size: 12px;
    min-width: 90px;
    min-height: 16px;
}}
QSpinBox#configInput::up-button, QSpinBox#configInput::down-button {{
    background-color: transparent;
    border: none;
    width: 18px;
}}
QComboBox#configCombo {{
    background-color: {BG};
    border: 1px solid {BRD};
    border-radius: 6px;
    padding: 7px 10px;
    color: {P2};
    font-size: 12px;
    min-height: 18px;
}}
QComboBox#configCombo:focus {{ border-color: {P1}; }}
QComboBox#configCombo::drop-down {{ border: none; padding-right: 6px; }}
QComboBox#configCombo QAbstractItemView {{
    background-color: {BG};
    border: 1px solid {BRD};
    color: {TP};
    selection-background-color: {P1};
    selection-color: {TOD};
}}

/* ── Card tab: Labels ────────────────────────────────────────────────────── */
QLabel#hintText    {{ color: {P2}; font-size: 11px; background-color: transparent;}}
QLabel#fieldLabel  {{ color: {TS}; font-size: 11px; background-color: transparent;}}
QLabel#idFmtLabel  {{ color: {P1}; font-size: 10px; font-family: 'Consolas', monospace; background-color: transparent; margin-top: 3px; }}
QLabel#resultLabel {{ color: {P2}; font-size: 11px; font-family: 'Consolas', monospace; padding: 4px; background-color: transparent;}}
QLabel#countLabel  {{ font-size: 12px; color: {P1}; font-weight: 600; background-color: transparent;}}
QLabel#progressLabel {{ color: {P2}; font-size: 10px; font-family: 'Consolas', monospace; background-color: transparent;}}

/* ── Card tab: Tombol ────────────────────────────────────────────────────── */
QPushButton#btnBrowse {{
    background-color: {SRF};
    color: {TP};
    border: 1px solid {BRD};
    border-radius: 6px;
    padding: 6px 12px;
    font-weight: 600;
}}
QPushButton#btnBrowse:hover {{ border-color: {P1}; color: {P1}; }}
QPushButton#btnPreview {{
    background-color: {P1};
    color: {P4};
    border: 1px solid {P3};
    border-radius: 6px;
    padding: 7px;
    font-weight: 600;
}}
QPushButton#btnPreview:hover {{ background-color: {P2}; }}
QPushButton#btnPreview:disabled {{ color: {P3}; border-color: {BRD}; background-color: {SRF} }}
QPushButton#btnGenerate {{
    background-color: {TOD};
    color: {P1};
    border: none;
    border-radius: 8px;
    padding: 12px;
    font-size: 13px;
    font-weight: 700;
}}
QPushButton#btnGenerate:hover {{ background-color: {P4}; }}
QPushButton#btnGenerate:disabled {{ background-color: {P3}; color: {BG}; }}
QPushButton#btnOpenFile {{
    background-color: {P1};
    color: {BG};
    border: 1px solid {P3};
    border-radius: 6px;
    padding: 7px;
    font-weight: 600;
    font-size: 11px;
}}
QPushButton#btnOpenFile:hover {{ background-color: {P2}; }}
QPushButton#btnOpenFile:disabled {{ color: {P3}; border-color: {BRD}; background-color: {SRF}; }}

/* ── Card tab: Tabel preview ─────────────────────────────────────────────── */
QTableWidget#previewTable {{
    background-color: {BG};
    border: 1px solid {BRD};
    border-radius: 8px;
    gridline-color: {BRD};
    color: {TP};
    font-size: 12px;
    alternate-background-color: {SRF};
}}
QTableWidget#previewTable QHeaderView::section {{
    background-color: {P1};
    color: {TOD};
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1px;
    border: none;
    border-bottom: 1px solid {P2};
    padding: 6px;
}}
QTableWidget#previewTable::item:selected {{ background-color: {P4}; color: {TP}; }}

/* ── Card tab: Progress bar ──────────────────────────────────────────────── */
QProgressBar#genProgress {{
    background-color: {SRF};
    border: 1px solid {BRD};
    border-radius: 5px;
    height: 6px;
    color: transparent;
}}
QProgressBar#genProgress::chunk {{
    background-color: {P1};
    border-radius: 4px;
}}

/* ── Camera dialog ───────────────────────────────────────────────────────── */
QDialog {{
    background-color: {BG};
    color: {TP};
}}
QLabel#dialogTitle {{
    font-size: 18px;
    background-color: transparent;
    font-weight: 700;
    color: {P1};
}}
QFrame#separator {{ color: {BRD}; }}
QGroupBox#camGroup {{
    background-color: {SRF};
    border: 1px solid {BRD};
    border-radius: 8px;
    margin-top: 8px;
    padding: 12px;
    font-size: 11px;
    color: {P2};
    font-weight: 700;
    letter-spacing: 1px;
}}
QGroupBox#camGroup::title {{
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    background-color: {SRF};
}}
QRadioButton {{
    color: {TP};
    font-size: 13px;
    spacing: 8px;
}}
QRadioButton::indicator {{
    width: 16px; height: 16px;
    border-radius: 8px;
    border: 2px solid {BRD};
    background: {BG};
}}
QRadioButton::indicator:checked {{
    border-color: {P1};
    background: {P1};
}}
QComboBox {{
    background-color: {BG};
    border: 1px solid {BRD};
    border-radius: 6px;
    padding: 6px 12px;
    color: {TP};
    font-size: 13px;
    min-height: 28px;
}}
QComboBox:disabled {{ color: {P2}; background-color: {SRF}; }}
QComboBox::drop-down {{ border: none; padding-right: 8px; }}
QComboBox QAbstractItemView {{
    background-color: {BG};
    border: 1px solid {BRD};
    color: {TP};
    selection-background-color: {P1};
    selection-color: {TOD};
}}
QLineEdit {{
    background-color: {BG};
    border: 1px solid {BRD};
    border-radius: 6px;
    padding: 8px 12px;
    color: {TP};
    font-size: 12px;
}}
QLineEdit:disabled {{ color: {P2}; background-color: {SRF}; }}
QLineEdit:focus {{ border-color: {P1}; }}
QLabel#previewLabel {{
    background-color: transparent;
    border: 1px dashed {BRD};
    border-radius: 6px;
    color: {P2};
    font-size: 12px;
}}
QLabel#statusSmall {{ color: {P2}; font-size: 11px; background-color: transparent;}}
QPushButton#btnPrimary {{
    background-color: {P1};
    color: {TOD};
    border: none;
}}
QPushButton#btnPrimary:hover {{ background-color: {P2}; }}
QPushButton#btnPrimary:disabled {{ background-color: {P3}; color: {BG}; }}
QPushButton#btnSecondary {{
    background-color: {SRF};
    color: {TP};
    border: 1px solid {BRD};
}}
QPushButton#btnSecondary:hover {{ border-color: {P1}; color: {P1}; }}
QPushButton#btnCancel {{
    background-color: transparent;
    color: {P2};
    border: 1px solid {BRD};
}}
QPushButton#btnCancel:hover {{ color: {TP}; border-color: {P2}; }}

/* ── Analytics tab: Sidebar ─────────────────────────────────────────────────── */
QWidget#analyticsSidebar {{
    background-color: {SRF};
    border-right: 1px solid {BRD};
}}
QLabel#sidebarTitle {{
    background-color: transparent;
    font-size: 14px;
    font-weight: 700;
    color: {P1};
    letter-spacing: 1.5px;
    padding: 4px 0px;
}}
QPushButton#sidebarBtn {{
    background-color: transparent;
    color: {P2};
    border: none;
    border-radius: 6px;
    padding: 10px 12px;
    font-size: 12px;
    font-weight: 600;
    text-align: left;
}}
QPushButton#sidebarBtn:hover {{
    background-color: {BG};
    color: {P1};
}}
QPushButton#sidebarBtn:checked {{
    background-color: {P1};
    color: {TOD};
}}
QFrame#sidebarDivider {{
    background-color: {BRD};
    max-height: 1px;
}}

/* ── Analytics tab: Right panel ─────────────────────────────────────────────── */
QWidget#analyticsRight {{
    background-color: {BG};
}}
QWidget#analyticsFilterBar {{
    background-color: {SRF};
    border-bottom: 1px solid {BRD};
}}
QDateEdit {{
    background-color: {BG};
    border: 1px solid {BRD};
    border-radius: 6px;
    padding: 6px 10px;
    color: {TP};
    font-size: 12px;
}}
QDateEdit:focus {{ border-color: {P1}; }}
QDateEdit::drop-down {{ border: none; padding-right: 6px; }}
QDateEdit QAbstractItemView {{
    background-color: {BG};
    border: 1px solid {BRD};
    color: {TP};
    selection-background-color: {P1};
    selection-color: {TOD};
}}
QPushButton#btnRefresh {{
    background-color: {P1};
    color: {TOD};
    border: none;
    border-radius: 6px;
    padding: 6px 14px;
    font-weight: 600;
}}
QPushButton#btnRefresh:hover {{ background-color: {P2}; }}

/* ── Analytics tab: Content ────────────────────────────────────────────────── */
QWidget#analyticsStack {{
    background-color: {BG};
}}
QScrollArea#analyticsScroll {{
    background-color: {BG};
    border: none;
}}
QWidget#analyticsCard {{
    background-color: {SRF};
    border: 1px solid {BRD};
    border-radius: 8px;
}}
QLabel#analyticsSectionLabel {{
    background-color: transparent;
    font-size: 13px;
    font-weight: 700;
    color: {P1};
    letter-spacing: 0.5px;
    margin: 4px 0px;
}}

/* ── Analytics tab: Stat cards ───────────────────────────────────────────────── */
QFrame#statCard {{
    background-color: {SRF};
    border: 1px solid {BRD};
    border-radius: 8px;
}}
QLabel#statCardValue {{
    background-color: transparent;
    font-size: 22px;
    font-weight: 700;
    color: {P1};
}}
QLabel#statCardValueAcc {{
    background-color: transparent;
    font-size: 22px;
    font-weight: 700;
    color: {P4};
}}
QLabel#statCardLabel {{
    background-color: transparent;
    font-size: 11px;
    font-weight: 600;
    color: {P2};
}}

/* ── Analytics tab: Tables ─────────────────────────────────────────────────── */
QTableWidget#analyticsTable {{
    background-color: {BG};
    border: 1px solid {BRD};
    border-radius: 6px;
    gridline-color: {BRD};
    color: {TP};
    font-size: 12px;
    alternate-background-color: {SRF};
}}
QTableWidget#analyticsTable QHeaderView::section {{
    background-color: {P1};
    color: {TOD};
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1px;
    border: none;
    border-bottom: 1px solid {P2};
    padding: 6px;
}}
QTableWidget#analyticsTable::item:selected {{ background-color: {P4}; color: {TP}; }}

/* ── Analytics tab: Info labels ─────────────────────────────────────────────── */
QLabel#analyticsInfo {{
    background-color: transparent;
    color: {P2};
    font-size: 11px;
    line-height: 150%;
}}
QLabel#analyticsCountLabel {{
    background-color: transparent;
    font-size: 13px;
    font-weight: 600;
    color: {P1};
}}

/* ── Analytics tab: Export panel ────────────────────────────────────────────── */
QLabel#exportTitle {{
    background-color: transparent;
    font-size: 14px;
    font-weight: 700;
    color: {P1};
}}
QFrame#exportDivider {{
    background-color: {BRD};
    max-height: 1px;
}}
QPushButton#btnExportExcel {{
    background-color: {P1};
    color: {TOD};
    border: none;
    border-radius: 6px;
    padding: 8px 14px;
    font-weight: 600;
}}
QPushButton#btnExportExcel:hover {{ background-color: {P2}; }}
QPushButton#btnExportPdf {{
    background-color: {P1};
    color: {TOD};
    border: none;
    border-radius: 6px;
    padding: 8px 14px;
    font-weight: 600;
}}
QPushButton#btnExportPdf:hover {{ background-color: {P2}; }}

/* ── Analytics tab: Loading bar ─────────────────────────────────────────────── */
QProgressBar#loadingBar {{
    background-color: {SRF};
    border: none;
    border-radius: 2px;
    height: 3px;
    color: transparent;
}}
QProgressBar#loadingBar::chunk {{
    background-color: {P1};
    border-radius: 2px;
}}

/* ── Analytics tab: Log bar ────────────────────────────────────────────────── */
QWidget#analyticsLogBar {{
    background-color: {SRF};
    border-top: 1px solid {BRD};
}}
QLabel#analyticsLogText {{
    background-color: transparent;
    color: {P2};
    font-size: 10px;
    font-family: 'Consolas', monospace;
}}
"""


# ══════════════════════════════════════════════════════════════════════════════
# Warna log — dipakai di _log() semua GUI
# ══════════════════════════════════════════════════════════════════════════════

def log_colors() -> dict[str, str]:
    """
    Kembalikan dict warna HTML untuk tiap level log.
    Dipakai di insertHtml() pada QTextEdit konsol log.
    """
    p = get_palette()
    return {
        "success": _c(p.log_success),
        "warning": _c(p.log_warning),
        "error":   _c(p.log_error),
        "info":    _c(p.log_info),
        "ts":      _c(p.log_text),      # timestamp
    }