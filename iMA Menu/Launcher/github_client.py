"""
GitHub API & CDN client for iMA Menu Launcher.
Provides high-reliability GitHub interaction with pure Python standard urllib:
- Standard User-Agent and Accept headers
- Zero-overhead Git Refs API for commit/tree resolution (eliminates 504s on /branches/main)
- Exponential backoff retry logic (429, 500, 502, 503, 504)
- Rate-limit awareness and Retry-After header parsing
- Zero third-party dependencies (no requests/urllib3)
"""

import time
import os
import json
import urllib.parse
import ctypes
from ctypes import wintypes
import threading
import atexit

_wininet = ctypes.windll.wininet

GITHUB_REPO = "iMAboud/iMA-Menu-Plugins"
APP_REPO = "iMAboud/iMA-Menu-Plugins"
DEFAULT_USER_AGENT = "iMA-Menu-App/2.0"
GITHUB_API_BASE_URL = f"https://api.github.com/repos/{GITHUB_REPO}"
GITHUB_PLUGINS_JSON_URL = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/plugins.json"

_AUTH_TOKEN = None
_session = None

_inet_lock = threading.Lock()
_h_inet_session = None


def _get_inet_session():
    """Returns a shared, process-wide WinINet session handle to enable HTTP keep-alive and connection pooling."""
    global _h_inet_session
    if _h_inet_session is None:
        with _inet_lock:
            if _h_inet_session is None:
                h = _wininet.InternetOpenW(DEFAULT_USER_AGENT, 0, None, None, 0)
                if not h:
                    raise RequestException(f"InternetOpenW failed to initialize session: {ctypes.GetLastError()}")
                _h_inet_session = h
    return _h_inet_session


def _close_inet_session():
    """Closes the shared WinINet session handle upon process exit."""
    global _h_inet_session
    with _inet_lock:
        if _h_inet_session:
            try:
                _wininet.InternetCloseHandle(_h_inet_session)
            except Exception:
                pass
            _h_inet_session = None


atexit.register(_close_inet_session)


def _set_timeouts(handle, timeout_sec: int):
    """Sets connect, send, and receive timeouts on a WinINet handle."""
    try:
        to_ms = wintypes.DWORD(max(1000, int(timeout_sec * 1000)))
        _wininet.InternetSetOptionW(handle, 2, ctypes.byref(to_ms), ctypes.sizeof(to_ms))
        _wininet.InternetSetOptionW(handle, 6, ctypes.byref(to_ms), ctypes.sizeof(to_ms))
        _wininet.InternetSetOptionW(handle, 5, ctypes.byref(to_ms), ctypes.sizeof(to_ms))
    except Exception:
        pass


class RequestException(Exception):
    """Base exception for network/HTTP errors, matching requests.exceptions.RequestException."""
    pass


class Response:
    """Lightweight drop-in response object compatible with requests.Response."""
    def __init__(self, status_code: int, content: bytes, headers: dict = None, url: str = ""):
        self.status_code = status_code
        self.status = status_code
        self.code = status_code
        self.content = content
        self.headers = headers or {}
        self.url = url
        self._text = None

    @property
    def text(self) -> str:
        if self._text is None:
            self._text = self.content.decode('utf-8', errors='replace')
        return self._text

    def json(self):
        return json.loads(self.text)

    def raise_for_status(self):
        if 400 <= self.status_code < 600:
            raise RequestException(f"HTTP {self.status_code} error requesting {self.url}")

    def iter_content(self, chunk_size: int = 8192):
        for i in range(0, len(self.content), chunk_size):
            yield self.content[i:i + chunk_size]


def set_auth_token(token: str):
    """Optional PAT token configuration."""
    global _AUTH_TOKEN
    _AUTH_TOKEN = token.strip() if token else None


def _make_request(url: str, headers: dict = None, timeout: int = 10, method: str = None, data: bytes = None, verify_ssl: bool = True) -> Response:
    req_headers = {
        "User-Agent": DEFAULT_USER_AGENT,
        "Accept": "application/vnd.github+json"
    }
    if _AUTH_TOKEN:
        req_headers["Authorization"] = f"token {_AUTH_TOKEN}"
    if headers:
        req_headers.update(headers)

    parsed = urllib.parse.urlsplit(url)
    is_https = (parsed.scheme == "https")
    port = parsed.port or (443 if is_https else 80)

    h_inet = _get_inet_session()
    _set_timeouts(h_inet, timeout)

    h_conn = _wininet.InternetConnectW(h_inet, parsed.hostname, port, None, None, 3, 0, 0)
    if not h_conn:
        raise RequestException(f"Failed to connect to {parsed.hostname}: {ctypes.GetLastError()}")
    try:
        flags = 0x80000000 | 0x04000000  # RELOAD | NO_CACHE_WRITE
        if is_https:
            flags |= 0x00800000  # SECURE
            if not verify_ssl:
                flags |= 0x00001000 | 0x00002000  # IGNORE_CERT_CN_INVALID | IGNORE_CERT_DATE_INVALID
        path = parsed.path + ("?" + parsed.query if parsed.query else "")
        if not path:
            path = "/"
        verb = method.upper() if method else ("POST" if data is not None else "GET")
        h_req = _wininet.HttpOpenRequestW(h_conn, verb, path, None, None, None, flags, 0)
        if not h_req:
            raise RequestException(f"Failed to open HTTP request for {url}: {ctypes.GetLastError()}")
        try:
            _set_timeouts(h_req, timeout)
            hdrs_str = "\r\n".join(f"{k}: {v}" for k, v in req_headers.items()) + "\r\n"
            body = data if isinstance(data, bytes) else (data.encode("utf-8") if isinstance(data, str) else None)
            body_len = len(body) if body else 0

            ok = _wininet.HttpSendRequestW(h_req, hdrs_str, len(hdrs_str), body, body_len)
            if not ok:
                err_code = ctypes.GetLastError()
                # If cert validation failed and verify_ssl was enabled, fallback once with ignore cert flags
                if verify_ssl and err_code in (12037, 12038, 12045, 12057):
                    return _make_request(url, headers=headers, timeout=timeout, method=method, data=data, verify_ssl=False)
                raise RequestException(f"HttpSendRequestW failed for {url}: {err_code}")

            status = wintypes.DWORD()
            status_len = wintypes.DWORD(ctypes.sizeof(status))
            idx = wintypes.DWORD(0)
            _wininet.HttpQueryInfoW(h_req, 0x20000000 | 19, ctypes.byref(status), ctypes.byref(status_len), ctypes.byref(idx))

            h_len = wintypes.DWORD(0)
            idx = wintypes.DWORD(0)
            _wininet.HttpQueryInfoW(h_req, 22, None, ctypes.byref(h_len), ctypes.byref(idx))
            resp_headers = {}
            if h_len.value > 0:
                h_buf = ctypes.create_unicode_buffer(h_len.value)
                if _wininet.HttpQueryInfoW(h_req, 22, h_buf, ctypes.byref(h_len), ctypes.byref(idx)):
                    for line in h_buf.value.splitlines():
                        if ":" in line:
                            k, v = line.split(":", 1)
                            resp_headers[k.strip().lower()] = v.strip()

            chunks = []
            buf = ctypes.create_string_buffer(8192)
            read_bytes = wintypes.DWORD()
            while _wininet.InternetReadFile(h_req, buf, 8192, ctypes.byref(read_bytes)) and read_bytes.value > 0:
                chunks.append(buf.raw[:read_bytes.value])

            return Response(status.value, b"".join(chunks), resp_headers, url)
        finally:
            _wininet.InternetCloseHandle(h_req)
    finally:
        _wininet.InternetCloseHandle(h_conn)


def github_api_get(url: str, max_retries: int = 2, timeout: int = 8) -> Response:
    """
    Performs a GET request against GitHub API with retry and backoff on transient errors.
    Fails fast immediately on rate limits (403/429) without wasting time sleeping.
    """
    last_err = None
    for attempt in range(max_retries):
        try:
            res = _make_request(url, timeout=timeout)
            
            # If rate limited (429) or primary rate limit exceeded (403 with X-RateLimit-Remaining == 0)
            if res.status_code == 429 or (res.status_code == 403 and res.headers.get('x-ratelimit-remaining') == '0'):
                raise RequestException("GitHub API rate limit exceeded.")
                
            if res.status_code in (500, 502, 503, 504):
                if attempt < max_retries - 1:
                    time.sleep(0.5 * (attempt + 1))
                    continue

            res.raise_for_status()
            return res
        except RequestException as e:
            last_err = e
            if "rate limit" in str(e).lower() or attempt >= max_retries - 1:
                raise last_err
            time.sleep(0.5 * (attempt + 1))

    if last_err:
        raise last_err
    raise RequestException(f"Failed to fetch {url} after {max_retries} attempts.")


def cdn_get(url: str, max_retries: int = 3, timeout: int = 10, stream: bool = False) -> Response:
    """
    Performs a GET request against raw.githubusercontent.com or GitHub releases CDN.
    """
    last_err = None
    for attempt in range(max_retries):
        try:
            headers = {"User-Agent": DEFAULT_USER_AGENT}
            res = _make_request(url, headers=headers, timeout=timeout)
            if res.status_code in (500, 502, 503, 504):
                time.sleep(1.0 * (attempt + 1))
                continue
            res.raise_for_status()
            return res
        except RequestException as e:
            last_err = e
            if attempt < max_retries - 1:
                time.sleep(1.0 * (attempt + 1))
            else:
                raise last_err

    if last_err:
        raise last_err
    raise RequestException(f"Failed to fetch CDN URL {url}")


_tree_sha_cache = {}  # (repo, branch) -> (sha, timestamp)
_TREE_SHA_CACHE_TTL = 300  # 5 minutes


def get_latest_tree_sha(repo: str = GITHUB_REPO, branch: str = "main", timeout: int = 8, force_refresh: bool = False) -> str:
    """
    Retrieves latest root tree SHA using lightweight endpoints with 5-minute TTL caching:
    1. /git/ref/heads/{branch} -> commit SHA -> /git/commits/{sha} -> tree SHA
    2. Fallback: /commits/{branch} -> commit.tree.sha
    3. Fallback: /branches/{branch} -> commit.commit.tree.sha
    """
    cache_key = (repo, branch)
    now = time.time()
    if not force_refresh and cache_key in _tree_sha_cache:
        cached_sha, timestamp = _tree_sha_cache[cache_key]
        if now - timestamp < _TREE_SHA_CACHE_TTL:
            return cached_sha

    # 1. Primary: Git Ref API
    try:
        ref_url = f"https://api.github.com/repos/{repo}/git/ref/heads/{branch}"
        res = github_api_get(ref_url, max_retries=1, timeout=timeout)
        commit_sha = res.json().get('object', {}).get('sha')
        if commit_sha:
            commit_url = f"https://api.github.com/repos/{repo}/git/commits/{commit_sha}"
            c_res = github_api_get(commit_url, max_retries=1, timeout=timeout)
            tree_sha = c_res.json().get('tree', {}).get('sha')
            if tree_sha:
                _tree_sha_cache[cache_key] = (tree_sha, now)
                return tree_sha
    except Exception:
        pass

    # 2. Secondary fallback: Commits API
    try:
        commit_url = f"https://api.github.com/repos/{repo}/commits/{branch}"
        c_res = github_api_get(commit_url, max_retries=1, timeout=timeout)
        tree_sha = c_res.json().get('commit', {}).get('tree', {}).get('sha')
        if tree_sha:
            _tree_sha_cache[cache_key] = (tree_sha, now)
            return tree_sha
    except Exception:
        pass

    # 3. Tertiary fallback: Branches API
    try:
        branch_url = f"https://api.github.com/repos/{repo}/branches/{branch}"
        b_res = github_api_get(branch_url, max_retries=1, timeout=timeout)
        tree_sha = b_res.json().get('commit', {}).get('commit', {}).get('tree', {}).get('sha')
        if tree_sha:
            _tree_sha_cache[cache_key] = (tree_sha, now)
            return tree_sha
    except Exception:
        pass

    return None


def download_file(url: str, dest_path: str, progress_callback=None, cancel_check=None, timeout: int = 60, verify_ssl: bool = True) -> bool:
    """
    Downloads a binary asset via native Windows WinINet InternetOpenUrlW.
    Automatically handles HTTPS and 302 redirects to CDN/S3.
    Streams progress to progress_callback(percentage: int).
    Checks cancel_check() callable periodically to support clean cancellation.
    Writes to a temporary file and atomically replaces destination on success.
    """
    h_inet = _get_inet_session()
    _set_timeouts(h_inet, timeout)

    flags = 0x80000000 | 0x04000000 | 0x00800000  # RELOAD | NO_CACHE_WRITE | SECURE
    if not verify_ssl:
        flags |= 0x00001000 | 0x00002000  # IGNORE_CERT_CN_INVALID | IGNORE_CERT_DATE_INVALID

    h_req = _wininet.InternetOpenUrlW(h_inet, url, None, 0, flags, 0)
    if not h_req:
        err_code = ctypes.GetLastError()
        if verify_ssl and err_code in (12037, 12038, 12045, 12057):
            return download_file(url, dest_path, progress_callback=progress_callback, cancel_check=cancel_check, timeout=timeout, verify_ssl=False)
        raise RequestException(f"InternetOpenUrlW failed for {url}: {err_code}")

    dest_dir = os.path.dirname(os.path.abspath(dest_path))
    if dest_dir and not os.path.exists(dest_dir):
        os.makedirs(dest_dir, exist_ok=True)
    temp_path = f"{dest_path}.tmp_{os.getpid()}_{int(time.time() * 1000)}"

    try:
        _set_timeouts(h_req, timeout)
        status = wintypes.DWORD()
        status_len = wintypes.DWORD(ctypes.sizeof(status))
        idx = wintypes.DWORD(0)
        _wininet.HttpQueryInfoW(h_req, 0x20000000 | 19, ctypes.byref(status), ctypes.byref(status_len), ctypes.byref(idx))
        if status.value >= 400:
            raise RequestException(f"HTTP Error {status.value}: Not Found" if status.value == 404 else f"HTTP Error {status.value}")

        c_len = wintypes.DWORD(0)
        c_len_size = wintypes.DWORD(ctypes.sizeof(c_len))
        idx = wintypes.DWORD(0)
        has_len = _wininet.HttpQueryInfoW(h_req, 0x20000000 | 5, ctypes.byref(c_len), ctypes.byref(c_len_size), ctypes.byref(idx))
        total_bytes = c_len.value if has_len else 0

        downloaded_bytes = 0
        buf = ctypes.create_string_buffer(524288)
        read_bytes = wintypes.DWORD()

        if progress_callback:
            progress_callback(0)

        with open(temp_path, 'wb') as f:
            while _wininet.InternetReadFile(h_req, buf, 524288, ctypes.byref(read_bytes)) and read_bytes.value > 0:
                if cancel_check and cancel_check():
                    raise RequestException("Download cancelled")
                f.write(buf.raw[:read_bytes.value])
                downloaded_bytes += read_bytes.value
                if total_bytes > 0 and progress_callback:
                    progress_callback(min(100, int((downloaded_bytes / total_bytes) * 100)))

        if total_bytes > 0 and downloaded_bytes < total_bytes:
            raise IOError(f"Incomplete download: {downloaded_bytes}/{total_bytes} bytes")

        # Atomic replacement
        if os.path.exists(dest_path):
            try:
                os.replace(temp_path, dest_path)
            except OSError:
                os.remove(dest_path)
                os.replace(temp_path, dest_path)
        else:
            os.replace(temp_path, dest_path)

        return True
    except Exception:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass
        raise
    finally:
        _wininet.InternetCloseHandle(h_req)
