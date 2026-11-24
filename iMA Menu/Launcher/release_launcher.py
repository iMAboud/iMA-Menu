#!/usr/bin/env python3
"""
Fast Launcher Release Script (Runs from Launcher/ folder or Root)
Reads APP_VERSION from launcher.pyw, compiles launcher.exe, and uploads it to GitHub (iMAboud/iMA-Menu-Plugins).
Does NOT touch native shell (src/), Inno Setup, or the main iMA-Menu repository.
"""

import os
import sys
import re
import json
import subprocess
import urllib.request
import urllib.parse
import urllib.error

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if os.path.basename(CURRENT_DIR).lower() == "launcher":
    LAUNCHER_DIR = CURRENT_DIR
    ROOT_DIR = os.path.dirname(CURRENT_DIR)
else:
    ROOT_DIR = CURRENT_DIR
    LAUNCHER_DIR = os.path.join(ROOT_DIR, "Launcher")

REPO = "iMAboud/iMA-Menu-Plugins"

def log(msg, level="INFO"):
    colors = {
        "INFO": "\033[94m",
        "SUCCESS": "\033[92m",
        "WARN": "\033[93m",
        "ERROR": "\033[91m",
        "RESET": "\033[0m"
    }
    print(f"{colors.get(level, '')}[{level}] {msg}{colors['RESET']}")

def get_wincred_token():
    try:
        helper = r"C:\Program Files\Git\mingw64\libexec\git-core\git-credential-wincred.exe"
        if not os.path.exists(helper):
            return None
        p = subprocess.Popen([helper, 'get'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        out, _ = p.communicate(input='protocol=https\nhost=github.com\n\n')
        for line in out.splitlines():
            if line.startswith('password='):
                return line.split('=', 1)[1].strip()
    except Exception:
        pass
    return None

def main():
    print("===================================================")
    print("      iMA Menu - Launcher Fast Release Tool       ")
    print("===================================================")

    # 1. Resolve version
    pyw_path = os.path.join(LAUNCHER_DIR, "launcher.pyw")
    if not os.path.exists(pyw_path):
        log(f"launcher.pyw not found at {pyw_path}", "ERROR")
        sys.exit(1)

    with open(pyw_path, "r", encoding="utf-8") as f:
        m = re.search(r"APP_VERSION\s*=\s*['\"]([^'\"]+)['\"]", f.read())
    if not m:
        log("Could not find APP_VERSION in launcher.pyw", "ERROR")
        sys.exit(1)

    version = m.group(1).strip()
    log(f"Detected Target Version: {version}", "INFO")

    # 2. Build launcher.exe
    log("Compiling launcher.exe via build_launcher.py...", "INFO")
    build_script = os.path.join(LAUNCHER_DIR, "build_launcher.py")
    res = subprocess.run([sys.executable, build_script], cwd=LAUNCHER_DIR)
    if res.returncode != 0:
        log("build_launcher.py failed!", "ERROR")
        sys.exit(res.returncode)

    # Locate compiled binary
    candidates = [
        os.path.join(ROOT_DIR, "dist", "launcher.exe"),
        os.path.join(LAUNCHER_DIR, "dist", "launcher.exe"),
        os.path.join(LAUNCHER_DIR, "launcher.exe"),
        os.path.join(ROOT_DIR, "launcher.exe")
    ]
    exe_path = None
    for c in candidates:
        if os.path.exists(c) and os.path.getsize(c) > 10000000:
            exe_path = c
            break

    if not exe_path:
        log("Compiled launcher.exe not found!", "ERROR")
        sys.exit(1)

    size_mb = os.path.getsize(exe_path) / (1024 * 1024)
    log(f"launcher.exe verified: {exe_path} ({size_mb:.2f} MB)", "SUCCESS")

    # 3. Retrieve GitHub Token
    token = get_wincred_token()
    if not token:
        log("GitHub token could not be retrieved from Windows Credential Manager!", "ERROR")
        sys.exit(1)

    headers = {
        "User-Agent": "iMA-Release-Tool",
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json"
    }

    # 4. Create or fetch GitHub release
    log(f"Querying GitHub release {version} on {REPO}...", "INFO")
    api_url = f"https://api.github.com/repos/{REPO}/releases"
    payload = json.dumps({
        "tag_name": version,
        "name": version,
        "prerelease": False,
        "draft": False
    }).encode("utf-8")

    req = urllib.request.Request(api_url, data=payload, headers=headers, method="POST")
    rel_data = None
    try:
        with urllib.request.urlopen(req) as resp:
            rel_data = json.loads(resp.read().decode())
            log(f"Created new GitHub release: {version}", "SUCCESS")
    except urllib.error.HTTPError as e:
        err_body = e.read().decode()
        if "already_exists" in err_body:
            log(f"Release {version} already exists. Fetching existing release...", "INFO")
            get_req = urllib.request.Request(f"{api_url}/tags/{version}", headers=headers)
            with urllib.request.urlopen(get_req) as gresp:
                rel_data = json.loads(gresp.read().decode())
        else:
            log(f"Failed to create release: {err_body}", "ERROR")
            sys.exit(1)

    if not rel_data:
        log("Could not obtain release metadata!", "ERROR")
        sys.exit(1)

    # 5. Remove previous launcher.exe asset if present
    for a in rel_data.get("assets", []):
        if a.get("name") == "launcher.exe":
            del_url = a.get("url")
            log(f"Removing old launcher.exe asset (id: {a.get('id')})...", "INFO")
            del_req = urllib.request.Request(del_url, headers=headers, method="DELETE")
            try:
                urllib.request.urlopen(del_req)
            except Exception as del_err:
                log(f"Warning on asset delete: {del_err}", "WARN")

    # 6. Upload launcher.exe
    upload_url = rel_data.get("upload_url", "").split("{")[0]
    upload_url = f"{upload_url}?name=launcher.exe"

    log("Reading launcher.exe into memory...", "INFO")
    with open(exe_path, "rb") as f:
        file_bytes = f.read()

    upload_headers = {
        "User-Agent": "iMA-Release-Tool",
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/octet-stream",
        "Content-Length": str(len(file_bytes))
    }

    log(f"Uploading launcher.exe ({size_mb:.2f} MB) to {REPO} release {version}...", "INFO")
    up_req = urllib.request.Request(upload_url, data=file_bytes, headers=upload_headers, method="POST")
    try:
        with urllib.request.urlopen(up_req) as up_resp:
            log(f"launcher.exe uploaded successfully to {REPO} release {version}!", "SUCCESS")
    except Exception as up_err:
        log(f"Asset upload failed: {up_err}", "ERROR")
        sys.exit(1)

    print("\n===================================================")
    log(f"RELEASE {version} COMPLETED SUCCESSFULLY!", "SUCCESS")
    print(f"URL: https://github.com/{REPO}/releases/tag/{version}")
    print("===================================================\n")

if __name__ == "__main__":
    main()
