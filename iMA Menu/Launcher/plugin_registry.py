import os
import json
import shutil
import hashlib
import ctypes
from ctypes import wintypes
from datetime import datetime, timezone


SCHEMA_VERSION = 2


class SHFILEOPSTRUCTW(ctypes.Structure):
    _fields_ = [
        ("hwnd", wintypes.HWND),
        ("wFunc", wintypes.UINT),
        ("pFrom", wintypes.LPCWSTR),
        ("pTo", wintypes.LPCWSTR),
        ("fFlags", wintypes.WORD),
        ("fAnyOperationsAborted", wintypes.BOOL),
        ("hNameMappings", wintypes.LPVOID),
        ("lpszProgressTitle", wintypes.LPCWSTR),
    ]


def delete_to_recycle_bin(path):
    if not os.path.exists(path):
        return True
    abs_path = os.path.abspath(path)
    buffer = abs_path + '\0\0'
    fileop = SHFILEOPSTRUCTW()
    fileop.hwnd = None
    fileop.wFunc = 0x0003
    fileop.pFrom = buffer
    fileop.pTo = None
    fileop.fFlags = 0x0040 | 0x0010
    try:
        res = ctypes.windll.shell32.SHFileOperationW(ctypes.byref(fileop))
        if res != 0 or fileop.fAnyOperationsAborted:
            if os.path.isdir(abs_path):
                shutil.rmtree(abs_path)
            else:
                os.remove(abs_path)
    except Exception:
        if os.path.isdir(abs_path):
            shutil.rmtree(abs_path)
        else:
            os.remove(abs_path)
    return True


def atomic_json_write(path, data):
    tmp = path + '.tmp'
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp, path)
    except Exception:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise


def safe_json_read(path):
    if not os.path.exists(path):
        return None
    try:
        with open(path, 'r', encoding='utf-8') as f:
            raw = f.read().strip()
        if not raw:
            return None
        data = json.loads(raw)
        return data
    except (json.JSONDecodeError, ValueError, IOError, OSError):
        return None


def git_blob_sha(filepath):
    try:
        with open(filepath, 'rb') as f:
            data = f.read()
        if filepath.endswith(('.nss', '.txt', '.json', '.md', '.py', '.bat', '.ps1')):
            data = data.replace(b'\r\n', b'\n')
        header = f"blob {len(data)}\0".encode('utf-8')
        return hashlib.sha1(header + data).hexdigest()
    except Exception:
        return None


def version_cmp(a, b):
    if not a or not b:
        return 0
    def parts(v):
        clean = str(v).strip().lstrip('vV').split('-')[0].split('+')[0]
        result = []
        for x in clean.split('.'):
            try:
                result.append(int(x))
            except ValueError:
                result.append(0)
        return result
    pa, pb = parts(a), parts(b)
    max_len = max(len(pa), len(pb))
    pa.extend([0] * (max_len - len(pa)))
    pb.extend([0] * (max_len - len(pb)))
    for x, y in zip(pa, pb):
        if x < y:
            return -1
        if x > y:
            return 1
    return 0


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _default_entry():
    return {
        'installed_version': None,
        'remote_version': None,
        'install_path': None,
        'installed_at': None,
        'file_count': 0,
        'file_hashes': {},
        'tree_sha': None,
        'status': 'not_installed'
    }


class PluginRegistry:

    def __init__(self, registry_path, plugins_dir):
        self._path = registry_path
        self._plugins_dir = plugins_dir
        self._data = {
            'schema_version': SCHEMA_VERSION,
            'last_remote_fetch': None,
            'cached_root_tree_sha': None,
            'plugins': {},
            'remote_manifest_cache': []
        }

    def load(self):
        raw = safe_json_read(self._path)
        if raw and isinstance(raw, dict) and raw.get('schema_version') == SCHEMA_VERSION:
            if isinstance(raw.get('plugins'), dict) and isinstance(raw.get('remote_manifest_cache'), list):
                self._data = raw
                return True
        return False

    def save(self):
        atomic_json_write(self._path, self._data)

    @property
    def plugins(self):
        return self._data['plugins']

    @property
    def remote_manifest_cache(self):
        return self._data['remote_manifest_cache']

    @remote_manifest_cache.setter
    def remote_manifest_cache(self, value):
        self._data['remote_manifest_cache'] = value

    @property
    def last_remote_fetch(self):
        return self._data.get('last_remote_fetch')

    @property
    def cached_root_tree_sha(self):
        return self._data.get('cached_root_tree_sha')

    @cached_root_tree_sha.setter
    def cached_root_tree_sha(self, value):
        self._data['cached_root_tree_sha'] = value

    def get_plugin_state(self, name):
        if name in self._data['plugins']:
            return self._data['plugins'][name]
        name_lower = name.lower()
        for k, v in self._data['plugins'].items():
            if k.lower() == name_lower:
                return v
        return _default_entry()

    def mark_installed(self, name, version, install_path, file_hashes=None, file_count=0):
        entry = self.get_plugin_state(name)
        entry['installed_version'] = version
        entry['install_path'] = install_path
        entry['installed_at'] = _now_iso()
        entry['file_count'] = file_count
        if file_hashes is not None:
            entry['file_hashes'] = file_hashes
        entry['status'] = 'installed'
        self._set_entry(name, entry)
        self.save()

    def mark_uninstalled(self, name):
        entry = self.get_plugin_state(name)
        entry['installed_version'] = None
        entry['install_path'] = None
        entry['installed_at'] = None
        entry['file_count'] = 0
        entry['file_hashes'] = {}
        entry['tree_sha'] = None
        entry['status'] = 'not_installed'
        self._set_entry(name, entry)
        self.save()

    def mark_update_available(self, name, changed_files=None):
        entry = self.get_plugin_state(name)
        if entry.get('status') in ('installed', 'update_available'):
            entry['status'] = 'update_available'
            if changed_files:
                entry['_changed_files'] = changed_files
            self._set_entry(name, entry)

    def mark_delisted(self, name):
        entry = self.get_plugin_state(name)
        if entry.get('installed_version'):
            entry['status'] = 'delisted'
            entry['remote_version'] = None
            self._set_entry(name, entry)

    def _set_entry(self, name, entry):
        name_lower = name.lower()
        to_delete = [k for k in self._data['plugins'] if k.lower() == name_lower and k != name]
        for k in to_delete:
            del self._data['plugins'][k]
        self._data['plugins'][name] = entry

    def merge_remote_manifest(self, remote_plugins, full_tree_data=None):
        if not isinstance(remote_plugins, list):
            return

        self._data['remote_manifest_cache'] = remote_plugins
        self._data['last_remote_fetch'] = _now_iso()

        remote_names_map = {}
        for rp in remote_plugins:
            if isinstance(rp, dict) and 'name' in rp:
                remote_names_map[rp['name'].lower()] = rp['name']

        for rp in remote_plugins:
            if not isinstance(rp, dict) or 'name' not in rp:
                continue
            name = rp['name']
            entry = self.get_plugin_state(name)
            rem_v = rp.get('version')
            entry['remote_version'] = rem_v
            inst_v = entry.get('installed_version')

            if inst_v and rem_v:
                if version_cmp(inst_v, rem_v) >= 0:
                    entry['status'] = 'installed'
                    entry.pop('_changed_files_count', None)
                else:
                    entry['status'] = 'update_available'
            elif inst_v:
                entry['status'] = 'installed'

            self._set_entry(name, entry)

        if full_tree_data and isinstance(full_tree_data, dict) and 'tree' in full_tree_data:
            self._check_file_changes(full_tree_data, remote_names_map)

        for name, entry in list(self._data['plugins'].items()):
            if name.lower() not in remote_names_map:
                if entry.get('installed_version'):
                    entry['status'] = 'delisted'
                    entry['remote_version'] = None
                else:
                    del self._data['plugins'][name]

        self.save()

    def _check_file_changes(self, full_tree_data, remote_names_map):
        tree_items = full_tree_data.get('tree', [])
        remote_file_map_lower = {}
        for item in tree_items:
            if item.get('type') != 'blob':
                continue
            path = item.get('path', '')
            parts = path.split('/', 1)
            if len(parts) == 2:
                plugin_name_lower = parts[0].lower()
                rel_path_lower = parts[1].lower()
                if plugin_name_lower not in remote_file_map_lower:
                    remote_file_map_lower[plugin_name_lower] = {}
                remote_file_map_lower[plugin_name_lower][rel_path_lower] = item.get('sha')

        for rp_lower, name in remote_names_map.items():
            entry = self.get_plugin_state(name)
            if not entry or not entry.get('installed_version'):
                continue

            inst_v = entry.get('installed_version')
            rem_v = entry.get('remote_version')

            # Strict Version Rule: If installed version matches or exceeds remote version, enforce status='installed'
            if inst_v and rem_v and version_cmp(inst_v, rem_v) >= 0:
                entry['status'] = 'installed'
                entry.pop('_changed_files_count', None)
                self._set_entry(name, entry)
                continue

            install_path = entry.get('install_path')
            if not install_path or not os.path.isdir(install_path):
                continue

            local_hashes = entry.get('file_hashes', {})
            remote_hashes = remote_file_map_lower.get(rp_lower, {})

            if not remote_hashes:
                continue

            if not local_hashes:
                local_hashes = self._compute_local_hashes(install_path)
                entry['file_hashes'] = remote_hashes
                entry['status'] = 'installed'
                self._set_entry(name, entry)
                continue

            local_hashes_lower = {k.lower(): v for k, v in local_hashes.items()}

            changed = []
            for rel_path_lower, remote_sha in remote_hashes.items():
                if rel_path_lower == 'version':
                    continue
                local_sha = local_hashes_lower.get(rel_path_lower)
                if local_sha and local_sha != remote_sha:
                    changed.append(rel_path_lower)

            if changed and rem_v and version_cmp(inst_v, rem_v) < 0:
                entry['status'] = 'update_available'
                entry['_changed_files_count'] = len(changed)
            else:
                entry['status'] = 'installed'
                entry.pop('_changed_files_count', None)

            self._set_entry(name, entry)

    def _compute_local_hashes(self, install_path):
        hashes = {}
        try:
            for root, dirs, files in os.walk(install_path):
                for fname in files:
                    if fname.lower() == 'version':
                        continue
                    full_path = os.path.join(root, fname)
                    rel_path = os.path.relpath(full_path, install_path).replace(os.sep, '/')
                    sha = git_blob_sha(full_path)
                    if sha:
                        hashes[rel_path] = sha
        except OSError:
            pass
        return hashes

    def reconcile_with_disk(self):
        if not os.path.isdir(self._plugins_dir):
            return

        disk_dirs_lower = {}
        try:
            for entry in os.scandir(self._plugins_dir):
                if entry.is_dir() and not entry.name.startswith('.'):
                    disk_dirs_lower[entry.name.lower()] = entry.name
        except OSError:
            return

        remote_names_lower = {}
        for rp in self._data.get('remote_manifest_cache', []):
            if isinstance(rp, dict) and 'name' in rp:
                remote_names_lower[rp['name'].lower()] = rp['name']

        for dir_lower, dir_name in disk_dirs_lower.items():
            dir_path = os.path.join(self._plugins_dir, dir_name)
            matched_name = remote_names_lower.get(dir_lower, dir_name)
            reg_entry = self.get_plugin_state(matched_name)

            if not reg_entry.get('installed_version'):
                version_file = os.path.join(dir_path, 'version')
                detected_version = None
                if os.path.exists(version_file):
                    try:
                        v = open(version_file, 'r').read().strip()
                        if v:
                            detected_version = v
                    except Exception:
                        pass

                has_content = False
                try:
                    has_content = any(True for _ in os.scandir(dir_path))
                except OSError:
                    pass

                if not has_content:
                    try:
                        shutil.rmtree(dir_path)
                    except OSError:
                        pass
                    continue

                rem_v = reg_entry.get('remote_version')
                reg_entry['installed_version'] = detected_version or rem_v or '1.0.0'
                reg_entry['install_path'] = dir_path
                reg_entry['status'] = 'installed'
                reg_entry['file_hashes'] = self._compute_local_hashes(dir_path)
                self._set_entry(matched_name, reg_entry)

        for name, entry in list(self._data['plugins'].items()):
            if entry.get('status') in ('installed', 'update_available', 'delisted'):
                install_path = entry.get('install_path')
                if install_path and not os.path.isdir(install_path):
                    alt_path = os.path.join(self._plugins_dir, name)
                    if os.path.isdir(alt_path):
                        entry['install_path'] = alt_path
                    elif name.lower() not in disk_dirs_lower:
                        entry['installed_version'] = None
                        entry['install_path'] = None
                        entry['installed_at'] = None
                        entry['file_count'] = 0
                        entry['file_hashes'] = {}
        # Special handling for iMA Switcher (check standard %LOCALAPPDATA%\iMA Switcher)
        switcher_appdata = os.path.join(os.getenv('LOCALAPPDATA', ''), 'iMA Switcher')
        switcher_exe = os.path.join(switcher_appdata, 'iMA Switcher.exe')
        if os.path.isfile(switcher_exe):
            s_entry = self.get_plugin_state('iMA Switcher')
            s_version = None
            for vf in ('version.txt', 'version'):
                v_file = os.path.join(switcher_appdata, vf)
                if os.path.exists(v_file):
                    try:
                        v = open(v_file, 'r', encoding='utf-8', errors='ignore').read().strip()
                        if v:
                            s_version = v.lstrip('vV')
                            break
                    except Exception:
                        pass
            
            rem_v = s_entry.get('remote_version')
            s_entry['installed_version'] = s_version or rem_v or '1.0.0'
            s_entry['install_path'] = switcher_appdata
            if rem_v and version_cmp(s_entry['installed_version'], rem_v) < 0:
                s_entry['status'] = 'update_available'
            else:
                s_entry['status'] = 'installed'
            self._set_entry('iMA Switcher', s_entry)

        self.save()

    def cleanup_staging(self):
        if not os.path.isdir(self._plugins_dir):
            return
        try:
            for entry in os.scandir(self._plugins_dir):
                if not entry.is_dir():
                    continue
                if entry.name.startswith('.staging_'):
                    try:
                        shutil.rmtree(entry.path)
                    except OSError:
                        pass
                elif entry.name.startswith('.backup_'):
                    real_name = entry.name[len('.backup_'):]
                    real_path = os.path.join(self._plugins_dir, real_name)
                    if os.path.isdir(real_path):
                        try:
                            shutil.rmtree(entry.path)
                        except OSError:
                            pass
                    else:
                        try:
                            os.rename(entry.path, real_path)
                        except OSError:
                            pass
        except OSError:
            pass

    def get_store_plugins_for_ui(self):
        result = []
        for rp in self._data.get('remote_manifest_cache', []):
            if not isinstance(rp, dict) or 'name' not in rp:
                continue
            name = rp['name']
            state = self.get_plugin_state(name)
            merged = dict(rp)
            merged['_installed_version'] = state.get('installed_version')
            merged['_status'] = state.get('status', 'not_installed')
            merged['_install_path'] = state.get('install_path') or os.path.join(self._plugins_dir, name)
            merged['_changed_files_count'] = state.get('_changed_files_count', 0)
            merged['_is_local'] = False
            result.append(merged)
        return result

    def get_local_plugins_for_ui(self):
        remote_names_lower = {rp['name'].lower() for rp in self._data.get('remote_manifest_cache', []) if isinstance(rp, dict) and 'name' in rp}
        result = []
        for name, entry in self._data['plugins'].items():
            if name.lower() not in remote_names_lower and entry.get('installed_version'):
                result.append({
                    'name': name,
                    'description': 'Custom local plugin',
                    'version': entry.get('installed_version') or '1.0.0',
                    '_installed_version': entry.get('installed_version'),
                    '_status': 'local',
                    '_install_path': entry.get('install_path') or os.path.join(self._plugins_dir, name),
                    '_is_local': True,
                })
        return result

    def get_all_plugins_for_ui(self):
        return self.get_store_plugins_for_ui()

    def is_installed(self, name):
        state = self.get_plugin_state(name)
        return state.get('status') in ('installed', 'update_available', 'delisted')

    def has_update(self, name):
        state = self.get_plugin_state(name)
        return state.get('status') == 'update_available'

    def is_delisted(self, name):
        state = self.get_plugin_state(name)
        return state.get('status') == 'delisted'

    def get_installed_version(self, name):
        return self.get_plugin_state(name).get('installed_version')

    def get_file_hashes(self, name):
        return self.get_plugin_state(name).get('file_hashes', {})
