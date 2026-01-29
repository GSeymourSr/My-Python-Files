import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import os
import subprocess
import webbrowser
import random
import time
import sys # For sys.executable to run python scripts

# (WHIMSICAL_COLORS, WHIMSICAL_FONTS, RELIEF_STYLES remain the same)
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

class WhimsicalFileLauncherApp:
    def __init__(self, root, is_generated_menu=False, initial_configs=None, initial_title="✨ Whimsical File Launcher Creator ✨", initial_root_bg=None):
        self.root = root
        self.is_generated_menu = is_generated_menu
        self.current_menu_title = initial_title
        self.root.title(self.current_menu_title)

        try: self.root.state('zoomed')
        except tk.TclError:
            try: self.root.attributes('-zoomed', True)
            except tk.TclError:
                self.root.geometry(f"{self.root.winfo_screenwidth()}x{self.root.winfo_screenheight()}+0+0")
        self.root.resizable(True, True)

        self.current_root_bg = initial_root_bg if initial_root_bg else self._get_random_color(light_bias=True)
        self.root.configure(bg=self.current_root_bg)

        self.selected_file_configs = [] # List of dicts
        if is_generated_menu and initial_configs:
            for config_data in initial_configs:
                self.selected_file_configs.append({
                    'path': config_data['path'],
                    'var': tk.BooleanVar(value=False),
                    'style': config_data['style'].copy(), # Use copies of styles
                    'process': None
                })


        self.menu_frame = None
        self.scrollable_frame_in_canvas = None
        self.active_processes = {} # For managing Popen objects of Python scripts
        self.is_running_sequence = False # Flag for multi-run loop

        # --- Title Label (more prominent in generated menu) ---
        self.title_label_frame = tk.Frame(self.root, bg=self.current_root_bg)
        self.title_label_frame.pack(pady=(10 if is_generated_menu else 0), fill=tk.X)
        self.title_label = tk.Label(self.title_label_frame, text=self.current_menu_title,
                                    font=(random.choice(WHIMSICAL_FONTS), 20, "bold"),
                                    bg=self._get_random_color(), fg=self._get_contrasting_color(self.current_root_bg))
        if is_generated_menu : # Only pack if it's a generated menu with a prominent title
             self.title_label.pack(pady=5, padx=20)
        self._update_title_label_style() # Initial style

        # --- Main Control Frame ---
        control_frame_bg = self._get_random_color(light_bias=True, avoid=self.current_root_bg)
        top_control_frame = tk.Frame(self.root, bg=control_frame_bg)
        top_control_frame.pack(pady=5, padx=10, fill=tk.X)

        # --- Left Aligned Controls (Select, Re-Enchant) ---
        left_controls = tk.Frame(top_control_frame, bg=control_frame_bg)
        left_controls.pack(side=tk.LEFT, padx=5)

        if not self.is_generated_menu:
            self.select_button = tk.Button(
                left_controls, text="🌟 Select Files 🌟", command=self.select_files_and_create_menu,
                font=(random.choice(WHIMSICAL_FONTS), 13, "bold"), bg=self._get_random_color(),
                fg=self._get_contrasting_color(left_controls.cget("bg")), padx=8, pady=5,
                relief=random.choice(RELIEF_STYLES), borderwidth=random.randint(2, 3)
            )
            self.select_button.pack(side=tk.LEFT, pady=2)

        self.regenerate_button = tk.Button(
            left_controls, text="🎨 Re-Enchant Menu 🎨", command=self.create_menu_ui, # Re-enchants existing files
            font=(random.choice(WHIMSICAL_FONTS), 13, "bold"), bg=self._get_random_color(),
            fg=self._get_contrasting_color(left_controls.cget("bg")), padx=8, pady=5,
            relief=random.choice(RELIEF_STYLES), borderwidth=random.randint(2, 3)
        )
        self.regenerate_button.pack(side=tk.LEFT, padx=(5 if not self.is_generated_menu else 0, 0), pady=2)

        # --- Center Controls (Multi-Run) ---
        center_controls = tk.Frame(top_control_frame, bg=control_frame_bg)
        center_controls.pack(side=tk.LEFT, expand=True, fill=tk.X) # Allow expansion

        multi_run_options_frame = tk.Frame(center_controls, bg=control_frame_bg)
        multi_run_options_frame.pack(pady=2)

        tk.Label(multi_run_options_frame, text="Delay(s):", bg=control_frame_bg, fg=self._get_contrasting_color(control_frame_bg), font=("Arial",9)).grid(row=0, column=0, padx=(0,2))
        self.duration_entry = tk.Entry(multi_run_options_frame, width=4, font=("Arial", 9))
        self.duration_entry.insert(0, "1")
        self.duration_entry.grid(row=0, column=1, padx=(0,5))

        self.run_order_var = tk.StringVar(value="order") # 'order' or 'random'
        tk.Radiobutton(multi_run_options_frame, text="In Order", variable=self.run_order_var, value="order", bg=control_frame_bg, fg=self._get_contrasting_color(control_frame_bg), selectcolor=self._get_random_color(light_bias=True), font=("Arial",9)).grid(row=0, column=2)
        tk.Radiobutton(multi_run_options_frame, text="Random", variable=self.run_order_var, value="random", bg=control_frame_bg, fg=self._get_contrasting_color(control_frame_bg), selectcolor=self._get_random_color(light_bias=True), font=("Arial",9)).grid(row=0, column=3, padx=(0,5))

        self.loop_behavior_var = tk.StringVar(value="once") # 'once' or 'loop'
        tk.Radiobutton(multi_run_options_frame, text="Run Once", variable=self.loop_behavior_var, value="once", bg=control_frame_bg, fg=self._get_contrasting_color(control_frame_bg), selectcolor=self._get_random_color(light_bias=True), font=("Arial",9)).grid(row=0, column=4)
        tk.Radiobutton(multi_run_options_frame, text="Loop", variable=self.loop_behavior_var, value="loop", bg=control_frame_bg, fg=self._get_contrasting_color(control_frame_bg), selectcolor=self._get_random_color(light_bias=True), font=("Arial",9)).grid(row=0, column=5, padx=(0,5))
        
        run_selected_button = tk.Button(
            multi_run_options_frame, text="🚀 Run Selected", command=self.run_selected_files_handler,
            font=(random.choice(WHIMSICAL_FONTS), 11, "bold"), bg=self._get_random_color(),
            fg=self._get_contrasting_color(multi_run_options_frame.cget("bg")), padx=6, pady=3,
            relief=random.choice(RELIEF_STYLES), borderwidth=random.randint(2,3)
        )
        run_selected_button.grid(row=0, column=6, padx=(5,0))


        # --- Right Aligned Controls (Save, Select All/None) ---
        right_controls = tk.Frame(top_control_frame, bg=control_frame_bg)
        right_controls.pack(side=tk.RIGHT, padx=5)
        
        select_all_button = tk.Button(right_controls, text="Select All", command=lambda: self.toggle_all_checkboxes(True), font=("Arial",9,"bold"), bg="#AEDFF7", fg="black", padx=4, pady=1)
        select_all_button.pack(side=tk.LEFT, padx=2, pady=2)
        deselect_all_button = tk.Button(right_controls, text="Select None", command=lambda: self.toggle_all_checkboxes(False), font=("Arial",9,"bold"), bg="#FFC0CB", fg="black", padx=4, pady=1)
        deselect_all_button.pack(side=tk.LEFT, padx=2, pady=2)

        if not self.is_generated_menu:
            save_button = tk.Button(
                right_controls, text="💾 Save Menu", command=self.prompt_and_save_menu,
                font=(random.choice(WHIMSICAL_FONTS), 13, "bold"), bg="#77DD77", fg="#000000",
                padx=8, pady=5, relief=tk.RAISED, borderwidth=3
            )
            save_button.pack(side=tk.LEFT, padx=(5,0), pady=2)


        # --- Menu Display Area ---
        self.menu_display_area = tk.Frame(self.root, bg=self.current_root_bg)
        self.menu_display_area.pack(expand=True, fill=tk.BOTH, padx=5, pady=5)
        
        if self.is_generated_menu: # Populate menu if it's a generated one
            self.create_menu_ui()


    def _update_title_label_style(self):
        if hasattr(self, 'title_label') and self.title_label.winfo_exists():
            bg_color = self._get_random_color()
            fg_color = self._get_contrasting_color(bg_color)
            font_family = random.choice(WHIMSICAL_FONTS)
            font_size = random.randint(18, 24) if self.is_generated_menu else random.randint(16, 20)
            self.title_label.config(text=self.current_menu_title,
                                    font=(font_family, font_size, "bold"),
                                    bg=bg_color, fg=fg_color)
        self.current_root_bg = self._get_random_color(light_bias=True)
        self.root.configure(bg=self.current_root_bg)
        if hasattr(self, 'menu_display_area') and self.menu_display_area.winfo_exists():
            self.menu_display_area.configure(bg=self.current_root_bg)
        if hasattr(self, 'title_label_frame') and self.title_label_frame.winfo_exists():
            self.title_label_frame.configure(bg=self.current_root_bg)


    def _get_random_color(self, light_bias=False, avoid=None):
        color = random.choice(WHIMSICAL_COLORS)
        if avoid:
            while color == avoid: color = random.choice(WHIMSICAL_COLORS)
        if light_bias:
            r, g, b = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)
            if (r + g + b) / 3 < 128:
                for _ in range(3):
                    new_color = random.choice(WHIMSICAL_COLORS)
                    nr, ng, nb = int(new_color[1:3],16), int(new_color[3:5],16), int(new_color[5:7],16)
                    if (nr + ng + nb) / 3 >= 128: return new_color
        return color

    def _get_contrasting_color(self, bg_color_hex):
        try:
            r=int(bg_color_hex[1:3],16); g=int(bg_color_hex[3:5],16); b=int(bg_color_hex[5:7],16)
            return "#000000" if (0.299*r + 0.587*g + 0.114*b) > 128 else "#FFFFFF"
        except: return random.choice(["#000000", "#FFFFFF"])

    def select_files_and_create_menu(self):
        # ... (file dialog as before)
        files = filedialog.askopenfilenames(
             title="Select your magical files",
             filetypes=(("All files", "*.*"), ("Python files", "*.py"), ("HTML files", "*.html;*.htm"),
                        ("Image files", "*.png;*.jpg;*.jpeg;*.gif;*.bmp;*.svg;*.webp"),
                        ("Audio files", "*.mp3;*.wav;*.ogg;*.m4a"),
                        ("Video files", "*.mp4;*.avi;*.mkv;*.mov"),
                        ("Text/Docs", "*.txt;*.md;*.pdf;*.doc;*.docx"))
        )
        if files:
            self.selected_file_configs = [] # Reset
            for f_path in files:
                self.selected_file_configs.append({
                    'path': os.path.abspath(f_path), # Store absolute path
                    'var': tk.BooleanVar(value=False),
                    'style': {}, # Will be populated
                    'process': None # For Popen object if it's a Python script
                })
            self.create_menu_ui()
        elif not self.selected_file_configs: # No files selected and no previous files
             if self.menu_frame: self.menu_frame.destroy(); self.menu_frame = None
             for widget in self.menu_display_area.winfo_children(): widget.destroy()
             no_files_label = tk.Label(self.menu_display_area, text="No files selected. The magic awaits!",
                                       font=("Comic Sans MS", 18), bg=self.menu_display_area.cget("bg"),
                                       fg=self._get_contrasting_color(self.menu_display_area.cget("bg")))
             no_files_label.pack(expand=True)
             self.root.after(3000, lambda: no_files_label.destroy() if no_files_label.winfo_exists() else None)


    def create_menu_ui(self, preserve_styles=False): # preserve_styles for generated menu's first load
        if not self.selected_file_configs:
            if not self.is_generated_menu: # Don't show if generated menu starts empty
                messagebox.showinfo("No Files", "No files selected to create a menu.")
            return

        if self.menu_frame: self.menu_frame.destroy()
        for widget in self.menu_display_area.winfo_children(): widget.destroy()

        self._update_title_label_style() # Randomize title and root bg on re-enchant

        menu_frame_bg = self._get_random_color(light_bias=True, avoid=self.current_root_bg)
        self.menu_frame = tk.Frame(self.menu_display_area, bg=menu_frame_bg)
        self.menu_frame.pack(expand=True, fill=tk.BOTH, padx=5, pady=5)

        canvas_bg = self._get_random_color(light_bias=True, avoid=menu_frame_bg)
        canvas = tk.Canvas(self.menu_frame, bg=canvas_bg, highlightthickness=0)
        scrollbar = tk.Scrollbar(self.menu_frame, orient="vertical", command=canvas.yview)
        self.scrollable_frame_in_canvas = tk.Frame(canvas, bg=canvas_bg) # This frame holds the grid

        self.scrollable_frame_in_canvas.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        # Center the scrollable_frame_in_canvas within the canvas
        canvas.create_window((0,0), window=self.scrollable_frame_in_canvas, anchor="nw") # Changed to anchor="center" later if possible

        canvas.configure(yscrollcommand=scrollbar.set)
        def _on_mousewheel(event): canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        def _on_mousewheel_linux(event):
            if event.num == 4: canvas.yview_scroll(-1, "units")
            elif event.num == 5: canvas.yview_scroll(1, "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        canvas.bind_all("<Button-4>", _on_mousewheel_linux)
        canvas.bind_all("<Button-5>", _on_mousewheel_linux)

        canvas.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        scrollbar.pack(side="right", fill="y")

        # --- Configure grid for centering ---
        # Add dummy columns with weights to push content to center
        self.scrollable_frame_in_canvas.grid_columnconfigure(0, weight=1) # Left spacer
        for i in range(NUM_COLUMNS):
            self.scrollable_frame_in_canvas.grid_columnconfigure(i + 1, weight=1) # Content columns
        self.scrollable_frame_in_canvas.grid_columnconfigure(NUM_COLUMNS + 1, weight=1) # Right spacer


        row = 0
        for i, config in enumerate(self.selected_file_configs):
            filepath = config['path']
            filename = os.path.basename(filepath)
            
            # Generate/Update style unless it's the first load of a generated menu preserving styles
            if not preserve_styles or not config['style'] or not config['style'].get('bg'):
                style = {
                    'bg': self._get_random_color(), 'font_family': random.choice(WHIMSICAL_FONTS),
                    'font_size': random.randint(10, 14), 'relief': random.choice(RELIEF_STYLES),
                    'borderwidth': random.randint(1, 3), 'padx': random.randint(6, 10),
                    'pady': random.randint(3, 6), 'text': filename
                }
                style['fg'] = self._get_contrasting_color(style['bg'])
                style['activebackground'] = self._get_random_color(avoid=style['bg'])
                style['activeforeground'] = self._get_contrasting_color(style['activebackground'])
                config['style'] = style
            
            item_style = config['style']
            col_offset = 1 # Start content from the second grid column (after left spacer)
            actual_col_in_grid = (i % NUM_COLUMNS) + col_offset
            if i % NUM_COLUMNS == 0 and i != 0: row += 1

            item_frame = tk.Frame(self.scrollable_frame_in_canvas, bg=self.scrollable_frame_in_canvas.cget("bg"))
            item_frame.grid(row=row, column=actual_col_in_grid, padx=3, pady=3, sticky="ew")

            chk = tk.Checkbutton(item_frame, variable=config['var'], bg=item_frame.cget("bg"), activebackground=item_frame.cget("bg"))
            chk.pack(side=tk.LEFT, padx=(0,1))

            btn_text = item_style['text']
            if len(btn_text) > 20: btn_text = btn_text[:9] + "..." + btn_text[-9:]

            try:
                btn = tk.Button(item_frame, text=btn_text, command=lambda p=filepath: self.launch_file(p),
                                bg=item_style['bg'], fg=item_style['fg'], font=(item_style['font_family'], item_style['font_size']),
                                relief=item_style['relief'], borderwidth=item_style['borderwidth'],
                                padx=item_style['padx'], pady=item_style['pady'],
                                activebackground=item_style['activebackground'], activeforeground=item_style['activeforeground'],
                                width=12) # Base width
                btn.pack(side=tk.LEFT, fill=tk.X, expand=True)
            except tk.TclError: # Font fallback
                btn = tk.Button(item_frame, text=btn_text, command=lambda p=filepath: self.launch_file(p),
                                bg=item_style['bg'], fg=item_style['fg'], font=("Arial", 10), width=12)
                btn.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # This line attempts to re-center the content after it's laid out. Might need adjustment.
        self.root.after(50, lambda: canvas.create_window((canvas.winfo_width()//2, 0), window=self.scrollable_frame_in_canvas, anchor="n") if canvas.winfo_exists() else None)


    def launch_file(self, filepath, is_part_of_sequence=False):
        _, ext = os.path.splitext(filepath)
        ext = ext.lower()
        abs_path = os.path.abspath(filepath) # Should already be absolute

        # Terminate previous Python script if this is a Python script in a sequence
        # For other types, we can't reliably close, so we'll skip or warn.
        if is_part_of_sequence:
            # Clear any completed/terminated non-python processes from self.active_processes
            for p_path, proc_obj in list(self.active_processes.items()):
                if proc_obj is not None and proc_obj.poll() is not None: # Process finished
                    del self.active_processes[p_path]

            # Terminate previous *Python* script
            prev_py_scripts = [p for p, proc in self.active_processes.items() if proc and p.lower().endswith('.py')]
            for prev_py_path in prev_py_scripts:
                if prev_py_path != filepath: # Don't terminate self if re-launching
                    self._terminate_process(prev_py_path)
        
        try:
            print(f"Launching: {abs_path} (ext: {ext})")
            process_obj = None # For Popen

            if ext == '.py':
                # Use sys.executable to be sure about the python interpreter
                py_exe = sys.executable if sys.executable else "python"
                if os.name == 'nt':
                    process_obj = subprocess.Popen([py_exe, abs_path], creationflags=subprocess.CREATE_NEW_CONSOLE)
                elif os.uname().sysname == 'Darwin':
                    # For macOS, running in a new Terminal window is complex.
                    # This runs it in background, output may go to launching terminal.
                    # For a new window: ['open', '-a', 'Terminal', py_exe, abs_path] but Popen control is harder.
                    process_obj = subprocess.Popen([py_exe, abs_path])
                else: # Linux
                    try:
                        process_obj = subprocess.Popen(['x-terminal-emulator', '-e', py_exe, abs_path])
                    except FileNotFoundError: # Fallback through common terminals
                        try: process_obj = subprocess.Popen(['gnome-terminal', '--', py_exe, abs_path])
                        except FileNotFoundError:
                            try: process_obj = subprocess.Popen(['konsole', '-e', py_exe, abs_path])
                            except FileNotFoundError: process_obj = subprocess.Popen([py_exe, abs_path])
                
                if process_obj:
                    self.active_processes[filepath] = process_obj
                    # Update corresponding config
                    for cfg in self.selected_file_configs:
                        if cfg['path'] == filepath:
                            cfg['process'] = process_obj
                            break
            # ... (other file types as before, they don't return manageable Popen objects)
            elif ext in ['.html', '.htm', '.svg']: webbrowser.open(f'file://{abs_path}')
            elif ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.ico',
                         '.mp3', '.wav', '.ogg', '.aac', '.flac', '.m4a',
                         '.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv',
                         '.pdf', '.txt', '.md', '.log', '.csv', '.json', '.xml',
                         '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.odt', '.ods', '.odp']:
                if os.name == 'nt': os.startfile(abs_path)
                elif os.uname().sysname == 'Darwin': subprocess.Popen(['open', abs_path])
                else: subprocess.Popen(['xdg-open', abs_path])
            else: # Fallback
                if os.name == 'nt': os.startfile(abs_path)
                elif os.uname().sysname == 'Darwin': subprocess.Popen(['open', abs_path])
                else: subprocess.Popen(['xdg-open', abs_path])

        except Exception as e:
            print(f"Error launching {filepath}: {e}")
            messagebox.showerror("Launch Error", f"Could not open file: {os.path.basename(filepath)}\nError: {e}")


    def _terminate_process(self, filepath):
        if filepath in self.active_processes and self.active_processes[filepath]:
            proc = self.active_processes[filepath]
            print(f"Terminating: {os.path.basename(filepath)} (PID: {proc.pid})")
            try:
                proc.terminate() # SIGTERM
                proc.wait(timeout=0.5) # Wait a bit
            except subprocess.TimeoutExpired:
                print(f"Process {proc.pid} did not terminate gracefully, killing.")
                proc.kill() # SIGKILL
                proc.wait(timeout=0.5) # Wait for kill
            except Exception as e:
                print(f"Error terminating process {proc.pid}: {e}")
            finally:
                self.active_processes[filepath] = None
                for cfg in self.selected_file_configs: # Clear from config too
                    if cfg['path'] == filepath:
                        cfg['process'] = None
                        break

    def run_selected_files_handler(self):
        if self.is_running_sequence: # Stop existing sequence
            self.is_running_sequence = False # Signal to stop
            # Terminate all currently running Python scripts from this app
            for path in list(self.active_processes.keys()):
                self._terminate_process(path)
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

        # Warn if trying to close non-Python files (as we can't reliably do it)
        has_non_python_files = any(not cfg['path'].lower().endswith('.py') for cfg in selected_to_run_configs)
        if delay_seconds > 0 and len(selected_to_run_configs) > 1 and has_non_python_files:
             if not messagebox.askyesno("Limitation",
                                       "Multi-run with delay will attempt to close previous PYTHON scripts.\n"
                                       "Other file types (HTML, images, docs, etc.) opened by the OS default "
                                       "application CANNOT be automatically closed by this launcher.\n\n"
                                       "Do you want to proceed?", parent=self.root):
                return

        self.is_running_sequence = True
        order = self.run_order_var.get()
        loop = self.loop_behavior_var.get() == "loop"
        
        current_list = selected_to_run_configs[:] # Make a copy

        def launch_sequence(index=0):
            if not self.is_running_sequence: # Check if stop was signalled
                print("Sequence stopped by user.")
                return

            if order == "random" and index == 0: # Shuffle only at the beginning of a pass (or if not looping)
                random.shuffle(current_list)
            
            actual_index = index % len(current_list) # For looping

            if not current_list: # Should not happen if check at start
                self.is_running_sequence = False
                return

            config_to_run = current_list[actual_index]
            self.launch_file(config_to_run['path'], is_part_of_sequence=True) # Pass sequence flag

            next_index = index + 1
            if next_index < len(current_list) or loop:
                if delay_seconds > 0:
                    self.root.after(int(delay_seconds * 1000), lambda: launch_sequence(next_index))
                else: # No delay, launch immediately (careful with UI freeze)
                    self.root.after(10, lambda: launch_sequence(next_index)) # Small delay to allow UI update
            else: # Reached end, not looping
                self.is_running_sequence = False
                print("Finished sequence.")
                # Optionally, terminate the last Python script after a final delay or immediately
                # self.root.after(int(delay_seconds * 1000), lambda: self._terminate_process(config_to_run['path']) if config_to_run['path'].lower().endswith('.py') else None)


        launch_sequence()


    def toggle_all_checkboxes(self, state=True):
        for config in self.selected_file_configs:
            config['var'].set(state)

    def prompt_and_save_menu(self):
        if not self.selected_file_configs:
            messagebox.showerror("No Menu", "No menu to save.", parent=self.root)
            return

        new_menu_title = simpledialog.askstring("Menu Title", "Enter a title for your saved menu window:",
                                                initialvalue=self.current_menu_title.replace("Creator","").strip(), parent=self.root)
        if not new_menu_title: return

        py_filename_suggestion = "".join(c if c.isalnum() or c in ('_','-') else '_' for c in new_menu_title.lower().replace(" ", "_"))
        py_filename_suggestion = (py_filename_suggestion[:30] + ".py") if py_filename_suggestion else "saved_menu.py"

        py_filename = filedialog.asksaveasfilename(
            title="Save Menu Script As...", initialfile=py_filename_suggestion,
            defaultextension=".py", filetypes=[("Python files", "*.py")], parent=self.root
        )
        if not py_filename: return

        # Prepare data for generation: paths and their current styles
        storable_configs_for_script = []
        for config in self.selected_file_configs:
            storable_configs_for_script.append({
                'path': config['path'],
                'style': config['style'].copy() # Save the current style for initial load
            })
        
        # Pass current root background and title
        script_content = self._generate_menu_script_content(
            new_menu_title,
            storable_configs_for_script,
            self.current_root_bg, # Pass current root bg
            NUM_COLUMNS # Pass num columns
        )
        try:
            with open(py_filename, "w", encoding="utf-8") as f: f.write(script_content)
            messagebox.showinfo("Menu Saved", f"Menu script saved as:\n{py_filename}", parent=self.root)
        except Exception as e:
            messagebox.showerror("Save Error", f"Could not save menu script:\n{e}", parent=self.root)


    def _generate_menu_script_content(self, menu_title_str, file_configs_with_styles, root_bg_str, num_cols_int):
        # This function now generates a script that uses the same WhimsicalFileLauncherApp class!
        # The generated script will instantiate the class with is_generated_menu=True
        # and provide the initial configurations.

        # Need to make sure WHIMSICAL_COLORS, FONTS, RELIEF_STYLES, NUM_COLUMNS are defined in generated script
        # or accessible. Easiest to redefine them.

        script = f"""\
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog # Keep simpledialog for consistency if needed later
import os
import subprocess
import webbrowser
import random
import time
import sys

# --- START OF COPIED/REDEFINED CONSTANTS AND CLASSES ---
# These are needed for the WhimsicalFileLauncherApp to run standalone
WHIMSICAL_COLORS = {repr(WHIMSICAL_COLORS)}
WHIMSICAL_FONTS = {repr(WHIMSICAL_FONTS)}
RELIEF_STYLES = {repr(RELIEF_STYLES)}
NUM_COLUMNS = {num_cols_int} # Use the passed num_cols

# --- WhimsicalFileLauncherApp Class (Copied from original, slightly adapted) ---
# (Paste the entire WhimsicalFileLauncherApp class definition here)
# For brevity in this example, I'll assume it's pasted.
# IMPORTANT: The pasted class should NOT include the _generate_menu_script_content method
# or the prompt_and_save_menu method, as those are for the creator, not the generated menu.

# --- Start of Actual WhimsicalFileLauncherApp class for generated script ---
# (Imagine the full class from above is pasted here, with 'is_generated_menu' handling)
# For example, the __init__ would look like:
# class WhimsicalFileLauncherApp:
#    def __init__(self, root, is_generated_menu=False, initial_configs=None, initial_title="...", initial_root_bg=None):
#        # ... (all the init logic) ...
#        if not self.is_generated_menu: # This block would be skipped
#            self.select_button = ...
#            save_button = ...
#
#        # ... (rest of the class methods: _get_random_color, create_menu_ui, launch_file, etc.)
#        # Make sure methods like select_files_and_create_menu and prompt_and_save_menu are omitted or disabled
#        # if is_generated_menu is True.
#        # The original class is already designed to handle this with 'if not self.is_generated_menu:' checks.

# --- End of WhimsicalFileLauncherApp Class for generated script ---

# Use the WhimsicalFileLauncherApp class directly (copied here)
# <<< PASTE THE WhimsicalFileLauncherApp CLASS DEFINITION HERE >>>
# For this example, I will use a placeholder for the full class definition
# but in the real generated script, the actual class code would be here.

class WhimsicalFileLauncherApp:
    # Placeholder: In reality, this would be the full class definition from the main script,
    # modified slightly to ensure it runs as a generated menu (e.g., disabling save/select files).
    # The original class is already mostly suitable due to 'is_generated_menu' checks.
    # I will paste the full class here for completeness of the generated script.
    def __init__(self, root, is_generated_menu=False, initial_configs=None, initial_title="✨ Whimsical File Launcher Creator ✨", initial_root_bg=None):
        self.root = root
        self.is_generated_menu = is_generated_menu
        self.current_menu_title = initial_title
        self.root.title(self.current_menu_title)

        try: self.root.state('zoomed')
        except tk.TclError:
            try: self.root.attributes('-zoomed', True)
            except tk.TclError:
                self.root.geometry(f"{{self.root.winfo_screenwidth()}}x{{self.root.winfo_screenheight()}}+0+0")
        self.root.resizable(True, True)

        self.current_root_bg = initial_root_bg if initial_root_bg else self._get_random_color(light_bias=True)
        self.root.configure(bg=self.current_root_bg)

        self.selected_file_configs = [] 
        if is_generated_menu and initial_configs:
            for config_data in initial_configs:
                self.selected_file_configs.append({{
                    'path': config_data['path'],
                    'var': tk.BooleanVar(value=False),
                    'style': config_data['style'].copy(), 
                    'process': None
                }})

        self.menu_frame = None
        self.scrollable_frame_in_canvas = None
        self.active_processes = {{}}
        self.is_running_sequence = False

        self.title_label_frame = tk.Frame(self.root, bg=self.current_root_bg)
        self.title_label_frame.pack(pady=(10 if is_generated_menu else 0), fill=tk.X)
        self.title_label = tk.Label(self.title_label_frame, text=self.current_menu_title,
                                    font=(random.choice(WHIMSICAL_FONTS), 20, "bold"),
                                    bg=self._get_random_color(), fg=self._get_contrasting_color(self.current_root_bg))
        if is_generated_menu :
             self.title_label.pack(pady=5, padx=20)
        self._update_title_label_style()

        control_frame_bg = self._get_random_color(light_bias=True, avoid=self.current_root_bg)
        top_control_frame = tk.Frame(self.root, bg=control_frame_bg)
        top_control_frame.pack(pady=5, padx=10, fill=tk.X)

        left_controls = tk.Frame(top_control_frame, bg=control_frame_bg)
        left_controls.pack(side=tk.LEFT, padx=5)

        if not self.is_generated_menu: # This part will be FALSE in generated script
            self.select_button = tk.Button(left_controls, text="🌟 Select Files 🌟", command=self.select_files_and_create_menu)
            self.select_button.pack(side=tk.LEFT, pady=2)

        self.regenerate_button = tk.Button(
            left_controls, text="🎨 Re-Enchant Menu 🎨", command=lambda: self.create_menu_ui(preserve_styles=False),
            font=(random.choice(WHIMSICAL_FONTS), 13, "bold"), bg=self._get_random_color(),
            fg=self._get_contrasting_color(left_controls.cget("bg")), padx=8, pady=5,
            relief=random.choice(RELIEF_STYLES), borderwidth=random.randint(2, 3)
        )
        self.regenerate_button.pack(side=tk.LEFT, padx=(0 if self.is_generated_menu else 5, 0), pady=2) # Adjusted padding

        center_controls = tk.Frame(top_control_frame, bg=control_frame_bg)
        center_controls.pack(side=tk.LEFT, expand=True, fill=tk.X)
        multi_run_options_frame = tk.Frame(center_controls, bg=control_frame_bg)
        multi_run_options_frame.pack(pady=2)
        tk.Label(multi_run_options_frame, text="Delay(s):", bg=control_frame_bg, fg=self._get_contrasting_color(control_frame_bg), font=("Arial",9)).grid(row=0, column=0, padx=(0,2))
        self.duration_entry = tk.Entry(multi_run_options_frame, width=4, font=("Arial", 9))
        self.duration_entry.insert(0, "1")
        self.duration_entry.grid(row=0, column=1, padx=(0,5))
        self.run_order_var = tk.StringVar(value="order")
        tk.Radiobutton(multi_run_options_frame, text="In Order", variable=self.run_order_var, value="order", bg=control_frame_bg, fg=self._get_contrasting_color(control_frame_bg), selectcolor=self._get_random_color(light_bias=True), font=("Arial",9)).grid(row=0, column=2)
        tk.Radiobutton(multi_run_options_frame, text="Random", variable=self.run_order_var, value="random", bg=control_frame_bg, fg=self._get_contrasting_color(control_frame_bg), selectcolor=self._get_random_color(light_bias=True), font=("Arial",9)).grid(row=0, column=3, padx=(0,5))
        self.loop_behavior_var = tk.StringVar(value="once")
        tk.Radiobutton(multi_run_options_frame, text="Run Once", variable=self.loop_behavior_var, value="once", bg=control_frame_bg, fg=self._get_contrasting_color(control_frame_bg), selectcolor=self._get_random_color(light_bias=True), font=("Arial",9)).grid(row=0, column=4)
        tk.Radiobutton(multi_run_options_frame, text="Loop", variable=self.loop_behavior_var, value="loop", bg=control_frame_bg, fg=self._get_contrasting_color(control_frame_bg), selectcolor=self._get_random_color(light_bias=True), font=("Arial",9)).grid(row=0, column=5, padx=(0,5))
        run_selected_button = tk.Button(
            multi_run_options_frame, text="🚀 Run Selected", command=self.run_selected_files_handler,
            font=(random.choice(WHIMSICAL_FONTS), 11, "bold"), bg=self._get_random_color(),
            fg=self._get_contrasting_color(multi_run_options_frame.cget("bg")), padx=6, pady=3,
            relief=random.choice(RELIEF_STYLES), borderwidth=random.randint(2,3)
        )
        run_selected_button.grid(row=0, column=6, padx=(5,0))

        right_controls = tk.Frame(top_control_frame, bg=control_frame_bg)
        right_controls.pack(side=tk.RIGHT, padx=5)
        select_all_button = tk.Button(right_controls, text="Select All", command=lambda: self.toggle_all_checkboxes(True), font=("Arial",9,"bold"), bg="#AEDFF7", fg="black", padx=4, pady=1)
        select_all_button.pack(side=tk.LEFT, padx=2, pady=2)
        deselect_all_button = tk.Button(right_controls, text="Select None", command=lambda: self.toggle_all_checkboxes(False), font=("Arial",9,"bold"), bg="#FFC0CB", fg="black", padx=4, pady=1)
        deselect_all_button.pack(side=tk.LEFT, padx=2, pady=2)

        if not self.is_generated_menu: # This part will be FALSE
            save_button = tk.Button(right_controls, text="💾 Save Menu", command=self.prompt_and_save_menu)
            save_button.pack(side=tk.LEFT, padx=(5,0), pady=2)

        self.menu_display_area = tk.Frame(self.root, bg=self.current_root_bg)
        self.menu_display_area.pack(expand=True, fill=tk.BOTH, padx=5, pady=5)
        
        if self.is_generated_menu: 
            self.create_menu_ui(preserve_styles=True) # Preserve initial styles for generated menu

    def _update_title_label_style(self):
        if hasattr(self, 'title_label') and self.title_label.winfo_exists():
            bg_color = self._get_random_color()
            fg_color = self._get_contrasting_color(bg_color)
            font_family = random.choice(WHIMSICAL_FONTS)
            font_size = random.randint(18, 24) if self.is_generated_menu else random.randint(16, 20)
            self.title_label.config(text=self.current_menu_title,
                                    font=(font_family, font_size, "bold"),
                                    bg=bg_color, fg=fg_color)
        self.current_root_bg = self._get_random_color(light_bias=True)
        self.root.configure(bg=self.current_root_bg)
        if hasattr(self, 'menu_display_area') and self.menu_display_area.winfo_exists():
            self.menu_display_area.configure(bg=self.current_root_bg)
        if hasattr(self, 'title_label_frame') and self.title_label_frame.winfo_exists():
            self.title_label_frame.configure(bg=self.current_root_bg)

    def _get_random_color(self, light_bias=False, avoid=None):
        color = random.choice(WHIMSICAL_COLORS)
        if avoid:
            while color == avoid: color = random.choice(WHIMSICAL_COLORS)
        if light_bias:
            r,g,b = int(color[1:3],16),int(color[3:5],16),int(color[5:7],16)
            if (r+g+b)/3 < 128:
                for _ in range(3):
                    nc = random.choice(WHIMSICAL_COLORS)
                    nr,ng,nb = int(nc[1:3],16),int(nc[3:5],16),int(nc[5:7],16)
                    if (nr+ng+nb)/3 >= 128: return nc
        return color

    def _get_contrasting_color(self, bg_hex):
        try:
            r,g,b = int(bg_hex[1:3],16),int(bg_hex[3:5],16),int(bg_hex[5:7],16)
            return "#000000" if (0.299*r + 0.587*g + 0.114*b) > 128 else "#FFFFFF"
        except: return random.choice(["#000000", "#FFFFFF"])

    # select_files_and_create_menu is NOT needed in generated script
    # def select_files_and_create_menu(self): ...

    def create_menu_ui(self, preserve_styles=False):
        if not self.selected_file_configs:
            if not self.is_generated_menu:
                 messagebox.showinfo("No Files", "No files selected to create a menu.")
            return

        if self.menu_frame: self.menu_frame.destroy()
        for widget in self.menu_display_area.winfo_children(): widget.destroy()
        if not preserve_styles: # If not preserving (i.e. re-enchant), update title/root
            self._update_title_label_style()

        menu_frame_bg = self._get_random_color(light_bias=True, avoid=self.current_root_bg)
        self.menu_frame = tk.Frame(self.menu_display_area, bg=menu_frame_bg)
        self.menu_frame.pack(expand=True, fill=tk.BOTH, padx=5, pady=5)
        canvas_bg = self._get_random_color(light_bias=True, avoid=menu_frame_bg)
        canvas = tk.Canvas(self.menu_frame, bg=canvas_bg, highlightthickness=0)
        scrollbar = tk.Scrollbar(self.menu_frame, orient="vertical", command=canvas.yview)
        self.scrollable_frame_in_canvas = tk.Frame(canvas, bg=canvas_bg)
        self.scrollable_frame_in_canvas.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0,0), window=self.scrollable_frame_in_canvas, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        def _on_mw(e): canvas.yview_scroll(int(-1*(e.delta/120)), "units")
        def _on_mw_l(e): canvas.yview_scroll(-1 if e.num==4 else 1, "units")
        canvas.bind_all("<MouseWheel>", _on_mw); canvas.bind_all("<Button-4>", _on_mw_l); canvas.bind_all("<Button-5>", _on_mw_l)
        canvas.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        scrollbar.pack(side="right", fill="y")
        self.scrollable_frame_in_canvas.grid_columnconfigure(0, weight=1)
        for i in range(NUM_COLUMNS): self.scrollable_frame_in_canvas.grid_columnconfigure(i + 1, weight=1)
        self.scrollable_frame_in_canvas.grid_columnconfigure(NUM_COLUMNS + 1, weight=1)
        row = 0
        for i, config in enumerate(self.selected_file_configs):
            if not preserve_styles or not config.get('style') or not config['style'].get('bg'):
                style = {{'bg':self._get_random_color(),'font_family':random.choice(WHIMSICAL_FONTS),'font_size':random.randint(10,14),'relief':random.choice(RELIEF_STYLES),'borderwidth':random.randint(1,3),'padx':random.randint(6,10),'pady':random.randint(3,6),'text':os.path.basename(config['path'])}}
                style['fg']=self._get_contrasting_color(style['bg']); style['activebackground']=self._get_random_color(avoid=style['bg']); style['activeforeground']=self._get_contrasting_color(style['activebackground'])
                config['style'] = style
            item_style = config['style']
            actual_col = (i % NUM_COLUMNS) + 1
            if i % NUM_COLUMNS == 0 and i != 0: row += 1
            item_f = tk.Frame(self.scrollable_frame_in_canvas, bg=self.scrollable_frame_in_canvas.cget("bg"))
            item_f.grid(row=row, column=actual_col, padx=3, pady=3, sticky="ew")
            tk.Checkbutton(item_f, variable=config['var'], bg=item_f.cget("bg"), activebackground=item_f.cget("bg")).pack(side=tk.LEFT,padx=(0,1))
            btn_txt = item_style['text']; btn_txt = btn_txt[:9]+"..."+btn_txt[-9:] if len(btn_txt)>20 else btn_txt
            try:
                tk.Button(item_f,text=btn_txt,command=lambda p=config['path']:self.launch_file(p),bg=item_style['bg'],fg=item_style['fg'],font=(item_style['font_family'],item_style['font_size']),relief=item_style['relief'],borderwidth=item_style['borderwidth'],padx=item_style['padx'],pady=item_style['pady'],activebackground=item_style['activebackground'],activeforeground=item_style['activeforeground'],width=12).pack(side=tk.LEFT,fill=tk.X,expand=True)
            except tk.TclError:
                tk.Button(item_f,text=btn_txt,command=lambda p=config['path']:self.launch_file(p),bg=item_style['bg'],fg=item_style['fg'],font=("Arial",10),width=12).pack(side=tk.LEFT,fill=tk.X,expand=True)
        self.root.after(50, lambda: canvas.create_window((canvas.winfo_width()//2, 0), window=self.scrollable_frame_in_canvas, anchor="n") if canvas.winfo_exists() else None)


    def launch_file(self, filepath, is_part_of_sequence=False):
        _, ext = os.path.splitext(filepath); ext=ext.lower(); abs_path=os.path.abspath(filepath)
        if is_part_of_sequence:
            for p_path, proc_obj in list(self.active_processes.items()):
                if proc_obj is not None and proc_obj.poll() is not None: del self.active_processes[p_path]
            prev_py_scripts = [p for p,proc in self.active_processes.items() if proc and p.lower().endswith('.py')]
            for prev_py_path in prev_py_scripts:
                if prev_py_path != filepath: self._terminate_process(prev_py_path)
        try:
            process_obj = None
            if ext == '.py':
                py_exe = sys.executable if sys.executable else "python"
                if os.name == 'nt': process_obj = subprocess.Popen([py_exe, abs_path], creationflags=subprocess.CREATE_NEW_CONSOLE)
                elif os.uname().sysname == 'Darwin': process_obj = subprocess.Popen([py_exe, abs_path])
                else:
                    try: process_obj = subprocess.Popen(['x-terminal-emulator', '-e', py_exe, abs_path])
                    except FileNotFoundError:
                        try: process_obj = subprocess.Popen(['gnome-terminal', '--', py_exe, abs_path])
                        except FileNotFoundError:
                             try: process_obj = subprocess.Popen(['konsole', '-e', py_exe, abs_path])
                             except FileNotFoundError: process_obj = subprocess.Popen([py_exe, abs_path])
                if process_obj:
                    self.active_processes[filepath] = process_obj
                    for cfg in self.selected_file_configs:
                        if cfg['path'] == filepath: cfg['process'] = process_obj; break
            elif ext in ['.html','.htm','.svg']: webbrowser.open(f'file://{{abs_path}}')
            elif ext in ['.jpg','.jpeg','.png','.gif','.bmp','.webp','.ico','.mp3','.wav','.ogg','.aac','.flac','.m4a','.mp4','.avi','.mkv','.mov','.wmv','.flv','.pdf','.txt','.md','.log','.csv','.json','.xml','.doc','.docx','.xls','.xlsx','.ppt','.pptx','.odt','.ods','.odp']:
                if os.name=='nt': os.startfile(abs_path)
                elif os.uname().sysname=='Darwin': subprocess.Popen(['open',abs_path])
                else: subprocess.Popen(['xdg-open',abs_path])
            else:
                if os.name=='nt': os.startfile(abs_path)
                elif os.uname().sysname=='Darwin': subprocess.Popen(['open',abs_path])
                else: subprocess.Popen(['xdg-open',abs_path])
        except Exception as e: messagebox.showerror("Launch Error", f"Could not open file: {{os.path.basename(filepath)}}\\nError: {{e}}")

    def _terminate_process(self, filepath):
        if filepath in self.active_processes and self.active_processes[filepath]:
            proc = self.active_processes[filepath]
            try:
                proc.terminate(); proc.wait(timeout=0.5)
            except subprocess.TimeoutExpired: proc.kill(); proc.wait(timeout=0.5)
            except Exception: pass
            finally:
                self.active_processes[filepath] = None
                for cfg in self.selected_file_configs:
                    if cfg['path']==filepath: cfg['process']=None; break

    def run_selected_files_handler(self):
        if self.is_running_sequence:
            self.is_running_sequence = False
            for path in list(self.active_processes.keys()): self._terminate_process(path)
            messagebox.showinfo("Stopped", "Multi-run sequence stopped.", parent=self.root)
            return
        selected_cfgs = [c for c in self.selected_file_configs if c['var'].get()]
        if not selected_cfgs: messagebox.showinfo("Nothing Selected","Please check files.",parent=self.root); return
        try: delay_s = float(self.duration_entry.get()); delay_s = 0 if delay_s < 0 else delay_s
        except ValueError: messagebox.showerror("Invalid Delay","Enter valid delay.",parent=self.root); return
        has_non_py = any(not c['path'].lower().endswith('.py') for c in selected_cfgs)
        if delay_s > 0 and len(selected_cfgs) > 1 and has_non_py:
            if not messagebox.askyesno("Limitation","Multi-run closes PYTHON scripts only. Other types (HTML, etc.) CANNOT be auto-closed. Proceed?",parent=self.root): return
        self.is_running_sequence = True
        order, loop = self.run_order_var.get(), self.loop_behavior_var.get() == "loop"
        current_l = selected_cfgs[:]
        def launch_seq(idx=0):
            if not self.is_running_sequence: return
            if order=="random" and idx==0: random.shuffle(current_l)
            actual_idx = idx % len(current_l)
            if not current_l: self.is_running_sequence=False; return
            cfg_to_run = current_l[actual_idx]
            self.launch_file(cfg_to_run['path'], is_part_of_sequence=True)
            next_idx = idx + 1
            if next_idx < len(current_l) or loop:
                self.root.after(int(delay_s*1000) if delay_s > 0 else 10, lambda: launch_seq(next_idx))
            else: self.is_running_sequence=False
        launch_seq()

    def toggle_all_checkboxes(self, state=True):
        for config in self.selected_file_configs: config['var'].set(state)

    # prompt_and_save_menu is NOT needed in generated script
    # def prompt_and_save_menu(self): ...
    # _generate_menu_script_content is NOT needed
    # def _generate_menu_script_content(self, ...): ...


# --- Script Entry Point for the Saved Menu ---
if __name__ == "__main__":
    SAVED_MENU_TITLE_STR = {repr(menu_title_str)}
    SAVED_FILE_CONFIGS_DATA = {repr(file_configs_with_styles)} # Paths and their initial styles
    INITIAL_ROOT_BG_STR = {repr(root_bg_str)}

    root = tk.Tk()
    # Instantiate with is_generated_menu=True and the saved data
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
    creator_app = WhimsicalFileLauncherApp(main_creator_root) # Default: is_generated_menu=False
    main_creator_root.mainloop()