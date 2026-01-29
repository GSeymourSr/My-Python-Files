import pygame
import random
import os
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter import font as tkFont
import json
import numpy as np

# --- Dependency Check for moviepy ---
# We check if moviepy is available. If not, we set a flag and disable recording features.
try:
    from moviepy.editor import ImageSequenceClip, AudioFileClip
    MOVIEPY_AVAILABLE = True
except ImportError:
    MOVIEPY_AVAILABLE = False
    print("WARNING: moviepy library not found. MP4 recording will be disabled.")
    print("Please install it: pip install moviepy")
    print("You might also need FFMPEG installed and in your system PATH.")

# --- Configuration Defaults ---
# These are the default values used if no config file is found or for the 'Default' preset.
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

# The name of the JSON file where all GUI settings and directories are saved.
CONFIG_FILE_NAME = "image_fader_config_v2.json"

# --- Pygame Helper Functions ---

def get_random_color():
    """Returns a random RGB color tuple."""
    return (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))

def interpolate_color(color1, color2, factor):
    """Linearly interpolates between two colors. Factor is 0.0 to 1.0."""
    r = int(color1[0] + (color2[0] - color1[0]) * factor)
    g = int(color1[1] + (color2[1] - color1[1]) * factor)
    b = int(color1[2] + (color2[2] - color1[2]) * factor)
    # Clamp values to the valid 0-255 range.
    return (max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b)))

def load_image_paths_from_selected_dirs(directories_list):
    """Scans a list of directory paths and returns a list of all found image file paths."""
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
                    current_dir_images += 1
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
    """Ensures a filename is unique by appending a number if it already exists."""
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
    """Represents a single image on the screen, handling its fading, position, and lifecycle."""
    def __init__(self, image_path, screen_width, screen_height,
                 p_scale_images, p_max_img_w_p, p_max_img_h_p,
                 p_min_fade, p_max_fade, p_min_visible, p_max_visible):
        self.surface = None
        self.original_surface = None

        try:
            # Load the image from the provided path.
            loaded_surface = pygame.image.load(image_path)
        except pygame.error as e:
            print(f"PYGAME Error loading image {image_path}: {e}")
            return
        except Exception as e:
            print(f"PYGAME Generic error loading image {image_path}: {e}")
            return

        surface_to_process = loaded_surface

        # Scale the image down if it's too large, based on GUI settings.
        if p_scale_images:
            img_w, img_h = surface_to_process.get_size()
            if img_w > 0 and img_h > 0:
                max_allowed_w = screen_width * p_max_img_w_p
                max_allowed_h = screen_height * p_max_img_h_p
                
                if img_w > max_allowed_w or img_h > max_allowed_h:
                    # Calculate the correct aspect ratio to scale the image without distortion.
                    ratio_w = max_allowed_w / img_w
                    ratio_h = max_allowed_h / img_h
                    scale_ratio = min(ratio_w, ratio_h)
                    
                    if scale_ratio < 1.0:
                        new_width = max(1, int(img_w * scale_ratio))
                        new_height = max(1, int(img_h * scale_ratio))
                        try:
                            # Use smoothscale for better quality resizing.
                            surface_to_process = pygame.transform.smoothscale(surface_to_process, (new_width, new_height))
                        except (pygame.error, ValueError) as e_scale:
                            print(f"PYGAME Warning: Error scaling {os.path.basename(image_path)}: {e_scale}. Using original.")
            else:
                print(f"PYGAME Warning: Image {os.path.basename(image_path)} has zero dimension. Skipping scaling.")

        try:
            # Convert the surface to a format that's faster for Pygame to blit and supports alpha.
            self.original_surface = surface_to_process.convert_alpha()
        except pygame.error as e:
            print(f"PYGAME Error converting surface for {os.path.basename(image_path)}: {e}")
            return
            
        self.surface = self.original_surface.copy()
        self.rect = self.surface.get_rect()
        
        # Position the image randomly on the screen.
        self.rect.x = random.randint(0, max(0, screen_width - self.rect.width))
        self.rect.y = random.randint(0, max(0, screen_height - self.rect.height))
        
        # Initialize animation state variables.
        self.alpha = 0  # Start fully transparent
        self.max_alpha = 255 
        self.fade_in_duration = random.uniform(p_min_fade, p_max_fade)
        self.visible_duration = random.uniform(p_min_visible, p_max_visible)
        self.fade_out_duration = random.uniform(p_min_fade, p_max_fade) 
        self.state = "fading_in"  # Initial state
        self.timer = 0.0

    def update(self, dt):
        """Update the image's state (fade in, visible, fade out). Returns False when it should be removed."""
        if self.surface is None: return False
        self.timer += dt
        
        # State machine for the image's lifecycle.
        if self.state == "fading_in":
            # Calculate alpha based on time elapsed during fade-in.
            self.alpha = min(self.max_alpha, (self.timer / self.fade_in_duration) * self.max_alpha) if self.fade_in_duration > 0 else self.max_alpha
            if self.timer >= self.fade_in_duration:
                # Transition to the next state.
                self.alpha = self.max_alpha; self.state = "visible"; self.timer = 0.0
        elif self.state == "visible":
            if self.timer >= self.visible_duration:
                # Transition to fading out.
                self.state = "fading_out"; self.timer = 0.0
        elif self.state == "fading_out":
            # Calculate alpha based on time elapsed during fade-out.
            self.alpha = max(0, self.max_alpha - (self.timer / self.fade_out_duration) * self.max_alpha) if self.fade_out_duration > 0 else 0
            if self.timer >= self.fade_out_duration or self.alpha <= 0:
                # Signal that this image is finished and can be deleted.
                return False
                
        # Apply the calculated alpha to the surface.
        self.surface.set_alpha(int(self.alpha))
        return True # The image is still active.

    def draw(self, screen):
        """Draw the image onto the main screen."""
        if self.surface:
            screen.blit(self.surface, self.rect)

# --- Pygame Visualization Main Function ---
def run_pygame_visualization(selected_image_dirs, screen_width, screen_height,
                             p_fps, p_color_change_speed,
                             p_min_fade, p_max_fade, p_min_visible, p_max_visible,
                             p_min_spawn, p_max_spawn, p_scale_images,
                             p_max_img_w_p, p_max_img_h_p, p_max_imgs_screen,
                             audio_file_path=None, play_audio=False,
                             record_video=False, record_duration=0, record_filename="",
                             use_audio_duration=False):
    
    # Initialize Pygame and its mixer if not already done.
    if not pygame.get_init(): pygame.init()
    if play_audio or (record_video and audio_file_path):
        pygame.mixer.init()

    print("PYGAME: Starting visualization with current settings...")
    try:
        # Set up a hardware-accelerated, double-buffered fullscreen display.
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

    # --- Setup for background gradient ---
    current_top_color, target_top_color = get_random_color(), get_random_color()
    current_bottom_color, target_bottom_color = get_random_color(), get_random_color()
    color_lerp_factor = 0.0

    # --- Setup for image management ---
    all_image_paths = load_image_paths_from_selected_dirs(selected_image_dirs)
    if not all_image_paths:
        messagebox.showwarning("No Images", "No images found in the selected directories. Returning to GUI.")
        pygame.mouse.set_visible(True)
        if play_audio and pygame.mixer.get_init(): pygame.mixer.music.stop(); pygame.mixer.quit()
        if pygame.get_init(): pygame.quit()
        return

    available_image_paths = []
    def replenish_image_paths():
        """Reshuffles and repopulates the list of available images to show."""
        nonlocal available_image_paths
        if not all_image_paths: return
        available_image_paths = all_image_paths[:] 
        random.shuffle(available_image_paths)
    replenish_image_paths()
    active_images = []
    next_image_spawn_time = time.time() + random.uniform(p_min_spawn, p_max_spawn)
    
    # --- Setup for Recording ---
    frames_for_video = []
    recording_active_this_session = False
    
    # If using audio duration, calculate it now.
    if record_video and use_audio_duration and audio_file_path and MOVIEPY_AVAILABLE:
        try:
            with AudioFileClip(audio_file_path) as audio_clip:
                record_duration = audio_clip.duration
            print(f"PYGAME: Setting recording duration to audio length: {record_duration:.2f}s")
        except Exception as e:
            print(f"PYGAME Error: Could not determine audio duration: {e}")
            messagebox.showerror("Audio Duration Error", f"Could not determine duration of audio file:\n{audio_file_path}\n{e}\n\nUsing specified duration instead.", parent=None)
            # Fallback to the duration specified in the GUI.

    if record_video and MOVIEPY_AVAILABLE and record_filename and record_duration > 0:
        recording_active_this_session = True
        print(f"PYGAME: Recording to '{record_filename}' for {record_duration}s at {p_fps} FPS.")

    # --- Setup for Audio Playback ---
    if play_audio and audio_file_path:
        try:
            pygame.mixer.music.load(audio_file_path)
            pygame.mixer.music.play(-1) # Loop indefinitely
            print(f"PYGAME: Playing audio: {audio_file_path}")
        except pygame.error as e:
            print(f"PYGAME Error playing audio {audio_file_path}: {e}")

    # --- Main Visualization Loop ---
    running = True
    print("PYGAME: Visualization running. Press any key or mouse button to return to GUI.")

    while running:
        # dt is the time in seconds since the last frame. Essential for smooth, framerate-independent animation.
        dt = clock.tick(p_fps) / 1000.0
        current_time = time.time()

        # Event handling (to exit the loop).
        for event in pygame.event.get():
            if event.type == pygame.QUIT or event.type == pygame.KEYDOWN or event.type == pygame.MOUSEBUTTONDOWN:
                running = False
        if not running: break

        # --- FIX FOR RECORDING SPEED ---
        # The primary exit condition when recording is reaching the target number of frames.
        # This ensures the final video is the correct length, regardless of live performance.
        if recording_active_this_session:
            total_frames_needed = int(record_duration * p_fps)
            if len(frames_for_video) >= total_frames_needed:
                print(f"PYGAME: Recording duration ({record_duration}s) reached with {len(frames_for_video)} frames.")
                running = False
                break # Exit the loop to compile the video.

        # --- Background Color Update ---
        color_lerp_factor += p_color_change_speed * dt
        if color_lerp_factor >= 1.0:
            color_lerp_factor = 0.0
            # Cycle to the next target color.
            current_top_color, target_top_color = target_top_color, get_random_color()
            current_bottom_color, target_bottom_color = target_bottom_color, get_random_color()

        # Calculate the intermediate colors for the gradient for this frame.
        display_top_color = interpolate_color(current_top_color, target_top_color, color_lerp_factor)
        display_bottom_color = interpolate_color(current_bottom_color, target_bottom_color, color_lerp_factor)

        # --- Image Spawning Logic ---
        if len(active_images) < p_max_imgs_screen and current_time >= next_image_spawn_time:
            if not available_image_paths: replenish_image_paths()
            if available_image_paths:
                img_path = available_image_paths.pop(0)
                new_image = FadingImage(img_path, screen_width, screen_height,
                                        p_scale_images, p_max_img_w_p, p_max_img_h_p,
                                        p_min_fade, p_max_fade, p_min_visible, p_max_visible)
                if new_image.surface: active_images.append(new_image)
            next_image_spawn_time = current_time + random.uniform(p_min_spawn, p_max_spawn)

        # Update all active images and remove any that have finished their lifecycle.
        active_images[:] = [img for img in active_images if img.update(dt)]

        # --- Drawing Everything ---
        # 1. Draw the background gradient line by line.
        for y_coord in range(screen_height):
            row_factor = y_coord / screen_height
            color = interpolate_color(display_top_color, display_bottom_color, row_factor)
            pygame.draw.line(screen, color, (0, y_coord), (screen_width, y_coord))
            
        # 2. Draw all active images on top of the background.
        for img in active_images: img.draw(screen)
        
        # 3. Capture the final screen as a frame for the video if recording.
        if recording_active_this_session:
            # We need to convert the Pygame surface to a numpy array that moviepy can understand.
            # The transpose is necessary because Pygame and numpy have different coordinate systems (x,y vs row,col).
            frame = pygame.surfarray.array3d(screen)
            frame = np.transpose(frame, (1, 0, 2))
            frames_for_video.append(frame.copy())

        # 4. Update the display to show the newly drawn frame.
        pygame.display.flip()

    # --- End of Visualization Loop ---
    print("PYGAME: Visualization ended. Cleaning up...")
    
    # Stop audio and quit the mixer.
    if play_audio and pygame.mixer.get_init():
        try:
            pygame.mixer.music.stop()
            print("PYGAME: Audio stopped.")
        except pygame.error as e:
            print(f"PYGAME Error stopping audio: {e}")
    if pygame.mixer.get_init():
         pygame.mixer.quit()

    # --- Video Compilation ---
    # If recording was active and we have frames, build the MP4.
    if recording_active_this_session and frames_for_video:
        print(f"PYGAME: Compiling video from {len(frames_for_video)} frames... This may take a moment.")
        try:
            # Create the video clip from the captured frames.
            video_clip = ImageSequenceClip(frames_for_video, fps=p_fps)
            
            final_clip = video_clip
            # If an audio file was used, attach it to the video.
            if audio_file_path:
                try:
                    with AudioFileClip(audio_file_path) as audio_clip:
                        # Set the audio duration to match the video's duration to avoid errors.
                        final_clip = video_clip.set_audio(audio_clip.set_duration(video_clip.duration))
                    print(f"PYGAME: Audio '{os.path.basename(audio_file_path)}' will be muxed into video.")
                except Exception as e_audio_mux:
                    print(f"PYGAME Error: Could not load or attach audio to video: {e_audio_mux}")
                    messagebox.showwarning("Video Audio Error", f"Could not add audio to video:\n{e_audio_mux}\n\nVideo will be saved without audio.", parent=None)
            
            # Write the final video file to disk.
            final_clip.write_videofile(record_filename, codec="libx264", audio_codec="aac", 
                                       threads=4, preset="medium", logger='bar') # logger='bar' gives a progress bar.
            print(f"PYGAME: Video saved as {record_filename}")
            messagebox.showinfo("Recording Complete", f"Video saved successfully as:\n{record_filename}", parent=None)
        except Exception as e:
            print(f"PYGAME Error saving video: {e}")
            messagebox.showerror("Video Export Error", f"Could not save video:\n{e}\n\nMake sure FFMPEG is installed and in your PATH.", parent=None)
    
    # Final cleanup before returning to the GUI.
    pygame.mouse.set_visible(True)
    if pygame.get_init(): pygame.quit()

# --- Tkinter GUI Class ---
class DirectorySelectorGUI:
    def __init__(self, master, system_screen_w, system_screen_h):
        self.master = master
        self.system_screen_w = system_screen_w
        self.system_screen_h = system_screen_h
        
        # Configure the main window to be maximized by default.
        self.master.resizable(True, True)
        try:
            # 'zoomed' works on Windows/Linux to maximize.
            self.master.state('zoomed')
        except tk.TclError:
             # Fallback for other systems like macOS.
             self.master.attributes('-fullscreen', False)
             self.master.geometry(f"{int(system_screen_w*0.9)}x{int(system_screen_h*0.85)}")

        self.master.title("Greg Seymour - AI Visualization Tool v2.0")
        
        self.directories_data = []
        self._init_style()
        self._init_vars()
        self._define_presets()
        self._define_help_texts()
        self._build_ui()
        self._load_configuration()
        # Ensure configuration is saved when the user closes the window with the 'X' button.
        self.master.protocol("WM_DELETE_WINDOW", self._on_quit)
        # After the UI is built, check if the current settings match a preset.
        self.master.after(100, self._check_vars_for_custom_preset)

    def _init_style(self):
        """Initializes the visual style for all Tkinter widgets (Nord theme)."""
        self.style = ttk.Style()
        self.style.theme_use('clam')

        # Color palette
        self.bg_color = "#2E3440"
        self.fg_color = "#E5E9F0"
        self.frame_bg = "#3B4252"
        self.accent_color_1 = "#88C0D0" # Blue
        self.accent_color_2 = "#BF616A" # Red
        self.button_color = "#5E81AC"
        self.entry_bg = "#4C566A"

        # Configure styles for different widget types
        self.style.configure('.', background=self.bg_color, foreground=self.fg_color, font=('Segoe UI', 10))
        self.style.configure('TFrame', background=self.frame_bg)
        self.style.configure('TLabel', background=self.frame_bg, foreground=self.fg_color, padding=5)
        self.style.configure('TLabelframe', background=self.frame_bg, bordercolor=self.accent_color_1)
        self.style.configure('TLabelframe.Label', background=self.frame_bg, foreground=self.accent_color_1, font=('Segoe UI Semibold', 12))
        
        self.style.configure('TButton', background=self.button_color, foreground='white',
                             font=('Segoe UI Semibold', 10), padding=6, borderwidth=0)
        self.style.map('TButton',
                       background=[('active', self.accent_color_1), ('pressed', self.accent_color_1)])
        
        self.style.configure('Accent.TButton', background=self.accent_color_2, foreground='white',
                             font=('Segoe UI Bold', 12), padding=8)
        self.style.map('Accent.TButton', background=[('active', '#D08770'), ('pressed', '#D08770')])

        self.style.configure('Info.TButton', background=self.frame_bg, foreground=self.accent_color_1,
                             font=('Segoe UI', 8, 'bold'), padding=(1,0), borderwidth=0)
        self.style.map('Info.TButton', foreground=[('active', self.fg_color)])

        self.style.configure('TCheckbutton', background=self.frame_bg, foreground=self.fg_color)
        self.style.map('TCheckbutton', indicatorcolor=[('selected', self.accent_color_1), ('active', self.accent_color_1), ('!selected', self.entry_bg)])
        
        self.style.configure('TEntry', fieldbackground=self.entry_bg, foreground=self.fg_color, insertcolor=self.fg_color, borderwidth=1, relief=tk.FLAT)
        self.style.configure('TSpinbox', fieldbackground=self.entry_bg, foreground=self.fg_color, arrowcolor=self.fg_color,
                             arrowbackground=self.button_color, borderwidth=1, relief=tk.FLAT)
        
        self.style.configure('Vertical.TScrollbar', background=self.button_color, troughcolor=self.frame_bg, arrowcolor=self.fg_color)
        
        # Custom Fonts
        self.title_font = tkFont.Font(family="Impact", size=28, weight="bold")

    def _init_vars(self):
        """Initializes all Tkinter control variables and maps them for saving/loading."""
        # --- Visualization Variables ---
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
        
        # --- Audio & Recording Variables ---
        self.play_audio_var = tk.BooleanVar(value=False)
        self.audio_file_path_var = tk.StringVar(value="")
        self.record_video_var = tk.BooleanVar(value=False)
        self.record_filename_var = tk.StringVar(value="visualization_output.mp4")
        self.record_duration_var = tk.IntVar(value=30)
        self.use_audio_duration_var = tk.BooleanVar(value=False)

        # --- FIX FOR CONFIG SAVING ---
        # This dictionary maps a string key to each variable.
        # It's the "master list" of what gets saved to and loaded from the JSON config file.
        # ALL variables that need to be persistent are included here.
        self.setting_vars_map = {
            "scale_images": self.scale_images_var, "max_img_w_p": self.max_img_w_p_var,
            "max_img_h_p": self.max_img_h_p_var, "min_fade": self.min_fade_var,
            "max_fade": self.max_fade_var, "min_visible": self.min_visible_var,
            "max_visible": self.max_visible_var, "min_spawn": self.min_spawn_var,
            "max_spawn": self.max_spawn_var, "max_imgs_screen": self.max_imgs_screen_var,
            "fps": self.fps_var, "color_speed": self.color_speed_var,
            "play_audio": self.play_audio_var,
            "audio_file_path": self.audio_file_path_var,
            "record_video": self.record_video_var,
            "record_filename": self.record_filename_var,
            "record_duration": self.record_duration_var,
            "use_audio_duration": self.use_audio_duration_var
        }

        # --- Tracing ---
        # A "trace" is a callback that runs whenever a variable's value changes.
        # This loop sets up a trace for EVERY variable in our map.
        for var_name, var_obj in self.setting_vars_map.items():
            var_obj.trace_add("write", lambda *args, vn=var_name, vo=var_obj: self._on_setting_var_changed(vn, vo))
        
        # We also need specific traces for updating the GUI state (e.g., disabling fields).
        self.record_video_var.trace_add("write", lambda *a: self._toggle_recording_fields_state())
        self.use_audio_duration_var.trace_add("write", lambda *a: self._toggle_recording_fields_state())
        self.audio_file_path_var.trace_add("write", lambda *a: self._toggle_recording_fields_state())

    def _on_setting_var_changed(self, var_name, var_obj):
        """This function is called any time a traced variable is modified."""
        self._save_configuration()
        self._check_vars_for_custom_preset()

    def _define_presets(self):
        """Defines all available presets. More can be easily added here."""
        self.presets = {
            "Custom": {}, # A placeholder for when settings don't match a preset.
            "Default": {
                "scale_images": True, "max_img_w_p": 0.75, "max_img_h_p": 0.75,
                "min_fade": 1.0, "max_fade": 2.0, "min_visible": 0.3, "max_visible": 1.5,
                "min_spawn": 0.5, "max_spawn": 1.0, "max_imgs_screen": 10, "fps": 30, "color_speed": 0.3
            },
            "Fast & Dynamic": {
                "scale_images": True, "max_img_w_p": 0.6, "max_img_h_p": 0.6,
                "min_fade": 0.3, "max_fade": 0.7, "min_visible": 0.2, "max_visible": 0.8,
                "min_spawn": 0.1, "max_spawn": 0.3, "max_imgs_screen": 15, "fps": 60, "color_speed": 0.8
            },
            "Slow & Gentle": {
                "scale_images": True, "max_img_w_p": 0.8, "max_img_h_p": 0.8,
                "min_fade": 2.0, "max_fade": 4.0, "min_visible": 3.0, "max_visible": 6.0,
                "min_spawn": 1.5, "max_spawn": 3.0, "max_imgs_screen": 5, "fps": 30, "color_speed": 0.1
            },
            "Image Showcase": {
                "scale_images": True, "max_img_w_p": 0.9, "max_img_h_p": 0.9,
                "min_fade": 2.5, "max_fade": 3.5, "min_visible": 5.0, "max_visible": 10.0,
                "min_spawn": 3.0, "max_spawn": 5.0, "max_imgs_screen": 3, "fps": 30, "color_speed": 0.05
            },
            "Chaotic": {
                "scale_images": True, "max_img_w_p": 0.3, "max_img_h_p": 0.3,
                "min_fade": 0.1, "max_fade": 0.2, "min_visible": 0.1, "max_visible": 0.3,
                "min_spawn": 0.05, "max_spawn": 0.1, "max_imgs_screen": 20, "fps": 60, "color_speed": 1.0
            },
            # --- 12 NEW PRESETS ---
            "Serene": {
                "scale_images": True, "max_img_w_p": 0.9, "max_img_h_p": 0.9,
                "min_fade": 3.0, "max_fade": 5.0, "min_visible": 10.0, "max_visible": 15.0,
                "min_spawn": 5.0, "max_spawn": 10.0, "max_imgs_screen": 2, "fps": 30, "color_speed": 0.05
            },
            "Minimalist": {
                "scale_images": True, "max_img_w_p": 0.8, "max_img_h_p": 0.8,
                "min_fade": 2.0, "max_fade": 3.0, "min_visible": 4.0, "max_visible": 6.0,
                "min_spawn": 2.0, "max_spawn": 4.0, "max_imgs_screen": 4, "fps": 30, "color_speed": 0.2
            },
            "Crowded": {
                "scale_images": True, "max_img_w_p": 0.2, "max_img_h_p": 0.2,
                "min_fade": 0.5, "max_fade": 1.0, "min_visible": 0.5, "max_visible": 1.5,
                "min_spawn": 0.2, "max_spawn": 0.5, "max_imgs_screen": 25, "fps": 60, "color_speed": 0.7
            },
            "Flashy": {
                "scale_images": True, "max_img_w_p": 0.5, "max_img_h_p": 0.5,
                "min_fade": 0.2, "max_fade": 0.5, "min_visible": 0.3, "max_visible": 0.7,
                "min_spawn": 0.1, "max_spawn": 0.3, "max_imgs_screen": 15, "fps": 60, "color_speed": 1.5
            },
            "Slideshow": {
                "scale_images": True, "max_img_w_p": 1.0, "max_img_h_p": 1.0,
                "min_fade": 1.0, "max_fade": 2.0, "min_visible": 5.0, "max_visible": 8.0,
                "min_spawn": 6.0, "max_spawn": 10.0, "max_imgs_screen": 1, "fps": 30, "color_speed": 0.1
            },
            "Ethereal": {
                "scale_images": True, "max_img_w_p": 0.7, "max_img_h_p": 0.7,
                "min_fade": 5.0, "max_fade": 8.0, "min_visible": 2.0, "max_visible": 4.0,
                "min_spawn": 3.0, "max_spawn": 5.0, "max_imgs_screen": 6, "fps": 30, "color_speed": 0.15
            },
            "Rapid Fire": {
                "scale_images": True, "max_img_w_p": 0.4, "max_img_h_p": 0.4,
                "min_fade": 0.1, "max_fade": 0.3, "min_visible": 0.1, "max_visible": 0.5,
                "min_spawn": 0.0, "max_spawn": 0.1, "max_imgs_screen": 20, "fps": 60, "color_speed": 1.2
            },
            "Spotlight": {
                "scale_images": True, "max_img_w_p": 0.85, "max_img_h_p": 0.85,
                "min_fade": 1.5, "max_fade": 1.5, "min_visible": 4.0, "max_visible": 4.0,
                "min_spawn": 5.6, "max_spawn": 5.6, "max_imgs_screen": 1, "fps": 30, "color_speed": 0.2
            },
            "Dreamlike": {
                "scale_images": True, "max_img_w_p": 0.8, "max_img_h_p": 0.8,
                "min_fade": 4.0, "max_fade": 6.0, "min_visible": 1.0, "max_visible": 3.0,
                "min_spawn": 1.0, "max_spawn": 2.0, "max_imgs_screen": 8, "fps": 30, "color_speed": 0.25
            },
            "Digital Storm": {
                "scale_images": True, "max_img_w_p": 0.5, "max_img_h_p": 0.5,
                "min_fade": 0.05, "max_fade": 0.2, "min_visible": 0.05, "max_visible": 0.2,
                "min_spawn": 0.0, "max_spawn": 0.05, "max_imgs_screen": 30, "fps": 60, "color_speed": 2.0
            },
            "Cinematic": {
                "scale_images": True, "max_img_w_p": 0.95, "max_img_h_p": 0.95,
                "min_fade": 2.5, "max_fade": 3.0, "min_visible": 6.0, "max_visible": 9.0,
                "min_spawn": 8.0, "max_spawn": 12.0, "max_imgs_screen": 2, "fps": 24, "color_speed": 0.08
            },
            "Pop-Up Book": {
                "scale_images": True, "max_img_w_p": 0.6, "max_img_h_p": 0.6,
                "min_fade": 0.2, "max_fade": 0.2, "min_visible": 2.0, "max_visible": 4.0,
                "min_spawn": 1.0, "max_spawn": 2.0, "max_imgs_screen": 7, "fps": 30, "color_speed": 0.5
            }
        }
        self.current_preset_var = tk.StringVar(value="Default")

    def _apply_preset(self, event=None):
        """Applies the selected preset's values to all the control variables."""
        preset_name = self.current_preset_var.get()
        if preset_name == "Custom":
            return
            
        preset_settings = self.presets.get(preset_name)
        if preset_settings:
            # We temporarily disable traces while setting values to prevent
            # a storm of events and unnecessary file writes.
            self._pause_var_traces = True
            for key, value in preset_settings.items():
                # Only apply settings that are part of the visualization, not audio/video.
                if key in self.setting_vars_map and key not in ["play_audio", "audio_file_path", "record_video", "record_filename", "record_duration", "use_audio_duration"]:
                    self.setting_vars_map[key].set(value)
            self._pause_var_traces = False
            print(f"GUI: Applied preset '{preset_name}'")
        # Save the new configuration after applying the preset.
        self._save_configuration()

    def _check_vars_for_custom_preset(self, *args):
        """Checks if the current settings match any preset; if not, sets the dropdown to 'Custom'."""
        if hasattr(self, '_pause_var_traces') and self._pause_var_traces:
            return

        # Get a dictionary of the current visualization settings.
        current_settings = {
            name: var.get() for name, var in self.setting_vars_map.items() 
            if name not in ["play_audio", "audio_file_path", "record_video", "record_filename", "record_duration", "use_audio_duration"]
        }
        
        matched_preset = None
        for preset_name, preset_values in self.presets.items():
            if preset_name == "Custom": continue 
            
            # Compare current settings to each preset's values.
            is_match = True
            for key, p_val in preset_values.items():
                curr_val = current_settings.get(key)
                if isinstance(p_val, float):
                    # Use a tolerance for floating point comparison.
                    if abs(curr_val - p_val) > 1e-5:
                        is_match = False
                        break
                elif curr_val != p_val:
                    is_match = False
                    break
            if is_match and len(preset_values) == len(current_settings):
                 matched_preset = preset_name
                 break
        
        # Update the combobox to reflect the match or lack thereof.
        if matched_preset:
            if self.current_preset_var.get() != matched_preset:
                self.current_preset_var.set(matched_preset)
        else:
            if self.current_preset_var.get() != "Custom":
                self.current_preset_var.set("Custom")

    def _define_help_texts(self):
        """Defines the help text for the '(i)' info buttons."""
        self.help_texts = {
            "scale_images": "Enable Image Scaling: If checked, images larger than the 'Max Image Width/Height Percent' will be scaled down to fit.",
            "max_img_w_p": "Max Image Width (% screen): Maximum width an image can take up as a percentage of the screen width.",
            "max_img_h_p": "Max Image Height (% screen): Maximum height an image can take up as a percentage of the screen height.",
            "min_fade": "Min Fade Time (s): The shortest possible duration for an image to fade in or out.",
            "max_fade": "Max Fade Time (s): The longest possible duration for an image to fade in or out.",
            "min_visible": "Min Visible Time (s): The minimum time an image stays fully visible after fading in.",
            "max_visible": "Max Visible Time (s): The maximum time an image stays fully visible after fading in.",
            "min_spawn": "Min Spawn Delay (s): The shortest possible delay before a new image appears on screen.",
            "max_spawn": "Max Spawn Delay (s): The longest possible delay before a new image appears on screen.",
            "max_imgs_screen": "Max Images on Screen: The maximum number of images that can be on screen at the same time.",
            "fps": "Target FPS: Frames Per Second for the animation and for video recording. Higher values are smoother but more demanding.",
            "color_speed": "BG Color Speed: How quickly the background gradient colors transition. Higher is faster.",
            "load_preset": "Load Preset: Select from a list of pre-configured settings for different visual styles.",
            "play_audio": "Play Audio: If checked, the selected audio file will play on a loop during the visualization.",
            "select_audio": "Select Audio File: Choose an MP3, WAV, or OGG file to play.",
            "record_video": "Record to MP4: If checked, the visualization will be recorded to an MP4 video file. Requires 'moviepy' and 'FFMPEG'.",
            "output_filename": "Output Filename: The name and location for the saved MP4 video.",
            "record_duration": "Recording Duration (s): The length of the video to record in seconds.",
            "use_audio_duration": "Use Audio Duration: If checked, the recording duration will automatically be set to the length of the selected audio file."
        }

    def _show_help_info(self, setting_key):
        """Shows a popup messagebox with help text."""
        messagebox.showinfo(f"Info: {setting_key.replace('_', ' ').title()}", self.help_texts.get(setting_key, "No information available."), parent=self.master)

    def _get_config_path(self):
        """Returns the full path to the configuration file."""
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), CONFIG_FILE_NAME)

    def _load_configuration(self):
        """Loads all settings and directories from the JSON config file."""
        config_path = self._get_config_path()
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    config_data = json.load(f)
                print(f"GUI: Configuration loaded from {config_path}")
            else:
                print(f"GUI: No configuration file found. Using defaults.")
                self.current_preset_var.set("Default")
                self._apply_preset()
                return

        except Exception as e:
            print(f"GUI Error loading configuration: {e}. Using defaults.")
            messagebox.showerror("Config Error", f"Could not load configuration file:\n{e}\n\nLoading default settings.", parent=self.master)
            self.current_preset_var.set("Default")
            self._apply_preset()
            return
        
        # Load directories
        loaded_dirs = config_data.get("directories", [])
        self.directories_data = []
        for item in loaded_dirs:
            path, enabled = item.get("path"), item.get("enabled", True)
            if path and os.path.isdir(path):
                enabled_var = tk.BooleanVar(value=enabled)
                enabled_var.trace_add("write", lambda *args, p=path: self._save_configuration())
                self.directories_data.append({'path': path, 'enabled_var': enabled_var})
            elif path: print(f"GUI Warning: Saved directory not found: {path}")
        
        # Load settings
        settings = config_data.get("settings", {})
        self._pause_var_traces = True
        # Loop through our master list of variables and set their values from the loaded data.
        for key, var_obj in self.setting_vars_map.items():
            if key in settings:
                try:
                    var_obj.set(settings[key])
                except (tk.TclError, TypeError) as e:
                    print(f"GUI Warning: Could not set '{key}' from config value '{settings[key]}'. Error: {e}")
        self._pause_var_traces = False
        
        self._populate_dir_list_ui()
        self._check_vars_for_custom_preset()
        self._toggle_recording_fields_state() # Ensure GUI state is correct after loading.

    def _save_configuration(self):
        """Saves all current settings and directories to the JSON config file."""
        if hasattr(self, '_pause_var_traces') and self._pause_var_traces:
            return

        config_path = self._get_config_path()
        dirs_to_save = [{'path': item['path'], 'enabled': item['enabled_var'].get()} for item in self.directories_data]
        
        # Get the current value of every variable in our master list.
        settings_to_save = {name: var.get() for name, var in self.setting_vars_map.items()}
        
        config_to_save = {
            "directories": dirs_to_save,
            "settings": settings_to_save
        }

        try:
            with open(config_path, 'w') as f:
                json.dump(config_to_save, f, indent=4)
        except Exception as e:
            print(f"GUI Error saving configuration: {e}")

    def _build_ui(self):
        """Constructs the entire Tkinter user interface."""
        # This function is long, but it's mostly boilerplate for creating and placing widgets.
        # Main layout
        self.master.configure(background=self.bg_color)
        main_frame = ttk.Frame(self.master, style='TFrame', padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True)
        main_frame.columnconfigure(0, weight=3) # Left panel (dirs)
        main_frame.columnconfigure(1, weight=4) # Right panel (settings)
        main_frame.rowconfigure(1, weight=1)    # Panels should expand vertically

        # Title
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

        # A Canvas with a Scrollbar is the standard way to make a scrollable frame in Tkinter.
        self.canvas = tk.Canvas(list_container, borderwidth=0, background=self.frame_bg, highlightthickness=0)
        self.dir_list_frame = ttk.Frame(self.canvas, style='TFrame') # The frame that will hold the list items.
        self.scrollbar = ttk.Scrollbar(list_container, orient="vertical", command=self.canvas.yview, style='Vertical.TScrollbar')
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.scrollbar.grid(row=0, column=1, sticky="ns")
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.canvas_window = self.canvas.create_window((0, 0), window=self.dir_list_frame, anchor="nw")
        
        # Bind events for scrolling and resizing.
        self.dir_list_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind('<Configure>', lambda e: self.canvas.itemconfig(self.canvas_window, width=e.width))
        self.master.bind_all("<MouseWheel>", lambda e: self.canvas.yview_scroll(int(-1*(e.delta/120)), "units"), add="+")

        # --- Right Panel: Settings (also in a scrollable canvas) ---
        settings_scroll_canvas = tk.Canvas(main_frame, borderwidth=0, background=self.frame_bg, highlightthickness=0)
        settings_scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=settings_scroll_canvas.yview, style='Vertical.TScrollbar')
        settings_scroll_canvas.configure(yscrollcommand=settings_scrollbar.set)
        
        settings_scroll_canvas.grid(row=1, column=1, sticky="nsew", padx=(10,0))
        settings_scrollbar.grid(row=1, column=2, sticky="ns")

        self.settings_panel_content = ttk.LabelFrame(settings_scroll_canvas, text="Visualization Settings", style='TLabelframe')
        settings_scroll_canvas.create_window((0,0), window=self.settings_panel_content, anchor="nw", tags="settings_frame")
        self.settings_panel_content.bind("<Configure>", lambda e: settings_scroll_canvas.configure(scrollregion=settings_scroll_canvas.bbox("all")))
        
        # --- Populate the Settings Panel ---
        spc = self.settings_panel_content
        spc.columnconfigure(1, weight=1)
        row_idx = 0
        
        # Helper function to reduce boilerplate when adding a setting control.
        def add_setting_control(label_text, var, setting_key, from_=0, to=1, resolution=0.01, is_scale=True, is_bool=False, precision=2):
            nonlocal row_idx
            # Frame for Label + Info Button
            label_frame = ttk.Frame(spc, style='TFrame')
            label_frame.grid(row=row_idx, column=0, sticky="w", padx=5, pady=3)
            ttk.Label(label_frame, text=label_text, style='TLabel').pack(side=tk.LEFT)
            ttk.Button(label_frame, text="(i)", style='Info.TButton', width=3,
                       command=lambda sk=setting_key: self._show_help_info(sk)).pack(side=tk.LEFT, padx=(2,0))

            if is_bool:
                ttk.Checkbutton(spc, variable=var, style='TCheckbutton').grid(row=row_idx, column=1, columnspan=2, sticky="w", padx=5, pady=3)
            elif is_scale:
                # This setup links a Scale (slider) and an Entry (text box) to the same variable.
                control_frame = ttk.Frame(spc, style='TFrame')
                control_frame.grid(row=row_idx, column=1, columnspan=2, sticky="ew", padx=5, pady=3)
                control_frame.columnconfigure(0, weight=3) # Slider takes up more space
                control_frame.columnconfigure(1, weight=1) # Entry is smaller

                scale = ttk.Scale(control_frame, variable=var, from_=from_, to=to, orient=tk.HORIZONTAL)
                scale.grid(row=0, column=0, sticky="ew", padx=(0,5))
                entry = ttk.Entry(control_frame, textvariable=var, width=6, style='TEntry')
                entry.grid(row=0, column=1, sticky="e")
            else: # is Spinbox
                spin = ttk.Spinbox(spc, textvariable=var, from_=from_, to=to, increment=resolution, wrap=False, style='TSpinbox', width=8)
                spin.grid(row=row_idx, column=1, sticky="w", padx=5, pady=3)
            row_idx += 1
            return row_idx

        # Presets Dropdown
        preset_frame = ttk.Frame(spc, style='TFrame')
        preset_frame.grid(row=row_idx, column=0, columnspan=3, sticky="ew", pady=(10,5), padx=5)
        ttk.Label(preset_frame, text="Load Preset:", style='TLabel').pack(side=tk.LEFT, padx=(0,2))
        self.preset_combo = ttk.Combobox(preset_frame, textvariable=self.current_preset_var,
                                         values=list(self.presets.keys()), state="readonly", width=20)
        self.preset_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0,5))
        self.preset_combo.bind("<<ComboboxSelected>>", self._apply_preset)
        row_idx += 1

        # Add all the setting controls
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

        ttk.Separator(spc, orient=tk.HORIZONTAL).grid(row=row_idx, column=0, columnspan=3, sticky="ew", pady=10); row_idx+=1

        # Audio Controls
        add_setting_control("Play Audio:", self.play_audio_var, "play_audio", is_bool=True)
        rec_file_frame = ttk.Frame(spc, style='TFrame'); rec_file_frame.grid(row=row_idx, column=0, sticky="w", padx=5, pady=3)
        ttk.Button(rec_file_frame, text="Select Audio File:", command=self._select_audio_file).pack(side=tk.LEFT)
        ttk.Button(rec_file_frame, text="(i)", style='Info.TButton', width=3, command=lambda: self._show_help_info("select_audio")).pack(side=tk.LEFT, padx=(2,0))
        self.audio_file_label = ttk.Label(spc, textvariable=self.audio_file_path_var, style='TLabel', relief="sunken", anchor='w', wraplength=250)
        self.audio_file_label.grid(row=row_idx, column=1, columnspan=2, sticky="ew", padx=5, pady=3); row_idx+=1

        ttk.Separator(spc, orient=tk.HORIZONTAL).grid(row=row_idx, column=0, columnspan=3, sticky="ew", pady=10); row_idx+=1

        # Recording Controls
        add_setting_control("Record to MP4:", self.record_video_var, "record_video", is_bool=True)
        
        rec_file_frame = ttk.Frame(spc, style='TFrame'); rec_file_frame.grid(row=row_idx, column=0, sticky="w", padx=5, pady=3)
        self.rec_browse_button = ttk.Button(rec_file_frame, text="Output Filename:", command=self._select_record_filename)
        self.rec_browse_button.pack(side=tk.LEFT)
        ttk.Button(rec_file_frame, text="(i)", style='Info.TButton', width=3, command=lambda: self._show_help_info("output_filename")).pack(side=tk.LEFT, padx=(2,0))
        self.record_filename_entry = ttk.Entry(spc, textvariable=self.record_filename_var, style='TEntry')
        self.record_filename_entry.grid(row=row_idx, column=1, columnspan=2, sticky="ew", padx=5, pady=3); row_idx+=1

        rec_dur_frame = ttk.Frame(spc, style='TFrame'); rec_dur_frame.grid(row=row_idx, column=0, sticky="w", padx=5, pady=3)
        ttk.Label(rec_dur_frame, text="Rec. Duration (s):", style='TLabel').pack(side=tk.LEFT)
        ttk.Button(rec_dur_frame, text="(i)", style='Info.TButton', width=3, command=lambda: self._show_help_info("record_duration")).pack(side=tk.LEFT, padx=(2,0))
        self.record_duration_spinbox = ttk.Spinbox(spc, textvariable=self.record_duration_var, from_=1, to=3600, increment=1, wrap=False, style='TSpinbox', width=8)
        self.record_duration_spinbox.grid(row=row_idx, column=1, sticky="w", padx=5, pady=3); row_idx+=1

        add_setting_control("Use Audio Duration:", self.use_audio_duration_var, "use_audio_duration", is_bool=True)

        self._toggle_recording_fields_state()

        # --- Bottom Buttons ---
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
        """Clears and redraws the list of directories in the left panel."""
        for widget in self.dir_list_frame.winfo_children(): widget.destroy()
        if not self.directories_data:
            ttk.Label(self.dir_list_frame, text="No directories added. Click 'Add Directory'.", style='TLabel', wraplength=self.canvas.winfo_width()-20).pack(pady=10, padx=10, fill=tk.X)
        
        for item_data in self.directories_data:
            path, enabled_var = item_data['path'], item_data['enabled_var']
            entry_frame = ttk.Frame(self.dir_list_frame, style='TFrame')
            entry_frame.pack(fill=tk.X, pady=1, padx=2)
            check = ttk.Checkbutton(entry_frame, variable=enabled_var, style='TCheckbutton')
            check.pack(side=tk.LEFT, padx=(0, 3))
            
            # Truncate long paths for display.
            max_len = 65
            display_path = path if len(path) <= max_len else f"...{path[-(max_len-3):]}"
            label = ttk.Label(entry_frame, text=display_path, anchor="w", style='TLabel')
            label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=3)
            
            remove_btn = ttk.Button(entry_frame, text="X", width=3, style='TButton',
                                   command=lambda p=path: self._remove_dir_entry(p))
            remove_btn.pack(side=tk.RIGHT, padx=(3,0))
        
        # Give Tkinter a moment to process before updating the scroll region.
        self.master.after(50, lambda: self.canvas.configure(scrollregion=self.canvas.bbox("all")))

    def _add_new_directory(self):
        """Opens a dialog to add a new directory to the list."""
        dir_path = filedialog.askdirectory(master=self.master, title="Select Image Directory")
        if dir_path:
            norm_path = os.path.normpath(dir_path)
            if any(item['path'] == norm_path for item in self.directories_data):
                messagebox.showinfo("Duplicate", "This directory is already in the list.", parent=self.master)
                return
            enabled_var = tk.BooleanVar(value=True)
            self.directories_data.append({'path': norm_path, 'enabled_var': enabled_var})
            self._populate_dir_list_ui()
            self._save_configuration() # Save immediately after adding.

    def _remove_dir_entry(self, path_to_remove):
        """Removes a directory from the list."""
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
        filepath = filedialog.askopenfilename(master=self.master, title="Select Audio File",
            filetypes=(("Audio Files", "*.mp3 *.wav *.ogg"), ("All files", "*.*")))
        if filepath: self.audio_file_path_var.set(filepath)

    def _select_record_filename(self):
        filepath = filedialog.asksaveasfilename(master=self.master, title="Save MP4 Video As...",
            defaultextension=".mp4", initialfile=self.record_filename_var.get(),
            filetypes=(("MP4 Video", "*.mp4"), ("All files", "*.*")))
        if filepath: self.record_filename_var.set(get_unique_filename(filepath))

    def _toggle_recording_fields_state(self, *args):
        """Enables or disables the recording-related UI fields based on the main checkbox."""
        # Check if moviepy is available first.
        if not MOVIEPY_AVAILABLE and self.record_video_var.get():
            messagebox.showwarning("MoviePy Missing", 
                                   "The 'moviepy' library is not installed. MP4 recording is disabled.\n"
                                   "Please install it by running: pip install moviepy\n"
                                   "You may also need FFMPEG.", parent=self.master)
            self.record_video_var.set(False)
        
        # Determine the state (NORMAL or DISABLED)
        state = tk.NORMAL if self.record_video_var.get() else tk.DISABLED
        
        # Apply the state to the relevant widgets.
        if hasattr(self, 'rec_browse_button'): self.rec_browse_button.configure(state=state)
        if hasattr(self, 'record_filename_entry'): self.record_filename_entry.configure(state=state)
        
        # The duration spinbox has special logic.
        is_using_audio_duration = self.use_audio_duration_var.get() and self.audio_file_path_var.get() != ""
        if self.record_video_var.get() and is_using_audio_duration:
            self.record_duration_spinbox.configure(state=tk.DISABLED)
        else:
            self.record_duration_spinbox.configure(state=state)

    def _show_general_instructions(self):
        instructions = """Welcome to the AI Visualization Tool!

1. **Add Image Directories:**
    * Click "Add Directory" to select folders containing your images.
    * Use the checkboxes to enable or disable directories for the current session.

2. **Configure Settings:**
    * Use the "Load Preset" dropdown for quick setups (20+ options available!).
    * Fine-tune any setting using the sliders and input fields. Your changes are saved automatically.

3. **Audio & Recording (Optional):**
    * **Play Audio:** Check this and select a file to have music during the visualization.
    * **Record to MP4:** Check this to save the output as a video.
    * **Use Audio Duration:** A handy option to make the video length match your selected song.

4. **Run Visualization:**
    * Click "Run Visualization" to start the fullscreen show.
    * **To exit:** Press any key or click the mouse.

5. **Quit:**
    * Click "Quit Program" or use the window's 'X' button. All your settings will be saved for next time."""
        messagebox.showinfo("Instructions - AI Visualization Tool", instructions, parent=self.master)

    def _on_run_visualization(self):
        """Performs final checks and launches the Pygame visualization."""
        # --- Validation ---
        if self.min_fade_var.get() > self.max_fade_var.get() or \
           self.min_visible_var.get() > self.max_visible_var.get() or \
           self.min_spawn_var.get() > self.max_spawn_var.get():
            messagebox.showerror("Settings Error", "A 'Min' value cannot be greater than its corresponding 'Max' value.", parent=self.master)
            return

        selected_paths = [item['path'] for item in self.directories_data if item['enabled_var'].get()]
        if not selected_paths:
            messagebox.showwarning("No Directories", "Please select at least one enabled image directory.", parent=self.master)
            return

        if self.play_audio_var.get() and not self.audio_file_path_var.get():
            messagebox.showwarning("Audio File Missing", "Play Audio is enabled, but no audio file has been selected.", parent=self.master)
            return
        
        if self.record_video_var.get():
            if not MOVIEPY_AVAILABLE:
                messagebox.showerror("Recording Error", "MoviePy library is not available. Recording is disabled.", parent=self.master)
                return
            if not self.record_filename_var.get():
                messagebox.showerror("Recording Error", "Please specify an output filename for the recording.", parent=self.master)
                return

        # Hide the GUI window while Pygame is running.
        self.master.withdraw()
        # It's good practice to quit a previous Pygame instance if it exists.
        if pygame.get_init(): pygame.quit()

        # Call the main Pygame function with all the settings from the GUI.
        run_pygame_visualization(
            selected_paths, self.system_screen_w, self.system_screen_h,
            p_fps=self.fps_var.get(), p_color_change_speed=self.color_speed_var.get(),
            p_min_fade=self.min_fade_var.get(), p_max_fade=self.max_fade_var.get(),
            p_min_visible=self.min_visible_var.get(), p_max_visible=self.max_visible_var.get(),
            p_min_spawn=self.min_spawn_var.get(), p_max_spawn=self.max_spawn_var.get(),
            p_scale_images=self.scale_images_var.get(),
            p_max_img_w_p=self.max_img_w_p_var.get(), p_max_img_h_p=self.max_img_h_p_var.get(),
            p_max_imgs_screen=self.max_imgs_screen_var.get(),
            audio_file_path=self.audio_file_path_var.get(), # Pass path regardless of checkbox for recording
            play_audio=self.play_audio_var.get(),
            record_video=self.record_video_var.get(),
            record_duration=self.record_duration_var.get(),
            record_filename=self.record_filename_var.get(),
            use_audio_duration=self.use_audio_duration_var.get()
        )
        
        # --- FIX FOR GUI WINDOW STATE ---
        # After Pygame finishes, bring the GUI back.
        if pygame.get_init(): pygame.quit()
        self.master.deiconify() # Un-hide the window
        try:
            # Force the window back to its maximized state.
            self.master.state('zoomed')
        except tk.TclError:
            pass # Ignore if 'zoomed' is not supported
        self.master.lift() # Bring it to the top
        self.master.focus_force() # Give it keyboard focus

    def _on_quit(self):
        """Saves config and properly exits the application."""
        self._save_configuration()
        if pygame.get_init(): pygame.quit()
        self.master.quit()
        self.master.destroy()

# --- Main Application Entry Point ---
if __name__ == '__main__':
    # Show a startup warning if moviepy is missing.
    if not MOVIEPY_AVAILABLE:
        temp_root = tk.Tk(); temp_root.withdraw()
        messagebox.showwarning("Dependency Missing",
                               "The 'moviepy' library was not found. MP4 recording features will be disabled.\n"
                               "To enable recording, install moviepy: pip install moviepy\n"
                               "You might also need FFMPEG in your system's PATH.", parent=None)
        temp_root.destroy()
        
    # Get screen dimensions for both Tkinter and Pygame.
    root_temp = tk.Tk(); root_temp.withdraw()
    tk_screen_width = root_temp.winfo_screenwidth()
    tk_screen_height = root_temp.winfo_screenheight()
    root_temp.destroy()

    try:
        pygame.init()
        info = pygame.display.Info()
        pg_screen_width = info.current_w
        pg_screen_height = info.current_h
        pygame.quit()
    except pygame.error:
        print("Warning: Could not get Pygame screen dimensions. Using Tkinter's as a fallback.")
        pg_screen_width, pg_screen_height = tk_screen_width, tk_screen_height

    # If Pygame fails, provide a sensible default.
    if pg_screen_width == 0 or pg_screen_height == 0:
        pg_screen_width, pg_screen_height = 1024, 768

    # Create the main window, instantiate the GUI class, and run the main loop.
    root = tk.Tk()
    app = DirectorySelectorGUI(root, pg_screen_width, pg_screen_height)
    root.mainloop()
    print("Application has exited.")