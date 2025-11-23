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
Dieses Modul unils.py enthält Hilfsfunktionen für das Projekt.

- debug(): einfache Debug-Ausgabe, wenn DEBUG=True gesetzt ist.
- prepare_input(): entpackt ZIP-Dateien oder prüft XML-Dateien und liefert Pfade zurück.
- cleanup_temp(): entfernt temporäre Verzeichnisse nach der Verarbeitung.
- find_ghostscript(): versucht Ghostscript in typischen Installationspfaden oder im PATH zu finden.
- resource_path(): liefert einen Pfad zu Ressourcen relativ zum Modulverzeichnis (z.B. Icons).
"""

import os
import tempfile
import zipfile
import shutil
from xjustiz2pdf import __debugstate__

DEBUG = __debugstate__

def debug(msg: str):
    if DEBUG:
        print(msg)


def prepare_input(path: str):
    if path.lower().endswith(".zip"):
        temp_dir = tempfile.mkdtemp(prefix="xjustiz_")
        with zipfile.ZipFile(path, "r") as z:
            z.extractall(temp_dir)
        xml_path = os.path.join(temp_dir, "xjustiz_nachricht.xml")
        if not os.path.exists(xml_path):
            raise FileNotFoundError("xjustiz_nachricht.xml nicht in ZIP gefunden.")
        return xml_path, temp_dir, temp_dir
    else:
        if not os.path.exists(path):
            raise FileNotFoundError(f"XML nicht gefunden: {path}")
        return path, os.path.dirname(path), None


def cleanup_temp(temp_dir: str):
    if temp_dir and os.path.isdir(temp_dir):
        shutil.rmtree(temp_dir, ignore_errors=True)


def find_ghostscript() -> str | None:  
    exe_names = ["gswin64c.exe", "gswin32c.exe"]

    def check_registry(exe_names) -> str | None:
        try:
            import winreg  # Lazy Import
        except ImportError:
            debug("[Utils] winreg nicht verfügbar (kein Windows)")
            return None
        reg_paths = [
            r"SOFTWARE\GPL Ghostscript",
            r"SOFTWARE\WOW6432Node\GPL Ghostscript"
        ]
        for reg_path in reg_paths:
            try:
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_path) as key:
                    i = 0
                    while True:
                        try:
                            subkey_name = winreg.EnumKey(key, i)
                            with winreg.OpenKey(key, subkey_name) as subkey:
                                dll_path, _ = winreg.QueryValueEx(subkey, "GS_DLL")
                                
                                if dll_path:
                                    print(dll_path)
                                    bin_dir = os.path.dirname(dll_path)
                                    for exe in exe_names:
                                        cand = os.path.join(bin_dir, exe)
                                        if os.path.isfile(cand):
                                            debug(f"[Utils] Ghostscript gefunden (Registry): {cand}")
                                            return cand
                        except OSError:
                            break
                        i += 1
            except FileNotFoundError:
                continue
        return None

    if os.name == "nt":
        # 1. PATH durchsuchen
        for exe in exe_names:
            cand = shutil.which(exe)
            if cand:
                debug(f"[Utils] Ghostscript gefunden (PATH): {cand}")
                return cand
       
        # 2. Registry prüfen
        cand = check_registry(exe_names)
        if cand:
            return cand
        
        # 3. Fallback: bekannte Ordnerstruktur
        search_roots = [
            os.environ.get("ProgramFiles", r"C:\Program Files"),
            os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
            os.environ.get("LOCALAPPDATA", r"C:\Users\%USERNAME%\AppData\Local"),
        ]
        for root in search_roots:
            if not root:
                continue
            gs_root = os.path.join(root, "gs")
            if not os.path.isdir(gs_root):
                continue
            
            for dirpath, _, files in os.walk(gs_root):
                for exe in exe_names:
                    if exe in files:
                        cand = os.path.join(dirpath, exe)
                        debug(f"[Utils] Ghostscript gefunden (Ordnerstruktur): {cand}")
                        return cand

    else:
        # Linux/macOS
        cand = shutil.which("gs")
        if cand:
            debug(f"[Utils] Ghostscript gefunden (PATH): {cand}")
            return cand

    debug("[Utils] Ghostscript nicht gefunden")
    return None

def resource_path(*parts: str) -> str:
    """
    Liefert einen Pfad zu Ressourcen relativ zum Verzeichnis dieses Moduls.
    Beispiel: resource_path("icons", "programmicon.ico")
    """
    return os.path.join(os.path.dirname(__file__), *parts)
