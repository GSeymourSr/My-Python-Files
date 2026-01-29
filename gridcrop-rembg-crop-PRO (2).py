import os
import io
import json
import hashlib
import datetime
import threading
import queue
from pathlib import Path

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageTk
import rembg  # You must have this installed: pip install rembg

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

# ===============================
# Config
# ===============================
## CHANGED ## Default folders for the two-step workflow
DEFAULT_CROP_OUTPUT_FOLDER = Path.home() / "GridCrop_Input"
DEFAULT_FINAL_OUTPUT_FOLDER = Path.home() / "GridCrop_Output"
# The config file will be saved in the final output folder
CONFIG_FILENAME = ".grid_crop_config.json"

# Theme
COLOR_BG = "#0f172a"
COLOR_PANEL = "#111827"
COLOR_TEXT = "#e5e7eb"
COLOR_ACCENT = "#a78bfa"
COLOR_ACCENT_2 = "#34d399"
COLOR_WARN = "#f59e0b"
COLOR_OK = "#22c55e"
COLOR_ERR = "#ef4444"

# ===============================
# Helpers: config, history & hashing
# ===============================

def _load_config(config_path):
    if config_path.exists():
        try:
            with open(config_path, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def _save_config(config, config_path):
    try:
        with open(config_path, "w") as f:
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
        Path(history_path).parent.mkdir(parents=True, exist_ok=True)
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

# ===============================
# Draggable Line (Matplotlib) - (No changes)
# ===============================
class DraggableLine:
    def __init__(self, ax, line, orientation, vmin, vmax):
        self.ax, self.line, self.orientation = ax, line, orientation
        self.vmin, self.vmax = vmin, vmax
        self._press_ref, self._moving, self.selected = None, False, False
        self._threshold = 1.0
        self.line.set_picker(6)
        self.cid_press = line.figure.canvas.mpl_connect('button_press_event', self._on_press)
        self.cid_release = line.figure.canvas.mpl_connect('button_release_event', self._on_release)
        self.cid_move = line.figure.canvas.mpl_connect('motion_notify_event', self._on_motion)
        self.set_selected(False)

    def get_pos(self):
        return float(self.line.get_xdata()[0]) if self.orientation == 'vertical' else float(self.line.get_ydata()[0])

    def set_pos(self, val):
        val = max(self.vmin, min(val, self.vmax))
        if self.orientation == 'vertical': self.line.set_xdata([val, val])
        else: self.line.set_ydata([val, val])
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
        if hasattr(self.ax.figure, '_owner_app'): self.ax.figure._owner_app._select_line(self)
        self._press_ref = event.xdata if self.orientation == 'vertical' else event.ydata
        self._start_pos, self._moving = self.get_pos(), False

    def _on_motion(self, event):
        if self._press_ref is None or event.inaxes != self.ax: return
        curr = event.xdata if self.orientation == 'vertical' else event.ydata
        if curr is None: return
        delta = curr - self._press_ref
        if not self._moving and abs(delta) < self._threshold: return
        self._moving = True
        self.set_pos(self._start_pos + delta)

    def _on_release(self, event):
        self._press_ref, self._moving = None, False
        self.line.figure.canvas.draw_idle()


# ===============================
# Main App
# ===============================
class CropWorkstation(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Professional Grid Crop & Process Workstation ✨")
        self.configure(bg=COLOR_BG)
        self.geometry("1400x900")
        self.minsize(1200, 750)

        self.image_path, self.image = None, None
        self.img_w, self.img_h = 0, 0
        self.vert, self.horz, self.selected = [], [], None
        self.rows, self.cols = tk.IntVar(value=2), tk.IntVar(value=2)
        self.processing_queue = queue.Queue()

        ## FIXED ## Build UI first so all widgets exist before they are accessed.
        self._build_ui()
        self._initialize_paths()
        self._bind_keys()

    ## CHANGED ## Handles loading and setting up the two-folder path system
    def _initialize_paths(self):
        # Temporarily use default path to find config
        temp_config_path = Path(DEFAULT_FINAL_OUTPUT_FOLDER) / CONFIG_FILENAME
        config = _load_config(temp_config_path)
        
        # Load paths from config, or use defaults
        crop_folder = config.get("crop_output_folder", str(DEFAULT_CROP_OUTPUT_FOLDER))
        final_folder = config.get("final_output_folder", str(DEFAULT_FINAL_OUTPUT_FOLDER))

        self.update_crop_output_path(crop_folder, save_config=False)
        self.update_final_output_path(final_folder, save_config=False)
        
        # Now save the potentially updated config to the correct final location
        self._save_current_config()

    def _build_ui(self):
        top_bar = tk.Frame(self, bg=COLOR_PANEL)
        top_bar.pack(side=tk.TOP, fill=tk.X, ipady=5)

        s = ttk.Style()
        s.theme_use('clam')
        s.configure('TButton', background=COLOR_PANEL, foreground=COLOR_TEXT, padding=8)
        s.map('TButton', background=[('active', COLOR_ACCENT)])
        s.configure('Accent.TButton', background=COLOR_ACCENT, foreground=COLOR_BG)
        s.configure('Good.TButton', background=COLOR_ACCENT_2, foreground=COLOR_BG)
        s.configure("custom.Horizontal.TProgressbar", foreground=COLOR_ACCENT_2, background=COLOR_ACCENT_2, troughcolor=COLOR_PANEL)

        # --- Left Controls ---
        left_controls = tk.Frame(top_bar, bg=COLOR_PANEL)
        left_controls.pack(side=tk.LEFT, padx=8)
        ttk.Button(left_controls, text='📂 Load Image', command=self.load_image).pack(side=tk.LEFT, padx=4)
        ttk.Button(left_controls, text='💾 Save Crops', command=self.save_crops, style='Good.TButton').pack(side=tk.LEFT, padx=4)
        ttk.Button(left_controls, text='🖼️ Show History', command=self.show_previous_crops).pack(side=tk.LEFT, padx=4)

        # --- Center Path Display ---
        path_frame = tk.Frame(top_bar, bg=COLOR_PANEL)
        path_frame.pack(side=tk.LEFT, padx=20, fill=tk.X, expand=True)

        ttk.Button(path_frame, text='Set Crop Output', command=self.set_crop_output_folder).grid(row=0, column=0, padx=(0, 10))
        self.crop_output_label = tk.Label(path_frame, text="Crop Output: Not set", bg=COLOR_PANEL, fg=COLOR_ACCENT, wraplength=400, justify='left')
        self.crop_output_label.grid(row=0, column=1, sticky='w')

        ttk.Button(path_frame, text='Set Final Output', command=self.set_final_output_folder).grid(row=1, column=0, padx=(0, 10), pady=(5,0))
        self.final_output_label = tk.Label(path_frame, text="Final Output: Not set", bg=COLOR_PANEL, fg=COLOR_ACCENT_2, wraplength=400, justify='left')
        self.final_output_label.grid(row=1, column=1, sticky='w')
        
        # --- Right Controls ---
        right_controls = tk.Frame(top_bar, bg=COLOR_PANEL)
        right_controls.pack(side=tk.RIGHT, padx=8)
        tk.Label(right_controls, text='Rows', bg=COLOR_PANEL, fg=COLOR_TEXT).pack(side=tk.LEFT)
        tk.Spinbox(right_controls, from_=1, to=30, width=4, textvariable=self.rows, command=self.redraw_grid).pack(side=tk.LEFT, padx=(4,12))
        tk.Label(right_controls, text='Cols', bg=COLOR_PANEL, fg=COLOR_TEXT).pack(side=tk.LEFT)
        tk.Spinbox(right_controls, from_=1, to=30, width=4, textvariable=self.cols, command=self.redraw_grid).pack(side=tk.LEFT, padx=4)

        # --- Matplotlib Canvas ---
        center = tk.Frame(self, bg=COLOR_BG)
        center.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.fig = Figure(figsize=(8,6), dpi=100, facecolor=COLOR_BG)
        self.ax = self.fig.add_subplot(111, facecolor='#0b1220')
        self.ax.set_axis_off()
        self.fig._owner_app = self
        self.fig.tight_layout(pad=0)
        self.canvas = FigureCanvasTkAgg(self.fig, master=center)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        # --- Status Bar ---
        self.status = tk.Label(self, text='Welcome! Set your folders and load an image.', bg=COLOR_PANEL, fg=COLOR_TEXT, anchor='w', padx=10)
        self.status.pack(side=tk.BOTTOM, fill=tk.X)

    def _bind_keys(self):
        # Nudging, save, load shortcuts...
        self.bind('<Left>', lambda e: self.nudge(-1, 0)); self.bind('<Right>', lambda e: self.nudge(1, 0))
        self.bind('<Up>', lambda e: self.nudge(0, -1)); self.bind('<Down>', lambda e: self.nudge(0, 1))
        self.bind('<Shift-Left>', lambda e: self.nudge(-10, 0)); self.bind('<Shift-Right>', lambda e: self.nudge(10, 0))
        self.bind('<Shift-Up>', lambda e: self.nudge(0, -10)); self.bind('<Shift-Down>', lambda e: self.nudge(0, 10))
        self.bind('<Control-s>', lambda e: self.save_crops())
        self.bind('<Control-o>', lambda e: self.load_image())
        self.fig.canvas.mpl_connect('button_press_event', self._on_mpl_click)

    ## CHANGED ## Path management functions
    def _save_current_config(self):
        config = {
            "crop_output_folder": self.crop_output_folder,
            "final_output_folder": self.final_output_folder
        }
        _save_config(config, self.config_path)
    
    def update_crop_output_path(self, path, save_config=True):
        self.crop_output_folder = str(path)
        Path(self.crop_output_folder).mkdir(parents=True, exist_ok=True)
        self.crop_output_label.config(text=f"Crop Output: {self.crop_output_folder}")
        if save_config: self._save_current_config()

    def update_final_output_path(self, path, save_config=True):
        self.final_output_folder = str(path)
        Path(self.final_output_folder).mkdir(parents=True, exist_ok=True)
        self.final_output_label.config(text=f"Final Output: {self.final_output_folder}")
        # Update config and history path locations
        self.config_path = Path(self.final_output_folder) / CONFIG_FILENAME
        self.history_path = Path(self.final_output_folder) / "cropped_history.json"
        self.history = _load_history(self.history_path)
        if save_config: self._save_current_config()

    def set_crop_output_folder(self):
        path = filedialog.askdirectory(title="Select Folder for Grid Crops (Processing Input)", initialdir=self.crop_output_folder)
        if path:
            self.update_crop_output_path(path)
            self.status_ok(f"Crop output folder set to: {path}")

    def set_final_output_folder(self):
        path = filedialog.askdirectory(title="Select Folder for Final Processed Images", initialdir=self.final_output_folder)
        if path:
            self.update_final_output_path(path)
            self.status_ok(f"Final output folder set to: {path}")

    def load_image(self):
        path = filedialog.askopenfilename(title='Select an Image', filetypes=[('Image Files', '*.jpg;*.jpeg;*.png;*.bmp;*.tiff')])
        if not path: return
        try:
            img = Image.open(path)
        except Exception as e:
            messagebox.showerror('Error', f'Failed to load image:\n{e}'); return

        h = file_hash(path)
        if h in self.history:
            self._dup_dialog(path, img, self.history[h])
        else:
            self._finalize_load(path, img)

    def _finalize_load(self, path, img):
        self.image_path = path
        self.image = img.convert("RGBA")
        self.img_w, self.img_h = img.size
        self.ax.clear()
        self.ax.set_axis_off()
        self.ax.imshow(img, origin='upper')
        self.ax.set_xlim(0, self.img_w); self.ax.set_ylim(self.img_h, 0)
        self.fig.tight_layout(pad=0)
        self.canvas.draw()
        self.status_ok(f"Loaded: {os.path.basename(path)} ({self.img_w}x{self.img_h})")
        self._build_grid()
    
    # ... (dup_dialog, _build_grid, redraw_grid, _on_mpl_click, _select_line, nudge - mostly unchanged) ...
    def _dup_dialog(self, path, img, record):
        dlg = tk.Toplevel(self); dlg.title('Already Cropped'); dlg.configure(bg=COLOR_PANEL); dlg.transient(self); dlg.grab_set()
        msg_text = f"⚠ This image was already cropped on {record.get('date', 'unknown')}\n\nPath:\n{record.get('path', '')}\n\nWould you like to view previous crops or crop again?"
        tk.Label(dlg, text=msg_text, bg=COLOR_PANEL, fg=COLOR_TEXT, justify='left').pack(padx=16, pady=16)
        btns = tk.Frame(dlg, bg=COLOR_PANEL); btns.pack(pady=8)
        def view_prev(): self._show_crops_list(record.get('crops', []), title='Previously Saved Crops')
        def crop_again(): dlg.destroy(); self._finalize_load(path, img)
        ttk.Button(btns, text='🖼 View Previous', command=view_prev).pack(side=tk.LEFT, padx=6)
        ttk.Button(btns, text='✂️ Crop Again', command=crop_again, style='Accent.TButton').pack(side=tk.LEFT, padx=6)
        ttk.Button(btns, text='Cancel', command=dlg.destroy).pack(side=tk.LEFT, padx=6)

    def _build_grid(self):
        for dl in self.vert + self.horz:
            try: dl.line.remove()
            except: pass
        self.vert.clear(); self.horz.clear(); self.selected = None
        cols, rows = max(1, self.cols.get()), max(1, self.rows.get())
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
        all_lines = self.vert + self.horz
        for dl in all_lines:
            d = abs((event.xdata or 0) - dl.get_pos()) if dl.orientation == 'vertical' else abs((event.ydata or 0) - dl.get_pos())
            if d < best: best, cand = d, dl
        if cand: self._select_line(cand)

    def _select_line(self, dl: DraggableLine):
        if self.selected and self.selected is not dl: self.selected.set_selected(False)
        self.selected = dl; dl.set_selected(True)
        self.status_ok('Line selected. Use arrows to move. Hold Shift for 10px steps.')

    def nudge(self, dx, dy):
        if not self.selected: self.status_warn('No line selected. Click to select.'); return
        new_pos = self.selected.get_pos() + (dx if self.selected.orientation == 'vertical' else dy)
        self.selected.set_pos(new_pos)
        self.status_ok('Nudged ✨')

    def save_crops(self):
        if not self.image: self.status_err('No image loaded.'); return
        try:
            test_file = Path(self.crop_output_folder) / ".test_write"
            test_file.touch(); test_file.unlink()
        except Exception as e:
            messagebox.showerror("Output Error", f"Cannot write to Crop Output folder:\n{self.crop_output_folder}\n\nError: {e}\n\nPlease select a valid folder.")
            return

        xs = [0] + sorted([dl.get_pos() for dl in self.vert]) + [self.img_w]
        ys = [0] + sorted([dl.get_pos() for dl in self.horz]) + [self.img_h]
        base_name, base_ts = Path(self.image_path).stem, datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        saved = []
        for j in range(len(ys) - 1):
            for i in range(len(xs) - 1):
                L, R, T, B = int(xs[i]), int(xs[i+1]), int(ys[j]), int(ys[j+1])
                if L >= R or T >= B: continue
                crop = self.image.crop((L, T, R, B))
                fname = f"{base_name}_crop_{j:02d}x{i:02d}_{base_ts}.png"
                out = os.path.join(self.crop_output_folder, fname)
                try:
                    crop.save(out, 'PNG'); saved.append(out)
                except Exception as e:
                    print(f'Save failed for {out}: {e}')

        if saved:
            self.history[file_hash(self.image_path)] = {'path': self.image_path, 'date': datetime.datetime.now().isoformat(), 'crops': saved}
            _save_history(self.history, self.history_path)
            self.status_ok(f'✅ Saved {len(saved)} crops to {self.crop_output_folder}.')
            self._post_save_dialog(saved)
        else:
            self.status_warn('No crops were saved.')

    def _post_save_dialog(self, paths):
        dlg = tk.Toplevel(self); dlg.title('Crops Saved'); dlg.configure(bg=COLOR_PANEL); dlg.transient(self); dlg.grab_set()
        tk.Label(dlg, text=f'Saved {len(paths)} crops. What next?', bg=COLOR_PANEL, fg=COLOR_TEXT).pack(padx=12, pady=12)
        btns = tk.Frame(dlg, bg=COLOR_PANEL); btns.pack(pady=8, fill=tk.X, expand=True)
        def open_folder(): os.startfile(self.crop_output_folder)
        def view_now(): self._show_crops_list(paths, title='Crops Preview')
        def process_now(): dlg.destroy(); self.run_post_processing(paths)
        def next_img(): dlg.destroy(); self.load_image()
        ttk.Button(btns, text='🗂️ Open Folder', command=open_folder).pack(side=tk.LEFT, padx=6, expand=True)
        ttk.Button(btns, text='🖼️ Preview', command=view_now).pack(side=tk.LEFT, padx=6, expand=True)
        ttk.Button(btns, text='✨ BG Remove & Crop', command=process_now, style='Accent.TButton').pack(side=tk.LEFT, padx=6, expand=True)
        ttk.Button(btns, text='➡️ Next Image', command=next_img).pack(side=tk.LEFT, padx=6, expand=True)

    ## CHANGED ## Post-processing uses the final_output_folder
    def run_post_processing(self, paths):
        Path(self.final_output_folder).mkdir(exist_ok=True)
        thread = threading.Thread(target=self._processing_worker, args=(paths, self.final_output_folder), daemon=True)
        thread.start()
        self._show_processing_dialog(len(paths), self.final_output_folder)

    def _processing_worker(self, paths, final_output_folder):
        for i, path in enumerate(paths):
            base_name = Path(path).stem
            output_path = Path(final_output_folder) / f"{base_name}_processed.png"
            success = self._process_single_image(path, str(output_path))
            self.processing_queue.put({'type': 'progress', 'value': i + 1, 'success': success})
        self.processing_queue.put({'type': 'done'})

    def _process_single_image(self, input_path, output_path):
        try:
            with open(input_path, 'rb') as i:
                img_data = rembg.remove(i.read())
            img = Image.open(io.BytesIO(img_data))
            if bbox := img.getbbox(): img = img.crop(bbox)
            img.save(output_path, 'PNG')
            return True
        except Exception as e:
            print(f"Error processing {input_path}: {e}"); return False
        
    def _show_processing_dialog(self, total_files, output_folder):
        dlg = tk.Toplevel(self); dlg.title("Processing Images..."); dlg.configure(bg=COLOR_PANEL); dlg.transient(self); dlg.grab_set(); dlg.geometry("450x150")
        status_label = tk.Label(dlg, text="Starting background removal...", bg=COLOR_PANEL, fg=COLOR_TEXT); status_label.pack(pady=(15, 5))
        progress = ttk.Progressbar(dlg, orient='horizontal', length=400, mode='determinate', maximum=total_files, style="custom.Horizontal.TProgressbar"); progress.pack(pady=10, padx=15)
        done_frame = tk.Frame(dlg, bg=COLOR_PANEL)

        def check_queue():
            try:
                msg = self.processing_queue.get_nowait()
                if msg['type'] == 'progress':
                    progress['value'] = msg['value']
                    status_label.config(text=f"Processing {msg['value']} of {total_files}...")
                    dlg.update_idletasks()
                elif msg['type'] == 'done':
                    status_label.config(text=f"✅ Done! Processed images saved to Final Output.", fg=COLOR_OK)
                    progress.pack_forget()
                    def open_processed(): os.startfile(output_folder)
                    ttk.Button(done_frame, text="🗂️ Open Final Folder", command=open_processed).pack(side=tk.LEFT, padx=10)
                    ttk.Button(done_frame, text="Close", command=dlg.destroy, style="Accent.TButton").pack(side=tk.LEFT, padx=10)
                    done_frame.pack(pady=10)
                    return
            except queue.Empty: pass
            dlg.after(100, check_queue)
        check_queue()

    # ... (_show_crops_list and show_previous_crops are fine) ...
    def _show_crops_list(self, paths, title='Crops'):
        if not paths: messagebox.showinfo('Crops', 'No crops available to show.'); return
        dlg = tk.Toplevel(self); dlg.title(title); dlg.geometry('1000x700'); dlg.configure(bg=COLOR_PANEL)
        container = tk.Frame(dlg, bg=COLOR_PANEL); container.pack(fill=tk.BOTH, expand=True)
        canvas = tk.Canvas(container, bg=COLOR_PANEL, highlightthickness=0)
        vsb = ttk.Scrollbar(container, orient='vertical', command=canvas.yview); canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y); canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        inner = tk.Frame(canvas, bg=COLOR_PANEL); canvas.create_window((0,0), window=inner, anchor='nw')
        inner.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        thumbs = []
        for idx, p in enumerate(paths):
            try:
                with Image.open(p) as im:
                    im.thumbnail((260, 220)); tkimg = ImageTk.PhotoImage(im); thumbs.append(tkimg)
                frame = tk.Frame(inner, bg=COLOR_PANEL, bd=1, relief='solid'); frame.grid(row=idx//3, column=idx%3, padx=8, pady=8, sticky='nsew')
                tk.Label(frame, image=tkimg, bg=COLOR_PANEL).pack(padx=8, pady=8)
                tk.Label(frame, text=os.path.basename(p), bg=COLOR_PANEL, fg=COLOR_TEXT, wraplength=240).pack(padx=8, pady=(0,8))
            except Exception as e: print(f'Thumbnail failed for {p}: {e}')
        dlg._thumb_refs = thumbs

    def show_previous_crops(self):
        if not self.image_path: messagebox.showinfo('Previous Crops', 'Load an image to check its history.'); return
        rec = self.history.get(file_hash(self.image_path))
        if not rec or not rec.get('crops'): messagebox.showinfo('Previous Crops', 'No history found for this image.'); return
        self._show_crops_list(rec.get('crops', []), title='Previously Saved Crops')
    
    # --- Status helpers ---
    def status_set(self, text, fg=COLOR_TEXT): self.status.configure(text=text, fg=fg)
    def status_ok(self, text): self.status_set(text, fg=COLOR_OK)
    def status_info(self, text): self.status_set(text, fg=COLOR_TEXT)
    def status_warn(self, text): self.status_set(text, fg=COLOR_WARN)
    def status_err(self, text): self.status_set(text, fg=COLOR_ERR)

if __name__ == '__main__':
    app = CropWorkstation()
    app.mainloop()