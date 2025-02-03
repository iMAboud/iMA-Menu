import os
import random
import string
from tkinter import Tk, Label, Entry, Button, Canvas, messagebox
import re
import ctypes
from ctypes import windll

CROC_BAT_PATH = r"C:\Program Files\iMA Menu\script\croc.bat"

def generate_random_code(length=6):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choices(characters, k=length))

def get_and_update_code(new_code=None):
    if os.path.exists(CROC_BAT_PATH):
        with open(CROC_BAT_PATH, 'r', encoding='utf-8') as file:
            content = file.read()
        match = re.search(r'--code (.*?) \\"\$\(Get-Clipboard\)\\"', content)
        current_code = match.group(1) if match else None
        if new_code:
            updated_content = re.sub(
                r'--code (.*?) \\"\$\(Get-Clipboard\)\\"',
                f'--code {new_code} \\"$(Get-Clipboard)\\"',
                content
            )
            with open(CROC_BAT_PATH, 'w', encoding='utf-8') as file:
                file.write(updated_content)
            return new_code
        return current_code
    else:
        raise FileNotFoundError(f"File not found at: {CROC_BAT_PATH}")

def make_window_draggable(widget):
    def start_drag(event):
        widget.start_x = event.x_root - widget.winfo_x()
        widget.start_y = event.y_root - widget.winfo_y()

    def drag(event):
        x = event.x_root - widget.start_x
        y = event.y_root - widget.start_y
        widget.geometry(f"+{x}+{y}")

    widget.bind("<Button-1>", start_drag)
    widget.bind("<B1-Motion>", drag)

def center_window(root, width, height):
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    x = (screen_width // 2) - (width // 2)
    y = (screen_height // 2) - (height // 2)
    root.geometry(f"{width}x{height}+{x}+{y}")

def add_rounded_corners(window, radius=22):
    hwnd = windll.user32.GetParent(window.winfo_id())
    windll.dwmapi.DwmSetWindowAttribute(hwnd, 2, ctypes.byref(ctypes.c_int(1)), ctypes.sizeof(ctypes.c_int(1)))
    region = windll.gdi32.CreateRoundRectRgn(0, 0, window.winfo_width(), window.winfo_height(), radius, radius)
    windll.user32.SetWindowRgn(hwnd, region, True)

def confirm_action(entry, root, success_label, error_label):
    new_code = entry.get().strip()
    
    if len(new_code) < 6:
        return

    get_and_update_code(new_code)

    success_label.config(text="SUCCESS", fg="green")
    root.update()

    root.after(1000, root.destroy)

def validate_input(entry, error_label, space_error_label):
    user_input = entry.get()
    if " " in user_input:
        entry.delete(len(user_input) -1, 'end') 
        space_error_label.config(text="No SPACE", fg="red")
    elif len(user_input.strip()) < 6:
        space_error_label.config(text="")
        error_label.config(text="6+ characters only", fg="red")
    else:
        error_label.config(text="")
        space_error_label.config(text="")
        
def main_ui():
    root = Tk()
    width, height = 350, 250
    center_window(root, width, height)

    root.overrideredirect(True)
    root.configure(bg="#2E2E2E")

    make_window_draggable(root)

    canvas = Canvas(root, width=width, height=height, bg="#2E2E2E", highlightthickness=0)
    canvas.pack(fill="both", expand=True)

    root.update_idletasks()
    add_rounded_corners(root, radius=22)

    try:
        current_code = get_and_update_code()
        if not current_code:
            current_code = generate_random_code()
            get_and_update_code(current_code)
    except FileNotFoundError as e:
        messagebox.showerror("Error", str(e))
        root.destroy()
        return

    label = Label(canvas, text="Type a unique CODE for others to receive files from you!",
                  font=("Arial", 10, "bold"), wraplength=300, bg="#2E2E2E", fg="white")
    label.place(relx=0.5, y=40, anchor="center")

    code_entry = Entry(canvas, font=("Arial", 12), justify="center", bg="#1C1C1C", fg="white", insertbackground="white")
    code_entry.insert(0, current_code)
    code_entry.place(relx=0.5, y=90, anchor="center", width=200)

    error_label = Label(canvas, text="", font=("Arial", 9), bg="#2E2E2E", fg="red")
    error_label.place(relx=0.5, y=120, anchor="center")
    
    space_error_label = Label(canvas, text="", font=("Arial", 9), bg="#2E2E2E", fg="red")
    space_error_label.place(relx=0.5, y=135, anchor="center")
    

    success_label = Label(canvas, text="", font=("Arial", 10), bg="#2E2E2E", fg="white")
    success_label.place(relx=0.5, y=150, anchor="center")

    button_frame = Canvas(canvas, bg="#2E2E2E", highlightthickness=0)
    button_frame.place(relx=0.5, y=200, anchor="center")

    confirm_button = Button(button_frame, text="Confirm", command=lambda: confirm_action(code_entry, root, success_label, error_label),
                            font=("Arial", 10), bg="#4CAF50", fg="white", width=10, relief="flat")
    confirm_button.pack(side="left", padx=5)

    cancel_button = Button(button_frame, text="Cancel", command=root.destroy, font=("Arial", 10),
                           bg="#F44336", fg="white", width=10, relief="flat")
    cancel_button.pack(side="left", padx=5)

    code_entry.bind("<KeyRelease>", lambda event: validate_input(code_entry, error_label, space_error_label))

    root.mainloop()

if __name__ == "__main__":
    main_ui()
