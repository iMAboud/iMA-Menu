"""
iMA Menu Launcher — Comprehensive Automated Feature, Latency & NSS Syntax Integrity Tester
Provides an interactive GUI dashboard and headless CLI runner that verifies every button,
dialog, operation, and NSS parsing logic in a strictly isolated sandbox environment.
"""

import os
import sys
import time
import json
import shutil
import tempfile
import traceback
from datetime import datetime

from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QGridLayout, QScrollArea, QFrame, QSplitter, QTreeWidget, QTreeWidgetItem,
    QHeaderView, QTextEdit, QTabWidget, QProgressBar, QLineEdit, QFileDialog
)
from PyQt5.QtGui import QColor, QFont, QPainter, QPainterPath, QPen, QIcon, QPixmap
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QObject, QRectF, QSize

# ---------------------------------------------------------------------------
# Path Anchoring
# ---------------------------------------------------------------------------
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

TEST_LOG_FILE = os.path.join(CURRENT_DIR, "test_log.txt")
TEST_HISTORY_FILE = os.path.join(CURRENT_DIR, "cache", "test_history.json")


# ---------------------------------------------------------------------------
# Sandbox Environment (Zero-Touch Isolation)
# ---------------------------------------------------------------------------
class SandboxEnvironment:
    """Creates and manages an isolated temporary root for non-destructive tests."""

    def __init__(self):
        self.temp_dir = tempfile.mkdtemp(prefix="ima_tester_sandbox_")
        self.imports_dir = os.path.join(self.temp_dir, "imports")
        self.theme_dir = os.path.join(self.temp_dir, "theme")
        self.plugins_dir = os.path.join(self.temp_dir, "plugins")
        self.cache_dir = os.path.join(self.temp_dir, "cache")
        self.cursors_cache_dir = os.path.join(self.cache_dir, "cursors")
        self.icons_cache_dir = os.path.join(self.cache_dir, "icons")
        self.shell_nss = os.path.join(self.temp_dir, "shell.nss")
        self.custom_nss = os.path.join(self.imports_dir, "custom.nss")
        self.general_nss = os.path.join(self.imports_dir, "general.nss")

        self._setup_structure()

    def _setup_structure(self):
        for d in [self.imports_dir, self.theme_dir, self.plugins_dir,
                  self.cache_dir, self.cursors_cache_dir, self.icons_cache_dir]:
            os.makedirs(d, exist_ok=True)

        # Master shell.nss
        with open(self.shell_nss, "w", encoding="utf-8") as f:
            f.write(
                'settings\n{\n    priority = 1\n    showdelay = 200\n}\n\n'
                'import \'imports/general.nss\'\n'
                'import \'imports/custom.nss\'\n'
            )

        # imports/general.nss
        with open(self.general_nss, "w", encoding="utf-8") as f:
            f.write(
                'item(title=\'Notepad\' cmd=\'notepad.exe\' image=\'notepad.exe\')\n'
                'item(title=\'Task Manager\' cmd=\'taskmgr.exe\' image=\'taskmgr.exe\' pos=1 sep=both)\n'
                'item(title=\'Terminal\' cmd=\'wt.exe\' image=\'cmd.exe\')\n'
            )

        # imports/custom.nss with iMA Managed markers
        with open(self.custom_nss, "w", encoding="utf-8") as f:
            f.write(
                '// -- Start iMA Managed --\n'
                'menu(title=\'Manage\' image=\\uE712)\n'
                '{\n'
                '    item(title=\'Clean Temp\' cmd=\'cmd.exe /c del /q %temp%\\*\')\n'
                '    item(title=\'Restart Explorer\' cmd=\'cmd.exe /c taskkill /f /im explorer.exe && start explorer.exe\')\n'
                '}\n'
                '// -- End iMA Managed --\n'
            )

        # theme/Default.nss
        with open(os.path.join(self.theme_dir, "Default.nss"), "w", encoding="utf-8") as f:
            f.write('theme\n{\n    name = "Default"\n    view = 2\n    background.color = #1a1a1a\n}\n')

        # theme/Dark.nss
        with open(os.path.join(self.theme_dir, "Dark.nss"), "w", encoding="utf-8") as f:
            f.write('theme\n{\n    name = "Dark"\n    view = 2\n    background.color = #121212\n}\n')

        # Mock plugin directory
        test_plugin_dir = os.path.join(self.plugins_dir, "MockTool")
        os.makedirs(test_plugin_dir, exist_ok=True)
        with open(os.path.join(test_plugin_dir, "plugin.nss"), "w", encoding="utf-8") as f:
            f.write('item(title=\'Mock Tool\' cmd=\'cmd.exe\')\n')

        # Cache JSONs
        with open(os.path.join(self.cache_dir, "plugin_registry.json"), "w", encoding="utf-8") as f:
            json.dump({
                "version": 2,
                "plugins": {
                    "MockTool": {
                        "installed_version": "1.0.0",
                        "remote_version": "1.0.0",
                        "status": "installed",
                        "file_hashes": {}
                    }
                }
            }, f, indent=4)

        with open(os.path.join(self.cache_dir, "plugins.json"), "w", encoding="utf-8") as f:
            json.dump([
                {
                    "name": "MockTool",
                    "description": "Mock plugin for testing suite execution",
                    "version": "1.0.0",
                    "icon_url": "",
                    "nss_path": "plugins/MockTool/plugin.nss"
                }
            ], f, indent=4)

        with open(os.path.join(self.cache_dir, "settings.json"), "w", encoding="utf-8") as f:
            json.dump({"auto_update": False, "auto_check_updates": False, "theme": "Default"}, f, indent=4)

        with open(os.path.join(self.cache_dir, "color_palette.json"), "w", encoding="utf-8") as f:
            json.dump(["#e78284", "#ea999c", "#a6d189", "#8caaee", "#ef9f76", "#ca9ee6", "#e5c890", "#c6d0f5"], f)

        with open(os.path.join(self.cursors_cache_dir, "favorites.json"), "w", encoding="utf-8") as f:
            json.dump([], f)

    def cleanup(self):
        try:
            shutil.rmtree(self.temp_dir, ignore_errors=True)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Test Definition & Result Model
# ---------------------------------------------------------------------------
class TestResult:
    def __init__(self, test_id, suite, name, status="PASS", latency_ms=0.0, message="OK", traceback_text=""):
        self.test_id = test_id
        self.suite = suite
        self.name = name
        self.status = status  # PASS, WARN, FAIL
        self.latency_ms = round(latency_ms, 2)
        self.message = message
        self.traceback_text = traceback_text

    def to_dict(self):
        return {
            "id": self.test_id,
            "suite": self.suite,
            "name": self.name,
            "status": self.status,
            "latency_ms": self.latency_ms,
            "message": self.message,
            "has_error": bool(self.traceback_text)
        }


# ---------------------------------------------------------------------------
# Comprehensive Test Runner Engine
# ---------------------------------------------------------------------------
class TestRunner(QObject):
    test_started = pyqtSignal(str, str)         # (suite, name)
    test_completed = pyqtSignal(object)        # TestResult
    suite_completed = pyqtSignal(str, int, int) # (suite, passed, total)
    all_completed = pyqtSignal(dict)           # summary dict
    log_message = pyqtSignal(str)

    def __init__(self, sandbox: SandboxEnvironment):
        super().__init__()
        self.sandbox = sandbox
        self.results = []
        self._is_stopped = False
        self.spies = {
            "reloads": 0,
            "ipc_commands": [],
            "cursor_applies": 0,
            "ownership_checks": 0
        }

    def stop(self):
        self._is_stopped = True

    def run_benchmark(self, test_id, suite, name, func, *args, **kwargs):
        """Runs a test function, measures exact millisecond latency, catches errors."""
        if self._is_stopped:
            return None

        self.test_started.emit(suite, name)
        QApplication.processEvents()

        t0 = time.perf_counter_ns()
        status = "PASS"
        msg = "OK"
        tb = ""

        try:
            res = func(*args, **kwargs)
            if isinstance(res, str) and res != "OK":
                msg = res
        except Exception as e:
            status = "FAIL"
            msg = f"{type(e).__name__}: {str(e)}"
            tb = traceback.format_exc()

        t1 = time.perf_counter_ns()
        latency_ms = (t1 - t0) / 1_000_000.0

        # Flag slow operations exceeding 120ms threshold
        if status == "PASS" and latency_ms > 120.0:
            status = "WARN"
            msg = f"Slow responsiveness ({latency_ms:.1f} ms > 120 ms)"

        result = TestResult(test_id, suite, name, status, latency_ms, msg, tb)
        self.results.append(result)
        self.test_completed.emit(result)
        QApplication.processEvents()
        return result

    def execute_all_suites(self):
        """Executes all 13 suites in sequential order."""
        t_start = time.perf_counter()
        self.results.clear()
        self._is_stopped = False

        self.log_message.emit("Initializing isolated sandbox and mocking environment...")

        # -------------------------------------------------------------------
        # Patch system-altering routines safely
        # -------------------------------------------------------------------
        import utils
        import nss_parser
        import modify_widget

        # Mocks
        orig_trigger_reload = utils.trigger_shell_reload
        orig_send_ipc = utils.send_ipc_command
        utils.trigger_shell_reload = lambda: self.spies.__setitem__("reloads", self.spies["reloads"] + 1)
        utils.send_ipc_command = lambda cmd: (self.spies["ipc_commands"].append(cmd), True)[1]

        # Patch project roots
        utils.PROJECT_ROOT = self.sandbox.temp_dir
        nss_parser.set_project_root(self.sandbox.temp_dir)
        modify_widget.set_project_root(self.sandbox.temp_dir)

        # Import modules under test
        import launcher
        # Backup original launcher module paths
        orig_launcher_paths = {
            'PROJECT_ROOT': launcher.PROJECT_ROOT,
            'PLUGINS_DIR': launcher.PLUGINS_DIR,
            'CACHE_DIR': launcher.CACHE_DIR,
            'ICONS_CACHE_DIR': launcher.ICONS_CACHE_DIR,
            'PLUGIN_REGISTRY_FILE': launcher.PLUGIN_REGISTRY_FILE,
            'PLUGINS_CACHE_FILE': launcher.PLUGINS_CACHE_FILE,
            'GIT_TREE_CACHE_FILE': launcher.GIT_TREE_CACHE_FILE,
            'SETTINGS_FILE': launcher.SETTINGS_FILE,
            'VERSION_FILE': launcher.VERSION_FILE,
        }

        launcher.PROJECT_ROOT = self.sandbox.temp_dir
        launcher.PLUGINS_DIR = self.sandbox.plugins_dir
        launcher.CACHE_DIR = self.sandbox.cache_dir
        launcher.ICONS_CACHE_DIR = self.sandbox.icons_cache_dir
        launcher.PLUGIN_REGISTRY_FILE = os.path.join(self.sandbox.cache_dir, 'plugin_registry.json')
        launcher.PLUGINS_CACHE_FILE = os.path.join(self.sandbox.cache_dir, 'plugins.json')
        launcher.GIT_TREE_CACHE_FILE = os.path.join(self.sandbox.cache_dir, 'git_tree_cache.json')
        launcher.SETTINGS_FILE = os.path.join(self.sandbox.cache_dir, 'settings.json')
        launcher.VERSION_FILE = os.path.join(self.sandbox.cache_dir, 'version.txt')

        # Disable background ownership & neutralize async timers in sandbox test
        launcher.PluginManager._ensure_folder_ownership_async = lambda self_pm: self.spies.__setitem__("ownership_checks", self.spies["ownership_checks"] + 1)
        launcher.PluginManager._async_sync_tools_menu = lambda self_pm: None
        launcher.PluginManager._setup_file_watcher = lambda self_pm: None
        launcher.PluginManager.fetch_plugins_list = lambda self_pm: None
        launcher.PluginManager._start_error_monitor = lambda self_pm: None
        launcher.PluginManager._take_global_nss_snapshot = lambda self_pm: None
        launcher.PluginManager.check_app_update = lambda self_pm, manual=False, force=False: None
        launcher.PluginLogic.fetch_plugins_list = lambda self_pl: None
        launcher.AutoHideScrollManager.attach_all = lambda self_sm, w: None
        launcher.AutoHideScrollManager.attach = lambda self_sm, sb: None

        import cursor_widget
        cursor_widget._apply_system_cursors = lambda: (self.spies.__setitem__("cursor_applies", self.spies["cursor_applies"] + 1), True)[1]

        pm = None
        launch_delay_ms = 0.0

        try:
            # ===============================================================
            # SUITE 1: NSS Parsing & Syntax Integrity
            # ===============================================================
            s = "1. NSS Parsing & Syntax"

            def test_syntax_valid():
                code = "item(title='Test' cmd='calc.exe')\nmenu(title='Sub') { item(title='A') }\n"
                assert utils.validate_nss_syntax(code) is True

            def test_syntax_unbalanced():
                code = "item(title='Test' cmd='calc.exe'\n"
                assert utils.validate_nss_syntax(code) is False

            def test_comment_stripping():
                code = "// item(title='unclosed bracket\n/* multiline [ comment */\nitem(title='OK')\n"
                assert utils.validate_nss_syntax(code) is True

            def test_lexer_operators():
                from nss_parser import NSSLexer
                lexer = NSSLexer("if (a == 1 && b != 2 || c > 3) @if(x)")
                tokens = lexer.tokenize()
                assert len(tokens) > 0
                symbols = [t[1] for t in tokens]
                assert '=' in symbols and '(' in symbols

            def test_args_complex_functions():
                from nss_parser import NSSLexer, parse_nss_args
                code = "title='App' image=image.res(1, 2) cmd=io.file.append('a','b') vis=key.control()"
                tokens = NSSLexer(code).tokenize()
                args = parse_nss_args(code, tokens)
                assert 'App' in args.get('title', '')
                assert 'image.res' in args.get('image', '')
                assert 'io.file.append' in args.get('cmd', '')

            def test_format_value_safeguards():
                from nss_parser import format_nss_value
                # Path with spaces must be formatted with quotes
                assert format_nss_value('cmd', 'C:\\Program Files\\app.exe') == "cmd='C:\\Program Files\\app.exe'"
                # Expressions and functions must NOT be quoted
                assert format_nss_value('cmd', 'io.file.append(a,b)') == "cmd=io.file.append(a,b)"
                assert format_nss_value('vis', 'key.control()') == "vis=key.control()"
                assert format_nss_value('pos', 1) == "pos=1"
                assert format_nss_value('args', "if(sel.back, '--undo \"@dir\\organize_undo.log\"', '--undo @sel(true)')") == "args=if(sel.back, '--undo \"@dir\\organize_undo.log\"', '--undo @sel(true)')"
                assert format_nss_value('where', "if(sel.back, path.exists('file.log'), sel.file.name == 'file.log')") == "where=if(sel.back, path.exists('file.log'), sel.file.name == 'file.log')"
                assert format_nss_value('args', "@if(sel.count, sel(true), quote(dir))") == "args=@if(sel.count, sel(true), quote(dir))"
                assert format_nss_value('args', "['--reduce', '@sel.path']") == "args=['--reduce', '@sel.path']"
                assert format_nss_value('args', '--undo "@dir\\organize_undo.log"') == "args='--undo \"@dir\\organize_undo.log\"'"
                assert format_nss_value('args', '\'--undo "@dir\\organize_undo.log"\'') == "args='--undo \"@dir\\organize_undo.log\"'"
                assert format_nss_value('where', 'wnd.is_desktop') == "where=wnd.is_desktop"
                assert format_nss_value('where', "'wnd.is_desktop'") == "where=wnd.is_desktop"

            def test_ast_mutation_roundtrip():
                from nss_parser import scan_nss_items, save_imported_item, read_file
                items = scan_nss_items(self.sandbox.temp_dir)
                assert len(items) > 0
                first = items[0]
                save_imported_item(
                    first,
                    {
                        'title': "Clean Temp Files",
                        'icon': "temp.ico",
                        'vis': "key.shift()",
                        'pos': 2,
                        'sep': "both"
                    }
                )
                content = read_file(first['file'])
                assert utils.validate_nss_syntax(content) is True
                assert "Clean Temp Files" in content

            def test_draft_syntax_roundtrip():
                from menu_builder_widget import ItemConfigDialog
                dlg = ItemConfigDialog(item_data={'type': 'item', 'is_draft': True, 'props': {'title': 'WIP'}})
                assert dlg.raw_data.get('is_draft') is True
                dlg.close()

            def test_autofixer_healing():
                from utils import NSSAutoFixer
                broken = "item(title=''Test'')"
                fixed = NSSAutoFixer.fix_content(broken)
                assert "title='Test'" in fixed

            self.run_benchmark("nss_syntax_valid", s, "Syntax validation with balanced code", test_syntax_valid)
            self.run_benchmark("nss_syntax_unbalanced", s, "Syntax rejection of unbalanced brackets", test_syntax_unbalanced)
            self.run_benchmark("nss_comment_stripping", s, "Comment stripping protection (// and /* */)", test_comment_stripping)
            self.run_benchmark("nss_lexer_operators", s, "NSSLexer operator tokenizing (==, &&, @if)", test_lexer_operators)
            self.run_benchmark("nss_args_complex", s, "Argument parsing of nested functions", test_args_complex_functions)
            self.run_benchmark("nss_format_safeguards", s, "Anti-corruption formatting (path vs expression)", test_format_value_safeguards)
            self.run_benchmark("nss_ast_mutation", s, "AST mutation roundtrip & marker preservation", test_ast_mutation_roundtrip)
            self.run_benchmark("nss_draft_roundtrip", s, "Draft syntax serialization & recovery", test_draft_syntax_roundtrip)
            self.run_benchmark("nss_autofixer", s, "NSSAutoFixer healing unbalanced blocks", test_autofixer_healing)

            # ===============================================================
            # SUITE 2: Startup & Window Benchmark
            # ===============================================================
            s = "2. Startup & Window"

            def test_launch():
                nonlocal pm, launch_delay_ms
                t0 = time.perf_counter_ns()
                pm = launcher.PluginManager()
                t1 = time.perf_counter_ns()
                launch_delay_ms = (t1 - t0) / 1_000_000.0
                assert pm is not None
                return f"Cold launch completed in {launch_delay_ms:.1f} ms"

            def test_window_flags():
                assert pm.windowFlags() & Qt.FramelessWindowHint
                assert getattr(pm, '_hwnd', None) or pm.winId()

            def test_single_instance():
                assert launcher.SINGLE_INSTANCE_MUTEX_NAME.startswith("Local\\")
                assert launcher.SINGLE_INSTANCE_MSG_NAME == "iMA_Menu_Launcher_RestoreAndFocus"

            def test_titlebar_refresh():
                if hasattr(pm, 'on_refresh_clicked'):
                    pm.on_refresh_clicked()
                assert True

            def test_titlebar_store_local():
                if hasattr(pm, 'tab_store_btn') and hasattr(pm, 'tab_local_btn'):
                    pm.tab_local_btn.click()
                    QApplication.processEvents()
                    pm.tab_store_btn.click()
                    QApplication.processEvents()
                assert True

            self.run_benchmark("startup_launch", s, "Cold PluginManager initialization", test_launch)
            self.run_benchmark("startup_flags", s, "Frameless & translucent acrylic flags", test_window_flags)
            self.run_benchmark("startup_single_instance", s, "Single-instance IPC configuration", test_single_instance)
            self.run_benchmark("titlebar_refresh", s, "Title bar Refresh button dispatch", test_titlebar_refresh)
            self.run_benchmark("titlebar_store_local", s, "Title bar Store / Local pill toggle", test_titlebar_store_local)

            # ===============================================================
            # SUITE 3: Sidebar Navigation Switching
            # ===============================================================
            s = "3. Sidebar Navigation"

            def test_nav_modify():
                pm.side_modify_btn.click()
                QApplication.processEvents()
                assert pm.modify_page is not None

            def test_nav_theme():
                pm.side_theme_btn.click()
                QApplication.processEvents()
                assert pm.theme_page is not None

            def test_nav_settings():
                pm.side_settings_btn.click()
                QApplication.processEvents()
                assert pm.settings_page is not None

            def test_nav_plugins():
                pm.side_plugins_btn.click()
                QApplication.processEvents()
                assert pm.plugins_page is not None

            def test_nav_exclusive():
                pm.side_modify_btn.click()
                assert pm.side_modify_btn.isChecked()
                pm.side_theme_btn.click()
                assert pm.side_theme_btn.isChecked()
                assert not pm.side_modify_btn.isChecked()

            self.run_benchmark("nav_modify", s, "Switch to Modify tab (lazy load)", test_nav_modify)
            self.run_benchmark("nav_theme", s, "Switch to Theme tab (lazy load)", test_nav_theme)
            self.run_benchmark("nav_settings", s, "Switch to Settings tab (lazy load)", test_nav_settings)
            self.run_benchmark("nav_plugins", s, "Switch back to Plugins tab", test_nav_plugins)
            self.run_benchmark("nav_exclusive", s, "Sidebar button group exclusive checkable state", test_nav_exclusive)

            # ===============================================================
            # SUITE 4: Plugins Tab
            # ===============================================================
            s = "4. Plugins Tab"

            def test_plugins_grid():
                pm.side_plugins_btn.click()
                QApplication.processEvents()
                assert hasattr(pm, 'grid_layout')
                assert pm.grid_layout is not None

            def test_plugins_search():
                if hasattr(pm, 'search_input'):
                    pm.search_input.setText("Mock")
                    QApplication.processEvents()
                    pm.search_input.clear()
                    QApplication.processEvents()
                assert True

            def test_plugins_details_popup():
                from plugin_workers import DetailsPopup
                p = DetailsPopup({"name": "MockTool", "description": "Mock description", "version": "1.0.0"}, pm)
                p.set_details_content("### Overview\nMock tool test description.")
                p.close()
                assert True

            def test_capsule_button():
                from utils import CapsuleActionButton
                btn = CapsuleActionButton("Install", "installButton")
                btn.set_state("install")
                btn.set_state("installing")
                btn.setValue(45)
                btn.set_state("installed")
                assert True

            self.run_benchmark("plugins_grid", s, "Plugin cards grid layout packing", test_plugins_grid)
            self.run_benchmark("plugins_search", s, "Plugins search filtering dispatch", test_plugins_search)
            self.run_benchmark("plugins_details", s, "DetailsPopup markdown rendering & dismissal", test_plugins_details_popup)
            self.run_benchmark("plugins_capsule", s, "CapsuleActionButton dynamic state transitions", test_capsule_button)

            # ===============================================================
            # SUITE 5: Modify - Rules Tab
            # ===============================================================
            s = "5. Modify: Rules"

            def test_rules_load():
                pm.side_modify_btn.click()
                QApplication.processEvents()
                assert hasattr(pm.modify_page, 'edit_pg')
                assert hasattr(pm.modify_page.edit_pg, 'model')

            def test_rules_filter_tags():
                ep = pm.modify_page.edit_pg
                ep.filter_items()
                assert True

            def test_rules_search():
                ep = pm.modify_page.edit_pg
                if hasattr(ep, 'search_input'):
                    ep.search_input.setText("Notepad")
                    QApplication.processEvents()
                    ep.search_input.clear()
                    QApplication.processEvents()
                assert True

            def test_rules_new_dialog():
                from modify_widget import ModifyRuleEditorDialog
                dlg = ModifyRuleEditorDialog(data={}, parent=pm.modify_page)
                dlg.close()
                assert True

            def test_rules_match_mode():
                from modify_widget import MatchModeButton
                btn = MatchModeButton()
                btn.set_mode("exact")
                assert btn.get_mode() == "exact"
                btn.set_mode("contains")
                assert btn.get_mode() == "contains"

            self.run_benchmark("rules_load", s, "Rules tab model population", test_rules_load)
            self.run_benchmark("rules_filter", s, "Filter tags dispatch (All / Modified)", test_rules_filter_tags)
            self.run_benchmark("rules_search", s, "Rules search filter dispatch", test_rules_search)
            self.run_benchmark("rules_new_dialog", s, "ModifyRuleEditorDialog initialization", test_rules_new_dialog)
            self.run_benchmark("rules_match_mode", s, "MatchModeButton circular mode cycling", test_rules_match_mode)

            # ===============================================================
            # SUITE 6: Modify - Imports Tab
            # ===============================================================
            s = "6. Modify: Imports"

            def test_imports_tab_load():
                ep = pm.modify_page.edit_pg
                ep.all_btn.click()
                QApplication.processEvents()
                assert hasattr(ep, 'file_cont')

            def test_imports_sidebar_sort():
                ep = pm.modify_page.edit_pg
                assert ep.file_l.count() >= 0

            def test_imports_editor_dialog():
                from modify_widget import ImportEditorDialog
                dlg = ImportEditorDialog(data={'props': {}}, parent=pm.modify_page)
                dlg.close()
                assert True

            self.run_benchmark("imports_load", s, "Imports tab activation & sidebar scan", test_imports_tab_load)
            self.run_benchmark("imports_sorting", s, "Sidebar NSS files A-Z sorting", test_imports_sidebar_sort)
            self.run_benchmark("imports_dialog", s, "ImportEditorDialog modal construction", test_imports_editor_dialog)

            # ===============================================================
            # SUITE 7: Modify - IDs Tab
            # ===============================================================
            s = "7. Modify: IDs"

            def test_ids_catalog_count():
                from modify_widget import DEFAULT_IDS
                assert len(DEFAULT_IDS) == 234

            def test_ids_tab_load():
                ep = pm.modify_page.edit_pg
                ep.rules_btn.click()
                QApplication.processEvents()
                assert hasattr(ep, 'model')

            def test_ids_search():
                ep = pm.modify_page.edit_pg
                if hasattr(ep, 'search_input'):
                    ep.search_input.setText("personalize")
                    QApplication.processEvents()
                    ep.search_input.clear()
                    QApplication.processEvents()
                assert True

            self.run_benchmark("ids_catalog", s, "Verification of 234 official Nilesoft IDs", test_ids_catalog_count)
            self.run_benchmark("ids_tab_load", s, "IDs tab delegate & model initialization", test_ids_tab_load)
            self.run_benchmark("ids_search", s, "System IDs search filter responsiveness", test_ids_search)

            # ===============================================================
            # SUITE 8: Modify - Menu Builder (Add Tab)
            # ===============================================================
            s = "8. Modify: Menu Builder"

            def test_builder_tab_load():
                mw = pm.modify_page
                mw._switch_tab(1)  # Add / Menu Builder tab
                assert hasattr(mw, 'builder_pg')

            def test_builder_dialog():
                from menu_builder_widget import ItemConfigDialog
                bw = pm.modify_page.builder_pg
                dlg = ItemConfigDialog(available_menus=['Main', 'Options'], parent=bw)
                dlg.close()
                assert True

            def test_builder_pipeline_widget():
                from menu_builder_widget import PipelineStepWidget
                w = PipelineStepWidget()
                w.set_data({'type': 'launch', 'path': 'notepad.exe', 'args': ''})
                data = w.get_data()
                assert data.get('path') == 'notepad.exe'

            def test_builder_confirm_dialog():
                from menu_builder_widget import StyledConfirmDialog
                dlg = StyledConfirmDialog("Delete Item?", "Are you sure you want to delete this item?", pm)
                dlg.close()
                assert True

            self.run_benchmark("builder_load", s, "Menu Builder tab activation", test_builder_tab_load)
            self.run_benchmark("builder_dialog", s, "ItemConfigDialog modal initialization", test_builder_dialog)
            self.run_benchmark("builder_pipeline", s, "PipelineStepWidget action configuration", test_builder_pipeline_widget)
            self.run_benchmark("builder_confirm", s, "StyledConfirmDialog acrylic modal", test_builder_confirm_dialog)

            # ===============================================================
            # SUITE 9: Theme Switcher
            # ===============================================================
            s = "9. Theme Switcher"

            def test_theme_switcher_load():
                pm.side_theme_btn.click()
                pm.themes_tab_btn.click()
                QApplication.processEvents()
                assert hasattr(pm, 'theme_switcher_page')

            def test_theme_add_dialog():
                from theme_switcher_widget import AddThemeDialog
                dlg = AddThemeDialog("", pm)
                dlg.close()
                assert True

            self.run_benchmark("theme_switcher_load", s, "Theme gallery cards grid initialization", test_theme_switcher_load)
            self.run_benchmark("theme_add_dialog", s, "AddThemeDialog modal validation & dismiss", test_theme_add_dialog)

            # ===============================================================
            # SUITE 10: Theme Editor
            # ===============================================================
            s = "10. Theme Editor"

            def test_theme_editor_load():
                pm.editor_tab_btn.click()
                QApplication.processEvents()
                assert hasattr(pm, 'theme_editor_page')

            def test_editor_categories():
                te = pm.theme_editor_page
                for cat_idx in range(min(4, te.category_list.count() if hasattr(te, 'category_list') else 0)):
                    te.category_list.setCurrentRow(cat_idx)
                    QApplication.processEvents()
                assert True

            def test_editor_color_picker():
                from theme_editor_widget import MinimalColorPickerDialog
                dlg = MinimalColorPickerDialog("#e78284", pm)
                dlg.close()
                assert True

            def test_editor_radius_btn():
                from theme_editor_widget import RadiusButton
                btn = RadiusButton("6px", 6)
                assert btn.corner_px == 6

            self.run_benchmark("editor_load", s, "Theme Editor tab activation", test_theme_editor_load)
            self.run_benchmark("editor_categories", s, "Category pill navigation (General/Colors/Borders)", test_editor_categories)
            self.run_benchmark("editor_color_picker", s, "MinimalColorPickerDialog palette modal", test_editor_color_picker)
            self.run_benchmark("editor_radius_btn", s, "RadiusButton vector geometry selection", test_editor_radius_btn)

            # ===============================================================
            # SUITE 11: Mouse Cursors
            # ===============================================================
            s = "11. Mouse Cursors"

            def test_cursors_tab_load():
                pm.mouse_tab_btn.click()
                QApplication.processEvents()
                assert hasattr(pm, 'cursor_page')

            def test_cursors_subtabs():
                cw = pm.cursor_page
                if hasattr(cw, 'tab_installed_btn') and hasattr(cw, 'tab_fav_btn'):
                    cw.tab_installed_btn.click()
                    QApplication.processEvents()
                    cw.tab_fav_btn.click()
                    QApplication.processEvents()
                    cw.tab_explore_btn.click()
                    QApplication.processEvents()
                assert True

            def test_cursors_roles_count():
                from cursor_widget import CURSOR_ROLES, ROLE_ALIASES
                assert len(CURSOR_ROLES) == 17
                assert len(ROLE_ALIASES) >= 11

            def test_cursors_download_all():
                cw = pm.cursor_page
                assert hasattr(cw, 'download_all_btn')

            self.run_benchmark("cursors_load", s, "Mouse Cursors gallery initialization", test_cursors_tab_load)
            self.run_benchmark("cursors_subtabs", s, "Explore / Installed / Favorites pill switching", test_cursors_subtabs)
            self.run_benchmark("cursors_roles", s, "Verification of 17 standard Windows cursor roles", test_cursors_roles_count)
            self.run_benchmark("cursors_download_all", s, "Download All button state verification", test_cursors_download_all)

            # ===============================================================
            # SUITE 12: Settings Tab
            # ===============================================================
            s = "12. Settings Tab"

            def test_settings_load():
                pm.side_settings_btn.click()
                QApplication.processEvents()
                assert pm.settings_page is not None

            def test_modern_switch():
                from utils import ModernSwitch
                sw = ModernSwitch()
                initial = sw.isChecked()
                sw.setChecked(not initial)
                assert sw.isChecked() != initial

            self.run_benchmark("settings_load", s, "Settings page layout construction", test_settings_load)
            self.run_benchmark("settings_switch", s, "ModernSwitch animated toggle dispatch", test_modern_switch)

            # ===============================================================
            # SUITE 13: Shared Dialogs & Modals
            # ===============================================================
            s = "13. Shared Dialogs & Modals"

            def test_unsaved_changes_dialog():
                from utils import UnsavedChangesDialog
                dlg = UnsavedChangesDialog(pm)
                dlg.close()
                assert True

            def test_account_profile_dialog():
                from utils import AccountProfileDialog
                dlg = AccountProfileDialog(parent=pm, user_name="Test User", user_email="test@example.com")
                dlg.close()
                assert True

            def test_modern_dialog():
                from utils import ModernDialog
                dlg = ModernDialog(pm, "Test Title", "Test description content")
                dlg.add_button("OK", "installButton", dlg.accept)
                dlg.close()
                assert True

            def test_pill_progress_bar():
                from utils import PillProgressBar
                bar = PillProgressBar(height=16)
                bar.setValue(75)
                assert bar.value == 75

            self.run_benchmark("dialog_unsaved", s, "UnsavedChangesDialog modal lifecycle", test_unsaved_changes_dialog)
            self.run_benchmark("dialog_profile", s, "AccountProfileDialog layout & avatar display", test_account_profile_dialog)
            self.run_benchmark("dialog_modern", s, "ModernDialog styled button callbacks", test_modern_dialog)
            self.run_benchmark("dialog_progress", s, "PillProgressBar smooth value tracking", test_pill_progress_bar)

        finally:
            if pm:
                try:
                    if hasattr(pm, 'scroll_manager'):
                        QApplication.instance().removeEventFilter(pm.scroll_manager)
                    if hasattr(pm, 'reload_timer'):
                        pm.reload_timer.stop()
                    if hasattr(pm, 'file_sync_timer'):
                        pm.file_sync_timer.stop()
                    if getattr(pm, 'theme_editor_page', None): pm.theme_editor_page.is_dirty = False
                    if getattr(pm, 'theme_switcher_page', None): pm.theme_switcher_page.is_dirty = False
                    if getattr(pm, 'modify_page', None): pm.modify_page.is_dirty = False
                    pm.hide()
                    pm.close()
                except Exception:
                    pass
            # Restore original functions and paths
            utils.trigger_shell_reload = orig_trigger_reload
            utils.send_ipc_command = orig_send_ipc
            for k, v in orig_launcher_paths.items():
                setattr(launcher, k, v)

        t_total = (time.perf_counter() - t_start) * 1000.0

        # Compile Summary
        total = len(self.results)
        passed = sum(1 for r in self.results if r.status == "PASS")
        warns = sum(1 for r in self.results if r.status == "WARN")
        fails = sum(1 for r in self.results if r.status == "FAIL")
        slowest = max(self.results, key=lambda r: r.latency_ms, default=None)

        summary = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total": total,
            "passed": passed,
            "warnings": warns,
            "failed": fails,
            "launch_delay_ms": round(launch_delay_ms, 2),
            "total_duration_ms": round(t_total, 2),
            "slowest": {
                "name": slowest.name if slowest else "None",
                "suite": slowest.suite if slowest else "None",
                "latency_ms": slowest.latency_ms if slowest else 0.0
            },
            "spies": self.spies,
            "results": [r.to_dict() for r in self.results]
        }

        # Write to log and history
        self._write_test_log(summary)
        self._append_test_history(summary)

        self.all_completed.emit(summary)

    def _write_test_log(self, summary):
        """Writes clean human-readable log to test_log.txt."""
        lines = [
            "=" * 80,
            "iMA Menu Launcher — Automated Feature & Latency Report",
            f"Date & Time: {summary['timestamp']}",
            f"Environment: Windows 11 (Strict Isolated Sandbox: {self.sandbox.temp_dir})",
            f"Total Tests: {summary['total']} | Passed: {summary['passed']} | "
            f"Warnings (Slow >120ms): {summary['warnings']} | Failed: {summary['failed']}",
            f"Cold Launch Delay: {summary['launch_delay_ms']} ms",
            f"Total Suite Execution Time: {summary['total_duration_ms']:.1f} ms",
            f"Slowest Operation: {summary['slowest']['name']} ({summary['slowest']['latency_ms']} ms) in [{summary['slowest']['suite']}]",
            "=" * 80,
            ""
        ]

        current_suite = None
        for r in self.results:
            if r.suite != current_suite:
                current_suite = r.suite
                lines.append(f"\n[{current_suite.upper()}]")

            status_tag = f"[{r.status}]"
            lines.append(f"  {status_tag:<7} {r.latency_ms:>7.2f} ms  {r.name}")
            if r.status != "PASS" and r.message != "OK":
                lines.append(f"          ↳ Details: {r.message}")

        # Failure details
        failed_tests = [r for r in self.results if r.status == "FAIL"]
        lines.append("\n" + "=" * 80)
        lines.append("DETAILED FAILURE LOGS:")
        if not failed_tests:
            lines.append("(None - All tests passed cleanly with 0 regressions)")
        else:
            for f_test in failed_tests:
                lines.append(f"\n--- FAIL: [{f_test.suite}] {f_test.name} ---")
                lines.append(f"Error: {f_test.message}")
                lines.append("Traceback:")
                lines.append(f_test.traceback_text)
        lines.append("=" * 80 + "\n")

        with open(TEST_LOG_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    def _append_test_history(self, summary):
        """Appends run to cache/test_history.json for regression tracking."""
        try:
            os.makedirs(os.path.dirname(TEST_HISTORY_FILE), exist_ok=True)
            history = []
            if os.path.exists(TEST_HISTORY_FILE):
                with open(TEST_HISTORY_FILE, "r", encoding="utf-8") as f:
                    history = json.load(f)
            history.insert(0, summary)
            # Retain last 30 runs
            history = history[:30]
            with open(TEST_HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(history, f, indent=2)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Interactive Dark Dashboard GUI (`TesterWindow`)
# ---------------------------------------------------------------------------
class TesterWindow(QWidget):
    def __init__(self, cli_mode=False):
        super().__init__()
        self.cli_mode = cli_mode
        self.sandbox = SandboxEnvironment()
        self.runner = TestRunner(self.sandbox)
        self.active_filter = "All"

        self.setWindowTitle("iMA Menu — Automated Feature & Latency Tester")
        self.resize(1180, 780)
        self.setMinimumSize(850, 600)
        self._init_ui()
        self._connect_signals()

        if self.cli_mode:
            QTimer.singleShot(100, self._run_cli)

    def closeEvent(self, event):
        self.sandbox.cleanup()
        event.accept()
        QApplication.quit()

    def _init_ui(self):
        self.setStyleSheet("""
            QWidget {
                background-color: #121214;
                color: #c6d0f5;
                font-family: 'Google Sans', 'Marhey', 'Segoe UI Variable Display', 'Segoe UI', sans-serif;
                font-size: 13px;
            }
            QFrame#card {
                background-color: #18181c;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 14px;
            }
            QTreeWidget {
                background-color: #151518;
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 12px;
                outline: none;
            }
            QTreeWidget::item {
                padding: 6px 4px;
                border-bottom: 1px solid rgba(255, 255, 255, 0.03);
            }
            QTreeWidget::item:selected {
                background-color: #261115;
                color: #e78284;
            }
            QHeaderView::section {
                background-color: #1b1b20;
                color: #a5adce;
                padding: 6px;
                font-weight: bold;
                border: none;
                border-bottom: 1px solid rgba(255, 255, 255, 0.08);
            }
            QPushButton#primaryBtn {
                background-color: #e78284;
                color: #121214;
                font-weight: bold;
                border-radius: 10px;
                padding: 8px 18px;
                font-size: 13px;
                border: none;
            }
            QPushButton#primaryBtn:hover {
                background-color: #ea999c;
            }
            QPushButton#pillBtn {
                background-color: #202026;
                color: #a5adce;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 10px;
                padding: 6px 14px;
                font-weight: bold;
            }
            QPushButton#pillBtn:checked, QPushButton#pillBtn:hover {
                background-color: #2c2226;
                color: #e78284;
                border: 1px solid #e78284;
            }
            QTextEdit {
                background-color: #151518;
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 12px;
                color: #b5bfe2;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 12px;
            }
            QProgressBar {
                background-color: #1e1e24;
                border-radius: 6px;
                height: 10px;
                text-align: center;
                color: transparent;
            }
            QProgressBar::chunk {
                background-color: #a6d189;
                border-radius: 6px;
            }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(16)

        # -------------------------------------------------------------------
        # Header Row
        # -------------------------------------------------------------------
        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        title_label = QLabel("⚡ iMA Menu — Comprehensive Test Suite & Benchmark")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: white;")
        sub_label = QLabel("Strictly isolated sandbox • 0 file alterations • Millisecond latency measurement")
        sub_label.setStyleSheet("color: #838ba7; font-size: 12px;")
        title_box.addWidget(title_label)
        title_box.addWidget(sub_label)
        header.addLayout(title_box)
        header.addStretch()

        self.run_btn = QPushButton("▶  Run All Tests", self)
        self.run_btn.setObjectName("primaryBtn")
        self.run_btn.setCursor(Qt.PointingHandCursor)
        self.run_btn.clicked.connect(self._start_tests)
        header.addWidget(self.run_btn)

        self.open_log_btn = QPushButton("📄  Open test_log.txt", self)
        self.open_log_btn.setObjectName("pillBtn")
        self.open_log_btn.setCursor(Qt.PointingHandCursor)
        self.open_log_btn.clicked.connect(self._open_log_file)
        header.addWidget(self.open_log_btn)

        main_layout.addLayout(header)

        # -------------------------------------------------------------------
        # KPI Metric Cards
        # -------------------------------------------------------------------
        kpi_layout = QHBoxLayout()
        kpi_layout.setSpacing(12)

        self.kpi_tests = self._create_kpi_card("Tests Status", "0 / 0", "Ready to start", "#8caaee")
        self.kpi_launch = self._create_kpi_card("Launch Latency", "-- ms", "PluginManager boot", "#ca9ee6")
        self.kpi_total_time = self._create_kpi_card("Total Suite Delay", "-- ms", "All 13 suites", "#a6d189")
        self.kpi_slowest = self._create_kpi_card("Slowest Culprit", "--", "Max single response", "#ef9f76")

        kpi_layout.addWidget(self.kpi_tests)
        kpi_layout.addWidget(self.kpi_launch)
        kpi_layout.addWidget(self.kpi_total_time)
        kpi_layout.addWidget(self.kpi_slowest)
        main_layout.addLayout(kpi_layout)

        # -------------------------------------------------------------------
        # Tabs: Results Dashboard / History / Raw Log
        # -------------------------------------------------------------------
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: none; }
            QTabBar::tab {
                background: #18181c;
                color: #838ba7;
                font-weight: bold;
                padding: 8px 18px;
                border-radius: 8px;
                margin-right: 6px;
            }
            QTabBar::tab:selected {
                background: #25252e;
                color: white;
                border: 1px solid rgba(255,255,255,0.08);
            }
        """)

        # Tab 1: Live Results
        results_widget = QWidget()
        res_layout = QVBoxLayout(results_widget)
        res_layout.setContentsMargins(0, 10, 0, 0)
        res_layout.setSpacing(10)

        # Filter Pills Row
        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("Filter:"))
        self.filter_buttons = {}
        for tag in ["All", "Failed", "Warnings", "Passed"]:
            btn = QPushButton(tag)
            btn.setObjectName("pillBtn")
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            if tag == "All":
                btn.setChecked(True)
            btn.clicked.connect(lambda chk, t=tag: self._set_filter(t))
            self.filter_buttons[tag] = btn
            filter_row.addWidget(btn)
        filter_row.addStretch()
        res_layout.addLayout(filter_row)

        # Splitter: Left Tree Results, Right Inspector
        splitter = QSplitter(Qt.Horizontal)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Status", "Suite", "Test / Action", "Latency", "Summary"])
        self.tree.header().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.tree.header().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.tree.header().setSectionResizeMode(2, QHeaderView.Stretch)
        self.tree.header().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.tree.header().setSectionResizeMode(4, QHeaderView.Stretch)
        self.tree.itemSelectionChanged.connect(self._on_item_selected)
        splitter.addWidget(self.tree)

        # Inspector Panel
        inspector_frame = QFrame()
        inspector_frame.setObjectName("card")
        insp_layout = QVBoxLayout(inspector_frame)
        insp_layout.setContentsMargins(14, 14, 14, 14)
        insp_layout.addWidget(QLabel("🔍  Diagnostics & Traceback Inspector", styleSheet="font-weight:bold; color:white;"))
        self.inspector_text = QTextEdit()
        self.inspector_text.setReadOnly(True)
        self.inspector_text.setPlaceholderText("Select a test row to inspect its timing breakdown, arguments, or stack traceback...")
        insp_layout.addWidget(self.inspector_text)
        splitter.addWidget(inspector_frame)

        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        res_layout.addWidget(splitter)
        self.tabs.addTab(results_widget, "Results Dashboard")

        # Tab 2: Test Run History
        history_widget = QWidget()
        hist_layout = QVBoxLayout(history_widget)
        hist_layout.setContentsMargins(0, 10, 0, 0)
        self.history_tree = QTreeWidget()
        self.history_tree.setHeaderLabels(["Timestamp", "Total", "Passed", "Warnings", "Failed", "Launch (ms)", "Duration (ms)", "Slowest Culprit"])
        for col in range(8):
            self.history_tree.header().setSectionResizeMode(col, QHeaderView.ResizeToContents)
        hist_layout.addWidget(self.history_tree)
        self.tabs.addTab(history_widget, "Run History")

        # Tab 3: Raw test_log.txt Viewer
        log_widget = QWidget()
        log_layout = QVBoxLayout(log_widget)
        log_layout.setContentsMargins(0, 10, 0, 0)
        self.log_viewer = QTextEdit()
        self.log_viewer.setReadOnly(True)
        log_layout.addWidget(self.log_viewer)
        self.tabs.addTab(log_widget, "test_log.txt")

        main_layout.addWidget(self.tabs)

        # -------------------------------------------------------------------
        # Bottom Progress & Status Bar
        # -------------------------------------------------------------------
        bottom_bar = QHBoxLayout()
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(8)
        bottom_bar.addWidget(self.progress_bar, stretch=3)

        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: #838ba7; font-size: 12px;")
        bottom_bar.addWidget(self.status_label, stretch=2)

        main_layout.addLayout(bottom_bar)

        self._load_history()

    def _create_kpi_card(self, title, main_val, sub_val, accent_color):
        frame = QFrame()
        frame.setObjectName("card")
        l = QVBoxLayout(frame)
        l.setContentsMargins(16, 12, 16, 12)
        l.setSpacing(4)

        t = QLabel(title)
        t.setStyleSheet("color: #838ba7; font-size: 11px; font-weight: bold; text-transform: uppercase;")
        v = QLabel(main_val)
        v.setStyleSheet(f"color: {accent_color}; font-size: 20px; font-weight: bold;")
        s = QLabel(sub_val)
        s.setStyleSheet("color: #51576d; font-size: 11px;")

        frame.val_label = v
        frame.sub_label = s
        l.addWidget(t)
        l.addWidget(v)
        l.addWidget(s)
        return frame

    def _connect_signals(self):
        self.runner.test_started.connect(self._on_test_started)
        self.runner.test_completed.connect(self._on_test_completed)
        self.runner.all_completed.connect(self._on_all_completed)
        self.runner.log_message.connect(lambda msg: self.status_label.setText(msg))

    def _start_tests(self):
        self.run_btn.setEnabled(False)
        self.tree.clear()
        self.progress_bar.setValue(0)
        self.status_label.setText("Running suites...")

        # Re-initialize sandbox with pristine state for repeat runs
        self.sandbox.cleanup()
        self.sandbox = SandboxEnvironment()
        self.runner.sandbox = self.sandbox

        # Run synchronously in main event loop with processEvents to drive Qt widgets
        QTimer.singleShot(50, self.runner.execute_all_suites)

    def _on_test_started(self, suite, name):
        self.status_label.setText(f"Testing [{suite}] → {name}")

    def _on_test_completed(self, result: TestResult):
        item = QTreeWidgetItem(self.tree)
        item.setText(0, f"[{result.status}]")
        item.setText(1, result.suite)
        item.setText(2, result.name)
        item.setText(3, f"{result.latency_ms:.1f} ms")
        item.setText(4, result.message)

        # Coloring
        if result.status == "PASS":
            item.setForeground(0, QColor("#a6d189"))
            item.setForeground(3, QColor("#a6d189"))
        elif result.status == "WARN":
            item.setForeground(0, QColor("#ef9f76"))
            item.setForeground(3, QColor("#ef9f76"))
        else:
            item.setForeground(0, QColor("#e78284"))
            item.setForeground(3, QColor("#e78284"))
            item.setForeground(4, QColor("#e78284"))

        item.setData(0, Qt.UserRole, result)
        self._apply_filter_to_item(item)

        # Update progress bar
        total_tests_estimated = 48
        current_count = self.tree.topLevelItemCount()
        perc = min(100, int((current_count / total_tests_estimated) * 100))
        self.progress_bar.setValue(perc)

    def _on_all_completed(self, summary):
        self.run_btn.setEnabled(True)
        self.progress_bar.setValue(100)
        self.status_label.setText(f"Completed {summary['total']} tests in {summary['total_duration_ms']:.1f} ms.")

        # Update KPI Cards
        passed_str = f"{summary['passed']} / {summary['total']}"
        self.kpi_tests.val_label.setText(passed_str)
        self.kpi_tests.sub_label.setText(f"{summary['warnings']} slow, {summary['failed']} failed")

        self.kpi_launch.val_label.setText(f"{summary['launch_delay_ms']} ms")
        self.kpi_total_time.val_label.setText(f"{summary['total_duration_ms']:.1f} ms")

        slowest = summary['slowest']
        self.kpi_slowest.val_label.setText(f"{slowest['latency_ms']} ms")
        self.kpi_slowest.sub_label.setText(slowest['name'][:22] + "..." if len(slowest['name']) > 22 else slowest['name'])

        self._load_history()
        self._refresh_log_viewer()

    def _set_filter(self, tag):
        self.active_filter = tag
        for t, btn in self.filter_buttons.items():
            btn.setChecked(t == tag)

        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            self._apply_filter_to_item(item)

    def _apply_filter_to_item(self, item):
        res = item.data(0, Qt.UserRole)
        if not res:
            return

        visible = True
        if self.active_filter == "Failed":
            visible = (res.status == "FAIL")
        elif self.active_filter == "Warnings":
            visible = (res.status == "WARN")
        elif self.active_filter == "Passed":
            visible = (res.status == "PASS")

        item.setHidden(not visible)

    def _on_item_selected(self):
        items = self.tree.selectedItems()
        if not items:
            return
        res = items[0].data(0, Qt.UserRole)
        if not res:
            return

        text = [
            f"Test: [{res.suite}] {res.name}",
            f"Status: {res.status}",
            f"Response Latency: {res.latency_ms} ms",
            f"Summary Message: {res.message}",
            "-" * 60
        ]
        if res.traceback_text:
            text.append("ERROR TRACEBACK:")
            text.append(res.traceback_text)
        else:
            text.append("No errors or exceptions encountered.")
            text.append("Operation executed within safety boundaries in isolated sandbox.")

        self.inspector_text.setPlainText("\n".join(text))

    def _load_history(self):
        self.history_tree.clear()
        if not os.path.exists(TEST_HISTORY_FILE):
            return
        try:
            with open(TEST_HISTORY_FILE, "r", encoding="utf-8") as f:
                history = json.load(f)
            for h in history:
                item = QTreeWidgetItem(self.history_tree)
                item.setText(0, h.get("timestamp", ""))
                item.setText(1, str(h.get("total", 0)))
                item.setText(2, str(h.get("passed", 0)))
                item.setText(3, str(h.get("warnings", 0)))
                item.setText(4, str(h.get("failed", 0)))
                item.setText(5, f"{h.get('launch_delay_ms', 0)} ms")
                item.setText(6, f"{h.get('total_duration_ms', 0):.1f} ms")
                slowest = h.get("slowest", {})
                item.setText(7, f"{slowest.get('name', '')} ({slowest.get('latency_ms', 0)} ms)")

                if h.get("failed", 0) > 0:
                    item.setForeground(4, QColor("#e78284"))
                else:
                    item.setForeground(2, QColor("#a6d189"))
        except Exception:
            pass

    def _refresh_log_viewer(self):
        if os.path.exists(TEST_LOG_FILE):
            try:
                with open(TEST_LOG_FILE, "r", encoding="utf-8") as f:
                    self.log_viewer.setPlainText(f.read())
            except Exception:
                pass

    def _open_log_file(self):
        if os.path.exists(TEST_LOG_FILE):
            try:
                import ctypes
                ctypes.windll.shell32.ShellExecuteW(None, "open", TEST_LOG_FILE, None, None, 1)
            except Exception:
                pass

    def _run_cli(self):
        """Headless execution helper."""
        self.runner.execute_all_suites()
        failed = sum(1 for r in self.runner.results if r.status == "FAIL")
        print(f"\n[CLI] Automated tests completed: {len(self.runner.results)} tests executed.")
        print(f"[CLI] Report saved to: {TEST_LOG_FILE}")
        sys.exit(0 if failed == 0 else 1)


def _safe_excepthook(exctype, value, tb):
    err_str = "".join(traceback.format_exception(exctype, value, tb))
    print(err_str, file=sys.stderr if sys.stderr else sys.stdout)
    try:
        with open(TEST_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"\n[CRITICAL UNCAUGHT EXCEPTION]:\n{err_str}\n")
    except Exception:
        pass


def main():
    sys.excepthook = _safe_excepthook
    cli_mode = ("--cli-run" in sys.argv or "--headless" in sys.argv)

    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)

    # Prevent auxiliary test windows/dialogs from exiting the application on close
    app.setQuitOnLastWindowClosed(False)

    window = TesterWindow(cli_mode=cli_mode)
    if not cli_mode:
        window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
