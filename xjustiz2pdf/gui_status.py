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
gui_status.py
'''

from PySide6.QtWidgets import QMessageBox

class StatusHandlerMixin:
    def on_progress(self, msg: str):
        self.statusBar().showMessage(f"Aktuell hinzugefügt: {msg}")

    def on_finished(self):
        self.set_enabled(True)
        self.statusBar().showMessage("Fertig – PDF erstellt.")
        QMessageBox.information(self, "Fertig", "PDF wurde erfolgreich erstellt.")
        self.update_build_button_state()

    def on_error(self, err: str):
        self.set_enabled(True)
        self.statusBar().showMessage("Fehler bei der Konvertierung.")
        QMessageBox.critical(self, "Fehler", err)
        self.update_build_button_state()
