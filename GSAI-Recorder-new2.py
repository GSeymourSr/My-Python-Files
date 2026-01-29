import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import mss
import cv2
import numpy as np
import threading
import time
import os
import wave  # ## NEW: For saving audio to a .wav file
import subprocess  # ## NEW: To run FFmpeg for combining audio/video
from datetime import datetime
from pynput import keyboard
import pygame
from PIL import Image, ImageTk
import soundcard as sc  # ## NEW: The core library for audio recording

# =============================================================================
# ===== CONFIGURATION & PRESETS =====
# =============================================================================
# IMPORTANT: Update this path to your sound file if it's different!
SOUND_FILE = r"C:\\- AAII TOOLS -\\firework-whistle-190306.mp3"

DEFAULT_OUTPUT_DIR = r"C:\- AI  NEW CONTENT"

PRESETS = {
    "Cinematic (24fps)": 24, "Standard (30fps)": 30, "Smooth (60fps)": 60,
    "Gamer Smooth (75fps)": 75, "VR / Mobile (90fps)": 90, "Pro Gamer (120fps)": 120,
    "High Refresh (144fps)": 144, "Butter (240fps)": 240
}

# ## NEW: FFmpeg path configuration.
# ## IMPORTANT: Change this to the location of ffmpeg.exe on your system!
# ## You can download it from: https://ffmpeg.org/download.html
# ## Example for Windows: FFMPEG_PATH = "C:\\ffmpeg\\bin\\ffmpeg.exe"
FFMPEG_PATH = "ffmpeg" # This works if ffmpeg is in your system's PATH

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
        self.progress_callback = progress_callback
        self.done_callback = done_callback
        self.audio_player = audio_player
        
        # ## NEW: Audio-related attributes
        self.audio_thread = None
        self.temp_audio_file = None

    def start(self, fps, duration_seconds, monitor_index, mode, audio_device): # ## NEW: audio_device parameter
        if self.is_recording:
            return

        self.is_recording = True
        self.is_paused = False
        self.stop_event.clear()
        self.pause_event.clear()

        self.audio_player.play()
        self.status_callback("Recording", "green")
        
        # ## NEW: Create temporary file path for audio
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.temp_audio_file = os.path.join(self.output_dir, f"temp_audio_{timestamp}.wav")

        # ## NEW: Start audio recording thread if a device is selected
        if audio_device:
            self.audio_thread = threading.Thread(
                target=self._record_audio_loop,
                args=(audio_device,),
                daemon=True
            )
            self.audio_thread.start()

        # ## NOTE: For this advanced version, we will focus on the superior RAM method.
        # ## The direct-to-disk method is significantly more complex to sync with audio.
        self.recording_thread = threading.Thread(
            target=self._record_video_loop_ram,
            args=(fps, duration_seconds, monitor_index),
            daemon=True
        )
        self.recording_thread.start()

    def stop(self):
        if not self.is_recording:
            return
        
        self.stop_event.set()
        self.audio_player.play()
        # The processing and saving will now happen after the thread finishes.
        # The status will be updated to "Saving..." inside the thread.

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

    ## NEW: Dedicated audio recording loop
    def _record_audio_loop(self, audio_device):
        try:
            with audio_device.recorder(samplerate=48000) as mic, \
                 wave.open(self.temp_audio_file, 'wb') as wf:
                
                wf.setnchannels(mic.channels)
                wf.setsampwidth(2) # 2 bytes = 16-bit audio
                wf.setframerate(48000)
                
                while not self.stop_event.is_set():
                    if self.pause_event.is_set():
                        time.sleep(0.1)
                        continue
                    
                    data = mic.record(numframes=1024)
                    wf.writeframes(data.tobytes())
        except Exception as e:
            # Using messagebox from a thread is tricky, printing is safer.
            print(f"Audio recording error: {e}")
            # Ensure the main thread knows the audio failed.
            self.temp_audio_file = None 

    def _record_video_loop_ram(self, target_fps, duration_seconds, monitor_index):
        frames = []
        capture_start_time = time.time()
        
        try:
            with mss.mss() as sct:
                monitor = sct.monitors[monitor_index]
                while not self.stop_event.is_set():
                    if self.pause_event.is_set():
                        time.sleep(0.1)
                        continue

                    img = sct.grab(monitor)
                    frames.append(cv2.cvtColor(np.array(img), cv2.COLOR_BGRA2BGR))
                    
                    if duration_seconds > 0 and (time.time() - capture_start_time) >= duration_seconds:
                        self.stop_event.set()
                    
                    time.sleep(0.001)

        except Exception as e:
            messagebox.showerror("Recording Error", f"An error occurred during video capture: {e}")
            self.done_callback(None, 0, 0)
            return
        
        # --- Post-Recording, Processing & Saving ---
        self.is_recording = False
        self.status_callback("Processing and Saving...", "cyan")
        
        if not frames:
            print("No frames captured.")
            self._cleanup_temp_files()
            self.done_callback(None, 0, 0)
            return

        actual_duration = time.time() - capture_start_time
        actual_fps = len(frames) / actual_duration

        # ## NEW: Handle video and audio combination with FFmpeg
        self._combine_audio_video(frames, actual_fps, target_fps)
        
    def _combine_audio_video(self, frames, actual_fps, target_fps):
        os.makedirs(self.output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        final_output_path = os.path.join(self.output_dir, f"Recording_{timestamp}_{actual_fps:.2f}fps.mp4")
        temp_video_path = os.path.join(self.output_dir, f"temp_video_{timestamp}.mp4")

        # --- Save video to a temporary file ---
        try:
            self.status_callback("Saving temporary video...", "cyan")
            height, width, _ = frames[0].shape
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(temp_video_path, fourcc, actual_fps, (width, height))
            
            total_frames = len(frames)
            for i, frame in enumerate(frames):
                out.write(frame)
                progress_percent = int(((i + 1) / total_frames) * 50) # Video saving is first 50%
                self.progress_callback(progress_percent)
            out.release()
        except Exception as e:
            messagebox.showerror("Saving Error", f"Could not save the temporary video file: {e}")
            self._cleanup_temp_files(temp_video_path)
            self.done_callback(None, 0, 0)
            return

        # --- Combine using FFmpeg ---
        try:
            self.status_callback("Combining Audio & Video with FFmpeg...", "#88C0D0")
            self.progress_callback(50) # Move progress to halfway

            # Check if FFmpeg exists
            try:
                subprocess.run([FFMPEG_PATH, "-version"], check=True, capture_output=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                messagebox.showerror("FFmpeg Error", f"FFmpeg not found or not working.\n"
                                     f"Please ensure FFmpeg is installed and the path is correct in the script.\n"
                                     f"Attempted path: {FFMPEG_PATH}")
                self._cleanup_temp_files(temp_video_path)
                self.done_callback(None, 0, 0)
                return

            if self.temp_audio_file and os.path.exists(self.temp_audio_file):
                # We have audio, combine it
                command = [
                    FFMPEG_PATH,
                    '-y',  # Overwrite output file if it exists
                    '-i', temp_video_path,
                    '-i', self.temp_audio_file,
                    '-c:v', 'copy',  # Copy video stream without re-encoding (very fast!)
                    '-c:a', 'aac',   # Encode audio to AAC
                    '-b:a', '192k',  # Audio bitrate
                    '-shortest',     # Finish encoding when the shortest input stream ends
                    final_output_path
                ]
            else:
                # No audio, just rename the temp video file
                os.rename(temp_video_path, final_output_path)
                self.done_callback(final_output_path, target_fps, actual_fps)
                return # Skip subprocess call
            
            # Run the FFmpeg command
            process = subprocess.run(command, check=True, capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
            self.progress_callback(100)
            self.done_callback(final_output_path, target_fps, actual_fps)

        except subprocess.CalledProcessError as e:
            error_message = f"FFmpeg failed to combine the files.\n\n" \
                            f"FFmpeg stderr:\n{e.stderr}"
            messagebox.showerror("FFmpeg Error", error_message)
            self.done_callback(None, 0, 0)
        except Exception as e:
            messagebox.showerror("Finalizing Error", f"An unexpected error occurred during finalization: {e}")
            self.done_callback(None, 0, 0)
        finally:
            self._cleanup_temp_files(temp_video_path)

    def _cleanup_temp_files(self, temp_video_path=None):
        if temp_video_path and os.path.exists(temp_video_path):
            os.remove(temp_video_path)
        if self.temp_audio_file and os.path.exists(self.temp_audio_file):
            os.remove(self.temp_audio_file)

# =============================================================================
# ===== GRAPHICAL USER INTERFACE (GUI) =====
# =============================================================================
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        # ## NEW: Store audio devices
        self.audio_devices = {}
        
        self.audio_player = AudioPlayer(SOUND_FILE)
        self.recorder = ScreenRecorder(
            self.update_status, self.update_save_progress, 
            self.on_recording_finished, self.audio_player
        )
        
        self.title("🎬 Greg Seymour Professional Screen Recorder")
        # ## NEW: Start maximized for a "big GUI" feel
        self.state('zoomed') 
        self.minsize(800, 700) # Set a minimum size
        self.configure(bg="#2E3440")

        self.app_stop_event = threading.Event()

        style = ttk.Style(self)
        style.theme_use('clam')
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
        
        top_frame = ttk.Frame(self.main_frame)
        top_frame.pack(fill=tk.X, pady=(0, 20))
        title_label = ttk.Label(top_frame, text="Greg Seymour Professional Screen Recorder", style='Title.TLabel')
        title_label.pack(side=tk.LEFT, expand=True)
        help_btn = ttk.Button(top_frame, text="❔ Help / Info", command=self.show_help_window, width=15)
        help_btn.pack(side=tk.RIGHT)

        settings_frame = ttk.Frame(self.main_frame)
        settings_frame.pack(fill=tk.X, pady=10)
        settings_frame.columnconfigure(1, weight=1)

        # --- Settings Widgets ---
        ttk.Label(settings_frame, text="Monitor to Record:").grid(row=0, column=0, padx=5, pady=10, sticky='w')
        self.monitor_box = ttk.Combobox(settings_frame, state="readonly")
        self.monitor_box.grid(row=0, column=1, padx=5, pady=10, sticky='ew')
        self.populate_monitors()

        # ## NEW: Audio device selection
        ttk.Label(settings_frame, text="Audio Source:").grid(row=1, column=0, padx=5, pady=10, sticky='w')
        self.audio_box = ttk.Combobox(settings_frame, state="readonly")
        self.audio_box.grid(row=1, column=1, padx=5, pady=10, sticky='ew')
        self.populate_audio_devices()

        ttk.Label(settings_frame, text="Preset:").grid(row=2, column=0, padx=5, pady=5, sticky='w')
        self.preset_box = ttk.Combobox(settings_frame, values=list(PRESETS.keys()), state="readonly")
        self.preset_box.set("Smooth (60fps)")
        self.preset_box.grid(row=2, column=1, padx=5, pady=5, sticky='ew')
        self.preset_box.bind("<<ComboboxSelected>>", self.apply_preset)

        ttk.Label(settings_frame, text="FPS:").grid(row=3, column=0, padx=5, pady=5, sticky='w')
        self.fps_entry = ttk.Entry(settings_frame, width=15)
        self.fps_entry.grid(row=3, column=1, padx=5, pady=5, sticky='w')
        self.apply_preset()

        ttk.Label(settings_frame, text="Duration (sec, 0=unlimited):").grid(row=4, column=0, padx=5, pady=5, sticky='w')
        self.duration_entry = ttk.Entry(settings_frame, width=15)
        self.duration_entry.insert(0, "0")
        self.duration_entry.grid(row=4, column=1, padx=5, pady=5, sticky='w')
        
        # ## Note: The "Mode" selection is removed for simplicity, as the RAM + FFmpeg method is superior for synced A/V.

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
        
        self.progress_bar = ttk.Progressbar(self.main_frame, orient='horizontal', length=300, mode='determinate', style='Horizontal.TProgressbar')
        self.progress_bar.pack(pady=5)
        self.progress_bar.pack_forget()

        self.setup_hotkeys()
        self.create_preview_window()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def start_recording(self):
        try:
            fps = float(self.fps_entry.get())
            duration = float(self.duration_entry.get())
            monitor_index = self.monitor_box.current() + 1 # Add 1 to match sct.monitors
            
            # ## NEW: Get selected audio device
            selected_audio_name = self.audio_box.get()
            audio_device = self.audio_devices.get(selected_audio_name, None)

            if fps <= 0 or duration < 0:
                raise ValueError("FPS must be > 0 and Duration must be >= 0.")
            
            os.makedirs(self.recorder.output_dir, exist_ok=True)
            
            self.recorder.start(fps, duration, monitor_index, "ram", audio_device)

        except ValueError as e:
            messagebox.showerror("Invalid Input", f"Please enter valid numbers. Details: {e}")
        except Exception as e:
            messagebox.showerror("Error", f"Could not start recording. Details: {e}")
            
    def on_recording_finished(self, filename, target_fps, actual_fps):
        self.update_status("Idle", "#D8DEE9")
        self.progress_bar.pack_forget()

        if filename:
            message = (f"Recording successful!\n\n"
                       f"Video saved to:\n{os.path.abspath(filename)}\n\n"
                       f"Target FPS: {target_fps:.2f}\n"
                       f"Actual Captured FPS: {actual_fps:.2f}")
            messagebox.showinfo("Success", message)
        else:
            messagebox.showwarning("Recording Canceled", "Recording stopped or failed. No file was saved.")
    
    def update_save_progress(self, percentage):
        if not self.progress_bar.winfo_viewable():
            self.progress_bar.pack(pady=5, fill=tk.X, padx=20)
        self.progress_bar['value'] = percentage
        self.update_idletasks()

    def populate_monitors(self):
        with mss.mss() as sct:
            monitors = [f"Monitor {i}: {m['width']}x{m['height']} @ ({m['left']},{m['top']})" for i, m in enumerate(sct.monitors)]
            self.monitor_box['values'] = monitors[1:] # Exclude the 'all-in-one' monitor 0
            if len(monitors) > 1:
                self.monitor_box.current(0)

    ## NEW: Method to find and list available audio devices
    def populate_audio_devices(self):
        self.audio_devices.clear()
        device_names = ["None (No Audio)"]
        
        try:
            # The most important device: default output (what you hear)
            default_speaker = sc.default_speaker()
            speaker_name = f"Default Speaker: {default_speaker.name}"
            self.audio_devices[speaker_name] = default_speaker
            device_names.append(speaker_name)

            # Also list microphones
            for mic in sc.all_microphones(include_loopback=True):
                if mic.id != default_speaker.id: # Avoid duplicates
                    mic_name = f"Mic: {mic.name}"
                    self.audio_devices[mic_name] = mic
                    device_names.append(mic_name)
        except Exception as e:
            print(f"Could not enumerate audio devices: {e}")

        self.audio_box['values'] = device_names
        if len(device_names) > 1:
            self.audio_box.current(1) # Default to the speaker if available
        else:
            self.audio_box.current(0) # Default to "None"

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
        try:
            focused_widget = self.focus_get()
            if isinstance(focused_widget, (ttk.Entry, tk.Text)):
                return
        except:
            pass

        try:
            if key.char == 'r':
                if self.recorder.is_recording: self.recorder.stop()
                else: self.start_recording()
            elif key.char == 'p': self.recorder.toggle_pause()
        except AttributeError: 
            # ## NEW: Fullscreen toggle hotkey
            if key == keyboard.Key.f11:
                self.toggle_fullscreen()

    def setup_hotkeys(self):
        # ## NEW: Use non-blocking listener for better integration
        self.listener = keyboard.Listener(on_press=self.on_hotkey_press)
        self.listener.start()
        
    def create_preview_window(self):
        self.preview_window = tk.Toplevel(self)
        self.preview_window.title("Live Preview")
        self.preview_window.geometry("480x270")
        self.preview_window.configure(bg="black")
        self.preview_window.resizable(True, True)
        self.preview_window.attributes("-topmost", True)
        self.preview_label = tk.Label(self.preview_window, bg="black")
        self.preview_label.pack(expand=True, fill=tk.BOTH)
        self.preview_thread = threading.Thread(target=self.update_preview, daemon=True)
        self.preview_thread.start()

    def update_preview(self):
        with mss.mss() as sct:
            while not self.app_stop_event.is_set():
                try:
                    monitor_index = self.monitor_box.current() + 1
                    monitor = sct.monitors[monitor_index]
                    img_np = np.array(sct.grab(monitor))
                    h, w, _ = img_np.shape
                    preview_w = self.preview_window.winfo_width()
                    preview_h = int(h * (preview_w / w))
                    img_pil = Image.fromarray(cv2.cvtColor(img_np, cv2.COLOR_BGRA2RGB))
                    img_pil.thumbnail((preview_w, preview_h), Image.LANCZOS)
                    photo_image = ImageTk.PhotoImage(image=img_pil)
                    self.preview_label.config(image=photo_image)
                    self.preview_label.image = photo_image
                    time.sleep(1/30)
                except (tk.TclError, RuntimeError):
                    break
                except Exception as e:
                    print(f"Preview Error: {e}")
                    time.sleep(1)

    # ## NEW: Fullscreen toggle method
    def toggle_fullscreen(self, event=None):
        self.attributes("-fullscreen", not self.attributes("-fullscreen"))

    def show_help_window(self):
        help_win = tk.Toplevel(self)
        help_win.title("Help & Information")
        help_win.geometry("700x600") # Increased size
        help_win.configure(bg="#2E3440")
        help_text_widget = scrolledtext.ScrolledText(
            help_win, wrap=tk.WORD, bg="#434C5E", fg="#ECEFF4",
            font=("Segoe UI", 10), relief=tk.FLAT, padx=10, pady=10
        )
        help_text_widget.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)

        # ## NEW: Updated help content
        help_content = """
        Welcome to the Greg Seymour Professional Screen Recorder!

        --- ❗ CRITICAL SETUP: FFmpeg ---
        This program now records audio and uses a professional tool called FFmpeg to combine it with the video. 
        YOU MUST INSTALL FFMPEG FOR THIS TO WORK.

        1. Download FFmpeg from: https://ffmpeg.org/download.html
        2. Unzip the file. Inside the 'bin' folder, you will find 'ffmpeg.exe'.
        3. Add the 'bin' folder to your system's PATH environment variable, OR
        4. Hardcode the full path to 'ffmpeg.exe' in the FFMPEG_PATH variable at the top of the Python script.

        --- QUICK START ---
        1. Select the monitor you want to record.
        2. Select the audio source (usually "Default Speaker" to record what you hear).
        3. Choose a quality preset (e.g., "Smooth (60fps)").
        4. Press 'R' or click the "Start Recording" button.

        --- HOTKEYS ---
        • R key: Toggles Start / Stop recording.
        • P key: Toggles Pause / Resume during a recording.
        • F11 key: Toggles fullscreen mode for the main window.

        --- AUDIO SOURCES ---
        • Default Speaker: Records the sound currently playing out of your speakers/headphones. This is what you want for recording games, videos, etc.
        • Mic: Records from your microphone.
        • None: Records video only.

        --- SAVING PROCESS ---
        After stopping, the app will:
        1. Save the captured video frames (Progress: 0-50%)
        2. Use FFmpeg to combine video and audio (Progress: 50-100%)
        Please be patient during this phase.

        """
        help_text_widget.insert(tk.INSERT, help_content)
        help_text_widget.config(state=tk.DISABLED)

    def on_closing(self):
        if self.recorder.is_recording:
            if messagebox.askyesno("Exit Confirmation", "Recording is active. Stop and exit? Any unsaved progress will be lost."):
                self.app_stop_event.set()
                self.recorder.stop()
                self.destroy()
        else:
            self.app_stop_event.set()
            # ## NEW: Gracefully stop the hotkey listener
            if self.listener.is_alive():
                self.listener.stop()
            self.destroy()

# ## NEW: Main execution block needs a helper class for AudioPlayer
class AudioPlayer:
    def __init__(self, sound_file):
        self.sound = None
        try:
            pygame.mixer.init()
            if os.path.exists(sound_file):
                self.sound = pygame.mixer.Sound(sound_file)
            else:
                messagebox.showwarning("Audio Warning", f"Start/Stop sound file not found.")
        except Exception as e:
            print(f"Could not initialize audio: {e}")
    def play(self):
        if self.sound:
            try: self.sound.play()
            except Exception as e: print(f"Error playing sound: {e}")

if __name__ == "__main__":
    os.makedirs(DEFAULT_OUTPUT_DIR, exist_ok=True)
    app = App()
    app.mainloop()