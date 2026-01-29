import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import mss
import numpy as np
import threading
import time
import os
import subprocess
import soundcard as sc
import soundfile as sf
import keyboard
from datetime import datetime, timedelta

# =============================================================================
# ===== CONFIGURATION =====
# =============================================================================
FFMPEG_BINARY = "ffmpeg"
DEFAULT_OUTPUT_DIR = r"C:\- AI  NEW CONTENT"
TARGET_FPS = 30 

# =============================================================================
# ===== GUI WITH QSV ACCELERATION =====
# =============================================================================
class QSVRecorderApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Greg Seymour - INTEL QSV RECORDER")
        self.state('zoomed')
        self.configure(bg="#2E3440")
        
        self.is_recording = False
        self.stop_event = threading.Event()
        self.start_time = None
        self.audio_devices = {}
        
        self.setup_ui()
        self.init_hotkeys()
        self.log("System Ready. Mode: Intel QuickSync (Hardware Acceleration)")
        self.log("Press 'r' to Record, 's' to Stop.")

    def setup_ui(self):
        # 1. Top Controls
        top_frame = ttk.Frame(self)
        top_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(top_frame, text="Monitor:").pack(side=tk.LEFT)
        self.mon_box = ttk.Combobox(top_frame, values=["Monitor 1", "Monitor 2"], state="readonly", width=10)
        self.mon_box.current(0)
        self.mon_box.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(top_frame, text="Audio:").pack(side=tk.LEFT, padx=(10,0))
        self.aud_box = ttk.Combobox(top_frame, state="readonly", width=40)
        self.aud_box.pack(side=tk.LEFT, padx=5)
        self.populate_audio()
        
        self.timer_lbl = ttk.Label(top_frame, text="00:00:00", font=("Consolas", 20, "bold"), foreground="#BF616A")
        self.timer_lbl.pack(side=tk.RIGHT, padx=20)
        
        # 2. Log Window
        log_frame = ttk.LabelFrame(self, text="FFmpeg Hardware Log")
        log_frame.pack(expand=True, fill=tk.BOTH, padx=10, pady=5)
        
        self.log_box = scrolledtext.ScrolledText(log_frame, bg="black", fg="#88C0D0", font=("Consolas", 10))
        self.log_box.pack(expand=True, fill=tk.BOTH)
        
        # 3. Bottom Controls
        bot_frame = ttk.Frame(self)
        bot_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.btn_record = tk.Button(bot_frame, text="[R] Record", bg="red", fg="white", font=("Segoe UI", 12, "bold"), command=self.start_recording)
        self.btn_record.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
        
        self.btn_stop = tk.Button(bot_frame, text="[S] Stop", bg="gray", fg="white", font=("Segoe UI", 12, "bold"), command=self.stop_recording, state="disabled")
        self.btn_stop.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)

    def log(self, msg):
        def _write():
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.log_box.insert(tk.END, f"[{timestamp}] {msg}\n")
            self.log_box.see(tk.END)
        self.after(0, _write)

    def populate_audio(self):
        try:
            mics = sc.all_microphones(include_loopback=True)
            self.audio_devices = {}
            for m in mics:
                # Filter to make names cleaner
                name = f"{m.name}"
                if m.isloopback: name = f"[SYSTEM AUDIO] {name}"
                else: name = f"[MIC] {name}"
                self.audio_devices[name] = m.id
            
            self.aud_box['values'] = list(self.audio_devices.keys())
            if self.aud_box['values']: self.aud_box.current(0)
        except Exception as e:
            self.log(f"Audio Error: {e}")

    def init_hotkeys(self):
        try:
            keyboard.add_hotkey('r', self.on_hotkey_r)
            keyboard.add_hotkey('s', self.on_hotkey_s)
        except: pass

    def on_hotkey_r(self):
        if not self.is_recording: self.after(0, self.start_recording)

    def on_hotkey_s(self):
        if self.is_recording: self.after(0, self.stop_recording)

    def start_recording(self):
        if self.is_recording: return
        self.is_recording = True
        self.stop_event.clear()
        self.btn_record.config(state="disabled", bg="gray")
        self.btn_stop.config(state="normal", bg="blue")
        self.log("--- INITIALIZING HARDWARE ENCODER ---")
        
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.temp_video = os.path.join(DEFAULT_OUTPUT_DIR, f"qsv_vid_{timestamp}.mp4")
        self.temp_audio = os.path.join(DEFAULT_OUTPUT_DIR, f"qsv_aud_{timestamp}.wav")
        self.final_output = os.path.join(DEFAULT_OUTPUT_DIR, f"Recording_{timestamp}.mp4")
        
        self.start_time = time.time()
        
        threading.Thread(target=self._audio_thread, daemon=True).start()
        threading.Thread(target=self._video_thread, daemon=True).start()
        threading.Thread(target=self._timer_thread, daemon=True).start()

    def stop_recording(self):
        if not self.is_recording: return
        self.log("Stopping...")
        self.stop_event.set()

    def _timer_thread(self):
        while not self.stop_event.is_set():
            elapsed = int(time.time() - self.start_time)
            t_str = str(timedelta(seconds=elapsed))
            self.after(0, lambda: self.timer_lbl.config(text=t_str))
            time.sleep(0.5)

    def _audio_thread(self):
        try:
            dev_name = self.aud_box.get()
            dev_id = self.audio_devices.get(dev_name)
            
            mic = sc.default_microphone()
            if dev_id:
                for m in sc.all_microphones(include_loopback=True):
                    if m.id == dev_id: mic = m
            
            self.log(f"Audio Device: {mic.name}")
            
            with mic.recorder(samplerate=44100) as recorder:
                with sf.SoundFile(self.temp_audio, mode='w', samplerate=44100, channels=2) as file:
                    while not self.stop_event.is_set():
                        # Larger buffer for stability
                        data = recorder.record(numframes=2048) 
                        file.write(data)
        except Exception as e:
            self.log(f"AUDIO ERROR: {e}")

    def _video_thread(self):
        try:
            mon_idx = self.mon_box.current() + 1
            with mss.mss() as sct:
                mon = sct.monitors[mon_idx]
                width, height = mon["width"], mon["height"]
                if width % 2 != 0: width -= 1
                if height % 2 != 0: height -= 1
                self.log(f"Target Resolution: {width}x{height}")

            # --- HARDWARE ACCELERATED COMMAND ---
            cmd = [
                FFMPEG_BINARY,
                '-y',
                '-f', 'rawvideo',
                '-vcodec', 'rawvideo',
                '-s', f'{width}x{height}',
                '-pix_fmt', 'bgr24',    # Input from MSS
                '-r', str(TARGET_FPS),  # 30 FPS
                '-i', '-',              # Pipe Input
                '-vf', 'format=nv12',   # CONVERT TO NV12 FOR INTEL QSV
                '-c:v', 'h264_qsv',     # INTEL HARDWARE ENCODER
                '-global_quality', '25',# Quality Factor
                '-preset', 'veryfast',  # Speed factor
                self.temp_video
            ]
            
            process = subprocess.Popen(
                cmd, 
                stdin=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                creationflags=subprocess.CREATE_NO_WINDOW
            )

            # Log Reader
            def log_reader():
                for line in iter(process.stderr.readline, b''):
                    try:
                        msg = line.decode().strip()
                        if "speed=" in msg:
                            # Parse speed to check performance
                            parts = msg.split("speed=")
                            if len(parts) > 1:
                                spd = parts[1].split('x')[0]
                                # Log only if slow
                                try:
                                    if float(spd) < 0.9: 
                                        self.log(f"WARNING: System Lagging (Speed {spd}x)")
                                except: pass
                    except: pass
            threading.Thread(target=log_reader, daemon=True).start()

            # Capture Loop (Metronome)
            frame_duration = 1.0 / TARGET_FPS
            next_tick = time.time() + frame_duration
            
            with mss.mss() as sct:
                monitor_area = {"top": mon["top"], "left": mon["left"], "width": width, "height": height}
                last_frame = None
                
                while not self.stop_event.is_set():
                    # Capture
                    try:
                        img = sct.grab(monitor_area)
                        last_frame = np.frombuffer(img.rgb, dtype=np.uint8).tobytes()
                    except: pass

                    # Write (Duplicate frame if capture failed to keep time)
                    if last_frame:
                        try:
                            process.stdin.write(last_frame)
                        except: break

                    # Sleep
                    now = time.time()
                    sleep_time = next_tick - now
                    if sleep_time > 0: time.sleep(sleep_time)
                    next_tick += frame_duration

            # Close
            if process.stdin: process.stdin.close()
            process.wait()
            self.after(0, self.finalize)
            
        except Exception as e:
            self.log(f"VIDEO THREAD CRASH: {e}")

    def finalize(self):
        self.log("Muxing Audio/Video...")
        if not os.path.exists(self.temp_video):
            self.log("CRITICAL: Video file failed to save.")
            self.reset_ui()
            return

        cmd = [FFMPEG_BINARY, '-y', '-i', self.temp_video]
        if os.path.exists(self.temp_audio):
            cmd.extend(['-i', self.temp_audio])
        
        # 'aac' is safer than 'copy' for audio if sample rates differ
        cmd.extend(['-c:v', 'copy', '-c:a', 'aac', '-shortest', self.final_output])
        
        subprocess.run(cmd, creationflags=subprocess.CREATE_NO_WINDOW)
        
        try:
            os.remove(self.temp_video)
            os.remove(self.temp_audio)
        except: pass
        
        self.log(f"COMPLETED. Saved to: {self.final_output}")
        messagebox.showinfo("Done", f"Recording Saved:\n{self.final_output}")
        self.reset_ui()

    def reset_ui(self):
        self.is_recording = False
        self.btn_record.config(state="normal", bg="red")
        self.btn_stop.config(state="disabled", bg="gray")
        self.timer_lbl.config(text="00:00:00")

if __name__ == "__main__":
    if not os.path.exists(DEFAULT_OUTPUT_DIR): os.makedirs(DEFAULT_OUTPUT_DIR)
    app = QSVRecorderApp()
    app.mainloop()