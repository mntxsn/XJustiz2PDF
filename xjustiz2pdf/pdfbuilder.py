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

"""
pdfbuilder.py – Einstiegspunkt, Orchestrierung des PDF-Builds
"""

import os
import tempfile
from pypdf import PdfReader, PdfWriter
from PySide6.QtCore import Qt
from fpdf import FPDF

from .parser import DocNode
from .utils import debug

from .pdfbuilder_selection import (
    build_state_accessor,
    get_root_docs_and_state,
    collect_docs_flat,
)
from .pdfbuilder_outline import (
    add_outline_safe,
    append_doc_with_outline,
)
from .pdfbuilder_utils import (
    sort_docs,
    title_for_doc,
    render_document_or_placeholder,
    cleanup_temp_pdf,
)


class PDFBuilder:
    def __init__(self, sort_order="original", flat_outline=False):
        self.sort_order = sort_order
        self.flat_outline = flat_outline
        self.check_states: dict[str, int] = {}

    def build(self, root: DocNode, base_dir: str, output_pdf: str,
              status_callback=None, filter_terms=None, only_originals=False,
              disabled_paths=None, post_option="none", post_params=None):

        writer = PdfWriter()
        filter_terms = [t.lower() for t in (filter_terms or []) if t]
        disabled_paths = set(disabled_paths or [])

        debug(f"[PDFBuilder] Start build: sort_order={self.sort_order}, flat_outline={self.flat_outline}")
        debug(f"[PDFBuilder] check_states(keys)={list(self.check_states.keys())[:10]} ... total={len(self.check_states)}")
        debug(f"[PDFBuilder] disabled_paths(sample)={list(disabled_paths)[:10]} ... total={len(disabled_paths)}")

        state_for_path = build_state_accessor(self.check_states, disabled_paths)

        # --------- Flaches Inhaltsverzeichnis ---------
        if self.flat_outline:
            debug("[PDFBuilder] Flaches Inhaltsverzeichnis – robuste Auswahl.")
            all_docs = collect_docs_flat(root, state_for_path, filter_terms, only_originals)
            sort_docs(all_docs, self.sort_order)
            for doc in all_docs:
                title = title_for_doc(doc)
                part_pdf = render_document_or_placeholder(doc, base_dir)
                append_doc_with_outline(writer, part_pdf, title, parent_bm=None, status_callback=status_callback)
                cleanup_temp_pdf(part_pdf)

        # --------- Verschachteltes Inhaltsverzeichnis ---------
        else:
            debug("[PDFBuilder] Verschachteltes Inhaltsverzeichnis – robuste Auswahl.")

            # Root-Dokumente
            root_docs, root_state = get_root_docs_and_state(root, state_for_path)
            bm_root = None
            if root_state in (Qt.PartiallyChecked, Qt.Checked) and root_docs:
                bm_root = add_outline_safe(writer, "Einzeldokumente", len(writer.pages), parent=None)
            if root_state == Qt.Checked:
                sort_docs(root_docs, self.sort_order)
                for doc in root_docs:
                    title = title_for_doc(doc)
                    part_pdf = render_document_or_placeholder(doc, base_dir)
                    append_doc_with_outline(writer, part_pdf, title, parent_bm=bm_root, status_callback=status_callback)
                    cleanup_temp_pdf(part_pdf)

            # Rekursive Verarbeitung der Ordner
            def write_folder(node: DocNode, path_here: str, parent_bm):
                state = state_for_path(path_here)
                debug(f"[Builder] Folder={node.anzeigename}, Path={path_here}, State={state}")

                bm = None
                if state in (Qt.PartiallyChecked, Qt.Checked):
                    bm = add_outline_safe(writer, node.anzeigename or "Akte", len(writer.pages), parent=parent_bm)

                if state == Qt.Checked:
                    docs_here = [c for c in node.children if c.is_doc()]
                    sort_docs(docs_here, self.sort_order)
                    for doc in docs_here:
                        text = (doc.anzeigename or "") + " " + (doc.file_path or "")
                        match_terms = any(term in text.lower() for term in filter_terms)
                        match_originals = only_originals and doc.bestandteil_code not in ("001", "002")
                        if match_terms or match_originals:
                            debug(f"[Builder] Dokument gefiltert: {doc.anzeigename}")
                            continue
                        title = title_for_doc(doc)
                        debug(f"[Builder] Dokument übernommen: {title}")
                        part_pdf = render_document_or_placeholder(doc, base_dir)
                        append_doc_with_outline(writer, part_pdf, title, parent_bm=bm, status_callback=status_callback)
                        cleanup_temp_pdf(part_pdf)

                for c in node.children:
                    if c.is_folder():
                        child_path = f"{path_here}/{c.anzeigename or 'Akte'}" if path_here else (c.anzeigename or "Akte")
                        write_folder(c, child_path, bm)

            for c in root.children:
                if c.is_folder():
                    child_path = c.anzeigename or "Akte"
                    write_folder(c, child_path, parent_bm=None)

        # --------- Platzhalter ---------
        if len(writer.pages) == 0:
            debug("[PDFBuilder] Keine Dokumente übrig – erzeuge Platzhalterseite.")
            font_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")
            font_path = os.path.join(font_dir, "Ubuntu-R.ttf")

            fd, out = tempfile.mkstemp(prefix="xmlpdf_", suffix="_empty.pdf")
            os.close(fd)

            try:
                pdf = FPDF(unit="pt", format="A4")
                pdf.add_page()
                pdf.add_font("Ubuntu", "", font_path)
                pdf.set_font("Ubuntu", "", 14)
                pdf.multi_cell(495, 18, "Keine Dokumente ausgewählt oder alle ausgefiltert.")
                pdf.output(out)
            except Exception as e:
                debug(f"[PDFBuilder] Fehler beim Erstellen der Platzhalter-PDF: {e}")
                with open(out, "wb") as f:
                    f.write(b"%PDF-1.4\n%EOF")

            reader = PdfReader(out)
            writer.append(reader)
            try:
                os.remove(out)
            except Exception:
                pass

        debug(f"[PDFBuilder] Schreibe finale PDF nach: {output_pdf}")
        with open(output_pdf, "wb") as f:
            writer.write(f)
