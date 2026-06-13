# XJustiz2PDF is a desktop application that converts German xJustiz 
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

'''
converter.py
'''

import os
import sys
import shutil
import tempfile
import subprocess
import platform
import re
import uuid
from typing import Optional, Tuple

from .utils import debug

# Globale Timeout-Konfiguration
SUBPROCESS_TIMEOUT_SECONDS = 180

try:
    from docx2pdf import convert as docx2pdf_convert
    DOCX2PDF_AVAILABLE = True
except Exception:
    DOCX2PDF_AVAILABLE = False

try:
    from PIL import Image
    PIL_AVAILABLE = True
except Exception:
    PIL_AVAILABLE = False

try:
    from fpdf import FPDF
    FPDF_AVAILABLE = True
except Exception:
    FPDF_AVAILABLE = False


def _safe_filename(name: str, replacement: str = "_") -> str:
    name = (name or "").strip()
    name = re.sub(r"\s+", replacement, name)
    name = re.sub(r"[^A-Za-z0-9._-]", replacement, name)
    name = re.sub(r"{0}+".format(re.escape(replacement)), replacement, name)
    name = name.strip("._-")
    return name or "Dokument"


def _detect_libreoffice() -> Optional[str]:
    for name in ("soffice", "libreoffice"):
        path = shutil.which(name)
        if path:
            debug(f"[Converter] LibreOffice gefunden via PATH: {path}")
            return path
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


def _with_timeout_subprocess(cmd: list, timeout: int = SUBPROCESS_TIMEOUT_SECONDS, cwd: Optional[str] = None) -> Tuple[bool, Optional[str]]:
    try:
        debug(f"[Converter] Starte Subprozess: {' '.join(cmd)} (timeout={timeout}s)")
        subprocess.run(cmd, check=True, timeout=timeout, cwd=cwd)
        return True, None
    except subprocess.TimeoutExpired:
        return False, "Timeout erreicht"
    except subprocess.CalledProcessError as e:
        return False, f"Konvertierung fehlgeschlagen: {e}"
    except Exception as e:
        return False, f"Unerwarteter Fehler: {e}"


def _fpdf_new_page_with_ubuntu(font_dir: str) -> FPDF:
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
    pdf.set_xy(margin_left, margin_top)
    pdf.multi_cell(max_width, line_height, text)


def _write_placeholder_pdf(message: str, font_dir: str) -> str:
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
        with open(tmp_path, "wb") as f:
            f.write(b"%PDF-1.4\n%EOF")
        return tmp_path


SUPPORTED_OFFICE = {".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".odt", ".ods", ".odp"}
SUPPORTED_IMAGES = {".tiff", ".tif", ".jpg", ".jpeg", ".png"}
SUPPORTED_TEXT = {".txt", ".csv", ".xml"}

def convert_to_pdf(input_path: str, tmpdir: str, font_dir: str) -> Optional[str]:
    """
    Konvertiert eine Eingabedatei (Office, Bild, Text) nach PDF.
    Gibt immer ein eindeutiges out_pdf zurück (UUID im Dateinamen).
    Bei Fehlern wird ein Platzhalter-PDF erzeugt.
    """

    # Prüfen ob Eingabedatei existiert
    if not os.path.isfile(input_path):
        debug(f"[Converter] Eingabedatei fehlt: {input_path}")
        return _write_placeholder_pdf(f"Eingabedatei fehlt: {input_path}", font_dir)

    ext = os.path.splitext(input_path)[1].lower()
    base_name_raw = os.path.splitext(os.path.basename(input_path))[0]
    base_name = _safe_filename(base_name_raw)
    unique_id = uuid.uuid4().hex[:8]
    out_pdf = os.path.join(tmpdir, f"{base_name}_{unique_id}.pdf")

    # --- Office-Dateien ---
    if ext in SUPPORTED_OFFICE:
        lo = _detect_libreoffice()
        if lo:
            debug(f"[Converter] Starte LibreOffice für {input_path} …")
            cmd = [lo, "--headless", "--convert-to", "pdf", "--outdir", tmpdir, input_path]
            success, err = _with_timeout_subprocess(cmd, timeout=SUBPROCESS_TIMEOUT_SECONDS)

            # LibreOffice erzeugt standardmäßig basename.pdf
            expected_pdf = os.path.join(tmpdir, base_name_raw + ".pdf")
            if success and os.path.isfile(expected_pdf):
                os.rename(expected_pdf, out_pdf)
                debug(f"[Converter] LibreOffice-Konvertierung erfolgreich: {out_pdf}")
                return out_pdf

            debug(f"[Converter] LibreOffice-Konvertierung fehlgeschlagen: {err}")
            return _write_placeholder_pdf(f"LibreOffice-Fehler: {err}", font_dir)

        # Fallback: docx2pdf für DOCX-Dateien
        if ext == ".docx" and DOCX2PDF_AVAILABLE:
            try:
                debug("[Converter] Versuche Fallback docx2pdf …")
                docx2pdf_convert(input_path, tmpdir)
                expected_pdf = os.path.join(tmpdir, base_name_raw + ".pdf")
                if os.path.isfile(expected_pdf):
                    os.rename(expected_pdf, out_pdf)
                    debug(f"[Converter] docx2pdf erfolgreich: {out_pdf}")
                    return out_pdf
                else:
                    # Falls mehrere PDFs erzeugt wurden, nimm die neueste
                    pdf_files = [
                        os.path.join(tmpdir, f)
                        for f in os.listdir(tmpdir)
                        if f.lower().endswith(".pdf")
                    ]
                    if pdf_files:
                        newest_pdf = max(pdf_files, key=os.path.getmtime)
                        os.rename(newest_pdf, out_pdf)
                        debug(f"[Converter] docx2pdf erzeugte PDF, umbenannt: {out_pdf}")
                        return out_pdf
                debug("[Converter] docx2pdf erzeugte keine PDF.")
                return _write_placeholder_pdf("docx2pdf erzeugte keine PDF.", font_dir)
            except Exception as e:
                debug(f"[Converter] docx2pdf Fehler: {e}")
                return _write_placeholder_pdf(f"docx2pdf Fehler: {e}", font_dir)

        debug("[Converter] Office-Datei konnte nicht konvertiert werden.")
        return _write_placeholder_pdf("Office-Datei konnte nicht konvertiert werden.", font_dir)

    # --- Bild-Dateien ---
    if ext in SUPPORTED_IMAGES:
        if not (PIL_AVAILABLE and FPDF_AVAILABLE):
            debug("[Converter] Bild-Fallback nicht verfügbar (Pillow/FPDF fehlt).")
            return _write_placeholder_pdf("Bild-Fallback nicht verfügbar.", font_dir)
        try:
            debug(f"[Converter] Konvertiere Bilddatei {input_path} nach PDF …")
            img = Image.open(input_path)
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")

            pdf = _fpdf_new_page_with_ubuntu(font_dir)
            page_w, page_h = 595, 842  # A4 in Punkten
            img_w, img_h = img.size
            scale = min(page_w / img_w, page_h / img_h)
            draw_w, draw_h = img_w * scale, img_h * scale
            x = (page_w - draw_w) / 2
            y = (page_h - draw_h) / 2

            tmp_img_fd, tmp_img_path = tempfile.mkstemp(prefix="xmlpdf_", suffix=".jpg")
            os.close(tmp_img_fd)
            img.save(tmp_img_path, "JPEG", quality=90)

            pdf.image(tmp_img_path, x=x, y=y, w=draw_w, h=draw_h)
            pdf.output(out_pdf)

            try:
                os.remove(tmp_img_path)
            except Exception:
                debug("[Converter] Temporäre Bilddatei konnte nicht gelöscht werden.")

            debug(f"[Converter] Bild zu PDF konvertiert: {out_pdf}")
            return out_pdf
        except Exception as e:
            debug(f"[Converter] Bild-Konvertierung fehlgeschlagen: {e}")
            return _write_placeholder_pdf(f"Bild-Konvertierung fehlgeschlagen: {e}", font_dir)

    # --- Text-Dateien ---
    if ext in SUPPORTED_TEXT:
        if not FPDF_AVAILABLE:
            debug("[Converter] Text-Fallback nicht verfügbar (FPDF fehlt).")
            return _write_placeholder_pdf("Text-Fallback nicht verfügbar.", font_dir)
        try:
            debug(f"[Converter] Konvertiere Textdatei {input_path} nach PDF …")
            try:
                with open(input_path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
            except UnicodeDecodeError:
                with open(input_path, "r", encoding="latin-1", errors="replace") as f:
                    content = f.read()

            pdf = _fpdf_new_page_with_ubuntu(font_dir)
            _fpdf_write_wrapped_text(pdf, f"Inhalt aus {os.path.basename(input_path)}:\n\n{content}")
            pdf.output(out_pdf)

            debug(f"[Converter] Textdatei zu PDF konvertiert: {out_pdf}")
            return out_pdf
        except Exception as e:
            debug(f"[Converter] Text-Konvertierung fehlgeschlagen: {e}")
            return _write_placeholder_pdf(f"Text-Konvertierung fehlgeschlagen: {e}", font_dir)

    # --- Nicht unterstützte Erweiterung ---
    debug(f"[Converter] Nicht unterstützte Erweiterung: {ext}")
    return _write_placeholder_pdf(f"Nicht unterstützte Erweiterung: {ext}", font_dir)


def render_text_to_pdf(text: str, font_dir: str, title: Optional[str] = None) -> str:
    """
    Rendert generierten Text (z. B. einen Registerauszug) in ein mehrseitiges PDF.
    Nutzt den Ubuntu-Font und automatischen Seitenumbruch (fpdf2 multi_cell).
    Bei Fehlern wird ein Platzhalter-PDF erzeugt.
    """
    tmp_fd, tmp_path = tempfile.mkstemp(prefix="xmlpdf_", suffix="_text.pdf")
    os.close(tmp_fd)
    try:
        pdf = _fpdf_new_page_with_ubuntu(font_dir)
        pdf.set_auto_page_break(auto=True, margin=50)
        pdf.set_xy(50, 50)
        if title:
            pdf.set_font("Ubuntu", "", 15)
            pdf.multi_cell(495, 20, title)
            pdf.ln(6)
        pdf.set_font("Ubuntu", "", 11)
        pdf.set_x(50)
        pdf.multi_cell(495, 15, text)
        pdf.output(tmp_path)
        debug(f"[Converter] Text-PDF erstellt: {tmp_path}")
        return tmp_path
    except Exception as e:
        debug(f"[Converter] Fehler beim Erstellen der Text-PDF: {e}")
        return _write_placeholder_pdf(f"Inhalt konnte nicht gerendert werden: {e}", font_dir)


def placeholder_for_unconvertible(input_path: Optional[str], reason: str, font_dir: str) -> str:
    filename = os.path.basename(input_path or "")
    message = f"Datei {filename} konnte bei der Aktenerstellung nicht konvertiert werden.\n\nGrund: {reason}"
    return _write_placeholder_pdf(message, font_dir)
