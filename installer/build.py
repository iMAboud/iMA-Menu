import PyInstaller.__main__
import os
import shutil

if __name__ == '__main__':
    workpath = os.path.abspath('build')
    distpath = os.path.abspath('dist')
    icon_path = 'ima.ico'

    # Clean previous builds
    if os.path.exists(distpath):
        shutil.rmtree(distpath)
    if os.path.exists(workpath):
        shutil.rmtree(workpath)

    # --- Build the main installer ---
    installer_script = os.path.abspath('installer.py')
    
    PyInstaller.__main__.run([
        installer_script,
        '--onefile',
        '--windowed',
        f'--icon={icon_path}',
        '--name=iMA Menu Installer',
        f'--add-data={os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "iMA Menu"))};iMA Menu',
        f'--add-data={icon_path};.',
        '--add-data=assets;assets',
        '--add-data=style.css;.',
        f'--workpath={workpath}',
        f'--distpath={distpath}',
        '--exclude-module=PyQt5.QtWebEngineWidgets',
        '--exclude-module=PyQt5.QtMultimedia',
        '--exclude-module=PyQt5.QtSql',
        '--exclude-module=PyQt5.QtTest',
        '--exclude-module=PyQt5.QtXml',
        '--exclude-module=PyQt5.QtDesigner',
        '--exclude-module=PyQt5.QtPrintSupport',
        '--exclude-module=PyQt5.QtOpenGL',
        '--exclude-module=PyQt5.QtSvg',
        '--uac-admin',
    ])