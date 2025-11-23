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

from PySide6.QtWidgets import QMessageBox, QTreeWidgetItem
from PySide6.QtCore import QThread, Qt
from .worker import PdfWorker
from .pdfbuilder import PDFBuilder
from .utils import debug
from .parser import DocNode


class BuildHandlerMixin:
    def set_enabled(self, enabled: bool):
        widgets = [
            self.input_edit, self.input_btn,
            self.out_edit, self.out_btn,
            self.filter_edit, self.only_originals_cb,
            self.sort_combo, self.flat_outline_cb,
            self.tree,
            self.build_btn,
            self.clear_checks_btn
        ]
        if hasattr(self, "post_group"):
            widgets += [self.post_group, self.post_none_rb]
            if hasattr(self, "post_gs_rb"):
                widgets += [self.post_gs_rb, self.post_gs_quality_combo]
        for w in widgets:
            w.setEnabled(enabled)

    def update_build_button_style(self):
        if self.build_btn.isEnabled():
            self.build_btn.setStyleSheet(
                "QPushButton { background-color: #28a745; color: white; font-weight: bold; }"
            )
        else:
            self.build_btn.setStyleSheet("")

    def validate_tree_has_checked(self) -> bool:
        count_checked = 0
        def walk(item):
            nonlocal count_checked
            if item.checkState(0) == Qt.Checked:
                count_checked += 1
            for i in range(item.childCount()):
                walk(item.child(i))
        for i in range(self.tree.topLevelItemCount()):
            walk(self.tree.topLevelItem(i))
        return count_checked > 0

    def update_build_button_state(self):
        ready = (
            bool(self.input_edit.text().strip())
            and bool(self.out_edit.text().strip())
            and self.validate_tree_has_checked()
        )
        self.build_btn.setEnabled(ready)
        self.update_build_button_style()

    def _collect_disabled_paths(self) -> set[tuple[str, ...]]:
        """
        Liefert nur Pfade, die explizit Unchecked sind.
        PartiallyChecked wird NICHT als disabled behandelt.
        """
        paths: set[tuple[str, ...]] = set()
        def walk(item):
            marker = item.data(0, Qt.UserRole)
            state = item.checkState(0)
            if state == Qt.Unchecked and marker:
                # Konvertiere Liste → Tuple
                if isinstance(marker, list):
                    marker = tuple(marker)
                paths.add(marker)
            for i in range(item.childCount()):
                walk(item.child(i))
        for i in range(self.tree.topLevelItemCount()):
            walk(self.tree.topLevelItem(i))
        debug(f"[GUI] collect_disabled_paths: total={len(paths)} examples={[ ' / '.join(p) for p in list(paths)[:5] ]}")
        return paths

    def _collect_check_states(self) -> dict[tuple[str, ...], int]:
        """
        Sammelt alle States aus dem Baum, inkl. PartiallyChecked.
        """
        states: dict[tuple[str, ...], int] = {}
        def walk(item):
            marker = item.data(0, Qt.UserRole)
            state = item.checkState(0)
            if marker is not None:
                # Konvertiere Liste → Tuple
                if isinstance(marker, list):
                    marker = tuple(marker)
                states[marker] = state
            for i in range(item.childCount()):
                walk(item.child(i))
        for i in range(self.tree.topLevelItemCount()):
            walk(self.tree.topLevelItem(i))
        debug(f"[GUI] collect_check_states: total={len(states)} examples={[(' / '.join(k), v) for k, v in list(states.items())[:5]]}")
        return states

    def build_pdf(self):
        in_path = self.input_edit.text().strip()
        out = self.out_edit.text().strip()
        filter_terms = self.filter_edit.text().strip().split()
        only_originals = self.only_originals_cb.isChecked()
        sort_order = self.sort_combo.currentText()
        flat_outline = self.flat_outline_cb.isChecked()

        if not in_path or not out:
            QMessageBox.warning(self, "Fehler", "Bitte Eingabe und Ziel-PDF angeben.")
            return
        if not self.validate_tree_has_checked():
            QMessageBox.warning(self, "Fehler", "Mindestens ein Aktenstruktur-Eintrag muss angehakt sein.")
            return

        post_option = "none"
        post_params = {}
        if hasattr(self, "post_gs_rb") and self.post_gs_rb.isChecked():
            post_option = "ghostscript"
            post_params = {
                "quality": self.post_gs_quality_combo.currentText(),
                "gs_path": self.ghostscript_path
            }

        # Sammle beide Sichten direkt aus dem Baum
        self.disabled_nodes_paths = self._collect_disabled_paths()
        builder_check_states = self._collect_check_states()

        debug(f"[GUI] disabled_paths={[ ' / '.join(p) for p in list(self.disabled_nodes_paths) ]}")
        debug(f"[GUI] builder_check_states(keys)={[ ' / '.join(k) for k in list(builder_check_states.keys())[:10] ]}")

        self.set_enabled(False)
        self.statusBar().showMessage("Die Akte wird konvertiert. Dies kann einige Zeit in Anspruch nehmen.")

        self.thread = QThread()
        self.worker = PdfWorker(
            parser=self.parser,
            builder=PDFBuilder(sort_order=sort_order, flat_outline=flat_outline),
            in_path=in_path,
            out=out,
            filter_terms=filter_terms,
            only_originals=only_originals,
            sort_order=sort_order,
            disabled_paths=list(self.disabled_nodes_paths),
            post_option=post_option,
            post_params=post_params
        )
        # Entscheidend: übergebe die tatsächlich gesammelten States
        self.worker.builder.check_states = builder_check_states

        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.on_finished)
        self.worker.error.connect(self.on_error)
        self.worker.progress.connect(self.on_progress)
        self.worker.finished.connect(self.thread.quit)
        self.worker.error.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.error.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()


    # Hilfsfunktion zum Aufbau des Tree mit Tupel-Markern
    def add_node_to_tree(self, node: DocNode, parent_item, path_here: tuple[str, ...]):
        item = QTreeWidgetItem(parent_item)
        item.setText(0, node.anzeigename or "Unbenannt")
        item.setCheckState(0, Qt.Unchecked)
        # WICHTIG: Marker als Tupel speichern
        marker = path_here
        item.setData(0, Qt.UserRole, marker)

        for child in node.children:
            if child.is_folder():
                child_path = path_here + (child.anzeigename or "Akte",)
                self.add_node_to_tree(child, item, child_path)
            elif child.is_doc():
                doc_path = path_here + (child.anzeigename or "Dokument",)
                self.add_node_to_tree(child, item, doc_path)
