"""
gui/camera_dialog.py — Dialog pemilihan sumber kamera
Ditampilkan satu kali saat startup sebelum masuk ke dashboard utama.
"""

import logging
from typing import Optional

import cv2
import numpy as np
from PySide6.QtCore import Signal as pyqtSignal
from PySide6.QtCore import Qt, QThread, QTimer
from PySide6.QtGui import QImage, QPixmap, QFont, QColor, QPalette
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QRadioButton,
    QLineEdit,
    QPushButton,
    QButtonGroup,
    QGroupBox,
    QSizePolicy,
    QMessageBox,
    QFrame,
    QSpacerItem,
)

from core.camera_manager import CameraManager
from config import APP_NAME

logger = logging.getLogger(__name__)


# ── Worker thread untuk scan kamera tersedia ──────────────────────────────────

class CameraScanWorker(QThread):
    """Scan kamera di background agar GUI tidak freeze."""
    finished = pyqtSignal(list)   # list[int] indeks kamera tersedia

    def run(self) -> None:
        available = CameraManager.list_available_cameras()
        self.finished.emit(available)


# ── Dialog utama ──────────────────────────────────────────────────────────────

class CameraDialog(QDialog):
    """
    Dialog pemilihan sumber kamera.

    Setelah user mengklik "Mulai", akses hasil lewat:
        dialog.selected_index  — int (indeks webcam) atau None
        dialog.selected_url    — str (URL IP cam) atau None
        dialog.use_ip          — bool
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"{APP_NAME} — Pilih Kamera")
        self.setMinimumWidth(520)
        self.setModal(True)

        # Hasil pilihan user
        self.selected_index: Optional[int] = None
        self.selected_url:   Optional[str] = None
        self.use_ip:         bool          = False

        # Objek kamera untuk preview
        self._preview_cap: Optional[cv2.VideoCapture] = None
        self._preview_timer = QTimer(self)
        self._preview_timer.timeout.connect(self._update_preview)

        self._build_ui()
        self._start_camera_scan()

    # ── Build UI ──────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(16)
        root.setContentsMargins(24, 24, 24, 24)

        # Judul
        title = QLabel("Pilih Sumber Kamera")
        title.setObjectName("dialogTitle")
        root.addWidget(title)

        # Garis pemisah
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setObjectName("separator")
        root.addWidget(line)

        # ── Grup: Webcam lokal ────────────────────────────────────────────────
        webcam_group = QGroupBox("Webcam / Kamera Lokal")
        webcam_group.setObjectName("camGroup")
        webcam_layout = QVBoxLayout(webcam_group)
        webcam_layout.setSpacing(10)

        row_webcam = QHBoxLayout()

        self._radio_webcam = QRadioButton("Gunakan webcam indeks:")
        self._radio_webcam.setChecked(True)
        self._radio_webcam.toggled.connect(self._on_mode_changed)
        row_webcam.addWidget(self._radio_webcam)

        self._combo_cameras = QComboBox()
        self._combo_cameras.setMinimumWidth(160)
        self._combo_cameras.addItem("Memindai kamera...")
        self._combo_cameras.setEnabled(False)
        row_webcam.addWidget(self._combo_cameras)
        row_webcam.addStretch()

        webcam_layout.addLayout(row_webcam)

        self._lbl_scan_status = QLabel("🔍 Memindai kamera yang tersedia...")
        self._lbl_scan_status.setObjectName("statusSmall")
        webcam_layout.addWidget(self._lbl_scan_status)

        root.addWidget(webcam_group)

        # ── Grup: IP Camera ───────────────────────────────────────────────────
        ip_group = QGroupBox("IP Camera / Stream URL")
        ip_group.setObjectName("camGroup")
        ip_layout = QVBoxLayout(ip_group)
        ip_layout.setSpacing(10)

        self._radio_ip = QRadioButton("Gunakan IP camera:")
        self._radio_ip.toggled.connect(self._on_mode_changed)
        ip_layout.addWidget(self._radio_ip)

        self._input_url = QLineEdit()
        self._input_url.setPlaceholderText("contoh: rtsp://192.168.1.100:554/stream  atau  http://192.168.1.100:8080/video")
        self._input_url.setEnabled(False)
        ip_layout.addWidget(self._input_url)

        root.addWidget(ip_group)

        # ── Preview kamera ────────────────────────────────────────────────────
        preview_group = QGroupBox("Preview")
        preview_group.setObjectName("camGroup")
        preview_layout = QVBoxLayout(preview_group)

        self._lbl_preview = QLabel()
        self._lbl_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lbl_preview.setMinimumSize(320, 200)
        self._lbl_preview.setObjectName("previewLabel")
        self._lbl_preview.setText("Tekan \"Tes Koneksi\" untuk melihat preview")
        preview_layout.addWidget(self._lbl_preview)

        root.addWidget(preview_group)

        # ── Tombol bawah ──────────────────────────────────────────────────────
        btn_row = QHBoxLayout()

        self._btn_test = QPushButton("🔌  Tes Koneksi")
        self._btn_test.setObjectName("btnSecondary")
        self._btn_test.clicked.connect(self._test_connection)
        btn_row.addWidget(self._btn_test)

        btn_row.addStretch()

        self._btn_cancel = QPushButton("Batal")
        self._btn_cancel.setObjectName("btnCancel")
        self._btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(self._btn_cancel)

        self._btn_start = QPushButton("▶  Mulai")
        self._btn_start.setObjectName("btnPrimary")
        self._btn_start.setEnabled(False)
        self._btn_start.clicked.connect(self._on_start)
        btn_row.addWidget(self._btn_start)

        root.addLayout(btn_row)

    # ── Style ─────────────────────────────────────────────────────────────────


    # ── Scan kamera ───────────────────────────────────────────────────────────

    def _start_camera_scan(self) -> None:
        self._scan_worker = CameraScanWorker()
        self._scan_worker.finished.connect(self._on_cameras_found)
        self._scan_worker.start()

    def _on_cameras_found(self, available: list[int]) -> None:
        self._combo_cameras.clear()
        if not available:
            self._combo_cameras.addItem("Tidak ada kamera ditemukan")
            self._lbl_scan_status.setText("⚠️  Tidak ada webcam yang terdeteksi.")
        else:
            for idx in available:
                self._combo_cameras.addItem(f"Kamera {idx}", userData=idx)
            self._combo_cameras.setEnabled(True)
            self._btn_start.setEnabled(True)
            self._lbl_scan_status.setText(f"✅  {len(available)} kamera ditemukan.")
        logger.info("Scan selesai: %s", available)

    # ── Mode toggle ───────────────────────────────────────────────────────────

    def _on_mode_changed(self) -> None:
        is_ip = self._radio_ip.isChecked()
        self._combo_cameras.setEnabled(not is_ip and self._combo_cameras.count() > 0)
        self._input_url.setEnabled(is_ip)
        self._btn_start.setEnabled(True)
        self._stop_preview()
        self._lbl_preview.setText("Tekan \"Tes Koneksi\" untuk melihat preview")

    # ── Test koneksi & preview ────────────────────────────────────────────────

    def _test_connection(self) -> None:
        self._stop_preview()
        cam = CameraManager()

        if self._radio_ip.isChecked():
            url = self._input_url.text().strip()
            if not url:
                QMessageBox.warning(self, "URL Kosong", "Masukkan URL IP camera terlebih dahulu.")
                return
            ok = cam.connect_ip(url)
        else:
            idx = self._combo_cameras.currentData()
            if idx is None:
                return
            ok = cam.connect(idx)

        if not ok:
            self._lbl_preview.setText("❌  Gagal terhubung ke kamera.")
            QMessageBox.critical(self, "Koneksi Gagal", "Tidak dapat membuka kamera. Periksa kembali pilihan atau URL.")
            return

        self._preview_cap = cam
        self._preview_timer.start(33)   # ~30fps

    def _update_preview(self) -> None:
        if self._preview_cap is None:
            return
        frame = self._preview_cap.read_frame()
        if frame is None:
            self._lbl_preview.setText("❌  Kehilangan sinyal kamera.")
            self._stop_preview()
            return
        self._show_frame(frame)

    def _show_frame(self, frame: np.ndarray) -> None:
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        qimg = QImage(rgb.data, w, h, ch * w, QImage.Format.Format_RGB888)
        pix = QPixmap.fromImage(qimg).scaled(
            self._lbl_preview.width(),
            self._lbl_preview.height(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._lbl_preview.setPixmap(pix)

    def _stop_preview(self) -> None:
        self._preview_timer.stop()
        if self._preview_cap is not None:
            self._preview_cap.release()
            self._preview_cap = None

    # ── Mulai ─────────────────────────────────────────────────────────────────

    def _on_start(self) -> None:
        self._stop_preview()
        if self._radio_ip.isChecked():
            url = self._input_url.text().strip()
            if not url:
                QMessageBox.warning(self, "URL Kosong", "Masukkan URL IP camera terlebih dahulu.")
                return
            self.use_ip       = True
            self.selected_url = url
        else:
            idx = self._combo_cameras.currentData()
            if idx is None:
                QMessageBox.warning(self, "Tidak Ada Kamera", "Pilih kamera terlebih dahulu.")
                return
            self.use_ip           = False
            self.selected_index   = idx
        self.accept()

    # ── Cleanup ───────────────────────────────────────────────────────────────

    def closeEvent(self, event) -> None:
        self._stop_preview()
        super().closeEvent(event)

    def reject(self) -> None:
        self._stop_preview()
        super().reject()