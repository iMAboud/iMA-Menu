import tkinter as tk
from tkinter import colorchooser
import ctypes
import random
from PIL import Image, ImageDraw, ImageTk
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ICONS_PATH = os.path.join(os.path.dirname(BASE_DIR), "script", "draw-icons")

class DrawingApp:
    def __init__(self, master):
        self.master = master
        self.icons_path = ICONS_PATH
        master.attributes('-fullscreen', True, '-topmost', True, '-alpha', 0.7)
        master.configure(bg='black')
        ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)

        self.color = 'white'
        self.size = 5
        self.start_coords = None
        self.prev_coords = None
        self.color_history = []
        self.action_history = []
        self.redo_history = []
        self.is_drawing = False
        self.erase_mode = False
        self.mirror_mode = False
        self.drawing_tool = 'brush'
        self.opacity = 0.7
        self.current_stroke = []
        self.random_color_mode = False
        self.preview_shape = None
        self.color_picker_window = None  # Store the color picker window

        self.bg_canvas = tk.Canvas(master, bg='black', highlightthickness=0)
        self.bg_canvas.pack(fill=tk.BOTH, expand=True)
        self.draw_canvas = tk.Canvas(self.bg_canvas, bg='black', highlightthickness=0)
        self.draw_canvas.pack(fill=tk.BOTH, expand=True)

        self.controls_frame = self._init_controls()  # Store the controls frame
        self.controls_frame.place(x=-100, y=10)  # Initially hidden offscreen
        self.hide_timer = None  # Store hide timer
        self._bind_events()
        self.master.bind("<Motion>", self._check_mouse_position)
        self.master.bind("<Button-1>", self._check_drag_start)
        self.master.bind("<ButtonRelease-1>", self._check_drag_end)
        self.is_dragging = False


    def _check_drag_start(self, event):
        self.is_dragging = True

    def _check_drag_end(self, event):
      self.is_dragging = False

    def _check_mouse_position(self, event):
      if self.is_dragging:
        return
      if event.x <= 5 or self._is_mouse_over_controls(event):
        self._show_controls()
      elif self.controls_frame.winfo_x() == 0:
        self._hide_controls()

    def _is_mouse_over_controls(self, event):
      if self.controls_frame.winfo_x() != 0:
         return False
      x, y = event.x, event.y
      ctrl_x, ctrl_y = self.controls_frame.winfo_x(), self.controls_frame.winfo_y()
      width, height = self.controls_frame.winfo_width(), self.controls_frame.winfo_height()
      return ctrl_x <= x <= ctrl_x + width and ctrl_y <= y <= ctrl_y + height

    def _init_controls(self):
        controls_frame = tk.Frame(self.master, bg='black')

        tools = {
            'brush': 'Brush', 'circle': 'Circle', 'square': 'Square', 'line': 'Line'
        }
        self.tool_buttons = {}
        for i, (tool, text) in enumerate(tools.items()):
            self.tool_buttons[tool] = self._create_icon_button(controls_frame, tool, text, lambda t=tool: self._set_tool(t))
            self.tool_buttons[tool].pack(padx=5, pady=5, fill='x')

        tk.Label(controls_frame, text="Size:", bg='black', fg='white').pack(padx=5, pady=5, fill='x')
        self.size_scale = tk.Scale(controls_frame, from_=1, to=100, orient=tk.VERTICAL, command=self._change_size, length=100, showvalue=1, sliderlength=15, highlightthickness=0, troughcolor='black', fg='white', bg='black')
        self.size_scale.set(self.size)
        self.size_scale.pack(padx=5, pady=5, fill='x')

        self.erase_button = self._create_icon_button(controls_frame, 'erase', "Erase", self._toggle_erase_mode)
        self.erase_button.pack(padx=5, pady=5, fill='x')
        self.mirror_button = self._create_icon_button(controls_frame, 'mirror', "Mirror", self._toggle_mirror_mode)
        self.mirror_button.pack(padx=5, pady=5, fill='x')
        self.random_color_button = self._create_icon_button(controls_frame, 'random', "RANDOM", self._toggle_random_color_mode)
        self.random_color_button.pack(padx=5, pady=5, fill='x')

        self._create_icon_button(controls_frame, 'clear', "Clear All", self._clear_all).pack(padx=5, pady=5, fill='x')
        self._create_icon_button(controls_frame, 'save', "Save", self._save_options).pack(padx=5, pady=5, fill='x')
        return controls_frame

    def _show_controls(self, event=None):
        if self.hide_timer:
            self.master.after_cancel(self.hide_timer)
            self.hide_timer = None
        self.controls_frame.place(x=0, y=10)

    def _hide_controls(self, event=None):
        self.hide_timer = self.master.after(1000, self._animate_hide_controls)

    def _animate_hide_controls(self):
        start_x = self.controls_frame.winfo_x()
        end_x = -self.controls_frame.winfo_width()
        def animate_step(x):
            if x > end_x:
                self.controls_frame.place(x=x)
                self.master.after(20, lambda: animate_step(x - 15))
            else:
                self.controls_frame.place(x=end_x, y=10)
        animate_step(start_x)

    def _create_icon_button(self, parent, icon_name, text, command):
        icon_path = os.path.join(self.icons_path, f'{icon_name}.ico')
        try:
            icon = ImageTk.PhotoImage(Image.open(icon_path))
            btn = tk.Button(parent, image=icon, command=lambda: [command(), self.draw_canvas.focus_set()], bg='black', relief=tk.FLAT, bd=0)
            btn.image = icon
        except Exception:
            btn = tk.Button(parent, text=text, command=lambda: [command(), self.draw_canvas.focus_set()], bg='black', relief=tk.FLAT, bd=0)
        return btn

    def _bind_events(self):
        self.draw_canvas.bind('<Button-1>', self._start_draw)
        self.draw_canvas.bind('<B1-Motion>', self._draw)
        self.draw_canvas.bind('<ButtonRelease-1>', self._stop_draw)
        self.draw_canvas.bind('<ButtonPress-3>', self._open_color_picker)
        self.master.bind('<Control-z>', self._undo)
        self.master.bind('<Control-y>', self._redo)
        self.master.bind('<Escape>', self._quit)
        self.master.bind('<MouseWheel>', self._on_mousewheel)

    def _set_tool(self, tool):
        self.drawing_tool = tool
        for t, button in self.tool_buttons.items():
            button.configure(bg='green' if t == tool else 'SystemButtonFace')

    def _toggle_erase_mode(self):
        self.erase_mode = not self.erase_mode
        self.color = 'black' if self.erase_mode else self.color_history[-1] if self.color_history else 'white'
        self.erase_button.configure(bg='green' if self.erase_mode else 'SystemButtonFace')

    def _toggle_mirror_mode(self):
        self.mirror_mode = not self.mirror_mode
        self.mirror_button.configure(bg='green' if self.mirror_mode else 'SystemButtonFace')

    def _toggle_random_color_mode(self):
        self.random_color_mode = not self.random_color_mode
        self.random_color_button.configure(bg='green' if self.random_color_mode else 'SystemButtonFace')

    def _start_draw(self, event):
        if self.random_color_mode:
            self.color = "#{:06x}".format(random.randint(0, 0xFFFFFF))
            self.color_history.append(self.color)
        self.is_drawing = True
        self.start_coords = event.x, event.y
        self.prev_coords = event.x, event.y
        self.preview_shape = None
        self.current_stroke = []

    def _draw(self, event):
        if self.is_drawing:
            x, y = event.x, event.y
            if self.preview_shape:
                self.draw_canvas.delete(self.preview_shape)
            draw_func = getattr(self, f'_draw_{self.drawing_tool}')
            self.preview_shape = draw_func(self.start_coords, (x, y), preview=True) if self.drawing_tool != 'brush' else self._draw_brush(self.prev_coords, (x,y))
            if self.drawing_tool == 'brush':
                self.prev_coords = (x, y)

    def _stop_draw(self, event):
        self.is_drawing = False
        end_coords = event.x, event.y
        if self.preview_shape:
            self.draw_canvas.delete(self.preview_shape)
        if self.start_coords and end_coords:
            draw_func = getattr(self, f'_draw_{self.drawing_tool}')
            if self.drawing_tool == 'brush':
                self._draw_brush(self.prev_coords, end_coords)
                self.action_history.append(('brush_stroke', self.current_stroke))
            else:
                draw_func(self.start_coords, end_coords)

        self.start_coords = None
        self.prev_coords = None
        self.preview_shape = None

    def _draw_line(self, start, end, preview=False):
        line = self.draw_canvas.create_line(*start, *end, fill=self.color, width=self.size, tags='preview' if preview else '')
        if not preview:
            self.action_history.append(('line', start, end, self.size, self.color))
            if self.mirror_mode:
                mirror_start = (self.draw_canvas.winfo_width() - start[0], start[1])
                mirror_end = (self.draw_canvas.winfo_width() - end[0], end[1])
                self.action_history.append(('line', mirror_start, mirror_end, self.size, self.color))
        return line

    def _draw_circle(self, start, end, preview=False):
        x0, y0 = start
        x1, y1 = end
        r = ((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5
        circle = self.draw_canvas.create_oval(x0 - r, y0 - r, x0 + r, y0 + r, outline=self.color, width=self.size, tags='preview' if preview else '')
        if not preview:
            self.action_history.append(('circle', start, r, self.size, self.color))
            if self.mirror_mode:
                mirror_start = (self.draw_canvas.winfo_width() - start[0], start[1])
                self.action_history.append(('circle', mirror_start, r, self.size, self.color))
        return circle

    def _draw_square(self, start, end, preview=False):
        x0, y0 = start
        x1, y1 = end
        x2, y2 = (x0 - abs(x1 - x0) if x1 < x0 else x0 + abs(x1 - x0)), (y0 - abs(y1 - y0) if y1 < y0 else y0 + abs(y1 - y0))
        square = self.draw_canvas.create_rectangle(x0, y0, x2, y2, outline=self.color, width=self.size, tags='preview' if preview else '')
        if not preview:
            self.action_history.append(('square', start, (x2, y2), self.size, self.color))
            if self.mirror_mode:
                mirror_start = (self.draw_canvas.winfo_width() - start[0], start[1])
                mirror_end = (self.draw_canvas.winfo_width() - x2, y2)
                self.action_history.append(('square', mirror_start, mirror_end, self.size, self.color))
        return square

    def _draw_brush(self, start, end):
        x0, y0 = start
        x1, y1 = end
        for point in self._get_line(x0, y0, x1, y1)[::2]:
            x, y = point
            item = self.draw_canvas.create_oval(x - self.size, y - self.size, x + self.size, y + self.size, fill=self.color, outline=self.color, width=self.size)
            self.current_stroke.append((x, y, self.size, self.color))
            if self.mirror_mode:
                mx = self.draw_canvas.winfo_width() - x
                self.draw_canvas.create_oval(mx - self.size, y - self.size, mx + self.size, y + self.size, fill=self.color, outline=self.color, width=self.size)
                self.current_stroke.append((mx, y, self.size, self.color))
        return None

    def _get_line(self, x0, y0, x1, y1):
        points = []
        dx, dy = abs(x1 - x0), abs(y1 - y0)
        sx, sy = 1 if x0 < x1 else -1, 1 if y0 < y1 else -1
        err = dx - dy
        while True:
            points.append((x0, y0))
            if x0 == x1 and y0 == y1: break
            e2 = 2 * err
            if e2 > -dy: err -= dy; x0 += sx
            if e2 < dx: err += dx; y0 += sy
        return points

    def _open_color_picker(self, event):
        if event.num == 3:
            self._pick_color()

    def _pick_color(self):
        color_data = colorchooser.askcolor(title="Pick a color", color=self.color)
        if color_data and color_data[1]:
            self.color = color_data[1]
            self.color_history.append(self.color)


    def _change_size(self, value):
        self.size = int(value)

    def _clear_all(self):
        self.draw_canvas.delete('all')
        self.action_history.clear()
        self.redo_history.clear()

    def _undo(self, event):
        if self.action_history:
            self.redo_history.append(self.action_history.pop())
            self._redraw_canvas()

    def _redo(self, event):
        if self.redo_history:
            self.action_history.append(self.redo_history.pop())
            self._redraw_canvas()

    def _redraw_canvas(self):
        self.draw_canvas.delete('all')
        for action_type, *params in self.action_history:
            if action_type == 'line':
                self.draw_canvas.create_line(*params[0], *params[1], fill=params[4], width=params[3])
            elif action_type == 'circle':
                x0, y0 = params[0]
                r = params[1]
                self.draw_canvas.create_oval(x0 - r, y0 - r, x0 + r, y0 + r, outline=params[4], width=params[3])
            elif action_type == 'square':
                self.draw_canvas.create_rectangle(*params[0], *params[1], outline=params[4], width=params[3])
            elif action_type == 'brush_stroke':
                for x, y, size, color in params[0]:
                    self.draw_canvas.create_oval(x - size, y - size, x + size, y + size, fill=color, outline=color)

    def _on_mousewheel(self, event):
        delta = 0.1 if event.delta > 0 else -0.2
        self.opacity = max(0.01, min(1.0, self.opacity + delta))
        self.master.attributes('-alpha', self.opacity)

    def _save_options(self):
        win = tk.Toplevel(self.master)
        win.title("Save Options")
        win.transient(self.master)
        win.grab_set()
        win.focus_set()
        tk.Button(win, text="Save PNG (Transparent)", command=self._save_png_transparent).pack(padx=20, pady=10)
        tk.Button(win, text="Save PNG (White Background)", command=self._save_png_white).pack(padx=20, pady=10)

    def _save_png_transparent(self):
        self._save_image(background='transparent')

    def _save_png_white(self):
        self._save_image(background='white')

    def _save_image(self, background='transparent'):
        x, y = self.master.winfo_rootx() + self.draw_canvas.winfo_x(), self.master.winfo_rooty() + self.draw_canvas.winfo_y()
        width, height = self.draw_canvas.winfo_width(), self.draw_canvas.winfo_height()
        self.master.withdraw()
        self.master.update_idletasks()
        image = Image.new('RGBA', (width, height), (0, 0, 0, 0) if background == 'transparent' else (255, 255, 255, 255))
        draw = ImageDraw.Draw(image)
        for action_type, *params in self.action_history:
            if action_type == 'line':
                draw.line(params[0] + params[1], fill=params[4], width=params[3])
            elif action_type == 'circle':
                x0, y0, r, size, color = params
                draw.ellipse((x0 - r, y0 - r, x0 + r, y0 + r), outline=color, width=size)
            elif action_type == 'square':
                draw.rectangle(params[0] + params[1], outline=params[4], width=params[3])
            elif action_type == 'brush_stroke':
                for x, y, size, color in params[0]:
                    draw.ellipse((x - size, y - size, x + size, y + size), fill=color, outline=color)
        image.save('drawing.png')
        self.master.deiconify()

    def _quit(self, event=None):
        self.master.quit()

if __name__ == "__main__":
    root = tk.Tk()
    DrawingApp(root)
    root.mainloop()
