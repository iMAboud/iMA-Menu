import sys
import os
import pyautogui
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QLineEdit, QCheckBox, QSlider, QComboBox, QColorDialog, QFileDialog,
    QTabWidget, QScrollArea, QFormLayout
)
from PyQt5.QtGui import QIcon, QColor
from PyQt5.QtCore import Qt, QTimer

ICON_PATH = r"C:\Program Files\Nilesoft Shell\icons\theme.ico"
THEME_PATH = r"c:\program files\Nilesoft Shell\imports\theme.nss"

def perform_ctrl_right_click(self):
    try:
        pyautogui.keyDown('ctrl')  
        pyautogui.click(button='right')  
        pyautogui.keyUp('ctrl')  
    except Exception as e:
        print(f"Failed to perform Ctrl+Right Click: {e}")
        
class ThemeEditor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.theme_data = {}
        self.initUI()
        self.load_theme()
        self.setWindowIcon(QIcon(ICON_PATH))

    def initUI(self):
        self.setWindowTitle('iMAboud - Theme Editor')
        self.setGeometry(100, 100, 900, 700)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.North)  
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: 0; }
            QTabBar::tab {
                background: #2b2b2b;
                color: #ffffff;
                border: 1px solid #1e1e1e;
                border-radius: 10px;
                padding: 10px;
                margin: 5px;
            }
            QTabBar::tab:selected {
                background: #3d3d3d;
            }
        """)
        main_layout.addWidget(self.tabs)

        button_layout = QHBoxLayout()
        self.save_button = QPushButton('Save Theme')
        self.save_button.setStyleSheet("""
            font-size: 16px;
            background-color: #4CAF50;
            color: white;
            border-radius: 10px;
            padding: 10px;
        """)
        self.save_button.clicked.connect(self.save_theme)
        button_layout.addWidget(self.save_button)

        self.import_button = QPushButton('Import Theme')
        self.import_button.setStyleSheet("""
            font-size: 16px;
            background-color: #f0ad4e;
            color: white;
            border-radius: 10px;
            padding: 10px;
        """)
        self.import_button.clicked.connect(self.import_theme)
        button_layout.addWidget(self.import_button)

        self.reset_button = QPushButton('Reset to Default')
        self.reset_button.setStyleSheet("""
            font-size: 16px;
            background-color: #d9534f;
            color: white;
            border-radius: 10px;
            padding: 10px;
        """)
        self.reset_button.clicked.connect(self.reset_to_default)
        button_layout.addWidget(self.reset_button)

        main_layout.addLayout(button_layout)


    def load_theme(self):
        if os.path.exists(THEME_PATH):
            try:
                with open(THEME_PATH, 'r') as file:
                    theme_content = file.read()
                    self.parse_theme(theme_content)
                    self.create_form()
            except Exception as e:
                print(f"Failed to load theme: {e}")

    def parse_theme(self, content):
        self.theme_data = {}
        lines = content.splitlines()
        current_section = None

        for line in lines:
            line = line.strip()
            if line.startswith('theme') or line.startswith('{') or line.startswith('}'):
                continue

            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip().strip('"')
                self.theme_data[key] = value

    def create_form(self):
        self.tabs.clear()

        icon_paths = {
            "General": r"C:\Program Files\Nilesoft Shell\script\theme-icons\general.ico",
            "Border": r"C:\Program Files\Nilesoft Shell\script\theme-icons\Border.ico",
            "Image": r"C:\Program Files\Nilesoft Shell\script\theme-icons\Image.ico",
            "Background": r"C:\Program Files\Nilesoft Shell\script\theme-icons\Background.ico",
            "Item": r"C:\Program Files\Nilesoft Shell\script\theme-icons\Item.ico",
            "Font": r"C:\Program Files\Nilesoft Shell\script\theme-icons\Font.ico",
            "Shadow": r"C:\Program Files\Nilesoft Shell\script\theme-icons\Shadow.ico",
            "Separator": r"C:\Program Files\Nilesoft Shell\script\theme-icons\Separator.ico",
            "Symbol": r"C:\Program Files\Nilesoft Shell\script\theme-icons\Symbol.ico",
        }
        
        slider_ranges = {
            "border.size": (0, 10),
            "item.opacity": (0, 100),
            "item.radius": (0, 4),
            "shadow.size": (0, 30),
            "shadow.opacity": (0, 100),
            "separator.size": (0, 40),
            "separator.opacity": (0, 100),
            "background.opacity": (0, 100),
            "font.size": (6, 100),
            "border.radius": (0, 4),
            "background.effect": (0, 3),
            "item.prefix": (0, 2),
            "font.weight": (1, 9),
        }

        categories = {
            "General": ["name", "view", "dark"],
            "Border": ["border.enabled", "border.size", "border.color", "border.opacity", "border.radius"],
            "Image": ["image.enabled", "image.align", "image.color", "image.scale"],
            "Background": ["background.color", "background.opacity", "background.effect"],
            "Item": [
                "item.opacity", "item.radius", "item.prefix", "item.text.normal",
                "item.text.select", "item.text.normal-disabled", "item.text.select-disabled",
                "item.back.select", "item.back.select-disabled", "item.border.normal",
                "item.border.normal.disabled", "item.border.select", "item.border.select.disabled"
            ],
            "Font": ["font.size", "font.name", "font.weight", "font.italic"],
            "Shadow": ["shadow.enabled", "shadow.size", "shadow.opacity", "shadow.color"],
            "Separator": ["separator.size", "separator.color", "separator.opacity"],
            "Symbol": [
                "symbol.normal", "symbol.select", "symbol.normal-disabled",
                "symbol.select-disabled"
            ]
        }

        display_names = {
            "name": "Theme",
            "view": "View Size",
            "dark": "Dark Mode",
            "border.enabled": "Enable Border",
            "border.size": "Border Size",
            "border.color": "Border Color",
            "border.opacity": "Border Opacity",
            "border.radius": "Border Radius",
            "image.enabled": "Enable Image",
            "image.align": "Image Alignment",
            "image.color": "Image Color",
            "image.scale": "Image Scale",
            "background.color": "Background Color",
            "background.opacity": "Background Opacity",
            "background.effect": "Background Effect : 0 = Disabled, 1 = Transparent, 2 = Blur, 3 = Acrylic",
            "item.opacity": "Item Opacity",
            "item.radius": "Item Radius",
            "item.prefix": "Item Prefix",
            "item.text.normal": "Normal Text",
            "item.text.select": "Selected Text",
            "item.text.normal-disabled": "Disabled Text",
            "item.text.select-disabled": "Disabled Selected Text",
            "item.back.select": "Selected Background",
            "item.back.select-disabled": "Disabled Background",
            "item.border.normal": "Border",
            "item.border.normal.disabled": "Disabled Border",
            "item.border.select": "Selected Border",
            "item.border.select.disabled": "Disabled Selected Broder",
            "font.size": "Font Size",
            "font.name": "Font Name",
            "font.weight": "Font Weight",
            "font.italic": "Italic",
            "shadow.enabled": "Enable Shadow",
            "shadow.size": "Shadow Size",
            "shadow.opacity": "Shadow Opacity",
            "shadow.color": "Shadow Color",
            "separator.size": "Separator Size",
            "separator.color": "Separator Color",
            "separator.opacity": "Separator Opacity",
            "symbol.normal": "Normal Symbol",
            "symbol.select": "Selected Symbol",
            "symbol.normal-disabled": "Disabled Symbol",
            "symbol.select-disabled": "Selected Disabled Symbol"
        }

        for category, keys in categories.items():
            tab = QWidget()
            scroll_area = QScrollArea()
            scroll_area.setWidgetResizable(True)
            tab_layout = QVBoxLayout(tab)
            form_layout = QFormLayout()
            form_layout.setVerticalSpacing(15)

            for key in keys:
                if key in self.theme_data:
                    value = self.theme_data[key]
                    display_name = display_names.get(key, key)
                    if value.lower() in ["true", "false"]:
                        self.add_checkbox(form_layout, display_name, key, value.lower() == "true")
                    elif value.startswith("#"):
                        self.add_color_picker(form_layout, display_name, key, value)
                    elif key == "background.color":
                        self.add_background_color_picker(form_layout, display_name, key, value)
                    elif value.isdigit():
                        min_val, max_val = slider_ranges.get(key, (0, 100))
                        self.add_slider(form_layout, display_name, key, int(value), min_val, max_val)
                    elif key in ["name", "view", "font.name"]:
                        self.add_dropdown(form_layout, display_name, key, value)
                    else:
                        self.add_text_input(form_layout, display_name, key, value)

            scroll_area.setLayout(form_layout)
            tab_layout.addWidget(scroll_area)
            self.tabs.addTab(tab, QIcon(icon_paths.get(category)), category) 

    def add_checkbox(self, layout, display_name, key, checked):
        checkbox = QCheckBox()
        checkbox.setChecked(checked)
        checkbox.stateChanged.connect(lambda state, k=key: self.update_theme_data(k, checkbox.isChecked()))
        layout.addRow(QLabel(display_name), checkbox)

    def add_color_picker(self, layout, display_name, key, value):
        hbox = QHBoxLayout()
        button = QPushButton()
        button.setStyleSheet(f"background-color: {value}; width: 50px; height: 25px;")
        button.clicked.connect(lambda: self.open_color_dialog(key, button))
        hbox.addWidget(button)
        line_edit = QLineEdit(value)
        line_edit.setFixedWidth(100)
        line_edit.textChanged.connect(lambda text, k=key: self.update_theme_data(k, text))
        hbox.addWidget(line_edit)
        layout.addRow(QLabel(display_name), hbox)

    def add_background_color_picker(self, layout, display_name, key, value):
        hbox = QHBoxLayout()
        button = QPushButton()
        button.setStyleSheet(f"background-color: {value if value != 'default' else '#FFFFFF'}; width: 50px; height: 25px;")
        button.clicked.connect(lambda: self.open_color_dialog(key, button))
        hbox.addWidget(button)
        line_edit = QLineEdit(value if value != 'default' else "")
        line_edit.setFixedWidth(100)
        line_edit.setEnabled(value != 'default')
        line_edit.textChanged.connect(lambda text, k=key: self.update_theme_data(k, text))
        hbox.addWidget(line_edit)
        default_checkbox = QCheckBox("Default")
        default_checkbox.setChecked(value == 'default')
        default_checkbox.stateChanged.connect(lambda state, le=line_edit, b=button: self.toggle_background_default(state, le, b))
        hbox.addWidget(default_checkbox)
        layout.addRow(QLabel(display_name), hbox)

    def open_color_dialog(self, key, button):
        color = QColorDialog.getColor()
        if color.isValid():
            hex_color = color.name()
            button.setStyleSheet(f"background-color: {hex_color}")
            self.theme_data[key] = hex_color

    def toggle_background_default(self, state, line_edit, button):
        if state == Qt.Checked:
            line_edit.setEnabled(False)
            line_edit.setText("")
            button.setStyleSheet("background-color: #FFFFFF")
            self.theme_data['background.color'] = 'default'
        else:
            line_edit.setEnabled(True)
            self.theme_data['background.color'] = line_edit.text()

    def add_slider(self, layout, display_name, key, value, min_val, max_val):
        hbox = QHBoxLayout()
        slider = QSlider(Qt.Horizontal)
        slider.setMinimum(min_val)
        slider.setMaximum(max_val)
        slider.setValue(value)
        label = QLabel(str(value))
        slider.valueChanged.connect(lambda val, k=key, l=label: self.update_slider_value(k, val, l))
        hbox.addWidget(slider)
        hbox.addWidget(label)
        layout.addRow(QLabel(display_name), hbox)

    def update_slider_value(self, key, value, label):
        label.setText(str(value))
        self.theme_data[key] = value

    def add_dropdown(self, layout, display_name, key, value):
        dropdown = QComboBox()
        options = []
        if key == "name":
            options = ["auto", "classic", "white", "black", "modern"]
        elif key == "view":
            options = ["auto", "compact", "small", "medium", "large", "wide"]
        elif key == "font.name":
            options = ["Segoe UI Variable Text", "Comic Sans MS", "Impact", "Arial", "Helvetica", "Times New Roman", "Courier New", 
                       "Calibri", "Cambria", "Garamond", "Georgia", "Tahoma", "Trebuchet MS", "Century Gothic", "Franklin Gothic Medium", "Consolas"]

        dropdown.addItems(options)
        dropdown.setCurrentText(value if key != "view" else value.split('.')[1])
        dropdown.currentTextChanged.connect(lambda text, k=key: self.update_theme_data(k, text if key != "view" else f"view.{text}"))
        layout.addRow(QLabel(display_name), dropdown)

    def add_text_input(self, layout, display_name, key, value):
        line_edit = QLineEdit(value)
        line_edit.textChanged.connect(lambda text, k=key: self.update_theme_data(k, text))
        layout.addRow(QLabel(display_name), line_edit)

    def update_theme_data(self, key, value):
        if isinstance(value, bool):
            self.theme_data[key] = "true" if value else "false"
        else:
            self.theme_data[key] = str(value)

    def save_theme(self):
        try:
            with open(THEME_PATH, 'w') as file:
                file.write("theme\n{\n")
                for key, value in self.theme_data.items():
                    if key in ["name", "font.name"]:
                        file.write(f"  {key} = \"{value}\"\n")
                    elif key == "view":
                        file.write(f"  view = {value}\n")
                    else:
                        file.write(f"  {key} = {value}\n")
                file.write("}\n")

            QTimer.singleShot(300, self.perform_ctrl_right_click)
        except Exception as e:
            print(f"Failed to save theme: {e}")

    def perform_ctrl_right_click(self):
        try:
            pyautogui.keyDown('ctrl')  
            pyautogui.click(button='right')  
            pyautogui.keyUp('ctrl')  
        except Exception as e:
            print(f"Failed to perform Ctrl+Right Click: {e}")

    def import_theme(self):
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(self, "Import Theme File", "", "All Files (*);;Text Files (*.nss)", options=options)
        if file_path:
            try:
                with open(file_path, 'r') as file:
                    theme_content = file.read()
                    self.parse_theme(theme_content)
                    self.create_form()
            except Exception as e:
                print(f"Failed to import theme: {e}")

    def reset_to_default(self):
        backup_path = os.path.join(os.path.dirname(THEME_PATH), 'theme_backup.nss')
        try:
            if os.path.exists(THEME_PATH):
                os.rename(THEME_PATH, backup_path)
            self.load_theme()
        except Exception as e:
            print(f"Failed to reset theme to default: {e}")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(ICON_PATH))
    editor = ThemeEditor()
    editor.show()
    sys.exit(app.exec_())
