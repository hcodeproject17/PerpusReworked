"""
gui/splash_screen.py — Splash screen dengan progress tracking
Menampilkan loading progress yang mirror proses inisialisasi aplikasi.
"""

from PySide6.QtCore import Qt, QTimer, Signal as pyqtSignal
from PySide6.QtGui import QFont, QPainter, QColor, QBrush, QPen
from PySide6.QtWidgets import (
    QSplashScreen, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QProgressBar, QFrame
)
from typing import Optional


class SplashScreen(QSplashScreen):
    """Splash screen dengan progress bar dan status text."""

    finished = pyqtSignal()

    def __init__(self):
        # Create a widget for the splash content
        self._widget = QWidget()
        self._widget.setFixedSize(500, 320)
        self._widget.setStyleSheet("background-color: #F2EFE7;")

        super().__init__(self._widget.pixmap() if hasattr(self._widget, 'pixmap') else None)
        self.setPixmap(self._widget.grab())

        self._steps = []
        self._current_step = 0
        self._total_steps = 0

        self._build_ui()
        self._apply_style()

    def _build_ui(self):
        """Build splash screen UI."""
        layout = QVBoxLayout(self._widget)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)

        # App title
        self._title = QLabel("PerpusReworked")
        self._title.setObjectName("splashTitle")
        self._title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._title)

        # Version
        from config import APP_VERSION
        self._version = QLabel(f"Version {APP_VERSION}")
        self._version.setObjectName("splashVersion")
        self._version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._version)

        layout.addStretch()

        # Status text
        self._status = QLabel("Initializing...")
        self._status.setObjectName("splashStatus")
        self._status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status.setWordWrap(True)
        layout.addWidget(self._status)

        # Progress bar
        self._progress = QProgressBar()
        self._progress.setObjectName("splashProgress")
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setTextVisible(False)
        self._progress.setFixedHeight(8)
        layout.addWidget(self._progress)

        # Step counter
        self._step_label = QLabel("0 / 0")
        self._step_label.setObjectName("splashStepLabel")
        self._step_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._step_label)

        # Update splash pixmap
        self.setPixmap(self._widget.grab())

    def _apply_style(self):
        """Apply theme-based styling."""
        from theme import get_palette
        p = get_palette()

        self._widget.setStyleSheet(f"""
            QWidget {{
                background-color: #{p.bg};
            }}
            QLabel#splashTitle {{
                font-size: 28px;
                font-weight: 700;
                color: #{p.p1};
                background-color: transparent;
                letter-spacing: 1px;
            }}
            QLabel#splashVersion {{
                font-size: 12px;
                color: #{p.p2};
                background-color: transparent;
            }}
            QLabel#splashStatus {{
                font-size: 13px;
                color: #{p.text_secondary};
                background-color: transparent;
                margin: 8px 0px;
            }}
            QLabel#splashStepLabel {{
                font-size: 11px;
                color: #{p.p3};
                background-color: transparent;
            }}
            QProgressBar#splashProgress {{
                background-color: #{p.surface};
                border: 1px solid #{p.border};
                border-radius: 4px;
            }}
            QProgressBar#splashProgress::chunk {{
                background-color: #{p.p1};
                border-radius: 3px;
            }}
        """)

    def set_steps(self, steps: list[str]):
        """Set initialization steps to track."""
        self._steps = steps
        self._total_steps = len(steps)
        self._current_step = 0
        self._step_label.setText(f"0 / {self._total_steps}")
        self.setPixmap(self._widget.grab())

    def next_step(self, message: Optional[str] = None):
        """Advance to next step with optional custom message."""
        if self._current_step < self._total_steps:
            if message is None and self._current_step < len(self._steps):
                message = self._steps[self._current_step]
            self._current_step += 1

            # Update progress
            progress = int((self._current_step / self._total_steps) * 100)
            self._progress.setValue(progress)
            self._step_label.setText(f"{self._current_step} / {self._total_steps}")

            if message:
                self._status.setText(message)

            self.setPixmap(self._widget.grab())
            self.repaint()

            # Check if finished
            if self._current_step >= self._total_steps:
                QTimer.singleShot(500, self._on_finished)

    def _on_finished(self):
        """Called when all steps complete."""
        self._status.setText("Ready!")
        self._progress.setValue(100)
        self.setPixmap(self._widget.grab())
        self.finished.emit()

    def show_message(self, message: str):
        """Update status message without advancing step."""
        self._status.setText(message)
        self.setPixmap(self._widget.grab())
        self.repaint()


class SplashScreenManager:
    """Manager untuk splash screen dengan task tracking."""

    def __init__(self):
        self._splash: Optional[SplashScreen] = None
        self._tasks = []

    def create(self):
        """Create and show splash screen."""
        self._splash = SplashScreen()
        self._splash.show()
        return self._splash

    def add_task(self, name: str, func):
        """Add a task to execute."""
        self._tasks.append((name, func))

    def run_tasks(self):
        """Execute all tasks with progress updates."""
        if not self._splash:
            return

        # Set steps from task names
        steps = [name for name, _ in self._tasks]
        self._splash.set_steps(steps)

        # Execute tasks
        for i, (name, func) in enumerate(self._tasks):
            try:
                self._splash.next_step(name)
                func()
            except Exception as e:
                self._splash.show_message(f"Error: {name} - {str(e)}")
                raise

    def close(self):
        """Close splash screen."""
        if self._splash:
            self._splash.close()
            self._splash = None
