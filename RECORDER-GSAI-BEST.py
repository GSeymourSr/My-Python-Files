import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import mss
import cv2
import numpy as np
import threading
import time
import os
import wave
import subprocess
import queue  # NEW: For buffering frames
from datetime import datetime, timedelta
from pynput import keyboard
import pygame
from PIL import Image, ImageTk
import soundcard as sc

# =============================================================================
# ===== CONFIGURATION & PRESETS =====
# =============================================================================
SOUND_FILE = r"C:\- AAII TOOLS -\firework-whistle-190306.mp3"
DEFAULT_OUTPUT_DIR = r"C:\- AI  NEW CONTENT"
FFMPEG_PATH = "ffmpeg"  # Change to full path like r"C:\ffmpeg\bin\ffmpeg.exe" if needed

# Optimized Presets for Low-End Hardware and Teaching
PRESETS = {
    "Teacher / Slides (10 FPS)": 10,       # Best for PowerPoint/Static screens
    "Desktop Demo (20 FPS)": 20,           # Good for software tutorials
    "Standard Video (30 FPS)": 30,         # Standard YouTube quality
    "Smooth Motion (48 FPS)": 48,          # Compromise for N5000 CPU
    "High Motion (60 FPS)": 60             # Only use if recording small windows
}

# =============================================================================
# ===== CORE SCREEN RECORDER LOGIC =====
# =============================================================================
class ScreenRecorder:
    def __init__(self, status_callback, progress_callback, done_callback, audio_player, timer_callback):
        self.is_recording = False
        self.is_paused = False
        self.stop_event = threading.Event()
        self.pause_event = threading.Event()
        self.output_dir = DEFAULT_OUTPUT_DIR
        self.status_callback = status_callback
        self.progress_callback = progress_callback
        self.done_callback = done_callback
        self.audio_player = audio_player
        self.timer_callback = timer_callback

        self.audio_thread = None
        self.video_thread = None
        self.writer_thread = None
        self.temp_audio_file = None
        self.start_time = None
        
        # Performance Buffer
        self.frame_queue = queue.Queue(maxsize=300) # Buffer about 10 seconds of video

    def start(self, fps, duration_seconds, monitor_index, audio_device):
        if self.is_recording: return

        self.is_recording = True
        self.is_paused = False
        self.stop_event.clear()
        self.pause_event.clear()
        self.frame_queue.queue.clear() # Clear old data

        self.audio_player.play()
        self.status_callback("Recording", "green")
        self.start_time = time.time()

        # Temp Files
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.temp_audio_file = os.path.join(self.output_dir, f"temp_audio_{timestamp}.wav")
        self.temp_video_file = os.path.join(self.output_dir, f"temp_video_{timestamp}.avi")

        # 1. Start Audio Thread
        if audio_device:
            self.audio_thread = threading.Thread(target=self._record_audio_loop, args=(audio_device,), daemon=True)
            self.audio_thread.start()

        # 2. Start Video Writer Thread (Consumer)
        self.writer_thread = threading.Thread(target=self._video_writer_loop, args=(fps, monitor_index), daemon=True)
        self.writer_thread.start()

        # 3. Start Video Capture Thread (Producer)
        self.video_thread = threading.Thread(target=self._screen_capture_loop, args=(fps, duration_seconds, monitor_index), daemon=True)
        self.video_thread.start()

        # 4. Start Timer Thread
        threading.Thread(target=self._timer_loop, daemon=True).start()

    def stop(self):
        if not self.is_recording: return
        self.stop_event.set()
        self.audio_player.play()

    def toggle_pause(self):
        if not self.is_recording: return
        self.is_paused = not self.is_paused
        if self.is_paused:
            self.pause_event.set()
            self.status_callback("Paused", "orange")
        else:
            self.pause_event.clear()
            self.status_callback("Recording", "green")
            # Adjust start time so the timer doesn't count paused time
            # (Simplified logic: timer keeps running but pauses visually in this version)

    def _timer_loop(self):
        while not self.stop_event.is_set():
            if not self.is_paused:
                elapsed = int(time.time() - self.start_time)
                formatted_time = str(timedelta(seconds=elapsed))
                self.timer_callback(formatted_time)
            time.sleep(0.5)

    def _record_audio_loop(self, audio_device):
        try:
            with audio_device.recorder(samplerate=44100) as mic, \
                 wave.open(self.temp_audio_file, 'wb') as wf:
                wf.setnchannels(mic.channels)
                wf.setsampwidth(2)
                wf.setframerate(44100)
                while not self.stop_event.is_set():
                    if self.pause_event.is_set():
                        time.sleep(0.1)
                        continue
                    data = mic.record(numframes=1024)
                    wf.writeframes(data.tobytes())
        except Exception as e:
            print(f"Audio Error: {e}")
            self.temp_audio_file = None

    def _screen_capture_loop(self, target_fps, duration_seconds, monitor_index):
        # This thread ONLY captures screens and puts them in the queue.
        # It needs to be fast.
        capture_delay = 1.0 / target_fps
        with mss.mss() as sct:
            monitor = sct.monitors[monitor_index]
            
            while not self.stop_event.is_set():
                loop_start = time.time()
                
                if self.pause_event.is_set():
                    time.sleep(0.1)
                    continue

                if duration_seconds > 0 and (time.time() - self.start_time) >= duration_seconds:
                    self.stop_event.set()
                    break

                # Capture Frame
                try:
                    img = sct.grab(monitor)
                    # Convert raw bytes to numpy array (fastest method)
                    frame = np.frombuffer(img.rgb, dtype=np.uint8)
                    frame = frame.reshape((img.height, img.width, 3))
                    frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                    
                    # Put in queue. If queue is full, we drop a frame (Performance protection)
                    if not self.frame_queue.full():
                        self.frame_queue.put(frame)
                except Exception as e:
                    print(f"Capture Error: {e}")

                # Maintain FPS
                process_time = time.time() - loop_start
                sleep_time = max(0, capture_delay - process_time)
                time.sleep(sleep_time)
        
        # Signal the writer to stop
        self.frame_queue.put(None)

    def _video_writer_loop(self, fps, monitor_index):
        # This thread takes frames from memory and writes to disk.
        # It handles the IO bottleneck.
        with mss.mss() as sct:
            monitor = sct.monitors[monitor_index]
            width, height = monitor["width"], monitor["height"]

        # MJPG is fast to encode, low CPU usage, but larger file size. 
        # We re-encode to MP4 later anyway.
        fourcc = cv2.VideoWriter_fourcc(*'MJPG') 
        out = cv2.VideoWriter(self.temp_video_file, fourcc, fps, (width, height))

        while True:
            frame = self.frame_queue.get()
            if frame is None: # Sentinel value to stop
                break
            out.write(frame)
            self.frame_queue.task_done()
        
        out.release()
        self._finalize_recording(fps)

    def _finalize_recording(self, target_fps):
        self.is_recording = False
        self.status_callback("Finalizing...", "cyan")
        
        # Combine with FFmpeg
        self._combine_audio_video(target_fps)

    def _combine_audio_video(self, target_fps):
        os.makedirs(self.output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        final_output_path = os.path.join(self.output_dir, f"Record_{timestamp}.mp4")

        try:
            self.status_callback("Encoding to MP4...", "#88C0D0")
            self.progress_callback(50)

            command = [
                FFMPEG_PATH, '-y',
                '-i', self.temp_video_file,
            ]

            if self.temp_audio_file and os.path.exists(self.temp_audio_file):
                command.extend(['-i', self.temp_audio_file])
            
            # Use 'ultrafast' preset for your CPU to ensure it finishes quickly
            command.extend([
                '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '23',
                '-c:a', 'aac', '-b:a', '128k',
                '-shortest', # Stop when shortest stream ends
                final_output_path
            ])

            subprocess.run(command, check=True, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
            
            self.progress_callback(100)
            self.done_callback(final_output_path)

        except Exception as e:
            messagebox.showerror("FFmpeg Error", f"Error saving file: {e}")
            self.done_callback(None)
        finally:
            self._cleanup_temp_files()

    def _cleanup_temp_files(self):
        if os.path.exists(self.temp_video_file): os.remove(self.temp_video_file)
        if self.temp_audio_file and os.path.exists(self.temp_audio_file): os.remove(self.temp_audio_file)

# =============================================================================
# ===== GUI =====
# =============================================================================
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.audio_devices = {}
        self.audio_player = AudioPlayer(SOUND_FILE)
        
        # Initialize Recorder with extra timer callback
        self.recorder = ScreenRecorder(
            self.update_status, self.update_progress, 
            self.on_finished, self.audio_player, self.update_timer_label
        )
        
        self.title("🎬 Greg Seymour - Optimized Teacher's Recorder")
        self.state('zoomed') 
        self.minsize(800, 700)
        self.configure(bg="#2E3440")

        self.app_stop_event = threading.Event()
        self.setup_ui()
        self.setup_hotkeys()
        self.create_preview_window()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def setup_ui(self):
        style = ttk.Style(self)
        style.theme_use('clam')
        style.configure('TFrame', background='#2E3440')
        style.configure('TLabel', font=('Segoe UI', 11), background='#2E3440', foreground='#D8DEE9')
        style.configure('Title.TLabel', font=('Segoe UI', 24, 'bold'), foreground='#88C0D0')
        style.configure('Timer.TLabel', font=('Consolas', 40, 'bold'), foreground='#A3BE8C', background='#2E3440')
        style.configure('TButton', font=('Segoe UI', 10, 'bold'))

        main = ttk.Frame(self, padding=20)
        main.pack(expand=True, fill=tk.BOTH)

        # Header
        ttk.Label(main, text="Greg Seymour Professional Recorder", style='Title.TLabel').pack(pady=(0, 10))
        
        # Timer Display
        self.timer_label = ttk.Label(main, text="00:00:00", style='Timer.TLabel')
        self.timer_label.pack(pady=10)

        # Settings Container
        settings = ttk.Frame(main)
        settings.pack(fill=tk.X, pady=10)
        settings.columnconfigure(1, weight=1)

        # Monitor
        ttk.Label(settings, text="Monitor:").grid(row=0, column=0, sticky='w', pady=5)
        self.monitor_box = ttk.Combobox(settings, state="readonly")
        self.monitor_box.grid(row=0, column=1, sticky='ew', pady=5)
        self.populate_monitors()

        # Audio
        ttk.Label(settings, text="Audio Source:").grid(row=1, column=0, sticky='w', pady=5)
        self.audio_box = ttk.Combobox(settings, state="readonly")
        self.audio_box.grid(row=1, column=1, sticky='ew', pady=5)
        self.populate_audio_devices()

        # Preset
        ttk.Label(settings, text="Quality Preset:").grid(row=2, column=0, sticky='w', pady=5)
        self.preset_box = ttk.Combobox(settings, values=list(PRESETS.keys()), state="readonly")
        self.preset_box.set("Standard Video (30 FPS)")
        self.preset_box.grid(row=2, column=1, sticky='ew', pady=5)
        self.preset_box.bind("<<ComboboxSelected>>", self.apply_preset)

        # FPS & Duration
        ttk.Label(settings, text="Target FPS:").grid(row=3, column=0, sticky='w', pady=5)
        self.fps_entry = ttk.Entry(settings)
        self.fps_entry.grid(row=3, column=1, sticky='w', pady=5)
        
        ttk.Label(settings, text="Auto-Stop (sec, 0=Never):").grid(row=4, column=0, sticky='w', pady=5)
        self.duration_entry = ttk.Entry(settings)
        self.duration_entry.insert(0, "0")
        self.duration_entry.grid(row=4, column=1, sticky='w', pady=5)

        self.apply_preset() # Set initial FPS

        # Output Button
        out_frame = ttk.Frame(main)
        out_frame.pack(fill=tk.X, pady=10)
        self.out_lbl = ttk.Label(out_frame, text=f"Save to: {self.recorder.output_dir}")
        self.out_lbl.pack(side=tk.LEFT)
        ttk.Button(out_frame, text="Change Folder", command=self.change_folder).pack(side=tk.RIGHT)

        # Buttons
        btns = ttk.Frame(main)
        btns.pack(pady=20)
        ttk.Button(btns, text="🔴 Record (R)", command=self.toggle_record).pack(side=tk.LEFT, padx=10, ipadx=10, ipady=5)
        ttk.Button(btns, text="⏸️ Pause (P)", command=self.recorder.toggle_pause).pack(side=tk.LEFT, padx=10, ipadx=10, ipady=5)
        ttk.Button(btns, text="⏹️ Stop (R)", command=self.recorder.stop).pack(side=tk.LEFT, padx=10, ipadx=10, ipady=5)

        # Status & Progress
        self.status_lbl = ttk.Label(main, text="Status: Ready", font=('Segoe UI', 12))
        self.status_lbl.pack()
        self.progress = ttk.Progressbar(main, mode='determinate')

        # Help
        ttk.Button(main, text="Need Help?", command=self.show_help).pack(side=tk.BOTTOM, pady=10)

    def populate_monitors(self):
        with mss.mss() as sct:
            self.monitor_box['values'] = [f"Monitor {i}" for i in range(1, len(sct.monitors))]
            if self.monitor_box['values']: self.monitor_box.current(0)

    def populate_audio_devices(self):
        self.audio_devices.clear()
        names = ["None"]
        try:
            def_spk = sc.default_speaker()
            names.append(f"Speaker: {def_spk.name}")
            self.audio_devices[f"Speaker: {def_spk.name}"] = def_spk
            for mic in sc.all_microphones(include_loopback=True):
                if mic.id != def_spk.id:
                    names.append(f"Mic: {mic.name}")
                    self.audio_devices[f"Mic: {mic.name}"] = mic
        except: pass
        self.audio_box['values'] = names
        self.audio_box.current(1 if len(names) > 1 else 0)

    def apply_preset(self, event=None):
        val = PRESETS.get(self.preset_box.get(), 30)
        self.fps_entry.delete(0, tk.END)
        self.fps_entry.insert(0, str(val))

    def change_folder(self):
        d = filedialog.askdirectory()
        if d: 
            self.recorder.output_dir = d
            self.out_lbl.config(text=f"Save to: {d}")

    def toggle_record(self):
        if self.recorder.is_recording: return
        try:
            fps = float(self.fps_entry.get())
            dur = float(self.duration_entry.get())
            mon = self.monitor_box.current() + 1
            dev = self.audio_devices.get(self.audio_box.get())
            self.recorder.start(fps, dur, mon, dev)
        except ValueError: messagebox.showerror("Error", "Check FPS/Duration values.")

    def update_status(self, txt, col): self.status_lbl.config(text=f"Status: {txt}", foreground=col)
    def update_timer_label(self, time_str): self.timer_label.config(text=time_str)
    
    def update_progress(self, val):
        if not self.progress.winfo_viewable(): self.progress.pack(fill=tk.X, pady=10)
        self.progress['value'] = val
        self.update_idletasks()

    def on_finished(self, path):
        self.update_status("Ready", "#D8DEE9")
        self.progress.pack_forget()
        self.timer_label.config(text="00:00:00")
        if path: messagebox.showinfo("Saved", f"Video saved to:\n{path}")
        else: messagebox.showerror("Error", "Recording failed.")

    def create_preview_window(self):
        self.preview_win = tk.Toplevel(self)
        self.preview_win.title("Preview (Low Refresh)")
        self.preview_win.geometry("400x225")
        self.preview_lbl = tk.Label(self.preview_win, bg="black")
        self.preview_lbl.pack(fill=tk.BOTH, expand=True)
        threading.Thread(target=self.run_preview, daemon=True).start()

    def run_preview(self):
        with mss.mss() as sct:
            while not self.app_stop_event.is_set():
                if self.recorder.is_recording:
                    time.sleep(1.0) # Very slow refresh during recording to save CPU
                else:
                    time.sleep(0.1) # Faster refresh when idle
                
                try:
                    mon = sct.monitors[self.monitor_box.current() + 1]
                    img = np.array(sct.grab(mon))
                    # Heavy downscale for performance
                    img = cv2.resize(img, (400, 225)) 
                    img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGRA2RGB))
                    photo = ImageTk.PhotoImage(img)
                    self.preview_lbl.config(image=photo)
                    self.preview_lbl.image = photo
                except: pass

    def setup_hotkeys(self):
        self.listener = keyboard.Listener(on_press=self.handle_key)
        self.listener.start()

    def handle_key(self, key):
        try:
            if key.char == 'r': 
                if self.recorder.is_recording: self.recorder.stop()
                else: self.toggle_record()
            elif key.char == 'p': self.recorder.toggle_pause()
        except: pass

    def show_help(self):
        msg = """
        OPTIMIZED FOR PERFORMANCE
        
        Presets Explained:
        - Teacher/Slides (10 FPS): Use for PowerPoint or Coding. Creates small files, uses very little CPU.
        - Desktop Demo (20 FPS): Great for showing how to use software.
        - Standard (30 FPS): Best general setting.
        
        Note: Recording will take a moment to 'Finalize' after you click stop. 
        This is normal as we compress the video to save space.
        """
        messagebox.showinfo("Help", msg)

    def on_closing(self):
        self.app_stop_event.set()
        if self.recorder.is_recording: self.recorder.stop()
        self.destroy()

class AudioPlayer:
    def __init__(self, f):
        pygame.mixer.init()
        self.s = pygame.mixer.Sound(f) if os.path.exists(f) else None
    def play(self): 
        if self.s: self.s.play()

if __name__ == "__main__":
    os.makedirs(DEFAULT_OUTPUT_DIR, exist_ok=True)
    app = App()
    app.mainloop()