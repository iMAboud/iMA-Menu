import sys
import os
from PyQt5.QtWidgets import (QApplication, QWidget, QLabel, QListWidget, QPushButton,
                             QHBoxLayout, QVBoxLayout, QFileDialog, QAbstractItemView,
                             QMessageBox, QListWidgetItem, QStyledItemDelegate,
                             QStyleOptionViewItem, QStyle, QDialog, QLineEdit, QFrame,
                             QScrollArea)
from PyQt5.QtGui import QPalette, QColor, QDrag, QPixmap, QPainter, QFont, QFontMetrics
from PyQt5.QtCore import Qt, QMimeData, QPoint, pyqtSignal, QTimer

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPT_DIR = os.path.dirname(BASE_DIR)
FILE_PATH = os.path.join(SCRIPT_DIR, "shell.nss")
IMPORTS_PATH = os.path.join(SCRIPT_DIR, "imports")

class DarkGrayStyle(QStyledItemDelegate):
    def paint(self, painter, option, index):
        painter.save()
        
        if option.state & QStyle.State_Selected:
           painter.setBrush(QColor(70, 0, 100))
           painter.setPen(Qt.NoPen)
           painter.drawRoundedRect(option.rect.adjusted(1, 1, -1, -1), 11, 11)
           
        if option.state & QStyle.State_MouseOver:
           painter.setPen(QColor(150, 0, 150))
           painter.drawRoundedRect(option.rect.adjusted(1, 1, -1, -1), 11, 11)
         
        text = index.data()
        painter.setPen(QColor(200, 200, 200))
        painter.setFont(QFont("Arial", 14))
        painter.drawText(option.rect, Qt.AlignLeft | Qt.AlignVCenter, text)
        painter.restore()
    
    def sizeHint(self, option, index):
        size = super().sizeHint(option, index)
        size.setHeight(35)
        return size

class RoundedInputDialog(QDialog):
    def __init__(self, parent=None, title="", label="", default_text=""):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Popup)
        self.setStyleSheet("background-color: #333; border-radius: 20px;")
        layout = QVBoxLayout()
        label_widget = QLabel(label)
        label_widget.setStyleSheet("color: white; font-size: 14px; padding-left: 15px; padding-top: 15px;")
        layout.addWidget(label_widget)
        self.input_field = QLineEdit(default_text)
        self.input_field.setStyleSheet("""
            QLineEdit {
                background-color: #555;
                color: white;
                border: none;
                border-radius: 10px;
                padding: 8px;
                margin: 10px;
                font-size: 14px;
            }
        """)
        layout.addWidget(self.input_field)
        buttons_layout = QHBoxLayout()
        ok_button = QPushButton("Ok")
        ok_button.clicked.connect(self.accept)
        ok_button.setStyleSheet("""
            QPushButton {
                background-color: #2ecc71;
                color: white;
                border: none;
                border-radius: 10px;
                padding: 8px;
                 margin: 10px;
                 font-size: 12px;
                 text-shadow: -1px -1px 0 black, 1px -1px 0 black, -1px 1px 0 black, 1px 1px 0 black;
            }
            QPushButton:hover {
              background-color: #27ae60;
            }
        """)
        buttons_layout.addWidget(ok_button)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                border-radius: 10px;
                padding: 8px;
                 margin: 10px;
                 font-size: 12px;
                  text-shadow: -1px -1px 0 black, 1px -1px 0 black, -1px 1px 0 black, 1px 1px 0 black;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)
        buttons_layout.addWidget(cancel_button)
        layout.addLayout(buttons_layout)
        self.setLayout(layout)
        self.input_field.setFocus()  # Set focus to the input field

    def getText(self):
        if self.exec_() == QDialog.Accepted:
            return self.input_field.text(), True
        else:
           return "", False

class ShellEditor(QWidget):
    def __init__(self):
        super().__init__()
        self.file_path = FILE_PATH
        self.imports_path = IMPORTS_PATH
        self.remove_items = []
        self.import_items = []
        self.remove_start = -1
        self.remove_start_line = ""
        self.remove_end_line = ""
        self.import_start = -1
        self.initUI()
        self.load_data()

    def set_button_style(self, button):
       button.setStyleSheet("""
           QPushButton {
               
               color: white;
               border-radius: 8px;
               padding: 12px;
               text-shadow: -1px -1px 0 black, 1px -1px 0 black, -1px 1px 0 black, 1px 1px 0 black;
                font-size: 16px;
           }
           QPushButton:hover {
             
           }
           QPushButton:pressed {
              padding-left: 13px;
              padding-top: 13px;
           }
        """)

    def initUI(self):
        self.setWindowTitle("Shell.nss Editor")
        self.setGeometry(100, 100, 800, 600)
        self.setMinimumSize(800, 600)
        self.setStyleSheet("background-color: #282828; color: #FFFFFF;")

        remove_label = QLabel("Remove Items")
        remove_label.setStyleSheet("font-weight: bold; background: none; font-size: 16px; padding-bottom: 5px;  padding-left: 5px;")
        remove_label.setAlignment(Qt.AlignCenter)
        self.remove_list = QListWidget()
        self.remove_list.setItemDelegate(DarkGrayStyle())
        self.remove_list.setStyleSheet("background-color: #1e1e1e; border-radius: 22px; padding: 10px; font-size: 14px; spacing: 5px;")
        self.add_remove_button = QPushButton("Add")
        self.add_remove_button.clicked.connect(self.add_remove_item)
        self.set_button_style(self.add_remove_button)
        self.add_remove_button.setStyleSheet(self.add_remove_button.styleSheet() + "QPushButton { background-color: #3498db; } QPushButton:hover {background-color: #2980b9;}")
        self.remove_text_remove_button = QPushButton("Remove")
        self.remove_text_remove_button.clicked.connect(self.remove_remove_items)
        self.set_button_style(self.remove_text_remove_button)
        self.remove_text_remove_button.setStyleSheet(self.remove_text_remove_button.styleSheet() + "QPushButton {background-color: #777777;} QPushButton:hover {background-color: #666666;}")
        self.remove_list.setSelectionMode(QAbstractItemView.SingleSelection)  # Only allow one item to be selected at a time
        remove_layout = QVBoxLayout()
        remove_layout.addWidget(remove_label)
        remove_layout.addWidget(self.remove_list)
        remove_buttons_layout = QHBoxLayout()
        remove_buttons_layout.addWidget(self.add_remove_button)
        remove_buttons_layout.addWidget(self.remove_text_remove_button)
        remove_layout.addLayout(remove_buttons_layout)

        import_label = QLabel("Import File")
        import_label.setStyleSheet("font-weight: bold; background: none; font-size: 16px;  padding-bottom: 5px;  padding-left: 5px;")
        import_label.setAlignment(Qt.AlignCenter)
        self.import_list = QListWidget()
        self.import_list.setItemDelegate(DarkGrayStyle())
        self.import_list.setStyleSheet("background-color: #1e1e1e; border-radius: 22px; padding: 10px; font-size: 14px; spacing: 5px;")
        self.add_import_button = QPushButton("Add")
        self.add_import_button.clicked.connect(self.add_import_item)
        self.set_button_style(self.add_import_button)
        self.add_import_button.setStyleSheet(self.add_import_button.styleSheet() + "QPushButton {background-color: #3498db; } QPushButton:hover {background-color: #2980b9;}")
        self.remove_import_button = QPushButton("Remove")
        self.remove_import_button.clicked.connect(self.remove_import_items)
        self.set_button_style(self.remove_import_button)
        self.remove_import_button.setStyleSheet(self.remove_import_button.styleSheet() + "QPushButton {background-color: #777777;} QPushButton:hover {background-color: #666666;}")
        self.import_list.setSelectionMode(QAbstractItemView.SingleSelection) # Only allow one item to be selected at a time
        import_layout = QVBoxLayout()
        import_layout.addWidget(import_label)
        import_layout.addWidget(self.import_list)
        import_buttons_layout = QHBoxLayout()
        import_buttons_layout.addWidget(self.add_import_button)
        import_buttons_layout.addWidget(self.remove_import_button)
        import_layout.addLayout(import_buttons_layout)
        main_layout = QHBoxLayout()
        main_layout.addLayout(remove_layout)
        main_layout.addLayout(import_layout)

        self.save_button = QPushButton("Save")
        self.save_button.clicked.connect(self.save_changes)
        self.set_button_style(self.save_button)
        self.save_button.setStyleSheet(self.save_button.styleSheet() + "QPushButton {background-color: #21964d;} QPushButton:hover {background-color: #1e8441;}")

        self.save_status_label = QLabel("")
        self.save_status_label.setStyleSheet("color: #2ecc71; font-size: 12px; background: none")
        self.save_status_label.setAlignment(Qt.AlignCenter)
        bottom_layout = QVBoxLayout()
        bottom_button_layout = QHBoxLayout()
        bottom_button_layout.addWidget(self.save_button)
        bottom_layout.addLayout(bottom_button_layout)
        bottom_layout.addWidget(self.save_status_label)
        bottom_layout.setAlignment(Qt.AlignCenter)
        overall_layout = QVBoxLayout()
        overall_layout.addLayout(main_layout)
        overall_layout.addLayout(bottom_layout)
        self.setLayout(overall_layout)

    def load_data(self):
        try:
            with open(self.file_path, 'r') as file:
                lines = file.readlines()
                for i, line in enumerate(lines):
                    if "remove(find=" in line:
                        self.remove_start = i
                        self.remove_start_line = lines[i-1] if i > 0 else ''
                        self.remove_end_line = lines[i+1] if i < len(lines) - 1 else ''
                        remove_line = line.strip()
                        items_str = remove_line[remove_line.find("remove(find=\"") + len("remove(find=\"") :remove_line.rfind("\")")]
                        self.remove_items = items_str.split('|') if items_str else []
                        for item in self.remove_items:
                            self.remove_list.addItem(item)

                    if "import" in line and self.import_start == -1:
                       self.import_start = i
                if self.import_start != -1:
                    for line in lines[self.import_start:]:
                        line = line.strip()
                        if line.startswith("import 'imports/"):
                          file_name = line[line.rfind("/")+1:line.rfind("'")]
                          self.import_items.append(file_name)
                          self.import_list.addItem(file_name)
        except FileNotFoundError:
            QMessageBox.critical(self, "Error", f"File not found: {self.file_path}")
            self.close()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error loading file: {e}")
            self.close()
    def import_item_reordered(self, old_index, new_index):
        item = self.import_items.pop(old_index)
        self.import_items.insert(new_index, item)
    
    def add_remove_item(self):
         dialog = RoundedInputDialog(self, "Add Remove Item", "Type item name to remove:")
         text, ok = dialog.getText()
         if ok and text:
            self.remove_items.append(text)
            self.remove_list.addItem(text)
    
    def remove_remove_items(self):
        selected_items = self.remove_list.selectedItems()
        if not selected_items:
            QMessageBox.information(self, "Info", "Select an item to remove")
            return
        for item in selected_items:
            row = self.remove_list.row(item)
            self.remove_list.takeItem(row)
            self.remove_items.pop(row)
    
    def add_import_item(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Import File", self.imports_path, "NSS Files (*.nss)")
        if file_path:
            file_name = os.path.basename(file_path)
            if file_name not in self.import_items:
                self.import_items.append(file_name)
                self.import_list.addItem(file_name)
            else:
                QMessageBox.information(self, "Info", "Import already on the list")

    def remove_import_items(self):
        selected_items = self.import_list.selectedItems()
        if not selected_items:
            QMessageBox.information(self, "Info", "Select an item to remove")
            return
        for item in selected_items:
            row = self.import_list.row(item)
            self.import_list.takeItem(row)
            self.import_items.pop(row)

    def save_changes(self):
        try:
            with open(self.file_path, 'r') as file:
                lines = file.readlines()
            if self.remove_start != -1:
                new_remove_str = ""
                if self.remove_items:
                    new_remove_str = "remove(find=\"" + "|".join(self.remove_items) + "\")"
                if self.remove_items:
                    lines[self.remove_start] = new_remove_str + '\n'
                else:
                    lines.pop(self.remove_start)
                    if not lines[self.remove_start-1].strip():
                        lines.pop(self.remove_start - 1)
            if self.import_start != -1:
                 new_lines = lines[:self.import_start]
                 for line in lines[self.import_start:]:
                     line = line.strip()
                     if not line.startswith("import 'imports/"):
                         new_lines.append(line + '\n')
                 for import_file in self.import_items:
                    new_lines.append(f"import 'imports/{import_file}'\n")
                 lines = new_lines
            else:
                for import_file in self.import_items:
                   lines.append(f"import 'imports/{import_file}'\n")

            with open(self.file_path, 'w') as file:
                file.writelines(lines)
            self.save_status_label.setText("Saved!")
            QTimer.singleShot(3000, lambda: self.save_status_label.setText(""))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error saving file: {e}")
            
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()
        else:
             super().keyPressEvent(event)

    def mousePressEvent(self, event):
          if event.button() == Qt.LeftButton:
             # Deselect from remove list
             if not self.remove_list.geometry().contains(event.pos()):
                 if not self.add_remove_button.geometry().contains(event.pos()) and not self.remove_text_remove_button.geometry().contains(event.pos()):
                     self.remove_list.clearSelection()

            # Deselect from import list
             if not self.import_list.geometry().contains(event.pos()):
                if not self.add_import_button.geometry().contains(event.pos()) and not self.remove_import_button.geometry().contains(event.pos()):
                    self.import_list.clearSelection()
          super().mousePressEvent(event)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(40, 40, 40))
    palette.setColor(QPalette.WindowText, Qt.white)
    palette.setColor(QPalette.Base, QColor(50, 50, 50))
    palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
    palette.setColor(QPalette.ToolTipBase, Qt.white)
    palette.setColor(QPalette.ToolTipText, Qt.white)
    palette.setColor(QPalette.Text, Qt.white)
    palette.setColor(QPalette.Button, QColor(53, 53, 53))
    palette.setColor(QPalette.ButtonText, Qt.white)
    palette.setColor(QPalette.BrightText, Qt.red)
    palette.setColor(QPalette.Link, QColor(42, 130, 218))
    palette.setColor(QPalette.Highlight, QColor(70, 70, 70))
    palette.setColor(QPalette.HighlightedText, Qt.white)
    app.setPalette(palette)
    editor = ShellEditor()
    editor.show()
    sys.exit(app.exec_())
