# iMA Menu Launcher — Development Context

> **Usage**: Reference this file before starting work to understand current state. Update after completing tasks.

---

## Current Version

**2.1.7** — Context menu right-click rule editor, automated cross-repo CI/CD & release pipeline (Shell 2.0.0.4)

---

- **Right-Click Context Menu Rule Targeting & Exact Find (2.1.7)**:
  - **Nested Submenu Right-Click Race & Hook Fix**: Hooked `WH_GETMESSAGE` (`GetMsgProc`) on the menu thread in `ContextMenu.cpp`, stopped `MN_BUTTONDOWN` from overwriting `mouse_button` with `VK_LBUTTON` when `VK_RBUTTON` was already released during submenu render delay, and ensured `WinEventProc` subclasses reused `#32768` submenu HWNDs on `EVENT_OBJECT_SHOW`.
  - **Moved/Nested System Item Metadata**: Preserved `original_path` (`--in`), `move_menu` (`--menu`), and `raw_title` (`--original-title`) for moved/renamed system items, removed false `owner->source_file` custom tagging on system items inside custom menus, and filtered `vis=vis.remove` items from `.nss` auto-discovery.
  - **Rule Modification Title Preservation**: Fixed `ModifyRuleEditorDialog.get_data()` silently stripping `title` property when editing other attributes (e.g. icon). Eliminated incorrect `orig_ref` and `find_ref` case-insensitive equality wipeout, guaranteeing modified titles persist unless user explicitly empties the New Title input. Added `IDENT_ID_DISPLAY_SETTINGS`, `IDENT_ID_PERSONALIZE`, and fallback system titles to `ContextMenu.cpp`.
  - **Context Menu Right-Click Targeting**: Added `MN_BUTTONDOWN` / `MN_BUTTONUP` and `WM_RBUTTONUP` interception in `ContextMenu::MenuSubClassProc` (`src/dll/src/ContextMenu.cpp`). Right-clicking any item cancels the modal menu loop cleanly via `::SendMessageW(hWnd, MN_CANCELMENUS, 0, 0)` & `::EndMenu()` and launches `launcher.exe --edit-rule` targeting the clicked item (`--title`, `--id`, `--in`, `--pos`, `--type`, `--icon`, `--src-file`, `--src-line`, `--is-custom`).
  - **Custom NSS In-Place Editing**: Items and menus originating from custom `.nss` files (e.g. `valo.nss`, `items.nss`) pass their origin file and line number (`menu->source_file`, `menu->source_line`) or auto-discover their source `.nss` in Launcher, opening `ImportEditorDialog` to edit and save them in-place directly in their source `.nss` file instead of creating unwanted `modify.nss` rules.
  - **In-Frame Viewport Clamping**: Implemented `availableGeometry()` work-area boundary clamping and dynamic `adjustSize()` sizing on `ModifyRuleEditorDialog` and `ImportEditorDialog`, with `showEvent` safety bounds to ensure rule editor popups opened near taskbars or screen edges always stay 100% visible in frame.
  - **Exact Find Persistence**: Fixed `nss_parser.py` and `modify_widget.py` to preserve double quotes for exact find (`find='"item"'`). Correctly loads exact mode from NSS and saves exact rules with inner double quotes (`SearchType::Equals`).

- **Cloudflare Telemetry Proxy & Antivirus-Safe Crash Reporting (2.1.6)**:
  - **Discord Webhook Shielding**: Isolated Discord webhook URL into a standalone Cloudflare Worker proxy (`cloudflare_worker.js`), completely removing all Discord endpoints and strings from the client binary to avoid antivirus heuristic detections.
  - **Non-Blocking Telemetry Hook**: Implemented `telemetry.py` hooking `sys.excepthook` and `sys.unraisablehook`, dispatching sanitized crash reports asynchronously via daemon threads with zero GUI blocking.
  - **Dual PII Redaction & Deduplication**: Scrubbed Windows username directory paths and sensitive credentials at both client and edge levels, with 60s rate-limiting to prevent Discord error loop spamming.

- **Standalone Apps Re-download, Update & Delete Architecture (2.1.5)**:
  - **App Delete Button**: Added dedicated 30x30 vector trash action button (`AppDeleteButton`) to standalone app cards for removing downloaded binaries and resetting card state to Download.
  - **Vertical Stacked Action Buttons**: Placed `Open` on top and `Update` below in a vertical column matching the plugins card layout, preventing horizontal overflow.
  - **Purple Open Gradient Badge**: Switched `Open` action button badge from sky blue to Catppuccin purple (`#ca9ee6` -> `#a855f7`), reserving blue exclusively for `Update`.
  - **Clean Executable Lifecycle**: Terminated running processes prior to binary replacement and purged older `.exe` variants from `Apps/<app_name>/`, ensuring the "Open" button always launches the latest version.
  - **App Card Context Menu**: Added right-click context menu to app cards with Open, Update, Open Folder, View GitHub, and Delete actions.

- **Context Menu Git Version Manager (2.0.81)**:
  - **Separate Git Repos**: Configured independent Git snapshot tracking for `Launcher/` and `src/` with `.gitignore` exclusions for build intermediates (`obj/`, `build/`, `dist/`, `Apps/`, static `_internal/` DLLs).
  - **Nilesoft Shell `Version` Menu**: Added `imports/version.nss` and `cache/version_snapshots.nss` via `imports/version_manager.pyw` showing `Save Snapshot` at top and non-destructive tagged snapshots (`v1`, `v2`, ...) with active checkmarks and automatic `Return to Latest` unsaved state preservation.
  - **Build Auto-Snapshots**: Hooked `build_launcher.py` and `src/compile.bat` to record capped `[Auto]` snapshots on successful builds.

- **Restore Native "Open with" (2.0.80)**:
  - **Root Cause**: Default `modify(find='Open' vis=vis.remove)` is a contains-match (`FindPattern.h`), hiding "Open with", "Open file location", etc. `where.id=` does not filter (parsed as truthy `where`).
  - **Defaults Fixed**: `src/bin/imports/modify.nss` and `_internal/imports/modify.nss` now use exact `find='"Open"'`.
  - **Legacy Migration**: `restore_open_with_once` (`utils.py`) rewrites bare `find='Open'` to exact in `imports/modify.nss` once (stamp `open_with_restored.stamp`), then reloads shell. Scheduled at 2200ms in `launcher.pyw`.
  - **Rule Editor**: ID-based rules in `modify_widget.py` now default to exact match (full friendly name), not first-word contains.

- **High-DPI Coordinate & Region Normalization in `nativeEvent` (2.0.79)**:
  - **Screen-to-Client DPI Conversion**: Converted `WM_NCHITTEST` physical screen coordinates via Win32 `ScreenToClient` and divided by `devicePixelRatioF` before hit-testing. Resolves bug on monitors with scaling >100% (e.g. 4K at 150%) where raw physical coordinates passed directly into `mapFromGlobal` caused false resize border detection across window contents.
  - **Physical Window Region Scaling**: Fixed `_apply_rounded_mask` passing unscaled logical dimensions to GDI `CreateRoundRectRgn`, which caused HWND clipping to 1/DPR of the window on scaled monitors (cropping window contents, buttons, and borders). Sized region via `GetClientRect` physical bounds and scaled corner radius by `devicePixelRatioF`.

- **iMA Switcher Migration to Standalone Apps (2.0.78)**:
  - **Manifest Migration**: Moved `iMA Switcher` out of plugins into `apps.json` and `cache/apps.json` with repository `iMAboud/iMA-Switcher`.
  - **Purged from Plugins**: Excluded `iMA Switcher` from `FetchPluginsThread` in `plugin_workers.py` and pruned from `cache/plugin_registry.json` and `plugin_registry.py`.
  - **Direct Post-Download Execution**: Enhanced `launch_app` and `AppDownloadWorker` in `apps_manager.py` to immediately run the downloaded binary upon completion.

- **Apps Tab Update Flag & GitHub Repository Button (2.0.77)**:
  - **Version Update Detection**: Compared installed version (`version.txt`) against remote version (`apps.json`/GitHub). Kept version badge blue (`#8caaee`) while an update is available.
  - **"New" Update Flag**: Added purple (`#ca9ee6`) `"new"` badge next to version badge on app cards when remote version is newer.
  - **Circular GitHub Repo Button**: Added 30x30 circular GitHub vector button to the left of the folder/action buttons for apps with a `"github"` repository field in `apps.json`.
  - **Updated Apps Manifest**: Added Blink's repository (`https://github.com/iMAboud/Blink`) to `apps.json` and `cache/apps.json`. Retained local manifest fields across remote fetches.

- **Fast Startup & Smooth UI Loading Architecture (2.0.76)**:
  - **Eliminated Startup Heavy AST Import (C6)**: Replaced `from modify_widget import find_items_and_menus` in `check_tools_menu_in_file` with fast multiline regex, avoiding import of the 284KB `modify_widget` module during startup.
  - **Deferred Font GDI & Registry Registration (C2)**: Split `init_app_fonts()` into synchronous `QFontDatabase` loading for instant Qt UI rendering and deferred background thread for GDI registration, user fonts folder copies, and registry persistence.
  - **Deferred Plugin Reconcile & Hash Validation (C3)**: Preserved sync `registry.load()` for instant UI card display while deferring disk SHA1 hashing and staging cleanup to idle timer (`800ms`).
  - **Deferred Module-Level Tasks (C1, M1, M2)**: Moved executable cleanup, folder ownership checks, and NSS syntax migration off module import into timed background workers (2s, 5s, 8s).
  - **Staggered Page Pre-Warming (M3)**: Extended idle prewarm timers to 1500ms, 2500ms, 3500ms, and 4500ms, preventing main-thread stutter during the first 1.5s of launch.
  - **Cached Repaint Fonts & Pruned Redundancies (M7, C5, L2)**: Cached `QFont` in `NavTabButton`, removed duplicate `scroll_manager.attach_all` walk, and pruned dead duplicate `check_visible_cards`. Verified 54/54 automated tests pass.

- **Store Plugin Version Badges & 24h "New" Flag (2.0.75)**:
  - **Version Badges**: Added pill version badge (`v{version}`) next to every plugin title in the Store tab matching Apps tab styling (`#ea999c` peach/rose).
  - **Older Installed Version State**: When installed version is older than remote store version (`status == 'update_available'`), version flag dynamically renders in soft blue (`#8caaee`).
  - **24-Hour "New" Flag**: When a plugin is updated within 24 hours or today (`is_recently_updated` in `utils.py`), added an adjacent purple (`#ca9ee6`) `"new"` badge next to the version.
  - **Rebuilt Executable**: Rebuilt `dist/launcher.exe` and copied to `launcher.exe` (22.19 MB). Automated tests verified all 14 store badges, blue styling on outdated versions, and purple "new" badge on 24h updates.

- **Local Tab Plugin Rendering & Query Fix (2.0.74)**:
  - **Restored Local Plugins Query**: Fixed `UnboundLocalError`/`NameError` in `on_plugins_fetched` by querying `get_local_plugins_for_ui()` directly when `current_plugins_tab == "local"`.
  - **Grid & Tab State Retention**: Hardened `recalculate_plugin_grid` to clear layout widgets cleanly, prevented unwanted auto-reset to store tab in `load_cached_plugins_immediately`, and preserved all 6 local custom plugins.
  - **Rebuilt Executable**: Rebuilt `dist/launcher.exe` and copied to `launcher.exe` (22.18 MB). Verified tab switching across Store (14 plugins), Local (6 custom plugins), and Apps (Blink).

- **Standalone Apps Tab & Manifest Architecture (2.0.73)**:
  - **Apps Tab Navigation**: Added **Apps** pill tab to title bar segmented container alongside **Store** and **Local**. Retained container visibility across all plugin page sub-views.
  - **Standalone Apps Manifest**: Created `apps.json` and `cache/apps.json` tracking external applications (Blink) with metadata for GitHub release resolution, download targets, and auto-run settings.
  - **Engine & Worker Architecture**: Implemented `apps_manager.py` with `FetchAppsWorker`, `AppDownloadWorker`, and `AppIconWorker` to query GitHub `/releases/latest` for tags, download binaries into `Launcher/Apps/{app_name}/`, and launch executables on completion.
  - **CapsuleActionButton Extension**: Added `download`, `downloading`, `open`, and `launch` action states with vector play icon in `utils.py`.
  - **Fixed Downloader Method Collision**: Renamed standalone app downloader to `start_standalone_app_download` to prevent collision with launcher updater `start_app_download(download_url)`, fixing WinINet 12006 scheme error.

- **Corner Resizing Zone Balance & Button Shielding (2.0.72)**:
  - **Interactive Controls Priority**: Routed `WM_NCHITTEST` through `childAt` interactive controls check first; all buttons, line edits, combos, and `windowControlsPill` immediately return `HTCLIENT`, completely preventing corner resize interception over the close button.
  - **Balanced Resize Zones**: Set `corner` hit zone to balanced 20px and `border` to 8px; edges and corners are effortlessly grabbable while buttons remain 100% shielded.
  - **Rebuilt Executable**: Rebuilt `dist/launcher.exe` and copied to `launcher.exe` (22.15 MB). Verified hit-testing over close button returns `HTCLIENT` and edges/corners grab cleanly.

- **Update Loop, Theme Sync & Plugin Directory Preservation Fixes (2.0.71)**:
  - **Resolved Update Loop (Issue 1)**: Bumped `APP_VERSION` to `2.0.30`, added dynamic disk-backed `.version` / `version.txt` override resolution in `launcher.pyw`, short-circuited update checks when authoritative CDN `version.json` reports local is up to date (preventing fallthrough to stale GitHub Releases API edge cache), and added dismissal tracking for "Later" to prevent auto-check popup loops.
  - **Theme Auto-Healing & Fast Sync (Issue 2)**: Added auto-healing on launch and in `refresh_list()` when `theme/` contains 0 `.nss` files, accelerated downloads using `ThreadPoolExecutor(max_workers=6)` in `FetchThemesWorker`, hooked the Theme tab sync button to trigger GitHub sync, and added fallback directory resolution for `themes`/`theme`.
  - **Plugin Empty Folder Preservation (Issue 3)**: Removed destructive `shutil.rmtree(dir_path)` on empty directories in `reconcile_with_disk` (`plugin_registry.py`), ensuring newly created user folders inside `plugins/` are preserved instead of auto-deleted on launch.
  - **Rebuilt Executable**: Rebuilt `dist/launcher.exe` and copied to `launcher.exe` (22.15 MB). Automated tests verified empty folder preservation, update check non-triggering on 2.0.30, and full 77-file theme sync.

- **20 Curated Unique Themes & Rendered Previews (2.0.70)**:
  - **New Themes Collection**: Created 20 distinct themes in `new themes/` (`Catppuccin Mocha`, `Tokyo Night`, `Nordic Frost`, `Cyberpunk Gold`, `Dracula Velvet`, `Emerald Obsidian`, `Crimson Abyss`, `Solarized Dark`, `Amethyst Twilight`, `Sakura Blossom`, `Gold Luxury`, `Midnight Amber`, `Synthwave Sunset`, `Gruvbox Retro`, `Matcha Zen`, `Monochrome Clean`, `Deep Nebula`, `Coffee Caramel`, `Cyber Lime`, `Rose Pine`).
  - **NSS Configs & Screenshots**: Generated complete `.nss` configurations and rendered 140x138 `.png` context menu screenshots with drop shadows, custom item selections, borders, and typography for every theme.

- **Win32 GDI Rounded Window & Zero-Ghost DWM Region (2.0.69)**:
  - **DWM 8px Frame Ghost Elimination**: Set `DWMWA_WINDOW_CORNER_PREFERENCE = 33` to `DWMWCP_DONOTROUND = 1` in `_setup_native_window` and removed `border-radius: 15px` from `QWidget#sidePanel` in `style.css`, completely eliminating the less-rounded ghost DWM frame behind the window.
  - **Win32 `CreateRoundRectRgn` Regional Masking**: In `_apply_rounded_mask`, applied GDI `CreateRoundRectRgn` (28px radius) to `HWND` via `SetWindowRgn` when normal, and removed it (`SetWindowRgn(hwnd, 0, True)`) when maximized.
  - **Instant State Synchronization in `WM_SIZE`**: Added `WM_SIZE` and `WM_EXITSIZEMOVE` handlers in `nativeEvent` to dynamically sync the rounded region across Aero Snap, title bar drag-to-restore, and resize cycles.
  - **Corner Resize Hit-Zone Alignment**: Aligned `WM_NCHITTEST` diagonal corner resize hit-zones with `_corner_radius` (28px).
  - **Rebuilt Executable**: Rebuilt `dist/launcher.exe` and copied to `launcher.exe` (22.14 MB). Automated tests verified initial `1112x750` with complex region (3), maximized `1920x1032` with no region (0), and restore with region (3).

- **Non-Layered Native Window, Full Aero Snap & Maximize Architecture (2.0.68)**:
  - **Eliminated `WS_EX_LAYERED` (0x00080000)**: Removed `WA_TranslucentBackground` and explicitly stripped `WS_EX_LAYERED` from `GWL_EXSTYLE`. Layered windows break Windows DWM maximize calculations, causing the window to snap to `(0, 0)` without resizing and disabling native drag-to-restore.
  - **DWM Native Non-Client Frame**: Native DWM now handles rounded corners (`DWMWCP_ROUND`) and aero drop shadows (`DwmExtendFrameIntoClientArea`) directly without synthetic layered masking.
  - **Standardized `WM_NCCALCSIZE` Deflation**: Removed conflicting `WM_GETMINMAXINFO` work-area overrides; Windows calculates native maximize bounds and `WM_NCCALCSIZE` deflates by sizing border metrics (`SM_CXSIZEFRAME + 92`), guaranteeing exact work-area fit without clipping or taskbar overlap.

- **Native Window Maximize, Work-Area Inset & Drag-to-Restore Fix (2.0.67)**:
  - **Removed `WM_SYSCOMMAND` Interception**: Removed `SC_MAXIMIZE`/`SC_RESTORE` interception in `nativeEvent`, allowing Windows DWM to process maximize/restore commands natively via `DefWindowProc`. Fixes native drag-to-restore and prevents re-entrant toggle loops.
  - **Dynamic Work-Area Insets in `WM_NCCALCSIZE`**: Populated `params.rgrc[0]` directly with `mi.rcWork` when zoomed, ensuring maximized client area matches monitor work area without taskbar overlap or title bar clipping.
  - **Work-Area Constraints in `WM_GETMINMAXINFO`**: Set `ptMaxPosition`, `ptMaxSize`, and `ptMaxTrackSize` dynamically from monitor info to ensure proper multi-monitor maximized positioning.
  - **Maximized State Preservation in `bring_to_focus`**: Added `_was_maximized_before_minimize` tracking to restore maximized state when un-minimizing.
  - **Rebuilt Executable**: Rebuilt `dist/launcher.exe` and `launcher.exe` (22.14 MB). Automated tests verified initial `1112x750`, maximized work-area `1920x1032` (`IsZoomed: 1`), and restore.

- **True Native Windows Maximize & Drag-to-Restore Fix (2.0.66)**:
  - **Stripped `WS_POPUP` from Window Style**: In `_setup_native_window`, stripped `WS_POPUP` (`0x80000000`) before applying `WS_THICKFRAME | WS_CAPTION | WS_MAXIMIZEBOX | WS_MINIMIZEBOX | WS_SYSMENU`. `WS_POPUP` conflicted with `WS_CAPTION`, causing Windows 11 DWM to reject native `SW_MAXIMIZE` and snap the window to `(0, 0)` with `SWP_NOSIZE`. Removing `WS_POPUP` converts the window into a true Win32 overlapped window.
  - **Native Win32 Maximize & Drag-to-Restore**: Restored native `showMaximized()` and `showNormal()` in `toggle_maximize()`. Windows DWM now natively manages the maximized state (`IsZoomed: 1`), enabling full native title bar drag-to-restore (dragging down automatically un-maximizes and restores normal size under cursor) and Aero Snap.
  - **Verified Standalone Executable**: Stopped stale background processes, rebuilt `dist/launcher.exe` and updated `launcher.exe` (22.14 MB). Automated click tests verified initial size (`1112x750`), native maximize (`IsZoomed: 1`), and restore (`IsZoomed: 0`).

- **Cloud Sync Google OAuth IDNA Encoding Fix (2.0.63)**:
  - **FQDN Lookup Bypass**: Subclassed `HTTPServer` with `OAuthServer` in `cloud_sync.py`, overriding `server_bind` to bypass `socket.getfqdn(host)`. Prevents reverse DNS queries and Python `_socket` hostname encoding via `idna` codec during local loopback bind.
  - **PyInstaller IDNA & Unicodedata Bundling**: Removed `idna` and `unicodedata` from `excludes` and added `encodings.idna` and `unicodedata` to `hiddenimports` in `launcher.spec` and `build_launcher.py`. Rebuilt `launcher.exe` ensuring runtime availability of standard library IDNA codecs.

- **Native Maximize & Top-Left Snap Bug Fix (2.0.62)**:
  - **Removed HTMAXBUTTON DWM Conflict**: Removed artificial `HTMAXBUTTON` non-client hit-testing from the custom maximize button. In Windows 11 (build 26200+), DWM Snap Layouts intercepted clicks on `HTMAXBUTTON` and snapped the window into the top-left quadrant instead of maximizing.
  - **Clean Maximize/Restore Toggle**: Button click routes directly to `toggle_maximize()`, ensuring reliable full work-area maximization and restoration. Title bar double-click and Aero Snap drag continue working natively.
  - **Max Tracking Sizing**: Configured `mmi.ptMaxTrackSize` in `WM_GETMINMAXINFO` to allow seamless multi-monitor work-area tracking.

- **NSS Sync & Tab-Switching Parsing Fixes, PillNotification Auto-Dismiss (2.0.61)**:
  - **Zero-Modification Tab Switching**: Removed `os.utime()` file touching from `trigger_shell_reload` in `utils.py`, eliminating spurious `QFileSystemWatcher` file change events during reloads or tab navigation.
  - **Content Snapshot Diff Hardening**: Added snapshot content comparisons across `modify.nss`, `theme.nss`, `shell.nss`, `imports/`, `theme/`, and `plugins/` in `_handle_file_sync`, preventing false "Synced Imports" and "Synced Plugins & Icons" toasts when file contents have not changed. Excluded `cache/icons` from the file watcher.
  - **Eliminated Redundant Tab AST Parsing**: Guarded `ThemeSwitcherWidget.showEvent` with `_initial_theme_sync_done` to run background theme downloads only once on initial view. Guarded `ModifyWidget._switch_tab` with `_is_loaded` checks to prevent re-scanning all project `.nss` files on tab switches.
  - **PillNotification Hang Prevention**: Fixed notification hang bug by clearing `_active_anim` on expand finish, running hold timer unconditionally, fixing `leaveEvent` timer restart, and adding an absolute 5-second auto-collapse fallback.

- **Fast Startup Tab Animation & Transition Race Condition Hardening (2.0.60)**:
  - **AnimatedStackedWidget Race Condition Prevention**: Added `_target_idx` tracking and duplicate-target ignore; immediately hides and detaches canceled canvases (`hide()`, `setParent(None)`) to prevent ghost canvas captures during rapid tab switches.
  - **Pre-Activation & Opaque Transition Backing**: Forces widget layout activation and posted events dispatch before snapshot grabs, preventing unlaid-out captures; added `#121212` opaque backing under incoming pixmaps in `SlideFadeCanvas` to prevent old tab bleed-through.
  - **Animation-Aware Idle Pre-Warming**: Staged idle prewarm timers (`_prewarm_modify_page`, `_prewarm_theme_page`, etc.) now check `is_animating()` and defer 300ms, eliminating main-thread stutters during active tab switches.
  - **ModifyWidget Styled Background**: Added `WA_StyledBackground` and `#121212` root background to `ModifyWidget`.

- **Native Maximize Work-Area, Corner Resizing & Maximize Pointing Cursor (2.0.59)**:
  - **WM_GETMINMAXINFO & Work-Area Maximize**: Added `WM_GETMINMAXINFO` handling to populate `ptMaxSize` and `ptMaxPosition` with monitor work area; updated `WM_NCCALCSIZE` to subtract frame borders when maximized for exact work-area alignment without off-screen clipping.
  - **Diagonal Corner Resizing**: Added dedicated 20px diagonal corner hit zones in `WM_NCHITTEST` (`HTTOPLEFT`, `HTTOPRIGHT`, `HTBOTTOMLEFT`, `HTBOTTOMRIGHT`) before edge checks, fixing corner resize cursor detection on rounded corners.
  - **Maximize Pointing Hand Cursor & Hover**: Intercepted `WM_SETCURSOR` on `HTMAXBUTTON` returning `IDC_HAND` to match Minimize/Close button cursor; synchronized `hovered="true"` state and dynamic stylesheet polish for `#5ecaa8` hover feedback.

- **Native Windows Snapping, Sizing & macOS Pastel Controls (2.0.58)**:
  - **Native Win32 Sizing & Snapping**: Enabled `WS_THICKFRAME | WS_CAPTION | WS_MAXIMIZEBOX | WS_MINIMIZEBOX` and DWM frame extension, activating native Aero Snap (top edge maximize, left/right split, corner quadrants, Win+Arrow shortcuts) and hardware-accelerated window resizing across all 4 edges and corners.
  - **Windows 11 Snap Layouts & NCCALCSIZE**: Implemented `HTMAXBUTTON` hit-testing for the maximize button, enabling the native Windows 11 Snap Layouts menu on hover; handled `WM_NCCALCSIZE` monitor work-area sizing to eliminate taskbar and off-screen clipping when maximized.
  - **macOS Circular Pastel Controls**: Redesigned window control buttons into circular 14px pastel dots in pill container matching Catppuccin / macOS Frappé palette (Yellow `#c6a853` minimize, Mint Green `#4ab494` maximize, Coral Red `#da7d9b` close) with hover/pressed feedback.

- **Mouse Gallery 60 FPS Smooth Scrolling & Persistent Disk Caching (2.0.57)**:
  - **Bundled Atlas Priority in `load_previews`**: Fixed installed cursor cards bypassing the bundled preview atlas (`cursors_previews.json`). Cards now check `get_theme_preview_pixmap` first, eliminating repetitive binary `.cur`/`.ani` extraction, directory walks, and INF parsing for 338+ packs (99.1% coverage) on the main thread.
  - **Disk-Backed Preview & Role Caching**: Added persistent disk caching in `PREVIEWS_CACHE_DIR` for extracted `.cur` pixmaps (`cur_local_{safe_name}_{role}_{size}.png` and `cur_{hash}_{size}.png`) and theme roles (`theme_roles.json`), eliminating all binary decoding and directory walks across app relaunches (loads in <0.05ms).
  - **Memory QPixmap Cache & Fast Lookups**: Added `_THEME_PIXMAP_CACHE` storing pre-scaled `QPixmap` objects to bypass redundant `QImage.scaled` and format conversions; added `_EMBEDDED_PREVIEWS_LOWER` for O(1) case-insensitive lookups and negative lookup caching for missing cursor roles.
  - **Removed UI-Blocking Synchronous PNG Writes**: Eliminated synchronous `img.save(..., "PNG")` from the GUI thread during scroll view lookups.
  - **Direct Coordinate Viewport Testing**: Replaced recursive `card.mapTo(vp, ...)` tree walking in `check_visible_cards` with direct `card.y() - scroll_y` coordinate math and early break past the viewport buffer.
  - **Progressive Idle Pre-Rendering & Throttling**: Added `_schedule_idle_render` batching 36 cards every 45ms during idle time to complete full gallery layout without scroll frame drops. Debounced viewport check timer from 10ms to 25ms. Average scroll frame time reduced to 14.91 ms (solid 60 FPS).

- **Cursor Gallery Truncation Fix & Tab Switch Latency Optimization (2.0.56)**:
  - **Cursor Gallery Infinite Chunk Fix**: Fixed `_check_and_load_more_chunks` in `cursor_widget.py` using `grid_layout.heightForWidth(vp_w)` instead of misleading `sizeHint()`. Parented `empty_container` to `grid_widget` avoiding GC memory drops during `processEvents`. Raised initial chunk to 24 cards and reset scroll on category tab switch to prevent scrollbar lockouts.
  - **Zero-Delay Startup Tab Pre-Warming**: Added staged idle background timers (`_prewarm_modify_page`, `_prewarm_theme_page`, `_prewarm_settings_page`, `_prewarm_theme_subtabs`) in `launcher.pyw`. Instantiates heavy widget trees during idle periods so clicking sidebar tabs triggers 60 FPS animated transitions instantly.
  - **Lazy Add/Builder Tab Loading**: Refactored `ModifyWidget` in `modify_widget.py` to lazy-load `MenuBuilderWidget` on first Add tab activation or property access, reducing initial `ModifyWidget` instantiation overhead from 390ms+ to ~15ms.

- **Scheduled Cloud Sync, Conflict UI & Animated Transitions (2.0.55)**:
  - **Directional Slide + Fade Page Transitions**: Built `SlideFadeCanvas` and `AnimatedStackedWidget` in `utils.py` executing silky directional sliding (70px glide in tab direction) and simultaneous crossfading (240ms OutCubic) via dual pixmap blitting. Applied across main sidebar tabs (Plugins/Modify/Theme/Settings), Theme sub-tabs (Themes/Editor/Mouse), and Modify sub-tabs (Edit/Add).
  - **Daily Auto Cloud Backup**: Added `"auto_cloud_backup": True` setting switch and startup timer (3000ms) triggering silent background backups every 24h when logged into Google Drive.
  - **Last Backup Timestamp**: Added dynamic backup timestamp in Settings Sync section (`Last backup: <date/time>` or `Never`), updating automatically after backups.
  - **Sync Conflict Resolution UI**: Created `CloudSyncConflictDialog` in `utils.py` and pre-restore conflict inspection in `cloud_sync.py`, displaying diffs for modified local files and offering Keep Local, Restore Selected, or Restore All.
  - **Plugin Ratings & Downloads Evaluation**: Verified GitHub API only tracks downloads on Releases and cannot track repo code retroactively or accept ratings without an external backend; canceled Feature 1 per specification.

- **Top Title Bar Animated Pill Notification (2.0.54)**:
  - **PillNotification Overlay**: Created `PillNotification` in `utils.py` floating over the title bar as a frameless translucent overlay child widget, avoiding layout constraints and clipping.
  - **Expand & Glide Animation**: Appears initially as a circular badge with the icon, expands symmetrically from both sides with text fade-in, holds for 3 seconds (pausing on mouse hover), collapses back to a circle with text fade-out, and smoothly glides up while fading out.
  - **Cross-Component Event Triggers**: Hooked notifications for plugin installation and uninstallation in `on_operation_finished`, theme selection in `_on_theme_picked`, and cursor changes in `_on_cursor_changed` with corresponding icons and titles.
  - **Legacy Status Text Replacement**: Removed old `title_status_label` from the title bar; routed `show_sync_status` and status messages directly to `PillNotification` with single/two-line support and fallback icon handling.
  - **Sync Message Conflict Suppression**: Blocked file-watcher background sync messages (`Synced Imports`, `Synced Theme`, etc.) from canceling or overwriting active/recent user action notifications.
  - **Interactive Hit Testing**: Integrated with `nativeEvent` to prevent title bar drag interception and allow click-to-dismiss.

- **NSS Expression Safeguarding & Corrupted Args Auto-Fix (2.0.53)**:
  - **Expression Safeguarding in `format_nss_value`**: Fixed unintended quoting and backslash-escaping of code expressions (`if(...)`, `@if(...)`, function calls, arrays `[...]`, nilesoft objects) in `args`/`arg` and other properties. Expressions are now emitted unquoted and preserved during icon, title, and item modifications.
  - **Enclosed String Preservation**: Added `is_enclosed_string` validator to ensure already-quoted arguments and paths never receive nested quotes or redundant quote-escaping during re-serialization.
  - **Corrupted Expression Healing**: Added `heal_corrupted_nss_expr` in `nss_parser.py` and `_fix_corrupted_expressions` in `NSSAutoFixer` (`utils.py`) to auto-detect and heal escaped quote expressions (e.g. `args='\'if(...)\''`) during AST parsing and syntax auto-fixing.
  - **Regression Test Coverage**: Added expression and argument formatting safeguards in `tester.pyw` (`test_format_value_safeguards`).

- **Details Popup Header Buttons & Styled Pill Tooltips (2.0.52)**:
  - **Details Header Buttons Paint Fix**: Resolved `NameError` on missing `QRectF` and `QPainterPath` in `plugin_workers.py` causing `PopupHeaderButton.paintEvent` to abort silently, restoring visibility and interactivity for **Close**, **Open Plugin Directory**, and **Edit Item/Menu** buttons.
  - **High-DPI & Vector Fallback Icons**: Added device pixel ratio scaling (`devicePixelRatioF`) for crisp high-DPI rasterization and fallback rendering to vector `"✕"` and MDL2 icons (`0xED25`, `0xE70F`), plus 6px button spacing.
  - **Styled Pill-Shaped Tooltips**: Overhauled `QToolTip` across `style.css`, `_internal/style.css`, `modify_widget.py`, `menu_builder_widget.py`, and `svg_manager.py` with 14px border-radius, `#18181c` surface, `1.5px solid rgba(231, 130, 132, 0.7)` specular border, bold typography, and 5px 15px padding.
  - **Window Translucency & Corner Elimination**: Added `Qt.WA_TranslucentBackground` in `AutoHideScrollManager.eventFilter` for `QLabel` tooltip windows to eliminate black corner clipping on Windows.

- **Unified Button & Label Typography (2.0.51)**:
  - **PillPushButton Unification**: Upgraded default typography to `QFont("Google Sans", 11, QFont.Bold)` with explicit painter bold styling and font metrics calculation. Unifies **Save**, **Reset**, **Backup**, **Restore**, **Import**, **Check for Update**, **Apply**, **Save Changes**, **Cancel**, **Yes**, **No**, and rule action buttons across all pages and modals.
  - **Sync Header Alignment**: Changed label text to **Sync** and matched font size to **11pt** (`Google Sans 11 Bold`), resolving point-vs-pixel scale discrepancy. Matched container to 30px pill height with 15px radius.
  - **Settings Typography**: Bolded "Settings" title (26px bold), "V {VERSION}" label (14px bold), and setting section row headers (15px bold).
  - **Modal & Popup Buttons**: Unified button stylesheets across `ModernDialog`, `AccountProfileDialog`, `CustomConfirmDialog`, `AddThemeDialog`, `LocalIconTintDialog`, `ManualSyncConflictDialog`, and `style.css` (`QPushButton` base, `#installButton`, `#updateButton`, `#uninstallButton`, `#dangerBtn`, `#cancelBtn`, `#secondaryBtn`).

- **Google Sans English, Marhey Arabic & UnifiedFindInput Vertical Balance (2.0.50)**:
  - **Google Sans App Typography**: Switched English font across the entire launcher to Google Sans (`GoogleSans-Regular.ttf`, `GoogleSans-Medium.ttf`, `GoogleSans-Bold.ttf`), falling back cleanly to Marhey for Arabic text. Enhanced font weight and sizing to bold across plugin card names (14px bold), top app title "iMA Menu" (18px bold), action buttons (`CapsuleActionButton` 11.5px bold), sidebar tabs (`NavTabButton` 11px bold), segmented tabs (`PillTabButton` 11px bold), and page/dialog titles.
  - **UnifiedFindInput Vertical Centering**: Resolved Arabic text clipping and bottom-burial in `UnifiedFindInput` by adjusting layout margins to `(4, 0, 4, 0)` and line-edit padding to `0px 4px 4px 8px;`, balancing top and bottom breathing space (11px top / 12px bottom) without increasing overall input height.
  - **Marhey Arabic Integration**: Bundled "Marhey" (Regular & Bold) and configured `QFont.insertSubstitutions` so `Google Sans`, `Segoe UI`, and UI fonts automatically render Arabic text in Marhey.
  - **Modern English & Arabic Google Fonts**: Bundled 17 clean TTF font files in `fonts/` and `_internal/fonts/` (`Google Sans`, `Marhey`, `Cairo`, `Inter`, `Outfit`, `Poppins`, `Plus Jakarta Sans`, `JetBrains Mono`).
  - **GDI & Native Shell Registration**: Added `init_app_fonts()` in `utils.py` registering all fonts with `QFontDatabase`, Windows GDI `AddFontResourceExW`, and per-user Windows fonts registry (`HKCU\Software\Microsoft\Windows NT\CurrentVersion\Fonts`) so Nilesoft Shell (`shell.dll` in Explorer) can immediately render them in context menus without admin rights.
  - **Theme Editor Font Options**: Replaced 16 hardcoded fonts with `get_supported_theme_fonts()` providing 100+ organized, clean, scalable fonts (modern Google fonts, Arabic typefaces, core Windows UI sans-serif, monospace, serif, display, and dynamically enumerated clean system fonts).
  - **Live Typeface Previews in Dropdown**: Enhanced `ModernComboDelegate` and `ModernComboBox` to render font names in their actual typeface preview with peach badges (`#ef9f76`) for Arabic and soft blue (`#8caaee`) for English fonts.
  - **App Stylesheet Sync**: Updated `style.css` and `_internal/style.css` font families to `'Google Sans', 'Marhey', 'Segoe UI Variable Display', 'Segoe UI', sans-serif`.

- **Mouse Cursors Gallery Latency Optimization (2.0.49)**:
  - **Eliminated Duplicate Render Cycle**: Added identity check `if self.catalog and self.catalog == catalog: return` in `_on_catalog_fetched` to prevent `FetchCatalogWorker` from destroying and re-rendering all cards when emitting the already-loaded local cached catalog.
  - **Removed Cascade Runaway Timers**: Removed recursive `QTimer.singleShot` from `_render_next_chunk` and replaced synchronous `_check_and_load_more_chunks` call in `showEvent` with a deferred 150ms timer; updated viewport fill check to `(sb.maximum() > 0 and sb.value() >= sb.maximum() - 600) or (vp_h > 0 and grid_h > 0 and grid_h < vp_h)`.
  - **Tuned Initial Render Batch**: Reduced initial synchronous chunk from 24 to 12 cards (completely filling viewport without excess invisible widgets), loading subsequent chunks seamlessly on scroll.
  - **Cached Vector Star Icons**: Cached 5-point vector star `QIcon` objects in `_STAR_ICON_CACHE`, eliminating repetitive trigonometry math and `QPainterPath` allocations.
  - **Latency Benchmark Pass**: Reduced `[11. Mouse Cursors] Mouse Cursors gallery initialization` latency from 221.78 ms to 97.06 ms (`Status: PASS` under 120 ms threshold) with zero feature loss and zero stutter.

- **Reliability, Performance & Networking Architecture Hardening (2.0.48)**:
  - **WinINet Session Re-use & Keep-Alive**: Created singleton session handle `_get_inet_session()` in `github_client.py` with thread-safe lock and `atexit` cleanup; eliminates repeated TCP/TLS handshakes across API calls.
  - **Tree SHA 5-Min TTL Cache**: Added `_tree_sha_cache` in `github_client.py` to prevent burning GitHub's unauthenticated 60 req/hr rate limit.
  - **Atomic File Downloads**: Refactored `download_file` to stream into `.tmp` file and perform `os.replace` on verification; prevents corrupt/half-written assets on cancel or error.
  - **Strict SSL Validation with Fallback**: Removed global SSL ignore flags from default requests; validates certificates by default with graceful fallback on CA/date errors.
  - **Memory Optimization**: Stored `_tree_data` once on `PluginLogic._cached_tree_data` instead of duplicating 1-5MB tree payloads across all plugin dicts in memory.
  - **Non-blocking Async Uninstallation**: Introduced `UninstallWorker` running in background `QThread` for `uninstall_plugin` and `delete_local_plugin`; eliminates UI freezes during folder removal, process termination, and recycle bin moves. Fixed thread cleanup order and `CapsuleActionButton.set_state` custom text clearing to ensure button resets cleanly to "Install".
  - **Orphan Thread Prevention**: Parented `GlobalTintWorker` `QThread(self)` and added `worker.deleteLater` on finished signal in `launcher.pyw`.

- **Zero-Latency Auto Updates & Plugin Auto-Install Pipeline (2.0.47)**:
  - Added non-blocking startup update check `_auto_check_app_update` (1500ms idle timer) running `UpdateWorker` in a background `QThread` with 0ms launch impact.
  - Removed 24-hour rate limit barrier in `check_app_update` so startup update checks run reliably when `auto_check_updates` is enabled.
  - Guarded `ver_label` and `update_btn` against `AttributeError` when update popup triggers without opening Settings page.
  - Fixed `PluginRegistry._check_file_changes` bug that previously cleared `update_available` status when file diff was empty despite higher remote versions.
  - Added `_auto_update_available_plugins` auto-queuing all pending plugin updates in background upon manifest fetch and on settings toggle.

- **Items Tab Deactivation & Bundle Exclusion (2.0.46)**:
  - Hid segmented "Items" sub-tab in `launcher.pyw` (`plugins_sub_tab_container.hide()`, `switch_plugins_sub_tab` guard).
  - Disabled background `items_manager` preloading and reading of `cache/items.json` in `launcher.pyw` and `items_manager.py`.
  - Excluded `cache/items.json`, `items_widget`, and `items_manager` from PyInstaller build configs in `build_launcher.py` and `launcher.spec`.
  - Disabled `imports/items.nss` creation and registration in `items_manager.py`; removed `import 'imports/items.nss'` from `shell.nss`.
  - Preserved files in workspace for offline testing and future bugfixes.

- **NSS Mode Syntax Migration (2.0.45)**:
  - Added one-time migration [`fix_nss_mode_syntax_once`](file:///d:/Program%20Files/iMA%20Menu/Launcher/utils.py) in [`utils.py`](file:///d:/Program%20Files/iMA%20Menu/Launcher/utils.py) invoked on launcher startup in [`launcher.pyw`](file:///d:/Program%20Files/iMA%20Menu/Launcher/launcher.pyw).
  - Cleanly repairs unquoted `mode=multiple` to `mode='multiple'` in `shell.nss` and `imports/file-manage.nss`.
  - Stamped via `CACHE_DIR/nss_mode_syntax_fixed.stamp` to execute once; safely skips files that already have single/double quotes.
  - Reinforced `NSSAutoFixer.fix_line()` and `NSSAutoFixer.fix_content()` to auto-heal unquoted `mode=multiple`.

- **Regex Inline Flag Bugfix (2.0.44)**:
  - Fixed `re.error: global flags not at the start of the expression` crash in `NSSAutoFixer.fix_content()` (`utils.py` L280) by moving `(?i)` from mid-group `((?i)\b...)` to pattern start `(?i)(\b...)`.

- **Standalone Items & Snippets Editor Tool (2.0.43)**:
  - **Standalone Developer Editor (`items_editor.pyw`)**: Built PyQt5 developer tool to browse, add, edit, and manage catalog snippets in `cache/items.json`.
  - **"Test All in Shell" & Real-Time Engine Audit**: Added "🚀 Test All in Shell" across top header, editor toolbar, and inspection frame to validate all catalog snippets and active shell files in native shell engine.
  - **Granular Shell.log Diagnostic Report (`ShellTestAllReportDialog`)**: Built modal table mapping `shell.log` errors/warnings to exact file, snippet ID/title, relative line in snippet, absolute line, column, and diagnostic message.
  - **Live Code Inspection & Cursor Navigation**: Displays offending line preview; double-clicking error jumps directly to snippet and line in `CodeEditor`. Supports single/bulk auto-fix, immediate shell re-test, and Markdown report export.
  - **Zero Test Pollution Isolation**: Test blocks cleanly injected with line-mapping into `imports/items.nss` and immediately purged post-reload via `ItemsManager`.
  - **Uncopyable Line Numbers Gutter**: Added VS Code style line numbers area on the code editor, preserving unpolluted text selection when copying code, with active line highlight and cursor line tracking.
  - **Single-Click & Bulk Auto-Fix with Revert**: Added `auto_fix_nss_code` healing unclosed quotes, unbalanced parens/brackets/braces, and duplicate quotes; includes single-click "↺ Revert Fix" and "🩹 Auto-Fix All Items" for catalog-wide repair.
  - **Live Real-Time Shell.log Testing**: Added "🚀 Test in Shell" to inject snippet into `imports/items.nss`, trigger `shell.exe -reload`, and parse real-time `shell.log` errors/warnings with auto-navigation to line.
  - **Live Nilesoft Shell AST & Syntax Inspector**: Real-time bracket/quote balance validation with line/column reporting and hierarchical AST tree view (`QTreeWidget`).
  - **Live JSON & Pure NSS Output**: Dynamic real-time preview of exact JSON payload and comment-stripped NSS statements.
  - **Atomic Persistence & Backup**: Formats `cache/items.json` with 2-space indentation and writes `.bak` backups before atomic swap.
  - **Permanent Snippet Deletion**: Updated `_on_delete_snippet` to atomically purge deleted items with their IDs and blocks from `cache/items.json` on disk with `.bak` backup and remove from `items.nss`.
  - **Quick Test Item Deletion & Shell Isolation**: Added top-bar "🗑️ Delete Test Item" button and reliable cleanup in `_clear_test_item_from_shell`; scoped `shell.log` error detection strictly to the test payload line range.
  - **EOF Menu Parser Compatibility**: Aligned `validate_nss_syntax` in `utils.py` and `items_editor.pyw` with Nilesoft Shell C++ engine (`if (!imported && !l->eof) expect_closeCurly()`), preventing false-positive unclosed brace errors.
  - **Category Group Management & Empty Category Preservation**: Retained empty category groups in tree view with `(Empty category)` indicator; added `+ Category` creation, direct category deletion (`_on_delete_category`), and tree right-click context menu.
  - **Standalone Developer Isolation**: Removed "✎ Edit Catalog" button from `ItemsWidget` top bar to keep `items_editor.pyw` strictly developer-facing standalone.

- **Plugins: Items UI & Edit Interactivity Hardening (2.0.42)**:
  - **Human-Readable Snippet Catalog**: Reformatted `cache/items.json` with 2-space indentation (63,478 lines); verified 100% data fidelity and launcher parser compatibility.
  - **ImportEditorDialog Integration**: Hooked native `ImportEditorDialog` for items and menus with AST property formatting.
  - **Consistent Edit Button Styling**: Standardized circular 28x28 button with `\uE104` pencil glyph and `#e78284` styling.
  - **Reactive State & Instant UI Sync**: Immediate widget tree detachment; separator exclusion; fallback snippet item checks.
  - **Focus Outline Elimination**: Disabled label mouse events and text interaction; removed outline borders in `style.css`.

- **Plugins: Items Performance & Dynamic Layout Containment (2.0.41)**:
  - **Zero Startup Delay & Fast Open**: Items page lazy-instantiated upon sub-tab selection; idle background preloading (`_preload_items_manager`); progressive card batching (14 initial cards in ~9ms, then idle background batches).
  - **Eliminated Race Condition & Visual Overlap**: Explicitly hide `scroll_area` and individual cards when Items sub-tab is active; guard `render_current_plugins_tab` from forcing `scroll_area.show()` during background updates; added opaque backgrounds (`#141416`) to Items gallery and detail views.
  - **Pruned Catalog & Clean Menu Headers**: Pruned 2 non-item desktop theme scripts and nested menu tree duplication, reducing `cache/items.json` from 33MB to 3.3MB (19ms parse).
  - **Dynamic 2-Column Containment**: Bounded `SnippetCard` with `minimumSizeHint` (`QSize(220, 105)`), `setMinimumWidth(0)`, unconstrained `desc_lbl` (`QSizePolicy.Ignored`), disabled horizontal scroll (`ScrollBarAlwaysOff`), and 50/50 column stretch.
  - **User-Friendly Naming & Branding**: Shortened all descriptions (<10 words), sanitized raw tech/DLL titles (`str.res`, `curl`, variables), and replaced all "Nilesoft Shell" occurrences with "iMA Menu".
  - **Pure Commentless NSS**: Enforced clean comment-free statement writing in `imports/items.nss` via `ItemsManager`.

- **Plugins: Items Tab & Snippet Catalog Integration (2.0.40)**:
  - Added segmented **"Plugins - Items"** sub-tab inside Plugins view (`pillTabContainer`) matching Modify tab pattern.
  - Extracted, structured, and cached 95 snippets across 14 categories from `RubicBG/Nilesoft-Shell-Snippets` into `cache/items.json`.
  - Built `ItemsManager` (`items_manager.py`) handling atomic snippet/menu/item additions, removals, and updates in `imports/items.nss` (auto-imported in `shell.nss`).
  - Built `ItemsWidget` (`items_widget.py`) featuring 2-column acrylic card gallery, category filters (`FlowLayout`), search, and drill-down hierarchy explorer.
  - Implemented selective menu/item installation with visual distinction (bright added items vs dimmed unadded items).
  - Added quick item editor modal (`ItemQuickEditDialog`) and Before/After update diff modal (`SnippetDiffDialog`).
  - Updated `build_launcher.py` and `launcher.spec` to include `cache/items.json`, `items_widget`, and `items_manager`.

- **Add Tab & NSS Configuration Overhaul (2.0.39)**:
  - Fixed argument quote auto-stripping in `nss_parser.py` and `menu_builder_widget.py`.
  - Fixed code editor manual edit saving with `_code_manually_edited` flag and direct parsing.
  - Redesigned target modes into **"One Action"** and **"Sequence Actions"**.
  - Added Action Type selector, dual File/Folder browsing, and collapsible **Advanced Options** drawer.
  - Added native controls for **Admin** (`admin=true`), **Window State** (`window=min|max|hidden`), **Working Dir** (`dir`), and **Wait** (`wait=true`) across both **One Action** and **Sequence Actions** modes in a spacious, dedicated Execution row.
  - Added curated argument presets for window half-snapping and multi-monitor placement.
  - Fixed draft false-positives via `shell.log` offset tracking and exact item line interval mapping.

- **Host Environment & System Optimization**:
  - Resolved Valorant matchmaking freeze: purged broken GameBar IFEO hijack (`systray.exe`), disabled GameBar policies, and disabled orphaned `SteelSeries_Sonar_VAD` driver.
  - Isolated Windhawk hooks from games and Discord via process exclusion settings.
  - Optimized Discord: reverted to standard audio subsystem, enabled background EcoQoS, disabled devtools logging.
  - Repaired services: disabled broken `luafv` (resolving Event 7000) and set `LanmanWorkstation` to manual (resolving VSS 8193).
  - Cleaned & deduplicated System/User PATH (removed broken `Launcher\lib` entries).
  - Debloated telemetry & disk logging: disabled NTFS Last Access updates, ETW autologgers, and appraiser tasks.
  - Completed read-only DPC latency, event fault, and timer resolution deep-dive scan.

- **Automated Diagnostic & Latency Tester (2.0.38)**:
  - Created standalone QA test harness (`tester.pyw`) with 13 test suites (54 tests).
  - Evaluates NSS syntax, dialogs, buttons, navigation, and latency with zero host file touches.
  - Logs execution times to `test_log.txt` and `cache/test_history.json`.
  - Added dark PyQt5 dashboard with benchmark KPIs, history comparison, and traceback inspector.
  - Fixed `CapsuleActionButton._get_display_text` string return type in `utils.py`.
  - Configured `setQuitOnLastWindowClosed(False)` and neutralized background timers in `tester.pyw`.
  - Redirected module path constants (`PLUGIN_REGISTRY_FILE`, `SETTINGS_FILE`, etc.) to sandbox, preventing registry leakage.

- **Zero-Risk Codebase Optimization & Dead Code Pruning (2.0.37)**:
  - Removed obsolete standalone `svg_manager.py` (164 lines) and stale `fatal_error.log`.
  - Pruned ~745 lines of unused legacy widget classes in `modify_widget.py` (`ImportedItemCard`, `IDEntryWidget`, `ModificationRuleCard`, `InlinePalettePopup`, etc.).
  - Pruned dead methods and unused imports across `launcher.pyw`, `utils.py`, `cursor_widget.py`, `nss_parser.py`, and `plugin_registry.py`.
  - Excluded `libcrypto-3.dll` (5.23 MB) from PyInstaller build configuration in `build_launcher.py` and `launcher.spec`.
  - Hoisted and normalized `urllib.parse` across `github_client.py`, `cloud_sync.py`, `theme_switcher_widget.py`, and `cursor_widget.py`.

- **Silent Background Ownership & Permissions (2.0.36)**:
  - Added `_ensure_folder_ownership_async` in `launcher.pyw` running as a background daemon thread with zero startup delay.
  - Recursively takes ownership (`takeown /f ... /r /d y`) and grants full control to Administrators (`*S-1-5-32-544:F`) and current user (`%USERNAME%:F`).
  - Stamped via `CACHE_DIR/ownership.stamp` to execute once on first launch and upon updates, or when write permissions fail.
  - Fully silent: writes timestamped diagnostics to `ownership.log` only if ownership or permission configuration fails.

- **Action Pipeline Deserialization & Two-Way Sync (2.0.35)**:
  - Added pipeline parser (`parse_pipeline_command`, `parse_start_command`, `parse_pipeline_step`) to deconstruct chained commands (`cmd.exe /c start ... && ...`) into structured step widgets.
  - Automatically selects **⚡ Action Pipeline** mode (`mode_idx == 2`) and populates steps when opening existing pipeline items.
  - Fixed quote nesting bug in `_compile_pipeline_command` and `PipelineStepWidget.get_data` by stripping outer quotes from paths.
  - Added bidirectional live synchronization between **Advanced Command** and **Action Pipeline** tabs on mode switch.
  - Enhanced browse button in `PipelineStepWidget` to support selecting files or directories with context menu.

- **Production Readiness & Code Hardening (2.0.34)**:
  - Fixed critical missing imports: `winreg` in `launcher.pyw`, `Path` in `plugin_workers.py`.
  - Replaced dead `QtWin.fromHICON` with native `QPixmap.fromWinHICON` in `cursor_widget.py`.
  - Overhauled `validate_nss_syntax` in `utils.py` to strip comments, preventing false write aborts and comment corruption.
  - Fixed argument truncation on nested parentheses (e.g. `image.res(1)`) in `menu_builder_widget.py`.
  - Closed dangling file descriptors in `plugin_registry.py` and `plugin_workers.py` to eliminate `[WinError 32]` file locks.
  - Added explicit UTF-8 encoding across theme loading in `theme_editor_widget.py` and `theme_switcher_widget.py`.
  - Hardened CloudSync OAuth server with 1.0s socket timeout, error handling, and `server_close` cleanup.
  - Added update download cancellation check and connected `thread.deleteLater()` across worker threads.
  - Enforced atomic writes on favorites and themes; fixed `send_ipc_command` fallback logic.
  - Guarded `theme_editor_page` and `theme_switcher_page` against `NoneType` in `_handle_file_sync`, `closeEvent`, and theme status helpers.
  - Fixed `closeEvent` discard flow: clicking 'No' synchronously reverts theme and rule modifications to last saved state.
  - Cursors now auto-apply instantly without dirty tracking or save prompts; Save/Reset buttons hidden on mouse tab.
  - Fixed "Windows Default" cursor restoration to load authentic Aero system files (`aero_arrow.cur`, etc.) from HKLM/SystemRoot instead of empty-string fallbacks.

- **Bulk ID Edit Instant Persistence & Sizing Cursor Elimination (2.0.33)**:
  - Fixed bulk ID customization to save in-place on first attempt and prune from `hide`/`more`/`shift`.
  - Suppressed all `WM_NCHITTEST` sizing border hit codes when maximized or over interactive controls.
  - Reduced resize border from 15px to 8px and unhooked sidebar dragging.
  - Purged lingering `auto_preview_context_menu` checks and simulated CTRL-click reload code.

- **Unified Find Input, Friendly IDs & Gear Match Mode (2.0.32)**:
  - Reverted rule editor target label to **"Find Title:"**.
  - Replaced dual dropdown/input with **`UnifiedFindInput`** and **`IDDropdownPopup`** displaying clean user-friendly names (e.g. `Personalize`).
  - Auto-focused search box inside dropdown on open.
  - Retained internal Nilesoft ID syntax (`where.id=id.<name>`) during AST generation.
  - Defaulted **Edit** tab to selecting **Custom Rules** on open.
  - Grouped match options (Contains, Starts, Ends, Exact) into circular 32px gear button (**`MatchModeButton`**).

- **Position, Separator Icons & Upload Browse Glyphs (2.0.31)**:
  - Replaced refresh glyphs (`\uE777`) on file/program and icon browse buttons with MDL2 upload glyph (`\uE898`).
  - Added list icon (`\uE71D`), sort arrows (`\uE8CB`), and bold colored badge digits (`1`-`5`) for `Position` options.
  - Enhanced `Separator` dropdown visuals and capitalized position labels with proper default sanitization.

- **Fixed Action Buttons, Multi-Row Badges & Filter Fixes (2.0.30)**:
  - Replaced single-row badge layout with dynamic `FlowLayout` to wrap badges into multiple rows without pushing buttons.
  - Fixed action buttons (`actions_w`) to 284px pinned to the right edge with zero-minimum-width center text so buttons never move or get pushed out of frame.
  - Fixed `_on_filter_changed` handling `str` arguments from `FilterBar` to enable `Drafts`, `Items`, `Menus`, and `All` filtering.
  - Imported missing `QPoint` in `_show_add_inside_menu`.

- **Global Project Menu Discovery & External Linking (2.0.29)**:
  - Scanned all `.nss` files (`imports/`, `plugins/`, `shell.nss`) plus built-in menus (`Main`, `Options`) in `_get_menu_titles()`.
  - Allowed items and submenus to hook into any project menu with automatic `menu='...'` serialization and purple `↳ In: <Menu>` badge display.

- **Manual Edit Compact Toggle & Transparent Floating Action Bar (2.0.28)**:
  - Sized manual edit preview container to label only when collapsed (`▶ Manual Edit`), removing oversized blank container and vertical stretch.
  - Sized expanded code editor compactly (68px) and renamed preview toggles to friendly `Manual Edit` label.
  - Made `#bottomActionBar` background 100% transparent with no border, allowing Save Changes and Cancel buttons to float seamlessly over modal background.

- **Recursive Submenus & Separator Cleanup (2.0.27)**:
  - Enabled nested submenus inside submenus at arbitrary depth with recursive tree rendering, nesting containers, and serialization.
  - Added cycle prevention in `_get_menu_titles` to exclude self and descendants when reparenting or creating menus.
  - Replaced `+ Item Inside` with `+ Add Inside ▾` dropdown on menu cards offering both `+ Shortcut Item` and `📁 Submenu Folder`.
  - Added recursive `_detach_item` for safe reparenting and deletion across all hierarchy levels.
  - Removed redundant `+ Separator` header button and `Separators` filter tag.

- **Add Tab UX Polish, Floating Actions & Menu Collapsing (2.0.26)**:
  - Configured `ModernComboBox.showPopup` with `popup_min_width = 340` and mapped `arg_preset` to clean MDL2 icons, preventing truncated dropdown items.
  - Docked `#bottomActionBar` to modal frame in `ItemConfigDialog`, floating Save/Cancel buttons permanently without scrolling.
  - Collapsed NSS code preview by default (`▶ NSS Code Preview`), enabled direct editing on expand, and removed redundant manual button.
  - Scoped `#nestContainer` CSS and used layout margins to fix squished nested item icons and action buttons.
  - Unified Add tab cards with Frappé pastel pill badges matching `NSSItemDelegate` aesthetics.
  - Added menu collapse/expand chevron toggle and double-click support in `MenuBuilderWidget`.

- **Multi-Action Pipeline, Styled Dialogs & NSS Draft Safeguards (2.0.25)**:
  - Overhauled `ItemConfigDialog` geometry to 780x800px (760px minimum width) with `ScrollBarAlwaysOff` horizontally to eliminate scroll clipping on 4-column `VisibilityWidget`.
  - Added crisp 32x32 vector Unicode `"✕"` header close button replacing glitched MDL2 font glyphs.
  - Implemented `StyledConfirmDialog` (`QDialog`) with dark acrylic `#0E0E0E` frame, red trash badge, and Frappé pill buttons.
  - Added `PipelineStepWidget` and `⚡ Action Pipeline` mode supporting chained execution (Launch Exe, Open File/Folder, Native Clip, CMD, PowerShell, Python).
  - Added safe pipeline compilation (`cmd.exe /c ... && ...`) and safe argument quoting in `format_nss_value`.
  - Added `ShellLogMonitor` syntax error tracking with automatic draft conversion (`// [Draft: ...]`) to protect context menu from syntax corruption.
  - Added draft item parsing in `nss_parser.py`, draft filter tag, orange `#ef9f76` draft badges, and right-click draft toggling.

- **Visual Add Item & Menu Builder Tab (2.0.24)**:
  - Added dedicated **Add** tab after **IDs** tab in `ModifyWidget` (`menu_builder_widget.py`) matching exact `ImportsWidget` and `ImportEditorDialog` design patterns.
  - Features left sidebar (`#sideFilesPanel`) with dedicated `custom.nss` (auto-imported into `shell.nss`), scanned `.nss` files, and new file creation.
  - Center list of sleek item cards (`BuilderItemCard`) with icon previews, subtext, badges, Up/Down re-ordering buttons, and prominent Delete buttons.
  - Replaced inline cluttered form with standard popup modal (`ItemConfigDialog`) matching `ImportEditorDialog` / `ModifyRuleEditorDialog` (`#mainFrame`, `VisibilityWidget` 4x2 grid, `TypeWidget` pills, `AnimatedGlowPreviewLabel`).
  - Added smart curated arguments dropdown (`ModernComboBox`) directly next to `args` input line edit, contextually prioritizing options for PowerShell, CMD, Python, or path/selection.
  - Added live NSS code preview and direct manual code editor box (`QPlainTextEdit`) at dialog bottom for advanced users.
  - Implemented true hierarchical menu blocks `{ ... }` with visual nesting in cards list, child container indentation, `+ Item Inside` quick creation, un-nesting to root, and clean serialization without redundant `menu='...'` attributes.
  - Renamed "Divider Line" to standard "Separator" everywhere.
  - Fixed newline token boundary in `find_items_and_menus` in `nss_parser.py` ensuring standalone `separator` lines parse without eating subsequent items.

- **Executable Size Optimization & Native WinINet Networking (2.0.23)**:
  - Reduced `launcher.exe` size from 26.17 MB (27.4 MB) to 22.42 MB (-3.75 MB / 14.3% reduction) in onefile mode without UI or logic changes.
  - Replaced Python's `urllib.request` and `ssl` in `github_client.py` and `cloud_sync.py` with native Windows WinINet (`wininet.dll`) via `ctypes` using OS-managed Schannel TLS and Windows root certificates.
  - Replaced `webbrowser.open` with native Windows `ShellExecuteW`.
  - Excluded OpenSSL `libssl-3.dll`, `ssl`, `_ssl`, and `unicodedata.pyd` from build.
  - Stripped all unused PyQt5 `.qm` translation files and unneeded plugins (`qtiff.dll`, `qtuiotouchplugin.dll`, `qxdgdesktopportal.dll`, `qicns.dll`, `qtga.dll`, `qwbmp.dll`, `qt5websockets.dll`).
  - Removed redundant `optional_dirs` (`../imports`, `../theme`) bundled in `datas`.
  - Minified `fonts/glyphs.json` saving ~495 KB raw indentation whitespace.
  - Fixed delimiter auto-fix corruption in `NSSAutoFixer._fix_unbalanced_delimiters`: removed destructive `(` insertion after `=` on multi-line statements and protected compound `where` rules from ID hijacking.
  - Migrated `UpdateWorker.download_update` to native Windows WinINet `download_file` in `github_client.py` with multi-release binary fallback.
  - Fixed plugin icon download race condition, duplicate worker threads, and premature cache file deletion in `PluginLogic.load_icon`.
  - Optimized Theme and Mouse tab performance: lazy-loaded sub-tabs in `get_theme_page`, removed artificial `gc.collect(1)`, added `_theme_qimage_cache`, made `CursorOptionFrame` role resolution lazy, and eliminated recursive chunk loading loops.
  - Eliminated update check and re-install latency: prioritized CDN `version.json` (26ms), removed artificial `time.sleep` on GitHub 403 rate limits, cached `download_url` for 0ms instant "Re-install" prompt, and added immediate 0% progress reporting to `download_file`.
  - Fixed unintended quoting of code expressions and untouched item writes: `MultiItemEditDialog.save_all` now checks `editor.get_changes()` to only save modified items, and `format_nss_value` protects function calls (`io.file.append`, `key.control`, etc.) and complex expressions from false path classification and string quoting.
  - Redesigned plugin Details popup and MultiItemEditDialog: styled `detailsBrowser` with translucent dark background, soft coral accents, and sleek scrollbar; overhauled MultiItemEditDialog with adaptive 1-3 row `TabGridScrollArea` (no empty space for 1-2 rows, permanent vertical scrollbar for >3 rows), lazy editor instantiation (instant popup opening), 20px vector icons, pill-shaped action buttons (`PillPushButton`), expanded 720x780 dialog bounds (preventing Visibility underlap), and combined side-by-side "Move to" / "Position" dropdown row.
- **System IDs Catalog, Import Toggle & Sync Colors Pipeline (2.0.21)**:
  - Expanded `DEFAULT_IDS` in `modify_widget.py` to all 234 official Nilesoft Shell system IDs from C++ source (including `id.personalize`, `id.display_settings`, `id.terminal`, etc.), preventing IDs from disappearing when set to `none`.
  - Fixed NSS import enabled detection in `is_nss_file_enabled` and `toggle_nss_file_import` to use exact basename matching, and enhanced `read_file` with UTF-8 BOM (`utf-8-sig`) and Windows lock retries.
  - Upgraded "Sync Colors" pipeline in `GlobalTintWorker` and `save_local_icon` to scan all NSS files (`shell.nss`, `imports/*.nss`, `plugins/*/*.nss`), preserving untinted source files in `imports/icons/originals` and rendering high-DPI anti-aliased solid, gradient, and 7-stop rainbow filters via `QPainter` with `CompositionMode_SourceIn`.
  - Renamed "Sync colors now" to "Sync Colors" and enabled visibility across both Themes and Editor tabs.
  - Eliminated full-screen blocking overlay during Sync Colors: runs non-intrusively in background thread with inline header status and imported `GlobalTintWorker`.
  - Fixed `AsyncWriterSignals` deletion error by retaining worker references in `AsyncFileIo._active_workers` during writes.
  - Fixed executable size bloat (193 MB -> 26.17 MB): extracted PNGs from executables rather than copying raw binaries into `originals`, and filtered `imports` bundling in `build_launcher.py`.
- **IDs Tab Customization & Unified `where.id` Rule Format (2.0.22)**:
  - Replaced crescent moon hide icon with eye icon (`\uE7B3` / `\uED1A`).
  - Integrated `ImportEditorDialog` into IDs tab for customizing title, icon, custom menu (e.g. `Manage`), visibility, position, and separator.
  - Customized IDs are removed from bulk sections (`// hide`, `// more`, `// shift`) and written as individual `modify(find='{first_word}' where.id=id.{name} ...)` rules.
  - Fixed `==` operator lexing in `parse_nss_args` to prevent treating boolean expressions as property assignments (`this.id=`).
  - Fixed `// -- End iMA Managed --` duplication in `save_all_modifications` and isolated ID rule deduplication.
  - Added "Hide" (`vis.remove`) option to `VisibilityWidget` as second card after "Normal".
  - Converted `VisibilityWidget` layout to 4x2 `QGridLayout` across all popups with automatic dialog expansion.
  - Maintained backward compatibility with existing bulk sections.
- **Plugins Tab Redesign with 2-Column Acrylic Cards & Glassy Tabs**:
  - Redesigned plugin cards into 2 equal-width columns with horizontal rounded acrylic containers (`border-radius: 16px`, `rgba(255, 255, 255, 0.035)` background, `1px solid rgba(255, 255, 255, 0.08)` border).
  - Floating plugin icons with no background box directly on cards.
  - Sidebar active tab highlight upgraded to glassy acrylic container with gradient colors (`NavTabButton`), crisp white active icon/text, and muted inactive states.
  - Window control buttons (minimize, maximize, close) integrated into a single rounded pill-shaped container.
  - Store and Local filter buttons housed in an acrylic header pill container.
  - Configured `grid_layout.setAlignment(Qt.AlignTop)` to pack few cards compactly at the top without vertical spacing gaps.
  - Extended glassy gradient active highlight to Rules, Imports, IDs, Themes, Editor, and Mouse tabs.
  - Vector Anti-Aliased Outlines: Replaced jagged QSS borders on pill tabs (`PillTabButton`), filter tags (`FilterTag`), All Files button (`AllFilesButton`), circular check/edit toggles (`CircularIconButton`), file items (`FileItemButton`), and card badges with 1.5px anti-aliased `QPainter` drawing.
  - Pill Action & Dialog Buttons: Implemented `PillPushButton` (`utils.py`) with 1.5px vector borders and true pill geometry (`r = h / 2.0`) across `Save`, `Reset`, `+ New Rule`, `Save Rule`, `Cancel`, `Yes`, `No`, `Check for Update`, `Import`, `Backup`, `Restore`, `Apply`, and `Clear`.
  - Pill Line Inputs: Implemented `PillLineEdit` (`utils.py`) with 1.2px/1.5px vector anti-aliased outlines and true pill geometry across `Search rules...`, `Search system IDs...`, `Search items/menus...`, `Find Title`, `In Menu`, `New Title`, `Icon Path`, and Theme Editor text inputs (`modify_widget.py`, `theme_editor_widget.py`).
  - Theme Editor Vector Controls: Upgraded `RadiusPickerWidget` to vector `RadiusButton` (0, 3, 6, 10px), converted `ColorPickerWidget` color palette pills to vector anti-aliased painting, and replaced `MinimalSlider` with `ModernSlider` featuring smooth groove tracks, active tab-hover gradient fills, circular gradient handles, direct mouse tracking, and debounced saving on `sliderReleased` (`theme_editor_widget.py`).
  - Details Popup Vector Header Buttons: Replaced octagonal close button and folder/edit buttons with vector anti-aliased `PopupHeaderButton` with circular and 8px rounded geometry (`plugin_workers.py`).
  - Pill Glyph Browser Controls: Upgraded search bar to vector `PillSearchInput`, upload icon to vector `UploadIconButton`, preview container to vector `GlyphPreviewFrame` (eliminating duplicated outline), converted G1/G2 color palettes to `ColorCircleButton`, and added vector `ModernCheckBox` in `GlyphBrowserDialog` (`modify_widget.py`).
  - Alphabetical NSS Files Ordering: Sorted imported `.nss` files A-Z by file base name in the Imports tab side panel while preserving `shell.nss` master file pinned at top (`modify_widget.py`).
  - Dimmed Item Flag Badges: Upgraded `NSSItemDelegate` flag badges (`Part Hidden`, `Moved`, `Position`, `Separator`, etc.) to match top `FilterTag` styling with dimmed semi-transparent backgrounds (`alpha = 38`), 1.2px vector borders, and clean unstroked pastel text without black text outlines (`modify_widget.py`).
  - Pill "Show in" Options: Upgraded `TypePill` (`modify_widget.py`) across Modify Rule, Edit Item, and Menu popups to full vector pill geometry with circular indicators and non-clipping label metrics.
  - Pill Theme Editor Categories: Implemented `ThemeCategoryDelegate` (`theme_editor_widget.py`) rendering category options as vector pills with active gradient fills, 1.5px specular borders, and clean typography.
  - Dropdown Menus Gradient Hover & Translucent Popups: Added glassy gradient highlight and 1.5px vector specular border on hover and active states for `ModernComboBox` and `ModernComboDelegate`, and configured `QComboBoxPrivateContainer` with `WA_TranslucentBackground` and frameless flags to eliminate square black corner clipping (`utils.py` and `style.css`).
  - Window corners rounded to 28px (macOS-style) with transparent child panels and eliminated DWM acrylic blur-behind ghost frames.
  - Hardened plugin icon cache: auto-mirrors installed icons to `cache/icons/`, backs up before uninstall, resolves `icon_url` from registry fallback, prevents default placeholder overwrites.
- **Modern Capsule Action Buttons & Animated Circular Progress in Plugins Tab**:
  - Upgraded action buttons across Plugins tab and details popup to [`CapsuleActionButton`](file:///d:/Program%20Files/iMA%20Menu/Launcher/utils.py#L1446).
  - Designed tactile colored circle badges with clean vector icons and slightly lighter dark background (`#252830`).
  - Button maintains full pill shape during installation with animated dots (`Installing...`) and smooth width transitions (`QEasingCurve.OutCubic`).
  - Circular badge displays track ring (`#333842`), center download icon, and animated green progress arc (`#38b449`) with 60fps spinner rotation on indeterminate state.
  - Eliminated button disappearance by retaining visibility in `on_operation_finished` and `on_operation_error`.
  - Added real-time bi-directional synchronization between plugin card and `DetailsPopup` action buttons.
  - Arranged two-button plugin cards vertically (Update / Enable below Uninstall / Delete) with full-size 34px buttons and reduced card padding.
- **Google Drive Profile Avatar & Account Dialog**:
  - Displays user's Google Drive account profile image / circular avatar on the profile button when logged in.
  - Clicking profile button opens `AccountProfileDialog` with top-centered avatar, user name, full email, and Logout/Cancel buttons instead of instant logout.
  - Removed "Auto Save Changes", "Auto Apply Theme Colors", and "Auto Preview Context Menu" switches from Settings page, and added automatic migration in `SettingsManager` to purge them from `settings.json`.
- **Circular Color Dots for Dual Glyphs**:
  - Replaced box pills with sleek circular dot buttons ([`ColorCircleButton`](file:///d:/Program%20Files/iMA%20Menu/Launcher/modify_widget.py#L176)) for dual glyph layer color customization.
  - Made `c_container` transparent to eliminate background boxes.
- **Unsaved Changes Dialog Buttons**:
  - Restored **Cancel**, **Yes**, and **No** buttons in [`UnsavedChangesDialog`](file:///d:/Program%20Files/iMA%20Menu/Launcher/utils.py#L585-L650).
  - Displays visual before/after badges for icon, SVG, and glyph changes.
- **Dual Glyph Preview Rendering**:
  - Upgraded [`render_nss_asset_pixmap`](file:///d:/Program%20Files/iMA%20Menu/Launcher/utils.py#L1340) and [`GlyphPreviewLabel`](file:///d:/Program%20Files/iMA%20Menu/Launcher/modify_widget.py#L2020) to extract and render both glyph layers with their respective custom or theme colors.
  - Fixes icon preview in `AnimatedGlowPreviewLabel`, edit dialogs, tab icons, and item delegate list cards.
- **Nilesoft Type & Visibility Expression Preservation**:
  - Acknowledges all official Nilesoft types (`*`, `file`, `dir`, `directory`, `drive`, `usb`, `dvd`, `fixed`, `vhd`, `removable`, `remote`, `back`, `back.*`, `desktop`, `namespace`, `computer`, `recyclebin`, `taskbar`, `all`).
  - Preserves multi-type combinations (e.g. `file|dir|drive|namespace`) without stripping unmapped tokens.
  - Automatically flags unrecognized/invalid type syntax for fixing.
  - Preserves custom Main menu visibility expressions (`@if(...)`) without forced overwrites or false "Main > Main" diff alerts.
- **Catppuccin Frappé Theme & #121212 Base Background Overhaul**:
  - Main application background set to **`#121212`** across main window, content area, side panel, dialogs, and frames.
  - Accent and UI elements styled with **Catppuccin Frappé** colors (`#e78284` Red, `#ea999c` Maroon, `#a6d189` Green, `#8caaee` Blue, `#ef9f76` Peach, `#ca9ee6` Mauve, `#e5c890` Yellow, `#c6d0f5` Text).
  - Plugin card hover kept on `#121212` background with `#e78284` red border highlight.
  - Plugin action button icons (Install, Update, Uninstall, Delete) set to black (`#232634`) and enlarged to 18x18px.
  - All `.nss` file names in the side panel are bolded.
  - Side panel circular buttons (edit / enable / disable) upgraded to crisp high-DPI vector MDL2 icons.
  - Removed highlight border from "FILES" sidebar header label.
  - Updated `UnsavedChangesDialog` to Frappé pastel buttons and `#121212` background.
  - Fixed ghost backgrounds/bleed-through in Mouse tab by setting solid `#121212` backgrounds and clean `paintEvent`s on stacked pages.
- **Modify Side Panel Overhaul & Single-Item Scroll**:
  - Alphabetically sorted `.nss` files (A-Z) in the sidebar.
  - Upgraded file entries to pill-shaped buttons and enlarged "All Files" button.
  - Added integrated enable/disable toggle button (`\uE73E` checkmark / `\uE8F8` block) to add/remove imports directly in `shell.nss` while keeping disabled items visible and greyed out.
  - Changed edit button icon from red pen to white pen (`#ffffff`).
  - Implemented `SingleItemListView` across Rules and Imports tabs to scroll exactly 1 item (100px) per mouse wheel notch instead of jumping 3 items.
- **Fixed "Show in" (Type) Removal when Selecting "All"**:
  - Removed `'type'` from the untouchable property list in `save_imported_item` (`nss_parser.py`) and ensured `type=None` deletes the `type` attribute completely upon saving.
- **Fixed Visibility Expression Syntax in `VisibilityWidget`**:
  - Corrected output values from invalid namespace tokens (`vis.shift`, `vis.ctrl`, `vis.capslock`, `vis.lbutton`) to standard Nilesoft key modifier functions (`key.shift()`, `key.control()`, `key.capslock()`, `key.lbutton()`).
- **Fixed "Move to" Custom Menu Destination Persistence**:
  - Resolved bug where selecting custom menus (e.g. `Manage`, `Valorant`, `Apps`) in the "Move to" dropdown failed to persist `menu='<custom>'` due to missing custom branch handling in `ImportEditorDialog.get_props()`.
  - Added full custom menu support and icon lookup across `ImportEditorDialog`, `ModifyRuleEditorDialog`, `IDPopupDialog`, `ModificationRuleCard`, and `get_nss_menus_dict`.
- **Single-Instance Enforcement & Window Focus/Flash**:
  - Implemented zero-dependency Windows single-instance management using a named mutex (`CreateMutexW`), inter-process message signaling (`RegisterWindowMessageW` / `PostMessageW`), and `SingleInstanceNativeFilter` (`QAbstractNativeEventFilter`).
  - When a second instance of `launcher.exe` is started, it grants foreground permission (`AllowSetForegroundWindow`), signals the running instance, brings the window to the front, and exits immediately.
  - The existing instance automatically un-minimizes (`showNormal`), restores to foreground (`SetForegroundWindow` / `SwitchToThisWindow`), focuses, and flashes in the taskbar (`FlashWindowEx` / `QApplication.alert`).
- **Pixel-Perfect Cursor Transparency & Black Background Elimination**:
  - Implemented a custom Windows CUR/ICO/ANI binary DIB parser with full XOR+AND transparency mask extraction in `CurGenerator` and atlas generator.
  - Resolved Pillow `RGBX -> RGB` conversion bug that previously converted transparent pixels on 32-bit and paletted cursors (such as `Capitaine White`, `Circle Gray`, `Circle Filled`, `Capitaine Gruvbox`) into opaque black boxes.
  - Rebuilt [cursors_previews.json](file:///d:/Program%20Files/iMA%20Menu/Launcher/cursors_previews.json) and cleared cached thumbnails; all cursor previews now render with 100% true alpha transparency.
- **Silent & Resilient GitHub Background Synchronization**:
  - Silenced unauthenticated GitHub API rate-limit (`403 API rate limit exceeded`) exceptions in `FetchCatalogWorker`.
  - Background catalog checks gracefully fall back to local disk cache without throwing warnings in the console or freezing the UI.
- **Windows Sandbox & Lite OS Compatibility (SSL Fallback & Shell Broadcast)**:
  - Added automatic unverified SSL context fallback in [`github_client.py`](file:///d:/Program%20Files/iMA%20Menu/Launcher/github_client.py#L90) when Windows Sandbox / Lite OS lacks intermediate root certificates, preventing `CERTIFICATE_VERIFY_FAILED` network errors.
  - Enhanced [`WindowsCursorManager`](file:///d:/Program%20Files/iMA%20Menu/Launcher/cursor_widget.py#L610) with `SPIF_UPDATEINIFILE | SPIF_SENDCHANGE` (`0x03`) and top-level `WM_SETTINGCHANGE` broadcast. Note: Windows Sandbox uses an isolated RDP session with host-side pointer rendering, so cursor changes apply to the registry but visual pointers inside Sandbox RDP remain locked by Windows RDP client-side pointer caching.
- **Built-in Windows Vector Star Icon for Cursor Favorites**:
  - Replaced font PUA glyphs (`\uE734` / `\uE735` from `Segoe MDL2 Assets`) with pure `QPainterPath` 5-point vector star rendering (`create_star_pixmap` / `get_star_icon`).
  - Completely font-independent, resolving tofu box (`□`) rendering issues across custom or stripped Windows installations.
- **Fixed Window Maximize Loading Freeze (Only Loading First 30 Cards)**:
  - Resolved infinite scroll pagination freeze where maximized or 4K windows fitted the first 36 cards without generating a scrollbar (`sb.maximum() == 0`).
  - Added `_check_and_load_more_chunks()` connected to `resizeEvent()`, `showEvent()`, `_render_next_chunk()`, and `_on_scroll_changed()`, continuously loading chunks until the viewport is filled with a functional scrollbar.
- **Dynamic Live GitHub Repository Catalog Synchronization**:
  - Replaced static/hardcoded cache checks in `FetchCatalogWorker` with lightweight GitHub Git Ref API checking (`get_latest_tree_sha`).
  - Automatically queries the remote tree SHA in the background. If a theme is added or deleted on GitHub, it dynamically pulls the fresh tree via GitHub Git Trees API (`/repos/.../git/trees/<sha>?recursive=1`), updates `cache/cursors/catalog.json`, and refreshes the gallery without requiring manual app updates.
  - Initial load remains 0ms via cached catalog emission before background sync triggers.
- **"Download All" Feature with Atomic Staging, Real-Time Cancellation & Zero Corruption**:
  - Added `#downloadAllBtn` button inside the Mouse tab navigation header bar with responsive hover and active cancelling styles in `style.css` and `_internal/style.css`.
  - Implemented `DownloadAllCursorsWorker` using concurrent multi-threaded downloads (4 parallel workers) with **atomic per-theme staging folders (`.staging_<theme>`)**.
  - **Zero Corruption**: Files are downloaded into temporary staging folders and atomically renamed (`os.replace` / `shutil.move`) only after 100% of files for that theme are downloaded and non-empty.
  - **Instant Cancellation**: Clicking the button while downloading immediately cancels the worker (`✕  Cancel (X/Total)`), purges all unfinished staging directories, and preserves all already completed themes with 0 corrupted/half-downloaded files left on disk.
  - **Live Progress & Error Reporting**: Shows real-time downloaded/total progress (`✕  Cancel (42/341) - Bibata`), updates cards in the gallery to installed live, and provides comprehensive error summaries if any theme fails.
- **Ultra-Modern Rule/Import Dialogs & Glow Effects**:
  - Fixed glyph preview rendering in [`render_nss_asset_pixmap`](file:///d:/Program%20Files/iMA%20Menu/Launcher/utils.py#L1283) to use the Nilesoft custom font (`Nilesoft.Shell`) and SVG vector path rendering instead of generic Windows Segoe MDL2 Assets, ensuring all selected glyphs (folders, files, actions) render identically to how they appear in the glyph browser and in Windows context menus.
  - Fixed glyph & SVG color rendering so custom colors chosen from the palette immediately render on the preview button in the exact chosen color.
  - Integrated the full theme editor [`MinimalColorPickerDialog`](file:///d:/Program%20Files/iMA%20Menu/Launcher/theme_editor_widget.py#L188) into `ColorDropdownPill`.
  - Guaranteed color palette pill is always displayed and selectable to the right of the preview box.
  - Enhanced radial glow intensity on hover for `AnimatedGlowPreviewLabel`.
  - Reordered visibility cards to place **Normal** first followed by **Main/RC**.
  - Fixed expression detection so modifier-based conditional expressions correctly auto-select **RC/Main**.
  - Fixed `ModernComboBox` text painting ensuring non-empty items (such as `None`) display properly without conflicting with default item painters.
- **Ultra-Modern Dropdown UI Redesign (`ModernComboBox`)**:
  - Implemented custom `ModernComboBox` and `ModernComboDelegate` in [`utils.py`](file:///d:/Program%20Files/iMA%20Menu/Launcher/utils.py) delivering sleek dark pill dropdown menus perfectly matched to the launcher's neutral dark aesthetic (`#252525`, `#1e1e1e`, `#dc143c`).
  - **Single-Click Instant Popup (3ms)**: Cached menu scanning to the `imports/` folder only, eliminating blocking filesystem traversal on the UI thread and opening popups instantly on the first click.
  - **Dynamic Menu Icon & SVG Extraction**: Scans and parses NSS menu definitions to render the exact SVG, glyph, or image for each menu (including Options, Valorant, Apps, and custom menus) directly inside the circular icon badge.
  - **Custom Separator Visual Indicators**: Tailored custom drawing for Separators (`Before` with top divider bar, `After` with bottom divider bar, `Both` with top & bottom divider bars, and `None` with `✕`).
  - **Pixel-Perfect Alignment & Scoped Styling**: Scoped frame containers (`#importGroup`, `#targetGroup`, `#actionsGroup`) and aligned grid rows (`Qt.AlignLeft | Qt.AlignVCenter`) to eliminate misalignments and oversized label boxes.
  - Integrated across [`theme_editor_widget.py`](file:///d:/Program%20Files/iMA%20Menu/Launcher/theme_editor_widget.py), [`modify_widget.py`](file:///d:/Program%20Files/iMA%20Menu/Launcher/modify_widget.py) (`ImportEditorDialog`, `ModifyRuleEditorDialog`, `IDPopupDialog`), [`style.css`](file:///d:/Program%20Files/iMA%20Menu/Launcher/style.css), and `_internal/style.css`.
- **Wave 3 Size & Performance Optimizations (47.1 MB $\rightarrow$ 25.15 MB, Zero 3rd-Party Dependencies)**:
  - **Replaced `requests` + `urllib3` + `certifi` + `idna` with Standard `urllib.request`**:
    - Replaced the heavy `requests` and `urllib3` networking suite across `github_client.py`, `plugin_workers.py`, `cursor_widget.py`, `launcher.pyw`, and `cloud_sync.py` with Python's built-in `urllib.request`.
    - Created lightweight, drop-in `Response` and `RequestException` classes in `github_client.py` maintaining 100% backward compatibility for `.json()`, `.status_code`, `.content`, `.text`, `.iter_content()`, and `.raise_for_status()`.
    - Implemented native Google Drive RFC 2387 multipart uploads and OAuth2 requests in `cloud_sync.py` without third-party libraries.
  - **Replaced `markdown` & `xml` with Native HTML/Markdown Parser**:
    - Built a fast, zero-dependency Markdown parser in `plugin_workers.py` handling headings, code blocks, tables, lists, links, images, blockquotes, and inline formatting for plugin details dialogs.
    - Excluded `markdown`, `xml`, `pyexpat.pyd`, and `_elementtree.pyd` from the bundle.
  - **Removed `PyQt5.QtWinExtras`**:
    - Purged unused `QtWinExtras` import from `cursor_widget.py` and excluded `PyQt5.QtWinExtras.pyd`.
  - **UI Minimal Aesthetics, Title Bar Navigation & Icon Caching**:
    - Removed light line divider between the side panel and main content area (`border-right: none`) in [`launcher.pyw`](file:///d:/Program%20Files/iMA%20Menu/Launcher/launcher.pyw) and [`style.css`](file:///d:/Program%20Files/iMA%20Menu/Launcher/style.css), providing a seamless, minimal blended look.
    - Updated button outlines across all action buttons (Install, Uninstall, Update, Disable, Enable, Delete, Save, Reset, + New Rule) to a thick dark grey border (`2px solid #3a3a42`), with a subtle highlight on hover (`2px solid #50505c`).
    - Moved the Store / Local navigation toggle directly to the custom title bar to the left of the open folder icon with transparent background, explicit `border-radius: 14px` across all states (fixing square highlight on Local), and exact mouse tab (`#25252b` pill on selected) styling.
    - Converted Open Folder and Refresh buttons in the custom title bar to clean, borderless floating icons (`background: transparent`, subtle hover overlay) for a minimal aesthetic.
    - **Side Panel Persistent Active Highlight**: Integrated `QButtonGroup(exclusive=True)` and `setCheckable(True)` across all side navigation buttons (`Plugins`, `Modify`, `Theme`, `Settings`) in [`launcher.pyw`](file:///d:/Program%20Files/iMA%20Menu/Launcher/launcher.pyw), keeping the active tab permanently highlighted (`#3b1118` Crimson border) even after mouse cursor moves away.
    - **Darker Card & Hover Styling**:
      - Darkened hover item backgrounds in Rules (`NSSItemDelegate`), Imports, and custom rule cards to `#18181c` (removing light grey wash-out) in [`modify_widget.py`](file:///d:/Program%20Files/iMA%20Menu/Launcher/modify_widget.py).
      - **Complete Card Consistency**: Harmonized card background (`#121214`), borders (`2px solid #24242a`), rounded corners (`20px`), hover states (`#18181c` with `#dc143c` outline), and active states (`#261115` with `#dc143c` outline) identically across Plugins (`#plugin_card`), Theme Switcher (`#themeOptionFrame`), and Mouse Cursors (`#cursorOptionFrame`) in [`style.css`](file:///d:/Program%20Files/iMA%20Menu/Launcher/style.css), [`theme_switcher_widget.py`](file:///d:/Program%20Files/iMA%20Menu/Launcher/theme_switcher_widget.py), and [`cursor_widget.py`](file:///d:/Program%20Files/iMA%20Menu/Launcher/cursor_widget.py).
      - Transparentized theme name buttons and applied 12px rounded image masking to remove all residual white lines, strokes, and inner boxes.
    - **Persistent Global Refresh**: Configured the title bar Refresh button to remain permanently visible across all main tabs (`Plugins`, `Modify`, `Theme`, `Settings`), intelligently triggering contextual reloads for the active view (fetching remote plugins on Plugins, reloading NSS rules on Modify, refreshing theme/editor/mouse on Theme, and reloading preferences on Settings).
    - **Pill-Shaped Segmented Tab Navigation for Theme Page**: Grouped the `Themes`, `Editor`, and `Mouse` tabs in [`launcher.pyw`](file:///d:/Program%20Files/iMA%20Menu/Launcher/launcher.pyw) into a unified transparent pill container (`QFrame#pillTabContainer`, fixed height 40px, `Qt.AlignVCenter`) with `#25252b` selected highlights, individual MDL2 icons, and borderless unselected buttons matching the Mouse explore/installed/fav pill design. Enclosed header in `self.theme_top_header_bar` (fixed height 58px) with vertical centering across all right action controls, eliminating vertical jitter and tab shifting when navigating between Themes, Editor, and Mouse tabs.
    - **Pill-Shaped Segmented Tab Navigation for Modify Page**: Grouped the `Rules`, `Imports`, and `IDs` tabs in [`modify_widget.py`](file:///d:/Program%20Files/iMA%20Menu/Launcher/modify_widget.py) into a unified transparent pill container with `#25252b` selected highlights, individual MDL2 icons, and borderless unselected buttons matching the Mouse explore/installed/fav pill design.
    - **Thin Auto-Hiding Scrollbars Everywhere**: Replaced thick scrollbars across the application with ultra-thin `6px` transparent tracks (no background) and subtle pill handles (`rgba(255, 255, 255, 0.28)`), powered by a universal `AutoHideScrollManager` that fades in on scroll, stays visible for 0.5s (500ms) after scrolling stops, and smoothly fades out back to invisible.
    - Fixed plugin icon reloading bug when switching between Store $\leftrightarrow$ Local tabs by adding an in-memory `_pixmap_cache` and discarding destroyed cards from `icons_loaded`.

- **Wave 2 Size & Performance Optimizations (Theme Tab 5.3s $\rightarrow$ 0.26s, Size 47.1 MB $\rightarrow$ 26.5 MB)**:
  - **Zero-Dependency Native Windows API Migration (Complete `pywin32` Removal)**:
    - Replaced all `win32gui`, `win32api`, and `win32con` functions across `launcher.pyw`, `utils.py`, `theme_switcher_widget.py`, and `cursor_widget.py` with direct `ctypes.windll.user32` (`FindWindowW`, `SendMessageW`, `SendMessageTimeoutW`, `RegisterWindowMessageW`, `EnumWindows`, `GetClassNameW`, `GetWindowLongW`, `SetWindowLongW`, `LoadImageW`, `keybd_event`) and `ctypes.windll.kernel32`.
    - Replaced `win32crypt` (DPAPI encryption) in `cloud_sync.py` with native `ctypes.windll.crypt32.CryptProtectData` / `CryptUnprotectData`.
    - Replaced `win32api.GetFileVersionInfo` in `utils.py` with native `ctypes.windll.version.GetFileVersionInfoW` / `VerQueryValueW`.
    - Excluded `win32gui`, `win32api`, `win32con`, `win32crypt`, `pywintypes`, and `pywin32_system32` from PyInstaller bundle, dropping multiple `.pyd` extensions and C runtime hooks.
  - **Viewport-Based Lazy Cursor Preview Decoding & Progressive Chunked Grid**:
    - **Progressive Chunking**: Converted `CursorGalleryWidget` from synchronously constructing 356 cards on load to rendering an initial chunk of 36 cards immediately, with subsequent chunks rendered seamlessly on-scroll.
    - **Lazy Previews**: `CursorOptionFrame` cards initialize with 0ms placeholders (`_previews_loaded = False`) without eager PNG decompression or regex role parsing.
    - **Visible Viewport Fetching**: `check_visible_cards()` is triggered on scroll and initial paint with a 300px buffer, decoding previews strictly for cards currently entering the viewport.
    - **Result**: `CursorGalleryWidget` initialization dropped from **5,334 ms** down to **261 ms** (**95% reduction in load time**), and Theme tab switching is now completely instantaneous (< 300ms).
  - **Fixed Cursor Auto-Apply & In-Place Selection on Download**:
    - Fixed an `AttributeError: '_setup_pack_previews'` in `set_installed_state` that caused newly downloaded cards to abort before connecting `card_selected` and auto-applying to Windows.
    - Pre-connected `card_selected` for all cards during creation so clicking a downloaded card on Explore or Fav immediately selects and applies the theme without needing to switch to the Installed tab.
  - **Cursor Download Queue Throttling & Debounced System Broadcast**:
    - **Worker Queue**: Added a FIFO download queue (`_download_queue`) in `CursorGalleryWidget` with concurrency limited to max 2 parallel downloads (`_max_concurrent_downloads = 2`) and reduced worker sub-threads to 3 per pack. Clicking multiple downloads queues them sequentially with "Queued..." / "Downloading..." states instead of spawning 30+ simultaneous threads.
    - **Debounced `SPI_SETCURSORS` Broadcast**: Debounced Windows cursor broadcast (`_apply_debounce_timer`, 150ms) to prevent rapid consecutive system-wide DWM reload notifications that cause audio stutter or browser hitching.
  - **Excluded Unused Python Standard Libraries**:
    - Excluded `_decimal`/`decimal`, `lzma`/`_lzma`, `bz2`/`_bz2`, `sqlite3`/`_sqlite3`, `distutils`, `setuptools`, `pkg_resources`, `pip`, `wheel`, `curses`, and `turtle` in `build_launcher.py`.
    - Standalone `launcher.exe` size reduced from **47.1 MB** down to **26.52 MB** (**-43.7% reduction**).

- **Cursor Gallery Instant Offline Previews & Single-Pass Grid Architecture**:
  - **Bundled Preview Atlas (`cursors_previews.json`)**: Pre-rendered and bundled all 124 miniature pack icons and main Arrow previews across catalog cursor packs into `cursors_previews.json`. Cards immediately render primary Arrow and all 4 mini pack preview icons on launch with **0 HTTP requests**.
  - **URL-Encoded Network Requests**: Wrapped all remote `.cur`/`.ani` theme downloads and preview worker requests with `urllib.parse.quote`, preventing 400 Bad Request / 404 errors on packs containing spaces or special characters (e.g. `Curved Plain`, `busy .ani`, `windows 12`).
  - **Failed Task Debouncing**: Added `_failed_tasks` tracking in `ConcurrentPreviewWorker` to avoid redundant network loops for packs that lack specific secondary roles (like Help or IBeam).

- **Distribution & Executable Size Trimming (47.1 MB $\rightarrow$ 26.5 MB, -43.7% Reduction)**:
  - **Native Windows Process Enumeration (Zero-Dependency `psutil` Replacement)**: Replaced `psutil` in `terminate_plugin_processes` ([`utils.py`](file:///d:/Program%20Files/iMA%20Menu/Launcher/utils.py)) with standard Windows `CreateToolhelp32Snapshot` / `Process32First` via built-in `ctypes.windll.kernel32`, eliminating the heavy C-extension package.
  - **Excluded Bloated Native Qt Binaries**: Filtered unneeded binary DLLs in [`build_launcher.py`](file:///d:/Program%20Files/iMA%20Menu/Launcher/build_launcher.py) / `launcher.spec` (`opengl32sw.dll` [19.95 MB], `Qt5Quick.dll` / `Qt5Qml.dll` [7.8 MB], `d3dcompiler_47.dll` / `libGLESv2.dll` [7.2 MB], `Qt5Network.dll` [1.3 MB], and headless platform plugins).
  - **Excluded `cryptography` & CFFI**: Excluded `cryptography` (9.5 MB) and `libcrypto-3.dll` (5.0 MB) from PyInstaller bundling since Python's standard `_ssl` natively handles all HTTPS network requests.

- **12-Point Lightweight Performance & Responsiveness Engine**:
  - **Lazy Category Page Construction in ThemeEditorWidget**: Converted `ThemeEditorWidget` from eagerly instantiating all 6 category pages (300+ widgets) on load to on-demand construction (`_build_category_page_content`) when each category is clicked. Slashes initialization time and cuts startup widgets by ~250.
  - **Lazy Tab Execution in ModifyWidget**: Removed startup timer `QTimer.singleShot(200, self.refresh)` in `ImportsWidget`. Multi-file AST parsing now executes only on first tab activation or explicit switch.
  - **Flattened Plugin Card Widget Hierarchy**: Removed intermediate `QWidget#iconContainer` and `QVBoxLayout` wrappers from `create_plugin_card` in `launcher.pyw`, embedding `QLabel#iconLabel` directly into the card layout and eliminating ~100 redundant nested layout containers.
  - **True Viewport Plugin Icon Loading**: Eliminated eager icon loading for all 50 plugin cards in `create_plugin_card`. Plugin cards initialize instantly with cached default icons; actual plugin icons load asynchronously strictly when scrolled into view via debounced `check_visible_cards()`.
  - **In-Memory LRU Cache for `.cur` / `.ani` Images**: Added `_image_cache` and `_pixmap_cache` with timestamp validation and bounded capacity (256 items) to `CurGenerator` in `cursor_widget.py`, avoiding repeated binary RIFF parsing and Windows GDI handle leaks.
  - **Bounded Dynamic MDL2 & Font Icon Caches**: Bounded `_font_icon_cache` and `_mdl2_icon_cache` in `utils.py` and `_crisp_pixmap_cache` to prevent memory growth during long sessions.
  - **Event-Driven Log Monitoring**: Increased fallback heartbeat polling interval in `ShellLogMonitor` (`nss_error_monitor.py`) from 2,000ms to 15,000ms, relying directly on `QFileSystemWatcher` file change notifications and eliminating continuous CPU wakeups.
  - **Batched Grid & Layout Updates**: Wrapped card and theme grid rebuilding in `ThemeSwitcherWidget.refresh_list()` and `PluginManager.recalculate_plugin_grid()` in `setUpdatesEnabled(False)` ... `setUpdatesEnabled(True)` to prevent costly relayout passes.
  - **Pre-Compiled NSS Parser Regexes**: Hoisted and pre-compiled recurring regex objects (`_RE_WORD_KEY`, `_RE_ID_EXTRACT`, `_RE_HASHED_ICON`) in `nss_parser.py`.
  - **Debounced External Sync & Selective AST Invalidation**: `_handle_file_sync` only triggers AST re-parsing of `ImportsWidget` if its tab is currently active; otherwise marks dirty for lazy evaluation on next visit.
  - **Side Panel Memory Management**: Added delayed generational garbage collection (`gc.collect(1)`) on tab transitions in `PluginManager.create_side_panel`.
  - **Total Startup Widget Count Reduction**: Dropped active `QWidget` count at startup from **812** down to **150** (~81.5% reduction) with startup latency reduced to **< 580ms**.

- **Instant App Launch & Event Loop Non-Blocking Architecture**:
  - **Eliminated Startup Pre-Warming Freeze**: Removed main-thread `_prewarm_secondary_pages` timers that previously froze the GUI event loop for 2.5+ seconds at startup by attempting to build heavy secondary pages (`ModifyWidget`, `ThemeSwitcherWidget`, `CursorGalleryWidget`, `SettingsPage`) on the Qt main thread. Secondary pages now instantiate instantaneously on-demand when clicked.
  - **Instant Cursor Active Scheme Detection**: Rewrote `_detect_current_active_theme` in `cursor_widget.py` to query the Windows registry `Control Panel\Cursors` key once rather than looping over all 31 cursor directories, parsing 31 INFs with regex, and opening the registry 62 times. Drops detection latency from **813ms** down to **< 0.5ms**.
  - **Lazy IDS Tab Loading in ModifyWidget**: Defer instantiation of 130+ `IDEntryWidget` widgets in `ModifyWidget` until the user actually switches to the IDS tab (`tab.currentChanged`), cutting `ModifyWidget` load time from **511.8ms** down to **41.8ms**.
  - **Cached Scaled Theme Pixmaps & Fast Resolution**: Added `_theme_pixmap_cache` and fast content-length matching in `ThemeSwitcherWidget` to eliminate redundant disk reads and high-resolution PNG downscaling on UI creation, with dynamic cache resolution on card hover (`enterEvent`/`leaveEvent`).
  - **CRLF/LF Normalized Git SHA Matching**: Implemented `file_matches_git_sha` in `plugin_registry.py` to compare against raw, normalized LF, and normalized CRLF Git blob hashes. This resolved a bug in `FetchThemesWorker` (`ThemeSwitcherWidget`) that caused `Desert.nss`, `Forest.nss`, and `Sunset.nss` (committed with CRLF) to be continually flagged as modified and re-downloaded on every launch.
  - **Streamlined Module Initialization**: Removed synchronous `shell.exe -reload` execution from top-level `get_app_base_path` at module import, avoiding redundant shell unhook/rehook storms during app launch.
  - **Staggered Idle Background Workers**: Spaced out non-blocking background workers (`sync_tools_menu`, `QFileSystemWatcher`, `FetchPluginsThread`, `ShellLogMonitor`, and NSS snapshot) across idle intervals after initial window paint.

- **Non-Blocking Background Cursor Applying & In-Place Uninstall Scroll Lock**:
  - **Threaded Live Cursor Application**: Windows registry updating and `SystemParametersInfoW(SPI_SETCURSORS)` broadcast now execute on a background daemon thread, eliminating UI stutter and lag when auto-applying newly downloaded cursor packs.
  - **In-Place Card Uninstall**: Deleting/uninstalling a cursor on Explore and Fav tabs updates the card directly in-place without tearing down or rebuilding the grid, completely eliminating scrollbar position shifting.
- **Unified A-Z Grid Sorting & Stable Positioning**:
  - **Alphabetical A-Z Ordering Across Explore & Fav**: Unified installed and online cursor themes into a single merged dataset sorted strictly A-Z (`th_name.lower()`). Deleting or installing a cursor theme now preserves its exact grid position without displacing uninstalled packs to the bottom.
- **Unified Persistent Save & Reset Buttons & Add Theme inside My Themes**:
  - **Persistent Save & Reset**: Save and Reset buttons in the top-right corner layout are now permanently visible across all Theme tabs (`Themes`, `Editor`, and `Mouse`). Clicking Save/Reset applies or reverts changes across all 3 subsystems simultaneously with a single unified action.
  - **Relocated "Add Theme" Button**: Moved the "Add Theme" button out of the global corner action bar and placed it directly inside the "My Themes" tab header above the custom themes grid (`ThemeSwitcherWidget`), keeping the top bar minimalist and focused.
- **Cursor Store Fixes, Auto-Apply, Centered Title Status & Fav Empty State**:
  - **Case-Insensitive Deduplication & Resolution**: Resolved re-download issue for `Naruto` / `PandO dark` / `PandO light` by adding case-insensitive deduplication in `FetchCatalogWorker` and case-insensitive matching between remote catalog items and `cursor/` folder on disk.
  - **Uninstall to Re-Download Card State**: Fixed card state transition in `set_installed_state` so uninstalling a cursor pack completely cleans up `uninstall_btn`, recreates `download_btn` (`\uE118`), restores online pack previews, and resets tooltips.
  - **Auto-Apply on Download**: Completed cursor downloads now immediately auto-apply to Windows (`self._on_card_selected(theme_name)`), ensuring the last finished download becomes active.
  - **Centered Title Bar Status**: Moved status messages from the tab/button corner layout into a dedicated centered title bar label (`self.title_status_label`) in `create_title_bar()`, preventing UI shift of action buttons and tabs.
  - **Centered Fav Empty State**: Replaced default top-left text with a centered `QVBoxLayout` container featuring a golden star icon (`\uE734`), bold title, and instructions centered in the viewport.
- **NSS Item & Menu Parser & Imports Tab Fix**:
  - **Nested Menu & Item Body Parsing**: Fixed token index advancement in `find_items_and_menus` (`nss_parser.py`) which previously advanced past closing braces (`i = temp_i`), inadvertently skipping all child `item(...)` and submenu definitions inside menu bodies `{ ... }`.
  - **Imports Tab Filtering & Search**: Resolved issue where only menus appeared and items were missing in the Imports tab; search queries (e.g. `Settings`, `Directory`) and type filter tags (`All`, `Item`, `Menu`) now correctly discover, filter, and display all items and menus across all imported `.nss` files (e.g., `taskbar.nss`, `valo.nss`).
  - **Safe UI Controls & Delegate Rendering**: Safeguarded button group state extraction in `FilterBar` (`checkedButton()`), added fallback title/label extraction in `NSSItemDelegate`, and connected tab activation in `ModifyWidget` to refresh the Imports tab on demand.
- **Wave 3: Maximum Launch Speed & Cold-Start Acceleration**:
  - **Deferred Heavy Submodule Imports**: Shifted `modify_widget`, `theme_switcher_widget`, `theme_editor_widget`, `cursor_widget`, `cloud_sync`, and `nss_error_monitor` from top-level imports in `launcher.pyw` into on-demand page getters and background tasks, reducing module import time from ~600ms to < 80ms.
  - **Non-Blocking Startup Pipeline**: Removed synchronous directory walking (`sync_tools_menu`) and DPAPI encryption reads (`CloudSyncManager`) from `PluginManager.__init__`. Tools menu synchronization is now asynchronous on a background daemon thread, and CloudSyncManager is instantiated lazily upon first access.
  - **LRU Cached Resource & Icon Atlas**: Added `@functools.lru_cache` to `resource_path` and fast in-memory dictionary caching for `get_mdl2_icon` and `get_font_icon` in `utils.py`, cutting redundant character rasterization and path calculations to 0ms.
  - **Background Pre-Warming**: Staggered secondary page pre-warming (`ModifyWidget`, `ThemeSwitcherWidget`, `SettingsPage`) across 200ms–1100ms idle intervals to deliver instant 0ms tab switching without delaying initial window paint.
  - **Background Cleanup**: Moved `_cleanup_old_executables` to a background daemon thread to eliminate startup temp file locking and disk I/O latency.
  - **Verified Standalone Packaging**: Recompiled and verified `--onefile` standalone binary build (`launcher.exe`, 47MB) with complete backward compatibility.
- **Wave 2 Modularization & Token Optimization**:
  - Extracted Nilesoft AST lexing, argument parsing, property formatting, rule replacement, and scanning engine into dedicated submodule `nss_parser.py`, trimming ~600 lines from `modify_widget.py`.
  - Extracted plugin download/install workers, icon download worker, thread management, and Markdown detail popup into dedicated submodule `plugin_workers.py`, trimming ~900 lines from `launcher.pyw`.
  - Consolidated canonical shared UI widgets (`FlowLayout`, `ModernSwitch`, `ModernDialog`, `PillProgressBar`, `normalize_path`) in `utils.py`, eliminating duplicate definitions across `launcher.pyw`, `modify_widget.py`, and `cursor_widget.py`.
  - Pre-computed and cached item search keys in `NSSItemModel` (`_stitle`, `_sfind`, `_sfile`, etc.), making real-time search filtering in `modify_widget.py` instant (<1ms) without CPU spikes or redundant string allocations.
  - Purged unused workspace artifacts (`lib/`, scratch dev notes).
  - Maintained 100% facade backward compatibility and verified `--onefile` PyInstaller standalone build (`launcher.exe`, 47MB).
- **Performance, CPU & Code Optimization (Wave 1)**:
  - Eliminated 1MB embedded compressed data bloat from `glyphs_data.py`: `utils.get_glyphs_data()` now reads directly from `fonts/glyphs.json` with an in-memory cache, saving ~15MB RAM and eliminating startup base64 decompression.
  - Removed CPU/GPU bottlenecking `QGraphicsDropShadowEffect` from `ThemeOptionFrame` (`theme_switcher_widget.py`) and `apply_card_style` (`launcher.pyw`), dropping scroll CPU usage from 70% to 0–2%.
  - Upgraded `load_crisp_pixmap` with a bounded LRU cache (`OrderedDict`, max 128 pixmaps) to prevent unbounded memory growth during plugin and cursor store browsing.
  - Increased `QFileSystemWatcher` debounce to 800ms and staggered secondary page pre-warming (Modify, Theme, Settings) to eliminate main UI thread startup stutter.
- **Deep INF & Native Alias Cursor Scheme Parser**:
  - Restored full original cursor structure and filenames across all 31 themes.
  - Implemented deep parser in `resolve_theme_directory_roles` supporting both Windows INF CSV positional scheme formats (`HKCU\Control Panel\Cursors\Schemes`) and key-value pairs (`HKCU\Control Panel\Cursors`), with automatic string variable expansion (`[Strings]`).
  - Added extended regex alias matching to map non-standard naming (e.g. `EWResize`, `NSResize`, `NWResize`, `NEResize`, `dgn1`, `dgn2`, `vert`, `horz`, `link`, `beam`, `unavaliable`, `pencil`, etc.) accurately without renaming files on disk.
  - Removed 37 unneeded `.txt`, `.pdf`, `.url`, and `.jpg` non-cursor files from cursor packs while keeping all original `.cur`, `.ani`, and `.inf` files intact.
  - Verified 100% path resolution and registry mapping across all 31 themes.
- **Mouse Cursor Store in Standalone Binary**:
  - Made cursor cache path dynamic so that when compiled to `launcher.exe`, `cache/cursors/` is placed beside the executable rather than deleted inside the ephemeral `_MEIPASS` temporary extraction directory.
  - Implemented multi-tier catalog fetcher (`FetchCatalogWorker`): CDN `cursors.json` (instant, 0 rate limits) -> Git Trees API -> Bundled / Cached fallback (`cursors.json` bundled into the binary).
  - Bundled 28 curated cursor themes into `cursors.json` and added PyInstaller `--add-data` config.
- **Fast & Responsive Updater (`UpdateWorker`)**:
  - Streamlined `check_for_updates`: Replaced 4 sequential rate-limited GitHub API endpoints with a single fast query to `https://api.github.com/repos/iMAboud/iMA-Menu-Plugins/releases/latest` (4s timeout) and CDN `version.json` fallback.
  - "Check for Update" in settings now responds instantly (< 0.5s) with zero UI freezing.
- **Fixed `_MEI*` Temporary Directory Warning upon Update**:
  - Removed aggressive startup `_MEI*` folder deletion in `updater.cs` / `ima_updater.exe` that conflicted with PyInstaller's exit routine while the launcher process was terminating.
  - Updated `apply_app_update` to cleanly close windows and stop watcher threads before launching the updater, allowing PyInstaller bootloader to shut down cleanly without file lock conflicts.
- **Startup Performance & UI Stability**:
  - Replaced concurrent `QThread` spam with `SequentialPreviewWorker` to eliminate audio stuttering and CPU spikes on startup.
  - Fixed `QLabel has been deleted` RuntimeError by routing previews through validated slot handlers.
  - Fixed Qt segmentation fault on clicking Download by preventing `QPushButton` self-deletion in its own click event.
- Fixed `NSSLexer` and `parse_nss_args` so that escaped quotes within strings (such as Nilesoft expressions like `vis='@if(...)'`) do not prematurely terminate strings or leak phantom attributes like `hidden=true normal=true`.
- Fixed raw glyph literal serialization in `format_nss_value` so that unicode glyph characters (`\uE150`, `\uE0D0`, etc.) are cleanly emitted unquoted (e.g. `icon=\uE150`, `image=\uE230`).
- Cleaned superfluous parentheses wrapping strings in properties (e.g. `menu=("Terminal")` -> `menu="Terminal"`).
- Updated `VisibilityWidget` to introduce a dedicated **Main** button (`vis=@if(key.shift() || key.control() || key.capslock() || key.lbutton(), 'hidden', 'normal')`), making **Normal** mean visible everywhere (omitting the `vis=` attribute entirely), and properly identifying existing Main conditional visibility expressions.
- Fixed `parse_nss_args` token parsing for long strings and SVGs containing inner double quotes and complex attributes so tokens are not truncated during file sync or parsing.
- Added deduplication by rule target criteria (`find`, `in`, `where`, `type`) and state preservation in `save_all_modifications` and `refresh_rules_model` to prevent duplicate lines when editing icons, glyphs, and SVGs.
- Upgraded C# updater (`ima_updater.exe` / `updater.cs`) to clean up legacy orphaned PyInstaller `_MEI*` temporary folders in `%TEMP%`.
- Updated release build pipeline (`build_launcher.py`) to automatically generate `runtime.zip` alongside `launcher.exe` for seamless zero-dependency GitHub releases.
- Enhanced `UpdateWorker` to support dynamic multi-release fallback discovery of `runtime.zip` without requiring redundant runtime re-uploads on standard code-only updates.
- Ensured 100% backward compatibility with legacy single-file users (single `launcher.exe` download replaces cleanly via elevated updater without breaking file tree).
- Preserved zero external prerequisites for end users (no Python or external runtimes needed).
- Normalized `format_nss_value` to strip any stray outer enclosing parentheses from `cmd` and `path` values (formatting as clean `cmd='...'` instead of `cmd=('...')`).
- Fixed NSS item replacement in `save_imported_item`: replaced precisely at header boundaries (`cmd_end`) instead of block bounds, preventing extra stray closing parentheses on nested menus.
- Fixed `format_nss_value` path formatting to ensure paths with spaces and parentheses (e.g. `(x86)`) in `cmd` and `path` properties remain properly wrapped in quotes (`cmd='...'`).
- Fixed icon preview containers in item and rule editor dialogs: optimized aspect-fit scaling and removed cutoffs for SVG, glyphs, and raster image icons.
- Enhanced "Inherit Icon" button to automatically resolve Windows Start Menu / desktop `.lnk` shortcuts, `.exe` paths, and app executables directly into `image=image.res('...')` without prompting for manual file selection unless no matching file could be found.
- Implemented 1000ms debounced auto-saving for Rule Editor dialogs and prevented disk rewrites when canceling without changes.
- Implemented infinite-scroll lazy loading for `GlyphBrowserDialog` in `modify_widget.py` (chunked batch rendering on-demand as user scrolls, opening instantly with 0ms lag).
- Added in-memory cached pixmap scaler in `load_crisp_pixmap` with optimal default bounds (96px) to eliminate redundant disk reads and icon decode stuttering.
- Optimized performance and eliminated UI freezes: removed CPU/GPU bottlenecking `QGraphicsDropShadowEffect` from individual widgets and cards, increased network stream buffer to 256KB for updates and installations, filtered staging/temporary files from triggering watcher sync cascades, and deduplicated `git_blob_sha`.
- Reduced binary size and startup unpack overhead in PyInstaller build configuration by excluding unused heavy standard library test suites and debug modules.
- Improved search accuracy and relevance ranking in Imports & Rules tabs (`NSSItemModel`): eliminated false positives caused by searching raw SVG/image strings with loose subsequence checks, and added multi-tiered relevance scoring to rank exact and title/file prefix matches at the top
- Fixed visibility parsing bug in `VisibilityWidget` where substring check on `key.shift()` falsely matched conditional expressions (e.g. `@if(key.shift() || key.control(), "hidden", "normal")`) and auto-selected Shift when editing icons/properties
- Preserved custom visibility expressions in `VisibilityWidget` and corrected format_nss_value pipe handling for boolean expressions
- Fixed plugin uninstall file handle locking by unwatching target plugin directories in `QFileSystemWatcher` before folder deletion
- Fixed `remove_nss_import` to robustly parse and delete any plugin import references from `shell.nss` (by name, folder, file, and regex)
- Added direct repository ZIP archive download fallback to `InstallationWorker` (bypasses GitHub REST API 60 req/hr rate limits)
- Made `FetchPluginsThread` tree data retrieval non-blocking so remote plugin manifest displays even if GitHub API is rate-limited
- Optimized GitHub API client (`github_client.py`): replaced heavy `/branches/main` with Git Refs API (`/git/ref/heads/main`), added exponential backoff (429/500/502/503/504), rate-limit awareness, proper User-Agent/Accept headers, and eliminated redundant API calls
- Plugin system with GitHub-based manifest and Git Trees API bulk downloads
- NSS file editor with syntax highlighting and auto-fix
- Theme switcher and visual theme editor with color picker/eyedropper
- Mouse cursor theme store and manager (`cursor_widget.py`) connected to GitHub repository (`iMAboud/iMA-Menu-cursors`) with background catalog syncing, disk-cached lazy preview loading, 1-click theme download, live Windows registry scheme application, and in-gallery theme uninstalling
- Google Drive cloud sync for backups
- NSS error monitoring with auto-healing
- SVG/glyph icon management
- Atomic file writes and crash-safe operations
- Frameless dark UI with acrylic transparency effects
- Added `wnd.is_` and `wnd.` expression safeguarding in `format_nss_value` and `heal_corrupted_nss_expr` to prevent unintended single-quoting when saving modified items.
- Added Noise (4) option to background.effect and changed its UI to a dropdown

---

## Completed Tasks

- [x] Single-instance enforcement with foreground window focus, taskbar flash, and zero-dependency Win32 IPC
- [x] Mouse cursor theme tab ("Mouse") inside Theme page, with `.cur` compiler, cursor role mix-and-match, and Windows registry scheme integration
- [x] Fast startup persistent runtime architecture (`--onedir` mode + `_internal/`)
- [x] Automated release asset packager (`runtime.zip` + `launcher.exe` in `build_launcher.py`)
- [x] Multi-release fallback discovery for `runtime.zip` in `UpdateWorker`
- [x] C# elevated updater (`ima_updater.exe`) stale temp cleanups
- [x] GitHub API optimization: Git Refs endpoint, exponential backoff, rate-limit handling, consolidated session
- [x] Core plugin store UI (PluginManager, plugin grid, detail view)
- [x] Plugin installation with staging/rollback pattern
- [x] NSS file editor (ModifyWidget) with undo/redo
- [x] Theme gallery (ThemeSwitcherWidget) and visual editor (ThemeEditorWidget)
- [x] Cloud sync via Google Drive OAuth2
- [x] NSS error monitor and auto-fixer
- [x] Shell integration (IPC, reload, error monitoring)
- [x] Plugin registry with disk reconciliation
- [x] Atomic JSON writes and safe file operations
- [x] Frameless dark UI with acrylic effects
- [x] Build pipeline (PyInstaller persistent runtime, VS2022 native builds)

---

## Pending Objectives

- [ ] Execute Master Optimization Plan Wave 2 (`plan.md`): Deep code streamlining, extracting `nss_parser.py` (~1,000 lines) and `plugin_workers.py` (~600 lines), pre-indexed instant search, duplicate class deduplication, and workspace purge while strictly maintaining `--onefile` standalone binary mode.

---

## Known Issues

- (None currently tracked — add issues as they are discovered)

---

## Notes

- Master Optimization Plan Wave 2 created in `plan.md` focusing on reducing code length across `modify_widget.py` (~4,309 lines) and `launcher.pyw` (~4,313 lines) to prevent AI token exhaustion and clutter while preserving 100% of features and `--onefile` packaging.
- All data stores are file-based JSON — no database.
- Native C++ source requires VS2022 with Detours and PlutoSVG dependencies.
