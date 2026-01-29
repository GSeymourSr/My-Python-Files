import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image
import os

# Function to flip image horizontally
def flip_horizontal(image):
    return image.transpose(Image.FLIP_LEFT_RIGHT)

# Function to flip image vertically
def flip_vertical(image):
    return image.transpose(Image.FLIP_TOP_BOTTOM)

# Function to rotate image
def rotate_image(image, degrees):
    return image.rotate(degrees, expand=True)

# Function to handle file selection
def select_files():
    file_paths = filedialog.askopenfilenames(title="Select Image Files", filetypes=[("Image Files", "*.png;*.jpg;*.jpeg;*.bmp;*.gif")])
    return file_paths

# Function to select a save directory
def select_save_directory():
    save_directory = filedialog.askdirectory(title="Select Save Directory")
    return save_directory

# Function to save modified images automatically in the selected directory
def save_images(images, save_directory, transformation):
    for image, original_path in images:
        try:
            # Get the original file name and extension
            file_name = os.path.basename(original_path)
            file_name_no_ext = os.path.splitext(file_name)[0]
            extension = os.path.splitext(file_name)[1]

            # Construct the new file path
            new_file_name = f"{file_name_no_ext}_{transformation}{extension}"
            save_path = os.path.join(save_directory, new_file_name)

            # Save the image
            image.save(save_path)
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred while saving {original_path}: {e}")

# Function to perform transformations on selected images
def transform_images():
    files = select_files()
    if not files:
        messagebox.showerror("No Files Selected", "Please select one or more files to process.")
        return
    
    save_directory = select_save_directory()
    if not save_directory:
        messagebox.showerror("No Directory Selected", "Please select a directory to save the files.")
        return
    
    transformation = transformation_var.get()

    images = []
    # Loop through selected files
    for file_path in files:
        try:
            image = Image.open(file_path)

            # Apply the chosen transformation
            if transformation == "Flip Horizontal":
                transformed_image = flip_horizontal(image)
            elif transformation == "Flip Vertical":
                transformed_image = flip_vertical(image)
            elif transformation == "Rotate 90°":
                transformed_image = rotate_image(image, 90)
            elif transformation == "Rotate 180°":
                transformed_image = rotate_image(image, 180)
            elif transformation == "Rotate 270°":
                transformed_image = rotate_image(image, 270)

            images.append((transformed_image, file_path))

        except Exception as e:
            messagebox.showerror("Error", f"An error occurred while processing {file_path}: {e}")

    # Save all images in the selected directory
    save_images(images, save_directory, transformation)
    messagebox.showinfo("Success", f"Images have been saved to {save_directory}")

# Create main tkinter window
root = tk.Tk()
root.title("Batch Image Manipulator")

# Set window size
root.geometry("400x200")

# Dropdown menu for transformation options
transformation_var = tk.StringVar(root)
transformation_var.set("Flip Horizontal")  # Default option

transformation_menu = tk.OptionMenu(root, transformation_var, "Flip Horizontal", "Flip Vertical", "Rotate 90°", "Rotate 180°", "Rotate 270°")
transformation_menu.pack(pady=20)

# Button to apply transformations
apply_button = tk.Button(root, text="Apply Transformation", command=transform_images)
apply_button.pack(pady=10)

# Start the GUI loop
root.mainloop()
