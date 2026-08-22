import sys
import os
import ctypes

try:
    ctypes.windll.kernel32.SetEnvironmentVariableW("_MEIPASS2", None)
    ctypes.windll.kernel32.SetEnvironmentVariableW("_MEIPASS", None)
except Exception:
    pass
for env_key in list(os.environ.keys()):
    if env_key.startswith('_MEI'):
        os.environ.pop(env_key, None)

import traceback
import time

def global_exception_handler(exctype, value, tb):
    try:
        log_dir = os.path.dirname(os.path.abspath(__file__))
        log_path = os.path.join(log_dir, "fatal_error.log")
        with open(log_path, "a") as f:
            f.write("\n" + "="*50 + "\n")
            f.write(f"FATAL ERROR: {exctype.__name__}: {value}\n")
            f.write("".join(traceback.format_exception(exctype, value, tb)))
    except:
        pass
    sys.__excepthook__(exctype, value, tb)

sys.excepthook = global_exception_handler
import tempfile
import requests
import threading
import json
import shutil
import zipfile
import re
import base64
import subprocess
import winreg
import hashlib
from collections import deque
import markdown
import ctypes
from ctypes import wintypes
import win32gui
import win32con
from PyQt5.QtWidgets import (QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QGridLayout,
                             QScrollArea, QGraphicsDropShadowEffect, QProgressBar, QTextBrowser, QStackedWidget, 
                             QTabWidget, QDialog, QDialogButtonBox, QLineEdit, QScrollBar, QAbstractSlider, QComboBox, 
                             QTabBar, QSizePolicy, QFrame, QCheckBox, QFileDialog, QInputDialog, QShortcut)
from PyQt5.QtGui import QColor, QPixmap, QFont, QPainter, QPainterPath, QPen, QTextOption, QIcon, QCursor, QKeySequence
from PyQt5.QtCore import (Qt, pyqtSignal, QObject, QThread, QTimer, QPropertyAnimation, QEasingCurve, 
                             QSize, QEvent, QPoint, QRect, pyqtProperty, QFileSystemWatcher, QParallelAnimationGroup)
try: from PyQt5 import QtSvg
except ImportError: QtSvg = None
from modify_widget import ModifyWidget, CustomMessageBox, GlobalTintWorker, _get_theme_glyph_colors, get_font_icon, set_project_root
from theme_switcher_widget import ThemeSwitcherWidget
from theme_editor_widget import ThemeEditorWidget
from utils import resource_path, safe_file_write, set_window_effect, UnsavedChangesDialog, trigger_shell_reload, terminate_plugin_processes, get_mdl2_icon, global_undo_stack
from cloud_sync import CloudSyncManager
from nss_error_monitor import ShellLogMonitor
from plugin_registry import PluginRegistry, git_blob_sha, version_cmp, atomic_json_write, safe_json_read, delete_to_recycle_bin

# Win32 Constants
HTLEFT = 10
HTRIGHT = 11
HTTOP = 12
HTTOPLEFT = 13
HTTOPRIGHT = 14
HTBOTTOM = 15
HTBOTTOMLEFT = 16
HTBOTTOMRIGHT = 17
HTCAPTION = 2
WM_NCHITTEST = 0x0084
WM_NCCALCSIZE = 0x0083
WM_GETMINMAXINFO = 0x0024

APP_REPO = "iMAboud/iMA-Menu-Updater"
_GITHUB_REPO = "iMAboud/iMA-Menu-Plugins"
GITHUB_PLUGINS_JSON_URL = f"https://raw.githubusercontent.com/{_GITHUB_REPO}/main/plugins.json"
GITHUB_API_BASE_URL = f"https://api.github.com/repos/{_GITHUB_REPO}"
GITHUB_RELEASES_API_URL = f"{GITHUB_API_BASE_URL}/releases/latest"
APP_LATEST_RELEASE_URL = f"https://api.github.com/repos/{APP_REPO}/releases/latest"
APP_RELEASES_API_URL = f"https://api.github.com/repos/{APP_REPO}/releases"
REQUEST_TIMEOUT = 15

import github_client
from github_client import github_api_get, cdn_get, get_latest_tree_sha
session = github_client._session

# --- Robust Path Detection & Directory Initialization ---
def _initialize_app_paths():
    if getattr(sys, 'frozen', False):
        base = os.path.dirname(os.path.abspath(sys.executable))
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    
    base = os.path.normpath(base)
    
    # Anchor the PROJECT_ROOT by looking for shell.nss
    root = base
    temp_curr = base
    for _ in range(4):
        if os.path.exists(os.path.join(temp_curr, 'shell.nss')):
            root = temp_curr
            break
        parent = os.path.dirname(temp_curr)
        if parent == temp_curr: break
        temp_curr = parent
    
    # Fallback: If root not found but base is 'Launcher', root is parent
    if root == base and os.path.basename(base).lower() == 'launcher':
        root = os.path.abspath(os.path.join(base, '..'))
        
    return base, root

APP_BASE_PATH, PROJECT_ROOT = _initialize_app_paths()
set_project_root(PROJECT_ROOT)

# Directory Definitions
PLUGINS_DIR = os.path.join(PROJECT_ROOT, 'plugins')
LIB_DIR = os.path.join(APP_BASE_PATH, 'lib')
CACHE_DIR = os.path.join(APP_BASE_PATH, 'cache')
LAUNCHER_ICONS_DIR = os.path.join(APP_BASE_PATH, 'icons')
ICONS_CACHE_DIR = os.path.join(CACHE_DIR, 'icons')

# File Definitions
PLUGIN_REGISTRY_FILE = os.path.join(CACHE_DIR, 'plugin_registry.json')
PLUGINS_CACHE_FILE = os.path.join(CACHE_DIR, 'plugins.json')
GIT_TREE_CACHE_FILE = os.path.join(CACHE_DIR, 'git_tree_cache.json')
SETTINGS_FILE = os.path.join(CACHE_DIR, 'settings.json')
VERSION_FILE = os.path.join(CACHE_DIR, 'version.txt')
DEFAULT_ICON_PATH = os.path.join(LAUNCHER_ICONS_DIR, 'icon.ico')

# Ensure all required directories exist immediately at startup
try:
    for d in [PLUGINS_DIR, LIB_DIR, CACHE_DIR, LAUNCHER_ICONS_DIR, ICONS_CACHE_DIR]:
        os.makedirs(d, exist_ok=True)
except Exception as e:
    # Log permission errors to a safe location
    try:
        temp_log = os.path.join(os.environ.get('TEMP', os.path.expanduser('~')), 'ima_menu_boot_error.log')
        with open(temp_log, 'a', encoding='utf-8') as f:
            import time
            f.write(f"[{time.ctime()}] Failed to create dirs in {APP_BASE_PATH}: {str(e)}\n")
    except: pass

def _cleanup_old_executables():
    try:
        temp_dir = tempfile.gettempdir()
        for item_name in ['iMA_Launcher_Update.exe', 'iMA_Launcher_Update.exe.tmp', 'ima_update_runner.cmd', 'ima_update_runner.ps1', 'ima_apply_update.vbs', 'ima_just_updated.txt', 'ima_launcher_version.txt']:
            file_path = os.path.join(temp_dir, item_name)
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except Exception:
                    pass
        if getattr(sys, 'frozen', False):
            current_directory = os.path.dirname(os.path.abspath(sys.executable))
        else:
            current_directory = APP_BASE_PATH
        for old_file_name in ['launcher.old.exe', 'launcher.exe.old', 'launcher.exe.bak', 'launcher.exe.tmp']:
            old_file_path = os.path.join(current_directory, old_file_name)
            if os.path.exists(old_file_path):
                try:
                    os.remove(old_file_path)
                except Exception:
                    pass
    except Exception:
        pass

_cleanup_old_executables()

def _restore_bundled_assets():
    if not getattr(sys, 'frozen', False): return
    try:
        # Bundled source (from _MEIPASS)
        bundled_icons = resource_path('icons')
        if not os.path.exists(bundled_icons): return
        
        # Check if physical folder is empty or key icons missing
        if not os.path.exists(LAUNCHER_ICONS_DIR) or not os.listdir(LAUNCHER_ICONS_DIR):
            for item in os.listdir(bundled_icons):
                src = os.path.join(bundled_icons, item)
                dst = os.path.join(LAUNCHER_ICONS_DIR, item)
                if os.path.isfile(src) and not os.path.exists(dst):
                    shutil.copy2(src, dst)
    except: pass

_restore_bundled_assets()

def get_app_base_path():
    # Detect flags from arguments
    open_only = "--open-only" in sys.argv
    close_only = "--close-only" in sys.argv
    
    # ALWAYS close any open context menus first to prevent stacking
    import win32gui, win32con
    hwnd_menu = win32gui.FindWindow("#32768", None)
    while hwnd_menu:
        win32gui.SendMessage(hwnd_menu, win32con.WM_CLOSE, 0, 0)
        hwnd_menu = win32gui.FindWindow("#32768", None)

    if not open_only:
        # Trigger reload using global constants
        root = PROJECT_ROOT
        
        # Touch config files to ensure shell notices changes
        for f in ['shell.nss', 'imports/modify.nss', 'imports/theme.nss']:
            fp = os.path.join(root, f)
            if os.path.exists(fp):
                try: os.utime(fp, None)
                except: pass

        exe = os.path.join(root, 'shell.exe')
        if os.path.exists(exe):
            clean_environment = os.environ.copy()
            for key in list(clean_environment.keys()):
                if key.startswith('_MEI'):
                    clean_environment.pop(key, None)
            subprocess.Popen([exe, '-reload'], env=clean_environment, creationflags=0x08000000)
        
        if close_only: sys.exit(0)

    return APP_BASE_PATH

TEMP_DIR = os.environ.get('TEMP', os.path.expanduser('~'))

def _can_write_to_dir(directory_path):
    try:
        test_file_path = os.path.join(directory_path, '.write_test_tmp')
        with open(test_file_path, 'w') as test_file:
            test_file.write('x')
        os.remove(test_file_path)
        return True
    except Exception:
        return False

def _parse_version(version_tag):
    if not version_tag:
        return (0,)
    clean_tag = str(version_tag).lower().lstrip('v').split('-')[0].split('+')[0].strip()
    tag_parts = clean_tag.split('.')
    parsed_parts = []
    for part in tag_parts:
        try:
            parsed_parts.append(int(part))
        except ValueError:
            parsed_parts.append(0)
    return tuple(parsed_parts) if parsed_parts else (0,)

APP_VERSION = '2.0.9'
VERSION = APP_VERSION

class UpdateWorker(QObject):
    check_finished = pyqtSignal(bool, str, str)
    download_progress = pyqtSignal(int)
    download_finished = pyqtSignal(bool, str)

    def check_for_updates(self, force=False):
        try:
            candidates = []
            parsed_current = _parse_version(VERSION)

            # 1. CDN-based version manifest with cache-buster
            cdn_url = f"https://raw.githubusercontent.com/{_GITHUB_REPO}/main/version.json?t={int(time.time())}"
            try:
                cdn_res = cdn_get(cdn_url, max_retries=2, timeout=REQUEST_TIMEOUT)
                if cdn_res.status_code == 200:
                    cdn_data = cdn_res.json()
                    remote_v = str(cdn_data.get('version', '')).lstrip('vV').strip()
                    dl_url = cdn_data.get('download_url')
                    if remote_v and dl_url:
                        candidates.append((_parse_version(remote_v), remote_v, dl_url))
            except Exception:
                pass

            # 2. GitHub Releases API (query all releases and sort descending)
            endpoints = [
                f"https://api.github.com/repos/{_GITHUB_REPO}/releases?per_page=15",
                f"https://api.github.com/repos/{_GITHUB_REPO}/releases/latest"
            ]
            for endpoint in endpoints:
                try:
                    response = github_api_get(endpoint, max_retries=2, timeout=REQUEST_TIMEOUT)
                    if response.status_code == 200:
                        raw_data = response.json()
                        releases_list = raw_data if isinstance(raw_data, list) else [raw_data]
                        for release_data in releases_list:
                            tag_name = release_data.get('tag_name', '')
                            remote_version = tag_name.lstrip('vV').strip()
                            if not remote_version:
                                continue
                            parsed_v = _parse_version(remote_version)
                            download_url = None
                            for asset in release_data.get('assets', []):
                                asset_name = asset.get('name', '').lower()
                                if asset_name.endswith('.exe'):
                                    download_url = asset.get('browser_download_url')
                                    if 'launcher' in asset_name:
                                        break
                            if download_url:
                                candidates.append((parsed_v, remote_version, download_url))
                except Exception:
                    pass

            # Sort all candidates to find absolute highest available release
            if candidates:
                candidates.sort(key=lambda x: x[0], reverse=True)
                highest_parsed, highest_v_str, highest_url = candidates[0]

                if highest_parsed > parsed_current:
                    self.check_finished.emit(True, highest_v_str, highest_url)
                    return
                elif force:
                    target_v = highest_v_str if highest_parsed >= parsed_current else VERSION
                    self.check_finished.emit(True, target_v, highest_url)
                    return

            self.check_finished.emit(False, VERSION, None)
        except Exception:
            self.check_finished.emit(False, VERSION, None)

    def download_update(self, target_url):
        if getattr(sys, 'frozen', False):
            app_dir = os.path.dirname(os.path.abspath(sys.executable))
        else:
            app_dir = APP_BASE_PATH

        if _can_write_to_dir(app_dir):
            final_destination = os.path.join(app_dir, 'launcher.new.exe')
        else:
            final_destination = os.path.join(tempfile.gettempdir(), 'launcher.new.exe')
        temp_destination = final_destination + '.tmp'

        try:
            if os.path.exists(temp_destination):
                try: os.remove(temp_destination)
                except Exception: pass
            if os.path.exists(final_destination):
                try: os.remove(final_destination)
                except Exception: pass

            if os.path.exists(target_url) and os.path.isfile(target_url):
                shutil.copy2(target_url, temp_destination)
                self.download_progress.emit(100)
            else:
                response = requests.get(target_url, stream=True, timeout=60, headers={"User-Agent": "iMA-Menu-Updater"})
                response.raise_for_status()
                total_bytes = int(response.headers.get('content-length', 0))
                downloaded_bytes = 0
                with open(temp_destination, 'wb') as output_file:
                    for data_chunk in response.iter_content(chunk_size=262144):
                        if data_chunk:
                            output_file.write(data_chunk)
                            downloaded_bytes += len(data_chunk)
                            if total_bytes > 0:
                                progress_percentage = min(100, int((downloaded_bytes / total_bytes) * 100))
                                self.download_progress.emit(progress_percentage)
                if total_bytes > 0 and downloaded_bytes < total_bytes:
                    raise IOError(f'Incomplete download: received {downloaded_bytes}/{total_bytes} bytes')

            if not os.path.exists(temp_destination) or os.path.getsize(temp_destination) < 1024 * 100:
                raise ValueError("Downloaded file is invalid or corrupted")

            with open(temp_destination, 'rb') as binary_file:
                magic_bytes = binary_file.read(2)
                if magic_bytes != b'MZ':
                    raise ValueError("Downloaded file is not a valid Windows executable")

            if os.path.exists(final_destination):
                try: os.remove(final_destination)
                except Exception: pass
            os.replace(temp_destination, final_destination)
            self.download_finished.emit(True, final_destination)
        except Exception as error_message:
            if os.path.exists(temp_destination):
                try: os.remove(temp_destination)
                except Exception: pass
            self.download_finished.emit(False, str(error_message))


class SettingsManager:
    def __init__(self):
        self.defaults = {
            "auto_update": False,
            "auto_check_updates": False,
            "auto_save": False,
            "auto_apply_theme_colors": False,
            "auto_preview_context_menu": False
        }
        self.settings = self.defaults.copy()
        self.load()

    def load(self):
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, 'r') as f:
                    self.settings.update(json.load(f))
            except Exception:
                pass
        else:
            # Create default settings if missing
            self.save()

    def save(self):
        try:
            os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
            with open(SETTINGS_FILE, 'w') as f:
                json.dump(self.settings, f, indent=4)
        except Exception:
            pass

    def get(self, key):
        return self.settings.get(key, self.defaults.get(key))

    def set(self, key, value):
        self.settings[key] = value
        self.save()


def get_auth_headers():
    return {}

def resolve_path(path_str):
    resolved_path = os.path.normpath(os.path.expandvars(path_str))
    if os.path.isabs(resolved_path):
        return resolved_path

    project_name = os.path.basename(PROJECT_ROOT)
    path_parts = resolved_path.split(os.sep)
    if path_parts and path_parts[0] == project_name:
        resolved_path = os.path.join(*path_parts[1:])

    return os.path.join(PROJECT_ROOT, resolved_path)

def get_plugin_install_path(plugin_data):
    install_path_str = plugin_data.get('install_path')
    if not install_path_str:
        return os.path.join(PLUGINS_DIR, plugin_data['name'])
    return resolve_path(install_path_str)

class ModernSwitch(QWidget):
    stateChanged = pyqtSignal(bool)
    def __init__(self, parent=None, checked=False):
        super().__init__(parent); self.setFixedSize(50, 26); self._checked = checked; self._pos_val = 1.0 if checked else 0.0
        self._anim = QPropertyAnimation(self, b"pos_val"); self._anim.setDuration(400); self._anim.setEasingCurve(QEasingCurve.OutBack)
        self.setCursor(Qt.PointingHandCursor)
    @pyqtProperty(float)
    def pos_val(self): return self._pos_val
    @pos_val.setter
    def pos_val(self, v): self._pos_val = v; self.update()
    def mousePressEvent(self, e): self._checked = not self._checked; self._anim.setStartValue(self._pos_val); self._anim.setEndValue(1.0 if self._checked else 0.0); self._anim.start(); self.stateChanged.emit(self._checked)
    def isChecked(self): return self._checked
    def setChecked(self, v): self._checked = v; self._pos_val = 1.0 if v else 0.0; self.update()
    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing); r = self.rect(); bg = QColor("#dc143c") if self._checked else QColor("#2a2a30")
        p.setBrush(bg); p.setPen(Qt.NoPen); p.drawRoundedRect(r, r.height()/2, r.height()/2); handle = QColor("#ffffff") if self._checked else QColor("#b0b0b0")
        p.setBrush(handle); x = 4 + (r.width() - 24) * self._pos_val; p.drawEllipse(int(x), 4, 18, 18)

class ModernTabBar(QTabBar):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDrawBase(False)
        self.setCursor(Qt.PointingHandCursor)
        self.setObjectName("modernTabBar")

class ModernTabWidget(QTabWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTabBar(ModernTabBar())
        self.setObjectName("modernTabWidget")
        self.setIconSize(QSize(28, 28))
        self.setStyleSheet("""
            QTabWidget#modernTabWidget::pane { 
                border: none; 
                background: transparent; 
            }
        """)

class ModernDialog(QDialog):
    def __init__(self, parent=None, title="Message", text=""):
        super().__init__(parent); self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog); self.setAttribute(Qt.WA_TranslucentBackground); self.setMinimumWidth(400)
        l = QVBoxLayout(self); self.f = QFrame(); self.f.setObjectName("modalFrame"); self.f.setStyleSheet("#modalFrame { background-color: #121212; border: 1px solid #2a2a30; border-radius: 20px; }"); l.addWidget(self.f)
        self.cl = QVBoxLayout(self.f); self.cl.setContentsMargins(30, 30, 30, 30); self.cl.setSpacing(15)
        self.tl = QLabel(title); self.tl.setStyleSheet("color: white; font-size: 20px; font-weight: bold; border: none;"); self.cl.addWidget(self.tl)
        self.ml = QLabel(text); self.ml.setStyleSheet("color: #b0b0b0; font-size: 14px; border: none;"); self.ml.setWordWrap(True); self.cl.addWidget(self.ml)
        self.bl = QHBoxLayout(); self.bl.setSpacing(10); self.cl.addLayout(self.bl)
        self.add_button("Close", "secondaryButton", self.accept)
    def add_button(self, text, style_obj, callback):
        # Remove default button if a new one is added manually
        if self.bl.count() == 1 and isinstance(self.bl.itemAt(0).widget(), QPushButton) and self.bl.itemAt(0).widget().text() == "Close":
            w = self.bl.itemAt(0).widget(); self.bl.removeWidget(w); w.hide(); w.setParent(None); w.deleteLater()
        b = QPushButton(text); b.setFixedHeight(40); b.setCursor(Qt.PointingHandCursor); b.setObjectName(style_obj); b.clicked.connect(callback); self.bl.addWidget(b); return b
    def mousePressEvent(self, e):
        if not self.f.geometry().contains(e.pos()): self.reject()
_crisp_pixmap_cache = {}

def load_crisp_pixmap(icon_path, target_size=96):
    if not icon_path or not os.path.exists(icon_path):
        return QPixmap()
    cache_key = (icon_path, target_size)
    if cache_key in _crisp_pixmap_cache:
        return _crisp_pixmap_cache[cache_key]
    try:
        icon = QIcon(icon_path)
        if not icon.isNull():
            pix = icon.pixmap(target_size, target_size)
            if not pix.isNull():
                _crisp_pixmap_cache[cache_key] = pix
                return pix
        pix = QPixmap(icon_path)
        if not pix.isNull():
            if pix.width() > target_size or pix.height() > target_size:
                pix = pix.scaled(target_size, target_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            _crisp_pixmap_cache[cache_key] = pix
            return pix
        return QPixmap()
    except Exception:
        return QPixmap()

def find_plugin_nss_info(plugin_name, plugin_dir):
    if not plugin_dir or not os.path.exists(plugin_dir):
        return None, None
    target_nss = None
    try:
        for root, dirs, files in os.walk(plugin_dir):
            for f in files:
                if f.lower() == f"{plugin_name.lower()}.nss":
                    target_nss = os.path.join(root, f)
                    break
                elif f.lower().endswith('.nss') and not target_nss:
                    target_nss = os.path.join(root, f)
            if target_nss:
                break
    except Exception:
        pass

    if not target_nss:
        return None, None

    nss_dir = os.path.dirname(target_nss)
    nss_file = os.path.basename(target_nss)
    return nss_dir, nss_file

def is_plugin_nss_enabled(plugin_name, plugin_dir=None, nss_file_path=None):
    if not nss_file_path:
        nss_file_path = os.path.join(PROJECT_ROOT, 'shell.nss')
    
    folder_pattern = f"plugins/{plugin_name.lower()}/"

    try:
        with open(nss_file_path, 'r', encoding='utf-8-sig') as f:
            lines = f.readlines()
        return any(line.strip().lower().startswith("import") and folder_pattern in line.strip().lower() for line in lines)
    except Exception:
        return False

def add_nss_import(plugin_data, nss_file_path):
    if not plugin_data or not nss_file_path or not os.path.exists(nss_file_path):
        return

    nss_path = resolve_path(plugin_data.get('nss_path', '')) if isinstance(plugin_data, dict) else ''
    nss_file = plugin_data.get('nss_file', '') if isinstance(plugin_data, dict) else ''
    if not nss_file:
        return

    relative_nss_path = os.path.relpath(nss_path, PROJECT_ROOT).replace(os.sep, '/') if nss_path else 'imports'
    import_statement = f"import '{relative_nss_path}/{nss_file}'\n"

    try:
        with open(nss_file_path, 'r', encoding='utf-8-sig') as f:
            lines = f.readlines()

        for line in lines:
            line_lower = line.strip().lower()
            if line_lower.startswith("import"):
                if nss_file.lower() in line_lower:
                    return

        last_import_index = -1
        for i, line in enumerate(lines):
            if line.strip().lower().startswith("import"):
                last_import_index = i
        
        if last_import_index != -1:
            lines.insert(last_import_index + 1, import_statement)
        else:
            lines.append(import_statement)

        safe_file_write(nss_file_path, "".join(lines))
    except Exception as e:
        print(f"Error updating {nss_file_path}: {e}")

def remove_nss_import(plugin_data, nss_file_path):
    if not nss_file_path or not os.path.exists(nss_file_path):
        return
        
    plugin_name = ""
    nss_path = ""
    nss_file = ""
    if isinstance(plugin_data, str):
        plugin_name = plugin_data.strip()
    elif isinstance(plugin_data, dict):
        plugin_name = (plugin_data.get('name') or '').strip()
        nss_path_raw = plugin_data.get('nss_path') or ''
        if nss_path_raw:
            nss_path = resolve_path(nss_path_raw)
        nss_file = (plugin_data.get('nss_file') or '').strip()

    name_lower = plugin_name.lower() if plugin_name else ""
    nss_file_lower = nss_file.lower() if nss_file else ""
    folder_name = os.path.basename(nss_path).lower() if nss_path else ""
    project_base_name = os.path.basename(PROJECT_ROOT).lower()

    try:
        with open(nss_file_path, 'r', encoding='utf-8-sig') as f:
            lines = f.readlines()
        
        new_lines = []
        for line in lines:
            line_str = line.strip()
            line_lower = line_str.lower()
            if not line_lower.startswith("import"):
                new_lines.append(line)
                continue

            target_matched = False
            
            # 1. Match explicit nss_file if known (e.g. 'organize.nss')
            if nss_file_lower and nss_file_lower in line_lower:
                target_matched = True
                
            # 2. Match folder_name if valid and not project root
            elif folder_name and folder_name != project_base_name:
                if f"plugins/{folder_name}/" in line_lower or f"plugins/{folder_name}.nss" in line_lower or f"/{folder_name}/" in line_lower:
                    target_matched = True

            # 3. Match plugin_name (e.g. 'organize')
            if not target_matched and name_lower:
                if (f"plugins/{name_lower}/" in line_lower or 
                    f"plugins/{name_lower}.nss" in line_lower or 
                    f"/{name_lower}.nss" in line_lower or 
                    f"'{name_lower}.nss'" in line_lower or 
                    f'"{name_lower}.nss"' in line_lower or
                    f"'{name_lower}/" in line_lower or
                    f'"{name_lower}/' in line_lower):
                    target_matched = True

            # 4. Regex parsing for import 'path'
            if not target_matched:
                m = re.search(r"import\s+['\"]([^'\"]+)['\"]", line_str, re.IGNORECASE)
                if m:
                    imported_path = m.group(1).replace('\\', '/').lower().strip('/')
                    parts = imported_path.split('/')
                    if len(parts) >= 2 and parts[0] == 'plugins':
                        if name_lower and parts[1] == name_lower:
                            target_matched = True
                        elif folder_name and folder_name != project_base_name and parts[1] == folder_name:
                            target_matched = True
                        elif nss_file_lower and (parts[-1] == nss_file_lower or nss_file_lower in parts[-1]):
                            target_matched = True

            if target_matched:
                continue

            new_lines.append(line)

        safe_file_write(nss_file_path, "".join(new_lines))
    except Exception as e:
        print(f"Error removing import from {nss_file_path}: {e}")

TOOLS_MENU_TEMPLATE = """menu(mode="multiple" find='.mkv|.mp4|.webm|.flv|.m4p|.mov|.png|.jpg|.jpeg|.svg|.webp|.bmp|.ico|.gif' title='Tools' image =["\\uE0F8"])
{
}
"""

TOOLS_TARGET_PLUGINS = {'imgur', 'resize', 'image2ico', 'convert to ico'}

def is_tools_plugin(name):
    if not name:
        return False
    normalized = str(name).strip().lower()
    return normalized in TOOLS_TARGET_PLUGINS or any(normalized == target or normalized.startswith(f"{target}.") or normalized.endswith(f"/{target}") for target in TOOLS_TARGET_PLUGINS)

def check_tools_menu_in_file(file_path):
    try:
        if not os.path.exists(file_path):
            return False
        with open(file_path, 'r', encoding='utf-8-sig', errors='ignore') as f:
            file_content = f.read()
        if re.search(r'\bmenu\s*\([^)]*title\s*=\s*[\'"]?\s*tools\s*[\'"]?[^)]*\)', file_content, re.IGNORECASE):
            return True
        from modify_widget import find_items_and_menus
        parsed_entries = find_items_and_menus(file_content, types=('menu',))
        for entry in parsed_entries:
            title_value = entry.get('props', {}).get('title', '')
            if isinstance(title_value, str) and title_value.strip('\'" ').lower() == 'tools':
                return True
        return False
    except Exception:
        return False

def sync_tools_menu(project_root=None, registry=None):
    if not project_root:
        project_root = PROJECT_ROOT
    modify_nss_path = os.path.join(project_root, 'imports', 'modify.nss')
    plugins_directory = os.path.join(project_root, 'plugins')
    
    tools_menu_exists_elsewhere = False
    for root_dir, sub_dirs, dir_files in os.walk(project_root):
        sub_dirs[:] = [d for d in sub_dirs if d.lower() not in ('cache', '_internal', 'build', 'dist', '.git', 'node_modules', 'temp')]
        for single_file in dir_files:
            if single_file.lower().endswith('.nss'):
                resolved_path = os.path.normpath(os.path.join(root_dir, single_file))
                if os.path.normcase(resolved_path) == os.path.normcase(os.path.normpath(modify_nss_path)):
                    continue
                if check_tools_menu_in_file(resolved_path):
                    tools_menu_exists_elsewhere = True
                    break
        if tools_menu_exists_elsewhere:
            break

    if tools_menu_exists_elsewhere:
        return

    active_tools_plugin_present = False
    if registry:
        for plugin_name_key in getattr(registry, 'plugins', {}).keys():
            if is_tools_plugin(plugin_name_key) and registry.is_installed(plugin_name_key):
                active_tools_plugin_present = True
                break
                
    if not active_tools_plugin_present and os.path.exists(plugins_directory):
        try:
            for dir_entry in os.listdir(plugins_directory):
                entry_full_path = os.path.join(plugins_directory, dir_entry)
                if os.path.isdir(entry_full_path) and is_tools_plugin(dir_entry):
                    active_tools_plugin_present = True
                    break
        except Exception:
            pass

    try:
        os.makedirs(os.path.dirname(modify_nss_path), exist_ok=True)
        current_modify_content = ""
        if os.path.exists(modify_nss_path):
            with open(modify_nss_path, 'r', encoding='utf-8-sig', errors='ignore') as f:
                current_modify_content = f.read()
                
        tools_menu_in_modify = bool(re.search(r'\bmenu\s*\([^)]*title\s*=\s*[\'"]?\s*tools\s*[\'"]?[^)]*\)', current_modify_content, re.IGNORECASE))

        if active_tools_plugin_present:
            if not tools_menu_in_modify:
                updated_content = current_modify_content.rstrip()
                if updated_content:
                    updated_content += "\n\n" + TOOLS_MENU_TEMPLATE
                else:
                    updated_content = TOOLS_MENU_TEMPLATE
                safe_file_write(modify_nss_path, updated_content)
        else:
            if tools_menu_in_modify:
                removal_pattern = r'\n?\s*menu\s*\([^)]*title\s*=\s*[\'"]?\s*tools\s*[\'"]?[^)]*\)\s*\{\s*\}\s*'
                updated_content = re.sub(removal_pattern, '\n', current_modify_content, flags=re.IGNORECASE).strip()
                if updated_content:
                    updated_content += "\n"
                safe_file_write(modify_nss_path, updated_content)
    except Exception as error:
        print(f"Error syncing tools menu: {error}")

def add_to_path(directory):
    try:
        key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, "Environment")
        try:
            current_path, _ = winreg.QueryValueEx(key, "Path")

            if directory not in current_path.split(os.pathsep):
                new_path = f"{current_path}{os.pathsep}{directory}"
                winreg.SetValueEx(key, "Path", 0, winreg.REG_EXPAND_SZ, new_path)
                print(f"Added {directory} to system PATH.")
            else:
                print(f"{directory} is already in system PATH.")
        finally:
            winreg.CloseKey(key)
    except Exception as e:
        print(f"Error adding {directory} to PATH: {e}")

def find_riot_client_path():
    from pathlib import Path
    try:
        key_path = r'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Riot Game valorant.live'
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
            loc, _ = winreg.QueryValueEx(key, 'InstallLocation')
            if loc and os.path.isdir(loc):
                p = os.path.join(loc, 'RiotClientServices.exe')
                if os.path.exists(p): return p
    except Exception: pass

    try:
        key_path = r'SOFTWARE\Riot Games\Riot Client'
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as key:
            p, _ = winreg.QueryValueEx(key, 'ExecutablePath')
            if p and os.path.exists(p): return p
    except Exception: pass

    installs_json = Path(os.getenv('ALLUSERSPROFILE', 'C:/ProgramData')) / 'Riot Games' / 'RiotClientInstalls.json'
    if installs_json.exists():
        try:
            with open(installs_json, 'r') as f:
                data = json.load(f)
                for k in ('rc_default', 'rc_live', 'associated_client'):
                    if k in data and os.path.exists(data[k]):
                        return data[k]
        except Exception: pass

    common_paths = [
        r'C:\Riot Games\Riot Client\RiotClientServices.exe',
        os.path.join(os.getenv('PROGRAMFILES', 'C:/Program Files'), 'Riot Games', 'Riot Client', 'RiotClientServices.exe'),
        os.path.join(os.getenv('PROGRAMFILES(X86)', 'C:/Program Files (x86)'), 'Riot Games', 'Riot Client', 'RiotClientServices.exe'),
        r'D:\Riot Games\Riot Client\RiotClientServices.exe',
        r'E:\Riot Games\Riot Client\RiotClientServices.exe',
    ]
    for cp in common_paths:
        if os.path.exists(cp): return cp
    return None

def fetch_ima_switcher_release():
    icon_url = "https://raw.githubusercontent.com/iMAboud/iMA-Switcher/main/Assets/ima.png"
    try:
        url = "https://api.github.com/repos/iMAboud/iMA-Switcher/releases/latest"
        res = github_api_get(url, max_retries=2, timeout=REQUEST_TIMEOUT)
        if res.status_code == 200:
            data = res.json()
            raw_tag = data.get('tag_name', '1.0.29')
            tag = raw_tag.lstrip('vV')
            dl_url = None
            for asset in data.get('assets', []):
                if asset.get('name', '').lower() == 'ima.switcher.installer.exe':
                    dl_url = asset.get('browser_download_url')
                    break
            if not dl_url:
                dl_url = f"https://github.com/iMAboud/iMA-Switcher/releases/download/{raw_tag}/iMA.Switcher.Installer.exe"
            return {
                "name": "iMA Switcher",
                "description": "Modern Valorant & Riot Games Account Switcher",
                "version": tag,
                "download_url": dl_url,
                "icon_url": icon_url,
                "repo": "iMAboud/iMA-Switcher",
                "custom_repo": True
            }
    except Exception:
        pass
    return {
        "name": "iMA Switcher",
        "description": "Modern Valorant & Riot Games Account Switcher",
        "version": "1.0.27",
        "download_url": "https://github.com/iMAboud/iMA-Switcher/releases/download/V1.0.27/iMA.Switcher.Installer.exe",
        "icon_url": icon_url,
        "repo": "iMAboud/iMA-Switcher",
        "custom_repo": True
    }

class FetchPluginsThread(QObject):
    finished = pyqtSignal(list, dict)
    error = pyqtSignal(str)

    def __init__(self, token=None):
        super().__init__()
        self.token = token

    def run(self):
        try:
            response = cdn_get(GITHUB_PLUGINS_JSON_URL, max_retries=3, timeout=REQUEST_TIMEOUT)
            plugins = response.json()
            if not isinstance(plugins, list):
                raise ValueError("Manifest response is not a valid list")

            try:
                atomic_json_write(PLUGINS_CACHE_FILE, plugins)
            except Exception:
                pass

            switcher_info = fetch_ima_switcher_release()
            found_switcher = False
            for p in plugins:
                if isinstance(p, dict) and p.get('name', '').lower() in ('ima switcher', 'ima-switcher', 'switcher'):
                    p['version'] = switcher_info['version']
                    p['download_url'] = switcher_info['download_url']
                    p['custom_repo'] = True
                    found_switcher = True
                    break
            if not found_switcher:
                plugins.append(switcher_info)

            tree_data = None
            try:
                root_tree_sha = get_latest_tree_sha(repo=_GITHUB_REPO, branch="main", timeout=REQUEST_TIMEOUT)

                if os.path.exists(GIT_TREE_CACHE_FILE):
                    try:
                        cache_data = safe_json_read(GIT_TREE_CACHE_FILE)
                        if cache_data and cache_data.get('sha') == root_tree_sha:
                            tree_data = cache_data.get('tree')
                    except Exception:
                        tree_data = None

                if tree_data is None and root_tree_sha:
                    trees_api_url = f"{GITHUB_API_BASE_URL}/git/trees/{root_tree_sha}?recursive=true"
                    tree_res = github_api_get(trees_api_url, max_retries=3, timeout=REQUEST_TIMEOUT)
                    tree_data = tree_res.json()
                    try:
                        atomic_json_write(GIT_TREE_CACHE_FILE, {'sha': root_tree_sha, 'tree': tree_data})
                    except Exception:
                        pass
            except Exception as tree_err:
                print(f"Non-critical tree fetch error (falling back to CDN/archive): {tree_err}")
                tree_data = {}

            self.finished.emit(plugins, tree_data or {})
        except requests.exceptions.RequestException as e:
            self.error.emit(f"Network error: {e}")
        except Exception as e:
            self.error.emit(f"Error checking plugins: {e}")

class PillProgressBar(QWidget):
    def __init__(self, parent=None, height=20):
        super().__init__(parent); self.setFixedHeight(height); self.value = 0
        self.setMinimumWidth(120)
        self.main_layout = QHBoxLayout(self); self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.groove = QFrame(); self.groove.setObjectName("pillGroove")
        self.groove.setStyleSheet(f"QFrame#pillGroove {{ background-color: rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: {height//2}px; }}")
        self.fill = QFrame(self.groove); self.fill.setObjectName("pillFill")
        self.fill.setStyleSheet(f"QFrame#pillFill {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #dc143c, stop:1 #ff2a55); border-radius: {max(2, (height-4)//2)}px; }}")
        self.fill.setGeometry(2, 2, 0, height - 4); self.main_layout.addWidget(self.groove)
    def setValue(self, val):
        self.value = max(0, min(100, val))
        if self.value <= 0: self.fill.hide(); return
        self.fill.show()
        max_w = self.groove.width() - 4
        if max_w <= 0: return
        new_w = max(2, int(max_w * (self.value / 100)))
        self.fill.setGeometry(2, 2, new_w, self.height() - 4)
    def resizeEvent(self, e): super().resizeEvent(e); self.setValue(self.value)
    def setVisible(self, v): super().setVisible(v)

class IconDownloadWorker(QObject):
    finished = pyqtSignal(str, QPixmap)
    error = pyqtSignal(str)

    def __init__(self, plugin_name, url, save_path):
        super().__init__()
        self.plugin_name = plugin_name
        self.url = url
        self.save_path = save_path

    def run(self):
        pixmap = None
        try:
            response = cdn_get(self.url, max_retries=2, timeout=REQUEST_TIMEOUT)
            pixmap = QPixmap()
            pixmap.loadFromData(response.content)
            if not pixmap.isNull():
                pixmap.save(self.save_path)
            self.finished.emit(self.plugin_name, pixmap)
        except requests.exceptions.RequestException as e:
            print(f"Error downloading icon for {self.plugin_name}: {e}")
            pixmap = None
            self.error.emit(str(e))
        except Exception as e:
            print(f"Error processing icon for {self.plugin_name}: {e}")
            pixmap = None
            self.error.emit(str(e))

class InstallationWorker(QObject):
    progress = pyqtSignal(str, int)
    finished = pyqtSignal(str, str, dict, int)
    error = pyqtSignal(str, str, str)

    def __init__(self, plugin_data):
        super().__init__()
        self.plugin_data = plugin_data
        self.plugin_name = plugin_data['name']
        self._is_cancelled = False
        self.files_to_download = []

    def install_ima_switcher(self):
        try:
            target_dir = os.path.join(os.getenv('LOCALAPPDATA', ''), 'iMA Switcher')
            os.makedirs(target_dir, exist_ok=True)

            dl_url = self.plugin_data.get('download_url') or "https://github.com/iMAboud/iMA-Switcher/releases/download/V1.0.27/iMA.Switcher.Installer.exe"
            
            self.progress.emit(self.plugin_name, 10)
            res = cdn_get(dl_url, max_retries=3, timeout=45, stream=True)

            temp_installer = os.path.join(target_dir, "iMA_Switcher_Update.exe")
            target_exe = os.path.join(target_dir, "iMA Switcher.exe")

            total_size = int(res.headers.get('content-length', 0))
            downloaded = 0

            with open(temp_installer, 'wb') as f:
                for chunk in res.iter_content(chunk_size=262144):
                    if self._is_cancelled:
                        if os.path.exists(temp_installer):
                            try: os.remove(temp_installer)
                            except OSError: pass
                        self.finished.emit(self.plugin_name, "cancelled", {}, 0)
                        return
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            pct = int((downloaded / total_size) * 80) + 10
                            self.progress.emit(self.plugin_name, pct)

            if os.path.exists(target_exe):
                try: os.remove(target_exe)
                except OSError: pass

            shutil.copy2(temp_installer, target_exe)
            try: os.remove(temp_installer)
            except OSError: pass

            version_str = self.plugin_data.get('version', '1.0.27')
            with open(os.path.join(target_dir, 'version.txt'), 'w', encoding='utf-8') as f:
                f.write(version_str)

            riot_exe = find_riot_client_path()
            if riot_exe:
                config_file = os.path.join(target_dir, 'config.json')
                cfg = {}
                if os.path.exists(config_file):
                    try: cfg = json.load(open(config_file, 'r', encoding='utf-8'))
                    except Exception: cfg = {}
                cfg['riot_client_services_path'] = riot_exe
                atomic_json_write(config_file, cfg)

            app_nss = os.path.join(target_dir, 'valo.nss')
            imports_nss = os.path.join(PROJECT_ROOT, 'imports', 'valo.nss')
            if os.path.exists(app_nss) or os.path.exists(imports_nss):
                try:
                    add_nss_import({'nss_path': 'imports', 'nss_file': 'valo.nss'}, os.path.join(PROJECT_ROOT, 'shell.nss'))
                except Exception:
                    pass

            self.progress.emit(self.plugin_name, 100)
            self.finished.emit(self.plugin_name, "installed", {}, 1)
        except Exception as e:
            self.error.emit(self.plugin_name, "failed", str(e))

    def _install_from_repo_archive(self, staging_dir, file_hashes):
        """
        Fallback installation using direct repository ZIP download.
        Bypasses GitHub REST API rate limits.
        """
        zip_urls = [
            f"https://codeload.github.com/{_GITHUB_REPO}/zip/refs/heads/main",
            f"https://github.com/{_GITHUB_REPO}/archive/refs/heads/main.zip",
        ]
        
        last_error = None
        zip_bytes = None
        for url in zip_urls:
            if self._is_cancelled:
                return False
            try:
                self.progress.emit(self.plugin_name, 15)
                res = cdn_get(url, max_retries=2, timeout=45, stream=True)
                total_size = int(res.headers.get('content-length', 0))
                chunks = []
                downloaded = 0
                for chunk in res.iter_content(chunk_size=262144):
                    if self._is_cancelled:
                        return False
                    if chunk:
                        chunks.append(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            pct = 15 + int((downloaded / total_size) * 45)
                            self.progress.emit(self.plugin_name, min(pct, 60))
                zip_bytes = b"".join(chunks)
                if zip_bytes:
                    break
            except Exception as e:
                last_error = e
                continue

        if not zip_bytes:
            raise Exception(f"Failed to download repository archive: {last_error}")

        self.progress.emit(self.plugin_name, 65)
        import io
        extracted_any = False
        target_name_lower = self.plugin_name.strip().lower()

        with zipfile.ZipFile(io.BytesIO(zip_bytes), 'r') as zf:
            namelist = zf.namelist()
            matching_prefix = None
            for item in namelist:
                parts = item.replace('\\', '/').split('/')
                if len(parts) >= 2 and parts[1].strip().lower() == target_name_lower:
                    matching_prefix = f"{parts[0]}/{parts[1]}/"
                    break

            if not matching_prefix:
                for item in namelist:
                    parts = item.replace('\\', '/').split('/')
                    if len(parts) >= 1 and parts[0].strip().lower() == target_name_lower:
                        matching_prefix = f"{parts[0]}/"
                        break

            if not matching_prefix:
                raise Exception(f"Could not find folder for plugin '{self.plugin_name}' in repository archive.")

            for member in zf.infolist():
                if self._is_cancelled:
                    return False
                member_path = member.filename.replace('\\', '/')
                if member_path.startswith(matching_prefix) and not member.is_dir():
                    rel_path = member_path[len(matching_prefix):].strip('/')
                    if not rel_path:
                        continue
                    dest_path = os.path.join(staging_dir, rel_path)
                    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                    with zf.open(member) as src_f, open(dest_path, 'wb') as dst_f:
                        content = src_f.read()
                        dst_f.write(content)
                    file_hashes[rel_path] = git_blob_sha(dest_path)
                    extracted_any = True

        if not extracted_any:
            raise Exception(f"No files extracted for plugin '{self.plugin_name}' from repository archive.")

        self.progress.emit(self.plugin_name, 80)
        return True

    def run(self):
        if self.plugin_name.lower() in ('ima switcher', 'ima-switcher', 'switcher', 'valo'):
            self.install_ima_switcher()
            return

        staging_dir = os.path.join(PLUGINS_DIR, f".staging_{self.plugin_name}")
        backup_dir = os.path.join(PLUGINS_DIR, f".backup_{self.plugin_name}")
        target_plugin_dir = get_plugin_install_path(self.plugin_data)
        file_hashes = {}

        try:
            tree_data = self.plugin_data.get('_tree_data')
            
            if tree_data is None and os.path.exists(GIT_TREE_CACHE_FILE):
                try:
                    cache_age = time.time() - os.path.getmtime(GIT_TREE_CACHE_FILE)
                    cache_data = safe_json_read(GIT_TREE_CACHE_FILE)
                    if cache_data and isinstance(cache_data, dict) and cache_age < 300:
                        tree_data = cache_data.get('tree')
                except Exception:
                    tree_data = None

            if tree_data is None:
                try:
                    root_tree_sha = get_latest_tree_sha(repo=_GITHUB_REPO, branch="main", timeout=REQUEST_TIMEOUT)
                    if root_tree_sha:
                        trees_api_url = f"{GITHUB_API_BASE_URL}/git/trees/{root_tree_sha}?recursive=true"
                        tree_res = github_api_get(trees_api_url, max_retries=3, timeout=REQUEST_TIMEOUT)
                        tree_data = tree_res.json()
                        try:
                            atomic_json_write(GIT_TREE_CACHE_FILE, {'sha': root_tree_sha, 'tree': tree_data})
                        except Exception:
                            pass
                except Exception as e:
                    print(f"Git trees resolution failed, will attempt archive download fallback: {e}")
                    tree_data = None

            if tree_data and isinstance(tree_data, dict) and 'tree' in tree_data:
                plugin_path_prefix = f"{self.plugin_name}/"
                base_download_url = f"https://raw.githubusercontent.com/{_GITHUB_REPO}/main"

                for item in tree_data['tree']:
                    if self._is_cancelled:
                        if os.path.exists(staging_dir): shutil.rmtree(staging_dir)
                        self.finished.emit(self.plugin_name, "cancelled", {}, 0)
                        return
                    if item.get('type') == 'blob' and item['path'].startswith(plugin_path_prefix):
                        relative_path = item['path'][len(plugin_path_prefix):]
                        download_url = f"{base_download_url}/{item['path']}"
                        self.files_to_download.append({'url': download_url, 'path': relative_path, 'sha': item.get('sha')})

            if self._is_cancelled:
                if os.path.exists(staging_dir): shutil.rmtree(staging_dir)
                self.finished.emit(self.plugin_name, "cancelled", {}, 0)
                return

            if os.path.exists(staging_dir):
                shutil.rmtree(staging_dir)

            if self.files_to_download:
                self.download_files(staging_dir, file_hashes)
            else:
                # Fallback to repo archive ZIP download
                success = self._install_from_repo_archive(staging_dir, file_hashes)
                if not success and self._is_cancelled:
                    if os.path.exists(staging_dir): shutil.rmtree(staging_dir)
                    self.finished.emit(self.plugin_name, "cancelled", {}, 0)
                    return

            if self._is_cancelled:
                if os.path.exists(staging_dir): shutil.rmtree(staging_dir)
                self.finished.emit(self.plugin_name, "cancelled", {}, 0)
                return

            if 'dependencies' in self.plugin_data:
                self.progress.emit(self.plugin_name, 0)
                self.download_dependencies(self.plugin_data['dependencies'])
                add_to_path(LIB_DIR)

            version_file_path = os.path.join(staging_dir, 'version')
            with open(version_file_path, 'w', encoding='utf-8') as f:
                f.write(self.plugin_data.get('version', '1.0.0'))

            terminate_plugin_processes(target_plugin_dir)
            import gc
            gc.collect()
            time.sleep(0.1)

            if os.path.exists(backup_dir):
                try: shutil.rmtree(backup_dir, ignore_errors=True)
                except Exception: pass

            if os.path.exists(target_plugin_dir):
                try:
                    os.rename(target_plugin_dir, backup_dir)
                except OSError:
                    time.sleep(0.2)
                    try:
                        os.rename(target_plugin_dir, backup_dir)
                    except OSError:
                        # Fallback: copy staging into target and clean staging
                        try: shutil.rmtree(backup_dir, ignore_errors=True)
                        except Exception: pass

            if os.path.exists(staging_dir):
                if os.path.exists(target_plugin_dir):
                    try:
                        shutil.rmtree(target_plugin_dir, ignore_errors=True)
                    except Exception:
                        pass
                try:
                    os.rename(staging_dir, target_plugin_dir)
                except OSError:
                    # Fallback copy if rename fails
                    shutil.copytree(staging_dir, target_plugin_dir, dirs_exist_ok=True)
                    shutil.rmtree(staging_dir, ignore_errors=True)

            if os.path.exists(backup_dir):
                try: shutil.rmtree(backup_dir, ignore_errors=True)
                except Exception: pass

            if self.plugin_data.get('launch') and self.plugin_data.get('launch_file'):
                launch_file_path = os.path.join(target_plugin_dir, self.plugin_data['launch_file'])
                if os.path.exists(launch_file_path):
                    try:
                        os.startfile(launch_file_path)
                    except Exception as e:
                        print(f"Failed to auto-launch {launch_file_path}: {e}")

            add_nss_import(self.plugin_data, os.path.join(PROJECT_ROOT, 'shell.nss'))
            self.finished.emit(self.plugin_name, "installed", file_hashes, len(file_hashes))
        except Exception as e:
            if self._is_cancelled:
                if os.path.exists(staging_dir):
                    try: shutil.rmtree(staging_dir)
                    except Exception: pass
                self.finished.emit(self.plugin_name, "cancelled", {}, 0)
                return
            if os.path.exists(staging_dir):
                try: shutil.rmtree(staging_dir)
                except Exception: pass
            if os.path.exists(backup_dir) and not os.path.exists(target_plugin_dir):
                try: os.rename(backup_dir, target_plugin_dir)
                except Exception: pass
            self.error.emit(self.plugin_name, "failed", str(e))

    def download_files(self, target_plugin_dir, file_hashes):
        os.makedirs(target_plugin_dir, exist_ok=True)
        total_files = len(self.files_to_download)
        for i, file_info in enumerate(self.files_to_download):
            if self._is_cancelled:
                return

            relative_path = file_info['path']
            local_path = os.path.join(target_plugin_dir, relative_path)
            os.makedirs(os.path.dirname(local_path), exist_ok=True)

            download_success = False
            last_err = None
            for attempt in range(3):
                if self._is_cancelled:
                    return
                try:
                    response = cdn_get(file_info['url'], max_retries=2, timeout=REQUEST_TIMEOUT)
                    with open(local_path, 'wb') as f:
                        f.write(response.content)
                    file_hashes[relative_path] = file_info.get('sha') or git_blob_sha(local_path)
                    download_success = True
                    break
                except Exception as e:
                    last_err = e
                    time.sleep(1.0 * (attempt + 1))
            
            if not download_success:
                raise last_err

            progress_val = int(((i + 1) / total_files) * 100)
            self.progress.emit(self.plugin_name, progress_val)

    def download_dependencies(self, dependencies):
        self.progress.emit(self.plugin_name, 0)
        total_dependencies = len(dependencies)
        for i, dep_info in enumerate(dependencies):
            if self._is_cancelled:
                return
            dep_name = dep_info['name']
            dep_path = os.path.join(LIB_DIR, dep_name)

            if os.path.exists(dep_path):
                print(f"Dependency {dep_name} already exists. Skipping download.")
                self.progress.emit(self.plugin_name, int(((i + 1) / total_dependencies) * 100))
                continue

            try:
                # Search through all releases for the dependency
                response = github_api_get(f"https://api.github.com/repos/{_GITHUB_REPO}/releases", max_retries=3, timeout=REQUEST_TIMEOUT)
                releases = response.json()

                asset_url = None
                for release in releases:
                    for asset in release.get('assets', []):
                        if asset['name'] == dep_name:
                            asset_url = asset['browser_download_url']
                            break
                    if asset_url: break
                
                if not asset_url:
                    raise Exception(f"Dependency {dep_name} not found in any release assets.")

                dep_response = cdn_get(asset_url, max_retries=3, timeout=REQUEST_TIMEOUT, stream=True)

                os.makedirs(LIB_DIR, exist_ok=True)
                with open(dep_path, 'wb') as f:
                    for chunk in dep_response.iter_content(chunk_size=262144):
                        if chunk:
                            f.write(chunk)
                print(f"Downloaded dependency: {dep_name}")
            except Exception as e:
                print(f"Error downloading dependency {dep_name}: {e}")
            self.progress.emit(self.plugin_name, int(((i + 1) / total_dependencies) * 100))

    def cancel(self):
        self._is_cancelled = True

class DetailsFetchWorker(QObject):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, plugin_name):
        super().__init__()
        self.plugin_name = plugin_name

    def run(self):
        try:
            temp_html_path = os.path.join(CACHE_DIR, f"{self.plugin_name}_details.html")
            temp_md_path = os.path.join(CACHE_DIR, f"{self.plugin_name}_details.md")

            # Priority 1: Check local installed plugin folder
            plugin_dir = os.path.join(PLUGINS_DIR, self.plugin_name)
            if not os.path.isdir(plugin_dir) and os.path.exists(PLUGINS_DIR):
                for d in os.listdir(PLUGINS_DIR):
                    if d.lower() == self.plugin_name.lower():
                        plugin_dir = os.path.join(PLUGINS_DIR, d)
                        break

            if os.path.isdir(plugin_dir):
                for candidate in ('details.md', 'README.md', 'readme.md', 'DETAILS.md'):
                    local_path = os.path.join(plugin_dir, candidate)
                    if os.path.exists(local_path):
                        try:
                            with open(local_path, 'r', encoding='utf-8', errors='ignore') as f:
                                markdown_content = f.read()
                            if markdown_content.strip():
                                html_content = self.markdown_to_html_with_images(markdown_content)
                                self.finished.emit(html_content)
                                return
                        except Exception:
                            pass

            # Priority 2: Check cached HTML
            if os.path.exists(temp_html_path):
                try:
                    with open(temp_html_path, 'r', encoding='utf-8', errors='ignore') as f:
                        cached_html = f.read()
                    if cached_html.strip():
                        self.finished.emit(cached_html)
                        return
                except Exception:
                    pass

            # Priority 3: Check cached Markdown
            if os.path.exists(temp_md_path):
                try:
                    with open(temp_md_path, 'r', encoding='utf-8', errors='ignore') as f:
                        cached_md = f.read()
                    if cached_md.strip():
                        html_content = self.markdown_to_html_with_images(cached_md)
                        try:
                            safe_file_write(temp_html_path, html_content)
                        except Exception:
                            pass
                        self.finished.emit(html_content)
                        return
                except Exception:
                    pass

            # Priority 4: Network fetch with cache saving
            if self.plugin_name.lower() in ('ima switcher', 'ima-switcher', 'switcher', 'valo'):
                details_urls = [
                    "https://raw.githubusercontent.com/iMAboud/iMA-Switcher/main/README.md",
                    "https://raw.githubusercontent.com/iMAboud/iMA-Switcher/master/README.md"
                ]
            else:
                details_urls = [
                    f"https://raw.githubusercontent.com/iMAboud/iMA-Menu-Plugins/main/{self.plugin_name}/README.md",
                    f"https://raw.githubusercontent.com/iMAboud/iMA-Menu-Plugins/main/{self.plugin_name}/readme.md",
                    f"https://raw.githubusercontent.com/iMAboud/iMA-Menu-Plugins/main/{self.plugin_name}/details.md",
                ]

            markdown_content = None
            for url in details_urls:
                try:
                    res = cdn_get(url, max_retries=2, timeout=REQUEST_TIMEOUT)
                    if res.status_code == 200 and res.text.strip():
                        markdown_content = res.text
                        break
                except Exception:
                    pass

            if markdown_content:
                try:
                    safe_file_write(temp_md_path, markdown_content)
                except Exception:
                    pass
                html_content = self.markdown_to_html_with_images(markdown_content)
                try:
                    safe_file_write(temp_html_path, html_content)
                except Exception:
                    pass
                self.finished.emit(html_content)
            else:
                # Generate clean synthetic overview from local NSS file or plugin metadata if present
                fallback_md = f"# {self.plugin_name}\n\nPlugin overview for **{self.plugin_name}**."
                if os.path.isdir(plugin_dir):
                    nss_files = [f for f in os.listdir(plugin_dir) if f.endswith('.nss')]
                    if nss_files:
                        fallback_md += f"\n\n### Script Files\n- `{nss_files[0]}`"
                html_content = self.markdown_to_html_with_images(fallback_md)
                self.finished.emit(html_content)
        except Exception as e:
            self.error.emit(str(e))

    def markdown_to_html_with_images(self, markdown_content):
        try:
            html_content = markdown.markdown(markdown_content, extensions=['tables', 'fenced_code', 'codehilite', 'nl2br', 'sane_lists'])
        except Exception:
            html_content = markdown.markdown(markdown_content)

        def replace_markdown_img(match):
            alt_text = match.group(1)
            src_url = match.group(2)
            if src_url and not src_url.startswith('data:'):
                try:
                    response = cdn_get(src_url, max_retries=2, timeout=REQUEST_TIMEOUT)
                    if response.status_code == 200:
                        encoded_img = base64.b64encode(response.content).decode('utf-8')
                        mime_type = response.headers.get('Content-Type', 'image/png')
                        data_uri = f"data:{mime_type};base64,{encoded_img}"
                        return f'<img alt="{alt_text}" src="{data_uri}">' 
                except Exception as e:
                    print(f"Failed to download or embed image {src_url}: {e}")
            return match.group(0)

        html_content = re.sub(r'!\((.*?)\)\((.*?)\)', replace_markdown_img, html_content)

        def replace_img_src(match):
            full_tag = match.group(0)
            src_url = match.group(1)
            if src_url and not src_url.startswith('data:'):
                try:
                    response = cdn_get(src_url, max_retries=2, timeout=REQUEST_TIMEOUT)
                    if response.status_code == 200:
                        encoded_img = base64.b64encode(response.content).decode('utf-8')
                        mime_type = response.headers.get('Content-Type', 'image/png')
                        data_uri = f"data:{mime_type};base64,{encoded_img}"
                        return full_tag.replace(src_url, data_uri)
                except Exception as e:
                    print(f"Failed to download or embed image {src_url}: {e}")
            return full_tag
        
        html_content = re.sub(r'<img[^>]+src="(.*?)"[^>]*>', replace_img_src, html_content)

        return f'''
        <html><head><style>
            body {{ color: #e6e6e6; background-color: transparent; overflow-x: hidden; margin: 0; padding: 12px; font-family: 'Segoe UI Variable Display', 'Segoe UI', sans-serif; font-size: 13px; line-height: 1.6; }}
            h1, h2, h3, h4, h5, h6 {{ color: #ffffff; margin-top: 1.2em; margin-bottom: 0.6em; font-weight: bold; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 4px; }}
            h1 {{ font-size: 20px; color: #dc143c; }}
            h2 {{ font-size: 16px; }}
            h3 {{ font-size: 14px; }}
            p {{ margin-bottom: 1em; color: #d0d0d0; }}
            a {{ color: #dc143c; text-decoration: none; font-weight: bold; }}
            a:hover {{ text-decoration: underline; }}
            img {{ max-width: 90%; max-height: 380px; height: auto; display: block; margin: 12px auto; border-radius: 10px; border: 1px solid rgba(255,255,255,0.1); }}
            ul, ol {{ margin-bottom: 1em; padding-left: 24px; color: #d0d0d0; }}
            li {{ margin-bottom: 4px; }}
            code {{ background: rgba(255,255,255,0.08); color: #ff7b72; padding: 2px 6px; border-radius: 6px; font-family: 'Consolas', 'Courier New', monospace; font-size: 12px; }}
            pre {{ background: #1a1a20; border: 1px solid #2a2a30; border-radius: 10px; padding: 12px; overflow-x: auto; color: #e6e6e6; }}
            pre code {{ background: transparent; padding: 0; color: inherit; }}
            blockquote {{ border-left: 4px solid #dc143c; background: rgba(220,20,60,0.08); margin: 0 0 1em 0; padding: 8px 16px; border-radius: 0 8px 8px 0; color: #cccccc; }}
            table {{ border-collapse: collapse; width: 100%; margin-bottom: 1em; background: rgba(255,255,255,0.02); border-radius: 8px; overflow: hidden; }}
            th, td {{ border: 1px solid #2a2a30; padding: 8px 12px; text-align: left; }}
            th {{ background: rgba(255,255,255,0.06); color: #ffffff; font-weight: bold; }}
            tr:nth-child(even) {{ background: rgba(255,255,255,0.02); }}
        </style></head><body>{html_content}</body></html>
        '''

class ClickableWidget(QWidget):
    plugin_card_clicked = pyqtSignal(str, QWidget)

    def __init__(self, plugin_name, parent=None):
        super().__init__(parent)
        self.plugin_name = plugin_name
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setMouseTracking(True)

    def mousePressEvent(self, event):
        self.plugin_card_clicked.emit(self.plugin_name, self)
        super().mousePressEvent(event)

class DetailsPopup(QWidget):
    def __init__(self, plugin_data, parent=None, start_geom=None):
        super().__init__(parent)
        self.plugin_data = plugin_data
        self.start_geom = start_geom
        self._is_closing = False
        self.setWindowFlags(Qt.SubWindow | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setObjectName("detailsPopup")
        self.setWindowOpacity(0.0)

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)

        title_bar = QWidget()
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(0, 0, 0, 0)

        icon_label = QLabel()
        icon_label.setFixedSize(40, 40)
        icon_label.setScaledContents(True)
        icon_pixmap = QPixmap()
        if self.plugin_data['name'].lower() in ('ima switcher', 'ima-switcher', 'switcher', 'valo'):
            switcher_appdata = os.path.join(os.getenv('LOCALAPPDATA', ''), 'iMA Switcher')
            candidates = [
                os.path.join(switcher_appdata, 'Assets', 'ima.png'),
                os.path.join(switcher_appdata, 'ima.png'),
                os.path.join(PROJECT_ROOT, 'iMA Switcher 1', 'Assets', 'ima.png'),
            ]
            for c in candidates:
                if os.path.exists(c):
                    icon_pixmap = load_crisp_pixmap(c, 128)
                    if not icon_pixmap.isNull():
                        break
        install_path = os.path.join(PLUGINS_DIR, self.plugin_data['name'])
        if icon_pixmap.isNull() and os.path.isdir(install_path):
            try:
                for fname in os.listdir(install_path):
                    if fname.lower().endswith(('.png', '.ico', '.jpg', '.svg')):
                        icon_pixmap = load_crisp_pixmap(os.path.join(install_path, fname), 128)
                        if not icon_pixmap.isNull():
                            break
            except Exception:
                pass
        if icon_pixmap.isNull():
            for cname in (f"{self.plugin_data['name']}.png", f"{self.plugin_data['name'].lower()}.png"):
                icon_pixmap = load_crisp_pixmap(os.path.join(ICONS_CACHE_DIR, cname), 128)
                if not icon_pixmap.isNull():
                    break
        if icon_pixmap.isNull():
            icon_pixmap = QPixmap(DEFAULT_ICON_PATH)
        icon_label.setPixmap(icon_pixmap)
        title_layout.addWidget(icon_label)

        title_label = QLabel(self.plugin_data['name'])
        title_label.setFont(QFont('Segoe UI Variable Display', 18, QFont.Bold))
        title_layout.addWidget(title_label)
        title_layout.addStretch()

        # Add Open Folder & Edit Item/Menu buttons if plugin is installed
        plugin_dir = get_plugin_install_path(self.plugin_data)
        if os.path.exists(plugin_dir):
            self.folder_button = QPushButton()
            self.folder_button.setIcon(QIcon(resource_path('icons/Open.png')))
            self.folder_button.setIconSize(QSize(18, 18))
            self.folder_button.setFixedSize(32, 32)
            self.folder_button.setToolTip("Open Plugin Directory")
            self.folder_button.setCursor(Qt.PointingHandCursor)
            self.folder_button.setStyleSheet("QPushButton { background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; } QPushButton:hover { background: rgba(220,20,60,0.2); border-color: #dc143c; }")
            self.folder_button.clicked.connect(lambda _, p=plugin_dir: os.startfile(p))
            title_layout.addWidget(self.folder_button)

            self.edit_button = QPushButton()
            self.edit_button.setIcon(QIcon(resource_path('icons/modify.png')))
            self.edit_button.setIconSize(QSize(18, 18))
            self.edit_button.setFixedSize(32, 32)
            self.edit_button.setToolTip("Edit Item/Menu (.nss)")
            self.edit_button.setCursor(Qt.PointingHandCursor)
            self.edit_button.setStyleSheet("QPushButton { background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; } QPushButton:hover { background: rgba(220,20,60,0.2); border-color: #dc143c; }")
            self.edit_button.clicked.connect(self._open_plugin_nss_editor)
            title_layout.addWidget(self.edit_button)

        close_button = QPushButton()
        close_button.setIcon(QIcon(resource_path('icons/x.png')))
        close_button.setIconSize(QSize(24, 24))
        close_button.setFixedSize(30, 30)
        close_button.setObjectName("iconButton")
        close_button.clicked.connect(self.close)
        title_layout.addWidget(close_button)
        self.layout.addWidget(title_bar)
        self._setup_body()

    def _open_plugin_nss_editor(self):
        plugin_dir = get_plugin_install_path(self.plugin_data)
        if not os.path.exists(plugin_dir):
            return
        from modify_widget import find_items_and_menus, ImportEditorDialog, MultiItemEditDialog, save_imported_item, read_file
        nss_files = []
        for r, _, files in os.walk(plugin_dir):
            for f in files:
                if f.endswith('.nss'):
                    nss_files.append(os.path.join(r, f))
        
        items = []
        for fp in nss_files:
            try:
                content = read_file(fp)
                if content:
                    find_items_and_menus.current_file = fp
                    for m in find_items_and_menus(content):
                        m['file'] = fp
                        items.append(m)
            except Exception:
                pass

        if not items:
            for fp in nss_files:
                os.startfile(fp)
            return

        if len(items) == 1:
            dlg = ImportEditorDialog(items[0], self)
            if dlg.exec_():
                save_imported_item(items[0], dlg.get_props())
        else:
            dlg = MultiItemEditDialog(items, self)
            if dlg.exec_():
                dlg.save_all()

    def _setup_body(self):
        description_label = QLabel(self.plugin_data.get('description', 'No description available.'))
        description_label.setWordWrap(True)
        self.layout.addWidget(description_label)

        self.details_browser = QTextBrowser()
        self.details_browser.setOpenExternalLinks(True)
        self.details_browser.setObjectName("detailsBrowser")
        self.details_browser.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.details_browser.setWordWrapMode(QTextOption.WordWrap)
        self.layout.addWidget(self.details_browser)

        self.action_button = QPushButton("Install")
        self.action_button.setObjectName("installButton")
        font = self.action_button.font()
        font.setBold(True)
        self.action_button.setFont(font)
        self.layout.addWidget(self.action_button, alignment=Qt.AlignRight)

    def set_details_content(self, content):
        self.details_browser.setHtml(content)

    def closeEvent(self, event):
        if self.start_geom and not self._is_closing:
            event.ignore()
            self._is_closing = True

            self.close_anim_group = QParallelAnimationGroup(self)
            
            geo_anim = QPropertyAnimation(self, b"geometry")
            geo_anim.setDuration(200)
            geo_anim.setStartValue(self.geometry())
            geo_anim.setEndValue(self.start_geom)
            geo_anim.setEasingCurve(QEasingCurve.OutQuint)
            self.close_anim_group.addAnimation(geo_anim)

            opac_anim = QPropertyAnimation(self, b"windowOpacity")
            opac_anim.setDuration(180)
            opac_anim.setStartValue(self.windowOpacity())
            opac_anim.setEndValue(0.0)
            opac_anim.setEasingCurve(QEasingCurve.OutQuad)
            self.close_anim_group.addAnimation(opac_anim)

            self.close_anim_group.finished.connect(self.close_actual)
            self.close_anim_group.start()
        else:
            super().closeEvent(event)

    def close_actual(self):
        super().close()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor(22, 22, 26, 245))
        painter.setPen(QPen(QColor(255, 255, 255, 30), 1))
        painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 16, 16)

class PluginLogic(QObject):
    plugins_fetched = pyqtSignal(list)
    fetch_error = pyqtSignal(str)
    icon_loaded = pyqtSignal(str, QPixmap)
    install_progress = pyqtSignal(str, int)
    install_started = pyqtSignal(str)
    operation_finished = pyqtSignal(str, str)
    operation_error = pyqtSignal(str, str, str)
    details_fetched = pyqtSignal(str)
    details_fetch_error = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.active_threads = {}
        self.installation_queue = deque()
        self.current_installing_plugin = None
        self.all_plugins_data = {}

        self.registry = PluginRegistry(PLUGIN_REGISTRY_FILE, PLUGINS_DIR)
        self.registry.load()
        self.registry.cleanup_staging()
        self.registry.reconcile_with_disk()

        # Preload cached plugins into all_plugins_data so metadata is available immediately
        if os.path.exists(PLUGINS_CACHE_FILE):
            try:
                cached_plugins = safe_json_read(PLUGINS_CACHE_FILE)
                if isinstance(cached_plugins, list):
                    for p in cached_plugins:
                        if isinstance(p, dict) and 'name' in p:
                            self.all_plugins_data[p['name']] = dict(p)
            except Exception:
                pass

    def get_auth_headers(self):
        return {}

    def fetch_plugins_list(self):
        thread = QThread(self)
        worker = FetchPluginsThread(None)
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.finished.connect(self._on_plugins_fetched)
        worker.error.connect(self.fetch_error.emit)
        worker.finished.connect(thread.quit)
        worker.error.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        worker.error.connect(worker.deleteLater)
        thread.finished.connect(lambda: self.cleanup_thread('plugin_list'))

        thread.start()
        self.active_threads['plugin_list'] = (thread, worker)

    def _on_plugins_fetched(self, plugins, tree_data):
        self.all_plugins_data = {}
        for p in plugins:
            item = dict(p)
            if tree_data:
                item['_tree_data'] = tree_data
            self.all_plugins_data[p['name']] = item
        self.registry.merge_remote_manifest(plugins, tree_data)
        ui_plugins = self.registry.get_all_plugins_for_ui()
        self.plugins_fetched.emit(ui_plugins)

    def _extract_nss_fallback_icon(self, plugin_name, install_path):
        try:
            if not os.path.exists(install_path):
                return None
            from modify_widget import find_items_and_menus, _update_label_asset, read_file
            nss_files = []
            for r, _, files in os.walk(install_path):
                for f in files:
                    if f.endswith('.nss'):
                        nss_files.append(os.path.join(r, f))
            
            menus = []
            items = []
            for fp in nss_files:
                try:
                    content = read_file(fp)
                    if content:
                        find_items_and_menus.current_file = fp
                        for entry in find_items_and_menus(content):
                            entry['file'] = fp
                            if entry.get('type') == 'menu':
                                menus.append(entry)
                            else:
                                items.append(entry)
                except Exception:
                    pass

            target_entry = (menus[0] if menus else (items[0] if items else None))
            if not target_entry:
                return None

            icon_val = (target_entry['props'].get('image') or target_entry['props'].get('icon') or '').strip('\'" ')
            if not icon_val:
                return None

            lbl = QLabel()
            lbl.setFixedSize(70, 70)
            _update_label_asset(lbl, icon_val, target_entry.get('file'))
            pix = lbl.grab()
            if pix and not pix.isNull():
                return pix
        except Exception as e:
            print(f"Error generating fallback icon for {plugin_name}: {e}")
        return None

    def load_icon(self, plugin):
        plugin_name = plugin['name']

        if plugin_name.lower() in ('ima switcher', 'ima-switcher', 'switcher', 'valo'):
            switcher_appdata = os.path.join(os.getenv('LOCALAPPDATA', ''), 'iMA Switcher')
            candidates = [
                os.path.join(switcher_appdata, 'Assets', 'ima.png'),
                os.path.join(switcher_appdata, 'ima.png'),
                os.path.join(PROJECT_ROOT, 'iMA Switcher 1', 'Assets', 'ima.png'),
            ]
            for c in candidates:
                if os.path.exists(c):
                    pix = load_crisp_pixmap(c, 128)
                    if not pix.isNull():
                        self.icon_loaded.emit(plugin_name, pix)
                        return

        # 1. Check local plugin directory if present on disk
        install_path = plugin.get('_install_path') or os.path.join(PLUGINS_DIR, plugin_name)
        if not os.path.isdir(install_path):
            install_path = os.path.join(PLUGINS_DIR, plugin_name)

        if os.path.isdir(install_path):
            try:
                for fname in os.listdir(install_path):
                    if fname.lower().endswith(('.png', '.ico', '.jpg', '.svg')):
                        icon_path = os.path.join(install_path, fname)
                        pix = load_crisp_pixmap(icon_path, 128)
                        if not pix.isNull():
                            self.icon_loaded.emit(plugin_name, pix)
                            return
            except Exception:
                pass

        # 2. Check ICONS_CACHE_DIR (case-insensitive) — but invalidate if icon_url changed
        icon_url = plugin.get('icon_url', '')
        cached_icon_path = os.path.join(ICONS_CACHE_DIR, f"{plugin_name}.png")
        icon_urls_file = os.path.join(ICONS_CACHE_DIR, '_icon_urls.json')
        cached_urls = {}
        if os.path.exists(icon_urls_file):
            try:
                cached_urls = json.loads(open(icon_urls_file, 'r', encoding='utf-8').read())
            except Exception:
                cached_urls = {}

        url_changed = bool(icon_url and cached_urls.get(plugin_name) != icon_url)
        if url_changed and os.path.exists(cached_icon_path):
            try:
                os.remove(cached_icon_path)
            except Exception:
                pass

        if not url_changed:
            cache_candidates = [
                cached_icon_path,
                os.path.join(ICONS_CACHE_DIR, f"{plugin_name.lower()}.png")
            ]
            if os.path.isdir(ICONS_CACHE_DIR):
                try:
                    for fname in os.listdir(ICONS_CACHE_DIR):
                        if fname.lower() == f"{plugin_name.lower()}.png":
                            cache_candidates.append(os.path.join(ICONS_CACHE_DIR, fname))
                except Exception:
                    pass

            for cpath in cache_candidates:
                if os.path.exists(cpath):
                    pix = load_crisp_pixmap(cpath, 128)
                    if not pix.isNull():
                        self.icon_loaded.emit(plugin_name, pix)
                        return

        def handle_icon_error(e):
            fallback_pix = self._extract_nss_fallback_icon(plugin_name, install_path)
            self.icon_loaded.emit(plugin_name, fallback_pix if fallback_pix else QPixmap(DEFAULT_ICON_PATH))

        def handle_icon_success(p_name, pix):
            if pix and not pix.isNull() and icon_url:
                try:
                    cached_urls[p_name] = icon_url
                    atomic_json_write(icon_urls_file, cached_urls)
                except Exception:
                    pass
            self.icon_loaded.emit(p_name, pix if (pix and not pix.isNull()) else (self._extract_nss_fallback_icon(p_name, install_path) or QPixmap(DEFAULT_ICON_PATH)))

        # 3. Download from icon_url if provided
        if plugin.get('icon_url'):
            local_icon_path = os.path.join(ICONS_CACHE_DIR, f"{plugin_name}.png")
            thread = QThread(self)
            worker = IconDownloadWorker(plugin_name, plugin['icon_url'], local_icon_path)
            worker.moveToThread(thread)

            worker.finished.connect(handle_icon_success)
            worker.error.connect(handle_icon_error)
            thread.started.connect(worker.run)
            worker.finished.connect(thread.quit)
            worker.error.connect(thread.quit)
            worker.finished.connect(worker.deleteLater)
            worker.error.connect(worker.deleteLater)
            plugin_key = f"icon_{plugin_name}"
            thread.finished.connect(lambda _k=plugin_key: self.cleanup_thread(_k))
            
            thread.start()
            self.active_threads[plugin_key] = (thread, worker)
        else:
            fallback_pix = self._extract_nss_fallback_icon(plugin_name, install_path)
            self.icon_loaded.emit(plugin_name, fallback_pix if fallback_pix else QPixmap(DEFAULT_ICON_PATH))

    def fetch_details(self, plugin_name):
        thread = QThread(self)
        worker = DetailsFetchWorker(plugin_name)
        worker.moveToThread(thread)

        worker.finished.connect(self.details_fetched.emit)
        worker.error.connect(self.details_fetch_error.emit)
        thread.started.connect(worker.run)
        worker.finished.connect(thread.quit)
        worker.error.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        worker.error.connect(worker.deleteLater)
        thread.finished.connect(lambda: self.cleanup_thread(f"details_{plugin_name}"))

        thread.start()
        self.active_threads[f"details_{plugin_name}"] = (thread, worker)

    def add_to_installation_queue(self, plugin_name):
        if plugin_name in [p['name'] for p in self.installation_queue] or self.current_installing_plugin == plugin_name:
            return
            
        plugin_data = self.all_plugins_data.get(plugin_name)
        if not plugin_data:
            # Fallback for delisted or registry-only plugins
            state = self.registry.get_plugin_state(plugin_name)
            plugin_data = {'name': plugin_name, 'version': state.get('remote_version') or '1.0.0'}

        self.installation_queue.append(plugin_data)
        
        if not self.current_installing_plugin:
            self.process_next_in_queue()

    def process_next_in_queue(self):
        if not self.installation_queue:
            self.current_installing_plugin = None
            return

        plugin_data = self.installation_queue.popleft()
        self.current_installing_plugin = plugin_data['name']
        self.install_started.emit(self.current_installing_plugin)
        
        thread = QThread(self)
        worker = InstallationWorker(plugin_data)
        worker.moveToThread(thread)

        self.active_threads[self.current_installing_plugin] = (thread, worker)

        thread.started.connect(worker.run)
        worker.progress.connect(self.install_progress.emit)
        worker.finished.connect(self._on_operation_finished)
        worker.error.connect(self._on_operation_error)
        worker.finished.connect(thread.quit)
        worker.error.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        worker.error.connect(worker.deleteLater)
        plugin_key = self.current_installing_plugin
        thread.finished.connect(lambda _key=plugin_key: self.cleanup_thread(_key))
        
        thread.start()

    def _on_operation_finished(self, plugin_name, status, file_hashes=None, file_count=0):
        if status == "installed":
            plugin_data = self.all_plugins_data.get(plugin_name, {})
            version = plugin_data.get('version', '1.0.0')
            install_path = get_plugin_install_path({'name': plugin_name, 'install_path': plugin_data.get('install_path')})
            self.registry.mark_installed(plugin_name, version, install_path, file_hashes or {}, file_count)
            sync_tools_menu(PROJECT_ROOT, self.registry)

        if plugin_name == self.current_installing_plugin:
            self.cleanup_thread(plugin_name)
            self.current_installing_plugin = None
            self.process_next_in_queue()
        self.operation_finished.emit(plugin_name, status)

    def _on_operation_error(self, plugin_name, status, error_message):
        if plugin_name == self.current_installing_plugin:
            self.cleanup_thread(plugin_name)
            self.current_installing_plugin = None
            self.process_next_in_queue()
        self.operation_error.emit(plugin_name, status, error_message)

    def cancel_operation(self, plugin_name):
        if self.current_installing_plugin == plugin_name and plugin_name in self.active_threads:
            thread, worker = self.active_threads[plugin_name]
            worker.cancel()
        else:
            self.installation_queue = deque([p for p in self.installation_queue if p['name'] != plugin_name])
            self.operation_finished.emit(plugin_name, "cancelled_from_queue")

    def uninstall_plugin(self, plugin_name):
        try:
            plugin_data = self.all_plugins_data.get(plugin_name, {'name': plugin_name})

            if plugin_name.lower() in ('ima switcher', 'ima-switcher', 'switcher', 'valo'):
                appdata_dir = os.path.join(os.getenv('LOCALAPPDATA', ''), 'iMA Switcher')
                for item in ('iMA Switcher.exe', 'iMA_Switcher_Update.exe', 'version.txt', 'version'):
                    target_file = os.path.join(appdata_dir, item)
                    if os.path.isfile(target_file):
                        try: os.remove(target_file)
                        except OSError: pass

                try:
                    remove_nss_import({'nss_path': appdata_dir, 'nss_file': 'valo.nss'}, os.path.join(PROJECT_ROOT, 'shell.nss'))
                    remove_nss_import({'nss_path': 'imports', 'nss_file': 'valo.nss'}, os.path.join(PROJECT_ROOT, 'shell.nss'))
                    remove_nss_import('valo', os.path.join(PROJECT_ROOT, 'shell.nss'))
                    trigger_shell_reload()
                except Exception:
                    pass

                self.registry.mark_uninstalled(plugin_name)
                sync_tools_menu(PROJECT_ROOT, self.registry)
                self.operation_finished.emit(plugin_name, "uninstalled")
                return

            target_plugin_dir = os.path.abspath(get_plugin_install_path(plugin_data))
            if os.path.exists(target_plugin_dir):
                terminate_plugin_processes(target_plugin_dir)
                import gc, time
                gc.collect()
                time.sleep(0.1)
                try:
                    shutil.rmtree(target_plugin_dir)
                except Exception:
                    time.sleep(0.3)
                    shutil.rmtree(target_plugin_dir, ignore_errors=True)
                if os.path.exists(target_plugin_dir):
                    try:
                        os.rmdir(target_plugin_dir)
                    except Exception:
                        pass

            try:
                remove_nss_import(plugin_data, os.path.join(PROJECT_ROOT, 'shell.nss'))
                remove_nss_import(plugin_name, os.path.join(PROJECT_ROOT, 'shell.nss'))
            except Exception:
                pass

            self.registry.mark_uninstalled(plugin_name)
            sync_tools_menu(PROJECT_ROOT, self.registry)
            trigger_shell_reload()
            self.operation_finished.emit(plugin_name, "uninstalled")
        except Exception as e:
            self.operation_error.emit(plugin_name, "failed", str(e))

    def delete_local_plugin(self, plugin_name):
        try:
            target_plugin_dir = os.path.abspath(os.path.join(PLUGINS_DIR, plugin_name))
            if os.path.exists(target_plugin_dir):
                terminate_plugin_processes(target_plugin_dir)
                delete_to_recycle_bin(target_plugin_dir)

            try:
                remove_nss_import({'name': plugin_name, 'nss_file': f"{plugin_name}.nss", 'nss_path': f"iMA Menu/plugins/{plugin_name}"}, os.path.join(PROJECT_ROOT, 'shell.nss'))
                remove_nss_import(plugin_name, os.path.join(PROJECT_ROOT, 'shell.nss'))
            except Exception:
                pass

            self.registry.mark_uninstalled(plugin_name)
            sync_tools_menu(PROJECT_ROOT, self.registry)
            trigger_shell_reload()
            self.operation_finished.emit(plugin_name, "uninstalled")
        except Exception as e:
            self.operation_error.emit(plugin_name, "failed", str(e))

    def get_local_plugin_version(self, plugin_name):
        return self.registry.get_installed_version(plugin_name)

    def cleanup_thread(self, key):
        if key in self.active_threads:
            thread, worker = self.active_threads.pop(key)
            thread.quit()

    def stop_all_threads(self):
        for key, (thread, worker) in list(self.active_threads.items()):
            if hasattr(worker, 'cancel'):
                worker.cancel()
            thread.quit()
            if not thread.wait(100):
                thread.terminate()

class PluginManager(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("iMA Menu")
        self.setMinimumSize(750, 500)
        self.resize(1002, 648)
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        self.setWindowIcon(QIcon(resource_path('icons/icon.ico')))
        self.setup_cache_dirs()
        
        self.settings_manager = SettingsManager()
        self.plugin_logic = PluginLogic()
        sync_tools_menu(PROJECT_ROOT, self.plugin_logic.registry)
        self.sync_manager = CloudSyncManager(PROJECT_ROOT)
        self.sync_manager.auth_finished.connect(self.on_sync_auth_finished)
        self.sync_manager.sync_progress.connect(self.on_sync_progress)
        self.sync_manager.sync_finished.connect(self.on_sync_finished)
        
        self.error_monitor = None
        
        # Debounced reload timer
        self.reload_timer = QTimer()
        self.reload_timer.setSingleShot(True)
        self.reload_timer.timeout.connect(self._do_reload_shell)
        
        self.uninstalled_plugins = set()

        self.all_plugins_data = {}
        self.plugin_cards = {}
        self.plugin_progress_bars = {}
        self.plugin_buttons = {}
        self.plugin_update_buttons = {}
        self.plugin_action_layouts = {}
        self.plugin_description_labels = {}
        self.plugin_icon_labels = {}
        self.icons_loaded = set()
        self.details_popup = None
        self.ignore_next_click = False
        self._active_tint_threads = []
        
        # Setup Undo/Redo Shortcuts
        self.undo_shortcut = QShortcut(QKeySequence("Ctrl+Z"), self)
        self.undo_shortcut.activated.connect(global_undo_stack.undo)
        
        self.redo_shortcut = QShortcut(QKeySequence("Ctrl+Y"), self)
        self.redo_shortcut.activated.connect(global_undo_stack.redo)

        self.installEventFilter(self)
        
        # Debounced file reload timer
        self.file_sync_timer = QTimer()
        self.file_sync_timer.setSingleShot(True)
        self.file_sync_timer.timeout.connect(self._handle_file_sync)
        self._pending_sync_paths = set()
        
        self._is_shutting_down = False
        
        # Resize debouncer to prevent flickering
        self.resize_timer = QTimer()
        self.resize_timer.setSingleShot(True)
        self.resize_timer.timeout.connect(self.recalculate_plugin_grid)

        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        self.side_panel = self.create_side_panel()
        self.side_panel.setMinimumWidth(80)
        self.side_panel.setMaximumWidth(80)
        self.main_layout.addWidget(self.side_panel)

        self.content_area = QWidget()
        self.content_area.setObjectName("contentArea")
        self.content_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.content_layout = QVBoxLayout(self.content_area)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.addWidget(self.content_area)

        self.title_bar = self.create_title_bar()
        self.content_layout.addWidget(self.title_bar)

        self.stacked_widget = QStackedWidget()
        self.stacked_widget.currentChanged.connect(self.update_refresh_btn_visibility)
        self.content_layout.addWidget(self.stacked_widget)

        self.plugins_page = QWidget()
        self.plugins_layout = QVBoxLayout(self.plugins_page)
        self.plugins_layout.setContentsMargins(10, 10, 10, 10)
        self.plugins_layout.setSpacing(10)

        # Dynamic Top Navigation Bar (Store / Local)
        self.current_plugins_tab = "store"
        self.plugins_tab_container = QWidget()
        self.plugins_tab_container.setObjectName("pluginsTabContainer")
        self.plugins_tab_container.setAttribute(Qt.WA_StyledBackground, True)
        self.plugins_tab_container.setStyleSheet("""
            QWidget#pluginsTabContainer {
                background-color: #121215;
                border-radius: 18px;
                padding: 4px;
            }
            QWidget#pluginsTabContainer QPushButton {
                background-color: transparent;
                color: #b0b0b0;
                border: none;
                border-radius: 14px;
                padding: 6px 20px;
                font-weight: bold;
                font-size: 13px;
            }
            QWidget#pluginsTabContainer QPushButton:hover {
                color: white;
                background-color: rgba(255, 255, 255, 0.05);
                border: none;
            }
            QWidget#pluginsTabContainer QPushButton:checked {
                background-color: #25252b;
                color: white;
                border: 1px solid rgba(255, 255, 255, 0.1);
            }
        """)
        pt_lay = QHBoxLayout(self.plugins_tab_container)
        pt_lay.setContentsMargins(0, 0, 0, 0); pt_lay.setSpacing(2)

        self.store_tab_btn = QPushButton("Store")
        self.store_tab_btn.setCheckable(True); self.store_tab_btn.setChecked(True)
        self.store_tab_btn.setCursor(Qt.PointingHandCursor)
        self.store_tab_btn.clicked.connect(lambda: self.switch_plugins_tab("store"))

        self.local_tab_btn = QPushButton("Local")
        self.local_tab_btn.setCheckable(True)
        self.local_tab_btn.setCursor(Qt.PointingHandCursor)
        self.local_tab_btn.clicked.connect(lambda: self.switch_plugins_tab("local"))

        from PyQt5.QtWidgets import QButtonGroup
        self.plugins_tab_group = QButtonGroup(self)
        self.plugins_tab_group.setExclusive(True)
        self.plugins_tab_group.addButton(self.store_tab_btn)
        self.plugins_tab_group.addButton(self.local_tab_btn)

        pt_lay.addWidget(self.store_tab_btn)
        pt_lay.addWidget(self.local_tab_btn)

        self.top_pt_widget = QWidget()
        top_pt_lay = QHBoxLayout(self.top_pt_widget)
        top_pt_lay.setContentsMargins(0, 0, 0, 5)
        top_pt_lay.addStretch()
        top_pt_lay.addWidget(self.plugins_tab_container)
        top_pt_lay.addStretch()

        self.plugins_layout.addWidget(self.top_pt_widget)
        self.plugins_tab_container.hide()

        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setObjectName("scrollArea")
        self.scroll_content = QWidget()
        self.grid_layout = QGridLayout(self.scroll_content)
        self.scroll_area.setWidget(self.scroll_content)
        self.scroll_area.setStyleSheet("border: 0px;")
        self.plugins_layout.addWidget(self.scroll_area)
        self.scroll_area.verticalScrollBar().valueChanged.connect(self.debounce_check_visible_cards)
        self.stacked_widget.addWidget(self.plugins_page)
        
        self.visible_check_timer = QTimer()
        self.visible_check_timer.setSingleShot(True)
        self.visible_check_timer.timeout.connect(self.check_visible_cards)

        self._modify_page_widget = None
        self._theme_page_widget = None
        self._settings_page_widget = None

        self.tint_backups = {}
        self._active_tint_threads = []


        self.loading_label = QLabel("Loading plugins...", self)
        self.loading_label.setAlignment(Qt.AlignCenter)
        self.loading_label.setFont(QFont('Segoe UI Variable Display', 16, QFont.Bold))
        self.loading_label.setObjectName("loadingLabel")
        self.loading_label.hide()
        self.content_layout.addWidget(self.loading_label)

        self.plugin_logic.plugins_fetched.connect(self.on_plugins_fetched)
        self.plugin_logic.fetch_error.connect(self.on_fetch_error)
        self.plugin_logic.icon_loaded.connect(self.on_icon_loaded)
        self.plugin_logic.install_progress.connect(self.on_install_progress)
        self.plugin_logic.install_started.connect(self.update_card_ui)
        self.plugin_logic.operation_finished.connect(self.on_operation_finished)
        self.plugin_logic.operation_error.connect(self.on_operation_error)
        self.plugin_logic.details_fetched.connect(self.on_details_fetched)
        self.plugin_logic.details_fetch_error.connect(self.on_details_fetch_error)
        
        self.nss_snapshot = {}

        # 1. Immediately render local cached plugins for instant UI display
        self.load_cached_plugins_immediately()

        # 2. Schedule background pre-warming of remaining tabs & network/watcher tasks
        QTimer.singleShot(50, self._start_error_monitor)
        QTimer.singleShot(100, self._prewarm_secondary_pages)
        QTimer.singleShot(200, self._setup_file_watcher)
        QTimer.singleShot(400, self.fetch_plugins_list)
        QTimer.singleShot(1000, self._take_global_nss_snapshot)

    def load_cached_plugins_immediately(self):
        local_plugins = self.plugin_logic.registry.get_local_plugins_for_ui()
        if len(local_plugins) > 0:
            self.plugins_tab_container.show()
        else:
            self.plugins_tab_container.hide()
            self.current_plugins_tab = "store"
            self.store_tab_btn.setChecked(True)

        self.render_current_plugins_tab()

    def _prewarm_secondary_pages(self):
        # Pre-instantiate remaining tabs in background idle slices so tab switches are 0ms instant
        def step1():
            if not self._is_shutting_down: self.get_modify_page()
        def step2():
            if not self._is_shutting_down: self.get_theme_page()
        def step3():
            if not self._is_shutting_down: self.get_settings_page()

        QTimer.singleShot(10, step1)
        QTimer.singleShot(150, step2)
        QTimer.singleShot(300, step3)

    def _start_error_monitor(self):
        try:
            self.error_monitor = ShellLogMonitor(PROJECT_ROOT, self)
            self.error_monitor.manual_fix_required.connect(self._on_manual_fix_required)
            self.error_monitor.start()
        except Exception as e:
            print(f"Error starting error monitor: {e}")

    def _setup_file_watcher(self):
        # File Watcher for external changes
        self._is_internal_change = False
        self.file_watcher = QFileSystemWatcher(self)
        
        # Files to watch specifically for content changes
        self.watch_files = [
            os.path.abspath(os.path.join(PROJECT_ROOT, 'shell.nss')),
            os.path.abspath(os.path.join(PROJECT_ROOT, 'imports', 'modify.nss')),
            os.path.abspath(os.path.join(PROJECT_ROOT, 'imports', 'theme.nss')),
            os.path.abspath(os.path.join(PROJECT_ROOT, 'shell.log'))
        ]
        # Directories to watch for additions/removals/plugin edits
        self.watch_dirs = [
            os.path.abspath(os.path.join(PROJECT_ROOT, 'imports')),
            os.path.abspath(os.path.join(PROJECT_ROOT, 'theme')),
            os.path.abspath(PLUGINS_DIR),
            os.path.abspath(ICONS_CACHE_DIR)
        ]
        # Also watch all installed plugin directories
        if os.path.exists(PLUGINS_DIR):
            for sub in os.listdir(PLUGINS_DIR):
                sub_p = os.path.join(PLUGINS_DIR, sub)
                if os.path.isdir(sub_p):
                    self.watch_dirs.append(os.path.abspath(sub_p))
        
        for f in self.watch_files:
            if os.path.exists(f): self.file_watcher.addPath(f)
        for d in self.watch_dirs:
            if os.path.exists(d): self.file_watcher.addPath(d)
            
        self.file_watcher.fileChanged.connect(self._on_external_file_changed)
        self.file_watcher.directoryChanged.connect(self._on_external_file_changed)

    def _take_global_nss_snapshot(self):
        def worker():
            snapshot = {}
            # Only scan top-level nss files and specific folders to avoid walking into deep plugin deps
            dirs_to_scan = [PROJECT_ROOT, os.path.join(PROJECT_ROOT, 'imports')]
            for d in dirs_to_scan:
                if not os.path.exists(d): continue
                for f in os.listdir(d):
                    if f.endswith('.nss'):
                        fp = os.path.abspath(os.path.join(d, f))
                        try:
                            with open(fp, 'r', encoding='utf-8') as file: snapshot[fp] = file.read()
                        except: pass
            
            # For plugins, only scan their root for .nss files, don't recurse deep
            plugins_dir = os.path.join(PROJECT_ROOT, 'plugins')
            if os.path.exists(plugins_dir):
                for plugin_name in os.listdir(plugins_dir):
                    p_path = os.path.join(plugins_dir, plugin_name)
                    if os.path.isdir(p_path):
                        for f in os.listdir(p_path):
                            if f.endswith('.nss'):
                                fp = os.path.abspath(os.path.join(p_path, f))
                                try:
                                    with open(fp, 'r', encoding='utf-8') as file: snapshot[fp] = file.read()
                                except: pass
            self.nss_snapshot = snapshot
        threading.Thread(target=worker, daemon=True).start()

    def update_snapshot(self, path=None):
        if path and os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as file:
                    self.nss_snapshot[os.path.abspath(path)] = file.read()
            except: pass

    def save_theme_and_update_status(self):
        self._is_internal_change = True
        try:
            editor_saved = self.theme_editor_page.save_theme()
            switcher_saved = self.theme_switcher_page.save_theme()
            
            if editor_saved or switcher_saved:
                self.commit_tinted_icons()
                self.update_snapshot(os.path.join(PROJECT_ROOT, 'imports', 'theme.nss'))
                self.reload_shell()
                self.theme_status_label.setText("Theme Saved")
                self.theme_status_label.setStyleSheet("color: #dc143c;")
                QTimer.singleShot(3000, self.theme_status_label.clear)
        finally:
            self._is_internal_change = False

    def reset_theme_and_update_status(self):
        if self.theme_editor_page.reset_theme():
            self.revert_tinted_icons()
            self.theme_status_label.setText("Reset to Default")
            self.theme_status_label.setStyleSheet("color: #ffffff;")
            QTimer.singleShot(3000, self.theme_status_label.clear)

    def commit_tinted_icons(self):
        prev_dir = os.path.join(PROJECT_ROOT, 'imports', 'icons', 'preview')
        main_dir = os.path.join(PROJECT_ROOT, 'imports', 'icons')
        if os.path.exists(prev_dir):
            for f in os.listdir(prev_dir):
                try:
                    src = os.path.join(prev_dir, f)
                    dst = os.path.join(main_dir, f)
                    if os.path.exists(dst): os.remove(dst)
                    shutil.move(src, dst)
                except Exception as e:
                    print(f"Error committing tinted icon {f}: {e}")
            try: shutil.rmtree(prev_dir)
            except: pass
        self._update_nss_icon_paths()
        self.tint_backups = {} # Clear backups after commit
        from modify_widget import cleanup_orphan_icons
        cleanup_orphan_icons(PROJECT_ROOT)
        self.reload_shell()

    def revert_tinted_icons(self):
        if self.tint_backups:
            for fp, content in self.tint_backups.items():
                if os.path.exists(fp):
                    try:
                        from utils import safe_file_write
                        safe_file_write(fp, content)
                    except: pass
            self.tint_backups = {}
            
        prev_dir = os.path.join(PROJECT_ROOT, 'imports', 'icons', 'preview')
        if os.path.exists(prev_dir):
            try: shutil.rmtree(prev_dir)
            except: pass
            
        from modify_widget import cleanup_orphan_icons
        cleanup_orphan_icons(PROJECT_ROOT)
        self.reload_shell()
        if hasattr(self, 'modify_page'): self.modify_page.refresh_ui()

    def reload_shell(self):
        # Debounce reloads to 50ms to prevent spamming
        self.reload_timer.start(50)

    def _do_reload_shell(self):
        # 0. Sync check - ensure no background writes are pending
        from utils import AsyncFileIo, trigger_shell_reload
        if AsyncFileIo.has_pending_writes():
            self.reload_timer.start(100) # Defer
            return

        # 1. Pre-validation: check if there's an existing error we should fix first
        if hasattr(self, 'error_monitor') and self.error_monitor._enabled:
             if not self.error_monitor.pre_reload_check():
                 # Monitor found errors and is likely fixing them. 
                 # Let the monitor trigger the reload when done.
                 return

        # 2. Trigger the actual reload (non-blocking)
        trigger_shell_reload(close_only=True)
        
        # 1000ms is the sweet spot for the CTRL+Click reload mechanism
        if self.settings_manager.get('auto_preview_context_menu'):
            QTimer.singleShot(1000, self._check_and_open_preview)

    def _check_and_open_preview(self):
        if hasattr(self, 'error_monitor'):
            if not self.error_monitor.check_log_clean_after_reload():
                return
        self._open_shell_preview()

    def _on_manual_fix_required(self, filename, line, message):
        # User requested no popup. Logging the error instead.
        print(f"ERROR: Syntax error in {filename}:{line} - {message}")

    def _open_shell_preview(self):
        # Calculate position to show menu next to the app
        geom = self.geometry()
        pos = (geom.right() + 10, geom.top())
        
        # Determine scenario based on current tab or active selection
        scenario = 'reload' # Default for theme changes
        if hasattr(self, 'theme_switcher_page'):
            scenario = self.theme_switcher_page.active_scenario
            
        from utils import trigger_shell_reload
        trigger_shell_reload(pos=pos, open_only=True, scenario=scenario)

    def _update_nss_icon_paths(self):
        # Match 'icons' followed by any number of slashes, then 'preview', then any number of slashes
        # This handles \, \\, and / consistently
        pat = r'(?i)(icons)([\\/]+)preview([\\/]+)'
        repl = r'\1\2'
        
        search_dirs = [
            os.path.join(PROJECT_ROOT, 'imports'), 
            os.path.join(PROJECT_ROOT, 'plugins'),
            os.path.join(PROJECT_ROOT, 'shell.nss')
        ]
        
        for p in search_dirs:
            if not os.path.exists(p): continue
            if os.path.isfile(p):
                self._apply_path_update(p, pat, repl)
            else:
                for root, _, files in os.walk(p):
                    for f in files:
                        if f.endswith('.nss'):
                            self._apply_path_update(os.path.join(root, f), pat, repl)

    def _apply_path_update(self, filepath, pattern, replacement):
        try:
            self._is_internal_change = True
            from utils import safe_file_write
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            new_content = re.sub(pattern, replacement, content)
            if new_content != content:
                safe_file_write(filepath, new_content)
        except Exception:
            pass
        finally:
            self._is_internal_change = False

    def eventFilter(self, obj, event):
        if event.type() == QEvent.MouseButtonPress:
            if self.details_popup and not self.details_popup.geometry().contains(event.globalPos()):
                if self.ignore_next_click:
                    self.ignore_next_click = False
                else:
                    self.details_popup.close()
        return super().eventFilter(obj, event)

    def _on_external_file_changed(self, path):
        if self._is_internal_change or self._is_shutting_down: return
        # Ignore temporary and staging directories
        norm = path.replace('\\', '/').lower()
        if '/.staging_' in norm or '/.backup_' in norm or norm.endswith('.tmp'):
            return
        self._pending_sync_paths.add(path)
        self.file_sync_timer.start(500) # 500ms debounce to prevent lag

    def _handle_file_sync(self):
        if not self._pending_sync_paths or self._is_internal_change or self._is_shutting_down: 
            self._pending_sync_paths.clear()
            return
            
        paths = list(self._pending_sync_paths)
        self._pending_sync_paths.clear()
        
        for path in paths:
            clean_path = os.path.normpath(path).lower().replace('\\', '/')
            
            # Re-add path to watcher if it was deleted/recreated (atomic save)
            if os.path.exists(path) and path not in self.file_watcher.files() and path not in self.file_watcher.directories():
                self.file_watcher.addPath(path)

            # Core Modify Rules
            if clean_path.endswith('/modify.nss'):
                if hasattr(self, 'modify_page'):
                    self.modify_page.refresh_rules_model()
                    self.show_sync_status("Synced Rules")
            
            # Core Theme
            elif clean_path.endswith('/theme.nss'):
                if hasattr(self, 'theme_editor_page'):
                    self.theme_editor_page.reload_theme()
                if hasattr(self, 'theme_switcher_page'):
                    self.theme_switcher_page.selected_theme = self.theme_switcher_page._get_current_theme_from_file()
                    self.theme_switcher_page._highlight_current_theme()
                self.show_sync_status("Synced Theme")
            
            # Shell or Imports directory (Plugin changes)
            elif clean_path.endswith('/shell.nss') or '/imports/' in clean_path or clean_path.endswith('/imports'):
                if hasattr(self, 'modify_page') and hasattr(self.modify_page, 'imports_pg'):
                    self.modify_page.imports_pg.refresh()
                self.show_sync_status("Synced Imports")
            
            # Theme directory (New/Removed theme files)
            elif '/theme/' in clean_path or clean_path.endswith('/theme'):
                if hasattr(self, 'theme_switcher_page'):
                    self.theme_switcher_page.refresh_list()
                self.show_sync_status("Synced Themes")

            # Plugin directory or icons cache (Plugin files, icons, PNG edits, name changes)
            elif '/plugins/' in clean_path or clean_path.endswith('/plugins') or '/cache/icons' in clean_path or clean_path.endswith('/icons'):
                self.plugin_logic.registry.reconcile_with_disk()
                # Re-add any newly created subdirectories in PLUGINS_DIR to file watcher
                if os.path.exists(PLUGINS_DIR):
                    for sub in os.listdir(PLUGINS_DIR):
                        sub_p = os.path.abspath(os.path.join(PLUGINS_DIR, sub))
                        if os.path.isdir(sub_p) and not sub.startswith('.') and sub_p not in self.file_watcher.directories():
                            self.file_watcher.addPath(sub_p)

                # Debounce card UI updates for only visible cards
                self.icons_loaded.clear()
                QTimer.singleShot(100, self.check_visible_cards)
                self.show_sync_status("Synced Plugins & Icons")

    def full_ui_refresh(self):
        """ Force a complete reload of all UI components from disk files. """
        self._is_internal_change = True
        try:
            # 1. Reload Rules & Imports
            if hasattr(self, 'modify_page'):
                self.modify_page.load_and_init_ui()
                if hasattr(self.modify_page, 'imports_pg'):
                    self.modify_page.imports_pg.refresh()
                
            # 2. Reload Themes
            if hasattr(self, 'theme_editor_page'):
                self.theme_editor_page.reload_theme()
            if hasattr(self, 'theme_switcher_page'):
                self.theme_switcher_page.refresh_list()
                self.theme_switcher_page.selected_theme = self.theme_switcher_page._get_current_theme_from_file()
                self.theme_switcher_page._highlight_current_theme()
                
            # 3. Reload Shell
            self.reload_shell()
            self.show_sync_status("UI Refreshed")
        finally:
            self._is_internal_change = False

    def show_sync_status(self, text):
        if hasattr(self, 'theme_status_label'):
            self.theme_status_label.setText(text)
            self.theme_status_label.setStyleSheet("color: #dc143c;")
            QTimer.singleShot(2000, self.theme_status_label.clear)

    def setup_cache_dirs(self):
        # Folders are now initialized at startup globally
        pass

    def _apply_shadow_effect(self, widget):
        # No-op on micro UI elements to prevent GPU/CPU rasterization bottlenecks during scrolling/resizing
        pass

    def create_title_bar(self):
        title_bar = QWidget()
        title_bar.setFixedHeight(42)
        title_layout = QHBoxLayout(title_bar)

        app_icon_label = QLabel()
        app_icon_pixmap = QPixmap(resource_path('icons/icon.ico'))
        app_icon_label.setPixmap(app_icon_pixmap.scaled(24, 24, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        title_layout.addWidget(app_icon_label)

        title_label = QLabel("iMA Menu")
        title_label.setFont(QFont('Segoe UI Variable Display', 16, QFont.Bold))
        title_label.setObjectName("titleLabel")

        open_folder_button = QPushButton()
        open_folder_button.setIcon(QIcon(resource_path('icons/open.png')))
        open_folder_button.setIconSize(QSize(24, 24))
        open_folder_button.setFixedSize(30, 30)
        open_folder_button.setObjectName("iconButton")
        open_folder_button.clicked.connect(self.open_root_folder)

        self.refresh_button = QPushButton()
        self.refresh_button.setIcon(QIcon(resource_path('icons/refresh.png')))
        self.refresh_button.setIconSize(QSize(24, 24))
        self.refresh_button.setFixedSize(30, 30)
        self.refresh_button.setCursor(Qt.PointingHandCursor)
        self.refresh_button.setObjectName("iconButton")
        self.refresh_button.clicked.connect(self.refresh_plugins)

        chrome_btn_style = """
            QPushButton { background: rgba(255,255,255,0.05); border: none; border-radius: 8px; color: #b0b0b0; font-family: 'Segoe MDL2 Assets'; font-size: 10px; }
            QPushButton:hover { background: rgba(255,255,255,0.12); color: #ffffff; }
        """
        minimize_button = QPushButton("\uE921")
        minimize_button.setFixedSize(32, 32)
        minimize_button.setCursor(Qt.PointingHandCursor)
        minimize_button.setStyleSheet(chrome_btn_style)
        minimize_button.clicked.connect(self.showMinimized)

        self.maximize_button = QPushButton("\uE922")
        self.maximize_button.setFixedSize(32, 32)
        self.maximize_button.setCursor(Qt.PointingHandCursor)
        self.maximize_button.setStyleSheet(chrome_btn_style)
        self.maximize_button.clicked.connect(self.toggle_maximize)

        close_button = QPushButton("\uE8BB")
        close_button.setFixedSize(32, 32)
        close_button.setCursor(Qt.PointingHandCursor)
        close_button.setStyleSheet("""
            QPushButton { background: rgba(255,42,85,0.1); border: none; border-radius: 8px; color: #dc143c; font-family: 'Segoe MDL2 Assets'; font-size: 10px; }
            QPushButton:hover { background: #dc143c; color: #ffffff; }
        """)
        close_button.clicked.connect(self.close)
        
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        title_layout.addWidget(open_folder_button)
        title_layout.addWidget(self.refresh_button)
        title_layout.addWidget(minimize_button)
        title_layout.addWidget(self.maximize_button)
        title_layout.addWidget(close_button)
        return title_bar

    def toggle_maximize(self):
        if self.isMaximized():
            self.showNormal()
            self.maximize_button.setText("\uE922")
        else:
            self.showMaximized()
            self.maximize_button.setText("\uE923")

    def update_refresh_btn_visibility(self, index):
        # Index 0 is plugins_page
        self.refresh_button.setVisible(index == 0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.resize_timer.start(50)
        if hasattr(self, 'details_popup') and self.details_popup and self.details_popup.isVisible():
            self.details_popup.setGeometry(self.rect().adjusted(40, 50, -40, -30))

    def recalculate_plugin_grid(self):
        if not hasattr(self, 'grid_layout') or not self.plugin_cards:
            return
            
        available_width = self.scroll_area.viewport().width() - 20
        if available_width <= 0:
            available_width = self.scroll_area.width() - 20
            
        card_width = 180 + 15
        max_cols = 5
        cols = max(1, min(max_cols, available_width // card_width))
        
        total_grid_width = cols * card_width
        left_margin = max(15, (available_width - total_grid_width) // 2)
        
        self.grid_layout.setContentsMargins(left_margin, 10, left_margin, 20)
        self.grid_layout.setHorizontalSpacing(15)
        self.grid_layout.setVerticalSpacing(15)
        
        for i, (plugin_name, card) in enumerate(self.plugin_cards.items()):
            row, col = i // cols, i % cols
            if self.grid_layout.indexOf(card) != -1:
                self.grid_layout.removeWidget(card)
            self.grid_layout.addWidget(card, row, col)
            card.show()
        
        QTimer.singleShot(50, self.check_visible_cards)

    def get_modify_page(self):
        if self._modify_page_widget is None:
            self.modify_page = ModifyWidget(os.path.join(PROJECT_ROOT, 'imports', 'modify.nss'), os.path.join(PROJECT_ROOT, 'shell.nss'), PROJECT_ROOT)
            self._modify_page_widget = self.modify_page
            self.modify_page.reload_requested.connect(self.reload_shell)
            if hasattr(self.modify_page, 'rules_saved'):
                self.modify_page.rules_saved.connect(lambda: self.update_snapshot(os.path.join(PROJECT_ROOT, 'imports', 'modify.nss')))
            self.stacked_widget.addWidget(self._modify_page_widget)
            self._update_widgets_autosave()
        return self._modify_page_widget

    def get_theme_page(self):
        if self._theme_page_widget is None:
            self.theme_page = QWidget()
            self._theme_page_widget = self.theme_page
            self.theme_layout = QVBoxLayout(self.theme_page)
            self.theme_tab_widget = ModernTabWidget()
            self.theme_layout.addWidget(self.theme_tab_widget)

            corner_widget = QWidget()
            corner_layout = QHBoxLayout(corner_widget)
            corner_layout.setContentsMargins(0, 0, 10, 0)
            corner_layout.setSpacing(10)
            corner_layout.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

            self.theme_status_label = QLabel("")
            self.theme_status_label.setObjectName("themeStatusLabel")
            self.theme_status_label.setMinimumWidth(120)
            self.theme_status_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            corner_layout.addWidget(self.theme_status_label)

            self.theme_save_button = QPushButton("Save")
            self.theme_save_button.setObjectName("themeSaveButton")
            self.theme_reset_button = QPushButton("Reset")
            self.theme_reset_button.setObjectName("themeResetButton")
            self.sync_container = QFrame(); self.sync_container.setObjectName("syncContainer")
            self.sync_container.setStyleSheet("QFrame#syncContainer { background: rgba(255, 255, 255, 0.05); border-radius: 16px; border: 1px solid rgba(255, 255, 255, 0.1); }")
            sync_cl = QHBoxLayout(self.sync_container); sync_cl.setContentsMargins(15, 0, 8, 0); sync_cl.setSpacing(10)

            sync_label = QLabel("Sync colors now"); sync_label.setStyleSheet("color: white; font-weight: 500; font-size: 11px; background: transparent; border: none;")
            self.theme_sync_button = QPushButton("\uE117"); self.theme_sync_button.setFont(QFont('Segoe MDL2 Assets', 12))
            self.theme_sync_button.setFixedSize(30, 30); self.theme_sync_button.setCursor(QCursor(Qt.PointingHandCursor))
            self.theme_sync_button.setStyleSheet("QPushButton { color: white; background: rgba(255,255,255,0.1); border: none; border-radius: 15px; } QPushButton:hover { background: rgba(255,255,255,0.2); }")
            self.theme_sync_button.clicked.connect(lambda: self.trigger_global_tint(force=True))

            sync_cl.addWidget(sync_label); sync_cl.addWidget(self.theme_sync_button)

            self.add_theme_btn = QPushButton("Add Theme")
            self.add_theme_btn.setObjectName("addThemeBtn")
            self.add_theme_btn.setStyleSheet("QPushButton#addThemeBtn { background: rgba(255,255,255,0.05); color: white; border-radius: 15px; border: 1px solid rgba(255,255,255,0.1); padding: 6px 20px; font-weight: bold; } QPushButton#addThemeBtn:hover { background: rgba(255,255,255,0.1); }")
            self.add_theme_btn.setCursor(QCursor(Qt.PointingHandCursor))

            corner_layout.addWidget(self.add_theme_btn)
            corner_layout.addWidget(self.sync_container)
            corner_layout.addWidget(self.theme_save_button)
            corner_layout.addWidget(self.theme_reset_button)

            self.theme_tab_widget.setCornerWidget(corner_widget, Qt.TopRightCorner)

            self.theme_switcher_page = ThemeSwitcherWidget(
                theme_dir=os.path.join(PROJECT_ROOT, 'theme'),
                theme_nss_path=os.path.join(PROJECT_ROOT, 'imports', 'theme.nss')
            )
            self.theme_editor_page = ThemeEditorWidget(
                theme_path=os.path.join(PROJECT_ROOT, 'imports', 'theme.nss'),
                theme_dir=os.path.join(PROJECT_ROOT, 'theme')
            )

            self.add_theme_btn.clicked.connect(self.theme_switcher_page._add_current_theme)
            self.theme_switcher_page.status_message_requested.connect(self.theme_status_label.setText)

            self.theme_save_button.clicked.connect(self.save_theme_and_update_status)
            self.theme_reset_button.clicked.connect(self.reset_theme_and_update_status)
            self.theme_switcher_page.theme_selected.connect(self.theme_editor_page.reload_theme)
            self.theme_switcher_page.theme_applied.connect(self.trigger_global_tint)
            self.theme_switcher_page.reload_requested.connect(self.reload_shell)
            self.theme_editor_page.reload_requested.connect(self.reload_shell)

            self.theme_tab_widget.addTab(self.theme_switcher_page, get_mdl2_icon(0xE790, 36), "Themes")
            self.theme_tab_widget.addTab(self.theme_editor_page, get_mdl2_icon(0xE104, 36), "Editor")

            self.stacked_widget.addWidget(self._theme_page_widget)
            self._update_widgets_autosave()
        return self._theme_page_widget

    def get_settings_page(self):
        if self._settings_page_widget is None:
            self.settings_scroll = QScrollArea()
            self._settings_page_widget = self.settings_scroll
            self.settings_scroll.setWidgetResizable(True)
            self.settings_scroll.setStyleSheet("background: transparent; border: none;")
            self.settings_page = QWidget()
            self.settings_scroll.setWidget(self.settings_page)
            self.setup_settings_page()
            self._update_widgets_autosave()
            self.stacked_widget.addWidget(self._settings_page_widget)
        return self._settings_page_widget

    def create_side_panel(self):
        side_panel = QFrame()
        side_panel.setObjectName("sidePanel")
        side_panel.setStyleSheet("#sidePanel { background-color: #121212; border-right: 1px solid #2a2a30; border-top-left-radius: 15px; border-bottom-left-radius: 15px; }")
        side_panel.setFixedWidth(84)
        side_panel_layout = QVBoxLayout(side_panel)
        side_panel_layout.setContentsMargins(6, 12, 6, 12)
        side_panel_layout.setSpacing(16)
        side_panel_layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)

        def create_nav_item(icon_name, label_text, page_getter):
            w = QWidget()
            w_layout = QVBoxLayout(w)
            w_layout.setContentsMargins(0, 0, 0, 0)
            w_layout.setSpacing(4)
            w_layout.setAlignment(Qt.AlignCenter)

            btn = QPushButton()
            btn.setObjectName("sideButton")
            btn.setIcon(QIcon(resource_path(f'icons/{icon_name}')))
            btn.setIconSize(QSize(36, 36))
            btn.setFixedSize(54, 54)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda: self.stacked_widget.setCurrentWidget(page_getter()))
            self._apply_shadow_effect(btn)

            lbl = QLabel(label_text)
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet("color: #b0b0b0; font-size: 11px; font-weight: 600; background: transparent;")

            w_layout.addWidget(btn, 0, Qt.AlignCenter)
            w_layout.addWidget(lbl, 0, Qt.AlignCenter)
            return w

        side_panel_layout.addWidget(create_nav_item('plugins.png', 'Plugins', lambda: self.plugins_page))
        side_panel_layout.addWidget(create_nav_item('modify.png', 'Modify', lambda: self.get_modify_page()))
        side_panel_layout.addWidget(create_nav_item('theme.png', 'Theme', lambda: self.get_theme_page()))

        side_panel_layout.addStretch()

        side_panel_layout.addWidget(create_nav_item('settings.png', 'Settings', lambda: self.get_settings_page()))

        return side_panel

    def open_root_folder(self):
        try:
            os.startfile(PROJECT_ROOT)
        except Exception as e:
            print(f"Error opening root folder: {e}")

    def switch_plugins_tab(self, tab_name):
        self.current_plugins_tab = tab_name
        if tab_name == "store":
            self.store_tab_btn.setChecked(True)
        else:
            self.local_tab_btn.setChecked(True)
        self.render_current_plugins_tab()

    def render_current_plugins_tab(self):
        if self.current_plugins_tab == "local":
            plugins = self.plugin_logic.registry.get_local_plugins_for_ui()
        else:
            plugins = self.plugin_logic.registry.get_store_plugins_for_ui()

        self.on_plugins_fetched(plugins)

    def load_plugins(self):
        local_plugins = self.plugin_logic.registry.get_local_plugins_for_ui()
        if len(local_plugins) > 0:
            self.plugins_tab_container.show()
        else:
            self.plugins_tab_container.hide()
            self.current_plugins_tab = "store"
            self.store_tab_btn.setChecked(True)

        self.render_current_plugins_tab()
        self.fetch_plugins_list()

    def fetch_plugins_list(self):
        self.plugin_logic.fetch_plugins_list()

    def on_plugins_fetched(self, plugins):
        local_plugins = self.plugin_logic.registry.get_local_plugins_for_ui()
        if len(local_plugins) > 0:
            self.plugins_tab_container.show()
        else:
            self.plugins_tab_container.hide()
            if self.current_plugins_tab == "local":
                self.current_plugins_tab = "store"
                self.store_tab_btn.setChecked(True)

        if self.current_plugins_tab == "local":
            active_plugins = local_plugins
        else:
            active_plugins = self.plugin_logic.registry.get_store_plugins_for_ui()

        self.all_plugins_data = {p['name']: p for p in active_plugins}

        # Smart diff: check if the card layout set actually changed
        current_names = set(self.plugin_cards.keys())
        valid_names = {p['name'] for p in active_plugins}
        cards_changed = (current_names != valid_names)

        # Create cards for new active plugins and update existing ones in-place
        for plugin in active_plugins:
            p_name = plugin['name']
            if p_name not in self.plugin_cards:
                self.create_plugin_card(plugin)
            else:
                # Update description label if changed remotely
                if p_name in self.plugin_description_labels:
                    desc_lbl = self.plugin_description_labels[p_name]
                    new_desc = plugin.get('description', 'No description available.')
                    if desc_lbl.text() != new_desc:
                        desc_lbl.setText(new_desc)
                self.update_card_ui(p_name)

        # Remove cards for plugins that are no longer in active UI list
        if cards_changed:
            for p_name in list(self.plugin_cards.keys()):
                if p_name not in valid_names:
                    card = self.plugin_cards.pop(p_name)
                    card.deleteLater()
                    self.plugin_progress_bars.pop(p_name, None)
                    self.plugin_buttons.pop(p_name, None)
                    self.plugin_update_buttons.pop(p_name, None)
                    self.plugin_action_layouts.pop(p_name, None)
                    self.plugin_description_labels.pop(p_name, None)
                    self.plugin_icon_labels.pop(p_name, None)

        # Arrange grid only if card membership changed to preserve scroll & avoid layout flicker
        self.loading_label.hide()
        self.scroll_area.show()
        if cards_changed or not self.grid_layout.count():
            self.recalculate_plugin_grid()
        
        # Trigger icon loading for the visible cards
        QTimer.singleShot(100, self.check_visible_cards)

    def on_fetch_error(self, error_message):
        self.loading_label.setText(f"Error: {error_message}")

    def refresh_plugins(self):
        if self.plugin_logic.current_installing_plugin: return
        self.fetch_plugins_list()

    def display_plugins(self, plugins):
        for i in reversed(range(self.grid_layout.count())):
            widget = self.grid_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()

        self.plugin_cards.clear()
        self.plugin_progress_bars.clear()
        self.plugin_buttons.clear()
        self.plugin_update_buttons.clear()
        self.plugin_action_layouts.clear()
        self.plugin_description_labels.clear()
        self.plugin_icon_labels.clear()
        self.icons_loaded.clear()

        self.all_plugins_data = {p['name']: p for p in plugins}

        self.recalculate_plugin_grid()

        QTimer.singleShot(100, self.check_visible_cards)

    def create_plugin_card(self, plugin):
        plugin_name = plugin['name']
        card = ClickableWidget(plugin_name)
        card.setObjectName("plugin_card")
        card.setFixedSize(180, 250)
        layout = QVBoxLayout(card)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(10)

        card.plugin_card_clicked.connect(self.show_details_popup)

        title = QLabel(plugin_name)
        title.setFont(QFont('Segoe UI Variable Display', 14, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        layout.addWidget(title)

        icon_container = QWidget()
        icon_container.setObjectName("iconContainer")
        icon_container.setFixedSize(80, 80)
        icon_layout = QVBoxLayout(icon_container)
        icon_layout.setContentsMargins(0,0,0,0)
        icon_layout.setAlignment(Qt.AlignCenter)
        icon = QLabel()
        icon.setFixedSize(70, 70)
        icon.setScaledContents(True)
        icon.setObjectName("iconLabel")
        icon.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.plugin_icon_labels[plugin_name] = icon
        icon.setPixmap(QPixmap(DEFAULT_ICON_PATH))
        self.load_icon(plugin)
        self.icons_loaded.add(plugin_name)
        icon_layout.addWidget(icon)
        layout.addWidget(icon_container, alignment=Qt.AlignCenter)

        description = QLabel(plugin.get('description', 'No description available.'))
        description.setWordWrap(True)
        description.setAlignment(Qt.AlignCenter)
        description.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        layout.addWidget(description)

        layout.addStretch()

        progress_bar = PillProgressBar(height=16)
        progress_bar.setFixedWidth(140)
        progress_bar.setVisible(False)
        self.plugin_progress_bars[plugin_name] = progress_bar
        layout.addWidget(progress_bar, alignment=Qt.AlignCenter)

        action_layout = QHBoxLayout()
        action_layout.setContentsMargins(0, 10, 0, 0)
        action_layout.setSpacing(10)
        action_layout.setAlignment(Qt.AlignCenter)
        layout.addLayout(action_layout)

        action_button = QPushButton()
        action_button.setObjectName("installButton")
        action_button.setCursor(Qt.PointingHandCursor)
        action_layout.addWidget(action_button)

        self.plugin_cards[plugin_name] = card
        self.plugin_progress_bars[plugin_name] = progress_bar
        self.plugin_buttons[plugin_name] = action_button
        self.plugin_action_layouts[plugin_name] = action_layout
        self.plugin_description_labels[plugin_name] = description

        self.update_card_ui(plugin_name)
        self.apply_card_style(card)
        return card

    def show_details_popup(self, plugin_name, card):
        if self.details_popup:
            self.details_popup.close()

        plugin_data = self.all_plugins_data.get(plugin_name)
        if not plugin_data:
            state = self.plugin_logic.registry.get_plugin_state(plugin_name)
            plugin_data = {
                'name': plugin_name,
                'description': 'Custom local plugin',
                'version': state.get('installed_version', '1.0.0')
            }

        start_pos = card.mapTo(self, QPoint(0, 0))
        start_geom = QRect(start_pos, card.size())

        self.details_popup = DetailsPopup(plugin_data, self, start_geom=start_geom)
        self.details_popup.raise_()
        self.details_popup.show()

        end_geom = self.rect().adjusted(40, 50, -40, -30)

        self.details_popup.setGeometry(start_geom)
        self.details_popup.setWindowOpacity(0.0)

        self.open_anim_group = QParallelAnimationGroup(self)

        geo_anim = QPropertyAnimation(self.details_popup, b"geometry")
        geo_anim.setDuration(200)
        geo_anim.setStartValue(start_geom)
        geo_anim.setEndValue(end_geom)
        geo_anim.setEasingCurve(QEasingCurve.OutQuint)
        self.open_anim_group.addAnimation(geo_anim)

        opac_anim = QPropertyAnimation(self.details_popup, b"windowOpacity")
        opac_anim.setDuration(180)
        opac_anim.setStartValue(0.0)
        opac_anim.setEndValue(1.0)
        opac_anim.setEasingCurve(QEasingCurve.OutQuad)
        self.open_anim_group.addAnimation(opac_anim)

        self.open_anim_group.start(QPropertyAnimation.DeleteWhenStopped)

        self.plugin_logic.fetch_details(plugin_name)

        self.details_popup.action_button.clicked.connect(lambda: self.handle_popup_action(plugin_name))
        self.update_popup_button(plugin_name)
        self.ignore_next_click = True

    def on_details_fetched(self, content):
        if self.details_popup:
            self.details_popup.set_details_content(content)

    def on_details_fetch_error(self, error):
        if self.details_popup:
            self.details_popup.set_details_content(f"Error: {error}")

    def handle_popup_action(self, plugin_name):
        plugin_info = self.all_plugins_data.get(plugin_name, {})
        state = self.plugin_logic.registry.get_plugin_state(plugin_name)
        is_local = plugin_info.get('_is_local') or state.get('status') == 'local'
        if is_local:
            self.confirm_delete_local_plugin(plugin_name)
            return

        if state.get('status') in ('installed', 'update_available', 'delisted'):
            self.uninstall_plugin(plugin_name)
        else:
            self.add_to_installation_queue(plugin_name)
        self.update_popup_button(plugin_name)

    def confirm_delete_local_plugin(self, plugin_name):
        dlg = ModernDialog(self, title="Delete Local Plugin", text=f"Are you sure you want to delete local plugin '{plugin_name}'?\n\nThis will move the plugin files to the Recycle Bin and remove it from your shell menu.")
        dlg.add_button("Cancel", "secondaryButton", dlg.reject)
        dlg.add_button("Delete to Recycle Bin", "uninstallButton", dlg.accept)
        if dlg.exec_() == QDialog.Accepted:
            self._is_internal_change = True
            try:
                target_plugin_dir = os.path.abspath(os.path.join(PLUGINS_DIR, plugin_name))
                if hasattr(self, 'file_watcher') and self.file_watcher:
                    for d in list(self.file_watcher.directories()):
                        if d == target_plugin_dir or d.lower().startswith(target_plugin_dir.lower() + os.sep):
                            try:
                                self.file_watcher.removePath(d)
                            except Exception:
                                pass
            except Exception:
                pass
            finally:
                self._is_internal_change = False
            self.plugin_logic.delete_local_plugin(plugin_name)
            self.load_plugins()

    def update_popup_button(self, plugin_name):
        if not self.details_popup: return
        plugin_info = self.all_plugins_data.get(plugin_name, {})
        state = self.plugin_logic.registry.get_plugin_state(plugin_name)
        status = state.get('status', 'not_installed')
        is_local = plugin_info.get('_is_local') or status == 'local'

        if is_local:
            self.details_popup.action_button.setText("Delete")
            self.details_popup.action_button.setObjectName("uninstallButton")
        elif status == 'update_available':
            self.details_popup.action_button.setText("Update")
            self.details_popup.action_button.setObjectName("updateButton")
        elif status in ('installed', 'delisted'):
            self.details_popup.action_button.setText("Uninstall")
            self.details_popup.action_button.setObjectName("uninstallButton")
        else:
            self.details_popup.action_button.setText("Install")
            self.details_popup.action_button.setObjectName("installButton")
        
        self.details_popup.action_button.style().unpolish(self.details_popup.action_button)
        self.details_popup.action_button.style().polish(self.details_popup.action_button)

    def debounce_check_visible_cards(self):
        self.visible_check_timer.start(100)

    def check_visible_cards(self):
        if self.stacked_widget.currentWidget() != self.plugins_page:
            return

        scroll_bar = self.scroll_area.verticalScrollBar()
        viewport_top = scroll_bar.value()
        viewport_bottom = viewport_top + self.scroll_area.viewport().height()

        for plugin_name, card in self.plugin_cards.items():
            if plugin_name not in self.icons_loaded:
                card_top = card.y()
                card_bottom = card_top + card.height()
                # Buffer of 100px for smoother loading
                if card_top < viewport_bottom + 100 and card_bottom > viewport_top - 100:
                    plugin_data = self.all_plugins_data.get(plugin_name, {'name': plugin_name})
                    self.load_icon(plugin_data)
                    self.icons_loaded.add(plugin_name)

    def get_local_plugin_version(self, plugin_name):
        return self.plugin_logic.get_local_plugin_version(plugin_name)

    def disable_local_plugin(self, plugin_name):
        plugin_dir = os.path.join(PLUGINS_DIR, plugin_name)
        if not os.path.isdir(plugin_dir) and os.path.exists(PLUGINS_DIR):
            for d in os.listdir(PLUGINS_DIR):
                if d.lower() == plugin_name.lower():
                    plugin_dir = os.path.join(PLUGINS_DIR, d)
                    break
        nss_dir, nss_file = find_plugin_nss_info(plugin_name, plugin_dir)
        if nss_dir and nss_file:
            remove_nss_import({'nss_path': nss_dir, 'nss_file': nss_file}, os.path.join(PROJECT_ROOT, 'shell.nss'))
            sync_tools_menu(PROJECT_ROOT, self.plugin_logic.registry)
            trigger_shell_reload()
        self.update_card_ui(plugin_name)

    def enable_local_plugin(self, plugin_name):
        plugin_dir = os.path.join(PLUGINS_DIR, plugin_name)
        if not os.path.isdir(plugin_dir) and os.path.exists(PLUGINS_DIR):
            for d in os.listdir(PLUGINS_DIR):
                if d.lower() == plugin_name.lower():
                    plugin_dir = os.path.join(PLUGINS_DIR, d)
                    break
        nss_dir, nss_file = find_plugin_nss_info(plugin_name, plugin_dir)
        if nss_dir and nss_file:
            add_nss_import({'nss_path': nss_dir, 'nss_file': nss_file}, os.path.join(PROJECT_ROOT, 'shell.nss'))
            sync_tools_menu(PROJECT_ROOT, self.plugin_logic.registry)
            trigger_shell_reload()
        self.update_card_ui(plugin_name)

    def update_card_ui(self, plugin_name):
        action_button = self.plugin_buttons.get(plugin_name)
        if not action_button: return

        action_layout = self.plugin_action_layouts.get(plugin_name)
        if not action_layout: return

        font = action_button.font()
        font.setBold(True)
        action_button.setFont(font)

        if self.plugin_update_buttons.get(plugin_name):
            button_to_remove = self.plugin_update_buttons.pop(plugin_name)
            button_to_remove.deleteLater()

        try: action_button.clicked.disconnect()
        except TypeError: pass

        is_queued = plugin_name in [p['name'] for p in self.plugin_logic.installation_queue]
        is_installing = self.plugin_logic.current_installing_plugin == plugin_name

        plugin_info = self.all_plugins_data.get(plugin_name, {})
        state = self.plugin_logic.registry.get_plugin_state(plugin_name)
        status = state.get('status', 'not_installed')
        is_local = plugin_info.get('_is_local') or status == 'local'
        has_update = status == 'update_available'
        is_delisted = status == 'delisted'
        is_installed = status in ('installed', 'update_available', 'delisted', 'local')
        
        # Auto Update Logic
        if has_update and self.settings_manager.get('auto_update') and not is_queued and not is_installing:
             self.add_to_installation_queue(plugin_name)
             return
        
        if plugin_name in self.plugin_progress_bars:
            self.plugin_progress_bars[plugin_name].setVisible(is_installing)

        if is_installing:
            action_button.setText(" Cancel")
            action_button.setIcon(get_mdl2_icon(0xE711, 20, '#ffffff'))
            action_button.setIconSize(QSize(14, 14))
            action_button.setObjectName("textButton")
            action_button.setEnabled(True)
            action_button.clicked.connect(lambda: self.cancel_operation(plugin_name))
        elif is_queued:
            action_button.setText(" Queued")
            action_button.setIcon(get_mdl2_icon(0xE825, 20, '#ffffff'))
            action_button.setIconSize(QSize(14, 14))
            action_button.setObjectName("textButton")
            action_button.setEnabled(True)
            action_button.clicked.connect(lambda: self.cancel_operation(plugin_name))
        elif is_local:
            action_button.setText(" Delete")
            action_button.setIcon(get_mdl2_icon(0xE74D, 20, '#ffffff'))
            action_button.setIconSize(QSize(14, 14))
            action_button.setObjectName("uninstallButton")
            action_button.setEnabled(True)
            action_button.clicked.connect(lambda: self.confirm_delete_local_plugin(plugin_name))

            plugin_dir = os.path.join(PLUGINS_DIR, plugin_name)
            nss_enabled = is_plugin_nss_enabled(plugin_name, plugin_dir)
            if nss_enabled is not None:
                toggle_btn = QPushButton(" Disable" if nss_enabled else " Enable")
                toggle_btn.setIcon(get_mdl2_icon(0xE711 if nss_enabled else 0xE73E, 20, '#ffffff'))
                toggle_btn.setIconSize(QSize(14, 14))
                toggle_btn.setObjectName("secondaryButton" if nss_enabled else "updateButton")
                toggle_btn.setCursor(Qt.PointingHandCursor)
                font = toggle_btn.font(); font.setBold(True); toggle_btn.setFont(font)
                if nss_enabled:
                    toggle_btn.clicked.connect(lambda: self.disable_local_plugin(plugin_name))
                else:
                    toggle_btn.clicked.connect(lambda: self.enable_local_plugin(plugin_name))
                action_layout.addWidget(toggle_btn)
                self.plugin_update_buttons[plugin_name] = toggle_btn
        elif is_delisted:
            action_button.setText(" Uninstall")
            action_button.setIcon(get_mdl2_icon(0xE74D, 20, '#ffffff'))
            action_button.setIconSize(QSize(14, 14))
            action_button.setObjectName("uninstallButton")
            action_button.setEnabled(True)
            action_button.clicked.connect(lambda: self.uninstall_plugin(plugin_name))
        elif is_installed:
            action_button.setText(" Uninstall")
            action_button.setIcon(get_mdl2_icon(0xE74D, 20, '#ffffff'))
            action_button.setIconSize(QSize(14, 14))
            action_button.setObjectName("uninstallButton")
            action_button.setEnabled(True)
            action_button.clicked.connect(lambda: self.uninstall_plugin(plugin_name))
            
            if has_update:
                update_button = QPushButton(" Update")
                update_button.setIcon(get_mdl2_icon(0xE895, 20, '#ffffff'))
                update_button.setIconSize(QSize(14, 14))
                update_button.setObjectName("updateButton")
                update_button.setCursor(Qt.PointingHandCursor)
                font = update_button.font(); font.setBold(True); update_button.setFont(font)
                update_button.clicked.connect(lambda: self.add_to_installation_queue(plugin_name))
                action_layout.addWidget(update_button)
                self.plugin_update_buttons[plugin_name] = update_button
        else:
            action_button.setText(" Install")
            action_button.setIcon(get_mdl2_icon(0xE896, 20, '#ffffff'))
            action_button.setIconSize(QSize(14, 14))
            action_button.setObjectName("installButton")
            action_button.setEnabled(True)
            action_button.clicked.connect(lambda: self.add_to_installation_queue(plugin_name))
        
        action_button.style().unpolish(action_button)
        action_button.style().polish(action_button)

    def on_icon_loaded(self, plugin_name, pixmap):
        if plugin_name in self.plugin_icon_labels:
            label = self.plugin_icon_labels[plugin_name]
            if pixmap and not pixmap.isNull():
                label.setPixmap(pixmap)
            else:
                label.setPixmap(QPixmap(DEFAULT_ICON_PATH))

    def load_icon(self, plugin):
        self.plugin_logic.load_icon(plugin)

    def add_to_installation_queue(self, plugin_name):
        if plugin_name in [p['name'] for p in self.plugin_logic.installation_queue] or self.plugin_logic.current_installing_plugin == plugin_name:
            return
            
        self.plugin_logic.add_to_installation_queue(plugin_name)
        self.update_card_ui(plugin_name)

    def on_install_progress(self, plugin_name, value):
        if plugin_name == self.plugin_logic.current_installing_plugin:
            self.plugin_progress_bars[plugin_name].setValue(value)
            progress_bar = self.plugin_progress_bars[plugin_name]
            if not progress_bar.isVisible():
                progress_bar.setVisible(True)


    def on_operation_error(self, plugin_name, status, error_message):
        print(f"Operation error for {plugin_name}: {error_message}")
        if plugin_name in self.plugin_progress_bars:
            self.plugin_progress_bars[plugin_name].setVisible(False)

        self.update_card_ui(plugin_name)

        if self.details_popup and self.details_popup.plugin_data['name'] == plugin_name:
            self.details_popup.set_details_content(f"<font color='red'>Error: {error_message}</font>")
        elif not getattr(self, '_error_dialog_visible', False):
            self._error_dialog_visible = True
            msgBox = CustomMessageBox(self)
            msgBox.setText(f"Error for {plugin_name}")
            msgBox.setInformativeText(error_message)
            msgBox.finished.connect(lambda: setattr(self, '_error_dialog_visible', False))
            msgBox.show()

    def on_operation_finished(self, plugin_name, status):
        if status == "cancelled_from_queue":
            self.update_card_ui(plugin_name)
            return

        if plugin_name in self.plugin_progress_bars:
            self.plugin_progress_bars[plugin_name].setVisible(False)

        self.update_card_ui(plugin_name)
        if status == "installed" or status == "uninstalled":
            self.reload_shell()

    def cancel_operation(self, plugin_name):
        self.plugin_logic.cancel_operation(plugin_name)

    def uninstall_plugin(self, plugin_name):
        self._is_internal_change = True
        try:
            plugin_data = self.all_plugins_data.get(plugin_name, {'name': plugin_name})
            target_plugin_dir = os.path.abspath(get_plugin_install_path(plugin_data))
            if hasattr(self, 'file_watcher') and self.file_watcher:
                for d in list(self.file_watcher.directories()):
                    if d == target_plugin_dir or d.lower().startswith(target_plugin_dir.lower() + os.sep):
                        try:
                            self.file_watcher.removePath(d)
                        except Exception:
                            pass
        except Exception:
            pass
        finally:
            self._is_internal_change = False
        self.plugin_logic.uninstall_plugin(plugin_name)

    def apply_card_style(self, card):
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 160))
        shadow.setOffset(5, 5)
        card.setGraphicsEffect(shadow)

    def nativeEvent(self, event_type, message):
        if event_type == "windows_generic_MSG":
            msg = wintypes.MSG.from_address(message.__int__())
            if msg.message == win32con.WM_NCHITTEST:
                x, y = msg.pt.x, msg.pt.y
                pos = self.mapFromGlobal(QPoint(x, y))
                lx, ly = pos.x(), pos.y()
                w, h = self.width(), self.height()

                border = 15
                
                if lx < border:
                    if ly < border: return True, win32con.HTTOPLEFT
                    if ly > h - border: return True, win32con.HTBOTTOMLEFT
                    return True, win32con.HTLEFT
                if lx > w - border:
                    if ly < border: return True, win32con.HTTOPRIGHT
                    if ly > h - border: return True, win32con.HTBOTTOMRIGHT
                    return True, win32con.HTRIGHT
                if ly < border: return True, win32con.HTTOP
                if ly > h - border: return True, win32con.HTBOTTOM
                
                if ly < 50:
                    child = self.childAt(lx, ly)
                    if child and (child.inherits("QPushButton") or child.inherits("QTabBar") or child.inherits("QLineEdit") or child.objectName() == "tabBar"):
                        return False, 0
                    return True, win32con.HTCAPTION
                
                if lx < 80:
                    child = self.childAt(lx, ly)
                    # If clicking on a button or something interactive inside the sidebar, don't drag
                    if child and (child.inherits("QPushButton") or child.inherits("QTabBar") or child.inherits("QLineEdit") or "sideButton" in child.objectName()):
                        return False, 0
                    return True, win32con.HTCAPTION

                return False, 0

            elif msg.message == win32con.WM_NCCALCSIZE:
                return True, 0

            elif msg.message == 0x02E0:  # WM_DPICHANGED
                try:
                    rect_ptr = ctypes.cast(msg.lParam, ctypes.POINTER(wintypes.RECT))
                    if rect_ptr:
                        rect = rect_ptr.contents
                        x, y = rect.left, rect.top
                        w, h = rect.right - rect.left, rect.bottom - rect.top
                        wid = self.winId()
                        if wid:
                            hwnd = int(wid)
                            ctypes.windll.user32.SetWindowPos(hwnd, 0, x, y, w, h, 0x0004 | 0x0020)
                            self.setGeometry(x, y, w, h)
                            set_window_effect(hwnd, effect="acrylic")
                except Exception:
                    pass
                self.update()

            elif msg.message == 0x0232:  # WM_EXITSIZEMOVE
                try:
                    wid = self.winId()
                    if wid:
                        hwnd = int(wid)
                        set_window_effect(hwnd, effect="acrylic")
                        ctypes.windll.user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, 0x0002 | 0x0001 | 0x0004 | 0x0020)
                except Exception:
                    pass
                self.update()

        return super().nativeEvent(event_type, message)

    def showEvent(self, event):
        super().showEvent(event)
        if not getattr(self, '_window_initialized', False):
            self._window_initialized = True
            try:
                wid = self.winId()
                if wid:
                    hwnd = int(wid)
                    try:
                        DWMWCP_ROUND = 2
                        DWMWA_WINDOW_CORNER_PREFERENCE = 33
                        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_WINDOW_CORNER_PREFERENCE, ctypes.byref(ctypes.c_int(DWMWCP_ROUND)), 4)
                    except Exception:
                        pass

                    try:
                        style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
                        win32gui.SetWindowLong(hwnd, win32con.GWL_STYLE, style | win32con.WS_THICKFRAME | win32con.WS_CAPTION | win32con.WS_MINIMIZEBOX | win32con.WS_MAXIMIZEBOX | win32con.WS_SYSMENU)
                    except Exception:
                        pass

                    try:
                        set_window_effect(hwnd, effect="acrylic")
                    except Exception:
                        pass
            except Exception:
                pass

    def moveEvent(self, event):
        super().moveEvent(event)
        try:
            wid = self.winId()
            if wid:
                hwnd = int(wid)
                set_window_effect(hwnd, effect="acrylic")
        except Exception:
            pass

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() in (QEvent.WindowStateChange, QEvent.StyleChange):
            try:
                wid = self.winId()
                if wid:
                    hwnd = int(wid)
                    set_window_effect(hwnd, effect="acrylic")
                    ctypes.windll.user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, 0x0002 | 0x0001 | 0x0004 | 0x0020)
            except Exception:
                pass
            self.update()







    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor(30, 32, 48, 150))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(self.rect(), 15, 15)

    def closeEvent(self, event):
        self._is_shutting_down = True
        has_editor_dirty = hasattr(self, 'theme_editor_page') and getattr(self.theme_editor_page, 'is_dirty', False)
        has_switcher_dirty = hasattr(self, 'theme_switcher_page') and getattr(self.theme_switcher_page, 'is_dirty', False)
        has_modify_dirty = hasattr(self, 'modify_page') and getattr(self.modify_page, 'is_dirty', False)

        if has_editor_dirty or has_switcher_dirty or has_modify_dirty:
            from utils import UnsavedChangesDialog
            changes = []
            if has_switcher_dirty:
                orig_t = getattr(self.theme_switcher_page, 'original_theme', 'Default')
                curr_t = getattr(self.theme_switcher_page, 'selected_theme', 'Modified')
                changes.append(f"[Theme Switcher] Selected Theme: '{orig_t}' ➔ '{curr_t}'")
            if has_editor_dirty:
                changes.append(f"[Theme Editor] Unsaved custom theme properties / colors")
            if has_modify_dirty:
                changes.append(f"[Modify Rules] Unsaved context menu rule modifications / IDs")

            dialog = UnsavedChangesDialog(self, text="You have unsaved changes. Do you want to save them?", changes=changes)
            res = dialog.exec_()
            
            if res == 1: # Yes
                if hasattr(self, 'theme_editor_page'): self.theme_editor_page.save_theme()
                if hasattr(self, 'theme_switcher_page'): self.theme_switcher_page.save_theme()
                self.commit_tinted_icons()
                if has_modify_dirty:
                    self.modify_page.save_all_modifications()
                    self.modify_page.save_ids()
            elif res == 0: # No
                # Fast Revert: Only revert files that actually changed
                snapshot = getattr(self, 'nss_snapshot', {})
                def revert_worker():
                    from utils import safe_file_write
                    for fp, content in snapshot.items():
                        if os.path.exists(fp):
                            try:
                                with open(fp, 'r', encoding='utf-8') as f:
                                    current = f.read()
                                if current != content:
                                    safe_file_write(fp, content)
                            except: pass
                    
                    # Async cleanup
                    prev_dir = os.path.join(PROJECT_ROOT, 'imports', 'icons', 'preview')
                    if os.path.exists(prev_dir):
                        try: shutil.rmtree(prev_dir)
                        except: pass
                    from modify_widget import cleanup_orphan_icons
                    cleanup_orphan_icons(PROJECT_ROOT)
                
                threading.Thread(target=revert_worker, daemon=True).start()
                
                if hasattr(self, 'theme_editor_page'): self.theme_editor_page.is_dirty = False
                if hasattr(self, 'theme_switcher_page'): self.theme_switcher_page.is_dirty = False
                if hasattr(self, 'modify_page'): self.modify_page.is_dirty = False

            else: # Cancel (2) or any other value
                event.ignore()
                return

        # Hide window immediately for instant visual exit feeling
        self.hide()
        # Stop threads and trigger final reload via IPC (instant)
        self.plugin_logic.stop_all_threads()
        from utils import send_ipc_command
        send_ipc_command('CMD_RELOAD')
        event.accept()

    def trigger_global_tint(self, force=False):
        if not force and not self.settings_manager.get('auto_apply_theme_colors'): return
        if any(t.isRunning() for t, w in self._active_tint_threads): return
        
        # Backup all .nss files before tinting if not already backed up
        if not self.tint_backups:
            for d in [os.path.join(PROJECT_ROOT, 'imports'), os.path.join(PROJECT_ROOT, 'plugins')]:
                if not os.path.exists(d): continue
                for root, _, files in os.walk(d):
                    for f in files:
                        if f.endswith('.nss'):
                            fp = os.path.join(root, f)
                            try:
                                with open(fp, 'r', encoding='utf-8') as file: self.tint_backups[fp] = file.read()
                            except: pass

        from modify_widget import scan_nss_items, _extract_glyph_codes, _extract_all_colors, ManualSyncConflictDialog
        items = scan_nss_items(PROJECT_ROOT)
        manual_items = []
        for i in items:
            val = i['props'].get('image') or i['props'].get('icon') or ''
            codes = _extract_glyph_codes(val)
            if codes:
                colors = _extract_all_colors(val)
                if any(colors): manual_items.append(i)
                
        skip_manual_keys = set()
        if manual_items:
            # Automatically skip custom-colored items to avoid the popup
            for i in manual_items:
                skip_manual_keys.add(f"{i['file']}:{i['start']}")
        # Create backups before tinting if we don't have them
        if not self.tint_backups:
            imports_dir = os.path.join(PROJECT_ROOT, 'imports')
            if os.path.exists(imports_dir):
                for f in os.listdir(imports_dir):
                    if f.endswith('.nss') and f != 'theme.nss':
                        fp = os.path.join(imports_dir, f)
                        try:
                            with open(fp, 'r', encoding='utf-8') as f_obj:
                                self.tint_backups[fp] = f_obj.read()
                        except: pass

        theme_c = _get_theme_glyph_colors()[0]
        self.tint_overlay = QFrame(self); self.tint_overlay.setGeometry(self.rect())
        self.tint_overlay.setStyleSheet("background: rgba(15, 17, 26, 230); border-radius: 15px;")
        vl = QVBoxLayout(self.tint_overlay); vl.setAlignment(Qt.AlignCenter); vl.setSpacing(15)
        
        self.tint_progress = PillProgressBar(self.tint_overlay, height=20); self.tint_progress.setFixedWidth(320)
        vl.addWidget(self.tint_progress)
        
        self.tint_label = QLabel("Syncing theme colors to all icons...")
        self.tint_label.setStyleSheet("color: #b0b0b0; font-size: 14px; font-weight: bold; background: transparent;")
        self.tint_label.setAlignment(Qt.AlignCenter); vl.addWidget(self.tint_label)
        self.tint_overlay.show()
        
        thread = QThread(); worker = GlobalTintWorker(PROJECT_ROOT, theme_c, skip_manual_keys); worker.moveToThread(thread)
        thread.started.connect(worker.run); worker.progress.connect(lambda v, t: self.tint_progress.setValue(int(v/t*100)))
        worker.status.connect(lambda msg: self.tint_label.setText(msg))
        worker.finished.connect(thread.quit); worker.finished.connect(self.tint_overlay.deleteLater); worker.finished.connect(lambda: self.modify_page.refresh_ui())
        worker.finished.connect(lambda: self._active_tint_threads.remove((thread, worker)))
        worker.finished.connect(self.reload_shell)
        thread.finished.connect(thread.deleteLater); self._active_tint_threads.append((thread, worker)); thread.start()

    def setup_settings_page(self):
        layout = QVBoxLayout(self.settings_page)
        layout.setContentsMargins(40, 40, 40, 40); layout.setSpacing(15); layout.setAlignment(Qt.AlignTop)
        
        # Settings Header
        header = QHBoxLayout()
        header.setSpacing(15)
        header.setContentsMargins(0, 0, 0, 10)
        title = QLabel("Settings"); title.setFont(QFont('Segoe UI Variable Display', 26, QFont.Bold)); title.setStyleSheet("color: white; background: transparent; border: none;")
        header.addWidget(title)
        header.addStretch()
        
        self.ver_label = QLabel(f"V {VERSION}")
        self.ver_label.setStyleSheet("color: #b0b0b0; font-size: 14px; font-weight: bold; border: none; background: transparent;")
        header.addWidget(self.ver_label)
        
        self.update_btn = QPushButton("Check for Update"); self.update_btn.setFixedSize(140, 36); self.update_btn.setCursor(Qt.PointingHandCursor)
        self.update_btn.setFocusPolicy(Qt.NoFocus)
        self.update_btn.setStyleSheet("QPushButton { background-color: #dc143c !important; border-radius: 12px !important; color: #1e2030 !important; font-weight: bold !important; border: none !important; } QPushButton:hover { background-color: #f53155 !important; }")
        self.update_btn.clicked.connect(lambda: self.check_app_update(manual=True))
        header.addWidget(self.update_btn)
        layout.addLayout(header)
        layout.addSpacing(10)

        self.auto_update_sw = self._create_setting_row(layout, "Auto Update Plugins", "Automatically install updates on startup", "auto_update")
        self.auto_check_sw = self._create_setting_row(layout, "Auto Check Updates", "Show notification when updates are available", "auto_check_updates")
        self.auto_save_sw = self._create_setting_row(layout, "Auto Save Changes", "Commit changes immediately in all editors", "auto_save")
        self.auto_tint_sw = self._create_setting_row(layout, "Auto Apply Theme Colors", "Sync local icons with Image 1/2 theme colors", "auto_apply_theme_colors")
        self.auto_preview_sw = self._create_setting_row(layout, "Auto Preview Context Menu", "Show preview automatically. If disabled, use (Left + Right Click or Ctrl + Right Click) manually", "auto_preview_context_menu")
        
        self._create_import_row(layout)
        self._create_sync_section(layout)
        layout.addStretch()
        
        # Force a UI state update to ensure buttons are visible based on login status
        QTimer.singleShot(100, self._update_sync_ui_state)

        # Check for update on startup (silently)
        QTimer.singleShot(5000, lambda: self.check_app_update(manual=False))

    def check_app_update(self, manual=False, force=False):
        import time
        if not manual and not force:
            last_check = self.settings_manager.get('last_update_check') or 0
            if last_check == 0 and os.path.exists(os.path.join(TEMP_DIR, 'ima_last_update_check.txt')):
                try:
                    with open(os.path.join(TEMP_DIR, 'ima_last_update_check.txt')) as f:
                        last_check = float(f.read().strip())
                except Exception:
                    last_check = 0
            if time.time() - last_check < 86400:
                return

        now = time.time()
        self.settings_manager.set('last_update_check', now)
        self.settings_manager.save()
        try:
            marker = os.path.join(TEMP_DIR, 'ima_last_update_check.txt')
            with open(marker, 'w') as f:
                f.write(str(now))
        except Exception:
            pass

        if getattr(self, '_update_dialog_active', False):
            return
        if manual:
            self.update_btn.setText('Checking...'); self.update_btn.setEnabled(False)

        self._update_threads = getattr(self, '_update_threads', [])
        thread = QThread(self)
        worker = UpdateWorker()
        worker.moveToThread(thread)
        self._update_threads.append((thread, worker))

        def _cleanup():
            try:
                self._update_threads.remove((thread, worker))
            except Exception:
                pass

        thread.started.connect(lambda: worker.check_for_updates(force=force))
        worker.check_finished.connect(lambda h, v, u: self.on_check_finished(h, v, u, manual, force))
        worker.check_finished.connect(thread.quit)
        thread.finished.connect(_cleanup)
        thread.finished.connect(thread.deleteLater)
        thread.start()

    def on_check_finished(self, has_update, latest_version, download_url, manual, force=False):
        if manual:
            self.update_btn.setText('Check for Update')
            self.update_btn.setEnabled(True)

        if has_update:
            if download_url:
                self._update_dialog_active = True
                self.latest_app_version = latest_version
                self.ver_label.setText(f"Current: {VERSION} | <span style='color: #dc143c;'>Latest: {latest_version}</span>")
                dialog = ModernDialog(self, 'Update Available', f"A new version of iMA Menu Launcher is available: <b>v{latest_version}</b><br><br>Would you like to download and install it now?")
                dialog.add_button('Update Now', 'installButton', lambda: dialog.done(1))
                dialog.add_button('Later', 'sideButton', dialog.reject)
                dialog_result = dialog.exec_()
                self._update_dialog_active = False
                if dialog_result == 1:
                    self.start_app_download(download_url)
            elif manual:
                info_dialog = ModernDialog(self, 'Update Available', f"A new release <b>v{latest_version}</b> was found, but no installer binary is attached to the release yet.")
                info_dialog.add_button('OK', 'sideButton', info_dialog.accept)
                info_dialog.exec_()
        elif manual:
            up_to_date_dialog = ModernDialog(self, 'Up to Date', f'You are running the latest version <b>v{VERSION}</b>.')
            up_to_date_dialog.add_button('OK', 'sideButton', up_to_date_dialog.accept)
            up_to_date_dialog.add_button('Re-install', 'installButton', lambda: up_to_date_dialog.done(2))
            dialog_result = up_to_date_dialog.exec_()
            if dialog_result == 2:
                self.check_app_update(manual=True, force=True)

    def start_app_download(self, download_url):
        self.dl_msg = ModernDialog(self, "Downloading Update", "Please wait while the new version is being downloaded...")
        
        progress_container = QWidget()
        progress_layout = QVBoxLayout(progress_container)
        progress_layout.setContentsMargins(0, 5, 0, 5)
        progress_layout.setSpacing(8)

        self.dl_bar = PillProgressBar(height=20)
        
        self.percent_label = QLabel("0%")
        self.percent_label.setStyleSheet("color: white; font-weight: bold; font-size: 14px;")
        self.percent_label.setAlignment(Qt.AlignCenter)
        progress_layout.addWidget(self.dl_bar)
        progress_layout.addWidget(self.percent_label)
        
        self.dl_msg.cl.insertWidget(2, progress_container)
        self.dl_msg.add_button("Cancel", "uninstallButton", self.dl_msg.reject)
        
        self.dl_thread = QThread(self)
        self.dl_worker = UpdateWorker()
        self.dl_worker.moveToThread(self.dl_thread)
        self.dl_thread.started.connect(lambda: self.dl_worker.download_update(download_url))
        self.dl_worker.download_progress.connect(self._update_dl_progress)
        self.dl_worker.download_finished.connect(self.on_download_finished)
        self.dl_worker.download_finished.connect(self.dl_thread.quit)
        self.dl_thread.finished.connect(self.dl_thread.deleteLater)
        self.dl_thread.start()
        self.dl_msg.exec_()

    def _update_dl_progress(self, val):
        self.dl_bar.setValue(val)
        self.percent_label.setText(f"{val}%")
        QApplication.processEvents()

    def on_download_finished(self, success, result):
        self.dl_msg.accept()
        if success:
            self.apply_app_update(result)
        else:
            error_dialog = ModernDialog(self, "Download Failed", f"An error occurred while downloading the update:<br>{result}")
            error_dialog.add_button("OK", "installButton", error_dialog.accept)
            error_dialog.exec_()

    def apply_app_update(self, new_exe_path):
        if getattr(sys, 'frozen', False):
            current_exe = os.path.abspath(sys.executable)
        else:
            current_exe = os.path.abspath(os.path.join(APP_BASE_PATH, 'launcher.exe'))
            if not os.path.exists(current_exe):
                current_exe = os.path.abspath(sys.argv[0])

        current_pid = os.getpid()
        app_dir = os.path.dirname(current_exe)
        old_exe_path = os.path.join(app_dir, 'launcher.old.exe')
        needs_elevation = not _can_write_to_dir(app_dir)

        updater_src = resource_path('ima_updater.exe')
        temp_updater = os.path.join(tempfile.gettempdir(), 'ima_updater.exe')
        if os.path.exists(updater_src):
            try:
                shutil.copy2(updater_src, temp_updater)
            except Exception:
                pass
        elif os.path.exists(os.path.join(APP_BASE_PATH, 'ima_updater.exe')):
            try:
                shutil.copy2(os.path.join(APP_BASE_PATH, 'ima_updater.exe'), temp_updater)
            except Exception:
                pass

        temp_new_shell_dll = os.path.join(tempfile.gettempdir(), 'shell_new.dll')
        temp_new_shell_exe = os.path.join(tempfile.gettempdir(), 'shell_new.exe')
        
        bundled_shell_dll = resource_path('shell.dll')
        if not os.path.exists(bundled_shell_dll):
            bundled_shell_dll = os.path.join(APP_BASE_PATH, 'shell.dll')
        if os.path.exists(bundled_shell_dll):
            try: shutil.copy2(bundled_shell_dll, temp_new_shell_dll)
            except Exception: pass

        bundled_shell_exe = resource_path('shell.exe')
        if not os.path.exists(bundled_shell_exe):
            bundled_shell_exe = os.path.join(APP_BASE_PATH, 'shell.exe')
        if os.path.exists(bundled_shell_exe):
            try: shutil.copy2(bundled_shell_exe, temp_new_shell_exe)
            except Exception: pass

        parent_dir = os.path.abspath(os.path.join(app_dir, '..'))
        target_shell_dll = os.path.join(parent_dir, 'shell.dll')
        target_shell_exe = os.path.join(parent_dir, 'shell.exe')

        updater_args = f'--pid {current_pid} --target "{current_exe}" --new "{new_exe_path}" --old "{old_exe_path}" --dir "{app_dir}" --new-shell "{temp_new_shell_dll}" --new-shell-exe "{temp_new_shell_exe}" --target-shell "{target_shell_dll}" --shell-exe "{target_shell_exe}"'

        try:
            ctypes.windll.shell32.ShellExecuteW(
                None,
                'runas' if needs_elevation else None,
                temp_updater,
                updater_args,
                app_dir,
                0
            )
            os._exit(0)
        except Exception as launch_error:
            error_dialog = ModernDialog(self, 'Update Error', f'Could not launch updater:<br>{launch_error}')
            error_dialog.add_button('OK', 'installButton', error_dialog.accept)
            error_dialog.exec_()


    def _create_setting_row(self, layout, title, desc, key):
        row = QFrame(); row.setStyleSheet("QFrame { background: rgba(255,255,255,0.04); border-radius: 15px; border: 1px solid rgba(255,255,255,0.05); } QFrame:hover { background: rgba(255,255,255,0.06); }")
        rl = QHBoxLayout(row); rl.setContentsMargins(20, 15, 20, 15)
        v = QVBoxLayout(); t = QLabel(title); t.setStyleSheet("color: white; font-size: 15px; font-weight: bold; border: none; background: transparent;")
        d = QLabel(desc); d.setStyleSheet("color: #b0b0b0; font-size: 12px; border: none; background: transparent;")
        v.addWidget(t); v.addWidget(d); rl.addLayout(v); rl.addStretch()
        sw = ModernSwitch(checked=self.settings_manager.get(key)); sw.stateChanged.connect(lambda v: self.settings_manager.set(key, v))
        if key == "auto_save": sw.stateChanged.connect(self._update_widgets_autosave)
        rl.addWidget(sw); layout.addWidget(row); return sw

    def _update_widgets_autosave(self):
        enabled = self.settings_manager.get('auto_save')
        if hasattr(self, 'modify_page'): self.modify_page.auto_save = enabled
        if hasattr(self, 'theme_switcher_page'): self.theme_switcher_page.auto_save = enabled
        if hasattr(self, 'theme_editor_page'): self.theme_editor_page.auto_save = enabled

    def _create_import_row(self, layout):
        row = QFrame(); row.setStyleSheet("QFrame { background: rgba(255,255,255,0.04); border-radius: 15px; border: 1px solid rgba(255,255,255,0.05); } QFrame:hover { background: rgba(255,255,255,0.06); }")
        rl = QHBoxLayout(row); rl.setContentsMargins(20, 15, 20, 15)
        v = QVBoxLayout(); t = QLabel("Import NSS Files"); t.setStyleSheet("color: white; font-size: 15px; font-weight: bold; border: none; background: transparent;")
        d = QLabel("Copy external files to imports and shell.nss"); d.setStyleSheet("color: #b0b0b0; font-size: 12px; border: none; background: transparent;")
        v.addWidget(t); v.addWidget(d); rl.addLayout(v); rl.addStretch()
        
        edit_btn = QPushButton("\uE104"); edit_btn.setFixedSize(36, 36); edit_btn.setCursor(Qt.PointingHandCursor)
        edit_btn.setFont(QFont('Segoe MDL2 Assets', 14))
        edit_btn.setStyleSheet("QPushButton { background: rgba(255,255,255,0.05); border-radius: 18px; border: 1px solid rgba(255,255,255,0.1); color: #b0b0b0; } QPushButton:hover { background: rgba(220, 20, 60, 0.2); border: 1px solid #dc143c; color: white; }")
        edit_btn.clicked.connect(self.show_imports_manager)
        
        btn = QPushButton("Import"); btn.setFixedSize(100, 36); btn.setCursor(Qt.PointingHandCursor); btn.clicked.connect(self.import_nss_files)
        btn.setStyleSheet("QPushButton { background-color: #dc143c !important; border-radius: 12px !important; color: #1e2030 !important; font-weight: bold !important; border: none !important; } QPushButton:hover { background-color: #f53155 !important; }")
        rl.addWidget(edit_btn); rl.addWidget(btn); layout.addWidget(row)

    def show_imports_manager(self):
        d = ModernDialog(self, "Manage Imports", "Review or remove NSS imports from your shell configuration.")
        d.setMinimumHeight(500)
        
        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setStyleSheet("background: transparent; border: none;")
        cont = QWidget(); cl = QVBoxLayout(cont); cl.setSpacing(10); cl.setAlignment(Qt.AlignTop); scroll.setWidget(cont)
        d.cl.insertWidget(2, scroll)
        
        sh_nss = os.path.join(PROJECT_ROOT, 'shell.nss')
        if not os.path.exists(sh_nss): return
        
        def refresh_list():
            for i in reversed(range(cl.count())): cl.itemAt(i).widget().deleteLater()
            with open(sh_nss, 'r') as f: lines = f.readlines()
            imports = [line.strip() for line in lines if line.strip().startswith("import ")]
            if not imports:
                empty = QLabel("No imports found."); empty.setStyleSheet("color: #333333; padding: 20px;"); empty.setAlignment(Qt.AlignCenter); cl.addWidget(empty)
            for imp in imports:
                path = re.search(r"['\"](.+?)['\"]", imp)
                if not path: continue
                path = path.group(1)
                item = QFrame(); item.setStyleSheet("QFrame { background: rgba(255,255,255,0.05); border-radius: 12px; border: 1px solid rgba(255,255,255,0.05); }")
                il = QHBoxLayout(item); il.setContentsMargins(15, 10, 15, 10)
                iv = QVBoxLayout(); it = QLabel(os.path.basename(path)); it.setStyleSheet("color: white; font-weight: bold; border: none; font-size: 14px; background: transparent;")
                ip = QLabel(path); ip.setStyleSheet("color: #888888; font-size: 11px; border: none; background: transparent;")
                iv.addWidget(it); iv.addWidget(ip); il.addLayout(iv); il.addStretch()
                
                open_btn = QPushButton(); open_btn.setFixedSize(30, 30); open_btn.setIcon(QIcon(resource_path('icons/open.png'))); open_btn.setIconSize(QSize(20, 20))
                open_btn.setStyleSheet("QPushButton { background: transparent; border: none; } QPushButton:hover { background: rgba(255, 255, 255, 0.05); border-radius: 5px; }")
                open_btn.clicked.connect(lambda _, p=path: os.startfile(os.path.join(PROJECT_ROOT, p)) if os.path.exists(os.path.join(PROJECT_ROOT, p)) else None)
                
                del_btn = QPushButton("\uE107"); del_btn.setFixedSize(30, 30); del_btn.setFont(QFont('Segoe MDL2 Assets', 14))
                del_btn.setStyleSheet("QPushButton { background: transparent; border: none; color: #b0b0b0; } QPushButton:hover { color: #dc143c; }")
                del_btn.clicked.connect(lambda _, s=imp: self.remove_import_from_shell(s, refresh_list))
                
                il.addWidget(open_btn); il.addWidget(del_btn); cl.addWidget(item)

        refresh_list()
        d.add_button("Close", "uninstallButton", d.accept); d.exec_()

    def remove_import_from_shell(self, import_line, callback):
        sh_nss = os.path.join(PROJECT_ROOT, 'shell.nss')
        if not os.path.exists(sh_nss): return
        with open(sh_nss, 'r') as f: lines = f.readlines()
        new_lines = [l for l in lines if l.strip() != import_line]
        with open(sh_nss, 'w') as f: f.writelines(new_lines)
        callback()

    def import_nss_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Select NSS Files", "", "NSS Files (*.nss)")
        if not files: return
        imp_dir = os.path.join(PROJECT_ROOT, 'imports'); os.makedirs(imp_dir, exist_ok=True)
        sh_nss = os.path.join(PROJECT_ROOT, 'shell.nss')
        for src in files:
            fname = os.path.basename(src); dest = os.path.join(imp_dir, fname)
            if os.path.exists(dest) and os.path.abspath(src) != os.path.abspath(dest):
                d = ModernDialog(self, "File Conflict", f"'{fname}' already exists in imports.")
                d.add_button("Overwrite", "installButton", lambda: d.done(1))
                d.add_button("Rename", "sideButton", lambda: d.done(2))
                d.add_button("Cancel", "uninstallButton", lambda: d.done(0))
                res = d.exec_()
                if res == 0: continue
                if res == 2:
                    new, ok = QInputDialog.getText(self, "Rename", "New name:", QLineEdit.Normal, fname)
                    if not ok or not new: continue
                    if not new.endswith(".nss"): new += ".nss"
                    fname = new; dest = os.path.join(imp_dir, fname)
            try:
                if os.path.abspath(src) != os.path.abspath(dest): shutil.copy2(src, dest)
                line = f"import \'imports/{fname}\'"
                if os.path.exists(sh_sh := os.path.join(PROJECT_ROOT, 'shell.nss')):
                    with open(sh_sh, 'r') as f: c = f.read()
                    if line not in c:
                        with open(sh_sh, 'a') as f: f.write(f"\n{line}")
            except Exception as e: self.on_operation_error("Import", "failed", str(e))
        self.reload_shell()
        m = ModernDialog(self, "Success", "Selected NSS files imported."); m.add_button("OK", "installButton", m.accept); m.exec_()


    def _create_sync_section(self, layout):
        row = QFrame(); row.setStyleSheet("QFrame { background: rgba(255,255,255,0.04); border-radius: 15px; border: 1px solid rgba(255,255,255,0.05); } QFrame:hover { background: rgba(255,255,255,0.06); }")
        rl = QHBoxLayout(row); rl.setContentsMargins(20, 15, 20, 15)
        v = QVBoxLayout(); t = QLabel("Google Drive Sync"); t.setStyleSheet("color: white; font-size: 15px; font-weight: bold; border: none; background: transparent;")
        self.sync_status_label = QLabel("Not logged in" if not self.sync_manager.user_email else f"Logged in as {self.sync_manager.user_email}")
        self.sync_status_label.setStyleSheet("color: #b0b0b0; font-size: 12px; border: none; background: transparent;")
        v.addWidget(t); v.addWidget(self.sync_status_label); rl.addLayout(v); rl.addStretch()
        
        self.sync_login_btn = QPushButton("Login"); self.sync_login_btn.setFixedSize(100, 36); self.sync_login_btn.setCursor(Qt.PointingHandCursor)
        self.sync_login_btn.setStyleSheet("QPushButton { background-color: #dc143c !important; border-radius: 12px !important; color: #1e2030 !important; font-weight: bold !important; border: none !important; } QPushButton:hover { background-color: #f53155 !important; }")
        self.sync_login_btn.clicked.connect(self.sync_manager.login)
        
        self.sync_backup_btn = QPushButton("Backup"); self.sync_backup_btn.setFixedSize(100, 36); self.sync_backup_btn.setCursor(Qt.PointingHandCursor)
        self.sync_backup_btn.setStyleSheet("QPushButton { background-color: #4AE290 !important; border-radius: 12px !important; color: #121212 !important; font-weight: bold !important; border: 2px solid #2a2a30 !important; } QPushButton:hover { background-color: #60F2A5 !important; }")
        self.sync_backup_btn.clicked.connect(self.sync_manager.backup)
        
        self.sync_restore_btn = QPushButton("Restore"); self.sync_restore_btn.setFixedSize(100, 36); self.sync_restore_btn.setCursor(Qt.PointingHandCursor)
        self.sync_restore_btn.setStyleSheet("QPushButton { background-color: #4A90E2 !important; border-radius: 12px !important; color: #121212 !important; font-weight: bold !important; border: 2px solid #2a2a30 !important; } QPushButton:hover { background-color: #5D9CEB !important; }")
        self.sync_restore_btn.clicked.connect(self.sync_manager.restore)
        
        self.sync_logout_btn = QPushButton("\uE77B"); self.sync_logout_btn.setFixedSize(36, 36); self.sync_logout_btn.setCursor(Qt.PointingHandCursor)
        self.sync_logout_btn.setFont(QFont('Segoe MDL2 Assets', 14))
        self.sync_logout_btn.setStyleSheet("QPushButton { background: rgba(255,255,255,0.05); border-radius: 18px; border: 1px solid rgba(255,255,255,0.1); color: #b0b0b0; } QPushButton:hover { background: rgba(255, 42, 85, 0.2); border: 1px solid #dc143c; color: white; }")
        self.sync_logout_btn.clicked.connect(self._handle_sync_logout)
        
        rl.addWidget(self.sync_login_btn); rl.addWidget(self.sync_backup_btn); rl.addWidget(self.sync_restore_btn); rl.addWidget(self.sync_logout_btn)
        layout.addWidget(row)
        self._update_sync_ui_state()

    def _handle_sync_logout(self):
        self.sync_manager.logout()
        self._update_sync_ui_state()

    def _update_sync_ui_state(self):
        logged_in = self.sync_manager.access_token is not None
        self.sync_login_btn.setVisible(not logged_in)
        self.sync_backup_btn.setVisible(logged_in)
        self.sync_restore_btn.setVisible(logged_in)
        self.sync_logout_btn.setVisible(logged_in)
        self.sync_status_label.setText("Not logged in" if not logged_in else f"Logged in as {self.sync_manager.user_email}")

    def on_sync_auth_finished(self, success, message):
        if success:
            self._update_sync_ui_state()
            ModernDialog(self, "Cloud Sync", f"Successfully logged in as {message}").show()
        else:
            ModernDialog(self, "Cloud Sync Error", f"Authentication failed: {message}").show()

    def on_sync_progress(self, percentage, status):
        if not hasattr(self, 'sync_dl_msg') or not self.sync_dl_msg.isVisible():
            self.sync_dl_msg = ModernDialog(self, "Cloud Sync", status)
            self.sync_bar = PillProgressBar(height=20)
            self.sync_perc = QLabel("0%"); self.sync_perc.setStyleSheet("color: #dc143c; font-size: 12px; font-weight: bold; background: transparent;"); self.sync_perc.setAlignment(Qt.AlignCenter)
            self.sync_dl_msg.cl.insertWidget(2, self.sync_bar)
            self.sync_dl_msg.cl.insertWidget(3, self.sync_perc)
            self.sync_dl_msg.show()
        
        self.sync_dl_msg.ml.setText(status)
        self.sync_bar.setValue(percentage)
        self.sync_perc.setText(f"{percentage}%")

    def on_sync_finished(self, success, message):
        if hasattr(self, 'sync_dl_msg'): self.sync_dl_msg.close()
        if success:
            self.full_ui_refresh()
            ModernDialog(self, "Cloud Sync", message).show()
        else:
            ModernDialog(self, "Cloud Sync Error", message).show()

if __name__ == '__main__':
    if os.name == 'nt':
        try:
            myappid = 'iMAboud.iMAMenu.Launcher.1'
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except Exception:
            pass

    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    app_font = QFont('Segoe UI Variable Display', 10)
    app_font.setWeight(QFont.Medium)
    app.setFont(app_font)
    try:
        with open(resource_path('style.css')) as f:
            app.setStyleSheet(f.read())
    except FileNotFoundError:
        print("Warning: style.css not found.")
    manager = PluginManager()
    manager.show()

    def _auto_upgrade_shell_core_if_needed():
        try:
            from utils import get_shell_dll_version, launch_shell_core_update
            ver = get_shell_dll_version()
            if ver < (2, 0, 0, 2):
                launch_shell_core_update(parent=manager)
        except Exception as e:
            print(f"Auto-upgrade shell core error: {e}")

    QTimer.singleShot(1500, _auto_upgrade_shell_core_if_needed)
    sys.exit(app.exec_())