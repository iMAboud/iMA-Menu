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
                             QAbstractItemView, QSizePolicy, QSpacerItem, QDialog, QGridLayout,
                             QFileDialog, QScrollArea, QScrollBar, QGraphicsDropShadowEffect, QMenu,
                             QToolButton)
from PyQt5.QtGui import QColor, QPainter, QBrush, QLinearGradient, QFont, QPixmap, QIcon, QRegion,QCursor, QPolygon, QPainterPath # Import QPainterPath
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QUrl, QPoint
from PyQt5.QtGui import QDesktopServices, QImage


def is_windows():
    return platform.system() == "Windows"

def resource_path(relative_path):
    if getattr(sys, 'frozen', False):
        if hasattr(sys, '_MEIPASS'):
            return os.path.join(sys._MEIPASS, relative_path)
        else:
             return os.path.join(os.path.dirname(os.path.abspath(__file__)),relative_path)
    else:
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), relative_path)
        
colors = {
    "background_gradient_start": "#333d3d",
    "background_gradient_end": "#182e2e",
    "queue_background": "rgba(0, 102, 102, 0.3)",
    "queue_text": "white",
    "queue_border": "none",
    "path_entry_background": "#008080",
    "path_entry_text": "white",
    "path_entry_border": "#008080",
    "clear_button_background": "#008080",
     "clear_button_background_hover": "#555",
    "send_button_color": "#008080",
    "progress_bar_border": "#555",
    "progress_bar_background": "#333",
    "progress_bar_text": "white",
     "progress_bar_chunk": "#008080",
     "time_speed_text": "#bbb",
     "friends_scroll_background": "rgba(0, 102, 102, 0.05)",
     "status_frame_background": "rgba(50, 50, 50, 0.3)",
     "status_text": "white",
     "status_shadow": "black",
     "output_expand_background": "rgba(100, 100, 100, 0.1)",
     "output_expand_hover": "rgba(100, 100, 100, 0.2)",
     "output_text_background": "#333",
     "output_text_color": "lightgray",
     "output_text_border": "#008080",
     "scroll_bar_handle": "rgba(0, 102, 102, 150)",
     "add_friend_button": "rgba(0, 102, 102, 0.3)",
     "add_friend_button_hover": "rgba(10, 66, 66, 0.5)",
     "friend_image_border": "#008080",
     "add_friend_popup_background": "#333",
     "add_friend_popup_text": "white",
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
    finished_signal = pyqtSignal(bool, str)
    progress_signal = pyqtSignal(int)
    speed_signal = pyqtSignal(str)
    hashing_progress_signal = pyqtSignal(int)
    hashing_finished_signal = pyqtSignal()
    status_update_signal = pyqtSignal(str, str)
    time_remaining_signal = pyqtSignal(str)
    current_file_signal = pyqtSignal(str, str)
    queue_id_signal = pyqtSignal(str)
    file_name_size_signal = pyqtSignal(str,str,str)

    def __init__(self, code_prefix, progress_color, hashing_color, parent=None, queue_id=None):
        super().__init__(parent)
        self.code_prefix = code_prefix
        self.progress_color = progress_color
        self.hashing_color = hashing_color
        self.process = None
        self.is_hashing = True
        self.hashing_complete = False
        self.start_time = 0
        self.queue_id = queue_id
        self.filename = "File"
        self.filesize = "N/A"
        self.full_file_path = None
        self.path_exists = False

    def run(self):
        try:
            command = f'croc {self.code_prefix}'
            full_command = ["powershell", "-NoExit", "-Command", command] if is_windows() else ["croc", self.code_prefix]
            
            self.process = subprocess.Popen(full_command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                            universal_newlines=True, creationflags=subprocess.CREATE_NO_WINDOW if is_windows() else 0)

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
                self.finished_signal.emit(False, self.queue_id)
            else:
                self.finished_signal.emit(True, self.queue_id)
                self.status_update_signal.emit("Completed!", "white")
                self.queue_id_signal.emit(self.queue_id)
        except Exception as e:
            self.output_signal.emit(f"\nAn error occurred: {e}\n")
            self.finished_signal.emit(False, self.queue_id)
    
    def parse_output_line(self, line):
        if accept_match := re.search(r"Accept '(.+)' \((.+)\)\?", line):
            self.filename = accept_match.group(1).strip()
            self.filesize = accept_match.group(2).strip()
            self.file_name_size_signal.emit(self.filename, self.filesize, self.queue_id)
            self.current_file_signal.emit(self.filename, self.filesize)

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
            self.status_update_signal.emit("Ready to Download", "#0058d3")
            self.time_remaining_signal.emit("")
        elif uploading_match := re.match(r'(.+?)\s+(\d+)%\s+.*?\((.+?)\,\s+(.+?)\)\s+\[(.+?)\]', line):
             _, progress, _, speed, time_remaining = uploading_match.groups()
             self.progress_signal.emit(int(progress))
             self.speed_signal.emit(speed.strip())
             self.is_hashing = False
             self.status_update_signal.emit("Downloading...", "yellow")
             self.time_remaining_signal.emit(time_remaining.strip())
            
             size_match = re.search(r'\(([\d\.]+ [KMGT]?B)', line)
             if size_match:
                self.filesize = size_match.group(1)

        if file_created := re.search(r'file: (.+)', line):
            full_file_path = file_created.group(1).strip()
            if os.path.exists(full_file_path):
                self.full_file_path = full_file_path
                self.path_exists = True
            else:
               self.full_file_path = None
               self.path_exists = False

    def format_time(self, seconds):
        minutes = int(seconds // 60)
        seconds = int(seconds % 60)
        return f"{minutes}m{seconds}s"
    
    def close_process(self):
        if self.process and self.process.poll() is None:
            kill_command = ['taskkill', '/F', '/T', '/PID', str(self.process.pid)] if is_windows() else ['kill', '-9',
                                                                                                      str(self.process.pid)]
            subprocess.Popen(kill_command, creationflags=subprocess.CREATE_NO_WINDOW if is_windows() else 0)

def update_output(output_widget, line):
    output_widget.insertPlainText(line)
    output_widget.verticalScrollBar().setValue(output_widget.verticalScrollBar().maximum())

def handle_command_completion(success, status_label, progress_bar, window, queue_id):
    status_label.setText("Complete!" if success else "Failed.")
    status_label.setStyleSheet(f"color: {'green' if success else 'red'};")
    window.speed_label.setText("")
    progress_bar.setValue(0)
    window.is_sending = False
    if not success:
        window.remove_queue_item(queue_id)
    window.process_pending_queue()

class ModernScrollBar(QScrollBar):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""QScrollBar:vertical {{background-color: transparent;width: 10px;margin: 0px 0px 0px 0px;}}
            QScrollBar::handle:vertical {{background-color: {colors['scroll_bar_handle']};min-height: 20px;border-radius: 5px;}}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{background: none;}}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical{{background: none;}}""")


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("iMShare")
        self.setMinimumSize(800, 500)

        self.window_position = None
        self.start_move_position = None # Initialize here
        self.title_bar_height = 30
        self.setWindowFlag(Qt.FramelessWindowHint)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Custom Title Bar
        self.title_bar = QWidget(self)
        self.title_bar.setFixedHeight(self.title_bar_height)
        self.title_bar.setAttribute(Qt.WA_StyledBackground, True)
        
        # Initialize gradient for the title bar
        self.title_bar_gradient = QLinearGradient(0, 0, self.width(), self.title_bar_height)
        self.title_bar_gradient.setColorAt(0, QColor(colors["background_gradient_start"]))
        self.title_bar_gradient.setColorAt(1, QColor(colors["background_gradient_end"]))
        self.title_bar_palette = self.title_bar.palette()
        self.title_bar_palette.setBrush(self.title_bar.backgroundRole(), QBrush(self.title_bar_gradient))
        self.title_bar.setPalette(self.title_bar_palette)
        self.title_bar.setAutoFillBackground(True) # Necessary for the palette to apply


        title_layout = QHBoxLayout(self.title_bar)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(0)
        main_layout.addWidget(self.title_bar)


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


        content_layout = QHBoxLayout()
        content_layout.setContentsMargins(20, 20, 20, 20)


        queue_area_layout = QVBoxLayout()
        self.queue_layout = QVBoxLayout()
        self.queue_layout.setAlignment(Qt.AlignTop)
        self.file_queue_list = QListWidget()
        self.file_queue_list.setStyleSheet(
            f"QListWidget {{background-color: {colors['queue_background']};color: {colors['queue_text']};border: {colors['queue_border']};border-radius: 10px;padding: 5px;outline: 0;}}")
        self.file_queue_list.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.file_queue_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.file_queue_list.setVerticalScrollBar(ModernScrollBar()) # Apply the custom scrollbar here
        self.file_queue_list.setMaximumWidth(200)
        self.file_queue_list.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self.file_queue_list.itemClicked.connect(self.handle_queue_item_click)
        self.queue_layout.addWidget(self.file_queue_list)
        queue_area_layout.addLayout(self.queue_layout)
        content_layout.addLayout(queue_area_layout)

        main_content_layout = QVBoxLayout()
        main_content_layout.setAlignment(Qt.AlignTop)


        self.file_info_layout = QVBoxLayout()
        self.file_info_layout.setAlignment(Qt.AlignCenter)
        self.file_name_label = QLabel("No File Selected")
        self.file_name_label.setStyleSheet("color: white; font-size: 14px; font-weight: bold;")
        self.file_name_label.setAlignment(Qt.AlignCenter)
        self.file_info_layout.addWidget(self.file_name_label)
        self.file_size_label = QLabel("")
        self.file_size_label.setStyleSheet(f"color: {colors['time_speed_text']}; font-size: 10px; font-style: italic")
        self.file_size_label.setAlignment(Qt.AlignCenter)
        self.file_info_layout.addWidget(self.file_size_label)
        main_content_layout.addLayout(self.file_info_layout)

        path_layout = QHBoxLayout()
        path_label = QLabel("Code:")
        path_label.setStyleSheet("color: white;")
        path_layout.addWidget(path_label)
        self.path_entry = QLineEdit()
        self.path_entry.setStyleSheet(
            f"QLineEdit {{background-color: {colors['path_entry_background']};color: {colors['path_entry_text']};border: 2px solid {colors['path_entry_border']};border-radius: 10px;padding: 5px;}}"
        )
        self.path_entry.mousePressEvent = self.select_all_text
        path_layout.addWidget(self.path_entry)
        self.clear_path_button = QPushButton("🗑")
        self.clear_path_button.clicked.connect(self.clear_all)
        self.clear_path_button.setFixedWidth(30)
        self.clear_path_button.setStyleSheet(
            f"QPushButton {{background-color: {colors['clear_button_background']};color: white;border: 2px solid {colors['path_entry_border']};border-radius: 10px;padding: 5px;}}\n            QPushButton:hover {{background-color: {colors['clear_button_background_hover']};}}")
        path_layout.addWidget(self.clear_path_button)
        main_content_layout.addLayout(path_layout)
        
        button_layout = QHBoxLayout()
        button_layout.setAlignment(Qt.AlignCenter)
        self.send_file_button = QPushButton("Download File")
        self.send_file_color = colors["send_button_color"]
        self.set_button_style(self.send_file_button, self.send_file_color, rounded=True)
        self.send_file_button.clicked.connect(self.start_command)
        button_layout.addWidget(self.send_file_button)
        main_content_layout.addLayout(button_layout)

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(20)
        self.progress_bar.setStyleSheet(
            f"QProgressBar {{border: 2px solid {colors['progress_bar_border']};border-radius: 5px;background-color: {colors['progress_bar_background']};text-align: center;color: {colors['progress_bar_text']};font-size: 14px;}} QProgressBar::chunk {{background-color: {colors['progress_bar_chunk']};border-radius: 10px;}}")
        self.progress_bar.setValue(0)
        main_content_layout.addWidget(self.progress_bar)

        self.progress_info_layout = QHBoxLayout()
        self.progress_info_layout.setAlignment(Qt.AlignCenter)
        self.time_remaining_label = QLabel("")
        self.time_remaining_label.setStyleSheet(f"color: {colors['time_speed_text']}; font-size: 10px; font-style: italic")
        self.time_remaining_label.setAlignment(Qt.AlignCenter)
        self.progress_info_layout.addWidget(self.time_remaining_label)
        self.speed_label = QLabel("")
        self.speed_label.setStyleSheet(f"color: {colors['time_speed_text']}; font-size: 10px; font-style: italic")
        self.speed_label.setAlignment(Qt.AlignCenter)
        self.progress_info_layout.addWidget(self.speed_label)
        main_content_layout.addLayout(self.progress_info_layout)

        self.friends_scroll_area = QScrollArea()
        self.friends_scroll_area.setWidgetResizable(True)
        self.friends_scroll_area.setFrameShape(QFrame.NoFrame)
        self.friends_scroll_area.setStyleSheet(f"background-color: {colors['friends_scroll_background']}; border-radius: 10px;")
        self.friends_scroll_area.setVerticalScrollBar(ModernScrollBar()) # Apply the custom scrollbar here
        self.friends_container = QWidget()
        self.friends_container_layout = QGridLayout(self.friends_container)
        self.friends_container_layout.setAlignment(Qt.AlignTop)
        self.friends_container_layout.setContentsMargins(10, 10, 10, 10)
        self.friends_scroll_area.setWidget(self.friends_container)
        main_content_layout.addWidget(self.friends_scroll_area)
        self.add_friend_button = self.create_add_button()
        self.friends_container_layout.addWidget(self.add_friend_button, 0, 0)

        self.status_frame = QFrame()
        self.status_frame.setStyleSheet(f"background-color: {colors['status_frame_background']}; border-radius: 10px;")
        self.status_layout = QHBoxLayout(self.status_frame)
        self.status_layout.setAlignment(Qt.AlignCenter)
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet(
            f"color: {colors['status_text']}; font-size: 14px; text-shadow: -1px -1px 0 {colors['status_shadow']}, 1px -1px 0 {colors['status_shadow']}, -1px 1px 0 {colors['status_shadow']}, 1px 1px 0 {colors['status_shadow']};")
        self.status_layout.addWidget(self.status_label)
        main_content_layout.addWidget(self.status_frame)

        self.output_expand_button = QPushButton("v")
        self.output_expand_button.setFixedSize(30, 30)
        self.output_expand_button.setStyleSheet(
            f"QPushButton {{background-color: {colors['output_expand_background']};color: white;border: 0px solid rgba(50, 50, 50, 0.1);border-radius: 15px;}}\n            QPushButton:hover {{background-color: {colors['output_expand_hover']};}}")
        self.output_expand_button.clicked.connect(self.toggle_output)
        output_layout = QHBoxLayout()
        output_layout.addWidget(self.output_expand_button, alignment=Qt.AlignLeft)
        main_content_layout.addLayout(output_layout)
        
        self.output_text = QTextEdit()
        self.output_text.setStyleSheet(
            f"QTextEdit {{background-color: {colors['output_text_background']};color: {colors['output_text_color']};border: 2px solid {colors['output_text_border']};border-radius: 10px;padding: 1px;}}"
        )
        self.output_text.setVerticalScrollBar(ModernScrollBar())
        self.output_text.setHorizontalScrollBar(ModernScrollBar())
        self.output_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.output_text.setFixedHeight(80)
        main_content_layout.addWidget(self.output_text)
        
        content_layout.addLayout(main_content_layout)
       
        main_layout.addLayout(content_layout)

        self.queue_layout.setStretch(0, 1)
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
        self.clear_message_timer = QTimer(self)
        self.clear_message_timer.timeout.connect(self.clear_message_timeout)
        self.current_file = None
        self.output_visible = False 
        self.output_text.setVisible(self.output_visible) 
        self.output_expand_button.setText("^") 
        
        self.config_dir = os.path.join(resource_path("."), "config")
        os.makedirs(self.config_dir, exist_ok=True)
        self.config_file = os.path.join(self.config_dir, "iMShare.json")
        self.settings = self.load_settings()
        self.download_code = self.settings.get("download_code", None)
        self.path_entry.setText(self.download_code or "")

        self.friends = self.settings.get("friends", [])
        self.load_friends()

        set_drop_shadow(self.send_file_button)
        set_drop_shadow(self.file_queue_list)
        set_drop_shadow(self.friends_scroll_area)
        set_drop_shadow(self.status_frame)
        set_drop_shadow(self.path_entry)
        set_drop_shadow(self.clear_path_button)
        set_drop_shadow(self.progress_bar)

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
    
    def resizeEvent(self, event):
        # Update the title bar gradient if window size changes
        self.title_bar_gradient = QLinearGradient(0, 0, self.width(), self.title_bar_height)
        self.title_bar_gradient.setColorAt(0, QColor(colors["background_gradient_start"]))
        self.title_bar_gradient.setColorAt(1, QColor(colors["background_gradient_end"]))
        self.title_bar_palette.setBrush(self.title_bar.backgroundRole(), QBrush(self.title_bar_gradient))
        self.title_bar.setPalette(self.title_bar_palette)


        self.set_gradient_background()
        super().resizeEvent(event)

    def update_progress_bar(self, progress, color, is_hashing):
         self.progress_bar.setStyleSheet(
            f"""QProgressBar {{border: 2px solid {colors['progress_bar_border']};border-radius: 5px;background-color: {colors['progress_bar_background']};text-align: center;color: {colors['progress_bar_text']};font-size: 14px;}}
             QProgressBar::chunk {{background-color: {color};border-radius: 10px;}}""")
         self.progress_bar.setValue(progress)

    def update_speed(self, speed):
        self.speed_label.setText(f"{speed}")

    def update_time_remaining(self, time_remaining):
        self.time_remaining_label.setText(f"{time_remaining}")

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

        if message == "Ready to Download":
            self.status_label.setStyleSheet(
                f"color: {color}; font-style: normal; {shadow_style}"
            )
        else:
             self.status_label.setStyleSheet(
                f"color: {color}; {shadow_style}"
             )
        self.dot_count = 0
        self.update_dots()
        if "Loading..." in message or "Downloading..." in message:
            self.dot_animation_timer.start(500)
        else:
            self.dot_animation_timer.stop()

    def update_dots(self):
        if "Loading..." in self.current_status_message or "Downloading..." in self.current_status_message:
            dots = "." * (self.dot_count % 4)
            self.status_label.setText(f"{self.current_status_message}{dots}")
            self.dot_count += 1
        else:
            self.status_label.setText(self.current_status_message)

    def set_button_style(self, button, color, rounded=False):
        border_radius = "10px" if rounded else "0px"
        button.setStyleSheet(f"""QPushButton {{background-color: #444;color: white;border: 2px solid #555;border-radius: {border_radius};padding: 10px 20px;font-size: 12px;min-width: 150px;}}
            QPushButton:hover {{background-color: {color};}}
            QPushButton:pressed {{background-color: #333;}}""")

    def center_window(self):
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())
    
    def select_all_text(self, event):
        self.path_entry.selectAll()
        QLineEdit.mousePressEvent(self.path_entry, event)
    
    def load_settings(self):
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as file:
                    return json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
            pass
        return {}

    def save_code_to_json(self, code):
        self.download_code = code
        self.settings["download_code"] = code
        try:
            with open(self.config_file, 'w') as file:
                json.dump(self.settings, file, indent=4)
        except Exception as e:
            print(f"Failed to save settings: {e}")
        self.process_pending_queue()
    
    def toggle_output(self):
        self.output_visible = not self.output_visible
        self.output_text.setVisible(self.output_visible)
        self.output_expand_button.setText("v" if self.output_visible else "^")
        
    
    def start_command(self):
        code_prefix = self.path_entry.text().strip()
        if not code_prefix:
            self.status_label.setText("Please enter a code.")
            self.status_label.setStyleSheet(
                "color: red; text-shadow: -1px -1px 0 black, 1px -1px 0 black, -1px 1px 0 black, 1px 1px 0 black;")
            self.clear_message_timer.start(3000)
            return
        
        if self.is_sending:
            self.status_label.setText("Already sending.")
            self.status_label.setStyleSheet(
                "color: red; text-shadow: -1px -1px 0 black, 1px -1px 0 black, -1px 1px 0 black, 1px 1px 0 black;")
            self.clear_message_timer.start(3000)
            return
        
        self.download_code = code_prefix
        self.save_code_to_json(code_prefix)
            
        queue_id = str(uuid.uuid4())
        
        self.file_queue.put((code_prefix, queue_id))
        self.process_pending_queue()

    def process_pending_queue(self):
        if self.is_sending:
            return
        if not self.file_queue.empty():
            code_prefix, queue_id = self.file_queue.get()
            self.is_sending = True
            
            self.current_file = ("File", "N/A")
            self.file_name_label.setText(f"File: File")
            self.file_size_label.setText(f"Size: N/A")
            
            list_item = QListWidgetItem("File", self.file_queue_list)
            list_item.queue_id = queue_id
            self.file_queue_list.addItem(list_item)
            
            self.start_send_thread(code_prefix, queue_id)

    def start_send_thread(self, code_prefix, queue_id):
        send_thread = SendFileThread(code_prefix, self.send_file_color, self.send_file_color, self, queue_id=queue_id)
        send_thread.output_signal.connect(lambda line: update_output(self.output_text, line))
        send_thread.finished_signal.connect(
            lambda success, queue_id: handle_command_completion(success, self.status_label, self.progress_bar, self, queue_id))
        send_thread.progress_signal.connect(lambda progress: self.update_progress_bar(progress, self.send_file_color, False))
        send_thread.hashing_progress_signal.connect(lambda progress: self.update_progress_bar(progress, self.send_file_color, True))
        send_thread.speed_signal.connect(self.update_speed)
        send_thread.status_update_signal.connect(self.update_animated_status)
        send_thread.time_remaining_signal.connect(self.update_time_remaining)
        send_thread.current_file_signal.connect(self.update_current_file_info)
        send_thread.queue_id_signal.connect(self.update_queue_item_status)
        send_thread.file_name_size_signal.connect(self.update_queue_item_name_size)
        send_thread.start()
        self.active_threads.append(send_thread)

    def update_queue_item_status(self, queue_id):
        for i in range(self.file_queue_list.count()):
            item = self.file_queue_list.item(i)
            if hasattr(item, 'queue_id') and item.queue_id == queue_id:
                if self.status_label.text() == "Completed!":
                    item.setText(f"📁  {item.text()}")
                    item.is_complete = True
                if self.status_label.text() == "Downloading...":
                    item.setText(f"⏳ {item.text().replace('📁 ', '')}")
                    item.is_complete = False
                if self.status_label.text() == "Ready to Download":
                    item.setText(f"{item.text().replace('⏳ ', '')}")
                item.is_complete = False
                    
    def update_queue_item_name_size(self, filename, filesize, queue_id):
       for i in range(self.file_queue_list.count()):
          item = self.file_queue_list.item(i)
          if hasattr(item, 'queue_id') and item.queue_id == queue_id:
            item.setText(f"{filename} ({filesize})")
            break
           
    def remove_queue_item(self, queue_id):
        for i in range(self.file_queue_list.count()):
            item = self.file_queue_list.item(i)
            if hasattr(item, 'queue_id') and item.queue_id == queue_id:
                self.file_queue_list.takeItem(i)
                break

    def update_current_file_info(self, filename, filesize):
        self.current_file = (filename, filesize)
        self.file_name_label.setText(f"File: {filename}")
        self.file_size_label.setText(f"Size: {filesize}")
    
    def handle_queue_item_click(self, item):
        if hasattr(item, 'queue_id') and hasattr(item, 'is_complete') and item.is_complete:
          for thread in self.active_threads:
                if hasattr(thread, "queue_id") and thread.queue_id == item.queue_id:
                    if not thread.path_exists:
                      print("Error: path not found")
                      break

                    if item.text().startsWith("📁 "):
                        if thread.full_file_path:
                            QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.dirname(thread.full_file_path)))
                        else:
                           print("Error: full_file_path not found for the folder")
                    elif thread.full_file_path:
                        QDesktopServices.openUrl(QUrl.fromLocalFile(thread.full_file_path))
                    else:
                        print("Error: full_file_path not found")
                    break
        self.file_queue_list.clearSelection()
    
    def create_add_button(self):
       button = QPushButton()
       button.setFixedSize(70, 70)
       button.setStyleSheet(f"""QPushButton {{
         background-color: {colors['add_friend_button']};
         border: 2px solid #008080;
         border-radius: 35px;
         color: white;
         font-size: 12px;
         }}
         QPushButton:hover {{
             background-color: {colors['add_friend_button_hover']};
         }}""")
       button.clicked.connect(self.show_add_friend_popup)
       button.setText("Add")
       set_drop_shadow(button)  
       return button

    
    def show_add_friend_popup(self):
        popup = AddFriendPopup(self)
        if popup.exec_() == QDialog.Accepted:
           new_friend = popup.get_new_friend_data()
           if new_friend:
            self.add_friend(new_friend)
        
    def load_friends(self):
        self.clear_friends_container()
        row = 0
        col = 0
        for friend in self.friends:
            friend_widget = self.create_friend_widget(friend)
            self.friends_container_layout.addWidget(friend_widget, row, col)
            col += 1
            if col > 5:
                col = 0
                row += 1
        self.friends_container_layout.addWidget(self.add_friend_button, row, col)

    def clear_friends_container(self):
        while self.friends_container_layout.count():
             item = self.friends_container_layout.takeAt(0)
             widget = item.widget()
             if widget and widget != self.add_friend_button:
                 widget.deleteLater()
    
    def add_friend(self, new_friend):
        self.friends.append(new_friend)
        self.save_friends_to_json()
        self.load_friends()

       
    def save_friends_to_json(self):
        self.settings["friends"] = self.friends #now it is saving the updated list
        try:
            with open(self.config_file, 'w') as file:
                json.dump(self.settings, file, indent=4)
        except Exception as e:
            print(f"Failed to save friends settings: {e}")
            
    def create_friend_widget(self, friend):
        container = QWidget()
        container.setFixedSize(75, 100)
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container.setStyleSheet("background: transparent;")
        set_drop_shadow(container)

        image_container = QWidget(container)
        image_container.setFixedSize(72, 72)
        image_container_layout = QVBoxLayout(image_container)
        image_container_layout.setContentsMargins(0, 0, 0, 0)
        image_container.setStyleSheet(f"border: 1px solid black; border-radius: 36px; background: transparent;")

        image_label = QLabel(image_container)
        image_label.setFixedSize(70, 70)
        image_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        image_label.setAlignment(Qt.AlignCenter)

        pixmap = self.create_thumbnail(friend.get("image", resource_path(os.path.join("img", "default-profile.png"))), size=70)

        mask = QRegion(0, 0, 70, 70, QRegion.Ellipse)
        image_label.setMask(mask)

        image_label.setPixmap(pixmap)
        image_label.setScaledContents(True)

        image_container_layout.addWidget(image_label, alignment=Qt.AlignCenter)

        name_label = QLabel(friend.get("name", "Name"), container)
        name_label.setStyleSheet("color: white; margin-top: 5px; border:none;")
        name_label.setAlignment(Qt.AlignCenter)

        code_prefix = friend.get("download_code", "")

        # Left-click event on image_label for command execution
        image_label.mousePressEvent = lambda event, code=code_prefix, current_friend=friend: self.handle_friend_image_click(event, code)

        # Right-click event on container for context menu, only trigger if the container is right clicked (not its children)
        container.mousePressEvent = lambda event, code=code_prefix, current_friend=friend, current_container=container: self.handle_container_click(event, current_container, current_friend)


        container_layout.addWidget(image_container, alignment=Qt.AlignCenter)
        container_layout.addWidget(name_label)

        return container


    def handle_container_click(self, event, container, friend_data):
        if event.button() == Qt.RightButton:
            self.show_friend_context_menu(container, friend_data)
            event.accept()
        else:
            event.ignore()


    def show_friend_context_menu(self, container, friend_data):
         menu = QMenu(self)
         menu.setStyleSheet(
             f"QMenu {{background-color: rgba(50, 50, 50, 0.8); border: 1px solid #008080; border-radius: 10px; color: white;}} "
             f"QMenu::item:selected {{background-color: rgba(100, 100, 100, 0.9);}}"
         )
         delete_action = menu.addAction("Delete")
         action = menu.exec_(container.mapToGlobal(container.rect().topLeft()))
         if action == delete_action:
            self.delete_friend(friend_data)

    def handle_friend_image_click(self, event, code):
      if event.button() == Qt.LeftButton:
        self.execute_croc_command(code) 

    def delete_friend(self, friend_to_delete):
        self.friends = [friend for friend in self.friends if friend != friend_to_delete]
        self.save_friends_to_json()
        self.load_friends()
    
    def create_thumbnail(self, image_path, size=64):
        try:
            image = QImage(image_path)
            if image.isNull():
              return QPixmap(resource_path(os.path.join("img", "default-profile.png")))
            scaled_image = image.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            pixmap = QPixmap.fromImage(scaled_image)
            return pixmap
        except Exception:
            return QPixmap(resource_path(os.path.join("img", "default-profile.png")))
    
    def execute_croc_command(self, code):
      if not code:
          self.status_label.setText("No code for friend.")
          self.status_label.setStyleSheet("color: red;")
          self.clear_message_timer.start(3000)
          return
      
      if self.is_sending:
          self.status_label.setText("Already sending.")
          self.status_label.setStyleSheet("color: red;")
          self.clear_message_timer.start(3000)
          return
      
      self.path_entry.setText(code)
      self.start_command()


class AddFriendPopup(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Friend")
        self.setModal(True)
        self.setFixedSize(350, 300)
        self.setStyleSheet(f"background-color: {colors['add_friend_popup_background']}; color: {colors['add_friend_popup_text']};")
        self.new_friend_data = {}
        self.current_pixmap = None

        layout = QVBoxLayout(self)

        self.profile_preview = QLabel()
        self.profile_preview.setFixedSize(80, 80)
        self.profile_preview.setAlignment(Qt.AlignCenter)
        self.profile_preview.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        
        default_pixmap = self.create_default_pixmap(size=80)
        mask = QRegion(0, 0, 80, 80, QRegion.Ellipse)
        self.profile_preview.setMask(mask)
        
        self.profile_preview.setPixmap(default_pixmap)
        self.profile_preview.setScaledContents(True)
        layout.addWidget(self.profile_preview, alignment=Qt.AlignCenter)
        set_drop_shadow(self.profile_preview) 
            
        profile_label = QLabel("Profile:")
        profile_label.setStyleSheet("color: white;")
        layout.addWidget(profile_label)
        
        self.profile_selector_button = QPushButton("Select Image")
        self.profile_selector_button.clicked.connect(self.select_profile_image)
        self.profile_selector_button.setStyleSheet(
                "QPushButton {background-color: #444;color: white;border: 2px solid #008080;border-radius: 10px;padding: 5px;}\n            QPushButton:hover {background-color: #555;}")
        layout.addWidget(self.profile_selector_button)
        set_drop_shadow(self.profile_selector_button)
        
        name_label = QLabel("Name:")
        name_label.setStyleSheet("color: white;")
        layout.addWidget(name_label)
        
        self.name_entry = QLineEdit()
        self.name_entry.setStyleSheet(
            "QLineEdit {background-color: #444;color: white;border: 2px solid #008080;border-radius: 10px;padding: 5px;}"
        )
        layout.addWidget(self.name_entry)
        set_drop_shadow(self.name_entry) 
        
        code_label = QLabel("Code:")
        code_label.setStyleSheet("color: white;")
        layout.addWidget(code_label)

        self.code_entry = QLineEdit()
        self.code_entry.setStyleSheet(
            "QLineEdit {background-color: #444;color: white;border: 2px solid #008080;border-radius: 10px;padding: 5px;}"
        )
        layout.addWidget(self.code_entry)
        set_drop_shadow(self.code_entry) 

        button_layout = QHBoxLayout()
        save_button = QPushButton("Add")
        save_button.clicked.connect(self.accept)
        save_button.setStyleSheet(
            "QPushButton {background-color: #444;color: white;border: 2px solid #008080;border-radius: 10px;padding: 5px;}\n            QPushButton:hover {background-color: #555;}")
        button_layout.addWidget(save_button)
        set_drop_shadow(save_button)
        
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        cancel_button.setStyleSheet(
             "QPushButton {background-color: #444;color: white;border: 2px solid #555;border-radius: 10px;padding: 5px;}\n            QPushButton:hover {background-color: #555;}")
        button_layout.addWidget(cancel_button)
        set_drop_shadow(cancel_button) 
        
        layout.addLayout(button_layout)

    def create_default_pixmap(self, size=64):
        default_image = QImage(resource_path(os.path.join("img", "default-profile.png")))
        scaled_image = default_image.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        pixmap = QPixmap.fromImage(scaled_image)
        return pixmap
        
    def select_profile_image(self):
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getOpenFileName(self, "Select Profile Image", "", "Image Files (*.png *.jpg *.jpeg *.bmp)")
        if file_path:
          self.new_friend_data["image"] = file_path
          self.current_pixmap = self.create_thumbnail(file_path, size=80)
          mask = QRegion(0, 0, 80, 80, QRegion.Ellipse)
          self.profile_preview.setMask(mask)
          self.profile_preview.setPixmap(self.current_pixmap)

    def create_thumbnail(self, image_path, size=64):
            try:
                image = QImage(image_path)
                if image.isNull():
                    return self.create_default_pixmap(size)
                scaled_image = image.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                pixmap = QPixmap.fromImage(scaled_image)
                return pixmap
            except Exception:
               return self.create_default_pixmap(size)

    def get_new_friend_data(self):
        name = self.name_entry.text().strip()
        code = self.code_entry.text().strip()
        
        if not name or not code:
            return None
        
        friend_data = {}
        friend_data["name"] = name
        friend_data["download_code"] = code
        if "image" in self.new_friend_data:
            friend_data["image"] = self.new_friend_data["image"]
        self.new_friend_data = {}
        return friend_data

if __name__ == '__main__':
    if is_windows():
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("myappid")
        
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
