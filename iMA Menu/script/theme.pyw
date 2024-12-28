import sys
import os
import pyautogui
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QLineEdit, QCheckBox, QSlider, QComboBox, QColorDialog, QFileDialog,
    QScrollArea, QFrame, QSplitter, QStackedWidget, QGridLayout, QSpacerItem,
    QSizePolicy
)
from PyQt5.QtGui import QIcon, QColor, QFont, QPixmap, QPainter, QPolygon
from PyQt5.QtCore import Qt, QTimer, QSize, pyqtSignal, QPoint
import shutil

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
        self.setFixedSize(30, 30)
        self.set_color(initial_color)
        self.clicked.connect(self._open_color_dialog)
        self.setStyleSheet("border: 2px solid #444;")

    def set_color(self, hex_color):
        self.hex_color = hex_color
        self.setStyleSheet(f"background-color: {hex_color}; border: 2px solid #444;")

    def _open_color_dialog(self):
        color = QColorDialog.getColor(QColor(self.hex_color), self)
        if color.isValid():
            self.set_color(color.name())
            self.colorChanged.emit(self.hex_color)

# --- Collapsible Section ---
class CollapsibleSection(QWidget):
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.is_collapsed = False
        self._setup_ui(title)

    def _setup_ui(self, title):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        self.header = QPushButton(title, self)
        self.header.setStyleSheet("""QPushButton {
            background-color: #333;
            color: #ddd;
            border: 2px solid #444;
            border-radius: 4px;
            padding: 8px;
            font-size: 14px;
            text-align: left;
            margin-bottom: 1px;
        }
        QPushButton:hover {
            background-color: #444;
        }""")
        self.header.setCursor(Qt.PointingHandCursor)
        self.header.clicked.connect(self._toggle)
        self.main_layout.addWidget(self.header)

        self.content_area = QWidget()
        self.content_layout = QVBoxLayout(self.content_area)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(0)
        self.main_layout.addWidget(self.content_area)
        self.content_area.hide()

    def _toggle(self):
        self.is_collapsed = not self.is_collapsed
        self.content_area.setVisible(not self.is_collapsed)

    def add_widget(self, widget):
        self.content_layout.addWidget(widget)

# --- Expand Arrow Button ---
class ExpandArrowButton(QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(18, 18)
        self.setCursor(Qt.PointingHandCursor)
        self.is_expanded = False
        self._update_arrow_icon()

    def _update_arrow_icon(self):
        pixmap = QPixmap(18, 18)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        polygon = QPolygon()
        if self.is_expanded:
            polygon.append(QPoint(0, 5))
            polygon.append(QPoint(9, 14))
            polygon.append(QPoint(18, 5))
        else:
             polygon.append(QPoint(5, 0))
             polygon.append(QPoint(14, 9))
             polygon.append(QPoint(5, 18))
        painter.setBrush(QColor("#ddd"))
        painter.drawPolygon(polygon)
        painter.end()
        self.setIcon(QIcon(pixmap))
        self.setStyleSheet("QPushButton { border: none; }")

    def toggle_expand(self):
        self.is_expanded = not self.is_expanded
        self._update_arrow_icon()

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
            "background.effect": (0, 3),
            "item.prefix": (0, 2),
            "font.weight": (1, 9),
        }
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
        self.setGeometry(100, 100, 1000, 700)
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)

        self.sidebar = QFrame()
        self.sidebar.setFixedWidth(180)
        self.sidebar.setStyleSheet("background-color: #2b2b2b; border-right: 1px solid #444;")
        sidebar_layout = QVBoxLayout(self.sidebar)
        splitter.addWidget(self.sidebar)

        self.tab_area = QFrame()
        self.tab_area.setStyleSheet("background-color: #333; border: none;")
        self.tab_area_layout = QVBoxLayout(self.tab_area)
        splitter.addWidget(self.tab_area)

        self.tab_buttons = {}
        icon_paths = {
            "General": os.path.join(SCRIPT_DIR, "script", "theme-icons", "general.ico"),
            "Border": os.path.join(SCRIPT_DIR, "script", "theme-icons", "Border.ico"),
            "Image": os.path.join(SCRIPT_DIR, "script", "theme-icons", "Image.ico"),
            "Background": os.path.join(SCRIPT_DIR, "script", "theme-icons", "Background.ico"),
            "Item": os.path.join(SCRIPT_DIR, "script", "theme-icons", "Item.ico"),
            "Font": os.path.join(SCRIPT_DIR, "script", "theme-icons", "Font.ico"),
            "Shadow": os.path.join(SCRIPT_DIR, "script", "theme-icons", "Shadow.ico"),
            "Separator": os.path.join(SCRIPT_DIR, "script", "theme-icons", "Separator.ico"),
            "Symbol": os.path.join(SCRIPT_DIR, "script", "theme-icons", "Symbol.ico"),
        }

        categories = ["General", "Border", "Background", "Item", "Font", "Shadow", "Separator", "Image", "Symbol"]
        for category in categories:
            tab_button = QPushButton(QIcon(icon_paths.get(category)), category, self)
            tab_button.setStyleSheet("""QPushButton {
                background-color: #333;
                color: #ddd;
                border: 1px solid #444;
                border-radius: 4px;
                padding: 8px;
                font-size: 14px;
                text-align: left;
                margin: 1px;
            }
            QPushButton:hover {
                background-color: #444;
            }
            QPushButton:checked {
                background-color: #555;
            }""")
            tab_button.setCheckable(True)
            tab_button.clicked.connect(lambda checked, cat=category: self._show_form(cat))
            sidebar_layout.addWidget(tab_button)
            self.tab_buttons[category] = tab_button

        self.stacked_widget = QStackedWidget()
        self.tab_area_layout.addWidget(self.stacked_widget)

        button_layout = QVBoxLayout()
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
        sidebar_layout.addLayout(button_layout)

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
        while self.stacked_widget.count() > 0:
            widget = self.stacked_widget.widget(0)
            self.stacked_widget.removeWidget(widget)
            widget.deleteLater()

        categories = {
            "General": ["name", "view"],
            "Border": ["border.enabled", "border.size", "border.color", "border.opacity", "border.radius"],
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
            "background.effect": "Background Effect : 0 = Disabled, 1 = Transparent, 2 = Blur, 3 = Acrylic",
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

        for category, keys in categories.items():
            form_scroll = QScrollArea()
            form_scroll.setWidgetResizable(True)
            form_widget = QWidget()
            form_layout = QVBoxLayout(form_widget)
            form_layout.setContentsMargins(5, 5, 5, 5)
            form_layout.setSpacing(10)

            if category == "Item":
                self._add_item_settings(form_layout, display_names)
            else:
                for key in keys:
                   if key in self.theme_data:
                       value = self.theme_data[key]
                       display_name = display_names.get(key, key)
                       if value.lower() in ["true", "false"]:
                           self._add_checkbox(form_layout, display_name, key, value.lower() == "true")
                       elif value.startswith("#"):
                           if key == "background.color":
                              self._add_background_color_picker(form_layout, display_name, key, value)
                           else:
                               self._add_color_picker(form_layout, display_name, key, value)
                       elif value.isdigit():
                            min_val, max_val = self.slider_ranges.get(key, (0, 100))
                            self._add_slider(form_layout, display_name, key, int(value), min_val, max_val)
                       elif key in ["name", "view", "font.name"]:
                            self._add_dropdown(form_layout, display_name, key, value)
                       else:
                            self._add_text_input(form_layout, display_name, key, value)

            form_scroll.setWidget(form_widget)
            self.stacked_widget.addWidget(form_scroll)
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

        # Unified Text Color
       text_group = CollapsibleSection("Text Settings")
       unified_text_color = self.theme_data.get(text_keys["normal"], '#ffffff')
       def update_text_color(color):
          for key in text_keys.values():
              if not key.endswith('-disabled'):
                self._update_theme_data(key, color)
                text_group.advanced_settings.layout().itemAt(list(text_keys.values()).index(key) * 2).widget().set_color(color)

       text_color_picker = self._add_color_picker_no_label(unified_text_color, update_text_color)
       text_group.add_widget(text_color_picker)
       # Text expand area
       text_expand = QHBoxLayout()
       text_group.expand_arrow = ExpandArrowButton()
       text_expand.addStretch(1)
       text_expand.addWidget(text_group.expand_arrow)
       text_group.add_widget(self._add_layout_widget(text_expand))
       # Advanced Text Settings
       text_group.advanced_settings = QWidget()
       adv_text_layout = QVBoxLayout(text_group.advanced_settings)
       adv_text_layout.setContentsMargins(0, 0, 0, 0)
       adv_text_layout.setSpacing(5)
       for key, value in text_keys.items():
           if not key.endswith("disabled"):
               color_picker = self._add_color_picker_no_label(self.theme_data.get(value, '#ffffff'), lambda color, k=value: self._update_theme_data(k, color))
               adv_text_layout.addWidget(QLabel(f"{display_names[value]}"))
               adv_text_layout.addWidget(color_picker)

       text_group.expand_arrow.clicked.connect(lambda: self._toggle_expand_setting(text_group))
       text_group.add_widget(text_group.advanced_settings)
       text_group.advanced_settings.hide()
       layout.addWidget(text_group)

       # Unified Disabled Text Color
       disabled_text_group = CollapsibleSection("Disabled Text Settings")
       unified_disabled_text_color = self.theme_data.get(text_keys["normal-disabled"], '#a0a0a0')
       def update_disabled_text_color(color):
         for key in text_keys.values():
            if key.endswith('-disabled'):
               self._update_theme_data(key, color)
               disabled_text_group.advanced_settings.layout().itemAt(list(text_keys.values()).index(key) - 2 ).widget().set_color(color)


       disabled_text_color_picker = self._add_color_picker_no_label(unified_disabled_text_color, update_disabled_text_color)
       disabled_text_group.add_widget(disabled_text_color_picker)
        # Disabled Text Expand Area
       disabled_text_expand = QHBoxLayout()
       disabled_text_group.expand_arrow = ExpandArrowButton()
       disabled_text_expand.addStretch(1)
       disabled_text_expand.addWidget(disabled_text_group.expand_arrow)
       disabled_text_group.add_widget(self._add_layout_widget(disabled_text_expand))
       # Advanced Disabled Text Settings
       disabled_text_group.advanced_settings = QWidget()
       adv_disabled_text_layout = QVBoxLayout(disabled_text_group.advanced_settings)
       adv_disabled_text_layout.setContentsMargins(0, 0, 0, 0)
       adv_disabled_text_layout.setSpacing(5)
       for key, value in text_keys.items():
           if key.endswith("disabled"):
                color_picker = self._add_color_picker_no_label(self.theme_data.get(value, '#a0a0a0'), lambda color, k=value: self._update_theme_data(k, color))
                adv_disabled_text_layout.addWidget(QLabel(f"{display_names[value]}"))
                adv_disabled_text_layout.addWidget(color_picker)

       disabled_text_group.expand_arrow.clicked.connect(lambda: self._toggle_expand_setting(disabled_text_group))
       disabled_text_group.add_widget(disabled_text_group.advanced_settings)
       disabled_text_group.advanced_settings.hide()
       layout.addWidget(disabled_text_group)

        #Border Settings
       border_group = CollapsibleSection("Border Settings")
       for key, value in border_keys.items():
          color_picker = self._add_color_picker_no_label(self.theme_data.get(value, '#444'), lambda color, k=value: self._update_theme_data(k, color))
          border_group.add_widget(QLabel(f"{display_names[value]}"))
          border_group.add_widget(color_picker)
       layout.addWidget(border_group)
        # BackGround Settings
       back_group = CollapsibleSection("Background Settings")
       for key, value in back_keys.items():
           color_picker = self._add_color_picker_no_label(self.theme_data.get(value, '#444'), lambda color, k=value: self._update_theme_data(k, color))
           back_group.add_widget(QLabel(f"{display_names[value]}"))
           back_group.add_widget(color_picker)
       layout.addWidget(back_group)

        # Other Settings
       settings_keys = ["item.opacity", "item.radius", "item.prefix"]
       other_group = CollapsibleSection("Other Item Settings")
       for key in settings_keys:
          if key in self.theme_data:
              value = self.theme_data[key]
              display_name = display_names.get(key, key)
              min_val, max_val = self.slider_ranges.get(key, (0, 100))
              self._add_slider(other_group.content_layout, display_name, key, int(value), min_val, max_val)
       layout.addWidget(other_group)

    def _toggle_expand_setting(self, setting_group):
        setting_group.expand_arrow.toggle_expand()
        setting_group.advanced_settings.setVisible(setting_group.expand_arrow.is_expanded)

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

    def _add_layout_widget(self, layout):
       widget = QWidget()
       widget.setLayout(layout)
       return widget
    def _add_color_picker(self, layout, display_name, key, value):
            hbox = QHBoxLayout()
            label = QLabel(display_name)
            hbox.addWidget(label)
            color_button = ColorPickerButton(value)
            color_button.colorChanged.connect(lambda color, k=key: self._update_theme_data(k, color))
            hbox.addWidget(color_button)
            hbox.addSpacing(10)
            line_edit = QLineEdit(value)
            line_edit.setFixedSize(70,30)
            line_edit.textChanged.connect(lambda text, k=key: self._update_theme_data(k, text))
            hbox.addWidget(line_edit)
            hbox.addStretch(1)
            layout.addLayout(hbox)

    def _add_color_picker_no_label(self, initial_color, color_changed_func):
            hbox = QHBoxLayout()
            color_button = ColorPickerButton(initial_color)
            color_button.colorChanged.connect(color_changed_func)
            hbox.addWidget(color_button)
            hbox.addSpacing(10)
            line_edit = QLineEdit(initial_color)
            line_edit.setFixedSize(70, 30)
            line_edit.textChanged.connect(lambda text,  c=color_button: c.set_color(text))
            hbox.addWidget(line_edit)
            hbox.addStretch(1)
            widget = QWidget()
            widget.setLayout(hbox)
            return widget

    def _add_background_color_picker(self, layout, display_name, key, value):
            hbox = QHBoxLayout()
            label = QLabel(display_name)
            hbox.addWidget(label)
            color_button = ColorPickerButton(value if value != 'default' else "#ffffff")
            color_button.colorChanged.connect(lambda color, k=key: self._update_background_color(color, k))
            hbox.addWidget(color_button)
            hbox.addSpacing(10)
            line_edit = QLineEdit(value if value != 'default' else "")
            line_edit.setFixedSize(70, 30)
            line_edit.setEnabled(value != 'default')
            line_edit.textChanged.connect(lambda text, k=key: self._update_theme_data(k, text))
            hbox.addWidget(line_edit)
            default_checkbox = QCheckBox("Default")
            default_checkbox.setChecked(value == 'default')
            default_checkbox.stateChanged.connect(lambda state, le=line_edit, cb=color_button: self._toggle_background_default(state, le, cb))
            hbox.addWidget(default_checkbox)
            hbox.addStretch(1)
            layout.addLayout(hbox)

    def _update_background_color(self, color, key):
         self.theme_data[key] = color

    def _toggle_background_default(self, state, line_edit, button):
         if state == Qt.Checked:
               line_edit.setEnabled(False)
               line_edit.setText("")
               button.set_color("#FFFFFF")
               self.theme_data['background.color'] = 'default'
         else:
                line_edit.setEnabled(True)
                self.theme_data['background.color'] = line_edit.text()

    def _add_slider(self, layout, display_name, key, value, min_val, max_val):
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
            hbox.addStretch(1)
            layout.addLayout(hbox)

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

    def _show_form(self, category):
        for btn in self.tab_buttons.values():
            btn.setChecked(False)
        self.tab_buttons[category].setChecked(True)
        index = list(self.tab_buttons.keys()).index(category)
        self.stacked_widget.setCurrentIndex(index)


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
