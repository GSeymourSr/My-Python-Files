import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import shutil
import subprocess
import sys
from pathlib import Path
import threading
import os
import traceback
import time
import atexit
import pathlib

# --- Use correct path separator for --add-data ---
PATH_SEP = ';' if sys.platform == 'win32' else ':'

class SimpleHtmlToExeGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Simple HTML to EXE (Syntax Error FIXED)") # Updated Title
        self.geometry("600x400")
        self.resizable(True, True)

        # Variables
        self.html_path_var = tk.StringVar()
        self.output_name_var = tk.StringVar()
        self.icon_path_var = tk.StringVar()
        self.use_noconsole_var = tk.BooleanVar(value=False) # Keep console visible

        self.log_file_path = None
        self.log_file_handle = None
        atexit.register(self.close_log_file)

        frame = tk.Frame(self, padx=10, pady=10)
        frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(frame, text="Standalone HTML File:").grid(row=0, column=0, sticky="w", pady=2)
        tk.Entry(frame, textvariable=self.html_path_var, width=50).grid(row=0, column=1, padx=5, pady=2, sticky="ew")
        tk.Button(frame, text="Browse...", command=self.select_html).grid(row=0, column=2, padx=2, pady=2)

        tk.Label(frame, text="Output EXE Name:").grid(row=1, column=0, sticky="w", pady=2)
        tk.Entry(frame, textvariable=self.output_name_var, width=30).grid(row=1, column=1, sticky="ew", padx=5, pady=2)

        tk.Label(frame, text="Icon (optional .ico):").grid(row=2, column=0, sticky="w", pady=2)
        tk.Entry(frame, textvariable=self.icon_path_var, width=50).grid(row=2, column=1, padx=5, pady=2, sticky="ew")
        tk.Button(frame, text="Browse...", command=self.select_icon).grid(row=2, column=2, padx=2, pady=2)

        options_frame = tk.Frame(frame)
        options_frame.grid(row=3, column=1, columnspan=2, sticky="w", pady=5)
        tk.Checkbutton(
            options_frame, text="Hide Console Window on Run", variable=self.use_noconsole_var
        ).pack(side=tk.LEFT, padx=5)

        self.build_button = tk.Button(frame, text="Build EXE", command=self.start_build, bg="#007bff", fg="white", width=15)
        self.build_button.grid(row=4, column=1, pady=10, sticky="w", padx=5)

        tk.Label(frame, text="Build Log:").grid(row=5, column=0, sticky="nw", pady=2)
        self.log_box = scrolledtext.ScrolledText(frame, height=10, wrap=tk.WORD)
        self.log_box.grid(row=5, column=1, columnspan=2, pady=(0,5), sticky="nsew")

        frame.grid_columnconfigure(1, weight=1)
        frame.grid_rowconfigure(5, weight=1)

    def close_log_file(self):
        if self.log_file_handle:
            print(f"Closing log file handle for: {self.log_file_path}")
            try: self.log_file_handle.close(); self.log_file_handle = None
            except Exception as e: print(f"Error closing log file: {e}")

    def log(self, message):
        str_message = str(message)
        if self.log_file_handle:
            try: self.log_file_handle.write(str_message + "\n"); self.log_file_handle.flush()
            except Exception as e: print(f"ERROR writing to log file {self.log_file_path}: {e}")
        def _do_log_gui():
            try:
                if self.winfo_exists(): self.log_box.insert(tk.END, str_message + "\n"); self.log_box.see(tk.END); self.update_idletasks()
            except Exception as e_gui: print(f"GUI Logging failed: {e_gui}")
        if self.winfo_exists():
            if threading.current_thread() is threading.main_thread(): _do_log_gui()
            else: self.after(0, _do_log_gui)
        else: print(f"Log (GUI closed): {str_message}")

    def select_html(self):
        path = filedialog.askopenfilename(title="Select Standalone HTML File", filetypes=[("HTML files", "*.html;*.htm")])
        if path: self.html_path_var.set(path);
        if not self.output_name_var.get() and path: self.output_name_var.set(Path(path).stem)

    def select_icon(self):
        path = filedialog.askopenfilename(title="Select Icon File", filetypes=[("Icon files", "*.ico")])
        if path: self.icon_path_var.set(path)

    def start_build(self):
        self.build_button.config(state=tk.DISABLED, text="Building..."); self.update_idletasks()
        self.log_box.delete('1.0', tk.END); print("Starting build thread...")
        thread = threading.Thread(target=self.build, daemon=True); thread.start()

    def _update_button_state(self, enabled, text):
         def _do_update():
            if self.winfo_exists(): self.build_button.config(state=tk.NORMAL if enabled else tk.DISABLED, text=text); self.update_idletasks()
         if self.winfo_exists():
            if threading.current_thread() is threading.main_thread(): _do_update()
            else: self.after(0, _do_update)

    def build(self):
        original_cwd = Path.cwd(); build_successful = False; name = ""; bundle_dir = None; html_path = None
        self.close_log_file()
        try:
            html_path_str = self.html_path_var.get()
            if not html_path_str: messagebox.showerror("Error", "Please select an HTML file."); self._update_button_state(True, "Build EXE"); return
            html_path = Path(html_path_str).resolve()
            if not html_path.is_file(): messagebox.showerror("Error", "Selected HTML file not found or is not a file."); self._update_button_state(True, "Build EXE"); return
            name = self.output_name_var.get().strip() or html_path.stem
            name = "".join(c for c in name if c.isalnum() or c in ('_', '-')).strip() or "output"
            bundle_dir = (html_path.parent / f"{name}_bundle").resolve()
            log_filename = f"{name}_build_log.txt"; self.log_file_path = bundle_dir / log_filename
            bundle_dir.mkdir(parents=True, exist_ok=True); self.log_file_path.unlink(missing_ok=True)
            try:
                self.log_file_handle = open(self.log_file_path, "w", encoding="utf-8", buffering=1); print(f"Opened build log file for writing: {self.log_file_path}")
            except Exception as e:
                print(f"CRITICAL ERROR: Could not open log file {self.log_file_path}: {e}"); messagebox.showerror("Log Error", f"Could not open log file:\n{self.log_file_path}\nError: {e}"); self._update_button_state(True, "Build EXE"); return

            self.log(f"Starting build process log in: {self.log_file_path}")
            self.log(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}"); self.log(f"Python Version: {sys.version}"); self.log(f"Platform: {sys.platform}")
            self.log(f"Original CWD: {original_cwd}"); self.log(f"HTML Path: {html_path}"); self.log(f"Output Name: {name}"); self.log(f"Bundle Directory: {bundle_dir}")
            self.log(f"Cleaning bundle dir (if exists, keeping log file)...")
            try: # Clean bundle dir
                if bundle_dir.exists():
                    for item in bundle_dir.iterdir():
                         if item.resolve() != self.log_file_path.resolve(): self.log(f"  Deleting: {item.name}"); (shutil.rmtree(item) if item.is_dir() else item.unlink())
            except Exception as e_clean: self.log(f"Warning: Error during bundle cleanup: {e_clean}")
            bundle_dir.mkdir(parents=True, exist_ok=True) # Recreate just in case

            target_html_path = bundle_dir / html_path.name # Define target path for copy
            try: # Copy HTML
                 shutil.copy2(html_path, target_html_path); self.log(f"Copied HTML: {html_path.name} to {bundle_dir}")
            except Exception as e_copy:
                 self.log(f"ERROR: Failed to copy HTML file: {e_copy}"); self.log(traceback.format_exc()); messagebox.showerror("File Error", f"Failed to copy HTML file:\n{e_copy}"); return

            # --- Create the launcher script (Ultra-Simple Direct Open + Pause) ---
            launcher_filename = "launcher.py"; launcher_path = bundle_dir / launcher_filename
            self.log(f"Creating launcher (Ultra-Simple Direct Open): {launcher_path}")
            html_filename_only = html_path.name
            escaped_html_filename_only = html_filename_only.replace('\\', '\\\\').replace("'", "\\'")

            launcher_template = '''
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
    print(f"Contents of Base Path ('{{base_path}}'):")
    try: # List contents
        for item in os.listdir(base_path): print(f"  - {{item}}")
    except Exception as e_list: print(f"    Error listing contents: {{e_list}}")

    # --- Calculate paths at RUNTIME ---
    html_file_name_runtime = r'{0}' # Get the simple filename passed via .format()
    print(f"HTML Filename (from build): {{html_file_name_runtime}}")
    path_to_html_abs_runtime = os.path.abspath(os.path.join(base_path, html_file_name_runtime))
    print(f"Absolute Path to HTML (Runtime Calc): {{path_to_html_abs_runtime}}")
    if not os.path.exists(path_to_html_abs_runtime): print(f"*** ERROR: HTML file NOT FOUND at runtime path: {{path_to_html_abs_runtime}} ***"); raise FileNotFoundError(f"Bundled HTML not found: {{path_to_html_abs_runtime}}")

    # --- Try to open the target HTML file URI directly ---
    target_uri_runtime = pathlib.Path(path_to_html_abs_runtime).as_uri(); print(f"Target URI (Runtime Calc): {{target_uri_runtime}}")
    print("\\nAttempting to open TARGET URI directly in web browser...");
    opened = webbrowser.open(target_uri_runtime, new=2); print(f"webbrowser.open call returned: {{opened}}")
    if not opened: print("*** Warning: webbrowser.open returned False/None. Check if browser opened anyway. ***")
    time.sleep(2) # Give browser time to start loading
    print("\\n--- Launcher Script Reached End of Try Block ---")

except Exception as e_runtime:
    print(f"\\n**************** RUNTIME ERROR ****************"); print(f"Error Type: {{type(e_runtime).__name__}}"); print(f"Error Details: {{e_runtime}}"); traceback.print_exc(); exit_code = 1
finally:
    print("\\n--- Launcher Script Reached Finally Block ---"); input("--- Press Enter to close this window ---"); sys.exit(exit_code)
'''
            # Format the main launcher template ONLY with the escaped HTML filename
            launcher_code = launcher_template.format(escaped_html_filename_only) # Pass filename as {0}

            # Write the generated launcher code to file
            try:
                 launcher_path.write_text(launcher_code, encoding='utf-8'); self.log("Launcher script created successfully (Ultra-Simple).")
            except Exception as e_launcher:
                 self.log(f"ERROR: Failed to write launcher script: {e_launcher}"); self.log(traceback.format_exc()); messagebox.showerror("File Error", f"Failed to write launcher script:\n{e_launcher}"); return

            # --- PyInstaller Command Setup ---
            self.log("\nPreparing simplified PyInstaller command...")
            dist_path = bundle_dir / "dist"; build_path = bundle_dir / "build"
            add_data_options = [f"--add-data={html_path.name}{PATH_SEP}."]; self.log(f"Adding data: '{html_path.name}' -> '.' (root)")
            icon_opt = []
            icon_path_str = self.icon_path_var.get()
            if icon_path_str: # ... (icon handling) ...
                 icon_path = Path(icon_path_str).resolve()
                 if icon_path.is_file() and icon_path.suffix.lower() == ".ico":
                     try: icon_target_path = bundle_dir / icon_path.name; shutil.copy2(icon_path, icon_target_path); icon_opt = ["--icon", icon_path.name]; self.log(f"Using icon: {icon_path.name} (Copied)")
                     except Exception as e_icon_copy: self.log(f"Warning: Could not copy icon: {e_icon_copy}")
                 else: self.log(f"Warning: Invalid icon file skipped: {icon_path}")
            console_opt = ["--windowed"] if self.use_noconsole_var.get() else []; self.log(f"Console option: {'--windowed' if console_opt else 'Shown (Default)'}")
            cmd = [ sys.executable, "-m", "PyInstaller", "--noconfirm", "--onefile", "--clean", f"--name={name}", f"--distpath={dist_path}", f"--workpath={build_path}", *console_opt, *icon_opt, *add_data_options, launcher_filename ]

            # --- Run PyInstaller ---
            self.log("\nExecuting PyInstaller...")
            log_cmd = ' '.join(f'"{arg}"' if ' ' in arg else arg for arg in cmd); self.log(f"Command:\n{log_cmd}\n")
            try: os.chdir(bundle_dir); self.log(f"Changed CWD for PyInstaller to: {bundle_dir}")
            except Exception as e_chdir_pyi: self.log(f"ERROR: Failed CWD: {e_chdir_pyi}"); self.log(traceback.format_exc()); messagebox.showerror("Directory Error", f"Failed switch CWD:\n{e_chdir_pyi}"); return
            process = subprocess.run(cmd, check=False, capture_output=True, text=True, encoding='utf-8', errors='replace')

            # --- Log Output & Check Result ---
            self.log("\n--- PyInstaller Execution Log ---")
            stdout_log = process.stdout or ""; stderr_log = process.stderr or ""
            # <<< CORRECTED Logging using separate lines >>>
            if stdout_log:
                self.log(f"--- STDOUT ---\n{stdout_log}")
            else:
                self.log("--- STDOUT (empty) ---")
            if stderr_log:
                self.log(f"--- STDERR ---\n{stderr_log}")
            else:
                self.log("--- STDERR (empty) ---")
            # <<< End of Correction >>>
            self.log(f"--- Return Code: {process.returncode} ---") # Log return code

            final_exe_path = dist_path / (f"{name}.exe" if sys.platform == 'win32' else name)
            if process.returncode == 0 and final_exe_path.exists():
                 self.log(f"\nPyInstaller finished successfully."); self.log(f"Executable created at: {final_exe_path}"); messagebox.showinfo("Success", f"Executable created!\nLocation:\n{final_exe_path}"); build_successful = True
            else:
                 self.log(f"\n--- PyInstaller Failed (Code: {process.returncode}) ---")
                 if not final_exe_path.exists(): self.log("Executable file NOT found.")
                 messagebox.showerror("PyInstaller Error", f"PyInstaller failed (Code: {process.returncode}).\nExecutable NOT created.\n\nCheck log:\n{self.log_file_path}")

        except Exception as e:
             self.log(f"\n--- An Unexpected Build Error Occurred ---"); self.log(traceback.format_exc()); print(traceback.format_exc())
             messagebox.showerror("Build Error", f"An unexpected error occurred:\n{e}\n\nCheck log:\n{self.log_file_path}")
        finally: # --- Cleanup and Reset ---
             if Path.cwd().resolve() != original_cwd.resolve():
                 try:
                     os.chdir(original_cwd)
                     self.log(f"\nChanged back to original directory: {original_cwd}") # Corrected line
                 except Exception as e_chdir_back:
                     self.log(f"Warning: Failed change back CWD: {e_chdir_back}")
             else:
                 self.log(f"\nRemained in original directory: {original_cwd}")
             if build_successful and bundle_dir:
                 self.log("Cleaning up build files (build folder, spec file)..."); shutil.rmtree(bundle_dir / "build", ignore_errors=True); (bundle_dir / f"{name}.spec").unlink(missing_ok=True)
             self._update_button_state(True, "Build EXE"); self.log("Build process finished."); self.close_log_file()

# --- Main execution ---
if __name__ == "__main__":
    print("Starting Simplified HTML Packager (Syntax Error FIXED)...") # Update print
    app = SimpleHtmlToExeGUI()
    app.mainloop()
    print("GUI closed.")