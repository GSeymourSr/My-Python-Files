import tkinter as tk
from tkinter import filedialog
import os
import shutil
import ast
import subprocess
import sys

def select_file():
    """Prompt the user to select a Python file using a file dialog."""
    root = tk.Tk()
    root.withdraw()  # Hide the main window
    file_path = filedialog.askopenfilename(filetypes=[("Python files", "*.py")])
    return file_path

def is_likely_file_path(s):
    """
    Check if a string likely represents a relative or absolute file path.
    Uses a heuristic: must have a dot in the final part (e.g., file.ext) and no newlines.
    """
    if not s or '\n' in s:
        return False
    normalized_s = s.replace('\\', '/')
    basename = normalized_s.split('/')[-1]
    return ('.' in basename and basename not in ('.', '..'))

def parse_assets(code, original_script_dir):
    """
    Parse the source code using AST to locate string constants that look like file paths.
    Returns a set of asset paths (as found in the code) that exist relative to the original script.
    """
    assets = set()
    try:
        tree = ast.parse(code)
    except Exception as e:
        print("Error parsing the Python code:", e)
        return assets

    for node in ast.walk(tree):
        # Check for both ast.Constant (Python 3.8+) and ast.Str (older versions)
        value = None
        if hasattr(node, 'value') and isinstance(node.value, str):
            value = node.value
        elif isinstance(node, ast.Str):
            value = node.s

        if value and is_likely_file_path(value):
            possible_asset_path = os.path.join(original_script_dir, value)
            if os.path.isfile(possible_asset_path):
                print(f"Identified asset: '{value}' exists.")
                assets.add(value)
            else:
                print(f"Found string '{value}' (missing file), skipping.")

    return assets

def inject_header(code):
    """
    Prepares a header to inject into the Python code.
    This header defines how to resolve asset paths at runtime.
    """
    header_code = f"""
# --- Begin injected asset path handling ---
import sys
import os

if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    base_path = sys._MEIPASS
else:
    base_path = os.path.dirname(os.path.abspath(__file__))

def get_asset_path(relative_path):
    return os.path.join(base_path, relative_path)
# --- End injected asset path handling ---

"""
    return header_code + code

def replace_asset_paths(code, assets, original_script_dir):
    """
    Replace all occurrences of asset file paths in the code with a call to get_asset_path.
    This method creates a mapping from the original asset string literal to the new function call.
    """
    # Prepare the mapping. We resolve each asset to its basename.
    replacement_map = {}
    for asset in assets:
        asset_basename = os.path.basename(os.path.normpath(os.path.join(original_script_dir, asset)))
        # Replacement call must be inserted as a string literal in Python code.
        replacement_call = f"get_asset_path('{asset_basename}')"
        # Consider both single and double quoted versions of the asset string.
        replacement_map[f"'{asset}'"] = replacement_call
        replacement_map[f'"{asset}"'] = replacement_call

    # Process code lines to replace strings that represent asset paths
    modified_lines = []
    for line in code.splitlines(keepends=True):
        modified_line = line
        # Attempt replacement while not altering commented-out code (a simple heuristic: check position before '#')
        comment_index = modified_line.find('#')
        for key, val in sorted(replacement_map.items(), key=lambda item: len(item[0]), reverse=True):
            # Only replace if the asset reference is not within a comment section of the line
            if comment_index == -1 or modified_line.find(key) < comment_index:
                modified_line = modified_line.replace(key, val)
        modified_lines.append(modified_line)
    return "".join(modified_lines)

def main():
    # Step 1: User selects a Python file
    print("Select the main Python script for your application...")
    file_path = select_file()
    if not file_path:
        print("No file selected. Exiting.")
        return

    original_script_dir = os.path.dirname(file_path)
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    safe_base_name = "".join(c for c in base_name if c.isalnum() or c in ('-', '_')) or "output"
    new_dir = safe_base_name + "_bundle"

    if os.path.exists(new_dir):
        print(f"Warning: Directory '{new_dir}' already exists. Files may be overwritten.")
    else:
        os.makedirs(new_dir)
        print(f"Created directory: {new_dir}")

    # Step 2: Copy selected script to the new directory
    script_name = os.path.basename(file_path)
    target_script_path = os.path.join(new_dir, script_name)
    shutil.copy(file_path, target_script_path)
    print(f"Copied script to: {target_script_path}")

    # Read original copied script
    with open(target_script_path, "r", encoding="utf-8") as f:
        original_code = f.read()

    # Step 3: Parse the code to identify and verify asset paths.
    print("Analyzing code for asset references...")
    assets = parse_assets(original_code, original_script_dir)
    print(f"Found {len(assets)} assets: {assets}")

    # Change working directory to the new directory
    os.chdir(new_dir)
    print(f"Changed working directory to: {os.getcwd()}")

    # Step 4: Copy asset files (if they exist) into the new directory.
    copied_assets = set()
    for asset in assets:
        asset_path = os.path.normpath(os.path.join(original_script_dir, asset))
        asset_basename = os.path.basename(asset_path)
        target_asset_path = os.path.join(os.getcwd(), asset_basename)
        if os.path.exists(asset_path):
            try:
                if os.path.isfile(asset_path):
                    shutil.copy(asset_path, target_asset_path)
                    print(f"Copied file asset: {asset_path} -> {target_asset_path}")
                    copied_assets.add(asset_basename)
                elif os.path.isdir(asset_path):
                    shutil.copytree(asset_path, target_asset_path, dirs_exist_ok=True)
                    print(f"Copied directory asset: {asset_path} -> {target_asset_path}")
                    copied_assets.add(asset_basename)
            except Exception as e:
                print(f"Error copying asset '{asset}': {e}")
        else:
            print(f"Asset '{asset}' does not exist at expected location: {asset_path}")

    # Step 5: Inject header for asset path handling and update code with replacements.
    modified_code = replace_asset_paths(original_code, assets, original_script_dir)
    modified_code = inject_header(modified_code)

    with open(script_name, "w", encoding="utf-8") as f:
        f.write(modified_code)
    print("Modified script with asset path handling.")

    # Step 6: Run PyInstaller to build a standalone executable.
    print("Preparing PyInstaller command...")
    # Construct --add-data options
    add_data_options = []
    separator = ';' if sys.platform == 'win32' else ':'
    for asset in copied_assets:
        source_path = os.path.join(os.getcwd(), asset)
        add_data_options.extend(["--add-data", f"{source_path}{separator}{asset}"])

    command = [
        "pyinstaller",
        "--onefile",        # Create a single bundled executable file
        "--distpath=.",     # Place the executable in the current directory
        *add_data_options,  # Include all asset files
        script_name         # The Python script to compile
    ]
    print("Running PyInstaller...")
    print("Command:", " ".join(command))

    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
        print("PyInstaller finished successfully.")
        print("Executable is located in:", os.getcwd())
    except subprocess.CalledProcessError as e:
        print("PyInstaller failed with return code", e.returncode)
        print("Output:", e.stdout)
        print("Error:", e.stderr)
    except FileNotFoundError:
        print("PyInstaller command not found. Make sure PyInstaller is installed and in your system's PATH.")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("An unexpected error occurred:", e)
        import traceback
        traceback.print_exc()
