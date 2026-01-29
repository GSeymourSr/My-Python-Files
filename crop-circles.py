import os
from PIL import Image, ImageDraw
import tkinter as tk
from tkinter import filedialog
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, Button
from datetime import datetime

# Global variables
image = None
circle_radius = 100
circle_center = [0, 0]  # Tracks the circle's center position
is_dragging = False  # Tracks whether the circle is being dragged

def load_image(image_path):
    """Load the image."""
    global image, circle_center
    image = Image.open(image_path).convert("RGBA")
    # Set the initial circle center to the image center
    circle_center[0] = image.width // 2
    circle_center[1] = image.height // 2
    return image

def apply_circle_crop(image, center, radius):
    """Apply a circular crop to the image and center it on a transparent background."""
    # Create a mask for the circle
    mask = Image.new("L", image.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((center[0] - radius, center[1] - radius,
                  center[0] + radius, center[1] + radius), fill=255)

    # Apply the mask to the image
    cropped_image = Image.new("RGBA", image.size, (0, 0, 0, 0))
    cropped_image.paste(image, mask=mask)

    # Create a new transparent canvas to center the cropped circle
    canvas_size = max(image.size)  # Ensure the canvas is large enough
    centered_image = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    # Calculate the position to paste the cropped circle
    paste_position = ((canvas_size - cropped_image.width) // 2, (canvas_size - cropped_image.height) // 2)
    centered_image.paste(cropped_image, paste_position, cropped_image)

    return centered_image

def update_circle(val):
    """Update the circle radius based on the slider value."""
    global circle_radius
    circle_radius = int(slider_radius.val)
    draw_circle()

def draw_circle():
    """Draw the circle on the image."""
    ax.clear()
    ax.imshow(image)
    # Draw the circle at its current position
    circle = plt.Circle((circle_center[0], circle_center[1]), circle_radius, edgecolor='r', fill=False, linewidth=2)
    ax.add_patch(circle)
    plt.draw()

def save_cropped_image(event):
    """Save the circle-cropped image to a user-specified directory with a timestamped filename."""
    global image, circle_center, circle_radius
    output_folder = filedialog.askdirectory(title="Select Output Folder")
    if output_folder:
        # Crop the image to the circle and center it on a transparent background
        cropped_image = apply_circle_crop(image, circle_center, circle_radius)
        # Generate a timestamped filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(output_folder, f"circle_cropped_{timestamp}.png")
        cropped_image.save(output_path)
        print(f"Saved: {output_path}")
        plt.close()

def on_press(event):
    """Handle mouse button press event."""
    global is_dragging
    if event.inaxes == ax:
        is_dragging = True

def on_release(event):
    """Handle mouse button release event."""
    global is_dragging
    is_dragging = False

def on_motion(event):
    """Handle mouse motion event to reposition the circle."""
    global circle_center, is_dragging
    if is_dragging and event.inaxes == ax:
        # Update the circle's center position
        circle_center[0] = event.xdata
        circle_center[1] = event.ydata
        draw_circle()

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

    # Connect mouse events for dragging
    fig.canvas.mpl_connect('button_press_event', on_press)
    fig.canvas.mpl_connect('button_release_event', on_release)
    fig.canvas.mpl_connect('motion_notify_event', on_motion)

    # Draw the initial circle
    draw_circle()
    plt.show()

if __name__ == "__main__":
    main()