import tkinter as tk
from tkinter import filedialog, scrolledtext, ttk, font, messagebox
import re
import json
import os

def extract_shaders_from_html(html_content):
    """
    Analyzes HTML content and extracts shader effect data.

    Args:
        html_content (str): The content of the HTML file.

    Returns:
        list: A list of dictionaries, each containing effect data, or None if errors.
    """
    fs_source_match = re.search(r"const fsSource = `(.*?)`;", html_content, re.DOTALL)
    if not fs_source_match:
        return "Error: Could not find 'const fsSource = `...`;' in the HTML."

    fs_source = fs_source_match.group(1).strip()
    effect_blocks_regex = re.compile(r"if\(effectType == (\d+)\) \{\s*\/\/\s*(.*?)\s*\n(.*?)\n\s*\}", re.DOTALL)
    effect_matches = effect_blocks_regex.findall(fs_source)

    if not effect_matches:
        return "Error: No shader effect blocks found in fsSource."

    extracted_effects = []
    for index, effect_type, effect_name, shader_code in effect_matches:
        extracted_effects.append({
            "effect_type": effect_type,
            "name": effect_name.strip(),
            "source": shader_code.strip()
        })
    return extracted_effects


def run_extraction(window, output_display, html_content_var, effect_vars, effects_data):
    """Gets HTML content, extracts shaders, and saves selected ones to JSON."""
    html_content = html_content_var.get()
    if not html_content:
        messagebox.showerror("Error", "Please load an HTML file first.")
        return

    extraction_result = extract_shaders_from_html(html_content)
    if isinstance(extraction_result, str) and extraction_result.startswith("Error:"):
        messagebox.showerror("Extraction Error", extraction_result)
        return

    effects_data.clear() # Clear previous data
    for effect in extraction_result:
        effects_data.append(effect)

    # Update GUI List with Checkboxes
    update_effect_list(window, effect_vars, effects_data, output_display)


def update_effect_list(window, effect_vars, effects_data, output_display):
    """Updates the GUI listbox with effects and checkboxes."""
    # Clear existing checkboxes and list (if needed - in this case, we recreate)
    for var in effect_vars[:]: # Iterate over a copy to avoid modification issues
        var.destroy()
        effect_vars.remove(var)

    effect_list_frame = tk.Frame(window, bg="#f0f0f0") # Frame to hold checkboxes & labels
    effect_list_frame.pack(pady=10)

    for i, effect in enumerate(effects_data):
        var = tk.BooleanVar()
        effect_vars.append(var) # Add to effect_vars list
        checkbox = tk.Checkbutton(effect_list_frame, text=effect['name'], variable=var,
                                   bg="#f0f0f0", fg="black", font=("Arial", 11), selectcolor="#f0f0f0") # Match bg color
        checkbox.grid(row=i, column=0, sticky="w", padx=10) # Use grid for layout

    # Select All/None Buttons - placed below the list
    select_buttons_frame = tk.Frame(window, bg="#f0f0f0")
    select_buttons_frame.pack(pady=5)

    select_all_button = ModernButton(select_buttons_frame, text="Select All", command=lambda: set_checkboxes(effect_vars, True))
    select_all_button.pack(side=tk.LEFT, padx=5)
    select_none_button = ModernButton(select_buttons_frame, text="Select None", command=lambda: set_checkboxes(effect_vars, False))
    select_none_button.pack(side=tk.LEFT, padx=5)


def set_checkboxes(effect_vars, value):
    """Sets the value of all effect checkboxes."""
    for var in effect_vars:
        var.set(value)

def save_selected_effects(output_display, effect_vars, effects_data):
    """Saves the selected effects to JSON files."""
    output_dir = "shaders_json"
    os.makedirs(output_dir, exist_ok=True)

    output_display.config(state=tk.NORMAL)
    output_display.delete(1.0, tk.END)
    output_display.insert(tk.END, "Saving selected effects...\n")

    for i, effect in enumerate(effects_data):
        if effect_vars[i].get(): # Check if checkbox is selected
            filename = f"{effect['name'].lower().replace(' ', '_')}.json"
            filepath = os.path.join(output_dir, filename)
            json_data = {
                "name": effect['name'],
                "source": effect['source'].replace("\\n", "\n")
            }
            try:
                with open(filepath, 'w', encoding='utf-8') as json_file:
                    json.dump(json_data, json_file, indent=2)
                output_display.insert(tk.END, f"Saved effect '{effect['name']}' to '{filepath}'\n")
            except Exception as e:
                output_display.insert(tk.END, f"Error saving '{filename}': {e}\n")
        else:
            output_display.insert(tk.END, f"Skipped effect '{effect['name']}' (not selected).\n")

    output_display.insert(tk.END, "\nJSON file creation process finished.\n")
    output_display.config(state=tk.DISABLED)


def load_html_file(output_display, html_content_var):
    """Opens file dialog to load HTML, reads content."""
    filepath = filedialog.askopenfilename(
        title="Select HTML file",
        filetypes=(("HTML files", "*.html;*.htm"), ("All files", "*.*"))
    )
    if filepath:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                html_content = f.read()
                html_content_var.set(html_content)
                output_display.config(state=tk.NORMAL)
                output_display.delete(1.0, tk.END)
                output_display.insert(tk.END, f"HTML file loaded from: {filepath}\n")
                output_display.config(state=tk.DISABLED)
                # Automatically extract effects after loading a file:
                run_extraction_auto_list(window, output_display, html_content_var, effect_vars, effects_data)
        except Exception as e:
            output_display.config(state=tk.NORMAL)
            output_display.delete(1.0, tk.END)
            output_display.insert(tk.END, f"Error loading HTML file: {e}\n")
            output_display.config(state=tk.DISABLED)
    else:
        output_display.config(state=tk.NORMAL)
        output_display.delete(1.0, tk.END)
        output_display.insert(tk.END, "File loading cancelled.\n")
        output_display.config(state=tk.DISABLED)


def run_extraction_auto_list(window, output_display, html_content_var, effect_vars, effects_data):
    """Auto runs extraction and updates list, without confirmation."""
    html_content = html_content_var.get()
    if not html_content:
        output_display.config(state=tk.NORMAL)
        output_display.delete(1.0, tk.END)
        output_display.insert(tk.END, "Please load an HTML file first.\n")
        output_display.config(state=tk.DISABLED)
        return

    extraction_result = extract_shaders_from_html(html_content)
    if isinstance(extraction_result, str) and extraction_result.startswith("Error:"):
        output_display.config(state=tk.NORMAL)
        output_display.delete(1.0, tk.END)
        output_display.insert(tk.END, f"{extraction_result}\n")
        output_display.config(state=tk.DISABLED)
        return

    effects_data.clear() # Clear previous data
    for effect in extraction_result:
        effects_data.append(effect)

    # Update GUI List with Checkboxes
    update_effect_list(window, effect_vars, effects_data, output_display)
    output_display.config(state=tk.NORMAL)
    output_display.delete(1.0, tk.END)
    output_display.insert(tk.END, "Effects list updated after HTML load.\n")
    output_display.config(state=tk.DISABLED)


class ModernButton(tk.Button): # Custom button class for styling
    def __init__(self, parent, **kwargs):
        tk.Button.__init__(self, parent, **kwargs)
        self.config(
            relief=tk.RAISED,
            borderwidth=0,
            bg="#4CAF50", # Default green color
            fg="white",
            font=("Arial", 12, "bold"),
            padx=20,
            pady=10,
            cursor="hand2",
        )
        self.original_bg = "#4CAF50" # Store original background for hover effect
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)

    def on_enter(self, event):
        self.config(bg="#45a049", relief=tk.RAISED, bd=2) # Darker green, raised with border

    def on_leave(self, event):
        self.config(bg=self.original_bg, relief=tk.RAISED, bd=0) # Original color, no border


if __name__ == "__main__":
    window = tk.Tk()
    window.title("Shader Extractor Pro")
    window.geometry("700x600") # Increased height and width

    # --- Modern Theme ---
    window.configure(bg="#f0f0f0") # Light gray background

    bold_font = font.Font(family="Arial", size=12, weight="bold") # Define bold font

    # --- UI Elements ---
    html_content_var = tk.StringVar()
    effect_vars = [] # List to hold BooleanVars for checkboxes
    effects_data = [] # List to hold extracted effect dictionaries

    title_label = tk.Label(window, text="Shader Extractor Pro", font=bold_font, bg="#f0f0f0") # Bold title
    title_label.pack(pady=20)

    load_button = ModernButton(window, text="Load HTML File", command=lambda: load_html_file(output_display, html_content_var))
    load_button.pack(pady=10)

    extract_list_button = ModernButton(window, text="Extract Effects List", command=lambda: run_extraction(window, output_display, html_content_var, effect_vars, effects_data))
    extract_list_button.pack(pady=10)

    save_json_button = ModernButton(window, text="Save Selected Effects to JSON", command=lambda: save_selected_effects(output_display, effect_vars, effects_data))
    save_json_button.pack(pady=10)


    output_display = scrolledtext.ScrolledText(window, wrap=tk.WORD, height=10, bg="#e0e0e0", fg="black", font=("Arial", 11)) # Adjusted height, font
    output_display.pack(padx=20, pady=15, fill=tk.BOTH, expand=True)
    output_display.config(state=tk.DISABLED)

    window.mainloop()