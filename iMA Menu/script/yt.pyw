import sys
import os
import platform
import subprocess
import re
import json
from PyQt5.QtWidgets import (QApplication, QWidget, QLabel, QLineEdit,
                             QPushButton, QTextEdit, QVBoxLayout, QHBoxLayout,
                             QSizePolicy, QProgressBar, QDesktopWidget, QScrollBar,
                             QListWidget, QListWidgetItem, QMessageBox)
from PyQt5.QtGui import QIcon, QFont, QPixmap, QClipboard, QColor
from PyQt5.QtCore import Qt, QSize, QThread, pyqtSignal, QObject, QMutex, QWaitCondition
import pyperclip

def is_windows():
    return platform.system() == "Windows"

def resource_path(relative_path):
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
    item_id_signal = pyqtSignal(int)

    def __init__(self, command, progress_bar_color, item_id, output_widget, status_label, progress_bar, parent=None):
        super().__init__(parent)
        self.command = command
        self.progress_bar_color = progress_bar_color
        self.item_id = item_id
        self.output_widget = output_widget
        self.status_label = status_label
        self.progress_bar = progress_bar
        self.process = None

    def run(self):
        self.item_id_signal.emit(self.item_id)
        try:
            self.process = subprocess.Popen(self.command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, creationflags=subprocess.CREATE_NO_WINDOW if is_windows() else 0)
            while True:
                line = self.process.stdout.readline()
                if not line:
                    break
                self.output_signal.emit(line)
                match = re.search(r'\[download\]\s+(\d+(\.\d+)?)%', line)
                if match:
                     self.progress_signal.emit(int(float(match.group(1))))
            self.process.wait()
            self.finished_signal.emit(self.process.returncode == 0)
            if self.process.returncode != 0:
                self.output_signal.emit(f"\nError: Command exited with code {self.process.returncode}\n")
        except Exception as e:
             self.output_signal.emit(f"\nAn error occurred: {e}\n")
             self.finished_signal.emit(False)
        finally:
            if self.process:
                self.process.stdout.close()


def get_clipboard_link():
    try:
        clipboard_content = pyperclip.paste()
        return clipboard_content if clipboard_content.startswith("http") else ""
    except:
         return ""

class ThumbnailFetcher(QThread):
    thumbnail_loaded = pyqtSignal(QPixmap)
    title_loaded = pyqtSignal(str, bool)
    error_signal = pyqtSignal(str)

    def __init__(self, url, output_dir, is_audio, parent=None):
        super().__init__(parent)
        self.url = url
        self.output_dir = output_dir
        self.is_audio = is_audio

    def run(self):
        try:
            info_process = subprocess.Popen(["yt-dlp", "--no-warnings", "--playlist-items", "1", "-j", self.url],
                                            stdout=subprocess.PIPE,
                                            stderr=subprocess.STDOUT,
                                            universal_newlines=True,
                                            creationflags=subprocess.CREATE_NO_WINDOW if is_windows() else 0)
            info_out, _ = info_process.communicate()

            if info_process.returncode == 0:
                try:
                    info_json = json.loads(info_out)
                    title = info_json.get('title', 'No title found')
                    self.title_loaded.emit(title, self.is_audio)
                    thumbnail_url = info_json.get('thumbnail')
                    if thumbnail_url:
                        process = subprocess.run(["curl", "-s", thumbnail_url],
                                                 capture_output=True,
                                                 creationflags=subprocess.CREATE_NO_WINDOW if is_windows() else 0)
                        if process.returncode == 0:
                            pixmap = QPixmap()
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


def download_video(url, output_widget, status_label, window, thumbnail_label, progress_bar, progress_color, output_dir, item_id):
    yt_dlp_command = [
        "yt-dlp",
        "--no-warnings",
        "--no-playlist",
        url,
        "-f", "bv*+ba/b",  # Request best video + best audio, or best overall
        "--merge-output-format", "mp4", # Ensure the final output is MP4
        "-o",
        os.path.join(output_dir, "%(title)s.%(ext)s"),
    ]
    executor = CommandExecutor(yt_dlp_command, progress_color, item_id, output_widget, status_label, progress_bar, window)
    executor.output_signal.connect(lambda line: update_output(output_widget, line))
    executor.finished_signal.connect(lambda success: handle_command_completion(success, status_label, progress_bar))
    # executor.status_signal.emit("Downloading...", "yellow") # This is not received by anything
    status_label.setText("Downloading Video...") # Set status directly or ensure MainWindow slot handles it
    status_label.setStyleSheet("color: yellow;")
    executor.progress_signal.connect(progress_bar.setValue)
    executor.item_id_signal.connect(window.on_item_start) # Connect to a slot in MainWindow if it exists
    executor.finished_signal.connect(window.on_item_finished) # Connect to a slot in MainWindow if it exists
    progress_bar.setStyleSheet(f"""QProgressBar {{ border: 3px solid #555; border-radius: 10px; background-color: #333; text-align: center; color: white; font-size: 12px }}
            QProgressBar::chunk {{ background-color: {progress_color}; border-radius: 10px;}}""")
    progress_bar.setValue(0)
    window.download_queue.start_download(executor)

def download_audio(url, output_widget, status_label, window, thumbnail_label, progress_bar, progress_color, output_dir, item_id):
    yt_dlp_command = [
        "yt-dlp",
        "--no-warnings",
        "--no-playlist",
        "-x",  # Extract audio
        "--audio-format", "mp3",
        url,
        "-o",
        os.path.join(output_dir, "%(title)s.%(ext)s") # Corrected: removed extra ')'
    ]
    executor = CommandExecutor(yt_dlp_command, progress_color, item_id, output_widget, status_label, progress_bar, window)
    executor.output_signal.connect(lambda line: update_output(output_widget, line))
    executor.finished_signal.connect(lambda success: handle_command_completion(success, status_label, progress_bar))
    # executor.status_signal.emit("Downloading Audio...", "yellow") # This is not received by anything
    status_label.setText("Downloading Audio...") # Set status directly
    status_label.setStyleSheet("color: yellow;")
    executor.progress_signal.connect(progress_bar.setValue)
    executor.item_id_signal.connect(window.on_item_start) # Connect to a slot in MainWindow
    executor.finished_signal.connect(window.on_item_finished) # Connect to a slot in MainWindow
    progress_bar.setStyleSheet(f"""QProgressBar {{ border: 3px solid #555; border-radius: 10px; background-color: #333; text-align: center; color: white; font-size: 12px }}
            QProgressBar::chunk {{ background-color: {progress_color}; border-radius: 10px;}}""")
    progress_bar.setValue(0)
    window.download_queue.start_download(executor)

def on_download_video_clicked(url, output_widget, status_label, window, thumbnail_label, progress_bar, progress_color, output_dir, item_id):
    if not url:
        return

    window.fetch_video_title(url, item_id, False)
    download_video(url, output_widget, status_label, window, thumbnail_label, progress_bar, progress_color, output_dir, item_id)


def on_download_audio_clicked(url, output_widget, status_label, window, thumbnail_label, progress_bar, progress_color, output_dir, item_id):
    if not url:
        return
    window.fetch_video_title(url, item_id, True)
    download_audio(url, output_widget, status_label, window, thumbnail_label, progress_bar, progress_color, output_dir, item_id)

def update_output(output_widget, line):
    output_widget.insertPlainText(line)
    output_widget.verticalScrollBar().setValue(output_widget.verticalScrollBar().maximum())

def handle_command_completion(success, status_label, progress_bar):
    status_label.setText("Download Complete!" if success else "Download Failed.")
    status_label.setStyleSheet("color: green;" if success else "color: red;")
    progress_bar.setValue(0)

class CustomLabel(QLabel):
    def set_pixmap(self, pixmap):
       self.setPixmap(pixmap)

class ModernScrollBar(QScrollBar):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""QScrollBar:vertical { background-color: transparent; width: 10px; margin: 0px 0px 0px 0px; border-radius: 10px; }
            QScrollBar::handle:vertical { background-color: rgba(80, 80, 80, 150); min-height: 20px; border-radius: 10px; }
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical { background: none; }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical{ background: none; border-radius: 10px;}""")

class DownloadQueue(QObject):
    item_started = pyqtSignal(int)
    item_finished = pyqtSignal(int)

    def __init__(self, max_concurrent_downloads=2):
        super().__init__()
        self.queue = []
        self.running_downloads = 0
        self.max_concurrent_downloads = max_concurrent_downloads
        self.mutex = QMutex()
        self.wait_condition = QWaitCondition()

    def enqueue(self, executor):
        self.mutex.lock()
        self.queue.append(executor)
        self.mutex.unlock()
        self.wait_condition.wakeAll()
        self.try_start_next()

    def start_download(self, executor):
        self.enqueue(executor)

    def try_start_next(self):
        self.mutex.lock()
        while self.running_downloads < self.max_concurrent_downloads and self.queue:
            executor = self.queue.pop(0)
            self.running_downloads += 1
            self.mutex.unlock()
            executor.finished_signal.connect(self.on_download_finished)
            executor.start()
            self.mutex.lock()
        self.mutex.unlock()

    def on_download_finished(self):
        self.mutex.lock()
        self.running_downloads -= 1
        self.mutex.unlock()
        self.try_start_next()
        self.wait_condition.wakeAll()


class QueueListWidget(QListWidget):
    itemDoubleClickedSignal = pyqtSignal(QListWidgetItem)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QListWidget {
                background-color: #333;
                color: white;
                border: none;
                outline: 0; /* Remove dotted border on focus */
            }
            QListWidget::item {
                background-color: #444;
                border-radius: 10px;
                padding: 10px;
                margin: 5px;
                color: white;
                box-shadow: 2px 2px 5px rgba(0, 0, 0, 0.5);
            }
            QListWidget::item:selected {
                background-color: #555;
            }
             QListWidget::item:hover {
                background-color: #555;
            }
        """)
        self.itemDoubleClicked.connect(self.on_item_double_clicked)

    def addItem(self, text):
        item = QListWidgetItem(text)
        item.setSizeHint(QSize(200, 50))
        super().addItem(item)

    def on_item_double_clicked(self, item):
        self.itemDoubleClickedSignal.emit(item)

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("iMA Menu: Downloader")
        self.app_styles = {
            "MainWindow": "QWidget { background-color: #2b2b2b; }",
             "CustomLabel": "QLabel { border-radius: 10px; background-color: #444; min-width: 200px; max-width: 300px; }",
             "TitleLabel": "QLabel { color: white; }",
              "URLLabel": "QLabel { color: white; }",
            "QLineEdit": "QLineEdit { background-color: #444; color: white; border: 3px solid #555; border-radius: 10px; padding: 5px; }  QLineEdit:focus { border: 3px solid teal; }",
            "QPushButton_Paste": "QPushButton { background-color: #444; color: white; border: 3px solid teal; border-radius: 10px; padding: 1px; max-width: 30px; min-width: 30px; font-size: 18px; } QPushButton:hover { background-color: teal; } QPushButton:pressed{background-color: teal; } QPushButton:focus { border: 3px solid teal; }",
             "QPushButton": "QPushButton { background-color: #444; color: white; border: 3px solid %button_color%; border-radius: 10px; padding: 10px 20px;  font-size: 14px; min-width: 150px;} QPushButton:hover { background-color: %button_color%; border: 2px solid %button_color%; } QPushButton:pressed{background-color: %button_color%; border: 3px solid %button_color%;}",
            "QProgressBar": "QProgressBar { border: 3px solid #555; border-radius: 10px; background-color: #333; text-align: center; color: white; font-size: 14px; height: 20px;} QProgressBar::chunk { background-color: #007BFF; margin: 1px; border-radius: 9px; }",
             "QTextEdit": "QTextEdit { background-color: #333; color: lightgray; border: 1px solid #555; border-radius: 10px; padding: 5px; }  QTextEdit:focus {border: 3px teal;} ",
             "StatusLabel": "QLabel { color: white; font-style: italic; }"
          }
        self.setStyleSheet(self.app_styles["MainWindow"])

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)

        self.queue_list = QueueListWidget()
        self.queue_list.setFixedWidth(250)
        main_layout.addWidget(self.queue_list)
        self.queue_list.setStyleSheet("""
            QListWidget {
                background-color: #333;
                color: white;
                border: none;
                outline: 0; /* Remove dotted border on focus */
            }
            QListWidget::item {
                background-color: #444;
                border-radius: 10px;
                padding: 10px;
                margin: 5px;
                color: white;
                box-shadow: 2px 2px 5px rgba(0, 0, 0, 0.5);
            }
            QListWidget::item:selected {
                background-color: #555;
            }
             QListWidget::item:hover {
                background-color: #555;
            }
        """)

        right_layout = QVBoxLayout()
        main_layout.addLayout(right_layout)

        self.thumbnail_label = CustomLabel()
        self.thumbnail_label.setFixedSize(100, 100)
        self.thumbnail_label.setAlignment(Qt.AlignCenter)
        self.thumbnail_label.setStyleSheet(self.app_styles["CustomLabel"])
        thumbnail_layout = QHBoxLayout()
        thumbnail_layout.setAlignment(Qt.AlignCenter)
        thumbnail_layout.addWidget(self.thumbnail_label)
        right_layout.addLayout(thumbnail_layout)

        self.title_label = QLabel("")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setStyleSheet(self.app_styles["TitleLabel"])
        self.title_label.setWordWrap(True)
        self.title_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        right_layout.addWidget(self.title_label)

        url_layout = QHBoxLayout()
        url_label = QLabel("URL:")
        url_label.setStyleSheet(self.app_styles["URLLabel"])
        url_layout.addWidget(url_label)
        self.url_entry = QLineEdit()
        self.url_entry.setStyleSheet(self.app_styles["QLineEdit"])
        self.url_entry.mousePressEvent = self.select_all_text
        self.url_entry.textChanged.connect(self.on_url_changed)
        url_layout.addWidget(self.url_entry)
        self.paste_button = QPushButton("📋")
        self.paste_button.setStyleSheet(self.app_styles["QPushButton_Paste"])
        self.paste_button.clicked.connect(self.paste_link)
        url_layout.addWidget(self.paste_button)
        right_layout.addLayout(url_layout)

        button_layout = QHBoxLayout()
        button_layout.setAlignment(Qt.AlignCenter)

        self.download_video_button = QPushButton("🎬 Download Video")
        self.download_video_button.clicked.connect(self.add_video_to_queue)
        self.video_button_color = "#3e284f"
        self.set_button_style(self.download_video_button, self.video_button_color)
        button_layout.addWidget(self.download_video_button)

        self.download_audio_button = QPushButton("🎧 Download Audio")
        self.download_audio_button.clicked.connect(self.add_audio_to_queue)
        self.audio_button_color = "#28528d"
        self.set_button_style(self.download_audio_button, self.audio_button_color)
        button_layout.addWidget(self.download_audio_button)
        right_layout.addLayout(button_layout)

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(20)
        self.progress_bar.setStyleSheet(self.app_styles["QProgressBar"])
        self.progress_bar.setValue(0)
        right_layout.addWidget(self.progress_bar)

        self.output_text = QTextEdit()
        self.output_text.setStyleSheet(self.app_styles["QTextEdit"])
        self.output_text.setVerticalScrollBar(ModernScrollBar())
        self.output_text.setHorizontalScrollBar(ModernScrollBar())
        self.output_text.setFixedHeight(80)
        self.output_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        right_layout.addWidget(self.output_text)

        right_layout.addStretch()

        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet(self.app_styles["StatusLabel"])
        right_layout.addWidget(self.status_label)

        self.output_dir = os.getcwd()
        self.paste_link()
        self.load_initial_thumbnail()
        self.center_window()

        self.download_queue = DownloadQueue(max_concurrent_downloads=2)
        self.item_counter = 0
        self.queue_list.itemDoubleClickedSignal.connect(self.open_downloaded_file)


    def select_all_text(self, event):
        self.url_entry.selectAll()

    def load_initial_thumbnail(self):
       link = get_clipboard_link()
       if link:
            self.url_entry.setText(link)
            self.fetch_thumbnail(link)

    def set_button_style(self, button, color):
        button.setStyleSheet(self.app_styles["QPushButton"].replace("%button_color%",color))

    def paste_link(self):
        link = get_clipboard_link()
        if link:
            self.url_entry.setText(link)
            self.fetch_thumbnail(link)

    def fetch_thumbnail(self, url):
        if url.startswith("http"):
          self.thumbnail_fetcher = ThumbnailFetcher(url, self.output_dir, False, self)
          self.thumbnail_fetcher.thumbnail_loaded.connect(self.thumbnail_label.set_pixmap, type=Qt.QueuedConnection)
          self.thumbnail_fetcher.title_loaded.connect(self.update_title_and_queue, type=Qt.QueuedConnection)
          self.thumbnail_fetcher.error_signal.connect(lambda error: print(f"Error updating thumbnail {error}"))
          self.thumbnail_fetcher.start()
    def on_url_changed(self, url):
      self.fetch_thumbnail(url)

    def add_video_to_queue(self):
        url = self.url_entry.text()
        if url:
            self.item_counter += 1
            item_id = self.item_counter
            self.queue_list.addItem(f"Video: {url}")
            on_download_video_clicked(url, self.output_text, self.status_label, self, self.thumbnail_label, self.progress_bar, self.video_button_color, self.output_dir, item_id)

    def add_audio_to_queue(self):
        url = self.url_entry.text()
        if url:
            self.item_counter += 1
            item_id = self.item_counter
            self.queue_list.addItem(f"Audio: {url}")
            on_download_audio_clicked(url, self.output_text, self.status_label, self, self.thumbnail_label, self.progress_bar, self.audio_button_color, self.output_dir, item_id)

    def on_item_start(self, item_id):
        item = self.queue_list.item(item_id - 1)
        if item:
            item.setBackground(QColor("green"))

    def on_item_finished(self, success):
        item = self.queue_list.item(self.item_counter -1)
        if item:
            item.setBackground(QColor("white"))

    def fetch_video_title(self, url, item_id, is_audio):
        self.thumbnail_fetcher = ThumbnailFetcher(url, self.output_dir, is_audio, self)
        self.thumbnail_fetcher.title_loaded.connect(lambda title, is_audio: self.update_queue_item(item_id, f"Audio: {title}" if is_audio else f"Video: {title}"))
        self.thumbnail_fetcher.start()

    def update_queue_item(self, item_id, new_text):
        item = self.queue_list.item(item_id - 1)
        if item:
            item.setText(new_text)

    def update_title_and_queue(self, title, is_audio):
        self.title_label.setText(title)
        selected_items = self.queue_list.selectedItems()
        if selected_items:
            item = selected_items[0]
            if is_audio:
                item.setText(f"Audio: {title}")
            else:
                item.setText(f"Video: {title}")

    def center_window(self):
      qr = self.frameGeometry()
      cp = QDesktopWidget().availableGeometry().center()
      qr.moveCenter(cp)
      self.move(qr.topLeft())

    def open_downloaded_file(self, item):
         item_text = item.text()
         title = item_text.split(": ")[1]
         filepath = None
         for filename in os.listdir(self.output_dir):
            if title in filename:
                 filepath = os.path.join(self.output_dir, filename)
                 if os.path.isfile(filepath):
                      break
         if filepath:
            try:
                 if is_windows():
                      os.startfile(filepath)
                 else:
                      subprocess.Popen(['xdg-open', filepath])
                 return
            except Exception as e:
                 QMessageBox.critical(self, "Error", f"Could not open file:\n{e}")
         else:
            QMessageBox.warning(self, "Warning", "File not found in the download directory.")

if __name__ == '__main__':
    if is_windows():
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("myappid")
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
