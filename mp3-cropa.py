import tkinter as tk
from tkinter import ttk
from tkinter import filedialog, messagebox
import os
import threading
import time # For playback status updates

# --- Audio Libraries ---
from pydub import AudioSegment
# Make sure simpleaudio is installed: pip install simpleaudio
try:
    import simpleaudio as sa
except ImportError:
    messagebox.showerror("Missing Library", "SimpleAudio library not found.\nPlease install it: pip install simpleaudio")
    exit() # Exit if playback library is missing

# --- Core Cropping Logic (Unchanged from previous GUI version) ---
def crop_mp3(input_path, output_path, start_seconds, end_seconds, status_callback):
    """
    Crops an MP3 file and provides status updates via callback.
    (Same logic as before, handles loading for cropping)
    """
    status_callback(f"Loading for Crop: {os.path.basename(input_path)}...")
    if not os.path.exists(input_path):
        status_callback(f"Error: Input file not found.")
        messagebox.showerror("Error", f"Input file not found:\n{input_path}")
        return False
    try:
        audio = AudioSegment.from_mp3(input_path)
        status_callback(f"Loaded. Duration: {len(audio) / 1000.0:.2f}s")
    except Exception as e:
        status_callback(f"Error loading MP3: {e}")
        messagebox.showerror("Error", f"Error loading MP3 file:\n{e}\n\nEnsure FFmpeg is installed and in PATH.")
        return False

    start_ms = int(start_seconds * 1000)
    end_ms = int(end_seconds * 1000)
    audio_duration_ms = len(audio)

    # Validation
    if start_ms < 0: start_ms = 0
    if end_ms > audio_duration_ms: end_ms = audio_duration_ms
    if start_ms >= end_ms:
        status_callback("Error: Start time must be less than end time.")
        messagebox.showerror("Error", "Start time must be less than end time (even after clamping to duration).")
        return False

    status_callback(f"Cropping from {start_ms/1000.0:.2f}s to {end_ms/1000.0:.2f}s...")
    try:
        cropped_audio = audio[start_ms:end_ms]
        status_callback(f"Exporting to: {os.path.basename(output_path)}...")
        cropped_audio.export(output_path, format="mp3")
        status_callback(f"Success! Saved cropped audio.")
        return True
    except Exception as e:
        status_callback(f"Error exporting: {e}")
        messagebox.showerror("Error", f"Error exporting cropped MP3 file:\n{e}\n\nCheck write permissions.")
        return False

# --- Tkinter GUI Application ---

class Mp3CropperApp:
    def __init__(self, master):
        self.master = master
        master.title("MP3 Cropper & Preview")
        master.geometry("600x320") # Increased size for playback controls

        # --- Audio State ---
        self.loaded_audio = None # To store the pydub AudioSegment
        self.play_obj = None     # To store the simpleaudio PlayObject
        self.playback_thread = None
        self.update_playback_status_job = None # To store the 'after' job ID

        # Style
        style = ttk.Style()
        try:
            # Try nicer themes first
            style.theme_use('vista') # Or 'clam', 'xpnative'
        except tk.TclError:
            style.theme_use('default') # Fallback

        # --- Variables ---
        self.input_file_path = tk.StringVar()
        self.output_file_path = tk.StringVar()
        self.start_time_str = tk.StringVar(value="0.0")
        self.end_time_str = tk.StringVar(value="10.0")
        self.status_text = tk.StringVar(value="Ready. Select input MP3 file.")
        self.playback_status_text = tk.StringVar(value="Playback: - / -")

        # --- GUI Layout ---
        main_frame = ttk.Frame(master, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        master.columnconfigure(0, weight=1)
        master.rowconfigure(0, weight=1)

        # == File Selection Section ==
        file_frame = ttk.LabelFrame(main_frame, text="Files", padding="10")
        file_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=5, pady=5)
        file_frame.columnconfigure(1, weight=1)

        ttk.Label(file_frame, text="Input MP3:").grid(row=0, column=0, sticky=tk.W, pady=2)
        ttk.Entry(file_frame, textvariable=self.input_file_path, width=50).grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5)
        self.browse_input_btn = ttk.Button(file_frame, text="Browse...", command=self.select_input_file)
        self.browse_input_btn.grid(row=0, column=2, sticky=tk.E)

        ttk.Label(file_frame, text="Output MP3:").grid(row=1, column=0, sticky=tk.W, pady=2)
        ttk.Entry(file_frame, textvariable=self.output_file_path, width=50).grid(row=1, column=1, sticky=(tk.W, tk.E), padx=5)
        self.browse_output_btn = ttk.Button(file_frame, text="Save As...", command=self.select_output_file)
        self.browse_output_btn.grid(row=1, column=2, sticky=tk.E)

        # == Preview Section ==
        preview_frame = ttk.LabelFrame(main_frame, text="Preview", padding="10")
        preview_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), padx=5, pady=5)
        preview_frame.columnconfigure(0, weight=1) # Make status label expand

        self.playback_status_label = ttk.Label(preview_frame, textvariable=self.playback_status_text)
        self.playback_status_label.grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 5))

        self.play_button = ttk.Button(preview_frame, text="▶ Play", command=self.play_audio, state=tk.DISABLED)
        self.play_button.grid(row=1, column=0, sticky=tk.W, padx=5)
        self.stop_button = ttk.Button(preview_frame, text="■ Stop", command=self.stop_audio, state=tk.DISABLED)
        self.stop_button.grid(row=1, column=1, sticky=tk.W)

        # == Cropping Section ==
        crop_frame = ttk.LabelFrame(main_frame, text="Crop Settings", padding="10")
        crop_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), padx=5, pady=5)

        ttk.Label(crop_frame, text="Start Time (s):").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.start_entry = ttk.Entry(crop_frame, textvariable=self.start_time_str, width=10)
        self.start_entry.grid(row=0, column=1, sticky=tk.W, padx=5)

        ttk.Label(crop_frame, text="End Time (s):").grid(row=0, column=2, sticky=tk.W, padx=(20, 5))
        self.end_entry = ttk.Entry(crop_frame, textvariable=self.end_time_str, width=10)
        self.end_entry.grid(row=0, column=3, sticky=tk.W, padx=5)

        self.crop_button = ttk.Button(crop_frame, text="Crop Audio", command=self.start_cropping_thread, state=tk.DISABLED)
        self.crop_button.grid(row=1, column=0, columnspan=4, pady=10)

        # == Status Bar ==
        status_bar = ttk.Label(main_frame, textvariable=self.status_text, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(5,0))

        # Set initial state for buttons that depend on file selection
        self.update_button_states()


    def update_status(self, message):
        """Safely update the main status bar."""
        self.master.after(0, self.status_text.set, message)

    def update_playback_status(self):
        """Updates the playback timer label."""
        if self.play_obj and self.play_obj.is_playing() and self.loaded_audio:
            # Note: simpleaudio doesn't easily give current playback position.
            # We can *estimate* but it's not perfect, especially with threads.
            # A more robust solution would involve more complex audio handling.
            # For now, we'll just indicate playing state.
            total_duration_s = len(self.loaded_audio) / 1000.0
            self.playback_status_text.set(f"Playback: Playing... / {total_duration_s:.1f}s")
            # Schedule next update
            self.update_playback_status_job = self.master.after(500, self.update_playback_status) # Update every 500ms
        elif self.loaded_audio:
             total_duration_s = len(self.loaded_audio) / 1000.0
             self.playback_status_text.set(f"Playback: Stopped / {total_duration_s:.1f}s")
        else:
             self.playback_status_text.set("Playback: - / -")


    def cancel_playback_status_update(self):
         """Cancels the scheduled playback status update."""
         if self.update_playback_status_job:
              self.master.after_cancel(self.update_playback_status_job)
              self.update_playback_status_job = None

    def update_button_states(self):
        """Enable/disable buttons based on current state."""
        file_loaded = bool(self.loaded_audio)
        is_playing = bool(self.play_obj and self.play_obj.is_playing())

        self.play_button.config(state=(tk.NORMAL if file_loaded and not is_playing else tk.DISABLED))
        self.stop_button.config(state=(tk.NORMAL if is_playing else tk.DISABLED))
        self.crop_button.config(state=(tk.NORMAL if file_loaded else tk.DISABLED))

    def set_ui_state_during_process(self, enabled):
        """Enable/disable UI elements during long processes (cropping)."""
        state = tk.NORMAL if enabled else tk.DISABLED
        widgets_to_toggle = [
            self.browse_input_btn, self.browse_output_btn,
            self.play_button, self.stop_button,
            self.start_entry, self.end_entry,
            self.crop_button
        ]
        for widget in widgets_to_toggle:
            # Check if widget still exists (might be destroyed during shutdown)
            try:
                 widget.config(state=state)
            except tk.TclError:
                 pass # Widget likely destroyed, ignore
        # Keep stop button enabled if playing, even during crop start
        if self.play_obj and self.play_obj.is_playing():
             self.stop_button.config(state=tk.NORMAL)


    def select_input_file(self):
        # Stop any current playback first
        self.stop_audio()
        self.loaded_audio = None # Clear previous audio

        filetypes = (("MP3 files", "*.mp3"), ("All files", "*.*"))
        filepath = filedialog.askopenfilename(title="Select Input MP3", filetypes=filetypes)
        if not filepath:
            return # User cancelled

        self.input_file_path.set(filepath)
        self.update_status(f"Loading '{os.path.basename(filepath)}' for preview...")

        # Load audio in a thread to prevent GUI freeze for large files
        load_thread = threading.Thread(target=self._load_audio_task, args=(filepath,), daemon=True)
        load_thread.start()

        # Suggest output filename
        if not self.output_file_path.get():
             base, ext = os.path.splitext(os.path.basename(filepath))
             suggested_output = os.path.join(os.path.dirname(filepath), f"{base}_cropped.mp3")
             self.output_file_path.set(suggested_output)

    def _load_audio_task(self, filepath):
        """Task run in thread to load audio."""
        try:
            audio = AudioSegment.from_mp3(filepath)
            self.loaded_audio = audio
            self.master.after(0, self.update_status, f"Preview loaded ({len(audio)/1000.0:.1f}s). Ready to Play/Crop.")
            # Update playback status label and button states on main thread
            self.master.after(0, self.update_playback_status)
            self.master.after(0, self.update_button_states)
        except Exception as e:
            self.loaded_audio = None
            self.master.after(0, self.update_status, f"Error loading preview: {e}")
            self.master.after(0, messagebox.showerror, "Load Error", f"Failed to load audio for preview:\n{e}\n\nEnsure FFmpeg is installed and the file is valid.")
            # Update button states on main thread
            self.master.after(0, self.update_playback_status)
            self.master.after(0, self.update_button_states)

    def select_output_file(self):
        filetypes = (("MP3 files", "*.mp3"), ("All files", "*.*"))
        initial_dir = os.path.dirname(self.input_file_path.get()) if self.input_file_path.get() else "."
        initial_file = os.path.basename(self.output_file_path.get()) if self.output_file_path.get() else "cropped_audio.mp3"

        filepath = filedialog.asksaveasfilename(
            title="Save Cropped MP3 As",
            initialdir=initial_dir,
            initialfile=initial_file,
            defaultextension=".mp3",
            filetypes=filetypes)
        if filepath:
            self.output_file_path.set(filepath)
            self.update_status(f"Output set to: {os.path.basename(filepath)}")

    def play_audio(self):
        if not self.loaded_audio:
            messagebox.showwarning("No Audio", "Please load an input file first.")
            return
        if self.play_obj and self.play_obj.is_playing():
            return # Already playing

        self.stop_audio() # Stop previous playback if any remnant exists

        try:
            self.update_status("Starting playback...")
            # Ensure audio data is in a format simpleaudio likes (bytes)
            audio_data = self.loaded_audio.raw_data
            num_channels = self.loaded_audio.channels
            bytes_per_sample = self.loaded_audio.sample_width
            sample_rate = self.loaded_audio.frame_rate

            # Start playback in a new thread
            # simpleaudio's play_buffer handles threading internally somewhat,
            # but starting it from our thread prevents potential GUI block on start.
            def playback_task():
                try:
                     self.play_obj = sa.play_buffer(audio_data, num_channels, bytes_per_sample, sample_rate)
                     # Start status updater on main thread *after* play_obj is assigned
                     self.master.after(0, self.update_playback_status)
                     self.master.after(0, self.update_button_states) # Update buttons once playing
                     self.play_obj.wait_done() # Wait for playback to finish in this thread
                except Exception as e:
                     self.master.after(0, messagebox.showerror, "Playback Error", f"Could not play audio:\n{e}")
                     self.play_obj = None # Clear play object on error
                finally:
                     # Playback finished or stopped, update UI on main thread
                     self.master.after(0, self.cancel_playback_status_update) # Stop updater
                     self.master.after(0, self.update_playback_status) # Set final status
                     self.master.after(0, self.update_button_states) # Re-enable play etc.


            self.playback_thread = threading.Thread(target=playback_task, daemon=True)
            self.playback_thread.start()
            # Immediately update button state (disable play, enable stop)
            self.update_button_states()

        except Exception as e:
            messagebox.showerror("Playback Error", f"Failed to prepare audio for playback:\n{e}")
            self.update_status("Playback failed.")
            self.play_obj = None
            self.update_button_states()


    def stop_audio(self):
        self.cancel_playback_status_update() # Stop the timer updates
        if self.play_obj and self.play_obj.is_playing():
            self.update_status("Stopping playback...")
            self.play_obj.stop()
            self.play_obj = None # Clear the object
            # Note: The playback thread might still be running until wait_done() finishes or errors.
            # simpleaudio handles the actual audio stream stop.
        # Update status and buttons after stopping attempt
        self.update_playback_status()
        self.update_button_states()

    def start_cropping_thread(self):
        """Starts the cropping process in a separate thread."""
        input_p = self.input_file_path.get()
        output_p = self.output_file_path.get()

        if not input_p or not output_p:
            messagebox.showerror("Error", "Please select both input and output files.")
            return
        if not self.loaded_audio: # Should technically be prevented by button state, but double check
             messagebox.showerror("Error", "Input audio not loaded correctly.")
             return

        try:
            start_t = float(self.start_time_str.get())
            end_t = float(self.end_time_str.get())
        except ValueError:
            messagebox.showerror("Error", "Invalid start or end time. Please enter numbers (e.g., 5.0).")
            return

        # Basic Validation
        if start_t < 0 or end_t < 0:
            messagebox.showerror("Error", "Start and End times cannot be negative.")
            return
        if start_t >= end_t:
             messagebox.showerror("Error", "Start time must be less than End time.")
             return
        # Check against loaded duration
        duration_s = len(self.loaded_audio) / 1000.0
        if start_t >= duration_s:
             messagebox.showerror("Error", f"Start time ({start_t}s) is beyond the audio duration ({duration_s:.1f}s).")
             return
        # end_t will be clamped within crop_mp3 if it exceeds duration

        # Disable UI, start processing in thread
        self.set_ui_state_during_process(False)
        self.update_status("Starting crop...")

        # Run crop_mp3 in a separate thread
        thread = threading.Thread(target=self.run_crop_task, args=(input_p, output_p, start_t, end_t), daemon=True)
        thread.start()


    def run_crop_task(self, input_p, output_p, start_t, end_t):
         """The actual task run by the thread."""
         try:
             success = crop_mp3(input_p, output_p, start_t, end_t, self.update_status)
             # Status/messages handled within crop_mp3 now
         except Exception as e:
             self.master.after(0, self.update_status, f"Unexpected Cropping Error: {e}")
             self.master.after(0, messagebox.showerror, "Unexpected Error", f"An unexpected error occurred during cropping:\n{e}")
         finally:
             # Re-enable the UI on main thread
             self.master.after(0, self.set_ui_state_during_process, True)


# --- Main Execution ---
if __name__ == "__main__":
    root = tk.Tk()
    app = Mp3CropperApp(root)
    # Ensure playback stops cleanly when window is closed
    def on_closing():
        app.stop_audio()
        root.destroy()
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()