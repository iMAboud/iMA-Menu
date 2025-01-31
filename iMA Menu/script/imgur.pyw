import sys
import os
import re
import ctypes
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QPixmap, QImage
import requests
from PIL import Image, UnidentifiedImageError
from io import BytesIO
import pyperclip
import subprocess


    
class SplashScreen(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Loading...")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet("QWidget { background-color: #2b2b2b; border-radius: 15px; color: #f0f0f0; font-family: 'Arial'; }")
        self.layout = QVBoxLayout(self)
        self.layout.setAlignment(Qt.AlignCenter)
        loading_label = QLabel("Loading...", self)
        loading_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(loading_label)
        self.center_window()

    def center_window(self):
        qr = self.frameGeometry()
        cp = QApplication.desktop().screenGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def close_self(self):
        self.close()

    def show_and_close(self, timeout=300):
        self.show()
        QTimer.singleShot(timeout, self.close_self)
        QTimer.singleShot(timeout + 10, self.release)

    def release(self):
         self.deleteLater() # Clean up the splash screen after the timer.

class ImgurUploader(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Imgur Uploader")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet("QWidget { background-color: #2b2b2b; border-radius: 15px; color: #f0f0f0; font-family: 'Arial'; }")

        self.layout = QVBoxLayout(self)
        self.layout.setAlignment(Qt.AlignCenter)

        self.preview_label = QLabel(self)
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setFixedSize(150, 150)
        self.layout.addWidget(self.preview_label)
        self.preview_label.setStyleSheet("border: 2px solid #555;")

        self.upload_status_label = QLabel(self)
        self.upload_status_label.setAlignment(Qt.AlignCenter)
        self.upload_status_label.hide()
        self.layout.addWidget(self.upload_status_label)
        self.show()

        self.upload_worker = ImageUploadWorker()
        self.upload_worker.finished_signal.connect(self.handle_upload_complete)

        self.image_path = None
        QTimer.singleShot(10, self.start_upload)  # Start upload logic after initial window display
        self.center_window()


    def center_window(self):
        qr = self.frameGeometry()
        cp = QApplication.desktop().screenGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def start_upload(self):
        clipboard_text = pyperclip.paste()
        self.image_path = clipboard_text.strip().strip('"')

        if not self.image_path or not os.path.exists(self.image_path):
             self.close()
             return

        QTimer.singleShot(10, self.load_preview_image)
        self.upload_worker.set_image_path(self.image_path)
        self.upload_worker.start()

    def load_preview_image(self):
        try:
            image = Image.open(self.image_path)
            image.thumbnail((150, 150))
            img_byte_array = BytesIO()
            image.save(img_byte_array, format="PNG")
            qimage = QImage.fromData(img_byte_array.getvalue())
            pixmap = QPixmap.fromImage(qimage)
            self.preview_label.setPixmap(pixmap)
        except (UnidentifiedImageError, Exception):
            self.close()

    def handle_upload_complete(self, link):
        if link:
            pyperclip.copy(link)
            self.show_upload_status()
        else:
            self.close()

    def show_upload_status(self):
        self.upload_status_label.setText("✔")
        self.upload_status_label.setStyleSheet("QLabel { background-color: #4CAF50; color: white; border-radius: 10px; padding: 5px 10px; font-size: 20px; }")
        self.upload_status_label.show()
        QTimer.singleShot(1000, self.close)

class ImageUploadWorker(QThread):
    finished_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.image_path = None
        self.client_id = "07d8ebac38608e9"

    def set_image_path(self, image_path):
        self.image_path = image_path

    def run(self):
        if not self.image_path:
            self.finished_signal.emit(None)
            return

        try:
            with open(self.image_path, 'rb') as f:
                response = requests.post(
                    "https://api.imgur.com/3/image",
                    headers={"Authorization": f"Client-ID {self.client_id}"},
                    files={"image": f}
                )

            response.raise_for_status()
            data = response.json()

            if data.get('success') and 'link' in data.get('data', {}):
                match = re.search(r'https://i\.imgur\.com/([^/]+)', data['data']['link'])
                direct_link = f"https://i.imgur.com/{match.group(1)}" if match else None
                self.finished_signal.emit(direct_link)
            else:
                self.finished_signal.emit(None)

        except (requests.exceptions.RequestException, Exception):
            self.finished_signal.emit(None)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    splash = SplashScreen()
    splash.show_and_close()
    uploader = ImgurUploader()
    sys.exit(app.exec_())
