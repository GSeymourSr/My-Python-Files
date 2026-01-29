# --- START OF FILE -MENU-MAKER-.py ---

# --- Greg Seymour AI Menu Maker Deluxe ---
# This script combines the best features of all previous versions to create a powerful,
# themeable, and highly customizable file launching menu creator.

import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, font
import os
import subprocess
import webbrowser
import random
import time
import sys
import threading
import ast  # For safely parsing saved menu scripts
import colorsys # For advanced color palette generation
import inspect # For grabbing class source code when saving
import math # Now imported at the top for CanvasButton

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

# --- Constants (Expanded for Theming and Style) ---
# --- Palettes ---
PALETTES = {
    "Ocean": ["#006994", "#0096C7", "#48B5E3", "#90E0EF", "#CAF0F8"],
    "Sunset": ["#F7B267", "#F79D65", "#F4845F", "#F27059", "#F25C54"],
    "Forest": ["#2D6A4F", "#40916C", "#52B788", "#74C69D", "#95D5B2"],
    "Synthwave": ["#F94144", "#F3722C", "#F8961E", "#F9C74F", "#90BE6D", "#43AA8B", "#577590"],
    "Pastel": ["#FFADAD", "#FFD6A5", "#FDFFB6", "#CAFFBF", "#9BF6FF", "#A0C4FF", "#BDB2FF"],
    "Neon Glow": ["#FF00FF", "#00FFFF", "#FFFF00", "#00FF00", "#FF5E00", "#7D00FF"],
    "Earthy Tones": ["#A47C6A", "#C2937E", "#E3B598", "#6D5F53", "#4A423A"],
    "Grayscale": ["#222222", "#444444", "#666666", "#888888", "#AAAAAA", "#CCCCCC"],
    "Cyberpunk": ["#00F6F6", "#FDFE00", "#FF00FF", "#000000", "#5B00B5", "#242424"],
    "Autumn": ["#BF5700", "#E69F00", "#D55E00", "#A44A3F", "#5F2C21", "#F3E4C6"],
    "Vintage": ["#EAE0D5", "#C6AC8F", "#8A7968", "#594F45", "#D8C3A5", "#8E8D8A"],
    "Royal": ["#411530", "#D1512D", "#F5C7A9", "#F5E8E4", "#7900FF", "#FAD02C"],
    "Hacker": ["#00FF41", "#000000", "#1a1a1a", "#333333", "#0d0d0d", "#24C24A"],
    "Coffee Shop": ["#6F4E37", "#A77B5A", "#E1C699", "#F3E5AB", "#3A2B1D", "#FFFFFF"],
    "8-Bit": ["#0000FF", "#FF0000", "#00FF00", "#FFFF00", "#FFFFFF", "#000000"],
    "Steampunk": ["#8B4513", "#CD7F32", "#C0C0C0", "#FFD700", "#4B382A", "#1A1A1A"],
    "Arctic": ["#F0F8FF", "#E0FFFF", "#B0E0E6", "#778899", "#4682B4", "#000080"],
    "Desert": ["#EDC9AF", "#C19A6B", "#F5DEB3", "#8B7D6B", "#D2B48C", "#A0522D"],
    "Gothic": ["#2C003E", "#510073", "#8A00C2", "#C500FF", "#FFFFFF", "#E5E5E5"],
    "Jungle": ["#006400", "#228B22", "#556B2F", "#8FBC8F", "#FFD700", "#D2691E"],
    "Tropical": ["#FF6347", "#FFD700", "#32CD32", "#00BFFF", "#FF69B4", "#ADFF2F"],
    "Sakura": ["#FFC0CB", "#FFB6C1", "#DB7093", "#FFE4E1", "#FFFFFF", "#F5F5F5"],
    "Industrial": ["#708090", "#778899", "#A9A9A9", "#C0C0C0", "#D3D3D3", "#000000"]
}
WHIMSICAL_COLORS = sum(PALETTES.values(), []) # All palette colors for whimsical mode
WHIMSICAL_FONTS = [
    "Comic Sans MS", "Papyrus", "Curlz MT", "Kristen ITC", "Jokerman", "Lucida Handwriting",
    "Brush Script MT", "Segoe Print", "Impact", "Georgia", "Courier New", "Garamond",
    "Arial", "Verdana", "Helvetica", "Times New Roman" # Fallbacks
]
BUTTON_SHAPES = ["pill", "oval", "rounded_rect"]
DEFAULT_NUM_COLUMNS = 3
# --- End Constants ---


# --- Custom Canvas Button Widget ---
class CanvasButton(tk.Canvas):
    """A custom, themeable button widget with shapes, gradients, and shadows."""
    def __init__(self, master, text="", command=None, **kwargs):
        self.command = command
        self.style = {
            'shape': kwargs.get('shape', 'rounded_rect'),
            'text': text,
            'font_family': kwargs.get('font_family', 'Arial'),
            'font_size': kwargs.get('font_size', 12),
            'fg': kwargs.get('fg', '#000000'),
            'bg_start': kwargs.get('bg_start', '#FFFFFF'),
            'bg_end': kwargs.get('bg_end', '#CCCCCC'),
            'hover_bg_start': kwargs.get('hover_bg_start', '#FFFFFF'),
            'hover_bg_end': kwargs.get('hover_bg_end', '#B0B0B0'),
            'shadow_color': kwargs.get('shadow_color', '#A0A0A0'),
            'shadow_offset': kwargs.get('shadow_offset', (2, 2)),
            'width': kwargs.get('width', 200),
            'height': kwargs.get('height', 50),
            'corner_radius': kwargs.get('corner_radius', 15)
        }

        super().__init__(master, width=self.style['width'], height=self.style['height'], bg=master.cget("bg"), highlightthickness=0)
        self.state = 'normal'
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_click)

        self.draw_button()

    def draw_button(self):
        self.delete("all")
        width, height = self.style['width'], self.style['height']
        
        bg_start = self.style['hover_bg_start'] if self.state == 'hover' else self.style['bg_start']
        bg_end = self.style['hover_bg_end'] if self.state == 'hover' else self.style['bg_end']

        # 1. Draw Shadow
        self._draw_shape(self.style['shadow_offset'][0], self.style['shadow_offset'][1], fill=self.style['shadow_color'])

        # 2. Draw Gradient Body
        self._draw_shape(0, 0, fill=bg_start, tags="gradient_base") 
        self._create_gradient(0, 0, width, height, bg_start, bg_end)

        # 3. Draw Text
        self.create_text(width/2, height/2, text=self.style['text'],
                         font=(self.style['font_family'], self.style['font_size']),
                         fill=self.style['fg'], anchor='center')

    def _draw_shape(self, offset_x, offset_y, **kwargs):
        w, h = self.style['width'], self.style['height']
        shape = self.style['shape']
        cr = self.style['corner_radius']
        
        if shape == 'rounded_rect':
            points = []
            points.extend(self._arc(cr + offset_x, cr + offset_y, cr, 180, 90))
            points.extend(self._arc(w - cr + offset_x, cr + offset_y, cr, 270, 90))
            points.extend(self._arc(w - cr + offset_x, h - cr + offset_y, cr, 0, 90))
            points.extend(self._arc(cr + offset_x, h - cr + offset_y, cr, 90, 90))
            return self.create_polygon(points, **kwargs, smooth=False, outline="")
        elif shape == 'pill':
            radius = h / 2
            self.create_arc(offset_x, offset_y, h+offset_x, h+offset_y, start=90, extent=180, **kwargs, outline="")
            self.create_arc(w-h+offset_x, offset_y, w+offset_x, h+offset_y, start=270, extent=180, **kwargs, outline="")
            return self.create_rectangle(h/2+offset_x, offset_y, w-h/2+offset_x, h+offset_y, **kwargs, outline="")
        elif shape == 'oval':
            return self.create_oval(offset_x, offset_y, w+offset_x, h+offset_y, **kwargs, outline="")

    def _arc(self, x, y, r, start_angle, extent):
        """Helper function to generate points for a rounded corner."""
        points = []
        for i in range(extent + 1):
            angle = math.radians(start_angle + i)
            points.append((x + r * math.cos(angle), y + r * math.sin(angle)))
        return points
            
    def _create_gradient(self, x1, y1, x2, y2, color1, color2):
        r1, g1, b1 = self.winfo_rgb(color1)
        r2, g2, b2 = self.winfo_rgb(color2)
        steps = self.style['height']
        for i in range(steps):
            nr = r1 + (r2 - r1) * i // steps
            ng = g1 + (g2 - g1) * i // steps
            nb = b1 + (b2 - b1) * i // steps
            color = f'#{nr:04x}{ng:04x}{nb:04x}'
            self.create_line(x1, y1 + i, x2, y1 + i, fill=color, tags="gradient_line")
        self.tag_raise("gradient_base")
        self.itemconfig("gradient_base", fill="", outline="")
        self.tag_lower("gradient_line", "gradient_base") 
        
    def _on_enter(self, event):
        self.state = 'hover'
        self.draw_button()

    def _on_leave(self, event):
        self.state = 'normal'
        self.draw_button()
        
    def _on_click(self, event):
        if self.command:
            self.command()

    def update_style_and_redraw(self, new_style_dict):
        self.style.update(new_style_dict)
        self.draw_button()

    def update_text(self, new_text):
        self.style['text'] = new_text
        self.draw_button()
        
# --- Main Application ---
class WhimsicalFileLauncherApp:
    def __init__(self, root, is_generated_menu=False, initial_configs=None, initial_title="Greg Seymour AI Menu Maker Deluxe", initial_root_bg=None, initial_settings=None):
        self.root = root
        self.is_generated_menu = is_generated_menu
        self.current_menu_title = initial_title
        self.root.title(self.current_menu_title)

        try: self.root.state('zoomed')
        except tk.TclError:
            try: self.root.attributes('-zoomed', True)
            except tk.TclError: self.root.geometry(f"{self.root.winfo_screenwidth()}x{self.root.winfo_screenheight()}+0+0")

        settings = initial_settings or {}
        self.num_columns = tk.IntVar(value=settings.get('num_columns', DEFAULT_NUM_COLUMNS))
        self.num_columns.trace_add("write", lambda *args: self._reflow_menu_grid())
        
        self.theme_var = tk.StringVar(value=settings.get('theme', 'Whimsical'))
        self.style_mode_var = tk.StringVar(value=settings.get('style_mode', 'Whimsical'))
        self.sort_var = tk.StringVar(value=settings.get('sort', 'Name (A-Z)'))
        
        self.use_selenium_var = tk.BooleanVar(value=settings.get('use_selenium', SELENIUM_AVAILABLE))
        self.html_fullscreen_var = tk.BooleanVar(value=settings.get('html_fullscreen', True))
        self.single_view_mode_var = tk.BooleanVar(value=settings.get('single_view_mode', False))
        self.run_order_var = tk.StringVar(value="order")
        self.loop_behavior_var = tk.StringVar(value="loop")

        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *args: self._on_search_change())

        self.current_root_bg = initial_root_bg or self._get_random_color()
        self.root.configure(bg=self.current_root_bg)

        self.selected_file_configs = []
        self.filtered_configs = []
        if initial_configs:
            for config_data in initial_configs:
                self.selected_file_configs.append({
                    'path': config_data['path'],
                    'var': tk.BooleanVar(value=False),
                    'style': config_data['style'].copy(),
                    'process_info': None,
                    'widget': None
                })
        self.filtered_configs = self.selected_file_configs[:]

        self.menu_frame = None
        self.active_selenium_driver = None
        self.is_running_sequence = False
        self.animations_running = True

        self._build_ui()
        self._start_title_animations()

        if self.is_generated_menu: self.create_menu_ui(preserve_styles=True)
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _build_ui(self):
        control_font = ("Segoe UI", 8)
        control_padx = 2
        control_pady = 1
        frame_padx = 3
        frame_pady = 3

        top_frame = tk.Frame(self.root, bg=self.current_root_bg)
        top_frame.pack(pady=5, padx=10, fill=tk.X)

        self.title_label = tk.Label(top_frame, text=self.current_menu_title, font=("Arial", 22, "bold"), bg=self.current_root_bg)
        self.title_label.pack(pady=(0, 5))

        search_frame = tk.LabelFrame(self.root, text="🔍 Live Search", padx=frame_padx, pady=frame_pady, font=control_font)
        search_frame.pack(pady=2, padx=10, fill=tk.X)
        search_entry = tk.Entry(search_frame, textvariable=self.search_var, font=("Arial", 10))
        search_entry.pack(fill=tk.X, expand=True)

        control_bar = tk.Frame(self.root, bd=2, relief=tk.GROOVE)
        control_bar.pack(pady=2, padx=10, fill=tk.X)

        file_frame = tk.LabelFrame(control_bar, text="File & Selection", padx=frame_padx, pady=frame_pady, font=control_font)
        file_frame.pack(side=tk.LEFT, padx=5, pady=2, fill=tk.Y)
        appearance_frame = tk.LabelFrame(control_bar, text="Appearance & Layout", padx=frame_padx, pady=frame_pady, font=control_font)
        appearance_frame.pack(side=tk.LEFT, padx=5, pady=2, fill=tk.Y)
        actions_frame = tk.LabelFrame(control_bar, text="Actions for Selected", padx=frame_padx, pady=frame_pady, font=control_font)
        actions_frame.pack(side=tk.LEFT, padx=5, pady=2, fill=tk.Y)
        launch_frame = tk.LabelFrame(control_bar, text="Launching & Sequences", padx=frame_padx, pady=frame_pady, font=control_font)
        launch_frame.pack(side=tk.LEFT, padx=5, pady=2, fill=tk.Y, expand=True)
        
        btn_config = {'font': control_font, 'padx': control_padx, 'pady': control_pady}
        
        if not self.is_generated_menu:
            tk.Button(file_frame, text="🌟 Select Files", command=self.select_files_and_create_menu, **btn_config).grid(row=0, column=0, sticky='ew')
            tk.Button(file_frame, text="➕ Add Files", command=self.add_files_to_menu, **btn_config).grid(row=0, column=1, sticky='ew')
            tk.Button(file_frame, text="📂 Load Menu", command=self.load_menu_from_script, **btn_config).grid(row=1, column=0, sticky='ew')
            tk.Button(file_frame, text="✨ Merge Menu(s)", command=self.merge_menus_from_scripts, **btn_config).grid(row=1, column=1, sticky='ew')
            tk.Button(file_frame, text="💾 Save Menu", command=self.prompt_and_save_menu, bg="#77DD77", **btn_config).grid(row=0, column=2, sticky='ew')
        
        tk.Button(file_frame, text="Select All", command=lambda: self.toggle_all_checkboxes(True), **btn_config).grid(row=2, column=0, sticky='ew')
        tk.Button(file_frame, text="Select None", command=lambda: self.toggle_all_checkboxes(False), **btn_config).grid(row=2, column=1, sticky='ew')
        tk.Button(file_frame, text="💾 Save Selection", command=self._save_selection, **btn_config).grid(row=3, column=0, sticky='ew')
        tk.Button(file_frame, text="📂 Load Selection", command=self._load_selection, **btn_config).grid(row=3, column=1, sticky='ew')
        tk.Button(file_frame, text="❓ Help", command=self._show_help, **btn_config).grid(row=1, column=2, sticky='ew', rowspan=3, ipady=5)

        for i in range(3): file_frame.grid_columnconfigure(i, weight=1)

        tk.Button(appearance_frame, text="🎨 Re-Enchant All", command=lambda: self.create_menu_ui(preserve_styles=False), font=control_font, pady=control_pady).grid(row=0, column=0, rowspan=2, padx=2, ipady=5)
        
        tk.Label(appearance_frame, text="Style Mode:", font=control_font).grid(row=0, column=1, sticky='w')
        tk.Radiobutton(appearance_frame, text="Whimsical", variable=self.style_mode_var, value="Whimsical", font=control_font).grid(row=0, column=2, sticky='w')
        tk.Radiobutton(appearance_frame, text="Uniform", variable=self.style_mode_var, value="Uniform", font=control_font).grid(row=0, column=3, sticky='w')
        
        tk.Label(appearance_frame, text="Theme:", font=control_font).grid(row=1, column=1, sticky='w')
        theme_options = ["Whimsical", "Monochromatic", "Analogous", "Complementary"] + sorted(list(PALETTES.keys()))
        theme_menu = tk.OptionMenu(appearance_frame, self.theme_var, *theme_options)
        theme_menu.config(font=control_font)
        theme_menu.grid(row=1, column=2, columnspan=2, sticky='ew')

        tk.Label(appearance_frame, text="Sort By:", font=control_font).grid(row=0, column=4, padx=(10,0))
        # --- CHANGE: THE BUG FIX IS HERE ---
        sort_options = ["Name (A-Z)", "Name (Z-A)", "File Type", "Date Modified (Newest)", "Date Modified (Oldest)", "File Size (Largest)", "File Size (Smallest)", "Group by Folder"]
        sort_menu = tk.OptionMenu(appearance_frame, self.sort_var, *sort_options, command=self.sort_menu)
        sort_menu.config(font=control_font)
        sort_menu.grid(row=0, column=5, sticky='ew')

        tk.Label(appearance_frame, text="Cols:", font=control_font).grid(row=1, column=4, padx=(10,0))
        tk.Spinbox(appearance_frame, from_=1, to=20, width=3, textvariable=self.num_columns, font=control_font).grid(row=1, column=5)

        tk.Button(actions_frame, text="🎨 Enchant Selected", command=self._re_enchant_selected, **btn_config).pack(padx=2, pady=1, fill=tk.X)
        tk.Button(actions_frame, text="✏️ Rename Selected", command=self._rename_selected, **btn_config).pack(padx=2, pady=1, fill=tk.X)
        tk.Button(actions_frame, text="❌ Remove Selected", command=self._remove_selected, **btn_config).pack(padx=2, pady=1, fill=tk.X)

        tk.Label(launch_frame, text="Delay(s):", font=control_font).grid(row=0, column=0)
        self.duration_entry = tk.Entry(launch_frame, width=4, font=control_font); self.duration_entry.insert(0, "1"); self.duration_entry.grid(row=0, column=1)
        tk.Radiobutton(launch_frame, text="In Order", variable=self.run_order_var, value="order", font=control_font).grid(row=0, column=2)
        tk.Radiobutton(launch_frame, text="Random", variable=self.run_order_var, value="random", font=control_font).grid(row=0, column=3)
        tk.Radiobutton(launch_frame, text="Once", variable=self.loop_behavior_var, value="once", font=control_font).grid(row=0, column=4)
        tk.Radiobutton(launch_frame, text="Loop", variable=self.loop_behavior_var, value="loop", font=control_font).grid(row=0, column=5, padx=(0,5))
        self.run_selected_button = tk.Button(launch_frame, text="🚀 Run Selected", command=self.toggle_run_sequence, font=("Segoe UI", 8, "bold"))
        self.run_selected_button.grid(row=0, column=6, rowspan=2, padx=2, ipady=2)
        
        sel_state = tk.NORMAL if SELENIUM_AVAILABLE else tk.DISABLED
        tk.Checkbutton(launch_frame, text="Use Selenium", variable=self.use_selenium_var, state=sel_state, font=control_font).grid(row=1, column=0, columnspan=2, sticky='w')
        tk.Checkbutton(launch_frame, text="Kiosk HTML", variable=self.html_fullscreen_var, font=control_font).grid(row=1, column=2, columnspan=2, sticky='w')
        tk.Checkbutton(launch_frame, text="Single View Mode", variable=self.single_view_mode_var, anchor='w', font=control_font).grid(row=1, column=4, columnspan=2, sticky='w')
        
        self.menu_display_area = tk.Frame(self.root, bg=self.current_root_bg)
        self.menu_display_area.pack(expand=True, fill=tk.BOTH, padx=5, pady=5)

    def _get_config_by_path(self, filepath):
        return next((config for config in self.selected_file_configs if config['path'] == filepath), None)

    def select_files_and_create_menu(self):
        files = filedialog.askopenfilenames(title="Select your magical files")
        if files:
            self.selected_file_configs = [self._create_new_config(f) for f in files]
            self.sort_menu()

    def add_files_to_menu(self):
        if not self.selected_file_configs: return self.select_files_and_create_menu()
        files = filedialog.askopenfilenames(title="Select more magical files to add")
        if files:
            existing_paths = {c['path'] for c in self.selected_file_configs}
            for f in files:
                abs_path = os.path.abspath(f)
                if abs_path not in existing_paths:
                    self.selected_file_configs.append(self._create_new_config(abs_path))
            self.sort_menu()

    def _create_new_config(self, filepath):
        return {'path': os.path.abspath(filepath), 'var': tk.BooleanVar(value=False), 'style': {}, 'process_info': None, 'widget': None}

    def _clear_menu_display_area(self):
        for widget in self.menu_display_area.winfo_children():
            widget.destroy()
        self.menu_frame = None

    def create_menu_ui(self, preserve_styles=False):
        if not self.selected_file_configs:
            if not self.is_generated_menu: messagebox.showinfo("No Files", "No files selected.")
            return

        if not preserve_styles:
            self.current_root_bg = self._get_random_color(avoid=self.current_root_bg)
            self.root.configure(bg=self.current_root_bg)
            self.menu_display_area.configure(bg=self.current_root_bg)
            uniform_style = self._generate_style_dict() if self.style_mode_var.get() == 'Uniform' else None
            for config in self.selected_file_configs:
                saved_text = config['style'].get('text')
                config['style'] = uniform_style.copy() if uniform_style else self._generate_style_dict()
                if saved_text: config['style']['text'] = saved_text
        
        self._on_search_change()

    def _reflow_menu_grid(self, *args):
        if not self.menu_frame: return
        for widget in self.menu_frame.winfo_children(): widget.destroy()
        self._populate_menu_grid()
        
    def _build_scrollable_frame(self):
        self._clear_menu_display_area()
        canvas = tk.Canvas(self.menu_display_area, bg=self.current_root_bg, highlightthickness=0)
        scrollbar = tk.Scrollbar(self.menu_display_area, orient="vertical", command=canvas.yview)
        self.menu_frame = tk.Frame(canvas, bg=self.current_root_bg)
        
        self.menu_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.menu_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        def _on_mousewheel(event): canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        self.root.bind_all("<MouseWheel>", _on_mousewheel)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def _populate_menu_grid(self):
        if self.menu_frame is None or not self.menu_frame.winfo_exists():
            self._build_scrollable_frame()

        cols = self.num_columns.get()
        if cols <= 0: return

        for widget in self.menu_frame.winfo_children(): widget.destroy()
        for c in range(cols): self.menu_frame.grid_columnconfigure(c, weight=1)
            
        current_row_offset = 0
        last_group_key = None

        for i, config in enumerate(self.filtered_configs):
            if self.sort_var.get() == "Group by Folder":
                current_group_key = os.path.dirname(config['path'])
                if current_group_key != last_group_key:
                    header = tk.Label(self.menu_frame, text=current_group_key, font=("Arial", 12, "bold"),
                                      bg=self.current_root_bg, anchor='w', padx=10, pady=5)
                    header.grid(row=current_row_offset, column=0, columnspan=cols, sticky='ew', pady=(10, 2))
                    current_row_offset += 1
                    last_group_key = current_group_key
            
            row, col = divmod(i, cols)
            
            item_f = tk.Frame(self.menu_frame, bg=self.menu_frame.cget("bg"))
            item_f.grid(row=row + current_row_offset, column=col, padx=5, pady=5, sticky="nsew")

            tk.Checkbutton(item_f, variable=config['var'], bg=item_f.cget("bg")).pack(side=tk.LEFT, padx=(0, 5))
            
            btn_text = config['style'].get('text', os.path.basename(config['path']))
            btn_text_short = btn_text[:25] + '...' if len(btn_text) > 28 else btn_text
            config['style']['text'] = btn_text_short

            if config.get('widget') and config['widget'].winfo_exists():
                btn = config['widget']
                btn.master.destroy()
                btn = CanvasButton(item_f, command=lambda p=config['path']: self.launch_file(p), **config['style'])
            else:
                 btn = CanvasButton(item_f, command=lambda p=config['path']: self.launch_file(p), **config['style'])

            btn.pack(side=tk.LEFT, fill=tk.X, expand=True)
            btn.bind("<Button-3>", lambda e, c=config: self._show_context_menu(e, c))
            config['widget'] = btn

    def _generate_style_dict(self):
        theme = self.theme_var.get()
        palette = self._get_palette_for_theme(theme)
        
        bg1 = random.choice(palette)
        bg2 = random.choice([c for c in palette if c != bg1] or [bg1])
        hover_bg1 = self._adjust_brightness(bg1, 1.2)
        hover_bg2 = self._adjust_brightness(bg2, 1.2)
        shadow = self._adjust_brightness(bg1, 0.6)

        style = {
            'shape': random.choice(BUTTON_SHAPES), 'font_family': random.choice(WHIMSICAL_FONTS),
            'font_size': random.randint(11, 15), 'bg_start': bg1, 'bg_end': bg2,
            'hover_bg_start': hover_bg1, 'hover_bg_end': hover_bg2, 'shadow_color': shadow,
            'corner_radius': random.randint(10, 25), 'height': 50, 'width': 220,
        }
        avg_color_for_fg = self._average_hex_colors(bg1, bg2)
        style['fg'] = self._get_contrasting_color(avg_color_for_fg)
        return style

    # --- THEME AND COLOR HELPERS ---
    def _get_palette_for_theme(self, theme):
        if theme in PALETTES: return PALETTES[theme]
        elif theme == "Whimsical": return WHIMSICAL_COLORS
        else:
            base_color = self._get_random_color()
            if theme == "Monochromatic": return self._get_monochromatic_palette(base_color)
            elif theme == "Analogous": return self._get_analogous_palette(base_color)
            elif theme == "Complementary": return self._get_complementary_palette(base_color)
        return WHIMSICAL_COLORS
    
    def _hex_to_hls(self, hex_color):
        hex_color = hex_color.lstrip('#')
        r, g, b = [int(hex_color[i:i+2], 16)/255.0 for i in (0, 2, 4)]
        return colorsys.rgb_to_hls(r, g, b)

    def _hls_to_hex(self, h, l, s):
        r, g, b = colorsys.hls_to_rgb(h, l, s)
        return f'#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}'

    def _get_monochromatic_palette(self, hex_color, n=5):
        h, l, s = self._hex_to_hls(hex_color)
        return [self._hls_to_hex(h, min(1, max(0, l + (i - n//2) * 0.1)), s) for i in range(n)]

    def _get_analogous_palette(self, hex_color, n=5):
        h, l, s = self._hex_to_hls(hex_color)
        return [self._hls_to_hex((h + (i - n//2) * 0.08) % 1.0, l, s) for i in range(n)]

    def _get_complementary_palette(self, hex_color, n=6):
        h, l, s = self._hex_to_hls(hex_color)
        comp_h = (h + 0.5) % 1.0
        p1 = self._get_monochromatic_palette(self._hls_to_hex(h, l, s), n//2)
        p2 = self._get_monochromatic_palette(self._hls_to_hex(comp_h, l, s), n//2)
        return p1 + p2

    def _get_random_color(self, avoid=None):
        color = random.choice(WHIMSICAL_COLORS)
        while color == avoid: color = random.choice(WHIMSICAL_COLORS)
        return color
        
    def _get_contrasting_color(self, bg_color_hex):
        try:
            r,g,b=int(bg_color_hex[1:3],16),int(bg_color_hex[3:5],16),int(bg_color_hex[5:7],16)
            return "#000000" if (0.299*r+0.587*g+0.114*b)>128 else "#FFFFFF"
        except: return "#000000"

    def _adjust_brightness(self, hex_color, factor):
        h, l, s = self._hex_to_hls(hex_color)
        l = max(0, min(1, l * factor))
        return self._hls_to_hex(h, l, s)

    def _average_hex_colors(self, c1, c2):
        r1,g1,b1 = int(c1[1:3],16),int(c1[3:5],16),int(c1[5:7],16)
        r2,g2,b2 = int(c2[1:3],16),int(c2[3:5],16),int(c2[5:7],16)
        r,g,b = (r1+r2)//2, (g1+g2)//2, (b1+b2)//2
        return f'#{r:02x}{g:02x}{b:02x}'
        
    # --- ANIMATIONS ---
    def _start_title_animations(self):
        self._animate_title_color()

    def _animate_title_color(self):
        if not self.animations_running: return
        try:
            h, l, s = colorsys.rgb_to_hls(*[x/255.0 for x in self.title_label.winfo_rgb(self.title_label.cget('fg'))])
            h = (h + 0.005) % 1.0
            new_color = self._hls_to_hex(h, 0.5, 1.0)
            self.title_label.config(fg=new_color)
            self.root.after(50, self._animate_title_color)
        except (tk.TclError, AttributeError):
            self.animations_running = False

    # --- SORTING, SEARCHING, and FILTERING ---
    def _on_search_change(self, *args):
        search_term = self.search_var.get().lower()
        if not search_term:
            self.filtered_configs = self.selected_file_configs[:]
        else:
            self.filtered_configs = []
            for c in self.selected_file_configs:
                display_name = c['style'].get('text', os.path.basename(c['path'])).lower()
                if search_term in display_name:
                    self.filtered_configs.append(c)
        
        self._populate_menu_grid()

    def sort_menu(self, *args):
        sort_key = self.sort_var.get(); reverse = False
        
        def get_mtime(c):
            try: return os.path.getmtime(c['path'])
            except OSError: return 0
        def get_size(c):
            try: return os.path.getsize(c['path'])
            except OSError: return 0

        if sort_key == "Name (A-Z)": key_func = lambda c: os.path.basename(c['path']).lower()
        elif sort_key == "Name (Z-A)": key_func = lambda c: os.path.basename(c['path']).lower(); reverse = True
        elif sort_key == "File Type": key_func = lambda c: os.path.splitext(c['path'])[1].lower()
        elif sort_key == "Date Modified (Newest)": key_func = get_mtime; reverse = True
        elif sort_key == "Date Modified (Oldest)": key_func = get_mtime
        elif sort_key == "File Size (Largest)": key_func = get_size; reverse = True
        elif sort_key == "File Size (Smallest)": key_func = get_size
        elif sort_key == "Group by Folder": key_func = lambda c: (os.path.dirname(c['path']), os.path.basename(c['path']).lower())
        else: return

        self.selected_file_configs.sort(key=key_func, reverse=reverse)
        self._on_search_change()
    
    # --- LAUNCHING & SEQUENCES ---
    def launch_file(self, filepath, is_part_of_sequence=False):
        if self.single_view_mode_var.get() or is_part_of_sequence: self._terminate_all_managed_processes()
        abs_path = os.path.abspath(filepath); current_config = self._get_config_by_path(abs_path)
        _, ext = os.path.splitext(filepath); ext = ext.lower()
        print(f"Launching: {abs_path}")
        try:
            if ext == '.py':
                popen_obj = subprocess.Popen([sys.executable, abs_path])
                if current_config: current_config['process_info'] = {'type': 'popen', 'instance': popen_obj}
            elif ext in ['.html', '.htm']:
                if self.use_selenium_var.get() and SELENIUM_AVAILABLE: self._launch_selenium_html_in_thread(abs_path)
                else: webbrowser.open(f'file:///{abs_path}')
            else:
                if sys.platform == "win32": os.startfile(abs_path)
                elif sys.platform == "darwin": subprocess.Popen(['open', abs_path])
                else: subprocess.Popen(['xdg-open', abs_path])
        except Exception as e: messagebox.showerror("Launch Error", f"Could not open file: {os.path.basename(filepath)}\nError: {e}", parent=self.root)

    def _launch_selenium_html_in_thread(self, filepath):
        if self.active_selenium_driver: self._terminate_all_managed_processes(); time.sleep(0.5)
        def task():
            try:
                chrome_options = ChromeOptions()
                chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
                chrome_options.add_experimental_option('useAutomationExtension', False)
                if self.html_fullscreen_var.get(): chrome_options.add_argument("--kiosk")
                self.active_selenium_driver = webdriver.Chrome(options=chrome_options)
                self.active_selenium_driver.get(f"file:///{filepath}")
                while self.active_selenium_driver and self.active_selenium_driver.window_handles: time.sleep(0.5)
            except Exception as e: print(f"Selenium thread error: {e}")
            finally:
                if self.active_selenium_driver:
                    try: self.active_selenium_driver.quit()
                    except: pass
                self.active_selenium_driver = None
        threading.Thread(target=task, daemon=True).start()

    def toggle_run_sequence(self):
        if self.is_running_sequence:
            self.is_running_sequence = False; self.run_selected_button.config(text="🚀 Run Selected")
            self.root.after(100, self._terminate_all_managed_processes)
            messagebox.showinfo("Stopped", "Sequence has been stopped.", parent=self.root)
            return

        selected_to_run = [c for c in self.selected_file_configs if c['var'].get()]
        if not selected_to_run: messagebox.showwarning("Nothing Selected", "Check boxes to run a sequence.", parent=self.root); return
        try: delay = float(self.duration_entry.get()); delay = max(0, delay)
        except ValueError: messagebox.showerror("Invalid Delay", "Please enter a valid number for the delay.", parent=self.root); return
            
        self.is_running_sequence = True; self.current_sequence_configs = selected_to_run[:]
        self.run_selected_button.config(text="🛑 Stop Sequence")
        self._start_launch_sequence(self.current_sequence_configs, self.run_order_var.get(), self.loop_behavior_var.get() == "loop", delay)

    def _start_launch_sequence(self, configs_to_run, order, loop, delay):
        mutable_list = list(configs_to_run)
        def _recursive_launch(index=0):
            if not self.is_running_sequence or not self.root.winfo_exists():
                if self.root.winfo_exists(): self.run_selected_button.config(text="🚀 Run Selected")
                return
            if order == "random" and index == 0: random.shuffle(mutable_list)
            actual_index = index % len(mutable_list)
            self.launch_file(mutable_list[actual_index]['path'], is_part_of_sequence=True)
            next_index = index + 1
            if next_index < len(mutable_list) or loop:
                if self.root.winfo_exists(): self.root.after(int(delay * 1000), lambda: _recursive_launch(next_index))
            else:
                self.is_running_sequence = False
                if self.root.winfo_exists():
                    self.run_selected_button.config(text="🚀 Run Selected")
                    messagebox.showinfo("Sequence Complete", "The sequence has finished.", parent=self.root)
                self._terminate_all_managed_processes()
        if self.root.winfo_exists(): _recursive_launch()

    def _terminate_all_managed_processes(self):
        if self.active_selenium_driver:
            driver = self.active_selenium_driver; self.active_selenium_driver = None
            threading.Thread(target=driver.quit, daemon=True).start()
        for config in self.selected_file_configs:
            if config.get('process_info'):
                proc = config['process_info'].get('instance')
                if proc and proc.poll() is None: proc.terminate()
                config['process_info'] = None

    def _on_closing(self):
        self.animations_running = False
        self._terminate_all_managed_processes()
        if self.root.winfo_exists(): self.root.destroy()
        
    # --- CONTEXT MENU AND ITEM MANAGEMENT ---
    def _show_context_menu(self, event, config):
        context_menu = tk.Menu(self.root, tearoff=0)
        context_menu.add_command(label="Edit Button Text", command=lambda: self._edit_button_text(config))
        context_menu.add_command(label="Remove From Menu", command=lambda: self._remove_item(config))
        context_menu.tk_popup(event.x_root, event.y_root)

    def _edit_button_text(self, config):
        old_text = config['style'].get('text', os.path.basename(config['path']))
        new_text = simpledialog.askstring("Edit Text", "Enter new button text:", initialvalue=old_text, parent=self.root)
        if new_text and config.get('widget'):
            config['style']['text'] = new_text
            short_text = new_text[:25] + '...' if len(new_text) > 28 else new_text
            config['widget'].update_text(short_text)

    def _remove_item(self, config_to_remove):
        self.selected_file_configs.remove(config_to_remove)
        self._on_search_change()

    def toggle_all_checkboxes(self, state=True):
        for config in self.filtered_configs:
            config['var'].set(state)

    # --- MULTI-SELECT ACTIONS ---
    def _get_selected_configs(self):
        return [c for c in self.selected_file_configs if c['var'].get()]

    def _re_enchant_selected(self):
        selected = self._get_selected_configs()
        if not selected:
            messagebox.showwarning("No Selection", "Check the boxes next to the items you want to re-enchant.", parent=self.root)
            return
        
        uniform_style = self._generate_style_dict() if self.style_mode_var.get() == 'Uniform' else None
        for config in selected:
            saved_text = config['style'].get('text', os.path.basename(config['path']))
            new_style = uniform_style.copy() if uniform_style else self._generate_style_dict()
            new_style['text'] = saved_text
            config['style'] = new_style
            if config.get('widget') and config['widget'].winfo_exists():
                config['widget'].update_style_and_redraw(new_style)
        
        messagebox.showinfo("Enchantment Complete", f"{len(selected)} items have been re-enchanted!", parent=self.root)

    def _rename_selected(self):
        selected = self._get_selected_configs()
        if not selected:
            messagebox.showwarning("No Selection", "Check the boxes next to the items you want to rename.", parent=self.root)
            return
        
        base_name = simpledialog.askstring("Bulk Rename", "Enter the base name for the selected items (e.g., 'Chapter'). A number will be added.", parent=self.root)
        if not base_name: return
        start_num_str = simpledialog.askstring("Bulk Rename", "Enter the starting number:", initialvalue="1", parent=self.root)
        try: start_num = int(start_num_str)
        except (ValueError, TypeError): return

        for i, config in enumerate(selected):
            new_text = f"{base_name} {start_num + i}"
            config['style']['text'] = new_text
            if config.get('widget') and config['widget'].winfo_exists():
                short_text = new_text[:25] + '...' if len(new_text) > 28 else new_text
                config['widget'].update_text(short_text)

    def _remove_selected(self):
        selected = self._get_selected_configs()
        if not selected:
            messagebox.showwarning("No Selection", "Check the boxes next to the items you want to remove.", parent=self.root)
            return
        
        if messagebox.askyesno("Confirm Removal", f"Are you sure you want to remove {len(selected)} items from the menu?", parent=self.root):
            for config in selected:
                if config in self.selected_file_configs:
                    self.selected_file_configs.remove(config)
            self._on_search_change()

    # --- HELP WINDOW ---
    def _show_help(self):
        help_text = """
--- Greg Seymour AI Menu Maker Deluxe - Help ---

This tool allows you to create beautiful, runnable menus from any files on your computer.

- File & Selection -
  - Select/Add Files: Start a new menu or add more files to the current one.
  - Load/Save Menu: Save your entire menu layout and styles as a standalone Python (.py) script. You can run this script directly or load it back into the Menu Maker to edit it.
  - Merge Menu(s): Select one or more saved menu scripts to add their items to your current menu, skipping any duplicates.
  - Save/Load Selection: Save just the currently *checked* items to a simple '.sel' file. Load it later to quickly re-check the same items. Useful for saving task groups.
  - Select All / Select None: Toggles the checkboxes for all items.
    NOTE: These buttons only affect the items currently visible in the menu (respecting any active search filter).

- Search & Filtering -
  - The 'Live Search' bar at the top instantly filters the menu as you type. It searches button names. Clear the bar to see all items again.

- Appearance & Layout -
  - Re-Enchant All: Applies new random styles to EVERY item in the menu.
  - Style Mode: 'Whimsical' gives every button a unique look. 'Uniform' makes all buttons share the same style.
  - Theme: Choose a color palette for the random styles.
  - Sort By: Reorder the items in the menu.
  - Cols: Change the number of columns in the menu grid.

- Actions for Selected -
  These buttons only affect items with their checkbox ticked.
  - Enchant Selected: Applies a new random style to ONLY the selected items.
  - Rename Selected: Lets you rename multiple items at once with a base name and an incrementing number (e.g., Level 1, Level 2...).
  - Remove Selected: Deletes all checked items from the menu.

- Launching & Sequences -
  - Check the boxes for the files you want to run in a sequence.
  - Delay(s): The time in seconds between launching each file.
  - Run Selected: Starts the sequence. Click 'Stop Sequence' to end it.
  - Use Selenium/Kiosk: For opening HTML files in a dedicated, fullscreen Chrome window.
  - Single View Mode: When launching any file, it will automatically close any other program previously launched by the menu.

- Right-Click Menu -
  - Right-click on any button to edit its text individually or remove it from the menu.
"""
        help_win = tk.Toplevel(self.root)
        help_win.title("Help / Instructions")
        text_widget = tk.Text(help_win, wrap=tk.WORD, padx=10, pady=10, font=("Segoe UI", 10))
        text_widget.insert(tk.END, help_text)
        text_widget.config(state=tk.DISABLED)
        text_widget.pack(expand=True, fill=tk.BOTH)
        
    # --- SAVE / LOAD ---
    def _parse_menu_script(self, filename):
        with open(filename, 'r', encoding='utf-8') as f: source_code = f.read()
        tree = ast.parse(source_code)
        main_block = next((node for node in tree.body if isinstance(node, ast.If) and isinstance(node.test, ast.Compare) and node.test.comparators[0].s == '__main__'), None)
        if not main_block: raise ValueError("Could not find __main__ block.")
        def get_value(var_name): return ast.literal_eval(next(n.value for n in main_block.body if isinstance(n, ast.Assign) and n.targets[0].id == var_name))
        return { 'title': get_value('SAVED_MENU_TITLE_STR'), 'configs': get_value('SAVED_FILE_CONFIGS_DATA'), 'bg': get_value('INITIAL_ROOT_BG_STR'), 'settings': get_value('SAVED_APP_SETTINGS') }

    def load_menu_from_script(self):
        py_filename = filedialog.askopenfilename(title="Load Menu Script", filetypes=[("Python Menu Script", "*.py")], parent=self.root)
        if not py_filename: return
        try:
            data = self._parse_menu_script(py_filename)
            self.current_menu_title = data['title']; self.root.title(data['title']); self.title_label.config(text=data['title'])
            self.current_root_bg = data['bg']; self.root.config(bg=data['bg'])
            for key, var in vars(self).items():
                if isinstance(var, (tk.IntVar, tk.StringVar, tk.BooleanVar)):
                    setting_key = key.replace('_var', '')
                    if setting_key in data['settings']: var.set(data['settings'][setting_key])
            self.selected_file_configs = [{'path': c['path'], 'var': tk.BooleanVar(value=False), 'style': c['style'].copy(),'process_info': None, 'widget': None} for c in data['configs']]
            self.sort_menu()
            messagebox.showinfo("Load Success", "Menu loaded successfully.", parent=self.root)
        except Exception as e: messagebox.showerror("Load Error", f"Failed to parse menu script.\nError: {e}", parent=self.root)

    def merge_menus_from_scripts(self):
        py_filenames = filedialog.askopenfilenames(title="Select Menu Scripts to Merge", filetypes=[("Python Menu Script", "*.py")], parent=self.root)
        if not py_filenames: return
        existing_paths = {c['path'] for c in self.selected_file_configs}; added_count = 0; skipped_count = 0
        for filename in py_filenames:
            try:
                data = self._parse_menu_script(filename)
                for config_data in data['configs']:
                    if config_data['path'] not in existing_paths:
                        new_config = { 'path': config_data['path'], 'var': tk.BooleanVar(value=False), 'style': config_data['style'].copy(), 'process_info': None, 'widget': None }
                        self.selected_file_configs.append(new_config); existing_paths.add(new_config['path']); added_count += 1
                    else: skipped_count += 1
            except Exception as e: messagebox.showwarning("Merge Warning", f"Could not parse file:\n{os.path.basename(filename)}\nError: {e}\n\nSkipping this file.", parent=self.root)
        if added_count > 0: self.sort_menu()
        messagebox.showinfo("Merge Complete", f"Merge operation finished.\n\nAdded: {added_count} new items.\nSkipped: {skipped_count} duplicates.", parent=self.root)

    def _save_selection(self):
        selected = self._get_selected_configs()
        if not selected: messagebox.showwarning("Nothing to Save", "Check some boxes to save a selection.", parent=self.root); return
        filepath = filedialog.asksaveasfilename(defaultextension=".sel", filetypes=[("Menu Selections", "*.sel")], title="Save Selection As...", parent=self.root)
        if not filepath: return
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                for config in selected: f.write(config['path'] + '\n')
            messagebox.showinfo("Success", f"Selection of {len(selected)} items saved.", parent=self.root)
        except Exception as e: messagebox.showerror("Save Error", f"Could not save selection file:\n{e}", parent=self.root)

    def _load_selection(self):
        filepath = filedialog.askopenfilename(filetypes=[("Menu Selections", "*.sel")], title="Load Selection", parent=self.root)
        if not filepath: return
        try:
            with open(filepath, 'r', encoding='utf-8') as f: paths_to_select = {line.strip() for line in f if line.strip()}
            loaded_count = 0
            for config in self.selected_file_configs:
                if config['path'] in paths_to_select: config['var'].set(True); loaded_count += 1
                else: config['var'].set(False)
            messagebox.showinfo("Selection Loaded", f"Loaded and selected {loaded_count} items from the file.", parent=self.root)
        except Exception as e: messagebox.showerror("Load Error", f"Could not load selection file:\n{e}", parent=self.root)

    def prompt_and_save_menu(self):
        if not self.selected_file_configs: messagebox.showerror("No Menu","No menu to save.",parent=self.root); return
        title = simpledialog.askstring("Menu Title","Enter a title for your menu:", initialvalue=self.current_menu_title, parent=self.root)
        if not title: return
        py_filename = filedialog.asksaveasfilename(defaultextension=".py", filetypes=[("Python Menu Script", "*.py")], parent=self.root, title="Save Menu As...")
        if not py_filename: return
        configs = [{'path': c['path'], 'style': c['style']} for c in self.selected_file_configs]
        settings = {key.replace('_var',''): var.get() for key, var in vars(self).items() if isinstance(var, (tk.IntVar, tk.StringVar, tk.BooleanVar)) and key != 'search_var'}
        script_content = self._generate_menu_script_content(title, configs, self.current_root_bg, settings)
        try:
            with open(py_filename, "w", encoding="utf-8") as f: f.write(script_content)
            messagebox.showinfo("Menu Saved", f"Menu script saved as:\n{py_filename}", parent=self.root)
        except Exception as e: messagebox.showerror("Save Error", f"Could not save menu script:\n{e}", parent=self.root)

    def _generate_menu_script_content(self, title, configs, bg, settings):
        class_source = inspect.getsource(WhimsicalFileLauncherApp)
        canvas_button_source = inspect.getsource(CanvasButton)
        required_imports = "import tkinter as tk; from tkinter import filedialog, messagebox, simpledialog, font\nimport os, subprocess, webbrowser, random, time, sys, threading, ast, colorsys, inspect, math"
        return f"""# Generated Menu Script by Greg Seymour AI Menu Maker Deluxe
# To edit this menu, use "Load Menu" in the creator application.
{required_imports}
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    SELENIUM_AVAILABLE = True
except ImportError: SELENIUM_AVAILABLE = False

# --- Constants and Classes from the Creator ---
PALETTES = {repr(PALETTES)}
WHIMSICAL_COLORS = {repr(WHIMSICAL_COLORS)}
WHIMSICAL_FONTS = {repr(WHIMSICAL_FONTS)}
BUTTON_SHAPES = {repr(BUTTON_SHAPES)}
DEFAULT_NUM_COLUMNS = {DEFAULT_NUM_COLUMNS}

{canvas_button_source}
{class_source}

# --- Saved Menu Configuration ---
if __name__ == "__main__":
    SAVED_MENU_TITLE_STR = {repr(title)}
    SAVED_FILE_CONFIGS_DATA = {repr(configs)}
    INITIAL_ROOT_BG_STR = {repr(bg)}
    SAVED_APP_SETTINGS = {repr(settings)}
    
    root = tk.Tk()
    app = WhimsicalFileLauncherApp(root, is_generated_menu=True, initial_configs=SAVED_FILE_CONFIGS_DATA,
        initial_title=SAVED_MENU_TITLE_STR, initial_root_bg=INITIAL_ROOT_BG_STR, initial_settings=SAVED_APP_SETTINGS)
    root.mainloop()
"""

if __name__ == "__main__":
    main_creator_root = tk.Tk()
    creator_app = WhimsicalFileLauncherApp(main_creator_root)
    main_creator_root.mainloop()