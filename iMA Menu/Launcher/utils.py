import sys
import os
import struct
import zlib
import base64
import json
import tempfile
import shutil
import re
import time
import subprocess
import ctypes
from ctypes import wintypes
import win32api

try:
    ctypes.windll.kernel32.SetEnvironmentVariableW("_MEIPASS2", None)
    ctypes.windll.kernel32.SetEnvironmentVariableW("_MEIPASS", None)
except Exception:
    pass
for env_key in list(os.environ.keys()):
    if env_key.startswith('_MEI'):
        os.environ.pop(env_key, None)
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QDialogButtonBox, QUndoStack, QUndoCommand, QScrollArea, QWidget
from PyQt5.QtGui import QPainter, QColor, QFont, QIcon, QPixmap, QFontDatabase, QPainterPath, QPen, QFontMetrics
from PyQt5.QtCore import Qt, QRunnable, pyqtSignal, QObject, QThreadPool, QEvent

global_undo_stack = QUndoStack()

if getattr(sys, 'frozen', False):
    _base_path = os.path.dirname(os.path.abspath(sys.executable))
else:
    _base_path = os.path.dirname(os.path.abspath(__file__))

PROJECT_ROOT = _base_path
if os.path.basename(PROJECT_ROOT).lower() == 'launcher':
    PROJECT_ROOT = os.path.dirname(PROJECT_ROOT)

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    base_path = getattr(sys, '_MEIPASS', _base_path)
    temp_path = os.path.normpath(os.path.join(base_path, relative_path))
    if os.path.exists(temp_path):
        return temp_path
    return os.path.normpath(os.path.join(_base_path, relative_path))

def extract_ttf(dll_path, output_path):
    with open(dll_path, 'rb') as f:
        data = f.read()

    idx = 0
    while True:
        idx = data.find(b'\x00\x01\x00\x00', idx)
        if idx == -1: break
        
        if idx + 12 <= len(data):
            num_tables = struct.unpack('>H', data[idx+4:idx+6])[0]
            if 10 <= num_tables <= 40:
                max_offset = 0
                is_valid = True
                for i in range(num_tables):
                    table_entry = idx + 12 + (i * 16)
                    if table_entry + 16 > len(data):
                        is_valid = False
                        break
                    offset = struct.unpack('>I', data[table_entry+8:table_entry+12])[0]
                    length = struct.unpack('>I', data[table_entry+12:table_entry+16])[0]
                    max_offset = max(max_offset, offset + length)
                
                if is_valid and max_offset > 0 and max_offset < len(data):
                    font_data = data[idx:idx+max_offset]
                    if b'Nilesoft' in font_data:
                        with open(output_path, 'wb') as out:
                            out.write(font_data)
                        return True
        idx += 4
    return False

def generate_glyphs_data():
    base_dir = _base_path
    json_path = resource_path(os.path.join('fonts', 'glyphs.json'))
    if not os.path.exists(json_path):
        json_path = resource_path('glyphs.json')

    out_path = os.path.join(base_dir, 'glyphs_data.py')
    if not os.path.exists(json_path):
        return

    with open(json_path, 'rb') as f:
        raw_data = f.read()

    compressed = base64.b64encode(zlib.compress(raw_data, 9)).decode('ascii')
    content = f'''# Auto-generated bundled glyphs data module
import zlib
import base64
import json

_DATA = "{compressed}"

def get_glyphs_data():
    return json.loads(zlib.decompress(base64.b64decode(_DATA)).decode('utf-8'))
'''
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(content)

def get_glyphs_json_path():
    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(os.path.abspath(sys.executable))
    else:
        exe_dir = _base_path
    
    target_fonts_dir = os.path.join(exe_dir, 'fonts')
    try:
        os.makedirs(target_fonts_dir, exist_ok=True)
    except Exception:
        pass
    
    return os.path.join(target_fonts_dir, 'glyphs.json')

def ensure_fonts_unpacked():
    if not getattr(sys, 'frozen', False):
        return
    exe_dir = os.path.dirname(os.path.abspath(sys.executable))
    target_fonts_dir = os.path.join(exe_dir, 'fonts')
    os.makedirs(target_fonts_dir, exist_ok=True)
    
    target_json = os.path.join(target_fonts_dir, 'glyphs.json')
    if not os.path.exists(target_json) or os.path.getsize(target_json) == 0:
        data = None
        try:
            import glyphs_data
            data = glyphs_data.get_glyphs_data()
        except Exception:
            pass
        if not data:
            bundled_json = resource_path(os.path.join('fonts', 'glyphs.json'))
            if os.path.exists(bundled_json):
                try:
                    with open(bundled_json, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                except Exception:
                    pass
        if data:
            try:
                with open(target_json, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            except Exception:
                pass
    
    target_ttf = os.path.join(target_fonts_dir, 'nilesoft.ttf')
    if not os.path.exists(target_ttf):
        bundled_ttf = resource_path(os.path.join('fonts', 'nilesoft.ttf'))
        if os.path.exists(bundled_ttf):
            try:
                shutil.copy2(bundled_ttf, target_ttf)
            except Exception:
                pass

def get_glyphs_data():
    ensure_fonts_unpacked()
    target_json = get_glyphs_json_path()
    disk_data = {}
    if os.path.exists(target_json):
        try:
            with open(target_json, 'r', encoding='utf-8') as f:
                disk_data = json.load(f)
        except Exception:
            disk_data = {}
            
    bundled_data = {}
    try:
        import glyphs_data
        bundled_data = glyphs_data.get_glyphs_data()
    except Exception:
        bundled_json = resource_path(os.path.join('fonts', 'glyphs.json'))
        if os.path.exists(bundled_json):
            try:
                with open(bundled_json, 'r', encoding='utf-8') as f:
                    bundled_data = json.load(f)
            except Exception:
                pass

    if bundled_data and disk_data:
        merged = bundled_data.copy()
        merged.update(disk_data)
        return merged
    return disk_data or bundled_data or {}

NILESOFT_FONT_FAMILY = 'Nilesoft.Shell'
_font_initialized = False

def _init_nilesoft_font():
    global NILESOFT_FONT_FAMILY, _font_initialized
    if _font_initialized and NILESOFT_FONT_FAMILY in QFontDatabase().families(): return
    font_path = resource_path(os.path.join('fonts', 'nilesoft.ttf'))
    if not os.path.exists(font_path): font_path = resource_path('nilesoft.ttf')
    if os.path.exists(font_path):
        font_id = QFontDatabase.addApplicationFont(font_path)
        if font_id != -1:
            fams = QFontDatabase.applicationFontFamilies(font_id)
            if fams:
                NILESOFT_FONT_FAMILY = fams[0]
                _font_initialized = True
                return
    try:
        dll_path = os.path.join(os.path.dirname(resource_path('')), 'shell.dll')
        if os.path.exists(dll_path):
            if extract_ttf(dll_path, font_path):
                font_id = QFontDatabase.addApplicationFont(font_path)
                if font_id != -1:
                    fams = QFontDatabase.applicationFontFamilies(font_id); NILESOFT_FONT_FAMILY = fams[0]; _font_initialized = True
    except: pass

def get_font_icon(glyph, size=32, color='#ffffff', font_family=None):
    _init_nilesoft_font()
    family = font_family or NILESOFT_FONT_FAMILY
    pixmap = QPixmap(size, size); pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap); painter.setRenderHint(QPainter.Antialiasing)
    font = QFont(family, size // 2)
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
    font = QFont('Segoe MDL2 Assets', int(size * 0.75))
    font.setWeight(QFont.Bold)
    glyph = chr(glyph_code) if isinstance(glyph_code, int) else glyph_code
    fm = QFontMetrics(font); rect = fm.boundingRect(glyph)
    path = QPainterPath()
    path.addText((size - rect.width())/2 - rect.x(), (size - rect.height())/2 - rect.y(), font, glyph)
    painter.setPen(QPen(QColor(0, 0, 0, 255), 2.0, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    painter.drawPath(path)
    painter.fillPath(path, QColor(color)); painter.end()
    return QIcon(pixmap)

def generate_theme_preview(nss_path, output_png_path):
    theme_data = {}
    if os.path.exists(nss_path):
        with open(nss_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('theme') or line.startswith('{') or line.startswith('}'): continue
                if '=' in line:
                    key, value = line.split('=', 1)
                    theme_data[key.strip()] = value.strip().strip('"\'')
    
    def get_int(key, default_val):
        val = theme_data.get(key, str(default_val))
        try:
            return int(val)
        except ValueError:
            return default_val

    bg_color = QColor(theme_data.get("background.color", "#2b2b2b"))
    if bg_color.name() == "#000000" and theme_data.get("background.color") == "default":
        bg_color = QColor("#2b2b2b")
        
    bg_opacity = get_int("background.opacity", 100)
    border_color = QColor(theme_data.get("border.color", "#bf616a"))
    border_size = get_int("border.size", 1)
    text_color = QColor(theme_data.get("item.text.normal", "#ffffff"))
    if text_color.name() == "#000000" and theme_data.get("item.text.normal") == "default":
        text_color = QColor("#ffffff")
        
    border_radius = get_int("border.radius", 10)
    if border_radius < 10:
        border_radius = 16
        
    bg_image_path = theme_data.get("background.image", "")
    bg_color.setAlpha(int(bg_opacity * 2.55))
    
    w, h = 260, 310
    margin = 25
    img = QImage(w, h, QImage.Format_ARGB32)
    img.fill(Qt.transparent)
    
    painter = QPainter(img)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setRenderHint(QPainter.TextAntialiasing)
    painter.setRenderHint(QPainter.SmoothPixmapTransform)
    
    shadow_enabled = theme_data.get("shadow.enabled", "true") == "true"
    if shadow_enabled:
        shadow_color = QColor(theme_data.get("shadow.color", "#000000"))
        shadow_opacity = get_int("shadow.opacity", 20)
        shadow_color.setAlpha(int(shadow_opacity * 2.55))
        painter.setPen(Qt.NoPen)
        for i in range(1, 6):
            c = QColor(shadow_color)
            c.setAlpha(int(c.alpha() / i))
            painter.setBrush(c)
            painter.drawRoundedRect(QRectF(margin + i, margin + i, w - margin*2, h - margin*2), border_radius + 2, border_radius + 2)
        
    menu_rect = QRectF(margin, margin, w - margin*2, h - margin*2)
    path = QPainterPath()
    path.addRoundedRect(menu_rect, border_radius, border_radius)
    painter.setClipPath(path)
    
    if bg_image_path and os.path.exists(bg_image_path):
        bg_pixmap = QPixmap(bg_image_path)
        if not bg_pixmap.isNull():
            box_w = int(w - margin*2)
            box_h = int(h - margin*2)
            bg_pixmap = bg_pixmap.scaled(box_w, box_h, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            px_x = margin - (bg_pixmap.width() - box_w) / 2
            px_y = margin - (bg_pixmap.height() - box_h) / 2
            painter.drawPixmap(int(px_x), int(px_y), bg_pixmap)
            
            overlay_color = QColor(bg_color)
            overlay_color.setAlpha(int(min(255, bg_opacity * 2.55 + 50))) 
            painter.fillRect(menu_rect, overlay_color)
    else:
        painter.fillPath(path, bg_color)
        
    painter.setClipping(False)
    
    if border_size > 0:
        pen = QPen(border_color, border_size)
        painter.setPen(pen)
        painter.drawRoundedRect(menu_rect, border_radius, border_radius)
    
    items = [
        ("\uE81C", "Refresh", ""),
        ("\uE8A7", "Options", ">"),
        ("\uE713", "Manage", ">"),
        ("\uE7B3", "Valorant", ">"),
        ("\uE896", "Download", "")
    ]
    
    font_name = theme_data.get("font.name", "Segoe UI Variable Text")
    font_size_str = theme_data.get("font.size", "15")
    try: font_size = int(font_size_str)
    except ValueError: font_size = 15
        
    if font_name in ("auto", "default"): font_name = "Segoe UI Variable Text"
    font = QFont(font_name, max(9, font_size - 3))
    icon_font = QFont("Segoe Fluent Icons", max(10, font_size - 1))
    
    item_h = 36
    y = margin + 30
    
    for icon, text, arrow in items:
        painter.setFont(icon_font)
        painter.setPen(text_color)
        painter.drawText(margin + 18, y, 30, item_h, Qt.AlignLeft | Qt.AlignVCenter, icon)
        
        painter.setFont(font)
        painter.drawText(margin + 58, y, w - margin*2 - 80, item_h, Qt.AlignLeft | Qt.AlignVCenter, text)
        
        if arrow:
            painter.setFont(icon_font)
            painter.drawText(margin + 20, y, w - margin*2 - 40, item_h, Qt.AlignRight | Qt.AlignVCenter, "\uE76C")
            
        y += item_h + 8
            
    painter.end()
    img.save(output_png_path)

class NSSAutoFixer:
    @staticmethod
    def fix_line(line, column=0, message=""):
        fixed_line = line
        if column > 0 and column <= len(line):
            fixed_line = NSSAutoFixer._fix_at_column(line, column, message)
        
        if fixed_line == line:
            fixed_line = re.sub(r'=\s*[/\\@#$^&*]+\s*([\'"])', r'=\1', fixed_line)
            fixed_line = NSSAutoFixer._fix_unclosed_quotes(fixed_line)
            fixed_line = NSSAutoFixer._try_fix_quotes(fixed_line)
            fixed_line = NSSAutoFixer._fix_unbalanced_delimiters(fixed_line)
        return fixed_line

    @staticmethod
    def fix_content(content):
        content = re.sub(r"=''([^']+)''", r"='\1'", content)
        content = re.sub(r'=""([^"]+)""', r'="\1"', content)
        
        lines = content.splitlines(keepends=True)
        healed_lines = []
        for line in lines:
            fixed = NSSAutoFixer.fix_line(line)
            if re.search(r'(?i)\b(tip|image|icon)\s*=\s*(?![\[])[^\r\n,)]+,', fixed):
                fixed = re.sub(r'((?i)\b(?:tip|image|icon)\s*=\s*)([^\s\[][^)]*?,(?:(?!\s[a-z_.]+\s*=)[^)])*)', r'\1[\2', fixed)
                fixed = NSSAutoFixer._fix_unbalanced_delimiters(fixed)
            healed_lines.append(fixed)
            
        healed_content = "".join(healed_lines)
        
        for op, cl in [('(', ')'), ('[', ']'), ('{', '}')]:
            c_op = healed_content.count(op)
            c_cl = healed_content.count(cl)
            if c_op < c_cl and op == '[':
                healed_content = re.sub(r'((?:tip|image|icon)\s*=\s*)([^\s\[])', r'\1[\2', healed_content)
        return healed_content

    @staticmethod
    def _fix_at_column(line, col, msg):
        char_idx = col - 1
        if char_idx < 0 or char_idx >= len(line): return line
        char = line[char_idx]
        if char in '/\\@#$^&*':
            prev_part = line[:char_idx].rstrip()
            next_part = line[char_idx+1:].lstrip()
            if prev_part.endswith('=') or (next_part and next_part[0] in ("'", '"')):
                return line[:char_idx] + line[char_idx+1:]
        return line

    @staticmethod
    def _fix_unclosed_quotes(line):
        chars = list(line); in_quote = False; quote_char = None; i = 0
        while i < len(chars):
            c = chars[i]
            if c in ("'", '"'):
                if not in_quote: in_quote = True; quote_char = c
                elif c == quote_char: in_quote = False; quote_char = None
            elif in_quote and c == ' ':
                lookahead = "".join(chars[i+1:i+30])
                if re.match(r'^\s*[a-zA-Z0-9_.]+\s*=', lookahead):
                    chars.insert(i, quote_char); in_quote = False; quote_char = None; i += 1
            i += 1
        return "".join(chars)

    @staticmethod
    def _try_fix_quotes(line):
        stripped = line.rstrip('\r\n'); in_str = False; quote_char = None
        for i, ch in enumerate(stripped):
            if ch in ("'", '"'):
                if not in_str: in_str = True; quote_char = ch
                elif ch == quote_char: in_str = False
        if in_str:
            suffix = line[len(stripped):]
            if stripped.endswith(')'): return stripped[:-1] + quote_char + ')' + suffix
            elif stripped.endswith('}'): return stripped[:-1] + quote_char + '}' + suffix
            return stripped + quote_char + suffix
        return line

    @staticmethod
    def _fix_unbalanced_delimiters(line):
        stripped = line.strip()
        if re.search(r'(?i)\b(modify|item|menu)\s*\(', stripped) and not stripped.endswith(')'):
            return line
        if re.search(r'(?i)\b(where|this\.id|this\.find)\s*\(', stripped) and not stripped.endswith(')'):
            return line

        pairs = [('(', ')'), ('[', ']'), ('{', '}')]
        for op, cl in pairs:
            c_op = line.count(op); c_cl = line.count(cl)
            if c_op > c_cl:
                if op == '[':
                    if ',' in line and ']' not in line:
                        if ')' in line: line = line.replace(')', '])', 1)
                        else: line = line.rstrip() + ']'
            elif c_op < c_cl:
                cl_idx = line.find(cl); eq_idx = line.rfind('=', 0, cl_idx)
                if eq_idx != -1:
                    ins_pos = eq_idx + 1
                    while ins_pos < len(line) and line[ins_pos].isspace(): ins_pos += 1
                    if ins_pos < len(line) and line[ins_pos] != op:
                        line = line[:ins_pos] + op + line[ins_pos:]
        return line

    @staticmethod
    def fix_error(filepath, line_num, column, message):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            if line_num < 1 or line_num > len(lines):
                return False, f"Line {line_num} out of range"

            idx = line_num - 1
            original_line = lines[idx]
            
            content = "".join(lines)
            healed_content = NSSAutoFixer.fix_content(content)
            
            if healed_content != content:
                safe_file_write(filepath, healed_content)
                return True, "Healed structural errors"
                
            fixed_line = NSSAutoFixer.fix_line(original_line, column, message)
            if fixed_line != original_line:
                lines[idx] = fixed_line
                safe_file_write(filepath, "".join(lines))
                return True, f"Fixed line {line_num}"
            
            return False, "Could not safely auto-fix"
        except Exception as e:
            return False, str(e)

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

class UnsavedChangesDialog(QDialog):
    def __init__(self, parent=None, text='You have unsaved changes. Do you want to save them?', changes=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setObjectName('customMessageBox')
        self._drag_pos = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        label = QLabel(text)
        label.setWordWrap(True)
        label.setStyleSheet('color: #ffffff; font-size: 14px; font-weight: bold; background: transparent;')
        layout.addWidget(label)

        if changes:
            if isinstance(changes, (list, tuple, set)):
                items = [str(c) for c in changes if str(c).strip()]
            elif isinstance(changes, dict):
                items = [f"{k}: {v}" for k, v in changes.items() if str(v).strip()]
            else:
                items = [line for line in str(changes).splitlines() if line.strip()]

            if items:
                scroll = QScrollArea()
                scroll.setWidgetResizable(True)
                scroll.setFixedHeight(130)
                scroll.setStyleSheet("""
                    QScrollArea {
                        background: rgba(0, 0, 0, 0.25);
                        border: 1px solid #2a2a30;
                        border-radius: 10px;
                    }
                    QScrollBar:vertical {
                        background: transparent;
                        width: 6px;
                        margin: 4px 2px 4px 0;
                    }
                    QScrollBar::handle:vertical {
                        background: rgba(255, 255, 255, 0.2);
                        border-radius: 3px;
                        min-height: 20px;
                    }
                    QScrollBar::handle:vertical:hover {
                        background: #dc143c;
                    }
                    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                        height: 0px;
                    }
                """)
                container = QWidget()
                container.setStyleSheet("background: transparent;")
                c_lay = QVBoxLayout(container)
                c_lay.setContentsMargins(12, 10, 12, 10)
                c_lay.setSpacing(6)
                for item in items:
                    c_lbl = QLabel(f"•  {item}")
                    c_lbl.setWordWrap(True)
                    c_lbl.setStyleSheet("color: #e0e0e0; font-size: 12px; background: transparent;")
                    c_lay.addWidget(c_lbl)
                c_lay.addStretch()
                scroll.setWidget(container)
                layout.addWidget(scroll)

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
        cancel_btn.setFixedSize(80, 36)
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.clicked.connect(lambda: self.done(2))
        
        yes_btn = QPushButton("Yes")
        yes_btn.setObjectName("customYesBtn")
        yes_btn.setStyleSheet("QPushButton { background-color: #4AE290; color: #121212; border-radius: 12px; font-weight: bold; border: 2px solid #2a2a30; } QPushButton:hover { background-color: #60F2A5; border: 2px solid #60F2A5; }")
        yes_btn.setFixedSize(80, 36)
        yes_btn.setCursor(Qt.PointingHandCursor)
        yes_btn.clicked.connect(lambda: self.done(1))
        
        no_btn = QPushButton("No")
        no_btn.setObjectName("customNoBtn")
        no_btn.setStyleSheet("QPushButton { background-color: #FF4C4C; color: #121212; border-radius: 12px; font-weight: bold; border: 2px solid #2a2a30; } QPushButton:hover { background-color: #FF6B6B; border: 2px solid #FF6B6B; }")
        no_btn.setFixedSize(80, 36)
        no_btn.setCursor(Qt.PointingHandCursor)
        no_btn.clicked.connect(lambda: self.done(0))
        
        btn_layout.addStretch()
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(yes_btn)
        btn_layout.addWidget(no_btn)
        
        layout.addLayout(btn_layout)
        self.setFixedWidth(460)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self._drag_pos is not None:
            self.move(event.globalPos() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor(24, 24, 26, 250))
        painter.setPen(QPen(QColor("#2a2a30"), 2))
        painter.drawRoundedRect(self.rect().adjusted(1, 1, -2, -2), 15, 15)

class AsyncWriterSignals(QObject):
    finished = pyqtSignal(str)
    error = pyqtSignal(str, str)

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
        finally:
            AsyncFileIo._pending_count = max(0, AsyncFileIo._pending_count - 1)

class AsyncFileIo:
    _pool = QThreadPool.globalInstance()
    _pending_count = 0
    
    @classmethod
    def has_pending_writes(cls):
        return cls._pending_count > 0

    @classmethod
    def write(cls, filepath, content, on_success=None, on_error=None):
        cls._pending_count += 1
        worker = AsyncWriterWorker(filepath, content)
        if on_success: worker.signals.finished.connect(on_success)
        if on_error: worker.signals.error.connect(on_error)
        cls._pool.start(worker)

def validate_nss_syntax(content):
    stack = []
    in_string = False
    string_char = ''
    for i, char in enumerate(content):
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
    if filepath.endswith('.nss') and not validate_nss_syntax(content):
        try:
            healed_content = NSSAutoFixer.fix_content(content)
            if validate_nss_syntax(healed_content):
                content = healed_content
            else:
                raise ValueError(f"Failed to write {filepath}: Invalid NSS syntax detected. Write aborted to prevent corruption.")
        except Exception as e:
            if isinstance(e, ValueError): raise e
            raise ValueError(f"Failed to write {filepath}: Invalid NSS syntax detected. Write aborted to prevent corruption.")

    temp_fd = None
    temp_path = None
    try:
        temp_dir = os.path.dirname(os.path.abspath(filepath))
        os.makedirs(temp_dir, exist_ok=True)
        temp_fd, temp_path = tempfile.mkstemp(dir=temp_dir, text=True)
        
        with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
            
        os.replace(temp_path, filepath)
        os.utime(filepath, None)
        
    except Exception as e:
        if temp_path and os.path.exists(temp_path):
            try: os.remove(temp_path)
            except: pass
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
                f.flush()
                os.fsync(f.fileno())
        except:
            raise e

def terminate_plugin_processes(directory):
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

def send_ipc_command(cmd_string):
    import win32gui, win32con
    import ctypes
    from ctypes import wintypes
    
    try:
        if cmd_string == 'CMD_RELOAD':
            msg_id = win32gui.RegisterWindowMessage("iMA_IPC_Command")
            hwnd = win32gui.FindWindow("Shell_TrayWnd", None)
            if hwnd:
                win32gui.SendMessageTimeout(hwnd, msg_id, 1, 0, win32con.SMTO_ABORTIFHUNG, 1000)
            return True

        hwnd = win32gui.FindWindowEx(win32con.HWND_MESSAGE, 0, "iMA_IPC_Class", "iMA_IPC_Window")
        if not hwnd:
            return False
            
        class COPYDATASTRUCT(ctypes.Structure):
            _fields_ = [
                ('dwData', wintypes.ULONG),
                ('cbData', wintypes.DWORD),
                ('lpData', ctypes.c_void_p)
            ]
            
        cmd_bytes = cmd_string.encode('utf-16-le')
        cds = COPYDATASTRUCT()
        cds.dwData = 1
        cds.cbData = len(cmd_bytes)
        buffer = ctypes.create_string_buffer(cmd_bytes)
        cds.lpData = ctypes.cast(buffer, ctypes.c_void_p)
        
        win32gui.SendMessageTimeout(hwnd, win32con.WM_COPYDATA, 0, ctypes.addressof(cds), win32con.SMTO_ABORTIFHUNG, 1000)
        return True
    except Exception as e:
        print(f"IPC Error: {e}")
        return False

def trigger_shell_reload(pos=None, close_only=False, open_only=False, scenario=None):
    wait_start = time.time()
    while AsyncFileIo.has_pending_writes() and time.time() - wait_start < 1.0:
        time.sleep(0.05)
        
    try:
        import win32gui, win32con
        
        hwnd_menu = win32gui.FindWindow("#32768", None)
        while hwnd_menu:
            win32gui.SendMessage(hwnd_menu, win32con.WM_CLOSE, 0, 0)
            hwnd_menu = win32gui.FindWindow("#32768", None)

        if not open_only:
            if send_ipc_command('CMD_RELOAD'):
                if close_only: return
            else:
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
                
                if not os.path.exists(os.path.join(root, 'shell.nss')) and os.path.basename(exe_dir).lower() == 'launcher':
                    root = os.path.abspath(os.path.join(exe_dir, '..'))

                for f in ['shell.nss', 'imports/modify.nss', 'imports/theme.nss']:
                    fp = os.path.normpath(os.path.join(root, f))
                    if os.path.exists(fp):
                        try:
                            with open(fp, 'a'): os.utime(fp, None)
                        except: pass

                exe = os.path.join(root, 'shell.exe')
                if os.path.exists(exe):
                    time.sleep(0.05)
                    clean_environment = os.environ.copy()
                    for key in list(clean_environment.keys()):
                        if key.startswith('_MEI'):
                            clean_environment.pop(key, None)
                    subprocess.Popen([exe, '-reload'], env=clean_environment, creationflags=0x08000000)
                    time.sleep(0.1)
                
                if close_only: return

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
            
            target_hwnd = None
            if scenario == 'taskbar':
                target_hwnd = win32gui.FindWindow('Shell_TrayWnd', None)
                lparam = 10 | (10 << 16)
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

            if scenario == 'reload':
                perform_click(target_hwnd, lparam, ctrl=True)
                time.sleep(0.5)
                hm = win32gui.FindWindow("#32768", None)
                if hm: win32gui.SendMessage(hm, win32con.WM_CLOSE, 0, 0)
                time.sleep(0.2)
                perform_click(target_hwnd, lparam, ctrl=False)
            elif scenario == 'shift':
                perform_click(target_hwnd, lparam, shift=True)
            elif scenario == 'ctrl':
                perform_click(target_hwnd, lparam, ctrl=True)
            else:
                perform_click(target_hwnd, lparam)
        else:
            tray = win32gui.FindWindow('Shell_TrayWnd', None)
            if tray: win32gui.PostMessage(tray, win32con.WM_COMMAND, 28931, 0)
    except: pass

def get_shell_dll_version():
    try:
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
        
        if not os.path.exists(os.path.join(root, 'shell.nss')) and os.path.basename(exe_dir).lower() == 'launcher':
            root = os.path.abspath(os.path.join(exe_dir, '..'))

        dll_path = os.path.join(root, 'shell.dll')
        if not os.path.exists(dll_path):
            parent_dll = os.path.abspath(os.path.join(exe_dir, '..', 'shell.dll'))
            if os.path.exists(parent_dll):
                dll_path = parent_dll
            else:
                return (0, 0, 0, 0)

        info = win32api.GetFileVersionInfo(dll_path, "\\")
        ms = info['FileVersionMS']
        ls = info.get('FileVersionLS', 0)
        return (win32api.HIWORD(ms), win32api.LOWORD(ms), win32api.HIWORD(ls), win32api.LOWORD(ls))
    except Exception:
        return (0, 0, 0, 0)

def restart_explorer():
    try:
        subprocess.run(['taskkill', '/f', '/im', 'explorer.exe'],
                       creationflags=0x08000000, capture_output=True, timeout=5)
        time.sleep(1)
        subprocess.Popen(['explorer.exe'], creationflags=0x08000000)
    except Exception:
        try:
            os.startfile('explorer.exe')
        except Exception:
            pass

def get_default_image_dir():
    cache_path = resource_path(os.path.join('cache', 'last_image_dir.json'))
    if os.path.exists(cache_path):
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                saved_dir = data.get('last_dir', '')
                if saved_dir and os.path.exists(saved_dir):
                    return saved_dir
        except (json.JSONDecodeError, IOError):
            pass

    pictures_dir = os.path.join(os.path.expanduser('~'), 'Pictures')
    if os.path.exists(pictures_dir):
        return pictures_dir
    desktop_dir = os.path.join(os.path.expanduser('~'), 'Desktop')
    if os.path.exists(desktop_dir):
        return desktop_dir
    return os.path.expanduser('~')

def save_last_image_dir(directory_path):
    if not directory_path or not os.path.exists(directory_path):
        return
    cache_path = resource_path(os.path.join('cache', 'last_image_dir.json'))
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    try:
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump({'last_dir': directory_path}, f)
    except IOError:
        pass

class ModernDialog(QDialog):
    def __init__(self, parent=None, title="Message", text=""):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMinimumWidth(400)
        l = QVBoxLayout(self)
        self.f = QFrame()
        self.f.setObjectName("modalFrame")
        self.f.setStyleSheet("#modalFrame { background-color: #121212; border: 1px solid #2a2a30; border-radius: 20px; }")
        l.addWidget(self.f)
        self.cl = QVBoxLayout(self.f)
        self.cl.setContentsMargins(30, 30, 30, 30)
        self.cl.setSpacing(15)
        self.tl = QLabel(title)
        self.tl.setStyleSheet("color: white; font-size: 20px; font-weight: bold; border: none;")
        self.cl.addWidget(self.tl)
        self.ml = QLabel(text)
        self.ml.setStyleSheet("color: #b0b0b0; font-size: 14px; border: none;")
        self.ml.setWordWrap(True)
        self.cl.addWidget(self.ml)
        self.bl = QHBoxLayout()
        self.bl.setSpacing(10)
        self.cl.addLayout(self.bl)
        self.add_button("Close", "secondaryButton", self.accept)

    def add_button(self, text, style_obj, callback):
        if self.bl.count() == 1 and isinstance(self.bl.itemAt(0).widget(), QPushButton) and self.bl.itemAt(0).widget().text() == "Close":
            w = self.bl.itemAt(0).widget()
            self.bl.removeWidget(w)
            w.hide()
            w.setParent(None)
            w.deleteLater()
        b = QPushButton(text)
        b.setFixedHeight(40)
        b.setCursor(Qt.PointingHandCursor)
        b.setObjectName(style_obj)
        b.clicked.connect(callback)
        self.bl.addWidget(b)
        return b

    def mousePressEvent(self, e):
        if not self.f.geometry().contains(e.pos()):
            self.reject()

def launch_shell_core_update(parent=None):
    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(os.path.abspath(sys.executable))
    else:
        exe_dir = os.path.dirname(os.path.abspath(__file__))

    parent_dir = os.path.abspath(os.path.join(exe_dir, '..'))
    target_shell_dll = os.path.join(parent_dir, 'shell.dll')
    target_shell_exe = os.path.join(parent_dir, 'shell.exe')

    bundled_shell = resource_path('shell.dll')
    if not os.path.exists(bundled_shell):
        bundled_shell = os.path.join(exe_dir, 'shell.dll')
    if not os.path.exists(bundled_shell):
        bundled_shell = os.path.join(exe_dir, 'src', 'bin', 'shell.dll')

    if not os.path.exists(bundled_shell):
        return False

    temp_new_shell = os.path.join(tempfile.gettempdir(), 'shell_new.dll')
    try:
        shutil.copy2(bundled_shell, temp_new_shell)
    except Exception:
        pass

    updater_src = resource_path('ima_updater.exe')
    temp_updater = os.path.join(tempfile.gettempdir(), 'ima_updater.exe')
    if os.path.exists(updater_src):
        try: shutil.copy2(updater_src, temp_updater)
        except Exception: pass
    elif os.path.exists(os.path.join(exe_dir, 'ima_updater.exe')):
        try: shutil.copy2(os.path.join(exe_dir, 'ima_updater.exe'), temp_updater)
        except Exception: pass

    updater_args = f'--shell-only --new-shell "{temp_new_shell}" --target-shell "{target_shell_dll}" --shell-exe "{target_shell_exe}" --dir "{exe_dir}"'

    try:
        ret = ctypes.windll.shell32.ShellExecuteW(
            None,
            'runas',
            temp_updater,
            updater_args,
            exe_dir,
            0
        )
        return ret > 32
    except Exception:
        return False
