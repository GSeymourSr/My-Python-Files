import tkinter as tk
from tkinter import filedialog
import os
import shutil
import ast
import subprocess

def select_file():
    """Prompt the user to select a Python file using a file dialog."""
    root = tk.Tk()
    root.withdraw()  # Hide the main window
    file_path = filedialog.askopenfilename(filetypes=[("Python files", "*.py")])
    return file_path

def is_likely_file_path(s):
    """Check if a string likely represents a file path."""
    return ('/' in s or '\\' in s) and '.' in s.split('/')[-1]

def main():
    # Step 1: Prompt user to select a Python file
    file_path = select_file()
    if not file_path:
        print("No file selected.")
        return

    # Step 2: Create a directory named after the Python file (without extension)
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    new_dir = base_name
    os.mkdir(new_dir)

    # Step 3: Copy the selected Python file to the new directory
    script_name = base_name + ".py"
    shutil.copy(file_path, os.path.join(new_dir, script_name))
    os.chdir(new_dir)  # Change to the new directory for subsequent operations

    # Step 4: Read and parse the Python file to identify assets
    with open(script_name, "r") as f:
        code = f.read()

    tree = ast.parse(code)
    assets = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Str):
            s = node.s
            if is_likely_file_path(s):
                assets.append(s)

    # Step 5: Copy identified assets to the new directory
    for asset in assets:
        asset_basename = os.path.basename(asset)
        # Assume asset paths are relative to the original script's directory
        original_asset_path = os.path.join(os.path.dirname(file_path), asset)
        shutil.copy(original_asset_path, asset_basename)

    # Step 6: Update the code with imports and asset path logic
    import_code = """import sys
import os

if getattr(sys, 'frozen', False):
    base_path = sys._MEIPASS
else:
    base_path = os.path.dirname(__file__)

"""
    modified_code = import_code + code

    # Replace asset paths with references to basenames
    for asset in assets:
        asset_basename = os.path.basename(asset)
        new_path = f"os.path.join(base_path, '{asset_basename}')"
        # Handle single or double quotes based on asset content
        if "'" in asset:
            quoted_asset = f'"{asset}"'
        else:
            quoted_asset = f"'{asset}'"
        modified_code = modified_code.replace(quoted_asset, new_path)

    # Write the modified code back to the file
    with open(script_name, "w") as f:
        f.write(modified_code)

    # Step 7: Compile a standalone executable with PyInstaller
    add_data_options = [f"--add-data={os.path.basename(asset)}:." for asset in assets]
    subprocess.run([
        "pyinstaller",
        "--onefile",          # Create a single executable file
        "--distpath=.",       # Place the executable in the current (new) directory
        *add_data_options,    # Include all assets in the bundle
        script_name           # The script to compile
    ])

if __name__ == "__main__":
    main()