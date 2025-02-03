import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QTabWidget, QVBoxLayout, QWidget, QDesktopWidget, QPushButton, QHBoxLayout, QMessageBox, QTabBar, QStackedWidget, QSpacerItem, QSizePolicy
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import pyqtSignal, QObject, QEvent, QThread, QTimer
import os
import shutil
import hashlib
import requests
from io import BytesIO
from zipfile import ZipFile
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

        self.update_button = QPushButton("Update")
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

        # --- Main layout setup ---
        main_layout = QVBoxLayout()

        # Tab bar and tab content
        main_layout.addWidget(self.custom_tab_bar)
        main_layout.addWidget(self.tab_content_widget)

        # --- Bottom Bar Layout ---
        bottom_bar_layout = QHBoxLayout()
        
        bottom_bar_layout.addStretch(1)
        
        self.unified_save_button = QPushButton("Save Changes")
        self.unified_save_button.clicked.connect(self.save_all)
        self.unified_save_button.setStyleSheet("""
            QPushButton {
                background-color: #1b602e;
                color: #FFFFFF;
                border-radius: 8px;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #1e8441;
            }
        """)
        bottom_bar_layout.addWidget(self.unified_save_button)
        
        main_layout.addLayout(bottom_bar_layout)
        # --- End of layout setup ---
        
        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

        
        self.custom_tab_bar.addRightWidget(self.update_button)

        self.add_tab("Modify", ModifyWindow, os.path.join(ICONS_PATH, "modify.ico"))
        self.add_tab("Theme", ThemeEditor, os.path.join(ICONS_PATH, "theme.ico"))
        self.add_tab("Shell", ShellEditor, os.path.join(ICONS_PATH, "shell.ico"))
        self.add_tab("Shortcut", ShortcutWindow, os.path.join(ICONS_PATH, "shortcut.ico"))
    
        self.repo_url = "https://github.com/iMAboud/iMA-Menu/tree/main/iMA%20Menu" 
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
        self.update_button.setText("Update")
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
    
    def save_all(self):
        for i in range(self.tab_content_widget.count()):
          widget = self.tab_content_widget.widget(i).layout().itemAt(0).widget() 
          if hasattr(widget, 'save_data'):
                data = widget.save_data()
                if isinstance(widget, ModifyWindow):
                     self.save_modify_data(data, widget)
                elif isinstance(widget, ThemeEditor):
                     self.save_theme_data(data, widget)
                elif isinstance(widget, ShellEditor):
                     self.save_shell_data(data, widget)
                elif isinstance(widget, ShortcutWindow):
                     self.save_shortcut_data(data, widget)

    def save_modify_data(self, data, widget):
        try:
            content = data.get("content", "")
            hide_ids = data.get("hide_ids", [])
            more_ids = data.get("more_ids", [])
            shift_ids = data.get("shift_ids", [])
            filepath = data.get("filepath", "")

            print(f"Original content:\n{content}")
            
            content = self.update_section(content, "// hide\nmodify(mode=mode.multiple\nwhere=this.id(", ") vis=vis.remove)", hide_ids)
            content = self.update_section(content, "// more\nmodify(mode=mode.multiple\nwhere=this.id(", ") menu=title.options)", more_ids)
            content = self.update_section(content, "// shift\nmodify(mode=single\nwhere=this.id(", ") vis=key.shift())", shift_ids)
            
            print(f"Modified content:\n{content}")

            self.write_file(filepath, content)
            widget.save_label_text("Saved") 
            QTimer.singleShot(5000, widget.clear_save_label)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error saving modify data: {e}")
    def write_file(self, filepath, content):
        with open(filepath, 'w') as file:
            file.write(content)
    def save_theme_data(self, data, widget):
      try:
        theme_data = data.get("theme_data", {})
        widget.theme_data = theme_data 
        widget._save_theme()
      except Exception as e:
            QMessageBox.critical(self, "Error", f"Error saving theme data: {e}")

    def save_shell_data(self, data, widget):
        try:
            file_path = data.get("file_path", "")
            remove_start = data.get("remove_start", "")
            remove_items = data.get("remove_items", [])
            import_start = data.get("import_start", "")
            import_items = data.get("import_items", [])
            
            with open(file_path, 'r') as file:
                lines = file.readlines()
            if remove_start != -1:
                new_remove_str = ""
                if remove_items:
                    new_remove_str = "remove(find=\"" + "|".join(remove_items) + "\")"
                if remove_items:
                    lines[remove_start] = new_remove_str + '\n'
                else:
                    lines.pop(remove_start)
                    if not lines[remove_start-1].strip():
                        lines.pop(remove_start - 1)
            if import_start != -1:
                 new_lines = lines[:import_start]
                 for line in lines[import_start:]:
                     line = line.strip()
                     if not line.startswith("import 'imports/"):
                         new_lines.append(line + '\n')
                 for import_file in import_items:
                    new_lines.append(f"import 'imports/{import_file}'\n")
                 lines = new_lines
            else:
                for import_file in import_items:
                   lines.append(f"import 'imports/{import_file}'\n")

            with open(file_path, 'w') as file:
                file.writelines(lines)
            widget.save_status_text("Saved!")
            QTimer.singleShot(3000, widget.clear_save_status)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error saving shell data: {e}")
    
    def save_shortcut_data(self, data, widget):
        try:
             filepath = data.get("filepath", "")
             items = data.get("items", [])
             content = ""
             for item in items:
               if item["type"] == "shortcut":
                  key_prefix = f"key.{item['key_selected']}()" if item["key_selected"] != "none" else ""
                  if key_prefix:
                     content += f"item(vis={key_prefix} title='{item['title']}' image='{item['icon_path']}' cmd='{item['shortcut_path']}')\n"
                  else:
                    content += f"item(title='{item['title']}' image='{item['icon_path']}' cmd='{item['shortcut_path']}')\n"
               elif item["type"] == "cmd":
                     content += f"item(title='{item['title']}' cmd='{widget.create_cmd_file(item['cmd_input'])}' icon='{item['icon_path']}')\n"

             self.write_file(filepath, content)
        except Exception as e:
             QMessageBox.critical(self, "Error", f"Error saving shortcut file: {str(e)}")
    def read_file(self, filepath):
        with open(filepath, 'r') as file:
            return file.read()


    def update_section(self, content, start_marker, end_marker, ids):
        print(f"Updating section with start_marker: {start_marker}, end_marker: {end_marker}, ids: {ids}")
        start = content.find(start_marker)
        if start == -1:
            print(f"Start marker not found: {start_marker}")
            return content

        end = content.find(end_marker, start)
        if end == -1:
            print(f"End marker not found: {end_marker}")
            return content

        before_section = content[:start]
        after_section = content[end:]
        
        new_ids = [new_id.strip() for new_id in ids if new_id.strip() != '']
        updated_ids = ",\n".join(new_ids)

        if not new_ids:
           updated_section = f"{start_marker}\n{end_marker}"
        else:
           updated_section = f"{start_marker}\n{updated_ids}\n"

        print(f"Updated section: {updated_section}")
        updated_content = before_section + updated_section + after_section
        print(f"Updated Content:\n{updated_content}")
        return updated_content

if __name__ == '__main__':
    app = QApplication(sys.argv)
    unified_app = UnifiedApp()
    unified_app.show()
    sys.exit(app.exec_())
