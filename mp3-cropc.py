import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import threading
import time
import numpy as np

# --- Audio Libraries ---
from pydub import AudioSegment
try:
    import simpleaudio as sa
except ImportError:
    messagebox.showerror("Missing Library", "SimpleAudio library not found.\nPlease install it: pip install simpleaudio")
    exit()

# --- Plotting Libraries ---
try:
    import matplotlib.pyplot as plt
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    # plt.style.use('seaborn-v0_8-darkgrid') # Optional nice style
    plt.rcParams['axes.facecolor'] = '#F0F0F0' # Match default Tk background
    plt.rcParams['figure.facecolor'] = '#F0F0F0'
except ImportError:
     messagebox.showerror("Missing Library", "Matplotlib library not found.\nPlease install it: pip install matplotlib")
     exit()

# --- Core Cropping Logic (with Unique Filename Generation) ---
def get_unique_filename(output_path):
    """Checks if a file exists and returns a unique version if needed."""
    if not os.path.exists(output_path):
        return output_path

    directory, filename = os.path.split(output_path)
    base, ext = os.path.splitext(filename)
    counter = 1
    while True:
        new_filename = f"{base}_{counter}{ext}"
        new_path = os.path.join(directory, new_filename)
        if not os.path.exists(new_path):
            return new_path
        counter += 1

def crop_mp3(input_path, output_path, start_seconds, end_seconds, status_callback):
    """Crops MP3, ensuring unique output filename."""
    status_callback(f"Loading for Crop: {os.path.basename(input_path)}...")
    if not os.path.exists(input_path):
        status_callback(f"Error: Input file not found.")
        messagebox.showerror("Error", f"Input file not found:\n{input_path}")
        return False, None # Return None for actual_output_path

    try:
        audio = AudioSegment.from_mp3(input_path)
    except Exception as e:
        status_callback(f"Error loading MP3 for cropping: {e}")
        messagebox.showerror("Error", f"Error loading MP3 file:\n{e}")
        return False, None

    start_ms = int(start_seconds * 1000)
    end_ms = int(end_seconds * 1000)
    audio_duration_ms = len(audio)

    if start_ms < 0: start_ms = 0
    if end_ms > audio_duration_ms: end_ms = audio_duration_ms
    if start_ms >= end_ms:
        status_callback("Error: Start time must be less than end time.")
        messagebox.showerror("Error", "Start time must be less than end time.")
        return False, None

    # --- Unique Filename Check ---
    actual_output_path = get_unique_filename(output_path)
    if actual_output_path != output_path:
         status_callback(f"Note: Output file exists. Saving as {os.path.basename(actual_output_path)}")
         time.sleep(0.1) # Brief pause to let user see message
    # --- End Unique Filename Check ---

    status_callback(f"Cropping from {start_ms/1000.0:.2f}s to {end_ms/1000.0:.2f}s...")
    try:
        cropped_audio = audio[start_ms:end_ms]
        status_callback(f"Exporting to: {os.path.basename(actual_output_path)}...")
        cropped_audio.export(actual_output_path, format="mp3")
        # status_callback(f"Success! Saved: {os.path.basename(actual_output_path)}") # More specific success
        return True, actual_output_path # Return success and actual path used
    except Exception as e:
        status_callback(f"Error exporting: {e}")
        messagebox.showerror("Error", f"Error exporting cropped MP3 file:\n{e}")
        return False, None


# --- Tkinter GUI Application ---
class Mp3CropperApp:
    def __init__(self, master):
        self.master = master
        master.title("MP3 Visual Cropper")
        master.geometry("800x600")

        # --- Audio State ---
        self.loaded_audio = None
        self.play_obj = None
        self.playback_thread = None
        self.audio_duration_s = 0.0
        self.audio_samples = None
        self.audio_sample_rate = 0
        self.playback_lock = threading.Lock() # Lock for managing playback state

        # --- Plotting State ---
        self.fig = None
        self.ax = None
        self.canvas = None
        self.time_axis = None
        self.waveform_line = None
        self.selection_span = None

        # Style
        style = ttk.Style()
        try:
            style.theme_use('vista')
        except tk.TclError:
            style.theme_use('default')

        # --- Variables ---
        self.input_file_path = tk.StringVar()
        self.output_file_path = tk.StringVar()
        self.start_time_var = tk.DoubleVar(value=0.0)
        self.end_time_var = tk.DoubleVar(value=10.0)
        self.status_text = tk.StringVar(value="Ready. Select input MP3 file.")
        self.playback_status_text = tk.StringVar(value="Playback: - / -")
        self.start_slider_label_var = tk.StringVar(value="Start: 0.00s")
        self.end_slider_label_var = tk.StringVar(value="End: 10.00s")

        # --- GUI Layout (Same as before) ---
        main_frame = ttk.Frame(master, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        master.columnconfigure(0, weight=1)
        master.rowconfigure(0, weight=1)

        # == Top Row: File Selection ==
        file_frame = ttk.LabelFrame(main_frame, text="Files", padding="5")
        file_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), padx=5, pady=5)
        file_frame.columnconfigure(1, weight=1)
        ttk.Label(file_frame, text="Input MP3:").grid(row=0, column=0, sticky=tk.W, pady=2)
        ttk.Entry(file_frame, textvariable=self.input_file_path, width=60).grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5)
        self.browse_input_btn = ttk.Button(file_frame, text="Browse...", command=self.select_input_file)
        self.browse_input_btn.grid(row=0, column=2, sticky=tk.E, padx=5)
        ttk.Label(file_frame, text="Output MP3:").grid(row=1, column=0, sticky=tk.W, pady=2)
        ttk.Entry(file_frame, textvariable=self.output_file_path, width=60).grid(row=1, column=1, sticky=(tk.W, tk.E), padx=5)
        self.browse_output_btn = ttk.Button(file_frame, text="Save As...", command=self.select_output_file)
        self.browse_output_btn.grid(row=1, column=2, sticky=tk.E, padx=5)

        # == Middle Row: Waveform Plot ==
        plot_frame = ttk.Frame(main_frame)
        plot_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)
        main_frame.rowconfigure(1, weight=1)
        plot_frame.columnconfigure(0, weight=1)
        plot_frame.rowconfigure(0, weight=1)
        self.fig = Figure(figsize=(8, 2.5), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.ax.set_yticks([])
        self.ax.set_xlabel("Time (s)")
        self.fig.tight_layout(pad=0.5)
        self.canvas = FigureCanvasTkAgg(self.fig, master=plot_frame)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # == Control Row: Sliders & Playback ==
        control_frame = ttk.Frame(main_frame, padding="5")
        control_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), padx=5, pady=5)
        control_frame.columnconfigure(1, weight=1)
        control_frame.columnconfigure(3, weight=1)
        self.start_slider_label = ttk.Label(control_frame, textvariable=self.start_slider_label_var, width=12)
        self.start_slider_label.grid(row=0, column=0, sticky=tk.W, padx=5)
        self.start_slider = ttk.Scale(control_frame, from_=0, to=10, orient=tk.HORIZONTAL, variable=self.start_time_var, command=self._update_selection_from_sliders)
        self.start_slider.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5)
        self.end_slider_label = ttk.Label(control_frame, textvariable=self.end_slider_label_var, width=12)
        self.end_slider_label.grid(row=0, column=2, sticky=tk.W, padx=(15, 5))
        self.end_slider = ttk.Scale(control_frame, from_=0, to=10, orient=tk.HORIZONTAL, variable=self.end_time_var, command=self._update_selection_from_sliders)
        self.end_slider.grid(row=0, column=3, sticky=(tk.W, tk.E), padx=5)
        playback_button_frame = ttk.Frame(control_frame)
        playback_button_frame.grid(row=1, column=0, columnspan=4, pady=(5,0))
        self.play_button = ttk.Button(playback_button_frame, text="▶ Play All", command=self.play_audio, width=15)
        self.play_button.pack(side=tk.LEFT, padx=5)
        self.play_selection_button = ttk.Button(playback_button_frame, text="▶ Play Selection", command=self.play_selection, width=15)
        self.play_selection_button.pack(side=tk.LEFT, padx=5)
        self.stop_button = ttk.Button(playback_button_frame, text="■ Stop", command=self.stop_audio, width=10)
        self.stop_button.pack(side=tk.LEFT, padx=5)
        self.playback_status_label = ttk.Label(playback_button_frame, textvariable=self.playback_status_text)
        self.playback_status_label.pack(side=tk.LEFT, padx=(10, 0))

        # == Bottom Row: Crop Button & Status ==
        bottom_frame = ttk.Frame(main_frame, padding="5")
        bottom_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), padx=5, pady=5)
        bottom_frame.columnconfigure(0, weight=1)
        self.crop_button = ttk.Button(bottom_frame, text="Crop Selected Audio", command=self.start_cropping_thread)
        self.crop_button.pack(side=tk.LEFT, padx=5, pady=5)
        status_bar = ttk.Label(bottom_frame, textvariable=self.status_text, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=5)

        self.update_button_states()

    # --- GUI Update & Control Methods (Mostly unchanged) ---
    def update_status(self, message):
        # Use thread-safe update via 'after'
        if self.master.winfo_exists(): # Check if window still exists
            self.master.after(0, self.status_text.set, message)

    def update_playback_status(self, current_time=None, total_duration=None):
        if not self.master.winfo_exists(): return
        # (Logic same as before)
        if total_duration is None:
             total_duration = self.audio_duration_s
        with self.playback_lock: # Check playing state safely
             is_playing = bool(self.play_obj and self.play_obj.is_playing())

        if is_playing:
             status = f"Playback: Playing... / {total_duration:.1f}s"
        elif self.loaded_audio:
             status = f"Playback: Stopped / {total_duration:.1f}s"
        else:
             status = "Playback: - / -"
        self.master.after(0, self.playback_status_text.set, status)

    def update_button_states(self):
        if not self.master.winfo_exists(): return
        # Use thread-safe update via 'after'
        self.master.after(0, self._update_button_states_sync)

    def _update_button_states_sync(self):
        """Synchronous part of updating button states (called via 'after')"""
        if not self.master.winfo_exists(): return
        file_loaded = bool(self.loaded_audio)
        with self.playback_lock:
             is_playing = bool(self.play_obj and self.play_obj.is_playing())

        normal_if_loaded = tk.NORMAL if file_loaded else tk.DISABLED
        normal_if_playing = tk.NORMAL if is_playing else tk.DISABLED
        disabled_if_playing = tk.DISABLED if is_playing else tk.NORMAL
        normal_if_loaded_not_playing = tk.NORMAL if file_loaded and not is_playing else tk.DISABLED

        self.browse_output_btn.config(state=normal_if_loaded)
        self.crop_button.config(state=normal_if_loaded_not_playing)
        self.play_button.config(state=normal_if_loaded_not_playing)
        self.play_selection_button.config(state=normal_if_loaded_not_playing)
        self.stop_button.config(state=normal_if_playing)
        self.start_slider.config(state=normal_if_loaded_not_playing) # Disable sliders during play too
        self.end_slider.config(state=normal_if_loaded_not_playing)   # Disable sliders during play too

    def set_ui_state_during_process(self, enabled):
        """Enable/disable UI during cropping (called via 'after')"""
        if not self.master.winfo_exists(): return
        self.master.after(0, self._set_ui_state_during_process_sync, enabled)

    def _set_ui_state_during_process_sync(self, enabled):
        """Synchronous part of setting UI state"""
        if not self.master.winfo_exists(): return
        state = tk.NORMAL if enabled else tk.DISABLED

        # Keep stop button reflecting actual playing state
        with self.playback_lock:
            is_playing = bool(self.play_obj and self.play_obj.is_playing())
        stop_state = tk.NORMAL if is_playing else tk.DISABLED

        widgets_to_toggle = [
            self.browse_input_btn, self.browse_output_btn,
            self.play_button, self.play_selection_button,
            self.start_slider, self.end_slider,
            self.crop_button
        ]
        for widget in widgets_to_toggle:
            try: widget.config(state=state)
            except tk.TclError: pass
        try: self.stop_button.config(state=stop_state) # Handle stop separately
        except tk.TclError: pass

    # --- File Handling (Unchanged) ---
    def select_input_file(self):
        self.stop_audio()
        self.loaded_audio = None
        self.audio_samples = None
        self.clear_plot()
        filepath = filedialog.askopenfilename(title="Select Input MP3", filetypes=(("MP3 files", "*.mp3"), ("All files", "*.*")))
        if not filepath: return
        self.input_file_path.set(filepath)
        self.update_status(f"Loading '{os.path.basename(filepath)}'...")
        self.update_button_states()
        load_thread = threading.Thread(target=self._load_audio_task, args=(filepath,), daemon=True)
        load_thread.start()
        if not self.output_file_path.get():
             base = os.path.splitext(os.path.basename(filepath))[0]
             suggested = os.path.join(os.path.dirname(filepath), f"{base}_cropped.mp3")
             self.output_file_path.set(suggested)

    def _load_audio_task(self, filepath):
        # (Same as before)
        try:
            audio = AudioSegment.from_mp3(filepath)
            self.loaded_audio = audio
            self.audio_duration_s = len(audio) / 1000.0
            self.audio_sample_rate = audio.frame_rate
            samples_array = np.array(audio.get_array_of_samples())
            if audio.channels == 2: self.audio_samples = samples_array[::2]
            else: self.audio_samples = samples_array
            if self.master.winfo_exists(): self.master.after(0, self._update_gui_after_load)
        except Exception as e:
            self.loaded_audio = None
            self.audio_samples = None
            self.update_status(f"Error loading preview: {e}")
            if self.master.winfo_exists():
                self.master.after(0, messagebox.showerror, "Load Error", f"Failed to load audio for preview:\n{e}")
                self.master.after(0, self.update_button_states)

    def _update_gui_after_load(self):
        # (Same as before)
        if not self.loaded_audio or not self.master.winfo_exists(): return
        self.update_status(f"Preview loaded ({self.audio_duration_s:.1f}s). Ready.")
        self.update_playback_status()
        self.start_slider.config(to=self.audio_duration_s)
        self.end_slider.config(to=self.audio_duration_s)
        start_val = 0.0
        end_val = min(10.0, self.audio_duration_s)
        self.start_time_var.set(start_val)
        self.end_time_var.set(end_val)
        self.plot_waveform()
        self._update_selection_visuals()
        self.update_button_states()

    def select_output_file(self):
        # (Same as before)
        initial_dir = os.path.dirname(self.input_file_path.get()) if self.input_file_path.get() else "."
        initial_file = os.path.basename(self.output_file_path.get()) if self.output_file_path.get() else "cropped_audio.mp3"
        filepath = filedialog.asksaveasfilename(
            title="Save Cropped MP3 As", initialdir=initial_dir, initialfile=initial_file,
            defaultextension=".mp3", filetypes=(("MP3 files", "*.mp3"), ("All files", "*.*")))
        if filepath: self.output_file_path.set(filepath); self.update_status(f"Output set to: {os.path.basename(filepath)}")

    # --- Plotting Methods (Unchanged) ---
    def plot_waveform(self):
        # (Same as before)
        if self.audio_samples is None or self.ax is None: return
        self.clear_plot()
        num_samples = len(self.audio_samples)
        self.time_axis = np.linspace(0, self.audio_duration_s, num=num_samples)
        target_points = 2000
        if num_samples > target_points: step = num_samples // target_points; plot_samples = self.audio_samples[::step]; plot_time = self.time_axis[::step]
        else: plot_samples = self.audio_samples; plot_time = self.time_axis
        self.waveform_line, = self.ax.plot(plot_time, plot_samples, linewidth=0.5, color="#336699")
        self.ax.set_xlim(0, self.audio_duration_s)
        max_abs_sample = np.max(np.abs(plot_samples)) if len(plot_samples) > 0 else 1
        self.ax.set_ylim(-max_abs_sample * 1.1, max_abs_sample * 1.1)
        self.ax.set_xlabel("Time (s)")
        if self.canvas: self.canvas.draw_idle()

    def clear_plot(self):
        # (Same as before)
        if self.ax:
            if self.waveform_line: self.waveform_line.remove(); self.waveform_line = None
            if self.selection_span: self.selection_span.remove(); self.selection_span = None
            self.ax.set_xlim(0, 10); self.ax.set_ylim(-1, 1)
            if self.canvas: self.canvas.draw_idle()

    def _update_selection_from_sliders(self, event=None):
        # (Same as before, maybe slightly improved cross-over logic)
        start_t = self.start_time_var.get()
        end_t = self.end_time_var.get()
        if start_t > end_t:
            # If start > end, assume the slider *causing* the violation was the one moved last.
            # A simple heuristic: Assume start slider moved, so clamp end = start
             self.end_time_var.set(start_t)
             end_t = start_t
            # Or vice versa if you prefer pulling start back
        self.start_slider_label_var.set(f"Start: {start_t:.2f}s")
        self.end_slider_label_var.set(f"End: {end_t:.2f}s")
        self._update_selection_visuals(start_t, end_t)

    def _update_selection_visuals(self, start_t=None, end_t=None):
        # (Same as before)
        if self.ax is None or not self.master.winfo_exists(): return
        if start_t is None: start_t = self.start_time_var.get()
        if end_t is None: end_t = self.end_time_var.get()
        if self.selection_span: self.selection_span.remove(); self.selection_span = None
        if end_t > start_t and self.loaded_audio: self.selection_span = self.ax.axvspan(start_t, end_t, alpha=0.3, color='red', zorder=-1)
        if self.canvas: self.canvas.draw_idle()

    # --- Playback Methods (Improved Stability) ---

    def _play_segment(self, segment):
        """Handles playback with better locking and cleanup."""
        # Acquire lock to prevent concurrent playback attempts
        if not self.playback_lock.acquire(blocking=False):
             self.update_status("Playback already in progress or starting.")
             return # Don't start if already playing/starting

        # Ensure previous playback is fully stopped
        if self.play_obj:
             try:
                  if self.play_obj.is_playing():
                       self.play_obj.stop()
                  self.play_obj = None # Clear reference
             except Exception as e:
                  print(f"Minor error stopping previous playback: {e}") # Log minor error
                  self.play_obj = None
             time.sleep(0.05) # Small delay to let resources release

        if not segment:
             self.playback_lock.release()
             return

        self.update_status("Starting playback...")
        total_duration = len(segment) / 1000.0
        self.update_playback_status(None, total_duration) # Update status immediately
        self.update_button_states() # Update buttons immediately

        try:
            audio_data = segment.raw_data
            num_channels = segment.channels
            bytes_per_sample = segment.sample_width
            sample_rate = segment.frame_rate

            def playback_task():
                play_object_local = None # Use local variable in thread
                try:
                     play_object_local = sa.play_buffer(audio_data, num_channels, bytes_per_sample, sample_rate)
                     # Safely assign to self.play_obj *after* creation, still holding lock
                     with self.playback_lock:
                          self.play_obj = play_object_local

                     play_object_local.wait_done() # Wait for finish IN THIS THREAD

                except Exception as e:
                     # Ensure lock is released even on error during playback start/wait
                     if self.playback_lock.locked():
                         self.playback_lock.release()
                     self.update_status(f"Playback Error: {e}")
                     # Use master.after for messagebox from thread
                     if self.master.winfo_exists(): self.master.after(0, messagebox.showerror, "Playback Error", f"Could not play audio:\n{e}")
                finally:
                    # Clean up play_obj and release lock AFTER wait_done or error
                    with self.playback_lock:
                         # Check if self.play_obj is the one created by this thread
                         if self.play_obj == play_object_local:
                              self.play_obj = None
                         # Always release lock if held by this thread
                         if self.playback_lock.locked(): # Check if lock still held
                             self.playback_lock.release()

                    # Update GUI after task completion
                    self.update_playback_status()
                    self.update_button_states()

            # Keep reference to the thread if needed, but not strictly necessary now
            self.playback_thread = threading.Thread(target=playback_task, daemon=True)
            self.playback_thread.start()

        except Exception as e:
            # Error preparing audio data before thread start
            self.update_status(f"Playback Prep Error: {e}")
            messagebox.showerror("Playback Error", f"Failed to prepare audio for playback:\n{e}")
            self.playback_lock.release() # Release lock if preparation failed
            self.update_button_states()

    def play_audio(self):
        if not self.loaded_audio: messagebox.showwarning("No Audio", "Please load an input file first."); return
        self._play_segment(self.loaded_audio)

    def play_selection(self):
        if not self.loaded_audio: messagebox.showwarning("No Audio", "Please load an input file first."); return
        start_t = self.start_time_var.get(); end_t = self.end_time_var.get()
        if start_t >= end_t: messagebox.showwarning("Invalid Selection", "Start time must be less than end time."); return
        start_ms = int(start_t * 1000); end_ms = int(end_t * 1000)
        try:
            selected_segment = self.loaded_audio[start_ms:end_ms]
            self._play_segment(selected_segment)
        except Exception as e: messagebox.showerror("Playback Error", f"Could not prepare selected audio segment:\n{e}")

    def stop_audio(self):
        """Stops currently playing audio."""
        with self.playback_lock: # Acquire lock to safely modify play_obj
             if self.play_obj and self.play_obj.is_playing():
                  self.update_status("Stopping playback...")
                  try:
                      self.play_obj.stop()
                  except Exception as e:
                      print(f"Minor error during stop: {e}") # Log error but continue cleanup
                  self.play_obj = None # Clear reference
             else:
                  # If not playing but play_obj exists somehow, clear it
                  self.play_obj = None

        # Update GUI immediately after attempting stop
        self.update_playback_status()
        self.update_button_states()


    # --- Cropping Methods (Updated to handle new crop_mp3 return) ---

    def start_cropping_thread(self):
        input_p = self.input_file_path.get()
        output_p = self.output_file_path.get()

        if not input_p or not output_p: messagebox.showerror("Error", "Please select both input and output files."); return
        if not self.loaded_audio: messagebox.showerror("Error", "Input audio not loaded correctly."); return

        start_t = self.start_time_var.get(); end_t = self.end_time_var.get()
        if start_t < 0 or end_t < 0: messagebox.showerror("Error", "Start and End times cannot be negative."); return
        if start_t >= end_t: messagebox.showerror("Error", "Start time must be less than End time."); return

        self.set_ui_state_during_process(False) # Disable UI
        self.update_status("Starting crop...")
        thread = threading.Thread(target=self.run_crop_task, args=(input_p, output_p, start_t, end_t), daemon=True)
        thread.start()

    def run_crop_task(self, input_p, output_p, start_t, end_t):
         """The actual task run by the thread."""
         actual_output_path = None # Define before try block
         try:
             success, actual_output_path = crop_mp3(input_p, output_p, start_t, end_t, self.update_status)
             if success and actual_output_path:
                  self.update_status(f"Success! Saved: {os.path.basename(actual_output_path)}")
             # If success is False, crop_mp3 already showed message and updated status
         except Exception as e:
             self.update_status(f"Unexpected Cropping Error: {e}")
             if self.master.winfo_exists(): self.master.after(0, messagebox.showerror, "Unexpected Error", f"An unexpected error occurred during cropping:\n{e}")
         finally:
             # Re-enable the UI on main thread
             self.set_ui_state_during_process(True)
             # self.update_button_states() # set_ui_state should handle this


# --- Main Execution ---
if __name__ == "__main__":
    try: from ctypes import windll; windll.shcore.SetProcessDpiAwareness(1)
    except Exception: pass

    root = tk.Tk()
    app = Mp3CropperApp(root)

    def on_closing():
        print("Closing application...")
        app.stop_audio() # Ensure playback stops cleanly
        # Add a tiny delay to allow stop command to process before destroying window
        # This might help prevent rare crashes on close if audio was playing
        root.after(100, root.destroy)

    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()