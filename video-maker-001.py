"""
Multimedia MP4 Maker with a Whimsical GUI
==========================================

This application provides a user-friendly, colorful, and animated GUI for selecting
and configuring various media types (Images, Videos, Audio, Python, and HTML) to be
combined into a final MP4 file.

Features include:
    - Selection of entire directories or individual files via Windows Explorer dialogs.
    - Configuration options for each media type:
        * Images: number of images, sequential/random order, display duration, transition effects.
        * Videos: options to play the entire video or only a time segment, looping (repeat or ping-pong) with a set number of repeats.
        * Audio: sequential or random playback order.
        * Python & HTML files: duration for display and sequential/random order.
    - Overall MP4 output duration setting.
    - Two main control buttons: "Preview" and "Create MP4".

The final MP4 creation is performed using MoviePy. The GUI is built with PyQt5 and includes
custom styling (hover effects, gradient backgrounds, etc.) to give a whimsical feel.
"""

import sys
import os
import random

# PyQt5 imports for building the GUI
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QPushButton, QVBoxLayout, QHBoxLayout,
    QFileDialog, QLabel, QTabWidget, QSpinBox, QDoubleSpinBox, QComboBox,
    QLineEdit, QMessageBox, QGroupBox, QFormLayout
)
from PyQt5.QtGui import QFont, QPalette, QColor
from PyQt5.QtCore import Qt

# MoviePy imports for video processing
from moviepy.editor import (
    ImageClip, VideoFileClip, TextClip, concatenate_videoclips,
    AudioFileClip, CompositeAudioClip
)

# ============================
# Helper Functions for File Selection
# ============================
def ask_directory_or_files(media_type: str):
    """
    Ask the user whether they want to select an entire directory or specific files.
    Returns True if directory mode is chosen, False for individual files.
    """
    # Use a simple message box with Yes/No options.
    # "Yes" means "Directory" while "No" means "Individual Files"
    reply = QMessageBox.question(
        None,
        f"{media_type} Selection Mode",
        f"Do you want to select an entire directory for {media_type}?\n\n"
        "Click Yes for Directory, No for selecting individual files.",
        QMessageBox.Yes | QMessageBox.No,
        QMessageBox.Yes
    )
    return (reply == QMessageBox.Yes)


def select_media_files(media_type: str, file_filter: str):
    """
    Show a file/directory selection dialog based on user choice for a given media type.
    Returns a list of file paths.
    """
    files = []
    if ask_directory_or_files(media_type):
        # If user wants an entire directory, use getExistingDirectory.
        directory = QFileDialog.getExistingDirectory(
            None,
            f"Select Directory for {media_type}",
            os.getcwd()
        )
        if directory:
            # Walk through the directory and add all files that match our filter extensions.
            # Here, we extract the allowed extensions from the filter string.
            # Example file_filter: "Images (*.png *.jpg *.jpeg)"
            allowed_exts = [ext.strip("*.").lower() for ext in file_filter.split("(", 1)[1].rstrip(")").split()]
            for root, _, filenames in os.walk(directory):
                for filename in filenames:
                    if any(filename.lower().endswith(ext) for ext in allowed_exts):
                        files.append(os.path.join(root, filename))
    else:
        # If not a directory, allow multi-selection of individual files.
        files, _ = QFileDialog.getOpenFileNames(
            None,
            f"Select {media_type}",
            os.getcwd(),
            file_filter
        )
    return files

# ============================
# Main Application Window Class
# ============================
class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()

        # Set the window title and initial size
        self.setWindowTitle("Whimsical Multimedia MP4 Maker")
        self.setGeometry(100, 100, 1200, 800)

        # Initialize lists to store selected media file paths
        self.images_files = []
        self.videos_files = []
        self.audio_files = []
        self.python_files = []
        self.html_files = []

        # Initialize configuration settings (default values)
        # These will later be read from the UI widgets in the settings tabs.
        self.img_num = 5
        self.img_order = "Sequential"  # or "Random"
        self.img_duration = 3.0  # seconds per image
        self.img_transition = "Fade"  # Example transition option

        self.video_play_mode = "Entire"  # or "Specific Duration"
        self.video_duration = 5.0  # if using specific duration
        self.video_loop_mode = "None"  # Options: "None", "Repeat", "Ping-Pong"
        self.video_loop_count = 1

        self.audio_order = "Sequential"  # or "Random"

        self.code_order = "Sequential"  # applies to both Python and HTML files
        self.code_duration = 5.0  # seconds per file

        self.output_duration = 300.0  # overall MP4 length in seconds (e.g., 5 minutes)
        self.output_resolution = (1280, 720)  # width x height
        self.output_fps = 24  # frames per second
        self.output_filename = "output_video.mp4"

        # Setup the GUI layout
        self.setup_ui()

    def setup_ui(self):
        """
        Build and configure all the UI elements: file selection buttons, configuration tabs,
        preview area, and control buttons.
        """

        # Create a central widget and set a horizontal layout: left controls, right preview
        central_widget = QWidget()
        main_layout = QHBoxLayout()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

        # -------------------------------
        # Left Panel: Controls and Settings
        # -------------------------------
        controls_widget = QWidget()
        controls_layout = QVBoxLayout()
        controls_widget.setLayout(controls_layout)
        controls_widget.setMinimumWidth(350)

        # -- Media Selection Group --
        media_selection_group = QGroupBox("Media Selection")
        media_selection_layout = QVBoxLayout()

        # Button for selecting Images
        self.btn_select_images = QPushButton("Select Images")
        self.btn_select_images.clicked.connect(self.select_images)
        media_selection_layout.addWidget(self.btn_select_images)

        # Button for selecting Videos
        self.btn_select_videos = QPushButton("Select Videos")
        self.btn_select_videos.clicked.connect(self.select_videos)
        media_selection_layout.addWidget(self.btn_select_videos)

        # Button for selecting Audio
        self.btn_select_audio = QPushButton("Select Audio")
        self.btn_select_audio.clicked.connect(self.select_audio)
        media_selection_layout.addWidget(self.btn_select_audio)

        # Button for selecting Python Files
        self.btn_select_python = QPushButton("Select Python Files")
        self.btn_select_python.clicked.connect(self.select_python)
        media_selection_layout.addWidget(self.btn_select_python)

        # Button for selecting HTML Files
        self.btn_select_html = QPushButton("Select HTML Files")
        self.btn_select_html.clicked.connect(self.select_html)
        media_selection_layout.addWidget(self.btn_select_html)

        media_selection_group.setLayout(media_selection_layout)
        controls_layout.addWidget(media_selection_group)

        # -- Configuration Tabs --
        self.tabs = QTabWidget()
        self.tabs.setMinimumHeight(300)

        # Create separate tabs for each media type and output settings
        self.setup_images_tab()
        self.setup_videos_tab()
        self.setup_audio_tab()
        self.setup_code_tab()  # For both Python and HTML files
        self.setup_output_tab()

        controls_layout.addWidget(self.tabs)

        # -- Control Buttons: Preview and Create MP4 --
        btns_layout = QHBoxLayout()
        self.btn_preview = QPushButton("Preview")
        self.btn_preview.clicked.connect(self.preview)
        btns_layout.addWidget(self.btn_preview)

        self.btn_create = QPushButton("Create MP4")
        self.btn_create.clicked.connect(self.create_mp4)
        btns_layout.addWidget(self.btn_create)

        controls_layout.addLayout(btns_layout)

        # -------------------------------
        # Right Panel: Preview Area
        # -------------------------------
        # For now, we add a placeholder label. In a complete implementation, this
        # could be a widget that plays a simulation of the final video.
        self.preview_label = QLabel("Preview Area\n(Preview functionality not fully implemented)")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setStyleSheet("background-color: #f0f8ff; border: 2px dashed #ccc;")
        self.preview_label.setFont(QFont("Arial", 16))
        main_layout.addWidget(controls_widget, 0)
        main_layout.addWidget(self.preview_label, 1)

        # -- Set Global Styles for a Whimsical, Colorful Look --
        self.setStyleSheet("""
            QMainWindow { background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                      stop:0 #FFDEE9, stop:1 #B5FFFC); }
            QPushButton {
                background-color: #ffcc66;
                border: 2px solid #ffaa00;
                border-radius: 10px;
                padding: 8px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #ffdd88;
                border: 2px solid #ff8800;
            }
            QGroupBox {
                font-weight: bold;
                font-size: 14px;
            }
            QTabWidget::pane { border: 2px solid #ffaa00; border-radius: 8px; }
        """)

    # ============================
    # Setup for Each Configuration Tab
    # ============================
    def setup_images_tab(self):
        """
        Create the Images configuration tab with controls for number of images,
        display order, duration, and transition effect.
        """
        images_tab = QWidget()
        layout = QFormLayout()

        # Number of images to show (Spin Box)
        self.spin_img_num = QSpinBox()
        self.spin_img_num.setMinimum(1)
        self.spin_img_num.setMaximum(100)
        self.spin_img_num.setValue(self.img_num)
        layout.addRow("Number of Images:", self.spin_img_num)

        # Display order (Combo Box: Sequential or Random)
        self.combo_img_order = QComboBox()
        self.combo_img_order.addItems(["Sequential", "Random"])
        layout.addRow("Image Order:", self.combo_img_order)

        # Duration per image (in seconds)
        self.spin_img_duration = QDoubleSpinBox()
        self.spin_img_duration.setMinimum(0.5)
        self.spin_img_duration.setMaximum(30.0)
        self.spin_img_duration.setSingleStep(0.5)
        self.spin_img_duration.setValue(self.img_duration)
        layout.addRow("Image Duration (sec):", self.spin_img_duration)

        # Transition effect (Combo Box: example options)
        self.combo_img_transition = QComboBox()
        self.combo_img_transition.addItems(["None", "Fade", "Slide", "Zoom"])
        layout.addRow("Transition Effect:", self.combo_img_transition)

        images_tab.setLayout(layout)
        self.tabs.addTab(images_tab, "Images")

    def setup_videos_tab(self):
        """
        Create the Videos configuration tab with options for playback mode,
        duration, looping mode, and loop count.
        """
        videos_tab = QWidget()
        layout = QFormLayout()

        # Playback mode: Entire video or Specific Duration
        self.combo_video_play_mode = QComboBox()
        self.combo_video_play_mode.addItems(["Entire", "Specific Duration"])
        layout.addRow("Video Play Mode:", self.combo_video_play_mode)

        # Duration for video clip if Specific Duration is selected (in seconds)
        self.spin_video_duration = QDoubleSpinBox()
        self.spin_video_duration.setMinimum(1.0)
        self.spin_video_duration.setMaximum(600.0)
        self.spin_video_duration.setValue(self.video_duration)
        layout.addRow("Video Duration (sec):", self.spin_video_duration)

        # Looping mode: None, Repeat, or Ping-Pong
        self.combo_video_loop_mode = QComboBox()
        self.combo_video_loop_mode.addItems(["None", "Repeat", "Ping-Pong"])
        layout.addRow("Looping Mode:", self.combo_video_loop_mode)

        # Loop count (if looping is enabled)
        self.spin_video_loop_count = QSpinBox()
        self.spin_video_loop_count.setMinimum(1)
        self.spin_video_loop_count.setMaximum(20)
        self.spin_video_loop_count.setValue(self.video_loop_count)
        layout.addRow("Loop Count:", self.spin_video_loop_count)

        videos_tab.setLayout(layout)
        self.tabs.addTab(videos_tab, "Videos")

    def setup_audio_tab(self):
        """
        Create the Audio configuration tab with an option for playback order.
        """
        audio_tab = QWidget()
        layout = QFormLayout()

        # Audio playback order (Sequential or Random)
        self.combo_audio_order = QComboBox()
        self.combo_audio_order.addItems(["Sequential", "Random"])
        layout.addRow("Audio Order:", self.combo_audio_order)

        audio_tab.setLayout(layout)
        self.tabs.addTab(audio_tab, "Audio")

    def setup_code_tab(self):
        """
        Create the Code configuration tab for both Python and HTML files.
        Settings include display order and duration for each file.
        """
        code_tab = QWidget()
        layout = QFormLayout()

        # Order for code files (Sequential or Random)
        self.combo_code_order = QComboBox()
        self.combo_code_order.addItems(["Sequential", "Random"])
        layout.addRow("Code File Order:", self.combo_code_order)

        # Duration to display each code file (in seconds)
        self.spin_code_duration = QDoubleSpinBox()
        self.spin_code_duration.setMinimum(1.0)
        self.spin_code_duration.setMaximum(60.0)
        self.spin_code_duration.setValue(self.code_duration)
        layout.addRow("Code Display Duration (sec):", self.spin_code_duration)

        code_tab.setLayout(layout)
        self.tabs.addTab(code_tab, "Code (Python/HTML)")

    def setup_output_tab(self):
        """
        Create the Output configuration tab to set overall MP4 duration,
        resolution, frame rate, and output file name.
        """
        output_tab = QWidget()
        layout = QFormLayout()

        # Overall MP4 duration (in seconds)
        self.spin_output_duration = QDoubleSpinBox()
        self.spin_output_duration.setMinimum(10.0)
        self.spin_output_duration.setMaximum(3600.0)
        self.spin_output_duration.setValue(self.output_duration)
        layout.addRow("Total Video Duration (sec):", self.spin_output_duration)

        # Resolution (we use two spin boxes for width and height)
        self.spin_output_width = QSpinBox()
        self.spin_output_width.setMinimum(320)
        self.spin_output_width.setMaximum(3840)
        self.spin_output_width.setValue(self.output_resolution[0])
        self.spin_output_height = QSpinBox()
        self.spin_output_height.setMinimum(240)
        self.spin_output_height.setMaximum(2160)
        self.spin_output_height.setValue(self.output_resolution[1])
        resolution_layout = QHBoxLayout()
        resolution_layout.addWidget(QLabel("Width:"))
        resolution_layout.addWidget(self.spin_output_width)
        resolution_layout.addWidget(QLabel("Height:"))
        resolution_layout.addWidget(self.spin_output_height)
        layout.addRow("Resolution:", resolution_layout)

        # Frame rate
        self.spin_output_fps = QSpinBox()
        self.spin_output_fps.setMinimum(1)
        self.spin_output_fps.setMaximum(60)
        self.spin_output_fps.setValue(self.output_fps)
        layout.addRow("Frame Rate (fps):", self.spin_output_fps)

        # Output file name (using a QLineEdit)
        self.line_output_filename = QLineEdit()
        self.line_output_filename.setText(self.output_filename)
        layout.addRow("Output Filename:", self.line_output_filename)

        output_tab.setLayout(layout)
        self.tabs.addTab(output_tab, "Output")

    # ============================
    # File Selection Methods
    # ============================
    def select_images(self):
        """
        Opens a file/directory selection dialog for image files.
        """
        # File filter for images
        files = select_media_files("Images", "Images (*.png *.jpg *.jpeg)")
        if files:
            self.images_files = files
            QMessageBox.information(self, "Images Selected", f"{len(files)} image(s) selected.")

    def select_videos(self):
        """
        Opens a file/directory selection dialog for video files.
        """
        files = select_media_files("Videos", "Videos (*.mp4 *.avi *.mov)")
        if files:
            self.videos_files = files
            QMessageBox.information(self, "Videos Selected", f"{len(files)} video(s) selected.")

    def select_audio(self):
        """
        Opens a file/directory selection dialog for audio files.
        """
        files = select_media_files("Audio", "Audio (*.mp3 *.wav)")
        if files:
            self.audio_files = files
            QMessageBox.information(self, "Audio Selected", f"{len(files)} audio file(s) selected.")

    def select_python(self):
        """
        Opens a file/directory selection dialog for Python files.
        """
        files = select_media_files("Python Files", "Python Files (*.py)")
        if files:
            self.python_files = files
            QMessageBox.information(self, "Python Files Selected", f"{len(files)} Python file(s) selected.")

    def select_html(self):
        """
        Opens a file/directory selection dialog for HTML files.
        """
        files = select_media_files("HTML Files", "HTML Files (*.html *.htm)")
        if files:
            self.html_files = files
            QMessageBox.information(self, "HTML Files Selected", f"{len(files)} HTML file(s) selected.")

    # ============================
    # Preview and MP4 Creation Methods
    # ============================
    def preview(self):
        """
        Trigger a preview of the final video. (This is currently a placeholder.)
        In a full implementation, this would simulate the final output.
        """
        # Update the preview label text (or ideally, show a real preview video)
        self.preview_label.setText("Preview not implemented.\n(This would play a simulated video.)")
        QMessageBox.information(self, "Preview", "Preview functionality is not fully implemented in this demo.")

    def create_mp4(self):
        """
        Assemble the media according to the configuration settings and export the final MP4.
        Uses MoviePy to create video clips from images, videos, and text (for code files),
        and overlays the chosen audio.
        """
        # First, update the configuration from the UI widgets.
        self.img_num = self.spin_img_num.value()
        self.img_order = self.combo_img_order.currentText()
        self.img_duration = self.spin_img_duration.value()
        self.img_transition = self.combo_img_transition.currentText()

        self.video_play_mode = self.combo_video_play_mode.currentText()
        self.video_duration = self.spin_video_duration.value()
        self.video_loop_mode = self.combo_video_loop_mode.currentText()
        self.video_loop_count = self.spin_video_loop_count.value()

        self.audio_order = self.combo_audio_order.currentText()

        self.code_order = self.combo_code_order.currentText()
        self.code_duration = self.spin_code_duration.value()

        self.output_duration = self.spin_output_duration.value()
        self.output_resolution = (self.spin_output_width.value(), self.spin_output_height.value())
        self.output_fps = self.spin_output_fps.value()
        self.output_filename = self.line_output_filename.text()

        # Check that at least one type of media is selected.
        if not (self.images_files or self.videos_files or self.python_files or self.html_files):
            QMessageBox.warning(self, "No Media Selected", "Please select at least one type of media to create the video.")
            return

        # Create a list to hold video clips (MoviePy objects)
        clips = []

        # ----------------------------
        # Process Images
        # ----------------------------
        if self.images_files:
            # Optionally shuffle if Random order is selected.
            images_list = self.images_files.copy()
            if self.img_order == "Random":
                random.shuffle(images_list)
            # Limit to the number specified by the user.
            images_list = images_list[:self.img_num]
            for img_path in images_list:
                try:
                    # Create an ImageClip from the image file
                    clip = ImageClip(img_path, duration=self.img_duration)
                    # Resize to the output resolution (maintaining aspect ratio could be added)
                    clip = clip.resize(newsize=self.output_resolution)
                    clips.append(clip)
                except Exception as e:
                    print(f"Error processing image {img_path}: {e}")

        # ----------------------------
        # Process Videos
        # ----------------------------
        if self.videos_files:
            videos_list = self.videos_files.copy()
            # For demonstration, we are not shuffling videos.
            for vid_path in videos_list:
                try:
                    video_clip = VideoFileClip(vid_path)
                    # If the play mode is "Specific Duration", trim the clip.
                    if self.video_play_mode == "Specific Duration":
                        video_clip = video_clip.subclip(0, min(self.video_duration, video_clip.duration))
                    # Looping: if Repeat is selected, concatenate multiple copies.
                    if self.video_loop_mode == "Repeat":
                        video_clip = concatenate_videoclips([video_clip] * int(self.video_loop_count))
                    elif self.video_loop_mode == "Ping-Pong":
                        # For Ping-Pong, create a reversed copy and concatenate.
                        reversed_clip = video_clip.fx(vfx.time_mirror)
                        video_clip = concatenate_videoclips([video_clip, reversed_clip] * int(self.video_loop_count))
                    # Resize video to match output resolution
                    video_clip = video_clip.resize(newsize=self.output_resolution)
                    clips.append(video_clip)
                except Exception as e:
                    print(f"Error processing video {vid_path}: {e}")

        # ----------------------------
        # Process Code Files (Python and HTML)
        # ----------------------------
        code_files = self.python_files + self.html_files
        if code_files:
            code_list = code_files.copy()
            if self.code_order == "Random":
                random.shuffle(code_list)
            for file_path in code_list:
                try:
                    # Read the file content
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                    # Create a TextClip to simulate displaying the code.
                    # Here, we use a monospace font and a fixed background color.
                    txt_clip = TextClip(
                        content,
                        fontsize=20,
                        font="Courier",
                        color="white",
                        bg_color="black",
                        size=self.output_resolution,
                        method="caption"  # This method wraps text nicely.
                    ).set_duration(self.code_duration)
                    clips.append(txt_clip)
                except Exception as e:
                    print(f"Error processing code file {file_path}: {e}")

        # ----------------------------
        # Assemble the Final Video Clip
        # ----------------------------
        if not clips:
            QMessageBox.warning(self, "No Clips", "No media clips could be generated. Check your selections.")
            return

        # Concatenate all clips sequentially
        final_clip = concatenate_videoclips(clips, method="compose")

        # If the final clip is longer than the desired output duration, trim it.
        if final_clip.duration > self.output_duration:
            final_clip = final_clip.subclip(0, self.output_duration)
        # If it's shorter, you might consider looping it (this example does not loop the final clip).
        # Set the fps and size properties
        final_clip = final_clip.set_fps(self.output_fps)

        # ----------------------------
        # Process Audio (Background Track)
        # ----------------------------
        if self.audio_files:
            audio_list = self.audio_files.copy()
            if self.audio_order == "Random":
                random.shuffle(audio_list)
            audio_clips = []
            # Create an AudioFileClip for each and concatenate until reaching the desired duration.
            total_audio_duration = 0
            for audio_path in audio_list:
                try:
                    audio_clip = AudioFileClip(audio_path)
                    audio_clips.append(audio_clip)
                    total_audio_duration += audio_clip.duration
                    if total_audio_duration >= final_clip.duration:
                        break
                except Exception as e:
                    print(f"Error processing audio file {audio_path}: {e}")
            if audio_clips:
                # Concatenate audio clips in sequence
                combined_audio = concatenate_videoclips(audio_clips) if len(audio_clips) > 1 else audio_clips[0]
                # If the audio is longer than the video, cut it to match; if shorter, loop it.
                if combined_audio.duration > final_clip.duration:
                    combined_audio = combined_audio.subclip(0, final_clip.duration)
                else:
                    # Loop audio until reaching final_clip.duration
                    n_loops = int(final_clip.duration // combined_audio.duration) + 1
                    combined_audio = concatenate_videoclips([combined_audio] * n_loops)
                    combined_audio = combined_audio.subclip(0, final_clip.duration)
                final_clip = final_clip.set_audio(combined_audio)

        # ----------------------------
        # Export the Final Video to an MP4 File
        # ----------------------------
        try:
            QMessageBox.information(self, "Exporting", "Exporting video. This may take some time...")
            # Write the final video clip to the specified output file.
            final_clip.write_videofile(
                self.output_filename,
                fps=self.output_fps,
                codec="libx264",
                audio_codec="aac"
            )
            QMessageBox.information(self, "Success", f"Video exported successfully as {self.output_filename}")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"An error occurred during export:\n{e}")

# ============================
# Main Function to Run the Application
# ============================
def main():
    # Create the Qt Application
    app = QApplication(sys.argv)
    # Create and show the main window
    window = MainWindow()
    window.show()
    # Run the main Qt loop
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
