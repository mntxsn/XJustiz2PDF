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
# worker.py — unveränderte Schnittstellen; Build intern parallelisiert

'''
worker.py
'''

import os, sys, subprocess, tempfile, shutil
from PySide6.QtCore import QObject, Signal
from .utils import prepare_input, cleanup_temp, debug
from .parser import AktenParser
from .pdfbuilder import PDFBuilder

class PdfWorker(QObject):
    finished = Signal()
    error = Signal(str)
    progress = Signal(str)

    def __init__(self, parser, builder, in_path, out, filter_terms,
                 only_originals, sort_order, disabled_paths,
                 post_option="none", post_params=None):
        super().__init__()
        self.parser = parser
        self.builder = builder
        self.in_path = in_path
        self.out = out
        self.filter_terms = filter_terms
        self.only_originals = only_originals
        self.sort_order = sort_order
        self.disabled_paths = disabled_paths or []
        self.post_option = post_option
        self.post_params = post_params or {}

    def run(self):
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                debug(f"[Worker] Starte Verarbeitung, tmpdir={tmpdir}")
                xml_path, base_dir, temp_dir = prepare_input(self.in_path)
                debug(f"[Worker] Eingabe vorbereitet: xml={xml_path}, base_dir={base_dir}")

                root = self.parser.parse(xml_path)
                debug("[Worker] XML geparst, starte PDFBuilder.")

                def status_cb(msg):
                    self.progress.emit(msg)
                    debug(f"[Worker] Fortschritt: {msg}")

                self.builder.sort_order = self.sort_order

                tmp_initial = os.path.join(tmpdir, "initial.pdf")
                debug(f"[Worker] Erzeuge finale PDF (mit optionaler Parallel-Optimierung): {tmp_initial}")
                self.builder.build(root, base_dir, tmp_initial,
                                   status_callback=status_cb,
                                   filter_terms=self.filter_terms,
                                   only_originals=self.only_originals,
                                   disabled_paths=set(self.disabled_paths),
                                   post_option=self.post_option,
                                   post_params=self.post_params)
                cleanup_temp(temp_dir)

                debug(f"[Worker] Kopiere finale PDF nach Ziel: {self.out}")
                shutil.copyfile(tmp_initial, self.out)

            debug("[Worker] Verarbeitung abgeschlossen.")
            self.finished.emit()
        except Exception as e:
            debug(f"[Worker] Fehler: {e}")
            self.error.emit(str(e))
