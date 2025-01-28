import sys
import os
import platform
import subprocess
import time
import uuid
import re
import json
from queue import Queue
from PyQt5.QtWidgets import (QApplication, QWidget, QLabel, QLineEdit, QPushButton,
                             QTextEdit, QVBoxLayout, QHBoxLayout, QProgressBar,
                             QDesktopWidget, QFrame, QListWidget, QListWidgetItem,
                             QAbstractItemView, QSizePolicy, QSpacerItem, QFileDialog, QDialog, QGraphicsDropShadowEffect,
                             QScrollBar)
from PyQt5.QtGui import QIcon, QFont, QColor, QPainter, QBrush, QLinearGradient, QRegion, QPainterPath, QPolygon
from PyQt5.QtCore import Qt, QSize, QThread, pyqtSignal, QTimer, QPoint
import pyperclip


def is_windows():
    return platform.system() == "Windows"


def resource_path(relative_path):
    base_path = sys._MEIPASS if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)


def quote_path(path):
    path = (path or "").strip()
    return f'"{path}"' if path and not (path.startswith('"') and path.endswith('"')) else path


def get_clipboard_path():
    try:
        content = pyperclip.paste().strip()
        return content if content and os.path.exists(content) else ""
    except Exception:
        return ""


colors = {
    "background_gradient_start": "#373737",
    "background_gradient_end": "#261f2b",
    "send_button_color": "#7e57c2",
    "queue_background": "rgba(126, 87, 194, 0.3)",
    "queue_text": "white",
    "queue_border": "#000",
    "path_entry_background": "#7e57c2",
    "path_entry_text": "white",
    "path_entry_border": "#7e57c2",
    "clear_button_background": "#7e57c2",
    "clear_button_hover": "#555",
    "progress_bar_border": "#555",
    "progress_bar_background": "#333",
    "progress_bar_text": "white",
    "progress_bar_chunk": "#7e57c2",
    "time_speed_text": "#bbb",
    "output_text_background": "#333",
    "output_text_color": "lightgray",
    "output_text_border": "#7e57c2",
    "scroll_bar_handle": "rgba(80, 80, 80, 150)",
    "status_frame_background": "rgba(50, 50, 50, 0.6)",
    "status_text": "white",
    "status_shadow": "black",
    "circular_button_background": "#333",
    "circular_button_text": "white",
    "queue_item_background": "#444",
    "queue_item_border": "#7e57c2",
    "queue_item_text": "white",
    "queue_item_label_background": "rgba(80, 80, 80, 0.5)",
    "set_code_popup_background": "#333",
    "set_code_popup_border": "#555",
    "set_code_button_background": "#555",
    "set_code_button_hover": "#7e57c2",
    "set_code_button_text": "white",
    "app_context_menu_background": "#333",
    "app_context_menu_text": "white",
    "app_context_menu_border": "#555",
    "app_context_menu_selected": "#555",
     "title_bar_background": "#333",
    "title_bar_button_hover": "#555",
    "title_bar_button_text": "white",
    "title_bar_button_border": "#7e57c2",
    "minimize_button_color": "yellow",  
    "maximize_button_color": "cyan",  
    "close_button_color": "red", 
    "title_bar_button_hover_color": "rgba(80, 80, 80, 0.5)",  
    "title_bar_button_hover_border_size": 1, 
    "title_bar_button_font_size": "12px" 

}


def set_drop_shadow(widget, blur_radius=10, offset_x=4, offset_y=4, opacity=150):
    shadow = QGraphicsDropShadowEffect()
    shadow.setBlurRadius(blur_radius)
    shadow.setColor(QColor(0, 0, 0, opacity))
    shadow.setOffset(offset_x, offset_y)
    widget.setGraphicsEffect(shadow)


class SendFileThread(QThread):
    output_signal = pyqtSignal(str)
    status_signal = pyqtSignal(str, str)
    finished_signal = pyqtSignal(bool)
    progress_signal = pyqtSignal(int)
    speed_signal = pyqtSignal(str)
    hashing_progress_signal = pyqtSignal(int)
    hashing_finished_signal = pyqtSignal()
    status_update_signal = pyqtSignal(str, str)
    time_remaining_signal = pyqtSignal(str)
    current_file_signal = pyqtSignal(str, str)
    queue_id_signal = pyqtSignal(str)

    def __init__(self, filepath, code_prefix, progress_color, hashing_color, parent=None, queue_id=None):
        super().__init__(parent)
        self.filepath = filepath
        self.code_prefix = code_prefix
        self.progress_color = progress_color
        self.hashing_color = hashing_color
        self.process = None
        self.is_hashing = True
        self.hashing_complete = False
        self.start_time = 0
        self.queue_id = queue_id
        stripped_path = self.filepath.strip()
        if stripped_path.startswith('"') and stripped_path.endswith('"'):
            stripped_path = stripped_path[1:-1]
        self.filename = os.path.basename(stripped_path)
        try:
            self.filesize = self.format_file_size(os.path.getsize(stripped_path))
        except Exception:
            self.filesize = "N/A"

    def run(self):
        try:
            command = f'croc --ignore-stdin send --code {self.code_prefix} {quote_path(self.filepath)}'
            full_command = ["powershell", "-NoExit", "-Command", command]
            self.process = subprocess.Popen(full_command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                            universal_newlines=True, creationflags=subprocess.CREATE_NO_WINDOW)
            self.start_time = time.time()
            self.current_file_signal.emit(self.filename, self.filesize)
            self.queue_id_signal.emit(self.queue_id)

            while True:
                line = self.process.stdout.readline()
                if not line:
                    break
                self.output_signal.emit(line)
                self.parse_output_line(line)
            self.process.wait()

            if self.process.returncode != 0:
                self.output_signal.emit(f"\nError: Command exited with code {self.process.returncode}\n")
                self.finished_signal.emit(False)
            else:
                self.finished_signal.emit(True)
                self.status_update_signal.emit("Completed!", "white")
                self.queue_id_signal.emit(self.queue_id)
        except Exception as e:
            self.output_signal.emit(f"\nAn error occurred: {e}\n")
            self.finished_signal.emit(False)

    def parse_output_line(self, line):
        if hashing_match := re.match(r'Hashing (.+?)\s+(\d+)%\s+.*?\((.+?)\).*', line):
            _, progress, speed = hashing_match.groups()
            self.hashing_progress_signal.emit(int(progress))
            self.speed_signal.emit(speed.strip())
            self.is_hashing = True
            self.status_update_signal.emit("Loading...", "yellow")
            elapsed = time.time() - self.start_time
            self.time_remaining_signal.emit(self.format_time(elapsed))
        elif re.match(r'Sending\s+\d+\s+files.*', line) and not self.hashing_complete:
            self.hashing_progress_signal.emit(100)
            self.hashing_complete = True
            self.is_hashing = False
            self.hashing_finished_signal.emit()
            self.status_update_signal.emit("Ready to Upload", "#0058d3")
            self.time_remaining_signal.emit("")
        elif uploading_match := re.match(r'(.+?)\s+(\d+)%\s+.*?\((.+?)\,\s+(.+?)\)\s+\[(.+?)\]', line):
            _, progress, _, speed, time_remaining = uploading_match.groups()
            self.progress_signal.emit(int(progress))
            self.speed_signal.emit(speed.strip())
            self.is_hashing = False
            self.status_update_signal.emit("Uploading file...", "yellow")
            self.time_remaining_signal.emit(time_remaining.strip())

    def format_time(self, seconds):
        minutes = int(seconds // 60)
        seconds = int(seconds % 60)
        return f"{minutes}m{seconds}s"

    def format_file_size(self, size):
        units = ["B", "KB", "MB", "GB", "TB"]
        for unit in units:
            if size < 1024.0:
                break
            size /= 1024.0
        return f"{size:.1f}{unit}"

    def close_process(self):
        if self.process and self.process.poll() is None:
            kill_command = ['taskkill', '/F', '/T', '/PID', str(self.process.pid)] if is_windows() else ['kill', '-9',
                                                                                                      str(self.process.pid)]
            subprocess.Popen(kill_command, creationflags=subprocess.CREATE_NO_WINDOW if is_windows() else 0)


def update_output(output_widget, line):
    output_widget.insertPlainText(line)
    scrollbar = output_widget.verticalScrollBar()
    scrollbar.setValue(scrollbar.maximum())


def handle_command_completion(success, status_label, progress_bar, window):
    status_label.setText("Complete!" if success else "Failed.")
    status_label.setStyleSheet(f"color: {'green' if success else 'red'};")
    window.speed_label.setText("")
    progress_bar.setValue(0)
    window.is_sending = False
    window.process_pending_queue()


class CircularButton(QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(22, 22)
        self.setStyleSheet(f"background-color: {colors['circular_button_background']}; border-radius: 8px; color: {colors['circular_button_text']}; font-size: 12px; border: 2px solid {colors['send_button_color']};")
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QBrush(QColor(colors['circular_button_background'])))
        painter.drawEllipse(self.rect())
        super().paintEvent(event)


class ModernScrollBar(QScrollBar):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""QScrollBar:vertical {{background-color: transparent;width: 10px;margin: 0px 0px 0px 0px;}}
            QScrollBar::handle:vertical {{background-color: {colors['scroll_bar_handle']};min-height: 20px;border-radius: 5px;}}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{background: none;}}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical{{background: none;}}""")


class QueueListItem(QWidget):
    def __init__(self, filename, filesize, queue_id, remove_callback, parent=None):
        super().__init__(parent)
        self.queue_id = queue_id
        self.remove_callback = remove_callback
        self.filename = filename

        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        self.remove_button = CircularButton("✖")
        self.remove_button.clicked.connect(self.on_remove_clicked)
        layout.addWidget(self.remove_button)
        layout.setAlignment(self.remove_button, Qt.AlignLeft | Qt.AlignVCenter)
        layout.setSpacing(1)
        
        self.label = QLabel(f"{self.truncate_filename(filename, 14)} ({filesize})")
        self.label.setStyleSheet(f"QLabel {{color: {colors['queue_item_text']};background-color: {colors['queue_item_label_background']};border-radius: 5px;padding: 2px;}}")
        self.label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.label.setMaximumWidth(140) 
        layout.addWidget(self.label)


        self.setStyleSheet(f"QueueListItem {{background-color: {colors['queue_item_background']};border-radius: 10px;border: 2px solid {colors['queue_item_border']};}}")
        set_drop_shadow(self.label, opacity=150)
    
    def truncate_filename(self, filename, length):
        return filename[:length] + ".." if len(filename) > length else filename

    def on_remove_clicked(self):
        if self.remove_callback:
            self.remove_callback(self.filename, self.queue_id)


class SettingsPopup(QDialog):
    def __init__(self, main_window, initial_code, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.setWindowTitle("Set Code")
        self.setWindowFlag(Qt.FramelessWindowHint)
        self.setStyleSheet(f"background-color: {colors['set_code_popup_background']}; border-radius: 10px;")
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        self.code_label = QLabel("Set Code:")
        self.code_label.setStyleSheet(f"color: {colors['status_text']}; font-size: 14px; background-color: transparent;")
        layout.addWidget(self.code_label)
        set_drop_shadow(self.code_label, opacity=150)

        self.code_input = QLineEdit(initial_code)
        self.code_input.textChanged.connect(self.validate_code_input)
        self.code_input.setStyleSheet(
            f"QLineEdit {{background-color: #444; color: {colors['path_entry_text']}; border: 2px solid {colors['set_code_popup_border']}; border-radius: 10px; padding: 5px;}}")
        layout.addWidget(self.code_input)
        set_drop_shadow(self.code_input, opacity=150)

        self.code_description = QLabel("Set your special code here. This will be used by other users to download files")
        self.code_description.setStyleSheet("color: #ddd; font-size: 10px; background-color: transparent;")
        layout.addWidget(self.code_description)
        set_drop_shadow(self.code_description, opacity=150)

        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: red; font-size: 12px; background-color: transparent;")
        layout.addWidget(self.error_label)
        set_drop_shadow(self.error_label, opacity=150)

        button_layout = QHBoxLayout()

        self.set_button = QPushButton("Set")
        self.set_button.clicked.connect(self.save_settings)
        self.set_button.setStyleSheet(f"QPushButton {{background-color: {colors['set_code_button_background']}; color: {colors['set_code_button_text']}; border: 2px solid {colors['set_code_button_hover']}; border-radius: 10px; padding: 5px;}}"
                                     f"QPushButton:hover {{background-color: {colors['set_code_button_hover']};}}")
        button_layout.addWidget(self.set_button)
        set_drop_shadow(self.set_button, opacity=150)

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.close)
        self.cancel_button.setStyleSheet(
            "QPushButton {background-color: #444; color: white; border: 2px solid #555; border-radius: 10px; padding: 5px;}"
            "QPushButton:hover {background-color: #555;}")
        button_layout.addWidget(self.cancel_button)
        set_drop_shadow(self.cancel_button, opacity=150)

        layout.addLayout(button_layout)
        self.center_popup()

    def validate_code_input(self, text):
        if " " in text:
            self.code_input.setText(text.replace(" ", ""))
            self.error_label.setText("No Space")
            return
        if len(text) < 6:
            self.error_label.setText("6+ characters")
        else:
            self.error_label.setText("")

    def save_settings(self):
        code = self.code_input.text()
        if len(code) >= 6 and " " not in code:
            self.main_window.save_code_to_json(code)
            self.close()

    def center_popup(self):
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("iMShare")
        self.setMinimumSize(800, 500)
        
        self.window_position = None
       
        self.title_bar_height = 30
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

         # Custom Title Bar
        self.title_bar = QWidget(self)
        self.title_bar.setFixedHeight(self.title_bar_height)
        self.title_bar.setAttribute(Qt.WA_StyledBackground, True)  # This allows the stylesheet to fully style it
        title_layout = QHBoxLayout(self.title_bar)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(0)


        self.title_label = QLabel("iMShare")
        self.title_label.setStyleSheet(f"color: {colors['title_bar_button_text']}; font-size: 12px;")
        title_layout.addWidget(self.title_label)
        self.title_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        title_layout.setAlignment(self.title_label, Qt.AlignCenter)  

        # Minimize button
        self.minimize_button = QPushButton("–")
        self.minimize_button.setFixedSize(30,30)
        self.set_title_bar_button_style(self.minimize_button)
        self.minimize_button.clicked.connect(self.showMinimized)
        title_layout.addWidget(self.minimize_button)

        # Maximize / Restore button
        self.maximize_restore_button = QPushButton("■")
        self.maximize_restore_button.setFixedSize(30,30)
        self.set_title_bar_button_style(self.maximize_restore_button)
        self.maximize_restore_button.clicked.connect(self.toggle_maximize_restore)
        title_layout.addWidget(self.maximize_restore_button)

        # Close button
        self.close_button = QPushButton("x")
        self.close_button.setFixedSize(30,30)
        self.set_title_bar_button_style(self.close_button)
        self.close_button.clicked.connect(self.close)
        title_layout.addWidget(self.close_button)
        main_layout.addWidget(self.title_bar)
        
        content_layout = QHBoxLayout()
        content_layout.setContentsMargins(20, 20, 20, 20)

        queue_area_layout = QVBoxLayout()
        self.send_file_button = QPushButton("Send File")
        self.send_file_button.clicked.connect(self.open_file_dialog)
        self.send_file_color = colors["send_button_color"]
        self.set_button_style(self.send_file_button, self.send_file_color, rounded=True)
        queue_area_layout.addWidget(self.send_file_button)
        set_drop_shadow(self.send_file_button, opacity=150)

        self.queue_layout = QVBoxLayout()
        self.queue_layout.setAlignment(Qt.AlignTop)
        self.file_queue_list = QListWidget()
        self.file_queue_list.setStyleSheet(
            f"QListWidget {{background-color: {colors['queue_background']};color: {colors['queue_text']};border: {colors['queue_border']};border-radius: 10px;padding: 5px;outline: 0;}}")
        self.file_queue_list.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.file_queue_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.file_queue_list.setVerticalScrollBar(ModernScrollBar())
        self.file_queue_list.setMaximumWidth(200)
        self.file_queue_list.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self.queue_layout.addWidget(self.file_queue_list)
        set_drop_shadow(self.file_queue_list, opacity=150)

        queue_area_layout.addLayout(self.queue_layout)
        content_layout.addLayout(queue_area_layout)
        
        content_layout_inner = QVBoxLayout()
        content_layout_inner.setAlignment(Qt.AlignTop)

        self.file_info_layout = QVBoxLayout()
        self.file_info_layout.setAlignment(Qt.AlignCenter)

        self.file_name_label = QLabel("No File Selected")
        self.file_name_label.setStyleSheet("color: white; font-size: 14px; font-weight: bold;")
        self.file_name_label.setAlignment(Qt.AlignCenter)
        self.file_info_layout.addWidget(self.file_name_label)
        set_drop_shadow(self.file_name_label, opacity=150)

        self.file_size_label = QLabel("")
        self.file_size_label.setStyleSheet(f"color: {colors['time_speed_text']}; font-size: 10px; font-style: italic")
        self.file_size_label.setAlignment(Qt.AlignCenter)
        self.file_info_layout.addWidget(self.file_size_label)
        set_drop_shadow(self.file_size_label, opacity=150)

        content_layout_inner.addLayout(self.file_info_layout)

        path_layout = QHBoxLayout()
        path_label = QLabel("File Path:")
        path_label.setStyleSheet("color: white;")
        path_layout.addWidget(path_label)
        set_drop_shadow(path_label, opacity=150)

        self.path_entry = QLineEdit()
        self.path_entry.setStyleSheet(
            f"QLineEdit {{background-color: {colors['path_entry_background']};color: {colors['path_entry_text']};border: 2px solid {colors['path_entry_border']};border-radius: 10px;padding: 5px;}}"
        )
        path_layout.addWidget(self.path_entry)
        set_drop_shadow(self.path_entry, opacity=150)

        self.clear_path_button = QPushButton("🗑")
        self.clear_path_button.clicked.connect(self.clear_all)
        self.clear_path_button.setFixedWidth(30)
        self.clear_path_button.setStyleSheet(
            f"QPushButton {{background-color: {colors['clear_button_background']};color: white;border: 2px solid {colors['path_entry_border']};border-radius: 10px;padding: 5px;}}\n            QPushButton:hover {{background-color: {colors['clear_button_hover']};}}")
        path_layout.addWidget(self.clear_path_button)
        set_drop_shadow(self.clear_path_button, opacity=150)

        content_layout_inner.addLayout(path_layout)

        button_layout = QHBoxLayout()
        button_layout.setAlignment(Qt.AlignCenter)
        content_layout_inner.addLayout(button_layout)

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(20)
        self.progress_bar.setStyleSheet(
            f"QProgressBar {{border: 2px solid {colors['progress_bar_border']};border-radius: 5px;background-color: {colors['progress_bar_background']};text-align: center;color: {colors['progress_bar_text']};font-size: 14px;}} QProgressBar::chunk {{background-color: {colors['progress_bar_chunk']};border-radius: 10px;}}")
        self.progress_bar.setValue(0)
        content_layout_inner.addWidget(self.progress_bar)
        set_drop_shadow(self.progress_bar, opacity=150)

        self.progress_info_layout = QHBoxLayout()
        self.progress_info_layout.setAlignment(Qt.AlignCenter)

        self.time_remaining_label = QLabel("")
        self.time_remaining_label.setStyleSheet(f"color: {colors['time_speed_text']}; font-size: 10px; font-style: italic")
        self.time_remaining_label.setAlignment(Qt.AlignCenter)
        self.progress_info_layout.addWidget(self.time_remaining_label)
        set_drop_shadow(self.time_remaining_label, opacity=150)

        self.speed_label = QLabel("")
        self.speed_label.setStyleSheet(f"color: {colors['time_speed_text']}; font-size: 10px; font-style: italic")
        self.speed_label.setAlignment(Qt.AlignCenter)
        self.progress_info_layout.addWidget(self.speed_label)
        set_drop_shadow(self.speed_label, opacity=150)

        content_layout_inner.addLayout(self.progress_info_layout)
        

        self.output_text = QTextEdit()
        self.output_text.setStyleSheet(
            f"QTextEdit {{background-color: {colors['output_text_background']};color: {colors['output_text_color']};border: 2px solid {colors['output_text_border']};border-radius: 10px;padding: 5px;}}"
        )
        self.output_text.setVerticalScrollBar(ModernScrollBar())
        self.output_text.setHorizontalScrollBar(ModernScrollBar())
        self.output_text.setFixedHeight(80)
        self.output_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        content_layout_inner.addWidget(self.output_text)
        set_drop_shadow(self.output_text, opacity=150)

        spacer = QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Expanding)
        content_layout_inner.addItem(spacer)


        self.status_frame = QFrame()
        self.status_frame.setStyleSheet(f"background-color: {colors['status_frame_background']}; border-radius: 10px;")
        self.status_layout = QHBoxLayout(self.status_frame)
        self.status_layout.setAlignment(Qt.AlignCenter)
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet(
            f"color: {colors['status_text']}; font-size: 14px; text-shadow: -1px -1px 0 {colors['status_shadow']}, 1px -1px 0 {colors['status_shadow']}, -1px 1px 0 {colors['status_shadow']}, 1px 1px 0 {colors['status_shadow']};")

        self.status_layout.addWidget(self.status_label)
        set_drop_shadow(self.status_label, opacity=150)
        content_layout_inner.addWidget(self.status_frame)
        set_drop_shadow(self.status_frame, opacity=150)
        set_drop_shadow(self.status_label, opacity=150)
        
        content_layout.addLayout(content_layout_inner)
        
        main_layout.addLayout(content_layout)
        self.queue_layout.setStretch(0, 1)
        self.output_dir = os.getcwd()
        QTimer.singleShot(100, self.load_initial_path)
        self.center_window()
        self.set_rounded_window()
        self.set_gradient_background()
        
        
        self.active_threads = []
        self.dot_animation_timer = QTimer(self)
        self.dot_animation_timer.timeout.connect(self.update_dots)
        self.dot_count = 0
        self.current_status_message = ""
        self.is_sending = False
        self.file_queue = Queue()
        self.initial_path_loaded = False
        self.clear_message_timer = QTimer(self)
        self.clear_message_timer.timeout.connect(self.clear_message_timeout)
        self.current_file = None

        self.config_dir = os.path.join(resource_path("."), "config")
        os.makedirs(self.config_dir, exist_ok=True)
        self.config_file = os.path.join(self.config_dir, "iMShare.json")
        self.settings = self.load_settings()
        self.code = self.settings.get("code", None)
        if not self.code:
            self.open_settings_popup()
        else:
            QTimer.singleShot(100, self.process_pending_queue)

        self.app_context_menu_style = f"""
            QMenu {{
                background-color: {colors['app_context_menu_background']};
                color: {colors['app_context_menu_text']};
                border: 1px solid {colors['app_context_menu_border']};
                border-radius: 10px;
            }}
            QMenu::item {{
                background-color: transparent;
                padding: 5px 10px;
                margin: 1px 0px;
                border-radius: 10px;
                text-align: center;
            }}
            QMenu::item:selected {{
                background-color: {colors['app_context_menu_selected']};
            }}
            QMenu::item::text {{
                padding-right: 20px;
            }}
           QMenu::separator {{
                height: 0px;
            }}
        """
        app.setStyleSheet(self.app_context_menu_style)

    def set_title_bar_button_style(self, button):
        if button == self.minimize_button:
           button_color = colors["minimize_button_color"]
        elif button == self.maximize_restore_button:
           button_color = colors["maximize_button_color"]
        else:
           button_color = colors["close_button_color"]

        button.setStyleSheet(
            f"QPushButton {{background-color: transparent; color: {button_color}; border: none; border-radius: 15px;padding: 0px; font-size: {colors['title_bar_button_font_size']};}}"
            f"QPushButton:hover {{background-color: {colors['title_bar_button_hover_color']}; border: {colors['title_bar_button_hover_border_size']}px solid {colors['title_bar_button_border']}; padding: 0px; min-width: 30px; min-height: 30px;}}")
        
        
    def toggle_maximize_restore(self):
        if self.isMaximized():
            self.showNormal()
            self.maximize_restore_button.setText("□")
        else:
            self.showMaximized()
            self.maximize_restore_button.setText("▣")

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and event.y() < self.title_bar_height:
            self.start_move_position = event.globalPos()
            self.window_position = self.pos()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self.start_move_position is not None and event.y() < self.title_bar_height:
            delta = event.globalPos() - self.start_move_position
            self.move(self.window_position + delta)
            event.accept()

    def mouseReleaseEvent(self, event):
        self.start_move_position = None
        event.accept()
        
    def set_rounded_window(self):
        path = QPainterPath()
        rect = self.rect()
        path.addRoundedRect(rect.x(), rect.y(), rect.width(), rect.height(), 10, 10)
    # Convert the path to a region
        polygons = path.toSubpathPolygons()
        if polygons:
        # Convert QPointF points to QPoint
            qpolygon = QPolygon()
            for point in polygons[0]:
                qpolygon.append(QPoint(int(point.x()), int(point.y())))
            region = QRegion(qpolygon)
        # Set the window mask using this region
            self.setMask(region)

    def closeEvent(self, event):
        for thread in self.active_threads:
            if hasattr(thread, 'close_process'):
                thread.close_process()
        event.accept()
        
    def set_gradient_background(self):
        gradient = QLinearGradient(0, 0, self.width(), self.height())
        gradient.setColorAt(0, QColor(colors["background_gradient_start"]))
        gradient.setColorAt(1, QColor(colors["background_gradient_end"]))
        
        # Apply gradient color to the background of the MainWindow
        palette = self.palette()
        palette.setBrush(self.backgroundRole(), QBrush(gradient))
        self.setPalette(palette)

         # Apply gradient color to the title bar, this will blend it
        self.title_bar.setAutoFillBackground(True) # required to apply the background correctly
        title_palette = self.title_bar.palette()
        title_palette.setBrush(self.title_bar.backgroundRole(), QBrush(gradient))
        self.title_bar.setPalette(title_palette)
        
    def resizeEvent(self, event):
        self.set_gradient_background()
        self.set_rounded_window()
        super().resizeEvent(event)
        
    def update_queue_display(self):
        self.file_queue_list.clear()
        for file_path, queue_id in list(self.file_queue.queue):
            try:
                file_size = self.format_file_size(os.path.getsize(file_path))
            except Exception:
                file_size = "N/A"
            item_widget = QueueListItem(os.path.basename(file_path), file_size, queue_id, self.remove_from_queue)
            item = QListWidgetItem()
            item.setSizeHint(item_widget.sizeHint())
            self.file_queue_list.addItem(item)
            self.file_queue_list.setItemWidget(item, item_widget)

    def remove_from_queue(self, file_path, queue_id):
        temp_queue = Queue()
        while not self.file_queue.empty():
            item, id = self.file_queue.get()
            if id != queue_id:
                temp_queue.put((item, id))
        self.file_queue = temp_queue
        self.update_queue_display()

    def update_progress_bar(self, progress, color, is_hashing):
        self.progress_bar.setStyleSheet(
            f"""QProgressBar {{border: 2px solid {colors['progress_bar_border']};border-radius: 5px;background-color: {colors['progress_bar_background']};text-align: center;color: {colors['progress_bar_text']};font-size: 14px;}}
             QProgressBar::chunk {{background-color: {color};border-radius: 10px;}}""")
        self.progress_bar.setValue(progress)

    def update_speed(self, speed):
        self.speed_label.setText(f"{speed}")

    def update_time_remaining(self, time_remaining):
        self.time_remaining_label.setText(f"{time_remaining}")

    def format_file_size(self, size):
        units = ["B", "KB", "MB", "GB", "TB"]
        for unit in units:
            if size < 1024.0:
                break
            size /= 1024.0
        return f"{size:.1f}{unit}"

    def truncate_filename(self, filename, length):
        return filename[:length] + "..." if len(filename) > length else filename

    def clear_path(self):
        self.path_entry.clear()
        self.file_name_label.setText("No File Selected")
        self.file_size_label.setText("")

    def clear_all(self):
        for thread in self.active_threads:
            if hasattr(thread, 'close_process'):
                thread.close_process()
        for thread in self.active_threads:
            thread.wait()
        self.active_threads = []
        self.output_text.clear()
        self.clear_path()
        self.status_label.setText("Cleared!")
        self.status_label.setStyleSheet(
            "color: yellow; text-shadow: -1px -1px 0 black, 1px -1px 0 black, -1px 1px 0 black, 1px 1px 0 black;")
        self.progress_bar.setValue(0)
        self.speed_label.setText("")
        self.time_remaining_label.setText("")
        self.dot_animation_timer.stop()
        self.clear_message_timer.start(3000)
        self.is_sending = False
        self.current_file = None

    def clear_message_timeout(self):
        self.status_label.setText("")
        self.status_label.setStyleSheet(
            "color: white; text-shadow: -1px -1px 0 black, 1px -1px 0 black, -1px 1px 0 black, 1px 1px 0 black;")
        self.clear_message_timer.stop()

    def update_animated_status(self, message, color):
        self.current_status_message = message
        shadow_color = colors["status_shadow"]
        shadow_style = f"text-shadow: -1px -1px 0 {shadow_color}, 1px -1px 0 {shadow_color}, -1px 1px 0 {shadow_color}, 1px 1px 0 {shadow_color};"
        self.status_label.setFont(QFont("Arial", 12, QFont.Normal))

        if message == "Ready to Upload":
            self.status_label.setStyleSheet(
                f"color: {color}; font-style: normal; {shadow_style}"
            )
        else:
            self.status_label.setStyleSheet(
                f"color: {color}; {shadow_style}"
            )
        self.dot_count = 0
        self.update_dots()
        if "Loading..." in message or "Uploading file..." in message:
            self.dot_animation_timer.start(500)
        else:
            self.dot_animation_timer.stop()

    def update_dots(self):
        if "Loading..." in self.current_status_message or "Uploading file..." in self.current_status_message:
            dots = "." * (self.dot_count % 4)
            self.status_label.setText(f"{self.current_status_message}{dots}")
            self.dot_count += 1
        else:
            self.status_label.setText(self.current_status_message)

    def load_initial_path(self):
        path = get_clipboard_path()
        if path:
            self.path_entry.setText(quote_path(path))
            self.add_file_to_queue(path)
        self.initial_path_loaded = True

    def set_button_style(self, button, color, rounded=False):
        border_radius = "10px" if rounded else "0px"
        button.setStyleSheet(f"""QPushButton {{background-color: #444;color: white;border: 2px solid #555;border-radius: {border_radius};padding: 10px 20px;font-size: 12px;min-width: 150px;}}
            QPushButton:hover {{background-color: {color};}}
            QPushButton:pressed {{background-color: #333;}}""")

    def open_file_dialog(self):
        options = QFileDialog.Options()
        options |= QFileDialog.ExistingFiles | QFileDialog.Directory
        file_paths, _ = QFileDialog.getOpenFileNames(self, "Select Files or Folders", "", "All Files (*);;Folders (*)",
                                                    options=options)

        if file_paths:
            for path in file_paths:
                if os.path.isdir(path):
                    self.add_folder_to_queue(path)
                else:
                    self.add_file_to_queue(path)

    def add_folder_to_queue(self, folder_path):
        num_files = 0
        for _, _, files in os.walk(folder_path):
            num_files += len(files)

        if num_files > 2:
            self.add_file_to_queue(folder_path)
        else:
            for root, _, files in os.walk(folder_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    self.add_file_to_queue(file_path)

    def add_file_to_queue(self, file_path):
        unique_id = str(uuid.uuid4())
        self.file_queue.put((file_path, unique_id))
        self.update_queue_display()
        if self.code:
            self.process_next_file()

    def process_next_file(self):
        if not self.file_queue.empty() and not self.is_sending:
            self.is_sending = True
            filepath, queue_id = self.file_queue.get()
            self.current_file = filepath
            code_prefix = self.code
            hashing_color = "#28528d"
            thread = SendFileThread(filepath, code_prefix, self.send_file_color, hashing_color, self, queue_id)
            self.active_threads.append(thread)
            thread.output_signal.connect(lambda line: update_output(self.output_text, line))
            thread.finished_signal.connect(
                lambda success: handle_command_completion(success, self.status_label, self.progress_bar, self))
            thread.progress_signal.connect(
                lambda progress: self.update_progress_bar(progress, self.send_file_color, thread.is_hashing))
            thread.hashing_progress_signal.connect(
                lambda progress: self.update_progress_bar(progress, hashing_color, thread.is_hashing))
            thread.hashing_finished_signal.connect(lambda: self.update_progress_bar(100, hashing_color, False))
            thread.speed_signal.connect(self.update_speed)
            thread.status_update_signal.connect(lambda message, color: self.update_animated_status(message, color))
            thread.time_remaining_signal.connect(self.update_time_remaining)
            thread.current_file_signal.connect(self.update_current_file)
            thread.queue_id_signal.connect(self.remove_item_from_queue)
            self.progress_bar.setValue(0)
            thread.start()

    def update_current_file(self, file_name, file_size):
        self.file_name_label.setText(file_name)
        self.file_size_label.setText(f"({file_size})")
        self.speed_label.setText("")
        self.setWindowTitle(f"iMShare - {self.truncate_filename(file_name, 40)}")

    def remove_item_from_queue(self, queue_id):
        temp_queue = Queue()
        while not self.file_queue.empty():
            item, id = self.file_queue.get()
            if id != queue_id:
                temp_queue.put((item, id))
        self.file_queue = temp_queue
        self.update_queue_display()

    def center_window(self):
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def open_settings_popup(self):
        settings_dialog = SettingsPopup(self, self.code if self.code else "")
        settings_dialog.exec_()

    def load_settings(self):
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as file:
                    return json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
            pass
        return {}

    def save_code_to_json(self, code):
        self.code = code
        self.settings["code"] = code
        try:
            with open(self.config_file, 'w') as file:
                json.dump(self.settings, file, indent=4)
        except Exception as e:
            print(f"Failed to save settings: {e}")
        self.process_pending_queue()

    def process_pending_queue(self):
        while not self.file_queue.empty() and not self.is_sending:
            self.process_next_file()

if __name__ == '__main__':
    if is_windows():
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("myappid")

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
