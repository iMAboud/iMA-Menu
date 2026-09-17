import os
import sys
import json
import re
import time
import shutil

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QLabel, QPushButton, QComboBox, QLineEdit, QPlainTextEdit,
    QTreeWidget, QTreeWidgetItem, QSplitter, QFrame, QTabWidget,
    QHeaderView, QMessageBox, QFileDialog, QSizePolicy, QAbstractItemView,
    QTextEdit, QMenu, QInputDialog, QDialog, QProgressBar
)
from PyQt5.QtGui import QFont, QColor, QIcon, QPixmap, QPainter, QPen, QTextFormat, QTextCursor
from PyQt5.QtCore import Qt, QTimer, QSize, QRect, pyqtSignal

# Ensure local imports
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from nss_parser import find_items_and_menus, parse_nss_args
from utils import render_nss_asset_pixmap, get_mdl2_icon, trigger_shell_reload, send_ipc_command
from nss_error_monitor import parse_log_entries, resolve_nss_path

ITEMS_JSON_PATH = os.path.join(SCRIPT_DIR, "cache", "items.json")


def read_shell_log_new_data(log_path, initial_size):
    """Reads newly appended data from shell.log with multi-encoding fallback."""
    if not os.path.exists(log_path):
        return "", []
    try:
        current_size = os.path.getsize(log_path)
        if current_size <= initial_size:
            return "", []
        with open(log_path, "rb") as f:
            f.seek(initial_size)
            raw_bytes = f.read()

        decoded_text = ""
        for enc in ['utf-16', 'utf-16-le', 'utf-8']:
            try:
                decoded_text = raw_bytes.decode(enc)
                if enc == 'utf-8' and '\x00' in decoded_text:
                    continue
                break
            except (UnicodeDecodeError, UnicodeError):
                continue
        if not decoded_text:
            decoded_text = raw_bytes.decode('utf-8', errors='ignore')

        decoded_text = decoded_text.replace('\x00', '')
        entries = parse_log_entries(decoded_text)
        return decoded_text, entries
    except Exception as e:
        return f"Error: {e}", []


def get_project_root():
    """Resolves project root where shell.nss, shell.log, and shell.exe reside."""
    root = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
    if os.path.exists(os.path.join(root, "shell.nss")):
        return root
    if os.path.exists(os.path.join(SCRIPT_DIR, "shell.nss")):
        return SCRIPT_DIR
    return root


def clean_title(val):
    if not val:
        return ""
    s = str(val).strip()
    if (s.startswith("'") and s.endswith("'")) or (s.startswith('"') and s.endswith('"')):
        s = s[1:-1]
    if s.startswith('title.'):
        s = s[6:].replace('_', ' ').title()
    if '@' in s:
        s = s.split('@')[0].strip()
    if '\\t' in s or '\t' in s:
        s = s.replace('\\t', ' ').replace('\t', ' ').strip()
    if '+' in s and ('\\T' in s or '\\t' in s):
        s = s.split('+')[0].strip()
    if 'str.res' in s or 'shell32' in s:
        s = "System Menu"
    s = s.replace('&', '')
    s = re.sub(r'Nilesoft Shell', 'iMA Menu', s, flags=re.IGNORECASE)
    s = re.sub(r'Nilesoft', 'iMA Menu', s, flags=re.IGNORECASE)
    return s.strip()


def clean_friendly_menu_name(title):
    if not title:
        return ""
    t = clean_title(title)
    if t.startswith("{") or t == "{" or t == "}":
        return ""
    if "menu_od" in t.lower() or "onedrive" in t.lower():
        return "OneDrive"
    if "menu_gd" in t.lower() or "google" in t.lower():
        return "Google Drive"
    if "menu_db" in t.lower() or "dropbox" in t.lower():
        return "Dropbox"
    if "menu_cloud" in t.lower():
        return "Cloud Drives"
    if "theme_menu" in t.lower():
        return "Themes"
    if t.startswith("menu_") or t == "name_menu" or t == "app.name" or t == "Item":
        return ""
    if len(t) > 20:
        t = t[:18] + "…"
    return t


def clean_prop(val):
    if not val:
        return ""
    s = str(val).strip()
    if (s.startswith("'") and s.endswith("'")) or (s.startswith('"') and s.endswith('"')):
        return s[1:-1]
    return s


def strip_nss_comments(code):
    """Strips all single-line and multi-line comments from NSS code, returning pure commands."""
    lines = []
    in_block = False
    for line in code.splitlines():
        trimmed = line.strip()
        if in_block:
            if '*/' in trimmed:
                in_block = False
                line = trimmed.split('*/', 1)[1]
            else:
                continue
        if '/*' in trimmed and '*/' not in trimmed:
            in_block = True
            line = trimmed.split('/*', 1)[0]
        elif '/*' in trimmed and '*/' in trimmed:
            line = re.sub(r'/\*.*?\*/', '', line)

        trimmed = line.strip()
        if trimmed.startswith('//'):
            continue

        if '//' in line:
            in_q = False
            q_char = ''
            cut_idx = -1
            for i, c in enumerate(line):
                if c in ("'", '"'):
                    if not in_q:
                        in_q = True
                        q_char = c
                    elif c == q_char:
                        in_q = False
                elif not in_q and c == '/' and i + 1 < len(line) and line[i+1] == '/':
                    cut_idx = i
                    break
            if cut_idx != -1:
                line = line[:cut_idx].rstrip()

        line = re.sub(r'Nilesoft Shell', 'iMA Menu', line, flags=re.IGNORECASE)
        line = re.sub(r'Nilesoft', 'iMA Menu', line, flags=re.IGNORECASE)

        if line.strip():
            lines.append(line)

    return "\n".join(lines).strip()


def validate_nss_syntax_detailed(content):
    """Validates NSS syntax matching Nilesoft Shell C++ engine rules."""
    stack = []
    i = 0
    n = len(content)
    line = 1
    col = 0

    while i < n:
        c = content[i]
        col += 1
        if c == '\n':
            line += 1
            col = 0

        # Comments
        if c == '/' and i + 1 < n:
            n1 = content[i + 1]
            if n1 == '/':
                i += 2
                col += 1
                while i < n and content[i] != '\n':
                    i += 1
                continue
            elif n1 == '*':
                s_line = line
                s_col = col
                i += 2
                col += 1
                closed = False
                while i + 1 < n:
                    if content[i] == '\n':
                        line += 1
                        col = 0
                    elif content[i] == '*' and content[i + 1] == '/':
                        i += 2
                        col += 1
                        closed = True
                        break
                    i += 1
                    col += 1
                if not closed:
                    return False, f"Unclosed multiline comment '/*' starting at line {s_line}", s_line, s_col
                continue

        # Double-quoted string: "..."
        if c == '"':
            if i + 2 < n and content[i:i+3] == '"""':
                s_line = line
                s_col = col
                i += 3
                col += 2
                closed = False
                while i + 2 < n:
                    if content[i] == '\n':
                        line += 1
                        col = 0
                    elif content[i:i+3] == '"""':
                        i += 3
                        col += 2
                        closed = True
                        break
                    i += 1
                    col += 1
                if not closed:
                    return False, f"Unclosed string literal (\"\"\") starting at line {s_line}:{s_col}", s_line, s_col
                continue
            else:
                s_line = line
                s_col = col
                i += 1
                closed = False
                while i < n:
                    ch = content[i]
                    col += 1
                    if ch == '\n':
                        line += 1
                        col = 0
                    elif ch == '\\':
                        i += 2
                        col += 1
                        continue
                    elif ch == '"':
                        closed = True
                        i += 1
                        break
                    i += 1
                if not closed:
                    return False, f"Unclosed string literal (\") starting at line {s_line}:{s_col}", s_line, s_col
                continue

        # Backtick string: `...`
        if c == '`':
            s_line = line
            s_col = col
            i += 1
            closed = False
            while i < n:
                ch = content[i]
                col += 1
                if ch == '\n':
                    line += 1
                    col = 0
                elif ch == '`':
                    closed = True
                    i += 1
                    break
                i += 1
            if not closed:
                return False, f"Unclosed string literal (`) starting at line {s_line}:{s_col}", s_line, s_col
            continue

        # Single-quoted string: '...'
        if c == "'":
            if i + 2 < n and content[i:i+3] == "'''":
                s_line = line
                s_col = col
                i += 3
                col += 2
                closed = False
                while i + 2 < n:
                    if content[i] == '\n':
                        line += 1
                        col = 0
                    elif content[i:i+3] == "'''":
                        i += 3
                        col += 2
                        closed = True
                        break
                    i += 1
                    col += 1
                if not closed:
                    return False, f"Unclosed string literal (''') starting at line {s_line}:{s_col}", s_line, s_col
                continue
            else:
                s_line = line
                s_col = col
                i += 1
                closed = False
                while i < n:
                    ch = content[i]
                    col += 1
                    if ch == '\n':
                        line += 1
                        col = 0
                    elif ch == '@':
                        # 1. Check @"..." verbatim/interpolated double-quoted string inside '...'
                        if i + 1 < n and content[i + 1] == '"':
                            i += 2
                            col += 1
                            while i < n:
                                if content[i] == '\n':
                                    line += 1
                                    col = 0
                                elif content[i] == '\\':
                                    i += 2
                                    col += 1
                                    continue
                                elif content[i] == '"':
                                    i += 1
                                    col += 1
                                    break
                                i += 1
                                col += 1
                            continue

                        # 2. Check @(...) or @ident(...) expression inside '...'
                        m = re.match(r'^(?:[a-zA-Z0-9_\.]*\s*)?\(', content[i+1:])
                        if m:
                            paren_start = i + 1 + len(m.group(0)) - 1
                            p_depth = 1
                            j = paren_start + 1
                            col_adj = (j - i)
                            col += col_adj
                            while j < n and p_depth > 0:
                                if content[j] == '\n':
                                    line += 1
                                    col = 0
                                elif content[j] == '(':
                                    p_depth += 1
                                elif content[j] == ')':
                                    p_depth -= 1
                                    if p_depth == 0:
                                        i = j + 1
                                        col += 1
                                        break
                                elif content[j] in ('"', "'", '`'):
                                    q = content[j]
                                    j += 1
                                    col += 1
                                    while j < n:
                                        if content[j] == '\n':
                                            line += 1
                                            col = 0
                                        elif q == '"' and content[j] == '\\':
                                            j += 2
                                            col += 2
                                            continue
                                        elif content[j] == q:
                                            j += 1
                                            col += 1
                                            break
                                        j += 1
                                        col += 1
                                    continue
                                j += 1
                                col += 1
                            continue
                    elif ch == "'":
                        closed = True
                        i += 1
                        break
                    i += 1
                if not closed:
                    return False, f"Unclosed string literal (') starting at line {s_line}:{s_col}", s_line, s_col
                continue

        # Delimiters
        if c in ('(', '[', '{'):
            stack.append((c, line, col))
        elif c == ')':
            if not stack or stack[-1][0] != '(':
                return False, f"Unexpected closing parenthesis ')' at line {line}:{col}", line, col
            stack.pop()
        elif c == ']':
            if not stack or stack[-1][0] != '[':
                return False, f"Unexpected closing bracket ']' at line {line}:{col}", line, col
            stack.pop()
        elif c == '}':
            if not stack or stack[-1][0] != '{':
                return False, f"Unexpected closing brace '}}' at line {line}:{col}", line, col
            stack.pop()

        i += 1

    if stack:
        if all(x[0] == '{' for x in stack):
            return True, "Valid NSS Syntax", 0, 0
        open_c, o_l, o_c = stack[-1]
        matching = {'(': ')', '[': ']', '{': '}'}
        return False, f"Unclosed '{open_c}' at line {o_l}:{o_c} (expected '{matching.get(open_c)}')", o_l, o_c

    return True, "Valid NSS Syntax", 0, 0


def auto_fix_nss_code(code):
    """Repairs unclosed strings, unbalanced delimiters, duplicated quotes, and trailing syntax errors."""
    if not code:
        return code

    # 1. Fix repeated/malformed quotes
    code = re.sub(r"=''([^']+)''", r"='\1'", code)
    code = re.sub(r'=""([^"]+)""', r'="\1"', code)
    code = re.sub(r'(\b(?:menu|pos|title|find|image|icon)\s*=\s*)\(\s*(["\'][^"\']*["\'])\s*\)', r'\1\2)', code)

    # 2. Line-by-line unclosed quote and parameter healing
    lines = code.splitlines()
    fixed_lines = []

    keywords = r'\b(?:cmd|arg|args|tip|image|icon|vis|pos|type|key|keys|where|mode|admin|window|dir|wait|find|font|color|expanded|id|level|sep)\s*='

    for line in lines:
        in_quote = False
        quote_char = None
        chars = list(line)
        i = 0
        while i < len(chars):
            c = chars[i]
            if c in ('"', "'", '`'):
                if not in_quote:
                    in_quote = True
                    quote_char = c
                elif c == quote_char:
                    if quote_char == '"':
                        bs = 0
                        j = i - 1
                        while j >= 0 and chars[j] == '\\':
                            bs += 1
                            j -= 1
                        if bs % 2 == 0:
                            in_quote = False
                            quote_char = None
                    else:
                        in_quote = False
                        quote_char = None
            elif in_quote and c in (' ', '\t', ','):
                rem = ''.join(chars[i:])
                if re.match(r'[\s,]+' + keywords, rem):
                    chars.insert(i, quote_char)
                    in_quote = False
                    quote_char = None
                    i += 1
            elif in_quote and c == ')':
                rem = ''.join(chars[i:])
                if rem.strip().startswith((')', ') {', '){')):
                    chars.insert(i, quote_char)
                    in_quote = False
                    quote_char = None
                    i += 1
            i += 1

        if in_quote:
            rem = ''.join(chars).rstrip()
            if rem.endswith(')'):
                chars.insert(len(rem) - 1, quote_char)
            elif rem.endswith('}'):
                chars.insert(len(rem) - 1, quote_char)
            else:
                chars.append(quote_char)

        fixed_line = ''.join(chars)

        # Fix single-line command missing closing parentheses or brackets
        if re.search(r'^\s*(?:item|separator|modify)\b', fixed_line):
            if fixed_line.count('(') > fixed_line.count(')'):
                fixed_line += ')' * (fixed_line.count('(') - fixed_line.count(')'))
            if fixed_line.count('[') > fixed_line.count(']'):
                if fixed_line.endswith(')'):
                    fixed_line = fixed_line[:-1] + ']' + ')'
                else:
                    fixed_line += ']'

        fixed_lines.append(fixed_line)

    result = '\n'.join(fixed_lines)

    # 3. Overall block brace balancing for menus
    if result.count('{') > result.count('}'):
        result += ('\n}' * (result.count('{') - result.count('}')))

    return result


def build_hierarchy_from_elements(raw_items, full_code):
    """Builds nested hierarchy of elements matching items.json schema."""
    root_elements = []
    menu_stack = []

    for it in raw_items:
        it_type = it.get('type', 'item').lower()
        props = it.get('props', {})
        start = it.get('start', 0)
        end = it.get('end', 0)
        header_end = it.get('header_end', end)

        if it_type == 'menu':
            element_code = full_code[start:header_end].strip()
        else:
            element_code = full_code[start:end].strip()
        clean_elem_code = strip_nss_comments(element_code)

        title = clean_title(props.get('title'))
        if not title:
            if it_type == 'separator':
                title = "Separator"
            elif it_type == 'modify':
                find_str = clean_prop(props.get('find'))
                title = f"Modify: {find_str}" if find_str else "Modify Rule"
            else:
                title = "Item"

        icon = clean_prop(props.get('image')) or clean_prop(props.get('icon'))

        element_node = {
            "id": f"elem_{start}_{end}",
            "type": it_type,
            "title": title,
            "icon": icon,
            "tip": clean_prop(props.get('tip')),
            "cmd": clean_prop(props.get('cmd')),
            "args": clean_prop(props.get('args')),
            "key": clean_prop(props.get('keys')) or clean_prop(props.get('key')),
            "raw_code": clean_elem_code,
            "children": []
        }

        while menu_stack and start >= menu_stack[-1]['end']:
            menu_stack.pop()

        if menu_stack:
            menu_stack[-1]['node']['children'].append(element_node)
        else:
            root_elements.append(element_node)

        if it_type == 'menu':
            menu_stack.append({'end': end, 'node': element_node})

    return root_elements


class LineNumberArea(QWidget):
    """Uncopyable line numbers gutter for CodeEditor."""
    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor
        self.setCursor(Qt.ArrowCursor)

    def sizeHint(self):
        return QSize(self.editor.line_number_area_width(), 0)

    def paintEvent(self, event):
        self.editor.line_number_area_paint_event(event)


class CodeEditor(QPlainTextEdit):
    """Monospace code editor with VS Code style uncopyable line numbers gutter."""
    cursor_line_changed = pyqtSignal(int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("codeEditor")
        self.setFont(QFont("Cascadia Code", 10))
        self.setLineWrapMode(QPlainTextEdit.NoWrap)

        self.line_number_area = LineNumberArea(self)

        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.cursorPositionChanged.connect(self._on_cursor_changed)

        self.update_line_number_area_width(0)
        self._highlight_current_line()

    def line_number_area_width(self):
        digits = 1
        max_num = max(1, self.blockCount())
        while max_num >= 10:
            max_num //= 10
            digits += 1
        space = 16 + self.fontMetrics().horizontalAdvance('9') * max(2, digits)
        return space

    def update_line_number_area_width(self, _):
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def update_line_number_area(self, rect, dy):
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(0, rect.y(), self.line_number_area.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.line_number_area.setGeometry(cr.left(), cr.top(), self.line_number_area_width(), cr.height())

    def _on_cursor_changed(self):
        self._highlight_current_line()
        cursor = self.textCursor()
        line = cursor.blockNumber() + 1
        col = cursor.columnNumber() + 1
        self.cursor_line_changed.emit(line, col)

    def _highlight_current_line(self):
        extra_selections = []
        if not self.isReadOnly():
            selection = QTextEdit.ExtraSelection()
            line_color = QColor(255, 255, 255, 8)
            selection.format.setBackground(line_color)
            selection.format.setProperty(QTextFormat.FullWidthSelection, True)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            extra_selections.append(selection)
        self.setExtraSelections(extra_selections)

    def line_number_area_paint_event(self, event):
        painter = QPainter(self.line_number_area)
        painter.fillRect(event.rect(), QColor("#141418"))

        # Gutter right border
        painter.setPen(QPen(QColor("rgba(255, 255, 255, 0.08)"), 1))
        painter.drawLine(event.rect().right(), event.rect().top(), event.rect().right(), event.rect().bottom())

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = int(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + int(self.blockBoundingRect(block).height())

        current_line = self.textCursor().blockNumber()

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                if block_number == current_line:
                    painter.setPen(QColor("#e78284"))
                    f = painter.font()
                    f.setBold(True)
                    painter.setFont(f)
                else:
                    painter.setPen(QColor("#5c6370"))
                    f = painter.font()
                    f.setBold(False)
                    painter.setFont(f)

                painter.drawText(0, top, self.line_number_area.width() - 8, self.fontMetrics().height(),
                                 Qt.AlignRight, number)
            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())
            block_number += 1

    def go_to_line(self, line_number, column=1):
        """Moves cursor to specific line and column, highlighting the line."""
        if line_number < 1:
            line_number = 1
        block = self.document().findBlockByNumber(line_number - 1)
        if block.isValid():
            cursor = self.textCursor()
            cursor.setPosition(block.position() + max(0, column - 1))
            self.setTextCursor(cursor)
            self.centerCursor()
            self.setFocus()


class ShellTestAllReportDialog(QDialog):
    """Rich interactive modal report for Shell Test All diagnostics."""
    jump_requested = pyqtSignal(str, int, int)      # snippet_id, rel_line, col
    retest_requested = pyqtSignal()
    autofix_requested = pyqtSignal(list)            # list of snippet objects to autofix

    def __init__(self, parent=None, report_data=None):
        super().__init__(parent)
        self.setWindowTitle("iMA Menu — Shell & Syntax Diagnostic Report")
        self.resize(960, 620)
        self.setMinimumSize(820, 500)

        self.report_data = report_data or {}
        self.entries = self.report_data.get("entries", [])
        self._filtered_entries = list(self.entries)

        self._setup_ui()
        self._populate_tree()

    def _setup_ui(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #141416;
                color: #c6d0f5;
                font-family: 'Google Sans', 'Marhey', 'Segoe UI', system-ui, sans-serif;
            }
            QLabel {
                color: #c6d0f5;
            }
            QLineEdit, QComboBox {
                background-color: #1a1b20;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 6px;
                color: #c6d0f5;
                padding: 6px 10px;
                font-size: 11px;
            }
            QLineEdit:focus, QComboBox:focus {
                border-color: #e78284;
            }
            QTreeWidget {
                background-color: #16171b;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 8px;
                color: #c6d0f5;
                font-size: 11px;
                outline: none;
            }
            QTreeWidget::item {
                padding: 5px 4px;
                border-bottom: 1px solid rgba(255, 255, 255, 0.03);
            }
            QTreeWidget::item:selected {
                background-color: #262833;
                color: #ffffff;
            }
            QTreeWidget::item:hover:!selected {
                background-color: rgba(255, 255, 255, 0.03);
            }
            QHeaderView::section {
                background-color: #1c1d22;
                color: #8c92a4;
                font-weight: bold;
                font-size: 11px;
                border: none;
                border-bottom: 1px solid rgba(255, 255, 255, 0.1);
                padding: 6px 8px;
            }
            QPushButton#primaryBtn {
                background-color: #e78284;
                color: #141416;
                border: none;
                border-radius: 6px;
                padding: 6px 14px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton#primaryBtn:hover {
                background-color: #ea999c;
            }
            QPushButton#secondaryBtn {
                background-color: rgba(255, 255, 255, 0.06);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 6px;
                color: #c6d0f5;
                padding: 6px 12px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton#secondaryBtn:hover {
                background-color: rgba(255, 255, 255, 0.1);
                border-color: rgba(255, 255, 255, 0.2);
            }
            QPushButton#autofixBtn {
                background-color: rgba(166, 209, 137, 0.15);
                border: 1px solid #a6d189;
                border-radius: 6px;
                color: #a6d189;
                padding: 6px 12px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton#autofixBtn:hover {
                background-color: #a6d189;
                color: #141416;
            }
            QPushButton#shellTestBtn {
                background-color: rgba(202, 158, 230, 0.15);
                border: 1px solid #ca9ee6;
                border-radius: 6px;
                color: #ca9ee6;
                padding: 6px 12px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton#shellTestBtn:hover {
                background-color: #ca9ee6;
                color: #141416;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        # Header Title and Summary Badges
        top_box = QHBoxLayout()
        top_box.setSpacing(12)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        title_lbl = QLabel("🚀 Nilesoft Shell — Comprehensive Diagnostic Report")
        title_lbl.setStyleSheet("font-size: 15px; font-weight: bold; color: #c6d0f5;")
        title_col.addWidget(title_lbl)

        sub_lbl = QLabel("Real-time results from Nilesoft Shell C++ engine (shell.log) and NSS Syntax Inspector.")
        sub_lbl.setStyleSheet("font-size: 11px; color: #8c92a4;")
        title_col.addWidget(sub_lbl)
        top_box.addLayout(title_col, 1)

        # Stat Chips
        tot_cnt = self.report_data.get("total_snippets", 0)
        err_cnt = self.report_data.get("errors_count", 0)
        warn_cnt = self.report_data.get("warnings_count", 0)
        clean_cnt = self.report_data.get("clean_count", 0)

        chips_lay = QHBoxLayout()
        chips_lay.setSpacing(6)

        def make_chip(text, bg, fg, border):
            lbl = QLabel(text)
            lbl.setStyleSheet(f"background: {bg}; color: {fg}; border: 1px solid {border}; border-radius: 12px; padding: 3px 10px; font-size: 10px; font-weight: bold;")
            return lbl

        chips_lay.addWidget(make_chip(f"Total: {tot_cnt}", "rgba(255,255,255,0.06)", "#c6d0f5", "rgba(255,255,255,0.12)"))
        if err_cnt > 0:
            chips_lay.addWidget(make_chip(f"✕ Errors: {err_cnt}", "rgba(231,130,132,0.18)", "#e78284", "#e78284"))
        else:
            chips_lay.addWidget(make_chip("✓ Errors: 0", "rgba(166,209,137,0.15)", "#a6d189", "#a6d189"))

        if warn_cnt > 0:
            chips_lay.addWidget(make_chip(f"⚠️ Warnings: {warn_cnt}", "rgba(229,200,144,0.18)", "#e5c890", "#e5c890"))

        chips_lay.addWidget(make_chip(f"✓ Clean: {clean_cnt}", "rgba(166,209,137,0.15)", "#a6d189", "#a6d189"))
        top_box.addLayout(chips_lay)
        layout.addLayout(top_box)

        # Filter and Search Row
        filter_box = QHBoxLayout()
        filter_box.setSpacing(8)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Filter by filename, snippet name, line number, or error message...")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(self._apply_filter)
        filter_box.addWidget(self.search_input, 1)

        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["All Diagnostics", f"Errors Only ({err_cnt})", f"Warnings Only ({warn_cnt})", f"Clean Items ({clean_cnt})"])
        if err_cnt > 0:
            self.filter_combo.setCurrentIndex(1)  # Default to errors when present
        self.filter_combo.currentIndexChanged.connect(self._apply_filter)
        filter_box.addWidget(self.filter_combo)

        layout.addLayout(filter_box)

        # Tree Widget
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Level", "File", "Snippet / Target", "Line : Col", "Diagnostic Message"])
        self.tree.setRootIsDecorated(False)
        self.tree.setSortingEnabled(True)
        self.tree.header().resizeSection(0, 95)
        self.tree.header().resizeSection(1, 190)
        self.tree.header().resizeSection(2, 210)
        self.tree.header().resizeSection(3, 110)
        self.tree.header().setSectionResizeMode(4, QHeaderView.Stretch)
        self.tree.itemSelectionChanged.connect(self._on_tree_selection_changed)
        self.tree.itemDoubleClicked.connect(self._on_tree_double_clicked)
        layout.addWidget(self.tree, 1)

        # Code Preview Frame
        self.preview_frame = QFrame()
        self.preview_frame.setStyleSheet("background-color: #18191e; border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 8px;")
        pv_lay = QVBoxLayout(self.preview_frame)
        pv_lay.setContentsMargins(10, 8, 10, 8)
        pv_lay.setSpacing(4)

        pv_hdr = QHBoxLayout()
        self.preview_meta_lbl = QLabel("Code Inspection at Error Line:")
        self.preview_meta_lbl.setStyleSheet("font-size: 11px; font-weight: bold; color: #ca9ee6;")
        pv_hdr.addWidget(self.preview_meta_lbl, 1)

        self.source_badge_lbl = QLabel("")
        self.source_badge_lbl.setStyleSheet("font-size: 10px; color: #8c92a4;")
        pv_hdr.addWidget(self.source_badge_lbl)
        pv_lay.addLayout(pv_hdr)

        self.preview_edit = QPlainTextEdit()
        self.preview_edit.setReadOnly(True)
        self.preview_edit.setFont(QFont("Cascadia Code", 9))
        self.preview_edit.setFixedHeight(65)
        self.preview_edit.setStyleSheet("background-color: #141416; border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 4px; color: #e78284;")
        pv_lay.addWidget(self.preview_edit)
        layout.addWidget(self.preview_frame)

        # Bottom Action Bar
        bottom_bar = QHBoxLayout()
        bottom_bar.setSpacing(8)

        self.jump_btn = QPushButton("🔍 Jump to Snippet & Line")
        self.jump_btn.setObjectName("primaryBtn")
        self.jump_btn.setToolTip("Open this snippet in the editor and place cursor on the exact error line")
        self.jump_btn.clicked.connect(self._on_jump)
        bottom_bar.addWidget(self.jump_btn)

        self.fix_sel_btn = QPushButton("🩹 Auto-Fix Item")
        self.fix_sel_btn.setObjectName("autofixBtn")
        self.fix_sel_btn.setToolTip("Attempt automatic syntax repair on the selected snippet")
        self.fix_sel_btn.clicked.connect(self._on_fix_selected)
        bottom_bar.addWidget(self.fix_sel_btn)

        self.fix_all_btn = QPushButton("🩹 Auto-Fix All Broken")
        self.fix_all_btn.setObjectName("autofixBtn")
        self.fix_all_btn.setToolTip("Attempt automatic syntax repair across all broken snippets")
        self.fix_all_btn.clicked.connect(self._on_fix_all)
        bottom_bar.addWidget(self.fix_all_btn)

        self.retest_btn = QPushButton("🚀 Re-Test in Shell")
        self.retest_btn.setObjectName("shellTestBtn")
        self.retest_btn.setToolTip("Re-run shell testing to verify syntax fixes")
        self.retest_btn.clicked.connect(self._on_retest)
        bottom_bar.addWidget(self.retest_btn)

        bottom_bar.addStretch(1)

        self.copy_btn = QPushButton("📋 Copy Report")
        self.copy_btn.setObjectName("secondaryBtn")
        self.copy_btn.setToolTip("Copy diagnostic results formatted as Markdown to clipboard")
        self.copy_btn.clicked.connect(self._on_copy_report)
        bottom_bar.addWidget(self.copy_btn)

        self.close_btn = QPushButton("Close")
        self.close_btn.setObjectName("secondaryBtn")
        self.close_btn.clicked.connect(self.accept)
        bottom_bar.addWidget(self.close_btn)

        layout.addLayout(bottom_bar)

    def _populate_tree(self):
        self.tree.clear()
        for ent in self._filtered_entries:
            lvl = ent.get("level", "ok").lower()
            if lvl == "error":
                lvl_str = "✕ ERROR"
                lvl_color = QColor("#e78284")
            elif lvl == "warning":
                lvl_str = "⚠️ WARNING"
                lvl_color = QColor("#e5c890")
            else:
                lvl_str = "✓ PASS"
                lvl_color = QColor("#a6d189")

            file_str = ent.get("source_file") or ent.get("file", "items.nss")
            snip_name = ent.get("snippet_name") or "System Config"
            rel_l = ent.get("rel_line", 1)
            col = ent.get("column", 1)
            abs_l = ent.get("abs_line", rel_l)
            line_str = f"Line {rel_l}:{col}"
            if abs_l != rel_l:
                line_str += f" ({abs_l})"

            msg = ent.get("message", "")

            item = QTreeWidgetItem([lvl_str, file_str, snip_name, line_str, msg])
            item.setForeground(0, lvl_color)
            if lvl == "error":
                item.setForeground(4, QColor("#e78284"))
            elif lvl == "warning":
                item.setForeground(4, QColor("#e5c890"))
            else:
                item.setForeground(4, QColor("#8c92a4"))

            item.setData(0, Qt.UserRole, ent)
            self.tree.addTopLevelItem(item)

        if self.tree.topLevelItemCount() > 0:
            self.tree.setCurrentItem(self.tree.topLevelItem(0))
        else:
            self.preview_edit.setPlainText("(No items match current filter)")
            self.preview_meta_lbl.setText("Code Inspection:")

    def _apply_filter(self):
        query = self.search_input.text().strip().lower()
        filter_idx = self.filter_combo.currentIndex()

        filtered = []
        for ent in self.entries:
            lvl = ent.get("level", "ok").lower()
            if filter_idx == 1 and lvl != "error":
                continue
            elif filter_idx == 2 and lvl != "warning":
                continue
            elif filter_idx == 3 and lvl != "ok":
                continue

            if query:
                haystack = f"{ent.get('file', '')} {ent.get('source_file', '')} {ent.get('snippet_name', '')} {ent.get('message', '')} {ent.get('rel_line', '')}".lower()
                if query not in haystack:
                    continue

            filtered.append(ent)

        self._filtered_entries = filtered
        self._populate_tree()

    def _on_tree_selection_changed(self):
        curr = self.tree.currentItem()
        if not curr:
            return
        ent = curr.data(0, Qt.UserRole)
        if not ent:
            return

        code = ent.get("code_snippet", "").strip()
        rel_l = ent.get("rel_line", 1)
        col = ent.get("column", 1)
        src = ent.get("source", "shell.log")
        file_path = ent.get("source_file") or ent.get("file", "")

        self.preview_meta_lbl.setText(f"Line {rel_l}:{col} in {file_path}")
        self.source_badge_lbl.setText(f"Detected via: {src}")

        if code:
            self.preview_edit.setPlainText(f"{rel_l} |  {code}")
        else:
            self.preview_edit.setPlainText(f"(No code preview available)")

    def _on_tree_double_clicked(self, item, column):
        self._on_jump()

    def _on_jump(self):
        curr = self.tree.currentItem()
        if not curr:
            return
        ent = curr.data(0, Qt.UserRole)
        if not ent:
            return
        sid = ent.get("snippet_id")
        rel_l = ent.get("rel_line", 1)
        col = ent.get("column", 1)
        if sid:
            self.jump_requested.emit(sid, rel_l, col)
            self.accept()
        else:
            QMessageBox.information(
                self, "External File",
                f"This error is in an external shell file:\n\nFile: {ent.get('source_file')}\nLine: {rel_l}, Column: {col}\n\nMessage: {ent.get('message')}"
            )

    def _on_fix_selected(self):
        curr = self.tree.currentItem()
        if not curr:
            return
        ent = curr.data(0, Qt.UserRole)
        if not ent:
            return
        snip = ent.get("snippet")
        if snip:
            self.autofix_requested.emit([snip])
            ent["level"] = "ok"
            ent["message"] = "Auto-fix applied (Ready to re-test in shell)"
            curr.setText(0, "✓ FIXED")
            curr.setForeground(0, QColor("#a6d189"))
            curr.setText(4, ent["message"])
            curr.setForeground(4, QColor("#a6d189"))
        else:
            QMessageBox.information(self, "External File", "Auto-fix from this dialog only applies to catalog snippets.")

    def _on_fix_all(self):
        broken = []
        for ent in self.entries:
            if ent.get("level") == "error" and ent.get("snippet"):
                broken.append(ent.get("snippet"))
        if not broken:
            QMessageBox.information(self, "No Broken Snippets", "No catalog snippets currently have syntax errors to auto-fix.")
            return
        self.autofix_requested.emit(broken)
        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            ent = item.data(0, Qt.UserRole)
            if ent and ent.get("snippet") in broken:
                ent["level"] = "ok"
                ent["message"] = "Auto-fix applied (Ready to re-test in shell)"
                item.setText(0, "✓ FIXED")
                item.setForeground(0, QColor("#a6d189"))
                item.setText(4, ent["message"])
                item.setForeground(4, QColor("#a6d189"))

    def _on_retest(self):
        self.accept()
        self.retest_requested.emit()

    def _on_copy_report(self):
        lines = [
            "# iMA Menu — Shell & Syntax Diagnostic Report",
            f"Total Snippets Scanned: {self.report_data.get('total_snippets', 0)}",
            f"Errors: {self.report_data.get('errors_count', 0)} | Warnings: {self.report_data.get('warnings_count', 0)} | Clean: {self.report_data.get('clean_count', 0)}",
            "",
            "## Diagnostic Findings",
            "| Level | File | Snippet / Target | Line:Col | Message |",
            "|---|---|---|---|---|"
        ]
        for ent in self.entries:
            lvl = ent.get("level", "ok").upper()
            fn = ent.get("source_file") or ent.get("file", "")
            target = ent.get("snippet_name", "")
            pos = f"{ent.get('rel_line', 1)}:{ent.get('column', 1)}"
            msg = ent.get("message", "").replace("|", "/")
            lines.append(f"| {lvl} | {fn} | {target} | {pos} | {msg} |")

        text = "\n".join(lines)
        QApplication.clipboard().setText(text)
        QMessageBox.information(self, "Report Copied", "Full diagnostic report copied to clipboard in Markdown format.")


class ItemsEditorWindow(QMainWindow):
    """Standalone developer editor for iMA Menu items catalog and live NSS AST parsing."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("iMA Menu — Items & Snippets Editor")
        self.resize(1320, 860)
        self.setMinimumSize(980, 680)

        self.catalog = {"version": "1.0.0", "total_snippets": 0, "groups": []}
        self.current_snippet = None
        self.current_group_id = None
        self.is_dirty = False

        # Undo slot for auto-fixing
        self._autofix_backup = None
        self._last_err_line = 0
        self._last_err_col = 0

        # Shell test state
        self._shell_test_active = False
        self._shell_test_initial_size = 0

        self._parse_timer = QTimer(self)
        self._parse_timer.setSingleShot(True)
        self._parse_timer.timeout.connect(self._do_live_parse)

        self._setup_style()
        self._setup_ui()
        self.load_catalog()

    def _setup_style(self):
        self.setStyleSheet("""
            QMainWindow, QWidget#centralWidget {
                background-color: #121214;
                color: #c6d0f5;
                font-family: 'Google Sans', 'Marhey', 'Segoe UI Variable Text', 'Segoe UI', sans-serif;
            }
            QFrame#sidePanel, QFrame#editorPanel, QFrame#inspectPanel {
                background-color: #16161a;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 12px;
            }
            QLabel {
                color: #a5adce;
                font-size: 11px;
            }
            QLabel#headerTitle {
                color: #ffffff;
                font-size: 15px;
                font-weight: bold;
                font-family: 'Google Sans', 'Marhey', 'Segoe UI Variable Display', sans-serif;
            }
            QLabel#sectionTitle {
                color: #ffffff;
                font-size: 13px;
                font-weight: bold;
            }
            QLineEdit, QComboBox {
                background-color: #1c1d22;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 8px;
                color: #ffffff;
                padding: 6px 10px;
                font-size: 12px;
                selection-background-color: #e78284;
                selection-color: #121214;
            }
            QLineEdit:focus, QComboBox:focus {
                border: 1px solid #e78284;
            }
            QPlainTextEdit#codeEditor {
                font-family: 'Cascadia Code', 'Consolas', 'Courier New', monospace;
                font-size: 12px;
                line-height: 1.4;
                background-color: #16171b;
                border: 1px solid rgba(255, 255, 255, 0.1);
                color: #ffffff;
            }
            QTreeWidget {
                background-color: #16171b;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 8px;
                color: #c6d0f5;
                font-size: 11px;
            }
            QTreeWidget::item {
                padding: 4px 6px;
                border-bottom: 1px solid rgba(255, 255, 255, 0.03);
            }
            QTreeWidget::item:hover {
                background-color: rgba(255, 255, 255, 0.04);
            }
            QTreeWidget::item:selected {
                background-color: rgba(231, 130, 132, 0.25);
                color: #ffffff;
            }
            QHeaderView::section {
                background-color: #1c1d22;
                color: #8c92a4;
                font-weight: bold;
                font-size: 11px;
                border: none;
                border-bottom: 1px solid rgba(255, 255, 255, 0.1);
                padding: 5px 8px;
            }
            QTabWidget::pane {
                border: 1px solid rgba(255, 255, 255, 0.08);
                background-color: #16171b;
                border-radius: 8px;
            }
            QTabBar::tab {
                background: rgba(255, 255, 255, 0.04);
                color: #8c92a4;
                padding: 6px 14px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                font-size: 11px;
                font-weight: bold;
                margin-right: 4px;
            }
            QTabBar::tab:selected {
                background: #1c1d22;
                color: #e78284;
                border-bottom: 2px solid #e78284;
            }
            QPushButton#primaryBtn {
                background-color: #e78284;
                color: #141416;
                border: none;
                border-radius: 8px;
                padding: 6px 14px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton#primaryBtn:hover {
                background-color: #ea999c;
            }
            QPushButton#secondaryBtn {
                background-color: rgba(255, 255, 255, 0.06);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 8px;
                color: #c6d0f5;
                padding: 6px 12px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton#secondaryBtn:hover {
                background-color: rgba(255, 255, 255, 0.1);
                border-color: rgba(255, 255, 255, 0.2);
            }
            QPushButton#autofixBtn {
                background-color: rgba(166, 209, 137, 0.15);
                border: 1px solid #a6d189;
                border-radius: 8px;
                color: #a6d189;
                padding: 6px 12px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton#autofixBtn:hover {
                background-color: #a6d189;
                color: #141416;
            }
            QPushButton#shellTestBtn {
                background-color: rgba(202, 158, 230, 0.15);
                border: 1px solid #ca9ee6;
                border-radius: 8px;
                color: #ca9ee6;
                padding: 6px 12px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton#shellTestBtn:hover {
                background-color: #ca9ee6;
                color: #141416;
            }
            QPushButton#dangerBtn {
                background-color: rgba(231, 130, 132, 0.15);
                border: 1px solid rgba(231, 130, 132, 0.3);
                border-radius: 8px;
                color: #e78284;
                padding: 6px 12px;
                font-size: 11px;
            }
            QPushButton#dangerBtn:hover {
                background-color: #e78284;
                color: #141416;
            }
            QSplitter::handle {
                background-color: rgba(255, 255, 255, 0.05);
            }
        """)

    def _setup_ui(self):
        central = QWidget()
        central.setObjectName("centralWidget")
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(14, 12, 14, 12)
        main_layout.setSpacing(10)

        # Top App Header
        header = QHBoxLayout()
        header.setSpacing(10)

        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        app_title = QLabel("iMA Menu — Items & Snippets Catalog Editor")
        app_title.setObjectName("headerTitle")
        title_box.addWidget(app_title)

        self.catalog_stat_lbl = QLabel("Loading catalog...")
        self.catalog_stat_lbl.setStyleSheet("color: #737994; font-size: 10px;")
        title_box.addWidget(self.catalog_stat_lbl)
        header.addLayout(title_box, 1)

        # Top Right Actions
        self.reload_btn = QPushButton("↺ Reload")
        self.reload_btn.setObjectName("secondaryBtn")
        self.reload_btn.clicked.connect(self.load_catalog)
        header.addWidget(self.reload_btn)

        self.import_btn = QPushButton("📁 Import .nss")
        self.import_btn.setObjectName("secondaryBtn")
        self.import_btn.clicked.connect(self._on_import_file)
        header.addWidget(self.import_btn)

        self.autofix_all_btn = QPushButton("🩹 Auto-Fix All Items")
        self.autofix_all_btn.setObjectName("autofixBtn")
        self.autofix_all_btn.setToolTip("Scan every single snippet in items.json and auto-heal all syntax errors")
        self.autofix_all_btn.clicked.connect(self._on_autofix_all_snippets)
        header.addWidget(self.autofix_all_btn)

        self.test_all_btn = QPushButton("🚀 Test All in Shell")
        self.test_all_btn.setObjectName("shellTestBtn")
        self.test_all_btn.setToolTip("Test all snippets in shell and identify file and line of any error in shell.log")
        self.test_all_btn.clicked.connect(self._on_test_all_in_shell)
        header.addWidget(self.test_all_btn)

        self.save_all_btn = QPushButton("💾 Save items.json")
        self.save_all_btn.setObjectName("primaryBtn")
        self.save_all_btn.clicked.connect(self.save_catalog)
        header.addWidget(self.save_all_btn)

        main_layout.addLayout(header)

        # Splitter Layout (Left: Catalog | Center: Editor | Right: Inspector)
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(4)

        # ---------------- 1. Left Catalog Explorer ----------------
        side_panel = QFrame()
        side_panel.setObjectName("sidePanel")
        side_lay = QVBoxLayout(side_panel)
        side_lay.setContentsMargins(10, 10, 10, 10)
        side_lay.setSpacing(8)

        side_title = QLabel("SNIPPETS CATALOG")
        side_title.setObjectName("sectionTitle")
        side_lay.addWidget(side_title)

        # Search Bar
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search snippets (name, id, cmd)...")
        self.search_input.textChanged.connect(self._filter_snippets)
        side_lay.addWidget(self.search_input)

        # Category Filter
        self.cat_filter_combo = QComboBox()
        self.cat_filter_combo.addItem("All Categories", "all")
        self.cat_filter_combo.currentIndexChanged.connect(self._filter_snippets)
        side_lay.addWidget(self.cat_filter_combo)

        # Snippets Tree / List
        self.snippets_tree = QTreeWidget()
        self.snippets_tree.setHeaderLabels(["Snippet / Category", "Count"])
        self.snippets_tree.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.snippets_tree.header().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.snippets_tree.setSelectionMode(QAbstractItemView.SingleSelection)
        self.snippets_tree.currentItemChanged.connect(self._on_snippet_selected)
        self.snippets_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.snippets_tree.customContextMenuRequested.connect(self._on_tree_context_menu)
        side_lay.addWidget(self.snippets_tree, 1)

        # Bottom Side Panel Actions
        side_btn_lay = QHBoxLayout()
        side_btn_lay.setSpacing(4)

        self.add_snippet_btn = QPushButton("+ Snippet")
        self.add_snippet_btn.setObjectName("secondaryBtn")
        self.add_snippet_btn.setToolTip("Add a new snippet to the selected category")
        self.add_snippet_btn.clicked.connect(self._on_new_snippet)
        side_btn_lay.addWidget(self.add_snippet_btn)

        self.add_cat_btn = QPushButton("+ Category")
        self.add_cat_btn.setObjectName("secondaryBtn")
        self.add_cat_btn.setToolTip("Add a new category to the catalog")
        self.add_cat_btn.clicked.connect(self._on_add_category)
        side_btn_lay.addWidget(self.add_cat_btn)

        self.del_snippet_btn = QPushButton("Delete")
        self.del_snippet_btn.setObjectName("dangerBtn")
        self.del_snippet_btn.setToolTip("Delete selected snippet or category")
        self.del_snippet_btn.clicked.connect(self._on_delete_clicked)
        side_btn_lay.addWidget(self.del_snippet_btn)

        side_lay.addLayout(side_btn_lay)
        splitter.addWidget(side_panel)

        # ---------------- 2. Center Workspace (Editor) ----------------
        editor_panel = QFrame()
        editor_panel.setObjectName("editorPanel")
        editor_lay = QVBoxLayout(editor_panel)
        editor_lay.setContentsMargins(12, 12, 12, 12)
        editor_lay.setSpacing(8)

        editor_top_lay = QHBoxLayout()
        editor_title = QLabel("SNIPPET METADATA & NSS CODE")
        editor_title.setObjectName("sectionTitle")
        editor_top_lay.addWidget(editor_title)

        editor_top_lay.addStretch()

        self.cursor_pos_lbl = QLabel("Line 1, Col 1")
        self.cursor_pos_lbl.setStyleSheet("color: #737994; font-size: 10px; margin-right: 6px;")
        editor_top_lay.addWidget(self.cursor_pos_lbl)

        self.clean_code_btn = QPushButton("✨ Clean")
        self.clean_code_btn.setObjectName("secondaryBtn")
        self.clean_code_btn.setToolTip("Strip comments, format code, and normalize iMA Menu branding")
        self.clean_code_btn.clicked.connect(self._on_clean_code)
        editor_top_lay.addWidget(self.clean_code_btn)

        self.auto_meta_btn = QPushButton("⚡ Auto-Detect")
        self.auto_meta_btn.setObjectName("secondaryBtn")
        self.auto_meta_btn.setToolTip("Auto-detect title, icon, and menu from first item/menu statement")
        self.auto_meta_btn.clicked.connect(self._on_auto_detect_metadata)
        editor_top_lay.addWidget(self.auto_meta_btn)

        # Single-item Auto-fix & Revert
        self.autofix_item_btn = QPushButton("🩹 Auto-Fix Item")
        self.autofix_item_btn.setObjectName("autofixBtn")
        self.autofix_item_btn.setToolTip("Attempt to automatically repair unclosed quotes, brackets, and syntax errors")
        self.autofix_item_btn.clicked.connect(self._on_autofix_current_item)
        editor_top_lay.addWidget(self.autofix_item_btn)

        self.revert_autofix_btn = QPushButton("↺ Revert Fix")
        self.revert_autofix_btn.setObjectName("secondaryBtn")
        self.revert_autofix_btn.setEnabled(False)
        self.revert_autofix_btn.setToolTip("Revert code back to before auto-fix was applied")
        self.revert_autofix_btn.clicked.connect(self._on_revert_autofix)
        editor_top_lay.addWidget(self.revert_autofix_btn)

        self.test_shell_btn = QPushButton("🚀 Test in Shell")
        self.test_shell_btn.setObjectName("shellTestBtn")
        self.test_shell_btn.setToolTip("Inject item into imports/items.nss and reload shell to detect shell.log output in real time")
        self.test_shell_btn.clicked.connect(self._on_test_item_in_shell)
        editor_top_lay.addWidget(self.test_shell_btn)

        self.test_all_shell_btn = QPushButton("🚀 Test All in Shell")
        self.test_all_shell_btn.setObjectName("shellTestBtn")
        self.test_all_shell_btn.setToolTip("Test all snippets in catalog and shell configuration, identifying file and line of any error in shell.log")
        self.test_all_shell_btn.clicked.connect(self._on_test_all_in_shell)
        editor_top_lay.addWidget(self.test_all_shell_btn)

        self.delete_test_btn = QPushButton("🗑️ Delete Test Item")
        self.delete_test_btn.setObjectName("secondaryBtn")
        self.delete_test_btn.setToolTip("Quickly delete tested item from imports/items.nss and reload shell")
        self.delete_test_btn.clicked.connect(self._clear_test_item_from_shell)
        editor_top_lay.addWidget(self.delete_test_btn)

        editor_lay.addLayout(editor_top_lay)

        # Form Metadata Grid
        form_grid = QGridLayout()
        form_grid.setHorizontalSpacing(8)
        form_grid.setVerticalSpacing(6)

        # Row 0: ID & Name
        form_grid.addWidget(QLabel("Snippet ID:"), 0, 0)
        self.id_input = QLineEdit()
        self.id_input.setPlaceholderText("e.g. ex1_system_custom_tool")
        form_grid.addWidget(self.id_input, 0, 1)

        form_grid.addWidget(QLabel("Display Name:"), 0, 2)
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g. Custom Tool")
        self.name_input.textChanged.connect(self._on_name_changed)
        form_grid.addWidget(self.name_input, 0, 3)

        # Row 1: Category & Icon
        form_grid.addWidget(QLabel("Category:"), 1, 0)
        self.cat_combo = QComboBox()
        self.cat_combo.setEditable(True)
        form_grid.addWidget(self.cat_combo, 1, 1)

        form_grid.addWidget(QLabel("Icon / Glyph:"), 1, 2)
        icon_box = QHBoxLayout()
        icon_box.setSpacing(6)
        self.icon_input = QLineEdit()
        self.icon_input.setPlaceholderText("e.g. \\uE770, icon.rename, image.res")
        self.icon_input.textChanged.connect(self._update_icon_preview)
        icon_box.addWidget(self.icon_input, 1)

        self.icon_preview_lbl = QLabel()
        self.icon_preview_lbl.setFixedSize(26, 26)
        self.icon_preview_lbl.setAlignment(Qt.AlignCenter)
        self.icon_preview_lbl.setStyleSheet("background: rgba(255,255,255,0.05); border-radius: 13px;")
        icon_box.addWidget(self.icon_preview_lbl)
        form_grid.addLayout(icon_box, 1, 3)

        # Row 2: Menu Name & Description
        form_grid.addWidget(QLabel("Target Menu:"), 2, 0)
        self.menu_name_input = QLineEdit()
        self.menu_name_input.setPlaceholderText("e.g. Tools (or empty for root)")
        form_grid.addWidget(self.menu_name_input, 2, 1)

        form_grid.addWidget(QLabel("Description:"), 2, 2)
        self.desc_input = QLineEdit()
        self.desc_input.setPlaceholderText("Short description (<10 words)")
        form_grid.addWidget(self.desc_input, 2, 3)

        # Row 3: File Path & Version
        form_grid.addWidget(QLabel("NSS File Path:"), 3, 0)
        self.file_path_input = QLineEdit()
        self.file_path_input.setPlaceholderText("e.g. ex1.system/custom.tool.nss")
        form_grid.addWidget(self.file_path_input, 3, 1)

        form_grid.addWidget(QLabel("Version:"), 3, 2)
        self.version_input = QLineEdit("1.0.0")
        form_grid.addWidget(self.version_input, 3, 3)

        editor_lay.addLayout(form_grid)

        # Code Editor Container with Line Numbers Gutter
        editor_lay.addWidget(QLabel("Full Nilesoft Shell (.nss) Code with Line Numbers:"))
        self.code_editor = CodeEditor()
        self.code_editor.setPlaceholderText("Enter or paste Nilesoft Shell NSS statements:\n\nitem(title='My Tool' image=\\uE770 cmd='cmd.exe' args='/c echo Hello')\nmenu(title='Submenu') {\n    item(title='Child' cmd='calc.exe')\n}")
        self.code_editor.textChanged.connect(self._on_code_changed)
        self.code_editor.cursor_line_changed.connect(self._on_cursor_line_changed)
        editor_lay.addWidget(self.code_editor, 1)

        # Save Current Snippet to Memory Button
        bottom_editor_lay = QHBoxLayout()
        self.apply_snippet_btn = QPushButton("✓ Apply Snippet Changes")
        self.apply_snippet_btn.setObjectName("primaryBtn")
        self.apply_snippet_btn.clicked.connect(self._apply_current_snippet)
        bottom_editor_lay.addWidget(self.apply_snippet_btn)

        self.revert_btn = QPushButton("↺ Revert Snippet")
        self.revert_btn.setObjectName("secondaryBtn")
        self.revert_btn.clicked.connect(self._revert_current_snippet)
        bottom_editor_lay.addWidget(self.revert_btn)

        editor_lay.addLayout(bottom_editor_lay)
        splitter.addWidget(editor_panel)

        # ---------------- 3. Right Panel (Nilesoft Shell Parser & Inspector) ----------------
        inspect_panel = QFrame()
        inspect_panel.setObjectName("inspectPanel")
        inspect_lay = QVBoxLayout(inspect_panel)
        inspect_lay.setContentsMargins(12, 12, 12, 12)
        inspect_lay.setSpacing(8)

        inspect_title = QLabel("NILESOFT SHELL AST & STRUCTURE")
        inspect_title.setObjectName("sectionTitle")
        inspect_lay.addWidget(inspect_title)

        # Live Syntax Health Banner (Clickable to jump to error line)
        self.syntax_banner = QFrame()
        self.syntax_banner.setFixedHeight(44)
        self.syntax_banner.setCursor(Qt.PointingHandCursor)
        self.syntax_banner.setStyleSheet("background: rgba(166, 209, 137, 0.15); border: 1px solid #a6d189; border-radius: 8px;")
        sb_lay = QHBoxLayout(self.syntax_banner)
        sb_lay.setContentsMargins(10, 4, 10, 4)

        self.syntax_icon_lbl = QLabel("✓")
        self.syntax_icon_lbl.setStyleSheet("color: #a6d189; font-weight: bold; font-size: 16px;")
        sb_lay.addWidget(self.syntax_icon_lbl)

        self.syntax_text_lbl = QLabel("NSS Syntax: Error-Free Valid")
        self.syntax_text_lbl.setStyleSheet("color: #a6d189; font-weight: bold; font-size: 11px;")
        sb_lay.addWidget(self.syntax_text_lbl, 1)

        self.jump_err_btn = QPushButton("Jump to Error")
        self.jump_err_btn.setObjectName("secondaryBtn")
        self.jump_err_btn.setVisible(False)
        self.jump_err_btn.clicked.connect(self._on_jump_to_error)
        sb_lay.addWidget(self.jump_err_btn)

        self.syntax_banner.mousePressEvent = lambda e: self._on_jump_to_error()
        inspect_lay.addWidget(self.syntax_banner)

        # Real-time Shell Testing Banner / Box
        self.shell_test_box = QFrame()
        self.shell_test_box.setStyleSheet("background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 8px;")
        st_lay = QVBoxLayout(self.shell_test_box)
        st_lay.setContentsMargins(8, 6, 8, 6)
        st_lay.setSpacing(4)

        st_hdr = QHBoxLayout()
        self.shell_test_status_lbl = QLabel("Shell Engine: Idle (Ready to test live context menu)")
        self.shell_test_status_lbl.setStyleSheet("color: #8c92a4; font-size: 10px; font-weight: bold;")
        st_hdr.addWidget(self.shell_test_status_lbl, 1)

        self.shell_test_all_btn = QPushButton("🚀 Test All")
        self.shell_test_all_btn.setObjectName("shellTestBtn")
        self.shell_test_all_btn.setToolTip("Test all snippets in shell and review diagnostics in shell.log")
        self.shell_test_all_btn.clicked.connect(self._on_test_all_in_shell)
        st_hdr.addWidget(self.shell_test_all_btn)

        self.clear_shell_test_btn = QPushButton("🗑️ Delete Test Item")
        self.clear_shell_test_btn.setObjectName("secondaryBtn")
        self.clear_shell_test_btn.setToolTip("Removes injected test code from imports/items.nss and reloads shell")
        self.clear_shell_test_btn.setVisible(True)
        self.clear_shell_test_btn.clicked.connect(self._clear_test_item_from_shell)
        st_hdr.addWidget(self.clear_shell_test_btn)
        st_lay.addLayout(st_hdr)

        self.shell_log_output = QLabel("Click '🚀 Test in Shell' to verify with native shell.dll / shell.log in real time.")
        self.shell_log_output.setWordWrap(True)
        self.shell_log_output.setStyleSheet("color: #737994; font-size: 10px; font-family: 'Cascadia Code', monospace;")
        st_lay.addWidget(self.shell_log_output)
        inspect_lay.addWidget(self.shell_test_box)

        # Tabs for Tree, JSON Preview, and Clean NSS
        self.inspect_tabs = QTabWidget()

        # Tab 1: AST Tree
        tree_widget_container = QWidget()
        twc_lay = QVBoxLayout(tree_widget_container)
        twc_lay.setContentsMargins(4, 4, 4, 4)

        self.ast_tree = QTreeWidget()
        self.ast_tree.setHeaderLabels(["Element", "Command / Details", "Args / Hotkey"])
        self.ast_tree.header().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.ast_tree.header().setSectionResizeMode(1, QHeaderView.Stretch)
        self.ast_tree.header().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        twc_lay.addWidget(self.ast_tree)
        self.inspect_tabs.addTab(tree_widget_container, "Parsed AST Tree")

        # Tab 2: Generated JSON Preview
        json_container = QWidget()
        jc_lay = QVBoxLayout(json_container)
        jc_lay.setContentsMargins(4, 4, 4, 4)
        self.json_preview = QPlainTextEdit()
        self.json_preview.setReadOnly(True)
        self.json_preview.setFont(QFont("Cascadia Code", 10))
        jc_lay.addWidget(self.json_preview)
        self.inspect_tabs.addTab(json_container, "JSON Output")

        # Tab 3: Clean NSS Preview
        clean_nss_container = QWidget()
        cn_lay = QVBoxLayout(clean_nss_container)
        cn_lay.setContentsMargins(4, 4, 4, 4)
        self.clean_nss_preview = QPlainTextEdit()
        self.clean_nss_preview.setReadOnly(True)
        self.clean_nss_preview.setFont(QFont("Cascadia Code", 10))
        cn_lay.addWidget(self.clean_nss_preview)
        self.inspect_tabs.addTab(clean_nss_container, "Pure NSS")

        inspect_lay.addWidget(self.inspect_tabs, 1)

        # Summary statistics label
        self.parse_stats_lbl = QLabel("0 Elements (0 Menus, 0 Items, 0 Separators)")
        self.parse_stats_lbl.setStyleSheet("color: #737994; font-size: 10px;")
        inspect_lay.addWidget(self.parse_stats_lbl)

        splitter.addWidget(inspect_panel)

        # Set Splitter Proportions (25% Side | 45% Editor | 30% Inspector)
        splitter.setStretchFactor(0, 25)
        splitter.setStretchFactor(1, 45)
        splitter.setStretchFactor(2, 30)

        main_layout.addWidget(splitter, 1)

    # ---------------- Data Loading & Persistence ----------------
    def load_catalog(self):
        """Loads cache/items.json and populates the UI."""
        if not os.path.exists(ITEMS_JSON_PATH):
            QMessageBox.warning(self, "Catalog Missing", f"Catalog file not found at:\n{ITEMS_JSON_PATH}")
            self.catalog = {"version": "1.0.0", "total_snippets": 0, "groups": []}
        else:
            try:
                with open(ITEMS_JSON_PATH, "r", encoding="utf-8") as f:
                    self.catalog = json.load(f)
            except Exception as e:
                QMessageBox.critical(self, "Load Error", f"Failed to parse items.json:\n{e}")
                self.catalog = {"version": "1.0.0", "total_snippets": 0, "groups": []}

        # Populate category dropdowns
        self._populate_category_combos()
        self._filter_snippets()

        if self.snippets_tree.topLevelItemCount() > 0:
            first_group_item = self.snippets_tree.topLevelItem(0)
            if first_group_item.childCount() > 0:
                self.snippets_tree.setCurrentItem(first_group_item.child(0))
            else:
                self.snippets_tree.setCurrentItem(first_group_item)

    def _populate_category_combos(self):
        """Refreshes category filter and category selection dropdowns."""
        self.cat_filter_combo.blockSignals(True)
        self.cat_combo.blockSignals(True)

        current_filter_data = self.cat_filter_combo.currentData() or "all"
        current_cat_text = self.cat_combo.currentText()

        self.cat_filter_combo.clear()
        self.cat_filter_combo.addItem("All Categories", "all")
        self.cat_combo.clear()

        groups = self.catalog.get("groups", [])
        total_snips = 0
        for g in groups:
            g_name = g.get("name", "Unknown")
            g_id = g.get("id", g_name.lower())
            count = len(g.get('snippets', []))
            self.cat_filter_combo.addItem(f"{g_name} ({count})", g_id)
            self.cat_combo.addItem(g_name, g_id)
            total_snips += count

        idx = self.cat_filter_combo.findData(current_filter_data)
        if idx != -1:
            self.cat_filter_combo.setCurrentIndex(idx)
        else:
            self.cat_filter_combo.setCurrentIndex(0)

        if current_cat_text:
            idx = self.cat_combo.findText(current_cat_text)
            if idx != -1:
                self.cat_combo.setCurrentIndex(idx)
            else:
                self.cat_combo.setEditText(current_cat_text)

        self.cat_filter_combo.blockSignals(False)
        self.cat_combo.blockSignals(False)

        self.catalog_stat_lbl.setText(f"{total_snips} Snippets across {len(groups)} Categories | {ITEMS_JSON_PATH}")

    def save_catalog(self):
        """Atomically saves catalog to cache/items.json with a backup."""
        if self.current_snippet:
            self._apply_current_snippet(silent=True)

        total = sum(len(g.get("snippets", [])) for g in self.catalog.get("groups", []))
        self.catalog["total_snippets"] = total

        try:
            if os.path.exists(ITEMS_JSON_PATH):
                bak_path = ITEMS_JSON_PATH + ".bak"
                shutil.copyfile(ITEMS_JSON_PATH, bak_path)

            tmp_path = ITEMS_JSON_PATH + ".tmp"
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(self.catalog, f, indent=2, ensure_ascii=False)
            os.replace(tmp_path, ITEMS_JSON_PATH)

            self.is_dirty = False
            self._populate_category_combos()
            self.catalog_stat_lbl.setText(f"✓ Saved! {total} Snippets across {len(self.catalog.get('groups', []))} Categories")
            QMessageBox.information(self, "Catalog Saved", f"Successfully updated {ITEMS_JSON_PATH}\n(Total: {total} snippets, backup created: items.json.bak)")
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save items.json:\n{e}")

    # ---------------- Snippet Selection & Filtering ----------------
    def _filter_snippets(self):
        query = self.search_input.text().strip().lower()
        selected_cat = self.cat_filter_combo.currentData() or "all"

        self.snippets_tree.clear()

        for group in self.catalog.get("groups", []):
            g_id = group.get("id", "")
            g_name = group.get("name", "Unknown")

            if selected_cat != "all" and g_id != selected_cat:
                continue

            matching_snippets = []
            for snip in group.get("snippets", []):
                if query:
                    m = (
                        query in snip.get("name", "").lower() or
                        query in snip.get("id", "").lower() or
                        query in snip.get("description", "").lower() or
                        query in snip.get("full_code", "").lower()
                    )
                    if not m:
                        continue
                matching_snippets.append(snip)

            # Show group if not searching, or if group matches query, or if snippets match
            group_matches_query = bool(query and (query in g_name.lower() or query in g_id.lower()))
            if not query or matching_snippets or group_matches_query:
                snip_count = len(matching_snippets) if query else len(group.get("snippets", []))
                grp_item = QTreeWidgetItem([f"📁 {g_name}", f"{snip_count}"])
                grp_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                grp_item.setData(0, Qt.UserRole, ("category", g_id))
                grp_item.setForeground(0, QColor("#ca9ee6"))
                font = grp_item.font(0)
                font.setBold(True)
                grp_item.setFont(0, font)

                snippets_to_show = matching_snippets if query else group.get("snippets", [])
                if not snippets_to_show:
                    empty_item = QTreeWidgetItem(["  (Empty category)", "0"])
                    empty_item.setFlags(Qt.ItemIsEnabled)
                    empty_item.setForeground(0, QColor("#737994"))
                    grp_item.addChild(empty_item)
                else:
                    for snip in snippets_to_show:
                        is_valid, _, _, _ = validate_nss_syntax_detailed(snip.get("full_code", ""))
                        prefix = "" if is_valid else "⚠️ "
                        s_item = QTreeWidgetItem([f"{prefix}{snip.get('name', 'Unnamed')}", g_name])
                        s_item.setData(0, Qt.UserRole, ("snippet", g_id, snip.get("id")))
                        s_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                        if not is_valid:
                            s_item.setForeground(0, QColor("#e78284"))
                        grp_item.addChild(s_item)

                self.snippets_tree.addTopLevelItem(grp_item)
                grp_item.setExpanded(True)

    def _on_snippet_selected(self, current, previous):
        if not current:
            return
        data = current.data(0, Qt.UserRole)
        if not data or not isinstance(data, (tuple, list)):
            return

        item_type = data[0]
        if item_type == "category":
            g_id = data[1]
            self.selected_category_id = g_id
            self.current_group_id = g_id
            self.current_snippet = None
            self.del_snippet_btn.setText("Delete Category")
            self.del_snippet_btn.setToolTip(f"Permanently delete category '{g_id}' and remove it from items.json")
            self._load_category_into_form(g_id)
        elif item_type == "snippet":
            g_id = data[1]
            s_id = data[2]
            self.selected_category_id = g_id
            self.current_group_id = g_id
            self.del_snippet_btn.setText("Delete Snippet")
            self.del_snippet_btn.setToolTip("Permanently delete this snippet from items.json")
            snip = self._find_snippet(g_id, s_id)
            if snip:
                self.current_snippet = snip
                self._autofix_backup = None
                self.revert_autofix_btn.setEnabled(False)
                self._load_snippet_into_form(snip)

    def _find_snippet(self, g_id, s_id):
        for g in self.catalog.get("groups", []):
            if g.get("id") == g_id:
                for s in g.get("snippets", []):
                    if s.get("id") == s_id:
                        return s
        for g in self.catalog.get("groups", []):
            for s in g.get("snippets", []):
                if s.get("id") == s_id:
                    return s
        return None

    def _load_snippet_into_form(self, snip):
        self.id_input.setText(snip.get("id", ""))
        self.name_input.setText(snip.get("name", ""))

        cat_name = snip.get("category", "")
        idx = self.cat_combo.findText(cat_name)
        if idx != -1:
            self.cat_combo.setCurrentIndex(idx)
        else:
            self.cat_combo.setEditText(cat_name)

        self.icon_input.setText(snip.get("icon", ""))
        self.menu_name_input.setText(snip.get("menu_name", ""))
        self.desc_input.setText(snip.get("description", ""))
        self.file_path_input.setText(snip.get("file_path", ""))
        self.version_input.setText(snip.get("version", "1.0.0"))

        self.code_editor.blockSignals(True)
        self.code_editor.setPlainText(snip.get("full_code", ""))
        self.code_editor.blockSignals(False)

        self._update_icon_preview(snip.get("icon", ""))
        self._do_live_parse()

    def _load_category_into_form(self, g_id):
        """Displays category group metadata and snippet inventory in editor and preview."""
        target_group = None
        for g in self.catalog.get("groups", []):
            if g.get("id") == g_id:
                target_group = g
                break
        if not target_group:
            return

        self.id_input.setText(target_group.get("id", ""))
        self.name_input.setText(target_group.get("name", ""))

        cat_name = target_group.get("name", "")
        idx = self.cat_combo.findText(cat_name)
        if idx != -1:
            self.cat_combo.setCurrentIndex(idx)
        else:
            self.cat_combo.setEditText(cat_name)

        self.icon_input.setText(target_group.get("icon", "\\uE71D"))
        self.menu_name_input.setText("")
        self.desc_input.setText(target_group.get("description", ""))
        self.file_path_input.clear()
        self.version_input.setText(target_group.get("version", "1.0.0"))

        snips = target_group.get("snippets", [])
        snip_info = f"// ========================================================\n"
        snip_info += f"// CATEGORY GROUP: {target_group.get('name')} (ID: {g_id})\n"
        snip_info += f"// Total Snippets: {len(snips)}\n"
        snip_info += f"// Description: {target_group.get('description', '')}\n"
        snip_info += f"// ========================================================\n\n"
        if snips:
            snip_info += f"// Contained Snippets ({len(snips)}):\n"
            for s in snips:
                snip_info += f"//   • {s.get('name')} (ID: {s.get('id')})\n"
            snip_info += f"\n// Click any snippet in the left tree to edit its code.\n"
            snip_info += f"// Click '+ Snippet' to add an item into this category.\n"
            snip_info += f"// Click 'Delete Category' to delete this entire category from items.json.\n"
        else:
            snip_info += "// [EMPTY CATEGORY]\n"
            snip_info += "// This category currently has 0 snippets.\n"
            snip_info += "// • You can keep it empty in items.json as a placeholder.\n"
            snip_info += "// • You can click '+ Snippet' to add a snippet to this category.\n"
            snip_info += "// • You can click 'Delete Category' to remove it from items.json.\n"

        self.code_editor.blockSignals(True)
        self.code_editor.setPlainText(snip_info)
        self.code_editor.blockSignals(False)

        self._update_icon_preview(target_group.get("icon", "\\uE71D"))
        self.ast_tree.clear()
        self.clean_nss_preview.setPlainText(snip_info)
        self.json_preview.setPlainText(json.dumps(target_group, indent=2, ensure_ascii=False))

        self.parse_stats_lbl.setText(f"Category Group: {target_group.get('name')} ({len(snips)} Snippets)")
        self.syntax_banner.setStyleSheet("background: rgba(166, 209, 137, 0.15); border: 1px solid #a6d189; border-radius: 8px;")
        self.syntax_icon_lbl.setText("📁")
        self.syntax_text_lbl.setText(f"Category Group: {target_group.get('name')} ({len(snips)} items)")
        self.syntax_text_lbl.setStyleSheet("color: #a6d189; font-weight: bold; font-size: 11px;")
        self.jump_err_btn.setVisible(False)

    # ---------------- Live Parsing & AST Inspection ----------------
    def _on_code_changed(self):
        self._parse_timer.start(150)

    def _on_cursor_line_changed(self, line, col):
        self.cursor_pos_lbl.setText(f"Line {line}, Col {col}")

    def _on_name_changed(self, text):
        if not self.id_input.text() or self.id_input.text().startswith("custom_"):
            slug = re.sub(r'[^a-zA-Z0-9_]', '_', text.strip().lower())
            slug = re.sub(r'_+', '_', slug).strip('_')
            self.id_input.setText(f"custom_{slug}" if slug else "custom_new_item")

    def _update_icon_preview(self, icon_str):
        pixmap = render_nss_asset_pixmap(icon_str, 20)
        if pixmap and not pixmap.isNull():
            self.icon_preview_lbl.setPixmap(pixmap)
        else:
            self.icon_preview_lbl.setPixmap(get_mdl2_icon(0xE71D, 18, "#e78284").pixmap(18, 18))

    def _do_live_parse(self):
        raw_code = self.code_editor.toPlainText()

        # 1. Syntax Validation
        is_valid, msg, err_line, err_col = validate_nss_syntax_detailed(raw_code)
        self._last_err_line = err_line
        self._last_err_col = err_col

        if is_valid:
            self.syntax_banner.setStyleSheet("background: rgba(166, 209, 137, 0.15); border: 1px solid #a6d189; border-radius: 8px;")
            self.syntax_icon_lbl.setText("✓")
            self.syntax_icon_lbl.setStyleSheet("color: #a6d189; font-weight: bold; font-size: 16px;")
            self.syntax_text_lbl.setText("Nilesoft Shell NSS Syntax: Error-Free Valid")
            self.syntax_text_lbl.setStyleSheet("color: #a6d189; font-weight: bold; font-size: 11px;")
            self.jump_err_btn.setVisible(False)
        else:
            self.syntax_banner.setStyleSheet("background: rgba(231, 130, 132, 0.15); border: 1px solid #e78284; border-radius: 8px;")
            self.syntax_icon_lbl.setText("✕")
            self.syntax_icon_lbl.setStyleSheet("color: #e78284; font-weight: bold; font-size: 16px;")
            self.syntax_text_lbl.setText(f"Syntax Error: {msg}")
            self.syntax_text_lbl.setStyleSheet("color: #e78284; font-weight: bold; font-size: 11px;")
            self.jump_err_btn.setVisible(err_line > 0)

        # 2. Extract AST items with nss_parser
        clean_code = strip_nss_comments(raw_code)
        raw_items = find_items_and_menus(raw_code, types=('item', 'menu', 'separator', 'modify'))
        hierarchy = build_hierarchy_from_elements(raw_items, raw_code)

        # 3. Populate AST Tree
        self.ast_tree.clear()
        total_items, total_menus, total_seps, total_mods = 0, 0, 0, 0

        def add_nodes(parent_item, elems):
            nonlocal total_items, total_menus, total_seps, total_mods
            for el in elems:
                el_type = el.get("type", "item").lower()
                title = el.get("title", "")
                cmd = el.get("cmd", "")
                args = el.get("args", "")
                key = el.get("key", "")

                if el_type == "menu":
                    total_menus += 1
                    icon_prefix = "📁 Menu: "
                    col_color = "#ca9ee6"
                elif el_type == "separator":
                    total_seps += 1
                    icon_prefix = "― "
                    col_color = "#737994"
                elif el_type == "modify":
                    total_mods += 1
                    icon_prefix = "✏️ "
                    col_color = "#8caaee"
                else:
                    total_items += 1
                    icon_prefix = "⚙️ "
                    col_color = "#c6d0f5"

                tree_item = QTreeWidgetItem([f"{icon_prefix}{title}", cmd, f"{args} {key}".strip()])
                tree_item.setForeground(0, QColor(col_color))
                tree_item.setToolTip(0, el.get("raw_code", ""))

                if parent_item:
                    parent_item.addChild(tree_item)
                else:
                    self.ast_tree.addTopLevelItem(tree_item)

                if el.get("children"):
                    add_nodes(tree_item, el["children"])
                    tree_item.setExpanded(True)

        add_nodes(None, hierarchy)
        self.ast_tree.expandAll()

        total_elements = total_items + total_menus + total_seps + total_mods
        self.parse_stats_lbl.setText(
            f"{total_elements} Elements ({total_menus} Menus, {total_items} Items, {total_seps} Separators, {total_mods} Modifiers)"
        )

        # 4. Update Clean NSS Preview
        self.clean_nss_preview.setPlainText(clean_code)

        # 5. Update JSON Preview
        preview_snippet = {
            "id": self.id_input.text().strip(),
            "file_path": self.file_path_input.text().strip(),
            "name": self.name_input.text().strip(),
            "category": self.cat_combo.currentText().strip(),
            "category_id": self.cat_combo.currentData() or self._slugify(self.cat_combo.currentText()),
            "icon": self.icon_input.text().strip(),
            "menu_name": self.menu_name_input.text().strip(),
            "description": self.desc_input.text().strip(),
            "version": self.version_input.text().strip() or "1.0.0",
            "full_code": clean_code,
            "elements": hierarchy
        }
        self.json_preview.setPlainText(json.dumps(preview_snippet, indent=2, ensure_ascii=False))

    def _on_jump_to_error(self):
        if self._last_err_line > 0:
            self.code_editor.go_to_line(self._last_err_line, self._last_err_col)

    # ---------------- Auto-Fixing Logic ----------------
    def _on_autofix_current_item(self):
        """Auto-heals the current snippet code with single-click revert support."""
        current_code = self.code_editor.toPlainText()
        if not current_code.strip():
            return

        is_valid, msg, _, _ = validate_nss_syntax_detailed(current_code)
        if is_valid:
            QMessageBox.information(self, "Syntax Valid", "NSS code already has 0 syntax errors.")
            return

        # Save backup for revert
        self._autofix_backup = current_code
        self.revert_autofix_btn.setEnabled(True)

        fixed_code = auto_fix_nss_code(current_code)
        self.code_editor.setPlainText(fixed_code)

        new_valid, new_msg, _, _ = validate_nss_syntax_detailed(fixed_code)
        if new_valid:
            QMessageBox.information(
                self, "Auto-Fix Succeeded",
                "Successfully healed unclosed quotes, brackets, or delimiters!\nSyntax is now 100% valid.\n(Click '↺ Revert Fix' if you want to undo)"
            )
        else:
            QMessageBox.warning(
                self, "Partial Fix",
                f"Auto-fixed common patterns, but some issues remain:\n{new_msg}\nCheck the error line and adjust manually or revert."
            )

    def _on_revert_autofix(self):
        """Restores the code prior to auto-fix."""
        if self._autofix_backup is not None:
            self.code_editor.setPlainText(self._autofix_backup)
            self._autofix_backup = None
            self.revert_autofix_btn.setEnabled(False)
            QMessageBox.information(self, "Reverted", "Restored snippet code to state prior to auto-fix.")

    def _on_autofix_all_snippets(self):
        """Scans and auto-fixes every snippet in items.json all at once."""
        groups = self.catalog.get("groups", [])
        total_scanned = 0
        fixed_count = 0
        still_broken = []

        resp = QMessageBox.question(
            self, "Auto-Fix All Items",
            "This will scan all snippets across all categories in items.json and automatically repair unclosed quotes, brackets, and syntax delimiters.\n\nA backup (.bak) will be created.\n\nDo you want to proceed?",
            QMessageBox.Yes | QMessageBox.No
        )
        if resp != QMessageBox.Yes:
            return

        for g in groups:
            for snip in g.get("snippets", []):
                total_scanned += 1
                code = snip.get("full_code", "")
                is_valid, _, _, _ = validate_nss_syntax_detailed(code)
                if not is_valid:
                    healed = auto_fix_nss_code(code)
                    new_valid, _, _, _ = validate_nss_syntax_detailed(healed)
                    if new_valid:
                        fixed_count += 1
                        snip["full_code"] = strip_nss_comments(healed)
                        raw_items = find_items_and_menus(healed, types=('item', 'menu', 'separator', 'modify'))
                        snip["elements"] = build_hierarchy_from_elements(raw_items, healed)
                    else:
                        still_broken.append(f"• {snip.get('name', 'Item')} ({snip.get('id')})")

        # Refresh UI
        self._filter_snippets()
        if self.current_snippet:
            self._load_snippet_into_form(self.current_snippet)

        report = f"Scan complete!\n• Total snippets scanned: {total_scanned}\n• Repaired & syntax-verified: {fixed_count}"
        if still_broken:
            report += f"\n• Remaining with complex issues ({len(still_broken)}):\n" + "\n".join(still_broken[:10])
            if len(still_broken) > 10:
                report += f"\n...and {len(still_broken) - 10} more."
        else:
            report += "\n• All items in the catalog are now 100% syntax error-free!"

        QMessageBox.information(self, "Bulk Auto-Fix Report", report)

    # ---------------- Live Real-Time Shell Testing ----------------
    def _on_test_item_in_shell(self):
        """Injects current snippet cleanly into imports/items.nss and reloads shell to monitor shell.log."""
        raw_code = self.code_editor.toPlainText().strip()
        if not raw_code:
            QMessageBox.warning(self, "No Code", "Please enter NSS statements to test.")
            return

        root = get_project_root()
        shell_log_path = os.path.join(root, "shell.log")
        items_nss_path = os.path.join(root, "imports", "items.nss")

        os.makedirs(os.path.dirname(items_nss_path), exist_ok=True)

        # 1. Clean any previous test blocks first
        orig_items = ""
        if os.path.exists(items_nss_path):
            with open(items_nss_path, "r", encoding="utf-8", errors="ignore") as f:
                orig_items = f.read()

        cleaned_items = re.sub(r'// -- DEV_TEST_BEGIN --.*?// -- DEV_TEST_END --\n?', '', orig_items, flags=re.DOTALL).strip()
        self._pre_test_items_content = cleaned_items

        # 2. Record shell.log starting offset
        self._shell_test_initial_size = os.path.getsize(shell_log_path) if os.path.exists(shell_log_path) else 0

        # 3. Ensure test payload has balanced braces so it never corrupts items.nss
        test_payload = raw_code.strip()
        open_curlies = test_payload.count('{')
        close_curlies = test_payload.count('}')
        if open_curlies > close_curlies:
            test_payload += ('\n}' * (open_curlies - close_curlies))

        # Calculate exact start line of test item in items.nss
        self._test_item_start_line = (cleaned_items.count('\n') + 1) + 2 if cleaned_items else 2
        self._test_item_end_line = self._test_item_start_line + test_payload.count('\n')

        test_block = f"\n\n// -- DEV_TEST_BEGIN --\n{test_payload}\n// -- DEV_TEST_END --\n"
        new_items = (cleaned_items + test_block).strip() + "\n"

        try:
            with open(items_nss_path, "w", encoding="utf-8") as f:
                f.write(new_items)
        except Exception as e:
            QMessageBox.critical(self, "Write Error", f"Failed to write to imports/items.nss:\n{e}")
            return

        self._shell_test_active = True
        self.clear_shell_test_btn.setVisible(True)
        self.shell_test_status_lbl.setText("Shell Engine: Reloading shell & checking shell.log...")
        self.shell_test_status_lbl.setStyleSheet("color: #e5c890; font-size: 10px; font-weight: bold;")
        self.shell_log_output.setText("Reloading shell.exe and inspecting newly appended logs in shell.log...")

        # 4. Reload shell
        trigger_shell_reload()

        # 5. Check log after 400ms
        QTimer.singleShot(400, self._check_shell_log_results)

    def _check_shell_log_results(self):
        root = get_project_root()
        shell_log_path = os.path.join(root, "shell.log")

        new_log_entries = []
        raw_new_text = ""

        if os.path.exists(shell_log_path):
            try:
                with open(shell_log_path, "r", encoding="utf-8", errors="ignore") as f:
                    current_size = os.path.getsize(shell_log_path)
                    if current_size >= self._shell_test_initial_size:
                        f.seek(self._shell_test_initial_size)
                    raw_new_text = f.read()
                new_log_entries = parse_log_entries(raw_new_text)
            except Exception as e:
                raw_new_text = f"Error reading shell.log: {e}"

        start_l = getattr(self, '_test_item_start_line', 1)
        end_l = getattr(self, '_test_item_end_line', 999999)

        # Specifically isolate errors within the test block range
        test_errors = [e for e in new_log_entries if e.level == 'error' and 'items.nss' in e.filename.lower() and (start_l <= e.line <= end_l)]
        unrelated_items_errors = [e for e in new_log_entries if e.level == 'error' and 'items.nss' in e.filename.lower() and not (start_l <= e.line <= end_l)]
        other_errors = [e for e in new_log_entries if e.level == 'error' and 'items.nss' not in e.filename.lower()]
        test_warnings = [e for e in new_log_entries if e.level == 'warning' and 'items.nss' in e.filename.lower() and (start_l <= e.line <= end_l)]

        if test_errors:
            err = test_errors[0]
            rel_line = max(1, err.line - start_l + 1)
            self.shell_test_status_lbl.setText(f"✕ Shell Error in Tested Item: Line {rel_line} (Absolute {err.line}), Col {err.column}")
            self.shell_test_status_lbl.setStyleSheet("color: #e78284; font-size: 10px; font-weight: bold;")
            self.shell_log_output.setText(f"[{err.level.upper()}] {err.message}\nRaw: {err.raw}\n\nClick '🗑️ Delete Test Item' to remove from shell.")
            self.code_editor.go_to_line(rel_line, err.column)
        elif test_warnings:
            warn = test_warnings[0]
            rel_line = max(1, warn.line - start_l + 1)
            self.shell_test_status_lbl.setText(f"⚠️ Shell Warning in Tested Item: Line {rel_line}")
            self.shell_test_status_lbl.setStyleSheet("color: #e5c890; font-size: 10px; font-weight: bold;")
            self.shell_log_output.setText(f"[WARNING] {warn.message}\nRaw: {warn.raw}\n\nClick '🗑️ Delete Test Item' to remove from shell.")
        else:
            msg = "✓ Shell Engine Verified: Tested Item Loaded Cleanly (0 Errors)!"
            if unrelated_items_errors:
                msg += f" (Note: unrelated error in items.nss line {unrelated_items_errors[0].line})"
            elif other_errors:
                msg += f" (Note: unrelated error in {other_errors[0].filename})"
            self.shell_test_status_lbl.setText(msg)
            self.shell_test_status_lbl.setStyleSheet("color: #a6d189; font-size: 10px; font-weight: bold;")
            self.shell_log_output.setText("Tested item verified error-free by Nilesoft Shell C++ engine in shell.log.\nRight-click on desktop to verify in live context menu!\n\nClick '🗑️ Delete Test Item' when done testing.")

    def _clear_test_item_from_shell(self):
        """Removes the injected test block from imports/items.nss and reloads."""
        root = get_project_root()
        items_nss_path = os.path.join(root, "imports", "items.nss")
        try:
            if hasattr(self, '_pre_test_items_content') and self._pre_test_items_content is not None:
                cleaned = self._pre_test_items_content.strip() + "\n"
            elif os.path.exists(items_nss_path):
                with open(items_nss_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                cleaned = re.sub(r'// -- DEV_TEST_BEGIN --.*?// -- DEV_TEST_END --\n?', '', content, flags=re.DOTALL).strip() + "\n"
            else:
                cleaned = ""

            with open(items_nss_path, "w", encoding="utf-8") as f:
                f.write(cleaned)

            # Sync clean items via ItemsManager to ensure no broken snippets linger
            try:
                from items_manager import ItemsManager
                ItemsManager.instance(project_root=root)._write_items_nss()
            except Exception:
                pass

            trigger_shell_reload()
        except Exception:
            pass

        self._shell_test_active = False
        self._pre_test_items_content = None
        self.shell_test_status_lbl.setText("Shell Engine: Idle (Test items deleted)")
        self.shell_test_status_lbl.setStyleSheet("color: #a6d189; font-size: 10px; font-weight: bold;")
        self.shell_log_output.setText("✓ Test item successfully deleted from imports/items.nss.\nShell reloaded clean.")

    def _on_test_all_in_shell(self):
        """Tests all snippets in items.json and active shell configuration via native shell.exe -reload and shell.log."""
        groups = self.catalog.get("groups", [])
        all_snippets = []
        for g in groups:
            for s in g.get("snippets", []):
                all_snippets.append((g, s))

        if not all_snippets:
            QMessageBox.information(self, "No Snippets", "The catalog has no snippets to test.")
            return

        root = get_project_root()
        shell_log_path = os.path.join(root, "shell.log")
        items_nss_path = os.path.join(root, "imports", "items.nss")
        shell_nss_path = os.path.join(root, "shell.nss")

        os.makedirs(os.path.dirname(items_nss_path), exist_ok=True)

        # 1. Clean existing test blocks and save original state
        orig_items = ""
        if os.path.exists(items_nss_path):
            with open(items_nss_path, "r", encoding="utf-8", errors="ignore") as f:
                orig_items = f.read()

        cleaned_items = re.sub(r'// -- DEV_TEST.*?// -- DEV_TEST_.*?END --\n?', '', orig_items, flags=re.DOTALL).strip()

        # 2. Record initial shell.log size
        initial_log_size = os.path.getsize(shell_log_path) if os.path.exists(shell_log_path) else 0

        # 3. Update status UI
        self.shell_test_status_lbl.setText("Shell Engine: Compiling and testing all snippets in shell...")
        self.shell_test_status_lbl.setStyleSheet("color: #ca9ee6; font-size: 10px; font-weight: bold;")
        self.shell_log_output.setText("Injecting catalog snippets into imports/items.nss and reloading shell.exe...")
        QApplication.processEvents()

        # 4. Build line map and test payload
        line_map = []
        cur_line = (cleaned_items.count('\n') + 1) + 2 if cleaned_items else 2
        payload_parts = []

        for g, s in all_snippets:
            code = s.get("full_code", "").strip()
            # Balance open braces so missing braces don't bleed into subsequent snippets
            open_c = code.count('{')
            close_c = code.count('}')
            if open_c > close_c:
                code += ('\n}' * (open_c - close_c))
            lines_cnt = code.count('\n') + 1
            snip_start = cur_line
            snip_end = snip_start + lines_cnt - 1
            line_map.append({
                'start': snip_start,
                'end': snip_end,
                'snippet': s,
                'group': g,
                'code': code
            })
            payload_parts.append(code)
            cur_line = snip_end + 2

        test_payload = "\n\n".join(payload_parts)
        test_block = f"\n\n// -- DEV_TEST_ALL_BEGIN --\n{test_payload}\n// -- DEV_TEST_ALL_END --\n"
        full_content = (cleaned_items + test_block).strip() + "\n"

        try:
            with open(items_nss_path, "w", encoding="utf-8") as f:
                f.write(full_content)
        except Exception as e:
            QMessageBox.critical(self, "Write Error", f"Failed to write test payload to imports/items.nss:\n{e}")
            return

        # 5. Touch files to notify watcher and reload shell
        try:
            if os.path.exists(shell_nss_path):
                os.utime(shell_nss_path, None)
            os.utime(items_nss_path, None)
        except Exception:
            pass

        trigger_shell_reload()
        time.sleep(0.45)
        QApplication.processEvents()

        # 6. Read new logs from shell.log
        new_text, shell_log_entries = read_shell_log_new_data(shell_log_path, initial_log_size)

        # 7. Clean up imports/items.nss immediately so no test pollution lingers!
        try:
            with open(items_nss_path, "w", encoding="utf-8") as f:
                f.write((cleaned_items + "\n") if cleaned_items else "")
            try:
                from items_manager import ItemsManager
                ItemsManager.instance(project_root=root)._write_items_nss()
            except Exception:
                pass
            trigger_shell_reload()
        except Exception:
            pass

        # 8. Build diagnostic entries strictly from shell.log output
        report_entries = []
        seen_snippets = set()

        for err in shell_log_entries:
            fn_lower = err.filename.lower()
            if 'items.nss' in fn_lower:
                matched = False
                for item in line_map:
                    if item['start'] <= err.line <= item['end']:
                        snip = item['snippet']
                        group = item['group']
                        rel_l = err.line - item['start'] + 1
                        lines = snip.get("full_code", "").splitlines()
                        code_snippet = lines[rel_l - 1] if 0 <= rel_l - 1 < len(lines) else ""
                        report_entries.append({
                            'level': err.level.lower(),
                            'file': 'imports/items.nss',
                            'source_file': snip.get('file_path', 'items.json'),
                            'snippet_id': snip.get('id'),
                            'snippet_name': snip.get('name', 'Unknown Snippet'),
                            'snippet': snip,
                            'group_id': group.get('id'),
                            'group_name': group.get('name'),
                            'rel_line': rel_l,
                            'abs_line': err.line,
                            'column': err.column,
                            'message': err.message,
                            'raw': err.raw,
                            'code_snippet': code_snippet,
                            'source': 'shell.log'
                        })
                        seen_snippets.add(snip.get('id'))
                        matched = True
                        break
                if not matched:
                    report_entries.append({
                        'level': err.level.lower(),
                        'file': 'imports/items.nss',
                        'source_file': 'imports/items.nss',
                        'snippet_id': None,
                        'snippet_name': 'items.nss (Global)',
                        'snippet': None,
                        'group_id': None,
                        'group_name': None,
                        'rel_line': err.line,
                        'abs_line': err.line,
                        'column': err.column,
                        'message': err.message,
                        'raw': err.raw,
                        'code_snippet': '',
                        'source': 'shell.log'
                    })
            else:
                full_path = resolve_nss_path(err.filename, root)
                code_line = ""
                if full_path and os.path.exists(full_path):
                    try:
                        with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                            flines = f.read().splitlines()
                            if 0 <= err.line - 1 < len(flines):
                                code_line = flines[err.line - 1]
                    except Exception:
                        pass
                report_entries.append({
                    'level': err.level.lower(),
                    'file': err.filename,
                    'source_file': full_path or err.filename,
                    'snippet_id': None,
                    'snippet_name': f"File: {err.filename}",
                    'snippet': None,
                    'group_id': None,
                    'group_name': None,
                    'rel_line': err.line,
                    'abs_line': err.line,
                    'column': err.column,
                    'message': err.message,
                    'raw': err.raw,
                    'code_snippet': code_line,
                    'source': 'shell.log'
                })

        # Add PASS entries for clean snippets so user can view full audit in report
        for g, s in all_snippets:
            sid = s.get("id")
            if sid not in seen_snippets:
                report_entries.append({
                    'level': 'ok',
                    'file': 'imports/items.nss',
                    'source_file': s.get('file_path', 'items.json'),
                    'snippet_id': sid,
                    'snippet_name': s.get('name', 'Unknown Snippet'),
                    'snippet': s,
                    'group_id': g.get('id'),
                    'group_name': g.get('name'),
                    'rel_line': 1,
                    'abs_line': 1,
                    'column': 1,
                    'message': 'Valid NSS Syntax & Verified in Shell',
                    'raw': '',
                    'code_snippet': (s.get('full_code', '').splitlines() or [''])[0],
                    'source': 'verified'
                })

        errors_count = sum(1 for r in report_entries if r['level'] == 'error')
        warnings_count = sum(1 for r in report_entries if r['level'] == 'warning')
        clean_count = sum(1 for r in report_entries if r['level'] == 'ok')

        # Update editor banner
        if errors_count > 0:
            self.shell_test_status_lbl.setText(f"✕ Test All Complete: {errors_count} error(s), {warnings_count} warning(s) detected in shell.log")
            self.shell_test_status_lbl.setStyleSheet("color: #e78284; font-size: 10px; font-weight: bold;")
            self.shell_log_output.setText(f"Found {errors_count} syntax error(s) across catalog and shell files.\nSee diagnostic report for exact file and line mappings.")
        elif warnings_count > 0:
            self.shell_test_status_lbl.setText(f"⚠️ Test All Complete: 0 errors, {warnings_count} warning(s) in shell.log")
            self.shell_test_status_lbl.setStyleSheet("color: #e5c890; font-size: 10px; font-weight: bold;")
            self.shell_log_output.setText(f"All items passed with 0 errors. {warnings_count} warning(s) detected in shell.log.")
        else:
            self.shell_test_status_lbl.setText(f"✓ Test All Complete: All {len(all_snippets)} items verified 100% clean in shell.log!")
            self.shell_test_status_lbl.setStyleSheet("color: #a6d189; font-size: 10px; font-weight: bold;")
            self.shell_log_output.setText(f"All {len(all_snippets)} snippets and shell files verified error-free by Nilesoft Shell C++ engine.")

        # Show modal dialog
        report_data = {
            'total_snippets': len(all_snippets),
            'errors_count': errors_count,
            'warnings_count': warnings_count,
            'clean_count': clean_count,
            'entries': report_entries
        }
        dlg = ShellTestAllReportDialog(self, report_data)
        dlg.jump_requested.connect(self.select_snippet_and_go_to_line)
        dlg.retest_requested.connect(self._on_test_all_in_shell)
        dlg.autofix_requested.connect(self._on_autofix_snippets_from_report)
        dlg.exec_()

    def _on_autofix_snippets_from_report(self, snippets_to_fix):
        """Auto-fixes a list of snippets, updates catalog, and persists changes."""
        if not snippets_to_fix:
            return
        fixed_count = 0
        for snip in snippets_to_fix:
            orig = snip.get("full_code", "")
            fixed = auto_fix_nss_code(orig)
            if fixed != orig:
                snip["full_code"] = fixed
                fixed_count += 1

        if fixed_count > 0:
            self.save_catalog()
            self._filter_snippets()
            if self.current_snippet:
                self._load_snippet_into_form(self.current_snippet)
            QMessageBox.information(
                self, "Auto-Fix Applied",
                f"Auto-fixed and saved {fixed_count} snippet(s) to items.json.\nClick '🚀 Re-Test in Shell' to verify the fix."
            )

    def select_snippet_and_go_to_line(self, snippet_id, line=1, col=1):
        """Finds and selects snippet in tree, loads it into editor, and jumps cursor to exact line."""
        for g in self.catalog.get("groups", []):
            for s in g.get("snippets", []):
                if s.get("id") == snippet_id:
                    self.current_snippet = s
                    self.current_group_id = g.get("id")
                    self.selected_category_id = g.get("id")
                    self._load_snippet_into_form(s)
                    # Expand category and select snippet in tree
                    for i in range(self.snippets_tree.topLevelItemCount()):
                        top_item = self.snippets_tree.topLevelItem(i)
                        top_data = top_item.data(0, Qt.UserRole)
                        if top_data and top_data[1] == g.get("id"):
                            top_item.setExpanded(True)
                            for j in range(top_item.childCount()):
                                child = top_item.child(j)
                                c_data = child.data(0, Qt.UserRole)
                                if c_data and c_data[0] == "snippet" and c_data[2] == snippet_id:
                                    self.snippets_tree.setCurrentItem(child)
                                    break
                            break
                    self.code_editor.go_to_line(line, col)
                    self.activateWindow()
                    self.raise_()
                    return True
        return False

    def closeEvent(self, event):
        """Ensure test blocks are cleared on editor close."""
        if getattr(self, '_shell_test_active', False):
            self._clear_test_item_from_shell()
        event.accept()

    # ---------------- Tool Actions ----------------
    def _on_clean_code(self):
        code = self.code_editor.toPlainText()
        cleaned = strip_nss_comments(code)
        self.code_editor.setPlainText(cleaned)

    def _on_auto_detect_metadata(self):
        code = self.code_editor.toPlainText()
        raw_items = find_items_and_menus(code, types=('item', 'menu', 'separator', 'modify'))
        if not raw_items:
            QMessageBox.information(self, "Auto-Detect", "No NSS items or menus found in code.")
            return

        first = raw_items[0]
        props = first.get("props", {})

        title = clean_title(props.get("title"))
        if title and not self.name_input.text():
            self.name_input.setText(title)

        icon = clean_prop(props.get("image")) or clean_prop(props.get("icon"))
        if icon and not self.icon_input.text():
            self.icon_input.setText(icon)

        tip = clean_prop(props.get("tip"))
        if tip and not self.desc_input.text():
            self.desc_input.setText(tip)

        if first.get("type") == "menu" and not self.menu_name_input.text():
            self.menu_name_input.setText(title)

    def _on_new_snippet(self):
        new_snip = {
            "id": "custom_new_item",
            "file_path": "custom/new_item.nss",
            "name": "New Item",
            "category": self.cat_combo.currentText() or "Tools",
            "category_id": self.cat_combo.currentData() or "tools",
            "icon": "\\uE71D",
            "menu_name": "",
            "description": "New custom context menu action",
            "version": "1.0.0",
            "full_code": "item(title='New Item' image=\\uE71D cmd='notepad.exe')",
            "elements": []
        }

        groups = self.catalog.get("groups", [])
        if not groups:
            groups.append({
                "id": "tools",
                "name": "Tools",
                "icon": "\\uE71D",
                "description": "Custom user tools",
                "snippets": []
            })
            self.catalog["groups"] = groups

        target_group = groups[0]
        for g in groups:
            if g.get("id") == self.current_group_id:
                target_group = g
                break

        target_group.setdefault("snippets", []).insert(0, new_snip)
        self.current_snippet = new_snip
        self.current_group_id = target_group.get("id")

        self._filter_snippets()
        self._load_snippet_into_form(new_snip)

    def _on_delete_clicked(self):
        """Dispatches deletion to category or snippet depending on selection."""
        if self.current_snippet:
            self._on_delete_snippet()
        elif getattr(self, 'selected_category_id', None):
            self._on_delete_category(self.selected_category_id)
        else:
            QMessageBox.information(self, "No Selection", "Please select a snippet or category to delete.")

    def _on_delete_snippet(self):
        if not self.current_snippet:
            QMessageBox.information(self, "No Selection", "Please select a snippet to delete.")
            return

        name = self.current_snippet.get("name", "this snippet")
        target_id = self.current_snippet.get("id")
        resp = QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to permanently delete '{name}' ({target_id}) from items.json?",
            QMessageBox.Yes | QMessageBox.No
        )
        if resp != QMessageBox.Yes:
            return

        # 1. Remove from in-memory catalog
        found = False
        for g in self.catalog.get("groups", []):
            snips = g.get("snippets", [])
            initial_len = len(snips)
            g["snippets"] = [s for s in snips if s.get("id") != target_id]
            if len(g["snippets"]) < initial_len:
                found = True

        if not found:
            QMessageBox.warning(self, "Not Found", f"Snippet ID '{target_id}' was not found in catalog.")
            return

        # 2. Also uninstall from ItemsManager if it was installed
        try:
            from items_manager import ItemsManager
            ItemsManager.instance().remove_snippet(target_id)
        except Exception:
            pass

        # 3. Persist catalog to items.json immediately on disk with backup
        total = sum(len(g.get("snippets", [])) for g in self.catalog.get("groups", []))
        self.catalog["total_snippets"] = total
        try:
            if os.path.exists(ITEMS_JSON_PATH):
                bak_path = ITEMS_JSON_PATH + ".bak"
                shutil.copyfile(ITEMS_JSON_PATH, bak_path)

            tmp_path = ITEMS_JSON_PATH + ".tmp"
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(self.catalog, f, indent=2, ensure_ascii=False)
            os.replace(tmp_path, ITEMS_JSON_PATH)
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to persist items.json after delete:\n{e}")
            return

        # 4. Clear selection and update UI
        self.current_snippet = None
        self._populate_category_combos()
        self._filter_snippets()

        if self.snippets_tree.topLevelItemCount() > 0:
            first_group_item = self.snippets_tree.topLevelItem(0)
            if first_group_item.childCount() > 0:
                self.snippets_tree.setCurrentItem(first_group_item.child(0))
            else:
                self.snippets_tree.setCurrentItem(first_group_item)
        else:
            self._clear_form()

        self.catalog_stat_lbl.setText(f"✓ Deleted '{name}' ({target_id}) from items.json. Total: {total}")
        QMessageBox.information(self, "Snippet Deleted", f"Successfully deleted '{name}' ({target_id}) from items.json.\n(File updated on disk, total snippets: {total})")

    def _on_delete_category(self, category_id):
        """Permanently deletes a category group (and any contained snippets) from items.json."""
        target_group = None
        for g in self.catalog.get("groups", []):
            if g.get("id") == category_id:
                target_group = g
                break

        if not target_group:
            QMessageBox.warning(self, "Not Found", f"Category ID '{category_id}' was not found in catalog.")
            return

        cat_name = target_group.get("name", category_id)
        snips = target_group.get("snippets", [])
        snip_count = len(snips)

        if snip_count > 0:
            msg = (
                f"Category '{cat_name}' contains {snip_count} snippets.\n\n"
                f"Are you sure you want to permanently delete this category and ALL its {snip_count} snippets from items.json?"
            )
        else:
            msg = f"Are you sure you want to permanently delete the empty category '{cat_name}' ({category_id}) from items.json?"

        resp = QMessageBox.question(
            self, "Confirm Delete Category",
            msg,
            QMessageBox.Yes | QMessageBox.No
        )
        if resp != QMessageBox.Yes:
            return

        # 1. Uninstall any snippets in this category from ItemsManager
        if snip_count > 0:
            try:
                from items_manager import ItemsManager
                im = ItemsManager.instance()
                for s in snips:
                    im.remove_snippet(s.get("id"))
            except Exception:
                pass

        # 2. Remove group from catalog
        self.catalog["groups"] = [g for g in self.catalog.get("groups", []) if g.get("id") != category_id]
        total = sum(len(g.get("snippets", [])) for g in self.catalog.get("groups", []))
        self.catalog["total_snippets"] = total

        # 3. Persist immediately to items.json on disk with backup
        try:
            if os.path.exists(ITEMS_JSON_PATH):
                bak_path = ITEMS_JSON_PATH + ".bak"
                shutil.copyfile(ITEMS_JSON_PATH, bak_path)

            tmp_path = ITEMS_JSON_PATH + ".tmp"
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(self.catalog, f, indent=2, ensure_ascii=False)
            os.replace(tmp_path, ITEMS_JSON_PATH)
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to persist items.json after deleting category:\n{e}")
            return

        # 4. Clear selections and refresh UI
        self.selected_category_id = None
        self.current_snippet = None
        self.del_snippet_btn.setText("Delete")
        self._populate_category_combos()
        self._filter_snippets()
        self._clear_form()

        if self.snippets_tree.topLevelItemCount() > 0:
            first_group_item = self.snippets_tree.topLevelItem(0)
            self.snippets_tree.setCurrentItem(first_group_item)

        self.catalog_stat_lbl.setText(f"✓ Deleted category '{cat_name}' ({category_id}) from items.json. Total categories: {len(self.catalog.get('groups', []))}")
        QMessageBox.information(self, "Category Deleted", f"Successfully deleted category '{cat_name}' from items.json.\n(Catalog updated on disk)")

    def _on_add_category(self):
        """Prompts user to create a new category group in items.json."""
        cat_name, ok = QInputDialog.getText(self, "Add New Category", "Enter new category name:")
        if not ok or not cat_name.strip():
            return

        cat_name = cat_name.strip()
        cat_id = self._slugify(cat_name)

        for g in self.catalog.get("groups", []):
            if g.get("id") == cat_id or g.get("name", "").lower() == cat_name.lower():
                QMessageBox.warning(self, "Duplicate Category", f"A category with name '{cat_name}' (ID: '{cat_id}') already exists.")
                return

        new_group = {
            "id": cat_id,
            "name": cat_name,
            "icon": "\\uE71D",
            "description": f"{cat_name} context menu items",
            "snippets": []
        }
        self.catalog.setdefault("groups", []).append(new_group)

        try:
            if os.path.exists(ITEMS_JSON_PATH):
                bak_path = ITEMS_JSON_PATH + ".bak"
                shutil.copyfile(ITEMS_JSON_PATH, bak_path)

            tmp_path = ITEMS_JSON_PATH + ".tmp"
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(self.catalog, f, indent=2, ensure_ascii=False)
            os.replace(tmp_path, ITEMS_JSON_PATH)
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save items.json after adding category:\n{e}")
            return

        self._populate_category_combos()
        self._filter_snippets()

        for i in range(self.snippets_tree.topLevelItemCount()):
            item = self.snippets_tree.topLevelItem(i)
            data = item.data(0, Qt.UserRole)
            if data and data[0] == "category" and data[1] == cat_id:
                self.snippets_tree.setCurrentItem(item)
                break

        QMessageBox.information(self, "Category Added", f"Category '{cat_name}' added to items.json!\nYou can now add snippets to it or keep it empty.")

    def _on_tree_context_menu(self, pos):
        """Right-click menu on categories and snippets."""
        item = self.snippets_tree.itemAt(pos)
        if not item:
            return

        data = item.data(0, Qt.UserRole)
        if not data or not isinstance(data, (tuple, list)):
            return

        menu = QMenu(self)
        menu.setStyleSheet("QMenu { background: #1e1e2e; color: #cdd6f4; border: 1px solid #313244; padding: 4px; } QMenu::item:selected { background: #45475a; }")

        item_type = data[0]
        if item_type == "category":
            g_id = data[1]
            act_add = menu.addAction("➕ Add New Snippet Here")
            act_del = menu.addAction("🗑️ Delete Category")

            action = menu.exec_(self.snippets_tree.viewport().mapToGlobal(pos))
            if action == act_add:
                self.current_group_id = g_id
                self._on_new_snippet()
            elif action == act_del:
                self._on_delete_category(g_id)
        elif item_type == "snippet":
            act_del = menu.addAction("🗑️ Delete Snippet")
            act_fix = menu.addAction("🩹 Auto-Fix Snippet")
            act_test = menu.addAction("🚀 Test in Shell")

            action = menu.exec_(self.snippets_tree.viewport().mapToGlobal(pos))
            if action == act_del:
                self._on_delete_snippet()
            elif action == act_fix:
                self._on_autofix_current_item()
            elif action == act_test:
                self._on_test_item_in_shell()

    def _clear_form(self):
        self.id_input.clear()
        self.name_input.clear()
        self.icon_input.clear()
        self.menu_name_input.clear()
        self.desc_input.clear()
        self.file_path_input.clear()
        self.version_input.setText("1.0.0")
        self.code_editor.clear()
        self.ast_tree.clear()
        self.clean_nss_preview.clear()
        self.json_preview.clear()
        self.syntax_banner.setStyleSheet("background: rgba(166, 209, 137, 0.15); border: 1px solid #a6d189; border-radius: 8px;")
        self.syntax_icon_lbl.setText("✓")
        self.syntax_icon_lbl.setStyleSheet("color: #a6d189; font-weight: bold; font-size: 16px;")
        self.syntax_text_lbl.setText("NSS Syntax: Ready")
        self.syntax_text_lbl.setStyleSheet("color: #a6d189; font-weight: bold; font-size: 11px;")
        self.jump_err_btn.setVisible(False)

    def _apply_current_snippet(self, silent=False):
        if not self.current_snippet:
            return

        s_id = self.id_input.text().strip()
        if not s_id:
            if not silent:
                QMessageBox.warning(self, "Missing ID", "Snippet ID cannot be empty.")
            return

        raw_code = self.code_editor.toPlainText()
        is_valid, err_msg, _, _ = validate_nss_syntax_detailed(raw_code)
        if not is_valid and not silent:
            resp = QMessageBox.warning(
                self, "Syntax Warning",
                f"NSS syntax has errors:\n{err_msg}\n\nDo you still wish to save?",
                QMessageBox.Yes | QMessageBox.No
            )
            if resp != QMessageBox.Yes:
                return

        clean_code = strip_nss_comments(raw_code)
        raw_items = find_items_and_menus(raw_code, types=('item', 'menu', 'separator', 'modify'))
        hierarchy = build_hierarchy_from_elements(raw_items, raw_code)

        cat_name = self.cat_combo.currentText().strip() or "General"
        cat_id = self.cat_combo.currentData() or self._slugify(cat_name)

        self.current_snippet["id"] = s_id
        self.current_snippet["name"] = self.name_input.text().strip()
        self.current_snippet["category"] = cat_name
        self.current_snippet["category_id"] = cat_id
        self.current_snippet["icon"] = self.icon_input.text().strip()
        self.current_snippet["menu_name"] = self.menu_name_input.text().strip()
        self.current_snippet["description"] = self.desc_input.text().strip()
        self.current_snippet["file_path"] = self.file_path_input.text().strip()
        self.current_snippet["version"] = self.version_input.text().strip() or "1.0.0"
        self.current_snippet["full_code"] = clean_code
        self.current_snippet["elements"] = hierarchy

        self._ensure_snippet_in_group(self.current_snippet, cat_id, cat_name)

        if not silent:
            self.catalog_stat_lbl.setText(f"✓ Applied changes to '{self.current_snippet['name']}' in memory.")
            QMessageBox.information(self, "Changes Applied", f"Snippet '{self.current_snippet['name']}' updated in catalog memory.\nClick '💾 Save items.json' to persist to disk.")

        self._filter_snippets()

    def _revert_current_snippet(self):
        if self.current_snippet:
            self._load_snippet_into_form(self.current_snippet)

    def _ensure_snippet_in_group(self, snippet, cat_id, cat_name):
        for g in self.catalog.get("groups", []):
            g_snips = g.get("snippets", [])
            for idx, s in enumerate(g_snips):
                if s is snippet and g.get("id") != cat_id:
                    del g_snips[idx]
                    break

        target_group = None
        for g in self.catalog.get("groups", []):
            if g.get("id") == cat_id:
                target_group = g
                break

        if not target_group:
            target_group = {
                "id": cat_id,
                "name": cat_name,
                "icon": "\\uE71D",
                "description": f"{cat_name} context menu items",
                "snippets": []
            }
            self.catalog.setdefault("groups", []).append(target_group)

        if snippet not in target_group.get("snippets", []):
            target_group.setdefault("snippets", []).append(snippet)

    def _on_import_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Import NSS File", SCRIPT_DIR, "Nilesoft Shell (*.nss);;All Files (*.*)")
        if not file_path or not os.path.exists(file_path):
            return

        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                code = f.read()

            base_name = os.path.splitext(os.path.basename(file_path))[0]
            clean_name = " ".join([p.capitalize() for p in base_name.replace('.', '_').replace('-', '_').split('_')])

            self.name_input.setText(clean_name)
            self.file_path_input.setText(os.path.basename(file_path))
            self.code_editor.setPlainText(code)
            self._on_auto_detect_metadata()
            QMessageBox.information(self, "Imported", f"Successfully imported '{os.path.basename(file_path)}' into editor!")
        except Exception as e:
            QMessageBox.critical(self, "Import Error", f"Failed to read file:\n{e}")

    def _slugify(self, text):
        s = re.sub(r'[^a-zA-Z0-9_]', '_', text.strip().lower())
        return re.sub(r'_+', '_', s).strip('_') or "general"


def main():
    app = QApplication(sys.argv)
    try:
        from utils import init_app_fonts
        init_app_fonts()
    except Exception:
        pass
    app.setStyle("Fusion")
    app_font = QFont('Google Sans', 10)
    app_font.setFamilies(['Google Sans', 'Marhey', 'Segoe UI'])
    app.setFont(app_font)
    win = ItemsEditorWindow()
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
