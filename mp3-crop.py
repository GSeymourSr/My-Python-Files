import tkinter as tk
from tkinter import ttk  # For themed widgets (optional, looks nicer)
from tkinter import filedialog, messagebox
import os
from pydub import AudioSegment
import threading # To prevent GUI freezing during processing

# --- Core Cropping Logic (Slightly modified for GUI feedback) ---

def crop_mp3(input_path, output_path, start_seconds, end_seconds, status_callback):
    """
    Crops an MP3 file and provides status updates via callback.

    Args:
        input_path (str): Path to the input MP3 file.
        output_path (str): Path to save the cropped MP3 file.
        start_seconds (float): Start time for the crop in seconds.
        end_seconds (float): End time for the crop in seconds.
        status_callback (function): Function to call with status messages.

    Returns:
        bool: True if cropping was successful, False otherwise.
    """
    status_callback(f"Loading: {os.path.basename(input_path)}...")
    if not os.path.exists(input_path):
        status_callback(f"Error: Input file not found.")
        messagebox.showerror("Error", f"Input file not found:\n{input_path}")
        return False

    try:
        # Load the MP3 file
        audio = AudioSegment.from_mp3(input_path)
        status_callback(f"Loaded. Duration: {len(audio) / 1000.0:.2f}s")

    except Exception as e:
        status_callback(f"Error loading MP3: {e}")
        messagebox.showerror("Error", f"Error loading MP3 file:\n{e}\n\nEnsure FFmpeg is installed and in PATH.")
        return False

    # Convert start and end times from seconds to milliseconds
    start_ms = int(start_seconds * 1000)
    end_ms = int(end_seconds * 1000)

    # --- Basic Validation (More detailed validation done in GUI) ---
    audio_duration_ms = len(audio)
    if start_ms < 0: start_ms = 0
    if end_ms > audio_duration_ms: end_ms = audio_duration_ms
    if start_ms >= end_ms:
        status_callback("Error: Start time must be less than end time.")
        messagebox.showerror("Error", "Start time must be less than end time (even after clamping to duration).")
        return False
    # --- End Validation ---

    status_callback(f"Cropping from {start_ms/1000.0:.2f}s to {end_ms/1000.0:.2f}s...")

    try:
        # Perform the crop
        cropped_audio = audio[start_ms:end_ms]

        status_callback(f"Exporting to: {os.path.basename(output_path)}...")
        # Export the cropped segment
        cropped_audio.export(output_path, format="mp3")
        status_callback(f"Success! Saved cropped audio.")
        # messagebox.showinfo("Success", f"Successfully created:\n{output_path}") # Optional popup
        return True
    except Exception as e:
        status_callback(f"Error exporting: {e}")
        messagebox.showerror("Error", f"Error exporting cropped MP3 file:\n{e}\n\nCheck write permissions.")
        return False

# --- Tkinter GUI Application ---

class Mp3CropperApp:
    def __init__(self, master):
        self.master = master
        master.title("MP3 Cropper")
        master.geometry("550x250") # Adjust size as needed

        # Style (Optional)
        style = ttk.Style()
        style.theme_use('clam') # Or 'vista', 'xpnative', 'default'

        # --- Variables ---
        self.input_file_path = tk.StringVar()
        self.output_file_path = tk.StringVar()
        self.start_time_str = tk.StringVar(value="0.0")
        self.end_time_str = tk.StringVar(value="10.0")
        self.status_text = tk.StringVar(value="Ready. Select files and times.")

        # --- GUI Layout ---
        frame = ttk.Frame(master, padding="10")
        frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        master.columnconfigure(0, weight=1)
        master.rowconfigure(0, weight=1)

        # Input File Row
        ttk.Label(frame, text="Input MP3:").grid(row=0, column=0, sticky=tk.W, pady=2)
        ttk.Entry(frame, textvariable=self.input_file_path, width=50).grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5)
        ttk.Button(frame, text="Browse...", command=self.select_input_file).grid(row=0, column=2, sticky=tk.E)

        # Output File Row
        ttk.Label(frame, text="Output MP3:").grid(row=1, column=0, sticky=tk.W, pady=2)
        ttk.Entry(frame, textvariable=self.output_file_path, width=50).grid(row=1, column=1, sticky=(tk.W, tk.E), padx=5)
        ttk.Button(frame, text="Save As...", command=self.select_output_file).grid(row=1, column=2, sticky=tk.E)

        # Time Row
        time_frame = ttk.Frame(frame)
        time_frame.grid(row=2, column=0, columnspan=3, sticky=tk.W, pady=5)

        ttk.Label(time_frame, text="Start Time (s):").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Entry(time_frame, textvariable=self.start_time_str, width=10).pack(side=tk.LEFT, padx=5)

        ttk.Label(time_frame, text="End Time (s):").pack(side=tk.LEFT, padx=(20, 5))
        ttk.Entry(time_frame, textvariable=self.end_time_str, width=10).pack(side=tk.LEFT, padx=5)

        # Crop Button Row
        self.crop_button = ttk.Button(frame, text="Crop Audio", command=self.start_cropping_thread)
        self.crop_button.grid(row=3, column=0, columnspan=3, pady=10)

        # Status Bar
        status_bar = ttk.Label(frame, textvariable=self.status_text, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(5,0))

        # Make columns resizable
        frame.columnconfigure(1, weight=1)

    def select_input_file(self):
        filetypes = (("MP3 files", "*.mp3"), ("All files", "*.*"))
        filepath = filedialog.askopenfilename(title="Select Input MP3", filetypes=filetypes)
        if filepath:
            self.input_file_path.set(filepath)
            # Suggest an output filename based on input
            if not self.output_file_path.get():
                 base, ext = os.path.splitext(os.path.basename(filepath))
                 suggested_output = os.path.join(os.path.dirname(filepath), f"{base}_cropped.mp3")
                 self.output_file_path.set(suggested_output)
            self.status_text.set(f"Selected input: {os.path.basename(filepath)}")

    def select_output_file(self):
        filetypes = (("MP3 files", "*.mp3"), ("All files", "*.*"))
        # Suggest a name based on input if available
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
            self.status_text.set(f"Selected output: {os.path.basename(filepath)}")

    def update_status(self, message):
        # Ensure GUI updates happen on the main thread
        self.master.after(0, self.status_text.set, message)

    def set_ui_state(self, enabled):
        """Enable or disable UI elements during processing."""
        state = tk.NORMAL if enabled else tk.DISABLED
        # Find relevant widgets to disable/enable
        for widget in self.master.winfo_children():
             if isinstance(widget, ttk.Frame): # Look inside the main frame
                  for child in widget.winfo_children():
                      # Disable buttons and entries, but not labels or the inner time frame
                      if isinstance(child, (ttk.Button, ttk.Entry)):
                          child.configure(state=state)
                      # Need to disable entries within the time frame too
                      if child == widget.winfo_children()[2]: # A bit fragile, assumes time frame is 3rd widget
                          for time_entry in child.winfo_children():
                              if isinstance(time_entry, ttk.Entry):
                                   time_entry.configure(state=state)


    def start_cropping_thread(self):
        """Starts the cropping process in a separate thread."""
        # Get values from GUI
        input_p = self.input_file_path.get()
        output_p = self.output_file_path.get()

        if not input_p or not output_p:
            messagebox.showerror("Error", "Please select both input and output files.")
            return

        try:
            start_t = float(self.start_time_str.get())
            end_t = float(self.end_time_str.get())
        except ValueError:
            messagebox.showerror("Error", "Invalid start or end time. Please enter numbers (e.g., 5.0).")
            return

        # --- Input Validation ---
        if start_t < 0 or end_t < 0:
            messagebox.showerror("Error", "Start and End times cannot be negative.")
            return
        if start_t >= end_t:
             messagebox.showerror("Error", "Start time must be less than End time.")
             return
        # We'll let crop_mp3 handle validation against audio duration after loading


        # Disable button, start processing in thread
        self.set_ui_state(False)
        self.update_status("Starting crop...")

        # Run crop_mp3 in a separate thread
        thread = threading.Thread(target=self.run_crop_task, args=(input_p, output_p, start_t, end_t), daemon=True)
        thread.start()


    def run_crop_task(self, input_p, output_p, start_t, end_t):
         """The actual task run by the thread."""
         try:
             success = crop_mp3(input_p, output_p, start_t, end_t, self.update_status)
             if success:
                 # Optionally show success popup, or just rely on status bar
                 # messagebox.showinfo("Success", f"Successfully created:\n{output_p}")
                 pass # Status already updated by crop_mp3
             # If crop_mp3 returned False, it already showed an error message box.
         except Exception as e:
             # Catch any unexpected errors during the crop process itself
             self.update_status(f"Unexpected Error: {e}")
             messagebox.showerror("Unexpected Error", f"An unexpected error occurred:\n{e}")
         finally:
             # Re-enable the UI regardless of success or failure
             self.master.after(0, self.set_ui_state, True)


# --- Main Execution ---
if __name__ == "__main__":
    root = tk.Tk()
    app = Mp3CropperApp(root)
    root.mainloop()