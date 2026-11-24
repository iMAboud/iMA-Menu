# Explore Tab & `items.nss` — Deferred Testing Notes

> **Status**: Removed from Launcher UI (`v2.1.11`) and `shell.nss` so the release stays focused on **Chameleon Theme Engine** and UI polish. All source files and catalog data are preserved on disk for future testing.

---

## What Was Disconnected

1. **Items → Explore Tab (`Launcher/modify_widget.py`)**
   - Removed `explore_tab_btn`, `explore_pg`, `_ensure_explore_initialized`, `explore_placeholder`, and tab index `2` from `ModifyWidget`.
   - `Items` sidebar page now shows only **Edit** (`0`) and **Add** (`1`).
2. **Legacy Plugins Sub-Tab (`Launcher/launcher.pyw`)**
   - Removed unused `plugins_sub_tab_container`, `items_tab_sub_btn`, `items_page`, `items_placeholder`, `switch_plugins_sub_tab`, and `_preload_items_manager`.
   - `plugins_inner_stack` now maps index `0` → Store/Local plugins and index `1` → Apps.
3. **PyInstaller Packaging (`Launcher/build_launcher.py`)**
   - Removed `('cache/items.json', 'cache')` from `datas` and `'items_widget'`, `'items_manager'` from `hiddenimports`.
4. **Master Shell Config (`shell.nss`)**
   - Removed `import 'imports/items.nss'` (also eliminates the empty-file warning in `shell.log`).

---

## Preserved Files on Disk (Intact for Future Testing)

| File | Purpose |
|---|---|
| `Launcher/items_widget.py` | Explore gallery (`ItemsWidget`), `SnippetCard`, `SnippetDetailView`, `MenuBlockCard`, `ItemRowCard`, `AntialiasedTag`, `CategoryFilterButton` |
| `Launcher/items_manager.py` | Snippet catalog & `imports/items.nss` manager (`ItemsManager`) |
| `Launcher/items_editor.pyw` | Standalone catalog editor & live `shell.log` test runner |
| `Launcher/build_items_cache.py` | Catalog cache builder |
| `Launcher/cache/items.json` | Curated snippet catalog |
| `Launcher/cache/items.json.bak` | Previous full RubicBG catalog backup |
| `Launcher/cache/installed_items.json` | Installed items metadata index |
| `Launcher/cache/new items.nss` & `new items.txt` | Draft snippet collections |
| `imports/items.nss` | Target NSS file (currently empty, unimported) |

---

## How to Test & Re-Enable Later

1. **Test snippets standalone first**:
   - Run `python Launcher/items_editor.pyw` to edit, validate, and inject snippets into `imports/items.nss` while inspecting `shell.log` errors.
2. **Re-enable shell import** (`shell.nss`):
   - Add `import 'imports/items.nss'` once `imports/items.nss` has valid tested entries (or let `ItemsManager.ensure_items_nss()` add it).
3. **Re-wire Explore tab** (`Launcher/modify_widget.py`):
   - Restore `explore_tab_btn = PillTabButton(" Explore", 0xE1F0, height=30)` (index `2`), `explore_placeholder`, `explore_pg`, and `_ensure_explore_initialized()` importing `ItemsWidget` from `items_widget`.
4. **Re-add bundle entries** (`Launcher/build_launcher.py`):
   - Restore `('cache/items.json', 'cache')` in `datas` and `'items_widget'`, `'items_manager'` in `hiddenimports`.
