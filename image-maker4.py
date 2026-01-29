# === 1. IMPORTS ===
# Import necessary libraries for the application.
import tkinter as tk  # The core library for creating the graphical user interface (GUI).
from tkinter import ttk, filedialog, messagebox, colorchooser, simpledialog # More advanced widgets and standard dialogs.
from PIL import Image, ImageTk, ImageDraw, ImageFont, ImageFilter # The Python Imaging Library (Pillow) for all image manipulation.
import os # Provides functions for interacting with the operating system, like getting file names.
import random # Used for generating random numbers for scale, rotation, and placement.
import matplotlib.font_manager as fm # Used specifically to find system fonts for the title engine.

# === 2. MAIN APPLICATION CLASS ===
# This class encapsulates the entire application, holding its data, UI, and logic.
class SceneEditorApp:
    # --- 2.1. INITIALIZATION ---
    def __init__(self, root):
        """
        Constructor for the main application. Sets up the window, core data, and UI.
        'root' is the main Tkinter window instance.
        """
        # --- Root Window Setup ---
        self.root = root
        self.root.title("Advanced Scene Editor")
        self.root.state('zoomed') # Maximize the window on startup for more workspace.

        # --- Core Data Structures ---
        # These variables hold the state of the application.
        self.background_image = None           # The original, unmodified background PIL Image.
        self.generated_scene_no_title = None # The PIL Image *after* assets are placed, but *before* the title is added.
                                             # This is CRUCIAL for reapplying the title without re-generating assets.
        self.current_scene_image = None        # The final PIL Image that is currently being displayed (with title).
        self.tk_image = None                   # The Tkinter-compatible version of the displayed image. Must be kept as an instance variable to prevent garbage collection.

        # --- Font Loading ---
        # Find all available TrueType fonts on the system. This can be slow, so it's done once at startup.
        try:
            # Get a list of file paths to all .ttf fonts.
            font_paths = fm.findSystemFonts(fontpaths=None, fontext='ttf')
            # For each font path, get its family name (e.g., "Arial").
            # A 'set' is used here to automatically store only the unique names, removing duplicates.
            unique_font_names = {fm.FontProperties(fname=font_path).get_name() for font_path in font_paths}
            # Convert the set of unique names back to a list and sort it alphabetically for the dropdown menu.
            self.system_fonts = sorted(list(unique_font_names))
        except Exception as e:
            # If font scanning fails for any reason, fall back to a safe, default list.
            print(f"Could not load system fonts, falling back to a default list: {e}")
            self.system_fonts = ["Arial", "Courier New", "Times New Roman", "Verdana", "Helvetica"]


        # --- Layer Data ---
        # A list of dictionaries, where each dictionary represents one layer.
        # This structure allows for easy expansion with more layers in the future.
        self.layers = [
            # Each layer has its own set of assets, a UI treeview, and its own placement setting.
            {"name": "Layer 1 (e.g., Seafloor)", "assets": {}, "tree": None, "placement_var": tk.StringVar(value="Anywhere")},
            {"name": "Layer 2 (e.g., Coral/Plants)", "assets": {}, "tree": None, "placement_var": tk.StringVar(value="Anywhere")},
            {"name": "Layer 3 (e.g., Fish/Creatures)", "assets": {}, "tree": None, "placement_var": tk.StringVar(value="Anywhere")}
        ]

        # --- Main Layout Frames ---
        # The window is divided into a control panel on the left and an image display area on the right.
        self.control_panel = ttk.Frame(root, width=450)
        self.control_panel.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
        self.control_panel.pack_propagate(False) # Prevents the panel from shrinking to fit its contents.

        self.image_frame = ttk.Frame(root)
        self.image_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        # --- Create and Populate UI Elements ---
        self._create_scrollable_controls() # Creates the main scrollable area for controls.
        self.image_label = ttk.Label(self.image_frame, background='black', anchor=tk.CENTER) # Label to display the image.
        self.image_label.pack(fill=tk.BOTH, expand=True)

        # A status bar at the bottom to give feedback to the user.
        self.status_var = tk.StringVar(value="Welcome! Load a background or create a new canvas.")
        ttk.Label(root, textvariable=self.status_var, relief=tk.SUNKEN).pack(side=tk.BOTTOM, fill=tk.X)


    # --- 2.2. UI CREATION METHODS ---
    # These methods are responsible for building the GUI.

    def _create_scrollable_controls(self):
        """Creates a scrollable frame inside the main control panel."""
        # This is the standard Tkinter pattern for a scrollable area: Canvas + Scrollbar + Frame.
        canvas = tk.Canvas(self.control_panel)
        scrollbar = ttk.Scrollbar(self.control_panel, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        # When the frame's size changes, update the canvas's scroll region.
        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        # Place the frame inside the canvas.
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Now that the scrollable container is ready, fill it with the actual controls.
        self._populate_controls(scrollable_frame)

    def _populate_controls(self, parent_frame):
        """Fills the scrollable frame with all the main control sections."""
        # 1. Background Section
        bg_frame = ttk.LabelFrame(parent_frame, text="1. Background", padding=10)
        bg_frame.pack(fill=tk.X, padx=5, pady=5)
        bg_btn_frame = ttk.Frame(bg_frame)
        bg_btn_frame.pack(fill=tk.X)
        ttk.Button(bg_btn_frame, text="Load Background Image", command=self.load_background).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0,2))
        ttk.Button(bg_btn_frame, text="New Blank Canvas...", command=self.create_new_canvas).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(2,0))

        # 2. Asset Layers Section
        assets_frame = ttk.LabelFrame(parent_frame, text="2. Asset Layers", padding=10)
        assets_frame.pack(fill=tk.X, padx=5, pady=5)
        # Create a UI block for each layer defined in our data structure.
        for i, layer_info in enumerate(self.layers):
            self._create_layer_ui(assets_frame, i)

        # 3. Global Generation Settings Section
        gen_frame = ttk.LabelFrame(parent_frame, text="3. Generation Settings (Global)", padding=10)
        gen_frame.pack(fill=tk.X, padx=5, pady=5)
        self._create_generation_settings_ui(gen_frame)

        # 4. Title Engine Section
        title_frame = ttk.LabelFrame(parent_frame, text="4. Title Engine", padding=10)
        title_frame.pack(fill=tk.X, padx=5, pady=5)
        self._create_title_engine_ui(title_frame)

        # 5. Final Actions Section
        action_frame = ttk.LabelFrame(parent_frame, text="5. Actions", padding=10)
        action_frame.pack(fill=tk.X, padx=5, pady=5)
        # The main "Generate" button, styled to stand out.
        ttk.Style().configure("Accent.TButton", font=('Arial', 12, 'bold'), foreground='green')
        ttk.Button(action_frame, text="GENERATE SCENE", command=self.generate_scene, style="Accent.TButton").pack(fill=tk.X, ipady=5, pady=2)
        ttk.Button(action_frame, text="Save Final Image...", command=self.save_scene).pack(fill=tk.X, pady=2)

    def _create_layer_ui(self, parent, layer_index):
        """Creates the specific UI block for a single asset layer."""
        layer_info = self.layers[layer_index]
        frame = ttk.LabelFrame(parent, text=layer_info["name"], padding=5)
        frame.pack(fill=tk.X, expand=True, pady=5)

        # Per-Layer Placement Control
        placement_frame = ttk.Frame(frame)
        placement_frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(placement_frame, text="Placement:").pack(side=tk.LEFT, padx=(0, 5))
        ttk.OptionMenu(placement_frame, layer_info["placement_var"], "Anywhere", "Anywhere", "Top Half", "Bottom Half", "Left Half", "Right Half").pack(side=tk.LEFT, expand=True, fill=tk.X)

        # Treeview for listing assets
        tree = ttk.Treeview(frame, columns=("asset", "count"), show="headings", height=4)
        tree.heading("asset", text="Asset Name")
        tree.heading("count", text="# (Dbl-Click to Edit)")
        tree.column("asset", width=150)
        tree.column("count", width=110, anchor='center')

        # --- Checkbox Simulation in Treeview ---
        # Tkinter's Treeview doesn't have built-in checkboxes. We simulate them with images and tags.
        tree.tag_configure('checked', image=self.get_check_image(True))
        tree.tag_configure('unchecked', image=self.get_check_image(False))
        # Bind events to handle user interaction.
        tree.bind('<Button-1>', lambda event, t=tree: self.toggle_check(event, t)) # Left-click to toggle check.
        tree.bind('<Double-1>', lambda event, t=tree: self.edit_tree_cell(event, t)) # Double-click to edit count.
        tree.pack(fill=tk.X, expand=True)
        layer_info["tree"] = tree # Store a reference to the treeview in our layer data.

        # Layer Action Buttons
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X, pady=(5,0))
        ttk.Button(btn_frame, text="Add Assets...", command=lambda i=layer_index: self.load_assets(i)).pack(side=tk.LEFT, expand=True, fill=tk.X)
        ttk.Button(btn_frame, text="Clear", command=lambda i=layer_index: self.clear_layer(i)).pack(side=tk.LEFT, expand=True, fill=tk.X)

        # Bulk Selection Buttons
        select_frame = ttk.Frame(frame)
        select_frame.pack(fill=tk.X, pady=(2,0))
        ttk.Button(select_frame, text="Select All", command=lambda i=layer_index: self.select_all(i)).pack(side=tk.LEFT, expand=True, fill=tk.X)
        ttk.Button(select_frame, text="Select None", command=lambda i=layer_index: self.select_none(i)).pack(side=tk.LEFT, expand=True, fill=tk.X)

    def _create_generation_settings_ui(self, parent):
        """Creates controls for global settings like scale and rotation."""
        ttk.Label(parent, text="Scale (Min/Max %):").grid(row=0, column=0, sticky="w")
        self.scale_min_var = tk.DoubleVar(value=50); self.scale_max_var = tk.DoubleVar(value=100)
        ttk.Scale(parent, from_=1, to=150, variable=self.scale_min_var).grid(row=1, column=0, columnspan=2, sticky='ew')
        ttk.Scale(parent, from_=1, to=150, variable=self.scale_max_var).grid(row=2, column=0, columnspan=2, sticky='ew')

        ttk.Label(parent, text="Rotation (Min/Max °):").grid(row=3, column=0, sticky="w", pady=(5,0))
        self.rot_min_var = tk.DoubleVar(value=0); self.rot_max_var = tk.DoubleVar(value=0)
        ttk.Scale(parent, from_=-180, to=180, variable=self.rot_min_var).grid(row=4, column=0, columnspan=2, sticky='ew')
        ttk.Scale(parent, from_=-180, to=180, variable=self.rot_max_var).grid(row=5, column=0, columnspan=2, sticky='ew')

    def _create_title_engine_ui(self, parent):
        """Creates all the controls for adding a text title to the image."""
        # Variables to hold the state of the title controls.
        self.title_text_var = tk.StringVar(value="My Awesome Scene")
        self.title_font_var = tk.StringVar(value="Arial") # Default font
        self.title_size_var = tk.IntVar(value=72)
        self.title_pos_var = tk.StringVar(value="Center")
        self.title_color_var = tk.StringVar(value="#FFFFFF") # White
        self.shadow_enabled_var = tk.BooleanVar(value=True)
        self.shadow_color_var = tk.StringVar(value="#000000") # Black

        # Laying out the controls in a grid for neat alignment.
        parent.columnconfigure(1, weight=1) # Make the entry/dropdown column expandable.
        ttk.Label(parent, text="Title Text:").grid(row=0, column=0, sticky="w")
        ttk.Entry(parent, textvariable=self.title_text_var).grid(row=0, column=1, columnspan=2, sticky="ew")

        ttk.Label(parent, text="Font:").grid(row=1, column=0, sticky="w")
        ttk.Combobox(parent, textvariable=self.title_font_var, values=self.system_fonts, state='readonly').grid(row=1, column=1, columnspan=2, sticky="ew")

        ttk.Label(parent, text="Size:").grid(row=2, column=0, sticky="w")
        ttk.Spinbox(parent, from_=10, to=500, textvariable=self.title_size_var).grid(row=2, column=1, columnspan=2, sticky="ew")

        ttk.Label(parent, text="Position:").grid(row=3, column=0, sticky="w")
        ttk.OptionMenu(parent, self.title_pos_var, "Center", "Center", "Top Center", "Bottom Center", "Top Left", "Bottom Right").grid(row=3, column=1, columnspan=2, sticky="ew")

        ttk.Label(parent, text="Color:").grid(row=4, column=0, sticky="w")
        ttk.Button(parent, text="Choose...", command=lambda: self.choose_color(self.title_color_var)).grid(row=4, column=1, sticky="ew")

        ttk.Checkbutton(parent, text="Enable Shadow", variable=self.shadow_enabled_var).grid(row=5, column=0, sticky="w")
        ttk.Button(parent, text="Shadow Color...", command=lambda: self.choose_color(self.shadow_color_var)).grid(row=5, column=1, sticky="ew")

        # Button to apply the title settings to the current image.
        ttk.Button(parent, text="Add/Update Title", command=self.add_title).grid(row=6, column=0, columnspan=2, sticky="ew", pady=5)


    # --- 2.3. UI INTERACTION & HELPER METHODS ---
    # These methods handle events from the GUI and provide small utility functions.

    def choose_color(self, var_to_update):
        """Opens a color chooser dialog and updates a given StringVar with the chosen color."""
        color_code = colorchooser.askcolor(title="Choose color")
        if color_code and color_code[1]: # The chosen color is in hex format at index 1.
            var_to_update.set(color_code[1])

    def get_check_image(self, checked):
        """Creates or retrieves a small checkmark image for the Treeview."""
        # We cache the images so they are not re-created every time.
        if not hasattr(self, '_check_images'):
            self._check_images = {}
        if checked in self._check_images:
            return self._check_images[checked]

        # Create a tiny 16x16 transparent image.
        im = Image.new("RGBA", (16, 16), (0,0,0,0))
        draw = ImageDraw.Draw(im)
        if checked:
            # Draw a blue box with a white checkmark.
            draw.rectangle((2,2,12,12), outline="black", fill="dodgerblue")
            draw.line([(4,8), (7,11), (12,4)], fill="white", width=2)
        else:
            # Draw an empty box.
            draw.rectangle((2,2,12,12), outline="black")

        # Convert the PIL image to a Tkinter-compatible PhotoImage and cache it.
        photo = ImageTk.PhotoImage(im)
        ## FIX: The variable name was inconsistent. It must be `_check_images` to match the rest of the method.
        self._check_images[checked] = photo
        return photo

    def toggle_check(self, event, tree):
        """Toggles the 'checked'/'unchecked' tag of a clicked Treeview item."""
        # Identify the item that was clicked.
        item_id = tree.identify_row(event.y)
        if item_id: # If a valid item was clicked...
            tags = list(tree.item(item_id, 'tags'))
            # Swap the tag to change the checkbox image.
            if 'checked' in tags:
                tags.remove('checked')
                tags.append('unchecked')
            else:
                tags.remove('unchecked')
                tags.append('checked')
            tree.item(item_id, tags=tags)

    def select_all(self, layer_index):
        """Sets all assets in a given layer's tree to 'checked'."""
        tree = self.layers[layer_index]["tree"]
        for item_id in tree.get_children():
            tree.item(item_id, tags=('checked',))

    def select_none(self, layer_index):
        """Sets all assets in a given layer's tree to 'unchecked'."""
        tree = self.layers[layer_index]["tree"]
        for item_id in tree.get_children():
            tree.item(item_id, tags=('unchecked',))

    def edit_tree_cell(self, event, tree):
        """Handles the double-click event to make a treeview cell editable."""
        item_id = tree.identify_row(event.y)
        column_id = tree.identify_column(event.x)

        # Only allow editing the second column ('count').
        if not item_id or column_id != "#2":
            return

        # Get the position and size of the cell.
        x, y, width, height = tree.bbox(item_id, column_id)

        # Create a temporary Entry widget and place it exactly over the cell.
        val = tree.set(item_id, column_id)
        entry = ttk.Entry(tree, justify='center')
        entry.place(x=x, y=y, width=width, height=height)
        entry.insert(0, val)
        entry.focus_force() # Give focus to the entry widget.

        # Bind events to the entry widget to save the value and destroy it.
        entry.bind('<Return>', lambda e: self.save_cell_edit(entry, tree, item_id, column_id))
        entry.bind('<FocusOut>', lambda e: self.save_cell_edit(entry, tree, item_id, column_id))

    def save_cell_edit(self, entry, tree, item_id, column_id):
        """Saves the value from the temporary Entry widget back to the Treeview."""
        new_val = entry.get()
        # Validate that the input is a positive integer.
        try:
            if int(new_val) > 0:
                tree.set(item_id, column_id, int(new_val))
            else:
                tree.set(item_id, column_id, 1) # Default to 1 if not positive.
        except ValueError:
            # If the input is not a number, do nothing and keep the old value.
            pass
        entry.destroy() # Remove the temporary entry widget.

    # --- 2.4. CORE FUNCTIONALITY METHODS ---
    # These methods perform the main logic of the application.

    def create_new_canvas(self):
        """Opens a dialog to create a new blank background image."""
        # Use a Toplevel window as a custom dialog.
        dialog = tk.Toplevel(self.root)
        dialog.title("New Canvas")
        dialog.transient(self.root) # Keep dialog on top of the main window.
        dialog.grab_set() # Make the dialog modal (block interaction with main window).

        # Widgets for the dialog
        ttk.Label(dialog, text="Width:").grid(row=0, column=0, padx=5, pady=5, sticky='w')
        width_var = tk.IntVar(value=1920)
        ttk.Entry(dialog, textvariable=width_var).grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(dialog, text="Height:").grid(row=1, column=0, padx=5, pady=5, sticky='w')
        height_var = tk.IntVar(value=1080)
        ttk.Entry(dialog, textvariable=height_var).grid(row=1, column=1, padx=5, pady=5)

        color_var = tk.StringVar(value="#4682B4") # A pleasant SteelBlue default
        color_label = ttk.Label(dialog, text="        ", background=color_var.get(), relief=tk.SUNKEN)

        def pick_color():
            code = colorchooser.askcolor(title="Choose background color", parent=dialog)
            if code and code[1]:
                color_var.set(code[1])
                color_label.config(background=code[1])

        ttk.Label(dialog, text="Color:").grid(row=2, column=0, padx=5, pady=5, sticky='w')
        color_label.grid(row=2, column=1, sticky='ew', padx=5, pady=5)
        ttk.Button(dialog, text="Choose...", command=pick_color).grid(row=2, column=2, padx=5, pady=5)

        def on_create():
            """Function called when the 'Create' button is pressed."""
            W, H = width_var.get(), height_var.get()
            if W > 0 and H > 0:
                # Create the new blank PIL Image.
                self.background_image = Image.new("RGBA", (W, H), color_var.get())
                # Initialize the generation states.
                self.generated_scene_no_title = self.background_image.copy()
                self.display_image(self.generated_scene_no_title)
                self.status_var.set(f"Created new {W}x{H} canvas.")
                dialog.destroy() # Close the dialog.

        ttk.Button(dialog, text="Create", command=on_create).grid(row=3, column=0, columnspan=3, pady=10)
        self.root.wait_window(dialog) # Wait for the dialog to be closed before continuing.

    def load_background(self):
        """Opens a file dialog to load a background image."""
        path = filedialog.askopenfilename(filetypes=[("Images", "*.png *.jpg *.jpeg")])
        if not path: return
        self.background_image = Image.open(path).convert("RGBA")
        # Reset the generation states with the new background.
        self.generated_scene_no_title = self.background_image.copy()
        self.display_image(self.generated_scene_no_title)
        self.status_var.set(f"Loaded background: {os.path.basename(path)}")

    def load_assets(self, layer_index):
        """Opens a file dialog to load one or more assets into a layer."""
        paths = filedialog.askopenfilenames(title=f"Select assets for {self.layers[layer_index]['name']}", filetypes=[("PNG Images", "*.png")])
        if not paths: return

        layer = self.layers[layer_index]
        for path in paths:
            # Check for duplicates before adding.
            if path not in [d['path'] for d in layer["assets"].values()]:
                asset_name = os.path.basename(path)
                # Add the asset to the treeview with default count 1 and unchecked.
                item_id = layer["tree"].insert("", "end", values=(asset_name, 1), tags=('unchecked',))
                # Store the asset's data in our layer dictionary, using the tree item ID as the key.
                layer["assets"][item_id] = {"path": path, "name": asset_name}
        self.status_var.set(f"Added {len(paths)} assets to Layer {layer_index+1}.")

    def clear_layer(self, layer_index):
        """Removes all assets from a specific layer."""
        layer = self.layers[layer_index]
        layer["tree"].delete(*layer["tree"].get_children()) # Clear the UI
        layer["assets"].clear() # Clear the data

    def generate_scene(self):
        """The main generation logic. Places all selected assets onto the background."""
        if not self.background_image:
            messagebox.showerror("Error", "Please load a background or create a new canvas first.")
            return

        self.status_var.set("Generating scene... This may take a moment.")
        self.root.update_idletasks() # Force UI update to show the status message.

        # Always start fresh from the original background image.
        canvas = self.background_image.copy()
        W, H = canvas.size

        # Process layers in order (0, 1, 2) so they are drawn on top of each other correctly.
        for layer_info in self.layers:
            tree = layer_info["tree"]
            # Get only the assets that are checked in the treeview.
            checked_item_ids = tree.tag_has('checked')

            for item_id in checked_item_ids:
                asset_path = layer_info["assets"][item_id]["path"]
                try:
                    # Get the instance count from the treeview.
                    count = int(tree.item(item_id, 'values')[1])
                except (ValueError, IndexError):
                    count = 1 # Default to 1 if invalid.

                # For each instance of the asset...
                for _ in range(count):
                    try:
                        asset_img = Image.open(asset_path).convert("RGBA")

                        # --- Apply Transformations ---
                        # Scale
                        min_s, max_s = min(self.scale_min_var.get(), self.scale_max_var.get()), max(self.scale_min_var.get(), self.scale_max_var.get())
                        scale = random.uniform(min_s / 100.0, max_s / 100.0)
                        new_size = (int(asset_img.width * scale), int(asset_img.height * scale))
                        asset_img = asset_img.resize(new_size, Image.Resampling.LANCZOS)

                        # Rotation
                        min_r, max_r = min(self.rot_min_var.get(), self.rot_max_var.get()), max(self.rot_min_var.get(), self.rot_max_var.get())
                        angle = random.uniform(min_r, max_r)
                        asset_img = asset_img.rotate(angle, expand=True, resample=Image.Resampling.BICUBIC)

                        # --- Placement ---
                        w, h = asset_img.size
                        placement_zone = layer_info["placement_var"].get() # Use the per-layer setting.
                        x_range, y_range = self.get_placement_zone(W, H, w, h, placement_zone)

                        # Ensure the placement range is valid before trying to pick a random spot.
                        if x_range[1] < x_range[0] or y_range[1] < y_range[0]: continue
                        pos = (random.randint(*x_range), random.randint(*y_range))

                        # Paste the transformed asset onto the canvas, using its alpha channel as a mask.
                        canvas.paste(asset_img, pos, asset_img)
                    except Exception as e:
                        print(f"Error processing asset instance {asset_path}: {e}")

        # --- Finalize and Display ---
        # Save the result of the asset generation.
        self.generated_scene_no_title = canvas
        # Now, automatically render the current title settings on top of the newly generated scene.
        final_image = self._render_title_on_image(self.generated_scene_no_title)
        # Display the final image.
        self.display_image(final_image)
        self.status_var.set("Scene generation complete!")

    def get_placement_zone(self, W, H, w, h, zone):
        """Calculates the valid (x, y) coordinate ranges based on a placement zone string."""
        # Start with the full canvas area, adjusted for the asset's size.
        x_range, y_range = (0, max(0, W - w)), (0, max(0, H - h))
        # Narrow the range based on the selected zone.
        if zone == "Top Half": y_range = (0, max(0, H//2 - h))
        elif zone == "Bottom Half": y_range = (H//2, max(H//2, H - h))
        elif zone == "Left Half": x_range = (0, max(0, W//2 - w))
        elif zone == "Right Half": x_range = (W//2, max(W//2, W - w))
        return x_range, y_range

    def _render_title_on_image(self, base_image):
        """Takes a PIL image and draws the current title on it. Returns a new image."""
        # If there's no title text, just return the base image.
        if not self.title_text_var.get().strip():
            return base_image

        image_with_title = base_image.copy()
        draw = ImageDraw.Draw(image_with_title)
        text = self.title_text_var.get()
        font_name = self.title_font_var.get()
        font_size = self.title_size_var.get()

        # Load the font file.
        try:
            font_path = fm.findfont(fm.FontProperties(family=font_name))
            font = ImageFont.truetype(font_path, font_size)
        except Exception as e:
            print(f"Font error: {e}. Falling back to default.")
            font = ImageFont.load_default()

        # Calculate text position.
        W, H = image_with_title.size
        bbox = draw.textbbox((0,0), text, font=font)
        text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]

        pos_map = {
            "Center": ((W-text_w)//2, (H-text_h)//2), "Top Center": ((W-text_w)//2, 10),
            "Bottom Center": ((W-text_w)//2, H-text_h-10), "Top Left": (10, 10),
            "Bottom Right": (W-text_w-10, H-text_h-10)
        }
        x, y = pos_map.get(self.title_pos_var.get(), (10,10))

        # Draw shadow first, if enabled.
        if self.shadow_enabled_var.get():
            shadow_offset = int(font_size * 0.05) + 2 # Dynamic shadow offset based on font size
            draw.text((x + shadow_offset, y + shadow_offset), text, font=font, fill=self.shadow_color_var.get())

        # Draw the main text on top of the shadow.
        draw.text((x,y), text, font=font, fill=self.title_color_var.get())
        return image_with_title

    def add_title(self):
        """Applies or updates the title on the most recently generated scene."""
        if not self.generated_scene_no_title:
            messagebox.showerror("Error", "Generate a scene first before adding a title.")
            return

        self.status_var.set("Adding/Updating title...")
        self.root.update_idletasks()

        # Re-render the title on top of the clean, title-less generated scene.
        final_image = self._render_title_on_image(self.generated_scene_no_title)
        self.display_image(final_image)
        self.status_var.set("Title added/updated.")

    def save_scene(self):
        """Saves the currently displayed image to a file."""
        if not self.current_scene_image:
            messagebox.showerror("Error", "No scene to save.")
            return

        filepath = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG", "*.png"), ("JPEG", "*.jpg")])
        if not filepath: return

        # The image to save is the one currently on screen, which includes the title.
        image_to_save = self.current_scene_image

        # If saving as JPG, convert from RGBA to RGB to avoid errors.
        if filepath.lower().endswith(('.jpg', '.jpeg')):
            image_to_save = image_to_save.convert('RGB')

        image_to_save.save(filepath)
        self.status_var.set(f"Scene saved to {filepath}")

    def display_image(self, pil_image):
        """Updates the image label to show a new PIL image."""
        # Store a reference to the full-resolution PIL image.
        self.current_scene_image = pil_image

        # Get the size of the display area to create a properly-sized thumbnail.
        display_w = self.image_label.winfo_width()
        display_h = self.image_label.winfo_height()
        # Fallback size if the window isn't drawn yet.
        if display_w <= 1 or display_h <= 1:
            display_w, display_h = 800, 600

        # Create a copy and resize it to fit the display label without modifying the original.
        img_copy = pil_image.copy()
        img_copy.thumbnail((display_w - 10, display_h - 10), Image.Resampling.LANCZOS)

        # Convert to a Tkinter-compatible image and update the label.
        self.tk_image = ImageTk.PhotoImage(img_copy)
        self.image_label.config(image=self.tk_image)

# === 3. APPLICATION LAUNCHER ===
# This standard Python construct ensures the code inside only runs when the script is executed directly.
if __name__ == "__main__":
    root = tk.Tk()      # Create the main window.
    app = SceneEditorApp(root) # Create an instance of our application class.
    root.mainloop()     # Start the Tkinter event loop to run the application.