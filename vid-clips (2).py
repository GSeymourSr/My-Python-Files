import pygame
import random
import os
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter import font as tkFont
import json
import numpy as np
import tempfile

try:
    from moviepy.editor import VideoFileClip, AudioFileClip
    MOVIEPY_AVAILABLE = True
except ImportError:
    MOVIEPY_AVAILABLE = False

# --- Configuration Defaults ---
DEFAULT_FPS = 30
DEFAULT_COLOR_CHANGE_SPEED = 0.3
DEFAULT_MIN_SNIPPET_DURATION = 5.0
DEFAULT_MAX_SNIPPET_DURATION = 10.0
DEFAULT_BACKGROUND_AUDIO_ENABLED = False

CONFIG_FILE_NAME = "video_snippet_config.json"
TEMP_AUDIO_FILENAME = os.path.join(tempfile.gettempdir(), "snippet_audio.mp3")

# --- Helper Functions ---
def get_random_color():
    """Returns a random RGB tuple."""
    return (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))

def interpolate_color(color1, color2, factor):
    """Linearly interpolates between two RGB colors."""
    r = int(color1[0] + (color2[0] - color1[0]) * factor)
    g = int(color1[1] + (color2[1] - color1[1]) * factor)
    b = int(color1[2] + (color2[2] - color1[2]) * factor)
    return (max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b)))

def get_unique_filename(base_name):
    """Returns a unique filename by appending a number if the base name already exists."""
    if not os.path.exists(base_name):
        return base_name
    name, ext = os.path.splitext(base_name)
    counter = 1
    while True:
        new_name = f"{name}_{counter}{ext}"
        if not os.path.exists(new_name):
            return new_name
        counter += 1

def scale_surface_to_fit(surface, max_width, max_height):
    """Scales a pygame surface to fit within max dimensions while preserving aspect ratio."""
    surf_w, surf_h = surface.get_size()
    if surf_w == 0 or surf_h == 0:
        return surface
    
    ratio_w = max_width / surf_w
    ratio_h = max_height / surf_h
    scale_ratio = min(ratio_w, ratio_h)

    if scale_ratio < 1.0:
        new_w = int(surf_w * scale_ratio)
        new_h = int(surf_h * scale_ratio)
        try:
            return pygame.transform.smoothscale(surface, (new_w, new_h))
        except (pygame.error, ValueError):
            return surface # Return original on error
    return surface

# --- Pygame Visualization Main Function ---
def run_pygame_visualization(selected_video_files, screen_width, screen_height,
                             p_fps, p_color_change_speed,
                             p_min_snippet_duration, p_max_snippet_duration,
                             background_audio_path=None, play_background_audio=False,
                             record_video=False, record_duration=0, record_filename=""):
    """The main function to run the Pygame video snippet visualization loop."""
    if not MOVIEPY_AVAILABLE:
        messagebox.showerror("MoviePy Missing", "MoviePy is required for video playback. Please install it.")
        return

    pygame.init()
    pygame.mixer.init()

    print("PYGAME: Starting video snippet visualization...")
    try:
        screen = pygame.display.set_mode((screen_width, screen_height), pygame.FULLSCREEN | pygame.HWSURFACE | pygame.DOUBLEBUF)
    except pygame.error as e:
        messagebox.showerror("Pygame Error", f"Could not set up fullscreen display:\n{e}\n\nReturning to GUI.")
        pygame.mixer.quit()
        pygame.quit()
        return
        
    pygame.display.set_caption("Greg Seymour - AI Video Snippet Player")
    pygame.mouse.set_visible(False)
    clock = pygame.time.Clock()

    # Background color state
    current_top_color, target_top_color = get_random_color(), get_random_color()
    current_bottom_color, target_bottom_color = get_random_color(), get_random_color()
    color_lerp_factor = 0.0

    # Video snippet state
    current_state = "IDLE" # Can be "IDLE", "PREPARING", "PLAYING"
    frame_iterator = None
    video_frame_surface = None
    moviepy_clip = None

    # Play optional background audio
    if play_background_audio and background_audio_path:
        try:
            # Use a different channel or handle carefully if snippet audio is also desired
            pygame.mixer.music.load(background_audio_path)
            pygame.mixer.music.play(-1) # Loop background track
            print(f"PYGAME: Playing background audio: {background_audio_path}")
        except pygame.error as e:
            print(f"PYGAME Error playing background audio: {e}")

    # Video Recording Setup
    frames_for_video = []
    recording_active_this_session = False
    if record_video and record_filename and record_duration > 0:
        recording_active_this_session = True
        record_filename = get_unique_filename(record_filename)
        print(f"PYGAME: Recording to '{record_filename}' for {record_duration:.2f}s at {p_fps} FPS.")

    running = True
    print("PYGAME: Visualization running. Press any key or mouse button to return to GUI.")

    # --- Main Visualization Loop ---
    while running:
        dt = clock.tick(p_fps) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT or event.type == pygame.KEYDOWN or event.type == pygame.MOUSEBUTTONDOWN:
                running = False
        
        if not running: break

        # State machine for video snippets
        if current_state == "IDLE":
            current_state = "PREPARING"
            video_frame_surface = None # Clear old frame
            
            if moviepy_clip:
                moviepy_clip.close()
                moviepy_clip = None

            if not selected_video_files:
                print("PYGAME: No video files to play. Halting.")
                running = False
                break
            
            # --- Select and prepare a new random snippet ---
            try:
                video_path = random.choice(selected_video_files)
                print(f"\nPYGAME: Preparing snippet from: {os.path.basename(video_path)}")
                
                with VideoFileClip(video_path) as clip:
                    duration = clip.duration
                
                if duration < p_min_snippet_duration:
                    snippet_duration = duration
                    start_time = 0
                else:
                    snippet_duration = random.uniform(p_min_snippet_duration, min(p_max_snippet_duration, duration))
                    max_start_time = duration - snippet_duration
                    start_time = random.uniform(0, max_start_time)
                
                end_time = start_time + snippet_duration
                print(f"PYGAME: Snippet from {start_time:.2f}s to {end_time:.2f}s (Duration: {snippet_duration:.2f}s)")

                moviepy_clip = VideoFileClip(video_path, audio=True).subclip(start_time, end_time)
                
                # Extract audio to temp file and play it
                if moviepy_clip.audio:
                    moviepy_clip.audio.write_audiofile(TEMP_AUDIO_FILENAME, codec='mp3', logger=None)
                    pygame.mixer.music.load(TEMP_AUDIO_FILENAME)
                    pygame.mixer.music.play()
                else: # Stop any previous music if new clip has no audio
                    pygame.mixer.music.stop()

                frame_iterator = moviepy_clip.iter_frames(fps=p_fps, dtype='uint8')
                current_state = "PLAYING"

            except Exception as e:
                print(f"PYGAME ERROR: Could not process video file '{video_path}'. Skipping. Error: {e}")
                if moviepy_clip: moviepy_clip.close()
                current_state = "IDLE" # Try another video
                time.sleep(1) # Prevent rapid-fire errors

        # --- Update background color ---
        color_lerp_factor = (color_lerp_factor + p_color_change_speed * dt) % 1.0
        if color_lerp_factor < p_color_change_speed * dt: # Wrapped around
             current_top_color, target_top_color = target_top_color, get_random_color()
             current_bottom_color, target_bottom_color = target_bottom_color, get_random_color()
        display_top_color = interpolate_color(current_top_color, target_top_color, color_lerp_factor)
        display_bottom_color = interpolate_color(current_bottom_color, target_bottom_color, color_lerp_factor)

        # --- Drawing ---
        # Draw gradient background
        for y_coord in range(screen_height):
            row_factor = y_coord / screen_height
            color = interpolate_color(display_top_color, display_bottom_color, row_factor)
            pygame.draw.line(screen, color, (0, y_coord), (screen_width, y_coord))

        # Get next video frame and draw it
        if current_state == "PLAYING" and frame_iterator:
            try:
                frame_np = next(frame_iterator)
                # MoviePy frames are (h, w, c), Pygame needs (w, h, c) after transpose
                video_frame_surface = pygame.surfarray.make_surface(np.transpose(frame_np, (1, 0, 2)))
            except StopIteration:
                # End of snippet
                print("PYGAME: Snippet finished.")
                current_state = "IDLE"
                frame_iterator = None
                pygame.mixer.music.stop()
            except Exception as e:
                print(f"PYGAME ERROR: Error during frame iteration: {e}")
                current_state = "IDLE"

        if video_frame_surface:
            scaled_frame = scale_surface_to_fit(video_frame_surface, screen_width, screen_height)
            frame_rect = scaled_frame.get_rect(center=(screen_width // 2, screen_height // 2))
            screen.blit(scaled_frame, frame_rect)

        # --- Capture frame for video if recording ---
        if recording_active_this_session:
            total_frames_needed = int(record_duration * p_fps)
            if len(frames_for_video) < total_frames_needed:
                frame_data = pygame.surfarray.array3d(screen)
                frames_for_video.append(np.transpose(frame_data, (1, 0, 2)))
            else:
                print(f"PYGAME: Recording duration reached.")
                running = False
        
        pygame.display.flip()

    # --- End of Visualization Loop ---
    print("PYGAME: Visualization ended.")
    
    # Cleanup
    pygame.mixer.music.stop()
    if moviepy_clip:
        moviepy_clip.close()
    
    if os.path.exists(TEMP_AUDIO_FILENAME):
        try:
            os.remove(TEMP_AUDIO_FILENAME)
        except Exception as e:
            print(f"PYGAME Warning: Could not remove temp audio file: {e}")

    # Save video if recording was active
    if recording_active_this_session and frames_for_video:
        print(f"PYGAME: Compiling video from {len(frames_for_video)} frames...")
        try:
            video_clip = ImageSequenceClip(frames_for_video, fps=p_fps)
            final_clip = video_clip
            # Mux in the BACKGROUND audio if provided
            if background_audio_path:
                try:
                    with AudioFileClip(background_audio_path) as audio_clip:
                        final_clip = video_clip.set_audio(audio_clip.set_duration(video_clip.duration))
                    print(f"PYGAME: Background audio '{os.path.basename(background_audio_path)}' will be muxed into video.")
                except Exception as e_audio:
                    print(f"PYGAME Error: Could not attach background audio: {e_audio}")
            
            final_clip.write_videofile(record_filename, codec="libx264", audio_codec="aac", threads=4, preset="medium", logger='bar')
            print(f"PYGAME: Video saved as {record_filename}")
            messagebox.showinfo("Recording Complete", f"Video saved successfully as:\n{record_filename}", parent=None)
        except Exception as e:
            print(f"PYGAME Error saving video: {e}")
            messagebox.showerror("Video Export Error", f"Could not save video:\n{e}", parent=None)

    pygame.mixer.quit()
    pygame.quit()

# --- Tkinter GUI Class ---
class VideoSnippetGUI:
    """The main Tkinter application class for the video snippet tool."""
    def __init__(self, master, system_screen_w, system_screen_h):
        self.master = master
        self.system_screen_w = system_screen_w
        self.system_screen_h = system_screen_h
        
        self.master.resizable(True, True)
        try:
            self.master.state('zoomed')
        except tk.TclError:
             self.master.geometry(f"{int(system_screen_w*0.9)}x{int(system_screen_h*0.85)}")
        self.master.title("Greg Seymour - AI Video Snippet Player")
        
        self.video_files_data = []
        self._init_style()
        self._init_vars()
        self._build_ui()
        self._load_configuration()
        self.master.protocol("WM_DELETE_WINDOW", self._on_quit)

    def _init_style(self):
        """Initializes the ttk styles for a modern, dark theme."""
        self.style = ttk.Style()
        self.style.theme_use('clam')
        # (Style definitions are identical to the previous version, so they are omitted here for brevity)
        # ... You can copy the full _init_style method from the previous answer ...
        self.bg_color = "#2E3440"; self.fg_color = "#E5E9F0"; self.frame_bg = "#3B4252"
        self.accent_color_1 = "#88C0D0"; self.accent_color_2 = "#BF616A"; self.button_color = "#5E81AC"
        self.entry_bg = "#4C566A"
        self.style.configure('.', background=self.bg_color, foreground=self.fg_color, font=('Segoe UI', 10))
        self.style.configure('TFrame', background=self.frame_bg)
        self.style.configure('TLabel', background=self.frame_bg, foreground=self.fg_color, padding=5)
        self.style.configure('TLabelframe', background=self.frame_bg, bordercolor=self.accent_color_1)
        self.style.configure('TLabelframe.Label', background=self.frame_bg, foreground=self.accent_color_1, font=('Segoe UI Semibold', 12))
        self.style.configure('TButton', background=self.button_color, foreground=self.bg_color, font=('Segoe UI Semibold', 10), padding=6)
        self.style.map('TButton', background=[('active', self.accent_color_1), ('pressed', self.accent_color_1)], foreground=[('active', self.bg_color)])
        self.style.configure('Accent.TButton', background=self.accent_color_2, foreground='white', font=('Segoe UI Bold', 12), padding=8)
        self.style.map('Accent.TButton', background=[('active', '#D08770'), ('pressed', '#D08770')])
        self.style.configure('TCheckbutton', background=self.frame_bg, foreground=self.fg_color, indicatorcolor=self.fg_color)
        self.style.map('TCheckbutton', indicatorcolor=[('selected', self.accent_color_1), ('active', self.accent_color_1)])
        self.style.configure('TEntry', fieldbackground=self.entry_bg, foreground=self.fg_color, insertcolor=self.fg_color, borderwidth=1, relief=tk.FLAT)
        self.style.configure('Vertical.TScrollbar', background=self.button_color, troughcolor=self.frame_bg, arrowcolor=self.fg_color)
        self.style.configure('Horizontal.TScale', troughcolor=self.entry_bg, background=self.button_color, foreground=self.fg_color)
        self.style.map('Horizontal.TScale', background=[('active', self.accent_color_1)])
        self.title_font = tkFont.Font(family="Impact", size=28, weight="bold")

    def _init_vars(self):
        """Initializes all Tkinter control variables."""
        self.min_snippet_duration_var = tk.DoubleVar(value=DEFAULT_MIN_SNIPPET_DURATION)
        self.max_snippet_duration_var = tk.DoubleVar(value=DEFAULT_MAX_SNIPPET_DURATION)
        self.fps_var = tk.IntVar(value=DEFAULT_FPS)
        self.color_speed_var = tk.DoubleVar(value=DEFAULT_COLOR_CHANGE_SPEED)

        self.play_bg_audio_var = tk.BooleanVar(value=DEFAULT_BACKGROUND_AUDIO_ENABLED)
        self.bg_audio_file_path_var = tk.StringVar(value="")
        self.record_video_var = tk.BooleanVar(value=False)
        self.record_filename_var = tk.StringVar(value="video_snippet_output.mp4")
        self.record_duration_var = tk.IntVar(value=60)
        
        self.setting_vars = [
            self.min_snippet_duration_var, self.max_snippet_duration_var,
            self.fps_var, self.color_speed_var, self.play_bg_audio_var,
            self.record_video_var, self.record_duration_var
        ]
        for var in self.setting_vars:
            var.trace_add("write", self._save_configuration)

    def _get_config_path(self):
        """Gets the full path for the configuration file."""
        home_dir = os.path.expanduser("~")
        return os.path.join(home_dir, CONFIG_FILE_NAME)

    def _load_configuration(self):
        config_path = self._get_config_path()
        if not os.path.exists(config_path):
            print("GUI: No config file found, using defaults.")
            return

        try:
            with open(config_path, 'r') as f:
                config_data = json.load(f)

            # Load settings
            settings = config_data.get("settings", {})
            self.min_snippet_duration_var.set(settings.get("min_snippet_duration", DEFAULT_MIN_SNIPPET_DURATION))
            self.max_snippet_duration_var.set(settings.get("max_snippet_duration", DEFAULT_MAX_SNIPPET_DURATION))
            self.fps_var.set(settings.get("fps", DEFAULT_FPS))
            self.color_speed_var.set(settings.get("color_speed", DEFAULT_COLOR_CHANGE_SPEED))

            # Load video file list
            self.video_files_data = []
            loaded_files = config_data.get("video_files", [])
            for item in loaded_files:
                path, enabled = item.get("path"), item.get("enabled", True)
                if path and os.path.isfile(path):
                    enabled_var = tk.BooleanVar(value=enabled)
                    enabled_var.trace_add("write", self._save_configuration)
                    self.video_files_data.append({'path': path, 'enabled_var': enabled_var})
                elif path:
                    print(f"GUI Warning: Saved video file not found: {path}")
            
            self._populate_video_list_ui()
            print(f"GUI: Configuration loaded from {config_path}")
        except Exception as e:
            print(f"GUI Error loading configuration: {e}")

    def _save_configuration(self, *args):
        config_path = self._get_config_path()
        settings_to_save = {
            "min_snippet_duration": self.min_snippet_duration_var.get(),
            "max_snippet_duration": self.max_snippet_duration_var.get(),
            "fps": self.fps_var.get(),
            "color_speed": self.color_speed_var.get(),
        }
        files_to_save = [{'path': item['path'], 'enabled': item['enabled_var'].get()} for item in self.video_files_data]
        
        try:
            with open(config_path, 'w') as f:
                json.dump({"settings": settings_to_save, "video_files": files_to_save}, f, indent=4)
        except Exception as e:
            print(f"GUI Error saving configuration: {e}")

    def _build_ui(self):
        self.master.configure(background=self.bg_color)
        main_frame = ttk.Frame(self.master, style='TFrame', padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True)
        main_frame.columnconfigure(0, weight=3)
        main_frame.columnconfigure(1, weight=2)
        main_frame.rowconfigure(1, weight=1)

        title_label = ttk.Label(main_frame, text="Greg Seymour - AI Video Snippet Player",
                                font=self.title_font, anchor="center",
                                style='TLabel', foreground=self.accent_color_1, background=self.bg_color)
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20), sticky="ew")

        # --- Left Panel: Video Files ---
        video_panel = ttk.Frame(main_frame, style='TFrame')
        video_panel.grid(row=1, column=0, sticky="nsew", padx=(0,10))
        video_panel.rowconfigure(1, weight=1)
        video_panel.columnconfigure(0, weight=1)

        video_buttons_frame = ttk.Frame(video_panel, style='TFrame')
        video_buttons_frame.grid(row=0, column=0, sticky="ew", pady=(0,10))
        ttk.Button(video_buttons_frame, text="Add Video(s)", command=self._add_new_videos).pack(side=tk.LEFT, padx=2)
        ttk.Button(video_buttons_frame, text="Select All", command=lambda: self._toggle_all_videos(True)).pack(side=tk.LEFT, padx=2)
        ttk.Button(video_buttons_frame, text="Deselect All", command=lambda: self._toggle_all_videos(False)).pack(side=tk.LEFT, padx=2)

        list_container = ttk.LabelFrame(video_panel, text="Video Files", style='TLabelframe')
        list_container.grid(row=1, column=0, sticky="nsew")
        list_container.rowconfigure(0, weight=1)
        list_container.columnconfigure(0, weight=1)

        self.canvas = tk.Canvas(list_container, borderwidth=0, background=self.frame_bg, highlightthickness=0)
        self.video_list_frame = ttk.Frame(self.canvas, style='TFrame')
        self.scrollbar = ttk.Scrollbar(list_container, orient="vertical", command=self.canvas.yview, style='Vertical.TScrollbar')
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.scrollbar.grid(row=0, column=1, sticky="ns")
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.canvas_window = self.canvas.create_window((0, 0), window=self.video_list_frame, anchor="nw")
        self.video_list_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind('<Configure>', lambda e: self.canvas.itemconfig(self.canvas_window, width=e.width))
        self.master.bind_all("<MouseWheel>", lambda e: self.canvas.yview_scroll(int(-1*(e.delta/120)), "units"), add="+")
        
        # --- Right Panel: Settings ---
        settings_panel = ttk.LabelFrame(main_frame, text="Settings", style='TLabelframe', padding=10)
        settings_panel.grid(row=1, column=1, sticky="nsew", padx=(10,0))
        settings_panel.columnconfigure(1, weight=1)

        row_idx = 0
        def add_setting_slider(label, var, from_, to, precision=1):
            nonlocal row_idx
            ttk.Label(settings_panel, text=label).grid(row=row_idx, column=0, sticky="w", pady=4)
            scale = ttk.Scale(settings_panel, variable=var, from_=from_, to=to, orient=tk.HORIZONTAL)
            scale.grid(row=row_idx, column=1, sticky="ew", padx=5)
            entry = ttk.Entry(settings_panel, textvariable=var, width=5)
            entry.grid(row=row_idx, column=2, sticky="e")
            row_idx += 1

        add_setting_slider("Min Snippet Duration (s):", self.min_snippet_duration_var, 1.0, 30.0)
        add_setting_slider("Max Snippet Duration (s):", self.max_snippet_duration_var, 1.0, 60.0)
        add_setting_slider("Target FPS:", self.fps_var, 10, 60, precision=0)
        add_setting_slider("BG Color Speed:", self.color_speed_var, 0.1, 2.0, precision=2)

        # Background Audio & Recording Section
        ttk.Separator(settings_panel).grid(row=row_idx, column=0, columnspan=3, sticky="ew", pady=15)
        row_idx += 1
        
        ttk.Checkbutton(settings_panel, text="Play Background Audio", variable=self.play_bg_audio_var).grid(row=row_idx, column=0, columnspan=2, sticky="w")
        row_idx += 1
        ttk.Button(settings_panel, text="Select BG Audio...", command=self._select_bg_audio_file).grid(row=row_idx, column=0, sticky="w", pady=4)
        self.bg_audio_label = ttk.Label(settings_panel, textvariable=self.bg_audio_file_path_var, wraplength=200)
        self.bg_audio_label.grid(row=row_idx, column=1, columnspan=2, sticky="ew", padx=5)
        row_idx += 1

        ttk.Separator(settings_panel).grid(row=row_idx, column=0, columnspan=3, sticky="ew", pady=15)
        row_idx += 1
        
        ttk.Checkbutton(settings_panel, text="Record to MP4", variable=self.record_video_var).grid(row=row_idx, column=0, columnspan=2, sticky="w")
        row_idx += 1
        ttk.Label(settings_panel, text="Output Filename:").grid(row=row_idx, column=0, sticky="w", pady=4)
        ttk.Entry(settings_panel, textvariable=self.record_filename_var).grid(row=row_idx, column=1, columnspan=2, sticky="ew", padx=5)
        row_idx += 1
        add_setting_slider("Recording Duration (s):", self.record_duration_var, 10, 1800, precision=0)

        # --- Bottom Buttons ---
        bottom_button_frame = ttk.Frame(main_frame, style='TFrame')
        bottom_button_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(15,0))
        bottom_button_frame.columnconfigure(0, weight=1)
        bottom_button_frame.columnconfigure(1, weight=1)
        run_button = ttk.Button(bottom_button_frame, text="Run Visualization", command=self._on_run_visualization, style="Accent.TButton")
        run_button.grid(row=0, column=0, sticky="ew", padx=(0,5))
        quit_button = ttk.Button(bottom_button_frame, text="Quit Program", command=self._on_quit)
        quit_button.grid(row=0, column=1, sticky="ew", padx=(5,0))

    def _populate_video_list_ui(self):
        """Rebuilds the UI list of video files."""
        for widget in self.video_list_frame.winfo_children():
            widget.destroy()
        
        for item_data in self.video_files_data:
            path, enabled_var = item_data['path'], item_data['enabled_var']
            entry_frame = ttk.Frame(self.video_list_frame, style='TFrame')
            entry_frame.pack(fill=tk.X, pady=1, padx=2)
            ttk.Checkbutton(entry_frame, variable=enabled_var).pack(side=tk.LEFT)
            
            filename = os.path.basename(path)
            label = ttk.Label(entry_frame, text=filename, anchor="w", cursor="hand2")
            label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=3)
            label.bind("<Button-1>", lambda e, var=enabled_var: var.set(not var.get()))
            
            remove_btn = ttk.Button(entry_frame, text="X", width=3, command=lambda p=path: self._remove_video_entry(p))
            remove_btn.pack(side=tk.RIGHT, padx=(3,0))
        
        self.master.after(50, lambda: self.canvas.configure(scrollregion=self.canvas.bbox("all")))

    def _add_new_videos(self):
        """Opens a dialog to add new video files."""
        file_paths = filedialog.askopenfilenames(
            master=self.master, title="Select Video Files",
            filetypes=(("Video Files", "*.mp4 *.mov *.avi *.mkv"), ("All files", "*.*"))
        )
        if not file_paths: return

        added_count = 0
        for path in file_paths:
            norm_path = os.path.normpath(path)
            if not any(item['path'] == norm_path for item in self.video_files_data):
                enabled_var = tk.BooleanVar(value=True)
                enabled_var.trace_add("write", self._save_configuration)
                self.video_files_data.append({'path': norm_path, 'enabled_var': enabled_var})
                added_count += 1
        
        if added_count > 0:
            self._populate_video_list_ui()
            self._save_configuration()

    def _remove_video_entry(self, path_to_remove):
        self.video_files_data = [item for item in self.video_files_data if item['path'] != path_to_remove]
        self._populate_video_list_ui()
        self._save_configuration()

    def _toggle_all_videos(self, select=True):
        for item in self.video_files_data:
            item['enabled_var'].set(select)

    def _select_bg_audio_file(self):
        filepath = filedialog.askopenfilename(
            master=self.master, title="Select Background Audio File",
            filetypes=(("Audio Files", "*.mp3 *.wav *.ogg"), ("All files", "*.*"))
        )
        if filepath:
            self.bg_audio_file_path_var.set(filepath)

    def _on_run_visualization(self):
        if not MOVIEPY_AVAILABLE:
            messagebox.showerror("Dependency Error", "MoviePy is not installed.\nCannot run visualization.\nPlease run: pip install moviepy", parent=self.master)
            return
            
        if self.min_snippet_duration_var.get() > self.max_snippet_duration_var.get():
            messagebox.showerror("Settings Error", "Min Snippet Duration cannot be greater than Max Snippet Duration.", parent=self.master)
            return

        selected_files = [item['path'] for item in self.video_files_data if item['enabled_var'].get()]
        if not selected_files:
            messagebox.showwarning("No Videos Selected", "Please add and select at least one video file.", parent=self.master)
            return

        self.master.withdraw()
        
        run_pygame_visualization(
            selected_files, self.system_screen_w, self.system_screen_h,
            p_fps=self.fps_var.get(),
            p_color_change_speed=self.color_speed_var.get(),
            p_min_snippet_duration=self.min_snippet_duration_var.get(),
            p_max_snippet_duration=self.max_snippet_duration_var.get(),
            background_audio_path=self.bg_audio_file_path_var.get(),
            play_background_audio=self.play_bg_audio_var.get(),
            record_video=self.record_video_var.get(),
            record_duration=self.record_duration_var.get(),
            record_filename=self.record_filename_var.get()
        )
        
        self.master.deiconify()
        self.master.lift()
        self.master.focus_force()

    def _on_quit(self):
        self._save_configuration()
        self.master.quit()
        self.master.destroy()

# --- Main Application Entry ---
if __name__ == '__main__':
    if not MOVIEPY_AVAILABLE:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Dependency Missing: MoviePy",
                               "The 'moviepy' library is required for this program but was not found.\n\n"
                               "Please install it by running this command in your terminal:\n"
                               "pip install moviepy\n\n"
                               "You will also need to have FFMPEG installed on your system.",
                               parent=None)
        exit()

    # Get screen dimensions
    temp_root = tk.Tk()
    temp_root.withdraw()
    screen_width = temp_root.winfo_screenwidth()
    screen_height = temp_root.winfo_screenheight()
    temp_root.destroy()

    root = tk.Tk()
    app = VideoSnippetGUI(root, screen_width, screen_height)
    root.mainloop()
    print("Application has exited.")