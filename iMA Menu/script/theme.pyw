import sys
import os
import shutil
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QLineEdit, QCheckBox, QSlider, QComboBox, QColorDialog, QGridLayout,
    QFrame, QButtonGroup, QRadioButton, QTabWidget, QScrollArea
)
from PyQt5.QtGui import QIcon, QColor
from PyQt5.QtCore import Qt, pyqtSignal

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
        self.setFixedSize(64, 64)  # Increased Size
        self.setStyleSheet("border: 1px solid #268a86; border-radius: 16px; background-color: " + initial_color)
        self.hex_color = initial_color
        self.clicked.connect(self._open_color_dialog)

    def set_color(self, hex_color):
        self.hex_color = hex_color
        self.setStyleSheet(f"background-color: {hex_color}; border: 1px solid #268a86; border-radius: 16px;")

    def _open_color_dialog(self):
        color = QColorDialog.getColor(QColor(self.hex_color), self)
        if color.isValid():
            self.set_color(color.name())
            self.colorChanged.emit(self.hex_color)

# --- Main Theme Editor ---
class ThemeEditor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.theme_data = {
             "name": "modern",
              "view": "view.medium",
              "border.enabled": "true",
              "border.size": "5",
             "border.color": "default",
              "border.opacity": "38",
              "border.radius": "0",
             "image.enabled": "true",
            "image.color": "['#888888', '#888888']",
             "background.color": "default",
             "background.opacity": "0",
             "background.effect": "3",
              "item.radius": "2",
              "item.text.normal": "#888888",
             "item.text.select": "#888888",
              "item.text.normal-disabled": "#888888",
              "item.back.select": "#888888",
              "item.border.normal": "#228844",
              "item.border.select": "#888888",
              "font.size": "auto",
              "font.name": "Segoe UI Variable Text",
             "font.weight": "true",
            "font.italic": "true",
             "shadow.enabled": "true",
              "shadow.size": "8",
             "shadow.opacity": "7",
            "shadow.color": "#888888",
             "separator.size": "0",
              "separator.color": "#888888",
              "separator.opacity": "0",
             "symbol.normal": "#888888",
             "symbol.select": "#888888"
          }
        self.backup_theme_data = self.theme_data.copy()
        self.slider_ranges = {
            "border.size": (0, 10), "item.opacity": (0, 100), "item.radius": (0, 4),
            "shadow.size": (0, 30), "shadow.opacity": (0, 100), "separator.size": (0, 40),
            "separator.opacity": (0, 100), "background.opacity": (0, 100), "font.size": (6, 100),
            "border.radius": (0, 4), "item.prefix": (0, 2), "font.weight": (1, 9)
        }
        self.color_pickers = {}
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
        central_widget.setStyleSheet("background-color: #222; color: #fff;")
        main_layout.setSpacing(8)
         # Create Frames with Teal Borders
        self.general_frame = self._create_frame()
        self.border_frame = self._create_frame()
        self.background_frame = self._create_frame()
        self.item_text_frame = self._create_frame()
        self.image_symbol_frame = self._create_frame()
        self.shadow_separator_frame = self._create_frame()

         # Add Frames to Layout
        main_layout.addWidget(self.general_frame, 0, 0)
        main_layout.addWidget(self.border_frame, 0, 1)
        main_layout.addWidget(self.background_frame, 0, 2)
        main_layout.addWidget(self.item_text_frame, 1, 0)
        main_layout.addWidget(self.image_symbol_frame, 1, 1)
        main_layout.addWidget(self.shadow_separator_frame, 1, 2)

         # Create Layouts for Frames
        self.general_layout = QVBoxLayout(self.general_frame)
        self.border_layout = QVBoxLayout(self.border_frame)
        self.background_layout = QVBoxLayout(self.background_frame)
        self.item_text_layout = QVBoxLayout(self.item_text_frame)
        self.image_symbol_layout = QVBoxLayout(self.image_symbol_frame)
        self.shadow_separator_layout = QVBoxLayout(self.shadow_separator_frame)

        # Create a tab widget for Frame 4
        self.item_text_tab_widget = QTabWidget()
        self.item_text_tab_widget.setStyleSheet("QTabWidget::pane {border: none;}") #Removed Tab Border
        self.item_text_layout.addWidget(self.item_text_tab_widget)
        
        # Create the Item Text Tab
        self.item_text_tab = QWidget()
        self.item_text_tab_layout = QVBoxLayout(self.item_text_tab)
        self.item_text_tab_widget.addTab(self.item_text_tab, "Text")

        # Create the Font Tab
        self.font_tab = QWidget()
        self.font_tab_layout = QVBoxLayout(self.font_tab)
        self.item_text_tab_widget.addTab(self.font_tab, "Font")


        for layout in [self.general_layout, self.border_layout, self.background_layout, self.item_text_tab_layout,
                      self.image_symbol_layout, self.shadow_separator_layout, self.font_tab_layout]:
           layout.setContentsMargins(8, 8, 8, 8)
           layout.setSpacing(5)

    def _create_frame(self):
        frame = QFrame(self)
        frame.setStyleSheet("QFrame { border: 1px solid #268a86; border-radius: 22px;}")
        return frame

    def save_data(self):
        return {"theme_data": self.theme_data}

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

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def _create_form(self):
         # Clear Existing Layouts
        self._clear_layout(self.general_layout)
        self._clear_layout(self.border_layout)
        self._clear_layout(self.background_layout)
        self._clear_layout(self.item_text_tab_layout)
        self._clear_layout(self.image_symbol_layout)
        self._clear_layout(self.shadow_separator_layout)
        self._clear_layout(self.font_tab_layout)

        # --- FRAME 1: General ---
        self._add_setting_with_label(self.general_layout, "name")
        self._add_setting_with_label(self.general_layout, "view")
        self._add_setting_with_label(self.general_layout, "item.radius")
        self._add_setting_with_label(self.general_layout, "border.radius")

        # --- FRAME 2: Border ---
        self._add_setting_with_label(self.border_layout, "border.enabled")
        self._add_setting_with_label(self.border_layout, "border.size")
        self._add_setting_with_label(self.border_layout, "border.color")
        self._add_setting_with_label(self.border_layout, "border.opacity")
        self._add_setting_with_label(self.border_layout, "item.border.normal")
        self._add_setting_with_label(self.border_layout, "item.border.select")

        # --- FRAME 3: Background ---
        self._add_setting_with_label(self.background_layout, "background.color")
        self._add_setting_with_label(self.background_layout, "background.effect")
        self._add_setting_with_label(self.background_layout, "background.opacity")

       # --- FRAME 4: Item Text and Back - Now using the first tab
        self._add_setting_with_label(self.item_text_tab_layout, "item.text.normal")
        self._add_setting_with_label(self.item_text_tab_layout, "item.text.select")
        self._add_setting_with_label(self.item_text_tab_layout, "item.text.normal-disabled")
        self._add_setting_with_label(self.item_text_tab_layout, "item.back.select")

       # --- FRAME 5: Image and Symbols ---
        self._add_setting_with_label(self.image_symbol_layout, "image.enabled")
        self._add_setting_with_label(self.image_symbol_layout, "image.color", is_image=True)
        self._add_setting_with_label(self.image_symbol_layout, "symbol.normal")

        # --- FRAME 6: Shadow and Separator ---
        self._add_setting_with_label(self.shadow_separator_layout, "shadow.enabled")
        self._add_setting_with_label(self.shadow_separator_layout, "shadow.size")
        self._add_setting_with_label(self.shadow_separator_layout, "shadow.opacity")
        self._add_setting_with_label(self.shadow_separator_layout, "shadow.color")
        self._add_setting_with_label(self.shadow_separator_layout, "separator.size")
        self._add_setting_with_label(self.shadow_separator_layout, "separator.color")
        self._add_setting_with_label(self.shadow_separator_layout, "separator.opacity")

        # --- FRAME 7: Font - Moved to the new tab inside frame 4 ---
        self._add_setting_with_label(self.font_tab_layout, "font.size")
        self._add_setting_with_label(self.font_tab_layout, "font.weight")
        self._add_setting_with_label(self.font_tab_layout, "font.italic")
        self._add_setting_with_label(self.font_tab_layout, "font.name")

    def _add_setting_with_label(self, layout, key, is_image = False):
        display_names = {
            "name": "Theme", "border.enabled": "Enable Border",
            "border.size": "Border Size", "border.color": "Border Color",
            "border.opacity": "Border Opacity", "border.radius": "Border Radius",
            "image.enabled": "Enable Image", "image.color": "Image Color",
            "background.color": "Background Color",
            "background.opacity": "Background Opacity", "background.effect": "Background Effect",
            "item.radius": "Item Radius", "item.text.normal": "Normal Text",
            "item.text.select": "Selected Text", "item.back.select": "Selected Background",
            "item.border.normal": "Item Border", "item.border.select": "Selected Border",
            "item.text.normal-disabled": "Normal Disabled Text",
             "item.back.select-disabled": "Selected Disabled Background", "font.size": "Font Size",
            "font.name": "Font Name", "font.weight": "Font Weight", "font.italic": "Italic",
            "shadow.enabled": "Enable Shadow", "shadow.size": "Shadow Size",
            "shadow.opacity": "Shadow Opacity", "shadow.color": "Shadow Color",
            "separator.size": "Separator Size", "separator.color": "Separator Color",
            "separator.opacity": "Separator Opacity",  "symbol.normal": "Normal Symbol"
        }
        display_name = display_names.get(key, key)
        if key in self.theme_data:
            value = self.theme_data[key]

            if key in ["item.opacity", "background.opacity", "border.opacity",
                           "shadow.opacity", "separator.opacity", "border.size",
                           "shadow.size", "separator.size", "border.radius", "item.radius"]:
                min_val, max_val = self.slider_ranges.get(key, (0, 100))
                if key in ["border.size", "shadow.size", "separator.size", "border.radius", "item.radius"]:
                    min_val, max_val = self.slider_ranges.get(key, (0, 10))
                self._add_slider(layout, display_name, key, int(value), min_val, max_val)
            elif value.lower() in ["true", "false"] and key != "font.italic":
                self._add_checkbox(layout, display_name, key, value.lower() == "true")
            elif value.startswith("#") or value == "default" and not is_image:
                self._add_color_picker(layout, display_name, key, value)
            elif key == "font.italic":
               self._add_checkbox(layout, display_name, key, value.lower() == "true")
            elif key in ["name","font.name", "view"]:
                self._add_dropdown(layout, display_name, key, value)
            elif key == "font.weight":
                min_val, max_val = self.slider_ranges.get(key, (1, 9))
                self._add_slider(layout, display_name, key, int(value), min_val, max_val)
            elif is_image and key == "image.color":
                self._add_image_color_picker(layout, display_name, key, value)
            elif key == "background.color":
                 self._add_background_color_picker(layout, display_name, key, value)
            elif key == "background.effect":
                self._add_radio_switcher(layout, display_name, key, value)

            else:
               self._add_text_input(layout, display_name, key, value)

    def _add_radio_switcher(self, layout, display_name, key, value):
        hbox = QHBoxLayout()
        radio_group = QButtonGroup()
        if key == "background.effect":
            options = ["disabled", "transparent", "blur", "acrylic"]
        else:
             options = ["auto", "display", "ignore"]
        for i, option in enumerate(options):
            radio_button = QRadioButton(option)
            radio_button.setChecked(value == str(i) or option == value)
            radio_button.setStyleSheet("""QRadioButton::indicator {
                width: 14px;
                height: 14px;
                border-radius: 7px;
            }
            QRadioButton::indicator:checked {
                background-color: #268a86;
                border: 1px solid #268a86;
            }
            QRadioButton::indicator:unchecked {
                background-color: #333;
                border: 1px solid #555;
            }
            QRadioButton {color: #fff;}""")
            radio_group.addButton(radio_button)
            hbox.addWidget(radio_button)
            radio_button.toggled.connect(lambda checked, k=key, v=str(i), o=option: self._update_theme_data(k, v if k == "background.effect" else o) if checked else None )
        hbox.addStretch()
        layout.addLayout(hbox)

    def _add_checkbox(self, layout, display_name, key, checked):
        checkbox = QCheckBox()
        checkbox.setChecked(checked)
        checkbox.setStyleSheet("""QCheckBox::indicator {
                width: 14px;
                height: 14px;
                border-radius: 7px;
            }
            QCheckBox::indicator:checked {
                background-color: #268a86;
                border: 1px solid #268a86;
            }
            QCheckBox::indicator:unchecked {
                background-color: #333;
                border: 1px solid #555;
            }
             QCheckBox { color: #fff; }
            """)
        checkbox.stateChanged.connect(lambda state, k=key, chk=checkbox: self._update_theme_data(k, chk.isChecked()))
        hbox = QHBoxLayout()
        hbox.addWidget(checkbox)  # Checkbox left of the text
        label = QLabel(display_name)
        label.setStyleSheet("background-color: transparent; border: none;")
        hbox.addWidget(label)
        hbox.addStretch(1)
        layout.addLayout(hbox)

    def _add_color_picker(self, layout, display_name, key, value):
         hbox = QHBoxLayout()
         checkbox = QCheckBox()
         checkbox.setChecked(value != 'default')
         checkbox.setStyleSheet("""QCheckBox::indicator {
                 width: 14px;
                 height: 14px;
                 border-radius: 7px;
             }
             QCheckBox::indicator:checked {
                 background-color: #268a86;
                 border: 1px solid #268a86;
             }
             QCheckBox::indicator:unchecked {
                 background-color: #333;
                 border: 1px solid #555;
             }
              QCheckBox { color: #fff; }
             """)
         color_button = ColorPickerButton(value if value != 'default' else "#ffffff")
         color_button.setEnabled(value != 'default')
         checkbox.stateChanged.connect(lambda state, k=key, cb=color_button: self._toggle_color_default(k, cb, state) )
         color_button.colorChanged.connect(lambda color, k=key: self._update_theme_data(k, color))
         hbox.addWidget(checkbox)
         label = QLabel(display_name)
         label.setStyleSheet("background-color: transparent; border: none;")
         hbox.addWidget(label)
         hbox.addStretch()
         hbox.addWidget(color_button)
         layout.addLayout(hbox)

    def _toggle_color_default(self, key, color_button, state):
       color_button.setEnabled(state)
       if not state:
          self.theme_data[key] = "default"
          color_button.set_color("#ffffff")
       else:
            self.theme_data[key] = color_button.hex_color

    def _add_image_color_picker(self, layout, display_name, key, value):
        try:
            value = eval(value)
        except:
            value = ["#ffffff", "#ffffff"]
        hbox = QHBoxLayout()
        vbox1 = QVBoxLayout()
        vbox2 = QVBoxLayout()
        color_button_1 = ColorPickerButton(value[0] if isinstance(value, list) and len(value) > 0 else "#ffffff")
        checkbox_1 = QCheckBox()
        checkbox_1.setStyleSheet("""QCheckBox::indicator {
                width: 14px;
                height: 14px;
                border-radius: 7px;
            }
            QCheckBox::indicator:checked {
                background-color: #268a86;
                border: 1px solid #268a86;
            }
            QCheckBox::indicator:unchecked {
                background-color: #333;
                border: 1px solid #555;
            }
            QCheckBox { color: #fff; }
            """)
        checkbox_1.setChecked(value[0] != 'default' if isinstance(value, list) else True)
        color_button_1.setEnabled(value[0] != 'default' if isinstance(value, list) else True)
        checkbox_1.stateChanged.connect(lambda state, k=key, cb=color_button_1: self._toggle_image_color(k, cb, state, 0) )
        color_button_1.colorChanged.connect(lambda color, k=key: self._update_image_color(k, color, 0))
        vbox1.addWidget(checkbox_1)
        vbox1.addWidget(color_button_1)

        label = QLabel(display_name + " 1")
        label.setStyleSheet("text-align: center; color:#fff; background-color: transparent; border: none;")
        vbox1.addWidget(label, alignment=Qt.AlignCenter)
        color_button_2 = ColorPickerButton(value[1] if isinstance(value, list) and len(value) > 1 else "#ffffff")
        checkbox_2 = QCheckBox()
        checkbox_2.setStyleSheet("""QCheckBox::indicator {
                width: 14px;
                height: 14px;
                 border-radius: 7px;
            }
            QCheckBox::indicator:checked {
                background-color: #268a86;
                border: 1px solid #268a86;
            }
            QCheckBox::indicator:unchecked {
                background-color: #333;
                border: 1px solid #555;
            }
             QCheckBox { color: #fff; }
            """)
        checkbox_2.setChecked(value[1] != 'default' if isinstance(value, list) and len(value) > 1 else True)
        color_button_2.setEnabled(value[1] != 'default' if isinstance(value, list) and len(value) > 1 else True)
        checkbox_2.stateChanged.connect(lambda state, k=key, cb=color_button_2: self._toggle_image_color(k, cb, state, 1))
        color_button_2.colorChanged.connect(lambda color, k=key: self._update_image_color(k, color, 1))
        vbox2.addWidget(checkbox_2)
        vbox2.addWidget(color_button_2)
        label2 = QLabel(display_name + " 2")
        label2.setStyleSheet("text-align: center; color:#fff; background-color: transparent; border: none;")
        vbox2.addWidget(label2, alignment=Qt.AlignCenter)
        hbox.addLayout(vbox1)
        hbox.addLayout(vbox2)
        layout.addLayout(hbox)

    def _toggle_image_color(self, key, color_button, state, index):
        try:
            value = eval(self.theme_data.get(key, "['#ffffff', '#ffffff']"))
            if isinstance(value, list) and len(value) > index:
                color_button.setEnabled(state)
                if not state:
                    value[index] = 'default'
                    color_button.set_color("#ffffff")
                else:
                    value[index] = color_button.hex_color
                self.theme_data[key] = str(value)
        except:
             self.theme_data[key] = "['#ffffff', '#ffffff']"

    def _update_image_color(self, key, color, index):
        try:
            value = eval(self.theme_data.get(key, "['#ffffff', '#ffffff']"))
            if isinstance(value, list) and len(value) > index:
                value[index] = color
                self.theme_data[key] = str(value)
        except:
             self.theme_data[key] = "['#ffffff', '#ffffff']"

    def _add_background_color_picker(self, layout, display_name, key, value):
        hbox = QHBoxLayout()
        radio_group = QButtonGroup()
        default_radio = QRadioButton("Default")
        default_radio.setChecked(value == 'default')
        default_radio.setStyleSheet("color: #fff;")
        default_radio.toggled.connect(lambda checked, k=key: self._toggle_background_default(checked, color_button) )
        hbox.addWidget(default_radio)
        radio_group.addButton(default_radio)
        color_button = ColorPickerButton(value if value != 'default' else "#ffffff")
        color_button.setEnabled(value != 'default')
        color_button.colorChanged.connect(lambda color, k=key: self._update_background_color(color, k))
        hbox.addWidget(color_button)
        custom_radio = QRadioButton("Custom")
        custom_radio.setChecked(value != 'default')
        custom_radio.setStyleSheet("color: #fff;")
        hbox.addWidget(custom_radio)
        radio_group.addButton(custom_radio)
        custom_radio.toggled.connect(lambda checked, k=key, cb=color_button, v=value: self._toggle_background_color(checked, cb, v) )
        hbox.addStretch()
        hbox2 = QVBoxLayout()
        label = QLabel(display_name)
        label.setStyleSheet("background-color: transparent; border: none;")
        hbox2.addWidget(label)
        hbox2.addLayout(hbox)
        layout.addLayout(hbox2)

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

    def _add_slider(self, layout, display_name, key, value, min_val, max_val):
        hbox = QHBoxLayout()
        label = QLabel(display_name)
        label.setStyleSheet("background-color: transparent; border: none;")
        hbox.addWidget(label)
        slider = QSlider(Qt.Horizontal)
        slider.setMinimum(min_val)
        slider.setMaximum(max_val)
        slider.setValue(value)
        slider.setStyleSheet("""
        QSlider::groove:horizontal {
            border: 1px solid #268a86;
            height: 4px;
            background: #333;
            border-radius: 2px;
        }
        QSlider::handle:horizontal {
            background: #268a86;
            border: 1px solid #268a86;
            width: 12px; /* Increased handle size */
            height: 12px;
            margin: -5px 0;
            border-radius: 6px; /* Circular handle */
        }
        QSlider::add-page:horizontal {
            background: #268a86;
            border-radius: 2px;
        }
        QSlider::sub-page:horizontal {
            background: #333;
             border-radius: 2px;
        }
    """)

        label_val = QLabel(str(value))
        label_val.setFixedWidth(25)
        label_val.setStyleSheet("color: #fff; background-color: transparent; border: none;")
        slider.valueChanged.connect(lambda val, k=key, l=label_val, s=slider: self._update_slider_value(k, s.value(), l))
        hbox.addWidget(slider)
        hbox.addWidget(label_val)
        layout.addLayout(hbox)

    def _update_slider_value(self, key, value, label):
        label.setText(str(value))
        self.theme_data[key] = value

    def _add_dropdown(self, layout, display_name, key, value):
        hbox = QHBoxLayout()
        label = QLabel(display_name)
        label.setStyleSheet("background-color: transparent; border: none;")
        hbox.addWidget(label)
        dropdown = QComboBox()
        options = []
        if key == "name":
             options = ["auto", "classic", "white", "black", "modern"]
        elif key == "view":
           options = ["auto", "compact", "small", "medium", "large", "wide"]
        elif key == "font.name":
             options = ["Segoe UI Variable Text", "Comic Sans MS", "Impact" , "Arial", "Helvetica", "Times  New Roman", "Courier New",
                        "Calibri", "Cambria", "Garamond", "Georgia", "Tahoma", "Trebuchet MS", "Century Gothic", "Franklin Gothic Medium", "Consolas"]

        dropdown.addItems(options)
        dropdown.setStyleSheet(f"""
            QComboBox {{
                border: 1px solid #268a86;
                border-radius: 22px;
                padding: 3px;
                font-size: 13px;
                background: #333;
                color: #fff;
                min-width: 160px;
            }}
        QComboBox::drop-down {{
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: 18px;
            border-left: 1px solid #268a86;
            border-top-right-radius: 21px;
             border-bottom-right-radius: 21px;
        }}
        QComboBox::down-arrow {{
           image: url(none);
        }}
       QComboBox QAbstractItemView {{
             border: 1px solid #268a86;
            background: #333;
       }}
       QComboBox QAbstractItemView::item {{
            color: #fff;
        }}
        QComboBox QAbstractItemView::item:selected {{
            background: #555;
        }}""")
        dropdown.setCurrentText(value if key != "view" else value.split('.')[1] )
        dropdown.currentTextChanged.connect(lambda  text, k=key: self._update_theme_data(k, text if key != "view" else f"view.{text}"))
        hbox.addWidget(dropdown)
        hbox.addStretch(1)
        layout.addLayout(hbox)

    def _add_text_input(self, layout, display_name, key, value):
        hbox = QHBoxLayout()
        label = QLabel(display_name)
        label.setStyleSheet("background-color: transparent; border: none;")
        hbox.addWidget(label)
        line_edit = QLineEdit(value)
        line_edit.setStyleSheet("""QLineEdit {
                    border: 1px solid  #268a86;
                    border-radius: 22px;
                    padding: 3px;
                    font-size: 13px;
                    background: #333;
                    color: #fff;
               }
            QLineEdit:focus {
                border: 1px solid #268a86;
            }""")
        line_edit.setFixedSize(160, 25)
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
                  if key in ["name","font.name"]:
                     file.write(f"  {key} = \"{value}\"\n")
                  else:
                     file.write(f"  {key} = {value}\n")
                file.write("}\n")
        except Exception as e:
            print(f"Error in save_theme: {e}")

    def _save_backup(self):
        try:
            shutil.copyfile(THEME_PATH, THEME_BACKUP_PATH)
        except Exception as e:
            print(f"Failed to save backup theme: {e}")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(ICON_PATH))
    app.setStyleSheet("""
        QMainWindow {
            background-color: #222;
        }
        QLabel {
            color: #fff;
            font-size: 13px;
            margin-right: 6px;
             padding-left: 3px;
        }
         QLabel#SectionTitle {
            font-size: 15px;
            font-weight: bold;
            color: #fff;
            margin-bottom: 8px;
            text-align: center;
        }
        QScrollBar:vertical {
            border: none;
            background: #333;
            width: 8px;
        }
        QScrollBar::handle:vertical {
            background: #555;
            min-height: 14px;
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
