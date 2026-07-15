"""
core/label_utils.py — Helper bersama untuk generator label docx (kartu
anggota & label buku): styling cell tabel Word dan generate QR Code PNG.
"""

from pathlib import Path

import qrcode
from qrcode.constants import ERROR_CORRECT_M
from docx.oxml.ns import qn
from docx.oxml import OxmlElement


def set_cell_border(cell, sides=None, color="AAAAAA", sz="6") -> None:
    """Set border pada cell tabel Word."""
    if sides is None:
        sides = ["top", "left", "bottom", "right"]
    tcPr = cell._tc.get_or_add_tcPr()
    tcBorders = OxmlElement("w:tcBorders")
    for side in sides:
        el = OxmlElement(f"w:{side}")
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), sz)
        el.set(qn("w:space"), "0")
        el.set(qn("w:color"), color)
        tcBorders.append(el)
    tcPr.append(tcBorders)


def set_cell_bg(cell, hex_color: str) -> None:
    """Set background warna cell."""
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color)
    tcPr.append(shd)


def set_cell_margin(cell, top=60, bottom=60, left=80, right=80) -> None:
    """Set margin dalam cell (dalam twips, 1cm ≈ 567 twips)."""
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = OxmlElement("w:tcMar")
    for side, val in [("top", top), ("bottom", bottom), ("left", left), ("right", right)]:
        el = OxmlElement(f"w:{side}")
        el.set(qn("w:w"), str(val))
        el.set(qn("w:type"), "dxa")
        tcMar.append(el)
    tcPr.append(tcMar)


def make_qr_png(data: str, out_path: Path) -> None:
    """
    Generate satu QR Code PNG ke out_path.

    Parameter (box_size=15, border=3, ERROR_CORRECT_M) dipakai sama untuk
    kartu anggota dan label buku: toleransi ~15% kerusakan (noda/lipatan)
    dan quiet zone wajib agar mudah discan.
    """
    qr = qrcode.QRCode(
        version=None,
        error_correction=ERROR_CORRECT_M,
        box_size=15,
        border=3,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    img.save(str(out_path))
