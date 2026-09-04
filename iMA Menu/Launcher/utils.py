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

try:
    ctypes.windll.kernel32.SetEnvironmentVariableW("_MEIPASS2", None)
    ctypes.windll.kernel32.SetEnvironmentVariableW("_MEIPASS", None)
except Exception:
    pass
for env_key in list(os.environ.keys()):
    if env_key.startswith('_MEI'):
        os.environ.pop(env_key, None)
import functools
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
                             QDialogButtonBox, QUndoStack, QUndoCommand, QScrollArea, 
                             QWidget, QFrame, QLayout, QComboBox, QListView, QStyledItemDelegate, QStyle, QLineEdit)
from PyQt5.QtGui import QPainter, QColor, QFont, QIcon, QPixmap, QFontDatabase, QPainterPath, QPen, QFontMetrics, QImage, QLinearGradient
from PyQt5.QtCore import (Qt, QRunnable, pyqtSignal, QObject, QThreadPool, QEvent, 
                          QSize, QRect, QRectF, QPoint, QPointF, QPropertyAnimation, QEasingCurve, pyqtProperty, QTimer, QVariantAnimation)
try: from PyQt5 import QtSvg
except ImportError: QtSvg = None

global_undo_stack = QUndoStack()

@functools.lru_cache(maxsize=512)
def normalize_path(path: str) -> str:
    """Fast, cached path normalization."""
    if not path:
        return ""
    return os.path.normpath(path).lower().replace('\\', '/')

if getattr(sys, 'frozen', False):
    _base_path = os.path.dirname(os.path.abspath(sys.executable))
else:
    _base_path = os.path.dirname(os.path.abspath(__file__))

PROJECT_ROOT = _base_path
if os.path.basename(PROJECT_ROOT).lower() == 'launcher':
    PROJECT_ROOT = os.path.dirname(PROJECT_ROOT)

@functools.lru_cache(maxsize=512)
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

_cached_glyphs_dict = None

def generate_glyphs_data():
    """Stub kept for build backward-compatibility; glyphs are read directly from fonts/glyphs.json."""
    base_dir = _base_path
    out_path = os.path.join(base_dir, 'glyphs_data.py')
    content = '''# Auto-generated lightweight glyphs data forwarder
import os
import json

def get_glyphs_data():
    try:
        from utils import get_glyphs_data as _get_data
        return _get_data()
    except Exception:
        return {}
'''
    try:
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(content)
    except Exception:
        pass

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
        bundled_json = resource_path(os.path.join('fonts', 'glyphs.json'))
        if not os.path.exists(bundled_json):
            bundled_json = resource_path('glyphs.json')
        if os.path.exists(bundled_json):
            try:
                shutil.copy2(bundled_json, target_json)
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
    global _cached_glyphs_dict
    if _cached_glyphs_dict is not None:
        return _cached_glyphs_dict

    ensure_fonts_unpacked()
    target_json = get_glyphs_json_path()
    data = {}
    if os.path.exists(target_json):
        try:
            with open(target_json, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception:
            data = {}
            
    if not data:
        bundled_json = resource_path(os.path.join('fonts', 'glyphs.json'))
        if not os.path.exists(bundled_json):
            bundled_json = resource_path('glyphs.json')
        if os.path.exists(bundled_json):
            try:
                with open(bundled_json, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except Exception:
                data = {}

    _cached_glyphs_dict = data or {}
    return _cached_glyphs_dict

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

_font_icon_cache = {}
_mdl2_icon_cache = {}

def get_font_icon(glyph, size=32, color='#ffffff', font_family=None):
    _init_nilesoft_font()
    family = font_family or NILESOFT_FONT_FAMILY
    cache_key = (glyph, size, color, family)
    if cache_key in _font_icon_cache:
        return _font_icon_cache[cache_key]
    pixmap = QPixmap(size, size); pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap); painter.setRenderHint(QPainter.Antialiasing)
    font = QFont(family, size // 2)
    fm = QFontMetrics(font); rect = fm.boundingRect(glyph)
    path = QPainterPath()
    path.addText((size - rect.width())/2 - rect.x(), (size - rect.height())/2 - rect.y(), font, glyph)
    painter.setPen(QPen(QColor(0, 0, 0, 180), 2.5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    painter.drawPath(path)
    painter.fillPath(path, QColor(color)); painter.end()
    icon = QIcon(pixmap)
    if len(_font_icon_cache) < 256:
        _font_icon_cache[cache_key] = icon
    return icon

def get_mdl2_icon(glyph_code, size=32, color='#ffffff'):
    cache_key = (glyph_code, size, color)
    if cache_key in _mdl2_icon_cache:
        return _mdl2_icon_cache[cache_key]
    scale = 2
    px_size = size * scale
    pixmap = QPixmap(px_size, px_size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setRenderHint(QPainter.TextAntialiasing)
    painter.setRenderHint(QPainter.SmoothPixmapTransform)
    font = QFont('Segoe MDL2 Assets', int(px_size * 0.55))
    font.setWeight(QFont.DemiBold)
    painter.setFont(font)
    painter.setPen(QColor(color))
    glyph = chr(glyph_code) if isinstance(glyph_code, int) else glyph_code
    painter.drawText(QRect(0, 0, px_size, px_size), Qt.AlignCenter, glyph)
    painter.end()
    pixmap.setDevicePixelRatio(scale)
    icon = QIcon(pixmap)
    if len(_mdl2_icon_cache) < 256:
        _mdl2_icon_cache[cache_key] = icon
    return icon

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
        content = re.sub(r'(\b(?:menu|pos|title|find|image|icon)\s*=\s*)\(\s*(["\'][^"\']*["\'])\s*\)', r'\1\2)', content)
        
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


class PillPushButton(QPushButton):
    """
    High-quality vector-antialiased pill-shaped QPushButton.
    Eliminates low-quality / pixelated borders by rendering with QPainterPath, Antialiasing,
    and 1.5px crisp vector outlines.
    """
    def __init__(self, text, style_type="primary", height=32, icon_code=None, parent=None, **kwargs):
        super().__init__(text, parent)
        self.style_type = style_type
        self.icon_code = icon_code
        self._custom_bg = kwargs.get('bg_color')
        self._custom_border = kwargs.get('border_color')
        self._custom_fg = kwargs.get('text_color')
        if height:
            self.setFixedHeight(height)
        self.setCursor(Qt.PointingHandCursor)
        self.setFont(QFont("Segoe UI Variable Display", 9, QFont.Bold))
        self.setAttribute(Qt.WA_Hover, True)
        self.setStyleSheet("background: transparent; border: none; outline: none;")

    def sizeHint(self):
        fm = self.fontMetrics()
        w = fm.horizontalAdvance(self.text().strip()) + 32
        if self.icon_code:
            w += 22
        return QSize(max(w, 80), self.height() if self.height() > 0 else 32)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)

        rect = QRectF(self.rect()).adjusted(1.0, 1.0, -1.0, -1.0)
        path = QPainterPath()
        r = rect.height() / 2.0
        path.addRoundedRect(rect, r, r)

        is_hov = self.underMouse()
        is_down = self.isDown()

        if self.style_type == "primary":
            bg = QColor("#ea999c") if is_hov else QColor("#e78284")
            border = QColor("#ffccd0") if is_hov else QColor("#f4a5a8")
            fg = QColor("#232634")
        elif self.style_type in ("secondary", "cancel"):
            bg = QColor(255, 255, 255, 22) if is_hov else QColor(255, 255, 255, 10)
            border = QColor(255, 255, 255, 55) if is_hov else QColor(255, 255, 255, 28)
            fg = QColor("#ffffff") if is_hov else QColor("#c6d0f5")
        elif self.style_type == "reset":
            bg = QColor(140, 170, 238, 26) if is_hov else QColor(255, 255, 255, 8)
            border = QColor(140, 170, 238, 90) if is_hov else QColor(255, 255, 255, 28)
            fg = QColor("#ffffff") if is_hov else QColor("#8caaee")
        elif self.style_type in ("backup", "success"):
            bg = QColor("#60F2A5") if is_hov else QColor("#4AE290")
            border = QColor("#85ffc0") if is_hov else QColor("#38c777")
            fg = QColor("#121212")
        elif self.style_type in ("restore", "info"):
            bg = QColor("#5D9CEB") if is_hov else QColor("#4A90E2")
            border = QColor("#87baff") if is_hov else QColor("#3574c4")
            fg = QColor("#121212")
        elif self.style_type == "yes":
            bg = QColor("#81c8be") if is_hov else QColor("#a6d189")
            border = QColor("#a6e3d9") if is_hov else QColor("#92bd75")
            fg = QColor("#121212")
        elif self.style_type in ("no", "danger"):
            bg = QColor("#ea999c") if is_hov else QColor("#e78284")
            border = QColor("#ffccd0") if is_hov else QColor("#d06e70")
            fg = QColor("#121212")
        else:
            bg = QColor(self._custom_bg or "#e78284")
            border = QColor(self._custom_border or "#ea999c")
            fg = QColor(self._custom_fg or "#ffffff")
            if is_hov:
                bg = bg.lighter(115)
                border = border.lighter(120)

        if is_down:
            bg = bg.darker(110)

        p.fillPath(path, bg)
        p.setPen(QPen(border, 1.5))
        p.drawPath(path)

        p.setFont(self.font())
        p.setPen(fg)

        txt = self.text()
        if self.icon_code:
            icon_pix = get_mdl2_icon(self.icon_code, 14, fg.name()).pixmap(14, 14)
            fm = self.fontMetrics()
            txt_w = fm.horizontalAdvance(txt.strip())
            total_w = 14 + 6 + txt_w
            start_x = (self.width() - total_w) / 2.0
            p.drawPixmap(int(start_x), int((self.height() - 14) / 2.0), icon_pix)
            p.drawText(int(start_x + 20), int((self.height() + fm.ascent() - fm.descent()) / 2.0), txt.strip())
        else:
            p.drawText(self.rect(), Qt.AlignCenter, txt)


class PillLineEdit(QLineEdit):
    """
    High-quality vector-antialiased pill-shaped QLineEdit.
    Replaces rasterized QSS borders with QPainterPath, Antialiasing,
    and 1.5px crisp vector outlines.
    """
    def __init__(self, placeholder="", parent=None, height=36):
        super().__init__(parent)
        if placeholder:
            self.setPlaceholderText(placeholder)
        if height:
            self.setFixedHeight(height)
        self.setAttribute(Qt.WA_Hover, True)
        self.setFont(QFont("Segoe UI Variable Text", 9))
        self.setStyleSheet("""
            QLineEdit {
                background: transparent;
                border: none;
                padding-left: 14px;
                padding-right: 14px;
                color: #ffffff;
                selection-background-color: #e78284;
            }
        """)

    def enterEvent(self, event):
        super().enterEvent(event)
        self.update()

    def leaveEvent(self, event):
        super().leaveEvent(event)
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        rect = QRectF(self.rect()).adjusted(1.0, 1.0, -1.0, -1.0)
        r = rect.height() / 2.0
        path = QPainterPath()
        path.addRoundedRect(rect, r, r)

        is_focus = self.hasFocus()
        is_hover = self.underMouse()

        if is_focus:
            p.fillPath(path, QColor(255, 255, 255, 20))
            p.setPen(QPen(QColor("#e78284"), 1.5))
        elif is_hover:
            p.fillPath(path, QColor(255, 255, 255, 16))
            p.setPen(QPen(QColor(255, 255, 255, 75), 1.5))
        else:
            p.fillPath(path, QColor(255, 255, 255, 10))
            p.setPen(QPen(QColor(255, 255, 255, 30), 1.2))
        p.drawPath(path)
        p.end()

        super().paintEvent(event)


class UnsavedChangesDialog(QDialog):
    def __init__(self, parent=None, text='You have unsaved changes. Do you want to save them?', changes=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setObjectName('customMessageBox')
        self._drag_pos = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.card = QFrame(self)
        self.card.setObjectName('customMessageBoxCard')
        self.card.setStyleSheet('''
            #customMessageBoxCard {
                background-color: #121212;
                border: 1px solid #282828;
                border-radius: 14px;
            }
        ''')
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(15)

        title_layout = QHBoxLayout()
        title_layout.setSpacing(10)
        icon_lbl = QLabel(self)
        icon_lbl.setText('\uE7BA')
        icon_lbl.setFont(QFont('Segoe MDL2 Assets', 18))
        icon_lbl.setStyleSheet('color: #e78284;')
        title_layout.addWidget(icon_lbl)

        title_lbl = QLabel('Unsaved Changes', self)
        title_lbl.setStyleSheet('color: #ffffff; font-weight: bold; font-size: 15px;')
        title_layout.addWidget(title_lbl)
        title_layout.addStretch()
        card_layout.addLayout(title_layout)

        msg_lbl = QLabel(text, self)
        msg_lbl.setStyleSheet('color: #c6d0f5; font-size: 13px; margin-left: 2px;')
        msg_lbl.setWordWrap(True)
        card_layout.addWidget(msg_lbl)

        if changes:
            items = []
            if isinstance(changes, list):
                items = changes
            elif isinstance(changes, dict):
                items = [f"{k}: '{v}'" for k, v in changes.items()]
            
            if items:
                scroll = QScrollArea()
                scroll.setWidgetResizable(True)
                scroll.setMaximumHeight(140)
                scroll.setStyleSheet("""
                    QScrollArea { background-color: rgba(255, 255, 255, 0.03); border-radius: 8px; border: 1px solid rgba(255, 255, 255, 0.05); }
                    QScrollBar:vertical { width: 4px; background: transparent; }
                    QScrollBar::handle:vertical { background: rgba(255, 255, 255, 0.15); border-radius: 2px; }
                """)
                container = QWidget()
                container.setStyleSheet("background: transparent;")
                c_lay = QVBoxLayout(container)
                c_lay.setContentsMargins(12, 10, 12, 10)
                c_lay.setSpacing(6)
                for item in items:
                    m = re.match(r'^(?:\[(?P<prefix>[^\]]+)\]\s*)?Icon:\s*\'(?P<before>.*?)\'\s*➔\s*\'(?P<after>.*?)\'$', item)
                    if m:
                        prefix = f"[{m.group('prefix')}] " if m.group('prefix') else ""
                        before_val = m.group('before')
                        after_val = m.group('after')
                        row = self._create_icon_change_row(prefix, before_val, after_val)
                        c_lay.addWidget(row)
                    else:
                        c_lbl = QLabel(f"•  {item}")
                        c_lbl.setWordWrap(True)
                        c_lbl.setStyleSheet("color: #b5bfe2; font-size: 12px; background: transparent;")
                        c_lay.addWidget(c_lbl)
                c_lay.addStretch()
                scroll.setWidget(container)
                card_layout.addWidget(scroll)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        
        cancel_btn = PillPushButton("Cancel", "secondary", height=34)
        cancel_btn.setFixedWidth(80)
        cancel_btn.clicked.connect(lambda: self.done(2))
        
        yes_btn = PillPushButton("Yes", "yes", height=34)
        yes_btn.setFixedWidth(80)
        yes_btn.clicked.connect(lambda: self.done(1))
        
        no_btn = PillPushButton("No", "no", height=34)
        no_btn.setFixedWidth(80)
        no_btn.clicked.connect(lambda: self.done(0))
        
        btn_layout.addStretch()
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(yes_btn)
        btn_layout.addWidget(no_btn)
        
        card_layout.addLayout(btn_layout)
        layout.addWidget(self.card)
        self.setFixedWidth(460)

    def _create_icon_change_row(self, prefix, before_val, after_val):
        row = QWidget()
        row.setStyleSheet("background: transparent;")
        r_lay = QHBoxLayout(row)
        r_lay.setContentsMargins(0, 2, 0, 2)
        r_lay.setSpacing(8)

        prefix_text = f"•  {prefix}Icon:" if prefix else "•  Icon:"
        lbl = QLabel(prefix_text)
        lbl.setStyleSheet("color: #b5bfe2; font-size: 12px; font-weight: bold; background: transparent;")
        r_lay.addWidget(lbl)

        def make_badge(val, is_after=False):
            badge = QFrame()
            badge.setFixedSize(28, 28)
            border_color = "rgba(231, 130, 132, 0.6)" if is_after else "#414559"
            bg_color = "rgba(231, 130, 132, 0.15)" if is_after else "rgba(255, 255, 255, 0.05)"
            badge.setStyleSheet(f"QFrame {{ background: {bg_color}; border: 1px solid {border_color}; border-radius: 6px; }}")
            b_lay = QVBoxLayout(badge)
            b_lay.setContentsMargins(0, 0, 0, 0)
            b_lay.setAlignment(Qt.AlignCenter)

            val_clean = str(val or '').strip('\'" ')
            if val_clean and val_clean != '(none)':
                pix = render_nss_asset_pixmap(val_clean, size=20)
                if pix and not pix.isNull():
                    img_lbl = QLabel()
                    img_lbl.setPixmap(pix)
                    img_lbl.setAlignment(Qt.AlignCenter)
                    img_lbl.setStyleSheet("background: transparent; border: none;")
                    img_lbl.setToolTip(val_clean)
                    b_lay.addWidget(img_lbl)
                    badge.setToolTip(val_clean)
                    return badge
                else:
                    txt_lbl = QLabel(val_clean[:6])
                    txt_lbl.setStyleSheet("color: #c6d0f5; font-size: 10px; background: transparent; border: none;")
                    txt_lbl.setAlignment(Qt.AlignCenter)
                    badge.setToolTip(val_clean)
                    b_lay.addWidget(txt_lbl)
                    return badge
            else:
                txt_lbl = QLabel("(none)")
                txt_lbl.setStyleSheet("color: #737994; font-size: 9px; font-style: italic; background: transparent; border: none;")
                txt_lbl.setAlignment(Qt.AlignCenter)
                b_lay.addWidget(txt_lbl)
                badge.setToolTip("(no icon)")
                return badge

        r_lay.addWidget(make_badge(before_val, is_after=False))

        arrow = QLabel("➔")
        arrow.setStyleSheet("color: #ea999c; font-size: 12px; font-weight: bold; background: transparent;")
        r_lay.addWidget(arrow)

        r_lay.addWidget(make_badge(after_val, is_after=True))
        r_lay.addStretch()
        return row

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
        painter.setBrush(QColor("#121212"))
        painter.setPen(QPen(QColor("#414559"), 1.5))
        painter.drawRoundedRect(self.rect().adjusted(1, 1, -2, -2), 16, 16)

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
            try:
                if hasattr(self, 'signals') and self.signals:
                    self.signals.finished.emit(self.filepath)
            except RuntimeError:
                pass
        except Exception as e:
            try:
                if hasattr(self, 'signals') and self.signals:
                    self.signals.error.emit(self.filepath, str(e))
            except RuntimeError:
                pass
        finally:
            AsyncFileIo._pending_count = max(0, AsyncFileIo._pending_count - 1)
            AsyncFileIo._active_workers.discard(self)

class AsyncFileIo:
    _pool = QThreadPool.globalInstance()
    _pending_count = 0
    _active_workers = set()
    
    @classmethod
    def has_pending_writes(cls):
        return cls._pending_count > 0

    @classmethod
    def write(cls, filepath, content, on_success=None, on_error=None):
        cls._pending_count += 1
        worker = AsyncWriterWorker(filepath, content)
        cls._active_workers.add(worker)
        if on_success: worker.signals.finished.connect(on_success)
        if on_error: worker.signals.error.connect(on_error)
        cls._pool.start(worker)

def validate_nss_syntax(content):
    stack = []
    in_string = False
    string_char = ''
    is_triple = False
    in_comment = False
    in_multiline_comment = False

    i = 0
    n = len(content)
    while i < n:
        char = content[i]

        if in_comment:
            if char == '\n':
                in_comment = False
            i += 1
            continue

        if in_multiline_comment:
            if char == '*' and i + 1 < n and content[i+1] == '/':
                in_multiline_comment = False
                i += 2
                continue
            i += 1
            continue

        if in_string:
            if is_triple:
                if content[i:i+3] == string_char * 3:
                    in_string = False
                    is_triple = False
                    i += 3
                    continue
            else:
                if char == string_char and (i == 0 or content[i-1] != '\\'):
                    in_string = False
            i += 1
            continue

        if char == '/' and i + 1 < n:
            next_char = content[i+1]
            if next_char == '/':
                in_comment = True
                i += 2
                continue
            elif next_char == '*':
                in_multiline_comment = True
                i += 2
                continue

        if char in ('"', "'"):
            in_string = True
            string_char = char
            if i + 2 < n and content[i:i+3] == char * 3:
                is_triple = True
                i += 3
                continue
            i += 1
            continue

        if char in ('{', '[', '('):
            stack.append(char)
        elif char == '}':
            if not stack or stack[-1] != '{': return False
            stack.pop()
        elif char == ']':
            if not stack or stack[-1] != '[': return False
            stack.pop()
        elif char == ')':
            if not stack or stack[-1] != '(': return False
            stack.pop()

        i += 1

    return not in_string and not in_multiline_comment and len(stack) == 0

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
    if not directory or not os.path.exists(directory):
        return
    try:
        abs_dir = os.path.abspath(directory).lower()
        TH32CS_SNAPPROCESS = 0x00000002
        PROCESS_TERMINATE = 0x0001
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

        class PROCESSENTRY32(ctypes.Structure):
            _fields_ = [
                ('dwSize', wintypes.DWORD),
                ('cntUsage', wintypes.DWORD),
                ('th32ProcessID', wintypes.DWORD),
                ('th32DefaultHeapID', ctypes.c_void_p),
                ('th32ModuleID', wintypes.DWORD),
                ('cntThreads', wintypes.DWORD),
                ('th32ParentProcessID', wintypes.DWORD),
                ('pcPriClassBase', ctypes.c_long),
                ('dwFlags', wintypes.DWORD),
                ('szExeFile', ctypes.c_char * 260)
            ]

        h_snap = ctypes.windll.kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
        if h_snap == -1 or not h_snap:
            return

        try:
            pe = PROCESSENTRY32()
            pe.dwSize = ctypes.sizeof(PROCESSENTRY32)
            if ctypes.windll.kernel32.Process32First(h_snap, ctypes.byref(pe)):
                while True:
                    pid = pe.th32ProcessID
                    if pid > 4:
                        h_proc = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION | PROCESS_TERMINATE, False, pid)
                        if h_proc:
                            try:
                                exe_buf = (ctypes.c_wchar * 1024)()
                                exe_size = wintypes.DWORD(1024)
                                if ctypes.windll.kernel32.QueryFullProcessImageNameW(h_proc, 0, exe_buf, ctypes.byref(exe_size)):
                                    exe_path = exe_buf.value
                                    if exe_path and os.path.abspath(exe_path).lower().startswith(abs_dir):
                                        ctypes.windll.kernel32.TerminateProcess(h_proc, 1)
                            finally:
                                ctypes.windll.kernel32.CloseHandle(h_proc)
                    if not ctypes.windll.kernel32.Process32Next(h_snap, ctypes.byref(pe)):
                        break
        finally:
            ctypes.windll.kernel32.CloseHandle(h_snap)
    except Exception:
        pass

class WINDOWCOMPOSITIONATTRIBDATA(ctypes.Structure): _fields_ = [('Attribute', ctypes.c_int), ('Data', ctypes.c_void_p), ('SizeOfData', ctypes.c_size_t)]
class ACCENT_POLICY(ctypes.Structure): _fields_ = [('AccentState', ctypes.c_int), ('AccentFlags', ctypes.c_int), ('GradientColor', ctypes.c_int), ('AnimationId', ctypes.c_int)]

def set_window_effect(hwnd, effect='acrylic'):
    if not hwnd: return
    user32 = ctypes.windll.user32; dwmapi = ctypes.windll.dwmapi; margins = wintypes.RECT(-1, -1, -1, -1); dwmapi.DwmExtendFrameIntoClientArea(hwnd, ctypes.byref(margins))
    if effect == 'acrylic':
        accent = ACCENT_POLICY(); accent.AccentState = 4; accent.GradientColor = 0x01121212; data = WINDOWCOMPOSITIONATTRIBDATA(); data.Attribute = 19; data.Data = ctypes.cast(ctypes.pointer(accent), ctypes.c_void_p); data.SizeOfData = ctypes.sizeof(accent); user32.SetWindowCompositionAttribute(hwnd, ctypes.byref(data))
    elif effect == 'mica': DWMWA_MICA_EFFECT = 1029; dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_MICA_EFFECT, ctypes.byref(ctypes.c_int(1)), 4)

def send_ipc_command(cmd_string):
    try:
        user32 = ctypes.windll.user32
        SMTO_ABORTIFHUNG = 0x0002
        HWND_MESSAGE = -3
        WM_COPYDATA = 0x004A

        if cmd_string == 'CMD_RELOAD':
            msg_id = user32.RegisterWindowMessageW("iMA_IPC_Command")
            hwnd = user32.FindWindowW("Shell_TrayWnd", None)
            if hwnd:
                user32.SendMessageTimeoutW(hwnd, msg_id, 1, 0, SMTO_ABORTIFHUNG, 1000, None)
                return True
            return False

        hwnd = user32.FindWindowExW(HWND_MESSAGE, 0, "iMA_IPC_Class", "iMA_IPC_Window")
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

        user32.SendMessageTimeoutW(hwnd, WM_COPYDATA, 0, ctypes.addressof(cds), SMTO_ABORTIFHUNG, 1000, None)
        return True
    except Exception as e:
        print(f"IPC Error: {e}")
        return False

def trigger_shell_reload(close_only=False, **kwargs):
    wait_start = time.time()
    while AsyncFileIo.has_pending_writes() and time.time() - wait_start < 1.0:
        time.sleep(0.05)

    try:
        user32 = ctypes.windll.user32
        WM_CLOSE = 0x0010
        WM_COMMAND = 0x0111

        hwnd_menu = user32.FindWindowW("#32768", None)
        while hwnd_menu:
            user32.SendMessageW(hwnd_menu, WM_CLOSE, 0, 0)
            hwnd_menu = user32.FindWindowW("#32768", None)

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

        tray = user32.FindWindowW('Shell_TrayWnd', None)
        if tray: user32.PostMessageW(tray, WM_COMMAND, 28931, 0)
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

        class VS_FIXEDFILEINFO(ctypes.Structure):
            _fields_ = [
                ('dwSignature', wintypes.DWORD),
                ('dwStrucVersion', wintypes.DWORD),
                ('dwFileVersionMS', wintypes.DWORD),
                ('dwFileVersionLS', wintypes.DWORD),
                ('dwProductVersionMS', wintypes.DWORD),
                ('dwProductVersionLS', wintypes.DWORD),
                ('dwFileFlagsMask', wintypes.DWORD),
                ('dwFileFlags', wintypes.DWORD),
                ('dwFileOS', wintypes.DWORD),
                ('dwFileType', wintypes.DWORD),
                ('dwFileSubtype', wintypes.DWORD),
                ('dwFileDateMS', wintypes.DWORD),
                ('dwFileDateLS', wintypes.DWORD)
            ]

        version_dll = ctypes.windll.version
        size = version_dll.GetFileVersionInfoSizeW(dll_path, None)
        if not size:
            return (0, 0, 0, 0)
        res = ctypes.create_string_buffer(size)
        if not version_dll.GetFileVersionInfoW(dll_path, 0, size, res):
            return (0, 0, 0, 0)
        ptr = ctypes.c_void_p()
        uLen = wintypes.UINT()
        if not version_dll.VerQueryValueW(res, r'\\', ctypes.byref(ptr), ctypes.byref(uLen)):
            return (0, 0, 0, 0)
        ffi = VS_FIXEDFILEINFO.from_address(ptr.value)
        ms = ffi.dwFileVersionMS
        ls = ffi.dwFileVersionLS
        return (ms >> 16, ms & 0xFFFF, ls >> 16, ls & 0xFFFF)
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

def make_circular_pixmap(pixmap, size=72):
    if not pixmap or pixmap.isNull():
        return QPixmap()
    target = QPixmap(size, size)
    target.fill(Qt.transparent)
    scaled = pixmap.scaled(size, size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
    x = max(0, (scaled.width() - size) // 2)
    y = max(0, (scaled.height() - size) // 2)
    cropped = scaled.copy(x, y, size, size)
    painter = QPainter(target)
    painter.setRenderHint(QPainter.Antialiasing, True)
    painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
    path = QPainterPath()
    path.addEllipse(1, 1, size - 2, size - 2)
    painter.setClipPath(path)
    painter.drawPixmap(0, 0, cropped)
    painter.setClipping(False)
    painter.setPen(QPen(QColor(255, 255, 255, 45), 1.5))
    painter.setBrush(Qt.NoBrush)
    painter.drawEllipse(1, 1, size - 2, size - 2)
    painter.end()
    return target

def make_initial_avatar_pixmap(initial="U", size=72, bg_color="#e78284", text_color="#1e2030"):
    target = QPixmap(size, size)
    target.fill(Qt.transparent)
    painter = QPainter(target)
    painter.setRenderHint(QPainter.Antialiasing, True)
    painter.setRenderHint(QPainter.TextAntialiasing, True)
    painter.setBrush(QColor(bg_color))
    painter.setPen(QPen(QColor(255, 255, 255, 45), 1.5))
    painter.drawEllipse(1, 1, size - 2, size - 2)
    painter.setPen(QColor(text_color))
    font = QFont('Segoe UI Variable Display', max(10, int(size * 0.42)), QFont.Bold)
    painter.setFont(font)
    ch = (initial or 'U')[:1].upper()
    painter.drawText(QRect(0, 0, size, size), Qt.AlignCenter, ch)
    painter.end()
    return target

class AccountProfileDialog(QDialog):
    def __init__(self, parent=None, user_name="", user_email="", avatar_pixmap=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(360, 310)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        self.frame = QFrame()
        self.frame.setObjectName("accountProfileFrame")
        self.frame.setStyleSheet("""
            #accountProfileFrame {
                background-color: #121212;
                border: 1px solid #2a2a30;
                border-radius: 20px;
            }
        """)
        main_layout.addWidget(self.frame)

        fl = QVBoxLayout(self.frame)
        fl.setContentsMargins(28, 26, 28, 22)
        fl.setSpacing(6)
        fl.setAlignment(Qt.AlignTop | Qt.AlignHCenter)

        avatar_label = QLabel()
        avatar_label.setFixedSize(76, 76)
        avatar_label.setAlignment(Qt.AlignCenter)
        avatar_label.setStyleSheet("border: none; background: transparent;")
        if avatar_pixmap and not avatar_pixmap.isNull():
            avatar_label.setPixmap(avatar_pixmap)
        else:
            initial = (user_name or user_email or "U")[:1]
            avatar_label.setPixmap(make_initial_avatar_pixmap(initial, size=76))
        fl.addWidget(avatar_label, 0, Qt.AlignHCenter)

        fl.addSpacing(6)

        name_label = QLabel(user_name or "Google User")
        name_label.setStyleSheet("color: white; font-size: 17px; font-weight: bold; border: none; background: transparent;")
        name_label.setAlignment(Qt.AlignCenter)
        fl.addWidget(name_label, 0, Qt.AlignHCenter)

        email_label = QLabel(user_email or "")
        email_label.setStyleSheet("color: #a5adce; font-size: 13px; border: none; background: transparent;")
        email_label.setAlignment(Qt.AlignCenter)
        fl.addWidget(email_label, 0, Qt.AlignHCenter)

        fl.addSpacing(14)

        logout_btn = QPushButton("Log out")
        logout_btn.setFixedHeight(38)
        logout_btn.setCursor(Qt.PointingHandCursor)
        logout_btn.setStyleSheet("""
            QPushButton {
                background-color: #e78284;
                border: 1px solid #ea999c;
                border-radius: 12px;
                color: #1e2030;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #ea999c;
            }
        """)
        logout_btn.clicked.connect(lambda: self.done(1))
        fl.addWidget(logout_btn)

        fl.addSpacing(4)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedHeight(38)
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #26262c;
                border: 1px solid #363640;
                border-radius: 12px;
                color: #c6d0f5;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #363642;
                color: #ffffff;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        fl.addWidget(cancel_btn)

    def mousePressEvent(self, e):
        if hasattr(self, 'frame') and not self.frame.geometry().contains(e.pos()):
            self.reject()
        else:
            super().mousePressEvent(e)


class FlowLayout(QLayout):
    def __init__(self, parent=None, margin=0, spacing=-1):
        super().__init__(parent)
        if parent is not None:
            self.setContentsMargins(margin, margin, margin, margin)
        self.setSpacing(spacing)
        self.itemList = []

    def addItem(self, item): self.itemList.append(item)
    def count(self): return len(self.itemList)
    def itemAt(self, index): return self.itemList[index] if 0 <= index < len(self.itemList) else None
    def takeAt(self, index): return self.itemList.pop(index) if 0 <= index < len(self.itemList) else None
    def expandingDirections(self): return Qt.Orientations(Qt.Orientation(0))
    def hasHeightForWidth(self): return True
    def heightForWidth(self, width): return self.doLayout(QRect(0, 0, width, 0), True)
    def setGeometry(self, rect): super().setGeometry(rect); self.doLayout(rect, False)
    def sizeHint(self): return self.minimumSize()
    def minimumSize(self):
        size = QSize()
        for item in self.itemList:
            w = item.widget()
            if w is None or not w.isHidden():
                size = size.expandedTo(item.minimumSize())
        m = self.contentsMargins()
        return size + QSize(m.left() + m.right(), m.top() + m.bottom())

    def doLayout(self, rect, testOnly):
        x = rect.x(); y = rect.y(); lineHeight = 0
        m = self.contentsMargins()
        effective_spacing = self.spacing() if self.spacing() >= 0 else 6
        for item in self.itemList:
            w = item.widget()
            if w is not None and w.isHidden():
                continue
            spaceX = effective_spacing
            spaceY = effective_spacing
            nextX = x + item.sizeHint().width() + spaceX
            if nextX - spaceX > rect.right() and lineHeight > 0:
                x = rect.x()
                y = y + lineHeight + spaceY
                nextX = x + item.sizeHint().width() + spaceX
                lineHeight = 0
            if not testOnly:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))
            x = nextX
            lineHeight = max(lineHeight, item.sizeHint().height())
        return y + lineHeight - rect.y() + m.bottom()

class ModernSwitch(QWidget):
    stateChanged = pyqtSignal(bool)
    def __init__(self, parent=None, checked=False):
        super().__init__(parent); self.setFixedSize(50, 26); self._checked = checked; self._pos_val = 1.0 if checked else 0.0
        self._anim = QPropertyAnimation(self, b"pos_val"); self._anim.setDuration(400); self._anim.setEasingCurve(QEasingCurve.OutBack)
        self.setCursor(Qt.PointingHandCursor)
    @pyqtProperty(float)
    def pos_val(self): return self._pos_val
    @pos_val.setter
    def pos_val(self, v): self._pos_val = v; self.update()
    def mousePressEvent(self, e): self._checked = not self._checked; self._anim.setStartValue(self._pos_val); self._anim.setEndValue(1.0 if self._checked else 0.0); self._anim.start(); self.stateChanged.emit(self._checked)
    def isChecked(self): return self._checked
    def setChecked(self, v): self._checked = v; self._pos_val = 1.0 if v else 0.0; self.update()
    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing); r = self.rect(); bg = QColor("#e78284") if self._checked else QColor("#2a2a30")
        p.setBrush(bg); p.setPen(Qt.NoPen); p.drawRoundedRect(r, r.height()/2, r.height()/2); handle = QColor("#ffffff") if self._checked else QColor("#b0b0b0")
        p.setBrush(handle); x = 4 + (r.width() - 24) * self._pos_val; p.drawEllipse(int(x), 4, 18, 18)

class PillProgressBar(QWidget):
    def __init__(self, parent=None, height=20):
        super().__init__(parent); self.setFixedHeight(height); self.value = 0
        self.setMinimumWidth(120)
        self.main_layout = QHBoxLayout(self); self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.groove = QFrame(); self.groove.setObjectName("pillGroove")
        self.groove.setStyleSheet(f"QFrame#pillGroove {{ background-color: rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: {height//2}px; }}")
        self.fill = QFrame(self.groove); self.fill.setObjectName("pillFill")
        self.fill.setStyleSheet(f"QFrame#pillFill {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #e78284, stop:1 #ea999c); border-radius: {max(2, (height-4)//2)}px; }}")
        self.fill.setGeometry(2, 2, 0, height - 4); self.main_layout.addWidget(self.groove)
    def setValue(self, val):
        self.value = max(0, min(100, val))
        if self.value <= 0: self.fill.hide(); return
        self.fill.show()
        max_w = self.groove.width() - 4
        if max_w <= 0: return
        new_w = max(2, int(max_w * (self.value / 100)))
        self.fill.setGeometry(2, 2, new_w, self.height() - 4)
    def resizeEvent(self, e): super().resizeEvent(e); self.setValue(self.value)
    def setVisible(self, v): super().setVisible(v)

class CapsuleActionButton(QPushButton):
    """
    Modern capsule/pill action button with tactile colored icon badge, slightly lighter dark
    background, and smooth morphing animation into a circular progress widget during installation.
    """
    def __init__(self, action_type='install', text=None, parent=None, height=34):
        super().__init__(parent)
        self._height = height
        self._action_type = (action_type or 'install').lower()
        self._custom_text = text
        self._display_progress = 0.0
        self._target_progress = 0.0
        self._hover_alpha = 0.0
        self._is_pressed = False
        self._is_hovered = False
        self._spin_angle = 0.0
        self._dot_count = 0
        self._compact = False

        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(self._height)
        self.setAttribute(Qt.WA_Hover, True)
        self.setStyleSheet("background: transparent; border: none;")

        # Smooth width transition between action states
        self._width_anim = QVariantAnimation(self)
        self._width_anim.setDuration(200)
        self._width_anim.setEasingCurve(QEasingCurve.OutCubic)
        self._width_anim.valueChanged.connect(self._on_width_step)

        # Progress arc glide animation
        self._prog_anim = QVariantAnimation(self)
        self._prog_anim.setDuration(220)
        self._prog_anim.setEasingCurve(QEasingCurve.OutQuad)
        self._prog_anim.valueChanged.connect(self._on_prog_step)

        # Hover transition animation
        self._hover_anim = QVariantAnimation(self)
        self._hover_anim.setDuration(180)
        self._hover_anim.valueChanged.connect(self._on_hover_step)

        # Indeterminate 60fps spinner timer
        self._spin_timer = QTimer(self)
        self._spin_timer.setInterval(16)
        self._spin_timer.timeout.connect(self._on_spin_tick)

        # Animated dots timer for 'Installing...'
        self._dot_timer = QTimer(self)
        self._dot_timer.setInterval(350)
        self._dot_timer.timeout.connect(self._on_dot_tick)

        self._update_dimensions(animated=False)
        if self._action_type == 'installing':
            self._dot_timer.start()
            self._spin_timer.start()

    def set_compact(self, compact=True):
        if self._compact != compact:
            self._compact = compact
            self._update_dimensions(animated=False)
            self.update()

    def set_height(self, h):
        if self._height != h:
            self._height = h
            self.setFixedHeight(h)
            self._update_dimensions(animated=False)
            self.update()

    def _get_display_text(self):
        if self._custom_text is not None:
            return self._custom_text
        if self._action_type == 'installing':
            return "Installing" + ("." * self._dot_count)
        defaults = {
            'install': 'Install',
            'uninstall': 'Uninstall',
            'update': 'Update',
            'enable': 'Enable',
            'disable': 'Disable',
            'delete': 'Delete',
            'queued': 'Queued',
            'cancel': 'Cancel'
        }
        return defaults.get(self._action_type, self._action_type.capitalize())

    def _calculate_pill_width(self):
        txt = "Installing..." if self._action_type == 'installing' else self._get_display_text()
        font_size = 9 if self._compact else 10
        font = QFont('Segoe UI Variable Display', font_size, QFont.Bold)
        fm = QFontMetrics(font)
        txt_w = fm.horizontalAdvance(txt) if hasattr(fm, 'horizontalAdvance') else fm.width(txt)
        badge_diam = self._height - (6 if self._compact else 8)
        gap = 4 if self._compact else 8
        pad_right = 8 if self._compact else 14
        left_pad = 3 if self._compact else 4
        w = left_pad + badge_diam + gap + txt_w + pad_right
        min_w = self._height + (24 if self._compact else 40)
        return max(w, min_w)

    def _update_dimensions(self, animated=False):
        target_w = float(self._calculate_pill_width())
        if animated and self.isVisible() and self.width() > 0:
            if self._width_anim.state() == QVariantAnimation.Running:
                self._width_anim.stop()
            self._width_anim.setStartValue(float(self.width()))
            self._width_anim.setEndValue(target_w)
            self._width_anim.start()
        else:
            self.setFixedWidth(int(target_w))
            self.update()

    def _on_width_step(self, val):
        self.setFixedWidth(int(val))
        self.update()

    def _on_prog_step(self, val):
        self._display_progress = float(val)
        self.update()

    def _on_hover_step(self, val):
        self._hover_alpha = float(val)
        self.update()

    def _on_spin_tick(self):
        self._spin_angle = (self._spin_angle + 4.0) % 360.0
        self.update()

    def _on_dot_tick(self):
        self._dot_count = (self._dot_count + 1) % 4
        self.update()

    def set_state(self, action_type, text=None, animated=True):
        new_action = (action_type or 'install').lower()
        if text is not None:
            self._custom_text = text

        self._action_type = new_action

        if new_action == 'installing':
            self.setToolTip("Click to Cancel")
            self._dot_count = 0
            if not self._dot_timer.isActive():
                self._dot_timer.start()
            if self._target_progress <= 0:
                if not self._spin_timer.isActive():
                    self._spin_timer.start()
        else:
            self.setToolTip("")
            if self._dot_timer.isActive():
                self._dot_timer.stop()
            if self._spin_timer.isActive():
                self._spin_timer.stop()
            self._display_progress = 0.0
            self._target_progress = 0.0

        self._update_dimensions(animated=animated)
        self.update()

    def setValue(self, val):
        val = max(0.0, min(100.0, float(val)))
        self._target_progress = val
        if val > 0:
            if self._spin_timer.isActive():
                self._spin_timer.stop()
        elif self._action_type == 'installing' and not self._spin_timer.isActive():
            self._spin_timer.start()

        if self._prog_anim.state() == QVariantAnimation.Running:
            self._prog_anim.stop()
        self._prog_anim.setStartValue(self._display_progress)
        self._prog_anim.setEndValue(val)
        self._prog_anim.start()

    def setProgress(self, val):
        self.setValue(val)

    def value(self):
        return self._target_progress

    def setText(self, text):
        self._custom_text = text
        self._update_dimensions(animated=False)
        self.update()

    def text(self):
        return self._get_display_text()

    def enterEvent(self, e):
        self._is_hovered = True
        if self._hover_anim.state() == QVariantAnimation.Running:
            self._hover_anim.stop()
        self._hover_anim.setStartValue(self._hover_alpha)
        self._hover_anim.setEndValue(1.0)
        self._hover_anim.start()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._is_hovered = False
        if self._hover_anim.state() == QVariantAnimation.Running:
            self._hover_anim.stop()
        self._hover_anim.setStartValue(self._hover_alpha)
        self._hover_anim.setEndValue(0.0)
        self._hover_anim.start()
        super().leaveEvent(e)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._is_pressed = True
            self.update()
        super().mousePressEvent(e)

    def mouseReleaseEvent(self, e):
        self._is_pressed = False
        self.update()
        super().mouseReleaseEvent(e)

    @staticmethod
    def _draw_download_icon(p, cx, cy, size=18, color='#ffffff', stroke=2.2):
        p.setPen(QPen(QColor(color), stroke, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.setBrush(Qt.NoBrush)
        half = size / 2.0
        top_y = cy - half * 0.70
        bot_y = cy + half * 0.25
        p.drawLine(QPointF(cx, top_y), QPointF(cx, bot_y))
        head_w = half * 0.65
        head_h = half * 0.50
        path = QPainterPath()
        path.moveTo(cx - head_w, bot_y - head_h)
        path.lineTo(cx, bot_y)
        path.lineTo(cx + head_w, bot_y - head_h)
        p.drawPath(path)
        tray_y = cy + half * 0.75
        tray_w = half * 0.85
        p.drawLine(QPointF(cx - tray_w, tray_y), QPointF(cx + tray_w, tray_y))

    @staticmethod
    def _draw_trash_icon(p, cx, cy, size=16, color='#ffffff', stroke=1.8):
        p.setPen(QPen(QColor(color), stroke, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.setBrush(Qt.NoBrush)
        w = size * 0.7
        h = size * 0.8
        p.drawLine(QPointF(cx - w*0.6, cy - h*0.45), QPointF(cx + w*0.6, cy - h*0.45))
        p.drawLine(QPointF(cx - w*0.25, cy - h*0.6), QPointF(cx + w*0.25, cy - h*0.6))
        p.drawLine(QPointF(cx - w*0.25, cy - h*0.6), QPointF(cx - w*0.25, cy - h*0.45))
        p.drawLine(QPointF(cx + w*0.25, cy - h*0.6), QPointF(cx + w*0.25, cy - h*0.45))
        path = QPainterPath()
        path.moveTo(cx - w*0.45, cy - h*0.45)
        path.lineTo(cx - w*0.40, cy + h*0.45)
        path.lineTo(cx + w*0.40, cy + h*0.45)
        path.lineTo(cx + w*0.45, cy - h*0.45)
        p.drawPath(path)
        p.drawLine(QPointF(cx - w*0.15, cy - h*0.25), QPointF(cx - w*0.15, cy + h*0.25))
        p.drawLine(QPointF(cx + w*0.15, cy - h*0.25), QPointF(cx + w*0.15, cy + h*0.25))

    @staticmethod
    def _draw_sync_icon(p, cx, cy, size=16, color='#ffffff', stroke=2.0):
        p.setPen(QPen(QColor(color), stroke, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.setBrush(Qt.NoBrush)
        r = size * 0.40
        rect = QRectF(cx - r, cy - r, r*2, r*2)
        p.drawArc(rect, 35 * 16, 110 * 16)
        p.drawLine(QPointF(cx + r*0.5, cy - r*0.9), QPointF(cx + r*0.9, cy - r*0.5))
        p.drawLine(QPointF(cx + r*0.3, cy - r*0.4), QPointF(cx + r*0.9, cy - r*0.5))
        p.drawArc(rect, 215 * 16, 110 * 16)
        p.drawLine(QPointF(cx - r*0.5, cy + r*0.9), QPointF(cx - r*0.9, cy + r*0.5))
        p.drawLine(QPointF(cx - r*0.3, cy + r*0.4), QPointF(cx - r*0.9, cy + r*0.5))

    @staticmethod
    def _draw_check_icon(p, cx, cy, size=16, color='#ffffff', stroke=2.2):
        p.setPen(QPen(QColor(color), stroke, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.setBrush(Qt.NoBrush)
        path = QPainterPath()
        path.moveTo(cx - size*0.35, cy)
        path.lineTo(cx - size*0.08, cy + size*0.28)
        path.lineTo(cx + size*0.38, cy - size*0.28)
        p.drawPath(path)

    @staticmethod
    def _draw_ban_icon(p, cx, cy, size=16, color='#ffffff', stroke=2.0):
        p.setPen(QPen(QColor(color), stroke, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.setBrush(Qt.NoBrush)
        r = size * 0.42
        p.drawEllipse(QPointF(cx, cy), r, r)
        dx = r * 0.707
        dy = r * 0.707
        p.drawLine(QPointF(cx - dx, cy - dy), QPointF(cx + dx, cy + dy))

    @staticmethod
    def _draw_clock_icon(p, cx, cy, size=16, color='#ffffff', stroke=1.8):
        p.setPen(QPen(QColor(color), stroke, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.setBrush(Qt.NoBrush)
        r = size * 0.42
        p.drawEllipse(QPointF(cx, cy), r, r)
        p.drawLine(QPointF(cx, cy), QPointF(cx, cy - r * 0.55))
        p.drawLine(QPointF(cx, cy), QPointF(cx + r * 0.45, cy))

    @staticmethod
    def _draw_cancel_icon(p, cx, cy, size=14, color='#ffffff', stroke=2.0):
        p.setPen(QPen(QColor(color), stroke, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.setBrush(Qt.NoBrush)
        half = size * 0.40
        p.drawLine(QPointF(cx - half, cy - half), QPointF(cx + half, cy + half))
        p.drawLine(QPointF(cx + half, cy - half), QPointF(cx - half, cy + half))

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)

        w = self.width()
        h = self.height()
        r = h / 2.0
        btn_rect = QRectF(0, 0, w, h)

        # Lighter dark background (#252830 normal, #2e323c hover, #1d2027 pressed)
        if self._is_pressed:
            bg_col = QColor('#1d2027')
        else:
            base_r, base_g, base_b = 37, 40, 48       # #252830
            hover_r, hover_g, hover_b = 46, 50, 60    # #2e323c
            cur_r = int(base_r + (hover_r - base_r) * self._hover_alpha)
            cur_g = int(base_g + (hover_g - base_g) * self._hover_alpha)
            cur_b = int(base_b + (hover_b - base_b) * self._hover_alpha)
            bg_col = QColor(cur_r, cur_g, cur_b)

        p.setPen(Qt.NoPen)
        p.setBrush(bg_col)
        p.drawRoundedRect(btn_rect, r, r)

        # Specular rim / border
        border_alpha = int(22 + 23 * self._hover_alpha)
        p.setPen(QPen(QColor(255, 255, 255, border_alpha), 1.0))
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(btn_rect.adjusted(0.5, 0.5, -0.5, -0.5), r - 0.5, r - 0.5)

        # Badge coordinates
        badge_pad = 3.0 if self._compact else 4.0
        badge_diam = h - (badge_pad * 2.0)
        badge_radius = badge_diam / 2.0
        cx = badge_pad + badge_radius
        cy = h / 2.0

        if self._is_pressed:
            cy += 1.0

        if self._action_type == 'installing':
            # Circular progress arc around the install/download icon
            track_r = badge_radius - 1.0
            track_rect = QRectF(cx - track_r, cy - track_r, track_r * 2.0, track_r * 2.0)
            stroke_w = 2.2

            # Dark circular back
            p.setPen(Qt.NoPen)
            p.setBrush(QColor('#1b1e26'))
            p.drawEllipse(track_rect)

            # Circular track ring
            p.setPen(QPen(QColor('#333842'), stroke_w, Qt.SolidLine, Qt.RoundCap))
            p.setBrush(Qt.NoBrush)
            p.drawEllipse(track_rect)

            # Vibrant green progress arc
            arc_col = QColor('#38b449')
            p.setPen(QPen(arc_col, stroke_w, Qt.SolidLine, Qt.RoundCap))
            if self._display_progress <= 0:
                start_a = int((90.0 - self._spin_angle) * 16.0)
                p.drawArc(track_rect, start_a, -int(90.0 * 16.0))
            else:
                span = -int((self._display_progress / 100.0) * 360.0 * 16.0)
                p.drawArc(track_rect, 90 * 16, span)

            # Center download icon (or cancel if hovered)
            if self._is_hovered:
                self._draw_cancel_icon(p, cx, cy, size=13, stroke=2.0, color='#ff6b6b')
            else:
                self._draw_download_icon(p, cx, cy, size=15, stroke=1.8, color='#ffffff')
        else:
            # Solid tactile badge
            badge_rect = QRectF(cx - badge_radius, cy - badge_radius, badge_diam, badge_diam)
            b_grad = QLinearGradient(badge_rect.topLeft(), badge_rect.bottomLeft())

            if self._action_type == 'install':
                b_grad.setColorAt(0.0, QColor('#42be54'))
                b_grad.setColorAt(1.0, QColor('#2ea043'))
            elif self._action_type in ('uninstall', 'delete', 'cancel'):
                b_grad.setColorAt(0.0, QColor('#f87171'))
                b_grad.setColorAt(1.0, QColor('#dc2626'))
            elif self._action_type == 'update':
                b_grad.setColorAt(0.0, QColor('#60a5fa'))
                b_grad.setColorAt(1.0, QColor('#2563eb'))
            elif self._action_type == 'enable':
                b_grad.setColorAt(0.0, QColor('#34d399'))
                b_grad.setColorAt(1.0, QColor('#059669'))
            elif self._action_type == 'disable':
                b_grad.setColorAt(0.0, QColor('#f87171'))
                b_grad.setColorAt(1.0, QColor('#dc2626'))
            elif self._action_type == 'queued':
                b_grad.setColorAt(0.0, QColor('#fbbf24'))
                b_grad.setColorAt(1.0, QColor('#d97706'))
            else:
                b_grad.setColorAt(0.0, QColor('#42be54'))
                b_grad.setColorAt(1.0, QColor('#2ea043'))

            # Drop shadow
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(0, 0, 0, 60))
            p.drawEllipse(badge_rect.adjusted(0, 1, 0, 1))

            p.setBrush(b_grad)
            p.drawEllipse(badge_rect)

            # Specular inner ring
            p.setPen(QPen(QColor(255, 255, 255, 50), 0.75))
            p.setBrush(Qt.NoBrush)
            p.drawEllipse(badge_rect)

            # Vector icon
            icon_col = '#ffffff'
            if self._action_type == 'install':
                self._draw_download_icon(p, cx, cy, size=16, stroke=2.0, color=icon_col)
            elif self._action_type in ('uninstall', 'delete'):
                self._draw_trash_icon(p, cx, cy, size=15, stroke=1.8, color=icon_col)
            elif self._action_type == 'update':
                self._draw_sync_icon(p, cx, cy, size=15, stroke=2.0, color=icon_col)
            elif self._action_type == 'enable':
                self._draw_check_icon(p, cx, cy, size=15, stroke=2.2, color=icon_col)
            elif self._action_type == 'disable':
                self._draw_ban_icon(p, cx, cy, size=15, stroke=2.0, color=icon_col)
            elif self._action_type == 'queued':
                self._draw_clock_icon(p, cx, cy, size=15, stroke=1.8, color=icon_col)
            elif self._action_type == 'cancel':
                self._draw_cancel_icon(p, cx, cy, size=13, stroke=2.0, color=icon_col)
            else:
                self._draw_download_icon(p, cx, cy, size=16, stroke=2.0, color=icon_col)

        # Text rendering
        txt = self._get_display_text()
        p.setPen(QColor(255, 255, 255))
        font_size = 9 if self._compact else 10
        font = QFont('Segoe UI Variable Display', font_size, QFont.Bold)
        p.setFont(font)
        gap = 4.0 if self._compact else 8.0
        text_x = cx + badge_radius + gap
        text_rect = QRectF(text_x, 0, max(10.0, w - text_x - (4.0 if self._compact else 8.0)), h)
        p.drawText(text_rect, Qt.AlignLeft | Qt.AlignVCenter, txt)

        p.end()

# Icon & Menu Discovery Cache
_cached_nss_menus = {}
_asset_pixmap_cache = {}

def get_nss_menus_dict(force_refresh=False):
    global _cached_nss_menus
    if _cached_nss_menus and not force_refresh:
        return _cached_nss_menus
    
    root = PROJECT_ROOT
    if not root:
        if getattr(sys, 'frozen', False):
            base = os.path.dirname(os.path.abspath(sys.executable))
        else:
            base = os.path.dirname(os.path.abspath(__file__))
        root = os.path.dirname(base) if os.path.basename(base).lower() == 'launcher' else base

    menus = {}
    paths = [
        os.path.join(root, 'imports'),
        os.path.join(root, 'plugins'),
        os.path.join(root, 'Launcher', '_internal', 'imports'),
        os.path.join(root, '_internal', 'imports')
    ]
    try:
        from nss_parser import read_file, find_items_and_menus
        for p in paths:
            if not os.path.exists(p):
                continue
            for r, _, files in os.walk(p):
                for f in files:
                    if f.endswith('.nss') and f not in ('theme.nss', 'modify.nss'):
                        fp = os.path.join(r, f)
                        try:
                            content = read_file(fp)
                            for item in find_items_and_menus(content, types=('menu',)):
                                props = item.get('props', {})
                                title = str(props.get('title', '')).strip().strip("'\"")
                                if not title:
                                    m_target = str(props.get('menu', '')).strip().strip("'\"")
                                    if m_target.lower() in ('title.options', 'options'):
                                        title = 'Options'
                                if title:
                                    icon_val = props.get('icon') or props.get('image') or ''
                                    t_key = title.lower()
                                    if t_key not in menus or (icon_val and not menus[t_key].get('icon')):
                                        menus[t_key] = {'title': title, 'icon': icon_val, 'file': fp}
                        except Exception:
                            pass
    except Exception:
        pass
    _cached_nss_menus = menus
    return menus

def _extract_svg_markup(val):
    if not val: return None
    s = str(val).strip()
    s = re.sub(r"^[ '\"\[\\]+|[ '\"\]\\]+$", "", s).strip()
    if s.startswith('<svg') and s.endswith('</svg>'): return s
    if '<svg' in s and '</svg>' in s:
        start_idx = s.find('<svg')
        end_idx = s.rfind('</svg>') + 6
        return s[start_idx:end_idx]
    m = re.search(r"image\.svg\s*\(\s*", val, re.IGNORECASE)
    if not m: return None
    start = m.end(); pc = 1; p = start; qc = None
    while p < len(val) and pc > 0:
        if qc:
            if val[p] == qc and val[p-1] != '\\': qc = None
        elif val[p] in ("'", '"'): qc = val[p]
        elif val[p] == '(': pc += 1
        elif val[p] == ')': pc -= 1
        p += 1
    if pc == 0:
        return val[start:p-1].strip().strip("'").strip('"')
    return None

_THEME_COLOR_CACHE = ['#ffffff', '#ffffff']
_LAST_THEME_MTIME = 0

def get_theme_glyph_colors():
    global _THEME_COLOR_CACHE, _LAST_THEME_MTIME
    try:
        if getattr(sys, 'frozen', False):
            base = os.path.dirname(os.path.abspath(sys.executable))
        else:
            base = os.path.dirname(os.path.abspath(__file__))
        root = os.path.dirname(base) if os.path.basename(base).lower() == 'launcher' else base
        path = os.path.join(root, 'imports', 'theme.nss')
        if os.path.exists(path):
            mtime = os.path.getmtime(path)
            if mtime > _LAST_THEME_MTIME:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    m = re.search(r'image\.color\s*=\s*\[?\s*(#[0-9A-Fa-f]{3,8})\s*,\s*(#[0-9A-Fa-f]{3,8})\s*\]?', content)
                    if m: _THEME_COLOR_CACHE = [m.group(1), m.group(2)]
                    else:
                        m1 = re.search(r'image\.color\s*=\s*(#[0-9A-Fa-f]{3,8})', content)
                        if m1: _THEME_COLOR_CACHE = [m1.group(1), _THEME_COLOR_CACHE[1]]
                _LAST_THEME_MTIME = mtime
    except Exception:
        pass
    return _THEME_COLOR_CACHE

def render_nss_asset_pixmap(val, size=18):
    if not val: return None
    cache_key = (val, size)
    if cache_key in _asset_pixmap_cache:
        return _asset_pixmap_cache[cache_key]

    raw_str = str(val).strip()

    # 1. Check direct SVG markup
    svg = _extract_svg_markup(raw_str)
    if svg and QtSvg:
        try:
            custom_colors = re.findall(r"#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{4}|[0-9a-fA-F]{3})\b", raw_str)
            c1 = custom_colors[0] if len(custom_colors) > 0 and custom_colors[0] else "#ffffff"
            c2 = custom_colors[1] if len(custom_colors) > 1 and custom_colors[1] else c1
            clean_svg = svg.replace("@image.color1", c1).replace("@image.color2", c2).replace("@color3", c1)
            renderer = QtSvg.QSvgRenderer(clean_svg.encode('utf-8'))
            if renderer.isValid():
                pm = QPixmap(size * 2, size * 2); pm.fill(Qt.transparent)
                p = QPainter(pm); p.setRenderHint(QPainter.Antialiasing); p.setRenderHint(QPainter.SmoothPixmapTransform)
                renderer.render(p); p.end()
                res = pm.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                _asset_pixmap_cache[cache_key] = res
                return res
        except Exception:
            pass

    # 2. Check glyphs (supports single or dual glyphs / layered icons)
    codes = []
    for m in re.finditer(r'\\u([0-9A-Fa-f]{4})', raw_str, re.IGNORECASE):
        try: codes.append(int(m.group(1), 16))
        except Exception: pass
    if not codes:
        for m in re.finditer(r'0x([0-9A-Fa-f]{4})(?![0-9A-Fa-f])', raw_str, re.IGNORECASE):
            try: codes.append(int(m.group(1), 16))
            except Exception: pass
    if not codes and not raw_str.lower().endswith(('.png', '.svg', '.ico', '.dll', '.exe', '.jpg')):
        for ch in raw_str:
            c_ord = ord(ch)
            if 0xE000 <= c_ord <= 0xF8FF:
                codes.append(c_ord)

    if codes and not raw_str.lower().endswith(('.png', '.svg', '.ico', '.dll', '.exe', '.jpg')):
        try:
            glyphs_data = get_glyphs_data()
            _init_nilesoft_font()
            
            colors = []
            if '[[' in raw_str or '], [' in raw_str or '],[' in raw_str:
                blocks = re.findall(r'\[\s*([^\[\]]*?)\s*\]', raw_str)
                for b in blocks:
                    if '\\u' in b or '0x' in b:
                        c_match = re.search(r'#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{4}|[0-9a-fA-F]{3})\b', b)
                        colors.append(c_match.group(0) if c_match else None)
            if not colors:
                colors = re.findall(r'#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{4}|[0-9a-fA-F]{3})\b', raw_str)
                
            theme_colors = get_theme_glyph_colors()
            
            pm = QPixmap(size * 2, size * 2)
            pm.fill(Qt.transparent)
            p = QPainter(pm)
            p.setRenderHint(QPainter.Antialiasing)
            p.setRenderHint(QPainter.TextAntialiasing)
            p.setRenderHint(QPainter.SmoothPixmapTransform)
            
            rendered_any = False
            for idx, code in enumerate(codes[:2]):
                meta = glyphs_data.get(f"{code:04x}") or glyphs_data.get(f"{code:04X}") or glyphs_data.get(code) or glyphs_data.get(str(code)) or {}
                paths = meta.get('paths', [])
                c_hex = colors[idx] if (idx < len(colors) and colors[idx]) else (theme_colors[idx] if idx < len(theme_colors) else "#ffffff")
                
                if paths and QtSvg:
                    paths_xml = ''.join([f'<path fill="{c_hex}" d="{d}"/>' for d in paths])
                    svg_xml = f'<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">{paths_xml}</svg>'
                    renderer = QtSvg.QSvgRenderer(svg_xml.encode('utf-8'))
                    if renderer.isValid():
                        renderer.render(p, QRectF(0, 0, size * 2, size * 2))
                        rendered_any = True
                else:
                    font_family = meta.get('font') or NILESOFT_FONT_FAMILY
                    font = QFont(font_family)
                    font.setPixelSize(int(size * 2 * 0.72))
                    p.setFont(font)
                    p.setPen(QColor(c_hex))
                    p.drawText(QRect(0, 0, size * 2, size * 2), Qt.AlignCenter, chr(code))
                    rendered_any = True
                    
            p.end()
            if rendered_any:
                res = pm.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                _asset_pixmap_cache[cache_key] = res
                return res
        except Exception:
            pass

    # Check image path
    path = str(val).strip('\'"[] ')
    m_res = re.search(r"image\.res\s*\(\s*['\"]([^'\"]+)['\"]\s*\)", val, re.IGNORECASE)
    if m_res: path = m_res.group(1)
    if '@app.dir' in path:
        if getattr(sys, 'frozen', False):
            base = os.path.dirname(os.path.abspath(sys.executable))
        else:
            base = os.path.dirname(os.path.abspath(__file__))
        root = os.path.dirname(base) if os.path.basename(base).lower() == 'launcher' else base
        path = path.replace('@app.dir', root)

    if os.path.exists(path):
        try:
            if path.lower().endswith('.svg') and QtSvg:
                renderer = QtSvg.QSvgRenderer(path)
                if renderer.isValid():
                    pm = QPixmap(size * 2, size * 2); pm.fill(Qt.transparent)
                    p = QPainter(pm); p.setRenderHint(QPainter.Antialiasing); renderer.render(p); p.end()
                    res = pm.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    _asset_pixmap_cache[cache_key] = res
                    return res
            pm = QPixmap(path)
            if not pm.isNull():
                res = pm.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                _asset_pixmap_cache[cache_key] = res
                return res
        except Exception:
            pass

    return None

def get_combo_item_visuals(text, context_key=""):
    """
    Returns (glyph_or_pixmap_or_mode, badge_bg_hex, icon_color_hex) for a given combo item text and context.
    """
    t_clean = str(text).strip().lower()
    k_clean = str(context_key).strip().lower()
    
    # 1. Separator (Special Custom Drawing)
    if "sep" in k_clean or t_clean in ("none", "before", "after", "both"):
        if t_clean == "before": return ("sep_before", "#2a2a2a", "#e78284")
        elif t_clean == "after": return ("sep_after", "#2a2a2a", "#e78284")
        elif t_clean == "both": return ("sep_both", "#2a2a2a", "#e78284")
        elif t_clean in ("none", "", "(none)"): return ("\uE711", "#2a2a2a", "#888888")

    # 2. Menu / Move To
    if "menu" in k_clean or "moveto" in k_clean or t_clean in ("main", "options"):
        if t_clean in ("none", "", "(none)"): return ("\uE711", "#2a2a2a", "#888888")
        if t_clean == "main": return ("\uE80F", "#2a2a2a", "#e78284")
        menus = get_nss_menus_dict()
        if t_clean in menus and menus[t_clean].get('icon'):
            icon_val = menus[t_clean]['icon']
            pix = render_nss_asset_pixmap(icon_val, size=14)
            if pix:
                return (pix, "#2a2a2a", "#ffffff")
        if t_clean == "options": return ("\uE713", "#2a2a2a", "#e78284")
        return ("\uE8D2", "#2a2a2a", "#b0b0b8")

    # 3. Position
    if "pos" in k_clean or t_clean in ("top", "bottom", "middle", "1", "2", "3", "4", "5", "0", "-1", "default", "(default)"):
        if t_clean in ("", "default", "(default)", "none", "auto"):
            return ("\uE71D", "#2a2a2a", "#8caaee")
        elif t_clean == "top":
            return ("\uE74A", "#2a2a2a", "#e78284")
        elif t_clean == "bottom":
            return ("\uE74B", "#2a2a2a", "#e78284")
        elif t_clean == "middle":
            return ("\uE8CB", "#2a2a2a", "#e5c890")
        elif t_clean in ("1", "2", "3", "4", "5", "0"):
            return (f"num_{t_clean}", "#2a2a2a", "#a6d189")
        elif t_clean == "-1":
            return ("\uE74B", "#2a2a2a", "#e78284")

    # 4. Theme Mode
    if "name" in k_clean or t_clean in ("auto", "classic", "white", "black", "modern"):
        if t_clean == "auto": return ("\uE790", "#2a2a2a", "#e78284")
        elif t_clean == "classic": return ("\uE777", "#2a2a2a", "#e2b340")
        elif t_clean == "white": return ("\uE706", "#2a2a2a", "#facc15")
        elif t_clean == "black": return ("\uE708", "#2a2a2a", "#c084fc")
        elif t_clean == "modern": return ("\uE74C", "#2a2a2a", "#e78284")

    # 5. View
    if "view" in k_clean or t_clean in ("compact", "small", "medium", "large", "wide"):
        if t_clean == "compact": return ("\uE8A1", "#2a2a2a", "#b0b0b8")
        elif t_clean == "small": return ("\uE8A0", "#2a2a2a", "#b0b0b8")
        elif t_clean == "medium": return ("\uE737", "#2a2a2a", "#e78284")
        elif t_clean == "large": return ("\uE736", "#2a2a2a", "#b0b0b8")
        elif t_clean == "wide": return ("\uE8A2", "#2a2a2a", "#b0b0b8")

    # 6. Background Effect
    if "effect" in k_clean or t_clean in ("disabled", "transparent", "blur", "acrylic", "noise"):
        if t_clean == "disabled": return ("\uE711", "#2a2a2a", "#888888")
        elif t_clean == "transparent": return ("\uE727", "#2a2a2a", "#e78284")
        elif t_clean == "blur": return ("\uE7F4", "#2a2a2a", "#e78284")
        elif t_clean == "acrylic": return ("\uE790", "#2a2a2a", "#e78284")
        elif t_clean == "noise": return ("\uE7B5", "#2a2a2a", "#e78284")

    # 7. Dark Mode
    if "dark" in k_clean or t_clean in ("true", "false", "default"):
        if t_clean == "true": return ("\uE708", "#2a2a2a", "#c084fc")
        elif t_clean == "false": return ("\uE706", "#2a2a2a", "#facc15")
        elif t_clean == "default": return ("\uE790", "#2a2a2a", "#e78284")

    # 8. Argument Presets & Action Types
    if "arg" in k_clean or "action" in k_clean:
        if any(ch in str(text) for ch in ("📁", "📂", "📄")): return ("\uE838", "#2a2a2a", "#8caaee")
        if "⚡" in str(text) or "powershell" in t_clean or "ps:" in t_clean: return ("\uE945", "#2a2a2a", "#ef9f76")
        if "💻" in str(text) or "cmd" in t_clean: return ("\uE756", "#2a2a2a", "#8caaee")
        if "🐍" in str(text) or "python" in t_clean: return ("\uE230", "#2a2a2a", "#a6d189")
        if "🛡️" in str(text) or "admin" in t_clean: return ("\uEA18", "#2a2a2a", "#8caaee")
        if "📋" in str(text) or "copy" in t_clean or "clipboard" in t_clean: return ("\uE16F", "#2a2a2a", "#ca9ee6")
        if "🔄" in str(text) or "restart" in t_clean: return ("\uE149", "#2a2a2a", "#e5c890")
        if "👁️" in str(text) or "hidden" in t_clean: return ("\uE7B3", "#2a2a2a", "#ea999c")
        if "🚀" in str(text) or "launch" in t_clean: return ("\uE710", "#2a2a2a", "#ea999c")
        if any(ch in str(text) for ch in ("🏷️", "📑", "🔢")): return ("\uE8EC", "#2a2a2a", "#8caaee")
        if t_clean.startswith("+") or "insert" in t_clean: return ("\uE710", "#2a2a2a", "#ea999c")
        return ("\uE756", "#2a2a2a", "#838ba7")

    if t_clean == "shift": return ("\uE765", "#2a2a2a", "#e78284")
    if t_clean == "control": return ("\uE765", "#2a2a2a", "#e78284")
    if t_clean in ("left mouse", "mouse"): return ("\uE962", "#2a2a2a", "#e78284")

    return ("\uE8D2", "#2a2a2a", "#b0b0b8")

def draw_badge_content(painter, badge_rect, glyph_or_pix, icon_color):
    if isinstance(glyph_or_pix, QPixmap):
        pw = glyph_or_pix.width()
        ph = glyph_or_pix.height()
        px = badge_rect.x() + (badge_rect.width() - pw) / 2
        py = badge_rect.y() + (badge_rect.height() - ph) / 2
        painter.drawPixmap(int(px), int(py), glyph_or_pix)
    elif str(glyph_or_pix).startswith("num_"):
        digit_str = str(glyph_or_pix)[4:]
        num_font = QFont("Segoe UI Variable Display", 9, QFont.Bold)
        painter.setFont(num_font)
        painter.setPen(QColor(icon_color))
        painter.drawText(badge_rect, Qt.AlignCenter, digit_str)
    elif glyph_or_pix == "sep_before":
        painter.setPen(QPen(QColor("#e78284"), 2.0, Qt.SolidLine, Qt.RoundCap))
        painter.drawLine(int(badge_rect.left() + 4), int(badge_rect.top() + 5), int(badge_rect.right() - 4), int(badge_rect.top() + 5))
        painter.setPen(Qt.NoPen); painter.setBrush(QColor("#777777"))
        painter.drawRoundedRect(QRectF(badge_rect.left() + 6, badge_rect.top() + 11, badge_rect.width() - 12, 5), 2.5, 2.5)
    elif glyph_or_pix == "sep_after":
        painter.setPen(QPen(QColor("#e78284"), 2.0, Qt.SolidLine, Qt.RoundCap))
        painter.drawLine(int(badge_rect.left() + 4), int(badge_rect.bottom() - 5), int(badge_rect.right() - 4), int(badge_rect.bottom() - 5))
        painter.setPen(Qt.NoPen); painter.setBrush(QColor("#777777"))
        painter.drawRoundedRect(QRectF(badge_rect.left() + 6, badge_rect.top() + 6, badge_rect.width() - 12, 5), 2.5, 2.5)
    elif glyph_or_pix == "sep_both":
        painter.setPen(QPen(QColor("#e78284"), 2.0, Qt.SolidLine, Qt.RoundCap))
        painter.drawLine(int(badge_rect.left() + 4), int(badge_rect.top() + 4), int(badge_rect.right() - 4), int(badge_rect.top() + 4))
        painter.drawLine(int(badge_rect.left() + 4), int(badge_rect.bottom() - 4), int(badge_rect.right() - 4), int(badge_rect.bottom() - 4))
        painter.setPen(Qt.NoPen); painter.setBrush(QColor("#777777"))
        painter.drawRoundedRect(QRectF(badge_rect.left() + 6, badge_rect.top() + 9, badge_rect.width() - 12, 4), 2, 2)
    else:
        glyph_font = QFont("Segoe MDL2 Assets", 10, QFont.DemiBold)
        painter.setFont(glyph_font)
        painter.setPen(QColor(icon_color))
        painter.drawText(badge_rect, Qt.AlignCenter, str(glyph_or_pix))


class ModernComboDelegate(QStyledItemDelegate):
    def __init__(self, combo, parent=None):
        super().__init__(parent)
        self.combo = combo

    def sizeHint(self, option, index):
        return QSize(option.rect.width(), 34)

    def paint(self, painter, option, index):
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.TextAntialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        rect = option.rect.adjusted(3, 2, -3, -2)
        text = index.data(Qt.DisplayRole)
        display_text = text if text != "" else "(Default)"
        if "arg" in str(getattr(self.combo, "context_key", "")).lower():
            for emo in ("📁", "📂", "📄", "🏷️", "📑", "🔢", "💻", "⚡", "🐍", "🛡️", "🖥️", "📋", "🔄", "👁️", "🚀"):
                if display_text.startswith(emo):
                    display_text = display_text[len(emo):].strip()
                    break
        
        is_selected = bool(option.state & QStyle.State_Selected)
        is_hovered = bool(option.state & QStyle.State_MouseOver)

        path = QPainterPath()
        path.addRoundedRect(QRectF(rect), 8, 8)

        if is_selected or is_hovered:
            grad = QLinearGradient(QRectF(rect).topLeft(), QRectF(rect).bottomRight())
            grad.setColorAt(0.0, QColor(231, 130, 132, 58))
            grad.setColorAt(0.45, QColor(202, 158, 230, 40))
            grad.setColorAt(1.0, QColor(140, 170, 238, 30))
            painter.fillPath(path, grad)
            painter.setPen(QPen(QColor(255, 255, 255, 85), 1.5))
            painter.drawPath(path)
        else:
            painter.fillPath(path, QColor(255, 255, 255, 6))
            painter.setPen(QPen(QColor(255, 255, 255, 18), 1.0))
            painter.drawPath(path)

        # Draw circular icon badge
        context_key = getattr(self.combo, "context_key", "")
        glyph_or_pix, badge_bg, icon_color = get_combo_item_visuals(text, context_key)

        badge_size = 20
        badge_x = rect.left() + 6
        badge_y = rect.top() + (rect.height() - badge_size) // 2
        badge_rect = QRectF(badge_x, badge_y, badge_size, badge_size)

        badge_path = QPainterPath()
        badge_path.addEllipse(badge_rect)
        painter.fillPath(badge_path, QColor(badge_bg))
        painter.setPen(QPen(QColor(255, 255, 255, 45) if (is_selected or is_hovered) else QColor("#2a2d3e"), 1.0))
        painter.drawPath(badge_path)

        draw_badge_content(painter, badge_rect, glyph_or_pix, icon_color)

        # Draw item text
        text_font = QFont("Segoe UI Variable Display", 10)
        text_font.setWeight(QFont.Medium if not (is_selected or is_hovered) else QFont.DemiBold)
        painter.setFont(text_font)

        text_x = badge_x + badge_size + 8
        text_w = rect.right() - text_x - 6
        text_rect = QRectF(text_x, rect.top(), text_w, rect.height())

        if text == "":
            painter.setPen(QColor("#777777"))
        elif is_selected or is_hovered:
            painter.setPen(QColor("#ffffff"))
        else:
            painter.setPen(QColor("#d0d0d0"))

        painter.drawText(text_rect, Qt.AlignLeft | Qt.AlignVCenter, display_text)
        painter.restore()


class ModernComboBox(QComboBox):
    def __init__(self, parent=None, context_key=""):
        super().__init__(parent)
        self.context_key = context_key
        self.setFocusPolicy(Qt.StrongFocus)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(32)
        self.setAttribute(Qt.WA_Hover, True)
        self.setMouseTracking(True)
        self._is_popup_open = False

        list_view = QListView(self)
        list_view.setObjectName("modernComboListView")
        list_view.setSelectionMode(QListView.SingleSelection)
        list_view.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        list_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        list_view.setAutoScroll(False)
        list_view.setMouseTracking(True)
        list_view.viewport().setAttribute(Qt.WA_Hover)
        
        self.setView(list_view)
        self.setItemDelegate(ModernComboDelegate(self, self))

        popup = self.view().window()
        popup.setAttribute(Qt.WA_TranslucentBackground, True)
        popup.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint)

        self.setStyleSheet("""
            QComboBoxPrivateContainer {
                background: transparent;
                border: none;
            }
            QComboBox {
                background: transparent;
                border: none;
                padding-left: 34px;
                padding-right: 26px;
                color: #ffffff;
                font-family: 'Segoe UI Variable Display', 'Segoe UI';
                font-size: 12px;
                font-weight: 500;
            }
            QComboBox:hover, QComboBox:focus {
                background: transparent;
                border: none;
            }
            QComboBox::drop-down {
                border: none;
                width: 24px;
            }
            QComboBox::down-arrow {
                image: none;
                border: none;
            }
            QComboBox QAbstractItemView {
                background-color: #121212;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 12px;
                padding: 4px 4px;
                outline: none;
                selection-background-color: transparent;
            }
            QComboBox QScrollBar:vertical {
                border: none;
                background: transparent;
                width: 6px;
                margin: 4px 2px 4px 0px;
                border-radius: 3px;
            }
            QComboBox QScrollBar::handle:vertical {
                background: rgba(255, 255, 255, 0.2);
                min-height: 20px;
                border-radius: 3px;
            }
            QComboBox QScrollBar::handle:vertical:hover {
                background: #e78284;
            }
            QComboBox QScrollBar::add-line:vertical,
            QComboBox QScrollBar::sub-line:vertical {
                height: 0px;
                border: none;
                background: transparent;
            }
            QComboBox QScrollBar::add-page:vertical,
            QComboBox QScrollBar::sub-page:vertical {
                background: transparent;
            }
        """)

    def enterEvent(self, event):
        self._is_hovered = True
        super().enterEvent(event)
        self.update()

    def leaveEvent(self, event):
        self._is_hovered = False
        super().leaveEvent(event)
        self.update()

    def wheelEvent(self, e):
        e.ignore()

    def showPopup(self):
        popup = self.view().window()
        popup.setAttribute(Qt.WA_TranslucentBackground, True)
        popup.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint)
        self._is_popup_open = True
        min_w = getattr(self, "popup_min_width", 0)
        if min_w > 0:
            popup.setMinimumWidth(min_w)
            self.view().setMinimumWidth(min_w)
        self.update()
        super().showPopup()
        if min_w > 0 and popup.width() < min_w:
            popup.resize(min_w, popup.height())

    def hidePopup(self):
        self._is_popup_open = False
        self.update()
        super().hidePopup()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.TextAntialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        rect = QRectF(self.rect()).adjusted(1.0, 1.0, -1.0, -1.0)
        path = QPainterPath()
        path.addRoundedRect(rect, 10.0, 10.0)

        is_hovered = getattr(self, '_is_hovered', False) or self.underMouse()
        is_active = is_hovered or self._is_popup_open

        if is_active:
            grad = QLinearGradient(rect.topLeft(), rect.bottomRight())
            grad.setColorAt(0.0, QColor(231, 130, 132, 58))
            grad.setColorAt(0.45, QColor(202, 158, 230, 40))
            grad.setColorAt(1.0, QColor(140, 170, 238, 30))
            painter.fillPath(path, grad)
            painter.setPen(QPen(QColor(255, 255, 255, 85), 1.5))
            painter.drawPath(path)
        else:
            painter.fillPath(path, QColor(255, 255, 255, 8))
            painter.setPen(QPen(QColor(255, 255, 255, 22), 1.0))
            painter.drawPath(path)

        # Draw left circular badge
        current_text = self.currentText()
        glyph_or_pix, badge_bg, icon_color = get_combo_item_visuals(current_text, self.context_key)

        badge_size = 20
        badge_x = 7
        badge_y = (self.height() - badge_size) // 2
        badge_rect = QRectF(badge_x, badge_y, badge_size, badge_size)

        badge_path = QPainterPath()
        badge_path.addEllipse(badge_rect)
        painter.fillPath(badge_path, QColor(badge_bg))
        painter.setPen(QPen(QColor(255, 255, 255, 45) if is_active else QColor("#383838"), 1.0))
        painter.drawPath(badge_path)

        draw_badge_content(painter, badge_rect, glyph_or_pix, icon_color)

        # Draw item text
        text_font = QFont("Segoe UI Variable Display", 10)
        text_font.setWeight(QFont.DemiBold if is_active else QFont.Medium)
        painter.setFont(text_font)
        text_rect = QRectF(34, 0, self.width() - 58, self.height())
        if not current_text:
            painter.setPen(QColor("#ffffff") if is_active else QColor("#777777"))
            painter.drawText(text_rect, Qt.AlignLeft | Qt.AlignVCenter, "(Default)")
        else:
            painter.setPen(QColor("#ffffff") if is_active else QColor("#d1d5db"))
            painter.drawText(text_rect, Qt.AlignLeft | Qt.AlignVCenter, current_text)

        # Draw right chevron arrow
        chevron = "\uE70E" if self._is_popup_open else "\uE70D"
        ch_font = QFont("Segoe MDL2 Assets", 8)
        painter.setFont(ch_font)
        painter.setPen(QColor("#ffffff") if is_active else QColor("#888888"))
        ch_rect = QRectF(self.width() - 22, (self.height() - 18) // 2, 18, 18)
        painter.drawText(ch_rect, Qt.AlignCenter, chevron)

        painter.end()


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


class PillTabButton(QPushButton):
    """Segmented pill tab button with crisp anti-aliased vector rendering."""
    def __init__(self, text="", icon_code=None, parent=None, height=30, icon_size=16):
        super().__init__(text, parent)
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self._height = height
        self.setFixedHeight(self._height)
        self._icon_code = icon_code
        self._icon_size = icon_size
        self.setFont(QFont('Segoe UI Variable Display', 10, QFont.Bold))
        self.setAttribute(Qt.WA_Hover, True)
        self.setStyleSheet('background: transparent; border: none; outline: none;')
        
    def sizeHint(self):
        fm = self.fontMetrics()
        has_icon = bool(self._icon_code or not self.icon().isNull())
        isize = getattr(self, '_icon_size', 16)
        w = fm.horizontalAdvance(self.text().strip()) + (isize + 10 if has_icon else 0) + 28
        return QSize(max(w, 75), self._height)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        
        rect = QRectF(self.rect()).adjusted(1.0, 1.0, -1.0, -1.0)
        path = QPainterPath()
        r = rect.height() / 2.0
        path.addRoundedRect(rect, r, r)
        
        is_chk = self.isChecked()
        is_hov = self.underMouse()
        
        if is_chk:
            grad = QLinearGradient(rect.topLeft(), rect.bottomRight())
            grad.setColorAt(0.0, QColor(231, 130, 132, 58))
            grad.setColorAt(0.45, QColor(202, 158, 230, 40))
            grad.setColorAt(1.0, QColor(140, 170, 238, 30))
            p.fillPath(path, grad)
            
            # Crisp, thick, vector anti-aliased border (1.5px)
            p.setPen(QPen(QColor(255, 255, 255, 85), 1.5))
            p.drawPath(path)
            text_color = QColor('#ffffff')
        elif is_hov:
            p.fillPath(path, QColor(255, 255, 255, 14))
            p.setPen(QPen(QColor(255, 255, 255, 38), 1.2))
            p.drawPath(path)
            text_color = QColor('#c6d0f5')
        else:
            text_color = QColor('#8c92a4')
            
        fm = self.fontMetrics()
        txt = self.text().strip()
        txt_w = fm.horizontalAdvance(txt)
        
        icon = self.icon()
        isize = getattr(self, '_icon_size', 16)
        if not icon.isNull():
            icon_pix = icon.pixmap(isize, isize)
            total_w = isize + 8 + txt_w
            start_x = (self.width() - total_w) / 2.0
            p.drawPixmap(int(start_x), int((self.height() - isize) / 2.0), icon_pix)
            p.setFont(self.font())
            p.setPen(text_color)
            p.drawText(int(start_x + isize + 8), int((self.height() + fm.ascent() - fm.descent()) / 2.0), txt)
        elif self._icon_code:
            icon_pix = get_mdl2_icon(self._icon_code, isize, text_color.name()).pixmap(isize, isize)
            total_w = isize + 8 + txt_w
            start_x = (self.width() - total_w) / 2.0
            p.drawPixmap(int(start_x), int((self.height() - isize) / 2.0), icon_pix)
            p.setFont(self.font())
            p.setPen(text_color)
            p.drawText(int(start_x + isize + 8), int((self.height() + fm.ascent() - fm.descent()) / 2.0), txt)
        else:
            p.setFont(self.font())
            p.setPen(text_color)
            p.drawText(self.rect(), Qt.AlignCenter, txt)

