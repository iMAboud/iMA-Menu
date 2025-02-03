import pyautogui
import pyperclip
import tkinter as tk
from pynput import mouse, keyboard
from colorama import init, Fore, Style
import ctypes
import os
import sys
import math

init()

class ColorWindow:
    def __init__(self):
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.attributes('-topmost', True)
        self.root.attributes("-transparentcolor", "white")
        self.canvas_width = 200
        self.canvas_height = 200
        self.canvas = tk.Canvas(self.root, width=self.canvas_width, height=self.canvas_height, bg="white", highlightthickness=0)
        self.canvas.pack()
        self.circle = self.canvas.create_oval(0, 0, self.canvas_width, self.canvas_height, fill="white", outline="black", width=2)
        self.highlighted_pixel = None
        self.root.bind("<ButtonPress-1>", self.start_drag)
        self.root.bind("<B1-Motion>", self.drag)
        self.mode = 'normal'
        self.pixel_size = 20  
        self.advanced_pixel_size = 32  
        self.border_thickness = 5
        self.offset_x = 10
        self.offset_y = 10
        self.last_x = None
        self.last_y = None
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
        screen_width, screen_height = pyautogui.size()

        if self.last_x == x and self.last_y == y:
             self.root.after(10, self.update_position)
             return
        
        self.last_x = x
        self.last_y = y

        new_offset_y = 10
        new_offset_x = 10
        if y + self.canvas_height + new_offset_y > screen_height:
            new_offset_y = - self.canvas_height - 10
        
        if x + self.canvas_width + new_offset_x > screen_width:
             new_offset_x = - self.canvas_width - 10

        self.offset_x = new_offset_x
        self.offset_y = new_offset_y

        self.root.geometry(f"+{x + self.offset_x}+{y + self.offset_y}")
        self.root.after(10, self.update_position)

    def update_canvas_size(self, width, height):
        self.canvas_width = width
        self.canvas_height = height
        self.canvas.config(width=self.canvas_width, height=self.canvas_height)
        self.canvas.delete("all")
        if self.mode == 'normal':
            self.circle = self.canvas.create_oval(0, 0, self.canvas_width, self.canvas_height, fill="white", outline="black", width=2)

    def update_color(self):
        x, y = pyautogui.position()
        try:
            if self.mode == 'normal':
                self.canvas.delete(self.highlighted_pixel) if self.highlighted_pixel else None
                screenshot = pyautogui.screenshot(region=(x - 50, y - 50, 100, 100))
                pixel_color = screenshot.getpixel((50, 50))
                hex_color = '#{:02x}{:02x}{:02x}'.format(*pixel_color)
                self.canvas.itemconfig(self.circle, fill=hex_color)
                self.root.config(bg=hex_color)  
                self.root.after(50, self.update_color)

            elif self.mode == 'pixel':
                self.canvas.delete("all")
                radius = min(self.canvas_width, self.canvas_height) / 2
                center_x = self.canvas_width / 2
                center_y = self.canvas_height / 2

                screenshot_size = int(radius * 2)
                screenshot_x = int(x - radius)
                screenshot_y = int(y - radius)
                screenshot = pyautogui.screenshot(region=(screenshot_x, screenshot_y, screenshot_size, screenshot_size))


                for px_y in range(0, self.canvas_height, self.advanced_pixel_size):
                    for px_x in range(0, self.canvas_width, self.advanced_pixel_size):

                        dist_x = px_x - center_x + self.advanced_pixel_size/2
                        dist_y = px_y - center_y + self.advanced_pixel_size/2
                        dist_center = math.sqrt(dist_x**2 + dist_y**2)

                        if dist_center <= radius:
                            screenshot_px_x = int((px_x / self.canvas_width) * screenshot_size)
                            screenshot_px_y = int((px_y / self.canvas_height) * screenshot_size)

                            pixel_color = screenshot.getpixel((screenshot_px_x, screenshot_px_y))
                            hex_color = '#{:02x}{:02x}{:02x}'.format(*pixel_color)
                            self.canvas.create_rectangle(px_x, px_y, px_x + self.advanced_pixel_size, px_y + self.advanced_pixel_size, fill=hex_color, outline="")

                highlight_size = self.advanced_pixel_size * 2
                highlight_x = center_x - highlight_size // 2
                highlight_y = center_y - highlight_size // 2
                
                pixel_color = screenshot.getpixel((screenshot_size // 2, screenshot_size // 2))
                hex_color = '#{:02x}{:02x}{:02x}'.format(*pixel_color)
                
                if self.highlighted_pixel:
                   self.canvas.delete(self.highlighted_pixel)

                self.highlighted_pixel = self.canvas.create_rectangle(highlight_x, highlight_y, highlight_x + highlight_size, highlight_y + highlight_size, fill=hex_color, outline="white", width=2)


                self.canvas.create_oval(0, 0, self.canvas_width, self.canvas_height, outline="white", width=2)

                self.root.config(bg=hex_color)  
                self.root.after(50, self.update_color)
        except Exception as e:
            print(f"Error: {e}")


def print_colored(text, color):
    colored_text = f"{getattr(Fore, color.upper(), '')}{text}{Style.RESET_ALL}"
    print(colored_text)


def get_color_hex():
    title = "iMColor"
    print_colored(title.center(110), 'white')
    print_colored("Right-click to copy HEX".center(110), 'cyan')
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
                print(f"Error: {e}".center(110))
    
    def on_scroll(x, y, dx, dy):
        if dy > 0:  
            color_window.mode = 'pixel'
            color_window.update_canvas_size(200, 200)
        elif dy < 0:  
            color_window.mode = 'normal'
            color_window.update_canvas_size(200, 200)

    def on_press(key):
        if key == keyboard.Key.esc:
            os._exit(0)

    with mouse.Listener(on_click=on_click, on_scroll=on_scroll) as mouse_listener, keyboard.Listener(on_press=on_press) as keyboard_listener:
        color_window.root.mainloop()


if __name__ == "__main__":
    if os.path.splitext(sys.argv[0])[1] != '.pyw':
        ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 6)
    get_color_hex()
