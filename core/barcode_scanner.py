"""
core/barcode_scanner.py — Deteksi barcode Code 128 dari frame OpenCV
dengan mekanisme debounce per barcode.
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Optional

import cv2
import numpy as np
from pyzbar import pyzbar

from config import BARCODE_DEBOUNCE_SECONDS, BARCODE_TYPE_FILTER

logger = logging.getLogger(__name__)


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
        self._type_filter = type_filter
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

        # Grayscale meningkatkan akurasi decode pyzbar
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        decoded = pyzbar.decode(gray)

        results: list[BarcodeResult] = []
        now = time.monotonic()

        for obj in decoded:
            barcode_type = obj.type
            if barcode_type != self._type_filter:
                continue

            try:
                barcode_data = obj.data.decode("utf-8").strip()
            except UnicodeDecodeError:
                logger.warning("Gagal decode barcode bytes: %s", obj.data)
                continue

            if not barcode_data:
                continue

            # Cek debounce
            last_time = self._last_seen.get(barcode_data, 0.0)
            if now - last_time < self._debounce:
                continue

            # Lolos semua filter
            self._last_seen[barcode_data] = now
            rect = obj.rect
            results.append(BarcodeResult(
                data=barcode_data,
                type=barcode_type,
                rect=(rect.left, rect.top, rect.width, rect.height),
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
