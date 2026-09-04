import os
import re
import time
import subprocess
from PyQt5.QtCore import QObject, QTimer, QFileSystemWatcher, pyqtSignal
from utils import (PROJECT_ROOT, resource_path, safe_file_write, NSSAutoFixer)


class NSSErrorEntry:
    def __init__(self, timestamp, level, line, column, message, filename, raw):
        self.timestamp = timestamp
        self.level = level
        self.line = line
        self.column = column
        self.message = message
        self.filename = filename
        self.raw = raw

    def __repr__(self):
        return f"[{self.level}] {self.filename}:{self.line}:{self.column} - {self.message}"


_ERROR_PATTERN = re.compile(
    r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s+'
    r'\[(error|warning)\]\s+'
    r'line\[(\d+)\]\s+column\[(\d+)\][,]?\s+'
    r'(.*?)\s+"([^"]+)"',
    re.IGNORECASE
)

_WARNING_IMPORT_PATTERN = re.compile(
    r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s+'
    r'\[warning\]\s+'
    r'line\[(\d+)\]\s+column\[(\d+)\]\s+'
    r"invalid import file,\s+'([^']+)'",
    re.IGNORECASE
)


def parse_log_entries(text):
    entries = []
    # Strip any null bytes that might leak from bad decoding
    text = text.replace('\x00', '')
    for m in _ERROR_PATTERN.finditer(text):
        entries.append(NSSErrorEntry(
            timestamp=m.group(1),
            level=m.group(2).lower(),
            line=int(m.group(3)),
            column=int(m.group(4)),
            message=m.group(5).strip().rstrip(','),
            filename=m.group(6),
            raw=m.group(0)
        ))
    for m in _WARNING_IMPORT_PATTERN.finditer(text):
        entries.append(NSSErrorEntry(
            timestamp=m.group(1),
            level='warning',
            line=int(m.group(2)),
            column=int(m.group(3)),
            message='invalid import file',
            filename=os.path.basename(m.group(4)),
            raw=m.group(0)
        ))
    return entries


def resolve_nss_path(filename, project_root):
    shell_nss = os.path.join(project_root, 'shell.nss')
    if not os.path.exists(shell_nss):
        return None

    if filename.lower() == 'shell.nss':
        return shell_nss

    try:
        with open(shell_nss, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line.startswith("import "):
                    path_match = re.search(r"'([^']+)'", line)
                    if path_match:
                        rel = path_match.group(1)
                        if os.path.basename(rel).lower() == filename.lower():
                            full = os.path.normpath(os.path.join(project_root, rel))
                            if os.path.exists(full):
                                return full
    except Exception:
        pass

    search_dirs = [
        os.path.join(project_root, 'imports'),
        os.path.join(project_root, 'plugins')
    ]
    for d in search_dirs:
        if not os.path.exists(d):
            continue
        for root, _, files in os.walk(d):
            for f in files:
                if f.lower() == filename.lower():
                    return os.path.join(root, f)
    return None





class ShellLogMonitor(QObject):
    error_detected = pyqtSignal(str)
    fix_applied = pyqtSignal(str)
    manual_fix_required = pyqtSignal(str, int, str)

    MAX_FIX_ATTEMPTS = 2
    POLL_INTERVAL_MS = 15000

    def __init__(self, project_root, parent=None):
        super().__init__(parent)
        self.project_root = project_root
        self.log_path = os.path.join(project_root, 'shell.log')
        self._last_size = 0
        self._fix_attempts = {}
        self._enabled = True
        self._processing = False

        # Clear log on startup to prevent reading ancient history
        try:
            with open(self.log_path, 'w', encoding='utf-8') as f:
                f.write('')
        except Exception:
            pass

        self._poll_timer = QTimer(self)
        self._poll_timer.timeout.connect(self._poll_log)

        self._watcher = QFileSystemWatcher(self)
        if os.path.exists(self.log_path):
            self._watcher.addPath(self.log_path)
            self._last_size = os.path.getsize(self.log_path)
        self._watcher.fileChanged.connect(self._on_log_changed)

    def start(self):
        if os.path.exists(self.log_path):
            self._last_size = os.path.getsize(self.log_path)
        self._poll_timer.start(self.POLL_INTERVAL_MS)

    def stop(self):
        self._poll_timer.stop()

    def set_enabled(self, enabled):
        self._enabled = enabled

    def _on_log_changed(self, path):
        if not self._enabled or self._processing:
            return
        if os.path.exists(path) and path not in self._watcher.files():
            self._watcher.addPath(path)
        QTimer.singleShot(300, self._poll_log)

    def _poll_log(self):
        if not self._enabled or self._processing:
            return
        if not os.path.exists(self.log_path):
            return

        try:
            current_size = os.path.getsize(self.log_path)
        except Exception:
            return

        if current_size <= self._last_size and current_size > 0:
            if current_size < self._last_size:
                self._last_size = 0
            else:
                return

        new_data = self._read_new_data(current_size)
        if not new_data:
            return

        entries = parse_log_entries(new_data)
        errors = [e for e in entries if e.level == 'error']

        if not errors:
            return

        self._processing = True
        try:
            self._handle_errors(errors)
        finally:
            self._processing = False

    def _read_new_data(self, current_size):
        try:
            with open(self.log_path, 'rb') as f:
                f.seek(self._last_size)
                raw = f.read()
                self._last_size = current_size
            
            if not raw:
                return ""

            # Try utf-16 first as it's the most common for shell.log
            for enc in ['utf-16', 'utf-16-le', 'utf-8']:
                try:
                    text = raw.decode(enc)
                    if enc == 'utf-8' and '\x00' in text:
                        continue
                    return text
                except (UnicodeDecodeError, UnicodeError):
                    continue
            return ""
        except Exception:
            return ""

    def _handle_errors(self, errors):
        for error in errors:
            error_key = f"{error.filename}:{error.line}"

            if error_key not in self._fix_attempts:
                self._fix_attempts[error_key] = 0

            if self._fix_attempts[error_key] >= self.MAX_FIX_ATTEMPTS:
                self.manual_fix_required.emit(error.filename, error.line, error.message)
                continue

            self.error_detected.emit(str(error))

            filepath = resolve_nss_path(error.filename, self.project_root)
            if not filepath:
                continue

            success, msg = NSSAutoFixer.fix_error(filepath, error.line, error.column, error.message)
            self._fix_attempts[error_key] += 1

            if success:
                self.fix_applied.emit(f"{error.filename}:{error.line} - {msg}")
            else:
                self.manual_fix_required.emit(error.filename, error.line, error.message)

    def check_log_clean_after_reload(self):
        if not os.path.exists(self.log_path):
            return True
        try:
            current_size = os.path.getsize(self.log_path)
        except Exception:
            return True
        new_data = self._read_new_data(current_size)
        if not new_data:
            return True

        entries = parse_log_entries(new_data)
        errors = [e for e in entries if e.level == 'error']

        if errors:
            self._handle_errors(errors)
            return False

        return True

    def pre_reload_check(self):
        if not os.path.exists(self.log_path):
            return True
        try:
            current_size = os.path.getsize(self.log_path)
            new_data = self._read_new_data(current_size)
        except Exception:
            return True

        if not new_data:
            return True

        entries = parse_log_entries(new_data)
        errors = [e for e in entries if e.level == 'error']

        if not errors:
            return True

        self._processing = True
        try:
            self._handle_errors(errors)
        finally:
            self._processing = False

        time.sleep(0.5)
        return self.check_log_clean_after_reload()

