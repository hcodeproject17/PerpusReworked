"""
database/sqlite_db.py — Handler SQLite untuk histori kunjungan
"""

import sqlite3
import logging
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from config import DATABASE_PATH
from database.loan_db import init_loan_db


logger = logging.getLogger(__name__)


def _get_connection() -> sqlite3.Connection:
    """Buka koneksi SQLite dengan row_factory agar hasil bisa diakses sebagai dict."""
    conn = sqlite3.connect(str(DATABASE_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")   # Lebih aman untuk akses bersamaan
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db() -> None:
    """
    Buat tabel histori_kunjungan jika belum ada.
    Aman dipanggil berulang kali (idempotent).
    """
    ddl = """
    CREATE TABLE IF NOT EXISTS histori_kunjungan (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        barcode_id  TEXT    NOT NULL,
        nama        TEXT    NOT NULL,
        tanggal     DATE    NOT NULL,
        waktu_masuk DATETIME NOT NULL
    );

    CREATE INDEX IF NOT EXISTS idx_barcode_tanggal
        ON histori_kunjungan (barcode_id, tanggal);
    """
    try:
        with _get_connection() as conn:
            conn.executescript(ddl)
        logger.info("Database diinisialisasi.")
        from database.book_db import init_book_db  # ← tambahkan
        init_book_db()
        from database.settings_db import init_settings_db
        init_settings_db()
    except sqlite3.Error as exc:
        logger.error("Gagal inisialisasi database: %s", exc)
        raise

init_loan_db()

def check_visitor_today(barcode_id: str) -> bool:
    """
    Kembalikan True jika barcode_id sudah tercatat pada tanggal hari ini.
    """
    sql = """
    SELECT 1 FROM histori_kunjungan
    WHERE barcode_id = ? AND tanggal = ?
    LIMIT 1
    """
    try:
        with _get_connection() as conn:
            row = conn.execute(sql, (barcode_id, date.today().isoformat())).fetchone()
        return row is not None
    except sqlite3.Error as exc:
        logger.error("Gagal cek pengunjung hari ini: %s", exc)
        return False


def record_visit(barcode_id: str, nama: str) -> bool:
    """
    Catat kunjungan baru.

    Returns:
        True  — berhasil dicatat
        False — sudah tercatat hari ini ATAU terjadi error
    """
    if check_visitor_today(barcode_id):
        logger.warning("Duplikat scan: %s (%s) sudah tercatat hari ini.", nama, barcode_id)
        return False

    sql = """
    INSERT INTO histori_kunjungan (barcode_id, nama, tanggal, waktu_masuk)
    VALUES (?, ?, ?, ?)
    """
    now = datetime.now()
    try:
        with _get_connection() as conn:
            conn.execute(sql, (
                barcode_id,
                nama,
                now.date().isoformat(),
                now.isoformat(timespec="seconds"),
            ))
        logger.info("Kunjungan dicatat: %s (%s) pukul %s", nama, barcode_id, now.strftime("%H:%M:%S"))
        return True
    except sqlite3.Error as exc:
        logger.error("Gagal catat kunjungan: %s", exc)
        return False


def get_today_visitors() -> list[dict]:
    """
    Kembalikan daftar pengunjung hari ini, urut dari terbaru.

    Returns:
        list of dict dengan key: id, barcode_id, nama, tanggal, waktu_masuk
    """
    sql = """
    SELECT id, barcode_id, nama, tanggal, waktu_masuk
    FROM histori_kunjungan
    WHERE tanggal = ?
    ORDER BY waktu_masuk DESC
    """
    try:
        with _get_connection() as conn:
            rows = conn.execute(sql, (date.today().isoformat(),)).fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as exc:
        logger.error("Gagal ambil data pengunjung hari ini: %s", exc)
        return []


def get_visits_by_date_range(
    start: date,
    end: date,
    barcode_id: Optional[str] = None,
) -> list[dict]:
    """
    Ambil histori kunjungan dalam rentang tanggal tertentu.
    Opsional filter per barcode_id (untuk fase analitik).

    Args:
        start       : Tanggal mulai (inklusif)
        end         : Tanggal akhir (inklusif)
        barcode_id  : Filter anggota tertentu, None = semua anggota

    Returns:
        list of dict, urut dari terbaru
    """
    if barcode_id:
        sql = """
        SELECT id, barcode_id, nama, tanggal, waktu_masuk
        FROM histori_kunjungan
        WHERE tanggal BETWEEN ? AND ? AND barcode_id = ?
        ORDER BY waktu_masuk DESC
        """
        params = (start.isoformat(), end.isoformat(), barcode_id)
    else:
        sql = """
        SELECT id, barcode_id, nama, tanggal, waktu_masuk
        FROM histori_kunjungan
        WHERE tanggal BETWEEN ? AND ?
        ORDER BY waktu_masuk DESC
        """
        params = (start.isoformat(), end.isoformat())

    try:
        with _get_connection() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as exc:
        logger.error("Gagal ambil histori kunjungan: %s", exc)
        return []


def get_visit_count_today() -> int:
    """Kembalikan jumlah kunjungan unik hari ini (untuk header dashboard)."""
    sql = "SELECT COUNT(*) FROM histori_kunjungan WHERE tanggal = ?"
    try:
        with _get_connection() as conn:
            result = conn.execute(sql, (date.today().isoformat(),)).fetchone()
        return result[0] if result else 0
    except sqlite3.Error as exc:
        logger.error("Gagal hitung kunjungan hari ini: %s", exc)
        return 0
