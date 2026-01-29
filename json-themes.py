import json
import os
from tkinter import Tk
from tkinter.filedialog import askopenfilename

def create_theme_files(json_file_path):
    # Load the JSON file
    with open(json_file_path, 'r') as file:
        data = json.load(file)
    
    # Get the directory of the input file
    directory = os.path.dirname(json_file_path)
    
    # Iterate through each theme
    for theme in data['themes']:
        # Create a filename by converting the theme name to lowercase and replacing spaces with underscores
        filename = theme['name'].lower().replace(' ', '_') + '.json'
        filepath = os.path.join(directory, filename)
        
        # Write the theme data to a new JSON file
        with open(filepath, 'w') as theme_file:
            json.dump(theme, theme_file, indent=4)
        
        print(f"Created file: {filepath}")

if __name__ == "__main__":
    # Hide the root Tkinter window
    Tk().withdraw()
    
    # Open a file dialog to select the JSON file
    json_file_path = askopenfilename(
        title="Select the JSON file",
        filetypes=[("JSON files", "*.json")]
    )
    
    # Check if a file was selected
    if json_file_path:
        create_theme_files(json_file_path)
    else:
        print("No file selected. Exiting.")