import os, re

def cleanup_file(path):
    if not os.path.exists(path): return
    with open(path, 'r', encoding='utf-8') as f: content = f.read()
    
    # Remove _order metadata
    new_content = re.sub(r"\s*_order='\[.*?\]'", "", content)
    # Remove empty properties
    new_content = re.sub(r"\bin=''\s*", "", new_content)
    new_content = re.sub(r"\btitle=''\s*", "", new_content)
    # Fix quoted glyphs: image='[[...]]' -> image=[[...]
    new_content = re.sub(r"\b(image|icon)='(\[\[.*?\]\])'", r"\1=\2", new_content)
    
    if new_content != content:
        with open(path, 'w', encoding='utf-8') as f: f.write(new_content)
        print(f"Cleaned up: {path}")

root = "."
for dirpath, _, filenames in os.walk(os.path.join(root, "imports")):
    for f in filenames:
        if f.endswith(".nss"): cleanup_file(os.path.join(dirpath, f))

for dirpath, _, filenames in os.walk(os.path.join(root, "plugins")):
    for f in filenames:
        if f.endswith(".nss"): cleanup_file(os.path.join(dirpath, f))
