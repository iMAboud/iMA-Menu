import os
import json
import zipfile
import shutil
import threading
import time
import base64
import ctypes
from ctypes import wintypes
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse
from urllib.parse import urlparse, parse_qs
from PyQt5.QtCore import QObject, pyqtSignal
from github_client import _make_request, Response as _CloudResponse

def _http_request(url, method="GET", headers=None, data=None, files=None, timeout=30):
    req_headers = headers.copy() if headers else {}
    body = None

    if files:
        boundary = "----iMACloudSyncBoundary7MA4YWxk"
        parts = []
        for field, (fn, fdata, mime) in files.items():
            parts.append(f"--{boundary}\r\nContent-Type: {mime}; charset=UTF-8\r\n\r\n".encode('utf-8'))
            if isinstance(fdata, str):
                parts.append(fdata.encode('utf-8'))
            else:
                parts.append(fdata)
            parts.append(b"\r\n")
        parts.append(f"--{boundary}--\r\n".encode('utf-8'))
        body = b"".join(parts)
        req_headers["Content-Type"] = f"multipart/related; boundary={boundary}"
    elif data is not None:
        if isinstance(data, dict):
            body = urllib.parse.urlencode(data).encode('utf-8')
            if "Content-Type" not in req_headers:
                req_headers["Content-Type"] = "application/x-www-form-urlencoded"
        elif isinstance(data, str):
            body = data.encode('utf-8')
        elif isinstance(data, bytes):
            body = data

    try:
        return _make_request(url, headers=req_headers, timeout=timeout, method=method, data=body)
    except Exception as e:
        return _CloudResponse(500, str(e).encode('utf-8'), {}, url)

class _DATA_BLOB(ctypes.Structure):
    _fields_ = [
        ('cbData', wintypes.DWORD),
        ('pbData', ctypes.POINTER(ctypes.c_byte))
    ]

# Google OAuth Credentials
def _resolve_oauth_credentials():
    creds_file = os.path.join(CACHE_DIR, 'oauth_client.json')
    if os.path.exists(creds_file):
        try:
            with open(creds_file, 'r', encoding='utf-8') as cf:
                data = json.load(cf)
                return data.get('client_id', ''), data.get('client_secret', '')
        except Exception:
            pass
    return os.environ.get("GDRIVE_CLIENT_ID", ""), os.environ.get("GDRIVE_CLIENT_SECRET", "")

CLIENT_ID, CLIENT_SECRET = _resolve_oauth_credentials()
REDIRECT_URI = "http://localhost:54321"
SCOPES = [
    "https://www.googleapis.com/auth/drive.appdata",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "openid"
]

class OAuthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        query = urlparse(self.path).query
        params = parse_qs(query)
        if "code" in params:
            self.server.auth_code = params["code"][0]
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(b"<html><body style='font-family: sans-serif; background: #1e1e2e; color: white; display: flex; align-items: center; justify-content: center; height: 100vh;'><div><h1>Success!</h1><p>Authentication complete. You can close this window and return to the app.</p></div></body></html>")
        elif "error" in params:
            err_msg = params.get("error_description", params["error"])[0]
            self.server.auth_error = err_msg
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(b"<html><body style='font-family: sans-serif; background: #1e1e2e; color: #ea999c; display: flex; align-items: center; justify-content: center; height: 100vh;'><div><h1>Authentication Cancelled</h1><p>You may close this window and return to the app.</p></div></body></html>")
        else:
            self.send_response(400)
            self.end_headers()

    def log_message(self, format, *args):
        pass


class OAuthServer(HTTPServer):
    """Local loopback HTTP server for OAuth redirection without FQDN reverse lookup."""
    def server_bind(self):
        import socketserver
        socketserver.TCPServer.server_bind(self)
        host, port = self.server_address[:2]
        self.server_name = host
        self.server_port = port


class CloudSyncManager(QObject):
    auth_finished = pyqtSignal(bool, str)
    sync_progress = pyqtSignal(int, str)
    sync_finished = pyqtSignal(bool, str)
    profile_updated = pyqtSignal()
    conflict_detected = pyqtSignal(list, str)

    def __init__(self, project_root):
        super().__init__()
        self.project_root = project_root
        self.access_token = None
        self.refresh_token = None
        self.user_email = None
        self.user_name = None
        self.user_picture = None
        self.token_file = os.path.join(self.project_root, '.cloud_token.dat')
        self.local_port = 54321
        self.load_token()

    def _encrypt(self, data):
        try:
            crypt32 = ctypes.windll.crypt32
            kernel32 = ctypes.windll.kernel32
            data_bytes = data.encode('utf-8')
            blob_in = _DATA_BLOB(len(data_bytes), ctypes.cast(ctypes.create_string_buffer(data_bytes), ctypes.POINTER(ctypes.c_byte)))
            blob_out = _DATA_BLOB()
            if crypt32.CryptProtectData(ctypes.byref(blob_in), 'iMA Menu Cloud Sync', None, None, None, 0, ctypes.byref(blob_out)):
                out_bytes = ctypes.string_at(blob_out.pbData, blob_out.cbData)
                kernel32.LocalFree(blob_out.pbData)
                return base64.b64encode(out_bytes).decode('utf-8')
            return data
        except Exception:
            return data

    def _decrypt(self, encrypted_data):
        try:
            crypt32 = ctypes.windll.crypt32
            kernel32 = ctypes.windll.kernel32
            enc_bytes = base64.b64decode(encrypted_data)
            blob_in = _DATA_BLOB(len(enc_bytes), ctypes.cast(ctypes.create_string_buffer(enc_bytes), ctypes.POINTER(ctypes.c_byte)))
            blob_out = _DATA_BLOB()
            if crypt32.CryptUnprotectData(ctypes.byref(blob_in), None, None, None, None, 0, ctypes.byref(blob_out)):
                out_bytes = ctypes.string_at(blob_out.pbData, blob_out.cbData)
                kernel32.LocalFree(blob_out.pbData)
                return out_bytes.decode('utf-8')
            return None
        except Exception:
            return None

    def load_token(self):
        if os.path.exists(self.token_file):
            try:
                with open(self.token_file, 'r') as f:
                    encrypted_json = f.read()
                
                decrypted_json = self._decrypt(encrypted_json)
                if decrypted_json:
                    data = json.loads(decrypted_json)
                    self.access_token = data.get('access_token')
                    self.refresh_token = data.get('refresh_token')
                    self.user_email = data.get('email')
                    self.user_name = data.get('name')
                    self.user_picture = data.get('picture')
            except: pass

    def save_token(self):
        data = {
            'access_token': self.access_token,
            'refresh_token': self.refresh_token,
            'email': self.user_email,
            'name': self.user_name,
            'picture': self.user_picture
        }
        json_data = json.dumps(data)
        encrypted_json = self._encrypt(json_data)
        with open(self.token_file, 'w') as f:
            f.write(encrypted_json)

    def logout(self):
        self.access_token = None
        self.refresh_token = None
        self.user_email = None
        self.user_name = None
        self.user_picture = None
        if os.path.exists(self.token_file):
            try: os.remove(self.token_file)
            except: pass
        avatar_path = os.path.join(self.project_root, 'cache', 'profile_avatar.png')
        if os.path.exists(avatar_path):
            try: os.remove(avatar_path)
            except: pass
        self.profile_updated.emit()

    def _download_avatar(self, picture_url):
        if not picture_url:
            return None
        avatar_path = os.path.join(self.project_root, 'cache', 'profile_avatar.png')
        try:
            os.makedirs(os.path.dirname(avatar_path), exist_ok=True)
            resp = _http_request(picture_url, timeout=15)
            if resp.status_code == 200 and resp.content:
                with open(avatar_path, 'wb') as f:
                    f.write(resp.content)
                return avatar_path
        except Exception:
            pass
        return avatar_path if os.path.exists(avatar_path) else None

    def _fetch_profile_info(self):
        if not self.access_token:
            return
        try:
            user_info_resp = _http_request(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {self.access_token}"}
            )
            if user_info_resp.status_code == 401:
                if self._refresh_access_token():
                    user_info_resp = _http_request(
                        "https://www.googleapis.com/oauth2/v3/userinfo",
                        headers={"Authorization": f"Bearer {self.access_token}"}
                    )
            if user_info_resp.status_code == 200:
                user_info = user_info_resp.json()
                if not self.user_email or not str(self.user_email).strip():
                    self.user_email = user_info.get("email")
                if user_info.get("name"):
                    self.user_name = user_info.get("name")
                if user_info.get("picture"):
                    self.user_picture = user_info.get("picture")

            if not self.user_name or not self.user_picture:
                drive_resp = _http_request(
                    "https://www.googleapis.com/drive/v3/about?fields=user",
                    headers={"Authorization": f"Bearer {self.access_token}"}
                )
                if drive_resp.status_code == 200:
                    d_user = drive_resp.json().get("user", {})
                    if not self.user_name and d_user.get("displayName"):
                        self.user_name = d_user.get("displayName")
                    if not self.user_picture and d_user.get("photoLink"):
                        self.user_picture = d_user.get("photoLink")
                    if not self.user_email and d_user.get("emailAddress"):
                        self.user_email = d_user.get("emailAddress")

            if not self.user_name and self.user_email:
                self.user_name = self.user_email.split('@')[0]

            if self.user_picture:
                self._download_avatar(self.user_picture)

            self.save_token()
            self.profile_updated.emit()
        except Exception:
            pass

    def fetch_user_profile(self, background=True):
        if background:
            threading.Thread(target=self._fetch_profile_info, daemon=True).start()
        else:
            self._fetch_profile_info()

    def _refresh_access_token(self):
        if not self.refresh_token: return False
        try:
            url = "https://oauth2.googleapis.com/token"
            data = {
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "refresh_token": self.refresh_token,
                "grant_type": "refresh_token"
            }
            resp = _http_request(url, method="POST", data=data)
            if resp.status_code == 200:
                res = resp.json()
                self.access_token = res.get("access_token")
                self.save_token()
                return True
        except: pass
        return False

    def login(self):
        threading.Thread(target=self._login_thread, daemon=True).start()

    def _login_thread(self):
        server = None
        try:
            server = OAuthServer(('localhost', self.local_port), OAuthHandler)
            server.timeout = 1.0
            server.auth_code = None
            server.auth_error = None

            auth_url = (
                "https://accounts.google.com/o/oauth2/v2/auth?"
                f"client_id={CLIENT_ID}&"
                f"redirect_uri={REDIRECT_URI}&"
                "response_type=code&"
                f"scope={' '.join(SCOPES)}&"
                "access_type=offline&"
                "prompt=consent"
            )

            ctypes.windll.shell32.ShellExecuteW(None, "open", auth_url, None, None, 1)

            # Wait for code
            start_time = time.time()
            while not server.auth_code and not server.auth_error and time.time() - start_time < 300:
                server.handle_request()

            if server.auth_error:
                self.auth_finished.emit(False, f"Login cancelled: {server.auth_error}")
                return

            if server.auth_code:
                url = "https://oauth2.googleapis.com/token"
                data = {
                    "code": server.auth_code,
                    "client_id": CLIENT_ID,
                    "client_secret": CLIENT_SECRET,
                    "redirect_uri": REDIRECT_URI,
                    "grant_type": "authorization_code"
                }
                resp = _http_request(url, method="POST", data=data)
                if resp.status_code == 200:
                    res = resp.json()

                    # Verify that the user actually granted the Drive permission
                    granted_scopes = res.get("scope", "").split()
                    if "https://www.googleapis.com/auth/drive.appdata" not in granted_scopes:
                        self.auth_finished.emit(False, "Permission denied: You must check the Google Drive box for sync to work.")
                        return

                    self.access_token = res.get("access_token")
                    self.refresh_token = res.get("refresh_token")

                    self._fetch_profile_info()
                    self.auth_finished.emit(True, self.user_email or "Google Drive")
                else:
                    self.auth_finished.emit(False, f"Token exchange failed: {resp.text}")
            else:
                self.auth_finished.emit(False, "Login timed out or cancelled.")

        except Exception as e:
            self.auth_finished.emit(False, str(e))
        finally:
            if server:
                try:
                    server.server_close()
                except Exception:
                    pass

    def backup(self, silent=False):
        if not self.access_token:
            if not silent:
                self.sync_finished.emit(False, "Not logged in")
            return
        threading.Thread(target=self._backup_thread, args=(silent,), daemon=True).start()

    def _backup_thread(self, silent=False):
        try:
            if not silent:
                self.sync_progress.emit(10, "Compressing files...")
            zip_path = os.path.join(self.project_root, 'backup.zip')
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for folder in ['imports', 'theme']:
                    path = os.path.join(self.project_root, folder)
                    if os.path.exists(path):
                        for root, _, files in os.walk(path):
                            for f in files:
                                fp = os.path.join(root, f)
                                zipf.write(fp, os.path.relpath(fp, self.project_root))
                
                shell_nss = os.path.join(self.project_root, 'shell.nss')
                if os.path.exists(shell_nss):
                    zipf.write(shell_nss, 'shell.nss')

            if not silent:
                self.sync_progress.emit(40, "Syncing with Google Drive...")
            
            headers = {"Authorization": f"Bearer {self.access_token}"}
            search_url = "https://www.googleapis.com/drive/v3/files?spaces=appDataFolder&q=name='backup.zip'"
            resp = _http_request(search_url, headers=headers)
            
            if resp.status_code == 401:
                if self._refresh_access_token():
                    headers = {"Authorization": f"Bearer {self.access_token}"}
                    resp = _http_request(search_url, headers=headers)
            
            file_id = None
            if resp.status_code == 200:
                files = resp.json().get("files", [])
                if files: file_id = files[0].get("id")

            with open(zip_path, 'rb') as f:
                data = f.read()

            if file_id:
                url = f"https://www.googleapis.com/upload/drive/v3/files/{file_id}?uploadType=media"
                resp = _http_request(url, method="PATCH", headers=headers, data=data)
            else:
                metadata = {"name": "backup.zip", "parents": ["appDataFolder"]}
                url = "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart"
                files = {
                    'data': ('metadata', json.dumps(metadata), 'application/json'),
                    'file': ('backup.zip', data, 'application/zip')
                }
                resp = _http_request(url, method="POST", headers=headers, files=files)

            if resp.status_code in [200, 201]:
                if not silent:
                    self.sync_progress.emit(100, "Backup complete!")
                self.sync_finished.emit(True, "Backup successfully synced to Google Drive.")
            else:
                if not silent:
                    self.sync_finished.emit(False, f"Upload failed: {resp.text}")

            if os.path.exists(zip_path): os.remove(zip_path)

        except Exception as e:
            if not silent:
                self.sync_finished.emit(False, str(e))

    def get_remote_backup_info(self):
        if not self.access_token:
            if not self._refresh_access_token():
                return {"exists": False, "error": "Not logged in"}
        try:
            headers = {"Authorization": f"Bearer {self.access_token}"}
            search_url = "https://www.googleapis.com/drive/v3/files?spaces=appDataFolder&q=name='backup.zip'&fields=files(id,name,modifiedTime,size)"
            resp = _http_request(search_url, headers=headers)
            if resp.status_code == 401:
                if self._refresh_access_token():
                    headers = {"Authorization": f"Bearer {self.access_token}"}
                    resp = _http_request(search_url, headers=headers)
            if resp.status_code == 200:
                files = resp.json().get("files", [])
                if files:
                    f = files[0]
                    return {
                        "exists": True,
                        "id": f.get("id"),
                        "name": f.get("name"),
                        "modifiedTime": f.get("modifiedTime"),
                        "size": f.get("size")
                    }
                return {"exists": False}
            return {"exists": False, "error": resp.text}
        except Exception as e:
            return {"exists": False, "error": str(e)}

    def get_backup_revisions(self):
        if not self.access_token:
            if not self._refresh_access_token():
                return {"success": False, "error": "Not logged in"}
        try:
            headers = {"Authorization": f"Bearer {self.access_token}"}
            search_url = "https://www.googleapis.com/drive/v3/files?spaces=appDataFolder&q=name='backup.zip'&fields=files(id,name,modifiedTime,size)"
            resp = _http_request(search_url, headers=headers)
            if resp.status_code == 401:
                if self._refresh_access_token():
                    headers = {"Authorization": f"Bearer {self.access_token}"}
                    resp = _http_request(search_url, headers=headers)
            if resp.status_code != 200:
                return {"success": False, "error": f"Search failed: {resp.text}"}

            files = resp.json().get("files", [])
            if not files:
                return {"success": False, "error": "No backup found in Google Drive."}

            file_id = files[0].get("id")
            rev_url = f"https://www.googleapis.com/drive/v3/files/{file_id}/revisions?fields=revisions(id,modifiedTime,size,keepForever)"
            rev_resp = _http_request(rev_url, headers=headers)
            if rev_resp.status_code == 401:
                if self._refresh_access_token():
                    headers = {"Authorization": f"Bearer {self.access_token}"}
                    rev_resp = _http_request(rev_url, headers=headers)

            if rev_resp.status_code == 200:
                revs = rev_resp.json().get("revisions", [])
                return {"success": True, "file_id": file_id, "revisions": revs}
            return {"success": False, "error": f"Failed to get revisions: {rev_resp.text}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def restore(self, revision_id=None):
        if not self.access_token:
            if not self._refresh_access_token():
                self.sync_finished.emit(False, "Not logged in")
                return
        threading.Thread(target=self._restore_thread, args=(revision_id,), daemon=True).start()

    def _restore_thread(self, revision_id=None):
        try:
            self.sync_progress.emit(10, "Searching for backup...")
            headers = {"Authorization": f"Bearer {self.access_token}"}
            search_url = "https://www.googleapis.com/drive/v3/files?spaces=appDataFolder&q=name='backup.zip'"
            resp = _http_request(search_url, headers=headers)
            
            if resp.status_code == 401:
                if self._refresh_access_token():
                    headers = {"Authorization": f"Bearer {self.access_token}"}
                    resp = _http_request(search_url, headers=headers)

            if resp.status_code == 200:
                files = resp.json().get("files", [])
                if not files:
                    self.sync_finished.emit(False, "No backup found in Google Drive.")
                    return
                file_id = files[0].get("id")
                
                self.sync_progress.emit(30, "Downloading from Google Drive...")
                if revision_id:
                    url = f"https://www.googleapis.com/drive/v3/files/{file_id}/revisions/{revision_id}?alt=media"
                else:
                    url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media"
                resp = _http_request(url, headers=headers)
                
                if resp.status_code == 200:
                    zip_path = os.path.join(self.project_root, 'restore.zip')
                    with open(zip_path, 'wb') as f:
                        for chunk in resp.iter_content(chunk_size=8192):
                            f.write(chunk)
                    
                    self.sync_progress.emit(50, "Checking for file conflicts...")
                    conflicts = []
                    try:
                        with zipfile.ZipFile(zip_path, 'r') as zipf:
                            for info in zipf.infolist():
                                if info.is_dir():
                                    continue
                                rel_path = info.filename.replace('\\', '/')
                                local_path = os.path.join(self.project_root, rel_path)
                                if os.path.exists(local_path):
                                    try:
                                        with open(local_path, 'rb') as lf:
                                            local_data = lf.read()
                                        cloud_data = zipf.read(info)
                                        if local_data != cloud_data:
                                            local_mtime = os.path.getmtime(local_path)
                                            cloud_dt = info.date_time
                                            cloud_mtime = time.mktime(cloud_dt + (0, 0, -1))
                                            conflicts.append({
                                                'path': rel_path,
                                                'local_mtime': local_mtime,
                                                'cloud_mtime': cloud_mtime,
                                                'local_size': len(local_data),
                                                'cloud_size': len(cloud_data)
                                            })
                                    except Exception:
                                        pass
                    except Exception:
                        pass

                    if conflicts:
                        self.conflict_detected.emit(conflicts, zip_path)
                    else:
                        self._apply_restore_thread(zip_path, None)
                else:
                    self.sync_finished.emit(False, f"Download failed: {resp.text}")
            else:
                self.sync_finished.emit(False, f"Search failed: {resp.text}")
                
        except Exception as e:
            self.sync_finished.emit(False, str(e))

    def apply_restore(self, zip_path, selected_relpaths=None):
        threading.Thread(target=self._apply_restore_thread, args=(zip_path, selected_relpaths), daemon=True).start()

    def _apply_restore_thread(self, zip_path, selected_relpaths=None):
        snapshot_zip = None
        try:
            self.sync_progress.emit(60, "Creating safety rollback snapshot...")
            snapshot_dir = os.path.join(self.project_root, 'cache')
            os.makedirs(snapshot_dir, exist_ok=True)
            snapshot_zip = os.path.join(snapshot_dir, '.pre_restore_snapshot.zip')
            try:
                with zipfile.ZipFile(snapshot_zip, 'w', zipfile.ZIP_DEFLATED) as s_zip:
                    for folder in ['imports', 'theme']:
                        p = os.path.join(self.project_root, folder)
                        if os.path.exists(p):
                            for root, _, files in os.walk(p):
                                for f in files:
                                    fp = os.path.join(root, f)
                                    s_zip.write(fp, os.path.relpath(fp, self.project_root))
                    sh_nss = os.path.join(self.project_root, 'shell.nss')
                    if os.path.exists(sh_nss):
                        s_zip.write(sh_nss, 'shell.nss')
            except Exception:
                snapshot_zip = None

            self.sync_progress.emit(75, "Extracting files in-place...")
            with zipfile.ZipFile(zip_path, 'r') as zipf:
                sel_set = {p.replace('\\', '/').lower() for p in selected_relpaths} if selected_relpaths is not None else None
                archive_relpaths = set()

                for info in zipf.infolist():
                    if info.is_dir():
                        continue
                    rel = info.filename.replace('\\', '/')
                    archive_relpaths.add(rel.lower())
                    if sel_set is not None and rel.lower() not in sel_set:
                        continue
                    dest_path = os.path.join(self.project_root, rel)
                    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                    with zipf.open(info) as src, open(dest_path, 'wb') as dst:
                        shutil.copyfileobj(src, dst)

                # Clean obsolete files during full restore without deleting directory roots
                if selected_relpaths is None:
                    for folder in ['imports', 'theme']:
                        base_p = os.path.join(self.project_root, folder)
                        if os.path.exists(base_p):
                            for root, _, files in os.walk(base_p):
                                for f in files:
                                    fp = os.path.join(root, f)
                                    rel = os.path.relpath(fp, self.project_root).replace('\\', '/').lower()
                                    if rel not in archive_relpaths:
                                        try:
                                            os.remove(fp)
                                        except Exception:
                                            pass

            self.sync_progress.emit(100, "Restore complete!")
            self.sync_finished.emit(True, "Settings successfully restored. Please restart the app.")
        except Exception as e:
            if snapshot_zip and os.path.exists(snapshot_zip):
                try:
                    with zipfile.ZipFile(snapshot_zip, 'r') as s_zip:
                        s_zip.extractall(self.project_root)
                except Exception:
                    pass
            self.sync_finished.emit(False, f"Restore failed: {e}")
        finally:
            if os.path.exists(zip_path):
                try: os.remove(zip_path)
                except: pass

    def cancel_restore(self, zip_path):
        if os.path.exists(zip_path):
            try: os.remove(zip_path)
            except: pass
        self.sync_finished.emit(False, "Restore cancelled. Local files kept.")
