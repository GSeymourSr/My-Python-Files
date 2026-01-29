import cv2
import numpy as np
import os
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import threading
from pathlib import Path

# --- Core Video Processing Logic (largely unchanged, but with logging) ---

def create_looped_video(input_path, output_path, num_loops, log_callback):
    """
    Reads a video, loops it, and saves the result. Now uses a callback for logging.
    """
    try:
        log_callback("-" * 50)
        log_callback(f"Processing: {os.path.basename(input_path)}")

        cap = cv2.VideoCapture(str(input_path))
        if not cap.isOpened():
            log_callback(f"!! ERROR: Could not open video file {input_path}")
            return False, None

        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)

        log_callback("-> Loading frames into memory...")
        frames = []
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            frames.append(frame)
        cap.release()

        if not frames:
            log_callback(f"!! ERROR: No frames could be read from {input_path}")
            return False, None

        log_callback(f"-> Loaded {len(frames)} frames successfully.")

        # For combining, we need to return the properties and frames
        video_properties = {
            'width': width,
            'height': height,
            'fps': fps,
            'frames': frames
        }

        # If an output path is provided, we are in "Separate Files" mode
        if output_path:
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            writer = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))
            if not writer.isOpened():
                log_callback(f"!! ERROR: Could not open VideoWriter for path {output_path}")
                return False, None

            log_callback(f"-> Writing {num_loops} loops to {os.path.basename(output_path)}...")
            for i in range(num_loops):
                log_callback(f"   - Writing loop {i + 1} of {num_loops}...")
                for frame in frames:
                    writer.write(frame)
                # For a boomerang loop, reverse the frames (excluding first and last to avoid stutter)
                for frame in reversed(frames[1:-1]):
                    writer.write(frame)
            
            writer.release()
            log_callback(f"-> SUCCESS: Video saved to {output_path}")
            log_callback("-" * 50)
        
        return True, video_properties

    except Exception as e:
        log_callback(f"!! UNEXPECTED ERROR processing {input_path}: {e}")
        return False, None


# --- GUI Application Class ---

class VideoLooperApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Video Looper Pro")
        self.root.geometry("700x600")

        self.video_files = []
        self.output_directory = ""
        self.processing_mode = tk.StringVar(value="separate")

        # --- UI Layout ---
        
        # Frame for file selection
        selection_frame = tk.LabelFrame(root, text="1. Select Videos", padx=10, pady=10)
        selection_frame.pack(fill="x", padx=10, pady=5)
        
        self.file_listbox = tk.Listbox(selection_frame, height=6)
        self.file_listbox.pack(fill="x", expand=True, side="top")
        
        select_button = tk.Button(selection_frame, text="Browse for Video Files", command=self.select_video_files)
        select_button.pack(pady=5)

        # Frame for loop settings
        settings_frame = tk.LabelFrame(root, text="2. Set Looping Options", padx=10, pady=10)
        settings_frame.pack(fill="x", padx=10, pady=5)
        
        tk.Label(settings_frame, text="Number of Loops (1 = 1 forward & 1 backward):").pack(side="left")
        self.num_loops_spinbox = tk.Spinbox(settings_frame, from_=1, to=100, width=5)
        self.num_loops_spinbox.pack(side="left", padx=10)

        # Frame for output settings
        output_frame = tk.LabelFrame(root, text="3. Choose Output Mode", padx=10, pady=10)
        output_frame.pack(fill="x", padx=10, pady=5)

        tk.Radiobutton(output_frame, text="Save each video as a separate looped file", variable=self.processing_mode, value="separate").pack(anchor="w")
        tk.Radiobutton(output_frame, text="Combine all selected videos into one single looped file", variable=self.processing_mode, value="combine").pack(anchor="w")
        
        # Frame for starting the process
        action_frame = tk.LabelFrame(root, text="4. Start Processing", padx=10, pady=10)
        action_frame.pack(fill="x", padx=10, pady=5)
        
        self.start_button = tk.Button(action_frame, text="Start Processing", bg="#4CAF50", fg="white", command=self.start_processing_thread)
        self.start_button.pack(pady=10, fill="x")

        # Frame for logging
        log_frame = tk.LabelFrame(root, text="Log", padx=10, pady=10)
        log_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.log_widget = scrolledtext.ScrolledText(log_frame, state='disabled', wrap=tk.WORD, height=10)
        self.log_widget.pack(fill="both", expand=True)

    def log(self, message):
        """ Appends a message to the log widget and console. """
        print(message)  # Also print to console for debugging
        self.log_widget.config(state='normal')
        self.log_widget.insert(tk.END, message + '\n')
        self.log_widget.config(state='disabled')
        self.log_widget.see(tk.END) # Scroll to the bottom

    def select_video_files(self):
        """ Opens a dialog to select multiple video files. """
        files = filedialog.askopenfilenames(
            title="Select one or more video files",
            filetypes=[("Video files", "*.mp4 *.avi *.mkv"), ("All files", "*.*")]
        )
        if files:
            self.video_files = list(files)
            self.file_listbox.delete(0, tk.END)
            for file in self.video_files:
                self.file_listbox.insert(tk.END, os.path.basename(file))
            self.log(f"Selected {len(self.video_files)} file(s).")

    def generate_unique_filepath(self, directory, filename):
        """ Generates a unique filename (e.g., file_1.mp4, file_2.mp4) to avoid overwriting. """
        base, ext = os.path.splitext(filename)
        output_path = Path(directory) / f"{base}{ext}"
        count = 1
        while output_path.exists():
            output_path = Path(directory) / f"{base}_{count}{ext}"
            count += 1
        return output_path

    def start_processing_thread(self):
        """ Starts the video processing in a separate thread to keep the GUI responsive. """
        # Basic validation
        if not self.video_files:
            messagebox.showerror("Error", "No video files selected.")
            return

        self.start_button.config(state="disabled", text="Processing...")
        
        # Create and start the processing thread
        thread = threading.Thread(target=self.process_videos)
        thread.daemon = True # Allows main window to exit even if thread is running
        thread.start()

    def process_videos(self):
        """ The main logic for processing videos based on the selected mode. """
        try:
            num_loops = int(self.num_loops_spinbox.get())
            mode = self.processing_mode.get()

            if mode == "separate":
                self.process_separate_files(num_loops)
            elif mode == "combine":
                self.process_combined_file(num_loops)
        
        except ValueError:
            messagebox.showerror("Error", "Number of loops must be a valid integer.")
        except Exception as e:
            self.log(f"!! A critical error occurred: {e}")
        finally:
            # Re-enable the button once processing is done
            self.start_button.config(state="normal", text="Start Processing")
            self.log("\nProcessing finished.")

    def process_separate_files(self, num_loops):
        output_dir = filedialog.askdirectory(title="Select a folder to save the output files")
        if not output_dir:
            self.log("Output folder selection cancelled. Aborting.")
            return

        self.log(f"\nMode: Separate Files. Outputting to: {output_dir}")
        for video_path in self.video_files:
            file_name, _ = os.path.splitext(os.path.basename(video_path))
            default_output_name = f"{file_name}_looped.mp4"
            output_path = self.generate_unique_filepath(output_dir, default_output_name)
            
            create_looped_video(video_path, output_path, num_loops, self.log)

    def process_combined_file(self, num_loops):
        output_path = filedialog.asksaveasfilename(
            title="Save combined video as...",
            defaultextension=".mp4",
            filetypes=[("MP4 Video", "*.mp4")]
        )
        if not output_path:
            self.log("Save operation cancelled. Aborting.")
            return

        self.log(f"\nMode: Combine into single file. Outputting to: {output_path}")

        all_video_data = []
        for video_path in self.video_files:
            success, properties = create_looped_video(video_path, None, num_loops, self.log)
            if success:
                all_video_data.append(properties)
            else:
                self.log(f"-> Skipping {os.path.basename(video_path)} due to read error.")

        if not all_video_data:
            self.log("!! No videos could be processed. Aborting combine operation.")
            return

        # Use properties from the first video as the standard for the output
        first_video = all_video_data[0]
        width, height, fps = first_video['width'], first_video['height'], first_video['fps']
        self.log(f"\nCreating combined video with properties: {width}x{height} @ {fps}fps")

        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        
        if not writer.isOpened():
            self.log(f"!! ERROR: Could not open VideoWriter for combined path {output_path}")
            return
            
        for i, video_data in enumerate(all_video_data):
            self.log(f"-> Combining video #{i+1}...")
            # Check if resizing is needed
            current_width, current_height = video_data['width'], video_data['height']
            frames = video_data['frames']
            
            for _ in range(num_loops):
                for frame in frames:
                    if (current_width, current_height) != (width, height):
                        frame = cv2.resize(frame, (width, height))
                    writer.write(frame)
                for frame in reversed(frames[1:-1]):
                    if (current_width, current_height) != (width, height):
                        frame = cv2.resize(frame, (width, height))
                    writer.write(frame)
        
        writer.release()
        self.log(f"-> SUCCESS: Combined video saved to {output_path}")


if __name__ == "__main__":
    root = tk.Tk()
    app = VideoLooperApp(root)
    root.mainloop()