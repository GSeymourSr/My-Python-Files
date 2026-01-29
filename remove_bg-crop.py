from rembg import remove
from PIL import Image, UnidentifiedImageError # Import UnidentifiedImageError
import os
from pathlib import Path

# Define the specific input and output paths
INPUT_FOLDER = r"C:\- AI  NEW CONTENT\input"
OUTPUT_FOLDER = r"C:\- AI  NEW CONTENT\output"

def remove_backgrounds_and_crop(input_folder=INPUT_FOLDER, output_folder=OUTPUT_FOLDER):
    """
    Remove backgrounds from all images in the input folder,
    crop them to the content, and save them to the output folder.

    Args:
        input_folder (str): Path to folder containing input images
        output_folder (str): Path to folder where processed images will be saved
    """
    # Convert paths to Path objects for better cross-platform compatibility
    input_path = Path(input_folder)
    output_path = Path(output_folder)

    # Create output folder if it doesn't exist
    output_path.mkdir(parents=True, exist_ok=True)

    # Supported image formats (rembg primarily works well with these)
    supported_formats = {'.png', '.jpg', '.jpeg', '.webp'}

    # Get list of all files in input folder, ensuring they are files
    try:
        all_files = list(input_path.glob('*'))
        # Filter for actual files with supported extensions
        image_files = [f for f in all_files if f.is_file() and f.suffix.lower() in supported_formats]
        total_files = len(image_files)

        if total_files == 0:
            print(f"No supported images found in {input_folder}")
            return

        print(f"Found {total_files} supported images to process in {input_folder}")
        processed = 0
        skipped_empty = 0

        # Process each image file
        for file in image_files:
            try:
                print(f"\nProcessing: {file.name}...")

                # --- Open image ---
                input_image = Image.open(file)

                # --- Remove background ---
                # The output 'output_image' will be an RGBA image with transparency
                print(f"Removing background...")
                output_image = remove(input_image)

                # --- Find bounding box of the content ---
                # getbbox() returns a (left, upper, right, lower) tuple or None if empty
                print(f"Calculating bounding box...")
                bbox = output_image.getbbox()

                if bbox:
                    # --- Crop the image to the bounding box ---
                    print(f"Cropping to box: {bbox}...")
                    cropped_image = output_image.crop(bbox)

                    # --- Prepare output path ---
                    # Add '_nobg_cropped' to distinguish from original name and indicate processing
                    output_filename = file.stem + '_nobg_cropped.png'
                    output_file = output_path / output_filename

                    # --- Save the cropped image ---
                    print(f"Saving cropped image as: {output_filename}...")
                    cropped_image.save(output_file, format="PNG") # Explicitly save as PNG
                    processed += 1
                    print(f"[{processed}/{total_files}] Successfully processed and saved: {file.name} -> {output_filename}")

                else:
                    # Handle cases where the image is empty after background removal (bbox is None)
                    skipped_empty += 1
                    print(f"Skipped {file.name}: Image appears empty after background removal (no content detected).")

            # --- Error Handling for individual files ---
            except UnidentifiedImageError:
                 print(f"Skipped {file.name}: Cannot identify image file. It might be corrupted or not a valid image format recognized by Pillow.")
            except IOError as e:
                 print(f"Skipped {file.name}: I/O Error (possibly file corruption or read issue): {str(e)}")
            except Exception as e:
                # Catch other potential errors during processing (e.g., from rembg)
                print(f"Error processing {file.name}: {str(e)}")
                # Optionally add more specific error types if rembg throws them

    # --- Error Handling for folder access ---
    except FileNotFoundError:
         print(f"Error: Input folder not found at '{input_folder}'. Please check the path.")
    except PermissionError:
         print(f"Error: Permission denied when accessing '{input_folder}' or '{output_folder}'. Check folder permissions.")
    except Exception as e:
        # Catch-all for other unexpected issues (e.g., path format errors on some OS)
        print(f"An unexpected error occurred: {str(e)}")
        print("Please ensure the input and output paths are correct and accessible.")

    # --- Final Summary ---
    print("\n" + "=" * 30)
    print("Processing Summary:")
    print(f"Total supported images found: {total_files}")
    print(f"Successfully processed and saved: {processed}")
    if skipped_empty > 0:
        print(f"Skipped (empty after processing): {skipped_empty}")
    print(f"Total completed or skipped: {processed + skipped_empty}")
    print("=" * 30)


if __name__ == "__main__":
    print(f"Input folder:  {INPUT_FOLDER}")
    print(f"Output folder: {OUTPUT_FOLDER}")
    print("-" * 20)
    print("Starting background removal and cropping process...")
    remove_backgrounds_and_crop()
    print("\nScript finished.")