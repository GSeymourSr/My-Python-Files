import tkinter as tk
from tkinter import filedialog, messagebox, font
import random
import time
import threading
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import WebDriverException

# --- A class for a more modern, styled button ---
class StyledButton(tk.Button):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.config(
            relief=tk.FLAT,
            activebackground=self.cget('bg'),
            activeforeground=self.cget('fg'),
            bd=0,
            padx=12,
            pady=8,
        )
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)

    def on_enter(self, e):
        # A simple darken/lighten effect on hover
        original_color = self.cget("background")
        r, g, b = self.winfo_rgb(original_color)
        # Create a slightly darker shade for hover
        darker_color = f'#{int(r/256*0.9):02x}{int(g/256*0.9):02x}{int(b/256*0.9):02x}'
        self.config(background=darker_color)

    def on_leave(self, e):
        # This feels a bit complex, let's store the original color
        self.config(background=self.orig_color)

# --- Main Application Class ---
class HTMLViewer:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Whimsical HTML Slideshow")
        self.root.geometry("550x550")
        self.root.resizable(False, False)
        
        # --- Whimsical Color Palette & Fonts ---
        self.BG_COLOR = "#f0f8ff"  # AliceBlue
        self.FRAME_COLOR = "#e0f0ff"
        self.BUTTON_COLOR = "#77dd77"  # Pastel Green
        self.STOP_BUTTON_COLOR = "#ff6961" # Pastel Red
        self.TEXT_COLOR = "#333333"
        self.ACCENT_COLOR = "#6a5acd"  # SlateBlue
        
        self.title_font = font.Font(family="Comic Sans MS", size=24, weight="bold")
        self.label_font = font.Font(family="Arial", size=12)
        self.button_font = font.Font(family="Arial", size=11, weight="bold")
        
        self.root.config(bg=self.BG_COLOR)

        self.selected_files = []
        self.slideshow_thread = None
        self.running = threading.Event() # Use an Event for clearer stop signal

        self.setup_gui()
        
    def setup_gui(self):
        main_frame = tk.Frame(self.root, bg=self.BG_COLOR, padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- 1. Title ---
        title_label = tk.Label(main_frame, text="HTML Slideshow", font=self.title_font, bg=self.BG_COLOR, fg=self.ACCENT_COLOR)
        title_label.pack(pady=(0, 20))

        # --- 2. File Selection Frame ---
        files_frame = tk.LabelFrame(main_frame, text="1. Select Your Files", font=self.label_font, bg=self.FRAME_COLOR, fg=self.TEXT_COLOR, padx=15, pady=15, relief=tk.GROOVE)
        files_frame.pack(fill=tk.X, pady=10)

        self.select_button = StyledButton(files_frame, text="Browse for HTML Files", command=self.select_files, bg=self.BUTTON_COLOR, fg="white", font=self.button_font)
        self.select_button.orig_color = self.BUTTON_COLOR
        self.select_button.pack(pady=(0, 10))
        
        list_frame = tk.Frame(files_frame, bg=self.FRAME_COLOR)
        list_frame.pack(fill=tk.X)
        self.files_listbox = tk.Listbox(list_frame, width=50, height=8, bg="white", fg=self.TEXT_COLOR, selectbackground=self.ACCENT_COLOR, relief=tk.SOLID, borderwidth=1)
        self.files_listbox.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        scrollbar = tk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.files_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.files_listbox.config(yscrollcommand=scrollbar.set)

        # --- 3. Settings Frame ---
        settings_frame = tk.LabelFrame(main_frame, text="2. Configure Slideshow", font=self.label_font, bg=self.FRAME_COLOR, fg=self.TEXT_COLOR, padx=15, pady=15, relief=tk.GROOVE)
        settings_frame.pack(fill=tk.X, pady=10)
        
        duration_label = tk.Label(settings_frame, text="Change file every (seconds):", font=self.label_font, bg=self.FRAME_COLOR, fg=self.TEXT_COLOR)
        duration_label.pack(side=tk.LEFT, padx=(0, 10))
        
        self.duration_spinbox = tk.Spinbox(settings_frame, from_=5, to=300, width=5, font=self.label_font)
        self.duration_spinbox.pack(side=tk.LEFT)
        self.duration_spinbox.delete(0, "end")
        self.duration_spinbox.insert(0, "30") # Default value

        # --- 4. Controls Frame ---
        controls_frame = tk.Frame(main_frame, bg=self.BG_COLOR)
        controls_frame.pack(pady=20)
        
        self.start_button = StyledButton(controls_frame, text="Start Slideshow", command=self.start_slideshow, bg=self.BUTTON_COLOR, fg="white", font=self.button_font)
        self.start_button.orig_color = self.BUTTON_COLOR
        self.start_button.pack(side=tk.LEFT, padx=10)
        
        self.stop_button = StyledButton(controls_frame, text="Stop Slideshow", command=self.stop_slideshow, bg=self.STOP_BUTTON_COLOR, fg="white", font=self.button_font, state=tk.DISABLED)
        self.stop_button.orig_color = self.STOP_BUTTON_COLOR
        self.stop_button.pack(side=tk.LEFT, padx=10)
        
    def select_files(self):
        files = filedialog.askopenfilenames(
            title="Select HTML Files",
            filetypes=[("HTML files", "*.html")]
        )
        if files:
            self.selected_files = list(files)
            self.update_listbox()
        
    def update_listbox(self):
        self.files_listbox.delete(0, tk.END)
        for file in self.selected_files:
            # Show just the filename, not the whole path, for cleanliness
            self.files_listbox.insert(tk.END, file.split('/')[-1])
            
    def start_slideshow(self):
        if not self.selected_files:
            messagebox.showwarning("No Files Selected", "Please select one or more HTML files to begin the slideshow.")
            return
            
        if not self.running.is_set():
            self.running.set() # Set the event to signal "running"
            duration = int(self.duration_spinbox.get())
            
            self.update_button_states()
            
            self.slideshow_thread = threading.Thread(
                target=self.run_slideshow, 
                args=(duration,), 
                daemon=True
            )
            self.slideshow_thread.start()

    def stop_slideshow(self):
        if self.running.is_set():
            self.running.clear() # Clear the event to signal "stop"
            # The thread will see this and exit its loop
            # The browser will be closed in the thread's finally block
            self.update_button_states()

    def update_button_states(self):
        """Updates the state of buttons based on the slideshow status."""
        if self.running.is_set():
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
            self.select_button.config(state=tk.DISABLED)
            self.duration_spinbox.config(state=tk.DISABLED)
        else:
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            self.select_button.config(state=tk.NORMAL)
            self.duration_spinbox.config(state=tk.NORMAL)
            
    def run_slideshow(self, duration):
        chrome_options = Options()
        # **ENHANCEMENT**: Remove the "Chrome is controlled by automated test software" infobar
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_argument("--start-fullscreen")
        
        driver = None # Initialize driver to None
        try:
            driver = webdriver.Chrome(options=chrome_options)
            
            while self.running.is_set() and self.selected_files:
                current_file = random.choice(self.selected_files)
                driver.get(f"file:///{current_file}")
                
                # **ENHANCEMENT**: Add event listener to exit on 'Escape' key press
                # This script attempts to close the window. Selenium will then raise an
                # exception, which we catch to gracefully end the slideshow.
                driver.execute_script("""
                    document.body.addEventListener('keydown', function(e) {
                        if (e.key === "Escape") {
                            window.close();
                        }
                    });
                    // Also focus the body to make sure it receives key events
                    document.body.focus();
                """)
                
                # Use a loop for sleeping to make it responsive to the stop signal
                for _ in range(duration):
                    if not self.running.is_set():
                        break
                    time.sleep(1)
                
        except WebDriverException as e:
            # This often happens if the user closes the browser window manually or via Escape.
            # It's an expected way to exit.
            print(f"Slideshow exited: Browser window was closed. ({e.__class__.__name__})")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
        finally:
            if driver:
                driver.quit()
            
            # Signal that the slideshow has stopped
            self.running.clear()
            # **IMPORTANT**: Update GUI from the main thread using `root.after`
            self.root.after(0, self.update_button_states)
            
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    # Custom StyledButton needs to be defined before it's used
    # This is a bit of a workaround for the hover color issue in the simple class
    class BetterStyledButton(tk.Button):
        def __init__(self, master=None, **kw):
            self.orig_color = kw.get('bg')
            super().__init__(master=master, **kw)
            self.config(
                relief=tk.FLAT,
                activebackground=self.orig_color,
                activeforeground=self.cget('fg'),
                bd=0, padx=12, pady=8,
            )
            self.bind("<Enter>", self.on_enter)
            self.bind("<Leave>", self.on_leave)

        def on_enter(self, e):
            r, g, b = self.winfo_rgb(self.orig_color)
            r, g, b = r//257, g//257, b//257 # Convert from 16-bit to 8-bit
            hover_color = f'#{max(0, r-20):02x}{max(0, g-20):02x}{max(0, b-20):02x}'
            self.config(background=hover_color, activebackground=hover_color)

        def on_leave(self, e):
            self.config(background=self.orig_color, activebackground=self.orig_color)

    # Overwrite the original StyledButton with our better one for the main app
    StyledButton = BetterStyledButton
    
    app = HTMLViewer()
    app.run()