import sys
import os
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QLineEdit, QFileDialog, QGridLayout,
                             QComboBox, QMessageBox, QScrollArea, QFrame, QDialog)
from PyQt5.QtGui import QPixmap, QColor
from PyQt5.QtCore import Qt, pyqtSignal, QPropertyAnimation, QRect, QEvent
from PyQt5.Qt import QGraphicsBlurEffect

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPT_DIR = os.path.dirname(BASE_DIR)
FILE_PATH = os.path.join(SCRIPT_DIR, "imports", "shortcut.nss")

class RoundedCard(QFrame):
    selection_changed = pyqtSignal(object)
    def __init__(self, title, image_path, item_index, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.StyledPanel)
        self.setFrameShadow(QFrame.Raised)
        self.setFixedSize(120, 120)
        self.setStyleSheet("background-color: #333333; border-radius: 10px; padding: 0px;")
        self.image_label = QLabel()
        self.image_label.setStyleSheet("background-color: transparent; border: none;")
        self.set_image(image_path)
        layout = QVBoxLayout()
        layout.addWidget(self.image_label)
        layout.setAlignment(Qt.AlignTop)
        self.setLayout(layout)
        self.selected = False
        self.item_index = item_index
        self.title = title
    def set_image(self, image_path):
        try:
            pixmap = QPixmap(image_path)
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(self.image_label.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                self.image_label.setPixmap(scaled_pixmap)
                self.image_label.setAlignment(Qt.AlignCenter)
            else:
                self.image_label.setText("Invalid Image")
                self.image_label.setStyleSheet("color: #FFFFFF; background-color: transparent;")
                self.image_label.setAlignment(Qt.AlignCenter)
        except Exception:
            self.image_label.setText("Invalid Image")
            self.image_label.setStyleSheet("color: #FFFFFF; background-color: transparent;")
            self.image_label.setAlignment(Qt.AlignCenter)
    def resizeEvent(self, event):
         if self.image_label.pixmap():
            scaled_pixmap = self.image_label.pixmap().scaled(self.image_label.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            self.image_label.setPixmap(scaled_pixmap)
         super().resizeEvent(event)
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
             self.toggle_selection()
             self.selection_changed.emit(self)
        super().mousePressEvent(event)
    def toggle_selection(self):
        self.selected = not self.selected
        self.setStyleSheet("background-color: #333333; border-radius: 10px; padding: 0px; border: 2px solid #1a73e8;" if self.selected else "background-color: #333333; border-radius: 10px; padding: 0px;")

class AddItemPopup(QDialog):
    item_added_signal = pyqtSignal(dict)
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlag(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet("background-color: rgba(0, 0, 0, 0.3);")
        self.popup_card = QFrame()
        self.popup_card.setStyleSheet("background-color: #1E1E1E; border-radius: 22px; padding: 20px;")
        layout = QVBoxLayout(self)
        layout.addWidget(self.popup_card, alignment=Qt.AlignCenter)
        card_layout = QVBoxLayout()
        self.popup_card.setLayout(card_layout)
        self.shortcut_path_layout = QHBoxLayout()
        self.shortcut_button = QPushButton("Select Shortcut Path")
        self.shortcut_button.setStyleSheet("background-color: #0078d4; color: #FFFFFF; border-radius: 8px; padding: 5px;")
        self.shortcut_button.clicked.connect(self.select_shortcut_path)
        self.shortcut_path_text = QLineEdit()
        self.shortcut_path_text.setStyleSheet("background-color: rgba(255, 255, 255, 0.1); border-radius: 8px; padding: 5px; color: #FFFFFF;")
        self.shortcut_path_layout.addWidget(self.shortcut_button)
        self.shortcut_path_layout.addWidget(self.shortcut_path_text)
        card_layout.addLayout(self.shortcut_path_layout)
        self.shortcut_path_layout.setContentsMargins(0, 0, 0, 10)
        self.command_input_layout = QHBoxLayout()
        self.command_label = QLabel("Command:")
        self.command_label.setStyleSheet("font-size: 16px; color: #FFFFFF; margin-right: 5px; background-color: transparent;")
        self.command_input = QLineEdit()
        self.command_input.setStyleSheet("background-color: rgba(255, 255, 255, 0.1); border-radius: 8px; padding: 5px; color: #FFFFFF;")
        self.command_input_layout.addWidget(self.command_label)
        self.command_input_layout.addWidget(self.command_input)
        card_layout.addLayout(self.command_input_layout)
        self.command_input_layout.setContentsMargins(0, 0, 0, 10)
        self.icon_layout = QHBoxLayout()
        self.icon_button = QPushButton("Select Icon")
        self.icon_button.setStyleSheet("background-color: #0078d4; color: #FFFFFF; border-radius: 8px; padding: 5px;")
        self.icon_button.clicked.connect(self.select_icon)
        self.icon_text = QLineEdit()
        self.icon_text.setStyleSheet("background-color: rgba(255, 255, 255, 0.1); border-radius: 8px; padding: 5px; color: #FFFFFF;")
        self.icon_layout.addWidget(self.icon_button)
        self.icon_layout.addWidget(self.icon_text)
        card_layout.addLayout(self.icon_layout)
        self.icon_layout.setContentsMargins(0, 0, 0, 10)
        self.key_layout = QHBoxLayout()
        self.key_dropdown_label = QLabel("Key:")
        self.key_dropdown_label.setStyleSheet("font-size: 16px; color: #FFFFFF; margin-right: 5px; background-color: transparent;")
        self.key_dropdown = QComboBox()
        key_options = ["ALL", "key.apps", "key.back", "key.cancel", "key.capital", "key.capslock", "key.control",
                         "key.delete", "key.down", "key.end", "key.enter", "key.escape", "key.execute", "key.f1",
                         "key.f10", "key.f11", "key.f12", "key.f2", "key.f3", "key.f4", "key.f5", "key.f6",
                         "key.f7", "key.f8", "key.f9", "key.help", "key.home", "key.insert", "key.lalt",
                         "key.lcontrol", "key.left", "key.lshift", "key.lwin", "key.next",
                         "key.pagedown", "key.pageup", "key.pause", "key.play", "key.print", "key.printscreen",
                         "key.prior", "key.ralt", "key.rcontrol", "key.return", "key.right", "key.rshift",
                         "key.rwin", "key.shift", "key.snapshot", "key.space", "key.tab", "key.up", "key.win"]
        self.key_dropdown.addItems([opt[4:].upper() if "key." in opt else opt for opt in key_options])
        self.key_dropdown.setStyleSheet("background-color: rgba(255, 255, 255, 0.1); border-radius: 8px; padding: 5px; color: #FFFFFF;")
        self.key_dropdown.setCurrentIndex(0)
        self.key_layout.addWidget(self.key_dropdown_label)
        self.key_layout.addWidget(self.key_dropdown)
        card_layout.addLayout(self.key_layout)
        self.key_layout.setContentsMargins(0, 0, 0, 10)
        self.title_layout = QHBoxLayout()
        self.title_label = QLabel("Title:")
        self.title_label.setStyleSheet("font-size: 16px; color: #FFFFFF; margin-right: 5px; background-color: transparent;")
        self.title_input = QLineEdit()
        self.title_input.setStyleSheet("background-color: rgba(255, 255, 255, 0.1); border-radius: 8px; padding: 5px; color: #FFFFFF;")
        self.title_layout.addWidget(self.title_label)
        self.title_layout.addWidget(self.title_input)
        card_layout.addLayout(self.title_layout)
        self.create_button = QPushButton("Add")
        self.create_button.setStyleSheet("background-color: #1a73e8; color: #FFFFFF; border-radius: 8px; padding: 10px; margin-top: 10px;")
        self.create_button.clicked.connect(self.create_item)
        card_layout.addWidget(self.create_button)
        self.shortcut_button = self.shortcut_button
        self.shortcut_path_text = self.shortcut_path_text
    def showEvent(self, event):
        self.blur_effect = QGraphicsBlurEffect(self)
        self.blur_effect.setBlurRadius(15)
        self.parent().window().setGraphicsEffect(self.blur_effect)
        parent_rect = self.parent().window().geometry()
        popup_rect = self.geometry()
        center_point = parent_rect.center()
        popup_rect.moveCenter(center_point)
        self.setGeometry(popup_rect)
        self.parent().window().installEventFilter(self)
    def hideEvent(self, event):
        self.parent().window().setGraphicsEffect(None)
        self.parent().window().removeEventFilter(self)
    def eventFilter(self, obj, event):
         if event.type() == QEvent.MouseButtonPress:
            if obj == self.parent().window() and not self.geometry().contains(event.globalPos()):
                self.close()
                return True
         return super().eventFilter(obj, event)
    def select_shortcut_path(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Shortcut", "", "All Files (*)")
        if file_path:
            self.shortcut_path_text.setText(file_path)
    def select_icon(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Icon", "", "Images (*.png *.xpm *.jpg *.ico)")
        if file_path:
            self.icon_text.setText(file_path)
    def create_item(self):
        shortcut_path = self.shortcut_path_text.text()
        cmd_input = self.command_input.text().strip()
        icon_path = self.icon_text.text()
        key_selected = self.key_dropdown.currentText()
        title = self.title_input.text()
        if not shortcut_path and not cmd_input:
             self.close()
             return
        new_item = {
            "type": "shortcut" if shortcut_path else "cmd",
            "shortcut_path": shortcut_path,
            "cmd_input": cmd_input,
            "icon_path": icon_path,
            "key_selected": key_selected.lower() if key_selected != "ALL" else "none",
            "title": title,
        }
        self.item_added_signal.emit(new_item)
        self.accept()

class MainWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("iMA - Shortcut Creator")
        self.setGeometry(100, 100, 800, 600)
        self.setMinimumSize(800, 600)
        self.selected_card = None
        self.card_widgets = []
        global filepath
        filepath = FILE_PATH
        self.items = self.load_items_from_file()
        self.init_ui()
    def init_ui(self):
        layout = QVBoxLayout()
        self.setStyleSheet("background-color: #1E1E1E; border-radius: 22px; padding: 5px;")
        add_button_layout = QHBoxLayout()
        add_button_layout.addStretch()
        self.add_button_card = QFrame()
        self.add_button_card.setStyleSheet("background-color: #2b2b2b; border-radius: 22px; padding: 10px;")
        self.add_button = QPushButton("+")
        self.add_button.setStyleSheet("background-color: #1a73e8; color: #FFFFFF; border-radius: 22px; padding: 10px; font-size: 20px; font-weight: bold;")
        self.add_button.clicked.connect(self.open_popup)
        add_button_layout.addWidget(self.add_button_card)
        add_button_layout.setAlignment(self.add_button_card, Qt.AlignHCenter)
        self.add_button_card.setLayout(QHBoxLayout())
        self.add_button_card.layout().addWidget(self.add_button)
        layout.addLayout(add_button_layout)
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("background: transparent;")
        self.scroll_area_widget = QWidget()
        self.grid_layout = QGridLayout(self.scroll_area_widget)
        self.scroll_area.setWidget(self.scroll_area_widget)
        layout.addWidget(self.scroll_area)
        self.populate_cards()
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        self.delete_button = QPushButton("Delete")
        self.delete_button.setStyleSheet("background-color: #d32f2f; color: #FFFFFF; border-radius: 8px; padding: 10px;")
        self.delete_button.clicked.connect(self.delete_selected_card)
        self.delete_button.setEnabled(False)
        button_layout.addWidget(self.delete_button)
        layout.addLayout(button_layout)
        self.setLayout(layout)
        self.animate_window()
    def animate_window(self):
        animation = QPropertyAnimation(self, b"geometry")
        animation.setDuration(500)
        animation.setStartValue(QRect(100, 100, 800, 600))
        animation.setEndValue(QRect(100, 100, 800, 600))
        animation.start()
    def populate_cards(self):
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self.card_widgets.clear()
        row = 0
        col = 0
        for index, item_data in enumerate(self.items):
            card = RoundedCard(item_data["title"], item_data["icon_path"], index, self)
            card.selection_changed.connect(self.card_selected)
            title_label = QLabel(card.title)
            title_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #FFFFFF; background-color: transparent; text-align: center; border:none;")
            title_label.setAlignment(Qt.AlignCenter)
            card_layout = card.layout()
            card_layout.addWidget(title_label)
            self.grid_layout.addWidget(card, row, col, Qt.AlignTop | Qt.AlignLeft)
            self.card_widgets.append(card)
            col += 1
            if col > 4:
                col = 0
                row += 1
    def card_selected(self, card):
        if self.selected_card and self.selected_card != card:
            self.selected_card.toggle_selection()
        self.selected_card = card
        self.delete_button.setEnabled(card.selected)
    def open_popup(self):
        popup = AddItemPopup(self)
        popup.item_added_signal.connect(self.add_new_item)
        popup.exec_()
    def add_new_item(self, new_item):
        self.items.append(new_item)
        self.populate_cards()
        self.save_items_to_file() 
    def delete_selected_card(self):
        if self.selected_card:
            index_to_remove = self.selected_card.item_index
            if 0 <= index_to_remove < len(self.items):
                del self.items[index_to_remove]
                for w in self.card_widgets:
                    if w == self.selected_card:
                         index_to_remove = self.card_widgets.index(w)
                del self.card_widgets[index_to_remove]
                self.selected_card.setParent(None)
                self.selected_card.deleteLater()
                self.selected_card = None
                self.delete_button.setEnabled(False)
                self.populate_cards()
                self.save_items_to_file()  
            else:
                QMessageBox.warning(self, "Delete Error", "Unable to delete the item")
    def save_data(self):
        return {"filepath": filepath, "items": self.items}

    def create_cmd_file(self, command):
        file_path = os.path.join(os.path.dirname(filepath), 'temp_cmd.bat')
        try:
            with open(file_path, 'w') as file:
                file.write(f"@echo off\n{command}")
            return file_path
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create a cmd file: {str(e)}")
            return None

    def load_items_from_file(self):
       if not os.path.exists(filepath):
            open(filepath, "w").close()  

       try:
            content = read_file(filepath)
            items = []
            for line in content.strip().split('\n'):
                line = line.strip()  
                if line.startswith("item(") and line.endswith(")"):  
                    item_data = self.parse_line(line)
                    items.append(item_data)
            return items
       except Exception as e:
           QMessageBox.critical(self, "Error", f"Error reading file: {str(e)}")
           return []


    def parse_line(self, line):
        line = line[5:-1].strip() 

        item = {"type": None, "shortcut_path": "", "cmd_input": "", "icon_path": "",
                "key_selected": "none", "title": ""}

        parts = line.split(" ")

        for part in parts:
            if "=" not in part:
                continue  

            key, value = part.split("=", 1)
            value = value.strip("'")

            if key == "title":
                item["title"] = value
            elif key == "image":
                item["icon_path"] = value
            elif key == "cmd":
                if value.endswith((".bat", ".cmd")):
                    item["type"] = "cmd"
                    item["cmd_input"] = self.read_cmd_file(value)
                else:
                    item["type"] = "shortcut"
                    item["shortcut_path"] = value
            elif key == "vis":
                key_part = value.replace("key.", "").replace("()", "")
                item["key_selected"] = f"key.{key_part}" if key_part != "none" else "none"

        return item


    def read_cmd_file(self, file_path):
        if not os.path.exists(file_path):
            return None
        try:
            with open(file_path, 'r') as file:
                lines = file.readlines()
                for line in lines:
                    if not line.startswith("@echo off"):
                        return line.strip()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error reading command file: {str(e)}")
            return None

    def save_items_to_file(self):
        content = ""
        for item in self.items:
            item_str = "item("
            if item["title"]:
                item_str += f"title='{item['title']}' "
            if item["icon_path"]:
                item_str += f"image='{item['icon_path']}' "
            if item["type"] == "shortcut" and item["shortcut_path"]:
                item_str += f"cmd='{item['shortcut_path']}' "
            elif item["type"] == "cmd" and item["cmd_input"]:
                cmd_path = self.create_cmd_file(item["cmd_input"])
                if cmd_path:
                    item_str += f"cmd='{cmd_path}' "
            key_str = item["key_selected"].replace("key.", "") if item["key_selected"] != "none" else "none"
            item_str += f"vis='key.{key_str}()'"
            item_str += ")"  
            content += item_str + "\n"
        write_file(filepath, content)


def read_file(filepath):
    try:
        with open(filepath, 'r') as file:
            return file.read()
    except Exception as e:
        raise RuntimeError(f"Failed to read the file: {str(e)}")

def write_file(filepath, content):
    try:
        with open(filepath, 'w') as file:
            file.write(content)
    except Exception as e:
        raise RuntimeError(f"Failed to write the file: {str(e)}")

def main():
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
