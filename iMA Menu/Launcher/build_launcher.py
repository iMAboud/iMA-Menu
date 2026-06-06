import PyInstaller.__main__
import os
import shutil
import sys

def build():
    # Clean previous builds
    if os.path.exists('dist'):
        shutil.rmtree('dist')
    if os.path.exists('build'):
        shutil.rmtree('build')

    base_args = [
        'launcher.pyw',
        '--onedir', 
        '--windowed',
        f'--icon={os.path.join("icons", "icon.ico")}',
        '--name=launcher',
        '--add-data=style.css;.',
        '--add-data=icons;icons',
        '--add-data=nilesoft.ttf;.',
        '--add-data=extract_font.py;.',
        '--add-data=color_palette.json;.',
        '--hidden-import=placeholder_ids',
        '--hidden-import=modify_widget',
        '--hidden-import=theme_editor_widget',
        '--hidden-import=theme_switcher_widget',
        '--hidden-import=utils',
        '--hidden-import=win32gui',
        '--hidden-import=win32api',
        '--hidden-import=win32con',
        # Aggressive exclusions
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
        '--noconfirm',
        '--clean',
    ]

    # Dynamically add existing folders
    optional_dirs = [
        (os.path.join("..", "imports"), "imports"),
        (os.path.join("..", "theme"), "theme"),
    ]

    for src, dst in optional_dirs:
        if os.path.exists(src):
            base_args.append(f'--add-data={src};{dst}')

    PyInstaller.__main__.run(base_args)

    # Post-build cleanup in the correct _internal folder
    dist_dir = os.path.join('dist', 'launcher', '_internal')
    if not os.path.exists(dist_dir):
        dist_dir = os.path.join('dist', 'launcher') # Fallback for older PyInstaller

    if os.path.exists(dist_dir):
        to_delete = [
            'Qt5Quick.dll', 'Qt5Qml.dll', 'Qt5QuickWidgets.dll', 
            'Qt5WebEngineCore.dll', 'Qt5WebEngineWidgets.dll',
            'libGLESv2.dll', 'libEGL.dll', 'd3dcompiler_47.dll', 'opengl32sw.dll',
            'Qt5VirtualKeyboard.dll', 'Qt5Network.dll', 'Qt5Svg.dll', 'Qt5Pdf.dll',
            'Qt5Bluetooth.dll', 'Qt5Positioning.dll', 'Qt5Sensors.dll', 'Qt5Multimedia.dll',
            'Qt5MultimediaWidgets.dll', 'Qt5Xml.dll', 'Qt5Sql.dll', 'Qt5Test.dll'
        ]
        for f in to_delete:
            f_path = os.path.join(dist_dir, f)
            if os.path.exists(f_path):
                try: os.remove(f_path)
                except: pass
            
            # Check subdirectories too
            for root, dirs, files in os.walk(dist_dir):
                if f in files:
                    try: os.remove(os.path.join(root, f))
                    except: pass

        # Aggressively remove large folders that shouldn't be there
        for folder in ['numpy', 'PyQt5/Qt5/plugins/platforms/qminimal.dll', 'PyQt5/Qt5/plugins/imageformats/qwebp.dll']:
             f_path = os.path.join(dist_dir, folder)
             if os.path.exists(f_path):
                 try:
                     if os.path.isdir(f_path): shutil.rmtree(f_path)
                     else: os.remove(f_path)
                 except: pass

    print(f"Build complete! Size-optimized results are in: {os.path.abspath('dist')}")

if __name__ == "__main__":
    build()