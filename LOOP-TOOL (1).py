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
from moviepy.editor import VideoFileClip, concatenate_videoclips, vfx, AudioFileClip

# --- Configuration & Styles ---
APP_TITLE = "Greg Seymour AI Loop Videos tool"
BG_COLOR = "#2C3E50"        # Dark Blue/Grey
TEXT_COLOR = "#ECF0F1"      # Off-White
ACCENT_COLOR = "#E67E22"    # Pumpkin Orange
BUTTON_BG = "#3498DB"       # Blue
BUTTON_FG = "#FFFFFF"
LIST_BG = "#34495E"
LIST_FG = "#ECF0F1"

class VideoLooperApp:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("1000x700")
        self.root.configure(bg=BG_COLOR)
        
        # Make window resizable and start maximized if supported
        self.root.resizable(True, True)
        try:
            self.root.state('zoomed') # Windows
        except:
            pass

        # State Variables
        self.video_files = [] # List of paths
        self.processing = False
        self.stop_playback = False
        
        # Initialize Audio Mixer
        pygame.mixer.init()

        self.setup_ui()

    def setup_ui(self):
        # --- Header ---
        header_frame = tk.Frame(self.root, bg=BG_COLOR)
        header_frame.pack(fill="x", pady=20)
        
        title_label = tk.Label(header_frame, text=APP_TITLE.upper(), 
                             font=("Helvetica", 24, "bold"), 
                             bg=BG_COLOR, fg=ACCENT_COLOR)
        title_label.pack()

        # --- Main Container (Split Left/Right) ---
        main_container = tk.Frame(self.root, bg=BG_COLOR)
        main_container.pack(fill="both", expand=True, padx=20, pady=10)

        # === LEFT SIDE: Controls ===
        left_frame = tk.Frame(main_container, bg=BG_COLOR, width=400)
        left_frame.pack(side="left", fill="y", padx=(0, 20))

        # 1. File Controls
        file_frame = tk.LabelFrame(left_frame, text="File Management", 
                                 bg=BG_COLOR, fg=TEXT_COLOR, font=("Arial", 12, "bold"))
        file_frame.pack(fill="x", pady=10, ipady=5)

        self.btn_add = self.create_button(file_frame, "Add Videos (From File or Folder)", self.add_files)
        self.btn_add.pack(fill="x", padx=10, pady=5)
        
        self.btn_clear = self.create_button(file_frame, "Clear List", self.clear_list, bg="#C0392B")
        self.btn_clear.pack(fill="x", padx=10, pady=5)

        # 2. Reordering Controls
        order_frame = tk.LabelFrame(left_frame, text="Reorder Queue", 
                                  bg=BG_COLOR, fg=TEXT_COLOR, font=("Arial", 12, "bold"))
        order_frame.pack(fill="x", pady=10, ipady=5)
        
        btn_up = self.create_button(order_frame, "Move Up ▲", self.move_up)
        btn_up.pack(side="left", expand=True, padx=5, pady=5)
        
        btn_down = self.create_button(order_frame, "Move Down ▼", self.move_down)
        btn_down.pack(side="left", expand=True, padx=5, pady=5)

        # 3. Settings
        settings_frame = tk.LabelFrame(left_frame, text="Loop Settings", 
                                     bg=BG_COLOR, fg=TEXT_COLOR, font=("Arial", 12, "bold"))
        settings_frame.pack(fill="x", pady=10, ipady=5)

        # Loops Count
        lbl_loops = tk.Label(settings_frame, text="Number of Loops (-1 = Infinite):", 
                           bg=BG_COLOR, fg=TEXT_COLOR)
        lbl_loops.pack(anchor="w", padx=10)
        self.spin_loops = tk.Spinbox(settings_frame, from_=-1, to=100, width=10, font=("Arial", 12))
        self.spin_loops.delete(0, "end")
        self.spin_loops.insert(0, 5) # Default
        self.spin_loops.pack(padx=10, pady=5, anchor="w")

        # Output Mode
        self.output_mode = tk.StringVar(value="combine")
        lbl_mode = tk.Label(settings_frame, text="Processing Mode:", bg=BG_COLOR, fg=TEXT_COLOR)
        lbl_mode.pack(anchor="w", padx=10, pady=(10,0))
        
        rb1 = tk.Radiobutton(settings_frame, text="Combine All into One MP4", 
                           variable=self.output_mode, value="combine",
                           bg=BG_COLOR, fg=TEXT_COLOR, selectcolor=BG_COLOR, activebackground=BG_COLOR)
        rb1.pack(anchor="w", padx=10)
        
        rb2 = tk.Radiobutton(settings_frame, text="Save as Separate Files", 
                           variable=self.output_mode, value="separate",
                           bg=BG_COLOR, fg=TEXT_COLOR, selectcolor=BG_COLOR, activebackground=BG_COLOR)
        rb2.pack(anchor="w", padx=10)

        # 4. Action Buttons
        action_frame = tk.Frame(left_frame, bg=BG_COLOR)
        action_frame.pack(fill="x", pady=20)

        self.btn_play = self.create_button(action_frame, "▶ PLAY LIVE PREVIEW", self.start_play_thread, bg="#27AE60", font=("Arial", 14, "bold"))
        self.btn_play.pack(fill="x", pady=5)

        self.btn_save = self.create_button(action_frame, "💾 RENDER & SAVE TO DISK", self.start_save_thread, bg=ACCENT_COLOR, font=("Arial", 14, "bold"))
        self.btn_save.pack(fill="x", pady=5)

        # === RIGHT SIDE: List & Log ===
        right_frame = tk.Frame(main_container, bg=BG_COLOR)
        right_frame.pack(side="right", fill="both", expand=True)

        # Listbox for files
        lbl_queue = tk.Label(right_frame, text="Video Queue", bg=BG_COLOR, fg=TEXT_COLOR, font=("Arial", 12, "bold"))
        lbl_queue.pack(anchor="w")

        list_scroll = tk.Scrollbar(right_frame)
        self.listbox = tk.Listbox(right_frame, bg=LIST_BG, fg=LIST_FG, 
                                font=("Consolas", 10), selectbackground=ACCENT_COLOR,
                                yscrollcommand=list_scroll.set)
        list_scroll.config(command=self.listbox.yview)
        
        self.listbox.pack(side="top", fill="both", expand=True)
        list_scroll.pack(side="right", fill="y") # This visual placement might need tweaking depending on exact layout

        # Log Window
        lbl_log = tk.Label(right_frame, text="System Log", bg=BG_COLOR, fg=TEXT_COLOR, font=("Arial", 12, "bold"))
        lbl_log.pack(anchor="w", pady=(10,0))

        self.log_widget = scrolledtext.ScrolledText(right_frame, height=8, bg="black", fg="#00FF00", font=("Consolas", 9))
        self.log_widget.pack(side="bottom", fill="x")

    def create_button(self, parent, text, command, bg=BUTTON_BG, font=("Arial", 10, "bold")):
        btn = tk.Button(parent, text=text, command=command, 
                      bg=bg, fg=BUTTON_FG, font=font, 
                      activebackground="#ECF0F1", activeforeground="#2C3E50",
                      relief="flat", pady=5)
        return btn

    # --- Logging ---
    def log(self, message):
        timestamp = time.strftime("%H:%M:%S")
        full_msg = f"[{timestamp}] {message}"
        print(full_msg)
        self.log_widget.insert(tk.END, full_msg + "\n")
        self.log_widget.see(tk.END)

    # --- File Management ---
    def add_files(self):
        # Ask user: Individual files or Directory?
        choice = messagebox.askquestion("Selection Mode", "Do you want to select a specific Folder?\n(No = Select individual files)")
        
        new_files = []
        if choice == 'yes':
            directory = filedialog.askdirectory()
            if directory:
                for f in os.listdir(directory):
                    if f.lower().endswith(('.mp4', '.avi', '.mkv', '.mov')):
                        new_files.append(os.path.join(directory, f))
        else:
            files = filedialog.askopenfilenames(filetypes=[("Video Files", "*.mp4 *.avi *.mkv *.mov")])
            new_files.extend(files)

        for f in new_files:
            if f not in self.video_files:
                self.video_files.append(f)
                self.listbox.insert(tk.END, os.path.basename(f))
        
        self.log(f"Added {len(new_files)} videos. Total: {len(self.video_files)}")

    def clear_list(self):
        self.video_files = []
        self.listbox.delete(0, tk.END)
        self.log("Queue cleared.")

    def move_up(self):
        pos_list = self.listbox.curselection()
        if not pos_list: return
        for pos in pos_list:
            if pos > 0:
                # Swap text
                text = self.listbox.get(pos)
                self.listbox.delete(pos)
                self.listbox.insert(pos-1, text)
                self.listbox.selection_set(pos-1)
                # Swap data
                self.video_files[pos], self.video_files[pos-1] = self.video_files[pos-1], self.video_files[pos]

    def move_down(self):
        pos_list = self.listbox.curselection()
        if not pos_list: return
        for pos in reversed(pos_list):
            if pos < self.listbox.size() - 1:
                text = self.listbox.get(pos)
                self.listbox.delete(pos)
                self.listbox.insert(pos+1, text)
                self.listbox.selection_set(pos+1)
                self.video_files[pos], self.video_files[pos+1] = self.video_files[pos+1], self.video_files[pos]

    # --- Live Player Logic (OpenCV + Pygame) ---
    def start_play_thread(self):
        if not self.video_files:
            messagebox.showwarning("Empty Queue", "Please add videos first.")
            return
        
        try:
            loops = int(self.spin_loops.get())
        except:
            loops = 1

        self.stop_playback = False
        threading.Thread(target=self.play_live, args=(loops,), daemon=True).start()

    def play_live(self, num_loops):
        self.btn_play.config(state="disabled", text="PLAYING...")
        self.log("--- Starting Live Playback ---")
        
        window_name = "GSAI Player (Press Q or ESC to Quit)"
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

        current_video_idx = 0
        
        try:
            while True: # Infinite loop for the list sequence
                video_path = self.video_files[current_video_idx]
                self.log(f"Playing: {os.path.basename(video_path)}")

                # 1. Prep Video
                cap = cv2.VideoCapture(video_path)
                fps = cap.get(cv2.CAP_PROP_FPS)
                if fps == 0: fps = 30
                delay = int(1000 / fps)

                # 2. Load Frames (needed for smooth reverse playback)
                frames = []
                while True:
                    ret, frame = cap.read()
                    if not ret: break
                    frames.append(frame)
                cap.release()

                if not frames:
                    self.log(f"Error reading {video_path}")
                    current_video_idx = (current_video_idx + 1) % len(self.video_files)
                    continue

                # 3. Prep Audio (Extract to temp)
                audio_path = None
                has_audio = False
                try:
                    # Using MoviePy just to extract audio quickly
                    clip = VideoFileClip(video_path)
                    if clip.audio:
                        fd, audio_path = tempfile.mkstemp(suffix=".wav")
                        os.close(fd)
                        clip.audio.write_audiofile(audio_path, verbose=False, logger=None)
                        has_audio = True
                    clip.close()
                except Exception as e:
                    self.log(f"Audio extraction warning: {e}")

                # 4. Play Loop
                loop_count = 0
                while num_loops == -1 or loop_count < num_loops:
                    if self.stop_playback: break

                    # -- FORWARD (With Audio) --
                    if has_audio and audio_path:
                        pygame.mixer.music.load(audio_path)
                        pygame.mixer.music.play()

                    for frame in frames:
                        cv2.imshow(window_name, frame)
                        key = cv2.waitKey(delay) & 0xFF
                        if key == ord('q') or key == 27:
                            self.stop_playback = True
                            break
                        # Check window closed
                        if cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE) < 1:
                            self.stop_playback = True
                            break
                    
                    if self.stop_playback: break

                    # -- REVERSE (No Audio) --
                    if has_audio:
                        pygame.mixer.music.stop() # Kill audio immediately

                    for frame in reversed(frames[1:-1]): # Skip first/last to smooth loop
                        cv2.imshow(window_name, frame)
                        key = cv2.waitKey(delay) & 0xFF
                        if key == ord('q') or key == 27:
                            self.stop_playback = True
                            break
                    
                    loop_count += 1
                
                # Cleanup audio temp file
                if audio_path and os.path.exists(audio_path):
                    try: os.remove(audio_path)
                    except: pass

                if self.stop_playback:
                    break

                # Move to next video
                current_video_idx = (current_video_idx + 1) % len(self.video_files)

        except Exception as e:
            self.log(f"Playback Error: {e}")
        finally:
            cv2.destroyAllWindows()
            self.btn_play.config(state="normal", text="▶ PLAY LIVE PREVIEW")
            self.log("Playback stopped.")

    # --- Save/Render Logic (MoviePy) ---
    def start_save_thread(self):
        if not self.video_files:
            messagebox.showwarning("Empty Queue", "No videos to process.")
            return

        try:
            loops = int(self.spin_loops.get())
            if loops == -1:
                messagebox.showerror("Error", "Cannot save 'Infinite' loops to a file.\nPlease specify a number (e.g., 5).")
                return
        except ValueError:
            messagebox.showerror("Error", "Invalid loop count.")
            return

        mode = self.output_mode.get()
        
        if mode == "combine":
            output_path = filedialog.asksaveasfilename(defaultextension=".mp4", filetypes=[("MP4", "*.mp4")])
            if not output_path: return
            target = lambda: self.render_combine(output_path, loops)
        else:
            output_dir = filedialog.askdirectory(title="Select Output Folder")
            if not output_dir: return
            target = lambda: self.render_separate(output_dir, loops)

        self.btn_save.config(state="disabled", text="RENDERING (Please Wait)...")
        threading.Thread(target=target, daemon=True).start()

    def process_boomerang_clip(self, path, num_loops):
        """ Creates a boomerang clip object: [Forward(Audio) + Reverse(No Audio)] * loops """
        try:
            # 1. Load Original
            clip_fwd = VideoFileClip(path)
            
            # 2. Create Reverse (Muted)
            clip_rev = clip_fwd.fx(vfx.time_mirror)
            clip_rev = clip_rev.without_audio() # Explicitly remove audio from reverse part

            # 3. Concatenate one loop unit
            # [Forward, Reverse]
            loop_unit = concatenate_videoclips([clip_fwd, clip_rev])

            # 4. Repeat N times
            # Note: loop_unit.loop(n=num_loops) creates a loop, but concatenating the object n times is safer for export
            final_clip = concatenate_videoclips([loop_unit] * num_loops)
            
            return final_clip, clip_fwd.w, clip_fwd.h
        except Exception as e:
            self.log(f"Error processing {os.path.basename(path)}: {e}")
            return None, 0, 0

    def render_combine(self, output_path, loops):
        self.log(f"--- Starting Render: Combined Video ({loops} loops each) ---")
        clips_to_concat = []
        
        # Get dimensions of first video to force consistency
        target_w, target_h = 0, 0

        for idx, path in enumerate(self.video_files):
            self.log(f"Processing part {idx+1}/{len(self.video_files)}: {os.path.basename(path)}")
            clip, w, h = self.process_boomerang_clip(path, loops)
            
            if clip:
                if idx == 0:
                    target_w, target_h = w, h
                    clips_to_concat.append(clip)
                else:
                    # Resize if dimensions differ
                    if (w, h) != (target_w, target_h):
                        self.log(f"Resizing {os.path.basename(path)} to match first video...")
                        clip = clip.resize(newsize=(target_w, target_h))
                    clips_to_concat.append(clip)

        if clips_to_concat:
            self.log("Concatenating all clips...")
            try:
                final_video = concatenate_videoclips(clips_to_concat)
                final_video.write_videofile(output_path, codec="libx264", audio_codec="aac")
                self.log(f"SUCCESS: Saved to {output_path}")
                messagebox.showinfo("Success", "Video Rendering Complete!")
            except Exception as e:
                self.log(f"Render Error: {e}")
        else:
            self.log("No clips were successfully processed.")

        self.btn_save.config(state="normal", text="💾 RENDER & SAVE TO DISK")

    def render_separate(self, output_dir, loops):
        self.log(f"--- Starting Render: Separate Files ({loops} loops each) ---")
        
        total = len(self.video_files)
        for idx, path in enumerate(self.video_files):
            self.log(f"Processing {idx+1}/{total}: {os.path.basename(path)}")
            
            filename = f"Looped_{os.path.basename(path)}"
            save_path = os.path.join(output_dir, filename)
            
            clip, _, _ = self.process_boomerang_clip(path, loops)
            if clip:
                try:
                    clip.write_videofile(save_path, codec="libx264", audio_codec="aac")
                    self.log(f"Saved: {filename}")
                except Exception as e:
                    self.log(f"Failed to save {filename}: {e}")
                
                # Close clip to free memory
                clip.close() 

        self.log("Batch processing complete.")
        messagebox.showinfo("Success", "Batch Rendering Complete!")
        self.btn_save.config(state="normal", text="💾 RENDER & SAVE TO DISK")

if __name__ == "__main__":
    root = tk.Tk()
    app = VideoLooperApp(root)
    root.mainloop()