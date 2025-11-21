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

# pdfbuilder_utils.py – Hilfsfunktionen 

import os
import tempfile
from datetime import datetime
from typing import List
from pypdf import PdfReader
from pypdf.errors import PdfReadError
from .parser import DocNode
from .utils import debug
from .converter import convert_to_pdf, placeholder_for_unconvertible

# Hinweis: Platzhalter werden jetzt per fpdf2 in converter.py erstellt, mit Ubuntu-Font und Zeilenumbruch.

def title_for_doc(node: DocNode) -> str:
    """Erzeugt einen Titel für ein Dokument basierend auf Name/Datum."""
    if node.date_iso:
        return f"{node.anzeigename} - {node.date_iso}"
    elif node.date_str:
        return f"{node.anzeigename} - {node.date_str}"
    elif node.anzeigename:
        return node.anzeigename
    elif node.file_path:
        return os.path.basename(node.file_path)
    return "Unbenannt"

def _keyfunc(n: DocNode):
    try:
        return datetime.strptime(n.date_iso, "%Y-%m-%d") if n.date_iso else datetime.min
    except Exception:
        return datetime.min

def sort_docs(docs: List[DocNode], sort_order: str):
    """Sortiert Dokumente nach Datum, abhängig von sort_order."""
    if sort_order == "original":
        debug("[Utils] Sortierung: original Reihenfolge")
        return
    reverse = (sort_order == "absteigend")
    docs.sort(key=_keyfunc, reverse=reverse)
    debug(f"[Utils] Dokumente sortiert ({'absteigend' if reverse else 'aufsteigend'}): {[d.anzeigename for d in docs]}")

def render_document_or_placeholder(node: DocNode, base_dir: str) -> str:
    """
    Liefert einen Pfad zu einem lesbaren PDF:
    - PDF: Validieren mit PdfReader; wenn ok → Originalpfad
    - Nicht-PDF: Konvertieren via converter.py (LibreOffice + Fallbacks)
    - Fehler → Platzhalter-PDF mit Ubuntu-Font und Zeilenumbruch
    """
    font_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".", "fonts")

    if not node.file_path:
        debug(f"[Utils] Kein file_path für {node.anzeigename} – Platzhalter.")
        return placeholder_for_unconvertible(None, "Kein Dateipfad angegeben", font_dir)

    path = os.path.join(base_dir, node.file_path)
    if not os.path.exists(path):
        debug(f"[Utils] Datei fehlt: {path} – Platzhalter.")
        return placeholder_for_unconvertible(path, "Datei nicht gefunden", font_dir)

    # Prüfe Extension (case-insensitive)
    ext = os.path.splitext(path)[1].lower()
    if ext == ".pdf":
        try:
            PdfReader(path)
            debug(f"[Utils] PDF gültig: {path}")
            return path
        except PdfReadError:
            debug(f"[Utils] PDF ungültig (PdfReadError): {path} – Platzhalter.")
            return placeholder_for_unconvertible(path, "Ungültiges PDF", font_dir)
        except Exception as e:
            debug(f"[Utils] Fehler beim Öffnen von {path}: {e} – Platzhalter.")
            return placeholder_for_unconvertible(path, f"Fehler beim Öffnen: {e}", font_dir)

    # Nicht-PDF: Konvertieren
    tmpdir = tempfile.gettempdir()
    try:
        converted = convert_to_pdf(path, tmpdir, font_dir)
        if converted and os.path.isfile(converted):
            debug(f"[Utils] Konvertierung erfolgreich: {converted}")
            return converted
        debug("[Utils] Konvertierung fehlgeschlagen – Platzhalter.")
        return placeholder_for_unconvertible(path, "Konvertierung fehlgeschlagen oder nicht unterstützt", font_dir)
    except Exception as e:
        debug(f"[Utils] Fehler bei Konvertierung: {e} – Platzhalter.")
        return placeholder_for_unconvertible(path, f"Fehler bei Konvertierung: {e}", font_dir)

def cleanup_temp_pdf(path: str):
    """
    Löscht temporäre PDFs aus dem System-Temp-Verzeichnis.
    Echte Quelldateien (nicht im Temp) bleiben unangetastet.
    """
    try:
        tmpdir = tempfile.gettempdir()
        if path and os.path.abspath(path).startswith(os.path.abspath(tmpdir)) and os.path.exists(path):
            os.remove(path)
            debug(f"[Utils] Temp-PDF gelöscht: {path}")
    except Exception as e:
        debug(f"[Utils] Fehler beim Löschen von Temp-PDF {path}: {e}")
