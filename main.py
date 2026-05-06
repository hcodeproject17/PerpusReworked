"""
main.py — Entry point PerpusReworked
"""

import logging
import sys
from datetime import datetime
from pathlib import Path

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont
from PySide6.QtCore import QTimer

from gui.camera_dialog import CameraDialog
from gui.main_window import MainWindow
from gui.splash_screen import SplashScreenManager
from theme import stylesheet
from config import APP_NAME, DATA_DIR
from database.sqlite_db import init_db
from database.excel_reader import load_members, backup_excel

# Setup logging with file handler
LOG_DIR = DATA_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

log_filename = LOG_DIR / f"perpus_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.FileHandler(log_filename, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)
logger.info(f"Log file: {log_filename}")


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setFont(QFont("Segoe UI", 10))

    # Terapkan tema di level app — berlaku ke semua window & dialog
    app.setStyleSheet(stylesheet())

    # Create and show splash screen
    splash_manager = SplashScreenManager()
    splash = splash_manager.create()

    # Add initialization tasks
    splash_manager.add_task("Memuat tema", lambda: None)  # Theme already loaded
    splash_manager.add_task("Inisialisasi database", init_db)
    splash_manager.add_task("Memuat data anggota", load_members)
    splash_manager.add_task("Backup data", backup_excel)

    # Run tasks with progress updates
    splash_manager.run_tasks()

    # Wait for splash to finish, then show camera dialog
    splash.finished.connect(lambda: _show_camera_dialog(app, splash_manager))
    sys.exit(app.exec())


def _show_camera_dialog(app, splash_manager):
    """Show camera dialog after splash screen finishes."""
    splash_manager.close()

    dialog = CameraDialog()
    if dialog.exec() != CameraDialog.DialogCode.Accepted:
        app.quit()
        return

    window = MainWindow(
        camera_index=dialog.selected_index,
        camera_url=dialog.selected_url,
    )
    window.showMaximized()


if __name__ == "__main__":
    main()