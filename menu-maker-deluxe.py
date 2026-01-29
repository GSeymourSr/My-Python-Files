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

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

# --- Constants (Expanded for more variety) ---
WHIMSICAL_COLORS = [
    "#FFADAD", "#FFD6A5", "#FDFFB6", "#CAFFBF", "#9BF6FF", "#A0C4FF", "#BDB2FF", "#FFC6FF",
    "#FFB3BA", "#FFDFBA", "#FFFFBA", "#BAFFC9", "#BAE1FF", "#E0BBE4", "#FEC8D8", "#FFDFD3",
    "#D16BA5", "#86A8E7", "#5FFBF1", "#A267AC", "#F67280", "#C06C84", "#6C5B7B", "#355C7D",
    "#F4A261", "#E76F51", "#2A9D8F", "#264653", "#E9C46A", "#F7B267", "#F79D65", "#F4845F",
    "#F27059", "#F25C54", "#A7C957", "#6A994E", "#386641", "#BC4749", "#6A040F", "#B5179E"
]
WHIMSICAL_FONTS = [
    "Comic Sans MS", "Papyrus", "Curlz MT", "Kristen ITC", "Jokerman", "Lucida Handwriting",
    "Brush Script MT", "Segoe Print", "Arial", "Verdana", "Helvetica", "Impact" # Fallbacks
]
RELIEF_STYLES = [tk.RAISED, tk.SUNKEN, tk.GROOVE, tk.RIDGE] # Flat is less fun
DEFAULT_NUM_COLUMNS = 3
# --- End Constants ---

class WhimsicalFileLauncherApp:
    def __init__(self, root, is_generated_menu=False, initial_configs=None, initial_title="✨ Whimsical File Launcher Creator ✨", initial_root_bg=None, initial_settings=None):
        self.root = root
        self.is_generated_menu = is_generated_menu
        self.current_menu_title = initial_title
        self.root.title(self.current_menu_title)

        try: self.root.state('zoomed')
        except tk.TclError:
            try: self.root.attributes('-zoomed', True)
            except tk.TclError: self.root.geometry(f"{self.root.winfo_screenwidth()}x{self.root.winfo_screenheight()}+0+0")

        # --- Settings with tk Variables ---
        settings = initial_settings or {}
        self.num_columns = tk.IntVar(value=settings.get('num_columns', DEFAULT_NUM_COLUMNS))
        self.style_mode_var = tk.StringVar(value=settings.get('style_mode', 'whimsical'))
        self.use_selenium_var = tk.BooleanVar(value=settings.get('use_selenium', SELENIUM_AVAILABLE))
        self.html_fullscreen_var = tk.BooleanVar(value=settings.get('html_fullscreen', True))
        self.single_view_mode_var = tk.BooleanVar(value=settings.get('single_view_mode', False))
        self.run_order_var = tk.StringVar(value="order")
        self.loop_behavior_var = tk.StringVar(value="once")

        self.current_root_bg = initial_root_bg or self._get_random_color(light_bias=True)
        self.root.configure(bg=self.current_root_bg)

        self.selected_file_configs = []
        if initial_configs:
            for config_data in initial_configs:
                self.selected_file_configs.append({
                    'path': config_data['path'],
                    'var': tk.BooleanVar(value=False),
                    'style': config_data['style'].copy(),
                    'process_info': None
                })

        # --- State Variables ---
        self.menu_frame = None
        self.active_selenium_driver = None
        self.is_running_sequence = False
        self.current_sequence_configs = []

        self._build_ui()

        if self.is_generated_menu: self.create_menu_ui(preserve_styles=True)
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _build_ui(self):
        # --- Top Control Frame ---
        top_frame = tk.Frame(self.root, bg=self.current_root_bg)
        top_frame.pack(pady=5, padx=10, fill=tk.X)

        self.title_label = tk.Label(top_frame, text=self.current_menu_title, font=(random.choice(WHIMSICAL_FONTS), 20, "bold"))
        self.title_label.pack(pady=(0, 10))
        self._update_title_label_style(update_root_bg=False)

        # --- Main Control Bar ---
        control_bar = tk.Frame(self.root, bd=2, relief=tk.GROOVE)
        control_bar.pack(pady=5, padx=10, fill=tk.X)

        # Section Frames
        file_frame = tk.LabelFrame(control_bar, text="File Management", padx=5, pady=5)
        file_frame.pack(side=tk.LEFT, padx=5, pady=5, fill=tk.Y)
        appearance_frame = tk.LabelFrame(control_bar, text="Appearance", padx=5, pady=5)
        appearance_frame.pack(side=tk.LEFT, padx=5, pady=5, fill=tk.Y)
        launch_frame = tk.LabelFrame(control_bar, text="Launching & Sequences", padx=5, pady=5)
        launch_frame.pack(side=tk.LEFT, padx=5, pady=5, fill=tk.Y, expand=True)

        # File Management Widgets
        if not self.is_generated_menu:
            tk.Button(file_frame, text="🌟 Select Files", command=self.select_files_and_create_menu).pack(side=tk.LEFT, padx=2)
            tk.Button(file_frame, text="➕ Add Files", command=self.add_files_to_menu).pack(side=tk.LEFT, padx=2)
            tk.Button(file_frame, text="📂 Load Menu", command=self.load_menu_from_script).pack(side=tk.LEFT, padx=2)
            tk.Button(file_frame, text="💾 Save Menu", command=self.prompt_and_save_menu, bg="#77DD77").pack(side=tk.LEFT, padx=(10, 2))
        
        tk.Button(file_frame, text="Select All", command=lambda: self.toggle_all_checkboxes(True)).pack(side=tk.LEFT, padx=2)
        tk.Button(file_frame, text="Select None", command=lambda: self.toggle_all_checkboxes(False)).pack(side=tk.LEFT, padx=2)

        # Appearance Widgets
        tk.Button(appearance_frame, text="🎨 Re-Enchant", command=lambda: self.create_menu_ui(preserve_styles=False)).pack(side=tk.LEFT, padx=2)
        tk.Label(appearance_frame, text="Style:").pack(side=tk.LEFT, padx=(5,0))
        tk.Radiobutton(appearance_frame, text="Whimsical", variable=self.style_mode_var, value="whimsical").pack(side=tk.LEFT)
        tk.Radiobutton(appearance_frame, text="Uniform", variable=self.style_mode_var, value="uniform").pack(side=tk.LEFT)
        tk.Label(appearance_frame, text="Cols:").pack(side=tk.LEFT, padx=(5,0))
        tk.Spinbox(appearance_frame, from_=1, to=10, width=3, textvariable=self.num_columns).pack(side=tk.LEFT)

        # Launching Widgets
        tk.Label(launch_frame, text="Delay(s):").grid(row=0, column=0)
        self.duration_entry = tk.Entry(launch_frame, width=4); self.duration_entry.insert(0, "1"); self.duration_entry.grid(row=0, column=1)
        tk.Radiobutton(launch_frame, text="In Order", variable=self.run_order_var, value="order").grid(row=0, column=2)
        tk.Radiobutton(launch_frame, text="Random", variable=self.run_order_var, value="random").grid(row=0, column=3)
        tk.Radiobutton(launch_frame, text="Run Once", variable=self.loop_behavior_var, value="once").grid(row=0, column=4)
        tk.Radiobutton(launch_frame, text="Loop", variable=self.loop_behavior_var, value="loop").grid(row=0, column=5, padx=(0,10))
        self.run_selected_button = tk.Button(launch_frame, text="🚀 Run Selected", command=self.toggle_run_sequence, font=("Arial", 10, "bold"))
        self.run_selected_button.grid(row=0, column=6, rowspan=2, padx=5, ipady=5)
        
        sel_state = tk.NORMAL if SELENIUM_AVAILABLE else tk.DISABLED
        tk.Checkbutton(launch_frame, text="Use Selenium", variable=self.use_selenium_var, state=sel_state).grid(row=1, column=0, columnspan=2, sticky='w')
        tk.Checkbutton(launch_frame, text="Kiosk HTML", variable=self.html_fullscreen_var).grid(row=1, column=2, columnspan=2, sticky='w')
        tk.Checkbutton(launch_frame, text="Single View Mode", variable=self.single_view_mode_var, anchor='w').grid(row=1, column=4, columnspan=2, sticky='w')
        
        self.menu_display_area = tk.Frame(self.root, bg=self.current_root_bg)
        self.menu_display_area.pack(expand=True, fill=tk.BOTH, padx=5, pady=5)

    # --- FIX: RESTORED HELPER METHOD ---
    def _get_config_by_path(self, filepath):
        """Finds the configuration dictionary for a given absolute file path."""
        return next((config for config in self.selected_file_configs if config['path'] == filepath), None)

    def select_files_and_create_menu(self):
        files = filedialog.askopenfilenames(title="Select your magical files")
        if files:
            self.selected_file_configs = [self._create_new_config(f) for f in files]
            self.create_menu_ui()

    def add_files_to_menu(self):
        if not self.selected_file_configs: return self.select_files_and_create_menu()
        files = filedialog.askopenfilenames(title="Select more magical files to add")
        if files:
            existing_paths = {c['path'] for c in self.selected_file_configs}
            new_files_added = any(os.path.abspath(f) not in existing_paths for f in files)
            if new_files_added:
                for f in files:
                    abs_path = os.path.abspath(f)
                    if abs_path not in existing_paths:
                        self.selected_file_configs.append(self._create_new_config(abs_path))
                        existing_paths.add(abs_path)
                self.create_menu_ui(preserve_styles=True)
            else:
                messagebox.showinfo("No New Files", "All selected files are already in the menu.", parent=self.root)

    def _create_new_config(self, filepath):
        return {'path': os.path.abspath(filepath), 'var': tk.BooleanVar(value=False), 'style': {}, 'process_info': None}

    def create_menu_ui(self, preserve_styles=False):
        if not self.selected_file_configs:
            if not self.is_generated_menu: messagebox.showinfo("No Files", "No files selected.")
            return

        if self.menu_frame: self.menu_frame.destroy()
        for widget in self.menu_display_area.winfo_children(): widget.destroy()

        if not preserve_styles: self._update_title_label_style(update_root_bg=True)

        canvas = tk.Canvas(self.menu_display_area, bg=self.current_root_bg, highlightthickness=0)
        scrollbar = tk.Scrollbar(self.menu_display_area, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=self.current_root_bg)
        
        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        def _on_mousewheel(event): canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        def _on_scroll_up(event): canvas.yview_scroll(-1, "units")
        def _on_scroll_down(event): canvas.yview_scroll(1, "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        canvas.bind_all("<Button-4>", _on_scroll_up)   # Linux scroll up
        canvas.bind_all("<Button-5>", _on_scroll_down) # Linux scroll down

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        cols = self.num_columns.get()
        uniform_style = self._generate_style_dict() if self.style_mode_var.get() == 'uniform' else None
        
        def create_hover_effect(button, original_relief, hover_relief):
            button.bind("<Enter>", lambda e: button.config(relief=hover_relief))
            button.bind("<Leave>", lambda e: button.config(relief=original_relief))

        for i, config in enumerate(self.selected_file_configs):
            saved_text = config['style'].get('text')
            if not preserve_styles or not config.get('style') or not config['style'].get('bg'):
                new_style = uniform_style.copy() if uniform_style else self._generate_style_dict()
                if saved_text: new_style['text'] = saved_text
                config['style'] = new_style
            
            item_style = config['style']
            row, col = divmod(i, cols)
            item_f = tk.Frame(scrollable_frame, bg=scrollable_frame.cget("bg"))
            item_f.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")
            scrollable_frame.grid_columnconfigure(col, weight=1)

            tk.Checkbutton(item_f, variable=config['var'], bg=item_f.cget("bg")).pack(side=tk.LEFT)
            btn_text = item_style.get('text', os.path.basename(config['path']))
            btn_text_short = btn_text[:25] + '...' if len(btn_text) > 28 else btn_text

            try:
                font_obj = font.Font(family=item_style['font_family'], size=item_style['font_size'])
                btn_config = {k:v for k,v in item_style.items() if k not in ['font_family', 'font_size', 'text']}
                btn = tk.Button(item_f, text=btn_text_short, command=lambda p=config['path']: self.launch_file(p),
                               font=font_obj, width=20, anchor='w', **btn_config)
                btn.pack(side=tk.LEFT, fill=tk.X, expand=True)
                btn.bind("<Button-3>", lambda e, c=config: self._show_context_menu(e, c))
                create_hover_effect(btn, item_style['relief'], tk.SUNKEN)
            except tk.TclError:
                btn = tk.Button(item_f, text=btn_text_short, command=lambda p=config['path']: self.launch_file(p), width=20)
                btn.pack(side=tk.LEFT, fill=tk.X, expand=True)
                btn.bind("<Button-3>", lambda e, c=config: self._show_context_menu(e, c))

    def _generate_style_dict(self):
        style = {
            'bg': self._get_random_color(), 'font_family': random.choice(WHIMSICAL_FONTS),
            'font_size': random.randint(10, 14), 'relief': random.choice(RELIEF_STYLES),
            'borderwidth': random.randint(2, 4), 'padx': 8, 'pady': 5,
        }
        style['fg'] = self._get_contrasting_color(style['bg'])
        style['activebackground'] = self._get_random_color(avoid=style['bg'])
        style['activeforeground'] = self._get_contrasting_color(style['activebackground'])
        return style

    def launch_file(self, filepath, is_part_of_sequence=False):
        if self.single_view_mode_var.get() or is_part_of_sequence:
            self._terminate_all_managed_processes()

        abs_path = os.path.abspath(filepath)
        current_config = self._get_config_by_path(abs_path)
        _, ext = os.path.splitext(filepath); ext = ext.lower()
        print(f"Launching: {abs_path}")
        try:
            if ext == '.py':
                popen_obj = subprocess.Popen([sys.executable, abs_path])
                if current_config: current_config['process_info'] = {'type': 'popen', 'instance': popen_obj}
            elif ext in ['.html', '.htm']:
                if self.use_selenium_var.get() and SELENIUM_AVAILABLE:
                    self._launch_selenium_html_in_thread(abs_path)
                else:
                    webbrowser.open(f'file:///{abs_path}')
            else:
                if sys.platform == "win32": os.startfile(abs_path)
                elif sys.platform == "darwin": subprocess.Popen(['open', abs_path])
                else: subprocess.Popen(['xdg-open', abs_path])
        except Exception as e:
            messagebox.showerror("Launch Error", f"Could not open file: {os.path.basename(filepath)}\nError: {e}", parent=self.root)

    def _launch_selenium_html_in_thread(self, filepath):
        if self.active_selenium_driver:
            self._terminate_all_managed_processes()
            time.sleep(0.5)
        def task():
            try:
                chrome_options = ChromeOptions()
                try:
                    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
                    chrome_options.add_experimental_option('useAutomationExtension', False)
                except Exception:
                    print("Could not set experimental options to hide automation bar.")

                if self.html_fullscreen_var.get():
                    chrome_options.add_argument("--start-fullscreen")
                    chrome_options.add_argument("--kiosk")
                
                self.active_selenium_driver = webdriver.Chrome(options=chrome_options)
                self.active_selenium_driver.get(f"file:///{filepath}")
                
                while self.active_selenium_driver and self.active_selenium_driver.window_handles:
                    time.sleep(0.5)
            except Exception as e:
                print(f"Selenium thread error: {e}")
            finally:
                if self.active_selenium_driver:
                    try: self.active_selenium_driver.quit()
                    except: pass
                self.active_selenium_driver = None
        threading.Thread(target=task, daemon=True).start()

    def toggle_run_sequence(self):
        if self.is_running_sequence:
            self.is_running_sequence = False
            self.run_selected_button.config(text="🚀 Run Selected")
            self.root.after(100, self._terminate_all_managed_processes)
            messagebox.showinfo("Stopped", "Sequence has been stopped.", parent=self.root)
            return

        selected_to_run = [c for c in self.selected_file_configs if c['var'].get()]
        if not selected_to_run:
            messagebox.showwarning("Nothing Selected", "Check the boxes next to files to run in a sequence.", parent=self.root)
            return
            
        try:
            delay = float(self.duration_entry.get())
            if delay < 0: delay = 0
        except ValueError:
            messagebox.showerror("Invalid Delay", "Please enter a valid number for the delay.", parent=self.root)
            return
            
        self.is_running_sequence = True
        self.current_sequence_configs = selected_to_run[:]
        self.run_selected_button.config(text="🛑 Stop Sequence")
        self._start_launch_sequence(self.current_sequence_configs, self.run_order_var.get(), self.loop_behavior_var.get() == "loop", delay)

    def _start_launch_sequence(self, configs_to_run, order, loop, delay):
        mutable_list = list(configs_to_run)
        def _recursive_launch(index=0):
            if not self.is_running_sequence:
                if self.root.winfo_exists(): self.run_selected_button.config(text="🚀 Run Selected")
                return
            
            if order == "random" and index == 0: random.shuffle(mutable_list)
            
            actual_index = index % len(mutable_list)
            config_to_run = mutable_list[actual_index]
            self.launch_file(config_to_run['path'], is_part_of_sequence=True)

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
            driver = self.active_selenium_driver
            self.active_selenium_driver = None
            threading.Thread(target=driver.quit, daemon=True).start()
        for config in self.selected_file_configs:
            if config.get('process_info'):
                proc = config['process_info'].get('instance')
                if proc and proc.poll() is None:
                    proc.terminate()
                config['process_info'] = None

    def _on_closing(self):
        self._terminate_all_managed_processes()
        if self.root.winfo_exists(): self.root.destroy()
        
    def _show_context_menu(self, event, config):
        context_menu = tk.Menu(self.root, tearoff=0)
        context_menu.add_command(label="Edit Button Text", command=lambda: self._edit_button_text(config))
        context_menu.add_command(label="Remove From Menu", command=lambda: self._remove_item(config))
        context_menu.tk_popup(event.x_root, event.y_root)

    def _edit_button_text(self, config):
        old_text = config['style'].get('text', os.path.basename(config['path']))
        new_text = simpledialog.askstring("Edit Text", "Enter new button text:", initialvalue=old_text, parent=self.root)
        if new_text:
            config['style']['text'] = new_text
            self.create_menu_ui(preserve_styles=True)

    def _remove_item(self, config_to_remove):
        self.selected_file_configs.remove(config_to_remove)
        self.create_menu_ui(preserve_styles=True)

    def toggle_all_checkboxes(self, state=True):
        for config in self.selected_file_configs: config['var'].set(state)
        
    def _update_title_label_style(self, update_root_bg=False):
        if update_root_bg:
            self.current_root_bg = self._get_random_color(light_bias=True, avoid=self.current_root_bg)
            self.root.configure(bg=self.current_root_bg)
        bg = self._get_random_color()
        try:
            self.title_label.config(font=(random.choice(WHIMSICAL_FONTS), 24, "bold"), bg=bg, fg=self._get_contrasting_color(bg))
        except tk.TclError:
            self.title_label.config(font=("Arial", 24, "bold"), bg=bg, fg=self._get_contrasting_color(bg))

    def _get_random_color(self, light_bias=False, avoid=None):
        color = random.choice(WHIMSICAL_COLORS)
        while color == avoid: color = random.choice(WHIMSICAL_COLORS)
        return color

    def _get_contrasting_color(self, bg_color_hex):
        try:
            r,g,b=int(bg_color_hex[1:3],16),int(bg_color_hex[3:5],16),int(bg_color_hex[5:7],16)
            return "#000000" if (0.299*r+0.587*g+0.114*b)>128 else "#FFFFFF"
        except: return "#000000"

    def load_menu_from_script(self):
        py_filename = filedialog.askopenfilename(title="Load Menu Script", filetypes=[("Python Menu Script", "*.py")], parent=self.root)
        if not py_filename: return
        try:
            with open(py_filename, 'r', encoding='utf-8') as f: source_code = f.read()
            tree = ast.parse(source_code)
            main_block = next((node for node in tree.body if isinstance(node, ast.If) and isinstance(node.test, ast.Compare) and node.test.comparators[0].s == '__main__'), None)
            if not main_block: raise ValueError("Could not find __main__ block.")
            
            loaded_title = ast.literal_eval(next(n.value for n in main_block.body if isinstance(n, ast.Assign) and n.targets[0].id == 'SAVED_MENU_TITLE_STR'))
            loaded_configs = ast.literal_eval(next(n.value for n in main_block.body if isinstance(n, ast.Assign) and n.targets[0].id == 'SAVED_FILE_CONFIGS_DATA'))
            loaded_bg = ast.literal_eval(next(n.value for n in main_block.body if isinstance(n, ast.Assign) and n.targets[0].id == 'INITIAL_ROOT_BG_STR'))
            loaded_settings = ast.literal_eval(next(n.value for n in main_block.body if isinstance(n, ast.Assign) and n.targets[0].id == 'SAVED_APP_SETTINGS'))

            self.current_menu_title = loaded_title; self.root.title(loaded_title); self.title_label.config(text=loaded_title)
            self.current_root_bg = loaded_bg; self.root.config(bg=loaded_bg)
            
            for key, var in vars(self).items():
                if isinstance(var, (tk.IntVar, tk.StringVar, tk.BooleanVar)):
                    setting_key = key.replace('_var', '')
                    if setting_key in loaded_settings: var.set(loaded_settings[setting_key])
            
            self.selected_file_configs = [{'path': c['path'], 'var': tk.BooleanVar(value=False), 'style': c['style'].copy(),'process_info': None} for c in loaded_configs]
            self.create_menu_ui(preserve_styles=True)
            messagebox.showinfo("Load Success", "Menu loaded successfully.", parent=self.root)
        except Exception as e:
            messagebox.showerror("Load Error", f"Failed to parse menu script.\nError: {e}", parent=self.root)

    def prompt_and_save_menu(self):
        if not self.selected_file_configs: messagebox.showerror("No Menu","No menu to save.",parent=self.root); return
        title = simpledialog.askstring("Menu Title","Enter a title for your menu:", initialvalue=self.current_menu_title, parent=self.root)
        if not title: return
        py_filename = filedialog.asksaveasfilename(defaultextension=".py", filetypes=[("Python Menu Script", "*.py")], parent=self.root)
        if not py_filename: return
        
        configs = [{'path': c['path'], 'style': c['style']} for c in self.selected_file_configs]
        settings = {key.replace('_var',''): var.get() for key, var in vars(self).items() if isinstance(var, (tk.IntVar, tk.StringVar, tk.BooleanVar))}
        
        script_content = self._generate_menu_script_content(title, configs, self.current_root_bg, settings)
        try:
            with open(py_filename, "w", encoding="utf-8") as f: f.write(script_content)
            messagebox.showinfo("Menu Saved", f"Menu script saved as:\n{py_filename}", parent=self.root)
        except Exception as e: messagebox.showerror("Save Error", f"Could not save menu script:\n{e}", parent=self.root)

    def _generate_menu_script_content(self, title, configs, bg, settings):
        class_source = inspect.getsource(WhimsicalFileLauncherApp)
        return f"""# Generated Menu Script. To edit, use "Load Menu" in the creator.
import tkinter as tk; from tkinter import filedialog, messagebox, simpledialog, font
import os, subprocess, webbrowser, random, time, sys, threading, ast
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
WHIMSICAL_COLORS = {repr(WHIMSICAL_COLORS)}
WHIMSICAL_FONTS = {repr(WHIMSICAL_FONTS)}
RELIEF_STYLES = {repr(RELIEF_STYLES)}
DEFAULT_NUM_COLUMNS = {DEFAULT_NUM_COLUMNS}
{class_source}
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
    import inspect
    main_creator_root = tk.Tk()
    creator_app = WhimsicalFileLauncherApp(main_creator_root)
    main_creator_root.mainloop()