import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import os
import subprocess
import webbrowser
import random
import time # For delays in multi-run

# Whimsical color palettes (background, foreground pairs or general use)
WHIMSICAL_COLORS = [
    "#FFADAD", "#FFD6A5", "#FDFFB6", "#CAFFBF", "#9BF6FF", "#A0C4FF", "#BDB2FF", "#FFC6FF",
    "#FFB3BA", "#FFDFBA", "#FFFFBA", "#BAFFC9", "#BAE1FF", "#E0BBE4", "#FEC8D8", "#FFDFD3",
    "#D16BA5", "#86A8E7", "#5FFBF1", "#A267AC", "#F67280", "#C06C84", "#6C5B7B", "#355C7D"
]

# Whimsical font families (ensure these are commonly available or provide fallbacks)
WHIMSICAL_FONTS = [
    "Comic Sans MS", "Papyrus", "Curlz MT", "Kristen ITC",
    "Arial", "Verdana", "Helvetica" # Fallbacks
]

# Button relief styles
RELIEF_STYLES = [tk.RAISED, tk.SUNKEN, tk.GROOVE, tk.RIDGE, tk.FLAT]

NUM_COLUMNS = 3 # Number of columns for the button grid

class WhimsicalFileLauncherApp:
    def __init__(self, root):
        self.root = root
        self.root.title("✨ Whimsical File Launcher Creator ✨")

        try:
            self.root.state('zoomed')
        except tk.TclError:
            try:
                self.root.attributes('-zoomed', True)
            except tk.TclError:
                width = self.root.winfo_screenwidth()
                height = self.root.winfo_screenheight()
                self.root.geometry(f"{width}x{height}+0+0")

        self.root.resizable(True, True)
        self.root.configure(bg=self._get_random_color(light_bias=True))

        self.selected_file_configs = [] # List of dicts: {'path': str, 'var': tk.BooleanVar, 'style': dict}
        self.menu_frame = None
        self.scrollable_frame_in_canvas = None # To hold grid items

        # --- Top Control Frame ---
        top_control_frame = tk.Frame(self.root, bg=self._get_random_color(light_bias=True, avoid=self.root.cget("bg")))
        top_control_frame.pack(pady=10, padx=10, fill=tk.X)

        self.select_button = tk.Button(
            top_control_frame, text="🌟 Select Files 🌟", command=self.select_files_and_create_menu,
            font=(random.choice(WHIMSICAL_FONTS), 14, "bold"), bg=self._get_random_color(),
            fg=self._get_contrasting_color(top_control_frame.cget("bg")), padx=10, pady=7,
            relief=random.choice(RELIEF_STYLES), borderwidth=random.randint(2, 4)
        )
        self.select_button.pack(side=tk.LEFT, padx=5)

        regenerate_button = tk.Button(
            top_control_frame, text="🎨 Re-Enchant Menu 🎨", command=self.create_menu_ui,
            font=(random.choice(WHIMSICAL_FONTS), 14, "bold"), bg=self._get_random_color(),
            fg=self._get_contrasting_color(top_control_frame.cget("bg")), padx=10, pady=7,
            relief=random.choice(RELIEF_STYLES), borderwidth=random.randint(2, 4)
        )
        regenerate_button.pack(side=tk.LEFT, padx=5)

        # --- Multi-Run Controls ---
        multi_run_frame = tk.Frame(top_control_frame, bg=top_control_frame.cget("bg"))
        multi_run_frame.pack(side=tk.LEFT, padx=10)

        tk.Label(multi_run_frame, text="Delay (s):", bg=top_control_frame.cget("bg"),
                 fg=self._get_contrasting_color(top_control_frame.cget("bg")),
                 font=(random.choice(WHIMSICAL_FONTS), 10)).pack(side=tk.LEFT)
        self.duration_entry = tk.Entry(multi_run_frame, width=5, font=("Arial", 10))
        self.duration_entry.insert(0, "1") # Default 1 second delay
        self.duration_entry.pack(side=tk.LEFT, padx=(0,5))

        run_selected_button = tk.Button(
            multi_run_frame, text="🚀 Run Selected w/ Delay", command=self.run_selected_files,
            font=(random.choice(WHIMSICAL_FONTS), 12, "bold"), bg=self._get_random_color(),
            fg=self._get_contrasting_color(multi_run_frame.cget("bg")), padx=8, pady=5,
            relief=random.choice(RELIEF_STYLES), borderwidth=random.randint(2,3)
        )
        run_selected_button.pack(side=tk.LEFT)

        # --- Save Menu Button ---
        save_button = tk.Button(
            top_control_frame, text="💾 Save This Menu 💾", command=self.prompt_and_save_menu,
            font=(random.choice(WHIMSICAL_FONTS), 14, "bold"), bg="#77DD77", fg="#000000",
            padx=10, pady=7, relief=tk.RAISED, borderwidth=3
        )
        save_button.pack(side=tk.RIGHT, padx=5)


        # --- Menu Display Area ---
        self.menu_display_area = tk.Frame(self.root, bg=self.root.cget("bg"))
        self.menu_display_area.pack(expand=True, fill=tk.BOTH, padx=5, pady=5)

    def _get_random_color(self, light_bias=False, avoid=None):
        # (Same as before)
        color = random.choice(WHIMSICAL_COLORS)
        if avoid:
            while color == avoid:
                color = random.choice(WHIMSICAL_COLORS)
        if light_bias:
            r, g, b = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)
            if (r + g + b) / 3 < 128:
                for _ in range(3):
                    new_color = random.choice(WHIMSICAL_COLORS)
                    nr, ng, nb = int(new_color[1:3], 16), int(new_color[3:5], 16), int(new_color[5:7], 16)
                    if (nr + ng + nb) / 3 >= 128: return new_color
        return color

    def _get_contrasting_color(self, bg_color_hex):
        # (Same as before)
        try:
            r = int(bg_color_hex[1:3], 16); g = int(bg_color_hex[3:5], 16); b = int(bg_color_hex[5:7], 16)
            brightness = (0.299 * r + 0.587 * g + 0.114 * b)
            return "#000000" if brightness > 128 else "#FFFFFF"
        except: return random.choice(["#000000", "#FFFFFF"])

    def select_files_and_create_menu(self):
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
                    'path': f_path,
                    'var': tk.BooleanVar(value=False), # Checkbox variable
                    'style': {} # Will be populated in create_menu_ui
                })
            self.create_menu_ui()
        elif not self.selected_file_configs:
             if self.menu_frame: self.menu_frame.destroy(); self.menu_frame = None
             for widget in self.menu_display_area.winfo_children(): widget.destroy() # Clear old "no files"
             no_files_label = tk.Label(self.menu_display_area, text="No files selected. The magic awaits!",
                                       font=("Comic Sans MS", 18), bg=self.menu_display_area.cget("bg"),
                                       fg=self._get_contrasting_color(self.menu_display_area.cget("bg")))
             no_files_label.pack(expand=True)
             self.root.after(3000, lambda: no_files_label.destroy() if no_files_label.winfo_exists() else None)

    def create_menu_ui(self):
        if not self.selected_file_configs:
            messagebox.showinfo("No Files", "No files selected to create a menu. Please select some files first!")
            return

        if self.menu_frame: self.menu_frame.destroy()
        for widget in self.menu_display_area.winfo_children(): widget.destroy()

        self.root.configure(bg=self._get_random_color(light_bias=True))
        self.menu_display_area.configure(bg=self.root.cget("bg"))
        self.menu_frame = tk.Frame(self.menu_display_area, bg=self._get_random_color(light_bias=True, avoid=self.root.cget("bg")))
        self.menu_frame.pack(expand=True, fill=tk.BOTH, padx=5, pady=5)

        canvas = tk.Canvas(self.menu_frame, bg=self.menu_frame.cget("bg"), highlightthickness=0)
        scrollbar = tk.Scrollbar(self.menu_frame, orient="vertical", command=canvas.yview)
        self.scrollable_frame_in_canvas = tk.Frame(canvas, bg=self.menu_frame.cget("bg"))

        self.scrollable_frame_in_canvas.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.scrollable_frame_in_canvas, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Mouse wheel scrolling for canvas
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units") # For Windows/macOS
        def _on_mousewheel_linux(event):
            if event.num == 4: # Scroll up
                canvas.yview_scroll(-1, "units")
            elif event.num == 5: # Scroll down
                canvas.yview_scroll(1, "units")

        canvas.bind_all("<MouseWheel>", _on_mousewheel) # For Windows and macOS
        canvas.bind_all("<Button-4>", _on_mousewheel_linux) # For Linux
        canvas.bind_all("<Button-5>", _on_mousewheel_linux) # For Linux

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        row, col = 0, 0
        for i, config in enumerate(self.selected_file_configs):
            filepath = config['path']
            filename = os.path.basename(filepath)
            
            # Generate and store style if not already generated (e.g., by regenerate)
            if not config.get('style') or not config['style'].get('bg'): # Check if style needs generation
                style = {
                    'bg': self._get_random_color(),
                    'font_family': random.choice(WHIMSICAL_FONTS),
                    'font_size': random.randint(11, 16),
                    'relief': random.choice(RELIEF_STYLES),
                    'borderwidth': random.randint(2, 4),
                    'padx': random.randint(7, 12),
                    'pady': random.randint(4, 8),
                    'text': f"{filename}" # Keep text short for grid
                }
                style['fg'] = self._get_contrasting_color(style['bg'])
                style['activebackground'] = self._get_random_color(avoid=style['bg'])
                style['activeforeground'] = self._get_contrasting_color(style['activebackground'])
                config['style'] = style
            
            item_style = config['style']

            # Frame to hold checkbox and button for consistent gridding
            item_frame = tk.Frame(self.scrollable_frame_in_canvas, bg=self.scrollable_frame_in_canvas.cget("bg"))
            item_frame.grid(row=row, column=col, padx=5, pady=5, sticky="ew")
            self.scrollable_frame_in_canvas.grid_columnconfigure(col, weight=1)


            chk = tk.Checkbutton(item_frame, variable=config['var'], bg=item_frame.cget("bg"))
            chk.pack(side=tk.LEFT, padx=(0,2))

            try:
                btn_text = item_style['text']
                if len(btn_text) > 25: # Truncate very long names
                    btn_text = btn_text[:10] + "..." + btn_text[-10:]

                btn = tk.Button(
                    item_frame, text=btn_text, command=lambda p=filepath: self.launch_file(p),
                    bg=item_style['bg'], fg=item_style['fg'],
                    font=(item_style['font_family'], item_style['font_size'], "bold"),
                    relief=item_style['relief'], borderwidth=item_style['borderwidth'],
                    padx=item_style['padx'], pady=item_style['pady'],
                    activebackground=item_style['activebackground'],
                    activeforeground=item_style['activeforeground'],
                    width=15 # Give some base width
                )
                btn.pack(side=tk.LEFT, fill=tk.X, expand=True)
            except tk.TclError as e: # Font fallback
                print(f"Warning: Font '{item_style['font_family']}' issue. Using default. Error: {e}")
                btn = tk.Button(item_frame, text=item_style['text'], command=lambda p=filepath: self.launch_file(p),
                                bg=item_style['bg'], fg=item_style['fg'], font=("Arial", 12, "bold"),
                                relief=item_style['relief'], borderwidth=item_style['borderwidth'],
                                padx=item_style['padx'], pady=item_style['pady'], width=15)
                btn.pack(side=tk.LEFT, fill=tk.X, expand=True)

            col += 1
            if col >= NUM_COLUMNS:
                col = 0
                row += 1
        
        # Configure row weights if you want them to expand vertically
        # for r in range(row + 1):
        #    self.scrollable_frame_in_canvas.grid_rowconfigure(r, weight=1)


    def launch_file(self, filepath):
        # (Same as before, but ensure abs_path is used consistently)
        try:
            _, ext = os.path.splitext(filepath)
            ext = ext.lower()
            abs_path = os.path.abspath(filepath)

            print(f"Launching: {abs_path} (ext: {ext})")

            if ext == '.py':
                if os.name == 'nt':
                    subprocess.Popen(['start', 'cmd', '/k', 'python', abs_path], shell=True)
                elif os.uname().sysname == 'Darwin':
                    subprocess.Popen(['open', '-a', 'Terminal', abs_path]) # Attempt to open with Terminal
                                                                          # Or, more complex AppleScript via osascript
                                                                          # Fallback: subprocess.Popen(['python3', abs_path])
                else:
                    try: subprocess.Popen(['x-terminal-emulator', '-e', 'python3', abs_path])
                    except FileNotFoundError:
                        try: subprocess.Popen(['gnome-terminal', '--', 'python3', abs_path])
                        except FileNotFoundError:
                            try: subprocess.Popen(['konsole', '-e', 'python3', abs_path])
                            except FileNotFoundError: subprocess.Popen(['python3', abs_path])
            elif ext in ['.html', '.htm', '.svg']:
                webbrowser.open(f'file://{abs_path}')
            elif ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.ico',
                         '.mp3', '.wav', '.ogg', '.aac', '.flac', '.m4a',
                         '.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv',
                         '.pdf', '.txt', '.md', '.log', '.csv', '.json', '.xml',
                         '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.odt', '.ods', '.odp']:
                if os.name == 'nt': os.startfile(abs_path)
                elif os.uname().sysname == 'Darwin': subprocess.Popen(['open', abs_path])
                else: subprocess.Popen(['xdg-open', abs_path])
            else:
                if os.name == 'nt': os.startfile(abs_path)
                elif os.uname().sysname == 'Darwin': subprocess.Popen(['open', abs_path])
                else: subprocess.Popen(['xdg-open', abs_path])
        except FileNotFoundError as e:
            print(f"Error launching {filepath}: Command not found or file association error. {e}")
            messagebox.showerror("Launch Error", f"Could not find a program to open: {os.path.basename(filepath)}\nEnsure default program or command in PATH.")
        except Exception as e:
            print(f"Error launching {filepath}: {e}")
            messagebox.showerror("Launch Error", f"Could not open file: {os.path.basename(filepath)}\nError: {e}")

    def run_selected_files(self):
        selected_to_run = [config['path'] for config in self.selected_file_configs if config['var'].get()]
        if not selected_to_run:
            messagebox.showinfo("Nothing Selected", "Please check the boxes next to the files you want to run.")
            return

        try:
            duration_str = self.duration_entry.get()
            delay_seconds = float(duration_str)
            if delay_seconds < 0: delay_seconds = 0
        except ValueError:
            messagebox.showerror("Invalid Delay", "Please enter a valid number for the delay duration (e.g., 0.5, 1, 2).")
            return

        def launch_next(index=0):
            if index < len(selected_to_run):
                self.launch_file(selected_to_run[index])
                if index + 1 < len(selected_to_run) and delay_seconds > 0:
                    self.root.after(int(delay_seconds * 1000), lambda: launch_next(index + 1))
                elif index + 1 < len(selected_to_run): # delay is 0 or less
                    launch_next(index + 1) # Launch immediately
        
        launch_next()

    def prompt_and_save_menu(self):
        if not self.selected_file_configs:
            messagebox.showerror("No Menu", "There's no menu to save. Please select files first.")
            return

        menu_title = simpledialog.askstring("Menu Title", "Enter a title for your saved menu window:", parent=self.root)
        if not menu_title: return # User cancelled

        py_filename_suggestion = "".join(c if c.isalnum() or c in ('_','-') else '_' for c in menu_title.lower().replace(" ", "_"))
        py_filename_suggestion = py_filename_suggestion[:30] + ".py" if py_filename_suggestion else "saved_menu.py"

        py_filename = filedialog.asksaveasfilename(
            title="Save Menu Script As...",
            initialfile=py_filename_suggestion,
            defaultextension=".py",
            filetypes=[("Python files", "*.py"), ("All files", "*.*")],
            parent=self.root
        )
        if not py_filename: return # User cancelled

        # Check for overwrite (Tkinter's asksaveasfilename usually handles this, but good to be sure or if non-Tk dialog)
        # For this implementation, asksaveasfilename will prompt if file exists.
        # If we wanted our own non-overwrite logic:
        # base, ext = os.path.splitext(py_filename)
        # counter = 1
        # while os.path.exists(py_filename):
        #     py_filename = f"{base}_{counter}{ext}"
        #     counter += 1

        script_content = self._generate_menu_script_content(menu_title, self.selected_file_configs)
        try:
            with open(py_filename, "w", encoding="utf-8") as f:
                f.write(script_content)
            messagebox.showinfo("Menu Saved", f"Menu script saved as:\n{py_filename}", parent=self.root)
        except Exception as e:
            messagebox.showerror("Save Error", f"Could not save the menu script:\n{e}", parent=self.root)


    def _generate_menu_script_content(self, menu_title, file_configs_data):
        # Prepare file_configs_data for string representation (it contains tk.BooleanVar)
        # We only need path and style for the generated script.
        storable_configs = []
        for config in file_configs_data:
            storable_configs.append({
                'path': config['path'], # Ensure paths are absolute for robustness
                'style': config['style']
            })

        # The launch_file function needs to be part of the generated script.
        # We'll embed its definition directly.
        # Also, _get_contrasting_color might be useful if the saved menu has active colors.
        
        # We need to be careful with string formatting, especially for paths
        # Using repr() for paths can help with backslashes on Windows.
        
        script = f"""\
import tkinter as tk
from tkinter import messagebox # For potential errors in launched script
import os
import subprocess
import webbrowser
import random # Only if generated menu itself will have random elements on regenerate

# --- Configuration for the Saved Menu ---
SAVED_MENU_TITLE = {repr(menu_title)}
SAVED_FILE_CONFIGS = {repr(storable_configs)} # repr() handles escaping in strings
NUM_COLUMNS_SAVED = {NUM_COLUMNS} # Use the same number of columns

# --- Helper function(s) needed by the saved menu ---
def _get_contrasting_color_saved(bg_color_hex):
    try:
        r = int(bg_color_hex[1:3], 16); g = int(bg_color_hex[3:5], 16); b = int(bg_color_hex[5:7], 16)
        brightness = (0.299 * r + 0.587 * g + 0.114 * b)
        return "#000000" if brightness > 128 else "#FFFFFF"
    except: return random.choice(["#000000", "#FFFFFF"]) # Fallback

# --- File Launch Logic (copied from main app) ---
def launch_file_saved(filepath):
    try:
        _, ext = os.path.splitext(filepath)
        ext = ext.lower()
        abs_path = os.path.abspath(filepath) # Already absolute from main app, but good practice

        print(f"Launching from saved menu: {{abs_path}} (ext: {{ext}})")

        if ext == '.py':
            if os.name == 'nt':
                subprocess.Popen(['start', 'cmd', '/k', 'python', abs_path], shell=True)
            elif os.uname().sysname == 'Darwin':
                subprocess.Popen(['open', '-a', 'Terminal', abs_path])
            else:
                try: subprocess.Popen(['x-terminal-emulator', '-e', 'python3', abs_path])
                except FileNotFoundError:
                    try: subprocess.Popen(['gnome-terminal', '--', 'python3', abs_path])
                    except FileNotFoundError:
                        try: subprocess.Popen(['konsole', '-e', 'python3', abs_path])
                        except FileNotFoundError: subprocess.Popen(['python3', abs_path])
        elif ext in ['.html', '.htm', '.svg']:
            webbrowser.open(f'file://{{abs_path}}')
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
    except FileNotFoundError as e:
        print(f"Error launching {{filepath}}: Command not found or file association error. {{e}}")
        messagebox.showerror("Launch Error", f"Could not find a program to open: {{os.path.basename(filepath)}}\\nEnsure default program or command in PATH.")
    except Exception as e:
        print(f"Error launching {{filepath}}: {{e}}")
        messagebox.showerror("Launch Error", f"Could not open file: {{os.path.basename(filepath)}}\\nError: {{e}}")

# --- Main Application for the Saved Menu ---
def run_saved_menu():
    root = tk.Tk()
    root.title(SAVED_MENU_TITLE)
    
    # Attempt to start maximized (optional, but consistent with original)
    try: root.state('zoomed')
    except tk.TclError:
        try: root.attributes('-zoomed', True)
        except tk.TclError: 
            sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
            root.geometry(f"{{sw}}x{{sh}}+0+0")
    root.resizable(True, True)

    # Overall background for the saved menu (can be fixed or random from a limited palette)
    # For now, let's pick one from the original whimsical list if available, or a default
    saved_menu_bg_colors = {repr(WHIMSICAL_COLORS)} # Embed the list
    root.configure(bg=random.choice(saved_menu_bg_colors) if saved_menu_bg_colors else "#ECECEC")

    # Display the Menu Title at the top
    title_label_bg = random.choice(saved_menu_bg_colors) if saved_menu_bg_colors else "#D0D0D0"
    title_label_fg = _get_contrasting_color_saved(title_label_bg)
    title_font_families = {repr(WHIMSICAL_FONTS)} # Embed the list
    title_font = (random.choice(title_font_families) if title_font_families else "Arial", 18, "bold")
    
    menu_header_frame = tk.Frame(root, bg=root.cget("bg"))
    menu_header_frame.pack(pady=10, fill=tk.X)
    
    tk.Label(menu_header_frame, text=SAVED_MENU_TITLE, font=title_font, 
             bg=title_label_bg, fg=title_label_fg, padx=10, pady=10).pack(expand=True)

    # Frame for the scrollable buttons
    menu_display_area = tk.Frame(root, bg=root.cget("bg"))
    menu_display_area.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)

    canvas = tk.Canvas(menu_display_area, bg=random.choice(saved_menu_bg_colors) if saved_menu_bg_colors else "#F0F0F0", highlightthickness=0)
    scrollbar = tk.Scrollbar(menu_display_area, orient="vertical", command=canvas.yview)
    scrollable_frame = tk.Frame(canvas, bg=canvas.cget("bg"))

    scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    def _on_mousewheel_saved(event): canvas.yview_scroll(int(-1*(event.delta/120)), "units")
    def _on_mousewheel_linux_saved(event):
        if event.num == 4: canvas.yview_scroll(-1, "units")
        elif event.num == 5: canvas.yview_scroll(1, "units")
    canvas.bind_all("<MouseWheel>", _on_mousewheel_saved)
    canvas.bind_all("<Button-4>", _on_mousewheel_linux_saved)
    canvas.bind_all("<Button-5>", _on_mousewheel_linux_saved)
    
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    row, col = 0, 0
    for config in SAVED_FILE_CONFIGS:
        filepath = config['path']
        style = config['style']
        
        # Here we don't need checkbox, just the button for the saved menu
        # If you want checkboxes in the saved menu too, you'd add them.
        # For simplicity, the saved menu just has direct launch buttons.

        btn_text = style.get('text', os.path.basename(filepath))
        if len(btn_text) > 25: btn_text = btn_text[:10] + "..." + btn_text[-10:]

        try:
            btn = tk.Button(
                scrollable_frame, text=btn_text, command=lambda p=filepath: launch_file_saved(p),
                bg=style.get('bg', '#DDDDDD'), fg=style.get('fg', '#000000'),
                font=(style.get('font_family','Arial'), style.get('font_size', 12), "bold"),
                relief=style.get('relief', tk.RAISED), borderwidth=style.get('borderwidth',2),
                padx=style.get('padx',5), pady=style.get('pady',3),
                activebackground=style.get('activebackground', '#CCCCCC'),
                activeforeground=style.get('activeforeground', '#000000'),
                width=15 # Base width
            )
            btn.grid(row=row, column=col, padx=7, pady=7, sticky="ewns") # Use sticky to fill cell
            scrollable_frame.grid_columnconfigure(col, weight=1) # Make columns expand
            # scrollable_frame.grid_rowconfigure(row, weight=1) # Make rows expand if desired

        except tk.TclError as e: # Font fallback
            print(f"Warning: Font '{{style.get('font_family','Arial')}}' issue. Using default. Error: {{e}}")
            btn = tk.Button(scrollable_frame, text=btn_text, command=lambda p=filepath: launch_file_saved(p),
                            font=("Arial", 12, "bold"))
            btn.grid(row=row, column=col, padx=7, pady=7, sticky="ewns")

        col += 1
        if col >= NUM_COLUMNS_SAVED:
            col = 0
            row += 1
            
    root.mainloop()

if __name__ == "__main__":
    run_saved_menu()
"""
        return script


if __name__ == "__main__":
    root = tk.Tk()
    app = WhimsicalFileLauncherApp(root)
    root.mainloop()