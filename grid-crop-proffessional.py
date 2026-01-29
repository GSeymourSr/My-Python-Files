import os
import json
import hashlib
import datetime
from pathlib import Path

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageTk

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

# ===============================
# Config
# ===============================
OUTPUT_FOLDER = r"C:\- AI  NEW CONTENT"
Path(OUTPUT_FOLDER).mkdir(parents=True, exist_ok=True)
HISTORY_PATH = os.path.join(OUTPUT_FOLDER, "cropped_history.json")

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
# Helpers: history & hashing
# ===============================

def _load_history():
    if os.path.exists(HISTORY_PATH):
        try:
            with open(HISTORY_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def _save_history(hist):
    try:
        with open(HISTORY_PATH, "w", encoding="utf-8") as f:
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
# Draggable Line (Matplotlib)
# ===============================
class DraggableLine:
    def __init__(self, ax, line, orientation, vmin, vmax):
        self.ax = ax
        self.line = line
        self.orientation = orientation  # 'vertical' or 'horizontal'
        self.vmin = vmin
        self.vmax = vmax
        self._press_ref = None
        self._moving = False
        self._threshold = 1.0
        self.selected = False

        self.line.set_picker(6)  # for pick_event
        self.cid_press = line.figure.canvas.mpl_connect('button_press_event', self._on_press)
        self.cid_release = line.figure.canvas.mpl_connect('button_release_event', self._on_release)
        self.cid_move = line.figure.canvas.mpl_connect('motion_notify_event', self._on_motion)

        # default style
        self.set_selected(False)

    def get_pos(self):
        if self.orientation == 'vertical':
            return float(self.line.get_xdata()[0])
        return float(self.line.get_ydata()[0])

    def set_pos(self, val):
        val = max(self.vmin, min(val, self.vmax))
        if self.orientation == 'vertical':
            self.line.set_xdata([val, val])
        else:
            self.line.set_ydata([val, val])
        self.line.figure.canvas.draw_idle()

    def set_selected(self, sel: bool):
        self.selected = sel
        if sel:
            self.line.set_linewidth(3.0)
            self.line.set_color(COLOR_ACCENT_2)
            self.line.set_alpha(0.95)
        else:
            self.line.set_linewidth(2.0)
            self.line.set_color(COLOR_ACCENT)
            self.line.set_alpha(0.8)
        self.line.figure.canvas.draw_idle()

    # --- mouse handlers ---
    def _on_press(self, event):
        if event.inaxes != self.ax:
            return
        contains, _ = self.line.contains(event)
        if not contains:
            return
        # mark as selected via app hook
        fig = self.ax.figure
        if hasattr(fig, '_owner_app'):
            fig._owner_app._select_line(self)
        self._press_ref = event.xdata if self.orientation == 'vertical' else event.ydata
        self._start_pos = self.get_pos()
        self._moving = False

    def _on_motion(self, event):
        if self._press_ref is None or event.inaxes != self.ax:
            return
        curr = event.xdata if self.orientation == 'vertical' else event.ydata
        if curr is None:
            return
        delta = curr - self._press_ref
        if not self._moving and abs(delta) < self._threshold:
            return
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
        self.title("Whimsical Crop Workstation ✂️✨")
        self.configure(bg=COLOR_BG)
        self.geometry("1280x860")
        self.minsize(1100, 720)

        self.history = _load_history()
        self.image_path = None
        self.image = None  # PIL.Image
        self.img_w = 0
        self.img_h = 0
        self.vert = []  # DraggableLine list
        self.horz = []
        self.selected = None

        # rows/cols
        self.rows = tk.IntVar(value=2)
        self.cols = tk.IntVar(value=2)

        # --- UI ---
        self._build_ui()
        self._bind_keys()

    def _build_ui(self):
        # Top bar
        top = tk.Frame(self, bg=COLOR_PANEL)
        top.pack(side=tk.TOP, fill=tk.X)

        ttk.Style().theme_use('clam')
        s = ttk.Style()
        s.configure('TButton', background=COLOR_PANEL, foreground=COLOR_TEXT, padding=8)
        s.map('TButton', background=[('active', COLOR_ACCENT)])
        s.configure('Accent.TButton', background=COLOR_ACCENT, foreground=COLOR_BG)
        s.configure('Good.TButton', background=COLOR_ACCENT_2, foreground=COLOR_BG)

        ttk.Button(top, text='📂 Load Image', command=self.load_image, style='Accent.TButton').pack(side=tk.LEFT, padx=8, pady=8)
        ttk.Button(top, text='💾 Save Crops', command=self.save_crops, style='Good.TButton').pack(side=tk.LEFT, padx=8, pady=8)
        ttk.Button(top, text='🖼 Show Previous Crops', command=self.show_previous_crops).pack(side=tk.LEFT, padx=8, pady=8)

        right = tk.Frame(top, bg=COLOR_PANEL)
        right.pack(side=tk.RIGHT, padx=8, pady=8)
        tk.Label(right, text='Rows', bg=COLOR_PANEL, fg=COLOR_TEXT).pack(side=tk.LEFT, padx=(0,4))
        self.sb_rows = tk.Spinbox(right, from_=1, to=30, width=4, textvariable=self.rows, command=self.redraw_grid)
        self.sb_rows.pack(side=tk.LEFT)
        tk.Label(right, text='Cols', bg=COLOR_PANEL, fg=COLOR_TEXT).pack(side=tk.LEFT, padx=(12,4))
        self.sb_cols = tk.Spinbox(right, from_=1, to=30, width=4, textvariable=self.cols, command=self.redraw_grid)
        self.sb_cols.pack(side=tk.LEFT)

        # Center canvas (Matplotlib)
        center = tk.Frame(self, bg=COLOR_BG)
        center.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.fig = Figure(figsize=(8,6), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.ax.set_axis_off()
        self.ax.set_facecolor('#0b1220')
        self.fig._owner_app = self  # backlink for selection callback

        self.canvas = FigureCanvasTkAgg(self.fig, master=center)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        # Status bar
        self.status = tk.Label(self, text='Welcome! Load an image to begin.', bg=COLOR_PANEL, fg=COLOR_TEXT, anchor='w')
        self.status.pack(side=tk.BOTTOM, fill=tk.X)

    def _bind_keys(self):
        # Keyboard nudging
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

        # select nearest line with mouse click on axes
        self.cid_button = self.fig.canvas.mpl_connect('button_press_event', self._on_mpl_click)

    # =============================
    # Image Loading & Duplicate Check
    # =============================
    def load_image(self):
        path = filedialog.askopenfilename(title='Select an Image',
                                          filetypes=[('Image Files', '*.jpg;*.jpeg;*.png;*.bmp;*.tiff')])
        if not path:
            return
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
        self.image = img
        self.img_w, self.img_h = img.size

        self.ax.clear()
        self.ax.set_axis_off()
        # ensure pixel coordinates map 1:1
        self.ax.imshow(img, origin='upper')
        self.ax.set_xlim(0, self.img_w)
        self.ax.set_ylim(self.img_h, 0)
        self.fig.tight_layout()
        self.canvas.draw()

        self.status_ok(f"Loaded: {os.path.basename(path)}  ({self.img_w}×{self.img_h})")
        self._build_grid()

    # =============================
    # Grid & Selection
    # =============================
    def _build_grid(self):
        # remove any existing lines
        for dl in self.vert + self.horz:
            try:
                dl.line.remove()
            except Exception:
                pass
        self.vert.clear()
        self.horz.clear()
        self.selected = None

        cols = max(1, int(self.cols.get()))
        rows = max(1, int(self.rows.get()))

        # vertical lines (interior)
        for i in range(1, cols):
            x = i * (self.img_w / cols)
            l, = self.ax.plot([x, x], [0, self.img_h], linestyle='--', linewidth=2,
                              alpha=0.8, color=COLOR_ACCENT)
            self.vert.append(DraggableLine(self.ax, l, 'vertical', 0, self.img_w))

        # horizontal lines
        for j in range(1, rows):
            y = j * (self.img_h / rows)
            l, = self.ax.plot([0, self.img_w], [y, y], linestyle='--', linewidth=2,
                              alpha=0.8, color=COLOR_ACCENT)
            self.horz.append(DraggableLine(self.ax, l, 'horizontal', 0, self.img_h))

        self.canvas.draw()
        self.status_info('Tip: Click near a line to select it. Use Arrow keys to nudge (Shift = 10px).')

    def redraw_grid(self):
        if not self.image:
            return
        self._build_grid()

    def _on_mpl_click(self, event):
        if event.inaxes != self.ax:
            return
        # pick nearest line by x or y
        cand = None
        best = 1e12
        for dl in self.vert:
            d = abs((event.xdata or 0) - dl.get_pos())
            if d < best:
                best = d
                cand = dl
        for dl in self.horz:
            d = abs((event.ydata or 0) - dl.get_pos())
            if d < best:
                best = d
                cand = dl
        if cand:
            self._select_line(cand)

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
        if self.selected.orientation == 'vertical':
            self.selected.set_pos(self.selected.get_pos() + dx)
        else:
            self.selected.set_pos(self.selected.get_pos() + dy)
        self.status_ok('Nudged ✨')

    # =============================
    # Cropping & Preview
    # =============================
    def _boundaries(self):
        xs = [0] + sorted([dl.get_pos() for dl in self.vert]) + [self.img_w]
        ys = [0] + sorted([dl.get_pos() for dl in self.horz]) + [self.img_h]
        return xs, ys

    def save_crops(self):
        if not self.image:
            self.status_err('No image loaded.')
            return
        xs, ys = self._boundaries()
        base_ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        saved = []
        counter = 0
        for i in range(len(xs) - 1):
            for j in range(len(ys) - 1):
                L, R = int(xs[i]), int(xs[i+1])
                T, B = int(ys[j]), int(ys[j+1])
                crop = self.image.crop((L, T, R, B))
                fname = f"crop_{j}_{i}_{base_ts}_{counter}.png"
                out = os.path.join(OUTPUT_FOLDER, fname)
                try:
                    crop.save(out)
                    saved.append(out)
                except Exception as e:
                    print('Save failed', out, e)
                counter += 1
        if saved:
            h = file_hash(self.image_path)
            self.history[h] = {
                'path': self.image_path,
                'date': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'crops': saved,
            }
            _save_history(self.history)

            self.status_ok(f'✅ Saved {len(saved)} crops to {OUTPUT_FOLDER}.')
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
        btns.pack(pady=8)

        def open_folder():
            try:
                os.startfile(OUTPUT_FOLDER)
            except Exception:
                messagebox.showinfo('Output Folder', OUTPUT_FOLDER)

        def view_now():
            self._show_crops_list(paths, title='Crops Preview')

        def next_img():
            dlg.destroy()
            self.load_image()

        ttk.Button(btns, text='🗂 Open Folder', command=open_folder).pack(side=tk.LEFT, padx=6)
        ttk.Button(btns, text='🖼 Preview Crops', command=view_now).pack(side=tk.LEFT, padx=6)
        ttk.Button(btns, text='➡ Load Next Image', command=next_img, style='Accent.TButton').pack(side=tk.LEFT, padx=6)

    def _show_crops_list(self, paths, title='Crops'):
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

        def on_config(_):
            canvas.configure(scrollregion=canvas.bbox('all'))
        inner.bind('<Configure>', on_config)

        thumbs = []
        max_w, max_h = 260, 220
        for idx, p in enumerate(paths):
            try:
                im = Image.open(p)
                im.thumbnail((max_w, max_h))
                tkimg = ImageTk.PhotoImage(im)
                thumbs.append(tkimg)

                frame = tk.Frame(inner, bg=COLOR_PANEL, bd=1, relief='solid')
                frame.grid(row=idx//3, column=idx%3, padx=8, pady=8, sticky='nsew')

                lbl = tk.Label(frame, image=tkimg, bg=COLOR_PANEL)
                lbl.pack(padx=8, pady=8)
                cap = tk.Label(frame, text=os.path.basename(p), bg=COLOR_PANEL, fg=COLOR_TEXT, wraplength=240)
                cap.pack(padx=8, pady=(0,8))
            except Exception as e:
                print('Thumb failed', p, e)
        dlg._thumb_refs = thumbs  # keep alive

    def show_previous_crops(self):
        if not self.image_path:
            messagebox.showinfo('Previous Crops', 'Load an image first.')
            return
        h = file_hash(self.image_path)
        rec = self.history.get(h)
        if not rec:
            messagebox.showinfo('Previous Crops', 'No previous crops for this image.')
            return
        self._show_crops_list(rec.get('crops', []), title='Previously Saved Crops')

    # =============================
    # Status helpers
    # =============================
    def status_set(self, text, fg=COLOR_TEXT):
        self.status.configure(text=text, fg=fg)

    def status_ok(self, text):
        self.status_set(text, fg=COLOR_OK)

    def status_info(self, text):
        self.status_set(text, fg=COLOR_TEXT)

    def status_warn(self, text):
        self.status_set(text, fg=COLOR_WARN)

    def status_err(self, text):
        self.status_set(text, fg=COLOR_ERR)


if __name__ == '__main__':
    app = CropWorkstation()
    app.mainloop()
