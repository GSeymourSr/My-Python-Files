from PIL import Image
import os
from pathlib import Path
import sys

# Define paths
INPUT_FOLDER = r"C:\- AI  NEW CONTENT\input"
OUTPUT_FOLDER = r"C:\- AI  NEW CONTENT\output"

def upscale_image(input_path, output_path, scale_factor=4):
    """
    Upscale a single image using Lanczos resampling
    """
    with Image.open(input_path) as img:
        # Convert to RGB if necessary
        if img.mode in ('RGBA', 'LA'):
            img = img.convert('RGB')
            
        # Calculate new size
        new_width = int(img.width * scale_factor)
        new_height = int(img.height * scale_factor)
        
        # Upscale image using Lanczos resampling
        upscaled = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Save the upscaled image
        upscaled.save(output_path, quality=95, optimize=True)

def process_folder(input_folder=INPUT_FOLDER, output_folder=OUTPUT_FOLDER, scale=4):
    """
    Process all images in the input folder
    """
    # Convert paths to Path objects
    input_path = Path(input_folder)
    output_path = Path(output_folder)
    
    # Create output folder if it doesn't exist
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Supported image formats
    supported_formats = {'.png', '.jpg', '.jpeg', '.webp'}
    
    try:
        # Get list of all files
        files = [f for f in input_path.glob('*') if f.suffix.lower() in supported_formats]
        total_files = len(files)
        
        if total_files == 0:
            print(f"No supported images found in {input_folder}")
            return
        
        print(f"Found {total_files} images to process")
        
        # Process each image
        for i, file in enumerate(files, 1):
            try:
                # Create output filename
                output_filename = f"{file.stem}_upscaled{file.suffix}"
                output_file = output_path / output_filename
                
                print(f"[{i}/{total_files}] Processing {file.name}...")
                
                # Upscale the image
                upscale_image(file, output_file, scale)
                
                print(f"Saved to: {output_file}")
                
            except Exception as e:
                print(f"Error processing {file.name}: {str(e)}")
    
    except Exception as e:
        print(f"Error accessing folder: {str(e)}")

if __name__ == "__main__":
    print("Image Upscaling Script")
    print(f"Input folder: {INPUT_FOLDER}")
    print(f"Output folder: {OUTPUT_FOLDER}")
    
    try:
        # Allow custom scale factor from command line
        scale_factor = 4  # default scale factor
        if len(sys.argv) > 1:
            try:
                scale_factor = float(sys.argv[1])
            except ValueError:
                print("Invalid scale factor. Using default (4x)")
        
        print(f"Upscaling images by {scale_factor}x")
        process_folder(scale=scale_factor)
        print("Process completed!")
        
    except KeyboardInterrupt:
        print("\nProcess interrupted by user")
    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")