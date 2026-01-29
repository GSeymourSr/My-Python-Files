import tkinter as tk
from tkinter import filedialog, messagebox, font, simpledialog, ttk
import threading
import time
import os
import tempfile
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# Try importing MoviePy for MP4 export; handle error if missing
try:
    from moviepy.editor import ImageClip, concatenate_videoclips
    MOVIEPY_AVAILABLE = True
except ImportError:
    MOVIEPY_AVAILABLE = False

# --- Modern Styled Button ---
class StyledButton(tk.Button):
    def __init__(self, master, **kwargs):
        self.orig_bg = kwargs.get('bg', '#dddddd')
        super().__init__(master, **kwargs)
        self.config(
            relief=tk.FLAT,
            activebackground=self.orig_bg,
            activeforeground=self.cget('fg'),
            bd=0, padx=15, pady=8, cursor="hand2"
        )
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)

    def on_enter(self, e):
        # Darken color slightly
        r, g, b = self.winfo_rgb(self.orig_bg)
        # RGB comes back as 16-bit, convert to 8-bit and darken
        factor = 0.85
        darker = f'#{int((r/256)*factor):02x}{int((g/256)*factor):02x}{int((b/256)*factor):02x}'
        self.config(background=darker)

    def on_leave(self, e):
        self.config(background=self.orig_bg)

# --- Main Application ---
class AdvancedHTMLViewer:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Whimsical HTML Studio Pro")
        
        # Start maximized/fullscreen
        try:
            self.root.state('zoomed')  # Windows
        except:
            self.root.attributes('-zoomed', True) # Linux/Mac
            
        self.root.minsize(900, 600)
        
        # --- Data Structure ---
        # List of dictionaries: [{'path': str, 'name': str, 'duration': int}]
        self.slides = [] 
        self.running_event = threading.Event()
        
        # --- Styles & Colors ---
        self.colors = {
            "bg": "#f0f8ff",      # AliceBlue
            "panel": "#e6f2ff",
            "btn_add": "#77dd77", # Pastel Green
            "btn_del": "#ffb7b2", # Pastel Pink
            "btn_act": "#ffdac1", # Pastel Orange
            "btn_go": "#84b6f4",  # Pastel Blue
            "btn_stop": "#ff6961",# Pastel Red
            "text": "#444444"
        }
        
        self.root.config(bg=self.colors["bg"])
        self.fonts = {
            "title": font.Font(family="Comic Sans MS", size=20, weight="bold"),
            "ui": font.Font(family="Segoe UI", size=11),
            "bold": font.Font(family="Segoe UI", size=11, weight="bold")
        }

        self.setup_gui()
        
        if not MOVIEPY_AVAILABLE:
            messagebox.showinfo("Feature Notice", "To use MP4 Export, please run: pip install moviepy")

    def setup_gui(self):
        # Configure Grid Weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1) # The list takes up most space

        # --- Header ---
        header_frame = tk.Frame(self.root, bg=self.colors["bg"], pady=15)
        header_frame.grid(row=0, column=0, sticky="ew")
        tk.Label(header_frame, text="✨ Whimsical HTML Studio ✨", font=self.fonts["title"], 
                 bg=self.colors["bg"], fg="#6a5acd").pack()

        # --- Main Content (Treeview) ---
        list_frame = tk.Frame(self.root, bg=self.colors["panel"], padx=20, pady=10)
        list_frame.grid(row=1, column=0, sticky="nsew", padx=20)
        
        # Treeview Scrollbar
        tree_scroll = tk.Scrollbar(list_frame)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Treeview setup
        cols = ("Order", "Filename", "Duration (s)", "Full Path")
        self.tree = ttk.Treeview(list_frame, columns=cols, show="headings", yscrollcommand=tree_scroll.set)
        
        # Column Config
        self.tree.heading("Order", text="#")
        self.tree.column("Order", width=50, anchor="center")
        self.tree.heading("Filename", text="File Name")
        self.tree.column("Filename", width=400)
        self.tree.heading("Duration (s)", text="Duration")
        self.tree.column("Duration (s)", width=100, anchor="center")
        self.tree.heading("Full Path", text="Path")
        self.tree.column("Full Path", width=0, stretch=False) # Hidden column
        
        self.tree.pack(fill=tk.BOTH, expand=True)
        tree_scroll.config(command=self.tree.yview)
        
        # Double click to edit duration
        self.tree.bind("<Double-1>", self.on_double_click)

        # --- Controls Sidebar (Right Side) ---
        btn_frame = tk.Frame(self.root, bg=self.colors["bg"], padx=20, pady=20)
        btn_frame.grid(row=1, column=1, sticky="ns")
        
        # File Operations
        lbl_files = tk.Label(btn_frame, text="File Actions", font=self.fonts["bold"], bg=self.colors["bg"])
        lbl_files.pack(pady=(0, 10))
        
        StyledButton(btn_frame, text="Add Files...", bg=self.colors["btn_add"], fg="white", font=self.fonts["bold"], 
                     command=self.add_files).pack(fill=tk.X, pady=5)
        
        StyledButton(btn_frame, text="Remove Selected", bg=self.colors["btn_del"], fg="white", font=self.fonts["bold"], 
                     command=self.remove_file).pack(fill=tk.X, pady=5)

        tk.Frame(btn_frame, height=20, bg=self.colors["bg"]).pack() # Spacer

        # Order Operations
        lbl_order = tk.Label(btn_frame, text="Ordering", font=self.fonts["bold"], bg=self.colors["bg"])
        lbl_order.pack(pady=(0, 10))
        
        StyledButton(btn_frame, text="Move Up ▲", bg=self.colors["btn_act"], font=self.fonts["ui"], 
                     command=lambda: self.move_item(-1)).pack(fill=tk.X, pady=5)
        StyledButton(btn_frame, text="Move Down ▼", bg=self.colors["btn_act"], font=self.fonts["ui"], 
                     command=lambda: self.move_item(1)).pack(fill=tk.X, pady=5)
        
        StyledButton(btn_frame, text="Set Duration ⏱", bg=self.colors["btn_act"], font=self.fonts["ui"], 
                     command=self.edit_duration).pack(fill=tk.X, pady=5)

        # --- Bottom Action Bar ---
        action_frame = tk.Frame(self.root, bg="#dee2e6", pady=15)
        action_frame.grid(row=2, column=0, columnspan=2, sticky="ew")
        
        self.btn_play = StyledButton(action_frame, text="▶ Start Slideshow", bg=self.colors["btn_go"], fg="white", 
                                     font=self.fonts["bold"], command=self.start_slideshow)
        self.btn_play.pack(side=tk.LEFT, padx=20)
        
        self.btn_stop = StyledButton(action_frame, text="■ Stop", bg=self.colors["btn_stop"], fg="white", 
                                     font=self.fonts["bold"], command=self.stop_slideshow, state=tk.DISABLED)
        self.btn_stop.pack(side=tk.LEFT, padx=5)

        # MP4 Export Button
        if MOVIEPY_AVAILABLE:
            self.btn_export = StyledButton(action_frame, text="💾 Export to MP4", bg="#b19cd9", fg="white", 
                                          font=self.fonts["bold"], command=self.export_mp4)
            self.btn_export.pack(side=tk.RIGHT, padx=20)

        # Progress Label for Export
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        tk.Label(action_frame, textvariable=self.status_var, bg="#dee2e6", font=self.fonts["ui"]).pack(side=tk.RIGHT, padx=20)

    # --- Logic: File Management ---
    def add_files(self):
        files = filedialog.askopenfilenames(title="Select HTML Files", filetypes=[("HTML files", "*.html")])
        if files:
            # Ask for default duration for this batch
            dur = simpledialog.askinteger("Duration", "Seconds per slide:", initialvalue=5, minvalue=1, parent=self.root)
            if not dur: dur = 5
            
            for f in files:
                name = os.path.basename(f)
                self.slides.append({'path': f, 'name': name, 'duration': dur})
            
            self.refresh_tree()

    def remove_file(self):
        selected = self.tree.selection()
        if not selected: return
        
        # Get indexes to delete (reverse order to avoid index shifting)
        indices = [self.tree.index(i) for i in selected]
        indices.sort(reverse=True)
        
        for i in indices:
            del self.slides[i]
        self.refresh_tree()

    def refresh_tree(self):
        # Clear current tree
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        # Repopulate
        for idx, slide in enumerate(self.slides):
            self.tree.insert("", "end", values=(idx+1, slide['name'], slide['duration'], slide['path']))

    # --- Logic: Ordering & Editing ---
    def move_item(self, direction):
        selected = self.tree.selection()
        if not selected: return
        
        # Only move one item at a time for simplicity
        row_id = selected[0]
        index = self.tree.index(row_id)
        
        new_index = index + direction
        
        if 0 <= new_index < len(self.slides):
            # Swap in list
            self.slides[index], self.slides[new_index] = self.slides[new_index], self.slides[index]
            self.refresh_tree()
            # Reselect the moved item
            child_id = self.tree.get_children()[new_index]
            self.tree.selection_set(child_id)

    def on_double_click(self, event):
        self.edit_duration()

    def edit_duration(self):
        selected = self.tree.selection()
        if not selected: return
        
        # Get current value
        index = self.tree.index(selected[0])
        current_dur = self.slides[index]['duration']
        
        new_dur = simpledialog.askinteger("Edit Duration", f"Duration for {self.slides[index]['name']}:", 
                                          initialvalue=current_dur, minvalue=1, parent=self.root)
        if new_dur:
            self.slides[index]['duration'] = new_dur
            self.refresh_tree()
            # Reselect
            self.tree.selection_set(selected[0])

    # --- Logic: Slideshow ---
    def start_slideshow(self):
        if not self.slides:
            messagebox.showwarning("Empty", "Add some files first!")
            return
            
        self.running_event.set()
        self.toggle_controls(running=True)
        
        threading.Thread(target=self._run_browser_slideshow, daemon=True).start()

    def stop_slideshow(self):
        self.running_event.clear()

    def toggle_controls(self, running):
        if running:
            self.btn_play.config(state=tk.DISABLED)
            self.btn_stop.config(state=tk.NORMAL)
            if MOVIEPY_AVAILABLE: self.btn_export.config(state=tk.DISABLED)
        else:
            self.btn_play.config(state=tk.NORMAL)
            self.btn_stop.config(state=tk.DISABLED)
            if MOVIEPY_AVAILABLE: self.btn_export.config(state=tk.NORMAL)

    def _run_browser_slideshow(self):
        chrome_options = Options()
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_argument("--start-fullscreen")
        
        driver = None
        try:
            driver = webdriver.Chrome(options=chrome_options)
            
            # Loop forever until stop is pressed, or just once? Usually slideshows loop.
            # Let's loop continuously.
            while self.running_event.is_set():
                for slide in self.slides:
                    if not self.running_event.is_set(): break
                    
                    driver.get(f"file:///{slide['path']}")
                    
                    # Wait for duration
                    expiry = time.time() + slide['duration']
                    while time.time() < expiry:
                        if not self.running_event.is_set(): break
                        time.sleep(0.1)
                        
                    # Check if user closed window
                    if not driver.service.is_connectable():
                        raise Exception("Window Closed")
                        
        except Exception as e:
            print(f"Slideshow ended: {e}")
        finally:
            if driver:
                try: driver.quit()
                except: pass
            self.running_event.clear()
            self.root.after(0, lambda: self.toggle_controls(running=False))

    # --- Logic: MP4 Export ---
    def export_mp4(self):
        if not self.slides: return
        
        save_path = filedialog.asksaveasfilename(defaultextension=".mp4", 
                                                 filetypes=[("MP4 Video", "*.mp4")])
        if not save_path: return

        self.btn_export.config(state=tk.DISABLED, text="Exporting...")
        self.btn_play.config(state=tk.DISABLED)
        
        threading.Thread(target=self._process_mp4, args=(save_path,), daemon=True).start()

    def _process_mp4(self, save_path):
        self.status_var.set("Initializing Headless Browser...")
        
        chrome_options = Options()
        chrome_options.add_argument("--headless") # Run in background
        chrome_options.add_argument("--hide-scrollbars")
        # Set Resolution (HD)
        chrome_options.add_argument("--window-size=1920,1080")
        
        driver = webdriver.Chrome(options=chrome_options)
        temp_files = []
        clips = []
        
        try:
            for idx, slide in enumerate(self.slides):
                self.status_var.set(f"Capturing Slide {idx+1}/{len(self.slides)}...")
                
                driver.get(f"file:///{slide['path']}")
                # Give it a moment to render CSS/JS
                time.sleep(1) 
                
                # Take Screenshot
                fd, tmp_name = tempfile.mkstemp(suffix=".png")
                os.close(fd)
                driver.save_screenshot(tmp_name)
                temp_files.append(tmp_name)
                
                # Create Clip
                clip = ImageClip(tmp_name).set_duration(slide['duration'])
                clips.append(clip)
            
            self.status_var.set("Rendering Video (this may take time)...")
            driver.quit() # Close browser before rendering
            
            final_clip = concatenate_videoclips(clips, method="compose")
            final_clip.write_videofile(save_path, fps=24, codec="libx264", logger=None)
            
            self.root.after(0, lambda: messagebox.showinfo("Success", "Video Saved Successfully!"))
            
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", f"Export Failed: {str(e)}"))
        finally:
            # Cleanup
            self.status_var.set("Cleaning up...")
            for f in temp_files:
                try: os.remove(f)
                except: pass
            
            if MOVIEPY_AVAILABLE: 
                try:
                    final_clip.close()
                    for c in clips: c.close()
                except: pass

            self.root.after(0, lambda: self.status_var.set("Ready"))
            self.root.after(0, lambda: self.toggle_controls(running=False))

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = AdvancedHTMLViewer()
    app.run()