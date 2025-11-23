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
GUI-Modulstruktur 

- gui.py              → Einstiegspunkt, MainWindow-Klasse
- gui_tree.py         → TreeView-Logik (populate_tree, Propagation, TriState)
- gui_io.py           → Input/Output-Handler (choose_input, choose_output)
- gui_build.py        → PDF-Build-Logik (build_pdf, update_build_button_state)
- gui_status.py       → Status- und Progress-Handling (on_progress, on_finished, on_error)
- gui_helpers.py      → Kleine Hilfsfunktionen für TreeView

"""
import os
import requests  # NEU: GitHub API für Release-Check
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QGridLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QCheckBox, QComboBox,
    QGroupBox, QRadioButton, QVBoxLayout
)
from PySide6.QtGui import QIcon
from PySide6.QtCore import QSettings, Qt  # NEU: Qt für Zentrierung
from .parser import AktenParser, DocNode
from .pdfbuilder import PDFBuilder
from .utils import find_ghostscript, resource_path

# Importiere die modularisierten Mixins
from .gui_tree import TreeHandlerMixin
from .gui_io import IOHandlerMixin
from .gui_build import BuildHandlerMixin
from .gui_status import StatusHandlerMixin
from xjustiz2pdf import __version__

class MainWindow(QMainWindow,
                 TreeHandlerMixin,
                 IOHandlerMixin,
                 BuildHandlerMixin,
                 StatusHandlerMixin):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"XJustiz2PDF {__version__} | XJustiz E-Akte → PDF-Akte")
        self.setFixedSize(840, 750)

        # Icon über resource_path laden
        icon_path = resource_path("icons", "programmicon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        # Kernobjekte
        self.parser = AktenParser()
        self.builder = PDFBuilder()
        self.settings = QSettings("digidigital", "XJustiz2PDF")

        self.root_node: DocNode | None = None
        self.disabled_nodes_paths: set[str] = set()
        self.check_states: dict[str, int] = {}
        self.ghostscript_path = find_ghostscript()

        # Setup der GUI-Elemente
        self._setup_ui()
        self._setup_persistence_hooks()
        self.statusBar().showMessage("Bereit.")

    def _check_latest_release(self):
        """
        Gibt (latest_tag, release_url) zurück, oder (None, None) bei Fehler/Offline.
        """
        try:
            url = "https://api.github.com/repos/digidigital/XJustiz2PDF/releases/latest"
            r = requests.get(url, timeout=5)
            r.raise_for_status()
            data = r.json()
            return data.get("tag_name"), data.get("html_url")
        except Exception:
            return None, None

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)

        # Grid-Layout für Hauptinhalte
        grid_container = QWidget()
        grid = QGridLayout(grid_container)
        grid.setColumnStretch(1, 1)
        main_layout.addWidget(grid_container)

        # Eingabe
        self.input_label = QLabel("Eingabe:")
        self.input_edit = QLineEdit()
        self.input_edit.setReadOnly(True)
        self.input_btn = QPushButton("XML/ZIP wählen")
        self.input_btn.clicked.connect(self.choose_input)
        grid.addWidget(self.input_label, 0, 0)
        grid.addWidget(self.input_edit, 0, 1)
        grid.addWidget(self.input_btn, 0, 2)

        # TreeView
        self._setup_tree(grid)

        # Ausgabe
        self.out_label = QLabel("Ausgabe:")
        self.out_edit = QLineEdit()
        self.out_edit.setReadOnly(True)
        self.out_btn = QPushButton("Ziel-PDF wählen")
        self.out_btn.clicked.connect(self.choose_output)
        grid.addWidget(self.out_label, 4, 0)
        grid.addWidget(self.out_edit, 4, 1)
        grid.addWidget(self.out_btn, 4, 2)

        # Ausfiltern
        self.filter_label = QLabel("Ausfiltern:")
        self.filter_edit = QLineEdit()
        grid.addWidget(self.filter_label, 5, 0)
        grid.addWidget(self.filter_edit, 5, 1, 1, 2)
        self.filter_edit.setText(self.settings.value("filter_terms", ""))

        # Optionen
        self.only_originals_cb = QCheckBox("Nur Originale/Repräsentate exportieren")
        self.flat_outline_cb = QCheckBox("Flaches Inhaltsverzeichnis erzeugen")
        self.sort_label = QLabel("Sortierreihenfolge (Veraktungsdatum):")
        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["original", "absteigend", "aufsteigend"])

        # Automatisches Laden der gespeicherten Werte
        self.only_originals_cb.setChecked(self.settings.value("only_originals", False, type=bool))
        self.flat_outline_cb.setChecked(self.settings.value("flat_outline", False, type=bool))
        self.sort_combo.setCurrentText(self.settings.value("sort_order", "original"))
        options_row = QHBoxLayout()
        options_row.addWidget(self.only_originals_cb)
        options_row.addStretch(1)
        options_row.addWidget(self.flat_outline_cb)
        options_row.addStretch(1)
        options_row.addWidget(self.sort_label)
        options_row.addWidget(self.sort_combo)
        options_row.addStretch(1)
        grid.addLayout(options_row, 6, 0, 1, 3)

        # Nachbearbeitung
        if self.ghostscript_path:
            self.post_group = QGroupBox("Optionale Nachbearbeitungsoptionen")
            post_layout = QGridLayout()
            self.post_none_rb = QRadioButton("Keine Nachbearbeitung (Standard)")
            self.post_none_rb.setChecked(True)
            self.post_gs_rb = QRadioButton("Qualität anpassen mit Ghostscript")
            self.post_gs_quality_label = QLabel("Qualitätsstufe:")
            self.post_gs_quality_combo = QComboBox()
            self.post_gs_quality_combo.addItems(["screen", "ebook", "printer", "prepress"])
            row_gs = QHBoxLayout()
            row_gs.addWidget(self.post_gs_rb)
            row_gs.addStretch(1)
            row_gs_params = QHBoxLayout()
            row_gs_params.addWidget(self.post_gs_quality_label)
            row_gs_params.addWidget(self.post_gs_quality_combo)
            row_gs_params.addStretch(1)
            post_layout.addWidget(self.post_none_rb, 0, 0, 1, 3)
            post_layout.addLayout(row_gs, 1, 0, 1, 3)
            post_layout.addLayout(row_gs_params, 2, 0, 1, 3)
            self.post_group.setLayout(post_layout)
            grid.addWidget(self.post_group, 7, 0, 1, 3)

        # Build button
        self.build_btn = QPushButton("PDF erstellen")
        self.build_btn.setToolTip(
            "Wird aktiv (grün), sobald XML geladen, Akteninhalt gewählt und Ziel-PDF gesetzt."
        )
        self.build_btn.clicked.connect(self.build_pdf)
        self.build_btn.setEnabled(False)
        self.update_build_button_style()
        grid.addWidget(self.build_btn, 8, 0, 1, 3)
        # Links
        links_layout = QHBoxLayout()
        self.help_link = QLabel(
            '<a href="https://github.com/digidigital/XJustiz2PDF/issues">Hilfe & Support</a>'
        )
        self.homepage_link = QLabel(
            '<a href="https://xjustiz2pdf.digidigital.de">XJustiz2PDF Homepage</a>'
        )
        self.help_link.setStyleSheet("font-size: 8pt;")
        self.homepage_link.setStyleSheet("font-size: 8pt;")
        self.help_link.setOpenExternalLinks(True)
        self.homepage_link.setOpenExternalLinks(True)
        links_layout.addStretch(1)
        links_layout.addWidget(self.help_link)
        
        # Versionshinweis zwischen den Links
        latest_tag, release_url = self._check_latest_release()
        if latest_tag and latest_tag != __version__:
            links_layout.addStretch(1)
            self.update_label = QLabel(
                f'<a href="{release_url}">Neue Version {latest_tag} verfügbar</a>'
            )
            #self.update_label.setAlignment(Qt.AlignCenter)
            self.update_label.setStyleSheet("font-size: 8pt;")
            self.update_label.setOpenExternalLinks(True)
            links_layout.addWidget(self.update_label)
            links_layout.addStretch(1)
        else:
            links_layout.addStretch(2)
        links_layout.addWidget(self.homepage_link)
        links_layout.addStretch(1)
        grid.addLayout(links_layout, 9, 0, 1, 3)



    def _setup_persistence_hooks(self):
        self.filter_edit.textChanged.connect(
            lambda txt: self.settings.setValue("filter_terms", txt)
        )
        self.only_originals_cb.toggled.connect(
            lambda checked: self.settings.setValue("only_originals", checked)
        )
        self.flat_outline_cb.toggled.connect(
            lambda checked: self.settings.setValue("flat_outline", checked)
        )
        self.sort_combo.currentTextChanged.connect(
            lambda txt: self.settings.setValue("sort_order", txt)
        )
        if hasattr(self, "post_none_rb"):
            self.post_none_rb.toggled.connect(
                lambda checked: self.settings.setValue("post_none", checked)
            )
        if hasattr(self, "post_gs_rb"):
            self.post_gs_rb.toggled.connect(
                lambda checked: self.settings.setValue("post_ghostscript", checked)
            )
        if hasattr(self, "post_gs_quality_combo"):
            self.post_gs_quality_combo.currentTextChanged.connect(
                lambda txt: self.settings.setValue("post_gs_quality", txt)
            )
