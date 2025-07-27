import sys
import os
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QGraphicsOpacityEffect
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import (
    Qt, QPropertyAnimation, QRect, QParallelAnimationGroup,
    pyqtSignal, QThread, QTimer, QEasingCurve
)
from PIL import Image

class ResizeWorker(QThread):
    finished = pyqtSignal(str)

    def __init__(self, file_path, quality, optimize, reduce_colors, dither, prefix):
        super().__init__()
        self.file_path = file_path
        self.quality = quality
        self.optimize = optimize
        self.reduce_colors = reduce_colors
        self.dither = dither
        self.prefix = prefix

    def run(self):
        try:
            input_path = self.file_path.strip().strip('\'"')
            supported_formats = [".png", ".jpg", ".jpeg", ".bmp", ".ico"]
            
            if not os.path.exists(input_path):
                self.finished.emit(self.file_path)
                return
            
            if not input_path.lower().endswith(tuple(supported_formats)):
                self.finished.emit(self.file_path)
                return

            directory = os.path.dirname(input_path)
            basename = os.path.basename(input_path)
            name, ext = os.path.splitext(basename)
            output_path = os.path.join(directory, f"{self.prefix}{name}{ext}")

            with Image.open(input_path) as img:
                if img.mode != 'RGBA':
                    img = img.convert('RGBA')
                
                if self.reduce_colors and ext.lower() == ".png":
                    img = img.quantize(colors=256, method=Image.Quantize.FASTOCTREE, dither=self.dither)

                if ext.lower() in [".jpg", ".jpeg"]:
                    img.save(output_path, optimize=self.optimize, quality=self.quality)
                else:
                    img.save(output_path, optimize=self.optimize)

        except Exception:
            pass
        finally:
            self.finished.emit(self.file_path)


class AnimationWindow(QWidget):
    def __init__(self, file_paths, quality, optimize, reduce_colors, dither, prefix):
        super().__init__()
        self.all_file_paths = list(file_paths)
        self.pending_file_paths = list(file_paths)
        self.active_workers = []
        self.quality = quality
        self.optimize = optimize
        self.reduce_colors = reduce_colors
        self.dither = dither
        self.prefix = prefix
        self.initUI()
        self.start_processing()

    def initUI(self):
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        screen_geo = QApplication.desktop().screenGeometry()
        self.setGeometry(screen_geo.width() // 2 - 150, screen_geo.height() // 2 - 150, 300, 300)
        
        self.hide() 
        self.total_processed_count = 0

    def start_processing(self):
        if not self.pending_file_paths:
            QTimer.singleShot(0, QApplication.instance().quit)
            return

        self.process_next_image()

    def process_next_image(self):
        if not self.pending_file_paths:
            if not self.active_workers:
                QTimer.singleShot(500, QApplication.instance().quit)
            return

        file_path = self.pending_file_paths.pop(0)

        try:
            pixmap = QPixmap(file_path)
            if not pixmap.isNull():
                card = QLabel(self)
                card.setPixmap(pixmap.scaled(128, 128, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                card.adjustSize()
                card.move(self.width() // 2 - card.width() // 2, self.height() // 2 - card.height() // 2)
                card.show()
                if self.isHidden():
                    self.show()
                self.animate_card(card)
            else:
                self.start_worker_for_path(file_path)
                self.process_next_image()
                return
        except Exception:
            self.start_worker_for_path(file_path)
            self.process_next_image()
            return

        self.start_worker_for_path(file_path)


    def start_worker_for_path(self, file_path):
        worker = ResizeWorker(file_path, self.quality, self.optimize, self.reduce_colors, self.dither, self.prefix)
        worker.finished.connect(self.on_worker_finished)
        self.active_workers.append(worker)
        worker.start()

    def on_worker_finished(self, file_path):
        self.total_processed_count += 1
        for worker in list(self.active_workers):
            if worker.file_path == file_path:
                self.active_workers.remove(worker)
                worker.quit()
                worker.wait()
                break
        
        if self.total_processed_count == len(self.all_file_paths):
            QTimer.singleShot(999, QApplication.instance().quit)


    def animate_card(self, card):
        anim_pos = QPropertyAnimation(card, b"geometry")
        anim_pos.setDuration(500)
        start_rect = card.geometry()
        end_rect = QRect(self.width(), start_rect.y(), start_rect.width(), start_rect.height())
        anim_pos.setStartValue(start_rect)
        anim_pos.setEndValue(end_rect)
        anim_pos.setEasingCurve(QEasingCurve.InQuad)

        opacity_effect = QGraphicsOpacityEffect(card)
        card.setGraphicsEffect(opacity_effect)
        anim_opacity = QPropertyAnimation(opacity_effect, b"opacity")
        anim_opacity.setDuration(500)
        anim_opacity.setStartValue(1.0)
        anim_opacity.setEndValue(0.0)
        anim_opacity.setEasingCurve(QEasingCurve.InQuad)

        self.anim_group = QParallelAnimationGroup()
        self.anim_group.addAnimation(anim_pos)
        self.anim_group.addAnimation(anim_opacity)
        self.anim_group.finished.connect(card.deleteLater)
        self.anim_group.finished.connect(self.process_next_image) 
        self.anim_group.start()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        output_prefix = "resized_"
        compression_quality = 70
        enable_quantization = True
        dithering_strength = 0.5

        app = QApplication(sys.argv)
        cleaned_paths = [p.strip().strip('\'"') for p in sys.argv[1:]]
        
        window = AnimationWindow(
            file_paths=[p for p in cleaned_paths if os.path.exists(p)],
            quality=compression_quality,
            optimize=True,
            reduce_colors=enable_quantization,
            dither=dithering_strength,
            prefix=output_prefix
        )
        sys.exit(app.exec_())
    else:
        print("Usage: python script.py <image_path_1> [<image_path_2> ...]")
        print("Please provide one or more image paths as arguments.")
