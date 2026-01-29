import cv2
import numpy as np
import os
import tkinter as tk
from tkinter import filedialog, messagebox
import sys

def select_files_or_directory():
    """
    Opens a dialog for selecting either multiple files or a directory.
    Returns a list of video file paths.
    """
    root = tk.Tk()
    root.withdraw()  # Hide the main window

    choice = messagebox.askquestion("Selection Mode", 
                                  "Do you want to select individual files?\n"
                                  "Select 'No' to choose an entire directory.")
    
    video_files = []
    if choice == 'yes':
        # Multiple file selection
        files = filedialog.askopenfilenames(
            title="Select video files",
            filetypes=[("Video files", "*.mp4 *.avi *.mkv"), ("All files", "*.*")]
        )
        video_files.extend(files)
    else:
        # Directory selection
        directory = filedialog.askdirectory(title="Select directory containing videos")
        if directory:
            for file in os.listdir(directory):
                if file.lower().endswith(('.mp4', '.avi', '.mkv')):
                    video_files.append(os.path.join(directory, file))
    
    return video_files

def play_video_forward_backward(video_path, num_loops=-1):
    """
    Plays a video forward then backward for a specified number of loops.
    
    Args:
        video_path (str): Path to the MP4 video file
        num_loops (int): Number of times to loop the forward/backward playback
                        Use -1 for infinite looping
    """
    video_path = os.path.normpath(video_path)
    print(f"\nNow playing: {os.path.basename(video_path)}")
    
    cap = cv2.VideoCapture(video_path)
    
    if not cap.isOpened():
        print(f"Error: Could not open video file {video_path}")
        return
    
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    window_name = "Video Player"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    
    # Store frames in memory
    print("Loading video frames...")
    frames = []
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frames.append(frame)
    
    cap.release()
    print(f"Loaded {len(frames)} frames")
    
    # Display controls
    print("\nControls:")
    print("'q' - Quit the current video")
    print("'n' - Skip to next video (if multiple videos selected)")
    print("'esc' - Exit the program entirely")
    
    loop_count = 0
    while num_loops == -1 or loop_count < num_loops:
        if num_loops != -1:
            print(f"\nLoop {loop_count + 1}/{num_loops}")
        else:
            print(f"\nLoop {loop_count + 1} (infinite mode)")
        
        # Forward playback
        print("Playing forward...")
        for frame in frames:
            cv2.imshow(window_name, frame)
            key = cv2.waitKey(1000 // fps) & 0xFF
            
            if key == ord('q'):
                cv2.destroyWindow(window_name)
                return 'next'
            elif key == 27:  # ESC key
                cv2.destroyAllWindows()
                sys.exit()
        
        # Backward playback
        print("Playing backward...")
        for frame in reversed(frames):
            cv2.imshow(window_name, frame)
            key = cv2.waitKey(1000 // fps) & 0xFF
            
            if key == ord('q'):
                cv2.destroyWindow(window_name)
                return 'next'
            elif key == 27:  # ESC key
                cv2.destroyAllWindows()
                sys.exit()
        
        loop_count += 1
    
    cv2.destroyWindow(window_name)
    return 'next'

def main():
    # Get video files
    video_files = select_files_or_directory()
    
    if not video_files:
        print("No video files selected. Exiting...")
        return
    
    # Ask for number of loops
    root = tk.Tk()
    root.withdraw()
    
    infinite_loop = messagebox.askquestion("Loop Mode", 
                                         "Do you want to loop videos infinitely?\n"
                                         "Select 'No' to specify number of loops.")
    
    num_loops = -1 if infinite_loop == 'yes' else None
    
    if num_loops is None:
        try:
            num_loops = int(input("Enter number of loops (1 or more): "))
            if num_loops < 1:
                raise ValueError
        except ValueError:
            print("Invalid input. Using default value of 1 loop.")
            num_loops = 1
    
    print(f"\nSelected {len(video_files)} video(s)")
    print("Starting playback...")
    
    # Play all selected videos
    current_video = 0
    while current_video < len(video_files):
        result = play_video_forward_backward(video_files[current_video], num_loops)
        if result == 'next':
            current_video += 1

if __name__ == "__main__":
    main()