import os
import sys
import json
import struct
import shutil
import ctypes
import winreg
import subprocess
import fnmatch
import re
import threading
from collections import deque
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import BytesIO

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QFrame,
    QPushButton, QSizePolicy, QLayout, QApplication, QButtonGroup
)
from PyQt5.QtGui import QPixmap, QIcon, QCursor, QColor, QFont, QPainter, QImage, QPainterPath, QPen
from PyQt5.QtCore import Qt, QSize, pyqtSignal, QRect, QPoint, QThread, QObject, QTimer

from github_client import github_api_get, cdn_get, get_latest_tree_sha
from plugin_registry import file_matches_git_sha, git_blob_sha, atomic_json_write
from utils import FlowLayout, PillTabButton


CURSOR_ROLES = [
    ("Arrow", "Normal Select", "arrow.cur", (0.0, 0.0)),
    ("Help", "Help Select", "help.cur", (0.0, 0.0)),
    ("AppStarting", "Working in Background", "working.cur", (0.0, 0.0)),
    ("Wait", "Busy", "busy.cur", (0.5, 0.5)),
    ("Crosshair", "Precision Select", "cross.cur", (0.5, 0.5)),
    ("IBeam", "Text Select", "ibeam.cur", (0.5, 0.5)),
    ("NWPen", "Handwriting", "handwriting.cur", (0.0, 0.0)),
    ("No", "Unavailable", "unavail.cur", (0.5, 0.5)),
    ("SizeNS", "Vertical Resize", "vert.cur", (0.5, 0.5)),
    ("SizeWE", "Horizontal Resize", "horz.cur", (0.5, 0.5)),
    ("SizeNWSE", "Diagonal Resize 1", "dgn1.cur", (0.5, 0.5)),
    ("SizeNESW", "Diagonal Resize 2", "dgn2.cur", (0.5, 0.5)),
    ("SizeAll", "Move", "move.cur", (0.5, 0.5)),
    ("UpArrow", "Alternate Select", "alternate.cur", (0.5, 0.0)),
    ("Hand", "Link Select", "link.cur", (0.15, 0.0)),
    ("Pin", "Location Select", "pin.cur", (0.5, 1.0)),
    ("Person", "Person Select", "person.cur", (0.5, 0.5)),
]

ROLE_ALIASES = {
    'Arrow': ['arrow.cur', 'arrow.ani', '*arrow*.cur', '*arrow*.ani', '*normal*.cur', '*normal*.ani', '*pointer*.cur', '*pointer*.ani', '*default*.cur', '*default*.ani', '01*.ani', '01*.cur', 'wii-pointer*.cur'],
    'Help': ['help.cur', 'help.ani', '*help*.cur', '*help*.ani', '02*.ani', '02*.cur', '*sakura*.ani', '05sakura.ani', 'wii-help*.cur'],
    'AppStarting': ['*working*.ani', '*working*.cur', '*loading*.ani', '*loading*.cur', '*appstarting*.ani', '*appstarting*.cur', '03*.ani', '03*.cur', '*work*.ani', '*work*.cur', 'wii-loading-cd*.ani', 'wii-loading-ring*.ani'],
    'Wait': ['*busy*.ani', '*busy*.cur', '*busy *.ani', '*wait*.ani', '*wait*.cur', '04*.ani', '04*.cur', '06naruto.ani', 'wii-loading-cd*.cur'],
    'Crosshair': ['*cross*.cur', '*cross*.ani', '*precision*.cur', '*precision*.ani', '*crosshair*.cur', '*crosshair*.ani', '05*.ani', '05*.cur', '07naruto.ani'],
    'IBeam': ['*text*.cur', '*text*.ani', '*ibeam*.cur', '*ibeam*.ani', '*beam*.cur', '*beam*.ani', '06*.ani', '06*.cur'],
    'NWPen': ['*pen*.cur', '*pencil*.cur', '*handwriting*.cur', '*handwriting*.ani', '*draft*.cur', '07*.ani', '07*.cur', '*kakashi*.ani', '08kakashi.ani', 'wii-open*.cur'],
    'No': ['*unavailable*.cur', '*unavailable*.ani', '*unavail*.cur', '*unavail*.ani', '*unavailible*.cur', '*unavailible*.ani', '*unavaliable*.cur', '*unavaliable*.ani', '*notallowed*.cur', '*notallowed*.ani', '*no*.cur', '*no*.ani', '*dnd*.cur', '*nodrop*.cur', '*cancel*.cur', '08*.ani', '08*.cur', '*sasuke*.ani', '09sasuke.ani'],
    'SizeNS': ['*nsresize*.cur', '*nsresize*.ani', '*vert*.cur', '*vert*.ani', '*vertical*.cur', '*vertical*.ani', '*vertical resize*.cur', '*size_ns*.cur', '*size_ns*.ani', '*sizens*.cur', '*sizens*.ani', '*v-resize*.cur', '*v-resize*.ani', '09*.ani', '09*.cur', '10naruto.ani', '*sizes*.ani', '*sizes*.cur'],
    'SizeWE': ['*ewresize*.cur', '*ewresize*.ani', '*horz*.cur', '*horz*.ani', '*horizontal*.cur', '*horizontal*.ani', '*horizonta*.cur', '*horizonta*.ani', '*horizontal resize*.cur', '*size_we*.cur', '*size_we*.ani', '*sizewe*.cur', '*sizewe*.ani', '*h-resize*.cur', '*h-resize*.ani', '10*.ani', '10*.cur', '*sizee*.ani', '*sizee*.cur'],
    'SizeNWSE': ['*nwresize*.cur', '*nwresize*.ani', '*diagonal*1*.ani', '*diagonal*1*.cur', '*diagonal*resize*1*.cur', '*diagonal resize.cur', '*diagonal*resize*.cur', '*dgn1*.cur', '*dgn1*.ani', '*sizenwse*.cur', '*sizenwse*.ani', '*uperleft*.cur', '*upper left*.cur', '*sizese*.ani', '*sizese*.cur'],
    'SizeNESW': ['*neresize*.cur', '*neresize*.ani', '*diagonal*2*.ani', '*diagonal*2*.cur', '*diagonal*resize*2*.cur', '*diagonal resize2.cur', '*dgn2*.cur', '*dgn2*.ani', '*sizenesw*.cur', '*sizenesw*.ani', '*uperright*.cur', '*upper right*.cur', '*upper*right*.cur', '*sizesw*.ani', '*sizesw*.cur'],
    'SizeAll': ['*move*.cur', '*move*.ani', '*sizeall*.cur', '*sizeall*.ani', '*all*.cur', '*all*.ani', 'wii-move*.cur'],
    'UpArrow': ['*alternate*.cur', '*alternate*.ani', '*uparrow*.cur', '*uparrow*.ani', '*up-arrow*.cur', '*up-arrow*.ani', '*alt*.cur', '*alt*.ani', '*aletetnativa*.cur', '*aleternativa*.cur', '*seleccion aleternativa*.cur', '*sb_up_arrow*.cur'],
    'Hand': ['*link*.cur', '*link*.ani', '*hand*.cur', '*hand*.ani', '*grab*.cur', '*grab*.ani', '*open*.cur', '*closehand*.cur', '*pointing*.cur', '*pointing*.ani', 'wii-grab*.cur'],
    'Pin': ['*pin*.cur', '*pin*.ani', '*location*.cur', '*location*.ani'],
    'Person': ['*person*.cur', '*person*.ani', '*user*.cur', '*user*.ani', '*account*.cur', '*account*.ani'],
}

CURSOR_REPO = "iMAboud/iMA-Menu-cursors"
CURSOR_BRANCH = "main"

if getattr(sys, 'frozen', False):
    APP_ROOT = os.path.dirname(os.path.abspath(sys.executable))
else:
    APP_ROOT = os.path.dirname(os.path.abspath(__file__))

CACHE_DIR = os.path.join(APP_ROOT, "cache", "cursors")
PREVIEWS_CACHE_DIR = os.path.join(CACHE_DIR, "previews")
CATALOG_CACHE_FILE = os.path.join(CACHE_DIR, "catalog.json")
TREE_SHA_CACHE_FILE = os.path.join(CACHE_DIR, "tree_sha.txt")
FAVORITES_FILE = os.path.join(CACHE_DIR, "favorites.json")

os.makedirs(PREVIEWS_CACHE_DIR, exist_ok=True)

def create_star_pixmap(size: int = 20, filled: bool = False, color: str = "#FFB800", outline_color: str = "#FFFFFF", outline_width: float = 1.5) -> QPixmap:
    """Renders a pure vector 5-pointed star pixmap with mathematical precision, immune to missing OS fonts."""
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.Antialiasing)

    import math
    cx = size / 2.0
    cy = size / 2.0
    outer_r = (size / 2.0) - 2.0
    inner_r = outer_r * 0.40

    path = QPainterPath()
    for i in range(10):
        angle = -math.pi / 2.0 + (i * math.pi / 5.0)
        r = outer_r if i % 2 == 0 else inner_r
        x = cx + r * math.cos(angle)
        y = cy + r * math.sin(angle)
        if i == 0:
            path.moveTo(x, y)
        else:
            path.lineTo(x, y)
    path.closeSubpath()

    if filled:
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(color))
        painter.drawPath(path)
    else:
        painter.setPen(QPen(QColor(outline_color), outline_width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(path)
    painter.end()
    return pix

def get_star_icon(filled: bool = False, color: str = "#FFB800", outline_color: str = "#FFFFFF", size: int = 20) -> QIcon:
    """Returns a QIcon containing a vector 5-pointed star."""
    pix = create_star_pixmap(size=size, filled=filled, color=color, outline_color=outline_color)
    return QIcon(pix)


_EMBEDDED_PREVIEWS = {}

def _load_embedded_previews():
    global _EMBEDDED_PREVIEWS
    if _EMBEDDED_PREVIEWS:
        return _EMBEDDED_PREVIEWS
    for path in [
        os.path.join(APP_ROOT, "cursors_previews.json"),
        os.path.join(os.path.dirname(__file__), "cursors_previews.json"),
        getattr(sys, '_MEIPASS', '') and os.path.join(getattr(sys, '_MEIPASS', ''), "cursors_previews.json")
    ]:
        if path and os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if data and isinstance(data, dict):
                    _EMBEDDED_PREVIEWS = data
                    break
            except Exception:
                pass
    return _EMBEDDED_PREVIEWS

_theme_qimage_cache = {}

def get_theme_preview_image(theme_name: str, role_name: str = "Arrow") -> QImage:
    """Returns pre-cached QImage for theme and role, checking memory cache, disk cache and embedded atlas."""
    cache_key = (theme_name, role_name)
    if cache_key in _theme_qimage_cache:
        return _theme_qimage_cache[cache_key]

    cache_img = os.path.join(PREVIEWS_CACHE_DIR, f"{theme_name}_{role_name}.png")
    if os.path.exists(cache_img):
        try:
            img = QImage(cache_img)
            if not img.isNull():
                if len(_theme_qimage_cache) < 600:
                    _theme_qimage_cache[cache_key] = img
                return img
        except Exception:
            pass

    if role_name == "Arrow":
        legacy_cache = os.path.join(PREVIEWS_CACHE_DIR, f"{theme_name}.png")
        if os.path.exists(legacy_cache):
            try:
                img = QImage(legacy_cache)
                if not img.isNull():
                    if len(_theme_qimage_cache) < 600:
                        _theme_qimage_cache[cache_key] = img
                    return img
            except Exception:
                pass

    atlas = _load_embedded_previews()
    th_data = atlas.get(theme_name)
    if not th_data:
        for k, v in atlas.items():
            if k.lower() == theme_name.lower():
                th_data = v
                break

    if th_data and role_name in th_data:
        try:
            import base64
            png_bytes = base64.b64decode(th_data[role_name])
            img = QImage.fromData(png_bytes)
            if not img.isNull():
                if len(_theme_qimage_cache) < 600:
                    _theme_qimage_cache[cache_key] = img
                try:
                    save_path = os.path.join(PREVIEWS_CACHE_DIR, f"{theme_name}_{role_name}.png")
                    img.save(save_path, "PNG")
                except Exception:
                    pass
                return img
        except Exception:
            pass

    return QImage()

def resolve_online_theme_roles(file_list: list, default_arrow: str = "") -> dict:
    """Resolves role -> rel_file for an online theme file list."""
    resolved = {}
    used_files = set()
    if default_arrow and default_arrow in file_list:
        resolved["Arrow"] = default_arrow
        used_files.add(default_arrow)

    for role in ["Arrow", "Help", "Wait", "Hand", "IBeam"]:
        if role in resolved:
            continue
        patterns = ROLE_ALIASES.get(role, [])
        for pat in patterns:
            matched = False
            for fn in file_list:
                if fn not in used_files and fnmatch.fnmatch(os.path.basename(fn).lower(), pat.lower()):
                    resolved[role] = fn
                    used_files.add(fn)
                    matched = True
                    break
            if matched:
                break
    return resolved





class CurGenerator:
    """Decodes .cur and .ani files to clean QImage frames."""

    @staticmethod
    def extract_ani_first_frame(data: bytes) -> bytes:
        if not (data.startswith(b'RIFF') and data[8:12] == b'ACON'):
            return None
        pos = 12
        while pos < len(data):
            chunk_id = data[pos:pos+4]
            if len(data) < pos + 8:
                break
            chunk_sz = struct.unpack('<I', data[pos+4:pos+8])[0]
            if chunk_id == b'LIST' and data[pos+8:pos+12] == b'fram':
                sub_pos = pos + 12
                while sub_pos < pos + 8 + chunk_sz:
                    if len(data) < sub_pos + 8:
                        break
                    f_id = data[sub_pos:sub_pos+4]
                    f_sz = struct.unpack('<I', data[sub_pos+4:sub_pos+8])[0]
                    if f_id == b'icon':
                        return data[sub_pos+8:sub_pos+8+f_sz]
                    sub_pos += 8 + f_sz + (f_sz % 2)
            pos += 8 + chunk_sz + (chunk_sz % 2)
        return None

    @staticmethod
    def extract_best_cursor_image_from_bytes(data: bytes) -> QImage:
        if not data:
            return QImage()

        if data.startswith(b'RIFF') and data[8:12] == b'ACON':
            ani_cur = CurGenerator.extract_ani_first_frame(data)
            if ani_cur:
                data = ani_cur

        if len(data) > 6 and struct.unpack('<H', data[0:2])[0] == 0 and struct.unpack('<H', data[2:4])[0] in (1, 2):
            count = struct.unpack('<H', data[4:6])[0]
            best_img = None
            best_w = 0
            for i in range(count):
                entry_off = 6 + (i * 16)
                if entry_off + 16 > len(data):
                    break
                bw = data[entry_off]
                actual_w = 256 if bw == 0 else bw
                res_sz, off = struct.unpack('<II', data[entry_off+8:entry_off+16])
                img_data = data[off:off+res_sz]

                if img_data.startswith(b'\x89PNG'):
                    sub_img = QImage.fromData(img_data)
                    if not sub_img.isNull() and sub_img.width() >= best_w:
                        best_img = sub_img
                        best_w = sub_img.width()
                elif len(img_data) >= 40:
                    try:
                        bih = img_data[:40]
                        biWidth, biHeight, biBitCount = struct.unpack('<iiH', bih[4:14])
                        target_w = biWidth
                        target_h = biHeight // 2
                        if target_w > 0 and target_h > 0:
                            if biBitCount == 32:
                                xor_len = target_w * target_h * 4
                                xor_data = img_data[40:40+xor_len]
                                and_stride = (target_w + 31) // 32 * 4
                                and_data = img_data[40+xor_len:40+xor_len + and_stride * target_h]
                                has_alpha = any(xor_data[k+3] > 0 for k in range(0, len(xor_data), 4))
                                
                                qimg = QImage(target_w, target_h, QImage.Format_ARGB32)
                                qimg.fill(0)
                                for y in range(target_h):
                                    row_y = target_h - 1 - y
                                    for x in range(target_w):
                                        x_idx = (row_y * target_w + x) * 4
                                        b, g, r, a = xor_data[x_idx:x_idx+4]
                                        if and_data:
                                            and_b_idx = row_y * and_stride + (x // 8)
                                            and_bit = (and_data[and_b_idx] >> (7 - (x % 8))) & 1 if and_b_idx < len(and_data) else 0
                                        else:
                                            and_bit = 0
                                        
                                        final_a = 0 if and_bit == 1 else (a if has_alpha else 255)
                                        val = (final_a << 24) | (r << 16) | (g << 8) | b
                                        qimg.setPixel(x, y, val)
                                
                                if target_w >= best_w:
                                    best_img = qimg
                                    best_w = target_w
                            else:
                                sub_img = QImage.fromData(img_data)
                                if not sub_img.isNull() and sub_img.width() >= best_w:
                                    best_img = sub_img
                                    best_w = sub_img.width()
                    except Exception:
                        pass

            if best_img and not best_img.isNull():
                return best_img

        img = QImage.fromData(data)
        if not img.isNull():
            return img

        return QImage()

    _image_cache = {}
    _pixmap_cache = {}

    @staticmethod
    def extract_best_cursor_image(file_path: str) -> QImage:
        if not file_path or not os.path.exists(file_path):
            return QImage()
        try:
            mtime = os.path.getmtime(file_path)
        except Exception:
            mtime = 0
        cache_key = (file_path, mtime)
        if cache_key in CurGenerator._image_cache:
            return CurGenerator._image_cache[cache_key]

        img = QImage()
        try:
            with open(file_path, 'rb') as f:
                data = f.read()
            img = CurGenerator.extract_best_cursor_image_from_bytes(data)
        except Exception:
            pass

        if img.isNull():
            try:
                IMAGE_CURSOR = 2
                LR_LOADFROMFILE = 0x00000010
                hcursor = ctypes.windll.user32.LoadImageW(0, os.path.abspath(file_path), IMAGE_CURSOR, 0, 0, LR_LOADFROMFILE)
                if hcursor:
                    try:
                        pix = QPixmap.fromWinHICON(hcursor)
                        if not pix.isNull():
                            img = pix.toImage()
                    finally:
                        ctypes.windll.user32.DestroyIcon(hcursor)
            except Exception:
                pass

        if len(CurGenerator._image_cache) > 256:
            CurGenerator._image_cache.clear()
        CurGenerator._image_cache[cache_key] = img
        return img

    @staticmethod
    def extract_pixmap_from_cur(file_path: str, target_size: int = 64) -> QPixmap:
        if not file_path:
            return QPixmap()
        try:
            mtime = os.path.getmtime(file_path)
        except Exception:
            mtime = 0
        cache_key = (file_path, mtime, target_size)
        if cache_key in CurGenerator._pixmap_cache:
            return CurGenerator._pixmap_cache[cache_key]

        img = CurGenerator.extract_best_cursor_image(file_path)
        if not img.isNull():
            scaled = img.scaled(target_size, target_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            pix = QPixmap.fromImage(scaled)
            if len(CurGenerator._pixmap_cache) > 256:
                CurGenerator._pixmap_cache.clear()
            CurGenerator._pixmap_cache[cache_key] = pix
            return pix
        return QPixmap()


@lru_cache(maxsize=128)
def find_effective_theme_dir(theme_dir: str) -> str:
    if not os.path.exists(theme_dir):
        return theme_dir
    files = os.listdir(theme_dir)
    has_cursors = any(f.lower().endswith(('.cur', '.ani', '.inf')) for f in files)
    if has_cursors:
        return theme_dir
    for root, dirs, fnames in os.walk(theme_dir):
        if any(f.lower().endswith(('.cur', '.ani', '.inf')) for f in fnames):
            return root
    return theme_dir


INF_POS_ROLES = [
    'Arrow',        # 0: %pointer%
    'Help',         # 1: %help%
    'AppStarting',  # 2: %work%
    'Wait',         # 3: %busy%
    'Crosshair',    # 4: %cross%
    'IBeam',        # 5: %text%
    'NWPen',        # 6: %hand% (pen/handwriting)
    'No',           # 7: %unavailiable%
    'SizeNS',       # 8: %vert%
    'SizeWE',       # 9: %horz%
    'SizeNWSE',     # 10: %dgn1%
    'SizeNESW',     # 11: %dgn2%
    'SizeAll',      # 12: %move%
    'UpArrow',      # 13: %alternate%
    'Hand',         # 14: %link% (pointing hand)
    'Pin',          # 15: %pin%
    'Person'        # 16: %person%
]

INF_KEY_MAP = {
    'arrow': 'Arrow',
    'pointer': 'Arrow',
    'normal': 'Arrow',
    'help': 'Help',
    'appstarting': 'AppStarting',
    'working': 'AppStarting',
    'work': 'AppStarting',
    'wait': 'Wait',
    'busy': 'Wait',
    'crosshair': 'Crosshair',
    'precision': 'Crosshair',
    'precisionhair': 'Crosshair',
    'cross': 'Crosshair',
    'ibeam': 'IBeam',
    'beam': 'IBeam',
    'text': 'IBeam',
    'nwpen': 'NWPen',
    'handwriting': 'NWPen',
    'pen': 'NWPen',
    'pencil': 'NWPen',
    'draft': 'NWPen',
    'no': 'No',
    'unavailable': 'No',
    'unavail': 'No',
    'unavailible': 'No',
    'notallowed': 'No',
    'sizens': 'SizeNS',
    'vert': 'SizeNS',
    'nsresize': 'SizeNS',
    'vertical': 'SizeNS',
    'sizewe': 'SizeWE',
    'horz': 'SizeWE',
    'ewresize': 'SizeWE',
    'horizontal': 'SizeWE',
    'sizenwse': 'SizeNWSE',
    'dgn1': 'SizeNWSE',
    'nwresize': 'SizeNWSE',
    'sizenesw': 'SizeNESW',
    'dgn2': 'SizeNESW',
    'neresize': 'SizeNESW',
    'sizeall': 'SizeAll',
    'move': 'SizeAll',
    'uparrow': 'UpArrow',
    'alternate': 'UpArrow',
    'alt': 'UpArrow',
    'hand': 'Hand',
    'link': 'Hand',
    'pin': 'Pin',
    'person': 'Person',
}

_theme_roles_cache = {}

def resolve_theme_directory_roles(theme_dir: str) -> tuple:
    if not os.path.exists(theme_dir):
        return (os.path.basename(theme_dir), {}, theme_dir)

    try:
        curr_mtime = os.path.getmtime(theme_dir)
    except Exception:
        curr_mtime = 0

    norm_dir = os.path.normpath(theme_dir).lower()
    if norm_dir in _theme_roles_cache:
        cached_mtime, cached_res = _theme_roles_cache[norm_dir]
        if cached_mtime == curr_mtime:
            return cached_res

    all_files = {}  # rel_path -> rel_path
    inf_files = []

    for root, dirs, fnames in os.walk(theme_dir):
        for f in fnames:
            fp = os.path.join(root, f)
            rel = os.path.relpath(fp, theme_dir)
            low = f.lower()
            if low.endswith(('.cur', '.ani')):
                all_files[f] = rel
                all_files[rel] = rel
            elif low.endswith('.inf'):
                inf_files.append(fp)

    resolved = {}
    display_name = os.path.basename(theme_dir)

    # 1. Parse INF files (positional scheme strings and key-value entries)
    for inf_p in inf_files:
        try:
            with open(inf_p, 'r', errors='ignore') as f:
                content = f.read()

            strings_vars = {}
            in_strings = False
            for line in content.splitlines():
                line = line.strip()
                if line.startswith('[') and line.endswith(']'):
                    in_strings = (line.lower() == '[strings]')
                    continue
                if in_strings and '=' in line and not line.startswith(';'):
                    k, v = line.split('=', 1)
                    k_str = k.strip().lower()
                    v_str = v.strip(' "\'\t')
                    strings_vars[k_str] = v_str
                    if k_str in ('scheme_name', 'schemename'):
                        display_name = v_str

            for line in content.splitlines():
                line = line.strip()
                if not line or line.startswith(';'):
                    continue

                # Check for CSV positional Schemes format
                if 'control panel\\cursors\\schemes' in line.lower() and line.count(',') >= 5:
                    parts = [p.strip(' "\'\t') for p in line.split(',')]
                    if len(parts) >= 5:
                        csv_items = parts[4:]
                        if len(csv_items) >= 13:
                            for idx, val in enumerate(csv_items):
                                if idx < len(INF_POS_ROLES):
                                    role = INF_POS_ROLES[idx]
                                    fn = os.path.basename(val.replace('\\\\', '/').replace('\\', '/'))
                                    fn_match = re.match(r'^%([^%]+)%$', fn)
                                    if fn_match:
                                        var_name = fn_match.group(1).lower()
                                        fn = strings_vars.get(var_name, fn)
                                    for test_k, test_rel in all_files.items():
                                        if test_k.lower() == fn.lower() or os.path.basename(test_rel).lower() == fn.lower():
                                            resolved[role] = test_rel
                                            break

                # Check for HKCU,"Control Panel\Cursors","<Key>",... format
                if 'control panel\\cursors' in line.lower() and line.count(',') >= 3:
                    parts = [p.strip(' "\'\t') for p in line.split(',')]
                    if len(parts) >= 5 and 'schemes' not in parts[1].lower():
                        k = parts[2].lower()
                        v = parts[4]
                        if k in ('(default)', ''):
                            display_name = v
                        else:
                            fn = os.path.basename(v.replace('\\\\', '/').replace('\\', '/'))
                            fn_match = re.match(r'^%([^%]+)%$', fn)
                            if fn_match:
                                var_name = fn_match.group(1).lower()
                                fn = strings_vars.get(var_name, fn)
                            norm_role = INF_KEY_MAP.get(k)
                            if norm_role:
                                for test_k, test_rel in all_files.items():
                                    if test_k.lower() == fn.lower() or os.path.basename(test_rel).lower() == fn.lower():
                                        resolved[norm_role] = test_rel
                                        break
        except Exception:
            pass

    # 2. Resolve scheme display name if wrapped in %VARIABLE%
    dn_match = re.match(r'^%([^%]+)%$', display_name)
    if dn_match:
        display_name = os.path.basename(theme_dir)

    # 3. Fallback matching with ROLE_ALIASES for unmapped roles
    used_files = set(resolved.values())
    for role, patterns in ROLE_ALIASES.items():
        if role in resolved and resolved[role]:
            continue
        for pat in patterns:
            matched = False
            for f_name, rel in all_files.items():
                if rel not in used_files and fnmatch.fnmatch(os.path.basename(f_name).lower(), pat.lower()):
                    resolved[role] = rel
                    used_files.add(rel)
                    matched = True
                    break
            if matched:
                break

    res = (display_name, resolved, theme_dir)
    _theme_roles_cache[norm_dir] = (curr_mtime, res)
    return res


class WindowsCursorManager:
    """Interacts with Windows Registry HKCU\\Control Panel\\Cursors and updates live cursors."""

    SPI_SETCURSORS     = 0x0057
    SPIF_UPDATEINIFILE = 0x0001
    SPIF_SENDCHANGE    = 0x0002
    SPIF_FLAGS         = 0
    WM_SETTINGCHANGE   = 0x001A
    HWND_BROADCAST     = 0xFFFF
    SMTO_ABORTIFHUNG   = 0x0002

    @classmethod
    def get_current_scheme_name(cls) -> str:
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Control Panel\Cursors") as key:
                val, _ = winreg.QueryValueEx(key, "")
                return val or "Windows Default"
        except Exception:
            return "Windows Default"

    @classmethod
    def is_theme_active(cls, theme_name: str, display_name: str, theme_dir: str, current_name: str = None, arrow_val: str = None) -> bool:
        if current_name is None:
            current_name = cls.get_current_scheme_name()
        if theme_name == "Windows Default":
            return current_name in ["Windows Default", "Windows Aero", "Windows Default (system scheme)", ""] or not current_name

        if current_name and (current_name.lower() == theme_name.lower() or current_name.lower() == display_name.lower()):
            return True

        if not theme_dir or not os.path.exists(theme_dir):
            return False

        if arrow_val is None:
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Control Panel\Cursors") as key:
                    arrow_val, _ = winreg.QueryValueEx(key, "Arrow")
            except Exception:
                arrow_val = ""

        if arrow_val:
            norm_arrow = os.path.normpath(arrow_val).lower()
            norm_theme = os.path.normpath(theme_dir).lower()
            if norm_theme in norm_arrow:
                return True
            eff_dir = find_effective_theme_dir(theme_dir)
            norm_eff = os.path.normpath(eff_dir).lower()
            if norm_eff in norm_arrow:
                return True

        return False

    @classmethod
    def _broadcast_change(cls):
        try:
            from ctypes import wintypes
            send_msg = ctypes.windll.user32.SendMessageTimeoutW
            send_msg.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM, wintypes.UINT, wintypes.UINT, ctypes.POINTER(wintypes.DWORD)]
            send_msg.restype = wintypes.LPARAM

            result = wintypes.DWORD()
            send_msg(
                cls.HWND_BROADCAST,
                cls.WM_SETTINGCHANGE,
                cls.SPI_SETCURSORS,
                0,
                cls.SMTO_ABORTIFHUNG,
                200,
                ctypes.byref(result)
            )
        except Exception:
            pass

    @classmethod
    def apply_cursor_theme(cls, theme_display_name: str, role_file_map: dict) -> bool:
        try:
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Control Panel\Cursors") as key:
                winreg.SetValueEx(key, "", 0, winreg.REG_SZ, theme_display_name)
                winreg.SetValueEx(key, "Scheme Source", 0, winreg.REG_DWORD, 2)
                for reg_key, _, _, _ in CURSOR_ROLES:
                    file_path = role_file_map.get(reg_key, "")
                    winreg.SetValueEx(key, reg_key, 0, winreg.REG_SZ, file_path)

            scheme_parts = [role_file_map.get(reg_key, "") for reg_key, _, _, _ in CURSOR_ROLES]
            scheme_str = ",".join(scheme_parts)
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Control Panel\Cursors\Schemes") as key:
                winreg.SetValueEx(key, theme_display_name, 0, winreg.REG_SZ, scheme_str)

            from ctypes import wintypes
            spi = ctypes.windll.user32.SystemParametersInfoW
            spi.argtypes = [wintypes.UINT, wintypes.UINT, wintypes.LPVOID, wintypes.UINT]
            spi.restype = wintypes.BOOL
            ret = spi(cls.SPI_SETCURSORS, 0, None, cls.SPIF_FLAGS)
            cls._broadcast_change()
            return bool(ret)
        except Exception as e:
            print(f"[WindowsCursorManager] Error applying cursor theme: {e}")
            return False

    @classmethod
    def restore_default_cursors(cls) -> bool:
        try:
            defaults = {}
            try:
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Control Panel\Cursors\Default") as hklm_key:
                    i = 0
                    while True:
                        try:
                            val_name, val_data, val_type = winreg.EnumValue(hklm_key, i)
                            defaults[val_name] = (val_data, val_type)
                            i += 1
                        except OSError:
                            break
            except Exception as e:
                print(f"[WindowsCursorManager] Could not read HKLM Cursors\\Default: {e}")

            if not defaults:
                defaults = {
                    "": ("Windows Default", winreg.REG_SZ),
                    "Scheme Source": (2, winreg.REG_DWORD),
                    "Arrow": (r"%SystemRoot%\cursors\aero_arrow.cur", winreg.REG_EXPAND_SZ),
                    "Help": (r"%SystemRoot%\cursors\aero_helpsel.cur", winreg.REG_EXPAND_SZ),
                    "AppStarting": (r"%SystemRoot%\cursors\aero_working.ani", winreg.REG_EXPAND_SZ),
                    "Wait": (r"%SystemRoot%\cursors\aero_busy.ani", winreg.REG_EXPAND_SZ),
                    "Crosshair": ("", winreg.REG_EXPAND_SZ),
                    "IBeam": ("", winreg.REG_EXPAND_SZ),
                    "NWPen": (r"%SystemRoot%\cursors\aero_pen.cur", winreg.REG_EXPAND_SZ),
                    "No": (r"%SystemRoot%\cursors\aero_unavail.cur", winreg.REG_EXPAND_SZ),
                    "SizeNS": (r"%SystemRoot%\cursors\aero_ns.cur", winreg.REG_EXPAND_SZ),
                    "SizeWE": (r"%SystemRoot%\cursors\aero_ew.cur", winreg.REG_EXPAND_SZ),
                    "SizeNWSE": (r"%SystemRoot%\cursors\aero_nwse.cur", winreg.REG_EXPAND_SZ),
                    "SizeNESW": (r"%SystemRoot%\cursors\aero_nesw.cur", winreg.REG_EXPAND_SZ),
                    "SizeAll": (r"%SystemRoot%\cursors\aero_move.cur", winreg.REG_EXPAND_SZ),
                    "UpArrow": (r"%SystemRoot%\cursors\aero_up.cur", winreg.REG_EXPAND_SZ),
                    "Hand": (r"%SystemRoot%\cursors\aero_link.cur", winreg.REG_EXPAND_SZ),
                    "Pin": (r"%SystemRoot%\cursors\aero_pin.cur", winreg.REG_EXPAND_SZ),
                    "Person": (r"%SystemRoot%\cursors\aero_person.cur", winreg.REG_EXPAND_SZ),
                }

            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Control Panel\Cursors") as key:
                for reg_name, (reg_val, reg_type) in defaults.items():
                    if reg_name == "" and str(reg_val).startswith("@"):
                        reg_val = "Windows Default"
                        reg_type = winreg.REG_SZ
                    winreg.SetValueEx(key, reg_name, 0, reg_type, reg_val)
                for reg_role, _, _, _ in CURSOR_ROLES:
                    if not any(k.lower() == reg_role.lower() for k in defaults.keys()):
                        winreg.SetValueEx(key, reg_role, 0, winreg.REG_SZ, "")

            from ctypes import wintypes
            spi = ctypes.windll.user32.SystemParametersInfoW
            spi.argtypes = [wintypes.UINT, wintypes.UINT, wintypes.LPVOID, wintypes.UINT]
            spi.restype = wintypes.BOOL
            ret = spi(cls.SPI_SETCURSORS, 0, None, cls.SPIF_FLAGS)
            cls._broadcast_change()
            return bool(ret)
        except Exception as e:
            print(f"[WindowsCursorManager] Error restoring default cursors: {e}")
            return False


class FetchCatalogWorker(QThread):
    """
    Fetches full cursor repository catalog in background and saves cache.
    Emits local cache immediately on startup for 0ms load, then queries GitHub
    Git Ref API to check if remote repository commits have changed. If changed,
    fetches the full live tree dynamically and syncs additions/deletions immediately.
    """
    catalog_fetched = pyqtSignal(dict)

    def __init__(self, force_refresh: bool = False, parent=None):
        super().__init__(parent)
        self.force_refresh = force_refresh

    def run(self):
        catalog = {}

        # 1. Immediate local disk cache or bundled cursors.json check (0ms display)
        for fallback_path in [
            CATALOG_CACHE_FILE,
            os.path.join(APP_ROOT, "cursors.json"),
            os.path.join(os.path.dirname(__file__), "cache", "cursors", "catalog.json"),
            os.path.join(os.path.dirname(__file__), "cursors.json")
        ]:
            if os.path.exists(fallback_path):
                try:
                    with open(fallback_path, 'r', encoding='utf-8') as f:
                        cached_data = json.load(f)
                    if cached_data and isinstance(cached_data, dict):
                        catalog = cached_data
                        self.catalog_fetched.emit(catalog)
                        break
                except Exception:
                    pass

        # 2. Check remote repository commit/tree SHA using lightweight Git Ref API (1 fast request)
        cached_sha = ""
        if os.path.exists(TREE_SHA_CACHE_FILE):
            try:
                with open(TREE_SHA_CACHE_FILE, 'r', encoding='utf-8') as f:
                    cached_sha = f.read().strip()
            except Exception:
                pass

        remote_sha = None
        try:
            remote_sha = get_latest_tree_sha(CURSOR_REPO, CURSOR_BRANCH, timeout=6)
        except Exception:
            pass

        # If cache matches latest commit and we already emitted catalog and not forced, no remote refetch needed
        if not self.force_refresh and remote_sha and cached_sha and remote_sha == cached_sha and catalog:
            return

        # 3. Dynamic Remote Sync: Fetch fresh live Git tree from GitHub
        remote_catalog = {}

        # 3a. Check if remote cursors.json exists on CDN
        try:
            cdn_url = f"https://raw.githubusercontent.com/{CURSOR_REPO}/{CURSOR_BRANCH}/cursors.json"
            res = cdn_get(cdn_url, max_retries=1, timeout=6)
            if res.status_code == 200:
                remote_catalog = res.json()
        except Exception:
            pass

        # 3b. Git Trees API (dynamic parsing directly from live GitHub repository tree)
        if not remote_catalog and remote_sha:
            try:
                target_ref = remote_sha
                url = f"https://api.github.com/repos/{CURSOR_REPO}/git/trees/{target_ref}?recursive=1"
                res = github_api_get(url, max_retries=1, timeout=6)
                if res.status_code == 200:
                    tree_data = res.json()
                    tree = tree_data.get('tree', [])
                    name_case_map = {}  # lower -> canonical
                    for item in tree:
                        p = item.get('path', '')
                        if p.startswith('cursors/'):
                            parts = p.split('/')
                            if len(parts) >= 2:
                                raw_th_name = parts[1]
                                low_name = raw_th_name.lower()
                                if low_name not in name_case_map:
                                    name_case_map[low_name] = raw_th_name
                                canonical_name = name_case_map[low_name]
                                if canonical_name not in remote_catalog:
                                    remote_catalog[canonical_name] = {'files': [], 'arrow_file': '', 'file_shas': {}}
                                if item.get('type') == 'blob':
                                    rel_path = '/'.join(parts[2:])
                                    if rel_path:
                                        if rel_path not in remote_catalog[canonical_name]['files']:
                                            remote_catalog[canonical_name]['files'].append(rel_path)
                                        if item.get('sha'):
                                            remote_catalog[canonical_name]['file_shas'][rel_path] = item.get('sha')

                    for th_name, info in remote_catalog.items():
                        for f in info['files']:
                            low = f.lower()
                            if any(w in low for w in ['normal', 'arrow', 'pointer', '01']):
                                info['arrow_file'] = f
                                break
                        if not info['arrow_file'] and info['files']:
                            info['arrow_file'] = info['files'][0]
            except Exception:
                pass

        # 4. Save and emit if catalog changed or forced
        if remote_catalog:
            if remote_catalog != catalog or self.force_refresh:
                catalog = remote_catalog
                self.catalog_fetched.emit(catalog)
            try:
                os.makedirs(os.path.dirname(CATALOG_CACHE_FILE), exist_ok=True)
                with open(CATALOG_CACHE_FILE, 'w', encoding='utf-8') as f:
                    json.dump(catalog, f, indent=2)
                if remote_sha:
                    with open(TREE_SHA_CACHE_FILE, 'w', encoding='utf-8') as f:
                        f.write(remote_sha)
            except Exception:
                pass


class DownloadThemeWorker(QObject):
    """Thread-safe worker for downloading cursor themes using python native daemon threads."""
    download_finished = pyqtSignal(str, bool, str)

    def __init__(self, theme_name: str, file_list: list, target_dir: str, parent=None):
        super().__init__(parent)
        self.theme_name = theme_name
        self.file_list = file_list
        self.target_dir = target_dir

    def start(self):
        t = threading.Thread(target=self._run, daemon=True)
        t.start()

    def _run(self):
        try:
            os.makedirs(self.target_dir, exist_ok=True)
            import urllib.parse

            def _download_single(rel_file):
                safe_theme = urllib.parse.quote(self.theme_name)
                safe_rel = urllib.parse.quote(rel_file)
                url = f"https://raw.githubusercontent.com/{CURSOR_REPO}/{CURSOR_BRANCH}/cursors/{safe_theme}/{safe_rel}"
                res = cdn_get(url, max_retries=2, timeout=12)
                dest_path = os.path.join(self.target_dir, rel_file.replace('/', os.sep))
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                with open(dest_path, 'wb') as f:
                    f.write(res.content)
                return True

            with ThreadPoolExecutor(max_workers=3) as executor:
                list(executor.map(_download_single, self.file_list))

            self.download_finished.emit(self.theme_name, True, "Successfully downloaded.")
        except Exception as e:
            print(f"[DownloadThemeWorker] Failed downloading '{self.theme_name}': {e}")
            self.download_finished.emit(self.theme_name, False, str(e))


class DownloadAllCursorsWorker(QObject):
    """
    Background worker that downloads all catalog cursor themes locally.
    Uses atomic per-theme staging folders (.staging_<theme>) so cancellation or failures
    never leave corrupted / half-downloaded theme folders.
    Supports real-time cancellation, progress streaming, and hash verification.
    """
    progress_updated = pyqtSignal(int, int, str)   # current, total, msg
    theme_downloaded = pyqtSignal(str, bool, str)   # theme_name, success, target_dir_or_err
    all_finished = pyqtSignal(int, int, int, list)  # downloaded_count, skipped_count, error_count, error_list
    cancelled = pyqtSignal(int, int)               # downloaded_count, total_count

    def __init__(self, catalog: dict, cursor_dir: str, parent=None):
        super().__init__(parent)
        self.catalog = dict(catalog)
        self.cursor_dir = cursor_dir
        self._is_cancelled = False
        self._active_stagings = set()
        self._lock = threading.Lock()
        self._thread = None

    def start(self):
        self._is_cancelled = False
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def cancel(self):
        self._is_cancelled = True
        self._cleanup_all_stagings()

    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def _cleanup_all_stagings(self):
        with self._lock:
            for s_dir in list(self._active_stagings):
                if os.path.exists(s_dir):
                    try:
                        shutil.rmtree(s_dir, ignore_errors=True)
                    except Exception:
                        pass
            self._active_stagings.clear()

            if os.path.exists(self.cursor_dir):
                try:
                    for entry in os.listdir(self.cursor_dir):
                        if entry.startswith('.staging_'):
                            shutil.rmtree(os.path.join(self.cursor_dir, entry), ignore_errors=True)
                except Exception:
                    pass

    def _is_theme_fully_downloaded(self, theme_name: str, info: dict) -> bool:
        theme_dir = os.path.join(self.cursor_dir, theme_name)
        if not os.path.exists(theme_dir):
            if os.path.exists(self.cursor_dir):
                for sub in os.listdir(self.cursor_dir):
                    if sub.lower() == theme_name.lower():
                        theme_dir = os.path.join(self.cursor_dir, sub)
                        break
            if not os.path.exists(theme_dir):
                return False

        files = info.get('files', [])
        if not files:
            return False

        file_shas = info.get('file_shas', {})
        for rel_f in files:
            dest_p = os.path.join(theme_dir, rel_f.replace('/', os.sep))
            if not os.path.exists(dest_p) or os.path.getsize(dest_p) == 0:
                return False
            if file_shas and rel_f in file_shas:
                remote_sha = file_shas[rel_f]
                if not file_matches_git_sha(dest_p, remote_sha):
                    return False
        return True

    def _download_single_theme(self, th_name: str, info: dict) -> tuple:
        """
        Downloads a single theme into an atomic staging directory.
        Returns (th_name, success, target_dir_or_err).
        """
        if self._is_cancelled:
            return th_name, False, "Cancelled"

        files = info.get('files', [])
        if not files:
            return th_name, False, "No files in theme manifest"

        staging_dir = os.path.join(self.cursor_dir, f".staging_{th_name}")
        final_dir = os.path.join(self.cursor_dir, th_name)
        with self._lock:
            self._active_stagings.add(staging_dir)

        try:
            os.makedirs(staging_dir, exist_ok=True)
            import urllib.parse
            for rel_f in files:
                if self._is_cancelled:
                    raise InterruptedError("Cancelled by user")

                safe_th = urllib.parse.quote(th_name)
                safe_f = urllib.parse.quote(rel_f)
                url = f"https://raw.githubusercontent.com/{CURSOR_REPO}/{CURSOR_BRANCH}/cursors/{safe_th}/{safe_f}"
                res = cdn_get(url, max_retries=3, timeout=10)

                dest_p = os.path.join(staging_dir, rel_f.replace('/', os.sep))
                os.makedirs(os.path.dirname(dest_p), exist_ok=True)
                with open(dest_p, 'wb') as f:
                    f.write(res.content)

                if not os.path.exists(dest_p) or os.path.getsize(dest_p) == 0:
                    raise IOError(f"Failed to write file '{rel_f}' (0 bytes)")

            if self._is_cancelled:
                raise InterruptedError("Cancelled by user")

            # All files downloaded & verified: Atomic rename to final directory
            if os.path.exists(final_dir):
                shutil.rmtree(final_dir, ignore_errors=True)
            shutil.move(staging_dir, final_dir)

            with self._lock:
                self._active_stagings.discard(staging_dir)
            return th_name, True, final_dir

        except Exception as e:
            with self._lock:
                self._active_stagings.discard(staging_dir)
            if os.path.exists(staging_dir):
                try:
                    shutil.rmtree(staging_dir, ignore_errors=True)
                except Exception:
                    pass
            return th_name, False, str(e)

    def _run(self):
        total_themes = len(self.catalog)
        if total_themes == 0:
            self.all_finished.emit(0, 0, 0, [])
            return

        to_download = []
        skipped_count = 0

        # 1. Quick initial scan for already downloaded and valid themes
        for idx, (th_name, info) in enumerate(self.catalog.items()):
            if self._is_cancelled:
                self._cleanup_all_stagings()
                self.cancelled.emit(0, total_themes)
                return
            if self._is_theme_fully_downloaded(th_name, info):
                skipped_count += 1
            else:
                to_download.append((th_name, info))

        if skipped_count > 0:
            self.progress_updated.emit(skipped_count, total_themes, f"{skipped_count} up to date")

        if not to_download:
            self.all_finished.emit(0, skipped_count, 0, [])
            return

        downloaded_count = 0
        error_count = 0
        error_list = []
        processed_count = skipped_count

        # 2. Concurrently download missing themes across 4 workers
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {executor.submit(self._download_single_theme, th_n, inf): th_n for th_n, inf in to_download}
            for future in as_completed(futures):
                if self._is_cancelled:
                    executor.shutdown(wait=False, cancel_futures=True)
                    self._cleanup_all_stagings()
                    self.cancelled.emit(downloaded_count, total_themes)
                    return

                try:
                    th_name, success, result_str = future.result()
                    processed_count += 1
                    if success:
                        downloaded_count += 1
                        self.theme_downloaded.emit(th_name, True, result_str)
                        self.progress_updated.emit(processed_count, total_themes, th_name)
                    else:
                        if "Cancelled" not in result_str and "InterruptedError" not in result_str:
                            error_count += 1
                            error_list.append(f"{th_name}: {result_str}")
                            self.theme_downloaded.emit(th_name, False, result_str)
                            self.progress_updated.emit(processed_count, total_themes, f"Failed {th_name}")
                except Exception as e:
                    error_count += 1
                    error_list.append(str(e))

        if self._is_cancelled:
            self._cleanup_all_stagings()
            self.cancelled.emit(downloaded_count, total_themes)
        else:
            self.all_finished.emit(downloaded_count, skipped_count, error_count, error_list)


class ConcurrentPreviewWorker(QObject):
    """Processes online preview thumbnail downloads concurrently in background daemon threads with zero UI freezing."""
    preview_ready = pyqtSignal(str, str, QImage)  # theme_name, role_name, qimage

    def __init__(self, tasks: list, parent=None):
        super().__init__(parent)
        self.tasks = list(tasks)  # list of (theme_name, role_name, rel_file)
        self._is_running = True
        self._thread = None
        self._pending_lock = threading.Lock()
        self._pending_tasks = list(tasks)
        self._failed_tasks = set()

    def start(self):
        self._is_running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def isRunning(self):
        return self._thread is not None and self._thread.is_alive()

    def stop(self):
        self._is_running = False

    def add_tasks(self, new_tasks: list):
        with self._pending_lock:
            existing = set((t[0], t[1]) for t in self.tasks)
            for nt in new_tasks:
                if (nt[0], nt[1]) not in existing and (nt[0], nt[1]) not in self._failed_tasks:
                    self.tasks.append(nt)
                    self._pending_tasks.append(nt)

    def _run(self):
        import urllib.parse

        def _fetch_task(task):
            if not self._is_running:
                return
            theme_name, role_name, rel_file = task
            if not rel_file:
                return

            img = get_theme_preview_image(theme_name, role_name)
            if not img.isNull() and self._is_running:
                self.preview_ready.emit(theme_name, role_name, img)
                return

            try:
                safe_theme = urllib.parse.quote(theme_name)
                safe_rel = urllib.parse.quote(rel_file)
                url = f"https://raw.githubusercontent.com/{CURSOR_REPO}/{CURSOR_BRANCH}/cursors/{safe_theme}/{safe_rel}"
                res = cdn_get(url, max_retries=1, timeout=8)
                if res.status_code == 200 and res.content and self._is_running:
                    img = CurGenerator.extract_best_cursor_image_from_bytes(res.content)
                    if not img.isNull() and self._is_running:
                        target_sz = 60 if role_name == "Arrow" else 20
                        scaled_img = img.scaled(target_sz, target_sz, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                        try:
                            save_path = os.path.join(PREVIEWS_CACHE_DIR, f"{theme_name}_{role_name}.png")
                            scaled_img.save(save_path, "PNG")
                            if role_name == "Arrow":
                                legacy_p = os.path.join(PREVIEWS_CACHE_DIR, f"{theme_name}.png")
                                if not os.path.exists(legacy_p):
                                    scaled_img.save(legacy_p, "PNG")
                        except Exception:
                            pass
                        if self._is_running:
                            self.preview_ready.emit(theme_name, role_name, scaled_img)
                else:
                    self._failed_tasks.add((theme_name, role_name))
            except Exception:
                self._failed_tasks.add((theme_name, role_name))

        try:
            with ThreadPoolExecutor(max_workers=6) as executor:
                while self._is_running:
                    with self._pending_lock:
                        if not self._pending_tasks:
                            break
                        batch = self._pending_tasks[:12]
                        self._pending_tasks = self._pending_tasks[12:]
                    try:
                        list(executor.map(_fetch_task, batch))
                    except Exception:
                        break
        except Exception:
            pass
        finally:
            try:
                session.close()
            except Exception:
                pass


class CursorOptionFrame(QFrame):
    """
    Sleek cursor card supporting local selection, fast concurrent download, favorite starring, and instant uninstall.
    """
    card_selected = pyqtSignal(str)
    download_requested = pyqtSignal(str)
    uninstall_requested = pyqtSignal(str)
    favorite_toggled = pyqtSignal(str, bool)

    def __init__(self, theme_name: str, theme_dir: str, is_installed: bool = True, is_active: bool = False, is_favorite: bool = False, info: dict = None, parent=None):
        super().__init__(parent)
        self.theme_name = theme_name
        self.theme_dir = theme_dir
        self.is_installed = is_installed
        self.is_active = is_active
        self.is_favorite = is_favorite
        self.info = info or {}
        self.online_roles = {}
        self.is_default = (theme_name == "Windows Default")
        self.is_downloading = False
        self.mini_labels = {}
        self._previews_loaded = False

        self.display_name = theme_name
        self.resolved_roles = None
        self.effective_dir = theme_dir

        self.setObjectName("cursorOptionFrame")
        self.setFixedSize(150, 190)
        self.setCursor(QCursor(Qt.PointingHandCursor))

        self._setup_ui()
        self.update_style()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignCenter)

        # 1. Main Arrow Preview
        self.image_label = QLabel("↖")
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setFixedHeight(84)
        self.image_label.setStyleSheet("font-size: 34px; color: #888899; background: transparent; border: none;")
        layout.addWidget(self.image_label, 0, Qt.AlignCenter)

        # 2. Miniature Pack Preview Strip (Help, Wait, Hand, IBeam)
        self.bottom_action_container = QWidget()
        self.bottom_action_layout = QHBoxLayout(self.bottom_action_container)
        self.bottom_action_layout.setContentsMargins(0, 0, 0, 0)
        self.bottom_action_layout.setSpacing(6)
        self.bottom_action_layout.setAlignment(Qt.AlignCenter)

        for role_key in ["Help", "Wait", "Hand", "IBeam"]:
            mini_lbl = QLabel()
            mini_lbl.setFixedSize(20, 20)
            mini_lbl.setAlignment(Qt.AlignCenter)
            mini_lbl.setStyleSheet("background: transparent; border: none;")
            self.mini_labels[role_key] = mini_lbl
            self.bottom_action_layout.addWidget(mini_lbl)

        layout.addWidget(self.bottom_action_container)
        layout.addSpacing(2)

        # 3. Theme Title Label
        self.name_label = QLabel(self.display_name)
        self.name_label.setAlignment(Qt.AlignCenter)
        self.name_label.setStyleSheet("color: white; font-weight: bold; font-size: 12px; background: transparent;")
        self.name_label.setToolTip(self.display_name)
        layout.addWidget(self.name_label, 0, Qt.AlignCenter)

        # 4. Favorite Star Button (Top Left)
        self.favorite_btn = QPushButton(self)
        self.favorite_btn.setObjectName("favoriteBtn")
        self.favorite_btn.setFixedSize(26, 26)
        self.favorite_btn.setIconSize(QSize(16, 16))
        self.favorite_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.favorite_btn.move(8, 8)
        self.favorite_btn.clicked.connect(self._on_favorite_clicked)
        self.update_favorite_style()

        # 5. Top Right Action Button (Uninstall if installed, Download icon if online)
        if self.is_installed:
            if not self.is_default:
                self.uninstall_btn = QPushButton("\uE74D", self)
                self.uninstall_btn.setObjectName("uninstallBtn")
                self.uninstall_btn.setFont(QFont('Segoe MDL2 Assets', 10))
                self.uninstall_btn.setFixedSize(26, 26)
                self.uninstall_btn.setCursor(QCursor(Qt.PointingHandCursor))
                self.uninstall_btn.setToolTip("Uninstall Cursor")
                self.uninstall_btn.setStyleSheet("""
                    QPushButton#uninstallBtn {
                        background-color: rgba(255, 255, 255, 0.12);
                        color: #ffffff;
                        border-radius: 13px;
                        border: 1px solid rgba(255, 255, 255, 0.2);
                    }
                    QPushButton#uninstallBtn:hover {
                        background-color: #e78284;
                        border: 1px solid #e78284;
                    }
                """)
                self.uninstall_btn.move(116, 8)
                self.uninstall_btn.clicked.connect(self._on_uninstall_clicked)
                self.uninstall_btn.hide()
            else:
                self.uninstall_btn = None
            self.download_btn = None
        else:
            self.uninstall_btn = None
            self.download_btn = QPushButton("\uE118", self)
            self.download_btn.setObjectName("downloadBtn")
            self.download_btn.setFont(QFont('Segoe MDL2 Assets', 10))
            self.download_btn.setFixedSize(26, 26)
            self.download_btn.setCursor(QCursor(Qt.PointingHandCursor))
            self.download_btn.setToolTip("Download Cursor Pack")
            self.download_btn.setStyleSheet("""
                QPushButton#downloadBtn {
                    background-color: rgba(231, 130, 132, 0.2);
                    color: #ff6b81;
                    border: 1px solid rgba(231, 130, 132, 0.4);
                    border-radius: 13px;
                }
                QPushButton#downloadBtn:hover {
                    background-color: #e78284;
                    color: white;
                    border: 1px solid #e78284;
                }
            """)
            self.download_btn.move(116, 8)
            self.download_btn.clicked.connect(self._on_download_clicked)

    def load_previews(self):
        if self._previews_loaded:
            return
        self._previews_loaded = True

        if self.is_installed:
            pix = self._get_local_preview_pixmap("Arrow", 64)
            if not pix.isNull():
                self.image_label.setPixmap(pix.scaled(60, 60, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                self.image_label.setStyleSheet("background: transparent; border: none;")
            else:
                self._load_cached_arrow_or_placeholder()
        else:
            if not self.online_roles and self.info:
                flist = self.info.get('files', [])
                def_arrow = self.info.get('arrow_file', '')
                self.online_roles = resolve_online_theme_roles(flist, def_arrow)
            self._load_cached_arrow_or_placeholder()

        for role_key, mini_lbl in self.mini_labels.items():
            if self.is_installed:
                mini_pix = self._get_local_preview_pixmap(role_key, 20)
                if not mini_pix.isNull():
                    mini_lbl.setPixmap(mini_pix.scaled(18, 18, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            else:
                img = get_theme_preview_image(self.theme_name, role_key)
                if not img.isNull():
                    mini_lbl.setPixmap(QPixmap.fromImage(img.scaled(18, 18, Qt.KeepAspectRatio, Qt.SmoothTransformation)))

    def update_favorite_style(self):
        if self.is_favorite:
            self.favorite_btn.setIcon(get_star_icon(filled=True, color="#FFB800", size=16))
            self.favorite_btn.setText("")
            self.favorite_btn.setToolTip("Favorited")
            self.favorite_btn.setStyleSheet("""
                QPushButton#favoriteBtn {
                    background-color: rgba(255, 184, 0, 0.22);
                    border-radius: 13px;
                    border: 1px solid rgba(255, 184, 0, 0.55);
                    padding: 0px;
                }
                QPushButton#favoriteBtn:hover {
                    background-color: rgba(255, 184, 0, 0.38);
                    border: 1px solid #FFB800;
                }
            """)
            self.favorite_btn.show()
        else:
            self.favorite_btn.setIcon(get_star_icon(filled=False, outline_color="#ffffff", size=16))
            self.favorite_btn.setText("")
            self.favorite_btn.setToolTip("Add to Favorites")
            self.favorite_btn.setStyleSheet("""
                QPushButton#favoriteBtn {
                    background-color: rgba(255, 255, 255, 0.12);
                    border-radius: 13px;
                    border: 1px solid rgba(255, 255, 255, 0.2);
                    padding: 0px;
                }
                QPushButton#favoriteBtn:hover {
                    background-color: rgba(255, 184, 0, 0.25);
                    border: 1px solid #FFB800;
                }
            """)
            self.favorite_btn.hide()

    def _on_favorite_clicked(self):
        self.is_favorite = not self.is_favorite
        self.update_favorite_style()
        self.favorite_toggled.emit(self.theme_name, self.is_favorite)

    def _load_cached_arrow_or_placeholder(self):
        img = get_theme_preview_image(self.theme_name, "Arrow")
        if not img.isNull():
            pix = QPixmap.fromImage(img.scaled(60, 60, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            self.image_label.setPixmap(pix)
            self.image_label.setStyleSheet("background: transparent; border: none;")
            return

        self.image_label.setText("↖")
        self.image_label.setStyleSheet("font-size: 34px; color: #888899; background: transparent;")

    def set_preview_pixmap(self, pix: QPixmap):
        if not pix.isNull():
            self.arrow_pixmap = pix
            self.image_label.setPixmap(pix.scaled(60, 60, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            self.image_label.setStyleSheet("background: transparent; border: none;")

    def set_mini_preview_pixmap(self, role: str, pix: QPixmap):
        if role in self.mini_labels and not pix.isNull():
            self.mini_labels[role].setPixmap(pix.scaled(18, 18, Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self.is_downloading:
                event.accept()
                return
            if self.is_installed:
                self.card_selected.emit(self.theme_name)
            else:
                self._on_download_clicked()
        super().mousePressEvent(event)

    def _on_download_clicked(self):
        if not self.is_downloading and not self.is_installed:
            self.is_downloading = True
            if hasattr(self, 'download_btn') and self.download_btn:
                self.download_btn.setText("\uE10C")
                self.download_btn.setEnabled(False)
                self.download_btn.setToolTip("Downloading...")
            self.download_requested.emit(self.theme_name)

    def _on_uninstall_clicked(self):
        self.uninstall_requested.emit(self.theme_name)

    def enterEvent(self, event):
        if not self.is_active:
            self.setStyleSheet("QFrame#cursorOptionFrame { background-color: #18181c; border-radius: 20px; border: 2px solid #e78284; }")
        if self.favorite_btn and not self.is_favorite:
            self.favorite_btn.show()
        if self.uninstall_btn and self.is_installed and not self.is_default:
            self.uninstall_btn.show()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.update_style()
        if self.favorite_btn and not self.is_favorite:
            self.favorite_btn.hide()
        if self.uninstall_btn:
            self.uninstall_btn.hide()
        super().leaveEvent(event)

    def set_active(self, active: bool):
        self.is_active = active
        self.update_style()

    def set_installed_state(self, is_installed: bool, theme_dir: str = ""):
        self.is_installed = is_installed
        self.is_downloading = False
        self.theme_dir = theme_dir

        if is_installed:
            if hasattr(self, 'download_btn') and self.download_btn:
                self.download_btn.deleteLater()
                self.download_btn = None

            if not self.is_default:
                if not getattr(self, 'uninstall_btn', None):
                    self.uninstall_btn = QPushButton("\uE74D", self)
                    self.uninstall_btn.setObjectName("uninstallBtn")
                    self.uninstall_btn.setFont(QFont('Segoe MDL2 Assets', 10))
                    self.uninstall_btn.setFixedSize(26, 26)
                    self.uninstall_btn.setCursor(QCursor(Qt.PointingHandCursor))
                    self.uninstall_btn.setToolTip("Uninstall Cursor")
                    self.uninstall_btn.setStyleSheet("""
                        QPushButton#uninstallBtn {
                            background-color: rgba(255, 255, 255, 0.12);
                            color: #ffffff;
                            border-radius: 13px;
                            border: 1px solid rgba(255, 255, 255, 0.2);
                        }
                        QPushButton#uninstallBtn:hover {
                            background-color: #e78284;
                            border: 1px solid #e78284;
                        }
                    """)
                    self.uninstall_btn.move(116, 8)
                    self.uninstall_btn.clicked.connect(self._on_uninstall_clicked)
                self.uninstall_btn.hide()
            else:
                self.uninstall_btn = None

            if theme_dir and os.path.exists(theme_dir):
                self.display_name, self.resolved_roles, self.effective_dir = resolve_theme_directory_roles(theme_dir)
                self.name_label.setText(self.display_name)
                self.name_label.setToolTip(self.display_name)
                pix = self._get_local_preview_pixmap("Arrow", 64)
                if not pix.isNull():
                    self.set_preview_pixmap(pix)
        else:
            if hasattr(self, 'uninstall_btn') and self.uninstall_btn:
                self.uninstall_btn.deleteLater()
                self.uninstall_btn = None

            if not getattr(self, 'download_btn', None):
                self.download_btn = QPushButton("\uE118", self)
                self.download_btn.setObjectName("downloadBtn")
                self.download_btn.setFont(QFont('Segoe MDL2 Assets', 10))
                self.download_btn.setFixedSize(26, 26)
                self.download_btn.setCursor(QCursor(Qt.PointingHandCursor))
                self.download_btn.setToolTip("Download Cursor Pack")
                self.download_btn.setStyleSheet("""
                    QPushButton#downloadBtn {
                        background-color: rgba(231, 130, 132, 0.2);
                        color: #ff6b81;
                        border: 1px solid rgba(231, 130, 132, 0.4);
                        border-radius: 13px;
                    }
                    QPushButton#downloadBtn:hover {
                        background-color: #e78284;
                        color: white;
                        border: 1px solid #e78284;
                    }
                """)
                self.download_btn.move(116, 8)
                self.download_btn.clicked.connect(self._on_download_clicked)
                self.download_btn.show()

            self.display_name = self.theme_name
            self.name_label.setText(self.display_name)
            self.name_label.setToolTip(self.display_name)
            self._load_cached_arrow_or_placeholder()

        self._previews_loaded = False
        self.load_previews()
        self.update_style()

    def update_style(self):
        if self.is_active:
            self.setStyleSheet("QFrame#cursorOptionFrame { background-color: #261115; border-radius: 20px; border: 2px solid #e78284; }")
        else:
            self.setStyleSheet("QFrame#cursorOptionFrame { background-color: #121214; border-radius: 20px; border: 2px solid #24242a; }")

    def get_resolved_roles(self):
        if self.resolved_roles is None:
            if self.is_installed and not self.is_default and self.theme_dir and os.path.exists(self.theme_dir):
                self.display_name, self.resolved_roles, self.effective_dir = resolve_theme_directory_roles(self.theme_dir)
                if hasattr(self, 'name_label') and self.name_label.text() != self.display_name:
                    self.name_label.setText(self.display_name)
                    self.name_label.setToolTip(self.display_name)
            else:
                self.resolved_roles = {}
        return self.resolved_roles

    def _get_local_preview_pixmap(self, role: str, size: int) -> QPixmap:
        if self.is_default:
            def_filenames = {
                "Arrow": "aero_arrow.cur", "Help": "aero_helpsel.cur", "Wait": "aero_busy.ani",
                "AppStarting": "aero_working.ani", "Hand": "aero_link.cur", "IBeam": "beam_r.cur"
            }
            fn = def_filenames.get(role, "aero_arrow.cur")
            sys_path = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "Cursors", fn)
            if os.path.exists(sys_path):
                return CurGenerator.extract_pixmap_from_cur(sys_path, size)
            return QPixmap()

        roles = self.get_resolved_roles()
        if self.is_installed and role in roles and self.effective_dir:
            target_path = os.path.join(self.effective_dir, roles[role])
            if os.path.exists(target_path):
                return CurGenerator.extract_pixmap_from_cur(target_path, size)

        return QPixmap()


class CursorGalleryWidget(QWidget):
    """
    Mouse Cursor Gallery & Store.
    Pulls catalog from GitHub, caches previews, fast multi-threaded downloads, favorites, and buttery smooth lazy loading.
    """
    status_message_requested = pyqtSignal(str)
    reload_requested = pyqtSignal()

    def __init__(self, cursor_dir: str, parent=None):
        super().__init__(parent)
        self.cursor_dir = cursor_dir
        os.makedirs(self.cursor_dir, exist_ok=True)

        self.original_theme = self._detect_current_active_theme()
        self.selected_theme = self.original_theme
        self.is_dirty = False

        self.cards_map = {}
        self.catalog = {}
        self.download_workers = {}
        self.download_all_worker = None
        self.preview_worker = None
        self._sync_started = False
        self.favorites = self._load_favorites()

        self.current_tab = "explore"  # "explore", "installed", or "fav"
        self._all_theme_items = []
        self._pending_preview_tasks = []
        self._rendered_count = 0
        self._download_queue = deque()
        self._max_concurrent_downloads = 2
        self._active_download_count = 0
        self._is_checking_chunks = False

        self._apply_debounce_timer = QTimer(self)
        self._apply_debounce_timer.setSingleShot(True)
        self._apply_debounce_timer.timeout.connect(self._do_apply_pending_theme)
        self._pending_apply_theme = None

        self._setup_ui()
        self._load_cached_catalog()
        self.refresh_list()
        self.catalog_worker = None
        self.sync_catalog(force=False)

    def sync_catalog(self, force=False):
        if self.catalog_worker and self.catalog_worker.isRunning():
            return
        self.catalog_worker = FetchCatalogWorker(force_refresh=force)
        self.catalog_worker.catalog_fetched.connect(self._on_catalog_fetched)
        self.catalog_worker.start()

    def _load_favorites(self) -> set:
        if os.path.exists(FAVORITES_FILE):
            try:
                with open(FAVORITES_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if isinstance(data, list):
                    return set(data)
            except Exception:
                pass
        return set()

    def _save_favorites(self):
        try:
            atomic_json_write(FAVORITES_FILE, sorted(list(self.favorites)))
        except Exception:
            pass

    def showEvent(self, event):
        super().showEvent(event)
        if not self._sync_started:
            self._sync_started = True
            QTimer.singleShot(200, lambda: self.sync_catalog(force=False))
        self._schedule_viewport_check()
        self._check_and_load_more_chunks()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._schedule_viewport_check()
        self._check_and_load_more_chunks()

    def _schedule_viewport_check(self):
        if not hasattr(self, '_vp_check_timer'):
            self._vp_check_timer = QTimer(self)
            self._vp_check_timer.setSingleShot(True)
            self._vp_check_timer.timeout.connect(self.check_visible_cards)
        self._vp_check_timer.start(10)

    def _check_and_load_more_chunks(self):
        """Ensures enough cards are rendered to fill the viewport and create a scrollbar even on 4K/maximized windows."""
        if self._is_checking_chunks or self._rendered_count >= len(self._all_theme_items):
            return
        self._is_checking_chunks = True
        try:
            sb = self.scroll_area.verticalScrollBar()
            if sb.maximum() > 0 and sb.value() >= sb.maximum() - 400:
                self._render_next_chunk(24)
        finally:
            self._is_checking_chunks = False

    def check_visible_cards(self):
        if not self.cards_map or not self.isVisible():
            return
        vp = self.scroll_area.viewport()
        vp_rect = vp.rect()
        buffer_rect = QRect(vp_rect.x(), vp_rect.y() - 300, vp_rect.width(), vp_rect.height() + 600)

        new_tasks = []
        for card in self.cards_map.values():
            if card._previews_loaded:
                continue
            card_pt = card.mapTo(vp, QPoint(0, 0))
            card_rect = QRect(card_pt, card.size())
            if buffer_rect.intersects(card_rect):
                card.load_previews()
                if not card.is_installed and card.online_roles:
                    for role_name in ["Arrow", "Help", "Wait", "Hand", "IBeam"]:
                        rel_f = card.online_roles.get(role_name, '')
                        if rel_f:
                            img = get_theme_preview_image(card.theme_name, role_name)
                            if img.isNull():
                                new_tasks.append((card.theme_name, role_name, rel_f))

        if new_tasks:
            self._pending_preview_tasks.extend(new_tasks)
            if not self.preview_worker or not self.preview_worker.isRunning():
                tasks_to_run = self._pending_preview_tasks[:]
                self._pending_preview_tasks.clear()
                self.preview_worker = ConcurrentPreviewWorker(tasks_to_run)
                self.preview_worker.preview_ready.connect(self._on_preview_ready)
                self.preview_worker.start()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#121212"))

    def _setup_ui(self):
        self.setObjectName("cursorGalleryWidget")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet("QWidget#cursorGalleryWidget { background-color: #121212; } QScrollArea { border: none; background: transparent; } QWidget#cursorGridWidget { background: transparent; }")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)

        # 1. Pill-shaped Segmented Tabs Container (Explore / Installed / Fav / Download All)
        self.tab_container = QFrame()
        self.tab_container.setObjectName("pillTabContainer")
        self.tab_container.setStyleSheet("""
            QFrame#pillTabContainer {
                background-color: rgba(255,255,255,0.05);
                border: 1px solid rgba(255,255,255,0.06);
                border-radius: 18px;
                padding: 4px;
            }
        """)
        tab_layout = QHBoxLayout(self.tab_container)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.setSpacing(4)

        self.explore_tab = PillTabButton("Explore", height=30)
        self.explore_tab.setChecked(True)
        self.explore_tab.clicked.connect(lambda: self._set_category_tab("explore"))

        self.installed_tab = PillTabButton("Installed", height=30)
        self.installed_tab.clicked.connect(lambda: self._set_category_tab("installed"))

        self.fav_tab = PillTabButton("Fav", height=30)
        self.fav_tab.clicked.connect(lambda: self._set_category_tab("fav"))

        self.tab_group = QButtonGroup(self)
        self.tab_group.setExclusive(True)
        self.tab_group.addButton(self.explore_tab)
        self.tab_group.addButton(self.installed_tab)
        self.tab_group.addButton(self.fav_tab)

        tab_layout.addWidget(self.explore_tab)
        tab_layout.addWidget(self.installed_tab)
        tab_layout.addWidget(self.fav_tab)

        tab_layout.addSpacing(6)

        # Download All button
        self.download_all_btn = QPushButton("\uE118  Download All")
        self.download_all_btn.setObjectName("downloadAllBtn")
        self.download_all_btn.setFont(QFont('Segoe MDL2 Assets', 10))
        self.download_all_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.download_all_btn.setToolTip("Download all cursor packs locally")
        self.download_all_btn.clicked.connect(self._on_download_all_clicked)
        tab_layout.addWidget(self.download_all_btn)

        # 2. Scroll Area & Grid Layout
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setObjectName("cursorScrollArea")
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setFocusPolicy(Qt.NoFocus)
        self.scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; } QWidget#cursorGridWidget { background: transparent; }")
        self.scroll_area.verticalScrollBar().valueChanged.connect(self._on_scroll_changed)

        self.grid_widget = QWidget()
        self.grid_widget.setObjectName("cursorGridWidget")
        self.grid_layout = FlowLayout(self.grid_widget, spacing=14)

        self.scroll_area.setWidget(self.grid_widget)
        main_layout.addWidget(self.scroll_area, 1)

    def _set_category_tab(self, category: str):
        if self.current_tab != category:
            self.current_tab = category
            self.refresh_list()

    def _load_cached_catalog(self):
        for fallback_path in [
            CATALOG_CACHE_FILE,
            os.path.join(APP_ROOT, "cursors.json"),
            os.path.join(os.path.dirname(__file__), "cache", "cursors", "catalog.json"),
            os.path.join(os.path.dirname(__file__), "cursors.json")
        ]:
            if os.path.exists(fallback_path):
                try:
                    with open(fallback_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    if data and isinstance(data, dict):
                        self.catalog = data
                        break
                except Exception:
                    pass

    def _on_catalog_fetched(self, catalog: dict):
        self.catalog = catalog
        self.refresh_list()

    def _detect_current_active_theme(self) -> str:
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Control Panel\Cursors") as key:
                scheme_name, _ = winreg.QueryValueEx(key, "")
                try:
                    arrow_val, _ = winreg.QueryValueEx(key, "Arrow")
                except Exception:
                    arrow_val = ""
        except Exception:
            scheme_name = ""
            arrow_val = ""

        scheme_name = scheme_name or "Windows Default"
        if scheme_name in ["Windows Default", "Windows Aero", "Windows Default (system scheme)", ""]:
            return "Windows Default"

        if not os.path.exists(self.cursor_dir):
            return "Windows Default"

        scheme_lower = scheme_name.lower()
        entries = [e for e in sorted(os.listdir(self.cursor_dir)) if os.path.isdir(os.path.join(self.cursor_dir, e))]

        # 1. Direct folder name match
        for entry in entries:
            if entry.lower() == scheme_lower:
                return entry

        # 2. Match folder path inside registry Arrow value
        if arrow_val:
            norm_arrow = os.path.normpath(arrow_val).lower()
            for entry in entries:
                entry_p = os.path.normpath(os.path.join(self.cursor_dir, entry)).lower()
                if entry_p in norm_arrow:
                    return entry

        # 3. Fallback: match by display name
        for entry in entries:
            full_p = os.path.join(self.cursor_dir, entry)
            disp_name, _, _ = resolve_theme_directory_roles(full_p)
            if disp_name.lower() == scheme_lower:
                return entry

        return "Windows Default"

    def refresh_list(self):
        scroll_pos = self.scroll_area.verticalScrollBar().value()

        if self.preview_worker and self.preview_worker.isRunning():
            self.preview_worker.stop()

        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        self.cards_map.clear()

        # 1. Local themes (with case-insensitive index)
        local_themes = {}
        local_themes_lower = {}
        if os.path.exists(self.cursor_dir):
            for entry in sorted(os.listdir(self.cursor_dir)):
                full_p = os.path.join(self.cursor_dir, entry)
                if os.path.isdir(full_p):
                    local_themes[entry] = full_p
                    local_themes_lower[entry.lower()] = (entry, full_p)

        # 2. Collect all unique theme names across catalog + local themes
        all_theme_names = set()
        for cat_name in self.catalog.keys():
            all_theme_names.add(cat_name)

        for loc_name in local_themes.keys():
            matching_cat = next((k for k in self.catalog.keys() if k.lower() == loc_name.lower()), None)
            if matching_cat:
                all_theme_names.add(matching_cat)
            else:
                all_theme_names.add(loc_name)

        # Sort all themes alphabetically A-Z
        sorted_theme_names = sorted(all_theme_names, key=lambda s: s.lower())

        # 3. Build unified item descriptor list filtered by current tab
        items = []

        # Windows Default theme (always at the top if present)
        if self.current_tab != "fav" or "Windows Default" in self.favorites:
            items.append({
                'type': 'default',
                'theme_name': 'Windows Default',
                'theme_dir': '',
                'is_installed': True,
                'info': {}
            })

        for th_name in sorted_theme_names:
            if th_name == "Windows Default":
                continue

            th_name_lower = th_name.lower()
            is_installed = th_name_lower in local_themes_lower
            th_dir = ""
            actual_th_name = th_name
            if is_installed:
                actual_th_name, th_dir = local_themes_lower[th_name_lower]

            info = self.catalog.get(th_name, {})
            if not info and actual_th_name in self.catalog:
                info = self.catalog[actual_th_name]

            is_fav = (th_name in self.favorites) or (actual_th_name in self.favorites)

            if self.current_tab == "installed":
                if not is_installed:
                    continue
            elif self.current_tab == "fav":
                if not is_fav:
                    continue

            items.append({
                'type': 'local' if is_installed else 'online',
                'theme_name': actual_th_name,
                'theme_dir': th_dir,
                'is_installed': is_installed,
                'info': info
            })

        self._all_theme_items = items
        self._pending_preview_tasks = []

        if not items and self.current_tab == "fav":
            empty_container = QWidget()
            vp_w = max(450, self.scroll_area.viewport().width() - 30)
            vp_h = max(320, self.scroll_area.viewport().height() - 40)
            empty_container.setMinimumSize(vp_w, vp_h)
            empty_layout = QVBoxLayout(empty_container)
            empty_layout.setAlignment(Qt.AlignCenter)
            empty_layout.setContentsMargins(0, 0, 0, 0)
            empty_layout.setSpacing(12)

            star_icon = QLabel()
            star_icon.setPixmap(create_star_pixmap(size=48, filled=False, outline_color="#FFB800", outline_width=2.5))
            star_icon.setAlignment(Qt.AlignCenter)
            star_icon.setStyleSheet("background: transparent;")

            empty_title = QLabel("No Favorite Cursors")
            empty_title.setFont(QFont('Segoe UI', 15, QFont.Bold))
            empty_title.setAlignment(Qt.AlignCenter)
            empty_title.setStyleSheet("color: #ffffff; background: transparent;")

            empty_desc = QLabel("Click the star icon on the top-left of any cursor pack\nto add it to your favorites.")
            empty_desc.setFont(QFont('Segoe UI', 12))
            empty_desc.setAlignment(Qt.AlignCenter)
            empty_desc.setStyleSheet("color: #888899; background: transparent;")

            empty_layout.addWidget(star_icon)
            empty_layout.addWidget(empty_title)
            empty_layout.addWidget(empty_desc)

            self.grid_layout.addWidget(empty_container)
            return

        self._rendered_count = 0
        self._render_next_chunk(24)

        if scroll_pos > 0:
            QTimer.singleShot(0, lambda pos=scroll_pos: self.scroll_area.verticalScrollBar().setValue(pos))
        else:
            self.scroll_area.verticalScrollBar().setValue(0)

        QTimer.singleShot(10, self._check_and_load_more_chunks)

    def _on_scroll_changed(self, val):
        self._schedule_viewport_check()
        sb = self.scroll_area.verticalScrollBar()
        if sb.maximum() > 0 and val >= sb.maximum() - 600:
            if self._rendered_count < len(self._all_theme_items):
                self._render_next_chunk(24)

    def _render_next_chunk(self, chunk_size=24):
        if self._rendered_count >= len(self._all_theme_items):
            return
        end_idx = min(self._rendered_count + chunk_size, len(self._all_theme_items))
        batch = self._all_theme_items[self._rendered_count:end_idx]
        self._rendered_count = end_idx

        self.grid_widget.setUpdatesEnabled(False)
        try:
            for item_data in batch:
                th_name = item_data['theme_name']
                th_dir = item_data['theme_dir']
                is_installed = item_data['is_installed']
                is_act = (self.selected_theme == th_name)
                is_fav = (th_name in self.favorites)

                card = CursorOptionFrame(
                    th_name, th_dir,
                    is_installed=is_installed,
                    is_active=is_act,
                    is_favorite=is_fav,
                    info=item_data.get('info')
                )
                card.favorite_toggled.connect(self._on_favorite_toggled)
                card.card_selected.connect(self._on_card_selected)

                if is_installed:
                    if th_name != "Windows Default":
                        card.uninstall_requested.connect(self._on_uninstall_theme)
                else:
                    card.download_requested.connect(self._on_download_theme)

                self.cards_map[th_name] = card
                self.grid_layout.addWidget(card)
        finally:
            self.grid_widget.setUpdatesEnabled(True)

        self.grid_widget.updateGeometry()
        self.grid_layout.invalidate()
        self._schedule_viewport_check()

        sb = self.scroll_area.verticalScrollBar()
        if sb.maximum() <= 0 and self._rendered_count < len(self._all_theme_items):
            QTimer.singleShot(10, self._check_and_load_more_chunks)

    def _on_favorite_toggled(self, theme_name: str, is_fav: bool):
        if is_fav:
            self.favorites.add(theme_name)
        else:
            self.favorites.discard(theme_name)
        self._save_favorites()

        if theme_name in self.cards_map:
            self.cards_map[theme_name].is_favorite = is_fav
            self.cards_map[theme_name].update_favorite_style()

        if self.current_tab == "fav" and not is_fav:
            self.refresh_list()

    def _on_preview_ready(self, theme_name: str, role_name: str, img: QImage):
        card = self.cards_map.get(theme_name)
        if card and not img.isNull():
            try:
                pix = QPixmap.fromImage(img)
                if role_name == "Arrow":
                    card.set_preview_pixmap(pix)
                else:
                    card.set_mini_preview_pixmap(role_name, pix)
            except RuntimeError:
                pass

    def _on_card_selected(self, theme_name: str):
        self.selected_theme = theme_name
        self.original_theme = theme_name

        for th, card in self.cards_map.items():
            card.set_active(th == theme_name)

        self._apply_theme_to_windows(theme_name)

    def _on_download_theme(self, theme_name: str):
        if theme_name in self.download_workers or theme_name in self._download_queue:
            return

        card = self.cards_map.get(theme_name)
        if card:
            card.is_downloading = True
            if hasattr(card, 'download_btn') and card.download_btn:
                card.download_btn.setText("\uE10C")
                card.download_btn.setEnabled(False)
                card.download_btn.setToolTip("Queued...")

        self._download_queue.append(theme_name)
        self._process_download_queue()

    def _process_download_queue(self):
        while self._active_download_count < self._max_concurrent_downloads and self._download_queue:
            theme_name = self._download_queue.popleft()
            file_list = self.catalog.get(theme_name, {}).get('files', [])
            if not file_list:
                continue

            card = self.cards_map.get(theme_name)
            if card and hasattr(card, 'download_btn') and card.download_btn:
                card.download_btn.setToolTip("Downloading...")

            target_dir = os.path.join(self.cursor_dir, theme_name)
            worker = DownloadThemeWorker(theme_name, file_list, target_dir)
            worker.download_finished.connect(self._on_download_completed)
            self.download_workers[theme_name] = worker
            self._active_download_count += 1
            worker.start()

    def _on_download_completed(self, theme_name: str, success: bool, msg: str):
        self._active_download_count = max(0, self._active_download_count - 1)
        self.download_workers.pop(theme_name, None)
        if success:
            target_dir = os.path.join(self.cursor_dir, theme_name)
            card = self.cards_map.get(theme_name)
            if card:
                card.set_installed_state(True, target_dir)
                try:
                    card.card_selected.disconnect()
                except (TypeError, RuntimeError):
                    pass
                card.card_selected.connect(self._on_card_selected)
                try:
                    card.uninstall_requested.disconnect()
                except (TypeError, RuntimeError):
                    pass
                card.uninstall_requested.connect(self._on_uninstall_theme)

            # Update in-memory item descriptor
            for it in self._all_theme_items:
                if it['theme_name'].lower() == theme_name.lower():
                    it['is_installed'] = True
                    it['theme_dir'] = target_dir
                    it['type'] = 'local'
                    break

            # Auto-apply smoothly
            self._on_card_selected(theme_name)
        else:
            card = self.cards_map.get(theme_name)
            if card:
                card.is_downloading = False
                if hasattr(card, 'download_btn') and card.download_btn:
                    card.download_btn.setText("\uE118")
                    card.download_btn.setEnabled(True)
                    card.download_btn.setToolTip("Download Cursor Pack")

        self._process_download_queue()

    def _on_uninstall_theme(self, theme_name: str):
        target_dir = os.path.join(self.cursor_dir, theme_name)
        try:
            if os.path.exists(target_dir):
                shutil.rmtree(target_dir, ignore_errors=True)

            # Check case-insensitive folder names on disk
            if os.path.exists(self.cursor_dir):
                for sub in os.listdir(self.cursor_dir):
                    if sub.lower() == theme_name.lower():
                        shutil.rmtree(os.path.join(self.cursor_dir, sub), ignore_errors=True)

            if self.selected_theme == theme_name or self.selected_theme.lower() == theme_name.lower():
                self.selected_theme = "Windows Default"
                self.original_theme = "Windows Default"
                self._apply_theme_to_windows("Windows Default")
                for th, c in self.cards_map.items():
                    c.set_active(th == "Windows Default")

            # Update in-memory item descriptor
            for it in self._all_theme_items:
                if it['theme_name'].lower() == theme_name.lower():
                    it['is_installed'] = False
                    it['theme_dir'] = ""
                    it['type'] = 'online'
                    break

            # Update card in-place to avoid any scrollbar jumping
            if self.current_tab in ("explore", "fav"):
                card = self.cards_map.get(theme_name)
                if card:
                    card.set_installed_state(False, "")
                    try:
                        card.download_requested.disconnect()
                    except (TypeError, RuntimeError):
                        pass
                    card.download_requested.connect(self._on_download_theme)
            elif self.current_tab == "installed":
                card = self.cards_map.pop(theme_name, None)
                if card:
                    if self.grid_layout.indexOf(card) != -1:
                        self.grid_layout.removeWidget(card)
                    card.deleteLater()
                    self.grid_widget.updateGeometry()
                    self.grid_layout.invalidate()

        except Exception as e:
            print(f"[CursorGalleryWidget] Error uninstalling theme '{theme_name}': {e}")

    def _on_download_all_clicked(self):
        if self.download_all_worker and self.download_all_worker.is_running():
            self.download_all_btn.setText("Stopping...")
            self.download_all_btn.setEnabled(False)
            self.download_all_worker.cancel()
            self.status_message_requested.emit("Cancelling download and cleaning up temporary files...")
            return

        if not self.catalog:
            self.status_message_requested.emit("Cursor catalog is still loading, please wait a moment...")
            return

        total_count = len(self.catalog)
        self.download_all_btn.setText(f"✕  Cancel (0/{total_count})")
        self.download_all_btn.setToolTip(f"Click to cancel download (0/{total_count})")
        self.download_all_btn.setProperty("cancelling", True)
        self.download_all_btn.style().unpolish(self.download_all_btn)
        self.download_all_btn.style().polish(self.download_all_btn)

        self.download_all_worker = DownloadAllCursorsWorker(self.catalog, self.cursor_dir)
        self.download_all_worker.progress_updated.connect(self._on_download_all_progress)
        self.download_all_worker.theme_downloaded.connect(self._on_download_all_theme_done)
        self.download_all_worker.all_finished.connect(self._on_download_all_finished)
        self.download_all_worker.cancelled.connect(self._on_download_all_cancelled)
        self.download_all_worker.start()

    def _on_download_all_progress(self, current: int, total: int, msg: str):
        self.download_all_btn.setText(f"✕  Cancel ({current}/{total})")
        self.download_all_btn.setToolTip(f"Click to cancel download ({current}/{total})\nCurrently: {msg}")
        self.status_message_requested.emit(f"Downloading cursors ({current}/{total}): {msg}")

    def _on_download_all_theme_done(self, theme_name: str, success: bool, target_dir: str):
        if success:
            card = self.cards_map.get(theme_name)
            if card:
                card.set_installed_state(True, target_dir)
                try:
                    card.card_selected.disconnect()
                except (TypeError, RuntimeError):
                    pass
                card.card_selected.connect(self._on_card_selected)
                try:
                    card.uninstall_requested.disconnect()
                except (TypeError, RuntimeError):
                    pass
                card.uninstall_requested.connect(self._on_uninstall_theme)

            for it in self._all_theme_items:
                if it['theme_name'].lower() == theme_name.lower():
                    it['is_installed'] = True
                    it['theme_dir'] = target_dir
                    it['type'] = 'local'
                    break

    def _on_download_all_cancelled(self, downloaded: int, total: int):
        self.status_message_requested.emit(f"Download cancelled ({downloaded}/{total} saved, incomplete files cleaned up)")
        self._reset_download_all_btn()

    def _on_download_all_finished(self, downloaded: int, skipped: int, errors: int, error_list: list):
        if errors == 0:
            msg = f"All cursors ready! ({downloaded} downloaded, {skipped} up to date)"
            self.download_all_btn.setText("\uE73E  Done")
        else:
            first_err = error_list[0] if error_list else "Network error"
            msg = f"Downloaded {downloaded} cursors ({skipped} up to date, {errors} errors): {first_err}"
            self.download_all_btn.setText(f"\uE783  {errors} Errors")
            self.download_all_btn.setToolTip("\n".join(error_list[:10]))
        self.status_message_requested.emit(msg)
        QTimer.singleShot(3500, self._reset_download_all_btn)

    def _reset_download_all_btn(self):
        self.download_all_btn.setEnabled(True)
        self.download_all_btn.setText("\uE118  Download All")
        self.download_all_btn.setToolTip("Download all cursor packs locally")
        self.download_all_btn.setProperty("cancelling", False)
        self.download_all_btn.style().unpolish(self.download_all_btn)
        self.download_all_btn.style().polish(self.download_all_btn)

    def _apply_theme_to_windows(self, theme_name: str) -> bool:
        self._pending_apply_theme = theme_name
        self._apply_debounce_timer.start(150)
        return True

    def _do_apply_pending_theme(self):
        theme_name = self._pending_apply_theme
        if not theme_name:
            return
        if theme_name == "Windows Default":
            threading.Thread(target=WindowsCursorManager.restore_default_cursors, daemon=True).start()
            return
        theme_path = os.path.join(self.cursor_dir, theme_name)
        if not os.path.exists(theme_path):
            return

        display_name, resolved_map, eff_dir = resolve_theme_directory_roles(theme_path)
        applied_name = display_name or theme_name

        role_map = {}
        for reg_key, _, _, _ in CURSOR_ROLES:
            if reg_key in resolved_map and eff_dir:
                role_map[reg_key] = os.path.abspath(os.path.join(eff_dir, resolved_map[reg_key]))
            else:
                role_map[reg_key] = ""

        threading.Thread(target=lambda: WindowsCursorManager.apply_cursor_theme(applied_name, role_map), daemon=True).start()

    @property
    def is_dirty(self):
        return False

    @is_dirty.setter
    def is_dirty(self, val):
        pass

    def save_selection(self):
        """Commits the currently selected cursor theme."""
        self._pending_apply_theme = self.selected_theme
        self._do_apply_pending_theme()
        self.original_theme = self.selected_theme

    def revert_selection(self):
        """Cursors apply immediately on pick and do not require revert on discard."""
        pass


