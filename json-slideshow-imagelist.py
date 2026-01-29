import os
import json
import tkinter as tk
from tkinter import filedialog

def select_directory():
    # Create a root window, hide it, and then open the directory selection dialog.
    root = tk.Tk()
    root.withdraw()
    directory = filedialog.askdirectory(title="Select Image Directory")
    root.destroy()
    return directory

def create_json(directory):
    if not os.path.exists(directory):
        print(f"Directory {directory} does not exist.")
        return

    # Get list of all image files (using full paths)
    image_files = [
        os.path.join(directory, file)
        for file in os.listdir(directory)
        if file.lower().endswith(('.png', '.jpg', '.jpeg'))
    ]

    if not image_files:
        print(f"No images found in {directory}.")
        return

    # Use the last part of the directory as the JSON file name.
    directory_name = os.path.basename(os.path.normpath(directory))
    json_filename = f"{directory_name}.json"

    # Save the list of image paths to the JSON file.
    with open(json_filename, "w") as json_file:
        json.dump(image_files, json_file, indent=4)

    print(f"JSON file '{json_filename}' created successfully with {len(image_files)} images.")

if __name__ == "__main__":
    while True:
        selected_dir = select_directory()
        if not selected_dir:
            print("No directory selected. Exiting.")
            break

        create_json(selected_dir)

        cont = input("Do you want to create a JSON for another directory? (y/n): ")
        if cont.lower() != 'y':
            print("Exiting.")
            break
