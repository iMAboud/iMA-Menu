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
import winreg

def _sync_local_runtime():
    """If running in frozen onefile mode, sync extracted files to local _internal folder for fast caching."""
    if not getattr(sys, 'frozen', False):
        return
    try:
        meipass = getattr(sys, '_MEIPASS', None)
        if not meipass or not os.path.exists(meipass):
            return
        
        exe_dir = os.path.dirname(os.path.abspath(sys.executable))
        internal_dir = os.path.join(exe_dir, '_internal')
        
        # Check if local _internal is missing or outdated
        stamp_file = os.path.join(internal_dir, '.version')
        should_sync = False
        if not os.path.exists(internal_dir) or not os.path.exists(stamp_file):
            should_sync = True
        else:
            try:
                with open(stamp_file, 'r', encoding='utf-8') as sf:
                    cached_v = sf.read().strip()
                if cached_v != VERSION:
                    should_sync = True
            except Exception:
                should_sync = True
                
        if should_sync:
            os.makedirs(internal_dir, exist_ok=True)
            # Copy runtime libraries in background or non-blocking to populate _internal
            def _copy_worker():
                try:
                    for item in os.listdir(meipass):
                        s = os.path.join(meipass, item)
                        d = os.path.join(internal_dir, item)
                        if os.path.isdir(s):
                            if not os.path.exists(d):
                                shutil.copytree(s, d, dirs_exist_ok=True)
                        else:
                            if not os.path.exists(d) or os.path.getsize(s) != os.path.getsize(d):
                                shutil.copy2(s, d)
                    with open(stamp_file, 'w', encoding='utf-8') as sf:
                        sf.write(VERSION)
                except Exception:
                    pass
            import threading
            threading.Thread(target=_copy_worker, daemon=True).start()
    except Exception:
        pass

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
import threading
import json
import shutil
import re
import subprocess
import hashlib
import gc
from collections import deque, OrderedDict
import ctypes
from ctypes import wintypes
from PyQt5.QtWidgets import (QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QGridLayout,
                             QScrollArea, QGraphicsDropShadowEffect, QGraphicsOpacityEffect, QProgressBar, QTextBrowser, QStackedWidget, 
                             QTabWidget, QDialog, QDialogButtonBox, QLineEdit, QScrollBar, QAbstractSlider, QComboBox, 
                             QTabBar, QSizePolicy, QFrame, QCheckBox, QFileDialog, QInputDialog, QShortcut, QButtonGroup)
from PyQt5.QtGui import QColor, QPixmap, QFont, QPainter, QPainterPath, QPen, QTextOption, QIcon, QCursor, QKeySequence, QLinearGradient, QRegion
from PyQt5.QtCore import (Qt, pyqtSignal, QObject, QThread, QTimer, QPropertyAnimation, QEasingCurve, 
                             QSize, QEvent, QPoint, QRect, QRectF, pyqtProperty, QFileSystemWatcher, QParallelAnimationGroup,
                             QAbstractNativeEventFilter)
try: from PyQt5 import QtSvg
except ImportError: QtSvg = None

SINGLE_INSTANCE_MUTEX_NAME = "Local\\iMA_Menu_Launcher_SingleInstance_Mutex"
SINGLE_INSTANCE_MSG_NAME = "iMA_Menu_Launcher_RestoreAndFocus"
SINGLE_INSTANCE_MSG_ID = ctypes.windll.user32.RegisterWindowMessageW(SINGLE_INSTANCE_MSG_NAME) if os.name == 'nt' else 0
_single_instance_mutex = None

class SingleInstanceNativeFilter(QAbstractNativeEventFilter):
    def __init__(self, target_widget, msg_id):
        super().__init__()
        self.target_widget = target_widget
        self.msg_id = msg_id

    def nativeEventFilter(self, eventType, message):
        if eventType in (b'windows_generic_MSG', 'windows_generic_MSG'):
            try:
                msg = wintypes.MSG.from_address(int(message))
                if self.msg_id and msg.message == self.msg_id:
                    if self.target_widget:
                        self.target_widget.bring_to_focus()
                    return True, 0
            except Exception:
                pass
        return False, 0

from utils import (resource_path, safe_file_write, set_window_effect, UnsavedChangesDialog, 
                   trigger_shell_reload, terminate_plugin_processes, get_mdl2_icon, global_undo_stack,
                   ModernDialog, ModernSwitch, PillProgressBar, FlowLayout, normalize_path,
                   make_circular_pixmap, make_initial_avatar_pixmap, AccountProfileDialog,
                   CapsuleActionButton, PillTabButton, PillPushButton)
from plugin_registry import PluginRegistry, git_blob_sha, version_cmp, atomic_json_write, safe_json_read, delete_to_recycle_bin
from plugin_workers import (
    FetchPluginsThread, IconDownloadWorker, InstallationWorker,
    DetailsFetchWorker, ClickableWidget, DetailsPopup, init_plugin_workers,
    find_riot_client_path, fetch_ima_switcher_release
)

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
APP_REPO = "iMAboud/iMA-Menu-Plugins"
_GITHUB_REPO = "iMAboud/iMA-Menu-Plugins"
GITHUB_PLUGINS_JSON_URL = f"https://raw.githubusercontent.com/{_GITHUB_REPO}/main/plugins.json"
GITHUB_API_BASE_URL = f"https://api.github.com/repos/{_GITHUB_REPO}"
GITHUB_RELEASES_API_URL = f"{GITHUB_API_BASE_URL}/releases/latest"
APP_LATEST_RELEASE_URL = f"https://api.github.com/repos/{APP_REPO}/releases/latest"
APP_RELEASES_API_URL = f"https://api.github.com/repos/{APP_REPO}/releases"
REQUEST_TIMEOUT = 10

import github_client
from github_client import github_api_get, cdn_get, get_latest_tree_sha

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

threading.Thread(target=_cleanup_old_executables, daemon=True).start()

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

def get_app_base_path():
    # Detect flags from arguments
    open_only = "--open-only" in sys.argv
    close_only = "--close-only" in sys.argv
    
    # ALWAYS close any open context menus first to prevent stacking
    try:
        user32 = ctypes.windll.user32
        WM_CLOSE = 0x0010
        hwnd_menu = user32.FindWindowW("#32768", None)
        while hwnd_menu:
            user32.SendMessageW(hwnd_menu, WM_CLOSE, 0, 0)
            hwnd_menu = user32.FindWindowW("#32768", None)
    except Exception:
        pass

    if close_only:
        # Trigger reload using global constants and exit immediately
        root = PROJECT_ROOT
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
        os._exit(0)

    return APP_BASE_PATH

_restore_bundled_assets()
get_app_base_path()
_sync_local_runtime()

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

APP_VERSION = '2.0.23'
VERSION = APP_VERSION

class UpdateWorker(QObject):
    check_finished = pyqtSignal(bool, str, str)
    download_progress = pyqtSignal(int)
    download_finished = pyqtSignal(bool, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def check_for_updates(self, force=False):
        try:
            candidates = []
            parsed_current = _parse_version(VERSION)

            # 1. Fast CDN-based version manifest (Instant, 20-100ms, zero rate limit)
            cdn_url = f"https://raw.githubusercontent.com/{APP_REPO}/main/version.json?t={int(time.time())}"
            try:
                cdn_res = cdn_get(cdn_url, max_retries=1, timeout=3)
                if cdn_res.status_code == 200:
                    cdn_data = cdn_res.json()
                    remote_v = str(cdn_data.get('version', '')).lstrip('vV').strip()
                    dl_url = cdn_data.get('download_url')
                    if remote_v and dl_url:
                        candidates.append((_parse_version(remote_v), remote_v, dl_url))
            except Exception:
                pass

            # If force=True (Re-install) or CDN already found a newer version, return immediately!
            if candidates:
                highest_parsed, highest_v_str, highest_url = candidates[0]
                if force or highest_parsed > parsed_current:
                    target_v = highest_v_str if highest_parsed >= parsed_current else VERSION
                    self.check_finished.emit(True, target_v, highest_url)
                    return

            # 2. Check GitHub Releases latest API (Fallback for releases not yet in version.json)
            try:
                latest_url = f"https://api.github.com/repos/{APP_REPO}/releases/latest"
                response = github_api_get(latest_url, max_retries=1, timeout=2)
                if response.status_code == 200:
                    release_data = response.json()
                    tag_name = release_data.get('tag_name', '')
                    remote_version = tag_name.lstrip('vV').strip()
                    if remote_version:
                        for asset in release_data.get('assets', []):
                            asset_name = asset.get('name', '').lower()
                            if asset_name.endswith('.exe'):
                                download_url = asset.get('browser_download_url')
                                candidates.append((_parse_version(remote_version), remote_version, download_url))
                                break
            except Exception:
                pass

            # 3. Multi-release fallback if still no binary candidate found
            if not candidates:
                try:
                    releases_url = f"https://api.github.com/repos/{APP_REPO}/releases"
                    res = github_api_get(releases_url, max_retries=1, timeout=2)
                    if res.status_code == 200:
                        for rel in res.json():
                            r_tag = rel.get('tag_name', '').lstrip('vV').strip()
                            for asset in rel.get('assets', []):
                                a_name = asset.get('name', '').lower()
                                if a_name.endswith('.exe'):
                                    candidates.append((_parse_version(r_tag), r_tag, asset.get('browser_download_url')))
                                    break
                            if candidates:
                                break
                except Exception:
                    pass

            # Sort all candidates to find highest available release
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
                else:
                    self.check_finished.emit(False, highest_v_str, highest_url)
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

            if self._is_cancelled:
                raise ValueError("Download cancelled")

            if os.path.exists(target_url) and os.path.isfile(target_url):
                shutil.copy2(target_url, temp_destination)
                self.download_progress.emit(100)
            else:
                from github_client import download_file
                download_file(target_url, temp_destination, progress_callback=self.download_progress.emit, cancel_check=lambda: self._is_cancelled, timeout=120)

            if self._is_cancelled:
                raise ValueError("Download cancelled")

            if not os.path.exists(temp_destination) or os.path.getsize(temp_destination) < 1024 * 50:
                raise ValueError("Downloaded file is invalid or corrupted")

            with open(temp_destination, 'rb') as binary_file:
                magic_bytes = binary_file.read(2)
                if magic_bytes != b'MZ' and magic_bytes != b'PK':
                    raise ValueError("Downloaded file is not a valid binary asset")

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
    DEPRECATED_KEYS = ("auto_save", "auto_apply_theme_colors", "auto_preview_context_menu")

    def __init__(self):
        self.defaults = {
            "auto_update": False,
            "auto_check_updates": False
        }
        self.settings = self.defaults.copy()
        self.load()

    def load(self):
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, 'r') as f:
                    data = json.load(f)
                
                had_deprecated = False
                for k in self.DEPRECATED_KEYS:
                    if k in data:
                        data.pop(k, None)
                        had_deprecated = True
                
                self.settings.update(data)
                if had_deprecated:
                    self.save()
            except Exception:
                pass
        else:
            # Create default settings if missing
            self.save()

    def save(self):
        try:
            os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
            for k in self.DEPRECATED_KEYS:
                self.settings.pop(k, None)
            with open(SETTINGS_FILE, 'w') as f:
                json.dump(self.settings, f, indent=4)
        except Exception:
            pass

    def get(self, key, default=None):
        if key in self.DEPRECATED_KEYS:
            return False
        return self.settings.get(key, self.defaults.get(key, default))

    def set(self, key, value):
        if key in self.DEPRECATED_KEYS:
            return
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
_crisp_pixmap_cache = OrderedDict()
_MAX_PIXMAP_CACHE_SIZE = 128

def load_crisp_pixmap(icon_path, target_size=96):
    if not icon_path or not os.path.exists(icon_path):
        return QPixmap()
    norm_path = os.path.normpath(icon_path).lower()
    cache_key = (norm_path, target_size)
    if cache_key in _crisp_pixmap_cache:
        _crisp_pixmap_cache.move_to_end(cache_key)
        return _crisp_pixmap_cache[cache_key]
    try:
        pix = None
        icon = QIcon(icon_path)
        if not icon.isNull():
            p = icon.pixmap(target_size, target_size)
            if not p.isNull():
                pix = p
        if pix is None or pix.isNull():
            p = QPixmap(icon_path)
            if not p.isNull():
                if p.width() > target_size or p.height() > target_size:
                    pix = p.scaled(target_size, target_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                else:
                    pix = p
        if pix and not pix.isNull():
            if len(_crisp_pixmap_cache) >= _MAX_PIXMAP_CACHE_SIZE:
                _crisp_pixmap_cache.popitem(last=False)
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

init_plugin_workers(
    project_root=PROJECT_ROOT,
    plugins_dir=PLUGINS_DIR,
    cache_dir=CACHE_DIR,
    icons_cache_dir=ICONS_CACHE_DIR,
    lib_dir=LIB_DIR,
    default_icon_path=DEFAULT_ICON_PATH,
    request_timeout=REQUEST_TIMEOUT,
    github_repo=_GITHUB_REPO,
    git_tree_cache_file=GIT_TREE_CACHE_FILE,
    plugins_cache_file=PLUGINS_CACHE_FILE,
    load_crisp_pixmap_fn=load_crisp_pixmap,
    get_plugin_install_path_fn=get_plugin_install_path,
    add_nss_import_fn=add_nss_import,
    add_directory_to_system_path_fn=add_to_path
)

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
        self._cached_icon_urls = {}
        self._downloading_icons = set()
        icon_urls_file = os.path.join(ICONS_CACHE_DIR, '_icon_urls.json')
        if os.path.exists(icon_urls_file):
            try:
                self._cached_icon_urls = safe_json_read(icon_urls_file) or {}
            except Exception:
                self._cached_icon_urls = {}

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

        if plugin_name in self._downloading_icons:
            return

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

        # Resolve icon_url if missing from local plugin data
        if not plugin.get('icon_url') and hasattr(self.registry, 'get_remote_plugin'):
            remote_info = self.registry.get_remote_plugin(plugin_name)
            if remote_info and remote_info.get('icon_url'):
                plugin['icon_url'] = remote_info['icon_url']

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
                            # Auto-cache locally so icon survives uninstallation
                            cached_icon_path = os.path.join(ICONS_CACHE_DIR, f"{plugin_name}.png")
                            if not os.path.exists(cached_icon_path):
                                try:
                                    pix.save(cached_icon_path, "PNG")
                                except Exception:
                                    pass
                            self.icon_loaded.emit(plugin_name, pix)
                            return
            except Exception:
                pass

        # 2. Check ICONS_CACHE_DIR (case-insensitive) — but invalidate ONLY if recorded icon_url changed
        icon_url = plugin.get('icon_url', '')
        cached_icon_path = os.path.join(ICONS_CACHE_DIR, f"{plugin_name}.png")
        icon_urls_file = os.path.join(ICONS_CACHE_DIR, '_icon_urls.json')
        prev_url = self._cached_icon_urls.get(plugin_name)

        url_changed = bool(icon_url and prev_url is not None and prev_url != icon_url)
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
                        if icon_url and prev_url != icon_url:
                            self._cached_icon_urls[plugin_name] = icon_url
                            try: atomic_json_write(icon_urls_file, self._cached_icon_urls)
                            except Exception: pass
                        self.icon_loaded.emit(plugin_name, pix)
                        return

        def handle_icon_error(e):
            self._downloading_icons.discard(plugin_name)
            cached_path = os.path.join(ICONS_CACHE_DIR, f"{plugin_name}.png")
            if os.path.exists(cached_path):
                pix = load_crisp_pixmap(cached_path, 128)
                if not pix.isNull():
                    self.icon_loaded.emit(plugin_name, pix)
                    return
            fallback_pix = self._extract_nss_fallback_icon(plugin_name, install_path)
            self.icon_loaded.emit(plugin_name, fallback_pix if fallback_pix else QPixmap(DEFAULT_ICON_PATH))

        def handle_icon_success(p_name, pix):
            self._downloading_icons.discard(p_name)
            if pix and not pix.isNull() and icon_url:
                try:
                    self._cached_icon_urls[p_name] = icon_url
                    atomic_json_write(icon_urls_file, self._cached_icon_urls)
                except Exception:
                    pass
            self.icon_loaded.emit(p_name, pix if (pix and not pix.isNull()) else (self._extract_nss_fallback_icon(p_name, install_path) or QPixmap(DEFAULT_ICON_PATH)))

        # 3. Download from icon_url if provided
        if plugin.get('icon_url'):
            self._downloading_icons.add(plugin_name)
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
                # Ensure icon is cached locally before deleting the plugin folder
                cached_icon_path = os.path.join(ICONS_CACHE_DIR, f"{plugin_name}.png")
                if not os.path.exists(cached_icon_path) and os.path.isdir(target_plugin_dir):
                    try:
                        for fname in os.listdir(target_plugin_dir):
                            if fname.lower().endswith(('.png', '.ico', '.jpg', '.svg')):
                                src_icon = os.path.join(target_plugin_dir, fname)
                                p = load_crisp_pixmap(src_icon, 128)
                                if not p.isNull():
                                    p.save(cached_icon_path, "PNG")
                                    break
                    except Exception:
                        pass
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
            thread.deleteLater()

    def stop_all_threads(self):
        for key, (thread, worker) in list(self.active_threads.items()):
            if hasattr(worker, 'cancel'):
                worker.cancel()
            thread.quit()
            if not thread.wait(100):
                thread.terminate()
            thread.deleteLater()

class AutoHideScrollManager(QObject):
    """Universal auto-hiding scrollbar manager.
    Keeps scrollbars hidden (0.0 opacity) until user scrolls, displays them for 500ms (0.5s),
    and smoothly fades them out. Keeps them visible while hovered/dragged."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._scrollbars = {}

    def attach(self, scrollbar: QScrollBar):
        if not scrollbar or not isinstance(scrollbar, QScrollBar) or scrollbar in self._scrollbars:
            return
        
        effect = QGraphicsOpacityEffect(scrollbar)
        effect.setOpacity(0.0)
        scrollbar.setGraphicsEffect(effect)
        
        timer = QTimer(scrollbar)
        timer.setSingleShot(True)
        timer.setInterval(500)  # 0.5s
        
        anim = QPropertyAnimation(effect, b"opacity", scrollbar)
        anim.setDuration(200)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        
        def fade_out():
            if scrollbar.underMouse():
                timer.start(500)
                return
            anim.stop()
            anim.setStartValue(effect.opacity())
            anim.setEndValue(0.0)
            anim.start()
            
        timer.timeout.connect(fade_out)
        
        def show_scrollbar(*args):
            if scrollbar.maximum() > scrollbar.minimum():
                anim.stop()
                effect.setOpacity(1.0)
                timer.start(500)
            
        scrollbar.valueChanged.connect(show_scrollbar)
        scrollbar.sliderMoved.connect(show_scrollbar)
        scrollbar.installEventFilter(self)
        
        self._scrollbars[scrollbar] = (effect, timer, anim)

    def attach_all(self, widget: QWidget):
        if not widget:
            return
        from PyQt5.QtWidgets import QAbstractScrollArea
        if isinstance(widget, QAbstractScrollArea):
            self.attach(widget.verticalScrollBar())
            self.attach(widget.horizontalScrollBar())
        if hasattr(widget, 'findChildren'):
            for sa in widget.findChildren(QAbstractScrollArea):
                self.attach(sa.verticalScrollBar())
                self.attach(sa.horizontalScrollBar())
            for sb in widget.findChildren(QScrollBar):
                self.attach(sb)

    def eventFilter(self, obj, event):
        if isinstance(obj, QScrollBar) and obj in self._scrollbars:
            effect, timer, anim = self._scrollbars[obj]
            if event.type() in (QEvent.Enter, QEvent.MouseMove, QEvent.MouseButtonPress):
                anim.stop()
                effect.setOpacity(1.0)
                timer.stop()
            elif event.type() in (QEvent.Leave, QEvent.MouseButtonRelease):
                timer.start(500)
        elif event.type() == QEvent.Show:
            if isinstance(obj, QScrollBar):
                self.attach(obj)
            elif hasattr(obj, 'findChildren'):
                for sb in obj.findChildren(QScrollBar):
                    self.attach(sb)
        elif event.type() == QEvent.Wheel:
            if hasattr(obj, 'verticalScrollBar'):
                self.attach(obj.verticalScrollBar())
                if obj.verticalScrollBar() in self._scrollbars:
                    effect, timer, anim = self._scrollbars[obj.verticalScrollBar()]
                    if obj.verticalScrollBar().maximum() > obj.verticalScrollBar().minimum():
                        anim.stop()
                        effect.setOpacity(1.0)
                        timer.start(500)
            if hasattr(obj, 'horizontalScrollBar'):
                self.attach(obj.horizontalScrollBar())
                if obj.horizontalScrollBar() in self._scrollbars:
                    effect, timer, anim = self._scrollbars[obj.horizontalScrollBar()]
                    if obj.horizontalScrollBar().maximum() > obj.horizontalScrollBar().minimum():
                        anim.stop()
                        effect.setOpacity(1.0)
                        timer.start(500)
        return super().eventFilter(obj, event)


class NavTabButton(QPushButton):
    def __init__(self, icon_name, label_text, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setFixedSize(66, 68)
        self.setCursor(Qt.PointingHandCursor)
        self.label_text = label_text
        self.icon_pix = load_crisp_pixmap(resource_path(f'icons/{icon_name}'), 28)
        self.setObjectName("navTabButton")

    def enterEvent(self, event):
        super().enterEvent(event)
        self.update()

    def leaveEvent(self, event):
        super().leaveEvent(event)
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        r = self.rect()

        is_checked = self.isChecked()
        is_hovered = self.underMouse()

        if is_checked:
            # Glassy container with gradient sheen
            grad = QLinearGradient(0, 0, r.width(), r.height())
            grad.setColorAt(0.0, QColor(231, 130, 132, 55))
            grad.setColorAt(0.45, QColor(202, 158, 230, 38))
            grad.setColorAt(1.0, QColor(140, 170, 238, 28))
            p.setBrush(grad)
            p.setPen(QPen(QColor(255, 255, 255, 45), 1.0))
            p.drawRoundedRect(r.adjusted(1, 1, -1, -1), 14, 14)
        elif is_hovered:
            p.setBrush(QColor(255, 255, 255, 12))
            p.setPen(QPen(QColor(255, 255, 255, 22), 1.0))
            p.drawRoundedRect(r.adjusted(1, 1, -1, -1), 14, 14)

        # Draw icon
        if not self.icon_pix.isNull():
            p.setOpacity(1.0 if is_checked else (0.85 if is_hovered else 0.55))
            ix = (r.width() - 26) // 2
            p.drawPixmap(ix, 10, 26, 26, self.icon_pix)
            p.setOpacity(1.0)

        # Draw text
        font = QFont('Segoe UI Variable Display', 10, QFont.Bold if is_checked else QFont.Normal)
        p.setFont(font)
        text_color = QColor(255, 255, 255) if is_checked else (QColor(198, 208, 245) if is_hovered else QColor(140, 146, 164))
        p.setPen(text_color)
        p.drawText(0, 40, r.width(), 22, Qt.AlignCenter, self.label_text)


class PluginManager(QWidget):
    _corner_radius = 28

    def __init__(self):
        self._corner_radius = 28
        super().__init__()
        self.setWindowTitle("iMA Menu")
        self.setMinimumSize(750, 500)
        self.resize(1112, 750)
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self._apply_rounded_mask()
        
        self.setWindowIcon(QIcon(resource_path('icons/icon.ico')))
        self.setup_cache_dirs()
        
        # Universal Auto-Hide Scrollbar Manager
        self.scroll_manager = AutoHideScrollManager(self)
        QApplication.instance().installEventFilter(self.scroll_manager)
        self.scroll_manager.attach_all(self)

        self.settings_manager = SettingsManager()
        self.plugin_logic = PluginLogic()
        self.sync_manager = None
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
        self._pixmap_cache = {}
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

        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setObjectName("scrollArea")
        self.scroll_content = QWidget()
        self.grid_layout = QGridLayout(self.scroll_content)
        self.grid_layout.setAlignment(Qt.AlignTop)
        self.scroll_area.setWidget(self.scroll_content)
        self.scroll_area.setStyleSheet("#scrollArea { border: 0px; background: transparent; }")
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
        self._default_icon_pixmap = QPixmap(DEFAULT_ICON_PATH)


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

        # 2. Schedule non-blocking background synchronization tasks in idle intervals
        QTimer.singleShot(400, self._async_sync_tools_menu)
        self.scroll_manager.attach_all(self)
        
        QTimer.singleShot(800, self._setup_file_watcher)
        QTimer.singleShot(1200, self.fetch_plugins_list)
        QTimer.singleShot(1800, self._start_error_monitor)
        QTimer.singleShot(2500, self._take_global_nss_snapshot)

    def _init_sync_manager(self):
        if self.sync_manager is None:
            from cloud_sync import CloudSyncManager
            self.sync_manager = CloudSyncManager(PROJECT_ROOT)
            self.sync_manager.auth_finished.connect(self.on_sync_auth_finished)
            self.sync_manager.sync_progress.connect(self.on_sync_progress)
            self.sync_manager.sync_finished.connect(self.on_sync_finished)
            self.sync_manager.profile_updated.connect(self._update_sync_ui_state)
            avatar_file = os.path.join(PROJECT_ROOT, 'cache', 'profile_avatar.png')
            if self.sync_manager.access_token and (not self.sync_manager.user_name or not os.path.exists(avatar_file)):
                self.sync_manager.fetch_user_profile(background=True)
        return self.sync_manager

    def _async_sync_tools_menu(self):
        def worker():
            try:
                sync_tools_menu(PROJECT_ROOT, self.plugin_logic.registry)
            except Exception:
                pass
        threading.Thread(target=worker, daemon=True).start()

    def load_cached_plugins_immediately(self):
        local_plugins = self.plugin_logic.registry.get_local_plugins_for_ui()
        is_plugins_page = (self.stacked_widget.currentWidget() == self.plugins_page) if hasattr(self, 'stacked_widget') else True
        if len(local_plugins) > 0 and is_plugins_page:
            self.plugins_tab_container.show()
        else:
            self.plugins_tab_container.hide()
            self.current_plugins_tab = "store"
            self.store_tab_btn.setChecked(True)

        self.render_current_plugins_tab()

    def _start_error_monitor(self):
        try:
            from nss_error_monitor import ShellLogMonitor
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
            editor_saved = self.theme_editor_page.save_theme() if getattr(self, 'theme_editor_page', None) else False
            switcher_saved = self.theme_switcher_page.save_theme() if getattr(self, 'theme_switcher_page', None) else False
            
            if editor_saved or switcher_saved:
                self.commit_tinted_icons()
                self.update_snapshot(os.path.join(PROJECT_ROOT, 'imports', 'theme.nss'))
                self.reload_shell()
                self.theme_status_label.setText("Theme Saved")
                self.theme_status_label.setStyleSheet("color: #e78284;")
                QTimer.singleShot(3000, self.theme_status_label.clear)
        finally:
            self._is_internal_change = False

    def reset_theme_and_update_status(self):
        if getattr(self, 'theme_editor_page', None) and self.theme_editor_page.reset_theme():
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
        if hasattr(self, 'error_monitor') and self.error_monitor and getattr(self.error_monitor, '_enabled', False):
             if not self.error_monitor.pre_reload_check():
                 # Monitor found errors and is likely fixing them. 
                 # Let the monitor trigger the reload when done.
                 return

        # 2. Trigger the actual reload (non-blocking)
        trigger_shell_reload(close_only=True)

    def _on_manual_fix_required(self, filename, line, message):
        # User requested no popup. Logging the error instead.
        print(f"ERROR: Syntax error in {filename}:{line} - {message}")

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
        self.file_sync_timer.start(800) # 800ms debounce to prevent lag

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
                if getattr(self, 'theme_editor_page', None):
                    self.theme_editor_page.reload_theme()
                if getattr(self, 'theme_switcher_page', None):
                    self.theme_switcher_page.selected_theme = self.theme_switcher_page._get_current_theme_from_file()
                    self.theme_switcher_page._highlight_current_theme()
                self.show_sync_status("Synced Theme")
            
            # Shell or Imports directory (Plugin changes)
            elif clean_path.endswith('/shell.nss') or '/imports/' in clean_path or clean_path.endswith('/imports'):
                if hasattr(self, 'modify_page') and hasattr(self.modify_page, 'imports_pg'):
                    if getattr(self.modify_page, 'tab', None) and self.modify_page.tab.currentIndex() == 1:
                        self.modify_page.imports_pg.refresh()
                    else:
                        self.modify_page.imports_pg._is_loaded = False
                self.show_sync_status("Synced Imports")
            
            # Theme directory (New/Removed theme files)
            elif '/theme/' in clean_path or clean_path.endswith('/theme'):
                if getattr(self, 'theme_switcher_page', None):
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
            if getattr(self, 'theme_editor_page', None):
                self.theme_editor_page.reload_theme()
            if getattr(self, 'theme_switcher_page', None):
                self.theme_switcher_page.refresh_list()
                self.theme_switcher_page.selected_theme = self.theme_switcher_page._get_current_theme_from_file()
                self.theme_switcher_page._highlight_current_theme()
                
            # 3. Reload Shell
            self.reload_shell()
            self.show_sync_status("UI Refreshed")
        finally:
            self._is_internal_change = False

    def show_sync_status(self, text):
        if hasattr(self, 'title_status_label') and self.title_status_label:
            self.title_status_label.setText(text)
            self.title_status_label.setStyleSheet("color: #ff6b81; font-size: 13px; font-weight: bold; background: transparent;")
            QTimer.singleShot(2500, self.title_status_label.clear)
        elif hasattr(self, 'theme_status_label') and self.theme_status_label:
            self.theme_status_label.setText(text)
            self.theme_status_label.setStyleSheet("color: #e78284;")
            QTimer.singleShot(2500, self.theme_status_label.clear)

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
        title_layout.setContentsMargins(10, 0, 10, 0)
        title_layout.setSpacing(6)

        app_icon_label = QLabel()
        app_icon_pixmap = QPixmap(resource_path('icons/icon.ico'))
        app_icon_label.setPixmap(app_icon_pixmap.scaled(24, 24, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        title_layout.addWidget(app_icon_label)

        title_label = QLabel("iMA Menu")
        title_label.setFont(QFont('Segoe UI Variable Display', 16, QFont.Bold))
        title_label.setObjectName("titleLabel")
        title_layout.addWidget(title_label)

        title_layout.addStretch(1)

        self.title_status_label = QLabel("")
        self.title_status_label.setObjectName("titleStatusLabel")
        self.title_status_label.setAlignment(Qt.AlignCenter)
        self.title_status_label.setStyleSheet("color: #ff6b81; font-size: 13px; font-weight: bold; background: transparent;")
        title_layout.addWidget(self.title_status_label, 2)

        title_layout.addStretch(1)

        # Dynamic Top Navigation Bar (Store / Local) in title bar left of open folder
        self.current_plugins_tab = "store"
        self.plugins_tab_container = QFrame()
        self.plugins_tab_container.setObjectName("pluginsTabContainer")
        self.plugins_tab_container.setFixedHeight(32)
        self.plugins_tab_container.setStyleSheet("""
            QFrame#pluginsTabContainer {
                background-color: rgba(255, 255, 255, 0.04);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 16px;
            }
        """)
        pt_lay = QHBoxLayout(self.plugins_tab_container)
        pt_lay.setContentsMargins(2, 2, 2, 2)
        pt_lay.setSpacing(2)

        self.store_tab_btn = PillTabButton("Store", height=28)
        self.store_tab_btn.setChecked(True)
        self.store_tab_btn.clicked.connect(lambda: self.switch_plugins_tab("store"))

        self.local_tab_btn = PillTabButton("Local", height=28)
        self.local_tab_btn.clicked.connect(lambda: self.switch_plugins_tab("local"))

        from PyQt5.QtWidgets import QButtonGroup
        self.plugins_tab_group = QButtonGroup(self)
        self.plugins_tab_group.setExclusive(True)
        self.plugins_tab_group.addButton(self.store_tab_btn)
        self.plugins_tab_group.addButton(self.local_tab_btn)

        pt_lay.addWidget(self.store_tab_btn)
        pt_lay.addWidget(self.local_tab_btn)

        title_layout.addWidget(self.plugins_tab_container, 0, Qt.AlignVCenter)

        floating_icon_btn_style = """
            QPushButton {
                background: transparent;
                border: none;
                border-radius: 6px;
                padding: 3px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.08);
            }
            QPushButton:pressed {
                background: rgba(255, 255, 255, 0.15);
            }
        """
        open_folder_button = QPushButton()
        open_folder_button.setIcon(QIcon(resource_path('icons/open.png')))
        open_folder_button.setIconSize(QSize(22, 22))
        open_folder_button.setFixedSize(30, 30)
        open_folder_button.setCursor(Qt.PointingHandCursor)
        open_folder_button.setStyleSheet(floating_icon_btn_style)
        open_folder_button.clicked.connect(self.open_root_folder)

        self.refresh_button = QPushButton()
        self.refresh_button.setIcon(QIcon(resource_path('icons/refresh.png')))
        self.refresh_button.setIconSize(QSize(22, 22))
        self.refresh_button.setFixedSize(30, 30)
        self.refresh_button.setCursor(Qt.PointingHandCursor)
        self.refresh_button.setStyleSheet(floating_icon_btn_style)
        self.refresh_button.clicked.connect(self.handle_global_refresh)

        # Single pill-shaped container for minimize, maximize, and close
        window_controls_pill = QFrame()
        window_controls_pill.setObjectName("windowControlsPill")
        window_controls_pill.setFixedHeight(28)
        window_controls_pill.setStyleSheet("""
            QFrame#windowControlsPill {
                background-color: rgba(255, 255, 255, 0.04);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 14px;
            }
            QPushButton.windowControlBtn {
                background: transparent;
                border: none;
                border-radius: 11px;
                color: #8c92a4;
                font-family: 'Segoe MDL2 Assets';
                font-size: 10px;
                min-width: 28px;
                max-width: 28px;
                min-height: 22px;
                max-height: 22px;
            }
            QPushButton.windowControlBtn:hover {
                background: rgba(255, 255, 255, 0.08);
                color: #ffffff;
            }
            QPushButton#closeControlBtn:hover {
                background: #e78284;
                color: #ffffff;
            }
        """)
        wc_layout = QHBoxLayout(window_controls_pill)
        wc_layout.setContentsMargins(2, 2, 2, 2)
        wc_layout.setSpacing(1)

        minimize_button = QPushButton("\uE921")
        minimize_button.setProperty("class", "windowControlBtn")
        minimize_button.setCursor(Qt.PointingHandCursor)
        minimize_button.clicked.connect(self.showMinimized)

        self.maximize_button = QPushButton("\uE922")
        self.maximize_button.setProperty("class", "windowControlBtn")
        self.maximize_button.setCursor(Qt.PointingHandCursor)
        self.maximize_button.clicked.connect(self.toggle_maximize)

        close_button = QPushButton("\uE8BB")
        close_button.setObjectName("closeControlBtn")
        close_button.setProperty("class", "windowControlBtn")
        close_button.setCursor(Qt.PointingHandCursor)
        close_button.clicked.connect(self.close)

        wc_layout.addWidget(minimize_button)
        wc_layout.addWidget(self.maximize_button)
        wc_layout.addWidget(close_button)

        title_layout.addWidget(open_folder_button)
        title_layout.addWidget(self.refresh_button)
        title_layout.addWidget(window_controls_pill)
        return title_bar

    def toggle_maximize(self):
        if self.isMaximized():
            self.showNormal()
            self.maximize_button.setText("\uE922")
        else:
            self.showMaximized()
            self.maximize_button.setText("\uE923")

    def update_refresh_btn_visibility(self, index):
        # Refresh button is always persistent across all tabs
        self.refresh_button.setVisible(True)
        if hasattr(self, 'plugins_tab_container'):
            self.plugins_tab_container.setVisible(index == 0)
        
        # Keep matching side panel button checked
        if hasattr(self, 'side_plugins_btn'):
            cur_w = self.stacked_widget.currentWidget()
            if cur_w == self.plugins_page:
                self.side_plugins_btn.setChecked(True)
            elif hasattr(self, '_modify_page_widget') and cur_w == self._modify_page_widget and self._modify_page_widget is not None:
                self.side_modify_btn.setChecked(True)
            elif hasattr(self, '_theme_page_widget') and cur_w == self._theme_page_widget and self._theme_page_widget is not None:
                self.side_theme_btn.setChecked(True)
            elif hasattr(self, '_settings_page_widget') and cur_w == self._settings_page_widget and self._settings_page_widget is not None:
                self.side_settings_btn.setChecked(True)

    def handle_global_refresh(self):
        cur_w = self.stacked_widget.currentWidget()
        if cur_w == self.plugins_page:
            self.refresh_plugins()
        elif hasattr(self, '_modify_page_widget') and cur_w == self._modify_page_widget and self._modify_page_widget is not None:
            self._modify_page_widget.load_and_init_ui()
            self.show_sync_status("Rules Refreshed")
        elif hasattr(self, '_theme_page_widget') and cur_w == self._theme_page_widget and self._theme_page_widget is not None:
            if hasattr(self, 'theme_stacked_widget'):
                active_idx = self.theme_stacked_widget.currentIndex()
                if active_idx == 0 and getattr(self, 'theme_switcher_page', None):
                    self.theme_switcher_page.refresh_list()
                elif active_idx == 1 and getattr(self, 'theme_editor_page', None):
                    self.theme_editor_page.reload_theme()
                elif active_idx == 2 and getattr(self, 'cursor_page', None):
                    self.cursor_page.refresh_list()
            self.show_sync_status("Theme Refreshed")
        elif hasattr(self, '_settings_page_widget') and cur_w == self._settings_page_widget and self._settings_page_widget is not None:
            self.setup_settings_page()
            self.show_sync_status("Settings Refreshed")
        else:
            self.refresh_plugins()

    def bring_to_focus(self):
        try:
            if self.isMinimized():
                self.showNormal()
            self.show()
            self.raise_()
            self.activateWindow()

            hwnd = int(self.winId())
            if hwnd and os.name == 'nt':
                user32 = ctypes.windll.user32
                SW_RESTORE = 9
                user32.ShowWindow(hwnd, SW_RESTORE)
                user32.BringWindowToTop(hwnd)

                fore_hwnd = user32.GetForegroundWindow()
                fore_thread = user32.GetWindowThreadProcessId(fore_hwnd, None)
                app_thread = ctypes.windll.kernel32.GetCurrentThreadId()
                if fore_thread and fore_thread != app_thread:
                    user32.AttachThreadInput(fore_thread, app_thread, True)
                    user32.SetForegroundWindow(hwnd)
                    user32.AttachThreadInput(fore_thread, app_thread, False)
                else:
                    user32.SetForegroundWindow(hwnd)

                user32.SwitchToThisWindow(hwnd, True)

                # Flash taskbar icon
                class FLASHWINFO(ctypes.Structure):
                    _fields_ = [
                        ('cbSize', wintypes.UINT),
                        ('hwnd', wintypes.HWND),
                        ('dwFlags', wintypes.DWORD),
                        ('uCount', wintypes.UINT),
                        ('dwTimeout', wintypes.DWORD)
                    ]
                FLASHW_ALL = 0x00000003
                FLASHW_TIMERNOFG = 0x0000000C
                fwi = FLASHWINFO()
                fwi.cbSize = ctypes.sizeof(FLASHWINFO)
                fwi.hwnd = hwnd
                fwi.dwFlags = FLASHW_ALL | FLASHW_TIMERNOFG
                fwi.uCount = 4
                fwi.dwTimeout = 0
                user32.FlashWindowEx(ctypes.byref(fwi))
        except Exception:
            pass
        try:
            QApplication.alert(self, 0)
        except Exception:
            pass


    def resizeEvent(self, event):
        self._apply_rounded_mask()
        super().resizeEvent(event)
        self.resize_timer.start(50)
        if hasattr(self, 'details_popup') and self.details_popup and self.details_popup.isVisible():
            self.details_popup.setGeometry(self.rect().adjusted(40, 50, -40, -30))

    def recalculate_plugin_grid(self):
        if not hasattr(self, 'grid_layout') or not self.plugin_cards:
            return
            
        self.scroll_content.setUpdatesEnabled(False)
        try:
            while self.grid_layout.count():
                self.grid_layout.takeAt(0)

            cols = 2
            self.grid_layout.setAlignment(Qt.AlignTop)
            self.grid_layout.setContentsMargins(16, 12, 16, 20)
            self.grid_layout.setHorizontalSpacing(14)
            self.grid_layout.setVerticalSpacing(12)
            self.grid_layout.setColumnStretch(0, 1)
            self.grid_layout.setColumnStretch(1, 1)
            
            for i, (plugin_name, card) in enumerate(self.plugin_cards.items()):
                row, col = i // cols, i % cols
                self.grid_layout.addWidget(card, row, col)
                card.show()
        finally:
            self.scroll_content.setUpdatesEnabled(True)
        
        QTimer.singleShot(50, self.check_visible_cards)

    def get_modify_page(self):
        if self._modify_page_widget is None:
            from modify_widget import ModifyWidget, set_project_root
            set_project_root(PROJECT_ROOT)
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
            from theme_switcher_widget import ThemeSwitcherWidget
            from cursor_widget import CursorGalleryWidget
            from theme_editor_widget import ThemeEditorWidget

            self.theme_page = QWidget()
            self._theme_page_widget = self.theme_page
            self.theme_layout = QVBoxLayout(self.theme_page)
            self.theme_layout.setContentsMargins(0, 0, 0, 0)
            self.theme_layout.setSpacing(0)

            # 1. Pill-shaped Segmented Main Tabs Container (Themes / Editor / Mouse)
            self.theme_main_tab_container = QFrame()
            self.theme_main_tab_container.setObjectName("pillTabContainer")
            self.theme_main_tab_container.setStyleSheet("background-color: transparent; border: none; padding: 0px;")
            theme_main_tab_lay = QHBoxLayout(self.theme_main_tab_container)
            theme_main_tab_lay.setContentsMargins(0, 0, 0, 0)
            theme_main_tab_lay.setSpacing(4)

            self.themes_tab_btn = PillTabButton(" Themes", 0xE790, height=30)
            self.themes_tab_btn.setChecked(True)
            self.themes_tab_btn.clicked.connect(lambda: switch_theme_page_tab(0))

            self.editor_tab_btn = PillTabButton(" Editor", 0xE104, height=30)
            self.editor_tab_btn.clicked.connect(lambda: switch_theme_page_tab(1))

            self.mouse_tab_btn = PillTabButton(" Mouse", 0xE962, height=30)
            self.mouse_tab_btn.clicked.connect(lambda: switch_theme_page_tab(2))

            self.theme_main_tab_group = QButtonGroup(self)
            self.theme_main_tab_group.setExclusive(True)
            self.theme_main_tab_group.addButton(self.themes_tab_btn)
            self.theme_main_tab_group.addButton(self.editor_tab_btn)
            self.theme_main_tab_group.addButton(self.mouse_tab_btn)

            theme_main_tab_lay.addWidget(self.themes_tab_btn)
            theme_main_tab_lay.addWidget(self.editor_tab_btn)
            theme_main_tab_lay.addWidget(self.mouse_tab_btn)

            self.theme_switcher_page = ThemeSwitcherWidget(
                theme_dir=os.path.join(PROJECT_ROOT, 'theme'),
                theme_nss_path=os.path.join(PROJECT_ROOT, 'imports', 'theme.nss')
            )
            self.cursor_page = None
            self.theme_editor_page = None
            self._theme_editor_initialized = False
            self._cursor_page_initialized = False
            self.editor_placeholder = QWidget()
            self.mouse_placeholder = QWidget()

            self.theme_save_button = PillPushButton("Save", "primary", height=30)
            self.theme_save_button.setFixedWidth(70)
            self.theme_reset_button = PillPushButton("Reset", "reset", height=30)
            self.theme_reset_button.setFixedWidth(70)
            self.sync_container = QFrame(); self.sync_container.setObjectName("syncContainer")
            self.sync_container.setStyleSheet("QFrame#syncContainer { background: rgba(255, 255, 255, 0.05); border-radius: 16px; border: 1px solid rgba(255, 255, 255, 0.1); }")
            sync_cl = QHBoxLayout(self.sync_container); sync_cl.setContentsMargins(15, 0, 8, 0); sync_cl.setSpacing(10)

            self.sync_label = QLabel("Sync Colors"); self.sync_label.setStyleSheet("color: white; font-weight: 500; font-size: 11px; background: transparent; border: none;")
            self.theme_sync_button = QPushButton("\uE117"); self.theme_sync_button.setFont(QFont('Segoe MDL2 Assets', 12))
            self.theme_sync_button.setFixedSize(30, 30); self.theme_sync_button.setCursor(QCursor(Qt.PointingHandCursor))
            self.theme_sync_button.setStyleSheet("QPushButton { color: white; background: rgba(255,255,255,0.1); border: none; border-radius: 15px; } QPushButton:hover { background: rgba(255,255,255,0.2); }")
            self.theme_sync_button.clicked.connect(lambda: self.trigger_global_tint(force=True))

            sync_cl.addWidget(self.sync_label); sync_cl.addWidget(self.theme_sync_button)

            top_header_layout = QHBoxLayout()
            top_header_layout.setContentsMargins(15, 10, 15, 8)
            top_header_layout.addWidget(self.theme_main_tab_container)
            top_header_layout.addStretch(1)

            right_controls = QHBoxLayout()
            right_controls.setContentsMargins(0, 0, 0, 0)
            right_controls.setSpacing(10)
            right_controls.addWidget(self.theme_switcher_page.tab_container)
            right_controls.addWidget(self.sync_container)
            right_controls.addWidget(self.theme_save_button)
            right_controls.addWidget(self.theme_reset_button)

            top_header_layout.addLayout(right_controls)
            self.theme_layout.addLayout(top_header_layout)

            self.theme_stacked_widget = QStackedWidget()
            self.theme_stacked_widget.setObjectName("themeStackedWidget")
            self.theme_stacked_widget.setStyleSheet("QStackedWidget#themeStackedWidget { background-color: #121212; border: none; }")
            self.theme_stacked_widget.addWidget(self.theme_switcher_page)
            self.theme_stacked_widget.addWidget(self.editor_placeholder)
            self.theme_stacked_widget.addWidget(self.mouse_placeholder)
            self.theme_layout.addWidget(self.theme_stacked_widget)

            self.theme_switcher_page.status_message_requested.connect(self.show_sync_status)

            def on_save_clicked():
                if hasattr(self, 'theme_switcher_page') and self.theme_switcher_page:
                    self.theme_switcher_page.save_selection()
                if getattr(self, '_theme_editor_initialized', False) and self.theme_editor_page:
                    self.theme_editor_page.save_theme()
                if getattr(self, '_cursor_page_initialized', False) and self.cursor_page:
                    self.cursor_page.save_selection()
                self.commit_tinted_icons()
                self.update_snapshot(os.path.join(PROJECT_ROOT, 'imports', 'theme.nss'))
                self.show_sync_status("Changes Saved")

            def on_reset_clicked():
                if hasattr(self, 'theme_switcher_page') and self.theme_switcher_page:
                    self.theme_switcher_page.revert_selection()
                if getattr(self, '_theme_editor_initialized', False) and self.theme_editor_page:
                    self.theme_editor_page.revert_theme()
                if getattr(self, '_cursor_page_initialized', False) and self.cursor_page:
                    self.cursor_page.revert_selection()
                self.revert_tinted_icons()
                self.show_sync_status("Changes Reverted")

            self.theme_save_button.clicked.connect(on_save_clicked)
            self.theme_reset_button.clicked.connect(on_reset_clicked)
            self.theme_switcher_page.theme_applied.connect(self.trigger_global_tint)
            self.theme_switcher_page.reload_requested.connect(self.reload_shell)

            def switch_theme_page_tab(idx):
                if idx == 0:
                    self.themes_tab_btn.setChecked(True)
                elif idx == 1:
                    self.editor_tab_btn.setChecked(True)
                    if not self._theme_editor_initialized:
                        self._theme_editor_initialized = True
                        self.theme_editor_page = ThemeEditorWidget(
                            theme_path=os.path.join(PROJECT_ROOT, 'imports', 'theme.nss'),
                            theme_dir=os.path.join(PROJECT_ROOT, 'theme')
                        )
                        self.theme_stacked_widget.removeWidget(self.editor_placeholder)
                        self.editor_placeholder.deleteLater()
                        self.theme_stacked_widget.insertWidget(1, self.theme_editor_page)
                        self.theme_switcher_page.theme_selected.connect(self.theme_editor_page.reload_theme)
                        self.theme_editor_page.reload_requested.connect(self.reload_shell)
                        self._update_widgets_autosave()
                elif idx == 2:
                    self.mouse_tab_btn.setChecked(True)
                    if not self._cursor_page_initialized:
                        self._cursor_page_initialized = True
                        self.cursor_page = CursorGalleryWidget(
                            cursor_dir=os.path.join(PROJECT_ROOT, 'cursor')
                        )
                        self.theme_stacked_widget.removeWidget(self.mouse_placeholder)
                        self.mouse_placeholder.deleteLater()
                        self.theme_stacked_widget.insertWidget(2, self.cursor_page)
                        right_controls.insertWidget(1, self.cursor_page.tab_container)
                        self.cursor_page.status_message_requested.connect(self.show_sync_status)

                self.theme_stacked_widget.setCurrentIndex(idx)
                self.theme_switcher_page.tab_container.setVisible(idx == 0)
                self.sync_container.setVisible(idx in (0, 1))
                if self._cursor_page_initialized and self.cursor_page:
                    self.cursor_page.tab_container.setVisible(idx == 2)
                self.theme_save_button.setVisible(idx != 2)
                self.theme_reset_button.setVisible(idx != 2)
                if self.theme_stacked_widget.currentWidget():
                    self.theme_stacked_widget.currentWidget().update()

            switch_theme_page_tab(0)

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
        side_panel.setStyleSheet("#sidePanel { background-color: transparent; border-right: none; }")
        side_panel.setFixedWidth(82)
        side_panel_layout = QVBoxLayout(side_panel)
        side_panel_layout.setContentsMargins(8, 12, 8, 12)
        side_panel_layout.setSpacing(14)
        side_panel_layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)

        self.side_btn_group = QButtonGroup(self)
        self.side_btn_group.setExclusive(True)

        def _switch_to_page(page_getter, btn):
            while QApplication.overrideCursor():
                QApplication.restoreOverrideCursor()
            self.unsetCursor()
            btn.setChecked(True)
            w = page_getter()
            self.stacked_widget.setCurrentWidget(w)

        def create_nav_item(icon_name, label_text, page_getter):
            btn = NavTabButton(icon_name, label_text)
            self.side_btn_group.addButton(btn)
            btn.clicked.connect(lambda: _switch_to_page(page_getter, btn))
            return btn

        self.side_plugins_btn = create_nav_item('plugins.png', 'Plugins', lambda: self.plugins_page)
        self.side_modify_btn = create_nav_item('modify.png', 'Modify', lambda: self.get_modify_page())
        self.side_theme_btn = create_nav_item('theme.png', 'Theme', lambda: self.get_theme_page())
        self.side_settings_btn = create_nav_item('Settings.png', 'Settings', lambda: self.get_settings_page())

        self.side_plugins_btn.setChecked(True)

        side_panel_layout.addWidget(self.side_plugins_btn)
        side_panel_layout.addWidget(self.side_modify_btn)
        side_panel_layout.addWidget(self.side_theme_btn)

        side_panel_layout.addStretch()

        side_panel_layout.addWidget(self.side_settings_btn)

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
        is_plugins_page = (self.stacked_widget.currentWidget() == self.plugins_page) if hasattr(self, 'stacked_widget') else True
        if len(local_plugins) > 0 and is_plugins_page:
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
                    card.hide()
                    card.deleteLater()
                    self.icons_loaded.discard(p_name)
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
        card.setFixedHeight(84)
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        card.setMinimumWidth(260)
        card.setCursor(Qt.PointingHandCursor)

        layout = QHBoxLayout(card)
        layout.setContentsMargins(16, 5, 16, 5)
        layout.setSpacing(14)
        layout.setAlignment(Qt.AlignVCenter)

        card.plugin_card_clicked.connect(self.show_details_popup)

        # Floating icon (no background box)
        icon = QLabel()
        icon.setFixedSize(54, 54)
        icon.setScaledContents(True)
        icon.setObjectName("iconLabel")
        icon.setStyleSheet("background: transparent; border: none;")
        icon.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.plugin_icon_labels[plugin_name] = icon
        
        # Immediately use cached pixmap if already in memory
        if plugin_name in self._pixmap_cache and not self._pixmap_cache[plugin_name].isNull():
            icon.setPixmap(self._pixmap_cache[plugin_name])
            self.icons_loaded.add(plugin_name)
        else:
            self.icons_loaded.discard(plugin_name)
            icon.setPixmap(self._default_icon_pixmap)
        layout.addWidget(icon, 0, Qt.AlignVCenter)

        # Text column (Title + Description)
        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(3)
        text_layout.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)

        title = QLabel(plugin_name)
        title.setFont(QFont('Segoe UI Variable Display', 12, QFont.Bold))
        title.setStyleSheet("color: #ffffff; background: transparent;")
        title.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        text_layout.addWidget(title)

        description = QLabel(plugin.get('description', 'No description available.'))
        description.setFont(QFont('Segoe UI Variable Text', 10))
        description.setStyleSheet("color: #8c92a4; background: transparent;")
        description.setWordWrap(True)
        description.setMaximumHeight(38)
        description.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        text_layout.addWidget(description)

        layout.addLayout(text_layout, 1)

        # Action layout (vertical so update button sits below main action)
        action_layout = QVBoxLayout()
        action_layout.setContentsMargins(0, 0, 0, 0)
        action_layout.setSpacing(3)
        action_layout.setAlignment(Qt.AlignVCenter | Qt.AlignRight)
        layout.addLayout(action_layout, 0)

        action_button = CapsuleActionButton('install')
        action_layout.addWidget(action_button)

        self.plugin_cards[plugin_name] = card
        self.plugin_progress_bars[plugin_name] = action_button
        self.plugin_buttons[plugin_name] = action_button
        self.plugin_action_layouts[plugin_name] = action_layout
        self.plugin_description_labels[plugin_name] = description

        self.update_card_ui(plugin_name)
        self.apply_card_style(card)
        return card

    def debounce_check_visible_cards(self):
        self.visible_check_timer.start(50)

    def check_visible_cards(self):
        if not hasattr(self, 'scroll_area') or not self.scroll_area.isVisible():
            return
        scroll_bar = self.scroll_area.verticalScrollBar()
        viewport_top = scroll_bar.value()
        viewport_bottom = viewport_top + self.scroll_area.viewport().height()

        for plugin_name, card in list(self.plugin_cards.items()):
            if plugin_name in self.icons_loaded:
                continue
            card_top = card.y()
            card_bottom = card_top + card.height()
            if card_bottom >= viewport_top - 200 and card_top <= viewport_bottom + 200:
                self.icons_loaded.add(plugin_name)
                if plugin_name in self._pixmap_cache and not self._pixmap_cache[plugin_name].isNull():
                    if plugin_name in self.plugin_icon_labels:
                        self.plugin_icon_labels[plugin_name].setPixmap(self._pixmap_cache[plugin_name])
                else:
                    plugin_data = self.all_plugins_data.get(plugin_name)
                    if plugin_data:
                        self.load_icon(plugin_data)

    def show_details_popup(self, plugin_name, card=None):
        if self.details_popup:
            self.details_popup.close()

        if card is None:
            card = self.plugin_cards.get(plugin_name)
        if not card: return
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
        if getattr(self.details_popup, 'plugin_data', {}).get('name') != plugin_name: return
        plugin_info = self.all_plugins_data.get(plugin_name, {})
        state = self.plugin_logic.registry.get_plugin_state(plugin_name)
        status = state.get('status', 'not_installed')
        is_local = plugin_info.get('_is_local') or status == 'local'
        is_installing = (self.plugin_logic.current_installing_plugin == plugin_name)
        is_queued = plugin_name in [p['name'] for p in self.plugin_logic.installation_queue]

        try: self.details_popup.action_button.clicked.disconnect()
        except TypeError: pass

        if is_installing:
            self.details_popup.action_button.set_state('installing')
            self.details_popup.action_button.clicked.connect(lambda: self.cancel_operation(plugin_name))
        elif is_queued:
            self.details_popup.action_button.set_state('queued')
            self.details_popup.action_button.clicked.connect(lambda: self.cancel_operation(plugin_name))
        elif is_local:
            self.details_popup.action_button.set_state('delete')
            self.details_popup.action_button.clicked.connect(lambda: self.confirm_delete_local_plugin(plugin_name))
        elif status == 'update_available':
            self.details_popup.action_button.set_state('update')
            self.details_popup.action_button.clicked.connect(lambda: self.add_to_installation_queue(plugin_name))
        elif status in ('installed', 'delisted'):
            self.details_popup.action_button.set_state('uninstall')
            self.details_popup.action_button.clicked.connect(lambda: self.uninstall_plugin(plugin_name))
        else:
            self.details_popup.action_button.set_state('install')
            self.details_popup.action_button.clicked.connect(lambda: self.add_to_installation_queue(plugin_name))

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

        action_button.setVisible(True)

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

        if is_installing:
            action_button.set_height(34)
            action_button.set_compact(False)
            action_button.set_state('installing')
            action_button.setEnabled(True)
            action_button.clicked.connect(lambda: self.cancel_operation(plugin_name))
        elif is_queued:
            action_button.set_height(34)
            action_button.set_compact(False)
            action_button.set_state('queued')
            action_button.setEnabled(True)
            action_button.clicked.connect(lambda: self.cancel_operation(plugin_name))
        elif is_local:
            action_button.set_state('delete')
            action_button.setEnabled(True)
            action_button.clicked.connect(lambda: self.confirm_delete_local_plugin(plugin_name))

            plugin_dir = os.path.join(PLUGINS_DIR, plugin_name)
            nss_enabled = is_plugin_nss_enabled(plugin_name, plugin_dir)
            if nss_enabled is not None:
                toggle_btn = CapsuleActionButton('disable' if nss_enabled else 'enable', height=34)
                action_button.set_height(34)
                action_button.set_compact(False)
                toggle_btn.set_compact(False)
                if nss_enabled:
                    toggle_btn.clicked.connect(lambda: self.disable_local_plugin(plugin_name))
                else:
                    toggle_btn.clicked.connect(lambda: self.enable_local_plugin(plugin_name))
                action_layout.addWidget(toggle_btn)
                self.plugin_update_buttons[plugin_name] = toggle_btn
            else:
                action_button.set_height(34)
                action_button.set_compact(False)
        elif is_delisted:
            action_button.set_height(34)
            action_button.set_compact(False)
            action_button.set_state('uninstall')
            action_button.setEnabled(True)
            action_button.clicked.connect(lambda: self.uninstall_plugin(plugin_name))
        elif is_installed:
            action_button.set_state('uninstall')
            action_button.setEnabled(True)
            action_button.clicked.connect(lambda: self.uninstall_plugin(plugin_name))
            
            if has_update:
                update_button = CapsuleActionButton('update', height=34)
                action_button.set_height(34)
                action_button.set_compact(False)
                update_button.set_compact(False)
                update_button.clicked.connect(lambda: self.add_to_installation_queue(plugin_name))
                action_layout.addWidget(update_button)
                self.plugin_update_buttons[plugin_name] = update_button
            else:
                action_button.set_height(34)
                action_button.set_compact(False)
        else:
            action_button.set_height(34)
            action_button.set_compact(False)
            action_button.set_state('install')
            action_button.setEnabled(True)
            action_button.clicked.connect(lambda: self.add_to_installation_queue(plugin_name))

        if self.details_popup and getattr(self.details_popup, 'plugin_data', {}).get('name') == plugin_name:
            self.update_popup_button(plugin_name)

    def on_icon_loaded(self, plugin_name, pixmap):
        is_default = bool(self._default_icon_pixmap and pixmap and pixmap.cacheKey() == self._default_icon_pixmap.cacheKey())
        if pixmap and not pixmap.isNull() and not is_default:
            self._pixmap_cache[plugin_name] = pixmap
        if plugin_name in self.plugin_icon_labels:
            label = self.plugin_icon_labels[plugin_name]
            if plugin_name in self._pixmap_cache and not self._pixmap_cache[plugin_name].isNull():
                label.setPixmap(self._pixmap_cache[plugin_name])
            elif pixmap and not pixmap.isNull():
                label.setPixmap(pixmap)
            else:
                label.setPixmap(self._default_icon_pixmap)

    def load_icon(self, plugin):
        self.plugin_logic.load_icon(plugin)

    def add_to_installation_queue(self, plugin_name):
        if plugin_name in [p['name'] for p in self.plugin_logic.installation_queue] or self.plugin_logic.current_installing_plugin == plugin_name:
            return
            
        self.plugin_logic.add_to_installation_queue(plugin_name)
        self.update_card_ui(plugin_name)
        if self.details_popup and getattr(self.details_popup, 'plugin_data', {}).get('name') == plugin_name:
            self.update_popup_button(plugin_name)

    def on_install_progress(self, plugin_name, value):
        if plugin_name == self.plugin_logic.current_installing_plugin:
            if plugin_name in self.plugin_buttons:
                self.plugin_buttons[plugin_name].setValue(value)
            if self.details_popup and getattr(self.details_popup, 'plugin_data', {}).get('name') == plugin_name:
                self.details_popup.action_button.setValue(value)

    def on_operation_error(self, plugin_name, status, error_message):
        print(f"Operation error for {plugin_name}: {error_message}")
        if plugin_name in self.plugin_buttons:
            self.plugin_buttons[plugin_name].setValue(0)
            self.plugin_buttons[plugin_name].setVisible(True)

        self.update_card_ui(plugin_name)

        if self.details_popup and getattr(self.details_popup, 'plugin_data', {}).get('name') == plugin_name:
            self.details_popup.action_button.setValue(0)
            self.update_popup_button(plugin_name)
            self.details_popup.set_details_content(f"<font color='red'>Error: {error_message}</font>")
        elif not getattr(self, '_error_dialog_visible', False):
            self._error_dialog_visible = True
            msgBox = ModernDialog(self, title=f"Error for {plugin_name}", text=error_message)
            msgBox.add_button("OK", "installButton", msgBox.accept)
            msgBox.finished.connect(lambda: setattr(self, '_error_dialog_visible', False))
            msgBox.show()

    def on_operation_finished(self, plugin_name, status):
        if plugin_name in self.plugin_buttons:
            self.plugin_buttons[plugin_name].setValue(0)
            self.plugin_buttons[plugin_name].setVisible(True)

        self.update_card_ui(plugin_name)
        if self.details_popup and getattr(self.details_popup, 'plugin_data', {}).get('name') == plugin_name:
            self.details_popup.action_button.setValue(0)
            self.update_popup_button(plugin_name)

        if status == "installed" or status == "uninstalled":
            self.reload_shell()

    def cancel_operation(self, plugin_name):
        self.plugin_logic.cancel_operation(plugin_name)
        if plugin_name in self.plugin_buttons:
            self.plugin_buttons[plugin_name].setValue(0)
            self.plugin_buttons[plugin_name].setVisible(True)
        self.update_card_ui(plugin_name)
        if self.details_popup and getattr(self.details_popup, 'plugin_data', {}).get('name') == plugin_name:
            self.details_popup.action_button.setValue(0)
            self.update_popup_button(plugin_name)

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
        self.update_card_ui(plugin_name)
        if self.details_popup and getattr(self.details_popup, 'plugin_data', {}).get('name') == plugin_name:
            self.update_popup_button(plugin_name)

    def apply_card_style(self, card):
        card.setStyleSheet("""
            QFrame#plugin_card {
                background-color: rgba(255, 255, 255, 0.035);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 16px;
            }
            QFrame#plugin_card:hover {
                background-color: rgba(255, 255, 255, 0.065);
                border: 1px solid rgba(255, 255, 255, 0.18);
            }
        """)

    def nativeEvent(self, event_type, message):
        if event_type == "windows_generic_MSG":
            msg = wintypes.MSG.from_address(message.__int__())
            WM_NCHITTEST = 0x0084
            WM_NCCALCSIZE = 0x0083
            HTCAPTION = 2
            HTLEFT = 10
            HTRIGHT = 11
            HTTOP = 12
            HTTOPLEFT = 13
            HTTOPRIGHT = 14
            HTBOTTOM = 15
            HTBOTTOMLEFT = 16
            HTBOTTOMRIGHT = 17

            if msg.message == WM_NCHITTEST:
                x, y = msg.pt.x, msg.pt.y
                pos = self.mapFromGlobal(QPoint(x, y))
                lx, ly = pos.x(), pos.y()
                w, h = self.width(), self.height()

                # Sizing borders: NEVER return resize hit codes when maximized!
                if not self.isMaximized():
                    child = self.childAt(lx, ly)
                    is_interactive = False
                    curr = child
                    while curr and curr is not self:
                        if (curr.inherits("QAbstractButton") or 
                            curr.inherits("QLineEdit") or 
                            curr.inherits("QComboBox") or 
                            curr.inherits("QTabBar") or 
                            curr.inherits("QSlider") or 
                            curr.inherits("QScrollBar") or
                            curr.objectName() in ("navTabButton", "pillTabContainer", "sidePanel")):
                            is_interactive = True
                            break
                        curr = curr.parentWidget()

                    if not is_interactive:
                        border = 8
                        if lx < border:
                            if ly < border: return True, HTTOPLEFT
                            if ly > h - border: return True, HTBOTTOMLEFT
                            return True, HTLEFT
                        if lx > w - border:
                            if ly < border: return True, HTTOPRIGHT
                            if ly > h - border: return True, HTBOTTOMRIGHT
                            return True, HTRIGHT
                        if ly < border: return True, HTTOP
                        if ly > h - border: return True, HTBOTTOM

                # Title bar drag: only at the top and never over interactive controls
                if ly < 45:
                    child = self.childAt(lx, ly)
                    curr = child
                    while curr and curr is not self:
                        if (curr.inherits("QAbstractButton") or 
                            curr.inherits("QLineEdit") or 
                            curr.inherits("QComboBox") or 
                            curr.inherits("QTabBar") or
                            curr.objectName() in ("navTabButton", "windowControlsPill")):
                            return False, 0
                        curr = curr.parentWidget()
                    return True, HTCAPTION

                return False, 0

            elif msg.message == WM_NCCALCSIZE:
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
                except Exception:
                    pass
                self.update()

            elif msg.message == 0x0232:  # WM_EXITSIZEMOVE
                try:
                    wid = self.winId()
                    if wid:
                        hwnd = int(wid)
                        ctypes.windll.user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, 0x0002 | 0x0001 | 0x0004 | 0x0020)
                except Exception:
                    pass
                self.update()

        return super().nativeEvent(event_type, message)

    def showEvent(self, event):
        self._apply_rounded_mask()
        super().showEvent(event)

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() in (QEvent.WindowStateChange, QEvent.StyleChange):
            self._apply_rounded_mask()
            self.update()

    def _apply_rounded_mask(self):
        """Clip window to rounded rect at OS level when not maximized."""
        if self.isMaximized():
            self.clearMask()
            return
        radius = getattr(self, '_corner_radius', 28)
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), radius, radius)
        self.setMask(QRegion(path.toFillPolygon().toPolygon()))

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor("#121212"))
        painter.setPen(Qt.NoPen)
        if self.isMaximized():
            painter.drawRect(self.rect())
        else:
            radius = getattr(self, '_corner_radius', 28)
            painter.drawRoundedRect(self.rect(), radius, radius)

    def closeEvent(self, event):
        self._is_shutting_down = True
        has_editor_dirty = getattr(self, 'theme_editor_page', None) and getattr(self.theme_editor_page, 'is_dirty', False)
        has_switcher_dirty = getattr(self, 'theme_switcher_page', None) and getattr(self.theme_switcher_page, 'is_dirty', False)
        has_modify_dirty = getattr(self, 'modify_page', None) and getattr(self.modify_page, 'is_dirty', False)

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
                if getattr(self, 'theme_editor_page', None): self.theme_editor_page.save_theme()
                if getattr(self, 'theme_switcher_page', None): self.theme_switcher_page.save_theme()
                self.commit_tinted_icons()
                if has_modify_dirty:
                    self.modify_page.save_all_modifications()
                    self.modify_page.save_ids()
            elif res == 0: # No
                # Synchronously revert each dirty widget back to last saved state
                if has_switcher_dirty and getattr(self, 'theme_switcher_page', None):
                    self.theme_switcher_page.revert_changes()
                if has_editor_dirty and getattr(self, 'theme_editor_page', None):
                    self.theme_editor_page.revert_theme()
                self.revert_tinted_icons()
                if has_modify_dirty and getattr(self, 'modify_page', None):
                    self.modify_page.revert_changes()

                # Synchronously restore any other modified files from global snapshot
                snapshot = getattr(self, 'nss_snapshot', {})
                from utils import safe_file_write
                for fp, content in snapshot.items():
                    if os.path.exists(fp):
                        try:
                            with open(fp, 'r', encoding='utf-8') as f:
                                current = f.read()
                            if current != content:
                                safe_file_write(fp, content)
                        except: pass
                
                prev_dir = os.path.join(PROJECT_ROOT, 'imports', 'icons', 'preview')
                if os.path.exists(prev_dir):
                    try: shutil.rmtree(prev_dir)
                    except: pass
                from modify_widget import cleanup_orphan_icons
                cleanup_orphan_icons(PROJECT_ROOT)
                
                if getattr(self, 'theme_editor_page', None): self.theme_editor_page.is_dirty = False
                if getattr(self, 'theme_switcher_page', None): self.theme_switcher_page.is_dirty = False
                if getattr(self, 'modify_page', None): self.modify_page.is_dirty = False

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

        from modify_widget import scan_nss_items, _extract_glyph_codes, _extract_all_colors, ManualSyncConflictDialog, GlobalTintWorker
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

        # Determine current theme image config (mode, colors)
        theme_nss = os.path.join(PROJECT_ROOT, 'imports', 'theme.nss')
        mode = "gradient"
        colors = ["#ffffff", "#ffffff"]
        try:
            theme_data = getattr(self.theme_editor_page, 'theme_data', {}) if getattr(self, 'theme_editor_page', None) else {}
            raw_c = theme_data.get('image.color')
            raw_eff = str(theme_data.get('image.effect', '0')).strip().lower()
            
            if not raw_c and os.path.exists(theme_nss):
                with open(theme_nss, 'r', encoding='utf-8-sig', errors='replace') as f:
                    content = f.read()
                m_c = re.search(r'image\.color\s*=\s*\[?\s*(#[0-9A-Fa-f]{3,8})\s*(?:,\s*(#[0-9A-Fa-f]{3,8}))?\s*\]?', content)
                if m_c:
                    colors = [m_c.group(1)]
                    if m_c.group(2): colors.append(m_c.group(2))
                m_eff = re.search(r'image\.effect\s*=\s*([0-9a-zA-Z]+)', content)
                if m_eff:
                    raw_eff = m_eff.group(1).lower()
            elif raw_c:
                c_matches = re.findall(r'#[0-9A-Fa-f]{3,8}', raw_c)
                if c_matches:
                    colors = c_matches
                    
            if raw_eff in ('2', 'rainbow') or any('rainbow' in str(c).lower() for c in colors):
                mode = 'rainbow'
            elif raw_eff in ('1', 'gradient') or (len(colors) >= 2 and colors[0].lower() != colors[1].lower()):
                mode = 'gradient'
            else:
                mode = 'solid'
        except Exception:
            pass

        if hasattr(self, 'sync_label'):
            self.sync_label.setText("Syncing...")
        if hasattr(self, 'theme_sync_button'):
            self.theme_sync_button.setEnabled(False)
        self.show_sync_status(f"Syncing {mode.title()} colors...")

        thread = QThread()
        worker = GlobalTintWorker(PROJECT_ROOT, mode, colors, skip_manual_keys)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)

        def on_tint_progress(v, t):
            if hasattr(self, 'sync_label'):
                self.sync_label.setText(f"Syncing {v}/{t}")
            if hasattr(self, 'title_status_label'):
                self.title_status_label.setText(f"Syncing {mode.title()} colors ({v}/{t})...")

        def on_tint_finished():
            if hasattr(self, 'sync_label'):
                self.sync_label.setText("Sync Colors")
            if hasattr(self, 'theme_sync_button'):
                self.theme_sync_button.setEnabled(True)
            self.show_sync_status("Colors Synced")
            if hasattr(self, 'modify_page'):
                self.modify_page.refresh_ui()

        worker.progress.connect(on_tint_progress)
        worker.finished.connect(thread.quit)
        worker.finished.connect(on_tint_finished)
        worker.finished.connect(lambda: self._active_tint_threads.remove((thread, worker)) if (thread, worker) in self._active_tint_threads else None)
        worker.finished.connect(self.reload_shell)
        thread.finished.connect(thread.deleteLater)
        self._active_tint_threads.append((thread, worker))
        thread.start()

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
        
        self.update_btn = PillPushButton("Check for Update", "primary", height=34)
        self.update_btn.setFixedWidth(140)
        self.update_btn.setFocusPolicy(Qt.NoFocus)
        self.update_btn.clicked.connect(lambda: self.check_app_update(manual=True))
        header.addWidget(self.update_btn)
        layout.addLayout(header)
        layout.addSpacing(10)

        self.auto_update_sw = self._create_setting_row(layout, "Auto Update Plugins", "Automatically install updates on startup", "auto_update")
        self.auto_check_sw = self._create_setting_row(layout, "Auto Check Updates", "Show notification when updates are available", "auto_check_updates")
        
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
        worker.check_finished.connect(worker.deleteLater)
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
                self.ver_label.setText(f"Current: {VERSION} | <span style='color: #e78284;'>Latest: {latest_version}</span>")
                title = 'Re-install Launcher' if force else 'Update Available'
                msg = f"Re-install iMA Menu Launcher <b>v{latest_version}</b> now?" if force else f"A new version of iMA Menu Launcher is available: <b>v{latest_version}</b><br><br>Would you like to download and install it now?"
                btn_txt = 'Re-install Now' if force else 'Update Now'
                dialog = ModernDialog(self, title, msg)
                dialog.add_button(btn_txt, 'installButton', lambda: dialog.done(1))
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
                if download_url:
                    self.on_check_finished(True, latest_version or VERSION, download_url, manual=True, force=True)
                else:
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

        def _on_cancel():
            if hasattr(self, 'dl_worker') and self.dl_worker:
                self.dl_worker.cancel()
            self.dl_msg.reject()

        self.dl_msg.add_button("Cancel", "uninstallButton", _on_cancel)

        self.dl_thread = QThread(self)
        self.dl_worker = UpdateWorker()
        self.dl_worker.moveToThread(self.dl_thread)
        self.dl_thread.started.connect(lambda: self.dl_worker.download_update(download_url))
        self.dl_worker.download_progress.connect(self._update_dl_progress)
        self.dl_worker.download_finished.connect(self.on_download_finished)
        self.dl_worker.download_finished.connect(self.dl_thread.quit)
        self.dl_thread.finished.connect(self.dl_thread.deleteLater)
        self.dl_thread.finished.connect(self.dl_worker.deleteLater)
        self.dl_thread.start()
        self.dl_msg.exec_()

    def _update_dl_progress(self, val):
        self.dl_bar.setValue(val)
        self.percent_label.setText(f"{val}%")
        QApplication.processEvents()

    def on_download_finished(self, success, result):
        if hasattr(self, 'dl_worker') and self.dl_worker and getattr(self.dl_worker, '_is_cancelled', False):
            return
        if not self.dl_msg.isVisible():
            return
        self.dl_msg.accept()
        if success:
            self.apply_app_update(result)
        elif "cancelled" not in str(result).lower():
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
            self.hide()
            self.plugin_logic.stop_all_threads()
            QApplication.closeAllWindows()
            QApplication.quit()
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
        if getattr(self, 'modify_page', None): self.modify_page.auto_save = enabled
        if getattr(self, 'theme_switcher_page', None): self.theme_switcher_page.auto_save = enabled
        if getattr(self, 'theme_editor_page', None): self.theme_editor_page.auto_save = enabled

    def _create_import_row(self, layout):
        row = QFrame(); row.setStyleSheet("QFrame { background: rgba(255,255,255,0.04); border-radius: 15px; border: 1px solid rgba(255,255,255,0.05); } QFrame:hover { background: rgba(255,255,255,0.06); }")
        rl = QHBoxLayout(row); rl.setContentsMargins(20, 15, 20, 15)
        v = QVBoxLayout(); t = QLabel("Import NSS Files"); t.setStyleSheet("color: white; font-size: 15px; font-weight: bold; border: none; background: transparent;")
        d = QLabel("Copy external files to imports and shell.nss"); d.setStyleSheet("color: #b0b0b0; font-size: 12px; border: none; background: transparent;")
        v.addWidget(t); v.addWidget(d); rl.addLayout(v); rl.addStretch()
        
        edit_btn = QPushButton("\uE104"); edit_btn.setFixedSize(36, 36); edit_btn.setCursor(Qt.PointingHandCursor)
        edit_btn.setFont(QFont('Segoe MDL2 Assets', 14))
        edit_btn.setStyleSheet("QPushButton { background: rgba(255,255,255,0.05); border-radius: 18px; border: 1px solid rgba(255,255,255,0.1); color: #b0b0b0; } QPushButton:hover { background: rgba(231, 130, 132, 0.2); border: 1px solid #e78284; color: white; }")
        edit_btn.clicked.connect(self.show_imports_manager)
        
        btn = PillPushButton("Import", "primary", height=34)
        btn.setFixedWidth(100)
        btn.clicked.connect(self.import_nss_files)
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
                del_btn.setStyleSheet("QPushButton { background: transparent; border: none; color: #b0b0b0; } QPushButton:hover { color: #e78284; }")
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
        self._init_sync_manager()
        row = QFrame(); row.setStyleSheet("QFrame { background: rgba(255,255,255,0.04); border-radius: 15px; border: 1px solid rgba(255,255,255,0.05); } QFrame:hover { background: rgba(255,255,255,0.06); }")
        rl = QHBoxLayout(row); rl.setContentsMargins(20, 15, 20, 15)
        v = QVBoxLayout(); t = QLabel("Google Drive Sync"); t.setStyleSheet("color: white; font-size: 15px; font-weight: bold; border: none; background: transparent;")
        user_email = self.sync_manager.user_email if self.sync_manager else ""
        self.sync_status_label = QLabel("Not logged in" if not user_email else f"Logged in as {user_email}")
        self.sync_status_label.setStyleSheet("color: #b0b0b0; font-size: 12px; border: none; background: transparent;")
        v.addWidget(t); v.addWidget(self.sync_status_label); rl.addLayout(v); rl.addStretch()
        
        self.sync_login_btn = PillPushButton("Login", "primary", height=34)
        self.sync_login_btn.setFixedWidth(100)
        self.sync_login_btn.clicked.connect(lambda: self._init_sync_manager().login())
        
        self.sync_backup_btn = PillPushButton("Backup", "backup", height=34)
        self.sync_backup_btn.setFixedWidth(100)
        self.sync_backup_btn.clicked.connect(lambda: self._init_sync_manager().backup())
        
        self.sync_restore_btn = PillPushButton("Restore", "restore", height=34)
        self.sync_restore_btn.setFixedWidth(100)
        self.sync_restore_btn.clicked.connect(lambda: self._init_sync_manager().restore())
        
        self.sync_logout_btn = QPushButton("\uE77B"); self.sync_logout_btn.setFixedSize(36, 36); self.sync_logout_btn.setCursor(Qt.PointingHandCursor)
        self.sync_logout_btn.setFont(QFont('Segoe MDL2 Assets', 14))
        self.sync_logout_btn.setStyleSheet("QPushButton { background: rgba(255,255,255,0.05); border-radius: 18px; border: 1px solid rgba(255,255,255,0.1); color: #b0b0b0; } QPushButton:hover { background: rgba(234, 153, 156, 0.2); border: 1px solid #e78284; color: white; }")
        self.sync_logout_btn.clicked.connect(self.show_account_profile_popup)
        
        rl.addWidget(self.sync_login_btn); rl.addWidget(self.sync_backup_btn); rl.addWidget(self.sync_restore_btn); rl.addWidget(self.sync_logout_btn)
        layout.addWidget(row)
        self._update_sync_ui_state()

    def _get_profile_pixmap(self, size=36):
        if not self.sync_manager:
            return None
        avatar_path = os.path.join(PROJECT_ROOT, 'cache', 'profile_avatar.png')
        if os.path.exists(avatar_path):
            pix = QPixmap(avatar_path)
            if not pix.isNull():
                return make_circular_pixmap(pix, size)
        
        if self.sync_manager.access_token:
            if hasattr(self.sync_manager, 'fetch_user_profile'):
                self.sync_manager.fetch_user_profile(background=True)
            init_char = (self.sync_manager.user_name or self.sync_manager.user_email or "U")[:1]
            return make_initial_avatar_pixmap(init_char, size)
        return None

    def show_account_profile_popup(self):
        if not self.sync_manager or not self.sync_manager.access_token:
            return
        user_name = self.sync_manager.user_name or ""
        user_email = self.sync_manager.user_email or ""
        if not user_name and user_email:
            user_name = user_email.split('@')[0]
        avatar_pix = self._get_profile_pixmap(size=76)
        dlg = AccountProfileDialog(self, user_name, user_email, avatar_pix)
        if dlg.exec_() == 1:
            self._handle_sync_logout()

    def _handle_sync_logout(self):
        if self._init_sync_manager():
            self.sync_manager.logout()
        self._update_sync_ui_state()

    def _update_sync_ui_state(self):
        if not hasattr(self, 'sync_login_btn') or self.sync_manager is None:
            return
        logged_in = self.sync_manager.access_token is not None
        self.sync_login_btn.setVisible(not logged_in)
        self.sync_backup_btn.setVisible(logged_in)
        self.sync_restore_btn.setVisible(logged_in)
        self.sync_logout_btn.setVisible(logged_in)
        
        if logged_in:
            user_name = self.sync_manager.user_name or ""
            user_email = self.sync_manager.user_email or ""
            display_str = f"Logged in as {user_name} ({user_email})" if user_name and user_email else f"Logged in as {user_email or user_name}"
            self.sync_status_label.setText(display_str)
            
            avatar_pix = self._get_profile_pixmap(size=36)
            if avatar_pix and not avatar_pix.isNull():
                self.sync_logout_btn.setText("")
                self.sync_logout_btn.setIcon(QIcon(avatar_pix))
                self.sync_logout_btn.setIconSize(QSize(36, 36))
                self.sync_logout_btn.setStyleSheet("QPushButton { background: transparent; border-radius: 18px; border: 1.5px solid rgba(255,255,255,0.25); padding: 0px; } QPushButton:hover { border: 1.5px solid #e78284; }")
            else:
                self.sync_logout_btn.setIcon(QIcon())
                self.sync_logout_btn.setText("\uE77B")
                self.sync_logout_btn.setFont(QFont('Segoe MDL2 Assets', 14))
                self.sync_logout_btn.setStyleSheet("QPushButton { background: rgba(255,255,255,0.05); border-radius: 18px; border: 1px solid rgba(255,255,255,0.1); color: #b0b0b0; } QPushButton:hover { background: rgba(234, 153, 156, 0.2); border: 1px solid #e78284; color: white; }")
            
            tip = f"{user_name}\n{user_email}".strip() if user_name else user_email
            self.sync_logout_btn.setToolTip(tip or "Google Account Profile")
        else:
            self.sync_status_label.setText("Not logged in")
            self.sync_logout_btn.setIcon(QIcon())
            self.sync_logout_btn.setText("\uE77B")
            self.sync_logout_btn.setStyleSheet("QPushButton { background: rgba(255,255,255,0.05); border-radius: 18px; border: 1px solid rgba(255,255,255,0.1); color: #b0b0b0; } QPushButton:hover { background: rgba(234, 153, 156, 0.2); border: 1px solid #e78284; color: white; }")
            self.sync_logout_btn.setToolTip("")

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
            self.sync_perc = QLabel("0%"); self.sync_perc.setStyleSheet("color: #e78284; font-size: 12px; font-weight: bold; background: transparent;"); self.sync_perc.setAlignment(Qt.AlignCenter)
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

        # Single instance check
        try:
            kernel32 = ctypes.windll.kernel32
            user32 = ctypes.windll.user32

            _single_instance_mutex = kernel32.CreateMutexW(None, False, SINGLE_INSTANCE_MUTEX_NAME)
            last_err = kernel32.GetLastError()
            ERROR_ALREADY_EXISTS = 183

            if last_err == ERROR_ALREADY_EXISTS:
                try:
                    user32.AllowSetForegroundWindow(0xFFFFFFFF)
                except Exception:
                    pass

                msg_id = user32.RegisterWindowMessageW(SINGLE_INSTANCE_MSG_NAME)
                if msg_id:
                    user32.PostMessageW(0xFFFF, msg_id, 0, 0)

                try:
                    hwnd = user32.FindWindowW(None, "iMA Menu")
                    if hwnd:
                        user32.ShowWindow(hwnd, 9)
                        user32.BringWindowToTop(hwnd)
                        user32.SetForegroundWindow(hwnd)
                        user32.SwitchToThisWindow(hwnd, True)
                except Exception:
                    pass

                sys.exit(0)
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

    if os.name == 'nt':
        try:
            msg_id = ctypes.windll.user32.RegisterWindowMessageW(SINGLE_INSTANCE_MSG_NAME)
            if msg_id:
                native_filter = SingleInstanceNativeFilter(manager, msg_id)
                app.installNativeEventFilter(native_filter)
        except Exception:
            pass

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