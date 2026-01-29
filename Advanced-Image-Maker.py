# ==================================================
# ===	"Advanced Scene Editor by GregSeymourAI"   ==
# ==================================================
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser
from PIL import Image, ImageTk, ImageDraw, ImageFont
import os
import random
import uuid
import math
import matplotlib.font_manager as fm
from tkinterdnd2 import DND_FILES, TkinterDnD

# === 2. MAIN APPLICATION CLASS ===
class SceneEditorApp:
    # --- 2.1. INITIALIZATION ---
    def __init__(self, root):
        self.root = root
        self.root.title("Advanced Scene Editor by GregSeymouAI")
        self.root.state('zoomed')

        # --- Core Data Structures ---
        self.background_image = None; self.generated_scene_no_title = None
        self.current_scene_image = None; self.tk_image = None
        self.asset_cache = {}; self.thumbnail_cache = {}; self.composite_image_cache = {}
        self.placed_assets = []; self.selected_asset_id = None
        self._drag_data = {}

        # --- Pan & Zoom State ---
        self._zoom_level = 1.0; self._view_x = 0; self._view_y = 0
        self._pan_start_x = 0; self._pan_start_y = 0
        
        # --- Font Loading ---
        try: self.system_fonts = sorted({fm.FontProperties(fname=p).get_name() for p in fm.findSystemFonts(fontext='ttf')})
        except Exception: self.system_fonts = ["Arial", "Courier New", "Times New Roman"]

        # --- Layer Data Structure ---
        self.layers = []
        for i in range(3):
            self.layers.append({
                "name": f"Layer {i+1}", "assets": {}, "tree": None,
                "placement_var": tk.StringVar(value="Anywhere"),
                "scale_min_var": tk.DoubleVar(value=50), "scale_max_var": tk.DoubleVar(value=100),
                "rot_min_var": tk.DoubleVar(value=0), "rot_max_var": tk.DoubleVar(value=0)
            })

        self.setup_styles()

        # --- Main UI Layout ---
        self.paned_window = ttk.PanedWindow(root, orient=tk.HORIZONTAL)
        self.paned_window.pack(fill=tk.BOTH, expand=True)
        self.control_panel = ttk.Frame(self.paned_window, width=450); self.paned_window.add(self.control_panel, weight=0)
        self.image_frame = ttk.Frame(self.paned_window); self.paned_window.add(self.image_frame, weight=1)
        self.control_panel.pack_propagate(False)

        # --- Build and Place UI Elements ---
        self._create_scrollable_controls()
        self.canvas = tk.Canvas(self.image_frame, background='black', highlightthickness=0); self.canvas.pack(fill=tk.BOTH, expand=True)
        self.status_var = tk.StringVar(value="Welcome! Drop asset files or use 'Add...' to begin."); ttk.Label(root, textvariable=self.status_var, relief=tk.SUNKEN).pack(side=tk.BOTTOM, fill=tk.X)
        self._setup_event_bindings()

    # --- 2.2. UI CREATION METHODS ---
    def setup_styles(self):
        style = ttk.Style()
        style.configure("Accent.TButton", font=('Arial', 12, 'bold'), foreground='green')
        style.configure("Add.TButton", font=('Arial', 10, 'bold'), foreground='blue')
        style.configure("Custom.Treeview", rowheight=60)

    def _create_scrollable_controls(self):
        container_canvas = tk.Canvas(self.control_panel); scrollbar = ttk.Scrollbar(self.control_panel, orient="vertical", command=container_canvas.yview)
        self.scrollable_frame = ttk.Frame(container_canvas)
        self.scrollable_frame.bind("<Configure>", lambda e: container_canvas.configure(scrollregion=container_canvas.bbox("all")))
        container_canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw"); container_canvas.configure(yscrollcommand=scrollbar.set)
        self._bind_mouse_wheel_recursive(container_canvas); container_canvas.pack(side="left", fill=tk.BOTH, expand=True); scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self._populate_controls(self.scrollable_frame)

    def _populate_controls(self, parent_frame):
        bg_frame = ttk.LabelFrame(parent_frame, text="1. Background", padding=10); bg_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Button(bg_frame, text="Load Background", command=self.load_background).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0,2))
        ttk.Button(bg_frame, text="New Canvas...", command=self.create_new_canvas).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(2,0))
        assets_frame = ttk.LabelFrame(parent_frame, text="2. Asset Layers & Settings", padding=10); assets_frame.pack(fill=tk.X, padx=5, pady=5)
        for i in range(len(self.layers)): self._create_layer_ui(assets_frame, i)
        self._create_title_engine_ui(parent_frame); self._create_actions_ui(parent_frame)
        self._bind_mouse_wheel_recursive(self.scrollable_frame)

    def _create_layer_ui(self, parent, layer_index):
        layer_info = self.layers[layer_index]
        frame = ttk.LabelFrame(parent, text=layer_info["name"], padding=5); frame.pack(fill=tk.X, expand=True, pady=5, padx=3)
        list_frame = ttk.Frame(frame); list_frame.pack(fill=tk.X, expand=True)
        
        tree = ttk.Treeview(list_frame, columns=("name", "count"), height=4, style="Custom.Treeview")
        tree.heading("#0", text="Active"); tree.heading("name", text="Asset Name"); tree.heading("count", text="#")
        tree.column("#0", width=80, stretch=tk.NO, anchor='w')
        tree.column("name", width=150, stretch=tk.YES); tree.column("count", width=40, stretch=tk.NO, anchor='center')
        tree.pack(side=tk.LEFT, fill=tk.X, expand=True)
        layer_info["tree"] = tree
        
        btn_frame = ttk.Frame(list_frame); btn_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(5,0))
        ttk.Button(btn_frame, text="Add...", command=lambda i=layer_index: self.load_assets(i)).pack(fill=tk.X)
        ttk.Button(btn_frame, text="Clear", command=lambda i=layer_index: self.clear_layer(i)).pack(fill=tk.X)
        ttk.Button(btn_frame, text="All", command=lambda i=layer_index: self.select_all(i)).pack(fill=tk.X)
        ttk.Button(btn_frame, text="None", command=lambda i=layer_index: self.select_none(i)).pack(fill=tk.X)
        
        tree.bind('<Button-1>', self.on_tree_click); tree.bind('<Double-1>', self.on_tree_double_click)
        tree.drop_target_register(DND_FILES); tree.dnd_bind('<<Drop>>', lambda e, i=layer_index: self.handle_drop(e, i))
        
        settings_frame = ttk.Frame(frame); settings_frame.pack(fill=tk.X, expand=True, pady=(5,0))
        self._create_per_layer_settings_ui(settings_frame, layer_index)

    def _create_per_layer_settings_ui(self, parent, i):
        layer = self.layers[i]; placement_frame = ttk.Frame(parent); placement_frame.pack(fill=tk.X)
        ttk.Label(placement_frame, text="Placement:").pack(side=tk.LEFT, padx=(0,5))
        placement_options = ["Anywhere", "Center", "Top Half", "Bottom Half", "Left Half", "Right Half", "Top Left", "Top Center", "Top Right", "Middle Left", "Middle Right", "Bottom Left", "Bottom Center", "Bottom Right"]
        ttk.OptionMenu(placement_frame, layer["placement_var"], placement_options[0], *placement_options).pack(fill=tk.X, expand=True)
        f_scale = ttk.Frame(parent); f_scale.pack(fill=tk.X, pady=(5,0)); ttk.Label(f_scale, text="Scale:").pack(side=tk.LEFT); self._create_slider_with_entry(f_scale, layer["scale_min_var"], 1, 300); self._create_slider_with_entry(f_scale, layer["scale_max_var"], 1, 300)
        f_rot = ttk.Frame(parent); f_rot.pack(fill=tk.X, pady=(5,0)); ttk.Label(f_rot, text="Rotation:").pack(side=tk.LEFT); self._create_slider_with_entry(f_rot, layer["rot_min_var"], -180, 180); self._create_slider_with_entry(f_rot, layer["rot_max_var"], -180, 180)

    def _create_slider_with_entry(self, parent, var, from_, to):
        f = ttk.Frame(parent); f.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        entry = ttk.Entry(f, textvariable=var, width=5); entry.pack(side=tk.RIGHT)
        slider = ttk.Scale(f, from_=from_, to=to, variable=var, orient=tk.HORIZONTAL); slider.pack(side=tk.RIGHT, fill=tk.X, expand=True)

    def _create_title_engine_ui(self, parent):
        title_frame = ttk.LabelFrame(parent, text="3. Title Engine", padding=10); title_frame.pack(fill=tk.X, padx=5, pady=5)
        self.title_text_var=tk.StringVar(value="My Scene"); self.title_font_var=tk.StringVar(value="Arial"); self.title_size_var=tk.IntVar(value=72)
        self.title_pos_var=tk.StringVar(value="Center"); self.title_color_var=tk.StringVar(value="#FFFFFF"); self.shadow_enabled_var=tk.BooleanVar(value=True); self.shadow_color_var=tk.StringVar(value="#000000")
        title_frame.columnconfigure(1, weight=1); ttk.Label(title_frame, text="Title Text:").grid(row=0, column=0, sticky="w"); ttk.Entry(title_frame, textvariable=self.title_text_var).grid(row=0, column=1, columnspan=2, sticky="ew")
        ttk.Label(title_frame, text="Font:").grid(row=1, column=0, sticky="w"); ttk.Combobox(title_frame, textvariable=self.title_font_var, values=self.system_fonts, state='readonly').grid(row=1, column=1, columnspan=2, sticky="ew")
        ttk.Label(title_frame, text="Size:").grid(row=2, column=0, sticky="w"); ttk.Spinbox(title_frame, from_=10, to=500, textvariable=self.title_size_var).grid(row=2, column=1, columnspan=2, sticky="ew")
        ttk.Label(title_frame, text="Position:").grid(row=3, column=0, sticky="w"); ttk.OptionMenu(title_frame, self.title_pos_var, "Center", "Center", "Top Center", "Bottom Center", "Top Left", "Bottom Right").grid(row=3, column=1, columnspan=2, sticky="ew")
        ttk.Label(title_frame, text="Color:").grid(row=4, column=0, sticky="w"); ttk.Button(title_frame, text="Choose...", command=lambda: self.choose_color(self.title_color_var)).grid(row=4, column=1, sticky="ew")
        ttk.Checkbutton(title_frame, text="Enable Shadow", variable=self.shadow_enabled_var).grid(row=5, column=0, sticky="w"); ttk.Button(title_frame, text="Shadow Color...", command=lambda: self.choose_color(self.shadow_color_var)).grid(row=5, column=1, sticky="ew")
        ttk.Button(title_frame, text="Add/Update Title", command=self.add_title).grid(row=6, column=0, columnspan=2, sticky="ew", pady=5)

    def _create_actions_ui(self, parent):
        action_frame = ttk.LabelFrame(parent, text="4. Actions", padding=10); action_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Button(action_frame, text="GENERATE NEW SCENE", command=self.generate_scene, style="Accent.TButton").pack(fill=tk.X, ipady=5, pady=2)
        ttk.Button(action_frame, text="ADD TO SCENE", command=lambda: self.generate_scene(add_only=True), style="Add.TButton").pack(fill=tk.X, pady=2)
        ttk.Button(action_frame, text="Save Final Image...", command=self.save_scene).pack(fill=tk.X, pady=2)

    def _setup_event_bindings(self):
        self.canvas.bind("<ButtonPress-1>", self.on_canvas_press); self.canvas.bind("<B1-Motion>", self.on_canvas_drag); self.canvas.bind("<ButtonRelease-1>", self.on_canvas_release)
        self.root.bind("<Delete>", self.delete_selected_asset); self.root.bind("<BackSpace>", self.delete_selected_asset)
        self.canvas.bind("<MouseWheel>", self.on_mouse_wheel); self.canvas.bind("<Button-4>", self.on_mouse_wheel); self.canvas.bind("<Button-5>", self.on_mouse_wheel)
        self.canvas.bind("<ButtonPress-2>", self.on_pan_start); self.canvas.bind("<B2-Motion>", self.on_pan_drag)
        self.canvas.bind("<Configure>", lambda e: self.display_image(self.current_scene_image))

    # --- 2.3. CORE LOGIC & EVENT HANDLERS ---
    
    def _calculate_asset_geometry(self, asset_obj):
        """CRITICAL FIX: This function calculates an asset's corner points for click detection."""
        w2, h2 = (self.asset_cache[asset_obj['path']].width * asset_obj['scale_x']) / 2, (self.asset_cache[asset_obj['path']].height * asset_obj['scale_y']) / 2
        cx, cy = asset_obj['x'], asset_obj['y']; points = [(-w2, -h2), (w2, -h2), (w2, h2), (-w2, h2)]
        angle_rad = math.radians(asset_obj['rotation']); cos_a, sin_a = math.cos(angle_rad), math.sin(angle_rad)
        rotated_points = [(x * cos_a - y * sin_a + cx, x * sin_a + y * cos_a + cy) for x, y in points]
        asset_obj['corner_points'] = rotated_points

    def redraw_canvas(self, with_title=True):
        if not self.background_image: return
        
        # *** CRITICAL FIX FOR SELECTION ***
        # Before drawing, we must calculate the geometry for ALL assets so they can be clicked.
        for asset in self.placed_assets:
            self._calculate_asset_geometry(asset)
            
        canvas_image = self.background_image.copy()
        for asset_obj in sorted(self.placed_assets, key=lambda k: k['layer_index']):
            self.draw_single_asset(canvas_image, asset_obj)
        if self.selected_asset_id:
            selected = self.get_asset_by_id(self.selected_asset_id)
            if selected: self.draw_selection_handles(canvas_image, selected)
        self.generated_scene_no_title = canvas_image
        final_image = self._render_title_on_image(canvas_image) if with_title else canvas_image
        self.display_image(final_image)
        
    def draw_single_asset(self, target_image, asset_obj):
        asset_img = self.asset_cache[asset_obj['path']]; w, h = asset_img.size
        new_size = (int(w * asset_obj['scale_x']), int(h * asset_obj['scale_y']))
        if new_size[0] < 1 or new_size[1] < 1: return
        transformed_img = asset_img.resize(new_size, Image.Resampling.LANCZOS).rotate(asset_obj['rotation'], expand=True, resample=Image.Resampling.BICUBIC)
        paste_x = int(asset_obj['x'] - transformed_img.width / 2); paste_y = int(asset_obj['y'] - transformed_img.height / 2)
        target_image.paste(transformed_img, (paste_x, paste_y), transformed_img)
        
    def draw_selection_handles(self, target_image, asset_obj):
        # This function now assumes corner_points have already been calculated.
        draw = ImageDraw.Draw(target_image)
        rotated_points = asset_obj['corner_points']
        cx, cy = asset_obj['x'], asset_obj['y']
        h2 = (self.asset_cache[asset_obj['path']].height * asset_obj['scale_y']) / 2
        
        draw.polygon(rotated_points, outline="cyan", width=2)
        midpoints = [((p1[0]+p2[0])/2, (p1[1]+p2[1])/2) for p1, p2 in zip(rotated_points, rotated_points[1:] + [rotated_points[0]])]
        handle_size = 6
        for x, y in rotated_points + midpoints: draw.rectangle((x-handle_size, y-handle_size, x+handle_size, y+handle_size), fill="cyan", outline="black")
        
        rot_handle_y_offset = -h2 - 25
        angle_rad = math.radians(asset_obj['rotation']); sin_a = math.sin(angle_rad); cos_a = math.cos(angle_rad)
        rh_x = rot_handle_y_offset * -sin_a + cx; rh_y = rot_handle_y_offset * cos_a + cy
        draw.line([(cx, cy), (rh_x, rh_y)], fill="cyan", width=2); draw.ellipse((rh_x-8, rh_y-8, rh_x+8, rh_y+8), fill="cyan", outline="black")
        asset_obj['rot_handle_pos'] = (rh_x, rh_y)
        
    def on_canvas_press(self, event):
        click_x, click_y = self._display_to_image_coords(event.x, event.y); mode = None; newly_selected_id = None
        selected = self.get_asset_by_id(self.selected_asset_id)
        if selected:
            if 'rot_handle_pos' in selected and math.hypot(selected['rot_handle_pos'][0] - click_x, selected['rot_handle_pos'][1] - click_y) < 20: mode = "rotate"
            if not mode and 'corner_points' in selected:
                handles = ["tl", "tr", "br", "bl", "t", "r", "b", "l"]; midpoints = [((p1[0]+p2[0])/2, (p1[1]+p2[1])/2) for p1, p2 in zip(selected['corner_points'], selected['corner_points'][1:] + [selected['corner_points'][0]])]
                for i, (px, py) in enumerate(selected['corner_points'] + midpoints):
                    if math.hypot(px - click_x, py - click_y) < 15: mode = f"scale_{handles[i]}"; break
            if mode: newly_selected_id = selected['id']
        if not mode:
            for asset_obj in reversed(sorted(self.placed_assets, key=lambda k: k['layer_index'])):
                if self.is_point_in_asset(click_x, click_y, asset_obj): mode = "move"; newly_selected_id = asset_obj['id']; break
        self.selected_asset_id = newly_selected_id
        if newly_selected_id:
            item = self.get_asset_by_id(newly_selected_id)
            self._drag_data = {'item_id': newly_selected_id, 'mode': mode, 'x': click_x, 'y': click_y, 'start_rot': item['rotation'], 'start_angle': math.atan2(click_y - item['y'], click_x - item['x'])}
        else: self._drag_data = {}
        self.redraw_canvas()

    def on_canvas_drag(self, event):
        if not self._drag_data.get("item_id"): return
        item = self.get_asset_by_id(self._drag_data["item_id"]); new_x, new_y = self._display_to_image_coords(event.x, event.y)
        if not item: return
        mode = self._drag_data['mode']
        if mode == "move": item['x'] += new_x - self._drag_data['x']; item['y'] += new_y - self._drag_data['y']
        elif mode == "rotate": current_angle = math.atan2(new_y - item['y'], new_x - item['x']); item['rotation'] = self._drag_data['start_rot'] + math.degrees(current_angle - self._drag_data['start_angle'])
        elif "scale_" in mode: self.scale_asset(item, mode.split('_')[1], new_x, new_y)
        self._drag_data['x'] = new_x; self._drag_data['y'] = new_y; self.redraw_canvas(with_title=False)

    def on_canvas_release(self, event):
        if self._drag_data.get('item_id'): self.redraw_canvas()
        self._drag_data.clear()
        
    def scale_asset(self, item, handle, mx, my):
        cx, cy = item['x'], item['y']; angle_rad = -math.radians(item['rotation']); cos_a, sin_a = math.cos(angle_rad), math.sin(angle_rad)
        local_mx = (mx - cx) * cos_a - (my - cy) * sin_a; local_my = (mx - cx) * sin_a + (my - cy) * cos_a
        img_w, img_h = self.asset_cache[item['path']].size
        if 'l' in handle or 'r' in handle: item['scale_x'] = max(0.05, abs(local_mx * 2 / img_w))
        if 't' in handle or 'b' in handle: item['scale_y'] = max(0.05, abs(local_my * 2 / img_h))

    def generate_scene(self, add_only=False):
        if not self.background_image: messagebox.showerror("Error", "Load background first."); return
        if not add_only: self.placed_assets.clear(); self.selected_asset_id = None
        W, H = self.background_image.size
        for i, layer in enumerate(self.layers):
            for item_id in layer["tree"].get_children():
                if 'checked' in layer["tree"].item(item_id, 'tags'):
                    asset_path = layer["assets"].get(item_id)
                    if not asset_path or asset_path not in self.asset_cache: continue
                    count = int(layer["tree"].set(item_id, "count"))
                    for _ in range(count):
                        min_s, max_s = min(layer["scale_min_var"].get(), layer["scale_max_var"].get()), max(layer["scale_min_var"].get(), layer["scale_max_var"].get())
                        scale = random.uniform(min_s / 100.0, max_s / 100.0)
                        min_r, max_r = min(layer["rot_min_var"].get(), layer["rot_max_var"].get()), max(layer["rot_min_var"].get(), layer["rot_max_var"].get())
                        rotation = random.uniform(min_r, max_r); asset_img = self.asset_cache[asset_path]
                        w, h = int(asset_img.width * scale), int(asset_img.height * scale)
                        x_r, y_r = self.get_placement_zone(W, H, w, h, layer["placement_var"].get())
                        if x_r[1] < x_r[0] or y_r[1] < y_r[0]: continue
                        x, y = (random.randint(*x_r) + w//2, random.randint(*y_r) + h//2)
                        self.placed_assets.append({"id": str(uuid.uuid4()), "path": asset_path, "x": x, "y": y, "scale_x": scale, "scale_y": scale, "rotation": rotation, "layer_index": i})
        self.redraw_canvas(); self.status_var.set(f"Scene {'updated' if add_only else 'generated'}!")

    def save_scene(self):
        if not self.current_scene_image: messagebox.showerror("Error", "No scene to save."); return
        filepath = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG", "*.png"), ("JPEG", "*.jpg")])
        if not filepath: return
        self.selected_asset_id = None
        final_image_no_handles = self.background_image.copy()
        for asset in sorted(self.placed_assets, key=lambda k: k['layer_index']): self.draw_single_asset(final_image_no_handles, asset)
        final_image_with_title = self._render_title_on_image(final_image_no_handles)
        if filepath.lower().endswith(('.jpg', '.jpeg')): final_image_with_title = final_image_with_title.convert('RGB')
        final_image_with_title.save(filepath); self.status_var.set(f"Scene saved to {filepath}")
        self.redraw_canvas()
        
    def create_new_canvas(self):
        dialog = tk.Toplevel(self.root); dialog.title("New Canvas"); dialog.transient(self.root); dialog.grab_set()
        width_var = tk.IntVar(value=1920); height_var = tk.IntVar(value=1080); color_var = tk.StringVar(value="#4682B4")
        ttk.Label(dialog, text="Width:").grid(row=0, column=0, padx=5, pady=5, sticky='w'); ttk.Entry(dialog, textvariable=width_var).grid(row=0, column=1, padx=5, pady=5)
        ttk.Label(dialog, text="Height:").grid(row=1, column=0, padx=5, pady=5, sticky='w'); ttk.Entry(dialog, textvariable=height_var).grid(row=1, column=1, padx=5, pady=5)
        color_label = ttk.Label(dialog, text=" "*8, background=color_var.get(), relief=tk.SUNKEN)
        def pick_color():
            code = colorchooser.askcolor(title="Choose background", parent=dialog);
            if code and code[1]: color_var.set(code[1]); color_label.config(background=code[1])
        ttk.Label(dialog, text="Color:").grid(row=2, column=0, padx=5, pady=5, sticky='w'); color_label.grid(row=2, column=1, sticky='ew'); ttk.Button(dialog, text="Choose...", command=pick_color).grid(row=2, column=2, padx=5, pady=5)
        def on_create():
            W, H = width_var.get(), height_var.get()
            if W > 0 and H > 0:
                self.background_image = Image.new("RGBA", (W, H), color_var.get())
                self.placed_assets.clear(); self.selected_asset_id = None
                self._zoom_level = 1.0; self._view_x = 0; self._view_y = 0; self.redraw_canvas()
                self.status_var.set(f"Created new {W}x{H} canvas."); dialog.destroy()
        ttk.Button(dialog, text="Create", command=on_create).grid(row=3, column=0, columnspan=3, pady=10)

    # --- Full, Unabridged List of All Other Helper Methods ---
    def load_assets(self, layer_index, paths=None):
        if paths is None: paths = filedialog.askopenfilenames(title=f"Select assets for Layer {layer_index+1}", filetypes=[("PNG Images", "*.png")])
        if not paths: return
        layer = self.layers[layer_index]; count = 0
        for path in paths:
            if path.lower().endswith('.png') and path not in layer["assets"].values():
                try:
                    img = Image.open(path).convert("RGBA"); self.asset_cache[path] = img
                    thumb = img.copy(); thumb.thumbnail((50,50)); self.thumbnail_cache[path] = thumb
                    initial_image = self.get_composite_image(path, False)
                    item_id = layer["tree"].insert("", "end", image=initial_image, values=(os.path.basename(path), 1), tags=('unchecked',))
                    layer["assets"][item_id] = path; count += 1
                except Exception as e: print(f"Asset load error: {e}")
        if count > 0: self.status_var.set(f"Loaded {count} new assets.")
    def handle_drop(self, event, layer_index): self.load_assets(layer_index, paths=self.root.tk.splitlist(event.data))
    def on_tree_click(self, event):
        tree = event.widget; item_id = tree.identify_row(event.y)
        if not item_id: return
        # The click can be anywhere on the row to toggle
        layer_index = -1
        for i, layer in enumerate(self.layers):
            if layer["tree"] == tree: layer_index = i; break
        if layer_index == -1: return
        is_checked = 'checked' in tree.item(item_id, 'tags')
        new_tags = ('unchecked',) if is_checked else ('checked',)
        tree.item(item_id, tags=new_tags)
        path = self.layers[layer_index].assets[item_id]
        new_image = self.get_composite_image(path, not is_checked)
        tree.item(item_id, image=new_image)
    def on_tree_double_click(self, event):
        tree = event.widget; region = tree.identify_region(event.x, event.y); item_id = tree.identify_row(event.y)
        if region == 'cell' and item_id and tree.identify_column(event.x) == "#2":
            x, y, width, height = tree.bbox(item_id, "#2"); val = tree.set(item_id, "count")
            entry = ttk.Entry(tree, justify='center'); entry.place(x=x, y=y, width=width, height=height); entry.insert(0, val); entry.focus_force()
            def save_edit(e):
                new_val = entry.get();
                try: tree.set(item_id, "count", int(new_val) if int(new_val) > 0 else 1)
                except ValueError: pass
                entry.destroy()
            entry.bind('<Return>', save_edit); entry.bind('<FocusOut>', save_edit)
    def is_point_in_asset(self, px, py, asset_obj):
        if 'corner_points' not in asset_obj: return False
        points = asset_obj['corner_points']; n = len(points); inside = False; p1x, p1y = points[0]
        for i in range(n + 1):
            p2x, p2y = points[i % n]
            if py > min(p1y, p2y) and py <= max(p1y, p2y) and px <= max(p1x, p2x):
                if p1y != p2y: xinters = (py - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                if p1x == p2x or px <= xinters: inside = not inside
            p1x, p1y = p2x, p2y
        return inside
    def on_mouse_wheel(self, event):
        if not self.background_image: return
        zoom_factor = 1.2 if (event.num == 4 or event.delta > 0) else 1 / 1.2; pre_zoom_x, pre_zoom_y = self._display_to_image_coords(event.x, event.y)
        self._zoom_level *= zoom_factor; self._zoom_level = max(0.1, min(self._zoom_level, 20.0)); post_zoom_x, post_zoom_y = self._display_to_image_coords(event.x, event.y)
        self._view_x += pre_zoom_x - post_zoom_x; self._view_y += pre_zoom_y - post_zoom_y; self.display_image(self.current_scene_image)
    def on_pan_start(self, event): self._pan_start_x = event.x; self._pan_start_y = event.y
    def on_pan_drag(self, event):
        if not self.background_image: return
        dx, dy = event.x - self._pan_start_x, event.y - self._pan_start_y
        self._view_x -= dx * (self.current_scene_image.width / self.canvas.winfo_width()) / self._zoom_level; self._view_y -= dy * (self.current_scene_image.height / self.canvas.winfo_height()) / self._zoom_level
        self._pan_start_x, self._pan_start_y = event.x, event.y; self.display_image(self.current_scene_image)
    def display_image(self, pil_image):
        if not pil_image: self.canvas.delete("all"); return
        self.current_scene_image = pil_image; canvas_w, canvas_h = self.canvas.winfo_width(), self.canvas.winfo_height()
        if canvas_w <= 1 or canvas_h <= 1: return
        view_w = self.current_scene_image.width / self._zoom_level; view_h = self.current_scene_image.height / self._zoom_level
        self._view_x = max(0, min(self._view_x, self.current_scene_image.width - view_w)); self._view_y = max(0, min(self._view_y, self.current_scene_image.height - view_h))
        box = (self._view_x, self._view_y, self._view_x + view_w, self._view_y + view_h)
        visible_region = self.current_scene_image.crop(box); display_img = visible_region.resize((canvas_w, canvas_h), Image.Resampling.LANCZOS)
        self.tk_image = ImageTk.PhotoImage(display_img); self.canvas.delete("all"); self.canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_image)
    def _display_to_image_coords(self, event_x, event_y):
        if not self.current_scene_image: return 0, 0
        canvas_w, canvas_h = self.canvas.winfo_width(), self.canvas.winfo_height()
        if canvas_w <= 1 or canvas_h <=1: return 0,0
        img_x = self._view_x + (event_x / canvas_w) * (self.current_scene_image.width / self._zoom_level); img_y = self._view_y + (event_y / canvas_h) * (self.current_scene_image.height / self._zoom_level)
        return int(img_x), int(img_y)
    def get_placement_zone(self, W, H, w, h, zone):
        zones = {"Top Left": ((0, W//3 - w), (0, H//3 - h)), "Top Center": ((W//3, 2*W//3 - w), (0, H//3 - h)),"Top Right": ((2*W//3, W - w), (0, H//3 - h)),"Middle Left": ((0, W//3 - w), (H//3, 2*H//3 - h)),"Center": ((W//3, 2*W//3 - w), (H//3, 2*H//3 - h)),"Middle Right": ((2*W//3, W - w), (H//3, 2*H//3 - h)),"Bottom Left": ((0, W//3 - w), (2*H//3, H - h)),"Bottom Center": ((W//3, 2*W//3 - w), (2*H//3, H - h)),"Bottom Right": ((2*W//3, W - w), (2*H//3, H - h)),"Top Half": ((0, W - w), (0, H//2 - h)),"Bottom Half": ((0, W - w), (H//2, H - h)),"Left Half": ((0, W//2 - w), (0, H - h)),"Right Half": ((W//2, W - w), (0, H - h)),}
        x_r, y_r = zones.get(zone, ((0, W - w), (0, H - h))); return (max(0, x_r[0]), max(0, x_r[1])), (max(0, y_r[0]), max(0, y_r[1]))
    def load_background(self):
        path = filedialog.askopenfilename(filetypes=[("Images", "*.png *.jpg *.jpeg")]);
        if not path: return
        self.background_image = Image.open(path).convert("RGBA"); self.placed_assets.clear(); self.selected_asset_id = None
        self._zoom_level = 1.0; self._view_x = 0; self._view_y = 0; self.redraw_canvas(); self.status_var.set(f"Loaded background: {os.path.basename(path)}")
    def get_asset_by_id(self, asset_id): return next((asset for asset in self.placed_assets if asset['id'] == asset_id), None) if asset_id else None
    def delete_selected_asset(self, e=None):
        if self.selected_asset_id: self.placed_assets.remove(self.get_asset_by_id(self.selected_asset_id)); self.selected_asset_id=None; self.redraw_canvas(); self.status_var.set("Asset deleted.")
    def add_title(self): self.redraw_canvas()
    def _bind_mouse_wheel_recursive(self, widget):
        widget.bind("<MouseWheel>", self._on_mouse_wheel_controls); widget.bind("<Button-4>", self._on_mouse_wheel_controls); widget.bind("<Button-5>", self._on_mouse_wheel_controls)
        for child in widget.winfo_children(): self._bind_mouse_wheel_recursive(child)
    def _on_mouse_wheel_controls(self, event):
        canvas = self.control_panel.winfo_children()[0]
        if event.num == 5 or event.delta < 0: canvas.yview_scroll(1, "units")
        elif event.num == 4 or event.delta > 0: canvas.yview_scroll(-1, "units")
    def _render_title_on_image(self, base_image):
        if not self.title_text_var.get().strip(): return base_image
        image_with_title = base_image.copy(); draw = ImageDraw.Draw(image_with_title); text = self.title_text_var.get()
        font_name = self.title_font_var.get(); font_size = self.title_size_var.get()
        try: font = ImageFont.truetype(fm.findfont(fm.FontProperties(family=font_name)), font_size)
        except Exception: font = ImageFont.load_default()
        W, H = image_with_title.size; bbox = draw.textbbox((0,0), text, font=font); text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        pos_map = {"Center": ((W-text_w)//2, (H-text_h)//2), "Top Center": ((W-text_w)//2, 20),"Bottom Center": ((W-text_w)//2, H-text_h-20), "Top Left": (20, 20),"Bottom Right": (W-text_w-20, H-text_h-20)}
        x, y = pos_map.get(self.title_pos_var.get(), (20,20))
        if self.shadow_enabled_var.get():
            shadow_offset = int(font_size * 0.05) + 2
            draw.text((x + shadow_offset, y + shadow_offset), text, font=font, fill=self.shadow_color_var.get())
        draw.text((x,y), text, font=font, fill=self.title_color_var.get()); return image_with_title
    def choose_color(self, var_to_update):
        color_code = colorchooser.askcolor(title="Choose color");
        if color_code and color_code[1]: var_to_update.set(color_code[1])
    def clear_layer(self, layer_index): self.layers[layer_index]["tree"].delete(*self.layers[layer_index]["tree"].get_children()); self.layers[layer_index]["assets"].clear()
    def select_all(self, i): 
        tree = self.layers[i]["tree"]
        for item_id in tree.get_children(): 
            if 'checked' not in tree.item(item_id, 'tags'):
                tree.item(item_id, tags=('checked',))
                path = self.layers[i]["assets"][item_id]
                tree.item(item_id, image=self.get_composite_image(path, True))
    def select_none(self, i): 
        tree = self.layers[i]["tree"]
        for item_id in tree.get_children():
            if 'checked' in tree.item(item_id, 'tags'):
                tree.item(item_id, tags=('unchecked',))
                path = self.layers[i]["assets"][item_id]
                tree.item(item_id, image=self.get_composite_image(path, False))
    def get_composite_image(self, path, checked):
        cache_key = (path, checked)
        if cache_key in self.composite_image_cache: return self.composite_image_cache[cache_key]
        base_thumb = self.thumbnail_cache[path].copy().convert("RGBA")
        composite = Image.new("RGBA", (base_thumb.width + 24, base_thumb.height), (0,0,0,0))
        draw = ImageDraw.Draw(composite); box_size = 16
        y_offset = (composite.height - box_size) // 2
        if checked:
            draw.rectangle((2,y_offset,box_size,y_offset+box_size), outline="black", fill="dodgerblue")
            draw.line([(4,y_offset+6), (8,y_offset+10), (14,y_offset+2)], fill="white", width=2)
        else:
            draw.rectangle((2,y_offset,box_size,y_offset+box_size), outline="black", fill="white")
        composite.paste(base_thumb, (22, 0), base_thumb)
        photo = ImageTk.PhotoImage(composite)
        self.composite_image_cache[cache_key] = photo
        return photo

# === 3. APPLICATION LAUNCHER ===
if __name__ == "__main__":
    root = TkinterDnD.Tk()
    app = SceneEditorApp(root)
    root.mainloop()