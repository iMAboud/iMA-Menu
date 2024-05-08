import tkinter as tk
from tkinter import filedialog
from moviepy.video.io.VideoFileClip import VideoFileClip

class VideoTrimmer:
    def __init__(self, root):
        self.root = root
        self.root.title("Video Trimmer")
        self.root.geometry("600x400")

        self.file_path = None
        self.clip = None
        self.start_time = 0
        self.end_time = 0

        self.create_widgets()

    def create_widgets(self):
        self.select_button = tk.Button(self.root, text="Select Video", command=self.select_video)
        self.select_button.pack(pady=10)

        self.trim_button = tk.Button(self.root, text="Trim Video", command=self.trim_video)
        self.trim_button.pack(pady=10)

        self.canvas = tk.Canvas(self.root, bg="black", width=600, height=300)
        self.canvas.pack()

        self.canvas.bind("<Button-1>", self.set_start_time)
        self.canvas.bind("<ButtonRelease-1>", self.set_end_time)

    def select_video(self):
        self.file_path = filedialog.askopenfilename(title="Select Video File", filetypes=[("Video files", "*.mp4 *.avi *.mkv")])
        self.clip = VideoFileClip(self.file_path)
        self.clip_duration = self.clip.duration
        self.update_canvas()

    def update_canvas(self):
        self.canvas.delete("all")
        self.canvas.create_rectangle(0, 0, 600, 300, outline="white")
        self.canvas.create_line(self.start_time / self.clip_duration * 600, 0, self.start_time / self.clip_duration * 600, 300, fill="red")
        self.canvas.create_line(self.end_time / self.clip_duration * 600, 0, self.end_time / self.clip_duration * 600, 300, fill="red")

    def set_start_time(self, event):
        self.start_time = event.x / 600 * self.clip_duration
        self.update_canvas()

    def set_end_time(self, event):
        self.end_time = event.x / 600 * self.clip_duration
        self.update_canvas()

    def trim_video(self):
        if self.file_path is None:
            tk.messagebox.showerror("Error", "No video selected!")
            return

        trimmed_clip = self.clip.subclip(self.start_time, self.end_time)
        trimmed_clip.write_videofile("trimmed_video.mp4", codec="libx264")
        tk.messagebox.showinfo("Success", "Video trimmed successfully!")

if __name__ == "__main__":
    root = tk.Tk()
    app = VideoTrimmer(root)
    root.mainloop()
