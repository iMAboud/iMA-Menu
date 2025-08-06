import PyInstaller.__main__
import os

if __name__ == '__main__':
    PyInstaller.__main__.run([
        'launcher.pyw',
        '--onefile',
        '--windowed',
        f'--icon={os.path.join("icons", "icon.png")}',
        '--name=launcher',
        f'--add-data=style.css;.',
        f'--add-data=icons;icons',
        f'--add-data={os.path.join("..", "imports")};imports',
        f'--add-data={os.path.join("..", "theme")};theme',
        '--hidden-import=modify_widget',
        '--hidden-import=theme_editor_widget',
        '--hidden-import=theme_switcher_widget',
        '--hidden-import=utils',
        '--exclude-module=PyQt5.QtWebEngineWidgets',
        '--exclude-module=PyQt5.QtMultimedia',
        '--exclude-module=PyQt5.QtSql',
        '--exclude-module=PyQt5.QtTest',
        '--exclude-module=PyQt5.QtXml',
        '--exclude-module=PyQt5.QtDesigner',
        '--exclude-module=PyQt5.QtPrintSupport',
        '--exclude-module=PyQt5.QtOpenGL',
        '--exclude-module=PyQt5.QtSvg',
        '--strip',
    ])