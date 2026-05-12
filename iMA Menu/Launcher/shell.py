import sys
import os
import json
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QListWidget, QPushButton,
    QHBoxLayout, QVBoxLayout, QFileDialog, QAbstractItemView,
    QMessageBox, QListWidgetItem, QStyledItemDelegate,
    QStyleOptionViewItem, QStyle, QDialog, QLineEdit, QFrame,
    QScrollArea
)
from PyQt5.QtGui import QPalette, QColor, QDrag, QPixmap, QPainter, QFont, QFontMetrics
from PyQt5.QtCore import Qt, QMimeData, QPoint, pyqtSignal, QTimer

def load_theme(theme_name='default'):
    # In a real app, you might load this from a JSON file
    # For this example, we'll keep it simple and return a dictionary
    return {
        "palette": {
            "Window": "#282828", "WindowText": "#FFFFFF", "Base": "#1e1e1e",
            "AlternateBase": "#353535", "ToolTipBase": "#FFFFFF", "ToolTipText": "#FFFFFF",
            "Text": "#FFFFFF", "Button": "#353535", "ButtonText": "#FFFFFF",
            "BrightText": "#FF0000", "Link": "#2A82DA", "Highlight": "#464646",
            "HighlightedText": "#FFFFFF"
        },
        "dialog_theme": {
            "background_color": "#333", "border_radius": "20px",
            "input_bg": "#555", "ok_button_bg": "#2ecc71",
            "ok_button_hover_bg": "#27ae60", "cancel_button_bg": "#e74c3c",
            "cancel_button_hover_bg": "#c0392b"
        },
        "delegate_style": {
            "selected_bg": "#460064", "mouseover_border": "#960096",
            "text": "#C8C8C8", "radius": 11
        }
    }

class DarkGrayStyle(QStyledItemDelegate):
    def __init__(self, theme_style, parent=None):
        super().__init__(parent)
        self.theme_style = theme_style

    def paint(self, painter, option, index):
        painter.save()
        
        radius = self.theme_style.get('radius', 11)
        
        if option.state & QStyle.State_Selected:
           painter.setBrush(QColor(self.theme_style['selected_bg']))
           painter.setPen(Qt.NoPen)
           painter.drawRoundedRect(option.rect.adjusted(1, 1, -1, -1), radius, radius)
           
        if option.state & QStyle.State_MouseOver:
           painter.setPen(QColor(self.theme_style['mouseover_border']))
           painter.drawRoundedRect(option.rect.adjusted(1, 1, -1, -1), radius, radius)
         
        text = index.data()
        painter.setPen(QColor(self.theme_style['text']))
        painter.setFont(QFont("Arial", 14))
        painter.drawText(option.rect, Qt.AlignLeft | Qt.AlignVCenter, text)
        painter.restore()
    
    def sizeHint(self, option, index):
        size = super().sizeHint(option, index)
        size.setHeight(35)
        return size

class RoundedInputDialog(QDialog):
    def __init__(self, parent=None, title="", label="", default_text="", theme=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Popup)

        if not theme:
            theme = {
                "background_color": "#333", "border_radius": "20px",
                "input_bg": "#555", "ok_button_bg": "#2ecc71",
                "ok_button_hover_bg": "#27ae60", "cancel_button_bg": "#e74c3c",
                "cancel_button_hover_bg": "#c0392b"
            }

        self.setStyleSheet(f"background-color: {theme['background_color']}; border-radius: {theme['border_radius']};")
        
        layout = QVBoxLayout()
        label_widget = QLabel(label)
        label_widget.setStyleSheet("color: white; font-size: 14px; padding-left: 15px; padding-top: 15px;")
        layout.addWidget(label_widget)
        self.input_field = QLineEdit(default_text)
        self.input_field.setStyleSheet(f'''
            QLineEdit {{
                background-color: {theme['input_bg']};
                color: white;
                border: none;
                border-radius: 10px;
                padding: 8px;
                margin: 10px;
                font-size: 14px;
            }}
        ''')
        layout.addWidget(self.input_field)
        buttons_layout = QHBoxLayout()
        ok_button = QPushButton("Ok")
        ok_button.clicked.connect(self.accept)
        ok_button.setStyleSheet(f'''
            QPushButton {{
                background-color: {theme['ok_button_bg']};
                color: white;
                border: none;
                border-radius: 10px;
                padding: 8px;
                 margin: 10px;
                 font-size: 12px;
                 text-shadow: -1px -1px 0 black, 1px -1px 0 black, -1px 1px 0 black, 1px 1px 0 black;
            }}
            QPushButton:hover {{
              background-color: {theme['ok_button_hover_bg']};
            }}
        ''')
        buttons_layout.addWidget(ok_button)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        cancel_button.setStyleSheet(f'''
            QPushButton {{
                background-color: {theme['cancel_button_bg']};
                color: white;
                border: none;
                border-radius: 10px;
                padding: 8px;
                 margin: 10px;
                 font-size: 12px;
                  text-shadow: -1px -1px 0 black, 1px -1px 0 black, -1px 1px 0 black, 1px 1px 0 black;
            }}
            QPushButton:hover {{
                background-color: {theme['cancel_button_hover_bg']};
            }}
        ''')
        buttons_layout.addWidget(cancel_button)
        layout.addLayout(buttons_layout)
        self.setLayout(layout)
        self.input_field.setFocus()  

    def getText(self):
        if self.exec_() == QDialog.Accepted:
            return self.input_field.text(), True
        else:
           return "", False

class ShellEditor(QWidget):
    save_status_text_signal = pyqtSignal(str)
    def __init__(self, file_path, imports_path):
        super().__init__()
        self.file_path = file_path
        self.imports_path = imports_path
        self.theme = None
        self.remove_items = []
        self.import_items = []
        self.remove_start = -1
        self.remove_start_line = ""
        self.remove_end_line = ""
        self.import_start = -1
        self.initUI()
        self.load_data()

    def set_theme(self, theme):
        self.theme = theme
        self.initUI()
        self.load_data() # Reload data to apply theme to lists

    def set_button_style(self, button):
       button.setStyleSheet('''
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
        ''')

    def initUI(self):
        if self.layout():
            while self.layout().count():
                item = self.layout().takeAt(0)
                widget = item.widget()
                if widget:
                    widget.deleteLater()

        self.setWindowTitle("Shell.nss Editor")
        self.setGeometry(100, 100, 800, 600)
        self.setMinimumSize(800, 600)

        delegate_style = self.theme['delegate_style'] if self.theme else {
            'selected_bg': '#460064', 'mouseover_border': '#960096',
            'text': '#C8C8C8', 'radius': 11
        }

        remove_label = QLabel("Remove Items")
        remove_label.setStyleSheet("font-weight: bold; background: none; font-size: 16px; padding-bottom: 5px;  padding-left: 5px;")
        remove_label.setAlignment(Qt.AlignCenter)
        self.remove_list = QListWidget()
        self.remove_list.setItemDelegate(DarkGrayStyle(delegate_style))
        self.remove_list.setStyleSheet("background-color: #1e1e1e; border-radius: 22px; padding: 10px; font-size: 14px; spacing: 5px;")
        self.add_remove_button = QPushButton("Add")
        self.add_remove_button.clicked.connect(self.add_remove_item)
        self.set_button_style(self.add_remove_button)
        self.add_remove_button.setStyleSheet(self.add_remove_button.styleSheet() + "QPushButton { background-color: #3498db; } QPushButton:hover {background-color: #2980b9;}")
        self.remove_text_remove_button = QPushButton("Remove")
        self.remove_text_remove_button.clicked.connect(self.remove_remove_items)
        self.set_button_style(self.remove_text_remove_button)
        self.remove_text_remove_button.setStyleSheet(self.remove_text_remove_button.styleSheet() + "QPushButton {background-color: #777777;} QPushButton:hover {background-color: #666666;}")
        self.remove_list.setSelectionMode(QAbstractItemView.SingleSelection) 
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
        self.import_list.setItemDelegate(DarkGrayStyle(delegate_style))
        self.import_list.setStyleSheet("background-color: #1e1e1e; border-radius: 22px; padding: 10px; font-size: 14px; spacing: 5px;")
        self.add_import_button = QPushButton("Add")
        self.add_import_button.clicked.connect(self.add_import_item)
        self.set_button_style(self.add_import_button)
        self.add_import_button.setStyleSheet(self.add_import_button.styleSheet() + "QPushButton {background-color: #3498db; } QPushButton:hover {background-color: #2980b9;}")
        self.remove_import_button = QPushButton("Remove")
        self.remove_import_button.clicked.connect(self.remove_import_items)
        self.set_button_style(self.remove_import_button)
        self.remove_import_button.setStyleSheet(self.remove_import_button.styleSheet() + "QPushButton {background-color: #777777;} QPushButton:hover {background-color: #666666;}")
        self.import_list.setSelectionMode(QAbstractItemView.SingleSelection) 
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


        self.save_status_label = QLabel("")
        self.save_status_label.setStyleSheet("color: #2ecc71; font-size: 12px; background: none")
        self.save_status_label.setAlignment(Qt.AlignCenter)
        bottom_layout = QVBoxLayout()
        bottom_layout.addWidget(self.save_status_label)
        bottom_layout.setAlignment(Qt.AlignCenter)
        overall_layout = QVBoxLayout()
        overall_layout.addLayout(main_layout)
        overall_layout.addLayout(bottom_layout)
        self.setLayout(overall_layout)

    def load_data(self):
        self.remove_list.clear()
        self.import_list.clear()
        self.remove_items.clear()
        self.import_items.clear()
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
         dialog = RoundedInputDialog(self, "Add Remove Item", "Type item name to remove:", theme=self.theme.get('dialog_theme') if self.theme else None)
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

    def save_data(self):
       return {
            "file_path": self.file_path,
            "remove_start": self.remove_start,
            "remove_items": self.remove_items,
            "import_start": self.import_start,
            "import_items": self.import_items
        }
    def save_status_text(self, text):
        self.save_status_label.setText(text)
    
    def clear_save_status(self):
        self.save_status_label.setText("")
    
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()
        else:
             super().keyPressEvent(event)

    def mousePressEvent(self, event):
          if event.button() == Qt.LeftButton:
             if not self.remove_list.geometry().contains(event.pos()):
                 if not self.add_remove_button.geometry().contains(event.pos()) and not self.remove_text_remove_button.geometry().contains(event.pos()):
                     self.remove_list.clearSelection()

             if not self.import_list.geometry().contains(event.pos()):
                if not self.add_import_button.geometry().contains(event.pos()) and not self.remove_import_button.geometry().contains(event.pos()):
                    self.import_list.clearSelection()
          super().mousePressEvent(event)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    theme = load_theme()
    
    palette = QPalette()
    if 'palette' in theme:
        for role, color in theme['palette'].items():
            if hasattr(QPalette, role):
                palette.setColor(getattr(QPalette, role), QColor(color))
    app.setPalette(palette)

    base_dir = os.path.dirname(os.path.abspath(__file__))
    script_dir = os.path.dirname(base_dir)
    file_path = os.path.join(script_dir, "shell.nss")
    imports_path = os.path.join(script_dir, "imports")

    editor = ShellEditor(file_path, imports_path)
    editor.set_theme(theme)
    editor.show()
    sys.exit(app.exec_())
