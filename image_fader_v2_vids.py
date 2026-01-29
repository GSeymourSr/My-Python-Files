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
import threading
import queue
from datetime import datetime

try:
    from moviepy.editor import VideoFileClip
    MOVIEPY_AVAILABLE = True
except ImportError:
    MOVIEPY_AVAILABLE = False

# --- Configuration Defaults ---
DEFAULT_FPS = 30
DEFAULT_COLOR_CHANGE_SPEED = 0.3
DEFAULT_MIN_SNIPPET_DURATION = 5.0
DEFAULT_MAX_SNIPPET_DURATION = 10.0
DEFAULT_SMART_SNIPPET_ENABLED = True
DEFAULT_SMART_SNIPPET_THRESHOLD = 30.0 # Videos under 30s play fully
DEFAULT_VIDEO_SCALING_MODE = "Fit (Letterbox)" # or "Fill (Crop)"

CONFIG_FILE_NAME = "video_snippet_config_v2.json"
TEMP_AUDIO_FILENAME_TEMPLATE = os.path.join(tempfile.gettempdir(), "snippet_audio_{}.mp3")

# --- Helper Functions ---
def get_random_color():
    return (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))

def interpolate_color(color1, color2, factor):
    r = int(color1[0] + (color2[0] - color1[0]) * factor)
    g = int(color1[1] + (color2[1] - color1[1]) * factor)
    b = int(color1[2] + (color2[2] - color1[2]) * factor)
    return (max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b)))

def scale_surface(surface, target_w, target_h, mode='Fit (Letterbox)'):
    """Scales a pygame surface to a target resolution using fit or fill."""
    surf_w, surf_h = surface.get_size()
    if surf_w == 0 or surf_h == 0: return surface, pygame.Rect(0,0,0,0)

    if mode == 'Fill (Crop)':
        target_ratio = target_w / target_h
        surf_ratio = surf_w / surf_h
        if surf_ratio > target_ratio: # Wider than target
            scale = target_h / surf_h
        else: # Taller than or same as target
            scale = target_w / surf_w
        new_w, new_h = int(surf_w * scale), int(surf_h * scale)
        scaled_surf = pygame.transform.smoothscale(surface, (new_w, new_h))
        # Center the cropped image
        crop_rect = pygame.Rect((new_w - target_w) / 2, (new_h - target_h) / 2, target_w, target_h)
        return scaled_surf, crop_rect

    else: # 'Fit (Letterbox)'
        scale = min(target_w / surf_w, target_h / surf_h)
        new_w, new_h = int(surf_w * scale), int(surf_h * scale)
        scaled_surf = pygame.transform.smoothscale(surface, (new_w, new_h))
        return scaled_surf, None # No crop needed

# --- Video Snippet Preparation (for worker thread) ---
def prepare_next_snippet_worker(video_queue, clip_queue, stop_event, params):
    """Worker thread function to prepare video snippets in the background."""
    audio_file_counter = 0
    while not stop_event.is_set():
        try:
            # Wait for a request to prepare a new clip
            video_path = video_queue.get(timeout=1)
            print(f"[WORKER] Received request for: {os.path.basename(video_path)}")

            # --- Smart Snippet Logic ---
            with VideoFileClip(video_path) as clip:
                duration = clip.duration

            if params['smart_snippet_enabled'] and duration <= params['smart_snippet_threshold']:
                snippet_duration = duration
                start_time = 0
                print(f"[WORKER] Short video ({duration:.1f}s), playing fully.")
            else:
                min_dur = params['min_snippet_duration']
                max_dur = params['max_snippet_duration']
                snippet_duration = random.uniform(min_dur, min(max_dur, duration))
                if duration > snippet_duration:
                    start_time = random.uniform(0, duration - snippet_duration)
                else:
                    start_time = 0
                print(f"[WORKER] Long video ({duration:.1f}s), taking snippet.")

            end_time = start_time + snippet_duration
            
            # Use a unique temp file for each audio snippet to avoid conflicts
            audio_file_counter += 1
            temp_audio_path = TEMP_AUDIO_FILENAME_TEMPLATE.format(audio_file_counter)

            moviepy_clip = VideoFileClip(video_path, audio=True).subclip(start_time, end_time)
            
            audio_path_to_play = None
            if moviepy_clip.audio:
                moviepy_clip.audio.write_audiofile(temp_audio_path, codec='mp3', logger=None)
                audio_path_to_play = temp_audio_path

            frame_iterator = moviepy_clip.iter_frames(fps=params['fps'], dtype='uint8')
            
            # Put the prepared result in the output queue
            clip_queue.put((moviepy_clip, frame_iterator, audio_path_to_play))
            print(f"[WORKER] Snippet prepared and queued.")

        except queue.Empty:
            continue # Timeout waiting for a video, just loop again
        except Exception as e:
            print(f"[WORKER] ERROR preparing snippet: {e}")
            clip_queue.put(None) # Signal an error to the main thread

# --- Pygame Visualization Main Function ---
def run_pygame_visualization(params):
    """Main function for the Pygame loop, now with preloading."""
    if not MOVIEPY_AVAILABLE: return
    pygame.init()
    pygame.mixer.init()

    screen_width, screen_height = params['screen_width'], params['screen_height']
    screen = pygame.display.set_mode((screen_width, screen_height), pygame.FULLSCREEN | pygame.HWSURFACE | pygame.DOUBLEBUF)
    pygame.display.set_caption("Greg Seymour - AI Video Snippet Player")
    pygame.mouse.set_visible(False)
    clock = pygame.time.Clock()
    
    font = pygame.font.Font(None, 64)
    loading_text = font.render("Preparing Snippet...", True, (255, 255, 255))
    loading_rect = loading_text.get_rect(center=(screen_width / 2, screen_height / 2))

    # --- Threading and Queue Setup for Preloading ---
    video_request_queue = queue.Queue() # Main thread sends video paths here
    prepared_clip_queue = queue.Queue(maxsize=1) # Worker sends prepared clips here
    stop_worker_event = threading.Event()
    
    worker_thread = threading.Thread(target=prepare_next_snippet_worker,
                                     args=(video_request_queue, prepared_clip_queue, stop_worker_event, params))
    worker_thread.daemon = True
    worker_thread.start()

    # --- State Management ---
    current_state = "IDLE"
    moviepy_clip, frame_iterator = None, None
    video_frame_surface, video_crop_rect = None, None
    
    # Background color
    current_top_color, target_top_color = get_random_color(), get_random_color()
    current_bottom_color, target_bottom_color = get_random_color(), get_random_color()
    color_lerp_factor = 0.0

    # Prime the worker with the first two video requests
    if params['video_files']:
        video_request_queue.put(random.choice(params['video_files']))
        if len(params['video_files']) > 1:
            video_request_queue.put(random.choice(params['video_files']))

    running = True
    while running:
        dt = clock.tick(params['fps']) / 1000.0
        for event in pygame.event.get():
            if event.type in (pygame.QUIT, pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                running = False
        
        # --- State Machine for Video Playback ---
        if current_state == "IDLE":
            video_frame_surface = None
            if moviepy_clip:
                moviepy_clip.close()
            
            try:
                # Block until the first clip is ready
                result = prepared_clip_queue.get(timeout=0.5) 
                if result is None: # Worker signaled an error
                    current_state = "IDLE"
                    if not video_request_queue.full() and params['video_files']:
                         video_request_queue.put(random.choice(params['video_files']))
                    continue
                
                moviepy_clip, frame_iterator, audio_path = result
                if audio_path:
                    pygame.mixer.music.load(audio_path)
                    pygame.mixer.music.play()
                else:
                    pygame.mixer.music.stop()
                current_state = "PLAYING"
            except queue.Empty:
                current_state = "LOADING" # Show loading screen
                if not video_request_queue.full() and params['video_files']:
                    video_request_queue.put(random.choice(params['video_files']))
                if not params['video_files']: # No files to play
                    running = False

        # --- Draw Background ---
        color_lerp_factor = (color_lerp_factor + params['color_speed'] * dt) % 1.0
        display_top_color = interpolate_color(current_top_color, target_top_color, color_lerp_factor)
        display_bottom_color = interpolate_color(current_bottom_color, target_bottom_color, color_lerp_factor)
        for y in range(screen_height):
            c = interpolate_color(display_top_color, display_bottom_color, y / screen_height)
            pygame.draw.line(screen, c, (0, y), (screen_width, y))

        # --- Handle Frame Drawing and State Transitions ---
        if current_state == "LOADING":
            screen.blit(loading_text, loading_rect)
            current_state = "IDLE" # Immediately try to get clip again next frame

        elif current_state == "PLAYING":
            try:
                frame_np = next(frame_iterator)
                video_frame_surface = pygame.surfarray.make_surface(np.transpose(frame_np, (1, 0, 2)))
            except StopIteration:
                # Snippet finished, transition to the next preloaded one
                print("PYGAME: Snippet finished.")
                current_state = "IDLE"
                continue # Skip drawing old frame
            
            if video_frame_surface:
                scaled_surf, video_crop_rect = scale_surface(video_frame_surface, screen_width, screen_height, params['video_scaling_mode'])
                if video_crop_rect: # Fill mode
                    screen.blit(scaled_surf, (0, 0), video_crop_rect)
                else: # Fit mode
                    frame_rect = scaled_surf.get_rect(center=(screen_width / 2, screen_height / 2))
                    screen.blit(scaled_surf, frame_rect)
        
        pygame.display.flip()

    # --- Cleanup ---
    print("PYGAME: Visualization ended. Cleaning up...")
    stop_worker_event.set()
    worker_thread.join(timeout=2)
    pygame.mixer.quit()
    pygame.quit()
    
    # Clean up any leftover temp audio files
    for f in os.listdir(tempfile.gettempdir()):
        if f.startswith("snippet_audio_") and f.endswith(".mp3"):
            try:
                os.remove(os.path.join(tempfile.gettempdir(), f))
            except:
                pass


# --- Tkinter GUI Class ---
class VideoSnippetGUI:
    def __init__(self, master, screen_w, screen_h):
        self.master = master
        self.screen_w, self.screen_h = screen_w, screen_h
        self.master.title("Greg Seymour - AI Video Snippet Player v2")
        self.master.geometry(f"{int(screen_w*0.8)}x{int(screen_h*0.7)}")
        self.master.minsize(900, 600)
        
        self.video_files_data = []
        self._init_style()
        self._init_vars()
        self._define_presets()
        self._build_ui()
        self._load_configuration()
        self.master.protocol("WM_DELETE_WINDOW", self._on_quit)

    def _init_style(self):
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.bg_color = "#2E3440"; self.fg_color = "#E5E9F0"; self.frame_bg = "#3B4252"
        self.accent_color_1 = "#88C0D0"; self.accent_color_2 = "#BF616A"; self.button_color = "#5E81AC"
        self.entry_bg = "#4C566A"; self.tree_heading_bg = "#434C5E"
        self.style.configure('.', background=self.bg_color, foreground=self.fg_color, font=('Segoe UI', 10))
        self.style.configure('TFrame', background=self.frame_bg)
        self.style.configure('TLabel', background=self.frame_bg, foreground=self.fg_color)
        self.style.configure('TLabelframe', background=self.frame_bg, bordercolor=self.accent_color_1)
        self.style.configure('TLabelframe.Label', background=self.frame_bg, foreground=self.accent_color_1, font=('Segoe UI Semibold', 12))
        self.style.configure('TButton', background=self.button_color, foreground=self.bg_color, font=('Segoe UI Semibold', 10), padding=6)
        self.style.map('TButton', background=[('active', self.accent_color_1)])
        self.style.configure('Accent.TButton', background=self.accent_color_2, foreground='white', font=('Segoe UI Bold', 12), padding=8)
        self.style.map('Accent.TButton', background=[('active', '#D08770')])
        self.style.configure('TCheckbutton', background=self.frame_bg, foreground=self.fg_color)
        self.style.configure('TSpinbox', fieldbackground=self.entry_bg, foreground=self.fg_color)
        self.style.configure('Vertical.TScrollbar', background=self.button_color, troughcolor=self.frame_bg)
        self.style.configure('Horizontal.TScale', troughcolor=self.entry_bg, background=self.button_color)
        self.style.configure('Treeview', background=self.entry_bg, fieldbackground=self.entry_bg, foreground=self.fg_color)
        self.style.configure('Treeview.Heading', background=self.tree_heading_bg, foreground=self.accent_color_1, font=('Segoe UI Semibold', 10))
        self.style.map('Treeview.Heading', background=[('active', self.button_color)])
        self.title_font = tkFont.Font(family="Impact", size=28, weight="bold")

    def _init_vars(self):
        self.min_snippet_duration_var = tk.DoubleVar(value=DEFAULT_MIN_SNIPPET_DURATION)
        self.max_snippet_duration_var = tk.DoubleVar(value=DEFAULT_MAX_SNIPPET_DURATION)
        self.fps_var = tk.IntVar(value=DEFAULT_FPS)
        self.color_speed_var = tk.DoubleVar(value=DEFAULT_COLOR_CHANGE_SPEED)
        self.smart_snippet_enabled_var = tk.BooleanVar(value=DEFAULT_SMART_SNIPPET_ENABLED)
        self.smart_snippet_threshold_var = tk.DoubleVar(value=DEFAULT_SMART_SNIPPET_THRESHOLD)
        self.video_scaling_mode_var = tk.StringVar(value=DEFAULT_VIDEO_SCALING_MODE)
        self.setting_vars_map = {
            "min_snippet_duration": self.min_snippet_duration_var,
            "max_snippet_duration": self.max_snippet_duration_var,
            "color_speed": self.color_speed_var,
            "fps": self.fps_var,
            "smart_snippet_enabled": self.smart_snippet_enabled_var,
            "smart_snippet_threshold": self.smart_snippet_threshold_var,
            "video_scaling_mode": self.video_scaling_mode_var
        }
        for var in self.setting_vars_map.values():
            var.trace_add("write", self._on_setting_changed)

    def _on_setting_changed(self, *args):
        self._check_for_custom_preset()
        self._save_configuration()

    def _define_presets(self):
        self.presets = {
            "Custom": {},
            "Default": {"min_snippet_duration": 5.0, "max_snippet_duration": 10.0, "color_speed": 0.3},
            "Slow & Relaxing": {"min_snippet_duration": 15.0, "max_snippet_duration": 30.0, "color_speed": 0.1},
            "Exciting & Upbeat": {"min_snippet_duration": 3.0, "max_snippet_duration": 7.0, "color_speed": 0.8},
        }
        self.current_preset_var = tk.StringVar(value="Default")

    def _apply_preset(self, event=None):
        preset_settings = self.presets.get(self.current_preset_var.get())
        if not preset_settings: return
        self._pause_trace = True
        for key, value in preset_settings.items():
            if key in self.setting_vars_map:
                self.setting_vars_map[key].set(value)
        self._pause_trace = False
        self._save_configuration()

    def _check_for_custom_preset(self):
        if hasattr(self, '_pause_trace') and self._pause_trace: return
        current_settings = {k: v.get() for k, v in self.setting_vars_map.items()}
        matched_preset = None
        for name, values in self.presets.items():
            if name == "Custom": continue
            is_match = all(current_settings.get(k) == v for k, v in values.items())
            if is_match:
                matched_preset = name
                break
        self.current_preset_var.set(matched_preset if matched_preset else "Custom")

    def _build_ui(self):
        self.master.configure(background=self.bg_color)
        main_frame = ttk.Frame(self.master, style='TFrame', padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True)
        main_frame.columnconfigure(0, weight=3)
        main_frame.columnconfigure(1, weight=2)
        main_frame.rowconfigure(1, weight=1)

        title = ttk.Label(main_frame, text="AI Video Snippet Player", font=self.title_font, foreground=self.accent_color_1, background=self.bg_color)
        title.grid(row=0, column=0, columnspan=2, pady=(0, 20), sticky="ew")

        # --- Left Panel: Video Files ---
        video_panel = ttk.LabelFrame(main_frame, text="Video Files", style='TLabelframe')
        video_panel.grid(row=1, column=0, sticky="nsew", padx=(0, 10))
        video_panel.rowconfigure(1, weight=1)
        video_panel.columnconfigure(0, weight=1)

        # Buttons
        btn_frame = ttk.Frame(video_panel, style='TFrame')
        btn_frame.grid(row=0, column=0, sticky="ew", pady=5, padx=5)
        ttk.Button(btn_frame, text="Add Video(s)", command=self._add_new_videos).pack(side=tk.LEFT, padx=2)
        
        sort_label = ttk.Label(btn_frame, text="Sort By:")
        sort_label.pack(side=tk.LEFT, padx=(10, 2))
        self.sort_combo = ttk.Combobox(btn_frame, values=["A-Z (Filename)", "Date (Newest)", "Size (Largest)"], state="readonly", width=15)
        self.sort_combo.pack(side=tk.LEFT, padx=2)
        self.sort_combo.set("A-Z (Filename)")
        self.sort_combo.bind("<<ComboboxSelected>>", self._sort_videos)

        ttk.Button(btn_frame, text="Clear All", command=self._clear_all_videos).pack(side=tk.RIGHT, padx=2)

        # Treeview for file list
        tree_frame = ttk.Frame(video_panel)
        tree_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=(0,5))
        tree_frame.rowconfigure(0, weight=1)
        tree_frame.columnconfigure(0, weight=1)

        self.tree = ttk.Treeview(tree_frame, columns=('size', 'date'), show='headings')
        self.tree.heading('size', text='Size', command=lambda: self._sort_videos(sort_key='size'))
        self.tree.heading('date', text='Date Modified', command=lambda: self._sort_videos(sort_key='date'))
        self.tree.column('size', width=100, anchor='e')
        self.tree.column('date', width=150, anchor='w')
        # Add a hidden column for the full path
        self.tree['displaycolumns'] = ('size', 'date')
        self.tree.heading('#0', text='Filename', command=lambda: self._sort_videos(sort_key='name'))
        self.tree.column('#0', stretch=True)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, columnspan=2, sticky='ew')
        
        # --- Right Panel: Settings ---
        settings_panel = ttk.LabelFrame(main_frame, text="Settings", style='TLabelframe', padding=10)
        settings_panel.grid(row=1, column=1, sticky="nsew", padx=(10,0))
        settings_panel.columnconfigure(1, weight=1)

        row = 0
        # Presets
        ttk.Label(settings_panel, text="Preset:").grid(row=row, column=0, sticky="w", pady=5)
        preset_combo = ttk.Combobox(settings_panel, textvariable=self.current_preset_var, values=list(self.presets.keys()), state="readonly")
        preset_combo.grid(row=row, column=1, columnspan=2, sticky="ew", padx=5)
        preset_combo.bind("<<ComboboxSelected>>", self._apply_preset)
        row += 1

        # Sliders
        def add_slider(label, var, from_, to):
            nonlocal row
            ttk.Label(settings_panel, text=label).grid(row=row, column=0, sticky="w", pady=4)
            ttk.Scale(settings_panel, variable=var, from_=from_, to=to).grid(row=row, column=1, sticky="ew", padx=5)
            ttk.Spinbox(settings_panel, textvariable=var, from_=from_, to=to, increment=0.1 if isinstance(var, tk.DoubleVar) else 1, width=6).grid(row=row, column=2)
            row += 1
        
        add_slider("Min Snippet (s):", self.min_snippet_duration_var, 1.0, 60.0)
        add_slider("Max Snippet (s):", self.max_snippet_duration_var, 1.0, 120.0)
        add_slider("BG Color Speed:", self.color_speed_var, 0.1, 2.0)
        add_slider("Target FPS:", self.fps_var, 10, 60)

        # Smart Snippet
        ttk.Separator(settings_panel).grid(row=row, column=0, columnspan=3, sticky="ew", pady=10); row+=1
        check = ttk.Checkbutton(settings_panel, text="Play short videos fully (under...)", variable=self.smart_snippet_enabled_var)
        check.grid(row=row, column=0, columnspan=2, sticky="w")
        ttk.Spinbox(settings_panel, textvariable=self.smart_snippet_threshold_var, from_=5, to=300, increment=5, width=6).grid(row=row, column=2)
        row += 1

        # Video Scaling
        ttk.Separator(settings_panel).grid(row=row, column=0, columnspan=3, sticky="ew", pady=10); row+=1
        ttk.Label(settings_panel, text="Video Scaling:").grid(row=row, column=0, sticky="w")
        scaling_combo = ttk.Combobox(settings_panel, textvariable=self.video_scaling_mode_var, values=["Fit (Letterbox)", "Fill (Crop)"], state="readonly")
        scaling_combo.grid(row=row, column=1, columnspan=2, sticky="ew", padx=5)
        row += 1

        # Bottom Buttons
        bottom_frame = ttk.Frame(main_frame, style='TFrame')
        bottom_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(15, 0))
        bottom_frame.columnconfigure(0, weight=1)
        ttk.Button(bottom_frame, text="Run Visualization", command=self._on_run, style="Accent.TButton").pack(fill=tk.X)
    
    # --- UI Logic ---
    def _add_new_videos(self):
        paths = filedialog.askopenfilenames(filetypes=(("Video Files", "*.mp4 *.mov *.avi *.mkv"), ("All", "*.*")))
        if not paths: return
        
        for path in paths:
            norm_path = os.path.normpath(path)
            if not any(item['path'] == norm_path for item in self.video_files_data):
                try:
                    stats = os.stat(norm_path)
                    self.video_files_data.append({
                        'path': norm_path,
                        'size': stats.st_size,
                        'mtime': stats.st_mtime
                    })
                except OSError as e:
                    print(f"Could not get stats for file {norm_path}: {e}")
        
        self._populate_video_list_ui()
        self._save_configuration()
    
    def _clear_all_videos(self):
        if messagebox.askyesno("Confirm Clear", "Are you sure you want to remove all videos from the list?"):
            self.video_files_data = []
            self._populate_video_list_ui()
            self._save_configuration()

    def _sort_videos(self, event=None, sort_key=None):
        if sort_key is None:
            sort_map = {"A-Z (Filename)": "name", "Date (Newest)": "date", "Size (Largest)": "size"}
            sort_key = sort_map.get(self.sort_combo.get())

        reverse = sort_key in ['date', 'size']
        key_map = {'name': lambda x: x['path'], 'date': lambda x: x['mtime'], 'size': lambda x: x['size']}
        
        self.video_files_data.sort(key=key_map[sort_key], reverse=reverse)
        self._populate_video_list_ui()

    def _populate_video_list_ui(self):
        self.tree.delete(*self.tree.get_children())
        for item in self.video_files_data:
            filename = os.path.basename(item['path'])
            size_mb = f"{item['size'] / (1024*1024):.1f} MB"
            mod_time = datetime.fromtimestamp(item['mtime']).strftime('%Y-%m-%d %H:%M')
            # The full path is stored implicitly with the item id (text field)
            self.tree.insert('', 'end', text=filename, values=(size_mb, mod_time), iid=item['path'])

    def _get_config_path(self):
        return os.path.join(os.path.expanduser("~"), CONFIG_FILE_NAME)

    def _save_configuration(self, *args):
        if hasattr(self, '_pause_trace') and self._pause_trace: return
        settings = {k: v.get() for k, v in self.setting_vars_map.items()}
        # Only save paths, not full metadata
        files_to_save = [{'path': item['path']} for item in self.video_files_data]
        try:
            with open(self._get_config_path(), 'w') as f:
                json.dump({"settings": settings, "video_files": files_to_save}, f, indent=4)
        except Exception as e:
            print(f"Error saving config: {e}")

    def _load_configuration(self):
        path = self._get_config_path()
        if not os.path.exists(path): return
        try:
            with open(path, 'r') as f:
                data = json.load(f)
            
            self._pause_trace = True
            settings = data.get("settings", {})
            for k, v in settings.items():
                if k in self.setting_vars_map: self.setting_vars_map[k].set(v)
            self._pause_trace = False

            self.video_files_data = []
            for item in data.get("video_files", []):
                filepath = item.get('path')
                if filepath and os.path.isfile(filepath):
                    stats = os.stat(filepath)
                    self.video_files_data.append({'path': filepath, 'size': stats.st_size, 'mtime': stats.st_mtime})

            self._populate_video_list_ui()
            self._check_for_custom_preset()
        except Exception as e:
            print(f"Error loading config: {e}")
            
    def _on_run(self):
        if not MOVIEPY_AVAILABLE:
            messagebox.showerror("Dependency Error", "MoviePy is not installed.")
            return

        selected_files = [item['path'] for item in self.video_files_data]
        if not selected_files:
            messagebox.showwarning("No Videos", "Please add at least one video file.")
            return
            
        params = {
            "screen_width": self.screen_w, "screen_height": self.screen_h,
            "video_files": selected_files,
            **{k: v.get() for k, v in self.setting_vars_map.items()}
        }
        
        self.master.withdraw()
        run_pygame_visualization(params)
        self.master.deiconify()

    def _on_quit(self):
        self._save_configuration()
        self.master.destroy()

# --- Main Application Entry ---
if __name__ == '__main__':
    if not MOVIEPY_AVAILABLE:
        root = tk.Tk(); root.withdraw()
        messagebox.showerror("Dependency Missing", "MoviePy is required. Please run: pip install moviepy")
        exit()

    temp_root = tk.Tk()
    screen_w = temp_root.winfo_screenwidth()
    screen_h = temp_root.winfo_screenheight()
    temp_root.destroy()

    root = tk.Tk()
    app = VideoSnippetGUI(root, screen_w, screen_h)
    root.mainloop()