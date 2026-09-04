import PyInstaller.__main__
import os
import shutil
import sys
import zipfile

SPEC_TEMPLATE = '''# -*- mode: python ; coding: utf-8 -*-
import os

block_cipher = None

# Heavy native DLLs that are completely unused by pure QWidget Windows apps
excluded_binaries = {
    'opengl32sw.dll',
    'd3dcompiler_47.dll',
    'libglesv2.dll',
    'libegl.dll',
    'qt5quick.dll',
    'qt5qml.dll',
    'qt5qmlmodels.dll',
    'qt5network.dll',
    'qt5dbus.dll',
    'qt5sensors.dll',
    'qt5location.dll',
    'qt5positioning.dll',
    'qt5multimedia.dll',
    'qt5multimediawidgets.dll',
    'qt5xml.dll',
    'qt5xmlpatterns.dll',
    'qt5sql.dll',
    'qt5test.dll',
    'qt5printsupport.dll',
    'qminimal.dll',
    'qoffscreen.dll',
    'qwebgl.dll',
    'qtiff.dll',
    'qtuiotouchplugin.dll',
    'qxdgdesktopportal.dll',
    'qicns.dll',
    'qtga.dll',
    'qwbmp.dll',
    'qt5websockets.dll',
    'libssl-3.dll',
}

datas = [
    ('style.css', '.'),
    ('ima_updater.exe', '.'),
    ('shell.dll', '.'),
    ('shell.exe', '.'),
    ('icons', 'icons'),
    ('fonts', 'fonts'),
    ('cursors.json', '.'),
    ('cursors_previews.json', '.'),
    ('cache/plugins.json', 'cache'),
]

a = Analysis(
    ['launcher.pyw'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[
        'encodings', 'glyphs_data', 'modify_widget',
        'theme_editor_widget', 'theme_switcher_widget', 'cursor_widget',
        'github_client', 'utils', 'cloud_sync', 'nss_error_monitor',
        'plugin_registry', 'nss_parser', 'plugin_workers'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'requests', 'urllib3', 'idna', 'certifi', 'charset_normalizer',
        'markdown', 'xml', 'pyexpat', '_elementtree', 'xmlrpc',
        'win32gui', 'win32api', 'win32con', 'win32', 'win32crypt', 'pywintypes', 'pywin32_system32', 'win32trace', 'win32ui',
        '_decimal', 'decimal', 'lzma', '_lzma', 'bz2', '_bz2', 'sqlite3', '_sqlite3',
        'distutils', 'setuptools', 'pkg_resources', 'pip', 'wheel', 'curses', 'turtle',
        'cryptography', 'cffi', '_cffi_backend', 'pycparser', 'psutil',
        'brotlicffi', 'brotli', 'numpy',
        'PyQt5.QtWinExtras',
        'PyQt5.QtWebEngine', 'PyQt5.QtWebEngineCore', 'PyQt5.QtWebEngineWidgets',
        'PyQt5.QtWebKit', 'PyQt5.QtWebKitWidgets',
        'PyQt5.QtSql', 'PyQt5.QtTest', 'PyQt5.QtXml', 'PyQt5.QtMultimedia',
        'PyQt5.QtQuick', 'PyQt5.QtQml', 'PyQt5.QtLocation', 'PyQt5.QtSensors',
        'PyQt5.QtRemoteObjects', 'PyQt5.QtWebChannel', 'PyQt5.QtBluetooth',
        'PyQt5.QtNfc', 'PyQt5.QtPositioning', 'PyQt5.QtQuickWidgets',
        'PyQt5.QtMultimediaWidgets', 'PyQt5.QtNetwork', 'PyQt5.QtDBus',
        'PyQt5.QtDesigner', 'PyQt5.QtHelp', 'PyQt5.QtPrintSupport',
        'PyQt5.QtXmlPatterns', 'PyQt5.QtOpenGL', 'PyQt5.QtOpenGLWidgets',
        'tkinter', 'unittest', 'pydoc',
        'unicodedata', 'multiprocessing', '_multiprocessing',
        'ssl', '_ssl', 'webbrowser', 'tarfile'
    ],
    noarchive=False,
    optimize=2,
)

# Strip out heavy unneeded native binaries from the bundle
a.binaries = [
    x for x in a.binaries
    if not any(x[0].lower().endswith(ex) for ex in excluded_binaries)
]

# Strip out unused translation files from datas
a.datas = [
    x for x in a.datas
    if not x[0].lower().endswith('.qm')
]

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='launcher',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join('icons', 'icon.ico'),
)
'''

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

    with open('launcher.spec', 'w', encoding='utf-8') as f:
        f.write(SPEC_TEMPLATE)

    PyInstaller.__main__.run(['launcher.spec', '--noconfirm', '--clean'])

    dist_dir = os.path.abspath('dist')
    exe_path = os.path.join(dist_dir, 'launcher.exe')

    if os.path.exists(exe_path):
        size_mb = os.path.getsize(exe_path) / (1024 * 1024)
        print(f"\n=======================================================")
        print(f"Build complete!")
        print(f"Standalone Executable: {exe_path} ({size_mb:.2f} MB)")
        print(f"=======================================================\n")

if __name__ == "__main__":
    build()