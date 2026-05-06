"""
core/camera_manager.py — Manager kamera dengan threaded VideoStream

Pola dari file lama user diadaptasi ke class-based + thread-safe:
- Thread kamera baca frame terus-menerus di background
- Main thread hanya ambil frame terbaru dari buffer (tidak blocking)
- Thread scanner terpisah untuk decode barcode (tidak ganggu display)
"""

import logging
import threading
from typing import Optional

import cv2
import numpy as np

from config import (
    CAMERA_SCAN_RANGE,
    CAMERA_FRAME_WIDTH,
    CAMERA_FRAME_HEIGHT,
    CAMERA_FPS,
)

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# VideoStream — thread baca frame terus-menerus (dari pola file lama user)
# ══════════════════════════════════════════════════════════════════════════════

class VideoStream:
    """
    Baca frame kamera di background thread secara terus-menerus.
    Main thread hanya ambil frame terbaru — tidak pernah blocking di cap.read().

    Ini yang membuat display jauh lebih responsif dibanding memanggil
    cap.read() langsung dari QTimer di main thread.
    """

    def __init__(self, src: int | str) -> None:
        if isinstance(src, int):
            self._cap = cv2.VideoCapture(src, cv2.CAP_DSHOW)
        else:
            self._cap = cv2.VideoCapture(src)

        # Atur properti kamera
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH,  CAMERA_FRAME_WIDTH)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_FRAME_HEIGHT)
        self._cap.set(cv2.CAP_PROP_FPS,          CAMERA_FPS)
        self._cap.set(cv2.CAP_PROP_BUFFERSIZE,   1)   # buffer minimal

        # Baca frame pertama untuk inisialisasi
        self._grabbed, self._frame = self._cap.read()
        self._lock    = threading.Lock()
        self._stopped = False

    def start(self) -> "VideoStream":
        """Mulai thread baca frame, kembalikan self untuk chaining."""
        t = threading.Thread(target=self._update, daemon=True)
        t.start()
        return self

    def _update(self) -> None:
        """Loop baca frame — berjalan di background thread."""
        while not self._stopped:
            if self._cap.isOpened():
                grabbed, frame = self._cap.read()
                with self._lock:
                    self._grabbed = grabbed
                    self._frame   = frame
            # Tidak ada sleep — baca secepat mungkin
            # agar frame buffer selalu fresh

    def read(self) -> Optional[np.ndarray]:
        """
        Ambil frame terbaru (non-blocking, thread-safe).
        Returns None jika stream belum siap atau gagal.
        """
        with self._lock:
            if not self._grabbed or self._frame is None:
                return None
            return self._frame.copy()   # copy agar aman diproses di thread lain

    @property
    def is_opened(self) -> bool:
        return self._cap.isOpened() and not self._stopped

    def stop(self) -> None:
        """Hentikan thread dan lepas kamera."""
        self._stopped = True
        # Beri waktu thread selesai sebelum release
        self._cap.release()
        logger.info("VideoStream dihentikan.")

    def __del__(self) -> None:
        self.stop()


# ══════════════════════════════════════════════════════════════════════════════
# CameraManager — wrapper VideoStream untuk integrasi dengan GUI
# ══════════════════════════════════════════════════════════════════════════════

class CameraManager:
    """
    Kelola VideoStream (webcam atau IP stream).

    Penggunaan:
        cam = CameraManager()
        cam.connect(0)           # atau cam.connect_ip("rtsp://...")
        frame = cam.read_frame() # non-blocking, selalu frame terbaru
        cam.release()
    """

    def __init__(self) -> None:
        self._stream: Optional[VideoStream] = None
        self._source: Optional[int | str]   = None

    # ── Deteksi kamera tersedia ───────────────────────────────────────────────

    @staticmethod
    def list_available_cameras() -> list[int]:
        """Scan indeks kamera 0 hingga CAMERA_SCAN_RANGE-1."""
        available: list[int] = []
        for index in range(CAMERA_SCAN_RANGE):
            cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
            if cap.isOpened():
                ret, _ = cap.read()
                if ret:
                    available.append(index)
            cap.release()
        logger.info("Kamera tersedia: %s", available)
        return available

    # ── Koneksi ──────────────────────────────────────────────────────────────

    def connect(self, camera_index: int) -> bool:
        """Buka webcam lokal dan mulai VideoStream thread."""
        self.release()
        try:
            stream = VideoStream(camera_index).start()
            # Cek apakah stream berhasil dapat frame pertama
            if not stream.is_opened:
                stream.stop()
                logger.error("Gagal membuka webcam indeks %d", camera_index)
                return False
            self._stream = stream
            self._source = camera_index
            logger.info("Webcam terhubung: indeks %d", camera_index)
            return True
        except Exception as exc:
            logger.error("Error koneksi webcam: %s", exc)
            return False

    def connect_ip(self, url: str) -> bool:
        """Buka IP camera stream dan mulai VideoStream thread."""
        self.release()
        try:
            stream = VideoStream(url).start()
            if not stream.is_opened:
                stream.stop()
                logger.error("Gagal membuka IP camera: %s", url)
                return False
            self._stream = stream
            self._source = url
            logger.info("IP camera terhubung: %s", url)
            return True
        except Exception as exc:
            logger.error("Error koneksi IP camera: %s", exc)
            return False

    def reconnect(self) -> bool:
        """Sambungkan ulang ke sumber terakhir."""
        if self._source is None:
            return False
        logger.info("Reconnect ke: %s", self._source)
        if isinstance(self._source, int):
            return self.connect(self._source)
        return self.connect_ip(self._source)

    # ── Baca frame ───────────────────────────────────────────────────────────

    def read_frame(self) -> Optional[np.ndarray]:
        """
        Ambil frame terbaru dari buffer VideoStream (non-blocking).
        Frame selalu fresh karena background thread baca terus-menerus.
        """
        if self._stream is None:
            return None
        return self._stream.read()

    # ── Status ───────────────────────────────────────────────────────────────

    @property
    def is_connected(self) -> bool:
        return self._stream is not None and self._stream.is_opened

    @property
    def source(self) -> Optional[int | str]:
        return self._source

    # ── Lepas resource ────────────────────────────────────────────────────────

    def release(self) -> None:
        if self._stream is not None:
            self._stream.stop()
            self._stream = None
            logger.info("CameraManager: stream dilepas.")

    def __del__(self) -> None:
        self.release()


# ══════════════════════════════════════════════════════════════════════════════
# ScannerThread — decode barcode di thread terpisah (tidak ganggu display)
# ══════════════════════════════════════════════════════════════════════════════

class ScannerThread(threading.Thread):
    """
    Thread khusus untuk scan barcode.
    Mengambil frame dari CameraManager dan memanggil callback saat barcode terdeteksi.

    Dipisahkan dari display thread agar:
    - Display tetap smooth meski decode barcode butuh waktu
    - Barcode scan tidak terpengaruh oleh kecepatan render GUI
    """

    def __init__(
        self,
        camera: CameraManager,
        on_barcode,          # callback(barcode_data: str)
        on_frame_ready,      # callback(frame: np.ndarray) untuk display
        scan_interval: float = 0.05,   # detik antar scan (20 scan/detik)
    ) -> None:
        super().__init__(daemon=True)
        self._camera        = camera
        self._on_barcode    = on_barcode
        self._on_frame_ready = on_frame_ready
        self._scan_interval = scan_interval
        self._stopped       = threading.Event()

        # Import di sini agar tidak circular
        from core.barcode_scanner import BarcodeScanner
        self._scanner = BarcodeScanner()

    def run(self) -> None:
        import time
        while not self._stopped.is_set():
            frame = self._camera.read_frame()
            if frame is not None:
                # Scan barcode
                results = self._scanner.scan_frame(frame)
                for bc in results:
                    self._on_barcode(bc.data)

                # Gambar overlay jika ada barcode
                if results:
                    frame = self._scanner.draw_overlay(frame, results)

                # Kirim frame ke callback display
                self._on_frame_ready(frame)

            self._stopped.wait(self._scan_interval)

    def stop(self) -> None:
        self._stopped.set()