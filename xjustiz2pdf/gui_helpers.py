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

from PySide6.QtWidgets import QTreeWidgetItem
from PySide6.QtCore import Qt

def _is_checked_or_partial(item: QTreeWidgetItem) -> bool:
    state = item.checkState(0)
    return state == Qt.Checked or state == Qt.PartiallyChecked

def _any_child_checked_or_partial(item: QTreeWidgetItem) -> bool:
    for i in range(item.childCount()):
        ch = item.child(i)
        if _is_checked_or_partial(ch):
            return True
    return False
