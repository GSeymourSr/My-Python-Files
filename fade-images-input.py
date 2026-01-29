import pygame
import random
import os
import time
import tkinter as tk
from tkinter import filedialog, messagebox

# --- Configuration ---
FPS = 30  # Frames per second

# Color change speed (lower is slower)
COLOR_CHANGE_SPEED = 0.3 # 0.1 is quite slow, 1 is faster

# Image appearance timing (seconds)
MIN_FADE_TIME = 1.0
MAX_FADE_TIME = 2.0
MIN_VISIBLE_TIME = 0.3
MAX_VISIBLE_TIME = 1.5
MIN_SPAWN_DELAY = 0.5 # Min time between new images appearing
MAX_SPAWN_DELAY = 1.0 # Max time

# Image Scaling Configuration
SCALE_IMAGES = True  # Set to False to disable scaling
# Max image dimension as a percentage of screen dimension
MAX_IMAGE_WIDTH_PERCENT = 0.75  # e.g., image width won't exceed 30% of screen width
MAX_IMAGE_HEIGHT_PERCENT = 0.75 # e.g., image height won't exceed 30% of screen height

# --- Helper Functions ---
def get_random_color():
    return (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))

def interpolate_color(color1, color2, factor):
    """Linearly interpolate between two colors."""
    r = int(color1[0] + (color2[0] - color1[0]) * factor)
    g = int(color1[1] + (color2[1] - color1[1]) * factor)
    b = int(color1[2] + (color2[2] - color1[2]) * factor)
    return (max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b)))

def load_image_paths(directories_list):
    """Loads all valid image paths from a list of directories."""
    supported_formats = ('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp') # Added webp
    all_paths = []
    if not directories_list:
        print("Error: No directories provided to load images from.")
        return []

    print("\n--- Scanning Directories for Images ---")
    for directory in directories_list:
        if not os.path.isdir(directory):
            print(f"Warning: Path is not a directory or not found: {directory}")
            continue
        
        current_dir_images = 0
        try:
            for filename in os.listdir(directory):
                if filename.lower().endswith(supported_formats):
                    all_paths.append(os.path.join(directory, filename))
                    current_dir_images +=1
            print(f"Found {current_dir_images} images in '{os.path.basename(directory)}' ({directory})")
        except OSError as e:
            print(f"Error accessing directory {directory}: {e}")
            continue # Skip this directory

    if not all_paths:
        print("-----------------------------------------")
        print("Warning: No images found in any of the provided directories.")
        print("-----------------------------------------")
    else:
        print(f"Total unique image paths loaded: {len(all_paths)}")
        print("-----------------------------------------\n")
    return all_paths

# --- Image Class ---
class FadingImage:
    def __init__(self, image_path, screen_width, screen_height):
        self.surface = None # Initialize to None, indicates failure if it remains None
        self.original_surface = None # For clarity, also initialize

        try:
            # Load the image first
            loaded_surface = pygame.image.load(image_path)
        except pygame.error as e:
            print(f"Pygame error loading image {image_path}: {e}")
            return # self.surface remains None, constructor fails gracefully
        except Exception as e: # Catch other potential errors like file not found
            print(f"Generic error loading image {image_path}: {e}")
            return

        surface_to_process = loaded_surface # Start with the successfully loaded surface

        if SCALE_IMAGES:
            img_w = surface_to_process.get_width()
            img_h = surface_to_process.get_height()

            if img_w == 0 or img_h == 0: # Should ideally not happen with valid images
                print(f"Warning: Image {os.path.basename(image_path)} has zero dimension ({img_w}x{img_h}). Skipping scaling.")
            else:
                max_allowed_w = screen_width * MAX_IMAGE_WIDTH_PERCENT
                max_allowed_h = screen_height * MAX_IMAGE_HEIGHT_PERCENT
                
                needs_scaling = False
                if img_w > max_allowed_w or img_h > max_allowed_h:
                    needs_scaling = True

                if needs_scaling:
                    # Calculate scale ratios for width and height
                    ratio_w = max_allowed_w / img_w
                    ratio_h = max_allowed_h / img_h
                    
                    # Choose the smaller ratio to ensure the image fits both dimensions while maintaining aspect ratio
                    scale_ratio = min(ratio_w, ratio_h)
                    
                    if scale_ratio < 1.0: # Only scale down, not up
                        new_width = int(img_w * scale_ratio)
                        new_height = int(img_h * scale_ratio)
                        
                        # Ensure new dimensions are at least 1x1 to avoid errors with (smooth)scale
                        new_width = max(1, new_width)
                        new_height = max(1, new_height)
                        
                        print(f"Scaling {os.path.basename(image_path)} from ({img_w}x{img_h}) to ({new_width}x{new_height})")
                        try:
                            surface_to_process = pygame.transform.smoothscale(surface_to_process, (new_width, new_height))
                        except pygame.error as e_smooth:
                            print(f"Error during smoothscale for {os.path.basename(image_path)}: {e_smooth}. Trying regular scale.")
                            try:
                                surface_to_process = pygame.transform.scale(surface_to_process, (new_width, new_height))
                            except pygame.error as e_scale:
                                print(f"Error during regular scale for {os.path.basename(image_path)}: {e_scale}. Using original loaded size.")
                        except ValueError as e_val: # Can happen if new_width/height is invalid for smoothscale
                             print(f"ValueError during scaling {os.path.basename(image_path)} to ({new_width}x{new_height}): {e_val}. Using original loaded size.")


        # Convert to a format optimal for blitting, with alpha transparency
        try:
            self.original_surface = surface_to_process.convert_alpha()
        except pygame.error as e:
            print(f"Error converting surface for {os.path.basename(image_path)} after potential scaling: {e}")
            return # self.surface remains None
            
        self.surface = self.original_surface.copy() # Work with a copy for alpha changes
        self.rect = self.surface.get_rect()

        # Random position (ensure it's fully on screen)
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
        if self.surface is None: # Check if initialization failed
            return False # Signal to remove this "image" (which is invalid)

        self.timer += dt

        if self.state == "fading_in":
            if self.fade_in_duration > 0:
                self.alpha = min(self.max_alpha, (self.timer / self.fade_in_duration) * self.max_alpha)
            else:
                self.alpha = self.max_alpha # Instant fade in

            if self.timer >= self.fade_in_duration:
                self.alpha = self.max_alpha
                self.state = "visible"
                self.timer = 0.0

        elif self.state == "visible":
            if self.timer >= self.visible_duration:
                self.state = "fading_out"
                self.timer = 0.0

        elif self.state == "fading_out":
            if self.fade_out_duration > 0:
                self.alpha = max(0, self.max_alpha - (self.timer / self.fade_out_duration) * self.max_alpha)
            else:
                self.alpha = 0 # Instant fade out

            if self.timer >= self.fade_out_duration or self.alpha <= 0:
                return False  # Signal to remove this image

        self.surface.set_alpha(int(self.alpha))
        return True

    def draw(self, screen):
        if self.surface:
            screen.blit(self.surface, self.rect)

# --- Main Program ---
def main():
    pygame.init()

    # Get screen dimensions first
    try:
        screen_info = pygame.display.Info()
        screen_width = screen_info.current_w
        screen_height = screen_info.current_h
    except pygame.error as e:
        print(f"Could not get screen info: {e}. Pygame display might not be initialized correctly.")
        print("Try ensuring a desktop environment is active if not running headless.")
        pygame.quit()
        return


    # --- Directory Selection GUI ---
    selected_image_dirs = []
    root_tk = None # Initialize to allow conditional destruction in finally block
    try:
        root_tk = tk.Tk()
        root_tk.withdraw()  # Hide the main Tkinter window
        
        print("Please use the dialogs to select your image directories.")
        while True:
            # For askdirectory, parent should ideally be an existing Tk window.
            # If root_tk is withdrawn, it still serves as the logical parent.
            dir_path = filedialog.askdirectory(
                parent=root_tk, 
                title="Select an Image Directory (Press Cancel or close dialog to finish)"
            )
            if dir_path: # User selected a directory
                if dir_path not in selected_image_dirs: # Avoid duplicates
                    selected_image_dirs.append(dir_path)
                    print(f"Added directory: {dir_path}")
                else:
                    print(f"Directory already selected, skipping: {dir_path}")
                
                # Ask if they want to add another using messagebox
                if not messagebox.askyesno("Select More?", "Do you want to select another image directory?", parent=root_tk):
                    print("Finished selecting directories.")
                    break
            else: # User pressed Cancel or closed the dialog without selection
                print("No directory selected in this step, or selection process cancelled by user.")
                break
    except tk.TclError as e: # Handles issues like "display name and display var cannot be None"
        print(f"Could not initialize Tkinter for directory selection: {e}")
        print("This program requires a graphical environment with Tkinter support.")
        print("Exiting.")
        pygame.quit()
        return
    except Exception as e: # Catch any other unexpected error during Tkinter phase
        print(f"An unexpected error occurred during directory selection: {e}")
        pygame.quit()
        return
    finally:
        if root_tk: # Only destroy if it was successfully created
            root_tk.destroy()

    if not selected_image_dirs:
        print("No image directories were selected. Exiting program.")
        pygame.quit()
        return
    
    print(f"\nProceeding with images from selected directories: {selected_image_dirs}")

    # --- Pygame Screen Setup ---
    try:
        screen = pygame.display.set_mode((screen_width, screen_height), pygame.FULLSCREEN | pygame.HWSURFACE | pygame.DOUBLEBUF)
    except pygame.error as e:
        print(f"Error setting up Pygame fullscreen display: {e}")
        print("This might be due to display driver issues or running in a headless environment.")
        pygame.quit()
        return
        
    pygame.display.set_caption("Color Shifting Fader")
    pygame.mouse.set_visible(False)
    clock = pygame.time.Clock()

    # Background color management
    current_top_color = get_random_color()
    target_top_color = get_random_color()
    current_bottom_color = get_random_color()
    target_bottom_color = get_random_color()
    color_lerp_factor = 0.0

    # Image management
    all_image_paths = load_image_paths(selected_image_dirs)
    if not all_image_paths:
        print("No usable images found in the selected directories. Exiting.")
        pygame.quit()
        return

    available_image_paths = []
    def replenish_image_paths():
        nonlocal available_image_paths
        if not all_image_paths: # Safeguard, though checked above
             print("Warning: No images in all_image_paths to replenish from. This cycle will have no new images.")
             return
        available_image_paths = all_image_paths[:] 
        random.shuffle(available_image_paths)
        print(f"Image pool replenished and shuffled. {len(available_image_paths)} images available for this cycle.")

    replenish_image_paths() # Initial fill

    active_images = []
    next_image_spawn_time = time.time() + random.uniform(MIN_SPAWN_DELAY, MAX_SPAWN_DELAY)

    running = True
    print("\nProgram started. Press any key or mouse button to quit.")
    print("(ESC key also quits explicitly).")

    while running:
        dt = clock.tick(FPS) / 1000.0  # Delta time in seconds

        for event in pygame.event.get():
            if event.type == pygame.QUIT: # Window close button (less relevant in fullscreen)
                print("QUIT event received, exiting...")
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    print("ESC key pressed, exiting...")
                    running = False
                else:
                    # Any other key press
                    print(f"Key '{pygame.key.name(event.key)}' pressed, exiting...")
                    running = False
            if event.type == pygame.MOUSEBUTTONDOWN:
                print(f"Mouse button {event.button} pressed, exiting...")
                running = False
        
        if not running: # Check if an event in the loop set running to False
            break

        # --- Update Logic ---
        # Background color transition
        color_lerp_factor += COLOR_CHANGE_SPEED * dt
        if color_lerp_factor >= 1.0:
            color_lerp_factor = 0.0
            current_top_color = target_top_color
            target_top_color = get_random_color()
            current_bottom_color = target_bottom_color
            target_bottom_color = get_random_color()

        display_top_color = interpolate_color(current_top_color, target_top_color, color_lerp_factor)
        display_bottom_color = interpolate_color(current_bottom_color, target_bottom_color, color_lerp_factor)

        # Spawn new images
        if time.time() >= next_image_spawn_time:
            if not available_image_paths:
                if not all_image_paths: 
                    # This state means no images were loaded at all, or all_image_paths got emptied somehow.
                    # The program should have exited earlier if no images were loaded initially.
                    # If it reaches here, it implies an issue or that all images had errors.
                    pass # No new images to spawn this cycle
                else:
                    replenish_image_paths()

            if available_image_paths: # Check again after potential replenish
                image_path_to_load = available_image_paths.pop(0)
                new_image = FadingImage(image_path_to_load, screen_width, screen_height)
                if new_image.surface: # Check if FadingImage was successfully initialized
                    active_images.append(new_image)
                # else: FadingImage __init__ already prints errors if it fails
            
            next_image_spawn_time = time.time() + random.uniform(MIN_SPAWN_DELAY, MAX_SPAWN_DELAY)

        # Update active images
        # Iterate backwards for safe removal if an image signals it's done
        for i in range(len(active_images) - 1, -1, -1):
            if not active_images[i].update(dt):
                active_images.pop(i)

        # --- Drawing ---
        # Draw gradient background
        for y_coord in range(screen_height):
            row_factor = y_coord / screen_height # Normalized y for interpolation
            color = interpolate_color(display_top_color, display_bottom_color, row_factor)
            pygame.draw.line(screen, color, (0, y_coord), (screen_width, y_coord))

        # Draw images
        for img in active_images:
            img.draw(screen)

        pygame.display.flip()

    print("Exiting program normally...")
    pygame.quit()

if __name__ == '__main__':
    main()