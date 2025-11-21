# Xjustiz2PDF is a desktop application that converts German xJustiz 
# e‑files (E-Akte) into a single PDF document
# Copyright (C) 2025 Björn Seipel
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

# converter.py – Plattformunabhängige Konvertierung zu PDF
# - Unterstützt: Office (doc, docx, xls, xlsx, ppt, pptx, odt, ods, odp), txt, csv, xml, bilder (tiff, tif, jpg, jpeg, png)
# - Nutzt LibreOffice (wenn verfügbar) headless via --convert-to
# - Fallbacks: docx2pdf für DOCX; Pillow + fpdf2 für Bilder; fpdf2 für txt/csv/xml
# - 30 Sekunden Timeout pro Konvertierung
# - Robuste Fehlerbehandlung, Ubuntu-Font für generierte PDFs und Platzhalter

import os
import sys
import time
import shutil
import tempfile
import subprocess
import platform
from typing import Optional, Tuple

from .utils import debug

# Optionale Imports nur verwenden, wenn benötigt
try:
    from docx2pdf import convert as docx2pdf_convert  # Fallback für DOCX
    DOCX2PDF_AVAILABLE = True
except Exception:
    DOCX2PDF_AVAILABLE = False

try:
    from PIL import Image  # Fallback für Bilder
    PIL_AVAILABLE = True
except Exception:
    PIL_AVAILABLE = False

try:
    from fpdf import FPDF  # Generierung von PDFs für Text und Bilder
    FPDF_AVAILABLE = True
except Exception:
    FPDF_AVAILABLE = False

# --------- LibreOffice Detection ---------

def _detect_libreoffice() -> Optional[str]:
    """
    Liefert den Pfad zum LibreOffice/soffice-Executable, wenn vorhanden.
    - Cross-Platform: nutzt shutil.which
    - Unter Windows zusätzlich Registry-Check inkl. Subkeys (Versionen) und HKCU.
    """
    # 1. PATH-Check
    for name in ("soffice", "libreoffice"):
        path = shutil.which(name)
        if path:
            debug(f"[Converter] LibreOffice gefunden via PATH: {path}")
            return path

    # 2. Windows Registry-Check
    if platform.system() == "Windows":
        try:
            import winreg

            base_keys = [
                r"SOFTWARE\LibreOffice\UNO",
                r"SOFTWARE\LibreOffice\LibreOffice",
                r"SOFTWARE\WOW6432Node\LibreOffice\LibreOffice",
                r"SOFTWARE\The Document Foundation\LibreOffice",
                r"SOFTWARE\WOW6432Node\The Document Foundation\LibreOffice",
            ]

            def check_key(root, key):
                try:
                    with winreg.OpenKey(root, key) as k:
                        # Direktwerte prüfen
                        for value_name in ("Path", "InstallPath", "Default", ""):
                            try:
                                val, _ = winreg.QueryValueEx(k, value_name)
                                if isinstance(val, str) and val:
                                    for candidate in (
                                        os.path.join(val, "program", "soffice.exe"),
                                        os.path.join(val, "soffice.exe"),
                                    ):
                                        if os.path.isfile(candidate):
                                            debug(f"[Converter] LibreOffice gefunden via Registry: {candidate}")
                                            return candidate
                            except OSError:
                                pass

                        # Subkeys (z. B. Versionsnummern) prüfen
                        i = 0
                        while True:
                            try:
                                subkey = winreg.EnumKey(k, i)
                                i += 1
                                candidate = check_key(root, key + "\\" + subkey)
                                if candidate:
                                    return candidate
                            except OSError:
                                break
                except OSError:
                    return None
                return None

            for root in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
                for key in base_keys:
                    candidate = check_key(root, key)
                    if candidate:
                        return candidate

        except Exception as e:
            debug(f"[Converter] Registry-Check für LibreOffice fehlgeschlagen: {e}")

    debug("[Converter] LibreOffice nicht gefunden.")
    return None


# --------- Hilfsfunktionen ---------

def _with_timeout_subprocess(cmd: list, timeout: int, cwd: Optional[str] = None) -> Tuple[bool, Optional[str]]:
    """
    Führt einen Subprozess mit Timeout aus. Gibt (success, error_msg) zurück.
    """
    try:
        debug(f"[Converter] Starte Subprozess: {' '.join(cmd)} (timeout={timeout}s)")
        subprocess.run(cmd, check=True, timeout=timeout, cwd=cwd)
        return True, None
    except subprocess.TimeoutExpired:
        return False, "Timeout erreicht (30s)"
    except subprocess.CalledProcessError as e:
        return False, f"Konvertierung fehlgeschlagen: {e}"
    except Exception as e:
        return False, f"Unerwarteter Fehler: {e}"

def _fpdf_new_page_with_ubuntu(font_dir: str) -> FPDF:
    """
    Erstellt ein FPDF Objekt mit registriertem Ubuntu-Font.
    """
    if not FPDF_AVAILABLE:
        raise RuntimeError("FPDF nicht verfügbar")
    font_path = os.path.join(font_dir, "Ubuntu-R.ttf")
    if not os.path.isfile(font_path):
        raise RuntimeError(f"Ubuntu-Font nicht gefunden: {font_path}")
    pdf = FPDF(unit="pt", format="A4")
    pdf.add_page()
    pdf.add_font("Ubuntu", "", font_path)
    pdf.set_font("Ubuntu", "", 12)
    return pdf

def _fpdf_write_wrapped_text(pdf: FPDF, text: str, margin_left=50, margin_top=80, max_width=495, line_height=18):
    """
    Schreibt Text mit automatischem Zeilenumbruch in die PDF-Seite (A4, pt).
    """
    pdf.set_xy(margin_left, margin_top)
    pdf.multi_cell(max_width, line_height, text)

def _write_placeholder_pdf(message: str, font_dir: str) -> str:
    """
    Erstellt eine Platzhalter-PDF mit Ubuntu-Font und Zeilenumbruch.
    """
    tmp_fd, tmp_path = tempfile.mkstemp(prefix="xmlpdf_", suffix="_placeholder.pdf")
    os.close(tmp_fd)
    try:
        pdf = _fpdf_new_page_with_ubuntu(font_dir)
        _fpdf_write_wrapped_text(pdf, message)
        pdf.output(tmp_path)
        debug(f"[Converter] Platzhalter-PDF erstellt: {tmp_path}")
        return tmp_path
    except Exception as e:
        debug(f"[Converter] Fehler beim Erstellen der Platzhalter-PDF: {e}")
        # Letzte Rettung: leere Datei schreiben
        with open(tmp_path, "wb") as f:
            f.write(b"%PDF-1.4\n%EOF")
        return tmp_path

# --------- Konvertierer ---------

SUPPORTED_OFFICE = {".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".odt", ".ods", ".odp"}
SUPPORTED_IMAGES = {".tiff", ".tif", ".jpg", ".jpeg", ".png"}
SUPPORTED_TEXT = {".txt", ".csv", ".xml"}

def convert_to_pdf(input_path: str, tmpdir: str, font_dir: str) -> Optional[str]:
    """
    Konvertiert die Datei zu PDF und gibt den Pfad zur erzeugten PDF zurück.
    - Nutzt LibreOffice, wenn möglich (Office-Formate).
    - Fallbacks entsprechend Dateityp.
    - Bei Fehlern oder nicht unterstützten Formaten: None zurückgeben.
    - 30 Sekunden Timeout pro Konvertierung.
    """
    if not os.path.isfile(input_path):
        debug(f"[Converter] Eingabedatei fehlt: {input_path}")
        return None

    ext = os.path.splitext(input_path)[1].lower()
    base_name = os.path.splitext(os.path.basename(input_path))[0]
    out_pdf = os.path.join(tmpdir, f"{base_name}.pdf")

    # 1) Office-Formate: zuerst LibreOffice
    if ext in SUPPORTED_OFFICE:
        lo = _detect_libreoffice()
        if lo:
            cmd = [lo, "--headless", "--convert-to", "pdf", "--outdir", tmpdir, input_path]
            success, err = _with_timeout_subprocess(cmd, timeout=30)
            if success and os.path.isfile(out_pdf):
                debug(f"[Converter] LibreOffice-Konvertierung erfolgreich: {out_pdf}")
                return out_pdf
            debug(f"[Converter] LibreOffice-Konvertierung fehlgeschlagen: {err}")
        # Fallback für DOCX mit docx2pdf
        if ext == ".docx" and DOCX2PDF_AVAILABLE:
            try:
                debug("[Converter] Versuche Fallback docx2pdf…")
                # docx2pdf erzeugt die Datei im Zielordner mit gleichem Namen
                docx2pdf_convert(input_path, tmpdir)
                if os.path.isfile(out_pdf):
                    return out_pdf
                else:
                    # manche Implementierungen rzeugen abweichende Namen
                    # Suche die zuletzt erzeugte PDF im tmpdir
                    pdf_files = [
                        os.path.join(tmpdir, f)
                        for f in os.listdir(tmpdir)
                        if f.lower().endswith(".pdf")
                    ]
                    if pdf_files:
                        newest_pdf = max(pdf_files, key=os.path.getmtime)
                        return newest_pdf
                debug("[Converter] docx2pdf erzeugte keine PDF.")
            except Exception as e:
                debug(f"[Converter] docx2pdf Fehler: {e}")
        debug("[Converter] Office-Datei konnte nicht konvertiert werden.")
        return None

    # 2) Bildformate: Pillow + FPDF
    if ext in SUPPORTED_IMAGES:
        if not (PIL_AVAILABLE and FPDF_AVAILABLE):
            debug("[Converter] Bild-Fallback nicht verfügbar (Pillow/FPDF fehlt).")
            return None
        try:
            img = Image.open(input_path)
            # Konvertiere in RGB für PDF
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            # Speichere temporäre JPEG/PNG falls nötig (FPDF kann direkt ein Bild einbetten)
            pdf = _fpdf_new_page_with_ubuntu(font_dir)
            # Ganzformatig einfügen: Seite A4 = 595x842 pt; wir nutzen 0-Margins und skalieren proportional
            page_w, page_h = 595, 842
            img_w, img_h = img.size
            # DPI-unabhängige Skalierung: wir rechnen Pixel auf Punkte proportional
            scale = min(page_w / img_w, page_h / img_h)
            draw_w, draw_h = img_w * scale, img_h * scale
            x = (page_w - draw_w) / 2
            y = (page_h - draw_h) / 2
            # Bild muss auf Disk, damit FPDF es laden kann
            tmp_img_fd, tmp_img_path = tempfile.mkstemp(prefix="xmlpdf_", suffix=".jpg")
            os.close(tmp_img_fd)
            img.save(tmp_img_path, "JPEG", quality=90)
            pdf.image(tmp_img_path, x=x, y=y, w=draw_w, h=draw_h)
            pdf.output(out_pdf)
            try:
                os.remove(tmp_img_path)
            except Exception:
                pass
            debug(f"[Converter] Bild zu PDF konvertiert: {out_pdf}")
            return out_pdf
        except Exception as e:
            debug(f"[Converter] Bild-Konvertierung fehlgeschlagen: {e}")
            return None

    # 3) Textbasierte Formate: FPDF MultiCell
    if ext in SUPPORTED_TEXT:
        if not FPDF_AVAILABLE:
            debug("[Converter] Text-Fallback nicht verfügbar (FPDF fehlt).")
            return None
        try:
            # Inhalte lesen (robust)
            try:
                with open(input_path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
            except UnicodeDecodeError:
                with open(input_path, "r", encoding="latin-1", errors="replace") as f:
                    content = f.read()
            # Einfache Überschrift und Inhalt
            pdf = _fpdf_new_page_with_ubuntu(font_dir)
            _fpdf_write_wrapped_text(pdf, f"Inhalt aus {os.path.basename(input_path)}:\n\n{content}")
            pdf.output(out_pdf)
            debug(f"[Converter] Textdatei zu PDF konvertiert: {out_pdf}")
            return out_pdf
        except Exception as e:
            debug(f"[Converter] Text-Konvertierung fehlgeschlagen: {e}")
            return None

    # Nicht unterstützter Typ
    debug(f"[Converter] Nicht unterstützte Erweiterung: {ext}")
    return None


def placeholder_for_unconvertible(input_path: Optional[str], reason: str, font_dir: str) -> str:
    """
    Erzeugt eine Platzhalter-PDF mit Ubuntu-Font, die informiert, dass Konvertierung nicht möglich war.
    """
    filename = os.path.basename(input_path or "")
    message = f"Datei {filename} konnte bei der Aktenerstellung nicht konvertiert werden.\n\nGrund: {reason}"
    return _write_placeholder_pdf(message, font_dir)
