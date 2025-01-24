import sys
import os
import platform
import subprocess
import threading
import re
import json
from PyQt5.QtWidgets import (QApplication, QWidget, QLabel, QLineEdit,
                             QPushButton, QTextEdit, QVBoxLayout, QHBoxLayout,
                             QMessageBox, QSizePolicy, QProgressBar, QDesktopWidget, QScrollBar)
from PyQt5.QtGui import QIcon, QFont, QPixmap, QClipboard, QColor
from PyQt5.QtCore import Qt, QSize, QThread, pyqtSignal, QObject
import pyperclip

def is_windows():
    return platform.system() == "Windows"

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class CommandExecutor(QThread):
    output_signal = pyqtSignal(str)
    status_signal = pyqtSignal(str, str)
    finished_signal = pyqtSignal(bool)
    progress_signal = pyqtSignal(int)

    def __init__(self, command, progress_bar_color, parent=None):
        super().__init__(parent)
        self.command = command
        self.progress_bar_color = progress_bar_color

    def run(self):
        try:
            process = subprocess.Popen(self.command,
                           stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT,
                           universal_newlines=True,
                           creationflags=subprocess.CREATE_NO_WINDOW if is_windows() else 0)
            
            while True:
                line = process.stdout.readline()
                if not line:
                    break
                self.output_signal.emit(line)
                match = re.search(r'\[download\]\s+(\d+(\.\d+)?)%', line)
                if match:
                     progress = int(float(match.group(1)))
                     self.progress_signal.emit(progress)
            process.wait()

            if process.returncode != 0:
                 self.output_signal.emit(f"\nError: Command exited with code {process.returncode}\n")
                 self.finished_signal.emit(False)
            else:
                self.finished_signal.emit(True)


        except Exception as e:
             self.output_signal.emit(f"\nAn error occurred: {e}\n")
             self.finished_signal.emit(False)

def get_clipboard_link():
    try:
        clipboard_content = pyperclip.paste()
        if clipboard_content.startswith("http"):
            return clipboard_content
        else:
             return ""
    except Exception as e:
         print(f"Error reading clipboard: {e}")
         return ""


class ThumbnailFetcher(QThread):
    thumbnail_loaded = pyqtSignal(QPixmap)
    title_loaded = pyqtSignal(str)
    error_signal = pyqtSignal(str)
    
    def __init__(self, url, output_dir, parent = None):
        super().__init__(parent)
        self.url = url
        self.output_dir = output_dir

    def run(self):
        try:
           yt_dlp_command = ["yt-dlp", "--no-warnings", "--playlist-items", "1", "-j", self.url]
           info_process = subprocess.Popen(yt_dlp_command,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT,
                                 universal_newlines=True,
                                 creationflags=subprocess.CREATE_NO_WINDOW if is_windows() else 0)

           info_out, info_err = info_process.communicate()

           if info_process.returncode == 0:
                try:
                    info_json = json.loads(info_out)
                    title = info_json.get('title', 'No title found')
                    self.title_loaded.emit(title)
                    thumbnail_url = info_json.get('thumbnail')
                    if thumbnail_url:
                      pixmap = QPixmap()
                      process = subprocess.run(["curl", "-s", thumbnail_url],
                                            capture_output=True,
                                            creationflags=subprocess.CREATE_NO_WINDOW if is_windows() else 0)
                      if process.returncode == 0:
                        pixmap.loadFromData(process.stdout)
                        if not pixmap.isNull():
                          pixmap = pixmap.scaled(200, 300, Qt.KeepAspectRatio)
                          self.thumbnail_loaded.emit(pixmap)
                        else:
                          self.error_signal.emit("Error: Failed to load pixmap from downloaded data")
                      else:
                           self.error_signal.emit(f"Error: Failed to download thumbnail from url using curl, code {process.returncode}")

                    else:
                       self.error_signal.emit("Error: No thumbnail URL found in yt-dlp output")
                except json.JSONDecodeError:
                   self.error_signal.emit("Error: Could not decode json from yt-dlp")
           else:
               self.error_signal.emit(f"Error: yt-dlp failed with code {info_process.returncode}")

        except Exception as e:
            self.error_signal.emit(f"Error loading thumbnail {e}")


def download_video(url, output_widget, status_label, window, thumbnail_label, progress_bar, progress_color, output_dir):
    
    yt_dlp_command = ["yt-dlp", "--no-warnings", "--no-playlist", url, "-f", "best", "-o", os.path.join(output_dir, "%(title)s.%(ext)s")]

    executor = CommandExecutor(yt_dlp_command, progress_color, window)
    executor.output_signal.connect(lambda line: update_output(output_widget, line))
    executor.finished_signal.connect(lambda success: handle_command_completion(success, status_label, progress_bar))
    executor.status_signal.emit("Downloading...", "yellow")
    executor.progress_signal.connect(progress_bar.setValue)
    progress_bar.setStyleSheet(f"""
          QProgressBar {{
            border: 2px solid #555;
            border-radius: 5px;
            background-color: #333;
            text-align: center;
            color: white;
            font-size: 12px
          }}
           QProgressBar::chunk {{
             background-color: {progress_color};
             border-radius: 5px;
           }}
        """)
    progress_bar.setValue(0)
    executor.start()

def download_audio(url, output_widget, status_label, window, thumbnail_label, progress_bar, progress_color, output_dir):
    
    yt_dlp_command = ["yt-dlp", "--no-warnings", "--no-playlist", "-x", "--audio-format", "mp3",url, "-o", os.path.join(output_dir, "%(title)s.%(ext)s)")]
    
    executor = CommandExecutor(yt_dlp_command, progress_color, window)
    executor.output_signal.connect(lambda line: update_output(output_widget, line))
    executor.finished_signal.connect(lambda success: handle_command_completion(success, status_label, progress_bar))
    executor.status_signal.emit("Downloading Audio...", "yellow")
    executor.progress_signal.connect(progress_bar.setValue)
    progress_bar.setStyleSheet(f"""
          QProgressBar {{
            border: 2px solid #555;
            border-radius: 5px;
            background-color: #333;
            text-align: center;
            color: white;
            font-size: 12px
          }}
           QProgressBar::chunk {{
             background-color: {progress_color};
             border-radius: 5px;
           }}
        """)
    progress_bar.setValue(0)
    executor.start()
        
def on_download_video_clicked(url, output_widget, status_label, window, thumbnail_label, progress_bar, progress_color, output_dir):
    if not url:
        return
    status_label.setText("Downloading...")
    status_label.setStyleSheet("color: yellow;")
    download_video(url, output_widget, status_label, window, thumbnail_label, progress_bar, progress_color, output_dir)
    
def on_download_audio_clicked(url, output_widget, status_label, window, thumbnail_label, progress_bar, progress_color, output_dir):
    if not url:
         return
    status_label.setText("Downloading Audio...")
    status_label.setStyleSheet("color: yellow;")
    download_audio(url, output_widget, status_label, window, thumbnail_label, progress_bar, progress_color, output_dir)


def update_output(output_widget, line):
    output_widget.insertPlainText(line)
    output_widget.verticalScrollBar().setValue(output_widget.verticalScrollBar().maximum())
    

def handle_command_completion(success, status_label, progress_bar):
   if success:
     status_label.setText("Download Complete!")
     status_label.setStyleSheet("color: green;")
   else:
    status_label.setText("Download Failed.")
    status_label.setStyleSheet("color: red;")
   progress_bar.setValue(0)
        
class CustomLabel(QLabel):
    def __init__(self):
      super().__init__()
    def set_pixmap(self, pixmap):
        
       self.setPixmap(pixmap)

class ModernScrollBar(QScrollBar):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
           QScrollBar:vertical {
                background-color: transparent;
                width: 10px;
                margin: 0px 0px 0px 0px;
            }

            QScrollBar::handle:vertical {
                background-color: rgba(80, 80, 80, 150);
                min-height: 20px;
                border-radius: 5px;
            }

            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                background: none;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical{
                background: none;
            }


        """)
class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("yt-dlp Downloader")
        self.setStyleSheet("background-color: #2b2b2b;")
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        self.thumbnail_label = CustomLabel()
        self.thumbnail_label.setFixedSize(100, 100)
        self.thumbnail_label.setAlignment(Qt.AlignCenter)
        self.thumbnail_label.setStyleSheet("border-radius: 10px; background-color: #444; min-width: 200px; max-width: 300px;")
        
        thumbnail_layout = QHBoxLayout()
        thumbnail_layout.setAlignment(Qt.AlignCenter)
        thumbnail_layout.addWidget(self.thumbnail_label)
        main_layout.addLayout(thumbnail_layout)

        self.title_label = QLabel("")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setStyleSheet("color: white;")
        self.title_label.setWordWrap(True)
        self.title_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        main_layout.addWidget(self.title_label)
        
        
        url_layout = QHBoxLayout()
        url_label = QLabel("URL:")
        url_label.setStyleSheet("color: white;")
        url_layout.addWidget(url_label)

        self.url_entry = QLineEdit()
        self.url_entry.setStyleSheet("""
                QLineEdit {
                    background-color: #444;
                    color: white;
                    border: 2px solid #555;
                    border-radius: 10px;
                    padding: 5px;
                }
            """)
        self.url_entry.mousePressEvent = self.select_all_text
        self.url_entry.textChanged.connect(self.on_url_changed)
        url_layout.addWidget(self.url_entry)

        self.paste_button = QPushButton("📋")
        self.paste_button.setStyleSheet("""
            QPushButton {
                background-color: #444;
                color: white;
                border: 3px solid #555;
                border-radius: 10px;
                padding: 2px;
                max-width: 30px;
                min-width: 30px;
                font-size: 18px
            }
            QPushButton:hover {
                background-color: #666;
            }
        """)
        self.paste_button.clicked.connect(self.paste_link)
        url_layout.addWidget(self.paste_button)

        main_layout.addLayout(url_layout)
        
        button_layout = QHBoxLayout()
        button_layout.setAlignment(Qt.AlignCenter)


        
        self.download_video_button = QPushButton("🎬 Download Video")
        self.download_video_button.clicked.connect(self.start_video_download)
        self.video_button_color = "#3e284f"
        self.set_button_style(self.download_video_button, self.video_button_color)
        button_layout.addWidget(self.download_video_button)

        self.download_audio_button = QPushButton("🎧 Download Audio")
        self.download_audio_button.clicked.connect(self.start_audio_download)
        self.audio_button_color = "#28528d"
        self.set_button_style(self.download_audio_button, self.audio_button_color)
        button_layout.addWidget(self.download_audio_button)
        
        main_layout.addLayout(button_layout)

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(20)
        self.progress_bar.setStyleSheet("""
          QProgressBar {
            border: 2px solid #555;
            border-radius: 5px;
            background-color: #333;
            text-align: center;
            color: white;
             font-size: 14px;
          }
           QProgressBar::chunk {
             background-color: #007BFF;
             border-radius: 10px;
           }
        """)
        self.progress_bar.setValue(0)
        main_layout.addWidget(self.progress_bar)

        self.output_text = QTextEdit()
        self.output_text.setStyleSheet("""
            QTextEdit {
                background-color: #333;
                color: lightgray;
                border: 1px solid #555;
                border-radius: 10px;
                padding: 5px;
            }
        """)
        
        self.output_text.setVerticalScrollBar(ModernScrollBar())
        self.output_text.setHorizontalScrollBar(ModernScrollBar())
        
        self.output_text.setFixedHeight(80)
        self.output_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        main_layout.addWidget(self.output_text)
        
        main_layout.addStretch()
        
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: white; font-style: italic")
        main_layout.addWidget(self.status_label)
        
        self.output_dir = os.getcwd()
        self.paste_link()
        self.load_initial_thumbnail()
        self.center_window()
    
    def select_all_text(self, event):
        self.url_entry.selectAll()


    def load_initial_thumbnail(self):
       link = get_clipboard_link()
       if link:
            self.url_entry.setText(link)
            self.fetch_thumbnail(link)

    def set_button_style(self, button, color):
        button.setStyleSheet(f"""
        QPushButton {{
            background-color: #444;
            color: white;
            border: 2px solid #555;
            border-radius: 10px;
            padding: 10px 20px;
            font-size: 12px;
            min-width: 150px;
        }}
        QPushButton:hover {{
            background-color: {color};
        }}
        QPushButton:pressed {{
            background-color: #333;
        }}
    """)

            
    def paste_link(self):
        link = get_clipboard_link()
        if link:
            self.url_entry.setText(link)
            self.fetch_thumbnail(link)

    def fetch_thumbnail(self, url):
        if url.startswith("http"):
          self.thumbnail_fetcher = ThumbnailFetcher(url, self.output_dir, self)
          self.thumbnail_fetcher.thumbnail_loaded.connect(self.thumbnail_label.set_pixmap, type=Qt.QueuedConnection)
          self.thumbnail_fetcher.title_loaded.connect(self.title_label.setText)
          self.thumbnail_fetcher.error_signal.connect(lambda error: print(f"Error updating thumbnail {error}"))
          self.thumbnail_fetcher.start()
    def on_url_changed(self, url):
      self.fetch_thumbnail(url)
    
    def start_video_download(self):
       url = self.url_entry.text()
       if url:
          on_download_video_clicked(url, self.output_text, self.status_label, self, self.thumbnail_label, self.progress_bar, self.video_button_color, self.output_dir)
        
    def start_audio_download(self):
       url = self.url_entry.text()
       if url:
         on_download_audio_clicked(url, self.output_text, self.status_label, self, self.thumbnail_label, self.progress_bar, self.audio_button_color, self.output_dir)
    
    def center_window(self):
      qr = self.frameGeometry()
      cp = QDesktopWidget().availableGeometry().center()
      qr.moveCenter(cp)
      self.move(qr.topLeft())

if __name__ == '__main__':
    if is_windows():
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("myappid")
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
