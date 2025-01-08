import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QTabWidget, QVBoxLayout, QWidget, QDesktopWidget, QPushButton, QHBoxLayout, QMessageBox, QTabBar, QStackedWidget
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import pyqtSignal, QObject, QEvent, QThread
import os
import shutil
import hashlib
import requests
from io import BytesIO
from zipfile import ZipFile
from modify import MainWindow as ModifyWindow
from theme import ThemeEditor
from shortcut_creator import MainWindow as ShortcutWindow
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
class UpdateThread(QThread):
    update_finished = pyqtSignal(str)
    def __init__(self, repo_url, install_folder, skip_files):
        super().__init__()
        self.repo_url = repo_url
        self.install_folder = install_folder
        self.skip_files = skip_files

    def run(self):
        try:
            update_result = self.perform_update()
            self.update_finished.emit(update_result)
        except Exception as e:
            self.update_finished.emit(f"Update Failed: {e}")
            
    def hash_file(self, filepath):
        """Calculate the MD5 hash of a file."""
        hasher = hashlib.md5()
        try:
            with open(filepath, 'rb') as file:
                while True:
                    chunk = file.read(4096)
                    if not chunk:
                        break
                    hasher.update(chunk)
        except FileNotFoundError:
             return None
        return hasher.hexdigest()

    def download_repo_zip(self):
        """Downloads the repository as a zip and extracts it into memory."""
        try:
           repo_url_parts = self.repo_url.split("/")
           user = repo_url_parts[3]
           repo = repo_url_parts[4]
           repo_zip_url = f"https://api.github.com/repos/{user}/{repo}/zipball/main"
           response = requests.get(repo_zip_url, stream=True)
           response.raise_for_status()  
           zip_file = ZipFile(BytesIO(response.content))
           root_folder_name = zip_file.namelist()[0].split("/")[0]
           extracted_files = {}
           
           for file_path in zip_file.namelist():
               if not file_path.endswith("/"):
                  parts = file_path.split("/")
                  if len(parts) > 2 and parts[1] == repo.replace("-", " "):
                       name = "/".join(parts[2:])
                       extracted_files[name] = zip_file.read(file_path)
           return extracted_files
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to Download repo {repo_zip_url}: {e}")
        except Exception as e:
            raise Exception(f"Failed to Extract zip: {e}")

    def perform_update(self):
        """Updates files in install_folder based on repo_folder."""
        try:
            extracted_files = self.download_repo_zip()
        except Exception as e:
            return f"Update Failed: {e}"
        
        updated_count = 0
        skipped_count = 0
        new_count = 0
        for relative_path, content in extracted_files.items():
            install_file_path = os.path.join("C:\\Program Files\\IMA Menu", relative_path)
           
            print(f"Checking file at: {install_file_path}")
            skip_this = False
            for skip in self.skip_files:
                 if relative_path.replace("\\", "/").startswith(skip.replace("\\", "/")):
                    skip_this = True
                    break

            if skip_this:
                skipped_count += 1
                print(f"Skipping file: {install_file_path}")
                continue
            
            os.makedirs(os.path.dirname(install_file_path), exist_ok = True)
            
            if os.path.exists(install_file_path):
                print(f"Updating file: {install_file_path}")
                with open(install_file_path, "wb") as f:
                    f.write(content)
                updated_count += 1
            else:
                print(f"Creating file: {install_file_path}")
                with open(install_file_path, "wb") as f:
                    f.write(content)
                new_count += 1
        return f"Update completed: {updated_count} updated, {new_count} new, {skipped_count} skipped"
    
class CustomTabBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QHBoxLayout(self)
        self.tab_bar = QTabBar()
        self.layout.addWidget(self.tab_bar)
        self.layout.addStretch(1)  
        self.tab_bar.setExpanding(False)
    def addTab(self, icon, text):
        return self.tab_bar.addTab(icon, text)
    
    def addRightWidget(self, widget):
        self.layout.addWidget(widget)
    
    def currentIndex(self):
        return self.tab_bar.currentIndex()

    def setCurrentIndex(self, index):
        self.tab_bar.setCurrentIndex(index)
    
    def count(self):
        return self.tab_bar.count()

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

        self.update_button = QPushButton("Check for Updates")
        self.update_button.clicked.connect(self.start_update_process)
        self.update_button.setStyleSheet("""
            QPushButton {
                background-color: #555;
                color: #ddd;
                border: 1px solid #777;
                border-radius: 10px;
                padding: 5px 15px;
            }
            QPushButton:hover {
               background-color: #666;
               border-color: #888;
            }
            QPushButton:pressed {
                background-color: #444;
                border-color: #666;
            }
            QPushButton:disabled {
              background-color: #333;
               border-color: #555;
               color: #777;
            }
            """)
        self.custom_tab_bar = CustomTabBar()

        self.tab_content_widget = QStackedWidget()


        main_layout = QVBoxLayout()
        main_layout.addWidget(self.custom_tab_bar)
        main_layout.addWidget(self.tab_content_widget)


        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)
        
        self.custom_tab_bar.addRightWidget(self.update_button)

        self.add_tab("Modify", ModifyWindow, os.path.join(ICONS_PATH, "modify.ico"))
        self.add_tab("Theme", ThemeEditor, os.path.join(ICONS_PATH, "theme.ico"))
        self.add_tab("Shell", ShellEditor, os.path.join(ICONS_PATH, "shell.ico"))
        self.add_tab("Shortcut", ShortcutWindow, os.path.join(ICONS_PATH, "shortcut.ico"))
    
        self.repo_url = "https://github.com/iMAboud/iMA-Menu/tree/main/iMA%20Menu" #This is not a raw url
        self.install_folder = SCRIPT_DIR
        self.skip_files = [
            os.path.join("imports","theme.nss"),
            os.path.join("imports", "theme_backup.nss"),
            os.path.join("imports", "modify.nss"),
            os.path.join("script", "croc.bat"),
            "shell.log",
            "shell.nss",
            "shell.dll",
            "shell.dl_",
            "shell.exe"
        ]

        self.custom_tab_bar.tab_bar.currentChanged.connect(self.tab_changed)


    def tab_changed(self, index):
        self.tab_content_widget.setCurrentIndex(index)

    def start_update_process(self):
        self.update_button.setEnabled(False)
        self.update_button.setText("Updating...")
        self.update_thread = UpdateThread(self.repo_url, self.install_folder, self.skip_files)
        self.update_thread.update_finished.connect(self.update_completed)
        self.update_thread.start()

    def update_completed(self, result):
        self.update_button.setEnabled(True)
        self.update_button.setText("Check for Updates")
        QMessageBox.information(self, "Update Status", result)

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
        index = self.custom_tab_bar.addTab(icon, tab_name)
        self.tab_content_widget.insertWidget(index, new_tab)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    unified_app = UnifiedApp()
    unified_app.show()
    sys.exit(app.exec_())
