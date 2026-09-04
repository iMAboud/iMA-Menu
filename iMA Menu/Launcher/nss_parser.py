"""
Nilesoft Shell (NSS) Parser, Lexer & AST Rule Manipulation Engine.
Extracted from modify_widget.py for high performance, clean architecture, and modularity.
All functions strictly preserve 100% of Nilesoft syntax formatting and keyword tokens.
"""

import os
import re
import sys
import json
from utils import safe_file_write, normalize_path

_RE_WORD_KEY = re.compile(r'^\w+$')
_RE_ID_EXTRACT = re.compile(r'(?:id\.\w+)')
_RE_HASHED_ICON = re.compile(r'_[a-f0-9]{6}\.(?:png|ico|bmp|svg)$', re.I)

PROJECT_ROOT = None

def set_project_root(root):
    global PROJECT_ROOT
    PROJECT_ROOT = root

def read_file(path):
    if not path or not os.path.exists(path):
        return ""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception:
        return ""

def write_file(path, content, on_success=None, on_error=None):
    try:
        safe_file_write(path, content)
        if on_success:
            on_success()
    except Exception as e:
        if on_error:
            on_error(str(e))


class NSSLexer:
    def __init__(self, text):
        self.text = text
        self.pos = 0

    def tokenize(self):
        tokens = []
        while self.pos < len(self.text):
            ch = self.text[self.pos]
            if ch.isspace():
                self.pos += 1
                continue
            if ch == '/' and self.pos + 1 < len(self.text):
                if self.text[self.pos + 1] == '/':
                    start = self.pos
                    while self.pos < len(self.text) and self.text[self.pos] != '\n':
                        self.pos += 1
                    tokens.append(('COMMENT', self.text[start:self.pos], start))
                    continue
                if self.text[self.pos + 1] == '*':
                    start = self.pos
                    self.pos += 2
                    while self.pos + 1 < len(self.text) and self.text[self.pos:self.pos + 2] != '*/':
                        self.pos += 1
                    self.pos += 2
                    tokens.append(('COMMENT', self.text[start:self.pos], start))
                    continue
            if ch in ("'", '"'):
                start = self.pos
                if ch == "'" and self.text[self.pos:self.pos + 3] == "'''":
                    self.pos += 3
                    while self.pos < len(self.text):
                        if self.text[self.pos:self.pos + 3] == "'''":
                            self.pos += 3
                            break
                        self.pos += 1
                    tokens.append(('STRING', self.text[start:self.pos], start))
                    continue
                elif ch == '"' and self.text[self.pos:self.pos + 3] == '"""':
                    self.pos += 3
                    while self.pos < len(self.text):
                        if self.text[self.pos:self.pos + 3] == '"""':
                            self.pos += 3
                            break
                        self.pos += 1
                    tokens.append(('STRING', self.text[start:self.pos], start))
                    continue
                else:
                    qc = ch
                    self.pos += 1
                    while self.pos < len(self.text):
                        cur = self.text[self.pos]
                        if cur == '\\' and self.pos + 1 < len(self.text):
                            self.pos += 2
                            continue
                        if cur == qc:
                            self.pos += 1
                            break
                        self.pos += 1
                    tokens.append(('STRING', self.text[start:self.pos], start))
                    continue
            if ch.isalpha() or ch in ('@', '_', '$', '#', '\\'):
                start = self.pos
                self.pos += 1
                while self.pos < len(self.text) and (self.text[self.pos].isalnum() or self.text[self.pos] in ('.', '_', '\\', '#', '-')):
                    self.pos += 1
                tokens.append(('IDENTIFIER', self.text[start:self.pos], start))
                continue
            if ch.isdigit():
                start = self.pos
                while self.pos < len(self.text) and (self.text[self.pos].isdigit() or self.text[self.pos] == '.'):
                    self.pos += 1
                tokens.append(('NUMBER', self.text[start:self.pos], start))
                continue
            tokens.append((ch, ch, self.pos))
            self.pos += 1
        return tokens


def parse_nss_args(text, tokens):
    props = {}
    order = []
    i = 0
    while i < len(tokens):
        t_type, t_val, t_pos = tokens[i]
        if t_type == 'COMMENT' or t_val == ',':
            i += 1
            continue
        if t_type == 'IDENTIFIER' and i + 1 < len(tokens) and tokens[i + 1][1] == '=':
            if i + 2 < len(tokens) and tokens[i + 2][1] == '=':
                i += 1
                continue
            key = t_val
            i += 2
            if i >= len(tokens):
                break
            
            # If the next token is a STRING and not immediately followed by an opening paren/bracket/operator
            if tokens[i][0] == 'STRING' and (i + 1 >= len(tokens) or tokens[i + 1][1] in (',', ')', ' ') or (i + 1 < len(tokens) and tokens[i + 1][0] == 'IDENTIFIER' and i + 2 < len(tokens) and tokens[i + 2][1] == '=' and (i + 3 >= len(tokens) or tokens[i + 3][1] != '='))):
                val = tokens[i][1].strip()
                i += 1
            else:
                v_start_pos = tokens[i][2]
                pc, bc, last_pos = 0, 0, v_start_pos
                while i < len(tokens):
                    vt_type, vt_val, vt_pos = tokens[i]
                    if pc == 0 and bc == 0:
                        if vt_val in (',', ')'):
                            break
                        if vt_type == 'IDENTIFIER' and i + 1 < len(tokens) and tokens[i + 1][1] == '=':
                            if i + 2 >= len(tokens) or tokens[i + 2][1] != '=':
                                break
                    if vt_val == '(':
                        pc += 1
                    elif vt_val == ')':
                        if pc > 0:
                            pc -= 1
                        else:
                            break
                    elif vt_val == '[':
                        bc += 1
                    elif vt_val == ']':
                        bc -= 1
                    last_pos = vt_pos + len(vt_val)
                    i += 1
                val = text[v_start_pos:last_pos].strip()
            
            while val.startswith('(') and val.endswith(')'):
                inner = val[1:-1].strip()
                if (inner.startswith("'") and inner.endswith("'")) or (inner.startswith('"') and inner.endswith('"')):
                    val = inner
                else:
                    break

            props[key] = val
            order.append(key)
        else:
            if t_type == 'IDENTIFIER':
                props[t_val] = True
                order.append(t_val)
            i += 1
    props['_order'] = order
    return props


def find_items_and_menus(content, types=('modify', 'item', 'menu')):
    results = []
    lexer = NSSLexer(content)
    tokens = lexer.tokenize()
    i = 0
    while i < len(tokens):
        t_type, t_val, t_pos = tokens[i]
        if t_type == 'IDENTIFIER' and t_val.lower() in [t.lower() for t in types]:
            start_pos = t_pos
            header_end = start_pos + len(t_val)
            
            # Find command header boundary (...)
            if i + 1 < len(tokens) and tokens[i + 1][1] == '(':
                i += 2
                arg_tokens = []
                pc = 1
                bc = 0
                while i < len(tokens) and pc > 0:
                    vt_type, vt_val, vt_pos = tokens[i]
                    if vt_val == '(':
                        pc += 1
                    elif vt_val == ')':
                        pc -= 1
                        if pc == 0:
                            header_end = vt_pos + len(vt_val)
                            i += 1
                            break
                    elif vt_val == '[':
                        bc += 1
                    elif vt_val == ']':
                        bc -= 1
                    arg_tokens.append(tokens[i])
                    i += 1
                props = parse_nss_args(content, arg_tokens)
            else:
                props = {}
                i += 1
                while i < len(tokens):
                    prev_end = header_end
                    curr_start = tokens[i][2]
                    if '\n' in content[prev_end:curr_start] or tokens[i][1] == '{':
                        break
                    header_end = tokens[i][2] + len(tokens[i][1])
                    i += 1
            
            # Peek for optional body { ... }
            block_end = header_end
            has_children = False
            raw_inner = ""
            temp_i = i
            while temp_i < len(tokens) and tokens[temp_i][0] == 'COMMENT':
                temp_i += 1
            if temp_i < len(tokens) and tokens[temp_i][1] == '{':
                body_start_idx = temp_i
                bc_body = 1
                temp_i += 1
                while temp_i < len(tokens) and bc_body > 0:
                    vt_type, vt_val, vt_pos = tokens[temp_i]
                    if vt_val == '{':
                        bc_body += 1
                    elif vt_val == '}':
                        bc_body -= 1
                    elif vt_type == 'IDENTIFIER' and vt_val.lower() in ('item', 'menu', 'modify'):
                        has_children = True
                    temp_i += 1
                block_end = tokens[temp_i - 1][2] + 1
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
        elif t_type == 'COMMENT':
            c_txt = t_val.strip()
            if c_txt.startswith('//'):
                inner = c_txt[2:].strip()
                error_note = None
                if inner.startswith('[Draft'):
                    close_b = inner.find(']')
                    if close_b != -1:
                        meta = inner[1:close_b]
                        if ':' in meta:
                            error_note = meta.split(':', 1)[1].strip()
                        inner = inner[close_b + 1:].strip()
                if inner.lower().startswith(('item(', 'menu(', 'separator')):
                    draft_items = find_items_and_menus(inner, types=types)
                    for d_it in draft_items:
                        d_it['start'] = t_pos
                        d_it['end'] = t_pos + len(t_val)
                        d_it['is_draft'] = True
                        if error_note:
                            d_it['error_msg'] = error_note
                        results.append(d_it)
            i += 1
        else:
            i += 1
    return results


def format_nss_value(k, v):
    if not isinstance(v, str):
        v = str(v)
    if v.lower() in ('true', 'false', 'none'):
        v = v.lower()
    if k == 'where.id':
        clean_v = str(v).strip('\'" ')
        if not clean_v.startswith('id.'):
            clean_v = f"id.{clean_v}"
        return f"where.id={clean_v}"
    if v == '':
        return f"{k}=''"
    v = v.strip()
    
    # Strip unnecessary enclosing parentheses if wrapping a single path/string
    while v.startswith('(') and v.endswith(')'):
        inner = v[1:-1].strip()
        if (inner.startswith("'") or inner.startswith('"') or ('\\' in inner or '/' in inner)) and not re.match(r'^[a-zA-Z_@][\w@.]*\s*\(', inner):
            v = inner
        else:
            break

    # Normalize: strip existing quotes to prevent nesting
    while (v.startswith("'") and v.endswith("'")) or (v.startswith('"') and v.endswith('"')):
        if v.startswith('[') or (v.count("'") + v.count('"')) > 2:
            if v.startswith("''") and v.endswith("''"):
                v = v[2:-2]
                continue
            break
        v = v[1:-1]
    
    v = v.strip()
    
    is_quoted = (v.startswith("'") and v.endswith("'")) or (v.startswith('"') and v.endswith('"'))
    if is_quoted:
        return f"{k}={v}"

    is_wrapped = v.startswith('[') and v.endswith(']')
    is_image_res = v.lower().startswith('image.res(') and v.endswith(')')
    is_image_svg = v.lower().startswith('image.svg(') and v.endswith(')')
    is_svg_tag = v.startswith('<svg') or '<svg' in v.lower()
    is_glyph = v.startswith('\\u') or v.startswith('0x') or (len(v) == 1 and ord(v) > 0xE000)
    
    nilesoft_prefixes = (
        'vis.', 'key.', 'clr.', 'sys.', 'app.', 'this.', 'id.', 'menu.', 'tip.', 'sel.', 'title.',
        'command.', 'io.', 'str.', 'reg.', 'path.', 'theme.', 'icon.', 'image.', 'window.', 
        'cursor.', 'process.', 'user.', 'computer.', 'dt.', 'color.', 'file.', 'dir.',
        '@app.', '@sel.', '@clipboard.', '@sys.', '@path.', '@user.', '@dt.', 'item.', 'menu.'
    )
    is_nilesoft_obj = any(v.lower().startswith(p) for p in nilesoft_prefixes)
    is_func_call = bool(re.match(r'^[a-zA-Z_@][\w@.]*\s*\(', v)) and v.endswith(')')
    is_expression = is_func_call or (('(' in v and ')' in v) and not (v.startswith('@app.dir') or v.startswith('@sel.path'))) or any(op in v for op in ('==', '!=', '&&', '||', ' + ', '+'))
    is_complex = ('@if' in v or '@sel' in v or 'key.' in v or is_expression)
    
    # A real path does not have function calls or expressions
    is_path = ('\\' in v or '/' in v or (':' in v and not v.startswith('0x'))) and not (is_image_res or is_image_svg or is_wrapped or is_glyph or is_func_call or is_expression)
    
    keywords = (
        'true', 'false', 'none', 'inherit', 'parent', 'all', 'auto', 'before', 'after', 
        'both', 'top', 'bottom', 'middle', 'left', 'right', 'contains', 'starts', 'ends', 
        'exact', 'single', 'multiple', 'if', 'else', 'any', 'not', 'and', 'or', 'normal', 'hidden', 'remove'
    )
    has_space = ' ' in v
    has_dot = '.' in v
    
    if is_wrapped or is_glyph or is_image_res or is_image_svg:
        return f"{k}={v}"
    if is_svg_tag:
        return f"{k}='{v}'"
    if is_path:
        return f"{k}='{v}'"
    if k in ('find', 'title', 'menu', 'in', 'cmd', 'path') and not (is_complex or is_nilesoft_obj or is_glyph or is_func_call):
        return f"{k}='{v}'"
    if k in ('args', 'arg') and (v.startswith('/') or v.startswith('-') or (' ' in v and not is_func_call and not v.startswith('@'))):
        if "'" in v and '"' not in v:
            return f'{k}="{v}"'
        elif '"' in v and "'" not in v:
            return f"{k}='{v}'"
        elif "'" in v and '"' in v:
            escaped = v.replace("'", "\\'")
            return f"{k}='{escaped}'"
        return f"{k}='{v}'"

    has_pipe = '|' in v
    should_not_quote = is_complex or is_nilesoft_obj or is_glyph or is_func_call or (v.isdigit() and not has_dot) or v.lower() in keywords
    if has_pipe and not (is_expression or is_complex):
        should_not_quote = False

    if should_not_quote:
        if has_space and not (is_expression or is_complex):
            return f"{k}='{v}'"
        return f"{k}={v}"
    
    return f"{k}='{v}'"


def save_imported_item(data, new_props):
    fp = data['file']
    content = read_file(fp)
    if not content:
        return
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
                target = it
                break
    
    if not target:
        for it in items:
            if abs(it['start'] - data['start']) < 300 and it['type'] == data['type']:
                target = it
                break
    
    if not target:
        target = data
    
    merged = target['props'].copy()
    for k in list(merged.keys()):
        if k not in new_props and k not in ('_order', 'file', 'start', 'end', 'cmd', 'arg', 'args', 'where', 'mode', 'window', 'admin'):
            del merged[k]
    for k, v in new_props.items():
        if v is None or v == 'None' or (k in ('vis', 'pos', 'type', 'menu') and not str(v).strip()):
            if k in merged:
                del merged[k]
        else:
            merged[k] = v
            
    pts = []
    handled = set()
    orig_order = target['props'].get('_order', [])
    for k in orig_order:
        if k in merged:
            v = str(merged[k]).strip()
            pts.append(format_nss_value(k, v))
            handled.add(k)
        elif k == 'sep' and 'sep' in merged:
            v = merged['sep']
            pts.append(format_nss_value('sep', v))
            handled.add('sep')
    for k, v in merged.items():
        if k and k not in handled and k not in ('_order', 'file', 'start', 'end', 'cmd_end', 'raw_inner', 'has_children', 'indent') and _RE_WORD_KEY.match(k):
            pts.append(format_nss_value(k, str(v).strip()))
            
    header = f"{target['type']}({ ' '.join(pts) })"
    cmd_end = target.get('cmd_end', target['end'])
    try:
        new_content = content[:target['start']] + header + content[cmd_end:]
        safe_file_write(fp, new_content)
    except Exception as e:
        print(f"Failed to save changes to {fp}: {e}")


def mass_save_op(item_data, new_props):
    pts = []
    handled = set()
    orig_order = item_data['props'].get('_order', [])
    for k in orig_order:
        if k == 'sep':
            v = new_props.get('sep')
            if v:
                pts.append(format_nss_value('sep', v))
                handled.add('sep')
        elif k in new_props:
            raw_v = new_props[k]
            if raw_v is None or raw_v == 'None':
                if k in ('menu', 'type'):
                    handled.add(k)
                    continue
            v = raw_v.strip() if isinstance(raw_v, str) else str(raw_v)
            if k in ('pos', 'vis', 'remove', 'hidden', 'type') and not v:
                handled.add(k)
                continue
            if k in ('menu', 'type') and (raw_v is None or v == 'None'):
                handled.add(k)
                continue
            pts.append(format_nss_value(k, v))
            handled.add(k)
    for k, v in new_props.items():
        if k and k not in handled and k not in ('_order', 'file', 'start', 'end', 'raw_inner', 'indent', 'cmd_end', 'has_children') and re.match(r'^\w+$', k):
            if v is None or v == 'None':
                continue
            v_s = str(v).strip()
            if k in ('pos', 'vis', 'remove', 'hidden', 'type') and not v_s:
                continue
            pts.append(format_nss_value(k, v_s))
    
    return f"{item_data['type']}({ ' '.join(pts) })"


def _get_custom_menus_from_nss():
    root = PROJECT_ROOT or (os.path.dirname(os.path.dirname(sys.executable)) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    titles = []
    paths = [os.path.join(root, 'imports'), os.path.join(root, 'plugins')]
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
                            title = item['props'].get('title', '').strip().strip("'\"")
                            if title and title.lower() not in ('main', 'options', 'menu.main', 'title.options', ''):
                                if title not in titles:
                                    titles.append(title)
                    except Exception:
                        pass
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
    if all(selection_dict.values()):
        return ""
    hide_conds = []
    if not selection_dict.get('shift'):
        hide_conds.append("key.shift()")
    if not selection_dict.get('ctrl'):
        hide_conds.append("key.control()")
    if not selection_dict.get('caps'):
        hide_conds.append("key.capslock()")
    if not selection_dict.get('lmb'):
        hide_conds.append("key.lbutton()")
    if not hide_conds:
        return ""
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


def is_rule_complete(props):
    find = props.get('find')
    where_id = props.get('where.id') or props.get('where')
    if not find and not where_id:
        return False
    action_props = [k for k in props.keys() if k not in ('find', 'in', 'where', 'where.id', 'type', '_order')]
    return len(action_props) > 0


def extract_ids_from_section(content, name):
    return _RE_ID_EXTRACT.findall(content)


def extract_custom_rules(content):
    rules = []
    s_m = re.search(r"//\s*--\s*iMA\s*Managed\s*--", content, re.IGNORECASE)
    if s_m:
        e_m = re.search(r"//\s*--\s*End\s*iMA\s*Managed\s*--", content[s_m.end():], re.IGNORECASE)
        target_content = content[s_m.end():s_m.end() + e_m.start()] if e_m else content[s_m.end():]
    else:
        target_content = content

    for it in find_items_and_menus(target_content, types=('modify',)):
        raw_where = str(it.get('props', {}).get('where', ''))
        if 'this.id(' in raw_where:
            continue
        if not is_rule_complete(it.get('props', {})):
            continue
        rules.append(it)
    return rules


def update_section(content, sm, em, ids):
    s = content.find(sm)
    e = content.find(em, s)
    return content if (s == -1 or e == -1) else content[:s + len(sm)] + "\n" + ",\n".join([f"    {i}" for i in ids]) + "\n" + content[e:]


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
        except Exception:
            pass

    paths = [os.path.join(root, 'imports'), os.path.join(root, 'plugins')]
    for p in paths:
        if not os.path.exists(p):
            continue
        for r, _, files in os.walk(p):
            for f in files:
                if f.endswith('.nss') and f not in ('theme.nss', 'modify.nss'):
                    fp = os.path.join(r, f)
                    try:
                        find_items_and_menus.current_file = fp
                        content = read_file(fp)
                        matches = find_items_and_menus(content)
                        for m in matches:
                            m['file'] = fp
                            items.append(m)
                    except Exception:
                        pass
    return items


def cleanup_orphan_icons(root):
    icons_dir = os.path.join(root, 'imports', 'icons')
    if not os.path.exists(icons_dir):
        return
    
    nss_contents = []
    search_paths = [os.path.join(root, 'imports'), os.path.join(root, 'plugins'), os.path.join(root, 'shell.nss')]
    for p in search_paths:
        if not os.path.exists(p):
            continue
        if os.path.isfile(p):
            try:
                with open(p, 'r', encoding='utf-8') as f:
                    nss_contents.append(f.read().lower())
            except Exception:
                pass
        else:
            for r, _, files in os.walk(p):
                for f in files:
                    if f.endswith('.nss'):
                        try:
                            with open(os.path.join(r, f), 'r', encoding='utf-8') as f_obj:
                                nss_contents.append(f_obj.read().lower())
                        except Exception:
                            pass

    for r, dirs, files in os.walk(icons_dir):
        if 'originals' in r:
            continue
        for f in files:
            if not _RE_HASHED_ICON.search(f):
                continue
            full_path = os.path.join(r, f)
            f_lower = f.lower()
            is_referenced = any(f_lower in content for content in nss_contents)
            if not is_referenced:
                try:
                    os.remove(full_path)
                except Exception:
                    pass
        
    for r, dirs, files in os.walk(icons_dir, topdown=False):
        if 'originals' in r:
            continue
        if not dirs and not files:
            try:
                os.rmdir(r)
            except Exception:
                pass
