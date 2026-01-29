import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import threading
from pydub import AudioSegment

class M4aToMp3Converter:
    def __init__(self, root):
        self.root = root
        self.root.title("M4A to MP3 Converter")
        self.root.geometry("600x450")
        self.root.minsize(500, 400)

        # --- Data Storage ---
        self.input_files = []
        self.output_dir = tk.StringVar()

        # --- UI Styling ---
        style = ttk.Style(self.root)
        style.configure('TButton', font=('Helvetica', 10))
        style.configure('TLabel', font=('Helvetica', 10))
        style.configure('Header.TLabel', font=('Helvetica', 12, 'bold'))

        # --- Main Frame ---
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- Input Section ---
        input_frame = ttk.LabelFrame(main_frame, text="1. Select M4A Files", padding="10")
        input_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.select_files_btn = ttk.Button(input_frame, text="Browse for Files...", command=self.select_files)
        self.select_files_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.file_listbox = tk.Listbox(input_frame, selectmode=tk.EXTENDED, height=8)
        self.file_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(input_frame, orient=tk.VERTICAL, command=self.file_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.file_listbox.config(yscrollcommand=scrollbar.set)
        
        # --- Output Section ---
        output_frame = ttk.LabelFrame(main_frame, text="2. Select Output Folder", padding="10")
        output_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.select_output_btn = ttk.Button(output_frame, text="Browse for Folder...", command=self.select_output_dir)
        self.select_output_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        output_label = ttk.Label(output_frame, textvariable=self.output_dir, foreground="blue", wraplength=400)
        output_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.output_dir.set("No output folder selected.")

        # --- Action Section ---
        action_frame = ttk.Frame(main_frame, padding="10")
        action_frame.pack(fill=tk.X, padx=5, pady=10)
        
        self.convert_btn = ttk.Button(action_frame, text="Convert to MP3", command=self.start_conversion_thread)
        self.convert_btn.pack(pady=5)
        
        self.status_label = ttk.Label(action_frame, text="Ready to convert.", font=('Helvetica', 10, 'italic'))
        self.status_label.pack(pady=5)

    def select_files(self):
        """Opens a dialog to select one or more M4A files."""
        # The filetypes tuple restricts the dialog to show only .m4a files
        files = filedialog.askopenfilenames(
            title="Select M4A files",
            filetypes=[("M4A audio files", "*.m4a"), ("All files", "*.*")]
        )
        if files:
            self.input_files = list(files)
            self.file_listbox.delete(0, tk.END) # Clear previous list
            for file_path in self.input_files:
                # Insert just the filename for cleaner display
                self.file_listbox.insert(tk.END, os.path.basename(file_path))
            self.status_label.config(text=f"{len(self.input_files)} file(s) selected.")

    def select_output_dir(self):
        """Opens a dialog to select an output directory."""
        directory = filedialog.askdirectory(title="Select Output Folder")
        if directory:
            self.output_dir.set(directory)

    def start_conversion_thread(self):
        """Starts the conversion process in a separate thread to keep the GUI responsive."""
        # --- Validation Checks ---
        if not self.input_files:
            messagebox.showerror("Error", "No input files selected. Please select M4A files to convert.")
            return
        if self.output_dir.get() == "No output folder selected.":
            messagebox.showerror("Error", "No output folder selected. Please select where to save the MP3s.")
            return
            
        # Disable buttons to prevent multiple clicks during conversion
        self.toggle_buttons(enabled=False)
        self.status_label.config(text="Starting conversion...")
        
        # Run the potentially long conversion task in a new thread
        conversion_thread = threading.Thread(target=self.run_conversion)
        conversion_thread.daemon = True # Allows main window to exit even if thread is running
        conversion_thread.start()

    def run_conversion(self):
        """The core conversion logic that runs in the background."""
        total_files = len(self.input_files)
        for i, file_path in enumerate(self.input_files):
            filename_base = os.path.splitext(os.path.basename(file_path))[0]
            output_path = os.path.join(self.output_dir.get(), f"{filename_base}.mp3")
            
            # Update status in the GUI thread
            self.root.after(0, self.update_status, f"Converting ({i+1}/{total_files}): {filename_base}.m4a")
            
            try:
                # The actual conversion using pydub
                audio = AudioSegment.from_file(file_path, format="m4a")
                audio.export(output_path, format="mp3", bitrate="192k") # You can change bitrate
            except Exception as e:
                # Show error message box in the main GUI thread
                self.root.after(0, messagebox.showerror, "Conversion Error", f"Failed to convert {filename_base}.m4a\n\nError: {e}")
                continue # Skip to the next file

        # Re-enable buttons and show completion message in the GUI thread
        self.root.after(0, self.finish_conversion)

    def update_status(self, message):
        """Safely updates the status label from any thread."""
        self.status_label.config(text=message)

    def finish_conversion(self):
        """Called when the conversion process is complete."""
        self.toggle_buttons(enabled=True)
        self.status_label.config(text="Conversion complete!")
        messagebox.showinfo("Success", "All selected files have been converted successfully!")
        self.file_listbox.delete(0, tk.END) # Clear the list for the next batch
        self.input_files = []


    def toggle_buttons(self, enabled=True):
        """Disables or enables the main control buttons."""
        state = tk.NORMAL if enabled else tk.DISABLED
        self.select_files_btn.config(state=state)
        self.select_output_btn.config(state=state)
        self.convert_btn.config(state=state)


if __name__ == "__main__":
    root = tk.Tk()
    app = M4aToMp3Converter(root)
    root.mainloop()