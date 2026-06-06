import struct

def extract_ttf(dll_path, output_path):
    with open(dll_path, 'rb') as f:
        data = f.read()

    # Search for TTF header
    idx = 0
    font_count = 0
    while True:
        idx = data.find(b'\x00\x01\x00\x00', idx)
        if idx == -1: break
        
        if idx + 12 <= len(data):
            num_tables = struct.unpack('>H', data[idx+4:idx+6])[0]
            if 10 <= num_tables <= 40: # Likely a real font
                # Read table directory to find total size
                max_offset = 0
                is_valid = True
                for i in range(num_tables):
                    table_entry = idx + 12 + (i * 16)
                    if table_entry + 16 > len(data):
                        is_valid = False
                        break
                    tag = data[table_entry:table_entry+4]
                    if not tag.isalnum() and tag != b'OS/2':
                        pass
                    
                    offset = struct.unpack('>I', data[table_entry+8:table_entry+12])[0]
                    length = struct.unpack('>I', data[table_entry+12:table_entry+16])[0]
                    max_offset = max(max_offset, offset + length)
                
                if is_valid and max_offset > 0 and max_offset < len(data):
                    font_data = data[idx:idx+max_offset]
                    
                    if b'Nilesoft' in font_data:
                        print(f"Found Nilesoft font at offset {idx}, size {len(font_data)}")
                        with open(output_path, 'wb') as out:
                            out.write(font_data)
                        return True
        idx += 4
    return False

if __name__ == "__main__":
    if extract_ttf(r"C:\Program Files\iMA Menu\shell.dll", "nilesoft.ttf"):
        print("Successfully extracted nilesoft.ttf")
    else:
        if extract_ttf(r"C:\Program Files\iMA Menu\shell.exe", "nilesoft.ttf"):
            print("Successfully extracted nilesoft.ttf from shell.exe")
        else:
            print("Failed to extract font")
