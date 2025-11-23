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

'''
gui_io.py
'''

import os
from PySide6.QtWidgets import QFileDialog, QMessageBox
from PySide6.QtCore import QStandardPaths
from .utils import prepare_input, cleanup_temp, debug

class IOHandlerMixin:
    def _documents_default_dir(self) -> str:
        """
        Liefert plattformunabhängig den Dokumente-Ordner.
        Fallbacks: HOME, dann aktuelles Arbeitsverzeichnis.
        """
        docs = QStandardPaths.writableLocation(QStandardPaths.DocumentsLocation)
        if docs and os.path.isdir(docs):
            return docs
        home = os.path.expanduser("~")
        if home and os.path.isdir(home):
            # Häufiger Fall: "Documents" unter HOME, wenn QStandardPaths nichts liefert
            candidate = os.path.join(home, "Documents")
            return candidate if os.path.isdir(candidate) else home
        return os.getcwd()

    def _start_dir(self, setting_key: str) -> str:
        """
        Ermittelt den Startordner für Dialoge:
        - gespeicherter Pfad (wenn vorhanden und existent)
        - sonst: Dokumente-Ordner (Fallbacks eingebaut)
        """
        saved = self.settings.value(setting_key, "", type=str)
        if saved and os.path.isdir(saved):
            return saved
        return self._documents_default_dir()

    def _remember_dir(self, setting_key: str, any_path: str):
        """
        Merkt sich nur den Ordner (nicht die Datei).
        """
        if not any_path:
            return
        directory = any_path
        # Falls ein Datei-Pfad übergeben wurde, extrahiere den Ordner
        if not os.path.isdir(any_path):
            directory = os.path.dirname(any_path) or any_path
        if directory and os.path.isdir(directory):
            self.settings.setValue(setting_key, directory)

    def choose_input(self):
        start_dir = self._start_dir("last_input_dir")
        path, _ = QFileDialog.getOpenFileName(
            self, "XML/ZIP wählen", start_dir, "XML/ZIP (*.xml *.zip)"
        )
        if not path:
            return
        self.input_edit.setText(path)
        # Nur den Ordner merken (nicht die ausgewählte Datei)
        self._remember_dir("last_input_dir", path)
        try:
            xml_path, base_dir, temp_dir = prepare_input(path)
            self.statusBar().showMessage("XML wird geparst…")
            self.root_node = self.parser.parse(xml_path)
            self.populate_tree()
            self.statusBar().showMessage("XML erfolgreich geparst.")
            cleanup_temp(temp_dir)
        except Exception as e:
            self.root_node = None
            self.tree.clear()
            self.statusBar().showMessage("Fehler beim Parsen der XML.")
            QMessageBox.critical(
                self, "Fehler", f"Beim Parsen der XML ist ein Fehler aufgetreten:\n{e}"
            )
        finally:
            self.update_build_button_state()

    def choose_output(self):
        start_dir = self._start_dir("last_output_dir")
        path, _ = QFileDialog.getSaveFileName(
            self, "Ziel-PDF wählen", start_dir, "PDF (*.pdf)"
        )
        if not path:
            return
        self.out_edit.setText(path)
        # Nur den Ordner merken (nicht die Datei)
        self._remember_dir("last_output_dir", path)
        self.update_build_button_state()
