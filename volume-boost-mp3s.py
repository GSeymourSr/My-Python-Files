import os
import tkinter as tk
from tkinter import filedialog, messagebox
from pydub import AudioSegment

# Core function to increase MP3 volume
def increase_volume(file_path, volume_db, output_path):
    audio = AudioSegment.from_file(file_path, format="mp3")
    louder_audio = audio + volume_db
    louder_audio.export(output_path, format="mp3")

# Triggered when user clicks the "Boost Volume" button
def on_boost_volume():
    try:
        input_path = file_entry.get()
        volume_increase = float(volume_entry.get())
        output_path = output_entry.get()

        if not os.path.exists(input_path):
            messagebox.showerror("Error", "Input MP3 file does not exist.")
            return
        if not output_path:
            messagebox.showerror("Error", "Please select where to save the boosted MP3.")
            return

        increase_volume(input_path, volume_increase, output_path)
        messagebox.showinfo("Success", f"Volume increased by {volume_increase} dB.\nSaved to:\n{output_path}")

    except Exception as e:
        messagebox.showerror("Error", str(e))

# Open file browser to choose an input MP3
def browse_input_file():
    path = filedialog.askopenfilename(filetypes=[("MP3 Files", "*.mp3")])
    if path:
        file_entry.delete(0, tk.END)
        file_entry.insert(0, path)

# Open file browser to choose output file location
def browse_output_file():
    path = filedialog.asksaveasfilename(defaultextension=".mp3", filetypes=[("MP3 Files", "*.mp3")])
    if path:
        output_entry.delete(0, tk.END)
        output_entry.insert(0, path)

# --- GUI Setup ---
root = tk.Tk()
root.title("MP3 Volume Booster")
root.geometry("520x260")
root.resizable(False, False)

# Input MP3 file
tk.Label(root, text="Select MP3 File:").pack(anchor="w", padx=10, pady=(10, 0))
file_frame = tk.Frame(root)
file_frame.pack(fill="x", padx=10)
file_entry = tk.Entry(file_frame)
file_entry.pack(side="left", fill="x", expand=True)
tk.Button(file_frame, text="Browse", command=browse_input_file).pack(side="left", padx=5)

# Volume increase field
tk.Label(root, text="Volume Increase (in dB):").pack(anchor="w", padx=10, pady=(10, 0))
volume_entry = tk.Entry(root)
volume_entry.pack(fill="x", padx=10)
volume_entry.insert(0, "5")  # Default +5 dB

# Output path
tk.Label(root, text="Save Boosted MP3 As:").pack(anchor="w", padx=10, pady=(10, 0))
output_frame = tk.Frame(root)
output_frame.pack(fill="x", padx=10)
output_entry = tk.Entry(output_frame)
output_entry.pack(side="left", fill="x", expand=True)
tk.Button(output_frame, text="Save As", command=browse_output_file).pack(side="left", padx=5)

# Main Boost Volume Button
tk.Button(root, text="🎚️ Boost Volume and Save", command=on_boost_volume,
          bg="#007acc", fg="white", font=("Arial", 12, "bold"), height=2).pack(pady=20)

root.mainloop()
