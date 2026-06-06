import sys
import os
import time
import threading
import glob
import shutil
import win32api
import win32con
import win32gui
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTabBar,
    QScrollArea, QFrame, QButtonGroup, QGridLayout, QPushButton, QGraphicsDropShadowEffect, QLayout, QSizePolicy, QInputDialog, QMessageBox, QMenu, QAction, QFileDialog, QDialog, QLineEdit, QApplication
)
from PyQt5.QtGui import QPixmap, QIcon, QCursor, QColor, QFont, QPainter, QPainterPath, QImage
from PyQt5.QtCore import Qt, QSize, pyqtSignal, QRect, QPoint, QMetaObject, Q_ARG
from utils import safe_file_write, get_shell_dll_version
import re


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

class ClickableLabel(QLabel):
    clicked = pyqtSignal()
    def mousePressEvent(self, event):
        self.clicked.emit()

class AddThemeDialog(QDialog):
    def __init__(self, preview_img_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Theme")
        self.setFixedSize(360, 480)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        self.setStyleSheet("""
            QFrame#mainFrame { background-color: #1a1a1e; border: 1px solid rgba(255,255,255,0.05); border-radius: 15px; }
            QLabel { color: white; font-weight: bold; font-size: 14px; }
            QLineEdit { background-color: #25252b; color: white; border: 2px solid #555566; border-radius: 12px; padding: 10px; font-size: 14px; }
            QLineEdit:focus { border: 2px solid #dc143c; }
            QPushButton { border-radius: 12px; font-weight: bold; font-size: 13px; padding: 8px 16px; }
            QPushButton#primaryBtn { background-color: #dc143c; color: white; border: none; }
            QPushButton#primaryBtn:hover { background-color: #e62045; }
            QPushButton#secondaryBtn { background-color: rgba(255,255,255,0.05); color: white; border: 1px solid rgba(255,255,255,0.1); }
            QPushButton#secondaryBtn:hover { background-color: rgba(255,255,255,0.1); }
        """)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_frame = QFrame()
        self.main_frame.setObjectName("mainFrame")
        main_layout.addWidget(self.main_frame)
        
        layout = QVBoxLayout(self.main_frame)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(15)
        
        self.preview_label = ClickableLabel()
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setFixedSize(180, 260)
        self.preview_label.setCursor(QCursor(Qt.PointingHandCursor))
        
        self.current_img_path = preview_img_path
        self._load_preview(self.current_img_path)
        self.preview_label.clicked.connect(self.on_upload)
        layout.addWidget(self.preview_label, 0, Qt.AlignCenter)
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter new theme name...")
        layout.addWidget(self.name_input)
        
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setObjectName("secondaryBtn")
        self.cancel_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.cancel_btn.clicked.connect(self.reject)
        
        self.add_btn = QPushButton("Add Theme")
        self.add_btn.setObjectName("primaryBtn")
        self.add_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.add_btn.clicked.connect(self.on_add)
        
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self.add_btn)
        
        layout.addLayout(btn_layout)
        
        self.theme_name = ""
        self.action_type = ""

    def _load_preview(self, path):
        if os.path.exists(path):
            from PyQt5.QtGui import QImage
            img = QImage(path)
            if not img.isNull():
                scaled_img = img.scaled(180, 260, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                pixmap = QPixmap.fromImage(scaled_img)
                
                x_pos = (180 - pixmap.width()) // 2
                y_pos = (260 - pixmap.height()) // 2
                
                rounded = QPixmap(180, 260)
                rounded.fill(Qt.transparent)
                painter = QPainter(rounded)
                painter.setRenderHint(QPainter.Antialiasing)
                painter.setRenderHint(QPainter.SmoothPixmapTransform)
                
                path_clip = QPainterPath()
                path_clip.addRoundedRect(0, 0, 180, 260, 12, 12)
                painter.setClipPath(path_clip)
                
                painter.drawPixmap(x_pos, y_pos, pixmap)
                painter.end()
                self.preview_label.setPixmap(rounded)
                self.preview_label.setStyleSheet("background-color: transparent;")
        else:
            self.preview_label.setText("+\nUpload Image")
            self.preview_label.setStyleSheet("""
                background-color: #25252b; 
                border-radius: 12px; 
                border: 2px dashed #555566; 
                color: #888899; 
                font-size: 16px;
            """)

    def on_upload(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Image", "", "Images (*.png *.jpg *.jpeg)")
        if file_path:
            self.current_img_path = file_path
            self._load_preview(file_path)

    def on_add(self):
        self.theme_name = self.name_input.text().strip()
        if not self.theme_name:
            QMessageBox.warning(self, "Invalid Name", "Please enter a valid theme name.")
            return
        self.accept()

class EditThemeDialog(QDialog):
    def __init__(self, theme_name, preview_img_path, parent=None):
        super().__init__(parent)
        self.original_theme_name = theme_name
        self.setWindowTitle(f"Edit Theme: {theme_name}")
        self.setFixedSize(360, 520)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        self.setStyleSheet("""
            QFrame#mainFrame { background-color: #1a1a1e; border: 1px solid rgba(255,255,255,0.05); border-radius: 15px; }
            QLabel { color: white; font-weight: bold; font-size: 14px; }
            QLineEdit { background-color: #25252b; color: white; border: 2px solid #555566; border-radius: 12px; padding: 10px; font-size: 14px; }
            QLineEdit:focus { border: 2px solid #dc143c; }
            QPushButton { border-radius: 12px; font-weight: bold; font-size: 13px; padding: 8px 16px; font-family: 'Segoe Fluent Icons', 'Segoe UI'; }
            QPushButton#primaryBtn { background-color: #dc143c; color: white; border: none; }
            QPushButton#primaryBtn:hover { background-color: #e62045; }
            QPushButton#secondaryBtn { background-color: rgba(255,255,255,0.05); color: white; border: 1px solid rgba(255,255,255,0.1); }
            QPushButton#secondaryBtn:hover { background-color: rgba(255,255,255,0.1); }
            QPushButton#dangerBtn { background-color: rgba(255,68,68,0.05); color: #ff4444; border: 1px solid rgba(255,68,68,0.2); }
            QPushButton#dangerBtn:hover { background-color: rgba(255,68,68,0.1); }
        """)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_frame = QFrame()
        self.main_frame.setObjectName("mainFrame")
        main_layout.addWidget(self.main_frame)
        
        layout = QVBoxLayout(self.main_frame)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(15)
        
        top_layout = QHBoxLayout()
        self.delete_btn = QPushButton("\uE107  Delete")
        self.delete_btn.setObjectName("dangerBtn")
        self.delete_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.delete_btn.clicked.connect(self.on_delete)
        top_layout.addWidget(self.delete_btn, 0, Qt.AlignLeft)
        top_layout.addStretch()
        layout.addLayout(top_layout)
        
        self.preview_label = ClickableLabel()
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setFixedSize(180, 260)
        self.preview_label.setCursor(QCursor(Qt.PointingHandCursor))
        
        self.current_img_path = preview_img_path
        self._load_preview(self.current_img_path)
        self.preview_label.clicked.connect(self.on_upload)
        layout.addWidget(self.preview_label, 0, Qt.AlignCenter)
        
        self.name_input = QLineEdit()
        self.name_input.setText(theme_name.replace("theme_", "").replace("_", " "))
        layout.addWidget(self.name_input)
        
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setObjectName("secondaryBtn")
        self.cancel_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.cancel_btn.clicked.connect(self.reject)
        
        self.update_btn = QPushButton("\uE105  Update")
        self.update_btn.setObjectName("primaryBtn")
        self.update_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.update_btn.clicked.connect(self.on_update)
        
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self.update_btn)
        
        layout.addLayout(btn_layout)
        
        self.theme_name = ""
        self.action_type = ""

    def _load_preview(self, path):
        if os.path.exists(path):
            from PyQt5.QtGui import QImage
            img = QImage(path)
            if not img.isNull():
                scaled_img = img.scaled(180, 260, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                pixmap = QPixmap.fromImage(scaled_img)
                x_pos = (180 - pixmap.width()) // 2
                y_pos = (260 - pixmap.height()) // 2
                rounded = QPixmap(180, 260)
                rounded.fill(Qt.transparent)
                painter = QPainter(rounded)
                painter.setRenderHint(QPainter.Antialiasing)
                painter.setRenderHint(QPainter.SmoothPixmapTransform)
                path_clip = QPainterPath()
                path_clip.addRoundedRect(0, 0, 180, 260, 12, 12)
                painter.setClipPath(path_clip)
                painter.drawPixmap(x_pos, y_pos, pixmap)
                painter.end()
                self.preview_label.setPixmap(rounded)
                self.preview_label.setStyleSheet("background-color: transparent;")
        else:
            self.preview_label.setText("+\nUpload Image")
            self.preview_label.setStyleSheet("""
                background-color: #25252b; 
                border-radius: 12px; 
                border: 2px dashed #555566; 
                color: #888899; 
                font-size: 16px;
            """)

    def on_upload(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Image", "", "Images (*.png *.jpg *.jpeg)")
        if file_path:
            self.current_img_path = file_path
            self._load_preview(file_path)

    def on_delete(self):
        self.action_type = "delete"
        self.accept()

    def on_update(self):
        self.theme_name = self.name_input.text().strip()
        if not self.theme_name:
            QMessageBox.warning(self, "Invalid Name", "Please enter a valid theme name.")
            return
        self.action_type = "update"
        self.accept()

class CustomConfirmDialog(QDialog):
    def __init__(self, title, message, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setFixedSize(400, 160)
        self.setStyleSheet("""
            QDialog { background-color: #1a1a1e; }
            QLabel { color: white; font-weight: bold; font-size: 14px; }
            QPushButton { border-radius: 12px; font-weight: bold; font-size: 13px; padding: 8px 24px; }
            QPushButton#primaryBtn { background-color: #dc143c; color: white; border: none; }
            QPushButton#primaryBtn:hover { background-color: #e62045; }
            QPushButton#secondaryBtn { background-color: rgba(255,255,255,0.05); color: white; border: 1px solid rgba(255,255,255,0.1); }
            QPushButton#secondaryBtn:hover { background-color: rgba(255,255,255,0.1); }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(20)
        
        msg_label = QLabel(message)
        msg_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(msg_label)
        
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(15)
        
        self.yes_btn = QPushButton("Yes")
        self.yes_btn.setObjectName("primaryBtn")
        self.yes_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.yes_btn.clicked.connect(self.accept)
        
        self.no_btn = QPushButton("No")
        self.no_btn.setObjectName("secondaryBtn")
        self.no_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.no_btn.clicked.connect(self.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.no_btn)
        btn_layout.addWidget(self.yes_btn)
        btn_layout.addStretch()
        
        layout.addLayout(btn_layout)

class ThemeOptionFrame(QFrame):
    def __init__(self, pixmap, theme_name, parent=None):
        super().__init__(parent)
        self.original_pixmap = pixmap
        self.theme_name = theme_name
        self.setObjectName("themeOptionFrame")
        self.setProperty("selected", False)
        self.setCursor(QCursor(Qt.PointingHandCursor))
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setXOffset(5)
        shadow.setYOffset(5)
        shadow.setColor(QColor(0, 0, 0, 160))
        self.setGraphicsEffect(shadow)
        self.setFixedSize(160, 210)
        self.image_label = QLabel()
        self.image_label.setPixmap(self.original_pixmap.scaled(144, 164, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.image_label.setAlignment(Qt.AlignCenter)
        
        self.edit_button = QPushButton("\uE70F", self)
        self.edit_button.setObjectName("editThemeBtn")
        self.edit_button.setFont(QFont('Segoe MDL2 Assets', 11))
        self.edit_button.setFixedSize(32, 32)
        self.edit_button.setCursor(QCursor(Qt.PointingHandCursor))
        self.edit_button.setStyleSheet("""
            QPushButton#editThemeBtn {
                background-color: rgba(255, 255, 255, 0.15);
                color: #ffffff;
                border-radius: 16px;
                border: 1px solid rgba(255, 255, 255, 0.3);
            }
            QPushButton#editThemeBtn:hover {
                background-color: #dc143c;
                border: 1px solid #dc143c;
            }
        """)
        self.edit_button.move(120, 8)
        self.edit_button.clicked.connect(self.show_edit_menu)
        self.edit_button.hide()

    def enterEvent(self, event):
        if not self.property("selected"):
            self.setStyleSheet("QFrame#themeOptionFrame { background-color: #25252b; border-radius: 20px; border: 2px solid #555566; }")
        self.image_label.setPixmap(self.original_pixmap.scaled(150, 170, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        if self.theme_name.startswith("theme_"):
            self.edit_button.show()
        super().enterEvent(event)

    def leaveEvent(self, event):
        if not self.property("selected"):
            self.setStyleSheet("QFrame#themeOptionFrame { background-color: #1a1a1e; border-radius: 20px; border: 1px solid rgba(255,255,255,0.05); }")
        self.image_label.setPixmap(self.original_pixmap.scaled(144, 164, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.edit_button.hide()
        super().leaveEvent(event)

    def update_style(self):
        is_selected = self.property("selected")
        if is_selected:
            self.setStyleSheet("QFrame#themeOptionFrame { background-color: #2a2a30; border-radius: 20px; border: 2px solid #dc143c; }")
        else:
            self.setStyleSheet("QFrame#themeOptionFrame { background-color: #1a1a1e; border-radius: 20px; border: 1px solid rgba(255,255,255,0.05); }")
        
        btn = self.findChild(QPushButton, "themeOptionButton")
        if btn:
            if is_selected:
                btn.setStyleSheet("QPushButton#themeOptionButton { background-color: #dc143c; color: white; border-radius: 14px; font-weight: bold; font-size: 13px; padding: 6px 12px; }")
            else:
                btn.setStyleSheet("QPushButton#themeOptionButton { background-color: rgba(255,255,255,0.05); color: #b0b0b0; border-radius: 14px; font-weight: bold; font-size: 13px; padding: 6px 12px; } QPushButton#themeOptionButton:hover { background-color: rgba(255,255,255,0.1); color: white; }")

    def show_edit_menu(self):
        if hasattr(self, 'edit_cb') and self.edit_cb:
            self.edit_cb()

class ThemeSwitcherWidget(QWidget):
    theme_selected = pyqtSignal(str)
    theme_applied = pyqtSignal()
    reload_requested = pyqtSignal()
    status_message_requested = pyqtSignal(str)
    refresh_requested = pyqtSignal()

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
        
        self.refresh_requested.connect(self.refresh_list)

    def refresh_list(self):
        self.theme_files = self._find_theme_files()
        
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            widget = item.widget()
            if widget: widget.deleteLater()
            
        self.frames.clear()
        self.selected_button = None
            
        for i, theme_file in enumerate(self.theme_files):
            theme_name = os.path.splitext(theme_file)[0]
            self._add_theme_option(self.grid_layout, theme_name, i)
            
        self._highlight_current_theme()
        
        # Re-apply current filter
        current_category = "explore" if self.explore_tab.isChecked() else "my_themes"
        self._filter_themes(current_category)

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
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(20)
        
        # Tabs container
        tab_container = QFrame()
        tab_container.setObjectName("themeTabContainer")
        tab_container.setStyleSheet("""
            QFrame#themeTabContainer {
                background-color: rgba(255,255,255,0.05);
                border-radius: 18px;
                padding: 4px;
            }
            QPushButton {
                background-color: transparent;
                color: #b0b0b0;
                border: none;
                border-radius: 14px;
                padding: 6px 20px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                color: white;
                background-color: rgba(255,255,255,0.05);
            }
            QPushButton:checked {
                background-color: #25252b;
                color: white;
                border: 1px solid rgba(255,255,255,0.1);
            }
        """)
        tab_layout = QHBoxLayout(tab_container)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.setSpacing(2)
        
        self.explore_tab = QPushButton("Explore")
        self.explore_tab.setCheckable(True)
        self.explore_tab.setChecked(True)
        self.explore_tab.setCursor(QCursor(Qt.PointingHandCursor))
        self.explore_tab.clicked.connect(lambda: self._filter_themes("explore"))
        
        self.my_themes_tab = QPushButton("My Themes")
        self.my_themes_tab.setCheckable(True)
        self.my_themes_tab.setCursor(QCursor(Qt.PointingHandCursor))
        self.my_themes_tab.clicked.connect(lambda: self._filter_themes("my_themes"))
        
        self.tab_group = QButtonGroup(self)
        self.tab_group.setExclusive(True)
        self.tab_group.addButton(self.explore_tab)
        self.tab_group.addButton(self.my_themes_tab)
        
        tab_layout.addWidget(self.explore_tab)
        tab_layout.addWidget(self.my_themes_tab)
        
        top_layout = QHBoxLayout()
        top_layout.addStretch()
        top_layout.addWidget(tab_container)
        top_layout.addStretch()
        main_layout.addLayout(top_layout)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setObjectName("themeSwitcherScrollArea")
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; } QWidget#themeSwitcherGrid { background: transparent; }")

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
        
        # Apply initial filter
        self._filter_themes("explore")

    def _filter_themes(self, category):
        for i in range(self.grid_layout.count()):
            item = self.grid_layout.itemAt(i)
            if item and item.widget():
                frame = item.widget()
                if isinstance(frame, ThemeOptionFrame):
                    is_custom = frame.theme_name.startswith("theme_")
                    if category == "explore":
                        frame.setVisible(not is_custom)
                    else:
                        frame.setVisible(is_custom)
        
        # Force FlowLayout to recalculate
        self.grid_widget.updateGeometry()
        self.grid_layout.invalidate()

    def _add_current_theme(self):
        # We start with no auto-capture. We just show the AddThemeDialog with no preview.
        dialog = AddThemeDialog("", self)
        if dialog.exec_() == QDialog.Accepted:
            new_theme_name = dialog.theme_name
            theme_name = "theme_" + new_theme_name.replace(" ", "_")
            if new_theme_name.lower().startswith("theme_"):
                theme_name = new_theme_name.replace(" ", "_")
            
            dest_nss = os.path.join(self.theme_dir, f"{theme_name}.nss")
            if os.path.exists(dest_nss):
                dialog_confirm = CustomConfirmDialog('Theme Exists', f"The theme '{new_theme_name}' already exists. Overwrite?", self)
                if dialog_confirm.exec_() != QDialog.Accepted:
                    return

            try:
                with open(self.theme_nss_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                with open(dest_nss, 'w', encoding='utf-8') as f:
                    f.write(content)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not save theme: {e}")
                return
            
            # If user uploaded an image, copy it
            preview_dest = os.path.join(self.theme_dir, f"{theme_name}.png")
            if dialog.current_img_path and os.path.exists(dialog.current_img_path):
                import shutil
                shutil.copy2(dialog.current_img_path, preview_dest)
            
            self.status_message_requested.emit(f"Added theme successfully!")
            self.refresh_list()

    def _update_theme_settings(self, theme_name):
        dest_nss = os.path.join(self.theme_dir, f"{theme_name}.nss")
        try:
            with open(self.theme_nss_path, 'r', encoding='utf-8') as f:
                content = f.read()
            with open(dest_nss, 'w', encoding='utf-8') as f:
                f.write(content)
            self.status_message_requested.emit(f"Updated {theme_name}")
            self.refresh_list()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not update theme: {e}")

    def _delete_theme(self, theme_name):
        display = theme_name.replace("theme_", "").replace("_", " ")
        dialog = CustomConfirmDialog('Confirm Delete', f"Are you sure you want to delete '{display}'?", self)
        if dialog.exec_() == QDialog.Accepted:
            png_path = os.path.join(self.theme_dir, f"{theme_name}.png")
            nss_path = os.path.join(self.theme_dir, f"{theme_name}.nss")
            if os.path.exists(png_path): os.remove(png_path)
            if os.path.exists(nss_path): os.remove(nss_path)
            self.refresh_list()



    def _add_theme_option(self, layout, theme_name, button_id):
        image_path = os.path.join(self.theme_dir, f"{theme_name}.png")
        if os.path.exists(image_path):
            pixmap = QPixmap(image_path)
        else:
            pixmap = QPixmap(144, 164); pixmap.fill(Qt.transparent)
        
        frame = ThemeOptionFrame(pixmap, theme_name)
        frame.edit_cb = lambda n=theme_name: self._edit_theme(n)

        frame_layout = QVBoxLayout(frame)
        frame_layout.setAlignment(Qt.AlignCenter)
        frame_layout.setContentsMargins(0, 10, 0, 10)
        frame_layout.setSpacing(10)

        frame_layout.addWidget(frame.image_label, 0, Qt.AlignCenter)

        display_name = theme_name.replace("theme_", "").replace("_", " ")
        if display_name.islower():
            display_name = display_name.title()
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
                button.findChild(QPushButton, "themeOptionButton").setChecked(True)
                self._theme_selected(name, button)
        frame.mousePressEvent = frame_press

        layout.addWidget(frame)
        self.frames[theme_name] = frame
        frame.edit_button.raise_()
        self.update_frame_style(frame)

    def _edit_theme(self, theme_name):
        png_path = os.path.join(self.theme_dir, f"{theme_name}.png")
        dialog = EditThemeDialog(theme_name, png_path, self)
        
        if dialog.exec_() == QDialog.Accepted:
            if dialog.action_type == "delete":
                self._delete_theme(theme_name)
            elif dialog.action_type == "update":
                new_theme_name = dialog.theme_name
                new_theme_key = "theme_" + new_theme_name.replace(" ", "_")
                if new_theme_name.lower().startswith("theme_"):
                    new_theme_key = new_theme_name.replace(" ", "_")
                
                # Handle rename
                if new_theme_key != theme_name:
                    old_nss = os.path.join(self.theme_dir, f"{theme_name}.nss")
                    new_nss = os.path.join(self.theme_dir, f"{new_theme_key}.nss")
                    if os.path.exists(old_nss):
                        os.rename(old_nss, new_nss)
                        
                    old_png = os.path.join(self.theme_dir, f"{theme_name}.png")
                    new_png = os.path.join(self.theme_dir, f"{new_theme_key}.png")
                    if os.path.exists(old_png):
                        os.rename(old_png, new_png)
                
                # Handle image upload
                final_png = os.path.join(self.theme_dir, f"{new_theme_key}.png")
                if dialog.current_img_path and dialog.current_img_path != final_png and os.path.exists(dialog.current_img_path):
                    import shutil
                    shutil.copy2(dialog.current_img_path, final_png)
                
                self._update_theme_settings(new_theme_key)
                self.refresh_list()
                self.status_message_requested.emit(f"Updated '{new_theme_name}' successfully!")

    def _highlight_current_theme(self):
        if self.selected_theme and self.selected_theme in self.frames:
            self._theme_selected(self.selected_theme, self.frames[self.selected_theme], emit_signal=False, preview=False)

    def update_frame_style(self, frame):
        is_selected = frame.property("selected")
        if is_selected:
            frame.setStyleSheet("QFrame#themeOptionFrame { background-color: #2a2a30; border-radius: 20px; border: 2px solid #dc143c; }")
        else:
            frame.setStyleSheet("QFrame#themeOptionFrame { background-color: #1a1a1e; border-radius: 20px; border: 1px solid rgba(255,255,255,0.05); }")
        
        btn = frame.findChild(QPushButton)
        if btn:
            btn.setStyleSheet(f"color: {'#dc143c' if is_selected else '#ffffff'}; background: transparent; font-weight: bold; font-size: 13px; border: none;")

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
                
                # Compatibility check for shell.dll version
                version = get_shell_dll_version()
                if version[0] < 2:
                    # Remove background.image line if present
                    theme_content = re.sub(r'^\s*background\.image\s*=.*$', '', theme_content, flags=re.MULTILINE)

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
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(0, trigger_shell_reload)

            if self.selected_theme in self.frames:
                self._theme_selected(self.selected_theme, self.frames[self.selected_theme], emit_signal=True, preview=False)
            else:
                if self.selected_button:
                    self.selected_button.setProperty("selected", False)
                    self.update_frame_style(self.selected_button)
                    self.selected_button = None
            return True
        return False