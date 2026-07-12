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

GLOWING_MOSS = Palette(
    p1 = "6A7A5D",  # Muted forest green / Hijau hutan pudar
    p2 = "88997A",  # Soft sage / Hijau sage terang
    p3 = "B2C0A5",  # Pale moss / Hijau lumut pucat
    p4 = "C8B992",  # Muted sand / Pasir pudar untuk aksen

    text_primary   = "E8E6DF",  # Putih tulang pucat (tidak menyilaukan)
    text_secondary = "9C9F96",  # Abu-abu kehijauan pudar
    text_on_dark   = "111310",  # Hijau arang pekat (untuk teks di atas tombol p1/p2)

    bg      = "111310",  # Hijau arang sangat pekat (hampir hitam)
    surface = "1A1D18",  # Hijau batu gelap (sedikit lebih terang dari bg)
    border  = "2B3027",  # Garis batas abu-abu hijau redup

    log_bg      = "0A0B09",  # Hitam pekat dengan sedikit rona hijau
    log_text    = "B2C0A5",  # Sama dengan p3
    log_success = "7DA36D",  # Hijau klorofil redup
    log_warning = "CCA35C",  # Kuning emas tua
    log_error   = "C26A5F",  # Merah karat terang
    log_info    = "7292A1",  # Biru kabut malam
)

WHITE_FOREST = Palette(
# Palet utama
    p1 = "253D2C",   # #557153 — hijau tua (header, tombol, tab aktif)
    p2 = "245632",   # #7D8F69 — hijau menengah (sidebar, label)
    p3 = "68BA7F",   # #A9AF7E — sage muda (border, hover, divider)
    p4 = "B7E1C4",   # #E6E5A3 — krem kuning (badge, accent, highlight)

    # Teks
    text_primary   = "132A1A",   # hijau sangat gelap
    text_secondary = "2D6C3F",   # diperdalam dari 3C9054 (3.58:1 gagal AA) → 5.71:1 lolos AA
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

TERRACOTTA = Palette(
    p1 = "7A3E31",  # Deep rust / Bata gelap
    p2 = "A35E4E",  # Muted terracotta / Tanah liat
    p3 = "C88D7D",  # Soft clay / Persik redup
    p4 = "E0B986",  # Warm ochre / Pasir hangat

    text_primary   = "2E1813",  # Cokelat kehitaman (sangat gelap)
    text_secondary = "7A3E31",  # Sama dengan p1
    text_on_dark   = "FDF9F3",  # Krem putih hangat

    bg      = "F6EFEA",  # Abu-abu krem sangat terang
    surface = "EADED5",  # Krem tanah (sedikit lebih gelap dari bg)
    border  = "CDB6A6",  # Cokelat redup pucat

    log_bg      = "241512",  # Kopi gelap / Espresso
    log_text    = "C88D7D",  # Sama dengan p3
    log_success = "A4C982",  # Hijau redup (menjaga konsistensi alam)
    log_warning = "F2BE74",  # Kuning senja
    log_error   = "E37669",  # Merah bata lembut
    log_info    = "C88D7D",
)

RIVERSTONE = Palette(
    p1 = "3A4E5E",  # Deep slate blue / Biru batu gelap
    p2 = "58717F",  # Muted steel blue / Biru keabu-abuan
    p3 = "7C96A8",  # Soft grayish blue / Biru kabut
    p4 = "BFCBCE",  # Pale river sand / Abu-abu pucat

    text_primary   = "151C22",  # Biru dongker kehitaman
    text_secondary = "3A4E5E",  # Sama dengan p1
    text_on_dark   = "EEF3F9",  # Putih kebiruan bersih

    bg      = "E7EDF2",  # Abu-abu kebiruan sangat terang
    surface = "D8E2E8",  # Abu-abu batu muda
    border  = "A6B8C7",  # Biru pudar untuk garis batas

    log_bg      = "141A22",  # Biru malam sangat gelap
    log_text    = "7C96A8",  # Sama dengan p3
    log_success = "8DC4A7",  # Hijau air / Seafoam redup
    log_warning = "DFCA73",  # Kuning pasir redup
    log_error   = "D97B7B",  # Merah karang redup
    log_info    = "7C96A8",
)

SANDSTONE = Palette(
    p1 = "82623B",  # Deep ochre / Cokelat emas gelap
    p2 = "A38052",  # Warm caramel / Karamel redup
    p3 = "C4A77D",  # Soft beige / Krem gandum
    p4 = "E6C998",  # Pale gold / Kuning pasir pucat

    text_primary   = "2B2013",  # Cokelat kopi pekat
    text_secondary = "82623B",  # Sama dengan p1
    text_on_dark   = "FBF8F1",  # Putih gading

    bg      = "F7F4EB",  # Krem sangat terang (hampir putih)
    surface = "EBE3D3",  # Krem pasir hangat
    border  = "D1C3A5",  # Cokelat pudar

    log_bg      = "231A0F",  # Cokelat tanah hitam
    log_text    = "C4A77D",  # Sama dengan p3
    log_success = "A3C47D",  # Hijau daun redup
    log_warning = "E3B666",  # Kuning madu
    log_error   = "DF7C72",  # Merah koral redup
    log_info    = "C4A77D",
)

DUSKSTONE = Palette(
    p1 = "52485E",  # Deep dusty plum / Ungu gelap pudar
    p2 = "71647F",  # Muted mauve / Lembayung redup
    p3 = "998BA8",  # Soft lavender gray / Abu-abu keunguan
    p4 = "C7B2A9",  # Warm dusty rose / Merah muda abu-abu sebagai aksen

    text_primary   = "1A161E",  # Ungu kehitaman gelap
    text_secondary = "52485E",  # Sama dengan p1
    text_on_dark   = "F8F5FA",  # Putih salju dengan sentuhan ungu

    bg      = "F3EFF5",  # Abu-abu ungu sangat terang
    surface = "E6E0E9",  # Abu-abu lembayung pucat
    border  = "C2BAC7",  # Garis batas abu-abu ungu

    log_bg      = "19151C",  # Malam gelap
    log_text    = "998BA8",  # Sama dengan p3
    log_success = "93C298",  # Hijau mint pudar
    log_warning = "DDB87C",  # Kuning senja
    log_error   = "CD7987",  # Merah mawar pudar
    log_info    = "998BA8",
)

ASHWOOD = Palette(
    p1 = "5B5652",  # Dark taupe / Abu-abu kecokelatan gelap
    p2 = "7A746E",  # Muted warm gray / Abu-abu hangat
    p3 = "A19B96",  # Soft ash / Warna debu kayu
    p4 = "859688",  # Muted sage / Hijau lumut pudar sebagai aksen

    text_primary   = "1E1C1A",  # Abu-abu kehitaman pekat
    text_secondary = "5B5652",  # Sama dengan p1
    text_on_dark   = "F5F4F2",  # Putih tulang

    bg      = "F0EFEA",  # Abu-abu sangat terang
    surface = "E2DFDA",  # Abu-abu batu koral muda
    border  = "C1BCB7",  # Abu-abu pudar

    log_bg      = "1E1C1A",  # Arang gelap
    log_text    = "A19B96",  # Sama dengan p3
    log_success = "96B392",  # Hijau herbal
    log_warning = "D1BE84",  # Kuning zaitun pucat
    log_error   = "C77B77",  # Merah terakota pudar
    log_info    = "A19B96",
)

DEEP_TERRA = Palette(
    p1 = "945A4C",  # Muted rust / Karat bata terang
    p2 = "B37766",  # Soft terracotta / Tanah liat terang
    p3 = "D6A79A",  # Pale peach / Persik debu
    p4 = "C7A56F",  # Muted ochre / Emas pasir

    text_primary   = "EAE6E1",  # Krem putih sangat lembut
    text_secondary = "A39994",  # Cokelat keabu-abuan pudar
    text_on_dark   = "14100F",  # Kopi hitam pekat

    bg      = "14100F",  # Kopi hitam pekat (hampir hitam)
    surface = "1F1917",  # Cokelat arang (sedikit lebih terang dari bg)
    border  = "332824",  # Garis batas cokelat gelap

    log_bg      = "0A0807",  # Hitam pekat absolut dengan rona hangat
    log_text    = "D6A79A",  # Sama dengan p3
    log_success = "8DA671",  # Hijau zaitun
    log_warning = "D4A86A",  # Kuning jingga redup
    log_error   = "D17769",  # Merah koral terang
    log_info    = "D6A79A",
)

# ── Registri tema ─────────────────────────────────────────────────────────────
_THEMES: dict[str, Palette] = {
    "sage_light":    SAGE_LIGHT,
    "glowing_moss": GLOWING_MOSS,
    "earthstone": EARTHSTONE,
    "terracotta": TERRACOTTA,
    "riverstone": RIVERSTONE,
    "sandstone": SANDSTONE,
    "duskstone": DUSKSTONE,
    "ashwood": ASHWOOD,
    "deep_terra": DEEP_TERRA,
}

def get_palette() -> Palette:
    """
    Kembalikan Palette yang sedang aktif.

    Prioritas: nilai 'active_theme' di settings_db (diset lewat jendela
    Pengaturan) → fallback ke konstanta ACTIVE_THEME di atas. Dibungkus
    try/except karena stylesheet() dipanggil sebelum init_db() saat startup
    (lihat main.py) — di titik itu tabel settings belum tentu ada.
    """
    theme_name = ACTIVE_THEME
    try:
        from database import settings_db
        theme_name = settings_db.get_active_theme() or ACTIVE_THEME
    except Exception:
        pass
    return _THEMES.get(theme_name, _THEMES.get(ACTIVE_THEME, SAGE_LIGHT))


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
    color: {TS};
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
    color: {TS};
    letter-spacing: 1.1px;
}}

/* ── Kamera ──────────────────────────────────────────────────────────────── */
QLabel#cameraDisplay {{
    background-color: transparent;
    border: 1px solid {BRD};
    border-radius: 8px;
    color: {TS};
    font-size: 13px;
}}
QLabel#camStatusStandby {{ background-color: transparent; color: {TS}; font-size: 11px; font-weight: 600; }}
QLabel#camStatusActive  {{ background-color: transparent; color: {P1}; font-size: 11px; font-weight: 600; }}
QLabel#camStatusError   {{ background-color: transparent; color: #C0392B; font-size: 11px; font-weight: 600; }}

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
QLabel#hintLabel {{ margin: 3px 5px; color: {TS}; font-size: 10px; font-style: italic; background-color: transparent; }}

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
QTableWidget#visitorTable::item {{ padding: 6px 10px; }}
QTableWidget#visitorTable QHeaderView::section {{
    background-color: {P1};
    color: {TOD};
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1px;
    border: none;
    border-bottom: 1px solid {P2};
    padding: 8px 10px;
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
    color: {TS};
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
    background-color: transparent;
    color: {TS};
    font-size: 14px;
    line-height: 180%;
}}

/* ── Card tab: Input ─────────────────────────────────────────────────────── */
QLineEdit#fileInput {{
    background-color: {BG};
    border: 1px solid {BRD};
    border-radius: 6px;
    padding: 6px 10px;
    color: {TS};
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
    color: {TS};
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
QLabel#hintText    {{ color: {TS}; font-size: 11px; background-color: transparent;}}
QLabel#fieldLabel  {{ color: {TS}; font-size: 11px; background-color: transparent;}}
QLabel#idFmtLabel  {{ color: {P1}; font-size: 10px; font-family: 'Consolas', monospace; background-color: transparent; margin-top: 3px; }}
QLabel#resultLabel {{ color: {TS}; font-size: 11px; font-family: 'Consolas', monospace; padding: 4px; background-color: transparent;}}
QLabel#countLabel  {{ font-size: 12px; color: {P1}; font-weight: 600; background-color: transparent;}}
QLabel#progressLabel {{ color: {TS}; font-size: 10px; font-family: 'Consolas', monospace; background-color: transparent;}}

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
    color: {TS};
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
    background-color: transparent;
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
    color: {TS};
    font-size: 12px;
}}
QLabel#statusSmall {{ color: {TS}; font-size: 11px; background-color: transparent;}}
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
    color: {TS};
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
QLabel#filterLabel {{
    background-color: transparent;
    color: {TS};
    font-size: 12px;
    font-weight: 500;
}}
QPushButton#filterShortcut {{
    background-color: {BG};
    color: {P1};
    border: 1px solid {P3};
    border-radius: 5px;
    padding: 4px 10px;
    font-size: 11px;
    font-weight: 600;
}}
QPushButton#filterShortcut:hover {{ background-color: {P4}; }}
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
    background-color: transparent;
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
QTableWidget#analyticsTable::item {{ padding: 6px 10px; }}
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
    color: {TS};
    font-size: 13px;
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
    color: {TS};
    font-size: 10px;
    font-family: 'Consolas', monospace;
}}
QTextEdit#logConsoleInline {{
    background-color: transparent;
    border: none;
    color: {_c(p.log_text)};
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 11px;
    padding: 0px;
}}

/* ── Navigasi utama (sidebar) ───────────────────────────────────────────────
   Macrostructure aplikasi produktivitas padat-data: navigasi persisten di
   kiri (bukan tab horizontal) supaya (a) semua menu terlihat sekaligus tanpa
   overflow saat menu bertambah, (b) label + ikon + shortcut angka terlihat
   bersamaan untuk navigasi cepat via mouse ATAU keyboard (Ctrl+1..6), dan
   (c) area kerja kanan mendapat lebar maksimum untuk tabel data.        ── */
QWidget#navSidebar {{
    background-color: {SRF};
    border-right: 1px solid {BRD};
}}
QLabel#navBrand {{
    background-color: transparent;
    font-size: 15px;
    font-weight: 700;
    color: {P1};
    letter-spacing: 0.2px;
    padding: 2px 0px;
}}
QLabel#navBrandSub {{
    background-color: transparent;
    font-size: 10px;
    color: {TS};
    letter-spacing: 0.5px;
}}
QFrame#navDivider {{
    background-color: {BRD};
    max-height: 1px;
}}
QPushButton#navItem {{
    background-color: transparent;
    color: {TS};
    border: none;
    border-radius: 8px;
    padding: 10px 12px;
    font-size: 13px;
    font-weight: 600;
    text-align: left;
}}
QPushButton#navItem:hover {{
    background-color: {BG};
    color: {P1};
}}
QPushButton#navItem:checked {{
    background-color: {P1};
    color: {TOD};
}}
QLabel#navShortcut {{
    background-color: transparent;
    color: {TS};
    font-size: 10px;
    font-family: 'Consolas', monospace;
}}
QPushButton#navSettingsBtn {{
    background-color: transparent;
    color: {TS};
    border: 1px solid {BRD};
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 12px;
    font-weight: 600;
    text-align: left;
}}
QPushButton#navSettingsBtn:hover {{
    color: {P1};
    border-color: {P1};
}}

/* ── Jendela Pengaturan Aplikasi ─────────────────────────────────────────── */
QDialog#settingsDialog {{
    background-color: {BG};
    color: {TP};
}}
QLabel#settingsTitle {{
    background-color: transparent;
    font-size: 18px;
    font-weight: 700;
    color: {P1};
}}
QLabel#settingsSubtitle {{
    background-color: transparent;
    font-size: 12px;
    color: {TS};
}}
QWidget#settingsSection {{
    background-color: {SRF};
    border: 1px solid {BRD};
    border-radius: 10px;
}}
QLabel#settingsSectionTitle {{
    background-color: transparent;
    font-size: 11px;
    font-weight: 700;
    color: {P1};
    letter-spacing: 1px;
}}
QLabel#settingsFieldLabel {{
    background-color: transparent;
    font-size: 12px;
    font-weight: 600;
    color: {TP};
}}
QLabel#settingsFieldHint {{
    background-color: transparent;
    font-size: 11px;
    color: {TS};
}}
QSpinBox#settingsInput {{
    background-color: {BG};
    border: 1px solid {BRD};
    border-radius: 6px;
    padding: 7px 10px;
    color: {TP};
    font-size: 13px;
    min-height: 20px;
}}
QSpinBox#settingsInput:focus {{ border-color: {P1}; }}
QLineEdit#settingsInput {{
    background-color: {BG};
    border: 1px solid {BRD};
    border-radius: 6px;
    padding: 8px 10px;
    color: {TP};
    font-size: 13px;
}}
QLineEdit#settingsInput:focus {{ border-color: {P1}; }}
QComboBox#settingsInput {{
    background-color: {BG};
    border: 1px solid {BRD};
    border-radius: 6px;
    padding: 7px 10px;
    color: {TP};
    font-size: 13px;
    min-height: 20px;
}}
QComboBox#settingsInput:focus {{ border-color: {P1}; }}
QComboBox#settingsInput QAbstractItemView {{
    background-color: {BG};
    border: 1px solid {BRD};
    color: {TP};
    selection-background-color: {P1};
    selection-color: {TOD};
}}
QLabel#settingsSavedBadge {{
    background-color: transparent;
    color: {_c(p.log_success)};
    font-size: 12px;
    font-weight: 600;
}}
QPushButton#btnSettingsSave {{
    background-color: {P1};
    color: {TOD};
    border: none;
    border-radius: 6px;
    padding: 9px 20px;
    font-weight: 700;
}}
QPushButton#btnSettingsSave:hover {{ background-color: {P2}; }}
QPushButton#btnSettingsCancel {{
    background-color: transparent;
    color: {TS};
    border: 1px solid {BRD};
    border-radius: 6px;
    padding: 9px 18px;
    font-weight: 600;
}}
QPushButton#btnSettingsCancel:hover {{ color: {TP}; border-color: {P2}; }}
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