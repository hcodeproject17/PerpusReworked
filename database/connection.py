"""
database/connection.py — Pembuat koneksi SQLite bersama untuk semua
modul di database/ (row_factory + PRAGMA journal_mode/foreign_keys,
dengan opsi override sesuai kebutuhan tiap modul).
"""

import sqlite3

from config import DATABASE_PATH


def get_connection(wal: bool = True, foreign_keys: bool = True) -> sqlite3.Connection:
    """Buka koneksi SQLite dengan row_factory agar hasil bisa diakses sebagai dict."""
    conn = sqlite3.connect(str(DATABASE_PATH))
    conn.row_factory = sqlite3.Row
    if wal:
        conn.execute("PRAGMA journal_mode=WAL")   # Lebih aman untuk akses bersamaan
    if foreign_keys:
        conn.execute("PRAGMA foreign_keys=ON")
    return conn
