"""
database/loan_db.py — Handler SQLite untuk peminjaman & pengembalian buku

Tabel:
    peminjaman — satu record per transaksi pinjam
        status: 'dipinjam' | 'dikembalikan' | 'terlambat'

Relasi:
    peminjaman.barcode_anggota → anggota.xlsx (ID Barcode)
    peminjaman.kode_buku       → buku.kode_buku (FK)
    jumlah_tersedia            → dikelola di tabel buku (book_db.py)

Denda:
    Dihitung saat pengembalian: Rp 500 per hari keterlambatan (default).
    Konstanta DENDA_PER_HARI bisa diubah di config.py atau di sini.
"""

import sqlite3
import logging
from datetime import date, datetime, timedelta
from typing import Optional

from config import DATABASE_PATH

logger = logging.getLogger(__name__)

# ── Konstanta ─────────────────────────────────────────────────────────────────
DENDA_PER_HARI   = 500     # Rupiah per hari keterlambatan
DURASI_PINJAM    = 7       # Hari pinjam default
MAX_PINJAM       = 3       # Maksimal buku dipinjam sekaligus per anggota


def _get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DATABASE_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


# ══════════════════════════════════════════════════════════════════════════════
# Inisialisasi
# ══════════════════════════════════════════════════════════════════════════════

def init_loan_db() -> None:
    """
    Buat tabel peminjaman jika belum ada.
    Dipanggil dari sqlite_db.init_db().
    """
    ddl = """
    CREATE TABLE IF NOT EXISTS peminjaman (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        barcode_anggota     TEXT    NOT NULL,
        nama_anggota        TEXT    NOT NULL,
        kode_buku           TEXT    NOT NULL,
        judul_buku          TEXT    NOT NULL,
        tanggal_pinjam      DATE    NOT NULL,
        tanggal_kembali_rencana  DATE NOT NULL,
        tanggal_kembali_aktual   DATE,
        status              TEXT    NOT NULL DEFAULT 'dipinjam',
        denda               INTEGER NOT NULL DEFAULT 0,
        petugas             TEXT    NOT NULL DEFAULT '',
        catatan             TEXT    NOT NULL DEFAULT ''
    );

    CREATE INDEX IF NOT EXISTS idx_loan_anggota ON peminjaman (barcode_anggota);
    CREATE INDEX IF NOT EXISTS idx_loan_buku    ON peminjaman (kode_buku);
    CREATE INDEX IF NOT EXISTS idx_loan_status  ON peminjaman (status);
    CREATE INDEX IF NOT EXISTS idx_loan_tgl     ON peminjaman (tanggal_pinjam);
    """
    try:
        with _get_connection() as conn:
            conn.executescript(ddl)
        logger.info("Tabel peminjaman diinisialisasi.")
    except sqlite3.Error as exc:
        logger.error("Gagal inisialisasi tabel peminjaman: %s", exc)
        raise


# ══════════════════════════════════════════════════════════════════════════════
# Operasi utama
# ══════════════════════════════════════════════════════════════════════════════

def borrow_book(
    barcode_anggota: str,
    nama_anggota: str,
    kode_buku: str,
    durasi_hari: int = DURASI_PINJAM,
    petugas: str = "",
    catatan: str = "",
) -> tuple[bool, str]:
    """
    Catat transaksi peminjaman baru.

    Validasi:
        - Buku tersedia (jumlah_tersedia > 0)
        - Anggota tidak melebihi MAX_PINJAM buku aktif
        - Anggota tidak sedang meminjam buku yang sama

    Returns:
        (True, id_peminjaman_str)  — berhasil
        (False, pesan_error)       — gagal
    """
    from database.book_db import get_book_by_kode

    barcode_anggota = barcode_anggota.strip().upper()
    kode_buku       = kode_buku.strip().upper()

    # ── Validasi buku ─────────────────────────────────────────────────────────
    book = get_book_by_kode(kode_buku)
    if not book:
        return False, f"Buku dengan kode '{kode_buku}' tidak ditemukan."

    judul_buku = book["judul"]

    if book["jumlah_tersedia"] <= 0:
        return False, (
            f"Buku '{judul_buku}' sudah habis dipinjam.\n"
            f"Semua {book['jumlah_eksemplar']} eksemplar sedang dipinjam."
        )

    try:
        with _get_connection() as conn:
            # ── Validasi anggota ──────────────────────────────────────────────
            aktif = conn.execute(
                "SELECT COUNT(*) FROM peminjaman "
                "WHERE barcode_anggota = ? AND status = 'dipinjam'",
                (barcode_anggota,),
            ).fetchone()[0]

            if aktif >= MAX_PINJAM:
                return False, (
                    f"Anggota sudah meminjam {aktif} buku (batas: {MAX_PINJAM}).\n"
                    "Kembalikan buku sebelum meminjam lagi."
                )

            sudah = conn.execute(
                "SELECT 1 FROM peminjaman "
                "WHERE barcode_anggota = ? AND kode_buku = ? AND status = 'dipinjam'",
                (barcode_anggota, kode_buku),
            ).fetchone()

            if sudah:
                return False, f"Anggota sudah meminjam buku '{judul_buku}' dan belum dikembalikan."

            # ── Insert transaksi ──────────────────────────────────────────────
            today    = date.today()
            due_date = today + timedelta(days=durasi_hari)

            cur = conn.execute(
                """
                INSERT INTO peminjaman
                    (barcode_anggota, nama_anggota, kode_buku, judul_buku,
                     tanggal_pinjam, tanggal_kembali_rencana, status, petugas, catatan)
                VALUES (?, ?, ?, ?, ?, ?, 'dipinjam', ?, ?)
                """,
                (barcode_anggota, nama_anggota, kode_buku, judul_buku,
                 today.isoformat(), due_date.isoformat(), petugas, catatan),
            )
            loan_id = cur.lastrowid

            # ── Kurangi stok tersedia ─────────────────────────────────────────
            conn.execute(
                "UPDATE buku SET jumlah_tersedia = jumlah_tersedia - 1 WHERE kode_buku = ?",
                (kode_buku,),
            )

        logger.info("Peminjaman #%d: %s meminjam '%s'", loan_id, nama_anggota, judul_buku)
        return True, str(loan_id)

    except sqlite3.Error as exc:
        logger.error("Gagal catat peminjaman: %s", exc)
        return False, str(exc)


def return_book(
    loan_id: int,
    catatan: str = "",
) -> tuple[bool, str, int]:
    """
    Catat pengembalian buku.

    Returns:
        (True,  pesan_sukses, denda_rupiah)   — berhasil
        (False, pesan_error,  0)              — gagal
    """
    try:
        with _get_connection() as conn:
            loan = conn.execute(
                "SELECT * FROM peminjaman WHERE id = ?", (loan_id,)
            ).fetchone()

            if not loan:
                return False, f"Data peminjaman ID {loan_id} tidak ditemukan.", 0

            if loan["status"] != "dipinjam":
                return False, (
                    f"Buku ini sudah dikembalikan pada "
                    f"{loan['tanggal_kembali_aktual']}."
                ), 0

            # ── Hitung denda ──────────────────────────────────────────────────
            today    = date.today()
            due_date = date.fromisoformat(loan["tanggal_kembali_rencana"])
            terlambat = max(0, (today - due_date).days)
            denda     = terlambat * DENDA_PER_HARI
            status    = "terlambat" if terlambat > 0 else "dikembalikan"

            conn.execute(
                """
                UPDATE peminjaman SET
                    tanggal_kembali_aktual = ?,
                    status  = ?,
                    denda   = ?,
                    catatan = ?
                WHERE id = ?
                """,
                (today.isoformat(), status, denda,
                 catatan or loan["catatan"], loan_id),
            )

            # ── Tambah kembali stok ───────────────────────────────────────────
            conn.execute(
                "UPDATE buku SET jumlah_tersedia = jumlah_tersedia + 1 WHERE kode_buku = ?",
                (loan["kode_buku"],),
            )

        pesan = (
            f"Buku '{loan['judul_buku']}' berhasil dikembalikan.\n"
            + (f"⚠ Terlambat {terlambat} hari — Denda: Rp {denda:,}" if denda else "✓ Tepat waktu, tidak ada denda.")
        )
        logger.info("Pengembalian #%d: denda Rp %d (%d hari terlambat)", loan_id, denda, terlambat)
        return True, pesan, denda

    except sqlite3.Error as exc:
        logger.error("Gagal catat pengembalian: %s", exc)
        return False, str(exc), 0


# ══════════════════════════════════════════════════════════════════════════════
# Query
# ══════════════════════════════════════════════════════════════════════════════

def get_active_loans() -> list[dict]:
    """Semua peminjaman yang belum dikembalikan, urut dari yang paling hampir jatuh tempo."""
    today = date.today().isoformat()
    sql = """
    SELECT
        p.*,
        CAST(julianday(?) - julianday(p.tanggal_kembali_rencana) AS INTEGER) AS hari_terlambat
    FROM peminjaman p
    WHERE p.status = 'dipinjam'
    ORDER BY p.tanggal_kembali_rencana ASC
    """
    try:
        with _get_connection() as conn:
            rows = conn.execute(sql, (today,)).fetchall()
        return [dict(r) for r in rows]
    except sqlite3.Error as exc:
        logger.error("Gagal ambil peminjaman aktif: %s", exc)
        return []


def get_overdue_loans() -> list[dict]:
    """Semua peminjaman yang sudah melewati tanggal kembali."""
    today = date.today().isoformat()
    sql = """
    SELECT
        p.*,
        CAST(julianday(?) - julianday(p.tanggal_kembali_rencana) AS INTEGER) AS hari_terlambat,
        CAST(julianday(?) - julianday(p.tanggal_kembali_rencana) AS INTEGER) * ? AS estimasi_denda
    FROM peminjaman p
    WHERE p.status = 'dipinjam' AND p.tanggal_kembali_rencana < ?
    ORDER BY p.tanggal_kembali_rencana ASC
    """
    try:
        with _get_connection() as conn:
            rows = conn.execute(sql, (today, today, DENDA_PER_HARI, today)).fetchall()
        return [dict(r) for r in rows]
    except sqlite3.Error as exc:
        logger.error("Gagal ambil peminjaman terlambat: %s", exc)
        return []


def get_loans_by_member(barcode_anggota: str) -> list[dict]:
    """Riwayat peminjaman satu anggota, terbaru dulu."""
    sql = """
    SELECT * FROM peminjaman
    WHERE barcode_anggota = ?
    ORDER BY tanggal_pinjam DESC
    """
    try:
        with _get_connection() as conn:
            rows = conn.execute(sql, (barcode_anggota.strip().upper(),)).fetchall()
        return [dict(r) for r in rows]
    except sqlite3.Error as exc:
        logger.error("Gagal ambil riwayat anggota: %s", exc)
        return []


def get_loans_by_book(kode_buku: str) -> list[dict]:
    """Riwayat peminjaman satu buku."""
    sql = """
    SELECT * FROM peminjaman
    WHERE kode_buku = ?
    ORDER BY tanggal_pinjam DESC
    """
    try:
        with _get_connection() as conn:
            rows = conn.execute(sql, (kode_buku.strip().upper(),)).fetchall()
        return [dict(r) for r in rows]
    except sqlite3.Error as exc:
        logger.error("Gagal ambil riwayat buku: %s", exc)
        return []


def search_loans(query: str, status_filter: str = "semua") -> list[dict]:
    """
    Cari transaksi berdasarkan nama anggota, barcode, kode buku, atau judul.
    status_filter: 'semua' | 'dipinjam' | 'dikembalikan' | 'terlambat'
    """
    q = f"%{query.strip()}%"
    today = date.today().isoformat()

    status_clause = "" if status_filter == "semua" else f"AND p.status = '{status_filter}'"

    sql = f"""
    SELECT
        p.*,
        CASE
            WHEN p.status = 'dipinjam' AND p.tanggal_kembali_rencana < ?
            THEN CAST(julianday(?) - julianday(p.tanggal_kembali_rencana) AS INTEGER)
            ELSE 0
        END AS hari_terlambat
    FROM peminjaman p
    WHERE (
        p.nama_anggota    LIKE ? COLLATE NOCASE OR
        p.barcode_anggota LIKE ? COLLATE NOCASE OR
        p.judul_buku      LIKE ? COLLATE NOCASE OR
        p.kode_buku       LIKE ? COLLATE NOCASE
    ) {status_clause}
    ORDER BY p.tanggal_pinjam DESC
    LIMIT 200
    """
    try:
        with _get_connection() as conn:
            rows = conn.execute(sql, (today, today, q, q, q, q)).fetchall()
        return [dict(r) for r in rows]
    except sqlite3.Error as exc:
        logger.error("Gagal cari peminjaman: %s", exc)
        return []


def get_loan_by_id(loan_id: int) -> Optional[dict]:
    """Ambil satu record peminjaman berdasarkan ID."""
    try:
        with _get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM peminjaman WHERE id = ?", (loan_id,)
            ).fetchone()
        return dict(row) if row else None
    except sqlite3.Error as exc:
        logger.error("Gagal ambil peminjaman by id: %s", exc)
        return None


def get_loan_stats() -> dict:
    """Stat ringkas: aktif, dikembalikan, terlambat, total denda terkumpul."""
    today = date.today().isoformat()
    sql = """
    SELECT
        COUNT(CASE WHEN status = 'dipinjam' THEN 1 END)                        AS aktif,
        COUNT(CASE WHEN status IN ('dikembalikan','terlambat') THEN 1 END)      AS selesai,
        COUNT(CASE WHEN status = 'dipinjam'
                    AND tanggal_kembali_rencana < ? THEN 1 END)                 AS terlambat,
        COALESCE(SUM(CASE WHEN status = 'terlambat' THEN denda ELSE 0 END), 0) AS total_denda
    FROM peminjaman
    """
    try:
        with _get_connection() as conn:
            row = conn.execute(sql, (today,)).fetchone()
        return {
            "aktif"      : row["aktif"]       or 0,
            "selesai"    : row["selesai"]     or 0,
            "terlambat"  : row["terlambat"]   or 0,
            "total_denda": row["total_denda"] or 0,
        }
    except sqlite3.Error as exc:
        logger.error("Gagal ambil statistik peminjaman: %s", exc)
        return {"aktif": 0, "selesai": 0, "terlambat": 0, "total_denda": 0}
