import tkinter as tk
from tkinter import filedialog, colorchooser, messagebox
import customtkinter as ctk
import os
import webbrowser
import subprocess # To run python scripts from the GUI
import sys # To find python executable

# --- Configuration ---
ctk.set_appearance_mode("System")  # Modes: "System" (default), "Dark", "Light"
ctk.set_default_color_theme("blue") # Themes: "blue" (default), "green", "dark-blue"

AVAILABLE_FONTS = ["Arial", "Helvetica", "Verdana", "Tahoma", "Trebuchet MS",
                   "Times New Roman", "Georgia", "Garamond",
                   "Courier New", "Lucida Console", "Monaco",
                   "Comic Sans MS", "Impact", # Use with caution ;)
                   "'Segoe UI'", # Good default on Windows
                   "sans-serif"] # Generic fallback

BUTTON_SHAPES = {
    "Rectangle": "0px",
    "Rounded": "8px",
    "Pill": "50px"
    # "Circle" is hard without fixed size, omitting for individual buttons
}

HOVER_EFFECTS = {
    "None": "",
    "Lighten": "filter: brightness(1.2);",
    "Darken": "filter: brightness(0.85);",
    "Grow": "transform: scale(1.05);",
    "Shrink": "transform: scale(0.95);",
    "Pop Up": "transform: translateY(-3px); box-shadow: 0 4px 8px rgba(0,0,0,0.2);",
    "Pop Down": "transform: translateY(2px);",
    "Rotate": "transform: rotate(5deg) scale(1.02);"
}

# --- Helper Functions ---
def get_unique_css_class(base_name, index):
    """Creates a unique CSS class name."""
    return f"{base_name}-{index}"

def get_python_executable():
    """Gets the path to the current Python executable."""
    return sys.executable

# --- Main Application Class ---
class HtmlMenuApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("HTML Menu Generator")
        self.geometry("900x700")

        self.buttons_config = [] # List to hold config dict for each button
        self.selected_button_index = None
        self.python_executable = get_python_executable()

        # --- Configure grid layout (2x2) ---
        self.grid_columnconfigure(0, weight=1) # File list area
        self.grid_columnconfigure(1, weight=2) # Customization area
        self.grid_rowconfigure(0, weight=1)    # Main content row
        self.grid_rowconfigure(1, weight=0)    # Action button row

        # --- Left Frame: File List and Management ---
        self.left_frame = ctk.CTkFrame(self, corner_radius=5)
        self.left_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        self.left_frame.grid_rowconfigure(1, weight=1) # Make listbox expand
        self.left_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self.left_frame, text="Menu Items (Files)").grid(row=0, column=0, columnspan=3, pady=(5,0))

        self.file_listbox = tk.Listbox(self.left_frame, selectmode=tk.SINGLE, exportselection=False,
                                      bg="#333333", fg="white", # Basic styling for listbox
                                      selectbackground="#555555", borderwidth=0,
                                      highlightthickness=0)
        self.file_listbox.grid(row=1, column=0, columnspan=3, sticky="nsew", padx=5, pady=5)
        self.file_listbox.bind("<<ListboxSelect>>", self.on_listbox_select)

        self.add_button = ctk.CTkButton(self.left_frame, text="Add File(s)", command=self.add_files)
        self.add_button.grid(row=2, column=0, padx=5, pady=5, sticky="ew")

        self.remove_button = ctk.CTkButton(self.left_frame, text="Remove Selected", command=self.remove_selected_file, state="disabled")
        self.remove_button.grid(row=2, column=1, padx=5, pady=5, sticky="ew")

        self.run_script_button = ctk.CTkButton(
            self.left_frame, text="Run Selected Script (.py)",
            command=self.run_selected_script, state="disabled"
        )
        self.run_script_button.grid(row=3, column=0, columnspan=2, padx=5, pady=5, sticky="ew")
        self.info_label_run = ctk.CTkLabel(self.left_frame, text="(Runs script from this app, not HTML)", text_color="gray", font=ctk.CTkFont(size=10))
        self.info_label_run.grid(row=4, column=0, columnspan=2, pady=(0,5))

        # --- Right Frame: Customization Options ---
        self.right_frame = ctk.CTkFrame(self, corner_radius=5)
        self.right_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        self.right_frame.grid_columnconfigure(1, weight=1) # Make entry widgets expand slightly

        # --- Global Settings Section ---
        self.global_label = ctk.CTkLabel(self.right_frame, text="Global Page Settings", font=ctk.CTkFont(weight="bold"))
        self.global_label.grid(row=0, column=0, columnspan=3, pady=10, sticky="w", padx=10)

        ctk.CTkLabel(self.right_frame, text="Page Title:").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.page_title_entry = ctk.CTkEntry(self.right_frame, placeholder_text="My Awesome Menu")
        self.page_title_entry.grid(row=1, column=1, columnspan=2, padx=10, pady=5, sticky="ew")
        self.page_title_entry.insert(0, "My File Menu")

        ctk.CTkLabel(self.right_frame, text="Page BG:").grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.page_bg_color_button = ctk.CTkButton(self.right_frame, text="Choose Color", width=120, command=self.choose_page_bg_color)
        self.page_bg_color_button.grid(row=2, column=1, padx=5, pady=5, sticky="w")
        self.page_bg_color_preview = ctk.CTkFrame(self.right_frame, width=30, height=30, fg_color="#f0f0f0", border_width=1, border_color="gray")
        self.page_bg_color_preview.grid(row=2, column=2, padx=5, pady=5, sticky="w")
        self.page_bg_color = "#f0f0f0" # Default

        # --- Individual Button Settings Section (Initially hidden/disabled) ---
        self.button_settings_label = ctk.CTkLabel(self.right_frame, text="Selected Button Settings", font=ctk.CTkFont(weight="bold"))
        self.button_settings_label.grid(row=4, column=0, columnspan=3, pady=(20, 10), sticky="w", padx=10)

        # Display Name
        ctk.CTkLabel(self.right_frame, text="Display Name:").grid(row=5, column=0, padx=10, pady=5, sticky="w")
        self.display_name_entry = ctk.CTkEntry(self.right_frame, state="disabled")
        self.display_name_entry.grid(row=5, column=1, columnspan=2, padx=10, pady=5, sticky="ew")
        self.display_name_entry.bind("<KeyRelease>", self.update_button_config_from_ui) # Update on typing


        # --- Button Shape ---
        ctk.CTkLabel(self.right_frame, text="Shape:").grid(row=6, column=0, padx=10, pady=5, sticky="w")
        self.shape_frame = ctk.CTkFrame(self.right_frame, fg_color="transparent")
        self.shape_frame.grid(row=6, column=1, columnspan=2, padx=5, pady=5, sticky="w")
        self.shape_var = ctk.StringVar(value=list(BUTTON_SHAPES.keys())[0])
        col = 0
        for shape_name in BUTTON_SHAPES.keys():
            rb = ctk.CTkRadioButton(self.shape_frame, text=shape_name, variable=self.shape_var, value=shape_name,
                                    command=self.update_button_config_from_ui, state="disabled")
            rb.grid(row=0, column=col, padx=5, pady=2, sticky="w")
            col += 1

        # --- Button Colors ---
        ctk.CTkLabel(self.right_frame, text="Button BG:").grid(row=7, column=0, padx=10, pady=5, sticky="w")
        self.button_bg_color_button = ctk.CTkButton(self.right_frame, text="Choose", width=80, command=lambda: self.choose_button_color('bg_color'), state="disabled")
        self.button_bg_color_button.grid(row=7, column=1, padx=5, pady=5, sticky="w")
        self.button_bg_color_preview = ctk.CTkFrame(self.right_frame, width=30, height=30, fg_color="gray", border_width=1, border_color="gray")
        self.button_bg_color_preview.grid(row=7, column=2, padx=5, pady=5, sticky="w")

        ctk.CTkLabel(self.right_frame, text="Button Text:").grid(row=8, column=0, padx=10, pady=5, sticky="w")
        self.button_text_color_button = ctk.CTkButton(self.right_frame, text="Choose", width=80, command=lambda: self.choose_button_color('text_color'), state="disabled")
        self.button_text_color_button.grid(row=8, column=1, padx=5, pady=5, sticky="w")
        self.button_text_color_preview = ctk.CTkFrame(self.right_frame, width=30, height=30, fg_color="gray", border_width=1, border_color="gray")
        self.button_text_color_preview.grid(row=8, column=2, padx=5, pady=5, sticky="w")

        ctk.CTkLabel(self.right_frame, text="Hover BG:").grid(row=9, column=0, padx=10, pady=5, sticky="w")
        self.button_hover_bg_color_button = ctk.CTkButton(self.right_frame, text="Choose", width=80, command=lambda: self.choose_button_color('hover_bg_color'), state="disabled")
        self.button_hover_bg_color_button.grid(row=9, column=1, padx=5, pady=5, sticky="w")
        self.button_hover_bg_color_preview = ctk.CTkFrame(self.right_frame, width=30, height=30, fg_color="gray", border_width=1, border_color="gray")
        self.button_hover_bg_color_preview.grid(row=9, column=2, padx=5, pady=5, sticky="w")

        ctk.CTkLabel(self.right_frame, text="Hover Text:").grid(row=10, column=0, padx=10, pady=5, sticky="w")
        self.button_hover_text_color_button = ctk.CTkButton(self.right_frame, text="Choose", width=80, command=lambda: self.choose_button_color('hover_text_color'), state="disabled")
        self.button_hover_text_color_button.grid(row=10, column=1, padx=5, pady=5, sticky="w")
        self.button_hover_text_color_preview = ctk.CTkFrame(self.right_frame, width=30, height=30, fg_color="gray", border_width=1, border_color="gray")
        self.button_hover_text_color_preview.grid(row=10, column=2, padx=5, pady=5, sticky="w")

        # --- Font Selection ---
        ctk.CTkLabel(self.right_frame, text="Font:").grid(row=11, column=0, padx=10, pady=5, sticky="w")
        self.font_combobox = ctk.CTkComboBox(self.right_frame, values=AVAILABLE_FONTS,
                                             command=self.update_button_config_from_ui, state="disabled")
        self.font_combobox.grid(row=11, column=1, columnspan=2, padx=10, pady=5, sticky="ew")
        self.font_combobox.set(AVAILABLE_FONTS[-1]) # Default to sans-serif

        # --- Hover Effect ---
        ctk.CTkLabel(self.right_frame, text="Hover Effect:").grid(row=12, column=0, padx=10, pady=5, sticky="w")
        self.hover_effect_combobox = ctk.CTkComboBox(self.right_frame, values=list(HOVER_EFFECTS.keys()),
                                                     command=self.update_button_config_from_ui, state="disabled")
        self.hover_effect_combobox.grid(row=12, column=1, columnspan=2, padx=10, pady=5, sticky="ew")
        self.hover_effect_combobox.set("None") # Default


        # --- Bottom Frame: Action Button ---
        self.bottom_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.bottom_frame.grid(row=1, column=0, columnspan=2, padx=10, pady=10, sticky="ew")
        self.bottom_frame.grid_columnconfigure(0, weight=1) # Make button centered or expand

        self.generate_button = ctk.CTkButton(self.bottom_frame, text="Generate and Save HTML Menu",
                                             height=40, command=self.generate_and_save)
        self.generate_button.grid(row=0, column=0, padx=5, pady=5)

    # --- Event Handlers and Logic ---

    def add_files(self):
        """Opens file dialog and adds selected files to the list."""
        file_paths = filedialog.askopenfilenames(title="Select Files for Menu")
        if file_paths:
            for file_path in file_paths:
                if not any(btn['file_path'] == file_path for btn in self.buttons_config): # Avoid duplicates
                    base_name = os.path.basename(file_path)
                    is_python = file_path.lower().endswith(".py")
                    # Add default config for this button
                    self.buttons_config.append({
                        'file_path': file_path,
                        'display_name': base_name,
                        'shape': list(BUTTON_SHAPES.keys())[0], # Default shape
                        'bg_color': "#4CAF50",
                        'text_color': "#ffffff",
                        'hover_bg_color': "#45a049",
                        'hover_text_color': "#ffffff",
                        'font_family': AVAILABLE_FONTS[-1], # Default font
                        'hover_effect': "None", # Default effect
                        'is_python_script': is_python
                    })
            self.update_listbox()
            # Select the last added item perhaps?
            # self.file_listbox.selection_set(tk.END)
            # self.on_listbox_select(None) # Trigger update for the last item

    def remove_selected_file(self):
        """Removes the selected file from the list and config."""
        selected_indices = self.file_listbox.curselection()
        if selected_indices:
            index = selected_indices[0]
            del self.buttons_config[index]
            self.update_listbox()
            self.disable_button_controls()
            self.selected_button_index = None # Clear selection index

    def update_listbox(self):
        """Updates the listbox display based on buttons_config."""
        self.file_listbox.delete(0, tk.END)
        for i, config in enumerate(self.buttons_config):
            prefix = "[Py] " if config['is_python_script'] else ""
            self.file_listbox.insert(tk.END, f"{prefix}{config['display_name']}")

    def on_listbox_select(self, event):
        """Handles selection change in the listbox."""
        selected_indices = self.file_listbox.curselection()
        if selected_indices:
            self.selected_button_index = selected_indices[0]
            self.update_ui_for_selection()
            self.enable_button_controls()
        else:
            self.selected_button_index = None
            self.disable_button_controls()

    def update_ui_for_selection(self):
        """Updates the right panel controls with the selected button's config."""
        if self.selected_button_index is None or self.selected_button_index >= len(self.buttons_config):
            return

        config = self.buttons_config[self.selected_button_index]

        self.display_name_entry.delete(0, tk.END)
        self.display_name_entry.insert(0, config.get('display_name', ''))

        self.shape_var.set(config.get('shape', list(BUTTON_SHAPES.keys())[0]))

        self.button_bg_color_preview.configure(fg_color=config.get('bg_color', 'gray'))
        self.button_text_color_preview.configure(fg_color=config.get('text_color', 'gray'))
        self.button_hover_bg_color_preview.configure(fg_color=config.get('hover_bg_color', 'gray'))
        self.button_hover_text_color_preview.configure(fg_color=config.get('hover_text_color', 'gray'))

        self.font_combobox.set(config.get('font_family', AVAILABLE_FONTS[-1]))
        self.hover_effect_combobox.set(config.get('hover_effect', "None"))

        # Update run script button state
        if config.get('is_python_script', False):
            self.run_script_button.configure(state="normal")
        else:
            self.run_script_button.configure(state="disabled")

    def update_button_config_from_ui(self, *args):
        """Updates the config dictionary for the selected button based on UI controls."""
        if self.selected_button_index is None or self.selected_button_index >= len(self.buttons_config):
            return

        config = self.buttons_config[self.selected_button_index]

        # Update display name and listbox entry
        new_display_name = self.display_name_entry.get()
        if new_display_name != config['display_name']:
            config['display_name'] = new_display_name
            prefix = "[Py] " if config['is_python_script'] else ""
            self.file_listbox.delete(self.selected_button_index)
            self.file_listbox.insert(self.selected_button_index, f"{prefix}{new_display_name}")
            self.file_listbox.selection_set(self.selected_button_index) # Keep selected

        config['shape'] = self.shape_var.get()
        config['font_family'] = self.font_combobox.get()
        config['hover_effect'] = self.hover_effect_combobox.get()
        # Colors are updated directly by their respective chooser functions

        # No need to call update_ui_for_selection here, avoids loops

    def choose_page_bg_color(self):
        """Opens color chooser for page background."""
        color_code = colorchooser.askcolor(title="Choose Page Background Color", initialcolor=self.page_bg_color)
        if color_code and color_code[1]:
            self.page_bg_color = color_code[1]
            self.page_bg_color_preview.configure(fg_color=self.page_bg_color)

    def choose_button_color(self, color_key):
        """Opens color chooser for a specific button color property."""
        if self.selected_button_index is None: return

        config = self.buttons_config[self.selected_button_index]
        initial_color = config.get(color_key, "#ffffff") # Default to white if key missing

        color_code = colorchooser.askcolor(title=f"Choose {color_key.replace('_', ' ').title()}", initialcolor=initial_color)

        if color_code and color_code[1]:
            chosen_color = color_code[1]
            config[color_key] = chosen_color
            # Update the corresponding preview swatch
            if color_key == 'bg_color':
                self.button_bg_color_preview.configure(fg_color=chosen_color)
            elif color_key == 'text_color':
                self.button_text_color_preview.configure(fg_color=chosen_color)
            elif color_key == 'hover_bg_color':
                self.button_hover_bg_color_preview.configure(fg_color=chosen_color)
            elif color_key == 'hover_text_color':
                self.button_hover_text_color_preview.configure(fg_color=chosen_color)
            # No need to call update_button_config_from_ui

    def enable_button_controls(self):
        """Enables individual button setting controls."""
        self.remove_button.configure(state="normal")
        self.display_name_entry.configure(state="normal")
        for widget in self.shape_frame.winfo_children():
            if isinstance(widget, ctk.CTkRadioButton):
                widget.configure(state="normal")
        self.button_bg_color_button.configure(state="normal")
        self.button_text_color_button.configure(state="normal")
        self.button_hover_bg_color_button.configure(state="normal")
        self.button_hover_text_color_button.configure(state="normal")
        self.font_combobox.configure(state="normal")
        self.hover_effect_combobox.configure(state="normal")
        # Run script button state is handled in update_ui_for_selection

    def disable_button_controls(self):
        """Disables individual button setting controls."""
        self.remove_button.configure(state="disabled")
        self.run_script_button.configure(state="disabled")
        self.display_name_entry.configure(state="disabled")
        self.display_name_entry.delete(0, tk.END)
        for widget in self.shape_frame.winfo_children():
            if isinstance(widget, ctk.CTkRadioButton):
                widget.configure(state="disabled")
        self.button_bg_color_button.configure(state="disabled")
        self.button_text_color_button.configure(state="disabled")
        self.button_hover_bg_color_button.configure(state="disabled")
        self.button_hover_text_color_button.configure(state="disabled")
        self.font_combobox.configure(state="disabled")
        self.hover_effect_combobox.configure(state="disabled")
        # Clear previews
        self.button_bg_color_preview.configure(fg_color="gray")
        self.button_text_color_preview.configure(fg_color="gray")
        self.button_hover_bg_color_preview.configure(fg_color="gray")
        self.button_hover_text_color_preview.configure(fg_color="gray")


    def run_selected_script(self):
        """Executes the selected Python script using subprocess."""
        if self.selected_button_index is None or not self.buttons_config:
            messagebox.showwarning("No Selection", "Please select a Python script from the list first.")
            return

        config = self.buttons_config[self.selected_button_index]
        if not config.get('is_python_script', False):
            messagebox.showerror("Not a Python Script", "The selected file is not a Python script (.py).")
            return

        file_path = config['file_path']
        if not os.path.exists(file_path):
             messagebox.showerror("File Not Found", f"The script file was not found:\n{file_path}")
             return

        if not self.python_executable:
             messagebox.showerror("Python Not Found", "Could not determine the Python executable path.")
             return

        try:
            print(f"Attempting to run: {self.python_executable} \"{file_path}\"")
            # Run in a new process, don't wait for it to finish
            # Use creationflags on Windows to detach the process console if desired
            kwargs = {}
            if sys.platform == "win32":
                # CREATE_NEW_CONSOLE makes it run in a new window
                # DETACHED_PROCESS runs it without a visible window (might be undesirable)
                 kwargs['creationflags'] = subprocess.CREATE_NEW_CONSOLE
                # kwargs['creationflags'] = subprocess.DETACHED_PROCESS
                 kwargs['shell'] = False # Recommended when not using shell features

            subprocess.Popen([self.python_executable, file_path], **kwargs)
            messagebox.showinfo("Script Launched", f"Launched script:\n{os.path.basename(file_path)}")

        except Exception as e:
            messagebox.showerror("Execution Error", f"Failed to run the script:\n{e}")
            print(f"Error running script: {e}")


    def generate_html_css(self):
        """Generates the HTML and CSS content based on current config."""
        page_title = self.page_title_entry.get() or "My Menu"
        page_bg = self.page_bg_color

        css_styles = f"""
body {{
    font-family: sans-serif; /* Default fallback */
    background-color: {page_bg};
    margin: 20px;
    padding: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
}}

h1 {{
    color: #333; /* Consider making this customizable */
    text-align: center;
}}

.menu-list {{
    list-style-type: none;
    padding: 0;
    margin: 20px 0;
    display: flex;
    flex-wrap: wrap;
    justify-content: center;
    gap: 15px;
}}

.menu-item {{
    /* No specific style needed here usually */
}}

/* Base button style - gets overridden by specific button classes */
.menu-button {{
    display: inline-block;
    padding: 12px 25px;
    margin: 5px;
    text-decoration: none;
    text-align: center;
    font-size: 16px;
    border: none;
    cursor: pointer;
    transition: all 0.3s ease; /* Transition for hover effects */
}}
"""
        # --- Generate CSS for EACH button ---
        html_list_items = ""
        for i, config in enumerate(self.buttons_config):
            button_class = get_unique_css_class("menu-button", i)
            shape_css = f"border-radius: {BUTTON_SHAPES.get(config['shape'], '0px')};"
            font_css = f"font-family: {config['font_family']}, sans-serif;" # Add fallback
            hover_effect_css = HOVER_EFFECTS.get(config['hover_effect'], "")

            css_styles += f"""
.{button_class} {{
    background-color: {config['bg_color']};
    color: {config['text_color']};
    {shape_css}
    {font_css}
}}

.{button_class}:hover {{
    background-color: {config['hover_bg_color']};
    color: {config['hover_text_color']};
    {hover_effect_css}
}}
"""
            # --- Generate HTML list item for this button ---
            # Ensure path works in href (replace backslashes, add file:///)
            href_path = f"file:///{os.path.abspath(config['file_path']).replace(os.sep, '/')}"
            display_name = config.get('display_name', os.path.basename(config['file_path']))
            html_list_items += f'            <li class="menu-item"><a href="{href_path}" class="menu-button {button_class}" target="_blank">{display_name}</a></li>\n'
            # Added target="_blank" to open files potentially in new tab/window


        # --- Final HTML Structure ---
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{page_title}</title>
    <style>
{css_styles}
    </style>
</head>
<body>
    <h1>{page_title}</h1>
    <nav>
        <ul class="menu-list">
{html_list_items}
        </ul>
    </nav>
    <!-- Note: Links to .py files will open/download them, not execute them due to browser security. -->
    <!-- Use the 'Run Selected Script' button in the generator app to execute .py files. -->
</body>
</html>
"""
        return html_content

    def generate_and_save(self):
        """Generates the HTML/CSS and prompts the user to save."""
        if not self.buttons_config:
            messagebox.showwarning("No Items", "Please add at least one file to the menu.")
            return

        html_content = self.generate_html_css()

        file_path = filedialog.asksaveasfilename(
            defaultextension=".html",
            filetypes=[("HTML Files", "*.html"), ("All Files", "*.*")],
            title="Save HTML Menu As",
            initialfile="my_menu.html"
        )

        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                messagebox.showinfo("Success", f"HTML menu saved successfully to:\n{file_path}")

                # Ask to open
                if messagebox.askyesno("Open File", "Do you want to open the generated HTML file now?"):
                    webbrowser.open(f"file:///{os.path.abspath(file_path)}")

            except Exception as e:
                messagebox.showerror("Save Error", f"Error saving file: {e}")
                print(f"Error saving file: {e}")
        else:
            print("Save cancelled.")


# --- Run the Application ---
if __name__ == "__main__":
    app = HtmlMenuApp()
    app.mainloop()