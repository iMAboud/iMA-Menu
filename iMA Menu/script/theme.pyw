import sys
import os
import shutil
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QLineEdit, QCheckBox, QSlider, QComboBox, QColorDialog, QGridLayout,
    QFrame, QButtonGroup, QRadioButton, QTabWidget, QScrollArea, QGraphicsDropShadowEffect
)
from PyQt5.QtGui import QIcon, QColor, QFont
from PyQt5.QtCore import Qt, pyqtSignal

# --- Constants ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPT_DIR = os.path.dirname(BASE_DIR)
ICON_PATH = os.path.join(SCRIPT_DIR, "icons", "theme.ico")
THEME_PATH = os.path.join(SCRIPT_DIR, "imports", "theme.nss")
THEME_BACKUP_PATH = os.path.join(SCRIPT_DIR, "imports", "theme_backup.nss")

# --- Colors ---
colors = {
    "background_color": "transparent",
    "text_color": "white",
    "frame_background": "#444",
    "frame_border": "#268a86",
     "frame1_background": "rgba(108, 137, 151, 0.22)",
    "frame1_border": "#268a86",
    "frame2_background": "rgba(37, 115, 152, 0.22)",
     "frame2_border": "#268a86",
     "frame3_background": "rgba(108, 137, 151, 0.22)",
    "frame3_border": "#268a86",
     "frame4_background": "rgba(37, 115, 152, 0.22)",
    "frame4_border": "#268a86",
    "frame5_background": "rgba(108, 137, 151, 0.22)",
    "frame5_border": "#268a86",
    "frame6_background": "rgba(37, 115, 152, 0.22)",
    "frame6_border": "#268a86",
    "frame_drop_shadow": "rgba(0, 0, 0, 150)",
    "button_background": "#555",
    "button_hover": "#268a86",
    "button_text": "white",
    "checkbox_background": "transparent",
    "checkbox_border": "#268a86",
    "checkbox_checked": "#268a86",
    "slider_groove": "#333",
    "slider_handle": "#268a86",
     "slider_add_page": "#555",
    "slider_text": "#fff",
    "dropdown_background": "#333",
    "dropdown_border": "#268a86",
    "dropdown_text": "#fff",
    "dropdown_item_background": "#333",
    "dropdown_item_hover": "#268a86",
    "dropdown_item_selected": "#268a86",
    "line_edit_background": "#333",
    "line_edit_border": "#268a86",
     "line_edit_text": "#fff",
     "tab_background": "rgba(37, 115, 152, 0.22)",
    "tab_border": "#268a86",
    "tab_text": "white",
    "tab_selected": "#268a86"
}

# --- Color Picker Button ---
class ColorPickerButton(QPushButton):
    colorChanged = pyqtSignal(str)

    def __init__(self, initial_color="#333333", parent=None):
        super().__init__(parent)
        self.setFixedSize(64, 64)
        self.setStyleSheet(f"border: 1px solid {colors['frame_border']}; border-radius: 22px; background-color: {initial_color}")
        self.hex_color = initial_color
        self.clicked.connect(self._open_color_dialog)

    def set_color(self, hex_color):
        self.hex_color = hex_color
        self.setStyleSheet(f"background-color: {hex_color}; border: 1px solid {colors['frame_border']}; border-radius: 22px;")

    def _open_color_dialog(self):
        color = QColorDialog.getColor(QColor(self.hex_color), self)
        if color.isValid():
            self.set_color(color.name())
            self.colorChanged.emit(self.hex_color)

# --- Drop Shadow Function ---
def set_drop_shadow(widget, blur_radius=10, offset_x=4, offset_y=4, opacity=150):
    shadow = QGraphicsDropShadowEffect()
    shadow.setBlurRadius(blur_radius)
    shadow.setColor(QColor(0, 0, 0, opacity))
    shadow.setOffset(offset_x, offset_y)
    widget.setGraphicsEffect(shadow)

# --- Main Theme Editor ---
class ThemeEditor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.theme_data = {

        }
        self.backup_theme_data = self.theme_data.copy()
        self.slider_ranges = {
            "border.size": (0, 10), "item.opacity": (0, 100), "item.radius": (0, 3),
            "shadow.size": (0, 30), "shadow.opacity": (0, 100), "separator.size": (0, 40),
            "separator.opacity": (0, 100), "background.opacity": (0, 100), "font.size": (6, 100),
            "border.radius": (0, 3), "item.prefix": (0, 2), "font.weight": (1, 9)
        }
        self.color_pickers = {}
        self._setup_ui()
        self._load_theme()
        self.setWindowIcon(QIcon(ICON_PATH))
        self.is_closing = False
        self.launcher_background_color = colors["background_color"]
        self.central_widget.setStyleSheet(f"background-color: {self.launcher_background_color}; color: {colors['text_color']};")

    def closeEvent(self, event):
        self.is_closing = True
        if self.theme_data != self.backup_theme_data:
            self._save_backup()
        event.accept()

    def _setup_ui(self):
        self.setWindowTitle('iMAboud - Theme Editor')
        self.setGeometry(100, 100, 900, 700)
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        main_layout = QGridLayout(self.central_widget)
        main_layout.setSpacing(8)

         # Create Frames with Teal Borders
        self.general_frame = self._create_frame(1)
        self.border_frame = self._create_frame(2)
        self.background_frame = self._create_frame(3)
        self.item_text_frame = self._create_frame(4)
        self.image_symbol_frame = self._create_frame(5)
        self.shadow_separator_frame = self._create_frame(6)

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
        self.item_text_tab_widget.setStyleSheet(f"QTabWidget::pane {{background-color: {colors['tab_background']};border: none;}} QTabBar::tab {{ border-bottom: none;background-color: {colors['tab_background']};color: {colors['tab_text']};}} QTabBar::tab:selected {{background-color: {colors['tab_selected']};}}") #Removed Tab Border
        self.item_text_layout.addWidget(self.item_text_tab_widget)

        self.item_text_tab = QWidget()
        self.item_text_tab_layout = QVBoxLayout(self.item_text_tab)
        self.item_text_tab_widget.addTab(self.item_text_tab, "Text")

        self.font_tab = QWidget()
        self.font_tab_layout = QVBoxLayout(self.font_tab)
        self.item_text_tab_widget.addTab(self.font_tab, "Font")

        for layout in [self.general_layout, self.border_layout, self.background_layout, self.item_text_tab_layout,
                      self.image_symbol_layout, self.shadow_separator_layout, self.font_tab_layout]:
           layout.setContentsMargins(8, 8, 8, 8)
           layout.setSpacing(5)

    def _create_frame(self, frame_number):
        frame = QFrame(self)
        frame.setStyleSheet(f"QFrame {{ background-color: {colors[f'frame{frame_number}_background']}; border-radius: 10px; border: 2px solid {colors[f'frame{frame_number}_border']}}} ")
        set_drop_shadow(frame, 8, 3, 3, 150)
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
        self._add_setting_with_label(self.general_layout, "frame1.background")
        self._add_setting_with_label(self.general_layout, "frame1.border")


        # --- FRAME 2: Border ---
        self._add_setting_with_label(self.border_layout, "border.enabled")
        self._add_setting_with_label(self.border_layout, "border.size")
        self._add_setting_with_label(self.border_layout, "border.color")
        self._add_setting_with_label(self.border_layout, "border.opacity")
        self._add_setting_with_label(self.border_layout, "item.border.normal")
        self._add_setting_with_label(self.border_layout, "item.border.select")
        self._add_setting_with_label(self.border_layout, "frame2.background")
        self._add_setting_with_label(self.border_layout, "frame2.border")


        # --- FRAME 3: Background ---
        self._add_setting_with_label(self.background_layout, "background.color")
        self._add_setting_with_label(self.background_layout, "background.effect")
        self._add_setting_with_label(self.background_layout, "background.opacity")
        self._add_setting_with_label(self.background_layout, "frame3.background")
        self._add_setting_with_label(self.background_layout, "frame3.border")


       # --- FRAME 4: Item Text and Back ---
        self._add_setting_with_label(self.item_text_tab_layout, "item.text.normal")
        self._add_setting_with_label(self.item_text_tab_layout, "item.text.select")
        self._add_setting_with_label(self.item_text_tab_layout, "item.text.normal-disabled")
        self._add_setting_with_label(self.item_text_tab_layout, "item.back.select")
        self._add_setting_with_label(self.item_text_tab_layout, "frame4.background")
        self._add_setting_with_label(self.item_text_tab_layout, "frame4.border")


       # --- FRAME 5: Image and Symbols ---
        hbox = QHBoxLayout()
        self._add_setting_with_label(hbox, "image.enabled")
        hbox.addStretch()
        self.image_symbol_layout.addLayout(hbox)
        self._add_setting_with_label(self.image_symbol_layout, "image.color", is_image=True)
        self._add_setting_with_label(self.image_symbol_layout, "symbol.normal")
        self._add_setting_with_label(self.image_symbol_layout, "frame5.background")
        self._add_setting_with_label(self.image_symbol_layout, "frame5.border")

        # --- FRAME 6: Shadow and Separator ---
        self._add_setting_with_label(self.shadow_separator_layout, "shadow.enabled")
        self._add_setting_with_label(self.shadow_separator_layout, "shadow.size")
        self._add_setting_with_label(self.shadow_separator_layout, "shadow.opacity")
        self._add_setting_with_label(self.shadow_separator_layout, "shadow.color")
        self._add_setting_with_label(self.shadow_separator_layout, "separator.size")
        self._add_setting_with_label(self.shadow_separator_layout, "separator.color")
        self._add_setting_with_label(self.shadow_separator_layout, "separator.opacity")
        self._add_setting_with_label(self.shadow_separator_layout, "frame6.background")
        self._add_setting_with_label(self.shadow_separator_layout, "frame6.border")

        # --- FRAME 7: Font ---
        self._add_setting_with_label(self.font_tab_layout, "font.size")
        self._add_setting_with_label(self.font_tab_layout, "font.name")
        self._add_setting_with_label(self.font_tab_layout, "font.weight")
        self._add_setting_with_label(self.font_tab_layout, "font.italic")

         # --- FRAME 8: Custom Styling ---
        self._add_setting_with_label(self.general_layout, "button.background")
        self._add_setting_with_label(self.general_layout, "button.hover")
        self._add_setting_with_label(self.general_layout, "button.text")
        self._add_setting_with_label(self.general_layout, "checkbox.background")
        self._add_setting_with_label(self.general_layout, "checkbox.border")
        self._add_setting_with_label(self.general_layout, "checkbox.checked")
        self._add_setting_with_label(self.general_layout, "slider.groove")
        self._add_setting_with_label(self.general_layout, "slider.handle")
        self._add_setting_with_label(self.general_layout, "slider.add_page")
        self._add_setting_with_label(self.general_layout, "slider.text")
        self._add_setting_with_label(self.general_layout, "dropdown.background")
        self._add_setting_with_label(self.general_layout, "dropdown.border")
        self._add_setting_with_label(self.general_layout, "dropdown.text")
        self._add_setting_with_label(self.general_layout, "dropdown.item_background")
        self._add_setting_with_label(self.general_layout, "dropdown.item_hover")
        self._add_setting_with_label(self.general_layout, "dropdown.item_selected")
        self._add_setting_with_label(self.general_layout, "line_edit.background")
        self._add_setting_with_label(self.general_layout, "line_edit.border")
        self._add_setting_with_label(self.general_layout, "line_edit.text")
        self._add_setting_with_label(self.general_layout, "tab.background")
        self._add_setting_with_label(self.general_layout, "tab.border")
        self._add_setting_with_label(self.general_layout, "tab.text")
        self._add_setting_with_label(self.general_layout, "tab.selected")
        self._add_setting_with_label(self.general_layout, "frame_drop_shadow")

    def _add_setting_with_label(self, layout, key, is_image = False):
        display_names = {
            "name": "Theme", "border.enabled": "Enable Border",
            "border.size": "Border Size", "border.color": "Border Color",
            "border.opacity": "Border Opacity", "border.radius": "Border Radius",
            "image.enabled": "Enable Image", "image.color": "Image Color",
            "background.color": "Background Color",
            "background.opacity": "Background Opacity", "background.effect": "Background Effect",
            "item.radius": "Item Radius", "item.text.normal": "Text",
            "item.text.select": "Selected Text", "item.back.select": "Text Background",
            "item.border.normal": "Item Border", "item.border.select": "Text Border",
            "item.text.normal-disabled": "Disabled Text",
            "font.size": "Font Size",
            "font.name": "Font Name", "font.weight": "Bold", "font.italic": "Italic",
            "shadow.enabled": "Enable Shadow", "shadow.size": "Shadow Size",
            "shadow.opacity": "Shadow Opacity", "shadow.color": "Shadow Color",
            "separator.size": "Separator Size", "separator.color": "Separator Color",
            "separator.opacity": "Separator Opacity",  "symbol.normal": "Symbol",
             "button.background": "Button Background",
            "button.hover": "Button Hover",
             "button.text": "Button Text",
            "checkbox.background": "Checkbox Background",
            "checkbox.border": "Checkbox Border",
            "checkbox.checked": "Checkbox Checked",
             "slider.groove": "Slider Groove",
            "slider.handle": "Slider Handle",
            "slider.add_page": "Slider Add Page",
              "slider.text": "Slider Text",
           "dropdown.background": "Dropdown Background",
            "dropdown.border": "Dropdown Border",
           "dropdown.text": "Dropdown Text",
            "dropdown.item_background": "Dropdown Item Bg",
            "dropdown.item_hover": "Dropdown Item Hover",
            "dropdown.item_selected": "Dropdown Item Sel",
            "line_edit.background": "Line Edit Background",
             "line_edit.border": "Line Edit Border",
            "line_edit.text": "Line Edit Text",
            "tab.background": "Tab Background",
            "tab.border": "Tab Border",
             "tab.text": "Tab Text",
            "tab.selected": "Tab Selected",
             "frame.background": "Frame Default Bg",
            "frame.border": "Frame Default Border",
            "frame1.background": "Frame 1 Background",
             "frame1.border": "Frame 1 Border",
             "frame2.background": "Frame 2 Background",
            "frame2.border": "Frame 2 Border",
            "frame3.background": "Frame 3 Background",
            "frame3.border": "Frame 3 Border",
            "frame4.background": "Frame 4 Background",
            "frame4.border": "Frame 4 Border",
            "frame5.background": "Frame 5 Background",
            "frame5.border": "Frame 5 Border",
            "frame6.background": "Frame 6 Background",
            "frame6.border": "Frame 6 Border",
            "frame_drop_shadow": "Frame Drop Shadow",
        }
        display_name = display_names.get(key, key)
        if key in self.theme_data:
            value = self.theme_data[key]

            if key in ["item.opacity", "background.opacity", "border.opacity",
                           "shadow.opacity", "separator.opacity", "border.size",
                           "shadow.size", "separator.size", "border.radius", "item.radius"]:
                min_val, max_val = self.slider_ranges.get(key, (0, 100))
                if key in ["border.size", "shadow.size", "separator.size", "border.radius", "item.radius"]:
                    min_val, max_val = self.slider_ranges.get(key, (0, 3)) if key in ["border.radius", "item.radius"] else self.slider_ranges.get(key, (0, 10))
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
            radio_button.setStyleSheet(f"""QRadioButton::indicator {{
                width: 14px;
                height: 14px;
                border-radius: 7px;
            }}
            QRadioButton::indicator:checked {{
                background-color: {colors['checkbox_checked']};
                border: 1px solid {colors['checkbox_checked']};
            }}
            QRadioButton::indicator:unchecked {{
                background-color: {colors['checkbox_background']};
                border: 1px solid {colors['checkbox_border']};
            }}
            QRadioButton {{color: {colors['text_color']};}}""")
            radio_group.addButton(radio_button)
            hbox.addWidget(radio_button)
            radio_button.toggled.connect(lambda checked, k=key, v=str(i), o=option: self._update_theme_data(k, v if k == "background.effect" else o) if checked else None )
        hbox.addStretch()
        layout.addLayout(hbox)

    def _add_checkbox(self, layout, display_name, key, checked):
        checkbox = QCheckBox()
        checkbox.setChecked(checked)
        checkbox.setStyleSheet(f"""QCheckBox::indicator {{
                width: 14px;
                height: 14px;
                border-radius: 7px;
            }}
            QCheckBox::indicator:checked {{
                background-color: {colors['checkbox_checked']};
                border: 1px solid {colors['checkbox_checked']};
            }}
            QCheckBox::indicator:unchecked {{
                background-color: {colors['checkbox_background']};
                border: 1px solid {colors['checkbox_border']};
            }}
             QCheckBox {{ color: {colors['text_color']}; background-color: transparent;}}
            """)
        set_drop_shadow(checkbox, 4, 1, 1, 120)
        checkbox.stateChanged.connect(lambda state, k=key, chk=checkbox: self._update_theme_data(k, chk.isChecked()))
        hbox = QHBoxLayout()
        hbox.addWidget(checkbox)
        label = QLabel(display_name)
        label.setStyleSheet("background-color: transparent; border: none;")
        set_drop_shadow(label, 4, 1, 1, 120)
        hbox.addWidget(label)
        hbox.addStretch(1)
        layout.addLayout(hbox)

    def _add_color_picker(self, layout, display_name, key, value):
         hbox = QHBoxLayout()
         checkbox = QCheckBox()
         checkbox.setChecked(value != 'default')
         checkbox.setStyleSheet(f"""QCheckBox::indicator {{
                 width: 14px;
                 height: 14px;
                 border-radius: 7px;
             }}
             QCheckBox::indicator:checked {{
                 background-color: {colors['checkbox_checked']};
                 border: 1px solid {colors['checkbox_checked']};
             }}
             QCheckBox::indicator:unchecked {{
                 background-color: {colors['checkbox_background']};
                 border: 1px solid {colors['checkbox_border']};
             }}
              QCheckBox {{ color: {colors['text_color']};background-color: transparent;}}
             """)
         set_drop_shadow(checkbox, 4, 1, 1, 120)
         color_button = ColorPickerButton(value if value != 'default' else "#ffffff")
         color_button.setEnabled(value != 'default')
         checkbox.stateChanged.connect(lambda state, k=key, cb=color_button: self._toggle_color_default(k, cb, state) )
         color_button.colorChanged.connect(lambda color, k=key: self._update_theme_data(k, color))
         hbox.addWidget(checkbox)
         label = QLabel(display_name)
         label.setStyleSheet("background-color: transparent; border: none;")
         set_drop_shadow(label, 4, 1, 1, 120)
         hbox.addWidget(label)
         hbox.addStretch()
         hbox.addWidget(color_button)
         layout.addLayout(hbox)
         set_drop_shadow(color_button, 4, 1, 1, 120)

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
        checkbox_1.setStyleSheet(f"""QCheckBox::indicator {{
                width: 14px;
                height: 14px;
                border-radius: 7px;
            }}
            QCheckBox::indicator:checked {{
                background-color: {colors['checkbox_checked']};
                border: 1px solid {colors['checkbox_checked']};
            }}
            QCheckBox::indicator:unchecked {{
                background-color: {colors['checkbox_background']};
                border: 1px solid {colors['checkbox_border']};
            }}
            QCheckBox {{ color: {colors['text_color']}; background-color: transparent;}}
            """)
        set_drop_shadow(checkbox_1, 4, 1, 1, 120)
        checkbox_1.setChecked(value[0] != 'default' if isinstance(value, list) else True)
        color_button_1.setEnabled(value[0] != 'default' if isinstance(value, list) else True)
        checkbox_1.stateChanged.connect(lambda state, k=key, cb=color_button_1: self._toggle_image_color(k, cb, state, 0) )
        color_button_1.colorChanged.connect(lambda color, k=key: self._update_image_color(k, color, 0))
        vbox1.addWidget(checkbox_1)
        vbox1.addWidget(color_button_1)
         
        label = QLabel(display_name + " 1")
        label.setStyleSheet(f"text-align: center; color:{colors['text_color']}; background-color: transparent; border: none;")
        set_drop_shadow(label, 4, 1, 1, 120)
        vbox1.addWidget(label, alignment=Qt.AlignCenter)
        color_button_2 = ColorPickerButton(value[1] if isinstance(value, list) and len(value) > 1 else "#ffffff")
        checkbox_2 = QCheckBox()
        checkbox_2.setStyleSheet(f"""QCheckBox::indicator {{
                width: 14px;
                height: 14px;
                 border-radius: 7px;
            }}
            QCheckBox::indicator:checked {{
                background-color: {colors['checkbox_checked']};
                border: 1px solid {colors['checkbox_checked']};
            }}
            QCheckBox::indicator:unchecked {{
                background-color: {colors['checkbox_background']};
                border: 1px solid {colors['checkbox_border']};
            }}
             QCheckBox {{ color: {colors['text_color']};background-color: transparent; }}
            """)
        set_drop_shadow(checkbox_2, 4, 1, 1, 120)
        checkbox_2.setChecked(value[1] != 'default' if isinstance(value, list) and len(value) > 1 else True)
        color_button_2.setEnabled(value[1] != 'default' if isinstance(value, list) and len(value) > 1 else True)
        checkbox_2.stateChanged.connect(lambda state, k=key, cb=color_button_2: self._toggle_image_color(k, cb, state, 1))
        color_button_2.colorChanged.connect(lambda color, k=key: self._update_image_color(k, color, 1))
        vbox2.addWidget(checkbox_2)
        vbox2.addWidget(color_button_2)
        label2 = QLabel(display_name + " 2")
        label2.setStyleSheet(f"text-align: center; color:{colors['text_color']}; background-color: transparent; border: none;")
        set_drop_shadow(label2, 4, 1, 1, 120)
        vbox2.addWidget(label2, alignment=Qt.AlignCenter)
        hbox.addLayout(vbox1)
        hbox.addLayout(vbox2)
        layout.addLayout(hbox)
        set_drop_shadow(color_button_1, 4, 1, 1, 120)
        set_drop_shadow(color_button_2, 4, 1, 1, 120)


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
        default_radio.setStyleSheet(f"color: {colors['text_color']}; background-color: transparent;")
        set_drop_shadow(default_radio, 4, 1, 1, 120)
        default_radio.toggled.connect(lambda checked, k=key: self._toggle_background_default(checked, color_button) )
        hbox.addWidget(default_radio)
        radio_group.addButton(default_radio)
        color_button = ColorPickerButton(value if value != 'default' else "#ffffff")
        color_button.setEnabled(value != 'default')
        set_drop_shadow(color_button, 4, 1, 1, 120)
        color_button.colorChanged.connect(lambda color, k=key: self._update_background_color(color, k))
        hbox.addWidget(color_button)
        custom_radio = QRadioButton("Custom")
        custom_radio.setChecked(value != 'default')
        custom_radio.setStyleSheet(f"color: {colors['text_color']}; background-color: transparent;")
        set_drop_shadow(custom_radio, 4, 1, 1, 120)
        hbox.addWidget(custom_radio)
        radio_group.addButton(custom_radio)
        custom_radio.toggled.connect(lambda checked, k=key, cb=color_button, v=value: self._toggle_background_color(checked, cb, v) )
        hbox.addStretch()
        hbox2 = QVBoxLayout()
        label = QLabel(display_name)
        label.setStyleSheet("background-color: transparent; border: none;")
        set_drop_shadow(label, 4, 1, 1, 120)
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
        set_drop_shadow(label, 4, 1, 1, 120)
        hbox.addWidget(label)
        slider = QSlider(Qt.Horizontal)
        slider.setMinimum(min_val)
        slider.setMaximum(max_val)
        slider.setValue(value)
        slider.setStyleSheet(f"""
        QSlider::groove:horizontal {{
            border: 1px solid {colors['frame_border']};
            height: 4px;
            background: {colors['slider_groove']};
            border-radius: 7px;
        }}
        QSlider::handle:horizontal {{
            background: {colors['slider_handle']};
            border: 1px solid {colors['slider_handle']};
            width: 12px;
            height: 12px;
            margin: -5px 0;
            border-radius: 7px;
        }}
         QSlider::add-page:horizontal {{
           background: {colors['slider_add_page']};
           border-radius: 7px;
         }}
        QSlider::sub-page:horizontal {{
          background: {colors['slider_handle']};
           border-radius: 7px;
        }}
    """)
        set_drop_shadow(slider, 4, 1, 1, 120)
        slider.setLayoutDirection(Qt.LeftToRight)
        label_val = QLabel(str(value))
        label_val.setFixedWidth(30)
        label_val.setStyleSheet(f"color: {colors['slider_text']}; background-color: transparent; border: none; font-size: 14px; -webkit-text-stroke: 1px {colors['slider_handle']};")
        set_drop_shadow(label_val, 4, 1, 1, 120)
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
        set_drop_shadow(label, 4, 1, 1, 120)
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
        dropdown.setStyleSheet(f"""
        QComboBox {{
            border: 1px solid {colors['dropdown_border']};
            border-radius: 10px;
            padding: 3px 8px;
            font-size: 13px;
            background: {colors['dropdown_background']};
            color: {colors['dropdown_text']};
            min-width: 160px;
        }}
        QComboBox:hover {{
            border: 1px solid {colors['dropdown_border']};
        }}
        QComboBox::drop-down {{
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: 18px;
            border-left: 1px solid {colors['dropdown_border']};
            border-top-right-radius: 21px;
            border-bottom-right-radius: 21px;
        }}
        QComboBox::down-arrow {{
            image: none;
        }}
        QComboBox QAbstractItemView {{
            border: 1px solid {colors['dropdown_border']};
            border-radius: 10px;
            background: {colors['dropdown_item_background']};
            outline: none;
        }}
        QComboBox QAbstractItemView::item {{
            color: {colors['dropdown_text']};
            padding: 3px 8px;
            margin: 1px;
            border-radius: 10px;
            text-align: center;
        }}
        QComboBox QAbstractItemView::item:selected {{
            background: {colors['dropdown_item_selected']};
        }}
        QComboBox QAbstractItemView::item:hover {{
             background: {colors['dropdown_item_hover']};
        }}
        QComboBox QAbstractItemView::pane {{
            border-radius: 10px;
            outline: none;
        }}
        QComboBox QAbstractItemView::viewport {{
            border-radius: 10px;
        }}
    """)
        set_drop_shadow(dropdown, 4, 1, 1, 120)
        dropdown.setCurrentText(value if key != "view" else value.split('.')[1])
        dropdown.currentTextChanged.connect(lambda text, k=key: self._update_theme_data(k, text if key != "view" else f"view.{text}"))
        hbox.addWidget(dropdown)
        hbox.addStretch(1)
        layout.addLayout(hbox)

    def _add_text_input(self, layout, display_name, key, value):
        hbox = QHBoxLayout()
        label = QLabel(display_name)
        label.setStyleSheet("background-color: transparent; border: none;")
        set_drop_shadow(label, 4, 1, 1, 120)
        hbox.addWidget(label)
        line_edit = QLineEdit(value)
        line_edit.setStyleSheet(f"""QLineEdit {{
                    border: 1px solid  {colors['line_edit_border']};
                    border-radius: 10px;
                    padding: 3px;
                    font-size: 13px;
                    background: {colors['line_edit_background']};
                    color: {colors['line_edit_text']};
               }}
            QLineEdit:focus {{
                border: 1px solid {colors['line_edit_border']};
            }}""")
        set_drop_shadow(line_edit, 4, 1, 1, 120)
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
                   if key == 'image.color':
                        try:
                            color_list = eval(value)
                            if isinstance(color_list, list):
                                formatted_value = f"[{', '.join(c if c != 'default' else '#ffffff' for c in color_list)}]"
                                file.write(f"  {key} = {formatted_value}\n")
                            else:
                                file.write(f"  {key} = {value}\n")
                        except:
                            file.write(f"  {key} = {value}\n")
                   elif key in ["name", "font.name"]:
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
    app.setStyleSheet(f"""
        QMainWindow {{
            background-color: {colors['background_color']}; /* Changed to launcher background */
        }}
        QLabel {{
            color: {colors['text_color']};
            font-size: 13px;
            margin-right: 6px;
             padding-left: 3px;
        }}
         QLabel#SectionTitle {{
            font-size: 15px;
            font-weight: bold;
            color: {colors['text_color']};
            margin-bottom: 8px;
            text-align: center;
        }}
        QScrollBar:vertical {{
            border: none;
            background: {colors['background_color']};
            width: 8px;
        }}
        QScrollBar::handle:vertical {{
            background: #555;
            min-height: 14px;
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            border: none;
            background: none;
        }}
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
            background: none;
        }}
       QTabWidget::pane {{
          border: none;
        }}
         QTabBar::tab {{
          border-bottom: none;
        }}
    """)
    editor = ThemeEditor()
    editor.show()
    sys.exit(app.exec_())
