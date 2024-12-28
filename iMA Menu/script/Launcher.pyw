import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QTabWidget, QVBoxLayout, QWidget, QDesktopWidget
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import pyqtSignal, QObject, QEvent
import os
from modify import MainWindow as ModifyWindow
from theme import ThemeEditor
from shortcut import MainWindow as ShortcutWindow
from PyQt5 import QtCore
from shell import ShellEditor
import tkinter as tk

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ICONS_PATH = os.path.join(SCRIPT_DIR, "..", "icons")

sys.path.append(SCRIPT_DIR)

class TkinterWidget(QWidget):
    closed = pyqtSignal()
    def __init__(self, parent=None, **kwargs):
        super().__init__(parent)
        self.window_closed = False
        self.setFocusPolicy(QtCore.Qt.StrongFocus)

    def show(self, window=None):
        super().show()
        if not hasattr(self, "window_id") or not self.window_id:
           self.window = tk.Toplevel()
           self.window_id = self.window.winfo_id()
           self.app = object()

    def hideEvent(self, event):
        super().hideEvent(event)
        if not self.window_closed:
            if self.window:
                 self.window.destroy()
        self.window_closed = True

class UnifiedApp(QMainWindow):
    def __init__(self):
        super().__init__()
        print(f"Script Dir: {SCRIPT_DIR}")
        print(f"Icons Path: {ICONS_PATH}")
        self.setWindowTitle("Settings")
        window_icon_path = os.path.join(ICONS_PATH, "ima.png")
        print(f"Window Icon Path: {window_icon_path}")
        self.setWindowIcon(QIcon(window_icon_path))
        self.resize(1000, 700)
        self.setStyleSheet("""
            QMainWindow {
                background-color: #333333;
                color: #ddd;
            }
            QTabWidget::pane {
                border: 1px solid #333333;
                background: #333333;
            }
            QTabBar::tab {
               background: #444;
               color: #ddd;
               padding: 5px 15px;
               border: 1px solid #555;
               border-radius: 11px;
               margin: 2px;
               min-height: 22px;
            }

            QTabBar::tab:selected {
                background: #555;
                border-color: #777;
            }
            QTabBar::tab:hover {
                background: #666;
            }
        """)
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self.add_tab("Modify", ModifyWindow, os.path.join(ICONS_PATH, "modify.ico"))
        self.add_tab("Theme", ThemeEditor, os.path.join(ICONS_PATH, "theme.ico"))
        self.add_tab("Shell", ShellEditor, os.path.join(ICONS_PATH, "shell.ico"))
        self.add_tab("Shortcut", ShortcutWindow, os.path.join(ICONS_PATH, "shortcut.ico"))

    def showEvent(self, event: QEvent):
        super().showEvent(event)
        self.center_on_screen()

    def center_on_screen(self):
        screen = QDesktopWidget().availableGeometry()
        size = self.geometry()
        new_left = (screen.width() - size.width()) // 2
        new_top = (screen.height() - size.height()) // 2
        self.move(new_left, new_top)

    def add_tab(self, tab_name, widget_class, icon_path):
        new_tab = QWidget()
        new_layout = QVBoxLayout()
        new_widget = widget_class()
        new_layout.addWidget(new_widget)
        new_tab.setLayout(new_layout)
        print(f"Tab Icon Path: {icon_path}")
        icon = QIcon(icon_path)
        self.tabs.addTab(new_tab, icon, tab_name)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    unified_app = UnifiedApp()
    unified_app.show()
    sys.exit(app.exec_())
