"""
gui/widgets.py — Widget helper kecil yang dipakai lebih dari satu tab.
"""

from PySide6.QtWidgets import QLabel


def section_label(text: str) -> QLabel:
    """Label judul section dengan styling QSS 'analyticsSectionLabel'
    (dipakai bersama oleh tab analitik & peminjaman)."""
    lbl = QLabel(text)
    lbl.setObjectName("analyticsSectionLabel")
    return lbl
