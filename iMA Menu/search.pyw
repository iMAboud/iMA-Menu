import sys
import os
import subprocess
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit,
    QListWidget, QListWidgetItem, QLabel, QProgressBar, QDesktopWidget,
    QScrollBar
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QColor, QPalette, QFont, QBrush, QIcon
from pathlib import Path

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPT_DIR = os.path.dirname(BASE_DIR)


class SearchWorker(QThread):
    result_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int)
    finished_signal = pyqtSignal()

    def __init__(self, search_term, drives_to_search):
        super().__init__()
        self.search_term = search_term.lower()
        self.drives_to_search = drives_to_search
        self.total_files = 0
        self.searched_files = 0

    def run(self):
        self.total_files = self._count_files()
        if self.total_files == 0:
            self.progress_signal.emit(100)
            self.finished_signal.emit()
            return

        for drive in self.drives_to_search:
            for root, dirs, files in os.walk(drive, followlinks=True):
                for file in files:
                    if self.search_term in file.lower():
                        file_path = os.path.join(root, file)
                        self.result_signal.emit(file_path)

                    self.searched_files += 1
                    progress = int((self.searched_files / self.total_files) * 100)
                    self.progress_signal.emit(progress)
        self.finished_signal.emit()

    def _count_files(self):
        count = 0
        for drive in self.drives_to_search:
            for root, dirs, files in os.walk(drive, followlinks=True):
                count += len(files)
        return count


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
            QScrollBar:horizontal {
                background-color: transparent;
                height: 10px;
                margin: 0px 0px 0px 0px;
            }

            QScrollBar::handle:horizontal {
                background-color: rgba(80, 80, 80, 150);
                min-width: 20px;
                border-radius: 5px;
            }

            QScrollBar::add-line:horizontal,
            QScrollBar::sub-line:horizontal {
                background: none;
            }
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal{
                background: none;
            }

        """)


class SearchApp(QWidget):
    def __init__(self):
        super().__init__()

        self.search_active = False
        self.dots = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_search_dots)
        self.initUI()
        self.centerWindow()

    def initUI(self):
        self.setWindowTitle('iMSearch')
        self.setGeometry(100, 100, 800, 600)
        self.setStyleSheet(self.getStyle())

        ICON_PATH = os.path.join(SCRIPT_DIR, "icons", "search.ico")
        self.setWindowIcon(QIcon(ICON_PATH))

        main_layout = QVBoxLayout()
        input_layout = QHBoxLayout()

        self.search_input = QLineEdit(self)
        self.search_input.setPlaceholderText("Search for...")
        self.search_button = QPushButton('Search', self)
        self.results_list = QListWidget(self)
        self.results_list.setSelectionMode(QListWidget.SingleSelection)
        self.results_list.setSpacing(5)

        # Set custom scrollbars
        self.results_list.setVerticalScrollBar(ModernScrollBar(self.results_list))
        self.results_list.setHorizontalScrollBar(ModernScrollBar(self.results_list))


        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #555;
                border-radius: 9px;
                height: 20px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #5C5CFF;
                border-radius: 9px;
            }
        """)

        input_layout.addWidget(QLabel('Search:'))
        input_layout.addWidget(self.search_input)
        input_layout.addWidget(self.search_button)

        main_layout.addLayout(input_layout)
        main_layout.addWidget(self.progress_bar)
        main_layout.addWidget(self.results_list)

        self.setLayout(main_layout)

        self.search_button.clicked.connect(self.performSearch)
        self.search_input.returnPressed.connect(self.performSearch)
        self.results_list.itemClicked.connect(self.openFileLocation)

    def getStyle(self):
        return """
            QWidget {
                background-color: #2E2E2E;
                color: white;
                border-radius: 10px;
                font-family: Arial, sans-serif;
                font-size: 14px;
            }
            QLineEdit {
                background-color: #444;
                border: 1px solid #555;
                border-radius: 9px;
                padding: 5px;
                color: white;
            }
            QPushButton {
                background-color: #5C5CFF;
                border: 1px solid #4D4DCC;
                border-radius: 10px;
                padding: 10px;
                color: white;
            }
            QLabel {
                color: #B0B0B0;
                padding-right: 10px;
            }
           
            QListWidget{
                border: none;
            }
           QListWidget::item {
                background-color: rgba(80, 80, 80, 150); 
                border-radius: 8px; 
                padding: 5px; 
                margin-bottom: 4px;  
            }
            QListWidget::item:selected {
                background-color: rgba(100, 100, 100, 200); 
            }

        """

    def centerWindow(self):
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def update_search_dots(self):
        self.dots = (self.dots + 1) % 4
        self.search_button.setText(f'Searching{"." * self.dots}')

    def performSearch(self):
        if self.search_active:
            return

        search_term = self.search_input.text().strip()
        if not search_term:
            self.results_list.clear()
            self.results_list.addItem("Search for a file or folder.")
            return

        self.results_list.clear()
        self.search_active = True
        self.progress_bar.setValue(0)

        self.timer.start(500)
        self.search_button.setStyleSheet("background-color: grey;")
        self.update_search_dots()

        drives_to_search = ['C:\\', 'D:\\']

        self.worker = SearchWorker(search_term, drives_to_search)
        self.worker.result_signal.connect(self.addResult)
        self.worker.progress_signal.connect(self.updateProgress)
        self.worker.finished_signal.connect(self.searchFinished)
        self.worker.start()

    def addResult(self, file_path):
        item = QListWidgetItem(f"{Path(file_path).name}\n{file_path}")
        item.setData(Qt.UserRole, file_path)
        self.results_list.addItem(item)

    def updateProgress(self, value):
        self.progress_bar.setValue(value)

    def searchFinished(self):
        self.search_active = False
        self.timer.stop()
        self.search_button.setText("Search")
        self.search_button.setStyleSheet("")

    def openFileLocation(self, item):
        file_path = item.data(Qt.UserRole)
        if file_path:
            try:
                folder_path = os.path.dirname(file_path)
                subprocess.Popen(['explorer', '/select,', os.path.normpath(file_path)])
            except Exception as e:
                print(f"Error opening file location: {e}")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(45, 45, 45))
    palette.setColor(QPalette.WindowText, Qt.white)
    app.setPalette(palette)

    window = SearchApp()
    window.show()
    sys.exit(app.exec_())
