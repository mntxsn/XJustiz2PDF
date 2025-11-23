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

from PySide6.QtWidgets import QLabel, QTreeWidget, QPushButton, QTreeWidgetItem
from PySide6.QtCore import Qt
from .gui_helpers import _is_checked_or_partial, _any_child_checked_or_partial
from .utils import debug

class TreeHandlerMixin:
    def _setup_tree(self, grid):
        self.tree_label = QLabel("Zu exportierende Aktenstrukturen (Nativ unterstützt: PDF und Bildformate. Der Export von Office-Formaten benötigt ein separat installiertes LibreOffice.)")
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.itemChanged.connect(self.on_tree_item_changed)
        self.tree.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.tree.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        grid.addWidget(self.tree_label, 1, 0, 1, 3)
        grid.addWidget(self.tree, 2, 0, 1, 3)

        self.clear_checks_btn = QPushButton("Alle Haken entfernen")
        self.clear_checks_btn.clicked.connect(self.clear_all_checks)
        grid.addWidget(self.clear_checks_btn, 3, 0, 1, 3)

    def populate_tree(self):
        self.tree.clear()
        if not self.root_node:
            return
        has_root_docs = any(ch.is_doc() for ch in self.root_node.children)
        if has_root_docs:
            placeholder_item = QTreeWidgetItem(["Einzeldateien"])
            placeholder_item.setFlags(placeholder_item.flags() | Qt.ItemIsUserCheckable)
            placeholder_item.setCheckState(0, Qt.Checked)
            # Marker als Tupel speichern
            placeholder_item.setData(0, Qt.UserRole, ("ROOT_DOCS",))
            self.tree.addTopLevelItem(placeholder_item)
        for ch in self.root_node.children:
            if ch.is_folder():
                item = self._create_tree_item_for_node(ch, parent_path=())
                self.tree.addTopLevelItem(item)
                
        self.tree.expandAll()
        self.update_build_button_state()

    def _create_tree_item_for_node(self, node, parent_path: tuple[str, ...]) -> QTreeWidgetItem:
        item = QTreeWidgetItem([node.anzeigename or "Akte"])
        item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
        item.setCheckState(0, Qt.Checked)
        marker = parent_path + (node.anzeigename or "Akte",)
        item.setData(0, Qt.UserRole, marker)

        # Nur Ordner als Tree-Items; keine Dokumente hinzufügen
        for ch in node.children:
            if ch.is_folder():
                child_item = self._create_tree_item_for_node(ch, parent_path=marker)
                item.addChild(child_item)
        return item

    def _parent_of(self, item: QTreeWidgetItem):
        return item.parent()

    def _propagate_up_on_child_checked(self, item: QTreeWidgetItem):
        parent = self._parent_of(item)
        while parent is not None:
            if parent.checkState(0) != Qt.Checked:
                parent.setCheckState(0, Qt.PartiallyChecked)
                path_marker = parent.data(0, Qt.UserRole)
                if path_marker:
                    if isinstance(path_marker, list):
                        path_marker = tuple(path_marker)
                    # PartiallyChecked: NICHT als disabled markieren
                    self.check_states[path_marker] = Qt.PartiallyChecked
            parent = self._parent_of(parent)

    def _propagate_up_on_child_unchecked(self, item: QTreeWidgetItem):
        parent = self._parent_of(item)
        while parent is not None:
            if parent.checkState(0) == Qt.PartiallyChecked:
                if not _any_child_checked_or_partial(parent):
                    parent.setCheckState(0, Qt.Unchecked)
                    path_marker = parent.data(0, Qt.UserRole)
                    if path_marker:
                        if isinstance(path_marker, list):
                            path_marker = tuple(path_marker)
                        # Unchecked: als disabled markieren
                        self.check_states[path_marker] = Qt.Unchecked
                        self.disabled_nodes_paths.add(path_marker)
            parent = self._parent_of(parent)

    def clear_all_checks(self):
        debug("[GUI] Entferne alle Haken im TreeView.")
        if not hasattr(self, "tree") or self.tree is None or self.tree.topLevelItemCount() == 0:
            debug("[GUI] Kein TreeView vorhanden oder leer – Aktion ignoriert.")
            return
        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            self._uncheck_recursive(item)
        self.update_build_button_state()

    def _uncheck_recursive(self, item: QTreeWidgetItem):
        item.setCheckState(0, Qt.Unchecked)
        for i in range(item.childCount()):
            self._uncheck_recursive(item.child(i))

    def on_tree_item_changed(self, item: QTreeWidgetItem, column: int):
        try:
            path_marker = item.data(0, Qt.UserRole)
            state = item.checkState(0)
            if isinstance(path_marker, list):
                path_marker = tuple(path_marker)
            debug(f"[GUI] Item geändert: {' / '.join(path_marker)}, State={state}")
            if path_marker:
                self.check_states[path_marker] = state
                if state == Qt.Checked:
                    # Checked: sicherstellen, dass nicht als disabled geführt
                    self.disabled_nodes_paths.discard(path_marker)
                elif state == Qt.Unchecked:
                    # Unchecked: als disabled führen
                    self.disabled_nodes_paths.add(path_marker)
                else:
                    # PartiallyChecked: NICHT als disabled führen
                    self.disabled_nodes_paths.discard(path_marker)

            if state == Qt.Checked:
                self._propagate_up_on_child_checked(item)
            elif state == Qt.Unchecked:
                if item.childCount() > 0 and _any_child_checked_or_partial(item):
                    item.setCheckState(0, Qt.PartiallyChecked)
                    if path_marker:
                        self.check_states[path_marker] = Qt.PartiallyChecked
                        # PartiallyChecked nicht disabled
                        self.disabled_nodes_paths.discard(path_marker)
                    self._propagate_up_on_child_checked(item)
                else:
                    self._propagate_up_on_child_unchecked(item)
            else:  # Qt.PartiallyChecked
                self._propagate_up_on_child_checked(item)

            self.update_build_button_state()
        except Exception as e:
            debug(f"[GUI] Fehler bei Tree-Änderung: {e}")
            self.statusBar().showMessage("Fehler beim Aktualisieren der Aktenstrukturen.")
