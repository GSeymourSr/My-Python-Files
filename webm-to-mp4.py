import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import subprocess
import threading
import os
import re

class WebmToMp4Converter:
    def __init__(self, root):
        self.root = root
        self.root.title("WebM to MP4 Converter (Final)")
        self.root.geometry("500x270")
        self.root.resizable(False, False)

        self.style = ttk.Style(self.root)
        self.style.theme_use('clam')

        self.input_file = tk.StringVar()
        self.output_file = tk.StringVar()
        self.error_output = ""

        main_frame = ttk.Frame(self.root, padding="15")
        main_frame.pack(fill="both", expand=True)

        input_label = ttk.Label(main_frame, text="Input WebM File:")
        input_label.grid(row=0, column=0, sticky="w", pady=(0, 5))
        
        self.input_entry = ttk.Entry(main_frame, textvariable=self.input_file, width=50)
        self.input_entry.grid(row=1, column=0, sticky="ew", padx=(0, 10))

        input_button = ttk.Button(main_frame, text="Browse...", command=self.browse_input)
        input_button.grid(row=1, column=1, sticky="ew")

        output_label = ttk.Label(main_frame, text="Output MP4 File:")
        output_label.grid(row=2, column=0, sticky="w", pady=(10, 5))

        self.output_entry = ttk.Entry(main_frame, textvariable=self.output_file, width=50)
        self.output_entry.grid(row=3, column=0, sticky="ew", padx=(0, 10))

        output_button = ttk.Button(main_frame, text="Save As...", command=self.browse_output)
        output_button.grid(row=3, column=1, sticky="ew")
        
        self.convert_button = ttk.Button(main_frame, text="Convert to MP4", command=self.start_conversion)
        self.convert_button.grid(row=4, column=0, columnspan=2, pady=(15, 10), sticky="ew")

        self.progress = ttk.Progressbar(main_frame, orient="horizontal", length=100, mode="determinate")
        self.progress.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(0, 5))
        
        self.status_label = ttk.Label(main_frame, text="Ready. Select a WebM file to begin.")
        self.status_label.grid(row=6, column=0, columnspan=2, sticky="w")
        
        main_frame.columnconfigure(0, weight=1)

    def browse_input(self):
        file_path = filedialog.askopenfilename(
            title="Select a WebM File",
            filetypes=(("WebM files", "*.webm"), ("All files", "*.*"))
        )
        if file_path:
            self.input_file.set(file_path)
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            output_dir = os.path.dirname(file_path)
            self.output_file.set(os.path.join(output_dir, f"{base_name}.mp4"))
            self.status_label.config(text=f"Ready to convert '{os.path.basename(file_path)}'")

    def browse_output(self):
        input_path = self.input_file.get()
        initial_file = os.path.splitext(os.path.basename(input_path))[0] if input_path else "output"

        file_path = filedialog.asksaveasfilename(
            title="Save MP4 As",
            defaultextension=".mp4",
            initialfile=f"{initial_file}.mp4",
            filetypes=(("MP4 files", "*.mp4"), ("All files", "*.*"))
        )
        if file_path:
            self.output_file.set(file_path)

    def start_conversion(self):
        input_path = self.input_file.get()
        output_path = self.output_file.get()

        if not input_path or not output_path:
            messagebox.showerror("Error", "Please select both input and output files.")
            return

        self.convert_button.config(state="disabled")
        self.status_label.config(text="Starting conversion...")
        self.progress["value"] = 0
        self.error_output = ""
        
        conversion_thread = threading.Thread(
            target=self.run_ffmpeg, args=(input_path, output_path)
        )
        conversion_thread.start()

    def run_ffmpeg(self, input_path, output_path):
        try:
            duration_cmd = ['ffmpeg', '-i', input_path]
            process_info = subprocess.Popen(
                duration_cmd, stderr=subprocess.PIPE, stdout=subprocess.DEVNULL, 
                universal_newlines=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            info_output = process_info.stderr.read()
            
            total_duration_seconds = 0
            duration_match = re.search(r'Duration: (\d{2}):(\d{2}):(\d{2})\.(\d{2})', info_output)
            if duration_match:
                h, m, s, ms = map(int, duration_match.groups())
                total_duration_seconds = h * 3600 + m * 60 + s + ms / 100.0
            
            # ** THE FINAL FIX IS HERE: a second video filter is added to ensure even dimensions **
            command = [
                'ffmpeg', '-y', '-i', input_path,
                # Use a filter complex to chain our two required fixes
                '-vf', 'format=yuv420p,scale=trunc(iw/2)*2:trunc(ih/2)*2',
                '-c:v', 'libx264',
                '-preset', 'veryfast',
                '-c:a', 'aac',
                output_path
            ]
            
            self.status_label.config(text="Converting... 0%")
            process_conv = subprocess.Popen(
                command, stderr=subprocess.PIPE, stdout=subprocess.DEVNULL, 
                universal_newlines=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )

            for line in process_conv.stderr:
                self.error_output += line
                if "time=" in line and total_duration_seconds > 0:
                    time_match = re.search(r'time=(\d{2}):(\d{2}):(\d{2})\.(\d{2})', line)
                    if time_match:
                        h, m, s, ms = map(int, time_match.groups())
                        current_time = h * 3600 + m * 60 + s + ms / 100.0
                        progress_percent = (current_time / total_duration_seconds) * 100
                        self.progress["value"] = progress_percent
                        self.status_label.config(text=f"Converting... {int(progress_percent)}%")
                        self.root.update_idletasks()

            process_conv.wait()
            
            if process_conv.returncode == 0:
                self.progress["value"] = 100
                self.status_label.config(text="Conversion successful!")
                messagebox.showinfo("Success", f"File converted successfully to:\n{output_path}")
            else:
                self.status_label.config(text=f"Error! FFmpeg exited with code {process_conv.returncode}")
                messagebox.showerror(
                    "Conversion Failed", 
                    f"FFmpeg exited with error code {process_conv.returncode}.\n\n"
                    f"Detailed error log:\n\n{self.error_output[-1000:]}"
                )

        except FileNotFoundError:
            self.status_label.config(text="Error: FFmpeg not found.")
            messagebox.showerror("Error", "FFmpeg not found. Please make sure it's installed and in your system's PATH.")
        except Exception as e:
            self.status_label.config(text=f"An unexpected error occurred.")
            messagebox.showerror("Error", f"An unexpected error occurred:\n{e}")
        finally:
            self.convert_button.config(state="normal")


if __name__ == "__main__":
    root = tk.Tk()
    app = WebmToMp4Converter(root)
    root.mainloop()