import os
import sys
import numpy as np
from pathlib import Path
from PIL import Image
import cv2
from rembg import remove

# Define the specific input and output paths
INPUT_FOLDER = r"C:\- AI  NEW CONTENT\input"
OUTPUT_FOLDER = r"C:\- AI  NEW CONTENT\output"

def remove_video_background(input_folder=INPUT_FOLDER, output_folder=OUTPUT_FOLDER):
    """
    Remove backgrounds from all videos in the input folder using a memory-efficient approach.
    
    Args:
        input_folder (str): Path to folder containing input videos.
        output_folder (str): Path to folder where processed videos will be saved.
    """
    # Ensure output directory exists
    os.makedirs(output_folder, exist_ok=True)
    
    # Supported video formats
    supported_formats = {'.mp4', '.mov', '.avi', '.mkv'}
    
    try:
        # Get list of video files
        video_files = [
            f for f in os.listdir(input_folder) 
            if os.path.splitext(f)[1].lower() in supported_formats
        ]
        
        if not video_files:
            print(f"No supported videos found in {input_folder}")
            return
        
        print(f"Found {len(video_files)} videos to process")
        
        # Process each video
        for index, filename in enumerate(video_files, 1):
            input_path = os.path.join(input_folder, filename)
            output_filename = f"{os.path.splitext(filename)[0]}_nobg.mp4"
            output_path = os.path.join(output_folder, output_filename)
            
            try:
                # Open video capture
                cap = cv2.VideoCapture(input_path)
                
                # Get video properties
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                fps = cap.get(cv2.CAP_PROP_FPS)
                total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                
                # Setup video writer
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                out = cv2.VideoWriter(output_path, fourcc, fps, (width, height), True)
                
                # Process frames
                processed_frames = 0
                while True:
                    # Read a frame
                    ret, frame = cap.read()
                    if not ret:
                        break
                    
                    # Convert OpenCV BGR to RGB
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    
                    # Convert to PIL Image
                    pil_image = Image.fromarray(frame_rgb)
                    
                    # Remove background
                    processed_image = remove(pil_image)
                    
                    # Convert back to OpenCV format (BGR)
                    processed_frame = cv2.cvtColor(np.array(processed_image), cv2.COLOR_RGB2BGR)
                    
                    # Write processed frame
                    out.write(processed_frame)
                    
                    # Progress tracking
                    processed_frames += 1
                    if processed_frames % 10 == 0:
                        print(f"Processing {filename}: {processed_frames}/{total_frames} frames")
                
                # Release resources
                cap.release()
                out.release()
                
                print(f"[{index}/{len(video_files)}] Processed: {filename}")
                
            except Exception as e:
                print(f"Error processing {filename}: {str(e)}")
                continue
    
    except Exception as e:
        print(f"Error accessing folder: {str(e)}")
        print("Please make sure the input and output paths are correct and accessible.")

def main():
    """Main function to run the background removal process."""
    print(f"Input folder: {INPUT_FOLDER}")
    print(f"Output folder: {OUTPUT_FOLDER}")
    print("Starting background removal process...")
    
    # Add a way to pause and prevent console from closing immediately
    try:
        remove_video_background()
        print("Process completed!")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    
    input("Press Enter to exit...")

if __name__ == "__main__":
    main()