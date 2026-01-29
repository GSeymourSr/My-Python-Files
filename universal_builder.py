import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import os
import shutil
import ast
import subprocess
import sys
import threading
import traceback
import time
import pathlib # For HTML URI

# --- Constants ---
PATH_SEP = ';' if sys.platform == 'win32' else ':'

# --- Helper Functions from your scripts (to be defined here) ---

def is_likely_file_path_for_assets(s):
    # From Make-a-EXE.py (the more robust one)
    if not s or '\n' in s:
        return False
    normalized_s = s.replace('\\', '/')
    basename = normalized_s.split('/')[-1]
    return ('.' in basename and basename not in ('.', '..'))

def parse_assets_from_code(code, original_script_dir):
    # From Make-a-EXE.py
    assets = set()
    try:
        tree = ast.parse(code)
    except Exception: # Simplified error handling for brevity
        return assets
    for node in ast.walk(tree):
        value = None
        if hasattr(node, 'value') and isinstance(node.value, str):
            value = node.value
        elif isinstance(node, ast.Str): # Python < 3.8
            value = node.s
        if value and is_likely_file_path_for_assets(value):
            possible_asset_path = os.path.join(original_script_dir, value)
            if os.path.isfile(possible_asset_path) or os.path.isdir(possible_asset_path): # Check for dir too
                assets.add(value)
    return assets

def generate_asset_handler_code():
    # From Make-a-EXE.py (inject_header)
    return f"""
# --- Begin injected asset path handling ---
import sys
import os
if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    _base_path_for_assets = sys._MEIPASS
else:
    _base_path_for_assets = os.path.dirname(os.path.abspath(__file__))
def get_asset_path(relative_path):
    return os.path.join(_base_path_for_assets, relative_path)
# --- End injected asset path handling ---
"""

def modify_code_for_assets(code, assets, original_script_dir):
    # From Make-a-EXE.py (replace_asset_paths)
    header = generate_asset_handler_code()
    modified_code = header + "\n" + code
    
    replacement_map = {}
    for asset in assets:
        asset_basename = os.path.basename(os.path.normpath(os.path.join(original_script_dir, asset)))
        replacement_call = f"get_asset_path('{asset_basename.replace('\\', '\\\\')}')" # Ensure \) are escaped for string literal
        # Create versions with different quotes for matching
        replacement_map[f"'{asset}'"] = replacement_call
        replacement_map[f'"{asset}"'] = replacement_call
        # Potentially raw strings too, though less common for simple assets
        replacement_map[f"r'{asset}'"] = replacement_call 
        replacement_map[f'r"{asset}"'] = replacement_call

    # Apply replacements - process longer strings first to avoid partial replacements
    sorted_keys = sorted(replacement_map.keys(), key=len, reverse=True)
    
    # More robust replacement needed than simple .replace() on whole code
    # This simplified version is for demonstration. AST-based replacement is better.
    # For now, we'll do line-by-line simple replacement which is error-prone
    # but demonstrates the idea.
    
    processed_lines = []
    for line in modified_code.splitlines(keepends=True):
        processed_line = line
        comment_index = processed_line.find('#')
        for original_quoted_asset in sorted_keys:
            # Only replace if the asset reference is not within a comment section of the line
            if comment_index == -1 or processed_line.find(original_quoted_asset) < comment_index:
                 processed_line = processed_line.replace(original_quoted_asset, replacement_map[original_quoted_asset])
        processed_lines.append(processed_line)
    return "".join(processed_lines)


def generate_html_launcher_code(html_filename_in_bundle):
    # From make-exe-html.py (simplified)
    # Ensure html_filename_in_bundle is just the filename, not a path
    escaped_html_filename = html_filename_in_bundle.replace('\\', '\\\\').replace("'", "\\'")
    
    # Using the "Ultra-Simple Direct Open + Pause" launcher from your make-exe-html.py
    # but slightly adapted to fit here.
    return f'''
# -*- coding: utf-8 -*-
# Launcher for HTML - Ultra-Simple Direct Open + Pause
import sys, os, webbrowser, pathlib, time, traceback

print("--- Launcher Script Start (Ultra-Simple) ---")
print(f"Python Executable: {{sys.executable}}"); print(f"Script Arguments: {{sys.argv}}"); print(f"Initial CWD: {{os.getcwd()}}")

exit_code = 0
try: # Main logic wrapped in try block
    base_path = None; running_frozen = False
    try: base_path = sys._MEIPASS; running_frozen = True; print(f"Running Frozen: True / _MEIPASS: {{base_path}}")
    except AttributeError: base_path = os.path.dirname(os.path.abspath(__file__)); running_frozen = False; print(f"Running Frozen: False / Base Path: {{base_path}}")
    if not base_path: print("*** CRITICAL ERROR: Could not determine base path! ***"); raise RuntimeError("Base path not found")

    print(f"Base Path Exists: {{os.path.exists(base_path)}}")
    if not os.path.exists(base_path): print(f"*** ERROR: Base path '{{base_path}}' does not exist! ***"); raise FileNotFoundError("Base path missing")
    
    html_file_name_runtime = r'{escaped_html_filename}' 
    print(f"HTML Filename (from build): {{html_file_name_runtime}}")
    path_to_html_abs_runtime = os.path.abspath(os.path.join(base_path, html_file_name_runtime))
    print(f"Absolute Path to HTML (Runtime Calc): {{path_to_html_abs_runtime}}")
    if not os.path.exists(path_to_html_abs_runtime): print(f"*** ERROR: HTML file NOT FOUND at runtime path: {{path_to_html_abs_runtime}} ***"); raise FileNotFoundError(f"Bundled HTML not found: {{path_to_html_abs_runtime}}")

    target_uri_runtime = pathlib.Path(path_to_html_abs_runtime).as_uri(); print(f"Target URI (Runtime Calc): {{target_uri_runtime}}")
    print("\\nAttempting to open TARGET URI directly in web browser...");
    opened = webbrowser.open(target_uri_runtime, new=2); print(f"webbrowser.open call returned: {{opened}}")
    if not opened: print("*** Warning: webbrowser.open returned False/None. Check if browser opened anyway. ***")
    time.sleep(2) 
    print("\\n--- Launcher Script Reached End of Try Block ---")

except Exception as e_runtime:
    print(f"\\n**************** RUNTIME ERROR ****************"); print(f"Error Type: {{type(e_runtime).__name__}}"); print(f"Error Details: {{e_runtime}}"); traceback.print_exc(); exit_code = 1
finally:
    print("\\n--- Launcher Script Reached Finally Block ---"); input("--- Press Enter to close this window ---"); sys.exit(exit_code)
'''

class UniversalExeBuilderGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Universal EXE Builder")
        self.geometry("700x550")

        self.input_file_path_var = tk.StringVar()
        self.output_name_var = tk.StringVar()
        self.icon_path_var = tk.StringVar()
        self.noconsole_var = tk.BooleanVar(value=False)
        self.build_mode_var = tk.StringVar(value="Python with Assets") # Default mode

        self.log_file_handle = None # For logging to file
        self.current_build_dir = None # To store the path of the _bundle or temp dir

        self._setup_ui()

    def _setup_ui(self):
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- Build Mode Selection ---
        mode_frame = ttk.LabelFrame(main_frame, text="Build Mode")
        mode_frame.pack(fill=tk.X, pady=5)
        
        modes = [
            ("Simple Python EXE", "Simple Python EXE"),
            ("Python EXE with Assets", "Python with Assets"),
            ("HTML to EXE", "HTML to EXE")
        ]
        for text, mode in modes:
            rb = ttk.Radiobutton(mode_frame, text=text, variable=self.build_mode_var, value=mode, command=self._update_ui_for_mode)
            rb.pack(side=tk.LEFT, padx=5, pady=5)

        # --- File Input ---
        file_frame = ttk.LabelFrame(main_frame, text="Input File")
        file_frame.pack(fill=tk.X, pady=5)
        
        self.input_file_label = ttk.Label(file_frame, text="Python Script (*.py):")
        self.input_file_label.pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Entry(file_frame, textvariable=self.input_file_path_var, width=50).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
        ttk.Button(file_frame, text="Browse...", command=self._select_input_file).pack(side=tk.LEFT, padx=5)

        # --- Output Options ---
        options_frame = ttk.LabelFrame(main_frame, text="Output Options")
        options_frame.pack(fill=tk.X, pady=5)

        ttk.Label(options_frame, text="Output EXE Name:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        ttk.Entry(options_frame, textvariable=self.output_name_var, width=30).grid(row=0, column=1, padx=5, pady=5, sticky=tk.EW)
        
        ttk.Label(options_frame, text="Icon (*.ico):").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        ttk.Entry(options_frame, textvariable=self.icon_path_var, width=40).grid(row=1, column=1, padx=5, pady=5, sticky=tk.EW)
        ttk.Button(options_frame, text="Browse...", command=self._select_icon).grid(row=1, column=2, padx=5, pady=5)
        
        ttk.Checkbutton(options_frame, text="Hide Console Window (No Console)", variable=self.noconsole_var).grid(row=2, column=0, columnspan=3, padx=5, pady=5, sticky=tk.W)
        options_frame.columnconfigure(1, weight=1)

        # --- Build Button & Log ---
        self.build_button = ttk.Button(main_frame, text="Build EXE", command=self._start_build_thread)
        self.build_button.pack(pady=10)

        log_frame = ttk.LabelFrame(main_frame, text="Build Log")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        self.log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, height=10)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self._update_ui_for_mode() # Initial UI setup based on default mode

    def _update_ui_for_mode(self):
        mode = self.build_mode_var.get()
        if mode == "HTML to EXE":
            self.input_file_label.config(text="HTML File (*.html, *.htm):")
        else:
            self.input_file_label.config(text="Python Script (*.py):")
        # You can add more UI changes here if needed for different modes

    def _select_input_file(self):
        mode = self.build_mode_var.get()
        if mode == "HTML to EXE":
            filetypes = [("HTML files", "*.html;*.htm"), ("All files", "*.*")]
            title = "Select HTML File"
        else:
            filetypes = [("Python files", "*.py"), ("All files", "*.*")]
            title = "Select Python Script"
            
        path = filedialog.askopenfilename(title=title, filetypes=filetypes)
        if path:
            self.input_file_path_var.set(path)
            if not self.output_name_var.get(): # Auto-fill output name if empty
                self.output_name_var.set(pathlib.Path(path).stem)

    def _select_icon(self):
        path = filedialog.askopenfilename(title="Select Icon File", filetypes=[("Icon files", "*.ico")])
        if path:
            self.icon_path_var.set(path)

    def _log(self, message, to_file=True):
        print(message) # Also print to console for debugging the GUI itself
        msg_with_newline = str(message) + "\n"
        if self.winfo_exists():
            self.log_text.insert(tk.END, msg_with_newline)
            self.log_text.see(tk.END)
            self.update_idletasks() # Force GUI update
        if to_file and self.log_file_handle:
            try:
                self.log_file_handle.write(msg_with_newline)
                self.log_file_handle.flush()
            except Exception as e:
                print(f"Error writing to log file: {e}") # Log this error to console

    def _close_log_file(self):
        if self.log_file_handle:
            self._log("Closing build log file.", to_file=False) # Log to GUI only
            try:
                self.log_file_handle.close()
            except Exception as e:
                print(f"Error closing log file handle: {e}")
            self.log_file_handle = None

    def _start_build_thread(self):
        input_path = self.input_file_path_var.get()
        output_name = self.output_name_var.get()

        if not input_path:
            messagebox.showerror("Error", "Please select an input file.")
            return
        if not output_name:
            messagebox.showerror("Error", "Please specify an output EXE name.")
            return
        
        self.build_button.config(state=tk.DISABLED, text="Building...")
        self.log_text.delete('1.0', tk.END) # Clear previous log
        
        # Prepare log file in the directory of the input file
        input_file_path_obj = pathlib.Path(input_path)
        log_dir = input_file_path_obj.parent
        log_filename = f"{output_name}_build_log_{time.strftime('%Y%m%d-%H%M%S')}.txt"
        self.log_file_path = log_dir / log_filename
        try:
            self._close_log_file() # Close any previous one
            self.log_file_handle = open(self.log_file_path, "w", encoding="utf-8", buffering=1)
            self._log(f"Build log started: {self.log_file_path}", to_file=False)
        except Exception as e:
            messagebox.showerror("Log Error", f"Could not create log file: {self.log_file_path}\n{e}")
            self.log_file_handle = None # Ensure it's None if open failed
            # Don't disable build button yet, but log the error prominently
            self._log(f"CRITICAL: Failed to open log file {self.log_file_path}. Build log will not be saved to file.", to_file=False)


        build_thread = threading.Thread(target=self._execute_build, daemon=True)
        build_thread.start()

    def _execute_build(self):
        original_cwd = os.getcwd()
        build_successful = False
        final_exe_location = None

        try:
            mode = self.build_mode_var.get()
            input_path_str = self.input_file_path_var.get()
            output_name_str = self.output_name_var.get().strip()
            output_name_str = "".join(c for c in output_name_str if c.isalnum() or c in ('_', '-')).strip() or "output"
            
            icon_path_str = self.icon_path_var.get()
            use_noconsole = self.noconsole_var.get()

            input_file_p = pathlib.Path(input_path_str)
            self.current_build_dir = input_file_p.parent / f"{output_name_str}_bundle"
            self.current_build_dir.mkdir(parents=True, exist_ok=True)
            self._log(f"Build Mode: {mode}")
            self._log(f"Input File: {input_path_str}")
            self._log(f"Output Name: {output_name_str}")
            self._log(f"Build Directory: {self.current_build_dir}")

            # --- Clean current_build_dir (optional, but good practice) ---
            # Be careful not to delete the log file if it's inside
            for item in self.current_build_dir.iterdir():
                if item.resolve() != self.log_file_path.resolve(): # Don't delete active log file
                    if item.is_dir():
                        shutil.rmtree(item, ignore_errors=True)
                    else:
                        item.unlink(missing_ok=True)
            self.current_build_dir.mkdir(parents=True, exist_ok=True) # Recreate if deleted

            if mode == "Simple Python EXE":
                build_successful, final_exe_location = self._build_simple_python(input_path_str, output_name_str, icon_path_str, use_noconsole)
            elif mode == "Python with Assets":
                build_successful, final_exe_location = self._build_python_with_assets(input_path_str, output_name_str, icon_path_str, use_noconsole)
            elif mode == "HTML to EXE":
                build_successful, final_exe_location = self._build_html_to_exe(input_path_str, output_name_str, icon_path_str, use_noconsole)
            
            if build_successful and final_exe_location:
                messagebox.showinfo("Success", f"Build successful!\nEXE created at: {final_exe_location}")
            elif not build_successful:
                messagebox.showerror("Build Failed", f"Build failed. Check the log for details:\n{self.log_file_path if self.log_file_handle else '(Log file not opened)'}")

        except Exception as e:
            self._log(f"\n--- UNEXPECTED BUILD ERROR ---")
            self._log(traceback.format_exc())
            messagebox.showerror("Critical Build Error", f"An unexpected error occurred during the build process: {e}\nCheck log.")
        finally:
            if os.getcwd() != original_cwd:
                os.chdir(original_cwd)
                self._log(f"Restored CWD to: {original_cwd}")
            
            # Clean up build directory (spec, build folder) if successful
            if build_successful and self.current_build_dir and (self.current_build_dir / "dist").exists(): # dist will contain the exe
                self._log("Cleaning up temporary build files...")
                shutil.rmtree(self.current_build_dir / "build", ignore_errors=True)
                spec_file = self.current_build_dir / f"{output_name_str}.spec"
                spec_file.unlink(missing_ok=True)
                # Optionally, remove the whole _bundle dir if the EXE was moved out of its "dist"
                # For now, we keep the _bundle/dist/<exe> structure

            if self.winfo_exists():
                self.build_button.config(state=tk.NORMAL, text="Build EXE")
            self._close_log_file()
            self.current_build_dir = None


    def _run_pyinstaller(self, pyinstaller_cmd, target_dir_for_exe_build):
        self._log("\nRunning PyInstaller...")
        self._log(f"Command: {' '.join(pyinstaller_cmd)}")
        original_cwd = os.getcwd()
        try:
            os.chdir(target_dir_for_exe_build) # PyInstaller works best when run from the dir containing the script/spec
            self._log(f"Changed CWD for PyInstaller to: {target_dir_for_exe_build}")
            
            process = subprocess.Popen(pyinstaller_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='replace', bufsize=1)
            
            self._log("\n--- PyInstaller Output ---")
            # Stream stdout
            if process.stdout:
                for line in iter(process.stdout.readline, ''):
                    self._log(line.strip())
                process.stdout.close()
            
            # Stream stderr
            if process.stderr:
                for line in iter(process.stderr.readline, ''):
                    self._log(f"ERR: {line.strip()}") # Prefix stderr lines
                process.stderr.close()

            return_code = process.wait() # Wait for the process to complete
            self._log(f"--- PyInstaller Return Code: {return_code} ---")
            return return_code == 0
        except FileNotFoundError:
            self._log("ERROR: PyInstaller command not found. Make sure PyInstaller is installed and in your system's PATH.")
            return False
        except Exception as e:
            self._log(f"Error during PyInstaller execution: {e}")
            self._log(traceback.format_exc())
            return False
        finally:
            if os.getcwd() != original_cwd:
                 os.chdir(original_cwd) # Change back CWD
                 self._log(f"Restored CWD from PyInstaller run: {original_cwd}")


    def _build_simple_python(self, script_path_str, exe_name, icon_path_str, noconsole):
        self._log(f"\n--- Starting Simple Python EXE Build ---")
        script_path = pathlib.Path(script_path_str)
        
        # PyInstaller expects the script to be in the CWD or specified with full path
        # For simplicity, we can let PyInstaller run from the script's directory or our bundle dir
        # Let's use the current_build_dir as the base for PyInstaller work, and copy script there.
        
        target_script_in_bundle = self.current_build_dir / script_path.name
        shutil.copy2(script_path, target_script_in_bundle)
        self._log(f"Copied script to build directory: {target_script_in_bundle}")

        cmd = ["pyinstaller", "--noconfirm", "--onefile", f"--name={exe_name}"]
        if noconsole: cmd.append("--windowed")
        if icon_path_str and pathlib.Path(icon_path_str).is_file():
            # Copy icon to bundle dir so PyInstaller can find it easily with just name
            icon_p = pathlib.Path(icon_path_str)
            target_icon_in_bundle = self.current_build_dir / icon_p.name
            shutil.copy2(icon_p, target_icon_in_bundle)
            cmd.extend(["--icon", target_icon_in_bundle.name]) # Use name relative to CWD (bundle dir)
        
        cmd.append(target_script_in_bundle.name) # Script name relative to CWD (bundle dir)

        # PyInstaller will create 'dist' and 'build' folders inside self.current_build_dir
        # We tell it to put the final exe in self.current_build_dir/dist
        cmd.extend([f"--distpath={self.current_build_dir / 'dist'}", f"--workpath={self.current_build_dir / 'build'}"])

        success = self._run_pyinstaller(cmd, self.current_build_dir)
        final_exe_path = self.current_build_dir / "dist" / (f"{exe_name}.exe" if sys.platform == "win32" else exe_name)
        
        if success and final_exe_path.exists():
            self._log(f"Simple Python EXE build successful. Output: {final_exe_path}")
            return True, final_exe_path
        else:
            self._log(f"Simple Python EXE build failed.")
            if not final_exe_path.exists(): self._log("Executable not found at expected location.")
            return False, None


    def _build_python_with_assets(self, script_path_str, exe_name, icon_path_str, noconsole):
        self._log(f"\n--- Starting Python EXE with Assets Build ---")
        original_script_path = pathlib.Path(script_path_str)
        original_script_dir = original_script_path.parent
        
        # 1. Copy script to bundle directory
        target_script_name = original_script_path.name
        target_script_in_bundle = self.current_build_dir / target_script_name
        shutil.copy2(original_script_path, target_script_in_bundle)
        self._log(f"Copied script to build directory: {target_script_in_bundle}")

        # 2. Parse for assets from the original script content
        with open(original_script_path, "r", encoding="utf-8") as f:
            original_code = f.read()
        
        self._log("Parsing script for assets...")
        # Use original_script_dir to resolve relative paths found in code
        found_assets_relative_to_script = parse_assets_from_code(original_code, original_script_dir) 
        self._log(f"Found {len(found_assets_relative_to_script)} potential asset string(s): {found_assets_relative_to_script}")

        # 3. Copy assets to bundle directory and prepare --add-data
        pyinstaller_add_data = []
        copied_asset_basenames = set()

        if found_assets_relative_to_script:
            self._log("Copying assets to build directory...")
            for asset_str_in_code in found_assets_relative_to_script:
                # Resolve full path of the asset from original script location
                actual_asset_path = (original_script_dir / asset_str_in_code).resolve()
                asset_basename = actual_asset_path.name
                
                target_asset_in_bundle = self.current_build_dir / asset_basename

                if actual_asset_path.exists():
                    if actual_asset_path.is_file():
                        shutil.copy2(actual_asset_path, target_asset_in_bundle)
                        self._log(f"  Copied FILE: {asset_str_in_code} -> {target_asset_in_bundle.name}")
                    elif actual_asset_path.is_dir():
                        shutil.copytree(actual_asset_path, target_asset_in_bundle, dirs_exist_ok=True)
                        self._log(f"  Copied DIR: {asset_str_in_code} -> {target_asset_in_bundle.name}")
                    else:
                        self._log(f"  Skipped (not file/dir): {asset_str_in_code}")
                        continue
                    
                    # For PyInstaller, source is the asset in bundle dir, dest is its name in _MEIPASS root
                    # Source path for --add-data should be relative to where pyinstaller is run (current_build_dir)
                    # or absolute. Using basename which is now in current_build_dir.
                    pyinstaller_add_data.extend(["--add-data", f"{asset_basename}{PATH_SEP}."]) # '.' means bundle root
                    copied_asset_basenames.add(asset_basename) # Track for code modification
                else:
                    self._log(f"  Asset NOT FOUND (skipping): {asset_str_in_code} (resolved to {actual_asset_path})")
        else:
            self._log("No assets found or specified to copy.")

        # 4. Modify the copied script in bundle_dir to use get_asset_path
        self._log("Modifying script for asset handling...")
        # Read the script we copied into the bundle dir
        with open(target_script_in_bundle, "r", encoding="utf-8") as f:
            code_to_modify = f.read()
        
        # The `assets` argument to `modify_code_for_assets` should be the original strings found in the code
        # that were successfully copied.
        # `original_script_dir` is used by `modify_code_for_assets` to correctly derive basenames
        # for the `get_asset_path()` calls.
        modified_code = modify_code_for_assets(code_to_modify, found_assets_relative_to_script, original_script_dir)
        
        with open(target_script_in_bundle, "w", encoding="utf-8") as f:
            f.write(modified_code)
        self._log("Script modification complete.")

        # 5. Run PyInstaller
        cmd = ["pyinstaller", "--noconfirm", "--onefile", f"--name={exe_name}"]
        if noconsole: cmd.append("--windowed")
        if icon_path_str and pathlib.Path(icon_path_str).is_file():
            icon_p = pathlib.Path(icon_path_str)
            target_icon_in_bundle = self.current_build_dir / icon_p.name
            shutil.copy2(icon_p, target_icon_in_bundle)
            cmd.extend(["--icon", target_icon_in_bundle.name])
        
        cmd.extend(pyinstaller_add_data)
        cmd.append(target_script_name) # The modified script in current_build_dir
        cmd.extend([f"--distpath={self.current_build_dir / 'dist'}", f"--workpath={self.current_build_dir / 'build'}"])

        success = self._run_pyinstaller(cmd, self.current_build_dir)
        final_exe_path = self.current_build_dir / "dist" / (f"{exe_name}.exe" if sys.platform == "win32" else exe_name)

        if success and final_exe_path.exists():
            self._log(f"Python with Assets EXE build successful. Output: {final_exe_path}")
            return True, final_exe_path
        else:
            self._log(f"Python with Assets EXE build failed.")
            if not final_exe_path.exists(): self._log("Executable not found at expected location.")
            return False, None


    def _build_html_to_exe(self, html_path_str, exe_name, icon_path_str, noconsole):
        self._log(f"\n--- Starting HTML to EXE Build ---")
        original_html_path = pathlib.Path(html_path_str)

        # 1. Copy HTML to bundle directory
        html_basename_in_bundle = original_html_path.name
        target_html_in_bundle = self.current_build_dir / html_basename_in_bundle
        shutil.copy2(original_html_path, target_html_in_bundle)
        self._log(f"Copied HTML file to: {target_html_in_bundle}")

        # 2. Generate Python launcher script
        launcher_script_name = f"{exe_name}_launcher.py"
        launcher_script_path_in_bundle = self.current_build_dir / launcher_script_name
        launcher_code = generate_html_launcher_code(html_basename_in_bundle) # Pass only basename
        with open(launcher_script_path_in_bundle, "w", encoding="utf-8") as f:
            f.write(launcher_code)
        self._log(f"Generated launcher script: {launcher_script_path_in_bundle}")

        # 3. Run PyInstaller on the launcher script
        cmd = ["pyinstaller", "--noconfirm", "--onefile", f"--name={exe_name}"]
        if noconsole: cmd.append("--windowed") # Important for HTML wrappers
        if icon_path_str and pathlib.Path(icon_path_str).is_file():
            icon_p = pathlib.Path(icon_path_str)
            target_icon_in_bundle = self.current_build_dir / icon_p.name
            shutil.copy2(icon_p, target_icon_in_bundle)
            cmd.extend(["--icon", target_icon_in_bundle.name])
        
        # Add the HTML file itself as data, to be placed in the root of _MEIPASS
        # Source path is relative to CWD (bundle dir)
        cmd.extend(["--add-data", f"{html_basename_in_bundle}{PATH_SEP}."])
        cmd.append(launcher_script_name) # Launcher script in current_build_dir
        cmd.extend([f"--distpath={self.current_build_dir / 'dist'}", f"--workpath={self.current_build_dir / 'build'}"])

        success = self._run_pyinstaller(cmd, self.current_build_dir)
        final_exe_path = self.current_build_dir / "dist" / (f"{exe_name}.exe" if sys.platform == "win32" else exe_name)

        if success and final_exe_path.exists():
            self._log(f"HTML to EXE build successful. Output: {final_exe_path}")
            return True, final_exe_path
        else:
            self._log(f"HTML to EXE build failed.")
            if not final_exe_path.exists(): self._log("Executable not found at expected location.")
            return False, None


if __name__ == "__main__":
    app = UniversalExeBuilderGUI()
    app.mainloop()