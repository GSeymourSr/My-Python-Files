import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import os
import subprocess
import webbrowser
import random
import time
import sys
import threading # For Selenium in a new thread
import ast # For safely evaluating literals from saved files later

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options as ChromeOptions # Alias for clarity
    # from selenium.webdriver.common.keys import Keys # For emulating key presses if needed
    # from selenium.webdriver.common.action_chains import ActionChains # If needed for complex interactions
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

# --- Constants ---
WHIMSICAL_COLORS = [
    "#FFADAD", "#FFD6A5", "#FDFFB6", "#CAFFBF", "#9BF6FF", "#A0C4FF", "#BDB2FF", "#FFC6FF",
    "#FFB3BA", "#FFDFBA", "#FFFFBA", "#BAFFC9", "#BAE1FF", "#E0BBE4", "#FEC8D8", "#FFDFD3",
    "#D16BA5", "#86A8E7", "#5FFBF1", "#A267AC", "#F67280", "#C06C84", "#6C5B7B", "#355C7D"
]
WHIMSICAL_FONTS = [
    "Comic Sans MS", "Papyrus", "Curlz MT", "Kristen ITC",
    "Arial", "Verdana", "Helvetica" # Fallbacks
]
RELIEF_STYLES = [tk.RAISED, tk.SUNKEN, tk.GROOVE, tk.RIDGE, tk.FLAT]
NUM_COLUMNS = 3
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
        self.root.resizable(True, True)

        self.current_root_bg = initial_root_bg if initial_root_bg else self._get_random_color(light_bias=True)
        self.root.configure(bg=self.current_root_bg)

        self.selected_file_configs = []
        if is_generated_menu and initial_configs:
            for config_data in initial_configs:
                self.selected_file_configs.append({
                    'path': config_data['path'],
                    'var': tk.BooleanVar(value=False),
                    'style': config_data['style'].copy(),
                    'process_info': None
                })

        self.menu_frame = None
        self.scrollable_frame_in_canvas = None
        self.active_selenium_driver = None
        self.active_selenium_filepath = None
        self.is_running_sequence = False
        self.current_sequence_configs = [] # Stores configs for the currently running sequence

        # --- UI Variables for new features ---
        self.use_selenium_var = tk.BooleanVar(value=SELENIUM_AVAILABLE)
        self.html_fullscreen_var = tk.BooleanVar(value=True)

        if initial_settings: # For generated menus
            self.use_selenium_var.set(initial_settings.get('use_selenium', SELENIUM_AVAILABLE))
            self.html_fullscreen_var.set(initial_settings.get('html_fullscreen', True))


        # --- GUI Setup ---
        self.title_label_frame = tk.Frame(self.root, bg=self.current_root_bg)
        self.title_label_frame.pack(pady=(10 if is_generated_menu else 0), fill=tk.X)
        
        title_bg_color = self._get_random_color() 
        self.title_label = tk.Label(self.title_label_frame, text=self.current_menu_title,
                                    font=(random.choice(WHIMSICAL_FONTS), 20, "bold"),
                                    bg=title_bg_color, 
                                    fg=self._get_contrasting_color(title_bg_color))
        
        if is_generated_menu : self.title_label.pack(pady=5, padx=20)
        self._update_title_label_style()

        control_frame_bg = self._get_random_color(light_bias=True, avoid=self.current_root_bg)
        top_control_frame = tk.Frame(self.root, bg=control_frame_bg); top_control_frame.pack(pady=5, padx=10, fill=tk.X)
        left_controls = tk.Frame(top_control_frame, bg=control_frame_bg); left_controls.pack(side=tk.LEFT, padx=5)
        
        if not self.is_generated_menu:
            self.select_button = tk.Button(left_controls, text="🌟 Select Files 🌟", command=self.select_files_and_create_menu, font=(random.choice(WHIMSICAL_FONTS), 13, "bold"), bg=self._get_random_color(), fg=self._get_contrasting_color(left_controls.cget("bg")), padx=8, pady=5, relief=random.choice(RELIEF_STYLES), borderwidth=random.randint(2, 3)); self.select_button.pack(side=tk.LEFT, pady=2)
        
        self.regenerate_button = tk.Button(left_controls, text="🎨 Re-Enchant Menu 🎨", command=lambda: self.create_menu_ui(preserve_styles=False), font=(random.choice(WHIMSICAL_FONTS), 13, "bold"), bg=self._get_random_color(), fg=self._get_contrasting_color(left_controls.cget("bg")), padx=8, pady=5, relief=random.choice(RELIEF_STYLES), borderwidth=random.randint(2, 3)); self.regenerate_button.pack(side=tk.LEFT, padx=(0 if self.is_generated_menu else 5, 0), pady=2)
        
        center_controls = tk.Frame(top_control_frame, bg=control_frame_bg); center_controls.pack(side=tk.LEFT, expand=True, fill=tk.X)
        
        # Multi-run options
        multi_run_options_frame = tk.Frame(center_controls, bg=control_frame_bg); multi_run_options_frame.pack(pady=2)
        tk.Label(multi_run_options_frame, text="Delay(s):", bg=control_frame_bg, fg=self._get_contrasting_color(control_frame_bg), font=("Arial",9)).grid(row=0, column=0, padx=(0,2))
        self.duration_entry = tk.Entry(multi_run_options_frame, width=4, font=("Arial", 9)); self.duration_entry.insert(0, "1"); self.duration_entry.grid(row=0, column=1, padx=(0,5))
        self.run_order_var = tk.StringVar(value="order")
        tk.Radiobutton(multi_run_options_frame, text="In Order", variable=self.run_order_var, value="order", bg=control_frame_bg, fg=self._get_contrasting_color(control_frame_bg), selectcolor=self._get_random_color(light_bias=True), font=("Arial",9)).grid(row=0, column=2)
        tk.Radiobutton(multi_run_options_frame, text="Random", variable=self.run_order_var, value="random", bg=control_frame_bg, fg=self._get_contrasting_color(control_frame_bg), selectcolor=self._get_random_color(light_bias=True), font=("Arial",9)).grid(row=0, column=3, padx=(0,5))
        self.loop_behavior_var = tk.StringVar(value="once")
        tk.Radiobutton(multi_run_options_frame, text="Run Once", variable=self.loop_behavior_var, value="once", bg=control_frame_bg, fg=self._get_contrasting_color(control_frame_bg), selectcolor=self._get_random_color(light_bias=True), font=("Arial",9)).grid(row=0, column=4)
        tk.Radiobutton(multi_run_options_frame, text="Loop", variable=self.loop_behavior_var, value="loop", bg=control_frame_bg, fg=self._get_contrasting_color(control_frame_bg), selectcolor=self._get_random_color(light_bias=True), font=("Arial",9)).grid(row=0, column=5, padx=(0,5))
        
        self.run_selected_button = tk.Button(multi_run_options_frame, text="🚀 Run Selected", command=self.toggle_run_sequence, font=(random.choice(WHIMSICAL_FONTS), 11, "bold"), bg=self._get_random_color(), fg=self._get_contrasting_color(multi_run_options_frame.cget("bg")), padx=6, pady=3, relief=random.choice(RELIEF_STYLES), borderwidth=random.randint(2,3))
        self.run_selected_button.grid(row=0, column=6, padx=(5,0))

        # Selenium options below multi-run
        selenium_options_frame = tk.Frame(center_controls, bg=control_frame_bg); selenium_options_frame.pack(pady=2)
        self.use_selenium_cb = tk.Checkbutton(selenium_options_frame, text="Use Selenium for HTML", variable=self.use_selenium_var,
                                 bg=control_frame_bg, fg=self._get_contrasting_color(control_frame_bg),
                                 selectcolor=self._get_random_color(light_bias=True), font=("Arial",9),
                                 command=self._update_selenium_options_availability)
        self.use_selenium_cb.pack(side=tk.LEFT, padx=(0,5))
        if not SELENIUM_AVAILABLE: self.use_selenium_cb.config(state=tk.DISABLED)

        self.html_fullscreen_cb = tk.Checkbutton(selenium_options_frame, text="Kiosk HTML (Fullscreen)", variable=self.html_fullscreen_var,
                                   bg=control_frame_bg, fg=self._get_contrasting_color(control_frame_bg),
                                   selectcolor=self._get_random_color(light_bias=True), font=("Arial",9))
        self.html_fullscreen_cb.pack(side=tk.LEFT)
        self._update_selenium_options_availability() # Set initial state

        right_controls = tk.Frame(top_control_frame, bg=control_frame_bg); right_controls.pack(side=tk.RIGHT, padx=5)
        tk.Button(right_controls, text="Select All", command=lambda: self.toggle_all_checkboxes(True), font=("Arial",9,"bold"), bg="#AEDFF7", fg="black", padx=4, pady=1).pack(side=tk.LEFT, padx=2, pady=2)
        tk.Button(right_controls, text="Select None", command=lambda: self.toggle_all_checkboxes(False), font=("Arial",9,"bold"), bg="#FFC0CB", fg="black", padx=4, pady=1).pack(side=tk.LEFT, padx=2, pady=2)
        
        if not self.is_generated_menu:
            save_button = tk.Button(right_controls, text="💾 Save Menu", command=self.prompt_and_save_menu, font=(random.choice(WHIMSICAL_FONTS), 13, "bold"), bg="#77DD77", fg="#000000", padx=8, pady=5, relief=tk.RAISED, borderwidth=3); save_button.pack(side=tk.LEFT, padx=(5,0), pady=2)
        
        self.menu_display_area = tk.Frame(self.root, bg=self.current_root_bg); self.menu_display_area.pack(expand=True, fill=tk.BOTH, padx=5, pady=5)
        # --- End GUI Setup ---
        
        if self.is_generated_menu:
            self.create_menu_ui(preserve_styles=True)

        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)

        if not SELENIUM_AVAILABLE and not is_generated_menu: # Show warning only once for creator
            print("WARNING: Selenium library not found or failed to import.")
            print("HTML files will be opened using the default web browser instead of kiosk/custom window mode.")
            print("For enhanced HTML slideshows, please install Selenium and ChromeDriver:")
            print("  pip install selenium")
            print("  Ensure ChromeDriver matching your Chrome version is in your system PATH.")
    
    def _update_selenium_options_availability(self):
        if SELENIUM_AVAILABLE and self.use_selenium_var.get():
            self.html_fullscreen_cb.config(state=tk.NORMAL)
        else:
            self.html_fullscreen_cb.config(state=tk.DISABLED)

    def _on_closing(self):
        print("Closing application...")
        if self.is_running_sequence:
            self.is_running_sequence = False # Signal sequence to stop
            self.root.after(100, self._perform_sequence_cleanup_and_destroy) # Delay cleanup slightly
        else:
            self._perform_sequence_cleanup_and_destroy()

    def _perform_sequence_cleanup_and_destroy(self):
        print("Performing final cleanup before exit...")
        # Terminate all Popen processes
        for config in self.selected_file_configs:
            if config.get('process_info') and config['process_info']['type'] == 'popen':
                self._terminate_process_info(config['path'])
        
        self._terminate_selenium_driver_global() # Terminate Selenium if active
        
        if self.root.winfo_exists():
            self.root.destroy()

    def _update_title_label_style(self):
        if hasattr(self, 'title_label') and self.title_label.winfo_exists():
            bg_color = self._get_random_color()
            fg_color = self._get_contrasting_color(bg_color)
            font_family = random.choice(WHIMSICAL_FONTS)
            font_size = random.randint(18, 24) if self.is_generated_menu else random.randint(16, 20)
            try:
                self.title_label.config(text=self.current_menu_title,font=(font_family, font_size, "bold"),bg=bg_color, fg=fg_color)
            except tk.TclError: # Fallback font
                self.title_label.config(text=self.current_menu_title,font=("Arial", font_size, "bold"),bg=bg_color, fg=fg_color)
        
        if not hasattr(self, '_initial_bg_set_flag'):
            self.current_root_bg = self._get_random_color(light_bias=True)
            self.root.configure(bg=self.current_root_bg)
        else:
            del self._initial_bg_set_flag 

        if hasattr(self, 'menu_display_area') and self.menu_display_area.winfo_exists():
            self.menu_display_area.configure(bg=self.current_root_bg)
        if hasattr(self, 'title_label_frame') and self.title_label_frame.winfo_exists():
            self.title_label_frame.configure(bg=self.current_root_bg)
        
        if not hasattr(self, '_initial_bg_set_flag_for_update_call'):
             self._initial_bg_set_flag_for_update_call = True

    def _get_random_color(self, light_bias=False, avoid=None):
        # (This method remains the same as in your provided code)
        color = random.choice(WHIMSICAL_COLORS)
        if avoid:
            while color == avoid:
                color = random.choice(WHIMSICAL_COLORS)
        if light_bias:
            try:
                r, g, b = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)
            except ValueError: return color
            if (r + g + b) / 3 < 128:
                for _ in range(3): 
                    nc = random.choice(WHIMSICAL_COLORS)
                    if avoid and nc == avoid: continue
                    try:
                        nr, ng, nb = int(nc[1:3], 16), int(nc[3:5], 16), int(nc[5:7], 16)
                    except ValueError: continue
                    if (nr + ng + nb) / 3 >= 128: return nc
        return color

    def _get_contrasting_color(self, bg_color_hex):
        # (This method remains the same)
        try:
            r,g,b=int(bg_color_hex[1:3],16),int(bg_color_hex[3:5],16),int(bg_color_hex[5:7],16)
            return"#000000"if(0.299*r+0.587*g+0.114*b)>128 else"#FFFFFF"
        except (ValueError, TypeError): return random.choice(["#000000","#FFFFFF"])

    def select_files_and_create_menu(self):
        # (This method remains largely the same, ensure _initial_bg_set_flag logic is sound)
        files=filedialog.askopenfilenames(title="Select your magical files",filetypes=(("All files","*.*"),("Python files","*.py"),("HTML files","*.html;*.htm"),("Image files","*.png;*.jpg;*.jpeg;*.gif;*.bmp;*.svg;*.webp"),("Audio files","*.mp3;*.wav;*.ogg;*.m4a"),("Video files","*.mp4;*.avi;*.mkv;*.mov"),("Text/Docs","*.txt;*.md;*.pdf;*.doc;*.docx")))
        if files:
            self.selected_file_configs=[] # Clears existing if re-selecting all
            for f_path in files:self.selected_file_configs.append({'path':os.path.abspath(f_path),'var':tk.BooleanVar(value=False),'style':{},'process_info':None})
            self._initial_bg_set_flag = True 
            self.create_menu_ui()
        elif not self.selected_file_configs:
            if self.menu_frame:self.menu_frame.destroy();self.menu_frame=None
            for widget in self.menu_display_area.winfo_children():widget.destroy()
            no_files_label_fg = self._get_contrasting_color(self.menu_display_area.cget("bg"))
            no_files_label=tk.Label(self.menu_display_area,text="No files selected. The magic awaits!",font=("Comic Sans MS",18),bg=self.menu_display_area.cget("bg"),fg=no_files_label_fg)
            no_files_label.pack(expand=True)
            self.root.after(3000,lambda:no_files_label.destroy() if no_files_label.winfo_exists() else None)


    def create_menu_ui(self, preserve_styles=False):
        # (This method remains largely the same, font fallback for button text is good)
        if not self.selected_file_configs:
            if not self.is_generated_menu:messagebox.showinfo("No Files","No files selected to create a menu.")
            return
        if self.menu_frame:self.menu_frame.destroy()
        for widget in self.menu_display_area.winfo_children():widget.destroy()
        
        if not preserve_styles:
            if not hasattr(self, '_initial_bg_set_flag_for_update_call'):
                 self._update_title_label_style()
            elif hasattr(self, '_initial_bg_set_flag_for_update_call'):
                 del self._initial_bg_set_flag_for_update_call 

        menu_frame_bg=self._get_random_color(light_bias=True,avoid=self.current_root_bg)
        self.menu_frame=tk.Frame(self.menu_display_area,bg=menu_frame_bg)
        self.menu_frame.pack(expand=True,fill=tk.BOTH,padx=5,pady=5)
        
        canvas_bg=self._get_random_color(light_bias=True,avoid=menu_frame_bg)
        canvas=tk.Canvas(self.menu_frame,bg=canvas_bg,highlightthickness=0)
        scrollbar=tk.Scrollbar(self.menu_frame,orient="vertical",command=canvas.yview)
        self.scrollable_frame_in_canvas=tk.Frame(canvas,bg=canvas_bg)
        
        self.scrollable_frame_in_canvas.bind("<Configure>",lambda e:canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0,0),window=self.scrollable_frame_in_canvas,anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        def _on_mw(e):canvas.yview_scroll(int(-1*(e.delta/120)),"units")
        def _on_mw_l(e):canvas.yview_scroll(-1 if e.num==4 else 1,"units")
        canvas.bind_all("<MouseWheel>",_on_mw)
        canvas.bind_all("<Button-4>",_on_mw_l)
        canvas.bind_all("<Button-5>",_on_mw_l)
        
        canvas.pack(side="left",fill="both",expand=True,padx=5,pady=5)
        scrollbar.pack(side="right",fill="y")
        
        self.scrollable_frame_in_canvas.grid_columnconfigure(0,weight=1);
        for i in range(NUM_COLUMNS):self.scrollable_frame_in_canvas.grid_columnconfigure(i+1,weight=1)
        self.scrollable_frame_in_canvas.grid_columnconfigure(NUM_COLUMNS+1,weight=1)
        
        row=0
        for i,config in enumerate(self.selected_file_configs):
            filepath=config['path']
            filename=os.path.basename(filepath)
            if not preserve_styles or not config.get('style') or not config['style'].get('bg'):
                style={'bg':self._get_random_color(),
                       'font_family':random.choice(WHIMSICAL_FONTS),
                       'font_size':random.randint(10,14),
                       'relief':random.choice(RELIEF_STYLES),
                       'borderwidth':random.randint(1,3),
                       'padx':random.randint(6,10),
                       'pady':random.randint(3,6),
                       'text':filename}
                style['fg']=self._get_contrasting_color(style['bg'])
                style['activebackground']=self._get_random_color(avoid=style['bg'])
                style['activeforeground']=self._get_contrasting_color(style['activebackground'])
                config['style']=style
            
            item_style=config['style']
            actual_col=(i%NUM_COLUMNS)+1
            if i%NUM_COLUMNS==0 and i!=0: row+=1
            
            item_f=tk.Frame(self.scrollable_frame_in_canvas,bg=self.scrollable_frame_in_canvas.cget("bg"))
            item_f.grid(row=row,column=actual_col,padx=3,pady=3,sticky="ew")
            
            tk.Checkbutton(item_f,variable=config['var'],bg=item_f.cget("bg"),activebackground=item_f.cget("bg")).pack(side=tk.LEFT,padx=(0,1))
            
            btn_txt=item_style['text']
            btn_txt=btn_txt[:9]+"..."+btn_txt[-9:] if len(btn_txt)>20 else btn_txt
            try:
                btn = tk.Button(item_f,text=btn_txt,command=lambda p=filepath:self.launch_file(p),
                               bg=item_style['bg'],fg=item_style['fg'],
                               font=(item_style['font_family'],item_style['font_size']),
                               relief=item_style['relief'],borderwidth=item_style['borderwidth'],
                               padx=item_style['padx'],pady=item_style['pady'],
                               activebackground=item_style['activebackground'],
                               activeforeground=item_style['activeforeground'],width=12)
                btn.pack(side=tk.LEFT,fill=tk.X,expand=True)
            except tk.TclError: 
                 tk.Button(item_f,text=btn_txt,command=lambda p=filepath:self.launch_file(p),
                           bg=item_style['bg'],fg=item_style['fg'],font=("Arial",10),width=12).pack(side=tk.LEFT,fill=tk.X,expand=True)
        
        self.root.after(50,lambda:canvas.create_window((canvas.winfo_width()//2,0),window=self.scrollable_frame_in_canvas,anchor="n") if canvas.winfo_exists() else None)


    def _get_config_by_path(self, filepath):
        for config in self.selected_file_configs:
            if config['path'] == filepath:
                return config
        return None

    def _launch_selenium_html_in_thread(self, filepath_to_load):
        if not SELENIUM_AVAILABLE or not self.use_selenium_var.get():
            webbrowser.open(f'file:///{filepath_to_load}')
            config = self._get_config_by_path(filepath_to_load)
            if config: config['process_info'] = None
            return

        target_config = self._get_config_by_path(filepath_to_load)

        def task():
            nonlocal target_config
            driver_instance = None
            try:
                if self.active_selenium_driver and self.active_selenium_filepath != filepath_to_load:
                    print(f"Closing previous Selenium instance for {self.active_selenium_filepath}")
                    self._terminate_selenium_driver_global()

                if not self.active_selenium_driver:
                    print(f"Creating new Selenium driver for {filepath_to_load}")
                    chrome_options = ChromeOptions()
                    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"]) # Hide "Chrome is controlled" bar
                    
                    if self.html_fullscreen_var.get():
                        chrome_options.add_argument("--start-fullscreen")
                        chrome_options.add_argument("--kiosk")
                    # else: regular window, no specific options needed unless size is desired

                    try:
                        driver_instance = webdriver.Chrome(options=chrome_options)
                        self.active_selenium_driver = driver_instance
                        self.active_selenium_filepath = filepath_to_load
                        if target_config:
                            target_config['process_info'] = {'type': 'selenium', 'instance': driver_instance}
                    except Exception as e:
                        self.root.after(0, lambda: messagebox.showerror("Selenium Error",
                            f"Could not start Chrome WebDriver for HTML.\n"
                            f"Ensure ChromeDriver is installed and in PATH, and matches Chrome version.\n"
                            f"Error: {e}", parent=self.root))
                        print(f"Error creating WebDriver: {e}")
                        self.root.after(0, lambda: webbrowser.open(f'file:///{filepath_to_load}'))
                        if target_config: target_config['process_info'] = None
                        self.active_selenium_driver = None
                        self.active_selenium_filepath = None
                        return

                print(f"Selenium loading: file:///{filepath_to_load}")
                self.active_selenium_driver.get(f"file:///{filepath_to_load}")
                self.active_selenium_filepath = filepath_to_load

                try:
                    _ = self.active_selenium_driver.window_handles
                except Exception: 
                    print("Selenium window closed during/after load.")
                    self._terminate_selenium_driver_global()

            except Exception as e:
                print(f"Error in Selenium task for {filepath_to_load}: {e}")
                if driver_instance:
                    try: driver_instance.quit()
                    except: pass
                if self.active_selenium_driver and (not driver_instance or driver_instance == self.active_selenium_driver):
                    self._terminate_selenium_driver_global()
                if target_config: target_config['process_info'] = None
        
        threading.Thread(target=task, daemon=True).start()

    def launch_file(self, filepath, is_part_of_sequence=False):
        _, ext = os.path.splitext(filepath); ext = ext.lower()
        abs_path = os.path.abspath(filepath)
        current_config = self._get_config_by_path(abs_path)

        if is_part_of_sequence:
            for config_item in self.selected_file_configs:
                if config_item['path'] != abs_path and \
                   config_item.get('process_info') and \
                   config_item['process_info']['type'] == 'popen':
                    self._terminate_process_info(config_item['path'])
            
            # If current file is not HTML and Selenium is active (and fullscreen), close Selenium
            if not (ext in ['.html', '.htm']) and self.active_selenium_driver and self.html_fullscreen_var.get():
                print(f"Sequence: Current file '{os.path.basename(abs_path)}' is not HTML. Closing active KIOSK Selenium driver.")
                self._terminate_selenium_driver_global()
            # If current file is HTML, and we are in windowed mode, and a *different* HTML was open,
            # the _launch_selenium_html_in_thread will handle closing the old one.

        print(f"Launching: {abs_path} (ext: {ext})")
        try:
            if ext == '.py':
                py_exe = sys.executable if sys.executable else "python"; popen_obj = None
                # ... (rest of .py launching logic remains same) ...
                if os.name == 'nt': popen_obj = subprocess.Popen([py_exe, abs_path], creationflags=subprocess.CREATE_NEW_CONSOLE)
                elif sys.platform == 'darwin': popen_obj = subprocess.Popen([py_exe, abs_path])
                else: 
                    try: popen_obj = subprocess.Popen(['x-terminal-emulator', '-e', py_exe, abs_path])
                    except FileNotFoundError:
                        try: popen_obj = subprocess.Popen(['gnome-terminal', '--', py_exe, abs_path])
                        except FileNotFoundError:
                            try: popen_obj = subprocess.Popen(['konsole', '-e', py_exe, abs_path])
                            except FileNotFoundError: popen_obj = subprocess.Popen([py_exe, abs_path])
                if current_config and popen_obj: current_config['process_info'] = {'type': 'popen', 'instance': popen_obj}


            elif ext in ['.html', '.htm']:
                if SELENIUM_AVAILABLE and self.use_selenium_var.get():
                    self._launch_selenium_html_in_thread(abs_path)
                else: 
                    webbrowser.open(f'file:///{abs_path}')
                    if current_config: current_config['process_info'] = None 

            # ... (rest of file type handling remains same) ...
            elif ext in ['.svg','.jpg','.jpeg','.png','.gif','.bmp','.webp','.ico','.mp3','.wav','.ogg','.aac','.flac','.m4a','.mp4','.avi','.mkv','.mov','.wmv','.flv','.pdf','.txt','.md','.log','.csv','.json','.xml','.doc','.docx','.xls','.xlsx','.ppt','.pptx','.odt','.ods','.odp']:
                if os.name == 'nt': os.startfile(abs_path)
                elif sys.platform == 'darwin': subprocess.Popen(['open', abs_path])
                else: subprocess.Popen(['xdg-open', abs_path])
                if current_config: current_config['process_info'] = None 
            else: 
                if os.name == 'nt': os.startfile(abs_path)
                elif sys.platform == 'darwin': subprocess.Popen(['open', abs_path])
                else: subprocess.Popen(['xdg-open', abs_path])
                if current_config: current_config['process_info'] = None

        except Exception as e:
            print(f"Error launching {filepath}: {e}")
            self.root.after(0, lambda: messagebox.showerror("Launch Error", f"Could not open file: {os.path.basename(filepath)}\nError: {e}", parent=self.root))
            if current_config: current_config['process_info'] = None


    def _terminate_selenium_driver_global(self):
        # (This method remains largely the same)
        if self.active_selenium_driver:
            driver_to_quit = self.active_selenium_driver
            filepath_it_was_for = self.active_selenium_filepath
            
            self.active_selenium_driver = None 
            self.active_selenium_filepath = None

            print(f"Terminating global Selenium driver (was for: {filepath_it_was_for or 'Unknown File'})")
            try:
                threading.Thread(target=driver_to_quit.quit, daemon=True).start()
            except Exception as e:
                print(f"Error initiating quit for global Selenium driver: {e}")
            
            if filepath_it_was_for:
                old_config = self._get_config_by_path(filepath_it_was_for)
                if old_config and old_config.get('process_info') and \
                   old_config['process_info'].get('instance') == driver_to_quit: 
                    old_config['process_info'] = None


    def _terminate_process_info(self, filepath_to_terminate):
        # (This method remains largely the same)
        config_to_terminate = self._get_config_by_path(filepath_to_terminate)
        if not config_to_terminate or not config_to_terminate.get('process_info'):
            return

        info = config_to_terminate['process_info']
        instance = info['instance']
        ptype = info['type']

        print(f"Attempting to terminate {ptype} for: {os.path.basename(filepath_to_terminate)}")

        if ptype == 'popen' and instance:
            try:
                if instance.poll() is None: # Check if process is still running
                    instance.terminate()
                    instance.wait(timeout=0.2) 
            except subprocess.TimeoutExpired:
                print(f"Popen (PID {instance.pid}) for {os.path.basename(filepath_to_terminate)} did not terminate, killing.")
                instance.kill()
                instance.wait(timeout=0.2)
            except Exception as e:
                print(f"Error terminating Popen process for {os.path.basename(filepath_to_terminate)}: {e}")
        elif ptype == 'selenium':
            if instance and instance == self.active_selenium_driver:
                self._terminate_selenium_driver_global()
            elif instance : 
                print(f"Warning: Terminating a Selenium instance for {os.path.basename(filepath_to_terminate)} that was not the global active one.")
                try: 
                    threading.Thread(target=instance.quit, daemon=True).start()
                except Exception as e: print(f"Error initiating quit for stray selenium instance: {e}")
        
        config_to_terminate['process_info'] = None 


    def toggle_run_sequence(self):
        if self.is_running_sequence: # If it is running, we want to stop it
            print("Stop sequence requested by user.")
            self.is_running_sequence = False # Signal to any running `_start_launch_sequence`'s recursion
            
            # Schedule cleanup of processes related to the sequence that was just stopped.
            # A small delay allows the recursive launch to see the flag and exit gracefully.
            self.root.after(100, self._perform_sequence_cleanup) 
            
            self.run_selected_button.config(text="🚀 Run Selected")
            # Message moved to _perform_sequence_cleanup to ensure it shows after actual stop actions
        else: # If it's not running, we want to start it
            selected_to_run_configs = [config for config in self.selected_file_configs if config['var'].get()]
            if not selected_to_run_configs:
                messagebox.showinfo("Nothing Selected", "Please check files to run.", parent=self.root)
                return

            try:
                delay_seconds = float(self.duration_entry.get())
                if delay_seconds < 0: delay_seconds = 0
            except ValueError:
                messagebox.showerror("Invalid Delay", "Enter a valid number for delay.", parent=self.root)
                return

            # Check if all files can be auto-closed (Python scripts or Selenium-handled HTML)
            # This check is important if there's a delay, as users expect prior item to close.
            can_all_be_auto_closed = all(
                os.path.splitext(cfg['path'])[1].lower() == '.py' or \
                (os.path.splitext(cfg['path'])[1].lower() in ['.html', '.htm'] and SELENIUM_AVAILABLE and self.use_selenium_var.get())
                for cfg in selected_to_run_configs
            )
            if delay_seconds > 0 and len(selected_to_run_configs) > 1 and not can_all_be_auto_closed:
                 if not messagebox.askyesno("Limitation",
                                           "Multi-run with delay attempts to close previous PYTHON scripts "
                                           "and HTML files (if Selenium is used and enabled).\n"
                                           "Other file types (images, docs, etc.) opened by the OS default "
                                           "application CANNOT be automatically closed by this launcher.\n\n"
                                           "Do you want to proceed?", parent=self.root):
                    return

            self.is_running_sequence = True
            self.run_selected_button.config(text="🛑 Stop Sequence")
            
            order = self.run_order_var.get()
            loop = self.loop_behavior_var.get() == "loop"
            
            self.current_sequence_configs = selected_to_run_configs[:] # Store for cleanup
            self._start_launch_sequence(self.current_sequence_configs, order, loop, delay_seconds)

    def _perform_sequence_cleanup(self):
        print("Performing sequence cleanup...")
        cleaned_popen = False
        cleaned_selenium = False

        if hasattr(self, 'current_sequence_configs') and self.current_sequence_configs:
            for config_item in self.current_sequence_configs:
                ext = os.path.splitext(config_item['path'])[1].lower()
                if ext == '.py': 
                    if config_item.get('process_info') and config_item['process_info']['type'] == 'popen':
                        print(f"Cleaning up Popen for sequenced item: {config_item['path']}")
                        self._terminate_process_info(config_item['path'])
                        cleaned_popen = True
                elif ext in ['.html', '.htm']:
                    # Selenium cleanup is handled globally if it was the active one for this sequence
                    if self.active_selenium_driver and self.active_selenium_filepath == config_item['path']:
                         print(f"Cleaning up Selenium for sequenced item: {config_item['path']}")
                         self._terminate_selenium_driver_global()
                         cleaned_selenium = True
        
        # If selenium was active but not for the last item, but an HTML was in sequence, also clean.
        if not cleaned_selenium and self.active_selenium_driver and \
           hasattr(self, 'current_sequence_configs') and \
           any(os.path.splitext(cfg['path'])[1].lower() in ['.html', '.htm'] for cfg in self.current_sequence_configs):
            print("Cleaning up active Selenium driver as HTML was part of the stopped sequence.")
            self._terminate_selenium_driver_global()
            cleaned_selenium = True
        
        if hasattr(self, 'current_sequence_configs'):
            self.current_sequence_configs = [] # Clear it after cleanup

        if not self.is_running_sequence: # Confirm sequence is indeed marked as stopped
             messagebox.showinfo("Stopped", "Multi-run sequence stopped.", parent=self.root)


    def _start_launch_sequence(self, configs_to_run, order, loop, delay_seconds):
        mutable_configs_list = list(configs_to_run) # Use a copy that can be shuffled

        def _recursive_launch(index=0):
            if not self.root.winfo_exists() or not self.is_running_sequence :
                print("Sequence stopping: Root window closed or flag is false.")
                if self.root.winfo_exists() and self.run_selected_button.winfo_exists():
                     self.run_selected_button.config(text="🚀 Run Selected")
                # The _perform_sequence_cleanup is already scheduled by toggle_run_sequence if stopped by button
                return

            if not mutable_configs_list: 
                self.is_running_sequence = False
                if self.root.winfo_exists() and self.run_selected_button.winfo_exists():
                    self.run_selected_button.config(text="🚀 Run Selected")
                return

            if order == "random" and index == 0: 
                random.shuffle(mutable_configs_list)
            
            actual_index = index % len(mutable_configs_list) 
            config_to_run = mutable_configs_list[actual_index]

            print(f"Sequence: Launching item {actual_index + 1}/{len(mutable_configs_list)}: {os.path.basename(config_to_run['path'])}")
            self.launch_file(config_to_run['path'], is_part_of_sequence=True)

            next_index = index + 1
            if next_index < len(mutable_configs_list) or loop:
                if not self.is_running_sequence: # Check flag again before scheduling next
                    print("Sequence stopping by flag before scheduling next item.")
                    if self.root.winfo_exists() and self.run_selected_button.winfo_exists():
                         self.run_selected_button.config(text="🚀 Run Selected")
                    return
                
                actual_delay_ms = int(delay_seconds * 1000) if delay_seconds > 0 else 50 
                if self.root.winfo_exists():
                    self.root.after(actual_delay_ms, lambda: _recursive_launch(next_index))
            else: # Sequence finished naturally
                self.is_running_sequence = False
                if self.root.winfo_exists() and self.run_selected_button.winfo_exists():
                    self.run_selected_button.config(text="🚀 Run Selected")
                self.current_sequence_configs = [] # Clear list of sequenced items
                print("Finished sequence naturally.")
                
                # Optionally, close the last Selenium window if it was part of sequence and kiosk
                last_ext = os.path.splitext(config_to_run['path'])[1].lower()
                if last_ext in ['.html', '.htm'] and self.active_selenium_driver and self.html_fullscreen_var.get():
                    print("Sequence finished, closing final KIOSK Selenium window.")
                    self._terminate_selenium_driver_global()
        
        if self.root.winfo_exists():
            _recursive_launch()


    def toggle_all_checkboxes(self, state=True):
        # (This method remains the same)
        for config in self.selected_file_configs:config['var'].set(state)

    def prompt_and_save_menu(self):
        # (This method remains largely the same, needs to save new settings)
        if not self.selected_file_configs:messagebox.showerror("No Menu","No menu to save.",parent=self.root);return
        new_menu_title=simpledialog.askstring("Menu Title","Enter a title for your saved menu window:",initialvalue=self.current_menu_title.replace("Creator","").strip(),parent=self.root)
        if not new_menu_title:return
        
        py_filename_suggestion="".join(c if c.isalnum()or c in('_','-')else'_'for c in new_menu_title.lower().replace(" ","_"));py_filename_suggestion=(py_filename_suggestion[:30]+".py")if py_filename_suggestion else"saved_menu.py"
        py_filename=filedialog.asksaveasfilename(title="Save Menu Script As...",initialfile=py_filename_suggestion,defaultextension=".py",filetypes=[("Python files","*.py")],parent=self.root)
        if not py_filename:return
        
        storable_configs_for_script=[{'path':c['path'],'style':c['style'].copy()}for c in self.selected_file_configs]
        app_settings_for_script = {
            'use_selenium': self.use_selenium_var.get(),
            'html_fullscreen': self.html_fullscreen_var.get()
        }

        script_content=self._generate_menu_script_content(new_menu_title,storable_configs_for_script,self.current_root_bg,NUM_COLUMNS, app_settings_for_script)
        try:
            with open(py_filename,"w",encoding="utf-8")as f:f.write(script_content)
            messagebox.showinfo("Menu Saved",f"Menu script saved as:\n{py_filename}",parent=self.root)
        except Exception as e:messagebox.showerror("Save Error",f"Could not save menu script:\n{e}",parent=self.root)

    def _generate_menu_script_content(self, menu_title_str, file_configs_with_styles, root_bg_str, num_cols_int, app_settings_dict):
        import inspect
        class_source = inspect.getsource(WhimsicalFileLauncherApp)
        
        class_source = class_source.replace("os.uname().sysname == 'Darwin'", "sys.platform == 'darwin'") # Already present

        # Ensure ast import is available in generated script if needed for parsing its own future saves (not currently used this way)
        # but good to have for consistency.
        ast_import_line = "import ast\n" if "import ast" not in class_source else ""


        selenium_imports_for_generated_script = """
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
"""
        script = f"""\
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog 
import os
import subprocess
import webbrowser
import random
import time
import sys
import threading
{ast_import_line}
# --- Selenium Imports for Generated Script ---
{selenium_imports_for_generated_script}

# --- START OF COPIED/REDEFINED CONSTANTS ---
WHIMSICAL_COLORS = {repr(WHIMSICAL_COLORS)}
WHIMSICAL_FONTS = {repr(WHIMSICAL_FONTS)}
RELIEF_STYLES = {repr(RELIEF_STYLES)}
NUM_COLUMNS = {num_cols_int}
# --- End Constants ---

# --- WhimsicalFileLauncherApp Class (Copied from original) ---
{class_source}
# --- End WhimsicalFileLauncherApp Class ---

# --- Script Entry Point for the Saved Menu ---
if __name__ == "__main__":
    SAVED_MENU_TITLE_STR = {repr(menu_title_str)}
    SAVED_FILE_CONFIGS_DATA = {repr(file_configs_with_styles)} 
    INITIAL_ROOT_BG_STR = {repr(root_bg_str)}
    SAVED_APP_SETTINGS = {repr(app_settings_dict)} # New line

    if not SELENIUM_AVAILABLE:
        print("Generated Menu Warning: Selenium library not found. HTML files will open in default browser.")
        print("For enhanced HTML viewing, please install Selenium and ChromeDriver.")

    root = tk.Tk()
    app = WhimsicalFileLauncherApp(
        root,
        is_generated_menu=True, 
        initial_configs=SAVED_FILE_CONFIGS_DATA,
        initial_title=SAVED_MENU_TITLE_STR,
        initial_root_bg=INITIAL_ROOT_BG_STR,
        initial_settings=SAVED_APP_SETTINGS # New argument
    )
    root.mainloop()
"""
        return script


# --- Main application entry point (for the creator) ---
if __name__ == "__main__":
    if sys.platform == 'darwin': # macOS specific Tkinter focus fix
        try:
            # Attempt to ensure the app comes to the foreground on macOS
            # This might involve platform-specific code or libraries if simple focus doesn't work
            # For now, we rely on Tkinter's default behavior after window creation.
            pass # os.system('''/usr/bin/osascript -e 'tell app "Finder" to set frontmost of process "Python" to true' ''') - this is too aggressive
        except Exception as e:
            print(f"macOS focus enhancement failed: {e}")

    main_creator_root = tk.Tk()
    creator_app = WhimsicalFileLauncherApp(main_creator_root)
    main_creator_root.mainloop()