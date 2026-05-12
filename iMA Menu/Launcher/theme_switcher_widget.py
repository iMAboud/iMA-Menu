import sys
import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTabBar,
    QScrollArea, QFrame, QButtonGroup, QGridLayout, QPushButton, QGraphicsDropShadowEffect, QLayout, QSizePolicy
)
from PyQt5.QtGui import QPixmap, QIcon, QCursor, QColor
from PyQt5.QtCore import Qt, QSize, pyqtSignal, QRect, QPoint
from utils import safe_file_write



class FlowLayout(QLayout):
    def __init__(self, parent=None, margin=0, spacing=-1):
        super(FlowLayout, self).__init__(parent); self.setContentsMargins(margin, margin, margin, margin) if parent else None; self.setSpacing(spacing); self.itemList = []
    def __del__(self):
        item = self.takeAt(0)
        while item: item = self.takeAt(0)
    def addItem(self, item): self.itemList.append(item)
    def count(self): return len(self.itemList)
    def itemAt(self, index): return self.itemList[index] if 0 <= index < len(self.itemList) else None
    def takeAt(self, index): return self.itemList.pop(index) if 0 <= index < len(self.itemList) else None
    def expandingDirections(self): return Qt.Orientations(Qt.Orientation(0))
    def hasHeightForWidth(self): return True
    def heightForWidth(self, width): return self.doLayout(QRect(0, 0, width, 0), True)
    def setGeometry(self, rect): super(FlowLayout, self).setGeometry(rect); self.doLayout(rect, False)
    def sizeHint(self): return self.minimumSize()
    def minimumSize(self):
        size = QSize()
        for item in self.itemList:
            if item.widget().isHidden(): continue
            size = size.expandedTo(item.minimumSize())
        size += QSize(2 * self.contentsMargins().top(), 2 * self.contentsMargins().top()); return size
    def doLayout(self, rect, testOnly):
        x, y, lineHeight = rect.x(), rect.y(), 0
        for item in self.itemList:
            wid = item.widget()
            if wid.isHidden(): continue
            spaceX = self.spacing() + wid.style().layoutSpacing(QSizePolicy.PushButton, QSizePolicy.PushButton, Qt.Horizontal)
            spaceY = self.spacing() + wid.style().layoutSpacing(QSizePolicy.PushButton, QSizePolicy.PushButton, Qt.Vertical); nextX = x + item.sizeHint().width() + spaceX
            if nextX - spaceX > rect.right() and lineHeight > 0: x, y = rect.x(), y + lineHeight + spaceY; nextX, lineHeight = x + item.sizeHint().width() + spaceX, 0
            if not testOnly: item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))
            x, lineHeight = nextX, max(lineHeight, item.sizeHint().height())
        return y + lineHeight - rect.y()

class ThemeSwitcherWidget(QWidget):
    theme_selected = pyqtSignal(str)
    theme_applied = pyqtSignal()
    reload_requested = pyqtSignal()

    def __init__(self, theme_dir, theme_nss_path):
        super().__init__()
        self.theme_dir = theme_dir
        self.theme_nss_path = theme_nss_path
        self.selected_theme = self._get_current_theme_from_file()
        self.original_theme = self.selected_theme
        self.original_content = self._get_current_content()
        self.selected_button = None
        self.is_dirty = False
        self.auto_save = False
        self.active_scenario = 'reload' # Default: Reload + Show Normal

        self.theme_files = self._find_theme_files()
        self._setup_ui()
        self._highlight_current_theme()

    def refresh_list(self):
        self.theme_files = self._find_theme_files()
        self._setup_ui()
        self._highlight_current_theme()

    def _get_current_theme_from_file(self):
        if os.path.exists(self.theme_nss_path):
            try:
                with open(self.theme_nss_path, 'r') as f:
                    content = f.read()
                
                for filename in os.listdir(self.theme_dir):
                    if filename.endswith(".nss"):
                        with open(os.path.join(self.theme_dir, filename), 'r') as tf:
                            if tf.read() == content:
                                return os.path.splitext(filename)[0]
            except Exception:
                pass
        return None

    def _get_current_content(self):
        if os.path.exists(self.theme_nss_path):
            try:
                with open(self.theme_nss_path, 'r') as f:
                    return f.read()
            except Exception:
                pass
        return ""

    def _find_theme_files(self):
        theme_files = []
        if os.path.exists(self.theme_dir):
            for filename in os.listdir(self.theme_dir):
                if filename.endswith(".nss"):
                    theme_files.append(filename)
        return theme_files

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setObjectName("themeSwitcherScrollArea")
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.grid_widget = QWidget()
        self.grid_widget.setObjectName("themeSwitcherGrid")
        self.grid_layout = FlowLayout(self.grid_widget, spacing=15)
        self.button_group = QButtonGroup()
        self.button_group.setExclusive(True)

        self.frames = {}

        for i, theme_file in enumerate(self.theme_files):
            theme_name = os.path.splitext(theme_file)[0]
            self._add_theme_option(self.grid_layout, theme_name, i)

        scroll_area.setWidget(self.grid_widget)
        main_layout.addWidget(scroll_area)


    def _add_theme_option(self, layout, theme_name, button_id):
        image_path = os.path.join(self.theme_dir, f"{theme_name}.png")
        if os.path.exists(image_path):
            pixmap = QPixmap(image_path).scaled(138, 158, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        else:
            pixmap = QPixmap(138, 158); pixmap.fill(QColor(40, 42, 62))
        
        frame = QFrame()
        frame.setObjectName("themeOptionFrame")
        frame.setProperty("selected", False)
        frame.setCursor(QCursor(Qt.PointingHandCursor))
        shadow = QGraphicsDropShadowEffect(blurRadius=15, xOffset=5, yOffset=5)
        shadow.setColor(QColor(0, 0, 0, 160))
        frame.setGraphicsEffect(shadow)

        frame_layout = QVBoxLayout(frame)
        frame_layout.setAlignment(Qt.AlignCenter)
        frame_layout.setContentsMargins(0, 0, 0, 0)
        frame_layout.setSpacing(10)
        frame.setFixedSize(160, 210)

        img_container = QFrame(); img_container.setFixedSize(144, 164)
        img_container.setObjectName("imgContainer")
        img_container.setStyleSheet("background-color: #282a3e; border-radius: 20px; border: 1px solid rgba(255,255,255,0.05);")
        icl = QVBoxLayout(img_container); icl.setContentsMargins(0, 0, 0, 0)
        image_label = QLabel(); image_label.setPixmap(pixmap); image_label.setAlignment(Qt.AlignCenter)
        icl.addWidget(image_label); frame_layout.addWidget(img_container, 0, Qt.AlignCenter)

        display_name = theme_name.replace("theme_", "").replace("_", " ").title()
        theme_button = QPushButton(display_name)
        theme_button.setObjectName("themeOptionButton")
        theme_button.setCursor(QCursor(Qt.PointingHandCursor))
        theme_button.setCheckable(True)
        theme_button.clicked.connect(lambda checked, name=theme_name, button=frame: self._theme_selected(name, button))
        self.button_group.addButton(theme_button)
        self.button_group.setId(theme_button, button_id)

        theme_button.setFixedWidth(150)
        frame_layout.addWidget(theme_button, 0, Qt.AlignCenter)
        
        # Only set mousePressEvent on the frame to avoid double triggering if button is clicked
        def frame_press(event, name=theme_name, button=frame):
            if event.button() == Qt.LeftButton:
                self._theme_selected(name, button)
        frame.mousePressEvent = frame_press

        layout.addWidget(frame)
        self.frames[theme_name] = frame
        self.update_frame_style(frame)

    def _highlight_current_theme(self):
        if self.selected_theme and self.selected_theme in self.frames:
            self._theme_selected(self.selected_theme, self.frames[self.selected_theme], emit_signal=False, preview=False)

    def update_frame_style(self, frame):
        is_selected = frame.property("selected")
        img_container = frame.findChild(QFrame)
        if img_container:
            if is_selected:
                img_container.setStyleSheet("background-color: #494d64; border-radius: 20px; border: 2px solid #8aadf4;")
            else:
                img_container.setStyleSheet("background-color: #282a3e; border-radius: 20px; border: 1px solid rgba(255,255,255,0.05);")
        
        btn = frame.findChild(QPushButton)
        if btn:
            btn.setStyleSheet(f"color: {'#8aadf4' if is_selected else '#ffffff'}; background: transparent; font-weight: {'bold' if is_selected else 'normal'}; font-size: 13px;")

    def _theme_selected(self, theme_name, frame, emit_signal=True, preview=True):
        if self.selected_button is not None:
            self.selected_button.setProperty("selected", False)
            self.update_frame_style(self.selected_button)

        self.selected_theme = theme_name
        self.selected_button = frame
        self.selected_button.setProperty("selected", True)
        self.update_frame_style(self.selected_button)
        
        self.is_dirty = (self.selected_theme != self.original_theme)
        
        if preview:
            self._apply_theme(theme_name)
            self.reload_requested.emit()

        if emit_signal:
            self.theme_selected.emit(theme_name)
        
        if self.auto_save: self.save_theme()

    def _apply_theme(self, theme_name):
        source_path = os.path.join(self.theme_dir, f"{theme_name}.nss")
        if os.path.exists(source_path):
            try:
                with open(source_path, 'r', encoding='utf-8') as source_file:
                    theme_content = source_file.read()
                safe_file_write(self.theme_nss_path, theme_content)
                print(f"Theme applied (preview): {theme_name}")
            except Exception as e:
                print(f"Error applying theme: {e}")

    def save_theme(self):
        if self.is_dirty:
            self.original_theme = self.selected_theme
            self.original_content = self._get_current_content()
            self.is_dirty = False
            self.theme_applied.emit()
            print(f"Theme changes committed: {self.selected_theme}")
            return True
        return False

    def revert_changes(self):
        if self.is_dirty:
            self.selected_theme = self.original_theme
            self.is_dirty = False
            
            # Revert file content
            if self.original_content:
                try:
                    safe_file_write(self.theme_nss_path, self.original_content)
                except Exception as e:
                    print(f"Error reverting theme content: {e}")
            from utils import trigger_shell_reload
            trigger_shell_reload()

            if self.selected_theme in self.frames:
                self._theme_selected(self.selected_theme, self.frames[self.selected_theme], emit_signal=True, preview=False)
            else:
                if self.selected_button:
                    self.selected_button.setProperty("selected", False)
                    self.update_frame_style(self.selected_button)
                    self.selected_button = None
            return True
        return False