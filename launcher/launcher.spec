# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['launcher.pyw'],
    pathex=[],
    binaries=[],
    datas=[('style.css', '.'), ('icons', 'icons'), ('..\\imports', 'imports'), ('..\\theme', 'theme')],
    hiddenimports=['modify_widget', 'theme_editor_widget', 'theme_switcher_widget', 'utils'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PyQt5.QtWebEngineWidgets', 'PyQt5.QtMultimedia', 'PyQt5.QtSql', 'PyQt5.QtTest', 'PyQt5.QtXml', 'PyQt5.QtDesigner', 'PyQt5.QtPrintSupport', 'PyQt5.QtOpenGL', 'PyQt5.QtSvg'],
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
    strip=True,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['icons\\icon.png'],
)
