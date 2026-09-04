"""
Plugin Workers & Detail Popups for iMA Menu Launcher.
Handles asynchronous plugin fetching, icon caching, staged installation, and markdown detail popups.
Extracted from launcher.pyw for clean architecture and reduced token consumption.
"""

import os
import re
import sys
import json
import time
import shutil
import zipfile
import winreg
import html
from pathlib import Path

from PyQt5.QtWidgets import (QWidget, QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
                             QTextBrowser, QSizePolicy, QLayout)
from PyQt5.QtGui import QColor, QFont, QPainter, QPen, QIcon, QPixmap, QTextOption, QPainterPath
from PyQt5.QtCore import (Qt, pyqtSignal, QSize, QEvent, QPoint, QRect, QRectF, QObject, 
                          QPropertyAnimation, QEasingCurve, QParallelAnimationGroup)

from github_client import github_api_get, cdn_get, get_latest_tree_sha, RequestException
from plugin_registry import atomic_json_write, safe_json_read, git_blob_sha
from utils import resource_path, safe_file_write, terminate_plugin_processes, CapsuleActionButton

PROJECT_ROOT = None
PLUGINS_DIR = None
CACHE_DIR = None
ICONS_CACHE_DIR = None
LIB_DIR = None
DEFAULT_ICON_PATH = None
REQUEST_TIMEOUT = 10
_GITHUB_REPO = "iMAboud/iMA-Menu-Plugins"
GITHUB_API_BASE_URL = f"https://api.github.com/repos/{_GITHUB_REPO}"
GITHUB_PLUGINS_JSON_URL = f"https://raw.githubusercontent.com/{_GITHUB_REPO}/main/plugins.json"
GIT_TREE_CACHE_FILE = None
PLUGINS_CACHE_FILE = None

_load_crisp_pixmap = None
_get_plugin_install_path = None
_add_nss_import = None
_add_directory_to_system_path = None

def init_plugin_workers(project_root, plugins_dir, cache_dir, icons_cache_dir, lib_dir,
                        default_icon_path, request_timeout, github_repo, git_tree_cache_file,
                        plugins_cache_file, load_crisp_pixmap_fn, get_plugin_install_path_fn,
                        add_nss_import_fn, add_directory_to_system_path_fn):
    global PROJECT_ROOT, PLUGINS_DIR, CACHE_DIR, ICONS_CACHE_DIR, LIB_DIR
    global DEFAULT_ICON_PATH, REQUEST_TIMEOUT, _GITHUB_REPO, GITHUB_API_BASE_URL
    global GITHUB_PLUGINS_JSON_URL, GIT_TREE_CACHE_FILE, PLUGINS_CACHE_FILE
    global _load_crisp_pixmap, _get_plugin_install_path, _add_nss_import, _add_directory_to_system_path

    PROJECT_ROOT = project_root
    PLUGINS_DIR = plugins_dir
    CACHE_DIR = cache_dir
    ICONS_CACHE_DIR = icons_cache_dir
    LIB_DIR = lib_dir
    DEFAULT_ICON_PATH = default_icon_path
    REQUEST_TIMEOUT = request_timeout
    _GITHUB_REPO = github_repo
    GITHUB_API_BASE_URL = f"https://api.github.com/repos/{_GITHUB_REPO}"
    GITHUB_PLUGINS_JSON_URL = f"https://raw.githubusercontent.com/{_GITHUB_REPO}/main/plugins.json"
    GIT_TREE_CACHE_FILE = git_tree_cache_file
    PLUGINS_CACHE_FILE = plugins_cache_file

    _load_crisp_pixmap = load_crisp_pixmap_fn
    _get_plugin_install_path = get_plugin_install_path_fn
    _add_nss_import = add_nss_import_fn
    _add_directory_to_system_path = add_directory_to_system_path_fn


def find_riot_client_path():
    from pathlib import Path
    try:
        key_path = r'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Riot Game valorant.live'
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
            loc, _ = winreg.QueryValueEx(key, 'InstallLocation')
            if loc and os.path.isdir(loc):
                p = os.path.join(loc, 'RiotClientServices.exe')
                if os.path.exists(p): return p
    except Exception:
        pass

    try:
        key_path = r'SOFTWARE\Riot Games\Riot Client'
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as key:
            p, _ = winreg.QueryValueEx(key, 'ExecutablePath')
            if p and os.path.exists(p): return p
    except Exception:
        pass

    installs_json = Path(os.getenv('ALLUSERSPROFILE', 'C:/ProgramData')) / 'Riot Games' / 'RiotClientInstalls.json'
    if installs_json.exists():
        try:
            with open(installs_json, 'r') as f:
                data = json.load(f)
                for k in ('rc_default', 'rc_live', 'associated_client'):
                    if k in data and os.path.exists(data[k]):
                        return data[k]
        except Exception:
            pass

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
                        if cache_data and (not root_tree_sha or cache_data.get('sha') == root_tree_sha):
                            tree_data = cache_data.get('tree')
                    except Exception:
                        tree_data = None

                if tree_data is None and root_tree_sha:
                    trees_api_url = f"{GITHUB_API_BASE_URL}/git/trees/{root_tree_sha}?recursive=true"
                    tree_res = github_api_get(trees_api_url, max_retries=2, timeout=REQUEST_TIMEOUT)
                    tree_data = tree_res.json()
                    try:
                        atomic_json_write(GIT_TREE_CACHE_FILE, {'sha': root_tree_sha, 'tree': tree_data})
                    except Exception:
                        pass
            except Exception:
                if os.path.exists(GIT_TREE_CACHE_FILE):
                    try:
                        cache_data = safe_json_read(GIT_TREE_CACHE_FILE)
                        tree_data = cache_data.get('tree') if cache_data else {}
                    except Exception:
                        tree_data = {}
                else:
                    tree_data = {}

            self.finished.emit(plugins, tree_data or {})
        except RequestException as e:
            self.error.emit(f"Network error: {e}")
        except Exception as e:
            self.error.emit(f"Error checking plugins: {e}")


class IconDownloadWorker(QObject):
    finished = pyqtSignal(str, QPixmap)
    error = pyqtSignal(str)

    def __init__(self, plugin_name, url, save_path):
        super().__init__()
        self.plugin_name = plugin_name
        self.url = url
        self.save_path = save_path

    def run(self):
        try:
            response = cdn_get(self.url, max_retries=2, timeout=REQUEST_TIMEOUT)
            pixmap = QPixmap()
            pixmap.loadFromData(response.content)
            if not pixmap.isNull():
                pixmap.save(self.save_path)
            self.finished.emit(self.plugin_name, pixmap)
        except Exception as e:
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
                    try:
                        with open(config_file, 'r', encoding='utf-8') as cf:
                            cfg = json.load(cf)
                    except Exception: cfg = {}
                cfg['riot_client_services_path'] = riot_exe
                atomic_json_write(config_file, cfg)

            app_nss = os.path.join(target_dir, 'valo.nss')
            imports_nss = os.path.join(PROJECT_ROOT, 'imports', 'valo.nss')
            if os.path.exists(app_nss) or os.path.exists(imports_nss):
                try:
                    if _add_nss_import:
                        _add_nss_import({'nss_path': 'imports', 'nss_file': 'valo.nss'}, os.path.join(PROJECT_ROOT, 'shell.nss'))
                except Exception:
                    pass

            self.progress.emit(self.plugin_name, 100)
            self.finished.emit(self.plugin_name, "installed", {}, 1)
        except Exception as e:
            self.error.emit(self.plugin_name, "failed", str(e))

    def _install_from_repo_archive(self, staging_dir, file_hashes):
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
                        dst_f.write(src_f.read())
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
        target_plugin_dir = _get_plugin_install_path(self.plugin_data) if _get_plugin_install_path else os.path.join(PLUGINS_DIR, self.plugin_name)
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
                    print(f"Git trees resolution fallback: {e}")
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
                if _add_directory_to_system_path:
                    _add_directory_to_system_path(LIB_DIR)

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
                        try: shutil.rmtree(backup_dir, ignore_errors=True)
                        except Exception: pass

            if os.path.exists(staging_dir):
                if os.path.exists(target_plugin_dir):
                    try: shutil.rmtree(target_plugin_dir, ignore_errors=True)
                    except Exception: pass
                try:
                    os.rename(staging_dir, target_plugin_dir)
                except OSError:
                    shutil.copytree(staging_dir, target_plugin_dir, dirs_exist_ok=True)
                    shutil.rmtree(staging_dir, ignore_errors=True)

            if os.path.exists(backup_dir):
                try: shutil.rmtree(backup_dir, ignore_errors=True)
                except Exception: pass

            if self.plugin_data.get('launch') and self.plugin_data.get('launch_file'):
                launch_file_path = os.path.join(target_plugin_dir, self.plugin_data['launch_file'])
                if os.path.exists(launch_file_path):
                    try: os.startfile(launch_file_path)
                    except Exception as e: print(f"Failed to auto-launch {launch_file_path}: {e}")

            if _add_nss_import:
                _add_nss_import(self.plugin_data, os.path.join(PROJECT_ROOT, 'shell.nss'))
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
                self.progress.emit(self.plugin_name, int(((i + 1) / total_dependencies) * 100))
                continue

            try:
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
                        if chunk: f.write(chunk)
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

            if os.path.exists(temp_html_path):
                try:
                    with open(temp_html_path, 'r', encoding='utf-8', errors='ignore') as f:
                        cached_html = f.read()
                    if cached_html.strip():
                        self.finished.emit(cached_html)
                        return
                except Exception:
                    pass

            if os.path.exists(temp_md_path):
                try:
                    with open(temp_md_path, 'r', encoding='utf-8', errors='ignore') as f:
                        cached_md = f.read()
                    if cached_md.strip():
                        html_content = self.markdown_to_html_with_images(cached_md)
                        try: safe_file_write(temp_html_path, html_content)
                        except Exception: pass
                        self.finished.emit(html_content)
                        return
                except Exception:
                    pass

            details_url = f"https://raw.githubusercontent.com/{_GITHUB_REPO}/main/{self.plugin_name}/details.md"
            readme_url = f"https://raw.githubusercontent.com/{_GITHUB_REPO}/main/{self.plugin_name}/README.md"
            markdown_content = ""

            for url in (details_url, readme_url):
                try:
                    response = cdn_get(url, max_retries=2, timeout=REQUEST_TIMEOUT)
                    if response.status_code == 200 and response.text.strip():
                        markdown_content = response.text
                        break
                except Exception:
                    continue

            if not markdown_content.strip():
                markdown_content = f"# {self.plugin_name}\n\n*No extended details or README available for this plugin.*"

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
        except Exception as e:
            self.error.emit(f"Error fetching details: {e}")

    def markdown_to_html_with_images(self, markdown_text):
        raw_base_url = f"https://raw.githubusercontent.com/{_GITHUB_REPO}/main/{self.plugin_name}"

        def replace_img(match):
            alt_text = match.group(1)
            img_path = match.group(2).strip()
            if not img_path.startswith(('http://', 'https://')):
                clean_path = img_path.lstrip('./').lstrip('/')
                full_url = f"{raw_base_url}/{clean_path}"
                return f"![{alt_text}]({full_url})"
            return match.group(0)

        processed_markdown = re.sub(r'!\[(.*?)\]\((.*?)\)', replace_img, markdown_text)
        
        # Pure Python Markdown to HTML
        lines = processed_markdown.replace('\r\n', '\n').split('\n')
        out = []
        in_code = False
        in_table = False
        in_list = False
        code_buf = []

        def inline_fmt(text: str) -> str:
            text = html.escape(text)
            text = re.sub(r'!\[(.*?)\]\((.*?)\)', r'<img src="\2" alt="\1">', text)
            text = re.sub(r'\[(.*?)\]\((.*?)\)', r'<a href="\2">\1</a>', text)
            text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
            text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
            text = re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)', r'<i>\1</i>', text)
            return text

        for line in lines:
            stripped = line.strip()
            if stripped.startswith('```'):
                if in_code:
                    in_code = False
                    escaped = html.escape('\n'.join(code_buf))
                    out.append(f'<pre><code>{escaped}</code></pre>')
                    code_buf = []
                else:
                    if in_list:
                        out.append('</ul>')
                        in_list = False
                    in_code = True
                continue

            if in_code:
                code_buf.append(line)
                continue

            if '|' in line and (stripped.startswith('|') or line.count('|') >= 2):
                cells = [c.strip() for c in stripped.strip('|').split('|')]
                if all(set(c).issubset({'-', ':', ' '}) for c in cells if c):
                    continue
                if not in_table:
                    in_table = True
                    out.append('<table><thead><tr>' + ''.join(f'<th>{inline_fmt(c)}</th>' for c in cells) + '</tr></thead><tbody>')
                else:
                    out.append('<tr>' + ''.join(f'<td>{inline_fmt(c)}</td>' for c in cells) + '</tr>')
                continue
            elif in_table:
                out.append('</tbody></table>')
                in_table = False

            m_list = re.match(r'^\s*[-*+]\s+(.*)', line)
            if m_list:
                if not in_list:
                    in_list = True
                    out.append('<ul>')
                out.append(f'<li>{inline_fmt(m_list.group(1))}</li>')
                continue
            elif in_list:
                out.append('</ul>')
                in_list = False

            if stripped.startswith('#'):
                level = len(stripped) - len(stripped.lstrip('#'))
                if 1 <= level <= 6:
                    h_text = stripped[level:].strip()
                    out.append(f'<h{level}>{inline_fmt(h_text)}</h{level}>')
                    continue

            if stripped.startswith('>'):
                q_text = stripped.lstrip('>').strip()
                out.append(f'<blockquote>{inline_fmt(q_text)}</blockquote>')
                continue

            if not stripped:
                continue

            out.append(f'<p>{inline_fmt(line)}</p>')

        if in_code:
            out.append(f'<pre><code>{html.escape(chr(10).join(code_buf))}</code></pre>')
        if in_table:
            out.append('</tbody></table>')
        if in_list:
            out.append('</ul>')

        html_content = '\n'.join(out)

        return f'''<!DOCTYPE html>
        <html><head><meta charset="utf-8">
        <style>
            body {{ font-family: 'Segoe UI Variable Display', 'Segoe UI', system-ui, sans-serif; font-size: 13.5px; line-height: 1.65; color: #c6d0f5; background-color: transparent; margin: 0; padding: 0 4px 0 0; }}
            h1, h2, h3, h4 {{ color: #ffffff; font-weight: 600; margin-top: 1.1em; margin-bottom: 0.4em; }}
            h1 {{ font-size: 18px; border-bottom: 1px solid rgba(255, 255, 255, 0.08); padding-bottom: 6px; }}
            h2 {{ font-size: 15px; color: #ea999c; }}
            h3 {{ font-size: 14px; }}
            p {{ margin-bottom: 0.8em; color: #bac2de; }}
            b, strong {{ color: #ffffff; font-weight: 600; }}
            a {{ color: #ea999c; text-decoration: none; font-weight: bold; }}
            a:hover {{ color: #f5a9b8; text-decoration: underline; }}
            img {{ max-width: 95%; max-height: 380px; height: auto; display: block; margin: 14px auto; border-radius: 12px; border: 1px solid rgba(255, 255, 255, 0.1); }}
            ul, ol {{ margin-bottom: 1em; padding-left: 22px; color: #bac2de; }}
            li {{ margin-bottom: 6px; }}
            code {{ background: rgba(234, 153, 156, 0.12); color: #ea999c; border: 1px solid rgba(234, 153, 156, 0.22); padding: 2px 7px; border-radius: 6px; font-family: 'Cascadia Code', 'Consolas', 'Courier New', monospace; font-size: 12px; font-weight: 600; }}
            pre {{ background: #121214; border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 10px; padding: 12px 14px; overflow-x: auto; color: #cdd6f4; }}
            pre code {{ background: transparent; border: none; padding: 0; color: inherit; }}
            blockquote {{ border-left: 3px solid #ea999c; background: rgba(234, 153, 156, 0.06); margin: 0 0 1em 0; padding: 8px 14px; border-radius: 0 8px 8px 0; color: #a6adc8; }}
            table {{ border-collapse: collapse; width: 100%; margin-bottom: 1em; background: rgba(255, 255, 255, 0.02); border-radius: 8px; overflow: hidden; }}
            th, td {{ border: 1px solid rgba(255, 255, 255, 0.08); padding: 8px 12px; text-align: left; }}
            th {{ background: rgba(255, 255, 255, 0.05); color: #ffffff; font-weight: bold; }}
            tr:nth-child(even) {{ background: rgba(255, 255, 255, 0.02); }}
        </style></head><body>{html_content}</body></html>
        '''


class ClickableWidget(QFrame):
    plugin_card_clicked = pyqtSignal(str, QWidget)

    def __init__(self, plugin_name, parent=None):
        super().__init__(parent)
        self.plugin_name = plugin_name
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setAttribute(Qt.WA_Hover, True)
        self.setMouseTracking(True)

    def mousePressEvent(self, event):
        self.plugin_card_clicked.emit(self.plugin_name, self)
        super().mousePressEvent(event)


class PopupHeaderButton(QPushButton):
    """Vector anti-aliased header button with smooth rounded or circular border."""
    def __init__(self, icon_path, is_circle=False, parent=None):
        super().__init__(parent)
        self.setFixedSize(32, 32)
        self.setCursor(Qt.PointingHandCursor)
        self.setAttribute(Qt.WA_Hover, True)
        self.is_circle = is_circle
        self._pixmap = QPixmap(icon_path) if icon_path and os.path.exists(icon_path) else QPixmap()
        self.setStyleSheet("background: transparent; border: none; outline: none;")

    def enterEvent(self, e):
        super().enterEvent(e)
        self.update()

    def leaveEvent(self, e):
        super().leaveEvent(e)
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)

        rect = QRectF(self.rect()).adjusted(1.0, 1.0, -1.0, -1.0)
        path = QPainterPath()
        if self.is_circle:
            path.addEllipse(rect)
        else:
            path.addRoundedRect(rect, 8.0, 8.0)

        is_hov = self.underMouse()
        if is_hov:
            p.fillPath(path, QColor(231, 130, 132, 45))
            p.setPen(QPen(QColor("#e78284"), 1.5))
        else:
            p.fillPath(path, QColor(255, 255, 255, 15))
            p.setPen(QPen(QColor(255, 255, 255, 30), 1.2))
        p.drawPath(path)

        if not self._pixmap.isNull():
            isize = 16 if self.is_circle else 18
            scaled = self._pixmap.scaled(isize, isize, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            ix = int((self.width() - scaled.width()) / 2.0)
            iy = int((self.height() - scaled.height()) / 2.0)
            p.drawPixmap(ix, iy, scaled)
        p.end()


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
                os.path.join(PROJECT_ROOT or '', 'iMA Switcher 1', 'Assets', 'ima.png'),
            ]
            for c in candidates:
                if os.path.exists(c) and _load_crisp_pixmap:
                    icon_pixmap = _load_crisp_pixmap(c, 128)
                    if not icon_pixmap.isNull():
                        break
        install_path = os.path.join(PLUGINS_DIR, self.plugin_data['name']) if PLUGINS_DIR else None
        if icon_pixmap.isNull() and install_path and os.path.isdir(install_path):
            try:
                for fname in os.listdir(install_path):
                    if fname.lower().endswith(('.png', '.ico', '.jpg', '.svg')) and _load_crisp_pixmap:
                        icon_pixmap = _load_crisp_pixmap(os.path.join(install_path, fname), 128)
                        if not icon_pixmap.isNull():
                            break
            except Exception:
                pass
        if icon_pixmap.isNull() and ICONS_CACHE_DIR and _load_crisp_pixmap:
            for cname in (f"{self.plugin_data['name']}.png", f"{self.plugin_data['name'].lower()}.png"):
                icon_pixmap = _load_crisp_pixmap(os.path.join(ICONS_CACHE_DIR, cname), 128)
                if not icon_pixmap.isNull():
                    break
        if icon_pixmap.isNull() and DEFAULT_ICON_PATH:
            icon_pixmap = QPixmap(DEFAULT_ICON_PATH)
        icon_label.setPixmap(icon_pixmap)
        title_layout.addWidget(icon_label)

        title_label = QLabel(self.plugin_data['name'])
        title_label.setFont(QFont('Segoe UI Variable Display', 18, QFont.Bold))
        title_layout.addWidget(title_label)
        title_layout.addStretch()

        plugin_dir = _get_plugin_install_path(self.plugin_data) if _get_plugin_install_path else None
        if plugin_dir and os.path.exists(plugin_dir):
            self.folder_button = PopupHeaderButton(resource_path('icons/Open.png'), is_circle=False)
            self.folder_button.setToolTip("Open Plugin Directory")
            self.folder_button.clicked.connect(lambda _, p=plugin_dir: os.startfile(p))
            title_layout.addWidget(self.folder_button)

            self.edit_button = PopupHeaderButton(resource_path('icons/modify.png'), is_circle=False)
            self.edit_button.setToolTip("Edit Item/Menu (.nss)")
            self.edit_button.clicked.connect(self._open_plugin_nss_editor)
            title_layout.addWidget(self.edit_button)

        close_button = PopupHeaderButton(resource_path('icons/x.png'), is_circle=True)
        close_button.setToolTip("Close")
        close_button.clicked.connect(self.close)
        title_layout.addWidget(close_button)
        self.layout.addWidget(title_bar)
        self._setup_body()

    def _open_plugin_nss_editor(self):
        plugin_dir = _get_plugin_install_path(self.plugin_data) if _get_plugin_install_path else None
        if not plugin_dir or not os.path.exists(plugin_dir):
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
                if dlg.get_changes():
                    save_imported_item(items[0], dlg.get_props())
        else:
            dlg = MultiItemEditDialog(items, self)
            if dlg.exec_():
                dlg.save_all()

    def _setup_body(self):
        description_label = QLabel(self.plugin_data.get('description', 'No description available.'))
        description_label.setWordWrap(True)
        description_label.setStyleSheet("color: #a6adc8; font-size: 13px; font-weight: 500; background: transparent; border: none; margin-top: 2px; margin-bottom: 6px;")
        self.layout.addWidget(description_label)

        self.details_browser = QTextBrowser()
        self.details_browser.setOpenExternalLinks(True)
        self.details_browser.setObjectName("detailsBrowser")
        self.details_browser.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.details_browser.setWordWrapMode(QTextOption.WordWrap)
        self.details_browser.setStyleSheet("""
            QTextBrowser#detailsBrowser {
                background-color: rgba(18, 18, 22, 0.75);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 14px;
                padding: 14px 16px;
                color: #c6d0f5;
            }
            QScrollBar:vertical {
                background: transparent;
                width: 8px;
                margin: 6px 2px 6px 0;
            }
            QScrollBar::handle:vertical {
                background: rgba(255, 255, 255, 0.15);
                border-radius: 4px;
                min-height: 24px;
            }
            QScrollBar::handle:vertical:hover {
                background: #ea999c;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        self.layout.addWidget(self.details_browser)

        self.action_button = CapsuleActionButton("install")
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
        painter.setBrush(QColor(18, 18, 22, 248))
        painter.setPen(QPen(QColor(255, 255, 255, 26), 1.5))
        painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 16, 16)
