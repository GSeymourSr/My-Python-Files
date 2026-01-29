import os
import json
import hashlib
import datetime
import threading
import queue
from pathlib import Path

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageTk
import rembg  # ## NEW ## For background removal

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

# ===============================
# Config
# ===============================
## NEW ## Default output folder in the user's home directory for better portability
DEFAULT_OUTPUT_FOLDER = Path.home() / "AI Content Crops"
CONFIG_FILE = Path.home() / ".grid_crop_config.json"

# Theme
COLOR_BG = "#0f172a"       # slate-900
COLOR_PANEL = "#111827"    # gray-900
COLOR_TEXT = "#e5e7eb"     # gray-200
COLOR_ACCENT = "#a78bfa"   # violet-300
COLOR_ACCENT_2 = "#34d399" # emerald-400
COLOR_WARN = "#f59e0b"     # amber-500
COLOR_OK = "#22c55e"       # green-500
COLOR_ERR = "#ef4444"      # red-500

# ===============================
# Helpers: history, hashing, config
# ===============================

## NEW ## Config persistence for output folder
def _load_config():
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def _save_config(config):
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)
    except Exception as e:
        print(f"Config save error: {e}")

def _load_history(history_path):
    if os.path.exists(history_path):
        try:
            with open(history_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def _save_history(hist, history_path):
    try:
        with open(history_path, "w", encoding="utf-8") as f:
            json.dump(hist, f, indent=2)
    except Exception as e:
        print("History save error:", e)

def file_hash(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

## NEW ## Core function for background removal and auto-cropping
def process_single_image_post_crop(input_path, output_path):
    """Removes background and crops to the content."""
    try:
        with open(input_path, 'rb') as i:
            input_data = i.read()
            # Use rembg to remove the background
            output_data = rembg.remove(input_data)
            
            # Open the result with Pillow to auto-crop
            img = Image.open(io.BytesIO(output_data))
            
            # Get the bounding box of the non-transparent parts
            bbox = img.getbbox()
            if bbox:
                img = img.crop(bbox)
            
            img.save(output_path, 'PNG')
            return True
    except Exception as e:
        print(f"Failed to process {os.path.basename(input_path)}: {e}")
        return False

# ===============================
# Draggable Line (Matplotlib) - (No changes needed here)
# ===============================
class DraggableLine:
    def __init__(self, ax, line, orientation, vmin, vmax):
        self.ax = ax
        self.line = line
        self.orientation = orientation
        self.vmin = vmin
        self.vmax = vmax
        self._press_ref = None
        self._moving = False
        self._threshold = 1.0
        self.selected = False

        self.line.set_picker(6)
        self.cid_press = line.figure.canvas.mpl_connect('button_press_event', self._on_press)
        self.cid_release = line.figure.canvas.mpl_connect('button_release_event', self._on_release)
        self.cid_move = line.figure.canvas.mpl_connect('motion_notify_event', self._on_motion)
        self.set_selected(False)

    def get_pos(self):
        return float(self.line.get_xdata()[0]) if self.orientation == 'vertical' else float(self.line.get_ydata()[0])

    def set_pos(self, val):
        val = max(self.vmin, min(val, self.vmax))
        if self.orientation == 'vertical':
            self.line.set_xdata([val, val])
        else:
            self.line.set_ydata([val, val])
        self.line.figure.canvas.draw_idle()

    def set_selected(self, sel: bool):
        self.selected = sel
        self.line.set_linewidth(3.0 if sel else 2.0)
        self.line.set_color(COLOR_ACCENT_2 if sel else COLOR_ACCENT)
        self.line.set_alpha(0.95 if sel else 0.8)
        self.line.figure.canvas.draw_idle()

    def _on_press(self, event):
        if event.inaxes != self.ax: return
        contains, _ = self.line.contains(event)
        if not contains: return
        if hasattr(self.ax.figure, '_owner_app'):
            self.ax.figure._owner_app._select_line(self)
        self._press_ref = event.xdata if self.orientation == 'vertical' else event.ydata
        self._start_pos = self.get_pos()
        self._moving = False

    def _on_motion(self, event):
        if self._press_ref is None or event.inaxes != self.ax: return
        curr = event.xdata if self.orientation == 'vertical' else event.ydata
        if curr is None: return
        delta = curr - self._press_ref
        if not self._moving and abs(delta) < self._threshold: return
        self._moving = True
        self.set_pos(self._start_pos + delta)

    def _on_release(self, event):
        self._press_ref = None
        self._moving = False
        self.line.figure.canvas.draw_idle()

# ===============================
# Main App
# ===============================
class CropWorkstation(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Whimsical Crop Workstation ✂️✨ v2.0")
        self.configure(bg=COLOR_BG)
        self.geometry("1400x900")
        self.minsize(1200, 750)

        ## NEW ## Load config and set up dynamic paths
        self.config = _load_config()
        self.output_folder = self.config.get("output_folder", str(DEFAULT_OUTPUT_FOLDER))
        self._update_paths(self.output_folder) # This sets history path and loads history

        self.image_path = None
        self.image = None
        self.img_w, self.img_h = 0, 0
        self.vert, self.horz = [], []
        self.selected = None
        self.rows = tk.IntVar(value=2)
        self.cols = tk.IntVar(value=2)
        
        ## NEW ## Queue for thread communication
        self.processing_queue = queue.Queue()

        self._build_ui()
        self._bind_keys()

    ## NEW ## Method to handle path updates
    def _update_paths(self, new_folder_path):
        self.output_folder = new_folder_path
        Path(self.output_folder).mkdir(parents=True, exist_ok=True)
        self.history_path = os.path.join(self.output_folder, "cropped_history.json")
        self.history = _load_history(self.history_path)
        self.config["output_folder"] = self.output_folder
        _save_config(self.config)
        if hasattr(self, 'output_path_label'): # check if UI is built
            self.output_path_label.config(text=f"Output: {self.output_folder}")
        self.status_ok(f"Output folder set to: {self.output_folder}")

    def _build_ui(self):
        top = tk.Frame(self, bg=COLOR_PANEL)
        top.pack(side=tk.TOP, fill=tk.X)

        s = ttk.Style()
        s.theme_use('clam')
        s.configure('TButton', background=COLOR_PANEL, foreground=COLOR_TEXT, padding=8)
        s.map('TButton', background=[('active', COLOR_ACCENT)])
        s.configure('Accent.TButton', background=COLOR_ACCENT, foreground=COLOR_BG)
        s.configure('Good.TButton', background=COLOR_ACCENT_2, foreground=COLOR_BG)
        ## NEW ## Style for progress bar
        s.configure("custom.Horizontal.TProgressbar", foreground=COLOR_ACCENT_2, background=COLOR_ACCENT_2, troughcolor=COLOR_PANEL)

        left_buttons = tk.Frame(top, bg=COLOR_PANEL)
        left_buttons.pack(side=tk.LEFT, padx=8, pady=8)

        ttk.Button(left_buttons, text='📂 Load Image', command=self.load_image).pack(side=tk.LEFT, padx=4)
        ttk.Button(left_buttons, text='💾 Save Crops', command=self.save_crops, style='Good.TButton').pack(side=tk.LEFT, padx=4)
        ## NEW ## Button to set output directory
        ttk.Button(left_buttons, text='🗂️ Set Output', command=self.set_output_folder).pack(side=tk.LEFT, padx=4)
        ttk.Button(left_buttons, text='🖼️ Show History', command=self.show_previous_crops).pack(side=tk.LEFT, padx=4)

        right = tk.Frame(top, bg=COLOR_PANEL)
        right.pack(side=tk.RIGHT, padx=8, pady=8)
        tk.Label(right, text='Rows', bg=COLOR_PANEL, fg=COLOR_TEXT).pack(side=tk.LEFT, padx=(0,4))
        self.sb_rows = tk.Spinbox(right, from_=1, to=30, width=4, textvariable=self.rows, command=self.redraw_grid)
        self.sb_rows.pack(side=tk.LEFT)
        tk.Label(right, text='Cols', bg=COLOR_PANEL, fg=COLOR_TEXT).pack(side=tk.LEFT, padx=(12,4))
        self.sb_cols = tk.Spinbox(right, from_=1, to=30, width=4, textvariable=self.cols, command=self.redraw_grid)
        self.sb_cols.pack(side=tk.LEFT)
        
        ## NEW ## Label to display current output path
        self.output_path_label = tk.Label(top, text=f"Output: {self.output_folder}", bg=COLOR_PANEL, fg=COLOR_ACCENT, wraplength=400)
        self.output_path_label.pack(side=tk.LEFT, padx=20, fill=tk.X, expand=True)

        center = tk.Frame(self, bg=COLOR_BG)
        center.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.fig = Figure(figsize=(8,6), dpi=100, facecolor=COLOR_BG)
        self.ax = self.fig.add_subplot(111)
        self.ax.set_axis_off()
        self.ax.set_facecolor('#0b1220')
        self.fig._owner_app = self
        self.fig.tight_layout(pad=0)

        self.canvas = FigureCanvasTkAgg(self.fig, master=center)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        self.status = tk.Label(self, text='Welcome! Load an image to begin.', bg=COLOR_PANEL, fg=COLOR_TEXT, anchor='w', padx=10)
        self.status.pack(side=tk.BOTTOM, fill=tk.X)

    def _bind_keys(self):
        self.bind('<Left>', lambda e: self.nudge(-1, 0))
        self.bind('<Right>', lambda e: self.nudge(1, 0))
        self.bind('<Up>', lambda e: self.nudge(0, -1))
        self.bind('<Down>', lambda e: self.nudge(0, 1))
        self.bind('<Shift-Left>', lambda e: self.nudge(-10, 0))
        self.bind('<Shift-Right>', lambda e: self.nudge(10, 0))
        self.bind('<Shift-Up>', lambda e: self.nudge(0, -10))
        self.bind('<Shift-Down>', lambda e: self.nudge(0, 10))
        self.bind('<Control-s>', lambda e: self.save_crops())
        self.bind('<Control-o>', lambda e: self.load_image())
        self.fig.canvas.mpl_connect('button_press_event', self._on_mpl_click)

    ## NEW ## Command for the "Set Output" button
    def set_output_folder(self):
        path = filedialog.askdirectory(title="Select Output Folder", initialdir=self.output_folder)
        if path:
            self._update_paths(path)

    # =============================
    # Image Loading & Duplicate Check
    # =============================
    def load_image(self):
        path = filedialog.askopenfilename(title='Select an Image', filetypes=[('Image Files', '*.jpg;*.jpeg;*.png;*.bmp;*.tiff')])
        if not path: return
        try:
            img = Image.open(path)
        except Exception as e:
            messagebox.showerror('Error', f'Failed to load image:\n{e}')
            return

        h = file_hash(path)
        record = self.history.get(h)
        if record:
            self._dup_dialog(path, img, record)
        else:
            self._finalize_load(path, img)
    
    # ... (dup_dialog and finalize_load are mostly unchanged) ...
    def _dup_dialog(self, path, img, record):
        dlg = tk.Toplevel(self)
        dlg.title('Already Cropped')
        dlg.configure(bg=COLOR_PANEL)
        dlg.transient(self)
        dlg.grab_set()

        msg = tk.Label(dlg, text=(
            f"⚠ This image was already cropped on {record.get('date', 'unknown')}\n\n"
            f"Path:\n{record.get('path', '')}\n\n"
            "Would you like to view previous crops or crop again?"),
            bg=COLOR_PANEL, fg=COLOR_TEXT, justify='left')
        msg.pack(padx=16, pady=16)

        btns = tk.Frame(dlg, bg=COLOR_PANEL)
        btns.pack(pady=8)

        def view_prev():
            self._show_crops_list(record.get('crops', []), title='Previously Saved Crops')
        def crop_again():
            dlg.destroy()
            self._finalize_load(path, img)
        def cancel():
            dlg.destroy()

        ttk.Button(btns, text='🖼 View Previous Crops', command=view_prev).pack(side=tk.LEFT, padx=6)
        ttk.Button(btns, text='✂️ Crop Again', command=crop_again, style='Accent.TButton').pack(side=tk.LEFT, padx=6)
        ttk.Button(btns, text='Cancel', command=cancel).pack(side=tk.LEFT, padx=6)

    def _finalize_load(self, path, img):
        self.image_path = path
        self.image = img.convert("RGBA") # Ensure it has alpha for consistency
        self.img_w, self.img_h = img.size

        self.ax.clear()
        self.ax.set_axis_off()
        self.ax.imshow(img, origin='upper')
        self.ax.set_xlim(0, self.img_w)
        self.ax.set_ylim(self.img_h, 0)
        self.fig.tight_layout(pad=0)
        self.canvas.draw()

        self.status_ok(f"Loaded: {os.path.basename(path)}  ({self.img_w}×{self.img_h})")
        self._build_grid()

    # =============================
    # Grid & Selection - (No changes needed here)
    # =============================
    def _build_grid(self):
        for dl in self.vert + self.horz:
            try: dl.line.remove()
            except: pass
        self.vert.clear()
        self.horz.clear()
        self.selected = None

        cols = max(1, int(self.cols.get()))
        rows = max(1, int(self.rows.get()))

        for i in range(1, cols):
            x = i * (self.img_w / cols)
            l, = self.ax.plot([x, x], [0, self.img_h], linestyle='--', color=COLOR_ACCENT)
            self.vert.append(DraggableLine(self.ax, l, 'vertical', 0, self.img_w))

        for j in range(1, rows):
            y = j * (self.img_h / rows)
            l, = self.ax.plot([0, self.img_w], [y, y], linestyle='--', color=COLOR_ACCENT)
            self.horz.append(DraggableLine(self.ax, l, 'horizontal', 0, self.img_h))

        self.canvas.draw()
        self.status_info('Tip: Click a line to select. Use Arrow keys to nudge (Shift = 10px).')

    def redraw_grid(self):
        if self.image: self._build_grid()

    def _on_mpl_click(self, event):
        if event.inaxes != self.ax: return
        cand, best = None, 1e12
        for dl in self.vert:
            d = abs((event.xdata or 0) - dl.get_pos())
            if d < best: best, cand = d, dl
        for dl in self.horz:
            d = abs((event.ydata or 0) - dl.get_pos())
            if d < best: best, cand = d, dl
        if cand: self._select_line(cand)

    def _select_line(self, dl: DraggableLine):
        if self.selected and self.selected is not dl:
            self.selected.set_selected(False)
        self.selected = dl
        dl.set_selected(True)
        self.status_ok('Line selected. Use arrows to move. Hold Shift for 10px steps.')

    def nudge(self, dx, dy):
        if not self.selected:
            self.status_warn('No line selected. Click near a line to select it.')
            return
        new_pos = self.selected.get_pos() + (dx if self.selected.orientation == 'vertical' else dy)
        self.selected.set_pos(new_pos)
        self.status_ok('Nudged ✨')

    # =============================
    # Cropping & Post-Processing
    # =============================
    def _boundaries(self):
        xs = [0] + sorted([dl.get_pos() for dl in self.vert]) + [self.img_w]
        ys = [0] + sorted([dl.get_pos() for dl in self.horz]) + [self.img_h]
        return xs, ys

    def save_crops(self):
        if not self.image:
            self.status_err('No image loaded.')
            return
        
        ## NEW ## Check if output folder is set and writable
        try:
            test_file = Path(self.output_folder) / ".test_write"
            test_file.touch()
            test_file.unlink()
        except Exception as e:
            messagebox.showerror("Output Error", f"Cannot write to output folder:\n{self.output_folder}\n\nError: {e}\n\nPlease select a valid folder.")
            return

        xs, ys = self._boundaries()
        base_name = Path(self.image_path).stem
        base_ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        saved = []
        counter = 0

        for j in range(len(ys) - 1):
            for i in range(len(xs) - 1):
                L, R = int(xs[i]), int(xs[i+1])
                T, B = int(ys[j]), int(ys[j+1])
                if L >= R or T >= B: continue # Skip zero-size crops
                
                crop = self.image.crop((L, T, R, B))
                ## NEW ## More descriptive filename
                fname = f"{base_name}_crop_{j:02d}x{i:02d}_{base_ts}.png"
                out = os.path.join(self.output_folder, fname)
                try:
                    crop.save(out, 'PNG')
                    saved.append(out)
                except Exception as e:
                    print('Save failed', out, e)
                counter += 1
        if saved:
            h = file_hash(self.image_path)
            self.history[h] = {
                'path': self.image_path,
                'date': datetime.datetime.now().isoformat(),
                'crops': saved,
            }
            _save_history(self.history, self.history_path)

            self.status_ok(f'✅ Saved {len(saved)} crops to {self.output_folder}.')
            self._post_save_dialog(saved)
        else:
            self.status_warn('No crops were saved.')

    def _post_save_dialog(self, paths):
        dlg = tk.Toplevel(self)
        dlg.title('Crops Saved')
        dlg.configure(bg=COLOR_PANEL)
        dlg.transient(self)
        dlg.grab_set()

        tk.Label(dlg, text=f'Saved {len(paths)} crops. What next?', bg=COLOR_PANEL, fg=COLOR_TEXT).pack(padx=12, pady=12)
        btns = tk.Frame(dlg, bg=COLOR_PANEL)
        btns.pack(pady=8, fill=tk.X, expand=True)

        def open_folder():
            try: os.startfile(self.output_folder)
            except: messagebox.showinfo('Output Folder', self.output_folder)

        def view_now():
            self._show_crops_list(paths, title='Crops Preview')

        ## NEW ## Function to launch the post-processing step
        def process_now():
            self.run_post_processing(paths)

        def next_img():
            dlg.destroy()
            self.load_image()

        ttk.Button(btns, text='🗂️ Open Folder', command=open_folder).pack(side=tk.LEFT, padx=6, expand=True)
        ttk.Button(btns, text='🖼️ Preview', command=view_now).pack(side=tk.LEFT, padx=6, expand=True)
        ## NEW ## Button to start post-processing
        ttk.Button(btns, text='✨ BG Remove & Crop', command=process_now, style='Accent.TButton').pack(side=tk.LEFT, padx=6, expand=True)
        ttk.Button(btns, text='➡️ Next Image', command=next_img).pack(side=tk.LEFT, padx=6, expand=True)

    ## NEW ## Entire section for Post-Processing with threading
    def run_post_processing(self, paths):
        # Create a dedicated subfolder for processed images
        processed_folder = Path(self.output_folder) / "_processed"
        processed_folder.mkdir(exist_ok=True)

        # Start the worker thread
        thread = threading.Thread(target=self._processing_worker, args=(paths, processed_folder), daemon=True)
        thread.start()

        # Show the progress dialog
        self._show_processing_dialog(len(paths), processed_folder)

    def _processing_worker(self, paths, processed_folder):
        """This function runs in a separate thread."""
        import io # Import here as it's only used in this thread
        
        for i, path in enumerate(paths):
            base_name = Path(path).stem
            output_path = processed_folder / f"{base_name}_processed.png"
            
            # Use a helper for the actual rembg/PIL logic
            success = self._process_single_image(path, str(output_path), io)
            
            # Put progress update into the queue for the main thread
            self.processing_queue.put({'type': 'progress', 'value': i + 1, 'success': success})
        
        self.processing_queue.put({'type': 'done'})

    def _process_single_image(self, input_path, output_path, io_module):
        """Helper to contain the core rembg logic and error handling."""
        try:
            with open(input_path, 'rb') as i:
                img_data = rembg.remove(i.read())
            img = Image.open(io_module.BytesIO(img_data))
            bbox = img.getbbox()
            if bbox: img = img.crop(bbox)
            img.save(output_path, 'PNG')
            return True
        except Exception as e:
            print(f"Error processing {input_path}: {e}")
            return False
        
    def _show_processing_dialog(self, total_files, processed_folder):
        dlg = tk.Toplevel(self)
        dlg.title("Processing Images...")
        dlg.configure(bg=COLOR_PANEL)
        dlg.transient(self)
        dlg.grab_set()
        dlg.geometry("450x150")

        status_label = tk.Label(dlg, text="Starting background removal...", bg=COLOR_PANEL, fg=COLOR_TEXT)
        status_label.pack(pady=(15, 5))

        progress = ttk.Progressbar(dlg, orient='horizontal', length=400, mode='determinate', maximum=total_files, style="custom.Horizontal.TProgressbar")
        progress.pack(pady=10, padx=15)

        # Use a frame for the final buttons
        done_frame = tk.Frame(dlg, bg=COLOR_PANEL)
        # done_frame will be packed later

        def check_queue():
            try:
                msg = self.processing_queue.get_nowait()
                if msg['type'] == 'progress':
                    progress['value'] = msg['value']
                    status_label.config(text=f"Processing {msg['value']} of {total_files}...")
                    dlg.update_idletasks()
                elif msg['type'] == 'done':
                    status_label.config(text=f"✅ Done! {total_files} images processed.", fg=COLOR_OK)
                    progress.pack_forget() # Hide progress bar
                    
                    # Show final action buttons
                    def open_processed():
                        try: os.startfile(processed_folder)
                        except: messagebox.showinfo('Output Folder', str(processed_folder))
                    
                    ttk.Button(done_frame, text="🗂️ Open Processed Folder", command=open_processed).pack(side=tk.LEFT, padx=10)
                    ttk.Button(done_frame, text="Close", command=dlg.destroy, style="Accent.TButton").pack(side=tk.LEFT, padx=10)
                    done_frame.pack(pady=10)
                    return # Stop polling
            except queue.Empty:
                pass # No messages, continue polling
            
            dlg.after(100, check_queue) # Poll the queue every 100ms

        check_queue()

    # =============================
    # UI Helpers (Preview, Status)
    # =============================
    def _show_crops_list(self, paths, title='Crops'):
        # This is large and unchanged, keeping it as is.
        if not paths:
            messagebox.showinfo('Crops', 'No crops available to show.')
            return
        dlg = tk.Toplevel(self)
        dlg.title(title)
        dlg.geometry('1000x700')
        dlg.configure(bg=COLOR_PANEL)

        container = tk.Frame(dlg, bg=COLOR_PANEL)
        container.pack(fill=tk.BOTH, expand=True)
        canvas = tk.Canvas(container, bg=COLOR_PANEL, highlightthickness=0)
        vsb = ttk.Scrollbar(container, orient='vertical', command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        inner = tk.Frame(canvas, bg=COLOR_PANEL)
        canvas.create_window((0,0), window=inner, anchor='nw')
        inner.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))

        thumbs = []
        for idx, p in enumerate(paths):
            try:
                im = Image.open(p)
                im.thumbnail((260, 220))
                tkimg = ImageTk.PhotoImage(im)
                thumbs.append(tkimg)

                frame = tk.Frame(inner, bg=COLOR_PANEL, bd=1, relief='solid')
                frame.grid(row=idx//3, column=idx%3, padx=8, pady=8, sticky='nsew')

                tk.Label(frame, image=tkimg, bg=COLOR_PANEL).pack(padx=8, pady=8)
                tk.Label(frame, text=os.path.basename(p), bg=COLOR_PANEL, fg=COLOR_TEXT, wraplength=240).pack(padx=8, pady=(0,8))
            except Exception as e:
                print('Thumb failed', p, e)
        dlg._thumb_refs = thumbs

    def show_previous_crops(self):
        if not self.image_path:
            messagebox.showinfo('Previous Crops', 'Load an image first to check its history.')
            return
        h = file_hash(self.image_path)
        rec = self.history.get(h)
        if not rec or not rec.get('crops'):
            messagebox.showinfo('Previous Crops', 'No previous crops found in history for this image.')
            return
        self._show_crops_list(rec.get('crops', []), title='Previously Saved Crops')

    def status_set(self, text, fg=COLOR_TEXT): self.status.configure(text=text, fg=fg)
    def status_ok(self, text): self.status_set(text, fg=COLOR_OK)
    def status_info(self, text): self.status_set(text, fg=COLOR_TEXT)
    def status_warn(self, text): self.status_set(text, fg=COLOR_WARN)
    def status_err(self, text): self.status_set(text, fg=COLOR_ERR)


if __name__ == '__main__':
    # Add io module to global scope for the worker thread if it's not already there.
    # This avoids potential issues with some module loaders.
    import io
    app = CropWorkstation()
    app.mainloop()