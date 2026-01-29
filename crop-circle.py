import os
from PIL import Image, ImageDraw
import tkinter as tk
from tkinter import filedialog
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, Button

# Global variables
image = None
circle_radius = 100
circle_center = (0, 0)

def load_image(image_path):
    """Load the image and set the circle center to the image center."""
    global image, circle_center
    image = Image.open(image_path).convert("RGBA")
    circle_center = (image.width // 2, image.height // 2)  # Center of the image
    return image

def apply_circle_crop(image, center, radius):
    """Apply a circular crop to the image."""
    # Create a mask for the circle
    mask = Image.new("L", image.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((center[0] - radius, center[1] - radius, center[0] + radius, center[1] + radius), fill=255)

    # Apply the mask to the image
    result = Image.new("RGBA", image.size)
    result.paste(image, mask=mask)
    return result

def update_circle(val):
    """Update the circle radius based on the slider value."""
    global circle_radius
    circle_radius = int(slider_radius.val)
    draw_circle()

def draw_circle():
    """Draw the circle on the image."""
    ax.clear()
    ax.imshow(image)
    circle = plt.Circle(circle_center, circle_radius, edgecolor='r', fill=False, linewidth=2)
    ax.add_patch(circle)
    plt.draw()

def save_cropped_image(event):
    """Save the circle-cropped image to a user-specified directory."""
    global image, circle_center, circle_radius
    output_folder = filedialog.askdirectory(title="Select Output Folder")
    if output_folder:
        cropped_image = apply_circle_crop(image, circle_center, circle_radius)
        output_path = os.path.join(output_folder, "circle_cropped.png")
        cropped_image.save(output_path)
        print(f"Saved: {output_path}")
        plt.close()

def main():
    global slider_radius, ax

    # Use tkinter to select an image file
    root = tk.Tk()
    root.withdraw()  # Hide the root window
    image_path = filedialog.askopenfilename(
        title="Select an Image",
        filetypes=[("Image Files", "*.jpg;*.jpeg;*.png;*.bmp;*.tiff")]
    )
    if not image_path:
        print("No image selected. Exiting.")
        return

    # Load the image
    image = load_image(image_path)

    # Display the image with matplotlib
    fig, ax = plt.subplots()
    plt.subplots_adjust(left=0.1, bottom=0.25)
    ax.imshow(image)

    # Add a slider for circle radius
    ax_radius = plt.axes([0.2, 0.1, 0.65, 0.03])
    slider_radius = Slider(ax_radius, 'Circle Radius', 10, min(image.width, image.height) // 2, valinit=circle_radius)
    slider_radius.on_changed(update_circle)

    # Add a button to save the cropped image
    ax_button = plt.axes([0.4, 0.025, 0.2, 0.05])
    save_button = Button(ax_button, 'Save Cropped Image')
    save_button.on_clicked(save_cropped_image)

    # Draw the initial circle
    draw_circle()
    plt.show()

if __name__ == "__main__":
    main()