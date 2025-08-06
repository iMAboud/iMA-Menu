import sys
import os
import shutil
import subprocess
import winshell
import pythoncom
import time
import win32gui
import win32con
import ctypes
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QFileDialog, QProgressBar, QGraphicsDropShadowEffect, QLineEdit, QSizePolicy, QCheckBox, QStyle, QGraphicsOpacityEffect
)
from PyQt5.QtGui import QColor, QPixmap, QFont, QIcon, QPainter, QPainterPath, QMouseEvent, QPen
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QRectF, QPoint, QPropertyAnimation, QEasingCurve, QUrl, QSize

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

class InstallerThread(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(bool, str)

    def __init__(self, source_dir, install_dir, add_to_desktop, add_to_start_menu):
        super().__init__()
        self.source_dir = source_dir
        self.install_dir = install_dir
        self.add_to_desktop = add_to_desktop
        self.add_to_start_menu = add_to_start_menu
        self.last_percentage = 0

    def _should_overwrite(self, file_path, install_dir):
        rel_path = os.path.relpath(file_path, install_dir).replace('\\', '/')
        files_to_overwrite = [
            'launcher/launcher.exe',
            'imports/file-manage.nss',
            'imports/image.nss',
            'imports/taskbar.nss'
        ]
        return rel_path in files_to_overwrite

    def run(self):
        pythoncom.CoInitialize()
        try:
            if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
                actual_source_dir = os.path.join(sys._MEIPASS, 'iMA Menu')
            else:
                actual_source_dir = os.path.abspath(self.source_dir)

            self.progress.emit(5)
            self.msleep(100)

            if os.path.exists(self.install_dir):
                self.progress.emit(10)
                self.msleep(100)

                shell_exe_path_in_target = os.path.normpath(os.path.join(self.install_dir, 'shell.exe'))
                if os.path.exists(shell_exe_path_in_target):
                    self.progress.emit(15)
                    self.msleep(100)
                    try:
                        subprocess.run('start /wait "" "shell.exe" -unregister', check=True, shell=True, cwd=self.install_dir, capture_output=True, text=True)
                        self.progress.emit(20)
                        self.msleep(100)
                    except subprocess.CalledProcessError as e:
                        print(f"Unregister failed: {e.cmd} stdout: {e.stdout} stderr: {e.stderr}")
                    except Exception as e:
                        print(f"Error during unregister: {e}")

            self.progress.emit(25)
            self.msleep(100)

            os.makedirs(self.install_dir, exist_ok=True)
            shutil.copy2(os.path.join(sys._MEIPASS, 'ima.ico'), os.path.join(self.install_dir, 'ima.ico'))

            total_files = sum([len(files) for r, d, files in os.walk(actual_source_dir)])
            copied_files = 0

            for root, dirs, files in os.walk(actual_source_dir):
                dest_root = os.path.join(self.install_dir, os.path.relpath(root, actual_source_dir))
                os.makedirs(dest_root, exist_ok=True)

                for file in files:
                    source_path = os.path.join(root, file)
                    dest_path = os.path.join(dest_root, file)

                    if not os.path.exists(dest_path) or self._should_overwrite(dest_path, self.install_dir):
                        shutil.copy2(source_path, dest_path)

                    copied_files += 1
                    progress_percentage = int(25 + (copied_files / total_files) * 45) if total_files > 0 else 25
                    if progress_percentage > self.last_percentage:
                        self.progress.emit(progress_percentage)
                        self.last_percentage = progress_percentage
                        self.msleep(1)  # Yield to keep UI responsive

            self.progress.emit(70)
            self.msleep(100)

            subprocess.run('start /wait "" "shell.exe" -register', check=True, shell=True, cwd=self.install_dir, capture_output=True, text=True)
            self.progress.emit(85)
            self.msleep(100)

            if self.add_to_desktop or self.add_to_start_menu:
                launcher_path = os.path.join(self.install_dir, 'launcher', 'launcher.exe')
                icon_path = os.path.join(self.install_dir, 'ima.ico')

                # Set the working directory to the main install folder, not the launcher's subfolder.
                if self.add_to_desktop:
                    desktop = winshell.desktop()
                    shortcut_path = os.path.join(desktop, "iMA Menu.lnk")
                    with winshell.shortcut(shortcut_path) as shortcut:
                        shortcut.path = launcher_path
                        shortcut.working_directory = self.install_dir
                        shortcut.description = "iMA Menu Launcher"
                        shortcut.icon_location = (icon_path, 0)

                if self.add_to_start_menu:
                    start_menu = winshell.start_menu()
                    shortcut_path = os.path.join(start_menu, "Programs", "iMA Menu.lnk")
                    with winshell.shortcut(shortcut_path) as shortcut:
                        shortcut.path = launcher_path
                        shortcut.working_directory = self.install_dir
                        shortcut.description = "iMA Menu Launcher"
                        shortcut.icon_location = (icon_path, 0)

            subprocess.run('start /wait "" "shell.exe" -restart', check=True, shell=True, cwd=self.install_dir, capture_output=True, text=True)
            self.progress.emit(100)
            self.msleep(100)

            self.finished.emit(True, "Installation successful!")
        except subprocess.CalledProcessError as e:
            self.finished.emit(False, f"Command failed: {e.cmd} with exit code {e.returncode}. Stdout: {e.stdout}. Stderr: {e.stderr}")
        except Exception as e:
            self.finished.emit(False, f"Installation failed: {e}")
        finally:
            pythoncom.CoUninitialize()

class CustomCheckBox(QCheckBox):
    def __init__(self, text):
        super().__init__(text)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(250, 25)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        indicator_size = 18
        indicator_x = 0
        indicator_y = (self.height() - indicator_size) / 2
        indicator_rect = QRectF(indicator_x, indicator_y, indicator_size, indicator_size)

        painter.setBrush(QColor("#5b6078"))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(indicator_rect)

        inner_rect = indicator_rect.adjusted(1, 1, -1, -1)
        painter.setBrush(QColor("#494d64"))
        painter.drawEllipse(inner_rect)

        if self.isChecked():
            checked_rect = indicator_rect.adjusted(4, 4, -4, -4)
            painter.setBrush(QColor("#94e2d5"))
            painter.drawEllipse(checked_rect)

        painter.setPen(QColor("#ffffff"))
        painter.setFont(QFont('Open Sans', 10))
        text_rect = self.rect().adjusted(indicator_size + 10, 0, 0, 0)
        painter.drawText(text_rect, Qt.AlignVCenter, self.text())

class CustomTitleBar(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent_window = parent
        self.setFixedHeight(42)
        self.setAttribute(Qt.WA_StyledBackground)
        self.setObjectName("titleBar")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 5, 0)
        layout.setSpacing(5)

        self.icon_label = QLabel()
        self.icon_label.setPixmap(QPixmap(resource_path('ima.ico')).scaled(24, 24, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        layout.addWidget(self.icon_label)

        self.title_label = QLabel("iMA Menu Installer")
        self.title_label.setObjectName("titleLabel")
        layout.addWidget(self.title_label)

        layout.addStretch(1)

        self.minimize_button = QPushButton()
        self.minimize_button.setIcon(QIcon(resource_path('assets/min.png')))
        self.minimize_button.setIconSize(QSize(16, 16))
        self.minimize_button.setFixedSize(30, 30)
        self.minimize_button.setObjectName("minimizeButton")
        self.minimize_button.clicked.connect(self.parent_window.showMinimized)
        layout.addWidget(self.minimize_button)

        self.close_button = QPushButton()
        self.close_button.setIcon(QIcon(resource_path('assets/x.png')))
        self.close_button.setIconSize(QSize(16, 16))
        self.close_button.setFixedSize(30, 30)
        self.close_button.setObjectName("closeButton")
        self.close_button.clicked.connect(self.parent_window.close)
        layout.addWidget(self.close_button)

        self.start_pos = None
        self.window_start_pos = None

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self.start_pos = event.globalPos()
            self.window_start_pos = self.parent_window.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.start_pos:
            delta = event.globalPos() - self.start_pos
            self.parent_window.move(self.window_start_pos + delta)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        self.start_pos = None
        self.window_start_pos = None
        super().mouseReleaseEvent(event)

class InstallerWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("iMA Menu Installer")
        self.setWindowIcon(QIcon(resource_path('ima.ico')))
        self.setFixedSize(550, 450)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.installation_successful = False

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.title_bar = CustomTitleBar(self)
        main_layout.addWidget(self.title_bar)

        content_widget = QWidget()
        content_widget.setObjectName("contentArea")
        main_layout.addWidget(content_widget)

        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(30, 20, 30, 30)
        content_layout.setSpacing(15)

        top_section_layout = QHBoxLayout()
        top_section_layout.setAlignment(Qt.AlignCenter)
        top_section_layout.setSpacing(10)

        self.icon_label = QLabel()
        pixmap = QPixmap(resource_path('ima.ico')).scaled(128, 128, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.icon_label.setPixmap(pixmap)
        top_section_layout.addWidget(self.icon_label)

        self.title_text_label = QLabel("menu")
        self.title_text_label.setFont(QFont('Montserrat', 32, QFont.Bold))
        top_section_layout.addWidget(self.title_text_label)

        content_layout.addLayout(top_section_layout)

        path_input_layout = QHBoxLayout()
        self.path_label_prefix = QLabel("Install to:")
        self.path_label_prefix.setFont(QFont('Open Sans', 12))
        path_input_layout.addWidget(self.path_label_prefix)

        self.path_input = QLineEdit()
        default_install_dir = os.path.join(os.environ.get('ProgramFiles', r'C:\Program Files'), 'iMA Menu')
        self.install_path = os.path.normpath(default_install_dir)
        self.path_input.setText(self.install_path)
        self.path_input.setReadOnly(True)
        self.path_input.setObjectName("pathInput")
        path_input_layout.addWidget(self.path_input)

        self.browse_button = QPushButton("Browse...")
        self.browse_button.setFixedSize(100, 35)
        self.browse_button.clicked.connect(self.browse_path)
        self.browse_button.setObjectName("browseButton")
        path_input_layout.addWidget(self.browse_button)
        content_layout.addLayout(path_input_layout)

        content_layout.addStretch(1)

        self.desktop_shortcut_checkbox = CustomCheckBox("Add Launcher to Desktop")
        self.desktop_shortcut_checkbox.setChecked(True)
        content_layout.addWidget(self.desktop_shortcut_checkbox)

        self.start_menu_shortcut_checkbox = CustomCheckBox("Add Launcher to Start Menu")
        self.start_menu_shortcut_checkbox.setChecked(True)
        content_layout.addWidget(self.start_menu_shortcut_checkbox)

        self.launch_on_close_checkbox = CustomCheckBox("Launch iMA Menu")
        self.launch_on_close_checkbox.setChecked(True)
        self.launch_on_close_checkbox.setVisible(False)
        content_layout.addWidget(self.launch_on_close_checkbox)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setTextVisible(True)
        self.progress_opacity_effect = QGraphicsOpacityEffect(self.progress_bar)
        self.progress_bar.setGraphicsEffect(self.progress_opacity_effect)
        self.progress_opacity_effect.setOpacity(0.0)
        content_layout.addWidget(self.progress_bar)

        self.status_label = QLabel("")
        self.status_label.setFont(QFont('Open Sans', 12))
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_opacity_effect = QGraphicsOpacityEffect(self.status_label)
        self.status_label.setGraphicsEffect(self.status_opacity_effect)
        self.status_opacity_effect.setOpacity(0.0)
        content_layout.addWidget(self.status_label)

        bottom_buttons_layout = QHBoxLayout()
        bottom_buttons_layout.addStretch()

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setFixedSize(120, 40)
        self.cancel_button.clicked.connect(self.close)
        self.cancel_button.setObjectName("cancelButton")
        bottom_buttons_layout.addWidget(self.cancel_button)

        self.install_button = QPushButton("Install")
        self.install_button.setFixedSize(120, 40)
        self.install_button.clicked.connect(self.install)
        self.install_button.setObjectName("installButton")
        bottom_buttons_layout.addWidget(self.install_button)
        bottom_buttons_layout.addStretch()
        content_layout.addLayout(bottom_buttons_layout)

        self.apply_shadow(self.title_text_label)
        self.apply_shadow(self.path_input)
        self.apply_shadow(self.browse_button)
        self.apply_shadow(self.install_button)
        self.apply_shadow(self.cancel_button)
        self.apply_shadow(self.icon_label)
        self.apply_shadow(self.desktop_shortcut_checkbox)
        self.apply_shadow(self.start_menu_shortcut_checkbox)

        self.center_on_screen()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor("#1e2030"))
        painter.setPen(Qt.NoPen)
        rect = self.rect()
        painter.drawRoundedRect(rect, 15, 15)

    def apply_shadow(self, widget):
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 160))
        shadow.setOffset(5, 5)
        widget.setGraphicsEffect(shadow)

    def browse_path(self):
        current_path = self.path_input.text()
        if not os.path.isdir(current_path):
            current_path = os.environ.get('ProgramFiles', 'C:\\Program Files')

        path = QFileDialog.getExistingDirectory(self, "Select Installation Directory", current_path)
        if path:
            if os.path.basename(path).lower() != "ima menu":
                self.install_path = os.path.normpath(os.path.join(path, "iMA Menu"))
            else:
                self.install_path = os.path.normpath(path)
            self.path_input.setText(self.install_path)

    def install(self):
        self.install_button.setEnabled(False)
        self.browse_button.setEnabled(False)
        self.cancel_button.setEnabled(False)
        self.desktop_shortcut_checkbox.setVisible(False)
        self.start_menu_shortcut_checkbox.setVisible(False)

        self.progress_bar.setVisible(True)
        self.status_label.setVisible(True)

        self.progress_anim = QPropertyAnimation(self.progress_opacity_effect, b"opacity")
        self.progress_anim.setDuration(300)
        self.progress_anim.setStartValue(0.0)
        self.progress_anim.setEndValue(1.0)
        self.progress_anim.setEasingCurve(QEasingCurve.InOutQuad)
        self.progress_anim.start()

        self.status_anim = QPropertyAnimation(self.status_opacity_effect, b"opacity")
        self.status_anim.setDuration(300)
        self.status_anim.setStartValue(0.0)
        self.status_anim.setEndValue(1.0)
        self.status_anim.setEasingCurve(QEasingCurve.InOutQuad)
        self.status_anim.start()

        self.status_label.setText("Starting installation...")
        self.progress_bar.setValue(0)

        source_dir_relative = os.path.join('..', 'iMA Menu')

        self.thread = InstallerThread(
            source_dir_relative,
            self.install_path,
            self.desktop_shortcut_checkbox.isChecked(),
            self.start_menu_shortcut_checkbox.isChecked()
        )
        self.thread.progress.connect(self.progress_bar.setValue)
        self.thread.finished.connect(self.on_installation_finished)
        self.thread.start()

    def on_installation_finished(self, success, message):
        self.status_label.setText(message)
        self.installation_successful = success
        self.install_button.setEnabled(True)
        self.browse_button.setEnabled(True)
        self.cancel_button.setEnabled(True)
        if success:
            self.install_button.setText("Finished")
            self.install_button.setEnabled(False)
            self.cancel_button.setText("Close")
            self.launch_on_close_checkbox.setVisible(True)

    def closeEvent(self, event):
        if self.installation_successful and self.launch_on_close_checkbox.isChecked():
            launcher_path = os.path.join(self.install_path, 'launcher', 'launcher.exe')
            if os.path.exists(launcher_path):
                try:
                    os.startfile(launcher_path)
                except Exception as e:
                    print(f"Failed to launch {launcher_path}: {e}")
        super().closeEvent(event)

    def center_on_screen(self):
        screen_geometry = QApplication.desktop().screenGeometry()
        x = (screen_geometry.width() - self.width()) // 2
        y = (screen_geometry.height() - self.height()) // 2
        self.move(x, y)

if __name__ == '__main__':
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)

    app = QApplication(sys.argv)
    try:
        with open(resource_path('style.css')) as f:
            app.setStyleSheet(f.read())
    except FileNotFoundError:
        print("Warning: style.css not found. Using default styles.")

    def is_admin():
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
            return False

    if is_admin():
        window = InstallerWindow()
        window.show()
        sys.exit(app.exec_())
    else:
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
        sys.exit(0)
