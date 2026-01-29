import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import os
import subprocess
import webbrowser
import random
import time
import sys
import threading # For Selenium in a new thread

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options as ChromeOptions # Alias for clarity
    # from selenium.webdriver.common.keys import Keys # For emulating key presses if needed
    # from selenium.webdriver.common.action_chains import ActionChains # If needed for complex interactions
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    # This message will be printed when the script starts if Selenium is not found.
    # The GUI will still run, but HTML files will open in the default browser.

# --- Constants (WHIMSICAL_COLORS, WHIMSICAL_FONTS, RELIEF_STYLES, NUM_COLUMNS) ---
# (These remain the same as in your previous full version)
WHIMSICAL_COLORS = [
    "#FFADAD", "#FFD6A5", "#FDFFB6", "#CAFFBF", "#9BF6FF", "#A0C4FF", "#BDB2FF", "#FFC6FF",
    "#FFB3BA", "#FFDFBA", "#FFFFBA", "#BAFFC9", "#BAE1FF", "#E0BBE4", "#FEC8D8", "#FFDFD3",
    "#D16BA5", "#86A8E7", "#5FFBF1", "#A267AC", "#F67280", "#C06C84", "#6C5B7B", "#355C7D"
]
WHIMSICAL_FONTS = [
    "Comic Sans MS", "Papyrus", "Curlz MT", "Kristen ITC",
    "Arial", "Verdana", "Helvetica"
]
RELIEF_STYLES = [tk.RAISED, tk.SUNKEN, tk.GROOVE, tk.RIDGE, tk.FLAT]
NUM_COLUMNS = 3
# --- End Constants ---

class WhimsicalFileLauncherApp:
    def __init__(self, root, is_generated_menu=False, initial_configs=None, initial_title="✨ Whimsical File Launcher Creator ✨", initial_root_bg=None):
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
                    'process_info': None # Stores {'type': 'popen'/'selenium', 'instance': obj}
                })

        self.menu_frame = None
        self.scrollable_frame_in_canvas = None
        self.active_selenium_driver = None # Single active Selenium driver instance
        self.active_selenium_filepath = None # File path currently shown by active_selenium_driver
        self.is_running_sequence = False

        # --- GUI Setup ---
        self.title_label_frame = tk.Frame(self.root, bg=self.current_root_bg)
        self.title_label_frame.pack(pady=(10 if is_generated_menu else 0), fill=tk.X)
        
        # Call to _get_random_color() that was causing the error
        title_bg_color = self._get_random_color() 
        self.title_label = tk.Label(self.title_label_frame, text=self.current_menu_title,
                                    font=(random.choice(WHIMSICAL_FONTS), 20, "bold"),
                                    bg=title_bg_color, 
                                    fg=self._get_contrasting_color(title_bg_color)) # Use the determined title_bg_color for contrast
        
        if is_generated_menu : self.title_label.pack(pady=5, padx=20)
        self._update_title_label_style() # This might re-randomize title, ensure consistency if needed or call after initial setup

        control_frame_bg = self._get_random_color(light_bias=True, avoid=self.current_root_bg)
        top_control_frame = tk.Frame(self.root, bg=control_frame_bg); top_control_frame.pack(pady=5, padx=10, fill=tk.X)
        left_controls = tk.Frame(top_control_frame, bg=control_frame_bg); left_controls.pack(side=tk.LEFT, padx=5)
        if not self.is_generated_menu:
            self.select_button = tk.Button(left_controls, text="🌟 Select Files 🌟", command=self.select_files_and_create_menu, font=(random.choice(WHIMSICAL_FONTS), 13, "bold"), bg=self._get_random_color(), fg=self._get_contrasting_color(left_controls.cget("bg")), padx=8, pady=5, relief=random.choice(RELIEF_STYLES), borderwidth=random.randint(2, 3)); self.select_button.pack(side=tk.LEFT, pady=2)
        self.regenerate_button = tk.Button(left_controls, text="🎨 Re-Enchant Menu 🎨", command=lambda: self.create_menu_ui(preserve_styles=False), font=(random.choice(WHIMSICAL_FONTS), 13, "bold"), bg=self._get_random_color(), fg=self._get_contrasting_color(left_controls.cget("bg")), padx=8, pady=5, relief=random.choice(RELIEF_STYLES), borderwidth=random.randint(2, 3)); self.regenerate_button.pack(side=tk.LEFT, padx=(0 if self.is_generated_menu else 5, 0), pady=2)
        center_controls = tk.Frame(top_control_frame, bg=control_frame_bg); center_controls.pack(side=tk.LEFT, expand=True, fill=tk.X); multi_run_options_frame = tk.Frame(center_controls, bg=control_frame_bg); multi_run_options_frame.pack(pady=2)
        tk.Label(multi_run_options_frame, text="Delay(s):", bg=control_frame_bg, fg=self._get_contrasting_color(control_frame_bg), font=("Arial",9)).grid(row=0, column=0, padx=(0,2)); self.duration_entry = tk.Entry(multi_run_options_frame, width=4, font=("Arial", 9)); self.duration_entry.insert(0, "1"); self.duration_entry.grid(row=0, column=1, padx=(0,5))
        self.run_order_var = tk.StringVar(value="order"); tk.Radiobutton(multi_run_options_frame, text="In Order", variable=self.run_order_var, value="order", bg=control_frame_bg, fg=self._get_contrasting_color(control_frame_bg), selectcolor=self._get_random_color(light_bias=True), font=("Arial",9)).grid(row=0, column=2); tk.Radiobutton(multi_run_options_frame, text="Random", variable=self.run_order_var, value="random", bg=control_frame_bg, fg=self._get_contrasting_color(control_frame_bg), selectcolor=self._get_random_color(light_bias=True), font=("Arial",9)).grid(row=0, column=3, padx=(0,5))
        self.loop_behavior_var = tk.StringVar(value="once"); tk.Radiobutton(multi_run_options_frame, text="Run Once", variable=self.loop_behavior_var, value="once", bg=control_frame_bg, fg=self._get_contrasting_color(control_frame_bg), selectcolor=self._get_random_color(light_bias=True), font=("Arial",9)).grid(row=0, column=4); tk.Radiobutton(multi_run_options_frame, text="Loop", variable=self.loop_behavior_var, value="loop", bg=control_frame_bg, fg=self._get_contrasting_color(control_frame_bg), selectcolor=self._get_random_color(light_bias=True), font=("Arial",9)).grid(row=0, column=5, padx=(0,5))
        run_selected_button = tk.Button(multi_run_options_frame, text="🚀 Run Selected", command=self.run_selected_files_handler, font=(random.choice(WHIMSICAL_FONTS), 11, "bold"), bg=self._get_random_color(), fg=self._get_contrasting_color(multi_run_options_frame.cget("bg")), padx=6, pady=3, relief=random.choice(RELIEF_STYLES), borderwidth=random.randint(2,3)); run_selected_button.grid(row=0, column=6, padx=(5,0))
        right_controls = tk.Frame(top_control_frame, bg=control_frame_bg); right_controls.pack(side=tk.RIGHT, padx=5); tk.Button(right_controls, text="Select All", command=lambda: self.toggle_all_checkboxes(True), font=("Arial",9,"bold"), bg="#AEDFF7", fg="black", padx=4, pady=1).pack(side=tk.LEFT, padx=2, pady=2); tk.Button(right_controls, text="Select None", command=lambda: self.toggle_all_checkboxes(False), font=("Arial",9,"bold"), bg="#FFC0CB", fg="black", padx=4, pady=1).pack(side=tk.LEFT, padx=2, pady=2)
        if not self.is_generated_menu:
            save_button = tk.Button(right_controls, text="💾 Save Menu", command=self.prompt_and_save_menu, font=(random.choice(WHIMSICAL_FONTS), 13, "bold"), bg="#77DD77", fg="#000000", padx=8, pady=5, relief=tk.RAISED, borderwidth=3); save_button.pack(side=tk.LEFT, padx=(5,0), pady=2)
        self.menu_display_area = tk.Frame(self.root, bg=self.current_root_bg); self.menu_display_area.pack(expand=True, fill=tk.BOTH, padx=5, pady=5)
        # --- End Full GUI Setup ---
        
        if self.is_generated_menu:
            self.create_menu_ui(preserve_styles=True)

        self.root.protocol("WM_DELETE_WINDOW", self._on_closing) # Graceful exit

        if not SELENIUM_AVAILABLE:
            print("WARNING: Selenium library not found or failed to import.")
            print("HTML files will be opened using the default web browser instead of fullscreen kiosk mode.")
            print("For fullscreen HTML slideshows, please install Selenium and ChromeDriver:")
            print("  pip install selenium")
            print("  Ensure ChromeDriver matching your Chrome version is in your system PATH.")


    def _on_closing(self):
        print("Closing application, terminating active processes...")
        self.is_running_sequence = False # Stop any running sequence first
        time.sleep(0.1) # Give a moment for sequence to acknowledge stop

        # Terminate all Popen processes
        for config in self.selected_file_configs:
            if config.get('process_info') and config['process_info']['type'] == 'popen':
                self._terminate_process_info(config['path']) # Use path to find and terminate
        
        # Terminate the single active Selenium driver if it exists
        self._terminate_selenium_driver_global()

        self.root.destroy()

    def _update_title_label_style(self):
        if hasattr(self, 'title_label') and self.title_label.winfo_exists():
            bg_color = self._get_random_color()
            fg_color = self._get_contrasting_color(bg_color)
            font_family = random.choice(WHIMSICAL_FONTS)
            font_size = random.randint(18, 24) if self.is_generated_menu else random.randint(16, 20)
            self.title_label.config(text=self.current_menu_title,font=(font_family, font_size, "bold"),bg=bg_color, fg=fg_color)
        
        # Update root background unless it's the initial setup where it's already set
        if not hasattr(self, '_initial_bg_set_flag'): # Avoid changing on first call from init if already set
            self.current_root_bg = self._get_random_color(light_bias=True)
            self.root.configure(bg=self.current_root_bg)
        else:
            del self._initial_bg_set_flag # Remove flag after first potential skip

        if hasattr(self, 'menu_display_area') and self.menu_display_area.winfo_exists():
            self.menu_display_area.configure(bg=self.current_root_bg)
        if hasattr(self, 'title_label_frame') and self.title_label_frame.winfo_exists():
            self.title_label_frame.configure(bg=self.current_root_bg)
        
        # A flag to ensure initial root_bg from __init__ is not immediately overwritten by _update_title_label_style
        if not hasattr(self, '_initial_bg_set_flag_for_update_call'):
             self._initial_bg_set_flag_for_update_call = True


    def _get_random_color(self, light_bias=False, avoid=None):
        color = random.choice(WHIMSICAL_COLORS)
        if avoid:
            while color == avoid:
                color = random.choice(WHIMSICAL_COLORS)

        if light_bias:
            # Calculate r,g,b for the current color
            try:
                r, g, b = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)
            except ValueError: # Should not happen with valid hex strings in WHIMSICAL_COLORS
                return color # Return original color if parsing fails

            # Check if this color is dark
            if (r + g + b) / 3 < 128:
                # If it's dark, try to find a lighter one
                for _ in range(3): # Try up to 3 times
                    nc = random.choice(WHIMSICAL_COLORS)
                    if avoid and nc == avoid: # Also check against avoid color here
                        continue
                    try:
                        nr, ng, nb = int(nc[1:3], 16), int(nc[3:5], 16), int(nc[5:7], 16)
                    except ValueError:
                        continue # Try next color if parsing fails

                    if (nr + ng + nb) / 3 >= 128: # If the new color (nc) is light
                        return nc # Return the new, lighter color
                # If loop finishes, no lighter color was found in 3 tries.
                # The function will proceed to return the original 'color' (which might be dark).
        
        # If light_bias is False, or
        # if light_bias is True and the original color was already light, or
        # if light_bias is True, original color was dark, but no lighter alternative was found:
        return color

    def _get_contrasting_color(self, bg_color_hex):
        try:
            r,g,b=int(bg_color_hex[1:3],16),int(bg_color_hex[3:5],16),int(bg_color_hex[5:7],16)
            return"#000000"if(0.299*r+0.587*g+0.114*b)>128 else"#FFFFFF"
        except (ValueError, TypeError): # Handle cases where bg_color_hex might be invalid
            return random.choice(["#000000","#FFFFFF"])

    def select_files_and_create_menu(self):
        files=filedialog.askopenfilenames(title="Select your magical files",filetypes=(("All files","*.*"),("Python files","*.py"),("HTML files","*.html;*.htm"),("Image files","*.png;*.jpg;*.jpeg;*.gif;*.bmp;*.svg;*.webp"),("Audio files","*.mp3;*.wav;*.ogg;*.m4a"),("Video files","*.mp4;*.avi;*.mkv;*.mov"),("Text/Docs","*.txt;*.md;*.pdf;*.doc;*.docx")))
        if files:
            self.selected_file_configs=[]
            for f_path in files:self.selected_file_configs.append({'path':os.path.abspath(f_path),'var':tk.BooleanVar(value=False),'style':{},'process_info':None})
            # Set a flag so _update_title_label_style knows not to change root bg immediately after this
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
        if not self.selected_file_configs:
            if not self.is_generated_menu:messagebox.showinfo("No Files","No files selected to create a menu.")
            return
        if self.menu_frame:self.menu_frame.destroy()
        for widget in self.menu_display_area.winfo_children():widget.destroy()
        
        if not preserve_styles:
            # Set a flag so the _update_title_label_style call does not immediately re-randomize root background
            # if it was just set by select_files_and_create_menu or __init__
            # This logic is a bit tricky with multiple paths calling _update_title_label_style
            if not hasattr(self, '_initial_bg_set_flag_for_update_call'): # Only call if not already called in a way that sets the initial bg
                 self._update_title_label_style()
            elif hasattr(self, '_initial_bg_set_flag_for_update_call'):
                 del self._initial_bg_set_flag_for_update_call # Reset for next full regeneration

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
            except tk.TclError: # Fallback font if whimsical one fails
                 tk.Button(item_f,text=btn_txt,command=lambda p=filepath:self.launch_file(p),
                           bg=item_style['bg'],fg=item_style['fg'],font=("Arial",10),width=12).pack(side=tk.LEFT,fill=tk.X,expand=True)
        
        self.root.after(50,lambda:canvas.create_window((canvas.winfo_width()//2,0),window=self.scrollable_frame_in_canvas,anchor="n") if canvas.winfo_exists() else None)

    def _get_config_by_path(self, filepath):
        for config in self.selected_file_configs:
            if config['path'] == filepath:
                return config
        return None

    def _launch_selenium_html_in_thread(self, filepath_to_load):
        """Handles Selenium WebDriver interactions in a separate thread."""
        if not SELENIUM_AVAILABLE: # Should be checked before calling, but as a safeguard
            webbrowser.open(f'file:///{filepath_to_load}')
            return

        target_config = self._get_config_by_path(filepath_to_load)

        def task():
            nonlocal target_config # Allow modification of the config from the outer scope
            driver_instance = None
            try:
                # If there's an active Selenium driver and it's not for the current file, close it.
                if self.active_selenium_driver and self.active_selenium_filepath != filepath_to_load:
                    print(f"Closing previous Selenium instance for {self.active_selenium_filepath}")
                    self._terminate_selenium_driver_global() # This will set self.active_selenium_driver to None

                if not self.active_selenium_driver: # Need to create a new driver
                    print(f"Creating new Selenium driver for {filepath_to_load}")
                    chrome_options = ChromeOptions()
                    chrome_options.add_argument("--start-fullscreen")
                    chrome_options.add_argument("--kiosk")
                    # Consider adding these if issues arise, but start simple:
                    # chrome_options.add_argument("--no-sandbox")
                    # chrome_options.add_argument("--disable-dev-shm-usage")
                    # chrome_options.add_argument("--disable-gpu") # If rendering issues
                    # chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"]) # Hides "Chrome is controlled" bar

                    try:
                        driver_instance = webdriver.Chrome(options=chrome_options)
                        self.active_selenium_driver = driver_instance # Now it's the active one
                        self.active_selenium_filepath = filepath_to_load
                        if target_config:
                            target_config['process_info'] = {'type': 'selenium', 'instance': driver_instance}
                    except Exception as e:
                        # Schedule messagebox on main thread
                        self.root.after(0, lambda: messagebox.showerror("Selenium Error",
                            f"Could not start Chrome WebDriver for HTML.\n"
                            f"Ensure ChromeDriver is installed and in PATH, and matches your Chrome version.\n"
                            f"Error: {e}", parent=self.root))
                        print(f"Error creating WebDriver: {e}")
                        # Fallback to default browser
                        self.root.after(0, lambda: webbrowser.open(f'file:///{filepath_to_load}'))
                        if target_config: target_config['process_info'] = None
                        self.active_selenium_driver = None # Ensure it's cleared
                        self.active_selenium_filepath = None
                        return # Exit thread

                # Load the file into the (now guaranteed to be active) driver
                print(f"Selenium loading: file:///{filepath_to_load}")
                self.active_selenium_driver.get(f"file:///{filepath_to_load}")
                self.active_selenium_filepath = filepath_to_load # Update just in case it was an existing driver for a new file

                # Check if the window is still open after get() - user might close it quickly
                try:
                    _ = self.active_selenium_driver.window_handles
                except Exception: # Likely NoSuchWindowException or WebDriverException
                    print("Selenium window closed during/after load.")
                    self._terminate_selenium_driver_global() # Clean up references

            except Exception as e:
                print(f"Error in Selenium task for {filepath_to_load}: {e}")
                if driver_instance: # If this thread created it and it failed
                    try: driver_instance.quit()
                    except: pass
                # If it was using self.active_selenium_driver, and it failed, clear it
                if self.active_selenium_driver and (not driver_instance or driver_instance == self.active_selenium_driver):
                    self._terminate_selenium_driver_global()
                if target_config: target_config['process_info'] = None
        
        threading.Thread(target=task, daemon=True).start()

    def launch_file(self, filepath, is_part_of_sequence=False):
        _, ext = os.path.splitext(filepath); ext = ext.lower()
        abs_path = os.path.abspath(filepath)
        current_config = self._get_config_by_path(abs_path)

        if is_part_of_sequence:
            # Terminate Popen processes for *other* files
            for config_item in self.selected_file_configs:
                if config_item['path'] != abs_path and \
                   config_item.get('process_info') and \
                   config_item['process_info']['type'] == 'popen':
                    self._terminate_process_info(config_item['path'])
            
            if not (ext in ['.html', '.htm']) and self.active_selenium_driver:
                print(f"Sequence: Current file '{os.path.basename(abs_path)}' is not HTML. Closing active Selenium driver.")
                self._terminate_selenium_driver_global()

        print(f"Launching: {abs_path} (ext: {ext})")
        try:
            if ext == '.py':
                py_exe = sys.executable if sys.executable else "python"; popen_obj = None
                if os.name == 'nt': popen_obj = subprocess.Popen([py_exe, abs_path], creationflags=subprocess.CREATE_NEW_CONSOLE)
                elif sys.platform == 'darwin': popen_obj = subprocess.Popen([py_exe, abs_path]) # Use sys.platform
                else: # Linux
                    try: popen_obj = subprocess.Popen(['x-terminal-emulator', '-e', py_exe, abs_path])
                    except FileNotFoundError:
                        try: popen_obj = subprocess.Popen(['gnome-terminal', '--', py_exe, abs_path])
                        except FileNotFoundError:
                            try: popen_obj = subprocess.Popen(['konsole', '-e', py_exe, abs_path])
                            except FileNotFoundError: popen_obj = subprocess.Popen([py_exe, abs_path])
                if current_config and popen_obj: current_config['process_info'] = {'type': 'popen', 'instance': popen_obj}

            elif ext in ['.html', '.htm']:
                if SELENIUM_AVAILABLE:
                    self._launch_selenium_html_in_thread(abs_path)
                else: 
                    webbrowser.open(f'file:///{abs_path}')
                    if current_config: current_config['process_info'] = None 

            elif ext in ['.svg','.jpg','.jpeg','.png','.gif','.bmp','.webp','.ico','.mp3','.wav','.ogg','.aac','.flac','.m4a','.mp4','.avi','.mkv','.mov','.wmv','.flv','.pdf','.txt','.md','.log','.csv','.json','.xml','.doc','.docx','.xls','.xlsx','.ppt','.pptx','.odt','.ods','.odp']:
                if os.name == 'nt': os.startfile(abs_path)
                elif sys.platform == 'darwin': subprocess.Popen(['open', abs_path]) # Use sys.platform
                else: subprocess.Popen(['xdg-open', abs_path])
                if current_config: current_config['process_info'] = None 
            else: 
                if os.name == 'nt': os.startfile(abs_path)
                elif sys.platform == 'darwin': subprocess.Popen(['open', abs_path]) # Use sys.platform
                else: subprocess.Popen(['xdg-open', abs_path])
                if current_config: current_config['process_info'] = None

        except Exception as e:
            print(f"Error launching {filepath}: {e}")
            self.root.after(0, lambda: messagebox.showerror("Launch Error", f"Could not open file: {os.path.basename(filepath)}\nError: {e}", parent=self.root))
            if current_config: current_config['process_info'] = None


    def _terminate_selenium_driver_global(self):
        if self.active_selenium_driver:
            driver_to_quit = self.active_selenium_driver
            filepath_it_was_for = self.active_selenium_filepath
            
            self.active_selenium_driver = None 
            self.active_selenium_filepath = None

            print(f"Terminating global Selenium driver (was for: {filepath_it_was_for or 'Unknown File'})")
            try:
                # Run quit in a separate thread to avoid blocking UI if it hangs
                threading.Thread(target=driver_to_quit.quit, daemon=True).start()
            except Exception as e:
                print(f"Error initiating quit for global Selenium driver: {e}")
            
            if filepath_it_was_for:
                old_config = self._get_config_by_path(filepath_it_was_for)
                if old_config and old_config.get('process_info') and \
                   old_config['process_info'].get('instance') == driver_to_quit: 
                    old_config['process_info'] = None


    def _terminate_process_info(self, filepath_to_terminate):
        config_to_terminate = self._get_config_by_path(filepath_to_terminate)
        if not config_to_terminate or not config_to_terminate.get('process_info'):
            return

        info = config_to_terminate['process_info']
        instance = info['instance']
        ptype = info['type']

        print(f"Attempting to terminate {ptype} for: {os.path.basename(filepath_to_terminate)}")

        if ptype == 'popen' and instance:
            try:
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
                    # Run quit in a separate thread
                    threading.Thread(target=instance.quit, daemon=True).start()
                except Exception as e: print(f"Error initiating quit for stray selenium instance: {e}")
        
        config_to_terminate['process_info'] = None 


    def run_selected_files_handler(self):
        if self.is_running_sequence:
            self.is_running_sequence = False
            time.sleep(0.1) 
            for config_item in self.selected_file_configs:
                if config_item.get('process_info') and config_item['process_info']['type'] == 'popen':
                    self._terminate_process_info(config_item['path'])
            self._terminate_selenium_driver_global() 
            messagebox.showinfo("Stopped", "Multi-run sequence stopped.", parent=self.root)
            return

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

        can_all_be_auto_closed = all(
            cfg['path'].lower().endswith('.py') or \
            (cfg['path'].lower().endswith(('.html', '.htm')) and SELENIUM_AVAILABLE)
            for cfg in selected_to_run_configs
        )
        if delay_seconds > 0 and len(selected_to_run_configs) > 1 and not can_all_be_auto_closed:
             if not messagebox.askyesno("Limitation",
                                       "Multi-run with delay attempts to close previous PYTHON scripts "
                                       "and HTML files (if Selenium is used).\n"
                                       "Other file types (images, docs, etc.) opened by the OS default "
                                       "application CANNOT be automatically closed by this launcher.\n\n"
                                       "Do you want to proceed?", parent=self.root):
                return

        self.is_running_sequence = True
        order = self.run_order_var.get()
        loop = self.loop_behavior_var.get() == "loop"
        current_list = selected_to_run_configs[:] 

        def launch_sequence(index=0):
            if not self.is_running_sequence:
                print("Sequence stopped by user flag.")
                return

            if order == "random" and index == 0: 
                random.shuffle(current_list)
            
            actual_index = index % len(current_list) 

            if not current_list: 
                self.is_running_sequence = False
                return

            config_to_run = current_list[actual_index]
            self.launch_file(config_to_run['path'], is_part_of_sequence=True)

            next_index = index + 1
            if next_index < len(current_list) or loop:
                if not self.is_running_sequence: return 
                
                actual_delay_ms = int(delay_seconds * 1000) if delay_seconds > 0 else 50 
                
                self.root.after(actual_delay_ms, lambda: launch_sequence(next_index))
            else: 
                self.is_running_sequence = False
                print("Finished sequence.")
        launch_sequence()


    def toggle_all_checkboxes(self, state=True):
        for config in self.selected_file_configs:config['var'].set(state)

    def prompt_and_save_menu(self):
        if not self.selected_file_configs:messagebox.showerror("No Menu","No menu to save.",parent=self.root);return
        new_menu_title=simpledialog.askstring("Menu Title","Enter a title for your saved menu window:",initialvalue=self.current_menu_title.replace("Creator","").strip(),parent=self.root)
        if not new_menu_title:return
        py_filename_suggestion="".join(c if c.isalnum()or c in('_','-')else'_'for c in new_menu_title.lower().replace(" ","_"));py_filename_suggestion=(py_filename_suggestion[:30]+".py")if py_filename_suggestion else"saved_menu.py"
        py_filename=filedialog.asksaveasfilename(title="Save Menu Script As...",initialfile=py_filename_suggestion,defaultextension=".py",filetypes=[("Python files","*.py")],parent=self.root)
        if not py_filename:return
        storable_configs_for_script=[{'path':c['path'],'style':c['style'].copy()}for c in self.selected_file_configs]
        # Use self.current_root_bg for the saved menu's initial background
        script_content=self._generate_menu_script_content(new_menu_title,storable_configs_for_script,self.current_root_bg,NUM_COLUMNS)
        try:
            with open(py_filename,"w",encoding="utf-8")as f:f.write(script_content)
            messagebox.showinfo("Menu Saved",f"Menu script saved as:\n{py_filename}",parent=self.root)
        except Exception as e:messagebox.showerror("Save Error",f"Could not save menu script:\n{e}",parent=self.root)

    def _generate_menu_script_content(self, menu_title_str, file_configs_with_styles, root_bg_str, num_cols_int):
        import inspect
        class_source = inspect.getsource(WhimsicalFileLauncherApp)
        
        # Use sys.platform consistently for OS checks in generated script's launch_file
        class_source = class_source.replace("os.uname().sysname == 'Darwin'", "sys.platform == 'darwin'")


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

# --- Selenium Imports for Generated Script ---
{selenium_imports_for_generated_script}

# --- START OF COPIED/REDEFINED CONSTANTS ---
WHIMSICAL_COLORS = {repr(WHIMSICAL_COLORS)}
WHIMSICAL_FONTS = {repr(WHIMSICAL_FONTS)}
RELIEF_STYLES = {repr(RELIEF_STYLES)}
NUM_COLUMNS = {num_cols_int} # Use the passed num_cols_int
# --- End Constants ---

# --- WhimsicalFileLauncherApp Class (Copied from original, including Selenium logic) ---
{class_source}
# --- End WhimsicalFileLauncherApp Class ---

# --- Script Entry Point for the Saved Menu ---
if __name__ == "__main__":
    SAVED_MENU_TITLE_STR = {repr(menu_title_str)}
    SAVED_FILE_CONFIGS_DATA = {repr(file_configs_with_styles)} 
    INITIAL_ROOT_BG_STR = {repr(root_bg_str)}

    if not SELENIUM_AVAILABLE:
        # Optional: Show warning in generated menu at startup via console
        print("Generated Menu Warning: Selenium library not found. HTML files will open in default browser.")
        print("For fullscreen HTML viewing, please install Selenium and ChromeDriver.")

    root = tk.Tk()
    app = WhimsicalFileLauncherApp(
        root,
        is_generated_menu=True, 
        initial_configs=SAVED_FILE_CONFIGS_DATA,
        initial_title=SAVED_MENU_TITLE_STR,
        initial_root_bg=INITIAL_ROOT_BG_STR
    )
    root.mainloop()
"""
        return script


# --- Main application entry point (for the creator) ---
if __name__ == "__main__":
    main_creator_root = tk.Tk()
    creator_app = WhimsicalFileLauncherApp(main_creator_root)
    main_creator_root.mainloop()