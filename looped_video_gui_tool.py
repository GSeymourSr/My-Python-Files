import cv2
import numpy as np
import os
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog

# ===============================
# GUI FILE SELECTOR
# ===============================
def select_video_files():
    """
    Opens a dialog for selecting one or more video files.
    Returns a list of selected video file paths.
    """
    root = tk.Tk()
    root.withdraw()  # Hide the root tkinter window

    # Allow user to pick multiple files
    files = filedialog.askopenfilenames(
        title="Select one or more video files to loop",
        filetypes=[("Video files", "*.mp4 *.avi *.mkv"), ("All files", "*.*")]
    )
    return list(files)  # Convert the tuple to a list

# ===============================
# VIDEO LOOPING AND WRITING
# ===============================
def create_looped_video(input_path, output_path, num_loops):
    """
    Loops a video forward and backward multiple times, writes to a new file.

    Args:
        input_path (str): Source video file path.
        output_path (str): Destination path for looped video.
        num_loops (int): Number of forward+backward loops.
    Returns:
        bool: Success status
    """
    input_path = os.path.normpath(input_path)
    output_path = os.path.normpath(output_path)
    print("-" * 50)
    print(f"Processing: {os.path.basename(input_path)}")

    # Load the video using OpenCV
    cap = cv2.VideoCapture(input_path)
    if not cap.isOpened():
        print(f"!! ERROR: Could not open {input_path}")
        return False

    # Read video properties (resolution and framerate)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)

    frames = []
    print("-> Reading frames into memory (small videos only)...")

    # Read all frames into a list
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frames.append(frame)
    cap.release()

    if not frames:
        print("!! ERROR: No frames read from video")
        return False

    print(f"-> Loaded {len(frames)} frames.")

    # Set up VideoWriter with mp4 codec
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # 'avc1' is an alternative
    writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    if not writer.isOpened():
        print(f"!! ERROR: Cannot open output file {output_path}")
        return False

    # Loop through and write each round of frames
    for i in range(num_loops):
        print(f"-> Writing loop {i + 1} of {num_loops}")
        for frame in frames:
            writer.write(frame)        # Write forward
        for frame in reversed(frames):
            writer.write(frame)        # Write backward

    writer.release()
    print(f"-> SUCCESS: Saved to {output_path}")
    return True

# ===============================
# PREVIEW MODE WITH PAUSE + SCREENSHOT
# ===============================
def preview_and_screenshot(video_path):
    """
    Opens a preview window with pause/screenshot/quit controls.
    Args:
        video_path (str): The path to the video to preview.
    """
    cap = cv2.VideoCapture(video_path)
    paused = False
    print("\n[Preview Mode]\nPress SPACE to pause/play, 's' to save screenshot, 'q' to quit.")

    while cap.isOpened():
        if not paused:
            ret, frame = cap.read()
            if not ret:
                break
            cv2.imshow('Preview (q=quit, space=pause, s=screenshot)', frame)

        # Wait for key input: 30ms if playing, wait forever if paused
        key = cv2.waitKey(30 if not paused else 0) & 0xFF
        if key == ord('q'):
            break
        elif key == ord(' '):
            paused = not paused
        elif key == ord('s') and paused:
            frame_number = int(cap.get(cv2.CAP_PROP_POS_FRAMES))
            filename = f"screenshot_{frame_number}.png"
            cv2.imwrite(filename, frame)
            print(f"-> Screenshot saved as {filename}")

    cap.release()
    cv2.destroyAllWindows()

# ===============================
# MAIN GUI ENTRY POINT
# ===============================
def main():
    video_files = select_video_files()
    if not video_files:
        print("No files selected. Exiting...")
        return

    # Ask user for number of loops using simple dialog
    root = tk.Tk()
    root.withdraw()
    try:
        num_loops_str = simpledialog.askstring("Loop Count", "Enter how many times to loop each video:", initialvalue='1')
        num_loops = int(num_loops_str)
        if num_loops < 1:
            raise ValueError
    except (ValueError, TypeError):
        messagebox.showinfo("Invalid Input", "Defaulting to 1 loop.")
        num_loops = 1

    print(f"\nProcessing {len(video_files)} video(s) with {num_loops} loop(s) each.")

    for input_video_path in video_files:
        file_name, _ = os.path.splitext(os.path.basename(input_video_path))
        default_output_name = f"{file_name}_looped.mp4"

        output_path = filedialog.asksaveasfilename(
            title=f"Save looped version of '{os.path.basename(input_video_path)}'",
            initialfile=default_output_name,
            defaultextension=".mp4",
            filetypes=[("MP4 Video", "*.mp4")]
        )

        if not output_path:
            print(f"Skipped: {input_video_path}")
            continue

        success = create_looped_video(input_video_path, output_path, num_loops)
        if success:
            preview_and_screenshot(output_path)

    print("\nAll processing complete. Goodbye!")

# ===============================
# RUN THE TOOL
# ===============================
if __name__ == "__main__":
    main()
