import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import threading
import time
import numpy as np # For numerical operations (waveform data)

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
except ImportError:
     messagebox.showerror("Missing Library", "Matplotlib library not found.\nPlease install it: pip install matplotlib")
     exit()

# --- Core Cropping Logic (Unchanged) ---
def crop_mp3(input_path, output_path, start_seconds, end_seconds, status_callback):
    # (Same function as before - handles the actual file cropping)
    status_callback(f"Loading for Crop: {os.path.basename(input_path)}...")
    if not os.path.exists(input_path):
        status_callback(f"Error: Input file not found.")
        messagebox.showerror("Error", f"Input file not found:\n{input_path}")
        return False
    try:
        audio = AudioSegment.from_mp3(input_path)
        # Don't update status here, _load_audio_task does preview loading status
    except Exception as e:
        status_callback(f"Error loading MP3 for cropping: {e}")
        messagebox.showerror("Error", f"Error loading MP3 file:\n{e}\n\nEnsure FFmpeg is installed and in PATH.")
        return False

    start_ms = int(start_seconds * 1000)
    end_ms = int(end_seconds * 1000)
    audio_duration_ms = len(audio)

    if start_ms < 0: start_ms = 0
    if end_ms > audio_duration_ms: end_ms = audio_duration_ms
    if start_ms >= end_ms:
        # This case should ideally be prevented by slider logic, but double-check
        status_callback("Error: Start time must be less than end time.")
        messagebox.showerror("Error", "Start time must be less than end time.")
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
        master.title("MP3 Visual Cropper")
        master.geometry("800x600") # Need more space for plot

        # --- Audio State ---
        self.loaded_audio = None
        self.play_obj = None
        self.playback_thread = None
        self.audio_duration_s = 0.0
        self.audio_samples = None
        self.audio_sample_rate = 0

        # --- Plotting State ---
        self.fig = None
        self.ax = None
        self.canvas = None
        self.time_axis = None
        self.waveform_line = None
        self.selection_span = None # To store the axvspan object

        # Style
        style = ttk.Style()
        try:
            style.theme_use('vista')
        except tk.TclError:
            style.theme_use('default')

        # --- Variables ---
        self.input_file_path = tk.StringVar()
        self.output_file_path = tk.StringVar()
        # Use DoubleVar for sliders
        self.start_time_var = tk.DoubleVar(value=0.0)
        self.end_time_var = tk.DoubleVar(value=10.0) # Default end
        self.status_text = tk.StringVar(value="Ready. Select input MP3 file.")
        self.playback_status_text = tk.StringVar(value="Playback: - / -")
        self.start_slider_label_var = tk.StringVar(value="Start: 0.00s")
        self.end_slider_label_var = tk.StringVar(value="End: 10.00s")


        # --- GUI Layout ---
        main_frame = ttk.Frame(master, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        master.columnconfigure(0, weight=1)
        master.rowconfigure(0, weight=1) # Allow main frame to expand

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
        plot_frame = ttk.Frame(main_frame) # No label frame needed
        plot_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)
        main_frame.rowconfigure(1, weight=1) # Allow plot frame to expand vertically
        plot_frame.columnconfigure(0, weight=1)
        plot_frame.rowconfigure(0, weight=1)

        # Setup Matplotlib Figure and Canvas
        self.fig = Figure(figsize=(8, 2.5), dpi=100) # Adjust figsize/dpi as needed
        self.ax = self.fig.add_subplot(111)
        self.ax.set_yticks([]) # Hide Y axis ticks
        self.ax.set_xlabel("Time (s)")
        self.fig.tight_layout(pad=0.5) # Adjust padding

        self.canvas = FigureCanvasTkAgg(self.fig, master=plot_frame)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # == Control Row: Sliders & Playback ==
        control_frame = ttk.Frame(main_frame, padding="5")
        control_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), padx=5, pady=5)
        control_frame.columnconfigure(1, weight=1) # Allow sliders to expand
        control_frame.columnconfigure(3, weight=1)

        # Sliders
        self.start_slider_label = ttk.Label(control_frame, textvariable=self.start_slider_label_var, width=12)
        self.start_slider_label.grid(row=0, column=0, sticky=tk.W, padx=5)
        self.start_slider = ttk.Scale(control_frame, from_=0, to=10, orient=tk.HORIZONTAL,
                                      variable=self.start_time_var, command=self._update_selection_from_sliders)
        self.start_slider.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5)

        self.end_slider_label = ttk.Label(control_frame, textvariable=self.end_slider_label_var, width=12)
        self.end_slider_label.grid(row=0, column=2, sticky=tk.W, padx=(15, 5))
        self.end_slider = ttk.Scale(control_frame, from_=0, to=10, orient=tk.HORIZONTAL,
                                     variable=self.end_time_var, command=self._update_selection_from_sliders)
        self.end_slider.grid(row=0, column=3, sticky=(tk.W, tk.E), padx=5)

        # Playback Buttons
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
        bottom_frame.columnconfigure(0, weight=1) # Allow status bar to expand

        self.crop_button = ttk.Button(bottom_frame, text="Crop Selected Audio", command=self.start_cropping_thread)
        self.crop_button.pack(side=tk.LEFT, padx=5, pady=5)

        status_bar = ttk.Label(bottom_frame, textvariable=self.status_text, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=5)

        self.update_button_states() # Set initial state

    # --- GUI Update & Control Methods ---

    def update_status(self, message):
        self.master.after(0, self.status_text.set, message)

    def update_playback_status(self, current_time=None, total_duration=None):
         """Updates playback status. total_duration expected if known."""
         if total_duration is None:
              total_duration = self.audio_duration_s

         if self.play_obj and self.play_obj.is_playing():
             # SimpleAudio doesn't give easy current time, so we estimate or just show playing
             status = f"Playback: Playing... / {total_duration:.1f}s"
         elif self.loaded_audio:
             status = f"Playback: Stopped / {total_duration:.1f}s"
         else:
             status = "Playback: - / -"
         self.playback_status_text.set(status)


    def update_button_states(self):
        """Enable/disable buttons based on current state."""
        file_loaded = bool(self.loaded_audio)
        is_playing = bool(self.play_obj and self.play_obj.is_playing())

        # General Buttons
        self.browse_output_btn.config(state=(tk.NORMAL if file_loaded else tk.DISABLED))
        self.crop_button.config(state=(tk.NORMAL if file_loaded and not is_playing else tk.DISABLED))

        # Playback Buttons
        self.play_button.config(state=(tk.NORMAL if file_loaded and not is_playing else tk.DISABLED))
        self.play_selection_button.config(state=(tk.NORMAL if file_loaded and not is_playing else tk.DISABLED))
        self.stop_button.config(state=(tk.NORMAL if is_playing else tk.DISABLED))

        # Sliders
        self.start_slider.config(state=(tk.NORMAL if file_loaded else tk.DISABLED))
        self.end_slider.config(state=(tk.NORMAL if file_loaded else tk.DISABLED))


    def set_ui_state_during_process(self, enabled):
        """Enable/disable UI elements during long processes (cropping)."""
        state = tk.NORMAL if enabled else tk.DISABLED
        widgets_to_toggle = [
            self.browse_input_btn, self.browse_output_btn,
            self.play_button, self.play_selection_button, # Stop is handled separately
            self.start_slider, self.end_slider,
            self.crop_button
        ]
        # Keep stop button enabled if playing
        self.stop_button.config(state=(tk.NORMAL if self.play_obj and self.play_obj.is_playing() else tk.DISABLED))

        for widget in widgets_to_toggle:
            try:
                 widget.config(state=state)
            except tk.TclError:
                 pass # Widget might be destroyed

    # --- File Handling ---

    def select_input_file(self):
        self.stop_audio() # Stop playback
        self.loaded_audio = None
        self.audio_samples = None
        self.clear_plot() # Clear waveform

        filepath = filedialog.askopenfilename(title="Select Input MP3", filetypes=(("MP3 files", "*.mp3"), ("All files", "*.*")))
        if not filepath: return

        self.input_file_path.set(filepath)
        self.update_status(f"Loading '{os.path.basename(filepath)}'...")
        self.update_button_states() # Disable buttons during load

        # Load audio in thread
        load_thread = threading.Thread(target=self._load_audio_task, args=(filepath,), daemon=True)
        load_thread.start()

        # Suggest output
        if not self.output_file_path.get():
             base = os.path.splitext(os.path.basename(filepath))[0]
             suggested = os.path.join(os.path.dirname(filepath), f"{base}_cropped.mp3")
             self.output_file_path.set(suggested)

    def _load_audio_task(self, filepath):
        try:
            audio = AudioSegment.from_mp3(filepath)
            self.loaded_audio = audio
            self.audio_duration_s = len(audio) / 1000.0
            self.audio_sample_rate = audio.frame_rate

            # Get samples for plotting (convert to numpy array)
            # For stereo, just use the first channel for visualization simplicity
            samples_array = np.array(audio.get_array_of_samples())
            if audio.channels == 2:
                self.audio_samples = samples_array[::2] # Take every other sample (left channel)
            else:
                self.audio_samples = samples_array

            # Schedule GUI updates on the main thread
            self.master.after(0, self._update_gui_after_load)

        except Exception as e:
            self.loaded_audio = None
            self.audio_samples = None
            self.master.after(0, self.update_status, f"Error loading preview: {e}")
            self.master.after(0, messagebox.showerror, "Load Error", f"Failed to load audio for preview:\n{e}")
            self.master.after(0, self.update_button_states) # Re-enable browse maybe

    def _update_gui_after_load(self):
        """Updates GUI elements that depend on loaded audio (called from main thread)."""
        if not self.loaded_audio: return

        self.update_status(f"Preview loaded ({self.audio_duration_s:.1f}s). Ready.")
        self.update_playback_status()

        # Configure sliders
        self.start_slider.config(to=self.audio_duration_s)
        self.end_slider.config(to=self.audio_duration_s)
        # Reset sliders to default (or keep previous relative position if desired)
        start_val = 0.0
        end_val = min(10.0, self.audio_duration_s) # Default 10s or full duration
        self.start_time_var.set(start_val)
        self.end_time_var.set(end_val)

        # Plot waveform
        self.plot_waveform()

        # Update selection visuals and button states
        self._update_selection_visuals()
        self.update_button_states()


    def select_output_file(self):
        # (Same as before)
        initial_dir = os.path.dirname(self.input_file_path.get()) if self.input_file_path.get() else "."
        initial_file = os.path.basename(self.output_file_path.get()) if self.output_file_path.get() else "cropped_audio.mp3"
        filepath = filedialog.asksaveasfilename(
            title="Save Cropped MP3 As", initialdir=initial_dir, initialfile=initial_file,
            defaultextension=".mp3", filetypes=(("MP3 files", "*.mp3"), ("All files", "*.*")))
        if filepath:
            self.output_file_path.set(filepath)
            self.update_status(f"Output set to: {os.path.basename(filepath)}")

    # --- Plotting Methods ---

    def plot_waveform(self):
        if self.audio_samples is None or self.ax is None:
            return

        self.clear_plot() # Clear previous plot elements

        num_samples = len(self.audio_samples)
        self.time_axis = np.linspace(0, self.audio_duration_s, num=num_samples)

        # --- Performance Optimization: Downsampling for plotting ---
        # Plotting millions of points is slow. Plot a subset.
        target_points = 2000 # Target number of points to plot
        if num_samples > target_points:
            step = num_samples // target_points
            plot_samples = self.audio_samples[::step]
            plot_time = self.time_axis[::step]
        else:
            plot_samples = self.audio_samples
            plot_time = self.time_axis
        # --- End Optimization ---

        self.waveform_line, = self.ax.plot(plot_time, plot_samples, linewidth=0.5)
        self.ax.set_xlim(0, self.audio_duration_s)
        # Set Y limits based on sample range (adjust if needed, e.g., for normalized data)
        max_abs_sample = np.max(np.abs(plot_samples)) if len(plot_samples) > 0 else 1
        self.ax.set_ylim(-max_abs_sample * 1.1, max_abs_sample * 1.1)

        self.ax.set_xlabel("Time (s)")
        self.canvas.draw_idle() # Use draw_idle for efficiency


    def clear_plot(self):
        if self.ax:
            # Remove specific elements instead of ax.clear() to keep labels/ticks
            if self.waveform_line:
                 self.waveform_line.remove()
                 self.waveform_line = None
            if self.selection_span:
                 self.selection_span.remove()
                 self.selection_span = None
            # self.ax.clear() # Avoid this as it removes labels etc.
            self.ax.set_xlim(0, 10) # Reset limits
            self.ax.set_ylim(-1, 1) # Reset limits
            self.canvas.draw_idle()


    def _update_selection_from_sliders(self, event=None):
        """Callback when either slider is moved."""
        start_t = self.start_time_var.get()
        end_t = self.end_time_var.get()

        # Ensure start <= end
        if start_t > end_t:
            # Which slider moved? Adjust the *other* one.
            # This logic assumes ttk.Scale calls command *after* variable update.
            # A bit tricky to know which one triggered if simultaneous.
            # Simplest: If start > end, assume start moved last, push end.
            # Or, if end < start, assume end moved last, pull start.
            # Let's try: if start slider is source, adjust end, else adjust start
            # (Checking widget focus might work but is complex)
            # Easiest robust fix: just force end to be >= start
             end_t = start_t
             self.end_time_var.set(end_t)
             # Or: force start to be <= end
             # start_t = end_t
             # self.start_time_var.set(start_t)


        self.start_slider_label_var.set(f"Start: {start_t:.2f}s")
        self.end_slider_label_var.set(f"End: {end_t:.2f}s")

        self._update_selection_visuals(start_t, end_t)


    def _update_selection_visuals(self, start_t=None, end_t=None):
        """Updates the shaded region on the plot."""
        if self.ax is None: return

        if start_t is None: start_t = self.start_time_var.get()
        if end_t is None: end_t = self.end_time_var.get()

        # Remove previous span if it exists
        if self.selection_span:
            self.selection_span.remove()
            self.selection_span = None

        # Draw new span if duration is positive
        if end_t > start_t and self.loaded_audio:
             self.selection_span = self.ax.axvspan(start_t, end_t, alpha=0.3, color='red', zorder=-1) # zorder=-1 puts it behind waveform

        self.canvas.draw_idle()


    # --- Playback Methods ---

    def _play_segment(self, segment):
        """Handles playback of a pydub AudioSegment in a thread."""
        if self.play_obj and self.play_obj.is_playing():
            self.stop_audio() # Stop current playback first
            time.sleep(0.1) # Brief pause allow stop to register

        if not segment: return

        self.update_status("Starting playback...")
        total_duration = len(segment) / 1000.0 # Duration of the segment being played

        try:
            audio_data = segment.raw_data
            num_channels = segment.channels
            bytes_per_sample = segment.sample_width
            sample_rate = segment.frame_rate

            def playback_task():
                try:
                     self.play_obj = sa.play_buffer(audio_data, num_channels, bytes_per_sample, sample_rate)
                     self.master.after(0, self.update_playback_status, None, total_duration) # Update status with segment duration
                     self.master.after(0, self.update_button_states)
                     self.play_obj.wait_done()
                except Exception as e:
                     self.master.after(0, messagebox.showerror, "Playback Error", f"Could not play audio:\n{e}")
                     self.play_obj = None
                finally:
                     # Update UI after playback finishes/stops
                     self.master.after(0, self.update_playback_status)
                     self.master.after(0, self.update_button_states)

            self.playback_thread = threading.Thread(target=playback_task, daemon=True)
            self.playback_thread.start()
            self.update_button_states() # Disable play etc. immediately

        except Exception as e:
            messagebox.showerror("Playback Error", f"Failed to prepare audio for playback:\n{e}")
            self.update_status("Playback failed.")
            self.play_obj = None
            self.update_button_states()

    def play_audio(self):
        """Plays the entire loaded audio file."""
        if not self.loaded_audio:
            messagebox.showwarning("No Audio", "Please load an input file first.")
            return
        self._play_segment(self.loaded_audio)

    def play_selection(self):
        """Plays only the selected portion of the audio."""
        if not self.loaded_audio:
            messagebox.showwarning("No Audio", "Please load an input file first.")
            return

        start_t = self.start_time_var.get()
        end_t = self.end_time_var.get()

        if start_t >= end_t:
             messagebox.showwarning("Invalid Selection", "Start time must be less than end time.")
             return

        start_ms = int(start_t * 1000)
        end_ms = int(end_t * 1000)

        try:
            selected_segment = self.loaded_audio[start_ms:end_ms]
            self._play_segment(selected_segment)
        except Exception as e:
             messagebox.showerror("Playback Error", f"Could not prepare selected audio segment:\n{e}")


    def stop_audio(self):
        if self.play_obj and self.play_obj.is_playing():
            self.update_status("Stopping playback...")
            self.play_obj.stop()
            # Playback thread will eventually finish due to wait_done() ending
        self.play_obj = None # Clear reference immediately
        # UI updates happen in the finally block of the playback thread task
        # but force an update now for responsiveness
        self.master.after(0, self.update_playback_status)
        self.master.after(0, self.update_button_states)


    # --- Cropping Methods ---

    def start_cropping_thread(self):
        input_p = self.input_file_path.get()
        output_p = self.output_file_path.get()

        if not input_p or not output_p:
            messagebox.showerror("Error", "Please select both input and output files.")
            return
        if not self.loaded_audio:
             messagebox.showerror("Error", "Input audio not loaded correctly.")
             return

        start_t = self.start_time_var.get()
        end_t = self.end_time_var.get()

        if start_t < 0 or end_t < 0: # Should be prevented by slider range, but check
            messagebox.showerror("Error", "Start and End times cannot be negative.")
            return
        if start_t >= end_t:
             messagebox.showerror("Error", "Start time must be less than End time.")
             return

        self.set_ui_state_during_process(False) # Disable UI
        self.update_status("Starting crop...")

        thread = threading.Thread(target=self.run_crop_task, args=(input_p, output_p, start_t, end_t), daemon=True)
        thread.start()

    def run_crop_task(self, input_p, output_p, start_t, end_t):
         """The actual task run by the thread."""
         try:
             # Use the original crop_mp3 function which re-loads the file for cropping
             # This avoids potential issues if the self.loaded_audio was modified or is huge
             success = crop_mp3(input_p, output_p, start_t, end_t, self.update_status)
             # Status/messages handled within crop_mp3
         except Exception as e:
             self.master.after(0, self.update_status, f"Unexpected Cropping Error: {e}")
             self.master.after(0, messagebox.showerror, "Unexpected Error", f"An unexpected error occurred during cropping:\n{e}")
         finally:
             # Re-enable the UI on main thread
             self.master.after(0, self.set_ui_state_during_process, True)
             self.master.after(0, self.update_button_states) # Ensure buttons reflect final state


# --- Main Execution ---
if __name__ == "__main__":
    # Fix blurry fonts on Windows High DPI displays (optional but recommended)
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except ImportError: # Not Windows or ctypes failed
        pass
    except AttributeError: # Older Windows version without SetProcessDpiAwareness
        try: # Try older method
             windll.user32.SetProcessDPIAware()
        except: # Still failed, ignore
             pass

    root = tk.Tk()
    app = Mp3CropperApp(root)

    def on_closing():
        app.stop_audio() # Stop playback cleanly
        root.destroy()
    root.protocol("WM_DELETE_WINDOW", on_closing)

    root.mainloop()