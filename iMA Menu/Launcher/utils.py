import sys
import os
import tempfile
import shutil
import ctypes
import time
import subprocess
from ctypes import wintypes
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QDialogButtonBox, QUndoStack, QUndoCommand
from PyQt5.QtGui import QPainter, QColor, QFont, QIcon, QPixmap, QFontDatabase, QPainterPath, QPen, QFontMetrics
from PyQt5.QtCore import Qt, QRunnable, pyqtSignal, QObject, QThreadPool, QEvent

global_undo_stack = QUndoStack()

class FileChangeCommand(QUndoCommand):
    def __init__(self, filepath, old_content, new_content, success_cb=None, error_cb=None):
        super().__init__()
        self.filepath = filepath
        self.old_content = old_content
        self.new_content = new_content
        self.success_cb = success_cb
        self.error_cb = error_cb

    def redo(self):
        AsyncFileIo.write(self.filepath, self.new_content, self.success_cb, self.error_cb)

    def undo(self):
        AsyncFileIo.write(self.filepath, self.old_content, self.success_cb, self.error_cb)

NILESOFT_FONT_FAMILY = 'Nilesoft.Shell'
_font_initialized = False

def _init_nilesoft_font():
    global NILESOFT_FONT_FAMILY, _font_initialized
    if _font_initialized and NILESOFT_FONT_FAMILY in QFontDatabase().families(): return
    font_path = resource_path('nilesoft.ttf')
    if os.path.exists(font_path):
        font_id = QFontDatabase.addApplicationFont(font_path)
        if font_id != -1:
            fams = QFontDatabase.applicationFontFamilies(font_id)
            if fams:
                NILESOFT_FONT_FAMILY = fams[0]
                _font_initialized = True
                return
    try:
        from extract_font import extract_ttf
        dll_path = os.path.join(os.path.dirname(resource_path('')), 'shell.dll')
        if os.path.exists(dll_path):
            if extract_ttf(dll_path, font_path):
                font_id = QFontDatabase.addApplicationFont(font_path)
                if font_id != -1:
                    fams = QFontDatabase.applicationFontFamilies(font_id); NILESOFT_FONT_FAMILY = fams[0]; _font_initialized = True
    except: pass

def get_font_icon(glyph, size=32, color='#cdd6f4'):
    _init_nilesoft_font()
    pixmap = QPixmap(size, size); pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap); painter.setRenderHint(QPainter.Antialiasing)
    font = QFont(NILESOFT_FONT_FAMILY, size // 2)
    fm = QFontMetrics(font); rect = fm.boundingRect(glyph)
    path = QPainterPath()
    path.addText((size - rect.width())/2 - rect.x(), (size - rect.height())/2 - rect.y(), font, glyph)
    painter.setPen(QPen(QColor(0, 0, 0, 180), 2.5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    painter.drawPath(path)
    painter.fillPath(path, QColor(color)); painter.end()
    return QIcon(pixmap)

def get_mdl2_icon(glyph_code, size=32, color='#ffffff'):
    pixmap = QPixmap(size, size); pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap); painter.setRenderHint(QPainter.Antialiasing)
    font = QFont('Segoe MDL2 Assets', int(size * 0.55))
    font.setWeight(QFont.Bold)
    glyph = chr(glyph_code) if isinstance(glyph_code, int) else glyph_code
    fm = QFontMetrics(font); rect = fm.boundingRect(glyph)
    path = QPainterPath()
    path.addText((size - rect.width())/2 - rect.x(), (size - rect.height())/2 - rect.y(), font, glyph)
    painter.setPen(QPen(QColor(0, 0, 0, 120), 1.5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    painter.drawPath(path)
    painter.fillPath(path, QColor(color)); painter.end()
    return QIcon(pixmap)

class UnsavedChangesDialog(QDialog):
    def __init__(self, parent=None, text='You have unsaved changes. Do you want to save them?'):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setObjectName('customMessageBox')
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        label = QLabel(text)
        label.setStyleSheet('color: #ffffff; font-size: 14px; padding: 10px;')
        layout.addWidget(label)
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("secondaryButton")
        cancel_btn.setStyleSheet("""
            QPushButton { 
                background-color: rgba(255, 255, 255, 0.1); 
                color: white; 
                border-radius: 12px; 
                border: 1px solid rgba(255, 255, 255, 0.2);
                font-weight: bold;
            } 
            QPushButton:hover { 
                background-color: rgba(255, 255, 255, 0.2); 
            }
        """)
        cancel_btn.setFixedSize(80, 32)
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.clicked.connect(lambda: self.done(2))
        
        yes_btn = QPushButton("Yes")
        yes_btn.setObjectName("installButton")
        yes_btn.setFixedSize(80, 32)
        yes_btn.setCursor(Qt.PointingHandCursor)
        yes_btn.clicked.connect(lambda: self.done(1))
        
        no_btn = QPushButton("No")
        no_btn.setObjectName("uninstallButton")
        no_btn.setFixedSize(80, 32)
        no_btn.setCursor(Qt.PointingHandCursor)
        no_btn.clicked.connect(lambda: self.done(0))
        
        btn_layout.addStretch()
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(yes_btn)
        btn_layout.addWidget(no_btn)
        
        layout.addLayout(btn_layout)
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor(40, 42, 62, 230))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(self.rect(), 15, 15)



def resource_path(relative_path):
    if getattr(sys, 'frozen', False):
        # 1. Check PyInstaller temp extraction dir (_MEIPASS)
        base_path = sys._MEIPASS
        temp_path = os.path.join(base_path, relative_path)
        if os.path.exists(temp_path):
            return temp_path
        # 2. Check the directory where the executable is located
        return os.path.join(os.path.dirname(sys.executable), relative_path)
    
    # Not frozen: use script directory
    base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

class AsyncWriterSignals(QObject):
    finished = pyqtSignal(str) # Emits filepath
    error = pyqtSignal(str, str) # Emits filepath, error_message

class AsyncWriterWorker(QRunnable):
    def __init__(self, filepath, content):
        super().__init__()
        self.filepath = filepath
        self.content = content
        self.signals = AsyncWriterSignals()

    def run(self):
        try:
            safe_file_write(self.filepath, self.content)
            self.signals.finished.emit(self.filepath)
        except Exception as e:
            self.signals.error.emit(self.filepath, str(e))

class AsyncFileIo:
    _pool = QThreadPool.globalInstance()
    
    @classmethod
    def write(cls, filepath, content, on_success=None, on_error=None):
        worker = AsyncWriterWorker(filepath, content)
        if on_success: worker.signals.finished.connect(on_success)
        if on_error: worker.signals.error.connect(on_error)
        cls._pool.start(worker)

def validate_nss_syntax(content):
    """Validates the basic structure of an NSS file to prevent corruption."""
    stack = []
    in_string = False
    string_char = ''
    for i, char in enumerate(content):
        # Ignore escaped quotes
        if in_string and char == string_char and (i == 0 or content[i-1] != '\\'):
            in_string = False
        elif not in_string and char in ('"', "'"):
            in_string = True; string_char = char
        elif not in_string:
            if char == '{': stack.append('{')
            elif char == '}':
                if not stack or stack[-1] != '{': return False
                stack.pop()
            elif char == '[': stack.append('[')
            elif char == ']':
                if not stack or stack[-1] != '[': return False
                stack.pop()
    return not in_string and len(stack) == 0

def safe_file_write(filepath, content):
    """Writes content to a file atomically and ensures it's flushed to disk."""
    if filepath.endswith('.nss') and not validate_nss_syntax(content):
        raise ValueError(f"Failed to write {filepath}: Invalid NSS syntax detected. Write aborted to prevent corruption.")

    temp_fd = None
    temp_path = None
    try:
        # 1. Write to a temporary file first
        temp_dir = os.path.dirname(os.path.abspath(filepath))
        os.makedirs(temp_dir, exist_ok=True)
        temp_fd, temp_path = tempfile.mkstemp(dir=temp_dir, text=True)
        
        with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno()) # Force write to physical disk
            
        # 2. Rename temp file to target (atomic on Windows if both in same drive)
        # We use os.replace to overwrite existing file
        os.replace(temp_path, filepath)
        
        # 3. Touch the file one more time to ensure the OS notices the change
        os.utime(filepath, None)
        
    except Exception as e:
        if temp_path and os.path.exists(temp_path):
            try: os.remove(temp_path)
            except: pass
        
        # Fallback to direct write if atomic fails
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
                f.flush()
                os.fsync(f.fileno())
        except:
            raise e

def terminate_plugin_processes(directory):
    """Terminates any processes running from the specified directory."""
    try:
        import psutil
        abs_dir = os.path.abspath(directory).lower()
        for proc in psutil.process_iter(['pid', 'name', 'exe']):
            try:
                exe_path = proc.info.get('exe')
                if exe_path and os.path.abspath(exe_path).lower().startswith(abs_dir):
                    proc.terminate()
                    try:
                        proc.wait(timeout=2)
                    except psutil.TimeoutExpired:
                        proc.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    except:
        pass

class WINDOWCOMPOSITIONATTRIBDATA(ctypes.Structure): _fields_ = [('Attribute', ctypes.c_int), ('Data', ctypes.c_void_p), ('SizeOfData', ctypes.c_size_t)]
class ACCENT_POLICY(ctypes.Structure): _fields_ = [('AccentState', ctypes.c_int), ('AccentFlags', ctypes.c_int), ('GradientColor', ctypes.c_int), ('AnimationId', ctypes.c_int)]

def set_window_effect(hwnd, effect='acrylic'):
    if not hwnd: return
    user32 = ctypes.windll.user32; dwmapi = ctypes.windll.dwmapi; margins = wintypes.RECT(-1, -1, -1, -1); dwmapi.DwmExtendFrameIntoClientArea(hwnd, ctypes.byref(margins))
    if effect == 'acrylic':
        accent = ACCENT_POLICY(); accent.AccentState = 4; accent.GradientColor = 0x011e2030; data = WINDOWCOMPOSITIONATTRIBDATA(); data.Attribute = 19; data.Data = ctypes.cast(ctypes.pointer(accent), ctypes.c_void_p); data.SizeOfData = ctypes.sizeof(accent); user32.SetWindowCompositionAttribute(hwnd, ctypes.byref(data))
    elif effect == 'mica': DWMWA_MICA_EFFECT = 1029; dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_MICA_EFFECT, ctypes.byref(ctypes.c_int(1)), 4)

def trigger_shell_reload(pos=None, close_only=False, open_only=False, scenario=None):
    try:
        import win32gui, win32con
        
        # 1. ALWAYS close any open context menus first to prevent stacking and stale state
        hwnd_menu = win32gui.FindWindow("#32768", None)
        while hwnd_menu:
            win32gui.SendMessage(hwnd_menu, win32con.WM_CLOSE, 0, 0)
            hwnd_menu = win32gui.FindWindow("#32768", None)

        if not open_only:
            # 2. Trigger reload
            # Attempt to find the PROJECT_ROOT consistently
            if getattr(sys, 'frozen', False):
                exe_dir = os.path.dirname(os.path.abspath(sys.executable))
            else:
                exe_dir = os.path.dirname(os.path.abspath(__file__))
                
            root = exe_dir
            for _ in range(4):
                if os.path.exists(os.path.join(root, 'shell.nss')): break
                p = os.path.dirname(root)
                if p == root: break
                root = p
            
            # Fallback for Launcher folder
            if not os.path.exists(os.path.join(root, 'shell.nss')) and os.path.basename(exe_dir).lower() == 'launcher':
                root = os.path.abspath(os.path.join(exe_dir, '..'))

            # Touch critical config files to force shell re-parsing
            for f in ['shell.nss', 'imports/modify.nss', 'imports/theme.nss']:
                fp = os.path.normpath(os.path.join(root, f))
                if os.path.exists(fp):
                    try:
                        # Ensure any cached writes are flushed before touching
                        with open(fp, 'a'): os.utime(fp, None)
                    except: pass

            exe = os.path.join(root, 'shell.exe')
            if os.path.exists(exe):
                # Small sleep to ensure OS file system handles the utime properly
                time.sleep(0.05)
                subprocess.Popen([exe, '-reload'], creationflags=0x08000000)
                # Give shell a moment to start parsing
                time.sleep(0.1)
            
            if close_only: return

        # 3. Open preview at specific position if provided
        def find_targets():
            t = []
            def callback(hwnd, extra):
                if win32gui.GetClassName(hwnd) == 'WorkerW':
                    child = win32gui.FindWindowEx(hwnd, 0, 'SHELLDLL_DefView', None)
                    if child: extra.append(child)
                return True
            win32gui.EnumWindows(callback, t)
            p = win32gui.FindWindow('Progman', None)
            if p:
                s = win32gui.FindWindowEx(p, 0, 'SHELLDLL_DefView', None)
                if s: t.append(s)
            return list(set(t))
        
        if pos:
            x, y = pos
            lparam = y << 16 | x
            targets = find_targets()
            
            import win32api
            import time

            # Scenario handling
            target_hwnd = None
            if scenario == 'taskbar':
                target_hwnd = win32gui.FindWindow('Shell_TrayWnd', None)
                lparam = 10 | (10 << 16) # Click at top-left of taskbar (relative to window)
            else:
                if targets: target_hwnd = targets[-1]

            if not target_hwnd: return

            def perform_click(hwnd, lp, ctrl=False, shift=False):
                if ctrl: win32api.keybd_event(win32con.VK_CONTROL, 0, 0, 0)
                if shift: win32api.keybd_event(win32con.VK_SHIFT, 0, 0, 0)
                try:
                    win32gui.SendMessageTimeout(hwnd, win32con.WM_ACTIVATE, win32con.WA_ACTIVE, 0, win32con.SMTO_ABORTIFHUNG, 200)
                    win32gui.SendMessageTimeout(hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lp, win32con.SMTO_ABORTIFHUNG, 200)
                    win32gui.SendMessageTimeout(hwnd, win32con.WM_LBUTTONUP, 0, lp, win32con.SMTO_ABORTIFHUNG, 200)
                    win32api.Sleep(50)
                    win32gui.SendMessageTimeout(hwnd, win32con.WM_RBUTTONDOWN, win32con.MK_RBUTTON, lp, win32con.SMTO_ABORTIFHUNG, 200)
                    win32gui.SendMessageTimeout(hwnd, win32con.WM_RBUTTONUP, 0, lp, win32con.SMTO_ABORTIFHUNG, 200)
                finally:
                    if ctrl: win32api.keybd_event(win32con.VK_CONTROL, 0, win32con.KEYEVENTF_KEYUP, 0)
                    if shift: win32api.keybd_event(win32con.VK_SHIFT, 0, win32con.KEYEVENTF_KEYUP, 0)

            # Execution logic
            if scenario == 'reload':
                # Force reload with CTRL, then close and show normal
                perform_click(target_hwnd, lparam, ctrl=True)
                time.sleep(0.5) # Wait for shell to re-parse
                # Close the reload menu
                hm = win32gui.FindWindow("#32768", None)
                if hm: win32gui.SendMessage(hm, win32con.WM_CLOSE, 0, 0)
                time.sleep(0.2) # Wait for menu to fully dispose
                # Show normal preview
                perform_click(target_hwnd, lparam, ctrl=False)
            elif scenario == 'shift':
                perform_click(target_hwnd, lparam, shift=True)
            elif scenario == 'ctrl':
                perform_click(target_hwnd, lparam, ctrl=True)
            else:
                perform_click(target_hwnd, lparam)
        else:
            # Fallback to standard refresh
            tray = win32gui.FindWindow('Shell_TrayWnd', None)
            if tray: win32gui.PostMessage(tray, win32con.WM_COMMAND, 28931, 0)
    except: pass
