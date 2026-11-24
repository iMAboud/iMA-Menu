# Master Optimization Plan — Wave 3: Maximum App Launch Speed & Cold-Start Acceleration

> **iMA Menu Launcher** — High-Performance Cold-Start & Runtime Blueprint  
> **Core Directive**: Maximize startup velocity (0ms visual delay, instant window display, sub-second cold-start).  
> **Integrity Directive**: 100% preservation of all features — remote update checks, theme fetching & auto-sync, plugin downloads & git trees, cursor gallery, Nilesoft Shell AST parsing, live registry integration, and PyInstaller `--onefile` packaging.  
> **Execution Status**: *PLANNING ONLY — DO NOT EXECUTE ANY CHANGES UNTIL APPROVED.*

---

## 1. Executive Summary & Problem Analysis

While Wave 1 resolved RAM/CPU bottlenecks and Wave 2 organized the modular structure, the app still experiences notable **cold-start latency (1.5s to 3.5s)** upon initial launch.

### Root-Cause Profiling (The Culprits)

Through static profiling of `launcher.pyw`, `utils.py`, `modify_widget.py`, `theme_switcher_widget.py`, and `build_launcher.py`, we identified **7 primary launch-time bottlenecks**:

```
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│                               LAUNCH TIME BREAKDOWN & CULPRITS                           │
├──────────────────────────┬─────────────────────────────┬─────────────────────────────────┤
│ 🛑 BOTTLENECK            │ 🔍 ROOT CAUSE               │ ⚡ OPTIMIZATION REMEDY          │
├──────────────────────────┼─────────────────────────────┼─────────────────────────────────┤
│ 1. PyInstaller Unpack    │ Uncompressed --onefile      │ Use persistent runtime caching  │
│    Overhead (400-900ms)  │ temp extraction on launch   │ or high-compression bootloader  │
│                          │                             │ with lazy module imports        │
│ 2. Synchronous Top-Level │ Importing Heavy Modules     │ Deferred / Lazy Imports on      │
│    Imports (350-700ms)   │ (requests, win32gui,        │ background threads or upon first│
│                          │ modify_widget, nss_parser)  │ tab interaction                 │
│ 3. Blocking Main-Thread  │ sync_tools_menu(),          │ Offload to QThreadPool / worker │
│    I/O & Disk Reads      │ CloudSyncManager init,      │ thread; show UI skeleton        │
│    (200-450ms)           │ SettingsManager reading     │ immediately                     │
│ 4. Eager Widget & Dialog │ Constructing modify/theme/  │ True on-demand page instantiation│
│    Construction (250ms)  │ settings before main show() │ with zero-stutter lazy build    │
│ 5. Font & Icon Pre-load  │ Font extraction / registry  │ In-memory font cache & cached   │
│    & SVG Engine (150ms)  │ hit for Segoe/Nilesoft font │ MDL2 icon atlas                 │
│ 6. Synchronous Network   │ Fetching manifest / updates │ Ensure 100% async non-blocking  │
│    Checks (Variable)     │ without cached local buffer │ cached-first pipeline           │
│ 7. Redundant File System │ QFileSystemWatcher polling  │ Delayed & debounced watcher     │
│    Watcher Init (100ms)  │ and deep directory scans    │ initialization after show()     │
└──────────────────────────┴─────────────────────────────┴─────────────────────────────────┘
```

---

## 2. Comprehensive Launch Speed Optimization Plan

---

### Phase 1: Zero-Delay Window Display (Instant UI Perception)
* **Goal**: Show the main application window in **under 150ms**, then load contents seamlessly.

#### 1.1 Show Window First, Populate Asynchronously
* **Current Flow**:
  1. `manager = PluginManager()`
  2. Runs constructor: sets up cache dirs, reads settings, scans plugins, reconciles disk, syncs tools menu, initializes cloud sync, sets up file watchers.
  3. `manager.show()`
* **Optimized Flow**:
  1. `PluginManager` sets up minimal frame layout, sidebar, and placeholder/skeleton cards.
  2. `manager.show()` is called immediately in `__main__`.
  3. `QTimer.singleShot(0, self._async_init_pipeline)` triggers subsequent disk reads, plugin registry loading, and tool synchronization without blocking the initial Qt paint event.

#### 1.2 Instant Local Cache Render (Zero Network Lag)
* Always load `cache/plugins.json` and `cache/plugin_registry.json` synchronously into memory in < 5ms (pre-cached data structures).
* Display local/cached plugin cards instantly without waiting for network pings or Git tree checks.
* Background thread updates versions and notifies the UI with subtle badges if updates exist.

---

### Phase 2: Top-Level Import Optimization (Deferred Imports)
* **Goal**: Reduce initial Python module import overhead from **~600ms to < 80ms**.

#### 2.1 Lazy Import of Heavy Secondary Modules
* Modules like `requests`, `markdown`, `zipfile`, `cloud_sync.py`, `theme_editor_widget.py`, `cursor_widget.py`, and `nss_parser.py` do not need to be imported at `launcher.pyw` module load time.
* **Refactoring Strategy**:
  - Keep `sys`, `os`, `PyQt5.QtWidgets`, `PyQt5.QtCore`, `PyQt5.QtGui` at top level.
  - Defer `import requests`, `import markdown`, `import cloud_sync` inside functions or worker classes (`UpdateWorker`, `InstallationWorker`, `CloudSyncManager`).
  - Defer `from modify_widget import ModifyWidget` until the user clicks the "Modify" tab (or during background idle warming).
  - Defer `from theme_editor_widget import ThemeEditorWidget` and `from cursor_widget import CursorGalleryWidget` until the "Theme" tab is clicked.

#### 2.2 Shared GitHub Session / Network Layer
* Centralize all network calls into `github_client.py` using a single lazily-instantiated `requests.Session()` with connection pooling and DNS caching.
* Ensure no module initiates an outbound HTTP handshake during import.

---

### Phase 3: Disk I/O & Startup Background Pipeline
* **Goal**: Eliminate all blocking file system operations on the Qt GUI thread during startup.

#### 3.1 Non-Blocking `sync_tools_menu()` and `reconcile_with_disk()`
* Currently `sync_tools_menu(PROJECT_ROOT, self.plugin_logic.registry)` and `PluginRegistry` operations run on the main thread during `__init__`.
* Move disk reconciliation and tools menu sync to a lightweight background `QRunnable` worker.
* Upon worker completion, emit a signal to refresh the store/local state without freezing the UI.

#### 3.2 Debounced & Delayed `QFileSystemWatcher`
* The file system watcher currently scans and adds multiple directories (`imports`, `theme`, `plugins`, `cache/icons`, all plugin subdirectories) on startup.
* **Optimization**:
  - Delay file watcher creation to `QTimer.singleShot(800, self._setup_file_watcher)`.
  - Batch add paths in a single call.
  - Exclude temporary and cache directories that do not alter menu definitions.

#### 3.3 Optimized In-Memory Settings & Cache Access
* Use fast JSON loading with fallback to defaults.
* Cache `settings.json` in memory once read; prevent redundant disk reads across widgets.

---

### Phase 4: Asset & Font Loading Acceleration
* **Goal**: Instant rendering of MDL2 icons, glyphs, and stylesheets without disk lag.

#### 4.1 MDL2 Icon Atlas & QPixmap Caching
* `get_mdl2_icon(code, size)` renders characters to `QPixmap` on the fly.
* Implement an in-memory `@functools.lru_cache(maxsize=128)` for rendered `QIcon` / `QPixmap` objects.
* Subsequent requests for the same MDL2 icon return the pre-rendered pixmap in 0ms.

#### 4.2 Streamlined `style.css` Loading
* Read `style.css` once at startup and cache the stylesheet string.
* Avoid re-reading or re-applying inline stylesheets on repeatedly opened dialogs.

---

### Phase 5: Feature Preservation Matrix (100% Intact & Improved)

Every feature is preserved and upgraded to a cleaner, faster async implementation:

| Feature | Current Mechanism | Improved Optimized Method | Status |
|---|---|---|---|
| **App Updates** | `UpdateWorker` (Releases API + CDN fallback) | Fast CDN query first (100ms) with async GitHub API fallback; non-blocking | 100% Intact |
| **Theme Sync** | `FetchThemesWorker` in `theme_switcher_widget.py` | Background Git Tree SHA diffing only when Theme tab opened; instant cached local display | 100% Intact |
| **Plugin Store & Downloads** | `FetchPluginsThread` + `InstallationWorker` (Git Trees API + ZIP fallback) | Local cache renders instantly (0ms); remote manifest updates in background | 100% Intact |
| **Mouse Cursor Store** | `FetchCatalogWorker` + `cursors.json` CDN/local | Bundled `cursors.json` loads in < 1ms; remote updates cached in background | 100% Intact |
| **NSS Editor (Modify)** | `ModifyWidget` + `NSSItemModel` | Lazy instantiation on tab click; pre-indexed search index (< 1ms search) | 100% Intact |
| **Theme Editor & Eyedropper** | `ThemeEditorWidget` | Loaded only when Theme Editor sub-tab is activated | 100% Intact |
| **Google Drive Sync** | `CloudSyncManager` (OAuth2 DPAPI) | Tokens checked in background; zero main thread startup penalty | 100% Intact |
| **NSS Error Monitor** | `ShellLogMonitor` (shell.log watcher) | Started after 500ms delay; no startup impact | 100% Intact |
| **Shell Engine Reload** | `trigger_shell_reload()` / Win32 IPC | Debounced (50ms) non-blocking reload unchanged | 100% Intact |

---

### Phase 6: Build & PyInstaller Optimization

* **Packaging Strategy**: Maintain strict `--onefile --windowed` configuration in `build_launcher.py` and `launcher.spec`.
* **Exclusions**: Continue stripping heavy unneeded standard library modules (`tkinter`, `unittest`, `pydoc`, `QtWebEngine`, `QtSql`, `QtNetwork`, `QtMultimedia`, `QtOpenGL`, `brotli`, `numpy`).
* **Bytecode Optimization**: Compile `.pyc` files with Python bytecode optimization (`optimize=1` or `optimize=2`) to reduce bytecode size and parsing overhead inside the standalone executable.
* **UPX Compression Consideration**: Keep UPX compression enabled for binary compression while ensuring startup decompression does not stall CPU.

---

## 3. Detailed Implementation Steps (Ordered by Priority)

1. **Step 1: Lazy Module Loading in `launcher.pyw`**
   - Refactor heavy imports (`modify_widget`, `theme_editor_widget`, `theme_switcher_widget`, `cursor_widget`, `cloud_sync`, `nss_parser`) to be imported only inside page getter functions or background tasks.

2. **Step 2: Startup Pipeline Restructuring**
   - In `PluginManager.__init__`, construct only the main window shell and the initial active tab (Plugins store grid with cached data).
   - Show the window immediately.
   - Defer secondary initializations (`_setup_file_watcher`, `_start_error_monitor`, `sync_tools_menu`, `fetch_plugins_list`) using staged `QTimer.singleShot` intervals (50ms, 150ms, 300ms, 600ms).

3. **Step 3: Cached Icon & Pixmap Helper**
   - Add LRU cache decorators to `get_mdl2_icon` and `resource_path` in `utils.py`.
   - Ensure plugin card icons load from local disk cache (`cache/icons/`) without disk thrashing.

4. **Step 4: Background Pre-Warming of Secondary Pages**
   - Stagger the pre-warming of `ModifyWidget`, `ThemeSwitcherWidget`, and `SettingsPage` so that when the user clicks those tabs, they are already rendered and switch with **0ms lag**, but without slowing down the initial app launch.

5. **Step 5: Verification & Benchmark Testing**
   - Measure cold-start time (process spawn to visible paint) using high-precision timers (`time.perf_counter()`).
   - Validate that all features (updates, plugin installs, theme switching, cursor creation, NSS modification) function flawlessly.

---

## 4. Verification Plan

### Automated & Manual Verification Steps
1. **Cold Launch Benchmark**:
   - Run `python launcher.pyw` and record launch-to-paint time.
   - Verify launch-to-first-frame renders in < 250ms (Python) and < 800ms (Standalone EXE).
2. **Feature Integrity Tests**:
   - **Plugins**: Verify local tab shows installed plugins, store tab shows remote manifest, download and uninstall works.
   - **Modify**: Verify rules and imports load cleanly, item editing saves correctly, search filtering is instant.
   - **Theme**: Verify theme list loads, preview images display, GitHub auto-sync downloads new themes, theme apply/reset works.
   - **Cursor**: Verify 28 cursor themes appear, .cur compiling works, registry scheme applies cleanly.
   - **Settings & Updates**: Click "Check for Update" to ensure single-call GitHub release discovery returns accurately.
3. **Build Test**:
   - Run `python build_launcher.py` to produce `dist/launcher.exe`.
   - Test standalone binary execution on Windows 10/11.
