from rembg import remove
from PIL import Image
import os
from pathlib import Path

# Define the specific input and output paths
INPUT_FOLDER = r"C:\- AI  NEW CONTENT\input"
OUTPUT_FOLDER = r"C:\- AI  NEW CONTENT\output"

def remove_backgrounds(input_folder=INPUT_FOLDER, output_folder=OUTPUT_FOLDER):
    """
    Remove backgrounds from all images in the input folder and save them to the output folder.
    
    Args:
        input_folder (str): Path to folder containing input images
        output_folder (str): Path to folder where processed images will be saved
    """
    # Convert paths to Path objects for better cross-platform compatibility
    input_path = Path(input_folder)
    output_path = Path(output_folder)
    
    # Create output folder if it doesn't exist
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Supported image formats
    supported_formats = {'.png', '.jpg', '.jpeg', '.webp'}
    
    # Get list of all files in input folder
    try:
        files = list(input_path.glob('*'))
        total_files = len([f for f in files if f.suffix.lower() in supported_formats])
        
        if total_files == 0:
            print(f"No supported images found in {input_folder}")
            return
        
        print(f"Found {total_files} images to process")
        processed = 0
        
        # Process each image in the input folder
        for file in files:
            if file.suffix.lower() in supported_formats:
                try:
                    # Open image and remove background
                    input_image = Image.open(file)
                    output_image = remove(input_image)
                    
                    # Create output filename with PNG extension
                    output_filename = file.stem + '_nobg.png'
                    output_file = output_path / output_filename
                    
                    # Save processed image
                    output_image.save(output_file)
                    processed += 1
                    print(f"[{processed}/{total_files}] Processed: {file.name}")
                    
                except Exception as e:
                    print(f"Error processing {file.name}: {str(e)}")
    
    except Exception as e:
        print(f"Error accessing folder: {str(e)}")
        print("Please make sure the input and output paths are correct and accessible.")

if __name__ == "__main__":
    print(f"Input folder: {INPUT_FOLDER}")
    print(f"Output folder: {OUTPUT_FOLDER}")
    print("Starting background removal process...")
    remove_backgrounds()
    print("Process completed!")