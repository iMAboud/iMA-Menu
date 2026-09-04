import os
import re
import uuid
import subprocess
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QFileDialog, QMessageBox, QMenu, QAction,
    QInputDialog, QButtonGroup, QDialog, QSizePolicy, QPlainTextEdit
)
from PyQt5.QtCore import Qt, pyqtSignal, QSize, QPoint
from PyQt5.QtGui import QFont, QIcon, QColor

from utils import (
    PillPushButton, PillLineEdit, ModernComboBox, render_nss_asset_pixmap, get_mdl2_icon,
    validate_nss_syntax, FlowLayout
)
from nss_parser import (
    read_file, safe_file_write, find_items_and_menus, format_nss_value, _get_custom_menus_from_nss,
    parse_nss_args, NSSLexer
)
from modify_widget import (
    AnimatedGlowPreviewLabel, VisibilityWidget, TypeWidget, GlyphBrowserDialog,
    LocalIconTintDialog, ColorCircleButton, FilterBar, _extract_all_colors,
    _extract_glyph_codes, _get_theme_glyph_colors, ModifyRuleEditorDialog
)
from nss_error_monitor import parse_log_entries


# Curated list of Nilesoft Shell arguments with user-friendly descriptions
CURATED_ARGS = [
    # Paths & Files
    ("📁 Selected Path (Quoted)", '@sel.path.quote'),
    ("📁 Selected Path (Raw)", '@sel.path'),
    ("📄 File Name (Quoted)", '@sel.file.quote'),
    ("📄 File Name (Raw)", '@sel.file'),
    ("📂 Directory (Quoted)", '@sel.dir.quote'),
    ("📂 Directory (Raw)", '@sel.dir'),
    ("🏷️ File Title (No Ext)", '@sel.title'),
    ("🏷️ File Extension", '@sel.ext'),
    ("📑 All Selected (Lines)", 'sel(true, "\\n")'),
    ("📑 All Selected (Spaces)", 'sel(false, " ")'),
    ("🔢 Selected Count", '@sel.count'),
    # Command Prompt (cmd.exe)
    ("💻 CMD: Open Here", '/k pushd "@sel.path"'),
    ("💻 CMD: Run & Exit", '/c "@sel.path"'),
    ("💻 CMD: Run Script", '/k call "@sel.path"'),
    ("💻 CMD: Keep Open", '/k'),
    # PowerShell
    ("⚡ PS: Open Folder Here", '-NoExit -Command "Set-Location -LiteralPath \'@sel.path\'"'),
    ("⚡ PS: Run Script File", '-NoProfile -ExecutionPolicy Bypass -File "@sel.path"'),
    ("⚡ PS: Hidden Window", '-WindowStyle Hidden'),
    # Python
    ("🐍 Python: Run File", '/k python "@sel.path.quote"'),
    ("🐍 Python: Install Req", '-m pip install -r "@sel.path.quote"'),
    # Admin & System
    ("🛡️ Run as Admin", 'runas'),
    ("🖥️ Windows Dir", '@sys.bin'),
    ("🖥️ Desktop Dir", '@sys.desktop'),
    ("🖥️ Temp Dir", '@sys.temp'),
    # Nilesoft Commands
    ("📋 Copy Path to Clipboard", 'command.copy(sel(true, "\\n"))'),
    ("🔄 Restart Explorer", 'command.restart_explorer'),
    ("👁️ Toggle Hidden Files", 'command.toggle_hidden'),
]


def get_curated_args_for_command(cmd_text=""):
    """Returns curated arguments prioritized based on the command."""
    cmd_lower = (cmd_text or "").lower()
    if "powershell" in cmd_lower or "pwsh" in cmd_lower:
        priority_prefixes = ["⚡", "📁", "📄"]
    elif "cmd" in cmd_lower or ".bat" in cmd_lower or ".cmd" in cmd_lower:
        priority_prefixes = ["💻", "📁", "📄"]
    elif "python" in cmd_lower or ".py" in cmd_lower:
        priority_prefixes = ["🐍", "📁", "📄"]
    else:
        priority_prefixes = ["📁", "📄", "📂", "🏷️", "📑"]

    top = []
    for prefix in priority_prefixes:
        for item in CURATED_ARGS:
            if item[0].startswith(prefix) and item not in top:
                top.append(item)

    others = [item for item in CURATED_ARGS if item not in top]
    return top + others


class StyledConfirmDialog(QDialog):
    """Sleek modal dialog for delete/action confirmation matching launcher theme."""
    def __init__(self, title, message, parent=None, confirm_text="Delete", danger=True):
        super().__init__(parent)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMinimumWidth(440)
        self._drag_pos = None

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        frame = QFrame()
        frame.setObjectName("confirmFrame")
        frame.setStyleSheet("""
            #confirmFrame {
                background-color: #0E0E0E;
                border: 1.5px solid #1e2130;
                border-radius: 20px;
            }
        """)
        outer.addWidget(frame)

        cl = QVBoxLayout(frame)
        cl.setContentsMargins(24, 22, 24, 22)
        cl.setSpacing(14)

        # Header Row
        h = QHBoxLayout()
        ic = QLabel()
        ic.setFixedSize(36, 36)
        ic.setFont(QFont("Segoe MDL2 Assets", 14))
        ic.setAlignment(Qt.AlignCenter)
        ic.setText("\uE74D" if danger else "\uE7BA")
        accent = "#e78284" if danger else "#8caaee"
        ic.setStyleSheet(f"background: rgba(231, 130, 132, 0.15); border: 1px solid {accent}; border-radius: 10px; color: {accent};")
        h.addWidget(ic)

        tl = QLabel(title)
        tl.setStyleSheet("color: #ffffff; font-size: 16px; font-weight: bold; background: transparent; border: none;")
        h.addWidget(tl, 1)

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(28, 28)
        close_btn.setFont(QFont("Segoe UI Variable Display", 10, QFont.Bold))
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.10);
                border-radius: 8px;
                color: #838ba7;
            }
            QPushButton:hover {
                background: rgba(231, 130, 132, 0.25);
                border: 1px solid #e78284;
                color: #ffffff;
            }
        """)
        close_btn.clicked.connect(self.reject)
        h.addWidget(close_btn)
        cl.addLayout(h)

        ml = QLabel(message)
        ml.setStyleSheet("color: #c6d0f5; font-size: 12px; background: transparent; border: none; line-height: 1.4;")
        ml.setWordWrap(True)
        cl.addWidget(ml)

        btns = QHBoxLayout()
        btns.setContentsMargins(0, 8, 0, 0)
        btns.addStretch()

        cancel_btn = PillPushButton("Cancel", "secondary", height=34)
        cancel_btn.setFixedWidth(85)
        cancel_btn.clicked.connect(self.reject)
        btns.addWidget(cancel_btn)

        action_btn = PillPushButton(confirm_text, "danger" if danger else "primary", height=34)
        action_btn.setFixedWidth(100)
        action_btn.clicked.connect(self.accept)
        btns.addWidget(action_btn)

        cl.addLayout(btns)

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


class PresetChip(QPushButton):
    """Clickable pill chip for quick presets (args, cmd, types, etc.)."""
    def __init__(self, text, value, parent=None):
        super().__init__(text, parent)
        self.preset_value = value
        self.setFixedHeight(24)
        self.setCursor(Qt.PointingHandCursor)
        self.setFont(QFont("Segoe UI Variable Text", 8))
        self.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.05);
                color: #c6d0f5;
                border: 1px solid rgba(255, 255, 255, 0.10);
                border-radius: 12px;
                padding: 0 10px;
            }
            QPushButton:hover {
                background: rgba(231, 130, 132, 0.20);
                color: #ffffff;
                border: 1px solid #e78284;
            }
            QPushButton:pressed {
                background: rgba(231, 130, 132, 0.35);
            }
        """)


class PipelineStepWidget(QFrame):
    """A single configurable action step in a multi-action pipeline."""
    changed = pyqtSignal()
    delete_requested = pyqtSignal()
    move_up_requested = pyqtSignal()
    move_down_requested = pyqtSignal()

    ACTION_TYPES = [
        ("🚀 Launch App / Exe", "launch"),
        ("📄 Open File or Folder", "file"),
        ("📋 Copy Path to Clipboard", "clipboard"),
        ("💻 CMD Command", "cmd"),
        ("⚡ PowerShell Command", "powershell"),
        ("🐍 Python Script", "python")
    ]

    def __init__(self, step_index=1, initial_data=None, parent=None):
        super().__init__(parent)
        self.step_index = step_index
        self.setObjectName("stepFrame")
        self.setStyleSheet("""
            #stepFrame {
                background: rgba(255, 255, 255, 0.025);
                border: 1px solid #1e2130;
                border-radius: 12px;
            }
        """)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(8)

        # Header Row
        head = QHBoxLayout()
        self.step_lbl = QLabel(f"Action Step #{step_index}")
        self.step_lbl.setFont(QFont("Segoe UI Variable Display", 9, QFont.Bold))
        self.step_lbl.setStyleSheet("color: #ea999c; background: transparent;")
        head.addWidget(self.step_lbl)
        head.addStretch()

        btn_style = """
            QPushButton {
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.09);
                border-radius: 12px;
                color: #838ba7;
                font-family: 'Segoe MDL2 Assets';
                font-size: 10px;
            }
            QPushButton:hover {
                background: rgba(231, 130, 132, 0.25);
                border: 1px solid #e78284;
                color: #ffffff;
            }
        """
        self.up_btn = QPushButton("\uE010")
        self.up_btn.setFixedSize(24, 24)
        self.up_btn.setCursor(Qt.PointingHandCursor)
        self.up_btn.setStyleSheet(btn_style)
        self.up_btn.clicked.connect(self.move_up_requested.emit)
        head.addWidget(self.up_btn)

        self.down_btn = QPushButton("\uE011")
        self.down_btn.setFixedSize(24, 24)
        self.down_btn.setCursor(Qt.PointingHandCursor)
        self.down_btn.setStyleSheet(btn_style)
        self.down_btn.clicked.connect(self.move_down_requested.emit)
        head.addWidget(self.down_btn)

        del_btn = QPushButton("✕")
        del_btn.setFixedSize(24, 24)
        del_btn.setFont(QFont("Segoe UI Variable Display", 9, QFont.Bold))
        del_btn.setCursor(Qt.PointingHandCursor)
        del_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.09);
                border-radius: 12px;
                color: #838ba7;
            }
            QPushButton:hover {
                background: rgba(231, 130, 132, 0.35);
                border: 1px solid #e78284;
                color: #ffffff;
            }
        """)
        del_btn.clicked.connect(self.delete_requested.emit)
        head.addWidget(del_btn)

        lay.addLayout(head)

        # Action Type + Path Row
        row1 = QHBoxLayout()
        row1.setSpacing(8)

        self.type_combo = ModernComboBox(context_key="action_type")
        for label, code in self.ACTION_TYPES:
            self.type_combo.addItem(label, code)
        self.type_combo.setFixedWidth(200)
        self.type_combo.currentIndexChanged.connect(self._on_type_changed)
        row1.addWidget(self.type_combo)

        self.path_inp = PillLineEdit("Target program, script, or command...")
        self.path_inp.textChanged.connect(self.changed.emit)
        row1.addWidget(self.path_inp, 1)

        self.browse_btn = QPushButton("\uE898")
        self.browse_btn.setFont(QFont("Segoe MDL2 Assets", 11))
        self.browse_btn.setFixedSize(32, 32)
        self.browse_btn.setCursor(Qt.PointingHandCursor)
        self.browse_btn.setToolTip("Upload / browse program, file, or script...")
        self.browse_btn.setStyleSheet("""
            QPushButton {
                background: #121212;
                border: 1px solid #242738;
                border-radius: 10px;
                color: #9ca3af;
            }
            QPushButton:hover {
                background: rgba(234, 153, 156, 0.2);
                border: 1px solid #ea999c;
                color: #ffffff;
            }
        """)
        self.browse_btn.clicked.connect(self._browse_path)
        row1.addWidget(self.browse_btn)

        lay.addLayout(row1)

        # Arguments Row with Curated Dropdown
        self.args_row = QHBoxLayout()
        self.args_row.setSpacing(8)

        self.args_inp = PillLineEdit("Arguments e.g. @sel.path.quote")
        self.args_inp.textChanged.connect(self.changed.emit)
        self.args_row.addWidget(self.args_inp, 1)

        self.args_combo = ModernComboBox(context_key="arg_preset")
        self.args_combo.setFixedWidth(180)
        self.args_combo.popup_min_width = 320
        self._populate_args_combo("")
        self.args_combo.activated.connect(self._on_arg_preset_selected)
        self.args_row.addWidget(self.args_combo)

        lay.addLayout(self.args_row)

        if initial_data:
            self.set_data(initial_data)

    def set_step_index(self, idx):
        self.step_index = idx
        self.step_lbl.setText(f"Action Step #{idx}")

    def _on_type_changed(self):
        code = self.type_combo.currentData() or "launch"
        if code == "clipboard":
            self.path_inp.setText("command.copy")
            self.path_inp.setEnabled(False)
            self.browse_btn.setEnabled(False)
            self.args_inp.setPlaceholderText('Clipboard content e.g. sel(true, "\\n") or @sel.path')
        elif code == "file":
            self.path_inp.setEnabled(True)
            self.browse_btn.setEnabled(True)
            self.path_inp.setPlaceholderText("Select file or folder to open...")
        else:
            self.path_inp.setEnabled(True)
            self.browse_btn.setEnabled(True)
            self.path_inp.setPlaceholderText("Target executable (.exe), script, or command...")
        self.changed.emit()

    def _browse_path(self):
        code = self.type_combo.currentData() or "launch"
        if code == "file":
            p, _ = QFileDialog.getOpenFileName(self, "Select File to Open", "", "All Files (*.*)")
        else:
            p, _ = QFileDialog.getOpenFileName(self, "Select Executable / Script", "", "All Files (*.*);;Executables (*.exe *.bat *.cmd *.ps1 *.py)")
        if p:
            self.path_inp.setText(os.path.normpath(p))

    def _populate_args_combo(self, cmd_text):
        if getattr(self, 'args_combo', None) is None:
            return
        self.args_combo.blockSignals(True)
        self.args_combo.clear()
        self.args_combo.addItem("+ Insert Argument...")
        curated = get_curated_args_for_command(cmd_text)
        for label, val in curated:
            self.args_combo.addItem(label, val)
        self.args_combo.setCurrentIndex(0)
        self.args_combo.blockSignals(False)

    def _on_arg_preset_selected(self, index):
        if index <= 0 or getattr(self, 'args_inp', None) is None:
            return
        val = self.args_combo.itemData(index) or ""
        if val:
            cur = self.args_inp.text().strip()
            if cur:
                self.args_inp.setText(f"{cur} {val}")
            else:
                self.args_inp.setText(val)
        self.args_combo.setCurrentIndex(0)
        self.changed.emit()

    def get_data(self):
        return {
            'type': self.type_combo.currentData() or "launch",
            'path': self.path_inp.text().strip(),
            'args': self.args_inp.text().strip()
        }

    def set_data(self, data):
        t = data.get('type', 'launch')
        idx = self.type_combo.findData(t)
        if idx != -1:
            self.type_combo.setCurrentIndex(idx)
        self.path_inp.setText(data.get('path', ''))
        self.args_inp.setText(data.get('args', ''))


class ItemConfigDialog(QDialog):
    """
    Popup dialog matching ImportEditorDialog / ModifyRuleEditorDialog pattern.
    Configures new or existing items, submenus, and separators.
    Includes smart args dropdown, menu nesting, multi-action pipeline, and live NSS code editor.
    """
    item_deleted = pyqtSignal()

    def __init__(self, item_data=None, kind="item", parent=None, is_new=True, available_menus=None, parent_menu_title=None):
        super().__init__(parent)
        self.is_new = is_new
        self.kind = kind if is_new else (item_data.get('type') or 'item')
        self.props = item_data.get('props', {}).copy() if item_data else {}
        self.raw_data = item_data or {}
        self.available_menus = available_menus or []
        self.parent_menu_title = parent_menu_title or (item_data.get('parent') if item_data else None)

        self.setMinimumWidth(760)
        self.setMinimumHeight(680)
        self.resize(780, 800)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet("QToolTip { background-color: #1e1e24; color: #ffffff; border: 1px solid rgba(231, 130, 132, 0.6); border-radius: 8px; padding: 6px 12px; font-family: 'Segoe UI Variable Display'; font-size: 12px; font-weight: bold; }")
        self._drag_pos = None
        self._is_updating_code = False
        self.pipeline_steps = []

        self._setup_ui()
        self._sync_live_code()

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

    def _setup_ui(self):
        self.mf = QFrame(self)
        self.mf.setObjectName("mainFrame")
        self.mf.setStyleSheet("""
            #mainFrame {
                background-color: #0E0E0E;
                border: 1.5px solid #1e2130;
                border-radius: 20px;
            }
            QLabel {
                color: #ffffff;
                font-size: 12px;
                background: transparent;
                border: none;
            }
        """)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(self.mf)

        # Scrollable container for dialog content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("background: transparent; border: none;")
        scroll_content = QWidget()
        scroll_content.setMinimumWidth(730)
        scroll_content.setStyleSheet("background: transparent;")
        cl = QVBoxLayout(scroll_content)
        cl.setContentsMargins(24, 20, 24, 20)
        cl.setSpacing(14)
        scroll.setWidget(scroll_content)

        dialog_vbox = QVBoxLayout(self.mf)
        dialog_vbox.setContentsMargins(0, 0, 0, 0)
        dialog_vbox.setSpacing(0)
        dialog_vbox.addWidget(scroll, 1)

        # 1. Header Row
        h_row = QHBoxLayout()
        ic_badge = QLabel()
        ic_badge.setFixedSize(36, 36)
        ic_badge.setFont(QFont("Segoe MDL2 Assets", 14))
        ic_badge.setAlignment(Qt.AlignCenter)
        badge_glyph = "\uE710" if self.kind == "item" else ("\uE15C" if self.kind == "menu" else "\uE108")
        ic_badge.setText(badge_glyph)
        ic_badge.setStyleSheet("background: rgba(234, 153, 156, 0.15); border: 1px solid #ea999c; border-radius: 10px; color: #ea999c;")
        h_row.addWidget(ic_badge)

        h_titles = QVBoxLayout()
        h_titles.setSpacing(2)
        action_verb = "Add New" if self.is_new else "Edit"
        type_str = "Shortcut Item" if self.kind == "item" else ("Submenu" if self.kind == "menu" else "Separator")
        t1 = QLabel(f"{action_verb} {type_str}")
        t1.setStyleSheet("font-size: 16px; font-weight: bold; color: #ffffff;")
        t2 = QLabel("Configure shortcut target, icon, appearance, and position.")
        t2.setStyleSheet("font-size: 11px; color: #8d94a6;")
        h_titles.addWidget(t1)
        h_titles.addWidget(t2)
        h_row.addLayout(h_titles, 1)

        # Clear vector Unicode Close Button
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(32, 32)
        close_btn.setFont(QFont("Segoe UI Variable Display", 11, QFont.Bold))
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setToolTip("Close")
        close_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.10);
                border-radius: 10px;
                color: #838ba7;
            }
            QPushButton:hover {
                background: rgba(231, 130, 132, 0.25);
                border: 1px solid #e78284;
                color: #ffffff;
            }
        """)
        close_btn.clicked.connect(self.reject)
        h_row.addWidget(close_btn)
        cl.addLayout(h_row)

        if self.raw_data.get('is_draft'):
            draft_banner = QFrame()
            draft_banner.setStyleSheet("background: rgba(239, 159, 118, 0.12); border: 1px solid #ef9f76; border-radius: 10px; padding: 6px 10px;")
            dbl = QHBoxLayout(draft_banner)
            dbl.setContentsMargins(6, 4, 6, 4)
            dbl_txt = QLabel(f"⚠️ Draft Item — This item is currently commented out to prevent context menu syntax errors.")
            if self.raw_data.get('error_msg'):
                dbl_txt.setText(f"⚠️ Draft Item ({self.raw_data.get('error_msg')}) — Commented out to prevent syntax errors.")
            dbl_txt.setStyleSheet("color: #ef9f76; font-size: 11px; font-weight: bold;")
            dbl.addWidget(dbl_txt, 1)
            cl.addWidget(draft_banner)

        if self.kind == "separator":
            sep_group = QFrame()
            sep_group.setObjectName("importGroup")
            sep_group.setStyleSheet("#importGroup { background: transparent; } #importGroup QLabel { font-size: 13px; font-weight: bold; color: #ffffff; }")
            sl = QGridLayout(sep_group)
            sl.setVerticalSpacing(12)
            sl.setHorizontalSpacing(14)
            sl.setContentsMargins(0, 0, 0, 0)
            cl.addWidget(sep_group)

            sl.addWidget(QLabel("Type:"), 0, 0, Qt.AlignLeft | Qt.AlignVCenter)
            sep_desc = QLabel("Horizontal separator line between items in the right-click menu.")
            sep_desc.setStyleSheet("color: #838ba7; font-size: 12px;")
            sl.addWidget(sep_desc, 0, 1)

            # Parent Menu
            m_opts = ["None"] + [m for m in self.available_menus if m and m.lower() != "none"]
            self.m_box = ModernComboBox(context_key="menu")
            self.m_box.addItems(list(dict.fromkeys(m_opts)))
            self.m_box.setFixedWidth(200)
            if self.parent_menu_title:
                clean_m = self.parent_menu_title.replace("📁 ", "").strip()
                if clean_m in [self.m_box.itemText(i) for i in range(self.m_box.count())]:
                    self.m_box.setCurrentText(clean_m)
            self.m_box.currentIndexChanged.connect(self._sync_live_code)

            sl.addWidget(QLabel("Parent Menu:"), 1, 0, Qt.AlignLeft | Qt.AlignVCenter)
            sl.addWidget(self.m_box, 1, 1, Qt.AlignLeft)

            self.t_inp = None
            self.ic_inp = None
            self.cmd_inp = None
            self.args_inp = None
            self.dir_inp = None
            self.vis_widget = None
            self.type_widget = None
            self.sep_box = None
            self.p_box = None

        else:
            # Item / Menu Form
            ag = QFrame()
            ag.setObjectName("importGroup")
            ag.setStyleSheet("#importGroup { background: transparent; } #importGroup QLabel { font-size: 13px; font-weight: bold; color: #ffffff; }")
            al = QGridLayout(ag)
            al.setVerticalSpacing(12)
            al.setHorizontalSpacing(14)
            al.setContentsMargins(0, 0, 0, 0)
            cl.addWidget(ag)

            # Row 0: Title
            self.t_inp = PillLineEdit("Enter a title")
            self.t_inp.setText(self.props.get('title', '').strip('\'"'))
            self.t_inp.textChanged.connect(self._sync_live_code)
            al.addWidget(QLabel("Title:"), 0, 0, Qt.AlignLeft | Qt.AlignVCenter)
            al.addWidget(self.t_inp, 0, 1)

            # Row 1: Icon / Image
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

            default_icon = self.props.get('icon') or self.props.get('image') or ('["\\uE15C"]' if self.kind == 'menu' else '')
            self.ic_inp = PillLineEdit("Icon Path or Glyph")
            self.ic_inp.setText(default_icon)
            self.ic_inp.textChanged.connect(self._update_colors_ui)
            self.ic_inp.textChanged.connect(lambda t: self.ic_prev_lbl.set_asset(t))
            self.ic_inp.textChanged.connect(self._sync_live_code)

            btn_action_style = """
                QPushButton {
                    background: #121212;
                    border: 1px solid #242738;
                    border-radius: 10px;
                    color: #9ca3af;
                }
                QPushButton:hover {
                    background: rgba(234, 153, 156, 0.2);
                    border: 1px solid #ea999c;
                    color: #ffffff;
                }
            """
            self.ic_browse = QPushButton("\uE898")
            self.ic_browse.setFont(QFont('Segoe MDL2 Assets', 12))
            self.ic_browse.setFixedSize(34, 34)
            self.ic_browse.setCursor(Qt.PointingHandCursor)
            self.ic_browse.setToolTip("Upload / browse local image file (.png, .ico, .svg)")
            self.ic_browse.setStyleSheet(btn_action_style)
            self.ic_browse.clicked.connect(self._browse_icon)

            self.ic_remove = QPushButton("\uE74D")
            self.ic_remove.setFont(QFont('Segoe MDL2 Assets', 12))
            self.ic_remove.setFixedSize(34, 34)
            self.ic_remove.setCursor(Qt.PointingHandCursor)
            self.ic_remove.setToolTip("Remove Icon")
            self.ic_remove.setStyleSheet("""
                QPushButton { background: #121212; border: 1px solid #242738; border-radius: 10px; color: #9ca3af; }
                QPushButton:hover { background: rgba(255, 50, 50, 0.25); border: 1px solid #ff4444; color: #ffffff; }
            """)
            self.ic_remove.clicked.connect(lambda: self.ic_inp.setText(""))

            ic_row.addWidget(self.ic_prev_lbl)
            ic_row.addWidget(self.c_container)
            ic_row.addWidget(self.ic_inp, 1)
            ic_row.addWidget(self.ic_browse)
            ic_row.addWidget(self.ic_remove)
            al.addWidget(QLabel("Icon / Image:"), 1, 0, Qt.AlignLeft | Qt.AlignVCenter)
            al.addLayout(ic_row, 1, 1)
            self.ic_prev_lbl.set_asset(self.ic_inp.text())
            self._update_colors_ui()

            row_idx = 2
            if self.kind == "item":
                target_box = QVBoxLayout()
                target_box.setSpacing(8)

                # Segmented Toggle: Simple Shortcut vs Advanced Command vs Action Pipeline
                mode_row = QHBoxLayout()
                self.mode_shortcut_btn = QPushButton("Simple Shortcut")
                self.mode_cmd_btn = QPushButton("Advanced Command")
                self.mode_pipeline_btn = QPushButton("⚡ Action Pipeline")
                
                for btn in (self.mode_shortcut_btn, self.mode_cmd_btn, self.mode_pipeline_btn):
                    btn.setCheckable(True)
                    btn.setFixedHeight(28)
                    btn.setCursor(Qt.PointingHandCursor)
                    btn.setFont(QFont("Segoe UI Variable Display", 8, QFont.Bold))
                    btn.setStyleSheet("""
                        QPushButton {
                            background: rgba(255, 255, 255, 0.05);
                            color: #838ba7;
                            border: 1px solid rgba(255, 255, 255, 0.08);
                            border-radius: 13px;
                            padding: 0 14px;
                        }
                        QPushButton:hover:!checked { color: #ffffff; background: rgba(255, 255, 255, 0.09); }
                        QPushButton:checked {
                            background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 rgba(231, 130, 132, 0.35), stop:1 rgba(202, 158, 230, 0.25));
                            color: #ffffff;
                            border: 1px solid #e78284;
                        }
                    """)

                self.mode_group = QButtonGroup(self)
                self.mode_group.setExclusive(True)
                self.mode_group.addButton(self.mode_shortcut_btn)
                self.mode_group.addButton(self.mode_cmd_btn)
                self.mode_group.addButton(self.mode_pipeline_btn)
                mode_row.addWidget(self.mode_shortcut_btn)
                mode_row.addWidget(self.mode_cmd_btn)
                mode_row.addWidget(self.mode_pipeline_btn)
                mode_row.addStretch()
                target_box.addLayout(mode_row)

                # 1. Simple Shortcut Stack Page
                self.simple_container = QWidget()
                sc_lay = QVBoxLayout(self.simple_container)
                sc_lay.setContentsMargins(0, 0, 0, 0)
                sc_lay.setSpacing(6)

                browse_row = QHBoxLayout()
                browse_row.setSpacing(8)
                self.shortcut_path_inp = PillLineEdit("Browse executable (.exe), script (.bat, .py, .ps1), or document...")
                self.shortcut_path_inp.setText(self.props.get('cmd', '').strip('\'"'))
                self.shortcut_path_inp.textChanged.connect(self._sync_live_code)
                browse_row.addWidget(self.shortcut_path_inp, 1)

                self.shortcut_browse = QPushButton("\uE898")
                self.shortcut_browse.setFont(QFont("Segoe MDL2 Assets", 12))
                self.shortcut_browse.setFixedSize(34, 34)
                self.shortcut_browse.setCursor(Qt.PointingHandCursor)
                self.shortcut_browse.setToolTip("Upload / browse executable, file, or script...")
                self.shortcut_browse.setStyleSheet(btn_action_style)
                self.shortcut_browse.clicked.connect(self._browse_program)
                browse_row.addWidget(self.shortcut_browse)
                sc_lay.addLayout(browse_row)

                # Quick Templates
                t_row = QHBoxLayout()
                t_row.setSpacing(6)
                t_lbl = QLabel("Quick Presets:")
                t_lbl.setStyleSheet("color: #70707c; font-size: 11px;")
                t_row.addWidget(t_lbl)
                for t_name, t_code in [
                    ("Terminal Here", "terminal"),
                    ("PowerShell Here", "powershell"),
                    ("Copy Path", "copy_path"),
                    ("Run Python", "run_py"),
                    ("Restart Explorer", "restart_explorer")
                ]:
                    chip = PresetChip(t_name, t_code)
                    chip.clicked.connect(lambda _, c=t_code: self._apply_template(c))
                    t_row.addWidget(chip)
                t_row.addStretch()
                sc_lay.addLayout(t_row)
                target_box.addWidget(self.simple_container)

                # 2. Advanced Command Stack Page
                self.adv_container = QWidget()
                adv_lay = QVBoxLayout(self.adv_container)
                adv_lay.setContentsMargins(0, 0, 0, 0)
                adv_lay.setSpacing(6)

                cmd_grid = QGridLayout()
                cmd_grid.setVerticalSpacing(8)
                cmd_grid.setHorizontalSpacing(10)

                self.cmd_inp = PillLineEdit("Command e.g. cmd.exe, powershell.exe")
                self.cmd_inp.setText(self.props.get('cmd', '').strip('\'"'))
                self.cmd_inp.textChanged.connect(self._on_cmd_changed)
                self.cmd_inp.textChanged.connect(self._sync_live_code)
                cmd_grid.addWidget(QLabel("Command:"), 0, 0)
                cmd_grid.addWidget(self.cmd_inp, 0, 1)

                # Arguments Row with Smart Dropdown Next to Input
                args_h_row = QHBoxLayout()
                args_h_row.setSpacing(8)

                self.args_inp = PillLineEdit('Arguments e.g. @sel.path.quote, /k pushd "@sel.path"')
                self.args_inp.setText(self.props.get('args', self.props.get('arg', '')).strip('\'"'))
                self.args_inp.textChanged.connect(self._sync_live_code)
                args_h_row.addWidget(self.args_inp, 1)

                self.args_combo = ModernComboBox(context_key="arg_preset")
                self.args_combo.setFixedWidth(180)
                self.args_combo.popup_min_width = 320
                self._populate_args_combo(self.cmd_inp.text())
                self.args_combo.activated.connect(self._on_arg_preset_selected)
                args_h_row.addWidget(self.args_combo)

                cmd_grid.addWidget(QLabel("Arguments:"), 1, 0)
                cmd_grid.addLayout(args_h_row, 1, 1)

                # Working dir
                self.dir_inp = PillLineEdit('Working Dir e.g. @sel.dir')
                self.dir_inp.setText(self.props.get('dir', '').strip('\'"'))
                self.dir_inp.textChanged.connect(self._sync_live_code)
                cmd_grid.addWidget(QLabel("Working Dir:"), 2, 0)
                cmd_grid.addWidget(self.dir_inp, 2, 1)

                adv_lay.addLayout(cmd_grid)
                target_box.addWidget(self.adv_container)

                # 3. Action Pipeline Stack Page (Series of Actions)
                self.pipeline_container = QWidget()
                pipe_lay = QVBoxLayout(self.pipeline_container)
                pipe_lay.setContentsMargins(0, 0, 0, 0)
                pipe_lay.setSpacing(8)

                self.pipeline_steps_layout = QVBoxLayout()
                self.pipeline_steps_layout.setSpacing(6)
                pipe_lay.addLayout(self.pipeline_steps_layout)

                pipe_btn_row = QHBoxLayout()
                add_step_btn = PillPushButton("+ Add Action Step", "secondary", height=30)
                add_step_btn.clicked.connect(self._add_pipeline_step)
                pipe_btn_row.addWidget(add_step_btn)
                pipe_btn_row.addStretch()
                pipe_lay.addLayout(pipe_btn_row)

                target_box.addWidget(self.pipeline_container)

                self.mode_shortcut_btn.clicked.connect(lambda: self._set_target_mode(0))
                self.mode_cmd_btn.clicked.connect(lambda: self._set_target_mode(1))
                self.mode_pipeline_btn.clicked.connect(lambda: self._set_target_mode(2))

                # Determine initial mode
                has_complex_args = bool(self.args_inp.text().strip() or self.props.get('args') or self.props.get('arg'))
                self._set_target_mode(1 if has_complex_args else 0)

                al.addWidget(QLabel("Target:"), row_idx, 0, Qt.AlignLeft | Qt.AlignTop)
                al.addLayout(target_box, row_idx, 1)
                row_idx += 1
            else:
                self.shortcut_path_inp = None
                self.cmd_inp = None
                self.args_inp = None
                self.dir_inp = None
                self.args_combo = None

            # Visibility
            self.vis_widget = VisibilityWidget()
            self.vis_widget.set_value(str(self.props.get('vis', '')))
            al.addWidget(QLabel("Visibility:"), row_idx, 0, Qt.AlignLeft | Qt.AlignVCenter)
            al.addWidget(self.vis_widget, row_idx, 1)
            row_idx += 1

            # Show in (Type)
            self.type_widget = TypeWidget()
            self.type_widget.set_value(self.props.get('type', ''))
            al.addWidget(QLabel("Show in:"), row_idx, 0, Qt.AlignLeft | Qt.AlignVCenter)
            al.addWidget(self.type_widget, row_idx, 1)
            row_idx += 1

            # Parent Menu & Position
            pos_move_row = QHBoxLayout()
            pos_move_row.setContentsMargins(0, 0, 0, 0)
            pos_move_row.setSpacing(14)

            # Available menus options
            menu_choices = ["None"] + [m for m in self.available_menus if m and m.lower() != "none"]
            self.m_box = ModernComboBox(context_key="menu")
            self.m_box.addItems(list(dict.fromkeys(menu_choices)))
            self.m_box.setFixedWidth(200)

            # Set pre-selected parent menu
            if self.parent_menu_title:
                clean_m = self.parent_menu_title.replace("📁 ", "").strip()
                if clean_m in [self.m_box.itemText(i) for i in range(self.m_box.count())]:
                    self.m_box.setCurrentText(clean_m)
            elif self.props.get('menu'):
                raw_m = str(self.props.get('menu')).strip('\'"')
                if raw_m:
                    clean_m = raw_m.replace("📁 ", "").strip()
                    if clean_m in [self.m_box.itemText(i) for i in range(self.m_box.count())]:
                        self.m_box.setCurrentText(clean_m)
                    else:
                        self.m_box.addItem(clean_m)
                        self.m_box.setCurrentText(clean_m)

            self.m_box.currentIndexChanged.connect(self._sync_live_code)
            pos_move_row.addWidget(self.m_box)

            pos_lbl = QLabel("Position:")
            pos_move_row.addWidget(pos_lbl)
            self.p_box = ModernComboBox(context_key="pos")
            self.p_box.addItems(["(Default)", "Top", "Bottom", "Middle", "1", "2", "3", "4", "5"])
            self.p_box.setFixedWidth(140)
            p_val = str(self.props.get('pos', '')).strip('\'"')
            if p_val:
                p_cap = p_val.title()
                items = [self.p_box.itemText(i) for i in range(self.p_box.count())]
                if p_cap in items:
                    self.p_box.setCurrentText(p_cap)
                elif p_val in items:
                    self.p_box.setCurrentText(p_val)
                else:
                    self.p_box.addItem(p_val)
                    self.p_box.setCurrentText(p_val)
            else:
                self.p_box.setCurrentText("(Default)")
            self.p_box.currentIndexChanged.connect(self._sync_live_code)
            pos_move_row.addWidget(self.p_box)
            pos_move_row.addStretch()

            al.addWidget(QLabel("Parent Menu:"), row_idx, 0, Qt.AlignLeft | Qt.AlignVCenter)
            al.addLayout(pos_move_row, row_idx, 1, Qt.AlignLeft | Qt.AlignVCenter)
            row_idx += 1

            # Separator
            self.sep_box = ModernComboBox(context_key="sep")
            self.sep_box.addItems(["None", "Before", "After", "Both"])
            self.sep_box.setFixedWidth(160)
            curr_sep = str(self.props.get('sep', '')).strip('\'"')
            if curr_sep:
                if curr_sep.lower() in ('true', '1'):
                    self.sep_box.setCurrentText("Before")
                else:
                    self.sep_box.setCurrentText(curr_sep.title())
            else:
                self.sep_box.setCurrentText("None")
            self.sep_box.currentIndexChanged.connect(self._sync_live_code)

            al.addWidget(QLabel("Separator:"), row_idx, 0, Qt.AlignLeft | Qt.AlignVCenter)
            al.addWidget(self.sep_box, row_idx, 1, Qt.AlignLeft | Qt.AlignVCenter)

        # 3. Live NSS Code Box (Collapsible & Directly Editable)
        code_frame = QFrame()
        code_frame.setObjectName("codeFrame")
        code_frame.setStyleSheet("""
            #codeFrame {
                background: transparent;
                border: none;
            }
        """)
        code_vl = QVBoxLayout(code_frame)
        code_vl.setContentsMargins(0, 4, 0, 0)
        code_vl.setSpacing(6)

        toggle_row = QHBoxLayout()
        toggle_row.setContentsMargins(0, 0, 0, 0)

        self.code_toggle_btn = QPushButton("▶  Manual Edit")
        self.code_toggle_btn.setCursor(Qt.PointingHandCursor)
        self.code_toggle_btn.setFont(QFont("Segoe UI Variable Display", 9, QFont.Bold))
        self.code_toggle_btn.setStyleSheet("""
            QPushButton {
                text-align: left;
                background: rgba(255, 255, 255, 0.04);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 6px;
                color: #838ba7;
                padding: 4px 10px;
            }
            QPushButton:hover {
                color: #ffffff;
                background: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.15);
            }
        """)
        toggle_row.addWidget(self.code_toggle_btn)
        toggle_row.addStretch()
        code_vl.addLayout(toggle_row)

        self.code_container = QWidget()
        self.code_container.setStyleSheet("background: transparent; border: none;")
        cc_lay = QVBoxLayout(self.code_container)
        cc_lay.setContentsMargins(0, 2, 0, 0)
        cc_lay.setSpacing(4)

        self.code_edit = QPlainTextEdit()
        self.code_edit.setFixedHeight(68)
        self.code_edit.setFont(QFont("Consolas", 9))
        self.code_edit.setReadOnly(False)
        self.code_edit.setStyleSheet("""
            QPlainTextEdit {
                background: #09090b;
                color: #a6d189;
                border: 1px solid #242738;
                border-radius: 8px;
                padding: 6px 8px;
            }
            QPlainTextEdit:focus {
                border: 1px solid #e78284;
            }
        """)
        cc_lay.addWidget(self.code_edit)
        code_vl.addWidget(self.code_container)

        self.code_container.setVisible(False)
        self.code_toggle_btn.clicked.connect(self._toggle_code_preview)
        cl.addWidget(code_frame)
        cl.addStretch()

        # 4. Floating Docked Bottom Action Bar
        bottom_frame = QFrame()
        bottom_frame.setObjectName("bottomActionBar")
        bottom_frame.setStyleSheet("""
            #bottomActionBar {
                background: transparent;
                border: none;
            }
        """)
        btns = QHBoxLayout(bottom_frame)
        btns.setContentsMargins(24, 4, 24, 18)

        if not self.is_new:
            del_btn = PillPushButton("Delete Item", "danger", height=34)
            del_btn.clicked.connect(self._on_delete_clicked)
            btns.addWidget(del_btn)

        btns.addStretch()

        c = PillPushButton("Cancel", "secondary", height=34)
        c.setFixedWidth(85)
        c.clicked.connect(self.reject)
        btns.addWidget(c)

        s = PillPushButton("Save Changes", "primary", height=34)
        s.setFixedWidth(120)
        s.clicked.connect(self.accept)
        btns.addWidget(s)

        dialog_vbox.addWidget(bottom_frame)

    def _set_target_mode(self, mode_idx):
        """0 = Simple, 1 = Advanced, 2 = Pipeline."""
        self.mode_shortcut_btn.setChecked(mode_idx == 0)
        self.mode_cmd_btn.setChecked(mode_idx == 1)
        self.mode_pipeline_btn.setChecked(mode_idx == 2)

        self.simple_container.setVisible(mode_idx == 0)
        self.adv_container.setVisible(mode_idx == 1)
        self.pipeline_container.setVisible(mode_idx == 2)

        if mode_idx == 2 and not self.pipeline_steps:
            self._add_pipeline_step()
        self._sync_live_code()

    def _add_pipeline_step(self, data=None):
        idx = len(self.pipeline_steps) + 1
        step_w = PipelineStepWidget(step_index=idx, initial_data=data)
        step_w.changed.connect(self._sync_live_code)
        step_w.delete_requested.connect(lambda w=step_w: self._remove_pipeline_step(w))
        step_w.move_up_requested.connect(lambda w=step_w: self._move_pipeline_step_up(w))
        step_w.move_down_requested.connect(lambda w=step_w: self._move_pipeline_step_down(w))

        self.pipeline_steps.append(step_w)
        self.pipeline_steps_layout.addWidget(step_w)
        self._update_step_indices()
        self._sync_live_code()

    def _remove_pipeline_step(self, step_w):
        if step_w in self.pipeline_steps:
            self.pipeline_steps.remove(step_w)
            self.pipeline_steps_layout.removeWidget(step_w)
            step_w.deleteLater()
            self._update_step_indices()
            self._sync_live_code()

    def _move_pipeline_step_up(self, step_w):
        if step_w in self.pipeline_steps:
            idx = self.pipeline_steps.index(step_w)
            if idx > 0:
                self.pipeline_steps[idx], self.pipeline_steps[idx - 1] = self.pipeline_steps[idx - 1], self.pipeline_steps[idx]
                self.pipeline_steps_layout.removeWidget(step_w)
                self.pipeline_steps_layout.insertWidget(idx - 1, step_w)
                self._update_step_indices()
                self._sync_live_code()

    def _move_pipeline_step_down(self, step_w):
        if step_w in self.pipeline_steps:
            idx = self.pipeline_steps.index(step_w)
            if idx < len(self.pipeline_steps) - 1:
                self.pipeline_steps[idx], self.pipeline_steps[idx + 1] = self.pipeline_steps[idx + 1], self.pipeline_steps[idx]
                self.pipeline_steps_layout.removeWidget(step_w)
                self.pipeline_steps_layout.insertWidget(idx + 1, step_w)
                self._update_step_indices()
                self._sync_live_code()

    def _update_step_indices(self):
        for i, sw in enumerate(self.pipeline_steps):
            sw.set_step_index(i + 1)

    def _compile_pipeline_command(self):
        """Compiles pipeline steps into safe, chained cmd and args."""
        if not self.pipeline_steps:
            return "", ""

        raw_steps = [sw.get_data() for sw in self.pipeline_steps]
        if len(raw_steps) == 1:
            st = raw_steps[0]
            st_type = st.get('type')
            path = st.get('path', '')
            args = st.get('args', '')
            if st_type == 'clipboard':
                clip_val = args or 'sel(true, "\\n")'
                return f"command.copy({clip_val})", ""
            return path, args

        chain_commands = []
        for st in raw_steps:
            st_type = st.get('type')
            path = st.get('path', '')
            args = st.get('args', '')

            if st_type == 'clipboard':
                clip_val = args or '@sel.path'
                chain_commands.append(f"echo {clip_val}| clip")
            elif st_type == 'cmd':
                if args:
                    chain_commands.append(f"{path} {args}".strip())
                else:
                    chain_commands.append(f"{path}".strip())
            elif st_type == 'powershell':
                chain_commands.append(f"powershell.exe -NoProfile -Command \"{path} {args}\"".strip())
            elif st_type == 'python':
                chain_commands.append(f"python \"{path}\" {args}".strip())
            elif st_type == 'file':
                chain_commands.append(f"start \"\" \"{path}\"")
            else:
                if args:
                    chain_commands.append(f"start \"\" \"{path}\" {args}")
                else:
                    chain_commands.append(f"start \"\" \"{path}\"")

        joined = " && ".join(chain_commands)
        return "cmd.exe", f"/c {joined}"

    def _toggle_code_preview(self):
        is_vis = self.code_container.isVisible()
        new_vis = not is_vis
        self.code_container.setVisible(new_vis)
        if new_vis:
            self.code_toggle_btn.setText("▼  Manual Edit")
            self._sync_live_code()
            self.code_edit.setFocus()
        else:
            self.code_toggle_btn.setText("▶  Manual Edit")

    def _populate_args_combo(self, cmd_text):
        if getattr(self, 'args_combo', None) is None:
            return
        self.args_combo.blockSignals(True)
        self.args_combo.clear()
        self.args_combo.addItem("+ Insert Argument...")

        curated = get_curated_args_for_command(cmd_text)
        for label, val in curated:
            self.args_combo.addItem(label, val)
        self.args_combo.setCurrentIndex(0)
        self.args_combo.blockSignals(False)

    def _on_cmd_changed(self, text):
        if hasattr(self, 'mode_cmd_btn') and not self.mode_cmd_btn.isChecked() and not self.mode_pipeline_btn.isChecked():
            self._set_target_mode(1)
        self._populate_args_combo(text)

    def _on_arg_preset_selected(self, index):
        if index <= 0 or getattr(self, 'args_inp', None) is None:
            return
        if hasattr(self, 'mode_cmd_btn') and not self.mode_cmd_btn.isChecked() and not self.mode_pipeline_btn.isChecked():
            self._set_target_mode(1)
        val = self.args_combo.itemData(index) or ""
        if val:
            cur = self.args_inp.text().strip()
            if cur:
                self.args_inp.setText(f"{cur} {val}")
            else:
                self.args_inp.setText(val)
        self.args_combo.setCurrentIndex(0)
        self._sync_live_code()

    def _browse_program(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Program or File", "", "All Files (*.*);;Executables (*.exe *.bat *.cmd *.ps1)")
        if path:
            norm = os.path.normpath(path)
            self.shortcut_path_inp.setText(norm)
            if self.cmd_inp:
                self.cmd_inp.setText(f'"{norm}"')
            if not self.t_inp.text().strip():
                base = os.path.splitext(os.path.basename(path))[0]
                self.t_inp.setText(base.replace('-', ' ').replace('_', ' ').title())

    def _apply_template(self, tid):
        if tid == "terminal":
            self.t_inp.setText("Terminal Here")
            self.ic_inp.setText('["\\uE0D6"]')
            self.shortcut_path_inp.setText("cmd.exe")
            if self.cmd_inp:
                self.cmd_inp.setText("cmd.exe")
                self.args_inp.setText('/k pushd "@sel.path"')
            if self.type_widget:
                self.type_widget.set_value("back")
        elif tid == "powershell":
            self.t_inp.setText("PowerShell Here")
            self.ic_inp.setText('["\\uE218"]')
            self.shortcut_path_inp.setText("powershell.exe")
            if self.cmd_inp:
                self.cmd_inp.setText("powershell.exe")
                self.args_inp.setText('-NoExit -Command "Set-Location -LiteralPath \'@sel.path\'"')
        elif tid == "copy_path":
            self.t_inp.setText("Copy Path")
            self.ic_inp.setText('["\\uE0AC"]')
            self.shortcut_path_inp.setText('command.copy(sel(true, "\\n"))')
            if self.cmd_inp:
                self.cmd_inp.setText('command.copy(sel(true, "\\n"))')
                self.args_inp.setText("")
            if self.type_widget:
                self.type_widget.set_value("file|dir")
        elif tid == "run_py":
            self.t_inp.setText("Run Python")
            self.ic_inp.setText('["\\uE230"]')
            self.shortcut_path_inp.setText("cmd.exe")
            if self.cmd_inp:
                self.cmd_inp.setText("cmd.exe")
                self.args_inp.setText('/k python @sel.path.quote')
            if self.type_widget:
                self.type_widget.set_value("file")
        elif tid == "restart_explorer":
            self.t_inp.setText("Restart Explorer")
            self.ic_inp.setText('["\\uE1EA"]')
            self.shortcut_path_inp.setText("command.restart_explorer")
            if self.cmd_inp:
                self.cmd_inp.setText("command.restart_explorer")
                self.args_inp.setText("")
            if self.type_widget:
                self.type_widget.set_value("taskbar")
        self._update_colors_ui()
        self._sync_live_code()

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
            if dlg.exec_():
                self.ic_inp.setText(dlg.result_value)

    def _update_colors_ui(self):
        val = self.ic_inp.text().strip()
        while self.c_lay.count():
            it = self.c_lay.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
        colors = _extract_all_colors(val)
        theme_cs = _get_theme_glyph_colors()
        codes = _extract_glyph_codes(val)
        num = len(codes) if codes else (1 if val else 0)
        for i in range(max(num, len(colors))):
            if i >= 2:
                break
            c = colors[i] if i < len(colors) else None
            btn = ColorCircleButton(c or theme_cs[min(i, 1)])
            btn.clicked.connect(self._open_glyph_browser)
            self.c_lay.addWidget(btn)

    def _on_delete_clicked(self):
        title = self.t_inp.text().strip() if self.t_inp else "this item"
        dlg = StyledConfirmDialog(
            title="Delete Item",
            message=f"Are you sure you want to delete '{title}'?",
            parent=self,
            confirm_text="Delete",
            danger=True
        )
        if dlg.exec_():
            self.item_deleted.emit()
            self.reject()

    def _sync_live_code(self):
        """Generates live NSS code string and reflects it into the code edit."""
        if not hasattr(self, 'code_edit') or self._is_updating_code or self.code_edit.hasFocus():
            return
        self._is_updating_code = True
        try:
            p = self._collect_properties(raw_code_mode=False)
            t = self.kind
            if t == "separator":
                code_str = "separator"
            else:
                pts = []
                for k, v in p.items():
                    if k in ('_order', 'file', 'start', 'end', 'cmd_end', 'raw_inner', 'has_children', 'indent', '_is_temp', 'children', 'parent'):
                        continue
                    if v is not None and str(v).strip() != '':
                        pts.append(format_nss_value(k, str(v).strip()))
                header = f"{t}({' '.join(pts)})"
                if t == "menu":
                    code_str = f"{header}\n{{\n    // Nested items appear here\n}}"
                else:
                    code_str = header
            if hasattr(self, 'code_edit'):
                self.code_edit.setPlainText(code_str)
        finally:
            self._is_updating_code = False

    def _collect_properties(self, raw_code_mode=False):
        if self.kind == "separator":
            return {}

        p = self.props.copy()
        t = self.t_inp.text().strip() if self.t_inp else ''
        if t:
            p['title'] = f"'{t}'" if ' ' in t and not t.startswith("'") else t
        else:
            p.pop('title', None)

        ic = self.ic_inp.text().strip() if self.ic_inp else ''
        if ic:
            p['image'] = ic
            p.pop('icon', None)
        else:
            p.pop('image', None)
            p.pop('icon', None)

        if self.kind == "item":
            if hasattr(self, 'mode_pipeline_btn') and self.mode_pipeline_btn.isChecked():
                comp_cmd, comp_args = self._compile_pipeline_command()
                if comp_cmd:
                    p['cmd'] = comp_cmd
                else:
                    p.pop('cmd', None)
                if comp_args:
                    p['args'] = comp_args
                else:
                    p.pop('args', None)
                p.pop('dir', None)
            elif hasattr(self, 'mode_cmd_btn') and self.mode_cmd_btn.isChecked():
                c = self.cmd_inp.text().strip() if self.cmd_inp else ''
                a = self.args_inp.text().strip() if self.args_inp else ''
                d = self.dir_inp.text().strip() if self.dir_inp else ''
                if c:
                    p['cmd'] = c
                else:
                    p.pop('cmd', None)
                if a:
                    p['args'] = a
                else:
                    p.pop('args', None)
                if d:
                    p['dir'] = d
                else:
                    p.pop('dir', None)
            else:
                sp = self.shortcut_path_inp.text().strip() if self.shortcut_path_inp else ''
                if sp:
                    p['cmd'] = f'"{sp}"' if ('\\' in sp or '/' in sp) and not sp.startswith('"') else sp
                else:
                    p.pop('cmd', None)
                p.pop('args', None)
                p.pop('dir', None)

        if hasattr(self, 'vis_widget') and self.vis_widget:
            v = self.vis_widget.get_value()
            if v:
                p['vis'] = v
            else:
                p.pop('vis', None)

        if hasattr(self, 'type_widget') and self.type_widget:
            tp = self.type_widget.get_value()
            if tp:
                p['type'] = tp
            else:
                p.pop('type', None)

        if getattr(self, 'p_box', None) is not None:
            pos = self.p_box.currentText().strip()
            if pos and pos.lower() not in ("", "default", "(default)"):
                p['pos'] = pos.lower()
            else:
                p.pop('pos', None)

        if getattr(self, 'sep_box', None) is not None:
            sep = self.sep_box.currentText().strip()
            if sep and sep.lower() not in ("", "none", "(none)"):
                p['sep'] = sep.lower()
            else:
                p.pop('sep', None)

        return p

    def get_parent_menu(self):
        """Returns the chosen parent menu title or None for top level."""
        if getattr(self, 'm_box', None) is None:
            return self.parent_menu_title
        txt = self.m_box.currentText().strip()
        if txt.startswith("📁 "):
            txt = txt[2:].strip()
        if not txt or txt.lower() in ("none", "none (top-level)"):
            return None
        return txt

    def get_props(self):
        if hasattr(self, 'code_container') and self.code_container.isVisible() and hasattr(self, 'code_edit'):
            code_text = self.code_edit.toPlainText().strip()
            lexer = NSSLexer(code_text)
            tokens = lexer.tokenize()
            if tokens and tokens[0][1].lower() in ('item', 'menu', 'separator'):
                if tokens[0][1].lower() == 'separator':
                    return {}
                if len(tokens) > 2 and tokens[1][1] == '(':
                    arg_tokens = []
                    pc = 1
                    for tk in tokens[2:]:
                        if tk[1] == '(':
                            pc += 1
                        elif tk[1] == ')':
                            pc -= 1
                            if pc == 0:
                                break
                        arg_tokens.append(tk)
                    parsed = parse_nss_args(code_text, arg_tokens)
                    return parsed
        return self._collect_properties()


class BuilderItemCard(QFrame):
    """
    Card matching ImportedItemCard / ModificationRuleCard style.
    Renders an item, submenu, or separator with clear actions.
    Supports expandable nested children for menus and drafts.
    """
    edit_requested = pyqtSignal(dict)
    delete_requested = pyqtSignal(dict)
    move_up_requested = pyqtSignal(dict)
    move_down_requested = pyqtSignal(dict)
    add_inside_requested = pyqtSignal(dict)
    add_menu_inside_requested = pyqtSignal(dict)
    un_nest_requested = pyqtSignal(dict)
    toggle_draft_requested = pyqtSignal(dict)
    collapse_toggle_requested = pyqtSignal(dict)

    def __init__(self, item_data, parent=None, is_nested=False, parent_title=None, is_collapsed=False):
        super().__init__(parent)
        self.item_data = item_data
        self.is_nested = is_nested
        self.parent_title = parent_title
        self.is_collapsed = is_collapsed
        self.setObjectName("builderCard")
        self.setMinimumHeight(74)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.setCursor(Qt.PointingHandCursor)

        is_draft = item_data.get('is_draft', False)
        if is_draft:
            border_color = "rgba(239, 159, 118, 0.4)"
            hover_color = "rgba(239, 159, 118, 0.7)"
            bg_color = "#161314"
        elif is_nested:
            border_color = "rgba(202, 158, 230, 0.25)"
            hover_color = "rgba(202, 158, 230, 0.45)"
            bg_color = "#141418"
        else:
            border_color = "rgba(255, 255, 255, 0.05)"
            hover_color = "rgba(231, 130, 132, 0.45)"
            bg_color = "#121212"

        self.setStyleSheet(f"""
            #builderCard {{
                background-color: {bg_color};
                border-radius: 14px;
                border: 1px solid {border_color};
            }}
            #builderCard:hover {{
                background-color: #18181c;
                border: 1px solid {hover_color};
            }}
        """)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 10, 14, 10)
        lay.setSpacing(12)
        lay.setAlignment(Qt.AlignVCenter)

        # Icon Badge
        self.icon_badge = QLabel()
        self.icon_badge.setFixedSize(36, 36)
        self.icon_badge.setAlignment(Qt.AlignCenter)
        self.icon_badge.setStyleSheet("background: rgba(255, 255, 255, 0.035); border-radius: 10px; border: 1px solid rgba(255, 255, 255, 0.08);")
        lay.addWidget(self.icon_badge, 0, Qt.AlignVCenter | Qt.AlignLeft)

        # Center Text Details (wraps long labels, minimum width 0 to never push actions)
        center_w = QWidget()
        center_w.setStyleSheet("background: transparent; border: none;")
        center_w.setMinimumWidth(0)
        center_w.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        center_lay = QVBoxLayout(center_w)
        center_lay.setContentsMargins(0, 0, 0, 0)
        center_lay.setSpacing(4)
        center_lay.setAlignment(Qt.AlignVCenter)

        self.title_lbl = QLabel()
        self.title_lbl.setStyleSheet("font-size: 13px; font-weight: bold; color: #ffffff; background: transparent;")
        self.title_lbl.setWordWrap(True)
        center_lay.addWidget(self.title_lbl)

        self.sub_lbl = QLabel()
        self.sub_lbl.setStyleSheet("font-size: 11px; color: #838ba7; background: transparent;")
        self.sub_lbl.setWordWrap(True)
        center_lay.addWidget(self.sub_lbl)

        # Badges row with FlowLayout to wrap flags onto multiple rows
        self.badge_container = QWidget()
        self.badge_container.setStyleSheet("background: transparent; border: none;")
        self.badge_lay = FlowLayout(self.badge_container, margin=0, spacing=6)
        center_lay.addWidget(self.badge_container)

        lay.addWidget(center_w, 1)

        # Right Action Buttons (Fixed 284px width, anchored to right frame, never moves)
        actions_w = QWidget()
        actions_w.setFixedWidth(284)
        actions_w.setStyleSheet("background: transparent; border: none;")
        al = QHBoxLayout(actions_w)
        al.setContentsMargins(0, 0, 0, 0)
        al.setSpacing(6)
        al.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        btn_base_style = """
            QPushButton {
                background: rgba(255, 255, 255, 0.06);
                border: 1px solid rgba(255, 255, 255, 0.10);
                border-radius: 15px;
                color: #c6d0f5;
                font-family: 'Segoe MDL2 Assets';
                font-size: 11px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.14);
                color: #ffffff;
                border: 1px solid #e78284;
            }
        """

        if self.item_data.get('type', '').lower() == 'menu':
            self.collapse_btn = QPushButton("\uE76C" if self.is_collapsed else "\uE70D")
            self.collapse_btn.setFixedSize(30, 30)
            self.collapse_btn.setCursor(Qt.PointingHandCursor)
            self.collapse_btn.setToolTip("Expand Submenu" if self.is_collapsed else "Collapse Submenu")
            self.collapse_btn.setStyleSheet(btn_base_style)
            self.collapse_btn.clicked.connect(lambda: self.collapse_toggle_requested.emit(self.item_data))
            al.addWidget(self.collapse_btn)

            self.add_in_btn = PillPushButton("+ Add Inside ▾", "secondary", height=28)
            self.add_in_btn.setFixedWidth(104)
            self.add_in_btn.setFont(QFont("Segoe UI Variable Text", 8, QFont.Bold))
            self.add_in_btn.clicked.connect(self._show_add_inside_menu)
            al.addWidget(self.add_in_btn)
        else:
            al.addStretch()

        self.up_btn = QPushButton("\uE010")
        self.up_btn.setFixedSize(30, 30)
        self.up_btn.setCursor(Qt.PointingHandCursor)
        self.up_btn.setToolTip("Move Up")
        self.up_btn.setStyleSheet(btn_base_style)
        self.up_btn.clicked.connect(lambda: self.move_up_requested.emit(self.item_data))
        al.addWidget(self.up_btn)

        self.down_btn = QPushButton("\uE011")
        self.down_btn.setFixedSize(30, 30)
        self.down_btn.setCursor(Qt.PointingHandCursor)
        self.down_btn.setToolTip("Move Down")
        self.down_btn.setStyleSheet(btn_base_style)
        self.down_btn.clicked.connect(lambda: self.move_down_requested.emit(self.item_data))
        al.addWidget(self.down_btn)

        self.edit_btn = QPushButton("\uE104")
        self.edit_btn.setFixedSize(30, 30)
        self.edit_btn.setCursor(Qt.PointingHandCursor)
        self.edit_btn.setToolTip("Edit Item")
        self.edit_btn.setStyleSheet(btn_base_style)
        self.edit_btn.clicked.connect(lambda: self.edit_requested.emit(self.item_data))
        al.addWidget(self.edit_btn)

        self.del_btn = QPushButton("\uE74D")
        self.del_btn.setFixedSize(30, 30)
        self.del_btn.setCursor(Qt.PointingHandCursor)
        self.del_btn.setToolTip("Delete Item")
        self.del_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.06);
                border: 1px solid rgba(255, 255, 255, 0.10);
                border-radius: 15px;
                color: #c6d0f5;
                font-family: 'Segoe MDL2 Assets';
                font-size: 11px;
            }
            QPushButton:hover {
                background: rgba(231, 130, 132, 0.25);
                border: 1px solid #e78284;
                color: #e78284;
            }
        """)
        self.del_btn.clicked.connect(lambda: self.delete_requested.emit(self.item_data))
        al.addWidget(self.del_btn)

        lay.addWidget(actions_w, 0, Qt.AlignVCenter | Qt.AlignRight)
        self.update_content()

    def _show_add_inside_menu(self):
        m = QMenu(self)
        m.setStyleSheet("""
            QMenu {
                background-color: #1e1e24;
                color: #ffffff;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 8px;
                padding: 4px;
            }
            QMenu::item { padding: 6px 20px; border-radius: 6px; }
            QMenu::item:selected { background-color: #e78284; color: #232634; }
        """)
        act_item = m.addAction("+ Shortcut Item")
        act_menu = m.addAction("📁 Submenu Folder")
        selected = m.exec_(self.add_in_btn.mapToGlobal(QPoint(0, self.add_in_btn.height() + 2)))
        if selected == act_item:
            self.add_inside_requested.emit(self.item_data)
        elif selected == act_menu:
            self.add_menu_inside_requested.emit(self.item_data)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self.item_data.get('type', '').lower() == 'menu':
                self.collapse_toggle_requested.emit(self.item_data)
            else:
                self.edit_requested.emit(self.item_data)
            event.accept()
        else:
            super().mouseDoubleClickEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            menu = QMenu(self)
            menu.setStyleSheet("""
                QMenu {
                    background-color: #1e1e24;
                    color: #ffffff;
                    border: 1px solid rgba(255, 255, 255, 0.12);
                    border-radius: 8px;
                    padding: 4px;
                }
                QMenu::item { padding: 6px 20px; border-radius: 6px; }
                QMenu::item:selected { background-color: #e78284; color: #232634; }
            """)
            e_act = menu.addAction("Edit Item")
            up_act = menu.addAction("Move Up")
            down_act = menu.addAction("Move Down")

            is_menu = self.item_data.get('type', '').lower() == 'menu'
            if is_menu:
                menu.addSeparator()
                add_item_act = menu.addAction("+ Add Shortcut Item Inside")
                add_menu_act = menu.addAction("📁 Add Submenu Folder Inside")
                menu.addSeparator()
            else:
                add_item_act = None
                add_menu_act = None

            is_draft = self.item_data.get('is_draft', False)
            draft_act = menu.addAction("Activate / Publish" if is_draft else "Save as Draft (Comment out)")

            if self.is_nested:
                unnest_act = menu.addAction("Move Out of Menu (To Top Level)")
            else:
                unnest_act = None

            menu.addSeparator()
            del_act = menu.addAction("Delete Item")

            action = menu.exec_(event.globalPos())
            if action == e_act:
                self.edit_requested.emit(self.item_data)
            elif action == up_act:
                self.move_up_requested.emit(self.item_data)
            elif action == down_act:
                self.move_down_requested.emit(self.item_data)
            elif add_item_act and action == add_item_act:
                self.add_inside_requested.emit(self.item_data)
            elif add_menu_act and action == add_menu_act:
                self.add_menu_inside_requested.emit(self.item_data)
            elif action == draft_act:
                self.toggle_draft_requested.emit(self.item_data)
            elif unnest_act and action == unnest_act:
                self.un_nest_requested.emit(self.item_data)
            elif action == del_act:
                self.delete_requested.emit(self.item_data)
            event.accept()
        else:
            super().mousePressEvent(event)

    def update_content(self):
        t = self.item_data.get('type', 'item').lower()
        props = self.item_data.get('props', {})
        is_draft = self.item_data.get('is_draft', False)

        while self.badge_lay.count():
            it = self.badge_lay.takeAt(0)
            if it.widget():
                it.widget().deleteLater()

        if is_draft:
            err_msg = self.item_data.get('error_msg')
            self._add_badge(f"Draft: {err_msg}" if err_msg else "Draft (Commented)", "#ef9f76")

        if t == "separator":
            self.icon_badge.setPixmap(get_mdl2_icon(0xE108, 18, "#e5c890").pixmap(18, 18))
            self.title_lbl.setText("Separator")
            self.sub_lbl.setText("Horizontal separator line")
            if self.is_nested and self.parent_title:
                self._add_badge(f"↳ In: {self.parent_title}", "#ca9ee6")
            return

        # Title
        raw_title = props.get('title', '')
        clean_title = str(raw_title).strip('\'"') or "(Unnamed)"
        self.title_lbl.setText(clean_title)

        # Icon / Image rendering
        raw_icon = str(props.get('image') or props.get('icon') or '').strip('\'"')
        if raw_icon:
            pm = render_nss_asset_pixmap(raw_icon, 20)
            if pm and not pm.isNull():
                self.icon_badge.setPixmap(pm)
            elif raw_icon.lower().endswith(('.png', '.ico', '.jpg', '.jpeg', '.svg')):
                self.icon_badge.setPixmap(get_mdl2_icon(0xEB9F, 18, "#85c1dc").pixmap(18, 18))
            else:
                glyph = 0xE15C if t == "menu" else 0xE710
                self.icon_badge.setPixmap(get_mdl2_icon(glyph, 18, "#ea999c").pixmap(18, 18))
        else:
            glyph = 0xE15C if t == "menu" else 0xE710
            self.icon_badge.setPixmap(get_mdl2_icon(glyph, 18, "#838ba7").pixmap(18, 18))

        # Subtext details
        cmd = str(props.get('cmd', '')).strip('\'"')
        children = self.item_data.get('children', [])
        children_count = len(children)
        if t == "menu":
            state_desc = "collapsed" if self.is_collapsed else "expanded"
            self.sub_lbl.setText(f"Submenu Folder • {children_count} items nested inside ({state_desc})")
            self._add_badge(f"Menu ({children_count})", "#ca9ee6")
        elif cmd:
            self.sub_lbl.setText(cmd[:75] + ("..." if len(cmd) > 75 else ""))
        else:
            self.sub_lbl.setText("Shortcut Action")

        if self.is_nested and self.parent_title:
            self._add_badge(f"↳ In: {self.parent_title}", "#ca9ee6")
        elif self.item_data.get('parent'):
            self._add_badge(f"↳ In: {self.item_data.get('parent')}", "#ca9ee6")
        elif props.get('menu'):
            clean_m = str(props.get('menu')).strip('\'"')
            self._add_badge(f"↳ In: {clean_m}", "#ca9ee6")

        # Action / Pipeline Flags
        if t != "menu":
            if '\n' in cmd or '&&' in cmd or ';' in cmd:
                steps_cnt = len([s for s in cmd.split('\n') if s.strip()]) if '\n' in cmd else 2
                self._add_badge(f"Pipeline ({steps_cnt})", "#8caaee")
            elif 'powershell' in cmd.lower() or '.ps1' in cmd.lower():
                self._add_badge("PowerShell", "#85c1dc")
            elif 'cmd.exe' in cmd.lower() or '.bat' in cmd.lower() or '.cmd' in cmd.lower():
                self._add_badge("CMD", "#81c8be")
            elif 'python' in cmd.lower() or '.py' in cmd.lower():
                self._add_badge("Python", "#e5c890")
            elif cmd.lower().endswith('.exe') or '.exe ' in cmd.lower():
                self._add_badge("App", "#a6d189")

        raw_args = str(props.get('args', '')).strip('\'"')
        if raw_args:
            self._add_badge("Args", "#8caaee")

        admin = str(props.get('admin', '')).lower()
        if admin in ('true', '1') or 'runas' in cmd.lower():
            self._add_badge("Admin", "#e78284")

        sep = str(props.get('sep', '')).strip('\'"')
        if sep and sep.lower() not in ("none", "false", "0"):
            self._add_badge(f"Sep: {sep.title()}", "#e5c890")

        vis = str(props.get('vis', '')).strip('\'"')
        if vis:
            if 'key.control' in vis and 'key.shift' in vis:
                self._add_badge("Ctrl+Shift", "#babbf1")
            elif 'key.control' in vis:
                self._add_badge("Ctrl", "#babbf1")
            elif 'key.shift' in vis:
                self._add_badge("Shift", "#babbf1")
            elif 'hidden' in vis:
                self._add_badge("Hidden", "#e78284")

        pos = str(props.get('pos', '')).strip('\'"')
        if pos:
            self._add_badge(f"Pos: {pos.title()}", "#a6d189")

        typ = str(props.get('type', '')).strip('\'"')
        if typ and typ.lower() != "all":
            self._add_badge(f"Target: {typ.title()}", "#99d1db")

    def _add_badge(self, text, color):
        lbl = QLabel(text)
        lbl.setFont(QFont("Segoe UI Variable Text", 8, QFont.Bold))
        c = QColor(color)
        bg_rgba = f"rgba({c.red()}, {c.green()}, {c.blue()}, 0.16)"
        border_rgba = f"rgba({c.red()}, {c.green()}, {c.blue()}, 0.42)"
        lbl.setStyleSheet(f"""
            QLabel {{
                background-color: {bg_rgba};
                color: #c6d0f5;
                border: 1px solid {border_rgba};
                border-radius: 9px;
                padding: 1px 8px;
            }}
        """)
        self.badge_lay.addWidget(lbl)


class MenuBuilderWidget(QWidget):
    """
    Dedicated Add Tab.
    100% consistent with ImportsWidget and ModifyRuleEditorDialog patterns.
    Full support for true menu blocks { ... }, visual nesting, multi-action pipelines, and live NSS code preview.
    """
    reload_requested = pyqtSignal()

    def __init__(self, project_root, shell_nss_path=None, parent=None):
        super().__init__(parent)
        self.root = project_root
        self.shell_nss_path = shell_nss_path or os.path.join(self.root, "shell.nss")
        self.dedicated_file_path = os.path.join(self.root, "imports", "custom.nss")

        self.current_file = self.dedicated_file_path
        self.items = []  # Root items (menus contain 'children')
        self._collapsed_menus = set()
        self._current_type_filter = "All"
        self._search_text = ""

        self._setup_ui()
        self._ensure_dedicated_file_exists()
        self.load_file(self.dedicated_file_path)

    def _setup_ui(self):
        main_lay = QHBoxLayout(self)
        main_lay.setContentsMargins(0, 10, 0, 0)
        main_lay.setSpacing(14)

        # Left Side Files Panel (Identical to ImportsWidget)
        self.side = QFrame()
        self.side.setObjectName("sideFilesPanel")
        self.side.setFixedWidth(240)
        self.side.setStyleSheet("""
            #sideFilesPanel {
                background: rgba(0, 0, 0, 0.22);
                border-radius: 16px;
                border: 1px solid rgba(255, 255, 255, 0.04);
            }
        """)
        self.sl = QVBoxLayout(self.side)
        self.sl.setAlignment(Qt.AlignTop)
        self.sl.setContentsMargins(8, 14, 8, 14)
        self.sl.setSpacing(8)

        lbl = QLabel("TARGET FILE")
        lbl.setStyleSheet("color: #70707c; font-size: 11px; font-weight: bold; margin: 4px 0 2px 8px; background: transparent; border: none; letter-spacing: 0.5px;")
        self.sl.addWidget(lbl)

        # Dedicated Custom File Button (Pinned at top)
        self.custom_file_btn = QPushButton(" ★ custom.nss (Default)")
        self.custom_file_btn.setFixedHeight(36)
        self.custom_file_btn.setCursor(Qt.PointingHandCursor)
        self.custom_file_btn.setFont(QFont("Segoe UI Variable Display", 9, QFont.Bold))
        self.custom_file_btn.setStyleSheet("""
            QPushButton {
                background: rgba(231, 130, 132, 0.15);
                color: #ffffff;
                border: 1.5px solid #e78284;
                border-radius: 14px;
                text-align: left;
                padding-left: 12px;
            }
        """)
        self.custom_file_btn.clicked.connect(lambda: self.load_file(self.dedicated_file_path))
        self.sl.addWidget(self.custom_file_btn)

        files_sublbl = QLabel("OTHER FILES")
        files_sublbl.setStyleSheet("color: #70707c; font-size: 10px; font-weight: bold; margin: 8px 0 2px 8px;")
        self.sl.addWidget(files_sublbl)

        # Scroll area for scanned files
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
        self.sl.addWidget(self.f_scroll)

        # New File Button
        new_f_btn = PillPushButton("+ New File", "secondary", height=32)
        new_f_btn.clicked.connect(self._create_new_file_dialog)
        self.sl.addWidget(new_f_btn)

        main_lay.addWidget(self.side)

        # Right Main Content Area
        cr = QWidget()
        crl = QVBoxLayout(cr)
        crl.setContentsMargins(0, 0, 0, 0)
        crl.setSpacing(10)
        main_lay.addWidget(cr, 1)

        # Top Header Bar: Search input + Add buttons
        head = QHBoxLayout()
        head.setSpacing(8)

        self.search = PillLineEdit("Search items/menus...")
        self.search.textChanged.connect(self._on_search_changed)
        head.addWidget(self.search, 1)

        add_item_btn = PillPushButton("+ New Item", "primary", height=34)
        add_item_btn.clicked.connect(lambda: self._open_add_item_dialog())
        head.addWidget(add_item_btn)

        add_menu_btn = PillPushButton("+ New Menu", "secondary", height=34)
        add_menu_btn.setFont(QFont("Segoe UI Variable Text", 9, QFont.Bold))
        add_menu_btn.clicked.connect(self._open_add_menu_dialog)
        head.addWidget(add_menu_btn)

        crl.addLayout(head)

        # Filter Tags Bar (includes Drafts tag)
        self.type_tags = FilterBar([
            ("All", "#51576d"),
            ("Items", "#8caaee"),
            ("Menus", "#ca9ee6"),
            ("Drafts", "#ef9f76")
        ])
        self.type_tags.filter_changed.connect(self._on_filter_changed)
        crl.addWidget(self.type_tags)

        # Scroll area for items list
        self.cards_scroll = QScrollArea()
        self.cards_scroll.setWidgetResizable(True)
        self.cards_scroll.setStyleSheet("background: transparent; border: none;")
        self.cards_cont = QWidget()
        self.cards_cont.setStyleSheet("background: transparent;")
        self.cards_lay = QVBoxLayout(self.cards_cont)
        self.cards_lay.setContentsMargins(0, 0, 4, 0)
        self.cards_lay.setSpacing(8)
        self.cards_lay.setAlignment(Qt.AlignTop)
        self.cards_scroll.setWidget(self.cards_cont)

        crl.addWidget(self.cards_scroll, 1)

    def _ensure_dedicated_file_exists(self):
        if not os.path.exists(self.dedicated_file_path):
            os.makedirs(os.path.dirname(self.dedicated_file_path), exist_ok=True)
            with open(self.dedicated_file_path, 'w', encoding='utf-8') as f:
                f.write("// Custom User Items & Menus\n// Managed by iMA Menu Launcher\n\n")
        self._ensure_file_imported_in_shell(self.dedicated_file_path)

    def _ensure_file_imported_in_shell(self, filepath):
        if not os.path.exists(self.shell_nss_path):
            return
        rel = os.path.relpath(filepath, self.root).replace('\\', '/')
        import_stmt = f"import '{rel}'"
        content = read_file(self.shell_nss_path)
        if import_stmt in content or import_stmt.replace('/', '\\') in content:
            return
        new_content = content.rstrip() + f"\n{import_stmt}\n"
        safe_file_write(self.shell_nss_path, new_content)

    def _get_menu_and_descendant_titles(self, menu_data):
        titles = set()
        if not menu_data:
            return titles
        t = str(menu_data.get('props', {}).get('title', '')).strip('\'"')
        if t:
            titles.add(t.lower())
        for ch in menu_data.get('children', []):
            if ch.get('type', '').lower() == 'menu':
                titles.update(self._get_menu_and_descendant_titles(ch))
        return titles

    def _get_menu_titles(self, exclude_menu=None):
        """Returns list of clean menu titles existing across all .nss files and active tree (recursive)."""
        excluded = self._get_menu_and_descendant_titles(exclude_menu) if exclude_menu else set()
        titles = []

        # 1. Menus in the currently loaded file tree (active unsaved or nested items)
        def _collect(items):
            for it in items:
                if it.get('type', '').lower() == 'menu':
                    raw_t = str(it.get('props', {}).get('title', '')).strip('\'"')
                    if raw_t and raw_t.lower() not in excluded:
                        if raw_t not in titles:
                            titles.append(raw_t)
                    _collect(it.get('children', []))
        _collect(self.items)

        # Register local menu icons into get_nss_menus_dict so live custom icons render
        try:
            from utils import get_nss_menus_dict
            menus_dict = get_nss_menus_dict()
            def _register_local_icons(items):
                for it in items:
                    if it.get('type', '').lower() == 'menu':
                        raw_t = str(it.get('props', {}).get('title', '')).strip('\'"')
                        icon_v = it.get('props', {}).get('icon') or it.get('props', {}).get('image') or ''
                        if raw_t:
                            t_k = raw_t.lower()
                            if t_k not in menus_dict or (icon_v and not menus_dict[t_k].get('icon')):
                                menus_dict[t_k] = {'title': raw_t, 'icon': icon_v, 'file': self.current_file}
                        _register_local_icons(it.get('children', []))
            _register_local_icons(self.items)
        except Exception:
            pass

        # 2. Standard built-in menus supported by Nilesoft Shell
        for builtin in ("Main", "Options"):
            if builtin.lower() not in excluded and builtin not in titles:
                titles.append(builtin)

        # 3. All menus across all .nss files in imports, plugins, and root
        if getattr(self, 'root', None) and os.path.exists(self.root):
            paths = [os.path.join(self.root, 'imports'), os.path.join(self.root, 'plugins')]
            for p in paths:
                if not os.path.exists(p):
                    continue
                for r, _, files in os.walk(p):
                    for f in files:
                        if f.endswith('.nss') and not f.endswith('.bak'):
                            fp = os.path.join(r, f)
                            try:
                                content = read_file(fp)
                                for item in find_items_and_menus(content, types=('menu',)):
                                    raw_t = str(item.get('props', {}).get('title', '')).strip('\'"')
                                    if raw_t and raw_t.lower() not in excluded:
                                        if raw_t not in titles:
                                            titles.append(raw_t)
                            except Exception:
                                pass

            shell_nss = os.path.join(self.root, 'shell.nss')
            if os.path.exists(shell_nss):
                try:
                    content = read_file(shell_nss)
                    for item in find_items_and_menus(content, types=('menu',)):
                        raw_t = str(item.get('props', {}).get('title', '')).strip('\'"')
                        if raw_t and raw_t.lower() not in excluded:
                            if raw_t not in titles:
                                titles.append(raw_t)
                except Exception:
                    pass

        return titles

    def load_file(self, filepath):
        self.current_file = filepath
        self._refresh_sidebar_files()

        content = read_file(filepath)
        raw_items = find_items_and_menus(content, types=('item', 'menu', 'separator'))

        # Build hierarchy: nested items inside menu blocks { ... }
        self.items = []
        menu_stack = []
        for it in raw_items:
            it['children'] = []
            it['file'] = filepath
            it['id'] = it.get('id') or str(uuid.uuid4())

            # Pop finished menus
            while menu_stack and it['start'] >= menu_stack[-1]['end']:
                menu_stack.pop()

            if menu_stack:
                it['parent'] = str(menu_stack[-1]['props'].get('title', '')).strip('\'"')
                menu_stack[-1]['children'].append(it)
            else:
                raw_m = str(it.get('props', {}).get('menu', '')).strip('\'"')
                it['parent'] = raw_m if raw_m else None
                self.items.append(it)

            if it.get('type', '').lower() == 'menu':
                menu_stack.append(it)

        self._apply_filters()

    def _refresh_sidebar_files(self):
        while self.file_l.count():
            it = self.file_l.takeAt(0)
            if it.widget():
                it.widget().deleteLater()

        is_custom = os.path.normpath(self.current_file) == os.path.normpath(self.dedicated_file_path)
        if is_custom:
            self.custom_file_btn.setStyleSheet("""
                QPushButton {
                    background: rgba(231, 130, 132, 0.18);
                    color: #ffffff;
                    border: 1.5px solid #e78284;
                    border-radius: 14px;
                    text-align: left;
                    padding-left: 12px;
                }
            """)
        else:
            self.custom_file_btn.setStyleSheet("""
                QPushButton {
                    background: rgba(255, 255, 255, 0.04);
                    color: #c6d0f5;
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    border-radius: 14px;
                    text-align: left;
                    padding-left: 12px;
                }
                QPushButton:hover {
                    background: rgba(255, 255, 255, 0.08);
                    border-color: #e78284;
                }
            """)

        scanned = []
        imports_dir = os.path.join(self.root, "imports")
        if os.path.exists(imports_dir):
            for fn in sorted(os.listdir(imports_dir)):
                if fn.lower().endswith(".nss"):
                    fp = os.path.join(imports_dir, fn)
                    if os.path.normpath(fp) != os.path.normpath(self.dedicated_file_path):
                        scanned.append((fn, fp))

        for fn, fp in scanned:
            btn = QPushButton(f"  {fn}")
            btn.setFixedHeight(32)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFont(QFont("Segoe UI Variable Text", 9))
            is_active = os.path.normpath(self.current_file) == os.path.normpath(fp)
            if is_active:
                btn.setStyleSheet("""
                    QPushButton {
                        background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 rgba(231, 130, 132, 0.28), stop:1 rgba(202, 158, 230, 0.18));
                        color: #ffffff;
                        font-weight: bold;
                        border: 1px solid rgba(231, 130, 132, 0.5);
                        border-radius: 12px;
                        text-align: left;
                        padding-left: 10px;
                    }
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        background: transparent;
                        color: #838ba7;
                        border: 1px solid transparent;
                        border-radius: 12px;
                        text-align: left;
                        padding-left: 10px;
                    }
                    QPushButton:hover {
                        background: rgba(255, 255, 255, 0.05);
                        color: #c6d0f5;
                        border-color: rgba(255, 255, 255, 0.09);
                    }
                """)
            btn.clicked.connect(lambda _, path=fp: self.load_file(path))
            self.file_l.addWidget(btn)

    def _on_search_changed(self, text):
        self._search_text = text.strip().lower()
        self._apply_filters()

    def _on_filter_changed(self, tag_btn):
        if hasattr(tag_btn, 'text'):
            self._current_type_filter = tag_btn.text().strip()
        elif isinstance(tag_btn, str):
            self._current_type_filter = tag_btn.strip()
        else:
            self._current_type_filter = "All"
        self._apply_filters()

    def _item_matches_filter(self, it):
        t = it.get('type', 'item').lower()
        props = it.get('props', {})
        title = str(props.get('title', '')).strip('\'"').lower()
        cmd = str(props.get('cmd', '')).strip('\'"').lower()
        is_draft = it.get('is_draft', False)

        if self._current_type_filter == "Items":
            if t != "item" and not any(self._item_matches_filter(ch) for ch in it.get('children', [])):
                return False
        elif self._current_type_filter == "Menus" and t != "menu":
            return False
        elif self._current_type_filter == "Drafts":
            if not is_draft and not any(self._item_matches_filter(ch) for ch in it.get('children', [])):
                return False

        if self._search_text:
            if self._search_text not in title and self._search_text not in cmd and self._search_text not in t:
                return any(self._item_matches_filter(ch) for ch in it.get('children', []))
        return True

    def _toggle_menu_collapse(self, menu_data):
        menu_key = str(menu_data.get('props', {}).get('title', '')).strip('\'"') or str(id(menu_data))
        if menu_key in self._collapsed_menus:
            self._collapsed_menus.remove(menu_key)
        else:
            self._collapsed_menus.add(menu_key)
        self._apply_filters()

    def _apply_filters(self):
        while self.cards_lay.count():
            it = self.cards_lay.takeAt(0)
            if it.widget():
                w = it.widget()
                w.setParent(None)
                w.deleteLater()

        visible_count = 0
        for it in self.items:
            if not self._item_matches_filter(it):
                continue
            visible_count += 1
            self._render_item_tree(it, self.cards_lay, parent_menu=None, nest_level=0)

        if visible_count == 0:
            empty_w = QWidget()
            el = QVBoxLayout(empty_w)
            el.setAlignment(Qt.AlignCenter)
            el.setSpacing(10)
            el.setContentsMargins(0, 60, 0, 60)

            ic = QLabel("\uE710")
            ic.setFont(QFont("Segoe MDL2 Assets", 36))
            ic.setStyleSheet("color: #70707c;")
            ic.setAlignment(Qt.AlignCenter)
            el.addWidget(ic)

            title_lbl = QLabel("No items found in this file")
            title_lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #838ba7;")
            title_lbl.setAlignment(Qt.AlignCenter)
            el.addWidget(title_lbl)

            sub_lbl = QLabel("Click '+ New Item' or '+ New Menu' above to create a context menu item.")
            sub_lbl.setStyleSheet("font-size: 12px; color: #51576d;")
            sub_lbl.setAlignment(Qt.AlignCenter)
            el.addWidget(sub_lbl)

            self.cards_lay.addWidget(empty_w)

    def _render_item_tree(self, it, container_layout, parent_menu=None, nest_level=0):
        t = it.get('type', 'item').lower()
        props = it.get('props', {})
        menu_key = str(props.get('title', '')).strip('\'"') or str(id(it))
        is_collapsed = menu_key in self._collapsed_menus
        parent_title = str(parent_menu.get('props', {}).get('title', '')).strip('\'"') if parent_menu else None

        card = BuilderItemCard(it, container_layout.parentWidget(), is_nested=(nest_level > 0), parent_title=parent_title, is_collapsed=is_collapsed)
        card.edit_requested.connect(self._open_edit_dialog)
        card.delete_requested.connect(lambda item=it: self._delete_item(item))
        card.move_up_requested.connect(lambda item=it, pm=parent_menu: self._move_child_up(pm, item) if pm else self._move_item_up(item))
        card.move_down_requested.connect(lambda item=it, pm=parent_menu: self._move_child_down(pm, item) if pm else self._move_item_down(item))
        card.un_nest_requested.connect(lambda item=it, pm=parent_menu: self._un_nest_child_item(pm, item) if pm else None)
        card.add_inside_requested.connect(self._open_add_child_item_dialog)
        card.add_menu_inside_requested.connect(self._open_add_child_menu_dialog)
        card.toggle_draft_requested.connect(self._toggle_item_draft)
        card.collapse_toggle_requested.connect(self._toggle_menu_collapse)
        container_layout.addWidget(card)

        if t == "menu":
            children = it.get('children', [])
            if children:
                rendered_children = [ch for ch in children if self._item_matches_filter(ch)]
                if rendered_children:
                    nest_container = QFrame()
                    nest_container.setObjectName("nestContainer")
                    nest_container.setStyleSheet("""
                        QFrame#nestContainer {
                            background: transparent;
                            border-left: 2px solid rgba(202, 158, 230, 0.35);
                            border-radius: 0px;
                        }
                    """)
                    nl = QVBoxLayout(nest_container)
                    nl.setContentsMargins(24, 4, 0, 4)
                    nl.setSpacing(6)

                    for ch in rendered_children:
                        self._render_item_tree(ch, nl, parent_menu=it, nest_level=nest_level + 1)

                    nest_container.setVisible(not is_collapsed)
                    container_layout.addWidget(nest_container)

    def _open_add_item_dialog(self, parent_menu=None):
        avail_menus = self._get_menu_titles()
        parent_title = str(parent_menu.get('props', {}).get('title', '')).strip('\'"') if parent_menu else None
        dlg = ItemConfigDialog(kind="item", parent=self, is_new=True, available_menus=avail_menus, parent_menu_title=parent_title)
        if dlg.exec_():
            new_props = dlg.get_props()
            new_parent_title = dlg.get_parent_menu()
            new_item = {'type': 'item', 'props': new_props, 'file': self.current_file, 'children': []}

            if new_parent_title:
                target_menu = self._find_menu_by_title(new_parent_title)
                if target_menu:
                    new_item['parent'] = new_parent_title
                    new_item['props'].pop('menu', None)
                    target_menu['children'].append(new_item)
                else:
                    new_item['parent'] = new_parent_title
                    new_item['props']['menu'] = f"'{new_parent_title}'" if ' ' in new_parent_title else new_parent_title
                    self.items.append(new_item)
            else:
                new_item['parent'] = None
                new_item['props'].pop('menu', None)
                self.items.append(new_item)
            self._save_items_to_file()

    def _open_add_child_item_dialog(self, parent_menu):
        self._open_add_item_dialog(parent_menu=parent_menu)

    def _open_add_menu_dialog(self, parent_menu=None):
        avail_menus = self._get_menu_titles()
        parent_title = str(parent_menu.get('props', {}).get('title', '')).strip('\'"') if parent_menu else None
        dlg = ItemConfigDialog(kind="menu", parent=self, is_new=True, available_menus=avail_menus, parent_menu_title=parent_title)
        if dlg.exec_():
            new_props = dlg.get_props()
            new_parent_title = dlg.get_parent_menu()
            new_item = {'type': 'menu', 'props': new_props, 'file': self.current_file, 'children': []}

            if new_parent_title:
                target_menu = self._find_menu_by_title(new_parent_title)
                if target_menu:
                    new_item['parent'] = new_parent_title
                    new_item['props'].pop('menu', None)
                    target_menu['children'].append(new_item)
                else:
                    new_item['parent'] = new_parent_title
                    new_item['props']['menu'] = f"'{new_parent_title}'" if ' ' in new_parent_title else new_parent_title
                    self.items.append(new_item)
            else:
                new_item['parent'] = None
                new_item['props'].pop('menu', None)
                self.items.append(new_item)
            self._save_items_to_file()

    def _open_add_child_menu_dialog(self, parent_menu):
        self._open_add_menu_dialog(parent_menu=parent_menu)

    def _open_edit_dialog(self, item_data):
        avail_menus = self._get_menu_titles(exclude_menu=item_data if item_data.get('type') == 'menu' else None)
        cur_parent = item_data.get('parent')
        dlg = ItemConfigDialog(item_data=item_data, parent=self, is_new=False, available_menus=avail_menus, parent_menu_title=cur_parent)
        dlg.item_deleted.connect(lambda: self._delete_item(item_data, confirm=False))
        if dlg.exec_():
            item_data['props'] = dlg.get_props()
            new_parent_title = dlg.get_parent_menu()

            # If user fixed the item, clear draft status
            if item_data.get('is_draft'):
                item_data['is_draft'] = False
                item_data.pop('error_msg', None)

            # Handle parent change (nesting/un-nesting)
            if new_parent_title != cur_parent:
                self._reparent_item(item_data, cur_parent, new_parent_title)

            self._save_items_to_file()

    def _toggle_item_draft(self, item_data):
        item_data['is_draft'] = not item_data.get('is_draft', False)
        if not item_data['is_draft']:
            item_data.pop('error_msg', None)
        self._save_items_to_file()

    def _find_menu_by_title(self, title):
        clean = (title or "").strip('\'"').lower()
        def _search(items):
            for it in items:
                if it.get('type', '').lower() == 'menu':
                    m_title = str(it.get('props', {}).get('title', '')).strip('\'"').lower()
                    if m_title == clean:
                        return it
                    found = _search(it.get('children', []))
                    if found:
                        return found
            return None
        return _search(self.items)

    def _detach_item(self, item_data):
        """Safely removes an item from self.items or any menu's children at any depth."""
        if item_data in self.items:
            self.items.remove(item_data)
            return True
        def _remove_from(items):
            for it in items:
                children = it.get('children', [])
                if item_data in children:
                    children.remove(item_data)
                    return True
                if _remove_from(children):
                    return True
            return False
        return _remove_from(self.items)

    def _reparent_item(self, item_data, old_parent_title, new_parent_title):
        self._detach_item(item_data)
        if new_parent_title:
            target = self._find_menu_by_title(new_parent_title)
            if target:
                item_data['parent'] = new_parent_title
                item_data.get('props', {}).pop('menu', None)
                target['children'].append(item_data)
            else:
                item_data['parent'] = new_parent_title
                item_data.setdefault('props', {})['menu'] = f"'{new_parent_title}'" if ' ' in new_parent_title else new_parent_title
                self.items.append(item_data)
        else:
            item_data['parent'] = None
            item_data.get('props', {}).pop('menu', None)
            self.items.append(item_data)

    def _un_nest_child_item(self, parent_menu, child_item):
        self._detach_item(child_item)
        child_item['parent'] = None
        self.items.append(child_item)
        self._save_items_to_file()

    def _delete_item(self, item_data, confirm=True):
        if confirm:
            title = str(item_data.get('props', {}).get('title', '')).strip('\'"') or item_data.get('type')
            is_menu = item_data.get('type') == 'menu'
            msg = f"Are you sure you want to delete '{title}'?"
            if is_menu and item_data.get('children'):
                msg += f"\nAll {len(item_data['children'])} items inside will also be deleted."
            dlg = StyledConfirmDialog(
                title="Delete Menu" if is_menu else "Delete Item",
                message=msg,
                parent=self,
                confirm_text="Delete",
                danger=True
            )
            if not dlg.exec_():
                return

        self._detach_item(item_data)
        self._save_items_to_file()

    def _delete_child_item(self, parent_menu, child_item):
        self._delete_item(child_item, confirm=True)

    def _move_item_up(self, item_data):
        if item_data in self.items:
            idx = self.items.index(item_data)
            if idx > 0:
                self.items[idx], self.items[idx - 1] = self.items[idx - 1], self.items[idx]
                self._save_items_to_file()

    def _move_item_down(self, item_data):
        if item_data in self.items:
            idx = self.items.index(item_data)
            if idx < len(self.items) - 1:
                self.items[idx], self.items[idx + 1] = self.items[idx + 1], self.items[idx]
                self._save_items_to_file()

    def _move_child_up(self, parent_menu, child_item):
        if not parent_menu:
            return self._move_item_up(child_item)
        children = parent_menu.get('children', [])
        if child_item in children:
            idx = children.index(child_item)
            if idx > 0:
                children[idx], children[idx - 1] = children[idx - 1], children[idx]
                self._save_items_to_file()

    def _move_child_down(self, parent_menu, child_item):
        if not parent_menu:
            return self._move_item_down(child_item)
        children = parent_menu.get('children', [])
        if child_item in children:
            idx = children.index(child_item)
            if idx < len(children) - 1:
                children[idx], children[idx + 1] = children[idx + 1], children[idx]
                self._save_items_to_file()

    def _serialize_item_block(self, it, indent=""):
        t = it.get('type', 'item').lower()
        props = it.get('props', {})
        is_draft = it.get('is_draft', False)
        error_msg = it.get('error_msg')

        if t == "separator":
            raw_sep = f"{indent}separator"
            if is_draft:
                return f"{indent}// [Draft] separator"
            return raw_sep

        pts = []
        for k, v in props.items():
            if k in ('_order', 'file', 'start', 'end', 'cmd_end', 'raw_inner', 'has_children', 'indent', '_is_temp', 'children', 'parent', 'id', 'is_draft', 'error_msg'):
                continue
            if k == 'menu' and it.get('parent') and indent != "":
                continue
            if v is not None and str(v).strip() != '':
                pts.append(format_nss_value(k, str(v).strip()))

        header = f"{indent}{t}({' '.join(pts)})"
        if t == "menu":
            children_str = []
            for ch in it.get('children', []):
                children_str.append(self._serialize_item_block(ch, indent + "    "))
            body = "\n".join(children_str)
            block = f"{header}\n{indent}{{\n{body}\n{indent}}}" if body else f"{header}\n{indent}{{\n{indent}}}"
            if is_draft:
                # Comment out menu block
                lines = block.split('\n')
                tag = f"// [Draft: {error_msg}] " if error_msg else "// [Draft] "
                return tag + lines[0] + "\n" + "\n".join([f"// {l}" for l in lines[1:]])
            return block
        else:
            if is_draft:
                tag = f"// [Draft: {error_msg}] " if error_msg else "// [Draft] "
                return f"{indent}{tag}{header.strip()}"
            return header

    def _check_shell_log_errors(self):
        """Monitors shell.log for syntax errors in the current file."""
        log_path = os.path.join(self.root, "shell.log")
        if not os.path.exists(log_path):
            return None
        try:
            with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            entries = parse_log_entries(content)
            cur_fn = os.path.basename(self.current_file).lower()
            for ent in reversed(entries):
                if ent.level == 'error' and os.path.basename(ent.filename).lower() == cur_fn:
                    return ent
        except Exception:
            pass
        return None

    def _find_item_by_line(self, line_num):
        """Finds item in self.items whose line in file matches error line."""
        try:
            content = read_file(self.current_file)
            lines = content.splitlines()
            if 0 <= line_num - 1 < len(lines):
                target_line = lines[line_num - 1].strip()
                # Check root items
                for it in self.items:
                    props = it.get('props', {})
                    t = it.get('type')
                    title = str(props.get('title', '')).strip('\'"')
                    cmd = str(props.get('cmd', '')).strip('\'"')
                    if (title and title in target_line) or (cmd and cmd in target_line):
                        return it
                    for ch in it.get('children', []):
                        ch_p = ch.get('props', {})
                        ch_t = str(ch_p.get('title', '')).strip('\'"')
                        ch_c = str(ch_p.get('cmd', '')).strip('\'"')
                        if (ch_t and ch_t in target_line) or (ch_c and ch_c in target_line):
                            return ch
        except Exception:
            pass
        # Fallback to last added/edited item
        if self.items:
            return self.items[-1]
        return None

    def _save_items_to_file(self, skip_log_check=False):
        """Serializes current items and writes safely to current file with log monitoring."""
        blocks = []
        for it in self.items:
            blocks.append(self._serialize_item_block(it))

        header_comment = f"// Managed by iMA Menu Launcher\n\n"
        full_content = header_comment + "\n\n".join(blocks) + "\n"

        safe_file_write(self.current_file, full_content)
        self._ensure_file_imported_in_shell(self.current_file)

        # Trigger shell reload
        self.reload_requested.emit()

        # Check shell.log for syntax errors
        if not skip_log_check:
            # Let shell engine process
            err = self._check_shell_log_errors()
            if err:
                offending_item = self._find_item_by_line(err.line)
                if offending_item and not offending_item.get('is_draft'):
                    offending_item['is_draft'] = True
                    offending_item['error_msg'] = f"Line {err.line}, col {err.column}: {err.message}"
                    # Re-save with draft commented out to protect the context menu
                    self._save_items_to_file(skip_log_check=True)

                    # Pop styled error alert
                    alert_dlg = StyledConfirmDialog(
                        title="Syntax Error Caught",
                        message=(
                            f"Nilesoft Shell reported a syntax error in '{os.path.basename(self.current_file)}':\n\n"
                            f"• Line {err.line}, Column {err.column}\n"
                            f"• Error: {err.message}\n\n"
                            f"To protect your context menu, this item has been automatically saved as a Draft (commented out).\n"
                            f"You can edit it anytime to fix the syntax and re-activate it."
                        ),
                        parent=self,
                        confirm_text="Got It",
                        danger=True
                    )
                    alert_dlg.exec_()
                    return

        self.load_file(self.current_file)

    def _create_new_file_dialog(self):
        name, ok = QInputDialog.getText(self, "Create New NSS File", "Enter file name (e.g. tools.nss, my-menu.nss):")
        if not ok or not name.strip():
            return
        clean_name = name.strip()
        if not clean_name.lower().endswith(".nss"):
            clean_name += ".nss"

        new_fp = os.path.join(self.root, "imports", clean_name)
        if os.path.exists(new_fp):
            dlg = StyledConfirmDialog("File Exists", f"File '{clean_name}' already exists.", parent=self, confirm_text="OK", danger=False)
            dlg.exec_()
            return

        os.makedirs(os.path.dirname(new_fp), exist_ok=True)
        with open(new_fp, 'w', encoding='utf-8') as f:
            f.write(f"// {clean_name} — Custom items created with iMA Menu Launcher\n\n")

        self._ensure_file_imported_in_shell(new_fp)
        self.load_file(new_fp)

    def refresh(self):
        """Called when user switches to Add tab."""
        self._ensure_dedicated_file_exists()
        self.load_file(self.current_file or self.dedicated_file_path)
