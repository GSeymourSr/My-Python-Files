import pygame
import random
import os
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import json

# --- Configuration (Pygame Visualization) ---
FPS = 30  # Frames per second
COLOR_CHANGE_SPEED = 0.3 # Color change speed (lower is slower)
MIN_FADE_TIME = 1.0
MAX_FADE_TIME = 2.0
MIN_VISIBLE_TIME = 0.3
MAX_VISIBLE_TIME = 1.5
MIN_SPAWN_DELAY = 0.5 # Min time between new images appearing
MAX_SPAWN_DELAY = 1.0 # Max time

SCALE_IMAGES = True
MAX_IMAGE_WIDTH_PERCENT = 0.75
MAX_IMAGE_HEIGHT_PERCENT = 0.75

CONFIG_FILE_NAME = "image_fader_config.json"

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

# --- Pygame Image Class ---
class FadingImage:
    def __init__(self, image_path, screen_width, screen_height):
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

        if SCALE_IMAGES:
            img_w, img_h = surface_to_process.get_size()
            if img_w > 0 and img_h > 0:
                max_allowed_w = screen_width * MAX_IMAGE_WIDTH_PERCENT
                max_allowed_h = screen_height * MAX_IMAGE_HEIGHT_PERCENT
                
                if img_w > max_allowed_w or img_h > max_allowed_h:
                    ratio_w = max_allowed_w / img_w
                    ratio_h = max_allowed_h / img_h
                    scale_ratio = min(ratio_w, ratio_h)
                    
                    if scale_ratio < 1.0:
                        new_width = max(1, int(img_w * scale_ratio))
                        new_height = max(1, int(img_h * scale_ratio))
                        # print(f"PYGAME: Scaling {os.path.basename(image_path)} from ({img_w}x{img_h}) to ({new_width}x{new_height})")
                        try:
                            surface_to_process = pygame.transform.smoothscale(surface_to_process, (new_width, new_height))
                        except (pygame.error, ValueError) as e_scale:
                            print(f"PYGAME Warning: Error scaling {os.path.basename(image_path)}: {e_scale}. Using original loaded size.")
                            # Fallback to original loaded if scaling fails
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
        self.fade_in_duration = random.uniform(MIN_FADE_TIME, MAX_FADE_TIME)
        self.visible_duration = random.uniform(MIN_VISIBLE_TIME, MAX_VISIBLE_TIME)
        self.fade_out_duration = random.uniform(MIN_FADE_TIME, MAX_FADE_TIME)
        self.state = "fading_in"
        self.timer = 0.0

    def update(self, dt):
        if self.surface is None: return False
        self.timer += dt
        if self.state == "fading_in":
            self.alpha = min(self.max_alpha, (self.timer / self.fade_in_duration) * self.max_alpha) if self.fade_in_duration > 0 else self.max_alpha
            if self.timer >= self.fade_in_duration:
                self.alpha = self.max_alpha
                self.state = "visible"
                self.timer = 0.0
        elif self.state == "visible":
            if self.timer >= self.visible_duration:
                self.state = "fading_out"
                self.timer = 0.0
        elif self.state == "fading_out":
            self.alpha = max(0, self.max_alpha - (self.timer / self.fade_out_duration) * self.max_alpha) if self.fade_out_duration > 0 else 0
            if self.timer >= self.fade_out_duration or self.alpha <= 0:
                return False
        self.surface.set_alpha(int(self.alpha))
        return True

    def draw(self, screen):
        if self.surface:
            screen.blit(self.surface, self.rect)

# --- Pygame Visualization Main Function ---
def run_pygame_visualization(selected_image_dirs, screen_width, screen_height):
    if not pygame.get_init(): # Ensure Pygame is initialized
        pygame.init()

    print("PYGAME: Starting visualization...")
    try:
        screen = pygame.display.set_mode((screen_width, screen_height), pygame.FULLSCREEN | pygame.HWSURFACE | pygame.DOUBLEBUF)
    except pygame.error as e:
        print(f"PYGAME Error setting up Pygame fullscreen display: {e}")
        messagebox.showerror("Pygame Error", f"Could not set up fullscreen display:\n{e}\n\nReturning to GUI.")
        if pygame.get_init(): pygame.quit()
        return
        
    pygame.display.set_caption("Color Shifting Fader")
    pygame.mouse.set_visible(False)
    clock = pygame.time.Clock()

    current_top_color = get_random_color()
    target_top_color = get_random_color()
    current_bottom_color = get_random_color()
    target_bottom_color = get_random_color()
    color_lerp_factor = 0.0

    all_image_paths = load_image_paths_from_selected_dirs(selected_image_dirs)
    if not all_image_paths:
        print("PYGAME: No usable images found. Aborting visualization.")
        messagebox.showwarning("No Images", "No images found in the selected directories. Returning to GUI.")
        pygame.mouse.set_visible(True)
        if pygame.get_init(): pygame.quit()
        return

    available_image_paths = []
    def replenish_image_paths():
        nonlocal available_image_paths
        if not all_image_paths: return
        available_image_paths = all_image_paths[:] 
        random.shuffle(available_image_paths)
        # print(f"PYGAME: Image pool replenished. {len(available_image_paths)} images available.")

    replenish_image_paths()
    active_images = []
    next_image_spawn_time = time.time() + random.uniform(MIN_SPAWN_DELAY, MAX_SPAWN_DELAY)
    running = True
    print("PYGAME: Visualization running. Press any key or mouse button to return to GUI.")

    while running:
        dt = clock.tick(FPS) / 1000.0
        for event in pygame.event.get():
            if event.type == pygame.QUIT: running = False
            if event.type == pygame.KEYDOWN or event.type == pygame.MOUSEBUTTONDOWN:
                running = False
        
        if not running: break

        color_lerp_factor += COLOR_CHANGE_SPEED * dt
        if color_lerp_factor >= 1.0:
            color_lerp_factor = 0.0
            current_top_color, target_top_color = target_top_color, get_random_color()
            current_bottom_color, target_bottom_color = target_bottom_color, get_random_color()

        display_top_color = interpolate_color(current_top_color, target_top_color, color_lerp_factor)
        display_bottom_color = interpolate_color(current_bottom_color, target_bottom_color, color_lerp_factor)

        if time.time() >= next_image_spawn_time:
            if not available_image_paths: replenish_image_paths()
            if available_image_paths:
                new_image = FadingImage(available_image_paths.pop(0), screen_width, screen_height)
                if new_image.surface: active_images.append(new_image)
            next_image_spawn_time = time.time() + random.uniform(MIN_SPAWN_DELAY, MAX_SPAWN_DELAY)

        active_images[:] = [img for img in active_images if img.update(dt)] # Efficient update and removal

        for y_coord in range(screen_height):
            row_factor = y_coord / screen_height
            color = interpolate_color(display_top_color, display_bottom_color, row_factor)
            pygame.draw.line(screen, color, (0, y_coord), (screen_width, y_coord))
        
        for img in active_images: img.draw(screen)
        pygame.display.flip()

    print("PYGAME: Visualization ended. Returning to GUI.")
    pygame.mouse.set_visible(True) # Make mouse visible before quitting Pygame
    if pygame.get_init(): pygame.quit()


# --- Tkinter GUI Class ---
class DirectorySelectorGUI:
    def __init__(self, master, screen_w, screen_h):
        self.master = master
        self.screen_width = screen_w
        self.screen_height = screen_h
        self.master.title("Image Fader - Directory Selector")
        self.master.geometry("600x450") # Adjusted size

        # Data structure: list of dicts {'path': str, 'enabled_var': tk.BooleanVar}
        self.directories_data = []

        self._build_ui()
        self._load_configuration() # Load and populate

        self.master.protocol("WM_DELETE_WINDOW", self._on_quit)


    def _get_config_path(self):
        # Place config in user's documents or appdata if preferred for broader distribution
        # For simplicity, placing it next to the script
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), CONFIG_FILE_NAME)

    def _load_configuration(self):
        config_path = self._get_config_path()
        loaded_dirs = []
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    config_data = json.load(f)
                    loaded_dirs = config_data.get("directories", [])
                print(f"GUI: Configuration loaded from {config_path}")
            else:
                print(f"GUI: No configuration file found at {config_path}. Starting fresh.")

        except json.JSONDecodeError:
            print(f"GUI Error: Could not decode JSON from {config_path}. Starting fresh.")
        except Exception as e:
            print(f"GUI Error loading configuration: {e}. Starting fresh.")

        self.directories_data = [] # Clear existing before loading
        for item in loaded_dirs:
            path = item.get("path")
            enabled = item.get("enabled", True) # Default to True if missing
            if path and os.path.isdir(path): # Check if directory still exists
                 # Create a new BooleanVar for each loaded item
                enabled_var = tk.BooleanVar(value=enabled)
                enabled_var.trace_add("write", lambda *args: self._save_configuration()) # Auto-save on check/uncheck
                self.directories_data.append({'path': path, 'enabled_var': enabled_var})
            elif path:
                print(f"GUI Warning: Saved directory path not found or not a directory, skipping: {path}")
        
        self._populate_dir_list_ui()


    def _save_configuration(self):
        config_path = self._get_config_path()
        # Prepare data for JSON: convert BooleanVar.get() to bool
        dirs_to_save = [{'path': item['path'], 'enabled': item['enabled_var'].get()} for item in self.directories_data]
        
        try:
            with open(config_path, 'w') as f:
                json.dump({"directories": dirs_to_save}, f, indent=4)
            print(f"GUI: Configuration saved to {config_path}")
        except Exception as e:
            print(f"GUI Error saving configuration: {e}")
            messagebox.showerror("Save Error", f"Could not save configuration:\n{e}")

    def _build_ui(self):
        # Main frame
        main_frame = ttk.Frame(self.master, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Top buttons frame
        top_button_frame = ttk.Frame(main_frame)
        top_button_frame.pack(fill=tk.X, pady=(0, 10))

        add_button = ttk.Button(top_button_frame, text="Add Directory", command=self._add_new_directory)
        add_button.pack(side=tk.LEFT, padx=(0, 5))
        
        select_all_button = ttk.Button(top_button_frame, text="Select All", command=self._select_all_dirs)
        select_all_button.pack(side=tk.LEFT, padx=5)

        deselect_all_button = ttk.Button(top_button_frame, text="Deselect All", command=self._deselect_all_dirs)
        deselect_all_button.pack(side=tk.LEFT, padx=5)


        # Directory list area (Scrollable)
        list_container = ttk.LabelFrame(main_frame, text="Image Directories")
        list_container.pack(fill=tk.BOTH, expand=True, pady=(0,10))

        self.canvas = tk.Canvas(list_container, borderwidth=0, background="#ffffff")
        self.dir_list_frame = ttk.Frame(self.canvas, padding="5") # Frame to hold directory entries
        self.scrollbar = ttk.Scrollbar(list_container, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.canvas_window = self.canvas.create_window((0, 0), window=self.dir_list_frame, anchor="nw")

        self.dir_list_frame.bind("<Configure>", self._on_frame_configure)
        self.canvas.bind('<Configure>', self._on_canvas_configure)
        
        # Mouse wheel scrolling for canvas
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel) # For Windows/macOS
        self.canvas.bind_all("<Button-4>", self._on_mousewheel) # For Linux (scroll up)
        self.canvas.bind_all("<Button-5>", self._on_mousewheel) # For Linux (scroll down)


        # Bottom buttons frame
        bottom_button_frame = ttk.Frame(main_frame)
        bottom_button_frame.pack(fill=tk.X, pady=(10,0))

        run_button = ttk.Button(bottom_button_frame, text="Run Visualization", command=self._on_run_visualization, style="Accent.TButton")
        run_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0,5))
        
        # Add a style for the accent button if ttkthemes is not used or for more control
        style = ttk.Style()
        style.configure("Accent.TButton", font=('Helvetica', 10, 'bold')) # Example

        quit_button = ttk.Button(bottom_button_frame, text="Quit Program", command=self._on_quit)
        quit_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(5,0))

    def _on_frame_configure(self, event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event=None):
        # Update the canvas window size to match the canvas width
        self.canvas.itemconfig(self.canvas_window, width=self.canvas.winfo_width())

    def _on_mousewheel(self, event):
        # Check if mouse is over the canvas
        if self.canvas.winfo_containing(event.x_root, event.y_root) == self.canvas:
            if event.num == 4 or event.delta > 0: # Scroll up
                self.canvas.yview_scroll(-1, "units")
            elif event.num == 5 or event.delta < 0: # Scroll down
                self.canvas.yview_scroll(1, "units")

    def _populate_dir_list_ui(self):
        # Clear existing widgets in dir_list_frame
        for widget in self.dir_list_frame.winfo_children():
            widget.destroy()

        if not self.directories_data:
            no_dirs_label = ttk.Label(self.dir_list_frame, text="No directories added yet. Click 'Add Directory'.")
            no_dirs_label.pack(pady=10)
            return

        for i, item_data in enumerate(self.directories_data):
            path = item_data['path']
            enabled_var = item_data['enabled_var']

            entry_frame = ttk.Frame(self.dir_list_frame)
            entry_frame.pack(fill=tk.X, pady=2)

            check = ttk.Checkbutton(entry_frame, variable=enabled_var)
            check.pack(side=tk.LEFT, padx=(0, 5))

            # Truncate long paths for display
            display_path = path
            if len(path) > 60: # Arbitrary length
                display_path = "..." + path[-57:]
            
            label = ttk.Label(entry_frame, text=display_path, anchor="w", width=60) # Fixed width helps layout
            label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
            label.bind("<Button-1>", lambda e, p=path: self._toggle_check_for_path(p)) # Click label to toggle

            remove_btn = ttk.Button(entry_frame, text="Remove", width=8,
                                   command=lambda p=path: self._remove_dir_entry(p))
            remove_btn.pack(side=tk.RIGHT, padx=(5, 0))
        
        self._on_frame_configure() # Update scrollregion


    def _toggle_check_for_path(self, path_to_toggle):
        for item_data in self.directories_data:
            if item_data['path'] == path_to_toggle:
                item_data['enabled_var'].set(not item_data['enabled_var'].get())
                # self._save_configuration() is automatically called by trace_add
                break

    def _add_new_directory(self):
        dir_path = filedialog.askdirectory(master=self.master, title="Select Image Directory")
        if dir_path:
            normalized_path = os.path.normpath(dir_path)
            if any(item['path'] == normalized_path for item in self.directories_data):
                messagebox.showinfo("Duplicate", "This directory is already in the list.", parent=self.master)
                return

            enabled_var = tk.BooleanVar(value=True)
            enabled_var.trace_add("write", lambda *args: self._save_configuration()) # Auto-save on check/uncheck
            self.directories_data.append({'path': normalized_path, 'enabled_var': enabled_var})
            print(f"GUI: Added directory: {normalized_path}")
            self._populate_dir_list_ui()
            self._save_configuration() # Save after adding

    def _remove_dir_entry(self, path_to_remove):
        self.directories_data = [item for item in self.directories_data if item['path'] != path_to_remove]
        print(f"GUI: Removed directory: {path_to_remove}")
        self._populate_dir_list_ui()
        self._save_configuration() # Save after removing

    def _select_all_dirs(self):
        for item in self.directories_data:
            item['enabled_var'].set(True)
        # self._save_configuration() will be called by trace for each change
    
    def _deselect_all_dirs(self):
        for item in self.directories_data:
            item['enabled_var'].set(False)
        # self._save_configuration() will be called by trace for each change

    def _on_run_visualization(self):
        selected_paths = [item['path'] for item in self.directories_data if item['enabled_var'].get()]
        
        if not selected_paths:
            messagebox.showwarning("No Directories Selected", 
                                   "Please select at least one directory to run the visualization.", 
                                   parent=self.master)
            return

        print(f"GUI: Starting visualization with {len(selected_paths)} selected directories.")
        self.master.withdraw() # Hide Tkinter window
        
        # It's important Pygame is properly initialized and quit for each run
        # to avoid conflicts if Tkinter also uses display resources subtly.
        if pygame.get_init(): # If Pygame was somehow left initialized
             pygame.quit()
        pygame.init() # Fresh init

        run_pygame_visualization(selected_paths, self.screen_width, self.screen_height)
        
        # Ensure Pygame is quit before showing Tkinter window again
        if pygame.get_init():
            pygame.quit()
            
        self.master.deiconify() # Show Tkinter window again
        self.master.lift() # Bring to front
        self.master.focus_force() # Try to give focus

    def _on_quit(self):
        print("GUI: Quit button pressed. Saving configuration and exiting.")
        # self._save_configuration() # Usually auto-saved, but one last save can't hurt
        self.master.quit()
        self.master.destroy()


# --- Main Application Entry ---
if __name__ == '__main__':
    # Initialize Pygame temporarily just to get screen dimensions
    # This is a common pattern when mixing Pygame with a GUI toolkit that takes precedence.
    pg_screen_width, pg_screen_height = 0, 0
    try:
        pygame.init()
        screen_info = pygame.display.Info()
        pg_screen_width = screen_info.current_w
        pg_screen_height = screen_info.current_h
        pygame.quit() # Quit Pygame immediately, it will be re-initialized by run_pygame_visualization
    except pygame.error as e:
        print(f"CRITICAL: Could not initialize Pygame to get screen dimensions: {e}")
        print("The program might not function correctly or at all.")
        # Fallback or ask user? For now, try default.
        # Alternatively, exit here or use hardcoded defaults if Pygame can't init at all.
        # If this fails, the visualization part will likely also fail.
        # For now, let's assume it's a transient issue or a headless environment setup.
        # We can try to proceed and let run_pygame_visualization handle its own init.
        # If screen dimensions are critical for the GUI itself, this is a problem.
        # For this app, screen_w/h are only passed to Pygame, so it's less critical for the GUI.

    if pg_screen_width == 0 or pg_screen_height == 0:
        print("Warning: Could not determine primary screen dimensions via Pygame. Visualization might use default or fail.")
        # Provide some defaults if Pygame fails to initialize for screen info
        # This is a fallback, actual screen detection is preferred
        pg_screen_width, pg_screen_height = 1024, 768 # Common fallback
        # Inform user through a simple dialog if Tk is available
        root_temp = tk.Tk()
        root_temp.withdraw()
        messagebox.showwarning("Screen Detection Failed",
                               "Could not automatically detect screen dimensions.\n"
                               "Visualization will attempt to run but might not be optimal.\n"
                               f"Using fallback: {pg_screen_width}x{pg_screen_height}")
        root_temp.destroy()


    root = tk.Tk()
    app = DirectorySelectorGUI(root, pg_screen_width, pg_screen_height)
    root.mainloop()

    print("Application has exited.")