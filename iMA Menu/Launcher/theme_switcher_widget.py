import sys
import os
import time
import threading
import glob
import shutil
import urllib.parse
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTabBar,
    QScrollArea, QFrame, QButtonGroup, QGridLayout, QPushButton, QGraphicsDropShadowEffect, QLayout, QSizePolicy, QInputDialog, QMessageBox, QMenu, QAction, QFileDialog, QDialog, QLineEdit, QApplication, QCheckBox
)
from PyQt5.QtGui import QPixmap, QIcon, QCursor, QColor, QFont, QPainter, QPainterPath, QImage
from PyQt5.QtCore import Qt, QSize, pyqtSignal, QRect, QPoint, QMetaObject, Q_ARG, QThread
from utils import safe_file_write, get_shell_dll_version, get_default_image_dir, save_last_image_dir, FlowLayout, PillTabButton
from github_client import github_api_get, cdn_get, get_latest_tree_sha
from plugin_registry import safe_json_read, atomic_json_write, git_blob_sha, file_matches_git_sha
import re

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
            QLineEdit:focus { border: 2px solid #e78284; }
            QPushButton { border-radius: 12px; font-weight: bold; font-size: 13px; padding: 8px 16px; }
            QPushButton#primaryBtn { background-color: #e78284; color: white; border: none; }
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
        initial_dir = get_default_image_dir()
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Image", initial_dir, "Images (*.png *.jpg *.jpeg)")
        if file_path:
            save_last_image_dir(os.path.dirname(file_path))
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
            QLineEdit:focus { border: 2px solid #e78284; }
            QPushButton { border-radius: 12px; font-weight: bold; font-size: 13px; padding: 8px 16px; font-family: 'Segoe Fluent Icons', 'Segoe UI'; }
            QPushButton#primaryBtn { background-color: #e78284; color: white; border: none; }
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

        self.update_settings_cb = QCheckBox("Overwrite with current theme changes")
        self.update_settings_cb.setChecked(True)
        self.update_settings_cb.setCursor(QCursor(Qt.PointingHandCursor))
        self.update_settings_cb.setStyleSheet("""
            QCheckBox { color: #b0b0b0; font-size: 12px; font-weight: 500; }
            QCheckBox:hover { color: #ffffff; }
            QCheckBox::indicator { width: 16px; height: 16px; border-radius: 4px; border: 1px solid #555566; background-color: #25252b; }
            QCheckBox::indicator:checked { background-color: #e78284; border: 1px solid #e78284; }
        """)
        layout.addWidget(self.update_settings_cb)
        
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
        initial_dir = ""
        if self.current_img_path and os.path.exists(self.current_img_path):
            initial_dir = os.path.dirname(self.current_img_path)
        if not initial_dir or not os.path.exists(initial_dir):
            initial_dir = get_default_image_dir()
            
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Image", initial_dir, "Images (*.png *.jpg *.jpeg)")
        if file_path:
            save_last_image_dir(os.path.dirname(file_path))
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
        self.should_overwrite_settings = self.update_settings_cb.isChecked()
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
            QPushButton#primaryBtn { background-color: #e78284; color: white; border: none; }
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

_theme_pixmap_cache = {}

def get_cached_theme_pixmap(image_path: str, width: int = 144, height: int = 164) -> QPixmap:
    if not image_path or not os.path.exists(image_path):
        empty = QPixmap(width, height)
        empty.fill(Qt.transparent)
        return empty
    try:
        mtime = os.path.getmtime(image_path)
    except Exception:
        mtime = 0
    cache_key = (image_path, mtime, width, height)
    if cache_key in _theme_pixmap_cache:
        return _theme_pixmap_cache[cache_key]
    
    img = QImage(image_path)
    if not img.isNull():
        scaled = img.scaled(width, height, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        rounded = QPixmap(scaled.size())
        rounded.fill(Qt.transparent)
        p = QPainter(rounded)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        path = QPainterPath()
        path.addRoundedRect(0, 0, scaled.width(), scaled.height(), 12, 12)
        p.setClipPath(path)
        p.drawImage(0, 0, scaled)
        p.end()
        pix = rounded
    else:
        pix = QPixmap(width, height)
        pix.fill(Qt.transparent)
    if len(_theme_pixmap_cache) < 128:
        _theme_pixmap_cache[cache_key] = pix
    return pix

class ThemeOptionFrame(QFrame):
    def __init__(self, pixmap, theme_name, parent=None, image_path=None):
        super().__init__(parent)
        self.image_path = image_path
        self.original_pixmap = pixmap
        self.theme_name = theme_name
        self.setObjectName("themeOptionFrame")
        self.setProperty("selected", False)
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setFixedSize(146, 196)
        self.image_label = QLabel()
        if self.image_path:
            self.image_label.setPixmap(get_cached_theme_pixmap(self.image_path, 130, 152))
        elif self.original_pixmap and not self.original_pixmap.isNull():
            self.image_label.setPixmap(self.original_pixmap.scaled(130, 152, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            empty = QPixmap(130, 152)
            empty.fill(Qt.transparent)
            self.image_label.setPixmap(empty)
        self.image_label.setAlignment(Qt.AlignCenter)
        
        self.edit_button = QPushButton("\uE70F", self)
        self.edit_button.setObjectName("editThemeBtn")
        self.edit_button.setFont(QFont('Segoe MDL2 Assets', 11))
        self.edit_button.setFixedSize(30, 30)
        self.edit_button.setCursor(QCursor(Qt.PointingHandCursor))
        self.edit_button.setStyleSheet("""
            QPushButton#editThemeBtn {
                background-color: rgba(255, 255, 255, 0.15);
                color: #ffffff;
                border-radius: 15px;
                border: 1px solid rgba(255, 255, 255, 0.3);
            }
            QPushButton#editThemeBtn:hover {
                background-color: #e78284;
                border: 1px solid #e78284;
            }
        """)
        self.edit_button.move(106, 8)
        self.edit_button.clicked.connect(self.show_edit_menu)
        self.edit_button.hide()

    def enterEvent(self, event):
        if not self.property("selected"):
            self.setStyleSheet("QFrame#themeOptionFrame { background-color: #18181c; border-radius: 20px; border: 2px solid #e78284; }")
        if self.image_path:
            self.image_label.setPixmap(get_cached_theme_pixmap(self.image_path, 136, 158))
        elif self.original_pixmap and not self.original_pixmap.isNull():
            self.image_label.setPixmap(self.original_pixmap.scaled(136, 158, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        if self.theme_name.startswith("theme_"):
            self.edit_button.show()
        super().enterEvent(event)

    def leaveEvent(self, event):
        if not self.property("selected"):
            self.setStyleSheet("QFrame#themeOptionFrame { background-color: #121214; border-radius: 20px; border: 2px solid #24242a; }")
        if self.image_path:
            self.image_label.setPixmap(get_cached_theme_pixmap(self.image_path, 130, 152))
        elif self.original_pixmap and not self.original_pixmap.isNull():
            self.image_label.setPixmap(self.original_pixmap.scaled(130, 152, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.edit_button.hide()
        super().leaveEvent(event)

    def update_style(self):
        is_selected = self.property("selected")
        if is_selected:
            self.setStyleSheet("QFrame#themeOptionFrame { background-color: #261115; border-radius: 20px; border: 2px solid #e78284; }")
        else:
            self.setStyleSheet("QFrame#themeOptionFrame { background-color: #121214; border-radius: 20px; border: 2px solid #24242a; }")
        
        btn = self.findChild(QPushButton, "themeOptionButton")
        if btn:
            if is_selected:
                btn.setStyleSheet("QPushButton#themeOptionButton { background-color: transparent; color: #e78284; border: none; font-weight: bold; font-size: 12px; padding: 2px 4px; }")
            else:
                btn.setStyleSheet("QPushButton#themeOptionButton { background-color: transparent; color: #b0b0b0; border: none; font-weight: bold; font-size: 12px; padding: 2px 4px; } QPushButton#themeOptionButton:hover { color: white; }")

    def show_edit_menu(self):
        if hasattr(self, 'edit_cb') and self.edit_cb:
            self.edit_cb()

class FetchThemesWorker(QThread):
    """
    Asynchronously checks and downloads new or modified themes from the official iMA-Menu repository.
    Only downloads files that are missing or have changed SHA hashes.
    Emits themes_updated(int) with count of downloaded files.
    """
    themes_updated = pyqtSignal(int)

    def __init__(self, theme_dir, cache_file=None):
        super().__init__()
        self.theme_dir = theme_dir
        if not cache_file:
            base_dir = os.path.dirname(self.theme_dir) if os.path.basename(self.theme_dir).lower() == 'theme' else self.theme_dir
            self.cache_file = os.path.join(base_dir, 'cache', 'theme_sync_cache.json')
        else:
            self.cache_file = cache_file

    def run(self):
        THEME_REPO = "iMAboud/iMA-Menu"
        THEME_BRANCH = "main"
        
        try:
            os.makedirs(self.theme_dir, exist_ok=True)
            cache_dir = os.path.dirname(self.cache_file)
            if cache_dir:
                os.makedirs(cache_dir, exist_ok=True)

            cached_state = safe_json_read(self.cache_file) or {}
            last_tree_sha = cached_state.get('tree_sha')

            # 1. Check latest commit / tree sha
            tree_sha = get_latest_tree_sha(THEME_REPO, THEME_BRANCH, timeout=8)
            if not tree_sha:
                tree_sha = THEME_BRANCH

            # 2. Check if we have cached tree data matching latest tree sha
            tree_data = None
            if tree_sha != THEME_BRANCH and tree_sha == last_tree_sha and 'tree' in cached_state:
                tree_data = cached_state.get('tree')
            
            if not tree_data:
                tree_url = f"https://api.github.com/repos/{THEME_REPO}/git/trees/{tree_sha}?recursive=1"
                res = github_api_get(tree_url, max_retries=1, timeout=10)
                if res.status_code == 200:
                    tree_res = res.json()
                    if isinstance(tree_res, dict) and 'tree' in tree_res:
                        tree_data = tree_res['tree']
                        if tree_sha != THEME_BRANCH:
                            atomic_json_write(self.cache_file, {'tree_sha': tree_sha, 'tree': tree_data})

            if not tree_data or not isinstance(tree_data, list):
                return

            # 3. Filter files under 'theme/'
            files_to_download = []
            for item in tree_data:
                if not isinstance(item, dict) or item.get('type') != 'blob':
                    continue
                path = item.get('path', '').replace('\\', '/')
                path_lower = path.lower()
                if 'theme/' not in path_lower:
                    continue
                
                parts = path.split('/')
                theme_idx = -1
                for idx, p in enumerate(parts):
                    if p.lower() == 'theme':
                        theme_idx = idx
                        break
                if theme_idx == -1 or theme_idx == len(parts) - 1:
                    continue

                filename = parts[-1]
                if not filename.lower().endswith(('.nss', '.png', '.jpg', '.jpeg', '.bmp', '.svg')):
                    continue
                
                # Custom user themes created locally (starting with theme_) should never be touched
                if filename.lower().startswith('theme_'):
                    continue

                local_path = os.path.join(self.theme_dir, filename)
                remote_sha = item.get('sha')
                
                needs_update = False
                if not os.path.exists(local_path):
                    needs_update = True
                elif remote_sha:
                    if not file_matches_git_sha(local_path, remote_sha):
                        needs_update = True

                if needs_update:
                    encoded_path = urllib.parse.quote(path)
                    raw_url = f"https://raw.githubusercontent.com/{THEME_REPO}/{THEME_BRANCH}/{encoded_path}"
                    files_to_download.append((filename, local_path, raw_url, remote_sha))

            if not files_to_download:
                return

            # 4. Download only changed / new files
            downloaded_count = 0
            for filename, local_path, raw_url, remote_sha in files_to_download:
                try:
                    res = cdn_get(raw_url, max_retries=2, timeout=15)
                    if res.status_code == 200 and res.content:
                        temp_dest = local_path + ".tmp"
                        with open(temp_dest, 'wb') as f:
                            f.write(res.content)
                        os.replace(temp_dest, local_path)
                        downloaded_count += 1
                except Exception as dl_err:
                    print(f"[ThemeSync] Failed to download {filename}: {dl_err}")

            if downloaded_count > 0:
                self.themes_updated.emit(downloaded_count)
        except Exception:
            pass


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
        self._last_sync_time = 0

        self.theme_files = self._find_theme_files()
        self._setup_ui()
        self._highlight_current_theme()
        
        self.refresh_requested.connect(self.refresh_list)

        self.theme_sync_worker = FetchThemesWorker(self.theme_dir)
        self.theme_sync_worker.themes_updated.connect(self._on_themes_synced)

    def showEvent(self, event):
        super().showEvent(event)
        self.start_background_theme_sync()

    def start_background_theme_sync(self, force=False):
        now = time.time()
        if not force and (now - self._last_sync_time < 60):
            return
        self._last_sync_time = now
        if not self.theme_sync_worker.isRunning():
            self.theme_sync_worker.start()

    def _on_themes_synced(self, count):
        if count > 0:
            self.refresh_list()
            self.status_message_requested.emit(f"Downloaded {count} new/updated themes")

    def refresh_list(self):
        self.setUpdatesEnabled(False)
        try:
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
        finally:
            self.setUpdatesEnabled(True)

    def _get_current_theme_from_file(self):
        if os.path.exists(self.theme_nss_path):
            try:
                with open(self.theme_nss_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                # Check for direct theme tag comment
                for line in content.splitlines()[:5]:
                    line_s = line.strip()
                    if line_s.startswith("//") and ("iMA Theme:" in line_s or "Theme:" in line_s):
                        tag_name = line_s.split(":", 1)[1].strip()
                        if tag_name and os.path.exists(os.path.join(self.theme_dir, f"{tag_name}.nss")):
                            return tag_name

                if hasattr(self, 'selected_theme') and self.selected_theme:
                    current_path = os.path.join(self.theme_dir, f"{self.selected_theme}.nss")
                    if os.path.exists(current_path):
                        with open(current_path, 'r', encoding='utf-8', errors='ignore') as tf:
                            if tf.read() == content:
                                return self.selected_theme
                
                content_len = len(content.encode('utf-8'))
                if os.path.exists(self.theme_dir):
                    for filename in os.listdir(self.theme_dir):
                        if filename.endswith(".nss"):
                            full_path = os.path.join(self.theme_dir, filename)
                            try:
                                if os.path.getsize(full_path) == content_len:
                                    with open(full_path, 'r', encoding='utf-8', errors='ignore') as tf:
                                        if tf.read() == content:
                                            return os.path.splitext(filename)[0]
                            except Exception:
                                pass
            except Exception:
                pass
        return None

    def _get_current_content(self):
        if os.path.exists(self.theme_nss_path):
            try:
                with open(self.theme_nss_path, 'r', encoding='utf-8', errors='ignore') as f:
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

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#121212"))

    def _setup_ui(self):
        self.setAttribute(Qt.WA_StyledBackground, True)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(20)
        
        # 1. Pill-shaped Segmented Tabs Container (Explore / My Themes)
        self.tab_container = QFrame()
        self.tab_container.setObjectName("pillTabContainer")
        self.tab_container.setStyleSheet("""
            QFrame#pillTabContainer {
                background-color: rgba(255,255,255,0.05);
                border: 1px solid rgba(255,255,255,0.06);
                border-radius: 18px;
                padding: 4px;
            }
        """)
        tab_layout = QHBoxLayout(self.tab_container)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.setSpacing(4)
        
        self.explore_tab = PillTabButton("Explore", height=30)
        self.explore_tab.setChecked(True)
        self.explore_tab.clicked.connect(lambda: self._filter_themes("explore"))
        
        self.my_themes_tab = PillTabButton("My Themes", height=30)
        self.my_themes_tab.clicked.connect(lambda: self._filter_themes("my_themes"))
        
        self.tab_group = QButtonGroup(self)
        self.tab_group.setExclusive(True)
        self.tab_group.addButton(self.explore_tab)
        self.tab_group.addButton(self.my_themes_tab)
        
        tab_layout.addWidget(self.explore_tab)
        tab_layout.addWidget(self.my_themes_tab)

        # Header for My Themes tab containing Add Theme button
        self.my_themes_header = QFrame()
        self.my_themes_header.setObjectName("myThemesHeader")
        self.my_themes_header.setStyleSheet("background: transparent; border: none; margin-bottom: 5px;")
        header_layout = QHBoxLayout(self.my_themes_header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(12)

        my_themes_title = QLabel("Custom Themes")
        my_themes_title.setFont(QFont('Segoe UI', 13, QFont.Bold))
        my_themes_title.setStyleSheet("color: white; background: transparent;")

        self.add_theme_btn = QPushButton("\uE109  Add Theme")
        self.add_theme_btn.setObjectName("addThemeBtn")
        self.add_theme_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.add_theme_btn.setFont(QFont('Segoe UI', 11, QFont.Bold))
        self.add_theme_btn.setStyleSheet("""
            QPushButton#addThemeBtn {
                background: rgba(231, 130, 132, 0.18);
                color: #ff6b81;
                border: 1px solid rgba(231, 130, 132, 0.4);
                border-radius: 14px;
                padding: 6px 18px;
            }
            QPushButton#addThemeBtn:hover {
                background: #e78284;
                color: white;
                border: 1px solid #e78284;
            }
        """)
        self.add_theme_btn.clicked.connect(self._add_current_theme)

        header_layout.addWidget(my_themes_title)
        header_layout.addStretch()
        header_layout.addWidget(self.add_theme_btn)

        self.my_themes_header.hide()
        main_layout.addWidget(self.my_themes_header)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setObjectName("themeSwitcherScrollArea")
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; } QWidget#themeSwitcherGrid { background: transparent; }")

        self.grid_widget = QWidget()
        self.grid_widget.setObjectName("themeSwitcherGrid")
        self.grid_layout = FlowLayout(self.grid_widget, spacing=10)
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

        if category == "my_themes":
            self.my_themes_header.show()
        else:
            self.my_themes_header.hide()
        
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
                with open(self.theme_nss_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                safe_file_write(dest_nss, content)
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
            with open(self.theme_nss_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            safe_file_write(dest_nss, content)
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
        frame = ThemeOptionFrame(None, theme_name, image_path=image_path)
        frame.edit_cb = lambda n=theme_name: self._edit_theme(n)

        frame_layout = QVBoxLayout(frame)
        frame_layout.setAlignment(Qt.AlignCenter)
        frame_layout.setContentsMargins(0, 8, 0, 6)
        frame_layout.setSpacing(4)

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

        theme_button.setFixedWidth(136)
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
                    if os.path.exists(old_png) and (not dialog.current_img_path or dialog.current_img_path == old_png):
                        os.rename(old_png, new_png)
                        
                # Handle image upload
                final_png = os.path.join(self.theme_dir, f"{new_theme_key}.png")
                if dialog.current_img_path and dialog.current_img_path != final_png and os.path.exists(dialog.current_img_path):
                    import shutil
                    shutil.copy2(dialog.current_img_path, final_png)

                # Handle settings overwrite
                if getattr(dialog, 'should_overwrite_settings', False):
                    self._update_theme_settings(new_theme_key)
                
                self.refresh_list()
                self.status_message_requested.emit(f"Updated '{new_theme_name}' successfully!")

    def _highlight_current_theme(self):
        if self.selected_theme and self.selected_theme in self.frames:
            self._theme_selected(self.selected_theme, self.frames[self.selected_theme], emit_signal=False, preview=False)

    def update_frame_style(self, frame):
        is_selected = frame.property("selected")
        if is_selected:
            frame.setStyleSheet("QFrame#themeOptionFrame { background-color: #261115; border-radius: 20px; border: 2px solid #e78284; }")
        else:
            frame.setStyleSheet("QFrame#themeOptionFrame { background-color: #121214; border-radius: 20px; border: 2px solid #24242a; }")
        
        btn = frame.findChild(QPushButton)
        if btn:
            btn.setStyleSheet(f"color: {'#e78284' if is_selected else '#ffffff'}; background: transparent; font-weight: bold; font-size: 12px; border: none;")

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
                if version < (2, 0, 0, 2):
                    theme_content = re.sub(r'^\s*image\.effect\s*=.*$', '', theme_content, flags=re.MULTILINE)
                    theme_content = re.sub(r'^\s*symbol\.effect\s*=.*$', '', theme_content, flags=re.MULTILINE)
                    def _simplify_sym_normal(match):
                        arr_str = match.group(1)
                        items = [x.strip().strip("'\"") for x in arr_str.split(',') if x.strip()]
                        return f"  symbol.normal = {items[0]}" if items else "  symbol.normal = #ffffff"
                    theme_content = re.sub(r'^\s*symbol\.normal\s*=\s*\[(.*?)\]', _simplify_sym_normal, theme_content, flags=re.MULTILINE)
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

    def save_selection(self):
        return self.save_theme()

    def revert_changes(self):
        if self.is_dirty or (self.original_theme and self.selected_theme != self.original_theme):
            self.selected_theme = self.original_theme
            self.is_dirty = False
            
            # Revert file content
            reverted = False
            if self.original_content:
                try:
                    safe_file_write(self.theme_nss_path, self.original_content)
                    reverted = True
                except Exception as e:
                    print(f"Error reverting theme content: {e}")
            if not reverted and self.original_theme:
                orig_file = os.path.join(self.theme_dir, f"{self.original_theme}.nss")
                if os.path.exists(orig_file):
                    try:
                        with open(orig_file, 'r', encoding='utf-8', errors='ignore') as f:
                            orig_c = f.read()
                        safe_file_write(self.theme_nss_path, orig_c)
                        reverted = True
                    except Exception as e:
                        print(f"Error reverting theme file from source: {e}")

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

    def revert_selection(self):
        return self.revert_changes()

    def revert_theme(self):
        return self.revert_changes()