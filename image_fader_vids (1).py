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
import atexit

# --- Dependency Check ---
try:
    from moviepy.editor import VideoFileClip
    MOVIEPY_AVAILABLE = True
except ImportError:
    MOVIEPY_AVAILABLE = False

# --- Configuration ---
CONFIG_FILE_NAME = "unified_visualizer_config_v2.json"
TEMP_AUDIO_DIR = os.path.join(tempfile.gettempdir(), "unified_visualizer_audio_v2")
os.makedirs(TEMP_AUDIO_DIR, exist_ok=True)

# --- Cleanup for Temp Files ---
def cleanup_temp_files():
    print("Cleaning up temporary audio files...")
    try:
        if os.path.exists(TEMP_AUDIO_DIR):
            for f in os.listdir(TEMP_AUDIO_DIR):
                os.remove(os.path.join(TEMP_AUDIO_DIR, f))
            os.rmdir(TEMP_AUDIO_DIR)
    except Exception as e:
        print(f"Error during cleanup: {e}")
atexit.register(cleanup_temp_files)

# --- Helper Functions ---
def get_random_color(): return (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))

def interpolate_color(c1, c2, f):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * f) for i in range(3))

def scale_surface(surface, screen_w, screen_h, scale_params):
    surf_w, surf_h = surface.get_size()
    if surf_w == 0 or surf_h == 0: return surface
    if scale_params['scale_enabled']:
        max_w = screen_w * scale_params['max_w_percent']
        max_h = screen_h * scale_params['max_h_percent']
        if surf_w > max_w or surf_h > max_h:
            scale = min(max_w / surf_w, max_h / surf_h)
            new_w, new_h = max(1, int(surf_w * scale)), max(1, int(surf_h * scale))
            try:
                surface = pygame.transform.smoothscale(surface, (new_w, new_h))
            except (pygame.error, ValueError) as e:
                print(f"Warning: could not scale surface: {e}")
    return surface

# --- Pygame Media Classes ---
class FadingMedia:
    def __init__(self, p):
        self.state = "fading_in"; self.alpha = 0; self.timer = 0.0
        self.fade_in_duration = random.uniform(p['min_fade_time'], p['max_fade_time'])
        self.visible_duration = random.uniform(p['min_visible_time'], p['max_visible_time'])
        self.fade_out_duration = random.uniform(p['min_fade_time'], p['max_fade_time'])
        self.surface = None

    def update_fade(self, dt):
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
            if self.timer >= self.fade_out_duration: return False
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
            self.original_surface = scale_surface(loaded_surface, screen_w, screen_h, p['image_settings'])
            self.surface = self.original_surface.copy()
            self.rect = self.surface.get_rect()
            self.rect.x = random.randint(0, max(0, screen_w - self.rect.width))
            self.rect.y = random.randint(0, max(0, screen_h - self.rect.height))
        except Exception as e:
            print(f"ERROR loading image {image_path}: {e}"); self.surface = None

    def update(self, dt): return self.update_fade(dt)

class FadingVideoSnippet(FadingMedia):
    def __init__(self, prep_result, screen_w, screen_h, p):
        super().__init__(p)
        self.moviepy_clip, self.audio_sound = prep_result
        self.p = p
        self.is_valid = self.moviepy_clip is not None
        if not self.is_valid: return

        self.frames = []
        self.ping_pong = self.p['video_settings']['ping_pong']
        self.is_looping = self.p['video_settings']['snippet_mode'] == "Loop Short Videos"
        self.direction = 1
        self.frame_idx = 0
        
        try:
            if (self.ping_pong or self.is_looping) and self.moviepy_clip.duration > 15:
                print(f"WARNING: Ping-Pong/Looping on a video longer than 15s ({self.moviepy_clip.duration:.1f}s) may use significant RAM.")
            
            frame_iterator = self.moviepy_clip.iter_frames(fps=p['fps'], dtype='uint8')
            for frame_np in frame_iterator:
                self.frames.append(pygame.surfarray.make_surface(np.transpose(frame_np, (1, 0, 2))))
            if not self.frames: raise ValueError("Video has no frames.")
            
            scaled_frame = scale_surface(self.frames[0], screen_w, screen_h, p['video_settings'])

            # --- CRITICAL FIX HERE ---
            # OLD: self.surface = pygame.Surface(scaled_frame.get_size(), pygame.SRCALPHA) # This creates an invisible surface
            # NEW: Create an opaque surface. The .convert() is for performance.
            self.surface = pygame.Surface(scaled_frame.get_size()).convert()
            # --- END OF FIX ---

            self.rect = self.surface.get_rect()
            self.rect.x = random.randint(0, max(0, screen_w - self.rect.width))
            self.rect.y = random.randint(0, max(0, screen_h - self.rect.height))
        except Exception as e:
            print(f"ERROR initializing video snippet: {e}"); self.cleanup(); return

        if self.audio_sound: self.audio_sound.set_volume(0.7)

    def update(self, dt):
        if not self.is_valid: return False
        
        is_alive = self.update_fade(dt)
        if not is_alive: self.cleanup(); return False

        if self.state == "visible" and self.audio_sound and not self.audio_sound.get_num_channels():
            self.audio_sound.play(-1 if self.is_looping else 0)

        if self.state == "fading_out" and self.audio_sound:
            vol = max(0, 1.0 - (self.timer / self.fade_out_duration)) if self.fade_out_duration > 0 else 0
            self.audio_sound.set_volume(vol * 0.7)

        if self.state in ["visible", "fading_out", "fading_in"]:
            num_frames = len(self.frames)
            # Use the correct scaled surface as the destination for the transform
            current_frame_surf = self.frames[int(self.frame_idx)]
            pygame.transform.scale(current_frame_surf, self.rect.size, self.surface)
            
            if self.state != "fading_in":
                frame_increment = dt * self.p['fps'] * self.direction
                self.frame_idx += frame_increment
                
                if self.frame_idx >= num_frames:
                    if self.ping_pong: self.direction = -1; self.frame_idx = num_frames - 1
                    elif self.is_looping: self.frame_idx = 0
                    else: self.visible_duration = self.timer; return self.update_fade(0)
                elif self.frame_idx < 0:
                    if self.ping_pong: self.direction = 1; self.frame_idx = 0
                    else: self.frame_idx = 0
        return True

    def cleanup(self):
        if self.audio_sound: self.audio_sound.stop()
        if self.moviepy_clip: self.moviepy_clip.close()
        self.is_valid = False

# --- Video Snippet Preparation Worker ---
def prepare_video_snippet_worker(request_q, ready_q, stop_event, p):
    if not MOVIEPY_AVAILABLE: return
    while not stop_event.is_set():
        try:
            video_path = request_q.get(timeout=1)
            vs = p['video_settings']
            with VideoFileClip(video_path) as clip: duration = clip.duration

            snippet_mode = vs['snippet_mode']
            start_time, end_time = 0, duration
            if snippet_mode == "Random Snippet":
                min_dur, max_dur = vs['min_snippet_duration'], vs['max_snippet_duration']
                snippet_duration = random.uniform(min_dur, min(max_dur, duration))
                start_time = random.uniform(0, duration - snippet_duration) if duration > snippet_duration else 0
                end_time = start_time + snippet_duration
            elif snippet_mode == "Loop Short Videos" and duration > vs['loop_threshold']:
                min_dur, max_dur = vs['min_snippet_duration'], vs['max_snippet_duration']
                snippet_duration = random.uniform(min_dur, min(max_dur, duration))
                start_time = random.uniform(0, duration - snippet_duration) if duration > snippet_duration else 0
                end_time = start_time + snippet_duration

            moviepy_clip = VideoFileClip(video_path, audio=True).subclip(start_time, end_time)
            
            audio_sound = None
            if moviepy_clip.audio:
                try:
                    temp_audio_path = os.path.join(TEMP_AUDIO_DIR, f"snippet_{time.time_ns()}.wav")
                    moviepy_clip.audio.write_audiofile(temp_audio_path, codec='pcm_s16le', logger=None)
                    audio_sound = pygame.mixer.Sound(temp_audio_path)
                except Exception as e: print(f"[WORKER] ERROR creating audio: {e}")
            
            ready_q.put((moviepy_clip, audio_sound))
        except queue.Empty: continue
        except Exception as e:
            print(f"[WORKER] FATAL ERROR preparing snippet for {os.path.basename(video_path)}: {e}")
            ready_q.put((None, None))

# --- Main Pygame Visualization Function ---
def run_pygame_visualization(p):
    try:
        pygame.mixer.pre_init(44100, -16, 2, 4096)
        pygame.init()
        pygame.mixer.init()
        pygame.mixer.set_num_channels(64)
        print("PYGAME: Audio mixer initialized successfully.")
    except pygame.error as e:
        print(f"PYGAME FATAL: Could not initialize audio mixer: {e}. All audio features disabled.")
        p['mode'] = "Images Only"

    screen = pygame.display.set_mode((p['screen_w'], p['screen_h']), pygame.FULLSCREEN | pygame.HWSURFACE | pygame.DOUBLEBUF)
    pygame.mouse.set_visible(False)
    clock = pygame.time.Clock()

    video_request_queue, prepared_video_queue = queue.Queue(maxsize=5), queue.Queue(maxsize=2)
    stop_worker_event = threading.Event()
    worker_thread = threading.Thread(target=prepare_video_snippet_worker, args=(video_request_queue, prepared_video_queue, stop_worker_event, p))
    worker_thread.daemon = True
    if any(s['type'] == 'Video' for s in p['media_sources']): worker_thread.start()

    image_paths = [s['path'] for s in p['media_sources'] if s['type'] == 'Images']
    video_paths = [s['path'] for s in p['media_sources'] if s['type'] == 'Video']
    
    image_idx, video_idx = 0, 0
    if p['playback_order'] == 'Random':
        random.shuffle(image_paths)
        random.shuffle(video_paths)
    
    if video_paths:
        for _ in range(min(5, len(video_paths))):
            path_to_add = video_paths[video_idx % len(video_paths)] if p['playback_order'].startswith('In Order') else random.choice(video_paths)
            video_request_queue.put(path_to_add)
            if p['playback_order'].startswith('In Order'): video_idx += 1
    
    active_media = []; next_spawn_time = time.time()
    ctc, ttc = get_random_color(), get_random_color()
    cbc, tbc = get_random_color(), get_random_color()
    clf = 0.0

    bg_video_clip, bg_video_iterator = None, None
    if p['mode'] == 'Video Background with Images' and video_paths:
        try:
            bg_vid_path = random.choice(video_paths)
            bg_video_clip = VideoFileClip(bg_vid_path)
            bg_video_iterator = bg_video_clip.iter_frames(fps=p['fps'], dtype='uint8')
        except Exception as e: print(f"PYGAME ERROR: Could not load background video: {e}"); p['mode'] = 'Images Only'
    
    running = True
    while running:
        dt = clock.tick(p['fps']) / 1000.0
        for event in pygame.event.get():
            if event.type in (pygame.QUIT, pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN): running = False
        
        if p['mode'] == 'Video Background with Images' and bg_video_iterator:
            try:
                frame_np = next(bg_video_iterator)
                frame_surf = pygame.surfarray.make_surface(np.transpose(frame_np, (1, 0, 2)))
                scaled_surf = pygame.transform.scale(frame_surf, (p['screen_w'], p['screen_h']))
                screen.blit(scaled_surf, (0, 0))
            except StopIteration: bg_video_iterator = bg_video_clip.iter_frames(fps=p['fps'], dtype='uint8')
        else:
            clf += p['color_speed'] * dt
            if clf >= 1.0:
                clf %= 1.0
                ctc, ttc = ttc, get_random_color()
                cbc, tbc = tbc, get_random_color()
            display_top_color = interpolate_color(ctc, ttc, clf)
            display_bottom_color = interpolate_color(cbc, tbc, clf)
            for y in range(p['screen_h']):
                row_color = interpolate_color(display_top_color, display_bottom_color, y / p['screen_h'])
                pygame.draw.line(screen, row_color, (0, y), (p['screen_w'], y))

        if len(active_media) < p['max_media_on_screen'] and time.time() >= next_spawn_time:
            media_type, path = None, None
            mode, playback = p['mode'], p['playback_order']
            
            if mode in ['Images Only', 'Video Background with Images']:
                if image_paths: media_type = 'Image'
            elif mode == 'Video Snippets as Pop-ups':
                if video_paths: media_type = 'Video'
            elif mode == 'Mixed Media Pop-ups':
                choices = [t for t, l in [('Image', image_paths), ('Video', video_paths)] if l]
                if choices: media_type = random.choice(choices)

            new_media = None
            if media_type == 'Image':
                if image_idx < len(image_paths):
                    path = image_paths[image_idx] if playback.startswith('In Order') else random.choice(image_paths)
                    new_media = FadingImage(path, p['screen_w'], p['screen_h'], p)
                    if playback.startswith('In Order'):
                        image_idx += 1
                        if image_idx >= len(image_paths) and playback.endswith('(Loop Playlist)'): image_idx = 0
                
            elif media_type == 'Video':
                try:
                    prep_result = prepared_video_queue.get_nowait()
                    if prep_result[0]: new_media = FadingVideoSnippet(prep_result, p['screen_w'], p['screen_h'], p)
                    if video_paths and not video_request_queue.full():
                        if playback.startswith('In Order'):
                            if video_idx < len(video_paths):
                                video_request_queue.put(video_paths[video_idx])
                                video_idx += 1
                                if video_idx >= len(video_paths) and playback.endswith('(Loop Playlist)'): video_idx = 0
                        else: video_request_queue.put(random.choice(video_paths))
                except queue.Empty: pass
            
            if new_media and getattr(new_media, 'surface', None):
                active_media.append(new_media)
                next_spawn_time = time.time() + random.uniform(p['min_spawn_delay'], p['max_spawn_delay'])

        active_media[:] = [m for m in active_media if m.update(dt)]
        for m in active_media: m.draw(screen)
        pygame.display.flip()

    print("PYGAME: Cleaning up...")
    for m in active_media:
        if hasattr(m, 'cleanup'): m.cleanup()
    if bg_video_clip: bg_video_clip.close()
    stop_worker_event.set()
    if worker_thread.is_alive():
        while not video_request_queue.empty():
            try: video_request_queue.get_nowait()
            except queue.Empty: break
        worker_thread.join(timeout=2)
    pygame.quit()

# --- Tkinter GUI Class ---
class VisualizationToolGUI_V2:
    def __init__(self, master, screen_w, screen_h):
        self.master = master
        self.screen_w, self.screen_h = screen_w, screen_h
        self.master.title("Unified Visualization Tool v2.2 (FINAL FIX)")
        self.master.geometry(f"{int(screen_w*0.85)}x{int(screen_h*0.8)}")
        self.master.minsize(1200, 800)
        
        self.media_sources_data = []
        self._init_style(); self._init_vars(); self._define_presets(); self._build_ui()
        self._load_configuration()
        self.master.protocol("WM_DELETE_WINDOW", self._on_quit)

    def _init_style(self):
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.bg = "#2E3440"; self.fg = "#E5E9F0"; self.frame_bg = "#3B4252"
        self.accent1 = "#88C0D0"; self.accent2 = "#BF616A"; self.btn = "#5E81AC"; self.entry_bg = "#4C566A"
        self.style.configure('.', background=self.bg, foreground=self.fg, font=('Segoe UI', 10))
        self.style.configure('TFrame', background=self.frame_bg); self.style.configure('TLabel', background=self.frame_bg, foreground=self.fg)
        self.style.configure('TRadiobutton', background=self.frame_bg, foreground=self.fg); self.style.map('TRadiobutton', indicatorcolor=[('selected', self.accent1)])
        self.style.configure('TLabelframe', background=self.frame_bg, bordercolor=self.accent1)
        self.style.configure('TLabelframe.Label', background=self.frame_bg, foreground=self.accent1, font=('Segoe UI Semibold', 12))
        self.style.configure('TButton', background=self.btn, foreground='white', padding=6); self.style.map('TButton', background=[('active', self.accent1)])
        self.style.configure('Accent.TButton', background=self.accent2, foreground='white', font=('Segoe UI Bold', 12), padding=8); self.style.map('Accent.TButton', background=[('active', '#D08770')])
        self.style.configure('Treeview', background=self.entry_bg, fieldbackground=self.entry_bg, foreground=self.fg, rowheight=25)
        self.style.map('Treeview', background=[('selected', self.btn)])
        self.style.configure('Treeview.Heading', background=self.entry_bg, foreground=self.accent1, font=('Segoe UI Semibold', 10)); self.style.map('Treeview.Heading', background=[('active', self.btn)])
        self.title_font = tkFont.Font(family="Impact", size=28, weight="bold")

    def _init_vars(self):
        self.mode_var = tk.StringVar(value="Mixed Media Pop-ups")
        self.playback_order_var = tk.StringVar(value="Random")
        self.min_fade_var = tk.DoubleVar(value=1.0); self.max_fade_var = tk.DoubleVar(value=2.0)
        self.min_visible_var = tk.DoubleVar(value=2.0); self.max_visible_var = tk.DoubleVar(value=4.0)
        self.min_spawn_var = tk.DoubleVar(value=0.8); self.max_spawn_var = tk.DoubleVar(value=1.5)
        self.max_media_var = tk.IntVar(value=10)
        self.scale_images_var = tk.BooleanVar(value=True)
        self.max_img_w_p_var = tk.DoubleVar(value=0.75); self.max_img_h_p_var = tk.DoubleVar(value=0.75)
        self.scale_videos_var = tk.BooleanVar(value=True)
        self.max_vid_w_p_var = tk.DoubleVar(value=0.6); self.max_vid_h_p_var = tk.DoubleVar(value=0.6)
        self.snippet_mode_var = tk.StringVar(value="Random Snippet")
        self.min_snippet_dur_var = tk.DoubleVar(value=5.0); self.max_snippet_dur_var = tk.DoubleVar(value=10.0)
        self.loop_threshold_var = tk.DoubleVar(value=15.0); self.ping_pong_var = tk.BooleanVar(value=False)
        self.fps_var = tk.IntVar(value=30); self.color_speed_var = tk.DoubleVar(value=0.3)
        
        self.setting_vars_map = {
            "mode": self.mode_var, "playback_order": self.playback_order_var,
            "min_fade_time": self.min_fade_var, "max_fade_time": self.max_fade_var, "min_visible_time": self.min_visible_var, 
            "max_visible_time": self.max_visible_var, "min_spawn_delay": self.min_spawn_var, "max_spawn_delay": self.max_spawn_var,
            "max_media_on_screen": self.max_media_var, "image_settings.scale_enabled": self.scale_images_var, 
            "image_settings.max_w_percent": self.max_img_w_p_var, "image_settings.max_h_percent": self.max_img_h_p_var,
            "video_settings.scale_enabled": self.scale_videos_var, "video_settings.max_w_percent": self.max_vid_w_p_var, 
            "video_settings.max_h_percent": self.max_vid_h_p_var, "video_settings.snippet_mode": self.snippet_mode_var, 
            "video_settings.min_snippet_duration": self.min_snippet_dur_var, "video_settings.max_snippet_duration": self.max_snippet_dur_var, 
            "video_settings.loop_threshold": self.loop_threshold_var, "video_settings.ping_pong": self.ping_pong_var,
            "fps": self.fps_var, "color_speed": self.color_speed_var
        }
        for var in self.setting_vars_map.values(): var.trace_add("write", self._save_configuration)
        self.mode_var.trace_add("write", self._toggle_ui_elements_by_mode)
        self.snippet_mode_var.trace_add("write", self._toggle_ui_elements_by_mode)

    def _define_presets(self):
        self.presets = {
            "Default Mixed Media": {"min_fade_time": 1, "max_fade_time": 2, "min_visible_time": 2, "max_visible_time": 4, "min_spawn_delay": 0.8, "max_spawn_delay": 1.5, "max_media_on_screen": 10, "image_settings.max_w_percent": 0.75, "video_settings.max_w_percent": 0.6},
            "Image Showcase (Slow)": {"mode": "Images Only", "min_fade_time": 2.5, "max_fade_time": 4, "min_visible_time": 5, "max_visible_time": 8, "min_spawn_delay": 3, "max_spawn_delay": 5, "max_media_on_screen": 4, "color_speed": 0.1, "image_settings.max_w_percent": 0.9, "image_settings.max_h_percent": 0.9},
            "Ordered Slideshow": {"mode": "Images Only", "playback_order": "In Order (Loop Playlist)", "min_fade_time": 1.5, "max_fade_time": 1.5, "min_visible_time": 5, "max_visible_time": 5, "min_spawn_delay": 6.5, "max_spawn_delay": 6.5, "max_media_on_screen": 1},
            "Video Wall (Fast)": {"mode": "Video Snippets as Pop-ups", "min_fade_time": 0.5, "max_fade_time": 1, "min_visible_time": 5, "max_visible_time": 10, "min_spawn_delay": 0.2, "max_spawn_delay": 0.5, "max_media_on_screen": 12, "color_speed": 0.6},
            "Tiny Video Swarm": {"mode": "Video Snippets as Pop-ups", "max_media_on_screen": 20, "video_settings.max_w_percent": 0.2, "video_settings.max_h_percent": 0.2, "min_spawn_delay": 0.1, "max_spawn_delay": 0.3},
            "Gentle Looping Clips": {"mode": "Video Snippets as Pop-ups", "video_settings.snippet_mode": "Loop Short Videos", "min_fade_time": 3, "max_fade_time": 5, "max_media_on_screen": 5, "min_spawn_delay": 2, "max_spawn_delay": 4},
            "Ping-Pong Madness": {"mode": "Video Snippets as Pop-ups", "video_settings.snippet_mode": "Full Video", "video_settings.ping_pong": True, "max_media_on_screen": 8, "min_fade_time": 0.3, "max_fade_time": 0.3},
            "Cinematic Showcase": {"mode": "Video Background with Images", "min_fade_time": 3, "max_fade_time": 5, "min_visible_time": 6, "max_visible_time": 10, "min_spawn_delay": 4, "max_spawn_delay": 7, "max_media_on_screen": 3},
            "Dynamic Duo (Small Vids, Big Pics)": {"mode": "Mixed Media Pop-ups", "image_settings.max_w_percent": 0.8, "video_settings.max_w_percent": 0.3, "max_media_on_screen": 12},
        }
        self.current_preset_var = tk.StringVar(value="Default Mixed Media")

    def _apply_preset(self, event=None):
        settings_to_apply = self.presets.get(self.current_preset_var.get())
        if not settings_to_apply: return
        self._pause_trace = True
        # Reset to default before applying, to catch any unspecified keys
        default_settings = self.presets.get("Default Mixed Media", {})
        for key, var in self.setting_vars_map.items():
            if key in default_settings: var.set(default_settings[key])
        # Now apply the selected preset over the default
        for key, value in settings_to_apply.items():
            if key in self.setting_vars_map: self.setting_vars_map[key].set(value)
        self._pause_trace = False
        self._save_configuration()
    
    def _build_ui(self):
        self.master.configure(background=self.bg)
        main_frame = ttk.Frame(self.master, style='TFrame', padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True)
        main_frame.columnconfigure(0, weight=3); main_frame.columnconfigure(1, weight=2)
        main_frame.rowconfigure(1, weight=1)
        title = ttk.Label(main_frame, text="Unified Visualization Tool v2.2", font=self.title_font, foreground=self.accent1, background=self.bg)
        title.grid(row=0, column=0, columnspan=2, pady=(0, 20), sticky="ew")

        left_panel = ttk.Frame(main_frame, style='TFrame')
        left_panel.grid(row=1, column=0, sticky="nsew", padx=(0, 10))
        left_panel.rowconfigure(1, weight=1); left_panel.columnconfigure(0, weight=1)
        
        btn_frame = ttk.Frame(left_panel, style='TFrame')
        btn_frame.grid(row=0, column=0, sticky="ew", pady=5)
        ttk.Button(btn_frame, text="Add Images Dir", command=self._add_image_dir).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Add Video(s)", command=self._add_video_files).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Select All", command=lambda: self._toggle_all_media(True)).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Deselect All", command=lambda: self._toggle_all_media(False)).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Remove Sel.", command=self._remove_selected_media).pack(side=tk.RIGHT, padx=2)
        
        tree_frame = ttk.Frame(left_panel)
        tree_frame.grid(row=1, column=0, sticky='nsew')
        tree_frame.rowconfigure(0, weight=1); tree_frame.columnconfigure(0, weight=1)
        self.tree = ttk.Treeview(tree_frame, columns=('enabled', 'type', 'path'), show='headings', selectmode="extended")
        self.tree.heading('enabled', text='Enabled'); self.tree.column('enabled', width=60, anchor='center', stretch=False)
        self.tree.heading('type', text='Type'); self.tree.column('type', width=100, anchor='w', stretch=False)
        self.tree.heading('path', text='Source Path'); self.tree.column('path', stretch=True)
        self.tree.bind('<Button-1>', self._on_tree_click)
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview); self.tree.configure(yscrollcommand=vsb.set)
        self.tree.grid(row=0, column=0, sticky='nsew'); vsb.grid(row=0, column=1, sticky='ns')

        sort_frame = ttk.Frame(left_panel, style='TFrame')
        sort_frame.grid(row=2, column=0, sticky='ew', pady=(5,0))
        ttk.Button(sort_frame, text="Sort by Type", command=lambda: self._sort_media('type')).pack(side=tk.LEFT, padx=2)
        ttk.Button(sort_frame, text="Sort by Name", command=lambda: self._sort_media('path')).pack(side=tk.LEFT, padx=2)

        canvas = tk.Canvas(main_frame, borderwidth=0, background=self.frame_bg, highlightthickness=0)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview); canvas.configure(yscrollcommand=scrollbar.set)
        self.settings_panel = ttk.Frame(canvas, style='TFrame', padding=10)
        canvas.create_window((0, 0), window=self.settings_panel, anchor="nw")
        self.settings_panel.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.grid(row=1, column=1, sticky="nsew", padx=(10,0)); scrollbar.grid(row=1, column=2, sticky='ns')
        
        sp = self.settings_panel; sp.columnconfigure(0, weight=1); row = 0

        def add_slider(label, var, r, c, parent, from_, to, precision=1):
            lf = ttk.Frame(parent, style='TFrame'); lf.grid(row=r, column=c, columnspan=2, sticky='ew', pady=2)
            ttk.Label(lf, text=label).pack(side=tk.LEFT, padx=(0,5))
            ttk.Scale(lf, variable=var, from_=from_, to=to).pack(side=tk.LEFT, expand=True, fill=tk.X)
            fmt = f"%.{precision}f"; ttk.Spinbox(lf, textvariable=var, from_=from_, to=to, increment=0.1 if precision > 0 else 1, width=6, format=fmt).pack(side=tk.LEFT, padx=(5,0))
            return r+1

        core_f = ttk.LabelFrame(sp, text="Core Settings", padding=10); core_f.grid(row=row, column=0, sticky='ew'); row+=1
        ttk.Label(core_f, text="Preset:").grid(row=0, column=0, sticky='w')
        preset_combo = ttk.Combobox(core_f, textvariable=self.current_preset_var, values=list(self.presets.keys()), state="readonly")
        preset_combo.grid(row=0, column=1, sticky="ew", padx=5); preset_combo.bind("<<ComboboxSelected>>", self._apply_preset)
        ttk.Label(core_f, text="Mode:").grid(row=1, column=0, sticky='w')
        mode_combo = ttk.Combobox(core_f, textvariable=self.mode_var, values=["Images Only", "Video Snippets as Pop-ups", "Video Background with Images", "Mixed Media Pop-ups"], state="readonly")
        mode_combo.grid(row=1, column=1, sticky="ew", padx=5)
        ttk.Label(core_f, text="Playback Order:").grid(row=2, column=0, sticky='w')
        order_combo = ttk.Combobox(core_f, textvariable=self.playback_order_var, values=["Random", "In Order (Loop Playlist)", "In Order (Once)"], state="readonly")
        order_combo.grid(row=2, column=1, sticky="ew", padx=5)
        core_f.columnconfigure(1, weight=1)

        self.gen_popup_f = ttk.LabelFrame(sp, text="General Pop-up Settings", padding=10); self.gen_popup_f.grid(row=row, column=0, sticky='ew', pady=5); row+=1
        r=0; r=add_slider("Min Fade (s):", self.min_fade_var, r, 0, self.gen_popup_f, 0.1, 10)
        r=add_slider("Max Fade (s):", self.max_fade_var, r, 0, self.gen_popup_f, 0.1, 10)
        r=add_slider("Min Visible (s):", self.min_visible_var, r, 0, self.gen_popup_f, 0.1, 20)
        r=add_slider("Max Visible (s):", self.max_visible_var, r, 0, self.gen_popup_f, 0.1, 20)
        r=add_slider("Min Spawn (s):", self.min_spawn_var, r, 0, self.gen_popup_f, 0.1, 10, 2)
        r=add_slider("Max Spawn (s):", self.max_spawn_var, r, 0, self.gen_popup_f, 0.1, 10, 2)
        r=add_slider("Max On Screen:", self.max_media_var, r, 0, self.gen_popup_f, 1, 50, 0)
        
        self.img_popup_f = ttk.LabelFrame(sp, text="Image Pop-up Settings", padding=10); self.img_popup_f.grid(row=row, column=0, sticky='ew', pady=5); row+=1
        ttk.Checkbutton(self.img_popup_f, text="Scale Images", variable=self.scale_images_var).grid(row=0, column=0, sticky='w')
        r=1; r=add_slider("Max Width %:", self.max_img_w_p_var, r, 0, self.img_popup_f, 0.05, 1.0, 2)
        r=add_slider("Max Height %:", self.max_img_h_p_var, r, 0, self.img_popup_f, 0.05, 1.0, 2)

        self.vid_popup_f = ttk.LabelFrame(sp, text="Video Pop-up Settings", padding=10); self.vid_popup_f.grid(row=row, column=0, sticky='ew', pady=5); row+=1
        ttk.Checkbutton(self.vid_popup_f, text="Scale Videos", variable=self.scale_videos_var).grid(row=0, column=0, sticky='w')
        r=1; r=add_slider("Max Width %:", self.max_vid_w_p_var, r, 0, self.vid_popup_f, 0.05, 1.0, 2)
        r=add_slider("Max Height %:", self.max_vid_h_p_var, r, 0, self.vid_popup_f, 0.05, 1.0, 2)
        ttk.Label(self.vid_popup_f, text="Snippet Mode:").grid(row=r, column=0, sticky='w'); 
        self.snippet_mode_combo = ttk.Combobox(self.vid_popup_f, textvariable=self.snippet_mode_var, values=["Random Snippet", "Full Video", "Loop Short Videos"], state="readonly")
        self.snippet_mode_combo.grid(row=r, column=1, sticky='ew', padx=5); r+=1
        self.min_max_snippet_frame = ttk.Frame(self.vid_popup_f, style='TFrame'); self.min_max_snippet_frame.grid(row=r, column=0, columnspan=2, sticky='ew'); r+=1
        r_sub=0; r_sub=add_slider("Min Snippet (s):", self.min_snippet_dur_var, r_sub, 0, self.min_max_snippet_frame, 1, 60, 0)
        r_sub=add_slider("Max Snippet (s):", self.max_snippet_dur_var, r_sub, 0, self.min_max_snippet_frame, 1, 120, 0)
        self.loop_thresh_frame = ttk.Frame(self.vid_popup_f, style='TFrame'); self.loop_thresh_frame.grid(row=r, column=0, columnspan=2, sticky='ew'); r+=1
        r_sub=0; r_sub=add_slider("Loop Threshold (s):", self.loop_threshold_var, r_sub, 0, self.loop_thresh_frame, 1, 60, 0)
        ttk.Checkbutton(self.vid_popup_f, text="Ping-Pong Playback (Memory Intensive)", variable=self.ping_pong_var).grid(row=r, column=0, columnspan=2, sticky='w')
        
        self.bg_f = ttk.LabelFrame(sp, text="Background & Performance", padding=10); self.bg_f.grid(row=row, column=0, sticky='ew', pady=5); row+=1
        r=0; r=add_slider("BG Color Speed:", self.color_speed_var, r, 0, self.bg_f, 0.0, 2.0, 2)
        r=add_slider("Target FPS:", self.fps_var, r, 0, self.bg_f, 10, 120, 0)

        bottom_frame = ttk.Frame(self.master, style='TFrame', padding=(15,0,15,15))
        bottom_frame.pack(fill=tk.X, side=tk.BOTTOM)
        ttk.Button(bottom_frame, text="Run Visualization", command=self._on_run, style="Accent.TButton").pack(fill=tk.X)

    def _toggle_ui_elements_by_mode(self, *args):
        mode = self.mode_var.get(); s_mode = self.snippet_mode_var.get()
        def set_state(widget, state):
            try:
                for child in widget.winfo_children(): set_state(child, state)
                if 'state' in widget.configure(): widget.configure(state=state)
            except tk.TclError: pass
        set_state(self.gen_popup_f, 'normal' if 'Pop-ups' in mode else 'disabled')
        set_state(self.img_popup_f, 'normal' if 'Images' in mode else 'disabled')
        set_state(self.vid_popup_f, 'normal' if 'Video Snippets' in mode or 'Mixed' in mode else 'disabled')
        set_state(self.bg_f.winfo_children()[0], 'normal' if 'Background' not in mode else 'disabled')
        set_state(self.min_max_snippet_frame, 'normal' if s_mode == 'Random Snippet' and 'disabled' not in self.vid_popup_f.state() else 'disabled')
        set_state(self.loop_thresh_frame, 'normal' if s_mode == 'Loop Short Videos' and 'disabled' not in self.vid_popup_f.state() else 'disabled')

    def _on_tree_click(self, event):
        iid = self.tree.identify_row(event.y)
        if not iid: return
        item = next((i for i in self.media_sources_data if i['path'] == iid), None)
        if item:
            item['enabled_var'].set(not item['enabled_var'].get())
            self._populate_media_list_ui()

    def _populate_media_list_ui(self):
        selection = self.tree.selection()
        self.tree.delete(*self.tree.get_children())
        for item in self.media_sources_data:
            enabled_str = "Yes" if item['enabled_var'].get() else "No"
            self.tree.insert('', 'end', iid=item['path'], values=(enabled_str, item['type'], os.path.basename(item['path'])))
        if selection: self.tree.selection_set(selection)
    
    def _sort_media(self, key):
        if key == 'path': self.media_sources_data.sort(key=lambda x: os.path.basename(x[key]).lower())
        else: self.media_sources_data.sort(key=lambda x: (x[key], os.path.basename(x['path']).lower()))
        self._populate_media_list_ui()

    def _add_image_dir(self): self._add_media_source(filedialog.askdirectory(title="Select Image Directory"), "Images")
    def _add_video_files(self):
        paths = filedialog.askopenfilenames(filetypes=(("Video", "*.mp4 *.mov *.avi *.mkv"),("All","*.*")))
        if paths:
            for p in paths: self._add_media_source(p, "Video")

    def _add_media_source(self, path, type):
        if not path: return
        path = os.path.normpath(path)
        if not any(item['path'] == path for item in self.media_sources_data):
            enabled_var = tk.BooleanVar(value=True)
            enabled_var.trace_add('write', self._save_configuration)
            self.media_sources_data.append({'path': path, 'type': type, 'enabled_var': enabled_var})
        self._populate_media_list_ui(); self._save_configuration()
    
    def _remove_selected_media(self):
        for iid in self.tree.selection():
            self.media_sources_data = [i for i in self.media_sources_data if i['path'] != iid]
        self._populate_media_list_ui(); self._save_configuration()
    
    def _toggle_all_media(self, state):
        for item in self.media_sources_data: item['enabled_var'].set(state)
        self._populate_media_list_ui(); self._save_configuration()

    def _get_config_path(self): return os.path.join(os.path.expanduser("~"), CONFIG_FILE_NAME)
    
    def _save_configuration(self, *args):
        if hasattr(self, '_pause_trace') and self._pause_trace: return
        settings = {k: v.get() for k, v in self.setting_vars_map.items()}
        media = [{'path': i['path'], 'type': i['type'], 'enabled': i['enabled_var'].get()} for i in self.media_sources_data]
        try:
            with open(self._get_config_path(), 'w') as f: json.dump({"settings": settings, "media_sources": media}, f, indent=2)
        except Exception as e: print(f"Error saving config: {e}")

    def _load_configuration(self):
        path = self._get_config_path()
        if not os.path.exists(path): self._apply_preset(); return
        try:
            with open(path, 'r') as f: data = json.load(f)
            self._pause_trace = True
            settings = data.get("settings", {})
            for k, v_obj in self.setting_vars_map.items():
                if k in settings:
                    try: v_obj.set(settings[k])
                    except: pass
            self.media_sources_data = []
            for item in data.get("media_sources", []):
                if item.get('path') and os.path.exists(item['path']):
                    enabled_var = tk.BooleanVar(value=item.get('enabled', True))
                    enabled_var.trace_add('write', self._save_configuration)
                    self.media_sources_data.append({'path': item['path'], 'type': item['type'], 'enabled_var': enabled_var})
            self._pause_trace = False
            self._populate_media_list_ui(); self._toggle_ui_elements_by_mode()
        except Exception as e: print(f"Error loading config: {e}")

    def _on_run(self):
        enabled_sources = [{'path': i['path'], 'type': i['type']} for i in self.media_sources_data if i['enabled_var'].get()]
        if not enabled_sources: messagebox.showwarning("No Media", "Please add and enable at least one media source."); return
        params = {}
        for k, v in self.setting_vars_map.items():
            if '.' in k:
                top, sub = k.split('.')
                if top not in params: params[top] = {}
                params[top][sub] = v.get()
            else: params[k] = v.get()
        params.update({"screen_w": self.screen_w, "screen_h": self.screen_h, "media_sources": enabled_sources})
        
        self.is_zoomed = self.master.state() == 'zoomed'
        self.master.withdraw()
        run_pygame_visualization(params)
        self.master.deiconify()
        if self.is_zoomed:
             try: self.master.state('zoomed')
             except tk.TclError: self.master.attributes('-zoomed', True)
        self.master.lift(); self.master.focus_force()

    def _on_quit(self): self._save_configuration(); self.master.destroy()

# --- Main Application Entry ---
if __name__ == '__main__':
    if not MOVIEPY_AVAILABLE:
        root = tk.Tk(); root.withdraw()
        messagebox.showerror("Dependency Missing", "MoviePy is required for all video features. Please run: pip install moviepy")
        
    temp_root = tk.Tk()
    screen_w = temp_root.winfo_screenwidth()
    screen_h = temp_root.winfo_screenheight()
    temp_root.destroy()

    root = tk.Tk()
    app = VisualizationToolGUI_V2(root, screen_w, screen_h)
    root.mainloop()