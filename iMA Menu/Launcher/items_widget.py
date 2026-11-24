import os
import sys
import difflib
import re
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QStackedWidget, QDialog, QSizePolicy,
    QTextEdit, QGraphicsOpacityEffect, QButtonGroup
)
from PyQt5.QtGui import QColor, QFont, QPixmap, QCursor, QPainter, QPen, QIcon, QPainterPath, QFontMetrics
from PyQt5.QtCore import Qt, pyqtSignal, QSize, QTimer, QRectF

from utils import (
    PillPushButton, PillLineEdit, render_nss_asset_pixmap, get_mdl2_icon,
    FlowLayout, ModernDialog, _init_nilesoft_font, NILESOFT_FONT_FAMILY, get_font_icon
)
from items_manager import ItemsManager
from modify_widget import ImportEditorDialog
from nss_parser import find_items_and_menus, format_nss_value


def extract_snippet_flags(snippet_data):
    """Extracts human-friendly badges from snippet metadata and code using Edit tab colors."""
    flags = []
    cat = snippet_data.get("category", "")
    if cat:
        flags.append(("category", cat, "#8caaee"))

    raw = snippet_data.get("full_code", "") or snippet_data.get("code", "")

    # Context / Type flag (Human-friendly)
    m_type = re.search(r'\btype\s*=\s*[\'"]?([^\'",)\s]+)', raw, re.IGNORECASE)
    if m_type:
        raw_types = set(m_type.group(1).lower().replace('.', '|').split('|'))
        if {'file', 'dir', 'back'}.issubset(raw_types) or {'desktop', 'dir', 'file'}.issubset(raw_types):
            type_label = "Everywhere"
        elif 'back' in raw_types and 'desktop' in raw_types:
            type_label = "Desktop Background"
        elif 'back' in raw_types and 'dir' in raw_types:
            type_label = "Folder Background"
        elif 'file' in raw_types and 'dir' in raw_types:
            type_label = "Files & Folders"
        elif 'file' in raw_types:
            type_label = "Files Only"
        elif 'dir' in raw_types:
            type_label = "Folders Only"
        elif 'taskbar' in raw_types:
            type_label = "Taskbar"
        elif 'drive' in raw_types:
            type_label = "Drives"
        else:
            type_label = m_type.group(1).replace('|', ' & ').title()
        flags.append(("type", type_label, "#a6d189"))

    # Admin flag (Text only, NO blue shield emoji)
    if re.search(r'(?:^|[\s,(])admin(?:\s*=\s*(?:1|true|\'1\'|\'true\'))?(?:[\s,)]|$)', raw, re.IGNORECASE):
        flags.append(("admin", "Admin", "#e78284"))

    # Key / Modifier Trigger (CTRL, SHIFT, etc.)
    has_ctrl = "key.control" in raw.lower() or "keys.control" in raw.lower() or "key='ctrl'" in raw.lower() or "key='control'" in raw.lower()
    has_shift = "key.shift" in raw.lower() or "keys.shift" in raw.lower() or "key='shift'" in raw.lower()
    if has_ctrl and has_shift:
        flags.append(("key", "Ctrl + Shift + Right Click", "#e5c890"))
    elif has_ctrl:
        flags.append(("key", "Ctrl + Right Click", "#e5c890"))
    elif has_shift:
        flags.append(("key", "Shift + Right Click", "#e5c890"))

    # Position
    m_pos = re.search(r'\bpos\s*=\s*([^\s,)]+)', raw, re.IGNORECASE)
    if m_pos:
        pos_val = m_pos.group(1).strip("'\"")
        flags.append(("pos", f"Position: {pos_val.title()}", "#ef9f76"))

    # Menu
    if raw.strip().lower().startswith("menu(") or snippet_data.get("menu_name"):
        flags.append(("menu", "Submenu", "#ca9ee6"))

    return flags


class AntialiasedTag(QWidget):
    """Vector antialiased tag badge matching Edit tab flag styling."""
    def __init__(self, text, base_color="#8caaee", bg_color=None, border_color=None, parent=None):
        super().__init__(parent)
        self.text = text
        c = QColor(base_color)
        if not c.isValid():
            c = QColor("#8caaee")
        self.fg = QColor("#c6d0f5")
        self.bg = QColor(c.red(), c.green(), c.blue(), 38)
        self.border = QColor(c.red(), c.green(), c.blue(), 100)
        self.setFixedHeight(20)
        self.setFont(QFont("Google Sans", 8, QFont.Bold))
        fm = QFontMetrics(self.font())
        w = fm.horizontalAdvance(text) + 16
        self.setFixedWidth(max(w, 44))

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setRenderHint(QPainter.TextAntialiasing, True)
        r = QRectF(self.rect()).adjusted(0.75, 0.75, -0.75, -0.75)
        path = QPainterPath()
        radius = r.height() / 2.0
        path.addRoundedRect(r, radius, radius)
        p.fillPath(path, self.bg)
        p.setPen(QPen(self.border, 1.2))
        p.drawPath(path)
        p.setPen(self.fg)
        p.setFont(self.font())
        p.drawText(r, Qt.AlignCenter, self.text)
        p.end()


class AntialiasedIconCircle(QWidget):
    """Vector antialiased circular container for item icons."""
    def __init__(self, size=40, bg_color=None, border_color=None, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        bg = QColor(bg_color) if bg_color is not None else QColor()
        self.bg = bg if bg.isValid() else QColor(255, 255, 255, 15)
        bd = QColor(border_color) if border_color is not None else QColor()
        self.border = bd if bd.isValid() else QColor(255, 255, 255, 28)
        self.pixmap = None
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)

    def set_pixmap(self, pm):
        self.pixmap = pm
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setRenderHint(QPainter.SmoothPixmapTransform, True)
        r = QRectF(self.rect()).adjusted(1.0, 1.0, -1.0, -1.0)
        p.setBrush(self.bg)
        p.setPen(QPen(self.border, 1.2))
        p.drawEllipse(r)
        if self.pixmap and not self.pixmap.isNull():
            px = int((self.width() - self.pixmap.width()) / 2)
            py = int((self.height() - self.pixmap.height()) / 2)
            p.drawPixmap(px, py, self.pixmap)
        p.end()


class AntialiasedCircleButton(QPushButton):
    """Vector antialiased circular action button with smooth hover glow."""
    def __init__(self, icon_char, tooltip="", parent=None, size=30, accent=False):
        super().__init__(parent)
        self.icon_char = icon_char
        self.setToolTip(tooltip)
        self.setFixedSize(size, size)
        self.setCursor(Qt.PointingHandCursor)
        self.accent = accent
        _init_nilesoft_font()
        self.setFont(QFont("Segoe MDL2 Assets", 10))
        self.setAttribute(Qt.WA_Hover, True)
        self.setStyleSheet("background: transparent; border: none; outline: none;")

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setRenderHint(QPainter.TextAntialiasing, True)
        r = QRectF(self.rect()).adjusted(1.0, 1.0, -1.0, -1.0)
        is_hov = self.underMouse()
        is_down = self.isDown()

        if self.accent:
            bg = QColor("#ca9ee6") if is_hov else QColor(202, 158, 230, 30)
            border = QColor("#ca9ee6") if is_hov else QColor(202, 158, 230, 80)
            fg = QColor("#18181c") if is_hov else QColor("#ca9ee6")
        else:
            bg = QColor(231, 130, 132, 50) if is_hov else QColor(255, 255, 255, 12)
            border = QColor("#e78284") if is_hov else QColor(255, 255, 255, 26)
            fg = QColor("#ffffff") if is_hov else QColor("#c6d0f5")

        if is_down:
            bg = bg.darker(115)

        p.setBrush(bg)
        p.setPen(QPen(border, 1.2))
        p.drawEllipse(r)

        p.setPen(fg)
        p.setFont(self.font())
        p.drawText(r, Qt.AlignCenter, self.icon_char)
        p.end()


class CategoryFilterButton(QPushButton):
    """Pill-shaped filter button for item categories matching Edit tab FilterTag."""
    def __init__(self, text, color="#51576d", icon_glyph=None, parent=None):
        super().__init__(text, parent)
        self.icon_glyph = icon_glyph
        self._color = QColor(color)
        if not self._color.isValid():
            self._color = QColor("#51576d")
        self.setCheckable(True)
        self.setFixedHeight(28)
        self.setCursor(Qt.PointingHandCursor)
        self.setFont(QFont("Google Sans", 9, QFont.Bold))
        self.setAttribute(Qt.WA_Hover, True)
        self.setStyleSheet("background: transparent; border: none; outline: none;")

    def sizeHint(self):
        fm = QFontMetrics(self.font())
        w = fm.horizontalAdvance(self.text().strip()) + 26
        return QSize(max(w, 58), 28)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setRenderHint(QPainter.TextAntialiasing, True)
        r = QRectF(self.rect()).adjusted(1.0, 1.0, -1.0, -1.0)
        path = QPainterPath()
        radius = r.height() / 2.0
        path.addRoundedRect(r, radius, radius)

        is_chk = self.isChecked()
        is_hov = self.underMouse()
        c = self._color

        if is_chk:
            bg = c
            border = c.lighter(115)
            fg = QColor("#ffffff")
        elif is_hov:
            bg = QColor(c.red(), c.green(), c.blue(), 75)
            border = QColor(c.red(), c.green(), c.blue(), 180)
            fg = QColor("#ffffff")
        else:
            bg = QColor(c.red(), c.green(), c.blue(), 38)
            border = QColor(c.red(), c.green(), c.blue(), 90)
            fg = QColor("#c6d0f5")

        p.fillPath(path, bg)
        p.setPen(QPen(border, 1.5))
        p.drawPath(path)

        p.setPen(fg)
        p.setFont(self.font())
        p.drawText(r, Qt.AlignCenter, self.text())
        p.end()


class SnippetCard(QFrame):
    """Vector antialiased card presenting a single snippet in the gallery."""
    clicked = pyqtSignal(str)
    edit_requested = pyqtSignal(str)
    restore_requested = pyqtSignal(str)
    toggle_requested = pyqtSignal(str, bool)

    def __init__(self, snippet_data, status, has_update, is_customized=False, view_mode="grid", parent=None):
        super().__init__(parent)
        self.snippet_data = snippet_data
        self.snippet_id = snippet_data["id"]
        self.status = status  # 'full', 'partial', 'none'
        self.has_update = has_update
        self.is_customized = is_customized
        self.view_mode = view_mode

        self.setObjectName("snippetCard")
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.NoFocus)
        self.setAttribute(Qt.WA_Hover, True)
        if self.view_mode == "list":
            self.setFixedHeight(62)
        else:
            self.setFixedHeight(114)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setStyleSheet("QFrame#snippetCard { background: transparent; border: none; }")
        self._setup_ui()

    def minimumSizeHint(self):
        return QSize(220, 62 if self.view_mode == "list" else 114)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        r = QRectF(self.rect()).adjusted(0.75, 0.75, -0.75, -0.75)
        path = QPainterPath()
        radius = 12.0 if self.view_mode == "list" else 14.0
        path.addRoundedRect(r, radius, radius)

        is_hov = self.underMouse()
        if self.status == "full":
            bg = QColor(166, 209, 137, 38) if is_hov else QColor(166, 209, 137, 22)
            border = QColor("#a6d189") if is_hov else QColor(166, 209, 137, 95)
        else:
            bg = QColor(14, 14, 14, 220) if is_hov else QColor(18, 18, 18, 140)
            border = QColor(231, 130, 132, 120) if is_hov else QColor(255, 255, 255, 22)

        p.fillPath(path, bg)
        p.setPen(QPen(border, 1.5 if is_hov else 1.0))
        p.drawPath(path)
        p.end()

    def _setup_ui(self):
        main_lay = QHBoxLayout(self)
        if self.view_mode == "list":
            main_lay.setContentsMargins(12, 6, 12, 6)
            main_lay.setSpacing(10)
        else:
            main_lay.setContentsMargins(14, 10, 14, 10)
            main_lay.setSpacing(12)

        # Left Icon Preview
        ic_box_sz = 36 if self.view_mode == "list" else 44
        self.icon_circle = AntialiasedIconCircle(size=ic_box_sz, parent=self)

        raw_icon = self.snippet_data.get("glyph", "") or self.snippet_data.get("icon", "")
        if not raw_icon:
            m_img = re.search(r'\b(?:image|icon)\s*=\s*([^\s,)]+)', self.snippet_data.get("full_code", "") or self.snippet_data.get("code", ""))
            if m_img:
                raw_icon = m_img.group(1).strip("'\"")

        ic_sz = 18 if self.view_mode == "list" else 22
        pixmap = render_nss_asset_pixmap(raw_icon, ic_sz)
        if pixmap and not pixmap.isNull():
            self.icon_circle.set_pixmap(pixmap)
        else:
            _init_nilesoft_font()
            self.icon_circle.set_pixmap(get_font_icon(0xE0EB, ic_sz * 2, '#ffffff').pixmap(ic_sz, ic_sz))

        main_lay.addWidget(self.icon_circle, 0, Qt.AlignVCenter)

        # Center Details
        center_lay = QVBoxLayout()
        center_lay.setContentsMargins(0, 0, 0, 0)
        center_lay.setSpacing(4)
        center_lay.setAlignment(Qt.AlignVCenter)

        flags = extract_snippet_flags(self.snippet_data)
        item_title = self.snippet_data.get("title") or self.snippet_data.get("name", "Snippet")

        if self.view_mode == "list":
            top_line = QHBoxLayout()
            top_line.setSpacing(6)
            top_line.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

            title_lbl = QLabel(item_title)
            title_lbl.setFont(QFont("Google Sans", 10, QFont.Bold))
            title_lbl.setStyleSheet("color: #ffffff; background: transparent;")
            top_line.addWidget(title_lbl)

            for f_kind, f_text, f_color in flags[:3]:
                top_line.addWidget(AntialiasedTag(f_text, f_color, parent=self))

            top_line.addStretch(1)
            center_lay.addLayout(top_line)

            desc_text = self.snippet_data.get("description", "")
            if len(desc_text) > 95:
                desc_text = desc_text[:92] + "..."
            desc_lbl = QLabel(desc_text)
            desc_lbl.setFont(QFont("Google Sans", 8))
            desc_lbl.setStyleSheet("color: #8c92a4; background: transparent;")
            center_lay.addWidget(desc_lbl)
        else:
            top_row = QHBoxLayout()
            top_row.setSpacing(6)
            top_row.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

            title_lbl = QLabel(item_title)
            title_lbl.setFont(QFont("Google Sans", 11, QFont.Bold))
            title_lbl.setStyleSheet("color: #ffffff; background: transparent;")
            top_row.addWidget(title_lbl)

            cat = self.snippet_data.get("category", "")
            if cat:
                top_row.addWidget(AntialiasedTag(cat, "#8caaee", parent=self))

            top_row.addStretch(1)
            center_lay.addLayout(top_row)

            flags_row = QHBoxLayout()
            flags_row.setSpacing(5)
            flags_row.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            for f_kind, f_text, f_color in flags:
                if f_kind == "category":
                    continue
                flags_row.addWidget(AntialiasedTag(f_text, f_color, parent=self))
            flags_row.addStretch(1)
            center_lay.addLayout(flags_row)

            desc_text = self.snippet_data.get("description", "")
            if len(desc_text) > 85:
                desc_text = desc_text[:82] + "..."
            desc_lbl = QLabel(desc_text)
            desc_lbl.setFont(QFont("Google Sans", 8))
            desc_lbl.setStyleSheet("color: #8c92a4; background: transparent;")
            center_lay.addWidget(desc_lbl)

        main_lay.addLayout(center_lay, 1)

        # Right Action Buttons
        actions_lay = QHBoxLayout()
        actions_lay.setSpacing(6)
        actions_lay.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        if self.is_customized:
            self.restore_btn = AntialiasedCircleButton("\uE094", tooltip="Restore to Curated Default", size=30, accent=True, parent=self)
            self.restore_btn.clicked.connect(lambda: self.restore_requested.emit(self.snippet_id))
            actions_lay.addWidget(self.restore_btn)

        self.edit_btn = AntialiasedCircleButton("\uE104", tooltip="Edit item in-place (name, icon, pos, properties)", size=30, parent=self)
        self.edit_btn.clicked.connect(lambda: self.edit_requested.emit(self.snippet_id))
        actions_lay.addWidget(self.edit_btn)

        if self.status == "full":
            self.action_btn = PillPushButton("✓ Added", "yes", height=28, parent=self)
            self.action_btn.setFixedWidth(80)
            self.action_btn.setToolTip("Click to remove from items.nss")
            self.action_btn.clicked.connect(lambda: self.toggle_requested.emit(self.snippet_id, False))
        else:
            self.action_btn = PillPushButton("＋ Add", "primary", height=28, parent=self)
            self.action_btn.setFixedWidth(74)
            self.action_btn.setToolTip("Add item to imports/items.nss")
            self.action_btn.clicked.connect(lambda: self.toggle_requested.emit(self.snippet_id, True))
        actions_lay.addWidget(self.action_btn)

        main_lay.addLayout(actions_lay)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            elems = self.snippet_data.get("elements", [])
            if len(elems) > 1:
                self.clicked.emit(self.snippet_id)
        super().mousePressEvent(event)


class ItemRowCard(QFrame):
    """Row card for an individual item inside a snippet/menu with added/unadded visual states."""
    add_toggle_requested = pyqtSignal(str, bool)  # elem_id, is_adding
    edit_requested = pyqtSignal(dict)  # element_dict

    def __init__(self, element_data, is_installed, parent_menu_title=None, parent=None):
        super().__init__(parent)
        self.elem_data = element_data
        self.elem_id = element_data["id"]
        self.is_installed = is_installed
        self.parent_menu_title = parent_menu_title

        self.setObjectName("itemRowCard")
        self.setFocusPolicy(Qt.NoFocus)
        self.setFixedHeight(54)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._update_appearance()
        self._setup_ui()

    def _update_appearance(self):
        if self.is_installed:
            self.setStyleSheet("""
                QFrame#itemRowCard {
                    background-color: rgba(166, 209, 137, 0.07);
                    border: 1px solid rgba(166, 209, 137, 0.35);
                    border-radius: 12px;
                    outline: none;
                }
                QFrame#itemRowCard:hover {
                    background-color: rgba(166, 209, 137, 0.12);
                    border: 1px solid #a6d189;
                }
                QFrame#itemRowCard QLabel, QLabel {
                    outline: none;
                    border: none;
                }
            """)
            self.setGraphicsEffect(None)
        else:
            self.setStyleSheet("""
                QFrame#itemRowCard {
                    background-color: rgba(255, 255, 255, 0.02);
                    border: 1px solid rgba(255, 255, 255, 0.05);
                    border-radius: 12px;
                    outline: none;
                }
                QFrame#itemRowCard:hover {
                    background-color: rgba(255, 255, 255, 0.05);
                    border: 1px solid rgba(255, 255, 255, 0.15);
                }
                QFrame#itemRowCard QLabel, QLabel {
                    outline: none;
                    border: none;
                }
            """)
            # Subtle dimming for not added items: readable yet distinct
            opacity = QGraphicsOpacityEffect(self)
            opacity.setOpacity(0.65)
            self.setGraphicsEffect(opacity)

    def _setup_ui(self):
        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 6, 10, 6)
        lay.setSpacing(10)

        # Left Icon Preview
        self.icon_lbl = QLabel()
        self.icon_lbl.setFocusPolicy(Qt.NoFocus)
        self.icon_lbl.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.icon_lbl.setTextInteractionFlags(Qt.NoTextInteraction)
        self.icon_lbl.setFixedSize(30, 30)
        self.icon_lbl.setAlignment(Qt.AlignCenter)
        self.icon_lbl.setStyleSheet("background: rgba(255,255,255,0.04); border-radius: 15px; border: 1px solid rgba(255,255,255,0.06); outline: none;")

        raw_icon = self.elem_data.get("icon")
        pix = render_nss_asset_pixmap(raw_icon, 18) if raw_icon else None
        if pix and not pix.isNull():
            self.icon_lbl.setPixmap(pix)
        else:
            glyph = 0xE15C if self.elem_data.get("type") == "menu" else 0xE710
            self.icon_lbl.setPixmap(get_mdl2_icon(glyph, 16, "#8caaee" if self.is_installed else "#737994").pixmap(16, 16))

        lay.addWidget(self.icon_lbl)

        # Middle Info
        mid_lay = QVBoxLayout()
        mid_lay.setContentsMargins(0, 0, 0, 0)
        mid_lay.setSpacing(2)
        mid_lay.setAlignment(Qt.AlignVCenter)

        top_r = QHBoxLayout()
        top_r.setSpacing(6)
        top_r.setAlignment(Qt.AlignLeft)

        title_text = self.elem_data.get("title", "Item")
        self.title_lbl = QLabel(title_text)
        self.title_lbl.setFocusPolicy(Qt.NoFocus)
        self.title_lbl.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.title_lbl.setTextInteractionFlags(Qt.NoTextInteraction)
        self.title_lbl.setFont(QFont("Google Sans", 10, QFont.Bold))
        self.title_lbl.setStyleSheet("color: #ffffff; background: transparent; border: none; outline: none;" if self.is_installed else "color: #b5bfe2; background: transparent; border: none; outline: none;")
        top_r.addWidget(self.title_lbl)

        # Key badge if present
        key = self.elem_data.get("key")
        if key:
            k_badge = QLabel(key)
            k_badge.setFocusPolicy(Qt.NoFocus)
            k_badge.setAttribute(Qt.WA_TransparentForMouseEvents, True)
            k_badge.setTextInteractionFlags(Qt.NoTextInteraction)
            k_badge.setFont(QFont("Google Sans", 8, QFont.Bold))
            k_badge.setStyleSheet("background: rgba(255,255,255,0.08); color: #e5c890; border-radius: 6px; padding: 0 5px; border: none; outline: none;")
            top_r.addWidget(k_badge)

        top_r.addStretch(1)
        mid_lay.addLayout(top_r)

        # Subtext: Tip or Command preview
        sub_text = self.elem_data.get("tip") or self.elem_data.get("cmd") or ""
        if len(sub_text) > 85:
            sub_text = sub_text[:82] + "..."
        sub_lbl = QLabel(sub_text)
        sub_lbl.setFocusPolicy(Qt.NoFocus)
        sub_lbl.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        sub_lbl.setTextInteractionFlags(Qt.NoTextInteraction)
        sub_lbl.setFont(QFont("Google Sans", 8))
        sub_lbl.setStyleSheet("color: #a5adce; background: transparent; border: none; outline: none;" if self.is_installed else "color: #626880; background: transparent; border: none; outline: none;")
        mid_lay.addWidget(sub_lbl)

        lay.addLayout(mid_lay, 1)

        # Right Action Buttons
        actions_lay = QHBoxLayout()
        actions_lay.setSpacing(8)
        actions_lay.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        # Edit button - circular button matching Edit tab on items lists
        self.edit_btn = QPushButton("\uE104")
        self.edit_btn.setFixedSize(28, 28)
        self.edit_btn.setCursor(Qt.PointingHandCursor)
        self.edit_btn.setFocusPolicy(Qt.NoFocus)
        self.edit_btn.setToolTip("Edit Item")
        self.edit_btn.setFont(QFont("Segoe MDL2 Assets", 11))
        self.edit_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.04);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 14px;
                color: #e78284;
                outline: none;
            }
            QPushButton:hover {
                background: #e78284;
                color: #ffffff;
                border: 1px solid #e78284;
            }
        """)
        self.edit_btn.clicked.connect(lambda: self.edit_requested.emit(self.elem_data))
        actions_lay.addWidget(self.edit_btn)

        # Toggle Add / Remove Button
        if self.is_installed:
            self.toggle_btn = QPushButton("✓ Added")
            self.toggle_btn.setFixedSize(68, 26)
            self.toggle_btn.setCursor(Qt.PointingHandCursor)
            self.toggle_btn.setFocusPolicy(Qt.NoFocus)
            self.toggle_btn.setFont(QFont("Google Sans", 8, QFont.Bold))
            self.toggle_btn.setStyleSheet("""
                QPushButton {
                    background: rgba(166, 209, 137, 0.2);
                    border: 1px solid #a6d189;
                    border-radius: 13px;
                    color: #a6d189;
                    outline: none;
                }
                QPushButton:hover {
                    background: rgba(231, 130, 132, 0.2);
                    border: 1px solid #e78284;
                    color: #e78284;
                }
            """)
            self.toggle_btn.setToolTip("Click to remove this item")
            self.toggle_btn.clicked.connect(lambda: self.add_toggle_requested.emit(self.elem_id, False))
        else:
            self.toggle_btn = QPushButton("+ Add")
            self.toggle_btn.setFixedSize(60, 26)
            self.toggle_btn.setCursor(Qt.PointingHandCursor)
            self.toggle_btn.setFocusPolicy(Qt.NoFocus)
            self.toggle_btn.setFont(QFont("Google Sans", 8, QFont.Bold))
            self.toggle_btn.setStyleSheet("""
                QPushButton {
                    background: #e78284;
                    border: none;
                    border-radius: 13px;
                    color: #18181c;
                    outline: none;
                }
                QPushButton:hover {
                    background: #ea999c;
                }
            """)
            self.toggle_btn.clicked.connect(lambda: self.add_toggle_requested.emit(self.elem_id, True))

        actions_lay.addWidget(self.toggle_btn)
        lay.addLayout(actions_lay)


class MenuBlockCard(QFrame):
    """Container card for a Menu block with its header and indented child items."""
    add_menu_requested = pyqtSignal(str, bool)  # menu_elem_id, is_adding
    item_toggle_requested = pyqtSignal(str, bool)  # elem_id, is_adding
    item_edit_requested = pyqtSignal(dict)
    menu_edit_requested = pyqtSignal(dict)

    def __init__(self, menu_data, is_menu_installed, items_installed_map, parent=None):
        super().__init__(parent)
        self.menu_data = menu_data
        self.menu_id = menu_data["id"]
        self.is_menu_installed = is_menu_installed
        self.items_installed_map = items_installed_map

        self.setObjectName("menuBlockCard")
        self.setFocusPolicy(Qt.NoFocus)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.setStyleSheet("""
            QFrame#menuBlockCard {
                background: rgba(255, 255, 255, 0.025);
                border: 1px solid rgba(255, 255, 255, 0.07);
                border-radius: 16px;
                outline: none;
            }
            QFrame#menuBlockCard QLabel, QLabel {
                outline: none;
                border: none;
            }
        """)

        self._setup_ui()

    def _setup_ui(self):
        main_lay = QVBoxLayout(self)
        main_lay.setContentsMargins(12, 10, 12, 12)
        main_lay.setSpacing(8)

        # Header Row
        header_frame = QFrame()
        header_frame.setFocusPolicy(Qt.NoFocus)
        header_frame.setStyleSheet("background: transparent; border: none; outline: none;")
        h_lay = QHBoxLayout(header_frame)
        h_lay.setContentsMargins(4, 2, 4, 2)
        h_lay.setSpacing(10)

        # Menu Icon
        icon_lbl = QLabel()
        icon_lbl.setFocusPolicy(Qt.NoFocus)
        icon_lbl.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        icon_lbl.setTextInteractionFlags(Qt.NoTextInteraction)
        icon_lbl.setFixedSize(30, 30)
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setStyleSheet("background: rgba(202, 158, 230, 0.15); border-radius: 15px; border: 1px solid rgba(202, 158, 230, 0.3); outline: none;")
        raw_icon = self.menu_data.get("icon")
        pix = render_nss_asset_pixmap(raw_icon, 18) if raw_icon else None
        if pix and not pix.isNull():
            icon_lbl.setPixmap(pix)
        else:
            icon_lbl.setPixmap(get_mdl2_icon(0xE15C, 18, "#ca9ee6").pixmap(18, 18))
        h_lay.addWidget(icon_lbl)

        # Menu Title & details
        t_lay = QVBoxLayout()
        t_lay.setSpacing(1)
        m_title = self.menu_data.get("title", "Menu")
        title_lbl = QLabel(f"📁 Menu: {m_title}")
        title_lbl.setFocusPolicy(Qt.NoFocus)
        title_lbl.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        title_lbl.setTextInteractionFlags(Qt.NoTextInteraction)
        title_lbl.setFont(QFont("Google Sans", 11, QFont.Bold))
        title_lbl.setStyleSheet("color: #ca9ee6; background: transparent; border: none; outline: none;")
        t_lay.addWidget(title_lbl)

        children_count = len(self.menu_data.get("children", []))
        tip_text = self.menu_data.get("tip") or f"Submenu containing {children_count} items"
        desc_lbl = QLabel(tip_text)
        desc_lbl.setFocusPolicy(Qt.NoFocus)
        desc_lbl.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        desc_lbl.setTextInteractionFlags(Qt.NoTextInteraction)
        desc_lbl.setFont(QFont("Google Sans", 8))
        desc_lbl.setStyleSheet("color: #8c92a4; background: transparent; border: none; outline: none;")
        t_lay.addWidget(desc_lbl)

        h_lay.addLayout(t_lay, 1)

        # Edit Menu Button - circular button matching Edit tab on items lists
        self.edit_btn = QPushButton("\uE104")
        self.edit_btn.setFixedSize(28, 28)
        self.edit_btn.setCursor(Qt.PointingHandCursor)
        self.edit_btn.setFocusPolicy(Qt.NoFocus)
        self.edit_btn.setToolTip("Edit Menu")
        self.edit_btn.setFont(QFont("Segoe MDL2 Assets", 11))
        self.edit_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.04);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 14px;
                color: #e78284;
                outline: none;
            }
            QPushButton:hover {
                background: #e78284;
                color: #ffffff;
                border: 1px solid #e78284;
            }
        """)
        self.edit_btn.clicked.connect(lambda: self.menu_edit_requested.emit(self.menu_data))
        h_lay.addWidget(self.edit_btn)

        # Add / Remove Entire Menu Button
        if self.is_menu_installed:
            menu_btn = PillPushButton("✓ Menu Added", "secondary", height=28)
            menu_btn.setFixedWidth(105)
            menu_btn.setFocusPolicy(Qt.NoFocus)
            menu_btn.setStyleSheet("""
                background: rgba(166, 209, 137, 0.2);
                border: 1px solid #a6d189;
                color: #a6d189;
                font-weight: bold;
                border-radius: 14px;
                outline: none;
            """)
            menu_btn.setToolTip("Click to remove this menu and all its items")
            menu_btn.clicked.connect(lambda: self.add_menu_requested.emit(self.menu_id, False))
        else:
            menu_btn = PillPushButton("+ Add Menu", "primary", height=28)
            menu_btn.setFixedWidth(95)
            menu_btn.setFocusPolicy(Qt.NoFocus)
            menu_btn.clicked.connect(lambda: self.add_menu_requested.emit(self.menu_id, True))

        h_lay.addWidget(menu_btn)
        main_lay.addWidget(header_frame)

        # Indented Child Items Container
        children_box = QFrame()
        children_box.setFocusPolicy(Qt.NoFocus)
        children_box.setStyleSheet("background: transparent; border: none; outline: none;")
        cb_lay = QVBoxLayout(children_box)
        cb_lay.setContentsMargins(14, 0, 0, 0)
        cb_lay.setSpacing(6)

        for child in self.menu_data.get("children", []):
            c_type = child.get("type", "").lower()
            if c_type == "separator":
                sep = QFrame()
                sep.setFixedHeight(1)
                sep.setStyleSheet("background: rgba(255, 255, 255, 0.08); margin: 3px 10px; border: none; outline: none;")
                cb_lay.addWidget(sep)
                continue

            child_installed = self.items_installed_map.get(child["id"], False)
            row = ItemRowCard(child, child_installed, parent_menu_title=m_title)
            row.add_toggle_requested.connect(self.item_toggle_requested.emit)
            row.edit_requested.connect(self.item_edit_requested.emit)
            cb_lay.addWidget(row)

        main_lay.addWidget(children_box)


class ItemQuickEditDialog(ModernDialog):
    """Quick edit modal for customizing title, icon, command, args, and tips before/after adding."""
    def __init__(self, elem_data, parent=None):
        super().__init__(parent, title="Edit Item", width=560, height=520)
        self.elem_data = elem_data
        self.result_code = None

        self._setup_content()

    def _setup_content(self):
        container = QWidget()
        lay = QVBoxLayout(container)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(14)

        # Title Row
        t_lbl = QLabel("Item Title")
        t_lbl.setFont(QFont("Google Sans", 9, QFont.Bold))
        t_lbl.setStyleSheet("color: #c6d0f5; background: transparent;")
        lay.addWidget(t_lbl)

        self.title_input = PillLineEdit(self.elem_data.get("title", ""))
        lay.addWidget(self.title_input)

        # Icon Row with live preview
        i_lbl = QLabel("Icon / Glyph (e.g. \\uE100 or icon.rename or shell32.dll,3)")
        i_lbl.setFont(QFont("Google Sans", 9, QFont.Bold))
        i_lbl.setStyleSheet("color: #c6d0f5; background: transparent;")
        lay.addWidget(i_lbl)

        icon_row = QHBoxLayout()
        icon_row.setSpacing(8)

        self.icon_preview = QLabel()
        self.icon_preview.setFixedSize(36, 36)
        self.icon_preview.setAlignment(Qt.AlignCenter)
        self.icon_preview.setStyleSheet("background: rgba(255,255,255,0.06); border-radius: 18px; border: 1px solid rgba(255,255,255,0.1);")
        self._update_icon_preview(self.elem_data.get("icon", ""))
        icon_row.addWidget(self.icon_preview)

        self.icon_input = PillLineEdit(self.elem_data.get("icon", ""))
        self.icon_input.textChanged.connect(self._update_icon_preview)
        icon_row.addWidget(self.icon_input, 1)
        lay.addLayout(icon_row)

        # Tip / Description Row
        tip_lbl = QLabel("Tooltip / Description")
        tip_lbl.setFont(QFont("Google Sans", 9, QFont.Bold))
        tip_lbl.setStyleSheet("color: #c6d0f5; background: transparent;")
        lay.addWidget(tip_lbl)

        self.tip_input = PillLineEdit(self.elem_data.get("tip", ""))
        lay.addWidget(self.tip_input)

        # Command & Args
        c_lbl = QLabel("Command (cmd)")
        c_lbl.setFont(QFont("Google Sans", 9, QFont.Bold))
        c_lbl.setStyleSheet("color: #c6d0f5; background: transparent;")
        lay.addWidget(c_lbl)

        self.cmd_input = PillLineEdit(self.elem_data.get("cmd", ""))
        lay.addWidget(self.cmd_input)

        a_lbl = QLabel("Arguments (args)")
        a_lbl.setFont(QFont("Google Sans", 9, QFont.Bold))
        a_lbl.setStyleSheet("color: #c6d0f5; background: transparent;")
        lay.addWidget(a_lbl)

        self.args_input = PillLineEdit(self.elem_data.get("args", ""))
        lay.addWidget(self.args_input)

        lay.addStretch(1)

        # Bottom Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        btn_row.addStretch(1)

        cancel_btn = PillPushButton("Cancel", "secondary", height=32)
        cancel_btn.setFixedWidth(80)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        save_btn = PillPushButton("Save Changes", "primary", height=32)
        save_btn.setFixedWidth(110)
        save_btn.clicked.connect(self._on_save)
        btn_row.addWidget(save_btn)

        lay.addLayout(btn_row)
        self.main_layout.addWidget(container)

    def _update_icon_preview(self, text):
        pix = render_nss_asset_pixmap(text.strip(), 20)
        if pix and not pix.isNull():
            self.icon_preview.setPixmap(pix)
        else:
            self.icon_preview.setPixmap(get_mdl2_icon(0xE710, 18, "#8caaee").pixmap(18, 18))

    def _on_save(self):
        new_title = self.title_input.text().strip()
        new_icon = self.icon_input.text().strip()
        new_tip = self.tip_input.text().strip()
        new_cmd = self.cmd_input.text().strip()
        new_args = self.args_input.text().strip()

        # Build clean NSS item statement
        props = []
        if new_title:
            props.append(f"title='{new_title}'")
        if new_icon:
            props.append(f"image={new_icon}")
        if new_tip:
            props.append(f"tip='{new_tip}'")
        if new_cmd:
            props.append(f"cmd='{new_cmd}'")
        if new_args:
            props.append(f"args='{new_args}'")

        raw_existing = self.elem_data.get("raw_code", "")
        # Preserve keys or where clauses from original if present
        for attr in ("keys", "where", "admin", "type", "vis"):
            m = re.search(rf'\b({attr}\s*=\s*[^ \t\r\n)]+)', raw_existing)
            if m and not any(p.startswith(f"{attr}=") for p in props):
                props.append(m.group(1))

        self.result_code = f"item({', '.join(props)})"
        self.accept()


class SnippetDiffDialog(ModernDialog):
    """Before > After diff modal showing changes between installed code and latest store update."""
    apply_requested = pyqtSignal()

    def __init__(self, snippet_name, installed_code, store_code, parent=None):
        super().__init__(parent, title=f"Update: {snippet_name}", width=740, height=600)
        self.installed_code = installed_code
        self.store_code = store_code

        self._setup_content()

    def _setup_content(self):
        container = QWidget()
        lay = QVBoxLayout(container)
        lay.setContentsMargins(20, 16, 20, 16)
        lay.setSpacing(12)

        info_lbl = QLabel("Review the changes below before updating this snippet in <b>items.nss</b>.")
        info_lbl.setFont(QFont("Google Sans", 10))
        info_lbl.setStyleSheet("color: #a5adce; background: transparent;")
        lay.addWidget(info_lbl)

        # Diff View Box
        diff_text_edit = QTextEdit()
        diff_text_edit.setReadOnly(True)
        diff_text_edit.setFont(QFont("Consolas", 10))
        diff_text_edit.setStyleSheet("""
            QTextEdit {
                background: #141416;
                color: #c6d0f5;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 12px;
                padding: 10px;
            }
        """)

        # Generate unified HTML diff
        diff_lines = list(difflib.unified_diff(
            self.installed_code.splitlines(),
            self.store_code.splitlines(),
            fromfile="Installed (Current)",
            tofile="Store (New)",
            lineterm=""
        ))

        html = []
        for line in diff_lines:
            escaped = line.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            if line.startswith('+') and not line.startswith('+++'):
                html.append(f"<span style='color: #a6d189; background: rgba(166,209,137,0.1);'>{escaped}</span>")
            elif line.startswith('-') and not line.startswith('---'):
                html.append(f"<span style='color: #e78284; background: rgba(231,130,132,0.1);'>{escaped}</span>")
            elif line.startswith('@@'):
                html.append(f"<span style='color: #8caaee;'>{escaped}</span>")
            else:
                html.append(f"<span style='color: #737994;'>{escaped}</span>")

        diff_text_edit.setHtml("<pre style='margin:0;'>" + "<br>".join(html) + "</pre>")
        lay.addWidget(diff_text_edit, 1)

        # Bottom Actions
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        btn_row.addStretch(1)

        keep_btn = PillPushButton("Keep Current", "secondary", height=32)
        keep_btn.setFixedWidth(110)
        keep_btn.clicked.connect(self.reject)
        btn_row.addWidget(keep_btn)

        apply_btn = PillPushButton("Apply Update", "primary", height=32)
        apply_btn.setFixedWidth(120)
        apply_btn.setStyleSheet("background: #e5c890; color: #18181c; font-weight: bold; border-radius: 16px;")
        apply_btn.clicked.connect(self._on_apply)
        btn_row.addWidget(apply_btn)

        lay.addLayout(btn_row)
        self.main_layout.addWidget(container)

    def _on_apply(self):
        self.apply_requested.emit()
        self.accept()


class SnippetDetailView(QWidget):
    """Drill-down explorer showing all nested menus and items with individual add/remove toggles."""
    back_requested = pyqtSignal()
    item_modified = pyqtSignal()

    def __init__(self, manager, parent=None):
        super().__init__(parent)
        self.manager = manager
        self.snippet_id = None
        self.snippet_data = None

        self._setup_ui()

    def _setup_ui(self):
        self.main_lay = QVBoxLayout(self)
        self.main_lay.setContentsMargins(14, 10, 14, 14)
        self.main_lay.setSpacing(12)

        # Top Navigation Header
        top_bar = QHBoxLayout()
        top_bar.setSpacing(10)

        self.back_btn = PillPushButton("← Back to Items", "secondary", height=30)
        self.back_btn.setFixedWidth(125)
        self.back_btn.setFocusPolicy(Qt.NoFocus)
        self.back_btn.clicked.connect(self.back_requested.emit)
        top_bar.addWidget(self.back_btn)

        top_bar.addStretch(1)

        self.add_all_btn = PillPushButton("+ Add All", "primary", height=30)
        self.add_all_btn.setFixedWidth(95)
        self.add_all_btn.setFocusPolicy(Qt.NoFocus)
        self.add_all_btn.clicked.connect(self._on_add_all)
        top_bar.addWidget(self.add_all_btn)

        self.remove_all_btn = PillPushButton("✕ Remove All", "secondary", height=30)
        self.remove_all_btn.setFixedWidth(105)
        self.remove_all_btn.setFocusPolicy(Qt.NoFocus)
        self.remove_all_btn.setStyleSheet("""
            QPushButton {
                background: rgba(231, 130, 132, 0.15);
                border: 1px solid #e78284;
                border-radius: 15px;
                color: #e78284;
                font-weight: bold;
                outline: none;
            }
            QPushButton:hover {
                background: rgba(231, 130, 132, 0.3);
            }
        """)
        self.remove_all_btn.clicked.connect(self._on_remove_all)
        top_bar.addWidget(self.remove_all_btn)

        self.update_btn = PillPushButton("⚡ Update", "primary", height=30)
        self.update_btn.setFixedWidth(90)
        self.update_btn.setFocusPolicy(Qt.NoFocus)
        self.update_btn.setStyleSheet("background: #e5c890; color: #18181c; font-weight: bold; border-radius: 15px; outline: none;")
        self.update_btn.clicked.connect(self._on_show_update_diff)
        self.update_btn.hide()
        top_bar.addWidget(self.update_btn)

        self.preview_code_btn = PillPushButton("▶ Code Preview", "secondary", height=30)
        self.preview_code_btn.setFixedWidth(115)
        self.preview_code_btn.setFocusPolicy(Qt.NoFocus)
        self.preview_code_btn.clicked.connect(self._toggle_raw_code)
        top_bar.addWidget(self.preview_code_btn)

        self.main_lay.addLayout(top_bar)

        # Snippet Info Header Banner
        self.banner = QFrame()
        self.banner.setFocusPolicy(Qt.NoFocus)
        self.banner.setStyleSheet("""
            QFrame {
                background: rgba(255, 255, 255, 0.035);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 14px;
                outline: none;
            }
            QFrame QLabel, QLabel {
                outline: none;
                border: none;
            }
        """)
        b_lay = QHBoxLayout(self.banner)
        b_lay.setContentsMargins(14, 12, 14, 12)
        b_lay.setSpacing(12)

        self.banner_icon = QLabel()
        self.banner_icon.setFocusPolicy(Qt.NoFocus)
        self.banner_icon.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.banner_icon.setTextInteractionFlags(Qt.NoTextInteraction)
        self.banner_icon.setFixedSize(36, 36)
        self.banner_icon.setAlignment(Qt.AlignCenter)
        self.banner_icon.setStyleSheet("background: rgba(255,255,255,0.05); border-radius: 18px; outline: none; border: none;")
        b_lay.addWidget(self.banner_icon)

        b_mid = QVBoxLayout()
        b_mid.setSpacing(2)
        self.banner_title = QLabel("Snippet Title")
        self.banner_title.setFocusPolicy(Qt.NoFocus)
        self.banner_title.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.banner_title.setTextInteractionFlags(Qt.NoTextInteraction)
        self.banner_title.setFont(QFont("Google Sans", 13, QFont.Bold))
        self.banner_title.setStyleSheet("color: #ffffff; background: transparent; outline: none; border: none;")
        b_mid.addWidget(self.banner_title)

        self.banner_desc = QLabel("Description")
        self.banner_desc.setFocusPolicy(Qt.NoFocus)
        self.banner_desc.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.banner_desc.setTextInteractionFlags(Qt.NoTextInteraction)
        self.banner_desc.setFont(QFont("Google Sans", 9))
        self.banner_desc.setStyleSheet("color: #a5adce; background: transparent; outline: none; border: none;")
        self.banner_desc.setWordWrap(True)
        b_mid.addWidget(self.banner_desc)

        b_lay.addLayout(b_mid, 1)
        self.main_lay.addWidget(self.banner)

        # Collapsible Code Preview Box
        self.code_box = QTextEdit()
        self.code_box.setReadOnly(True)
        self.code_box.setFont(QFont("Consolas", 10))
        self.code_box.setFixedHeight(140)
        self.code_box.setStyleSheet("""
            QTextEdit {
                background: #141416;
                color: #c6d0f5;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 10px;
                padding: 8px;
                outline: none;
            }
        """)
        self.code_box.hide()
        self.main_lay.addWidget(self.code_box)

        # Scroll Area for Nested Hierarchy
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setStyleSheet("QScrollArea { border: none; background: transparent; outline: none; }")
        self.scroll_content = QWidget()
        self.scroll_content.setStyleSheet("background: transparent; outline: none;")
        self.content_lay = QVBoxLayout(self.scroll_content)
        self.content_lay.setContentsMargins(0, 0, 4, 10)
        self.content_lay.setSpacing(10)
        self.content_lay.setAlignment(Qt.AlignTop)

        self.scroll.setWidget(self.scroll_content)
        self.main_lay.addWidget(self.scroll, 1)

    def load_snippet(self, snippet_id):
        self.snippet_id = snippet_id
        self.snippet_data = self.manager.get_snippet(snippet_id)
        if not self.snippet_data:
            return

        # Update Banner
        self.banner_title.setText(self.snippet_data.get("name", snippet_id))
        self.banner_desc.setText(self.snippet_data.get("description", ""))
        raw_icon = self.snippet_data.get("icon")
        pix = render_nss_asset_pixmap(raw_icon, 20)
        if pix and not pix.isNull():
            self.banner_icon.setPixmap(pix)
        else:
            self.banner_icon.setPixmap(get_mdl2_icon(0xE71D, 20, "#e78284").pixmap(20, 20))

        self.code_box.setPlainText(self.snippet_data.get("full_code", ""))

        # Update action buttons state
        self._refresh_hierarchy()

    def _refresh_hierarchy(self):
        # Clear existing rows cleanly and immediately detach from visual tree
        while self.content_lay.count():
            it = self.content_lay.takeAt(0)
            w = it.widget()
            if w:
                w.setParent(None)
                w.deleteLater()

        if not self.snippet_data:
            return

        status = self.manager.is_snippet_installed(self.snippet_id)
        has_update = self.manager.has_snippet_update(self.snippet_id)

        self.update_btn.setVisible(has_update)
        self.remove_all_btn.setVisible(status in ("full", "partial"))
        if status == "full":
            self.add_all_btn.setText("✓ All Added")
            self.add_all_btn.setStyleSheet("background: rgba(166, 209, 137, 0.2); border: 1px solid #a6d189; color: #a6d189; border-radius: 15px; font-weight: bold; outline: none;")
        else:
            self.add_all_btn.setText("+ Add All")
            self.add_all_btn.setStyleSheet("""
                QPushButton {
                    background: #e78284;
                    color: #18181c;
                    border: none;
                    border-radius: 15px;
                    font-weight: bold;
                    outline: none;
                }
                QPushButton:hover {
                    background: #ea999c;
                }
            """)

        # Map installed state for all elements
        all_flattened = self.manager._flatten_elements(self.snippet_data.get("elements", []))
        installed_map = {el["id"]: self.manager.is_element_installed(el["id"]) for el in all_flattened}

        elements = self.snippet_data.get("elements", [])
        for el in elements:
            el_type = el.get("type", "").lower()
            if el_type == "menu":
                is_menu_inst = installed_map.get(el["id"], False)
                menu_card = MenuBlockCard(el, is_menu_inst, installed_map)
                menu_card.add_menu_requested.connect(self._on_menu_toggle)
                menu_card.item_toggle_requested.connect(self._on_item_toggle)
                menu_card.item_edit_requested.connect(self._on_item_edit)
                menu_card.menu_edit_requested.connect(self._on_item_edit)
                self.content_lay.addWidget(menu_card)
            elif el_type == "separator":
                sep = QFrame()
                sep.setFixedHeight(1)
                sep.setStyleSheet("background: rgba(255, 255, 255, 0.08); margin: 4px 0; border: none; outline: none;")
                self.content_lay.addWidget(sep)
            else:
                # Standalone root item
                is_inst = installed_map.get(el["id"], False)
                row = ItemRowCard(el, is_inst)
                row.add_toggle_requested.connect(self._on_item_toggle)
                row.edit_requested.connect(self._on_item_edit)
                self.content_lay.addWidget(row)

    def _toggle_raw_code(self):
        if self.code_box.isVisible():
            self.code_box.hide()
            self.preview_code_btn.setText("▶ Code Preview")
        else:
            self.code_box.show()
            self.preview_code_btn.setText("▲ Hide Code")

    def _on_add_all(self):
        if self.snippet_id:
            self.manager.add_snippet(self.snippet_id)
            self._refresh_hierarchy()
            self.item_modified.emit()

    def _on_remove_all(self):
        if self.snippet_id:
            self.manager.remove_snippet(self.snippet_id)
            self._refresh_hierarchy()
            self.item_modified.emit()

    def _on_menu_toggle(self, menu_id, is_adding):
        if is_adding:
            self.manager.add_menu(self.snippet_id, menu_id)
        else:
            self.manager.remove_menu(self.snippet_id, menu_id)
        self._refresh_hierarchy()
        self.item_modified.emit()

    def _on_item_toggle(self, elem_id, is_adding):
        if is_adding:
            self.manager.add_element(self.snippet_id, elem_id)
        else:
            self.manager.remove_element(self.snippet_id, elem_id)
        self._refresh_hierarchy()
        self.item_modified.emit()

    def _on_item_edit(self, elem_data):
        target_code = self.manager.installed_data.get("elements", {}).get(elem_data["id"], {}).get("code") or elem_data.get("raw_code", "").strip()
        parsed = find_items_and_menus(target_code) if target_code else []
        parsed_item = parsed[0] if parsed else {}
        props = parsed_item.get('props', {}).copy()

        if 'title' not in props and elem_data.get('title'):
            props['title'] = elem_data['title']
        if 'image' not in props and 'icon' not in props and elem_data.get('icon'):
            props['image'] = elem_data['icon']
        if 'cmd' not in props and elem_data.get('cmd'):
            props['cmd'] = elem_data['cmd']
        if 'args' not in props and elem_data.get('args'):
            props['args'] = elem_data['args']
        if 'tip' not in props and elem_data.get('tip'):
            props['tip'] = elem_data['tip']
        if 'type' not in props and elem_data.get('type_filter'):
            props['type'] = elem_data['type_filter']

        item_dict = {
            'type': elem_data.get('type', 'item'),
            'props': props,
            'file': self.manager.items_nss_path,
            'start': parsed_item.get('start', 0),
            'end': parsed_item.get('end', len(target_code)),
            'has_children': parsed_item.get('has_children', False),
            'raw_inner': parsed_item.get('raw_inner', '')
        }

        dlg = ImportEditorDialog(item_dict, parent=self)
        if dlg.exec_() == QDialog.Accepted:
            new_props = dlg.get_props()
            merged = props.copy()
            for k in list(merged.keys()):
                if k not in new_props and k not in ('_order', 'file', 'start', 'end', 'cmd', 'arg', 'args', 'where', 'mode', 'window', 'admin', 'keys', 'key', 'tip'):
                    del merged[k]
            for k, v in new_props.items():
                if v is None or v == 'None' or (k in ('vis', 'pos', 'type', 'menu') and not str(v).strip()):
                    if k in merged:
                        del merged[k]
                else:
                    merged[k] = v

            pts = []
            handled = set()
            orig_order = props.get('_order', [])
            for k in orig_order:
                if k in merged:
                    v = str(merged[k]).strip()
                    formatted = format_nss_value(k, v)
                    if formatted:
                        pts.append(formatted)
                    handled.add(k)
            for k, v in merged.items():
                if k not in handled and not k.startswith('_') and k not in ('file', 'start', 'end', 'cmd_end', 'has_children', 'raw_inner', 'indent'):
                    formatted = format_nss_value(k, str(v).strip())
                    if formatted:
                        pts.append(formatted)

            elem_type = elem_data.get('type', 'item')
            new_code = f"{elem_type}({', '.join(pts)})"
            if item_dict.get('raw_inner'):
                new_code += f" {item_dict['raw_inner']}"

            if elem_type == "menu":
                self.manager.add_menu(self.snippet_id, elem_data["id"], custom_code=new_code)
            else:
                self.manager.add_element(self.snippet_id, elem_data["id"], custom_code=new_code)

            self._refresh_hierarchy()
            self.item_modified.emit()

    def _on_show_update_diff(self):
        installed_code, store_code = self.manager.get_diff(self.snippet_id)
        name = self.snippet_data.get("name", self.snippet_id)
        diff_dlg = SnippetDiffDialog(name, installed_code, store_code, parent=self)
        diff_dlg.apply_requested.connect(lambda: self.manager.apply_update(self.snippet_id))
        if diff_dlg.exec_():
            self._refresh_hierarchy()
            self.item_modified.emit()


class ItemsWidget(QWidget):
    """Main Items Store & Manager page inside Plugins tab."""
    reload_requested = pyqtSignal()

    def __init__(self, project_root=None, parent=None):
        super().__init__(parent)
        self.project_root = project_root
        self.manager = ItemsManager.instance(project_root=project_root)

        self.current_category = "all"
        self.search_query = ""
        self.filter_installed_only = False
        self.view_mode = "grid"

        self._setup_ui()
        self.refresh_catalog()

    def _setup_ui(self):
        main_lay = QVBoxLayout(self)
        main_lay.setContentsMargins(0, 0, 0, 0)
        main_lay.setSpacing(0)

        # Stacked View: 0 = Gallery / List, 1 = Snippet Drill-down
        self.stacked_view = QStackedWidget()

        # Page 0: Gallery View
        self.gallery_page = QWidget()
        self.gallery_page.setObjectName("itemsGalleryPage")
        self.gallery_page.setStyleSheet("#itemsGalleryPage { background-color: transparent; }")
        gal_lay = QVBoxLayout(self.gallery_page)
        gal_lay.setContentsMargins(14, 4, 14, 10)
        gal_lay.setSpacing(10)

        # Top Bar: Search + Installed Filter Toggle + View Switcher + Count
        top_bar = QHBoxLayout()
        top_bar.setSpacing(10)

        self.search_input = PillLineEdit("Search curated items, commands, flags...")
        self.search_input.setFixedHeight(32)
        self.search_input.setMinimumWidth(260)
        self.search_input.textChanged.connect(self._on_search_changed)
        top_bar.addWidget(self.search_input, 1)

        # Installed only filter button
        self.installed_filter_btn = QPushButton("✓ Added")
        self.installed_filter_btn.setCheckable(True)
        self.installed_filter_btn.setFixedHeight(32)
        self.installed_filter_btn.setCursor(Qt.PointingHandCursor)
        self.installed_filter_btn.setFont(QFont("Google Sans", 9, QFont.Bold))
        self.installed_filter_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.04);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 16px;
                color: #a5adce;
                padding: 0 12px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.08);
                color: #c6d0f5;
            }
            QPushButton:checked {
                background: rgba(166, 209, 137, 0.2);
                border: 1px solid #a6d189;
                color: #a6d189;
            }
        """)
        self.installed_filter_btn.toggled.connect(self._on_installed_filter_toggled)
        top_bar.addWidget(self.installed_filter_btn)

        # View mode toggle container (Grid / List)
        self.view_container = QFrame()
        self.view_container.setStyleSheet("background: rgba(255, 255, 255, 0.04); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 16px;")
        v_lay = QHBoxLayout(self.view_container)
        v_lay.setContentsMargins(2, 2, 2, 2)
        v_lay.setSpacing(2)

        view_btn_css = """
            QPushButton {
                background: transparent;
                border: none;
                border-radius: 12px;
                color: #8c92a4;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.08);
                color: #ffffff;
            }
            QPushButton:checked {
                background: rgba(231, 130, 132, 0.25);
                color: #ea999c;
                border: 1px solid rgba(231, 130, 132, 0.4);
            }
        """

        self.grid_view_btn = QPushButton("\uE80A")
        self.grid_view_btn.setFixedSize(28, 28)
        self.grid_view_btn.setFont(QFont("Segoe MDL2 Assets", 10))
        self.grid_view_btn.setToolTip("Grid View")
        self.grid_view_btn.setCheckable(True)
        self.grid_view_btn.setChecked(True)
        self.grid_view_btn.setCursor(Qt.PointingHandCursor)
        self.grid_view_btn.setStyleSheet(view_btn_css)

        self.list_view_btn = QPushButton("\uE8FD")
        self.list_view_btn.setFixedSize(28, 28)
        self.list_view_btn.setFont(QFont("Segoe MDL2 Assets", 10))
        self.list_view_btn.setToolTip("List View")
        self.list_view_btn.setCheckable(True)
        self.list_view_btn.setCursor(Qt.PointingHandCursor)
        self.list_view_btn.setStyleSheet(view_btn_css)

        self.view_group = QButtonGroup(self)
        self.view_group.setExclusive(True)
        self.view_group.addButton(self.grid_view_btn)
        self.view_group.addButton(self.list_view_btn)

        self.grid_view_btn.clicked.connect(lambda: self._set_view_mode("grid"))
        self.list_view_btn.clicked.connect(lambda: self._set_view_mode("list"))

        v_lay.addWidget(self.grid_view_btn)
        v_lay.addWidget(self.list_view_btn)
        top_bar.addWidget(self.view_container)

        self.count_lbl = QLabel("0 Items")
        self.count_lbl.setFont(QFont("Google Sans", 9))
        self.count_lbl.setStyleSheet("color: #737994; background: transparent;")
        top_bar.addWidget(self.count_lbl)

        gal_lay.addLayout(top_bar)

        # Category Filter Pills Flow Layout
        self.cats_frame = QFrame()
        self.cats_frame.setStyleSheet("background: transparent; border: none;")
        self.cats_layout = FlowLayout(self.cats_frame, margin=0, spacing=6)

        # Add 'All' tag
        cat_colors = {
            "all": "#51576d",
            "developer": "#8caaee",
            "file tools": "#a6d189",
            "system": "#ca9ee6",
        }
        all_btn = CategoryFilterButton("All", color=cat_colors["all"])
        all_btn.setChecked(True)
        all_btn.clicked.connect(lambda: self._select_category("all", all_btn))
        self.cats_layout.addWidget(all_btn)
        self.cat_buttons = [all_btn]

        # Dynamic categories from catalog
        for group in self.manager.catalog.get("groups", []):
            g_name = group.get("name", "")
            g_id = group.get("id") or g_name
            c_btn = CategoryFilterButton(g_name, color=cat_colors.get(g_name.lower(), "#ef9f76"))
            c_btn.clicked.connect(lambda checked, gid=g_id, b=c_btn: self._select_category(gid, b))
            self.cats_layout.addWidget(c_btn)
            self.cat_buttons.append(c_btn)

        gal_lay.addWidget(self.cats_frame)

        # Snippets Grid Scroll Area
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self.scroll_content = QWidget()
        self.scroll_content.setStyleSheet("background: transparent;")
        self.grid_layout = QGridLayout(self.scroll_content)
        self.grid_layout.setContentsMargins(0, 4, 8, 12)
        self.grid_layout.setHorizontalSpacing(14)
        self.grid_layout.setVerticalSpacing(10)
        self.grid_layout.setAlignment(Qt.AlignTop)
        self.grid_layout.setColumnStretch(0, 1)
        self.grid_layout.setColumnStretch(1, 1)

        self.scroll.setWidget(self.scroll_content)
        gal_lay.addWidget(self.scroll, 1)

        self.stacked_view.addWidget(self.gallery_page)

        # Page 1: Snippet Detail View
        self.detail_view = SnippetDetailView(self.manager, self)
        self.detail_view.setObjectName("itemsDetailPage")
        self.detail_view.setStyleSheet("#itemsDetailPage { background-color: transparent; }")
        self.detail_view.back_requested.connect(self._on_back_to_gallery)
        self.detail_view.item_modified.connect(self._on_item_modified)
        self.stacked_view.addWidget(self.detail_view)

        main_lay.addWidget(self.stacked_view)

    def _set_view_mode(self, mode):
        if self.view_mode == mode:
            return
        self.view_mode = mode
        self.grid_view_btn.setChecked(mode == "grid")
        self.list_view_btn.setChecked(mode == "list")
        self._populate_cards()

    def refresh_catalog(self):
        """Reloads catalog and updates snippet cards."""
        self.manager.load_catalog()
        self.manager.load_installed()
        self._populate_cards()

    def refresh_installed_only(self):
        """Quickly updates installed states without re-reading catalog."""
        self.manager.load_installed()
        self._populate_cards()

    def _select_category(self, cat_id, button):
        for b in self.cat_buttons:
            b.setChecked(b == button)
        self.current_category = cat_id
        self._populate_cards()

    def _on_search_changed(self, text):
        self.search_query = text.strip().lower()
        self._populate_cards()

    def _on_installed_filter_toggled(self, checked):
        self.filter_installed_only = checked
        self._populate_cards()

    def showEvent(self, e):
        super().showEvent(e)
        if hasattr(self, 'grid_layout') and hasattr(self, 'scroll_content'):
            self.grid_layout.activate()
            self.scroll_content.adjustSize()

    def _populate_cards(self):
        # Stop any active batch timer
        if hasattr(self, '_batch_timer') and self._batch_timer:
            self._batch_timer.stop()
            self._batch_timer = None

        self.scroll_content.setUpdatesEnabled(False)

        # Clear existing cards cleanly
        while self.grid_layout.count():
            it = self.grid_layout.takeAt(0)
            w = it.widget()
            if w:
                w.hide()
                w.setParent(None)
                w.deleteLater()

        # Filter snippets
        visible_snippets = []
        for group in self.manager.catalog.get("groups", []):
            gid = group.get("id") or group.get("name", "")
            if self.current_category != "all" and gid != self.current_category:
                continue

            for snip in group.get("snippets", []):
                # Search filter
                if self.search_query:
                    title_text = snip.get("title") or snip.get("name", "")
                    code_text = snip.get("full_code") or snip.get("code", "")
                    match = (
                        self.search_query in title_text.lower() or
                        self.search_query in snip.get("description", "").lower() or
                        self.search_query in snip.get("category", "").lower() or
                        self.search_query in code_text.lower()
                    )
                    if not match:
                        continue

                # Installed filter
                status = self.manager.is_snippet_installed(snip["id"])
                if self.filter_installed_only and status == "none":
                    continue

                has_upd = self.manager.has_snippet_update(snip["id"])
                visible_snippets.append((snip, status, has_upd))

        self.count_lbl.setText(f"{len(visible_snippets)} Item{'s' if len(visible_snippets) != 1 else ''}")

        if self.view_mode == "list":
            self.grid_layout.setColumnStretch(0, 1)
            self.grid_layout.setColumnStretch(1, 0)
        else:
            self.grid_layout.setColumnStretch(0, 1)
            self.grid_layout.setColumnStretch(1, 1)

        cols = 1 if self.view_mode == "list" else 2
        for idx, (snip, status, has_upd) in enumerate(visible_snippets):
            is_cust = self.manager.is_snippet_customized(snip["id"])
            card = SnippetCard(snip, status, has_upd, is_customized=is_cust, view_mode=self.view_mode, parent=self.scroll_content)
            card.clicked.connect(self._open_snippet_detail)
            card.edit_requested.connect(self._on_edit_snippet)
            card.restore_requested.connect(self._on_restore_snippet)
            card.toggle_requested.connect(self._on_toggle_snippet)
            if self.view_mode == "list":
                self.grid_layout.addWidget(card, idx, 0)
            else:
                r, c = idx // cols, idx % cols
                self.grid_layout.addWidget(card, r, c)

        self.grid_layout.activate()
        self.scroll_content.adjustSize()
        self.scroll_content.setUpdatesEnabled(True)

    def _on_edit_snippet(self, snippet_id):
        snip = self.manager.get_snippet(snippet_id)
        if not snip:
            return

        current_code = self.manager.get_installed_snippet_code(snippet_id) or snip.get("full_code", "") or snip.get("code", "")
        parsed_items = find_items_and_menus(current_code)
        target = parsed_items[0] if parsed_items else {}
        props = target.get('props', {}).copy()

        snip_title = snip.get('title') or snip.get('name')
        if 'title' not in props and snip_title:
            props['title'] = f"'{snip_title}'"
        snip_icon = snip.get('icon') or snip.get('glyph')
        if 'image' not in props and 'icon' not in props and snip_icon:
            props['image'] = snip_icon

        item_dict = {
            'type': target.get('type', 'item'),
            'props': props,
            'file': self.manager.items_nss_path,
            'start': target.get('start', 0),
            'end': target.get('end', len(current_code)),
            'has_children': target.get('has_children', False),
            'raw_inner': target.get('raw_inner', '')
        }

        dlg = ImportEditorDialog(item_dict, parent=self)
        if dlg.exec_() == QDialog.Accepted:
            new_props = dlg.get_props()
            merged = props.copy()
            for k in list(merged.keys()):
                if k not in new_props and k not in ('_order', 'file', 'start', 'end', 'cmd', 'arg', 'args', 'where', 'mode', 'window', 'admin', 'keys', 'key', 'tip'):
                    del merged[k]
            for k, v in new_props.items():
                if v is None or v == 'None' or (k in ('vis', 'pos', 'type', 'menu') and not str(v).strip()):
                    if k in merged:
                        del merged[k]
                else:
                    merged[k] = v

            pts = []
            handled = set()
            orig_order = props.get('_order', [])
            for k in orig_order:
                if k in merged:
                    v = str(merged[k]).strip()
                    formatted = format_nss_value(k, v)
                    if formatted:
                        pts.append(formatted)
                    handled.add(k)
            for k, v in merged.items():
                if k not in handled and not k.startswith('_') and k not in ('file', 'start', 'end', 'cmd_end', 'has_children', 'raw_inner', 'indent'):
                    formatted = format_nss_value(k, str(v).strip())
                    if formatted:
                        pts.append(formatted)

            elem_type = target.get('type', 'item')
            new_code = f"{elem_type}({', '.join(pts)})"
            if item_dict.get('raw_inner'):
                new_code += f" {item_dict['raw_inner']}"

            self.manager.add_snippet(snippet_id, custom_code=new_code)
            self.refresh_installed_only()
            self.reload_requested.emit()

    def _on_restore_snippet(self, snippet_id):
        self.manager.restore_snippet_default(snippet_id)
        self.refresh_installed_only()
        self.reload_requested.emit()

    def _on_toggle_snippet(self, snippet_id, is_adding):
        if is_adding:
            self.manager.add_snippet(snippet_id)
        else:
            self.manager.remove_snippet(snippet_id)
        self.refresh_installed_only()
        self.reload_requested.emit()

    def _open_snippet_detail(self, snippet_id):
        self.detail_view.load_snippet(snippet_id)
        self.stacked_view.setCurrentIndex(1)

    def _on_back_to_gallery(self):
        self.stacked_view.setCurrentIndex(0)
        self._populate_cards()

    def _on_item_modified(self):
        self.reload_requested.emit()


