import sys
from PyQt5.QtWidgets import (QApplication, QWidget, QPushButton, QLabel, QVBoxLayout,
                             QTextEdit, QFrame, QSizePolicy, QHBoxLayout)
from PyQt5.QtCore import Qt, QTimer, QSize
from PyQt5.QtGui import QFont, QColor, QPalette, QCursor, QIcon
import subprocess
import os
import time
import ctypes

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except:
        return False

def run_as_admin(cmd):
    if not is_admin():
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
        sys.exit()
    
def get_file_count(folder_path):
    total_files = 0
    try:
        for root, _, files in os.walk(folder_path):
            total_files += len(files)
    except OSError:
        return 0
    return total_files

class CleanGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("System Cleaner")
        self.setGeometry(100, 100, 600, 500)  
        self.setWindowFlags(Qt.FramelessWindowHint)  
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet("background-color: rgba(50, 50, 50, 0.9); border-radius: 10px;")  # semi-transparent background and rounded corners

        self.total_deleted_files = 0
        self.init_ui()

    def init_ui(self):
        self.main_layout = QVBoxLayout()

        # Title Bar
        self.title_bar = QWidget()
        self.title_bar.setObjectName("titleBar")
        self.title_bar.setFixedHeight(30)
        self.title_bar.setStyleSheet("""
            #titleBar {
               background-color: rgba(60, 60, 60, 0.9);
               border-top-left-radius: 10px;
               border-top-right-radius: 10px;
            }
        """)
        self.title_bar_layout = QHBoxLayout(self.title_bar)
        self.title_bar_layout.setContentsMargins(10,0,10,0)
        
         #Spacer for the left
        self.title_bar_layout.addStretch(1)

        # Close Button
        self.close_button = QPushButton()
        self.close_button.setFixedSize(20, 20)
        self.close_button.setStyleSheet("""
            QPushButton {
                background-color: red;
                border-radius: 10px;
                border: none;
                margin: 0;
            }
            QPushButton:hover {
                background-color: rgba(255, 0, 0, 0.8);
            }
            QPushButton:pressed {
               background-color: rgba(200, 0, 0, 0.8);
            }
        """)
        self.close_button.clicked.connect(self.close)
        self.close_button.setCursor(QCursor(Qt.PointingHandCursor))
        self.title_bar_layout.addWidget(self.close_button, alignment=Qt.AlignVCenter | Qt.AlignRight)
        self.main_layout.addWidget(self.title_bar)

        # Rounded Result Container
        self.output_container = QFrame()
        self.output_container.setObjectName("outputContainer")
        self.output_container.setStyleSheet("""
            #outputContainer {
                background-color: rgba(100, 100, 100, 0.9);
                border-radius: 15px;
                padding: 10px;
                margin: 10px;
                box-shadow: 2px 2px 5px rgba(0, 0, 0, 0.9);
            }
        """)

        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setStyleSheet("""
            QTextEdit {
               color: #40E0D0; 
               text-shadow: 0px 0px 5px rgba(0, 0, 0, 0.9);
                background-color: transparent;
                border: none;
                font-size: 12px;
            }
            QTextEdit:focus {
                border: none;
            }
            QScrollBar:vertical {
                border: none;
                background: rgba(80, 80, 80, 0.4);
                width: 10px;
                margin: 0px 0px 0px 0px;
            }
            QScrollBar::handle:vertical {
                background: rgba(150, 150, 150, 0.6);
                min-height: 20px;
                border-radius: 5px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                background: none;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """)

        self.output_container_layout = QVBoxLayout(self.output_container)
        self.output_container_layout.addWidget(self.output_text)

        # Clean Button
        self.clean_button = QPushButton("Clean!")
        self.clean_button.clicked.connect(self.run_cleanup)
        self.clean_button.setFixedHeight(50)
        self.clean_button.setStyleSheet("""
            QPushButton {
               background-color: rgba(60, 60, 60, 0.8);
                color: #40E0D0;
                border-radius: 15px;
                padding: 10px;
                font-size: 18px;
                box-shadow: 2px 2px 5px rgba(0, 0, 0, 0.7);
                border: none;
                text-shadow: 0px 0px 5px rgba(0, 0, 0, 0.9);
            }
            QPushButton:hover {
               background-color: rgba(80, 80, 80, 0.8);
            }
            QPushButton:pressed {
               background-color: rgba(50, 50, 50, 0.8);
            }
        """)

        # Counter Label
        self.counter_label = QLabel("Files Deleted: 0")
        self.counter_label.setAlignment(Qt.AlignCenter)
        self.counter_label.setStyleSheet("""
             QLabel {
               color: #40E0D0; 
               font-size: 14px; 
               text-shadow: 0px 0px 5px rgba(0, 0, 0, 0.9);
               background-color: rgba(100, 100, 100, 0.6);
               border-radius: 10px;
               padding: 5px;
               margin: 5px;
            }
        """)

        # Add elements to layout
        self.main_layout.addWidget(self.output_container)
        self.main_layout.addWidget(self.clean_button)
        self.main_layout.addWidget(self.counter_label, alignment=Qt.AlignCenter)
        self.setLayout(self.main_layout)

        # Set font for all labels for consistency
        font = QFont()
        font.setPointSize(12)  # Adjust as needed
        self.setFont(font)

        # Ensure layout is sized to parent
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def run_cleanup(self):
        self.output_text.clear()
        self.output_text.insertPlainText("Running Cleanup, please wait...\n")
        self.output_text.repaint()
        QTimer.singleShot(10,self._run_cleanup)

    def _run_cleanup(self):
        output_text = ""
        self.total_deleted_files = 0
        commands = [
            f'del /s /f /q %windir%\\temp\\*.*',
            f'rd /s /q %windir%\\temp',
            f'md %windir%\\temp',
            f'del /s /f /q %windir%\\Prefetch\\*.*',
            f'rd /s /q %windir%\\Prefetch',
            f'md %windir%\\Prefetch',
            f'del /s /f /q %windir%\\system32\\dllcache\\*.*',
            f'rd /s /q %windir%\\system32\\dllcache',
            f'md %windir%\\system32\\dllcache',
            f'del /s /f /q "{os.environ.get("SystemDrive")}\\Temp\\*.*"',
            f'rd /s /q "{os.environ.get("SystemDrive")}\\Temp"',
            f'md "{os.environ.get("SystemDrive")}\\Temp"',
            f'del /s /f /q %temp%\\*.*',
            f'rd /s /q %temp%',
            f'md %temp%',
            f'del /s /f /q "%USERPROFILE%\\Local Settings\\History\\*.*"',
            f'rd /s /q "%USERPROFILE%\\Local Settings\\History"',
            f'md "%USERPROFILE%\\Local Settings\\History"',
            f'del /s /f /q "%USERPROFILE%\\Local Settings\\Temporary Internet Files\\*.*"',
            f'rd /s /q "%USERPROFILE%\\Local Settings\\Temporary Internet Files"',
            f'md "%USERPROFILE%\\Local Settings\\Temporary Internet Files"',
            f'del /s /f /q "%USERPROFILE%\\Local Settings\\Temp\\*.*"',
            f'rd /s /q "%USERPROFILE%\\Local Settings\\Temp"',
            f'md "%USERPROFILE%\\Local Settings\\Temp"',
            f'del /s /f /q "%USERPROFILE%\\Recent\\*.*"',
            f'rd /s /q "%USERPROFILE%\\Recent"',
            f'md "%USERPROFILE%\\Recent"',
            f'del /s /f /q "%USERPROFILE%\\Cookies\\*.*"',
            f'rd /s /q "%USERPROFILE%\\Cookies"',
            f'md "%USERPROFILE%\\Cookies"'
        ]
        for cmd in commands:
                try:
                    process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    stdout, stderr = process.communicate()
                    if process.returncode == 0:
                         output_text += f"Command executed Successfully: {cmd}\n"
                    else:
                         output_text += f"Command Failed: {cmd}\n Error: {stderr.decode('utf-8')}\n"
                         
                except Exception as e:
                    output_text += f"Error executing: {cmd} {e}\n"

        for folder in [
        os.path.join(os.environ.get('windir'),'temp'),
        os.path.join(os.environ.get('windir'),'Prefetch'),
        os.path.join(os.environ.get('windir'),'system32','dllcache'),
        os.path.join(os.environ.get('SystemDrive'),'Temp'),
        os.environ.get('temp'),
        os.path.join(os.environ.get('USERPROFILE'),'Local Settings', 'History'),
        os.path.join(os.environ.get('USERPROFILE'),'Local Settings', 'Temporary Internet Files'),
        os.path.join(os.environ.get('USERPROFILE'),'Local Settings', 'Temp'),
        os.path.join(os.environ.get('USERPROFILE'),'Recent'),
        os.path.join(os.environ.get('USERPROFILE'),'Cookies')]:
           self.total_deleted_files += get_file_count(folder)
        self.output_text.insertPlainText(output_text)
        self.counter_label.setText(f"Files Deleted: {self.total_deleted_files}")
    def mousePressEvent(self, event):
         self.oldPos = event.globalPos()

    def mouseMoveEvent(self, event):
         delta = event.globalPos() - self.oldPos
         self.move(self.x() + delta.x(), self.y() + delta.y())
         self.oldPos = event.globalPos()


if __name__ == '__main__':
    if not is_admin():
       run_as_admin(sys.argv)
    else:
        app = QApplication(sys.argv)
        gui = CleanGUI()
        gui.show()
        sys.exit(app.exec_())
