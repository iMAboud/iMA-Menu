import pyautogui
import pyperclip
import tkinter as tk
from pynput import mouse

class ColorWindow:
    def __init__(self):
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.attributes('-topmost', True)
        self.root.attributes("-transparentcolor", "white")  
        self.canvas = tk.Canvas(self.root, width=50, height=50, bg="white", highlightthickness=0)
        self.canvas.pack()
        self.canvas.create_oval(0, 0, 50, 50, fill="white", outline="black")  
        self.root.bind("<ButtonPress-1>", self.start_drag)
        self.root.bind("<B1-Motion>", self.drag)

        self.update_position()

    def start_drag(self, event):
        self.drag_start_x = event.x
        self.drag_start_y = event.y
        self.last_x = self.root.winfo_pointerx()
        self.last_y = self.root.winfo_pointery()

    def drag(self, event):
        dx = self.root.winfo_pointerx() - self.last_x
        dy = self.root.winfo_pointery() - self.last_y
        x = self.root.winfo_x() + dx
        y = self.root.winfo_y() + dy
        self.root.geometry(f"+{x}+{y}")
        self.last_x = self.root.winfo_pointerx()
        self.last_y = self.root.winfo_pointery()

    def update_position(self):
        x, y = pyautogui.position()
        self.root.geometry(f"+{x}+{y}")
        self.root.after(50, self.update_position)

def update_color(color_window):
    x, y = pyautogui.position()
    try:
        screenshot = pyautogui.screenshot(region=(x, y, 1, 1))
        pixel_color = screenshot.getpixel((0, 0))
        hex_color = '#{:02x}{:02x}{:02x}'.format(*pixel_color)
        color_window.canvas.itemconfig("all", fill=hex_color)  
        color_window.root.after(100, update_color, color_window)
    except Exception as e:
        print(f"Error: {e}")

def on_click(x, y, button, pressed, color_window):
    if pressed and button == mouse.Button.right:
        try:
            screenshot = pyautogui.screenshot(region=(x, y, 1, 1))
            pixel_color = screenshot.getpixel((0, 0))
            hex_color = '#{:02x}{:02x}{:02x}'.format(*pixel_color)
            pyperclip.copy(hex_color)
            print(f"Hex color code: {hex_color} copied to clipboard.")
            return True  
        except Exception as e:
            print(f"Error: {e}")

def get_color_hex():
    print("Right-click to copy HEX")
    with mouse.Listener(on_click=lambda x, y, button, pressed: on_click(x, y, button, pressed, None)) as listener:
        color_window = ColorWindow()
        color_window.root.after(100, update_color, color_window)
        color_window.root.mainloop()

if __name__ == "__main__":
    get_color_hex()
