import os
import sys
import re
import json
from PyQt5.QtWidgets import (QApplication, QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QTextEdit, QPushButton, QFrame, QMessageBox)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from utils import get_glyphs_json_path, get_glyphs_data, generate_glyphs_data

class StandaloneSVGManager(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("iMA Custom SVG Icon Manager")
        self.setMinimumWidth(520)
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet("QToolTip { background-color: #1e1e24; color: #ffffff; border: 1px solid rgba(231, 130, 132, 0.6); border-radius: 8px; padding: 6px 12px; }")
        self._drag_pos = None
        self.setup_ui()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self._drag_pos is not None:
            self.move(event.globalPos() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None

    def setup_ui(self):
        self.mf = QFrame(self)
        self.mf.setObjectName("addSvgFrame")
        self.mf.setStyleSheet("""
            #addSvgFrame { background-color: #121212; border: 1px solid #2a2a30; border-radius: 20px; } 
            QLabel { color: #ffffff; font-size: 13px; } 
            QLineEdit, QTextEdit { background-color: #2a2a30; border: 1px solid #45475a; border-radius: 12px; padding: 10px; color: #ffffff; font-size: 12px; }
            QLineEdit:focus, QTextEdit:focus { border: 1px solid #e78284; }
        """)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(self.mf)
        
        cl = QVBoxLayout(self.mf)
        cl.setContentsMargins(24, 24, 24, 24)
        cl.setSpacing(12)
        
        head_lay = QHBoxLayout()
        h = QLabel("Custom SVG Icon Manager")
        h.setStyleSheet("font-size: 18px; font-weight: bold; color: white;")
        head_lay.addWidget(h)
        head_lay.addStretch()
        
        close_btn = QPushButton("\uE711")
        close_btn.setFont(QFont('Segoe MDL2 Assets', 10))
        close_btn.setFixedSize(28, 28)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet("QPushButton { background: rgba(255,255,255,0.05); border: none; border-radius: 14px; color: #b0b0b0; } QPushButton:hover { background: rgba(231, 130, 132,0.2); color: #e78284; }")
        close_btn.clicked.connect(self.close)
        head_lay.addWidget(close_btn)
        cl.addLayout(head_lay)
        
        desc = QLabel("Dev Tool: Add new SVG vector paths directly into glyphs.json and compile glyphs_data.py.")
        desc.setStyleSheet("color: #888888; font-size: 11px;")
        desc.setWordWrap(True)
        cl.addWidget(desc)
        
        cl.addWidget(QLabel("Icon Title / Name:"))
        self.name_inp = QLineEdit()
        self.name_inp.setPlaceholderText("e.g. Valorant, Discord, Custom Logo")
        cl.addWidget(self.name_inp)

        cl.addWidget(QLabel("Search Keywords (comma-separated):"))
        self.kw_inp = QLineEdit()
        self.kw_inp.setPlaceholderText("e.g. game, riot, fps, shooter, play")
        cl.addWidget(self.kw_inp)

        cl.addWidget(QLabel("SVG Content or Path(s):"))
        self.svg_inp = QTextEdit()
        self.svg_inp.setPlaceholderText("Paste raw <svg>...</svg> code or d=\"...\" path string")
        self.svg_inp.setFixedHeight(120)
        cl.addWidget(self.svg_inp)

        btns = QHBoxLayout()
        cancel_btn = QPushButton("Close")
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setStyleSheet("QPushButton { background: #2a2a30; color: #ffffff; border-radius: 10px; padding: 9px 18px; font-weight: bold; } QPushButton:hover { background: #45475a; }")
        cancel_btn.clicked.connect(self.close)
        
        save_btn = QPushButton("Add & Save SVG")
        save_btn.setCursor(Qt.PointingHandCursor)
        save_btn.setStyleSheet("QPushButton { background: #e78284; color: #ffffff; border-radius: 10px; padding: 9px 18px; font-weight: bold; } QPushButton:hover { background: #ea999c; }")
        save_btn.clicked.connect(self.save_svg)
        
        btns.addStretch()
        btns.addWidget(cancel_btn)
        btns.addWidget(save_btn)
        cl.addLayout(btns)

    def save_svg(self):
        title = self.name_inp.text().strip()
        raw_svg = self.svg_inp.toPlainText().strip()
        if not title:
            QMessageBox.warning(self, "Validation Error", "Please provide an Icon Title / Name.")
            return
        if not raw_svg:
            QMessageBox.warning(self, "Validation Error", "Please provide SVG content or path d string.")
            return
        
        paths = re.findall(r'd=["\']([^"\']+)["\']', raw_svg, re.IGNORECASE)
        if not paths:
            if raw_svg.startswith("M") or raw_svg.startswith("m"):
                paths = [raw_svg]

        if not paths:
            QMessageBox.warning(self, "Parse Error", "Could not extract valid SVG path data (d attribute) from input.")
            return

        json_path = get_glyphs_json_path()
        glyphs = get_glyphs_data() or {}

        clean_name = title.lower().replace(" ", "_")
        key = f"custom_{clean_name}"
        
        extra_keywords = [kw.strip().lower() for kw in self.kw_inp.text().split(',') if kw.strip()]
        base_keywords = [title.lower(), 'custom', 'svg']
        combined_keywords = list(dict.fromkeys(base_keywords + extra_keywords))

        glyphs[key] = {
            'name': title.lower(),
            'font': 'svg',
            'paths': paths,
            'keywords': combined_keywords
        }

        try:
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(glyphs, f, ensure_ascii=False, indent=2)
            try:
                generate_glyphs_data()
            except Exception as e:
                print("Could not update glyphs_data.py:", e)
            
            QMessageBox.information(self, "Success", f"Icon '{title}' added successfully as '{key}'!\nglyphs.json and glyphs_data.py updated.")
            self.name_inp.clear()
            self.kw_inp.clear()
            self.svg_inp.clear()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save SVG: {str(e)}")

def main():
    app = QApplication(sys.argv)
    dlg = StandaloneSVGManager()
    dlg.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
