import PyInstaller.__main__
import os
import shutil
import sys

def build():
    try:
        from utils import generate_glyphs_data
        generate_glyphs_data()
    except Exception as error_message:
        print(f"Warning: Could not generate glyphs_data: {error_message}")

    if os.path.exists('dist'):
        shutil.rmtree('dist', ignore_errors=True)
    if os.path.exists('build'):
        shutil.rmtree('build', ignore_errors=True)

    base_args = [
        'launcher.pyw',
        '--onefile', 
        '--windowed',
        f'--icon={os.path.join("icons", "icon.ico")}',
        '--name=launcher',
        '--add-data=style.css;.',
        '--add-data=ima_updater.exe;.',
        '--add-data=shell.dll;.',
        '--add-data=shell.exe;.',
        '--add-data=icons;icons',
        '--add-data=fonts;fonts',
        '--add-data=cache/plugins.json;cache',
        '--hidden-import=unicodedata',
        '--hidden-import=idna',
        '--hidden-import=urllib3',
        '--hidden-import=certifi',
        '--hidden-import=charset_normalizer',
        '--hidden-import=requests',
        '--hidden-import=encodings',
        '--hidden-import=glyphs_data',
        '--hidden-import=modify_widget',
        '--hidden-import=theme_editor_widget',
        '--hidden-import=theme_switcher_widget',
        '--hidden-import=utils',
        '--hidden-import=cloud_sync',
        '--hidden-import=nss_error_monitor',
        '--hidden-import=plugin_registry',
        '--hidden-import=win32gui',
        '--hidden-import=win32api',
        '--hidden-import=win32con',
        '--exclude-module=brotlicffi',
        '--exclude-module=brotli',
        '--exclude-module=numpy',
        '--exclude-module=PyQt5.QtWebEngine',
        '--exclude-module=PyQt5.QtWebEngineCore',
        '--exclude-module=PyQt5.QtWebEngineWidgets',
        '--exclude-module=PyQt5.QtWebKit',
        '--exclude-module=PyQt5.QtWebKitWidgets',
        '--exclude-module=PyQt5.QtSql',
        '--exclude-module=PyQt5.QtTest',
        '--exclude-module=PyQt5.QtXml',
        '--exclude-module=PyQt5.QtMultimedia',
        '--exclude-module=PyQt5.QtQuick',
        '--exclude-module=PyQt5.QtQml',
        '--exclude-module=PyQt5.QtLocation',
        '--exclude-module=PyQt5.QtSensors',
        '--exclude-module=PyQt5.QtRemoteObjects',
        '--exclude-module=PyQt5.QtWebChannel',
        '--exclude-module=PyQt5.QtBluetooth',
        '--exclude-module=PyQt5.QtNfc',
        '--exclude-module=PyQt5.QtPositioning',
        '--exclude-module=PyQt5.QtQuickWidgets',
        '--exclude-module=PyQt5.QtMultimediaWidgets',
        '--exclude-module=PyQt5.QtNetwork',
        '--exclude-module=PyQt5.QtDBus',
        '--exclude-module=PyQt5.QtDesigner',
        '--exclude-module=PyQt5.QtHelp',
        '--exclude-module=PyQt5.QtPrintSupport',
        '--exclude-module=PyQt5.QtXmlPatterns',
        '--exclude-module=PyQt5.QtOpenGL',
        '--exclude-module=PyQt5.QtOpenGLWidgets',
        '--exclude-module=tkinter',
        '--exclude-module=unittest',
        '--exclude-module=pydoc',
        '--noconfirm',
        '--clean',
    ]

    optional_dirs = [
        (os.path.join("..", "imports"), "imports"),
        (os.path.join("..", "theme"), "theme"),
    ]

    for src, dst in optional_dirs:
        if os.path.exists(src):
            base_args.append(f'--add-data={src};{dst}')

    PyInstaller.__main__.run(base_args)
    print(f"Build complete! Single executable is at: {os.path.abspath(os.path.join('dist', 'launcher.exe'))}")

if __name__ == "__main__":
    build()