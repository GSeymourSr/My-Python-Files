import tkinter as tk
from tkinter import filedialog
import subprocess
import os

def select_file():
    root = tk.Tk()
    root.withdraw()  # Hide the root window
    file_path = filedialog.askopenfilename(filetypes=[("Python files", "*.py")])
    return file_path

def convert_to_exe(file_path):
    if file_path:
        # Run PyInstaller to convert the file to an executable
        subprocess.run(["pyinstaller", "--onefile", file_path])
        # Move the executable to the same directory as the Python file
        exe_name = os.path.splitext(os.path.basename(file_path))[0] + ".exe"
        exe_path = os.path.join("dist", exe_name)
        if os.path.exists(exe_path):
            os.rename(exe_path, os.path.join(os.path.dirname(file_path), exe_name))
            print(f"Executable created: {os.path.join(os.path.dirname(file_path), exe_name)}")
        else:
            print("Failed to create executable.")
    else:
        print("No file selected.")

if __name__ == "__main__":
    file_path = select_file()
    convert_to_exe(file_path)
