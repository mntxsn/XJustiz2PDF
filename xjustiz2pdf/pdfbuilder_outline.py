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

"""
pdfbuilder_outline.py – Outline-/Bookmark-Logik

- Robuste Anlage von Outline-Einträgen.
- Dokumente anhängen und Outline aktualisieren.
"""

from pypdf import PdfReader
from .utils import debug


def sanitize_outline_title(name: str) -> str:
    """
    Bereinigt den Titel für Outline-Einträge ersetzt / und \\ durch 
    optisch identische Unicode ZeichenSlash 
    """
    return (name or "").replace("/", "∕").replace("\\", "⧵")


def add_outline_safe(writer, title: str, page_index: int, parent=None):
    """Outline-Eintrag robust anlegen; bei Fehler None zurückgeben."""
    try:
        safe_title = sanitize_outline_title(title)
        bm = writer.add_outline_item(safe_title, page_index, parent=parent)
        debug(f"[Outline] Bookmark gesetzt: '{safe_title}' auf Seite {page_index}")
        return bm
    except Exception as e:
        debug(f"[Outline] Konnte Bookmark '{title}' nicht setzen: {e}")
        return None


def append_doc_with_outline(writer, part_pdf: str, title: str, parent_bm, status_callback=None):
    """
    Hängt ein Dokument an den Writer und setzt den Outline-Eintrag.
    part_pdf kann ein echter Pfad oder ein Platzhalter-PDF sein.
    """
    if status_callback:
        status_callback(title)
    debug(f"[Outline] Schreibe Dokument: {title} aus Datei {part_pdf}")

    reader = PdfReader(part_pdf)
    current_page = len(writer.pages)
    
    # Loop über Seiten der PDF, da writer.append(reader) bestehende Outline übertragen würde
    for page in reader.pages:
        writer.add_page(page)

    add_outline_safe(writer, title, current_page, parent=parent_bm)
