import tkinter as tk
from tkinter import ttk, filedialog
import mss
import cv2
import numpy as np
import threading
import time
import os
from datetime import datetime
from pynput import keyboard
from playsound import playsound

# ===== CONFIGURATION =====
SOUND_FILE = r"C:\\- AAII TOOLS -\\firework-whistle-190306.mp3"  # Update this path as needed
OUTPUT_DIR = "recordings"
PRESETS = {
    "High Quality (60fps)": (60, 0),
    "Medium Quality (30fps)": (30, 5),
    "Low Quality (15fps)": (15, 1)
}

# ===== GLOBAL STATE =====
recording = False
paused = False
stop_event = threading.Event()
pause_event = threading.Event()
frames = []
frame_times = []

# ===== GUI SETUP =====
window = tk.Tk()
window.title("🎬 FrankenRecorder 3000 PRO")
window.geometry("480x400")
window.configure(background='lavender')
window.resizable(False, False)

style = ttk.Style()
style.theme_use('clam')
style.configure('TLabel', font=('Helvetica', 11, 'bold'), background='lavender', foreground='darkmagenta')
style.configure('TButton', font=('Helvetica', 10), background='mediumvioletred', foreground='white')
style.configure('TCombobox', font=('Helvetica', 10))

# ===== WIDGETS =====
title_label = ttk.Label(window, text="FrankenRecorder 3000 PRO", style='TLabel')
title_label.pack(pady=10)

fps_label = ttk.Label(window, text="FPS:", style='TLabel')
fps_label.pack()
fps_entry = ttk.Entry(window, width=10)
fps_entry.insert(0, "30")
fps_entry.pack()

duration_label = ttk.Label(window, text="Duration (minutes, 0 for unlimited):", style='TLabel')
duration_label.pack(pady=(10, 0))
duration_entry = ttk.Entry(window, width=10)
duration_entry.insert(0, "0")
duration_entry.pack()

preset_label = ttk.Label(window, text="Choose a Preset:", style='TLabel')
preset_label.pack(pady=(10, 0))
preset_box = ttk.Combobox(window, values=list(PRESETS.keys()))
preset_box.set("Select Preset")
preset_box.pack()

start_btn = ttk.Button(window, text="Start Recording", command=lambda: start_recording())
start_btn.pack(pady=5)
pause_btn = ttk.Button(window, text="Pause / Resume", command=lambda: toggle_pause())
pause_btn.pack(pady=5)
stop_btn = ttk.Button(window, text="Stop Recording", command=lambda: stop_recording())
stop_btn.pack(pady=5)

output_btn = ttk.Button(window, text="Select Output Folder", command=lambda: select_output_dir())
output_btn.pack(pady=5)

status_label = ttk.Label(window, text="Status: Idle", style='TLabel')
status_label.pack(pady=(10, 0))

# ===== SOUND HELPER =====
def play_sound():
    try:
        threading.Thread(target=lambda: playsound(SOUND_FILE), daemon=True).start()
    except Exception as e:
        print(f"Sound error: {e}")

# ===== PRESET HANDLER =====
def apply_preset(event):
    preset = preset_box.get()
    if preset in PRESETS:
        fps, duration = PRESETS[preset]
        fps_entry.delete(0, tk.END)
        fps_entry.insert(0, str(fps))
        duration_entry.delete(0, tk.END)
        duration_entry.insert(0, str(duration))

preset_box.bind("<<ComboboxSelected>>", apply_preset)

# ===== OUTPUT DIR SELECTION =====
def select_output_dir():
    global OUTPUT_DIR
    directory = filedialog.askdirectory()
    if directory:
        OUTPUT_DIR = directory

# ===== RECORDING CONTROL =====
def start_recording():
    global recording, paused, frames, frame_times
    if recording:
        return
    try:
        fps = float(fps_entry.get())
        duration = float(duration_entry.get())
        if fps <= 0 or duration < 0:
            raise ValueError
    except ValueError:
        status_label.config(text="Invalid input")
        return

    recording = True
    paused = False
    stop_event.clear()
    pause_event.clear()
    frames = []
    frame_times = []

    play_sound()
    status_label.config(text="Status: Recording")
    window.withdraw()
    threading.Thread(target=record_screen, args=(fps, duration), daemon=True).start()

def toggle_pause():
    global paused
    if not recording:
        return
    paused = not paused
    if paused:
        pause_event.set()
        status_label.config(text="Status: Paused")
    else:
        pause_event.clear()
        status_label.config(text="Status: Recording")


def stop_recording():
    global recording
    if not recording:
        return
    recording = False
    stop_event.set()
    pause_event.clear()
    play_sound()
    save_video()
    window.deiconify()
    status_label.config(text="Status: Idle")

# ===== SCREEN CAPTURE LOOP =====
def record_screen(fps, duration):
    with mss.mss() as sct:
        monitor = sct.monitors[1]  # Primary monitor
        start_time = time.time()
        while recording and not stop_event.is_set():
            if pause_event.is_set():
                time.sleep(0.1)
                continue
            img = sct.grab(monitor)
            frame = np.array(img)
            frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
            frames.append(frame)
            frame_times.append(time.time())
            time.sleep(1 / fps)
            if duration > 0 and (time.time() - start_time) >= duration * 60:
                stop_recording()
                break

# ===== SAVE VIDEO =====
def save_video():
    if not frames:
        print("No frames to save.")
        return

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    height, width, _ = frames[0].shape
    if len(frame_times) > 1:
        actual_duration = frame_times[-1] - frame_times[0]
        actual_fps = len(frames) / actual_duration
    else:
        actual_fps = float(fps_entry.get())

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(OUTPUT_DIR, f"screen_record_{actual_fps:.2f}fps_{timestamp}.mp4")

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(filename, fourcc, actual_fps, (width, height))
    for frame in frames:
        out.write(frame)
    out.release()
    print(f"Video saved to {filename}")

# ===== KEYBOARD SHORTCUTS =====
def on_press(key):
    try:
        if key.char == 'r':
            if recording:
                stop_recording()
            else:
                start_recording()
        elif key.char == 'p':
            toggle_pause()
    except AttributeError:
        pass

keyboard.Listener(on_press=on_press).start()

# ===== START GUI =====
window.mainloop()
