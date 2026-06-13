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
parser.py
Dieses Modul enthält die Datenklasse DocNode und den AktenParser.
Der Parser liest XJustiz-XML-Dateien (oder entpackte ZIPs) und baut eine Baumstruktur von DocNode-Objekten.
"""

import os
from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime
from lxml import etree
from .utils import debug
from .register import build_register_text, register_message_title


def first_non_none(*elements):
    """Hilfsfunktion: gibt das erste nicht-None Element zurück, sonst None."""
    for el in elements:
        if el is not None:
            return el
    return None


@dataclass
class DocNode:
    type: str  # 'folder' oder 'doc'
    anzeigename: str
    date_str: Optional[str] = None
    date_iso: Optional[str] = None
    file_path: Optional[str] = None
    bestandteil_code: Optional[str] = None
    text_content: Optional[str] = None  # generierter Inhalt (z. B. Registerauszug) statt Datei
    children: List["DocNode"] = field(default_factory=list)

    def is_folder(self): return self.type == "folder"
    def is_doc(self): return self.type == "doc"


class AktenParser:
    NS = "{http://www.xjustiz.de}"
    TAG_AKTE = f"{NS}akte"
    TAG_TEILAKTE = f"{NS}teilakte"
    TAG_DOKUMENT = f"{NS}dokument"
    TAG_SCHRIFTOBJEKTE = f"{NS}schriftgutobjekte"
    TAG_ANZEIGENAME = f"{NS}anzeigename"
    TAG_VERAKTUNGSDATUM = f"{NS}veraktungsdatum"
    TAG_DATEI = f"{NS}datei"
    TAG_DATEINAME = f"{NS}dateiname"
    TAG_BESTANDTEIL = f"{NS}bestandteil"

    def parse(self, xml_path: str) -> DocNode:
        tree = etree.parse(xml_path)
        root_el = tree.getroot()
        container = first_non_none(
            root_el.find(f".//{self.TAG_SCHRIFTOBJEKTE}"),
            root_el
        )

        docs_first, akten = [], []
        for child in container:
            if not isinstance(child.tag, str):
                continue
            if child.tag == self.TAG_DOKUMENT:
                docs_first.extend(self._parse_document(child))
            elif child.tag in (self.TAG_AKTE, self.TAG_TEILAKTE):
                akten.append(self._parse_folder(child))

        children = docs_first + akten

        # Strukturierte Registerdaten (z. B. HR-Auszug) als eigenen Ordner ergänzen.
        # Solche Nachrichten enthalten oft keine Schriftgutobjekte/Dokumente.
        register_node = self._build_register_node(root_el)
        if register_node is not None:
            children.append(register_node)

        debug(f"[Parser] Root hat {len(children)} Kinder")
        return DocNode("folder", "", children=children)

    def _build_register_node(self, root_el) -> Optional[DocNode]:
        """Erzeugt aus fachdatenRegister einen Ordner mit einem generierten Inhalts-Dokument."""
        try:
            text = build_register_text(root_el)
        except Exception as e:
            debug(f"[Parser] Registerextraktion fehlgeschlagen: {e}")
            return None
        if not text:
            return None
        title = register_message_title(root_el)
        debug(f"[Parser] Registerknoten erzeugt: {title}")
        # bestandteil_code="001" (Original): Der generierte Registerinhalt ist die
        # maßgebliche Primärinformation und darf vom "Nur Originale"-Filter nicht
        # entfernt werden (er hätte sonst keinen Code und würde ausgefiltert).
        doc = DocNode("doc", title, text_content=text, bestandteil_code="001")
        return DocNode("folder", title, children=[doc])

    def _parse_folder(self, el) -> DocNode:
        anzeigename = self._find_text_ns(el, self.TAG_ANZEIGENAME) or "Akte"
        date_raw = self._find_text_ns(el, self.TAG_VERAKTUNGSDATUM)
        date_iso = self._normalize_date(date_raw) if date_raw else None
        children = []

        for ch in el:
            if not isinstance(ch.tag, str):
                continue
            if ch.tag == self.TAG_TEILAKTE:
                children.append(self._parse_folder(ch))
            elif ch.tag == self.TAG_DOKUMENT:
                children.extend(self._parse_document(ch))

        inhalt = el.find(f".//{self.NS}inhalt")
        if inhalt is not None:
            for ch in inhalt:
                if not isinstance(ch.tag, str):
                    continue
                if ch.tag == self.TAG_TEILAKTE:
                    children.append(self._parse_folder(ch))
                elif ch.tag == self.TAG_DOKUMENT:
                    children.extend(self._parse_document(ch))

        debug(f"[Parser] Folder erkannt: {anzeigename} mit {len(children)} Kindern")
        return DocNode("folder", anzeigename,
                       date_str=date_raw, date_iso=date_iso,
                       file_path=None, bestandteil_code=None,
                       children=children)

    def _parse_document(self, el) -> List[DocNode]:
        anzeigename = self._find_text_ns(el, self.TAG_ANZEIGENAME)
        date_raw = self._find_text_ns(el, self.TAG_VERAKTUNGSDATUM)
        date_iso = self._normalize_date(date_raw) if date_raw else None

        nodes = []
        for datei in el.findall(f".//{self.TAG_DATEI}"):
            fname_el = datei.find(f".//{self.TAG_DATEINAME}")
            fname = fname_el.text.strip() if fname_el is not None and fname_el.text else None

            bestandteil_code = None
            bestandteil = first_non_none(
                datei.find(f"{self.TAG_BESTANDTEIL}"),
                datei.find(f".//{self.TAG_BESTANDTEIL}")
            )
            if bestandteil is not None:
                code_el = bestandteil.find("code")
                if code_el is None:
                    code_el = first_non_none(
                        bestandteil.find(f"{self.NS}code"),
                        bestandteil.find(f".//{self.NS}code")
                    )
                if code_el is not None and code_el.text:
                    bestandteil_code = code_el.text.strip()

            title = anzeigename or (os.path.basename(fname) if fname else "Unbenannt")
            nodes.append(DocNode("doc", title, date_raw, date_iso, fname, bestandteil_code))
            debug(f"[Parser] Dokument erkannt: {title} Datei={fname} Code={bestandteil_code}")
        return nodes

    def _find_text_ns(self, el, qname: str) -> Optional[str]:
        node = el.find(f".//{qname}")
        return node.text.strip() if node is not None and node.text else None

    def _normalize_date(self, s: str) -> Optional[str]:
        try:
            return datetime.strptime(s.strip(), "%Y-%m-%d").strftime("%Y-%m-%d")
        except Exception:
            return s
