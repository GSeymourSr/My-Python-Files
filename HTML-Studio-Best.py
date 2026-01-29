import tkinter as tk
from tkinter import filedialog, messagebox, font, simpledialog, ttk
import threading
import time
import os
import random
import traceback

# --- Dependencies Check ---
DEPENDENCIES_OK = True
try:
    import mss
    import numpy as np
    import imageio
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager
except ImportError as e:
    DEPENDENCIES_OK = False
    MISSING_LIB = str(e)

# --- Progress Window Class ---
class ProgressWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Rendering Progress")
        self.geometry("500x450")
        self.resizable(False, False)
        self.configure(bg="#f0f0f0")
        
        # Center info
        self.lbl_status = tk.Label(self, text="Initializing...", font=("Segoe UI", 12, "bold"), bg="#f0f0f0")
        self.lbl_status.pack(pady=(15, 5))
        
        self.progress = ttk.Progressbar(self, orient=tk.HORIZONTAL, length=400, mode='determinate')
        self.progress.pack(pady=10)
        
        self.lbl_details = tk.Label(self, text="Waiting for browser...", font=("Segoe UI", 10), bg="#f0f0f0")
        self.lbl_details.pack(pady=5)

        # Log Console
        tk.Label(self, text="Process Log:", bg="#f0f0f0", font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=20)
        
        self.log_text = tk.Text(self, height=12, width=55, font=("Consolas", 9), state=tk.DISABLED)
        self.log_text.pack(padx=20, pady=5)
        
        self.btn_cancel = tk.Button(self, text="Abort Recording", command=self.on_close, bg="#ff6961", fg="white")
        self.btn_cancel.pack(pady=10)

        self.cancelled = False
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def on_close(self):
        self.cancelled = True
        self.log("Stopping... please wait for cleanup.")
        self.btn_cancel.config(state=tk.DISABLED)

    def log(self, message):
        if self.winfo_exists():
            self.log_text.config(state=tk.NORMAL)
            self.log_text.insert(tk.END, f"> {message}\n")
            self.log_text.see(tk.END)
            self.log_text.config(state=tk.DISABLED)

    def update_bar(self, current, total, status_text):
        if self.winfo_exists():
            self.progress['value'] = (current / total) * 100
            self.lbl_status.config(text=f"Processing Slide {current}/{total}")
            self.lbl_details.config(text=status_text)

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
        self.root.title("Whimsical HTML Studio - High Speed Recorder")
        
        try:
            self.root.state('zoomed')
        except:
            self.root.attributes('-zoomed', True)
            
        self.root.minsize(900, 600)
        self.slides = [] 
        self.running_event = threading.Event()
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
        
        if not DEPENDENCIES_OK:
            messagebox.showerror("Missing Libraries", 
                "To use the smooth recorder, you need to install new libraries.\n\n"
                "Please run this command in your terminal:\n"
                "pip install mss numpy imageio webdriver-manager")

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
        
        self.btn_play = StyledButton(action_frame, text="▶ Start Slideshow", bg=self.colors["btn_go"], fg="white", 
                                     font=self.fonts["bold"], command=self.start_slideshow)
        self.btn_play.pack(side=tk.LEFT, padx=20)
        
        chk_random = tk.Checkbutton(action_frame, text="🔀 Randomize Order", variable=self.random_order, 
                                    bg="#dee2e6", font=self.fonts["ui"], activebackground="#dee2e6")
        chk_random.pack(side=tk.LEFT, padx=5)
        
        self.btn_stop = StyledButton(action_frame, text="■ Stop", bg=self.colors["btn_stop"], fg="white", 
                                     font=self.fonts["bold"], command=self.stop_slideshow, state=tk.DISABLED)
        self.btn_stop.pack(side=tk.LEFT, padx=20)

        if DEPENDENCIES_OK:
            self.btn_export = StyledButton(action_frame, text="🎥 Record Smooth MP4", bg="#b19cd9", fg="white", 
                                          font=self.fonts["bold"], command=self.export_mp4)
            self.btn_export.pack(side=tk.RIGHT, padx=20)
        else:
            tk.Label(action_frame, text="Export Disabled (Missing Libs)", fg="red", bg="#dee2e6").pack(side=tk.RIGHT, padx=20)

        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        tk.Label(action_frame, textvariable=self.status_var, bg="#dee2e6", font=self.fonts["ui"]).pack(side=tk.RIGHT, padx=20)

    # --- Standard Functions ---
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
            if hasattr(self, 'btn_export'): self.btn_export.config(state=tk.DISABLED)
        else:
            self.btn_play.config(state=tk.NORMAL)
            self.btn_stop.config(state=tk.DISABLED)
            if hasattr(self, 'btn_export'): self.btn_export.config(state=tk.NORMAL)

    def _run_browser_slideshow(self):
        chrome_options = Options()
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_argument("--start-fullscreen")
        
        driver = None
        try:
            driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
            
            while self.running_event.is_set():
                playlist = list(self.slides)
                if self.random_order.get():
                    random.shuffle(playlist)
                
                for slide in playlist:
                    if not self.running_event.is_set(): break
                    driver.get(f"file:///{slide['path']}")
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

    # --- NEW HIGH-SPEED RECORDER ---
    def export_mp4(self):
        if not self.slides: return
        
        # 1. Ask for Override Seconds
        override_seconds = simpledialog.askinteger("Global Setting", 
                                                 "How many seconds should EVERY slide play for?\n"
                                                 "(Click Cancel to use individual times from the list)",
                                                 parent=self.root, minvalue=1)
        
        save_path = filedialog.asksaveasfilename(defaultextension=".mp4", filetypes=[("MP4 Video", "*.mp4")])
        if not save_path: return

        self.btn_export.config(state=tk.DISABLED, text="Recording...")
        self.btn_play.config(state=tk.DISABLED)
        
        # Create Progress Window
        self.prog_win = ProgressWindow(self.root)
        
        threading.Thread(target=self._run_smooth_record, args=(save_path, override_seconds), daemon=True).start()

    def _run_smooth_record(self, save_path, override_seconds):
        FPS = 30  # Smooth 30fps
        
        driver = None
        writer = None
        sct = None

        try:
            # 1. Setup Chrome
            self.prog_win.log("Launching Chrome (Fullscreen)...")
            chrome_options = Options()
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_argument("--log-level=3") 
            chrome_options.add_argument("--silent")
            # We start maximized, but script will force F11 later
            chrome_options.add_argument("--start-maximized")
            
            driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
            
            # Setup Screen Capture (MSS)
            sct = mss.mss()
            
            # 2. Get Window Coordinates
            self.prog_win.log("Entering Fullscreen Mode...")
            
            # Force F11 Mode
            driver.fullscreen_window()
            # Wait for the "Press F11 to exit" bubble to fade away
            time.sleep(3) 
            
            # In Fullscreen, the content is the monitor size
            monitor = sct.monitors[1] # Primary monitor
            
            self.prog_win.log(f"Capture Area: {monitor['width']}x{monitor['height']}")
            
            # 3. Initialize Video Writer
            self.prog_win.log(f"Initializing Video Writer ({FPS} fps)...")
            writer = imageio.get_writer(save_path, fps=FPS, codec='libx264', quality=8)
            
            # 4. Recording Loop
            for idx, slide in enumerate(self.slides):
                if self.prog_win.cancelled: break
                
                slide_name = slide['name']
                # USE OVERRIDE IF SET, OTHERWISE LIST DURATION
                duration = override_seconds if override_seconds else slide['duration']
                
                self.prog_win.update_bar(idx + 1, len(self.slides), f"Recording: {slide_name}")
                self.prog_win.log(f"Loading {slide_name}...")
                
                driver.get(f"file:///{slide['path']}")
                
                # Small buffer for page load (doesn't count towards video time)
                time.sleep(0.5)
                
                # PRECISION TIMING LOGIC
                start_perf = time.perf_counter()
                frame_count = 0
                expected_frames = int(duration * FPS)
                frame_duration = 1.0 / FPS
                
                self.prog_win.log(f" > Recording {duration}s ({expected_frames} frames)...")
                
                for i in range(expected_frames):
                    if self.prog_win.cancelled: break
                    
                    loop_start = time.perf_counter()
                    
                    # --- CAPTURE ---
                    img = sct.grab(monitor)
                    frame = np.array(img)
                    
                    # --- COLOR FIX (BGR -> RGB) ---
                    # Drop Alpha (4th channel) AND Reverse colors (BGR to RGB)
                    frame = frame[:, :, :3][..., ::-1]
                    
                    # --- WRITE ---
                    writer.append_data(frame)
                    
                    frame_count += 1
                    
                    if frame_count % 30 == 0:
                        elapsed = time.perf_counter() - start_perf
                        self.prog_win.lbl_details.config(text=f"Recording {slide_name}: {elapsed:.1f}s / {duration}s (FPS: {FPS})")
                    
                    # --- SYNC SLEEP ---
                    # Calculate how long the processing took
                    process_time = time.perf_counter() - loop_start
                    # Sleep only the remainder of the frame time
                    sleep_time = frame_duration - process_time
                    
                    if sleep_time > 0:
                        time.sleep(sleep_time)
                
                self.prog_win.log(f" > Finished slide. Captured {frame_count} frames.")

            self.prog_win.log("Finalizing video file...")
            if writer:
                writer.close()
                writer = None
            
            if self.prog_win.cancelled:
                 self.root.after(0, lambda: messagebox.showinfo("Cancelled", "Recording aborted."))
                 try: os.remove(save_path) 
                 except: pass
            else:
                self.root.after(0, lambda: messagebox.showinfo("Success", "Smooth Video Saved Successfully!"))
                
            self.root.after(0, self.prog_win.destroy)
            
        except Exception as e:
            print(f"Error: {e}")
            err = traceback.format_exc()
            if self.prog_win and self.prog_win.winfo_exists():
                self.prog_win.log(f"ERROR: {e}")
            self.root.after(0, lambda: messagebox.showerror("Error", f"Recording Failed:\n{e}"))
            
        finally:
            if writer: 
                try: writer.close()
                except: pass
            if driver:
                try: driver.quit()
                except: pass
            
            self.root.after(0, lambda: self.status_var.set("Ready"))
            self.root.after(0, lambda: self.toggle_controls(False))
            self.root.after(0, lambda: self.btn_export.config(text="🎥 Record Smooth MP4", state=tk.NORMAL))

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = AdvancedHTMLViewer()
    app.run()