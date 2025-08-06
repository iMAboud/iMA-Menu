# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['D:\\iMA Menu Remake\\iMA Menu Remake\\installer\\installer.py'],
    pathex=[],
    binaries=[],
    datas=[('D:\\iMA Menu Remake\\iMA Menu Remake\\iMA Menu', 'iMA Menu'), ('ima.ico', '.'), ('assets', 'assets'), ('style.css', '.')],
    hiddenimports=[],
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
    name='iMA Menu Installer',
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
    uac_admin=True,
    icon=['ima.ico'],
)
