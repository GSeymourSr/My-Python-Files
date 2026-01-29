# === 1. IMPORTS ===
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser
from PIL import Image, ImageTk, ImageDraw, ImageFont
import os
import random
import uuid  # For giving each placed asset a unique ID
import matplotlib.font_manager as fm
from tkinterdnd2 import DND_FILES, TkinterDnD # For Drag-and-Drop functionality

# === 2. MAIN APPLICATION CLASS ===
class SceneEditorApp:
    # --- 2.1. INITIALIZATION ---
    def __init__(self, root):
        """
        Constructor for the main application. Sets up the window, core data, and UI.
        'root' is the main Tkinter window instance.
        """
        self.root = root
        self.root.title("Advanced Scene Editor (Generator + Editor)")
        self.root.state('zoomed')

        # --- Core Data Structures for Editing ---
        self.background_image = None
        self.generated_scene_no_title = None
        self.current_scene_image = None
        self.tk_image = None
        
        self.asset_cache = {}  # Caches loaded PIL Images to avoid re-reading from disk
        self.placed_assets = []  # The new "source of truth". A list of all asset objects on the canvas.
        self.selected_asset_id = None # Tracks the 'id' of the currently selected asset object.
        self._drag_data = {"x": 0, "y": 0, "item_id": None, "mode": None} # For mouse drag state

        # --- Display Coordinate Mapping ---
        # These are crucial for converting mouse clicks on the displayed thumbnail
        # back to coordinates on the full-resolution image.
        self._display_info = {"thumb_w": 1, "thumb_h": 1, "offset_x": 0, "offset_y": 0, "scale_factor": 1.0}

        # --- Font Loading ---
        try:
            font_paths = fm.findSystemFonts(fontpaths=None, fontext='ttf')
            unique_font_names = {fm.FontProperties(fname=font_path).get_name() for font_path in font_paths}
            self.system_fonts = sorted(list(unique_font_names))
        except Exception as e:
            print(f"Font loading failed: {e}")
            self.system_fonts = ["Arial", "Courier New", "Times New Roman"]

        # --- Layer Data ---
        self.layers = [
            {"name": "Layer 1 (e.g., Seafloor)", "assets": {}, "tree": None, "placement_var": tk.StringVar(value="Anywhere")},
            {"name": "Layer 2 (e.g., Coral/Plants)", "assets": {}, "tree": None, "placement_var": tk.StringVar(value="Anywhere")},
            {"name": "Layer 3 (e.g., Fish/Creatures)", "assets": {}, "tree": None, "placement_var": tk.StringVar(value="Anywhere")}
        ]

        # --- Main Layout ---
        self.control_panel = ttk.Frame(root, width=450)
        self.control_panel.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
        self.control_panel.pack_propagate(False)

        self.image_frame = ttk.Frame(root)
        self.image_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        # --- Create UI Elements ---
        self._create_scrollable_controls()
        # Using a Canvas is better for capturing precise mouse events than a Label
        self.canvas = tk.Canvas(self.image_frame, background='black', highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.status_var = tk.StringVar(value="Welcome! Load a background or drag assets onto a layer.")
        ttk.Label(root, textvariable=self.status_var, relief=tk.SUNKEN).pack(side=tk.BOTTOM, fill=tk.X)

        # --- Event Bindings for Direct Manipulation ---
        self.canvas.bind("<ButtonPress-1>", self.on_canvas_press)
        self.canvas.bind("<B1-Motion>", self.on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_canvas_release)
        self.root.bind("<Delete>", self.delete_selected_asset)
        self.root.bind("<BackSpace>", self.delete_selected_asset) # For convenience

    def _create_scrollable_controls(self):
        # ... (This method is unchanged)
        canvas = tk.Canvas(self.control_panel)
        scrollbar = ttk.Scrollbar(self.control_panel, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self._populate_controls(scrollable_frame)

    def _populate_controls(self, parent_frame):
        # ... (This method is largely unchanged, just updating commands)
        bg_frame = ttk.LabelFrame(parent_frame, text="1. Background", padding=10)
        bg_frame.pack(fill=tk.X, padx=5, pady=5)
        bg_btn_frame = ttk.Frame(bg_frame)
        bg_btn_frame.pack(fill=tk.X)
        ttk.Button(bg_btn_frame, text="Load Background Image", command=self.load_background).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0,2))
        ttk.Button(bg_btn_frame, text="New Blank Canvas...", command=self.create_new_canvas).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(2,0))
        
        assets_frame = ttk.LabelFrame(parent_frame, text="2. Asset Layers", padding=10)
        assets_frame.pack(fill=tk.X, padx=5, pady=5)
        for i, layer_info in enumerate(self.layers):
            self._create_layer_ui(assets_frame, i)

        gen_frame = ttk.LabelFrame(parent_frame, text="3. Generation Settings (Global)", padding=10)
        gen_frame.pack(fill=tk.X, padx=5, pady=5)
        self._create_generation_settings_ui(gen_frame)

        title_frame = ttk.LabelFrame(parent_frame, text="4. Title Engine", padding=10)
        title_frame.pack(fill=tk.X, padx=5, pady=5)
        self._create_title_engine_ui(title_frame)

        action_frame = ttk.LabelFrame(parent_frame, text="5. Actions", padding=10)
        action_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Style().configure("Accent.TButton", font=('Arial', 12, 'bold'), foreground='green')
        ttk.Button(action_frame, text="GENERATE NEW SCENE", command=self.generate_scene, style="Accent.TButton").pack(fill=tk.X, ipady=5, pady=2)
        ttk.Button(action_frame, text="Save Final Image...", command=self.save_scene).pack(fill=tk.X, pady=2)

    def _create_layer_ui(self, parent, layer_index):
        # ... (This method is largely unchanged, but now enables drop targets)
        layer_info = self.layers[layer_index]
        frame = ttk.LabelFrame(parent, text=layer_info["name"], padding=5)
        frame.pack(fill=tk.X, expand=True, pady=5)
        
        # ... (Placement control is the same)
        placement_frame = ttk.Frame(frame)
        placement_frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(placement_frame, text="Placement:").pack(side=tk.LEFT, padx=(0, 5))
        ttk.OptionMenu(placement_frame, layer_info["placement_var"], "Anywhere", "Anywhere", "Top Half", "Bottom Half", "Left Half", "Right Half").pack(side=tk.LEFT, expand=True, fill=tk.X)

        tree = ttk.Treeview(frame, columns=("asset", "count"), show="headings", height=4)
        tree.heading("asset", text="Asset Name")
        tree.heading("count", text="# (Dbl-Click to Edit)")
        tree.column("asset", width=150)
        tree.column("count", width=110, anchor='center')

        # --- Enable Drag and Drop on the Treeview ---
        tree.drop_target_register(DND_FILES)
        tree.dnd_bind('<<Drop>>', lambda e, i=layer_index: self.handle_drop(e, i))
        
        # ... (Rest of the method is the same)
        tree.tag_configure('checked', image=self.get_check_image(True))
        tree.tag_configure('unchecked', image=self.get_check_image(False))
        tree.bind('<Button-1>', lambda event, t=tree: self.toggle_check(event, t))
        tree.bind('<Double-1>', lambda event, t=tree: self.edit_tree_cell(event, t))
        tree.pack(fill=tk.X, expand=True)
        layer_info["tree"] = tree
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X, pady=(5,0))
        ttk.Button(btn_frame, text="Add Assets...", command=lambda i=layer_index: self.load_assets(i)).pack(side=tk.LEFT, expand=True, fill=tk.X)
        ttk.Button(btn_frame, text="Clear", command=lambda i=layer_index: self.clear_layer(i)).pack(side=tk.LEFT, expand=True, fill=tk.X)
        select_frame = ttk.Frame(frame)
        select_frame.pack(fill=tk.X, pady=(2,0))
        ttk.Button(select_frame, text="Select All", command=lambda i=layer_index: self.select_all(i)).pack(side=tk.LEFT, expand=True, fill=tk.X)
        ttk.Button(select_frame, text="Select None", command=lambda i=layer_index: self.select_none(i)).pack(side=tk.LEFT, expand=True, fill=tk.X)
    
    # --- UI Creation methods that are unchanged ---
    def _create_generation_settings_ui(self, parent): # Unchanged
        ttk.Label(parent, text="Scale (Min/Max %):").grid(row=0, column=0, sticky="w")
        self.scale_min_var = tk.DoubleVar(value=50); self.scale_max_var = tk.DoubleVar(value=100)
        ttk.Scale(parent, from_=1, to=200, variable=self.scale_min_var).grid(row=1, column=0, columnspan=2, sticky='ew')
        ttk.Scale(parent, from_=1, to=200, variable=self.scale_max_var).grid(row=2, column=0, columnspan=2, sticky='ew')
        ttk.Label(parent, text="Rotation (Min/Max °):").grid(row=3, column=0, sticky="w", pady=(5,0))
        self.rot_min_var = tk.DoubleVar(value=0); self.rot_max_var = tk.DoubleVar(value=0)
        ttk.Scale(parent, from_=-180, to=180, variable=self.rot_min_var).grid(row=4, column=0, columnspan=2, sticky='ew')
        ttk.Scale(parent, from_=-180, to=180, variable=self.rot_max_var).grid(row=5, column=0, columnspan=2, sticky='ew')
    
    def _create_title_engine_ui(self, parent): # Unchanged
        self.title_text_var = tk.StringVar(value="My Awesome Scene")
        self.title_font_var = tk.StringVar(value="Arial"); self.title_size_var = tk.IntVar(value=72)
        self.title_pos_var = tk.StringVar(value="Center"); self.title_color_var = tk.StringVar(value="#FFFFFF")
        self.shadow_enabled_var = tk.BooleanVar(value=True); self.shadow_color_var = tk.StringVar(value="#000000")
        parent.columnconfigure(1, weight=1)
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
        ttk.Button(parent, text="Add/Update Title", command=self.add_title).grid(row=6, column=0, columnspan=2, sticky="ew", pady=5)

    def get_check_image(self, checked): # Unchanged
        if not hasattr(self, '_check_images'): self._check_images = {}
        if checked in self._check_images: return self._check_images[checked]
        im = Image.new("RGBA", (16, 16), (0,0,0,0)); draw = ImageDraw.Draw(im)
        if checked:
            draw.rectangle((2,2,12,12), outline="black", fill="dodgerblue")
            draw.line([(4,8), (7,11), (12,4)], fill="white", width=2)
        else:
            draw.rectangle((2,2,12,12), outline="black")
        photo = ImageTk.PhotoImage(im)
        self._check_images[checked] = photo
        return photo

    # --- 2.3. NEW & REWRITTEN CORE METHODS ---

    def handle_drop(self, event, layer_index):
        """Handles files being dropped onto a specific layer's Treeview."""
        paths = self.root.tk.splitlist(event.data)
        png_paths = [p for p in paths if p.lower().endswith('.png')]
        if png_paths:
            self.load_assets(layer_index, paths=png_paths)
            self.status_var.set(f"Dropped {len(png_paths)} assets into Layer {layer_index + 1}.")
        else:
            self.status_var.set("Drop failed: Only .png files are supported.")

    def load_assets(self, layer_index, paths=None):
        """Loads assets from a file dialog or a provided list of paths."""
        if paths is None:
            paths = filedialog.askopenfilenames(title=f"Select assets for {self.layers[layer_index]['name']}", filetypes=[("PNG Images", "*.png")])
        if not paths: return

        layer = self.layers[layer_index]
        new_assets_count = 0
        for path in paths:
            if path not in self.asset_cache: # Prevent duplicates
                try:
                    # Cache the asset image to prevent re-reading from disk
                    self.asset_cache[path] = Image.open(path).convert("RGBA")
                    asset_name = os.path.basename(path)
                    item_id = layer["tree"].insert("", "end", values=(asset_name, 1), tags=('unchecked',))
                    layer["assets"][item_id] = {"path": path, "name": asset_name}
                    new_assets_count += 1
                except Exception as e:
                    print(f"Failed to load or cache asset {path}: {e}")
        if new_assets_count > 0:
            self.status_var.set(f"Added {new_assets_count} new assets to Layer {layer_index+1}.")

    def generate_scene(self):
        """Populates the canvas with new, randomly generated asset objects."""
        if not self.background_image:
            messagebox.showerror("Error", "Please load a background or create a new canvas first.")
            return

        self.status_var.set("Generating new scene...")
        self.root.update_idletasks()
        
        self.placed_assets.clear()
        self.selected_asset_id = None
        W, H = self.background_image.size

        for i, layer_info in enumerate(self.layers):
            tree = layer_info["tree"]
            checked_item_ids = tree.tag_has('checked')
            for item_id in checked_item_ids:
                asset_data = layer_info["assets"][item_id]
                asset_path = asset_data["path"]
                try:
                    count = int(tree.item(item_id, 'values')[1])
                except (ValueError, IndexError):
                    count = 1

                for _ in range(count):
                    asset_img = self.asset_cache.get(asset_path)
                    if not asset_img: continue
                    
                    min_s, max_s = min(self.scale_min_var.get(), self.scale_max_var.get()), max(self.scale_min_var.get(), self.scale_max_var.get())
                    scale = random.uniform(min_s / 100.0, max_s / 100.0)
                    
                    min_r, max_r = min(self.rot_min_var.get(), self.rot_max_var.get()), max(self.rot_min_var.get(), self.rot_max_var.get())
                    rotation = random.uniform(min_r, max_r)
                    
                    # Temporarily transform to get final size for placement
                    temp_size = (int(asset_img.width * scale), int(asset_img.height * scale))
                    temp_img = asset_img.resize(temp_size, Image.Resampling.LANCZOS)
                    temp_img = temp_img.rotate(rotation, expand=True, resample=Image.Resampling.BICUBIC)
                    w, h = temp_img.size

                    placement_zone = layer_info["placement_var"].get()
                    x_range, y_range = self.get_placement_zone(W, H, w, h, placement_zone)
                    if x_range[1] < x_range[0] or y_range[1] < y_range[0]: continue
                    x, y = (random.randint(*x_range), random.randint(*y_range))

                    # Create the asset object and add it to our list
                    asset_object = {
                        "id": str(uuid.uuid4()),
                        "path": asset_path,
                        "x": x, "y": y,
                        "scale": scale,
                        "rotation": rotation,
                        "layer_index": i,
                        "bbox": (x, y, x + w, y + h) # Initial bounding box
                    }
                    self.placed_assets.append(asset_object)

        self.redraw_canvas()
        self.status_var.set("Scene generation complete! Click assets to edit.")

    def redraw_canvas(self, with_title=True):
        """The main drawing function. Renders all placed assets onto the background."""
        if not self.background_image: return
        
        canvas_image = self.background_image.copy()

        # Sort assets by layer so they are drawn in the correct order
        sorted_assets = sorted(self.placed_assets, key=lambda k: k['layer_index'])
        
        for asset_obj in sorted_assets:
            asset_img = self.asset_cache[asset_obj['path']]
            
            # Apply transformations
            new_size = (int(asset_img.width * asset_obj['scale']), int(asset_img.height * asset_obj['scale']))
            if new_size[0] < 1 or new_size[1] < 1: continue # Skip if scaled too small
            
            transformed_img = asset_img.resize(new_size, Image.Resampling.LANCZOS)
            transformed_img = transformed_img.rotate(asset_obj['rotation'], expand=True, resample=Image.Resampling.BICUBIC)
            
            # Paste onto the main canvas image
            pos = (int(asset_obj['x']), int(asset_obj['y']))
            canvas_image.paste(transformed_img, pos, transformed_img)
            
            # Update the object's bounding box for future clicks
            w, h = transformed_img.size
            asset_obj['bbox'] = (pos[0], pos[1], pos[0] + w, pos[1] + h)

        # Draw selection handles if an asset is selected
        if self.selected_asset_id:
            selected = self.get_asset_by_id(self.selected_asset_id)
            if selected:
                draw = ImageDraw.Draw(canvas_image)
                x1, y1, x2, y2 = selected['bbox']
                draw.rectangle((x1, y1, x2, y2), outline="cyan", width=2)
                handle_size = 10
                # Draw resize handle at bottom-right
                draw.rectangle((x2 - handle_size//2, y2 - handle_size//2, x2 + handle_size//2, y2 + handle_size//2), fill="cyan", outline="black")

        self.generated_scene_no_title = canvas_image
        final_image = self._render_title_on_image(canvas_image) if with_title else canvas_image
        self.display_image(final_image)

    def display_image(self, pil_image):
        """Displays a PIL image, fitting it to the canvas and storing coordinate mapping info."""
        self.current_scene_image = pil_image
        canvas_w, canvas_h = self.canvas.winfo_width(), self.canvas.winfo_height()
        if canvas_w <= 1 or canvas_h <= 1: 
            canvas_w, canvas_h = 800, 600 # Fallback

        img_copy = pil_image.copy()
        img_copy.thumbnail((canvas_w, canvas_h), Image.Resampling.LANCZOS)
        
        # Store info for coordinate conversion
        self._display_info['thumb_w'], self._display_info['thumb_h'] = img_copy.size
        self._display_info['scale_factor'] = self.current_scene_image.width / self._display_info['thumb_w']
        self._display_info['offset_x'] = (canvas_w - self._display_info['thumb_w']) // 2
        self._display_info['offset_y'] = (canvas_h - self._display_info['thumb_h']) // 2
        
        self.tk_image = ImageTk.PhotoImage(img_copy)
        self.canvas.delete("all")
        self.canvas.create_image(self._display_info['offset_x'], self._display_info['offset_y'], anchor=tk.NW, image=self.tk_image)
    
    # --- Direct Manipulation Handlers ---
    
    def _display_to_image_coords(self, event_x, event_y):
        """Converts mouse coordinates on the canvas to coordinates on the full-res image."""
        x = (event_x - self._display_info['offset_x']) * self._display_info['scale_factor']
        y = (event_y - self._display_info['offset_y']) * self._display_info['scale_factor']
        return int(x), int(y)

    def on_canvas_press(self, event):
        """Handles selecting, moving, or resizing an asset."""
        click_x, click_y = self._display_to_image_coords(event.x, event.y)
        
        self.selected_asset_id = None
        # Iterate in reverse draw order to select the topmost asset
        for asset_obj in reversed(sorted(self.placed_assets, key=lambda k: k['layer_index'])):
            x1, y1, x2, y2 = asset_obj['bbox']
            if x1 <= click_x <= x2 and y1 <= click_y <= y2:
                self.selected_asset_id = asset_obj['id']
                self._drag_data['item_id'] = asset_obj['id']
                self._drag_data['x'] = click_x
                self._drag_data['y'] = click_y
                
                # Check if a resize handle was clicked
                handle_size = int(20 * self._display_info['scale_factor']) # Make handle bigger on image
                if (x2 - handle_size) < click_x < x2 and (y2 - handle_size) < click_y < y2:
                    self._drag_data["mode"] = "resize"
                else:
                    self._drag_data["mode"] = "move"
                break
        
        self.redraw_canvas()

    def on_canvas_drag(self, event):
        """Handles moving or resizing the selected asset."""
        if not self._drag_data["item_id"]: return
        
        item = self.get_asset_by_id(self._drag_data["item_id"])
        if not item: return

        new_x, new_y = self._display_to_image_coords(event.x, event.y)
        dx = new_x - self._drag_data['x']
        dy = new_y - self._drag_data['y']

        if self._drag_data["mode"] == "move":
            item['x'] += dx
            item['y'] += dy
        elif self._drag_data["mode"] == "resize":
            # Maintain aspect ratio while resizing
            img = self.asset_cache[item['path']]
            old_w = img.width * item['scale']
            new_w = old_w + dx
            if new_w > 10: # Prevent resizing to zero
                item['scale'] = new_w / img.width

        self._drag_data['x'] = new_x
        self._drag_data['y'] = new_y
        self.redraw_canvas(with_title=False) # Redraw without title for performance

    def on_canvas_release(self, event):
        """Finalizes the drag operation."""
        if self._drag_data['item_id']:
            self.redraw_canvas() # Final redraw with title
        self._drag_data = {"x": 0, "y": 0, "item_id": None, "mode": None}
    
    def delete_selected_asset(self, event=None):
        """Deletes the currently selected asset."""
        if self.selected_asset_id:
            self.placed_assets = [p for p in self.placed_assets if p['id'] != self.selected_asset_id]
            self.selected_asset_id = None
            self.redraw_canvas()
            self.status_var.set("Asset deleted.")

    def get_asset_by_id(self, asset_id):
        """Helper to find a placed asset by its unique ID."""
        for asset_obj in self.placed_assets:
            if asset_obj['id'] == asset_id:
                return asset_obj
        return None
        
    # --- Other Helper and Action Methods (mostly unchanged) ---
    def add_title(self):
        if not self.generated_scene_no_title:
            messagebox.showerror("Error", "Generate a scene first before adding a title.")
            return
        self.redraw_canvas() # Redrawing automatically handles the title
        self.status_var.set("Title added/updated.")
    
    def create_new_canvas(self): # Logic is the same, just triggers redraw
        # ... (dialog creation code is identical to original) ...
        dialog = tk.Toplevel(self.root) # ... full dialog code here ...
        # on_create function:
        # self.background_image = Image.new(...)
        # self.placed_assets.clear()
        # self.selected_asset_id = None
        # self.redraw_canvas()
        # dialog.destroy()
        # (For brevity, I'm omitting the full dialog code which is unchanged)
        dialog = tk.Toplevel(self.root); dialog.title("New Canvas"); dialog.transient(self.root); dialog.grab_set()
        width_var = tk.IntVar(value=1920); height_var = tk.IntVar(value=1080); color_var = tk.StringVar(value="#4682B4")
        ttk.Label(dialog, text="Width:").grid(row=0, column=0, padx=5, pady=5, sticky='w'); ttk.Entry(dialog, textvariable=width_var).grid(row=0, column=1, padx=5, pady=5)
        ttk.Label(dialog, text="Height:").grid(row=1, column=0, padx=5, pady=5, sticky='w'); ttk.Entry(dialog, textvariable=height_var).grid(row=1, column=1, padx=5, pady=5)
        color_label = ttk.Label(dialog, text=" "*8, background=color_var.get(), relief=tk.SUNKEN)
        def pick_color():
            code = colorchooser.askcolor(title="Choose background", parent=dialog)
            if code and code[1]: color_var.set(code[1]); color_label.config(background=code[1])
        ttk.Label(dialog, text="Color:").grid(row=2, column=0, padx=5, pady=5, sticky='w'); color_label.grid(row=2, column=1, sticky='ew'); ttk.Button(dialog, text="Choose...", command=pick_color).grid(row=2, column=2, padx=5, pady=5)
        def on_create():
            W, H = width_var.get(), height_var.get()
            if W > 0 and H > 0:
                self.background_image = Image.new("RGBA", (W, H), color_var.get())
                self.placed_assets.clear(); self.selected_asset_id = None
                self.redraw_canvas(); self.status_var.set(f"Created new {W}x{H} canvas.")
                dialog.destroy()
        ttk.Button(dialog, text="Create", command=on_create).grid(row=3, column=0, columnspan=3, pady=10)

    def load_background(self): # Logic is the same, just triggers redraw
        path = filedialog.askopenfilename(filetypes=[("Images", "*.png *.jpg *.jpeg")])
        if not path: return
        self.background_image = Image.open(path).convert("RGBA")
        self.placed_assets.clear()
        self.selected_asset_id = None
        self.redraw_canvas()
        self.status_var.set(f"Loaded background: {os.path.basename(path)}")

    def save_scene(self): # Unchanged
        if not self.current_scene_image:
            messagebox.showerror("Error", "No scene to save."); return
        filepath = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG", "*.png"), ("JPEG", "*.jpg")])
        if not filepath: return
        image_to_save = self.current_scene_image
        if filepath.lower().endswith(('.jpg', '.jpeg')):
            image_to_save = image_to_save.convert('RGB')
        image_to_save.save(filepath)
        self.status_var.set(f"Scene saved to {filepath}")
    
    # ... All other helper methods like clear_layer, toggle_check, edit_tree_cell,
    # _render_title_on_image, get_placement_zone, etc. are identical to the original
    # and are omitted here for brevity but should be included in the final file.
    def clear_layer(self, layer_index): # Unchanged
        layer = self.layers[layer_index]; tree = layer["tree"]
        for item_id in tree.get_children():
            path = layer["assets"][item_id]["path"]
            # We don't remove from asset_cache, might be used by another layer
        tree.delete(*tree.get_children()); layer["assets"].clear()
    def toggle_check(self, event, tree): # Unchanged
        item_id = tree.identify_row(event.y)
        if item_id:
            tags = list(tree.item(item_id, 'tags'))
            if 'checked' in tags: tags.remove('checked'); tags.append('unchecked')
            else: tags.remove('unchecked'); tags.append('checked')
            tree.item(item_id, tags=tags)
    def select_all(self, layer_index): # Unchanged
        tree = self.layers[layer_index]["tree"]
        for item_id in tree.get_children(): tree.item(item_id, tags=('checked',))
    def select_none(self, layer_index): # Unchanged
        tree = self.layers[layer_index]["tree"]
        for item_id in tree.get_children(): tree.item(item_id, tags=('unchecked',))
    def edit_tree_cell(self, event, tree): # Unchanged
        item_id = tree.identify_row(event.y); column_id = tree.identify_column(event.x)
        if not item_id or column_id != "#2": return
        x, y, width, height = tree.bbox(item_id, column_id)
        val = tree.set(item_id, column_id); entry = ttk.Entry(tree, justify='center')
        entry.place(x=x, y=y, width=width, height=height); entry.insert(0, val); entry.focus_force()
        entry.bind('<Return>', lambda e: self.save_cell_edit(entry, tree, item_id, column_id))
        entry.bind('<FocusOut>', lambda e: self.save_cell_edit(entry, tree, item_id, column_id))
    def save_cell_edit(self, entry, tree, item_id, column_id): # Unchanged
        new_val = entry.get()
        try:
            if int(new_val) > 0: tree.set(item_id, column_id, int(new_val))
            else: tree.set(item_id, column_id, 1)
        except ValueError: pass
        entry.destroy()
    def get_placement_zone(self, W, H, w, h, zone): # Unchanged
        x_range, y_range = (0, max(0, W - w)), (0, max(0, H - h))
        if zone == "Top Half": y_range = (0, max(0, H//2 - h))
        elif zone == "Bottom Half": y_range = (H//2, max(H//2, H - h))
        elif zone == "Left Half": x_range = (0, max(0, W//2 - w))
        elif zone == "Right Half": x_range = (W//2, max(W//2, W - w))
        return x_range, y_range
    def _render_title_on_image(self, base_image): # Unchanged
        if not self.title_text_var.get().strip(): return base_image
        image_with_title = base_image.copy(); draw = ImageDraw.Draw(image_with_title)
        text = self.title_text_var.get(); font_name = self.title_font_var.get(); font_size = self.title_size_var.get()
        try:
            font_path = fm.findfont(fm.FontProperties(family=font_name))
            font = ImageFont.truetype(font_path, font_size)
        except Exception: font = ImageFont.load_default()
        W, H = image_with_title.size; bbox = draw.textbbox((0,0), text, font=font)
        text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        pos_map = {"Center": ((W-text_w)//2, (H-text_h)//2), "Top Center": ((W-text_w)//2, 10),"Bottom Center": ((W-text_w)//2, H-text_h-10), "Top Left": (10, 10),"Bottom Right": (W-text_w-10, H-text_h-10)}
        x, y = pos_map.get(self.title_pos_var.get(), (10,10))
        if self.shadow_enabled_var.get():
            shadow_offset = int(font_size * 0.05) + 2
            draw.text((x + shadow_offset, y + shadow_offset), text, font=font, fill=self.shadow_color_var.get())
        draw.text((x,y), text, font=font, fill=self.title_color_var.get())
        return image_with_title
    def choose_color(self, var_to_update): # Unchanged
        color_code = colorchooser.askcolor(title="Choose color")
        if color_code and color_code[1]: var_to_update.set(color_code[1])


# === 3. APPLICATION LAUNCHER (MODIFIED FOR DND) ===
if __name__ == "__main__":
    # To use tkinterdnd2, the root must be a TkinterDnD.Tk() instance.
    root = TkinterDnD.Tk()
    app = SceneEditorApp(root)
    root.mainloop()