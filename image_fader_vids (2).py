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
import atexit

# --- Dependency Check ---
try:
    from moviepy.editor import VideoFileClip, AudioFileClip, ImageSequenceClip
    MOVIEPY_AVAILABLE = True
except ImportError:
    MOVIEPY_AVAILABLE = False
    print("WARNING: moviepy library not found. Video features and recording will be disabled.")
    print("Please install it: pip install moviepy")
    print("You might also need FFMPEG installed and in your system PATH.")

# --- Configuration Defaults ---
DEFAULT_FPS = 30
DEFAULT_COLOR_CHANGE_SPEED = 0.3
# Image Fader Defaults
DEFAULT_MIN_FADE_TIME = 1.0; DEFAULT_MAX_FADE_TIME = 2.0
DEFAULT_MIN_VISIBLE_TIME = 0.3; DEFAULT_MAX_VISIBLE_TIME = 1.5
DEFAULT_MIN_SPAWN_DELAY = 0.5; DEFAULT_MAX_SPAWN_DELAY = 1.0
DEFAULT_SCALE_MEDIA = True
DEFAULT_MAX_MEDIA_WIDTH_PERCENT = 0.75; DEFAULT_MAX_MEDIA_HEIGHT_PERCENT = 0.75
DEFAULT_MAX_MEDIA_ON_SCREEN = 10
# Video Snippet Defaults
DEFAULT_MIN_SNIPPET_DURATION = 5.0; DEFAULT_MAX_SNIPPET_DURATION = 10.0
DEFAULT_SMART_SNIPPET_ENABLED = True
DEFAULT_SMART_SNIPPET_THRESHOLD = 30.0 # Videos under 30s play fully

CONFIG_FILE_NAME = "unified_visualizer_config_v1.json"
TEMP_AUDIO_DIR = os.path.join(tempfile.gettempdir(), "unified_visualizer_audio")
os.makedirs(TEMP_AUDIO_DIR, exist_ok=True)

# --- Cleanup for Temp Files ---
def cleanup_temp_files():
    """Remove temporary audio files on exit."""
    print("Cleaning up temporary audio files...")
    try:
        for f in os.listdir(TEMP_AUDIO_DIR):
            os.remove(os.path.join(TEMP_AUDIO_DIR, f))
        os.rmdir(TEMP_AUDIO_DIR)
    except Exception as e:
        print(f"Error during cleanup: {e}")
atexit.register(cleanup_temp_files)


# --- Helper Functions ---
def get_random_color():
    return (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))

def interpolate_color(color1, color2, factor):
    r = int(color1[0] + (color2[0] - color1[0]) * factor)
    g = int(color1[1] + (color2[1] - color1[1]) * factor)
    b = int(color1[2] + (color2[2] - color1[2]) * factor)
    return (max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b)))

def scale_surface_and_get_rect(surface, screen_w, screen_h, p):
    """Scales a surface according to params and returns a random rect."""
    surf_w, surf_h = surface.get_size()
    if surf_w == 0 or surf_h == 0: return surface, pygame.Rect(0,0,0,0)

    if p['scale_media']:
        max_w = screen_w * p['max_media_width_percent']
        max_h = screen_h * p['max_media_height_percent']
        if surf_w > max_w or surf_h > max_h:
            scale = min(max_w / surf_w, max_h / surf_h)
            new_w, new_h = max(1, int(surf_w * scale)), max(1, int(surf_h * scale))
            try:
                surface = pygame.transform.smoothscale(surface, (new_w, new_h))
            except (pygame.error, ValueError):
                pass # Use original on error

    rect = surface.get_rect()
    rect.x = random.randint(0, max(0, screen_w - rect.width))
    rect.y = random.randint(0, max(0, screen_h - rect.height))
    return surface, rect

# --- Pygame Media Classes ---
class FadingMedia:
    """Base class for any media object that appears on screen."""
    def __init__(self, p):
        self.state = "fading_in"
        self.alpha = 0
        self.timer = 0.0
        self.fade_in_duration = random.uniform(p['min_fade_time'], p['max_fade_time'])
        self.visible_duration = random.uniform(p['min_visible_time'], p['max_visible_time'])
        self.fade_out_duration = random.uniform(p['min_fade_time'], p['max_fade_time'])
        self.surface = None # Must be set by subclass

    def update(self, dt):
        self.timer += dt
        if self.state == "fading_in":
            self.alpha = min(255, (self.timer / self.fade_in_duration) * 255) if self.fade_in_duration > 0 else 255
            if self.timer >= self.fade_in_duration:
                self.alpha = 255; self.state = "visible"; self.timer = 0.0
        elif self.state == "visible":
            if self.timer >= self.visible_duration:
                self.state = "fading_out"; self.timer = 0.0
        elif self.state == "fading_out":
            self.alpha = max(0, 255 - (self.timer / self.fade_out_duration) * 255) if self.fade_out_duration > 0 else 0
            if self.timer >= self.fade_out_duration:
                return False # Signal removal
        return True

    def draw(self, screen):
        if self.surface:
            self.surface.set_alpha(int(self.alpha))
            screen.blit(self.surface, self.rect)

class FadingImage(FadingMedia):
    def __init__(self, image_path, screen_w, screen_h, p):
        super().__init__(p)
        try:
            loaded_surface = pygame.image.load(image_path).convert_alpha()
            self.original_surface, self.rect = scale_surface_and_get_rect(loaded_surface, screen_w, screen_h, p)
            self.surface = self.original_surface.copy()
        except Exception as e:
            print(f"ERROR loading image {image_path}: {e}")
            self.surface = None # Mark as invalid

class FadingVideoSnippet(FadingMedia):
    def __init__(self, prep_result, screen_w, screen_h, p):
        super().__init__(p)
        self.moviepy_clip, self.frame_iterator, self.audio_sound = prep_result
        self.is_valid = self.moviepy_clip is not None

        if not self.is_valid:
            return

        # Get first frame to determine size
        try:
            first_frame_np = next(self.frame_iterator)
            frame_surface = pygame.surfarray.make_surface(np.transpose(first_frame_np, (1, 0, 2)))
            self.original_surface, self.rect = scale_surface_and_get_rect(frame_surface, screen_w, screen_h, p)
            self.surface = self.original_surface.copy()
        except Exception as e:
            print(f"ERROR initializing video snippet: {e}")
            self.is_valid = False
            self.cleanup()
            return

        if self.audio_sound:
            self.audio_sound.set_volume(0.7) # Avoid being too loud

    def update(self, dt):
        if not self.is_valid: return False
        
        is_alive = super().update(dt)

        if self.state == "visible" and self.timer == 0.0 and self.audio_sound:
            self.audio_sound.play()

        if self.state == "fading_out" and self.audio_sound:
             # Fade out sound with video
            vol = max(0, 1.0 - (self.timer / self.fade_out_duration)) if self.fade_out_duration > 0 else 0
            self.audio_sound.set_volume(vol * 0.7)

        if not is_alive:
            self.cleanup()
            return False

        # Get next frame if visible or fading out
        if self.state in ["visible", "fading_out"]:
            try:
                frame_np = next(self.frame_iterator)
                current_frame_surf = pygame.surfarray.make_surface(np.transpose(frame_np, (1, 0, 2)))
                # Rescale every frame in case of performance issues.
                # In practice, for snippets, it's better to scale once.
                # For this implementation, we'll blit to a surface of the correct size.
                pygame.transform.smoothscale(current_frame_surf, self.rect.size, self.surface)
            except StopIteration:
                self.visible_duration = self.timer # End visibility now
                return super().update(0) # Re-evaluate state immediately
            except Exception as e:
                print(f"ERROR processing video frame: {e}")
                self.cleanup()
                return False
        
        return True

    def cleanup(self):
        if self.audio_sound: self.audio_sound.stop()
        if self.moviepy_clip: self.moviepy_clip.close()
        self.is_valid = False

# --- Video Snippet Preparation Worker ---
def prepare_video_snippet_worker(request_q, ready_q, stop_event, p):
    """Worker thread to prepare video snippets in the background."""
    if not MOVIEPY_AVAILABLE: return
    
    while not stop_event.is_set():
        try:
            video_path = request_q.get(timeout=1)
            print(f"[WORKER] Preparing snippet for: {os.path.basename(video_path)}")
            
            with VideoFileClip(video_path) as clip:
                duration = clip.duration

            if p['smart_snippet_enabled'] and duration <= p['smart_snippet_threshold']:
                snippet_duration = duration
                start_time = 0
            else:
                min_dur = p['min_snippet_duration']
                max_dur = p['max_snippet_duration']
                snippet_duration = random.uniform(min_dur, min(max_dur, duration))
                start_time = random.uniform(0, duration - snippet_duration) if duration > snippet_duration else 0
            
            end_time = start_time + snippet_duration
            moviepy_clip = VideoFileClip(video_path, audio=True).subclip(start_time, end_time)
            
            audio_sound = None
            if moviepy_clip.audio:
                try:
                    # Use a unique temp file for each audio snippet to avoid conflicts
                    # WAV is required for pygame.mixer.Sound
                    temp_audio_path = os.path.join(TEMP_AUDIO_DIR, f"snippet_{time.time_ns()}.wav")
                    moviepy_clip.audio.write_audiofile(temp_audio_path, codec='pcm_s16le', logger=None)
                    audio_sound = pygame.mixer.Sound(temp_audio_path)
                except Exception as e:
                    print(f"[WORKER] ERROR creating audio for snippet: {e}")

            frame_iterator = moviepy_clip.iter_frames(fps=p['fps'], dtype='uint8')
            ready_q.put((moviepy_clip, frame_iterator, audio_sound))

        except queue.Empty:
            continue
        except Exception as e:
            print(f"[WORKER] FATAL ERROR preparing snippet: {e}")
            ready_q.put((None, None, None)) # Signal failure


# --- Main Pygame Visualization Function ---
def run_pygame_visualization(p):
    pygame.init()
    # Initialize mixer with robust settings to avoid conflicts
    try:
        pygame.mixer.pre_init(44100, -16, 2, 2048)
        pygame.mixer.init()
        pygame.mixer.set_num_channels(32) # Allow more simultaneous sounds
    except pygame.error as e:
        print(f"PYGAME: Could not initialize audio mixer: {e}. Audio will be disabled.")
        p['mode'] = "Images Only" # Fallback

    screen = pygame.display.set_mode((p['screen_w'], p['screen_h']), pygame.FULLSCREEN | pygame.HWSURFACE | pygame.DOUBLEBUF)
    pygame.display.set_caption("Unified Visualization Tool")
    pygame.mouse.set_visible(False)
    clock = pygame.time.Clock()

    # --- Worker Thread Setup for Videos ---
    video_request_queue = queue.Queue(maxsize=5)
    prepared_video_queue = queue.Queue(maxsize=2)
    stop_worker_event = threading.Event()
    worker_thread = threading.Thread(target=prepare_video_snippet_worker,
                                     args=(video_request_queue, prepared_video_queue, stop_worker_event, p))
    worker_thread.daemon = True
    if any(s['type'] == 'Video' for s in p['media_sources']):
        worker_thread.start()

    # --- Media Source Loading ---
    image_paths = []
    video_paths = []
    for source in p['media_sources']:
        if source['type'] == 'Images':
            supported_formats = ('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp')
            try:
                for filename in os.listdir(source['path']):
                    if filename.lower().endswith(supported_formats):
                        image_paths.append(os.path.join(source['path'], filename))
            except OSError as e:
                print(f"PYGAME Error accessing directory {source['path']}: {e}")
        elif source['type'] == 'Video':
            video_paths.append(source['path'])

    if p['mode'] == 'Images Only' and not image_paths:
        messagebox.showwarning("No Images", "Images Only mode selected, but no valid image sources found.")
        return
    if p['mode'] == 'Video Snippets as Pop-ups' and not video_paths:
        messagebox.showwarning("No Videos", "Video Snippets mode selected, but no video files found.")
        return
    
    available_image_paths = []
    def replenish_image_paths():
        nonlocal available_image_paths
        if not image_paths: return
        available_image_paths = image_paths[:] 
        random.shuffle(available_image_paths)
    replenish_image_paths()

    # Prime video worker
    if video_paths:
        for _ in range(min(5, len(video_paths))):
            video_request_queue.put(random.choice(video_paths))
    
    # --- State Management ---
    active_media = []
    next_spawn_time = time.time()
    current_top_color, target_top_color = get_random_color(), get_random_color()
    current_bottom_color, target_bottom_color = get_random_color(), get_random_color()
    color_lerp_factor = 0.0

    # --- Background Video Setup ---
    bg_video_clip, bg_video_iterator = None, None
    if p['mode'] == 'Video Background with Images':
        if video_paths:
            bg_vid_path = random.choice(video_paths)
            try:
                bg_video_clip = VideoFileClip(bg_vid_path)
                bg_video_iterator = bg_video_clip.iter_frames(fps=p['fps'], dtype='uint8')
                print(f"PYGAME: Using {os.path.basename(bg_vid_path)} as background.")
            except Exception as e:
                print(f"PYGAME ERROR: Could not load background video: {e}")
                p['mode'] = 'Images Only' # Fallback
        else:
            print("PYGAME WARNING: Video Background mode selected but no videos found. Falling back to Images Only.")
            p['mode'] = 'Images Only'

    # --- Main Loop ---
    running = True
    while running:
        dt = clock.tick(p['fps']) / 1000.0
        current_time = time.time()

        for event in pygame.event.get():
            if event.type in (pygame.QUIT, pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                running = False
        
        # --- Background Drawing ---
        if p['mode'] == 'Video Background with Images' and bg_video_iterator:
            try:
                frame_np = next(bg_video_iterator)
                frame_surf = pygame.surfarray.make_surface(np.transpose(frame_np, (1, 0, 2)))
                # Scale to fill screen (cropping may occur)
                scaled_surf = pygame.transform.scale(frame_surf, (p['screen_w'], p['screen_h']))
                screen.blit(scaled_surf, (0, 0))
            except StopIteration: # Loop video
                bg_video_iterator = bg_video_clip.iter_frames(fps=p['fps'], dtype='uint8')
            except Exception as e:
                print(f"PYGAME ERROR drawing background video frame: {e}")
                running = False
        else: # Gradient background
            color_lerp_factor = (color_lerp_factor + p['color_speed'] * dt) % 1.0
            display_top_color = interpolate_color(current_top_color, target_top_color, color_lerp_factor)
            display_bottom_color = interpolate_color(current_bottom_color, target_bottom_color, color_lerp_factor)
            for y in range(p['screen_h']):
                c = interpolate_color(display_top_color, display_bottom_color, y / p['screen_h'])
                pygame.draw.line(screen, c, (0, y), (p['screen_w'], y))

        # --- Media Spawning Logic ---
        if len(active_media) < p['max_media_on_screen'] and current_time >= next_spawn_time:
            media_type_to_spawn = None
            if p['mode'] == 'Images Only' or p['mode'] == 'Video Background with Images':
                if image_paths: media_type_to_spawn = 'Image'
            elif p['mode'] == 'Video Snippets as Pop-ups':
                if video_paths: media_type_to_spawn = 'Video'
            elif p['mode'] == 'Mixed Media Pop-ups':
                choices = []
                if image_paths: choices.append('Image')
                if video_paths: choices.append('Video')
                if choices: media_type_to_spawn = random.choice(choices)

            new_media = None
            if media_type_to_spawn == 'Image':
                if not available_image_paths: replenish_image_paths()
                if available_image_paths:
                    img_path = available_image_paths.pop(0)
                    new_media = FadingImage(img_path, p['screen_w'], p['screen_h'], p)
            elif media_type_to_spawn == 'Video':
                try:
                    prep_result = prepared_video_queue.get_nowait()
                    if prep_result[0] is not None:
                        new_media = FadingVideoSnippet(prep_result, p['screen_w'], p['screen_h'], p)
                    if video_paths and not video_request_queue.full():
                        video_request_queue.put(random.choice(video_paths))
                except queue.Empty:
                    pass # Wait for worker

            if new_media and getattr(new_media, 'surface', None):
                active_media.append(new_media)
                next_spawn_time = current_time + random.uniform(p['min_spawn_delay'], p['max_spawn_delay'])

        # --- Update and Draw Active Media ---
        active_media[:] = [m for m in active_media if m.update(dt)]
        for m in active_media:
            m.draw(screen)

        pygame.display.flip()

    # --- Cleanup ---
    print("PYGAME: Visualization ended. Cleaning up...")
    for m in active_media:
        if isinstance(m, FadingVideoSnippet): m.cleanup()
    if bg_video_clip: bg_video_clip.close()
    
    stop_worker_event.set()
    if worker_thread.is_alive():
        # Clear queue to unblock worker
        while not video_request_queue.empty():
            try: video_request_queue.get_nowait()
            except queue.Empty: break
        worker_thread.join(timeout=2)
    
    pygame.mixer.quit()
    pygame.quit()


# --- Tkinter GUI Class ---
class VisualizationToolGUI:
    def __init__(self, master, screen_w, screen_h):
        self.master = master
        self.screen_w, self.screen_h = screen_w, screen_h
        self.master.title("Unified Visualization Tool v1.0")
        self.master.geometry(f"{int(screen_w*0.8)}x{int(screen_h*0.7)}")
        self.master.minsize(1100, 700)
        
        self.media_sources_data = [] # List of dicts: {'path':, 'type':, 'enabled_var':}
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
        self.style.configure('TRadiobutton', background=self.frame_bg, foreground=self.fg_color)
        self.style.map('TRadiobutton', indicatorcolor=[('selected', self.accent_color_1)])
        self.style.configure('TLabelframe', background=self.frame_bg, bordercolor=self.accent_color_1)
        self.style.configure('TLabelframe.Label', background=self.frame_bg, foreground=self.accent_color_1, font=('Segoe UI Semibold', 12))
        self.style.configure('TButton', background=self.button_color, foreground='white', padding=6)
        self.style.map('TButton', background=[('active', self.accent_color_1)])
        self.style.configure('Accent.TButton', background=self.accent_color_2, foreground='white', font=('Segoe UI Bold', 12), padding=8)
        self.style.map('Accent.TButton', background=[('active', '#D08770')])
        self.style.configure('TCheckbutton', background=self.frame_bg, foreground=self.fg_color)
        self.style.configure('Treeview', background=self.entry_bg, fieldbackground=self.entry_bg, foreground=self.fg_color, rowheight=25)
        self.style.configure('Treeview.Heading', background=self.tree_heading_bg, foreground=self.accent_color_1, font=('Segoe UI Semibold', 10))
        self.style.map('Treeview.Heading', background=[('active', self.button_color)])
        self.title_font = tkFont.Font(family="Impact", size=28, weight="bold")

    def _init_vars(self):
        # General
        self.visualization_mode_var = tk.StringVar(value="Mixed Media Pop-ups")
        self.fps_var = tk.IntVar(value=DEFAULT_FPS)
        self.color_speed_var = tk.DoubleVar(value=DEFAULT_COLOR_CHANGE_SPEED)
        # Media Pop-up Settings
        self.min_fade_time_var = tk.DoubleVar(value=DEFAULT_MIN_FADE_TIME)
        self.max_fade_time_var = tk.DoubleVar(value=DEFAULT_MAX_FADE_TIME)
        self.min_visible_time_var = tk.DoubleVar(value=DEFAULT_MIN_VISIBLE_TIME)
        self.max_visible_time_var = tk.DoubleVar(value=DEFAULT_MAX_VISIBLE_TIME)
        self.min_spawn_delay_var = tk.DoubleVar(value=DEFAULT_MIN_SPAWN_DELAY)
        self.max_spawn_delay_var = tk.DoubleVar(value=DEFAULT_MAX_SPAWN_DELAY)
        self.scale_media_var = tk.BooleanVar(value=DEFAULT_SCALE_MEDIA)
        self.max_media_width_percent_var = tk.DoubleVar(value=DEFAULT_MAX_MEDIA_WIDTH_PERCENT)
        self.max_media_height_percent_var = tk.DoubleVar(value=DEFAULT_MAX_MEDIA_HEIGHT_PERCENT)
        self.max_media_on_screen_var = tk.IntVar(value=DEFAULT_MAX_MEDIA_ON_SCREEN)
        # Video Specific Settings
        self.min_snippet_duration_var = tk.DoubleVar(value=DEFAULT_MIN_SNIPPET_DURATION)
        self.max_snippet_duration_var = tk.DoubleVar(value=DEFAULT_MAX_SNIPPET_DURATION)
        self.smart_snippet_enabled_var = tk.BooleanVar(value=DEFAULT_SMART_SNIPPET_ENABLED)
        self.smart_snippet_threshold_var = tk.DoubleVar(value=DEFAULT_SMART_SNIPPET_THRESHOLD)
        
        self.setting_vars_map = {
            "mode": self.visualization_mode_var, "fps": self.fps_var, "color_speed": self.color_speed_var,
            "min_fade_time": self.min_fade_time_var, "max_fade_time": self.max_fade_time_var,
            "min_visible_time": self.min_visible_time_var, "max_visible_time": self.max_visible_time_var,
            "min_spawn_delay": self.min_spawn_delay_var, "max_spawn_delay": self.max_spawn_delay_var,
            "scale_media": self.scale_media_var, "max_media_width_percent": self.max_media_width_percent_var,
            "max_media_height_percent": self.max_media_height_percent_var, "max_media_on_screen": self.max_media_on_screen_var,
            "min_snippet_duration": self.min_snippet_duration_var, "max_snippet_duration": self.max_snippet_duration_var,
            "smart_snippet_enabled": self.smart_snippet_enabled_var, "smart_snippet_threshold": self.smart_snippet_threshold_var,
        }
        for var in self.setting_vars_map.values():
            var.trace_add("write", self._on_setting_changed)
        self.visualization_mode_var.trace_add("write", self._toggle_ui_elements_by_mode)

    def _on_setting_changed(self, *args):
        # More complex logic now, might need to adapt later
        self._save_configuration()

    def _define_presets(self):
        self.presets = {
            "Default Mixed Media": { "min_fade_time": 1.0, "max_fade_time": 2.0, "min_visible_time": 2.0, "max_visible_time": 4.0, "min_spawn_delay": 0.8, "max_spawn_delay": 1.5, "max_media_on_screen": 8, "min_snippet_duration": 4.0, "max_snippet_duration": 8.0, "color_speed": 0.3},
            "Image Showcase (Slow)": { "min_fade_time": 2.5, "max_fade_time": 4.0, "min_visible_time": 5.0, "max_visible_time": 8.0, "min_spawn_delay": 3.0, "max_spawn_delay": 5.0, "max_media_on_screen": 4, "color_speed": 0.1},
            "Video Wall (Fast)": { "min_fade_time": 0.5, "max_fade_time": 1.0, "min_visible_time": 5.0, "max_visible_time": 10.0, "min_spawn_delay": 0.2, "max_spawn_delay": 0.5, "max_media_on_screen": 12, "min_snippet_duration": 5.0, "max_snippet_duration": 10.0, "color_speed": 0.6},
            "Cinematic Showcase": { "mode": "Video Background with Images", "min_fade_time": 3.0, "max_fade_time": 5.0, "min_visible_time": 6.0, "max_visible_time": 10.0, "min_spawn_delay": 4.0, "max_spawn_delay": 7.0, "max_media_on_screen": 3 },
            "Media Frenzy": { "mode": "Mixed Media Pop-ups", "min_fade_time": 0.2, "max_fade_time": 0.5, "min_visible_time": 1.0, "max_visible_time": 3.0, "min_spawn_delay": 0.1, "max_spawn_delay": 0.3, "max_media_on_screen": 15, "min_snippet_duration": 2.0, "max_snippet_duration": 4.0, "color_speed": 1.0},
        }
        self.current_preset_var = tk.StringVar(value="Default Mixed Media")

    def _apply_preset(self, event=None):
        preset_settings = self.presets.get(self.current_preset_var.get())
        if not preset_settings: return
        self._pause_trace = True
        # Set default values for any missing keys in the preset
        full_defaults = {k: v.get() for k,v in self.setting_vars_map.items()}
        settings_to_apply = {**full_defaults, **preset_settings}

        for key, value in settings_to_apply.items():
            if key in self.setting_vars_map:
                self.setting_vars_map[key].set(value)
        self._pause_trace = False
        self._save_configuration()

    def _build_ui(self):
        self.master.configure(background=self.bg_color)
        main_frame = ttk.Frame(self.master, style='TFrame', padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True)
        main_frame.columnconfigure(0, weight=3); main_frame.columnconfigure(1, weight=2)
        main_frame.rowconfigure(1, weight=1)

        title = ttk.Label(main_frame, text="Unified Visualization Tool", font=self.title_font, foreground=self.accent_color_1, background=self.bg_color)
        title.grid(row=0, column=0, columnspan=2, pady=(0, 20), sticky="ew")

        # --- Left Panel: Media Sources ---
        media_panel = ttk.LabelFrame(main_frame, text="Media Sources", style='TLabelframe')
        media_panel.grid(row=1, column=0, sticky="nsew", padx=(0, 10))
        media_panel.rowconfigure(1, weight=1); media_panel.columnconfigure(0, weight=1)

        btn_frame = ttk.Frame(media_panel, style='TFrame')
        btn_frame.grid(row=0, column=0, sticky="ew", pady=5, padx=5)
        ttk.Button(btn_frame, text="Add Image Directory", command=self._add_image_dir).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Add Video File(s)", command=self._add_video_files).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Remove Selected", command=self._remove_selected_media).pack(side=tk.RIGHT, padx=2)
        ttk.Button(btn_frame, text="Clear All", command=self._clear_all_media).pack(side=tk.RIGHT, padx=2)

        self.tree = ttk.Treeview(media_panel, columns=('type', 'path'), show='headings', selectmode="extended")
        self.tree.heading('#0', text='Enabled'); self.tree.column('#0', width=60, anchor='center', stretch=False)
        self.tree.heading('type', text='Type', command=lambda: self._sort_media('type'))
        self.tree.column('type', width=100, anchor='w', stretch=False)
        self.tree.heading('path', text='Source Path', command=lambda: self._sort_media('path'))
        self.tree.column('path', stretch=True)
        self.tree['displaycolumns'] = ('type', 'path') # #0 is special
        
        # Checkbox logic
        self.tree.tag_configure('checked', image=self.get_checkbox_image(True))
        self.tree.tag_configure('unchecked', image=self.get_checkbox_image(False))
        self.tree.bind('<Button-1>', self._on_tree_click)

        vsb = ttk.Scrollbar(media_panel, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.grid(row=1, column=0, sticky='nsew', padx=5, pady=5)
        vsb.grid(row=1, column=1, sticky='ns')

        # --- Right Panel: Settings ---
        self.settings_panel = ttk.LabelFrame(main_frame, text="Settings", style='TLabelframe', padding=10)
        self.settings_panel.grid(row=1, column=1, sticky="nsew", padx=(10,0))
        self.settings_panel.columnconfigure(1, weight=1)
        
        row = 0
        # Mode
        mode_frame = ttk.LabelFrame(self.settings_panel, text="Visualization Mode", padding=5)
        mode_frame.grid(row=row, column=0, columnspan=3, sticky='ew', pady=5); row+=1
        modes = [("Images Only", "Images Only"), ("Video Snippets as Pop-ups", "Video Snippets as Pop-ups"),
                 ("Video Background with Images", "Video Background with Images"), ("Mixed Media Pop-ups", "Mixed Media Pop-ups")]
        for text, val in modes:
            ttk.Radiobutton(mode_frame, text=text, variable=self.visualization_mode_var, value=val).pack(anchor='w')

        # Presets
        ttk.Label(self.settings_panel, text="Preset:").grid(row=row, column=0, sticky="w", pady=5)
        preset_combo = ttk.Combobox(self.settings_panel, textvariable=self.current_preset_var, values=list(self.presets.keys()), state="readonly")
        preset_combo.grid(row=row, column=1, columnspan=2, sticky="ew", padx=5)
        preset_combo.bind("<<ComboboxSelected>>", self._apply_preset)
        row += 1

        def add_slider(label, var, from_, to, parent, precision=1):
            nonlocal row
            r = parent.grid_size()[1]
            ttk.Label(parent, text=label).grid(row=r, column=0, sticky="w", pady=4)
            ttk.Scale(parent, variable=var, from_=from_, to=to).grid(row=r, column=1, sticky="ew", padx=5)
            fmt = f"%.{precision}f"
            ttk.Spinbox(parent, textvariable=var, from_=from_, to=to, increment=0.1 if precision > 0 else 1, width=6, format=fmt).grid(row=r, column=2)

        # Pop-up settings
        self.popup_settings_frame = ttk.LabelFrame(self.settings_panel, text="Pop-up Media Settings", padding=5)
        self.popup_settings_frame.grid(row=row, column=0, columnspan=3, sticky='ew', pady=5); row+=1
        self.popup_settings_frame.columnconfigure(1, weight=1)
        add_slider("Min Fade (s):", self.min_fade_time_var, 0.1, 10.0, self.popup_settings_frame)
        add_slider("Max Fade (s):", self.max_fade_time_var, 0.1, 10.0, self.popup_settings_frame)
        add_slider("Min Visible (s):", self.min_visible_time_var, 0.1, 20.0, self.popup_settings_frame)
        add_slider("Max Visible (s):", self.max_visible_time_var, 0.1, 20.0, self.popup_settings_frame)
        add_slider("Min Spawn (s):", self.min_spawn_delay_var, 0.1, 10.0, self.popup_settings_frame, precision=2)
        add_slider("Max Spawn (s):", self.max_spawn_delay_var, 0.1, 10.0, self.popup_settings_frame, precision=2)
        add_slider("Max Media:", self.max_media_on_screen_var, 1, 50, self.popup_settings_frame, precision=0)
        
        # Video settings
        self.video_settings_frame = ttk.LabelFrame(self.settings_panel, text="Video Snippet Settings", padding=5)
        self.video_settings_frame.grid(row=row, column=0, columnspan=3, sticky='ew', pady=5); row+=1
        self.video_settings_frame.columnconfigure(1, weight=1)
        add_slider("Min Snippet (s):", self.min_snippet_duration_var, 1.0, 60.0, self.video_settings_frame, precision=0)
        add_slider("Max Snippet (s):", self.max_snippet_duration_var, 1.0, 120.0, self.video_settings_frame, precision=0)
        check = ttk.Checkbutton(self.video_settings_frame, text="Play short videos fully (under...)", variable=self.smart_snippet_enabled_var)
        check.grid(row=self.video_settings_frame.grid_size()[1], column=0, columnspan=2, sticky="w")
        ttk.Spinbox(self.video_settings_frame, textvariable=self.smart_snippet_threshold_var, from_=5, to=300, increment=5, width=6).grid(row=self.video_settings_frame.grid_size()[1]-1, column=2)

        # General settings (BG, etc.)
        self.general_settings_frame = ttk.LabelFrame(self.settings_panel, text="General Settings", padding=5)
        self.general_settings_frame.grid(row=row, column=0, columnspan=3, sticky='ew', pady=5); row+=1
        self.general_settings_frame.columnconfigure(1, weight=1)
        add_slider("BG Color Speed:", self.color_speed_var, 0.1, 2.0, self.general_settings_frame, precision=2)
        add_slider("Target FPS:", self.fps_var, 10, 60, self.general_settings_frame, precision=0)
        
        # Bottom Buttons
        bottom_frame = ttk.Frame(main_frame, style='TFrame')
        bottom_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(15, 0))
        bottom_frame.columnconfigure(0, weight=1)
        ttk.Button(bottom_frame, text="Run Visualization", command=self._on_run, style="Accent.TButton").pack(fill=tk.X)

    def _toggle_ui_elements_by_mode(self, *args):
        mode = self.visualization_mode_var.get()
        def set_state(widget, state):
            try:
                widget.config(state=state)
                for child in widget.winfo_children():
                    set_state(child, state)
            except: pass

        popup_state = tk.NORMAL if "Pop-ups" in mode else tk.DISABLED
        video_state = tk.NORMAL if "Video" in mode else tk.DISABLED
        general_state = tk.NORMAL if "Background" not in mode else tk.DISABLED

        set_state(self.popup_settings_frame, popup_state)
        set_state(self.video_settings_frame, video_state)
        set_state(self.general_settings_frame.winfo_children()[0], general_state) # Label
        set_state(self.general_settings_frame.winfo_children()[1], general_state) # Scale
        set_state(self.general_settings_frame.winfo_children()[2], general_state) # Spinbox

    # --- Checkbox Treeview Logic ---
    def get_checkbox_image(self, checked):
        # Creates a 16x16 checkbox image using Tkinter photoimage
        if not hasattr(self, '_checkbox_images'): self._checkbox_images = {}
        if checked in self._checkbox_images: return self._checkbox_images[checked]

        im = tk.PhotoImage(width=16, height=16)
        bg = self.entry_bg
        fg = self.accent_color_1
        im.put(f"{{{bg} {bg} {bg} {bg}}}", to=(2, 2, 14, 14)) # Box
        im.put(f"{{{self.fg_color} {self.fg_color} {self.fg_color} {self.fg_color}}}", to=(3, 3, 13, 13))
        im.put(f"{{{bg} {bg} {bg} {bg}}}", to=(4, 4, 12, 12))
        if checked:
            im.put(f"{{{fg} {fg} {fg} {fg} {fg} {fg}}}", to=(5, 7, 11, 8))
            im.put(f"{{{fg} {fg}}}", to=(7, 9, 8, 10))
        self._checkbox_images[checked] = im
        return im

    def _on_tree_click(self, event):
        region = self.tree.identify("region", event.x, event.y)
        if region != "heading": return
        
        col = self.tree.identify_column(event.x)
        if col == '#0': # Checkbox column
            # Toggle all
            all_enabled = all(item['enabled_var'].get() for item in self.media_sources_data)
            for item in self.media_sources_data:
                item['enabled_var'].set(not all_enabled)
            self._populate_media_list_ui()
            return
            
        iid = self.tree.identify_row(event.y)
        if not iid: return
        
        # Find item in data list by path
        clicked_item = next((item for item in self.media_sources_data if item['path'] == iid), None)
        if clicked_item:
            current_state = clicked_item['enabled_var'].get()
            clicked_item['enabled_var'].set(not current_state)
            self._update_tree_item_checkbox(iid)

    def _update_tree_item_checkbox(self, iid):
        item = next((item for item in self.media_sources_data if item['path'] == iid), None)
        if item:
            tag = 'checked' if item['enabled_var'].get() else 'unchecked'
            self.tree.item(iid, tags=(tag,))

    # --- UI Logic ---
    def _add_image_dir(self):
        path = filedialog.askdirectory(title="Select Image Directory")
        if not path: return
        self._add_media_source(os.path.normpath(path), "Images")
    
    def _add_video_files(self):
        paths = filedialog.askopenfilenames(filetypes=(("Video Files", "*.mp4 *.mov *.avi *.mkv"), ("All", "*.*")))
        if not paths: return
        for path in paths:
            self._add_media_source(os.path.normpath(path), "Video")

    def _add_media_source(self, path, type):
        if not any(item['path'] == path for item in self.media_sources_data):
            enabled_var = tk.BooleanVar(value=True)
            enabled_var.trace_add('write', self._save_configuration)
            self.media_sources_data.append({'path': path, 'type': type, 'enabled_var': enabled_var})
        self._populate_media_list_ui()
        self._save_configuration()

    def _remove_selected_media(self):
        selected_iids = self.tree.selection()
        if not selected_iids: return
        self.media_sources_data = [item for item in self.media_sources_data if item['path'] not in selected_iids]
        self._populate_media_list_ui()
        self._save_configuration()

    def _clear_all_media(self):
        if messagebox.askyesno("Confirm Clear", "Remove all media sources from the list?"):
            self.media_sources_data = []
            self._populate_media_list_ui()
            self._save_configuration()
    
    def _sort_media(self, key):
        self.media_sources_data.sort(key=lambda x: x[key])
        self._populate_media_list_ui()

    def _populate_media_list_ui(self):
        self.tree.delete(*self.tree.get_children())
        for item in self.media_sources_data:
            tag = 'checked' if item['enabled_var'].get() else 'unchecked'
            display_name = os.path.basename(item['path'])
            self.tree.insert('', 'end', iid=item['path'], values=(item['type'], display_name), tags=(tag,))

    def _get_config_path(self):
        return os.path.join(os.path.expanduser("~"), CONFIG_FILE_NAME)

    def _save_configuration(self, *args):
        if hasattr(self, '_pause_trace') and self._pause_trace: return
        settings = {k: v.get() for k, v in self.setting_vars_map.items()}
        media_to_save = [{'path': item['path'], 'type': item['type'], 'enabled': item['enabled_var'].get()} for item in self.media_sources_data]
        try:
            with open(self._get_config_path(), 'w') as f:
                json.dump({"settings": settings, "media_sources": media_to_save}, f, indent=4)
        except Exception as e:
            print(f"Error saving config: {e}")

    def _load_configuration(self):
        path = self._get_config_path()
        if not os.path.exists(path): return
        try:
            with open(path, 'r') as f: data = json.load(f)
            
            self._pause_trace = True
            settings = data.get("settings", {})
            for k, v in settings.items():
                if k in self.setting_vars_map: self.setting_vars_map[k].set(v)
            
            self.media_sources_data = []
            for item in data.get("media_sources", []):
                filepath, filetype, enabled = item.get('path'), item.get('type'), item.get('enabled', True)
                if filepath and os.path.exists(filepath):
                    enabled_var = tk.BooleanVar(value=enabled)
                    enabled_var.trace_add('write', self._save_configuration)
                    self.media_sources_data.append({'path': filepath, 'type': filetype, 'enabled_var': enabled_var})
            
            self._pause_trace = False
            self._populate_media_list_ui()
            self._toggle_ui_elements_by_mode()
        except Exception as e:
            print(f"Error loading config: {e}")
            
    def _on_run(self):
        if not MOVIEPY_AVAILABLE:
            messagebox.showerror("Dependency Error", "MoviePy is not installed. Video features are disabled.")
            return

        enabled_sources = [{'path': item['path'], 'type': item['type']} for item in self.media_sources_data if item['enabled_var'].get()]
        if not enabled_sources:
            messagebox.showwarning("No Media", "Please add and enable at least one media source.")
            return
            
        params = {
            "screen_w": self.screen_w, "screen_h": self.screen_h,
            "media_sources": enabled_sources,
            **{k: v.get() for k, v in self.setting_vars_map.items()}
        }
        
        self.is_zoomed = self.master.state() == 'zoomed'
        self.master.withdraw()
        run_pygame_visualization(params)
        self.master.deiconify()
        if self.is_zoomed:
             try: self.master.state('zoomed')
             except tk.TclError: pass # For non-Windows/X11
        self.master.lift()
        self.master.focus_force()

    def _on_quit(self):
        self._save_configuration()
        self.master.destroy()

# --- Main Application Entry ---
if __name__ == '__main__':
    if not MOVIEPY_AVAILABLE:
        root = tk.Tk(); root.withdraw()
        messagebox.showerror("Dependency Missing", "MoviePy is required for video features. Please run: pip install moviepy")
        
    temp_root = tk.Tk()
    screen_w = temp_root.winfo_screenwidth()
    screen_h = temp_root.winfo_screenheight()
    temp_root.destroy()

    root = tk.Tk()
    app = VisualizationToolGUI(root, screen_w, screen_h)
    root.mainloop()