import sys
import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QScrollArea, QFrame, QButtonGroup, QGridLayout, QPushButton, QGraphicsDropShadowEffect
)
from PyQt5.QtGui import QPixmap, QIcon, QCursor, QColor
from PyQt5.QtCore import Qt, QSize, pyqtSignal



class ThemeSwitcherWidget(QWidget):
    theme_selected = pyqtSignal(str)

    def __init__(self, theme_dir, theme_nss_path):
        super().__init__()
        self.theme_dir = theme_dir
        self.theme_nss_path = theme_nss_path
        self.selected_theme = None
        self.selected_button = None

        self.theme_files = self._find_theme_files()
        self._setup_ui()

    def _find_theme_files(self):
        theme_files = []
        if os.path.exists(self.theme_dir):
            for filename in os.listdir(self.theme_dir):
                if filename.endswith(".nss"):
                    theme_files.append(filename)
        return theme_files

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setObjectName("themeSwitcherScrollArea")
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        grid_widget = QWidget()
        grid_widget.setObjectName("themeSwitcherGrid")
        grid_layout = QGridLayout(grid_widget)
        grid_layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        self.button_group = QButtonGroup()
        self.button_group.setExclusive(True)

        row, col = 0, 0
        for i, theme_file in enumerate(self.theme_files):
            theme_name = os.path.splitext(theme_file)[0]
            self._add_theme_option(grid_layout, theme_name, row, col, i)
            col += 1
            if col > 4:
                col = 0
                row += 1

        scroll_area.setWidget(grid_widget)
        main_layout.addWidget(scroll_area)

    def _add_theme_option(self, layout, theme_name, row, col, button_id):
        frame = QFrame()
        frame.setObjectName("themeOptionFrame")
        frame.setProperty("selected", False)
        frame.setCursor(QCursor(Qt.PointingHandCursor))
        shadow = QGraphicsDropShadowEffect(blurRadius=15, xOffset=5, yOffset=5)
        shadow.setColor(QColor(0, 0, 0, 160))
        frame.setGraphicsEffect(shadow)

        frame_layout = QVBoxLayout(frame)
        frame_layout.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        frame_layout.setContentsMargins(5, 5, 5, 5)

        image_path = os.path.join(self.theme_dir, f"{theme_name}.png")
        if os.path.exists(image_path):
            pixmap = QPixmap(image_path)
            target_width = 128
            target_height = 128
            pixmap = pixmap.scaled(target_width, target_height, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        else:
            pixmap = QPixmap(128, 128)
            pixmap.fill(Qt.gray)

        image_label = QLabel()
        image_label.setPixmap(pixmap)
        image_label.setAlignment(Qt.AlignCenter)
        frame_layout.addWidget(image_label)

        theme_button = QPushButton(theme_name.replace("theme_", "").replace("_", " ").title())
        theme_button.setObjectName("themeOptionButton")
        theme_button.setCursor(QCursor(Qt.PointingHandCursor))
        theme_button.setCheckable(True)
        theme_button.clicked.connect(lambda checked, name=theme_name, button=frame: self._theme_selected(name, button))
        self.button_group.addButton(theme_button)
        self.button_group.setId(theme_button, button_id)

        frame_layout.addWidget(theme_button)
        frame.mousePressEvent = lambda event, name=theme_name, button=frame: self._theme_selected(name, button)

        layout.addWidget(frame, row, col)
        self.update_frame_style(frame)

    def update_frame_style(self, frame):
        if frame.property("selected"):
            frame.setObjectName("themeOptionFrameSelected")
        else:
            frame.setObjectName("themeOptionFrame")
        
        frame.style().unpolish(frame)
        frame.style().polish(frame)

    def _theme_selected(self, theme_name, frame):
        if self.selected_button is not None:
            self.selected_button.setProperty("selected", False)
            self.update_frame_style(self.selected_button)

        self.selected_theme = theme_name
        self.selected_button = frame
        self.selected_button.setProperty("selected", True)
        self.update_frame_style(self.selected_button)
        self._apply_theme(theme_name)
        self.theme_selected.emit(theme_name)

    def _apply_theme(self, theme_name):
        source_path = os.path.join(self.theme_dir, f"{theme_name}.nss")
        if os.path.exists(source_path):
            try:
                with open(source_path, 'r') as source_file:
                    theme_content = source_file.read()
                with open(self.theme_nss_path, 'w') as dest_file:
                    dest_file.write(theme_content)
                print(f"Theme applied: {theme_name}")
            except Exception as e:
                print(f"Error applying theme: {e}")
        else:
            print(f"Theme file not found: {theme_name}")