import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk
import os
import datetime

# Attempt to import Real-ESRGAN
try:
    from realesrgan import RealESRGAN
    import torch
except ImportError:
    RealESRGAN = None

# Maximum preview size (for display only)
MAX_PREVIEW_WIDTH = 400
MAX_PREVIEW_HEIGHT = 400

class ImageProcessorApp:
    def __init__(self, master):
        self.master = master
        self.master.title("Image Processor App")
        self.images = []       # List of image file paths
        self.thumbnails = []   # List of thumbnails for sidebar
        self.current_index = 0
        self.original_image = None  # Full resolution image
        self.processed_image = None  # Full resolution processed image
        self.esrgan_model = None  # Will hold the Real-ESRGAN model

        # Sidebar Frame for image list with scrollbar
        self.sidebar_frame = tk.Frame(master, width=200, bg="lightgray")
        self.sidebar_frame.pack(side=tk.LEFT, fill=tk.Y)
        self.load_button = tk.Button(self.sidebar_frame, text="Load Images", command=self.load_images)
        self.load_button.pack(padx=5, pady=5)
        
        self.listbox_frame = tk.Frame(self.sidebar_frame)
        self.listbox_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.listbox_scroll = tk.Scrollbar(self.listbox_frame)
        self.listbox_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.listbox = tk.Listbox(self.listbox_frame, yscrollcommand=self.listbox_scroll.set)
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.listbox_scroll.config(command=self.listbox.yview)
        self.listbox.bind("<<ListboxSelect>>", self.on_thumbnail_select)

        # Main Frame for previews and controls
        self.main_frame = tk.Frame(master)
        self.main_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Preview Frame (dual preview)
        self.preview_frame = tk.Frame(self.main_frame)
        self.preview_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # Original preview (scaled for display)
        self.original_label = tk.Label(self.preview_frame, text="Original Image", bg="white")
        self.original_label.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Processed preview (scaled for display)
        self.processed_label = tk.Label(self.preview_frame, text="Processed Image", bg="white")
        self.processed_label.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Control Panel Frame
        self.control_frame = tk.Frame(self.main_frame, height=200)
        self.control_frame.pack(side=tk.BOTTOM, fill=tk.X)

        # --- Control Widgets ---
        # Resize Options dropdown (now including new presets)
        self.resize_option = tk.StringVar(value="None")
        tk.Label(self.control_frame, text="Resize Preset:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.resize_menu = ttk.Combobox(
            self.control_frame,
            textvariable=self.resize_option,
            values=["None", "Half", "Double", "Custom", "16:9", "9:16"],
            state="readonly"
        )
        self.resize_menu.grid(row=0, column=1, padx=5, pady=5)
        self.resize_menu.bind("<<ComboboxSelected>>", self.on_resize_option_change)

        # Custom dimensions
        tk.Label(self.control_frame, text="Custom Width:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.custom_width = tk.Entry(self.control_frame, state=tk.DISABLED)
        self.custom_width.grid(row=1, column=1, padx=5, pady=5)
        tk.Label(self.control_frame, text="Custom Height:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.custom_height = tk.Entry(self.control_frame, state=tk.DISABLED)
        self.custom_height.grid(row=2, column=1, padx=5, pady=5)

        # Upscaling option (using Real-ESRGAN)
        self.upscale_var = tk.IntVar()
        self.upscale_check = tk.Checkbutton(
            self.control_frame,
            text="Upscale with Real-ESRGAN",
            variable=self.upscale_var,
            command=self.apply_changes
        )
        self.upscale_check.grid(row=0, column=2, padx=5, pady=5)

        # Transparency option
        self.transparency_var = tk.IntVar()
        self.transparency_check = tk.Checkbutton(
            self.control_frame,
            text="Enforce Transparent Background",
            variable=self.transparency_var,
            command=self.apply_changes
        )
        self.transparency_check.grid(row=1, column=2, padx=5, pady=5)

        # Apply and Save Buttons
        self.apply_button = tk.Button(self.control_frame, text="Apply Changes", command=self.apply_changes)
        self.apply_button.grid(row=3, column=0, padx=5, pady=5)
        self.save_button = tk.Button(self.control_frame, text="Save Processed Image", command=self.save_image)
        self.save_button.grid(row=3, column=1, padx=5, pady=5)

    def load_images(self):
        filetypes = [("Image files", "*.jpg *.jpeg *.png *.bmp"), ("All files", "*.*")]
        filenames = filedialog.askopenfilenames(title="Select Images", filetypes=filetypes)
        if filenames:
            for filename in filenames:
                self.images.append(filename)
                try:
                    img = Image.open(filename)
                    img.thumbnail((100, 100))
                    self.thumbnails.append(ImageTk.PhotoImage(img))
                    self.listbox.insert(tk.END, os.path.basename(filename))
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to load image {filename}.\nError: {e}")
            if self.images:
                self.current_index = 0
                self.show_image(self.current_index)

    def on_thumbnail_select(self, event):
        selection = event.widget.curselection()
        if selection:
            self.current_index = selection[0]
            self.show_image(self.current_index)

    def show_image(self, index):
        try:
            filepath = self.images[index]
            self.original_image = Image.open(filepath).convert("RGBA")
            # Show a scaled preview of the original image
            preview_orig = self.get_preview_image(self.original_image)
            orig_img_tk = ImageTk.PhotoImage(preview_orig)
            self.original_label.config(image=orig_img_tk)
            self.original_label.image = orig_img_tk

            # Process image with current settings and show preview
            self.apply_changes()
        except Exception as e:
            messagebox.showerror("Error", f"Error loading image: {e}")

    def on_resize_option_change(self, event):
        if self.resize_option.get() == "Custom":
            self.custom_width.config(state=tk.NORMAL)
            self.custom_height.config(state=tk.NORMAL)
        else:
            self.custom_width.config(state=tk.DISABLED)
            self.custom_height.config(state=tk.DISABLED)
        self.apply_changes()  # Update preview when resize option changes

    def get_preview_image(self, img, max_width=MAX_PREVIEW_WIDTH, max_height=MAX_PREVIEW_HEIGHT):
        """Returns a version of img scaled down to fit within max_width and max_height (for display)."""
        w, h = img.size
        scale = min(max_width / w, max_height / h, 1)  # Do not upscale for preview
        if scale < 1:
            try:
                resample_filter = Image.Resampling.LANCZOS
            except AttributeError:
                resample_filter = Image.LANCZOS
            new_size = (int(w * scale), int(h * scale))
            return img.resize(new_size, resample_filter)
        return img

    def apply_changes(self):
        self.process_image()

    def process_image(self):
        if not self.original_image:
            return
        # Work on a copy of the full resolution image
        img = self.original_image.copy()
        width, height = img.size
        new_width, new_height = width, height

        option = self.resize_option.get()
        if option == "Half":
            new_width, new_height = width // 2, height // 2
        elif option == "Double":
            new_width, new_height = width * 2, height * 2
        elif option == "Custom":
            try:
                new_width = int(self.custom_width.get()) if self.custom_width.get() != "" else width
                new_height = int(self.custom_height.get()) if self.custom_height.get() != "" else height
            except Exception as e:
                messagebox.showerror("Error", "Invalid custom dimensions. Please enter integer values.")
                return
        elif option == "16:9":
            # Force to 16:9 by keeping original width and adjusting height
            new_width = width
            new_height = round(width * 9 / 16)
        elif option == "9:16":
            # Force to 9:16 by keeping original height and adjusting width
            new_height = height
            new_width = round(height * 9 / 16)

        # Resize if dimensions have changed
        if (new_width, new_height) != (width, height):
            try:
                try:
                    resample_filter = Image.Resampling.LANCZOS  # For Pillow 10.0+
                except AttributeError:
                    resample_filter = Image.LANCZOS  # For older Pillow versions
                img = img.resize((new_width, new_height), resample_filter)
            except Exception as e:
                messagebox.showerror("Error", f"Error resizing image: {e}")
                return

        # Upscaling with Real-ESRGAN if enabled
        if self.upscale_var.get():
            if RealESRGAN is None:
                messagebox.showerror("Error", "Real-ESRGAN library is not installed.")
            else:
                if self.esrgan_model is None:
                    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
                    try:
                        self.esrgan_model = RealESRGAN(device, scale=2)
                    except Exception as e:
                        messagebox.showerror("Error", f"Failed to initialize Real-ESRGAN: {e}")
                        return
                try:
                    img = self.esrgan_model.predict(img)
                except Exception as e:
                    messagebox.showerror("Upscaling Error", f"Error during upscaling: {e}")

        # Enforce transparent background if selected
        if self.transparency_var.get():
            img = self.make_background_transparent(img)

        # Save the full processed image for saving
        self.processed_image = img

        # For preview, scale down the processed image if needed
        preview_img = self.get_preview_image(self.processed_image)
        processed_img_tk = ImageTk.PhotoImage(preview_img)
        self.processed_label.config(image=processed_img_tk)
        self.processed_label.image = processed_img_tk

    def make_background_transparent(self, img):
        # Convert nearly white pixels to transparent
        datas = img.getdata()
        newData = []
        for item in datas:
            if item[0] > 240 and item[1] > 240 and item[2] > 240:
                newData.append((255, 255, 255, 0))
            else:
                newData.append(item)
        img.putdata(newData)
        return img

    def save_image(self):
        if self.processed_image is None:
            messagebox.showerror("Error", "No processed image to save.")
            return

        file_path = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG files", "*.png")])
        if file_path:
            # If the file already exists, add a timestamp to the filename.
            if os.path.exists(file_path):
                base, ext = os.path.splitext(file_path)
                timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
                file_path = f"{base}_{timestamp}{ext}"
            try:
                self.processed_image.save(file_path, "PNG")
                messagebox.showinfo("Success", f"Image saved to {file_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save image: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = ImageProcessorApp(root)
    root.mainloop()
