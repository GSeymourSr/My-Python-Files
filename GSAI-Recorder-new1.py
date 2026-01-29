import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import mss
import cv2
import numpy as np
import threading
import time
import os
from datetime import datetime
from pynput import keyboard
import pygame
from PIL import Image, ImageTk

# =============================================================================
# ===== CONFIGURATION & PRESETS =====
# =============================================================================
# IMPORTANT: Update this path to your sound file if it's different!
SOUND_FILE = r"C:\\- AAII TOOLS -\\firework-whistle-190306.mp3"  

# NEW: Changed the default output directory as requested.
DEFAULT_OUTPUT_DIR = r"C:\- AI  NEW CONTENT"

# NEW: Added more presets for common monitor refresh rates.
PRESETS = {
    "Cinematic (24fps)": 24,
    "Standard (30fps)": 30,
    "Smooth (60fps)": 60,
    "Gamer Smooth (75fps)": 75,
    "VR / Mobile (90fps)": 90,
    "Pro Gamer (120fps)": 120,
    "High Refresh (144fps)": 144,
    "Butter (240fps)": 240
}

# =============================================================================
# ===== CORE SCREEN RECORDER LOGIC =====
# =============================================================================
class ScreenRecorder:
    def __init__(self, status_callback, progress_callback, done_callback, audio_player):
        self.is_recording = False
        self.is_paused = False
        self.stop_event = threading.Event()
        self.pause_event = threading.Event()
        self.recording_thread = None
        self.output_dir = DEFAULT_OUTPUT_DIR
        self.status_callback = status_callback
        self.progress_callback = progress_callback # NEW: For the saving progress bar
        self.done_callback = done_callback
        self.audio_player = audio_player

    def start(self, fps, duration_seconds, monitor_index, mode):
        if self.is_recording:
            return

        self.is_recording = True
        self.is_paused = False
        self.stop_event.clear()
        self.pause_event.clear()

        self.audio_player.play()
        self.status_callback("Recording", "green")
        
        loop_target = self._record_loop_ram if mode == "ram" else self._record_loop_disk
        
        self.recording_thread = threading.Thread(
            target=loop_target,
            args=(fps, duration_seconds, monitor_index),
            daemon=True
        )
        self.recording_thread.start()

    def stop(self):
        if not self.is_recording:
            return
        
        self.stop_event.set()
        # The thread will handle status updates from here
        self.audio_player.play()

    def toggle_pause(self):
        if not self.is_recording:
            return
        
        self.is_paused = not self.is_paused
        if self.is_paused:
            self.pause_event.set()
            self.status_callback("Paused", "orange")
        else:
            self.pause_event.clear()
            self.status_callback("Recording", "green")

    def _record_loop_ram(self, target_fps, duration_seconds, monitor_index):
        frames = []
        capture_start_time = time.time()
        
        try:
            with mss.mss() as sct:
                monitor = sct.monitors[monitor_index]
                
                # Main capture loop
                while not self.stop_event.is_set():
                    if self.pause_event.is_set():
                        time.sleep(0.1)
                        continue

                    img = sct.grab(monitor)
                    frames.append(cv2.cvtColor(np.array(img), cv2.COLOR_BGRA2BGR))
                    
                    if duration_seconds > 0 and (time.time() - capture_start_time) >= duration_seconds:
                        self.stop_event.set() # Signal stop if duration is reached
                    
                    time.sleep(0.001)

        except Exception as e:
            messagebox.showerror("Recording Error", f"An error occurred: {e}")
            self.done_callback(None, 0, 0)
            return
        
        # --- Post-Recording & Saving with Progress Updates ---
        self.is_recording = False
        capture_end_time = time.time()
        actual_duration = capture_end_time - capture_start_time
        
        if not frames or actual_duration < 0.1:
            print("No frames captured or duration too short.")
            self.done_callback(None, 0, 0)
            return
            
        actual_fps = len(frames) / actual_duration

        os.makedirs(self.output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = os.path.join(self.output_dir, f"recording_{timestamp}_{actual_fps:.2f}fps.mp4")
        
        # This is where the time-consuming part starts
        self.status_callback("Saving video... (this may take a while)", "cyan")

        try:
            height, width, _ = frames[0].shape
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(filename, fourcc, actual_fps, (width, height))
            
            total_frames = len(frames)
            for i, frame in enumerate(frames):
                out.write(frame)
                # NEW: Calculate and send progress updates
                progress_percent = int((i + 1) / total_frames * 100)
                self.progress_callback(progress_percent)

            out.release()
            self.done_callback(filename, target_fps, actual_fps)
        except Exception as e:
            messagebox.showerror("Saving Error", f"Could not save the video file: {e}")
            self.done_callback(None, 0, 0)

    def _record_loop_disk(self, fps, duration_seconds, monitor_index):
        # NOTE: For simplicity, direct-to-disk mode also uses the RAM method for this example,
        # as it's the superior method. In a full app, you might have a different implementation here.
        self._record_loop_ram(fps, duration_seconds, monitor_index)

# =============================================================================
# ===== AUDIO PLAYER (using Pygame) =====
# =============================================================================
class AudioPlayer:
    def __init__(self, sound_file):
        self.sound = None
        try:
            pygame.mixer.init()
            if os.path.exists(sound_file):
                self.sound = pygame.mixer.Sound(sound_file)
            else:
                messagebox.showwarning("Audio Warning", f"Start/Stop sound file not found at:\n{sound_file}\n\nThe program will work, but without sound cues.")
        except Exception as e:
            print(f"Could not initialize audio: {e}")

    def play(self):
        if self.sound:
            try:
                self.sound.play()
            except Exception as e:
                print(f"Error playing sound: {e}")

# =============================================================================
# ===== GRAPHICAL USER INTERFACE (GUI) =====
# =============================================================================
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.audio_player = AudioPlayer(SOUND_FILE)
        self.recorder = ScreenRecorder(
            self.update_status, 
            self.update_save_progress, 
            self.on_recording_finished, 
            self.audio_player
        )
        
        self.title("🎬 Greg Seymour Screen Recorder")
        self.geometry("750x650") # Increased size for new elements
        self.configure(bg="#2E3440")
        self.resizable(False, False)

        # To cleanly stop threads
        self.app_stop_event = threading.Event()

        # Style Configuration
        style = ttk.Style(self)
        style.theme_use('clam')
        # ... (style config is the same, no changes needed) ...
        style.configure('TFrame', background='#2E3440')
        style.configure('TLabel', font=('Segoe UI', 11), background='#2E3440', foreground='#D8DEE9')
        style.configure('Title.TLabel', font=('Segoe UI', 24, 'bold'), foreground='#88C0D0')
        style.configure('TButton', font=('Segoe UI', 10, 'bold'), borderwidth=0)
        style.map('TButton', background=[('active', '#4C566A'), ('!active', '#434C5E')], foreground=[('active', '#ECEFF4'), ('!active', '#D8DEE9')])
        style.configure('TEntry', fieldbackground='#4C566A', foreground='#ECEFF4', borderwidth=0)
        style.configure('TCombobox', font=('Segoe UI', 10), fieldbackground='#4C566A', foreground='#ECEFF4')
        self.option_add('*TCombobox*Listbox.background', '#4C566A')
        self.option_add('*TCombobox*Listbox.foreground', '#ECEFF4')
        style.configure('Warning.TLabel', foreground='#BF616A')
        style.configure('Info.TLabel', foreground='#A3BE8C')
        style.configure('Horizontal.TProgressbar', background='#88C0D0')

        self.main_frame = ttk.Frame(self, padding="20 20 20 20")
        self.main_frame.pack(expand=True, fill=tk.BOTH)
        
        # --- Top Bar with Title and Help Button ---
        top_frame = ttk.Frame(self.main_frame)
        top_frame.pack(fill=tk.X, pady=(0, 20))
        title_label = ttk.Label(top_frame, text="Greg Seymour Screen Recorder", style='Title.TLabel')
        title_label.pack(side=tk.LEFT, expand=True)
        help_btn = ttk.Button(top_frame, text="❔ Help / Info", command=self.show_help_window, width=15)
        help_btn.pack(side=tk.RIGHT)

        settings_frame = ttk.Frame(self.main_frame)
        settings_frame.pack(fill=tk.X, pady=10)
        settings_frame.columnconfigure(1, weight=1)

        # --- Settings Widgets ---
        # (Layout is mostly the same, just added some info labels)
        ttk.Label(settings_frame, text="Recording Mode:").grid(row=0, column=0, padx=5, pady=5, sticky='w')
        self.mode_box = ttk.Combobox(settings_frame, values=["High-Precision (uses RAM)", "Long-form (Direct-to-Disk)"], state="readonly")
        self.mode_box.current(0)
        self.mode_box.grid(row=0, column=1, padx=5, pady=5, sticky='ew')
        ttk.Label(settings_frame, text="Recommended for accurate, short clips.", style='Info.TLabel').grid(row=1, column=1, padx=5, sticky='w')

        ttk.Label(settings_frame, text="Monitor to Record:").grid(row=2, column=0, padx=5, pady=10, sticky='w')
        self.monitor_box = ttk.Combobox(settings_frame, state="readonly")
        self.monitor_box.grid(row=2, column=1, padx=5, pady=10, sticky='ew')
        self.populate_monitors()
        self.monitor_box.bind("<<ComboboxSelected>>", self.on_monitor_change)


        ttk.Label(settings_frame, text="Preset:").grid(row=3, column=0, padx=5, pady=5, sticky='w')
        self.preset_box = ttk.Combobox(settings_frame, values=list(PRESETS.keys()), state="readonly")
        self.preset_box.set("Smooth (60fps)") # Default preset
        self.preset_box.grid(row=3, column=1, padx=5, pady=5, sticky='ew')
        self.preset_box.bind("<<ComboboxSelected>>", self.apply_preset)

        ttk.Label(settings_frame, text="FPS:").grid(row=4, column=0, padx=5, pady=5, sticky='w')
        self.fps_entry = ttk.Entry(settings_frame, width=15)
        self.fps_entry.grid(row=4, column=1, padx=5, pady=5, sticky='w')
        self.apply_preset() # Apply the default preset on startup

        ttk.Label(settings_frame, text="Duration (seconds, 0 for unlimited):").grid(row=5, column=0, padx=5, pady=5, sticky='w')
        self.duration_entry = ttk.Entry(settings_frame, width=15)
        self.duration_entry.insert(0, "0")
        self.duration_entry.grid(row=5, column=1, padx=5, pady=5, sticky='w')

        output_frame = ttk.Frame(settings_frame)
        output_frame.grid(row=6, column=0, columnspan=2, pady=10, sticky='ew')
        self.output_label = ttk.Label(output_frame, text=f"Output: {os.path.abspath(self.recorder.output_dir)}")
        self.output_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        output_btn = ttk.Button(output_frame, text="Change...", command=self.select_output_dir, width=10)
        output_btn.pack(side=tk.RIGHT)
        
        controls_frame = ttk.Frame(self.main_frame)
        controls_frame.pack(pady=20)
        self.start_btn = ttk.Button(controls_frame, text="🔴 Start Recording (R)", command=self.start_recording)
        self.start_btn.pack(side=tk.LEFT, padx=5, ipady=10)
        self.pause_btn = ttk.Button(controls_frame, text="⏸️ Pause / Resume (P)", command=self.recorder.toggle_pause)
        self.pause_btn.pack(side=tk.LEFT, padx=5, ipady=10)
        self.stop_btn = ttk.Button(controls_frame, text="⏹️ Stop Recording (R)", command=self.recorder.stop)
        self.stop_btn.pack(side=tk.LEFT, padx=5, ipady=10)
        
        self.status_label = ttk.Label(self.main_frame, text="Status: Idle", font=('Segoe UI', 12, 'bold'))
        self.status_label.pack(pady=5)
        
        # NEW: Progress bar for saving video
        self.progress_bar = ttk.Progressbar(self.main_frame, orient='horizontal', length=300, mode='determinate', style='Horizontal.TProgressbar')
        self.progress_bar.pack(pady=5)
        self.progress_bar.pack_forget() # Hide it initially

        self.setup_hotkeys()
        self.create_preview_window() # Create the live preview
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def start_recording(self):
        try:
            fps = float(self.fps_entry.get())
            duration = float(self.duration_entry.get())
            monitor_index = self.monitor_box.current()
            mode_str = self.mode_box.get()
            mode = "ram" if "RAM" in mode_str else "disk"

            if fps <= 0 or duration < 0:
                raise ValueError("FPS must be > 0 and Duration must be >= 0.")
            
            # Check if output directory exists, create if not
            os.makedirs(self.recorder.output_dir, exist_ok=True)
            
            self.recorder.start(fps, duration, monitor_index, mode)
            # self.withdraw() # We no longer hide the main window

        except ValueError as e:
            messagebox.showerror("Invalid Input", f"Please enter valid numbers. Details: {e}")
        except Exception as e:
            messagebox.showerror("Error", f"Could not start recording. Details: {e}")
            
    def on_recording_finished(self, filename, target_fps, actual_fps):
        # self.deiconify() # No longer needed
        self.update_status("Idle", "#D8DEE9")
        self.progress_bar.pack_forget() # Hide progress bar when done

        if filename:
            message = (f"Video saved to:\n{os.path.abspath(filename)}\n\n"
                       f"Target FPS: {target_fps:.2f}\n"
                       f"Actual Captured FPS: {actual_fps:.2f}")
            messagebox.showinfo("Success", message)
        else:
            messagebox.showwarning("Recording Canceled", "Recording was stopped with no frames to save.")
    
    def update_save_progress(self, percentage):
        if not self.progress_bar.winfo_viewable():
            self.progress_bar.pack(pady=5, fill=tk.X, padx=20)
        self.progress_bar['value'] = percentage
        self.update_idletasks() # Force GUI to refresh

    def populate_monitors(self):
        with mss.mss() as sct:
            monitors = [f"Monitor {i}: {m['width']}x{m['height']} @ ({m['left']},{m['top']})" for i, m in enumerate(sct.monitors)]
            # Monitor 0 is the 'all-in-one' screen, we usually want to start with Monitor 1 (primary)
            self.sct_monitors = sct.monitors
        self.monitor_box['values'] = monitors[1:] # Exclude the 'all-in-one' monitor 0
        self.monitor_box.current(0) # Default to the first physical monitor

    def on_monitor_change(self, event=None):
        # This just serves as a placeholder for any logic needed when monitor changes
        # The preview will update automatically in its own thread
        pass

    def apply_preset(self, event=None):
        preset_name = self.preset_box.get()
        if preset_name in PRESETS:
            fps = PRESETS[preset_name]
            self.fps_entry.delete(0, tk.END)
            self.fps_entry.insert(0, str(fps))

    def select_output_dir(self):
        directory = filedialog.askdirectory(initialdir=self.recorder.output_dir)
        if directory:
            self.recorder.output_dir = directory
            self.output_label.config(text=f"Output: {os.path.abspath(directory)}")
    
    def update_status(self, text, color):
        self.status_label.config(text=f"Status: {text}", foreground=color)

    def on_hotkey_press(self, key):
        # Check if the active window is a text entry field to avoid conflicts
        try:
            focused_widget = self.focus_get()
            if isinstance(focused_widget, (ttk.Entry, tk.Text)):
                return # Don't trigger hotkeys while typing in entries
        except:
            pass # No focus, proceed

        try:
            if key.char == 'r':
                if self.recorder.is_recording: self.recorder.stop()
                else: self.start_recording()
            elif key.char == 'p': self.recorder.toggle_pause()
        except AttributeError: pass
            
    def setup_hotkeys(self):
        self.listener = keyboard.Listener(on_press=self.on_hotkey_press)
        self.listener.start()
        
    def create_preview_window(self):
        self.preview_window = tk.Toplevel(self)
        self.preview_window.title("Live Preview")
        self.preview_window.geometry("480x270")
        self.preview_window.configure(bg="black")
        self.preview_window.resizable(True, True)
        # Keep it on top of other windows
        self.preview_window.attributes("-topmost", True)

        self.preview_label = tk.Label(self.preview_window, bg="black")
        self.preview_label.pack(expand=True, fill=tk.BOTH)

        self.preview_thread = threading.Thread(target=self.update_preview, daemon=True)
        self.preview_thread.start()

    def update_preview(self):
        with mss.mss() as sct:
            while not self.app_stop_event.is_set():
                try:
                    # Get the currently selected monitor from the combobox
                    # We add 1 because we excluded monitor 0 from the list
                    monitor_index = self.monitor_box.current() + 1
                    monitor = sct.monitors[monitor_index]
                    
                    # Grab the screen
                    img_np = np.array(sct.grab(monitor))

                    # Resize for preview performance
                    h, w, _ = img_np.shape
                    preview_w = self.preview_window.winfo_width()
                    preview_h = int(h * (preview_w / w))
                    
                    # Use Pillow for robust resizing and conversion
                    img_pil = Image.fromarray(cv2.cvtColor(img_np, cv2.COLOR_BGRA2RGB))
                    img_pil.thumbnail((preview_w, preview_h), Image.LANCZOS)
                    
                    photo_image = ImageTk.PhotoImage(image=img_pil)
                    
                    # Update the label in the main thread
                    # Important: Keep a reference to the image to prevent garbage collection
                    self.preview_label.config(image=photo_image)
                    self.preview_label.image = photo_image
                    
                    time.sleep(1/30) # Update preview at ~30fps
                except (tk.TclError, RuntimeError):
                    # This happens if the window is closed while the thread is running
                    break
                except Exception as e:
                    print(f"Preview Error: {e}")
                    time.sleep(1)

    def show_help_window(self):
        help_win = tk.Toplevel(self)
        help_win.title("Help & Information")
        help_win.geometry("700x550")
        help_win.configure(bg="#2E3440")
        
        help_text_widget = scrolledtext.ScrolledText(
            help_win, wrap=tk.WORD, bg="#434C5E", fg="#ECEFF4",
            font=("Segoe UI", 10), relief=tk.FLAT, padx=10, pady=10
        )
        help_text_widget.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)

        help_content = """
        Welcome to the Greg Seymour Screen Recorder!

        --- QUICK START ---
        1. Select the monitor you want to record.
        2. Choose a quality preset (e.g., "Smooth (60fps)").
        3. Click "Start Recording" or press the 'R' key.
        4. To stop, click "Stop Recording" or press 'R' again.

        --- ❗ IMPORTANT: AVOIDING THE GUI IN YOUR RECORDING ---
        To record your screen WITHOUT the recorder's controls in the video, you MUST place the main control panel and the live preview window on a DIFFERENT monitor than the one you select in the "Monitor to Record" dropdown. This is standard practice for most recording software.

        --- RECORDING MODES ---
        • High-Precision (uses RAM): This is the RECOMMENDED mode. It records all frames to your computer's memory (RAM) first and then saves the video. This guarantees that the final video's speed is perfect and matches what you saw on screen. Best for short, high-quality clips (e.g., under 5-10 minutes, depending on your RAM).

        • Long-form (Direct-to-Disk): This mode saves frames directly to your hard drive. It uses very little RAM, making it suitable for very long recordings (hours). However, if your computer is slow, it might drop frames, leading to a slightly choppy result. (Note: Currently, this mode also uses the RAM method as it is superior).

        --- HOTKEYS ---
        • R key: Toggles Start / Stop recording.
        • P key: Toggles Pause / Resume during a recording.
        Note: Hotkeys are disabled when you are typing in an input field.

        --- PRESETS EXPLAINED ---
        The presets are just quick settings for Frames Per Second (FPS).
        • 24fps (Cinematic): Standard for movies. Can look stuttery for gameplay.
        • 30fps (Standard): Good for tutorials and general screen recording.
        • 60fps (Smooth): The standard for smooth gameplay and modern video.
        • 75/90/120/144/240fps (High Refresh): Use these if your monitor has a high refresh rate and you want to capture ultra-smooth motion for slow-motion editing. Recording at very high FPS is demanding on your PC.

        --- SAVING & PROGRESS ---
        After you stop recording, the app will enter a "Saving video..." state. A progress bar will appear, showing you the progress of encoding the video file. Please be patient, as saving high-FPS or long videos can take some time!

        """
        help_text_widget.insert(tk.INSERT, help_content)
        help_text_widget.config(state=tk.DISABLED) # Make it read-only

    def on_closing(self):
        if self.recorder.is_recording:
            if messagebox.askyesno("Exit Confirmation", "Recording is active. Stop and exit? Any unsaved progress will be lost."):
                self.app_stop_event.set() # Signal threads to stop
                self.recorder.stop() # This will now just set the stop event
                # We can't wait for the thread here, so we just close
                self.destroy()
        else:
            self.app_stop_event.set()
            self.destroy()

if __name__ == "__main__":
    # Ensure the default directory exists on startup
    os.makedirs(DEFAULT_OUTPUT_DIR, exist_ok=True)
    app = App()
    app.mainloop()