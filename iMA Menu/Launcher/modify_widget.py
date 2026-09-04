import os
import re
import sys
import json
import hashlib
from PyQt5.QtWidgets import (QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, 
                             QScrollArea, QFrame, QLineEdit, QFileDialog, QComboBox, 
                             QCheckBox, QRadioButton, QGridLayout, QButtonGroup, QListWidget,
                             QListWidgetItem, QSizePolicy, QDialog, QFormLayout, 
                             QGraphicsDropShadowEffect, QTabWidget, QStackedWidget, QLayout, QListView,
                             QStyledItemDelegate, QStyle, QAbstractItemView, QTextEdit, QFileIconProvider, QCompleter,
                             QMenu, QAction)
from PyQt5.QtGui import QColor, QFont, QPainter, QPainterPath, QPen, QIcon, QPixmap, QFontDatabase, QFontMetrics, QImage, QConicalGradient, QLinearGradient, QRadialGradient
from PyQt5.QtCore import Qt, pyqtSignal, QSize, QEvent, QPoint, QPointF, QRect, QRectF, QTimer, QObject, QAbstractListModel, QModelIndex, QFileInfo
try: from PyQt5 import QtSvg
except ImportError: QtSvg = None
from utils import resource_path, UnsavedChangesDialog, safe_file_write, get_font_icon, get_mdl2_icon, NILESOFT_FONT_FAMILY, _init_nilesoft_font, FlowLayout, normalize_path, ModernComboBox, render_nss_asset_pixmap, PillTabButton, PillPushButton, PillLineEdit
from theme_editor_widget import MinimalColorPickerDialog
from nss_parser import (
    NSSLexer, parse_nss_args, find_items_and_menus, format_nss_value,
    save_imported_item, mass_save_op, _get_custom_menus_from_nss,
    _get_vis_options, _build_vis_expression, _parse_vis_expression,
    is_rule_complete, extract_ids_from_section, extract_custom_rules,
    update_section, scan_nss_items, cleanup_orphan_icons,
    read_file, write_file
)

# Global path storage to be set by launcher.pyw
PROJECT_ROOT = None

def set_project_root(root):
    global PROJECT_ROOT
    PROJECT_ROOT = root
    import nss_parser
    nss_parser.set_project_root(root)

DEFAULT_IDS = [
    "id.account", "id.add_a_network_location", "id.add_to_favorites", "id.add_to_playlist",
    "id.add_to_windows_media_player_list", "id.adjust_date_time", "id.administrator", "id.align_icons_to_grid",
    "id.all_control_panel_items", "id.application", "id.arrange_by", "id.autoplay",
    "id.auto_arrange_icons", "id.burn_disc_image", "id.cancel", "id.cascade_windows",
    "id.cast_to_device", "id.cleanup", "id.close", "id.close_all_windows",
    "id.collapse", "id.collapse_all_groups", "id.collapse_group", "id.command_prompt",
    "id.compressed", "id.configure", "id.content", "id.control_panel",
    "id.copy", "id.copy_as_path", "id.copy_here", "id.copy_path",
    "id.copy_to", "id.copy_to_clipboard", "id.copy_to_folder", "id.cortana",
    "id.create_shortcut", "id.create_shortcuts", "id.create_shortcuts_here", "id.customize_notification_icons",
    "id.customize_this_folder", "id.cut", "id.default", "id.delete",
    "id.desktop", "id.details", "id.device_manager", "id.disconnect",
    "id.disconnect_network_drive", "id.display_settings", "id.documents", "id.downloads",
    "id.edit", "id.eject", "id.empty", "id.empty_recycle_bin",
    "id.erase_this_disc", "id.exit_explorer", "id.expand", "id.expand_all_groups",
    "id.expand_group", "id.expand_to_current_folder", "id.extract_all", "id.extract_to",
    "id.extra_large_icons", "id.favorites", "id.file_access_denied", "id.file_explorer",
    "id.file_explorer_options", "id.file_in_use", "id.folder", "id.folders",
    "id.folder_access_denied", "id.folder_in_use", "id.folder_options", "id.format",
    "id.general", "id.give_access_to", "id.go_to", "id.group_by",
    "id.hide", "id.import_pictures_and_videos", "id.include_in_library", "id.insert_unicode_control_character",
    "id.install", "id.invert_selection", "id.large_icons", "id.list",
    "id.lock_all_taskbars", "id.lock_the_taskbar", "id.make_available_offline", "id.make_available_online",
    "id.manage", "id.map_as_drive", "id.map_network_drive", "id.maximize",
    "id.media", "id.medium_icons", "id.merge", "id.minimize",
    "id.minimize_all_windows", "id.more", "id.more_options", "id.mount",
    "id.move", "id.move_here", "id.move_to", "id.move_to_folder",
    "id.music", "id.network", "id.new", "id.news_and_interests",
    "id.new_folder", "id.new_item", "id.next_desktop_background", "id.none",
    "id.open", "id.open_as_portable", "id.open_autoplay", "id.open_command_prompt",
    "id.open_command_window_here", "id.open_file_location", "id.open_folder_location", "id.open_in_new_process",
    "id.open_in_new_tab", "id.open_in_new_window", "id.open_new_tab", "id.open_new_window",
    "id.open_powershell_window_here", "id.open_windows_powershell", "id.open_with", "id.options",
    "id.paste", "id.paste_shortcut", "id.permanently_delete", "id.personalize",
    "id.personal_folder", "id.pictures", "id.pin_current_folder_to_quick_access", "id.pin_to_quick_access",
    "id.pin_to_start", "id.pin_to_start_menu", "id.pin_to_taskbar", "id.play",
    "id.play_with_windows_media_player", "id.power", "id.power_options", "id.preview",
    "id.print", "id.programs", "id.programs_and_features", "id.properties",
    "id.reconversion", "id.recycle_bin", "id.redo", "id.refresh",
    "id.remove", "id.remove_from_favorites", "id.remove_from_quick_access", "id.remove_from_recent",
    "id.remove_properties", "id.rename", "id.restart", "id.restore",
    "id.restore_all_windows", "id.restore_default_libraries", "id.restore_previous_versions", "id.rotate_left",
    "id.rotate_right", "id.run", "id.run_as_administrator", "id.run_as_another_user",
    "id.run_as_different_user", "id.run_with_powershell", "id.search", "id.security",
    "id.select", "id.select_all", "id.select_none", "id.send_feedback",
    "id.send_to", "id.settings", "id.set_as_desktop_background", "id.set_as_desktop_wallpaper",
    "id.share", "id.share_with", "id.shield", "id.shortcut",
    "id.show", "id.show_all_folders", "id.show_cortana_button", "id.show_desktop_icons",
    "id.show_file_extensions", "id.show_hidden_files", "id.show_libraries", "id.show_network",
    "id.show_open_windows", "id.show_pen_button", "id.show_people_on_the_taskbar", "id.show_task_view_button",
    "id.show_the_desktop", "id.show_this_pc", "id.show_touchpad_button", "id.show_touch_keyboard_button",
    "id.show_windows_side_by_side", "id.show_windows_stacked", "id.shut_down", "id.sign_out",
    "id.size", "id.small_icons", "id.sort_by", "id.start_menu",
    "id.store", "id.system", "id.system_folder", "id.taskbar",
    "id.taskbar_settings", "id.task_manager", "id.terminal", "id.this_pc",
    "id.tiles", "id.troubleshoot_compatibility", "id.turn_off_bitlocker", "id.turn_on_bitlocker",
    "id.undo", "id.unpin_from_quick_access", "id.unpin_from_start", "id.unpin_from_start_menu",
    "id.unpin_from_taskbar", "id.videos", "id.view", "id.windows",
    "id.windows_powershell", "id.windows_terminal"
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

class AnimatedGlowPreviewLabel(QPushButton):
    """
    Large icon preview box (68x68) with a continuous animated gradient glow border.
    Uses QPushButton's built-in clicked signal.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(68, 68)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip("Click to Browse Glyphs / Upload Icon")
        self._angle = 0
        self._asset_val = ""
        self._rendered_pixmap = None
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._rotate_glow)
        self._timer.start(35)

    def _rotate_glow(self):
        self._angle = (self._angle + 3) % 360
        self.update()

    def set_asset(self, val):
        self._asset_val = str(val or "")
        self._rendered_pixmap = render_nss_asset_pixmap(self._asset_val, size=40)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setRenderHint(QPainter.SmoothPixmapTransform)
            painter.setRenderHint(QPainter.TextAntialiasing)

            center = QPointF(self.width() / 2.0, self.height() / 2.0)
            is_hover = self.underMouse()

            # Outer radiant bloom glow on hover
            if is_hover:
                glow_radius = self.width() / 2.0
                glow_grad = QRadialGradient(center, glow_radius)
                glow_grad.setColorAt(0.0, QColor(234, 153, 156, 180))
                glow_grad.setColorAt(0.4, QColor(231, 130, 132, 140))
                glow_grad.setColorAt(0.7, QColor(168, 85, 247, 90))
                glow_grad.setColorAt(1.0, QColor(0, 0, 0, 0))
                painter.fillRect(self.rect(), glow_grad)

            rect = QRectF(5, 5, self.width() - 10, self.height() - 10)

            gradient = QConicalGradient(center, self._angle)
            gradient.setColorAt(0.0, QColor("#ea999c"))
            gradient.setColorAt(0.3, QColor("#e78284"))
            gradient.setColorAt(0.6, QColor("#a855f7"))
            gradient.setColorAt(0.85, QColor("#ec4899"))
            gradient.setColorAt(1.0, QColor("#ea999c"))

            border_pen = QPen(gradient, 2.5 if is_hover else 1.8)
            painter.setPen(border_pen)
            
            path = QPainterPath()
            path.addRoundedRect(rect, 14, 14)
            
            painter.fillPath(path, QColor("#121212") if not is_hover else QColor("#1a1018"))
            painter.drawPath(path)

            if self._rendered_pixmap and not self._rendered_pixmap.isNull():
                pw = self._rendered_pixmap.width()
                ph = self._rendered_pixmap.height()
                px = center.x() - pw / 2
                py = center.y() - ph / 2
                painter.drawPixmap(int(px), int(py), self._rendered_pixmap)
            else:
                glyph_font = QFont("Segoe MDL2 Assets", 18, QFont.Bold)
                painter.setFont(glyph_font)
                painter.setPen(QColor("#ea999c"))
                painter.drawText(rect, Qt.AlignCenter, "\uE734")
        finally:
            painter.end()


class ColorCircleButton(QPushButton):
    """
    Circular color dot button (●) for selecting glyph layer colors.
    """
    colorSelected = pyqtSignal(str)

    def __init__(self, color="#ea999c", tooltip="Select Color", parent=None):
        super().__init__(parent)
        self._color = color or "#ffffff"
        self.setFixedSize(28, 28)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip(tooltip)
        self.clicked.connect(self._toggle_palette)

    def get_color(self):
        return self._color

    def set_color(self, color):
        self._color = color or "#ffffff"
        self.update()

    def enterEvent(self, event):
        super().enterEvent(event)
        self.update()

    def leaveEvent(self, event):
        super().leaveEvent(event)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = QRectF(2.0, 2.0, self.width() - 4.0, self.height() - 4.0)
        is_hover = self.underMouse() and self.isEnabled()

        path = QPainterPath()
        path.addEllipse(rect)
        if not self.isEnabled():
            painter.fillPath(path, QColor(45, 48, 58))
            painter.setPen(QPen(QColor(255, 255, 255, 35), 1.2))
        else:
            painter.fillPath(path, QColor(self._color))
            border_color = QColor(255, 255, 255, 230) if is_hover else QColor(255, 255, 255, 80)
            painter.setPen(QPen(border_color, 2.0 if is_hover else 1.5))
        painter.drawPath(path)

        painter.end()

    def _toggle_palette(self):
        dlg = MinimalColorPickerDialog(self._color or "#ea999c", "glyph_color", self)
        dlg.default_checkbox.hide()
        def on_color(key, color):
            hex_c = color.name() if hasattr(color, 'name') else str(color)
            self._on_palette_color(hex_c)
        dlg.colorSelected.connect(on_color)
        dlg.exec_()

    def _on_palette_color(self, hex_color):
        self.set_color(hex_color)
        self.colorSelected.emit(hex_color)

ColorDropdownPill = ColorCircleButton


class ModernCheckBox(QCheckBox):
    """Anti-aliased vector checkbox with smooth 1.5px border and checkmark."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(18, 18)
        self.setCursor(Qt.PointingHandCursor)
        self.setAttribute(Qt.WA_Hover, True)
        self.setStyleSheet("background: transparent; border: none;")

    def enterEvent(self, event):
        super().enterEvent(event)
        self.update()

    def leaveEvent(self, event):
        super().leaveEvent(event)
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(1.0, 1.0, self.width() - 2.0, self.height() - 2.0)
        path = QPainterPath()
        path.addRoundedRect(rect, 4.0, 4.0)

        is_chk = self.isChecked()
        is_hov = self.underMouse()

        if is_chk:
            p.fillPath(path, QColor("#e78284"))
            p.setPen(QPen(QColor("#ea999c"), 1.5))
            p.drawPath(path)
            p.setPen(QPen(QColor("#ffffff"), 1.8, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            p.drawLine(int(rect.left() + 4), int(rect.top() + 9), int(rect.left() + 7), int(rect.top() + 12))
            p.drawLine(int(rect.left() + 7), int(rect.top() + 12), int(rect.left() + 13), int(rect.top() + 5))
        else:
            p.fillPath(path, QColor(255, 255, 255, 12))
            border_c = QColor(255, 255, 255, 120) if is_hov else QColor(255, 255, 255, 60)
            p.setPen(QPen(border_c, 1.5))
            p.drawPath(path)
        p.end()


class PillSearchInput(PillLineEdit):
    """Vector anti-aliased pill-shaped search line edit."""
    def __init__(self, placeholder="", parent=None):
        super().__init__(placeholder=placeholder, parent=parent, height=38)


class UploadIconButton(QPushButton):
    """Vector anti-aliased circular upload button."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(38, 38)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip("Upload Custom Image/Icon")
        self.setAttribute(Qt.WA_Hover, True)
        self.setStyleSheet("background: transparent; border: none; outline: none;")

    def enterEvent(self, event):
        super().enterEvent(event)
        self.update()

    def leaveEvent(self, event):
        super().leaveEvent(event)
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)

        rect = QRectF(self.rect()).adjusted(1.0, 1.0, -1.0, -1.0)
        path = QPainterPath()
        path.addEllipse(rect)

        is_hover = self.underMouse()
        if is_hover:
            p.fillPath(path, QColor(231, 130, 132, 45))
            p.setPen(QPen(QColor("#e78284"), 1.5))
            p.drawPath(path)
            p.setPen(QColor("#ffffff"))
        else:
            p.fillPath(path, QColor(255, 255, 255, 12))
            p.setPen(QPen(QColor(255, 255, 255, 32), 1.2))
            p.drawPath(path)
            p.setPen(QColor("#e0e0e0"))

        p.setFont(QFont('Segoe MDL2 Assets', 12))
        p.drawText(self.rect(), Qt.AlignCenter, "\uE8E5")
        p.end()


class GlyphPreviewFrame(QFrame):
    """Vector anti-aliased preview container with exactly ONE smooth outline."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(56, 38)
        self.setAttribute(Qt.WA_Hover, True)
        self.setStyleSheet("background: transparent; border: none;")

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
        path = QPainterPath()
        path.addRoundedRect(rect, 12.0, 12.0)

        is_hover = self.underMouse()
        p.fillPath(path, QColor(255, 255, 255, 18 if is_hover else 12))
        border_c = QColor(255, 255, 255, 70) if is_hover else QColor(255, 255, 255, 32)
        p.setPen(QPen(border_c, 1.2))
        p.drawPath(path)
        p.end()


class InlinePalettePopup(QDialog):
    """
    Sleek floating popup with swatches, custom hex input, and eyedropper tool.
    """
    colorSelected = pyqtSignal(str)

    PALETTE = [
        "#ea999c", "#e78284", "#f43f5e", "#ec4899", "#d946ef", "#a855f7",
        "#8b5cf6", "#6366f1", "#3b82f6", "#0ea5e9", "#06b6d4", "#14b8a6",
        "#10b981", "#22c55e", "#84cc16", "#eab308", "#f97316", "#ef4444",
        "#ffffff", "#d1d5db", "#9ca3af", "#6b7280", "#374151", "#111827"
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(220, 180)

        main_lay = QVBoxLayout(self)
        main_lay.setContentsMargins(0, 0, 0, 0)

        frame = QFrame(self)
        frame.setStyleSheet("""
            QFrame {
                background-color: #12141c;
                border: 1px solid #2a2e42;
                border-radius: 12px;
            }
        """)
        main_lay.addWidget(frame)

        cl = QVBoxLayout(frame)
        cl.setContentsMargins(10, 10, 10, 10)
        cl.setSpacing(8)

        grid_w = QWidget()
        grid_lay = QGridLayout(grid_w)
        grid_lay.setContentsMargins(0, 0, 0, 0)
        grid_lay.setSpacing(5)

        for i, color in enumerate(self.PALETTE):
            btn = QPushButton()
            btn.setFixedSize(22, 22)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {color};
                    border: 1px solid rgba(255,255,255,0.15);
                    border-radius: 6px;
                }}
                QPushButton:hover {{
                    border: 2px solid #ffffff;
                }}
            """)
            btn.clicked.connect(lambda _, c=color: self._select_color(c))
            row = i // 6
            col = i % 6
            grid_lay.addWidget(btn, row, col)

        cl.addWidget(grid_w)

        hex_row = QHBoxLayout()
        hex_row.setSpacing(6)
        
        self.hex_inp = QLineEdit("#ea999c")
        self.hex_inp.setFixedHeight(28)
        self.hex_inp.setStyleSheet("""
            QLineEdit {
                background-color: #121212;
                border: 1px solid #2a2e42;
                border-radius: 6px;
                color: #ffffff;
                padding: 0 6px;
                font-size: 11px;
                font-family: 'Consolas', monospace;
            }
            QLineEdit:focus {
                border: 1px solid #ea999c;
            }
        """)
        hex_row.addWidget(self.hex_inp, 1)

        apply_btn = QPushButton("Apply")
        apply_btn.setFixedHeight(28)
        apply_btn.setCursor(Qt.PointingHandCursor)
        apply_btn.setStyleSheet("""
            QPushButton {
                background-color: #ea999c;
                color: #ffffff;
                border-radius: 6px;
                font-weight: bold;
                font-size: 11px;
                padding: 0 10px;
                border: none;
            }
            QPushButton:hover {
                background-color: #ff4770;
            }
        """)
        apply_btn.clicked.connect(self._apply_custom_hex)
        hex_row.addWidget(apply_btn)

        cl.addLayout(hex_row)

    def _select_color(self, c):
        self.colorSelected.emit(c)
        self.close()

    def _apply_custom_hex(self):
        c = self.hex_inp.text().strip()
        if not c.startswith("#"):
            c = "#" + c
        if len(c) in (4, 7, 9):
            self.colorSelected.emit(c)
            self.close()


class CriteriaPill(QPushButton):
    """
    Pill-shaped radio switch with pink/magenta gradient border and glowing filled dot when active.
    """
    def __init__(self, text, mode, parent=None):
        super().__init__(parent)
        self.setText(text)
        self.mode = mode
        self.setCheckable(True)
        self.setFixedHeight(32)
        self.setMinimumWidth(76)
        self.setCursor(Qt.PointingHandCursor)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.TextAntialiasing)

        rect = QRectF(1, 1, self.width() - 2, self.height() - 2)
        path = QPainterPath()
        path.addRoundedRect(rect, 16, 16)

        is_checked = self.isChecked()
        is_hover = self.underMouse()

        if is_checked:
            painter.fillPath(path, QColor(234, 153, 156, 28))
            gradient = QLinearGradient(rect.topLeft(), rect.bottomRight())
            gradient.setColorAt(0.0, QColor("#ea999c"))
            gradient.setColorAt(1.0, QColor("#e78284"))
            painter.setPen(QPen(gradient, 1.5))
            painter.drawPath(path)

            dot_rect = QRectF(rect.left() + 8, (self.height() - 12) / 2, 12, 12)
            dot_path = QPainterPath()
            dot_path.addEllipse(dot_rect)
            painter.fillPath(dot_path, QColor("#ea999c"))
            painter.setPen(Qt.NoPen)
            painter.drawPath(dot_path)

            inner_rect = QRectF(rect.left() + 11.5, (self.height() - 5) / 2, 5, 5)
            painter.setBrush(QColor("#ffffff"))
            painter.drawEllipse(inner_rect)
        else:
            painter.fillPath(path, QColor("#121212") if not is_hover else QColor("#0E0E0E"))
            painter.setPen(QPen(QColor("#242738") if not is_hover else QColor("#383d56"), 1.0))
            painter.drawPath(path)

            dot_rect = QRectF(rect.left() + 8, (self.height() - 12) / 2, 12, 12)
            painter.setPen(QPen(QColor("#4b5563") if not is_hover else QColor("#9ca3af"), 1.2))
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(dot_rect)

        font = QFont("Segoe UI Variable Display", 9)
        font.setWeight(QFont.DemiBold if is_checked else QFont.Medium)
        painter.setFont(font)
        painter.setPen(QColor("#ffffff") if is_checked else QColor("#9ca3af"))
        
        text_rect = QRectF(rect.left() + 24, 0, self.width() - 28, self.height())
        painter.drawText(text_rect, Qt.AlignLeft | Qt.AlignVCenter, self.text())

        painter.end()


class VisibilityCard(QPushButton):
    """
    Modern rectangular card for visibility selection with top icon, bold title, 2-4 word description, and top right checkmark badge.
    """
    def __init__(self, key, title, subtitle, icon_code, parent=None):
        super().__init__(parent)
        self.key = key
        self.title_text = title
        self.sub_text = subtitle
        self.icon_code = icon_code
        self.setCheckable(True)
        self.setFixedHeight(70)
        self.setCursor(Qt.PointingHandCursor)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.TextAntialiasing)

        rect = QRectF(1, 1, self.width() - 2, self.height() - 2)
        path = QPainterPath()
        path.addRoundedRect(rect, 10, 10)

        is_checked = self.isChecked()
        is_hover = self.underMouse()

        if is_checked:
            painter.fillPath(path, QColor(234, 153, 156, 26))
            gradient = QLinearGradient(rect.topLeft(), rect.bottomRight())
            gradient.setColorAt(0.0, QColor("#ea999c"))
            gradient.setColorAt(1.0, QColor("#e78284"))
            painter.setPen(QPen(gradient, 1.5))
            painter.drawPath(path)

            chk_rect = QRectF(rect.right() - 15, rect.top() + 5, 11, 11)
            chk_path = QPainterPath()
            chk_path.addEllipse(chk_rect)
            painter.fillPath(chk_path, QColor("#ea999c"))
            painter.setPen(Qt.NoPen)
            painter.drawPath(chk_path)

            painter.setFont(QFont("Segoe MDL2 Assets", 6, QFont.Bold))
            painter.setPen(QColor("#ffffff"))
            painter.drawText(chk_rect, Qt.AlignCenter, "\uE73E")
        else:
            painter.fillPath(path, QColor("#121212") if not is_hover else QColor("#0E0E0E"))
            painter.setPen(QPen(QColor("#242738") if not is_hover else QColor("#383d56"), 1.0))
            painter.drawPath(path)

        icon_font = QFont("Segoe MDL2 Assets", 11, QFont.Bold)
        painter.setFont(icon_font)
        painter.setPen(QColor("#ea999c") if is_checked else (QColor("#9ca3af") if not is_hover else QColor("#d1d5db")))
        icon_rect = QRectF(rect.left() + 7, rect.top() + 7, 18, 14)
        painter.drawText(icon_rect, Qt.AlignLeft | Qt.AlignVCenter, chr(self.icon_code))

        title_font = QFont("Segoe UI Variable Display", 9, QFont.Bold)
        painter.setFont(title_font)
        painter.setPen(QColor("#ea999c") if is_checked else QColor("#ffffff"))
        title_rect = QRectF(rect.left() + 7, rect.top() + 25, rect.width() - 14, 15)
        painter.drawText(title_rect, Qt.AlignLeft | Qt.AlignVCenter, self.title_text)

        sub_font = QFont("Segoe UI Variable Display", 7, QFont.Medium)
        painter.setFont(sub_font)
        painter.setPen(QColor("#ec4899") if is_checked else QColor("#6b7280"))
        sub_rect = QRectF(rect.left() + 7, rect.top() + 41, rect.width() - 14, 24)
        painter.drawText(sub_rect, Qt.AlignLeft | Qt.AlignTop | Qt.TextWordWrap, self.sub_text)

        painter.end()


VALID_NIL_TYPES = {
    '*', 'file', 'dir', 'directory', 'drive', 'usb', 'dvd', 'fixed', 'vhd',
    'removable', 'remote', 'back', 'back.directory', 'back.dir', 'back.drive',
    'back.namespace', 'back.computer', 'back.recyclebin', 'desktop', 'namespace',
    'computer', 'recyclebin', 'taskbar', 'all'
}

class VisibilityWidget(QWidget):
    valueChanged = pyqtSignal(str)
    MAIN_VIS_EXPR = "@if(key.shift() || key.control() || key.capslock() || key.lbutton(), 'hidden', 'normal')"

    CARDS = [
        ('normal', 'Normal', 'Always Visible', 0xE890),
        ('hide', 'Hidden', 'Hidden Everywhere', 0xED1A),
        ('main', 'Right-Click', 'In Right-Click ONLY', 0xE80F),
        ('shift', 'Shift', 'Shift + Right-Click', 0xE74A),
        ('ctrl', 'Ctrl', 'Ctrl + Right-Click', 0xE765),
        ('caps', 'Capslock', 'Caps + Right-Click', 0xE8E8),
        ('lmb', 'Left Click', 'Left + Right-Click', 0xE962),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._updating = False
        self._custom_vis = ""
        self._user_modified = False

        layout = QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setHorizontalSpacing(6)
        layout.setVerticalSpacing(6)
        for col in range(4):
            layout.setColumnStretch(col, 1)

        self.cards = {}
        for idx, (key, title, sub, icon) in enumerate(self.CARDS):
            r = idx // 4
            c = idx % 4
            card = VisibilityCard(key, title, sub, icon)
            self.cards[key] = card
            layout.addWidget(card, r, c)
            card.toggled.connect(lambda checked, k=key: self._on_card_toggled(k, checked))

        self.set_value("")

    def _on_card_toggled(self, key, checked):
        if self._updating: return
        self._updating = True
        self._user_modified = True
        if checked:
            for k, card in self.cards.items():
                if k != key: card.setChecked(False)
        else:
            if not any(card.isChecked() for card in self.cards.values()):
                self.cards['normal'].setChecked(True)
        self._updating = False
        self.valueChanged.emit(self.get_value())

    def get_value(self):
        if not self._user_modified and self._custom_vis:
            return self._custom_vis
        for k, card in self.cards.items():
            if card.isChecked():
                if k == 'hide':
                    return "vis.remove"
                elif k == 'main':
                    if self._custom_vis:
                        cv = self._custom_vis.lower().replace('"', '').replace("'", "").replace(" ", "")
                        if ('key.shift' in cv or 'key.control' in cv or 'key.ctrl' in cv or 'key.lbutton' in cv or 'key.caps' in cv) and 'hidden' in cv:
                            return self._custom_vis
                    return self.MAIN_VIS_EXPR
                elif k == 'normal': return ""
                elif k == 'shift': return "key.shift()"
                elif k == 'ctrl': return "key.control()"
                elif k == 'caps': return "key.capslock()"
                elif k == 'lmb': return "key.lbutton()"
        return self._custom_vis if not self._user_modified else ""

    def set_value(self, vis_str):
        self._updating = True
        self._user_modified = False
        self._custom_vis = str(vis_str or '').strip()
        clean_vis = self._custom_vis.lower().replace('"', '').replace("'", "").replace(" ", "")

        if clean_vis in ('vis.remove', 'remove', 'vis.hidden', 'hidden', '0', 'none'):
            for k, card in self.cards.items(): card.setChecked(k == 'hide')
        elif ('key.shift' in clean_vis or 'key.control' in clean_vis or 'key.ctrl' in clean_vis or 'key.lbutton' in clean_vis or 'key.caps' in clean_vis) and 'hidden' in clean_vis:
            for k, card in self.cards.items(): card.setChecked(k == 'main')
        elif not clean_vis or clean_vis in ('vis.normal', 'normal', 'alwaysvisible', '1'):
            for k, card in self.cards.items(): card.setChecked(k == 'normal')
        elif clean_vis in ('key.shift()', 'vis.shift()', 'vis.shift', 'shift', 'key.shift'):
            for k, card in self.cards.items(): card.setChecked(k == 'shift')
        elif clean_vis in ('key.control()', 'key.ctrl()', 'vis.control()', 'vis.control', 'vis.ctrl', 'control', 'ctrl', 'key.control', 'key.ctrl'):
            for k, card in self.cards.items(): card.setChecked(k == 'ctrl')
        elif clean_vis in ('key.capslock()', 'key.caps()', 'vis.capslock()', 'vis.capslock', 'vis.caps', 'capslock', 'caps', 'key.capslock', 'key.caps'):
            for k, card in self.cards.items(): card.setChecked(k == 'caps')
        elif clean_vis in ('key.lbutton()', 'key.lmb()', 'vis.lbutton()', 'vis.lbutton', 'vis.lmb', 'lbutton', 'lmb', 'key.lbutton'):
            for k, card in self.cards.items(): card.setChecked(k == 'lmb')
        else:
            for k, card in self.cards.items(): card.setChecked(k == 'normal')
        self._updating = False


class TypePill(QPushButton):
    """
    Interactive checkbox pill for 'Show in' locations.
    """
    def __init__(self, val, text, icon_code=None, parent=None):
        super().__init__(parent)
        self.val = val
        self.title_text = text
        self.icon_code = icon_code
        self.setCheckable(True)
        self.setFixedHeight(32)
        self.setCursor(Qt.PointingHandCursor)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.TextAntialiasing)

        rect = QRectF(1.0, 1.0, self.width() - 2.0, self.height() - 2.0)
        path = QPainterPath()
        r = rect.height() / 2.0
        path.addRoundedRect(rect, r, r)

        is_checked = self.isChecked()
        is_hover = self.underMouse()

        if is_checked:
            painter.fillPath(path, QColor(234, 153, 156, 32))
            gradient = QLinearGradient(rect.topLeft(), rect.bottomRight())
            gradient.setColorAt(0.0, QColor("#ea999c"))
            gradient.setColorAt(1.0, QColor("#e78284"))
            painter.setPen(QPen(gradient, 1.5))
            painter.drawPath(path)

            box_rect = QRectF(rect.left() + 7, (self.height() - 13) / 2.0, 13, 13)
            box_path = QPainterPath()
            box_path.addEllipse(box_rect)
            painter.fillPath(box_path, QColor("#ea999c"))
            painter.setPen(Qt.NoPen)
            painter.drawPath(box_path)

            painter.setFont(QFont("Segoe MDL2 Assets", 7, QFont.Bold))
            painter.setPen(QColor("#ffffff"))
            painter.drawText(box_rect, Qt.AlignCenter, "\uE73E")
        else:
            painter.fillPath(path, QColor(255, 255, 255, 14) if is_hover else QColor(255, 255, 255, 6))
            painter.setPen(QPen(QColor(255, 255, 255, 55) if is_hover else QColor(255, 255, 255, 22), 1.5))
            painter.drawPath(path)

            box_rect = QRectF(rect.left() + 7, (self.height() - 13) / 2.0, 13, 13)
            box_path = QPainterPath()
            box_path.addEllipse(box_rect)
            painter.setPen(QPen(QColor("#737994") if not is_hover else QColor("#b5bfe2"), 1.5))
            painter.setBrush(Qt.NoBrush)
            painter.drawPath(box_path)

        cur_x = rect.left() + 24
        if self.icon_code:
            icon_font = QFont("Segoe MDL2 Assets", 8)
            painter.setFont(icon_font)
            painter.setPen(QColor("#ffffff") if is_checked else QColor("#9ca3af"))
            ic_rect = QRectF(cur_x, 0, 12, self.height())
            painter.drawText(ic_rect, Qt.AlignLeft | Qt.AlignVCenter, chr(self.icon_code))
            cur_x += 14

        text_font = QFont("Segoe UI Variable Display", 8)
        text_font.setWeight(QFont.DemiBold if is_checked else QFont.Medium)
        painter.setFont(text_font)
        painter.setPen(QColor("#ffffff") if is_checked else QColor("#d1d5db"))
        txt_rect = QRectF(cur_x, 0, rect.right() - cur_x - 2, self.height())
        painter.drawText(txt_rect, Qt.AlignLeft | Qt.AlignVCenter, self.title_text)

        painter.end()


class TypeWidget(QWidget):
    valueChanged = pyqtSignal(str)

    PRESETS = [
        ('all', 'All', None),
        ('desktop', 'Desktop', 0xE7F4),
        ('taskbar', 'Taskbar', 0xE7E8),
        ('computer', 'This PC', 0xE7F8),
        ('recyclebin', 'Recycle', 0xE74D),
        ('back', 'Background', 0xE8B9),
        ('dir', 'Folders', 0xE8B7),
        ('file', 'Files', 0xE8A5),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._updating = False
        self._user_modified = False
        self._initial_raw_type = ""
        self._extra_types = []
        self._has_invalid_syntax = False
        self.pills = {}

        grid = QGridLayout(self)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(6)

        for i, (val, text, icon) in enumerate(self.PRESETS):
            pill = TypePill(val, text, icon)
            self.pills[val] = pill
            row = i // 4
            col = i % 4
            grid.addWidget(pill, row, col)
            pill.toggled.connect(self._on_toggled)

        self.set_value("")

    def _on_toggled(self, checked):
        if self._updating: return
        sender = self.sender()
        val = sender.val
        self._updating = True
        self._user_modified = True
        if val == 'all':
            if checked:
                for k, p in self.pills.items():
                    if k != 'all': p.setChecked(False)
            else:
                if not any(p.isChecked() for k, p in self.pills.items() if k != 'all'):
                    self.pills['all'].setChecked(True)
        else:
            if checked:
                self.pills['all'].setChecked(False)
            else:
                if not any(p.isChecked() for k, p in self.pills.items() if k != 'all'):
                    self.pills['all'].setChecked(True)
        self._updating = False
        self.valueChanged.emit(self.get_value())

    def get_value(self):
        if not self._user_modified:
            if not self._has_invalid_syntax and self._initial_raw_type:
                return self._initial_raw_type
            if not self._initial_raw_type:
                return ""
        if self.pills['all'].isChecked():
            return ""
        active = [k for k, p in self.pills.items() if p.isChecked() and k != 'all']
        combined = []
        for a in active:
            if a not in combined:
                combined.append(a)
        for extra in self._extra_types:
            if extra not in combined:
                combined.append(extra)
        return "|".join(combined)

    def set_value(self, type_str):
        self._updating = True
        self._user_modified = False
        self._initial_raw_type = str(type_str or "").strip().strip("'\"")
        raw = self._initial_raw_type.lower()
        self._extra_types = []
        self._has_invalid_syntax = False

        if not raw or raw == 'all':
            self.pills['all'].setChecked(True)
            for k, p in self.pills.items():
                if k != 'all': p.setChecked(False)
        else:
            self.pills['all'].setChecked(False)
            parts = [p.strip().strip("'\"") for p in raw.split('|') if p.strip()]
            for part in parts:
                low_p = part.lower()
                if low_p in ('dir', 'directory'):
                    self.pills['dir'].setChecked(True)
                elif low_p == 'file':
                    self.pills['file'].setChecked(True)
                elif low_p == 'desktop':
                    self.pills['desktop'].setChecked(True)
                elif low_p == 'taskbar':
                    self.pills['taskbar'].setChecked(True)
                elif low_p in ('computer', 'drive'):
                    self.pills['computer'].setChecked(True)
                    if low_p == 'drive':
                        self._extra_types.append(part)
                elif low_p == 'recyclebin':
                    self.pills['recyclebin'].setChecked(True)
                elif low_p == 'back' or low_p.startswith('back.'):
                    self.pills['back'].setChecked(True)
                    if low_p.startswith('back.'):
                        self._extra_types.append(part)
                elif low_p in VALID_NIL_TYPES:
                    self._extra_types.append(part)
                else:
                    self._has_invalid_syntax = True

            if not any(p.isChecked() for k, p in self.pills.items() if k != 'all') and not self._extra_types:
                self.pills['all'].setChecked(True)

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
        
    title = item.get('_stitle')
    if title is None:
        props = item.get('props', {})
        title = str(props.get('title', '')).strip('\'" ').lower()
        find = str(props.get('find', '')).strip('\'" ').lower()
        file_name = os.path.basename(item.get('file', '')).replace('.nss', '').lower()
        in_menu = str(props.get('in', '')).strip('\'" ').lower()
        cmd = str(props.get('cmd', '')).strip('\'" ').lower()
        tip = str(props.get('tip', '')).strip('\'" ').lower()
        item_type = str(item.get('type', '')).lower()
    else:
        find = item.get('_sfind', '')
        file_name = item.get('_sfile', '')
        in_menu = item.get('_sin_menu', '')
        cmd = item.get('_scmd', '')
        tip = item.get('_stip', '')
        item_type = item.get('_stype', '')
    
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
        super().__init__(parent); self._items = []; self._filtered_items = []
        if items: self.set_items(items)
    def rowCount(self, parent=QModelIndex()): return len(self._filtered_items)
    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or role != Qt.UserRole: return None
        return self._filtered_items[index.row()]
    def set_items(self, items):
        self.beginResetModel()
        for it in (items or []):
            if isinstance(it, dict):
                props = it.get('props', {})
                it['_stitle'] = str(props.get('title', '')).strip('\'" ').lower()
                it['_sfind'] = str(props.get('find', '')).strip('\'" ').lower()
                it['_sfile'] = os.path.basename(it.get('file', '')).replace('.nss', '').lower()
                it['_sin_menu'] = str(props.get('in', '')).strip('\'" ').lower()
                it['_scmd'] = str(props.get('cmd', '')).strip('\'" ').lower()
                it['_stip'] = str(props.get('tip', '')).strip('\'" ').lower()
                it['_stype'] = str(it.get('type', '')).lower()
        self._items = items or []
        self._filtered_items = self._items[:]
        self.endResetModel()
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
        painter.setPen(Qt.NoPen); bg = QColor("#0E0E0E") if is_hover else QColor("#121212")
        bg.setAlpha(220 if is_hover else 140); painter.setBrush(bg); painter.drawRoundedRect(rect, 16, 16)
        if is_hover: painter.setPen(QPen(QColor(231, 130, 132, 120), 1.5)); painter.drawRoundedRect(rect, 16, 16)
        
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

        if not has_icon and (svg_content or codes or val):
            pix = render_nss_asset_pixmap(val, size=icon_rect.width() - 12)
            if pix and not pix.isNull():
                target_r = QRect((icon_rect.width() - pix.width())//2 + icon_rect.x(), (icon_rect.height() - pix.height())//2 + icon_rect.y(), pix.width(), pix.height())
                painter.drawPixmap(target_r, pix)
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
            wid = str(props.get('where.id', '')).strip('\'" ')
            if wid:
                draw_part("Modify ID: ", "#e78284", f_bold)
                draw_part(wid, "#ffffff", f_bold)
                if props.get('title'):
                    draw_part(" \u2192 ", "#A0A0A0", f_small)
                    draw_part(props['title'].strip(chr(39)+chr(34)), "#e78284", f_bold)
            elif props.get('find'):
                draw_part("Modify: ", "#e78284", f_bold)
                draw_part(props['find'].strip(chr(39)+chr(34)), "#ffffff", f_bold)
                if props.get('title'):
                    draw_part(" \u2192 ", "#A0A0A0", f_small)
                    draw_part(props['title'].strip(chr(39)+chr(34)), "#e78284", f_bold)
            elif props.get('type'):
                draw_part(f"All {props['type'].title()}s", "#e78284", f_bold)
                if props.get('title'):
                    draw_part(" \u2192 ", "#A0A0A0", f_small)
                    draw_part(props['title'].strip(chr(39)+chr(34)), "#e78284", f_bold)
            else:
                draw_part("Global Rule", "#e78284", f_bold)
        else:
            # item or menu - show title
            raw_title = props.get('title') or props.get('find') or props.get('where') or props.get('cmd') or 'Unnamed'
            t_str = str(raw_title).strip(chr(39)+chr(34))
            file_name = os.path.basename(data.get('file', ''))
            label = f"{file_name}: " if file_name else ""
            draw_part(label, "#e78284", f_bold)
            draw_part(t_str, "#ffffff", f_bold)
            
        if props.get('in'):
            draw_part(" in ", "#A0A0A0", f_small)
            draw_part(props['in'].strip(chr(39)+chr(34)), "#ea999c", f_bold)
        
        # Badges / Summary
        bx = rect.x() + 85; by = rect.y() + 48; acts = []
        if props.get('title'): acts.append(("Renamed", "#838ba7"))
        if props.get('icon') or props.get('image'): acts.append(("Icons", "#8caaee"))
        v = props.get('vis', '').lower()
        if v in ('vis.remove', 'vis.hidden', 'remove', 'hidden'): acts.append(("Hidden", "#e78284"))
        elif v and v != 'normal': acts.append(("Part Hidden", "#ca9ee6"))
        elif v: acts.append((f"Vis: {v}", "#e78284"))
        if 'menu' in props and props.get('menu') is not None: acts.append(("Moved", "#ef9f76"))
        if props.get('pos'): acts.append((f"Pos: {props['pos']}", "#a6d189"))
        if props.get('sep'): acts.append(("Separator", "#e5c890"))
        
        painter.setFont(QFont('Segoe UI Variable Display', 8, QFont.Bold))
        for txt, clr in acts:
            tw = painter.fontMetrics().horizontalAdvance(txt) + 16
            br = QRectF(bx, by, tw, 20)
            bpath = QPainterPath()
            r = br.height() / 2.0
            bpath.addRoundedRect(br, r, r)
            c = QColor(clr)
            bg_col = QColor(c.red(), c.green(), c.blue(), 38)
            border_pen = QPen(QColor(c.red(), c.green(), c.blue(), 100), 1.2)
            text_col = QColor('#c6d0f5')
            painter.fillPath(bpath, bg_col)
            painter.setPen(border_pen)
            painter.drawPath(bpath)
            painter.setPen(text_col)
            painter.drawText(br, Qt.AlignCenter, txt)
            bx += tw + 6
            
        # Source / File
        fp = data.get('file', 'modify.nss'); src = os.path.basename(fp)
        painter.setPen(QColor("#A0A0A0")); painter.setFont(QFont("Inter", 9))
        painter.drawText(rect.x() + 85, rect.y() + 82, f"Source: {src}")
        
        # Buttons Area (Right)
        if is_hover:
            is_local = src.lower() == 'modify.nss'
            btn_x = rect.right() - 45; btn_y = rect.y() + (rect.height() - 36) // 2
            btns = [("\uE107", "#e78284")] if is_local else [] # Delete (only for local)
            btns.append(("\uE104", "#e78284")) # Edit
            
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
                if del_rect.contains(pos):
                    if hasattr(mw, 'delete_rule'): mw.delete_rule(data); return True
                if edit_rect.contains(pos) or rect.contains(pos):
                    is_modify = (data.get('type') == 'modify' or os.path.basename(data.get('file', '')).lower() == 'modify.nss')
                    if is_modify and hasattr(mw, 'edit_rule'): mw.edit_rule(data)
                    elif hasattr(mw, 'edit_item'): mw.edit_item(data)
                    elif hasattr(mw, 'edit_rule'): mw.edit_rule(data)
                    return True
        return super().editorEvent(event, model, opt, index)

class NonScrollComboBox(ModernComboBox):
    def __init__(self, parent=None, context_key=""):
        super().__init__(parent, context_key=context_key)

class CustomMessageBox(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent); self.setWindowTitle("Message"); self.setFixedSize(350, 180); self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint); self.setAttribute(Qt.WA_TranslucentBackground); self.layout = QVBoxLayout(self); self.frame = QFrame(); self.frame.setStyleSheet("QFrame { background-color: #121212; border: 1px solid #2a2a30; border-radius: 15px; }"); self.layout.addWidget(self.frame); self.content_layout = QVBoxLayout(self.frame); self.title_label = QLabel("Title"); self.title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: white; border: none;"); self.msg_label = QLabel(""); self.msg_label.setWordWrap(True); self.msg_label.setStyleSheet("color: #b0b0b0; border: none;"); self.ok_btn = QPushButton("OK"); self.ok_btn.setFixedSize(80, 32); self.ok_btn.setStyleSheet("QPushButton { background-color: #e78284; color: #ffffff; border-radius: 8px; font-weight: bold; } QPushButton:hover { background-color: #e78284; }"); self.ok_btn.clicked.connect(self.accept); self.content_layout.addWidget(self.title_label); self.content_layout.addWidget(self.msg_label); self.content_layout.addWidget(self.ok_btn, 0, Qt.AlignRight)
    def setText(self, text): self.title_label.setText(text)
    def setInformativeText(self, text): self.msg_label.setText(text)



# scan_nss_items moved to later in file with improved parameters

class IDPopupDialog(QDialog):
    def __init__(self, parent_widget, current_menu, current_vis):
        super().__init__(parent_widget); self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint); self.setAttribute(Qt.WA_TranslucentBackground); self.current_menu = current_menu; self.current_vis = current_vis; self.setup_ui()
    def setup_ui(self):
        self.frame = QFrame(self); self.frame.setObjectName("popupFrame")
        self.frame.setStyleSheet("""
            #popupFrame { background-color: #121212; border: 1px solid #2a2a30; border-radius: 14px; } 
            QLabel { color: #8d94a6; font-size: 10px; font-weight: bold; letter-spacing: 0.5px; border: none; background: transparent; padding-left: 2px; } 
        """)
        layout = QVBoxLayout(self); layout.setContentsMargins(0,0,0,0); layout.addWidget(self.frame); cl = QVBoxLayout(self.frame); cl.setContentsMargins(15, 14, 15, 15); cl.setSpacing(10)
        h1 = QLabel("MENU LOCATION"); cl.addWidget(h1)
        self.m_box = ModernComboBox(self, context_key="menu")
        m_opts = ["None", "Main", "Options"]
        for cm in _get_custom_menus_from_nss():
            if cm not in m_opts:
                m_opts.append(cm)
        self.m_box.addItems(m_opts)
        
        curr_m = str(self.current_menu if self.current_menu is not None else '').strip('\'"')
        curr_m_low = curr_m.lower()
        if self.current_menu is None: self.m_box.setCurrentText("None")
        elif not curr_m or curr_m_low in ("main", "menu.main"): self.m_box.setCurrentText("Main")
        elif curr_m_low in ("options", "title.options"): self.m_box.setCurrentText("Options")
        else:
            if curr_m not in [self.m_box.itemText(i) for i in range(self.m_box.count())]:
                self.m_box.addItem(curr_m)
            self.m_box.setCurrentText(curr_m)
        
        cl.addWidget(self.m_box)
        h2 = QLabel("VISIBILITY"); cl.addWidget(h2)
        self.v_box = ModernComboBox(self, context_key="vis"); self.v_box.addItems(["None", "Shift", "Control", "Left Mouse"]); v_map = {"None": None, "Shift": "key.shift()", "Control": "key.control()", "Left Mouse": "key.lbutton()"}
        for i in range(self.v_box.count()):
            if v_map[self.v_box.itemText(i)] == self.current_vis: self.v_box.setCurrentIndex(i); break
        cl.addWidget(self.v_box)
        self.save = QPushButton("Apply Changes"); self.save.setFixedHeight(34)
        self.save.setStyleSheet("QPushButton { background: #e78284; color: #ffffff; font-weight: bold; border-radius: 8px; border: none; margin-top: 5px; } QPushButton:hover { background: #e78284; }")
        self.save.clicked.connect(self.accept); cl.addWidget(self.save)
    def get_values(self):
        m_sel = self.m_box.currentText()
        m_val = None
        if m_sel == "None": m_val = None
        elif m_sel == "Main": m_val = ""
        elif m_sel == "Options": m_val = "options"
        elif m_sel.strip(): m_val = m_sel.strip()
        
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
            p.setPen(Qt.NoPen); p.setBrush(QColor("#e78284")); p.drawEllipse(rect)
        else:
            p.setPen(QPen(QColor(255, 255, 255, 60), 1.5)); p.setBrush(Qt.NoBrush); p.drawEllipse(rect)
        p.end()

class IconSyncButton(QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent); self.setFixedSize(28, 28); self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("QPushButton { background: rgba(255,255,255,0.05); border-radius: 14px; border: 1px solid rgba(255,255,255,0.1); } QPushButton:hover { background: rgba(231, 130, 132, 0.15); border: 1px solid #e78284; }")
    def paintEvent(self, event):
        super().paintEvent(event); p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        c = QColor("#e78284") if self.underMouse() else QColor("#ffffff")
        p.setPen(QPen(c, 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        # Draw a circular arrow (Sync/Reload icon)
        rect = QRectF(7, 7, 14, 14); p.drawArc(rect, 40 * 16, 280 * 16)
        # Draw arrow head
        p.setBrush(c); p.drawPolygon(QPointF(17, 6), QPointF(21, 9), QPointF(17, 12))
        p.end()

class ColorPellet(QPushButton):
    def __init__(self, color, parent=None):
        super().__init__(parent); self.color = QColor(color); self.setFixedSize(22, 22); self.setCursor(Qt.PointingHandCursor)
    def paintEvent(self, event):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        p.setPen(QPen(QColor(255, 255, 255, 30), 2))
        p.setBrush(self.color); p.drawEllipse(2, 2, 18, 18)
        if self.underMouse():
            p.setPen(QPen(Qt.white, 2)); p.setBrush(Qt.NoBrush); p.drawEllipse(1, 1, 20, 20)
        p.end()

class FilterTag(QPushButton):
    def __init__(self, text, color="#e78284", parent=None):
        super().__init__(text, parent)
        self.setCheckable(True)
        self.setFixedHeight(28)
        self.setCursor(Qt.PointingHandCursor)
        self._color = QColor(color)
        self.setFont(QFont('Segoe UI Variable Display', 9, QFont.Bold))
        self.setAttribute(Qt.WA_Hover, True)
        self.setStyleSheet('background: transparent; border: none; outline: none;')
        
    def sizeHint(self):
        fm = self.fontMetrics()
        w = fm.horizontalAdvance(self.text().strip()) + 26
        return QSize(max(w, 58), 28)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)
        
        rect = QRectF(self.rect()).adjusted(1.0, 1.0, -1.0, -1.0)
        path = QPainterPath()
        r = rect.height() / 2.0
        path.addRoundedRect(rect, r, r)
        
        is_checked = self.isChecked()
        is_hover = self.underMouse()
        c = self._color
        
        if is_checked:
            bg_col = c
            border_pen = QPen(c.lighter(115), 1.5)
            text_col = QColor('#ffffff')
        elif is_hover:
            bg_col = QColor(c.red(), c.green(), c.blue(), 75)
            border_pen = QPen(QColor(c.red(), c.green(), c.blue(), 180), 1.5)
            text_col = QColor('#ffffff')
        else:
            bg_col = QColor(c.red(), c.green(), c.blue(), 38)
            border_pen = QPen(QColor(c.red(), c.green(), c.blue(), 90), 1.5)
            text_col = QColor('#c6d0f5')
            
        p.fillPath(path, bg_col)
        p.setPen(border_pen)
        p.drawPath(path)
        
        p.setFont(self.font())
        p.setPen(text_col)
        p.drawText(self.rect(), Qt.AlignCenter, self.text())

class FilterBar(QWidget):
    filter_changed = pyqtSignal(str)
    def __init__(self, tags_with_colors, parent=None):
        super().__init__(parent); self.layout = QHBoxLayout(self); self.layout.setContentsMargins(0, 0, 0, 0); self.layout.setSpacing(8); self.layout.setAlignment(Qt.AlignLeft)
        self.group = QButtonGroup(self); self.group.setExclusive(True)
        for i, (tag, color) in enumerate(tags_with_colors):
            btn = FilterTag(tag, color); self.group.addButton(btn, i); self.layout.addWidget(btn)
            if i == 0: btn.setChecked(True)
        self.group.buttonClicked.connect(lambda b: self.filter_changed.emit(b.text()))

def _resolve_icon_filepath(raw_path, nss_file=None, root_dir=None):
    if not raw_path:
        return None
    root = root_dir or PROJECT_ROOT or (os.path.dirname(os.path.dirname(sys.executable)) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    s = str(raw_path).strip('\'" ')
    m_res = re.match(r'image\.res\s*\(\s*[\'"]?([^\'",)]+)', s, re.I)
    if m_res:
        s = m_res.group(1).strip('\'" ')
    s = re.sub(r'\s*\[[^\]]+\]$', '', s).strip('\'" ')
    if '@app.dir' in s.lower():
        clean = s.replace('@app.dir', '').replace('@APP.DIR', '').lstrip('\\/')
        candidate = os.path.normpath(os.path.join(root, clean))
        if os.path.exists(candidate):
            return candidate
    if os.path.isabs(s) and os.path.exists(s):
        return os.path.normpath(s)
    if nss_file:
        cand1 = os.path.normpath(os.path.join(os.path.dirname(nss_file), s))
        if os.path.exists(cand1):
            return cand1
    cand2 = os.path.normpath(os.path.join(root, s))
    if os.path.exists(cand2):
        return cand2
    cand3 = os.path.normpath(os.path.join(root, 'imports', s))
    if os.path.exists(cand3):
        return cand3
    return None

def _get_or_create_original_icon(resolved_path, root_dir):
    icons_dir = os.path.join(root_dir, 'imports', 'icons')
    orig_dir = os.path.join(icons_dir, 'originals')
    os.makedirs(orig_dir, exist_ok=True)
    try:
        if os.path.normpath(resolved_path).lower().startswith(os.path.normpath(orig_dir).lower()):
            return resolved_path
    except Exception:
        pass
    fname = os.path.basename(resolved_path)
    clean_base = re.sub(r'_[a-f0-9]{6}(\.[a-zA-Z0-9]+)$', r'\1', fname, flags=re.I)
    orig_candidate = os.path.join(orig_dir, clean_base)
    if os.path.exists(orig_candidate):
        return orig_candidate
    stem, ext = os.path.splitext(clean_base)
    for existing in os.listdir(orig_dir):
        if existing.lower().startswith(stem.lower()):
            return os.path.join(orig_dir, existing)
    s_norm = os.path.normpath(resolved_path).lower()
    path_hash = hashlib.md5(s_norm.encode('utf-8')).hexdigest()[:8]
    stem_clean = re.sub(r'_[a-f0-9]{6}$', '', stem, flags=re.I)
    if ext.lower() in ('.exe', '.dll', '.lnk', '.cpl'):
        ext = '.png'
        unique_orig_name = f"{stem_clean}_{path_hash}{ext}"
        target_orig = os.path.join(orig_dir, unique_orig_name)
        if not os.path.exists(target_orig):
            src_img = _load_source_icon_qimage(resolved_path)
            if src_img and not src_img.isNull():
                try:
                    src_img.save(target_orig, "PNG")
                except Exception:
                    pass
        return target_orig if os.path.exists(target_orig) else resolved_path

    unique_orig_name = f"{stem_clean}_{path_hash}{ext}"
    target_orig = os.path.join(orig_dir, unique_orig_name)
    if not os.path.exists(target_orig):
        try:
            shutil.copy2(resolved_path, target_orig)
        except Exception:
            pass
    return target_orig if os.path.exists(target_orig) else resolved_path

def _load_source_icon_qimage(orig_path):
    ext = os.path.splitext(orig_path)[1].lower()
    if ext == '.svg':
        try:
            from PyQt5.QtSvg import QSvgRenderer
            renderer = QSvgRenderer(orig_path)
            sz = renderer.defaultSize()
            if sz.width() <= 0 or sz.height() <= 0:
                sz = QSize(256, 256)
            else:
                scale = max(1, 256 // max(sz.width(), sz.height()))
                sz = QSize(sz.width() * scale, sz.height() * scale)
            img = QImage(sz, QImage.Format_ARGB32)
            img.fill(Qt.transparent)
            p = QPainter(img)
            renderer.render(p)
            p.end()
            return img
        except Exception:
            pass
    elif ext in ('.ico', '.exe', '.dll', '.lnk') or os.path.isdir(orig_path):
        icon = QIcon(orig_path)
        pm = icon.pixmap(256, 256)
        if not pm.isNull():
            return pm.toImage().convertToFormat(QImage.Format_ARGB32)
    img = QImage(orig_path)
    if not img.isNull():
        return img.convertToFormat(QImage.Format_ARGB32)
    icon = QIcon(orig_path)
    pm = icon.pixmap(256, 256)
    if not pm.isNull():
        return pm.toImage().convertToFormat(QImage.Format_ARGB32)
    return None

def _filter_and_save_icon(orig_path, root_dir, mode, colors, subfolder=None):
    src_img = _load_source_icon_qimage(orig_path)
    if not src_img or src_img.isNull():
        return None, None
    orig_base = os.path.basename(orig_path)
    stem = os.path.splitext(orig_base)[0]
    stem_clean = re.sub(r'_[a-f0-9]{6}$', '', stem, flags=re.I)
    hash_payload = f"{stem_clean}_{mode}_{colors}".lower()
    filter_hash = hashlib.md5(hash_payload.encode('utf-8')).hexdigest()[:6]
    dest_name = f"{stem_clean}_{filter_hash}.png"
    icons_dir = os.path.join(root_dir, 'imports', 'icons')
    target_dir = os.path.join(icons_dir, subfolder) if subfolder else icons_dir
    os.makedirs(target_dir, exist_ok=True)
    dest_path = os.path.join(target_dir, dest_name)
    
    rel_sub = f"icons\\{subfolder}\\{dest_name}" if subfolder else f"icons\\{dest_name}"
    nss_path = f"@app.dir\\imports\\{rel_sub}"

    if os.path.exists(dest_path) and os.path.getsize(dest_path) > 0:
        return nss_path, dest_path

    res = QImage(src_img.size(), QImage.Format_ARGB32)
    res.fill(Qt.transparent)
    p = QPainter(res)
    p.setRenderHint(QPainter.Antialiasing)
    p.setRenderHint(QPainter.SmoothPixmapTransform)
    p.drawImage(0, 0, src_img)
    p.setCompositionMode(QPainter.CompositionMode_SourceIn)
    
    w, h = src_img.width(), src_img.height()
    if mode == 'rainbow':
        grad = QLinearGradient(0, 0, 0, h)
        rainbow_stops = [
            (0.0, '#ff3b30'),
            (0.18, '#ff9500'),
            (0.36, '#ffcc00'),
            (0.54, '#34c759'),
            (0.72, '#00c7be'),
            (0.85, '#007aff'),
            (1.0, '#af52de'),
        ]
        for pos, c_hex in rainbow_stops:
            grad.setColorAt(pos, QColor(c_hex))
        p.fillRect(res.rect(), grad)
    elif mode == 'gradient':
        c1 = colors[0] if len(colors) > 0 else '#ffffff'
        c2 = colors[1] if len(colors) > 1 else c1
        grad = QLinearGradient(0, 0, w, h)
        grad.setColorAt(0.0, QColor(c1))
        grad.setColorAt(1.0, QColor(c2))
        p.fillRect(res.rect(), grad)
    else:
        c1 = colors[0] if len(colors) > 0 else '#ffffff'
        p.fillRect(res.rect(), QColor(c1))
    p.end()
    
    try:
        res.save(dest_path, "PNG")
    except Exception:
        import time
        time.sleep(0.05)
        try: res.save(dest_path, "PNG")
        except: pass
    return nss_path, dest_path

class GlobalTintWorker(QObject):
    progress = pyqtSignal(int, int)
    status = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, root, mode_or_color, colors=None, skip_manual_keys=None):
        super().__init__()
        self.root = root
        if isinstance(mode_or_color, str) and mode_or_color in ('rainbow', 'gradient', 'solid'):
            self.mode = mode_or_color
            self.colors = colors or ['#ffffff']
        elif isinstance(mode_or_color, (list, tuple)):
            self.colors = list(mode_or_color)
            self.mode = 'gradient' if len(self.colors) >= 2 and self.colors[0] != self.colors[1] else 'solid'
        else:
            self.mode = 'solid'
            self.colors = [mode_or_color] if mode_or_color else ['#ffffff']
        self.skip_manual_keys = skip_manual_keys or set()

    def run(self):
        try:
            nss_files = []
            sh = os.path.join(self.root, 'shell.nss')
            if os.path.exists(sh):
                nss_files.append(sh)
            for d in ['imports', 'plugins']:
                p = os.path.join(self.root, d)
                if os.path.exists(p):
                    for r, _, fns in os.walk(p):
                        for f in fns:
                            if f.endswith('.nss') and f != 'theme.nss':
                                nss_files.append(os.path.join(r, f))

            pattern = re.compile(r'(?P<key>image|icon)\s*=\s*(?P<val>\[[^\]]+\]|\'[^\']*\'|\"[^\"]*\"|image\.res\([^)]*\)|[^\s,;)]+)', re.I)
            
            file_matches = []
            for fp in nss_files:
                content = read_file(fp)
                if not content:
                    continue
                for m in pattern.finditer(content):
                    val_raw = m.group('val').strip('\'"[] ')
                    if val_raw.startswith('<svg') or val_raw.startswith('\\u') or val_raw.startswith('0x'):
                        continue
                    if any(ext in val_raw.lower() for ext in ['.png', '.ico', '.svg', '.jpg', '.bmp', '.cur', 'image.', '\\', '/']):
                        resolved = _resolve_icon_filepath(val_raw, fp, self.root)
                        if resolved and os.path.exists(resolved) and not os.path.isdir(resolved):
                            file_matches.append((fp, m, val_raw, resolved))

            total = max(len(file_matches), 1)
            processed = 0
            file_replacements = {}

            for fp, m, val_raw, resolved in file_matches:
                fname = os.path.basename(fp)
                self.status.emit(f"Filtering {fname}... ({processed + 1}/{total})")
                
                orig = _get_or_create_original_icon(resolved, self.root)
                nss_path, _ = _filter_and_save_icon(orig, self.root, self.mode, self.colors)
                if nss_path:
                    if fp not in file_replacements:
                        file_replacements[fp] = []
                    file_replacements[fp].append((m.start('val'), m.end('val'), f"'{nss_path}'"))
                
                processed += 1
                self.progress.emit(processed, total)

            for fp, replacements in file_replacements.items():
                replacements.sort(key=lambda x: x[0], reverse=True)
                content = read_file(fp)
                for start, end, new_val in replacements:
                    content = content[:start] + new_val + content[end:]
                safe_file_write(fp, content)

            self.progress.emit(total, total)
        except Exception as e:
            print(f"[GlobalTintWorker] Error: {e}")
        finally:
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
        lbl.setText("\u2726"); lbl.setStyleSheet("color: rgba(231, 130, 132, 0.3); font-size: 18px; background: rgba(255,255,255,0.03); border-radius: 10px; border: 1px solid rgba(255,255,255,0.05);")
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
    lbl.setText("\uE12B"); lbl.setFont(QFont('Segoe MDL2 Assets', 18)); lbl.setStyleSheet("color: #e78284; background: transparent;")
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
        super().__init__(parent); self.data = data; self.setObjectName("ruleCard"); self.setFixedHeight(100); self.setStyleSheet("#ruleCard { background-color: #121212; border-radius: 12px; border: 1px solid rgba(255, 255, 255, 0.05); } #ruleCard:hover { background-color: #0E0E0E; border: 1px solid rgba(231, 130, 132, 0.4); }")
        self.main_layout = QHBoxLayout(self); self.main_layout.setContentsMargins(15, 10, 15, 10); self.main_layout.setSpacing(15); self.main_layout.setAlignment(Qt.AlignVCenter)
        
        self.icon_label = QLabel(self); self.icon_label.setFixedSize(40, 40); self.icon_label.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(self.icon_label)
        
        self.sb = QPushButton("\uE117", self); self.sb.setFixedSize(24, 24); self.sb.setCursor(Qt.PointingHandCursor); self.sb.setToolTip("Sync with Global Theme")
        self.sb.setFont(QFont('Segoe MDL2 Assets', 10))
        self.sb.setStyleSheet("QPushButton { background: transparent; border: none; color: #b0b0b0; } QPushButton:hover { color: #e78284; }")
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
        self.title_label.setText(f"{typ}: <span style='color: #e78284;'>{title}</span>")
        fname = os.path.basename(self.data.get('file', 'unknown'))
        self.desc_label.setText(f"Source: <span style='color: #ea999c;'>{fname}</span>" + (f" \u2022 Cmd: <span style='color: #b0b0b0;'>{data['cmd'][:50]}...</span>" if 'cmd' in data else ""))
        
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
            sb.setStyleSheet("QPushButton { background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); border-radius: 12px; color: #b0b0b0; font-family: 'Segoe MDL2 Assets'; font-size: 11px; } QPushButton:hover { background: rgba(231, 130, 132, 0.1); color: #e78284; border-color: #e78284; }")
            sb.clicked.connect(self.sync_to_theme)
            self.c_lay.addWidget(sb)

        btn_style = "QPushButton { background: rgba(255, 255, 255, 0.08); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 19px; color: #ffffff; font-family: 'Segoe MDL2 Assets'; font-size: 16px; } QPushButton:hover { background: rgba(255, 255, 255, 0.15); border: 1px solid #e78284; color: white; }"
        self.ab.setFixedSize(38, 38); self.ab.setStyleSheet(btn_style.replace("#ffffff", "#e78284")); self.ab.setText("\uE72B")
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
    def __init__(self, id_text, formatted_name, initial_menu=None, initial_vis=None, initial_hidden=False, custom_props=None, parent=None):
        super().__init__(parent)
        self.id_text = id_text
        self.default_name = id_text.replace("id.", "").replace("_", " ").title()
        self.formatted_name = formatted_name or self.default_name
        self.menu = initial_menu
        self.vis = initial_vis
        self.is_hidden = initial_hidden
        self.custom_props = custom_props.copy() if custom_props else {}
        self.setFixedSize(240, 60)
        self.setObjectName("idEntryWidget")
        self.update_style()
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 0, 10, 0)
        
        self.label = QLabel(self.formatted_name)
        self.label.setStyleSheet("font-size: 13px; color: white; background: transparent;")
        layout.addWidget(self.label, 1)
        
        btn_c = QFrame()
        btn_c.setStyleSheet("background: rgba(0,0,0,0.15); border-radius: 12px; padding: 2px;")
        bl = QHBoxLayout(btn_c)
        bl.setContentsMargins(2, 2, 2, 2)
        bl.setSpacing(2)
        
        self.h_btn = QPushButton("\uE7B3")
        self.h_btn.setFixedSize(24, 24)
        self.h_btn.setCursor(Qt.PointingHandCursor)
        self.h_btn.clicked.connect(self.toggle_hide)
        bl.addWidget(self.h_btn)
        
        self.e_btn = QPushButton("\uE104")
        self.e_btn.setFixedSize(24, 24)
        self.e_btn.setCursor(Qt.PointingHandCursor)
        self.e_btn.setStyleSheet("QPushButton { background: transparent; border: none; border-radius: 10px; color: #b0b0b0; font-family: 'Segoe MDL2 Assets'; } QPushButton:hover { color: #e78284; }")
        self.e_btn.clicked.connect(self.show_popup)
        bl.addWidget(self.e_btn)
        
        layout.addWidget(btn_c)
        self.update_label_state()

    def update_style(self):
        has_custom = bool(self.menu or self.vis or self.custom_props)
        self.setStyleSheet(f"#idEntryWidget {{ background-color: rgba(255, 255, 255, 0.05); border-radius: 15px; border: 1px solid {'rgba(231, 130, 132, 0.4)' if has_custom else 'rgba(255, 255, 255, 0.03)'}; }} #idEntryWidget:hover {{ background-color: rgba(255, 255, 255, 0.08); border: 1px solid rgba(231, 130, 132, 0.2); }}")

    def update_label_state(self):
        self.label.setGraphicsEffect(None)
        self.label.setStyleSheet(f"font-size: 13px; color: {'#555555' if self.is_hidden else 'white'}; background: transparent;")
        self.h_btn.setText("\uED1A" if self.is_hidden else "\uE7B3")
        self.h_btn.setToolTip("Unhide" if self.is_hidden else "Hide")
        self.h_btn.setStyleSheet(f"QPushButton {{ background: {'#e78284' if self.is_hidden else 'transparent'}; border: none; border-radius: 10px; color: {'#1e2030' if self.is_hidden else '#b0b0b0'}; font-family: 'Segoe MDL2 Assets'; font-size: 12px; }} QPushButton:hover {{ color: {'#1e2030' if self.is_hidden else '#e78284'}; }}")

    def toggle_hide(self):
        self.is_hidden = not self.is_hidden
        if getattr(self, 'custom_props', None):
            if self.is_hidden:
                self.custom_props['vis'] = 'vis.remove'
                self.vis = 'vis.remove'
            else:
                self.custom_props.pop('vis', None)
                self.vis = None
        self.update_label_state()
        self.changed.emit()

    def show_popup(self):
        initial_props = getattr(self, 'custom_props', {}).copy()
        initial_props['where.id'] = self.id_text
        if 'menu' not in initial_props and self.menu:
            initial_props['menu'] = self.menu
        if 'vis' not in initial_props and self.vis:
            initial_props['vis'] = self.vis
        if 'title' not in initial_props:
            initial_props['title'] = self.formatted_name if self.formatted_name != self.default_name else ''

        parent_window = self.window()
        file_path = getattr(parent_window, 'filepath', '')
        data = {
            'type': f'ID ({self.id_text})',
            'file': file_path,
            'props': initial_props
        }

        d = ImportEditorDialog(data, parent_window)
        if d.exec_():
            new_props = d.get_props()
            new_props['where.id'] = self.id_text
            clean_id_name = self.id_text.replace("id.", "").strip()
            first_word = clean_id_name.split('_')[0].strip().lower()
            if first_word:
                new_props['find'] = f"'{first_word}'"
            self.custom_props = new_props
            self.menu = new_props.get('menu')
            self.vis = new_props.get('vis')
            raw_title = str(new_props.get('title', '')).strip('\'"')
            if raw_title:
                self.formatted_name = raw_title
            else:
                self.formatted_name = self.default_name
            self.label.setText(self.formatted_name)
            
            v_low = str(self.vis or '').lower()
            self.is_hidden = ('remove' in v_low or 'hidden' in v_low)
            self.update_label_state()
            self.update_style()
            self.changed.emit()

class ModificationRuleCard(QFrame):
    def __init__(self, data, parent=None):
        super().__init__(parent); self.data = data; self.setObjectName("ruleCard"); self.setFixedHeight(100); self.setStyleSheet("#ruleCard { background-color: #121212; border-radius: 12px; border: 1px solid rgba(255, 255, 255, 0.05); } #ruleCard:hover { background-color: #0E0E0E; border: 1px solid rgba(231, 130, 132, 0.4); }")
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
        btn_style = "QPushButton { background: rgba(255, 255, 255, 0.08); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 19px; color: #ffffff; font-family: 'Segoe MDL2 Assets'; font-size: 16px; } QPushButton:hover { background: rgba(255, 255, 255, 0.15); border: 1px solid #e78284; color: white; }"
        for b in (self.eb, self.db): 
            b.setFixedSize(38, 38); b.setStyleSheet(btn_style); b.setCursor(Qt.PointingHandCursor); self.bl.addWidget(b)
        self.eb.setText("\uE104"); self.db.setText("\uE107")
        self.db.setStyleSheet(self.db.styleSheet() + "QPushButton:hover { color: #e78284; border-color: #e78284; }")
        self.main_layout.addWidget(self.bl_w)
        self.update_ui()
        
    def update_ui(self):
        data = self.data; val = data.get('image') or data.get('icon') or ''
        cmd_val = data.get('cmd') or data.get('path') or data.get('find') or ''
        _update_label_asset(self.il, val, cmd=cmd_val)
        
        # Build a friendly Target Title
        target = "Global Rule"
        if data.get('where.id'): target = f"ID: <span style='color: #e78284;'>{data['where.id'].strip(chr(39)+chr(34))}</span>"
        elif data.get('find'): target = f"Modify: <span style='color: #e78284;'>{data['find'].strip(chr(39)+chr(34))}</span>"
        elif data.get('where'): target = f"Rule: <span style='color: #e78284;'>{data['where'].strip(chr(39)+chr(34))}</span>"
        elif data.get('type'): target = f"All <span style='color: #ea999c;'>{data['type'].title()}s</span>"
        if data.get('in'): target += f" <span style='color: #333333;'>in</span> <span style='color: #b0b0b0;'>{data['in'].strip(chr(39)+chr(34))}</span>"
        self.tl.setText(target)
        
        # Build a friendly Actions Summary
        acts = []
        if data.get('title'): acts.append(f"Rename to <span style='color: #ffffff;'>'{data['title'].strip(chr(39)+chr(34))}'</span>")
        
        v = data.get('vis', '').lower()
        if 'remove' in v or 'hidden' in v: acts.append("<span style='color: #e78284;'>Hidden</span>")
        elif v and v != 'normal': acts.append(f"Vis: <span style='color: #e78284;'>{v}</span>")
        
        if 'menu' in data and data.get('menu') is not None:
            m = str(data.get('menu', '')).strip('\'"')
            if not m or m.lower() in ("main", "menu.main"):
                acts.append("Move to <span style='color: #e78284;'>Main</span>")
            elif m.lower() in ("options", "title.options"):
                acts.append("Move to <span style='color: #e78284;'>Options</span>")
            else:
                m_name = m.split('.')[-1].title() if '.' in m else m.title()
                acts.append(f"Move to <span style='color: #e78284;'>{m_name}</span>")
            
        if data.get('pos'): acts.append(f"Pos: <span style='color: #e78284;'>{data['pos']}</span>")
        if any(k in data for k in ('icon', 'image')): acts.append("<span style='color: #e78284;'>New Icon</span>")
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
            sb.setStyleSheet("QPushButton { background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); border-radius: 12px; color: #b0b0b0; font-family: 'Segoe MDL2 Assets'; font-size: 11px; } QPushButton:hover { background: rgba(231, 130, 132, 0.1); color: #e78284; border-color: #e78284; }")
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

def save_local_icon(source_path, tint_color, tint_enabled, subfolder=None, mode=None):
    root = PROJECT_ROOT or (os.path.dirname(os.path.dirname(sys.executable)) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    orig = _get_or_create_original_icon(source_path, root)
    if not tint_enabled:
        icons_dir = os.path.join(root, 'imports', 'icons')
        target_dir = os.path.join(icons_dir, subfolder) if subfolder else icons_dir
        os.makedirs(target_dir, exist_ok=True)
        name, ext = os.path.splitext(os.path.basename(orig))
        dest_name = f"{name}{ext}"
        dest_path = os.path.join(target_dir, dest_name)
        if not os.path.exists(dest_path) or not os.path.samefile(orig, dest_path):
            try:
                shutil.copy2(orig, dest_path)
            except Exception:
                pass
        rel_path = f"icons\\{subfolder}\\{dest_name}" if subfolder else f"icons\\{dest_name}"
        return f"@app.dir\\imports\\{rel_path}", dest_path

    if mode is None:
        if str(tint_color).lower() == 'rainbow':
            mode = 'rainbow'
            colors = []
        elif isinstance(tint_color, (list, tuple)) and len(tint_color) >= 2:
            mode = 'gradient'
            colors = list(tint_color)
        else:
            mode = 'solid'
            colors = [tint_color] if isinstance(tint_color, str) else ['#ffffff']
    else:
        colors = tint_color if isinstance(tint_color, (list, tuple)) else [tint_color]

    nss_path, dest_path = _filter_and_save_icon(orig, root, mode, colors, subfolder=subfolder)
    return nss_path, dest_path

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

_THEME_COLOR_CACHE = ['#e78284', '#ea999c']
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
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing); p.setRenderHint(QPainter.SmoothPixmapTransform); p.setRenderHint(QPainter.TextAntialiasing)
        metadata = getattr(GlyphBrowserDialog, '_glyphs_cache', None)
        if not metadata:
            from utils import get_glyphs_data
            data = get_glyphs_data() or {}
            metadata = {}
            for k, itm in data.items():
                try: code_int = int(k, 16)
                except ValueError: code_int = k
                metadata[code_int] = itm
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
                        font = QFont(self.font_families[i] if i < len(self.font_families) else self.font_family)
                        font.setPixelSize(font_size)
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
            cb = QCheckBox(); cb.setStyleSheet("QCheckBox::indicator { width: 18px; height: 18px; border-radius: 4px; border: 2px solid #333333; background: transparent; } QCheckBox::indicator:checked { background: #e78284; border: 2px solid #e78284; }"); cb.setChecked(False); cb.setProperty("item_idx", idx); self.checkboxes.append(cb); card_lay.addWidget(cb)
            val = item['props'].get('image') or item['props'].get('icon') or ''; codes = _extract_glyph_codes(val); colors = _extract_all_colors(val)
            prev = GlyphPreviewLabel(codes, size=24, font_family=NILESOFT_FONT_FAMILY, colors=colors); prev.setFixedSize(36, 36); card_lay.addWidget(prev)
            title = QLabel(item['props'].get('title', 'Unknown Item')); title.setStyleSheet("color: white; font-weight: bold; font-size: 14px;"); card_lay.addWidget(title)
            card_lay.addStretch(); self.scroll_layout.addWidget(card)
        scroll.setWidget(self.scroll_widget); cl.addWidget(scroll)
        btns = QHBoxLayout(); btns.addStretch()
        skip_all = QPushButton("Skip All"); skip_all.clicked.connect(self.reject); skip_all.setStyleSheet("background: #2a2a30; color: white; padding: 10px 20px; border-radius: 10px; font-weight: bold;")
        sync_btn = QPushButton("Sync Selected"); sync_btn.clicked.connect(self.accept); sync_btn.setStyleSheet("background: #e78284; color: #ffffff; padding: 10px 20px; border-radius: 10px; font-weight: bold;")
        btns.addWidget(skip_all); btns.addWidget(sync_btn); cl.addLayout(btns)
    def get_selected_indices(self): return [cb.property("item_idx") for cb in self.checkboxes if cb.isChecked()]

class AddSVGDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent); self.setWindowTitle("Add Custom SVG Icon"); self.setMinimumWidth(480); self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint); self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet("QToolTip { background-color: #1e1e24; color: #ffffff; border: 1px solid rgba(231, 130, 132, 0.6); border-radius: 8px; padding: 6px 12px; }")
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
        self.name_inp = PillLineEdit("e.g. Discord")
        cl.addWidget(self.name_inp)

        cl.addWidget(QLabel("Search Keywords (comma-separated):"))
        self.kw_inp = PillLineEdit("e.g. chrome, refresh, download")
        cl.addWidget(self.kw_inp)

        cl.addWidget(QLabel("SVG Content or Path(s):"))
        self.svg_inp = QTextEdit()
        self.svg_inp.setPlaceholderText("Paste raw <svg>...</svg> code or d=\"...\" path string")
        self.svg_inp.setFixedHeight(105)
        cl.addWidget(self.svg_inp)

        btns = QHBoxLayout()
        cancel_btn = QPushButton("Cancel"); cancel_btn.setCursor(Qt.PointingHandCursor); cancel_btn.setStyleSheet("QPushButton { background: #2a2a30; color: #ffffff; border-radius: 10px; padding: 8px 16px; } QPushButton:hover { background: #45475a; }")
        cancel_btn.clicked.connect(self.reject)
        save_btn = QPushButton("Add Icon"); save_btn.setCursor(Qt.PointingHandCursor); save_btn.setStyleSheet("QPushButton { background: #e78284; color: #ffffff; border-radius: 10px; padding: 8px 16px; font-weight: bold; } QPushButton:hover { background: #ea999c; }")
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
        self.search_inp = PillSearchInput("Search glyphs or keywords...")
        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.setInterval(40)
        self.search_timer.timeout.connect(lambda: self.filter_glyphs(self.search_inp.text()))
        self.search_inp.textChanged.connect(lambda: self.search_timer.start())
        top_row.addWidget(self.search_inp, 1)

        self.upload_img_btn = UploadIconButton()
        self.upload_img_btn.clicked.connect(self._upload_custom_icon)
        top_row.addWidget(self.upload_img_btn)
        
        self.preview_frame = GlyphPreviewFrame()
        self.preview_layout = QVBoxLayout(self.preview_frame)
        self.preview_layout.setContentsMargins(0, 0, 0, 0)
        self._update_preview()
        top_row.addWidget(self.preview_frame)
        self.sel_label = QLabel(self._selection_text()); self.sel_label.setStyleSheet("color: #e78284; font-size: 12px; font-weight: bold;"); self.sel_label.setFixedWidth(110)
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
        self.glyph_list.setStyleSheet("QListWidget { background: transparent; border: none; outline: none; } QListWidget::item { background: rgba(255,255,255,0.04); border-radius: 8px; margin: 2px; } QListWidget::item:hover { background: rgba(255,255,255,0.1); } QListWidget::item:selected { background: rgba(231, 130, 132, 0.2); border: 1px solid #e78284; }")
        self.glyph_list.itemClicked.connect(self.on_item_clicked)
        self.glyph_list.verticalScrollBar().valueChanged.connect(self._on_scroll)
        cl.addWidget(self.glyph_list, 1)

        self._current_items = []
        self._rendered_count = 0
        self._batch_size = 80
        self._populate_list(self.all_codes)
        btns = QHBoxLayout()
        color_area = QHBoxLayout(); color_area.setSpacing(8)
        theme_cs = _get_theme_glyph_colors()
        self.color1_enabled = ModernCheckBox()
        self.color1_enabled.setToolTip("Enable color for glyph 1")
        self.color1_enabled.setChecked(self.glyph_colors[0] is not None)
        self.color1_btn = ColorCircleButton(self.glyph_colors[0] or theme_cs[0], tooltip="Color for Glyph 1")
        self.color1_btn.setEnabled(self.color1_enabled.isChecked())
        self.color1_btn.colorSelected.connect(lambda hex_c: self._on_glyph_color_selected(0, hex_c))
        self.color1_enabled.stateChanged.connect(lambda s: (self.color1_btn.setEnabled(bool(s)), self._on_color_toggle(0, bool(s))))
        color_area.addWidget(self.color1_enabled); color_area.addWidget(self.color1_btn)
        c1l = QLabel("G1"); c1l.setStyleSheet("color: #c6d0f5; font-size: 11px; font-weight: bold;"); color_area.addWidget(c1l)
        color_area.addSpacing(10)
        self.color2_enabled = ModernCheckBox()
        self.color2_enabled.setToolTip("Enable color for glyph 2")
        self.color2_enabled.setChecked(self.glyph_colors[1] is not None)
        self.color2_btn = ColorCircleButton(self.glyph_colors[1] or theme_cs[1], tooltip="Color for Glyph 2")
        self.color2_btn.setEnabled(self.color2_enabled.isChecked())
        self.color2_btn.colorSelected.connect(lambda hex_c: self._on_glyph_color_selected(1, hex_c))
        self.color2_enabled.stateChanged.connect(lambda s: (self.color2_btn.setEnabled(bool(s)), self._on_color_toggle(1, bool(s))))
        color_area.addWidget(self.color2_enabled); color_area.addWidget(self.color2_btn)
        c2l = QLabel("G2"); c2l.setStyleSheet("color: #c6d0f5; font-size: 11px; font-weight: bold;"); color_area.addWidget(c2l)
        btns.addLayout(color_area)
        btns.addStretch()
        clear_btn = PillPushButton("Clear", "reset", height=34)
        clear_btn.clicked.connect(self.clear_selection)
        cancel_btn = PillPushButton("Cancel", "secondary", height=34)
        cancel_btn.clicked.connect(self.reject)
        ok_btn = PillPushButton("Apply", "primary", height=34)
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
        if hasattr(btn, 'set_color'):
            btn.set_color(color_hex)
        else:
            btn.setStyleSheet(f"background-color: {color_hex};")

    def _on_glyph_color_selected(self, idx, hex_c):
        self.glyph_colors[idx] = hex_c
        self._update_preview()

    def _on_color_toggle(self, idx, enabled):
        if enabled:
            if self.glyph_colors[idx] is None:
                def_cs = _get_theme_glyph_colors()
                self.glyph_colors[idx] = def_cs[idx]
                btn = self.color1_btn if idx == 0 else self.color2_btn
                self._update_color_btn(btn, self.glyph_colors[idx])
        else:
            self.glyph_colors[idx] = None
        self._update_preview()

    def _open_color_picker(self, idx):
        btn = self.color1_btn if idx == 0 else self.color2_btn
        btn.click()

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
            pw = GlyphPreviewLabel(self.selected, size=36, font_family=NILESOFT_FONT_FAMILY, colors=[c1, c2], font_families=font_families)
            pw.setStyleSheet("background: transparent; border: none;")
            pw.setFixedSize(50, 36)
            self.preview_layout.addWidget(pw)
            pw.show()
        else:
            pl = QLabel("\u2726")
            pl.setAlignment(Qt.AlignCenter)
            pl.setStyleSheet("color: #444444; font-size: 20px; background: transparent; border: none;")
            self.preview_layout.addWidget(pl)
            pl.show()
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
        self.toggle.setStyleSheet("QCheckBox { color: #ffffff; font-size: 13px; } QCheckBox::indicator { width: 18px; height: 18px; border-radius: 4px; border: 1px solid #45475a; background: #2a2a30; } QCheckBox::indicator:checked { background: #e78284; border: 1px solid #e78284; }")
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
        ok = QPushButton("Apply"); ok.setStyleSheet("QPushButton { background: #e78284; color: #ffffff; border-radius: 10px; padding: 8px 16px; font-weight: bold; } QPushButton:hover { background: #ea999c; }")
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
        self.setMinimumWidth(570)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet("QToolTip { background-color: #1e1e24; color: #ffffff; border: 1px solid rgba(231, 130, 132, 0.6); border-radius: 8px; padding: 6px 12px; font-family: 'Segoe UI Variable Display'; font-size: 12px; font-weight: bold; }")
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
            #mainFrame { background-color: #0E0E0E; border: 1px solid #1e2130; border-radius: 20px; } 
            QLabel { color: #ffffff; font-size: 12px; } 
            QLineEdit { background-color: #121212; border: 1px solid #242738; border-radius: 10px; padding: 7px 12px; color: #ffffff; selection-background-color: #ea999c; font-size: 12px; } 
            QLineEdit:focus { border: 1px solid #ea999c; }
            QPushButton#saveBtn { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ea999c, stop:1 #e78284); color: #ffffff; border-radius: 10px; padding: 8px 20px; font-weight: bold; font-size: 12px; border: none; } 
            QPushButton#saveBtn:hover { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ff4770, stop:1 #e01b44); }
            QPushButton#cancelBtn { background-color: #121212; border: 1px solid #282b3c; color: #d1d5db; border-radius: 10px; padding: 8px 18px; font-size: 12px; }
            QPushButton#cancelBtn:hover { background-color: #0E0E0E; color: #ffffff; }
        """)
        layout = QVBoxLayout(self); layout.setContentsMargins(0, 0, 0, 0); layout.addWidget(self.mf)
        cl = QVBoxLayout(self.mf); cl.setContentsMargins(20, 20, 20, 20); cl.setSpacing(14)
        
        # Header Row
        if not self.embed_mode:
            h_row = QHBoxLayout()
            ic_badge = QLabel("\uE70F")
            ic_badge.setFixedSize(36, 36)
            ic_badge.setFont(QFont("Segoe MDL2 Assets", 14))
            ic_badge.setAlignment(Qt.AlignCenter)
            ic_badge.setStyleSheet("background: rgba(234, 153, 156, 0.15); border: 1px solid #ea999c; border-radius: 10px; color: #ea999c;")
            h_row.addWidget(ic_badge)

            h_titles = QVBoxLayout()
            h_titles.setSpacing(2)
            t1 = QLabel(f"Edit {self.data.get('type', 'Item').title()}"); t1.setStyleSheet("font-size: 16px; font-weight: bold; color: #ffffff;")
            t2 = QLabel("Adjust properties and appearance."); t2.setStyleSheet("font-size: 11px; color: #8d94a6;")
            h_titles.addWidget(t1); h_titles.addWidget(t2)
            h_row.addLayout(h_titles, 1)

            close_btn = QPushButton("\uE711")
            close_btn.setFixedSize(30, 30)
            close_btn.setFont(QFont("Segoe MDL2 Assets", 10))
            close_btn.setCursor(Qt.PointingHandCursor)
            close_btn.setStyleSheet("QPushButton { background: #121212; border: 1px solid #282b3c; border-radius: 8px; color: #9ca3af; } QPushButton:hover { background: rgba(234, 153, 156, 0.2); border: 1px solid #ea999c; color: #ffffff; }")
            close_btn.clicked.connect(self.reject)
            h_row.addWidget(close_btn)
            cl.addLayout(h_row)
        
        ag = QFrame(); ag.setObjectName("importGroup"); ag.setStyleSheet("#importGroup { background: transparent; } #importGroup > QLabel, #importGroup QLabel { font-size: 13px; font-weight: bold; color: #ffffff; background: transparent; padding: 0; border: none; }"); al = QGridLayout(ag); al.setVerticalSpacing(12); al.setHorizontalSpacing(14); al.setContentsMargins(0, 0, 0, 0); cl.addWidget(ag)
        
        self.t_inp = PillLineEdit("Enter a title")
        self.t_inp.setText(self.props.get('title', '').strip('\'\"'))
        al.addWidget(QLabel("Title:"), 0, 0, Qt.AlignLeft | Qt.AlignVCenter); al.addWidget(self.t_inp, 0, 1)
        
        ic_row = QHBoxLayout()
        ic_row.setSpacing(8)
        
        self.ic_prev_lbl = AnimatedGlowPreviewLabel()
        self.ic_prev_lbl.clicked.connect(self._open_glyph_browser)
        
        self.c_container = QWidget()
        self.c_container.setStyleSheet("background: transparent; border: none;")
        self.c_lay = QHBoxLayout(self.c_container)
        self.c_lay.setContentsMargins(0, 0, 0, 0)
        self.c_lay.setSpacing(6)
        self.c_lay.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        
        self.ic_inp = PillLineEdit("Icon Path")
        self.ic_inp.setText(self.props.get('icon') or self.props.get('image') or '')
        self.ic_inp.textChanged.connect(self._update_colors_ui)
        self.ic_inp.textChanged.connect(lambda t: self.ic_prev_lbl.set_asset(t))
        
        btn_action_style = """
            QPushButton {
                background: #121212;
                border: 1px solid #242738;
                border-radius: 10px;
                color: #9ca3af;
                padding: 0;
            }
            QPushButton:hover {
                background: rgba(234, 153, 156, 0.2);
                border: 1px solid #ea999c;
                color: #ffffff;
            }
        """

        self.ic_inherit = QPushButton("\uE777")
        self.ic_inherit.setFont(QFont('Segoe MDL2 Assets', 12))
        self.ic_inherit.setFixedSize(34, 34)
        self.ic_inherit.setCursor(Qt.PointingHandCursor)
        self.ic_inherit.setToolTip("Inherit Icon from Target Command/File")
        self.ic_inherit.setStyleSheet(btn_action_style)
        self.ic_inherit.clicked.connect(self._inherit_icon)

        self.ic_remove = QPushButton("\uE74D")
        self.ic_remove.setFont(QFont('Segoe MDL2 Assets', 12))
        self.ic_remove.setFixedSize(34, 34)
        self.ic_remove.setCursor(Qt.PointingHandCursor)
        self.ic_remove.setToolTip("Remove Icon")
        self.ic_remove.setStyleSheet("""
            QPushButton {
                background: #121212;
                border: 1px solid #242738;
                border-radius: 10px;
                color: #9ca3af;
                padding: 0;
            }
            QPushButton:hover {
                background: rgba(255, 50, 50, 0.25);
                border: 1px solid #ff4444;
                color: #ffffff;
            }
        """)
        self.ic_remove.clicked.connect(lambda: self.ic_inp.setText(""))

        ic_row.addWidget(self.ic_prev_lbl)
        ic_row.addWidget(self.c_container)
        ic_row.addWidget(self.ic_inp, 1)
        if not self.embed_mode:
            ic_row.addWidget(self.ic_inherit)
            ic_row.addWidget(self.ic_remove)
        al.addWidget(QLabel("Icon / Image:"), 1, 0, Qt.AlignLeft | Qt.AlignVCenter); al.addLayout(ic_row, 1, 1)
        self.ic_prev_lbl.set_asset(self.ic_inp.text()); self._update_colors_ui()

        self.vis_widget = VisibilityWidget()
        self.vis_widget.set_value(str(self.props.get('vis', '')))
        al.addWidget(QLabel("Visibility:"), 2, 0, Qt.AlignLeft | Qt.AlignVCenter); al.addWidget(self.vis_widget, 2, 1)

        self.type_widget = TypeWidget()
        self.type_widget.set_value(self.props.get('type', ''))
        al.addWidget(QLabel("Show in:"), 3, 0, Qt.AlignLeft | Qt.AlignVCenter); al.addWidget(self.type_widget, 3, 1)
        
        m_opts = ["None", "Main", "Options"]
        for cm in _get_custom_menus_from_nss():
            if cm not in m_opts:
                m_opts.append(cm)
        self.m_box = ModernComboBox(context_key="menu"); self.m_box.addItems(m_opts)
        self.m_box.setFixedWidth(150)
        
        curr_m = str(self.props.get('menu', '')).strip('\'"')
        curr_m_low = curr_m.lower()
        if 'menu' not in self.props: self.m_box.setCurrentText("None")
        elif not curr_m or curr_m_low in ("main", "menu.main"): self.m_box.setCurrentText("Main")
        elif curr_m_low in ("options", "title.options"): self.m_box.setCurrentText("Options")
        else:
            if curr_m not in [self.m_box.itemText(i) for i in range(self.m_box.count())]:
                self.m_box.addItem(curr_m)
            self.m_box.setCurrentText(curr_m)
        
        self.p_box = ModernComboBox(context_key="pos"); self.p_box.addItems(ModifyRuleEditorDialog.POS_OPTIONS)
        self.p_box.setFixedWidth(150)
        p_val = str(self.props.get('pos', '')).strip('\'"')
        (self.p_box.setCurrentText(p_val) if p_val in ModifyRuleEditorDialog.POS_OPTIONS else (self.p_box.addItem(p_val), self.p_box.setCurrentText(p_val)))

        self.sep_box = ModernComboBox(context_key="sep"); self.sep_box.addItems(["None", "Before", "After", "Both"])
        self.sep_box.setFixedWidth(150)
        curr_sep = str(self.props.get('sep', '')).strip('\'"')
        if curr_sep:
            if curr_sep.lower() in ('true', '1'): self.sep_box.setCurrentText("Before")
            else: self.sep_box.setCurrentText(curr_sep.title())
        else:
            self.sep_box.setCurrentText("None")

        pos_move_row = QHBoxLayout()
        pos_move_row.setContentsMargins(0, 0, 0, 0)
        pos_move_row.setSpacing(14)
        pos_move_row.addWidget(self.m_box)
        
        pos_lbl = QLabel("Position:")
        pos_move_row.addWidget(pos_lbl)
        pos_move_row.addWidget(self.p_box)
        pos_move_row.addStretch()

        al.addWidget(QLabel("Move to:"), 4, 0, Qt.AlignLeft | Qt.AlignVCenter)
        al.addLayout(pos_move_row, 4, 1, Qt.AlignLeft | Qt.AlignVCenter)

        al.addWidget(QLabel("Separator:"), 5, 0, Qt.AlignLeft | Qt.AlignVCenter)
        al.addWidget(self.sep_box, 5, 1, Qt.AlignLeft | Qt.AlignVCenter)

        if not self.embed_mode:
            btns = QHBoxLayout()
            c = PillPushButton("Cancel", "secondary", height=34)
            c.setFixedWidth(85)
            c.clicked.connect(self.reject)
            s = PillPushButton("Save Changes", "primary", height=34)
            s.setFixedWidth(110)
            s.clicked.connect(self.accept)
            btns.addStretch()
            btns.addWidget(c)
            btns.addWidget(s)
            cl.addLayout(btns)
            
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
            it = self.c_lay.takeAt(0)
            if it.widget(): it.widget().deleteLater()
        colors = _extract_all_colors(self.ic_inp.text())
        theme_cs = _get_theme_glyph_colors()
        codes = _extract_glyph_codes(self.ic_inp.text())
        num_pellets = len(codes) if codes else (len(colors) if colors else 1)
        for i in range(min(max(num_pellets, len(colors)), 2)):
            c = colors[i] if i < len(colors) else None
            btn = ColorCircleButton(c or theme_cs[min(i, 1)], tooltip=f"Color for Glyph {i+1}")
            btn.colorSelected.connect(lambda hex_c, idx=i, oc=c: self._on_color_chosen(idx, oc, hex_c))
            self.c_lay.addWidget(btn)
        if codes and any(colors):
            sync_btn = QPushButton("\uE777")
            sync_btn.setFont(QFont("Segoe MDL2 Assets", 10))
            sync_btn.setFixedSize(26, 26)
            sync_btn.setCursor(Qt.PointingHandCursor)
            sync_btn.setStyleSheet("QPushButton { background: #121212; border: 1px solid #363a4f; border-radius: 13px; color: #9ca3af; } QPushButton:hover { border: 1px solid #ea999c; color: #ffffff; }")
            sync_btn.setToolTip("Sync with Theme (Remove custom colors)")
            sync_btn.clicked.connect(self._reset_glyph_colors)
            self.c_lay.addWidget(sync_btn)

    def _on_color_chosen(self, idx, old_color, hex_color):
        val = self.ic_inp.text().strip()
        codes = _extract_glyph_codes(val)
        if codes:
            new_val = _get_new_asset_value(val, old_color, hex_color, idx=idx)
            self.ic_inp.setText(new_val)
            if hasattr(self, 'ic_prev_lbl'): self.ic_prev_lbl.set_asset(new_val)
        else:
            path, _ = _extract_img_path_and_color(val)
            resolved = _resolve_app_dir_path(path)
            if resolved and os.path.exists(resolved):
                new_asset_path, _ = save_local_icon(resolved, hex_color, True)
                self.ic_inp.setText(f"'{new_asset_path}'")
                if hasattr(self, 'ic_prev_lbl'): self.ic_prev_lbl.set_asset(f"'{new_asset_path}'")

    def _reset_glyph_colors(self):
        codes = _extract_glyph_codes(self.ic_inp.text())
        if codes: self.ic_inp.setText(_build_glyph_val(codes, []))
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
        if title_val:
            p['title'] = f"'{title_val}'" if ' ' in title_val else title_val
        else:
            p.pop('title', None)
        p['pos'] = self.p_box.currentText()
        vis_val = self.vis_widget.get_value()
        if vis_val:
            p['vis'] = vis_val
        else:
            p.pop('vis', None)

        type_val = self.type_widget.get_value()
        if type_val and type_val.lower() != 'all':
            p['type'] = type_val
        else:
            p['type'] = None
        
        m_sel = self.m_box.currentText()
        if m_sel == "None": p.pop('menu', None)
        elif m_sel == "Main": p['menu'] = ""
        elif m_sel == "Options": p['menu'] = "options"
        elif m_sel.strip(): p['menu'] = m_sel.strip()
        else: p.pop('menu', None)
        
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
        def normalize_vis(v):
            vl = str(v or '').strip('\'" ').lower().replace('"', '').replace("'", "").replace(" ", "")
            if not vl or vl in ("normal", "alwaysvisible", "vis.normal", "1"):
                return ""
            if ('key.shift' in vl or 'key.control' in vl or 'key.ctrl' in vl or 'key.lbutton' in vl or 'key.caps' in vl) and 'hidden' in vl:
                return "main"
            if vl in ("vis.remove", "key.remove", "vis.hidden", "key.hidden", "remove", "hidden", "0"):
                return "hide"
            if vl in ("key.shift()", "vis.shift()", "vis.shift", "shift", "key.shift"):
                return "shift"
            if vl in ("key.control()", "key.ctrl()", "vis.control()", "vis.control", "vis.ctrl", "control", "ctrl", "key.control", "key.ctrl"):
                return "ctrl"
            if vl in ("key.capslock()", "key.caps()", "vis.capslock()", "vis.capslock", "vis.caps", "capslock", "caps", "key.capslock", "key.caps"):
                return "caps"
            if vl in ("key.lbutton()", "key.lmb()", "vis.lbutton()", "vis.lbutton", "vis.lmb", "lbutton", "lmb", "key.lbutton"):
                return "lmb"
            return vl

        def format_user_friendly(prop_key, val):
            val_clean = str(val or '').strip('\'" ')
            if prop_key == 'vis':
                norm = normalize_vis(val_clean)
                if not norm: return "Normal"
                if norm == "main": return "Main"
                if norm == "hide": return "Hide"
                if norm == "shift": return "Shift"
                if norm == "ctrl": return "Ctrl"
                if norm == "caps": return "Caps"
                if norm == "lmb": return "LMB"
                return val_clean
            if prop_key == 'sep':
                vl = val_clean.lower()
                if vl in ("true", "1", "before"): return "Before"
                if vl == "after": return "After"
                if vl == "both": return "Both"
                if vl in ("false", "0", "none", ""): return "None"
                return val_clean.title()
            if prop_key == 'type':
                if not val_clean or val_clean.lower() == 'all': return "All"
                return val_clean
            if prop_key == 'menu':
                if val is None: return "None"
                vl = val_clean.lower()
                if vl == "none": return "None"
                if not vl or vl in ("main", "menu.main"): return "Main"
                if vl in ("options", "title.options"): return "Options"
                return val_clean
            return val_clean or "(empty)"

        for k in ['title', 'pos', 'vis', 'type', 'menu', 'sep']:
            v1 = str(p1.get(k, '')).strip('\'" ')
            v2 = str(p2.get(k, '')).strip('\'" ')
            if k == 'vis':
                if normalize_vis(v1) == normalize_vis(v2):
                    continue
                display_k = key_names.get(k, k.title())
                changes.append(f"{display_k}: {format_user_friendly(k, v2)} ➔ {format_user_friendly(k, v1)}")
                continue
            if k == 'type':
                v1_clean = str(p1.get('type') or '').strip('\'" ')
                v2_clean = str(p2.get('type') or '').strip('\'" ')
                set1 = set(p.strip().lower() for p in v1_clean.split('|') if p.strip() and p.strip().lower() not in ('all', '*'))
                set2 = set(p.strip().lower() for p in v2_clean.split('|') if p.strip() and p.strip().lower() not in ('all', '*'))
                set1 = {'dir' if x == 'directory' else x for x in set1}
                set2 = {'dir' if x == 'directory' else x for x in set2}
                if set1 == set2:
                    continue
                display_k = key_names.get(k, k.title())
                changes.append(f"{display_k}: {format_user_friendly(k, v2_clean)} ➔ {format_user_friendly(k, v1_clean)}")
                continue
            if k == 'menu':
                v1_raw = p1.get('menu')
                v2_raw = p2.get('menu')
                if v1_raw is None and v2_raw is None:
                    continue
                v1_norm = "None" if v1_raw is None else ("Main" if str(v1_raw).strip('\'"').lower() in ("", "main", "menu.main") else str(v1_raw).strip('\'"'))
                v2_norm = "None" if v2_raw is None else ("Main" if str(v2_raw).strip('\'"').lower() in ("", "main", "menu.main") else str(v2_raw).strip('\'"'))
                if v1_norm.lower() == v2_norm.lower(): continue
                display_k = key_names.get(k, k.title())
                changes.append(f"{display_k}: {format_user_friendly(k, v2_raw)} ➔ {format_user_friendly(k, v1_raw)}")
                continue
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

class TabGridScrollArea(QScrollArea):
    """Scrollable tab grid showing 1, 2, or 3 rows adaptively, capped at 3 rows max with visible vertical scrollbar if >3 rows."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setStyleSheet("""
            QScrollArea { background: transparent; border: none; }
            QScrollBar:vertical {
                background: rgba(255, 255, 255, 0.04);
                width: 8px;
                margin: 2px 0 2px 2px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: rgba(234, 153, 156, 0.6);
                border-radius: 4px;
                min-height: 24px;
            }
            QScrollBar::handle:vertical:hover {
                background: #ea999c;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

    def update_grid_geometry(self):
        w = self.widget()
        if not w or not w.layout():
            return
        vp_w = self.viewport().width()
        if vp_w <= 10:
            vp_w = (self.parent().width() - 40) if self.parent() else 600
        needed_h = w.layout().heightForWidth(vp_w)
        if needed_h <= 50:
            # 1 row
            self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            self.setFixedHeight(needed_h + 4)
        elif needed_h <= 90:
            # 2 rows
            self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            self.setFixedHeight(needed_h + 4)
        elif needed_h <= 130:
            # 3 rows
            self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            self.setFixedHeight(needed_h + 4)
        else:
            # > 3 rows: clamp to exactly 3 rows (122px) and show permanent vertical scrollbar
            self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
            self.setFixedHeight(122)
            
        w.setMinimumHeight(needed_h)
        w.setMaximumHeight(needed_h)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_grid_geometry()

    def showEvent(self, event):
        super().showEvent(event)
        self.update_grid_geometry()


class MultiItemEditDialog(QDialog):
    def __init__(self, items, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(720, 780)
        self._drag_pos = None
        self.items = items
        self.editors = [None] * len(items)
        
        main_frame = QFrame(self)
        main_frame.setObjectName("multiMainFrame")
        main_frame.setStyleSheet("""
            #multiMainFrame { background-color: #121214; border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 20px; }
        """)
        
        dlg_layout = QVBoxLayout(self)
        dlg_layout.setContentsMargins(0, 0, 0, 0)
        dlg_layout.addWidget(main_frame)
        
        layout = QVBoxLayout(main_frame)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)
        
        # Header titlebar
        title_bar = QHBoxLayout()
        title_label = QLabel("Edit Items/Menus")
        title_label.setFont(QFont('Segoe UI Variable Display', 15, QFont.Bold))
        title_label.setStyleSheet("color: #ffffff; background: transparent; border: none;")
        title_bar.addWidget(title_label)
        title_bar.addStretch()
        
        close_btn = QPushButton("\uE711")
        close_btn.setFont(QFont('Segoe MDL2 Assets', 10))
        close_btn.setFixedSize(28, 28)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet("QPushButton { background: rgba(255,255,255,0.05); border: none; border-radius: 14px; color: #b0b0b0; } QPushButton:hover { background: rgba(231, 130, 132, 0.2); color: #e78284; }")
        close_btn.clicked.connect(self.reject)
        title_bar.addWidget(close_btn)
        layout.addLayout(title_bar)
        
        self._embed_style = """
            #mainFrame { background: transparent; border: none; }
            QLabel { color: #ffffff; font-size: 12px; } 
            QLineEdit { background-color: #1e1e24; border: 1px solid #363a4f; border-radius: 10px; padding: 6px 10px; color: #ffffff; selection-background-color: #e78284; } 
            QLineEdit:focus { border: 1px solid #e78284; }
        """
        
        if len(items) == 1:
            editor = ImportEditorDialog(items[0], self, embed_mode=True)
            editor.mf.setStyleSheet(self._embed_style)
            layout.addWidget(editor)
            self.editors[0] = editor
        else:
            self.tab_scroll = TabGridScrollArea(self)
            container = QWidget()
            container.setStyleSheet("background: transparent;")
            self.tab_layout = FlowLayout(container, margin=2, spacing=8)
            self.tab_group = QButtonGroup(self)
            self.tab_group.setExclusive(True)
            self.tab_buttons = []
            
            for idx, item in enumerate(items):
                title = str(item['props'].get('title', '')).strip('\'"') or f"Item {idx+1}"
                raw_icon = item['props'].get('image') or item['props'].get('icon') or ''
                pix = render_nss_asset_pixmap(raw_icon, size=20)
                
                btn = PillTabButton(title, height=32, icon_size=20)
                if pix and not pix.isNull():
                    btn.setIcon(QIcon(pix))
                else:
                    btn.setIcon(get_mdl2_icon(0xE71D, 20, '#ea999c'))
                    
                self.tab_group.addButton(btn, idx)
                self.tab_layout.addWidget(btn)
                self.tab_buttons.append(btn)
                btn.clicked.connect(lambda _, i=idx: self._switch_tab(i))
                if idx == 0:
                    btn.setChecked(True)
                    
            self.tab_scroll.setWidget(container)
            self.tab_scroll.update_grid_geometry()
            layout.addWidget(self.tab_scroll)
            
            self.editor_stack = QStackedWidget(self)
            layout.addWidget(self.editor_stack)
            self._switch_tab(0)

        # Global Save / Cancel action bar with PillPushButton
        action_bar = QHBoxLayout()
        action_bar.addStretch()
        
        cancel_b = PillPushButton("Cancel", "secondary", height=34)
        cancel_b.clicked.connect(self.reject)
        action_bar.addWidget(cancel_b)
        
        save_b = PillPushButton("Save Changes", "primary", height=34)
        save_b.clicked.connect(self.on_save_all)
        action_bar.addWidget(save_b)
        
        layout.addLayout(action_bar)

    def _switch_tab(self, idx):
        if idx < 0 or idx >= len(self.items):
            return
        if self.editors[idx] is None:
            editor = ImportEditorDialog(self.items[idx], self, embed_mode=True)
            editor.mf.setStyleSheet(self._embed_style)
            self.editors[idx] = editor
            self.editor_stack.addWidget(editor)
        self.editor_stack.setCurrentWidget(self.editors[idx])

    def showEvent(self, event):
        super().showEvent(event)
        if hasattr(self, 'tab_scroll'):
            self.tab_scroll.update_grid_geometry()

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
        for idx, editor in enumerate(self.editors):
            if editor:
                c = editor.get_changes()
                item_title = str(self.items[idx]['props'].get('title', '')).strip('\'"') or f"Item {idx+1}"
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
        saved_any = False
        for idx, editor in enumerate(self.editors):
            if editor and editor.get_changes():
                save_imported_item(self.items[idx], editor.get_props())
                saved_any = True
        return saved_any


class SingleItemListView(QListView):
    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        if delta != 0:
            num_steps = delta / 120.0
            item_h = 100
            scroll_delta = int(-num_steps * item_h)
            sb = self.verticalScrollBar()
            sb.setValue(sb.value() + scroll_delta)
            event.accept()
        else:
            super().wheelEvent(event)


def is_nss_file_enabled(fp, shell_nss_path):
    if not shell_nss_path or not os.path.exists(shell_nss_path):
        return False
    if os.path.abspath(fp) == os.path.abspath(shell_nss_path):
        return True
    fname = os.path.basename(fp).lower()
    try:
        content = read_file(shell_nss_path)
        if not content:
            return False
        for line in content.splitlines():
            s = line.strip()
            if s.startswith("//") or s.startswith("#") or s.startswith("/*"):
                continue
            if s.lower().startswith("import"):
                m = re.search(r"import\s+['\"]([^'\"]+)['\"]", s, re.I)
                if m:
                    imported = m.group(1).replace('\\', '/')
                    if os.path.basename(imported).lower() == fname:
                        return True
                else:
                    parts = s.split()
                    if len(parts) >= 2:
                        imported = parts[1].strip(';\'"').replace('\\', '/')
                        if os.path.basename(imported).lower() == fname:
                            return True
        return False
    except Exception:
        return False


def toggle_nss_file_import(fp, shell_nss_path, root):
    if not shell_nss_path or not os.path.exists(shell_nss_path):
        return False
    if os.path.abspath(fp) == os.path.abspath(shell_nss_path):
        return True
    fname = os.path.basename(fp)
    fname_lower = fname.lower()
    enabled = is_nss_file_enabled(fp, shell_nss_path)
    
    content = read_file(shell_nss_path)
    if not content and os.path.exists(shell_nss_path):
        return enabled
    
    lines = content.splitlines(True)
    if enabled:
        new_lines = []
        for line in lines:
            s = line.strip()
            if s.lower().startswith("import"):
                m = re.search(r"import\s+['\"]?([^'\";\s]+)", s, re.I)
                if m and os.path.basename(m.group(1).replace('\\', '/')).lower() == fname_lower:
                    continue
            new_lines.append(line)
        safe_file_write(shell_nss_path, "".join(new_lines))
        return False
    else:
        try:
            rel_path = os.path.relpath(fp, root).replace('\\', '/')
        except Exception:
            rel_path = f"imports/{fname}"
        
        import_stmt = f"import '{rel_path}'\n"
        last_import_idx = -1
        for i, line in enumerate(lines):
            if line.strip().lower().startswith("import"):
                last_import_idx = i
        
        if last_import_idx != -1:
            lines.insert(last_import_idx + 1, import_stmt)
        else:
            lines.insert(0, import_stmt)
        
        safe_file_write(shell_nss_path, "".join(lines))
        return True


class CustomRulesButton(QPushButton):
    def __init__(self, text="  Custom Rules", parent=None):
        super().__init__(text, parent)
        self.setFixedHeight(40)
        self.setCursor(Qt.PointingHandCursor)
        self.setFont(QFont('Segoe UI Variable Display', 10, QFont.Bold))
        self.setAttribute(Qt.WA_Hover, True)
        self.setStyleSheet('background: transparent; border: none; outline: none;')
        self._is_active = False

    def set_active(self, is_active):
        if self._is_active != is_active:
            self._is_active = is_active
            self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)

        rect = QRectF(self.rect()).adjusted(1.0, 1.0, -1.0, -1.0)
        path = QPainterPath()
        path.addRoundedRect(rect, 14, 14)

        is_hov = self.underMouse()
        if self._is_active:
            grad = QLinearGradient(rect.topLeft(), rect.bottomRight())
            grad.setColorAt(0.0, QColor(234, 153, 156, 140))
            grad.setColorAt(0.5, QColor(231, 130, 132, 100))
            grad.setColorAt(1.0, QColor(202, 158, 230, 80))
            p.fillPath(path, grad)
            p.setPen(QPen(QColor(255, 255, 255, 170 if is_hov else 130), 1.6))
            p.drawPath(path)
            text_color = QColor('#ffffff')
            icon_color = QColor('#ffffff')
        elif is_hov:
            p.fillPath(path, QColor(234, 153, 156, 35))
            p.setPen(QPen(QColor(234, 153, 156, 120), 1.5))
            p.drawPath(path)
            text_color = QColor('#ffffff')
            icon_color = QColor('#ea999c')
        else:
            p.fillPath(path, QColor(234, 153, 156, 16))
            p.setPen(QPen(QColor(234, 153, 156, 50), 1.5))
            p.drawPath(path)
            text_color = QColor('#ea999c')
            icon_color = QColor('#ea999c')

        icon_pix = get_mdl2_icon(0xE15E, 16, icon_color.name()).pixmap(16, 16)
        p.drawPixmap(14, int((self.height() - 16) / 2.0), icon_pix)
        p.setFont(self.font())
        p.setPen(text_color)
        p.drawText(38, int((self.height() + self.fontMetrics().ascent() - self.fontMetrics().descent()) / 2.0), self.text().strip())


class AllImportsButton(QPushButton):
    def __init__(self, text="  All Imports", parent=None):
        super().__init__(text, parent)
        self.setFixedHeight(40)
        self.setCursor(Qt.PointingHandCursor)
        self.setFont(QFont('Segoe UI Variable Display', 10, QFont.Bold))
        self.setAttribute(Qt.WA_Hover, True)
        self.setStyleSheet('background: transparent; border: none; outline: none;')
        self._is_all = True

    @property
    def _is_active(self):
        return self._is_all
        
    def set_active(self, is_all):
        if self._is_all != is_all:
            self._is_all = is_all
            self.update()
        
    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)
        
        rect = QRectF(self.rect()).adjusted(1.0, 1.0, -1.0, -1.0)
        path = QPainterPath()
        path.addRoundedRect(rect, 14, 14)
        
        is_hov = self.underMouse()
        if self._is_all:
            grad = QLinearGradient(rect.topLeft(), rect.bottomRight())
            grad.setColorAt(0.0, QColor(231, 130, 132, 65))
            grad.setColorAt(0.45, QColor(202, 158, 230, 48))
            grad.setColorAt(1.0, QColor(140, 170, 238, 38))
            p.fillPath(path, grad)
            p.setPen(QPen(QColor(255, 255, 255, 85 if not is_hov else 115), 1.5))
            p.drawPath(path)
            text_color = QColor('#ffffff')
        elif is_hov:
            p.fillPath(path, QColor(255, 255, 255, 22))
            p.setPen(QPen(QColor(255, 255, 255, 45), 1.5))
            p.drawPath(path)
            text_color = QColor('#ffffff')
        else:
            p.fillPath(path, QColor(255, 255, 255, 14))
            p.setPen(QPen(QColor(255, 255, 255, 25), 1.5))
            p.drawPath(path)
            text_color = QColor('#8c92a4')
            
        icon_pix = get_mdl2_icon(0xE8B5, 16, text_color.name()).pixmap(16, 16)
        p.drawPixmap(14, int((self.height() - 16) / 2.0), icon_pix)
        p.setFont(self.font())
        p.setPen(text_color)
        p.drawText(38, int((self.height() + self.fontMetrics().ascent() - self.fontMetrics().descent()) / 2.0), self.text().strip())

AllFilesButton = AllImportsButton


class CircularIconButton(QPushButton):
    def __init__(self, icon_code, color="#a6d189", hover_color=None, parent=None):
        super().__init__(parent)
        self.setFixedSize(28, 28)
        self.setCursor(Qt.PointingHandCursor)
        self._icon_code = icon_code
        self._color = QColor(color)
        self._hover_color = QColor(hover_color) if hover_color else self._color.lighter(120)
        self.setAttribute(Qt.WA_Hover, True)
        self.setStyleSheet('background: transparent; border: none; outline: none;')
        
    def set_icon_and_color(self, icon_code, color, hover_color=None):
        self._icon_code = icon_code
        self._color = QColor(color)
        self._hover_color = QColor(hover_color) if hover_color else self._color.lighter(120)
        self.update()
        
    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        
        rect = QRectF(self.rect()).adjusted(1.0, 1.0, -1.0, -1.0)
        is_hov = self.underMouse()
        c = self._hover_color if is_hov else self._color
        
        bg_alpha = 55 if is_hov else 28
        border_alpha = 190 if is_hov else 95
        
        p.setBrush(QColor(c.red(), c.green(), c.blue(), bg_alpha))
        p.setPen(QPen(QColor(c.red(), c.green(), c.blue(), border_alpha), 1.5))
        p.drawEllipse(rect)
        
        icon_pix = get_mdl2_icon(self._icon_code, 14, c.name()).pixmap(14, 14)
        p.drawPixmap(int((self.width() - 14) / 2.0), int((self.height() - 14) / 2.0), icon_pix)


class FileItemButton(QPushButton):
    def __init__(self, text, is_active=False, is_enabled=True, is_shell=False, parent=None):
        super().__init__(text, parent)
        self.setFixedHeight(34)
        self.setCursor(Qt.PointingHandCursor)
        self.setFont(QFont('Segoe UI Variable Display', 10, QFont.Bold))
        self.setAttribute(Qt.WA_Hover, True)
        self.setStyleSheet('background: transparent; border: none; outline: none;')
        self.is_active = is_active
        self.is_enabled = is_enabled
        self.is_shell = is_shell
        
    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)
        
        rect = QRectF(self.rect()).adjusted(1.0, 1.0, -1.0, -1.0)
        path = QPainterPath()
        path.addRoundedRect(rect, 12, 12)
        
        is_hov = self.underMouse()
        
        if not self.is_enabled and not self.is_shell:
            if self.is_active:
                bg = QColor(231, 130, 132, 40)
                pen = QPen(QColor(231, 130, 132, 120), 1.5)
                fg = QColor('#e78284')
            elif is_hov:
                bg = QColor(255, 255, 255, 22)
                pen = QPen(QColor(255, 255, 255, 50), 1.5)
                fg = QColor('#ffffff')
            else:
                bg = QColor(35, 38, 52, 130)
                pen = QPen(QColor('#51576d'), 1.5, Qt.DashLine)
                fg = QColor('#737994')
        else:
            if self.is_active:
                grad = QLinearGradient(rect.topLeft(), rect.bottomRight())
                grad.setColorAt(0.0, QColor(231, 130, 132, 60))
                grad.setColorAt(1.0, QColor(231, 130, 132, 25))
                bg = grad
                pen = QPen(QColor(231, 130, 132, 140), 1.5)
                fg = QColor('#ffffff')
            elif is_hov:
                bg = QColor(255, 255, 255, 25)
                pen = QPen(QColor(255, 255, 255, 55), 1.5)
                fg = QColor('#ffffff')
            else:
                bg = QColor(255, 255, 255, 12)
                pen = QPen(QColor(255, 255, 255, 25), 1.5)
                fg = QColor('#c6d0f5')
                
        p.fillPath(path, bg)
        p.setPen(pen)
        p.drawPath(path)
        
        p.setFont(self.font())
        p.setPen(fg)
        p.drawText(int(rect.left() + 14), int((self.height() + self.fontMetrics().ascent() - self.fontMetrics().descent()) / 2.0), self.text())


class ImportsWidget(QWidget):
    reload_requested = pyqtSignal()
    rules_saved = pyqtSignal()
    def __init__(self, project_root, shell_nss_path=None, modify_nss_path=None, parent=None):
        super().__init__(parent)
        self.root = project_root
        self.shell_nss_path = shell_nss_path
        self.modify_nss_path = modify_nss_path or os.path.join(self.root, 'imports', 'modify.nss')
        self.curr_filter = "rules"
        self.custom_rules = []
        self.imported_items = []
        self.is_dirty = False
        self.original_content = read_file(self.modify_nss_path)
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(0, 10, 0, 0)
        self.setup_ui()

    def setup_ui(self):
        self.side = QFrame()
        self.side.setObjectName("sideFilesPanel")
        self.side.setFixedWidth(240)
        self.side.setStyleSheet("#sideFilesPanel { background: rgba(0,0,0,0.22); border-radius: 16px; border: 1px solid rgba(255, 255, 255, 0.04); }")
        self.sl = QVBoxLayout(self.side)
        self.sl.setAlignment(Qt.AlignTop)
        self.sl.setContentsMargins(8, 14, 8, 14)
        self.sl.setSpacing(10)
        
        lbl = QLabel("FILES")
        lbl.setStyleSheet("color: #70707c; font-size: 11px; font-weight: bold; margin: 4px 0 2px 8px; background: transparent; border: none; letter-spacing: 0.5px;")
        self.sl.addWidget(lbl)
        
        # 1. Custom Rules Button (top, distinct look, NOT grouped in container)
        self.rules_btn = CustomRulesButton("  Custom Rules")
        self.rules_btn.clicked.connect(lambda: self.set_file_filter("rules"))
        self.sl.addWidget(self.rules_btn)
        
        # 2. Imports Group Container (groups 'All Imports' and scrollable .nss files)
        self.imports_container = QFrame()
        self.imports_container.setObjectName("importsContainer")
        self.imports_container.setStyleSheet("#importsContainer { background: rgba(0,0,0,0.16); border-radius: 14px; border: 1px solid rgba(255, 255, 255, 0.04); }")
        ic_l = QVBoxLayout(self.imports_container)
        ic_l.setContentsMargins(6, 8, 6, 8)
        ic_l.setSpacing(6)
        
        self.all_btn = AllImportsButton("  All Imports")
        self.all_btn.clicked.connect(lambda: self.set_file_filter(None))
        ic_l.addWidget(self.all_btn)
        
        self.f_scroll = QScrollArea()
        self.f_scroll.setWidgetResizable(True)
        self.f_scroll.setStyleSheet("background: transparent; border: none;")
        self.file_cont = QWidget()
        self.file_cont.setStyleSheet("background: transparent;")
        self.file_l = QVBoxLayout(self.file_cont)
        self.file_l.setContentsMargins(0, 0, 0, 0)
        self.file_l.setSpacing(4)
        self.file_l.setAlignment(Qt.AlignTop)
        self.f_scroll.setWidget(self.file_cont)
        ic_l.addWidget(self.f_scroll, 1)
        
        self.sl.addWidget(self.imports_container, 1)
        self.main_layout.addWidget(self.side)
        
        cr = QWidget()
        crl = QVBoxLayout(cr)
        crl.setContentsMargins(0, 0, 0, 0)
        self.main_layout.addWidget(cr)
        
        head = QHBoxLayout()
        self.search = PillLineEdit("Search items/menus...")
        self.search.textChanged.connect(self.filter_items)
        head.addWidget(self.search, 1)
        
        self.new_rule_btn = PillPushButton("+ New Rule", "primary", height=34)
        self.new_rule_btn.setFixedWidth(100)
        self.new_rule_btn.clicked.connect(self.add_new_rule_dialog)
        head.addWidget(self.new_rule_btn)
        
        crl.addLayout(head)
        
        self.type_tags = FilterBar([("All", "#51576d"), ("Item", "#51576d"), ("Menu", "#51576d")])
        self.type_tags.filter_changed.connect(lambda _: self.filter_items())
        crl.addWidget(self.type_tags)

        self.action_tags = FilterBar([
            ("All", "#51576d"), ("Renamed", "#838ba7"), ("Icons", "#8caaee"), 
            ("Hidden", "#e78284"), ("Part Hidden", "#ca9ee6"), ("Moved", "#ef9f76"), 
            ("Position", "#a6d189"), ("Separator", "#e5c890")
        ])
        self.action_tags.filter_changed.connect(lambda _: self.filter_items())
        crl.addWidget(self.action_tags)
        
        self.view = SingleItemListView()
        self.view.setStyleSheet("background: transparent; border: none;")
        self.view.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.view.setSpacing(0)
        self.view.setMouseTracking(True)
        self.model = NSSItemModel()
        self.view.setModel(self.model)
        self.delegate = NSSItemDelegate(self.view)
        self.view.setItemDelegate(self.delegate)
        crl.addWidget(self.view)
        
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #e78284; font-weight: 500;")
        crl.addWidget(self.status_label)
        
        self._is_loaded = False
        self.set_file_filter("rules")

    def refresh(self):
        self._is_loaded = True
        content = read_file(self.modify_nss_path)
        self.custom_rules = extract_custom_rules(content)
        for r in self.custom_rules:
            r['file'] = self.modify_nss_path

        all_items = scan_nss_items(self.root, self.shell_nss_path)
        items = []
        for i in all_items:
            if i.get('type') == 'item':
                items.append(i)
            elif i.get('type') == 'menu':
                p = i.get('props', {})
                if not p.get('title') and not p.get('icon') and not p.get('image') and str(p.get('expanded', '')).lower() == 'true':
                    continue
                has_visual = p.get('title') or p.get('icon') or p.get('image')
                if has_visual or i.get('has_children'):
                    items.append(i)
        
        items.sort(key=lambda x: (x.get('type') != 'menu', str(x.get('props', {}).get('title') or x.get('props', {}).get('find') or x.get('props', {}).get('where') or '').lower()))
        self.imported_items = items
        
        if self.curr_filter == "rules":
            self.model.set_items(self.custom_rules)
            self.type_tags.hide()
            self.search.setPlaceholderText("Search custom rules...")
        else:
            self.model.set_items(self.imported_items)
            self.type_tags.show()
            self.search.setPlaceholderText("Search items/menus...")
            
        self.refresh_sidebar_highlights()
        self.filter_items()

    def refresh_rules(self, preserve_item=None):
        content = read_file(self.modify_nss_path)
        new_rules = extract_custom_rules(content)
        for r in new_rules:
            r['file'] = self.modify_nss_path
            
        if preserve_item is not None:
            p_props = preserve_item.get('props', {})
            target_key = (
                str(p_props.get('find', '')).strip('\'" ').lower(),
                str(p_props.get('where.id', '')).strip('\'" ').lower(),
                str(p_props.get('in', '')).strip('\'" ').lower(),
                str(p_props.get('where', '')).strip('\'" ').lower()
            )
            for nr in new_rules:
                nr_props = nr.get('props', {})
                nr_key = (
                    str(nr_props.get('find', '')).strip('\'" ').lower(),
                    str(nr_props.get('where.id', '')).strip('\'" ').lower(),
                    str(nr_props.get('in', '')).strip('\'" ').lower(),
                    str(nr_props.get('where', '')).strip('\'" ').lower()
                )
                if nr_key == target_key and any(target_key):
                    preserve_item['start'] = nr.get('start')
                    preserve_item['end'] = nr.get('end')
                    preserve_item['cmd_end'] = nr.get('cmd_end')
                    break
        self.custom_rules = new_rules
        if self.curr_filter == "rules":
            self.model.set_items(self.custom_rules)
            self.filter_items()

    def filter_items(self):
        ab = self.action_tags.group.checkedButton()
        action_tag = ab.text() if ab else "All"
        if self.curr_filter == "rules":
            self.model.filter(self.search.text(), action_tag=action_tag)
        else:
            cb = self.type_tags.group.checkedButton()
            type_tag = cb.text() if cb else "All"
            self.model.filter(self.search.text(), self.curr_filter, type_tag=type_tag, action_tag=action_tag)

    def set_file_filter(self, fp):
        self.curr_filter = fp
        if fp == "rules":
            self.rules_btn.set_active(True)
            self.all_btn.set_active(False)
            self.type_tags.hide()
            self.search.setPlaceholderText("Search custom rules...")
            self.model.set_items(self.custom_rules)
        else:
            self.rules_btn.set_active(False)
            self.all_btn.set_active(fp is None)
            self.type_tags.show()
            self.search.setPlaceholderText("Search items/menus...")
            self.model.set_items(self.imported_items)
        self.filter_items()
        self.refresh_sidebar_highlights()

    def update_file_filters(self, items):
        while self.file_l.count():
            it = self.file_l.takeAt(0)
            wid = it.widget()
            if wid:
                wid.setParent(None)
                wid.deleteLater()
        
        files = []
        if self.shell_nss_path and os.path.exists(self.shell_nss_path):
            files.append(os.path.abspath(self.shell_nss_path))
        
        shell_abs = os.path.abspath(self.shell_nss_path) if self.shell_nss_path else None
        scanned_files = list(set(i['file'] for i in items if i.get('file')))
        other_files = [f for f in scanned_files if not (shell_abs and os.path.abspath(f) == shell_abs)]
        other_files.sort(key=lambda sf: os.path.basename(sf).lower())
        files.extend(other_files)
        
        for fp in files:
            name = os.path.basename(fp).replace('.nss', '')
            display_name = name
            is_shell = bool(self.shell_nss_path and os.path.abspath(fp) == os.path.abspath(self.shell_nss_path))
            if is_shell:
                display_name = "shell.nss"
            
            is_enabled = is_nss_file_enabled(fp, self.shell_nss_path)
            is_active = (self.curr_filter == fp)
            
            fw = QWidget()
            fl = QHBoxLayout(fw)
            fl.setContentsMargins(2, 2, 2, 2)
            fl.setSpacing(6)
            
            eb = CircularIconButton(0xE104, '#c6d0f5', '#ffffff')
            eb.setToolTip("Open in Editor")
            eb.clicked.connect(lambda _, x=fp: os.startfile(x))
            fl.addWidget(eb)

            if is_shell:
                tb = CircularIconButton(0xE73E, '#8caaee')
                tb.setToolTip("Master Configuration File")
            elif is_enabled:
                tb = CircularIconButton(0xE73E, '#a6d189', '#e78284')
                tb.setToolTip("Enabled in shell.nss (Click to Disable)")
                tb.clicked.connect(lambda _, f=fp: self.toggle_file_enabled(f))
            else:
                tb = CircularIconButton(0xE8F8, '#e78284', '#a6d189')
                tb.setToolTip("Disabled (Click to Enable in shell.nss)")
                tb.clicked.connect(lambda _, f=fp: self.toggle_file_enabled(f))
            fl.addWidget(tb)

            btn = FileItemButton(display_name, is_active=is_active, is_enabled=is_enabled, is_shell=is_shell)
            btn.clicked.connect(lambda _, f=fp: self.set_file_filter(f))
            fl.addWidget(btn, 1)

            self.file_l.addWidget(fw)

    def toggle_file_enabled(self, fp):
        toggle_nss_file_import(fp, self.shell_nss_path, self.root)
        self.refresh()
        self.reload_requested.emit()

    def refresh_sidebar_highlights(self):
        is_rules = (self.curr_filter == "rules")
        is_all = (self.curr_filter is None)
        self.rules_btn.set_active(is_rules)
        self.all_btn.set_active(is_all)
        self.update_file_filters(self.imported_items)

    def edit_item(self, data):
        d = ImportEditorDialog(data, self)
        d.reload_requested.connect(self.reload_requested.emit)
        if d.exec_():
            save_imported_item(data, d.get_props())
            self.refresh()
            self.reload_requested.emit()

    def _get_bulk_sections(self):
        content = read_file(self.modify_nss_path)
        return {
            'hide': extract_ids_from_section(content, "hide"),
            'more': extract_ids_from_section(content, "more"),
            'shift': extract_ids_from_section(content, "shift")
        }

    def _remove_id_from_bulk_sections(self, raw_id, base_content=None):
        if not raw_id:
            return base_content if base_content is not None else read_file(self.modify_nss_path)
        clean_id = raw_id.strip('\'" ')
        if not clean_id.startswith('id.'):
            clean_id = f"id.{clean_id}"
        clean_bare = clean_id.replace("id.", "")
        content = base_content if base_content is not None else read_file(self.modify_nss_path)
        for sec in ("hide", "more", "shift"):
            ids = extract_ids_from_section(content, sec)
            orig_len = len(ids)
            ids = [i for i in ids if i.strip() not in (clean_id, clean_bare)]
            if len(ids) != orig_len:
                if sec == "hide":
                    content = update_section(content, "// hide\nmodify(mode=mode.multiple\nwhere=this.id(", ") vis=vis.remove)", ids)
                elif sec == "more":
                    content = update_section(content, "// more\nmodify(mode=mode.multiple\nwhere=this.id(", ") menu=title.options)", ids)
                elif sec == "shift":
                    content = update_section(content, "// shift\nmodify(mode=single\nwhere=this.id(", ") vis=key.shift())", ids)
        return content

    def edit_rule(self, item):
        props = item.get('props', {})
        orig_props = props.copy()
        d = ModifyRuleEditorDialog(props, existing_rules=self.custom_rules, bulk_sections=self._get_bulk_sections(), parent=self)

        def handle_preview(nd):
            item['props'] = nd
            self.model.layoutChanged.emit()

        d.live_update.connect(handle_preview)

        if d.exec_():
            updated_data = d.get_data()
            target_wid = str(updated_data.get('where.id', '')).lower().strip('\'" ')
            target_find = str(updated_data.get('find', '')).lower().strip('\'" ')
            
            matched_idx = -1
            for idx, r in enumerate(self.custom_rules):
                if r is item or (r.get('start') is not None and r.get('start') == item.get('start') and r.get('type') == item.get('type')):
                    matched_idx = idx
                    break
                rp = r.get('props', {})
                r_wid = str(rp.get('where.id', '')).lower().strip('\'" ')
                r_find = str(rp.get('find', '')).lower().strip('\'" ')
                if target_wid and (r_wid == target_wid or f"id.{r_wid}" == target_wid or r_wid.replace("id.", "") == target_wid.replace("id.", "")):
                    matched_idx = idx
                    break
                if not target_wid and target_find and r_find == target_find:
                    matched_idx = idx
                    break

            if is_rule_complete(updated_data):
                if matched_idx >= 0:
                    self.custom_rules[matched_idx]['props'] = updated_data
                else:
                    self.custom_rules.insert(0, item)
                    item['props'] = updated_data
            elif matched_idx >= 0:
                self.custom_rules.pop(matched_idx)

            self.save_all_modifications()
            self.refresh_rules()
            self.reload_requested.emit()
        else:
            item['props'] = orig_props
            self.refresh_rules()

    def add_new_rule_dialog(self):
        d = ModifyRuleEditorDialog(existing_rules=self.custom_rules, bulk_sections=self._get_bulk_sections(), parent=self)
        temp_item = {'type': 'modify', 'props': {}, 'file': self.modify_nss_path, '_is_temp': True}

        def handle_new_preview(nd):
            temp_item['props'] = nd
            self.custom_rules = [r for r in self.custom_rules if not r.get('_is_temp')]
            self.custom_rules.insert(0, temp_item)
            self.model.layoutChanged.emit()

        d.live_update.connect(handle_new_preview)

        if d.exec_():
            final_data = d.get_data()
            self.custom_rules = [r for r in self.custom_rules if not r.get('_is_temp')]
            
            target_wid = str(final_data.get('where.id', '')).lower().strip('\'" ')
            target_find = str(final_data.get('find', '')).lower().strip('\'" ')
            matched_idx = -1
            for idx, r in enumerate(self.custom_rules):
                rp = r.get('props', {})
                r_wid = str(rp.get('where.id', '')).lower().strip('\'" ')
                r_find = str(rp.get('find', '')).lower().strip('\'" ')
                if target_wid and (r_wid == target_wid or f"id.{r_wid}" == target_wid or r_wid.replace("id.", "") == target_wid.replace("id.", "")):
                    matched_idx = idx
                    break
                if not target_wid and target_find and r_find == target_find:
                    matched_idx = idx
                    break

            if is_rule_complete(final_data):
                if matched_idx >= 0:
                    self.custom_rules[matched_idx]['props'] = final_data
                else:
                    new_item = {'type': 'modify', 'props': final_data, 'file': self.modify_nss_path}
                    self.custom_rules.insert(0, new_item)
            elif matched_idx >= 0:
                self.custom_rules.pop(matched_idx)

            self.save_all_modifications()
            self.set_file_filter("rules")
            self.reload_requested.emit()
        else:
            self.custom_rules = [r for r in self.custom_rules if not r.get('_is_temp')]
            self.model.set_items(self.custom_rules)
            self.filter_items()

    def delete_rule(self, item):
        if item in self.custom_rules:
            self.custom_rules.remove(item)
            self.save_all_modifications()
            if self.curr_filter == "rules":
                self.model.set_items(self.custom_rules)
                self.filter_items()
            self.reload_requested.emit()

    def save_all_modifications(self, preserve_item=None, base_content=None, status_msg="Rules Saved"):
        try:
            content = base_content if base_content is not None else read_file(self.modify_nss_path)
            start_m, end_m = "// -- iMA Managed --", "// -- End iMA Managed --"
            managed = []
            
            self.custom_rules = [r for r in self.custom_rules if is_rule_complete(r.get('props', {}))]

            for item in self.custom_rules:
                wid = item.get('props', {}).get('where.id')
                if wid:
                    content = self._remove_id_from_bulk_sections(wid, base_content=content)

            seen_targets = set()
            deduped = []
            for item in self.custom_rules:
                p = item.get('props', {})
                target_key = (
                    str(p.get('find', '')).strip('\'" ').lower(),
                    str(p.get('where.id', '')).strip('\'" ').lower(),
                    str(p.get('in', '')).strip('\'" ').lower(),
                    str(p.get('where', '')).strip('\'" ').lower(),
                    str(p.get('type', '')).strip('\'" ').lower()
                )
                if target_key in seen_targets and any(target_key):
                    continue
                if any(target_key):
                    seen_targets.add(target_key)
                deduped.append(item)
            self.custom_rules = deduped

            for item in self.custom_rules:
                data = item.get('props', {})
                if not is_rule_complete(data):
                    continue

                pts = []
                pr = ['find', 'where.id', 'type', 'where', 'in', 'pos', 'title', 'menu', 'vis', 'icon', 'image']
                for k in pr:
                    v = data.get(k)
                    if v is not None and (str(v).strip() != '' or k in ('menu', 'title')):
                        pts.append(format_nss_value(k, v))
                
                for k, v in data.items(): 
                    if k not in pr and k not in ('sep', '_order', 'file', 'start', 'end', '_is_temp') and str(v).strip() != '':
                        pts.append(format_nss_value(k, v))
                
                if data.get('sep'):
                    sv = data['sep']
                    if sv is True: pts.append("sep=before")
                    else: pts.append(f"sep={sv}")

                if pts:
                    managed.append(f"    modify({ ' '.join(pts) })")
            
            block = f"{start_m}\n" + "\n".join(managed) + f"\n{end_m}"
            
            s_re = re.compile(r"//\s*--\s*iMA\s*Managed\s*--", re.IGNORECASE)
            e_re = re.compile(r"//\s*--\s*End\s*iMA\s*Managed\s*--", re.IGNORECASE)
            
            s_match = s_re.search(content)
            if s_match:
                e_matches = list(e_re.finditer(content[s_match.end():]))
                if e_matches:
                    last_e = e_matches[-1]
                    end_pos = s_match.end() + last_e.end()
                    new_content = content[:s_match.start()].rstrip() + "\n\n" + block + "\n" + content[end_pos:].lstrip()
                else:
                    new_content = content[:s_match.start()].rstrip() + "\n\n" + block + "\n"
            else:
                lines = content.splitlines()
                rem = []
                for l in lines:
                    sl = l.strip()
                    if re.match(r'^modify\s*\(.*?\)\s*$', sl, re.IGNORECASE) and "where=this.id(" not in sl: continue
                    rem.append(l)
                new_content = "\n".join(rem).rstrip() + "\n\n" + block + "\n"
            
            def on_success(fp):
                if hasattr(NSSCacheManager, '_cache') and self.modify_nss_path in NSSCacheManager._cache:
                    del NSSCacheManager._cache[self.modify_nss_path]
                self.show_status(status_msg)
                self.refresh_rules(preserve_item=preserve_item)
                self.rules_saved.emit()
                self.reload_requested.emit()
                
            def on_error(fp, err):
                self.show_error(f"Save failed: {err}")
                
            from utils import global_undo_stack, FileChangeCommand
            old_content = read_file(self.modify_nss_path)
            cmd = FileChangeCommand(self.modify_nss_path, old_content, new_content, on_success, on_error)
            global_undo_stack.push(cmd)
            self.is_dirty = False
            
        except Exception as e:
            self.show_error(f"Save setup failed: {str(e)}")

    def revert_changes(self):
        if self.is_dirty:
            safe_file_write(self.modify_nss_path, self.original_content)
            self.is_dirty = False
            self.show_status("Changes Reverted")
            self.refresh_rules()
            self.reload_requested.emit()

    def show_status(self, t):
        self.status_label.setText(t)
        self.status_label.setStyleSheet("color: #e78284;")
        QTimer.singleShot(3000, lambda: self.status_label.setText(""))

    def show_error(self, t):
        m = CustomMessageBox(self)
        m.setText("Error")
        m.setInformativeText(t)
        m.exec_()

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


def get_friendly_id_name(id_str):
    clean = id_str.replace("id.", "").replace("_", " ").strip()
    replacements = {
        "vhd": "VHD", "dvd": "DVD", "usb": "USB", "cmd": "CMD", "ps": "PowerShell"
    }
    words = clean.split()
    return " ".join(replacements.get(w.lower(), w.capitalize()) for w in words)


class MatchModeButton(QPushButton):
    mode_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(32, 32)
        self.setCursor(Qt.PointingHandCursor)
        self._mode = "contains"
        self.setFont(QFont("Segoe MDL2 Assets", 12))
        self.setText("\uE713")
        self._update_style_and_tooltip()
        self.clicked.connect(self._show_menu)

    def _update_style_and_tooltip(self):
        self.setToolTip(f"Match Mode: {self._mode.title()} (Click to change)")
        self.setStyleSheet("""
            QPushButton {
                background-color: #121212;
                border: 1px solid #282b3c;
                border-radius: 16px;
                color: #c6d0f5;
            }
            QPushButton:hover {
                background-color: rgba(234, 153, 156, 0.2);
                border: 1px solid #ea999c;
                color: #ffffff;
            }
        """)

    def get_mode(self):
        return self._mode

    def set_mode(self, mode):
        m = str(mode or '').lower()
        if m in ("contains", "starts", "ends", "exact"):
            self._mode = m
        else:
            self._mode = "contains"
        self._update_style_and_tooltip()

    def _show_menu(self):
        menu = QMenu(self)
        menu.setWindowFlags(menu.windowFlags() | Qt.FramelessWindowHint)
        menu.setAttribute(Qt.WA_TranslucentBackground)
        menu.setStyleSheet("""
            QMenu {
                background-color: #121214;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 10px;
                padding: 6px;
            }
            QMenu::item {
                padding: 6px 20px 6px 14px;
                border-radius: 6px;
                color: #c6d0f5;
                font-family: 'Segoe UI Variable Display';
                font-size: 11px;
                font-weight: bold;
            }
            QMenu::item:selected {
                background-color: rgba(234, 153, 156, 0.22);
                color: #ea999c;
            }
        """)
        options = [
            ("contains", "Contains"),
            ("starts", "Starts with"),
            ("ends", "Ends with"),
            ("exact", "Exact")
        ]
        for opt_key, opt_label in options:
            prefix = "✓  " if self._mode == opt_key else "    "
            act = menu.addAction(f"{prefix}{opt_label}")
            act.triggered.connect(lambda _, k=opt_key: self._on_selected(k))

        menu.exec_(self.mapToGlobal(QPoint(0, self.height() + 4)))

    def _on_selected(self, mode):
        self.set_mode(mode)
        self.mode_changed.emit(mode)


class IDDropdownPopup(QFrame):
    id_chosen = pyqtSignal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent, Qt.Popup | Qt.FramelessWindowHint)
        self.setObjectName("idPopupFrame")
        self.setFixedWidth(340)
        self.setFixedHeight(300)
        self.setStyleSheet("""
            #idPopupFrame {
                background-color: #121214;
                border: 1px solid rgba(234, 153, 156, 0.4);
                border-radius: 12px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search System IDs...")
        self.search_box.setStyleSheet("""
            QLineEdit {
                background-color: #1a1a20;
                border: 1px solid #2c2d3a;
                border-radius: 8px;
                padding: 6px 10px;
                color: #ffffff;
                font-size: 11px;
                font-weight: bold;
            }
            QLineEdit:focus {
                border: 1px solid #ea999c;
            }
        """)
        self.search_box.textChanged.connect(self._filter_list)
        layout.addWidget(self.search_box)

        self.list_w = QListWidget()
        self.list_w.setStyleSheet("""
            QListWidget {
                background: transparent;
                border: none;
                outline: none;
                color: #c6d0f5;
                font-family: 'Segoe UI Variable Display';
                font-size: 11px;
            }
            QListWidget::item {
                height: 28px;
                border-radius: 6px;
                padding-left: 8px;
            }
            QListWidget::item:hover {
                background-color: rgba(255, 255, 255, 0.08);
                color: #ffffff;
            }
            QListWidget::item:selected {
                background-color: rgba(234, 153, 156, 0.25);
                color: #ea999c;
                font-weight: bold;
            }
        """)
        self.list_w.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self.list_w)

        self._populate()

    def _populate(self):
        self.list_w.clear()
        for raw_id in DEFAULT_IDS:
            friendly = get_friendly_id_name(raw_id)
            item = QListWidgetItem(friendly)
            item.setData(Qt.UserRole, (raw_id, friendly))
            self.list_w.addItem(item)

    def _filter_list(self, text):
        query = text.strip().lower()
        for i in range(self.list_w.count()):
            it = self.list_w.item(i)
            raw_id, friendly = it.data(Qt.UserRole)
            matches = (query in friendly.lower() or query in raw_id.lower())
            it.setHidden(not matches)

    def _on_item_clicked(self, item):
        raw_id, friendly = item.data(Qt.UserRole)
        self.id_chosen.emit(raw_id, friendly)
        self.close()

    def show_under(self, target_widget):
        self.search_box.clear()
        self._filter_list("")
        w = max(target_widget.width(), 320)
        self.setFixedWidth(w)
        p = target_widget.mapToGlobal(QPoint(0, target_widget.height() + 4))
        self.move(p)
        self.show()
        self.search_box.setFocus()


class UnifiedFindInput(QFrame):
    id_selected = pyqtSignal(str, str)
    textChanged = pyqtSignal(str)
    textEdited = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("unifiedFindInput")
        self.setFixedHeight(34)
        self._selected_id = None
        self._popup = IDDropdownPopup(self)
        self._popup.id_chosen.connect(self._on_id_chosen)

        self.setStyleSheet("""
            #unifiedFindInput {
                background-color: #121212;
                border: 1px solid #242738;
                border-radius: 10px;
            }
            #unifiedFindInput:focus-within {
                border: 1px solid #ea999c;
            }
        """)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(4, 2, 4, 2)
        lay.setSpacing(4)

        self.line_edit = QLineEdit()
        self.line_edit.setPlaceholderText("e.g. Refresh")
        self.line_edit.setStyleSheet("background: transparent; border: none; color: #ffffff; font-size: 12px; font-weight: bold; padding-left: 8px;")
        self.line_edit.textChanged.connect(self.textChanged.emit)
        self.line_edit.textEdited.connect(self._on_text_edited)
        self.line_edit.textEdited.connect(self.textEdited.emit)
        self.line_edit.installEventFilter(self)
        lay.addWidget(self.line_edit, 1)

        self.arrow_btn = QPushButton("\uE70D")
        self.arrow_btn.setFont(QFont("Segoe MDL2 Assets", 9))
        self.arrow_btn.setFixedSize(26, 26)
        self.arrow_btn.setCursor(Qt.PointingHandCursor)
        self.arrow_btn.setToolTip("Browse System IDs")
        self.arrow_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                border-radius: 6px;
                color: #8d94a6;
            }
            QPushButton:hover {
                background: rgba(234, 153, 156, 0.2);
                color: #ffffff;
            }
        """)
        self.arrow_btn.clicked.connect(self._toggle_popup)
        lay.addWidget(self.arrow_btn)

    def eventFilter(self, obj, event):
        if obj is self.line_edit and event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_Down and not self._popup.isVisible():
                self._toggle_popup()
                return True
        return super().eventFilter(obj, event)

    def _toggle_popup(self):
        if self._popup.isVisible():
            self._popup.close()
        else:
            self._popup.show_under(self)

    def _on_id_chosen(self, raw_id, friendly):
        self._selected_id = raw_id
        self.line_edit.setText(friendly)
        self.id_selected.emit(raw_id, friendly)

    def _on_text_edited(self, text):
        txt_low = text.strip().lower()
        if not txt_low:
            self._selected_id = None
            return
        matched_id = None
        for raw_id in DEFAULT_IDS:
            if get_friendly_id_name(raw_id).lower() == txt_low or raw_id.lower() == txt_low:
                matched_id = raw_id
                break
        if matched_id:
            self._selected_id = matched_id
        elif self._selected_id:
            friendly = get_friendly_id_name(self._selected_id)
            if txt_low != friendly.lower():
                self._selected_id = None

    def text(self):
        return self.line_edit.text()

    def setText(self, text):
        self.line_edit.setText(text)

    def get_selected_id(self):
        return self._selected_id or ""

    def set_id(self, raw_id):
        if not raw_id:
            self._selected_id = None
            return
        clean_id = raw_id.strip('\'" ')
        if not clean_id.startswith("id."):
            clean_id = f"id.{clean_id}"
        self._selected_id = clean_id
        friendly = get_friendly_id_name(clean_id)
        if not self.line_edit.text().strip():
            self.line_edit.setText(friendly)

    def clear_id(self):
        self._selected_id = None


class ModifyRuleEditorDialog(QDialog):
    POS_OPTIONS = ["", "top", "bottom", "1", "2", "3", "4", "5", "middle"]
    live_update = pyqtSignal(dict)
    def __init__(self, data=None, existing_rules=None, bulk_sections=None, parent=None):
        super().__init__(parent); self.data = data or {}; self._all_existing_rules = existing_rules or []; self._bulk_sections = bulk_sections or {}; self._target_existing_rule = None; self._is_loading = False; self.setMinimumWidth(720); self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint); self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet("QToolTip { background-color: #1e1e24; color: #ffffff; border: 1px solid rgba(231, 130, 132, 0.6); border-radius: 8px; padding: 6px 12px; font-family: 'Segoe UI Variable Display'; font-size: 12px; font-weight: bold; }")
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
            #mainFrame { background-color: #0E0E0E; border: 1px solid #1e2130; border-radius: 20px; } 
            QLabel { color: #ffffff; font-size: 12px; } 
            QLineEdit { background-color: #121212; border: 1px solid #242738; border-radius: 10px; padding: 7px 12px; color: #ffffff; selection-background-color: #ea999c; font-size: 12px; } 
            QLineEdit:focus { border: 1px solid #ea999c; }
            QPushButton#saveBtn { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ea999c, stop:1 #e78284); color: #ffffff; border-radius: 10px; padding: 8px 20px; font-weight: bold; font-size: 12px; border: none; } 
            QPushButton#saveBtn:hover { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ff4770, stop:1 #e01b44); }
            QPushButton#cancelBtn { background-color: #121212; border: 1px solid #282b3c; color: #d1d5db; border-radius: 10px; padding: 8px 18px; font-size: 12px; }
            QPushButton#cancelBtn:hover { background-color: #0E0E0E; color: #ffffff; }
        """)
        layout = QVBoxLayout(self); layout.setContentsMargins(0, 0, 0, 0); layout.addWidget(self.mf)
        cl = QVBoxLayout(self.mf); cl.setContentsMargins(20, 20, 20, 20); cl.setSpacing(12)
        
        # 1. Header Banner
        h_row = QHBoxLayout()
        ic_badge = QLabel("\uE713")
        ic_badge.setFixedSize(36, 36)
        ic_badge.setFont(QFont("Segoe MDL2 Assets", 14))
        ic_badge.setAlignment(Qt.AlignCenter)
        ic_badge.setStyleSheet("background: rgba(234, 153, 156, 0.15); border: 1px solid #ea999c; border-radius: 10px; color: #ea999c;")
        h_row.addWidget(ic_badge)

        h_titles = QVBoxLayout()
        h_titles.setSpacing(2)
        t1 = QLabel("Modify Rule Configuration"); t1.setStyleSheet("font-size: 16px; font-weight: bold; color: #ffffff;")
        t2 = QLabel("Adjust the settings for your rule."); t2.setStyleSheet("font-size: 11px; color: #8d94a6;")
        h_titles.addWidget(t1); h_titles.addWidget(t2)
        h_row.addLayout(h_titles, 1)

        close_btn = QPushButton("\uE711")
        close_btn.setFixedSize(30, 30)
        close_btn.setFont(QFont("Segoe MDL2 Assets", 10))
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet("QPushButton { background: #121212; border: 1px solid #282b3c; border-radius: 8px; color: #9ca3af; } QPushButton:hover { background: rgba(234, 153, 156, 0.2); border: 1px solid #ea999c; color: #ffffff; }")
        close_btn.clicked.connect(self.reject)
        h_row.addWidget(close_btn)
        cl.addLayout(h_row)
        
        # Non-interruptive info banner
        self.banner_frame = QFrame(self.mf)
        self.banner_frame.setObjectName("bannerFrame")
        self.banner_frame.setStyleSheet("""
            #bannerFrame {
                background-color: rgba(140, 170, 238, 0.12);
                border: 1px solid rgba(140, 170, 238, 0.35);
                border-radius: 10px;
            }
        """)
        banner_l = QHBoxLayout(self.banner_frame)
        banner_l.setContentsMargins(10, 6, 10, 6)
        banner_l.setSpacing(8)
        self.banner_icon = QLabel("\uE946")
        self.banner_icon.setFont(QFont("Segoe MDL2 Assets", 11))
        self.banner_icon.setStyleSheet("color: #8caaee; background: transparent; border: none;")
        banner_l.addWidget(self.banner_icon)
        self.banner_label = QLabel("")
        self.banner_label.setFont(QFont("Segoe UI Variable Display", 9, QFont.Bold))
        self.banner_label.setStyleSheet("color: #c6d0f5; background: transparent; border: none;")
        banner_l.addWidget(self.banner_label, 1)
        self.banner_frame.hide()
        cl.addWidget(self.banner_frame)
        
        # Step 1: Target Criteria
        s1_row = QHBoxLayout()
        s1_badge = QLabel("1")
        s1_badge.setFixedSize(20, 20)
        s1_badge.setAlignment(Qt.AlignCenter)
        s1_badge.setStyleSheet("background: #ea999c; color: #ffffff; font-weight: bold; border-radius: 10px; font-size: 11px;")
        s1_row.addWidget(s1_badge)
        s1_title = QLabel("Target Criteria"); s1_title.setStyleSheet("font-weight: bold; font-size: 13px; color: #ffffff;")
        s1_row.addWidget(s1_title); s1_row.addStretch()
        cl.addLayout(s1_row)

        tg = QFrame(); tg.setObjectName("targetGroup"); tg.setStyleSheet("#targetGroup { background: transparent; } #targetGroup > QLabel, #targetGroup QLabel { font-size: 13px; font-weight: bold; color: #ffffff; background: transparent; padding: 0; border: none; }"); tl = QGridLayout(tg); tl.setVerticalSpacing(10); tl.setHorizontalSpacing(12); tl.setContentsMargins(0, 0, 0, 0); cl.addWidget(tg)
        
        find_row = QHBoxLayout()
        find_row.setSpacing(8)
        self.f_inp = UnifiedFindInput(self)
        self.f_inp.id_selected.connect(self._on_id_selected)
        find_row.addWidget(self.f_inp, 1)

        self.match_mode_btn = MatchModeButton(self)
        self.match_mode_btn.mode_changed.connect(lambda _: self.live_update.emit(self.get_data()))
        find_row.addWidget(self.match_mode_btn)

        tl.addWidget(QLabel("Find Title:"), 0, 0, Qt.AlignLeft | Qt.AlignVCenter); tl.addLayout(find_row, 0, 1)
        self.i_inp = PillLineEdit("e.g. open with"); tl.addWidget(QLabel("In Menu:"), 1, 0, Qt.AlignLeft | Qt.AlignVCenter); tl.addWidget(self.i_inp, 1, 1)
        
        # Step 2: Actions to Perform
        s2_row = QHBoxLayout()
        s2_badge = QLabel("2")
        s2_badge.setFixedSize(20, 20)
        s2_badge.setAlignment(Qt.AlignCenter)
        s2_badge.setStyleSheet("background: #ea999c; color: #ffffff; font-weight: bold; border-radius: 10px; font-size: 11px;")
        s2_row.addWidget(s2_badge)
        s2_title = QLabel("Actions to Perform"); s2_title.setStyleSheet("font-weight: bold; font-size: 13px; color: #ffffff;")
        s2_row.addWidget(s2_title); s2_row.addStretch()
        cl.addLayout(s2_row)

        ag = QFrame(); ag.setObjectName("actionsGroup"); ag.setStyleSheet("#actionsGroup { background: transparent; } #actionsGroup > QLabel, #actionsGroup QLabel { font-size: 13px; font-weight: bold; color: #ffffff; background: transparent; padding: 0; border: none; }"); al = QGridLayout(ag); al.setVerticalSpacing(10); al.setHorizontalSpacing(12); al.setContentsMargins(0, 0, 0, 0); cl.addWidget(ag)
        self.ti_inp = PillLineEdit("Enter a new title (optional)"); al.addWidget(QLabel("New Title:"), 0, 0, Qt.AlignLeft | Qt.AlignVCenter); al.addWidget(self.ti_inp, 0, 1)
        
        ic_row = QHBoxLayout()
        ic_row.setSpacing(8)
        
        self.ic_prev_lbl = AnimatedGlowPreviewLabel()
        self.ic_prev_lbl.clicked.connect(self._open_glyph_browser)
        
        self.c_container = QWidget()
        self.c_container.setStyleSheet("background: transparent; border: none;")
        self.c_lay = QHBoxLayout(self.c_container)
        self.c_lay.setContentsMargins(0, 0, 0, 0)
        self.c_lay.setSpacing(6)
        self.c_lay.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        
        self.ic_inp = PillLineEdit("e.g. \\uE102, image path, or image.res(...)"); self.ic_inp.textChanged.connect(self._update_colors_ui)
        self.ic_inp.textChanged.connect(lambda t: self.ic_prev_lbl.set_asset(t))
        
        btn_action_style = """
            QPushButton {
                background: #121212;
                border: 1px solid #242738;
                border-radius: 10px;
                color: #9ca3af;
                padding: 0;
            }
            QPushButton:hover {
                background: rgba(234, 153, 156, 0.2);
                border: 1px solid #ea999c;
                color: #ffffff;
            }
        """
        
        self.ic_inherit = QPushButton("\uE777")
        self.ic_inherit.setFont(QFont('Segoe MDL2 Assets', 12)); self.ic_inherit.setFixedSize(34, 34)
        self.ic_inherit.setToolTip("Inherit Icon from Target Command/File"); self.ic_inherit.clicked.connect(self._inherit_icon); self.ic_inherit.setStyleSheet(btn_action_style); self.ic_inherit.setCursor(Qt.PointingHandCursor)

        self.ic_remove = QPushButton("\uE74D")
        self.ic_remove.setFont(QFont('Segoe MDL2 Assets', 12)); self.ic_remove.setFixedSize(34, 34)
        self.ic_remove.setToolTip("Remove Icon"); self.ic_remove.setStyleSheet("""
            QPushButton {
                background: #121212;
                border: 1px solid #242738;
                border-radius: 10px;
                color: #9ca3af;
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

        ic_row.addWidget(self.ic_prev_lbl)
        ic_row.addWidget(self.c_container)
        ic_row.addWidget(self.ic_inp, 1)
        ic_row.addWidget(self.ic_inherit)
        ic_row.addWidget(self.ic_remove)
        al.addWidget(QLabel("Icon / Image:"), 1, 0, Qt.AlignLeft | Qt.AlignVCenter); al.addLayout(ic_row, 1, 1)
        self.ic_prev_lbl.set_asset(self.ic_inp.text()); self._update_colors_ui()
        
        self.vis_widget = VisibilityWidget()
        self.vis_widget.set_value(str(self.data.get('vis', '')))
        self.vis_widget.valueChanged.connect(lambda _: self.live_update.emit(self.get_data()))
        al.addWidget(QLabel("Visibility:"), 2, 0, Qt.AlignLeft | Qt.AlignVCenter); al.addWidget(self.vis_widget, 2, 1)

        self.type_widget = TypeWidget()
        self.type_widget.valueChanged.connect(lambda _: self.live_update.emit(self.get_data()))
        al.addWidget(QLabel("Show in:"), 3, 0, Qt.AlignLeft | Qt.AlignVCenter); al.addWidget(self.type_widget, 3, 1)

        self.m_inp = ModernComboBox(context_key="menu"); self.m_inp.setEditable(False)
        self.m_inp.addItems(["None", "Main", "Options"])
        self.m_inp.setFixedWidth(150)

        self.p_inp = ModernComboBox(context_key="pos"); self.p_inp.addItems(self.POS_OPTIONS)
        self.p_inp.setFixedWidth(150)

        self.sep_box = ModernComboBox(context_key="sep"); self.sep_box.addItems(["None", "Before", "After", "Both"])
        self.sep_box.setFixedWidth(150)

        al.addWidget(QLabel("Move to:"), 4, 0, Qt.AlignLeft | Qt.AlignVCenter)
        al.addWidget(self.m_inp, 4, 1, Qt.AlignLeft | Qt.AlignVCenter)

        al.addWidget(QLabel("Position:"), 5, 0, Qt.AlignLeft | Qt.AlignVCenter)
        al.addWidget(self.p_inp, 5, 1, Qt.AlignLeft | Qt.AlignVCenter)

        al.addWidget(QLabel("Separator:"), 6, 0, Qt.AlignLeft | Qt.AlignVCenter)
        al.addWidget(self.sep_box, 6, 1, Qt.AlignLeft | Qt.AlignVCenter)

        self.i_inp.textChanged.connect(self._update_move_to_options)
        self._update_move_to_options(self.i_inp.text())

        for w in [self.f_inp, self.i_inp, self.ti_inp, self.ic_inp]: w.textChanged.connect(lambda: self.live_update.emit(self.get_data()))
        for w in [self.m_inp, self.p_inp, self.sep_box]: (w.currentTextChanged.connect(lambda: self.live_update.emit(self.get_data())) if hasattr(w, 'currentTextChanged') else w.currentIndexChanged.connect(lambda: self.live_update.emit(self.get_data())))
        btns = QHBoxLayout()
        c = PillPushButton("Cancel", "secondary", height=34)
        c.setFixedWidth(85)
        c.clicked.connect(self.reject)
        s = PillPushButton("Save Rule", "primary", height=34)
        s.setFixedWidth(100)
        s.clicked.connect(self.accept)
        btns.addStretch()
        btns.addWidget(c)
        btns.addWidget(s)
        cl.addLayout(btns)
    def _update_move_to_options(self, text=None):
        prev = self.m_inp.currentText()
        self.m_inp.blockSignals(True)
        self.m_inp.clear()
        base = ["None", "Main", "Options"]
        self.m_inp.addItems(base)
        for cm in self._custom_menus:
            if cm not in base:
                self.m_inp.addItem(cm)
        idx = self.m_inp.findText(prev)
        if idx >= 0:
            self.m_inp.setCurrentIndex(idx)
        elif prev:
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
            'where.id': 'Target ID',
            'in': 'In Menu',
            'title': 'New Title',
            'menu': 'Move to',
            'pos': 'Position',
            'vis': 'Visibility',
            'sep': 'Separator',
            'type': 'Show in',
            'icon': 'Icon / Image'
        }
        def normalize_vis(v):
            vl = str(v or '').strip('\'" ').lower().replace('"', '').replace("'", "").replace(" ", "")
            if not vl or vl in ("normal", "alwaysvisible", "vis.normal", "1"):
                return ""
            if ('key.shift' in vl or 'key.control' in vl or 'key.ctrl' in vl or 'key.lbutton' in vl or 'key.caps' in vl) and 'hidden' in vl:
                return "main"
            if vl in ("vis.remove", "key.remove", "vis.hidden", "key.hidden", "remove", "hidden", "0"):
                return "hide"
            if vl in ("key.shift()", "vis.shift()", "vis.shift", "shift", "key.shift"):
                return "shift"
            if vl in ("key.control()", "key.ctrl()", "vis.control()", "vis.control", "vis.ctrl", "control", "ctrl", "key.control", "key.ctrl"):
                return "ctrl"
            if vl in ("key.capslock()", "key.caps()", "vis.capslock()", "vis.capslock", "vis.caps", "capslock", "caps", "key.capslock", "key.caps"):
                return "caps"
            if vl in ("key.lbutton()", "key.lmb()", "vis.lbutton()", "vis.lbutton", "vis.lmb", "lbutton", "lmb", "key.lbutton"):
                return "lmb"
            return vl

        def format_user_friendly(prop_key, val):
            val_clean = str(val or '').strip('\'" ')
            if prop_key == 'where.id':
                return get_friendly_id_name(val_clean) if val_clean else "(none)"
            if prop_key == 'vis':
                norm = normalize_vis(val_clean)
                if not norm: return "Normal"
                if norm == "main": return "Main"
                if norm == "hide": return "Hide"
                if norm == "shift": return "Shift"
                if norm == "ctrl": return "Ctrl"
                if norm == "caps": return "Caps"
                if norm == "lmb": return "LMB"
                return val_clean
            if prop_key == 'sep':
                vl = val_clean.lower()
                if vl in ("true", "1", "before"): return "Before"
                if vl == "after": return "After"
                if vl == "both": return "Both"
                if vl in ("false", "0", "none", ""): return "None"
                return val_clean.title()
            if prop_key == 'type':
                if not val_clean or val_clean.lower() == 'all': return "All"
                return val_clean
            if prop_key == 'menu':
                if val is None: return "None"
                vl = val_clean.lower()
                if vl == "none": return "None"
                if not vl or vl in ("main", "menu.main"): return "Main"
                if vl in ("options", "title.options"): return "Options"
                return val_clean
            return val_clean or "(empty)"

        for k in ['find', 'where.id', 'in', 'title', 'menu', 'pos', 'vis', 'sep', 'type']:
            v1 = str(d1.get(k, '')).strip('\'" ')
            v2 = str(d2.get(k, '')).strip('\'" ')
            if k == 'where.id':
                if v1 != v2:
                    display_k = key_names.get(k, k.title())
                    changes.append(f"{display_k}: {format_user_friendly(k, v2)} ➔ {format_user_friendly(k, v1)}")
                continue
            if k == 'find':
                if v1.startswith('*') and v1.endswith('*') and v1.strip('*') == v2: continue
                if v2.startswith('*') and v2.endswith('*') and v2.strip('*') == v1: continue
            if k == 'vis':
                if normalize_vis(v1) == normalize_vis(v2):
                    continue
                display_k = key_names.get(k, k.title())
                changes.append(f"{display_k}: {format_user_friendly(k, v2)} ➔ {format_user_friendly(k, v1)}")
                continue
            if k == 'type':
                v1_clean = str(d1.get('type') or '').strip('\'" ')
                v2_clean = str(d2.get('type') or '').strip('\'" ')
                set1 = set(p.strip().lower() for p in v1_clean.split('|') if p.strip() and p.strip().lower() not in ('all', '*'))
                set2 = set(p.strip().lower() for p in v2_clean.split('|') if p.strip() and p.strip().lower() not in ('all', '*'))
                set1 = {'dir' if x == 'directory' else x for x in set1}
                set2 = {'dir' if x == 'directory' else x for x in set2}
                if set1 == set2:
                    continue
                display_k = key_names.get(k, k.title())
                changes.append(f"{display_k}: {format_user_friendly(k, v2_clean)} ➔ {format_user_friendly(k, v1_clean)}")
                continue
            if k == 'menu':
                v1_raw = d1.get('menu')
                v2_raw = d2.get('menu')
                if v1_raw is None and v2_raw is None:
                    continue
                v1_norm = "None" if v1_raw is None else ("Main" if str(v1_raw).strip('\'"').lower() in ("", "main", "menu.main") else str(v1_raw).strip('\'"'))
                v2_norm = "None" if v2_raw is None else ("Main" if str(v2_raw).strip('\'"').lower() in ("", "main", "menu.main") else str(v2_raw).strip('\'"'))
                if v1_norm.lower() == v2_norm.lower(): continue
                display_k = key_names.get(k, k.title())
                changes.append(f"{display_k}: {format_user_friendly(k, v2_raw)} ➔ {format_user_friendly(k, v1_raw)}")
                continue
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
        if not hasattr(self, 'c_lay'): return
        while self.c_lay.count():
            it = self.c_lay.takeAt(0)
            if it.widget(): it.widget().deleteLater()
        colors = _extract_all_colors(self.ic_inp.text())
        theme_cs = _get_theme_glyph_colors()
        codes = _extract_glyph_codes(self.ic_inp.text())
        num_pellets = len(codes) if codes else (len(colors) if colors else 1)
        
        for i in range(min(max(num_pellets, len(colors)), 2)):
            c = colors[i] if i < len(colors) else None
            btn = ColorCircleButton(c or theme_cs[min(i, 1)], tooltip=f"Color for Glyph {i+1}")
            btn.colorSelected.connect(lambda hex_c, idx=i, oc=c: self._on_color_chosen(idx, oc, hex_c))
            self.c_lay.addWidget(btn)

        val = self.ic_inp.text()
        if codes and any(colors):
            sync_btn = QPushButton("\uE777")
            sync_btn.setFont(QFont("Segoe MDL2 Assets", 10))
            sync_btn.setFixedSize(26, 26)
            sync_btn.setCursor(Qt.PointingHandCursor)
            sync_btn.setStyleSheet("QPushButton { background: #121212; border: 1px solid #363a4f; border-radius: 13px; color: #9ca3af; } QPushButton:hover { border: 1px solid #ea999c; color: #ffffff; }")
            sync_btn.setToolTip("Sync with Theme (Remove custom colors)")
            sync_btn.clicked.connect(self._reset_glyph_colors)
            self.c_lay.addWidget(sync_btn)

    def _on_color_chosen(self, idx, old_color, hex_color):
        val = self.ic_inp.text().strip()
        codes = _extract_glyph_codes(val)
        if codes:
            new_val = _get_new_asset_value(val, old_color, hex_color, idx=idx)
            self.ic_inp.setText(new_val)
            self._update_icon_preview(new_val)
        else:
            path, _ = _extract_img_path_and_color(val)
            resolved = _resolve_app_dir_path(path)
            if resolved and os.path.exists(resolved):
                new_asset_path, _ = save_local_icon(resolved, hex_color, True)
                if hasattr(self, 'created_temp_icons'):
                    self.created_temp_icons.append(new_asset_path)
                self.ic_inp.setText(f"'{new_asset_path}'")
                self._update_icon_preview(f"'{new_asset_path}'")
        if hasattr(self, 'live_update'):
            self.live_update.emit(self.get_data())

    def _reset_glyph_colors(self):
        codes = _extract_glyph_codes(self.ic_inp.text())
        if codes: self.ic_inp.setText(_build_glyph_val(codes, []))
        self.live_update.emit(self.get_data())

    def _update_icon_preview(self, text):
        if hasattr(self, 'ic_prev_lbl'):
            self.ic_prev_lbl.set_asset(text)

    def _on_id_selected(self, sel_id, friendly_name):
        if self._is_loading:
            return
        if not sel_id:
            self.banner_frame.hide()
            self._target_existing_rule = None
            self.live_update.emit(self.get_data())
            return

        target_id = sel_id.lower().strip()
        clean_bare = target_id.replace("id.", "").strip()

        matching = None
        for r in self._all_existing_rules:
            p = r.get('props', {}) if isinstance(r, dict) else {}
            wid = str(p.get('where.id', '')).lower().strip('\'" ')
            if wid and (wid == target_id or wid == clean_bare or f"id.{wid}" == target_id):
                matching = r
                break
            where = str(p.get('where', '')).lower().strip('\'" ')
            if where:
                m = re.search(r'\b(id\.\w+)\b', where)
                if m and m.group(1) == target_id:
                    matching = r
                    break
                if where == target_id or where == clean_bare:
                    matching = r
                    break

        if matching:
            self._target_existing_rule = matching
            self.banner_label.setText(f"Rule for '{friendly_name}' already exists \u2014 loaded existing settings to edit.")
            self.banner_frame.show()
            self.load_data(matching, sync_id=False)
            self.f_inp.set_id(sel_id)
            self.live_update.emit(self.get_data())
            return

        bulk_rule = None
        h_ids = [i.lower() for i in self._bulk_sections.get('hide', [])]
        s_ids = [i.lower() for i in self._bulk_sections.get('shift', [])]
        m_ids = [i.lower() for i in self._bulk_sections.get('more', [])]

        if target_id in s_ids or clean_bare in s_ids or f"id.{target_id}" in s_ids:
            bulk_rule = {'find': friendly_name, 'where.id': sel_id, 'vis': 'key.shift()'}
            self.banner_label.setText(f"'{friendly_name}' is in Shift section \u2014 loaded existing settings to edit.")
        elif target_id in h_ids or clean_bare in h_ids or f"id.{target_id}" in h_ids:
            bulk_rule = {'find': friendly_name, 'where.id': sel_id, 'vis': 'vis.remove'}
            self.banner_label.setText(f"'{friendly_name}' is in Remove/Hide section \u2014 loaded existing settings to edit.")
        elif target_id in m_ids or clean_bare in m_ids or f"id.{target_id}" in m_ids:
            bulk_rule = {'find': friendly_name, 'where.id': sel_id, 'menu': 'options'}
            self.banner_label.setText(f"'{friendly_name}' is in Options section \u2014 loaded existing settings to edit.")

        if bulk_rule:
            self._target_existing_rule = None
            self.banner_frame.show()
            self.load_data(bulk_rule, sync_id=False)
            self.f_inp.set_id(sel_id)
        else:
            self._target_existing_rule = None
            self.banner_frame.hide()
            self.f_inp.set_id(sel_id)

        self.live_update.emit(self.get_data())

    def load_data(self, d, sync_id=True):
        self._is_loading = True
        try:
            d = d.get('props') if (isinstance(d, dict) and 'props' in d) else d
            if not isinstance(d, dict):
                return
            act = d.get('action') if isinstance(d.get('action'), dict) else {}
            
            if sync_id:
                wid = d.get('where.id') or act.get('where.id')
                if not wid and d.get('where'):
                    w_val = str(d['where']).strip()
                    m_id = re.search(r'\b(id\.\w+)\b', w_val)
                    if m_id:
                        wid = m_id.group(1)
                if wid:
                    clean_wid = str(wid).strip('\'" ')
                    if not clean_wid.startswith('id.'):
                        clean_wid = f"id.{clean_wid}"
                    self.f_inp.set_id(clean_wid)
                else:
                    self.f_inp.clear_id()

            self.vis_widget.set_value(d.get('vis') or act.get('vis', ''))
            self.type_widget.set_value(d.get('type') or act.get('type', ''))

            f = d.get('find') or act.get('find', '')
            if f:
                mode = "contains"; clean_f = str(f)
                if clean_f.startswith('"') and clean_f.endswith('"'): mode = "exact"; clean_f = clean_f[1:-1]
                elif clean_f.startswith('*') and clean_f.endswith('*'): mode = "contains"; clean_f = clean_f[1:-1]
                elif clean_f.startswith('*'): mode = "ends"; clean_f = clean_f[1:]
                elif clean_f.endswith('*'): mode = "starts"; clean_f = clean_f[:-1]
                self.f_inp.setText(clean_f.strip('\'"'))
                self.match_mode_btn.set_mode(mode)
            elif sync_id and not self.f_inp.get_selected_id():
                self.f_inp.setText("")
            
            self.i_inp.setText(str(d.get('in') or act.get('in', '')).strip('\'"'))
            self.ti_inp.setText(str(d.get('title') or act.get('title', '')).strip('\'"'))
            
            m_val = d.get('menu') if 'menu' in d else act.get('menu', None)
            if m_val is None:
                self.m_inp.setCurrentText("None")
            else:
                m = str(m_val).strip('\'"')
                m_low = m.lower()
                if not m or m_low in ("main", "menu.main"): self.m_inp.setCurrentText("Main")
                elif m_low in ("options", "title.options"): self.m_inp.setCurrentText("Options")
                else:
                    if m not in [self.m_inp.itemText(i) for i in range(self.m_inp.count())]:
                        self.m_inp.addItem(m)
                    self.m_inp.setCurrentText(m)

            raw_ic = str(d.get('icon') or d.get('image') or act.get('icon') or act.get('image') or '')
            self.ic_inp.setText(raw_ic); self._update_icon_preview(self.ic_inp.text())
            p = str(d.get('pos') or act.get('pos', '')).strip('\'"')
            (self.p_inp.setCurrentText(p) if p in self.POS_OPTIONS else (self.p_inp.addItem(p), self.p_inp.setCurrentText(p)))
            s = str(d.get('sep') if 'sep' in d else act.get('sep', '')).strip('\'"')
            (self.sep_box.setCurrentText("None") if not s else self.sep_box.setCurrentText("Before") if (s.lower() in ('true', '1')) else self.sep_box.setCurrentText(s.title()))
        finally:
            self._is_loading = False

    def get_data(self):
        if self._target_existing_rule and isinstance(self._target_existing_rule, dict):
            res = self._target_existing_rule.get('props', {}).copy()
        else:
            res = self.data.copy()
            
        sel_id = self.f_inp.get_selected_id()
        if sel_id:
            res['where.id'] = sel_id
            f = self.f_inp.text().strip()
            if not f:
                f = get_friendly_id_name(sel_id)
            mode = self.match_mode_btn.get_mode()
            if mode == "exact": f = f'"{f}"'
            elif mode == "ends": f = f'*{f}'
            elif mode == "starts": f = f'{f}*'
            res['find'] = f
        else:
            res.pop('where.id', None)
            f = self.f_inp.text().strip()
            if f:
                mode = self.match_mode_btn.get_mode()
                if mode == "exact": f = f'"{f}"'
                elif mode == "ends": f = f'*{f}'
                elif mode == "starts": f = f'{f}*'
                res['find'] = f
            else:
                res.pop('find', None)
        
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
        if type_val and type_val.lower() != 'all':
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

    def __init__(self, modify_nss_path, shell_nss_path, project_root):
        super().__init__()
        _init_nilesoft_font()
        self.filepath = modify_nss_path
        self.shell_nss_path = shell_nss_path
        self.project_root = project_root
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(15, 15, 15, 15)
        self.auto_save = False
        self.load_and_init_ui()

    @property
    def is_dirty(self):
        return getattr(self.edit_pg, 'is_dirty', False) if hasattr(self, 'edit_pg') else False

    @is_dirty.setter
    def is_dirty(self, val):
        if hasattr(self, 'edit_pg'):
            self.edit_pg.is_dirty = val

    @property
    def custom_rules(self):
        return getattr(self.edit_pg, 'custom_rules', []) if hasattr(self, 'edit_pg') else []

    @custom_rules.setter
    def custom_rules(self, val):
        if hasattr(self, 'edit_pg'):
            self.edit_pg.custom_rules = val

    def _switch_tab(self, idx):
        if idx == 0:
            self.edit_tab_btn.setChecked(True)
            self.edit_pg.refresh()
        elif idx == 1:
            self.builder_tab_btn.setChecked(True)
            self.builder_pg.refresh()
        self.stacked_widget.setCurrentIndex(idx)

    def load_and_init_ui(self):
        old_idx = -1
        if hasattr(self, 'stacked_widget') and self.stacked_widget is not None:
            old_idx = self.stacked_widget.currentIndex()

        while self.main_layout.count():
            it = self.main_layout.takeAt(0)
            if it.widget():
                it.widget().setParent(None)
                it.widget().deleteLater()
            elif it.layout():
                while it.layout().count():
                    sub = it.layout().takeAt(0)
                    if sub.widget():
                        sub.widget().setParent(None)
                        sub.widget().deleteLater()

        # Pill-shaped Segmented Tabs Container (Edit / Add)
        self.tab_container = QFrame()
        self.tab_container.setObjectName("pillTabContainer")
        self.tab_container.setStyleSheet("background-color: transparent; border: none; padding: 0px;")
        tab_layout = QHBoxLayout(self.tab_container)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.setSpacing(4)

        self.edit_tab_btn = PillTabButton(" Edit", 0xE104, height=30)
        self.edit_tab_btn.clicked.connect(lambda: self._switch_tab(0))

        self.builder_tab_btn = PillTabButton(" Add", 0xE710, height=30)
        self.builder_tab_btn.clicked.connect(lambda: self._switch_tab(1))

        self.tab_group = QButtonGroup(self)
        self.tab_group.setExclusive(True)
        self.tab_group.addButton(self.edit_tab_btn)
        self.tab_group.addButton(self.builder_tab_btn)

        tab_layout.addWidget(self.edit_tab_btn)
        tab_layout.addWidget(self.builder_tab_btn)

        top_tab_bar = QHBoxLayout()
        top_tab_bar.setContentsMargins(0, 0, 0, 8)
        top_tab_bar.addWidget(self.tab_container)
        top_tab_bar.addStretch()
        self.main_layout.addLayout(top_tab_bar)

        self.edit_pg = ImportsWidget(self.project_root, self.shell_nss_path, self.filepath, self)
        self.edit_pg.reload_requested.connect(self.reload_requested.emit)
        self.edit_pg.rules_saved.connect(self.rules_saved.emit)
        self.imports_pg = self.edit_pg

        from menu_builder_widget import MenuBuilderWidget
        self.builder_pg = MenuBuilderWidget(self.project_root, self.shell_nss_path, self)
        self.builder_pg.reload_requested.connect(self.reload_requested.emit)

        self.stacked_widget = QStackedWidget()
        self.stacked_widget.addWidget(self.edit_pg)
        self.stacked_widget.addWidget(self.builder_pg)

        self._switch_tab(old_idx if old_idx in (0, 1) else 0)
        self.main_layout.addWidget(self.stacked_widget)

    def refresh_rules_model(self, preserve_item=None):
        if hasattr(self, 'edit_pg'):
            self.edit_pg.refresh_rules(preserve_item=preserve_item)

    def refresh_ui(self):
        if hasattr(self, 'edit_pg'):
            self.edit_pg.refresh()

    def save_all_modifications(self, preserve_item=None, base_content=None, status_msg="Rules Saved"):
        if hasattr(self, 'edit_pg'):
            self.edit_pg.save_all_modifications(preserve_item=preserve_item, base_content=base_content, status_msg=status_msg)

    def add_new_rule_dialog(self):
        if hasattr(self, 'edit_pg'):
            self.edit_pg.add_new_rule_dialog()

    def edit_rule(self, item):
        if hasattr(self, 'edit_pg'):
            self.edit_pg.edit_rule(item)

    def delete_rule(self, item):
        if hasattr(self, 'edit_pg'):
            self.edit_pg.delete_rule(item)

    def revert_changes(self):
        if hasattr(self, 'edit_pg'):
            self.edit_pg.revert_changes()

    def save_ids(self, preview=False):
        pass


def read_file(path):
    if not path or not os.path.exists(path):
        return ""
    import time
    for attempt in range(3):
        try:
            with open(path, 'r', encoding='utf-8-sig', errors='replace') as f:
                return f.read()
        except PermissionError:
            if attempt < 2:
                time.sleep(0.05)
            else:
                return ""
        except Exception:
            return ""
    return ""
def write_file(path, content, on_success=None, on_error=None): 
    from utils import global_undo_stack, FileChangeCommand
    old_content = read_file(path)
    cmd = FileChangeCommand(path, old_content, content, on_success, on_error)
    global_undo_stack.push(cmd)
    
def extract_ids_from_section(content, name):
    sec = name.lower().strip()
    pat = r"(?:hide|remove)" if sec in ("hide", "remove") else (r"(?:more|options)" if sec in ("more", "options") else r"shift")
    p = re.compile(r"//\s*" + pat + r"\b.*?where=this\.id\((.*?)\)", re.DOTALL | re.IGNORECASE)
    m = p.search(content)
    return [l.strip().rstrip(',') for l in m.group(1).split('\n') if l.strip().startswith("id.")] if m else []

def update_section(content, sm, em, ids):
    low = sm.lower()
    pat = r"(?:hide|remove)" if ("hide" in low or "remove" in low) else (r"(?:more|options)" if ("more" in low or "options" in low) else (r"shift" if "shift" in low else None))
    if pat:
        p = re.compile(r"(//\s*" + pat + r"\b.*?where=this\.id\()(.*?)(\))", re.DOTALL | re.IGNORECASE)
        m = p.search(content)
        if m:
            formatted_ids = "\n" + ",\n".join([f"    {i}" for i in ids]) + "\n"
            return content[:m.start(2)] + formatted_ids + content[m.end(2):]
    s = content.find(sm)
    e = content.find(em, s)
    return content if (s == -1 or e == -1) else content[:s + len(sm)] + "\n" + ",\n".join([f"    {i}" for i in ids]) + "\n" + content[e:]


