import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import subprocess
import threading
import os
import shutil

class VideoConverterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Simple Video Converter")
        self.root.geometry("600x400")
        
        # --- Conversion Presets ---
        # A dictionary mapping user-friendly names to FFmpeg command templates.
        self.presets = {
            "Web Standard (MP4, H.264, AAC)": 
                'ffmpeg -i "{input}" -c:v libx264 -preset medium -crf 23 -c:a aac -b:a 128k "{output}"',
            "Web - Smaller File (MP4, H.264, AAC)": 
                'ffmpeg -i "{input}" -c:v libx264 -preset slow -crf 28 -c:a aac -b:a 96k "{output}"',
            "High Quality (MP4, H.264, AAC)":
                'ffmpeg -i "{input}" -c:v libx264 -preset slow -crf 18 -c:a aac -b:a 192k "{output}"',
            "Audio Only (MP3)":
                'ffmpeg -i "{input}" -vn -c:a libmp3lame -q:a 2 "{output}"',
        }

        # --- Variables ---
        self.input_path = tk.StringVar()
        self.output_path = tk.StringVar()
        self.selected_preset = tk.StringVar()

        # --- Create Widgets ---
        self._create_widgets()
        
        # --- Check for FFmpeg ---
        self._check_ffmpeg()

    def _check_ffmpeg(self):
        """Checks if ffmpeg is in the system's PATH and disables the button if not."""
        if not shutil.which("ffmpeg"):
            messagebox.showerror(
                "FFmpeg Not Found",
                "FFmpeg could not be found. Please install it and make sure it's in your system's PATH. The convert button will be disabled."
            )
            self.convert_button.config(state="disabled")

    def _create_widgets(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill="both", expand=True)

        # --- Input File Selection ---
        input_frame = ttk.LabelFrame(main_frame, text="1. Select Input Video", padding="10")
        input_frame.pack(fill="x", pady=5)
        
        ttk.Entry(input_frame, textvariable=self.input_path, state="readonly").pack(side="left", fill="x", expand=True, padx=(0, 5))
        ttk.Button(input_frame, text="Browse...", command=self.browse_input).pack(side="left")

        # --- Preset Selection ---
        preset_frame = ttk.LabelFrame(main_frame, text="2. Choose Conversion Preset", padding="10")
        preset_frame.pack(fill="x", pady=5)
        
        preset_menu = ttk.Combobox(preset_frame, textvariable=self.selected_preset, values=list(self.presets.keys()), state="readonly")
        preset_menu.pack(fill="x", expand=True)
        preset_menu.current(0) # Set default selection
        preset_menu.bind("<<ComboboxSelected>>", self.suggest_output_path)


        # --- Output File Selection ---
        output_frame = ttk.LabelFrame(main_frame, text="3. Specify Output Location", padding="10")
        output_frame.pack(fill="x", pady=5)
        
        ttk.Entry(output_frame, textvariable=self.output_path).pack(side="left", fill="x", expand=True, padx=(0, 5))
        ttk.Button(output_frame, text="Browse...", command=self.browse_output).pack(side="left")

        # --- Convert Button and Progress ---
        action_frame = ttk.Frame(main_frame, padding="10")
        action_frame.pack(fill="x", pady=10)

        self.convert_button = ttk.Button(action_frame, text="Convert Video", command=self.start_conversion_thread)
        self.convert_button.pack(pady=5)

        self.progress = ttk.Progressbar(action_frame, orient="horizontal", length=300, mode="determinate")
        self.progress.pack(pady=5)

        self.status_label = ttk.Label(action_frame, text="Ready. Please select a file.")
        self.status_label.pack(pady=5)

    def browse_input(self):
        filepath = filedialog.askopenfilename(
            title="Select a Video File",
            filetypes=(("Video Files", "*.mp4 *.mov *.avi *.mkv"), ("All files", "*.*"))
        )
        if filepath:
            self.input_path.set(filepath)
            self.status_label.config(text=f"Selected: {os.path.basename(filepath)}")
            self.suggest_output_path()

    def suggest_output_path(self, event=None):
        """Automatically suggest an output path based on input and preset."""
        if not self.input_path.get():
            return
            
        preset_name = self.selected_preset.get()
        input_file = self.input_path.get()
        directory, filename = os.path.split(input_file)
        name_part, _ = os.path.splitext(filename)

        if "Audio Only (MP3)" in preset_name:
            new_extension = ".mp3"
        else:
            new_extension = ".mp4"
            
        suggested_filename = f"{name_part}_converted{new_extension}"
        self.output_path.set(os.path.join(directory, suggested_filename))


    def browse_output(self):
        preset_name = self.selected_preset.get()
        if "Audio Only (MP3)" in preset_name:
            default_ext = ".mp3"
            file_types = (("MP3 Audio", "*.mp3"), ("All files", "*.*"))
        else:
            default_ext = ".mp4"
            file_types = (("MP4 Video", "*.mp4"), ("All files", "*.*"))

        filepath = filedialog.asksaveasfilename(
            title="Save Converted File As",
            initialfile=os.path.basename(self.output_path.get() or "output"),
            defaultextension=default_ext,
            filetypes=file_types
        )
        if filepath:
            self.output_path.set(filepath)

    def start_conversion_thread(self):
        """Starts the conversion in a separate thread to avoid freezing the GUI."""
        if not self.input_path.get() or not self.output_path.get():
            messagebox.showwarning("Missing Info", "Please select an input and output file.")
            return

        self.convert_button.config(state="disabled")
        self.status_label.config(text="Starting conversion...")
        self.progress.config(mode='indeterminate')
        self.progress.start()

        # Run the time-consuming ffmpeg process in a new thread
        conversion_thread = threading.Thread(target=self.run_conversion, daemon=True)
        conversion_thread.start()
        
    def run_conversion(self):
        """The actual FFmpeg process execution."""
        try:
            input_file = self.input_path.get()
            output_file = self.output_path.get()
            preset_name = self.selected_preset.get()
            command_template = self.presets[preset_name]
            
            command = command_template.format(input=input_file, output=output_file)
            
            # Using Popen to capture stdout/stderr if needed for progress, but run is simpler for now
            # For a simple "done/fail" status, subprocess.run is great.
            process = subprocess.run(
                command, 
                shell=True, # Use shell=True for simplicity with complex commands
                check=True, # Raise an exception if ffmpeg returns a non-zero exit code (error)
                capture_output=True, # Capture stdout and stderr
                text=True # Decode stdout/stderr as text
            )

            # --- Success ---
            self.root.after(0, self.on_conversion_complete, True, "Conversion successful!")

        except subprocess.CalledProcessError as e:
            # --- Failure ---
            error_message = f"Conversion failed!\n\nFFmpeg Error:\n{e.stderr}"
            self.root.after(0, self.on_conversion_complete, False, error_message)
        except Exception as e:
            # --- Other unexpected errors ---
            self.root.after(0, self.on_conversion_complete, False, f"An unexpected error occurred: {e}")

    def on_conversion_complete(self, success, message):
        """Updates the GUI after conversion is done. Must be called via root.after()."""
        self.progress.stop()
        self.progress.config(mode='determinate')
        self.progress['value'] = 100 if success else 0
        self.convert_button.config(state="normal")

        if success:
            self.status_label.config(text="Done!")
            messagebox.showinfo("Success", message)
        else:
            self.status_label.config(text="Failed.")
            messagebox.showerror("Error", message)

if __name__ == "__main__":
    root = tk.Tk()
    app = VideoConverterApp(root)
    root.mainloop()