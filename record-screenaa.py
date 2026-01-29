import cv2
import numpy as np
import pyautogui
from pynput import keyboard
from threading import Thread, Event
import time
from datetime import datetime
from playsound import playsound  # Install via: pip install playsound

# Path to your sound file (adjust if needed)
SOUND_FILE = r"C:\- AAII TOOLS -\firework-whistle-190306.mp3"

def play_sound_async(filepath):
    """Play the sound file in a separate thread."""
    Thread(target=lambda: playsound(filepath), daemon=True).start()

class ScreenRecorder:
    def __init__(self, target_fps=30):
        self.recording = False
        self.frames = []
        self.frame_times = []
        self.target_fps = target_fps
        self.stop_event = Event()
        self.duration = None  # Duration in minutes; None means unlimited

    def start_recording(self):
        """Start capturing screenshots at the specified FPS."""
        if self.recording:  # Prevent starting multiple recordings
            return
        self.recording = True
        self.frames = []
        self.frame_times = []
        self.stop_event.clear()
        # Play start sound
        play_sound_async(SOUND_FILE)
        Thread(target=self._record, daemon=True).start()
        print("Recording started...")

    def stop_recording(self):
        """Stop recording and save the video file."""
        if not self.recording:  # Prevent stopping when not recording
            return
        self.recording = False
        self.stop_event.set()
        self._save_video()
        # Play stop sound
        play_sound_async(SOUND_FILE)
        print("Recording stopped and saved!")

    def _record(self):
        start_time = time.time()
        frame_interval = 1 / self.target_fps
        last_capture = time.time()

        while self.recording and not self.stop_event.is_set():
            current_time = time.time()
            if current_time - last_capture >= frame_interval:
                try:
                    screen = pyautogui.screenshot()
                    frame = np.array(screen)
                    # Convert from BGR (pyautogui) to RGB (cv2)
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    self.frames.append(frame)
                    self.frame_times.append(current_time)
                    last_capture = current_time
                except Exception as e:
                    print(f"Error capturing screenshot: {e}")
                    self.stop_recording()  # Stop recording if error
                    return
            else:
                time.sleep(max(0, frame_interval - (current_time - last_capture)))

            # Stop recording automatically if a duration is set
            if self.duration and (time.time() - start_time) >= self.duration * 60:
                self.stop_recording()
                break

    def _save_video(self):
        if not self.frames:
            print("No frames captured!")
            return

        height, width, _ = self.frames[0].shape

        # Estimate actual FPS based on timestamps
        if len(self.frame_times) > 1:
            actual_duration = self.frame_times[-1] - self.frame_times[0]
            actual_fps = len(self.frames) / actual_duration
        else:
            actual_fps = self.target_fps

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"screen_recorder_{self.target_fps}fps_{timestamp}.mp4"

        try:
            # Use H.264 encoding
            fourcc = cv2.VideoWriter_fourcc(*'avc1')
            out = cv2.VideoWriter(filename, fourcc, actual_fps, (width, height))
            for frame in self.frames:
                out.write(frame)
            out.release()
            print(f"Video saved as {filename} (Actual FPS: {actual_fps:.2f})")
        except Exception as e:
            print(f"Error saving video: {e}")

def on_press(key):
    """Toggle recording on spacebar press."""
    global recorder
    if key == keyboard.Key.space:
        if recorder.recording:
            recorder.stop_recording()
        else:
            recorder.start_recording()

def main():
    global recorder
    try:
        fps = int(input("Enter Desired FPS: "))
        duration = int(input("Enter Recording Duration (minutes, 0 for no limit): "))

        if fps <= 0:
            raise ValueError("FPS must be a positive integer.")
        if duration < 0:
            raise ValueError("Duration cannot be negative.")

        recorder = ScreenRecorder(fps)
        # Set duration to None if 0 is entered
        recorder.duration = duration if duration > 0 else None

        print("Press the spacebar to start/stop recording.")
        with keyboard.Listener(on_press=on_press) as listener:
            listener.join()
    except ValueError as e:
        print(f"Invalid input: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    main()
