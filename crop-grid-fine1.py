import os
import datetime
from PIL import Image
import tkinter as tk
from tkinter import filedialog
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, Button

# Define the constant output folder path.
OUTPUT_FOLDER = r"C:\- AI  NEW CONTENT"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Define a class to make lines draggable.
class DraggableLine:
    def __init__(self, line, orientation, min_val, max_val):
        """
        line: The matplotlib line artist.
        orientation: 'vertical' or 'horizontal'.
        min_val, max_val: Limits for the line’s position.
        """
        self.line = line
        self.orientation = orientation
        self.press = None
        self.min_val = min_val
        self.max_val = max_val
        # Connect to the mouse events.
        self.cidpress = line.figure.canvas.mpl_connect('button_press_event', self.on_press)
        self.cidrelease = line.figure.canvas.mpl_connect('button_release_event', self.on_release)
        self.cidmotion = line.figure.canvas.mpl_connect('motion_notify_event', self.on_motion)

    def on_press(self, event):
        if event.inaxes != self.line.axes:
            return
        # Check if the mouse is close enough to the line.
        contains, _ = self.line.contains(event)
        if not contains:
            return
        # Save the original position and the event coordinate.
        if self.orientation == 'vertical':
            self.press = (self.line.get_xdata()[0], event.xdata)
        else:
            self.press = (self.line.get_ydata()[0], event.ydata)

    def on_motion(self, event):
        if self.press is None:
            return
        if event.inaxes != self.line.axes:
            return
        # Compute the new position based on the mouse movement.
        if self.orientation == 'vertical':
            x0, xpress = self.press
            dx = event.xdata - xpress
            new_x = x0 + dx
            # Clamp within allowed bounds.
            new_x = max(self.min_val, min(new_x, self.max_val))
            self.line.set_xdata([new_x, new_x])
        else:
            y0, ypress = self.press
            dy = event.ydata - ypress
            new_y = y0 + dy
            new_y = max(self.min_val, min(new_y, self.max_val))
            self.line.set_ydata([new_y, new_y])
        self.line.figure.canvas.draw_idle()

    def on_release(self, event):
        self.press = None
        self.line.figure.canvas.draw_idle()

# Function to crop the image based on the current (possibly adjusted) grid.
def crop_image_grid(image, vertical_lines, horizontal_lines):
    img_width, img_height = image.size
    # Gather the positions from the vertical and horizontal lines.
    x_positions = [0] + sorted([line.get_xdata()[0] for line in vertical_lines]) + [img_width]
    y_positions = [0] + sorted([line.get_ydata()[0] for line in horizontal_lines]) + [img_height]

    # Create a base timestamp for uniqueness.
    base_timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    counter = 0

    # Crop each cell (each grid square defined by adjacent boundaries).
    for i in range(len(x_positions)-1):
        for j in range(len(y_positions)-1):
            left = int(x_positions[i])
            right = int(x_positions[i+1])
            upper = int(y_positions[j])
            lower = int(y_positions[j+1])
            cropped_img = image.crop((left, upper, right, lower))
            filename = f"crop_{j}_{i}_{base_timestamp}_{counter}.png"
            counter += 1
            output_path = os.path.join(OUTPUT_FOLDER, filename)
            cropped_img.save(output_path)
            print(f"Saved: {output_path}")

    print("Cropping complete!")

# Called when the sliders change: update the number of grid lines.
def update_grid(val):
    global rows, cols
    rows = int(row_slider.val)
    cols = int(col_slider.val)
    draw_grid()

# Draw (or re-draw) the grid lines. This function creates evenly spaced grid lines
# based on the current slider values. (Any manual adjustments will be lost when sliders are moved.)
def draw_grid():
    global vertical_lines, horizontal_lines, draggable_vertical, draggable_horizontal
    # Remove any existing grid lines.
    for line in vertical_lines:
        line.remove()
    for line in horizontal_lines:
        line.remove()
    vertical_lines = []
    horizontal_lines = []
    draggable_vertical = []
    draggable_horizontal = []

    img_width, img_height = image.size
    # Create vertical lines (there will be cols-1 lines).
    for i in range(1, cols):
        x = i * (img_width / cols)
        line = ax.axvline(x, color='r', linestyle='--', linewidth=2, picker=5)
        vertical_lines.append(line)
        # Make the line draggable between 0 and img_width.
        draggable_vertical.append(DraggableLine(line, 'vertical', 0, img_width))
    # Create horizontal lines (rows-1 lines).
    for i in range(1, rows):
        y = i * (img_height / rows)
        line = ax.axhline(y, color='r', linestyle='--', linewidth=2, picker=5)
        horizontal_lines.append(line)
        # Make the line draggable between 0 and img_height.
        draggable_horizontal.append(DraggableLine(line, 'horizontal', 0, img_height))
    plt.draw()

# Called when the "Save Cropped Images" button is pressed.
def save_cropped_images(event):
    crop_image_grid(image, vertical_lines, horizontal_lines)

# Called when the "Load New Image" button is pressed.
def load_new_image(event):
    global image, rows, cols
    # Use tkinter to select an image file.
    image_path = filedialog.askopenfilename(
        title="Select an Image",
        filetypes=[("Image Files", "*.jpg;*.jpeg;*.png;*.bmp;*.tiff")]
    )
    if not image_path:
        print("No image selected. Keeping the current image.")
        return

    # Load the new image.
    image = Image.open(image_path)
    # Clear the current axis and show the new image.
    ax.clear()
    ax.imshow(image, origin='upper')
    # Reset default grid settings (you may keep the current slider values if desired).
    rows, cols = int(row_slider.val), int(col_slider.val)
    draw_grid()
    plt.draw()

# Main script
if __name__ == "__main__":
    # Initialize tkinter and hide the root window.
    root = tk.Tk()
    root.withdraw()

    # Initially, ask the user to select an image.
    image_path = filedialog.askopenfilename(
        title="Select an Image",
        filetypes=[("Image Files", "*.jpg;*.jpeg;*.png;*.bmp;*.tiff")]
    )
    if not image_path:
        print("No image selected. Exiting.")
        exit()

    # Load the image.
    image = Image.open(image_path)
    # Default grid settings.
    rows, cols = 2, 2

    # Create the matplotlib figure and axis.
    fig, ax = plt.subplots()
    plt.subplots_adjust(left=0.1, bottom=0.35)
    # Show the image and set the origin to 'upper' so that (0,0) is the top‐left (like PIL).
    ax.imshow(image, origin='upper')

    # Global lists for the grid line artists and their draggable wrappers.
    vertical_lines = []
    horizontal_lines = []
    draggable_vertical = []
    draggable_horizontal = []

    # Add sliders for the number of rows and columns.
    ax_row = plt.axes([0.2, 0.2, 0.65, 0.03])
    ax_col = plt.axes([0.2, 0.15, 0.65, 0.03])
    row_slider = Slider(ax_row, 'Rows', 1, 10, valinit=rows, valstep=1)
    col_slider = Slider(ax_col, 'Columns', 1, 10, valinit=cols, valstep=1)
    row_slider.on_changed(update_grid)
    col_slider.on_changed(update_grid)

    # Add a button to save the cropped images.
    ax_save_button = plt.axes([0.25, 0.05, 0.2, 0.075])
    save_button = Button(ax_save_button, 'Save Cropped Images')
    save_button.on_clicked(save_cropped_images)

    # Add a button to load a new image.
    ax_load_button = plt.axes([0.55, 0.05, 0.2, 0.075])
    load_button = Button(ax_load_button, 'Load New Image')
    load_button.on_clicked(load_new_image)

    # Draw the initial grid.
    draw_grid()
    plt.show()
