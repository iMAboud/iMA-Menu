import tkinter as tk
from tkinter import Canvas
import pyautogui
import pyperclip
from pynput import mouse, keyboard
import ctypes
import os

class ColorWindow:
    def __init__(self):
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.attributes('-topmost', True)
        self.root.attributes("-transparentcolor", "white")
        self.canvas_width = 200
        self.canvas_height = 200
        self.canvas = Canvas(self.root, width=self.canvas_width, height=self.canvas_height, bg="white", highlightthickness=0)
        self.canvas.pack()
        self.oval_id = self.canvas.create_oval(0, 0, self.canvas_width, self.canvas_height, fill="white", outline="black")
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
        self.root.after(10, self.update_position)

    def update_canvas_size(self, width, height):
        self.canvas_width = width
        self.canvas_height = height
        self.canvas.config(width=self.canvas_width, height=self.canvas_height)
        self.canvas.delete("all")
        self.oval_id = self.canvas.create_oval(0, 0, self.canvas_width, self.canvas_height, fill="white", outline="black")

    def update_color(self):
        x, y = pyautogui.position()
        try:
            screenshot = pyautogui.screenshot(region=(x-50, y-50, 100, 100))
            pixel_color = screenshot.getpixel((50, 50))
            hex_color = '#{:02x}{:02x}{:02x}'.format(*pixel_color)
            self.canvas.itemconfig(self.oval_id, fill=hex_color)
            self.root.after(50, self.update_color)
        except Exception as e:
            print(f"Error: {e}")

def print_colored(text, color=''):
    if color:
        print(f"\033[38;2;{int(color[1:3], 16)};{int(color[3:5], 16)};{int(color[5:7], 16)}m{text}\033[0m")
    else:
        print(text)

def get_color_hex():
    title = "iMColor"
    print_colored(title.center(110), '#ffffff')
    print_colored("Right-click to copy HEX".center(110), '#00ffff')
    
    color_window = ColorWindow()
    color_window.update_color()
    
    def on_click(x, y, button, pressed):
      if pressed and button == mouse.Button.right:
        try:
            screenshot = pyautogui.screenshot(region=(x, y, 1, 1))
            pixel_color = screenshot.getpixel((0, 0))
            hex_color = '#{:02x}{:02x}{:02x}'.format(*pixel_color)
            pyperclip.copy(hex_color)
            print_colored(f"Hex code: {hex_color} copied to clipboard.".center(110), hex_color)
        except Exception as e:
            print_colored(f"Error: {e}".center(110))

    with mouse.Listener(on_click=on_click) as listener:
        color_window.root.mainloop()

def on_press(key):
    if key == keyboard.Key.esc:
        os._exit(0)  

if __name__ == "__main__":
    ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 6)
    
    with keyboard.Listener(on_press=on_press):
        get_color_hex()
