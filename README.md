# xjustiz2pdf

**English introduction:**  
xjustiz2pdf is a desktop application that converts German *xJustiz* electronic legal communication (ERV) messages and e‑files (*E‑Akte*) into single PDF documents with an outline that preserves structure of the source. It provides a graphical user interface (GUI) for selecting, filtering, and exporting documents with structured bookmarks.

---

## Bedienungsanleitung

### Über die Anwendung
Mit xjustiz2pdf können Nachrichten im xJustiz‑Format (ERV) sowie elektronische Akten der deutschen Justiz / Verwaltung komfortabel in PDF‑Dokumente umgewandelt werden. Die Anwendung bietet eine grafische Oberfläche, um Dokumente und Akten(teile) auszuwählen, zu sortieren und mit einem Inhaltsverzeichnis in ein einzelnes PDF-Dokument zu exportieren. 

Die Anwendung ist weitestgehend plattformunabhängig und läuft somit unter Windows, Linux und macOS. 
- Der Export von PDF-Dokumenten und Bilddateien wird ohne die Installation von Zusatzprogrammen unterstützt. 
- Sofern die Anwender [LibreOffice](https://de.libreoffice.org/download/download/) auf ihrem System installiert haben, können diverse Office-Formate konvertiert und beim Export in die PDF-Akte berücksichtigt werden.
- Falls auch die Anwendung [Ghostscript](https://ghostscript.com/releases/gsdnld.html) auf dem Anwendersystem installiert ist, besteht zudem die Möglichkeit, die Dateigröße der Akte deutlich zu reduzieren. 

![Screenshot der Xjustiz2PDF Benutzeroberfläche](https://github.com/digidigital/XJustiz2PDF/blob/main/Images/Screenshot_XJustiz2PDF_Konverter.png)

## Installation und Start der Anwendung
### Installation über PyPI - Python Package Index  
  ```bash
  pip install xjustiz2pdf
  ```
- (Optional) Installiere LibreOffice über einen Paketmanager oder nach Download von: [LibreOffice Download-Seite](https://de.libreoffice.org/download/download/)
- (Optional) Installiere Ghostscript über einen Paketmanager oder nach Download von: [Ghostscript Download-Seite](https://ghostscript.com/releases/gsdnld.html)

Start des Prgramms mit:  
  ```bash
  python -m xjustiz2pdf
  ```
  oder
  ```bash
  xjustiz2pdf
  ```

### Installation mit Windows-Installer
Den Windows-Installer findest du auf [Github](https://github.com/digidigital/XJustiz2PDF/releases).

Optional:
- Installiere LibreOffice, um Office-Formate zu konvertieren. Download von: [LibreOffice Download-Seite](https://de.libreoffice.org/download/download/)
- Installiere Ghostscript, um PDF-Akten verkleinern zu können. Download von: [Ghostscript Download-Seite](https://ghostscript.com/releases/gsdnld.html)

### Hauptfenster
Nach dem Start öffnet sich das Hauptfenster mit folgenden Bereichen:

- **Eingabe**: Auswahl einer XML‑ oder ZIP‑Datei mit xJustiz‑Nachrichten (Bei der Auswahl von ZIP-Dateien wird eine xjustiz_nachricht.xml in der obersten Ebene erwartet und automatisch eingelesen). 
- **Baumansicht**: Zeigt die komplette Aktenstruktur. Jeder Ordner kann einzeln angehakt werden. Nur Dokumente in Ordnern mit einem ☑ werden exportiert!   
- **Alle Haken entfernen**: Entfernt alle Häkchen im Baum. 
- **Ausgabe**: Zielpfad für die zu erzeugende PDF‑Akte/PDF-Datei.  
- **Ausfiltern**: Eingabefeld für mit Leerzeichen getrennte Suchbegriffe, um bestimmte Dokumente gezielt vom Export auszuschließen. Beispiel: "protokoll" filtert "Besprechungsprotokoll" und "Signaturprotokoll"  
- **Optionen**:
  - *Nur Originale/Repräsentate exportieren*: Lässt automatisch alle nicht als Original bzw. Repräsentat gekennzeichnete Dokumente aus (z. B. Signaturen).  
  - *Flaches Inhaltsverzeichnis*: Erzeugt ein einfaches Inhaltsverzeichnis ohne Hierarchie (alle Dokumente "in einem Topf").
  - *Sortierung*: Wahlweise Originalreihenfolge, aufsteigend oder absteigend nach Veraktungsdatum.  
  
- **Optionale Nachbearbeitungsoptionen** (Wird nur angezeigt, wenn Ghostscript installiert wurde)
   - Keine Nachbearbeitung(Standard)
   - Qualität anpassen mit Ghostscript.  Die Qualitässtufen von niedriger zu hoher Qualität lauten "screen"→"ebook"→"printer"→"prepress". Dieser Bearbeitungsschritt kann in Abhängigkeit vom Umfang des Akteninhalts sehr viel Zeit benötigen! 

- **PDF erzeugen**: Startet den Umwandlungsprozess. Wird aktiviert und grün, sobald Ein- und Ausgabedatei festgelegt wurden und mindestens ein Haken gesetzt wurde.  
 
## Hinweis
Die Ergebnisse des Exports können variieren, da es eine Vielzahl von Aktenverwaltungssoftware gibt und sich die E-Akten daher in ihremm Aufbau unterscheiden können. Da es sich bei der Umwandlung der E-Akte um einen Umwandlungsprozess handelt, entsprechen die resultierenden Dateien nicht mehr dem Original. Es ist nicht auszuschließen, dass Informationen (z.B. gehen Inhaltverzeichnisse der Originale verloren) und Details (Qualitätsverlust durch Komprimierung) verloren gehen. Trage Sorge, dass du die Originalakte zur späteren Verwendung archivierst.  

Für die Arbeit mit der Originalakte empfehle ich [openXJV](https://openxjv.de).

---

### Bedienung Schritt für Schritt
1. **Datei laden**  
   - Wähle über *Eingabe* eine XML‑ oder ZIP‑Datei.  
   - Die Aktenstruktur wird im Baum angezeigt.

2. **Dokumente auswählen**  
   - Setze Häkchen bei den gewünschten Ordnern oder Dokumenten.  
   - Teilweise gesetzte Häkchen "-" erzeugen leere Container im Inhaltsverzeichnis, ohne deren Dokumente selbst zu übernehmen.

3. **Filter anwenden (optional)**  
   - Gib (Teil-)Begriffe ein, um bestimmte Dokumente auszublenden. Trenne mit Leerzeichen.  
   - Aktiviere *Nur Originale/Repräsentate exportieren*, um z. B. automatisch Signaturprotokolle und Transfervermerke zu ignorieren.

4. **Sortierung festlegen**  
   - Wähle die gewünschte Reihenfolge (Original, aufsteigend, absteigend).

6. **(Optional) Größe und Qualität der Zieldatei beeinflussen**  
    - Sofern Ghostscript auf deinem System installiert ist, kannst du die Ausgabequalität in vier Schritten beeinflussen: *screen*, *ebook*, *print*, *prepress*.

6. **PDF erzeugen**  
   - Klicke auf *PDF erzeugen*.  
   - Der Fortschritt wird im Statusbereich angezeigt.  
   - Nicht unterstützte Dateitypen oder fehlende Dokumente werden automatisch durch Platzhalterseiten ersetzt, sodass der Prozess nicht abbricht.

7. **Ergebnis prüfen**  
   - Die erzeugte PDF enthält ein Inhaltsverzeichnis entsprechend der Baumstruktur des Originals. Bei flachem Inhaltsverzeichnis wird die Baumstruktur ignoriert.  
   - Dokumente sind sortiert und gefiltert wie eingestellt.

---

### Fehlerbehandlung
- **Nicht‑PDF‑Dateien**: Werden nach Möglichkeit in PDF konvertiert oder durch Platzhalterseiten ersetzt.  
- **Fehlende Dateien**: Ebenfalls Platzhalter mit Hinweistext.  
- **Leere Auswahl oder alle Dokumente ausgefiltert**: Erzeugt eine PDF mit einer Hinweisseite („Keine Dokumente ausgewählt“).

---

### Tipps
- Nutze "-" für Ordner, wenn du die Struktur im Inhaltsverzeichnis erhalten, aber keine Dokumente übernehmen möchtest.  
- Mit *Flaches Inhaltsverzeichnis* erhältst du eine einfache Aneinanderreihung aller ausgewählten Dokumente ohne Hierarchie. Nutze in diesem Fall ggf. die Option zur Anpassung der Sortierreihenfolge, da die Elemente sonst die Reihenfolge beibehalten, die sie gehabt hätten, wenn sie noch in Ordner/Teilakten einsortiert wären.  
---

## Lizenz
xjustiz2pdf ist Open Source unter GPLv3-Lizenz (FOSS mit ❤️) und richtet sich an Anwender:innen und Entwickler:innen, die mit xJustiz‑Nachrichten und E-Akten arbeiten dürfen oder müssen.
