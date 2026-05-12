# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['launcher.pyw'],
    pathex=[],
    binaries=[],
    datas=[('style.css', '.'), ('icons', 'icons'), ('nilesoft.ttf', '.'), ('extract_font.py', '.'), ('color_palette.json', '.'), ('..\\imports', 'imports'), ('..\\theme', 'theme')],
    hiddenimports=['placeholder_ids', 'modify_widget', 'theme_editor_widget', 'theme_switcher_widget', 'utils', 'win32gui', 'win32api', 'win32con'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['numpy', 'PyQt5.QtWebEngine', 'PyQt5.QtWebEngineCore', 'PyQt5.QtWebEngineWidgets', 'PyQt5.QtWebKit', 'PyQt5.QtWebKitWidgets', 'PyQt5.QtSql', 'PyQt5.QtTest', 'PyQt5.QtXml', 'PyQt5.QtMultimedia', 'PyQt5.QtQuick', 'PyQt5.QtQml', 'PyQt5.QtLocation', 'PyQt5.QtSensors', 'PyQt5.QtRemoteObjects', 'PyQt5.QtWebChannel', 'PyQt5.QtBluetooth', 'PyQt5.QtNfc', 'PyQt5.QtPositioning', 'PyQt5.QtQuickWidgets', 'PyQt5.QtMultimediaWidgets'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='launcher',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['icons\\icon.png'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='launcher',
)
