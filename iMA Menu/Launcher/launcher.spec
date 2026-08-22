# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['launcher.pyw'],
    pathex=[],
    binaries=[],
    datas=[('style.css', '.'), ('ima_updater.exe', '.'), ('shell.dll', '.'), ('shell.exe', '.'), ('icons', 'icons'), ('fonts', 'fonts'), ('cache/plugins.json', 'cache'), ('..\\imports', 'imports'), ('..\\theme', 'theme')],
    hiddenimports=['unicodedata', 'idna', 'urllib3', 'certifi', 'charset_normalizer', 'requests', 'encodings', 'glyphs_data', 'modify_widget', 'theme_editor_widget', 'theme_switcher_widget', 'utils', 'cloud_sync', 'nss_error_monitor', 'plugin_registry', 'win32gui', 'win32api', 'win32con'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['brotlicffi', 'brotli', 'numpy', 'PyQt5.QtWebEngine', 'PyQt5.QtWebEngineCore', 'PyQt5.QtWebEngineWidgets', 'PyQt5.QtWebKit', 'PyQt5.QtWebKitWidgets', 'PyQt5.QtSql', 'PyQt5.QtTest', 'PyQt5.QtXml', 'PyQt5.QtMultimedia', 'PyQt5.QtQuick', 'PyQt5.QtQml', 'PyQt5.QtLocation', 'PyQt5.QtSensors', 'PyQt5.QtRemoteObjects', 'PyQt5.QtWebChannel', 'PyQt5.QtBluetooth', 'PyQt5.QtNfc', 'PyQt5.QtPositioning', 'PyQt5.QtQuickWidgets', 'PyQt5.QtMultimediaWidgets', 'PyQt5.QtNetwork', 'PyQt5.QtDBus', 'PyQt5.QtDesigner', 'PyQt5.QtHelp', 'PyQt5.QtPrintSupport', 'PyQt5.QtXmlPatterns', 'PyQt5.QtOpenGL', 'PyQt5.QtOpenGLWidgets', 'tkinter', 'unittest', 'pydoc'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

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
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['icons\\icon.ico'],
)
