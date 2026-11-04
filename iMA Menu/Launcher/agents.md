# iMA Menu Launcher — Master Blueprint

> **Usage**: Reference this file before any code changes. Do not search or index secondary directory trees unless explicitly requested.

---

## Project Overview

A Windows desktop application that serves as a launcher/manager for **iMA Menu** — a tool that customizes the Windows right-click context menu. Version **2.1.7** (Shell 2.0.0.4).

---

## Tech Stack

| Layer | Technology |
|---|---|
| UI | Python 3.12 + PyQt5 (frameless, dark theme) |
| Shell Engine | C++ (Win32 API) — `shell.dll`, `shell.exe` (VS2022, Detours hooking, PlutoSVG) |
| Updater | C# — `ima_updater.exe` (UAC elevated file replacement + safe clean restart) |
| Build | PyInstaller (`--onefile --windowed`) → `launcher.exe` |

---

## Entry Points

| What | Where | Role |
|---|---|---|
| **App Start** | `launcher.pyw` → `__main__` (line ~3941) | Creates `QApplication`, loads stylesheet, instantiates `PluginManager` |
| **Main Window** | `PluginManager` class (launcher.pyw:2005) | Sidebar + `QStackedWidget` (plugins, modify, theme, settings pages) |
| **Shell Engine** | `shell.exe` / `shell.dll` | Native iMA Menu shell loaded by Windows Explorer |
| **NSS Config** | `shell.nss` (project root) | Master config that imports all `.nss` modules |
| **Updater** | `ima_updater.exe` (from `updater.cs`) | Elevated file operations for app updates |
| **Items Editor** | `items_editor.pyw` | Standalone catalog editor, AST inspector & shell diagnostics |
| **Build** | `build_launcher.py` | Invokes PyInstaller with correct flags |

**CLI flags**: `--open-only` (UI only, no reload), `--close-only` (reload shell and exit), `--edit-rule` (standalone rule/item editor popup from context menu right-click).

---

## Data Architecture

### Data Flow

```
GitHub API (iMAboud/iMA-Menu-Plugins)
  │  FetchPluginsThread — JSON manifest
  ▼
Local Cache (cache/plugins.json)
  │  PluginRegistry merge
  ▼
Plugin Registry (cache/plugin_registry.json)
  │  InstallationWorker — downloads from GitHub Git Trees API
  ▼
Plugin Directories (plugins/<name>/)
  │  NSS import management
  ▼
Shell Config (shell.nss → imports/*.nss, plugins/*.nss)
  │  shell.exe -reload
  ▼
Windows Explorer Context Menu
```

### Data Stores (all file-based, no DB)

| Store | Format | Purpose |
|---|---|---|
| `cache/settings.json` | JSON | App preferences (auto_update, auto_check_updates, etc.) |
| `cache/plugin_registry.json` | JSON (schema v2) | Plugin state: installed_version, remote_version, file_hashes, status |
| `cache/plugins.json` | JSON array | Remote plugin manifest (name, description, version, icon_url, nss_path, dependencies) |
| `cache/apps.json` | JSON array | Remote standalone apps manifest (name, description, repo, asset_name, auto_run) |
| `cache/items.json` | JSON | Snippet catalog (95 items across 14 categories from RubicBG repo) |
| `cache/installed_items.json` | JSON | Installed snippet items metadata index |
| `cache/git_tree_cache.json` | JSON | Cached GitHub Git Trees API response |
| `cache/color_palette.json` | JSON | Theme editor color palette |
| `cache/recent_colors.json` | JSON | Last 8 recently used colors |
| `cache/last_image_dir.json` | JSON | Last browsed directory for image selection |
| `cache/cursors/favorites.json` | JSON array | Starred/favorite cursor themes |
| `cache/icons/` | PNG files | Downloaded plugin icons |
| `.cloud_token.dat` | Encrypted text | Google Drive OAuth tokens (DPAPI-encrypted) |
| `shell.nss` | NSS config | Master context menu configuration |
| `imports/*.nss` | NSS config files | Modular menu/theme/modify/items scripts (`items.nss`) |
| `plugins/<name>/` | Directories | Installed plugin files (.nss, executables, assets) |
| `shell.log` | Text log | iMA Menu shell engine error/warning log |

### Critical Data Patterns

- **Atomic writes**: `atomic_json_write()` — temp file + `os.replace()` for crash safety
- **Safe file writes**: `safe_file_write()` — validates NSS syntax, uses temp file + `fsync` + replace
- **File hash tracking**: Git-compatible blob SHA1 for detecting file changes
- **Version comparison**: Semantic version parsing with `version_cmp()` / `_parse_version()`
- **NSS syntax validation**: `validate_nss_syntax()` checks bracket/quote balance with comment stripping before any write
- **Auto-fix**: `NSSAutoFixer` repairs common NSS syntax errors (up to 2 attempts)
- **Registry reconciliation**: `PluginRegistry.reconcile_with_disk()` syncs registry with actual files

---

## Module Map

| Module | Key Classes | Responsibility |
|---|---|---|
| `launcher.pyw` | `PluginManager`, `UpdateWorker`, `PluginLogic`, `UninstallWorker`, `AppDeleteButton`, `AppGitHubButton` | App orchestration, plugin store UI, standalone apps management, update logic, non-blocking uninstall worker |
| `nss_parser.py` | `NSSLexer`, `parse_nss_args`, `find_items_and_menus`, `format_nss_value`, `heal_corrupted_nss_expr`, `is_enclosed_string`, `save_imported_item`, `scan_nss_items` | iMA Menu NSS AST lexing, argument parsing, property formatting, rule replacement |
| `plugin_workers.py` | `FetchPluginsThread`, `IconDownloadWorker`, `InstallationWorker`, `DetailsFetchWorker`, `DetailsPopup` | Plugin download/install workers, icon caching, Markdown detail popups |
| `modify_widget.py` | `ModifyWidget`, `ImportsWidget`, `ModifyRuleEditorDialog`, `UnifiedFindInput`, `MatchModeButton`, `IDDropdownPopup`, `ImportEditorDialog`, `MultiItemEditDialog`, `TabGridScrollArea`, `NSSItemModel`, `NSSItemDelegate`, `GlobalTintWorker` | NSS file editor, item modification rules, import management, unified find ID dropdown, multi-mode icon tinting |
| `menu_builder_widget.py` | `MenuBuilderWidget`, `BuilderItemCard`, `ItemConfigDialog`, `PipelineStepWidget`, `StyledConfirmDialog`, `PresetChip` | Visual Add item/menu builder tab, cards list, popup editor dialog with One Action / Sequence Actions, collapsible advanced drawer, styled dialogs, file manager |
| `theme_switcher_widget.py` | `ThemeSwitcherWidget`, `ThemeOptionFrame`, `FetchThemesWorker` | Theme gallery grid, selection, add/edit/delete, GitHub auto-sync |
| `cursor_widget.py` | `CursorGalleryWidget`, `CursorOptionFrame`, `DownloadAllCursorsWorker`, `ConcurrentPreviewWorker`, `DownloadThemeWorker`, `CurGenerator`, `WindowsCursorManager` | Windows cursor theme store & manager, bundled preview atlas, vector star favorites, Download All with Git SHA hash skipping, .cur compiler, registry installer |
| `theme_editor_widget.py` | `ThemeEditorWidget`, `MinimalColorPickerDialog`, `ModernSlider`, `RadiusButton`, `ColorPickerWidget` | Visual theme property editor (colors, 100+ fonts with live previews, borders, sliders) |
| `plugin_registry.py` | `PluginRegistry` | Plugin state tracking, disk reconciliation, hash verification |
| `github_client.py` | `github_api_get`, `cdn_get`, `download_file`, `get_latest_tree_sha` | Native Windows WinINet client (ctypes, Schannel TLS, session reuse/keep-alive, strict SSL with fallback, tree SHA TTL cache, atomic downloads) |
| `cloud_sync.py` | `CloudSyncManager`, `OAuthHandler`, `OAuthServer` | Google Drive OAuth2, silent daily backup/restore, conflict detection, native Windows DPAPI (Crypt32.dll) |
| `nss_error_monitor.py` | `ShellLogMonitor`, `NSSErrorEntry` | Watches shell.log, auto-fixes NSS parse errors |
| `utils.py` | `NSSAutoFixer`, `fix_nss_mode_syntax_once`, `restore_open_with_once`, `init_app_fonts`, `get_supported_theme_fonts`, `AsyncFileIo`, `ModernDialog`, `AccountProfileDialog`, `FlowLayout`, `ModernSwitch`, `PillProgressBar`, `ModernComboBox`, `CapsuleActionButton`, `PillTabButton`, `PillPushButton`, `PillLineEdit`, `PillNotification`, `AnimatedStackedWidget`, `CloudSyncConflictDialog` | Shared utilities, canonical UI components, font subsystem, animated page transitions, sync conflict modal, file I/O, native Win32 ctypes API wrappers |
| `apps_manager.py` | `FetchAppsWorker`, `AppDownloadWorker`, `AppIconWorker` | Standalone apps manifest fetcher, GitHub latest release resolver, background downloader & process launcher |
| `items_widget.py` | `ItemsWidget`, `SnippetCard`, `SnippetDetailView`, `MenuBlockCard`, `ItemRowCard`, `ItemQuickEditDialog`, `SnippetDiffDialog` | Snippets gallery (workspace dev-only, hidden from launcher) |
| `items_manager.py` | `ItemsManager` | Snippets catalog manager (workspace dev-only, unbundled) |
| `items_editor.pyw` | `ItemsEditorWindow` | Standalone developer editor for items.json, live Nilesoft Shell AST inspection, syntax validation |
| `tester.pyw` | `TesterWindow`, `SandboxEnvironment`, `TestRunner` | Standalone automated QA harness, 13 test suites, latency benchmarking, isolated sandbox |
| `telemetry.py` | `init_telemetry`, `send_telemetry_event` | Non-blocking crash & error reporter, PII scrubber, rate-limiting proxy client |
| `cloudflare_worker.js` | Cloudflare Worker | Discord crash webhook proxy with PII redaction and rate limiting |
| `../imports/version_manager.pyw` | `save_snapshot`, `restore_snapshot`, `delete_snapshot`, `sync_nss_menu` | Context-menu Git snapshot manager for `Launcher/` and `src/` (`imports/version.nss`, `cache/version_snapshots.nss`) |


---

## Native C++ Source (src/)

| Directory | Role |
|---|---|
| `src/exe/` | `shell.exe` — Win32 main window, DPI handling, font loading, settings UI |
| `src/dll/` | `shell.dll` — COM server, context menu handler, Detours hooks |
| `src/dll/src/Expression/` | NSS expression evaluator |
| `src/dll/src/Parser/` | NSS file parser |
| `src/shared/` | Shared headers (Globals.h, System.h, RegistryConfig.h) |
| `src/shared/Library/` | PlutoVGWrap (SVG rendering) |
| `src/lib/detours/` | Microsoft Detours (function hooking) |
| `src/lib/plutosvg/` | PlutoSVG (SVG rendering) |
| `src/bin/` | Pre-built binaries, default `shell.nss`, imports, themes |
| `src/setup/` | WiX installer + custom action DLL |

---

## Component Rules

### Qt Widget Hierarchy
```
PluginManager (QWidget)
  ├── side_panel (80px fixed sidebar — icon buttons)
  └── content_area (QStackedWidget)
        ├── plugins_page (Plugin store grid)
        ├── modify_page (ModifyWidget — NSS editor)
        ├── theme_page (Tab: ThemeSwitcherWidget | ThemeEditorWidget | CursorGalleryWidget)
        └── settings_page (Settings rows)
```

### Naming Conventions
- **Classes**: PascalCase (`PluginManager`, `NSSAutoFixer`)
- **Functions/methods**: snake_case (`get_plugin_install_path`)
- **Constants**: UPPER_SNAKE_CASE (`PROJECT_ROOT`, `PLUGINS_DIR`)
- **Private methods**: Leading underscore (`_initialize_app_paths`)
- **Qt signals**: camelCase (`auth_finished`, `download_progress`)
- **File names**: snake_case (`theme_editor_widget.py`)
- **NSS files**: kebab-case for imports (`file-manage.nss`), PascalCase for themes (`Default.nss`)

### UI Patterns
- **Single Instance**: Named mutex (`CreateMutexW`) + `RegisterWindowMessageW` IPC to unminimize, focus, and flash running instance
- All windows are **frameless** (`Qt.FramelessWindowHint`) with custom title bars
- Win32 hit-testing for resize/move
- Acrylic/Mica transparency via `SetWindowCompositionAttribute` and DWM APIs
- Consistent `ModernDialog` pattern: dark frame, rounded corners, crimson accent
- **NavTabButton**: Sidebar tab with glassy acrylic container and gradient sheen highlight for active state
- **Horizontal Plugin Cards**: 2-column horizontal acrylic cards with floating icons and integrated CapsuleActionButton
- **CapsuleActionButton**: Pill-shaped action button with tactile circle badge, animated dots ("Installing..."), circular progress arc, and real-time card/popup synchronization
- Undo/Redo via `QUndoStack` (Ctrl+Z / Ctrl+Y) for file modifications

### Shell Integration
- IPC with native shell via `WM_COPYDATA` to hidden window `iMA_IPC_Class`
- Shell reload: `CMD_RELOAD` message or `shell.exe -reload`
- NSS error monitoring: file system watcher + polling on `shell.log`
- Auto-healing of NSS syntax errors with `NSSAutoFixer`

### Plugin Installation Pattern
- Staging directory pattern: `.staging_<name>` → rename to target
- Rollback to backup on failure
- File integrity tracked via Git-compatible SHA1 blob hashes

### Build Pipeline
- **Python**: PyInstaller `--onefile --windowed` with bundled assets (CSS, icons, fonts, shell binaries, cursors atlas; translations, unused Qt plugins, and OpenSSL stripped)
- **C++**: VS2022, multi-arch (x86/x64/ARM64), Detours + PlutoSVG
- **Installer**: WiX MSI with custom action DLL
- **App updates**: GitHub Releases (`iMAboud/iMA-Menu-Updater`)

### GitHub Integration
- Plugin manifest: `raw.githubusercontent.com` CDN
- Git Trees API for bulk file operations
- Tree SHA caching for deduplication
- Release API for launcher updates and dependency downloads
- Repos: `iMAboud/iMA-Menu-Plugins` (plugins), `iMAboud/iMA-Menu-Updater` (launcher updates)
