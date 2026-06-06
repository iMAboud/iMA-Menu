import sys
import os
import shutil
import json
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QLineEdit, QCheckBox, QSlider, QComboBox, QColorDialog, QGridLayout,
    QFrame, QButtonGroup, QRadioButton, QTabWidget, QScrollArea, QGraphicsDropShadowEffect, QStackedWidget, QDialog,
    QSpinBox, QAbstractSpinBox, QDialogButtonBox, QFileDialog, QListWidget, QListWidgetItem, QSizePolicy
)
from PyQt5.QtGui import QIcon, QColor, QFont, QPainter, QBrush, QPen
from PyQt5.QtCore import Qt, pyqtSignal, QSize, QPoint, QEvent, QTimer, QObject, QRect, QPropertyAnimation, pyqtProperty

from utils import resource_path, get_font_icon, get_mdl2_icon, safe_file_write, get_shell_dll_version

from PyQt5.QtWidgets import QMessageBox

def load_color_palette():
    palette_path = resource_path('color_palette.json')
    if not os.path.exists(palette_path):
        return []
    try:
        with open(palette_path, 'r') as f:
            data = json.load(f)
            return data.get('colors', [])
    except (json.JSONDecodeError, IOError):
        return []

def load_recent_colors():
    recent_path = resource_path('recent_colors.json')
    if not os.path.exists(recent_path):
        return []
    try:
        with open(recent_path, 'r') as f:
            data = json.load(f)
            return data.get('colors', [])
    except (json.JSONDecodeError, IOError):
        return []

def save_recent_color(color_hex):
    recent_colors = load_recent_colors()
    if color_hex in recent_colors:
        recent_colors.remove(color_hex)
    recent_colors.insert(0, color_hex)
    recent_colors = recent_colors[:8] # Keep top 8
    
    recent_path = resource_path('recent_colors.json')
    try:
        with open(recent_path, 'w') as f:
            json.dump({'colors': recent_colors}, f)
    except IOError:
        pass


class EyedropperTool(QWidget):
    colorPicked = pyqtSignal(str)
    closed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setCursor(Qt.CrossCursor)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # Cover all monitors (Virtual Desktop)
        self.setGeometry(QApplication.desktop().geometry())
        
        self.setMouseTracking(True)
        self.current_pos = QPoint(-100, -100)
        self.current_color = QColor(Qt.transparent)

    def paintEvent(self, event):
        painter = QPainter(self)
        # Draw nearly transparent background to ensure mouse events are captured
        painter.fillRect(self.rect(), QColor(0, 0, 0, 1))
        
        if not self.current_color.isValid() or self.current_color == Qt.transparent:
            return

        painter.setRenderHint(QPainter.Antialiasing)
        
        # Coordinates are relative to the virtual desktop's top-left
        origin = self.geometry().topLeft()
        local_pos = self.current_pos - origin
        
        bubble_size = 50
        offset = 20
        bubble_rect = QRect(local_pos.x() + offset, local_pos.y() - bubble_size - offset, bubble_size, bubble_size)
        
        # Ensure bubble stays within the widget bounds
        if bubble_rect.right() > self.width():
            bubble_rect.moveLeft(local_pos.x() - bubble_size - offset)
        if bubble_rect.top() < 0:
            bubble_rect.moveTop(local_pos.y() + offset)

        # Draw preview bubble
        painter.setPen(QPen(QColor(255, 255, 255, 220), 2))
        painter.setBrush(self.current_color)
        painter.drawEllipse(bubble_rect)
        
        painter.setPen(QPen(QColor(0, 0, 0, 120), 1))
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(bubble_rect)

    def mouseMoveEvent(self, event):
        self.current_pos = event.globalPos()
        
        # Use QApplication.screenAt for multi-monitor support
        screen = QApplication.screenAt(self.current_pos)
        if screen:
            # Grab a 1x1 pixel from the screen at cursor position
            # grabWindow takes screen-relative coordinates
            screen_geo = screen.geometry()
            local_x = self.current_pos.x() - screen_geo.x()
            local_y = self.current_pos.y() - screen_geo.y()
            
            pixmap = screen.grabWindow(0, local_x, local_y, 1, 1)
            if not pixmap.isNull():
                img = pixmap.toImage()
                self.current_color = QColor(img.pixel(0, 0))
        
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self.current_color.isValid() and self.current_color != Qt.transparent:
                self.colorPicked.emit(self.current_color.name().lower())
        self.close()

    def closeEvent(self, event):
        self.closed.emit()
        super().closeEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()

class WheelEventFilter(QObject):
    def eventFilter(self, obj, event):
        if event.type() == QEvent.Wheel:
            return True
        return False


class DimmingOverlay(QWidget):
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
        painter.setBrush(QBrush(QColor(0, 0, 0, 150)))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(self.rect(), 20, 20)


class MinimalColorPickerDialog(QDialog):
    colorSelected = pyqtSignal(str, str)

    def __init__(self, initial_color, key, parent=None):
        super().__init__(parent)
        self.key = key
        self.eyedropper_active = False
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)

        initial_color_str = initial_color if initial_color != "default" else "#ffffff"
        if len(initial_color_str) == 9 and initial_color_str.startswith('#'):
            self.base_hex = initial_color_str[:7]
            try:
                self.opacity_val = int(initial_color_str[7:9])
                if self.opacity_val == 0: self.opacity_val = 1
            except:
                self.opacity_val = 100
        elif len(initial_color_str) == 7 and initial_color_str.startswith('#'):
            self.base_hex = initial_color_str
            self.opacity_val = 100
        else:
            self.base_hex = initial_color_str
            self.opacity_val = 100

        self.selected_color = QColor(self.base_hex)
        self._last_hue = -1

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)

        top_bar_layout = QHBoxLayout()
        self.default_checkbox = QCheckBox("Default")
        self.default_checkbox.setObjectName("themeEditorCheckbox")
        self.default_checkbox.setChecked(initial_color == "default")
        self.default_checkbox.setStyleSheet("QCheckBox { color: #b0b0b0; font-weight: bold; } QCheckBox::indicator { width: 18px; height: 18px; border-radius: 9px; border: 2px solid #333333; } QCheckBox::indicator:checked { background: #dc143c; border: 2px solid #dc143c; }")
        top_bar_layout.addWidget(self.default_checkbox)
        top_bar_layout.addStretch()
        self.main_layout.addLayout(top_bar_layout)
        
        self.dimmable_area = QWidget()
        dimmable_layout = QHBoxLayout(self.dimmable_area)
        dimmable_layout.setContentsMargins(0, 0, 0, 0)
        dimmable_layout.setSpacing(15)
        self.main_layout.addWidget(self.dimmable_area)

        self.left_panel_widget = QWidget()
        left_layout = QVBoxLayout(self.left_panel_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)
        dimmable_layout.addWidget(self.left_panel_widget)

        self.color_grid_widget = QWidget()
        self.color_grid = QGridLayout(self.color_grid_widget)
        self.color_grid.setContentsMargins(0, 0, 0, 0)
        self.color_grid.setSpacing(8)
        left_layout.addWidget(self.color_grid_widget)

        colors = load_color_palette()
        row, col = 0, 0
        for color in colors:
            swatch = QPushButton()
            swatch.setFixedSize(28, 28)
            swatch.setCursor(Qt.PointingHandCursor)
            swatch.setStyleSheet(f"QPushButton {{ background-color: {color}; border-radius: 14px; border: 2px solid transparent; }} QPushButton:hover {{ border: 2px solid white; }}")
            swatch.clicked.connect(lambda _, c=color: self.select_color_from_swatch(c))
            self.color_grid.addWidget(swatch, row, col)
            col += 1
            if col > 7:
                col = 0
                row += 1

        self.recent_colors_label = QLabel("Recent Colors")
        self.recent_colors_label.setStyleSheet("color: #b0b0b0; font-size: 11px; font-weight: bold; margin-top: 5px;")
        left_layout.addWidget(self.recent_colors_label)

        self.recent_colors_widget = QWidget()
        self.recent_colors_grid = QHBoxLayout(self.recent_colors_widget)
        self.recent_colors_grid.setContentsMargins(0, 0, 0, 0)
        self.recent_colors_grid.setSpacing(8)
        self.recent_colors_grid.setAlignment(Qt.AlignLeft)
        left_layout.addWidget(self.recent_colors_widget)

        self.refresh_recent_colors()
        left_layout.addStretch()

        self.right_panel_widget = QWidget()
        right_layout = QVBoxLayout(self.right_panel_widget)
        right_layout.setSpacing(15)
        dimmable_layout.addWidget(self.right_panel_widget)

        self.preview = QLabel()
        self.preview.setFixedSize(160, 100)
        right_layout.addWidget(self.preview, alignment=Qt.AlignCenter)

        hex_layout = QHBoxLayout()
        hex_layout.setContentsMargins(0,0,0,0)
        self.hex_input = QLineEdit()
        self.hex_input.setAlignment(Qt.AlignCenter)
        self.hex_input.setStyleSheet("QLineEdit { background: #25252b; color: white; border: 1px solid #555566; border-radius: 6px; padding: 4px; font-family: monospace; font-size: 13px; font-weight: bold; } QLineEdit:focus { border: 1px solid #dc143c; }")
        self.hex_input.textEdited.connect(self.update_color_from_hex)
        
        self.eyedropper_btn = QPushButton("🖌")
        self.eyedropper_btn.setFixedSize(28, 28)
        self.eyedropper_btn.setCursor(Qt.PointingHandCursor)
        self.eyedropper_btn.setToolTip("Pick color from screen")
        self.eyedropper_btn.setStyleSheet("QPushButton { background: rgba(255,255,255,0.05); color: white; border: 1px solid #555566; border-radius: 6px; } QPushButton:hover { background: rgba(255,255,255,0.1); }")
        self.eyedropper_btn.clicked.connect(self.open_eyedropper)
        
        hex_layout.addWidget(self.hex_input)
        hex_layout.addWidget(self.eyedropper_btn)
        right_layout.addLayout(hex_layout)

        slider_layout = QVBoxLayout()
        slider_layout.setSpacing(12)
        right_layout.addLayout(slider_layout)

        self.hue_slider, _ = self._create_slider_with_label(359, "Hue", slider_layout)
        self.sat_slider, _ = self._create_slider_with_label(255, "Saturation", slider_layout)
        self.val_slider, _ = self._create_slider_with_label(255, "Lightness", slider_layout)
        self.opa_slider, self.opa_label = self._create_slider_with_label(100, "Opacity (100%)", slider_layout)
        self.opa_slider.setMinimum(1)
        
        self.hue_slider.valueChanged.connect(self.update_color_from_sliders)
        self.sat_slider.valueChanged.connect(self.update_color_from_sliders)
        self.val_slider.valueChanged.connect(self.update_color_from_sliders)
        self.opa_slider.valueChanged.connect(self.update_color_from_sliders)

        button_box = QDialogButtonBox()
        ok_btn = QPushButton("Apply")
        ok_btn.setFixedSize(100, 36)
        ok_btn.setCursor(Qt.PointingHandCursor)
        ok_btn.setStyleSheet("QPushButton { background: #dc143c; color: #ffffff; font-weight: bold; border-radius: 18px; border: none; } QPushButton:hover { background: #ff2a55; }")
        
        can_btn = QPushButton("Cancel")
        can_btn.setFixedSize(100, 36)
        can_btn.setCursor(Qt.PointingHandCursor)
        can_btn.setStyleSheet("QPushButton { background: rgba(255,255,255,0.05); color: #ffffff; font-weight: bold; border-radius: 18px; border: 1px solid rgba(255,255,255,0.1); } QPushButton:hover { background: rgba(255,255,255,0.1); }")
        
        button_box.addButton(ok_btn, QDialogButtonBox.AcceptRole)
        button_box.addButton(can_btn, QDialogButtonBox.RejectRole)
        button_box.accepted.connect(self.accept_color)
        button_box.rejected.connect(self.reject)
        
        self.main_layout.addSpacing(10)
        self.main_layout.addWidget(button_box, alignment=Qt.AlignCenter)

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

    def _create_slider_with_label(self, max_val, name, layout):
        container = QWidget()
        vbox = QVBoxLayout(container)
        vbox.setContentsMargins(0,0,0,0)
        vbox.setSpacing(4)
        lbl = QLabel(name)
        lbl.setStyleSheet("color: #b0b0b0; font-size: 11px; font-weight: bold;")
        slider = QSlider(Qt.Horizontal)
        slider.setMinimum(0)
        slider.setMaximum(max_val)
        slider.setStyleSheet("""
            QSlider::groove:horizontal { border-radius: 4px; height: 8px; background: rgba(255,255,255,0.1); }
            QSlider::handle:horizontal { background: #dc143c; border-radius: 8px; width: 16px; height: 16px; margin: -4px 0; }
            QSlider::handle:horizontal:hover { background: #ff2a55; width: 20px; height: 20px; border-radius: 10px; margin: -6px 0; }
        """)
        slider.setCursor(Qt.PointingHandCursor)
        vbox.addWidget(lbl)
        vbox.addWidget(slider)
        layout.addWidget(container)
        return slider, lbl

    def accept_color(self):
        if self.default_checkbox.isChecked():
            res_color = "default"
        else:
            res_color = self.selected_color.name()
            if self.opacity_val < 100:
                res_color += f"{self.opacity_val:02d}"
            save_recent_color(self.selected_color.name().lower())
        self.accept()
        self.colorSelected.emit(self.key, res_color)

    def refresh_recent_colors(self):
        for i in reversed(range(self.recent_colors_grid.count())): 
            widget_to_remove = self.recent_colors_grid.itemAt(i).widget()
            self.recent_colors_grid.removeWidget(widget_to_remove)
            widget_to_remove.setParent(None)
            
        recent_colors = load_recent_colors()
        if not recent_colors:
            self.recent_colors_label.hide()
            self.recent_colors_widget.hide()
            return
            
        self.recent_colors_label.show()
        self.recent_colors_widget.show()
        for color in recent_colors:
            swatch = QPushButton()
            swatch.setFixedSize(28, 28)
            swatch.setCursor(Qt.PointingHandCursor)
            swatch.setStyleSheet(f"QPushButton {{ background-color: {color}; border-radius: 14px; border: 2px solid transparent; }} QPushButton:hover {{ border: 2px solid white; }}")
            swatch.clicked.connect(lambda _, c=color: self.select_color_from_swatch(c))
            self.recent_colors_grid.addWidget(swatch)

    def update_color_from_hex(self, text):
        if len(text) == 7 and text.startswith('#'):
            c = QColor(text)
            if c.isValid():
                self.selected_color = c
                self._update_ui_from_color(self.selected_color, update_hex=False)
        elif len(text) == 4 and text.startswith('#'):
            c = QColor(f"#{text[1]*2}{text[2]*2}{text[3]*2}")
            if c.isValid():
                self.selected_color = c
                self._update_ui_from_color(self.selected_color, update_hex=False)

    def select_color_from_swatch(self, color_hex):
        self.selected_color = QColor(color_hex)
        self._update_ui_from_color(self.selected_color)

    def open_eyedropper(self):
        self.eyedropper_active = True
        self.dropper = EyedropperTool()
        self.dropper.colorPicked.connect(self.update_color_from_hex)
        self.dropper.closed.connect(self._on_eyedropper_closed)
        self.dropper.show()
        self.dropper.raise_()
        self.dropper.activateWindow()

    def _on_eyedropper_closed(self):
        self.eyedropper_active = False

    def update_color_from_sliders(self):
        h = self.hue_slider.value()
        s = self.sat_slider.value()
        v = self.val_slider.value()
        self.opacity_val = self.opa_slider.value()
        self.opa_label.setText(f"Opacity ({self.opacity_val}%)")
        if s > 0: self._last_hue = h
        self.selected_color.setHsv(h, s, v)
        self._update_preview()

    def _update_preview(self, update_hex=True):
        if self.opacity_val < 100:
            alpha = int((self.opacity_val / 100.0) * 255)
            preview_color = QColor(self.selected_color)
            preview_color.setAlpha(alpha)
            bg = f"rgba({preview_color.red()}, {preview_color.green()}, {preview_color.blue()}, {preview_color.alpha() / 255.0})"
        else:
            bg = self.selected_color.name()
        self.preview.setStyleSheet(f"background-color: {bg}; border-radius: 20px;")
        if update_hex:
            self.hex_input.setText(self.selected_color.name().lower())

    def _update_ui_from_color(self, color, update_hex=True):
        h, s, v, a = color.getHsv() 
        if h != -1: self._last_hue = h
        self.hue_slider.blockSignals(True)
        self.sat_slider.blockSignals(True)
        self.val_slider.blockSignals(True)
        self.opa_slider.blockSignals(True)
        self.hue_slider.setValue(self._last_hue if h == -1 else h)
        self.sat_slider.setValue(s)
        self.val_slider.setValue(v)
        self.opa_slider.setValue(self.opacity_val)
        self.opa_label.setText(f"Opacity ({self.opacity_val}%)")
        self.hue_slider.blockSignals(False)
        self.sat_slider.blockSignals(False)
        self.val_slider.blockSignals(False)
        self.opa_slider.blockSignals(False)
        self._update_preview(update_hex)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QBrush(QColor("#121212")))
        painter.setPen(QPen(QColor("#dc143c"), 2))
        painter.drawRoundedRect(self.rect().adjusted(1,1,-1,-1), 20, 20)


class ColorPickerWidget(QFrame):
    colorChanged = pyqtSignal(str, str)

    def __init__(self, initial_color='#333333', key=None, display_name="", parent=None):
        super().__init__(parent)
        self.hex_color = initial_color
        self.key = key
        self.display_name = display_name
        self.setCursor(Qt.PointingHandCursor)
        self.setObjectName("ColorPickerWidget")
        self.setFixedHeight(34)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 0, 15, 0)
        
        self.name_label = QLabel(display_name)
        self.name_label.setAttribute(Qt.WA_TransparentForMouseEvents)
        
        self.hex_label = QLabel(initial_color)
        self.hex_label.setAttribute(Qt.WA_TransparentForMouseEvents)
        
        layout.addWidget(self.name_label)
        layout.addStretch()
        layout.addWidget(self.hex_label)
        
        self.set_color(initial_color)

    def set_color(self, hex_color):
        if hex_color == "default":
            self.hex_color = "default"
            bg_color = "rgba(255, 255, 255, 0.05)"
            text_color = "#ffffff"
            self.hex_label.setText("default")
        else:
            self.hex_color = hex_color
            if len(hex_color) == 9 and hex_color.startswith('#'):
                base_hex = hex_color[:7]
                try:
                    opacity_val = int(hex_color[7:9])
                    if opacity_val == 0: opacity_val = 1
                except:
                    opacity_val = 100
            elif len(hex_color) == 7 and hex_color.startswith('#'):
                base_hex = hex_color
                opacity_val = 100
            else:
                base_hex = hex_color
                opacity_val = 100
                
            color_obj = QColor(base_hex)
            if opacity_val < 100 and color_obj.isValid():
                alpha = int((opacity_val / 100.0) * 255)
                color_obj.setAlpha(alpha)
                bg_color = f"rgba({color_obj.red()}, {color_obj.green()}, {color_obj.blue()}, {color_obj.alpha() / 255.0})"
            else:
                bg_color = base_hex if color_obj.isValid() else "rgba(255, 255, 255, 0.05)"

            if color_obj.isValid():
                luminance = 0.299 * color_obj.red() + 0.587 * color_obj.green() + 0.114 * color_obj.blue()
                text_color = "#000000" if luminance > 128 else "#ffffff"
            else:
                text_color = "#ffffff"
            
            self.hex_label.setText(hex_color)
            
        self.setStyleSheet(f"""
            #ColorPickerWidget {{
                background-color: {bg_color};
                border-radius: 17px;
                border: 1px solid rgba(255, 255, 255, 0.1);
            }}
            #ColorPickerWidget:hover {{
                border: 2px solid white;
            }}
            QLabel {{
                color: {text_color};
                font-weight: bold;
                font-size: 11px;
                background: transparent;
            }}
        """)

    def mousePressEvent(self, event):
        self.openColorDialog(event)

    def openColorDialog(self, event):
        self.dialog = MinimalColorPickerDialog(self.hex_color, self.key, self)
        self.dialog.colorSelected.connect(self.on_color_selected)
        QApplication.instance().installEventFilter(self)
        self.dialog.show()

    def eventFilter(self, source, event):
        if event.type() == QEvent.MouseButtonPress:
            if hasattr(self, 'dialog') and self.dialog and self.dialog.isVisible():
                if getattr(self.dialog, 'eyedropper_active', False):
                    return False
                if not self.dialog.geometry().contains(event.globalPos()):
                    self.dialog.reject()
                    QApplication.instance().removeEventFilter(self)
        return super().eventFilter(source, event)

    def on_color_selected(self, key, color_str):
        if color_str == "default":
             self.set_color("default")
             self.colorChanged.emit(key, "default")
        else:
            self.set_color(color_str)
            self.colorChanged.emit(key, color_str)


class ModernToggle(QCheckBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(44, 24)
        self.setCursor(Qt.PointingHandCursor)
        self._position = 4
        self.animation = QPropertyAnimation(self, b"position")
        self.animation.setDuration(150)
        self.toggled.connect(self.start_transition)

    def get_position(self):
        return self._position

    def set_position(self, pos):
        self._position = pos
        self.update()

    position = pyqtProperty(int, get_position, set_position)

    def start_transition(self, checked):
        self.animation.stop()
        self.animation.setStartValue(self._position)
        self.animation.setEndValue(24 if checked else 4)
        self.animation.start()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        
        # Track
        track_rect = QRect(0, 0, 44, 24)
        if self.isChecked():
            p.setBrush(QColor("#dc143c"))
            p.setPen(Qt.NoPen)
        else:
            p.setBrush(QColor(255, 255, 255, 25))
            p.setPen(QPen(QColor(255, 255, 255, 50), 1))
        p.drawRoundedRect(track_rect, 12, 12)
        
        # Thumb
        p.setBrush(QColor("#121212") if self.isChecked() else QColor("#ffffff"))
        p.setPen(Qt.NoPen)
        p.drawEllipse(self._position, 4, 16, 16)

    def hitButton(self, pos):
        return self.rect().contains(pos)


class MinimalSlider(QSlider):
    def __init__(self, orientation=Qt.Horizontal, parent=None):
        super().__init__(orientation, parent)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(24)
        self.setStyleSheet("""
            QSlider::groove:horizontal { border-radius: 4px; height: 8px; background: rgba(255,255,255,0.05); }
            QSlider::handle:horizontal { background: #dc143c; border-radius: 8px; width: 16px; margin: -4px 0; }
            QSlider::handle:horizontal:hover { background: #dc143c; width: 20px; border-radius: 10px; margin: -6px 0; }
        """)


class RadiusPickerWidget(QWidget):
    valueChanged = pyqtSignal(int)

    def __init__(self, current_value=0, max_value=3, parent=None):
        super().__init__(parent)
        self._value = current_value
        self._max = max_value
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        self._buttons = []
        radii_px = [0, 3, 6, 10]
        for i in range(max_value + 1):
            btn = QPushButton()
            btn.setFixedSize(36, 36)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setProperty("radius_val", i)
            btn.setProperty("corner_px", radii_px[min(i, len(radii_px)-1)])
            btn.clicked.connect(lambda _, v=i: self._select(v))
            self._buttons.append(btn)
            layout.addWidget(btn)
        self._update_styles()

    def _select(self, val):
        self._value = val
        self._update_styles()
        self.valueChanged.emit(val)

    def _update_styles(self):
        for btn in self._buttons:
            v = btn.property("radius_val")
            r = btn.property("corner_px")
            selected = v == self._value
            border_color = "#dc143c" if selected else "rgba(255,255,255,0.1)"
            bg = "rgba(220,20,60,0.15)" if selected else "rgba(255,255,255,0.05)"
            btn.setStyleSheet(f"QPushButton {{ background: {bg}; border: 2px solid {border_color}; border-radius: {r}px; }} QPushButton:hover {{ background: rgba(220,20,60,0.25); }}")

    def value(self):
        return self._value


class BorderPreviewWidget(QWidget):
    def __init__(self, border_width=1, border_color="#bf616a", parent=None):
        super().__init__(parent)
        self._border_width = border_width
        self._border_color = border_color
        self.setFixedSize(28, 28)

    def set_border_width(self, w):
        self._border_width = max(0, min(w, 10))
        self.update()

    def set_border_color(self, c):
        self._border_color = c
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setBrush(QBrush(QColor(40, 42, 62)))
        if self._border_width > 0:
            p.setPen(QPen(QColor(self._border_color), self._border_width))
        else:
            p.setPen(Qt.NoPen)
        margin = max(1, self._border_width // 2 + 1)
        p.drawRoundedRect(margin, margin, self.width() - margin * 2, self.height() - margin * 2, 4, 4)
        p.end()


class ThemeEditorWidget(QWidget):
    theme_saved = pyqtSignal()
    reload_requested = pyqtSignal()

    def __init__(self, theme_path, theme_dir, parent=None):
        super(ThemeEditorWidget, self).__init__(parent)
        self.theme_path = theme_path
        self.theme_dir = theme_dir
        self.selected_theme = None
        self.default_theme_path = os.path.abspath(os.path.join(os.path.dirname(theme_path), '..', 'theme', 'default.nss'))
        self.theme_data = {}
        self.backup_theme_data = {}
        self.is_dirty = False
        self.auto_save = False
        self.slider_ranges = {
            "border.size": (0, 10), "item.opacity": (0, 100), "item.radius": (0, 3),
            "shadow.size": (0, 30), "shadow.opacity": (0, 100), "separator.size": (0, 40),
            "separator.opacity": (0, 100), "background.opacity": (0, 100), "font.size": (6, 100),
            "border.radius": (0, 3), "item.prefix": (0, 2), "font.weight": (1, 9)
        }
        self.wheel_filter = WheelEventFilter(self)
        self.reload_timer = QTimer(self)
        self.reload_timer.setSingleShot(True)
        self.reload_timer.timeout.connect(self._trigger_reload)
        self._setup_ui()
        self._load_theme()

    def _load_theme(self):
        if os.path.exists(self.theme_path):
            try:
                with open(self.theme_path, 'r') as file:
                    theme_content = file.read()
                self._parse_theme(theme_content)

                # Compatibility check for shell.dll version
                version = get_shell_dll_version()
                if version[0] < 2:
                    if 'background.image' in self.theme_data:
                        del self.theme_data['background.image']
                        self.is_dirty = True
                        QTimer.singleShot(500, self._write_temporary_theme)
                        QMessageBox.warning(self, "Compatibility Note", 
                            "The 'background.image' feature was removed from your theme because it requires shell.dll version 2.0 or higher.\n"
                            "Please update your shell.dll to use this experimental feature.")

                self.backup_theme_data = self.theme_data.copy()
                self.is_dirty = False
                self._create_form()
            except Exception as e:
                print(f"Failed to load theme: {e}")
                self._create_form()
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
                self.theme_data[key.strip()] = value.strip().strip('"\'')
        
        if 'dark' not in self.theme_data: self.theme_data['dark'] = 'default'
        new_color_keys = [
            "item.text.normal.disabled", "item.text.select.disabled",
            "item.back.normal", "item.back.normal.disabled", "item.back.select", "item.back.select.disabled",
            "item.border.normal", "item.border.normal.disabled", "item.border.select", "item.border.select.disabled",
            "symbol.normal", "symbol.select", "symbol.normal.disabled", "symbol.select.disabled"
        ]
        for key in new_color_keys:
            if key not in self.theme_data:
                self.theme_data[key] = "#ffffff"

    def _setup_ui(self):
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(15, 15, 15, 15)
        self.main_layout.setSpacing(25)

        self.sidebar_layout = QVBoxLayout()
        self.sidebar_layout.setSpacing(12)
        
        sidebar_title = QLabel("Theme Editor")
        sidebar_title.setStyleSheet("font-size: 18px; font-weight: 800; color: #ffffff; margin-left: 10px; margin-bottom: 4px;")
        self.sidebar_layout.addWidget(sidebar_title)

        self.category_list = QListWidget()
        self.category_list.setFixedWidth(220)
        self.category_list.setIconSize(QSize(22, 22))
        self.category_list.setStyleSheet("""
            QListWidget {
                background: #1c1c20;
                border-radius: 16px;
                border: 1px solid rgba(255, 255, 255, 0.05);
                padding: 8px;
                outline: none;
            }
            QListWidget::item {
                color: #b0b0b0;
                padding: 10px 14px;
                border-radius: 12px;
                margin: 2px 0px;
                font-size: 13px;
                font-weight: 600;
            }
            QListWidget::item:selected {
                background: rgba(220, 20, 60, 0.15);
                color: #dc143c;
            }
            QListWidget::item:hover:!selected {
                background: rgba(255, 255, 255, 0.05);
                color: #ffffff;
            }
        """)
        self.sidebar_layout.addWidget(self.category_list)
        self.main_layout.addLayout(self.sidebar_layout)

        self.content_area = QStackedWidget()
        self.content_area.setStyleSheet("background: transparent;")
        self.main_layout.addWidget(self.content_area, 1)

        self.category_list.currentRowChanged.connect(self.content_area.setCurrentIndex)

    def _parse_nss_array(self, value):
        if not value or not isinstance(value, str): return value
        val = value.strip()
        if val.startswith('[') and val.endswith(']'):
            return [p.strip().strip("'").strip('"') for p in val[1:-1].split(',')]
        return [val]

    def _create_category_page(self, title):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(20)

        header = QLabel(title)
        header.setStyleSheet("font-size: 22px; font-weight: 800; color: #ffffff;")
        layout.addWidget(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("""
            QScrollArea { background: rgba(0, 0, 0, 0.2); border-radius: 20px; border: 1px solid rgba(255, 255, 255, 0.05); } 
            QScrollBar:vertical { width: 8px; background: transparent; border-radius: 4px; } 
            QScrollBar::handle:vertical { background: rgba(255,255,255,0.2); border-radius: 4px; }
            QScrollBar::handle:vertical:hover { background: rgba(255,255,255,0.3); }
        """)
        
        content = QWidget()
        content.setStyleSheet("background: transparent;")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(15, 15, 25, 20)
        content_layout.setSpacing(20)
        scroll.setWidget(content)
        
        layout.addWidget(scroll)
        return page, content_layout

    def _create_card(self, title):
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #202024;
                border-radius: 20px;
                border: 1px solid rgba(255, 255, 255, 0.04);
            }
        """)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        if title:
            title_lbl = QLabel(title.upper())
            title_lbl.setStyleSheet("font-size: 12px; font-weight: 700; color: #dc143c; border: none;")
            layout.addWidget(title_lbl)

        settings_container = QWidget()
        settings_container.setStyleSheet("background: transparent; border: none;")
        settings_layout = QVBoxLayout(settings_container)
        settings_layout.setContentsMargins(0, 0, 0, 0)
        settings_layout.setSpacing(16)
        layout.addWidget(settings_container)

        return card, settings_layout

    def _create_form(self):
        current_row = self.category_list.currentRow()
        
        scroll_positions = {}
        for i in range(self.category_list.count()):
            cat_name = self.category_list.item(i).text()
            page = self.content_area.widget(i)
            if page and page.layout():
                for j in range(page.layout().count()):
                    widget = page.layout().itemAt(j).widget()
                    if isinstance(widget, QScrollArea):
                        scroll_positions[cat_name] = widget.verticalScrollBar().value()
        
        self.category_list.clear()
        while self.content_area.count() > 0:
            widget = self.content_area.widget(0)
            self.content_area.removeWidget(widget)
            widget.deleteLater()
            
        categories = {
            "General": (0xE115, {
                "": ["name", "view", "dark"],
                "Border Padding": []
            }),
            "Background": (0xEB9F, {
                "": ["background.color", "background.image", "background.effect", "background.opacity"]
            }),
            "Items": (0xE71D, {
                "Dimensions": ["item.radius"],
                "Colors": ["item.text.normal", "item.text.select", "item.text.normal.disabled", "item.text.select.disabled"],
                "Background": ["item.back.normal", "item.back.select", "item.back.normal.disabled", "item.back.select.disabled"]
            }),
            "Borders": (0xE7C4, {
                "Menu Border": ["border.enabled", "border.size", "border.radius", "border.color", "border.opacity"],
                "Item Borders": ["item.border.normal", "item.border.select", "item.border.normal.disabled", "item.border.select.disabled"]
            }),
            "Shadow & Separator": (0xE81E, {
                "Shadow": ["shadow.enabled", "shadow.size", "shadow.color", "shadow.opacity"],
                "Separator": ["separator.size", "separator.color", "separator.opacity"]
            }),
            "Typography & Icons": (0xE8D2, {
                "Typography": ["font.name", "font.size", "font.weight", "font.italic"],
                "Icons": ["image.enabled", "image.color", "symbol.normal"]
            })
        }

        for cat_name, (icon_code, groups) in categories.items():
            item = QListWidgetItem(get_mdl2_icon(icon_code, 22, '#ffffff'), cat_name)
            self.category_list.addItem(item)
            page, page_layout = self._create_category_page(cat_name)
            
            for group_name, keys in groups.items():
                card, card_settings_layout = self._create_card(group_name)
                
                if group_name == "Border Padding":
                    layout = self._create_padding_cross_layout()
                    card_settings_layout.addLayout(layout)
                elif len(keys) == 4 and group_name in ["Colors", "Background", "Item Borders"]:
                    grid_layout = QGridLayout()
                    grid_layout.setSpacing(10)
                    for i, key in enumerate(keys):
                        widget = self._create_setting_row(key, is_image=False, grid_mode=True)
                        grid_layout.addWidget(widget, i // 2, i % 2)
                    card_settings_layout.addLayout(grid_layout)
                else:
                    for key in keys:
                        is_image = (key == "image.color")
                        row_layout = self._create_setting_row(key, is_image=is_image, grid_mode=False)
                        card_settings_layout.addLayout(row_layout)
                page_layout.addWidget(card)
                
            page_layout.addStretch()
            self.content_area.addWidget(page)
            
            if cat_name in scroll_positions:
                for j in range(page.layout().count()):
                    widget = page.layout().itemAt(j).widget()
                    if isinstance(widget, QScrollArea):
                        QTimer.singleShot(0, lambda w=widget, v=scroll_positions[cat_name]: w.verticalScrollBar().setValue(v))
            
        if self.category_list.count() > 0:
            if current_row >= 0 and current_row < self.category_list.count():
                self.category_list.setCurrentRow(current_row)
            else:
                self.category_list.setCurrentRow(0)

    def _create_padding_cross_layout(self):
        layout = QGridLayout()
        layout.setContentsMargins(20, 10, 20, 10)
        layout.setSpacing(10)
        
        keys = ["border.padding.top", "border.padding.bottom", "border.padding.left", "border.padding.right"]
        defaults = {"border.padding.top": 5, "border.padding.bottom": 5, "border.padding.left": 0, "border.padding.right": 0}
        
        for k in keys:
            if k not in self.theme_data:
                self.theme_data[k] = str(defaults[k])
                
        def make_padding_slider(name, key):
            container = QWidget()
            vbox = QVBoxLayout(container)
            vbox.setContentsMargins(0, 0, 0, 0)
            vbox.setSpacing(4)
            
            lbl = QLabel(name)
            lbl.setStyleSheet("color: #b0b0b0; font-size: 12px; font-weight: bold;")
            lbl.setAlignment(Qt.AlignCenter)
            
            control_layout = QHBoxLayout()
            control_layout.setSpacing(8)
            control_layout.setAlignment(Qt.AlignCenter)
            
            try:
                val = int(float(self.theme_data.get(key, defaults[key])))
            except ValueError:
                val = defaults[key]
                
            val_lbl = QLabel(str(val))
            val_lbl.setFixedWidth(25)
            val_lbl.setStyleSheet("color: #dc143c; font-weight: bold; font-size: 13px;")
            val_lbl.setAlignment(Qt.AlignCenter)
            
            btn_style = "QPushButton { background: rgba(255,255,255,0.05); color: white; border: 1px solid rgba(255,255,255,0.1); border-radius: 4px; font-weight: 900; font-size: 12px; } QPushButton:hover { background: rgba(255,255,255,0.1); }"
            
            left_btn = QPushButton("❮")
            left_btn.setFixedSize(24, 24)
            left_btn.setCursor(Qt.PointingHandCursor)
            left_btn.setStyleSheet(btn_style)
            
            right_btn = QPushButton("❯")
            right_btn.setFixedSize(24, 24)
            right_btn.setCursor(Qt.PointingHandCursor)
            right_btn.setStyleSheet(btn_style)
            
            def update_val(delta, l_lbl=val_lbl, k=key):
                curr = int(l_lbl.text())
                new_val = max(0, min(100, curr + delta))
                self._update_slider_value(k, new_val, l_lbl, trigger_reload=True)
                
            def setup_accel_btn(btn, delta):
                btn.timer = QTimer(btn)
                btn.interval = 300
                
                def on_timeout():
                    update_val(delta)
                    btn.interval = max(20, int(btn.interval * 0.85))
                    btn.timer.setInterval(btn.interval)
                    
                def on_pressed():
                    update_val(delta)
                    btn.interval = 300
                    btn.timer.start(btn.interval)
                    
                def on_released():
                    btn.timer.stop()
                    
                btn.pressed.connect(on_pressed)
                btn.released.connect(on_released)
                btn.timer.timeout.connect(on_timeout)

            setup_accel_btn(left_btn, -1)
            setup_accel_btn(right_btn, 1)
            
            control_layout.addWidget(left_btn)
            control_layout.addWidget(val_lbl)
            control_layout.addWidget(right_btn)
            
            vbox.addWidget(lbl)
            vbox.addLayout(control_layout)
            return container

        top_w = make_padding_slider("UP", "border.padding.top")
        left_w = make_padding_slider("LEFT", "border.padding.left")
        right_w = make_padding_slider("RIGHT", "border.padding.right")
        bottom_w = make_padding_slider("DOWN", "border.padding.bottom")
        
        layout.addWidget(top_w, 0, 1, Qt.AlignCenter)
        layout.addWidget(left_w, 1, 0, Qt.AlignCenter)
        layout.addWidget(right_w, 1, 2, Qt.AlignCenter)
        layout.addWidget(bottom_w, 2, 1, Qt.AlignCenter)
        
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 1)
        layout.setColumnStretch(2, 1)
        
        return layout

    def _create_setting_row(self, key, is_image=False, grid_mode=False):
        display_names = {
            "name": "Theme Mode", "border.enabled": "Enable Border",
            "border.size": "Border Size", "border.color": "Border Color",
            "border.opacity": "Border Opacity", "border.radius": "Border Radius",
            "image.enabled": "Enable Image", "image.color": "Image Color",
            "background.color": "Background Color", "background.image": "Background Image",
            "background.opacity": "Background Opacity", "background.effect": "Background Effect",
            "item.radius": "Item Radius",
            "item.text.normal": "Normal Text", "item.text.normal.disabled": "Disabled Text",
            "item.text.select": "Selected Text", "item.text.select.disabled": "Disabled Selected Text",
            "item.back.normal": "Normal BG", "item.back.normal.disabled": "Disabled BG",
            "item.back.select": "Selected BG", "item.back.select.disabled": "Disabled Selected BG",
            "item.border.normal": "Normal Border", "item.border.normal.disabled": "Disabled Border",
            "item.border.select": "Selected Border", "item.border.select.disabled": "Disabled Selected Border",
            "font.size": "Font Size", "font.name": "Font Name", "font.weight": "Bold", "font.italic": "Italic",
            "shadow.enabled": "Enable Shadow", "shadow.size": "Shadow Size",
            "shadow.opacity": "Shadow Opacity", "shadow.color": "Shadow Color",
            "separator.size": "Separator Size", "separator.color": "Separator Color",
            "separator.opacity": "Separator Opacity", "symbol.normal": "Symbol", "dark": "Dark Mode",
        }
        display_name = display_names.get(key, key)
        value = self.theme_data.get(key)
        
        # Init defaults
        if value is None:
            if key.endswith(".enabled") or key in ["font.italic", "font.weight"]: value = "false"
            elif key.endswith(".size") or key.endswith(".opacity") or key.endswith(".radius"): value = "0"
            elif key.endswith(".color") or key.endswith(".normal") or key.endswith(".select"): value = "#ffffff"
            elif key == "name" or key == "view": value = "auto"
            elif key == "font.name": value = "Segoe UI Variable Text"
            elif key == "background.effect": value = "disabled"
            else: value = ""
            self.theme_data[key] = value

        if grid_mode:
            # In grid mode, we just return the ColorPickerWidget directly, without the row label
            widget = ColorPickerWidget(value, key, display_name)
            widget.colorChanged.connect(self._update_theme_data)
            return widget

        row_layout = QHBoxLayout()
        row_layout.setContentsMargins(0, 4, 0, 4)
        
        label = QLabel(display_name)
        label.setStyleSheet("color: #b0b0b0; font-size: 13px; font-weight: 500;")
        row_layout.addWidget(label)
        row_layout.addStretch()

        control_layout = QHBoxLayout()
        control_layout.setSpacing(10)
        control_layout.setAlignment(Qt.AlignRight)

        if key == "dark":
            self._add_dropdown(control_layout, key, value)
        elif key == "font.size":
            self._add_font_size_widget(control_layout, key, value)
        elif key in ["border.radius", "item.radius"]:
            try:
                val_int = int(float(value))
            except ValueError:
                val_int = 0
            self._add_radius_picker(control_layout, key, val_int)
        elif key in ["item.opacity", "background.opacity", "border.opacity", "shadow.opacity", "separator.opacity", "border.size", "shadow.size", "separator.size"]:
            min_val, max_val = self.slider_ranges.get(key, (0, 100))
            if key in ["border.size", "shadow.size", "separator.size"]:
                min_val, max_val = self.slider_ranges.get(key, (0, 10))
            try:
                val_int = int(float(value))
            except ValueError:
                val_int = 0
            self._add_slider(control_layout, key, val_int, min_val, max_val, show_preview=(key == "border.size"))
        elif str(value).lower() in ["true", "false"] and key != "font.italic":
            self._add_checkbox(control_layout, key, str(value).lower() == "true")
        elif (str(value).startswith("#") or str(value) == "default") and not is_image:
            self._add_color_picker(control_layout, key, display_name, value)
        elif key == "font.italic" or key == "font.weight":
            self._add_checkbox(control_layout, key, str(value).lower() == "true" or str(value).lower() == "bold")
        elif key in ["name", "font.name", "view"]:
            self._add_dropdown(control_layout, key, value)
        elif is_image and key == "image.color":
            self._add_image_color_picker(control_layout, key, value)
        elif key == "background.color":
            self._add_background_color_picker(control_layout, key, value)
        elif key == "background.image":
            self._add_image_path_selector(control_layout, key, value)
        elif key == "background.effect":
            self._add_radio_switcher(control_layout, key, value)
        else:
            self._add_text_input(control_layout, key, value)

        row_layout.addLayout(control_layout)
        return row_layout

    def _add_font_size_widget(self, layout, key, value):
        spinbox = QSpinBox()
        spinbox.setRange(6, 100)
        spinbox.setButtonSymbols(QAbstractSpinBox.NoButtons)
        spinbox.setFixedSize(50, 34)
        spinbox.setAlignment(Qt.AlignCenter)
        spinbox.setStyleSheet("QSpinBox { background: rgba(255,255,255,0.05); color: #ffffff; border-radius: 17px; font-weight: bold; font-size: 13px; border: 1px solid rgba(255,255,255,0.1); } QSpinBox:focus { background: rgba(255,255,255,0.1); border: 1px solid #dc143c; } QSpinBox:disabled { background: rgba(0,0,0,0.2); color: rgba(255,255,255,0.2); border: 1px solid rgba(255,255,255,0.05); }")
        spinbox.installEventFilter(self.wheel_filter)

        auto_check = ModernToggle()
        
        is_auto = (str(value).lower() == "auto")
        if is_auto:
            auto_check.setChecked(True)
            auto_check.set_position(24)
            spinbox.setEnabled(False)
            spinbox.setValue(12)
        else:
            auto_check.setChecked(False)
            auto_check.set_position(4)
            spinbox.setEnabled(True)
            try: spinbox.setValue(int(value))
            except: spinbox.setValue(12)

        def on_auto_toggled(state):
            spinbox.setEnabled(not state)
            if state: self._update_theme_data(key, "auto")
            else: self._update_theme_data(key, spinbox.value())

        auto_check.toggled.connect(on_auto_toggled)
        spinbox.valueChanged.connect(lambda val: self._update_theme_data(key, val))

        auto_label = QLabel("Auto")
        auto_label.setStyleSheet("color: #b0b0b0; font-weight: 500; font-size: 13px;")

        layout.addWidget(spinbox)
        layout.addWidget(auto_check)
        layout.addWidget(auto_label)

    def _add_background_color_picker(self, layout, key, value):
        radio_group = QButtonGroup()
        
        default_radio = QRadioButton("Default")
        default_radio.setStyleSheet("QRadioButton { color: #b0b0b0; font-weight: bold; margin-right: 5px; } QRadioButton::indicator { width: 16px; height: 16px; border-radius: 9px; border: 2px solid #333333; background: rgba(255,255,255,0.05); } QRadioButton::indicator:checked { background: #dc143c; border: 4px solid #121212; } QRadioButton:hover { color: #ffffff; }")
        default_radio.setChecked(value == 'default')
        radio_group.addButton(default_radio)
        layout.addWidget(default_radio)

        custom_radio = QRadioButton("Custom")
        custom_radio.setStyleSheet("QRadioButton { color: #b0b0b0; font-weight: bold; margin-right: 5px; } QRadioButton::indicator { width: 16px; height: 16px; border-radius: 9px; border: 2px solid #333333; background: rgba(255,255,255,0.05); } QRadioButton::indicator:checked { background: #dc143c; border: 4px solid #121212; } QRadioButton:hover { color: #ffffff; }")
        custom_radio.setChecked(value != 'default')
        radio_group.addButton(custom_radio)
        layout.addWidget(custom_radio)
        
        color_picker = ColorPickerWidget(value if value != 'default' else "#ffffff", key, "Color")
        color_picker.colorChanged.connect(self._update_background_color)
        color_picker.setEnabled(value != 'default')
        layout.addWidget(color_picker)
        
        default_radio.toggled.connect(lambda checked, k=key: self._toggle_background_default(checked, color_picker) )
        custom_radio.toggled.connect(lambda checked, k=key, cp=color_picker, v=value: self._toggle_background_color(checked, cp, v) )

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

    def _add_radio_switcher(self, layout, key, value):
        radio_group = QButtonGroup()
        options = ["disabled", "transparent", "blur", "acrylic"] if key == "background.effect" else ["auto", "display", "ignore"]
        for i, option in enumerate(options):
            radio_button = QRadioButton(option.title())
            radio_button.setStyleSheet("QRadioButton { color: #b0b0b0; font-weight: bold; margin-right: 5px; } QRadioButton::indicator { width: 16px; height: 16px; border-radius: 9px; border: 2px solid #333333; background: rgba(255,255,255,0.05); } QRadioButton::indicator:checked { background: #dc143c; border: 4px solid #121212; } QRadioButton:hover { color: #ffffff; }")
            radio_button.setChecked(value == str(i) or option == value)
            radio_group.addButton(radio_button)
            layout.addWidget(radio_button)
            radio_button.toggled.connect(lambda checked, k=key, v=str(i), o=option: self._update_theme_data(k, v if k == "background.effect" else o) if checked else None )

    def _add_checkbox(self, layout, key, checked):
        toggle = ModernToggle()
        toggle.setChecked(checked)
        toggle.set_position(24 if checked else 4) # Ensure immediate visual state update
        toggle.stateChanged.connect(lambda state, k=key, chk=toggle: self._update_theme_data(k, chk.isChecked()))
        layout.addWidget(toggle)

    def _add_color_picker(self, layout, key, display_name, value):
        color_picker = ColorPickerWidget(value, key, display_name)
        color_picker.colorChanged.connect(self._update_theme_data)
        layout.addWidget(color_picker)

    def _add_image_color_picker(self, layout, key, value):
        color_list = self._parse_nss_array(value)
        if not color_list: color_list = ["#ffffff", "#ffffff"]
        while len(color_list) < 2: color_list.append("#ffffff")
        for i in range(2):
            cp = ColorPickerWidget(color_list[i], key, f"Color {i+1}")
            cp.colorChanged.connect(lambda k, c, idx=i: self._update_image_color(k, c, idx))
            layout.addWidget(cp)

    def _update_image_color(self, key, color, index):
        color_list = self._parse_nss_array(self.theme_data.get(key, "[#ffffff, #ffffff]"))
        while len(color_list) < 2: color_list.append("#ffffff")
        if index < len(color_list):
            color_list[index] = color
            self._update_theme_data(key, f"[{', '.join(color_list)}]")

    def _add_radius_picker(self, layout, key, value):
        max_val = self.slider_ranges.get(key, (0, 3))[1]
        picker = RadiusPickerWidget(value, max_val)
        picker.valueChanged.connect(lambda val, k=key: self._update_theme_data(k, val))
        layout.addWidget(picker)

    def _add_slider(self, layout, key, value, min_val, max_val, show_preview=False):
        label_val = QLabel(str(value))
        label_val.setFixedSize(30, 20)
        label_val.setAlignment(Qt.AlignCenter)
        label_val.setStyleSheet("color: #dc143c; font-weight: 700; font-size: 12px;")

        slider = MinimalSlider(Qt.Horizontal)
        slider.setFixedWidth(120)
        slider.installEventFilter(self.wheel_filter)
        slider.setMinimum(min_val)
        slider.setMaximum(max_val)
        slider.setValue(value)

        preview = None
        if show_preview:
            border_color = self.theme_data.get("border.color", "#bf616a")
            preview = BorderPreviewWidget(value, border_color)
            slider.valueChanged.connect(lambda val, p=preview: p.set_border_width(val))

        slider.valueChanged.connect(lambda val, k=key, l=label_val, s=slider: self._update_slider_value(k, s.value(), l, trigger_reload=False))
        
        if preview:
            layout.addWidget(preview)
        layout.addWidget(slider)
        layout.addWidget(label_val)

    def _update_slider_value(self, key, value, label, trigger_reload=True):
        label.setText(str(value))
        self._update_theme_data(key, value, trigger_reload=False)
        self.reload_timer.stop()
        self.reload_timer.start(250)

    def _trigger_reload(self):
        if not self.auto_save: self._write_temporary_theme()
        else: self.save_theme()

    def _add_dropdown(self, layout, key, value):
        dropdown = QComboBox()
        dropdown.setFixedHeight(34)
        dropdown.setCursor(Qt.PointingHandCursor)
        dropdown.setStyleSheet("""
            QComboBox { background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 17px; color: white; padding: 0 35px 0 15px; min-width: 120px; font-weight: 500; font-size: 13px; }
            QComboBox:hover { background: rgba(255, 255, 255, 0.1); border: 1px solid rgba(255, 255, 255, 0.2); }
            QComboBox:focus { border: 1px solid #dc143c; }
            QComboBox::drop-down { border: none; width: 30px; }
            QComboBox::down-arrow { image: none; border-left: 5px solid transparent; border-right: 5px solid transparent; border-top: 5px solid #b0b0b0; margin-right: 10px; }
            QComboBox::down-arrow:hover { border-top: 5px solid #ffffff; }
            QComboBox QAbstractItemView { background: #121212; color: white; selection-background-color: rgba(220, 20, 60, 0.2); selection-color: #dc143c; border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 12px; outline: none; padding: 5px; }
            QComboBox QAbstractItemView::item { padding: 8px 12px; border-radius: 8px; margin: 2px; }
        """)
        options = []
        if key == "name": options = ["auto", "classic", "white", "black", "modern"]
        elif key == "view": options = ["auto", "compact", "small", "medium", "large", "wide"]
        elif key == "font.name": options = ["Segoe UI Variable Text", "Comic Sans MS", "Impact", "Arial", "Helvetica", "Times New Roman", "Courier New", "Calibri", "Cambria", "Garamond", "Georgia", "Tahoma", "Trebuchet MS", "Century Gothic", "Franklin Gothic Medium", "Consolas"]
        elif key == "dark": options = ["true", "false", "default"]

        dropdown.addItems(options)
        dropdown.setCurrentText(value.split('.')[-1] if key == "view" else value)
        dropdown.currentTextChanged.connect(lambda text, k=key: self._update_theme_data(k, text if key not in ["view", "dark"] else (f"view.{text}" if key == "view" else text)))
        layout.addWidget(dropdown)

    def _add_text_input(self, layout, key, value):
        line_edit = QLineEdit(value)
        line_edit.setFixedSize(140, 34)
        line_edit.setStyleSheet("QLineEdit { background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 17px; color: white; padding: 0 15px; font-size: 13px; } QLineEdit:hover { background: rgba(255, 255, 255, 0.08); border: 1px solid rgba(255, 255, 255, 0.2); } QLineEdit:focus { border: 1px solid #dc143c; background: rgba(0, 0, 0, 0.2); }")
        line_edit.textChanged.connect(lambda text, k=key: self._update_theme_data(k, text))
        layout.addWidget(line_edit)

    def _add_image_path_selector(self, layout, key, value):
        clear_btn = QPushButton("✕")
        clear_btn.setFixedSize(24, 24)
        clear_btn.setCursor(Qt.PointingHandCursor)
        clear_btn.setStyleSheet("QPushButton { background: rgba(255, 255, 255, 0.05); border-radius: 12px; border: 1px solid rgba(255, 255, 255, 0.1); color: #888888; font-size: 10px; font-weight: bold; } QPushButton:hover { background: #dc143c; color: white; border: none; }")

        line_edit = QLineEdit(value)
        line_edit.setFixedSize(180, 34)
        line_edit.setStyleSheet("QLineEdit { background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 17px; color: white; padding: 0 15px; font-size: 13px; } QLineEdit:hover { background: rgba(255, 255, 255, 0.08); border: 1px solid rgba(255, 255, 255, 0.2); } QLineEdit:focus { border: 1px solid #dc143c; background: rgba(0, 0, 0, 0.2); }")
        line_edit.textChanged.connect(lambda text, k=key: self._update_theme_data(k, text))

        clear_btn.clicked.connect(lambda: line_edit.setText(""))

        layout.addWidget(clear_btn)
        layout.addWidget(line_edit)

        browse_btn = QPushButton(get_mdl2_icon(0xE838, 16), "")
        browse_btn.setFixedSize(34, 34)
        browse_btn.setCursor(Qt.PointingHandCursor)
        browse_btn.setStyleSheet("QPushButton { background: rgba(255, 255, 255, 0.05); border-radius: 17px; border: 1px solid rgba(255, 255, 255, 0.1); color: #ffffff; } QPushButton:hover { background: #dc143c; color: #ffffff; border: none; }")
        browse_btn.clicked.connect(lambda: self._browse_image(line_edit))
        layout.addWidget(browse_btn)

    def _browse_image(self, line_edit):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Image", "", "Images (*.png *.jpg *.jpeg *.bmp *.gif)")
        if file_path:
            line_edit.setText(file_path)

    def _update_theme_data(self, key, value, trigger_reload=True):
        str_value = str(value)
        if isinstance(value, bool) and key != "font.weight":
            str_value = "true" if value else "false"
        if key == "font.weight" and isinstance(value, bool):
             str_value = "7" if value else "4"
        
        if key == "background.image" and str_value.strip():
            version = get_shell_dll_version()
            if version[0] < 2:
                if not hasattr(self, '_notified_bg_image_compat') or not self._notified_bg_image_compat:
                    QMessageBox.information(self, "Update Required", "The 'background.image' feature requires shell.dll version 2.0 or higher.\nPlease update your shell.dll to use this experimental feature.")
                    self._notified_bg_image_compat = True
        
        if self.theme_data.get(key) == str_value:
            return

        self.theme_data[key] = str_value
        self.is_dirty = True
        if trigger_reload:
            self.reload_timer.stop()
            self.reload_timer.start(250)

    def _write_temporary_theme(self):
        def format_image_color(value): return value
        def format_string(value): return f'"{value}"'
        def format_single_quote(value): return f"'{value}'"

        formatters = {
            'image.color': format_image_color,
            'name': format_string,
            'font.name': format_string,
            'background.image': format_single_quote,
        }

        try:
            content = "theme\n{\n"
            keys = list(self.theme_data.keys())
            
            # Compatibility check for shell.dll version
            version = get_shell_dll_version()
            if version[0] < 2:
                if 'background.image' in keys:
                    keys.remove('background.image')

            if 'background.color' in keys and 'background.image' in keys:
                keys.remove('background.image')
                idx = keys.index('background.color')
                keys.insert(idx + 1, 'background.image')

            for key in keys:
                value = self.theme_data[key]
                if key == 'background.image' and not value.strip():
                    continue
                formatter = formatters.get(key, lambda v: v)
                formatted_value = formatter(value)
                content += f"  {key} = {formatted_value}\n"
            content += "}\n"
            
            self.ignore_external_reload = True
            
            def on_success(fp): 
                self.reload_requested.emit()
                QTimer.singleShot(1000, lambda: setattr(self, 'ignore_external_reload', False))
            def on_error(fp, err): 
                print(f"Async Write Error: {err}")
                self.ignore_external_reload = False
                
            from utils import global_undo_stack, FileChangeCommand
            with open(self.theme_path, 'r', encoding='utf-8') as f:
                old_content = f.read()
            cmd = FileChangeCommand(self.theme_path, old_content, content, on_success, on_error)
            global_undo_stack.push(cmd)
        except Exception as e:
            print(f"Error in _write_temporary_theme: {e}")
            self.ignore_external_reload = False

    def save_theme(self):
        try:
            self._write_temporary_theme()
            self.backup_theme_data = self.theme_data.copy()
            self.is_dirty = False
            self.theme_saved.emit()
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
        if getattr(self, 'ignore_external_reload', False):
            return
        if theme_name: self.selected_theme = theme_name
        self._load_theme()

    def closeEvent(self, event):
        super().closeEvent(event)