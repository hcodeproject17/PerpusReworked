"""
database/excel_reader.py — Handler baca data anggota dari .xlsx
Menggunakan openpyxl langsung (tanpa pandas) agar build .exe lebih ringan.
"""

import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

import openpyxl

from config import (
    MEMBER_EXCEL_PATH,
    BACKUP_DIR,
    EXCEL_COL_BARCODE,
    EXCEL_COL_NAME,
)

logger = logging.getLogger(__name__)

# Cache sederhana: (path, mtime) → list[dict]
_cache: dict = {}


def _load_raw() -> list[dict]:
    """
    Baca seluruh baris dari anggota.xlsx.
    Hasil di-cache berdasarkan waktu modifikasi file agar tidak baca ulang
    setiap kali ada scan barcode.

    Returns:
        list of dict dengan key sesuai header kolom Excel
    Raises:
        FileNotFoundError : jika file Excel tidak ditemukan
        ValueError        : jika kolom wajib tidak ada
    """
    path = MEMBER_EXCEL_PATH

    if not path.exists():
        raise FileNotFoundError(f"File anggota tidak ditemukan: {path}")

    mtime = path.stat().st_mtime

    # Kembalikan cache jika file belum berubah
    if _cache.get("mtime") == mtime:
        return _cache["data"]

    wb = openpyxl.load_workbook(str(path), read_only=True, data_only=True)
    ws = wb.active

    # Baca header dari baris pertama
    headers = [str(cell.value).strip() if cell.value is not None else "" for cell in next(ws.iter_rows(min_row=1, max_row=1))]

    # Validasi kolom wajib
    for required in (EXCEL_COL_BARCODE, EXCEL_COL_NAME):
        if required not in headers:
            wb.close()
            raise ValueError(
                f"Kolom '{required}' tidak ditemukan di {path.name}. "
                f"Kolom tersedia: {headers}"
            )

    # Baca semua baris data
    members: list[dict] = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        record = dict(zip(headers, row))

        # Skip baris kosong
        barcode = record.get(EXCEL_COL_BARCODE)
        nama    = record.get(EXCEL_COL_NAME)
        if not barcode or not nama:
            continue

        record[EXCEL_COL_BARCODE] = str(barcode).strip()
        record[EXCEL_COL_NAME]    = str(nama).strip()
        members.append(record)

    wb.close()

    # Simpan ke cache
    _cache["mtime"] = mtime
    _cache["data"]  = members

    logger.info("Excel dimuat: %d anggota dari %s", len(members), path.name)
    return members


def load_members() -> list[dict]:
    """
    Kembalikan semua data anggota.

    Returns:
        list of dict — bisa kosong jika file kosong
    Raises:
        FileNotFoundError, ValueError (diteruskan dari _load_raw)
    """
    return _load_raw()

def read_source_excel(path: str | Path) -> list[dict]:
    """
    Baca file Excel sumber untuk generate kartu massal.
    Kolom wajib: 'Nama'
    """
    from pathlib import Path as _Path
    path = _Path(path)
    if not path.exists():
        raise FileNotFoundError(f"File tidak ditemukan: {path}")

    wb = openpyxl.load_workbook(str(path), read_only=True, data_only=True)
    ws = wb.active
    headers = [str(c.value).strip() if c.value else "" for c in next(ws.iter_rows(max_row=1))]

    if "Nama" not in headers:
        wb.close()
        raise ValueError(f"Kolom 'Nama' tidak ditemukan. Kolom tersedia: {headers}")

    members = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        rec = dict(zip(headers, row))
        nama = str(rec.get("Nama", "")).strip()
        if not nama or nama.lower() == "none":
            continue
        rec["Nama"] = nama
        members.append(rec)

    wb.close()
    return members

def find_by_barcode(barcode_id: str) -> Optional[dict]:
    """
    Cari anggota berdasarkan ID Barcode (exact match, case-insensitive).

    Returns:
        dict anggota jika ditemukan, None jika tidak
    """
    target = barcode_id.strip().upper()
    for member in _load_raw():
        if member[EXCEL_COL_BARCODE].upper() == target:
            return member
    return None


def find_by_name(name: str) -> list[dict]:
    """
    Cari anggota berdasarkan nama (partial match, case-insensitive).

    Returns:
        list of dict — bisa kosong
    """
    query = name.strip().lower()
    return [
        m for m in _load_raw()
        if query in m[EXCEL_COL_NAME].lower()
    ]


def search(query: str) -> list[dict]:
    """
    Cari anggota berdasarkan barcode ATAU nama (untuk search box GUI).
    Prioritas: exact barcode match dulu, lalu partial name match.

    Returns:
        list of dict — bisa kosong
    """
    query = query.strip()
    if not query:
        return []

    # Coba exact barcode dulu
    by_barcode = find_by_barcode(query)
    if by_barcode:
        return [by_barcode]

    # Fallback ke partial name
    return find_by_name(query)


def backup_excel() -> Optional[Path]:
    """
    Buat salinan anggota.xlsx ke folder backup dengan timestamp.
    Dipanggil saat startup aplikasi.

    Returns:
        Path file backup jika berhasil, None jika gagal
    """
    src = MEMBER_EXCEL_PATH
    if not src.exists():
        logger.warning("Backup dibatalkan: file sumber tidak ada.")
        return None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dst = BACKUP_DIR / f"anggota_backup_{timestamp}.xlsx"

    try:
        shutil.copy2(str(src), str(dst))
        logger.info("Backup Excel berhasil: %s", dst.name)
        return dst
    except OSError as exc:
        logger.error("Gagal backup Excel: %s", exc)
        return None


def invalidate_cache() -> None:
    """
    Paksa reload Excel pada akses berikutnya.
    Berguna jika file Excel diperbarui saat aplikasi berjalan.
    """
    _cache.clear()
    logger.debug("Cache Excel dikosongkan.")
