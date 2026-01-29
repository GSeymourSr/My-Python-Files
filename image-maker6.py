# === 1. IMPORTS ===
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
        self.root.title("Advanced Scene Editor v3 (Per-Layer Controls)")
        self.root.state('zoomed')

        # --- Core Data Structures ---
        self.background_image = None
        self.generated_scene_no_title = None
        self.current_scene_image = None
        self.tk_image = None
        
        self.asset_cache = {}
        self.placed_assets = []
        self.selected_asset_id = None
        self._drag_data = {"x": 0, "y": 0, "item_id": None, "mode": None}

        # --- Pan & Zoom State ---
        self._zoom_level = 1.0
        self._view_x = 0; self._view_y = 0
        self._pan_start_x = 0; self._pan_start_y = 0
        
        try:
            font_paths = fm.findSystemFonts(fontpaths=None, fontext='ttf')
            unique_font_names = {fm.FontProperties(fname=font_path).get_name() for font_path in font_paths}
            self.system_fonts = sorted(list(unique_font_names))
        except Exception as e:
            print(f"Font loading failed: {e}")
            self.system_fonts = ["Arial", "Courier New", "Times New Roman"]

        # --- NEW: Layer Data with Per-Layer Settings ---
        self.layers = []
        for i in range(3):
            self.layers.append({
                "name": f"Layer {i+1}",
                "assets": {}, "tree": None,
                "placement_var": tk.StringVar(value="Anywhere"),
                "scale_min_var": tk.DoubleVar(value=50),
                "scale_max_var": tk.DoubleVar(value=100),
                "rot_min_var": tk.DoubleVar(value=0),
                "rot_max_var": tk.DoubleVar(value=0)
            })

        # --- Main Layout ---
        self.control_panel = ttk.Frame(root, width=450)
        self.control_panel.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
        self.control_panel.pack_propagate(False)

        self.image_frame = ttk.Frame(root)
        self.image_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        # --- UI Elements ---
        self._create_scrollable_controls()
        self.canvas = tk.Canvas(self.image_frame, background='black', highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.status_var = tk.StringVar(value="Welcome! Use mouse wheel to scroll controls or zoom preview.")
        ttk.Label(root, textvariable=self.status_var, relief=tk.SUNKEN).pack(side=tk.BOTTOM, fill=tk.X)

        # --- Event Bindings ---
        self.canvas.bind("<ButtonPress-1>", self.on_canvas_press)
        self.canvas.bind("<B1-Motion>", self.on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_canvas_release)
        self.root.bind("<Delete>", self.delete_selected_asset)
        self.root.bind("<BackSpace>", self.delete_selected_asset)
        self.canvas.bind("<MouseWheel>", self.on_mouse_wheel); self.canvas.bind("<Button-4>", self.on_mouse_wheel); self.canvas.bind("<Button-5>", self.on_mouse_wheel)
        self.canvas.bind("<ButtonPress-2>", self.on_pan_start); self.canvas.bind("<B2-Motion>", self.on_pan_drag)
        self.canvas.bind("<Configure>", lambda e: self.display_image(self.current_scene_image))

    # --- 2.2. UI CREATION METHODS ---
    def _create_scrollable_controls(self):
        container_canvas = tk.Canvas(self.control_panel)
        scrollbar = ttk.Scrollbar(self.control_panel, orient="vertical", command=container_canvas.yview)
        self.scrollable_frame = ttk.Frame(container_canvas)
        self.scrollable_frame.bind("<Configure>", lambda e: container_canvas.configure(scrollregion=container_canvas.bbox("all")))
        container_canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        container_canvas.configure(yscrollcommand=scrollbar.set)
        self._bind_mouse_wheel_recursive(container_canvas)
        container_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self._populate_controls(self.scrollable_frame)

    def _bind_mouse_wheel_recursive(self, widget):
        widget.bind("<MouseWheel>", self._on_mouse_wheel_controls)
        widget.bind("<Button-4>", self._on_mouse_wheel_controls)
        widget.bind("<Button-5>", self._on_mouse_wheel_controls)
        for child in widget.winfo_children():
            self._bind_mouse_wheel_recursive(child)
            
    def _on_mouse_wheel_controls(self, event):
        canvas = self.control_panel.winfo_children()[0]
        if event.num == 5 or event.delta < 0: canvas.yview_scroll(1, "units")
        elif event.num == 4 or event.delta > 0: canvas.yview_scroll(-1, "units")

    def _populate_controls(self, parent_frame):
        bg_frame = ttk.LabelFrame(parent_frame, text="1. Background", padding=10)
        bg_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Button(bg_frame, text="Load Background Image", command=self.load_background).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0,2))
        ttk.Button(bg_frame, text="New Blank Canvas...", command=self.create_new_canvas).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(2,0))
        
        assets_frame = ttk.LabelFrame(parent_frame, text="2. Asset Layers & Settings", padding=10)
        assets_frame.pack(fill=tk.X, padx=5, pady=5)
        for i, layer_info in enumerate(self.layers):
            self._create_layer_ui(assets_frame, i)
        
        self._create_title_engine_ui(parent_frame)
        
        action_frame = ttk.LabelFrame(parent_frame, text="4. Actions", padding=10)
        action_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Style().configure("Accent.TButton", font=('Arial', 12, 'bold'), foreground='green')
        ttk.Button(action_frame, text="GENERATE NEW SCENE", command=self.generate_scene, style="Accent.TButton").pack(fill=tk.X, ipady=5, pady=2)
        ttk.Button(action_frame, text="Save Final Image...", command=self.save_scene).pack(fill=tk.X, pady=2)
        
        # After all widgets are created, bind mouse wheel to all of them
        self._bind_mouse_wheel_recursive(self.scrollable_frame)

    def _create_layer_ui(self, parent, layer_index):
        layer_info = self.layers[layer_index]
        frame = ttk.LabelFrame(parent, text=layer_info["name"], padding=5)
        frame.pack(fill=tk.X, expand=True, pady=5, padx=3)

        # --- Asset List ---
        list_frame = ttk.Frame(frame)
        list_frame.pack(fill=tk.X, expand=True)
        tree = ttk.Treeview(list_frame, columns=("asset", "count"), show="headings", height=4)
        tree.heading("asset", text="Asset Name"); tree.heading("count", text="#")
        tree.column("asset", width=150, stretch=tk.YES); tree.column("count", width=50, stretch=tk.NO)
        tree.pack(side=tk.LEFT, fill=tk.X, expand=True)
        layer_info["tree"] = tree
        tree.drop_target_register(DND_FILES); tree.dnd_bind('<<Drop>>', lambda e, i=layer_index: self.handle_drop(e, i))
        tree.tag_configure('checked', image=self.get_check_image(True)); tree.tag_configure('unchecked', image=self.get_check_image(False))
        tree.bind('<Button-1>', lambda event, t=tree: self.toggle_check(event, t))
        tree.bind('<Double-1>', lambda event, t=tree: self.edit_tree_cell(event, t))

        # --- Buttons next to list ---
        btn_frame = ttk.Frame(list_frame)
        btn_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(5,0))
        ttk.Button(btn_frame, text="Add...", command=lambda i=layer_index: self.load_assets(i)).pack(fill=tk.X)
        ttk.Button(btn_frame, text="Clear", command=lambda i=layer_index: self.clear_layer(i)).pack(fill=tk.X)
        ttk.Button(btn_frame, text="All", command=lambda i=layer_index: self.select_all(i)).pack(fill=tk.X)
        ttk.Button(btn_frame, text="None", command=lambda i=layer_index: self.select_none(i)).pack(fill=tk.X)

        # --- Settings below the list ---
        settings_frame = ttk.Frame(frame)
        settings_frame.pack(fill=tk.X, expand=True, pady=(5,0))
        placement_options = ["Anywhere", "Center", "Top Half", "Bottom Half", "Left Half", "Right Half", "Top Left", "Top Center", "Top Right", "Middle Left", "Middle Right", "Bottom Left", "Bottom Center", "Bottom Right"]
        ttk.OptionMenu(settings_frame, layer_info["placement_var"], placement_options[0], *placement_options).pack(fill=tk.X, pady=(0,2))
        
        ttk.Label(settings_frame, text=f"Scale (%):").pack(anchor='w')
        ttk.Scale(settings_frame, from_=1, to=200, variable=layer_info["scale_min_var"]).pack(fill='x')
        ttk.Scale(settings_frame, from_=1, to=200, variable=layer_info["scale_max_var"]).pack(fill='x')
        
        ttk.Label(settings_frame, text=f"Rotation (°):").pack(anchor='w', pady=(5,0))
        ttk.Scale(settings_frame, from_=-180, to=180, variable=layer_info["rot_min_var"]).pack(fill='x')
        ttk.Scale(settings_frame, from_=-180, to=180, variable=layer_info["rot_max_var"]).pack(fill='x')

    def _create_title_engine_ui(self, parent):
        title_frame = ttk.LabelFrame(parent, text="3. Title Engine", padding=10)
        title_frame.pack(fill=tk.X, padx=5, pady=5)
        self.title_text_var = tk.StringVar(value="My Awesome Scene")
        self.title_font_var = tk.StringVar(value="Arial"); self.title_size_var = tk.IntVar(value=72)
        self.title_pos_var = tk.StringVar(value="Center"); self.title_color_var = tk.StringVar(value="#FFFFFF")
        self.shadow_enabled_var = tk.BooleanVar(value=True); self.shadow_color_var = tk.StringVar(value="#000000")
        title_frame.columnconfigure(1, weight=1)
        ttk.Label(title_frame, text="Title Text:").grid(row=0, column=0, sticky="w"); ttk.Entry(title_frame, textvariable=self.title_text_var).grid(row=0, column=1, columnspan=2, sticky="ew")
        ttk.Label(title_frame, text="Font:").grid(row=1, column=0, sticky="w"); ttk.Combobox(title_frame, textvariable=self.title_font_var, values=self.system_fonts, state='readonly').grid(row=1, column=1, columnspan=2, sticky="ew")
        ttk.Label(title_frame, text="Size:").grid(row=2, column=0, sticky="w"); ttk.Spinbox(title_frame, from_=10, to=500, textvariable=self.title_size_var).grid(row=2, column=1, columnspan=2, sticky="ew")
        ttk.Label(title_frame, text="Position:").grid(row=3, column=0, sticky="w"); ttk.OptionMenu(title_frame, self.title_pos_var, "Center", "Center", "Top Center", "Bottom Center", "Top Left", "Bottom Right").grid(row=3, column=1, columnspan=2, sticky="ew")
        ttk.Label(title_frame, text="Color:").grid(row=4, column=0, sticky="w"); ttk.Button(title_frame, text="Choose...", command=lambda: self.choose_color(self.title_color_var)).grid(row=4, column=1, sticky="ew")
        ttk.Checkbutton(title_frame, text="Enable Shadow", variable=self.shadow_enabled_var).grid(row=5, column=0, sticky="w")
        ttk.Button(title_frame, text="Shadow Color...", command=lambda: self.choose_color(self.shadow_color_var)).grid(row=5, column=1, sticky="ew")
        ttk.Button(title_frame, text="Add/Update Title", command=self.add_title).grid(row=6, column=0, columnspan=2, sticky="ew", pady=5)

    # --- 2.3. ALL OTHER METHODS (RESTORED AND FUNCTIONAL) ---
    
    # ... (All methods from previous versions are now here, no omissions) ...
    # This includes redraw_canvas, on_canvas_press, generate_scene, etc.
    # plus all the restored helper methods.

    # --- RESTORED HELPER METHODS ---
    def choose_color(self, var_to_update):
        color_code = colorchooser.askcolor(title="Choose color")
        if color_code and color_code[1]: var_to_update.set(color_code[1])
        
    def get_check_image(self, checked):
        if not hasattr(self, '_check_images'): self._check_images = {}
        if checked in self._check_images: return self._check_images[checked]
        im = Image.new("RGBA", (16, 16), (0,0,0,0)); draw = ImageDraw.Draw(im)
        if checked:
            draw.rectangle((2,2,12,12), outline="black", fill="dodgerblue"); draw.line([(4,8), (7,11), (12,4)], fill="white", width=2)
        else:
            draw.rectangle((2,2,12,12), outline="black")
        photo = ImageTk.PhotoImage(im); self._check_images[checked] = photo
        return photo
        
    def edit_tree_cell(self, event, tree):
        item_id = tree.identify_row(event.y); column_id = tree.identify_column(event.x)
        if not item_id or column_id != "#2": return
        x, y, width, height = tree.bbox(item_id, column_id)
        val = tree.set(item_id, column_id); entry = ttk.Entry(tree, justify='center')
        entry.place(x=x, y=y, width=width, height=height); entry.insert(0, val); entry.focus_force()
        entry.bind('<Return>', lambda e: self.save_cell_edit(entry, tree, item_id, column_id))
        entry.bind('<FocusOut>', lambda e: self.save_cell_edit(entry, tree, item_id, column_id))
        
    def save_cell_edit(self, entry, tree, item_id, column_id):
        new_val = entry.get()
        try:
            if int(new_val) > 0: tree.set(item_id, column_id, int(new_val))
            else: tree.set(item_id, column_id, 1)
        except ValueError: pass
        entry.destroy()
        
    def _render_title_on_image(self, base_image):
        if not self.title_text_var.get().strip(): return base_image
        image_with_title = base_image.copy(); draw = ImageDraw.Draw(image_with_title)
        text = self.title_text_var.get(); font_name = self.title_font_var.get(); font_size = self.title_size_var.get()
        try:
            font_path = fm.findfont(fm.FontProperties(family=font_name)); font = ImageFont.truetype(font_path, font_size)
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
    
    # --- ALL OTHER METHODS IN FULL ---
    def on_mouse_wheel(self, event):
        if not self.background_image: return
        zoom_factor = 1.2 if (event.num == 4 or event.delta > 0) else 1 / 1.2
        pre_zoom_x, pre_zoom_y = self._display_to_image_coords(event.x, event.y)
        self._zoom_level *= zoom_factor
        self._zoom_level = max(0.1, min(self._zoom_level, 20.0))
        post_zoom_x, post_zoom_y = self._display_to_image_coords(event.x, event.y)
        self._view_x += pre_zoom_x - post_zoom_x
        self._view_y += pre_zoom_y - post_zoom_y
        self.display_image(self.current_scene_image)
    def on_pan_start(self, event): self._pan_start_x = event.x; self._pan_start_y = event.y
    def on_pan_drag(self, event):
        if not self.background_image: return
        dx = event.x - self._pan_start_x; dy = event.y - self._pan_start_y
        self._view_x -= dx * (self.current_scene_image.width / self.canvas.winfo_width()) / self._zoom_level
        self._view_y -= dy * (self.current_scene_image.height / self.canvas.winfo_height()) / self._zoom_level
        self._pan_start_x = event.x; self._pan_start_y = event.y
        self.display_image(self.current_scene_image)
    def display_image(self, pil_image):
        if not pil_image: self.canvas.delete("all"); return
        self.current_scene_image = pil_image
        canvas_w, canvas_h = self.canvas.winfo_width(), self.canvas.winfo_height()
        if canvas_w <= 1 or canvas_h <= 1: return
        view_w = self.current_scene_image.width / self._zoom_level
        view_h = self.current_scene_image.height / self._zoom_level
        self._view_x = max(0, min(self._view_x, self.current_scene_image.width - view_w))
        self._view_y = max(0, min(self._view_y, self.current_scene_image.height - view_h))
        box = (self._view_x, self._view_y, self._view_x + view_w, self._view_y + view_h)
        visible_region = self.current_scene_image.crop(box)
        display_img = visible_region.resize((canvas_w, canvas_h), Image.Resampling.LANCZOS)
        self.tk_image = ImageTk.PhotoImage(display_img)
        self.canvas.delete("all"); self.canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_image)
    def _display_to_image_coords(self, event_x, event_y):
        if not self.current_scene_image: return 0, 0
        canvas_w = self.canvas.winfo_width(); canvas_h = self.canvas.winfo_height()
        if canvas_w <= 1 or canvas_h <=1: return 0,0
        img_x = self._view_x + (event_x / canvas_w) * (self.current_scene_image.width / self._zoom_level)
        img_y = self._view_y + (event_y / canvas_h) * (self.current_scene_image.height / self._zoom_level)
        return int(img_x), int(img_y)
    def redraw_canvas(self, with_title=True):
        if not self.background_image: return
        canvas_image = self.background_image.copy()
        sorted_assets = sorted(self.placed_assets, key=lambda k: k['layer_index'])
        for asset_obj in sorted_assets:
            asset_img = self.asset_cache[asset_obj['path']]
            new_size = (int(asset_img.width * asset_obj['scale']), int(asset_img.height * asset_obj['scale']))
            if new_size[0] < 1 or new_size[1] < 1: continue
            transformed_img = asset_img.resize(new_size, Image.Resampling.LANCZOS).rotate(asset_obj['rotation'], expand=True, resample=Image.Resampling.BICUBIC)
            pos = (int(asset_obj['x']), int(asset_obj['y']))
            canvas_image.paste(transformed_img, pos, transformed_img)
            w, h = transformed_img.size
            asset_obj['bbox'] = (pos[0], pos[1], pos[0] + w, pos[1] + h)
        if self.selected_asset_id:
            selected = self.get_asset_by_id(self.selected_asset_id)
            if selected:
                draw = ImageDraw.Draw(canvas_image)
                x1, y1, x2, y2 = selected['bbox']; draw.rectangle((x1, y1, x2, y2), outline="cyan", width=2)
                handle_size = 10; draw.rectangle((x2 - handle_size, y2 - handle_size, x2 + handle_size, y2 + handle_size), fill="cyan", outline="black")
                center_x, center_y = x1 + (x2 - x1) / 2, y1 + (y2 - y1) / 2
                handle_dist = 25; angle_rad = math.radians(-selected['rotation'])
                rot_handle_x = center_x + (handle_dist + (y1 - center_y)) * math.sin(angle_rad)
                rot_handle_y = center_y + (handle_dist + (y1 - center_y)) * -math.cos(angle_rad)
                draw.line([(center_x, center_y), (rot_handle_x, rot_handle_y)], fill="cyan", width=2)
                draw.ellipse([(rot_handle_x-6, rot_handle_y-6), (rot_handle_x+6, rot_handle_y+6)], fill="cyan", outline="black")
                selected['rot_handle_pos'] = (rot_handle_x, rot_handle_y)
        self.generated_scene_no_title = canvas_image
        final_image = self._render_title_on_image(canvas_image) if with_title else canvas_image
        self.display_image(final_image)
    def on_canvas_press(self, event):
        click_x, click_y = self._display_to_image_coords(event.x, event.y)
        newly_selected_id = None; mode = None
        selected = self.get_asset_by_id(self.selected_asset_id)
        if selected:
            if 'rot_handle_pos' in selected and math.hypot(selected['rot_handle_pos'][0] - click_x, selected['rot_handle_pos'][1] - click_y) < 15:
                newly_selected_id, mode = selected['id'], "rotate"
            else:
                x1, y1, x2, y2 = selected['bbox']
                if x2 - 15 < click_x < x2 + 15 and y2 - 15 < click_y < y2 + 15:
                    newly_selected_id, mode = selected['id'], "resize"
        if not newly_selected_id:
            for asset_obj in reversed(sorted(self.placed_assets, key=lambda k: k['layer_index'])):
                x1, y1, x2, y2 = asset_obj['bbox']
                if x1 <= click_x <= x2 and y1 <= click_y <= y2:
                    newly_selected_id, mode = asset_obj['id'], "move"
                    break
        self.selected_asset_id = newly_selected_id
        if self.selected_asset_id:
            self._drag_data = {'item_id': self.selected_asset_id, 'mode': mode, 'x': click_x, 'y': click_y}
        self.redraw_canvas()
    def on_canvas_drag(self, event):
        if not self._drag_data.get("item_id"): return
        item = self.get_asset_by_id(self._drag_data["item_id"])
        if not item: return
        new_x, new_y = self._display_to_image_coords(event.x, event.y)
        if self._drag_data["mode"] == "rotate":
            center_x, center_y = item['bbox'][0] + (item['bbox'][2] - item['bbox'][0])/2, item['bbox'][1] + (item['bbox'][3] - item['bbox'][1])/2
            item['rotation'] = math.degrees(math.atan2(new_y - center_y, new_x - center_x)) + 90
        elif self._drag_data["mode"] == "move":
            item['x'] += new_x - self._drag_data['x']; item['y'] += new_y - self._drag_data['y']
        elif self._drag_data["mode"] == "resize":
            img = self.asset_cache[item['path']]; old_w = img.width * item['scale']
            new_w = old_w + (new_x - self._drag_data['x'])
            if new_w > 10: item['scale'] = new_w / img.width
        self._drag_data['x'] = new_x; self._drag_data['y'] = new_y
        self.redraw_canvas(with_title=False)
    def on_canvas_release(self, event):
        if self._drag_data.get('item_id'): self.redraw_canvas()
        self._drag_data.clear()
    def get_placement_zone(self, W, H, w, h, zone):
        zones = {"Top Left": ((0, W//3 - w), (0, H//3 - h)), "Top Center": ((W//3, 2*W//3 - w), (0, H//3 - h)),"Top Right": ((2*W//3, W - w), (0, H//3 - h)),"MiddleLeft": ((0, W//3 - w), (H//3, 2*H//3 - h)),"Center": ((W//3, 2*W//3 - w), (H//3, 2*H//3 - h)),"Middle Right": ((2*W//3, W - w), (H//3, 2*H//3 - h)),"Bottom Left": ((0, W//3 - w), (2*H//3, H - h)),"Bottom Center": ((W//3, 2*W//3 - w), (2*H//3, H - h)),"Bottom Right": ((2*W//3, W - w), (2*H//3, H - h)),"Top Half": ((0, W - w), (0, H//2 - h)),"Bottom Half": ((0, W - w), (H//2, H - h)),"Left Half": ((0, W//2 - w), (0, H - h)),"Right Half": ((W//2, W - w), (0, H - h)),}
        x_r, y_r = zones.get(zone, ((0, W - w), (0, H - h)))
        return (max(0, x_r[0]), max(0, x_r[1])), (max(0, y_r[0]), max(0, y_r[1]))
    def load_background(self):
        path = filedialog.askopenfilename(filetypes=[("Images", "*.png *.jpg *.jpeg")])
        if not path: return
        self.background_image = Image.open(path).convert("RGBA"); self.placed_assets.clear(); self.selected_asset_id = None
        self._zoom_level = 1.0; self._view_x = 0; self._view_y = 0; self.redraw_canvas()
        self.status_var.set(f"Loaded background: {os.path.basename(path)}")
    def generate_scene(self):
        if not self.background_image: messagebox.showerror("Error", "Load background first."); return
        self.status_var.set("Generating..."); self.root.update_idletasks()
        self.placed_assets.clear(); self.selected_asset_id = None; W, H = self.background_image.size
        for i, layer in enumerate(self.layers):
            for item_id in layer["tree"].tag_has('checked'):
                asset_path = layer["assets"][item_id]["path"]; count = int(layer["tree"].item(item_id, 'values')[1])
                for _ in range(count):
                    asset_img = self.asset_cache.get(asset_path);
                    if not asset_img: continue
                    min_s, max_s = min(layer["scale_min_var"].get(), layer["scale_max_var"].get()), max(layer["scale_min_var"].get(), layer["scale_max_var"].get())
                    scale = random.uniform(min_s / 100.0, max_s / 100.0)
                    min_r, max_r = min(layer["rot_min_var"].get(), layer["rot_max_var"].get()), max(layer["rot_min_var"].get(), layer["rot_max_var"].get())
                    rotation = random.uniform(min_r, max_r)
                    temp_img = asset_img.resize((int(asset_img.width*scale), int(asset_img.height*scale)), Image.Resampling.LANCZOS).rotate(rotation, expand=True)
                    w,h = temp_img.size; x_r, y_r = self.get_placement_zone(W, H, w, h, layer["placement_var"].get())
                    if x_r[1] < x_r[0] or y_r[1] < y_r[0]: continue
                    x, y = (random.randint(*x_r), random.randint(*y_r))
                    self.placed_assets.append({"id": str(uuid.uuid4()), "path": asset_path, "x": x, "y": y, "scale": scale, "rotation": rotation, "layer_index": i, "bbox": (x, y, x + w, y + h)})
        self.redraw_canvas()
    def create_new_canvas(self):
        self.background_image = Image.new("RGBA", (1920, 1080), "#4682B4")
        self.placed_assets.clear(); self.selected_asset_id = None
        self._zoom_level = 1.0; self._view_x = 0; self._view_y = 0; self.redraw_canvas()
    def save_scene(self):
        if not self.current_scene_image: return
        filepath = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG", "*.png"), ("JPEG", "*.jpg")])
        if not filepath: return
        self.selected_asset_id = None; self.redraw_canvas() # Deselect before saving
        img_to_save = self.generated_scene_no_title
        if filepath.lower().endswith(('.jpg', '.jpeg')): img_to_save = img_to_save.convert('RGB')
        img_to_save.save(filepath); self.status_var.set(f"Scene saved to {filepath}")
    def get_asset_by_id(self, asset_id):
        if not asset_id: return None
        return next((asset for asset in self.placed_assets if asset['id'] == asset_id), None)
    def handle_drop(self, event, layer_index): self.load_assets(layer_index, paths=self.root.tk.splitlist(event.data))
    def load_assets(self, layer_index, paths=None):
        if paths is None: paths = filedialog.askopenfilenames(title=f"Select assets", filetypes=[("PNG Images", "*.png")])
        if not paths: return
        layer = self.layers[layer_index]; count = 0
        for path in paths:
            if path.lower().endswith('.png') and path not in self.asset_cache:
                try:
                    self.asset_cache[path] = Image.open(path).convert("RGBA")
                    item_id = layer["tree"].insert("", "end", values=(os.path.basename(path), 1), tags=('unchecked',))
                    layer["assets"][item_id] = {"path": path}; count += 1
                except Exception as e: print(f"Asset load error: {e}")
        self.status_var.set(f"Loaded {count} new assets.")
    def clear_layer(self, layer_index): self.layers[layer_index]["tree"].delete(*self.layers[layer_index]["tree"].get_children()); self.layers[layer_index]["assets"].clear()
    def select_all(self, i): [self.layers[i]["tree"].item(item_id, tags=('checked',)) for item_id in self.layers[i]["tree"].get_children()]
    def select_none(self, i): [self.layers[i]["tree"].item(item_id, tags=('unchecked',)) for item_id in self.layers[i]["tree"].get_children()]
    def toggle_check(self, event, tree):
        item_id = tree.identify_row(event.y)
        if item_id:
            tags = list(tree.item(item_id, 'tags')); is_checked = 'checked' in tags
            tree.item(item_id, tags=('unchecked',) if is_checked else ('checked',))
    def add_title(self): self.redraw_canvas()
    def delete_selected_asset(self, event=None):
        if self.selected_asset_id:
            self.placed_assets = [p for p in self.placed_assets if p['id'] != self.selected_asset_id]
            self.selected_asset_id = None; self.redraw_canvas()
            self.status_var.set("Asset deleted.")

# === 3. APPLICATION LAUNCHER ===
if __name__ == "__main__":
    root = TkinterDnD.Tk()
    app = SceneEditorApp(root)
    root.mainloop()