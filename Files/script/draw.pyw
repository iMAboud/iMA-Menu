import tkinter as tk
from tkinter import colorchooser
import ctypes
import random

class DrawingApp:
    def __init__(self, master):
        self.master = master
        self.master.attributes('-fullscreen', True)
        self.master.attributes('-topmost', True)
        self.master.attributes('-alpha', 0.7)
        self.master.configure(bg='black')

        ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)

        self.color = 'white'
        self.size = 5
        self.prev_coords = None
        self.color_history = []
        self.action_history = []
        self.redo_history = []
        self.is_drawing = False
        self.erase_mode = False
        self.mirror_mode = False
        self.drawing_tool = 'brush'  # Set default tool to brush
        self.opacity = 0.7
        self.current_stroke = []
        self.random_color_mode = False

        self.bg_canvas = tk.Canvas(master, bg='black', highlightthickness=0)
        self.bg_canvas.pack(fill=tk.BOTH, expand=True)

        self.draw_canvas = tk.Canvas(self.bg_canvas, bg='black', highlightthickness=0)
        self.draw_canvas.pack(fill=tk.BOTH, expand=True)

        self.init_widgets()

        self.draw_canvas.bind('<Button-1>', self.start_draw)
        self.draw_canvas.bind('<B1-Motion>', self.draw)
        self.draw_canvas.bind('<ButtonRelease-1>', self.stop_draw)
        self.draw_canvas.bind('<ButtonPress-3>', self.open_color_picker)
        self.master.bind('<Control-z>', self.undo)
        self.master.bind('<Control-y>', self.redo)
        self.master.bind('<Escape>', self.quit)
        self.master.bind('<MouseWheel>', self.on_mousewheel)

    def init_widgets(self):
        controls_frame = tk.Frame(self.master, bg='black')
        controls_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)

        self.brush_button = tk.Button(controls_frame, text="Brush", command=lambda: self.set_tool('brush'))
        self.brush_button.grid(row=0, column=1, padx=5, pady=5)

        self.circle_button = tk.Button(controls_frame, text="Circle", command=lambda: self.set_tool('circle'))
        self.circle_button.grid(row=0, column=2, padx=5, pady=5)
        
        self.square_button = tk.Button(controls_frame, text="Square", command=lambda: self.set_tool('square'))
        self.square_button.grid(row=0, column=3, padx=5, pady=5)

        self.line_button = tk.Button(controls_frame, text="Line", command=lambda: self.set_tool('line'))
        self.line_button.grid(row=0, column=4, padx=5, pady=5)
        
        size_label = tk.Label(controls_frame, text="Size:", bg='black', fg='white')
        size_label.grid(row=0, column=5, padx=5, pady=5)

        self.size_scale = tk.Scale(controls_frame, from_=1, to=100, orient=tk.HORIZONTAL, command=self.change_size)
        self.size_scale.set(self.size)
        self.size_scale.grid(row=0, column=6, padx=5, pady=5)

        self.erase_button = tk.Button(controls_frame, text="Erase", command=self.toggle_erase_mode)
        self.erase_button.grid(row=0, column=7, padx=5, pady=5)

        self.mirror_button = tk.Button(controls_frame, text="Mirror", command=self.toggle_mirror_mode)
        self.mirror_button.grid(row=0, column=8, padx=5, pady=5)


        self.random_color_button = self.create_rainbow_button(controls_frame, "RANDOM", self.toggle_random_color_mode)
        self.random_color_button.grid(row=0, column=9, padx=5, pady=5)


        clear_button = tk.Button(controls_frame, text="Clear All", command=self.clear_all, bg='red')
        clear_button.grid(row=0, column=10, padx=5, pady=5)


    def create_rainbow_button(self, parent, text, command):
        colors = ["red", "orange", "green", "yellow", "brown", "indigo", "violet"]
        canvas = tk.Canvas(parent, width=100, height=30, bg='black', highlightthickness=0)
        x = 5
        for i, char in enumerate(text):
            canvas.create_text(x, 15, text=char, fill=colors[i % len(colors)], font=("Arial", 10, "bold"))
            x += 10
        canvas.bind("<Button-1>", lambda e: command())
        return canvas
    
    def set_tool(self, tool):
        self.drawing_tool = tool
        self.brush_button.configure(bg='green' if tool == 'brush' else 'SystemButtonFace')
        self.line_button.configure(bg='green' if tool == 'line' else 'SystemButtonFace')
        self.circle_button.configure(bg='green' if tool == 'circle' else 'SystemButtonFace')
        self.square_button.configure(bg='green' if tool == 'square' else 'SystemButtonFace')

    def toggle_erase_mode(self):
        self.erase_mode = not self.erase_mode
        if self.erase_mode:
            self.color = 'black'
            self.erase_button.configure(bg='green')
        else:
            self.color = self.color_history[-1] if self.color_history else 'white'
            self.erase_button.configure(bg='SystemButtonFace')

    def toggle_mirror_mode(self):
        self.mirror_mode = not self.mirror_mode
        if self.mirror_mode:
            self.mirror_button.configure(bg='green')
        else:
            self.mirror_button.configure(bg='SystemButtonFace')

    def toggle_random_color_mode(self):
        self.random_color_mode = not self.random_color_mode
        if self.random_color_mode:
            self.random_color_button.configure(bg='green')
        else:
            self.random_color_button.configure(bg='SystemButtonFace')

    def start_draw(self, event):
        if self.random_color_mode:
            self.color = "#{:06x}".format(random.randint(0, 0xFFFFFF))
            self.color_history.append(self.color)
        self.is_drawing = True
        self.start_coords = (event.x, event.y)
        self.prev_coords = (event.x, event.y)
        self.preview_shape = None
        self.current_stroke = []

    def draw(self, event):
        if self.is_drawing:
            x, y = event.x, event.y

            if self.preview_shape:
                self.draw_canvas.delete(self.preview_shape)

            if self.drawing_tool == 'brush':
                self.draw_brush(self.prev_coords, (x, y))
                self.prev_coords = (x, y)
            elif self.drawing_tool == 'line':
                self.preview_shape = self.draw_line(self.start_coords, (x, y), preview=True)
            elif self.drawing_tool == 'circle':
                self.preview_shape = self.draw_circle(self.start_coords, (x, y), preview=True)
            elif self.drawing_tool == 'square':
                self.preview_shape = self.draw_square(self.start_coords, (x, y), preview=True)

    def stop_draw(self, event):
        self.is_drawing = False
        end_coords = (event.x, event.y)

        if self.preview_shape:
            self.draw_canvas.delete(self.preview_shape)

        if self.start_coords and end_coords:
            if self.drawing_tool == 'line':
                self.draw_line(self.start_coords, end_coords)
            elif self.drawing_tool == 'circle':
                self.draw_circle(self.start_coords, end_coords)
            elif self.drawing_tool == 'square':
                self.draw_square(self.start_coords, end_coords)
            elif self.drawing_tool == 'brush':
                self.draw_brush(self.prev_coords, end_coords)
                self.action_history.append(('brush_stroke', self.current_stroke))

        self.start_coords = None
        self.prev_coords = None
        self.preview_shape = None

    def draw_line(self, start, end, preview=False):
        tags = 'preview' if preview else ''
        line = self.draw_canvas.create_line(start[0], start[1], end[0], end[1], fill=self.color, width=self.size, tags=tags)
        if not preview:
            self.action_history.append(('line', start, end, self.size, self.color))
            if self.mirror_mode:
                self.action_history.append(('line', (self.draw_canvas.winfo_width() - start[0], start[1]), (self.draw_canvas.winfo_width() - end[0], end[1]), self.size, self.color))
        return line

    def draw_circle(self, start, end, preview=False):
        tags = 'preview' if preview else ''
        x0, y0 = start
        x1, y1 = end
        r = ((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5
        circle = self.draw_canvas.create_oval(x0 - r, y0 - r, x0 + r, y0 + r, outline=self.color, width=self.size, tags=tags)
        if not preview:
            self.action_history.append(('circle', start, r, self.size, self.color))
            if self.mirror_mode:
                self.action_history.append(('circle', (self.draw_canvas.winfo_width() - x0, y0), r, self.size, self.color))
        return circle

    def draw_square(self, start, end, preview=False):
        tags = 'preview' if preview else ''
        x0, y0 = start
        x1, y1 = end
        side_x = abs(x1 - x0)
        side_y = abs(y1 - y0)
        x2 = x0 - side_x if x1 < x0 else x0 + side_x
        y2 = y0 - side_y if y1 < y0 else y0 + side_y
        square = self.draw_canvas.create_rectangle(x0, y0, x2, y2, outline=self.color, width=self.size, tags=tags)
        if not preview:
            self.action_history.append(('square', start, (x2, y2), self.size, self.color))
            if self.mirror_mode:
                self.action_history.append(('square', (self.draw_canvas.winfo_width() - x0, y0), (self.draw_canvas.winfo_width() - x2, y2), self.size, self.color))
        return square

    def draw_brush(self, start, end):
        x0, y0 = start
        x1, y1 = end
        points = self.get_line(x0, y0, x1, y1)
        for point in points[::2]:
            self.draw_canvas.create_oval(point[0] - self.size, point[1] - self.size, point[0] + self.size, point[1] + self.size, fill=self.color, outline=self.color, width=self.size)
            self.current_stroke.append((point[0], point[1], self.size, self.color))
            if self.mirror_mode:
                mirrored_x = self.draw_canvas.winfo_width() - point[0]
                self.draw_canvas.create_oval(mirrored_x - self.size, point[1] - self.size, mirrored_x + self.size, point[1] + self.size, fill=self.color, outline=self.color, width=self.size)
                self.current_stroke.append((mirrored_x, point[1], self.size, self.color))

    def get_line(self, x0, y0, x1, y1):
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
        if event.num == 3:
            self.pick_color()

    def pick_color(self):
        color = colorchooser.askcolor(title="Pick a color", color=self.color)[1]
        if color:
            self.color = color
            self.color_history.append(color)

    def randomize_color(self):
        self.color = "#{:06x}".format(random.randint(0, 0xFFFFFF))
        self.color_history.append(self.color)

    def change_size(self, value):
        self.size = int(value)


    def clear_all(self):
        self.draw_canvas.delete('all')
        self.action_history.clear()
        self.redo_history.clear()

    def undo(self, event):
        if self.action_history:
            self.redo_history.append(self.action_history.pop())
            self.redraw_canvas()

    def redo(self, event):
        if self.redo_history:
            self.action_history.append(self.redo_history.pop())
            self.redraw_canvas()

    def redraw_canvas(self):
        self.draw_canvas.delete('all')
        for action in self.action_history:
            tool = action[0]
            if tool == 'line':
                _, start, end, size, color = action
                self.draw_canvas.create_line(start[0], start[1], end[0], end[1], fill=color, width=size)
            elif tool == 'circle':
                _, start, r, size, color = action
                self.draw_canvas.create_oval(start[0] - r, start[1] - r, start[0] + r, start[1] + r, outline=color, width=size)
            elif tool == 'square':
                _, start, end, size, color = action
                self.draw_canvas.create_rectangle(start[0], start[1], end[0], end[1], outline=color, width=size)
            elif tool == 'brush_stroke':
                for point in action[1]:
                    x, y, size, color = point
                    self.draw_canvas.create_oval(x - size, y - size, x + size, y + size, fill=color, outline=color)

    def on_mousewheel(self, event):
        if event.delta > 0:
            self.opacity += 0.1
        else:
            self.opacity = max(0.1, self.opacity - 0.1)
        self.update_opacity()

    def update_opacity(self):
        self.master.attributes('-alpha', self.opacity)

    def quit(self, event=None):
        self.master.quit()

if __name__ == "__main__":
    root = tk.Tk()
    app = DrawingApp(root)
    root.mainloop()
