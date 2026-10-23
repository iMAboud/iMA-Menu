import os
import sys
import json
import time
import subprocess
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtGui import QPixmap

from github_client import github_api_get, cdn_get, download_file, RequestException

APPS_JSON_URL = "https://raw.githubusercontent.com/iMAboud/iMA-Menu-Plugins/main/apps.json"


def get_apps_base_dir(app_base_path=None):
    if not app_base_path:
        if getattr(sys, 'frozen', False):
            app_base_path = os.path.dirname(os.path.abspath(sys.executable))
        else:
            app_base_path = os.path.dirname(os.path.abspath(__file__))
    apps_dir = os.path.join(app_base_path, 'Apps')
    try:
        os.makedirs(apps_dir, exist_ok=True)
    except Exception:
        pass
    return apps_dir


def get_app_install_dir(app_name, app_base_path=None):
    return os.path.join(get_apps_base_dir(app_base_path), app_name)


def get_app_executable_path(app_data, app_base_path=None):
    name = app_data.get('name', '')
    app_dir = get_app_install_dir(name, app_base_path)
    if not os.path.isdir(app_dir):
        return None

    target_exe = app_data.get('executable') or app_data.get('asset_name') or f"{name}.exe"
    exact_path = os.path.join(app_dir, target_exe)
    if os.path.isfile(exact_path):
        return exact_path

    # Case-insensitive search inside app_dir
    target_lower = target_exe.lower()
    for root, _, files in os.walk(app_dir):
        for f in files:
            if f.lower() == target_lower:
                return os.path.join(root, f)

    # Fallback to any .exe in app_dir
    for f in os.listdir(app_dir):
        if f.lower().endswith('.exe'):
            return os.path.join(app_dir, f)

    return None


def get_installed_app_version(app_data, app_base_path=None):
    name = app_data.get('name', '')
    app_dir = get_app_install_dir(name, app_base_path)
    ver_file = os.path.join(app_dir, 'version.txt')
    if os.path.isfile(ver_file):
        try:
            with open(ver_file, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except Exception:
            pass
    return None


def is_app_installed(app_data, app_base_path=None):
    exe_path = get_app_executable_path(app_data, app_base_path)
    return exe_path is not None and os.path.exists(exe_path)


def launch_app(app_data, app_base_path=None, exe_path=None):
    if not exe_path:
        exe_path = get_app_executable_path(app_data, app_base_path)
    if not exe_path or not os.path.exists(exe_path):
        return False
    app_dir = os.path.dirname(exe_path)
    try:
        os.startfile(exe_path)
        return True
    except Exception:
        try:
            subprocess.Popen([exe_path], cwd=app_dir, close_fds=True)
            return True
        except Exception:
            return False


class FetchAppsWorker(QObject):
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, cache_dir, app_base_path=None):
        super().__init__()
        self.cache_dir = cache_dir
        self.app_base_path = app_base_path
        self.apps_cache_file = os.path.join(cache_dir, 'apps.json')
        self.meta_cache_file = os.path.join(cache_dir, 'apps_meta_cache.json')

    def run(self):
        apps = []
        # 1. Load from local cache and bundled/root apps.json
        local_apps_json = os.path.join(self.app_base_path or '', 'apps.json')
        root_apps = []
        if os.path.isfile(local_apps_json):
            try:
                with open(local_apps_json, 'r', encoding='utf-8') as f:
                    root_apps = json.load(f)
            except Exception:
                root_apps = []

        cached_apps = []
        if os.path.isfile(self.apps_cache_file):
            try:
                with open(self.apps_cache_file, 'r', encoding='utf-8') as f:
                    cached_apps = json.load(f)
            except Exception:
                cached_apps = []

        # Merge local files (root apps.json takes priority for new items)
        apps = []
        seen_names = set()
        for a in (root_apps if isinstance(root_apps, list) else []) + (cached_apps if isinstance(cached_apps, list) else []):
            if isinstance(a, dict):
                nl = a.get('name', '').lower()
                if nl and nl not in seen_names:
                    seen_names.add(nl)
                    apps.append(a)

        # 2. Try fetching latest remote apps.json
        try:
            res = cdn_get(APPS_JSON_URL, max_retries=2, timeout=6)
            if res.status_code == 200:
                remote_apps = res.json()
                if isinstance(remote_apps, list) and remote_apps:
                    local_by_name = {a.get('name', '').lower(): a for a in apps if isinstance(a, dict)}
                    # Merge remote apps with local fields
                    merged_apps = []
                    remote_names = set()
                    for ra in remote_apps:
                        if isinstance(ra, dict):
                            ra_name_lower = ra.get('name', '').lower()
                            remote_names.add(ra_name_lower)
                            l_match = local_by_name.get(ra_name_lower, {})
                            for k, v in l_match.items():
                                if k not in ra or not ra[k]:
                                    ra[k] = v
                            merged_apps.append(ra)
                    # Keep local apps that do not exist yet on remote repo
                    for a in apps:
                        if isinstance(a, dict) and a.get('name', '').lower() not in remote_names:
                            merged_apps.append(a)
                    apps = merged_apps
                    try:
                        with open(self.apps_cache_file, 'w', encoding='utf-8') as f:
                            json.dump(apps, f, indent=2)
                    except Exception:
                        pass
        except Exception:
            pass

        # 3. Read cached release metadata
        meta_cache = {}
        if os.path.isfile(self.meta_cache_file):
            try:
                with open(self.meta_cache_file, 'r', encoding='utf-8') as f:
                    meta_cache = json.load(f)
            except Exception:
                meta_cache = {}

        # 4. Resolve latest release for each app
        updated_meta = False
        for app in apps:
            name = app.get('name', '')
            repo = app.get('repo', '').strip().rstrip('/')
            if repo.startswith('https://github.com/'):
                repo = repo.replace('https://github.com/', '')

            cached = meta_cache.get(name, {})
            app['version'] = cached.get('version', app.get('version', ''))
            app['download_url'] = cached.get('download_url', app.get('download_url', ''))
            if 'asset_name' in cached and not app.get('asset_name'):
                app['asset_name'] = cached['asset_name']

            if not repo:
                continue

            try:
                rel_url = f"https://api.github.com/repos/{repo}/releases/latest"
                rel_res = github_api_get(rel_url, max_retries=1, timeout=5)
                if rel_res.status_code == 200:
                    data = rel_res.json()
                    tag = data.get('tag_name', '').strip()
                    assets = data.get('assets', [])
                    target_asset = (app.get('asset_name') or f"{name}.exe").lower()
                    dl_url = None
                    matched_asset_name = None

                    for a in assets:
                        a_name = a.get('name', '')
                        if a_name.lower() == target_asset:
                            dl_url = a.get('browser_download_url')
                            matched_asset_name = a_name
                            break

                    if not dl_url:
                        for a in assets:
                            a_name = a.get('name', '')
                            if 'installer' in a_name.lower() and a_name.lower().endswith('.exe'):
                                dl_url = a.get('browser_download_url')
                                matched_asset_name = a_name
                                break

                    if not dl_url:
                        for a in assets:
                            a_name = a.get('name', '')
                            if a_name.lower().endswith('.exe'):
                                dl_url = a.get('browser_download_url')
                                matched_asset_name = a_name
                                break

                    if dl_url and tag:
                        app['version'] = tag
                        app['download_url'] = dl_url
                        if matched_asset_name:
                            app['asset_name'] = matched_asset_name
                        meta_cache[name] = {
                            'version': tag,
                            'download_url': dl_url,
                            'asset_name': matched_asset_name or app.get('asset_name'),
                            'updated_at': time.time()
                        }
                        updated_meta = True
            except Exception:
                # If API fails, construct fallback direct download url
                if not app.get('download_url') and app.get('asset_name'):
                    app['download_url'] = f"https://github.com/{repo}/releases/latest/download/{app['asset_name']}"

        if updated_meta:
            try:
                with open(self.meta_cache_file, 'w', encoding='utf-8') as f:
                    json.dump(meta_cache, f, indent=2)
            except Exception:
                pass

        self.finished.emit(apps)


class AppDownloadWorker(QObject):
    progress = pyqtSignal(str, int)
    finished = pyqtSignal(str, str, str)
    error = pyqtSignal(str, str)

    def __init__(self, app_data, app_base_path=None):
        super().__init__()
        self.app_data = app_data
        self.app_name = app_data['name']
        self.app_base_path = app_base_path
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        try:
            target_dir = get_app_install_dir(self.app_name, self.app_base_path)
            os.makedirs(target_dir, exist_ok=True)

            asset_name = self.app_data.get('asset_name') or f"{self.app_name}.exe"
            dl_url = self.app_data.get('download_url')

            if not dl_url:
                repo = self.app_data.get('repo', '').strip().rstrip('/')
                if repo.startswith('https://github.com/'):
                    repo = repo.replace('https://github.com/', '')
                if repo:
                    dl_url = f"https://github.com/{repo}/releases/latest/download/{asset_name}"

            if not dl_url:
                raise ValueError("No download URL available for this application.")

            target_exe = os.path.join(target_dir, asset_name)
            temp_path = os.path.join(target_dir, f".download_{asset_name}")

            def progress_cb(pct):
                self.progress.emit(self.app_name, pct)

            def cancel_check():
                return self._is_cancelled

            self.progress.emit(self.app_name, 5)

            download_file(
                dl_url,
                temp_path,
                progress_callback=progress_cb,
                cancel_check=cancel_check,
                timeout=60
            )

            if self._is_cancelled:
                if os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                    except OSError:
                        pass
                self.finished.emit(self.app_name, "cancelled", "")
                return

            # Atomic swap to target_exe
            if os.path.exists(target_exe):
                try:
                    os.remove(target_exe)
                except OSError:
                    pass
            os.replace(temp_path, target_exe)

            # Record version.txt
            version_str = self.app_data.get('version', '')
            if version_str:
                ver_file = os.path.join(target_dir, 'version.txt')
                try:
                    with open(ver_file, 'w', encoding='utf-8') as f:
                        f.write(version_str)
                except Exception:
                    pass

            # Auto run if requested
            if self.app_data.get('auto_run', True):
                try:
                    launch_app(self.app_data, self.app_base_path, target_exe)
                except Exception:
                    pass

            self.progress.emit(self.app_name, 100)
            self.finished.emit(self.app_name, "installed", target_exe)

        except Exception as e:
            if self._is_cancelled:
                self.finished.emit(self.app_name, "cancelled", "")
            else:
                self.error.emit(self.app_name, str(e))


class AppIconWorker(QObject):
    finished = pyqtSignal(str, QPixmap)
    error = pyqtSignal(str)

    def __init__(self, app_name, icon_url, save_path):
        super().__init__()
        self.app_name = app_name
        self.icon_url = icon_url
        self.save_path = save_path

    def run(self):
        try:
            res = cdn_get(self.icon_url, max_retries=2, timeout=8)
            pix = QPixmap()
            pix.loadFromData(res.content)
            if not pix.isNull():
                os.makedirs(os.path.dirname(self.save_path), exist_ok=True)
                pix.save(self.save_path)
            self.finished.emit(self.app_name, pix)
        except Exception as e:
            self.error.emit(str(e))
