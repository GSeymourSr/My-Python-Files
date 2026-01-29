import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import subprocess
import threading
import os
import shutil

class VideoConverterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Simple Video Converter (Batch Mode)")
        self.root.geometry("700x550") # Increased size for the listbox
        
        # --- Conversion Presets ---
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
        self.input_files = [] # CHANGED: Store a list of files, not a single string
        self.output_dir = tk.StringVar()
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

        # --- Input File Selection (NOW A LISTBOX) ---
        input_frame = ttk.LabelFrame(main_frame, text="1. Select Input Videos", padding="10")
        input_frame.pack(fill="both", expand=True, pady=5)
        
        # Listbox and Scrollbar
        list_frame = ttk.Frame(input_frame)
        list_frame.pack(fill="both", expand=True)
        
        self.file_listbox = tk.Listbox(list_frame, selectmode=tk.EXTENDED)
        self.file_listbox.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.file_listbox.yview)
        scrollbar.pack(side="right", fill="y")
        self.file_listbox.config(yscrollcommand=scrollbar.set)
        
        # Add/Remove Buttons
        button_frame = ttk.Frame(input_frame)
        button_frame.pack(fill="x", pady=(5,0))
        ttk.Button(button_frame, text="Add Files...", command=self.add_files).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Remove Selected", command=self.remove_selected_files).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Clear All", command=self.clear_all_files).pack(side="left", padx=5)


        # --- Preset Selection ---
        preset_frame = ttk.LabelFrame(main_frame, text="2. Choose Conversion Preset", padding="10")
        preset_frame.pack(fill="x", pady=5)
        
        preset_menu = ttk.Combobox(preset_frame, textvariable=self.selected_preset, values=list(self.presets.keys()), state="readonly")
        preset_menu.pack(fill="x", expand=True)
        preset_menu.current(0)

        # --- Output Directory Selection ---
        output_frame = ttk.LabelFrame(main_frame, text="3. Select Output Directory", padding="10")
        output_frame.pack(fill="x", pady=5)
        
        ttk.Entry(output_frame, textvariable=self.output_dir, state="readonly").pack(side="left", fill="x", expand=True, padx=(0, 5))
        ttk.Button(output_frame, text="Browse...", command=self.browse_output_dir).pack(side="left")

        # --- Convert Button and Progress ---
        action_frame = ttk.Frame(main_frame, padding="10")
        action_frame.pack(fill="x", pady=10)

        self.convert_button = ttk.Button(action_frame, text="Start Batch Conversion", command=self.start_conversion_thread)
        self.convert_button.pack(pady=5)

        # Progress for the current file
        self.file_progress_label = ttk.Label(action_frame, text="Current File Progress:")
        self.file_progress_label.pack(anchor="w")
        self.file_progress = ttk.Progressbar(action_frame, orient="horizontal", length=300, mode="indeterminate")
        self.file_progress.pack(fill="x", pady=2)
        
        # Progress for the entire batch
        self.batch_progress_label = ttk.Label(action_frame, text="Overall Batch Progress:")
        self.batch_progress_label.pack(anchor="w", pady=(5,0))
        self.batch_progress = ttk.Progressbar(action_frame, orient="horizontal", length=300, mode="determinate")
        self.batch_progress.pack(fill="x", pady=2)


        self.status_label = ttk.Label(action_frame, text="Ready. Please add files to convert.")
        self.status_label.pack(pady=5)

    def add_files(self):
        """NEW: Opens a dialog to select multiple files and adds them to the list."""
        filepaths = filedialog.askopenfilenames(
            title="Select Video Files",
            filetypes=(("Video Files", "*.mp4 *.mov *.avi *.mkv"), ("All files", "*.*"))
        )
        if filepaths:
            for path in filepaths:
                if path not in self.input_files: # Avoid duplicates
                    self.input_files.append(path)
                    self.file_listbox.insert(tk.END, os.path.basename(path))
            
            # Suggest an output directory based on the first file if one isn't set
            if not self.output_dir.get() and self.input_files:
                self.output_dir.set(os.path.dirname(self.input_files[0]))


    def remove_selected_files(self):
        """NEW: Removes selected files from the listbox and internal list."""
        selected_indices = self.file_listbox.curselection()
        # Iterate backwards to avoid index shifting issues
        for i in sorted(selected_indices, reverse=True):
            self.file_listbox.delete(i)
            del self.input_files[i]

    def clear_all_files(self):
        """NEW: Clears the entire list of files."""
        self.file_listbox.delete(0, tk.END)
        self.input_files.clear()

    def browse_output_dir(self):
        """MODIFIED: Asks for a directory instead of a filename."""
        directory = filedialog.askdirectory(
            title="Select Output Folder"
        )
        if directory:
            self.output_dir.set(directory)

    def start_conversion_thread(self):
        """MODIFIED: Starts the batch conversion in a separate thread."""
        if not self.input_files:
            messagebox.showwarning("No Files", "Please add at least one video file to the list.")
            return
        if not self.output_dir.get():
            messagebox.showwarning("No Output Directory", "Please select an output directory.")
            return

        self.convert_button.config(state="disabled")
        
        # Run the batch conversion in a new thread
        conversion_thread = threading.Thread(target=self.run_batch_conversion, daemon=True)
        conversion_thread.start()
        
    def run_batch_conversion(self):
        """NEW: The main logic for converting files sequentially."""
        total_files = len(self.input_files)
        success_count = 0
        failures = []

        self.root.after(0, self.batch_progress.config, {'maximum': total_files, 'value': 0})

        for i, input_file in enumerate(self.input_files):
            # --- Update GUI for the current file ---
            status_text = f"Converting file {i+1} of {total_files}: {os.path.basename(input_file)}"
            self.root.after(0, self.status_label.config, {'text': status_text})
            self.root.after(0, self.file_progress.start)
            
            try:
                # --- Generate Output Path ---
                preset_name = self.selected_preset.get()
                name_part, _ = os.path.splitext(os.path.basename(input_file))
                
                if "Audio Only (MP3)" in preset_name:
                    new_extension = ".mp3"
                else:
                    new_extension = ".mp4"
                
                output_filename = f"{name_part}_converted{new_extension}"
                output_file = os.path.join(self.output_dir.get(), output_filename)
                
                # --- Run FFmpeg Command ---
                command_template = self.presets[preset_name]
                command = command_template.format(input=input_file, output=output_file)
                
                subprocess.run(
                    command, 
                    shell=True, 
                    check=True, 
                    capture_output=True, 
                    text=True
                )
                success_count += 1

            except subprocess.CalledProcessError as e:
                # --- Handle Failure ---
                error_info = f"'{os.path.basename(input_file)}' failed: {e.stderr.strip().splitlines()[-1]}"
                failures.append(error_info)
            except Exception as e:
                error_info = f"'{os.path.basename(input_file)}' failed with unexpected error: {e}"
                failures.append(error_info)
            
            # --- Update Overall Progress ---
            self.root.after(0, self.batch_progress.step)
            self.root.after(0, self.file_progress.stop)
        
        # --- Finalize and show summary ---
        self.root.after(0, self.on_batch_complete, total_files, success_count, failures)

    def on_batch_complete(self, total, success, failures):
        """NEW: Updates the GUI after the entire batch is done."""
        self.convert_button.config(state="normal")
        self.status_label.config(text="Batch conversion complete.")
        self.file_progress.stop()

        summary_message = f"Batch Complete!\n\nSuccessfully converted: {success} of {total} files."
        if failures:
            summary_message += "\n\nThe following files failed:\n- " + "\n- ".join(failures)
            messagebox.showwarning("Batch Finished with Errors", summary_message)
        else:
            messagebox.showinfo("Success", summary_message)

if __name__ == "__main__":
    root = tk.Tk()
    app = VideoConverterApp(root)
    root.mainloop()