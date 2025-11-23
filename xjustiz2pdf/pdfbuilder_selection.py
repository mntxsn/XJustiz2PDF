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
pdfbuilder_selection.py – Auswahl-/Filterlogik
"""

from typing import Callable, List, Tuple, Optional
from PySide6.QtCore import Qt
from .parser import DocNode
from .utils import debug


def build_state_accessor(check_states: dict[Tuple[str, ...], int], disabled_paths: set[Tuple[str, ...]]) -> Callable[[Optional[Tuple[str, ...]]], int]:
    """
    Liefert eine Funktion, die für einen gegebenen Pfad den CheckState zurückgibt.
    - disabled_paths werden immer als Unchecked behandelt.
    - Wenn der Pfad nicht im Dict existiert, wird Unchecked zurückgegeben.
    """
    def state_for_path(path: Optional[Tuple[str, ...]]) -> int:
        if path and path in disabled_paths:
            debug(f"[StateAccessor] path='{ ' / '.join(path) }' ist disabled → Unchecked")
            return Qt.Unchecked
        state = check_states.get(path or tuple(), Qt.Unchecked)
        debug(f"[StateAccessor] path='{ ' / '.join(path or ()) }' → state={state}, keys_sample={[ ' / '.join(k) for k in list(check_states.keys())[:5] ]}")
        return state
    return state_for_path


def get_root_docs_and_state(root: DocNode, state_for_path: Callable[[Optional[Tuple[str, ...]]], int]) -> Tuple[List[DocNode], int]:
    """
    Liefert die Root-Dokumente und den State für ROOT_DOCS.
    """
    root_docs = [ch for ch in root.children if ch.is_doc()]
    root_state = state_for_path(("ROOT_DOCS",))
    debug(f"[Selection] Root-Dokumente={len(root_docs)}, ROOT_DOCS State={root_state}")
    return root_docs, root_state


def collect_docs_flat(
    root: DocNode,
    state_for_path: Callable[[Optional[Tuple[str, ...]]], int],
    filter_terms: List[str],
    only_originals: bool
) -> List[DocNode]:
    """
    Sammelt alle Dokumente für den flachen Outline-Modus.
    Nur Checked-Ordner liefern Dokumente, PartiallyChecked wird ignoriert.
    """
    selected: List[DocNode] = []

    def should_filter(doc: DocNode) -> bool:
        text = (doc.anzeigename or "") + " " + (doc.file_path or "")
        match_terms = any(term.lower() in text.lower() for term in filter_terms)
        match_originals = only_originals and doc.bestandteil_code not in ("001", "002")
        if match_terms:
            debug(f"[Selection] Flach: Dokument ausgefiltert durch Begriff(e): {doc.anzeigename}")
        if match_originals:
            debug(f"[Selection] Flach: Dokument ausgefiltert (kein Original/Repräsentat): {doc.anzeigename}")
        return match_terms or match_originals

    def walk(node: DocNode, path_here: Tuple[str, ...]):
        state = state_for_path(path_here)
        debug(f"[Selection] Walk Folder='{node.anzeigename}', Path='{ ' / '.join(path_here) }', State={state}")
        if node.is_folder():
            if state == Qt.Checked:
                debug(f"[Selection] Ordner '{node.anzeigename}' ist Checked – prüfe Dokumente …")
                for c in node.children:
                    if c.is_doc():
                        if not should_filter(c):
                            debug(f"[Selection] Flach: Dokument übernommen {c.anzeigename}")
                            selected.append(c)
                        else:
                            debug(f"[Selection] Flach: Dokument verworfen {c.anzeigename}")
            else:
                debug(f"[Selection] Ordner '{node.anzeigename}' nicht Checked – überspringe Dokumente.")
            for c in node.children:
                if c.is_folder():
                    child_path = path_here + ((c.anzeigename or "Akte"),)
                    walk(c, child_path)

    debug("[Selection] Starte Sammlung für flache Outline …")
    for c in root.children:
        if c.is_folder():
            path = (c.anzeigename or "Akte",)
            walk(c, path)

    root_docs = [ch for ch in root.children if ch.is_doc()]
    root_state = state_for_path(("ROOT_DOCS",))
    debug(f"[Selection] Flach: ROOT_DOCS State={root_state}, RootDocs={len(root_docs)}")
    if root_docs and root_state == Qt.Checked:
        debug("[Selection] ROOT_DOCS ist Checked – prüfe Dokumente …")
        for doc in root_docs:
            if not should_filter(doc):
                debug(f"[Selection] Flach: Root-Dokument übernommen {doc.anzeigename}")
                selected.append(doc)
            else:
                debug(f"[Selection] Flach: Root-Dokument verworfen {doc.anzeigename}")
    else:
        debug("[Selection] ROOT_DOCS nicht Checked oder keine Dokumente vorhanden.")

    debug(f"[Selection] Flach gesammelt: {len(selected)} Dokumente")
    return selected
