import os
import re
import sys
import json
import hashlib
from PyQt5.QtWidgets import (QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, 
                             QScrollArea, QFrame, QLineEdit, QFileDialog, QComboBox, 
                             QCheckBox, QRadioButton, QGridLayout, QButtonGroup, QListWidget,
                             QListWidgetItem, QSizePolicy, QDialog, QFormLayout, 
                             QGraphicsDropShadowEffect, QTabWidget, QLayout, QListView,
                             QStyledItemDelegate, QStyle, QAbstractItemView, QTextEdit, QFileIconProvider)
from PyQt5.QtGui import QColor, QFont, QPainter, QPainterPath, QPen, QIcon, QPixmap, QFontDatabase, QFontMetrics, QImage
from PyQt5.QtCore import Qt, pyqtSignal, QSize, QEvent, QPoint, QPointF, QRect, QRectF, QTimer, QObject, QAbstractListModel, QModelIndex, QFileInfo
try: from PyQt5 import QtSvg
except ImportError: QtSvg = None
from utils import resource_path, UnsavedChangesDialog, safe_file_write, get_font_icon, get_mdl2_icon, NILESOFT_FONT_FAMILY, _init_nilesoft_font
from theme_editor_widget import MinimalColorPickerDialog

# Global path storage to be set by launcher.pyw
PROJECT_ROOT = None

def set_project_root(root):
    global PROJECT_ROOT
    PROJECT_ROOT = root

DEFAULT_IDS = [
    "id.add_a_network_location", "id.align_icons_to_grid", "id.arrange_by", "id.auto_arrange_icons",
    "id.autoplay", "id.cancel", "id.cascade_windows", "id.cast_to_device", "id.cleanup", "id.collapse",
    "id.collapse_all_groups", "id.collapse_group", "id.configure", "id.content", "id.control_panel",
    "id.copy_as_path", "id.copy_here", "id.copy_to", "id.copy_to_folder", "id.cortana",
    "id.create_shortcuts_here", "id.customize_notification_icons", "id.customize_this_folder",
    "id.desktop", "id.details", "id.device_manager", "id.disconnect", "id.disconnect_network_drive",
    "id.erase_this_disc", "id.expand", "id.expand_all_groups", "id.expand_group", "id.extra_large_icons",
    "id.folder_options", "id.give_access_to", "id.group_by", "id.include_in_library",
    "id.insert_unicode_control_character", "id.large_icons", "id.list", "id.lock_all_taskbars",
    "id.lock_the_taskbar", "id.make_available_offline", "id.make_available_online", "id.manage",
    "id.map_as_drive", "id.map_network_drive", "id.medium_icons", "id.merge", "id.more_options",
    "id.move_here", "id.move_to", "id.move_to_folder", "id.new", "id.new_item", "id.news_and_interests",
    "id.next_desktop_background", "id.open", "id.open_as_portable", "id.open_autoplay",
    "id.open_in_new_process", "id.open_in_new_tab", "id.open_in_new_window", "id.open_new_tab",
    "id.open_new_window", "id.paste_shortcut", "id.play", "id.power_options", "id.print",
    "id.reconversion", "id.redo", "id.remove_properties", "id.restore_default_libraries",
    "id.restore_previous_versions", "id.rotate_left", "id.rotate_right", "id.run",
    "id.run_as_another_user", "id.search", "id.select_all", "id.share", "id.share_with",
    "id.shield", "id.show_cortana_button", "id.show_desktop_icons", "id.show_libraries",
    "id.show_network", "id.show_pen_button", "id.show_people_on_the_taskbar", "id.show_task_view_button",
    "id.show_the_desktop", "id.show_this_pc", "id.show_touch_keyboard_button", "id.show_touchpad_button",
    "id.show_windows_stacked", "id.small_icons", "id.sort_by", "id.store", "id.tiles",
    "id.troubleshoot_compatibility", "id.turn_off_bitlocker", "id.turn_on_bitlocker", "id.undo", "id.view"
]



class NSSCacheManager:
    CACHE_FILE = None
    _cache = {}
    @classmethod
    def init(cls, project_root):
        cls.CACHE_FILE = os.path.join(project_root, 'imports', '.nss_cache.json')
        if os.path.exists(cls.CACHE_FILE):
            try:
                with open(cls.CACHE_FILE, 'r', encoding='utf-8') as f: cls._cache = json.load(f)
            except: cls._cache = {}
    @classmethod
    def save(cls):
        if not cls.CACHE_FILE: return
        try:
            os.makedirs(os.path.dirname(cls.CACHE_FILE), exist_ok=True)
            safe_file_write(cls.CACHE_FILE, json.dumps(cls._cache))
        except: pass
    @classmethod
    def get_file_hash(cls, fp):
        try:
            with open(fp, 'rb') as f: return hashlib.md5(f.read()).hexdigest()
        except: return None
    @classmethod
    def get_items(cls, fp):
        h = cls.get_file_hash(fp)
        if fp in cls._cache and cls._cache[fp].get('hash') == h: return cls._cache[fp].get('items')
        return None
    @classmethod
    def set_items(cls, fp, items):
        h = cls.get_file_hash(fp)
        cls._cache[fp] = {'hash': h, 'items': items}

KEY_TOGGLE_ICONS = {
    'Hide': (0xED1A, 'Hide'),
    'Normal': (0xE73E, 'Normal'),
    'Shift': (0xE752, 'Shift'),
    'Ctrl': (0xE765, 'Ctrl'),
    'Caps': (0xE8E8, 'Caps'),
    'LMB': (0xE962, 'LMB'),
}

class KeyToggleButton(QPushButton):
    stateChanged = pyqtSignal(int)
    def __init__(self, label, parent=None):
        super().__init__(parent)
        icon_code, self._label = KEY_TOGGLE_ICONS.get(label, (0xE73E, label))
        glyph = chr(icon_code)
        self.setText(f"{glyph}\n{self._label}")
        self.setFont(QFont('Segoe MDL2 Assets', 10))
        self.setCheckable(True)
        self.setFixedSize(50, 40)
        self.setCursor(Qt.PointingHandCursor)
        self._update_style()
        self.toggled.connect(self._on_toggled)
    def _on_toggled(self, checked):
        self._update_style()
        self.stateChanged.emit(2 if checked else 0)
    def _update_style(self):
        if self.isChecked():
            self.setStyleSheet("QPushButton { background: rgba(220, 20, 60, 0.2); border: 1px solid rgba(220, 20, 60, 0.5); border-radius: 10px; color: #dc143c; font-size: 10px; padding: 2px; } QPushButton:hover { background: rgba(220, 20, 60, 0.3); }")
        else:
            self.setStyleSheet("QPushButton { background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 10px; color: #333333; font-size: 10px; padding: 2px; } QPushButton:hover { background: rgba(255, 255, 255, 0.1); color: #b0b0b0; }")
    def isChecked(self):
        return super().isChecked()
    def setChecked(self, val):
        super().setChecked(val)
        self._update_style()
    def setEnabled(self, val):
        super().setEnabled(val)
        if not val:
            self.setStyleSheet("QPushButton { background: rgba(220, 20, 60, 0.15); border: 1px solid rgba(220, 20, 60, 0.3); border-radius: 10px; color: rgba(220, 20, 60, 0.6); font-size: 10px; padding: 2px; }")
    def paintEvent(self, event):
        from PyQt5.QtGui import QPainter, QFont as QF
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        icon_code = KEY_TOGGLE_ICONS.get(self._label, (0xE73E, ''))[0]
        glyph = chr(icon_code)
        c = QColor('#dc143c') if self.isChecked() else QColor('#333333')
        if not self.isEnabled(): c = QColor(220, 20, 60, 153)
        if self.underMouse() and self.isEnabled(): c = c.lighter(130)
        painter.setPen(c)
        icon_font = QF('Segoe MDL2 Assets', 12)
        icon_font.setWeight(QF.Bold)
        painter.setFont(icon_font)
        painter.drawText(self.rect().adjusted(0, 3, 0, -14), Qt.AlignHCenter | Qt.AlignTop, glyph)
        label_font = QF('Segoe UI Variable Display', 8)
        label_font.setWeight(QF.DemiBold)
        painter.setFont(label_font)
        painter.drawText(self.rect().adjusted(0, 22, 0, 0), Qt.AlignHCenter | Qt.AlignTop, self._label)
        painter.end()

class VisibilityWidget(QWidget):
    valueChanged = pyqtSignal(str)
    def __init__(self, parent=None):
        super().__init__(parent)
        self._updating = False
        self._custom_vis = ""
        self._user_modified = False
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        
        self.btn_hide = KeyToggleButton("Hide")
        self.btn_normal = KeyToggleButton("Normal")
        self.btn_shift = KeyToggleButton("Shift")
        self.btn_ctrl = KeyToggleButton("Ctrl")
        self.btn_caps = KeyToggleButton("Caps")
        self.btn_lmb = KeyToggleButton("LMB")
        
        self.buttons = {
            'hide': self.btn_hide,
            'normal': self.btn_normal,
            'shift': self.btn_shift,
            'ctrl': self.btn_ctrl,
            'caps': self.btn_caps,
            'lmb': self.btn_lmb,
        }
        
        for key, btn in self.buttons.items():
            layout.addWidget(btn)
            btn.toggled.connect(lambda checked, k=key: self._on_btn_toggled(k, checked))
            
        self.set_value("")

    def _on_btn_toggled(self, key, checked):
        if self._updating:
            return
        self._updating = True
        self._user_modified = True
        if checked:
            for k, btn in self.buttons.items():
                if k != key:
                    btn.setChecked(False)
        else:
            if not any(btn.isChecked() for btn in self.buttons.values()):
                self.btn_normal.setChecked(True)
        self._updating = False
        self.valueChanged.emit(self.get_value())

    def get_value(self):
        if self.btn_hide.isChecked():
            return "vis.remove"
        if self.btn_shift.isChecked():
            return "key.shift()"
        if self.btn_ctrl.isChecked():
            return "key.control()"
        if self.btn_caps.isChecked():
            return "key.capslock()"
        if self.btn_lmb.isChecked():
            return "key.lbutton()"
        if not self._user_modified and self._custom_vis:
            return self._custom_vis
        return ""

    def set_value(self, vis_str):
        self._updating = True
        self._user_modified = False
        self._custom_vis = ""
        raw_str = str(vis_str or '').strip()
        clean_vis = raw_str.strip('\'" ').lower()
        
        if clean_vis in ('key.remove', 'vis.remove', 'key.hidden', 'vis.hidden', 'remove', 'hidden', '0'):
            for k, btn in self.buttons.items():
                btn.setChecked(k == 'hide')
        elif clean_vis in ('key.shift()', 'vis.shift', 'shift', 'key.shift'):
            for k, btn in self.buttons.items():
                btn.setChecked(k == 'shift')
        elif clean_vis in ('key.control()', 'key.ctrl()', 'vis.control', 'vis.ctrl', 'control', 'ctrl', 'key.control', 'key.ctrl'):
            for k, btn in self.buttons.items():
                btn.setChecked(k == 'ctrl')
        elif clean_vis in ('key.capslock()', 'key.caps()', 'vis.capslock', 'vis.caps', 'capslock', 'caps', 'key.capslock', 'key.caps'):
            for k, btn in self.buttons.items():
                btn.setChecked(k == 'caps')
        elif clean_vis in ('key.lbutton()', 'key.lmb()', 'vis.lbutton', 'vis.lmb', 'lbutton', 'lmb', 'key.lbutton'):
            for k, btn in self.buttons.items():
                btn.setChecked(k == 'lmb')
        elif clean_vis in ('', 'normal', 'vis.normal', '1', 'vis.visible', 'visible', 'always visible'):
            for k, btn in self.buttons.items():
                btn.setChecked(k == 'normal')
        else:
            self._custom_vis = raw_str
            for k, btn in self.buttons.items():
                btn.setChecked(k == 'normal')
        self._updating = False

TYPE_PRESETS = [
    ('all', 'All'),
    ('desktop', 'Desktop'),
    ('taskbar', 'Taskbar'),
    ('computer', 'This PC'),
    ('recyclebin', 'Recycle Bin'),
    ('back', 'Background'),
    ('dir', 'Folders'),
    ('file', 'Files'),
]

class TypeWidget(QWidget):
    valueChanged = pyqtSignal(str)
    def __init__(self, parent=None):
        super().__init__(parent)
        self._updating = False
        self.preset_checkboxes = {}
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(4)
        
        # Grid of checkboxes for presets
        grid_w = QWidget()
        grid_lay = QGridLayout(grid_w)
        grid_lay.setContentsMargins(0, 0, 0, 0)
        grid_lay.setSpacing(8)
        
        cb_style = """
            QCheckBox {
                color: #ffffff;
                font-size: 12px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border-radius: 4px;
                border: 1px solid #45475a;
                background: #2a2a30;
            }
            QCheckBox::indicator:checked {
                background: #dc143c;
                border: 1px solid #dc143c;
            }
        """
        
        for i, (val, friendly) in enumerate(TYPE_PRESETS):
            cb = QCheckBox(friendly)
            cb.setStyleSheet(cb_style)
            cb.setProperty("type_val", val)
            cb.setCursor(Qt.PointingHandCursor)
            self.preset_checkboxes[val] = cb
            row = i // 4
            col = i % 4
            grid_lay.addWidget(cb, row, col)
            cb.toggled.connect(self._on_cb_toggled)
            
        main_layout.addWidget(grid_w)
        
        # Set default state
        self.set_value("")

    def _on_cb_toggled(self, checked):
        if self._updating:
            return
        sender = self.sender()
        val = sender.property("type_val")
        self._updating = True
        if val == "all":
            if checked:
                for k, cb in self.preset_checkboxes.items():
                    if k != "all":
                        cb.setChecked(False)
            else:
                if not any(cb.isChecked() for k, cb in self.preset_checkboxes.items() if k != "all"):
                    self.preset_checkboxes["all"].setChecked(True)
        else:
            if checked:
                self.preset_checkboxes["all"].setChecked(False)
            else:
                if not any(cb.isChecked() for k, cb in self.preset_checkboxes.items() if k != "all"):
                    self.preset_checkboxes["all"].setChecked(True)
        self._updating = False
        self._on_state_changed()

    def _on_state_changed(self):
        if self._updating:
            return
        self.valueChanged.emit(self.get_value())

    def get_value(self):
        if self.preset_checkboxes["all"].isChecked():
            return ""
        parts = []
        for val, _ in TYPE_PRESETS:
            if val != "all" and self.preset_checkboxes[val].isChecked():
                parts.append(val)
        if not parts:
            return ""
        return "|".join(parts)

    def set_value(self, val_str):
        self._updating = True
        val_str = str(val_str or '').strip('\'" ')
        
        if not val_str:
            for k, cb in self.preset_checkboxes.items():
                cb.setChecked(k == "all")
            self._updating = False
            return
            
        items = [i.strip().lower() for i in val_str.split('|') if i.strip()]
        preset_vals = set(items)
                
        if not (preset_vals & set(p[0] for p in TYPE_PRESETS if p[0] != 'all')):
            for k, cb in self.preset_checkboxes.items():
                cb.setChecked(k == "all")
        else:
            self.preset_checkboxes["all"].setChecked(False)
            for k, cb in self.preset_checkboxes.items():
                if k != "all":
                    cb.setChecked(k in preset_vals)
                    
        self._updating = False

def _fuzzy_match(query, text):
    if not query: return True
    if not text: return False
    q_idx = 0
    for char in text:
        if char == query[q_idx]:
            q_idx += 1
            if q_idx == len(query): return True
    return False

def calculate_search_score(query, item):
    if not query:
        return True, 0
    
    q = query.strip().lower()
    if not q:
        return True, 0
        
    props = item.get('props', {})
    title = str(props.get('title', '')).strip('\'" ').lower()
    find = str(props.get('find', '')).strip('\'" ').lower()
    file_name = os.path.basename(item.get('file', '')).replace('.nss', '').lower()
    in_menu = str(props.get('in', '')).strip('\'" ').lower()
    cmd = str(props.get('cmd', '')).strip('\'" ').lower()
    tip = str(props.get('tip', '')).strip('\'" ').lower()
    item_type = str(item.get('type', '')).lower()
    
    score = 0
    
    # 1. Primary Title / Find Exact match
    if title == q or find == q:
        score = max(score, 1000)
    elif title.startswith(q) or find.startswith(q):
        score = max(score, 800)
    elif any(w.startswith(q) for w in title.split()) or any(w.startswith(q) for w in find.split()):
        score = max(score, 650)
    elif q in title or q in find:
        score = max(score, 500)
        
    # 2. File name match
    if file_name == q:
        score = max(score, 450)
    elif file_name.startswith(q):
        score = max(score, 400)
    elif q in file_name:
        score = max(score, 350)
        
    # 3. in_menu / tip match
    if q in in_menu or q in tip:
        score = max(score, 300)
        
    # 4. Command match (only check basename or clean command, not huge paths)
    if q in cmd:
        score = max(score, 200)
        
    # 5. Type match (e.g. searching 'menu' or 'item' or 'file')
    if q == item_type:
        score = max(score, 150)
        
    # 6. Fallback fuzzy match on title or find (only if query is at least 2 chars)
    if score == 0 and len(q) >= 2:
        if title and _fuzzy_match(q, title):
            score = max(score, 100 - max(0, len(title) - len(q)))
        elif find and _fuzzy_match(q, find):
            score = max(score, 90 - max(0, len(find) - len(q)))
        elif file_name and _fuzzy_match(q, file_name):
            score = max(score, 80 - max(0, len(file_name) - len(q)))
            
    return (score > 0), score

class NSSItemModel(QAbstractListModel):
    def __init__(self, items=None, parent=None):
        super().__init__(parent); self._items = items or []; self._filtered_items = self._items[:]
    def rowCount(self, parent=QModelIndex()): return len(self._filtered_items)
    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or role != Qt.UserRole: return None
        return self._filtered_items[index.row()]
    def set_items(self, items):
        self.beginResetModel(); self._items = items; self._filtered_items = items[:]; self.endResetModel()
    def filter(self, text, file_filter=None, type_tag=None, action_tag=None):
        self.beginResetModel()
        t = (text or '').strip().lower()
        scored_items = []
        for i in self._items:
            # 1. File filter check
            if file_filter and i.get('file') != file_filter:
                continue
            
            # 2. Type filter check (All, Item, Menu, Modify)
            if type_tag and type_tag != "All":
                tt = type_tag.lower()
                if i.get('type', '').lower() != tt:
                    continue
            
            # 3. Action/Property filter check
            props = i.get('props', {})
            if action_tag and action_tag != "All":
                at = action_tag.lower()
                has_tag = False
                if at == "renamed":
                    has_tag = bool(props.get('title'))
                elif at == "icons":
                    has_tag = bool(props.get('icon') or props.get('image'))
                elif at == "hidden": 
                    v = str(props.get('vis', '')).lower()
                    has_tag = v in ('vis.remove', 'vis.hidden', 'remove', 'hidden')
                elif at == "part hidden":
                    v = str(props.get('vis', '')).lower()
                    has_tag = v != '' and v != 'normal' and v not in ('vis.remove', 'vis.hidden', 'remove', 'hidden')
                elif at == "moved":
                    has_tag = bool(props.get('menu'))
                elif at == "position":
                    has_tag = bool(props.get('pos'))
                elif at == "separator":
                    has_tag = bool(props.get('sep'))
                elif at == "modified":
                    has_tag = any(k in props for k in ('title', 'icon', 'image', 'vis', 'menu', 'pos', 'sep'))
                
                if not has_tag:
                    continue
            
            # 4. Text search check with relevance scoring
            if not t:
                scored_items.append((0, i))
            else:
                matched, score = calculate_search_score(t, i)
                if matched:
                    scored_items.append((score, i))
                    
        if t:
            scored_items.sort(key=lambda x: (-x[0], x[1].get('type') != 'menu', str(x[1].get('props', {}).get('title', '')).lower()))
            
        self._filtered_items = [it for _, it in scored_items]
        self.endResetModel()

class NSSItemDelegate(QStyledItemDelegate):
    def __init__(self, parent=None): 
        super().__init__(parent); self._hover_row = -1; self._hover_btn = -1 # 0:del, 1:edit
    def sizeHint(self, opt, index): return QSize(opt.rect.width(), 100)
    def _get_mw_and_view(self, opt):
        p = self.parent()
        while p and not isinstance(p, QAbstractItemView): p = p.parent()
        view = p; mw = p.parent() if p else None
        while mw and not (hasattr(mw, 'edit_rule') or hasattr(mw, 'edit_item')): mw = mw.parent()
        return mw, view
    def paint(self, painter, opt, index):
        data = index.data(Qt.UserRole); painter.save(); painter.setRenderHint(QPainter.Antialiasing)
        rect = opt.rect.adjusted(12, 6, -12, -6); is_hover = (opt.state & QStyle.State_MouseOver)
        painter.setPen(Qt.NoPen); bg = QColor("#2a2a30") if is_hover else QColor("#121212")
        bg.setAlpha(200 if is_hover else 140); painter.setBrush(bg); painter.drawRoundedRect(rect, 16, 16)
        if is_hover: painter.setPen(QPen(QColor(220, 20, 60, 120), 1.5)); painter.drawRoundedRect(rect, 16, 16)
        
        ty, props = data.get('type', 'item'), data.get('props', {})
        val = props.get('image') or props.get('icon') or ''
        codes = _extract_glyph_codes(val); colors = _extract_all_colors(val)
        
        # Icon Area
        icon_rect = QRect(rect.x() + 18, rect.y() + 18, 52, 52)
        painter.setBrush(QColor(255,255,255,15)); painter.drawRoundedRect(icon_rect, 14, 14)
        
        svg_content = _extract_svg_content(val)
        has_icon = False
        if svg_content and QtSvg:
            try:
                clean_svg = svg_content.replace("@image.color1", "#ffffff").replace("@image.color2", "#ffffff").replace("@color3", "#ffffff")
                renderer = QtSvg.QSvgRenderer(clean_svg.encode('utf-8'))
                if renderer.isValid():
                    sz = renderer.defaultSize()
                    w = sz.width() if sz.width() > 0 else 24
                    h = sz.height() if sz.height() > 0 else 24
                    pm = QPixmap(w * 4, h * 4); pm.fill(Qt.transparent)
                    p_svg = QPainter(pm); p_svg.setRenderHint(QPainter.Antialiasing); renderer.render(p_svg); p_svg.end()
                    scaled_pm = pm.scaled(icon_rect.width() - 12, icon_rect.height() - 12, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    target_r = QRect((icon_rect.width() - scaled_pm.width())//2 + icon_rect.x(), (icon_rect.height() - scaled_pm.height())//2 + icon_rect.y(), scaled_pm.width(), scaled_pm.height())
                    painter.drawPixmap(target_r, scaled_pm)
                    has_icon = True
            except: pass

        if not has_icon and codes:
            theme_cs = _get_theme_glyph_colors()
            painter.setFont(QFont(NILESOFT_FONT_FAMILY, 28))
            c1 = colors[0] if len(colors) > 0 else theme_cs[0]
            painter.setPen(QColor(c1 or theme_cs[0]))
            painter.drawText(icon_rect, Qt.AlignCenter, chr(codes[0]))
            if len(codes) > 1:
                c2 = colors[1] if len(colors) > 1 else theme_cs[1]
                painter.setPen(QColor(c2 or theme_cs[1]))
                painter.drawText(icon_rect, Qt.AlignCenter, chr(codes[1]))
            has_icon = True
            
        if not has_icon:
            # Try to load as image
            path, clr = _extract_img_path_and_color(val)
            if not path: path = val.strip('\'" ')
            cmd_val = props.get('cmd') or props.get('path') or props.get('find') or ''
            res_path = _resolve_app_dir_path(path)
            if (not res_path or not os.path.exists(res_path)) and cmd_val:
                m = re.search(r'([a-zA-Z]:[\\/][^"\'\n\r\t]+?\.(?:exe|ico|dll))', str(cmd_val), re.I)
                if m and os.path.exists(m.group(1)):
                    res_path = m.group(1)
                elif os.path.exists(str(cmd_val).strip('\'" ')):
                    res_path = str(cmd_val).strip('\'" ')

            if (not res_path or not os.path.exists(res_path)) and data.get('file'):
                alt = os.path.join(os.path.dirname(data['file']), path)
                if os.path.exists(alt): res_path = alt
            
            if res_path and os.path.exists(res_path):
                pm = QPixmap()
                if res_path.lower().endswith('.svg') and QtSvg:
                    try:
                        renderer = QtSvg.QSvgRenderer(res_path)
                        if renderer.isValid():
                            pm = QPixmap(128, 128); pm.fill(Qt.transparent)
                            p_svg = QPainter(pm); renderer.render(p_svg); p_svg.end()
                    except: pass
                if pm.isNull():
                    try:
                        with open(res_path, 'rb') as f: data_b = f.read()
                        pm.loadFromData(data_b)
                    except: pass
                if pm.isNull():
                    provider = QFileIconProvider()
                    icon = provider.icon(QFileInfo(res_path))
                    if not icon.isNull():
                        pm = icon.pixmap(128, 128)
                    if pm.isNull():
                        icon = QIcon(res_path)
                        pm = icon.pixmap(128, 128)
                
                if not pm.isNull():
                    if clr:
                        img = pm.toImage().convertToFormat(QImage.Format_ARGB32); c = QColor(clr)
                        for y in range(img.height()):
                            for x in range(img.width()):
                                p = img.pixelColor(x, y)
                                if p.alpha() > 0: c.setAlpha(p.alpha()); img.setPixelColor(x, y, c)
                        pm = QPixmap.fromImage(img)
                    painter.drawPixmap(icon_rect.adjusted(4, 4, -4, -4), pm.scaled(icon_rect.width() - 8, icon_rect.height() - 8, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                    has_icon = True
        
        if not has_icon:
            painter.setPen(QColor(255,255,255,30)); painter.setFont(QFont("Segoe MDL2 Assets", 22))
            painter.drawText(icon_rect, Qt.AlignCenter, "\uE701" if ty == "menu" else "\uE8B7")
            
        # Title Syntax Highlighting
        tx = rect.x() + 85; ty = rect.y() + 38
        f_bold = QFont("Inter", 12, QFont.Bold); f_small = QFont("Inter", 10); f_italic = QFont("Inter", 10, -1, True)
        fm_b = QFontMetrics(f_bold); fm_s = QFontMetrics(f_small); fm_i = QFontMetrics(f_italic)
        
        def draw_part(text, clr, font):
            nonlocal tx
            painter.setFont(font); painter.setPen(QColor(clr))
            painter.drawText(tx, ty, text)
            tx += (fm_b if font.bold() else fm_s).horizontalAdvance(text)
            
        if data.get('type') == 'modify':
            if props.get('find'):
                draw_part("Modify: ", "#dc143c", f_bold)
                draw_part(props['find'].strip(chr(39)+chr(34)), "#ffffff", f_bold)
                if props.get('title'):
                    draw_part(" \u2192 ", "#A0A0A0", f_small)
                    draw_part(props['title'].strip(chr(39)+chr(34)), "#dc143c", f_bold)
            elif props.get('type'):
                draw_part(f"All {props['type'].title()}s", "#dc143c", f_bold)
                if props.get('title'):
                    draw_part(" \u2192 ", "#A0A0A0", f_small)
                    draw_part(props['title'].strip(chr(39)+chr(34)), "#dc143c", f_bold)
            else:
                draw_part("Global Rule", "#dc143c", f_bold)
        else:
            # item or menu - show title
            t_str = props.get('title', props.get('find', 'Unnamed')).strip(chr(39)+chr(34))
            file_name = os.path.basename(data.get('file', ''))
            label = f"{file_name}: " if file_name else ""
            draw_part(label, "#dc143c", f_bold)
            draw_part(t_str, "#ffffff", f_bold)
            
        if props.get('in'):
            draw_part(" in ", "#A0A0A0", f_small)
            draw_part(props['in'].strip(chr(39)+chr(34)), "#ff2a55", f_bold)
        
        # Badges / Summary
        bx = rect.x() + 85; by = rect.y() + 48; acts = []
        if props.get('title'): acts.append(("Renamed", "#808080"))
        if props.get('icon') or props.get('image'): acts.append(("Icons", "#4A90E2"))
        v = props.get('vis', '').lower()
        if v in ('vis.remove', 'vis.hidden', 'remove', 'hidden'): acts.append(("Hidden", "#dc143c"))
        elif v and v != 'normal': acts.append(("Part Hidden", "#9B59B6"))
        elif v: acts.append((f"Vis: {v}", "#dc143c"))
        if props.get('menu'): acts.append(("Moved", "#E29E4A"))
        if props.get('pos'): acts.append((f"Pos: {props['pos']}", "#4AE290"))
        if props.get('sep'): acts.append(("Separator", "#F1C40F"))
        
        painter.setFont(QFont("Inter", 8, QFont.Bold))
        for txt, clr in acts:
            tw = painter.fontMetrics().horizontalAdvance(txt) + 12
            painter.setBrush(QColor(clr)); painter.setPen(Qt.NoPen)
            br = QRect(bx, by, tw, 18); painter.drawRoundedRect(br, 9, 9)
            painter.setPen(QColor("#000000"))
            painter.drawText(br.adjusted(-1, -1, -1, -1), Qt.AlignCenter, txt)
            painter.drawText(br.adjusted(1, -1, 1, -1), Qt.AlignCenter, txt)
            painter.drawText(br.adjusted(-1, 1, -1, 1), Qt.AlignCenter, txt)
            painter.drawText(br.adjusted(1, 1, 1, 1), Qt.AlignCenter, txt)
            painter.setPen(QColor("#ffffff")); painter.drawText(br, Qt.AlignCenter, txt)
            bx += tw + 6
            
        # Source / File
        fp = data.get('file', 'modify.nss'); src = os.path.basename(fp)
        painter.setPen(QColor("#A0A0A0")); painter.setFont(QFont("Inter", 9))
        painter.drawText(rect.x() + 85, rect.y() + 82, f"Source: {src}")
        
        # Buttons Area (Right)
        if is_hover:
            is_local = src.lower() == 'modify.nss'
            btn_x = rect.right() - 45; btn_y = rect.y() + (rect.height() - 36) // 2
            btns = [("\uE107", "#dc143c")] if is_local else [] # Delete (only for local)
            btns.append(("\uE104", "#dc143c")) # Edit
            
            for i, (icon, clr) in enumerate(btns):
                br = QRect(btn_x, btn_y, 36, 36)
                is_btn_hover = (self._hover_btn == (0 if is_local and i == 0 else 1))
                painter.setBrush(QColor(clr) if is_btn_hover else QColor(255,255,255,10))
                painter.setPen(Qt.NoPen); painter.drawEllipse(br)
                painter.setPen(QColor("#ffffff") if is_btn_hover else QColor(clr))
                painter.setFont(QFont("Segoe MDL2 Assets", 14)); painter.drawText(br, Qt.AlignCenter, icon)
                btn_x -= 42
        painter.restore()

    def editorEvent(self, event, model, opt, index):
        if event.type() in (QEvent.MouseMove, QEvent.MouseButtonRelease):
            rect = opt.rect; pos = event.pos(); data = index.data(Qt.UserRole)
            is_local = os.path.basename(data.get('file', '')).lower() == 'modify.nss'
            btn_x = rect.right() - 45; btn_y = rect.y() + (rect.height() - 36) // 2
            
            del_rect = QRect(btn_x, btn_y, 36, 36) if is_local else QRect(-1, -1, 0, 0)
            edit_rect = QRect(btn_x - (42 if is_local else 0), btn_y, 36, 36)
            
            if event.type() == QEvent.MouseMove:
                old = self._hover_btn
                if del_rect.contains(pos): self._hover_btn = 0
                elif edit_rect.contains(pos): self._hover_btn = 1
                else: self._hover_btn = -1
                if old != self._hover_btn:
                    _, view = self._get_mw_and_view(opt)
                    if view: view.update(index)
                return True
            
            if event.type() == QEvent.MouseButtonRelease:
                mw, _ = self._get_mw_and_view(opt)
                if not mw: return False
                if del_rect.contains(pos): mw.delete_rule(data); return True
                if edit_rect.contains(pos) or rect.contains(pos):
                    if hasattr(mw, 'edit_rule'): mw.edit_rule(data)
                    elif hasattr(mw, 'edit_item'): mw.edit_item(data)
                    return True
        return super().editorEvent(event, model, opt, index)

class NonScrollComboBox(QComboBox):
    def __init__(self, parent=None): super().__init__(parent); self.setFocusPolicy(Qt.StrongFocus)
    def wheelEvent(self, e): e.ignore()

class CustomMessageBox(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent); self.setWindowTitle("Message"); self.setFixedSize(350, 180); self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint); self.setAttribute(Qt.WA_TranslucentBackground); self.layout = QVBoxLayout(self); self.frame = QFrame(); self.frame.setStyleSheet("QFrame { background-color: #121212; border: 1px solid #2a2a30; border-radius: 15px; }"); self.layout.addWidget(self.frame); self.content_layout = QVBoxLayout(self.frame); self.title_label = QLabel("Title"); self.title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: white; border: none;"); self.msg_label = QLabel(""); self.msg_label.setWordWrap(True); self.msg_label.setStyleSheet("color: #b0b0b0; border: none;"); self.ok_btn = QPushButton("OK"); self.ok_btn.setFixedSize(80, 32); self.ok_btn.setStyleSheet("QPushButton { background-color: #dc143c; color: #ffffff; border-radius: 8px; font-weight: bold; } QPushButton:hover { background-color: #dc143c; }"); self.ok_btn.clicked.connect(self.accept); self.content_layout.addWidget(self.title_label); self.content_layout.addWidget(self.msg_label); self.content_layout.addWidget(self.ok_btn, 0, Qt.AlignRight)
    def setText(self, text): self.title_label.setText(text)
    def setInformativeText(self, text): self.msg_label.setText(text)

class FlowLayout(QLayout):
    def __init__(self, parent=None, margin=0, spacing=-1):
        super(FlowLayout, self).__init__(parent); self.setContentsMargins(margin, margin, margin, margin) if parent else None; self.setSpacing(spacing); self.itemList = []
    def addItem(self, item): self.itemList.append(item)
    def count(self): return len(self.itemList)
    def itemAt(self, index): return self.itemList[index] if 0 <= index < len(self.itemList) else None
    def takeAt(self, index): return self.itemList.pop(index) if 0 <= index < len(self.itemList) else None
    def expandingDirections(self): return Qt.Orientations(Qt.Orientation(0))
    def hasHeightForWidth(self): return True
    def heightForWidth(self, width): return self.doLayout(QRect(0, 0, width, 0), True)
    def setGeometry(self, rect): super(FlowLayout, self).setGeometry(rect); self.doLayout(rect, False)
    def sizeHint(self): return self.minimumSize()
    def minimumSize(self):
        size = QSize()
        for item in self.itemList:
            if item.widget().isHidden(): continue
            size = size.expandedTo(item.minimumSize())
        size += QSize(2 * self.contentsMargins().top(), 2 * self.contentsMargins().top()); return size
    def doLayout(self, rect, testOnly):
        x, y, lineHeight = rect.x(), rect.y(), 0
        for item in self.itemList:
            wid = item.widget()
            if wid.isHidden(): continue
            spaceX = self.spacing() + wid.style().layoutSpacing(QSizePolicy.PushButton, QSizePolicy.PushButton, Qt.Horizontal)
            spaceY = self.spacing() + wid.style().layoutSpacing(QSizePolicy.PushButton, QSizePolicy.PushButton, Qt.Vertical); nextX = x + item.sizeHint().width() + spaceX
            if nextX - spaceX > rect.right() and lineHeight > 0: x, y = rect.x(), y + lineHeight + spaceY; nextX, lineHeight = x + item.sizeHint().width() + spaceX, 0
            if not testOnly: item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))
            x, lineHeight = nextX, max(lineHeight, item.sizeHint().height())
        return y + lineHeight - rect.y()

# scan_nss_items moved to later in file with improved parameters

class IDPopupDialog(QDialog):
    def __init__(self, parent_widget, current_menu, current_vis):
        super().__init__(parent_widget); self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint); self.setAttribute(Qt.WA_TranslucentBackground); self.current_menu = current_menu; self.current_vis = current_vis; self.setup_ui()
    def setup_ui(self):
        self.frame = QFrame(self); self.frame.setObjectName("popupFrame")
        self.frame.setStyleSheet("""
            #popupFrame { background-color: #121212; border: 1px solid #2a2a30; border-radius: 12px; } 
            QLabel { color: #333333; font-size: 10px; font-weight: bold; letter-spacing: 0.5px; border: none; background: transparent; padding-left: 2px; } 
            QComboBox { background: #2a2a30; border: 1px solid #45475a; border-radius: 8px; padding: 8px; color: #ffffff; font-size: 12px; }
            QComboBox:hover { border: 1px solid #dc143c; }
            QComboBox::drop-down { border: none; width: 20px; }
            QComboBox::down-arrow { image: url("icons/chevron_down.svg"); width: 14px; height: 14px; border: none; }
            QComboBox::down-arrow:hover { image: url("icons/chevron_down_hover.svg"); }
            QComboBox QAbstractItemView { background-color: #121212; border: 1px solid #2a2a30; color: #ffffff; outline: none; border-radius: 8px; padding: 6px; }
            QComboBox QAbstractItemView::item { min-height: 24px; padding: 8px 12px; border-radius: 8px; margin: 2px; }
            QComboBox QAbstractItemView::item:selected { background-color: rgba(255, 255, 255, 0.1); color: #ffffff; }
        """)
        layout = QVBoxLayout(self); layout.setContentsMargins(0,0,0,0); layout.addWidget(self.frame); cl = QVBoxLayout(self.frame); cl.setContentsMargins(15, 12, 15, 15); cl.setSpacing(10)
        h1 = QLabel("MENU LOCATION"); cl.addWidget(h1)
        self.m_box = QComboBox()
        self.m_box.addItems(["None", "Main", "Options"])
        
        if self.current_menu is None: self.m_box.setCurrentText("None")
        elif self.current_menu == "" or str(self.current_menu).lower() == "main": self.m_box.setCurrentText("Main")
        elif str(self.current_menu).lower() in ("options", "title.options"): self.m_box.setCurrentText("Options")
        else: self.m_box.setCurrentText("None")
        
        cl.addWidget(self.m_box)
        h2 = QLabel("VISIBILITY"); cl.addWidget(h2)
        self.v_box = QComboBox(); self.v_box.addItems(["None", "Shift", "Control", "Left Mouse"]); v_map = {"None": None, "Shift": "key.shift()", "Control": "key.control()", "Left Mouse": "key.lbutton()"}
        for i in range(self.v_box.count()):
            if v_map[self.v_box.itemText(i)] == self.current_vis: self.v_box.setCurrentIndex(i); break
        cl.addWidget(self.v_box)
        self.save = QPushButton("Apply Changes"); self.save.setFixedHeight(34)
        self.save.setStyleSheet("QPushButton { background: #dc143c; color: #ffffff; font-weight: bold; border-radius: 8px; border: none; margin-top: 5px; } QPushButton:hover { background: #dc143c; }")
        self.save.clicked.connect(self.accept); cl.addWidget(self.save)
    def get_values(self):
        m_sel = self.m_box.currentText()
        m_val = None
        if m_sel == "Main": m_val = ""
        elif m_sel == "Options": m_val = "options"
        elif m_sel != "None": m_val = m_sel
        
        v_sel = self.v_box.currentText()
        v_map = {"None": None, "Shift": "key.shift()", "Control": "key.control()", "Left Mouse": "key.lbutton()"}
        return m_val, v_map.get(v_sel)

class RadioDot(QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent); self.setCheckable(True); self.setFixedSize(20, 20); self.setCursor(Qt.PointingHandCursor)
    def paintEvent(self, event):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(4, 4, 12, 12)
        if self.isChecked():
            p.setPen(Qt.NoPen); p.setBrush(QColor("#dc143c")); p.drawEllipse(rect)
        else:
            p.setPen(QPen(QColor(255, 255, 255, 60), 1.5)); p.setBrush(Qt.NoBrush); p.drawEllipse(rect)

class IconSyncButton(QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent); self.setFixedSize(28, 28); self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("QPushButton { background: rgba(255,255,255,0.05); border-radius: 14px; border: 1px solid rgba(255,255,255,0.1); } QPushButton:hover { background: rgba(220, 20, 60, 0.15); border: 1px solid #dc143c; }")
    def paintEvent(self, event):
        super().paintEvent(event); p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        c = QColor("#dc143c") if self.underMouse() else QColor("#ffffff")
        p.setPen(QPen(c, 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        # Draw a circular arrow (Sync/Reload icon)
        rect = QRectF(7, 7, 14, 14); p.drawArc(rect, 40 * 16, 280 * 16)
        # Draw arrow head
        p.setBrush(c); p.drawPolygon(QPointF(17, 6), QPointF(21, 9), QPointF(17, 12))

class ColorPellet(QPushButton):
    def __init__(self, color, parent=None):
        super().__init__(parent); self.color = QColor(color); self.setFixedSize(22, 22); self.setCursor(Qt.PointingHandCursor)
    def paintEvent(self, event):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        p.setPen(QPen(QColor(255, 255, 255, 30), 2))
        p.setBrush(self.color); p.drawEllipse(2, 2, 18, 18)
        if self.underMouse():
            p.setPen(QPen(Qt.white, 2)); p.setBrush(Qt.NoBrush); p.drawEllipse(1, 1, 20, 20)

class FilterTag(QPushButton):
    def __init__(self, text, color="#dc143c", parent=None):
        super().__init__(text, parent); self.setCheckable(True); self.setFixedHeight(28); self.setCursor(Qt.PointingHandCursor)
        c = QColor(color); r, g, b = c.red(), c.green(), c.blue()
        self.setStyleSheet(f"""
            FilterTag {{ background: rgba({r},{g},{b},0.15); border: 1px solid rgba({r},{g},{b},0.3); border-radius: 14px; color: transparent; padding: 0 14px; font-size: 11px; font-weight: 600; }}
            FilterTag:hover {{ background: rgba({r},{g},{b},0.3); border: 1px solid rgba({r},{g},{b},0.5); }}
            FilterTag:checked {{ background: rgb({r},{g},{b}); border: 1px solid rgb({r},{g},{b}); color: transparent; font-weight: bold; }}
        """)

    def paintEvent(self, event):
        super().paintEvent(event)
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        p.setFont(self.font())
        r = self.rect()
        txt = self.text()
        p.setPen(QColor("#000000"))
        p.drawText(r.adjusted(-1, -1, -1, -1), Qt.AlignCenter, txt)
        p.drawText(r.adjusted(1, -1, 1, -1), Qt.AlignCenter, txt)
        p.drawText(r.adjusted(-1, 1, -1, 1), Qt.AlignCenter, txt)
        p.drawText(r.adjusted(1, 1, 1, 1), Qt.AlignCenter, txt)
        p.setPen(QColor("#ffffff")); p.drawText(r, Qt.AlignCenter, txt)

class FilterBar(QWidget):
    filter_changed = pyqtSignal(str)
    def __init__(self, tags_with_colors, parent=None):
        super().__init__(parent); self.layout = QHBoxLayout(self); self.layout.setContentsMargins(0, 0, 0, 0); self.layout.setSpacing(8); self.layout.setAlignment(Qt.AlignLeft)
        self.group = QButtonGroup(self); self.group.setExclusive(True)
        for i, (tag, color) in enumerate(tags_with_colors):
            btn = FilterTag(tag, color); self.group.addButton(btn, i); self.layout.addWidget(btn)
            if i == 0: btn.setChecked(True)
        self.group.buttonClicked.connect(lambda b: self.filter_changed.emit(b.text()))

class GlobalTintWorker(QObject):
    progress = pyqtSignal(int, int)
    status = pyqtSignal(str)
    finished = pyqtSignal()
    def __init__(self, root, color, skip_manual_keys=None): super().__init__(); self.root = root; self.color = color; self.skip_manual_keys = skip_manual_keys or set()
    def run(self):
        items = scan_nss_items(self.root); files = sorted(list(set(i['file'] for i in items)))
        processable = []
        for fp in files:
            file_items = [i for i in items if i['file'] == fp]
            for i in file_items:
                item_key = f"{fp}:{i['start']}"
                if item_key in self.skip_manual_keys: continue
                p = i['props']; val = p.get('image') or p.get('icon') or ''
                if val: processable.append((fp, i))
        total = max(len(processable), 1)
        processed = 0
        file_ops = {}
        for fp, i in processable:
            self.status.emit(f"Processing {os.path.basename(fp)}... ({processed + 1}/{total})")
            p = i['props']; val = p.get('image') or p.get('icon') or ''
            codes = _extract_glyph_codes(val)
            nv = None
            if codes:
                nv = _build_glyph_val(codes, [])
            else:
                path = _resolve_app_dir_path(val.strip('\'" '))
                if (not path or not os.path.exists(path)) and fp:
                    try_rel = os.path.join(os.path.dirname(fp), val.strip('\'" '))
                    if os.path.exists(try_rel): path = try_rel
                if path and os.path.exists(path):
                    nv, _ = save_local_icon(path, self.color, True, subfolder='preview')
                    if nv: nv = nv.strip('\'"')
            if nv:
                raw = read_file(fp)[i['start']:i.get('cmd_end', i['end'])]
                new_raw = raw
                for key in ('image', 'icon'):
                    if key in new_raw:
                        raw_val = p.get(key)
                        if raw_val:
                            base_n = os.path.basename(raw_val)
                            pattern = rf'({key}\s*=\s*)([\'\"\[]?)(?:.*?[/\\\\])?{re.escape(base_n)}([\'\"\]]?)'
                            if re.search(pattern, new_raw, re.I):
                                if nv.startswith('\\u') or nv.startswith('['):
                                    new_raw = re.sub(pattern, lambda m: f"{m.group(1)}{nv}", new_raw, count=1, flags=re.I)
                                else:
                                    new_raw = re.sub(pattern, lambda m: f"{m.group(1)}'{nv}'", new_raw, count=1, flags=re.I)
                                break
                if new_raw != raw:
                    if fp not in file_ops: file_ops[fp] = []
                    file_ops[fp].append((i, new_raw))
            processed += 1
            self.progress.emit(processed, total)
        for fp, ops in file_ops.items():
            ops.sort(key=lambda x: x[0]['start'], reverse=True); content = read_file(fp)
            for i, new_raw in ops:
                c_end = i.get('cmd_end', i['end'])
                content = content[:i['start']] + new_raw + content[c_end:]
            safe_file_write(fp, content)
        self.progress.emit(total, total)
        self.finished.emit()

def _find_target_executable_or_shortcut(cmd_or_title):
    if not cmd_or_title: return None
    s = str(cmd_or_title).strip('\'" ')
    # 1. Direct path check or extracted path with quotes/slashes
    m = re.search(r'([a-zA-Z]:[\\/][^"\'\n\r\t]+?\.(?:exe|lnk|ico|dll|png|svg))', s, re.I)
    if m and os.path.exists(m.group(1)):
        return m.group(1)
    if os.path.exists(s) and os.path.isfile(s):
        return s

    # 2. Check if clean name matches common app directories or Start Menu shortcuts
    clean_name = re.sub(r'[^a-zA-Z0-9 _\-]', '', s).strip().lower()
    if not clean_name: return None

    search_dirs = [
        os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs"),
        os.path.expandvars(r"%PROGRAMDATA%\Microsoft\Windows\Start Menu\Programs"),
        os.path.expandvars(r"%USERPROFILE%\Desktop"),
        os.path.expandvars(r"%PUBLIC%\Desktop"),
        os.path.expandvars(r"%LOCALAPPDATA%\Programs"),
        os.path.expandvars(r"%ProgramFiles%"),
        os.path.expandvars(r"%ProgramFiles(x86)%"),
    ]

    for base_dir in search_dirs:
        if not os.path.exists(base_dir): continue
        try:
            for root, _, files in os.walk(base_dir):
                for f in files:
                    fl = f.lower()
                    if fl.endswith(('.lnk', '.exe')):
                        name_without_ext = os.path.splitext(fl)[0]
                        if clean_name == name_without_ext or clean_name in name_without_ext:
                            candidate = os.path.join(root, f)
                            if os.path.exists(candidate):
                                return candidate
        except: pass
    return None

def _extract_svg_content(val):
    if not val: return None
    s = str(val).strip()
    # Strip any leading/trailing quotes or brackets
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

def _update_label_asset(lbl, val, nss_path=None, cmd=None):
    # Clear children
    for c in lbl.findChildren(QWidget): c.deleteLater()
    lbl.setPixmap(QPixmap()); lbl.setText("")
    if not val:
        lbl.setText("\u2726"); lbl.setStyleSheet("color: rgba(220, 20, 60, 0.3); font-size: 18px; background: rgba(255,255,255,0.03); border-radius: 10px; border: 1px solid rgba(255,255,255,0.05);")
        return
    svg_content = _extract_svg_content(val)
    if svg_content:
        try:
            if QtSvg:
                clean_svg = svg_content.replace("@image.color1", "#ffffff").replace("@image.color2", "#ffffff").replace("@color3", "#ffffff")
                renderer = QtSvg.QSvgRenderer(clean_svg.encode('utf-8'))
                if renderer.isValid():
                    sz = renderer.defaultSize()
                    w = sz.width() if sz.width() > 0 else 24
                    h = sz.height() if sz.height() > 0 else 24
                    pm = QPixmap(w * 4, h * 4); pm.fill(Qt.transparent)
                    p_obj = QPainter(pm); p_obj.setRenderHint(QPainter.Antialiasing); p_obj.setRenderHint(QPainter.SmoothPixmapTransform)
                    renderer.render(p_obj); p_obj.end()
                    target_w = max(20, (lbl.width() if lbl.width() > 0 else 46) - 10)
                    target_h = max(20, (lbl.height() if lbl.height() > 0 else 46) - 10)
                    scaled_pm = pm.scaled(target_w, target_h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    lbl.setPixmap(scaled_pm)
                    return
        except: pass
    codes = _extract_glyph_codes(val); colors = _extract_all_colors(val)
    if codes:
        pw = GlyphPreviewLabel(codes, size=lbl.height(), font_family=NILESOFT_FONT_FAMILY, colors=colors, parent=lbl)
        pw.setFixedSize(lbl.size()); pw.show(); return
    if val.strip('\'" ').startswith('icon.'):
        pw = GlyphPreviewLabel([0xE91B], size=lbl.height(), parent=lbl) # Image icon
        pw.setFixedSize(lbl.size()); pw.show(); return
    path, color = _extract_img_path_and_color(val)
    if not path:
        clean_v = val.strip('\'" ')
        m_res = re.search(r"image\.res\s*\(\s*['\"]([^'\"]+)['\"]\s*\)", val, re.IGNORECASE)
        if m_res:
            path = m_res.group(1)
        else:
            path = clean_v
    
    # Try resolving path directly or extracting executable path from command
    res_path = _resolve_app_dir_path(path)
    if (not res_path or not os.path.exists(res_path)) and cmd:
        m = re.search(r'([a-zA-Z]:[\\/][^"\'\n\r\t]+?\.(?:exe|ico|dll))', str(cmd), re.I)
        if m and os.path.exists(m.group(1)):
            res_path = m.group(1)
        elif os.path.exists(str(cmd).strip('\'" ')):
            res_path = str(cmd).strip('\'" ')

    if res_path and not os.path.exists(res_path) and nss_path:
        alt = os.path.join(os.path.dirname(nss_path), path)
        if os.path.exists(alt): res_path = alt
    if res_path and os.path.exists(res_path):
        pm = QPixmap()
        if res_path.lower().endswith('.svg') and QtSvg:
            try:
                renderer = QtSvg.QSvgRenderer(res_path)
                if renderer.isValid():
                    pm = QPixmap(256, 256); pm.fill(Qt.transparent)
                    p_svg = QPainter(pm); p_svg.setRenderHint(QPainter.Antialiasing); p_svg.setRenderHint(QPainter.SmoothPixmapTransform); renderer.render(p_svg); p_svg.end()
            except: pass
        if pm.isNull():
            try:
                with open(res_path, 'rb') as f: data = f.read()
                pm.loadFromData(data)
            except: pass
        if pm.isNull():
            # Use Windows system icon extraction for executables, dlls, shortcuts, etc.
            provider = QFileIconProvider()
            icon = provider.icon(QFileInfo(res_path))
            if not icon.isNull():
                pm = icon.pixmap(128, 128)
            if pm.isNull():
                icon = QIcon(res_path)
                pm = icon.pixmap(128, 128)
        
        if not pm.isNull():
            if color:
                img = pm.toImage().convertToFormat(QImage.Format_ARGB32); c = QColor(color)
                for y in range(img.height()):
                    for x in range(img.width()):
                        p = img.pixelColor(x, y)
                        if p.alpha() > 0: c.setAlpha(p.alpha()); img.setPixelColor(x, y, c)
                pm = QPixmap.fromImage(img)
            target_w = max(20, (lbl.width() if lbl.width() > 0 else 46) - 10)
            target_h = max(20, (lbl.height() if lbl.height() > 0 else 46) - 10)
            lbl.setPixmap(pm.scaled(target_w, target_h, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            return
    lbl.setText("\uE12B"); lbl.setFont(QFont('Segoe MDL2 Assets', 18)); lbl.setStyleSheet("color: #dc143c; background: transparent;")
def _build_glyph_val(codes, colors=None):
    if not codes: return ""
    colors = colors or []
    # Build list of strings like: ["\uE001"] or ["\uE001", #ffffff]
    parts = []
    for i, code in enumerate(codes):
        color = colors[i] if i < len(colors) else None
        glyph_str = f"\\u{code:04X}"
        if color:
            parts.append("[\"" + glyph_str + "\", " + str(color) + "]")
        else:
            parts.append("[\"" + glyph_str + "\"]")
    
    # Return single item as ["\uE001"] or multi as [ ["\uE001"], ["\uE002"] ]
    if len(parts) == 1:
        return parts[0]
    return "[ " + ", ".join(parts) + " ]"

def _get_new_asset_value(val, old_color, new_color, idx=None):
    val = str(val).strip()
    if not val: return val

    # 1. If it's a simple path or icon name without brackets/colors, just add bracketed color
    if not any(c in val for c in ('#', '[', '\\u', '0x')):
        return f"{val} [{new_color}]"

    # 2. Extract glyphs and colors
    codes = _extract_glyph_codes(val)
    if codes:
        colors = _extract_all_colors(val)
        while len(colors) < len(codes): colors.append(None)

        # If idx is provided, target that specific slot
        if idx is not None and idx < len(colors):
            colors[idx] = new_color
        else:
            # If old_color matches one of the existing colors, replace it
            replaced = False
            for i in range(len(colors)):
                if colors[i] and old_color and colors[i].lower() == old_color.lower():
                    colors[i] = new_color; replaced = True; break

            # If not replaced and we have space, set the first empty slot or just the first slot
            if not replaced:
                for i in range(len(colors)):
                    if not colors[i]: colors[i] = new_color; replaced = True; break
                if not replaced: colors[0] = new_color

        return _build_glyph_val(codes, colors)

    # 3. Handle image paths - handled physically in UI, just return val if not a glyph
    return val

class ImportedItemCard(QFrame):
    def __init__(self, data, parent=None):
        super().__init__(parent); self.data = data; self.setObjectName("ruleCard"); self.setFixedHeight(100); self.setStyleSheet("#ruleCard { background-color: rgba(255, 255, 255, 0.04); border-radius: 12px; border: 1px solid rgba(255, 255, 255, 0.05); } #ruleCard:hover { background-color: rgba(255, 255, 255, 0.07); border: 1px solid rgba(220, 20, 60, 0.2); }")
        self.main_layout = QHBoxLayout(self); self.main_layout.setContentsMargins(15, 10, 15, 10); self.main_layout.setSpacing(15); self.main_layout.setAlignment(Qt.AlignVCenter)
        
        self.icon_label = QLabel(self); self.icon_label.setFixedSize(40, 40); self.icon_label.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(self.icon_label)
        
        self.sb = QPushButton("\uE117", self); self.sb.setFixedSize(24, 24); self.sb.setCursor(Qt.PointingHandCursor); self.sb.setToolTip("Sync with Global Theme")
        self.sb.setFont(QFont('Segoe MDL2 Assets', 10))
        self.sb.setStyleSheet("QPushButton { background: transparent; border: none; color: #b0b0b0; } QPushButton:hover { color: #dc143c; }")
        self.sb.clicked.connect(self.sync_to_theme); self.main_layout.addWidget(self.sb)

        self.iw = QWidget(self); self.iw.setStyleSheet("background: transparent; border: none;")
        self.iwl = QVBoxLayout(self.iw); self.iwl.setContentsMargins(0, 0, 0, 0); self.iwl.setSpacing(4); self.iwl.setAlignment(Qt.AlignVCenter)
        self.title_label = QLabel(self.iw); self.title_label.setStyleSheet("font-size: 15px; font-weight: 500; color: white; background: transparent;")
        self.desc_label = QLabel(self.iw); self.desc_label.setStyleSheet("font-size: 11px; color: #b0b0b0; background: transparent;")
        self.c_lay = QHBoxLayout(); self.c_lay.setSpacing(6); self.c_lay.setAlignment(Qt.AlignLeft)
        self.iwl.addWidget(self.title_label); self.iwl.addWidget(self.desc_label); self.iwl.addLayout(self.c_lay)
        self.main_layout.addWidget(self.iw, 1)
        
        self.bl_w = QWidget(self); self.bl_w.setStyleSheet("background: transparent; border: none;")
        self.bl = QHBoxLayout(self.bl_w); self.bl.setContentsMargins(0, 0, 0, 0); self.bl.setSpacing(8); self.bl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.eb = QPushButton(self.bl_w); self.ab = QPushButton(self.bl_w)
        for b in (self.ab, self.eb): 
            b.setCursor(Qt.PointingHandCursor); self.bl.addWidget(b)
        self.main_layout.addWidget(self.bl_w)
        self.update_ui()

    def update_ui(self):
        data = self.data.get('props', {})
        val = data.get('image') or data.get('icon') or ''
        cmd_val = data.get('cmd') or data.get('path') or ''
        _update_label_asset(self.icon_label, val, self.data.get('file'), cmd=cmd_val)
        title = data.get('title', 'No Title'); typ = self.data.get('type', 'item').title()
        self.title_label.setText(f"{typ}: <span style='color: #dc143c;'>{title}</span>")
        fname = os.path.basename(self.data.get('file', 'unknown'))
        self.desc_label.setText(f"Source: <span style='color: #ff2a55;'>{fname}</span>" + (f" \u2022 Cmd: <span style='color: #b0b0b0;'>{data['cmd'][:50]}...</span>" if 'cmd' in data else ""))
        
        while self.c_lay.count():
            it = self.c_lay.takeAt(0); (it.widget().deleteLater() if it.widget() else None)
        
        colors = _extract_all_colors(val)
        theme_cs = _get_theme_glyph_colors()
        
        # Determine how many pellets to show based on asset type
        codes = _extract_glyph_codes(val)
        num_pellets = len(codes) if codes else (1 if val else 0)
        
        for i in range(max(num_pellets, len(colors))):
            if i >= 2: break
            c = colors[i] if i < len(colors) else None
            btn = ColorPellet(c or theme_cs[min(i, 1)])
            btn.clicked.connect(lambda checked, idx=i, oc=c: self._pick_color(idx, oc))
            self.c_lay.addWidget(btn)
        
        if colors or _extract_glyph_codes(val):
            sb = QPushButton("\uE72C")
            sb.setFixedSize(24, 24); sb.setCursor(Qt.PointingHandCursor)
            sb.setToolTip("Sync with Theme")
            sb.setStyleSheet("QPushButton { background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); border-radius: 12px; color: #b0b0b0; font-family: 'Segoe MDL2 Assets'; font-size: 11px; } QPushButton:hover { background: rgba(220, 20, 60, 0.1); color: #dc143c; border-color: #dc143c; }")
            sb.clicked.connect(self.sync_to_theme)
            self.c_lay.addWidget(sb)

        btn_style = "QPushButton { background: rgba(255, 255, 255, 0.08); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 19px; color: #ffffff; font-family: 'Segoe MDL2 Assets'; font-size: 16px; } QPushButton:hover { background: rgba(255, 255, 255, 0.15); border: 1px solid #dc143c; color: white; }"
        self.ab.setFixedSize(38, 38); self.ab.setStyleSheet(btn_style.replace("#ffffff", "#dc143c")); self.ab.setText("\uE72B")
        self.eb.setFixedSize(38, 38); self.eb.setStyleSheet(btn_style); self.eb.setText("\uE104")
        self.ab.show() if (colors or _extract_glyph_codes(val)) else self.ab.hide()

    def sync_to_theme(self):
        val = (self.data.get('props', {}).get('icon') or self.data.get('props', {}).get('image') or '').strip()
        if not val: return
        theme_c = _get_theme_glyph_colors()[0]
        codes = _extract_glyph_codes(val)
        if codes:
            # For glyphs, stripping explicit colors allows them to follow theme image.color
            new_val = _build_glyph_val(codes, [])
        else:
            # Physical re-tinting for images
            path, _ = _extract_img_path_and_color(val)
            resolved = _resolve_app_dir_path(path)
            if resolved and os.path.exists(resolved):
                new_val, _ = save_local_icon(resolved, theme_c, True)
                new_val = f"'{new_val}'"
            else: return # Can't resolve
            
        if new_val != val:
            _update_label_asset(self.icon_label, new_val, self.data.get('file'))
            np = self.data['props'].copy()
            target_key = 'icon' if 'icon' in np else 'image'
            np[target_key] = new_val
            save_imported_item(self.data, np)
            if hasattr(self.parent(), 'parent') and hasattr(self.parent().parent(), 'refresh'):
                self.parent().parent().refresh()

    def _pick_color(self, idx, old_color):
        theme_cs = _get_theme_glyph_colors()
        dlg = MinimalColorPickerDialog(old_color or theme_cs[min(idx, 1)], f"imp_card_{idx}" if hasattr(self, "data") and "file" in self.data else f"rule_card_{idx}", self); dlg.default_checkbox.hide()
        def on_color(key, color):
            val = (self.data.get('props', {}).get('icon') or self.data.get('props', {}).get('image') or '').strip()
            new_val = _get_new_asset_value(val, old_color, color.name(), idx=idx)
            _update_label_asset(self.icon_label, new_val, self.data.get('file'))
            np = self.data['props'].copy()
            np['icon' if 'icon' in np else 'image'] = new_val
            save_imported_item(self.data, np)
            if hasattr(self.parent(), 'parent') and hasattr(self.parent().parent(), 'refresh'):
                self.parent().parent().refresh()
        dlg.colorSelected.connect(on_color); dlg.exec_()

    def _update_c_btn(self, btn, color):
        btn.setStyleSheet(f"QPushButton {{ background-color: {color}; border-radius: 12px; border: 1px solid rgba(255,255,255,0.1); }} QPushButton:hover {{ border: 1px solid white; }}")

class IDEntryWidget(QFrame):
    changed = pyqtSignal()
    def __init__(self, id_text, formatted_name, initial_menu=None, initial_vis=None, initial_hidden=False, parent=None):
        super().__init__(parent); self.id_text = id_text; self.menu = initial_menu; self.vis = initial_vis; self.is_hidden = initial_hidden; self.setFixedSize(240, 60); self.setObjectName("idEntryWidget"); self.update_style(); layout = QHBoxLayout(self); layout.setContentsMargins(15, 0, 10, 0); self.label = QLabel(formatted_name); self.label.setStyleSheet("font-size: 13px; color: white; background: transparent;"); layout.addWidget(self.label, 1); btn_c = QFrame(); btn_c.setStyleSheet("background: rgba(0,0,0,0.15); border-radius: 12px; padding: 2px;"); bl = QHBoxLayout(btn_c); bl.setContentsMargins(2, 2, 2, 2); bl.setSpacing(2); self.h_btn = QPushButton("\uE708"); self.h_btn.setFixedSize(24, 24); self.h_btn.setCursor(Qt.PointingHandCursor); self.h_btn.setStyleSheet("QPushButton { background: transparent; border: none; border-radius: 10px; color: #b0b0b0; font-family: 'Segoe MDL2 Assets'; } QPushButton:hover { color: #dc143c; }"); self.h_btn.clicked.connect(self.toggle_hide); bl.addWidget(self.h_btn); self.e_btn = QPushButton("\uE104"); self.e_btn.setFixedSize(24, 24); self.e_btn.setCursor(Qt.PointingHandCursor); self.e_btn.setStyleSheet("QPushButton { background: transparent; border: none; border-radius: 10px; color: #b0b0b0; font-family: 'Segoe MDL2 Assets'; } QPushButton:hover { color: #dc143c; }"); self.e_btn.clicked.connect(self.show_popup); bl.addWidget(self.e_btn); layout.addWidget(btn_c); self.update_label_state()
    def update_style(self): self.setStyleSheet(f"#idEntryWidget {{ background-color: rgba(255, 255, 255, 0.05); border-radius: 15px; border: 1px solid {'rgba(220, 20, 60, 0.4)' if (self.menu or self.vis) else 'rgba(255, 255, 255, 0.03)'}; }} #idEntryWidget:hover {{ background-color: rgba(255, 255, 255, 0.08); border: 1px solid rgba(220, 20, 60, 0.2); }}")
    def update_label_state(self):
        self.label.setGraphicsEffect(None); self.label.setStyleSheet(f"font-size: 13px; color: {'#333333' if self.is_hidden else 'white'}; background: transparent;")
        self.h_btn.setStyleSheet(f"QPushButton {{ background: {'#dc143c' if self.is_hidden else 'transparent'}; border: none; border-radius: 10px; color: {'#1e2030' if self.is_hidden else '#b0b0b0'}; font-family: 'Segoe MDL2 Assets'; }}")
    def toggle_hide(self): self.is_hidden = not self.is_hidden; self.update_label_state(); self.changed.emit()
    def show_popup(self):
        d = IDPopupDialog(self, self.menu, self.vis); d.setFixedWidth(200); pos = self.e_btn.mapToGlobal(QPoint(-d.width() + self.e_btn.width(), self.e_btn.height() + 5)); d.move(pos)
        if d.exec_(): self.menu, self.vis = d.get_values(); self.update_style(); self.changed.emit()

class ModificationRuleCard(QFrame):
    def __init__(self, data, parent=None):
        super().__init__(parent); self.data = data; self.setObjectName("ruleCard"); self.setFixedHeight(100); self.setStyleSheet("#ruleCard { background-color: rgba(255, 255, 255, 0.04); border-radius: 12px; border: 1px solid rgba(255, 255, 255, 0.05); } #ruleCard:hover { background-color: rgba(255, 255, 255, 0.07); border: 1px solid rgba(220, 20, 60, 0.2); }")
        self.main_layout = QHBoxLayout(self); self.main_layout.setContentsMargins(15, 12, 15, 12); self.main_layout.setSpacing(15)
        
        self.il = QLabel(self); self.il.setFixedSize(40, 40); self.il.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(self.il)
        
        self.iw = QWidget(self); self.iw.setStyleSheet("background: transparent; border: none;")
        self.iwl = QVBoxLayout(self.iw); self.iwl.setContentsMargins(0, 0, 0, 0); self.iwl.setSpacing(2)
        self.tl = QLabel(self.iw); self.tl.setStyleSheet("font-size: 15px; font-weight: 500; color: white; background: transparent;")
        self.dl = QLabel(self.iw); self.dl.setStyleSheet("font-size: 11px; color: #b0b0b0; background: transparent;")
        self.c_lay = QHBoxLayout(); self.c_lay.setSpacing(6); self.c_lay.setAlignment(Qt.AlignLeft)
        self.iwl.addWidget(self.tl); self.iwl.addWidget(self.dl); self.iwl.addLayout(self.c_lay)
        self.main_layout.addWidget(self.iw, 1) # Give it stretch factor 1
        
        self.bl_w = QWidget(self); self.bl_w.setStyleSheet("background: transparent; border: none;")
        self.bl = QHBoxLayout(self.bl_w); self.bl.setContentsMargins(0, 0, 0, 0); self.bl.setSpacing(8); self.bl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.eb = QPushButton(self.bl_w); self.db = QPushButton(self.bl_w)
        btn_style = "QPushButton { background: rgba(255, 255, 255, 0.08); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 19px; color: #ffffff; font-family: 'Segoe MDL2 Assets'; font-size: 16px; } QPushButton:hover { background: rgba(255, 255, 255, 0.15); border: 1px solid #dc143c; color: white; }"
        for b in (self.eb, self.db): 
            b.setFixedSize(38, 38); b.setStyleSheet(btn_style); b.setCursor(Qt.PointingHandCursor); self.bl.addWidget(b)
        self.eb.setText("\uE104"); self.db.setText("\uE107")
        self.db.setStyleSheet(self.db.styleSheet() + "QPushButton:hover { color: #dc143c; border-color: #dc143c; }")
        self.main_layout.addWidget(self.bl_w)
        self.update_ui()
        
    def update_ui(self):
        data = self.data; val = data.get('image') or data.get('icon') or ''
        cmd_val = data.get('cmd') or data.get('path') or data.get('find') or ''
        _update_label_asset(self.il, val, cmd=cmd_val)
        
        # Build a friendly Target Title
        target = "Global Rule"
        if data.get('find'): target = f"Modify: <span style='color: #dc143c;'>{data['find'].strip(chr(39)+chr(34))}</span>"
        elif data.get('type'): target = f"All <span style='color: #ff2a55;'>{data['type'].title()}s</span>"
        if data.get('in'): target += f" <span style='color: #333333;'>in</span> <span style='color: #b0b0b0;'>{data['in'].strip(chr(39)+chr(34))}</span>"
        self.tl.setText(target)
        
        # Build a friendly Actions Summary
        acts = []
        if data.get('title'): acts.append(f"Rename to <span style='color: #ffffff;'>'{data['title'].strip(chr(39)+chr(34))}'</span>")
        
        v = data.get('vis', '').lower()
        if 'remove' in v or 'hidden' in v: acts.append("<span style='color: #dc143c;'>Hidden</span>")
        elif v and v != 'normal': acts.append(f"Vis: <span style='color: #dc143c;'>{v}</span>")
        
        m = data.get('menu', '').lower()
        if m: 
            m_name = m.split('.')[-1].title() if '.' in m else m.title()
            acts.append(f"Move to <span style='color: #dc143c;'>{m_name}</span>")
            
        if data.get('pos'): acts.append(f"Pos: <span style='color: #dc143c;'>{data['pos']}</span>")
        if any(k in data for k in ('icon', 'image')): acts.append("<span style='color: #dc143c;'>New Icon</span>")
        if data.get('sep'): acts.append("<span style='color: #333333;'>Separator</span>")
        
        self.dl.setText(" \u2022 ".join(acts) if acts else "No modifications defined")
        
        while self.c_lay.count():
            it = self.c_lay.takeAt(0); (it.widget().deleteLater() if it.widget() else None)
        
        colors = _extract_all_colors(val)
        theme_cs = _get_theme_glyph_colors()
        
        # Determine how many pellets to show based on asset type
        codes = _extract_glyph_codes(val)
        num_pellets = len(codes) if codes else (1 if val else 0)
        
        for i in range(max(num_pellets, len(colors))):
            if i >= 2: break
            c = colors[i] if i < len(colors) else None
            btn = ColorPellet(c or theme_cs[min(i, 1)])
            btn.clicked.connect(lambda checked, idx=i, oc=c: self._pick_color(idx, oc))
            self.c_lay.addWidget(btn)
        
        if colors or _extract_glyph_codes(val):
            sb = QPushButton("\uE117")
            sb.setFixedSize(24, 24); sb.setCursor(Qt.PointingHandCursor)
            sb.setToolTip("Sync with Theme")
            sb.setStyleSheet("QPushButton { background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); border-radius: 12px; color: #b0b0b0; font-family: 'Segoe MDL2 Assets'; font-size: 11px; } QPushButton:hover { background: rgba(220, 20, 60, 0.1); color: #dc143c; border-color: #dc143c; }")
            sb.clicked.connect(self.sync_to_theme)
            self.c_lay.addWidget(sb)

    def sync_to_theme(self):
        val = (self.data.get('image') or self.data.get('icon') or '').strip()
        if not val: return
        codes = _extract_glyph_codes(val)
        if codes:
            # For glyphs, removing explicit colors allows them to follow theme image.color
            new_val = _build_glyph_val(codes, [])
        else:
            theme_cs = _get_theme_glyph_colors()
            colors = _extract_all_colors(val)
            if colors:
                new_val = val
                for c in colors: new_val = new_val.replace(c, theme_cs[0])
            else: new_val = _get_new_asset_value(val, None, theme_cs[0])

        if new_val != val:
            _update_label_asset(self.il, new_val)
            self.data['image' if 'image' in self.data else 'icon'] = new_val
            p = self.parent()
            while p and not hasattr(p, 'save_all_modifications'): p = p.parent()
            if p: p.save_all_modifications(); p.refresh_ui()

    def _pick_color(self, idx, old_color):
        theme_cs = _get_theme_glyph_colors()
        dlg = MinimalColorPickerDialog(old_color or theme_cs[min(idx, 1)], f"rule_card_{idx}", self); dlg.default_checkbox.hide()
        def on_color(key, color):
            val = (self.data.get('image') or self.data.get('icon') or '').strip()
            new_val = _get_new_asset_value(val, old_color, color.name(), idx=idx)
            _update_label_asset(self.il, new_val)
            self.data['image' if 'image' in self.data else 'icon'] = new_val
            p = self.parent()
            while p and not hasattr(p, 'save_all_modifications'): p = p.parent()
            if p: p.save_all_modifications(); p.refresh_ui()
        dlg.colorSelected.connect(on_color); dlg.exec_()

def _extract_glyph_codes(value):
    if not value: return []
    import re
    res = []
    # Find all \uXXXX or 0xXXXX patterns regardless of token type
    raw = str(value)
    # Match \uXXXX
    for m in re.finditer(r'\\u([0-9A-Fa-f]{4})', raw):
        try: res.append(int(m.group(1), 16))
        except: pass
    # Match 0xXXXX (if not followed by more hex, to avoid matching colors)
    for m in re.finditer(r'0x([0-9A-Fa-f]{4})\b', raw):
        try: res.append(int(m.group(1), 16))
        except: pass
    return res[:2]
def _resolve_app_dir_path(icon_str):
    if not icon_str: return None
    import sys, os
    # Strip any bracketed color filters from the end
    import re
    icon_str = re.sub(r'\s*\[(?:color\.|theme\.|#|0x)[^\]]+\]$', '', icon_str, flags=re.I).strip('\'" ')
    
    if '@app.dir' in icon_str:
        root = PROJECT_ROOT or (os.path.dirname(os.path.dirname(sys.executable)) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        rel_path = icon_str.replace('@app.dir', '').lstrip('\\/')
        return os.path.normpath(os.path.join(root, rel_path))
    return icon_str

def save_local_icon(source_path, tint_color, tint_enabled, subfolder=None):
    import sys, os, shutil, hashlib
    from PyQt5.QtGui import QPixmap, QImage, QColor
    root = PROJECT_ROOT or (os.path.dirname(os.path.dirname(sys.executable)) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    icons_dir = os.path.join(root, 'imports', 'icons')
    target_dir = os.path.join(icons_dir, subfolder) if subfolder else icons_dir
    os.makedirs(target_dir, exist_ok=True)
    orig_dir = os.path.join(icons_dir, 'originals'); os.makedirs(orig_dir, exist_ok=True)
    
    # Generate a unique base name for this source path to avoid collisions
    s_norm = os.path.normpath(source_path).lower()
    path_hash = hashlib.md5(s_norm.encode('utf-8')).hexdigest()[:8]
    fname, fext = os.path.splitext(os.path.basename(source_path))
    unique_base = f"{fname}_{path_hash}{fext}"
    
    # If source is a tinted one, try finding its original in the originals folder
    if source_path.startswith(icons_dir) and not source_path.startswith(orig_dir):
        # Remove the color hash suffix (e.g., _abcdef) if present to find the original's name
        base = re.sub(r'_[a-f0-9]{6}(\.(?:png|ico|bmp|svg))$', r'\1', os.path.basename(source_path), flags=re.I)
        p_orig = os.path.join(orig_dir, base)
        if os.path.exists(p_orig): source_path = p_orig
    
    # Ensure source is in originals
    if not source_path.startswith(orig_dir):
        dest_orig = os.path.join(orig_dir, unique_base)
        if not os.path.exists(dest_orig): shutil.copy2(source_path, dest_orig)
        source_path = dest_orig
        
    # Final destination name (tinted or not)
    name, ext = os.path.splitext(os.path.basename(source_path))
    if tint_enabled: 
        ext = '.png'
        # Include a hash of the color to make it permanent and unique
        c_hash = hashlib.md5(str(tint_color).lower().encode()).hexdigest()[:6]
        # Remove any previous color hash if it exists to avoid double hashing
        name = re.sub(r'_[a-f0-9]{6}$', '', name)
        dest_name = f"{name}_{c_hash}{ext}"
    else: 
        dest_name = f"{name}{ext}"
        
    dest_path = os.path.join(target_dir, dest_name)
    
    if tint_enabled:
        if source_path.lower().endswith('.svg'):
            # For SVGs, we read as text and replace the color attributes
            try:
                with open(source_path, 'r', encoding='utf-8') as f: svg_data = f.read()
                # Replace fill/stroke with tint_color, but only if they aren't 'none'
                def sub_color(m):
                    attr, quote, val = m.group(1), m.group(2), m.group(3)
                    if val.lower() == 'none': return m.group(0)
                    return f'{attr}={quote}{tint_color}{quote}'
                
                new_svg = re.sub(r'(fill|stroke)=([\'"])(.*?)\2', sub_color, svg_data, flags=re.I)
                with open(dest_path, 'w', encoding='utf-8') as f: f.write(new_svg)
            except: shutil.copy2(source_path, dest_path)
        else:
            pm = QPixmap()
            try:
                with open(source_path, 'rb') as f: data = f.read()
                pm.loadFromData(data)
            except: pass

            if not pm.isNull():
                img = pm.toImage().convertToFormat(QImage.Format_ARGB32); color = QColor(tint_color)
                for y in range(img.height()):
                    for x in range(img.width()):
                        c = img.pixelColor(x, y)
                        if c.alpha() > 0: img.setPixelColor(x, y, QColor(color.red(), color.green(), color.blue(), c.alpha()))
                try:
                    img.save(dest_path, "PNG")
                except:
                    # If save fails due to lock, we might try a temp name or just ignore if it's just a preview
                    # but here it's meant to be permanent.
                    import time
                    for _ in range(3):
                        try: 
                            if os.path.exists(dest_path): os.remove(dest_path)
                            img.save(dest_path, "PNG"); break
                        except: time.sleep(0.1)
            else: 
                try: shutil.copy2(source_path, dest_path)
                except: pass
    else: 
        if not os.path.exists(dest_path) or not os.path.samefile(source_path, dest_path):
            try:
                shutil.copy2(source_path, dest_path)
            except Exception as e:
                # If it fails with WinError 1224, the file is already there and in use
                # Since we are not tinting, and the file exists, we can often safely ignore it
                if not os.path.exists(dest_path): raise e
        
    rel_path = f"icons\\{subfolder}\\{dest_name}" if subfolder else f"icons\\{dest_name}"
    return f"@app.dir\\imports\\{rel_path}", dest_path

def _extract_img_path_and_color(value):

    if not value: return None, None
    text = str(value).strip('\'" ')
    m = re.search(r"image\.(?:ico|png|bmp|svg|jpg|res)?\s*\(\s*(['\"].*?['\"])\s*\)", text, re.IGNORECASE)
    if m: 
        inner = m.group(1).strip('\'" ')
        if not inner.startswith('<svg'): text = inner
    # Check for string with bracketed color: "path.png [#ffffff]"
    m_bracket = re.search(r'(.*?)\s*\[((?:color\.|theme\.|#|0x)[^\]]+)\]', text, re.I)
    if m_bracket:
        return m_bracket.group(1).strip(), m_bracket.group(2)
        
    # Check for bracketed list format: [path, color]
    if text.startswith('[') and text.endswith(']') and 'image.glyph' not in text and '\\u' not in text:
        parts = text[1:-1].split(',')
        if len(parts) >= 2:
            path = parts[0].strip('\'" ')
            color = parts[-1].strip('\'" ')
            return path, color
            
    return text, None

def _extract_all_colors(value):
    if not value: return []
    raw = str(value)
    # If it's the strict list-of-lists format, extract colors per block to maintain alignment
    if '[[' in raw or '], [' in raw or '],[' in raw:
        import re
        blocks = re.findall(r'\[\s*([^\[\]]*?)\s*\]', raw)
        colors = []
        for b in blocks:
            if '\\u' in b or '0x' in b:
                c_match = re.search(r'#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{4}|[0-9a-fA-F]{3})\b', b)
                colors.append(c_match.group(0) if c_match else None)
        if any(colors): return colors
    
    # Fallback to general extraction for simpler formats
    tokens = NSSLexer(raw).tokenize(); colors = []
    for t_type, t_val, _ in tokens:
        if t_type == 'IDENTIFIER' and t_val.startswith('#'): 
            if t_val not in colors: colors.append(t_val)
        elif t_type == 'STRING' and '#' in t_val:
            import re
            hexes = re.findall(r'#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{4}|[0-9a-fA-F]{3})\b', t_val)
            for h in hexes: 
                if h not in colors: colors.append(h)
    if not colors:
        import re
        hexes = re.findall(r'#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{4}|[0-9a-fA-F]{3})\b', raw)
        for h in hexes: 
            if h not in colors: colors.append(h)
    return colors

def _detect_font_from_value(value):
    return "Nilesoft Shell"

_THEME_COLOR_CACHE = ['#dc143c', '#ff2a55']
_LAST_THEME_MTIME = 0

def _get_theme_glyph_colors():
    global _THEME_COLOR_CACHE, _LAST_THEME_MTIME
    try:
        if getattr(sys, 'frozen', False):
            base = os.path.dirname(os.path.dirname(sys.executable))
        else:
            base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        path = os.path.join(base, 'imports', 'theme.nss')
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
    except: pass
    return _THEME_COLOR_CACHE

class GlyphPreviewLabel(QLabel):
    def __init__(self, codes, size=36, parent=None, font_family=NILESOFT_FONT_FAMILY, colors=None, font_families=None):
        super().__init__(parent); self.codes = codes; self.glyph_size = size; self.font_family = font_family
        self.font_families = font_families or [font_family, font_family]
        self.colors = list(colors) if colors else [None, None]
        while len(self.colors) < 2: self.colors.append(None)
        _init_nilesoft_font()
        self.setAlignment(Qt.AlignCenter); self.setStyleSheet("background: transparent;")
    def paintEvent(self, event):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing); p.setRenderHint(QPainter.SmoothPixmapTransform)
        metadata = getattr(GlyphBrowserDialog, '_glyphs_cache', {})
        def_cs = _get_theme_glyph_colors()
        w_avail = self.width()
        h_avail = self.height()
        draw_size = max(16, min(w_avail, h_avail) - 8)
        
        if len(self.codes) >= 1:
            for i, code in enumerate(self.codes[:2]):
                meta = metadata.get(code, {})
                c_hex = self.colors[i] if (i < len(self.colors) and self.colors[i]) else def_cs[i if i < len(def_cs) else 0]
                paths = meta.get('paths', [])
                if paths:
                    paths_xml = ''.join([f'<path fill="{c_hex}" d="{d}"/>' for d in paths])
                    svg_xml = f'<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">{paths_xml}</svg>'
                    from PyQt5.QtSvg import QSvgRenderer
                    from PyQt5.QtCore import QByteArray, QRectF
                    renderer = QSvgRenderer(QByteArray(svg_xml.encode('utf-8')))
                    if renderer.isValid():
                        r = QRectF((w_avail - draw_size)/2, (h_avail - draw_size)/2, draw_size, draw_size)
                        renderer.render(p, r)
                else:
                    if isinstance(code, int):
                        font_size = int(draw_size * 0.72)
                        font = QFont(self.font_families[i] if i < len(self.font_families) else self.font_family, font_size)
                        p.setFont(font)
                        p.setPen(QColor(c_hex))
                        p.drawText(self.rect(), Qt.AlignCenter, chr(code))
        p.end()

NILESOFT_GLYPH_RANGES = [
    (0xE001, 0xE29C)
]

def get_all_font_glyphs():
    _init_nilesoft_font()
    codes = set()
    font = QFont(NILESOFT_FONT_FAMILY)
    fm = QFontMetrics(font)
    for start, end in NILESOFT_GLYPH_RANGES:
        for code in range(start, end + 1):
            ch = chr(code)
            if fm.inFont(ch) and fm.horizontalAdvance(ch) > 0:
                codes.add(code)
    try:
        from utils import get_glyphs_data
        data = get_glyphs_data()
        for key in data.keys():
            try:
                codes.add(int(key, 16))
            except ValueError:
                codes.add(key)
    except Exception:
        pass
    
    int_codes = sorted([c for c in codes if isinstance(c, int)])
    str_codes = sorted([c for c in codes if isinstance(c, str)])
    return int_codes + str_codes

class ManualSyncConflictDialog(QDialog):
    def __init__(self, manual_items, parent=None):
        super().__init__(parent); self.manual_items = manual_items; self.setMinimumWidth(500); self.setMinimumHeight(400); self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint); self.setAttribute(Qt.WA_TranslucentBackground); self.setup_ui()
    def setup_ui(self):
        self.mf = QFrame(self); self.mf.setObjectName("mainFrame"); self.mf.setStyleSheet("#mainFrame { background-color: #121212; border: 1px solid #2a2a30; border-radius: 20px; }")
        layout = QVBoxLayout(self); layout.setContentsMargins(0, 0, 0, 0); layout.addWidget(self.mf); cl = QVBoxLayout(self.mf); cl.setContentsMargins(25, 25, 25, 25); cl.setSpacing(15)
        head = QLabel("Manual Color Conflicts Found"); head.setStyleSheet("font-size: 20px; font-weight: bold; color: white;"); cl.addWidget(head)
        desc = QLabel("We found some items that you previously edited with custom colors.\nSelect which ones you want to overwrite and sync with the new global theme."); desc.setStyleSheet("color: #b0b0b0; font-size: 12px;"); desc.setWordWrap(True); cl.addWidget(desc)
        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self.scroll_widget = QWidget(); self.scroll_widget.setStyleSheet("background: transparent;"); self.scroll_layout = QVBoxLayout(self.scroll_widget); self.scroll_layout.setSpacing(10); self.scroll_layout.setAlignment(Qt.AlignTop)
        self.checkboxes = []
        for idx, item in enumerate(self.manual_items):
            card = QFrame(); card.setStyleSheet("background: rgba(255, 255, 255, 0.05); border-radius: 12px;"); card_lay = QHBoxLayout(card)
            cb = QCheckBox(); cb.setStyleSheet("QCheckBox::indicator { width: 18px; height: 18px; border-radius: 4px; border: 2px solid #333333; background: transparent; } QCheckBox::indicator:checked { background: #dc143c; border: 2px solid #dc143c; }"); cb.setChecked(False); cb.setProperty("item_idx", idx); self.checkboxes.append(cb); card_lay.addWidget(cb)
            val = item['props'].get('image') or item['props'].get('icon') or ''; codes = _extract_glyph_codes(val); colors = _extract_all_colors(val)
            prev = GlyphPreviewLabel(codes, size=24, font_family=NILESOFT_FONT_FAMILY, colors=colors); prev.setFixedSize(36, 36); card_lay.addWidget(prev)
            title = QLabel(item['props'].get('title', 'Unknown Item')); title.setStyleSheet("color: white; font-weight: bold; font-size: 14px;"); card_lay.addWidget(title)
            card_lay.addStretch(); self.scroll_layout.addWidget(card)
        scroll.setWidget(self.scroll_widget); cl.addWidget(scroll)
        btns = QHBoxLayout(); btns.addStretch()
        skip_all = QPushButton("Skip All"); skip_all.clicked.connect(self.reject); skip_all.setStyleSheet("background: #2a2a30; color: white; padding: 10px 20px; border-radius: 10px; font-weight: bold;")
        sync_btn = QPushButton("Sync Selected"); sync_btn.clicked.connect(self.accept); sync_btn.setStyleSheet("background: #dc143c; color: #ffffff; padding: 10px 20px; border-radius: 10px; font-weight: bold;")
        btns.addWidget(skip_all); btns.addWidget(sync_btn); cl.addLayout(btns)
    def get_selected_indices(self): return [cb.property("item_idx") for cb in self.checkboxes if cb.isChecked()]

class AddSVGDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent); self.setWindowTitle("Add Custom SVG Icon"); self.setMinimumWidth(480); self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint); self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet("QToolTip { background-color: #1e1e24; color: #ffffff; border: 1px solid rgba(220, 20, 60, 0.6); border-radius: 8px; padding: 6px 12px; }")
        self.created_key = None
        self._drag_pos = None
        self.setup_ui()

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

    def setup_ui(self):
        self.mf = QFrame(self); self.mf.setObjectName("addSvgFrame")
        self.mf.setStyleSheet("#addSvgFrame { background-color: #121212; border: 1px solid #2a2a30; border-radius: 20px; } QLabel { color: #ffffff; font-size: 13px; } QLineEdit, QTextEdit { background-color: #2a2a30; border: 1px solid #45475a; border-radius: 12px; padding: 10px; color: #ffffff; font-size: 12px; }")
        outer = QVBoxLayout(self); outer.setContentsMargins(0, 0, 0, 0); outer.addWidget(self.mf)
        cl = QVBoxLayout(self.mf); cl.setContentsMargins(22, 22, 22, 22); cl.setSpacing(10)
        h = QLabel("Add Custom SVG Icon"); h.setStyleSheet("font-size: 17px; font-weight: bold; color: white;"); cl.addWidget(h)
        
        cl.addWidget(QLabel("Icon Title / Name:"))
        self.name_inp = QLineEdit(); self.name_inp.setPlaceholderText("e.g. Valorant, Discord, Custom Logo")
        cl.addWidget(self.name_inp)

        cl.addWidget(QLabel("Search Keywords (comma-separated):"))
        self.kw_inp = QLineEdit(); self.kw_inp.setPlaceholderText("e.g. game, riot, fps, shooter, play")
        cl.addWidget(self.kw_inp)

        cl.addWidget(QLabel("SVG Content or Path(s):"))
        self.svg_inp = QTextEdit()
        self.svg_inp.setPlaceholderText("Paste raw <svg>...</svg> code or d=\"...\" path string")
        self.svg_inp.setFixedHeight(105)
        cl.addWidget(self.svg_inp)

        btns = QHBoxLayout()
        cancel_btn = QPushButton("Cancel"); cancel_btn.setCursor(Qt.PointingHandCursor); cancel_btn.setStyleSheet("QPushButton { background: #2a2a30; color: #ffffff; border-radius: 10px; padding: 8px 16px; } QPushButton:hover { background: #45475a; }")
        cancel_btn.clicked.connect(self.reject)
        save_btn = QPushButton("Add Icon"); save_btn.setCursor(Qt.PointingHandCursor); save_btn.setStyleSheet("QPushButton { background: #dc143c; color: #ffffff; border-radius: 10px; padding: 8px 16px; font-weight: bold; } QPushButton:hover { background: #ff2a55; }")
        save_btn.clicked.connect(self.save_svg)
        btns.addStretch(); btns.addWidget(cancel_btn); btns.addWidget(save_btn)
        cl.addLayout(btns)

    def save_svg(self):
        title = self.name_inp.text().strip()
        raw_svg = self.svg_inp.toPlainText().strip()
        if not title or not raw_svg:
            return
        
        paths = re.findall(r'd=["\']([^"\']+)["\']', raw_svg, re.IGNORECASE)
        if not paths:
            if raw_svg.startswith("M") or raw_svg.startswith("m"):
                paths = [raw_svg]

        if not paths:
            return

        from utils import get_glyphs_json_path, get_glyphs_data, generate_glyphs_data
        json_path = get_glyphs_json_path()
        glyphs = get_glyphs_data()

        clean_name = title.lower().replace(" ", "_")
        key = f"custom_{clean_name}"
        
        extra_keywords = [kw.strip().lower() for kw in self.kw_inp.text().split(',') if kw.strip()]
        base_keywords = [title.lower(), 'custom', 'svg']
        combined_keywords = list(dict.fromkeys(base_keywords + extra_keywords))

        glyphs[key] = {
            'name': title.lower(),
            'font': 'svg',
            'paths': paths,
            'keywords': combined_keywords
        }

        try:
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(glyphs, f, ensure_ascii=False, indent=2)
            try:
                generate_glyphs_data()
            except Exception:
                pass
            if hasattr(GlyphBrowserDialog, '_glyphs_cache'):
                GlyphBrowserDialog._glyphs_cache = None
            self.created_key = key
            self.accept()
        except Exception as e:
            print("Error saving SVG:", e)

class GlyphBrowserDialog(QDialog):
    preview_changed = pyqtSignal(str)
    def __init__(self, current_value='', parent=None):
        super().__init__(parent); _init_nilesoft_font(); self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog); self.setAttribute(Qt.WA_TranslucentBackground)
        self.selected = []; self.glyph_colors = [None, None]; self.result_value = current_value; self._parse_current(current_value)
        self.all_codes = get_all_font_glyphs(); self.setup_ui()
    def _parse_current(self, val):
        codes = _extract_glyph_codes(val)
        self.selected = codes[:2]
        colors = _extract_all_colors(val)
        while len(colors) < 2: colors.append(None)
        self.glyph_colors = list(colors[:2])
        while len(self.glyph_colors) < 2: self.glyph_colors.append(None)
    def setup_ui(self):
        self.mf = QFrame(self); self.mf.setObjectName("glyphFrame")
        self.mf.setStyleSheet("#glyphFrame { background-color: #121212; border: 1px solid #2a2a30; border-radius: 20px; }")
        self.mf.setMinimumSize(620, 520)
        outer = QVBoxLayout(self); outer.setContentsMargins(0, 0, 0, 0); outer.addWidget(self.mf)
        cl = QVBoxLayout(self.mf); cl.setContentsMargins(20, 20, 20, 20); cl.setSpacing(12)
        h = QLabel("Glyph Browser"); h.setStyleSheet("font-size: 18px; font-weight: bold; color: white;"); cl.addWidget(h)
        desc = QLabel("Select up to 2 glyphs. Single = image, Dual = layered icon."); desc.setStyleSheet("color: #888888; font-size: 12px;"); cl.addWidget(desc)
        top_row = QHBoxLayout()
        self.search_inp = QLineEdit(); self.search_inp.setPlaceholderText("Search glyphs or keywords...")
        self.search_inp.setStyleSheet("background-color: #2a2a30; border: 1px solid #45475a; border-radius: 10px; padding: 8px 12px; color: #ffffff; font-size: 13px;")
        
        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.setInterval(40)
        self.search_timer.timeout.connect(lambda: self.filter_glyphs(self.search_inp.text()))
        self.search_inp.textChanged.connect(lambda: self.search_timer.start())
        top_row.addWidget(self.search_inp, 1)

        self.upload_img_btn = QPushButton("\uE8E5")
        self.upload_img_btn.setFont(QFont('Segoe MDL2 Assets', 12))
        self.upload_img_btn.setFixedSize(38, 38)
        self.upload_img_btn.setCursor(Qt.PointingHandCursor)
        self.upload_img_btn.setToolTip("Upload Custom Image/Icon")
        self.upload_img_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 10px;
                color: #e0e0e0;
            }
            QPushButton:hover {
                background: rgba(220, 20, 60, 0.2);
                border: 1px solid #dc143c;
                color: #ffffff;
            }
        """)
        self.upload_img_btn.clicked.connect(self._upload_custom_icon)
        top_row.addWidget(self.upload_img_btn)
        
        self.preview_frame = QFrame(); self.preview_frame.setFixedSize(56, 44)
        self.preview_frame.setStyleSheet("background: rgba(255,255,255,0.05); border-radius: 10px; border: 1px solid rgba(255,255,255,0.1);")
        self.preview_layout = QVBoxLayout(self.preview_frame); self.preview_layout.setContentsMargins(0, 0, 0, 0)
        self._update_preview()
        top_row.addWidget(self.preview_frame)
        self.sel_label = QLabel(self._selection_text()); self.sel_label.setStyleSheet("color: #dc143c; font-size: 12px; font-weight: bold;"); self.sel_label.setFixedWidth(110)
        top_row.addWidget(self.sel_label)
        cl.addLayout(top_row)
        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setStyleSheet("background: transparent; border: none;")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.glyph_list = QListWidget()
        self.glyph_list.setViewMode(QListWidget.IconMode)
        self.glyph_list.setResizeMode(QListWidget.Adjust)
        self.glyph_list.setSpacing(4)
        self.glyph_list.setMovement(QListWidget.Static)
        self.glyph_list.setSelectionMode(QListWidget.MultiSelection)
        self.glyph_list.setStyleSheet("QListWidget { background: transparent; border: none; outline: none; } QListWidget::item { background: rgba(255,255,255,0.04); border-radius: 8px; margin: 2px; } QListWidget::item:hover { background: rgba(255,255,255,0.1); } QListWidget::item:selected { background: rgba(220, 20, 60, 0.2); border: 1px solid #dc143c; }")
        self.glyph_list.itemClicked.connect(self.on_item_clicked)
        self.glyph_list.verticalScrollBar().valueChanged.connect(self._on_scroll)
        cl.addWidget(self.glyph_list, 1)

        self._current_items = []
        self._rendered_count = 0
        self._batch_size = 80
        self._populate_list(self.all_codes)
        btns = QHBoxLayout()
        color_area = QHBoxLayout(); color_area.setSpacing(6)
        self.color1_enabled = QCheckBox(); self.color1_enabled.setFixedSize(16, 16)
        self.color1_enabled.setToolTip("Enable color for glyph 1")
        self.color1_enabled.setChecked(self.glyph_colors[0] is not None)
        self.color1_btn = QPushButton(); self.color1_btn.setFixedSize(28, 28); self.color1_btn.setCursor(Qt.PointingHandCursor)
        self.color1_btn.setToolTip("Color for Glyph 1")
        theme_cs = _get_theme_glyph_colors()
        self._update_color_btn(self.color1_btn, self.glyph_colors[0] or theme_cs[0])
        self.color1_btn.clicked.connect(lambda: self._open_color_picker(0))
        self.color1_btn.setEnabled(self.color1_enabled.isChecked())
        self.color1_enabled.stateChanged.connect(lambda s: (self.color1_btn.setEnabled(bool(s)), self._on_color_toggle(0, bool(s))))
        color_area.addWidget(self.color1_enabled); color_area.addWidget(self.color1_btn)
        c1l = QLabel("G1"); c1l.setStyleSheet("color: #888888; font-size: 10px;"); color_area.addWidget(c1l)
        color_area.addSpacing(8)
        self.color2_enabled = QCheckBox(); self.color2_enabled.setFixedSize(16, 16)
        self.color2_enabled.setToolTip("Enable color for glyph 2")
        self.color2_enabled.setChecked(self.glyph_colors[1] is not None)
        self.color2_btn = QPushButton(); self.color2_btn.setFixedSize(28, 28); self.color2_btn.setCursor(Qt.PointingHandCursor)
        self.color2_btn.setToolTip("Color for Glyph 2")
        theme_cs = _get_theme_glyph_colors()
        self._update_color_btn(self.color2_btn, self.glyph_colors[1] or theme_cs[1])
        self.color2_btn.clicked.connect(lambda: self._open_color_picker(1))
        self.color2_btn.setEnabled(self.color2_enabled.isChecked())
        self.color2_enabled.stateChanged.connect(lambda s: (self.color2_btn.setEnabled(bool(s)), self._on_color_toggle(1, bool(s))))
        color_area.addWidget(self.color2_enabled); color_area.addWidget(self.color2_btn)
        c2l = QLabel("G2"); c2l.setStyleSheet("color: #888888; font-size: 10px;"); color_area.addWidget(c2l)
        btns.addLayout(color_area)
        btns.addStretch()
        clear_btn = QPushButton("Clear"); clear_btn.setCursor(Qt.PointingHandCursor); clear_btn.setStyleSheet("QPushButton { background: #45475a; color: #ffffff; border-radius: 10px; padding: 8px 16px; font-weight: bold; } QPushButton:hover { background: #333333; }")
        clear_btn.clicked.connect(self.clear_selection)
        cancel_btn = QPushButton("Cancel"); cancel_btn.setCursor(Qt.PointingHandCursor); cancel_btn.setStyleSheet("QPushButton { background: #2a2a30; color: #ffffff; border-radius: 10px; padding: 8px 16px; } QPushButton:hover { background: #45475a; }")
        cancel_btn.clicked.connect(self.reject)
        ok_btn = QPushButton("Apply"); ok_btn.setCursor(Qt.PointingHandCursor); ok_btn.setStyleSheet("QPushButton { background: #dc143c; color: #ffffff; border-radius: 10px; padding: 8px 16px; font-weight: bold; } QPushButton:hover { background: #ff2a55; }")
        ok_btn.clicked.connect(self.apply_selection)
        btns.addWidget(clear_btn); btns.addWidget(cancel_btn); btns.addWidget(ok_btn)
        cl.addLayout(btns)

    def _upload_custom_icon(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Icon / Image", "", "Images (*.png *.ico *.bmp *.jpg *.svg)")
        if path:
            norm_path = os.path.normpath(path)
            dlg = LocalIconTintDialog(norm_path, self)
            if dlg.exec_():
                self.result_value = dlg.result_value
                self.preview_changed.emit(self.result_value)
                self.accept()
        
    def _update_color_btn(self, btn, color_hex):
        btn.setStyleSheet(f"QPushButton {{ background-color: {color_hex}; border-radius: 14px; border: 2px solid rgba(255,255,255,0.2); }} QPushButton:hover {{ border: 2px solid white; }} QPushButton:disabled {{ opacity: 0.3; background-color: #45475a; }}")
    def _on_color_toggle(self, idx, enabled):
        if enabled:
            if self.glyph_colors[idx] is None:
                def_cs = _get_theme_glyph_colors()
                self.glyph_colors[idx] = def_cs[idx]
                self._update_color_btn(self.color1_btn if idx == 0 else self.color2_btn, self.glyph_colors[idx])
        else:
            self.glyph_colors[idx] = None
        self._update_preview()
    def _open_color_picker(self, idx):
        from theme_editor_widget import MinimalColorPickerDialog
        def_cs = _get_theme_glyph_colors()
        current_c = self.glyph_colors[idx] or def_cs[idx]
        dlg = MinimalColorPickerDialog(current_c, f"glyph_{idx}", self)
        dlg.default_checkbox.hide()
        def on_color(key, color):
            hex_c = color.name()
            self.glyph_colors[idx] = hex_c
            self._update_color_btn(self.color1_btn if idx == 0 else self.color2_btn, hex_c)
            self._update_preview()
        dlg.colorSelected.connect(on_color)
        dlg.exec_()

    def on_item_clicked(self, item):
        code = item.data(Qt.UserRole)
        metadata, _ = self._load_glyphs_metadata()
        meta = metadata.get(code, {})
        is_svg = bool(meta.get('paths'))
        
        if code in self.selected:
            self.selected.remove(code)
            item.setSelected(False)
        else:
            if is_svg:
                for i in range(self.glyph_list.count()):
                    it = self.glyph_list.item(i)
                    it.setSelected(False)
                self.selected = [code]
                item.setSelected(True)
            else:
                svg_selected = [c for c in self.selected if metadata.get(c, {}).get('paths')]
                for old_code in svg_selected:
                    self.selected.remove(old_code)
                    for i in range(self.glyph_list.count()):
                        it = self.glyph_list.item(i)
                        if it.data(Qt.UserRole) == old_code:
                            it.setSelected(False)
                            break
                if len(self.selected) < 2:
                    self.selected.append(code)
                    item.setSelected(True)
                else:
                    old_code = self.selected.pop()
                    for i in range(self.glyph_list.count()):
                        it = self.glyph_list.item(i)
                        if it.data(Qt.UserRole) == old_code:
                            it.setSelected(False)
                            break
                    self.selected.append(code)
                    item.setSelected(True)
                    
        self.sel_label.setText(self._selection_text()); self._update_preview()
        self.preview_changed.emit(self._get_result_value())

    def _load_glyphs_metadata(self):
        from utils import get_glyphs_data, get_glyphs_json_path
        json_path = get_glyphs_json_path()
        curr_mtime = os.path.getmtime(json_path) if os.path.exists(json_path) else 0

        if hasattr(GlyphBrowserDialog, '_glyphs_cache') and GlyphBrowserDialog._glyphs_cache:
            if getattr(GlyphBrowserDialog, '_glyphs_mtime', 0) == curr_mtime and curr_mtime > 0:
                return GlyphBrowserDialog._glyphs_cache, GlyphBrowserDialog._glyphs_reverse_map

        data = get_glyphs_data()

        cache = {}
        reverse_map = {}
        if data:
            for key, item in data.items():
                try:
                    code_int = int(key, 16)
                except ValueError:
                    code_int = key
                name = str(item.get('name', '')).strip().lower()
                keywords = [str(kw).strip().lower() for kw in item.get('keywords', []) if str(kw).strip()]
                font_family = str(item.get('font', '')).strip()
                paths = item.get('paths', [])
                cache[code_int] = {
                    'key': key,
                    'name': name,
                    'keywords': keywords,
                    'font': font_family,
                    'paths': paths
                }
                reverse_map[code_int] = name

        GlyphBrowserDialog._glyphs_cache = cache
        GlyphBrowserDialog._glyphs_reverse_map = reverse_map
        GlyphBrowserDialog._glyphs_mtime = curr_mtime
        return cache, reverse_map

    def _on_scroll(self, value):
        scroll_bar = self.glyph_list.verticalScrollBar()
        if scroll_bar.maximum() - value < 150:
            self._render_next_batch()

    def _populate_list(self, items_to_show, preserve_order=False):
        self.glyph_list.setUpdatesEnabled(False)
        self.glyph_list.clear()
        metadata, rev_map = self._load_glyphs_metadata()
        
        if not hasattr(self, '_icon_cache'):
            self._icon_cache = {}

        processed = []
        for entry in items_to_show:
            if isinstance(entry, tuple):
                code, meta_name = entry
            else:
                code = entry
                meta_name = rev_map.get(code, '')
            processed.append((code, meta_name))
            
        if preserve_order:
            self._current_items = processed
        else:
            self._current_items = sorted(processed, key=lambda x: (0 if x[0] in self.selected else 1, 0 if isinstance(x[0], int) else 1, str(x[0])))

        self._rendered_count = 0
        self._render_next_batch()
        self.glyph_list.setUpdatesEnabled(True)

    def _render_next_batch(self):
        if self._rendered_count >= len(self._current_items):
            return

        metadata, _ = self._load_glyphs_metadata()
        batch = self._current_items[self._rendered_count:self._rendered_count + self._batch_size]
        self._rendered_count += len(batch)

        for code, meta_name in batch:
            meta = metadata.get(code, {})
            paths = meta.get('paths', [])
            item = QListWidgetItem()
            clean_title = meta_name
            if clean_title.startswith('ri '): clean_title = clean_title[3:]
            elif clean_title.startswith('la '): clean_title = clean_title[3:]
            tooltip = clean_title if clean_title else (f"\\u{code:04X}" if isinstance(code, int) else str(code))

            if paths:
                if code not in self._icon_cache:
                    paths_xml = ''.join([f'<path fill="#ffffff" d="{d}"/>' for d in paths])
                    svg_xml = f'<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">{paths_xml}</svg>'
                    from PyQt5.QtSvg import QSvgRenderer
                    from PyQt5.QtGui import QPixmap, QPainter, QIcon
                    from PyQt5.QtCore import QByteArray
                    renderer = QSvgRenderer(QByteArray(svg_xml.encode('utf-8')))
                    pixmap = QPixmap(32, 32)
                    pixmap.fill(Qt.transparent)
                    p = QPainter(pixmap)
                    renderer.render(p)
                    p.end()
                    self._icon_cache[code] = QIcon(pixmap)
                item.setIcon(self._icon_cache[code])
            else:
                item.setText(chr(code) if isinstance(code, int) else str(code))
                item.setFont(QFont(NILESOFT_FONT_FAMILY, 18))

            item.setTextAlignment(Qt.AlignCenter)
            item.setToolTip(tooltip)
            item.setData(Qt.UserRole, code)
            item.setSizeHint(QSize(46, 46))
            self.glyph_list.addItem(item)
            if code in self.selected:
                item.setSelected(True)

    def filter_glyphs(self, text):
        raw_query = text.strip()
        if not raw_query:
            self._populate_list(self.all_codes, preserve_order=False)
            return

        q_lower = raw_query.lower()
        q_hex = q_lower.replace("\\u", "").replace("0x", "")
        metadata, _ = self._load_glyphs_metadata()

        matched_results = []
        for code in self.all_codes:
            code_hex = f"{code:04X}" if isinstance(code, int) else str(code)
            score = float('inf')
            
            meta = metadata.get(code)
            meta_name = meta['name'] if meta else ''
            keywords = meta['keywords'] if meta else []

            if meta_name and meta_name == q_lower:
                score = 0
            elif keywords and any(kw == q_lower for kw in keywords):
                score = 1
            elif q_hex and isinstance(code, int) and code_hex.lower() == q_hex:
                score = 2
            elif isinstance(code, int) and raw_query == chr(code):
                score = 3
            elif meta_name and q_lower in re.split(r'[ _\-]+', meta_name):
                score = 4
            elif meta_name and meta_name.startswith(q_lower):
                score = 5 + min(len(meta_name) - len(q_lower), 50) * 0.01
            elif keywords and any(kw.startswith(q_lower) for kw in keywords):
                matching_kw = next(kw for kw in keywords if kw.startswith(q_lower))
                score = 6 + min(len(matching_kw) - len(q_lower), 50) * 0.01
            elif meta_name and q_lower in meta_name:
                score = 7 + min(len(meta_name), 50) * 0.01
            elif keywords and any(q_lower in kw for kw in keywords):
                score = 8
            elif q_hex and q_hex in code_hex.lower():
                score = 9
            elif meta_name and _fuzzy_match(q_lower, meta_name):
                score = 10
            elif keywords and any(_fuzzy_match(q_lower, kw) for kw in keywords):
                score = 11

            if score < float('inf'):
                matched_results.append((score, len(meta_name), code, meta_name))

        matched_results.sort(key=lambda x: (
            0 if x[2] in self.selected else 1,
            x[0],
            x[1],
            0 if isinstance(x[2], int) else 1,
            str(x[2])
        ))
        filtered_codes = [(item[2], item[3]) for item in matched_results]
        self._populate_list(filtered_codes, preserve_order=True)

    def clear_selection(self):
        self.selected.clear()
        self.glyph_list.clearSelection()
        self.sel_label.setText(self._selection_text()); self._update_preview()
        self.preview_changed.emit('')
    def _get_result_value(self):
        if len(self.selected) == 0: return ''
        metadata, _ = self._load_glyphs_metadata()
        def_cs = _get_theme_glyph_colors()
        
        selected_code = self.selected[0]
        meta = metadata.get(selected_code, {})
        paths = meta.get('paths', [])
        
        if paths:
            c1 = self.glyph_colors[0] if self.color1_enabled.isChecked() else None
            fill_val = c1 if c1 else "@image.color1"
            paths_xml = ''.join([f'<path fill="{fill_val}" d="{d}"/>' for d in paths])
            svg_str = f'<svg fill="none" viewBox="0 0 24 24">{paths_xml}</svg>'
            return f"'{svg_str}'"
            
        c1 = self.glyph_colors[0] if self.color1_enabled.isChecked() else None
        c2 = self.glyph_colors[1] if self.color2_enabled.isChecked() else None
        if len(self.selected) == 1:
            g = f"\\u{self.selected[0]:04X}"
            if c1: return f'[["{g}", {c1}]]'
            return f'["{g}"]'
        codes = [f"\\u{c:04X}" if isinstance(c, int) else str(c) for c in self.selected]
        parts = []
        for i, g in enumerate(codes):
            en = self.color1_enabled if i == 0 else self.color2_enabled
            c = self.glyph_colors[i] if (i < 2 and en.isChecked()) else None
            parts.append(f'["{g}", {c}]' if c else f'["{g}"]')
        return f"[{', '.join(parts)}]"
    def apply_selection(self):
        self.result_value = self._get_result_value()
        self.accept()

    def _selection_text(self):
        if not self.selected: return "None selected"
        return " + ".join([f"\\u{c:04X}" if isinstance(c, int) else str(c) for c in self.selected])

    def _update_preview(self):
        if not hasattr(self, 'preview_layout'): return
        for i in reversed(range(self.preview_layout.count())):
            w = self.preview_layout.itemAt(i).widget()
            if w: w.setParent(None)
        if self.selected:
            c1 = self.glyph_colors[0] if not hasattr(self, 'color1_enabled') or self.color1_enabled.isChecked() else None
            c2 = self.glyph_colors[1] if not hasattr(self, 'color2_enabled') or self.color2_enabled.isChecked() else None
            metadata, _ = self._load_glyphs_metadata()
            font_families = [NILESOFT_FONT_FAMILY for _ in self.selected]
            pw = GlyphPreviewLabel(self.selected, size=44, font_family=NILESOFT_FONT_FAMILY, colors=[c1, c2], font_families=font_families); pw.setFixedSize(50, 44)
            self.preview_layout.addWidget(pw); pw.show()
        else:
            pl = QLabel("\u2726"); pl.setAlignment(Qt.AlignCenter); pl.setStyleSheet("color: #333333; font-size: 24px; background: transparent;"); self.preview_layout.addWidget(pl); pl.show()
    def paintEvent(self, event):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        from PyQt5.QtGui import QBrush
        p.setBrush(QBrush(QColor(0, 0, 0, 80))); p.setPen(Qt.NoPen)
        p.drawRoundedRect(self.rect(), 20, 20); p.end()

class LocalIconTintDialog(QDialog):
    def __init__(self, image_path, parent=None):
        super().__init__(parent)
        self.image_path = image_path
        self.tint_enabled = False
        self.tint_color = _get_theme_glyph_colors()[0]
        self.result_value = f"'{self.image_path}'"
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(380, 260)
        self.setup_ui()
    def setup_ui(self):
        layout = QVBoxLayout(self)
        frame = QFrame()
        frame.setStyleSheet("QFrame { background-color: #121212; border: 1px solid #2a2a30; border-radius: 15px; } QLabel { border: none; }")
        layout.addWidget(frame)
        cl = QVBoxLayout(frame); cl.setContentsMargins(20, 20, 20, 20)
        title = QLabel("Configure Local Icon")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: white;")
        cl.addWidget(title)
        self.preview = QLabel()
        self.preview.setFixedSize(64, 64)
        self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setStyleSheet("background: rgba(255,255,255,0.05); border-radius: 12px; border: 1px solid rgba(255,255,255,0.1);")
        preview_layout = QHBoxLayout(); preview_layout.addWidget(self.preview); cl.addLayout(preview_layout)
        opt_layout = QHBoxLayout()
        self.toggle = QCheckBox("Apply Tint Color")
        self.toggle.setStyleSheet("QCheckBox { color: #ffffff; font-size: 13px; } QCheckBox::indicator { width: 18px; height: 18px; border-radius: 4px; border: 1px solid #45475a; background: #2a2a30; } QCheckBox::indicator:checked { background: #dc143c; border: 1px solid #dc143c; }")
        self.toggle.toggled.connect(self.on_toggle)
        opt_layout.addWidget(self.toggle)
        self.color_btn = QPushButton()
        self.color_btn.setFixedSize(28, 28)
        self.color_btn.setCursor(Qt.PointingHandCursor)
        self.color_btn.clicked.connect(self.pick_color)
        opt_layout.addWidget(self.color_btn); opt_layout.addStretch(); cl.addLayout(opt_layout)
        btns = QHBoxLayout()
        cancel = QPushButton("Cancel"); cancel.setStyleSheet("QPushButton { background: #2a2a30; color: #ffffff; border-radius: 10px; padding: 8px 16px; font-weight: bold; } QPushButton:hover { background: #45475a; }")
        cancel.clicked.connect(self.reject)
        ok = QPushButton("Apply"); ok.setStyleSheet("QPushButton { background: #dc143c; color: #ffffff; border-radius: 10px; padding: 8px 16px; font-weight: bold; } QPushButton:hover { background: #ff2a55; }")
        ok.clicked.connect(self.accept_result)
        btns.addStretch(); btns.addWidget(cancel); btns.addWidget(ok); cl.addLayout(btns)
        self.update_ui()
    def update_ui(self):
        self.color_btn.setEnabled(self.tint_enabled)
        color_hex = self.tint_color if self.tint_enabled else "#45475a"
        self.color_btn.setStyleSheet(f"QPushButton {{ background-color: {color_hex}; border-radius: 14px; border: 2px solid rgba(255,255,255,0.2); }} QPushButton:hover {{ border: 2px solid white; }} QPushButton:disabled {{ opacity: 0.3; background-color: #45475a; }}")
        from PyQt5.QtGui import QPixmap, QImage, QColor
        pm = QPixmap()
        try:
            with open(self.image_path, 'rb') as f: data = f.read()
            pm.loadFromData(data)
        except: pass

        if not pm.isNull():
            if self.tint_enabled:
                img = pm.toImage().convertToFormat(QImage.Format_ARGB32)
                c = QColor(self.tint_color)
                for y in range(img.height()):
                    for x in range(img.width()):
                        p = img.pixelColor(x, y)
                        if p.alpha() > 0:
                            c.setAlpha(p.alpha())
                            img.setPixelColor(x, y, c)
                pm = QPixmap.fromImage(img)
            self.preview.setPixmap(pm.scaled(48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation))
    def on_toggle(self, checked):
        self.tint_enabled = checked; self.update_ui()
    def pick_color(self):
        from theme_editor_widget import MinimalColorPickerDialog
        dlg = MinimalColorPickerDialog(self.tint_color, "icon_tint", self)
        dlg.default_checkbox.hide()
        def on_color(key, color):
            self.tint_color = color.name(); self.update_ui()
        dlg.colorSelected.connect(on_color); dlg.exec_()
    def accept_result(self):
        try:
            self.result_value, self.saved_path = save_local_icon(self.image_path, self.tint_color, self.tint_enabled)
            self.accept()
        except Exception as e:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Save Error", f"Failed to save icon. The file may be in use by another process.\n\nError: {str(e)}")

class ClickablePreviewLabel(QLabel):
    clicked = pyqtSignal()
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.PointingHandCursor)
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
            event.accept()
        else:
            super().mousePressEvent(event)

class ImportEditorDialog(QDialog):
    def __init__(self, data=None, parent=None, embed_mode=False):
        super().__init__(parent)
        self.data = data or {}
        self.props = data.get('props', {}).copy()
        self.embed_mode = embed_mode
        self.setMinimumWidth(500)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet("QToolTip { background-color: #1e1e24; color: #ffffff; border: 1px solid rgba(220, 20, 60, 0.6); border-radius: 8px; padding: 6px 12px; font-family: 'Segoe UI Variable Display'; font-size: 12px; font-weight: bold; }")
        self._drag_pos = None
        self.setup_ui()

    def mousePressEvent(self, event):
        if not self.embed_mode and event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if not self.embed_mode and event.buttons() == Qt.LeftButton and self._drag_pos is not None:
            self.move(event.globalPos() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None

    def setup_ui(self):
        self.mf = QFrame(self); self.mf.setObjectName("mainFrame")
        self.mf.setStyleSheet("""
            #mainFrame { background-color: #121212; border: 1px solid #2a2a30; border-radius: 20px; } 
            QLabel { color: #ffffff; font-size: 12px; } 
            QLineEdit { background-color: #2a2a30; border: 1px solid #45475a; border-radius: 10px; padding: 6px 10px; color: #ffffff; selection-background-color: #dc143c; } 
            QLineEdit:focus { border: 1px solid #dc143c; }
            QComboBox { background-color: #2a2a30; border: 1px solid #45475a; border-radius: 10px; padding: 6px 10px; color: #ffffff; }
            QComboBox:hover, QComboBox:focus { border: 1px solid #dc143c; }
            QComboBox QAbstractItemView { background-color: #121212; border: 1px solid #2a2a30; selection-background-color: #2a2a30; selection-color: #dc143c; color: #ffffff; outline: none; border-radius: 8px; padding: 4px; }
            QPushButton#saveBtn { background-color: #dc143c; color: #ffffff; border-radius: 10px; padding: 8px 18px; font-weight: bold; } 
            QPushButton#saveBtn:hover { background-color: #ff2a55; }
            QPushButton#cancelBtn { background-color: #2a2a30; color: #ffffff; border-radius: 10px; padding: 8px 18px; }
            QPushButton#cancelBtn:hover { background-color: #45475a; }
        """)
        layout = QVBoxLayout(self); layout.setContentsMargins(0, 0, 0, 0); layout.addWidget(self.mf)
        cl = QVBoxLayout(self.mf); cl.setContentsMargins(18, 16, 18, 16); cl.setSpacing(10)
        
        if not self.embed_mode:
            h = QLabel(f"Edit {self.data.get('type', 'Item').title()}"); h.setStyleSheet("font-size: 16px; font-weight: bold; color: white;"); cl.addWidget(h)
        
        ag = QFrame(); ag.setStyleSheet("background: rgba(255,255,255,0.03); border-radius: 12px; padding: 10px;"); al = QGridLayout(ag); al.setVerticalSpacing(8); al.setHorizontalSpacing(10); cl.addWidget(ag)
        
        self.t_inp = QLineEdit(self.props.get('title', '').strip('\'\"')); al.addWidget(QLabel("Title:"), 0, 0); al.addWidget(self.t_inp, 0, 1)
        
        ic_row = QHBoxLayout()
        ic_row.setSpacing(6)
        
        self.c_container = QWidget()
        self.c_lay = QHBoxLayout(self.c_container)
        self.c_lay.setContentsMargins(0, 0, 0, 0)
        self.c_lay.setSpacing(4)
        self.c_lay.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        
        self.ic_prev_lbl = ClickablePreviewLabel()
        self.ic_prev_lbl.setFixedSize(46, 46)
        self.ic_prev_lbl.setAlignment(Qt.AlignCenter)
        self.ic_prev_lbl.setToolTip("Click to Browse Glyphs / Upload Icon")
        self.ic_prev_lbl.setStyleSheet("""
            ClickablePreviewLabel {
                background: rgba(255,255,255,0.05); 
                border-radius: 12px; 
                border: 1px solid rgba(255,255,255,0.12);
            }
            ClickablePreviewLabel:hover {
                border: 1px solid #dc143c;
                background: rgba(220, 20, 60, 0.12);
            }
        """)
        self.ic_prev_lbl.clicked.connect(self._open_glyph_browser)
        
        self.ic_inp = QLineEdit(self.props.get('icon') or self.props.get('image') or '')
        self.ic_inp.setPlaceholderText("e.g. \\uE102, image path, or image.res(...)")
        self.ic_inp.textChanged.connect(self._update_colors_ui)
        self.ic_inp.textChanged.connect(lambda t: _update_label_asset(self.ic_prev_lbl, t))
        
        btn_action_style = """
            QPushButton {
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 10px;
                color: #e0e0e0;
                padding: 0;
            }
            QPushButton:hover {
                background: rgba(220, 20, 60, 0.2);
                border: 1px solid #dc143c;
                color: #ffffff;
            }
        """

        self.ic_inherit = QPushButton("\uE777")
        self.ic_inherit.setFont(QFont('Segoe MDL2 Assets', 13))
        self.ic_inherit.setFixedSize(34, 34)
        self.ic_inherit.setCursor(Qt.PointingHandCursor)
        self.ic_inherit.setToolTip("Inherit Icon from Target Command/File")
        self.ic_inherit.setStyleSheet(btn_action_style)
        self.ic_inherit.clicked.connect(self._inherit_icon)

        self.ic_remove = QPushButton("\uE74D")
        self.ic_remove.setFont(QFont('Segoe MDL2 Assets', 13))
        self.ic_remove.setFixedSize(34, 34)
        self.ic_remove.setCursor(Qt.PointingHandCursor)
        self.ic_remove.setToolTip("Remove Icon")
        self.ic_remove.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.03);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 10px;
                color: #888888;
                padding: 0;
            }
            QPushButton:hover {
                background: rgba(255, 50, 50, 0.25);
                border: 1px solid #ff4444;
                color: #ffffff;
            }
        """)
        self.ic_remove.clicked.connect(lambda: self.ic_inp.setText(""))

        ic_row.addWidget(self.c_container)
        ic_row.addWidget(self.ic_prev_lbl)
        ic_row.addWidget(self.ic_inp, 1)
        if not self.embed_mode:
            ic_row.addWidget(self.ic_inherit)
            ic_row.addWidget(self.ic_remove)
        al.addWidget(QLabel("Icon/Image:"), 1, 0); al.addLayout(ic_row, 1, 1)
        _update_label_asset(self.ic_prev_lbl, self.ic_inp.text()); self._update_colors_ui()

        self.p_box = NonScrollComboBox(); self.p_box.addItems(ModifyRuleEditorDialog.POS_OPTIONS)
        self.p_box.setFixedWidth(110)
        p_val = str(self.props.get('pos', '')).strip('\'"')
        (self.p_box.setCurrentText(p_val) if p_val in ModifyRuleEditorDialog.POS_OPTIONS else (self.p_box.addItem(p_val), self.p_box.setCurrentText(p_val)))
        
        v_val = str(self.props.get('vis', ''))
        self.vis_widget = VisibilityWidget()
        self.vis_widget.set_value(v_val)
        al.addWidget(QLabel("Visibility:"), 2, 0); al.addWidget(self.vis_widget, 2, 1)

        self.type_widget = TypeWidget()
        self.type_widget.set_value(self.props.get('type', ''))
        al.addWidget(QLabel("Show in:"), 3, 0); al.addWidget(self.type_widget, 3, 1)
        
        m_opts = ["None", "Main", "Options"]
        self.m_box = NonScrollComboBox(); self.m_box.addItems(m_opts)
        self.m_box.setFixedWidth(130)
        
        curr_m = str(self.props.get('menu', '')).strip('\'"')
        curr_m_low = curr_m.lower()
        if 'menu' not in self.props: self.m_box.setCurrentText("None")
        elif not curr_m or curr_m_low in ("main", "menu.main"): self.m_box.setCurrentText("Main")
        elif curr_m_low in ("options", "title.options"): self.m_box.setCurrentText("Options")
        else:
            if curr_m not in [self.m_box.itemText(i) for i in range(self.m_box.count())]:
                self.m_box.addItem(curr_m)
            self.m_box.setCurrentText(curr_m)
        
        self.sep_box = NonScrollComboBox(); self.sep_box.addItems(["None", "Before", "After", "Both"])
        self.sep_box.setFixedWidth(130)
        curr_sep = str(self.props.get('sep', '')).strip('\'"')
        if curr_sep:
            if curr_sep.lower() in ('true', '1'): self.sep_box.setCurrentText("Before")
            else: self.sep_box.setCurrentText(curr_sep.title())

        m_row = QHBoxLayout()
        m_row.addWidget(self.m_box)
        m_row.addStretch()
        al.addWidget(QLabel("Move to:"), 4, 0)
        al.addLayout(m_row, 4, 1)

        p_row = QHBoxLayout()
        p_row.addWidget(self.p_box)
        p_row.addStretch()
        al.addWidget(QLabel("Position:"), 5, 0)
        al.addLayout(p_row, 5, 1)

        sep_row = QHBoxLayout()
        sep_row.addWidget(self.sep_box)
        sep_row.addStretch()
        al.addWidget(QLabel("Separator:"), 6, 0)
        al.addLayout(sep_row, 6, 1)

        if not self.embed_mode:
            btns = QHBoxLayout(); c = QPushButton("Cancel"); c.setObjectName("cancelBtn"); c.clicked.connect(self.reject); c.setCursor(Qt.PointingHandCursor); s = QPushButton("Save Changes"); s.setObjectName("saveBtn"); s.clicked.connect(self.accept); s.setCursor(Qt.PointingHandCursor); btns.addStretch(); btns.addWidget(c); btns.addWidget(s); cl.addLayout(btns)
            
        self.ic_inp.textChanged.connect(lambda: self.reload_requested.emit())
        self.t_inp.textChanged.connect(lambda: self.reload_requested.emit())
        self.p_box.currentTextChanged.connect(lambda: self.reload_requested.emit())
        self.m_box.currentTextChanged.connect(lambda: self.reload_requested.emit())
        self.sep_box.currentTextChanged.connect(lambda: self.reload_requested.emit())
        self.vis_widget.valueChanged.connect(lambda _: self.reload_requested.emit())
        self.type_widget.valueChanged.connect(lambda _: self.reload_requested.emit())

    reload_requested = pyqtSignal()

    def _inherit_icon(self):
        cmd = self.props.get('cmd', '') or self.props.get('path', '') or self.props.get('title', '')
        target_path = _find_target_executable_or_shortcut(cmd)
        if not target_path:
            file_path, _ = QFileDialog.getOpenFileName(self, "Select Executable/Shortcut/Icon to Inherit From", "C:\\Program Files", "Executables & Shortcuts (*.exe *.lnk *.ico *.dll *.png)")
            if file_path:
                target_path = file_path
        if target_path:
            norm = os.path.normpath(target_path).replace('\\', '/')
            self.ic_inp.setText(f"image.res('{norm}')")

    def _update_colors_ui(self):
        if not hasattr(self, 'c_lay'): return
        while self.c_lay.count():
            it = self.c_lay.takeAt(0); (it.widget().deleteLater() if it.widget() else None)
        colors = _extract_all_colors(self.ic_inp.text()); theme_cs = _get_theme_glyph_colors(); codes = _extract_glyph_codes(self.ic_inp.text())
        for i in range(max(len(codes) if codes else (1 if self.ic_inp.text() else 0), len(colors))):
            if i >= 2: break
            c = colors[i] if i < len(colors) else None
            btn = ColorPellet(c or theme_cs[min(i, 1)]); btn.clicked.connect(lambda checked, idx=i, oc=c: self._pick_color(idx, oc)); self.c_lay.addWidget(btn)
        if codes and any(colors):
            sync_btn = IconSyncButton(self)
            sync_btn.setToolTip("Sync with Theme (Remove custom colors)")
            sync_btn.clicked.connect(self._reset_glyph_colors)
            self.c_lay.insertWidget(0, sync_btn)

    def _reset_glyph_colors(self):
        codes = _extract_glyph_codes(self.ic_inp.text())
        if codes: self.ic_inp.setText(_build_glyph_val(codes, []))
    def _pick_color(self, idx, old_color):
        theme_cs = _get_theme_glyph_colors()
        dlg = MinimalColorPickerDialog(old_color or theme_cs[min(idx, 1)], f"svg_c_{idx}", self); dlg.default_checkbox.hide()
        
        def on_color(key, hex_color):
            val = self.ic_inp.text().strip()
            codes = _extract_glyph_codes(val)
            if codes:
                self.ic_inp.setText(_get_new_asset_value(val, old_color, hex_color, idx=idx))
            else:
                path, _ = _extract_img_path_and_color(val)
                resolved = _resolve_app_dir_path(path)
                if resolved and os.path.exists(resolved):
                    new_asset_path, _ = save_local_icon(resolved, hex_color, True)
                    self.ic_inp.setText(f"'{new_asset_path}'")
        
        dlg.colorSelected.connect(on_color); dlg.exec_()
    def _open_glyph_browser(self):
        orig = self.ic_inp.text().strip()
        dlg = GlyphBrowserDialog(orig, self)
        if dlg.exec_():
            self.ic_inp.setText(dlg.result_value)
        else:
            self.ic_inp.setText(orig)
    def _browse_icon(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Icon", "", "Images (*.png *.ico *.bmp *.jpg *.svg)")
        if path:
            dlg = LocalIconTintDialog(os.path.normpath(path), self)
            if dlg.exec_(): self.ic_inp.setText(dlg.result_value)
    def get_props(self):
        p = self.props.copy()
        title_val = self.t_inp.text().strip()
        p['title'] = f"'{title_val}'" if title_val and ' ' in title_val else title_val
        p['pos'] = self.p_box.currentText()
        vis_val = self.vis_widget.get_value()
        if vis_val:
            p['vis'] = vis_val
        else:
            p.pop('vis', None)

        type_val = self.type_widget.get_value()
        if type_val:
            p['type'] = type_val
        else:
            p.pop('type', None)
        
        m_sel = self.m_box.currentText()
        if m_sel == "None": p['menu'] = None
        elif m_sel == "Main": p['menu'] = ""
        elif m_sel == "Options": p['menu'] = "options"
        
        icon_val = self.ic_inp.text().strip()
        if not icon_val:
            for ik in ('image', 'icon', 'fill', 'viewBox', 'd'):
                p.pop(ik, None)
        else:
            (p.__setitem__('image', icon_val) if 'image' in p or 'icon' not in p else p.__setitem__('icon', icon_val))
            
        sv = self.sep_box.currentText().lower()
        if sv == "none": p.pop('sep', None); p.pop('separator', None)
        elif sv == "before": p['sep'] = True
        else: p['sep'] = sv
        return p

    def get_changes(self):
        p1 = self.get_props()
        p2 = self.props
        changes = []
        key_names = {
            'title': 'Title',
            'pos': 'Position',
            'vis': 'Visibility',
            'type': 'Show in',
            'menu': 'Move to',
            'sep': 'Separator',
            'image': 'Icon / Image',
            'icon': 'Icon / Image'
        }
        def format_user_friendly(prop_key, val):
            val_clean = str(val or '').strip('\'" ')
            if prop_key == 'vis':
                vl = val_clean.lower().strip()
                if not vl or vl in ("normal", "always visible", "vis.normal", "1"): return "Normal"
                if vl in ("vis.remove", "key.remove", "vis.hidden", "key.hidden", "remove", "hidden", "0"): return "Hide"
                if vl in ("key.shift()", "vis.shift", "shift", "key.shift"): return "Shift"
                if vl in ("key.control()", "key.ctrl()", "vis.control", "vis.ctrl", "control", "ctrl", "key.control", "key.ctrl"): return "Ctrl"
                if vl in ("key.capslock()", "key.caps()", "vis.capslock", "vis.caps", "capslock", "caps", "key.capslock", "key.caps"): return "Caps"
                if vl in ("key.lbutton()", "key.lmb()", "vis.lbutton", "vis.lmb", "lbutton", "lmb", "key.lbutton"): return "LMB"
                return val_clean
            if prop_key == 'sep':
                vl = val_clean.lower()
                if vl in ("true", "1", "before"): return "Before"
                if vl == "after": return "After"
                if vl == "both": return "Both"
                if vl in ("false", "0", "none", ""): return "None"
                return val_clean.title()
            if prop_key == 'menu':
                vl = val_clean.lower()
                if not vl or vl in ("none", "main", "menu.main"): return "Main"
                if vl in ("options", "title.options"): return "Options"
                return val_clean
            return val_clean or "(empty)"

        for k in ['title', 'pos', 'vis', 'type', 'menu', 'sep']:
            v1 = str(p1.get(k, '')).strip('\'" ')
            v2 = str(p2.get(k, '')).strip('\'" ')
            if k == 'vis':
                v1_low = v1.lower()
                v2_low = v2.lower()
                v1_norm = "" if v1_low in ("normal", "always visible", "vis.normal") else ("vis.remove" if v1_low in ("vis.remove", "vis.hidden", "key.remove", "key.hidden", "remove", "hidden") else v1_low)
                v2_norm = "" if v2_low in ("normal", "always visible", "vis.normal") else ("vis.remove" if v2_low in ("vis.remove", "vis.hidden", "key.remove", "key.hidden", "remove", "hidden") else v2_low)
                if v1_norm == v2_norm: continue
            if k == 'menu':
                v1_norm = "" if v1.lower() in ("none", "main", "menu.main") else v1
                v2_norm = "" if v2.lower() in ("none", "main", "menu.main") else v2
                if v1_norm.lower() == v2_norm.lower(): continue
            if k == 'sep':
                v1_norm = "true" if v1.lower() in ("true", "1") else "false" if v1.lower() in ("false", "0", "none", "") else v1.lower()
                v2_norm = "true" if v2.lower() in ("true", "1") else "false" if v2.lower() in ("false", "0", "none", "") else v2.lower()
                if v1_norm == v2_norm: continue
            if v1.lower() != v2.lower():
                display_k = key_names.get(k, k.title())
                changes.append(f"{display_k}: {format_user_friendly(k, v2)} ➔ {format_user_friendly(k, v1)}")
        
        i1 = str(p1.get('icon') or p1.get('image') or '').strip('\'" ')
        i2 = str(p2.get('icon') or p2.get('image') or '').strip('\'" ')
        if i1 != i2:
            changes.append(f"Icon: '{i2 or '(none)'}' ➔ '{i1 or '(none)'}'")
        return changes

    def is_dirty(self):
        return len(self.get_changes()) > 0

    def reject(self):
        if not self.embed_mode and self.is_dirty():
            from utils import UnsavedChangesDialog
            changes = self.get_changes()
            dialog = UnsavedChangesDialog(None, text="You have unsaved changes in this item. Do you want to save them?", changes=changes)
            res = dialog.exec_()
            if res == 1:
                self.accept(); return
            elif res == 2:
                return
        super().reject()

class MultiItemEditDialog(QDialog):
    def __init__(self, items, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(650, 680)
        self._drag_pos = None
        
        main_frame = QFrame(self)
        main_frame.setObjectName("multiMainFrame")
        main_frame.setStyleSheet("""
            #multiMainFrame { background-color: #121212; border: 1px solid #2a2a30; border-radius: 20px; }
            QTabWidget::pane { border: 1px solid #2a2a30; border-radius: 12px; background: transparent; }
            QTabBar::tab { background: rgba(255,255,255,0.05); color: #b0b0b0; padding: 6px 14px; border-top-left-radius: 8px; border-top-right-radius: 8px; margin-right: 4px; height: 26px; font-weight: bold; }
            QTabBar::tab:selected { background: rgba(220, 20, 60, 0.2); color: #dc143c; border: 1px solid rgba(220, 20, 60, 0.4); }
        """)
        
        dlg_layout = QVBoxLayout(self)
        dlg_layout.setContentsMargins(0, 0, 0, 0)
        dlg_layout.addWidget(main_frame)
        
        layout = QVBoxLayout(main_frame)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)
        
        # Header titlebar
        title_bar = QHBoxLayout()
        title_label = QLabel("Edit Items/Menus")
        title_label.setFont(QFont('Segoe UI Variable Display', 15, QFont.Bold))
        title_label.setStyleSheet("color: white;")
        title_bar.addWidget(title_label)
        title_bar.addStretch()
        
        close_btn = QPushButton("\uE711")
        close_btn.setFont(QFont('Segoe MDL2 Assets', 10))
        close_btn.setFixedSize(28, 28)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet("QPushButton { background: rgba(255,255,255,0.05); border: none; border-radius: 14px; color: #b0b0b0; } QPushButton:hover { background: rgba(220,20,60,0.2); color: #dc143c; }")
        close_btn.clicked.connect(self.reject)
        title_bar.addWidget(close_btn)
        layout.addLayout(title_bar)
        
        embed_style = """
            #mainFrame { background: transparent; border: none; }
            QLabel { color: #ffffff; font-size: 12px; } 
            QLineEdit { background-color: #2a2a30; border: 1px solid #45475a; border-radius: 10px; padding: 6px 10px; color: #ffffff; selection-background-color: #dc143c; } 
            QLineEdit:focus { border: 1px solid #dc143c; }
            QComboBox { background-color: #2a2a30; border: 1px solid #45475a; border-radius: 10px; padding: 6px 10px; color: #ffffff; }
            QComboBox:hover, QComboBox:focus { border: 1px solid #dc143c; }
            QComboBox QAbstractItemView { background-color: #121212; border: 1px solid #2a2a30; selection-background-color: #2a2a30; selection-color: #dc143c; color: #ffffff; outline: none; border-radius: 8px; padding: 4px; }
        """
        self.editors = []
        if len(items) == 1:
            editor = ImportEditorDialog(items[0], self, embed_mode=True)
            editor.mf.setStyleSheet(embed_style)
            layout.addWidget(editor)
            self.editors.append((items[0], editor))
        else:
            self.tabs = QTabWidget()
            for idx, item in enumerate(items):
                title = str(item['props'].get('title', '')).strip('\'"') or f"Item {idx+1}"
                editor = ImportEditorDialog(item, self, embed_mode=True)
                editor.mf.setStyleSheet(embed_style)
                
                # Render exact icon thumbnail using editor's preview label
                tab_icon = None
                if hasattr(editor, 'ic_prev_lbl'):
                    pix = editor.ic_prev_lbl.grab()
                    if not pix.isNull():
                        tab_icon = QIcon(pix)
                
                if tab_icon and not tab_icon.isNull():
                    self.tabs.addTab(editor, tab_icon, title)
                else:
                    self.tabs.addTab(editor, title)
                self.editors.append((item, editor))
            layout.addWidget(self.tabs)

        # Global Save / Cancel action bar
        action_bar = QHBoxLayout()
        action_bar.addStretch()
        
        cancel_b = QPushButton("Cancel")
        cancel_b.setCursor(Qt.PointingHandCursor)
        cancel_b.setStyleSheet("QPushButton { background-color: #2a2a30; color: #ffffff; border-radius: 10px; padding: 8px 18px; font-weight: bold; } QPushButton:hover { background-color: #45475a; }")
        cancel_b.clicked.connect(self.reject)
        action_bar.addWidget(cancel_b)
        
        save_b = QPushButton("Save Changes")
        save_b.setCursor(Qt.PointingHandCursor)
        save_b.setStyleSheet("QPushButton { background-color: #dc143c; color: #ffffff; border-radius: 10px; padding: 8px 18px; font-weight: bold; } QPushButton:hover { background-color: #ff2a55; }")
        save_b.clicked.connect(self.on_save_all)
        action_bar.addWidget(save_b)
        
        layout.addLayout(action_bar)

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

    def get_changes(self):
        all_changes = []
        for item, editor in self.editors:
            c = editor.get_changes()
            item_title = str(item['props'].get('title', '')).strip('\'"') or 'Untitled'
            for line in c:
                all_changes.append(f"[{item_title}] {line}")
        return all_changes

    def is_dirty(self):
        return len(self.get_changes()) > 0

    def reject(self):
        if self.is_dirty():
            from utils import UnsavedChangesDialog
            changes = self.get_changes()
            dialog = UnsavedChangesDialog(None, text="You have unsaved changes in these items. Do you want to save them?", changes=changes)
            res = dialog.exec_()
            if res == 1:
                self.on_save_all(); return
            elif res == 2:
                return
        super().reject()
            
    def on_save_all(self):
        self.save_all()
        self.accept()

    def save_all(self):
        for item, editor in self.editors:
            save_imported_item(item, editor.get_props())


class ImportsWidget(QWidget):
    reload_requested = pyqtSignal()
    def __init__(self, project_root, shell_nss_path=None, parent=None):
        super().__init__(parent); self.root = project_root; self.shell_nss_path = shell_nss_path; self.curr_filter = None; self.main_layout = QHBoxLayout(self); self.main_layout.setContentsMargins(0, 10, 0, 0); self.setup_ui()
    def setup_ui(self):
        self.side = QFrame(); self.side.setFixedWidth(210); self.side.setStyleSheet("background: rgba(0,0,0,0.2); border-radius: 15px;")
        self.sl = QVBoxLayout(self.side); self.sl.setAlignment(Qt.AlignTop); self.sl.setContentsMargins(5, 15, 5, 15); self.sl.setSpacing(8)
        lbl = QLabel("FILES"); lbl.setStyleSheet("color: #333333; font-size: 10px; font-weight: bold; margin: 10px 0 5px 10px; background: transparent;")
        self.sl.addWidget(lbl)
        self.all_btn = QPushButton("All Files"); self.all_btn.setFixedHeight(36); self.all_btn.clicked.connect(lambda: self.set_file_filter(None))
        self.all_btn.setStyleSheet("QPushButton { background: rgba(49, 50, 68, 0.6); color: #dc143c; border-radius: 10px; text-align: left; padding-left: 12px; font-weight: bold; margin: 0 5px; border: 1px solid rgba(220, 20, 60, 0.1); } QPushButton:hover { background: #2a2a30; }")
        self.sl.addWidget(self.all_btn)
        self.f_scroll = QScrollArea(); self.f_scroll.setWidgetResizable(True); self.f_scroll.setStyleSheet("background: transparent; border: none;")
        self.file_cont = QWidget(); self.file_cont.setStyleSheet("background: transparent;")
        self.file_l = QVBoxLayout(self.file_cont); self.file_l.setContentsMargins(5,0,5,0); self.file_l.setSpacing(5); self.file_l.setAlignment(Qt.AlignTop)
        self.f_scroll.setWidget(self.file_cont); self.sl.addWidget(self.f_scroll)
        self.main_layout.addWidget(self.side)
        
        cr = QWidget(); crl = QVBoxLayout(cr); crl.setContentsMargins(0, 0, 0, 0); self.main_layout.addWidget(cr)
        head = QHBoxLayout(); self.search = QLineEdit(); self.search.setPlaceholderText("Search items/menus..."); self.search.textChanged.connect(self.filter_items)
        self.search.setStyleSheet("QLineEdit { background: rgba(255,255,255,0.05); border: 1px solid #2a2a30; border-radius: 15px; padding: 10px 15px; color: white; }")
        head.addWidget(self.search); crl.addLayout(head)
        
        self.type_tags = FilterBar([("All", "#45475a"), ("Item", "#45475a"), ("Menu", "#45475a")])
        self.type_tags.filter_changed.connect(lambda _: self.filter_items())
        crl.addWidget(self.type_tags)

        self.action_tags = FilterBar([
            ("All", "#2a2a30"), ("Renamed", "#808080"), ("Icons", "#4A90E2"), 
            ("Hidden", "#dc143c"), ("Part Hidden", "#9B59B6"), ("Moved", "#E29E4A"), 
            ("Position", "#4AE290"), ("Separator", "#F1C40F")
        ])
        self.action_tags.filter_changed.connect(lambda _: self.filter_items())
        crl.addWidget(self.action_tags)
        
        self.view = QListView(); self.view.setStyleSheet("background: transparent; border: none;")
        self.view.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.view.setSpacing(0); self.view.setMouseTracking(True)
        self.model = NSSItemModel(); self.view.setModel(self.model)
        self.delegate = NSSItemDelegate(self.view); self.view.setItemDelegate(self.delegate)
        crl.addWidget(self.view)
        
        QTimer.singleShot(200, self.refresh)

    def refresh(self):
        all_items = scan_nss_items(self.root, self.shell_nss_path)
        # ONLY show item and menu definitions in the Imports tab
        # Skip menus that have no title, no icon, and no nested items (logic-only menus)
        items = []
        for i in all_items:
            if i['type'] == 'item':
                items.append(i)
            elif i['type'] == 'menu':
                p = i.get('props', {})
                # Hide grouped items pattern (no title + expanded=true)
                if not p.get('title') and str(p.get('expanded', '')).lower() == 'true':
                    continue
                
                has_visual = p.get('title') or p.get('icon') or p.get('image')
                if has_visual or i.get('has_children'):
                    items.append(i)
        
        items.sort(key=lambda x: (x['type'] != 'menu', x['props'].get('title', '').lower()))
        self.model.set_items(items); self.update_file_filters(items)
        self.filter_items()

    def filter_items(self):
        type_tag = self.type_tags.group.checkedButton().text()
        action_tag = self.action_tags.group.checkedButton().text()
        self.model.filter(self.search.text(), self.curr_filter, type_tag=type_tag, action_tag=action_tag)

    def set_file_filter(self, fp):
        self.curr_filter = fp; self.filter_items(); self.refresh_sidebar_highlights()

    def update_file_filters(self, items):
        for i in reversed(range(self.file_l.count())): (w.setParent(None) if (w := self.file_l.itemAt(i).widget()) else None)
        files = sorted(list(set(i['file'] for i in items)))
        for fp in files:
            name = os.path.basename(fp).replace('.nss', '')
            display_name = name
            if self.shell_nss_path and os.path.abspath(fp) == os.path.abspath(self.shell_nss_path):
                display_name = "shell.nss"
            
            fw = QWidget(); fl = QHBoxLayout(fw); fl.setContentsMargins(5, 0, 5, 0); fl.setSpacing(5)
            
            # Edit button
            eb = QPushButton("\uE104"); eb.setFixedSize(28, 28); eb.setFont(QFont('Segoe MDL2 Assets', 10))
            eb.setToolTip("Open in Editor"); eb.setCursor(Qt.PointingHandCursor)
            eb.setStyleSheet("QPushButton { background: rgba(255,255,255,0.05); border: none; border-radius: 14px; color: #dc143c; } QPushButton:hover { background: rgba(255,255,255,0.1); }")
            eb.clicked.connect(lambda _, x=fp: os.startfile(x))
            fl.addWidget(eb)

            # Main button
            btn = QPushButton(display_name); btn.setFixedHeight(34); btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda _, f=fp: self.set_file_filter(f))
            
            is_active = (self.curr_filter == fp)
            bg = "rgba(220, 20, 60, 0.15)" if is_active else "transparent"
            fg = "#dc143c" if is_active else "#b0b0b0"
            border = "1px solid rgba(220, 20, 60, 0.3)" if is_active else "none"
            btn.setStyleSheet(f"QPushButton {{ background: {bg}; color: {fg}; border-radius: 10px; text-align: left; padding-left: 10px; border: {border}; font-weight: {'bold' if is_active else 'normal'}; }} QPushButton:hover {{ background: rgba(255,255,255,0.05); }}")
            fl.addWidget(btn, 1)

            self.file_l.addWidget(fw)

    def refresh_sidebar_highlights(self):
        self.all_btn.setStyleSheet(f"QPushButton {{ background: {'rgba(220, 20, 60, 0.1)' if not self.curr_filter else 'rgba(49, 50, 68, 0.6)'}; color: {'#dc143c' if not self.curr_filter else '#b0b0b0'}; border-radius: 10px; text-align: left; padding-left: 12px; font-weight: bold; margin: 0 5px; border: 1px solid {'rgba(220, 20, 60, 0.4)' if not self.curr_filter else 'rgba(220, 20, 60, 0.1)'}; }}")
        self.update_file_filters(self.model._items)

    def edit_item(self, data):
        d = ImportEditorDialog(data, self)
        d.reload_requested.connect(self.reload_requested.emit)
        if d.exec_(): save_imported_item(data, d.get_props()); self.refresh(); self.reload_requested.emit()
    def pick_item_color(self, data, idx):
        from theme_editor_widget import MinimalColorPickerDialog
        p = data['props']; val = (p.get('image') or p.get('icon') or '').strip('\'" ')
        codes = _extract_glyph_codes(val)
        is_icon_kw = val.startswith('icon.')
        
        # Get current color
        colors = _extract_all_colors(val)
        while len(colors) < 2: colors.append(None)
        if not codes:
            _, c = _extract_img_path_and_color(val)
            if c: colors[0] = c
        if not colors[idx]: colors[idx] = _get_theme_glyph_colors()[idx]
        
        dlg = MinimalColorPickerDialog(colors[idx], f"pick_{idx}", self); dlg.default_checkbox.hide()
        def on_color(key, color):
            hex_c = color.name(); np = p.copy()
            if codes:
                colors[idx] = hex_c; g_val = _build_glyph_val(codes, colors)
                (np.__setitem__('image', g_val) if 'image' in np or 'icon' not in np else np.__setitem__('icon', g_val))
            else:
                # Image or icon.xxx
                path = _resolve_app_dir_path(val)
                if path and os.path.exists(path):
                    nv, _ = save_local_icon(path, hex_c, True)
                    (np.__setitem__('image', nv) if 'image' in np or 'icon' not in np else np.__setitem__('icon', nv))
                elif is_icon_kw:
                    nv = f"[{val}, {hex_c}]"
                    (np.__setitem__('image', nv) if 'image' in np or 'icon' not in np else np.__setitem__('icon', nv))
            save_imported_item(data, np); self.refresh(); self.reload_requested.emit()
        dlg.colorSelected.connect(on_color); dlg.exec_()


def scan_nss_items(root, shell_nss_path=None):
    items = []
    if shell_nss_path and os.path.exists(shell_nss_path):
        try:
            content = read_file(shell_nss_path)
            if content:
                find_items_and_menus.current_file = shell_nss_path
                for m in find_items_and_menus(content):
                    m['file'] = shell_nss_path
                    items.append(m)
        except: pass

    paths = [os.path.join(root, 'imports'), os.path.join(root, 'plugins')]
    for p in paths:
        if not os.path.exists(p): continue
        for r, _, files in os.walk(p):
            for f in files:
                if f.endswith('.nss') and f not in ('theme.nss', 'modify.nss'):
                    fp = os.path.join(r, f)
                    try:
                        find_items_and_menus.current_file = fp
                        content = read_file(fp)
                        matches = find_items_and_menus(content)
                        for m in matches: m['file'] = fp; items.append(m)
                    except: pass
    return items



class NSSLexer:
    def __init__(self, text):
        self.text = text; self.pos = 0
    def tokenize(self):
        tokens = []
        while self.pos < len(self.text):
            ch = self.text[self.pos]
            if ch.isspace(): self.pos += 1; continue
            if ch == '/' and self.pos + 1 < len(self.text):
                if self.text[self.pos+1] == '/':
                    start = self.pos
                    while self.pos < len(self.text) and self.text[self.pos] != '\n': self.pos += 1
                    tokens.append(('COMMENT', self.text[start:self.pos], start)); continue
                if self.text[self.pos+1] == '*':
                    start = self.pos; self.pos += 2
                    while self.pos + 1 < len(self.text) and self.text[self.pos:self.pos+2] != '*/': self.pos += 1
                    self.pos += 2; tokens.append(('COMMENT', self.text[start:self.pos], start)); continue
            if ch in ("'", '"'):
                start = self.pos
                if ch == "'" and self.text[self.pos:self.pos+3] == "'''":
                    self.pos += 3
                    while self.pos < len(self.text):
                        if self.text[self.pos:self.pos+3] == "'''":
                            self.pos += 3
                            break
                        self.pos += 1
                    tokens.append(('STRING', self.text[start:self.pos], start)); continue
                elif ch == '"' and self.text[self.pos:self.pos+3] == '"""':
                    self.pos += 3
                    while self.pos < len(self.text):
                        if self.text[self.pos:self.pos+3] == '"""':
                            self.pos += 3
                            break
                        self.pos += 1
                    tokens.append(('STRING', self.text[start:self.pos], start)); continue
                else:
                    qc = ch; self.pos += 1
                    while self.pos < len(self.text):
                        if self.text[self.pos] == qc and self.text[self.pos-1] != '\\': self.pos += 1; break
                        self.pos += 1
                    tokens.append(('STRING', self.text[start:self.pos], start)); continue
            if ch.isalpha() or ch in ('@', '_', '$', '#', '\\'):
                start = self.pos; self.pos += 1
                while self.pos < len(self.text) and (self.text[self.pos].isalnum() or self.text[self.pos] in ('.', '_', '\\', '#', '-')): self.pos += 1
                tokens.append(('IDENTIFIER', self.text[start:self.pos], start)); continue
            if ch.isdigit():
                start = self.pos
                while self.pos < len(self.text) and (self.text[self.pos].isdigit() or self.text[self.pos] == '.'): self.pos += 1
                tokens.append(('NUMBER', self.text[start:self.pos], start)); continue
            tokens.append((ch, ch, self.pos)); self.pos += 1
        return tokens

def parse_nss_args(text, tokens):
    props = {}; order = []; i = 0
    while i < len(tokens):
        t_type, t_val, t_pos = tokens[i]
        if t_type == 'COMMENT' or t_val == ',': i += 1; continue
        if i + 1 < len(tokens) and tokens[i+1][1] == '=':
            key = t_val; i += 2; v_start_pos = tokens[i][2] if i < len(tokens) else t_pos
            pc, bc, last_pos = 0, 0, v_start_pos
            while i < len(tokens):
                vt_type, vt_val, vt_pos = tokens[i]
                if pc == 0 and bc == 0:
                    if vt_val in (',', ')'): break
                    if i + 1 < len(tokens) and tokens[i+1][1] == '=': break
                if vt_val == '(':
                    pc += 1
                elif vt_val == ')':
                    if pc > 0:
                        pc -= 1
                    else:
                        break
                elif vt_val == '[': bc += 1
                elif vt_val == ']': bc -= 1
                last_pos = vt_pos + len(vt_val); i += 1
            val = text[v_start_pos:last_pos].strip()
            # If the extracted value is wrapped in single quotes, keep it clean
            props[key] = val; order.append(key)
        else:
            if t_type == 'IDENTIFIER': props[t_val] = True; order.append(t_val)
            i += 1
    props['_order'] = order; return props

def find_items_and_menus(content, types=('modify', 'item', 'menu')):
    lexer = NSSLexer(content)
    tokens = lexer.tokenize()
    results = []
    i = 0
    while i < len(tokens):
        t_type, t_val, t_pos = tokens[i]
        if t_type == 'IDENTIFIER' and t_val.lower() in [t.lower() for t in types]:
            start_pos = t_pos
            header_end = start_pos + len(t_val)
            
            # Find command header boundary (...)
            has_paren = False
            if i + 1 < len(tokens) and tokens[i+1][1] == '(':
                has_paren = True; i += 2
                arg_tokens = []; pc, bc = 1, 0
                while i < len(tokens) and pc > 0:
                    vt_val = tokens[i][1]
                    if vt_val == '(': pc += 1
                    elif vt_val == ')': pc -= 1
                    elif vt_val == '[': bc += 1
                    elif vt_val == ']': bc -= 1
                    if pc > 0: arg_tokens.append(tokens[i])
                    i += 1
                header_end = tokens[i-1][2] + len(tokens[i-1][1])
                props = parse_nss_args(content, arg_tokens)
            else:
                # No parentheses, scan until newline or block
                props = {}; i += 1
                while i < len(tokens):
                    if tokens[i][1] in ('\n', '{'): break
                    header_end = tokens[i][2] + len(tokens[i][1])
                    i += 1
            
            # Peek for optional body { ... }
            block_end = header_end
            has_children = False
            raw_inner = ""
            temp_i = i
            while temp_i < len(tokens) and tokens[temp_i][0] == 'COMMENT': temp_i += 1
            if temp_i < len(tokens) and tokens[temp_i][1] == '{':
                body_start_idx = temp_i
                bc_body = 1; temp_i += 1
                while temp_i < len(tokens) and bc_body > 0:
                    vt_type, vt_val, vt_pos = tokens[temp_i]
                    if vt_val == '{': bc_body += 1
                    elif vt_val == '}': bc_body -= 1
                    elif vt_type == 'IDENTIFIER' and vt_val.lower() in ('item', 'menu', 'modify'):
                        has_children = True
                    temp_i += 1
                block_end = tokens[temp_i-1][2] + 1
                raw_inner = content[tokens[body_start_idx][2]:block_end]
            
            results.append({
                'type': t_val, 
                'start': start_pos, 
                'end': block_end, 
                'cmd_end': header_end, 
                'props': props,
                'has_children': has_children,
                'raw_inner': raw_inner,
                'file': getattr(find_items_and_menus, 'current_file', ''),
                'indent': content[:start_pos].split('\n')[-1] if '\n' in content[:start_pos] else ''
            })
        else:
            i += 1
    return results

def format_nss_value(k, v):
    if not isinstance(v, str): v = str(v)
    if v.lower() in ('true', 'false', 'none'): v = v.lower()
    if v == '': return f"{k}=''"
    v = v.strip()
    
    # Strip unnecessary enclosing parentheses if it's wrapping a single path/string (e.g. ('C:/...'))
    while v.startswith('(') and v.endswith(')'):
        inner = v[1:-1].strip()
        # Only strip if it's not a multi-term expression or Nilesoft function call
        if inner.startswith("'") or inner.startswith('"') or ('\\' in inner or '/' in inner):
            v = inner
        else:
            break

    # Normalize: strip existing quotes to prevent nesting
    while (v.startswith("'") and v.endswith("'")) or (v.startswith('"') and v.endswith('"')):
        # Only strip if it's a simple wrap, don't strip if quotes are part of an expression (e.g. ['A', 'B'])
        if v.startswith('[') or (v.count("'") + v.count('"')) > 2:
            if v.startswith("''") and v.endswith("''"):
                v = v[2:-2]
                continue
            break
        v = v[1:-1]
    
    v = v.strip()
    
    # Check if ALREADY quoted
    is_quoted = (v.startswith("'") and v.endswith("'")) or (v.startswith('"') and v.endswith('"'))
    if is_quoted:
        return f"{k}={v}"

    is_wrapped = v.startswith('[') and v.endswith(']')
    is_image_res = v.lower().startswith('image.res(') and v.endswith(')')
    is_image_svg = v.lower().startswith('image.svg(') and v.endswith(')')
    is_path = ('\\' in v or '/' in v or ':' in v) and not (is_image_res or is_image_svg)
    is_expression = '(' in v and ')' in v and not (is_image_res or is_image_svg or is_path)
    is_complex = ('@if' in v or '@sel' in v or 'key.' in v or is_expression) and not is_path
    
    nilesoft_prefixes = (
        'vis.', 'key.', 'clr.', 'sys.', 'app.', 'this.', 'id.', 'menu.', 'tip.', 'sel.', 'title.',
        'command.', 'io.', 'str.', 'reg.', 'path.', 'theme.', 'icon.', 'image.', 'window.', 
        'cursor.', 'process.', 'user.', 'computer.', 'dt.', 'color.', 'file.', 'dir.',
        '@app.', '@sel.', '@clipboard.', '@sys.', '@path.', '@user.', '@dt.', 'item.', 'menu.'
    )
    is_nilesoft_obj = any(v.lower().startswith(p) for p in nilesoft_prefixes)
    is_glyph = v.startswith('\\u') or v.startswith('0x') or (len(v) == 1 and ord(v) > 0xE000)
    
    keywords = (
        'true', 'false', 'none', 'inherit', 'parent', 'all', 'auto', 'before', 'after', 
        'both', 'top', 'bottom', 'middle', 'left', 'right', 'contains', 'starts', 'ends', 
        'exact', 'single', 'multiple', 'if', 'else', 'any', 'not', 'and', 'or', 'normal', 'hidden', 'remove'
    )
    has_space = ' ' in v
    has_dot = '.' in v
    
    # Force quotes for find, title, menu, in, cmd, and path strings
    if k in ('find', 'title', 'menu', 'in', 'cmd', 'path') and not (is_wrapped or is_complex or is_nilesoft_obj or is_glyph or is_image_res or is_image_svg):
        return f"{k}='{v}'"

    if is_path:
        return f"{k}='{v}'"

    has_pipe = '|' in v
    
    should_not_quote = is_wrapped or is_complex or is_nilesoft_obj or is_glyph or is_image_res or is_image_svg or \
                       (v.isdigit() and not has_dot) or v.lower() in keywords
    
    if has_pipe and not (is_expression or is_complex):
        should_not_quote = False

    if should_not_quote:
        if has_space and not (is_wrapped or is_expression or is_complex or is_image_res or is_image_svg):
            return f"{k}='{v}'"
        return f"{k}={v}"
    
    return f"{k}='{v}'"

def save_imported_item(data, new_props):
    fp = data['file']; content = read_file(fp)
    if not content: return
    find_items_and_menus.current_file = fp
    items = find_items_and_menus(content)
    target = None
    for it in items:
        dist = abs(it['start'] - data['start'])
        if dist < 500 and it['type'] == data['type']:
            t1 = str(it['props'].get('title', '')).strip().strip("'\"").lower()
            t2 = str(data['props'].get('title', '')).strip().strip("'\"").lower()
            w1 = str(it['props'].get('where', '')).strip().strip("'\"").lower()
            w2 = str(data['props'].get('where', '')).strip().strip("'\"").lower()
            if (t1 and t1 == t2) or (w1 and w1 == w2):
                target = it; break
    
    if not target:
        for it in items:
            if abs(it['start'] - data['start']) < 300 and it['type'] == data['type']:
                target = it; break
    
    if not target: target = data
    
    # Merge props: keep everything from target['props'], update with new_props
    merged = target['props'].copy()
    for k in list(merged.keys()):
        if k not in new_props and k not in ('_order', 'file', 'start', 'end', 'cmd', 'arg', 'args', 'where', 'mode', 'window', 'admin', 'type'):
            del merged[k]
    for k, v in new_props.items():
        if v is None or v == 'None' or (k in ('vis', 'pos', 'type') and not str(v).strip()):
            if k in merged: del merged[k]
        else: merged[k] = v
            
    pts = []; handled = set()
    orig_order = target['props'].get('_order', [])
    for k in orig_order:
        if k in merged:
            v = str(merged[k]).strip()
            pts.append(format_nss_value(k, v)); handled.add(k)
        elif k == 'sep' and 'sep' in merged:
            v = merged['sep']
            pts.append(format_nss_value('sep', v)); handled.add('sep')

    for k, v in merged.items():
        if k and k not in handled and k not in ('_order', 'file', 'start', 'end', 'cmd_end', 'raw_inner', 'has_children', 'indent') and re.match(r'^\w+$', k):
            pts.append(format_nss_value(k, str(v).strip()))
            
    header = f"{target['type']}({ ' '.join(pts) })"
    cmd_end = target.get('cmd_end', target['end'])
    try:
        new_content = content[:target['start']] + header + content[cmd_end:]
        safe_file_write(fp, new_content)
        if hasattr(NSSCacheManager, 'cache') and fp in NSSCacheManager.cache:
            del NSSCacheManager.cache[fp]
    except Exception as e:
        from PyQt5.QtWidgets import QMessageBox
        QMessageBox.critical(None, "Save Error", f"Failed to save changes to {fp}:\n{str(e)}")

def mass_save_op(item_data, new_props):
    pts = []; handled = set(); orig_order = item_data['props'].get('_order', [])
    for k in orig_order:
        if k == 'sep':
            v = new_props.get('sep')
            if v: pts.append(format_nss_value('sep', v)); handled.add('sep')
        elif k in new_props:
            v = new_props[k]
            if isinstance(v, str): v = v.strip()
            else: v = str(v)
            if k in ('pos', 'vis', 'remove', 'hidden') and not v: handled.add(k); continue
            if k == 'menu' and v is None: handled.add(k); continue
            pts.append(format_nss_value(k, v)); handled.add(k)
    for k, v in new_props.items():
        if k and k not in handled and k not in ('_order', 'file', 'start', 'end', 'raw_inner', 'indent', 'cmd_end', 'has_children') and re.match(r'^\w+$', k):
            v_s = str(v).strip()
            if k in ('pos', 'vis', 'remove', 'hidden', 'type') and not v_s: continue
            if k == 'menu' and v_s is None: continue
            pts.append(format_nss_value(k, v_s))
    
    header = f"{item_data['type']}({ ' '.join(pts) })"
    return header

def _get_custom_menus_from_nss():
    root = PROJECT_ROOT or (os.path.dirname(os.path.dirname(sys.executable)) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    titles = []
    paths = [os.path.join(root, 'imports'), os.path.join(root, 'plugins')]
    for p in paths:
        if not os.path.exists(p): continue
        for r, _, files in os.walk(p):
            for f in files:
                if f.endswith('.nss') and f not in ('theme.nss', 'modify.nss'):
                    fp = os.path.join(r, f)
                    try:
                        content = read_file(fp)
                        for item in find_items_and_menus(content, types=('menu',)):
                            title = item['props'].get('title', '').strip().strip("'\"")
                            if title and title.lower() not in ('main', 'options', 'menu.main', 'title.options', ''):
                                if title not in titles:
                                    titles.append(title)
                    except: pass
    return titles


def _get_vis_options():
    return {
        "Always Visible": "", 
        "Hidden": "vis.remove", 
        "Visible In...": "CONDITIONAL",
        "Shift Key Only": "key.shift()", 
        "Control Key Only": "key.control()", 
        "Caps Lock Only": "key.capslock()", 
        "Left Mouse Only": "key.lbutton()"
    }

def _build_vis_expression(selection_dict):
    # selection_dict maps 'shift', 'ctrl', 'caps', 'lmb' to boolean (True = show)
    # If all are True, it's always visible
    if all(selection_dict.values()): return ""
    hide_conds = []
    if not selection_dict.get('shift'): hide_conds.append("key.shift()")
    if not selection_dict.get('ctrl'): hide_conds.append("key.control()")
    if not selection_dict.get('caps'): hide_conds.append("key.capslock()")
    if not selection_dict.get('lmb'): hide_conds.append("key.lbutton()")
    if not hide_conds: return "" # Should not happen if not all are true
    return f"@if({' || '.join(hide_conds)}, 'hidden', 'normal')"

def _parse_vis_expression(expr):
    expr = expr.lower()
    res = {'shift': True, 'ctrl': True, 'caps': True, 'lmb': True}
    if '@if' in expr and 'hidden' in expr:
        res['shift'] = 'key.shift()' not in expr
        res['ctrl'] = 'key.control()' not in expr
        res['caps'] = 'key.capslock()' not in expr
        res['lmb'] = 'key.lbutton()' not in expr
    return res

class ModifyRuleEditorDialog(QDialog):
    POS_OPTIONS = ["", "top", "bottom", "1", "2", "3", "4", "5", "middle"]
    live_update = pyqtSignal(dict)
    def __init__(self, data=None, parent=None):
        super().__init__(parent); self.data = data or {}; self.setMinimumWidth(500); self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint); self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet("QToolTip { background-color: #1e1e24; color: #ffffff; border: 1px solid rgba(220, 20, 60, 0.6); border-radius: 8px; padding: 6px 12px; font-family: 'Segoe UI Variable Display'; font-size: 12px; font-weight: bold; }")
        self.created_temp_icons = []
        self._custom_menus = _get_custom_menus_from_nss()
        self._drag_pos = None
        self.setup_ui(); self.load_data(data) if data else None

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

    def setup_ui(self):
        self.mf = QFrame(self); self.mf.setObjectName("mainFrame")
        self.mf.setStyleSheet("""
            #mainFrame { background-color: #121212; border: 1px solid #2a2a30; border-radius: 20px; } 
            QLabel { color: #ffffff; font-size: 13px; } 
            QLineEdit, QComboBox { background-color: #2a2a30; border: 1px solid #45475a; border-radius: 10px; padding: 7px 10px; color: #ffffff; } 
            QLineEdit:focus { border: 1px solid #dc143c; }
            QComboBox:hover, QComboBox:focus { border: 1px solid #dc143c; }
            QComboBox QAbstractItemView { background-color: #121212; border: 1px solid #2a2a30; selection-background-color: #2a2a30; selection-color: #dc143c; color: #ffffff; outline: none; border-radius: 8px; padding: 4px; }
            QPushButton#saveBtn { background-color: #dc143c; color: #ffffff; border-radius: 10px; padding: 8px 18px; font-weight: bold; } 
            QPushButton#saveBtn:hover { background-color: #ff2a55; }
            QPushButton#cancelBtn { background-color: #2a2a30; color: #ffffff; border-radius: 10px; padding: 8px 18px; }
            QPushButton#cancelBtn:hover { background-color: #45475a; }
        """)
        layout = QVBoxLayout(self); layout.setContentsMargins(0, 0, 0, 0); layout.addWidget(self.mf)
        cl = QVBoxLayout(self.mf); cl.setContentsMargins(20, 18, 20, 18); cl.setSpacing(12)
        h = QLabel("Modify Rule Configuration"); h.setStyleSheet("font-size: 17px; font-weight: bold; color: white;"); cl.addWidget(h)
        
        tg = QFrame(); tg.setStyleSheet("background: rgba(255,255,255,0.03); border-radius: 12px; padding: 10px;"); tl = QGridLayout(tg); tl.setVerticalSpacing(8); tl.setHorizontalSpacing(10); cl.addWidget(QLabel("Target Criteria")); cl.addWidget(tg)
        
        find_row = QHBoxLayout()
        find_row.setSpacing(8)
        self.f_inp = QLineEdit(); self.f_inp.setPlaceholderText("e.g. Refresh")
        find_row.addWidget(self.f_inp, 1)
        
        self.find_mode_group = QButtonGroup(self)
        sw_row = QHBoxLayout(); sw_row.setContentsMargins(0, 0, 0, 0); sw_row.setSpacing(10)
        for i, (text, mode) in enumerate([("Contains", "contains"), ("Starts", "starts"), ("Ends", "ends"), ("Exact", "exact")]):
            h_sub = QHBoxLayout(); h_sub.setSpacing(3); h_sub.setAlignment(Qt.AlignVCenter)
            rb = RadioDot(); rb.setProperty("mode", mode)
            rb.setCursor(Qt.PointingHandCursor)
            rl = QLabel(text); rl.setStyleSheet("font-size: 11px; color: #b0b0b0; background: transparent; border: none;"); rl.setAlignment(Qt.AlignVCenter)
            h_sub.addWidget(rb); h_sub.addWidget(rl)
            sw_row.addLayout(h_sub)
            self.find_mode_group.addButton(rb, i)
            if i == 0: rb.setChecked(True)
        find_row.addLayout(sw_row)
        
        tl.addWidget(QLabel("Find Title:"), 0, 0); tl.addLayout(find_row, 0, 1)
        self.i_inp = QLineEdit(); self.i_inp.setPlaceholderText("e.g. open with"); tl.addWidget(QLabel("In Menu:"), 1, 0); tl.addWidget(self.i_inp, 1, 1)
        
        ag = QFrame(); ag.setStyleSheet("background: rgba(255,255,255,0.03); border-radius: 12px; padding: 10px;"); al = QGridLayout(ag); al.setVerticalSpacing(8); al.setHorizontalSpacing(10); cl.addWidget(QLabel("Actions to Perform")); cl.addWidget(ag)
        self.ti_inp = QLineEdit(); al.addWidget(QLabel("New Title:"), 0, 0); al.addWidget(self.ti_inp, 0, 1)
        
        self.m_inp = NonScrollComboBox(); self.m_inp.setEditable(False)
        self.m_inp.addItems(["None", "Main", "Options"])
        self.m_inp.setFixedWidth(130)
        
        ic_row = QHBoxLayout()
        ic_row.setSpacing(6)
        
        self.c_container = QWidget()
        self.c_lay = QHBoxLayout(self.c_container)
        self.c_lay.setContentsMargins(0, 0, 0, 0)
        self.c_lay.setSpacing(4)
        self.c_lay.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        
        self.ic_inp = QLineEdit(); self.ic_inp.setPlaceholderText("e.g. \\uE102, image path, or image.res(...)"); self.ic_inp.textChanged.connect(self._update_colors_ui)
        self.ic_prev_lbl = ClickablePreviewLabel()
        self.ic_prev_lbl.setFixedSize(46, 46)
        self.ic_prev_lbl.setAlignment(Qt.AlignCenter)
        self.ic_prev_lbl.setToolTip("Click to Browse Glyphs / Upload Icon")
        self.ic_prev_lbl.setStyleSheet("""
            ClickablePreviewLabel {
                background: rgba(255,255,255,0.05); 
                border-radius: 12px; 
                border: 1px solid rgba(255,255,255,0.12);
            }
            ClickablePreviewLabel:hover {
                border: 1px solid #dc143c;
                background: rgba(220, 20, 60, 0.12);
            }
        """)
        self.ic_prev_lbl.clicked.connect(self._open_glyph_browser)
        
        btn_action_style = """
            QPushButton {
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 10px;
                color: #e0e0e0;
                padding: 0;
            }
            QPushButton:hover {
                background: rgba(220, 20, 60, 0.2);
                border: 1px solid #dc143c;
                color: #ffffff;
            }
        """
        
        self.ic_inherit = QPushButton("\uE777")
        self.ic_inherit.setFont(QFont('Segoe MDL2 Assets', 13)); self.ic_inherit.setFixedSize(34, 34)
        self.ic_inherit.setToolTip("Inherit Icon from Target Command/File"); self.ic_inherit.clicked.connect(self._inherit_icon); self.ic_inherit.setStyleSheet(btn_action_style); self.ic_inherit.setCursor(Qt.PointingHandCursor)

        self.ic_remove = QPushButton("\uE74D")
        self.ic_remove.setFont(QFont('Segoe MDL2 Assets', 13)); self.ic_remove.setFixedSize(34, 34)
        self.ic_remove.setToolTip("Remove Icon"); self.ic_remove.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.03);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 10px;
                color: #888888;
                padding: 0;
            }
            QPushButton:hover {
                background: rgba(255, 50, 50, 0.25);
                border: 1px solid #ff4444;
                color: #ffffff;
            }
        """)
        self.ic_remove.setCursor(Qt.PointingHandCursor)
        self.ic_remove.clicked.connect(lambda: self.ic_inp.setText(""))

        self.sep_box = NonScrollComboBox(); self.sep_box.addItems(["None", "Before", "After", "Both"])
        self.sep_box.setFixedWidth(130)
        
        ic_row.addWidget(self.c_container)
        ic_row.addWidget(self.ic_prev_lbl)
        ic_row.addWidget(self.ic_inp, 1)
        ic_row.addWidget(self.ic_inherit)
        ic_row.addWidget(self.ic_remove)
        al.addWidget(QLabel("Icon/Image:"), 1, 0); al.addLayout(ic_row, 1, 1)
        self.ic_inp.textChanged.connect(self._update_icon_preview)
        self.p_inp = NonScrollComboBox(); self.p_inp.addItems(self.POS_OPTIONS)
        self.p_inp.setFixedWidth(110)
        
        v_val = str(self.data.get('vis', ''))
        self.vis_widget = VisibilityWidget()
        self.vis_widget.set_value(v_val)
        self.vis_widget.valueChanged.connect(lambda _: self.live_update.emit(self.get_data()))
        al.addWidget(QLabel("Visibility:"), 2, 0); al.addWidget(self.vis_widget, 2, 1)

        self.type_widget = TypeWidget()
        self.type_widget.valueChanged.connect(lambda _: self.live_update.emit(self.get_data()))
        al.addWidget(QLabel("Show in:"), 3, 0); al.addWidget(self.type_widget, 3, 1)

        m_row = QHBoxLayout()
        m_row.addWidget(self.m_inp)
        m_row.addStretch()
        al.addWidget(QLabel("Move to:"), 4, 0)
        al.addLayout(m_row, 4, 1)

        p_row = QHBoxLayout()
        p_row.addWidget(self.p_inp)
        p_row.addStretch()
        al.addWidget(QLabel("Position:"), 5, 0)
        al.addLayout(p_row, 5, 1)

        sep_row = QHBoxLayout()
        sep_row.addWidget(self.sep_box)
        sep_row.addStretch()
        al.addWidget(QLabel("Separator:"), 6, 0)
        al.addLayout(sep_row, 6, 1)

        self.i_inp.textChanged.connect(self._update_move_to_options)
        self._update_move_to_options(self.i_inp.text())

        for w in [self.f_inp, self.i_inp, self.ti_inp, self.ic_inp]: w.textChanged.connect(lambda: self.live_update.emit(self.get_data()))
        for w in [self.m_inp, self.p_inp, self.sep_box]: (w.currentTextChanged.connect(lambda: self.live_update.emit(self.get_data())) if hasattr(w, 'currentTextChanged') else w.currentIndexChanged.connect(lambda: self.live_update.emit(self.get_data())))
        btns = QHBoxLayout(); c = QPushButton("Cancel"); c.setObjectName("cancelBtn"); c.clicked.connect(self.reject); c.setCursor(Qt.PointingHandCursor); s = QPushButton("Save Rule"); s.setObjectName("saveBtn"); s.clicked.connect(self.accept); s.setCursor(Qt.PointingHandCursor); btns.addStretch(); btns.addWidget(c); btns.addWidget(s); cl.addLayout(btns)
    def _update_move_to_options(self, text=None):
        if text is None: text = self.i_inp.text()
        prev = self.m_inp.currentText()
        self.m_inp.blockSignals(True)
        self.m_inp.clear()
        base = ["None", "Main", "Options"]
        if text.strip():
            self.m_inp.addItems(base)
        else:
            self.m_inp.addItems(base)
            for cm in self._custom_menus:
                self.m_inp.addItem(cm)
        idx = self.m_inp.findText(prev)
        if idx >= 0:
            self.m_inp.setCurrentIndex(idx)
        elif prev and prev not in base and not text.strip():
            self.m_inp.addItem(prev)
            self.m_inp.setCurrentText(prev)
        else:
            self.m_inp.setCurrentIndex(0)
        self.m_inp.blockSignals(False)
    def _inherit_icon(self):
        cmd = self.data.get('cmd', '') or self.data.get('path', '') or self.f_inp.text() or self.ti_inp.text() or self.i_inp.text()
        target_path = _find_target_executable_or_shortcut(cmd)
        if not target_path:
            file_path, _ = QFileDialog.getOpenFileName(self, "Select Executable/Shortcut/Icon to Inherit From", "C:\\Program Files", "Executables & Shortcuts (*.exe *.lnk *.ico *.dll *.png)")
            if file_path:
                target_path = file_path
        if target_path:
            norm = os.path.normpath(target_path).replace('\\', '/')
            self.ic_inp.setText(f"image.res('{norm}')")

    def get_changes(self):
        d1 = self.get_data(); d2 = self.data
        changes = []
        key_names = {
            'find': 'Find Title',
            'in': 'In Menu',
            'title': 'New Title',
            'menu': 'Move to',
            'pos': 'Position',
            'vis': 'Visibility',
            'sep': 'Separator',
            'type': 'Show in',
            'icon': 'Icon / Image'
        }
        def format_user_friendly(prop_key, val):
            val_clean = str(val or '').strip('\'" ')
            if prop_key == 'vis':
                vl = val_clean.lower().strip()
                if not vl or vl in ("normal", "always visible", "vis.normal", "1"): return "Normal"
                if vl in ("vis.remove", "key.remove", "vis.hidden", "key.hidden", "remove", "hidden", "0"): return "Hide"
                if vl in ("key.shift()", "vis.shift", "shift", "key.shift"): return "Shift"
                if vl in ("key.control()", "key.ctrl()", "vis.control", "vis.ctrl", "control", "ctrl", "key.control", "key.ctrl"): return "Ctrl"
                if vl in ("key.capslock()", "key.caps()", "vis.capslock", "vis.caps", "capslock", "caps", "key.capslock", "key.caps"): return "Caps"
                if vl in ("key.lbutton()", "key.lmb()", "vis.lbutton", "vis.lmb", "lbutton", "lmb", "key.lbutton"): return "LMB"
                return val_clean
            if prop_key == 'sep':
                vl = val_clean.lower()
                if vl in ("true", "1", "before"): return "Before"
                if vl == "after": return "After"
                if vl == "both": return "Both"
                if vl in ("false", "0", "none", ""): return "None"
                return val_clean.title()
            if prop_key == 'menu':
                vl = val_clean.lower()
                if not vl or vl in ("none", "main", "menu.main"): return "Main"
                if vl in ("options", "title.options"): return "Options"
                return val_clean
            return val_clean or "(empty)"

        for k in ['find', 'in', 'title', 'menu', 'pos', 'vis', 'sep', 'type']:
            v1 = str(d1.get(k, '')).strip('\'" ')
            v2 = str(d2.get(k, '')).strip('\'" ')
            if k == 'find':
                if v1.startswith('*') and v1.endswith('*') and v1.strip('*') == v2: continue
                if v2.startswith('*') and v2.endswith('*') and v2.strip('*') == v1: continue
            if k == 'vis':
                v1_low = v1.lower()
                v2_low = v2.lower()
                v1_norm = "" if v1_low in ("normal", "always visible", "vis.normal") else ("vis.remove" if v1_low in ("vis.remove", "vis.hidden", "key.remove", "key.hidden", "remove", "hidden") else v1_low)
                v2_norm = "" if v2_low in ("normal", "always visible", "vis.normal") else ("vis.remove" if v2_low in ("vis.remove", "vis.hidden", "key.remove", "key.hidden", "remove", "hidden") else v2_low)
                if v1_norm == v2_norm: continue
            if k == 'menu':
                v1_norm = "" if v1.lower() in ("none", "main", "menu.main") else v1
                v2_norm = "" if v2.lower() in ("none", "main", "menu.main") else v2
                if v1_norm.lower() == v2_norm.lower(): continue
            if k == 'sep':
                v1_norm = "true" if v1.lower() in ("true", "1") else "false" if v1.lower() in ("false", "0", "none", "") else v1.lower()
                v2_norm = "true" if v2.lower() in ("true", "1") else "false" if v2.lower() in ("false", "0", "none", "") else v2.lower()
                if v1_norm == v2_norm: continue
            if v1.lower() != v2.lower():
                display_k = key_names.get(k, k.title())
                changes.append(f"{display_k}: {format_user_friendly(k, v2)} ➔ {format_user_friendly(k, v1)}")
        i1 = str(d1.get('icon') or d1.get('image') or '').strip('\'" ')
        i2 = str(d2.get('icon') or d2.get('image') or '').strip('\'" ')
        if i1 != i2:
            changes.append(f"Icon: '{i2 or '(none)'}' ➔ '{i1 or '(none)'}'")
        return changes

    def is_dirty(self):
        return len(self.get_changes()) > 0

    def reject(self):
        if self.is_dirty():
            from utils import UnsavedChangesDialog
            changes = self.get_changes()
            dialog = UnsavedChangesDialog(None, text="You have unsaved changes in this rule. Do you want to save them?", changes=changes)
            res = dialog.exec_()
            if res == 1:
                self.accept(); return
            elif res == 2:
                return
                
        import os
        for path in self.created_temp_icons:
            if os.path.exists(path):
                try: os.remove(path)
                except: pass
                
        super().reject()

    def accept(self):
        import os
        final_val = self.ic_inp.text().strip('\'" ')
        final_path = _resolve_app_dir_path(final_val)
        
        for path in self.created_temp_icons:
            if path != final_path and os.path.exists(path):
                try: os.remove(path)
                except: pass
                
        init_val = str(self.data.get('icon') or self.data.get('image') or '').strip('\'" ')
        if init_val.startswith('@app.dir\\imports\\icons\\') and init_val != final_val:
            init_path = _resolve_app_dir_path(init_val)
            if init_path and os.path.exists(init_path):
                try: os.remove(init_path)
                except: pass
                
        self.data = self.get_data()
        super().accept()

    def _open_glyph_browser(self):
        orig = self.ic_inp.text().strip()
        dlg = GlyphBrowserDialog(orig, self)
        if dlg.exec_():
            if dlg.result_value != orig:
                self.ic_inp.setText(dlg.result_value)
                self.live_update.emit(self.get_data())
        else:
            self.ic_inp.setText(orig)
    def _browse_icon(self):
        from PyQt5.QtWidgets import QFileDialog
        import os
        path, _ = QFileDialog.getOpenFileName(self, "Select Icon", "", "Images (*.png *.ico *.bmp *.jpg *.svg)")
        if path:
            norm_path = os.path.normpath(path)
            dlg = LocalIconTintDialog(norm_path, self)
            if dlg.exec_():
                if hasattr(dlg, 'saved_path'): self.created_temp_icons.append(dlg.saved_path)
                self.ic_inp.setText(dlg.result_value)
                self.live_update.emit(self.get_data())
    def _update_colors_ui(self):
        while self.c_lay.count():
            it = self.c_lay.takeAt(0); (it.widget().deleteLater() if it.widget() else None)
        colors = _extract_all_colors(self.ic_inp.text())
        theme_cs = _get_theme_glyph_colors()
        codes = _extract_glyph_codes(self.ic_inp.text())
        num_pellets = len(codes) if codes else (1 if self.ic_inp.text() else 0)
        
        for i in range(max(num_pellets, len(colors))):
            if i >= 2: break
            c = colors[i] if i < len(colors) else None
            btn = ColorPellet(c or theme_cs[min(i, 1)])
            btn.clicked.connect(lambda checked, idx=i, oc=c: self._pick_color(idx, oc))
            self.c_lay.addWidget(btn)

        val = self.ic_inp.text()
        if codes and any(colors):
            sync_btn = IconSyncButton(self)
            sync_btn.setToolTip("Sync with Theme (Remove custom colors)")
            sync_btn.clicked.connect(self._reset_glyph_colors)
            self.c_lay.insertWidget(0, sync_btn)

    def _reset_glyph_colors(self):
        codes = _extract_glyph_codes(self.ic_inp.text())
        if codes: self.ic_inp.setText(_build_glyph_val(codes, []))
        self.live_update.emit(self.get_data())
    def _pick_color(self, idx, old_color):
        theme_cs = _get_theme_glyph_colors()
        dlg = MinimalColorPickerDialog(old_color or theme_cs[min(idx, 1)], f"svg_c_{idx}", self); dlg.default_checkbox.hide()
        def on_color(key, hex_color):
            new_val = _get_new_asset_value(self.ic_inp.text(), old_color, hex_color, idx=idx)
            self.ic_inp.setText(new_val)
            self.live_update.emit(self.get_data())
        dlg.colorSelected.connect(on_color); dlg.exec_()
    def _update_icon_preview(self, text):
        _update_label_asset(self.ic_prev_lbl, text)
        if not text:
             self.ic_prev_lbl.setText("\u2726"); self.ic_prev_lbl.setStyleSheet("color: rgba(220, 20, 60, 0.3); font-size: 18px; background: rgba(255,255,255,0.03); border-radius: 10px; border: 1px solid rgba(255,255,255,0.05);")
    def load_data(self, d):
        self.vis_widget.set_value(d.get('vis', ''))
        self.type_widget.set_value(d.get('type', ''))

        f = d.get('find', '')
        if f:
            mode = "contains"; clean_f = f
            if f.startswith('"') and f.endswith('"'): mode = "exact"; clean_f = f[1:-1]
            elif f.startswith('*') and f.endswith('*'): mode = "contains"; clean_f = f[1:-1]
            elif f.startswith('*'): mode = "ends"; clean_f = f[1:]
            elif f.endswith('*'): mode = "starts"; clean_f = f[:-1]
            self.f_inp.setText(clean_f.strip('\'"'))
            for b in self.find_mode_group.buttons():
                if b.property("mode") == mode: b.setChecked(True); break
        
        self.i_inp.setText(d.get('in', '').strip('\'"')); self.ti_inp.setText(str(d.get('title', '')).strip('\'"'))
        
        m = str(d.get('menu', '')).strip('\'"')
        m_low = m.lower()
        if 'menu' not in d: self.m_inp.setCurrentText("None")
        elif not m or m_low in ("main", "menu.main"): self.m_inp.setCurrentText("Main")
        elif m_low in ("options", "title.options"): self.m_inp.setCurrentText("Options")
        else:
            if m not in [self.m_inp.itemText(i) for i in range(self.m_inp.count())]:
                self.m_inp.addItem(m)
            self.m_inp.setCurrentText(m)

        self.ic_inp.setText(str(d.get('icon') or d.get('image') or '')); self._update_icon_preview(self.ic_inp.text())
        p = str(d.get('pos', '')).strip('\'"')
        (self.p_inp.setCurrentText(p) if p in self.POS_OPTIONS else (self.p_inp.addItem(p), self.p_inp.setCurrentText(p)))
        s = str(d.get('sep', '')).strip('\'"')
        (self.sep_box.setCurrentText("None") if not s else self.sep_box.setCurrentText("Before") if (s.lower() in ('true', '1')) else self.sep_box.setCurrentText(s.title()))
    def get_data(self):
        res = self.data.copy()
        f = self.f_inp.text().strip()
        if f:
            mode = self.find_mode_group.checkedButton().property("mode")
            if mode == "exact": f = f'"{f}"'
            elif mode == "ends": f = f'*{f}'
            elif mode == "starts": f = f'{f}*'
            # Contains is now just f (no stars)
            res['find'] = f
        else: res.pop('find', None)
        
        in_val = self.i_inp.text().strip()
        if in_val: res['in'] = in_val
        else: res.pop('in', None)
        
        title_val = self.ti_inp.text().strip()
        if title_val:
            res['title'] = f"'{title_val}'" if ' ' in title_val else title_val
        else: res.pop('title', None)
        
        m = self.m_inp.currentText()
        if m == "Main": res['menu'] = ""
        elif m == "Options": res['menu'] = "options"
        elif m == "None": res.pop('menu', None)
        elif m.strip(): res['menu'] = m.strip()
        else: res.pop('menu', None)
        
        p = self.p_inp.currentText().strip()
        if p: res['pos'] = p
        else: res.pop('pos', None)
        
        vis_val = self.vis_widget.get_value()
        if vis_val:
            res['vis'] = vis_val
        else:
            res.pop('vis', None)

        type_val = self.type_widget.get_value()
        if type_val:
            res['type'] = type_val
        else:
            res.pop('type', None)
        
        i = self.ic_inp.text().strip()
        res.pop('icon', None); res.pop('image', None)
        if i:
            is_glyph = '\\u' in i or '[' in i or 'image.glyph' in i or '0x' in i
            key = 'image' if is_glyph else 'icon'
            res[key] = i
            
        sv = self.sep_box.currentText().lower()
        if sv == "none": res.pop('sep', None); res.pop('separator', None)
        elif sv == "before": res['sep'] = True
        elif sv == "after": res['sep'] = 'after'
        elif sv == "both": res['sep'] = 'both'
        else: res['sep'] = sv
        return res

def is_rule_complete(props):
    for k in ('title', 'menu', 'pos', 'vis', 'icon', 'image', 'sep', 'type'):
        v = props.get(k)
        if v is not None:
            if isinstance(v, str) and v.strip(): return True
            if isinstance(v, bool) and v is True: return True
    return False

class ModifyWidget(QWidget):
    reload_requested = pyqtSignal()
    rules_saved = pyqtSignal()
    def filter_rules(self, t=None): 
        action_tag = self.rules_tags.group.checkedButton().text()
        self.model.filter(self.search.text(), action_tag=action_tag)
    def filter_ids(self, t):
        t = t.lower()
        for w in self.id_widgets: w.setVisible(t in w.id_text.lower() or t in w.label.text().lower())
        self.id_cont_l.invalidate()
    def set_dirty(self): 
        if not self.is_dirty: self.original_content = read_file(self.filepath)
        self.is_dirty = True; self.status_label.setText("Unsaved changes (Previewing)..."); self.status_label.setStyleSheet("color: #dc143c;")
        self.save_ids(preview=True)

    def __init__(self, modify_nss_path, shell_nss_path, project_root):
        super().__init__(); _init_nilesoft_font(); self.filepath = modify_nss_path; self.shell_nss_path = shell_nss_path; self.project_root = project_root; self.main_layout = QVBoxLayout(self); self.main_layout.setContentsMargins(15, 15, 15, 15); self.is_dirty = False; self.auto_save = False; self.original_content = read_file(self.filepath); self.load_and_init_ui()
    def load_and_init_ui(self):
        old_idx = -1
        for i in range(self.main_layout.count()):
            w = self.main_layout.itemAt(i).widget()
            if isinstance(w, QTabWidget):
                old_idx = w.currentIndex()
                break

        while self.main_layout.count():
            it = self.main_layout.takeAt(0)
            w = it.widget()
            if w:
                w.setParent(None)
                w.deleteLater()
        content = read_file(self.filepath); self.custom_rules = extract_custom_rules(content)
        tab = QTabWidget()
        tab.setObjectName("modernTabWidget")
        tab.setIconSize(QSize(28, 28))
        rules_pg = QWidget(); rl = QVBoxLayout(rules_pg); head = QHBoxLayout(); self.search = QLineEdit(); self.search.setPlaceholderText("Search rules..."); self.search.textChanged.connect(self.filter_rules); self.search.setStyleSheet("QLineEdit { background: rgba(255,255,255,0.05); border: 1px solid #2a2a30; border-radius: 15px; padding: 10px 15px; color: white; } QLineEdit:focus { border: 1px solid #dc143c; }")
        add = QPushButton("+ New Rule"); add.setObjectName("saveButton"); add.setCursor(Qt.PointingHandCursor); add.clicked.connect(self.add_new_rule_dialog)
        head.addWidget(self.search); head.addWidget(add); rl.addLayout(head)
        
        self.rules_tags = FilterBar([
            ("All", "#2a2a30"), ("Renamed", "#808080"), ("Icons", "#4A90E2"), 
            ("Hidden", "#dc143c"), ("Part Hidden", "#9B59B6"), ("Moved", "#E29E4A"), 
            ("Position", "#4AE290"), ("Separator", "#F1C40F")
        ])
        self.rules_tags.filter_changed.connect(lambda _: self.filter_rules())
        rl.addWidget(self.rules_tags)
        self.view = QListView(); self.view.setStyleSheet("background: transparent; border: none;")
        self.view.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.view.setSpacing(0); self.view.setMouseTracking(True)
        self.model = NSSItemModel(); self.view.setModel(self.model)
        self.delegate = NSSItemDelegate(self.view); self.view.setItemDelegate(self.delegate)
        rl.addWidget(self.view)
        
        ids_pg = QWidget(); idl = QVBoxLayout(ids_pg); ihead = QHBoxLayout(); self.id_search = QLineEdit(); self.id_search.setPlaceholderText("Search system IDs..."); self.id_search.textChanged.connect(self.filter_ids); self.id_search.setStyleSheet(self.search.styleSheet()); ihead.addWidget(self.id_search)
        idl.addLayout(ihead); iscroll = QScrollArea(); iscroll.setWidgetResizable(True); iscroll.setStyleSheet("background: transparent; border: none;"); self.id_cont = QWidget(); self.id_cont_l = FlowLayout(self.id_cont, margin=10, spacing=10); iscroll.setWidget(self.id_cont); idl.addWidget(iscroll); self.imports_pg = ImportsWidget(self.project_root, self.shell_nss_path)
        self.imports_pg.reload_requested.connect(self.reload_requested.emit)
        
        tab.addTab(rules_pg, get_mdl2_icon(0xE15E, 40), "Rules")
        tab.addTab(self.imports_pg, get_mdl2_icon(0xE8B5, 40), "Imports")
        tab.addTab(ids_pg, get_mdl2_icon(0xE71B, 40), "IDS")
        if old_idx != -1: tab.setCurrentIndex(old_idx)
        self.main_layout.addWidget(tab); self.status_label = QLabel(""); self.status_label.setStyleSheet("color: #dc143c; font-weight: 500;"); self.main_layout.addWidget(self.status_label)
        
        all_ids = sorted(list(set(DEFAULT_IDS + extract_ids_from_section(content, "hide") + extract_ids_from_section(content, "more") + extract_ids_from_section(content, "shift"))))
        h, m, s = extract_ids_from_section(content, "hide"), extract_ids_from_section(content, "more"), extract_ids_from_section(content, "shift"); self.id_widgets = []
        for i in all_ids:
            v = 'key.shift()' if i in s else None; mn = 'title.options' if i in m else None; hid = (i in h)
            w = IDEntryWidget(i, i.replace("id.", "").replace("_", " ").title(), mn, v, hid); w.changed.connect(lambda *args: self.save_ids(False)); self.id_widgets.append(w); self.id_cont_l.addWidget(w)
        
        self.refresh_rules_model()

    def refresh_rules_model(self):
        content = read_file(self.filepath)
        self.custom_rules = extract_custom_rules(content)
        for r in self.custom_rules: r['file'] = self.filepath
        self.model.set_items(self.custom_rules)
        # Clear preview status if it was active
        if self.status_label.text() == "Previewing changes...":
            self.status_label.setText("")
    def refresh_ui(self): self.refresh_rules_model()
    def revert_changes(self):
        if self.is_dirty:
            safe_file_write(self.filepath, self.original_content)
            self.is_dirty = False; self.status_label.setText("Changes Reverted"); self.status_label.setStyleSheet("color: #dc143c;")
            self.refresh_rules_model(); self.reload_requested.emit()



    def save_ids(self, preview=False):
        try:
            content = read_file(self.filepath); h = [w.id_text for w in self.id_widgets if w.is_hidden]; m = [w.id_text for w in self.id_widgets if w.menu == 'title.options']; s = [w.id_text for w in self.id_widgets if w.vis == 'key.shift()']
            content = update_section(content, "// hide\nmodify(mode=mode.multiple\nwhere=this.id(", ") vis=vis.remove)", h); content = update_section(content, "// more\nmodify(mode=mode.multiple\nwhere=this.id(", ") menu=title.options)", m); content = update_section(content, "// shift\nmodify(mode=single\nwhere=this.id(", ") vis=key.shift())", s)
            
            def on_done(fp):
                self.reload_requested.emit()
                if not preview:
                    self.is_dirty = False; self.status_label.setText("IDS Saved"); self.status_label.setStyleSheet("color: #dc143c;")
            
            write_file(self.filepath, content, on_success=on_done)
        except Exception as e: self.status_label.setText(f"Error: {str(e)}"); self.status_label.setStyleSheet("color: #dc143c;")

    def on_item_clicked(self, index):
        item = index.data(Qt.UserRole)
        if item: self.edit_rule(item)

    def edit_rule(self, item):
        props = item.get('props', {}); orig_props = props.copy(); orig_content = read_file(self.filepath)
        d = ModifyRuleEditorDialog(props, self)
        self.live_timer = QTimer(); self.live_timer.setSingleShot(True)
        preview_saved = {'saved': False}
        def do_live_save():
            preview_saved['saved'] = True
            self.save_all_modifications()
        self.live_timer.timeout.connect(do_live_save)

        def handle_preview(nd):
            for r in self.custom_rules:
                if r is item or (r.get('start') == item.get('start') and r.get('type') == item.get('type')):
                    r['props'] = nd; break
            self.model.layoutChanged.emit()
            if is_rule_complete(nd):
                self.live_timer.start(1000)
                self.status_label.setText("Previewing changes...")
                self.status_label.setStyleSheet("color: #dc143c;")
            else:
                self.live_timer.stop()
                self.status_label.setText("Incomplete rule - Auto-save paused")
                self.status_label.setStyleSheet("color: #dc143c;")
        d.live_update.connect(handle_preview)
        if d.exec_():
            self.live_timer.stop()
            updated_data = d.get_data()
            if not self.is_dirty: self.original_content = read_file(self.filepath)
            self.is_dirty = True
            
            if is_rule_complete(updated_data):
                for r in self.custom_rules:
                    if r is item or (r.get('start') == item.get('start') and r.get('type') == item.get('type')):
                        r['props'] = updated_data; break
            else:
                self.custom_rules = [r for r in self.custom_rules if not (r is item or (r.get('start') == item.get('start') and r.get('type') == item.get('type')))]
                
            self.save_all_modifications()
            self.model.set_items(self.custom_rules)
            self.filter_rules(self.search.text())
        else:
            self.live_timer.stop()
            item['props'] = orig_props
            if preview_saved['saved']:
                write_file(self.filepath, orig_content)
                self.refresh_rules_model()
                self.reload_requested.emit()
            else:
                self.refresh_rules_model()

    def add_new_rule_dialog(self):
        orig_content = read_file(self.filepath); d = ModifyRuleEditorDialog(parent=self)
        self.live_timer = QTimer(); self.live_timer.setSingleShot(True)
        preview_saved = {'saved': False}
        def do_live_save():
            preview_saved['saved'] = True
            self.save_all_modifications()
        self.live_timer.timeout.connect(do_live_save)

        def handle_new_preview(nd):
            temp_item = {'type': 'modify', 'props': nd, 'file': self.filepath}
            self.custom_rules = [r for r in self.custom_rules if not r.get('_is_temp')]
            temp_item['_is_temp'] = True
            self.custom_rules.insert(0, temp_item)
            self.model.layoutChanged.emit()
            self.status_label.setText("Drafting new rule...")
            self.status_label.setStyleSheet("color: #b0b0b0;")
            if is_rule_complete(nd):
                self.live_timer.start(1000)
        d.live_update.connect(handle_new_preview)
        if d.exec_():
            self.live_timer.stop()
            final_data = d.get_data()
            self.custom_rules = [r for r in self.custom_rules if not r.get('_is_temp')]
            if is_rule_complete(final_data):
                new_item = {'type': 'modify', 'props': final_data, 'file': self.filepath}
                self.custom_rules.insert(0, new_item)
            self.model.set_items(self.custom_rules)
            self.save_all_modifications()
            self.filter_rules(self.search.text())
        else: 
            self.live_timer.stop()
            self.custom_rules = [r for r in self.custom_rules if not r.get('_is_temp')]
            self.model.set_items(self.custom_rules)
            if preview_saved['saved']:
                write_file(self.filepath, orig_content)

    def delete_rule(self, item):
        if item in self.custom_rules:
            self.custom_rules.remove(item); self.model.set_items(self.custom_rules); self.save_all_modifications()


    def save_all_modifications(self):
        try:
            content = read_file(self.filepath)
            start_m, end_m = "// -- iMA Managed --", "// -- End iMA Managed --"
            managed = []
            
            # Filter out rules that only have target criteria but no actions (empty modifications)
            self.custom_rules = [r for r in self.custom_rules if is_rule_complete(r.get('props', {}))]

            for item in self.custom_rules:
                data = item.get('props', {})
                if not is_rule_complete(data):
                    continue

                pts = []
                pr = ['find', 'type', 'where', 'in', 'pos', 'title', 'menu', 'vis', 'icon', 'image']
                for k in pr:
                    v = data.get(k)
                    if v is not None and (str(v).strip() != '' or k in ('menu', 'title')):
                        pts.append(format_nss_value(k, v))
                
                for k, v in data.items(): 
                    if k not in pr and k not in ('sep', '_order', 'file', 'start', 'end') and str(v).strip() != '':
                        pts.append(format_nss_value(k, v))
                
                if data.get('sep'):
                    sv = data['sep']
                    if sv is True: pts.append("sep=before")
                    else: pts.append(f"sep={sv}")

                if pts:
                    managed.append(f"    modify({ ' '.join(pts) })")
            
            block = f"{start_m}\n" + "\n".join(managed) + f"\n{end_m}"
            
            import re
            s_re = re.compile(r"//\s*--\s*iMA\s*Managed\s*--", re.IGNORECASE)
            e_re = re.compile(r"//\s*--\s*End\s*iMA\s*Managed\s*--", re.IGNORECASE)
            
            s_match = s_re.search(content); e_match = e_re.search(content)
            
            if s_match and e_match:
                new_content = content[:s_match.start()] + block + content[e_match.end():]
            else:
                lines = content.splitlines(); rem = []
                for l in lines:
                    sl = l.strip()
                    if re.match(r'^modify\s*\(.*?\)\s*$', sl, re.IGNORECASE) and "where=this.id(" not in sl: continue
                    rem.append(l)
                new_content = "\n".join(rem).rstrip() + "\n\n" + block + "\n"
            
            def on_success(fp):
                if hasattr(NSSCacheManager, '_cache') and self.filepath in NSSCacheManager._cache:
                    del NSSCacheManager._cache[self.filepath]
                self.show_status("Rules Saved")
                self.refresh_rules_model()
                self.rules_saved.emit()
                self.reload_requested.emit()
                
            def on_error(fp, err):
                self.show_error(f"Save failed: {err}")
                
            from utils import global_undo_stack, FileChangeCommand
            old_content = read_file(self.filepath)
            cmd = FileChangeCommand(self.filepath, old_content, new_content, on_success, on_error)
            global_undo_stack.push(cmd)
            self.is_dirty = False
            
        except Exception as e: self.show_error(f"Save setup failed: {str(e)}")
        
    def show_status(self, t): self.status_label.setText(t); self.status_label.setStyleSheet("color: #dc143c;"); QTimer.singleShot(3000, lambda: self.status_label.setText(""))
    def show_error(self, t): m = CustomMessageBox(self); m.setText("Error"); m.setInformativeText(t); m.exec_()

def read_file(path): return open(path, 'r', encoding='utf-8').read() if os.path.exists(path) else ""
def write_file(path, content, on_success=None, on_error=None): 
    from utils import global_undo_stack, FileChangeCommand
    old_content = read_file(path)
    cmd = FileChangeCommand(path, old_content, content, on_success, on_error)
    global_undo_stack.push(cmd)
    
def extract_ids_from_section(content, name):
    p = re.compile(r"//\s*" + re.escape(name) + r".*?where=this\.id\((.*?)\)", re.DOTALL); m = p.search(content)
    return [l.strip().rstrip(',') for l in m.group(1).split('\n') if l.strip().startswith("id.")] if m else []
def extract_custom_rules(content):
    start, end = "// -- iMA Managed --", "// -- End iMA Managed --"
    s_idx, e_idx = content.find(start), content.find(end)
    m_content = content[s_idx + len(start):e_idx] if (s_idx != -1 and e_idx != -1) else content
    items = find_items_and_menus(m_content, types=('modify',))
    rules = []
    for it in items:
        # If it was a generic scan (no managed markers), skip items with 'where' (likely built-ins)
        if s_idx == -1 and 'where' in it['props']: continue
        if not is_rule_complete(it.get('props', {})): continue
        rules.append(it)
    return rules
def update_section(content, sm, em, ids):
    s = content.find(sm); e = content.find(em, s)
    return content if (s == -1 or e == -1) else content[:s+len(sm)] + "\n" + ",\n".join([f"    {i}" for i in ids]) + "\n" + content[e:]




def cleanup_orphan_icons(root):
    import os, shutil, re
    icons_dir = os.path.join(root, 'imports', 'icons')
    if not os.path.exists(icons_dir): return
    
    # 1. Collect all NSS content to check for references
    nss_contents = []
    search_paths = [os.path.join(root, 'imports'), os.path.join(root, 'plugins'), os.path.join(root, 'shell.nss')]
    for p in search_paths:
        if not os.path.exists(p): continue
        if os.path.isfile(p):
            try:
                with open(p, 'r', encoding='utf-8') as f: nss_contents.append(f.read().lower())
            except: pass
        else:
            for r, _, files in os.walk(p):
                for f in files:
                    if f.endswith('.nss'):
                        try:
                            with open(os.path.join(r, f), 'r', encoding='utf-8') as f_obj:
                                nss_contents.append(f_obj.read().lower())
                        except: pass

    # 2. List all files in icons dir and check if their names appear in any NSS content
    for r, dirs, files in os.walk(icons_dir):
        if 'originals' in r: continue
        for f in files:
            # We only care about cleaning up tinted icons to avoid accidental data loss
            # Tinted icons have the pattern _[hash].png
            if not re.search(r'_[a-f0-9]{6}\.(?:png|ico|bmp|svg)$', f, re.I): continue
            
            full_path = os.path.join(r, f)
            f_lower = f.lower()
            
            # Check if this specific filename is referenced anywhere
            is_referenced = False
            for content in nss_contents:
                if f_lower in content:
                    is_referenced = True
                    break
            
            if not is_referenced:
                try: os.remove(full_path)
                except: pass
        
    # Clean up empty subdirs
    for r, dirs, files in os.walk(icons_dir, topdown=False):
        if 'originals' in r: continue
        if not dirs and not files:
            try: os.rmdir(r)
            except: pass
