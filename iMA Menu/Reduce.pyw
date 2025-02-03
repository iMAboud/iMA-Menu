import sys
import os
import subprocess
import shlex
from PyQt5.QtWidgets import (QApplication, QWidget, QLabel, QPushButton,
                             QProgressBar, QHBoxLayout, QVBoxLayout, QSizePolicy, QMessageBox, QComboBox, QTextEdit)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QObject
from PyQt5.QtGui import QPixmap, QImage, QColor
import pyperclip  # For clipboard access
import re

class CommandExecutor(QThread):
    console_output_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(bool, str) #Add error message for failed events
    progress_signal = pyqtSignal(int)

    def __init__(self, command, total_duration, parent=None):
        super().__init__(parent)
        self.command = command
        self.process = None
        self.error_message = ""
        self.total_duration = total_duration
        self.start_time = 0

    def run(self):
        try:
            self.process = subprocess.Popen(self.command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0)
            
            while True:
              
                output = self.process.stderr.read(1024)
                if not output:
                     break
               
                self.console_output_signal.emit(output)

                time_matches = re.findall(r"time=(\d{2}:\d{2}:\d{2}(?:\.\d+)?)", output)
                if time_matches:
                     for time_str in time_matches:
                         h, m, s = map(float, time_str.split(":"))
                         current_time = h * 3600 + m * 60 + s
                         progress = int(((current_time - self.start_time) / self.total_duration) * 100) if self.total_duration > 0 else 0
                         self.progress_signal.emit(max(0, min(progress, 100)))
                    
            self.process.wait()
            if self.process.returncode != 0:
               self.error_message = f"Error: Command exited with code {self.process.returncode}"
               self.finished_signal.emit(False, self.error_message)
            else:
              self.finished_signal.emit(True, "")
        except Exception as e:
             self.error_message = f"An error occurred: {e}"
             self.finished_signal.emit(False, self.error_message)
        finally:
             if self.process:
              self.process = None
             

    def stop(self):
        if self.process and self.process.poll() is None:
             self.process.terminate()

class FFmpegWorker(QThread):
    finished = pyqtSignal(str)
    progress = pyqtSignal(int)

    def __init__(self, file_path, is_video, preset_name, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.is_video = is_video
        self.preset_name = preset_name
        self.compressed_path = f"{file_path}.compressed.mp4" if is_video else f"{file_path}.compressed.jpg"
        self.executor = None
        self.total_duration = 0
        self.start_time = 0
    
    def get_filesize(self, path):
      try:
        size = os.path.getsize(path)
        return self.format_size(size)
      except FileNotFoundError:
        return "N/A"
    
    def get_video_duration(self):
        try:
            quoted_file_path = shlex.quote(self.file_path)
            command = f'ffmpeg -i {quoted_file_path}'
            creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            process = subprocess.Popen(shlex.split(command), stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, creationflags=creationflags)
            
            duration = 0
            start_time = 0
            while True:
                line = process.stderr.readline()
                if not line:
                    break
                duration_match = re.search(r"Duration: (\d{2}:\d{2}:\d{2}\.\d{2})", line)
                start_match = re.search(r"start: (\d+\.\d+)", line)
                if duration_match:
                     duration_str = duration_match.group(1)
                     h, m, s = map(float, duration_str.split(":"))
                     duration = h * 3600 + m * 60 + s
                if start_match:
                     start_time = float(start_match.group(1))
            process.wait()
            return duration, start_time
        except subprocess.CalledProcessError as e:
             print(f"Error getting duration: {e}")
             return 0, 0
        except ValueError as e:
             print(f"ValueError getting duration: {e}")
             return 0, 0

    def format_size(self, size_bytes):
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            size_kb = size_bytes / 1024
            return f"{size_kb:.2f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            size_mb = size_bytes / (1024 * 1024)
            return f"{size_mb:.2f} MB"
        else:
            size_gb = size_bytes / (1024 * 1024 * 1024)
            return f"{size_gb:.2f} GB"
    
    def run(self):
      if not os.path.exists(self.file_path):
        self.finished.emit("File does not exist!")
        return
      
      try:
            self.total_duration, self.start_time = self.get_video_duration()
            if self.total_duration == 0:
                  self.finished.emit("Could not get file duration")
                  return
            quoted_file_path = shlex.quote(self.file_path)
            preset = self.get_preset_options()
            if self.is_video:
                command = f'ffmpeg -y -i {quoted_file_path} -c:v libx264 {preset} -c:a aac -b:a 128k -pix_fmt yuv420p "{self.compressed_path}"'
            else:
                command = f'ffmpeg -y -i {quoted_file_path} -vf scale=600:-1 -quality:v 8 "{self.compressed_path}"'
            
            
      except FileNotFoundError:
         error_message = "ffmpeg not found"
      except Exception as e:
         error_message = f"An unexpected error happened {e}"
      else:
            self.executor = CommandExecutor(shlex.split(command), self.total_duration, self)
            self.executor.start_time = self.start_time
            self.executor.console_output_signal.connect(self.print_output)
            self.executor.finished_signal.connect(self.handle_command_completion)
            self.executor.progress_signal.connect(self.progress.emit)
            self.executor.start() # Start the thread if no errors
            return
      finally:
         if "error_message" in locals():
            self.finished.emit(error_message)

    
    def get_preset_options(self):
         match self.preset_name:
            case "Fastest - Lowest Quality":
                  return "-preset ultrafast -tune zerolatency -crf 32"
            case "Fast - Low Quality":
                 return "-preset fast -crf 30"
            case "Normal - Medium Quality":
                return "-preset medium -crf 26"
            case "Slow - High Quality":
                 return "-preset slow -crf 22"
            case "Slowest - Highest Quality":
                return "-preset veryslow -crf 18"
            case _:
                return "-preset ultrafast -tune zerolatency -crf 32"
    
    def print_output(self, line):
        print(line)

    def handle_command_completion(self, success, error):
        if success:
             self.finished.emit(self.compressed_path)
        else:
            self.finished.emit(error)
            
    def stop(self):
      if self.executor:
         self.executor.stop()
         self.executor.wait()
         self.executor = None

class RoundedButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setStyleSheet("""
            QPushButton {
                background-color: #282c34;
                color: white;
                border: 1px solid #333;
                border-radius: 10px;
                padding: 8px 15px;
            }
            QPushButton:hover {
                background-color: #353a44;
            }
             QPushButton:pressed {
                background-color: #20242b;
            }

        """)

class RoundedLabel(QLabel):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setStyleSheet("""
             QLabel{
                color: #fff;
                background-color: transparent;
                border-radius: 10px;
                padding: 8px 15px;
            }
        """)
        self.setAlignment(Qt.AlignCenter)
class RoundedProgressBar(QProgressBar):
  def __init__(self, parent=None):
    super().__init__(parent)
    self.setTextVisible(False)  # Disable default text
    self.setStyleSheet("""
      QProgressBar {
          background-color: #333;
          border-radius: 5px;
          text-align: center;
          border: 0.5px solid #fff;
      }
      QProgressBar::chunk {
          background-color: #009688;
          border-radius: 5px;
      }
  """)
  


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("File Compressor")
        self.setGeometry(100, 100, 800, 400)
        self.setStyleSheet("background-color: #21252b;")
        self.ffmpeg_worker = None
        self.init_ui()
        self.file_path = self.get_clipboard_path()
        
        if self.file_path:
          self.load_file(self.file_path)
        
        

    def init_ui(self):
        # Main layout
        main_layout = QHBoxLayout()
        main_layout.setSpacing(20)  # space between layout
        self.setLayout(main_layout)

        # Left Panel (Preview)
        left_layout = QVBoxLayout()
        self.preview_widget = QLabel()
        self.preview_widget.setMinimumSize(400, 300)
        self.preview_widget.setAlignment(Qt.AlignCenter)
        self.preview_widget.setStyleSheet("background-color: #333; border-radius: 15px;")
        left_layout.addWidget(self.preview_widget)
        left_layout.setAlignment(Qt.AlignCenter)
        main_layout.addLayout(left_layout)

        # Right Panel (Information and Control)
        right_layout = QVBoxLayout()
        
        # File Size Labels
        size_layout = QHBoxLayout()
        self.before_label = RoundedLabel("Before: N/A")
        self.after_label = RoundedLabel("After: N/A")

        size_layout.addWidget(self.before_label)
        size_layout.addWidget(self.after_label)
        right_layout.addLayout(size_layout)
        
        # Preset Selection
        self.preset_combo = QComboBox()
        self.preset_combo.addItems([
            "Fastest - Lowest Quality",
            "Fast - Low Quality",
            "Normal - Medium Quality",
            "Slow - High Quality",
            "Slowest - Highest Quality"
        ])
        right_layout.addWidget(self.preset_combo)
        
        # Progress Bar
        self.progress_bar = RoundedProgressBar()
        self.progress_bar.setFixedHeight(15)
        right_layout.addWidget(self.progress_bar)

        # Button
        self.run_button = RoundedButton("Compress")
        self.run_button.clicked.connect(self.run_command)
        self.run_button.setFixedWidth(100)
        self.run_button.setFixedHeight(40)
        right_layout.addWidget(self.run_button, alignment=Qt.AlignCenter)
        
        right_layout.setAlignment(Qt.AlignCenter)
        main_layout.addLayout(right_layout)

    def get_clipboard_path(self):
          clipboard = QApplication.clipboard()
          text = clipboard.text()
          if text:
              return text.strip()
          return None

    def load_file(self, file_path):
        if not file_path:
            return
        
        if file_path.startswith('"') and file_path.endswith('"'):
          file_path = file_path[1:-1]
        if not os.path.exists(file_path):
            print("File Not found")
            return
      
        self.before_label.setText(f"Before: {self.format_size(os.path.getsize(file_path))}")
        
        is_video = self.is_video_file(file_path)
        
        self.show_thumbnail(file_path)
        
        self.file_path = file_path
        self.is_video = is_video
        
    def is_video_file(self, file_path):
          try:
            creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            result = subprocess.run(
                ['ffmpeg', '-i', file_path],
                capture_output=True,
                text=True,
                check=False,  # Don't raise an exception if ffmpeg returns an error
                creationflags=creationflags
            )
            
            if "Video:" in result.stderr:
                return True
            else:
                return False
          except FileNotFoundError:
                return False

    def show_thumbnail(self, file_path):
      
      pixmap = QPixmap()
      
      if self.is_video_file(file_path):
          try:
              quoted_file_path = shlex.quote(file_path)
              command = f'ffmpeg -i {quoted_file_path} -ss 00:00:01 -vframes 1 -f image2 pipe:1'
              creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
              process = subprocess.Popen(shlex.split(command), stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=creationflags)
              image_data, _ = process.communicate()
              image = QImage()
              if image.loadFromData(image_data):
                    pixmap = QPixmap.fromImage(image)

          except Exception as e:
                print(f"could not create thumbnail {e}")

      else:
          pixmap = QPixmap(file_path)
      
      if not pixmap.isNull():
        scaled_pixmap = pixmap.scaled(390,290, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.preview_widget.setPixmap(scaled_pixmap)
      else:
        self.preview_widget.setText("Invalid file")
        self.preview_widget.setStyleSheet("background-color: #333; border-radius: 15px; color: #fff")
       

    def run_command(self):
        if not self.file_path:
            return

        self.progress_bar.setValue(0)
        self.after_label.setText("After: Processing...")
        self.run_button.setEnabled(False)
        selected_preset = self.preset_combo.currentText()
        self.ffmpeg_worker = FFmpegWorker(self.file_path, self.is_video, selected_preset)
        self.ffmpeg_worker.finished.connect(self.on_command_finished)
        self.ffmpeg_worker.progress.connect(self.update_progress)
        self.ffmpeg_worker.start()
    
    def update_progress(self,progress):
      self.progress_bar.setValue(min(progress,100))
    
    def format_size(self, size_bytes):
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            size_kb = size_bytes / 1024
            return f"{size_kb:.2f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            size_mb = size_bytes / (1024 * 1024)
            return f"{size_mb:.2f} MB"
        else:
            size_gb = size_bytes / (1024 * 1024 * 1024)
            return f"{size_gb:.2f} GB"

    def on_command_finished(self, compressed_path):
        self.run_button.setEnabled(True)
        if "Error" in compressed_path:
           self.after_label.setText("After: Error")
           QMessageBox.critical(self, "Error", compressed_path)
           print(compressed_path)
        else:
          size = self.ffmpeg_worker.get_filesize(compressed_path)
          self.after_label.setText(f"After: {size}")
        self.ffmpeg_worker = None
          
    def closeEvent(self, event):
         if self.ffmpeg_worker:
              self.ffmpeg_worker.stop()
              self.ffmpeg_worker.wait()
         event.accept()
          
if __name__ == '__main__':
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec_())
