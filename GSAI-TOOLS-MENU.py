import tkinter as tk
from tkinter import ttk, font, messagebox
import sys
import os
import subprocess
import webbrowser
import random
import time

# --- Tool Data ---
# Each dictionary: name (display), description, filename, type ('python' or 'html')
SCRIPTS_DATA = [
    {
        "name": "Image Fader & Recorder",
        "description": "Visualizes images from selected directories with fading effects, animated background colors, optional audio, and MP4 recording.",
        "filename": "fade-images-GSAI-tool.py",
        "type": "python"
    },
    {
        "name": "HTML to EXE Packer (Simple)",
        "description": "Converts a single standalone HTML file into a Windows executable using PyInstaller. (Fixed version)",
        "filename": "make-exe-html.py",
        "type": "python"
    },
    {
        "name": "Whimsical File Menu Maker",
        "description": "Generates a Python script for a customizable, themed menu to launch selected files (executables, scripts, documents, HTML with Selenium).",
        "filename": "menu-maker5.py",
        "type": "python"
    },
    {
        "name": "HTML Slideshow Player (30s)",
        "description": "A tool to select and play multiple HTML files in a fullscreen slideshow, each displayed for 30 seconds. Uses Selenium.",
        "filename": "HTML_VIEWER-30sec.py",
        "type": "python"
    },
    {
        "name": "Advanced HTML Slideshow",
        "description": "Fullscreen HTML-based image slideshow with numerous transition effects and controls for image selection (files, directory, JSON).",
        "filename": "slideshow8.html",
        "type": "html"
    },
    {
        "name": "MP3 Volume Booster",
        "description": "Increases or decreases the volume of MP3 files using pydub.",
        "filename": "volume-boost-mp3s.py",
        "type": "python"
    },
    {
        "name": "EXE Maker (AST Assets)",
        "description": "Bundles a Python script and its automatically detected assets (via AST parsing) into a single executable using PyInstaller.",
        "filename": "Make-a-EXE.py",
        "type": "python"
    },
    {
        "name": "MP3 Visual Cropper",
        "description": "Visually select start and end points on an MP3 waveform to crop audio segments. Features playback and waveform display.",
        "filename": "mp3-cropc.py",
        "type": "python"
    },
    {
        "name": "Image Flipper & Rotator",
        "description": "Batch flip (horizontally/vertically) or rotate (90°, 180°, 270°) multiple images. Saves modified images to a selected directory.",
        "filename": "flip-images1.py", # Corrected typo from flip-inages1.py
        "type": "python"
    },
    {
        "name": "Image Resizer & Upscaler",
        "description": "GUI tool to resize images with various presets (half, double, aspect ratios, custom) and optionally upscale with Real-ESRGAN. Supports transparency.",
        "filename": "resize-images001.py",
        "type": "python"
    },
    {
        "name": "Image Processor Suite",
        "description": "Comprehensive GUI for batch image processing: resize, flip, rotate, upscale (Real-ESRGAN), background removal (rembg), and crop.",
        "filename": "image-suite-gsai.py",
        "type": "python"
    },
    {
        "name": "EXE Maker (NEW - Advanced Assets)",
        "description": "Advanced PyInstaller wrapper. Select a Python script, it auto-detects assets, copies them, modifies the script for correct asset pathing, and builds an EXE.",
        "filename": "make-exe-NEW.py",
        "type": "python"
    },
    {
        "name": "Batch BG Remover & Cropper (Images)",
        "description": "Removes backgrounds from all images in a specified folder using rembg, then crops them to content, and saves to an output folder.",
        "filename": "remove_bg-crop.py",
        "type": "python"
    },
    {
        "name": "MP4 to Image Frames Extractor",
        "description": "Extracts frames from an MP4 video at a specified FPS (or all frames) and saves them as PNG images.",
        "filename": "mp4-to-images.py",
        "type": "python"
    },
    {
        "name": "MP4 to GIF Converter",
        "description": "Converts MP4 video files to animated GIFs with optional FPS adjustment using moviepy.",
        "filename": "mp4-to-gif.py",
        "type": "python"
    },
    {
        "name": "Screen Recorder (Groq3)",
        "description": "Records the screen (primary monitor) and saves as an MP4 video. Supports custom FPS and duration. Controllable via GUI and 'R' key.",
        "filename": "record-screen-groq3.py",
        "type": "python"
    },
    {
        "name": "Image List to JSON (for Slideshow)",
        "description": "Selects an image directory and creates a JSON file listing all image paths within it, suitable for use with slideshow applications.",
        "filename": "json-slideshow-imagelist.py",
        "type": "python"
    },
    {
        "name": "Image to MP4 Video (HTML)",
        "description": "Web-based tool to convert a sequence of selected images into an MP4 video. Controls for frame delay and looping.",
        "filename": "img-to-mp4-video.html",
        "type": "html"
    },
    {
        "name": "Grid-Based Image Cropper (Fine)",
        "description": "Displays an image with an adjustable grid (rows/columns). Allows dragging grid lines and crops the image into multiple segments based on the final grid.",
        "filename": "crop-grid-fine1.py",
        "type": "python"
    },
    {
        "name": "Circular Image Cropper",
        "description": "Loads an image and allows interactive placement and resizing of a circle to crop a circular region. Saves the cropped circle on a transparent background.",
        "filename": "crop-circles.py",
        "type": "python"
    },
    {
        "name": "Video Background Remover",
        "description": "Removes backgrounds from all videos in a specified input folder and saves the processed videos (with transparency) to an output folder using rembg.",
        "filename": "remove_bg-video.py",
        "type": "python"
    },
    {
        "name": "Looping Video Player (Fwd/Back)",
        "description": "Plays selected video files (or all in a directory) forward then backward, in a loop. Options for shuffle and loop count. Controls via 'q', 'n', 'esc'.",
        "filename": "loop-videos-forever.py",
        "type": "python"
    },
     {
        "name": "Image Upscaler (Pillow)",
        "description": "Upscales images in a folder by a specified factor (default 4x) using Pillow's Lanczos resampling. Saves to an output folder.",
        "filename": "upscale.py",
        "type": "python"
    },
    {
        "name": "Image Background Remover (Pillow)",
        "description": "Removes backgrounds from images in a folder using rembg and saves them as PNGs to an output folder.",
        "filename": "remove_bg.py",
        "type": "python"
    }
]


class ToolMenuApp:
    def __init__(self, root_window):
        self.root = root_window
        self.scripts_data = SCRIPTS_DATA
        self.current_selection_index = None
        self.active_process = None # To keep track of the launched subprocess

        # --- Colors & Fonts ---
        self.bg_color_1 = [40, 20, 80]  # Dark Purple
        self.bg_color_2 = [20, 80, 120] # Deep Teal
        self.bg_color_3 = [80, 30, 60]  # Muted Magenta
        self.target_color_1 = self.get_random_gradient_color()
        self.target_color_2 = self.get_random_gradient_color()
        self.target_color_3 = self.get_random_gradient_color()
        self.gradient_step = 0.005 # Speed of color change

        self.text_color = "#E0E0E0" # Light Grey for text
        self.button_bg_base = "#4A5568"  # Cool Grey
        self.button_fg_base = "#FFFFFF"
        self.button_bg_hover = "#636E80" # Lighter Cool Grey
        self.button_relief_base = tk.RAISED
        self.button_relief_hover = tk.SUNKEN
        self.button_border_width = 2

        self.launch_button_bg = "#48BB78" # Green
        self.launch_button_fg = "#FFFFFF"
        self.launch_button_hover_bg = "#38A169" # Darker Green

        self.title_font = font.Font(family="Impact", size=36, weight="bold")
        self.button_font = font.Font(family="Segoe UI", size=11, weight="bold")
        self.description_font = font.Font(family="Segoe UI", size=10)
        self.description_title_font = font.Font(family="Segoe UI", size=13, weight="bold")

        self.setup_window()
        self.create_styles()
        self.create_widgets()
        self.populate_script_buttons()
        self.animate_gradient_background()

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def get_random_gradient_color(self):
        # Biased towards blues, purples, teals
        r = random.randint(10, 60)
        g = random.randint(30, 100)
        b = random.randint(60, 150)
        return [r,g,b]

    def interpolate_color_val(self, current_val, target_val, step):
        if current_val < target_val:
            return min(current_val + step * (target_val - current_val) * 5 , target_val) # Faster step
        elif current_val > target_val:
            return max(current_val - step * (current_val - target_val) * 5, target_val)
        return current_val

    def setup_window(self):
        self.root.title("Greg Seymour AI Tools")
        try:
            self.root.state('zoomed') # Maximize on Windows
        except tk.TclError:
             # For other OS or if zoomed fails, try to set geometry to screen size
            self.root.attributes('-fullscreen', True) # More robust for fullscreen
            # Fallback if -fullscreen is not supported as expected by some WMs
            # self.root.geometry(f"{self.root.winfo_screenwidth()}x{self.root.winfo_screenheight()}+0+0")
        self.root.minsize(800, 600)

    def create_styles(self):
        self.style = ttk.Style()
        self.style.theme_use('clam') # A theme that allows more customization

        self.style.configure("TFrame", background="#2D3748") # Fallback, canvas will cover
        self.style.configure("Title.TLabel", foreground=self.text_color, font=self.title_font, anchor="center")
        # Buttons will be tk.Button for more control over relief and direct bg/fg for hover
        self.style.configure("DescTitle.TLabel", foreground=self.text_color, font=self.description_title_font, padding=(0, 5, 0, 10))
        self.style.configure("Launch.TButton", font=self.button_font, padding=10,
                             background=self.launch_button_bg, foreground=self.launch_button_fg,
                             borderwidth=self.button_border_width, relief=self.button_relief_base)
        self.style.map("Launch.TButton",
                       background=[('active', self.launch_button_hover_bg)],
                       relief=[('active', self.button_relief_hover), ('!active', self.button_relief_base)])

    def create_widgets(self):
        # Main canvas for gradient background
        self.bg_canvas = tk.Canvas(self.root, highlightthickness=0)
        self.bg_canvas.pack(fill=tk.BOTH, expand=True)

        # Title Label
        self.title_label = ttk.Label(self.bg_canvas, text="Greg Seymour AI Tools", style="Title.TLabel")
        self.title_label.pack(pady=(30, 20), fill=tk.X)
        self.title_label.bind("<Configure>", lambda e: self.title_label.config(wraplength=self.title_label.winfo_width()-20))


        # --- Main Content Frame (transparent to show canvas gradient) ---
        # This frame will hold the button list and description area
        self.main_content_frame = tk.Frame(self.bg_canvas, bg=self.bg_canvas.cget("background")) # Make it transparent
        self.main_content_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        self.main_content_frame.columnconfigure(0, weight=1, minsize=250) # Script buttons
        self.main_content_frame.columnconfigure(1, weight=2, minsize=400) # Description
        self.main_content_frame.rowconfigure(0, weight=1)

        # --- Left Pane: Scrollable Button List ---
        self.button_list_outer_frame = tk.Frame(self.main_content_frame, bg=self.bg_canvas.cget("background"))
        self.button_list_outer_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        self.button_list_outer_frame.rowconfigure(0, weight=1)
        self.button_list_outer_frame.columnconfigure(0, weight=1)

        self.button_canvas = tk.Canvas(self.button_list_outer_frame, highlightthickness=0, bg=self.bg_canvas.cget("background"))
        self.button_scrollbar = ttk.Scrollbar(self.button_list_outer_frame, orient="vertical", command=self.button_canvas.yview)
        self.button_canvas.configure(yscrollcommand=self.button_scrollbar.set)

        self.button_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.button_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.button_list_frame = tk.Frame(self.button_canvas, bg=self.bg_canvas.cget("background"))
        self.button_canvas.create_window((0, 0), window=self.button_list_frame, anchor="nw", tags="button_list_frame")

        self.button_list_frame.bind("<Configure>", lambda e: self.button_canvas.configure(scrollregion=self.button_canvas.bbox("all")))
        self.button_canvas.bind("<Configure>", lambda e: self.button_canvas.itemconfig("button_list_frame", width=e.width))
        # Mouse wheel scrolling for button list
        self.button_canvas.bind_all("<MouseWheel>", lambda e: self.button_canvas.yview_scroll(int(-1*(e.delta/120)), "units"))
        self.button_canvas.bind_all("<Button-4>", lambda e: self.button_canvas.yview_scroll(-1, "units")) # Linux scroll up
        self.button_canvas.bind_all("<Button-5>", lambda e: self.button_canvas.yview_scroll(1, "units"))  # Linux scroll down


        # --- Right Pane: Description and Launch ---
        self.description_frame = tk.Frame(self.main_content_frame, bg=self.bg_canvas.cget("background"), relief=tk.SOLID, borderwidth=0, padx=15, pady=15) # Changed relief
        self.description_frame.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        self.description_frame.rowconfigure(0, weight=0) # Title
        self.description_frame.rowconfigure(1, weight=1) # Description Text
        self.description_frame.rowconfigure(2, weight=0) # Launch Button
        self.description_frame.columnconfigure(0, weight=1)

        self.description_title_label = ttk.Label(self.description_frame, text="Select a Tool", style="DescTitle.TLabel")
        self.description_title_label.grid(row=0, column=0, sticky="w")

        self.description_text = tk.Text(self.description_frame, wrap=tk.WORD,
                                        font=self.description_font,
                                        bg="#3A475A", fg=self.text_color, # Darker background for text area
                                        padx=10, pady=10, relief=tk.SOLID, borderwidth=1,
                                        highlightthickness=0)
        self.description_text.grid(row=1, column=0, sticky="nsew", pady=(0,15))
        self.description_text.insert(tk.END, "Click on a tool from the list on the left to see its description here.")
        self.description_text.config(state=tk.DISABLED)

        self.launch_button = ttk.Button(self.description_frame, text="Launch Tool",
                                        style="Launch.TButton", state=tk.DISABLED,
                                        command=self.launch_selected_script)
        self.launch_button.grid(row=2, column=0, sticky="ew", ipady=5)


    def populate_script_buttons(self):
        for i, script_info in enumerate(self.scripts_data):
            btn = tk.Button(self.button_list_frame, text=script_info["name"],
                            font=self.button_font,
                            bg=self.button_bg_base, fg=self.button_fg_base,
                            relief=self.button_relief_base, borderwidth=self.button_border_width,
                            activebackground=self.button_bg_hover, activeforeground=self.button_fg_base,
                            command=lambda idx=i: self.display_script_info(idx),
                            padx=10, pady=7, anchor="w")
            btn.pack(fill=tk.X, pady=(0, 4), padx=5)

            btn.bind("<Enter>", lambda e, b=btn: self.on_button_hover(b, True))
            btn.bind("<Leave>", lambda e, b=btn: self.on_button_hover(b, False))

    def on_button_hover(self, button, is_hovering):
        if is_hovering:
            button.config(bg=self.button_bg_hover, relief=self.button_relief_hover)
        else:
            button.config(bg=self.button_bg_base, relief=self.button_relief_base)

    def display_script_info(self, script_index):
        self.current_selection_index = script_index
        script_info = self.scripts_data[script_index]

        self.description_title_label.config(text=script_info["name"])

        self.description_text.config(state=tk.NORMAL)
        self.description_text.delete(1.0, tk.END)
        self.description_text.insert(tk.END, script_info["description"])
        self.description_text.config(state=tk.DISABLED)

        self.launch_button.config(state=tk.NORMAL)

    def launch_selected_script(self):
        if self.current_selection_index is None:
            messagebox.showwarning("No Tool Selected", "Please select a tool from the list first.")
            return

        if self.active_process and self.active_process.poll() is None:
            messagebox.showwarning("Process Running", "Another tool is already running. Please close it first.")
            return

        script_info = self.scripts_data[self.current_selection_index]
        filename = script_info["filename"]
        script_type = script_info["type"]
        full_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)

        if not os.path.exists(full_path):
            messagebox.showerror("File Not Found", f"The tool file '{filename}' was not found in the application directory.")
            return

        self.root.withdraw() # Hide main menu

        try:
            if script_type == "python":
                command = [sys.executable, full_path]
                print(f"Launching Python script: {' '.join(command)}")
                # For GUI scripts, Popen is usually better as it's non-blocking for the menu
                # but since we withdraw/deiconify, we can use `run` and wait for it.
                # However, some GUIs might not block `run` if they daemonize or fork.
                # Popen allows us to check `poll()` later if needed.
                self.active_process = subprocess.Popen(command)
                self.check_process_completion() # Start checking if it finished

            elif script_type == "html":
                print(f"Opening HTML file: {full_path}")
                webbrowser.open_new_tab(f"file:///{os.path.abspath(full_path)}")
                # For HTML, we can't easily wait. Deiconify after a short delay or immediately.
                self.root.after(1000, self.root.deiconify)
                self.active_process = None # No process object for webbrowser

        except Exception as e:
            messagebox.showerror("Launch Error", f"Failed to launch '{filename}':\n{str(e)}")
            print(f"Error launching {filename}: {e}")
            self.root.deiconify() # Show menu again if launch failed
            self.active_process = None

    def check_process_completion(self):
        if self.active_process:
            if self.active_process.poll() is None: # Process still running
                self.root.after(500, self.check_process_completion) # Check again later
            else: # Process finished
                print(f"Process {self.active_process.args} finished with code {self.active_process.returncode}")
                self.active_process = None
                self.root.deiconify()
                self.root.focus_force() # Try to bring menu to front
                self.root.lift()
        else:
            # If active_process became None (e.g., for HTML or if it failed to start), ensure deiconify
            if not self.root.winfo_viewable(): # Check if window is withdrawn
                 self.root.deiconify()
                 self.root.focus_force()
                 self.root.lift()


    def animate_gradient_background(self):
        # Interpolate current colors towards target colors
        for i in range(3):
            self.bg_color_1[i] = self.interpolate_color_val(self.bg_color_1[i], self.target_color_1[i], self.gradient_step)
            self.bg_color_2[i] = self.interpolate_color_val(self.bg_color_2[i], self.target_color_2[i], self.gradient_step)
            self.bg_color_3[i] = self.interpolate_color_val(self.bg_color_3[i], self.target_color_3[i], self.gradient_step)

        # Check if targets are reached
        if self.bg_color_1 == self.target_color_1: self.target_color_1 = self.get_random_gradient_color()
        if self.bg_color_2 == self.target_color_2: self.target_color_2 = self.get_random_gradient_color()
        if self.bg_color_3 == self.target_color_3: self.target_color_3 = self.get_random_gradient_color()

        # Draw gradient on canvas
        width = self.bg_canvas.winfo_width()
        height = self.bg_canvas.winfo_height()
        if width == 1 and height == 1: # Canvas not yet realized
            self.root.after(50, self.animate_gradient_background)
            return

        self.bg_canvas.delete("gradient") # Clear previous gradient

        # Three-point gradient
        # Point 1: Top (color1)
        # Point 2: Middle (color2)
        # Point 3: Bottom (color3)
        for y in range(height):
            # Interpolate between color1 and color2 for the top half
            if y < height / 2:
                factor = y / (height / 2)
                r = int(self.bg_color_1[0] + (self.bg_color_2[0] - self.bg_color_1[0]) * factor)
                g = int(self.bg_color_1[1] + (self.bg_color_2[1] - self.bg_color_1[1]) * factor)
                b = int(self.bg_color_1[2] + (self.bg_color_2[2] - self.bg_color_1[2]) * factor)
            # Interpolate between color2 and color3 for the bottom half
            else:
                factor = (y - height / 2) / (height / 2)
                r = int(self.bg_color_2[0] + (self.bg_color_3[0] - self.bg_color_2[0]) * factor)
                g = int(self.bg_color_2[1] + (self.bg_color_3[1] - self.bg_color_2[1]) * factor)
                b = int(self.bg_color_2[2] + (self.bg_color_3[2] - self.bg_color_2[2]) * factor)

            color = f"#{r:02x}{g:02x}{b:02x}"
            self.bg_canvas.create_line(0, y, width, y, fill=color, tags="gradient")

        # Make sure other widgets are on top
        self.title_label.lift()
        self.main_content_frame.lift()

        self.root.after(30, self.animate_gradient_background) # Update roughly 30 FPS

    def on_closing(self):
        if self.active_process and self.active_process.poll() is None:
            if messagebox.askokcancel("Quit", "A tool is still running. Do you want to terminate it and quit?"):
                try:
                    self.active_process.terminate()
                    self.active_process.wait(timeout=1) # Give it a moment
                except Exception as e:
                    print(f"Error terminating active process: {e}")
                self.root.destroy()
            else:
                return # Don't close
        else:
            self.root.destroy()


if __name__ == "__main__":
    # Check if all script files exist
    missing_files = []
    script_dir = os.path.dirname(os.path.abspath(__file__))
    for script_info in SCRIPTS_DATA:
        if not os.path.exists(os.path.join(script_dir, script_info["filename"])):
            missing_files.append(script_info["filename"])

    if missing_files:
        error_msg = "The following tool files are missing from the application directory:\n\n"
        error_msg += "\n".join(missing_files)
        error_msg += "\n\nPlease ensure all tool scripts are in the same folder as this menu application."
        
        # Need a temporary root to show messagebox if main app doesn't start
        temp_root = tk.Tk()
        temp_root.withdraw()
        messagebox.showerror("Missing Tool Files", error_msg)
        temp_root.destroy()
        sys.exit(1)

    root = tk.Tk()
    app = ToolMenuApp(root)
    root.mainloop()