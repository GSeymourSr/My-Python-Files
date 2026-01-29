# =============================================================================
# Imports - Bringing in necessary tools (libraries/modules)
# =============================================================================
import subprocess  # Used to run external processes (like Python scripts, notepad)
import random      # Used for shuffling file lists and generating random colors/themes
import os          # Provides functions for interacting with the operating system (listing files, paths)
import threading   # Allows running tasks (like the file loop) in the background without freezing the GUI
import tkinter as tk # The main library for creating the Graphical User Interface (GUI)
from tkinter import ttk, filedialog, font, messagebox, simpledialog # Specific components from tkinter:
                   # ttk: Themed widgets (often look more modern)
                   # filedialog: Standard dialog boxes for opening/saving files/directories
                   # font: For creating and managing custom fonts
                   # messagebox: Standard message pop-up windows (info, warning, error)
                   # simpledialog: Simple dialogs for basic input (like asking for the loop duration)
from PIL import Image, ImageTk # Pillow library (PIL fork) used for image handling (though less directly used now)
# import cv2 # No longer needed directly here, as MP4 playback uses an external script or default player
import json        # Used for saving and loading theme settings (data serialization format)
from datetime import datetime # Used to get the current date and time for the clock
import time        # Used for pausing execution (e.g., delays in the loop)
import webbrowser  # Used to open web pages or local files (like HTML, MP4, MP3) in the default application
import platform    # Used to detect the operating system (e.g., Windows, macOS, Linux) for platform-specific actions

# =============================================================================
# Main GUI Class Definition
# =============================================================================
class ScriptRunnerGUI:
    """
    Manages the main application window and all its functionality for selecting,
    running, and managing various types of files (Python, HTML, Media).
    """

    # -------------------------------------------------------------------------
    # Constructor (__init__) - Sets up the initial state of the application
    # -------------------------------------------------------------------------
    def __init__(self, master):
        """
        Initializes the ScriptRunnerGUI application.

        Args:
            master: The root Tkinter window (tk.Tk instance) that this GUI will reside in.
        """
        self.master = master  # Store the root window reference
        master.title("GREG SEYMOUR AI")  # Set the initial window title
        master.state('zoomed')  # Maximize the window on startup

        # --- Font Definitions ---
        # Define reusable font objects for consistency. We can change their properties later.
        self.default_font_family = "Arial"
        self.default_font_size = 16
        self.custom_font = font.Font(family=self.default_font_family, size=self.default_font_size)
        self.button_font = font.Font(family=self.default_font_family, size=self.default_font_size - 2, weight="bold")
        self.list_font = font.Font(family=self.default_font_family, size=self.default_font_size)
        self.scrollbar_width = 25 # Desired width for the scrollbar

        # --- State Variables ---
        # Variables to keep track of the application's current state.
        self.current_script = tk.StringVar(value="No file running") # A special Tkinter variable; changes automatically update linked labels
        self.scripts_and_files = [] # List to hold the names of detected files in the selected directory
        self.directory = ""        # Stores the path of the currently selected directory
        self.file_vars = []        # List to hold Tkinter BooleanVar objects, one for each file checkbox (True if checked, False otherwise)
        self.running_loop = False  # Flag to indicate if the 'Run Selected Loop' is currently active
        self.current_process = None # Holds the subprocess object for the *currently running Python script* (if any started by the loop)
                                   # This is needed to terminate it when stopping the loop or running another script.
        self.current_scheme = None # Stores the currently applied color/font theme dictionary

        # --- Default Paths/Names (can be customized) ---
        self.loop_videos_script_path = "loop-videos-forever.py" # Name of the external script for the "Play MP4s" button
        self.slideshow_html_path = "slideshow007.html"         # Default name for the HTML slideshow file

        # --- Theme Resources ---
        # Predefined resources for the 'Change Theme' feature.
        self.available_fonts = ["Arial", "Helvetica", "Verdana", "Georgia", "Courier New", "Tahoma", "Comic Sans MS", "Times New Roman", "Trebuchet MS", "Palatino Linotype", "Lucida Console", "Segoe UI"]
        self.color_palettes = [ # A list of dictionaries, each defining a color scheme
            # Light Themes
            {"bg": "#EAEAEA", "fg": "#333333", "button": "#D5D5D5", "button_fg": "#111111"},
            {"bg": "#F0F8FF", "fg": "#4682B4", "button": "#ADD8E6", "button_fg": "#000080"}, # Alice Blue
            {"bg": "#FFFACD", "fg": "#8B4513", "button": "#FFEC8B", "button_fg": "#8B4513"}, # Lemon Chiffon
            # Dark Themes
            {"bg": "#2E2E2E", "fg": "#E0E0E0", "button": "#4A4A4A", "button_fg": "#FFFFFF"},
            {"bg": "#1A1A2E", "fg": "#E0E0E0", "button": "#16213E", "button_fg": "#FFFFFF"}, # Dark Blue/Purple
            {"bg": "#2F4F4F", "fg": "#F5F5F5", "button": "#5F9EA0", "button_fg": "#FFFFFF"}, # Dark Slate Gray / Cadet Blue
            # High Contrast
            {"bg": "#000000", "fg": "#FFFF00", "button": "#333333", "button_fg": "#FFFF00"}, # Black/Yellow
            {"bg": "#FFFFFF", "fg": "#FF00FF", "button": "#E0E0E0", "button_fg": "#FF00FF"}, # White/Magenta
        ]

        # --- Placeholder for GUI elements (initialized in setup_gui) ---
        # It's good practice to define these as None initially, so methods called
        # before setup_gui completes (like apply_color_scheme) don't cause errors
        # if they try to access a widget that doesn't exist yet.
        self.frame = None
        self.top_frame = None
        self.start_stop_button = None
        self.clock_label = None
        self.buttons = [] # List to hold references to the main action buttons
        self.script_frame = None
        self.script_canvas = None
        self.script_scrollbar = None
        self.scrollable_frame = None # The frame *inside* the canvas that holds the checkboxes
        self.script_canvas_window = None # The ID returned when putting the scrollable_frame into the canvas

        # --- Start Building the GUI ---
        self.setup_gui()

    # -------------------------------------------------------------------------
    # GUI Setup Method - Creates and arranges all the visual elements
    # -------------------------------------------------------------------------
    def setup_gui(self):
        """Creates and lays out the widgets (buttons, labels, etc.) in the main window."""

        # --- Main Container Frame ---
        # Use a Frame as the primary container within the master window for better organization.
        # padx/pady adds padding around the frame. fill=tk.BOTH and expand=True make it resize with the window.
        self.frame = ttk.Frame(self.master, padding="10")
        self.frame.pack(fill=tk.BOTH, expand=True)

        # --- Top Section (Current Script, Start/Stop, Clock) ---
        self.top_frame = ttk.Frame(self.frame)
        # fill=tk.X makes it stretch horizontally. pady adds vertical space below it.
        self.top_frame.pack(fill=tk.X, pady=(0, 10))

        # Labels for displaying the currently running script/file.
        ttk.Label(self.top_frame, text="Current File:", font=self.custom_font).pack(side=tk.LEFT)
        # This label's text automatically updates when self.current_script changes.
        ttk.Label(self.top_frame, textvariable=self.current_script, font=self.custom_font).pack(side=tk.LEFT, padx=(5, 20))

        # Start/Stop button for the main loop.
        # Use tk.Button here because ttk.Button styling across themes/platforms can be tricky.
        self.start_stop_button = tk.Button(self.top_frame, text="Start Loop", command=self.toggle_running_loop,
                                           font=self.button_font, width=12)
        self.start_stop_button.pack(side=tk.LEFT, padx=10) # Add some padding

        # Digital clock label.
        self.clock_label = ttk.Label(self.top_frame, font=self.custom_font, text="Loading Clock...")
        self.clock_label.pack(side=tk.RIGHT) # Align to the right
        self.update_clock() # Start the clock update cycle

        # --- Button Rows ---
        # Create separate frames for rows of buttons for better layout control.
        button_frame1 = ttk.Frame(self.frame)
        button_frame1.pack(fill=tk.X, pady=(0, 5))
        button_frame2 = ttk.Frame(self.frame)
        button_frame2.pack(fill=tk.X, pady=(0, 10))

        # Define button text and the method they should call when clicked.
        buttons_row1 = [
            ("Select Directory", self.select_directory),
            ("Run Selected Loop", self.run_selected_loop),
            ("Display Images (HTML)", self.display_images_html),
            ("Play MP4s (External)", self.play_mp4s_external),
            ("Change Theme", self.change_color_scheme),
            ("Edit in Notepad", self.edit_in_notepad),
        ]
        buttons_row2 = [
            ("Select All", self.select_all),
            ("Select None", self.select_none),
            ("Save Selection", self.save_selection),
            ("Load Selection", self.load_selection), # Use the method reference directly
            ("Save Theme", self.save_theme),
            ("Load Theme", self.load_theme)
        ]

        # Create and pack the buttons, storing them in a list for easier theme updates later.
        self.buttons = []
        for text, command in buttons_row1:
            btn = tk.Button(button_frame1, text=text, command=command, font=self.button_font, width=20)
            # fill=tk.X makes buttons expand horizontally within their frame. expand=True distributes extra space.
            btn.pack(side=tk.LEFT, padx=(0, 5), fill=tk.X, expand=True)
            self.buttons.append(btn)

        for text, command in buttons_row2:
            # <<< FIXED Check if command is string and get the actual method
            actual_command = getattr(self, command) if isinstance(command, str) else command
            btn = tk.Button(button_frame2, text=text, command=actual_command, font=self.button_font, width=20)
            btn.pack(side=tk.LEFT, padx=(0, 5), fill=tk.X, expand=True)
            self.buttons.append(btn)

        # --- File List Section (Scrollable Area) ---
        # Create a frame to hold the canvas and scrollbar.
        self.script_frame = ttk.Frame(self.frame)
        self.script_frame.pack(fill=tk.BOTH, expand=True) # Take up remaining space

        # Create a Canvas widget. This is the visible area.
        self.script_canvas = tk.Canvas(self.script_frame, highlightthickness=0) # highlightthickness=0 removes border

        # Create a vertical Scrollbar.
        # command=self.script_canvas.yview links the scrollbar's movement to the canvas's vertical view.
        self.script_scrollbar = ttk.Scrollbar(self.script_frame, orient="vertical", command=self.script_canvas.yview, style='Vertical.TScrollbar')

        # Create the Frame *inside* the Canvas. This frame will actually hold the checkboxes.
        # Its size can grow beyond the canvas's visible area.
        self.scrollable_frame = ttk.Frame(self.script_canvas)

        # --- Linking Canvas, Scrollbar, and Inner Frame ---
        # Tell the canvas how to control its view using the scrollbar.
        self.script_canvas.configure(yscrollcommand=self.script_scrollbar.set)

        # Place the scrollable_frame inside the canvas using create_window.
        # anchor="nw" means the top-left corner of the frame aligns with position (0,0) in the canvas.
        self.script_canvas_window = self.script_canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")

        # When the scrollable_frame's size changes (e.g., adding/removing checkboxes),
        # update the canvas's scrollable region (`scrollregion`) to encompass the entire frame.
        self.scrollable_frame.bind("<Configure>", self._on_configure_scrollable_frame)

        # --- Mouse Wheel Binding ---
        # Bind the mouse wheel event to the canvas and the inner frame to allow scrolling.
        # Binding to both helps ensure scrolling works regardless of where the mouse pointer is.
        self.script_canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.scrollable_frame.bind("<MouseWheel>", self._on_mousewheel)
        # Using bind_all might be too broad, but can catch events if focus is on a child widget (like a checkbox)
        # self.master.bind_all("<MouseWheel>", self._on_mousewheel, add='+') # Use bind_all cautiously

        # --- Packing Canvas and Scrollbar ---
        # Pack the canvas first, making it expand.
        self.script_canvas.pack(side="left", fill="both", expand=True)
        # Pack the scrollbar next, making it fill vertically.
        self.script_scrollbar.pack(side="right", fill="y")

        # --- Styling ---
        # Apply custom scrollbar width and initial font to checkboxes using ttk Styles.
        style = ttk.Style()
        try:
             # Attempt to use a theme that generally allows more customization.
             style.theme_use('clam') # Other options: 'alt', 'default', 'vista' (Windows)
        except tk.TclError:
             print("Warning: Could not set ttk theme 'clam'. Using default.")
        # Configure the style for vertical scrollbars.
        style.configure('Vertical.TScrollbar', width=self.scrollbar_width)
        # Configure the style for checkbuttons (will be refined in apply_color_scheme).
        style.configure('TCheckbutton', font=self.list_font)

        # --- Apply Initial Theme ---
        # Apply a random theme when the application first starts.
        self.apply_color_scheme(randomize=True)

    # -------------------------------------------------------------------------
    # Helper Methods for GUI Interaction
    # -------------------------------------------------------------------------
    def _on_configure_scrollable_frame(self, event):
        """Callback function when the scrollable_frame's size changes."""
        # Update the canvas's scrollable area to match the bounding box of all items inside it.
        self.script_canvas.configure(scrollregion=self.script_canvas.bbox("all"))
        # Optionally, resize the window holding the frame to match the canvas width
        # This helps if the frame is narrower than the canvas initially.
        # canvas_width = event.width # Or self.script_canvas.winfo_width()
        # self.script_canvas.itemconfig(self.script_canvas_window, width=canvas_width)

    def _on_mousewheel(self, event):
        """Handles mouse wheel scrolling events for the file list canvas."""
        # Platform-specific scroll handling:
        # Windows and macOS use event.delta (typically +/- 120 per wheel notch on Windows).
        # Linux often uses event.num (4 for up, 5 for down) for older bindings, but
        # modern Tk might use event.delta (often +/- 1).
        if platform.system() == 'Windows':
            delta = -1 * (event.delta // 120) # Divide by 120 for standard scroll units
        elif platform.system() == 'Darwin': # macOS
            delta = -1 * event.delta # macOS delta values are usually smaller, use directly
        else: # Linux and others
            # Prioritize delta if available (more modern)
            if hasattr(event, 'delta') and event.delta != 0:
                delta = -1 if event.delta > 0 else 1
            # Fallback to event.num if delta isn't useful
            elif event.num == 4:
                delta = -1 # Scroll Up
            elif event.num == 5:
                delta = 1  # Scroll Down
            else:
                delta = 0 # Unknown scroll event

        # Tell the canvas to scroll its view vertically by 'delta' units.
        self.script_canvas.yview_scroll(delta, "units")

    def update_clock(self):
        """Updates the clock label every second."""
        # Check if the clock_label widget exists (it might not during initial setup)
        if hasattr(self, 'clock_label') and self.clock_label and self.clock_label.winfo_exists():
             now = datetime.now().strftime("%Y-%m-%d %H:%M:%S") # Format the current time
             self.clock_label.config(text=now) # Update the label's text

        # Schedule this method to run again after 1000 milliseconds (1 second).
        # This creates the continuous update loop. Important: use self.master.after
        self.master.after(1000, self.update_clock)

    # -------------------------------------------------------------------------
    # Theme and Appearance Methods
    # -------------------------------------------------------------------------
    def apply_color_scheme(self, scheme=None, randomize=False):
        """
        Applies a color and font scheme to the application widgets.

        Args:
            scheme (dict, optional): A dictionary defining the theme
                                     (keys: 'bg', 'fg', 'button', 'button_fg', 'font').
                                     Defaults to None (uses current_scheme).
            randomize (bool, optional): If True, generates a random theme. Defaults to False.
        """
        if randomize:
            # --- Generate a Random Theme ---
            font_family = random.choice(self.available_fonts)
            font_size = random.randint(self.default_font_size - 2, self.default_font_size + 4)

            # Decide whether to use a predefined palette or fully random colors
            if random.random() < 0.7: # 70% chance of using a palette
                palette = random.choice(self.color_palettes)
                scheme = {
                    "bg": palette["bg"],
                    "fg": palette["fg"],
                    "button": palette["button"],
                    "button_fg": palette.get("button_fg", palette["fg"]), # Use specific button text color if defined
                    "font": (font_family, font_size)
                }
            else: # 30% chance of fully random colors
                scheme = {
                    "bg": self.random_color(),
                    "fg": self.random_color(),
                    "button": self.random_color(),
                    "button_fg": self.random_color(),
                    "font": (font_family, font_size)
                }
                # Very basic contrast check (heuristic) - try to ensure text is somewhat visible
                min_contrast_diff = 0x333333 # Arbitrary threshold
                while abs(int(scheme['fg'][1:], 16) - int(scheme['bg'][1:], 16)) < min_contrast_diff:
                     scheme['fg'] = self.random_color()
                while abs(int(scheme['button_fg'][1:], 16) - int(scheme['button'][1:], 16)) < min_contrast_diff:
                     scheme['button_fg'] = self.random_color()

        elif not scheme:
            # If no scheme provided, use the currently stored one
            scheme = self.current_scheme
            if not scheme: # Safety net: if no scheme exists yet, generate a random one
                print("Applying initial random scheme as none was set.")
                self.apply_color_scheme(randomize=True)
                return # Exit here, the recursive call will handle the rest

        # --- Store and Apply the Chosen Scheme ---
        self.current_scheme = scheme
        font_config = scheme["font"]
        # Derive button/list font sizes relative to the main font size in the theme
        button_font_config = (font_config[0], max(8, font_config[1] - 2), "bold") # Ensure minimum size 8
        list_font_config = (font_config[0], font_config[1])

        # --- Update Font Objects ---
        # Update the actual font objects used by widgets
        self.custom_font.configure(family=font_config[0], size=font_config[1])
        self.button_font.configure(family=button_font_config[0], size=button_font_config[1], weight=button_font_config[2])
        self.list_font.configure(family=list_font_config[0], size=list_font_config[1])

        # --- Apply Styles using ttk.Style ---
        # ttk widgets (Label, Frame, Checkbutton, Scrollbar) are styled primarily through the Style object.
        style = ttk.Style()
        # Configure the base style for all ttk widgets (can be overridden)
        style.configure('.', background=scheme["bg"], foreground=scheme["fg"], font=self.custom_font)
        style.configure('TFrame', background=scheme["bg"])
        style.configure('TLabel', background=scheme["bg"], foreground=scheme["fg"], font=self.custom_font) # Default Label style
        style.configure('TCheckbutton', background=scheme["bg"], foreground=scheme["fg"], font=self.list_font) # Checkbutton specific font
        # Map specific states (like 'selected', 'active') to colors for checkbuttons
        style.map('TCheckbutton',
                  indicatorcolor=[('selected', scheme["fg"]), ('!selected', scheme["fg"])], # Color of the check mark box
                  foreground=[('active', scheme["fg"])]) # Text color when hovered

        # Configure the scrollbar style
        style.configure('Vertical.TScrollbar',
                        troughcolor=scheme["bg"],      # Color of the scrollbar channel
                        background=scheme["button"],   # Color of the slider thumb
                        bordercolor=scheme["fg"],      # Border (might not be visible on all themes)
                        arrowcolor=scheme["fg"])       # Color of the arrows

        # --- Configure Specific Widgets ---
        # Configure the root window background
        self.master.configure(bg=scheme["bg"])
        # Ensure main frames use the TFrame style
        if self.frame: self.frame.configure(style='TFrame')
        if self.top_frame: self.top_frame.configure(style='TFrame')

        # Re-apply styles specifically to widgets in the top frame
        if self.top_frame:
             for widget in self.top_frame.winfo_children():
                 if isinstance(widget, ttk.Label):
                      # Ensure labels like the clock use the correct style and main font
                      widget.configure(style='TLabel', font=self.custom_font)
                 # tk.Button styling handled below

        # Configure tk.Button widgets (non-ttk) directly
        # These are styled individually, not primarily through ttk.Style.
        button_bg = scheme["button"]
        button_fg = scheme.get("button_fg", scheme["fg"]) # Use specific button text color if available
        active_bg = self.adjust_color(button_bg, -0.15) # Slightly darker background when pressed

        # Style the main action buttons
        for btn in self.buttons:
             if btn and btn.winfo_exists(): # Check if button exists
                 btn.configure(bg=button_bg, fg=button_fg, font=self.button_font,
                               activebackground=active_bg, # Color when button is clicked
                               activeforeground=button_fg) # Text color when button is clicked
        # Style the start/stop button
        if self.start_stop_button and self.start_stop_button.winfo_exists():
            self.start_stop_button.configure(bg=button_bg, fg=button_fg, font=self.button_font,
                                             activebackground=active_bg, activeforeground=button_fg)

        # Style the clock label (ttk) - Ensure it uses the updated Label style and font
        if self.clock_label and self.clock_label.winfo_exists():
            self.clock_label.configure(style='TLabel', font=self.custom_font)

        # Style the canvas background (non-ttk) and scrollable frame (ttk)
        if self.script_canvas: self.script_canvas.configure(bg=scheme["bg"])
        if self.scrollable_frame: self.scrollable_frame.configure(style='TFrame')

        # --- Refresh Checkboxes ---
        # If a directory is loaded, rebuild the checkboxes to fully apply the new theme/font.
        if self.directory:
            self.update_file_checkboxes()

    def adjust_color(self, color_hex, factor):
        """
        Adjusts the brightness of a hex color code.

        Args:
            color_hex (str): The color code (e.g., "#RRGGBB").
            factor (float): The adjustment factor. Negative values darken, positive lighten.
                            e.g., -0.1 makes it 10% darker, 0.2 makes it 20% lighter.

        Returns:
            str: The adjusted hex color code, or the original if input is invalid.
        """
        if not color_hex.startswith('#') or len(color_hex) != 7:
            return color_hex # Invalid format

        try:
            # Convert hex to RGB tuple
            rgb = tuple(int(color_hex[i:i+2], 16) for i in (1, 3, 5))
            # Adjust each component, clamping between 0 and 255
            new_rgb = tuple(max(0, min(255, int(c * (1 + factor)))) for c in rgb)
            # Convert back to hex
            return f"#{new_rgb[0]:02x}{new_rgb[1]:02x}{new_rgb[2]:02x}"
        except ValueError:
            return color_hex # Error during conversion

    def random_color(self):
        """Generates a random hex color code."""
        # Avoid pure black/white initially for potentially better default contrast.
        r = random.randint(20, 235)
        g = random.randint(20, 235)
        b = random.randint(20, 235)
        return f"#{r:02x}{g:02x}{b:02x}"

    def change_color_scheme(self):
        """Applies a new random color scheme when the 'Change Theme' button is clicked."""
        self.apply_color_scheme(randomize=True)

    def save_theme(self):
        """Saves the current color/font scheme to a JSON file."""
        if not self.current_scheme:
             messagebox.showwarning("Save Theme", "No theme is currently set to save.", parent=self.master)
             return

        # Ask user where to save the file
        file_path = filedialog.asksaveasfilename(
            parent=self.master,
            title="Save Theme As",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")]
        )
        if file_path: # If the user didn't cancel
            try:
                with open(file_path, 'w') as f:
                    # Dump the theme dictionary into the file as JSON
                    json.dump(self.current_scheme, f, indent=4) # indent=4 makes the file readable
                messagebox.showinfo("Save Theme", f"Theme saved successfully to:\n{file_path}", parent=self.master)
            except Exception as e:
                 messagebox.showerror("Save Theme Error", f"Could not save theme:\n{e}", parent=self.master)

    def load_theme(self):
        """Loads a color/font scheme from a JSON file."""
        # Ask user which file to load
        file_path = filedialog.askopenfilename(
            parent=self.master,
            title="Load Theme From",
            filetypes=[("JSON files", "*.json")]
        )
        if file_path: # If the user didn't cancel
            try:
                with open(file_path, 'r') as f:
                    # Load the dictionary from the JSON file
                    scheme = json.load(f)

                # --- Basic Validation ---
                # Check if it looks like a valid theme dictionary
                if not isinstance(scheme, dict) or not all(k in scheme for k in ["bg", "fg", "button", "font"]):
                     raise ValueError("Invalid theme file format. Missing required keys.")
                # Ensure font is a tuple (JSON loads lists, Tkinter needs tuples for fonts)
                if isinstance(scheme["font"], list):
                     scheme["font"] = tuple(scheme["font"])
                if not isinstance(scheme["font"], tuple) or len(scheme["font"]) != 2:
                     raise ValueError("Invalid font format in theme file. Expected [family, size].")

                # Apply the loaded scheme
                self.apply_color_scheme(scheme=scheme)
                messagebox.showinfo("Load Theme", f"Theme loaded successfully from:\n{file_path}", parent=self.master)

            except json.JSONDecodeError as e:
                 messagebox.showerror("Load Theme Error", f"Invalid JSON file:\n{e}", parent=self.master)
            except ValueError as e:
                 messagebox.showerror("Load Theme Error", f"Invalid theme data:\n{e}", parent=self.master)
            except Exception as e:
                 messagebox.showerror("Load Theme Error", f"Could not load theme:\n{e}", parent=self.master)

    # -------------------------------------------------------------------------
    # Directory and File Handling Methods
    # -------------------------------------------------------------------------
    def select_directory(self):
        """Opens a dialog to select a directory and scans it for supported files."""
        # Ask the user to choose a directory.
        new_directory = filedialog.askdirectory(parent=self.master, title="Select Directory Containing Files")
        if new_directory: # If a directory was selected (not cancelled)
            self.directory = new_directory
            # Update window title to show the selected directory name
            self.master.title(f"GREG SEYMOUR AI - [{os.path.basename(self.directory)}]")
            print(f"Directory selected: {self.directory}")
            self.scan_directory() # Scan the new directory for files
        else:
             print("Directory selection cancelled.")

    def scan_directory(self):
        """Scans the currently selected directory for supported file types."""
        if not self.directory or not os.path.isdir(self.directory):
             print("Scan aborted: No valid directory selected.")
             self.scripts_and_files = [] # Clear the list if directory is invalid
             self.update_file_checkboxes() # Update the display (will show "No files")
             return

        print(f"Scanning directory: {self.directory}")
        # Define the file extensions we are interested in
        supported_extensions = ('.py', '.html', '.htm', '.mp3', '.wav', '.ogg', '.mp4', '.avi', '.mov', '.mkv', '.jpg', '.jpeg', '.png', '.gif', '.bmp') # Added image types

        try:
             all_items = os.listdir(self.directory) # Get all items (files and folders) in the directory
             # Filter the list: keep only files with supported extensions, ignore temp files
             self.scripts_and_files = sorted([
                 item for item in all_items
                 if os.path.isfile(os.path.join(self.directory, item)) # Check if it's actually a file
                 and item.lower().endswith(supported_extensions)     # Check the extension
                 and not item.startswith('~')                        # Ignore temporary files (optional)
             ])
             print(f"Found {len(self.scripts_and_files)} supported files.")
        except OSError as e:
            messagebox.showerror("Directory Error", f"Error accessing directory contents:\n{e}", parent=self.master)
            self.scripts_and_files = [] # Clear list on error

        # Update the GUI list of checkboxes
        self.update_file_checkboxes()

    def update_file_checkboxes(self):
        """Clears and rebuilds the list of file checkboxes in the scrollable frame."""
        # Ensure the container frame exists before trying to modify it
        if not hasattr(self, 'scrollable_frame') or not self.scrollable_frame:
            print("Error: Cannot update checkboxes, scrollable frame not initialized.")
            return

        # --- Clear Old Checkboxes ---
        # Destroy all existing widgets inside the scrollable frame.
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        # --- Reset Variables ---
        self.file_vars = [] # Clear the list holding the checkbox variables

        # --- Display Message if No Files ---
        if not self.scripts_and_files:
             # Get theme colors safely, providing defaults if theme isn't set yet
             bg_color = self.current_scheme['bg'] if self.current_scheme else 'SystemButtonFace'
             fg_color = self.current_scheme['fg'] if self.current_scheme else 'SystemButtonText'
             # Show a label indicating no files were found
             ttk.Label(self.scrollable_frame, text="No supported files found in selected directory.",
                       font=self.list_font, background=bg_color, foreground=fg_color, wraplength=self.master.winfo_width()-50).pack(padx=10, pady=20) # Added wrap
        else:
            # --- Create New Checkboxes ---
            # Determine number of columns based on window width (heuristic)
            num_columns = max(1, (self.master.winfo_width() - self.scrollbar_width - 40) // 300) # Approx 300px per column

            # Define a specific ttk style for these checkboxes using current theme colors/fonts
            style = ttk.Style()
            cb_style_name = 'File.TCheckbutton'
            cb_bg = self.current_scheme['bg']
            cb_fg = self.current_scheme['fg']
            style.configure(cb_style_name, font=self.list_font, background=cb_bg, foreground=cb_fg)
            # Map states for better visual feedback (optional, but good practice)
            style.map(cb_style_name,
                      indicatorcolor=[('selected', cb_fg), ('!selected', cb_fg), ('active', cb_fg)],
                      foreground=[('active', cb_fg), ('!active', cb_fg)],
                      background=[('active', cb_bg), ('!active', cb_bg)])

            # Create a checkbutton for each file
            for i, file_name in enumerate(self.scripts_and_files):
                # Create a Tkinter variable to hold the checkbox state (checked/unchecked)
                var = tk.BooleanVar()
                self.file_vars.append(var) # Store the variable

                # Calculate grid position (row, column)
                row = i // num_columns
                col = i % num_columns

                # Create the Checkbutton widget
                cb = ttk.Checkbutton(self.scrollable_frame, text=file_name, variable=var,
                                     onvalue=True, offvalue=False, # Values when checked/unchecked
                                     style=cb_style_name,      # Apply the custom style
                                     takefocus=0)              # Prevent ugly focus rectangle
                # Place the checkbox in the grid
                cb.grid(row=row, column=col, sticky="w", padx=5, pady=3) # sticky="w" aligns text left

                # --- Bind Events to Checkbox ---
                # Double-click: Launch the single file immediately
                cb.bind("<Double-1>", lambda event, f=file_name: self.launch_single_file(f))
                # MouseWheel: Allow scrolling even when the mouse is directly over a checkbox
                cb.bind("<MouseWheel>", self._on_mousewheel)

            # Configure column weights for resizing (optional, set weight=0 for fixed width based on content)
            # for c in range(num_columns):
            #      self.scrollable_frame.columnconfigure(c, weight=1) # Give columns equal weight to expand

        # --- Update Scroll Region ---
        # Crucial: After adding/removing widgets, update the scrollable region of the canvas.
        self.scrollable_frame.update_idletasks() # Ensure Tkinter processes geometry changes first
        self.script_canvas.configure(scrollregion=self.script_canvas.bbox("all"))
        # Make the frame width match the canvas width initially if needed
        # self.script_canvas.itemconfig(self.script_canvas_window, width=self.script_canvas.winfo_width())


    def launch_single_file(self, file_name):
        """Launches a single specified file immediately (e.g., on double-click)."""
        if not self.directory:
            messagebox.showwarning("Launch Error", "Cannot launch file - No base directory selected.", parent=self.master)
            return
        print(f"Double-click launch requested for: {file_name}")
        # Call the main launch function. Duration is irrelevant for single launch.
        self.launch_file(file_name, duration=None)


    # -------------------------------------------------------------------------
    # Selection Management Methods (Checkboxes)
    # -------------------------------------------------------------------------
    def select_all(self):
        """Checks all file checkboxes."""
        print("Selecting all files.")
        for var in self.file_vars:
            var.set(True) # Set the BooleanVar associated with each checkbox to True

    def select_none(self):
        """Unchecks all file checkboxes."""
        print("Deselecting all files.")
        for var in self.file_vars:
            var.set(False) # Set the BooleanVar to False

    def save_selection(self):
        """Saves the names of currently checked files to a text file."""
        if not self.directory:
             messagebox.showwarning("Save Selection", "No directory is selected.", parent=self.master)
             return

        # Ask user for the save file name and location
        file_path = filedialog.asksaveasfilename(
            parent=self.master,
            title="Save Selection List As",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt")],
            initialdir=self.directory # Suggest saving in the current directory
        )
        if file_path:
            # Get a list of filenames corresponding to checked boxes
            selected_files = [
                file_name for file_name, var in zip(self.scripts_and_files, self.file_vars) if var.get()
            ]
            print(f"Saving {len(selected_files)} selected filenames to: {file_path}")
            try:
                with open(file_path, 'w') as f:
                    # Write each selected filename on a new line
                    f.write("\n".join(selected_files))
                messagebox.showinfo("Save Selection", f"Saved {len(selected_files)} selected file names to\n{file_path}", parent=self.master)
            except Exception as e:
                 messagebox.showerror("Save Error", f"Could not save selection list:\n{e}", parent=self.master)

    def load_selection(self):
        """Loads a list of filenames from a text file and checks the corresponding checkboxes."""
        if not self.directory:
             messagebox.showwarning("Load Selection", "Please select a directory first.", parent=self.master)
             return

        # Ask user for the file to load
        file_path = filedialog.askopenfilename(
            parent=self.master,
            title="Load Selection List From",
            filetypes=[("Text files", "*.txt")],
            initialdir=self.directory # Suggest looking in the current directory
        )
        if file_path:
            try:
                with open(file_path, 'r') as f:
                    # Read all lines, strip whitespace, ignore empty lines, and store in a set for fast lookup
                    selected_files_to_load = {line.strip() for line in f if line.strip()}
                print(f"Loading selection from: {file_path}. Found {len(selected_files_to_load)} names in file.")

                loaded_count = 0
                not_found_count = 0
                files_in_dir = set(self.scripts_and_files) # Set of files currently listed

                # Iterate through the checkboxes/files currently displayed
                for file_name, var in zip(self.scripts_and_files, self.file_vars):
                    # Check the box if the file name was in the loaded set
                    if file_name in selected_files_to_load:
                        var.set(True)
                        loaded_count += 1
                    else:
                        var.set(False) # Uncheck if not in the loaded list

                # Check for files listed in the load file but not found in the current directory
                not_found_names = selected_files_to_load - files_in_dir
                if not_found_names:
                     not_found_count = len(not_found_names)
                     print(f"Warning: {not_found_count} files from the list were not found in the current directory: {', '.join(list(not_found_names)[:5])}{'...' if not_found_count > 5 else ''}")


                message = f"Loaded selection from\n{file_path}\n\n"
                message += f"{loaded_count} files were checked."
                if not_found_count > 0:
                    message += f"\n{not_found_count} file(s) from the list were not found in the current directory."
                messagebox.showinfo("Load Selection", message, parent=self.master)

            except Exception as e:
                messagebox.showerror("Load Error", f"Could not load selection list:\n{e}", parent=self.master)

    # -------------------------------------------------------------------------
    # Main Execution Logic (Looping and File Launching)
    # -------------------------------------------------------------------------
    def toggle_running_loop(self):
        """Starts or stops the 'Run Selected Loop'."""
        if self.running_loop:
            # --- Stop the Loop ---
            print("Stop button clicked. Stopping the loop...")
            self.running_loop = False # Set the flag to signal the loop thread to stop
            if self.start_stop_button: self.start_stop_button.config(text="Start Loop") # Update button text
            self.current_script.set("Loop stopping...") # Update status label

            # Terminate the currently running Python process (if any) started by the loop
            if self.current_process and self.current_process.poll() is None: # Check if process exists and is running
                pid = self.current_process.pid
                print(f"Terminating active Python process PID {pid}...")
                try:
                    self.current_process.terminate() # Ask nicely first (SIGTERM)
                    try:
                        # Wait briefly to see if it terminates gracefully
                        self.current_process.wait(timeout=0.5)
                        print(f"Process {pid} terminated gracefully.")
                    except subprocess.TimeoutExpired:
                        # If it didn't terminate, force kill it (SIGKILL)
                        print(f"Process {pid} did not terminate, forcing kill...")
                        self.current_process.kill()
                        print(f"Process {pid} killed.")
                except ProcessLookupError:
                    print(f"Process {pid} already terminated.") # Process died before we could kill it
                except Exception as e:
                    print(f"Error terminating process {pid}: {e}")
            self.current_process = None # Clear the reference
            # Final status update after attempting termination
            self.master.after(100, lambda: self.current_script.set("Loop stopped."))

        else:
            # --- Start the Loop ---
            # This button only toggles the state; the actual start logic
            # is initiated by the "Run Selected Loop" button which asks for duration.
            # We call that button's function here.
            self.run_selected_loop()

    def run_selected_loop(self):
        """Initiates the process of running selected files in a loop."""
        if self.running_loop:
            messagebox.showinfo("Already Running", "The loop is already running. Stop it first to restart.", parent=self.master)
            return

        # Get the list of currently checked files
        selected_files = [file for file, var in zip(self.scripts_and_files, self.file_vars) if var.get()]
        if not selected_files:
            messagebox.showinfo("No Selection", "No files selected.\nPlease check the boxes next to the files you want to include in the loop.", parent=self.master)
            return

        # --- Ask User for Python Script Duration ---
        # Use simpledialog to get an integer input from the user.
        duration = simpledialog.askinteger(
            "Script Duration",
            "Enter duration (in seconds) for EACH Python script.\n"
            "(0 or less = run until next file or loop stops)\n\n"
            "Other files (HTML, MP4, etc.) will just be opened.",
            parent=self.master,
            minvalue=0,      # Minimum allowed value
            initialvalue=30 # Default value shown in the dialog
        )

        # If the user cancels the dialog, duration will be None
        if duration is None:
            print("Loop start cancelled by user (duration dialog).")
            return

        # --- Start the Loop in a Background Thread ---
        self.running_loop = True # Set the flag
        if self.start_stop_button: self.start_stop_button.config(text="Stop Loop") # Update button text
        print(f"Starting loop with {len(selected_files)} files. Python script duration: {duration if duration > 0 else 'unlimited'}.")

        # Create and start a new Thread.
        # target: The function the thread should execute (_run_loop_thread).
        # args: A tuple of arguments to pass to the target function.
        # daemon=True: Allows the main program to exit even if this thread is still running.
        loop_thread = threading.Thread(target=self._run_loop_thread, args=(selected_files, duration), daemon=True)
        loop_thread.start()

    def _run_loop_thread(self, selected_files, duration):
        """
        The function executed by the background thread to loop through selected files.
        *** Never directly update Tkinter GUI elements from this thread! Use self.master.after(). ***
        """
        print(f"Loop thread started (ID: {threading.current_thread().ident}).")
        effective_duration = duration if duration is not None and duration > 0 else None # Use None for no timeout

        while self.running_loop: # Keep looping as long as the flag is True
            print("--- Starting new loop cycle ---")
            # Shuffle a copy of the list for random order in each cycle
            current_cycle_files = list(selected_files)
            random.shuffle(current_cycle_files)

            for file_name in current_cycle_files:
                # --- Check if Stop Requested ---
                if not self.running_loop:
                    print("Loop flag turned off during cycle, breaking inner loop.")
                    break # Exit the inner 'for' loop

                # --- Safety Check: Directory Still Valid? ---
                if not self.directory or not os.path.isdir(self.directory):
                     print("Error: Loop directory seems invalid. Stopping loop.")
                     # Use 'after' to safely update GUI from main thread
                     self.master.after(0, lambda: messagebox.showerror("Loop Error", "The selected directory is no longer valid. Loop stopped.", parent=self.master))
                     self.running_loop = False # Set flag to stop outer loop too
                     break

                # --- Launch File ---
                print(f"Loop: Launching '{file_name}'")
                # Schedule GUI update (status label) on the main thread using lambda to capture current file_name
                self.master.after(0, lambda f=file_name: self.current_script.set(f"Running: {f}"))
                # Call the function that actually runs/opens the file
                self.launch_file(file_name, effective_duration) # This might block for python scripts with duration!

                # --- Check Again and Pause ---
                if not self.running_loop:
                    print("Loop flag turned off after launch_file, breaking inner loop.")
                    break # Exit the inner 'for' loop

                # Add a small delay *after* launching the file.
                # This prevents extremely rapid switching, especially for files opened by webbrowser
                # or Python scripts without a timeout (which return control immediately).
                if not file_name.lower().endswith('.py') or effective_duration is None:
                    # Longer delay for instantly opened files or background python scripts
                    sleep_time = 1.5
                else:
                    # Shorter delay after a python script with a timeout finished or was killed
                    sleep_time = 0.3
                print(f"Loop: Pausing for {sleep_time}s...")
                time.sleep(sleep_time)

            # --- End of Cycle ---
            if self.running_loop:
                print("--- Loop cycle finished ---")
                # Optional: Add a longer pause between full cycles
                # time.sleep(5)

        # --- Loop Finished ---
        print(f"Loop thread finished (ID: {threading.current_thread().ident}).")
        # Schedule the GUI cleanup function to run on the main thread.
        self.master.after(0, self._loop_finished)

    def _loop_finished(self):
        """Safely updates the GUI when the background loop thread ends or is stopped."""
        print("Executing _loop_finished on main thread.")
        self.running_loop = False # Ensure flag is False
        # Check if widgets still exist before configuring them (window might be closing)
        if self.start_stop_button and self.start_stop_button.winfo_exists():
             self.start_stop_button.config(text="Start Loop")
        # Use try-except for StringVar access as root window might be destroyed
        try:
             if self.current_script.get() not in ["Loop stopped.", "Loop stopping..."]:
                 self.current_script.set("Loop finished.")
        except tk.TclError:
             print("Warning: Could not update status label (window likely closed).")
        self.current_process = None # Clear any lingering process reference

    def launch_file(self, file_name, duration):
        """
        Handles the actual execution or opening of a single file based on its type.
        This can be called directly (double-click) or from the loop thread.

        Args:
            file_name (str): The name of the file (without the directory path).
            duration (int | None): The timeout in seconds for Python scripts.
                                   None means no timeout. Ignored for other file types.
        """
        full_path = os.path.join(self.directory, file_name)

        # --- File Existence Check ---
        if not os.path.exists(full_path):
            # If called from loop thread, show error via main thread
            error_msg = f"File not found: {file_name}\nPath: {full_path}"
            print(f"Error: {error_msg}")
            self.master.after(0, lambda msg=error_msg: messagebox.showerror("Launch Error", msg, parent=self.master))
            self.master.after(0, lambda f=file_name: self.current_script.set(f"Error: Not found '{f}'"))
            return

        # --- Determine File Type ---
        _, extension = os.path.splitext(file_name)
        extension = extension.lower() # Normalize to lowercase

        # --- Launch Logic ---
        try:
            # --- Python Scripts (.py) ---
            if extension == '.py':
                # Terminate any previous Python script *managed by this loop* that might still be running
                if self.current_process and self.current_process.poll() is None:
                    prev_pid = self.current_process.pid
                    print(f"Terminating previous Python process PID {prev_pid} before launching '{file_name}'...")
                    try:
                        self.current_process.terminate()
                        self.current_process.wait(timeout=0.5)
                    except (ProcessLookupError, subprocess.TimeoutExpired, Exception) as term_e:
                        print(f"Info: Issue terminating previous process PID {prev_pid}: {term_e}")
                        if self.current_process.poll() is None: self.current_process.kill() # Force kill if needed
                    self.current_process = None # Clear reference anyway

                # Prepare to run the script
                python_exe = 'python' # Assume 'python' is in PATH
                cmd = [python_exe, full_path]
                print(f"Executing: {' '.join(cmd)} (Timeout: {duration if duration else 'None'})")

                # Use subprocess.Popen for non-blocking execution initially.
                # creationflags hides the console window on Windows.
                creationflags = 0
                if platform.system() == "Windows":
                     creationflags = subprocess.CREATE_NO_WINDOW # Value is 0x08000000

                self.current_process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE, # Capture standard output
                    stderr=subprocess.PIPE, # Capture standard error
                    creationflags=creationflags,
                    text=True, # Decode stdout/stderr as text (Python 3.7+)
                    encoding='utf-8', errors='replace' # Specify encoding
                )
                print(f"Launched '{file_name}' with PID: {self.current_process.pid}")

                # --- Handle Timeout (if duration is set) ---
                if duration is not None and duration > 0:
                    try:
                        # communicate() waits for the process to finish OR the timeout occurs.
                        # This call WILL BLOCK the current thread (the loop thread) for 'duration' seconds.
                        stdout, stderr = self.current_process.communicate(timeout=duration)
                        exit_code = self.current_process.returncode # Get exit code *after* communicate
                        print(f"Script '{file_name}' finished within timeout ({duration}s). Exit code: {exit_code}")
                        if stderr: print(f"Stderr from '{file_name}':\n---\n{stderr.strip()}\n---")
                        # if stdout: print(f"Stdout from '{file_name}':\n---\n{stdout.strip()}\n---") # Optional: show output
                        self.current_process = None # Process finished, clear reference

                    except subprocess.TimeoutExpired:
                        # Timeout occurred! Terminate the process.
                        # Check if the main loop is still supposed to be running.
                        if self.running_loop:
                            print(f"Script '{file_name}' (PID: {self.current_process.pid}) exceeded timeout ({duration}s). Terminating...")
                            self.current_process.terminate()
                            try: self.current_process.wait(timeout=0.5)
                            except: pass # Ignore errors during forced wait
                            if self.current_process.poll() is None: self.current_process.kill() # Force kill
                            print(f"Script '{file_name}' terminated due to timeout.")
                            # Update status label via main thread
                            self.master.after(0, lambda f=file_name: self.current_script.set(f"Timeout: '{f}'"))
                        else:
                            # Loop was stopped while waiting for timeout, just clean up
                            print(f"Script '{file_name}' timeout occurred, but loop already stopping.")
                            if self.current_process.poll() is None: self.current_process.kill()
                        self.current_process = None # Clear reference

                    except Exception as comm_e:
                        # Handle potential errors during communicate() itself
                        print(f"Error communicating with script '{file_name}': {comm_e}")
                        self.master.after(0, lambda f=file_name: self.current_script.set(f"Comm Error: '{f}'"))
                        if self.current_process and self.current_process.poll() is None:
                            self.current_process.kill() # Kill if communication failed
                        self.current_process = None

                # else: (No duration specified)
                    # The script was launched via Popen and is running in the background.
                    # self.current_process holds the reference. It will run until it finishes
                    # on its own, or until the loop stops it, or the next .py script starts.

            # --- Other Supported Files (HTML, Media, Images) ---
            elif extension in ['.html', '.htm', '.mp3', '.wav', '.ogg', '.mp4', '.avi', '.mov', '.mkv', '.jpg', '.jpeg', '.png', '.gif', '.bmp']:
                # Use webbrowser.open() to open these files with the default system application.
                print(f"Opening '{file_name}' with default application.")
                # Construct a 'file:///' URI. Replace spaces for compatibility.
                file_uri = f"file:///{os.path.abspath(full_path).replace(' ', '%20')}"
                try:
                    success = webbrowser.open(file_uri)
                    if not success:
                         print(f"Warning: webbrowser.open() reported it might not have found an application for '{file_name}'.")
                except Exception as wb_e:
                    print(f"Error using webbrowser.open for '{file_name}': {wb_e}")
                    self.master.after(0, lambda f=file_name, e=str(wb_e): messagebox.showerror("Launch Error", f"Could not open '{f}' with default application:\n{e}", parent=self.master))

                # Update status label via main thread after a short delay
                self.master.after(100, lambda f=file_name: self.current_script.set(f"Opened: '{f}'"))
                # Don't clear self.current_process here, as a Python script might still be running in the background.

            # --- Unsupported Files ---
            else:
                print(f"Unsupported file type: '{extension}' for file '{file_name}'")
                self.master.after(0, lambda f=file_name: self.current_script.set(f"Unsupported: '{f}'"))

        # --- General Error Handling ---
        except FileNotFoundError as fnf_err:
             # Specifically handle if 'python' command isn't found
             if 'python' in str(fnf_err):
                  err_msg = f"Could not find Python executable.\nEnsure Python is installed and in your system's PATH.\nError: {fnf_err}"
                  print(f"Error: {err_msg}")
                  self.master.after(0, lambda msg=err_msg: messagebox.showerror("Python Error", msg, parent=self.master))
                  self.master.after(0, self.current_script.set("Error: Python not found"))
                  # Stop the loop if Python is essential and missing
                  if self.running_loop:
                       print("Stopping loop because Python executable was not found.")
                       self.running_loop = False
                       self.master.after(100, self._loop_finished) # Schedule cleanup
             else:
                  # FileNotFoundError for the script file itself (should be caught earlier, but safety check)
                  err_msg = f"File not found during launch attempt:\n{fnf_err}"
                  print(f"Error: {err_msg}")
                  self.master.after(0, lambda msg=err_msg: messagebox.showerror("Launch Error", msg, parent=self.master))
                  self.master.after(0, lambda f=file_name: self.current_script.set(f"Error: Not found '{f}'"))

        except Exception as launch_e:
            # Catch any other unexpected errors during launch
            err_msg = f"An unexpected error occurred launching '{file_name}':\n{launch_e}"
            print(f"Error: {err_msg}")
            self.master.after(0, lambda msg=err_msg: messagebox.showerror("Launch Error", msg, parent=self.master))
            self.master.after(0, lambda f=file_name: self.current_script.set(f"Error launching: '{f}'"))
            # Attempt to kill the process if it exists and seems to be running after the error
            if self.current_process and self.current_process.poll() is None:
                 try:
                      print(f"Killing process PID {self.current_process.pid} due to launch error.")
                      self.current_process.kill()
                 except Exception as kill_e:
                      print(f"Warning: Failed to kill process during error handling: {kill_e}")
            self.current_process = None # Clear reference after error

    # -------------------------------------------------------------------------
    # Specific Button Action Methods
    # -------------------------------------------------------------------------
    def display_images_html(self):
        """Handles the 'Display Images (HTML)' button click."""
        print("Display Images (HTML) button clicked.")
        # Guess the initial directory: current selection or script's location
        initial_dir = self.directory if self.directory else os.path.dirname(os.path.abspath(__file__))

        # Ask user to select the specific HTML file responsible for the slideshow
        html_path = filedialog.askopenfilename(
            parent=self.master,
            title=f"Select Slideshow HTML File (e.g., {self.slideshow_html_path})",
            filetypes=[("HTML files", "*.html *.htm")],
            initialdir=initial_dir
        )
        if html_path:
            print(f"Attempting to open slideshow HTML: {html_path}")
            try:
                # Open the HTML file in the default web browser
                webbrowser.open(f"file:///{os.path.abspath(html_path).replace(' ', '%20')}")
                self.current_script.set(f"Opened Slideshow: {os.path.basename(html_path)}")
            except Exception as e:
                 messagebox.showerror("Error Opening HTML", f"Could not open the slideshow HTML file:\n{e}", parent=self.master)
        else:
             print("Slideshow HTML selection cancelled.")

    def play_mp4s_external(self):
        """Handles the 'Play MP4s (External)' button click."""
        print("Play MP4s (External) button clicked.")

        # --- Locate the External Looping Script ---
        script_dir = os.path.dirname(os.path.abspath(__file__)) # Directory of this main script
        script_path_in_script_dir = os.path.join(script_dir, self.loop_videos_script_path)
        script_path_in_current_dir = os.path.join(self.directory, self.loop_videos_script_path) if self.directory else None

        found_script_path = None
        if os.path.exists(script_path_in_script_dir):
            found_script_path = script_path_in_script_dir
        elif script_path_in_current_dir and os.path.exists(script_path_in_current_dir):
            found_script_path = script_path_in_current_dir

        if not found_script_path:
             messagebox.showerror(
                 "Script Not Found",
                 f"The video looping script '{self.loop_videos_script_path}' was not found.\n\n"
                 f"Please place it either in the application's directory:\n{script_dir}\n\n"
                 f"OR in the currently selected media directory:\n{self.directory or '(No directory selected)'}",
                 parent=self.master
             )
             return

        # --- Select Directory Containing Videos ---
        video_directory = filedialog.askdirectory(
            parent=self.master,
            title="Select Directory Containing MP4/Video Files",
            initialdir=self.directory if self.directory else None # Start in last used directory
        )
        if not video_directory:
            print("Video directory selection cancelled.")
            return

        # --- Check if Directory Contains Videos (Basic Check) ---
        try:
             # Look for common video extensions
             video_extensions = ('.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv')
             has_videos = any(f.lower().endswith(video_extensions) for f in os.listdir(video_directory))
             if not has_videos:
                 messagebox.showwarning("No Videos Found", f"No files with common video extensions ({', '.join(video_extensions)}) were found in the selected directory:\n{video_directory}", parent=self.master)
                 # Optionally allow proceeding anyway? For now, we return.
                 return
        except OSError as e:
            messagebox.showerror("Directory Error", f"Could not read the contents of the video directory:\n{e}", parent=self.master)
            return

        # --- Run the External Script ---
        cmd = ['python', found_script_path, video_directory]
        print(f"Running external video script: {' '.join(cmd)}")
        self.current_script.set(f"Starting: {self.loop_videos_script_path}")

        try:
            # Run using Popen for non-blocking execution
            creationflags = 0
            if platform.system() == "Windows":
                 creationflags = subprocess.CREATE_NO_WINDOW # Hide console

            # Run the script. We don't store this in self.current_process because
            # it's a separate utility, not part of the main file loop.
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                creationflags=creationflags,
                text=True, encoding='utf-8', errors='replace'
            )
            print(f"Launched external script '{self.loop_videos_script_path}' with PID: {process.pid}")

            # Monitor the external script in a separate thread to show its output/errors when done.
            monitor_thread = threading.Thread(target=self._monitor_external_script, args=(process, self.loop_videos_script_path), daemon=True)
            monitor_thread.start()

        except FileNotFoundError:
            messagebox.showerror("Python Error", "Could not find Python executable.\nEnsure Python is installed and in your system's PATH.", parent=self.master)
            self.current_script.set("Error: Python not found")
        except Exception as e:
            messagebox.showerror("Script Error", f"Failed to run '{self.loop_videos_script_path}':\n{e}", parent=self.master)
            self.current_script.set(f"Error running ext. script")

    def _monitor_external_script(self, process, script_name):
         """
         Waits for the external script process to complete and prints its output/errors.
         Runs in a background thread.
         """
         print(f"Monitoring external script '{script_name}' (PID: {process.pid})...")
         try:
              # communicate() waits for the process to finish and captures all output.
              stdout, stderr = process.communicate()
              retcode = process.returncode # Get the exit code
              print(f"External script '{script_name}' (PID: {process.pid}) finished with exit code {retcode}.")

              # Print output/errors, especially if there was an error (non-zero exit code)
              if retcode != 0 or stderr:
                   print(f"--- Output from '{script_name}' ---")
                   if stdout: print(f"Stdout:\n{stdout.strip()}")
                   if stderr: print(f"Stderr:\n{stderr.strip()}")
                   print(f"--- End Output ---")
                   # Optionally show a message box on the main thread if there was an error
                   # self.master.after(0, lambda: messagebox.showwarning("External Script Error", f"'{script_name}' finished with error code {retcode}.\nSee console for details.", parent=self.master))

         except Exception as e:
              print(f"Error monitoring external script '{script_name}': {e}")

    def edit_in_notepad(self):
        """Handles the 'Edit in Notepad' button click."""
        print("Edit in Notepad button clicked.")
        if not self.directory:
             messagebox.showwarning("Edit File", "Please select a directory first to browse for a file.", parent=self.master)
             return

        # Ask user to select a file, suggesting text-based types
        file_path = filedialog.askopenfilename(
            parent=self.master,
            title="Select File to Edit",
            initialdir=self.directory,
            filetypes=[("Text Files", "*.py *.html *.htm *.txt *.json *.css *.js"), ("All Files", "*.*")]
        )

        if file_path:
            print(f"Attempting to open '{os.path.basename(file_path)}' for editing.")
            try:
                if platform.system() == "Windows":
                    # Use os.startfile with 'edit' verb on Windows - often opens in Notepad/default text editor
                    os.startfile(file_path, 'edit')
                elif platform.system() == "Darwin": # macOS
                     subprocess.Popen(['open', '-t', file_path]) # '-t' flag usually forces default text editor
                elif platform.system() == "Linux":
                     # Try xdg-open first (common Linux desktop standard)
                     try:
                          subprocess.Popen(['xdg-open', file_path])
                     except FileNotFoundError:
                          # Fallback: try to find common editors if xdg-open fails
                          found_editor = False
                          for editor in ['gedit', 'kate', 'mousepad', 'pluma', 'nano', 'vim']: # Add more if needed
                               try:
                                    subprocess.Popen([editor, file_path])
                                    found_editor = True
                                    print(f"Opened with {editor}.")
                                    break
                               except FileNotFoundError:
                                    continue
                          if not found_editor:
                               messagebox.showerror("Editor Error", "Could not find a default text editor (xdg-open failed). Please install one (like gedit, kate) or configure mime types.", parent=self.master)
                               return # Stop if no editor found
                else: # Other OS - fallback to webbrowser (might not work for editing)
                     webbrowser.open(f"file:///{os.path.abspath(file_path).replace(' ', '%20')}")

                self.current_script.set(f"Editing: {os.path.basename(file_path)}")

            except OSError as e:
                 # Handle specific errors like Notepad/editor not found or permission issues
                 messagebox.showerror("Editor Error", f"Could not open file for editing:\n{e}", parent=self.master)
            except Exception as e:
                 messagebox.showerror("Editor Error", f"An unexpected error occurred:\n{e}", parent=self.master)

    def manage_scripts(self):
        """Placeholder for future script management functionality."""
        # This is currently mapped to the __init__ method in the button setup, which is incorrect.
        # It should likely be removed or implemented. For now, show an info message.
        messagebox.showinfo("Manage Files", "File management features (delete, rename, etc.) are not yet implemented.", parent=self.master)

# =============================================================================
# Main Execution Block - Runs when the script is executed directly
# =============================================================================
if __name__ == "__main__":
    # This block ensures the code runs only when the script is the main program,
    # not when it's imported as a module into another script.

    # --- Create the Root Window ---
    root = tk.Tk() # Create the main application window

    # --- DPI Awareness (Windows Specific) ---
    # Improves rendering sharpness on high-resolution displays on Windows 8.1+.
    try:
        from ctypes import windll
        # Set the process DPI awareness context. Value 1 corresponds to PROCESS_SYSTEM_DPI_AWARE.
        windll.shcore.SetProcessDpiAwareness(1)
        print("DPI Awareness set (Windows).")
    except ImportError:
        print("Info: 'ctypes' module not found. Cannot set DPI awareness (non-Windows or old Python?).")
    except AttributeError:
        print("Info: Cannot set DPI awareness (likely not Windows 8.1+).")
    except Exception as e:
        print(f"Warning: Error setting DPI awareness: {e}")

    # --- Create an Instance of the GUI Class ---
    # This creates the ScriptRunnerGUI object and runs its __init__ method,
    # which in turn calls setup_gui() to build the interface.
    app = ScriptRunnerGUI(root)

    # --- Start the Tkinter Event Loop ---
    # This crucial line starts Tkinter's main loop. It makes the window visible
    # and responsive, listening for events (button clicks, mouse movements, etc.)
    # and dispatching them to the appropriate handlers (like button commands).
    # The program will stay in this loop until the main window is closed.
    root.mainloop()

    print("Application Exited.") # This line will run after the main window is closed.