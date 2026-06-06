import sys
import os
import traceback

# Fatal error logging
def global_exception_handler(exctype, value, tb):
    try:
        # Use PROJECT_ROOT if available, otherwise fallback to executable/script dir
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
                             QSize, QEvent, QPoint, QRect, pyqtProperty, QFileSystemWatcher)
try: from PyQt5 import QtSvg
except ImportError: QtSvg = None
from modify_widget import ModifyWidget, CustomMessageBox, GlobalTintWorker, _get_theme_glyph_colors, get_font_icon, set_project_root
from theme_switcher_widget import ThemeSwitcherWidget
from theme_editor_widget import ThemeEditorWidget
from utils import resource_path, safe_file_write, set_window_effect, UnsavedChangesDialog, trigger_shell_reload, terminate_plugin_processes, get_mdl2_icon, global_undo_stack
from cloud_sync import CloudSyncManager
from nss_error_monitor import ShellLogMonitor

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

APP_REPO = "iMAboud/iMA-Menu-Plugins"
_GITHUB_REPO = "iMAboud/iMA-Menu-Plugins"
GITHUB_PLUGINS_JSON_URL = f"https://raw.githubusercontent.com/{_GITHUB_REPO}/main/plugins.json"
GITHUB_API_BASE_URL = f"https://api.github.com/repos/{_GITHUB_REPO}"
GITHUB_RELEASES_API_URL = f"{GITHUB_API_BASE_URL}/releases/latest"
APP_RELEASES_API_URL = f"https://api.github.com/repos/{APP_REPO}/releases"
REQUEST_TIMEOUT = 15

session = requests.Session()

def git_blob_sha(filepath):
    try:
        with open(filepath, 'rb') as f:
            data = f.read()
        header = f"blob {len(data)}\0".encode('utf-8')
        return hashlib.sha1(header + data).hexdigest()
    except Exception:
        return None

# --- Robust Path Detection & Directory Initialization ---
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
        if os.path.exists(exe): subprocess.Popen([exe, '-reload'], creationflags=0x08000000)
        
        if close_only: sys.exit(0)

    return APP_BASE_PATH

TEMP_DIR = os.environ.get('TEMP', os.path.expanduser('~'))
VERSION_FILE_FALLBACK = os.path.join(TEMP_DIR, 'ima_launcher_version.txt')

def _can_write_to_dir(directory):
    try:
        test = os.path.join(directory, '.write_test_tmp')
        with open(test, 'w') as f:
            f.write('x')
        os.remove(test)
        return True
    except Exception:
        return False

def get_current_version():
    for vfile in [VERSION_FILE, VERSION_FILE_FALLBACK]:
        if os.path.exists(vfile):
            try:
                v = open(vfile, 'r').read().strip()
                if v:
                    return v
            except Exception:
                pass
    try:
        for vfile in [VERSION_FILE, VERSION_FILE_FALLBACK]:
            try:
                os.makedirs(os.path.dirname(vfile), exist_ok=True)
                with open(vfile, 'w') as f:
                    f.write('2.0.4')
                break
            except Exception:
                continue
    except Exception:
        pass
    return '2.0.4'

def _write_version(version_str):
    written = False
    for vfile in [VERSION_FILE, VERSION_FILE_FALLBACK]:
        try:
            os.makedirs(os.path.dirname(vfile), exist_ok=True)
            with open(vfile, 'w') as f:
                f.write(version_str)
            written = True
            break
        except Exception:
            continue
    return written

def _parse_version(tag):
    clean = tag.lower().lstrip('v').split('-')[0].split('+')[0]
    parts = clean.split('.')
    result = []
    for p in parts:
        try:
            result.append(int(p))
        except ValueError:
            result.append(0)
    return tuple(result) if result else (0,)


VERSION = get_current_version()

class UpdateWorker(QObject):
    check_finished = pyqtSignal(bool, str, str)
    download_progress = pyqtSignal(int)
    download_finished = pyqtSignal(bool, str)

    def check_for_updates(self):
        try:
            resp = requests.get(APP_RELEASES_API_URL, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list) and len(data) > 0:
                    data = data[0]
                latest_tag = data.get('tag_name', '').strip()
                if not latest_tag:
                    self.check_finished.emit(False, VERSION, None)
                    return
                try:
                    v_latest = _parse_version(latest_tag)
                    v_current = _parse_version(VERSION)
                except Exception:
                    self.check_finished.emit(False, VERSION, None)
                    return

                clean_latest = latest_tag.lower().lstrip('v').split('-')[0]

                if v_latest > v_current:
                    download_url = None
                    for asset in data.get('assets', []):
                        if asset['name'].lower() == 'launcher.exe':
                            download_url = asset['browser_download_url']
                            break
                    self.check_finished.emit(True, clean_latest, download_url)
                    return
            self.check_finished.emit(False, VERSION, None)
        except Exception:
            self.check_finished.emit(False, VERSION, None)

    def download_update(self, url):
        try:
            dest = os.path.join(TEMP_DIR, 'iMA_Launcher_update.exe')
            resp = requests.get(url, stream=True, timeout=60)
            resp.raise_for_status()
            total = int(resp.headers.get('content-length', 0))
            downloaded = 0
            with open(dest, 'wb') as f:
                for chunk in resp.iter_content(chunk_size=65536):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total > 0:
                            self.download_progress.emit(int(downloaded / total * 100))
            if total > 0 and downloaded < total * 0.95:
                raise IOError(f'Incomplete download: got {downloaded}/{total} bytes')
            self.download_finished.emit(True, dest)
        except Exception as e:
            self.download_finished.emit(False, str(e))


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
        super().mousePressEvent(e)

def add_nss_import(plugin_data, nss_file_path):
    nss_path = resolve_path(plugin_data['nss_path'])
    nss_file = plugin_data['nss_file']
    
    # Make the nss_path relative to the project root for the import statement
    relative_nss_path = os.path.relpath(nss_path, PROJECT_ROOT).replace(os.sep, '/')
    import_statement = f"import \'{relative_nss_path}/{nss_file}\'\n"

    try:
        with open(nss_file_path, 'r', encoding='utf-8-sig') as f:
            lines = f.readlines()

        if any(import_statement.strip() in line for line in lines):
            return

        last_import_index = -1
        for i, line in enumerate(lines):
            if line.strip().startswith("import"):
                last_import_index = i
        
        if last_import_index != -1:
            lines.insert(last_import_index + 1, import_statement)
        else:
            lines.append(import_statement)

        from utils import AsyncFileIo
        AsyncFileIo.write(nss_file_path, "".join(lines))
    except IOError as e:
        print(f"Error updating shell.nss: {e}")

def remove_nss_import(plugin_data, nss_file_path):
    nss_path = resolve_path(plugin_data['nss_path'])
    nss_file = plugin_data['nss_file']
    relative_nss_path = os.path.relpath(nss_path, PROJECT_ROOT).replace(os.sep, '/')
    import_statement = f"import '{relative_nss_path}/{nss_file}'"
    try:
        with open(nss_file_path, 'r', encoding='utf-8-sig') as f:
            lines = f.readlines()
        
        new_lines = [line for line in lines if import_statement not in line]
        
        from utils import AsyncFileIo
        AsyncFileIo.write(nss_file_path, "".join(new_lines))
    except IOError as e:
        print(f"Error updating shell.nss: {e}")


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

class FetchPluginsThread(QObject):
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, token):
        super().__init__()
        self.token = token

    def run(self):
        try:
            response = session.get(GITHUB_PLUGINS_JSON_URL, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            plugins = response.json()

            with open(PLUGINS_CACHE_FILE, 'w') as f:
                json.dump(plugins, f, indent=4)

            self.finished.emit(plugins)
        except requests.exceptions.RequestException as e:
            self.error.emit(f"Network error: {e}")
        except json.JSONDecodeError as e:
            self.error.emit(f"Error decoding JSON: {e}")

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
            response = session.get(self.url, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
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
    finished = pyqtSignal(str, str)
    error = pyqtSignal(str, str, str)

    def __init__(self, plugin_data):
        super().__init__()
        self.plugin_data = plugin_data
        self.plugin_name = plugin_data['name']
        self._is_cancelled = False
        self.files_to_download = []

    def run(self):
        try:
            target_plugin_dir = get_plugin_install_path(self.plugin_data)

            branch_url = f"{GITHUB_API_BASE_URL}/branches/main"
            branch_res = session.get(branch_url, timeout=REQUEST_TIMEOUT)
            branch_res.raise_for_status()
            root_tree_sha = branch_res.json()['commit']['commit']['tree']['sha']

            tree_data = None
            if os.path.exists(GIT_TREE_CACHE_FILE):
                try:
                    with open(GIT_TREE_CACHE_FILE, 'r') as f:
                        cache_data = json.load(f)
                    if cache_data.get('sha') == root_tree_sha:
                        tree_data = cache_data.get('tree')
                except (json.JSONDecodeError, IOError):
                    tree_data = None

            if tree_data is None:
                trees_api_url = f"{GITHUB_API_BASE_URL}/git/trees/{root_tree_sha}?recursive=true"
                tree_res = session.get(trees_api_url, timeout=REQUEST_TIMEOUT)
                tree_res.raise_for_status()
                tree_data = tree_res.json()
                with open(GIT_TREE_CACHE_FILE, 'w') as f:
                    json.dump({'sha': root_tree_sha, 'tree': tree_data}, f)

            if 'tree' not in tree_data:
                raise Exception("Malformed response from Git Trees API")

            plugin_path_prefix = f"{self.plugin_name}/"
            base_download_url = f"https://raw.githubusercontent.com/{_GITHUB_REPO}/main"

            for item in tree_data['tree']:
                if self._is_cancelled:
                    self.finished.emit(self.plugin_name, "cancelled")
                    return
                if item.get('type') == 'blob' and item['path'].startswith(plugin_path_prefix):
                    relative_path = item['path'][len(plugin_path_prefix):]
                    download_url = f"{base_download_url}/{item['path']}"
                    self.files_to_download.append({'url': download_url, 'path': relative_path, 'sha': item.get('sha')})
            
            if not self.files_to_download:
                 raise Exception(f"Could not find any files for plugin '{self.plugin_name}' in the repository.")

            if self._is_cancelled:
                self.finished.emit(self.plugin_name, "cancelled")
                return

            # Kill any running processes before updating
            terminate_plugin_processes(target_plugin_dir)
            self.download_files(target_plugin_dir)
            if self._is_cancelled:
                if os.path.exists(target_plugin_dir):
                    shutil.rmtree(target_plugin_dir)
                self.finished.emit(self.plugin_name, "cancelled")
                return

            if 'dependencies' in self.plugin_data:
                self.progress.emit(self.plugin_name, 0)
                self.download_dependencies(self.plugin_data['dependencies'])
                add_to_path(LIB_DIR)

            version_file_path = os.path.join(target_plugin_dir, 'version')
            with open(version_file_path, 'w') as f:
                f.write(self.plugin_data['version'])

            if self.plugin_data.get('launch') and self.plugin_data.get('launch_file'):
                launch_file_path = os.path.join(target_plugin_dir, self.plugin_data['launch_file'])
                if os.path.exists(launch_file_path):
                    try:
                        os.startfile(launch_file_path)
                    except Exception as e:
                        print(f"Failed to auto-launch {launch_file_path}: {e}")

            add_nss_import(self.plugin_data, os.path.join(PROJECT_ROOT, 'shell.nss'))
            self.finished.emit(self.plugin_name, "installed")
        except Exception as e:
            self.error.emit(self.plugin_name, "failed", str(e))

    def download_files(self, target_plugin_dir):
        if not os.path.exists(target_plugin_dir):
            os.makedirs(target_plugin_dir)

        total_files = len(self.files_to_download)
        for i, file_info in enumerate(self.files_to_download):
            if self._is_cancelled:
                return

            relative_path = file_info['path']
            local_path = os.path.join(target_plugin_dir, relative_path)
            
            # Check if file needs update
            local_sha = git_blob_sha(local_path)
            if local_sha == file_info.get('sha'):
                print(f"Skipping {relative_path} (identical)")
                continue

            os.makedirs(os.path.dirname(local_path), exist_ok=True)

            try:
                response = session.get(file_info['url'], timeout=REQUEST_TIMEOUT)
                response.raise_for_status()
                with open(local_path, 'wb') as f:
                    f.write(response.content)
            except Exception as e:
                raise e

            progress_val = int(((i + 1) / total_files) * 100)
            self.progress.emit(self.plugin_name, progress_val)

        # Cleanup files that are no longer in the repo
        remote_files = {f['path'] for f in self.files_to_download}
        for root, dirs, files in os.walk(target_plugin_dir):
            for file in files:
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, target_plugin_dir).replace(os.sep, '/')
                if rel_path not in remote_files and file != 'version':
                    try:
                        os.remove(full_path)
                        print(f"Removed stale file: {rel_path}")
                    except:
                        pass

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
                response = session.get(f"https://api.github.com/repos/{_GITHUB_REPO}/releases", timeout=REQUEST_TIMEOUT)
                response.raise_for_status()
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

                dep_response = session.get(asset_url, stream=True, timeout=REQUEST_TIMEOUT)
                dep_response.raise_for_status()

                os.makedirs(LIB_DIR, exist_ok=True)
                with open(dep_path, 'wb') as f:
                    for chunk in dep_response.iter_content(chunk_size=8192):
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
            details_url = f"https://raw.githubusercontent.com/iMAboud/iMA-Menu-Plugins/main/{self.plugin_name}/details.md"
            response = session.get(details_url, timeout=REQUEST_TIMEOUT)

            if response.status_code == 200:
                markdown_content = response.text
                html_content = self.markdown_to_html_with_images(markdown_content)
                
                temp_html_path = os.path.join(CACHE_DIR, f"{self.plugin_name}_details.html")
                with open(temp_html_path, 'w', encoding='utf-8') as f:
                    f.write(html_content)

                self.finished.emit(html_content)
            else:
                self.finished.emit(f"No details found for {self.plugin_name}.")
        except Exception as e:
            self.error.emit(str(e))

    def markdown_to_html_with_images(self, markdown_content):
        html_content = markdown.markdown(markdown_content)

        def replace_markdown_img(match):
            alt_text = match.group(1)
            src_url = match.group(2)
            if src_url and not src_url.startswith('data:'):
                try:
                    response = session.get(src_url, timeout=REQUEST_TIMEOUT)
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
                    response = session.get(src_url, timeout=REQUEST_TIMEOUT)
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
            body {{ color: white; background-color: transparent; overflow-x: hidden; margin: 0; padding: 0; font-family: sans-serif; }}
            p {{ margin-bottom: 1em; }}
            img {{ max-width: 100%; height: auto; display: block; margin: 0 auto; }}
            h1, h2, h3, h4, h5, h6 {{ margin-top: 1em; margin-bottom: 0.5em; }}
            ul, ol {{ margin-bottom: 1em; padding-left: 20px; }}
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
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
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
        icon_pixmap = QPixmap(os.path.join(ICONS_CACHE_DIR, f"{self.plugin_data['name']}.png"))
        if icon_pixmap.isNull():
            icon_pixmap = QPixmap(DEFAULT_ICON_PATH)
        icon_label.setPixmap(icon_pixmap)
        title_layout.addWidget(icon_label)

        title_label = QLabel(self.plugin_data['name'])
        title_label.setFont(QFont('Segoe UI Variable Display', 18, QFont.Bold))
        title_layout.addWidget(title_label)
        title_layout.addStretch()

        close_button = QPushButton()
        close_button.setIcon(QIcon(resource_path('icons/x.png')))
        close_button.setIconSize(QSize(24, 24))
        close_button.setFixedSize(30, 30)
        close_button.setObjectName("iconButton")
        close_button.clicked.connect(self.close)
        title_layout.addWidget(close_button)
        self.layout.addWidget(title_bar)

        description_label = QLabel(self.plugin_data.get('description', 'No description available.'))
        description_label.setWordWrap(True)
        self.layout.addWidget(description_label)

        self.details_browser = QTextBrowser()
        self.details_browser.setOpenExternalLinks(True)
        self.details_browser.setObjectName("detailsBrowser")
        self.details_browser.setMinimumHeight(200)
        self.details_browser.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.details_browser.setWordWrapMode(QTextOption.WordWrap)
        self.layout.addWidget(self.details_browser)

        self.action_button = QPushButton("Install")
        self.action_button.setObjectName("installButton")
        font = self.action_button.font()
        font.setBold(True)
        self.action_button.setFont(font)
        self.layout.addWidget(self.action_button, alignment=Qt.AlignRight)

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(25)
        shadow.setColor(QColor(0, 0, 0, 180))
        shadow.setOffset(5, 5)
        self.setGraphicsEffect(shadow)

    def set_details_content(self, content):
        self.details_browser.setHtml(content)

    def closeEvent(self, event):
        if self.start_geom and not self._is_closing:
            event.ignore()
            self._is_closing = True

            self.close_animation = QPropertyAnimation(self, b"geometry")
            self.close_animation.setDuration(400)
            self.close_animation.setStartValue(self.geometry())
            self.close_animation.setEndValue(self.start_geom)
            self.close_animation.setEasingCurve(QEasingCurve.OutBack)

            self.close_opacity_animation = QPropertyAnimation(self, b"windowOpacity")
            self.close_opacity_animation.setDuration(300)
            self.close_opacity_animation.setStartValue(1.0)
            self.close_opacity_animation.setEndValue(0.0)
            self.close_opacity_animation.setEasingCurve(QEasingCurve.OutBack)
            self.close_opacity_animation.finished.connect(self.close_actual)

            self.close_animation.start()
            self.close_opacity_animation.start()
        else:
            super().closeEvent(event)

    def close_actual(self):
        super().close()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        painter.setBrush(QColor("#18181a"))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(self.rect(), 15, 15)

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

    def _on_plugins_fetched(self, plugins):
        self.all_plugins_data = {p['name']: p for p in plugins}
        self.plugins_fetched.emit(plugins)

    def load_icon(self, plugin):
        plugin_name = plugin['name']
        local_icon_path = os.path.join(ICONS_CACHE_DIR, f"{plugin_name}.png")

        if os.path.exists(local_icon_path):
            pixmap = QPixmap(local_icon_path)
            if not pixmap.isNull():
                self.icon_loaded.emit(plugin_name, pixmap)
                return
        
        if plugin.get('icon_url'):
            thread = QThread(self)
            worker = IconDownloadWorker(plugin_name, plugin['icon_url'], local_icon_path)
            worker.moveToThread(thread)

            worker.finished.connect(self.icon_loaded.emit)
            worker.error.connect(lambda e: self.icon_loaded.emit(plugin_name, QPixmap()))
            thread.started.connect(worker.run)
            worker.finished.connect(thread.quit)
            worker.error.connect(thread.quit)
            worker.finished.connect(worker.deleteLater)
            worker.error.connect(worker.deleteLater)
            thread.finished.connect(lambda: self.cleanup_thread(f"icon_{plugin_name}"))
            
            thread.start()
            self.active_threads[f"icon_{plugin_name}"] = (thread, worker)
        else:
            self.icon_loaded.emit(plugin_name, QPixmap(DEFAULT_ICON_PATH))

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
            
        self.installation_queue.append(self.all_plugins_data[plugin_name])
        
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
        worker.error.connect(self.operation_error.emit)
        worker.finished.connect(thread.quit)
        worker.error.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        worker.error.connect(worker.deleteLater)
        thread.finished.connect(lambda: self.cleanup_thread(self.current_installing_plugin))
        
        thread.start()

    def _on_operation_finished(self, plugin_name, status):
        if plugin_name == self.current_installing_plugin:
            self.cleanup_thread(plugin_name)
            self.current_installing_plugin = None
            self.process_next_in_queue()
        self.operation_finished.emit(plugin_name, status)

    def cancel_operation(self, plugin_name):
        if self.current_installing_plugin == plugin_name and plugin_name in self.active_threads:
            thread, worker = self.active_threads[plugin_name]
            worker.cancel()
        else:
            self.installation_queue = deque([p for p in self.installation_queue if p['name'] != plugin_name])
            self.operation_finished.emit(plugin_name, "cancelled_from_queue")

    def uninstall_plugin(self, plugin_name):
        try:
            plugin_data = self.all_plugins_data.get(plugin_name)
            if not plugin_data:
                self.operation_error.emit(plugin_name, "failed", "Plugin data not found.")
                return

            target_plugin_dir = get_plugin_install_path(plugin_data)
            if os.path.exists(target_plugin_dir):
                terminate_plugin_processes(target_plugin_dir)
                shutil.rmtree(target_plugin_dir)
            remove_nss_import(plugin_data, os.path.join(PROJECT_ROOT, 'shell.nss'))
            self.operation_finished.emit(plugin_name, "uninstalled")
        except Exception as e:
            self.operation_error.emit(plugin_name, "failed", str(e))

    def get_local_plugin_version(self, plugin_name):
        plugin_data = self.all_plugins_data.get(plugin_name)
        if not plugin_data:
            return None
        install_path = get_plugin_install_path(plugin_data)
        version_file = os.path.join(install_path, 'version')
        if os.path.exists(version_file):
            with open(version_file, 'r') as f:
                return f.read().strip()
        return None

    def cleanup_thread(self, key):
        if key in self.active_threads:
            thread, worker = self.active_threads.pop(key)
            thread.quit()

    def stop_all_threads(self):
        for key, (thread, worker) in list(self.active_threads.items()):
            if hasattr(worker, 'cancel'):
                worker.cancel()
            thread.quit()
            if not thread.wait(2000):
                thread.terminate()

class PluginManager(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("iMA Plugin Manager")
        self.setMinimumSize(600, 400)
        self.resize(950, 620)
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint | Qt.WindowSystemMenuHint | Qt.WindowMinimizeButtonHint | Qt.WindowMaximizeButtonHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # Re-enable rounding for modern look
        try:
            DWMWCP_ROUND = 2
            DWMWA_WINDOW_CORNER_PREFERENCE = 33
            ctypes.windll.dwmapi.DwmSetWindowAttribute(int(self.winId()), DWMWA_WINDOW_CORNER_PREFERENCE, ctypes.byref(ctypes.c_int(DWMWCP_ROUND)), 4)
        except Exception:
            pass

        # Force the window to have a native resizing frame in the background
        hwnd = int(self.winId())
        style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
        win32gui.SetWindowLong(hwnd, win32con.GWL_STYLE, style | win32con.WS_THICKFRAME | win32con.WS_CAPTION)

        self.setWindowIcon(QIcon(resource_path('icons/icon.ico')))

        # Re-enabling Acrylic with safe check
        if os.name == 'nt':
            try:
                set_window_effect(int(self.winId()), effect="acrylic")
            except Exception:
                pass

        self.setup_cache_dirs()
        
        self.settings_manager = SettingsManager()
        self.plugin_logic = PluginLogic()
        self.sync_manager = CloudSyncManager(PROJECT_ROOT)
        self.sync_manager.auth_finished.connect(self.on_sync_auth_finished)
        self.sync_manager.sync_progress.connect(self.on_sync_progress)
        self.sync_manager.sync_finished.connect(self.on_sync_finished)
        
        self.error_monitor = ShellLogMonitor(PROJECT_ROOT, self)
        self.error_monitor.manual_fix_required.connect(self._on_manual_fix_required)
        self.error_monitor.start()
        
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

        self.modify_page = ModifyWidget(os.path.join(PROJECT_ROOT, 'imports', 'modify.nss'), os.path.join(PROJECT_ROOT, 'shell.nss'), PROJECT_ROOT)
        self.tint_backups = {}
        self._active_tint_threads = []
        self.stacked_widget.addWidget(self.modify_page)

        self.theme_page = QWidget()
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
        self.modify_page.reload_requested.connect(self.reload_shell)
        if hasattr(self.modify_page, 'rules_saved'):
            self.modify_page.rules_saved.connect(lambda: self.update_snapshot(os.path.join(PROJECT_ROOT, 'imports', 'modify.nss')))

        self.theme_tab_widget.addTab(self.theme_switcher_page, get_mdl2_icon(0xE790, 36), "Themes")
        self.theme_tab_widget.addTab(self.theme_editor_page, get_mdl2_icon(0xE104, 36), "Editor")

        self.stacked_widget.addWidget(self.theme_page)

        self.settings_scroll = QScrollArea()
        self.settings_scroll.setWidgetResizable(True)
        self.settings_scroll.setStyleSheet("background: transparent; border: none;")
        self.settings_page = QWidget()
        self.settings_scroll.setWidget(self.settings_page)
        self.setup_settings_page()
        self._update_widgets_autosave()
        self.stacked_widget.addWidget(self.settings_scroll)


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
        # Delayed heavy tasks to keep startup instant
        QTimer.singleShot(100, self._setup_file_watcher)
        QTimer.singleShot(200, self.load_plugins)
        QTimer.singleShot(1000, self._take_global_nss_snapshot)

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
            os.path.abspath(os.path.join(PROJECT_ROOT, 'theme'))
        ]
        
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
        if self._is_internal_change: return
        self._pending_sync_paths.add(path)
        self.file_sync_timer.start(300) # 300ms debounce

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
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 160))
        shadow.setOffset(2, 2)
        widget.setGraphicsEffect(shadow)

    def create_title_bar(self):
        title_bar = QWidget()
        title_bar.setFixedHeight(42)
        title_layout = QHBoxLayout(title_bar)

        app_icon_label = QLabel()
        app_icon_pixmap = QPixmap(resource_path('icons/icon.ico'))
        app_icon_label.setPixmap(app_icon_pixmap.scaled(24, 24, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        title_layout.addWidget(app_icon_label)

        title_label = QLabel("iMA Plugin Manager")
        title_label.setFont(QFont('Segoe UI Variable Display', 16, QFont.Bold))
        title_label.setObjectName("titleLabel")
        self._apply_shadow_effect(title_label)

        open_folder_button = QPushButton()
        open_folder_button.setIcon(QIcon(resource_path('icons/open.png')))
        open_folder_button.setIconSize(QSize(24, 24))
        open_folder_button.setFixedSize(30, 30)
        open_folder_button.setObjectName("iconButton")
        open_folder_button.clicked.connect(self.open_root_folder)
        self._apply_shadow_effect(open_folder_button)

        self.refresh_button = QPushButton()
        self.refresh_button.setIcon(QIcon(resource_path('icons/refresh.png')))
        self.refresh_button.setIconSize(QSize(24, 24))
        self.refresh_button.setFixedSize(30, 30)
        self.refresh_button.setCursor(Qt.PointingHandCursor)
        self.refresh_button.setObjectName("iconButton")
        self.refresh_button.clicked.connect(self.refresh_plugins)
        self._apply_shadow_effect(self.refresh_button)

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
        # Use timer to debounce resize and prevent layout flickering
        self.resize_timer.start(50)

    def recalculate_plugin_grid(self):
        if not hasattr(self, 'grid_layout') or not self.plugin_cards:
            return
            
        available_width = self.scroll_area.width() - 40 
        card_width = 180 + 20 
        cols = max(1, available_width // card_width)
        
        # Instead of clearing everything, just reposition what we have
        for i, (plugin_name, card) in enumerate(self.plugin_cards.items()):
            row, col = i // cols, i % cols
            # Only move if the position changed
            if self.grid_layout.indexOf(card) != -1:
                self.grid_layout.removeWidget(card)
            self.grid_layout.addWidget(card, row, col)
            card.show()
        
        # Debounce icon visibility check after repositioning
        QTimer.singleShot(100, self.check_visible_cards)

    def create_side_panel(self):
        side_panel = QFrame()
        side_panel.setObjectName("sidePanel")
        side_panel.setStyleSheet("#sidePanel { background-color: #121212; border-right: 1px solid #2a2a30; border-top-left-radius: 15px; border-bottom-left-radius: 15px; }")
        side_panel.setFixedWidth(80)
        side_panel_layout = QVBoxLayout(side_panel)
        side_panel_layout.setContentsMargins(10, 10, 10, 10)
        side_panel_layout.setSpacing(20)
        side_panel_layout.setAlignment(Qt.AlignTop)

        plugins_button = QPushButton()
        plugins_button.setObjectName("sideButton")
        plugins_button.setIcon(QIcon(resource_path('icons/plugins.png')))
        plugins_button.setIconSize(QSize(40, 40))
        plugins_button.setFixedSize(60, 60)
        plugins_button.setCursor(Qt.PointingHandCursor)
        plugins_button.clicked.connect(lambda: self.stacked_widget.setCurrentWidget(self.plugins_page))
        side_panel_layout.addWidget(plugins_button)
        self._apply_shadow_effect(plugins_button)

        modify_button = QPushButton()
        modify_button.setObjectName("sideButton")
        modify_button.setIcon(QIcon(resource_path('icons/modify.png')))
        modify_button.setIconSize(QSize(40, 40))
        modify_button.setFixedSize(60, 60)
        modify_button.setCursor(Qt.PointingHandCursor)
        modify_button.clicked.connect(lambda: self.stacked_widget.setCurrentWidget(self.modify_page))
        side_panel_layout.addWidget(modify_button)
        self._apply_shadow_effect(modify_button)

        theme_button = QPushButton()
        theme_button.setObjectName("sideButton")
        theme_button.setIcon(QIcon(resource_path('icons/theme.png')))
        theme_button.setIconSize(QSize(40, 40))
        theme_button.setFixedSize(60, 60)
        theme_button.setCursor(Qt.PointingHandCursor)
        theme_button.clicked.connect(lambda: self.stacked_widget.setCurrentWidget(self.theme_page))
        side_panel_layout.addWidget(theme_button)
        self._apply_shadow_effect(theme_button)

        side_panel_layout.addStretch()

        settings_button = QPushButton()
        settings_button.setObjectName("sideButton")
        settings_button.setIcon(QIcon(resource_path('icons/settings.png')))
        settings_button.setIconSize(QSize(40, 40))
        settings_button.setFixedSize(60, 60)
        settings_button.setCursor(Qt.PointingHandCursor)
        settings_button.clicked.connect(lambda: self.stacked_widget.setCurrentWidget(self.settings_scroll))
        side_panel_layout.addWidget(settings_button)
        self._apply_shadow_effect(settings_button)

        return side_panel

    def open_root_folder(self):
        try:
            os.startfile(PROJECT_ROOT)
        except Exception as e:
            print(f"Error opening root folder: {e}")

    def load_plugins(self):
        if os.path.exists(PLUGINS_CACHE_FILE):
            try:
                with open(PLUGINS_CACHE_FILE, 'r') as f: plugins = json.load(f)
                if not isinstance(plugins, list): raise ValueError("Invalid cache format")
                self.plugin_logic.all_plugins_data = {p['name']: p for p in plugins}
                self.on_plugins_fetched(plugins)
                return
            except (json.JSONDecodeError, IOError, ValueError) as e:
                print(f"Error loading cache: {e}. Fetching from remote.")
                if os.path.exists(PLUGINS_CACHE_FILE): os.remove(PLUGINS_CACHE_FILE)
        
        self.fetch_plugins_list()

    def fetch_plugins_list(self):
        self.loading_label.show()
        self.scroll_area.hide()
        self.plugin_logic.fetch_plugins_list()

    def on_plugins_fetched(self, plugins):
        self.all_plugins_data = {p['name']: p for p in plugins}

        # Create cards for plugins
        for plugin in plugins:
            if plugin['name'] not in self.plugin_cards:
                self.create_plugin_card(plugin)

        # Arrange them
        self.loading_label.hide()
        self.scroll_area.show()
        self.recalculate_plugin_grid()
        
        # Trigger icon loading for the visible cards
        QTimer.singleShot(100, self.check_visible_cards)

    def on_fetch_error(self, error_message):
        self.loading_label.setText(f"Error: {error_message}")

    def refresh_plugins(self):
        if self.plugin_logic.current_installing_plugin: return
        if os.path.exists(PLUGINS_CACHE_FILE): os.remove(PLUGINS_CACHE_FILE)
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

        self._apply_shadow_effect(title)

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
        icon_layout.addWidget(icon)
        layout.addWidget(icon_container, alignment=Qt.AlignCenter)

        self._apply_shadow_effect(icon_container)

        description = QLabel(plugin.get('description', 'No description available.'))
        description.setWordWrap(True)
        description.setAlignment(Qt.AlignCenter)
        description.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        layout.addWidget(description)

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(10)
        shadow.setColor(QColor(0, 0, 0, 160))
        shadow.setOffset(2, 2)
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

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(25)
        shadow.setColor(QColor(0, 0, 0, 180))
        shadow.setOffset(5, 5)
        action_button.setGraphicsEffect(shadow)

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
        if not plugin_data: return

        start_geom = card.geometry()
        start_geom.moveTopLeft(card.mapTo(self, card.rect().topLeft()))

        self.details_popup = DetailsPopup(plugin_data, self, start_geom=start_geom)
        self.details_popup.show()

        end_geom = self.rect().adjusted(50, 50, -50, -50)

        self.details_popup.setGeometry(start_geom)
        self.animation = QPropertyAnimation(self.details_popup, b"geometry")
        self.animation.setDuration(300)
        self.animation.setStartValue(start_geom)
        self.animation.setEndValue(end_geom)
        self.animation.setEasingCurve(QEasingCurve.OutBack)
        self.animation.start(QPropertyAnimation.DeleteWhenStopped)

        self.opacity_animation = QPropertyAnimation(self.details_popup, b"windowOpacity")
        self.opacity_animation.setDuration(300)
        self.opacity_animation.setStartValue(0.0)
        self.opacity_animation.setEndValue(1.0)
        self.opacity_animation.setEasingCurve(QEasingCurve.OutBack)
        self.opacity_animation.start(QPropertyAnimation.DeleteWhenStopped)

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
        local_version = self.get_local_plugin_version(plugin_name)
        if local_version:
            self.uninstall_plugin(plugin_name)
        else:
            self.add_to_installation_queue(plugin_name)
        self.update_popup_button(plugin_name)

    def update_popup_button(self, plugin_name):
        if not self.details_popup: return
        local_version = self.get_local_plugin_version(plugin_name)
        remote_version = self.all_plugins_data.get(plugin_name, {}).get('version')

        if local_version:
            if remote_version and local_version != remote_version:
                self.details_popup.action_button.setText("Update")
                self.details_popup.action_button.setObjectName("updateButton")
            else:
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
                    plugin_data = self.all_plugins_data.get(plugin_name)
                    if plugin_data:
                        self.load_icon(plugin_data)
                        self.icons_loaded.add(plugin_name)

    def get_local_plugin_version(self, plugin_name):
        return self.plugin_logic.get_local_plugin_version(plugin_name)

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
        local_version = self.get_local_plugin_version(plugin_name)
        remote_version = self.all_plugins_data.get(plugin_name, {}).get('version')

        is_partially_installed = os.path.exists(get_plugin_install_path(self.all_plugins_data.get(plugin_name, {}))) and not self.get_local_plugin_version(plugin_name)
        
        show_updates = self.settings_manager.get('auto_check_updates')
        has_update = show_updates and remote_version and local_version and remote_version != local_version
        
        # Auto Update Logic
        if has_update and self.settings_manager.get('auto_update') and not is_queued and not is_installing:
             self.add_to_installation_queue(plugin_name)
             return
        
        if plugin_name in self.plugin_progress_bars:
            self.plugin_progress_bars[plugin_name].setVisible(is_installing)

        if is_installing:
            action_button.setText("Cancel")
            action_button.setObjectName("textButton")
            action_button.setEnabled(True)
            action_button.clicked.connect(lambda: self.cancel_operation(plugin_name))
        elif is_queued:
            action_button.setText("Queued")
            action_button.setObjectName("textButton")
            action_button.setEnabled(True)
            action_button.clicked.connect(lambda: self.cancel_operation(plugin_name))
        elif local_version or is_partially_installed:
            action_button.setText("Uninstall")
            action_button.setObjectName("uninstallButton")
            action_button.setEnabled(True)
            action_button.clicked.connect(lambda: self.uninstall_plugin(plugin_name))
            
            if show_updates and remote_version and local_version != remote_version:
                update_button = QPushButton("Update")
                update_button.setObjectName("updateButton")
                update_button.setCursor(Qt.PointingHandCursor)
                update_button.clicked.connect(lambda: self.add_to_installation_queue(plugin_name))
                action_layout.addWidget(update_button)
                self.plugin_update_buttons[plugin_name] = update_button
        else:
            action_button.setText("Install")
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
        else:
            msgBox = CustomMessageBox(self)
            msgBox.setText(f"Error for {plugin_name}")
            msgBox.setInformativeText(error_message)
            msgBox.exec_()

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
                
                try:
                    rect = win32gui.GetWindowRect(int(self.winId()))
                    lx = x - rect[0]
                    ly = y - rect[1]
                    w = rect[2] - rect[0]
                    h = rect[3] - rect[1]
                except Exception:
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

                return True, win32con.HTCLIENT

            elif msg.message == win32con.WM_NCCALCSIZE:
                return True, 0
        return super().nativeEvent(event_type, message)







    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor(30, 32, 48, 150))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(self.rect(), 15, 15)

    def closeEvent(self, event):
        self._is_shutting_down = True
        if self.theme_editor_page.is_dirty or self.theme_switcher_page.is_dirty or self.modify_page.is_dirty:
            from utils import UnsavedChangesDialog
            dialog = UnsavedChangesDialog(self)
            res = dialog.exec_()
            
            if res == 1: # Yes
                self.theme_editor_page.save_theme()
                self.theme_switcher_page.save_theme()
                self.commit_tinted_icons()
                if self.modify_page.is_dirty:
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

    def check_app_update(self, manual=False):
        import time
        if not manual:
            last_check = 0
            try:
                last_check = float(self.settings_manager.get('last_update_check') or 0)
            except (ValueError, TypeError):
                last_check = 0
            if last_check == 0:
                try:
                    marker = os.path.join(TEMP_DIR, 'ima_last_update_check.txt')
                    if os.path.exists(marker):
                        last_check = float(open(marker).read().strip())
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

        self.update_thread = QThread()
        self.update_worker = UpdateWorker()
        self.update_worker.moveToThread(self.update_thread)
        self.update_thread.started.connect(self.update_worker.check_for_updates)
        self.update_worker.check_finished.connect(lambda h, v, u: self.on_check_finished(h, v, u, manual))
        self.update_worker.check_finished.connect(self.update_thread.quit)
        self.update_thread.finished.connect(self.update_thread.deleteLater)
        self.update_thread.start()
    def on_check_finished(self, has_update, latest_version, download_url, manual):
        if manual:
            self.update_btn.setText('Check for Update'); self.update_btn.setEnabled(True)

        if has_update and download_url:
            just_installed = os.path.join(TEMP_DIR, 'ima_just_updated.txt')
            if os.path.exists(just_installed):
                try:
                    installed_ver = open(just_installed).read().strip()
                    if installed_ver == latest_version:
                        os.remove(just_installed)
                        return
                except Exception:
                    pass

            self._update_dialog_active = True
            self.latest_app_version = latest_version
            self.ver_label.setText(f"Current: {VERSION} | <span style='color: #dc143c;'>Latest: {latest_version}</span>")
            msg = ModernDialog(self, 'Update Available', f"A new version of iMA Menu Launcher is available: <b>V{latest_version}</b><br><br>Would you like to download and install it now?")
            msg.add_button('Update Now', 'installButton', lambda: msg.done(1))
            msg.add_button('Later', 'sideButton', msg.reject)
            res = msg.exec_()
            self._update_dialog_active = False
            if res == 1:
                self.start_app_download(download_url)
        elif manual:
            m = ModernDialog(self, 'Up to Date', 'You are running the latest version of iMA Menu Launcher.')
            m.add_button('OK', 'installButton', m.accept); m.exec_()

    def start_app_download(self, url):
        self.dl_msg = ModernDialog(self, "Downloading Update", "Please wait while the new version is being downloaded...")
        
        # Enhanced progress container
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
        
        self.dl_thread = QThread()
        self.dl_worker = UpdateWorker()
        self.dl_worker.moveToThread(self.dl_thread)
        self.dl_thread.started.connect(lambda: self.dl_worker.download_update(url))
        self.dl_worker.download_progress.connect(self._update_dl_progress)
        self.dl_worker.download_finished.connect(self.on_download_finished)
        self.dl_worker.download_finished.connect(self.dl_thread.quit)
        self.dl_thread.finished.connect(self.dl_thread.deleteLater)
        self.dl_thread.start()
        self.dl_msg.exec_()

    def _update_dl_progress(self, val):
        self.dl_bar.setValue(val)
        self.percent_label.setText(f"{val}%")

    def on_download_finished(self, success, result):
        self.dl_msg.accept()
        if success:
            self.apply_app_update(result)
        else:
            m = ModernDialog(self, "Download Failed", f"An error occurred while downloading the update:<br>{result}"); m.add_button("OK", "installButton", m.accept); m.exec_()

    def apply_app_update(self, new_exe_path):
        m = ModernDialog(self, 'Ready to Update', 'The update has been downloaded. The application will now close and restart to complete the installation.')
        m.add_button('Restart Now', 'installButton', m.accept)
        m.add_button('Later', 'sideButton', m.reject)
        if m.exec_() != 1:
            return

        current_exe = sys.executable if getattr(sys, 'frozen', False) else os.path.abspath(sys.argv[0])
        new_version = getattr(self, 'latest_app_version', VERSION)
        needs_elevation = not _can_write_to_dir(APP_BASE_PATH)

        version_file_primary = VERSION_FILE.replace('\\', '\\\\')
        version_file_fallback = VERSION_FILE_FALLBACK.replace('\\', '\\\\')
        just_updated_marker = os.path.join(TEMP_DIR, 'ima_just_updated.txt').replace('\\', '\\\\')
        batch_dir = TEMP_DIR if needs_elevation else APP_BASE_PATH

        try:
            os.makedirs(batch_dir, exist_ok=True)
        except Exception:
            batch_dir = TEMP_DIR

        batch_path = os.path.join(batch_dir, 'ima_apply_update.bat')

        batch_content = f"""@echo off
setlocal enabledelayedexpansion
set "EXE_PATH={current_exe}"
set "NEW_EXE={new_exe_path}"
set "VERSION_FILE={VERSION_FILE}"
set "VERSION_FILE2={VERSION_FILE_FALLBACK}"
set "MARKER={os.path.join(TEMP_DIR, 'ima_just_updated.txt')}"
set "NEW_VERSION={new_version}"

if not exist "%NEW_EXE%" (
    echo ERROR: Update file not found.
    pause
    exit /b 1
)

echo Waiting for launcher to close...
set /a count=0
:wait
tasklist /FI "IMAGENAME Launcher.exe" 2>NUL | find /I "Launcher.exe" >NUL
if %ERRORLEVEL%==0 (
    set /a count+=1
    if !count! GTR 15 (
        taskkill /F /IM "Launcher.exe" >nul 2>&1
    )
    timeout /t 1 /nobreak >nul
    goto wait
)

echo Replacing launcher...
set /a retry=0
:retry_del
del /f /q "%EXE_PATH%" >nul 2>&1
if exist "%EXE_PATH%" (
    set /a retry+=1
    if !retry! LSS 8 (
        timeout /t 1 /nobreak >nul
        goto retry_del
    )
    echo ERROR: Could not remove old launcher.
    pause
    exit /b 1
)

move /y "%NEW_EXE%" "%EXE_PATH%" >nul 2>&1
if not exist "%EXE_PATH%" (
    echo ERROR: Move failed.
    pause
    exit /b 1
)

echo Updating version...
(echo {new_version})>"%VERSION_FILE%" 2>nul
(echo {new_version})>"%VERSION_FILE2%" 2>nul
(echo {new_version})>"%MARKER%" 2>nul

echo Restarting...
start "" "%EXE_PATH%"
timeout /t 2 /nobreak >nul
del /f /q "%~f0" >nul 2>&1
exit
"""

        try:
            with open(batch_path, 'w', encoding='utf-8') as f:
                f.write(batch_content)
        except Exception as e:
            m2 = ModernDialog(self, 'Update Error', f'Could not write update script:<br>{e}')
            m2.add_button('OK', 'installButton', m2.accept); m2.exec_()
            return

        try:
            if needs_elevation:
                import ctypes
                ctypes.windll.shell32.ShellExecuteW(
                    None, 'runas', 'cmd.exe',
                    f'/c "{batch_path}"',
                    None, 1
                )
            else:
                subprocess.Popen(
                    ['cmd.exe', '/c', batch_path],
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
            sys.exit(0)
        except Exception as e:
            m2 = ModernDialog(self, 'Update Error', f'Could not launch update script:<br>{e}')
            m2.add_button('OK', 'installButton', m2.accept); m2.exec_()


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
        # Enable High DPI awareness
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass
            
        myappid = 'iMAboud.iMAMenu.Launcher.1'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    
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
    sys.exit(app.exec_())
