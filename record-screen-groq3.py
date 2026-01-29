import tkinter as tk
from tkinter import ttk
import mss
import cv2
import numpy as np
import threading
import time
import os
from datetime import datetime
from pynput import keyboard

# Global variables
recording = False
stop_event = threading.Event()
frames = []
frame_times = []

# GUI setup
window = tk.Tk()
window.title("Screen Recorder")
window.geometry("300x200")
window.resizable(True, True)
window.configure(background='lightblue')  # Set background color

# Center the window
screen_width = window.winfo_screenwidth()
screen_height = window.winfo_screenheight()
x = (screen_width - 300) // 2
y = (screen_height - 200) // 2
window.geometry(f"300x200+{x}+{y}")

# Style for widgets
style = ttk.Style()
style.theme_use('clam')  # Use a modern theme
style.configure('TLabel', font=('Helvetica', 12, 'bold'), background='lightblue', foreground='darkblue')
style.configure('TButton', font=('Helvetica', 12), background='orange', foreground='white')

# Widgets
title_label = ttk.Label(window, text="Screen Recorder", style='TLabel')
title_label.pack(pady=10)

fps_label = ttk.Label(window, text="Desired FPS:", style='TLabel')
fps_label.pack(pady=(10, 0))
fps_entry = ttk.Entry(window, width=10)
fps_entry.insert(0, "30")
fps_entry.pack()

duration_label = ttk.Label(window, text="Duration (min, 0 for no limit):", style='TLabel')
duration_label.pack(pady=(10, 0))
duration_entry = ttk.Entry(window, width=10)
duration_entry.insert(0, "0")
duration_entry.pack()

start_button = ttk.Button(window, text="Start Recording", command=lambda: start_recording())
start_button.pack(pady=10)

status_label = ttk.Label(window, text="Status: Idle", style='TLabel')
status_label.pack(pady=(0, 10))

# Functions
def start_recording():
    global recording
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
    window.withdraw()  # Hide GUI
    status_label.config(text="Status: Recording")
    threading.Thread(target=record_screen, args=(fps, duration), daemon=True).start()

def stop_recording():
    global recording
    if not recording:
        return
    recording = False
    stop_event.set()
    save_video()
    window.deiconify()  # Show GUI
    status_label.config(text="Status: Idle")

def record_screen(target_fps, duration):
    global frames, frame_times
    frames = []
    frame_times = []
    start_time = time.time()
    with mss.mss() as sct:
        monitor = sct.monitors[1]  # Primary monitor
        while recording and not stop_event.is_set():
            screen = sct.grab(monitor)
            frame = np.array(screen)
            frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)  # Convert to BGR for OpenCV
            frames.append(frame)
            frame_times.append(time.time())
            time.sleep(1 / target_fps)
            if duration > 0 and (time.time() - start_time) >= duration * 60:
                stop_recording()
                break

def save_video():
    if not frames:
        return
    height, width, _ = frames[0].shape
    if len(frame_times) > 1:
        actual_duration = frame_times[-1] - frame_times[0]
        actual_fps = len(frames) / actual_duration
    else:
        actual_fps = float(fps_entry.get())
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    recordings_dir = "recordings"
    if not os.path.exists(recordings_dir):
        os.makedirs(recordings_dir)
    filename = os.path.join(recordings_dir, f"screen_recorder_{actual_fps:.2f}fps_{timestamp}.mp4")
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(filename, fourcc, actual_fps, (width, height))
    for frame in frames:
        out.write(frame)
    out.release()
    print(f"Video saved as {filename}")

# Keyboard listener for 'R' key
def on_press(key):
    if key == keyboard.KeyCode.from_char('r'):
        if recording:
            stop_recording()
        else:
            start_recording()

listener = keyboard.Listener(on_press=on_press)
listener.start()

# Start GUI
window.mainloop()