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
Dies ist der Einstiegspunkt für das Modul. 
Wenn man `python -m xjustiz2pdf` ausführt, startet automatisch die GUI.
Die GUI wird über MainWindow bereitgestellt. 
Fehler werden abgefangen, Debug-Ausgaben erfolgen wenn in __init__.py __debugstate__=True 
"""

import sys
import multiprocessing
from PySide6.QtWidgets import QApplication
from .gui import MainWindow
from .utils import debug

def main():
    try:
        app = QApplication(sys.argv)
        win = MainWindow()
        win.show()
        debug("[Main] GUI gestartet")
        sys.exit(app.exec())
    except Exception as e:
        debug(f"[Main] Fehler beim Starten der GUI: {e}")
        raise

if __name__ == "__main__":
    multiprocessing.freeze_support() # Nur zur Sicherheit ;)
    main()
