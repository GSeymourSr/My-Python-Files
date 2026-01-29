from PIL import Image, UnidentifiedImageError
from collections import Counter
from pathlib import Path

# --- Configuration ---
INPUT_FOLDER = r"C:\- AI  NEW CONTENT\input"
OUTPUT_FOLDER = r"C:\- AI  NEW CONTENT\output"

# How close a color needs to be to the border color to be considered part of the border.
# A higher value is more tolerant of small variations in color (e.g., JPEG artifacts).
# Start with a value like 25-35 and adjust if needed.
COLOR_TOLERANCE = 30

# --- Helper Functions ---

def colors_are_similar(color1, color2, tolerance=COLOR_TOLERANCE):
    """Checks if two RGB colors are similar within a given tolerance."""
    # Slicing [:3] ensures we only compare R,G,B and ignore Alpha (transparency)
    return sum(abs(c1 - c2) for c1, c2 in zip(color1[:3], color2[:3])) <= tolerance * 3

def get_dominant_border_color(image):
    """
    Determines the most common color from the four corners of the image.
    Returns the dominant RGB color tuple or None if no clear dominant color.
    """
    width, height = image.size
    # Get colors of the four corners
    corners = [
        image.getpixel((0, 0)),
        image.getpixel((width - 1, 0)),
        image.getpixel((0, height - 1)),
        image.getpixel((width - 1, height - 1)),
    ]

    # Use a Counter to "vote" for the most common color
    # We convert color tuples to strings to make them hashable for the Counter
    color_counts = Counter(str(c[:3]) for c in corners) # Only count RGB
    
    # Find the most common color string
    most_common_str = color_counts.most_common(1)[0][0]
    
    # Check if this color has a majority (at least 2 corners)
    if color_counts[most_common_str] >= 2:
        # Convert the string back to an integer tuple (e.g., "(255, 255, 255)" -> (255, 255, 255))
        return tuple(map(int, most_common_str.strip('()').split(',')))
    else:
        # If no color appears at least twice, we can't be sure what the border is.
        return None

def crop_images_to_content(input_folder=INPUT_FOLDER, output_folder=OUTPUT_FOLDER):
    """
    Crops solid-colored borders from all images in the input folder
    and saves them to the output folder. Uses a robust four-corner check.
    """
    input_path = Path(input_folder)
    output_path = Path(output_folder)

    output_path.mkdir(parents=True, exist_ok=True)

    supported_formats = {'.png', '.jpg', '.jpeg', '.webp', '.bmp', '.tiff'}

    try:
        all_files = list(input_path.glob('*'))
        image_files = [f for f in all_files if f.is_file() and f.suffix.lower() in supported_formats]
        total_files = len(image_files)

        if total_files == 0:
            print(f"No supported images found in {input_folder}")
            return

        print(f"Found {total_files} supported images to process in {input_folder}")
        processed_count = 0
        skipped_count = 0

        for i, file in enumerate(image_files, 1):
            try:
                print(f"\n[{i}/{total_files}] Processing: {file.name}...")

                with Image.open(file) as input_image:
                    # Convert to RGBA to handle all image types consistently.
                    # RGBA ensures the .getpixel() method always returns a 4-element tuple.
                    rgba_image = input_image.convert('RGBA')
                    
                    # Use the new robust method to find the border color
                    border_color = get_dominant_border_color(rgba_image)
                    
                    if border_color is None:
                        skipped_count += 1
                        print(f"Skipped {file.name}: Could not determine a common border color from the corners. Image may have no border or a complex one.")
                        continue

                    print(f"Dominant border color identified as: {border_color}")

                    # Use Pillow's built-in getbbox() on a difference image for efficiency
                    # Create a background image of the detected border color
                    bg = Image.new('RGBA', rgba_image.size, border_color + (255,))
                    
                    # Find the difference between the image and the solid background
                    # Note: This part is conceptually what we are doing. A manual scan is more flexible with tolerance.
                    # We will stick to the manual scan for tolerance control.
                    
                    # Get the bounding box of the content that is NOT the border color
                    pixels = rgba_image.load()
                    width, height = rgba_image.size
                    
                    left, top, right, bottom = 0, 0, width, height
                    
                    # This is a simplified and more correct way to find the box
                    # getbbox() is fast but doesn't support tolerance. A manual scan is better here.
                    non_border_pixels = []
                    for x in range(width):
                        for y in range(height):
                            if not colors_are_similar(pixels[x, y], border_color):
                                non_border_pixels.append((x, y))
                    
                    if not non_border_pixels:
                        skipped_count += 1
                        print(f"Skipped {file.name}: Image appears to be a single solid color.")
                        continue
                        
                    # Get the min/max x and y from the content pixels
                    min_x = min(p[0] for p in non_border_pixels)
                    max_x = max(p[0] for p in non_border_pixels)
                    min_y = min(p[1] for p in non_border_pixels)
                    max_y = max(p[1] for p in non_border_pixels)
                    
                    bbox = (min_x, min_y, max_x + 1, max_y + 1)
                    
                    print(f"Calculated content box: {bbox}...")
                    # Crop the original image to preserve its mode and quality
                    cropped_image = input_image.crop(bbox)

                    output_suffix = '.png' if file.suffix.lower() not in ['.png', '.jpg', '.jpeg'] else file.suffix
                    output_filename = file.stem + '_cropped' + output_suffix
                    output_file = output_path / output_filename
                    
                    print(f"Saving cropped image as: {output_filename}...")
                    cropped_image.save(output_file)
                    processed_count += 1
                    print(f"Successfully cropped and saved: {file.name}")

            except UnidentifiedImageError:
                print(f"Skipped {file.name}: Cannot identify image file. It might be corrupted or not a valid format.")
                skipped_count += 1
            except Exception as e:
                print(f"An unexpected error occurred while processing {file.name}: {e}")
                skipped_count += 1

    except Exception as e:
        print(f"A critical script error occurred: {e}")

    print("\n" + "=" * 30)
    print("Processing Summary:")
    print(f"Total images found: {total_files}")
    print(f"Successfully processed and saved: {processed_count}")
    print(f"Skipped (no border, error, etc.): {skipped_count}")
    print("=" * 30)

if __name__ == "__main__":
    print(f"Input folder:  {INPUT_FOLDER}")
    print(f"Output folder: {OUTPUT_FOLDER}")
    print(f"Color Tolerance set to: {COLOR_TOLERANCE}")
    print("-" * 20)
    print("Starting auto-cropping process with improved border detection...")
    crop_images_to_content()
    print("\nScript finished.")