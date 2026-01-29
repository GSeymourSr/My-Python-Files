import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image

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

# Function to save modified image
def save_image(image, original_path, transformation):
    # Get the original file name and extension
    file_name = original_path.split("/")[-1]
    file_name_no_ext = file_name.split(".")[0]
    extension = file_name.split(".")[-1]
    
    # Save the image with a new name based on the transformation
    save_path = filedialog.asksaveasfilename(initialfile=f"{file_name_no_ext}_{transformation}.{extension}", defaultextension=f".{extension}", filetypes=[(f"{extension.upper()} files", f"*.{extension}")])
    if save_path:
        image.save(save_path)

# Function to perform transformations on selected images
def transform_images():
    files = select_files()
    if not files:
        messagebox.showerror("No Files Selected", "Please select one or more files to process.")
        return
    
    transformation = transformation_var.get()

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

            # Save the transformed image
            save_image(transformed_image, file_path, transformation)
            messagebox.showinfo("Success", f"Image saved successfully: {file_path}")
        
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred while processing {file_path}: {e}")

# Create main tkinter window
root = tk.Tk()
root.title("Batch Image Manipulator")

# Dropdown menu for transformation options
transformation_var = tk.StringVar(root)
transformation_var.set("Flip Horizontal")  # Default option

transformation_menu = tk.OptionMenu(root, transformation_var, "Flip Horizontal", "Flip Vertical", "Rotate 90°", "Rotate 180°", "Rotate 270°")
transformation_menu.pack(pady=10)

# Button to apply transformations
apply_button = tk.Button(root, text="Apply Transformation", command=transform_images)
apply_button.pack(pady=10)

# Start the GUI loop
root.mainloop()
