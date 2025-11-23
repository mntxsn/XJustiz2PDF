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
pdfbuilder.py – Einstiegspunkt, Orchestrierung des PDF-Builds (mit paralleler Ghostscript-Optimierung)
"""

import os
import tempfile
import shutil
import re
import uuid
from typing import List, Optional, Tuple
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
)
from .pdfbuilder_utils import (
    sort_docs,
    title_for_doc,
    render_document_or_placeholder,
)
from .gs_pipeline import parallel_optimize


def _safe_filename(name: str, replacement: str = "_") -> str:
    name = (name or "").strip()
    name = re.sub(r"\s+", replacement, name)
    name = re.sub(r"[^A-Za-z0-9._-]", replacement, name)
    name = re.sub(r"{0}+".format(re.escape(replacement)), replacement, name)
    name = name.strip("._-")
    return name or "Dokument"

class PDFBuilder:
    def __init__(self, sort_order: str = "original", flat_outline: bool = False):
        self.sort_order = sort_order
        self.flat_outline = flat_outline
        self.check_states: dict[Tuple[str, ...], int] = {}

    def build(
        self,
        root: DocNode,
        base_dir: str,
        output_pdf: str,
        status_callback=None,
        filter_terms: Optional[List[str]] = None,
        only_originals: bool = False,
        disabled_paths: Optional[set[Tuple[str, ...]]] = None,
        post_option: str = "none",
        post_params: Optional[dict] = None,
    ):
        filter_terms = [t.lower() for t in (filter_terms or []) if t]
        disabled_paths = set(disabled_paths or set())
        post_params = post_params or {}

        debug("[Builder] Starte PDF-Build …")
        state_for_path = build_state_accessor(self.check_states, disabled_paths)

        with tempfile.TemporaryDirectory(prefix="xmlpdf_run_") as run_tmp:
            stage_convert = os.path.join(run_tmp, "stage_convert")
            stage_opt = os.path.join(run_tmp, "stage_opt")
            os.makedirs(stage_convert, exist_ok=True)
            os.makedirs(stage_opt, exist_ok=True)

            parts: List[Tuple[str, str, Optional[Tuple[str, ...]]]] = []

            if self.flat_outline:
                debug("[Builder] Verwende flache Outline.")
                all_docs = collect_docs_flat(root, state_for_path, filter_terms, only_originals)
                debug(f"[Builder] Gefundene Dokumente (flat): {len(all_docs)}")
                sort_docs(all_docs, self.sort_order)
                for doc in all_docs:
                    title = title_for_doc(doc)
                    if status_callback:
                        status_callback(f"Konvertiere: {title}")
                    part_pdf = render_document_or_placeholder(doc, base_dir)
                    target = self._materialize_to_stage(part_pdf, stage_convert, title)
                    parts.append((title, target, None))
            else:
                debug("[Builder] Verwende hierarchische Outline.")
                root_docs, root_state = get_root_docs_and_state(root, state_for_path)
                root_parent_key: Optional[Tuple[str, ...]] = None
                if root_state in (Qt.PartiallyChecked, Qt.Checked) and root_docs:
                    root_parent_key = ("ROOT_DOCS",)
                if root_state == Qt.Checked:
                    debug(f"[Builder] Root-Dokumente gefunden: {len(root_docs)}")
                    sort_docs(root_docs, self.sort_order)
                    for doc in root_docs:
                        text = (doc.anzeigename or "") + " " + (doc.file_path or "")
                        match_terms = any(term in text.lower() for term in filter_terms)
                        match_originals = only_originals and doc.bestandteil_code not in ("001", "002")
                        if match_terms or match_originals:
                            debug(f"[Builder] Root-Dokument ausgefiltert: {title_for_doc(doc)}")
                            continue
                        title = title_for_doc(doc)
                        if status_callback:
                            status_callback(f"Konvertiere: {title}")
                        part_pdf = render_document_or_placeholder(doc, base_dir)
                        target = self._materialize_to_stage(part_pdf, stage_convert, title)
                        parts.append((title, target, root_parent_key))

                def walk(node: DocNode, path_here: Tuple[str, ...], parent_key: Optional[Tuple[str, ...]]):
                    state = state_for_path(path_here)
                    current_parent_key = parent_key
                    if state in (Qt.PartiallyChecked, Qt.Checked):
                        current_parent_key = path_here
                    if state == Qt.Checked:
                        docs_here = [c for c in node.children if c.is_doc()]
                        debug(f"[Builder] Dokumente im Ordner '{' / '.join(path_here)}': {len(docs_here)}")
                        sort_docs(docs_here, self.sort_order)
                        for doc in docs_here:
                            text = (doc.anzeigename or "") + " " + (doc.file_path or "")
                            match_terms = any(term in text.lower() for term in filter_terms)
                            match_originals = only_originals and doc.bestandteil_code not in ("001", "002")
                            if match_terms or match_originals:
                                debug(f"[Builder] Dokument ausgefiltert: {title_for_doc(doc)}")
                                continue
                            title = title_for_doc(doc)
                            if status_callback:
                                status_callback(f"Konvertiere: {title}")
                            part_pdf = render_document_or_placeholder(doc, base_dir)
                            target = self._materialize_to_stage(part_pdf, stage_convert, title)
                            parts.append((title, target, current_parent_key))
                    for c in node.children:
                        if c.is_folder():
                            child_path = path_here + ((c.anzeigename or "Akte"),)
                            walk(c, child_path, current_parent_key)

                for c in root.children:
                    if c.is_folder():
                        child_path = (c.anzeigename or "Akte",)
                        walk(c, child_path, parent_key=None)

            if post_option == "ghostscript":
                debug("[Builder] Starte Ghostscript-Optimierung …")
                gs_path = post_params.get("gs_path")
                quality = post_params.get("quality", "ebook")
                inputs = [p for (_t, p, _pk) in parts]
                optimized_paths = parallel_optimize(
                    inputs,
                    out_dir=stage_opt,
                    gs_path=gs_path,
                    quality=quality,
                    max_workers=None,
                    status_callback=status_callback,
                )
                parts = [(title, optimized_paths[i], parent_key) for i, (title, _p, parent_key) in enumerate(parts)]
                debug("[Builder] Ghostscript-Optimierung abgeschlossen.")

            writer = PdfWriter()
            parent_bm_map: dict[Optional[Tuple[str, ...]], Optional[object]] = {}

            def ensure_parent_bm(parent_key: Optional[Tuple[str, ...]]):
                """
                Stellt sicher, dass für den gegebenen Pfad-Schlüssel ein Parent-Bookmark existiert.
                - Baut die Hierarchie rekursiv anhand des Tupel-Pfads.
                - Verwendet add_outline_safe (enthält Titel-Sanitization).
                """
                if parent_key in parent_bm_map:
                    return parent_bm_map[parent_key]

                # Spezieller Bereich für Root-Einzeldokumente
                if parent_key == ("ROOT_DOCS",):
                    bm = add_outline_safe(writer, "Einzeldokumente", len(writer.pages), parent=None)
                    parent_bm_map[parent_key] = bm
                    return bm

                # Kein Elternknoten erforderlich
                if not parent_key:
                    parent_bm_map[parent_key] = None
                    return None

                # Rekursiv den Eltern-Pfad sicherstellen
                if len(parent_key) > 1:
                    parent_parent_key = parent_key[:-1]
                else:
                    parent_parent_key = None

                parent_parent_bm = ensure_parent_bm(parent_parent_key)
                title = parent_key[-1] or "Akte"
                bm = add_outline_safe(writer, title, len(writer.pages), parent=parent_parent_bm)
                parent_bm_map[parent_key] = bm
                return bm

            debug(f"[Builder] Füge {len(parts)} Teile ins PDF ein …")
            for (title, part_path, parent_key) in parts:
                if not part_path or not os.path.isfile(part_path):
                    debug(f"[Builder] Datei fehlt: {title}")
                    self._append_fallback_page(writer, f"Fehler: Datei fehlt ({title})")
                    continue
                parent_bm = ensure_parent_bm(parent_key)
                current_page = len(writer.pages)
                try:
                    reader = PdfReader(part_path)
                    for page in reader.pages:
                        writer.add_page(page)
                except Exception:
                    debug(f"[Builder] Fehler beim Hinzufügen von {title}")
                    self._append_fallback_page(writer, f"Fehler beim Hinzufügen von {title}")
                add_outline_safe(writer, title, current_page, parent=parent_bm)

            if len(writer.pages) == 0:
                debug("[Builder] Keine Dokumente übrig – füge Platzhalterseite hinzu.")
                self._append_placeholder_page(writer)

            with open(output_pdf, "wb") as f:
                writer.write(f)
            debug(f"[Builder] PDF erfolgreich geschrieben: {output_pdf}")

    def _materialize_to_stage(self, source_path: str, stage_dir: str, title: str) -> str:
        os.makedirs(stage_dir, exist_ok=True)
        base = _safe_filename(title or "Dokument")
        unique_id = uuid.uuid4().hex[:8]
        target = os.path.join(stage_dir, f"{base}_{unique_id}.pdf")
        try:
            if os.path.abspath(source_path) != os.path.abspath(target):
                shutil.copyfile(source_path, target)
            else:
                alt = os.path.join(stage_dir, f"{base}_{unique_id}_1.pdf")
                shutil.copyfile(source_path, alt)
                target = alt
        except Exception:
            return source_path
        return target

    def _append_placeholder_page(self, writer: PdfWriter):
        font_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")
        font_path = os.path.join(font_dir, "Ubuntu-R.ttf")
        fd, out = tempfile.mkstemp(prefix="xmlpdf_", suffix="_empty.pdf")
        os.close(fd)
        try:
            pdf = FPDF(unit="pt", format="A4")
            pdf.add_page()
            if os.path.isfile(font_path):
                pdf.add_font("Ubuntu", "", font_path)
                pdf.set_font("Ubuntu", "", 14)
            else:
                pdf.set_font("Arial", "", 14)
            pdf.multi_cell(495, 18, "Keine Dokumente ausgewählt oder alle ausgefiltert.")
            pdf.output(out)
        except Exception:
            with open(out, "wb") as f:
                f.write(b"%PDF-1.4\n%EOF")
        try:
            reader = PdfReader(out)
            for page in reader.pages:
                writer.add_page(page)
        except Exception:
            pass
        try:
            os.remove(out)
        except Exception:
            pass

    def _append_fallback_page(self, writer: PdfWriter, message: str):
        font_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")
        font_path = os.path.join(font_dir, "Ubuntu-R.ttf")
        fd, out = tempfile.mkstemp(prefix="xmlpdf_", suffix="_fallback.pdf")
        os.close(fd)
        try:
            pdf = FPDF(unit="pt", format="A4")
            pdf.add_page()
            if os.path.isfile(font_path):
                pdf.add_font("Ubuntu", "", font_path)
                pdf.set_font("Ubuntu", "", 12)
            else:
                pdf.set_font("Arial", "", 12)
            pdf.multi_cell(495, 18, message)
            pdf.output(out)
        except Exception:
            with open(out, "wb") as f:
                f.write(b"%PDF-1.4\n%EOF")
        try:
            reader = PdfReader(out)
            for page in reader.pages:
                writer.add_page(page)
        except Exception:
            pass
        try:
            os.remove(out)
        except Exception:
            pass
