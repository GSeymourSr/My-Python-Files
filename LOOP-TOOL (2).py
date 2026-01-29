import cv2
import numpy as np
import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
import threading
import pygame
import tempfile
import time
import random
import datetime
from moviepy.editor import VideoFileClip, concatenate_videoclips, vfx

# --- Configuration & Styles ---
APP_TITLE = "Greg Seymour AI Video Tool v2.0"
BG_COLOR = "#2C3E50"        # Dark Blue/Grey
PANEL_BG = "#34495E"        # Lighter Blue/Grey
TEXT_COLOR = "#ECF0F1"      # Off-White
ACCENT_COLOR = "#E67E22"    # Orange
BUTTON_BG = "#2980B9"       # Standard Blue
BUTTON_FG = "#FFFFFF"
SUCCESS_COLOR = "#27AE60"   # Green
ALERT_COLOR = "#C0392B"     # Red

class VideoLooperApp:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("1280x800")
        self.root.configure(bg=BG_COLOR)
        
        # Start maximized
        try:
            self.root.state('zoomed')
        except:
            self.root.geometry("1280x800")

        # --- Data & State ---
        # self.video_data will hold dicts: {'path': str, 'name': str, 'size': int, 'date': float}
        self.video_data = [] 
        self.processing = False
        self.stop_playback = False
        self.playback_lock = False # The 'L' key toggle
        
        # Audio
        pygame.mixer.init()

        # Styles
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure("Treeview", 
                           background="white", fieldbackground="white", foreground="black", 
                           rowheight=25, font=("Arial", 10))
        self.style.map("Treeview", background=[('selected', ACCENT_COLOR)])
        
        self.setup_ui()

    def setup_ui(self):
        # --- Main Container ---
        # Left: Controls (Fixed Width) | Right: List (Expandable)
        main_split = tk.Frame(self.root, bg=BG_COLOR)
        main_split.pack(fill="both", expand=True, padx=10, pady=10)

        # === LEFT PANEL (Controls) ===
        left_frame = tk.Frame(main_split, bg=PANEL_BG, width=350)
        left_frame.pack(side="left", fill="y", padx=(0, 10))
        left_frame.pack_propagate(False) # Force width

        # Title
        tk.Label(left_frame, text="CONTROLS", bg=PANEL_BG, fg=ACCENT_COLOR, 
                 font=("Helvetica", 16, "bold")).pack(pady=10)

        # 1. File Actions
        grp_file = tk.LabelFrame(left_frame, text="1. Manage Files", bg=PANEL_BG, fg=TEXT_COLOR, font=("Arial", 10, "bold"))
        grp_file.pack(fill="x", padx=10, pady=5)

        self.btn_add = self.create_button(grp_file, "+ Add Videos", self.add_files, bg=BUTTON_BG)
        self.btn_add.pack(fill="x", padx=5, pady=2)
        
        self.btn_rem = self.create_button(grp_file, "- Remove Selected (Del)", self.remove_selected, bg=ALERT_COLOR)
        self.btn_rem.pack(fill="x", padx=5, pady=2)

        # Selection Helpers
        btn_row = tk.Frame(grp_file, bg=PANEL_BG)
        btn_row.pack(fill="x", padx=5, pady=2)
        self.create_button(btn_row, "Select All", self.select_all, width=12).pack(side="left", padx=1)
        self.create_button(btn_row, "Select None", self.select_none, width=12).pack(side="right", padx=1)

        # Sorting
        tk.Label(grp_file, text="Sort Queue By:", bg=PANEL_BG, fg="#BDC3C7", font=("Arial", 8)).pack(anchor="w", padx=5)
        sort_row = tk.Frame(grp_file, bg=PANEL_BG)
        sort_row.pack(fill="x", padx=5, pady=(0, 5))
        self.create_button(sort_row, "Name", lambda: self.sort_queue("name"), width=8).pack(side="left", padx=1)
        self.create_button(sort_row, "Date", lambda: self.sort_queue("date"), width=8).pack(side="left", padx=1)
        self.create_button(sort_row, "Size", lambda: self.sort_queue("size"), width=8).pack(side="left", padx=1)

        # 2. Settings
        grp_set = tk.LabelFrame(left_frame, text="2. Playback & Loop Settings", bg=PANEL_BG, fg=TEXT_COLOR, font=("Arial", 10, "bold"))
        grp_set.pack(fill="x", padx=10, pady=10)

        # Loops
        tk.Label(grp_set, text="Loops (0=Straight, -1=Inf):", bg=PANEL_BG, fg=TEXT_COLOR).pack(anchor="w", padx=5)
        self.spin_loops = tk.Spinbox(grp_set, from_=-1, to=100, font=("Arial", 12))
        self.spin_loops.delete(0, "end")
        self.spin_loops.insert(0, 5)
        self.spin_loops.pack(fill="x", padx=5, pady=2)

        # Order
        self.playback_order = tk.StringVar(value="sequential")
        tk.Label(grp_set, text="Order:", bg=PANEL_BG, fg=TEXT_COLOR).pack(anchor="w", padx=5, pady=(5,0))
        tk.Radiobutton(grp_set, text="Sequential", variable=self.playback_order, value="sequential", bg=PANEL_BG, fg=TEXT_COLOR, selectcolor=PANEL_BG).pack(anchor="w", padx=5)
        tk.Radiobutton(grp_set, text="Random (Shuffle)", variable=self.playback_order, value="random", bg=PANEL_BG, fg=TEXT_COLOR, selectcolor=PANEL_BG).pack(anchor="w", padx=5)

        # 3. Output Mode
        grp_out = tk.LabelFrame(left_frame, text="3. Save Settings", bg=PANEL_BG, fg=TEXT_COLOR, font=("Arial", 10, "bold"))
        grp_out.pack(fill="x", padx=10, pady=10)
        
        self.output_mode = tk.StringVar(value="combine")
        tk.Radiobutton(grp_out, text="Combine into ONE Video", variable=self.output_mode, value="combine", bg=PANEL_BG, fg=TEXT_COLOR, selectcolor=PANEL_BG).pack(anchor="w", padx=5)
        tk.Radiobutton(grp_out, text="Save as SEPARATE Files", variable=self.output_mode, value="separate", bg=PANEL_BG, fg=TEXT_COLOR, selectcolor=PANEL_BG).pack(anchor="w", padx=5)

        # === IMPORTANT: ACTION BUTTONS AT BOTTOM OF LEFT PANEL ===
        # We use a frame at the bottom to ensure they are never pushed off screen
        action_frame = tk.Frame(left_frame, bg=PANEL_BG)
        action_frame.pack(side="bottom", fill="x", padx=10, pady=20)

        self.btn_play = tk.Button(action_frame, text="▶ START PLAYER", command=self.start_play_thread, 
                                bg=SUCCESS_COLOR, fg="white", font=("Arial", 14, "bold"), height=2)
        self.btn_play.pack(fill="x", pady=5)

        self.btn_save = tk.Button(action_frame, text="💾 SAVE TO DISK", command=self.start_save_thread, 
                                bg=ACCENT_COLOR, fg="white", font=("Arial", 14, "bold"), height=2)
        self.btn_save.pack(fill="x", pady=5)


        # === RIGHT PANEL (List & Logs) ===
        right_frame = tk.Frame(main_split, bg=BG_COLOR)
        right_frame.pack(side="right", fill="both", expand=True)

        # Treeview (The List)
        columns = ("name", "size", "date")
        self.tree = ttk.Treeview(right_frame, columns=columns, show="headings", selectmode="extended")
        
        self.tree.heading("name", text="Filename")
        self.tree.heading("size", text="Size (MB)")
        self.tree.heading("date", text="Date Modified")
        
        self.tree.column("name", width=400)
        self.tree.column("size", width=80, anchor="center")
        self.tree.column("date", width=150, anchor="center")

        # Scrollbars
        vsb = ttk.Scrollbar(right_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        
        self.tree.pack(side="top", fill="both", expand=True)
        vsb.pack(side="right", fill="y", in_=self.tree)

        # Key Bindings for List
        self.tree.bind("<Delete>", lambda e: self.remove_selected())

        # Log
        self.log_widget = scrolledtext.ScrolledText(right_frame, height=6, bg="black", fg="#00FF00", font=("Consolas", 9))
        self.log_widget.pack(side="bottom", fill="x", pady=(10,0))

    def create_button(self, parent, text, command, bg="#95A5A6", width=None):
        return tk.Button(parent, text=text, command=command, bg=bg, fg="white", 
                       font=("Arial", 9, "bold"), relief="flat", padx=10, pady=5, width=width)

    # --- LOGIC ---
    def log(self, message):
        ts = time.strftime("%H:%M:%S")
        self.log_widget.insert(tk.END, f"[{ts}] {message}\n")
        self.log_widget.see(tk.END)
        print(message)

    def add_files(self):
        # Ask: Folder or Files?
        ans = messagebox.askyesnocancel("Add Videos", "Select YES for a Folder.\nSelect NO for Individual Files.")
        if ans is None: return

        new_paths = []
        if ans: # Folder
            d = filedialog.askdirectory()
            if d:
                for f in os.listdir(d):
                    if f.lower().endswith(('.mp4', '.avi', '.mov', '.mkv')):
                        new_paths.append(os.path.join(d, f))
        else: # Files
            files = filedialog.askopenfilenames(filetypes=[("Videos", "*.mp4 *.avi *.mov *.mkv")])
            new_paths.extend(files)

        # Add to data and tree
        count = 0
        for p in new_paths:
            # Check duplicates
            if any(d['path'] == p for d in self.video_data):
                continue
            
            try:
                stat = os.stat(p)
                size_mb = round(stat.st_size / (1024 * 1024), 2)
                mtime = datetime.datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M')
                
                entry = {
                    'path': p,
                    'name': os.path.basename(p),
                    'size': size_mb,
                    'date': stat.st_mtime, # raw float for sorting
                    'date_str': mtime
                }
                self.video_data.append(entry)
                self.tree.insert("", "end", iid=p, values=(entry['name'], entry['size'], entry['date_str']))
                count += 1
            except Exception as e:
                self.log(f"Error loading {p}: {e}")

        self.log(f"Added {count} videos.")

    def remove_selected(self):
        selected_ids = self.tree.selection()
        if not selected_ids: return

        for iid in selected_ids:
            self.tree.delete(iid)
            # Remove from data list
            self.video_data = [d for d in self.video_data if d['path'] != iid]
        
        self.log(f"Removed {len(selected_ids)} videos.")

    def select_all(self):
        for item in self.tree.get_children():
            self.tree.selection_add(item)

    def select_none(self):
        for item in self.tree.selection():
            self.tree.selection_remove(item)

    def sort_queue(self, key):
        # key: 'name', 'date', 'size'
        reverse = False
        if key in ['size', 'date']: reverse = True # Largest/Newest first usually preferred

        self.video_data.sort(key=lambda x: x[key], reverse=reverse)
        
        # Clear and repopulate tree
        self.tree.delete(*self.tree.get_children())
        for d in self.video_data:
            self.tree.insert("", "end", iid=d['path'], values=(d['name'], d['size'], d['date_str']))
        
        self.log(f"Sorted by {key}.")

    # --- PLAYER ---
    def start_play_thread(self):
        if not self.video_data:
            messagebox.showwarning("Empty", "No videos in queue.")
            return
        
        try:
            loops = int(self.spin_loops.get())
        except:
            loops = 5

        self.stop_playback = False
        threading.Thread(target=self.play_live, args=(loops,), daemon=True).start()

    def play_live(self, num_loops):
        self.btn_play.config(state="disabled", text="PLAYING...", bg="#7F8C8D")
        self.playback_lock = False
        mode = self.playback_order.get()
        
        # Create a working list index
        queue_indices = list(range(len(self.video_data)))
        if mode == "random":
            random.shuffle(queue_indices)
        
        idx_ptr = 0 # Pointer to where we are in queue_indices
        
        window_name = "AI Loop Player (L=Lock, Space/Right=Next, Left=Prev, Esc=Quit)"
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

        try:
            while True:
                if self.stop_playback: break

                # Handle wrapping
                if idx_ptr >= len(queue_indices): idx_ptr = 0
                if idx_ptr < 0: idx_ptr = len(queue_indices) - 1

                current_idx = queue_indices[idx_ptr]
                video_info = self.video_data[current_idx]
                path = video_info['path']
                
                self.log(f"Playing: {video_info['name']}")

                # Prepare Media
                cap = cv2.VideoCapture(path)
                fps = cap.get(cv2.CAP_PROP_FPS) or 30
                delay = int(1000/fps)
                
                # Pre-read frames for smooth reversing
                frames = []
                while True:
                    ret, frame = cap.read()
                    if not ret: break
                    frames.append(frame)
                cap.release()

                if not frames:
                    self.log("Error: Could not read frames.")
                    idx_ptr += 1
                    continue

                # Audio
                audio_path = None
                has_audio = False
                try:
                    clip = VideoFileClip(path)
                    if clip.audio:
                        fd, audio_path = tempfile.mkstemp(suffix=".wav")
                        os.close(fd)
                        clip.audio.write_audiofile(audio_path, verbose=False, logger=None)
                        has_audio = True
                    clip.close()
                except: pass

                # --- PLAYBACK LOGIC ---
                nav_action = None # 'next', 'prev', 'quit'

                # Loop Logic: 0 = Once, -1 = Inf, >0 = N times
                loop_counter = 0
                
                # The Loop Controller
                while True: 
                    # Check infinite loops (-1) OR standard loops
                    if num_loops != -1 and num_loops != 0 and loop_counter >= num_loops:
                        break
                    if num_loops == 0 and loop_counter >= 1:
                        break

                    # 1. Forward Pass
                    if has_audio and audio_path:
                        pygame.mixer.music.load(audio_path)
                        pygame.mixer.music.play()
                    
                    for frame in frames:
                        # Overlay
                        display_frame = frame.copy()
                        status_text = f"LOCKED: {video_info['name']}" if self.playback_lock else video_info['name']
                        color = (0, 0, 255) if self.playback_lock else (255, 255, 255)
                        cv2.putText(display_frame, status_text, (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
                        
                        cv2.imshow(window_name, display_frame)
                        
                        # Key Handling
                        key = cv2.waitKey(delay) & 0xFF
                        
                        # Space (32) or Right Arrow (usually 83 on Win, but vary. Use 2555904 masking logic or just keys)
                        # Standard arrow keys in OpenCV often map to: Left: 2424832, Right: 2555904 (on Windows)
                        # Or simple scan codes. We will check a few variants.
                        
                        if key == 27 or key == ord('q'): # ESC
                            nav_action = 'quit'; break
                        elif key == 32: # Space -> Next
                            nav_action = 'next'; break
                        elif key == 83 or key == 2555904: # Right Arrow (Approx)
                            nav_action = 'next'; break
                        elif key == 81 or key == 2424832: # Left Arrow (Approx)
                            nav_action = 'prev'; break
                        elif key == ord('l') or key == ord('L'):
                            self.playback_lock = not self.playback_lock
                            self.log(f"Loop Lock: {self.playback_lock}")

                    if nav_action: break
                    if has_audio: pygame.mixer.music.stop()

                    # Stop if straight play (0 loops)
                    if num_loops == 0:
                        break

                    # 2. Reverse Pass (Boomerang)
                    for frame in reversed(frames[1:-1]):
                        display_frame = frame.copy()
                        status_text = f"LOCKED (REV)" if self.playback_lock else "REVERSE"
                        cv2.putText(display_frame, status_text, (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,255), 2)
                        cv2.imshow(window_name, display_frame)
                        
                        key = cv2.waitKey(delay) & 0xFF
                        if key == 27 or key == ord('q'): 
                            nav_action = 'quit'; break
                        elif key == 32: 
                            nav_action = 'next'; break
                        elif key == ord('l') or key == ord('L'):
                            self.playback_lock = not self.playback_lock

                    if nav_action: break
                    
                    loop_counter += 1
                
                # Cleanup Audio
                if audio_path and os.path.exists(audio_path):
                    try: os.remove(audio_path)
                    except: pass

                # --- NAVIGATION DECISION ---
                if nav_action == 'quit':
                    self.stop_playback = True
                    break
                
                # If Locked, we ignore Next/Prev/LoopEnd and stay on current index
                # UNLESS the user explicitly pressed Next/Prev keys to break the lock
                if self.playback_lock:
                    if nav_action == 'next':
                        self.playback_lock = False # Unlock if manual move
                        idx_ptr += 1
                    elif nav_action == 'prev':
                        self.playback_lock = False
                        idx_ptr -= 1
                    else:
                        # Natural loop end, but locked -> Stay here
                        pass
                else:
                    # Normal navigation
                    if nav_action == 'prev':
                        idx_ptr -= 1
                    else:
                        # Space, Right, or Video Finished naturally
                        idx_ptr += 1

        except Exception as e:
            self.log(f"Player Error: {e}")
        finally:
            cv2.destroyAllWindows()
            try: pygame.mixer.music.stop()
            except: pass
            self.btn_play.config(state="normal", text="▶ START PLAYER", bg=SUCCESS_COLOR)

    # --- SAVE ---
    def start_save_thread(self):
        if not self.video_data:
            messagebox.showwarning("Error", "Queue is empty")
            return
        
        threading.Thread(target=self.render_videos, daemon=True).start()

    def render_videos(self):
        self.btn_save.config(state="disabled", text="RENDERING...")
        
        try:
            loops = int(self.spin_loops.get())
            if loops == -1:
                messagebox.showerror("Error", "Cannot save infinite loops. Set a number.")
                self.btn_save.config(state="normal", text="💾 SAVE TO DISK")
                return
        except:
            loops = 5

        mode = self.output_mode.get()
        
        # Get list based on current sort/order
        # Note: Render usually follows the visible list order
        # If "Random" playback is selected, user might expect random render, 
        # but usually "Sort" determines render order. We'll use the self.video_data order (Tree order).
        
        render_list = self.video_data.copy()

        if mode == "combine":
            out = filedialog.asksaveasfilename(defaultextension=".mp4", filetypes=[("MP4", "*.mp4")])
            if not out: 
                self.btn_save.config(state="normal", text="💾 SAVE TO DISK")
                return
            
            clips = []
            w, h = 0, 0
            
            for i, item in enumerate(render_list):
                self.log(f"Processing {i+1}/{len(render_list)}: {item['name']}")
                clip, cw, ch = self.process_clip(item['path'], loops)
                if clip:
                    if i == 0:
                        w, h = cw, ch
                        clips.append(clip)
                    else:
                        if (cw, ch) != (w, h):
                            clip = clip.resize(newsize=(w, h))
                        clips.append(clip)
            
            if clips:
                self.log("Concatenating...")
                final = concatenate_videoclips(clips)
                final.write_videofile(out, codec="libx264", audio_codec="aac")
                messagebox.showinfo("Done", "Video Saved Successfully")
            
        else:
            d = filedialog.askdirectory()
            if not d: 
                self.btn_save.config(state="normal", text="💾 SAVE TO DISK")
                return

            for i, item in enumerate(render_list):
                self.log(f"Saving {item['name']}...")
                clip, _, _ = self.process_clip(item['path'], loops)
                if clip:
                    prefix = "Straight_" if loops == 0 else f"Loop{loops}_"
                    fname = os.path.join(d, prefix + item['name'])
                    clip.write_videofile(fname, codec="libx264", audio_codec="aac")
                    clip.close()
            
            messagebox.showinfo("Done", "Batch Save Complete")

        self.btn_save.config(state="normal", text="💾 SAVE TO DISK")

    def process_clip(self, path, loops):
        try:
            clip = VideoFileClip(path)
            if loops == 0:
                return clip, clip.w, clip.h
            
            rev = clip.fx(vfx.time_mirror).without_audio()
            loop_seg = concatenate_videoclips([clip, rev])
            final = concatenate_videoclips([loop_seg] * loops)
            return final, clip.w, clip.h
        except Exception as e:
            self.log(f"Error processing {path}: {e}")
            return None, 0, 0

if __name__ == "__main__":
    root = tk.Tk()
    app = VideoLooperApp(root)
    root.mainloop()