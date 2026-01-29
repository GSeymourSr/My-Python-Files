import tkinter as tk
from tkinter import filedialog, messagebox
import os
import subprocess
import webbrowser
import random

# Whimsical color palettes (background, foreground pairs or general use)
# You can expand this list with more color hex codes
WHIMSICAL_COLORS = [
    # Pastels & Brights
    "#FFADAD", "#FFD6A5", "#FDFFB6", "#CAFFBF", "#9BF6FF", "#A0C4FF", "#BDB2FF", "#FFC6FF",
    "#FFB3BA", "#FFDFBA", "#FFFFBA", "#BAFFC9", "#BAE1FF", "#E0BBE4", "#FEC8D8", "#FFDFD3",
    # Some darker shades for text or contrast
    "#D16BA5", "#86A8E7", "#5FFBF1", "#A267AC", "#F67280", "#C06C84", "#6C5B7B", "#355C7D"
]

# Whimsical font families (ensure these are commonly available or provide fallbacks)
WHIMSICAL_FONTS = [
    "Comic Sans MS", "Papyrus", "Curlz MT", "Kristen ITC",
    "Arial", "Verdana", "Helvetica" # Fallbacks
]

# Button relief styles
RELIEF_STYLES = [tk.RAISED, tk.SUNKEN, tk.GROOVE, tk.RIDGE, tk.FLAT]

class WhimsicalFileLauncherApp:
    def __init__(self, root):
        self.root = root
        self.root.title("✨ Whimsical File Launcher ✨")

        # Attempt to start maximized
        try:
            self.root.state('zoomed')  # For Windows and some Linux WMs
        except tk.TclError:
            try:
                self.root.attributes('-zoomed', True) # For some other Linux WMs and macOS
            except tk.TclError:
                # Fallback: set to screen dimensions if 'zoomed' fails
                width = self.root.winfo_screenwidth()
                height = self.root.winfo_screenheight()
                self.root.geometry(f"{width}x{height}+0+0")

        self.root.resizable(True, True)
        self.root.configure(bg=self._get_random_color(light_bias=True)) # Initial window background

        self.selected_files = []
        self.menu_frame = None

        # --- Main Control Frame ---
        control_frame = tk.Frame(self.root, bg=self._get_random_color(light_bias=True, avoid=self.root.cget("bg")))
        control_frame.pack(pady=20, padx=20, fill=tk.X)

        self.select_button = tk.Button(
            control_frame,
            text="🌟 Select Your Magical Files 🌟",
            command=self.select_files_and_create_menu,
            font=(random.choice(WHIMSICAL_FONTS), 16, "bold"),
            bg=self._get_random_color(),
            fg=self._get_contrasting_color(control_frame.cget("bg")), # Text color contrasts with button bg
            padx=15, pady=10,
            relief=random.choice(RELIEF_STYLES),
            borderwidth=random.randint(2, 5)
        )
        self.select_button.pack(side=tk.LEFT, expand=True, padx=10)

        regenerate_button = tk.Button(
            control_frame,
            text="🎨 Re-Enchant Menu 🎨",
            command=self.create_menu_ui, # Re-uses existing files
            font=(random.choice(WHIMSICAL_FONTS), 14, "bold"),
            bg=self._get_random_color(),
            fg=self._get_contrasting_color(control_frame.cget("bg")),
            padx=10, pady=8,
            relief=random.choice(RELIEF_STYLES),
            borderwidth=random.randint(2, 4)
        )
        regenerate_button.pack(side=tk.LEFT, expand=True, padx=10)

        # --- Placeholder for menu ---
        self.menu_display_area = tk.Frame(self.root, bg=self.root.cget("bg"))
        self.menu_display_area.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)


    def _get_random_color(self, light_bias=False, avoid=None):
        color = random.choice(WHIMSICAL_COLORS)
        if avoid:
            while color == avoid: # Ensure some difference if avoid color is given
                color = random.choice(WHIMSICAL_COLORS)

        if light_bias: # Try to pick lighter colors more often for backgrounds
            r, g, b = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)
            if (r + g + b) / 3 < 128: # If it's a dark color
                # Try a few times to get a lighter one
                for _ in range(3):
                    new_color = random.choice(WHIMSICAL_COLORS)
                    nr, ng, nb = int(new_color[1:3], 16), int(new_color[3:5], 16), int(new_color[5:7], 16)
                    if (nr + ng + nb) / 3 >= 128:
                        return new_color
        return color

    def _get_contrasting_color(self, bg_color_hex):
        """Gets a black or white color that contrasts with the bg_color_hex."""
        try:
            r = int(bg_color_hex[1:3], 16)
            g = int(bg_color_hex[3:5], 16)
            b = int(bg_color_hex[5:7], 16)
            # Standard HSP (Highly Sensitive Poo) equation for perceived brightness
            brightness = (0.299 * r + 0.587 * g + 0.114 * b)
            return "#000000" if brightness > 128 else "#FFFFFF"
        except:
            return random.choice(["#000000", "#FFFFFF"]) # Fallback

    def select_files_and_create_menu(self):
        files = filedialog.askopenfilenames(
            title="Select your magical files (Python, HTML, Images, Audio, etc.)",
            filetypes=(
                ("All files", "*.*"),
                ("Python files", "*.py"),
                ("HTML files", "*.html;*.htm"),
                ("Image files", "*.png;*.jpg;*.jpeg;*.gif;*.bmp;*.svg;*.webp"),
                ("Audio files", "*.mp3;*.wav;*.ogg;*.m4a"),
                ("Video files", "*.mp4;*.avi;*.mkv;*.mov"),
                ("Text/Docs", "*.txt;*.md;*.pdf;*.doc;*.docx")
            )
        )
        if files:
            self.selected_files = list(files)
            self.create_menu_ui()
        elif not self.selected_files: # No files selected and no previous files
             if self.menu_frame:
                self.menu_frame.destroy()
                self.menu_frame = None
             no_files_label = tk.Label(self.menu_display_area, text="No files selected. The magic awaits!",
                                       font=("Comic Sans MS", 18), bg=self.menu_display_area.cget("bg"),
                                       fg=self._get_contrasting_color(self.menu_display_area.cget("bg")))
             no_files_label.pack(expand=True)
             # Auto-remove label after a few seconds
             self.root.after(3000, lambda: no_files_label.destroy() if no_files_label.winfo_exists() else None)


    def create_menu_ui(self):
        if not self.selected_files:
            messagebox.showinfo("No Files", "No files selected to create a menu. Please select some files first!")
            return

        if self.menu_frame:
            self.menu_frame.destroy()

        # Destroy any lingering "No files" message
        for widget in self.menu_display_area.winfo_children():
            widget.destroy()

        self.menu_frame = tk.Frame(self.menu_display_area, bg=self._get_random_color(light_bias=True))
        self.menu_frame.pack(expand=True, fill=tk.BOTH, padx=5, pady=5)

        # Make the menu frame itself more dynamic looking
        self.root.configure(bg=self._get_random_color(light_bias=True))
        self.menu_display_area.configure(bg=self.root.cget("bg"))
        self.menu_frame.configure(bg=self._get_random_color(light_bias=True, avoid=self.root.cget("bg")))


        # Create a canvas and a scrollbar for the buttons if there are many
        canvas = tk.Canvas(self.menu_frame, bg=self.menu_frame.cget("bg"), highlightthickness=0)
        scrollbar = tk.Scrollbar(self.menu_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=self.menu_frame.cget("bg"))

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(
                scrollregion=canvas.bbox("all")
            )
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")


        for filepath in self.selected_files:
            filename = os.path.basename(filepath)
            
            btn_bg = self._get_random_color()
            btn_fg = self._get_contrasting_color(btn_bg)
            btn_font_family = random.choice(WHIMSICAL_FONTS)
            btn_font_size = random.randint(12, 18)
            btn_relief = random.choice(RELIEF_STYLES)
            btn_borderwidth = random.randint(2, 5)
            btn_pady = random.randint(5, 10)
            btn_padx = random.randint(8, 15)

            try:
                # Using tk.Button for more reliable bg/fg styling across platforms
                btn = tk.Button(
                    scrollable_frame, # Add buttons to the scrollable frame
                    text=f"✨ {filename} ✨",
                    command=lambda p=filepath: self.launch_file(p),
                    bg=btn_bg,
                    fg=btn_fg,
                    font=(btn_font_family, btn_font_size, "bold"),
                    relief=btn_relief,
                    borderwidth=btn_borderwidth,
                    padx=btn_padx,
                    pady=btn_pady,
                    activebackground=self._get_random_color(avoid=btn_bg), # Color when clicked
                    activeforeground=self._get_contrasting_color(btn.cget("activebackground") if 'btn' in locals() else btn_bg)
                )
                btn.pack(pady=random.randint(5,10), padx=random.randint(10,20), fill=tk.X, expand=False)
            except tk.TclError as e:
                print(f"Warning: Could not apply font '{btn_font_family}'. Using default. Error: {e}")
                # Fallback if font is not found
                btn = tk.Button(
                    scrollable_frame,
                    text=f"✨ {filename} ✨",
                    command=lambda p=filepath: self.launch_file(p),
                    bg=btn_bg, fg=btn_fg,
                    font=("Arial", 14, "bold"), # Safe fallback
                    relief=btn_relief, borderwidth=btn_borderwidth,
                    padx=btn_padx, pady=btn_pady
                )
                btn.pack(pady=random.randint(5,10), padx=random.randint(10,20), fill=tk.X, expand=False)


    def launch_file(self, filepath):
        try:
            _, ext = os.path.splitext(filepath)
            ext = ext.lower()
            abs_path = os.path.abspath(filepath) # Important for some launchers

            print(f"Launching: {filepath} (ext: {ext})")

            if ext == '.py':
                # For Python scripts, try to open in a new terminal/console
                if os.name == 'nt':  # Windows
                    subprocess.Popen(['start', 'cmd', '/k', 'python', abs_path], shell=True)
                elif os.uname().sysname == 'Darwin':  # macOS
                    # This is a bit tricky, might need a .command file or more complex AppleScript
                    # Simpler: run in background, output might be lost or go to Python console
                    # For a visible terminal:
                    # script = f'tell app "Terminal" to do script "python3 \\"{abs_path}\\""'
                    # subprocess.Popen(['osascript', '-e', script])
                    # Fallback to running it non-interactively:
                    subprocess.Popen(['python3', abs_path])
                else:  # Linux
                    # Try common terminal emulators
                    try:
                        subprocess.Popen(['x-terminal-emulator', '-e', 'python3', abs_path])
                    except FileNotFoundError:
                        try:
                            subprocess.Popen(['gnome-terminal', '--', 'python3', abs_path])
                        except FileNotFoundError:
                             try:
                                subprocess.Popen(['konsole', '-e', 'python3', abs_path])
                             except FileNotFoundError:
                                subprocess.Popen(['python3', abs_path]) # Fallback

            elif ext in ['.html', '.htm', '.svg']: # SVG can also be opened by browsers
                webbrowser.open(f'file://{abs_path}')
            
            # Common image, audio, video, document types (OS default handler)
            elif ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.ico',  # images
                         '.mp3', '.wav', '.ogg', '.aac', '.flac', '.m4a',       # audio
                         '.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv',        # video
                         '.pdf', '.txt', '.md', '.log', '.csv', '.json', '.xml', # docs
                         '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.odt', '.ods', '.odp']:
                if os.name == 'nt':
                    os.startfile(abs_path)
                elif os.uname().sysname == 'Darwin':
                    subprocess.Popen(['open', abs_path])
                else: # Linux and other POSIX
                    subprocess.Popen(['xdg-open', abs_path])
            else:
                # General fallback for unknown types
                print(f"Attempting generic open for: {filepath}")
                if os.name == 'nt':
                    os.startfile(abs_path)
                elif os.uname().sysname == 'Darwin':
                    subprocess.Popen(['open', abs_path])
                else:
                    subprocess.Popen(['xdg-open', abs_path])
        except FileNotFoundError as e:
            print(f"Error launching {filepath}: Command not found or file association error. {e}")
            messagebox.showerror("Launch Error", f"Could not find a program to open: {os.path.basename(filepath)}\n\nEnsure you have a default program for this file type or the necessary command (e.g., 'python') is in your PATH.")
        except Exception as e:
            print(f"Error launching {filepath}: {e}")
            messagebox.showerror("Launch Error", f"Could not open file: {os.path.basename(filepath)}\n\nError: {e}")


if __name__ == "__main__":
    root = tk.Tk()
    app = WhimsicalFileLauncherApp(root)
    root.mainloop()