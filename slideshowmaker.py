import cv2
import os
import random
import numpy as np
import threading
import logging
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from moviepy.editor import ImageSequenceClip, AudioFileClip, VideoFileClip
from PIL import Image, ImageTk # For displaying images in the GUI if needed

# --- 1. CORE LOGIC (Separated from the GUI) ---
# This section contains the powerful backend for generating the slideshow.

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class TransitionManager:
    """Manages and provides a variety of visual transitions."""
    def __init__(self):
        self.transitions = {
            "Fade": self.fade,
            "Slide Left": self.slide_left,
            "Wipe Down": self.wipe_down,
            "Zoom In": self.zoom_in,
        }
    
    def get_transition_by_name(self, name):
        return self.transitions.get(name, self.fade)

    def fade(self, frame1, frame2, progress):
        """Fades frame1 into frame2."""
        return cv2.addWeighted(frame1, 1 - progress, frame2, progress, 0)

    def slide_left(self, frame1, frame2, progress):
        """Slides frame2 in from the right, over frame1."""
        width = frame1.shape[1]
        offset = int(width * progress)
        result = frame1.copy()
        result[:, :width - offset] = frame1[:, offset:]
        result[:, width - offset:] = frame2[:, :offset]
        return result

    def wipe_down(self, frame1, frame2, progress):
        """Wipes frame2 down from the top, over frame1."""
        height = frame1.shape[0]
        offset = int(height * progress)
        result = frame1.copy()
        result[:offset, :] = frame2[:offset, :]
        return result
        
    def zoom_in(self, frame1, frame2, progress):
        """Zooms from frame1 to the center of frame2."""
        h, w = frame1.shape[:2]
        
        # Calculate the zoom factor (starts at 1, goes up)
        scale = 1.0 + (progress * 0.5) # Zoom up to 150%
        
        # Create a scaled version of frame1
        zoomed_frame1 = cv2.resize(frame1, None, fx=scale, fy=scale, interpolation=cv2.INTER_LINEAR)
        
        # Crop the center of the zoomed frame
        zh, zw = zoomed_frame1.shape[:2]
        x1 = (zw - w) // 2
        y1 = (zh - h) // 2
        crop_zoomed = zoomed_frame1[y1:y1+h, x1:x1+w]

        # Blend the zoomed frame with the target frame
        return cv2.addWeighted(crop_zoomed, 1 - progress, frame2, progress, 0)


class SlideshowGenerator:
    """Handles the heavy lifting of creating the slideshow video."""

    def __init__(self, settings, progress_callback):
        self.settings = settings
        self.progress_callback = progress_callback
        self.media_files = self._load_media_files()
        self.transition_manager = TransitionManager()
        self.frames = []
        self.fps = 30

    def _load_media_files(self):
        """Scans the directory for valid media files."""
        media_dir = self.settings['media_dir']
        image_ext = {'.jpg', '.jpeg', '.png', '.bmp', '.gif'}
        video_ext = {'.mp4', '.avi', '.mov', '.mkv'}
        
        found_files = []
        for root, _, files in os.walk(media_dir):
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in image_ext or ext in video_ext:
                    found_files.append(os.path.join(root, file))
        
        if self.settings['shuffle']:
            random.shuffle(found_files)
        
        logging.info(f"Found {len(found_files)} media files.")
        return found_files

    def _prepare_frame(self, media_path):
        """Reads and resizes an image file to the target resolution."""
        try:
            img = cv2.imread(media_path)
            if img is None:
                raise ValueError("Image is None")
            # Convert to RGB for moviepy
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            return cv2.resize(img_rgb, self.settings['resolution'])
        except Exception as e:
            logging.error(f"Could not prepare image {media_path}: {e}")
            # Return a black frame as a fallback
            w, h = self.settings['resolution']
            return np.zeros((h, w, 3), dtype=np.uint8)

    def _generate_transition(self, frame1, frame2):
        """Generates a sequence of frames for a transition."""
        num_frames = int(self.settings['transition_duration'] * self.fps)
        transition_func = self.transition_manager.get_transition_by_name(random.choice(self.settings['transitions']))

        for i in range(num_frames):
            progress = (i + 1) / num_frames
            self.frames.append(transition_func(frame1, frame2, progress))

    def create_slideshow(self):
        """The main method to generate all video frames."""
        if not self.media_files:
            self.progress_callback(100, "Error: No media files found!", is_error=True)
            return

        total_files = len(self.media_files)
        last_frame = self._prepare_frame(self.media_files[0])

        for i, media_file in enumerate(self.media_files):
            progress = int((i / total_files) * 100)
            self.progress_callback(progress, f"Processing {os.path.basename(media_file)}...")
            
            # 1. Add static frames for the previous item
            if i > 0: # Don't add static frames for the very first image
                num_static_frames = int(self.settings['image_duration'] * self.fps)
                self.frames.extend([last_frame] * num_static_frames)

            # 2. Handle the current file (image or video)
            ext = os.path.splitext(media_file)[1].lower()
            if ext in {'.mp4', '.avi', '.mov', '.mkv'}:
                # It's a video file
                try:
                    with VideoFileClip(media_file, target_resolution=(self.settings['resolution'][1], self.settings['resolution'][0])) as clip:
                        # Transition *into* the video
                        first_video_frame = clip.get_frame(0)
                        self._generate_transition(last_frame, first_video_frame)
                        
                        # Add all video frames
                        self.frames.extend(list(clip.iter_frames(fps=self.fps)))
                        
                        # The new "last_frame" is the end of the video
                        last_frame = clip.get_frame(clip.duration - 1/self.fps)
                except Exception as e:
                    logging.error(f"Error processing video {media_file}: {e}")
                    # In case of error, just treat it like a static frame
                    self.frames.extend([last_frame] * int(self.settings['image_duration'] * self.fps))
            else:
                # It's an image file
                current_frame = self._prepare_frame(media_file)
                if i > 0:
                    self._generate_transition(last_frame, current_frame)
                last_frame = current_frame

        # Add the final image's static duration
        num_static_frames = int(self.settings['image_duration'] * self.fps)
        self.frames.extend([last_frame] * num_static_frames)

        # 3. Assemble the final video with moviepy
        self.progress_callback(95, "Assembling final video...")
        try:
            video_clip = ImageSequenceClip(self.frames, fps=self.fps)
            
            # Add audio if provided
            music_file = self.settings.get('music_file')
            if music_file:
                audio_clip = AudioFileClip(music_file).volumex(self.settings['audio_volume'])
                # Loop or trim audio to match video duration
                final_audio = audio_clip.set_duration(video_clip.duration)
                video_clip = video_clip.set_audio(final_audio)

            # Write the final file
            video_clip.write_videofile(self.settings['output_path'], codec='libx264', preset='medium', threads=4)
            self.progress_callback(100, f"Success! Video saved to {self.settings['output_path']}", is_done=True)

        except Exception as e:
            logging.error(f"Failed to write video file: {e}")
            self.progress_callback(100, f"Error writing video file: {e}", is_error=True)

# --- 2. GUI APPLICATION ---
# This class builds and manages the Tkinter user interface.

class SlideshowApp:
    def __init__(self, root):
        self.root = root
        self.root.title("🎃 Halloween Slideshow Creator 👻")
        self.root.geometry("600x650")

        # --- Style Configuration ---
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure("TLabel", background="#2E2E2E", foreground="orange", font=("Segoe UI", 10))
        self.style.configure("TButton", background="#3D3D3D", foreground="white", font=("Segoe UI", 10, "bold"))
        self.style.map("TButton", background=[('active', '#FF8C00')]) # Orange on hover
        self.style.configure("TFrame", background="#2E2E2E")
        self.style.configure("TEntry", fieldbackground="#555555", foreground="white", insertbackground="white")
        self.style.configure("Horizontal.TScale", background="#2E2E2E")
        self.style.configure("TCheckbutton", background="#2E2E2E", foreground="white")
        self.style.map("TCheckbutton", indicatorcolor=[('selected', 'orange')])
        
        self.root.configure(bg="#2E2E2E")

        # --- Main Frame ---
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- Variables to store user choices ---
        self.media_dir = tk.StringVar()
        self.music_file = tk.StringVar()
        self.output_dir = tk.StringVar()
        self.output_filename = tk.StringVar(value="my_halloween_slideshow.mp4")
        self.resolution = tk.StringVar(value="1280x720")
        self.image_duration = tk.DoubleVar(value=3.0)
        self.transition_duration = tk.DoubleVar(value=1.5)
        self.audio_volume = tk.DoubleVar(value=0.5)
        self.shuffle_media = tk.BooleanVar(value=True)
        self.transition_vars = {name: tk.BooleanVar(value=True) for name in TransitionManager().transitions}

        # --- Create Widgets ---
        self._create_widgets(main_frame)

    def _create_widgets(self, parent):
        row = 0
        
        # --- Section 1: Inputs ---
        input_frame = ttk.LabelFrame(parent, text=" 1. Select Your Media ", padding=10)
        input_frame.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        input_frame.columnconfigure(1, weight=1)

        ttk.Label(input_frame, text="Media Folder:").grid(row=0, column=0, sticky="w", pady=5)
        ttk.Entry(input_frame, textvariable=self.media_dir).grid(row=0, column=1, sticky="ew", padx=5)
        ttk.Button(input_frame, text="Browse...", command=self._browse_media).grid(row=0, column=2)

        ttk.Label(input_frame, text="Music File (Optional):").grid(row=1, column=0, sticky="w", pady=5)
        ttk.Entry(input_frame, textvariable=self.music_file).grid(row=1, column=1, sticky="ew", padx=5)
        ttk.Button(input_frame, text="Browse...", command=self._browse_music).grid(row=1, column=2)
        row += 1

        # --- Section 2: Settings ---
        settings_frame = ttk.LabelFrame(parent, text=" 2. Customize Your Slideshow ", padding=10)
        settings_frame.grid(row=row, column=0, columnspan=2, sticky="ew", pady=10)
        settings_frame.columnconfigure(1, weight=1)
        
        ttk.Label(settings_frame, text="Image Duration (s):").grid(row=0, column=0, sticky="w", pady=5)
        ttk.Scale(settings_frame, from_=1, to=10, orient="horizontal", variable=self.image_duration).grid(row=0, column=1, sticky="ew", padx=5)
        ttk.Label(settings_frame, textvariable=self.image_duration).grid(row=0, column=2)

        ttk.Label(settings_frame, text="Transition Duration (s):").grid(row=1, column=0, sticky="w", pady=5)
        ttk.Scale(settings_frame, from_=0.5, to=5, orient="horizontal", variable=self.transition_duration).grid(row=1, column=1, sticky="ew", padx=5)
        ttk.Label(settings_frame, textvariable=self.transition_duration).grid(row=1, column=2)

        ttk.Label(settings_frame, text="Audio Volume:").grid(row=2, column=0, sticky="w", pady=5)
        ttk.Scale(settings_frame, from_=0, to=1, orient="horizontal", variable=self.audio_volume).grid(row=2, column=1, sticky="ew", padx=5)
        ttk.Label(settings_frame, textvariable=self.audio_volume).grid(row=2, column=2)
        
        ttk.Checkbutton(settings_frame, text="Shuffle Media", variable=self.shuffle_media).grid(row=3, column=0, sticky="w", pady=5)
        row += 1
        
        # --- Transitions Sub-Frame ---
        trans_frame = ttk.LabelFrame(settings_frame, text="Enabled Transitions", padding=5)
        trans_frame.grid(row=4, column=0, columnspan=3, sticky="ew", pady=(10, 0))
        col_count = 0
        for name, var in self.transition_vars.items():
            ttk.Checkbutton(trans_frame, text=name, variable=var).grid(row=0, column=col_count, padx=10, sticky="w")
            col_count += 1
        
        # --- Section 3: Output ---
        output_frame = ttk.LabelFrame(parent, text=" 3. Set Output Destination ", padding=10)
        output_frame.grid(row=row, column=0, columnspan=2, sticky="ew", pady=10)
        output_frame.columnconfigure(1, weight=1)
        
        ttk.Label(output_frame, text="Output Folder:").grid(row=0, column=0, sticky="w", pady=5)
        ttk.Entry(output_frame, textvariable=self.output_dir).grid(row=0, column=1, sticky="ew", padx=5)
        ttk.Button(output_frame, text="Browse...", command=self._browse_output).grid(row=0, column=2)
        
        ttk.Label(output_frame, text="Filename:").grid(row=1, column=0, sticky="w", pady=5)
        ttk.Entry(output_frame, textvariable=self.output_filename).grid(row=1, column=1, sticky="ew", padx=5)
        
        ttk.Label(output_frame, text="Resolution:").grid(row=2, column=0, sticky="w", pady=5)
        ttk.Combobox(output_frame, textvariable=self.resolution, values=["1280x720", "1920x1080", "640x480"]).grid(row=2, column=1, sticky="w", padx=5)
        row += 1

        # --- Section 4: Action! ---
        action_frame = ttk.Frame(parent)
        action_frame.grid(row=row, column=0, columnspan=2, pady=20)

        self.generate_button = ttk.Button(action_frame, text="✨ Generate Slideshow!", command=self._start_generation, style="TButton")
        self.generate_button.pack()
        row += 1

        # --- Section 5: Progress ---
        progress_frame = ttk.Frame(parent)
        progress_frame.grid(row=row, column=0, columnspan=2, sticky="ew", pady=10)
        progress_frame.columnconfigure(0, weight=1)
        
        self.status_label = ttk.Label(progress_frame, text="Ready to create some spooky memories!", anchor="center")
        self.status_label.grid(row=0, column=0, sticky="ew")
        self.progress_bar = ttk.Progressbar(progress_frame, orient="horizontal", length=300, mode="determinate")
        self.progress_bar.grid(row=1, column=0, sticky="ew", pady=5)

    def _browse_media(self):
        dir_path = filedialog.askdirectory(title="Select Media Folder")
        if dir_path:
            self.media_dir.set(dir_path)

    def _browse_music(self):
        file_path = filedialog.askopenfilename(title="Select Music File", filetypes=[("Audio Files", "*.mp3 *.wav *.ogg")])
        if file_path:
            self.music_file.set(file_path)

    def _browse_output(self):
        dir_path = filedialog.askdirectory(title="Select Output Folder")
        if dir_path:
            self.output_dir.set(dir_path)

    def _get_settings(self):
        """Gathers all settings from the UI into a dictionary."""
        w, h = map(int, self.resolution.get().split('x'))
        selected_transitions = [name for name, var in self.transition_vars.items() if var.get()]
        if not selected_transitions: # Fallback if none are selected
            selected_transitions = ["Fade"]

        return {
            'media_dir': self.media_dir.get(),
            'music_file': self.music_file.get(),
            'output_path': os.path.join(self.output_dir.get(), self.output_filename.get()),
            'resolution': (w, h),
            'image_duration': self.image_duration.get(),
            'transition_duration': self.transition_duration.get(),
            'audio_volume': self.audio_volume.get(),
            'shuffle': self.shuffle_media.get(),
            'transitions': selected_transitions
        }
    
    def _validate_settings(self, settings):
        """Checks if required fields are filled."""
        if not settings['media_dir']:
            messagebox.showerror("Error", "Please select a media folder.")
            return False
        if not self.output_dir.get():
            messagebox.showerror("Error", "Please select an output folder.")
            return False
        return True

    def _update_progress(self, value, text, is_done=False, is_error=False):
        """Thread-safe method to update the GUI progress bar and label."""
        self.root.after(0, self._do_update, value, text, is_done, is_error)

    def _do_update(self, value, text, is_done, is_error):
        """The actual UI update logic."""
        self.progress_bar['value'] = value
        self.status_label['text'] = text
        if is_error:
            self.status_label.config(foreground="red")
            self.generate_button.config(state="normal")
        elif is_done:
            self.status_label.config(foreground="lightgreen")
            self.generate_button.config(state="normal")
            messagebox.showinfo("Success", "Your slideshow has been created successfully!")
        else:
             self.status_label.config(foreground="orange")

    def _start_generation(self):
        """Kicks off the slideshow generation in a new thread."""
        settings = self._get_settings()
        if not self._validate_settings(settings):
            return

        self.generate_button.config(state="disabled")
        self.progress_bar['value'] = 0
        
        # Create and run the generator in a separate thread
        generator = SlideshowGenerator(settings, self._update_progress)
        thread = threading.Thread(target=generator.create_slideshow, daemon=True)
        thread.start()

# --- 3. APPLICATION ENTRY POINT ---
if __name__ == "__main__":
    root = tk.Tk()
    app = SlideshowApp(root)
    root.mainloop()