import pygame
import random
import os
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter import font as tkFont
import json
import numpy as np

try:
    from moviepy.editor import ImageSequenceClip, AudioFileClip
    MOVIEPY_AVAILABLE = True
except ImportError:
    MOVIEPY_AVAILABLE = False
    print("WARNING: moviepy library not found. MP4 recording will be disabled.")
    print("Please install it: pip install moviepy")
    print("You might also need FFMPEG installed and in your system PATH.")

# --- Configuration Defaults ---
DEFAULT_FPS = 30
DEFAULT_COLOR_CHANGE_SPEED = 0.3
DEFAULT_MIN_FADE_TIME = 1.0
DEFAULT_MAX_FADE_TIME = 2.0
DEFAULT_MIN_VISIBLE_TIME = 0.3
DEFAULT_MAX_VISIBLE_TIME = 1.5
DEFAULT_MIN_SPAWN_DELAY = 0.5
DEFAULT_MAX_SPAWN_DELAY = 1.0
DEFAULT_SCALE_IMAGES = True
DEFAULT_MAX_IMAGE_WIDTH_PERCENT = 0.75
DEFAULT_MAX_IMAGE_HEIGHT_PERCENT = 0.75
DEFAULT_MAX_IMAGES_ON_SCREEN = 10

CONFIG_FILE_NAME = "image_fader_config_v2.json"

# --- Pygame Helper Functions ---
def get_random_color():
    return (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))

def interpolate_color(color1, color2, factor):
    r = int(color1[0] + (color2[0] - color1[0]) * factor)
    g = int(color1[1] + (color2[1] - color1[1]) * factor)
    b = int(color1[2] + (color2[2] - color1[2]) * factor)
    return (max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b)))

def load_image_paths_from_selected_dirs(directories_list):
    supported_formats = ('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp')
    all_paths = []
    if not directories_list:
        print("PYGAME: No directories provided to load images from.")
        return []
    print("\n--- PYGAME: Scanning Directories for Images ---")
    for directory in directories_list:
        if not os.path.isdir(directory):
            print(f"PYGAME Warning: Path is not a directory or not found: {directory}")
            continue
        current_dir_images = 0
        try:
            for filename in os.listdir(directory):
                if filename.lower().endswith(supported_formats):
                    all_paths.append(os.path.join(directory, filename))
                    current_dir_images +=1
            if current_dir_images > 0:
                print(f"PYGAME: Found {current_dir_images} images in '{os.path.basename(directory)}' ({directory})")
            else:
                print(f"PYGAME: No supported images found in '{os.path.basename(directory)}' ({directory})")
        except OSError as e:
            print(f"PYGAME Error accessing directory {directory}: {e}")
            continue
    if not all_paths:
        print("-----------------------------------------")
        print("PYGAME Warning: No images found in any of the selected directories.")
        print("-----------------------------------------")
    else:
        print(f"PYGAME: Total unique image paths loaded for this session: {len(all_paths)}")
        print("-----------------------------------------\n")
    return all_paths

def get_unique_filename(base_name):
    if not os.path.exists(base_name):
        return base_name
    name, ext = os.path.splitext(base_name)
    counter = 1
    while True:
        new_name = f"{name}_{counter}{ext}"
        if not os.path.exists(new_name):
            return new_name
        counter += 1

# --- Pygame Image Class ---
class FadingImage:
    def __init__(self, image_path, screen_width, screen_height,
                 p_scale_images, p_max_img_w_p, p_max_img_h_p,
                 p_min_fade, p_max_fade, p_min_visible, p_max_visible):
        self.surface = None
        self.original_surface = None

        try:
            loaded_surface = pygame.image.load(image_path)
        except pygame.error as e:
            print(f"PYGAME Error loading image {image_path}: {e}")
            return
        except Exception as e:
            print(f"PYGAME Generic error loading image {image_path}: {e}")
            return

        surface_to_process = loaded_surface

        if p_scale_images:
            img_w, img_h = surface_to_process.get_size()
            if img_w > 0 and img_h > 0:
                max_allowed_w = screen_width * p_max_img_w_p
                max_allowed_h = screen_height * p_max_img_h_p
                
                if img_w > max_allowed_w or img_h > max_allowed_h:
                    ratio_w = max_allowed_w / img_w
                    ratio_h = max_allowed_h / img_h
                    scale_ratio = min(ratio_w, ratio_h)
                    
                    if scale_ratio < 1.0:
                        new_width = max(1, int(img_w * scale_ratio))
                        new_height = max(1, int(img_h * scale_ratio))
                        try:
                            surface_to_process = pygame.transform.smoothscale(surface_to_process, (new_width, new_height))
                        except (pygame.error, ValueError) as e_scale:
                            print(f"PYGAME Warning: Error scaling {os.path.basename(image_path)}: {e_scale}. Using original.")
            else:
                print(f"PYGAME Warning: Image {os.path.basename(image_path)} has zero dimension. Skipping scaling.")

        try:
            self.original_surface = surface_to_process.convert_alpha()
        except pygame.error as e:
            print(f"PYGAME Error converting surface for {os.path.basename(image_path)}: {e}")
            return
            
        self.surface = self.original_surface.copy()
        self.rect = self.surface.get_rect()
        self.rect.x = random.randint(0, max(0, screen_width - self.rect.width))
        self.rect.y = random.randint(0, max(0, screen_height - self.rect.height))
        self.alpha = 0
        self.max_alpha = 255 
        self.fade_in_duration = random.uniform(p_min_fade, p_max_fade)
        self.visible_duration = random.uniform(p_min_visible, p_max_visible)
        self.fade_out_duration = random.uniform(p_min_fade, p_max_fade) 
        self.state = "fading_in"
        self.timer = 0.0

    def update(self, dt):
        if self.surface is None: return False
        self.timer += dt
        if self.state == "fading_in":
            self.alpha = min(self.max_alpha, (self.timer / self.fade_in_duration) * self.max_alpha) if self.fade_in_duration > 0 else self.max_alpha
            if self.timer >= self.fade_in_duration:
                self.alpha = self.max_alpha; self.state = "visible"; self.timer = 0.0
        elif self.state == "visible":
            if self.timer >= self.visible_duration:
                self.state = "fading_out"; self.timer = 0.0
        elif self.state == "fading_out":
            self.alpha = max(0, self.max_alpha - (self.timer / self.fade_out_duration) * self.max_alpha) if self.fade_out_duration > 0 else 0
            if self.timer >= self.fade_out_duration or self.alpha <= 0: return False
        self.surface.set_alpha(int(self.alpha))
        return True

    def draw(self, screen):
        if self.surface: screen.blit(self.surface, self.rect)

# --- Pygame Visualization Main Function ---
def run_pygame_visualization(selected_image_dirs, screen_width, screen_height,
                             p_fps, p_color_change_speed,
                             p_min_fade, p_max_fade, p_min_visible, p_max_visible,
                             p_min_spawn, p_max_spawn, p_scale_images,
                             p_max_img_w_p, p_max_img_h_p, p_max_imgs_screen,
                             audio_file_path=None, play_audio=False,
                             record_video=False, record_duration=0, record_filename="",
                             use_audio_duration=False):
    if not pygame.get_init(): pygame.init()
    if play_audio or (record_video and audio_file_path):
        pygame.mixer.init()

    print("PYGAME: Starting visualization with current settings...")
    try:
        screen = pygame.display.set_mode((screen_width, screen_height), pygame.FULLSCREEN | pygame.HWSURFACE | pygame.DOUBLEBUF)
    except pygame.error as e:
        print(f"PYGAME Error setting up Pygame fullscreen display: {e}")
        messagebox.showerror("Pygame Error", f"Could not set up fullscreen display:\n{e}\n\nReturning to GUI.")
        if pygame.mixer.get_init(): pygame.mixer.quit()
        if pygame.get_init(): pygame.quit()
        return
        
    pygame.display.set_caption("Greg Seymour - AI Visualization")
    pygame.mouse.set_visible(False)
    clock = pygame.time.Clock()

    current_top_color, target_top_color = get_random_color(), get_random_color()
    current_bottom_color, target_bottom_color = get_random_color(), get_random_color()
    color_lerp_factor = 0.0

    all_image_paths = load_image_paths_from_selected_dirs(selected_image_dirs)
    if not all_image_paths:
        messagebox.showwarning("No Images", "No images found in the selected directories. Returning to GUI.")
        pygame.mouse.set_visible(True)
        if play_audio and pygame.mixer.get_init(): pygame.mixer.music.stop(); pygame.mixer.quit()
        if pygame.get_init(): pygame.quit()
        return

    available_image_paths = []
    def replenish_image_paths():
        nonlocal available_image_paths
        if not all_image_paths: return
        available_image_paths = all_image_paths[:] 
        random.shuffle(available_image_paths)
    replenish_image_paths()
    active_images = []
    next_image_spawn_time = time.time() + random.uniform(p_min_spawn, p_max_spawn)
    
    running = True
    visualization_start_time = time.time()
    
    # Adjust recording duration if using audio duration
    if record_video and use_audio_duration and audio_file_path and MOVIEPY_AVAILABLE:
        try:
            audio_clip = AudioFileClip(audio_file_path)
            record_duration = audio_clip.duration
            print(f"PYGAME: Setting recording duration to audio length: {record_duration}s")
        except Exception as e:
            print(f"PYGAME Error: Could not determine audio duration: {e}")
            messagebox.showerror("Audio Duration Error", f"Could not determine duration of audio file:\n{audio_file_path}\n{e}\n\nUsing specified duration instead.", parent=None)
            record_duration = record_duration  # Fallback to specified duration

    # Audio Playback
    if play_audio and audio_file_path:
        try:
            pygame.mixer.music.load(audio_file_path)
            pygame.mixer.music.play(-1)
            print(f"PYGAME: Playing audio: {audio_file_path}")
        except pygame.error as e:
            print(f"PYGAME Error playing audio {audio_file_path}: {e}")

    # Video Recording Setup
    frames_for_video = []
    recording_active_this_session = False
    if record_video and MOVIEPY_AVAILABLE and record_filename and record_duration > 0:
        recording_active_this_session = True
        print(f"PYGAME: Recording to '{record_filename}' for {record_duration}s at {p_fps} FPS.")
        # Removed messagebox.showinfo for auto-start

    print("PYGAME: Visualization running. Press any key or mouse button to return to GUI.")

    while running:
        dt = clock.tick(p_fps) / 1000.0
        current_time = time.time()

        for event in pygame.event.get():
            if event.type == pygame.QUIT or event.type == pygame.KEYDOWN or event.type == pygame.MOUSEBUTTONDOWN:
                running = False
        if not running: break

        # Check recording duration with frame-based approach
        if recording_active_this_session:
            total_frames_needed = int(record_duration * p_fps)
            if len(frames_for_video) >= total_frames_needed:
                print(f"PYGAME: Recording duration ({record_duration}s) reached with {len(frames_for_video)} frames.")
                running = False
                break

        color_lerp_factor += p_color_change_speed * dt
        if color_lerp_factor >= 1.0:
            color_lerp_factor = 0.0
            current_top_color, target_top_color = target_top_color, get_random_color()
            current_bottom_color, target_bottom_color = target_bottom_color, get_random_color()

        display_top_color = interpolate_color(current_top_color, target_top_color, color_lerp_factor)
        display_bottom_color = interpolate_color(current_bottom_color, target_bottom_color, color_lerp_factor)

        if len(active_images) < p_max_imgs_screen and current_time >= next_image_spawn_time:
            if not available_image_paths: replenish_image_paths()
            if available_image_paths:
                img_path = available_image_paths.pop(0)
                new_image = FadingImage(img_path, screen_width, screen_height,
                                        p_scale_images, p_max_img_w_p, p_max_img_h_p,
                                        p_min_fade, p_max_fade, p_min_visible, p_max_visible)
                if new_image.surface: active_images.append(new_image)
            next_image_spawn_time = current_time + random.uniform(p_min_spawn, p_max_spawn)

        active_images[:] = [img for img in active_images if img.update(dt)]

        # Drawing
        for y_coord in range(screen_height):
            row_factor = y_coord / screen_height
            color = interpolate_color(display_top_color, display_bottom_color, row_factor)
            pygame.draw.line(screen, color, (0, y_coord), (screen_width, y_coord))
        for img in active_images: img.draw(screen)
        
        # Capture frame for video if recording
        if recording_active_this_session:
            frame = pygame.surfarray.array3d(screen)
            frame = np.transpose(frame, (1, 0, 2))
            frames_for_video.append(frame.copy())

        pygame.display.flip()

    # --- End of Visualization Loop ---
    print("PYGAME: Visualization ended.")
    
    if play_audio and pygame.mixer.get_init():
        try:
            pygame.mixer.music.stop()
            print("PYGAME: Audio stopped.")
        except pygame.error as e:
            print(f"PYGAME Error stopping audio: {e}")
    if pygame.mixer.get_init():
         pygame.mixer.quit()

    # Save video if recording was active
    if recording_active_this_session and frames_for_video:
        print(f"PYGAME: Compiling video from {len(frames_for_video)} frames...")
        try:
            video_clip = ImageSequenceClip(frames_for_video, fps=p_fps)
            
            final_clip = video_clip
            if audio_file_path:
                try:
                    audio_clip = AudioFileClip(audio_file_path)
                    final_clip = video_clip.set_audio(audio_clip.set_duration(video_clip.duration))
                    print(f"PYGAME: Audio '{os.path.basename(audio_file_path)}' will be muxed into video.")
                except Exception as e_audio_mux:
                    print(f"PYGAME Error: Could not load or attach audio to video: {e_audio_mux}")
                    messagebox.showwarning("Video Audio Error", f"Could not add audio to video:\n{e_audio_mux}\n\nVideo will be saved without audio.", parent=None)
            
            final_clip.write_videofile(record_filename, codec="libx264", audio_codec="aac", 
                                       threads=4, preset="medium")
            print(f"PYGAME: Video saved as {record_filename}")
            messagebox.showinfo("Recording Complete", f"Video saved successfully as:\n{record_filename}", parent=None)
        except Exception as e:
            print(f"PYGAME Error saving video: {e}")
            messagebox.showerror("Video Export Error", f"Could not save video:\n{e}\n\nMake sure FFMPEG is installed and in your PATH.", parent=None)
    
    pygame.mouse.set_visible(True)
    if pygame.get_init(): pygame.quit()

# --- Tkinter GUI Class ---
class DirectorySelectorGUI:
    def __init__(self, master, system_screen_w, system_screen_h):
        self.master = master
        self.system_screen_w = system_screen_w
        self.system_screen_h = system_screen_h
        
        self.master.resizable(True, True)
        try:
            self.master.state('zoomed')
        except tk.TclError:
             self.master.attributes('-fullscreen', False)
             self.master.geometry(f"{int(system_screen_w*0.9)}x{int(system_screen_h*0.85)}")

        self.master.title("Greg Seymour - AI Visualization Tool")
        
        self.directories_data = []
        self._init_style()
        self._init_vars()
        self._define_presets()
        self._define_help_texts()
        self._build_ui()
        self._load_configuration()
        self.master.protocol("WM_DELETE_WINDOW", self._on_quit)
        self.master.after(100, self._check_vars_for_custom_preset)

    def _init_style(self):
        self.style = ttk.Style()
        self.style.theme_use('clam')

        self.bg_color = "#2E3440"
        self.fg_color = "#E5E9F0"
        self.frame_bg = "#3B4252"
        self.accent_color_1 = "#88C0D0"
        self.accent_color_2 = "#BF616A"
        self.button_color = "#5E81AC"
        self.entry_bg = "#4C566A"

        self.style.configure('.', background=self.bg_color, foreground=self.fg_color, font=('Segoe UI', 10))
        self.style.configure('TFrame', background=self.frame_bg)
        self.style.configure('TLabel', background=self.frame_bg, foreground=self.fg_color, padding=5)
        self.style.configure('TLabelframe', background=self.frame_bg, bordercolor=self.accent_color_1)
        self.style.configure('TLabelframe.Label', background=self.frame_bg, foreground=self.accent_color_1, font=('Segoe UI Semibold', 12))
        
        self.style.configure('TButton', background=self.button_color, foreground=self.bg_color,
                             font=('Segoe UI Semibold', 10), padding=6)
        self.style.map('TButton',
                       background=[('active', self.accent_color_1), ('pressed', self.accent_color_1)],
                       foreground=[('active', self.bg_color)])
        
        self.style.configure('Accent.TButton', background=self.accent_color_2, foreground='white',
                             font=('Segoe UI Bold', 12), padding=8)
        self.style.map('Accent.TButton',
                       background=[('active', '#D08770'), ('pressed', '#D08770')])

        self.style.configure('Info.TButton', background=self.frame_bg, foreground=self.accent_color_1,
                             font=('Segoe UI', 8, 'bold'), padding=(1,0), borderwidth=0, relief=tk.FLAT)
        self.style.map('Info.TButton', foreground=[('active', self.fg_color)])

        self.style.configure('TCheckbutton', background=self.frame_bg, foreground=self.fg_color, indicatorcolor=self.fg_color)
        self.style.map('TCheckbutton',
                       indicatorcolor=[('selected', self.accent_color_1), ('active', self.accent_color_1)])
        
        self.style.configure('TEntry', fieldbackground=self.entry_bg, foreground=self.fg_color, insertcolor=self.fg_color, borderwidth=1, relief=tk.FLAT)
        self.style.configure('TSpinbox', fieldbackground=self.entry_bg, foreground=self.fg_color, arrowcolor=self.fg_color,
                             arrowbackground=self.button_color, borderwidth=1, relief=tk.FLAT)
        self.style.map('TSpinbox', background=[('readonly', self.entry_bg)])

        self.style.configure('Vertical.TScrollbar', background=self.button_color, troughcolor=self.frame_bg,
                             arrowcolor=self.fg_color)
        self.style.configure('Horizontal.TScale', troughcolor=self.entry_bg, background=self.button_color,
                             foreground=self.fg_color)
        self.style.map('Horizontal.TScale', background=[('active', self.accent_color_1)])
        
        self.title_font = tkFont.Font(family="Impact", size=28, weight="bold")
        self.info_button_font = tkFont.Font(family="Segoe UI", size=8, weight="bold")

    def _init_vars(self):
        self.scale_images_var = tk.BooleanVar(value=DEFAULT_SCALE_IMAGES)
        self.max_img_w_p_var = tk.DoubleVar(value=DEFAULT_MAX_IMAGE_WIDTH_PERCENT)
        self.max_img_h_p_var = tk.DoubleVar(value=DEFAULT_MAX_IMAGE_HEIGHT_PERCENT)
        self.min_fade_var = tk.DoubleVar(value=DEFAULT_MIN_FADE_TIME)
        self.max_fade_var = tk.DoubleVar(value=DEFAULT_MAX_FADE_TIME)
        self.min_visible_var = tk.DoubleVar(value=DEFAULT_MIN_VISIBLE_TIME)
        self.max_visible_var = tk.DoubleVar(value=DEFAULT_MAX_VISIBLE_TIME)
        self.min_spawn_var = tk.DoubleVar(value=DEFAULT_MIN_SPAWN_DELAY)
        self.max_spawn_var = tk.DoubleVar(value=DEFAULT_MAX_SPAWN_DELAY)
        self.max_imgs_screen_var = tk.IntVar(value=DEFAULT_MAX_IMAGES_ON_SCREEN)
        self.fps_var = tk.IntVar(value=DEFAULT_FPS)
        self.color_speed_var = tk.DoubleVar(value=DEFAULT_COLOR_CHANGE_SPEED)

        self.play_audio_var = tk.BooleanVar(value=False)
        self.audio_file_path_var = tk.StringVar(value="")
        self.record_video_var = tk.BooleanVar(value=False)
        self.record_filename_var = tk.StringVar(value="visualization_output.mp4")
        self.record_duration_var = tk.IntVar(value=30)
        self.use_audio_duration_var = tk.BooleanVar(value=False)

        self.setting_vars_map = {
            "scale_images": self.scale_images_var, "max_img_w_p": self.max_img_w_p_var,
            "max_img_h_p": self.max_img_h_p_var, "min_fade": self.min_fade_var,
            "max_fade": self.max_fade_var, "min_visible": self.min_visible_var,
            "max_visible": self.max_visible_var, "min_spawn": self.min_spawn_var,
            "max_spawn": self.max_spawn_var, "max_imgs_screen": self.max_imgs_screen_var,
            "fps": self.fps_var, "color_speed": self.color_speed_var
        }

        for var_name, var_obj in self.setting_vars_map.items():
            var_obj.trace_add("write", lambda *args, vn=var_name, vo=var_obj: self._on_setting_var_changed(vn, vo))
        
        self.play_audio_var.trace_add("write", lambda *a: self._check_vars_for_custom_preset())
        self.record_video_var.trace_add("write", lambda *a: self._toggle_recording_fields_state())
        self.use_audio_duration_var.trace_add("write", lambda *a: self._toggle_recording_fields_state())
        self.audio_file_path_var.trace_add("write", lambda *a: self._toggle_recording_fields_state())

    def _on_setting_var_changed(self, var_name, var_obj):
        self._save_configuration()
        self._check_vars_for_custom_preset()

    def _define_presets(self):
        self.presets = {
            "Custom": {},
            "Default": {
                "scale_images": DEFAULT_SCALE_IMAGES, "max_img_w_p": DEFAULT_MAX_IMAGE_WIDTH_PERCENT,
                "max_img_h_p": DEFAULT_MAX_IMAGE_HEIGHT_PERCENT, "min_fade": DEFAULT_MIN_FADE_TIME,
                "max_fade": DEFAULT_MAX_FADE_TIME, "min_visible": DEFAULT_MIN_VISIBLE_TIME,
                "max_visible": DEFAULT_MAX_VISIBLE_TIME, "min_spawn": DEFAULT_MIN_SPAWN_DELAY,
                "max_spawn": DEFAULT_MAX_SPAWN_DELAY, "max_imgs_screen": DEFAULT_MAX_IMAGES_ON_SCREEN,
                "fps": DEFAULT_FPS, "color_speed": DEFAULT_COLOR_CHANGE_SPEED
            },
            "Fast & Dynamic": {
                "scale_images": True, "max_img_w_p": 0.6, "max_img_h_p": 0.6,
                "min_fade": 0.3, "max_fade": 0.7, "min_visible": 0.2, "max_visible": 0.8,
                "min_spawn": 0.1, "max_spawn": 0.3, "max_imgs_screen": 15,
                "fps": 60, "color_speed": 0.8
            },
            "Slow & Gentle": {
                "scale_images": True, "max_img_w_p": 0.8, "max_img_h_p": 0.8,
                "min_fade": 2.0, "max_fade": 4.0, "min_visible": 3.0, "max_visible": 6.0,
                "min_spawn": 1.5, "max_spawn": 3.0, "max_imgs_screen": 5,
                "fps": 30, "color_speed": 0.1
            },
            "Image Showcase": {
                "scale_images": True, "max_img_w_p": 0.9, "max_img_h_p": 0.9,
                "min_fade": 2.5, "max_fade": 3.5, "min_visible": 5.0, "max_visible": 10.0,
                "min_spawn": 3.0, "max_spawn": 5.0, "max_imgs_screen": 3,
                "fps": 30, "color_speed": 0.05
            },
            "Chaotic": {
                "scale_images": True, "max_img_w_p": 0.3, "max_img_h_p": 0.3,
                "min_fade": 0.1, "max_fade": 0.2, "min_visible": 0.1, "max_visible": 0.3,
                "min_spawn": 0.05, "max_spawn": 0.1, "max_imgs_screen": 20,
                "fps": 60, "color_speed": 1.0
            },
            "Serene": {
                "scale_images": True, "max_img_w_p": 0.9, "max_img_h_p": 0.9,
                "min_fade": 3.0, "max_fade": 5.0, "min_visible": 10.0, "max_visible": 15.0,
                "min_spawn": 5.0, "max_spawn": 10.0, "max_imgs_screen": 2,
                "fps": 30, "color_speed": 0.05
            },
            "Minimalist": {
                "scale_images": True, "max_img_w_p": 0.8, "max_img_h_p": 0.8,
                "min_fade": 2.0, "max_fade": 3.0, "min_visible": 4.0, "max_visible": 6.0,
                "min_spawn": 2.0, "max_spawn": 4.0, "max_imgs_screen": 4,
                "fps": 30, "color_speed": 0.2
            },
            "Crowded": {
                "scale_images": True, "max_img_w_p": 0.2, "max_img_h_p": 0.2,
                "min_fade": 0.5, "max_fade": 1.0, "min_visible": 0.5, "max_visible": 1.5,
                "min_spawn": 0.2, "max_spawn": 0.5, "max_imgs_screen": 25,
                "fps": 60, "color_speed": 0.7
            },
            "Flashy": {
                "scale_images": True, "max_img_w_p": 0.5, "max_img_h_p": 0.5,
                "min_fade": 0.2, "max_fade": 0.5, "min_visible": 0.3, "max_visible": 0.7,
                "min_spawn": 0.1, "max_spawn": 0.3, "max_imgs_screen": 15,
                "fps": 60, "color_speed": 1.5
            },
            "Slideshow": {
                "scale_images": True, "max_img_w_p": 1.0, "max_img_h_p": 1.0,
                "min_fade": 1.0, "max_fade": 2.0, "min_visible": 5.0, "max_visible": 8.0,
                "min_spawn": 6.0, "max_spawn": 10.0, "max_imgs_screen": 1,
                "fps": 30, "color_speed": 0.1
            }
        }
        self.current_preset_var = tk.StringVar(value="Default")

    def _apply_preset(self, event=None):
        preset_name = self.current_preset_var.get()
        if preset_name == "Custom":
            return
            
        preset_settings = self.presets.get(preset_name)
        if preset_settings:
            self._pause_var_traces = True
            for key, value in preset_settings.items():
                if key in self.setting_vars_map:
                    self.setting_vars_map[key].set(value)
            self._pause_var_traces = False
            print(f"GUI: Applied preset '{preset_name}'")
        self._save_configuration()

    def _check_vars_for_custom_preset(self, *args):
        if hasattr(self, '_pause_var_traces') and self._pause_var_traces:
            return

        current_settings = {name: var.get() for name, var in self.setting_vars_map.items()}
        
        matched_preset = None
        for preset_name, preset_values in self.presets.items():
            if preset_name == "Custom": continue 
            
            is_match = True
            for key, p_val in preset_values.items():
                curr_val = current_settings.get(key)
                if isinstance(p_val, float):
                    if abs(curr_val - p_val) > 1e-5:
                        is_match = False
                        break
                elif curr_val != p_val:
                    is_match = False
                    break
            if is_match and len(preset_values) == len(current_settings):
                 matched_preset = preset_name
                 break
        
        if matched_preset:
            if self.current_preset_var.get() != matched_preset:
                self.current_preset_var.set(matched_preset)
        else:
            if self.current_preset_var.get() != "Custom":
                self.current_preset_var.set("Custom")

    def _define_help_texts(self):
        self.help_texts = {
            "scale_images": "Enable Image Scaling: If checked, images larger than the 'Max Image Width/Height Percent' will be scaled down to fit.",
            "max_img_w_p": "Max Image Width (% screen): Maximum width as a percentage of screen width.",
            "max_img_h_p": "Max Image Height (% screen): Maximum height as a percentage of screen height.",
            "min_fade": "Min Fade Time (s): Minimum duration for fade in/out.",
            "max_fade": "Max Fade Time (s): Maximum duration for fade in/out.",
            "min_visible": "Min Visible Time (s): Minimum time image stays fully visible.",
            "max_visible": "Max Visible Time (s): Maximum time image stays fully visible.",
            "min_spawn": "Min Spawn Delay (s): Minimum delay before a new image appears.",
            "max_spawn": "Max Spawn Delay (s): Maximum delay before a new image appears.",
            "max_imgs_screen": "Max Images on Screen: Maximum simultaneous images.",
            "fps": "Target FPS: Frames per second for animation and recording.",
            "color_speed": "BG Color Speed: Speed of background color transitions.",
            "load_preset": "Load Preset: Select predefined configurations.",
            "play_audio": "Play Audio: Play selected audio during visualization.",
            "select_audio": "Select Audio File: Choose an audio file to play.",
            "record_video": "Record to MP4: Record visualization to MP4 file.",
            "output_filename": "Output Filename: Name of the MP4 file.",
            "record_duration": "Recording Duration (s): Duration of the recording.",
            "use_audio_duration": "Use Audio Duration: Record for the length of the selected audio file."
        }

    def _show_help_info(self, setting_key):
        messagebox.showinfo(f"Info: {setting_key.replace('_', ' ').title()}", self.help_texts.get(setting_key, "No information available."), parent=self.master)

    def _get_config_path(self):
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), CONFIG_FILE_NAME)

    def _load_configuration(self):
        config_path = self._get_config_path()
        loaded_dirs = []
        settings = {}
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    config_data = json.load(f)
                    loaded_dirs = config_data.get("directories", [])
                    settings = config_data.get("settings", {})
                print(f"GUI: Configuration loaded from {config_path}")
            else:
                print(f"GUI: No configuration file found. Using defaults.")
                self.current_preset_var.set("Default")
                self._apply_preset()
                return

        except Exception as e:
            print(f"GUI Error loading configuration: {e}. Using defaults.")
            self.current_preset_var.set("Default")
            self._apply_preset()
            return

        self.directories_data = []
        for item in loaded_dirs:
            path, enabled = item.get("path"), item.get("enabled", True)
            if path and os.path.isdir(path):
                enabled_var = tk.BooleanVar(value=enabled)
                enabled_var.trace_add("write", lambda *args, p=path: self._save_configuration())
                self.directories_data.append({'path': path, 'enabled_var': enabled_var})
            elif path: print(f"GUI Warning: Saved directory not found: {path}")
        
        self._pause_var_traces = True
        for key, var_obj in self.setting_vars_map.items():
            if key in settings:
                try:
                    var_obj.set(settings[key])
                except tk.TclError:
                    if isinstance(var_obj, tk.BooleanVar):
                         var_obj.set(bool(settings[key]))
                    else:
                        print(f"GUI Warning: Could not set {key} from config value {settings[key]}")
        self._pause_var_traces = False
        self._populate_dir_list_ui()
        self._check_vars_for_custom_preset()

    def _save_configuration(self):
        if hasattr(self, '_pause_var_traces') and self._pause_var_traces:
            return

        config_path = self._get_config_path()
        dirs_to_save = [{'path': item['path'], 'enabled': item['enabled_var'].get()} for item in self.directories_data]
        
        settings_to_save = {name: var.get() for name, var in self.setting_vars_map.items()}
        
        try:
            with open(config_path, 'w') as f:
                json.dump({"directories": dirs_to_save, "settings": settings_to_save}, f, indent=4)
        except Exception as e:
            print(f"GUI Error saving configuration: {e}")

    def _build_ui(self):
        self.master.configure(background=self.bg_color)
        main_frame = ttk.Frame(self.master, style='TFrame', padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True)
        main_frame.columnconfigure(0, weight=3)
        main_frame.columnconfigure(1, weight=4)
        main_frame.rowconfigure(1, weight=1)

        title_label = ttk.Label(main_frame, text="Greg Seymour - AI Visualization Tool",
                                font=self.title_font, anchor="center",
                                style='TLabel', foreground=self.accent_color_1, background=self.bg_color)
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20), sticky="ew")

        # --- Left Panel: Directories ---
        dir_panel = ttk.Frame(main_frame, style='TFrame')
        dir_panel.grid(row=1, column=0, sticky="nsew", padx=(0,10))
        dir_panel.rowconfigure(1, weight=1)
        dir_panel.columnconfigure(0, weight=1)

        dir_buttons_frame = ttk.Frame(dir_panel, style='TFrame')
        dir_buttons_frame.grid(row=0, column=0, sticky="ew", pady=(0,10))
        ttk.Button(dir_buttons_frame, text="Add Directory", command=self._add_new_directory).pack(side=tk.LEFT, padx=2)
        ttk.Button(dir_buttons_frame, text="Sort A-Z", command=self._sort_dirs).pack(side=tk.LEFT, padx=2)
        ttk.Button(dir_buttons_frame, text="Select All", command=self._select_all_dirs).pack(side=tk.LEFT, padx=2)
        ttk.Button(dir_buttons_frame, text="Deselect All", command=self._deselect_all_dirs).pack(side=tk.LEFT, padx=2)

        list_container = ttk.LabelFrame(dir_panel, text="Image Directories", style='TLabelframe')
        list_container.grid(row=1, column=0, sticky="nsew")
        list_container.rowconfigure(0, weight=1)
        list_container.columnconfigure(0, weight=1)

        self.canvas = tk.Canvas(list_container, borderwidth=0, background=self.frame_bg, highlightthickness=0)
        self.dir_list_frame = ttk.Frame(self.canvas, style='TFrame')
        self.scrollbar = ttk.Scrollbar(list_container, orient="vertical", command=self.canvas.yview, style='Vertical.TScrollbar')
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.scrollbar.grid(row=0, column=1, sticky="ns")
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.canvas_window = self.canvas.create_window((0, 0), window=self.dir_list_frame, anchor="nw")
        
        def _on_canvas_configure(event):
            self.canvas.itemconfig(self.canvas_window, width=event.width)
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))

        self.dir_list_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind('<Configure>', _on_canvas_configure)
        
        self.master.bind_all("<MouseWheel>", lambda e: self.canvas.yview_scroll(int(-1*(e.delta/120)), "units"), add="+")
        self.master.bind_all("<Button-4>", lambda e: self.canvas.yview_scroll(-1, "units"), add="+")
        self.master.bind_all("<Button-5>", lambda e: self.canvas.yview_scroll(1, "units"), add="+")

        # --- Right Panel: Settings ---
        settings_scroll_canvas = tk.Canvas(main_frame, borderwidth=0, background=self.frame_bg, highlightthickness=0)
        settings_scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=settings_scroll_canvas.yview, style='Vertical.TScrollbar')
        settings_scroll_canvas.configure(yscrollcommand=settings_scrollbar.set)
        
        settings_scroll_canvas.grid(row=1, column=1, sticky="nsew", padx=(10,0))
        settings_scrollbar.grid(row=1, column=2, sticky="ns", padx=(0,0))

        self.settings_panel_content = ttk.LabelFrame(settings_scroll_canvas, text="Visualization Settings", style='TLabelframe')
        settings_scroll_canvas.create_window((0,0), window=self.settings_panel_content, anchor="nw", tags="settings_frame")

        def _on_settings_panel_content_configure(event):
            settings_scroll_canvas.configure(scrollregion=settings_scroll_canvas.bbox("all"))
            settings_scroll_canvas.itemconfig("settings_frame", width=event.width)

        self.settings_panel_content.bind("<Configure>", _on_settings_panel_content_configure)
        self.settings_panel_content.bind_all("<MouseWheel>", lambda e: settings_scroll_canvas.yview_scroll(int(-1*(e.delta/120)), "units"), add="+")
        self.settings_panel_content.bind_all("<Button-4>", lambda e: settings_scroll_canvas.yview_scroll(-1, "units"), add="+")
        self.settings_panel_content.bind_all("<Button-5>", lambda e: settings_scroll_canvas.yview_scroll(1, "units"), add="+")
        
        spc = self.settings_panel_content
        spc.columnconfigure(1, weight=1)
        spc.columnconfigure(2, weight=0)
        spc.columnconfigure(3, weight=0)

        row_idx = 0
        
        def add_setting_control(label_text, var, setting_key, from_=0, to=1, resolution=0.01, is_scale=True, is_bool=False, min_val=None, max_val=None, precision=2):
            nonlocal row_idx
            
            label_frame = ttk.Frame(spc, style='TFrame')
            label_frame.grid(row=row_idx, column=0, sticky="w", padx=5, pady=3)
            ttk.Label(label_frame, text=label_text, style='TLabel').pack(side=tk.LEFT)
            ttk.Button(label_frame, text="(i)", style='Info.TButton', width=3,
                       command=lambda sk=setting_key: self._show_help_info(sk)).pack(side=tk.LEFT, padx=(2,0))

            if is_bool:
                ttk.Checkbutton(spc, variable=var, style='TCheckbutton').grid(row=row_idx, column=1, columnspan=2, sticky="w", padx=5, pady=3)
            elif is_scale:
                control_frame = ttk.Frame(spc, style='TFrame')
                control_frame.grid(row=row_idx, column=1, columnspan=2, sticky="ew", padx=5, pady=3)
                control_frame.columnconfigure(0, weight=3)
                control_frame.columnconfigure(1, weight=1)

                scale = ttk.Scale(control_frame, variable=var, from_=from_, to=to, orient=tk.HORIZONTAL, style='Horizontal.TScale')
                scale.grid(row=0, column=0, sticky="ew", padx=(0,5))
                
                entry = ttk.Entry(control_frame, textvariable=var, width=6, style='TEntry')
                entry.grid(row=0, column=1, sticky="e")

                def _update_from_scale(value_str):
                    try:
                        if self.master.focus_get() != entry:
                             entry.delete(0, tk.END)
                             entry.insert(0, f"{float(value_str):.{precision}f}")
                    except: pass

                def _update_from_entry(event=None):
                    try:
                        val_str = entry.get()
                        val = float(val_str) if precision > 0 else int(val_str)
                        clamped_val = max(from_, min(to, val))
                        if clamped_val != val:
                            entry.delete(0, tk.END)
                            entry.insert(0, f"{clamped_val:.{precision}f}")
                            val = clamped_val
                        var.set(val)
                        scale.set(val)
                    except ValueError:
                        current_var_val = var.get()
                        entry.delete(0, tk.END)
                        entry.insert(0, f"{current_var_val:.{precision}f}")
                
                var.trace_add("write", lambda name, index, mode, v=var: _update_from_scale(v.get()))
                entry.bind("<Return>", _update_from_entry)
                entry.bind("<FocusOut>", _update_from_entry)
                _update_from_scale(var.get())

            else:
                spin = ttk.Spinbox(spc, textvariable=var, from_=from_, to=to, increment=resolution, wrap=False, style='TSpinbox', width=8)
                if min_val is not None and max_val is not None:
                     spin.configure(from_=min_val, to=max_val)
                spin.grid(row=row_idx, column=1, sticky="w", padx=5, pady=3)
            row_idx += 1
            return row_idx

        preset_frame = ttk.Frame(spc, style='TFrame')
        preset_frame.grid(row=row_idx, column=0, columnspan=3, sticky="ew", pady=(10,5), padx=5)
        ttk.Label(preset_frame, text="Load Preset:", style='TLabel').pack(side=tk.LEFT, padx=(0,2))
        self.preset_combo = ttk.Combobox(preset_frame, textvariable=self.current_preset_var,
                                         values=list(self.presets.keys()), state="readonly", width=20)
        self.preset_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0,5))
        self.preset_combo.bind("<<ComboboxSelected>>", self._apply_preset)
        ttk.Button(preset_frame, text="(i)", style='Info.TButton', width=3,
                   command=lambda: self._show_help_info("load_preset")).pack(side=tk.LEFT)
        row_idx += 1

        add_setting_control("Image Scaling:", self.scale_images_var, "scale_images", is_bool=True)
        add_setting_control("Max Img Width (%):", self.max_img_w_p_var, "max_img_w_p", 0.01, 1.0, 0.01, precision=2)
        add_setting_control("Max Img Height (%):", self.max_img_h_p_var, "max_img_h_p", 0.01, 1.0, 0.01, precision=2)
        add_setting_control("Min Fade (s):", self.min_fade_var, "min_fade", 0.1, 10.0, 0.1, precision=1)
        add_setting_control("Max Fade (s):", self.max_fade_var, "max_fade", 0.1, 10.0, 0.1, precision=1)
        add_setting_control("Min Visible (s):", self.min_visible_var, "min_visible", 0.1, 20.0, 0.1, precision=1)
        add_setting_control("Max Visible (s):", self.max_visible_var, "max_visible", 0.1, 20.0, 0.1, precision=1)
        add_setting_control("Min Spawn (s):", self.min_spawn_var, "min_spawn", 0.05, 5.0, 0.05, precision=2)
        add_setting_control("Max Spawn (s):", self.max_spawn_var, "max_spawn", 0.05, 5.0, 0.05, precision=2)
        add_setting_control("Max Images:", self.max_imgs_screen_var, "max_imgs_screen", is_scale=False, from_=1, to=100, resolution=1)
        add_setting_control("Target FPS:", self.fps_var, "fps", is_scale=False, from_=10, to=120, resolution=1)
        add_setting_control("BG Color Speed:", self.color_speed_var, "color_speed", 0.01, 2.0, 0.01, precision=2)

        ttk.Separator(spc, orient=tk.HORIZONTAL).grid(row=row_idx, column=0, columnspan=3, sticky="ew", pady=10)
        row_idx+=1

        audio_label_frame = ttk.Frame(spc, style='TFrame')
        audio_label_frame.grid(row=row_idx, column=0, sticky="w", padx=5, pady=3)
        ttk.Label(audio_label_frame, text="Play Audio:", style='TLabel').pack(side=tk.LEFT)
        ttk.Button(audio_label_frame, text="(i)", style='Info.TButton', width=3, command=lambda: self._show_help_info("play_audio")).pack(side=tk.LEFT, padx=(2,0))
        ttk.Checkbutton(spc, variable=self.play_audio_var, style='TCheckbutton').grid(row=row_idx, column=1, columnspan=2, sticky="w", padx=5, pady=3)
        row_idx+=1

        audio_file_frame = ttk.Frame(spc, style='TFrame')
        audio_file_frame.grid(row=row_idx, column=0, sticky="w", padx=5, pady=3)
        ttk.Button(audio_file_frame, text="Select Audio File:", command=self._select_audio_file).pack(side=tk.LEFT)
        ttk.Button(audio_file_frame, text="(i)", style='Info.TButton', width=3, command=lambda: self._show_help_info("select_audio")).pack(side=tk.LEFT, padx=(2,0))
        
        self.audio_file_label = ttk.Label(spc, textvariable=self.audio_file_path_var, style='TLabel', relief="sunken", width=30, anchor='w', wraplength=200)
        self.audio_file_label.grid(row=row_idx, column=1, columnspan=2, sticky="ew", padx=5, pady=3)
        row_idx+=1
        
        ttk.Separator(spc, orient=tk.HORIZONTAL).grid(row=row_idx, column=0, columnspan=3, sticky="ew", pady=10)
        row_idx+=1

        rec_label_frame = ttk.Frame(spc, style='TFrame')
        rec_label_frame.grid(row=row_idx, column=0, sticky="w", padx=5, pady=3)
        ttk.Label(rec_label_frame, text="Record to MP4:", style='TLabel').pack(side=tk.LEFT)
        ttk.Button(rec_label_frame, text="(i)", style='Info.TButton', width=3, command=lambda: self._show_help_info("record_video")).pack(side=tk.LEFT, padx=(2,0))
        self.record_video_check = ttk.Checkbutton(spc, variable=self.record_video_var, style='TCheckbutton', command=self._toggle_recording_fields_state)
        self.record_video_check.grid(row=row_idx, column=1, columnspan=2, sticky="w", padx=5, pady=3)
        row_idx+=1

        rec_file_frame = ttk.Frame(spc, style='TFrame')
        rec_file_frame.grid(row=row_idx, column=0, sticky="w", padx=5, pady=3)
        self.rec_browse_button = ttk.Button(rec_file_frame, text="Output Filename:", command=self._select_record_filename)
        self.rec_browse_button.pack(side=tk.LEFT)
        ttk.Button(rec_file_frame, text="(i)", style='Info.TButton', width=3, command=lambda: self._show_help_info("output_filename")).pack(side=tk.LEFT, padx=(2,0))
        
        self.record_filename_entry = ttk.Entry(spc, textvariable=self.record_filename_var, width=30, style='TEntry')
        self.record_filename_entry.grid(row=row_idx, column=1, columnspan=2, sticky="ew", padx=5, pady=3)
        row_idx+=1

        rec_dur_frame = ttk.Frame(spc, style='TFrame')
        rec_dur_frame.grid(row=row_idx, column=0, sticky="w", padx=5, pady=3)
        ttk.Label(rec_dur_frame, text="Rec. Duration (s):", style='TLabel').pack(side=tk.LEFT)
        ttk.Button(rec_dur_frame, text="(i)", style='Info.TButton', width=3, command=lambda: self._show_help_info("record_duration")).pack(side=tk.LEFT, padx=(2,0))
        self.record_duration_spinbox = ttk.Spinbox(spc, textvariable=self.record_duration_var, from_=1, to=3600, increment=1, wrap=False, style='TSpinbox', width=8)
        self.record_duration_spinbox.grid(row=row_idx, column=1, sticky="w", padx=5, pady=3)
        row_idx+=1

        use_audio_dur_frame = ttk.Frame(spc, style='TFrame')
        use_audio_dur_frame.grid(row=row_idx, column=0, sticky="w", padx=5, pady=3)
        ttk.Label(use_audio_dur_frame, text="Use Audio Duration:", style='TLabel').pack(side=tk.LEFT)
        ttk.Button(use_audio_dur_frame, text="(i)", style='Info.TButton', width=3, command=lambda: self._show_help_info("use_audio_duration")).pack(side=tk.LEFT, padx=(2,0))
        self.use_audio_duration_check = ttk.Checkbutton(spc, variable=self.use_audio_duration_var, style='TCheckbutton')
        self.use_audio_duration_check.grid(row=row_idx, column=1, columnspan=2, sticky="w", padx=5, pady=3)
        row_idx+=1

        self._toggle_recording_fields_state()

        bottom_button_frame = ttk.Frame(main_frame, style='TFrame')
        bottom_button_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(15,0))
        bottom_button_frame.columnconfigure(0, weight=1)
        bottom_button_frame.columnconfigure(1, weight=1)
        bottom_button_frame.columnconfigure(2, weight=1)
        
        run_button = ttk.Button(bottom_button_frame, text="Run Visualization", command=self._on_run_visualization, style="Accent.TButton")
        run_button.grid(row=0, column=0, sticky="ew", padx=(0,5))

        instructions_button = ttk.Button(bottom_button_frame, text="Show Instructions", command=self._show_general_instructions)
        instructions_button.grid(row=0, column=1, sticky="ew", padx=5)
        
        quit_button = ttk.Button(bottom_button_frame, text="Quit Program", command=self._on_quit)
        quit_button.grid(row=0, column=2, sticky="ew", padx=(5,0))

    def _populate_dir_list_ui(self):
        for widget in self.dir_list_frame.winfo_children(): widget.destroy()
        if not self.directories_data:
            ttk.Label(self.dir_list_frame, text="No directories added. Click 'Add Directory'.", style='TLabel', wraplength=self.canvas.winfo_width()-20).pack(pady=10, padx=10, fill=tk.X)
        
        for item_data in self.directories_data:
            path, enabled_var = item_data['path'], item_data['enabled_var']
            entry_frame = ttk.Frame(self.dir_list_frame, style='TFrame')
            entry_frame.pack(fill=tk.X, pady=1, padx=2)
            check = ttk.Checkbutton(entry_frame, variable=enabled_var, style='TCheckbutton')
            check.pack(side=tk.LEFT, padx=(0, 3))
            
            max_len = 65
            display_path = path if len(path) <= max_len else f"...{path[-(max_len-3):]}"

            label = ttk.Label(entry_frame, text=display_path, anchor="w", style='TLabel', cursor="hand2")
            label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=3)
            label.bind("<Button-1>", lambda e, p=path: self._toggle_check_for_path(p))
            label.bind("<Enter>", lambda e, l=label, p=path: l.configure(tool_tip_text=p))
            
            remove_btn = ttk.Button(entry_frame, text="X", width=3, style='TButton',
                                   command=lambda p=path: self._remove_dir_entry(p))
            remove_btn.pack(side=tk.RIGHT, padx=(3,0))
        
        self.master.after(50, lambda: self.canvas.configure(scrollregion=self.canvas.bbox("all")))

    def _toggle_check_for_path(self, path_to_toggle):
        for item in self.directories_data:
            if item['path'] == path_to_toggle:
                item['enabled_var'].set(not item['enabled_var'].get())
                break 

    def _add_new_directory(self):
        dir_path = filedialog.askdirectory(master=self.master, title="Select Image Directory")
        if dir_path:
            norm_path = os.path.normpath(dir_path)
            if any(item['path'] == norm_path for item in self.directories_data):
                messagebox.showinfo("Duplicate", "This directory is already in the list.", parent=self.master)
                return
            enabled_var = tk.BooleanVar(value=True)
            enabled_var.trace_add("write", lambda *args: self._save_configuration())
            self.directories_data.append({'path': norm_path, 'enabled_var': enabled_var})
            self._populate_dir_list_ui()
            self._save_configuration()

    def _remove_dir_entry(self, path_to_remove):
        self.directories_data = [item for item in self.directories_data if item['path'] != path_to_remove]
        self._populate_dir_list_ui()
        self._save_configuration()

    def _select_all_dirs(self):
        for item in self.directories_data: item['enabled_var'].set(True)
    
    def _deselect_all_dirs(self):
        for item in self.directories_data: item['enabled_var'].set(False)

    def _sort_dirs(self):
        self.directories_data.sort(key=lambda item: item['path'].lower())
        self._populate_dir_list_ui()
        self._save_configuration()

    def _select_audio_file(self):
        filepath = filedialog.askopenfilename(
            master=self.master,
            title="Select Audio File",
            filetypes=(("Audio Files", "*.mp3 *.wav *.ogg"), ("All files", "*.*"))
        )
        if filepath:
            self.audio_file_path_var.set(filepath)
            print(f"GUI: Selected audio file: {filepath}")

    def _select_record_filename(self):
        filepath = filedialog.asksaveasfilename(
            master=self.master,
            title="Save MP4 Video As...",
            defaultextension=".mp4",
            initialfile=self.record_filename_var.get(),
            filetypes=(("MP4 Video", "*.mp4"), ("All files", "*.*"))
        )
        if filepath:
            unique_filepath = get_unique_filename(filepath)
            self.record_filename_var.set(unique_filepath)

    def _toggle_recording_fields_state(self):
        state = tk.NORMAL if self.record_video_var.get() else tk.DISABLED
        if hasattr(self, 'rec_browse_button'): self.rec_browse_button.configure(state=state)
        if hasattr(self, 'record_filename_entry'): self.record_filename_entry.configure(state=state)
        if self.use_audio_duration_var.get() and self.audio_file_path_var.get():
            self.record_duration_spinbox.configure(state=tk.DISABLED)
        else:
            self.record_duration_spinbox.configure(state=state if self.record_video_var.get() else tk.DISABLED)
        
        if not MOVIEPY_AVAILABLE and self.record_video_var.get():
            messagebox.showwarning("MoviePy Missing", 
                                   "The 'moviepy' library is not installed. MP4 recording is disabled.\n"
                                   "Please install it by running: pip install moviepy\n"
                                   "You may also need FFMPEG.", parent=self.master)
            self.record_video_var.set(False)
            self.rec_browse_button.configure(state=tk.DISABLED)
            self.record_filename_entry.configure(state=tk.DISABLED)
            self.record_duration_spinbox.configure(state=tk.DISABLED)

    def _show_general_instructions(self):
        instructions = """Welcome to the AI Visualization Tool!

1. **Add Image Directories:**
    * Click "Add Directory" to select folders with images.
    * Enable/disable directories with checkboxes.

2. **Configure Settings:**
    * Adjust settings for image fading, timing, etc.
    * Use "Load Preset" for quick setups (10+ options available).

3. **Audio (Optional):**
    * Check "Play Audio" and select a file.
    * Check "Use Audio Duration" to record for the audio's length.

4. **Record to MP4 (Optional):**
    * Check "Record to MP4" and set filename/duration.
    * Files are numbered sequentially (e.g., video_1.mp4).

5. **Run Visualization:**
    * Click "Run Visualization" to start fullscreen.
    * No confirmation box when recording; it starts immediately.
    * Press any key or click to return to GUI.

6. **Quit:**
    * Click "Quit Program" to exit."""
        messagebox.showinfo("Instructions - AI Visualization Tool", instructions, parent=self.master)

    def _on_run_visualization(self):
        if self.min_fade_var.get() > self.max_fade_var.get():
            messagebox.showerror("Settings Error", "Min Fade Time cannot be greater than Max Fade Time.", parent=self.master)
            return
        if self.min_visible_var.get() > self.max_visible_var.get():
            messagebox.showerror("Settings Error", "Min Visible Time cannot be greater than Max Visible Time.", parent=self.master)
            return
        if self.min_spawn_var.get() > self.max_spawn_var.get():
            messagebox.showerror("Settings Error", "Min Spawn Delay cannot be greater than Max Spawn Delay.", parent=self.master)
            return

        selected_paths = [item['path'] for item in self.directories_data if item['enabled_var'].get()]
        if not selected_paths:
            messagebox.showwarning("No Directories", "Please select at least one directory.", parent=self.master)
            return

        if self.play_audio_var.get() and not self.audio_file_path_var.get():
            messagebox.showwarning("Audio File Missing", "Play Audio enabled but no file selected.", parent=self.master)
            return
        
        if self.record_video_var.get():
            if not MOVIEPY_AVAILABLE:
                messagebox.showerror("Recording Error", "MoviePy not available.", parent=self.master)
                return
            if not self.record_filename_var.get():
                messagebox.showerror("Recording Error", "Specify an output filename.", parent=self.master)
                return
            if self.record_duration_var.get() <= 0 and not self.use_audio_duration_var.get():
                messagebox.showerror("Recording Error", "Recording duration must be greater than 0.", parent=self.master)
                return

        self.master.withdraw()
        if pygame.get_init(): pygame.quit()

        run_pygame_visualization(
            selected_paths, self.system_screen_w, self.system_screen_h,
            p_fps=self.fps_var.get(), p_color_change_speed=self.color_speed_var.get(),
            p_min_fade=self.min_fade_var.get(), p_max_fade=self.max_fade_var.get(),
            p_min_visible=self.min_visible_var.get(), p_max_visible=self.max_visible_var.get(),
            p_min_spawn=self.min_spawn_var.get(), p_max_spawn=self.max_spawn_var.get(),
            p_scale_images=self.scale_images_var.get(),
            p_max_img_w_p=self.max_img_w_p_var.get(), p_max_img_h_p=self.max_img_h_p_var.get(),
            p_max_imgs_screen=self.max_imgs_screen_var.get(),
            audio_file_path=self.audio_file_path_var.get() if self.play_audio_var.get() else None,
            play_audio=self.play_audio_var.get(),
            record_video=self.record_video_var.get(),
            record_duration=self.record_duration_var.get(),
            record_filename=self.record_filename_var.get(),
            use_audio_duration=self.use_audio_duration_var.get()
        )
        
        if pygame.get_init(): pygame.quit()
        self.master.deiconify(); self.master.lift(); self.master.focus_force()

    def _on_quit(self):
        self._save_configuration()
        if pygame.get_init(): pygame.quit()
        self.master.quit()
        self.master.destroy()

# --- Main Application Entry ---
if __name__ == '__main__':
    if not MOVIEPY_AVAILABLE:
        temp_root = tk.Tk()
        temp_root.withdraw()
        messagebox.showwarning("Dependency Missing",
                               "The 'moviepy' library was not found. MP4 recording features will be disabled.\n"
                               "To enable recording, install moviepy: pip install moviepy\n"
                               "You might also need FFMPEG in your PATH.",
                               parent=None)
        temp_root.destroy()
        
    root_temp = tk.Tk()
    root_temp.withdraw()
    tk_screen_width = root_temp.winfo_screenwidth()
    tk_screen_height = root_temp.winfo_screenheight()
    root_temp.destroy()

    pg_screen_width, pg_screen_height = 0,0
    try:
        pygame.init()
        info = pygame.display.Info()
        pg_screen_width = info.current_w
        pg_screen_height = info.current_h
        pygame.quit()
    except pygame.error:
        print("Warning: Could not get Pygame screen dimensions. Using Tkinter's.")
        pg_screen_width, pg_screen_height = tk_screen_width, tk_screen_height

    if pg_screen_width == 0 or pg_screen_height == 0:
        pg_screen_width, pg_screen_height = 1024, 768

    root = tk.Tk()
    app = DirectorySelectorGUI(root, pg_screen_width, pg_screen_height)
    root.mainloop()
    print("Application has exited.")