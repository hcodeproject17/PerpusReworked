"""
database/settings_db.py — Penyimpanan pengaturan aplikasi PerpusReworked

Tabel `settings` menyimpan pasangan key/value (semua value disimpan sebagai
TEXT, dikonversi ke tipe yang sesuai saat dibaca). Ini dipakai oleh
gui/settings_dialog.py (jendela konfigurasi) dan dibaca ulang secara live
oleh database/loan_db.py serta gui/card_tab.py — jadi perubahan pengaturan
langsung berlaku tanpa perlu build ulang atau restart (kecuali tema warna,
yang butuh restart karena stylesheet di-generate sekali di awal aplikasi).

Key yang dikenal aplikasi (lihat DEFAULTS di bawah):
    denda_per_hari   — Rupiah per hari keterlambatan pengembalian buku
    durasi_pinjam    — Hari batas waktu pinjam default
    max_pinjam       — Maksimal buku dipinjam sekaligus per anggota
    nama_sekolah     — Nama sekolah/instansi default untuk cetak kartu
    active_theme     — Nama tema warna aktif (butuh restart aplikasi)
"""

from __future__ import annotations

import sqlite3
import logging
from typing import Any

from database.connection import get_connection

logger = logging.getLogger(__name__)

# ── Nilai default — dipakai jika key belum pernah diset ──────────────────────
DEFAULTS: dict[str, str] = {
    "denda_per_hari": "500",
    "durasi_pinjam":  "7",
    "max_pinjam":     "3",
    "nama_sekolah":   "MTs Negeri 12 Cirebon",
    "active_theme":   "earthstone",
}


def _get_connection() -> sqlite3.Connection:
    return get_connection(foreign_keys=False)


def init_settings_db() -> None:
    """Buat tabel settings jika belum ada. Dipanggil di init_db()."""
    with _get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key   TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)
        conn.commit()
    logger.info("settings_db siap.")


def get_setting(key: str, default: str | None = None) -> str:
    """Ambil satu nilai setting sebagai string. Fallback ke DEFAULTS lalu default param."""
    with _get_connection() as conn:
        row = conn.execute(
            "SELECT value FROM settings WHERE key = ?", (key,)
        ).fetchone()
    if row is not None:
        return row["value"]
    return DEFAULTS.get(key, default if default is not None else "")


def set_setting(key: str, value: Any) -> None:
    """Simpan satu nilai setting (di-cast ke string)."""
    with _get_connection() as conn:
        conn.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, str(value)),
        )
        conn.commit()
    logger.info("Setting diubah: %s = %s", key, value)


def set_many(values: dict[str, Any]) -> None:
    """Simpan beberapa setting sekaligus dalam satu transaksi."""
    with _get_connection() as conn:
        conn.executemany(
            "INSERT INTO settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            [(k, str(v)) for k, v in values.items()],
        )
        conn.commit()
    logger.info("Settings diubah sekaligus: %s", list(values.keys()))


def get_int(key: str, default: int | None = None) -> int:
    fallback = default if default is not None else int(DEFAULTS.get(key, "0"))
    raw = get_setting(key, str(fallback))
    try:
        return int(raw)
    except (TypeError, ValueError):
        logger.warning("Setting '%s' bernilai tidak valid (%r), pakai default %d", key, raw, fallback)
        return fallback


def get_str(key: str, default: str | None = None) -> str:
    fallback = default if default is not None else DEFAULTS.get(key, "")
    return get_setting(key, fallback)


def get_all_settings() -> dict[str, str]:
    """Kembalikan semua setting (default digabung dengan yang tersimpan di DB)."""
    merged = dict(DEFAULTS)
    with _get_connection() as conn:
        rows = conn.execute("SELECT key, value FROM settings").fetchall()
    for row in rows:
        merged[row["key"]] = row["value"]
    return merged


# ── Shortcut khusus — dipakai langsung oleh loan_db.py & card_tab.py ─────────

def get_denda_per_hari() -> int:
    return get_int("denda_per_hari")


def get_durasi_pinjam() -> int:
    return get_int("durasi_pinjam")


def get_max_pinjam() -> int:
    return get_int("max_pinjam")


def get_nama_sekolah() -> str:
    return get_str("nama_sekolah")


def get_active_theme() -> str:
    return get_str("active_theme")