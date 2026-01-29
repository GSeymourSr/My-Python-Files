import tkinter as tk
from tkinter import filedialog, messagebox, font, simpledialog, ttk
import threading
import time
import os
import random  # Added for shuffling
import tempfile
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# --- MoviePy Check ---
try:
    from moviepy.editor import ImageClip, concatenate_videoclips
    MOVIEPY_AVAILABLE = True
except ImportError:
    MOVIEPY_AVAILABLE = False
    print("MoviePy not found. To use MP4 export, run: pip install moviepy")

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
        r, g, b = self.winfo_rgb(self.orig_bg)
        factor = 0.85
        darker = f'#{int((r/256)*factor):02x}{int((g/256)*factor):02x}{int((b/256)*factor):02x}'
        self.config(background=darker)

    def on_leave(self, e):
        self.config(background=self.orig_bg)

class AdvancedHTMLViewer:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Whimsical HTML Studio - Ultimate")
        
        # Start maximized
        try:
            self.root.state('zoomed')
        except:
            self.root.attributes('-zoomed', True)
            
        self.root.minsize(900, 600)
        
        self.slides = [] 
        self.running_event = threading.Event()
        
        # Variable for Random Checkbox
        self.random_order = tk.BooleanVar()
        self.random_order.set(False)
        
        self.colors = {
            "bg": "#f0f8ff", "panel": "#e6f2ff",
            "btn_add": "#77dd77", "btn_del": "#ffb7b2",
            "btn_act": "#ffdac1", "btn_go": "#84b6f4",
            "btn_stop": "#ff6961", "text": "#444444"
        }
        
        self.root.config(bg=self.colors["bg"])
        self.fonts = {
            "title": font.Font(family="Comic Sans MS", size=20, weight="bold"),
            "ui": font.Font(family="Segoe UI", size=11),
            "bold": font.Font(family="Segoe UI", size=11, weight="bold")
        }

        self.setup_gui()

    def setup_gui(self):
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)

        # Header
        header_frame = tk.Frame(self.root, bg=self.colors["bg"], pady=15)
        header_frame.grid(row=0, column=0, sticky="ew")
        tk.Label(header_frame, text="✨ Whimsical HTML Studio ✨", font=self.fonts["title"], 
                 bg=self.colors["bg"], fg="#6a5acd").pack()

        # Treeview
        list_frame = tk.Frame(self.root, bg=self.colors["panel"], padx=20, pady=10)
        list_frame.grid(row=1, column=0, sticky="nsew", padx=20)
        
        tree_scroll = tk.Scrollbar(list_frame)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        cols = ("Order", "Filename", "Duration (s)", "Full Path")
        self.tree = ttk.Treeview(list_frame, columns=cols, show="headings", yscrollcommand=tree_scroll.set)
        
        self.tree.heading("Order", text="#")
        self.tree.column("Order", width=50, anchor="center")
        self.tree.heading("Filename", text="File Name")
        self.tree.column("Filename", width=400)
        self.tree.heading("Duration (s)", text="Duration")
        self.tree.column("Duration (s)", width=100, anchor="center")
        self.tree.heading("Full Path", text="Path")
        self.tree.column("Full Path", width=0, stretch=False)
        
        self.tree.pack(fill=tk.BOTH, expand=True)
        tree_scroll.config(command=self.tree.yview)
        self.tree.bind("<Double-1>", self.on_double_click)

        # Sidebar
        btn_frame = tk.Frame(self.root, bg=self.colors["bg"], padx=20, pady=20)
        btn_frame.grid(row=1, column=1, sticky="ns")
        
        tk.Label(btn_frame, text="File Actions", font=self.fonts["bold"], bg=self.colors["bg"]).pack(pady=(0, 10))
        StyledButton(btn_frame, text="Add Files...", bg=self.colors["btn_add"], fg="white", font=self.fonts["bold"], 
                     command=self.add_files).pack(fill=tk.X, pady=5)
        StyledButton(btn_frame, text="Remove Selected", bg=self.colors["btn_del"], fg="white", font=self.fonts["bold"], 
                     command=self.remove_file).pack(fill=tk.X, pady=5)

        tk.Frame(btn_frame, height=20, bg=self.colors["bg"]).pack()

        tk.Label(btn_frame, text="Ordering", font=self.fonts["bold"], bg=self.colors["bg"]).pack(pady=(0, 10))
        StyledButton(btn_frame, text="Move Up ▲", bg=self.colors["btn_act"], font=self.fonts["ui"], 
                     command=lambda: self.move_item(-1)).pack(fill=tk.X, pady=5)
        StyledButton(btn_frame, text="Move Down ▼", bg=self.colors["btn_act"], font=self.fonts["ui"], 
                     command=lambda: self.move_item(1)).pack(fill=tk.X, pady=5)
        StyledButton(btn_frame, text="Set Duration ⏱", bg=self.colors["btn_act"], font=self.fonts["ui"], 
                     command=self.edit_duration).pack(fill=tk.X, pady=5)

        # Bottom Bar
        action_frame = tk.Frame(self.root, bg="#dee2e6", pady=15)
        action_frame.grid(row=2, column=0, columnspan=2, sticky="ew")
        
        # Play / Stop / Random Controls
        self.btn_play = StyledButton(action_frame, text="▶ Start Slideshow", bg=self.colors["btn_go"], fg="white", 
                                     font=self.fonts["bold"], command=self.start_slideshow)
        self.btn_play.pack(side=tk.LEFT, padx=20)
        
        # New Random Checkbox
        chk_random = tk.Checkbutton(action_frame, text="🔀 Randomize Order", variable=self.random_order, 
                                    bg="#dee2e6", font=self.fonts["ui"], activebackground="#dee2e6")
        chk_random.pack(side=tk.LEFT, padx=5)
        
        self.btn_stop = StyledButton(action_frame, text="■ Stop", bg=self.colors["btn_stop"], fg="white", 
                                     font=self.fonts["bold"], command=self.stop_slideshow, state=tk.DISABLED)
        self.btn_stop.pack(side=tk.LEFT, padx=20)

        if MOVIEPY_AVAILABLE:
            self.btn_export = StyledButton(action_frame, text="💾 Export MP4", bg="#b19cd9", fg="white", 
                                          font=self.fonts["bold"], command=self.export_mp4)
            self.btn_export.pack(side=tk.RIGHT, padx=20)

        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        tk.Label(action_frame, textvariable=self.status_var, bg="#dee2e6", font=self.fonts["ui"]).pack(side=tk.RIGHT, padx=20)

    # --- File/Order Logic ---
    def add_files(self):
        files = filedialog.askopenfilenames(title="Select HTML Files", filetypes=[("HTML files", "*.html")])
        if files:
            dur = simpledialog.askinteger("Duration", "Seconds per slide:", initialvalue=5, minvalue=1, parent=self.root) or 5
            for f in files:
                self.slides.append({'path': f, 'name': os.path.basename(f), 'duration': dur})
            self.refresh_tree()

    def remove_file(self):
        selected = self.tree.selection()
        if not selected: return
        indices = [self.tree.index(i) for i in selected]
        indices.sort(reverse=True)
        for i in indices: del self.slides[i]
        self.refresh_tree()

    def refresh_tree(self):
        for item in self.tree.get_children(): self.tree.delete(item)
        for idx, slide in enumerate(self.slides):
            self.tree.insert("", "end", values=(idx+1, slide['name'], slide['duration'], slide['path']))

    def move_item(self, direction):
        selected = self.tree.selection()
        if not selected: return
        idx = self.tree.index(selected[0])
        new_idx = idx + direction
        if 0 <= new_idx < len(self.slides):
            self.slides[idx], self.slides[new_idx] = self.slides[new_idx], self.slides[idx]
            self.refresh_tree()
            self.tree.selection_set(self.tree.get_children()[new_idx])

    def on_double_click(self, event): self.edit_duration()

    def edit_duration(self):
        selected = self.tree.selection()
        if not selected: return
        idx = self.tree.index(selected[0])
        new_dur = simpledialog.askinteger("Edit Duration", f"Duration for {self.slides[idx]['name']}:", 
                                          initialvalue=self.slides[idx]['duration'], minvalue=1, parent=self.root)
        if new_dur:
            self.slides[idx]['duration'] = new_dur
            self.refresh_tree()
            self.tree.selection_set(selected[0])

    # --- Visual Slideshow (Browser) ---
    def start_slideshow(self):
        if not self.slides: return
        self.running_event.set()
        self.toggle_controls(True)
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
            
            while self.running_event.is_set():
                # --- RANDOM LOGIC ADDED HERE ---
                # Create a temporary playlist
                playlist = list(self.slides)
                
                # Check if random box is ticked
                if self.random_order.get():
                    random.shuffle(playlist)
                
                for slide in playlist:
                    if not self.running_event.is_set(): break
                    
                    driver.get(f"file:///{slide['path']}")
                    
                    # Wait for duration
                    expiry = time.time() + slide['duration']
                    while time.time() < expiry:
                        if not self.running_event.is_set(): break
                        time.sleep(0.1)
                        
                    if not driver.service.is_connectable(): raise Exception("Closed")
                    
        except Exception as e: 
            print(f"Slideshow ended: {e}")
        finally:
            if driver: 
                try: driver.quit()
                except: pass
            self.running_event.clear()
            self.root.after(0, lambda: self.toggle_controls(False))

    # --- MP4 EXPORT (Fixed & Improved) ---
    def export_mp4(self):
        if not self.slides: return
        save_path = filedialog.asksaveasfilename(defaultextension=".mp4", filetypes=[("MP4 Video", "*.mp4")])
        if not save_path: return

        self.btn_export.config(state=tk.DISABLED, text="Exporting...")
        self.btn_play.config(state=tk.DISABLED)
        
        threading.Thread(target=self._process_mp4_robust, args=(save_path,), daemon=True).start()

    def _process_mp4_robust(self, save_path):
        self.status_var.set("Starting capture...")
        
        # 1. Setup Headless Chrome
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--hide-scrollbars")
        # Ensure capturing at Full HD
        chrome_options.add_argument("--window-size=1920,1080")
        
        driver = None
        temp_files = []
        clips = []
        final_clip = None

        try:
            driver = webdriver.Chrome(options=chrome_options)
            # Explicitly set window size again to be sure
            driver.set_window_size(1920, 1080)
            
            # 2. Capture Loop
            for idx, slide in enumerate(self.slides):
                self.status_var.set(f"Capturing slide {idx+1}/{len(self.slides)}")
                
                driver.get(f"file:///{slide['path']}")
                # Wait for animations/rendering
                time.sleep(2)
                
                fd, tmp_name = tempfile.mkstemp(suffix=".png")
                os.close(fd)
                
                driver.save_screenshot(tmp_name)
                temp_files.append(tmp_name)
                
                # --- ROBUST IMAGE PROCESSING ---
                # 1. Load Image
                clip = ImageClip(tmp_name)
                # 2. Convert to RGB (Removes Alpha channel which crashes MP4 writers)
                clip = clip.convert("RGB")
                # 3. Force Resize (If screenshot was 1920x1079, it would crash. This fixes it)
                clip = clip.resize(newsize=(1920, 1080))
                # 4. Set Duration
                clip = clip.set_duration(slide['duration'])
                
                clips.append(clip)

            driver.quit() # Close browser to free RAM
            driver = None 
            
            # 3. Render Video
            self.status_var.set("Rendering Video (Please wait)...")
            
            final_clip = concatenate_videoclips(clips, method="compose")
            
            # Write file (No audio to prevent errors)
            final_clip.write_videofile(
                save_path, 
                fps=24, 
                codec="libx264", 
                audio=False, 
                preset="medium",
                threads=4,
                logger=None 
            )
            
            self.root.after(0, lambda: messagebox.showinfo("Success", "Video Saved Successfully!"))
            
        except Exception as e:
            print(f"Export Error: {e}") 
            self.root.after(0, lambda: messagebox.showerror("Export Failed", f"Detailed Error:\n{str(e)}"))
            
        finally:
            self.status_var.set("Cleaning up...")
            if driver:
                try: driver.quit()
                except: pass
            
            try:
                if final_clip: final_clip.close()
                for c in clips: c.close()
            except: pass
            
            # Give permission for file deletion
            time.sleep(0.5) 
            for f in temp_files:
                try: os.remove(f)
                except: pass

            self.root.after(0, lambda: self.status_var.set("Ready"))
            self.root.after(0, lambda: self.toggle_controls(False))
            self.root.after(0, lambda: self.btn_export.config(text="💾 Export MP4"))

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = AdvancedHTMLViewer()
    app.run()