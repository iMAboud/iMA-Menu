import os
import sys
import json
import hashlib
import re

from utils import safe_file_write, validate_nss_syntax
from nss_parser import read_file


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


class ItemsManager:
    """Manages iMA Menu snippet catalog, installed items in imports/items.nss, and update diffing."""
    _instance = None

    @classmethod
    def instance(cls, project_root=None, cache_dir=None):
        if cls._instance is None:
            cls._instance = cls(project_root, cache_dir)
        elif project_root:
            cls._instance.project_root = project_root
            cls._instance.items_nss_path = os.path.join(project_root, 'imports', 'items.nss')
            cls._instance.shell_nss_path = os.path.join(project_root, 'shell.nss')
        return cls._instance

    def __init__(self, project_root=None, cache_dir=None):
        base = os.path.dirname(os.path.abspath(__file__))
        self.project_root = project_root or os.path.abspath(os.path.join(base, '..'))
        self.cache_dir = cache_dir or os.path.join(base, 'cache')
        self.catalog_path = os.path.join(self.cache_dir, 'items.json')
        self.installed_path = os.path.join(self.cache_dir, 'installed_items.json')
        self.items_nss_path = os.path.join(self.project_root, 'imports', 'items.nss')
        self.shell_nss_path = os.path.join(self.project_root, 'shell.nss')

        self.catalog = {"groups": []}
        self.snippets_by_id = {}
        self.installed_data = {"snippets": {}, "elements": {}}

        self.load_catalog()
        self.load_installed()

    def load_catalog(self, force=False):
        """Loads snippet catalog from cache/items.json (disabled for now)."""
        self.catalog = {"groups": []}
        self.snippets_by_id = {}
        if not force:
            return
        if os.path.exists(self.catalog_path):
            try:
                with open(self.catalog_path, 'r', encoding='utf-8') as f:
                    self.catalog = json.load(f)
            except Exception as e:
                print(f"[ItemsManager] Error reading catalog: {e}")
                self.catalog = {"groups": []}
        else:
            self.catalog = {"groups": []}

        for group in self.catalog.get("groups", []):
            for snippet in group.get("snippets", []):
                self.snippets_by_id[snippet["id"]] = snippet

    def load_installed(self):
        """Loads installed items metadata."""
        if os.path.exists(self.installed_path):
            try:
                with open(self.installed_path, 'r', encoding='utf-8') as f:
                    self.installed_data = json.load(f)
            except Exception:
                self.installed_data = {"snippets": {}, "elements": {}}
        else:
            self.installed_data = {"snippets": {}, "elements": {}}

        if "snippets" not in self.installed_data:
            self.installed_data["snippets"] = {}
        if "elements" not in self.installed_data:
            self.installed_data["elements"] = {}

    def _save_installed(self):
        """Atomically saves installed items tracking data."""
        try:
            os.makedirs(self.cache_dir, exist_ok=True)
            tmp = self.installed_path + ".tmp"
            with open(tmp, 'w', encoding='utf-8') as f:
                json.dump(self.installed_data, f, indent=2, ensure_ascii=False)
            os.replace(tmp, self.installed_path)
        except Exception as e:
            print(f"[ItemsManager] Error saving installed index: {e}")

    def _ensure_items_nss(self):
        """Ensures imports/items.nss exists and is registered in shell.nss (disabled for now)."""
        return

    def _write_items_nss(self):
        """Reconstructs imports/items.nss cleanly with ZERO comments."""
        self._ensure_items_nss()
        parts = []

        # 1. Full Snippets
        for s_id, s_data in self.installed_data.get("snippets", {}).items():
            code = s_data.get("code", "").strip()
            if code:
                parts.append(code)

        # 2. Individual standalone Elements (only if parent snippet is not already installed as full snippet)
        for e_id, e_data in self.installed_data.get("elements", {}).items():
            s_id = e_data.get("snippet_id")
            if s_id not in self.installed_data.get("snippets", {}):
                code = e_data.get("code", "").strip()
                if code:
                    parts.append(code)

        final_content = "\n\n".join(parts).strip() + ("\n" if parts else "")
        safe_file_write(self.items_nss_path, final_content)

    def _hash_code(self, code_str):
        return hashlib.sha256(code_str.strip().encode('utf-8')).hexdigest()[:16]

    def get_snippet(self, snippet_id):
        return self.snippets_by_id.get(snippet_id)

    def is_snippet_installed(self, snippet_id):
        """Returns 'full', 'partial', or 'none'."""
        snippet = self.get_snippet(snippet_id)
        if not snippet:
            return "none"

        snip_data = self.installed_data.get("snippets", {}).get(snippet_id)
        if snip_data:
            return "full"

        elem_count = 0
        all_elems = self._flatten_elements(snippet.get("elements", []))
        actionable_elems = [el for el in all_elems if el.get("type", "").lower() != "separator"]
        if not actionable_elems:
            return "none"

        for el in actionable_elems:
            if el["id"] in self.installed_data.get("elements", {}):
                elem_count += 1

        if elem_count == 0:
            return "none"
        return "full" if elem_count >= len(actionable_elems) else "partial"

    def is_element_installed(self, elem_id):
        if elem_id in self.installed_data.get("elements", {}):
            return True
        for s_data in self.installed_data.get("snippets", {}).values():
            if elem_id in s_data.get("installed_elements", []):
                return True
        return False

    def has_snippet_update(self, snippet_id):
        """Returns True if the store version of this snippet differs from installed hash."""
        snip = self.get_snippet(snippet_id)
        if not snip:
            return False
        snip_data = self.installed_data.get("snippets", {}).get(snippet_id)
        if not snip_data:
            return False

        inst_hash = snip_data.get("hash")
        if not inst_hash:
            return False
        store_hash = self._hash_code(snip.get("full_code", ""))
        return inst_hash != store_hash

    def _flatten_elements(self, elements):
        res = []
        for el in elements:
            res.append(el)
            if el.get("children"):
                res.extend(self._flatten_elements(el["children"]))
        return res

    def add_snippet(self, snippet_id):
        """Adds clean snippet code with zero comments to imports/items.nss."""
        snippet = self.get_snippet(snippet_id)
        if not snippet:
            return False

        clean_code = strip_nss_comments(snippet.get("full_code", ""))
        s_hash = self._hash_code(clean_code)

        all_elems = self._flatten_elements(snippet.get("elements", []))
        elem_ids = [el["id"] for el in all_elems if el.get("type", "").lower() != "separator"]

        # Clean any partial individual elements of this snippet first
        for eid in elem_ids:
            self.installed_data["elements"].pop(eid, None)

        self.installed_data["snippets"][snippet_id] = {
            "code": clean_code,
            "installed_elements": elem_ids,
            "hash": s_hash,
            "customized": False
        }

        for el in all_elems:
            if el.get("type", "").lower() != "separator":
                self.installed_data["elements"][el["id"]] = {
                    "snippet_id": snippet_id,
                    "code": strip_nss_comments(el.get("raw_code", "")),
                    "customized": False
                }

        self._save_installed()
        self._write_items_nss()
        return True

    def remove_snippet(self, snippet_id):
        """Removes snippet and its elements from items.nss."""
        if snippet_id in self.installed_data["snippets"]:
            elem_ids = self.installed_data["snippets"][snippet_id].get("installed_elements", [])
            for eid in elem_ids:
                self.installed_data["elements"].pop(eid, None)
            del self.installed_data["snippets"][snippet_id]

        to_del = [eid for eid, ed in self.installed_data["elements"].items() if ed.get("snippet_id") == snippet_id]
        for eid in to_del:
            self.installed_data["elements"].pop(eid, None)

        self._save_installed()
        self._write_items_nss()
        return True

    def _unpack_snippet_if_needed(self, snippet_id):
        """Unpacks a full snippet into individual element tracking entries so edits/removals persist."""
        if snippet_id in self.installed_data.get("snippets", {}):
            del self.installed_data["snippets"][snippet_id]
            snip = self.get_snippet(snippet_id)
            if snip:
                for el in self._flatten_elements(snip.get("elements", [])):
                    eid = el["id"]
                    if el.get("type", "").lower() != "separator" and eid not in self.installed_data["elements"]:
                        self.installed_data["elements"][eid] = {
                            "snippet_id": snippet_id,
                            "code": strip_nss_comments(el.get("raw_code", "")),
                            "customized": False
                        }

    def add_menu(self, snippet_id, menu_elem_id, custom_code=None):
        """Adds a specific clean menu container with zero comments."""
        snippet = self.get_snippet(snippet_id)
        if not snippet:
            return False

        all_elems = snippet.get("elements", [])
        menu_node = None
        for el in all_elems:
            if el["id"] == menu_elem_id:
                menu_node = el
                break

        if not menu_node:
            return False

        self._unpack_snippet_if_needed(snippet_id)
        raw = custom_code or menu_node.get("raw_code", "")
        clean_menu_code = strip_nss_comments(raw)
        menu_children = self._flatten_elements(menu_node.get("children", []))
        elem_ids = [menu_node["id"]] + [c["id"] for c in menu_children if c.get("type", "").lower() != "separator"]

        # Store menu node code under menu_elem_id
        self.installed_data["elements"][menu_elem_id] = {
            "snippet_id": snippet_id,
            "code": clean_menu_code,
            "customized": bool(custom_code)
        }

        # Track child elements as installed
        for c in menu_children:
            cid = c["id"]
            if cid != menu_elem_id and c.get("type", "").lower() != "separator":
                self.installed_data["elements"][cid] = {
                    "snippet_id": snippet_id,
                    "code": strip_nss_comments(c.get("raw_code", "")),
                    "customized": False
                }

        self._save_installed()
        self._write_items_nss()
        return True

    def remove_menu(self, snippet_id, menu_elem_id):
        """Removes a menu and its child elements."""
        snippet = self.get_snippet(snippet_id)
        menu_node = None
        if snippet:
            for el in snippet.get("elements", []):
                if el["id"] == menu_elem_id:
                    menu_node = el
                    break

        self._unpack_snippet_if_needed(snippet_id)
        elem_ids = [menu_elem_id]
        if menu_node:
            elem_ids.extend([c["id"] for c in self._flatten_elements(menu_node.get("children", []))])

        for eid in elem_ids:
            self.installed_data["elements"].pop(eid, None)

        self._save_installed()
        self._write_items_nss()
        return True

    def add_element(self, snippet_id, elem_id, custom_code=None, parent_menu_title=None):
        """Adds or updates a single clean item with zero comments."""
        snippet = self.get_snippet(snippet_id)
        if not snippet:
            return False

        all_elems = self._flatten_elements(snippet.get("elements", []))
        target_elem = None
        for el in all_elems:
            if el["id"] == elem_id:
                target_elem = el
                break

        if not target_elem:
            return False

        self._unpack_snippet_if_needed(snippet_id)
        raw_code = custom_code or target_elem.get("raw_code", "").strip()
        clean_code = strip_nss_comments(raw_code)

        if not parent_menu_title:
            for el in snippet.get("elements", []):
                if el.get("type", "").lower() == "menu":
                    for child in el.get("children", []):
                        if child.get("id") == elem_id:
                            parent_menu_title = el.get("title") or snippet.get("menu_name")
                            break
                    if parent_menu_title:
                        break
            if not parent_menu_title and snippet.get("menu_name"):
                parent_menu_title = snippet.get("menu_name")

        if parent_menu_title and not re.search(r'\bmenu\s*=', clean_code, re.IGNORECASE):
            clean_code = self._inject_menu_attribute(clean_code, parent_menu_title)

        self.installed_data["elements"][elem_id] = {
            "snippet_id": snippet_id,
            "code": clean_code,
            "customized": bool(custom_code)
        }

        self._save_installed()
        self._write_items_nss()
        return True

    def remove_element(self, snippet_id, elem_id):
        """Removes a single item."""
        self._unpack_snippet_if_needed(snippet_id)
        self.installed_data["elements"].pop(elem_id, None)
        self._save_installed()
        self._write_items_nss()
        return True

    def get_installed_snippet_code(self, snippet_id):
        snip_data = self.installed_data.get("snippets", {}).get(snippet_id)
        if snip_data:
            return snip_data.get("code", "")
        return ""

    def get_diff(self, snippet_id):
        snippet = self.get_snippet(snippet_id)
        store_code = snippet.get("full_code", "").strip() if snippet else ""
        installed_code = self.get_installed_snippet_code(snippet_id)
        return installed_code, store_code

    def apply_update(self, snippet_id):
        return self.add_snippet(snippet_id)

    def _inject_menu_attribute(self, item_code, menu_title):
        m = re.search(r'\b(item|modify)\s*\(', item_code, re.IGNORECASE)
        if not m:
            return f"menu(title='{menu_title}') {{\n\t{item_code}\n}}"
        idx = m.end()
        return item_code[:idx] + f"menu='{menu_title}' " + item_code[idx:]
