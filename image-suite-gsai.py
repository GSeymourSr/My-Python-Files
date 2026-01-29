# --- START OF REWRITTEN FILE: image_processor_suite.py ---

# ==============================================================================
# Image Processor Suite
# ==============================================================================
# Description:
#   A comprehensive Tkinter GUI application for batch image processing.
#   Combines functionalities for resizing, flipping, rotating, upscaling
#   (with Real-ESRGAN), background removal (with rembg), and cropping.
#
# Author: Greg Seymour AI (Concept & Integration by AI)
# Date:   October 27, 2023 (Revised)
# Version: 1.2
#
# Dependencies:
#   - Python 3.x
#   - Pillow (PIL fork): Image manipulation library
#       pip install Pillow
#   - rembg: Background removal tool
#       pip install rembg
#   - realesrgan (Optional): AI image upscaling
#       pip install realesrgan
#   - torch (Required by realesrgan)
#       Installation depends on your system (CPU/GPU). See PyTorch website.
#       pip install torch torchvision torchaudio
# ==============================================================================

import tkinter as tk
from tkinter import filedialog, messagebox, ttk, font
from PIL import Image, ImageTk, UnidentifiedImageError
import os
import datetime
import sys
from pathlib import Path # Use Pathlib for robust path handling

# --- Attempt to import optional libraries and set flags ---

# Real-ESRGAN for Upscaling
try:
    from realesrgan import RealESRGAN
    import torch
    REALESRGAN_AVAILABLE = True
    print("INFO: Real-ESRGAN library found.")
except ImportError:
    RealESRGAN = None
    torch = None
    REALESRGAN_AVAILABLE = False
    print("INFO: Real-ESRGAN library not found or torch not installed. Upscaling feature disabled.")

# rembg for Background Removal
try:
    from rembg import remove as remove_bg # Alias to avoid potential name clashes
    REMBG_AVAILABLE = True
    print("INFO: rembg library found.")
except ImportError:
    remove_bg = None
    REMBG_AVAILABLE = False
    print("INFO: rembg library not found. Background removal and cropping features disabled.")

# --- Constants ---
MAX_PREVIEW_WIDTH = 350   # Max width for preview images (pixels)
MAX_PREVIEW_HEIGHT = 350  # Max height for preview images (pixels)
APP_BG_COLOR = "#F0F0F0"  # Light grey background for the main app window
SIDEBAR_BG_COLOR = "#D8D8D8" # Slightly darker grey for the sidebar
CONTROL_BG_COLOR = "#E8E8E8" # Grey for control panel background
BUTTON_COLOR = "#C0D0E0"   # A light blue-grey for standard buttons
ACCENT_COLOR = "#4A6FA5"   # A medium blue for accent elements (selection, main buttons)
TEXT_COLOR = "#333333"    # Dark grey for standard text
WHITE_COLOR = "#FFFFFF"   # White for specific backgrounds (previews, listbox, button text)
ERROR_COLOR = "#FF6B6B"   # A light red for error messages or indicators (optional)

# ==============================================================================
# Main Application Class
# ==============================================================================
class ImageProcessorApp:
    """
    Encapsulates the entire Image Processor GUI application, including UI setup,
    event handling, image processing logic, and batch operations.
    """
    def __init__(self, master):
        """
        Initializes the application window, state variables, styles, and UI components.
        Args:
            master (tk.Tk): The root Tkinter window.
        """
        self.master = master
        self.master.title("Image Processor Suite v1.2 - Created by Greg Seymour AI")
        self.master.minsize(850, 650) # Set a minimum size for usability
        self.master.configure(bg=APP_BG_COLOR)

        # --- Application State Variables ---
        self.image_paths = []         # Stores full paths of loaded image files
        self.current_index = -1       # Index of the image currently selected in the listbox (-1 if none)
        self.original_image = None    # PIL Image: Full resolution original of the selected image (RGBA)
        self.processed_image = None   # PIL Image: Full resolution processed version for saving/preview source
        self.tk_original_preview = None # ImageTk object: Scaled preview for the original image label
        self.tk_processed_preview = None# ImageTk object: Scaled preview for the processed image label
        self.output_directory = tk.StringVar(value=str(Path.cwd())) # Default output to current working directory
        self.esrgan_model = None      # Cache for the initialized Real-ESRGAN model (if used)
        self.processing_in_progress = False # Flag to prevent starting new batch jobs while one is running
        self._preview_update_job = None # Holds the ID of the scheduled preview update task (for debouncing)

        # --- Control Variables (Tkinter Vars) ---
        # These variables link GUI widgets to application state
        self.resize_option = tk.StringVar(value="None")
        self.custom_width_var = tk.StringVar()
        self.custom_height_var = tk.StringVar()
        self.upscale_var = tk.IntVar(value=0) # 0=off, 1=on
        self.flip_h_var = tk.IntVar(value=0)
        self.flip_v_var = tk.IntVar(value=0)
        self.rotate_var = tk.StringVar(value="0") # Rotation degrees (0, 90, 180, 270)
        self.remove_bg_var = tk.IntVar(value=0)
        self.crop_var = tk.IntVar(value=0)
        self.status_var = tk.StringVar(value="Ready. Load images to begin.")

        # --- Setup UI ---
        self.setup_styles()      # Configure ttk styles first
        self.setup_layout()      # Create main layout frames
        self.setup_sidebar()     # Populate the sidebar (load button, listbox)
        self.setup_previews()    # Setup the original/processed preview areas
        self.setup_controls()    # Setup the control panel with options
        self.setup_statusbar()   # Add the status bar at the bottom

        print("Application initialized.")

    # --------------------------------------------------------------------------
    # UI Setup Methods
    # --------------------------------------------------------------------------

    def setup_styles(self):
        """ Configures ttk styles for a consistent and enhanced appearance. """
        style = ttk.Style()
        try:
            if sys.platform == "win32": style.theme_use('vista')
            elif sys.platform == "darwin": style.theme_use('aqua')
            else: style.theme_use('clam')
        except tk.TclError:
            print("INFO: Preferred ttk theme not available, using default.")
            style.theme_use('default')

        # --- Frame Styles ---
        style.configure("App.TFrame", background=APP_BG_COLOR)
        style.configure("Sidebar.TFrame", background=SIDEBAR_BG_COLOR)
        style.configure("Control.TFrame", background=CONTROL_BG_COLOR)
        style.configure("ControlPanel.TLabelframe", background=CONTROL_BG_COLOR, relief=tk.GROOVE, borderwidth=1)
        style.configure("ControlPanel.TLabelframe.Label", background=CONTROL_BG_COLOR, foreground=TEXT_COLOR, font=('Helvetica', 9, 'bold'))
        style.configure("Group.TLabelframe", background=CONTROL_BG_COLOR, relief=tk.SOLID, borderwidth=1, padding=5)
        style.configure("Group.TLabelframe.Label", background=CONTROL_BG_COLOR, foreground=ACCENT_COLOR, font=('Helvetica', 9, 'italic'))

        # --- Label Styles ---
        style.configure("TLabel", background=APP_BG_COLOR, foreground=TEXT_COLOR, font=('Helvetica', 9))
        style.configure("Header.TLabel", background=APP_BG_COLOR, foreground=TEXT_COLOR, font=('Helvetica', 11, 'bold'))
        style.configure("Preview.TLabel", background=WHITE_COLOR, relief=tk.SUNKEN, borderwidth=1, anchor=tk.CENTER)
        style.configure("Status.TLabel", background="#E0E0E0", foreground=TEXT_COLOR, anchor=tk.W, font=('Helvetica', 8))

        # --- Button Styles ---
        style.configure("TButton", padding=5, foreground=TEXT_COLOR, font=('Helvetica', 9))
        style.map("TButton",
                  background=[('active', '#AEC0D0'), ('disabled', '#D0D0D0')],
                  foreground=[('disabled', '#888888')])
        # Explicitly set white foreground for Accent button for better contrast
        style.configure("Accent.TButton", padding=(8, 6), background=ACCENT_COLOR, foreground=WHITE_COLOR, font=('Helvetica', 10, 'bold'))
        style.map("Accent.TButton",
                  background=[('active', '#3A5F95'), ('disabled', '#9DB0C7')],
                  # Ensure disabled text is also visible enough
                  foreground=[('disabled', '#E0E0E0'), ('!disabled', WHITE_COLOR)]) # White when enabled

        # --- Checkbutton/Radiobutton Styles ---
        style.configure("TCheckbutton", background=CONTROL_BG_COLOR, foreground=TEXT_COLOR, font=('Helvetica', 9))
        style.map("TCheckbutton", background=[('active', CONTROL_BG_COLOR)])
        style.configure("TRadiobutton", background=CONTROL_BG_COLOR, foreground=TEXT_COLOR, font=('Helvetica', 9))
        style.map("TRadiobutton", background=[('active', CONTROL_BG_COLOR)])

        # --- Entry/Combobox Styles ---
        style.configure("TEntry", padding=3, fieldbackground=WHITE_COLOR, foreground=TEXT_COLOR)
        style.map("TEntry", fieldbackground=[('disabled', '#F0F0F0')])
        style.configure("TCombobox", padding=3, fieldbackground=WHITE_COLOR, foreground=TEXT_COLOR)
        self.master.option_add('*TCombobox*Listbox.background', WHITE_COLOR)
        self.master.option_add('*TCombobox*Listbox.foreground', TEXT_COLOR)
        self.master.option_add('*TCombobox*Listbox.selectBackground', ACCENT_COLOR)
        self.master.option_add('*TCombobox*Listbox.selectForeground', WHITE_COLOR)
        style.map('TCombobox', fieldbackground=[('readonly', WHITE_COLOR)])
        style.map('TCombobox', selectbackground=[('readonly', WHITE_COLOR)])
        style.map('TCombobox', selectforeground=[('readonly', TEXT_COLOR)])

        # --- Listbox Style (Direct configuration for tk.Listbox) ---
        self.listbox_font = font.Font(family='Helvetica', size=9)

    def setup_layout(self):
        """ Creates the main frames for the application layout. """
        # Sidebar Frame (Left)
        self.sidebar_frame = ttk.Frame(self.master, width=220, style="Sidebar.TFrame")
        self.sidebar_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(5, 2), pady=5)
        self.sidebar_frame.pack_propagate(False)

        # Main Area Frame (Right)
        self.main_frame = ttk.Frame(self.master, style="App.TFrame")
        self.main_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(2, 5), pady=5)

        # Preview Frame (Top of Main Area)
        self.preview_frame = ttk.Frame(self.main_frame, style="App.TFrame")
        self.preview_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=0, pady=(0, 5))

        # Control Panel Frame (Bottom of Main Area)
        self.control_frame = ttk.LabelFrame(self.main_frame, text=" Processing Controls ", style="ControlPanel.TLabelframe")
        self.control_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=0, pady=(5, 0))

    def setup_sidebar(self):
        """ Sets up the widgets within the sidebar frame (Load button, Listbox). """
        # Load Button
        self.load_button = ttk.Button(self.sidebar_frame, text="Load Images", command=self.load_images, style="Accent.TButton")
        self.load_button.pack(padx=10, pady=10, fill=tk.X)

        # Image Listbox with Scrollbar
        self.listbox_frame = ttk.Frame(self.sidebar_frame, style="Sidebar.TFrame")
        self.listbox_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=(0, 5))

        self.listbox_scroll = ttk.Scrollbar(self.listbox_frame, orient=tk.VERTICAL)
        self.listbox_scroll.pack(side=tk.RIGHT, fill=tk.Y, pady=(0, 1))

        self.listbox = tk.Listbox(
            self.listbox_frame, yscrollcommand=self.listbox_scroll.set,
            bg=WHITE_COLOR, fg=TEXT_COLOR,
            selectbackground=ACCENT_COLOR, selectforeground=WHITE_COLOR,
            borderwidth=1, relief=tk.SUNKEN, font=self.listbox_font,
            exportselection=False
        )
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.listbox_scroll.config(command=self.listbox.yview)
        self.listbox.bind("<<ListboxSelect>>", self.on_thumbnail_select)

    def setup_previews(self):
        """ Sets up the original and processed image preview areas within the preview_frame. """
        # Original Preview Area (Left)
        orig_frame = ttk.Frame(self.preview_frame, style="App.TFrame")
        orig_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 2))
        ttk.Label(orig_frame, text="Original", style="Header.TLabel").pack(pady=(0, 3))
        self.original_label = ttk.Label(orig_frame, text="(Load an image)", style="Preview.TLabel")
        self.original_label.pack(fill=tk.BOTH, expand=True)

        # Processed Preview Area (Right)
        proc_frame = ttk.Frame(self.preview_frame, style="App.TFrame")
        proc_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(2, 0))
        ttk.Label(proc_frame, text="Preview", style="Header.TLabel").pack(pady=(0, 3))
        self.processed_label = ttk.Label(proc_frame, text="(Apply changes)", style="Preview.TLabel")
        self.processed_label.pack(fill=tk.BOTH, expand=True)

    def setup_controls(self):
        """ Sets up the control panel widgets using LabelFrames for organization. """
        self.control_frame.columnconfigure(0, weight=1)
        self.control_frame.columnconfigure(1, weight=1)
        self.control_frame.rowconfigure(0, weight=1)
        self.control_frame.rowconfigure(1, weight=0)

        left_group_frame = ttk.Frame(self.control_frame, style="Control.TFrame")
        left_group_frame.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        right_group_frame = ttk.Frame(self.control_frame, style="Control.TFrame")
        right_group_frame.grid(row=0, column=1, padx=5, pady=5, sticky="nsew")
        bottom_actions_frame = ttk.Frame(self.control_frame, style="Control.TFrame")
        bottom_actions_frame.grid(row=1, column=0, columnspan=2, padx=5, pady=5, sticky="ew")

        # --- Group 1: Resizing (Top Left) ---
        self.resize_frame = ttk.LabelFrame(left_group_frame, text=" Resize ", style="Group.TLabelframe")
        self.resize_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=(0,5))
        self.resize_frame.columnconfigure(1, weight=1)

        ttk.Label(self.resize_frame, text="Preset:", style="TLabel", background=CONTROL_BG_COLOR).grid(row=0, column=0, padx=5, pady=3, sticky="w")
        # *** Add new resize options to the list ***
        self.resize_menu = ttk.Combobox(
            self.resize_frame, textvariable=self.resize_option,
            values=["None", "Quarter", "Half", "Three Quarter", "Custom", "Double", "16:9 Aspect", "9:16 Aspect"],
            state="readonly", width=15
        )
        self.resize_menu.grid(row=0, column=1, columnspan=2, padx=5, pady=3, sticky="ew")
        self.resize_menu.bind("<<ComboboxSelected>>", self.on_resize_option_change)

        ttk.Label(self.resize_frame, text="Width:", style="TLabel", background=CONTROL_BG_COLOR).grid(row=1, column=0, padx=5, pady=3, sticky="w")
        self.custom_width_entry = ttk.Entry(self.resize_frame, textvariable=self.custom_width_var, state=tk.DISABLED, width=7)
        self.custom_width_entry.grid(row=1, column=1, padx=5, pady=3, sticky="w")
        ttk.Label(self.resize_frame, text="px", style="TLabel", background=CONTROL_BG_COLOR).grid(row=1, column=2, padx=(0,5), pady=3, sticky="w")
        self.custom_width_entry.bind("<KeyRelease>", lambda e: self.schedule_preview_update())

        ttk.Label(self.resize_frame, text="Height:", style="TLabel", background=CONTROL_BG_COLOR).grid(row=2, column=0, padx=5, pady=3, sticky="w")
        self.custom_height_entry = ttk.Entry(self.resize_frame, textvariable=self.custom_height_var, state=tk.DISABLED, width=7)
        self.custom_height_entry.grid(row=2, column=1, padx=5, pady=3, sticky="w")
        ttk.Label(self.resize_frame, text="px", style="TLabel", background=CONTROL_BG_COLOR).grid(row=2, column=2, padx=(0,5), pady=3, sticky="w")
        self.custom_height_entry.bind("<KeyRelease>", lambda e: self.schedule_preview_update())


        # --- Group 2: Enhancements (Bottom Left) ---
        self.enhance_frame = ttk.LabelFrame(left_group_frame, text=" Enhance ", style="Group.TLabelframe")
        self.enhance_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.upscale_check = ttk.Checkbutton(
            self.enhance_frame, text="Upscale x2 (Real-ESRGAN)",
            variable=self.upscale_var, command=self.schedule_preview_update,
            state=tk.NORMAL if REALESRGAN_AVAILABLE else tk.DISABLED
        )
        self.upscale_check.pack(anchor="nw", padx=5, pady=3)
        if not REALESRGAN_AVAILABLE:
             ttk.Label(self.enhance_frame, text="(requires Real-ESRGAN library)", foreground="grey", background=CONTROL_BG_COLOR, font=('Helvetica', 8)).pack(anchor="nw", padx=25, pady=(0,3))

        # --- Group 3: Transformations (Top Right) ---
        self.transform_frame = ttk.LabelFrame(right_group_frame, text=" Transform ", style="Group.TLabelframe")
        self.transform_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=(0,5))
        self.transform_frame.columnconfigure(0, weight=1)
        self.transform_frame.columnconfigure(1, weight=1)

        self.flip_h_check = ttk.Checkbutton(self.transform_frame, text="Flip Horizontal", variable=self.flip_h_var, command=self.schedule_preview_update)
        self.flip_h_check.grid(row=0, column=0, sticky="w", padx=5, pady=2)
        self.flip_v_check = ttk.Checkbutton(self.transform_frame, text="Flip Vertical", variable=self.flip_v_var, command=self.schedule_preview_update)
        self.flip_v_check.grid(row=1, column=0, sticky="w", padx=5, pady=2)

        ttk.Label(self.transform_frame, text="Rotate:", style="TLabel", background=CONTROL_BG_COLOR).grid(row=0, column=1, sticky="w", padx=(15, 5), pady=2)
        ttk.Radiobutton(self.transform_frame, text="0°", variable=self.rotate_var, value="0", command=self.schedule_preview_update).grid(row=1, column=1, sticky="w", padx=(20, 5), pady=2)
        ttk.Radiobutton(self.transform_frame, text="90°", variable=self.rotate_var, value="90", command=self.schedule_preview_update).grid(row=2, column=0, sticky="w", padx=5, pady=2)
        ttk.Radiobutton(self.transform_frame, text="180°", variable=self.rotate_var, value="180", command=self.schedule_preview_update).grid(row=2, column=1, sticky="w", padx=(20, 5), pady=2)
        ttk.Radiobutton(self.transform_frame, text="270°", variable=self.rotate_var, value="270", command=self.schedule_preview_update).grid(row=3, column=0, sticky="w", padx=5, pady=2)

        # --- Group 4: Background & Cropping (Bottom Right) ---
        self.bg_crop_frame = ttk.LabelFrame(right_group_frame, text=" Background / Crop ", style="Group.TLabelframe")
        self.bg_crop_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.remove_bg_check = ttk.Checkbutton(
            self.bg_crop_frame, text="Remove Background (rembg)",
            variable=self.remove_bg_var, command=self.on_remove_bg_toggle,
            state=tk.NORMAL if REMBG_AVAILABLE else tk.DISABLED
        )
        self.remove_bg_check.pack(anchor="nw", padx=5, pady=3)
        if not REMBG_AVAILABLE:
             ttk.Label(self.bg_crop_frame, text="(requires rembg library)", foreground="grey", background=CONTROL_BG_COLOR, font=('Helvetica', 8)).pack(anchor="nw", padx=25, pady=(0,3))
        self.crop_check = ttk.Checkbutton(
            self.bg_crop_frame, text="Crop to Content (after removal)",
            variable=self.crop_var, command=self.schedule_preview_update,
            state=tk.DISABLED
        )
        self.crop_check.pack(anchor="nw", padx=5, pady=3)

        # --- Group 5: Output & Actions (Bottom Bar) ---
        output_frame = ttk.Frame(bottom_actions_frame, style="Control.TFrame")
        output_frame.pack(fill=tk.X, pady=(5, 5))
        output_frame.columnconfigure(1, weight=1)

        ttk.Label(output_frame, text="Output Folder:", style="TLabel", background=CONTROL_BG_COLOR).grid(row=0, column=0, padx=(5, 2), pady=5, sticky="w")
        self.output_entry = ttk.Entry(output_frame, textvariable=self.output_directory, width=45)
        self.output_entry.grid(row=0, column=1, padx=(0, 5), pady=5, sticky="ew")
        self.browse_button = ttk.Button(output_frame, text="Browse...", command=self.select_output_directory, style="TButton")
        self.browse_button.grid(row=0, column=2, padx=(0, 5), pady=5, sticky="e")

        ttk.Separator(bottom_actions_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=5, pady=5)

        action_buttons_frame = ttk.Frame(bottom_actions_frame, style="Control.TFrame")
        action_buttons_frame.pack(fill=tk.X, pady=(0, 5))

        self.directions_button = ttk.Button(action_buttons_frame, text="Directions", command=self.show_directions, style="TButton")
        self.directions_button.pack(side=tk.LEFT, padx=(5, 10))

        ttk.Frame(action_buttons_frame, style="Control.TFrame").pack(side=tk.LEFT, expand=True, fill=tk.X) # Spacer

        self.process_save_button = ttk.Button(action_buttons_frame, text="Process & Save All", command=self.process_and_save_all, style="Accent.TButton")
        self.process_save_button.pack(side=tk.RIGHT, padx=(5, 5))

    def setup_statusbar(self):
        """ Adds a status bar label at the very bottom of the window. """
        self.status_bar = ttk.Label(self.master, textvariable=self.status_var, relief=tk.SUNKEN, style="Status.TLabel")
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    # --------------------------------------------------------------------------
    # Event Handlers & UI Logic Methods
    # --------------------------------------------------------------------------

    def load_images(self):
        """ Opens a file dialog to select images and loads valid ones into the listbox. """
        supported_extensions = {
            ".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp", ".tiff", ".tif"
        }
        filetypes = [
            ("Image files", "*.jpg *.jpeg *.png *.bmp *.gif *.webp *.tiff *.tif"),
            ("All files", "*.*")
        ]

        filenames = filedialog.askopenfilenames(title="Select Images", filetypes=filetypes)

        if filenames:
            initial_load = not self.image_paths
            new_images_loaded = 0
            skipped_count = 0
            problematic_files = []

            for filename_str in filenames:
                try:
                    filepath = Path(filename_str)
                    if filename_str in self.image_paths:
                        print(f"Skipping duplicate: {filepath.name}")
                        skipped_count += 1
                        continue
                    if filepath.suffix.lower() not in supported_extensions:
                        print(f"Skipping unsupported type '{filepath.suffix}': {filepath.name}")
                        skipped_count += 1
                        problematic_files.append(f"{filepath.name} (unsupported type)")
                        continue
                    if not filepath.is_file():
                        print(f"Skipping non-file: {filepath.name}")
                        skipped_count += 1
                        problematic_files.append(f"{filepath.name} (not found/not a file)")
                        continue

                    self.image_paths.append(filename_str)
                    self.listbox.insert(tk.END, filepath.name)
                    new_images_loaded += 1

                except Exception as e:
                    print(f"Error processing path '{filename_str}': {e}")
                    skipped_count += 1
                    problematic_files.append(f"{filename_str} (error: {e})")

            if new_images_loaded > 0:
                total_images = len(self.image_paths)
                status_msg = f"Loaded {new_images_loaded} new image(s). Total: {total_images}."
                if skipped_count > 0: status_msg += f" Skipped: {skipped_count}."
                self.status_var.set(status_msg)

                if initial_load and total_images > 0:
                    self.listbox.selection_clear(0, tk.END)
                    self.listbox.selection_set(0)
                    self.listbox.activate(0)
                    self.listbox.see(0)
                    self.on_thumbnail_select(None)

                self.master.update_idletasks()

            elif skipped_count > 0:
                 self.status_var.set(f"No new valid images loaded. Skipped {skipped_count}. Total: {len(self.image_paths)}")

            if problematic_files:
                 messagebox.showwarning("Loading Issues",
                                      "Some files were skipped during loading:\n\n" +
                                      "\n".join(problematic_files[:10]) +
                                      ("\n..." if len(problematic_files) > 10 else "") +
                                      "\n\nCheck console for full details.")
        else:
            self.status_var.set("Image loading cancelled.")

    def on_thumbnail_select(self, event):
        """ Handles selection changes in the image listbox. Loads and displays the selected image. """
        selection = self.listbox.curselection()
        if not selection:
             self.current_index = -1
             self.clear_previews()
             return

        new_index = selection[0]
        if new_index != self.current_index:
            self.current_index = new_index
            self.display_selected_image()

    def display_selected_image(self):
        """ Loads the selected image, displays original preview, and updates processed preview. """
        if not (0 <= self.current_index < len(self.image_paths)):
             self.clear_previews()
             self.status_var.set("No image selected or index out of bounds.")
             return

        filepath_str = self.image_paths[self.current_index]
        filepath = Path(filepath_str)
        self.status_var.set(f"Loading: {filepath.name}")
        self.master.update_idletasks()

        try:
            self.original_image = Image.open(filepath).convert("RGBA")

            preview_orig_pil = self.get_scaled_preview(self.original_image)
            self.tk_original_preview = ImageTk.PhotoImage(preview_orig_pil)
            self.original_label.config(image=self.tk_original_preview, text="")
            self.original_label.image = self.tk_original_preview

            # *** Trigger immediate preview update on selection ***
            self.schedule_preview_update(immediate=True)

            self.status_var.set(f"Selected: {filepath.name}")

        except FileNotFoundError:
            messagebox.showerror("Error", f"Image file not found:\n{filepath_str}")
            self.remove_bad_entry(filepath_str)
        except UnidentifiedImageError:
            messagebox.showerror("Error", f"Cannot open or identify image file:\n{filepath.name}")
            self.remove_bad_entry(filepath_str)
        except Exception as e:
            messagebox.showerror("Error", f"Error loading image '{filepath.name}':\n{e}")
            self.remove_bad_entry(filepath_str)
            self.clear_previews()
        finally:
            self.master.update_idletasks()

    def remove_bad_entry(self, filepath_to_remove):
        """ Removes an entry from the listbox and internal list if it caused a loading error. """
        try:
            idx_internal = self.image_paths.index(filepath_to_remove)
            filename_to_remove = Path(filepath_to_remove).name
            idx_listbox = -1
            for i, item in enumerate(self.listbox.get(0, tk.END)):
                if item == filename_to_remove:
                    idx_listbox = i
                    break

            if idx_listbox != -1: self.listbox.delete(idx_listbox)
            del self.image_paths[idx_internal]

            self.current_index = -1
            self.clear_previews()
            self.listbox.selection_clear(0, tk.END)

            self.status_var.set(f"Removed problematic file: {filename_to_remove}. List updated.")
            print(f"Removed problematic file: {filename_to_remove}")

        except ValueError:
            print(f"Warning: Could not find '{filepath_to_remove}' to remove it from lists.")
        except Exception as e:
            print(f"Error removing bad list entry: {e}")

    def on_resize_option_change(self, event=None):
        """ Handles selection changes in the resize combobox. """
        is_custom = (self.resize_option.get() == "Custom")
        new_state = tk.NORMAL if is_custom else tk.DISABLED

        self.custom_width_entry.config(state=new_state)
        self.custom_height_entry.config(state=new_state)

        if not is_custom:
            self.custom_width_var.set("")
            self.custom_height_var.set("")

        # *** Trigger immediate preview update when preset changes ***
        self.schedule_preview_update(immediate=True)

    def on_remove_bg_toggle(self):
        """ Handles toggling the 'Remove Background' checkbox. """
        can_crop = (self.remove_bg_var.get() == 1 and REMBG_AVAILABLE)
        self.crop_check.config(state=tk.NORMAL if can_crop else tk.DISABLED)
        if not can_crop:
            self.crop_var.set(0)
        # *** Trigger immediate preview update on toggle ***
        self.schedule_preview_update(immediate=True)

    def schedule_preview_update(self, immediate=False, delay_ms=300):
        """ Schedules the _update_processed_preview function (debounced). """
        if self._preview_update_job:
            self.master.after_cancel(self._preview_update_job)
            self._preview_update_job = None

        if immediate:
            self._update_processed_preview()
        else:
            self._preview_update_job = self.master.after(delay_ms, self._update_processed_preview)

    def _update_processed_preview(self):
        """ Regenerates and displays the processed image preview. """
        self._preview_update_job = None

        if self.original_image is None or self.current_index == -1:
            self.clear_previews(clear_original=False)
            self.processed_label.config(text="(No image selected)")
            return

        current_filename = Path(self.image_paths[self.current_index]).name
        self.status_var.set(f"Updating preview for {current_filename}...")
        self.master.update_idletasks()

        try:
            processed_pil = self.apply_all_transformations(self.original_image.copy())
            self.processed_image = processed_pil

            preview_proc_pil = self.get_scaled_preview(self.processed_image)
            self.tk_processed_preview = ImageTk.PhotoImage(preview_proc_pil)
            self.processed_label.config(image=self.tk_processed_preview, text="")
            self.processed_label.image = self.tk_processed_preview
            self.status_var.set(f"Preview updated for {current_filename}")

        except Exception as e:
            messagebox.showerror("Preview Error", f"Could not generate preview:\n{e}\n\nCheck settings.")
            print(f"ERROR generating preview: {e}")
            self.clear_previews(clear_original=False, clear_processed=True)
            self.processed_label.config(text="(Preview Error)")
            self.status_var.set("Error generating preview.")
        finally:
             self.master.update_idletasks()

    def clear_previews(self, clear_original=True, clear_processed=True):
        """ Clears the image previews and resets associated variables. """
        if clear_original:
            self.original_label.config(image='', text="(Load an image)")
            self.original_label.image = None
            self.original_image = None
            self.tk_original_preview = None
        if clear_processed:
            self.processed_label.config(image='', text="(Apply changes)")
            self.processed_label.image = None
            self.processed_image = None
            self.tk_processed_preview = None

    def get_scaled_preview(self, img, max_w=MAX_PREVIEW_WIDTH, max_h=MAX_PREVIEW_HEIGHT):
        """ Scales a PIL Image down (only) to fit within max dimensions. """
        if img is None: return None
        w, h = img.size
        if w == 0 or h == 0: return img

        scale = min(max_w / w, max_h / h, 1.0)

        if scale < 1.0:
            new_w = int(w * scale)
            new_h = int(h * scale)
            try:
                resample_filter = Image.Resampling.LANCZOS
            except AttributeError:
                resample_filter = Image.LANCZOS
            try:
                return img.resize((new_w, new_h), resample_filter)
            except Exception as e:
                 print(f"Warning: Error during preview scaling ({e}). Returning original size.")
                 return img
        else:
            return img

    def select_output_directory(self):
        """ Opens a dialog to choose the output directory. """
        initial_dir = self.output_directory.get()
        if not Path(initial_dir).is_dir():
            initial_dir = str(Path.cwd())

        selected_dir = filedialog.askdirectory(title="Select Output Folder", initialdir=initial_dir)

        if selected_dir:
            self.output_directory.set(selected_dir)
            self.status_var.set(f"Output directory set to: {selected_dir}")

    def show_directions(self):
        """ Displays a modal message box with usage instructions. """
        # Updated directions including new resize options
        directions = """
    Image Processor Suite - How to Use (v1.2)

    1.  Load Images: Click 'Load Images' to select one or more image files. Supported types: JPG, PNG, BMP, GIF, WEBP, TIFF. Valid files will appear in the list on the left.

    2.  Select Image: Click on an image name in the list. Its original version will appear in the 'Original' preview pane.

    3.  Choose Options: Use the controls in the 'Processing Controls' panel below the previews:
        *   Resize: Select a preset ('None', 'Quarter', 'Half', 'Three Quarter', 'Double', '16:9', '9:16') or choose 'Custom' and enter integer pixel values for Width and Height.
        *   Enhance: Check 'Upscale x2' to use Real-ESRGAN (if installed). This doubles the dimensions *after* any resizing.
        *   Transform: Check 'Flip Horizontal'/'Vertical', or select a 'Rotate' angle (0°, 90°, 180°, 270°).
        *   Background/Crop: Check 'Remove Background' (if rembg installed). If checked, you can then optionally check 'Crop to Content' to trim transparency.

    4.  Preview Changes: As you change options, the 'Preview' pane on the right will update automatically showing the result for the *currently selected* image. (Preset changes trigger immediate updates, others after a short delay).

    5.  Select Output Folder: Click 'Browse...' next to 'Output Folder' to choose where the final processed images will be saved.

    6.  Process & Save All: When you are satisfied with the settings (based on the preview), click 'Process & Save All'.
        *   This will apply the *current* set of options to *every image* loaded in the list.
        *   Each processed image will be saved as a PNG file (to preserve transparency) in the chosen output folder.
        *   Filenames will be like: `original_filename_processed.png`.
        *   Watch the status bar at the bottom for progress. This can take time, especially with many files or demanding operations like upscaling/background removal.

    Notes:
    *   Make sure optional libraries (rembg, realesrgan & torch) are installed to use those features. Check the console output when starting the app.
    *   Processing is done in the order: Flip -> Rotate -> Resize -> Upscale -> Remove BG -> Crop.
        """
        messagebox.showinfo("Directions - Image Processor Suite", directions)

    # --------------------------------------------------------------------------
    # Core Image Processing Logic Methods
    # --------------------------------------------------------------------------

    def apply_all_transformations(self, img):
        """ Applies the sequence of selected transformations to a given PIL Image object. """
        if img.mode != 'RGBA':
            print(f"Warning: apply_all_transformations received non-RGBA image ({img.mode}). Converting.")
            img = img.convert('RGBA')

        current_op = "Starting transformations"
        try:
            # 1. Flipping
            current_op = "Flipping"
            if self.flip_h_var.get(): img = img.transpose(Image.FLIP_LEFT_RIGHT)
            if self.flip_v_var.get(): img = img.transpose(Image.FLIP_TOP_BOTTOM)

            # 2. Rotation
            current_op = "Rotation"
            rotation_degrees = int(self.rotate_var.get())
            if rotation_degrees != 0:
                img = img.rotate(rotation_degrees, expand=True, resample=Image.BICUBIC, fillcolor=(0,0,0,0))

            # 3. Resizing
            current_op = "Resizing"
            img = self.apply_resizing(img)

            # 4. Upscaling
            current_op = "Upscaling"
            if self.upscale_var.get() and REALESRGAN_AVAILABLE:
                img = self.apply_upscaling(img)
                if img.mode != 'RGBA': img = img.convert('RGBA')

            # 5. Background Removal
            current_op = "Background Removal"
            if self.remove_bg_var.get() and REMBG_AVAILABLE:
                img = self.apply_background_removal(img)
                if img.mode != 'RGBA': img = img.convert('RGBA')

            # 6. Cropping
            current_op = "Cropping"
            if self.remove_bg_var.get() and self.crop_var.get() and REMBG_AVAILABLE:
                 img = self.apply_cropping(img)

            return img

        except Exception as e:
            error_message = f"Error during '{current_op}' step: {e}"
            print(f"ERROR: {error_message}")
            raise RuntimeError(error_message) from e

    def apply_resizing(self, img):
        """ Applies resizing based on the selected preset or custom dimensions. """
        width, height = img.size
        new_width, new_height = width, height
        option = self.resize_option.get()

        try:
            # *** Add logic for Quarter and Three Quarter ***
            if option == "Quarter":
                new_width, new_height = max(1, width // 4), max(1, height // 4)
            elif option == "Half":
                new_width, new_height = max(1, width // 2), max(1, height // 2)
            elif option == "Three Quarter":
                new_width, new_height = max(1, round(width * 0.75)), max(1, round(height * 0.75))
            elif option == "Double":
                new_width, new_height = width * 2, height * 2
            elif option == "Custom":
                custom_w_str = self.custom_width_var.get().strip()
                custom_h_str = self.custom_height_var.get().strip()
                new_width = int(custom_w_str) if custom_w_str.isdigit() else width
                new_height = int(custom_h_str) if custom_h_str.isdigit() else height
                new_width = max(1, new_width)
                new_height = max(1, new_height)
            elif option == "16:9 Aspect":
                if width > 0: new_height = max(1, round(width * 9 / 16))
                else: new_height = height
            elif option == "9:16 Aspect":
                 if height > 0: new_width = max(1, round(height * 9 / 16))
                 else: new_width = width

            if (new_width, new_height) != (width, height):
                print(f"Resizing from ({width}x{height}) to ({new_width}x{new_height}) using '{option}'")
                try:
                    resample_filter = Image.Resampling.LANCZOS
                except AttributeError:
                    resample_filter = Image.LANCZOS
                img = img.resize((new_width, new_height), resample_filter)

        except ValueError as e:
            print(f"Resize Warning: Invalid value during resize calculation. Error: {e}. Using original size.")
        except Exception as e:
            print(f"Error during resizing operation: {e}")
            raise

        return img

    def apply_upscaling(self, img):
        """ Applies Real-ESRGAN upscaling (if available and model loaded). """
        if not REALESRGAN_AVAILABLE: return img

        if self.esrgan_model is None:
            try:
                self.status_var.set("Initializing Real-ESRGAN model...")
                print("Initializing Real-ESRGAN model...")
                self.master.update_idletasks()
                device_name = 'cuda' if torch.cuda.is_available() else 'cpu'
                print(f"Using device: {device_name}")
                device = torch.device(device_name)
                self.esrgan_model = RealESRGAN(device, scale=2)
                # Attempt to load weights, handle failure gracefully
                try:
                    # Adjust model name/path if needed
                    model_path = 'RealESRGAN_x2plus.pth'
                    print(f"Loading weights: {model_path}")
                    self.esrgan_model.load_weights(model_path, download=True)
                except Exception as weight_error:
                     print(f"WARNING: Failed to load/download RealESRGAN weights '{model_path}': {weight_error}")
                     self.esrgan_model = None # Disable on failure
                     self.upscale_var.set(0)
                     self.upscale_check.config(state=tk.DISABLED)
                     messagebox.showerror("Upscaling Error", f"Failed to load Real-ESRGAN weights: {weight_error}\nUpscaling disabled.")
                     return img

                print("Real-ESRGAN model initialized successfully.")
                self.status_var.set("Real-ESRGAN model loaded.")
                # Reset status after a delay (only if an image is selected)
                if self.current_index != -1:
                    self.master.after(2000, lambda: self.status_var.set(f"Selected: {Path(self.image_paths[self.current_index]).name}"))

            except Exception as e:
                messagebox.showerror("Real-ESRGAN Init Error", f"Failed to initialize Real-ESRGAN:\n{e}")
                print(f"ERROR: Failed to initialize Real-ESRGAN: {e}")
                self.esrgan_model = None
                self.upscale_var.set(0)
                self.upscale_check.config(state=tk.DISABLED)
                return img

        if self.esrgan_model:
            try:
                print("Applying Real-ESRGAN upscaling...")
                self.status_var.set("Upscaling with Real-ESRGAN...")
                self.master.update_idletasks()
                upscaled_img = self.esrgan_model.predict(img)
                print("Upscaling finished.")
                return upscaled_img
            except Exception as e:
                messagebox.showerror("Upscaling Error", f"Error during Real-ESRGAN prediction:\n{e}")
                print(f"ERROR: Upscaling prediction failed: {e}")
                return img
        else:
            return img


    def apply_background_removal(self, img):
        """ Applies background removal using the rembg library. """
        if not REMBG_AVAILABLE: return img
        try:
            print("Applying background removal (rembg)...")
            self.status_var.set("Removing background...")
            self.master.update_idletasks()
            removed_bg_img = remove_bg(img)
            print("Background removal finished.")
            return removed_bg_img
        except Exception as e:
            messagebox.showerror("Background Removal Error", f"Error during rembg processing:\n{e}")
            print(f"ERROR: rembg processing failed: {e}")
            return img

    def apply_cropping(self, img):
        """ Crops the image to the bounding box of non-transparent content. """
        if img.mode != 'RGBA':
             print("Warning: Cropping requires RGBA image. Skipping crop.")
             return img
        try:
            print("Applying cropping to content...")
            self.status_var.set("Cropping...")
            self.master.update_idletasks()
            bbox = img.getbbox()
            if bbox:
                print(f"Cropping to bounding box: {bbox}")
                return img.crop(bbox)
            else:
                print("Warning: Image appears empty (fully transparent). Skipping crop.")
                return img
        except Exception as e:
             messagebox.showerror("Cropping Error", f"Error during cropping:\n{e}")
             print(f"ERROR: Cropping failed: {e}")
             return img

    # --------------------------------------------------------------------------
    # Batch Processing and Saving Method
    # --------------------------------------------------------------------------

    def process_and_save_all(self):
        """ Applies current transformations to ALL loaded images and saves them. """
        if self.processing_in_progress:
            messagebox.showwarning("Busy", "Batch processing is already in progress.")
            return
        if not self.image_paths:
            messagebox.showerror("Error", "No images loaded to process.")
            return

        output_dir_str = self.output_directory.get()
        output_path = Path(output_dir_str)
        if not output_dir_str or not output_path.is_dir():
            messagebox.showerror("Error", "Invalid output directory selected.")
            self.select_output_directory()
            output_dir_str = self.output_directory.get()
            output_path = Path(output_dir_str)
            if not output_dir_str or not output_path.is_dir():
                self.status_var.set("Batch processing cancelled: No valid output directory.")
                return

        num_files = len(self.image_paths)
        options_summary = []
        if self.resize_option.get() != "None": options_summary.append(f"Resize: {self.resize_option.get()}")
        if self.flip_h_var.get(): options_summary.append("Flip H")
        if self.flip_v_var.get(): options_summary.append("Flip V")
        if self.rotate_var.get() != "0": options_summary.append(f"Rotate {self.rotate_var.get()}°")
        if self.upscale_var.get(): options_summary.append("Upscale x2")
        if self.remove_bg_var.get(): options_summary.append("Remove BG")
        if self.crop_var.get() and self.remove_bg_var.get(): options_summary.append("Crop")
        options_str = ", ".join(options_summary) if options_summary else "No transformations"

        confirm = messagebox.askyesno(
            "Confirm Batch Processing",
            f"Process all {num_files} image(s) with settings:\n[{options_str}]\n\nOutput to:\n{output_dir_str}\n\nProceed?"
        )
        if not confirm:
            self.status_var.set("Batch processing cancelled.")
            return

        self.processing_in_progress = True
        self.status_var.set(f"Starting batch processing of {num_files} images...")
        self.disable_controls()
        self.master.update_idletasks()

        processed_count = 0
        error_count = 0
        skipped_empty_count = 0
        start_time = datetime.datetime.now()

        for i, filepath_str in enumerate(self.image_paths):
            filepath = Path(filepath_str)
            self.status_var.set(f"Processing [{i+1}/{num_files}]: {filepath.name}")
            self.master.update_idletasks()

            try:
                current_original_img = Image.open(filepath).convert("RGBA")
                final_image = self.apply_all_transformations(current_original_img)

                output_filename = f"{filepath.stem}_processed.png"
                output_file_path = output_path / output_filename

                if final_image and final_image.width > 0 and final_image.height > 0:
                    final_image.save(output_file_path, "PNG")
                    processed_count += 1
                else:
                    print(f"Skipping save for {filepath.name}: Processed image is empty.")
                    skipped_empty_count += 1

            except FileNotFoundError:
                 print(f"ERROR processing {filepath.name}: Source file not found.")
                 error_count += 1
            except UnidentifiedImageError:
                 print(f"ERROR processing {filepath.name}: Cannot identify source image file.")
                 error_count += 1
            except Exception as e:
                print(f"ERROR processing {filepath.name}: {e}")
                error_count += 1

        end_time = datetime.datetime.now()
        duration = end_time - start_time
        self.processing_in_progress = False
        self.enable_controls()

        final_message = (
            f"Batch processing finished in {duration.total_seconds():.2f} seconds.\n\n"
            f"Successfully processed: {processed_count}\n"
            f"Skipped (empty result): {skipped_empty_count}\n"
            f"Errors encountered: {error_count}\n\n"
            f"Output saved to: {output_dir_str}"
        )
        self.status_var.set(f"Batch complete. Processed: {processed_count}, Skipped: {skipped_empty_count}, Errors: {error_count}.")
        print(f"\n--- Batch Summary ---\n{final_message.replace(' ', ' ')}\n---------------------\n")
        messagebox.showinfo("Processing Complete", final_message)


    # --------------------------------------------------------------------------
    # Helper Methods for Enabling/Disabling Controls
    # --------------------------------------------------------------------------

    def set_controls_state(self, state):
        """ Sets the state (tk.NORMAL or tk.DISABLED) for control widgets. """
        explicit_widgets = [
            self.load_button, self.resize_menu, self.custom_width_entry,
            self.custom_height_entry, self.output_entry, self.browse_button,
            self.directions_button, self.process_save_button
        ]
        frames_with_toggles = [
            self.enhance_frame, self.transform_frame, self.bg_crop_frame
        ]

        for widget in explicit_widgets:
            if widget:
                try:
                    if state == tk.NORMAL and widget in [self.custom_width_entry, self.custom_height_entry]:
                        widget.config(state=tk.NORMAL if self.resize_option.get() == "Custom" else tk.DISABLED)
                    else:
                        widget.config(state=state)
                except (tk.TclError, AttributeError) as e:
                    print(f"Warning: Could not set state for widget {widget}: {e}")

        for frame in frames_with_toggles:
            if frame:
                try:
                    for child in frame.winfo_children():
                        if isinstance(child, (ttk.Checkbutton, ttk.Radiobutton)):
                            try: child.config(state=state)
                            except tk.TclError as e: print(f"Warning: Could not set state for toggle {child}: {e}")
                except Exception as e: print(f"Warning: Error iterating children of frame {frame}: {e}")

        if state == tk.NORMAL:
            if hasattr(self, 'upscale_check'):
                self.upscale_check.config(state=tk.NORMAL if REALESRGAN_AVAILABLE else tk.DISABLED)
            if hasattr(self, 'remove_bg_check'):
                self.remove_bg_check.config(state=tk.NORMAL if REMBG_AVAILABLE else tk.DISABLED)
            if hasattr(self, 'crop_check'):
                 can_crop = REMBG_AVAILABLE and self.remove_bg_var.get() == 1
                 self.crop_check.config(state=tk.NORMAL if can_crop else tk.DISABLED)

    def disable_controls(self):
        """ Disables controls, typically during batch processing. """
        self.set_controls_state(tk.DISABLED)

    def enable_controls(self):
        """ Enables controls, typically after batch processing. """
        self.set_controls_state(tk.NORMAL)

# ==============================================================================
# Main Execution Block
# ==============================================================================
if __name__ == "__main__":
    print("-" * 60)
    print(" Starting Image Processor Suite v1.2")
    print(f" Python Version: {sys.version.split()[0]}")
    try: print(f" Pillow Version: {Image.__version__}")
    except Exception: print(" Pillow Version: Not Found (ERROR)")
    print(f" Real-ESRGAN Available: {REALESRGAN_AVAILABLE}")
    if REALESRGAN_AVAILABLE and torch:
        try:
            print(f" PyTorch Version: {torch.__version__}")
            print(f" CUDA Available: {torch.cuda.is_available()}")
            if torch.cuda.is_available(): print(f" CUDA Device Name: {torch.cuda.get_device_name(0)}")
        except Exception as e: print(f" PyTorch/CUDA Info Error: {e}")
    print(f" rembg Available: {REMBG_AVAILABLE}")
    print(f" Operating System: {sys.platform}")
    print("-" * 60)

    root = tk.Tk()
    app = ImageProcessorApp(root)
    root.mainloop()

    print("\nApplication closed.")

# --- END OF REWRITTEN FILE ---