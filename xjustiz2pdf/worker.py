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
                debug(f"[Worker] Erzeuge initiale PDF: {tmp_initial}")
                self.builder.build(root, base_dir, tmp_initial,
                                   status_callback=status_cb,
                                   filter_terms=self.filter_terms,
                                   only_originals=self.only_originals,
                                   disabled_paths=set(self.disabled_paths))
                cleanup_temp(temp_dir)

                final_tmp_pdf = tmp_initial
                if self.post_option == "ghostscript":
                    final_tmp_pdf = self._process_with_ghostscript(
                        pdf_path=tmp_initial,
                        quality=self.post_params.get("quality", "ebook"),
                        gs_path=self.post_params.get("gs_path"),
                        tmpdir=tmpdir
                    )

                debug(f"[Worker] Kopiere finale PDF nach Ziel: {self.out}")
                shutil.copyfile(final_tmp_pdf, self.out)

            debug("[Worker] Verarbeitung abgeschlossen.")
            self.finished.emit()
        except Exception as e:
            debug(f"[Worker] Fehler: {e}")
            self.error.emit(str(e))
            # Kein Re-raise, damit die Anwendung nicht hängt

    # ---------- Post-processing methods ----------

    def _process_with_ghostscript(self, pdf_path: str, quality: str, gs_path: str, tmpdir: str) -> str:
        """
        Führt eine optionale Ghostscript-Optimierung durch, falls gs_path vorhanden ist.
        Robust, mit Fehlerfang. Nutzt -dSAFER und deaktiviert aktive Inhalte.
        """
        try:
            debug(f"[Worker] Starte Ghostscript-Optimierung: Qualität={quality}, Pfad={gs_path}")
            self.status_cb_safe("PDF wird mit Ghostscript optimiert…")

            if not gs_path or not os.path.isfile(gs_path):
                debug("[Worker] Ghostscript-Pfad ungültig oder nicht angegeben – überspringe.")
                return pdf_path

            tmp_out = os.path.join(tmpdir, "gs.pdf")
            cmd = [
                gs_path,
                "-sDEVICE=pdfwrite",
                "-dSAFER",
                "-dCompatibilityLevel=1.7",
                "-sProcessColorModel=DeviceRGB",
                "-sColorConversionStrategy=RGB",
                "-dOverrideICC=true",
                "-dEmbedAllFonts=true",
                "-dSubsetFonts=true",
                f"-dPDFSETTINGS=/{quality}",
                "-dDisableJavaScripts=true",
                "-dNOPAUSE",
                "-dQUIET",
                "-dBATCH",
                f"-sOutputFile={tmp_out}",
                pdf_path
            ]

            # Plattformabhängige Flags setzen
            kwargs = {}
            if sys.platform.startswith("win"):
                CREATE_NO_WINDOW = 0x08000000
                kwargs["creationflags"] = CREATE_NO_WINDOW
            else:
                kwargs["stdout"] = subprocess.DEVNULL
                kwargs["stderr"] = subprocess.DEVNULL

            subprocess.run(cmd, check=True, **kwargs)

            self.status_cb_safe("Ghostscript-Optimierung abgeschlossen.")
            debug(f"[Worker] Ghostscript-Ausgabe: {tmp_out}")
            return tmp_out if os.path.isfile(tmp_out) else pdf_path
        except Exception as e:
            debug(f"[Worker] Fehler bei Ghostscript: {e}")
            self.error.emit(f"Fehler bei Ghostscript: {e}")
            return pdf_path

    # ---------- Helper ----------

    def status_cb_safe(self, msg: str):
        try:
            self.progress.emit(msg)
            debug(f"[Worker] Status: {msg}")
        except Exception:
            pass
