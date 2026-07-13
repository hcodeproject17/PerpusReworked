"""
core/barcode_scanner.py — Deteksi barcode/QR dari frame OpenCV
dengan mekanisme debounce per kode.

Menggunakan zxing-cpp (bindings Python untuk pustaka C++ ZXing) sebagai
mesin decode. Dipilih menggantikan pyzbar karena zxing-cpp adalah wheel
mandiri (tidak butuh DLL zbar eksternal seperti pyzbar di Windows),
lebih cepat, dan mendukung lebih banyak format barcode/QR.

Default BARCODE_TYPE_FILTER di config.py adalah "QRCODE" saja — kartu
anggota dan label buku sama-sama QR Code sekarang. Format lain tetap bisa
diaktifkan lewat daftar dipisah koma (mis. "CODE128,QRCODE") kalau suatu
saat perlu baca barcode linear juga (mis. ISBN cetakan penerbit).
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Optional

import cv2
import numpy as np
import zxingcpp

from config import BARCODE_DEBOUNCE_SECONDS, BARCODE_TYPE_FILTER

logger = logging.getLogger(__name__)

# Pemetaan nama filter tipe (gaya pyzbar, mis. "CODE128") ke enum
# zxingcpp.BarcodeFormat. Dipakai baik untuk membatasi format yang
# dicari (lebih cepat) maupun untuk mencocokkan hasil decode.
_FORMAT_MAP: dict[str, "zxingcpp.BarcodeFormat"] = {
    "CODE128": zxingcpp.BarcodeFormat.Code128,
    "CODE39": zxingcpp.BarcodeFormat.Code39,
    "CODE93": zxingcpp.BarcodeFormat.Code93,
    "CODABAR": zxingcpp.BarcodeFormat.Codabar,
    "EAN13": zxingcpp.BarcodeFormat.EAN13,
    "EAN8": zxingcpp.BarcodeFormat.EAN8,
    "UPCA": zxingcpp.BarcodeFormat.UPCA,
    "UPCE": zxingcpp.BarcodeFormat.UPCE,
    "ITF": zxingcpp.BarcodeFormat.ITF,
    "QRCODE": zxingcpp.BarcodeFormat.QRCode,
    "DATAMATRIX": zxingcpp.BarcodeFormat.DataMatrix,
    "PDF417": zxingcpp.BarcodeFormat.PDF417,
    "AZTEC": zxingcpp.BarcodeFormat.Aztec,
}


def _normalize_format_name(fmt: "zxingcpp.BarcodeFormat") -> str:
    """Ubah enum format zxingcpp (mis. 'Code 128') menjadi string
    gaya pyzbar tanpa spasi (mis. 'CODE128') agar konsisten dengan
    nilai BARCODE_TYPE_FILTER di config.py."""
    return str(fmt).upper().replace(" ", "")


def _bbox_from_position(position: "zxingcpp.Position") -> tuple[int, int, int, int]:
    """zxing-cpp mengembalikan 4 titik sudut (bisa miring/rotasi),
    sedangkan pyzbar mengembalikan rect axis-aligned langsung.
    Fungsi ini menghitung bounding box axis-aligned dari 4 titik
    tersebut supaya draw_overlay() tetap kompatibel."""
    xs = (position.top_left.x, position.top_right.x,
          position.bottom_right.x, position.bottom_left.x)
    ys = (position.top_left.y, position.top_right.y,
          position.bottom_right.y, position.bottom_left.y)
    x_min, x_max = min(xs), max(xs)
    y_min, y_max = min(ys), max(ys)
    return (x_min, y_min, x_max - x_min, y_max - y_min)


@dataclass
class BarcodeResult:
    """Data satu barcode yang berhasil terbaca."""
    data: str                    # String isi barcode
    type: str                    # Tipe barcode (misal "CODE128")
    rect: tuple[int, int, int, int]  # (x, y, w, h) bounding box


class BarcodeScanner:
    """
    Scanner barcode dengan debounce per barcode_id.

    Debounce mencegah scan yang sama tercatat berkali-kali
    dalam satu rentang waktu pendek (default 2 detik).
    """

    def __init__(
        self,
        debounce_seconds: float = BARCODE_DEBOUNCE_SECONDS,
        type_filter: str = BARCODE_TYPE_FILTER,
    ) -> None:
        self._debounce = debounce_seconds

        # Pecah filter dipisah koma, mis. "CODE128,QRCODE" → {"CODE128", "QRCODE"}
        # Backward-compatible: filter tunggal seperti dulu ("CODE128") tetap jalan.
        raw_names = [t.strip().upper().replace(" ", "") for t in type_filter.split(",")]
        raw_names = [t for t in raw_names if t]

        self._type_filter_set: set[str] = set(raw_names)

        # Gabungkan semua enum format yang dikenali dengan OR bitwise,
        # supaya read_barcodes() mencari SEMUA format yang diminta sekaligus
        # (bukan cuma satu) — ini yang tadinya jadi penyebab QR tidak pernah
        # terdeteksi saat filter cuma "CODE128".
        combined_format = None
        for name in raw_names:
            fmt = _FORMAT_MAP.get(name)
            if fmt is None:
                logger.warning(
                    "Tipe barcode filter '%s' tidak dikenal zxing-cpp, diabaikan.", name,
                )
                continue
            combined_format = fmt if combined_format is None else (combined_format | fmt)

        if combined_format is None:
            logger.warning(
                "Tidak ada tipe filter valid dari '%s', mencari semua format.", type_filter,
            )
            combined_format = zxingcpp.BarcodeFormat.All
            self._type_filter_set = set()  # kosong = terima semua tipe saat dicocokkan

        self._zxing_format = combined_format

        # barcode_data → timestamp terakhir terbaca
        self._last_seen: dict[str, float] = {}

    # ── Scan frame ───────────────────────────────────────────────────────────

    def scan_frame(self, frame: np.ndarray) -> list[BarcodeResult]:
        """
        Scan satu frame dan kembalikan barcode yang:
        1. Tipenya sesuai filter (CODE128)
        2. Belum dalam periode debounce

        Args:
            frame: numpy array BGR dari OpenCV

        Returns:
            list BarcodeResult — kosong jika tidak ada yang lolos filter/debounce
        """
        if frame is None:
            return []

        # Grayscale meningkatkan akurasi & kecepatan decode
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        try:
            decoded = zxingcpp.read_barcodes(gray, formats=self._zxing_format)
        except Exception:
            logger.exception("zxing-cpp gagal membaca frame")
            return []

        results: list[BarcodeResult] = []
        now = time.monotonic()

        for obj in decoded:
            if not obj.valid:
                continue

            barcode_type = _normalize_format_name(obj.format)
            if self._type_filter_set and barcode_type not in self._type_filter_set:
                continue

            barcode_data = (obj.text or "").strip()
            if not barcode_data:
                continue

            # Cek debounce
            last_time = self._last_seen.get(barcode_data, 0.0)
            if now - last_time < self._debounce:
                continue

            # Lolos semua filter
            self._last_seen[barcode_data] = now
            rect = _bbox_from_position(obj.position)
            results.append(BarcodeResult(
                data=barcode_data,
                type=barcode_type,
                rect=rect,
            ))
            logger.debug("Barcode terbaca: %s (%s)", barcode_data, barcode_type)

        return results

    # ── Utilitas ─────────────────────────────────────────────────────────────

    def draw_overlay(self, frame: np.ndarray, results: list[BarcodeResult]) -> np.ndarray:
        """
        Gambar bounding box dan label pada frame untuk setiap barcode hasil scan.
        Berguna untuk visual debug di panel kamera.

        Args:
            frame  : frame BGR asli
            results: hasil dari scan_frame()

        Returns:
            frame dengan overlay (modifikasi in-place sekaligus dikembalikan)
        """
        for bc in results:
            x, y, w, h = bc.rect
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.putText(
                frame,
                bc.data,
                (x, y - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 0),
                2,
                cv2.LINE_AA,
            )
        return frame

    def reset_debounce(self, barcode_data: Optional[str] = None) -> None:
        """
        Reset debounce.

        Args:
            barcode_data: Reset hanya barcode tertentu.
                          None = reset semua (berguna saat session baru).
        """
        if barcode_data:
            self._last_seen.pop(barcode_data, None)
        else:
            self._last_seen.clear()