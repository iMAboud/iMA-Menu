import sys
import os
import shutil
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QLineEdit, QCheckBox, QSlider, QComboBox, QColorDialog, QGridLayout,
    QFrame, QButtonGroup, QRadioButton, QTabWidget, QScrollArea, QGraphicsDropShadowEffect, QStackedWidget, QDialog,
    QSpinBox, QAbstractSpinBox
)
from PyQt5.QtGui import QIcon, QColor, QFont, QPainter, QBrush
from PyQt5.QtCore import Qt, pyqtSignal, QSize, QPoint, QEvent, QTimer, QObject

from utils import resource_path


class DimmingOverlay(QWidget):
    """ A semi-transparent overlay that captures mouse clicks. """
    clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setCursor(Qt.PointingHandCursor)

    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QBrush(QColor(0, 0, 0, 100)))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(self.rect(), 15, 15)


class MinimalColorPickerDialog(QDialog):
    colorSelected = pyqtSignal(str, QColor)

    def __init__(self, initial_color, key, parent=None):
        super().__init__(parent)
        self.key = key
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog | Qt.Popup)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.selected_color = QColor(initial_color if initial_color != "default" else "#ffffff")
        self._last_hue = -1

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(15, 15, 15, 15)

        top_bar_layout = QHBoxLayout()
        self.default_checkbox = QCheckBox("Default")
        self.default_checkbox.setObjectName("themeEditorCheckbox")
        self.default_checkbox.setChecked(initial_color == "default")
        top_bar_layout.addWidget(self.default_checkbox)
        top_bar_layout.addStretch()
        close_button = QPushButton()
        close_button.setIcon(QIcon(resource_path('icons/x.png')))
        close_button.setIconSize(QSize(24, 24))
        close_button.setFixedSize(30, 30)
        close_button.setObjectName("iconButton")
        close_button.clicked.connect(self.reject)
        top_bar_layout.addWidget(close_button)
        self.main_layout.addLayout(top_bar_layout)
        
        self.dimmable_area = QWidget()
        dimmable_layout = QHBoxLayout(self.dimmable_area)
        dimmable_layout.setContentsMargins(0, 0, 0, 0)
        dimmable_layout.setSpacing(10)
        self.main_layout.addWidget(self.dimmable_area)

        self.color_grid_widget = QWidget()
        self.color_grid = QGridLayout(self.color_grid_widget)
        self.color_grid.setSpacing(5)
        dimmable_layout.addWidget(self.color_grid_widget)

        colors = [
            "#f5e0dc", "#f2cdcd", "#f5c2e7", "#cba6f7", "#f38ba8", "#eba0ac", "#fab387", "#f9e2af",
            "#a6e3a1", "#94e2d5", "#89dceb", "#74c7ec", "#89b4fa", "#b4befe", "#cdd6f4", "#1e1e2e",
            "#BF616A", "#D08770", "#EBCB8B", "#A3BE8C", "#B48EAD", "#8FBCBB", "#88C0D0", "#81A1C1",
            "#5E81AC", "#4C566A", "#434C5E", "#3B4252", "#2E3440", "#ECEFF4", "#E5E9F0", "#D8DEE9"
        ]

        row, col = 0, 0
        for color in colors:
            swatch = QPushButton()
            swatch.setFixedSize(24, 24)
            swatch.setStyleSheet(f"background-color: {color}; border-radius: 12px; border: 1px solid #494d64;")
            swatch.clicked.connect(lambda _, c=color: self.select_color_from_swatch(c))
            self.color_grid.addWidget(swatch, row, col)
            col += 1
            if col > 7:
                col = 0
                row += 1

        self.right_panel_widget = QWidget()
        right_layout = QVBoxLayout(self.right_panel_widget)
        right_layout.setSpacing(10)
        dimmable_layout.addWidget(self.right_panel_widget)

        self.preview = QLabel()
        self.preview.setFixedSize(150, 100)
        right_layout.addWidget(self.preview, alignment=Qt.AlignCenter)

        slider_layout = QVBoxLayout()
        slider_layout.setSpacing(5)
        right_layout.addLayout(slider_layout)

        self.hue_slider = self._create_slider(359)
        self.sat_slider = self._create_slider(255)
        self.val_slider = self._create_slider(255)
        
        self.hue_slider.valueChanged.connect(self.update_color_from_sliders)
        self.sat_slider.valueChanged.connect(self.update_color_from_sliders)
        self.val_slider.valueChanged.connect(self.update_color_from_sliders)

        slider_layout.addWidget(self.hue_slider)
        slider_layout.addWidget(self.sat_slider)
        slider_layout.addWidget(self.val_slider)

        self.ok_button = QPushButton("OK")
        self.ok_button.setObjectName("themeSaveButton")
        self.ok_button.setFixedSize(80, 30)
        self.ok_button.clicked.connect(self.accept_color)
        self.main_layout.addWidget(self.ok_button, alignment=Qt.AlignCenter)

        self.overlay = DimmingOverlay(self)
        self.overlay.hide()

        self.default_checkbox.stateChanged.connect(self.toggle_default)
        self.overlay.clicked.connect(self.undim_on_click)
        self._update_ui_from_color(self.selected_color)
        self.toggle_default(self.default_checkbox.isChecked())

    

    def undim_on_click(self):
        if self.default_checkbox.isChecked():
            self.default_checkbox.setChecked(False)

    def showEvent(self, event):
        super().showEvent(event)
        if self.default_checkbox.isChecked():
            QTimer.singleShot(0, self.show_overlay)

    def show_overlay(self):
        point = self.dimmable_area.mapTo(self, self.dimmable_area.rect().topLeft())
        self.overlay.setGeometry(point.x(), point.y(), self.dimmable_area.width(), self.dimmable_area.height())
        self.overlay.show()
        self.overlay.raise_()

    def toggle_default(self, checked):
        if checked:
            self.show_overlay()
        else:
            self.overlay.hide()
        
        if not checked:
            self._update_ui_from_color(self.selected_color)

    def _create_slider(self, max_val):
        slider = QSlider(Qt.Horizontal)
        slider.setObjectName("themeEditorSlider")
        slider.setMinimum(0)
        slider.setMaximum(max_val)
        return slider

    def accept_color(self):
        if self.default_checkbox.isChecked():
            self.colorSelected.emit(self.key, QColor("default"))
        else:
            self.colorSelected.emit(self.key, self.selected_color)
        self.accept()

    def select_color_from_swatch(self, color_hex):
        self.selected_color = QColor(color_hex)
        self._update_ui_from_color(self.selected_color)

    def update_color_from_sliders(self):
        h = self.hue_slider.value()
        s = self.sat_slider.value()
        v = self.val_slider.value()
        
        if s > 0:
            self._last_hue = h

        self.selected_color.setHsv(h, s, v)
        self.preview.setStyleSheet(f"background-color: {self.selected_color.name()}; border-radius: 15px;")

    def _update_ui_from_color(self, color):
        h, s, v, a = color.getHsv() 
        
        if h != -1:
            self._last_hue = h

        self.hue_slider.blockSignals(True)
        self.sat_slider.blockSignals(True)
        self.val_slider.blockSignals(True)

        self.hue_slider.setValue(self._last_hue if h == -1 else h)
        self.sat_slider.setValue(s)
        self.val_slider.setValue(v)

        self.hue_slider.blockSignals(False)
        self.sat_slider.blockSignals(False)
        self.val_slider.blockSignals(False)

        self.preview.setStyleSheet(f"background-color: {color.name()}; border-radius: 15px;")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QBrush(QColor(30, 32, 48, 230)))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(self.rect(), 15, 15)


class ColorPickerWidget(QWidget):
    colorChanged = pyqtSignal(str, str)

    def __init__(self, initial_color='#333333', key=None, parent=None):
        super().__init__(parent)
        self.hex_color = initial_color
        self.key = key

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        self.color_preview = QLabel()
        self.color_preview.setFixedSize(30, 30)
        self.color_preview.mousePressEvent = self.openColorDialog

        self.hex_input = QLineEdit()
        self.hex_input.setMaxLength(7)
        self.hex_input.setFixedWidth(70)
        self.hex_input.setObjectName("colorHexInput")

        layout.addWidget(self.color_preview)
        layout.addWidget(self.hex_input)

        self.hex_input.textChanged.connect(self.on_text_changed)
        self.set_color(initial_color)


    def set_color(self, hex_color):
        if hex_color == "default":
            self.hex_color = "default"
            self.color_preview.setStyleSheet(f"background-color: #494d64; border-radius: 15px;")
            self.hex_input.setText("default")
        elif QColor(hex_color).isValid():
            self.hex_color = hex_color
            self.color_preview.setStyleSheet(f"background-color: {hex_color}; border-radius: 15px;")
            if self.hex_input.text() != hex_color:
                self.hex_input.setText(hex_color)

    def on_text_changed(self, text):
        if text == "default":
            self.set_color("default")
            self.colorChanged.emit(self.key, self.hex_color)
        elif QColor(text).isValid() and len(text) == 7 and text.startswith('#'):
            self.set_color(text)
            self.colorChanged.emit(self.key, self.hex_color)

    def openColorDialog(self, event):
        self.dialog = MinimalColorPickerDialog(self.hex_color, self.key, self)
        self.dialog.colorSelected.connect(self.on_color_selected)
        QApplication.instance().installEventFilter(self)
        self.dialog.show()

    def eventFilter(self, source, event):
        if event.type() == QEvent.MouseButtonPress:
            if hasattr(self, 'dialog') and self.dialog and self.dialog.isVisible():
                if not self.dialog.geometry().contains(event.globalPos()):
                    self.dialog.reject()
                    QApplication.instance().removeEventFilter(self)
        return super().eventFilter(source, event)

    def on_color_selected(self, key, color):
        if not color.isValid():
             self.set_color("default")
             self.colorChanged.emit(key, "default")
        elif color.isValid():
            self.set_color(color.name())
            self.colorChanged.emit(key, color.name())

    def setEnabled(self, enabled):
        self.hex_input.setEnabled(enabled)
        super().setEnabled(enabled)


class ThemeEditorWidget(QWidget):
    def __init__(self, theme_path, theme_dir, parent=None):
        super(ThemeEditorWidget, self).__init__(parent)
        self.theme_path = theme_path
        self.theme_dir = theme_dir
        self.selected_theme = None
        self.default_theme_path = os.path.abspath(os.path.join(os.path.dirname(theme_path), '..', 'theme', 'default.nss'))
        self.theme_data = {}
        self.backup_theme_data = {}
        self.is_dirty = False
        self.slider_ranges = {
            "border.size": (0, 10), "item.opacity": (0, 100), "item.radius": (0, 3),
            "shadow.size": (0, 30), "shadow.opacity": (0, 100), "separator.size": (0, 40),
            "separator.opacity": (0, 100), "background.opacity": (0, 100), "font.size": (6, 100),
            "border.radius": (0, 3), "item.prefix": (0, 2), "font.weight": (1, 9)
        }
        self.color_pickers = {}
        self._setup_ui()
        self._load_theme()

    def _load_theme(self):
        if os.path.exists(self.theme_path):
            try:
                with open(self.theme_path, 'r') as file:
                    theme_content = file.read()
                self._parse_theme(theme_content)
                self.backup_theme_data = self.theme_data.copy()
                self.is_dirty = False
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
        
        if 'dark' not in self.theme_data:
            self.theme_data['dark'] = 'default'

        new_color_keys = [
            "item.text.normal.disabled", "item.text.select.disabled",
            "item.back.normal", "item.back.normal.disabled", "item.back.select", "item.back.select.disabled",
            "item.border.normal", "item.border.normal.disabled", "item.border.select", "item.border.select.disabled"
        ]
        for key in new_color_keys:
            if key not in self.theme_data:
                self.theme_data[key] = "#ffffff"

    def _setup_ui(self):
        main_layout = QGridLayout(self)
        main_layout.setSpacing(8)

        self.general_frame = self._create_frame(1)
        self.border_frame = self._create_frame(2)
        self.background_frame = self._create_frame(3)
        self.item_text_frame = self._create_frame(4)
        self.image_symbol_frame = self._create_frame(5)
        self.shadow_separator_frame = self._create_frame(6)

        main_layout.addWidget(self.general_frame, 0, 0)
        main_layout.addWidget(self.border_frame, 0, 1)
        main_layout.addWidget(self.background_frame, 0, 2)
        main_layout.addWidget(self.item_text_frame, 1, 0)
        main_layout.addWidget(self.image_symbol_frame, 1, 1)
        main_layout.addWidget(self.shadow_separator_frame, 1, 2)

        self.general_layout = QVBoxLayout(self.general_frame)
        self.border_layout = QVBoxLayout(self.border_frame)
        self.background_layout = QVBoxLayout(self.background_frame)
        self.item_text_layout = QVBoxLayout(self.item_text_frame)
        self.image_symbol_layout = QVBoxLayout(self.image_symbol_frame)
        self.shadow_separator_layout = QVBoxLayout(self.shadow_separator_frame)

        custom_header_layout = QHBoxLayout()
        self.item_tab_button = QPushButton("Item")
        self.item_tab_button.setObjectName("themeTabButton")
        self.item_tab_button.setCheckable(True)
        self.item_tab_button.setChecked(True)
        self.font_tab_button = QPushButton("Font")
        self.font_tab_button.setObjectName("themeTabButton")
        self.font_tab_button.setCheckable(True)

        self.tab_button_group = QButtonGroup()
        self.tab_button_group.setExclusive(True)
        self.tab_button_group.addButton(self.item_tab_button)
        self.tab_button_group.addButton(self.font_tab_button)

        custom_header_layout.addWidget(self.item_tab_button)
        custom_header_layout.addWidget(self.font_tab_button)
        custom_header_layout.addStretch()

        self.item_text_layout.addLayout(custom_header_layout)

        self.item_font_stacked_widget = QStackedWidget()
        self.item_text_layout.addWidget(self.item_font_stacked_widget)

        self.item_sub_tab_widget = QTabWidget()
        self.item_font_stacked_widget.addWidget(self.item_sub_tab_widget)

        self.text_sub_page = QWidget()
        self.text_sub_page_layout = QVBoxLayout(self.text_sub_page)
        self.text_sub_page_layout.setContentsMargins(8, 8, 8, 8)
        self.text_sub_page_layout.setSpacing(5)
        self.item_sub_tab_widget.addTab(self.text_sub_page, "Text")

        self.back_sub_page = QWidget()
        self.back_sub_page_layout = QVBoxLayout(self.back_sub_page)
        self.back_sub_page_layout.setContentsMargins(8, 8, 8, 8)
        self.back_sub_page_layout.setSpacing(5)
        self.item_sub_tab_widget.addTab(self.back_sub_page, "Back")

        self.border_sub_page = QWidget()
        self.border_sub_page_layout = QVBoxLayout(self.border_sub_page)
        self.border_sub_page_layout.setContentsMargins(8, 8, 8, 8)
        self.border_sub_page_layout.setSpacing(5)
        self.item_sub_tab_widget.addTab(self.border_sub_page, "Border")

        self.font_page = QWidget()
        self.font_page_layout = QVBoxLayout(self.font_page)
        self.font_page_layout.setContentsMargins(8, 8, 8, 8)
        self.font_page_layout.setSpacing(5)
        self.item_font_stacked_widget.addWidget(self.font_page)

        self.item_tab_button.clicked.connect(lambda: self.item_font_stacked_widget.setCurrentWidget(self.item_sub_tab_widget))
        self.font_tab_button.clicked.connect(lambda: self.item_font_stacked_widget.setCurrentWidget(self.font_page))

        for layout in [self.general_layout, self.border_layout, self.background_layout,
                      self.image_symbol_layout, self.shadow_separator_layout]:
           layout.setContentsMargins(8, 8, 8, 8)
           layout.setSpacing(5)
        
        

    def _create_frame(self, frame_number):
        frame = QFrame(self)
        frame.setObjectName(f"themeEditorFrame{frame_number}")
        shadow = QGraphicsDropShadowEffect(blurRadius=15, xOffset=5, yOffset=5)
        shadow.setColor(QColor(0, 0, 0, 160))
        frame.setGraphicsEffect(shadow)
        return frame

    def _clear_layout(self, layout):
        if layout is not None:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()
                else:
                    sub_layout = item.layout()
                    if sub_layout is not None:
                        self._clear_layout(sub_layout)

    def _add_font_size_widget(self, layout, display_name, key, value):
        hbox = QHBoxLayout()
        label = QLabel(display_name)

        spinbox = QSpinBox()
        spinbox.setRange(6, 100)
        spinbox.setButtonSymbols(QAbstractSpinBox.NoButtons)
        spinbox.setObjectName("fontSizeSpinBox")

        auto_radio = QRadioButton("Auto")
        auto_radio.setObjectName("themeEditorRadioButton")

        manual_radio = QRadioButton()
        manual_radio.setVisible(False)

        button_group = QButtonGroup(self)
        button_group.addButton(auto_radio)
        button_group.addButton(manual_radio)

        is_auto = (str(value).lower() == "auto")
        if is_auto:
            auto_radio.setChecked(True)
            spinbox.setEnabled(False)
            spinbox.setValue(12)
        else:
            manual_radio.setChecked(True)
            spinbox.setEnabled(True)
            try:
                spinbox.setValue(int(value))
            except (ValueError, TypeError):
                spinbox.setValue(12)

        def on_auto_toggled(checked):
            spinbox.setEnabled(not checked)
            if checked:
                self._update_theme_data(key, "auto")
            else:
                self._update_theme_data(key, spinbox.value())

        auto_radio.toggled.connect(on_auto_toggled)
        spinbox.valueChanged.connect(lambda val: self._update_theme_data(key, val))

        class SpinBoxEventFilter(QObject):
            def eventFilter(self, obj, event):
                if event.type() == QEvent.MouseButtonPress:
                    if not manual_radio.isChecked():
                        manual_radio.setChecked(True)
                return super().eventFilter(obj, event)

        filter = SpinBoxEventFilter(spinbox)
        spinbox.installEventFilter(filter)

        hbox.addWidget(label)
        hbox.addStretch()
        hbox.addWidget(spinbox)
        hbox.addWidget(auto_radio)

        layout.addLayout(hbox)

    def _create_form(self):
        self._clear_layout(self.general_layout)
        self._clear_layout(self.border_layout)
        self._clear_layout(self.background_layout)
        self._clear_layout(self.image_symbol_layout)
        self._clear_layout(self.shadow_separator_layout)
        self._clear_layout(self.font_page_layout)
        self._clear_layout(self.text_sub_page_layout)
        self._clear_layout(self.back_sub_page_layout)
        self._clear_layout(self.border_sub_page_layout)

        self._add_setting_with_label(self.general_layout, "name")
        self._add_setting_with_label(self.general_layout, "view")
        self._add_setting_with_label(self.general_layout, "dark")
        self._add_setting_with_label(self.general_layout, "item.radius")
        self._add_setting_with_label(self.general_layout, "border.radius")

        self._add_setting_with_label(self.border_layout, "border.enabled")
        self._add_setting_with_label(self.border_layout, "border.size")
        self._add_setting_with_label(self.border_layout, "border.color")
        self._add_setting_with_label(self.border_layout, "border.opacity")

        self._add_setting_with_label(self.background_layout, "background.color")
        self._add_setting_with_label(self.background_layout, "background.effect")
        self._add_setting_with_label(self.background_layout, "background.opacity")

       
        self._add_setting_with_label(self.text_sub_page_layout, "item.text.normal")
        self._add_setting_with_label(self.text_sub_page_layout, "item.text.normal.disabled")
        self._add_setting_with_label(self.text_sub_page_layout, "item.text.select")
        self._add_setting_with_label(self.text_sub_page_layout, "item.text.select.disabled")

        self._add_setting_with_label(self.back_sub_page_layout, "item.back.normal")
        self._add_setting_with_label(self.back_sub_page_layout, "item.back.normal.disabled")
        self._add_setting_with_label(self.back_sub_page_layout, "item.back.select")
        self._add_setting_with_label(self.back_sub_page_layout, "item.back.select.disabled")

        self._add_setting_with_label(self.border_sub_page_layout, "item.border.normal")
        self._add_setting_with_label(self.border_sub_page_layout, "item.border.normal.disabled")
        self._add_setting_with_label(self.border_sub_page_layout, "item.border.select")
        self._add_setting_with_label(self.border_sub_page_layout, "item.border.select.disabled")

       
        hbox = QHBoxLayout()
        self._add_setting_with_label(hbox, "image.enabled")
        hbox.addStretch()
        self.image_symbol_layout.addLayout(hbox)
        self._add_setting_with_label(self.image_symbol_layout, "image.color", is_image=True)
        self._add_setting_with_label(self.image_symbol_layout, "symbol.normal")

        
        self._add_setting_with_label(self.shadow_separator_layout, "shadow.enabled")
        self._add_setting_with_label(self.shadow_separator_layout, "shadow.size")
        self._add_setting_with_label(self.shadow_separator_layout, "shadow.opacity")
        self._add_setting_with_label(self.shadow_separator_layout, "shadow.color")
        self._add_setting_with_label(self.shadow_separator_layout, "separator.size")
        self._add_setting_with_label(self.shadow_separator_layout, "separator.color")
        self._add_setting_with_label(self.shadow_separator_layout, "separator.opacity")

        
        self._add_setting_with_label(self.font_page_layout, "font.size")
        self._add_setting_with_label(self.font_page_layout, "font.name")
        self._add_setting_with_label(self.font_page_layout, "font.weight")
        self._add_setting_with_label(self.font_page_layout, "font.italic")

    def _add_background_color_picker(self, layout, display_name, key, value):
        hbox = QHBoxLayout()
        radio_group = QButtonGroup()
        default_radio = QRadioButton("Default")
        default_radio.setChecked(value == 'default')
        default_radio.toggled.connect(lambda checked, k=key: self._toggle_background_default(checked, color_picker) )
        hbox.addWidget(default_radio)
        radio_group.addButton(default_radio)
        color_picker = ColorPickerWidget(value if value != 'default' else "#ffffff", key)
        color_picker.setEnabled(value != 'default')
        color_picker.colorChanged.connect(self._update_background_color)
        hbox.addWidget(color_picker)
        custom_radio = QRadioButton("Custom")
        custom_radio.setChecked(value != 'default')
        hbox.addWidget(custom_radio)
        radio_group.addButton(custom_radio)
        custom_radio.toggled.connect(lambda checked, k=key, cp=color_picker, v=value: self._toggle_background_color(checked, cp, v) )
        hbox.addStretch()
        hbox2 = QVBoxLayout()
        label = QLabel(display_name)
        hbox2.addWidget(label)
        hbox2.addLayout(hbox)
        layout.addLayout(hbox2)

    def _toggle_background_color(self, state, color_picker, value):
        color_picker.setEnabled(state)
        if not state:
           self.theme_data['background.color'] = "default"
           color_picker.set_color("default")
        else:
            self.theme_data["background.color"] = value if value != "default" else "#ffffff"
            color_picker.set_color(value if value != "default" else "#ffffff")

    def _update_background_color(self, key, color):
            self.theme_data[key] = color

    def _toggle_background_default(self, state, color_picker):
         if state:
               color_picker.setEnabled(False)
               color_picker.set_color("default")
               self.theme_data['background.color'] = 'default'
         else:
             color_picker.setEnabled(True)

    def _add_setting_with_label(self, layout, key, is_image = False):
        display_names = {
            "name": "Theme", "border.enabled": "Enable Border",
            "border.size": "Border Size", "border.color": "Border Color",
            "border.opacity": "Border Opacity", "border.radius": "Border Radius",
            "image.enabled": "Enable Image", "image.color": "Image Color",
            "background.color": "Background Color",
            "background.opacity": "Background Opacity", "background.effect": "Background Effect",
            "item.radius": "Item Radius",
            "item.text.normal": "Normal Text",
            "item.text.normal.disabled": "Disabled Normal Text",
            "item.text.select": "Selected Text",
            "item.text.select.disabled": "Disabled Selected Text",
            "item.back.normal": "Normal Background",
            "item.back.normal.disabled": "Disabled Normal Background",
            "item.back.select": "Selected Background",
            "item.back.select.disabled": "Disabled Selected Background",
            "item.border.normal": "Normal Border",
            "item.border.normal.disabled": "Disabled Normal Border",
            "item.border.select": "Selected Border",
            "item.border.select.disabled": "Disabled Selected Border",
            "font.size": "Font Size",
            "font.name": "Font Name", "font.weight": "Bold", "font.italic": "Italic",
            "shadow.enabled": "Enable Shadow", "shadow.size": "Shadow Size",
            "shadow.opacity": "Shadow Opacity", "shadow.color": "Shadow Color",
            "separator.size": "Separator Size", "separator.color": "Separator Color",
            "separator.opacity": "Separator Opacity",  "symbol.normal": "Symbol", "dark": "Dark Mode",
        }
        display_name = display_names.get(key, key)
        value = self.theme_data.get(key)
        if value is None:
            if key.endswith(".enabled") or key == "font.italic":
                value = "false"
            elif key.endswith(".size") or key.endswith(".opacity") or key.endswith(".radius") or key == "font.weight":
                value = "0"
            elif key.endswith(".color") or key.endswith(".normal") or key.endswith(".select"):
                value = "#ffffff"
            elif key == "name":
                value = "auto"
            elif key == "view":
                value = "auto"
            elif key == "font.name":
                value = "Segoe UI Variable Text"
            elif key == "background.effect":
                value = "disabled"
            else:
                value = ""
            self.theme_data[key] = value

        if key == "dark":
            self._add_dropdown(layout, display_name, key, value)
        elif key == "font.size":
            self._add_font_size_widget(layout, display_name, key, value)
        elif key in ["item.opacity", "background.opacity", "border.opacity",
                       "shadow.opacity", "separator.opacity", "border.size",
                       "shadow.size", "separator.size", "border.radius", "item.radius"]:
            min_val, max_val = self.slider_ranges.get(key, (0, 100))
            if key in ["border.size", "shadow.size", "separator.size", "border.radius", "item.radius"]:
                min_val, max_val = self.slider_ranges.get(key, (0, 3)) if key in ["border.radius", "item.radius"] else self.slider_ranges.get(key, (0, 10))
            self._add_slider(layout, display_name, key, int(value), min_val, max_val)
        elif value.lower() in ["true", "false"] and key != "font.italic":
            self._add_checkbox(layout, display_name, key, value.lower() == "true")
        elif (value.startswith("#") or value == "default") and not is_image:
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
            radio_button.setObjectName("themeEditorRadioButton")
            radio_button.setChecked(value == str(i) or option == value)
            radio_group.addButton(radio_button)
            hbox.addWidget(radio_button)
            radio_button.toggled.connect(lambda checked, k=key, v=str(i), o=option: self._update_theme_data(k, v if k == "background.effect" else o) if checked else None )
        hbox.addStretch()
        layout.addLayout(hbox)

    def _add_checkbox(self, layout, display_name, key, checked):
        checkbox = QCheckBox()
        checkbox.setObjectName("themeEditorCheckbox")
        checkbox.setChecked(checked)
        checkbox.stateChanged.connect(lambda state, k=key, chk=checkbox: self._update_theme_data(k, chk.isChecked()))
        hbox = QHBoxLayout()
        hbox.addWidget(checkbox)
        label = QLabel(display_name)
        hbox.addWidget(label)
        hbox.addStretch(1)
        layout.addLayout(hbox)

    def _add_color_picker(self, layout, display_name, key, value):
        hbox = QHBoxLayout()
        color_picker = ColorPickerWidget(value, key)
        color_picker.colorChanged.connect(self._update_theme_data)
        
        label = QLabel(display_name)
        hbox.addWidget(label)
        hbox.addStretch()
        hbox.addWidget(color_picker)
        layout.addLayout(hbox)

    def _add_image_color_picker(self, layout, display_name, key, value):
        try:
            value = eval(value)
        except:
            value = ["#ffffff", "#ffffff"]
        hbox = QHBoxLayout()
        vbox1 = QVBoxLayout()
        vbox2 = QVBoxLayout()
        color_picker_1 = ColorPickerWidget(value[0] if isinstance(value, list) and len(value) > 0 else "#ffffff", key)
        color_picker_1.colorChanged.connect(lambda k, c, i=0: self._update_image_color(k, c, i))
        vbox1.addWidget(color_picker_1)
         
        label = QLabel(display_name + " 1")
        vbox1.addWidget(label, alignment=Qt.AlignCenter)
        color_picker_2 = ColorPickerWidget(value[1] if isinstance(value, list) and len(value) > 1 else "#ffffff", key)
        color_picker_2.colorChanged.connect(lambda k, c, i=1: self._update_image_color(k, c, i))
        vbox2.addWidget(color_picker_2)
        label2 = QLabel(display_name + " 2")
        vbox2.addWidget(label2, alignment=Qt.AlignCenter)
        hbox.addLayout(vbox1)
        hbox.addLayout(vbox2)
        layout.addLayout(hbox)

    def _update_image_color(self, key, color, index):
        try:
            value = eval(self.theme_data.get(key, "['#ffffff', '#ffffff']"))
            if isinstance(value, list) and len(value) > index:
                value[index] = color
                self._update_theme_data(key, str(value))
        except:
             self._update_theme_data(key, "['#ffffff', '#ffffff']")

    def _add_slider(self, layout, display_name, key, value, min_val, max_val):
        hbox = QHBoxLayout()
        label = QLabel(display_name)
        hbox.addWidget(label)
        slider = QSlider(Qt.Horizontal)
        slider.setObjectName("themeEditorSlider")
        slider.setMinimum(min_val)
        slider.setMaximum(max_val)
        slider.setValue(value)
        slider.setLayoutDirection(Qt.LeftToRight)
        label_val = QLabel(str(value))
        label_val.setFixedWidth(30)
        slider.valueChanged.connect(lambda val, k=key, l=label_val, s=slider: self._update_slider_value(k, s.value(), l))
        hbox.addWidget(slider)
        hbox.addWidget(label_val)
        layout.addLayout(hbox)

    def _update_slider_value(self, key, value, label):
        label.setText(str(value))
        self._update_theme_data(key, value)

    def _add_dropdown(self, layout, display_name, key, value):
        hbox = QHBoxLayout()
        label = QLabel(display_name)
        hbox.addWidget(label)
        dropdown = QComboBox()
        dropdown.setObjectName("themeEditorDropdown")
        options = []
        if key == "name":
            options = ["auto", "classic", "white", "black", "modern"]
        elif key == "view":
            options = ["auto", "compact", "small", "medium", "large", "wide"]
        elif key == "font.name":
            options = ["Segoe UI Variable Text", "Comic Sans MS", "Impact", "Arial", "Helvetica", "Times  New Roman", "Courier New",
                        "Calibri", "Cambria", "Garamond", "Georgia", "Tahoma", "Trebuchet MS", "Century Gothic", "Franklin Gothic Medium", "Consolas"]
        elif key == "dark":
            options = ["true", "false", "default"]

        dropdown.addItems(options)
        dropdown.setCurrentText(value.split('.')[-1] if key == "view" else value)
        dropdown.currentTextChanged.connect(lambda text, k=key: self._update_theme_data(k, text if key not in ["view", "dark"] else (f"view.{text}" if key == "view" else text)))
        hbox.addWidget(dropdown)
        hbox.addStretch(1)
        layout.addLayout(hbox)

    def _add_text_input(self, layout, display_name, key, value):
        hbox = QHBoxLayout()
        label = QLabel(display_name)
        hbox.addWidget(label)
        line_edit = QLineEdit(value)
        line_edit.setFixedSize(160, 25)
        line_edit.textChanged.connect(lambda text, k=key: self._update_theme_data(k, text))
        hbox.addWidget(line_edit)
        hbox.addStretch(1)
        layout.addLayout(hbox)

    def _update_theme_data(self, key, value):
        str_value = str(value)
        if isinstance(value, bool):
            str_value = "true" if value else "false"

        if self.theme_data.get(key) == str_value:
            return

        self.theme_data[key] = str_value
        self.is_dirty = True
        self._write_temporary_theme()

    def _write_temporary_theme(self):
        try:
            with open(self.theme_path, 'w') as file:
                file.write("theme\n{\n")
                for key, value in self.theme_data.items():
                   if key == 'image.color':
                        try:
                            color_list = eval(value)
                            if isinstance(color_list, list):
                                formatted_value = f"[{', '.join(c if c != 'default' else '#ffffff' for c in color_list)} ]"
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
            print(f"Error in _write_temporary_theme: {e}")

    def save_theme(self):
        try:
            self._write_temporary_theme()
            self.backup_theme_data = self.theme_data.copy()
            self.is_dirty = False
            return True
        except Exception as e:
            print(f"Error in save_theme: {e}")
            return False

    def reset_theme(self):
        self.theme_data = self.backup_theme_data.copy()
        self._write_temporary_theme()
        self.is_dirty = False
        self._create_form()
        return True

    def revert_changes(self):
        self.theme_data = self.backup_theme_data.copy()
        self._write_temporary_theme()
        self.is_dirty = False

    def reload_theme(self, theme_name=None):
        if theme_name:
            self.selected_theme = theme_name
        self._load_theme()

    def closeEvent(self, event):
        super().closeEvent(event)