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

from PySide6.QtWidgets import QFileDialog, QMessageBox
from .utils import prepare_input, cleanup_temp, debug

class IOHandlerMixin:
    def choose_input(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "XML/ZIP wählen", "", "XML/ZIP (*.xml *.zip)"
        )
        if not path:
            return
        self.input_edit.setText(path)
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
        path, _ = QFileDialog.getSaveFileName(
            self, "Ziel-PDF wählen", "", "PDF (*.pdf)"
        )
        if path:
            self.out_edit.setText(path)
            self.update_build_button_state()
