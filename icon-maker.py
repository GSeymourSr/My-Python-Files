from PIL import Image
import os

def create_icon(image_path, icon_path):
    """
    Converts a standard image file (PNG, JPG, etc.) into a multi-resolution
    .ico file.

    Args:
        image_path (str): The path to the source image file.
        icon_path (str): The path where the .ico file will be saved.
    """
    try:
        # A list of standard icon sizes
        # Windows recommends 16, 32, 48, 256. Others are for different uses.
        icon_sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]

        # Open the source image
        img = Image.open(image_path)

        # Pillow's save method for ICO format can take a list of sizes.
        # It will automatically resize the image to each specified size.
        img.save(icon_path, format='ICO', sizes=icon_sizes)

        print(f"Successfully created icon: {icon_path}")
        print(f"Contains sizes: {', '.join(map(str, icon_sizes))}")

    except FileNotFoundError:
        print(f"Error: The file '{image_path}' was not found.")
    except Exception as e:
        print(f"An error occurred: {e}")

# --- --- --- HOW TO USE --- --- ---
if __name__ == "__main__":
    # 1. Make sure your source image is in the same folder as this script,
    #    or provide the full path to it.
    #    Best choice: A square PNG file with a transparent background, 256x256 or larger.
    
    source_image = "image.png"  # <-- CHANGE THIS to your image file name
    
    # 2. Choose a name for your output icon file.
    output_icon_name = "python_script_icon.ico" # <-- CHANGE THIS if you want

    # Check if the source image exists before running the function
    if os.path.exists(source_image):
        create_icon(source_image, output_icon_name)
    else:
        print(f"Error: Source image '{source_image}' not found.")
        print("Please place your image in the same directory as this script, or update the 'source_image' variable with the correct path.")