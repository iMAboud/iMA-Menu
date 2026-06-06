import os
import json
import zipfile
import shutil
import webbrowser
import threading
import time
import requests
import base64
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from PyQt5.QtCore import QObject, pyqtSignal

try:
    import win32crypt
except ImportError:
    win32crypt = None

CLIENT_ID = "GOOGLE_DRIVE_CLIENT_ID"
CLIENT_SECRET = "GOOGLE_DRIVE_CLIENT_SECRET"
REDIRECT_URI = "http://localhost:54321"
SCOPES = [
    "https://www.googleapis.com/auth/drive.appdata",
    "https://www.googleapis.com/auth/userinfo.email",
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
        else:
            self.send_response(400)
            self.end_headers()

    def log_message(self, format, *args):
        pass

class CloudSyncManager(QObject):
    auth_finished = pyqtSignal(bool, str)
    sync_progress = pyqtSignal(int, str)
    sync_finished = pyqtSignal(bool, str)

    def __init__(self, project_root):
        super().__init__()
        self.project_root = project_root
        self.access_token = None
        self.refresh_token = None
        self.user_email = None
        self.token_file = os.path.join(self.project_root, '.cloud_token.dat')
        self.local_port = 54321
        self.load_token()

    def _encrypt(self, data):
        if not win32crypt: return data
        try:
            encrypted = win32crypt.CryptProtectData(data.encode('utf-8'), u"iMA Menu Cloud Sync", None, None, None, 0)
            return base64.b64encode(encrypted).decode('utf-8')
        except: return data

    def _decrypt(self, encrypted_data):
        if not win32crypt: return encrypted_data
        try:
            decoded = base64.b64decode(encrypted_data)
            decrypted = win32crypt.CryptUnprotectData(decoded, None, None, None, 0)
            return decrypted[1].decode('utf-8')
        except: return None

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
            except: pass

    def save_token(self):
        data = {
            'access_token': self.access_token,
            'refresh_token': self.refresh_token,
            'email': self.user_email
        }
        json_data = json.dumps(data)
        encrypted_json = self._encrypt(json_data)
        with open(self.token_file, 'w') as f:
            f.write(encrypted_json)

    def logout(self):
        self.access_token = None
        self.refresh_token = None
        self.user_email = None
        if os.path.exists(self.token_file):
            os.remove(self.token_file)

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
            resp = requests.post(url, data=data)
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
        try:
            server = HTTPServer(('localhost', self.local_port), OAuthHandler)
            server.auth_code = None
            
            auth_url = (
                "https://accounts.google.com/o/oauth2/v2/auth?"
                f"client_id={CLIENT_ID}&"
                f"redirect_uri={REDIRECT_URI}&"
                "response_type=code&"
                f"scope={' '.join(SCOPES)}&"
                "access_type=offline&"
                "prompt=consent"
            )
            
            webbrowser.open(auth_url)
            
            start_time = time.time()
            while not server.auth_code and time.time() - start_time < 300:
                server.handle_request()
            
            if server.auth_code:
                url = "https://oauth2.googleapis.com/token"
                data = {
                    "code": server.auth_code,
                    "client_id": CLIENT_ID,
                    "client_secret": CLIENT_SECRET,
                    "redirect_uri": REDIRECT_URI,
                    "grant_type": "authorization_code"
                }
                resp = requests.post(url, data=data)
                if resp.status_code == 200:
                    res = resp.json()
                    
                    granted_scopes = res.get("scope", "").split()
                    if "https://www.googleapis.com/auth/drive.appdata" not in granted_scopes:
                        self.auth_finished.emit(False, "Permission denied: You must check the Google Drive box for sync to work.")
                        return

                    self.access_token = res.get("access_token")
                    self.refresh_token = res.get("refresh_token")
                    
                    user_info = requests.get(
                        "https://www.googleapis.com/oauth2/v3/userinfo",
                        headers={"Authorization": f"Bearer {self.access_token}"}
                    ).json()
                    self.user_email = user_info.get("email")
                    
                    self.save_token()
                    self.auth_finished.emit(True, self.user_email)
                else:
                    self.auth_finished.emit(False, f"Token exchange failed: {resp.text}")
            else:
                self.auth_finished.emit(False, "Login timed out or cancelled.")
                
        except Exception as e:
            self.auth_finished.emit(False, str(e))

    def backup(self):
        if not self.access_token:
            self.sync_finished.emit(False, "Not logged in")
            return
        threading.Thread(target=self._backup_thread, daemon=True).start()

    def _backup_thread(self):
        try:
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

            self.sync_progress.emit(40, "Syncing with Google Drive...")
            
            headers = {"Authorization": f"Bearer {self.access_token}"}
            search_url = "https://www.googleapis.com/drive/v3/files?spaces=appDataFolder&q=name='backup.zip'"
            resp = requests.get(search_url, headers=headers)
            
            if resp.status_code == 401:
                if self._refresh_access_token():
                    headers = {"Authorization": f"Bearer {self.access_token}"}
                    resp = requests.get(search_url, headers=headers)
            
            file_id = None
            if resp.status_code == 200:
                files = resp.json().get("files", [])
                if files: file_id = files[0].get("id")

            with open(zip_path, 'rb') as f:
                data = f.read()

            if file_id:
                url = f"https://www.googleapis.com/upload/drive/v3/files/{file_id}?uploadType=media"
                resp = requests.patch(url, headers=headers, data=data)
            else:
                metadata = {"name": "backup.zip", "parents": ["appDataFolder"]}
                url = "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart"
                files = {
                    'data': ('metadata', json.dumps(metadata), 'application/json'),
                    'file': ('application/zip', data)
                }
                resp = requests.post(url, headers=headers, files=files)

            if resp.status_code in [200, 201]:
                self.sync_progress.emit(100, "Backup complete!")
                self.sync_finished.emit(True, "Backup successfully synced to Google Drive.")
            else:
                self.sync_finished.emit(False, f"Upload failed: {resp.text}")

            if os.path.exists(zip_path): os.remove(zip_path)

        except Exception as e:
            self.sync_finished.emit(False, str(e))

    def restore(self):
        if not self.access_token:
            self.sync_finished.emit(False, "Not logged in")
            return
        threading.Thread(target=self._restore_thread, daemon=True).start()

    def _restore_thread(self):
        try:
            self.sync_progress.emit(10, "Searching for backup...")
            headers = {"Authorization": f"Bearer {self.access_token}"}
            search_url = "https://www.googleapis.com/drive/v3/files?spaces=appDataFolder&q=name='backup.zip'"
            resp = requests.get(search_url, headers=headers)
            
            if resp.status_code == 401:
                if self._refresh_access_token():
                    headers = {"Authorization": f"Bearer {self.access_token}"}
                    resp = requests.get(search_url, headers=headers)

            if resp.status_code == 200:
                files = resp.json().get("files", [])
                if not files:
                    self.sync_finished.emit(False, "No backup found in Google Drive.")
                    return
                file_id = files[0].get("id")
                
                self.sync_progress.emit(30, "Downloading from Google Drive...")
                url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media"
                resp = requests.get(url, headers=headers, stream=True)
                
                if resp.status_code == 200:
                    zip_path = os.path.join(self.project_root, 'restore.zip')
                    with open(zip_path, 'wb') as f:
                        for chunk in resp.iter_content(chunk_size=8192):
                            f.write(chunk)
                    
                    self.sync_progress.emit(70, "Extracting files...")
                    with zipfile.ZipFile(zip_path, 'r') as zipf:
                        for folder in ['imports', 'theme']:
                            f_path = os.path.join(self.project_root, folder)
                            if os.path.exists(f_path):
                                try:
                                    shutil.rmtree(f_path, ignore_errors=True)
                                except:
                                    pass
                        
                        zipf.extractall(self.project_root)
                    
                    self.sync_progress.emit(100, "Restore complete!")
                    self.sync_finished.emit(True, "Settings successfully restored. Please restart the app.")
                    
                    if os.path.exists(zip_path): os.remove(zip_path)
                else:
                    self.sync_finished.emit(False, f"Download failed: {resp.text}")
            else:
                self.sync_finished.emit(False, f"Search failed: {resp.text}")
                
        except Exception as e:
            self.sync_finished.emit(False, str(e))
