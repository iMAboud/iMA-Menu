import os
import shutil
import sys
import subprocess

def build():
    print("Starting Nuitka build process...")
    # Clean previous builds
    if os.path.exists('launcher.dist'):
        shutil.rmtree('launcher.dist')
    if os.path.exists('launcher.build'):
        shutil.rmtree('launcher.build')

    base_args = [
        sys.executable,
        '-m', 'nuitka',
        'launcher.pyw',
        '--standalone',
        '--plugin-enable=pyqt5',
        '--windows-disable-console',
        f'--windows-icon-from-ico={os.path.join("icons", "icon.ico")}',
        '--include-data-file=style.css=.',
        '--include-data-dir=icons=icons',
        '--include-data-file=nilesoft.ttf=.',
        '--include-data-file=extract_font.py=.',
        '--include-data-file=color_palette.json=.',
        '--enable-plugin=anti-bloat',
        '--noinclude-pytest-mode=nofollow',
        '--noinclude-setuptools-mode=nofollow',
        '--noinclude-custom-mode=numpy:warning',
        '--output-dir=.',
    ]

    # Dynamically add existing folders
    optional_dirs = [
        (os.path.join("..", "imports"), "imports"),
        (os.path.join("..", "theme"), "theme"),
    ]

    for src, dst in optional_dirs:
        if os.path.exists(src):
            base_args.append(f'--include-data-dir={src}={dst}')

    try:
        subprocess.check_call(base_args)
        print(f"Build complete! Size-optimized results are in: {os.path.abspath('launcher.dist')}")
    except subprocess.CalledProcessError as e:
        print(f"Build failed: {e}")

if __name__ == "__main__":
    # Ensure nuitka is installed
    try:
        import nuitka
    except ImportError:
        print("Nuitka is not installed. Installing Nuitka...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "nuitka", "zstandard"])
    build()
