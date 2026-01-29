import os
import cv2
import tkinter as tk
from tkinter import filedialog, messagebox

class MP4FrameExtractor:
    def __init__(self, master):
        self.master = master
        master.title("MP4 Frame Extractor")
        master.geometry("500x300")
        
        self.input_file = ""
        self.output_dir = r"C:\- AI NEW CONTENT"

        # Label & Browse Button
        self.label_select = tk.Label(master, text="Select an MP4 file:")
        self.label_select.pack(pady=(10, 5))

        self.btn_browse = tk.Button(master, text="Browse", command=self.browse_file)
        self.btn_browse.pack()

        self.label_file = tk.Label(master, text="No file selected", fg="blue")
        self.label_file.pack(pady=(5, 10))

        # FPS Entry
        self.label_fps = tk.Label(master, text="Enter FPS for extraction (leave blank for ALL frames):")
        self.label_fps.pack()

        self.entry_fps = tk.Entry(master, width=10)
        self.entry_fps.pack(pady=(5, 10))

        # Extract Button
        self.btn_extract = tk.Button(master, text="Extract Frames", command=self.extract_frames)
        self.btn_extract.pack(pady=(10, 5))

        # Status Label
        self.label_status = tk.Label(master, text="")
        self.label_status.pack(pady=(10, 5))

    def browse_file(self):
        file_path = filedialog.askopenfilename(
            title="Select an MP4 file",
            filetypes=[("MP4 files", "*.mp4"), ("All files", "*.*")]
        )
        if file_path:
            self.input_file = file_path
            self.label_file.config(text=os.path.basename(file_path))

    def extract_frames(self):
        if not self.input_file:
            messagebox.showerror("Error", "No MP4 file selected.")
            return

        os.makedirs(self.output_dir, exist_ok=True)
        cap = cv2.VideoCapture(self.input_file)

        # Get video properties
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))  # Total number of frames
        original_fps = cap.get(cv2.CAP_PROP_FPS)  # Original FPS
        video_duration = total_frames / original_fps  # Duration in seconds

        # Get FPS input
        fps_value = self.entry_fps.get().strip()
        try:
            output_fps = float(fps_value) if fps_value else original_fps  # Default to original FPS if blank
        except ValueError:
            messagebox.showerror("Error", "Invalid FPS value. Please enter a number.")
            return

        # Calculate frame interval (how often we extract frames)
        frame_interval = int(original_fps / output_fps) if output_fps < original_fps else 1

        frame_count = 0
        saved_count = 0

        self.label_status.config(text=f"Video has {total_frames} frames, {video_duration:.2f} seconds long.\nExtracting frames...")
        self.master.update_idletasks()

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            if frame_count % frame_interval == 0:
                frame_path = os.path.join(self.output_dir, f"frame_{saved_count:05d}.png")
                cv2.imwrite(frame_path, frame)
                saved_count += 1

            frame_count += 1

        cap.release()
        self.label_status.config(text=f"Extraction complete! {saved_count} frames saved.")
        messagebox.showinfo("Success", f"Extracted {saved_count} frames to {self.output_dir}")

if __name__ == "__main__":
    root = tk.Tk()
    app = MP4FrameExtractor(root)
    root.mainloop()
