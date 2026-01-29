import tkinter as tk
from tkinter import filedialog, messagebox
import os

def combine_files():
    # 1. Initialize Tkinter and hide the main root window
    root = tk.Tk()
    root.withdraw()

    # 2. Select Multiple Input Files
    print("Opening file selector for input files...")
    input_files = filedialog.askopenfilenames(
        title="Select files to combine",
        filetypes=[("Text/Code files", "*.txt *.py *.js *.html *.css *.json *.md"), ("All files", "*.*")]
    )

    if not input_files:
        print("No files selected. Exiting.")
        return

    # 3. Select Output Destination and Name
    output_path = filedialog.asksaveasfilename(
        title="Save Combined File As",
        defaultextension=".txt",
        initialfile="combined_files.txt",
        filetypes=[("Text file", "*.txt"), ("Markdown file", "*.md"), ("All files", "*.*")]
    )

    if not output_path:
        print("No output location selected. Exiting.")
        return

    # 4. Process and Concatenate
    try:
        with open(output_path, 'w', encoding='utf-8') as outfile:
            for file_path in input_files:
                file_name = os.path.basename(file_path)
                
                # We add a header for each file so the AI knows which file it is reading
                outfile.write(f"\n\n{'='*50}\n")
                outfile.write(f"FILE: {file_name}\n")
                outfile.write(f"{'='*50}\n\n")
                
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as infile:
                        outfile.write(infile.read())
                except Exception as e:
                    outfile.write(f"[Error reading this file: {e}]")
                
        messagebox.showinfo("Success", f"Successfully combined {len(input_files)} files into:\n{output_path}")
        print("Done!")

    except Exception as e:
        messagebox.showerror("Error", f"An error occurred: {e}")

if __name__ == "__main__":
    combine_files()