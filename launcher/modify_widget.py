import sys
import os
import re
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QListWidget, QPushButton, QMessageBox, QLineEdit, QFileDialog,
                             QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView, QGraphicsDropShadowEffect, QListWidgetItem, QFrame, QTabWidget, QInputDialog, QStyledItemDelegate, QListView, QStyle, QDialog, QDialogButtonBox)
from PyQt5.QtGui import QIcon, QPixmap, QColor, QPainter, QFont, QFontMetrics, QPen, QPainterPath, QRegion
from PyQt5.QtCore import Qt, QPropertyAnimation, QRect, QTimer, pyqtSignal, QEvent, QRectF, QSize



class RemoveItemDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        painter.save()
        
        # Draw background for selected/hovered items
        if option.state & QStyle.State_Selected:
            painter.setBrush(QColor("#4a4e69")) # Selected background
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(option.rect, 5, 5)
        elif option.state & QStyle.State_MouseOver:
            painter.setBrush(QColor("#5b6078")) # Hover background
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(option.rect, 5, 5)
        else:
            painter.setBrush(QColor("transparent")) # Default background
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(option.rect, 5, 5)

        # Draw text
        text = index.data(Qt.DisplayRole)
        painter.setPen(QColor("white"))
        painter.setFont(option.font)
        painter.drawText(option.rect.adjusted(5, 0, -5, 0), Qt.AlignVCenter, text)

        # Draw 'X' button if hovered
        if option.state & QStyle.State_MouseOver:
            x_rect = QRect(option.rect.right() - 25, option.rect.center().y() - 10, 20, 20)
            painter.setBrush(QColor("red"))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(x_rect)

            x_font = QFont()
            x_font.setBold(True)
            x_font.setPointSize(10)
            painter.setFont(x_font)
            painter.setPen(Qt.white)
            painter.drawText(x_rect, Qt.AlignCenter, "X")

        painter.restore()

    def sizeHint(self, option, index):
        size = super().sizeHint(option, index)
        size.setHeight(30) # Adjust height as needed
        return size

class RemoveItemsListWidget(QListWidget):
    itemRemoved = pyqtSignal(str) # Emits the text of the removed item

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setObjectName("removeListWidget")
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setMouseTracking(True) # Enable mouse tracking for hover effects
        self.hovered_item = None

    def mouseMoveEvent(self, event):
        item = self.itemAt(event.pos())
        if item != self.hovered_item:
            if self.hovered_item:
                # Update previous hovered item to remove hover style
                self.model().dataChanged.emit(self.indexFromItem(self.hovered_item), self.indexFromItem(self.hovered_item))
            self.hovered_item = item
            if self.hovered_item:
                # Update current hovered item to apply hover style
                self.model().dataChanged.emit(self.indexFromItem(self.hovered_item), self.indexFromItem(self.hovered_item))
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        if self.hovered_item:
            self.model().dataChanged.emit(self.indexFromItem(self.hovered_item), self.indexFromItem(self.hovered_item))
            self.hovered_item = None
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        index = self.indexAt(event.pos())
        if index.isValid():
            item = self.itemFromIndex(index)
            if item:
                # Check if the click was on the 'X' button area
                item_rect = self.visualRect(index)
                x_button_rect = QRect(item_rect.right() - 25, item_rect.center().y() - 10, 20, 20)
                if x_button_rect.contains(event.pos()):
                    print(f"Emitting itemRemoved for: {item.text()}")
                    self.takeItem(self.row(item))
                    self.itemRemoved.emit(item.text())
                # If the click is on the item but not on the 'X' button, do nothing
                # else: # Removed this else block
                #    super().mousePressEvent(event) # Removed this line
        else:
            super().mousePressEvent(event)

    def addItems(self, texts):
        for text in texts:
            self.addItem(text)

    def addItem(self, text):
        item = QListWidgetItem(text)
        super().addItem(item)

class CustomMessageBox(QMessageBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.setObjectName("customMessageBox")

        self.setStyleSheet(
            "#customMessageBox {"
            "    background-color: transparent;"
            "}"
            "QLabel#qt_msgbox_label {"
            "    color: #ffffff;"
            "    font-size: 16px;"
            "    font-weight: bold;"
            "    padding: 10px;"
            "}"
            "QLabel#qt_msgbox_informativetext {"
            "    color: #ffffff;"
            "    font-size: 14px;"
            "    padding: 10px;"
            "}"
            "QPushButton {"
            "    background-color: #494d64;"
            "    color: #ffffff;"
            "    border-radius: 10px;"
            "    padding: 8px 16px;"
            "    font-weight: bold;"
            "    min-width: 60px;"
            "}"
            "QPushButton:hover {"
            "    background-color: #5b6078;"
            "}"
        )

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(25)
        shadow.setColor(QColor(0, 0, 0, 180))
        shadow.setOffset(5, 5)
        self.setGraphicsEffect(shadow)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        painter.setBrush(QColor(40, 42, 62, 230))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(self.rect(), 15, 15)
        
        super().paintEvent(event)

    def showEvent(self, event):
        parent = self.parentWidget()
        if parent:
            parent_center = parent.mapToGlobal(parent.rect().center())
            self.move(parent_center - self.rect().center())
        else:
            screen = QApplication.primaryScreen()
            if screen:
                screen_geometry = screen.availableGeometry()
                self.move(screen_geometry.center() - self.rect().center())

        self.activateWindow()
        self.raise_()
        event.accept()

class RoundedInputDialog(QDialog):
    def __init__(self, parent=None, title="", label="", default_text=""):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setObjectName("roundedInputDialog")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        label_widget = QLabel(label)
        label_widget.setStyleSheet("color: #ffffff; font-size: 14px; padding: 10px;")
        layout.addWidget(label_widget)

        self.input_field = QLineEdit(default_text)
        self.input_field.setStyleSheet("""
            QLineEdit {
                background-color: #494d64;
                color: white;
                border: none;
                border-radius: 10px;
                padding: 8px;
                font-size: 14px;
            }
        """)
        layout.addWidget(self.input_field)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.button(QDialogButtonBox.Ok).setObjectName("installButton")
        button_box.button(QDialogButtonBox.Cancel).setObjectName("uninstallButton")
        
        layout.addWidget(button_box)

        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(25)
        shadow.setColor(QColor(0, 0, 0, 180))
        shadow.setOffset(5, 5)
        self.setGraphicsEffect(shadow)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), 15, 15)
        self.setMask(QRegion(path.toFillPolygon().toPolygon()))

        painter.setBrush(QColor(40, 42, 62, 230))
        painter.setPen(QPen(QColor(73, 77, 100), 3))
        painter.drawRoundedRect(self.rect(), 15, 15)

    def getText(self):
        if self.exec_() == QDialog.Accepted:
            return self.input_field.text(), True
        else:
            return "", False

    def showEvent(self, event):
        parent = self.parentWidget()
        if parent:
            parent_center = parent.mapToGlobal(parent.rect().center())
            self.move(parent_center - self.rect().center())
        else:
            screen = QApplication.primaryScreen()
            if screen:
                screen_geometry = screen.availableGeometry()
                self.move(screen_geometry.center() - self.rect().center())

        self.activateWindow()
        self.raise_()
        event.accept()

def read_file(filepath):
    with open(filepath, 'r') as file:
        return file.read()

def write_file(filepath, content):
    with open(filepath, 'w') as file:
        file.write(content)

def append_to_file(filepath, line):
    with open(filepath, 'a') as file:
        file.write("\n" + line)

def delete_from_file(filepath, elements):
    try:
        old_name = elements[0].strip() if len(elements) > 0 else ""
        new_name = elements[1].strip() if len(elements) > 1 else ""
        icon = elements[2].strip() if len(elements) > 2 else None

        with open(filepath, 'r') as file:
            lines = file.readlines()

        with open(filepath, 'w') as file:
            for line in lines:
                if old_name in line and new_name in line and (not icon or icon in line):
                   continue
                file.write(line)
    except Exception as e:
        raise RuntimeError(f"Failed to delete modification from file: {str(e)}")

def modify_from_file(filepath, original_line, new_elements):
    print(f"modify_from_file: filepath={filepath}, original_line={original_line}, new_elements={new_elements}")
    try:
        new_old_name = new_elements[0].strip() if len(new_elements) > 0 else ""
        new_new_name = new_elements[1].strip() if len(new_elements) > 1 else ""
        new_icon = new_elements[2].strip() if len(new_elements) > 2 else ""

        with open(filepath, 'r') as file:
            lines = file.readlines()

        with open(filepath, 'w') as file:
            for line in lines:
                if line == original_line: # Match the exact original line
                    new_line = f"modify(find='{new_old_name}' title='{new_new_name}'"
                    if new_icon:
                        new_line += f" icon='{new_icon}'"
                    new_line += ")\n"
                    file.write(new_line)
                else:
                    file.write(line)
    except Exception as e:
       raise RuntimeError(f"Failed to modify the file: {str(e)}")

def _clear_layout(layout):
    if layout is not None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
            else:
                sub_layout = item.layout()
                if sub_layout is not None:
                    _clear_layout(sub_layout)

def extract_lines(content, start_marker, end_marker):
    sections = []
    start = content.find(start_marker)
    while start != -1:
        end = content.find(end_marker, start)
        if end == -1:
            break
        section = content[start:end].strip().split('\n')
        sections.extend([line.strip().rstrip(',') for line in section if line.strip().startswith("id")] )
        start = content.find(start_marker, end)
    return sections


def extract_modify_lines(content):
    lines = []
    for line in content.split('\n'):
        stripped_line = line.strip()
        if stripped_line.startswith("modify(find="):
            parts = stripped_line.split("'")
            if len(parts) > 3:
                old_name = parts[1]
                new_name = parts[3]
                icon = parts[5] if len(parts) > 5 else ""
                lines.append((old_name, new_name, icon, line)) # Store the unstripped line
    return lines

def extract_import_lines(content):
    lines = []
    for line in content.split('\n'):
        stripped_line = line.strip()
        match = re.search(r"^import\s+'(.*\.nss)'$", stripped_line)
        if match:
            full_path = match.group(1)
            file_name = os.path.basename(full_path)
            lines.append((file_name, full_path)) # Store (filename, relative_path)
    return lines

def extract_remove_line(content):

    for line in content.split('\n'):
        if line.strip().startswith("remove(find="):
            return line.strip()
    return None

def update_section(content, start_marker, end_marker, ids):
    start = content.find(start_marker)
    while start != -1:
        end = content.find(end_marker, start)
        if end == -1:
            break
        before_section = content[:start]
        section = content[start:end]
        after_section = content[end:]

        section_lines = section.strip().split('\n')
    
        if len(ids) < 1:
            msgBox = CustomMessageBox()
            msgBox.setIcon(QMessageBox.Critical)
            msgBox.setText("Error")
            msgBox.setInformativeText("Each section must contain at least one ID.")
            msgBox.setStandardButtons(QMessageBox.Ok)
            msgBox.exec_()
            return content

        new_ids = [new_id.strip() for new_id in ids if new_id.strip() != '']

        if len(new_ids) == 1:
            new_ids[0] = new_ids[0].rstrip(',')
        elif len(new_ids) > 1:
            for i in range(len(new_ids) - 1):
                new_ids[i] = new_ids[i].rstrip(',') + ","
            new_ids[-1] = new_ids[-1].rstrip(',')

        updated_lines = [line for line in section_lines if not line.strip().startswith("id")]
        updated_lines.extend(new_ids)

        updated_section = "\n".join(updated_lines)

        content = before_section + updated_section + after_section

        start = content.find(start_marker, start + len(updated_section))

    return content

class DragDropListWidget(QListWidget):
    def __init__(self, parent=None):
        super(DragDropListWidget, self).__init__(parent)
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setObjectName("modifyList")

    def dragEnterEvent(self, event):
        if event.source() != self:
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.source() != self:
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        if event.source() != self:
            item = event.source().currentItem()
            source_list = event.source()
            dest_list = self

            source_list.takeItem(source_list.row(item))

            new_item = QListWidgetItem(item.text())
            new_item.setData(Qt.UserRole, item.data(Qt.UserRole))
            dest_list.addItem(new_item)


class EditableTableWidget(QTableWidget):
    itemChangedSignal = pyqtSignal(int, int, str)
    iconChangedSignal = pyqtSignal(int, str)

    def __init__(self, parent=None):
        super(EditableTableWidget, self).__init__(parent)
        self.setColumnCount(4)
        self.setHorizontalHeaderLabels(["Old Name", "New Name", "Icon", ""])
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setEditTriggers(QAbstractItemView.DoubleClicked | QAbstractItemView.AnyKeyPressed | QAbstractItemView.SelectedClicked)
        self.verticalHeader().setVisible(False)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.viewport().setStyleSheet("background-color: transparent;")
        self.setShowGrid(False)
        self.horizontalHeader().setStyleSheet("QHeaderView::section {background-color: transparent; color: #FFFFFF; border: none; padding: 4px;}")
        self.setStyleSheet("QTableWidget::item {border: none; padding: 3px;} QTableWidget::item:selected { background-color: #4a4e69; }")
        self.setMouseTracking(True)
        self.hovered_row = -1

    def set_items(self, items):
        self.setRowCount(0)
        for item_data in items:
            if not item_data:
                continue
            old_name, new_name, icon, original_line = item_data # Unpack the tuple
            row_position = self.rowCount()
            self.insertRow(row_position)
            self.setItem(row_position, 0, QTableWidgetItem(old_name))
            self.setItem(row_position, 1, QTableWidgetItem(new_name))
            self.setItem(row_position, 2, QTableWidgetItem(icon))
            self.setItem(row_position, 3, QTableWidgetItem(""))

            self.set_icon_item(row_position, icon) # Call set_icon_item always

            # Store original data and the full original line for editing
            self.item(row_position, 0).setData(Qt.UserRole, old_name)
            self.item(row_position, 1).setData(Qt.UserRole, new_name)
            self.item(row_position, 2).setData(Qt.UserRole, icon)
            self.item(row_position, 3).setData(Qt.UserRole, original_line) # Store original line here

    def set_icon_item(self, row, icon_path):
            icon_item = self.item(row, 2)
            if not icon_item:
                icon_item = QTableWidgetItem()
                self.setItem(row, 2, icon_item)
            if icon_path:
                try:
                    pixmap = QPixmap(icon_path).scaled(24, 24, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    icon_item.setIcon(QIcon(pixmap))
                    icon_item.setText("") # Clear text if icon is set
                except:
                    icon_item.setText("Invalid")
            else:
                icon_item.setIcon(QIcon())
                icon_item.setText("Click to add icon")
            icon_item.setData(Qt.UserRole, icon_path)

    def itemChanged(self, item):
        row = item.row()
        column = item.column()
        text = item.text()
        self.itemChangedSignal.emit(row, column, text)

    def mouseDoubleClickEvent(self, event):
        index = self.indexAt(event.pos())
        if index.isValid() and index.column() == 2:
            row = index.row()
            current_icon_path = self.item(row, 2).data(Qt.UserRole)
            if current_icon_path:
                msg_box = CustomMessageBox(self)
                msg_box.setText("Icon Options")
                msg_box.setInformativeText("Do you want to change or remove the icon?")
                change_button = msg_box.addButton("Change Icon", QMessageBox.ActionRole)
                remove_button = msg_box.addButton("Remove Icon", QMessageBox.DestructiveRole)
                msg_box.addButton(QMessageBox.Cancel)
                msg_box.exec_()

                if msg_box.clickedButton() == change_button:
                    self.change_icon(row)
                elif msg_box.clickedButton() == remove_button:
                    self.remove_icon(row)
            else:
                self.change_icon(row)
        else:
            super().mouseDoubleClickEvent(event)

    def remove_icon(self, row):
        self.set_icon_item(row, "")
        self.iconChangedSignal.emit(row, "")

    def change_icon(self, row):
        icon_path, _ = QFileDialog.getOpenFileName(self, "Select Icon", "", "Images (*.png *.xpm *.jpg *.ico)")
        if icon_path:
            self.set_icon_item(row, icon_path)
            self.iconChangedSignal.emit(row, icon_path)

    def mouseMoveEvent(self, event):
        index = self.indexAt(event.pos())
        if index.isValid():
            new_hovered_row = index.row()
            if self.hovered_row != new_hovered_row:
                self.hovered_row = new_hovered_row
                self.viewport().update()
        else:
            if self.hovered_row != -1:
                self.hovered_row = -1
                self.viewport().update()
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        if self.hovered_row != -1:
            self.hovered_row = -1
            self.viewport().update()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        index = self.indexAt(event.pos())
        if index.isValid() and index.column() == 3:
            self.cellClicked.emit(index.row(), index.column())
        else:
            super().mousePressEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self.viewport())
        painter.setRenderHint(QPainter.Antialiasing)

        for row in range(self.rowCount()):
            rect = self.visualRect(self.model().index(row, 0))
            if not rect.isValid():
                continue

            if self.hovered_row == row:
                full_row_rect = QRect(0, rect.top(), self.viewport().width(), rect.height())
                painter.setBrush(QColor("#5b6078"))
                painter.setPen(Qt.NoPen)
                painter.drawRoundedRect(full_row_rect, 5, 5)

        super().paintEvent(event)

        painter.setRenderHint(QPainter.Antialiasing)
        for row in range(self.rowCount()):
            rect = self.visualRect(self.model().index(row, 0))
            if not rect.isValid():
                continue

            if self.hovered_row == row:
                x_col_rect = self.visualRect(self.model().index(row, 3))
                if x_col_rect.isValid():
                    x_rect = QRect(x_col_rect.center().x() - 10, x_col_rect.center().y() - 10, 20, 20)
                    painter.setBrush(QColor("red"))
                    painter.setPen(Qt.NoPen)
                    painter.drawEllipse(x_rect)

                    x_font = QFont()
                    x_font.setBold(True)
                    x_font.setPointSize(12)
                    painter.setFont(x_font)
                    painter.setPen(Qt.white)
                    painter.drawText(x_rect, Qt.AlignCenter, "X")

class ModifyWidget(QWidget):
    def __init__(self, nss_path, project_root, parent=None):
        super(ModifyWidget, self).__init__(parent)

        self.filepath = nss_path
        self.project_root = project_root
        self.shell_nss_path = os.path.join(self.project_root, 'shell.nss')

        

        self.main_layout = QVBoxLayout(self) # Initialize main_layout here

        if not os.path.exists(self.filepath):
            self.setup_placeholder_ui()
        else:
            content = read_file(self.filepath)
            shell_content = read_file(self.shell_nss_path)

            hide_lines = extract_lines(content, "// hide\nmodify(mode=mode.multiple\nwhere=this.id(", ") vis=vis.remove)")
            more_lines = extract_lines(content, "// more\nmodify(mode=mode.multiple\nwhere=this.id(", ") menu=title.options)")
            shift_lines = extract_lines(content, "// shift\nmodify(mode=single\nwhere=this.id(", ") vis=key.shift())")
            modify_lines = extract_modify_lines(content)
            remove_line = extract_remove_line(content)
            self.removed_items = []
            if remove_line:
                items_str = remove_line[remove_line.find('"') + 1:remove_line.rfind('"')]
                if items_str:
                    self.removed_items = items_str.split('|')
            
            self.imported_items = extract_import_lines(shell_content)

            self.init_ui(hide_lines, more_lines, shift_lines, modify_lines)

    def setup_placeholder_ui(self):
        _clear_layout(self.main_layout)
        error_label = QLabel(f"File not found:\n{self.filepath}\n\nPlease ensure the file exists to use this feature.")
        error_label.setAlignment(Qt.AlignCenter)
        error_label.setStyleSheet("font-size: 14px; color: #FFFFFF;")
        error_label.setWordWrap(True)
        self.main_layout.addWidget(error_label)

    def init_ui(self, hide_lines, more_lines, shift_lines, modify_lines):
        # Clear existing layout and its widgets if they exist
        # Clear existing widgets from the main_layout
        _clear_layout(self.main_layout)
        self.tab_widget = QTabWidget()
        self.main_layout.addWidget(self.tab_widget)

        ids_tab = QWidget()
        self.tab_widget.addTab(ids_tab, "IDS")
        ids_tab_layout = QVBoxLayout(ids_tab)
        ids_content_layout = QHBoxLayout()
        ids_tab_layout.addLayout(ids_content_layout)

        left_layout = QVBoxLayout()
        ids_content_layout.addLayout(left_layout)

        # Search input will be moved to the right column

        self.hide_label = QLabel("HIDE")
        self.hide_label.setStyleSheet("font-size: 18px; color: #FFFFFF; margin-bottom: 5px; background-color: transparent;")
        shadow = QGraphicsDropShadowEffect(blurRadius=15, xOffset=2, yOffset=2); shadow.setColor(QColor(0, 0, 0, 160))
        self.hide_label.setGraphicsEffect(shadow)
        left_layout.addWidget(self.hide_label)

        self.hide_list = DragDropListWidget()
        for line in hide_lines:
            item = QListWidgetItem(self.format_id_for_ui(line)); item.setData(Qt.UserRole, line)
            self.hide_list.addItem(item)
        self.hide_list.original_items = hide_lines
        hide_frame = QFrame(); hide_frame.setObjectName("modifyFrame")
        hide_frame_layout = QVBoxLayout(hide_frame); hide_frame_layout.setContentsMargins(10,10,10,10)
        hide_frame_layout.addWidget(self.hide_list)
        shadow = QGraphicsDropShadowEffect(blurRadius=15, xOffset=5, yOffset=5); shadow.setColor(QColor(0, 0, 0, 160))
        hide_frame.setGraphicsEffect(shadow)
        left_layout.addWidget(hide_frame)

        self.more_label = QLabel("MORE OPTIONS")
        self.more_label.setStyleSheet("font-size: 18px; color: #FFFFFF; margin-top: 5px; background-color: transparent;")
        shadow = QGraphicsDropShadowEffect(blurRadius=15, xOffset=2, yOffset=2); shadow.setColor(QColor(0, 0, 0, 160))
        self.more_label.setGraphicsEffect(shadow)
        left_layout.addWidget(self.more_label)

        self.more_list = DragDropListWidget()
        for line in more_lines:
            item = QListWidgetItem(self.format_id_for_ui(line)); item.setData(Qt.UserRole, line)
            self.more_list.addItem(item)
        self.more_list.original_items = more_lines
        more_frame = QFrame(); more_frame.setObjectName("modifyFrame")
        more_frame_layout = QVBoxLayout(more_frame); more_frame_layout.setContentsMargins(10,10,10,10)
        more_frame_layout.addWidget(self.more_list)
        shadow = QGraphicsDropShadowEffect(blurRadius=15, xOffset=5, yOffset=5); shadow.setColor(QColor(0, 0, 0, 160))
        more_frame.setGraphicsEffect(shadow)
        left_layout.addWidget(more_frame)

        self.shift_label = QLabel("SHIFT+RIGH-CLICK")
        self.shift_label.setStyleSheet("font-size: 18px; color: #FFFFFF; margin-top: 5px; background-color: transparent;")
        shadow = QGraphicsDropShadowEffect(blurRadius=15, xOffset=2, yOffset=2); shadow.setColor(QColor(0, 0, 0, 160))
        self.shift_label.setGraphicsEffect(shadow)
        left_layout.addWidget(self.shift_label)

        self.shift_list = DragDropListWidget()
        for line in shift_lines:
            item = QListWidgetItem(self.format_id_for_ui(line)); item.setData(Qt.UserRole, line)
            self.shift_list.addItem(item)
        self.shift_list.original_items = shift_lines
        shift_frame = QFrame(); shift_frame.setObjectName("modifyFrame")
        shift_frame_layout = QVBoxLayout(shift_frame); shift_frame_layout.setContentsMargins(10,10,10,10)
        shift_frame_layout.addWidget(self.shift_list)
        shadow = QGraphicsDropShadowEffect(blurRadius=15, xOffset=5, yOffset=5); shadow.setColor(QColor(0, 0, 0, 160))
        shift_frame.setGraphicsEffect(shadow)
        left_layout.addWidget(shift_frame)

        right_layout = QVBoxLayout()
        ids_content_layout.addLayout(right_layout)

        ids_header_layout = QHBoxLayout()
        self.ids_label = QLabel("IDS")
        self.ids_label.setStyleSheet("font-size: 18px; color: #FFFFFF; margin: 5px; background-color: transparent;")
        shadow = QGraphicsDropShadowEffect(blurRadius=15, xOffset=2, yOffset=2); shadow.setColor(QColor(0, 0, 0, 160))
        self.ids_label.setGraphicsEffect(shadow)
        ids_header_layout.addWidget(self.ids_label)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search...")
        self.search_input.setFixedWidth(150)
        self.search_input.setStyleSheet("background-color: rgba(255, 255, 255, 0.1); border-radius: 8px; padding: 5px; color: #FFFFFF;")
        shadow = QGraphicsDropShadowEffect(blurRadius=15, xOffset=2, yOffset=2); shadow.setColor(QColor(0, 0, 0, 160))
        self.search_input.setGraphicsEffect(shadow)
        self.search_input.textChanged.connect(self.filter_lists)
        ids_header_layout.addWidget(self.search_input)
        ids_header_layout.addStretch()
        right_layout.addLayout(ids_header_layout)

        self.ids_list = DragDropListWidget()
        placeholder_ids = ["id.add_a_network_location", "id.align_icons_to_grid", "id.arrange_by",
                           "id.auto_arrange_icons", "id.autoplay", "id.cancel", "id.cascade_windows", "id.cast_to_device",
                           "id.cleanup", "id.collapse", "id.collapse_all_groups", "id.collapse_group", "id.command_prompt",
                           "id.compressed", "id.configure", "id.content", "id.control_panel", "id.copy", "id.copy_as_path",
                           "id.copy_here", "id.copy_path", "id.copy_to", "id.copy_to_folder", "id.cortana", "id.create_shortcut",
                           "id.create_shortcuts_here", "id.customize_notification_icons", "id.customize_this_folder",
                           "id.cut", "id.delete", "id.desktop", "id.details", "id.device_manager", "id.disconnect",
                           "id.disconnect_network_drive", "id.display_settings", "id.edit", "id.eject", "id.empty_recycle_bin",
                           "id.erase_this_disc", "id.exit_explorer", "id.expand", "id.expand_all_groups", "id.expand_group",
                           "id.extra_large_icons", "id.extract_all", "id.extract_to",
                           "id.file_explorer", "id.folder_options", "id.format", "id.give_access_to", "id.group_by",
                           "id.include_in_library", "id.insert_unicode_control_character", "id.install", "id.large_icons",
                           "id.list", "id.lock_all_taskbars", "id.lock_the_taskbar", "id.make_available_offline",
                           "id.make_available_online", "id.manage", "id.map_as_drive", "id.map_network_drive", "id.medium_icons",
                           "id.merge", "id.more_options", "id.mount", "id.move_here", "id.move_to", "id.move_to_folder",
                           "id.new", "id.new_folder", "id.new_item", "id.news_and_interests", "id.next_desktop_background",
                           "id.open", "id.open_as_portable", "id.open_autoplay", "id.open_command_prompt",
                           "id.open_command_window_here", "id.open_file_location", "id.open_folder_location",
                           "id.open_in_new_process", "id.open_in_new_tab", "id.open_in_new_window", "id.open_new_tab",
                           "id.open_new_window", "id.open_powershell_window_here", "id.open_windows_powershell",
                           "id.open_with", "id.options", "id.paste", "id.paste_shortcut", "id.personalize",
                           "id.pin_current_folder_to_quick_access", "id.pin_to_quick_access", "id.pin_to_start",
                           "id.pin_to_taskbar", "id.play", "id.power_options",
                           "id.preview", "id.print", "id.properties", "id.reconversion", "id.redo", "id.refresh",
                           "id.remove_from_quick_access", "id.remove_properties", "id.rename", "id.restore",
                           "id.restore_default_libraries", "id.restore_previous_versions", "id.rotate_left", "id.rotate_right",
                           "id.run", "id.run_as_administrator", "id.run_as_another_user", "id.search", "id.select_all",
                           "id.send_to", "id.set_as_desktop_background", "id.set_as_desktop_wallpaper", "id.settings",
                           "id.share", "id.share_with", "id.shield", "id.show_cortana_button",
                           "id.show_desktop_icons", "id.show_file_extensions", "id.show_hidden_files", "id.show_libraries",
                           "id.show_network", "id.show_pen_button", "id.show_people_on_the_taskbar", "id.show_task_view_button",
                           "id.show_the_desktop", "id.show_this_pc", "id.show_touch_keyboard_button", "id.show_touchpad_button",
                           "id.show_windows_stacked", "id.small_icons", "id.sort_by", "id.store",
                           "id.task_manager", "id.taskbar_settings", "id.tiles", "id.troubleshoot_compatibility",
                           "id.turn_off_bitlocker", "id.turn_on_bitlocker", "id.undo", "id.unpin_from_quick_access",
                           "id.unpin_from_start", "id.unpin_from_taskbar", "id.view"]
        filtered_ids = self.filter_ids(placeholder_ids, hide_lines, more_lines, shift_lines)
        for line in filtered_ids:
            item = QListWidgetItem(self.format_id_for_ui(line)); item.setData(Qt.UserRole, line)
            self.ids_list.addItem(item)
        self.ids_list.original_items = filtered_ids
        ids_frame = QFrame(); ids_frame.setObjectName("modifyFrame")
        ids_frame_layout = QVBoxLayout(ids_frame); ids_frame_layout.setContentsMargins(10,10,10,10)
        ids_frame_layout.addWidget(self.ids_list)
        shadow = QGraphicsDropShadowEffect(blurRadius=15, xOffset=5, yOffset=5); shadow.setColor(QColor(0, 0, 0, 160))
        ids_frame.setGraphicsEffect(shadow)
        right_layout.addWidget(ids_frame)

        save_controls_layout = QHBoxLayout()
        save_controls_layout.setContentsMargins(0, 10, 0, 0)

        self.save_label = QLabel("")
        self.save_label.setStyleSheet("font-size: 14px; color: #4caf50; background-color: transparent;")
        save_controls_layout.addWidget(self.save_label, alignment=Qt.AlignLeft)

        self.save_button = QPushButton("Save")
        self.save_button.setObjectName("saveButton")
        font = self.save_button.font()
        font.setBold(True)
        self.save_button.setFont(font)
        self.save_button.clicked.connect(self.save_changes)
        shadow = QGraphicsDropShadowEffect(blurRadius=15, xOffset=2, yOffset=2)
        shadow.setColor(QColor(0, 0, 0, 160))
        self.save_button.setGraphicsEffect(shadow)
        save_controls_layout.addWidget(self.save_button, alignment=Qt.AlignRight)

        ids_tab_layout.addLayout(save_controls_layout)

        modify_tab = QWidget()
        self.tab_widget.addTab(modify_tab, "Modify")
        modify_layout = QVBoxLayout(modify_tab)

        modify_group_layout = QHBoxLayout()
        modify_fields_layout = QVBoxLayout()

        old_name_layout = QHBoxLayout()
        self.old_name_label = QLabel("Old name:")
        self.old_name_label.setStyleSheet("font-size: 16px; color: #FFFFFF; margin-right: 5px; background-color: transparent;")
        old_name_layout.addWidget(self.old_name_label)
        self.old_name_input = QLineEdit()
        self.old_name_input.setFixedWidth(250)
        self.old_name_input.setStyleSheet("background-color: rgba(255, 255, 255, 0.1); border-radius: 8px; padding: 5px; color: #FFFFFF;")
        shadow = QGraphicsDropShadowEffect(blurRadius=15, xOffset=2, yOffset=2); shadow.setColor(QColor(0, 0, 0, 160))
        self.old_name_input.setGraphicsEffect(shadow)
        old_name_layout.addStretch()
        old_name_layout.addWidget(self.old_name_input)
        modify_fields_layout.addLayout(old_name_layout)

        new_name_layout = QHBoxLayout()
        self.new_name_label = QLabel("New name:")
        self.new_name_label.setStyleSheet("font-size: 16px; color: #FFFFFF; margin-right: 5px; background-color: transparent;")
        new_name_layout.addWidget(self.new_name_label)
        self.new_name_input = QLineEdit()
        self.new_name_input.setFixedWidth(250)
        self.new_name_input.setStyleSheet("background-color: rgba(255, 255, 255, 0.1); border-radius: 8px; padding: 5px; color: #FFFFFF;")
        shadow = QGraphicsDropShadowEffect(blurRadius=15, xOffset=2, yOffset=2); shadow.setColor(QColor(0, 0, 0, 160))
        self.new_name_input.setGraphicsEffect(shadow)
        new_name_layout.addStretch()
        new_name_layout.addWidget(self.new_name_input)
        modify_fields_layout.addLayout(new_name_layout)

        icon_layout = QHBoxLayout()
        self.icon_label = QLabel("Icon:")
        self.icon_label.setStyleSheet("font-size: 16px; color: #FFFFFF; margin-right: 5px; background-color: transparent;")
        icon_layout.addWidget(self.icon_label)
        icon_layout.addStretch()
        icon_input_container = QWidget()
        icon_input_container_layout = QHBoxLayout(icon_input_container)
        icon_input_container_layout.setContentsMargins(0, 0, 0, 0); icon_input_container_layout.setSpacing(10)
        self.icon_input = QLineEdit()
        self.icon_input.setStyleSheet("background-color: rgba(255, 255, 255, 0.1); border-radius: 8px; padding: 5px; color: #FFFFFF;")
        shadow = QGraphicsDropShadowEffect(blurRadius=15, xOffset=2, yOffset=2); shadow.setColor(QColor(0, 0, 0, 160))
        self.icon_input.setGraphicsEffect(shadow)
        icon_input_container_layout.addWidget(self.icon_input)
        self.icon_button = QPushButton("Select Icon"); self.icon_button.setObjectName("selectIconButton")
        font = self.icon_button.font(); font.setBold(True); self.icon_button.setFont(font)
        self.icon_button.clicked.connect(self.select_icon)
        shadow = QGraphicsDropShadowEffect(blurRadius=15, xOffset=2, yOffset=2); shadow.setColor(QColor(0, 0, 0, 160))
        self.icon_button.setGraphicsEffect(shadow)
        icon_input_container_layout.addWidget(self.icon_button)
        icon_input_container.setFixedWidth(250)
        icon_layout.addWidget(icon_input_container)
        modify_fields_layout.addLayout(icon_layout)
        
        modify_group_layout.addLayout(modify_fields_layout)

        modification_section_layout = QVBoxLayout()
        self.modification_list = EditableTableWidget()
        self.modification_list.setObjectName("modificationList")
        self.modification_list.set_items(modify_lines)
        self.modification_list.itemChangedSignal.connect(self.edit_modification)
        self.modification_list.iconChangedSignal.connect(self.edit_icon_modification)
        self.modification_list.cellClicked.connect(self.delete_modification_item)
        modification_frame = QFrame(); modification_frame.setObjectName("modifyFrame")
        modification_frame_layout = QVBoxLayout(modification_frame); modification_frame_layout.setContentsMargins(10,10,10,10)
        modification_frame_layout.addWidget(self.modification_list)
        shadow = QGraphicsDropShadowEffect(blurRadius=15, xOffset=5, yOffset=5); shadow.setColor(QColor(0, 0, 0, 160))
        modification_frame.setGraphicsEffect(shadow)
        modification_section_layout.addWidget(modification_frame)

        modify_group_layout.addLayout(modification_section_layout)
        
        modify_layout.addLayout(modify_group_layout)

        self.modify_button = QPushButton("Modify"); self.modify_button.setObjectName("modifyButton")
        font = self.modify_button.font(); font.setBold(True); self.modify_button.setFont(font)
        self.modify_button.clicked.connect(self.modify_name)
        shadow = QGraphicsDropShadowEffect(blurRadius=15, xOffset=2, yOffset=2); shadow.setColor(QColor(0, 0, 0, 160))
        self.modify_button.setGraphicsEffect(shadow)
        modify_fields_layout.addWidget(self.modify_button)

        modify_layout.addLayout(modify_group_layout)

        bottom_section_layout = QHBoxLayout()
        modify_layout.addLayout(bottom_section_layout)

        remove_layout = QVBoxLayout()
        bottom_section_layout.addLayout(remove_layout)

        self.remove_label = QLabel("Remove Items")
        self.remove_label.setStyleSheet("font-size: 18px; color: #FFFFFF; margin-top: 5px; background-color: transparent;")
        shadow = QGraphicsDropShadowEffect(blurRadius=15, xOffset=2, yOffset=2); shadow.setColor(QColor(0, 0, 0, 160))
        self.remove_label.setGraphicsEffect(shadow)
        remove_layout.addWidget(self.remove_label)

        self.remove_list = RemoveItemsListWidget()
        self.remove_list.setItemDelegate(RemoveItemDelegate())
        self.remove_list.addItems(self.removed_items)
        self.remove_list.itemRemoved.connect(self.delete_remove_item)
        self.remove_list.setSelectionRectVisible(False)
        remove_frame = QFrame(); remove_frame.setObjectName("modifyFrame")
        remove_frame_layout = QVBoxLayout(remove_frame); remove_frame_layout.setContentsMargins(10,10,10,10)
        remove_frame_layout.addWidget(self.remove_list)
        shadow = QGraphicsDropShadowEffect(blurRadius=15, xOffset=5, yOffset=5); shadow.setColor(QColor(0, 0, 0, 160))
        remove_frame.setGraphicsEffect(shadow)
        remove_layout.addWidget(remove_frame)
        
        remove_buttons_layout = QHBoxLayout()
        self.add_remove_button = QPushButton("Enter Name"); self.add_remove_button.setObjectName("installButton")
        self.add_remove_button.clicked.connect(self.add_remove_item)
        self.add_remove_button.setFixedWidth(120) # Fixed width
        remove_buttons_layout.addWidget(self.add_remove_button)
        remove_layout.addLayout(remove_buttons_layout)

        import_layout = QVBoxLayout()
        bottom_section_layout.addLayout(import_layout)

        self.import_label = QLabel("Import .nss Files")
        self.import_label.setStyleSheet("font-size: 18px; color: #FFFFFF; margin-top: 5px; background-color: transparent;")
        shadow = QGraphicsDropShadowEffect(blurRadius=15, xOffset=2, yOffset=2); shadow.setColor(QColor(0, 0, 0, 160))
        self.import_label.setGraphicsEffect(shadow)
        import_layout.addWidget(self.import_label)

        self.import_list = RemoveItemsListWidget()
        self.import_list.setItemDelegate(RemoveItemDelegate())
        for filename, _ in self.imported_items: # Display only filename
            self.import_list.addItem(filename)
        self.import_list.itemRemoved.connect(self.delete_import_item)
        self.import_list.setSelectionRectVisible(False)
        import_frame = QFrame(); import_frame.setObjectName("modifyFrame")
        import_frame_layout = QVBoxLayout(import_frame); import_frame_layout.setContentsMargins(10,10,10,10)
        import_frame_layout.addWidget(self.import_list)
        shadow = QGraphicsDropShadowEffect(blurRadius=15, xOffset=5, yOffset=5); shadow.setColor(QColor(0, 0, 0, 160))
        import_frame.setGraphicsEffect(shadow)
        import_layout.addWidget(import_frame)

        import_buttons_layout = QHBoxLayout()
        self.browse_import_button = QPushButton("Browse")
        self.browse_import_button.setObjectName("installButton")
        self.browse_import_button.clicked.connect(self.add_import_item)
        self.browse_import_button.setFixedWidth(120) # Fixed width
        import_buttons_layout.addWidget(self.browse_import_button)
        import_layout.addLayout(import_buttons_layout)

        
        self.add_remove_button.setFixedWidth(120) # Fixed width
        self.browse_import_button.setFixedWidth(120) # Fixed width

        

    def filter_lists(self, text):
        text = text.lower()
        for list_widget in [self.hide_list, self.more_list, self.shift_list, self.ids_list]:
            for i in range(list_widget.count()):
                item = list_widget.item(i)
                item.setHidden(text not in item.text().lower())

    def filter_ids(self, ids, *lines_lists):
        used_ids = set()
        for lines in lines_lists:
            for line in lines:
                if line.startswith("id."):
                    used_ids.add(line.strip().rstrip(','))
        return [id_ for id_ in ids if id_ not in used_ids]

    def format_id_for_ui(self, id_string):
        if id_string.startswith("id."):
            id_string = id_string[3:]

        formatted_id = " ".join(word.capitalize() for word in id_string.replace("_", " ").split("."))

        return formatted_id

    def select_icon(self):
        icon_path, _ = QFileDialog.getOpenFileName(self, "Select Icon", "", "Images (*.png *.xpm *.jpg *.ico)")
        if icon_path:
            self.icon_input.setText(icon_path)

    def modify_name(self):
        old_name = self.old_name_input.text().strip()
        new_name = self.new_name_input.text().strip()
        icon = self.icon_input.text().strip()

        if old_name and new_name:
            modify_command = f"modify(find='{old_name}' title='{new_name}'"
            if icon:
                modify_command += f" icon='{icon}'"
            modify_command += ")"

            append_to_file(self.filepath, modify_command)
            self.refresh_modification_list()
            self.save_label_text(f"Modified '{old_name}' to '{new_name}'")
            QTimer.singleShot(3000, self.clear_save_label)

    def delete_modification_item(self, row, column):
        if column == 3:
            old_name = self.modification_list.item(row, 0).text().strip() if self.modification_list.item(row, 0) else ""
            new_name = self.modification_list.item(row, 1).text().strip() if self.modification_list.item(row, 1) else ""
            icon_item = self.modification_list.item(row, 2)
            icon = icon_item.icon().name() if icon_item and icon_item.icon() else ""
            
            delete_from_file(self.filepath, [old_name, new_name, icon])
            self.modification_list.removeRow(row)
            self.modification_list.hovered_row = -1
            self.save_label_text("Modification deleted.")
            QTimer.singleShot(3000, self.clear_save_label)

    def add_remove_item(self):
        dialog = RoundedInputDialog(self, "Add Remove Item", "Enter item to remove:")
        text, ok = dialog.getText()
        if ok and text:
            self.removed_items.append(text)
            self.remove_list.addItem(text)
            self.update_remove_line()

    def delete_remove_item(self, item_text):
        self.removed_items.remove(item_text)
        for i in range(self.remove_list.count()):
            if self.remove_list.item(i).text() == item_text:
                self.remove_list.takeItem(i)
                break
        self.update_remove_line()

    def update_remove_line(self):
        content = read_file(self.filepath)
        lines = content.split('\n')
        new_lines = []
        remove_line_exists = False
        for line in lines:
            if line.strip().startswith("remove(find="):
                remove_line_exists = True
                if self.removed_items:
                    new_lines.append(f'remove(find="{"|".join(self.removed_items)}")')
            else:
                new_lines.append(line)
        
        if not remove_line_exists and self.removed_items:
            new_lines.append(f'remove(find="{"|".join(self.removed_items)}")')

        write_file(self.filepath, "\n".join(new_lines))
        self.save_label_text("Removed items updated.")
        QTimer.singleShot(3000, self.clear_save_label)

    def refresh_modification_list(self):
            content = read_file(self.filepath)
            modify_lines = extract_modify_lines(content)
            self.modification_list.set_items(modify_lines)

    def add_remove_item(self):
        dialog = RoundedInputDialog(self, "Add Remove Item", "Enter item to remove:")
        text, ok = dialog.getText()
        if ok and text:
            self.removed_items.append(text)
            self.remove_list.addItem(text)
            self.update_remove_line()

    def delete_remove_item(self, item_text):
        self.removed_items.remove(item_text)
        for i in range(self.remove_list.count()):
            if self.remove_list.item(i).text() == item_text:
                self.remove_list.takeItem(i)
                break
        self.update_remove_line()

    def add_import_item(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select .nss File", self.project_root, "NSS Files (*.nss)")
        if file_path:
            relative_path = os.path.relpath(file_path, self.project_root).replace('\\', '/')
            if not relative_path.endswith('.nss'):
                relative_path += '.nss'

            file_name_only = os.path.basename(relative_path)

            if (file_name_only, relative_path) not in self.imported_items:
                self.imported_items.append((file_name_only, relative_path))
                self.import_list.addItem(file_name_only)
                self.update_shell_nss_imports()
                self.save_label_text(f"Added import: {file_name_only}")
                QTimer.singleShot(3000, self.clear_save_label)
            else:
                msgBox = CustomMessageBox(self)
                msgBox.setIcon(QMessageBox.Information)
                msgBox.setText("Info")
                msgBox.setInformativeText("This .nss file is already imported.")
                msgBox.setStandardButtons(QMessageBox.Ok)
                msgBox.exec_()

    def delete_import_item(self, item_text):
        # Find the tuple in self.imported_items that matches the filename
        for i, (filename, relative_path) in enumerate(self.imported_items):
            if filename == item_text:
                del self.imported_items[i]
                break
        for i in range(self.import_list.count()):
            if self.import_list.item(i).text() == item_text:
                self.import_list.takeItem(i)
                break
        self.update_shell_nss_imports()
        self.save_label_text(f"Removed import: {item_text}")
        QTimer.singleShot(3000, self.clear_save_label)

    def refresh_modification_list(self):
            content = read_file(self.filepath)
            modify_lines = extract_modify_lines(content)
            self.modification_list.set_items(modify_lines)

    def add_import_item(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select .nss File", self.project_root, "NSS Files (*.nss)")
        if file_path:
            relative_path = os.path.relpath(file_path, self.project_root).replace('\\', '/')
            if not relative_path.endswith('.nss'):
                relative_path += '.nss'

            file_name_only = os.path.basename(relative_path)

            if (file_name_only, relative_path) not in self.imported_items:
                self.imported_items.append((file_name_only, relative_path))
                self.import_list.addItem(file_name_only)
                self.update_shell_nss_imports()
                self.save_label_text(f"Added import: {file_name_only}")
                QTimer.singleShot(3000, self.clear_save_label)
            else:
                msgBox = CustomMessageBox(self)
                msgBox.setIcon(QMessageBox.Information)
                msgBox.setText("Info")
                msgBox.setInformativeText("This .nss file is already imported.")
                msgBox.setStandardButtons(QMessageBox.Ok)
                msgBox.exec_()

    def delete_import_item(self, item_text):
        # Find the tuple in self.imported_items that matches the filename
        for i, (filename, relative_path) in enumerate(self.imported_items):
            if filename == item_text:
                del self.imported_items[i]
                break
        for i in range(self.import_list.count()):
            if self.import_list.item(i).text() == item_text:
                self.import_list.takeItem(i)
                break
        self.update_shell_nss_imports()
        self.save_label_text(f"Removed import: {item_text}")
        QTimer.singleShot(3000, self.clear_save_label)

    def update_shell_nss_imports(self):
        try:
            with open(self.shell_nss_path, 'r') as f:
                original_lines = f.readlines()

            # 1. Get all import paths currently in the file
            existing_import_paths_in_file = set()
            for line in original_lines:
                stripped_line = line.strip()
                match = re.search(r"^import\s+'(.*\.nss)'$", stripped_line)
                if match:
                    existing_import_paths_in_file.add(match.group(1))

            # 2. Determine which imports need to be removed and which need to be added
            current_imported_paths = {path for _, path in self.imported_items}
            imports_to_remove = existing_import_paths_in_file - current_imported_paths
            imports_to_add = current_imported_paths - existing_import_paths_in_file

            # 3. Construct the new content, preserving non-import lines and existing desired imports
            new_content_lines = []
            for line in original_lines:
                stripped_line = line.strip()
                match = re.search(r"^import\s+'(.*\.nss)'$", stripped_line)
                
                if match:
                    current_import_path = match.group(1)
                    if current_import_path not in imports_to_remove:
                        new_content_lines.append(line)
                else:
                    new_content_lines.append(line)

            # 4. Append any new imports that were not present in the original file
            if imports_to_add:
                if new_content_lines and new_content_lines[-1].strip() != "":
                    new_content_lines.append("\n")
                
                for new_import_path in sorted(list(imports_to_add)):
                    new_content_lines.append(f"import '{new_import_path}'\n")
                

            write_file(self.shell_nss_path, "".join(new_content_lines))

        except Exception as e:
            msgBox = CustomMessageBox(self)
            msgBox.setIcon(QMessageBox.Critical)
            msgBox.setText("Error")
            msgBox.setInformativeText(f"An error occurred while updating shell.nss: {str(e)}")
            msgBox.setStandardButtons(QMessageBox.Ok)
            msgBox.exec_()

    def save_changes(self):
        try:
            content = read_file(self.filepath)

            hide_ids = [self.hide_list.item(i).data(Qt.UserRole) for i in range(self.hide_list.count())]
            content = update_section(content, "// hide\nmodify(mode=mode.multiple\nwhere=this.id(", ") vis=vis.remove)", hide_ids)

            more_ids = [self.more_list.item(i).data(Qt.UserRole) for i in range(self.more_list.count())]
            content = update_section(content, "// more\nmodify(mode=mode.multiple\nwhere=this.id(", ") menu=title.options)", more_ids)

            shift_ids = [self.shift_list.item(i).data(Qt.UserRole) for i in range(self.shift_list.count())]
            content = update_section(content, "// shift\nmodify(mode=single\nwhere=this.id(", ") vis=key.shift())", shift_ids)

            write_file(self.filepath, content)
            self.save_label_text("Changes saved successfully!")
            QTimer.singleShot(3000, self.clear_save_label)
        except Exception as e:
            msgBox = CustomMessageBox(self)
            msgBox.setIcon(QMessageBox.Critical)
            msgBox.setText("Error")
            msgBox.setInformativeText(f"An error occurred while saving changes: {str(e)}")
            msgBox.setStandardButtons(QMessageBox.Ok)
            msgBox.exec_()


    def save_data(self):
        content = read_file(self.filepath)

        hide_ids = [id_ for id_ in self.hide_list.original_items]
        more_ids = [id_ for id_ in self.more_list.original_items]
        shift_ids = [id_ for id_ in self.shift_list.original_items]

        data = {
            "filepath": self.filepath,
            "content": content,
            "hide_ids": hide_ids,
            "more_ids": more_ids,
            "shift_ids": shift_ids,
        }
        return data


    def save_label_text(self, text):
        self.save_label.setText(text)

    def clear_save_label(self):
         self.save_label.setText("")

    def edit_modification(self, row, column, text):
       if not self.modification_list:
            return

       original_line = self.modification_list.item(row, 3).data(Qt.UserRole) # Get original line

       current_old_name = self.modification_list.item(row, 0).text().strip()
       current_new_name = self.modification_list.item(row, 1).text().strip()
       current_icon = self.modification_list.item(row, 2).data(Qt.UserRole) # Get current icon path

       new_elements = [current_old_name, current_new_name, current_icon]
       print(f"edit_modification: original_line={original_line}, new_elements={new_elements}")

       modify_from_file(self.filepath, original_line, new_elements)
       self.refresh_modification_list()
       self.save_label_text("Modification updated.")
       QTimer.singleShot(3000, self.clear_save_label)

    def edit_icon_modification(self, row, icon_path):
       if not self.modification_list:
            return

       original_line = self.modification_list.item(row, 3).data(Qt.UserRole) # Get original line

       current_old_name = self.modification_list.item(row, 0).text().strip()
       current_new_name = self.modification_list.item(row, 1).text().strip()

       new_elements = [current_old_name, current_new_name, icon_path]
       print(f"edit_icon_modification: original_line={original_line}, new_elements={new_elements}")

       modify_from_file(self.filepath, original_line, new_elements)
       self.refresh_modification_list()
       self.save_label_text("Icon updated.")
       QTimer.singleShot(3000, self.clear_save_label)
