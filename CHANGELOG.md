# Changelog

Alle nennenswerten Änderungen an diesem Projekt werden in dieser Datei dokumentiert.

Das Format orientiert sich an [Keep a Changelog](https://keepachangelog.com/de/1.0.0/),
die Versionierung folgt [Semantic Versioning](https://semver.org/lang/de/).

Dies ist ein Fork von [digidigital/XJustiz2PDF](https://github.com/digidigital/XJustiz2PDF).

## [0.1.4] - 2026-06-14

### Hinzugefügt
- **Strukturierte Registerinhalte (z. B. HR-Auszug) werden jetzt exportiert.**
  Registernachrichten (`nachricht.reg.*`) ohne Schriftgutobjekte/Dokumente lieferten
  bisher keine auswählbare Aktenstruktur, da der gesamte Inhalt im `fachdatenRegister`
  steckt. Diese Daten werden nun ausgelesen und als eigener, abwählbarer Eintrag
  („HR-Auszug …") im Baum angezeigt und beim Export als lesbare PDF-Seite gerendert.
  Enthalten sind u. a. Registergericht, Aktenzeichen, Rechtsträger, Rechtsform,
  Sitz/Anschrift, Gegenstand, Kapital, Vertretungsregelung (mit aufgelösten
  Beteiligtennamen), Beteiligte und Eintragungstexte. Die in XJustiz-Dateien
  eingebetteten XML-Kommentare werden als Klartext zu den Codes genutzt.

### Geändert
- Der GitHub-Versionschecker und die Projekt-URLs verweisen jetzt auf den Fork
  `mntxsn/XJustiz2PDF`.

### Behoben
- Der generierte Registerauszug wurde bei aktivierter Option
  „Nur Originale/Repräsentate exportieren" fälschlich herausgefiltert (leeres PDF
  mit Platzhalter). Er wird nun korrekt als Original behandelt und immer exportiert.

## [0.1.3] - 2025-11-23

- GitHub-Versionschecker informiert über neue Versionen
- Ghostscript parallelisiert: nutzt jetzt alle Prozessorkerne (bei hoher Dateianzahl
  bis zu „Anzahl der Kerne mal" schneller)
- Die Statusleiste zeigt Informationen zu den aktuellen Bearbeitungsschritten an
- Robustere Verarbeitung von Verzeichnisnamen
- Dokumente der obersten Ebene „Einzeldokumente" werden korrekt gefiltert und auf
  Original/Repräsentat geprüft
- Button „Technische Dateien" fügt dem Filter typische Dateiendungen hinzu

## [0.1.2] - 2025-11-21

- Erste Veröffentlichung von XJustiz2PDF

[0.1.4]: https://github.com/mntxsn/XJustiz2PDF/releases/tag/v0.1.4
[0.1.3]: https://github.com/digidigital/XJustiz2PDF/releases/tag/v0.1.3
[0.1.2]: https://github.com/digidigital/XJustiz2PDF/releases/tag/v0.1.2
