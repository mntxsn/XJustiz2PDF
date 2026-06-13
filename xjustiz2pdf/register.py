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
register.py
Liest strukturierte Registerdaten (fachdatenRegister) aus XJustiz-Registernachrichten
(z. B. HR-Auszug, nachricht.reg.0400003) und erzeugt daraus einen lesbaren Textblock.

Registernachrichten enthalten oft keine Schriftgutobjekte/Dokumente, sondern nur
strukturierte Daten. Diese werden hier zu einem Text aufbereitet, der vom PDF-Builder
als eigene Seite gerendert werden kann.

Trick: XJustiz-Dateien enthalten zu codierten Werten i. d. R. einen XML-Kommentar mit
dem Klartext (z. B. <!--Geschäftsführer(in)--><code>086</code>). Dieser Klartext wird
für die Ausgabe bevorzugt verwendet, sodass keine Code-Listen gepflegt werden müssen.
"""

from typing import List, Optional
from lxml import etree
from .utils import debug

NS = "{http://www.xjustiz.de}"


def _q(name: str) -> str:
    return f"{NS}{name}"


def _find(el, *localnames):
    """Folgt einem Pfad lokaler Namen ab el (erstes Treffer-Element je Stufe)."""
    cur = el
    for ln in localnames:
        if cur is None:
            return None
        cur = cur.find(_q(ln))
    return cur


def _deep(el, localname):
    """Erstes Nachfahren-Element mit lokalem Namen."""
    return el.find(f".//{_q(localname)}") if el is not None else None


def _text(el) -> Optional[str]:
    if el is None or el.text is None:
        return None
    t = el.text.strip()
    return t or None


def _comment_of(el) -> Optional[str]:
    """Liefert den Text des ersten Kommentar-Kindknotens (Klartext zu einem Code)."""
    if el is None:
        return None
    for child in el:
        if isinstance(child, etree._Comment) and child.text:
            t = child.text.strip()
            if t:
                return t
    return None


def _code_text(el) -> Optional[str]:
    """Code-Wert eines codierten Elements. <code> ist in XJustiz unqualifiziert (kein Namespace)."""
    if el is None:
        return None
    return _text(el.find("code"))


def _coded(el) -> Optional[str]:
    """Klartext (Kommentar) eines codierten Elements; ersatzweise der Code selbst."""
    if el is None:
        return None
    label = _comment_of(el)
    if label:
        return label
    return _code_text(el)


def _beteiligter_name(beteiligter) -> Optional[str]:
    """Anzeigename eines <beteiligter> (Organisation oder natürliche Person)."""
    if beteiligter is None:
        return None
    org = _deep(beteiligter, "organisation")
    if org is not None:
        name = _text(_find(org, "bezeichnung", "bezeichnung.aktuell"))
        rechtsform = _coded(_find(org, "angabenZurRechtsform", "rechtsform"))
        if name and rechtsform:
            return f"{name} ({rechtsform})"
        return name
    person = _deep(beteiligter, "natuerlichePerson")
    if person is not None:
        vorname = _text(_find(person, "vollerName", "vorname"))
        nachname = _text(_find(person, "vollerName", "nachname"))
        full = " ".join(p for p in (vorname, nachname) if p)
        geb = _text(_deep(person, "geburtsdatum"))
        ort = _text(_deep(person, "ort"))
        extra = ", ".join(p for p in ([f"*{geb}"] if geb else []) + ([ort] if ort else []))
        if full and extra:
            return f"{full} ({extra})"
        return full or extra or None
    return None


def _format_anschrift(el) -> Optional[str]:
    if el is None:
        return None
    strasse = _text(_deep(el, "strasse"))
    hausnummer = _text(_deep(el, "hausnummer"))
    plz = _text(_deep(el, "postleitzahl"))
    ort = _text(_deep(el, "ort"))
    line1 = " ".join(p for p in (strasse, hausnummer) if p)
    line2 = " ".join(p for p in (plz, ort) if p)
    full = ", ".join(p for p in (line1, line2) if p)
    return full or None


def build_register_text(root_el) -> Optional[str]:
    """
    Erzeugt einen lesbaren Textblock aus dem fachdatenRegister-Teil einer
    Registernachricht. Gibt None zurück, wenn kein fachdatenRegister vorhanden ist.
    """
    fdr = _deep(root_el, "fachdatenRegister")
    if fdr is None:
        debug("[Register] Kein fachdatenRegister – kein Registertext.")
        return None

    lines: List[str] = []

    def add(label: str, value: Optional[str], indent: int = 0):
        if value:
            lines.append("  " * indent + (f"{label}: {value}" if label else value))

    def heading(title: str):
        if lines:
            lines.append("")
        lines.append(title)
        lines.append("-" * len(title))

    # --- Kopfdaten ---
    verfahrensdaten = _deep(root_el, "verfahrensdaten")
    instanzdaten = _deep(verfahrensdaten, "instanzdaten") if verfahrensdaten is not None else None

    # Die Überschrift (Mitteilungsart + Aktenzeichen) trägt der Dokumenttitel,
    # siehe register_message_title; hier folgt direkt der Inhalt.
    gericht = _coded(_find(instanzdaten, "auswahl_instanzbehoerde", "gericht")) if instanzdaten is not None else None
    add("Registergericht", gericht)

    az = _find(instanzdaten, "aktenzeichen", "auswahl_aktenzeichen", "aktenzeichen.strukturiert") if instanzdaten is not None else None
    if az is not None:
        register = _coded(_deep(az, "register"))
        lfd = _text(_deep(az, "laufendeNummer"))
        jahr = _text(_deep(az, "jahr"))
        register_code = _code_text(_deep(az, "register"))
        az_str = " ".join(p for p in (register_code, lfd) if p)
        if jahr:
            az_str = f"{az_str} ({jahr})"
        add("Aktenzeichen", az_str.strip() or None)
        add("Registerart", register)

    auszug = _deep(fdr, "auszug")
    if auszug is not None:
        add("Abrufdatum", _text(_deep(auszug, "abrufdatum")))
        add("Abrufuhrzeit", _text(_deep(auszug, "abrufuhrzeit")))
        add("Letzte Eintragung", _text(_deep(auszug, "letzteEintragung")))
        add("Anzahl Eintragungen", _text(_deep(auszug, "anzahlEintragungen")))
        add("Erste Satzung", _text(_deep(auszug, "satzungsdatum")))

    # --- Rechtsträger ---
    rechtstraeger = _find(fdr, "basisdatenRegister", "rechtstraeger")
    if rechtstraeger is not None:
        heading("Rechtsträger")
        add("Bezeichnung", _text(_find(rechtstraeger, "bezeichnung", "bezeichnung.aktuell")))
        add("Rechtsform", _coded(_find(rechtstraeger, "angabenZurRechtsform", "rechtsform")))
        add("Sitz", _text(_find(rechtstraeger, "sitz", "ort")))
        add("Anschrift", _format_anschrift(_deep(rechtstraeger, "anschrift")))

    basisdaten = _deep(fdr, "basisdatenRegister")
    if basisdaten is not None:
        gegenstand = _text(_deep(basisdaten, "gegenstand"))
        add("Gegenstand", gegenstand)
        kapital = _deep(basisdaten, "kapital")
        if kapital is not None:
            zahl = _text(_deep(kapital, "zahl"))
            waehrung = _coded(_find(_deep(kapital, "auswahl_waehrung"), "waehrung")) or _coded(_deep(kapital, "waehrung"))
            if zahl:
                add("Kapital", " ".join(p for p in (zahl, waehrung) if p))

    # --- Beteiligte (für Namensauflösung über Rollennummer) ---
    rollen_namen = {}
    for beteiligung in (verfahrensdaten.findall(_q("beteiligung")) if verfahrensdaten is not None else []):
        beteiligter = beteiligung.find(_q("beteiligter"))
        name = _beteiligter_name(beteiligter)
        for rolle in beteiligung.findall(_q("rolle")):
            rn = _text(_deep(rolle, "rollennummer"))
            if rn:
                rollen_namen[rn] = name

    # --- Vertretung ---
    vertretung = _find(fdr, "basisdatenRegister", "vertretung")
    if vertretung is not None:
        heading("Vertretung")
        allgemein = _coded(_find(vertretung, "allgemeineVertretungsregelung", "auswahl_vertretungsbefugnis", "vertretungsbefugnis"))
        add("Allgemeine Regelung", allgemein)
        for vb in vertretung.findall(_q("vertretungsberechtigte")):
            ref = _text(_deep(vb, "ref.rollennummer"))
            name = rollen_namen.get(ref, f"Rolle {ref}" if ref else "Unbekannt")
            besonders = _coded(_find(vb, "besondereVertretungsregelung", "auswahl_vertretungsbefugnis", "vertretungsbefugnis"))
            befreiung = _coded(_find(vb, "besondereVertretungsregelung", "auswahl_befreiungVon181BGB", "befreiungVon181BGB"))
            zusatz = "; ".join(p for p in (besonders, befreiung) if p)
            add("", f"{name}" + (f" – {zusatz}" if zusatz else ""), indent=1)

    # --- Beteiligte (vollständige Auflistung) ---
    beteiligungen = verfahrensdaten.findall(_q("beteiligung")) if verfahrensdaten is not None else []
    if beteiligungen:
        heading("Beteiligte")
        for beteiligung in beteiligungen:
            beteiligter = beteiligung.find(_q("beteiligter"))
            name = _beteiligter_name(beteiligter)
            if not name:
                continue
            rollen = [_coded(_deep(r, "rollenbezeichnung")) for r in beteiligung.findall(_q("rolle"))]
            rollen_str = ", ".join(r for r in rollen if r)
            add("", name + (f" [{rollen_str}]" if rollen_str else ""), indent=1)

    # --- Eintragungen ---
    if auszug is not None:
        eintragungen = auszug.findall(_q("eintragungstext"))
        if eintragungen:
            heading("Eintragungen")
            for et in eintragungen:
                lfd = _text(_deep(et, "laufendeNummer"))
                art = _coded(_deep(et, "eintragungsart"))
                text = _text(_deep(et, "text"))
                head = " ".join(p for p in ([f"Nr. {lfd}"] if lfd else []) + ([f"({art})"] if art else []))
                if head:
                    add("", head, indent=1)
                add("", text, indent=2)

    result = "\n".join(lines).strip()
    debug(f"[Register] Registertext erzeugt ({len(result)} Zeichen, {len(lines)} Zeilen).")
    return result or None


def register_message_title(root_el) -> str:
    """Kurzer Titel für den Registerknoten, z. B. 'HR-Auszug HRB 110584'."""
    fdr = _deep(root_el, "fachdatenRegister")
    art = _coded(_deep(fdr, "mitteilungsart")) if fdr is not None else None
    art = art or _coded(_deep(root_el, "ereignis")) or "Registerauszug"
    az = _deep(root_el, "aktenzeichen.strukturiert")
    az_str = None
    if az is not None:
        register_code = _code_text(_deep(az, "register"))
        lfd = _text(_deep(az, "laufendeNummer"))
        az_str = " ".join(p for p in (register_code, lfd) if p) or None
    return f"{art} {az_str}".strip() if az_str else art
