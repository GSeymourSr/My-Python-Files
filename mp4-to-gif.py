#!/usr/bin/env python3
import os
import tkinter as tk
from tkinter import filedialog, messagebox
from moviepy.editor import VideoFileClip
import traceback

LOG_FILE = os.path.join(os.getcwd(), "mp4_to_gif_error.log")

class MP4toGIFConverter:
    def __init__(self, master):
        self.master = master
        master.title("MP4 to GIF Converter")
        master.geometry("500x250")
        
        # Variables to store file path and output file path.
        self.input_file = ""
        self.output_file = ""
        
        # Label and button for file selection.
        self.label_select = tk.Label(master, text="Select an MP4 file:")
        self.label_select.pack(pady=(10, 5))
        
        self.btn_browse = tk.Button(master, text="Browse", command=self.browse_file)
        self.btn_browse.pack()
        
        self.label_file = tk.Label(master, text="No file selected", fg="blue")
        self.label_file.pack(pady=(5, 10))
        
        # Entry for output FPS.
        self.label_fps = tk.Label(master, text="Enter output FPS (leave blank for original):")
        self.label_fps.pack()
        
        self.entry_fps = tk.Entry(master, width=10)
        self.entry_fps.pack(pady=(5, 10))
        
        # Convert button.
        self.btn_convert = tk.Button(master, text="Convert", command=self.convert_video)
        self.btn_convert.pack(pady=(10, 5))
        
        # Status label.
        self.label_status = tk.Label(master, text="")
        self.label_status.pack(pady=(10, 5))
    
    def browse_file(self):
        # Open a file dialog to select an MP4 file.
        file_path = filedialog.askopenfilename(
            title="Select an MP4 file",
            filetypes=[("MP4 files", "*.mp4"), ("All files", "*.*")]
        )
        if file_path:
            self.input_file = file_path
            self.label_file.config(text=os.path.basename(file_path))
    
    def convert_video(self):
        if not self.input_file:
            messagebox.showerror("Error", "No MP4 file selected.")
            return
        
        # Get the output FPS value (if provided)
        fps_value = self.entry_fps.get().strip()
        try:
            output_fps = float(fps_value) if fps_value else None
        except ValueError:
            messagebox.showerror("Error", "Invalid FPS value. Please enter a number.")
            return
        
        # Save the GIF in the fixed directory "C:\- AI  NEW CONTENT"
        output_dir = r"C:\- AI  NEW CONTENT"
        os.makedirs(output_dir, exist_ok=True)
        base_name = os.path.basename(self.input_file)
        file_name, _ = os.path.splitext(base_name)
        self.output_file = os.path.join(output_dir, file_name + ".gif")
        
        self.label_status.config(text="Loading video...")
        self.master.update_idletasks()
        
        try:
            clip = VideoFileClip(self.input_file)
            duration = clip.duration
            fps = output_fps if output_fps is not None else clip.fps
                
            status_text = f"Video duration: {duration:.2f} sec\nUsing {fps:.2f} FPS\nConverting..."
            self.label_status.config(text=status_text)
            self.master.update_idletasks()
            
            clip.write_gif(self.output_file, fps=fps)
            
            self.label_status.config(text=f"Conversion complete!\nGIF saved as:\n{self.output_file}")
            messagebox.showinfo("Success", f"Conversion complete.\nGIF saved as:\n{self.output_file}")
        except Exception as e:
            error_msg = f"An error occurred during conversion:\n{e}"
            messagebox.showerror("Error", error_msg)
            self.label_status.config(text="Error during conversion.")
            with open(LOG_FILE, "w") as log:
                log.write(traceback.format_exc())

def main():
    try:
        root = tk.Tk()
        app = MP4toGIFConverter(root)
        root.mainloop()
    except Exception as e:
        error_msg = f"An unhandled error occurred:\n{e}"
        messagebox.showerror("Unhandled Error", error_msg)
        with open(LOG_FILE, "w") as log:
            log.write(traceback.format_exc())

if __name__ == "__main__":
    main()
