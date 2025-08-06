import sys
import os
import tempfile
import shutil

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def safe_file_write(filepath, content):
    temp_dir = os.path.dirname(os.path.abspath(filepath))
    temp_fd, temp_path = tempfile.mkstemp(dir=temp_dir)
    try:
        with os.fdopen(temp_fd, 'w') as temp_file:
            temp_file.write(content)
        shutil.move(temp_path, filepath)
    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise e