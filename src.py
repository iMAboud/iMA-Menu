import subprocess
import os
import shutil
import ctypes

def send_key(key):
    ctypes.windll.user32.keybd_event(key, 0, 0, 0)
    ctypes.windll.user32.keybd_event(key, 0, 2, 0)

def run_command(command):
    try:
        print(f"Executing command: {command}")
        subprocess.run(["powershell.exe", "-Command", command], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {e}")

        pass

def is_package_installed(package_name):
    try:
        subprocess.run(["winget", "show", package_name], check=True, stdout=subprocess.PIPE)
        return True
    except subprocess.CalledProcessError as e:
        return False

def install_package(package_name):
    try:
        print(f"Installing {package_name}...")
        subprocess.run(["winget", "install", package_name], check=True)
        print(f"{package_name} installed successfully.")
        return True
    except Exception as e:
        print(f"Error installing package '{package_name}': {e}")
        return False

def main():

    print("Installing Schollz.croc...")
    install_package("Schollz.croc")

    script_dir = os.path.dirname(os.path.abspath(__file__))
    source_dir = os.path.join(script_dir, "files")
    dest_dir = os.path.join("C:\\", "Program Files", "Nilesoft Shell")

    try:
        print("Copying files...")
        for root, dirs, files in os.walk(source_dir):
            dest_root = os.path.join(dest_dir, os.path.relpath(root, source_dir))
            os.makedirs(dest_root, exist_ok=True)
            for file in files:
                src_file = os.path.join(root, file)
                dest_file = os.path.join(dest_root, file)
                print(f"Copying {src_file} to {dest_file}")
                shutil.copy(src_file, dest_file)
    except Exception as e:
        print(f"Error copying files: {e}")
        return

    print("Files copied successfully.")

    shell_exe_path = os.path.join("C:\\", "Program Files", "Nilesoft Shell", "shell.exe")
    try:
        subprocess.Popen([shell_exe_path], shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        time.sleep(1)
        subprocess.run(["taskkill", "/f", "/im", "shell.exe"], check=True)
    except Exception as e:
        print(f"Error running shell.exe: {e}")

if __name__ == "__main__":
    main()
