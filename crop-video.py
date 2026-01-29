import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import cv2
from PIL import Image, ImageTk
import threading
import os
import subprocess
import sys

class VideoCropperApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Advanced Video Cropper")
        self.root.geometry("1024x768") # Start with a decent size
        self.root.configure(bg="#2E2E2E")

        # --- State Variables ---
        self.video_path = None
        self.original_frame = None  # OpenCV (BGR) format
        self.tk_photo = None        # Tkinter PhotoImage
        self.canvas_image_id = None
        self.crop_rect_id = None
        self.crop_coords = None     # Store as (x1, y1, x2, y2)
        self.start_pos = None
        self.current_action = None # 'draw', 'move', 'resize_nw', 'resize_ne', etc.

        # --- GUI Widgets ---
        # Top Frame for controls
        top_frame = tk.Frame(root, bg="#3C3C3C", pady=5)
        top_frame.pack(fill=tk.X, side=tk.TOP)

        self.open_btn = tk.Button(top_frame, text="Open Video", command=self.open_video, bg="#555", fg="white", activebackground="#666", relief=tk.FLAT)
        self.open_btn.pack(side=tk.LEFT, padx=10)

        self.crop_btn = tk.Button(top_frame, text="Start Cropping", command=self.start_cropping_thread, bg="#007ACC", fg="white", activebackground="#005C99", relief=tk.FLAT, state=tk.DISABLED)
        self.crop_btn.pack(side=tk.LEFT, padx=10)
        
        # Canvas for video frame display
        self.canvas = tk.Canvas(root, bg="black", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Bottom Frame for status and progress
        bottom_frame = tk.Frame(root, bg="#3C3C3C", pady=5)
        bottom_frame.pack(fill=tk.X, side=tk.BOTTOM)

        self.status_label = tk.Label(bottom_frame, text="Open a video to begin.", bg="#3C3C3C", fg="white")
        self.status_label.pack(side=tk.LEFT, padx=10)

        self.progress_bar = ttk.Progressbar(bottom_frame, orient='horizontal', mode='determinate')
        self.progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)

        self.output_frame = tk.Frame(bottom_frame, bg="#3C3C3C")
        # This frame will be packed later when needed

        self.output_label = tk.Label(self.output_frame, text="", bg="#3C3C3C", fg="#A0A0A0")
        self.output_label.pack(side=tk.LEFT)
        self.play_btn = tk.Button(self.output_frame, text="Play Cropped Video", command=self.play_output, bg="#4CAF50", fg="white", activebackground="#45a049", relief=tk.FLAT)
        self.play_btn.pack(side=tk.LEFT, padx=10)
        
        # --- Bindings ---
        self.canvas.bind("<ButtonPress-1>", self.on_mouse_press)
        self.canvas.bind("<B1-Motion>", self.on_mouse_move)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_release)
        self.canvas.bind("<Motion>", self.update_cursor)
        self.root.bind("<Key>", self.on_key_press)
        self.root.bind("<Configure>", self.on_resize) # Handle window resize

    def open_video(self):
        self.video_path = filedialog.askopenfilename(filetypes=[("Video Files", "*.mp4 *.avi *.mov *.mkv")])
        if not self.video_path:
            return

        cap = cv2.VideoCapture(self.video_path)
        if not cap.isOpened():
            messagebox.showerror("Error", "Could not open video file.")
            return
        
        ret, frame = cap.read()
        cap.release()
        if not ret:
            messagebox.showerror("Error", "Could not read the first frame.")
            return

        self.original_frame = frame
        self.reset_crop()
        self.display_image()
        self.crop_btn.config(state=tk.NORMAL)
        self.status_label.config(text="Drag to draw a crop box. Use corners to resize or drag inside to move.")

    def display_image(self):
        if self.original_frame is None:
            return
        
        # Resize frame to fit canvas while maintaining aspect ratio
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        if canvas_width == 1 or canvas_height == 1: # Window not yet drawn
             canvas_width, canvas_height = 1024, 768

        h, w, _ = self.original_frame.shape
        aspect_ratio = w / h
        
        if canvas_width / aspect_ratio <= canvas_height:
            self.display_w = canvas_width
            self.display_h = int(canvas_width / aspect_ratio)
        else:
            self.display_h = canvas_height
            self.display_w = int(canvas_height * aspect_ratio)

        # Position of image on canvas (centered)
        self.img_x_offset = (canvas_width - self.display_w) // 2
        self.img_y_offset = (canvas_height - self.display_h) // 2

        # Convert OpenCV image (BGR) to Tkinter PhotoImage (RGB)
        resized_frame = cv2.resize(self.original_frame, (self.display_w, self.display_h))
        rgb_frame = cv2.cvtColor(resized_frame, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(rgb_frame)
        self.tk_photo = ImageTk.PhotoImage(image=pil_img)
        
        self.canvas.delete("all")
        self.canvas_image_id = self.canvas.create_image(self.img_x_offset, self.img_y_offset, anchor=tk.NW, image=self.tk_photo)
        
        # Redraw the crop rectangle if it exists
        if self.crop_coords:
            self.draw_crop_rect(self.crop_coords)

    def on_resize(self, event):
        # Redraw image and crop box when window is resized
        self.display_image()

    def get_action(self, event):
        """Determine what action to take based on cursor position."""
        if not self.crop_coords:
            return 'draw'

        x, y = event.x, event.y
        x1, y1, x2, y2 = self.canvas.coords(self.crop_rect_id)
        margin = 10 # Cursors change within 10px of the handles

        if (x1 - margin < x < x1 + margin) and (y1 - margin < y < y1 + margin): return 'resize_nw'
        if (x2 - margin < x < x2 + margin) and (y2 - margin < y < y2 + margin): return 'resize_se'
        if (x2 - margin < x < x2 + margin) and (y1 - margin < y < y1 + margin): return 'resize_ne'
        if (x1 - margin < x < x1 + margin) and (y2 - margin < y < y2 + margin): return 'resize_sw'
        if x1 < x < x2 and y1 < y < y2: return 'move'
        return 'draw'

    def update_cursor(self, event):
        if self.crop_rect_id:
            action = self.get_action(event)
            if 'resize' in action:
                if 'nw' in action or 'se' in action:
                    self.canvas.config(cursor="fleur")
                else:
                    self.canvas.config(cursor="fleur")
            elif action == 'move':
                self.canvas.config(cursor="fleur")
            else:
                self.canvas.config(cursor="crosshair")
        else:
            self.canvas.config(cursor="crosshair")

    def on_mouse_press(self, event):
        self.current_action = self.get_action(event)
        self.start_pos = (event.x, event.y)
        if self.current_action == 'draw':
            self.reset_crop() # Start a new crop
            self.crop_rect_id = self.canvas.create_rectangle(event.x, event.y, event.x, event.y, outline="red", width=2, dash=(4, 4))
    
    def on_mouse_move(self, event):
        if not self.start_pos:
            return

        x, y = event.x, event.y
        if self.current_action == 'draw':
            self.canvas.coords(self.crop_rect_id, self.start_pos[0], self.start_pos[1], x, y)
        elif self.current_action == 'move':
            dx, dy = x - self.start_pos[0], y - self.start_pos[1]
            self.canvas.move(self.crop_rect_id, dx, dy)
            self.start_pos = (x, y)
        elif 'resize' in self.current_action:
            x1, y1, x2, y2 = self.canvas.coords(self.crop_rect_id)
            if 'nw' in self.current_action: self.canvas.coords(self.crop_rect_id, x, y, x2, y2)
            elif 'se' in self.current_action: self.canvas.coords(self.crop_rect_id, x1, y1, x, y)
            elif 'ne' in self.current_action: self.canvas.coords(self.crop_rect_id, x1, y, x, y2)
            elif 'sw' in self.current_action: self.canvas.coords(self.crop_rect_id, x, y1, x2, y)

    def on_mouse_release(self, event):
        if self.crop_rect_id:
            # Ensure x1 < x2 and y1 < y2
            coords = list(self.canvas.coords(self.crop_rect_id))
            x1, y1, x2, y2 = coords
            coords = [min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)]
            self.canvas.coords(self.crop_rect_id, *coords)
            self.canvas.itemconfig(self.crop_rect_id, dash=()) # Make solid line
            self.crop_coords = coords
        self.start_pos = None
        self.current_action = None

    def on_key_press(self, event):
        if not self.crop_coords:
            return
        
        coords = list(self.canvas.coords(self.crop_rect_id))
        nudge = 1
        resize_nudge = 1

        if event.state & 0x1: # Shift key is pressed for resizing
            if event.keysym == "Left": coords[2] -= resize_nudge
            elif event.keysym == "Right": coords[2] += resize_nudge
            elif event.keysym == "Up": coords[3] -= resize_nudge
            elif event.keysym == "Down": coords[3] += resize_nudge
        else: # Move
            if event.keysym == "Left": coords[0] -= nudge; coords[2] -= nudge
            elif event.keysym == "Right": coords[0] += nudge; coords[2] += nudge
            elif event.keysym == "Up": coords[1] -= nudge; coords[3] -= nudge
            elif event.keysym == "Down": coords[1] += nudge; coords[3] += nudge
        
        self.draw_crop_rect(coords)

    def reset_crop(self):
        if self.crop_rect_id:
            self.canvas.delete(self.crop_rect_id)
        self.crop_rect_id = None
        self.crop_coords = None

    def draw_crop_rect(self, coords):
        if self.crop_rect_id:
            self.canvas.coords(self.crop_rect_id, *coords)
        else:
            self.crop_rect_id = self.canvas.create_rectangle(*coords, outline="red", width=2)
        self.crop_coords = coords

    def start_cropping_thread(self):
        if not self.video_path or not self.crop_coords:
            messagebox.showwarning("Warning", "Please open a video and select a crop area first.")
            return

        self.crop_btn.config(state=tk.DISABLED)
        self.open_btn.config(state=tk.DISABLED)
        self.status_label.config(text="Processing... Please wait.")
        self.output_frame.pack_forget()

        # Create and start the background thread
        thread = threading.Thread(target=self.process_video)
        thread.daemon = True
        thread.start()

    def process_video(self):
        # Convert canvas coordinates to original frame coordinates
        h, w, _ = self.original_frame.shape
        scale_x = w / self.display_w
        scale_y = h / self.display_h

        # Clamp coordinates to be within the image bounds on canvas
        c_x1 = max(self.crop_coords[0] - self.img_x_offset, 0)
        c_y1 = max(self.crop_coords[1] - self.img_y_offset, 0)
        c_x2 = min(self.crop_coords[2] - self.img_x_offset, self.display_w)
        c_y2 = min(self.crop_coords[3] - self.img_y_offset, self.display_h)

        # Final video coordinates
        x1 = int(c_x1 * scale_x)
        y1 = int(c_y1 * scale_y)
        x2 = int(c_x2 * scale_x)
        y2 = int(c_y2 * scale_y)
        
        crop_w = x2 - x1
        crop_h = y2 - y1

        if crop_w <= 0 or crop_h <= 0:
            self.root.after(0, self.cropping_finished, None, "Invalid crop dimensions.")
            return

        # Prepare video reader and writer
        cap = cv2.VideoCapture(self.video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        base, ext = os.path.splitext(self.video_path)
        self.output_path = f"{base}_cropped.mp4"
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(self.output_path, fourcc, fps, (crop_w, crop_h))
        
        self.progress_bar['maximum'] = total_frames
        
        # Process frames
        for i in range(total_frames):
            ret, frame = cap.read()
            if not ret:
                break
            cropped_frame = frame[y1:y2, x1:x2]
            out.write(cropped_frame)
            self.progress_bar['value'] = i + 1
            # self.root.update_idletasks() # Let main thread update GUI

        cap.release()
        out.release()
        
        # Schedule the finish function to run on the main thread
        self.root.after(0, self.cropping_finished, self.output_path, None)

    def cropping_finished(self, output_path, error_msg):
        self.progress_bar['value'] = 0
        self.crop_btn.config(state=tk.NORMAL)
        self.open_btn.config(state=tk.NORMAL)

        if error_msg:
            messagebox.showerror("Error", error_msg)
            self.status_label.config(text="An error occurred.")
        else:
            self.status_label.config(text="Cropping complete!")
            self.output_label.config(text=f"Saved to: {os.path.basename(output_path)}")
            self.output_frame.pack(side=tk.RIGHT, padx=10)

    def play_output(self):
        if not self.output_path or not os.path.exists(self.output_path):
            messagebox.showerror("Error", "Output file not found.")
            return
        
        # Use platform-specific command to open the file
        if sys.platform == "win32":
            os.startfile(self.output_path)
        elif sys.platform == "darwin": # macOS
            subprocess.Popen(["open", self.output_path])
        else: # linux
            subprocess.Popen(["xdg-open", self.output_path])

if __name__ == "__main__":
    root = tk.Tk()
    app = VideoCropperApp(root)
    root.mainloop()