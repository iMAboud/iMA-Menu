import sys
import os
import pyautogui
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QLineEdit, QCheckBox, QSlider, QComboBox, QColorDialog, QFileDialog,
    QScrollArea, QFrame, QSplitter, QStackedWidget, QGridLayout, QSpacerItem,
    QSizePolicy, QRadioButton, QButtonGroup
)
from PyQt5.QtGui import QIcon, QColor, QFont, QPixmap, QPainter, QPolygon
from PyQt5.QtCore import Qt, QTimer, QSize, pyqtSignal, QPoint
import shutil
import math

# --- Constants ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPT_DIR = os.path.dirname(BASE_DIR)
ICON_PATH = os.path.join(SCRIPT_DIR, "icons", "theme.ico")
THEME_PATH = os.path.join(SCRIPT_DIR, "imports", "theme.nss")
THEME_BACKUP_PATH = os.path.join(SCRIPT_DIR, "imports", "theme_backup.nss")

# --- Color Picker Button ---
class ColorPickerButton(QPushButton):
    colorChanged = pyqtSignal(str)

    def __init__(self, initial_color="#ffffff", parent=None):
        super().__init__(parent)
        self.setFixedSize(50, 50)
        self.setStyleSheet("border: 1px solid #444; border-radius: 25px;")
        self.label = QLabel(self)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setStyleSheet("background-color: transparent; color: #ddd;")
        self.layout = QVBoxLayout(self)
        self.layout.addWidget(self.label)
        self.hex_color = initial_color
        self.is_default = False  # Add an attribute to track if it's default
        self.set_color(initial_color) #ensure label is set on start
        self.clicked.connect(self._open_color_dialog)

    def set_color(self, hex_color):
        self.hex_color = hex_color
        self.setStyleSheet(f"background-color: {hex_color}; border: 1px solid #444; border-radius: 25px;")
        self.label.setStyleSheet("background-color: transparent; color: #ddd; border: none;") # Remove label border
        self.label.setText(hex_color if not self.is_default else "default") #update label
    def set_default(self, is_default):
        self.is_default = is_default
        self.set_color(self.hex_color)

    def _open_color_dialog(self):
        if self.is_default:
              self.set_default(False) # Remove default state
        color = QColorDialog.getColor(QColor(self.hex_color), self)
        if color.isValid():
            self.set_color(color.name())
            self.colorChanged.emit(self.hex_color)

# --- Main Theme Editor ---
class ThemeEditor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.theme_data = {}
        self.backup_theme_data = {}
        self.slider_ranges = {
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
             "item.prefix": (0, 2),
             "font.weight": (1, 9),
        }
        self.color_pickers = {} # Keep track of color pickers for default toggle
        self._setup_ui()
        self._load_theme()
        self.setWindowIcon(QIcon(ICON_PATH))
        self.is_closing = False

    def closeEvent(self, event):
         self.is_closing = True
         if self.theme_data != self.backup_theme_data:
            self._save_backup()
         event.accept()

    def _setup_ui(self):
        self.setWindowTitle('iMAboud - Theme Editor')
        self.setGeometry(100, 100, 900, 700)
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QGridLayout(central_widget)
        central_widget.setStyleSheet("background-color: #2b2b2b;")
        main_layout.setSpacing(15) # Spacing between frames

        # Create Frames
        self.dropdown_frame = QFrame(self)
        self.dropdown_frame.setStyleSheet("QFrame { border: 1px solid #444; border-radius: 5px;}")
        self.slider_frame = QFrame(self)
        self.slider_frame.setStyleSheet("QFrame { border: 1px solid #444; border-radius: 5px;}")
        self.checkbox_frame = QFrame(self)
        self.checkbox_frame.setStyleSheet("QFrame { border: 1px solid #444; border-radius: 5px;}")
        self.color_picker_frame = QFrame(self)
        self.color_picker_frame.setStyleSheet("QFrame { border: 1px solid #444; border-radius: 5px;}")
        self.additional_settings_frame = QFrame(self)
        self.additional_settings_frame.setStyleSheet("QFrame { border: 1px solid #444; border-radius: 5px;}")

        # Add Frames to Layout
        main_layout.addWidget(self.dropdown_frame, 0, 0, 1, 1)
        main_layout.addWidget(self.slider_frame, 0, 1, 1, 2)
        main_layout.addWidget(self.checkbox_frame, 1, 0, 1, 1)
        main_layout.addWidget(self.additional_settings_frame, 1, 1, 1, 2)
        main_layout.addWidget(self.color_picker_frame, 2, 0, 1, 3)
        # Create Layouts for Frames
        self.dropdown_layout = QVBoxLayout(self.dropdown_frame)
        self.dropdown_layout.setContentsMargins(10, 10, 10, 10)
        self.dropdown_layout.setSpacing(5)
        self.slider_layout = QGridLayout(self.slider_frame)
        self.slider_layout.setContentsMargins(10, 10, 10, 10)
        self.slider_layout.setSpacing(5)
        self.checkbox_layout = QVBoxLayout(self.checkbox_frame)
        self.checkbox_layout.setContentsMargins(10, 10, 10, 10)
        self.checkbox_layout.setSpacing(5)
        self.color_picker_layout = QGridLayout(self.color_picker_frame)
        self.color_picker_layout.setContentsMargins(10, 10, 10, 10)
        self.color_picker_layout.setSpacing(5)
        self.additional_settings_layout = QVBoxLayout(self.additional_settings_frame)
        self.additional_settings_layout.setContentsMargins(10, 10, 10, 10)
        self.additional_settings_layout.setSpacing(5)
        # Control Buttons
        button_layout = QHBoxLayout()
        self.save_button = QPushButton('Save Theme', self)
        self.save_button.clicked.connect(self._save_theme)
        self.import_button = QPushButton('Import Theme', self)
        self.import_button.clicked.connect(self._import_theme)
        self.reset_button = QPushButton('Reset to Default', self)
        self.reset_button.clicked.connect(self._reset_to_default)
        for btn in [self.save_button, self.import_button, self.reset_button]:
           btn.setStyleSheet("""QPushButton {
               font-size: 14px;
               color: white;
               background-color: #444;
               border-radius: 4px;
               padding: 10px;
               margin: 2px;
            }
           QPushButton:hover {
               background-color: #555;
            }""")
           button_layout.addWidget(btn)
        main_layout.addLayout(button_layout, 3, 0, 1, 3)

    def _load_theme(self):
        if os.path.exists(THEME_PATH):
            try:
                with open(THEME_PATH, 'r') as file:
                    theme_content = file.read()
                    self._parse_theme(theme_content)
                    self.backup_theme_data = self.theme_data.copy()
                    self._create_form()
            except Exception as e:
               print(f"Failed to load theme: {e}")
        else:
            self._create_form()

    def _parse_theme(self, content):
        self.theme_data = {}
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith('theme') or line.startswith('{') or line.startswith('}'):
                continue
            if '=' in line:
                key, value = line.split('=', 1)
                self.theme_data[key.strip()] = value.strip().strip('"')
    def _create_form(self):
        # Clear Existing Layouts
        while self.dropdown_layout.count():
           item = self.dropdown_layout.takeAt(0)
           widget = item.widget()
           if widget:
              widget.deleteLater()
        while self.slider_layout.count():
           item = self.slider_layout.takeAt(0)
           widget = item.widget()
           if widget:
              widget.deleteLater()
        while self.checkbox_layout.count():
           item = self.checkbox_layout.takeAt(0)
           widget = item.widget()
           if widget:
              widget.deleteLater()
        while self.color_picker_layout.count():
            item = self.color_picker_layout.takeAt(0)
            widget = item.widget()
            if widget:
                 widget.deleteLater()
        while self.additional_settings_layout.count():
           item = self.additional_settings_layout.takeAt(0)
           widget = item.widget()
           if widget:
              widget.deleteLater()

        categories = {
            "General": ["name", "view"],
            "Border": ["border.enabled", "border.size", "border.opacity", "border.radius"],
            "Background": ["background.opacity"],
             "Item": [
                "item.opacity", "item.radius", "item.prefix", "item.text.normal",
                "item.text.select", "item.text.normal-disabled",
                 "item.back.select",  "item.border.normal",
                "item.border.normal.disabled",  "item.border.select",
                "item.back.select-disabled",  "item.border.select.disabled", "item.text.select-disabled"
            ],
            "Font": ["font.size", "font.name", "font.weight", "font.italic"],
            "Shadow": ["shadow.enabled", "shadow.size", "shadow.opacity", "shadow.color"],
            "Separator": ["separator.size", "separator.color", "separator.opacity"],
            "Image": ["image.enabled", "image.color"],
             "Symbol": [
                 "symbol.normal", "symbol.select", "symbol.normal-disabled",
                "symbol.select-disabled"
            ]
        }
        display_names = {
            "name": "Theme",
            "view": "View Size",
            "border.enabled": "Enable Border",
            "border.size": "Border Size",
            "border.color": "Border Color",
            "border.opacity": "Border Opacity",
            "border.radius": "Border Radius",
            "image.enabled": "Enable Image",
            "image.color": "Image Color",
             "background.color": "Background Color",
            "background.opacity": "Background Opacity",
             "background.effect": "Background Effect",
            "item.radius": "Item Radius",
            "item.text.normal": "Normal Text",
            "item.text.select": "Selected Text",
            "item.back.select": "Selected Background",
            "item.border.normal": "Border",
            "item.border.select": "Selected Border",
            "item.border.normal.disabled": "Disabled Border",
            "item.border.select.disabled": "Selected Disabled Border",
            "item.text.normal-disabled": "Normal Disabled Text",
            "item.text.select-disabled": "Selected Disabled Text",
              "item.back.select-disabled": "Selected Disabled Background",
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
        slider_index = 0
        color_index = 0
        for category, keys in categories.items():
            for key in keys:
                if key in self.theme_data:
                    value = self.theme_data[key]
                    display_name = display_names.get(key, key)
                    if key == "item.opacity":
                       min_val, max_val = self.slider_ranges.get(key, (0, 100))
                       self._add_slider(self.slider_layout, display_name, key, int(value), min_val, max_val, math.floor(slider_index/2), slider_index%2)
                       slider_index+=1
                    elif key == "background.opacity":
                        min_val, max_val = self.slider_ranges.get(key, (0, 100))
                        self._add_slider(self.slider_layout, display_name, key, int(value), min_val, max_val, math.floor(slider_index/2), slider_index%2)
                        slider_index+=1
                    elif key == "border.opacity":
                        min_val, max_val = self.slider_ranges.get(key, (0, 100))
                        self._add_slider(self.slider_layout, display_name, key, int(value), min_val, max_val, math.floor(slider_index/2), slider_index%2)
                        slider_index+=1
                    elif key == "shadow.opacity":
                       min_val, max_val = self.slider_ranges.get(key, (0, 100))
                       self._add_slider(self.slider_layout, display_name, key, int(value), min_val, max_val, math.floor(slider_index/2), slider_index%2)
                       slider_index+=1
                    elif key == "separator.opacity":
                        min_val, max_val = self.slider_ranges.get(key, (0, 100))
                        self._add_slider(self.slider_layout, display_name, key, int(value), min_val, max_val, math.floor(slider_index/2), slider_index%2)
                        slider_index+=1
                    elif key == "border.size":
                        min_val, max_val = self.slider_ranges.get(key, (0, 10))
                        self._add_slider(self.slider_layout, display_name, key, int(value), min_val, max_val, math.floor(slider_index/2), slider_index%2)
                        slider_index+=1
                    elif key == "shadow.size":
                        min_val, max_val = self.slider_ranges.get(key, (0, 30))
                        self._add_slider(self.slider_layout, display_name, key, int(value), min_val, max_val, math.floor(slider_index/2), slider_index%2)
                        slider_index+=1
                    elif key == "separator.size":
                         min_val, max_val = self.slider_ranges.get(key, (0, 40))
                         self._add_slider(self.slider_layout, display_name, key, int(value), min_val, max_val, math.floor(slider_index/2), slider_index%2)
                         slider_index+=1
                    elif key == "border.radius":
                         min_val, max_val = self.slider_ranges.get(key, (0, 4))
                         self._add_slider(self.slider_layout, display_name, key, int(value), min_val, max_val, math.floor(slider_index/2), slider_index%2)
                         slider_index+=1
                    elif key == "item.radius":
                       min_val, max_val = self.slider_ranges.get(key, (0, 4))
                       self._add_slider(self.slider_layout, display_name, key, int(value), min_val, max_val, math.floor(slider_index/2), slider_index%2)
                       slider_index+=1
                    elif value.lower() in ["true", "false"] and key != "font.italic":
                       self._add_checkbox(self.checkbox_layout, display_name, key, value.lower() == "true")
                    elif value.startswith("#"):
                        self._add_color_picker(self.color_picker_layout, display_name, key, value, color_index)
                        color_index+=1
                    elif key == "font.italic":
                         self._add_checkbox(self.checkbox_layout, display_name, key, value.lower() == "true")
                    elif key in ["name", "view", "font.name"]:
                         self._add_dropdown(self.dropdown_layout, display_name, key, value)
                    elif key == "font.weight":
                        min_val, max_val = self.slider_ranges.get(key, (1, 9))
                        self._add_slider(self.additional_settings_layout, display_name, key, int(value), min_val, max_val,  math.floor(slider_index/2), slider_index%2)
                        slider_index += 1
                    else:
                        self._add_text_input(self.additional_settings_layout, display_name, key, value)
        if "Item" in categories:
          self._add_item_settings(main_layout, display_names)
        self._add_font_and_image_settings(main_layout, display_names) #Move font and image settings, background settings are added here.

    def _add_font_and_image_settings(self, layout, display_names):
       # Font Size Control
        font_size_key = "font.size"
        font_size_display_name = display_names.get(font_size_key, font_size_key)
        font_size_value = int(self.theme_data.get(font_size_key, "14"))  # Default font size to 14 if not found
        min_font_size, max_font_size = self.slider_ranges.get(font_size_key, (6, 100))  # Default to 6-100 if not found
        self._add_slider(self.additional_settings_layout, font_size_display_name, font_size_key, font_size_value, min_font_size, max_font_size, 0, 0)
        # Image Color Control
        image_color_key = "image.color"
        image_color_display_name = display_names.get(image_color_key, image_color_key)
        image_color_value = self.theme_data.get(image_color_key, "['#ffffff', '#ffffff']")
        self._add_image_color_picker(self.additional_settings_layout, image_color_display_name, image_color_key, image_color_value, 1) # Add to correct frame
        #Background color
        background_color_key = "background.color"
        background_color_display_name = display_names.get(background_color_key, "Background Color")
        background_color_value = self.theme_data.get(background_color_key, '#ffffff')
        self._add_background_color_picker(self.additional_settings_layout, background_color_display_name, background_color_key, background_color_value, 2)
        #Background Effect radio group
        background_effect_key = "background.effect"
        background_effect_display_name = display_names.get(background_effect_key, "Background Effect")
        background_effect_value = self.theme_data.get(background_effect_key, "disabled")
        self._add_radio_switcher(self.additional_settings_layout, background_effect_display_name, background_effect_key, background_effect_value, 3)

    def _add_item_settings(self, layout, display_names):
       text_keys = {
            "normal": "item.text.normal",
            "select": "item.text.select",
            "normal-disabled": "item.text.normal-disabled",
             "select-disabled": "item.text.select-disabled",
        }

       border_keys = {
            "normal": "item.border.normal",
            "select": "item.border.select",
            "normal-disabled": "item.border.normal.disabled",
             "select-disabled": "item.border.select.disabled",
        }

       back_keys = {
           "select":"item.back.select",
           "select-disabled": "item.back.select-disabled"
       }
       # Item color pickers
       color_index = 0
       for key, value in text_keys.items():
           self._add_color_picker(self.color_picker_layout, f"{display_names[value]}", value, self.theme_data.get(value, '#ffffff'), color_index)
           color_index+=1
       for key, value in back_keys.items():
           self._add_color_picker(self.color_picker_layout, f"{display_names[value]}", value, self.theme_data.get(value, '#444'), color_index)
           color_index += 1
       for key, value in border_keys.items():
          self._add_color_picker(self.color_picker_layout, f"{display_names[value]}", value, self.theme_data.get(value, '#444'), color_index)
          color_index+=1

    def _add_radio_switcher(self, layout, display_name, key, value, row=0):
        hbox = QHBoxLayout()
        hbox.addWidget(QLabel(display_name))
        radio_group = QButtonGroup()
        if key == "background.effect":
            options = ["disabled", "transparent", "blur", "acrylic"]
        else:
             options = ["auto", "display", "ignore"]
        for i, option in enumerate(options):
            radio_button = QRadioButton(option)
            radio_button.setChecked(value == str(i) or option == value)
            radio_button.setStyleSheet("""QRadioButton::indicator {
                width: 16px;
                height: 16px;
            }
            QRadioButton::indicator:checked {
                background-color: #55aaff;
                border: 1px solid #55aaff;
            }
            QRadioButton::indicator:unchecked {
                background-color: #333;
                border: 1px solid #555;
            }""")
            radio_group.addButton(radio_button)
            hbox.addWidget(radio_button)
            radio_button.toggled.connect(lambda checked, k=key, v=str(i), o=option: self._update_theme_data(k, v if k == "background.effect" else o) if checked else None )
        hbox.addStretch()
        layout.addLayout(hbox)
    def _add_checkbox(self, layout, display_name, key, checked):
        checkbox = QCheckBox()
        checkbox.setChecked(checked)
        checkbox.setStyleSheet("""QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
            QCheckBox::indicator:checked {
                background-color: #55aaff;
                border: 1px solid #55aaff;
            }
            QCheckBox::indicator:unchecked {
                background-color: #333;
                border: 1px solid #555;
            }""")
        checkbox.stateChanged.connect(lambda state, k=key: self._update_theme_data(k, checkbox.isChecked()))
        hbox = QHBoxLayout()
        hbox.addWidget(QLabel(display_name))
        hbox.addStretch(1)
        hbox.addWidget(checkbox)
        layout.addLayout(hbox)

    def _add_color_picker(self, layout, display_name, key, value, row):
           color_button = ColorPickerButton(value)
           self.color_pickers[key] = color_button
           color_button.colorChanged.connect(lambda color, k=key: self._update_theme_data(k, color))
           hbox = QVBoxLayout()
           hbox.setSpacing(0)  # Remove spacing within the vertical layout
           hbox.addWidget(color_button)
           label = QLabel(display_name)
           label.setStyleSheet("text-align: center; margin-bottom: 0;") # reduce space below
           label.mousePressEvent = lambda event, k=key: self._toggle_color_default(k) #add mouse press event to label
           hbox.addWidget(label, alignment=Qt.AlignCenter)
           layout.addLayout(hbox, math.floor(row/5), row%5) # Modified for 5x3

    def _toggle_color_default(self, key):
         color_button = self.color_pickers.get(key)
         if color_button:
               if not color_button.is_default:
                   color_button.set_default(True) # Set as default
                   self.theme_data[key] = 'default'
               else:
                 color_button.set_default(False) # remove default
                 self.theme_data[key] = color_button.hex_color # set back to the last used hex
                 color_button.set_color(color_button.hex_color)

    def _add_image_color_picker(self, layout, display_name, key, value, row):
           try:
             value = eval(value)
           except:
               value = ["#ffffff", "#ffffff"]
           hbox = QHBoxLayout()
           vbox1 = QVBoxLayout()
           vbox2 = QVBoxLayout()
           color_button_1 = ColorPickerButton(value[0] if isinstance(value, list) and len(value) > 0 else "#ffffff")
           color_button_1.colorChanged.connect(lambda color, k=key: self._update_image_color(k, color, 0))
           vbox1.addWidget(color_button_1)
           label = QLabel(display_name + " 1")
           label.setStyleSheet("text-align: center;")
           vbox1.addWidget(label, alignment=Qt.AlignCenter)
           color_button_2 = ColorPickerButton(value[1] if isinstance(value, list) and len(value) > 1 else "#ffffff")
           color_button_2.colorChanged.connect(lambda color, k=key: self._update_image_color(k, color, 1))
           vbox2.addWidget(color_button_2)
           label2 = QLabel(display_name + " 2")
           label2.setStyleSheet("text-align: center;")
           vbox2.addWidget(label2, alignment=Qt.AlignCenter)
           hbox.addLayout(vbox1)
           hbox.addLayout(vbox2)
           layout.addLayout(hbox, math.floor(row/2), row%2)
    def _update_image_color(self, key, color, index):
        try:
            value = eval(self.theme_data.get(key, "['#ffffff', '#ffffff']"))
            if isinstance(value, list) and len(value) > index:
                value[index] = color
                self.theme_data[key] = str(value)
        except:
             self.theme_data[key] = "['#ffffff', '#ffffff']"

    def _add_color_picker_no_label(self, initial_color, color_changed_func):
        color_button = ColorPickerButton(initial_color)
        color_button.colorChanged.connect(color_changed_func)
        return color_button

    def _add_background_color_picker(self, layout, display_name, key, value, row):
        hbox = QHBoxLayout()
        radio_group = QButtonGroup()
        default_radio = QRadioButton("Default")
        default_radio.setChecked(value == 'default')
        default_radio.toggled.connect(lambda checked, k=key: self._toggle_background_default(checked, color_button) )
        hbox.addWidget(default_radio)
        radio_group.addButton(default_radio)
        color_button = ColorPickerButton(value if value != 'default' else "#ffffff")
        color_button.setEnabled(value != 'default')
        color_button.colorChanged.connect(lambda color, k=key: self._update_background_color(color, k))
        hbox.addWidget(color_button)
        custom_radio = QRadioButton("Custom")
        custom_radio.setChecked(value != 'default')
        hbox.addWidget(custom_radio)
        radio_group.addButton(custom_radio)
        custom_radio.toggled.connect(lambda checked, k=key, cb=color_button, v=value: self._toggle_background_color(checked, cb, v) )
        hbox.addStretch()
        hbox2 = QVBoxLayout()
        hbox2.addWidget(QLabel(display_name))
        hbox2.addLayout(hbox)
        layout.addLayout(hbox2, math.floor(row/2), row%2)
    def _toggle_background_color(self, state, color_button, value):
        color_button.setEnabled(state)
        if not state:
           self.theme_data['background.color'] = "default"
           color_button.set_color("#ffffff")
        else:
            self.theme_data["background.color"] = value if value != "default" else "#ffffff"
            color_button.set_color(value if value != "default" else "#ffffff")

    def _update_background_color(self, color, key):
            self.theme_data[key] = color

    def _toggle_background_default(self, state, color_button):
         if state:
               color_button.setEnabled(False)
               color_button.set_color("#ffffff")
               self.theme_data['background.color'] = 'default'
         else:
             color_button.setEnabled(True)
    def _add_slider(self, layout, display_name, key, value, min_val, max_val, row, column):
        hbox = QHBoxLayout()
        label = QLabel(display_name)
        hbox.addWidget(label)
        slider = QSlider(Qt.Horizontal)
        slider.setMinimum(min_val)
        slider.setMaximum(max_val)
        slider.setValue(value)
        slider.setStyleSheet("""QSlider::groove:horizontal {border: 1px solid #444;height: 4px;background: #444;}
            QSlider::handle:horizontal {background: #55aaff;border: 1px solid #55aaff;width: 12px;margin: -4px 0;border-radius: 5px;}
            QSlider::sub-page:horizontal {background: #55aaff;}""")
        label_val = QLabel(str(value))
        label_val.setFixedWidth(25)
        slider.valueChanged.connect(lambda val, k=key, l=label_val: self._update_slider_value(k, val, l))
        hbox.addWidget(slider)
        hbox.addWidget(label_val)
        layout.addLayout(hbox, row, column)
    def _update_slider_value(self, key, value, label):
        label.setText(str(value))
        self.theme_data[key] = value

    def _add_dropdown(self, layout, display_name, key, value):
        hbox = QHBoxLayout()
        label = QLabel(display_name)
        hbox.addWidget(label)
        dropdown = QComboBox()
        options = []
        if key == "name":
            options = ["auto", "classic", "white", "black", "modern"]
        elif key == "view":
            options = ["auto", "compact", "small", "medium", "large", "wide"]
        elif key == "font.name":
            options = ["Segoe UI Variable Text", "Comic Sans MS", "Impact", "Arial", "Helvetica", "Times  New Roman", "Courier New",
                       "Calibri", "Cambria", "Garamond", "Georgia", "Tahoma", "Trebuchet MS", "Century Gothic", "Franklin Gothic Medium", "Consolas"]

        dropdown.addItems(options)
        dropdown.setStyleSheet("""QComboBox {
                    border: 1px solid #444;
                    border-radius: 3px;
                    padding: 4px;
                    font-size: 14px;
                    background: #333;
                    color: white;
                }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 20px;
                border-left: 1px solid #444;
            }
            QComboBox::down-arrow {
                image: url(none);
            }
            QComboBox QAbstractItemView {
                border: 1px solid #444;
                background: #333;
            }
            QComboBox QAbstractItemView::item {
                color: #ddd;
            }
            QComboBox QAbstractItemView::item:selected {
                background: #555;
            }""")
        dropdown.setFixedSize(180, 28)
        dropdown.setCurrentText(value if key != "view" else value.split('.')[1])
        dropdown.currentTextChanged.connect(lambda text, k=key: self._update_theme_data(k, text if key != "view" else f"view.{text}"))
        hbox.addWidget(dropdown)
        hbox.addStretch(1)
        layout.addLayout(hbox)

    def _add_text_input(self, layout, display_name, key, value):
           hbox = QHBoxLayout()
           label = QLabel(display_name)
           hbox.addWidget(label)
           line_edit = QLineEdit(value)
           line_edit.setStyleSheet("""QLineEdit {
                    border: 1px solid #444;
                    border-radius: 3px;
                    padding: 4px;
                    font-size: 14px;
                    background: #333;
                    color: white;
               }
            QLineEdit:focus {
                border: 1px solid #55aaff;
            }""")
           line_edit.setFixedSize(180, 28)
           line_edit.textChanged.connect(lambda text, k=key: self._update_theme_data(k, text))
           hbox.addWidget(line_edit)
           hbox.addStretch(1)
           layout.addLayout(hbox)

    def _update_theme_data(self, key, value):
            if isinstance(value, bool):
                self.theme_data[key] = "true" if value else "false"
            else:
                self.theme_data[key] = str(value)

    def _save_theme(self):
        try:
            with open(THEME_PATH, 'w') as file:
                file.write("theme\n{\n")
                for key, value in self.theme_data.items():
                    if key in ["name", "font.name"]:
                        file.write(f"  {key} = \"{value}\"\n")
                    else:
                        file.write(f"  {key} = {value}\n")
                file.write("}\n")
            QTimer.singleShot(300, self._perform_ctrl_right_click)
        except Exception as e:
            print(f"Error in save_theme: {e}")
    def _save_backup(self):
        try:
             shutil.copyfile(THEME_PATH, THEME_BACKUP_PATH)
        except Exception as e:
              print(f"Failed to save backup theme: {e}")


    def _perform_ctrl_right_click(self):
        try:
            pyautogui.keyDown('ctrl')
            pyautogui.click(button='right')
            pyautogui.keyUp('ctrl')
        except Exception as e:
           print(f"Error in perform_ctrl_right_click: {e}")
    def _import_theme(self):
            options = QFileDialog.Options()
            file_path, _ = QFileDialog.getOpenFileName(self, "Import Theme File", "", "All Files (*);;Text Files (*.nss)", options=options)
            if file_path:
                try:
                    with open(file_path, 'r') as file:
                        theme_content = file.read()
                        self._parse_theme(theme_content)
                        self.backup_theme_data = self.theme_data.copy()
                        self._create_form()
                except Exception as e:
                    print(f"Error in import_theme: {e}")
    def _reset_to_default(self):
        if os.path.exists(THEME_BACKUP_PATH):
            try:
                with open(THEME_BACKUP_PATH, 'r') as file:
                    theme_content = file.read()
                    self._parse_theme(theme_content)
                    self._create_form()
            except Exception as e:
                print(f"Error in reset to default from backup: {e}")
        else:
            self.theme_data = {}
            self._load_theme()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(ICON_PATH))
    app.setStyleSheet("""
        QMainWindow {
            background-color: #222;
        }
        QLabel {
            color: #ddd;
            font-size: 14px;
            margin-right: 8px;
        }
        QLabel#SectionTitle {
            font-size: 16px;
            font-weight: bold;
            color: #ddd;
            margin-bottom: 10px;
            text-align: center;
        }
       QScrollBar:vertical {
            border: none;
            background: #333;
            width: 10px;
        }
        QScrollBar::handle:vertical {
            background: #555;
            min-height: 16px;
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            border: none;
            background: none;
        }
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
            background: none;
        }
    """)
    editor = ThemeEditor()
    editor.show()
    sys.exit(app.exec_())
