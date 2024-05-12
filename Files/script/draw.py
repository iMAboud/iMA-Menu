import tkinter as tk
from tkinter import colorchooser, ttk
import ctypes

class DrawingApp:
    def __init__(self, master):
        self.master = master
        self.master.attributes('-fullscreen', True)
        self.master.attributes('-topmost', True)
        self.master.attributes('-alpha', 0.7)  # Set transparency for drawing window
        self.master.configure(bg='black')

        # Hide the console window
        ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)

        self.color = 'white'
        self.opacity = 0.7
        self.size = 5
        self.brushes = ['Circle']
        self.selected_brush = tk.StringVar(value=self.brushes[0])
        self.prev_coords = None
        self.color_history = []
        self.action_history = []
        self.redo_history = []
        self.is_drawing = False  # Flag to indicate if drawing is in progress

        self.canvas = tk.Canvas(master, bg='black', highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.init_widgets()

        self.canvas.bind('<Button-1>', self.start_draw)
        self.canvas.bind('<B1-Motion>', self.draw_smooth)
        self.canvas.bind('<ButtonRelease-1>', self.stop_draw)
        self.canvas.bind('<ButtonPress-3>', self.open_color_picker)
        self.canvas.bind("<MouseWheel>", self.on_mousewheel)
        self.master.bind('<Control-z>', self.undo)
        self.master.bind('<Control-y>', self.redo)

        self.master.bind('<Escape>', self.quit)

    def init_widgets(self):
        controls_frame = tk.Frame(self.master, bg='black')
        controls_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)

        size_label = tk.Label(controls_frame, text="Size:", bg='black', fg='white')
        size_label.grid(row=0, column=0, padx=5, pady=5)

        self.size_scale = tk.Scale(controls_frame, from_=1, to=20, orient=tk.HORIZONTAL, command=self.change_size)
        self.size_scale.set(self.size)
        self.size_scale.grid(row=0, column=1, padx=5, pady=5)

        opacity_label = tk.Label(controls_frame, text="Opacity:", bg='black', fg='white')
        opacity_label.grid(row=0, column=2, padx=5, pady=5)

        self.opacity_scale = tk.Scale(controls_frame, from_=0, to=1, resolution=0.1, orient=tk.HORIZONTAL, command=self.change_opacity)
        self.opacity_scale.set(self.opacity)
        self.opacity_scale.grid(row=0, column=3, padx=5, pady=5)

        reset_button = tk.Button(controls_frame, text="Reset", command=self.reset_settings)
        reset_button.grid(row=0, column=4, padx=5, pady=5)

    def start_draw(self, event):
        self.is_drawing = True

    def stop_draw(self, event):
        self.is_drawing = False
        self.prev_coords = None  # Reset previous coordinates

    def draw_smooth(self, event):
        if self.is_drawing:
            x, y = event.x, event.y
            if self.prev_coords:
                points = self.get_line(self.prev_coords[0], self.prev_coords[1], x, y)
                for point in points[::2]:  # Sample every 2nd point
                    self.canvas.create_oval(point[0], point[1], point[0], point[1], fill=self.color, outline=self.color, width=self.size)
                    self.action_history.append((point[0], point[1], self.size, self.color))
            self.prev_coords = (x, y)
            self.curr_state = self.get_canvas_data()  # Capture state after drawing

    def get_line(self, x0, y0, x1, y1):
        """Bresenham's Line Algorithm"""
        points = []
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy

        while True:
            points.append((x0, y0))
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x0 += sx
            if e2 < dx:
                err += dx
                y0 += sy
        return points

    def open_color_picker(self, event):
        if event.num == 3:  # Right click
            self.pick_color()

    def pick_color(self):
        self.pick_color_window = tk.Toplevel(self.master)
        self.pick_color_window.attributes('-topmost', True)
        self.pick_color_window.geometry('200x200')
        self.pick_color_window.configure(bg='black')
        color = colorchooser.askcolor(title="Pick a color", color=self.color)[1]
        if color:
            self.color = color
            self.color_history.append(color)
        self.pick_color_window.destroy()

    def on_mousewheel(self, event):
        if event.delta > 0:
            self.opacity += 0.1
        else:
            self.opacity = max(0.1, self.opacity - 0.1)
        self.update_opacity()

    def update_opacity(self):
        self.opacity_scale.set(self.opacity)
        self.master.attributes('-alpha', self.opacity)

    def change_opacity(self, value):
        self.opacity = float(value)
        self.update_opacity()

    def change_size(self, value):
        self.size = int(value)

    def reset_settings(self):
        self.size = 5
        self.size_scale.set(self.size)
        self.opacity = 0.7
        self.update_opacity()
        self.prev_state = None  # Stores previous canvas data for undo
        self.curr_state = None  # Stores current canvas data for redo

    def undo(self, event):
        if self.action_history:
            self.redo_history.append(self.action_history.pop())
            self.canvas.delete('all')
            for action in self.action_history:
                x, y, size, color = action
                self.canvas.create_oval(x - size, y - size, x + size, y + size, fill=color, outline=color)

    def redo(self, event):
        if self.redo_history:
            action = self.redo_history.pop()
            self.action_history.append(action)
            x, y, size, color = action
            self.canvas.create_oval(x - size, y - size, x + size, y + size, fill=color, outline=color)

    def quit(self, event=None):
        self.master.quit()

if __name__ == "__main__":
    root = tk.Tk()
    app = DrawingApp(root)
    root.mainloop()
