import sys
import os
import requests
import threading
import json
import shutil
import zipfile
import re
import base64
import subprocess
import winreg
from collections import deque
import markdown
from PyQt5.QtWidgets import (QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QGridLayout,
                             QScrollArea, QGraphicsDropShadowEffect, QProgressBar, QTextBrowser, QStackedWidget, QTabWidget, QDialog, QDialogButtonBox)
from PyQt5.QtGui import QColor, QPixmap, QFont, QPainter, QPainterPath, QPen, QTextOption, QIcon
from PyQt5.QtCore import Qt, pyqtSignal, QObject, QThread, QTimer, QPropertyAnimation, QEasingCurve, QSize, QEvent
from modify_widget import ModifyWidget, CustomMessageBox
from theme_switcher_widget import ThemeSwitcherWidget
from theme_editor_widget import ThemeEditorWidget
from utils import resource_path, safe_file_write
import ctypes

_GITHUB_REPO = "iMAboud/iMA-Menu-Plugins"
GITHUB_PLUGINS_JSON_URL = f"https://raw.githubusercontent.com/{_GITHUB_REPO}/main/plugins.json"
GITHUB_API_BASE_URL = f"https://api.github.com/repos/{_GITHUB_REPO}"
GITHUB_RELEASES_API_URL = f"{GITHUB_API_BASE_URL}/releases/latest"
REQUEST_TIMEOUT = 15

def get_app_base_path():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))

APP_BASE_PATH = get_app_base_path()
PROJECT_ROOT = os.path.abspath(os.path.join(APP_BASE_PATH, '..'))

PLUGINS_DIR = os.path.join(PROJECT_ROOT, 'plugins')
LIB_DIR = os.path.join(APP_BASE_PATH, 'lib')
CACHE_DIR = os.path.join(APP_BASE_PATH, 'cache')
PLUGINS_CACHE_FILE = os.path.join(CACHE_DIR, 'plugins.json')
ICONS_CACHE_DIR = os.path.join(CACHE_DIR, 'icons')


DEFAULT_ICON_PATH = resource_path('icon.ico')


def get_auth_headers(token):
    return {'Authorization': f'token {token}'} if token else {}

def resolve_path(path_str):
    resolved_path_str = os.path.expandvars(path_str.replace('/', os.sep))
    if not os.path.isabs(resolved_path_str):
        project_name = os.path.basename(PROJECT_ROOT)
        path_parts = resolved_path_str.split(os.sep)
        if path_parts and path_parts[0] == project_name:
            resolved_path_str = os.path.join(*path_parts[1:])
        return os.path.abspath(os.path.join(PROJECT_ROOT, resolved_path_str))
    return resolved_path_str

def get_plugin_install_path(plugin_data):
    install_path_str = plugin_data.get('install_path')
    if not install_path_str:
        return os.path.join(PLUGINS_DIR, plugin_data['name'])
    return resolve_path(install_path_str)

def add_nss_import(plugin_data):
    nss_file_path = os.path.join(PROJECT_ROOT, 'shell.nss')
    nss_path = resolve_path(plugin_data['nss_path'])
    nss_file = plugin_data['nss_file']
    
    # Make the nss_path relative to the project root for the import statement
    relative_nss_path = os.path.relpath(nss_path, PROJECT_ROOT).replace(os.sep, '/')
    import_statement = f"import \'{relative_nss_path}/{nss_file}\'\n"

    try:
        with open(nss_file_path, 'r') as f:
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

        safe_file_write(nss_file_path, "".join(lines))
    except IOError as e:
        print(f"Error updating shell.nss: {e}")

def remove_nss_import(plugin_data):
    nss_file_path = os.path.join(PROJECT_ROOT, 'shell.nss')
    nss_path = resolve_path(plugin_data['nss_path'])
    nss_file = plugin_data['nss_file']
    relative_nss_path = os.path.relpath(nss_path, PROJECT_ROOT).replace(os.sep, '/')
    import_statement = f"import \'{relative_nss_path}/{nss_file}\'"
    try:
        with open(nss_file_path, 'r') as f:
            lines = f.readlines()
        
        new_lines = [line for line in lines if import_statement not in line]
        
        safe_file_write(nss_file_path, "".join(new_lines))
    except IOError as e:
        print(f"Error updating shell.nss: {e}")

def add_to_path(directory):
    try:
        key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, "Environment")
        current_path, _ = winreg.QueryValueEx(key, "Path")
        winreg.CloseKey(key)

        if directory not in current_path.split(os.pathsep):
            new_path = f"{current_path}{os.pathsep}{directory}"
            key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, "Environment")
            winreg.SetValueEx(key, "Path", 0, winreg.REG_EXPAND_SZ, new_path)
            winreg.CloseKey(key)
            subprocess.run(['powershell', '-command', '[Environment]::SetEnvironmentVariable(\"Path\", \"' + new_path + '\", \"User\")'], check=True)
            print(f"Added {directory} to system PATH.")
        else:
            print(f"{directory} is already in system PATH.")
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
            headers = get_auth_headers(self.token)
            response = requests.get(GITHUB_PLUGINS_JSON_URL, headers=headers, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            plugins = response.json()

            with open(PLUGINS_CACHE_FILE, 'w') as f:
                json.dump(plugins, f, indent=4)

            self.finished.emit(plugins)
        except Exception as e:
            self.error.emit(str(e))

class IconDownloadWorker(QObject):
    finished = pyqtSignal(str, QPixmap)
    error = pyqtSignal(str)

    def __init__(self, plugin_name, url, save_path, headers):
        super().__init__()
        self.plugin_name = plugin_name
        self.url = url
        self.save_path = save_path
        self.headers = headers

    def run(self):
        pixmap = None
        try:
            response = requests.get(self.url, headers=self.headers, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            pixmap = QPixmap()
            pixmap.loadFromData(response.content)
            if not pixmap.isNull():
                pixmap.save(self.save_path)
            self.finished.emit(self.plugin_name, pixmap)
        except Exception as e:
            print(f"Error downloading icon for {self.plugin_name}: {e}")
            pixmap = None
            self.error.emit(str(e))

class InstallationWorker(QObject):
    progress = pyqtSignal(str, int)
    finished = pyqtSignal(str, str)
    error = pyqtSignal(str, str, str)

    def __init__(self, plugin_data, headers):
        super().__init__()
        self.plugin_data = plugin_data
        self.plugin_name = plugin_data['name']
        self.headers = headers
        self._is_cancelled = False
        self.files_to_download = []

    def run(self):
        try:
            target_plugin_dir = get_plugin_install_path(self.plugin_data)

            branch_url = f"{GITHUB_API_BASE_URL}/branches/main"
            branch_res = requests.get(branch_url, headers=self.headers, timeout=REQUEST_TIMEOUT)
            branch_res.raise_for_status()
            root_tree_sha = branch_res.json()['commit']['commit']['tree']['sha']

            trees_api_url = f"{GITHUB_API_BASE_URL}/git/trees/{root_tree_sha}?recursive=true"
            tree_res = requests.get(trees_api_url, headers=self.headers, timeout=REQUEST_TIMEOUT)
            tree_res.raise_for_status()
            tree_data = tree_res.json()

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
                    self.files_to_download.append({'url': download_url, 'path': relative_path})
            
            if not self.files_to_download:
                 raise Exception(f"Could not find any files for plugin '{self.plugin_name}' in the repository.")

            if self._is_cancelled:
                self.finished.emit(self.plugin_name, "cancelled")
                return

            self.download_files(target_plugin_dir, self.headers)
            if self._is_cancelled:
                if os.path.exists(target_plugin_dir):
                    shutil.rmtree(target_plugin_dir)
                self.finished.emit(self.plugin_name, "cancelled")
                return

            if 'dependencies' in self.plugin_data:
                self.progress.emit(self.plugin_name, 0)
                self.download_dependencies(self.plugin_data['dependencies'], self.headers)
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

            add_nss_import(self.plugin_data)
            self.finished.emit(self.plugin_name, "installed")
        except Exception as e:
            self.error.emit(self.plugin_name, "failed", str(e))

    def download_files(self, target_plugin_dir, headers):
        if os.path.exists(target_plugin_dir): shutil.rmtree(target_plugin_dir)
        os.makedirs(target_plugin_dir)

        total_files = len(self.files_to_download)
        for i, file_info in enumerate(self.files_to_download):
            if self._is_cancelled:
                return

            relative_path = file_info['path']
            local_path = os.path.join(target_plugin_dir, relative_path)
            os.makedirs(os.path.dirname(local_path), exist_ok=True)

            try:
                response = requests.get(file_info['url'], headers=headers, timeout=REQUEST_TIMEOUT)
                response.raise_for_status()
                with open(local_path, 'wb') as f:
                    f.write(response.content)
            except Exception as e:
                shutil.rmtree(target_plugin_dir)
                raise e

            progress_val = int(((i + 1) / total_files) * 100)
            self.progress.emit(self.plugin_name, progress_val)

    def download_dependencies(self, dependencies, headers):
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
                response = requests.get(GITHUB_RELEASES_API_URL, headers=headers, timeout=REQUEST_TIMEOUT)
                response.raise_for_status()
                release_data = response.json()

                asset_url = None
                for asset in release_data['assets']:
                    if asset['name'] == dep_name:
                        asset_url = asset['browser_download_url']
                        break
                
                if not asset_url:
                    raise Exception(f"Dependency {dep_name} not found in latest release assets.")

                dep_response = requests.get(asset_url, stream=True, headers=headers, timeout=REQUEST_TIMEOUT)
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

    def __init__(self, plugin_name, headers):
        super().__init__()
        self.plugin_name = plugin_name
        self.headers = headers

    def run(self):
        try:
            details_url = f"https://raw.githubusercontent.com/iMAboud/iMA-Menu-Plugins/main/{self.plugin_name}/details.md"
            response = requests.get(details_url, headers=self.headers, timeout=REQUEST_TIMEOUT)

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
                    response = requests.get(src_url, timeout=REQUEST_TIMEOUT)
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
                    response = requests.get(src_url, timeout=REQUEST_TIMEOUT)
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
        title_label.setFont(QFont('Montserrat', 18, QFont.Bold))
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
            self.close_animation.setDuration(300)
            self.close_animation.setStartValue(self.geometry())
            self.close_animation.setEndValue(self.start_geom)
            self.close_animation.setEasingCurve(QEasingCurve.InOutCubic)

            self.close_opacity_animation = QPropertyAnimation(self, b"windowOpacity")
            self.close_opacity_animation.setDuration(300)
            self.close_opacity_animation.setStartValue(1.0)
            self.close_opacity_animation.setEndValue(0.0)
            self.close_opacity_animation.setEasingCurve(QEasingCurve.InOutCubic)
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
        
        painter.setBrush(QColor("#282a3e"))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(self.rect(), 15, 15)

class UnsavedChangesDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setObjectName("customMessageBox")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        label = QLabel("You have unsaved changes. Do you want to save them?")
        label.setStyleSheet("color: #ffffff; font-size: 14px; padding: 10px;")
        layout.addWidget(label)

        button_box = QDialogButtonBox()
        yes_button = button_box.addButton("Yes", QDialogButtonBox.YesRole)
        no_button = button_box.addButton("No", QDialogButtonBox.NoRole)
        yes_button.setObjectName("installButton")
        no_button.setObjectName("uninstallButton")

        layout.addWidget(button_box)

        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor(40, 42, 62, 230))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(self.rect(), 15, 15)

class PluginManager(QWidget):
    operation_signal = pyqtSignal(str, str, str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("iMA Plugin Manager")
        self.setFixedSize(880, 600)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowIcon(QIcon(resource_path('icons/icon.ico')))

        self.setup_cache_dirs()
        self.github_token = self.load_github_token()
        
        self.active_threads = {}
        self.installation_queue = deque()
        self.current_installing_plugin = None
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

        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        self.side_panel = self.create_side_panel()
        self.main_layout.addWidget(self.side_panel)

        self.content_area = QWidget()
        self.content_area.setObjectName("contentArea")
        self.content_layout = QVBoxLayout(self.content_area)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.addWidget(self.content_area)

        self.title_bar = self.create_title_bar()
        self.content_layout.addWidget(self.title_bar)

        self.stacked_widget = QStackedWidget()
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
        self.scroll_area.verticalScrollBar().valueChanged.connect(self.check_visible_cards)
        self.stacked_widget.addWidget(self.plugins_page)

        self.modify_page = ModifyWidget(os.path.join(PROJECT_ROOT, 'imports', 'modify.nss'), PROJECT_ROOT)
        self.stacked_widget.addWidget(self.modify_page)

        self.theme_page = QWidget()
        self.theme_layout = QVBoxLayout(self.theme_page)
        self.theme_tab_widget = QTabWidget()
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

        self.theme_save_button.clicked.connect(self.save_theme_and_update_status)
        self.theme_reset_button.clicked.connect(self.reset_theme_and_update_status)
        self.theme_switcher_page.theme_selected.connect(self.theme_editor_page.reload_theme)

        self.theme_tab_widget.addTab(self.theme_switcher_page, "Theme Switcher")
        self.theme_tab_widget.addTab(self.theme_editor_page, "Theme Editor")

        self.stacked_widget.addWidget(self.theme_page)

        self.settings_page = QWidget()
        settings_layout = QVBoxLayout(self.settings_page)
        settings_label = QLabel("Settings Page")
        settings_label.setAlignment(Qt.AlignCenter)
        settings_layout.addWidget(settings_label)
        self.stacked_widget.addWidget(self.settings_page)


        self.loading_label = QLabel("Loading plugins...", self)
        self.loading_label.setAlignment(Qt.AlignCenter)
        self.loading_label.setFont(QFont('Montserrat', 16, QFont.Bold))
        self.loading_label.setObjectName("loadingLabel")
        self.loading_label.hide()
        self.content_layout.addWidget(self.loading_label)

        self.operation_signal.connect(self.on_operation_finished)

        self.load_plugins()
        self.start_pos = None

        self.installEventFilter(self)

    def save_theme_and_update_status(self):
        if self.theme_editor_page.save_theme():
            self.theme_status_label.setText("Theme Saved")
            self.theme_status_label.setStyleSheet("color: #94e2d5;")
            QTimer.singleShot(3000, self.theme_status_label.clear)

    def reset_theme_and_update_status(self):
        if self.theme_editor_page.reset_theme():
            self.theme_status_label.setText("Reset to Default")
            self.theme_status_label.setStyleSheet("color: #ffffff;")
            QTimer.singleShot(3000, self.theme_status_label.clear)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.MouseButtonPress:
            if self.details_popup and not self.details_popup.geometry().contains(event.globalPos()):
                if self.ignore_next_click:
                    self.ignore_next_click = False
                else:
                    self.details_popup.close()
        return super().eventFilter(obj, event)

    def get_auth_headers(self):
        return {'Authorization': f'token {self.github_token}'} if self.github_token else {}

    def load_github_token(self):
        return os.environ.get('IMA_MENU_GITHUB_TOKEN')

    def setup_cache_dirs(self):
        os.makedirs(PLUGINS_DIR, exist_ok=True)
        os.makedirs(CACHE_DIR, exist_ok=True)
        os.makedirs(ICONS_CACHE_DIR, exist_ok=True)
        os.makedirs(LIB_DIR, exist_ok=True)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and event.y() < self.title_bar.height():
            self.start_pos = event.globalPos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.start_pos and event.buttons() == Qt.LeftButton:
            delta = event.globalPos() - self.start_pos
            self.move(self.pos() + delta)
            self.start_pos = event.globalPos()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self.start_pos = None
        super().mouseReleaseEvent(event)

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
        title_label.setFont(QFont('Montserrat', 16, QFont.Bold))
        title_label.setObjectName("titleLabel")
        self._apply_shadow_effect(title_label)

        open_folder_button = QPushButton()
        open_folder_button.setIcon(QIcon(resource_path('icons/open.png')))
        open_folder_button.setIconSize(QSize(24, 24))
        open_folder_button.setFixedSize(30, 30)
        open_folder_button.setObjectName("iconButton")
        open_folder_button.clicked.connect(self.open_root_folder)
        self._apply_shadow_effect(open_folder_button)

        refresh_button = QPushButton()
        refresh_button.setIcon(QIcon(resource_path('icons/refresh.png')))
        refresh_button.setIconSize(QSize(24, 24))
        refresh_button.setFixedSize(30, 30)
        refresh_button.setObjectName("iconButton")
        refresh_button.clicked.connect(self.refresh_plugins)
        self._apply_shadow_effect(refresh_button)

        minimize_button = QPushButton()
        minimize_button.setIcon(QIcon(resource_path('icons/min.png')))
        minimize_button.setIconSize(QSize(24, 24))
        minimize_button.setFixedSize(30, 30)
        minimize_button.setObjectName("iconButton")
        minimize_button.clicked.connect(self.showMinimized)
        self._apply_shadow_effect(minimize_button)

        close_button = QPushButton()
        close_button.setIcon(QIcon(resource_path('icons/x.png')))
        close_button.setIconSize(QSize(24, 24))
        close_button.setFixedSize(30, 30)
        close_button.setObjectName("iconButton")
        close_button.clicked.connect(self.close)
        self._apply_shadow_effect(close_button)
        
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        title_layout.addWidget(open_folder_button)
        title_layout.addWidget(refresh_button)
        title_layout.addWidget(minimize_button)
        title_layout.addWidget(close_button)
        return title_bar

    def create_side_panel(self):
        side_panel = QWidget()
        side_panel.setObjectName("sidePanel")
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
        plugins_button.clicked.connect(lambda: self.stacked_widget.setCurrentWidget(self.plugins_page))
        side_panel_layout.addWidget(plugins_button)
        self._apply_shadow_effect(plugins_button)

        modify_button = QPushButton()
        modify_button.setObjectName("sideButton")
        modify_button.setIcon(QIcon(resource_path('icons/modify.png')))
        modify_button.setIconSize(QSize(40, 40))
        modify_button.setFixedSize(60, 60)
        modify_button.clicked.connect(lambda: self.stacked_widget.setCurrentWidget(self.modify_page))
        side_panel_layout.addWidget(modify_button)
        self._apply_shadow_effect(modify_button)

        theme_button = QPushButton()
        theme_button.setObjectName("sideButton")
        theme_button.setIcon(QIcon(resource_path('icons/theme.png')))
        theme_button.setIconSize(QSize(40, 40))
        theme_button.setFixedSize(60, 60)
        theme_button.clicked.connect(lambda: self.stacked_widget.setCurrentWidget(self.theme_page))
        side_panel_layout.addWidget(theme_button)
        self._apply_shadow_effect(theme_button)

        side_panel_layout.addStretch()

        settings_button = QPushButton()
        settings_button.setObjectName("sideButton")
        settings_button.setIcon(QIcon(resource_path('icons/settings.png')))
        settings_button.setIconSize(QSize(40, 40))
        settings_button.setFixedSize(60, 60)
        settings_button.clicked.connect(lambda: self.stacked_widget.setCurrentWidget(self.settings_page))
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
                self.display_plugins(plugins)
                return
            except (json.JSONDecodeError, IOError, ValueError) as e:
                print(f"Error loading cache: {e}. Fetching from remote.")
                if os.path.exists(PLUGINS_CACHE_FILE): os.remove(PLUGINS_CACHE_FILE)
        
        self.fetch_plugins_list()

    def fetch_plugins_list(self):
        self.loading_label.show()
        self.scroll_area.hide()

        thread = QThread(self)
        worker = FetchPluginsThread(self.github_token)
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.finished.connect(self.on_plugins_fetched)
        worker.error.connect(self.on_fetch_error)
        worker.finished.connect(thread.quit)
        worker.error.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        worker.error.connect(worker.deleteLater)
        thread.finished.connect(lambda: self.cleanup_thread('plugin_list'))
        
        thread.start()
        self.active_threads['plugin_list'] = (thread, worker)

    def on_plugins_fetched(self, plugins):
        self.loading_label.hide()
        self.scroll_area.show()
        self.display_plugins(plugins)

    def on_fetch_error(self, error_message):
        self.loading_label.setText(f"Error: {error_message}")

    def refresh_plugins(self):
        if self.current_installing_plugin: return
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

        for i, plugin in enumerate(plugins):
            card = self.create_plugin_card(plugin)
            self.grid_layout.addWidget(card, i // 4, i % 4)

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
        title.setFont(QFont('Montserrat', 14, QFont.Bold))
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

        progress_bar = QProgressBar()
        progress_bar.setVisible(False)
        progress_bar.setObjectName(f"progressBar_{plugin_name}")
        layout.addWidget(progress_bar, alignment=Qt.AlignCenter)

        action_layout = QHBoxLayout()
        action_layout.setContentsMargins(0, 10, 0, 0)
        action_layout.setSpacing(10)
        layout.addLayout(action_layout)

        action_button = QPushButton()
        action_button.setObjectName("installButton")
        action_layout.addWidget(action_button, alignment=Qt.AlignCenter)

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
        self.animation.setEasingCurve(QEasingCurve.InOutCubic)
        self.animation.start(QPropertyAnimation.DeleteWhenStopped)

        self.opacity_animation = QPropertyAnimation(self.details_popup, b"windowOpacity")
        self.opacity_animation.setDuration(300)
        self.opacity_animation.setStartValue(0.0)
        self.opacity_animation.setEndValue(1.0)
        self.opacity_animation.setEasingCurve(QEasingCurve.InOutCubic)
        self.opacity_animation.start(QPropertyAnimation.DeleteWhenStopped)

        thread = QThread(self)
        worker = DetailsFetchWorker(plugin_name, self.get_auth_headers())
        worker.moveToThread(thread)

        worker.finished.connect(self.details_popup.set_details_content)
        worker.error.connect(lambda err: self.details_popup.set_details_content(f"Error: {err}"))
        thread.started.connect(worker.run)
        worker.finished.connect(thread.quit)
        worker.error.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        worker.error.connect(worker.deleteLater)
        thread.finished.connect(lambda: self.cleanup_thread(f"details_{plugin_name}"))

        thread.start()
        self.active_threads[f"details_{plugin_name}"] = (thread, worker)

        self.details_popup.action_button.clicked.connect(lambda: self.handle_popup_action(plugin_name))
        self.update_popup_button(plugin_name)
        self.ignore_next_click = True

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

    def check_visible_cards(self):
        scroll_bar = self.scroll_area.verticalScrollBar()
        viewport_top = scroll_bar.value()
        viewport_bottom = viewport_top + self.scroll_area.viewport().height()

        for plugin_name, card in self.plugin_cards.items():
            if plugin_name not in self.icons_loaded:
                card_top = card.y()
                card_bottom = card_top + card.height()
                if card_top < viewport_bottom and card_bottom > viewport_top:
                    plugin_data = self.all_plugins_data.get(plugin_name)
                    if plugin_data:
                        self.load_icon(plugin_data)
                        self.icons_loaded.add(plugin_name)

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

        is_queued = plugin_name in [p['name'] for p in self.installation_queue]
        is_installing = self.current_installing_plugin == plugin_name
        local_version = self.get_local_plugin_version(plugin_name)
        remote_version = self.all_plugins_data.get(plugin_name, {}).get('version')

        is_partially_installed = os.path.exists(get_plugin_install_path(self.all_plugins_data.get(plugin_name, {}))) and not self.get_local_plugin_version(plugin_name)

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
            
            if remote_version and local_version != remote_version:
                update_button = QPushButton("Update")
                update_button.setObjectName("updateButton")
                update_button.clicked.connect(lambda: self.add_to_installation_queue(plugin_name, is_update=True))
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
        plugin_name = plugin['name']
        label = self.plugin_icon_labels[plugin_name]
        local_icon_path = os.path.join(ICONS_CACHE_DIR, f"{plugin_name}.png")

        if os.path.exists(local_icon_path):
            pixmap = QPixmap(local_icon_path)
            if not pixmap.isNull():
                label.setPixmap(pixmap)
                return
        
        if plugin.get('icon_url'):
            thread = QThread(self)
            worker = IconDownloadWorker(plugin_name, plugin['icon_url'], local_icon_path, get_auth_headers(self.github_token))
            worker.moveToThread(thread)

            worker.finished.connect(self.on_icon_loaded)
            worker.error.connect(lambda e: self.on_icon_loaded(plugin_name, QPixmap()))
            thread.started.connect(worker.run)
            worker.finished.connect(thread.quit)
            worker.error.connect(thread.quit)
            worker.finished.connect(worker.deleteLater)
            worker.error.connect(worker.deleteLater)
            thread.finished.connect(lambda: self.cleanup_thread(f"icon_{plugin_name}"))
            
            thread.start()
            self.active_threads[f"icon_{plugin_name}"] = (thread, worker)
        else:
            label.setPixmap(QPixmap(DEFAULT_ICON_PATH))

    def add_to_installation_queue(self, plugin_name, is_update=False):
        if plugin_name in [p['name'] for p in self.installation_queue] or self.current_installing_plugin == plugin_name:
            return
            
        self.installation_queue.append(self.all_plugins_data[plugin_name])
        self.update_card_ui(plugin_name)
        
        if is_update and self.plugin_update_buttons.get(plugin_name):
            self.plugin_update_buttons[plugin_name].setEnabled(False)

        if not self.current_installing_plugin:
            self.process_next_in_queue()

    def process_next_in_queue(self):
        if not self.installation_queue:
            self.current_installing_plugin = None
            return

        plugin_data = self.installation_queue.popleft()
        self.current_installing_plugin = plugin_data['name']
        
        progress_bar = self.plugin_progress_bars[self.current_installing_plugin]
        button = self.plugin_buttons[self.current_installing_plugin]
        
        progress_bar.setVisible(True)
        progress_bar.setValue(0)
        self.update_card_ui(self.current_installing_plugin)

        thread = QThread(self)
        worker = InstallationWorker(plugin_data, self.get_auth_headers())
        worker.moveToThread(thread)

        self.active_threads[self.current_installing_plugin] = (thread, worker)

        thread.started.connect(worker.run)
        worker.progress.connect(self.on_install_progress)
        worker.finished.connect(self.on_operation_finished)
        worker.error.connect(self.on_operation_error)
        worker.finished.connect(thread.quit)
        worker.error.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        worker.error.connect(worker.deleteLater)
        thread.finished.connect(lambda: self.cleanup_thread(self.current_installing_plugin))
        
        thread.start()

    def on_install_progress(self, plugin_name, value):
        if plugin_name == self.current_installing_plugin:
            self.plugin_progress_bars[plugin_name].setValue(value)

    def on_operation_error(self, plugin_name, status, error_message):
        print(f"Operation error for {plugin_name}: {error_message}")
        if plugin_name in self.plugin_progress_bars:
            self.plugin_progress_bars[plugin_name].setVisible(False)

        if plugin_name == self.current_installing_plugin:
            self.cleanup_thread(plugin_name)
            self.current_installing_plugin = None
            self.process_next_in_queue()

        self.update_card_ui(plugin_name)

        if self.details_popup and self.details_popup.plugin_data['name'] == plugin_name:
            self.details_popup.set_details_content(f"<font color='red'>Error: {error_message}</font>")
        else:
            msgBox = CustomMessageBox()
            msgBox.setIcon(QMessageBox.Critical)
            msgBox.setText(f"Error for {plugin_name}")
            msgBox.setInformativeText(error_message)
            msgBox.setStandardButtons(QMessageBox.Ok)
            msgBox.exec_()

    def on_operation_finished(self, plugin_name, status):
        if plugin_name in self.plugin_progress_bars:
            self.plugin_progress_bars[plugin_name].setVisible(False)

        if plugin_name == self.current_installing_plugin:
            self.cleanup_thread(plugin_name)
            self.current_installing_plugin = None
            self.process_next_in_queue()

        self.update_card_ui(plugin_name)

    def cancel_operation(self, plugin_name):
        if self.current_installing_plugin == plugin_name and plugin_name in self.active_threads:
            thread, worker = self.active_threads[plugin_name]
            worker.cancel()
        else:
            self.installation_queue = deque([p for p in self.installation_queue if p['name'] != plugin_name])
            self.update_card_ui(plugin_name)

    def uninstall_plugin(self, plugin_name):
        try:
            plugin_data = self.all_plugins_data.get(plugin_name)
            if not plugin_data:
                self.operation_signal.emit(plugin_name, "failed", "Plugin data not found.")
                return

            target_plugin_dir = get_plugin_install_path(plugin_data)
            if os.path.exists(target_plugin_dir):
                shutil.rmtree(target_plugin_dir)
            remove_nss_import(plugin_data)
            self.operation_signal.emit(plugin_name, "uninstalled", "")
        except Exception as e:
            self.operation_signal.emit(plugin_name, "failed", str(e))

    def cleanup_thread(self, key):
        if key in self.active_threads:
            thread, worker = self.active_threads.pop(key)
            thread.quit()

    def apply_card_style(self, card):
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 160))
        shadow.setOffset(5, 5)
        card.setGraphicsEffect(shadow)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor("#1e2030"))
        painter.setPen(Qt.NoPen)
        rect = self.rect()
        painter.drawRoundedRect(rect, 15, 15)

    def closeEvent(self, event):
        if self.theme_editor_page.is_dirty:
            dialog = UnsavedChangesDialog(self)
            if dialog.exec_() == QDialog.Accepted:
                self.theme_editor_page.save_theme()
            else:
                self.theme_editor_page.revert_changes()

        for key, (thread, worker) in list(self.active_threads.items()):
            thread.quit()
            if not thread.wait(2000):
                thread.terminate()
        event.accept()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    if os.name == 'nt':
        myappid = 'iMAboud.iMAMenu.Launcher.1'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    try:
        with open(resource_path('style.css')) as f:
            app.setStyleSheet(f.read())
    except FileNotFoundError:
        print("Warning: style.css not found.")
    manager = PluginManager()
    manager.show()
    sys.exit(app.exec_())
