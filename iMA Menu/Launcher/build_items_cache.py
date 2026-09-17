import os
import sys
import json
import re
import urllib.request
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from nss_parser import find_items_and_menus

RAW_BASE = "https://raw.githubusercontent.com/RubicBG/Nilesoft-Shell-Snippets/main/"
TREE_URL = "https://api.github.com/repos/RubicBG/Nilesoft-Shell-Snippets/git/trees/main?recursive=1"

CATEGORY_MAP = {
    "ex1.system": {
        "id": "system",
        "name": "System",
        "icon": "\uE770",
        "description": "Shortcuts, clipboard tools, and system tweaks"
    },
    "ex2.user.cloud.share": {
        "id": "cloud_share",
        "name": "Cloud",
        "icon": "\uE753",
        "description": "Cloud drives, uploading, and file sharing tools"
    },
    "ex2.user.my": {
        "id": "media",
        "name": "Media",
        "icon": "\uE102",
        "description": "Media players and audio/video tools"
    },
    "ex3.archiver": {
        "id": "archiver",
        "name": "Archivers",
        "icon": "\uE8B7",
        "description": "7-Zip, NanaZip, WinRAR, and compression tools"
    },
    "ex3.multifunction": {
        "id": "tools",
        "name": "Tools",
        "icon": "\uE71D",
        "description": "Copy path, hashes, security, firewall, and files"
    },
    "ex4.terminal": {
        "id": "terminal",
        "name": "Terminal",
        "icon": "\uE756",
        "description": "Command Prompt, PowerShell, and custom shells"
    },
    "ex5.goto": {
        "id": "goto",
        "name": "Navigation",
        "icon": "\uE8A7",
        "description": "Jump to registry, run history, and special folders"
    },
    "ext.desktop": {
        "id": "desktop",
        "name": "Desktop",
        "icon": "\uE7F4",
        "description": "Desktop enhancements and Spotlight wallpapers"
    },
    "ext.managers": {
        "id": "managers",
        "name": "Power",
        "icon": "\uE7E8",
        "description": "Power controls, session management, and search"
    },
    "ext.nilesoft": {
        "id": "nilesoft",
        "name": "iMA Tools",
        "icon": "\uE713",
        "description": "iMA Menu tools, mode switcher, and disabler"
    },
    "ext.others": {
        "id": "extensions",
        "name": "Extensions",
        "icon": "\uE74C",
        "description": "Address bar, scrollbar, titlebar, and tweaks"
    },
    "dev.develop": {
        "id": "developer",
        "name": "Developer",
        "icon": "\uEBE8",
        "description": "Windows Sandbox and development shortcuts"
    },
    "dev.helpers": {
        "id": "helpers",
        "name": "Helpers",
        "icon": "\uE897",
        "description": "Segoe icon codes and system path variables"
    }
}

DEFAULT_CATEGORY = {
    "id": "general",
    "name": "General",
    "icon": "\uE71D",
    "description": "Starter context menu items"
}

SNIPPET_INFO = {
    # System
    "ex1_system_all_autorename": ("Auto Rename", "Shorten file and folder names exceeding Windows path limits"),
    "ex1_system_all_clipboard_save": ("Save Clipboard", "Save clipboard contents directly to a file"),
    "ex1_system_all_keyboard_shortcuts": ("Keyboard Shortcuts", "Quick keyboard shortcuts reference guide"),
    "ex1_system_all_openwith_minimal_ml": ("Open With (Minimal)", "Minimal clean Open With dialog launcher"),
    "ex1_system_all_openwith_simple": ("Open With (Simple)", "Quick Open With context menu item"),
    "ex1_system_all_sendto": ("Send To", "Modernized Send To menu with custom targets"),
    "ex1_system_app_mozilla": ("Firefox & Thunderbird", "Quick profile and launch actions for Mozilla apps"),
    "ex1_system_ext_msi": ("MSI Package Tools", "Install, extract, and repair MSI packages"),

    # Cloud & Sharing
    "ex2_user_cloud_share_app_tailscale": ("Tailscale", "Quick Tailscale VPN status and network actions"),
    "ex2_user_cloud_share_app_viber": ("Viber Sharing", "Quick share files via Viber"),
    "ex2_user_cloud_share_cloud_aio": ("Cloud Drives Hub", "Unified menu for all installed cloud drives"),
    "ex2_user_cloud_share_cloud_dropbox_basic_ml": ("Dropbox Shortcuts", "Quick access to Dropbox sync folders"),
    "ex2_user_cloud_share_cloud_dropbox_enhanced": ("Dropbox Enhanced", "Enhanced Dropbox sharing and sync actions"),
    "ex2_user_cloud_share_cloud_dropbox_remove": ("Remove Dropbox Menu", "Hide native Dropbox context menu items"),
    "ex2_user_cloud_share_cloud_google": ("Google Drive", "Quick access to Google Drive locations"),
    "ex2_user_cloud_share_cloud_odrive": ("odrive Sync", "Quick sync actions for odrive"),
    "ex2_user_cloud_share_cloud_onedrive": ("OneDrive", "Quick access and sharing for Microsoft OneDrive"),
    "ex2_user_cloud_share_curl_bashupload_com": ("Upload: BashUpload", "Upload selected file to bashupload.com"),
    "ex2_user_cloud_share_curl_paste_rs": ("Upload: Paste.rs", "Paste file contents to paste.rs"),
    "ex2_user_cloud_share_curl_temp_sh": ("Upload: Temp.sh", "Upload selected file to temp.sh"),
    "ex2_user_cloud_share_curl_transfer_sh": ("Upload: Transfer.sh", "Upload selected file to transfer.sh"),
    "ex2_user_cloud_share_curl_uguu_se": ("Upload: Uguu.se", "Upload selected file to uguu.se"),

    # Media
    "ex2_user_my_app_mpc_be": ("MPC-BE Player", "Open and queue media in MPC-BE player"),

    # Archivers
    "ex3_archiver_app_nanazip": ("NanaZip", "Modern 7-Zip archiver with context menu integration"),
    "ex3_archiver_app_nanazip_remove": ("Remove NanaZip", "Remove native NanaZip context menu entries"),
    "ex3_archiver_app_sevenzip": ("7-Zip", "Classic 7-Zip compression and extraction menu"),
    "ex3_archiver_app_sevenzip_remove": ("Remove 7-Zip", "Hide default 7-Zip context menu entries"),
    "ex3_archiver_app_uniextract": ("Universal Extractor", "Extract virtually any archive or installer format"),
    "ex3_archiver_app_winrar": ("WinRAR", "WinRAR archive management and extraction"),
    "ex3_archiver_app_winrar_portable": ("WinRAR (Portable)", "Portable WinRAR compression integration"),
    "ex3_archiver_sys_compress_extract": ("Compress & Extract", "Quick ZIP compression and extraction tools"),
    "ex3_archiver_sys_compress_ntsf": ("NTFS Compression", "Toggle NTFS filesystem folder compression"),
    "ex3_archiver_sys_compress_ps": ("PowerShell Zip", "Native Windows PowerShell ZIP archiving"),

    # Tools
    "ex3_multifunction_all_copy_hash_cmd": ("File Hash (CMD)", "Generate MD5, SHA1, SHA256 hashes via CMD"),
    "ex3_multifunction_all_copy_hash_ps": ("File Hash (PowerShell)", "Compute precise file hashes via PowerShell"),
    "ex3_multifunction_all_copy_list_cp": ("Copy File Names", "Copy list of selected filenames to clipboard"),
    "ex3_multifunction_all_copy_list_ns": ("Copy File Paths", "Copy list of full paths to clipboard"),
    "ex3_multifunction_all_copy_path_all": ("Copy Path Formats", "Copy path as standard, raw, 8.3, or WSL format"),
    "ex3_multifunction_all_copy_path_env": ("Copy Environment Path", "Copy path using environment variables (%USERPROFILE%)"),
    "ex3_multifunction_all_copy_path_lnk": ("Copy Shortcut Target", "Copy the actual destination path of .lnk files"),
    "ex3_multifunction_all_copy_path_ps": ("Copy Path (PowerShell)", "Copy escaped path formatted for PowerShell"),
    "ex3_multifunction_all_copy_path_url": ("Copy File URL", "Copy path as file:// URL format"),
    "ex3_multifunction_all_drive_file": ("Drive Shortcuts", "Quick access to system drives from files"),
    "ex3_multifunction_all_drive_folder": ("Drive Folders", "Drive navigation shortcuts for directories"),
    "ex3_multifunction_all_drive_hide": ("Hide Drive Letters", "Toggle visibility of specific drive letters"),
    "ex3_multifunction_all_drive_manage": ("Disk Management", "Quick launch for Windows Disk Management"),
    "ex3_multifunction_all_drive_swap": ("Swap Drive Letters", "Swap drive letter assignments easily"),
    "ex3_multifunction_all_security_antithreats": ("Defender Scan", "Scan selected file with Windows Defender"),
    "ex3_multifunction_all_security_encrypt": ("BitLocker & Encryption", "Manage drive encryption and BitLocker"),
    "ex3_multifunction_all_security_env": ("Security Environment", "System security and integrity tools"),
    "ex3_multifunction_all_security_firewall": ("Firewall Rules", "Block or allow application through Windows Firewall"),
    "ex3_multifunction_all_security_permissions": ("Take Ownership", "Grant full administrator permissions to selected path"),
    "ex3_multifunction_commands_item_options": ("File Properties", "Quick file attribute and properties tools"),
    "ex3_multifunction_commands_links_cmd": ("Create Symlink (CMD)", "Create symbolic links and hard links via CMD"),
    "ex3_multifunction_commands_links_ps": ("Create Symlink (PS)", "Create links and junctions via PowerShell"),
    "ex3_multifunction_commands_renamer": ("Batch Renamer", "Powerful batch file and directory renaming"),
    "ex3_multifunction_commands_shortcut": ("Create Shortcut", "Create desktop shortcut for selected item"),
    "ex3_multifunction_ext_comp_dx": ("DirectX Diagnostics", "DirectX runtime diagnostics and configuration"),
    "ex3_multifunction_ext_compatibility": ("Compatibility Mode", "Quick Windows compatibility mode switcher"),
    "ex3_multifunction_ext_priority": ("Process Priority", "Launch program with High/Realtime/Low CPU priority"),
    "ex3_multifunction_ext_regsvr": ("Register DLL/OCX", "Register or unregister ActiveX DLL libraries"),
    "ex3_multifunction_sys_select_mega": ("Select Matching", "Select all files with matching extensions or names"),
    "ex3_multifunction_sys_select_simple": ("Quick Select", "Invert selection or select all items in folder"),

    # Terminal
    "ex4_terminal_all_terminal": ("Terminals & Consoles", "Launch Command Prompt, PowerShell, or Windows Terminal"),

    # Navigation
    "ex5_goto_goto_address": ("Jump to Address", "Quick navigate to address bar path"),
    "ex5_goto_goto_aio": ("System Folders", "Jump to AppData, System32, Program Files, etc."),
    "ex5_goto_goto_reg": ("Registry Jump", "Open Registry Editor at copied key path"),
    "ex5_goto_goto_run": ("Run MRU History", "Jump to recent items from Windows Run history"),
    "ex5_goto_goto_temp": ("Temp Folder", "Open and clean Windows Temporary directory"),
    "ex5_goto_goto_v2": ("Special Folders", "Jump to Windows special folders and libraries"),
    "ex5_goto_goto2_settings": ("Windows Settings", "Jump to specific Windows 10/11 Settings pages"),

    # Desktop
    "ext_desktop_sys_spotlight": ("Windows Spotlight", "Save and view Windows Spotlight lock screen wallpapers"),

    # Power & Managers
    "ext_managers_all_power": ("Power & Session", "Lock, Sleep, Restart, and Shut Down menu"),
    "ext_managers_app_everything": ("Everything Search", "Search selected folder instantly in Everything"),
    "ext_managers_nss_winver": ("Windows Version", "Display detailed Windows build and edition info"),

    # iMA Tools
    "ext_nilesoft_nss_about": ("About iMA Menu", "Show version and build details for iMA Menu"),
    "ext_nilesoft_nss_disabler": ("Menu Item Disabler", "Quickly disable or hide native context menu items"),
    "ext_nilesoft_nss_manager": ("Menu Manager", "Manage context menu items and settings"),
    "ext_nilesoft_nss_mode": ("Shell Mode Switcher", "Toggle between Windows 10 and 11 menu styles"),
    "ext_nilesoft_nss_theme_editor_old": ("Legacy Theme Editor", "Quick theme adjustments"),

    # Extensions
    "ext_others_app_dgvoodoo2": ("dgVoodoo2", "Launch dgVoodoo2 DirectX wrapper settings"),
    "ext_others_bar_address": ("Address Bar Tools", "Actions for the Windows Explorer address bar"),
    "ext_others_bar_scroll": ("Scrollbar Controls", "Explorer scrollbar navigation actions"),
    "ext_others_bar_title": ("Titlebar Actions", "Maximize, minimize, or close from Explorer titlebar"),
    "ext_others_edit": ("Quick Edit Tools", "Open file in Notepad, VS Code, or default editor"),
    "ext_others_ext_audio_wrappers": ("Audio Tools", "Quick audio format operations and utilities"),
    "ext_others_recycle_bin": ("Recycle Bin Tools", "Empty Recycle Bin, view size, or restore items"),
    "ext_others_treeview_advance": ("Folder Tree Tools", "Advanced navigation for Explorer navigation pane"),

    # Developer
    "dev_develop_app_sandbox": ("Windows Sandbox", "Launch file or folder inside Windows Sandbox"),

    # Helpers
    "dev_helpers_nss_icons_segoe": ("Segoe Icons Guide", "Cheatsheet for Segoe MDL2 icon codes"),
    "dev_helpers_nss_icons_win": ("Windows Icons Guide", "Reference for native shell32 and imageres icons"),
    "dev_helpers_nss_meta": ("Menu Metadata", "Display context menu metadata and coordinates"),
    "dev_helpers_nss_paths": ("Path Variables", "Reference guide for iMA Menu path variables"),

    # General
    "shell_basic_1": ("Basic Context Menu", "Minimal starter menu configuration"),
    "shell_basic_2": ("Extended Context Menu", "Standard complete starter menu configuration")
}


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
    if len(t) > 18:
        t = t[:16] + "…"
    return t



def clean_prop(val):
    if not val:
        return ""
    s = str(val).strip()
    if (s.startswith("'") and s.endswith("'")) or (s.startswith('"') and s.endswith('"')):
        return s[1:-1]
    return s


def strip_nss_comments(code):
    """Strips all single-line and multi-line comments from NSS code, returning clean commands."""
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
            # Inline block comment
            line = re.sub(r'/\*.*?\*/', '', line)
            
        trimmed = line.strip()
        if trimmed.startswith('//'):
            continue
            
        # Strip trailing // if not in quotes
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


def build_hierarchy_from_elements(raw_items, full_code):
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


def fetch_file(path):
    url = RAW_BASE + path
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'iMA-Menu-Builder'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return path, resp.read().decode('utf-8', errors='ignore')
    except Exception as e:
        print(f"Error fetching {path}: {e}")
        return path, None


def main():
    print("Fetching repository tree...")
    req = urllib.request.Request(TREE_URL, headers={'User-Agent': 'iMA-Menu-Builder'})
    with urllib.request.urlopen(req) as resp:
        tree = json.loads(resp.read().decode('utf-8')).get('tree', [])

    nss_paths = [n['path'] for n in tree if n['path'].endswith('.nss')]
    md_paths = [n['path'] for n in tree if n['path'].endswith('.md')]

    print(f"Found {len(nss_paths)} NSS files. Downloading...")

    all_paths = nss_paths + md_paths
    file_contents = {}

    with ThreadPoolExecutor(max_workers=16) as executor:
        for p, content in executor.map(fetch_file, all_paths):
            if content is not None:
                file_contents[p] = content

    print(f"Downloaded {len(file_contents)} files. Processing snippets...")

    groups_dict = {}

    for nss_path in nss_paths:
        code = file_contents.get(nss_path, "")
        if not code or not code.strip():
            continue

        folder = nss_path.split('/')[0] if '/' in nss_path else ""
        cat_info = CATEGORY_MAP.get(folder, DEFAULT_CATEGORY)
        cat_id = cat_info["id"]

        if cat_id not in groups_dict:
            groups_dict[cat_id] = {
                "id": cat_id,
                "name": cat_info["name"],
                "icon": cat_info["icon"],
                "description": cat_info["description"],
                "snippets": []
            }

        snippet_id = nss_path.replace('/', '_').replace('.', '_').replace('-', '_')
        if snippet_id.endswith('_nss'):
            snippet_id = snippet_id[:-4]

        # Exclude non-item full desktop theme files
        if snippet_id in ('ext_nilesoft_nss_manager', 'ext_nilesoft_nss_theme_editor_old'):
            continue

        # Use curated friendly name & description
        curated = SNIPPET_INFO.get(snippet_id)
        if curated:
            snippet_name, description = curated
        else:
            base = os.path.basename(nss_path)[:-4]
            snippet_name = " ".join([p.capitalize() for p in base.split('.') if p not in ('all', 'app', 'sys', 'ext')])
            description = f"Context menu items for {snippet_name}"

        # Clean raw code: zero comments, replace references
        clean_code = strip_nss_comments(code)

        raw_items = find_items_and_menus(code, types=('item', 'menu', 'separator', 'modify'))
        hierarchy = build_hierarchy_from_elements(raw_items, code)

        top_icon = ""
        top_menu_title = ""
        for el in hierarchy:
            if el['type'] == 'menu':
                top_icon = el.get('icon', '')
                top_menu_title = el.get('title', '')
                break
            elif el.get('icon') and not top_icon:
                top_icon = el.get('icon', '')

        # Clean menu target if technical
        top_menu_title = clean_friendly_menu_name(top_menu_title)

        snippet_data = {
            "id": snippet_id,
            "file_path": nss_path,
            "name": snippet_name,
            "category": cat_info["name"],
            "category_id": cat_id,
            "icon": top_icon or cat_info["icon"],
            "menu_name": top_menu_title,
            "description": description,
            "version": "1.0.0",
            "full_code": clean_code,
            "elements": hierarchy
        }

        groups_dict[cat_id]["snippets"].append(snippet_data)

    cat_order = [
        "system", "tools", "archiver", "terminal", "goto", "managers",
        "cloud_share", "media", "desktop", "nilesoft", "extensions", "developer", "helpers", "general"
    ]
    sorted_groups = []
    for c_id in cat_order:
        if c_id in groups_dict:
            groups_dict[c_id]["snippets"].sort(key=lambda x: x["name"])
            sorted_groups.append(groups_dict[c_id])

    output_data = {
        "version": "1.0.0",
        "total_snippets": len(nss_paths),
        "groups": sorted_groups
    }

    cache_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache")
    os.makedirs(cache_dir, exist_ok=True)
    out_file = os.path.join(cache_dir, "items.json")

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    print(f"Successfully generated {out_file} with {len(sorted_groups)} groups and {len(nss_paths)} snippets!")


if __name__ == "__main__":
    main()
