import tkinter as tk
from tkinter import filedialog
import os
import shutil
import ast
import subprocess
import sys # Import sys

def select_file():
    """Prompt the user to select a Python file using a file dialog."""
    root = tk.Tk()
    root.withdraw()  # Hide the main window
    file_path = filedialog.askopenfilename(filetypes=[("Python files", "*.py")])
    return file_path

def is_likely_file_path(s):
    """
    Check if a string likely represents a relative or absolute file path
    intended to be used as an asset.
    """
    # Rule out empty strings, None, or strings containing newlines
    if not s or '\n' in s:
        return False

    # Check for common path separators
    has_sep = '/' in s or '\\' in s

    # Normalize separators for easier splitting
    normalized_s = s.replace('\\', '/')

    # Check if it looks like an absolute path (Windows or Unix-like)
    is_abs = os.path.isabs(s)

    # Get the potential filename part
    basename = normalized_s.split('/')[-1]

    # Check if the basename contains a dot (likely extension)
    # and isn't just "." or ".."
    has_dot_in_basename = '.' in basename and basename not in ('.', '..')

    # Heuristic:
    # - Must have a dot in the filename part.
    # - Must either contain a path separator OR be a simple filename
    #   (intended to be relative to the script). Allow simple filenames too.
    # - We already excluded newlines.
    if not has_dot_in_basename:
        return False

    # Consider it likely if it has a separator or if it's just a filename
    # with an extension (no separator needed for relative paths in the same dir).
    # Example: "image.png" is valid, "path/to/image.png" is valid.
    return True # Simplified: if it has a dot in basename and no newline, assume it might be an asset path


def main():
    # Step 1: Prompt user to select a Python file
    print("Please select the main Python script for your application...")
    file_path = select_file()
    if not file_path:
        print("No file selected. Exiting.")
        return

    print(f"Selected script: {file_path}")
    original_script_dir = os.path.dirname(file_path)

    # Step 2: Create a directory named after the Python file (without extension)
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    # Sanitize base_name to be a valid directory name if needed (optional)
    safe_base_name = "".join(c for c in base_name if c.isalnum() or c in ('-', '_')).rstrip()
    if not safe_base_name:
        safe_base_name = "output" # Default if name becomes empty
    new_dir = safe_base_name + "_standalone" # Make dir name more descriptive

    if os.path.exists(new_dir):
        print(f"Warning: Directory '{new_dir}' already exists. Files might be overwritten.")
    else:
        os.makedirs(new_dir)
        print(f"Created directory: {new_dir}")

    # Step 3: Copy the selected Python file to the new directory
    script_name_in_new_dir = os.path.basename(file_path) # Keep original script name
    target_script_path = os.path.join(new_dir, script_name_in_new_dir)
    shutil.copy(file_path, target_script_path)
    print(f"Copied script to: {target_script_path}")

    # --- Change working directory AFTER finding assets relative to original script ---
    # os.chdir(new_dir) # <-- Move this later

    # Step 4: Read and parse the Python file to identify assets
    print("Parsing script to find potential asset files...")
    with open(target_script_path, "r", encoding='utf-8') as f: # Specify encoding
        code = f.read()

    tree = ast.parse(code)
    assets = set() # Use a set to avoid duplicates
    for node in ast.walk(tree):
        # Updated for Python 3.8+ (Handles Str deprecation)
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            s = node.value # Use node.value instead of node.s
            if is_likely_file_path(s):
                # Crucially, resolve the path relative to the ORIGINAL script directory
                possible_asset_path = os.path.join(original_script_dir, s)
                # Check if the potential asset actually exists before adding
                if os.path.isfile(possible_asset_path):
                    print(f"  Identified potential asset: '{s}' -> Exists: True")
                    assets.add(s) # Store the original string found in the code
                # Optional: Add a check for directories too if needed
                # elif os.path.isdir(possible_asset_path):
                #     print(f"  Identified potential asset directory: '{s}' -> Exists: True")
                #     assets.add(s) # Handle directories differently if needed
                else:
                     print(f"  Identified potential asset: '{s}' -> Exists: False (Skipping)")


    print(f"\nFound {len(assets)} unique potential asset(s):")
    for asset in assets:
        print(f"- {asset}")

    # --- Now change working directory ---
    os.chdir(new_dir)
    print(f"Changed working directory to: {os.getcwd()}")


    # Step 5: Copy identified assets to the new directory
    copied_assets_basenames = set()
    if assets:
        print("\nCopying assets...")
        for asset_string_from_code in assets:
            # Important: Resolve path relative to the ORIGINAL script location
            original_asset_path = os.path.normpath(os.path.join(original_script_dir, asset_string_from_code))
            asset_basename = os.path.basename(original_asset_path)

            if not os.path.exists(original_asset_path):
                 print(f"  Warning: Asset '{asset_string_from_code}' resolved to '{original_asset_path}' which does not exist. Skipping copy.")
                 continue

            target_asset_path = os.path.join(os.getcwd(), asset_basename) # Target is CWD (the new dir)

            try:
                if os.path.isfile(original_asset_path):
                    print(f"  Copying file: '{original_asset_path}' -> '{target_asset_path}'")
                    shutil.copy(original_asset_path, target_asset_path)
                    copied_assets_basenames.add(asset_basename)
                elif os.path.isdir(original_asset_path):
                     print(f"  Copying directory: '{original_asset_path}' -> '{target_asset_path}'")
                     shutil.copytree(original_asset_path, target_asset_path, dirs_exist_ok=True) # Allows overwriting
                     copied_assets_basenames.add(asset_basename) # Add dir basename
                else:
                    print(f"  Warning: '{original_asset_path}' is not a file or directory. Skipping.")

            except Exception as e:
                print(f"  Error copying '{original_asset_path}': {e}")
    else:
        print("\nNo assets to copy.")


    # Step 6: Update the code with imports and asset path logic
    print("\nModifying script to handle asset paths correctly...")
    # Use the script path inside the new directory
    script_to_modify = script_name_in_new_dir # We are already in new_dir

    with open(script_to_modify, "r", encoding='utf-8') as f:
        original_code_lines = f.readlines()

    # Prepare the header code
    header_code = f"""
# --- Start of code added by make-exe-standalone.py ---
import sys
import os

# Determine the base path for assets depending on whether running as a script or frozen executable
if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    # Running as a bundled executable (PyInstaller)
    base_path = sys._MEIPASS
else:
    # Running as a normal script
    base_path = os.path.dirname(os.path.abspath(__file__))

def get_asset_path(relative_path):
    # Joins the base_path with the relative path of the asset
    return os.path.join(base_path, relative_path)
# --- End of code added by make-exe-standalone.py ---

"""

    modified_code = header_code

    # Process original code line by line
    lines_to_write = []
    asset_replacements = {asset_str: os.path.basename(os.path.normpath(os.path.join(original_script_dir, asset_str))) for asset_str in assets}

    # Generate replacements mapping original string literal to get_asset_path call
    replacement_map = {}
    for original_asset_str, asset_base in asset_replacements.items():
        # Need to handle quotes carefully in the replacement target
        escaped_basename = asset_base.replace('\\', '\\\\').replace("'", "\\'")
        replacement_call = f"get_asset_path('{escaped_basename}')"

        # Create versions with different quotes for matching
        quoted_versions = [f"'{original_asset_str}'", f'"{original_asset_str}"']
        for qv in quoted_versions:
            replacement_map[qv] = replacement_call

    # Add the original code, performing replacements
    for line in original_code_lines:
        modified_line = line
        # Apply replacements - process longer strings first to avoid partial replacements
        # Sort keys by length descending
        sorted_keys = sorted(replacement_map.keys(), key=len, reverse=True)
        for original_quoted_asset in sorted_keys:
            if original_quoted_asset in modified_line:
                 # Basic check to avoid replacing within comments (imperfect)
                 comment_start = modified_line.find('#')
                 if comment_start == -1 or modified_line.find(original_quoted_asset) < comment_start:
                      modified_line = modified_line.replace(original_quoted_asset, replacement_map[original_quoted_asset])

        lines_to_write.append(modified_line)


    # Write the modified code back to the file
    with open(script_to_modify, "w", encoding='utf-8') as f:
        f.writelines(lines_to_write)
    print("Script modification complete.")


    # Step 7: Compile a standalone executable with PyInstaller
    if copied_assets_basenames:
        print("\nPreparing PyInstaller command...")
        # We only need to add data for assets actually copied
        # Format: --add-data "source_in_new_dir;destination_in_bundle"
        # Use '.' for destination to place assets in the root alongside the exe in _MEIPASS
        add_data_options = []
        for asset_base in copied_assets_basenames:
             source_path = os.path.join(os.getcwd(), asset_base) # Asset path in the build directory
             destination = asset_base # Destination relative to bundle root
             # PyInstaller uses ';' as separator on Windows, ':' on Unix
             separator = ';' if sys.platform == 'win32' else ':'
             add_data_options.extend(["--add-data", f"{source_path}{separator}{destination}"])


        command = [
            "pyinstaller",
            "--onefile",          # Create a single executable file
            "--distpath=.",       # Place the executable in the current (new) directory
            # Optional: Add --windowed or --noconsole if it's a GUI app
            # Optional: Add --name="YourAppName"
            *add_data_options,    # Include all assets in the bundle
            script_to_modify      # The script to compile (already in cwd)
        ]

        print("\nRunning PyInstaller...")
        print(f"Command: {' '.join(command)}") # Print the command for debugging
        try:
            subprocess.run(command, check=True, capture_output=True, text=True) # Use check=True to raise error on failure
            print("\nPyInstaller finished successfully.")
            print(f"Executable should be in: {os.getcwd()}")
        except subprocess.CalledProcessError as e:
             print("\n--- PyInstaller Failed ---")
             print(f"Return Code: {e.returncode}")
             print("--- STDOUT ---")
             print(e.stdout)
             print("--- STDERR ---")
             print(e.stderr)
             print("--------------------------")
        except FileNotFoundError:
             print("\nError: 'pyinstaller' command not found.")
             print("Please ensure PyInstaller is installed (pip install pyinstaller) and in your system's PATH.")

    else:
        print("\nSkipping PyInstaller step as no assets were copied.")
        print("You can run PyInstaller manually if needed:")
        print(f"cd \"{os.getcwd()}\"")
        print(f"pyinstaller --onefile --distpath=. {script_to_modify}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Optional: Pause at the end to see output before console closes
        # input("\nPress Enter to exit...")
        pass