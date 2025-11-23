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
gs_pipeline.py — Parallel-Optimierung mit Ghostscript (prozessbasiert)
'''

import os
import sys
import subprocess
import re
import uuid
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import List, Tuple, Optional
from .utils import debug

# Globale Timeout-Konfiguration
SUBPROCESS_TIMEOUT_SECONDS = 180


def _safe_filename(name: str, replacement: str = "_") -> str:
    name = (name or "").strip()
    name = re.sub(r"\s+", replacement, name)
    name = re.sub(r"[^A-Za-z0-9._-]", replacement, name)
    name = re.sub(r"{0}+".format(re.escape(replacement)), replacement, name)
    name = name.strip("._-")
    return name or "Dokument"


def _gs_cmd(gs_path: str, input_pdf: str, output_pdf: str, quality: str) -> list:
    return [
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
        f"-sOutputFile={output_pdf}",
        input_pdf
    ]
def _run_gs(gs_path: Optional[str], input_pdf: str, output_pdf: str, quality: str) -> Tuple[str, bool, Optional[str]]:
    if not gs_path or not os.path.isfile(gs_path):
        return input_pdf, False, "Ungültiger Ghostscript-Pfad"

    cmd = _gs_cmd(gs_path, input_pdf, output_pdf, quality)
    kwargs = {}
    if sys.platform.startswith("win"):
        CREATE_NO_WINDOW = 0x08000000
        kwargs["creationflags"] = CREATE_NO_WINDOW
    else:
        kwargs["stdout"] = subprocess.DEVNULL
        kwargs["stderr"] = subprocess.DEVNULL

    try:
        subprocess.run(cmd, check=True, timeout=SUBPROCESS_TIMEOUT_SECONDS, **kwargs)
        if os.path.isfile(output_pdf):
            return output_pdf, True, None
        return input_pdf, False, "Ghostscript erzeugte keine Ausgabedatei"
    except Exception as e:
        return input_pdf, False, str(e)


def parallel_optimize(
    inputs: List[str],
    out_dir: str,
    gs_path: Optional[str],
    quality: str = "ebook",
    max_workers: Optional[int] = None,
    status_callback=None
) -> List[str]:
    if not inputs:
        return []

    os.makedirs(out_dir, exist_ok=True)
    max_workers = max_workers or os.cpu_count() or 1

    outputs = []
    jobs = []
    for inp in inputs:
        base_raw = os.path.splitext(os.path.basename(inp))[0]
        base = _safe_filename(base_raw)
        unique_id = uuid.uuid4().hex[:8]
        out = os.path.join(out_dir, f"{base}_{unique_id}_gs.pdf")
        outputs.append(out)
        jobs.append((inp, out))

    results = [None] * len(inputs)

    debug(f"[GS] Starte parallele Optimierung mit {max_workers} Prozessen für {len(inputs)} Dokumente.")
    if status_callback:
        status_callback("Starte parallele Ghostscript-Optimierung…")

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        future_to_index = {
            executor.submit(_run_gs, gs_path, inp, out, quality): idx
            for idx, (inp, out) in enumerate(jobs)
        }
        for future in as_completed(future_to_index):
            idx = future_to_index[future]
            try:
                out_path, success, err = future.result()
                if success:
                    results[idx] = out_path
                else:
                    placeholder = os.path.join(out_dir, f"error_{idx}.pdf")
                    with open(placeholder, "wb") as f:
                        f.write(b"%PDF-1.4\n%EOF")
                    results[idx] = placeholder
                msg = f"Ghostscript {'Erfolgreich' if success else 'Fehler'} für {os.path.basename(jobs[idx][0])}"
                debug(f"[GS] {msg}")
                if status_callback:
                    status_callback(msg)
            except Exception as e:
                placeholder = os.path.join(out_dir, f"error_{idx}.pdf")
                with open(placeholder, "wb") as f:
                    f.write(b"%PDF-1.4\n%EOF")
                results[idx] = placeholder
                debug(f"[GS] Unerwarteter Fehler: {e}")
                if status_callback:
                    status_callback(f"Ghostscript Fehler: {e}")

    if status_callback:
        status_callback("Ghostscript-Optimierung abgeschlossen.")
    debug("[GS] Parallele Optimierung abgeschlossen.")
    return results
