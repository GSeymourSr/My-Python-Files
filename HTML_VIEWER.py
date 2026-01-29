import tkinter as tk
from tkinter import filedialog, messagebox
import random
import time
import threading
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

class HTMLViewer:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("HTML Files Viewer")
        self.selected_files = []
        self.running = False
        self.setup_gui()

    def setup_gui(self):
        # Button to select HTML files
        select_button = tk.Button(self.root, text="Select HTML Files", command=self.select_files)
        select_button.pack(pady=10)

        # Entry to set the duration (in seconds)
        duration_label = tk.Label(self.root, text="Duration (seconds):")
        duration_label.pack()
        self.duration_entry = tk.Entry(self.root)
        self.duration_entry.insert(0, "60")  # default is 60 seconds
        self.duration_entry.pack()

        # Radio buttons to select playback mode: Order or Random
        mode_label = tk.Label(self.root, text="Playback Mode:")
        mode_label.pack()
        self.mode_var = tk.StringVar(value="order")
        order_rb = tk.Radiobutton(self.root, text="Order", variable=self.mode_var, value="order")
        order_rb.pack()
        random_rb = tk.Radiobutton(self.root, text="Random", variable=self.mode_var, value="random")
        random_rb.pack()

        # Button to start the slideshow
        start_button = tk.Button(self.root, text="Start Slideshow", command=self.start_slideshow)
        start_button.pack(pady=10)

        # Listbox to show the selected files
        self.files_listbox = tk.Listbox(self.root, width=50, height=10)
        self.files_listbox.pack(pady=10)

    def select_files(self):
        files = filedialog.askopenfilenames(
            title="Select HTML Files",
            filetypes=[("HTML files", "*.html")]
        )
        self.selected_files = list(files)
        self.update_listbox()

    def update_listbox(self):
        self.files_listbox.delete(0, tk.END)
        for file in self.selected_files:
            self.files_listbox.insert(tk.END, file)

    def start_slideshow(self):
        if not self.selected_files:
            messagebox.showwarning("Warning", "Please select HTML files first!")
            return
        if not self.running:
            self.running = True
            threading.Thread(target=self.run_slideshow, daemon=True).start()

    def run_slideshow(self):
        # Set up Chrome options for fullscreen, kiosk mode and hiding the cursor.
        chrome_options = Options()
        chrome_options.add_argument("--start-fullscreen")
        chrome_options.add_argument("--kiosk")
        chrome_options.add_argument("--cursor-none")

        try:
            driver = webdriver.Chrome(options=chrome_options)
        except Exception as e:
            print("Error launching Chrome driver:", e)
            self.running = False
            return

        try:
            # Read duration from the GUI (default is 60 seconds)
            try:
                duration = float(self.duration_entry.get())
            except:
                duration = 60

            mode = self.mode_var.get()  # "order" or "random"

            if mode == "order":
                idx = 0
                while self.running and self.selected_files:
                    current_file = self.selected_files[idx]
                    driver.get(f"file:///{current_file}")

                    # Inject JavaScript to listen for key events:
                    # - Escape: stop the slideshow
                    # - q: skip to the next file
                    driver.execute_script("""
                        window.skipFile = false;
                        window.exitSlideshow = false;
                        document.addEventListener('keydown', function(e) {
                            if (e.key === 'Escape') {
                                window.exitSlideshow = true;
                            }
                            if (e.key.toLowerCase() === 'q') {
                                window.skipFile = true;
                            }
                        });
                    """)

                    # Wait for the duration or until a key event occurs.
                    t_start = time.time()
                    while time.time() - t_start < duration:
                        time.sleep(0.2)
                        try:
                            if driver.execute_script("return window.exitSlideshow;"):
                                self.running = False
                                break
                            if driver.execute_script("return window.skipFile;"):
                                break
                        except Exception:
                            break  # in case the page was closed
                    if not self.running:
                        break
                    idx = (idx + 1) % len(self.selected_files)

            elif mode == "random":
                # In random mode, show every file once before reshuffling.
                while self.running and self.selected_files:
                    files_to_show = self.selected_files[:]
                    random.shuffle(files_to_show)
                    for current_file in files_to_show:
                        if not self.running:
                            break
                        driver.get(f"file:///{current_file}")
                        driver.execute_script("""
                            window.skipFile = false;
                            window.exitSlideshow = false;
                            document.addEventListener('keydown', function(e) {
                                if (e.key === 'Escape') {
                                    window.exitSlideshow = true;
                                }
                                if (e.key.toLowerCase() === 'q') {
                                    window.skipFile = true;
                                }
                            });
                        """)
                        t_start = time.time()
                        while time.time() - t_start < duration:
                            time.sleep(0.2)
                            try:
                                if driver.execute_script("return window.exitSlideshow;"):
                                    self.running = False
                                    break
                                if driver.execute_script("return window.skipFile;"):
                                    break
                            except Exception:
                                break
                        if not self.running:
                            break

            driver.quit()

        except Exception as e:
            print("Error during slideshow:", e)
            try:
                driver.quit()
            except Exception:
                pass
            self.running = False

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    viewer = HTMLViewer()
    viewer.run()
