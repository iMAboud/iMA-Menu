import requests
import os
import subprocess
import ctypes
from PIL import Image, ImageTk
import tkinter as tk
from io import BytesIO

class WallpaperManager:
    def __init__(self):
        self.search_term = ""
        self.page = 1
        self.per_page = 9
        self.client_id = "H65txLx-PMfCGiE08SCHegN7ZM7nAPtGEFOkTCRTLLM"  # Replace this with your Unsplash client ID
        self.base_url = "https://api.unsplash.com"
        self.wallpapers = []

    def search_wallpapers(self, query):
        self.search_term = query
        self.page = 1  # Reset page to 1 when searching for new wallpapers
        self.fetch_wallpapers()

    def fetch_wallpapers(self):
        url = f"{self.base_url}/search/photos/?query={self.search_term}&page={self.page}&per_page={self.per_page}&client_id={self.client_id}"
        response = requests.get(url)
        data = response.json()
        self.wallpapers = data['results']

    def set_wallpaper(self, image_url):
        response = requests.get(image_url)
        with open('temp_wallpaper.jpg', 'wb') as f:
            f.write(response.content)
        # Set wallpaper based on operating system
        if os.name == 'posix':  # For Unix/Linux based systems
            subprocess.run(["gsettings", "set", "org.gnome.desktop.background", "picture-uri", "file://" + os.path.abspath('temp_wallpaper.jpg')])
        elif os.name == 'nt':  # For Windows
            ctypes.windll.user32.SystemParametersInfoW(20, 0, os.path.abspath('temp_wallpaper.jpg') , 0)
        else:
            print("Unsupported operating system")

def set_wallpaper_and_close(image_url):
    wallpaper_manager.set_wallpaper(image_url)
    root.destroy()

def fetch_next_page():
    wallpaper_manager.page += 1
    wallpaper_manager.fetch_wallpapers()
    display_wallpapers()

def fetch_previous_page():
    if wallpaper_manager.page > 1:
        wallpaper_manager.page -= 1
        wallpaper_manager.fetch_wallpapers()
        display_wallpapers()

def display_wallpapers():
    # Clear existing buttons
    for widget in wallpaper_frame.winfo_children():
        widget.destroy()
    
    # Display new buttons
    for i, wallpaper in enumerate(wallpaper_manager.wallpapers):
        response = requests.get(wallpaper['urls']['thumb'])
        img_data = response.content
        img = Image.open(BytesIO(img_data))
        img.thumbnail((200, 200))
        img = ImageTk.PhotoImage(img)

        button = tk.Button(wallpaper_frame, image=img, command=lambda url=wallpaper['urls']['full']: set_wallpaper_and_close(url), bg="black", fg="white", activebackground="black", activeforeground="white", relief="flat", bd=0)
        button.grid(row=i // 3, column=i % 3)

        button.image = img  # Keep a reference to the image to prevent garbage collection

if __name__ == "__main__":
    wallpaper_manager = WallpaperManager()
    search_query = input("Wallpaper: ")
    wallpaper_manager.search_wallpapers(search_query)

    root = tk.Tk()
    root.title("Wallpaper Selector")
    root.config(bg="black")

    wallpaper_frame = tk.Frame(root, bg="black")
    wallpaper_frame.pack(pady=10)

    navigation_frame = tk.Frame(root, bg="black")
    navigation_frame.pack()

    display_wallpapers()

    previous_button = tk.Button(navigation_frame, text="Previous", command=fetch_previous_page, bg="black", fg="white", activebackground="black", activeforeground="white", relief="flat", bd=0)
    previous_button.grid(row=0, column=0)

    next_button = tk.Button(navigation_frame, text="Next", command=fetch_next_page, bg="black", fg="white", activebackground="black", activeforeground="white", relief="flat", bd=0)
    next_button.grid(row=0, column=1)

    root.mainloop()
