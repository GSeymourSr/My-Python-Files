import tkinter as tk
from tkinter import filedialog
import random
import time
import threading
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains

class HTMLViewer:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("HTML Files Viewer")
        self.selected_files = []
        self.running = False
        self.setup_gui()
        
    def setup_gui(self):
        # Create and pack widgets
        select_button = tk.Button(self.root, text="Select HTML Files", command=self.select_files)
        select_button.pack(pady=10)
        
        start_button = tk.Button(self.root, text="Start Slideshow", command=self.start_slideshow)
        start_button.pack(pady=10)
        
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
            tk.messagebox.showwarning("Warning", "Please select HTML files first!")
            return
            
        if not self.running:
            self.running = True
            threading.Thread(target=self.run_slideshow, daemon=True).start()
            
    def run_slideshow(self):
        # Set up Chrome options for fullscreen
        chrome_options = Options()
        chrome_options.add_argument("--start-fullscreen")
        chrome_options.add_argument("--kiosk")
        chrome_options.add_argument("--cursor-none")  # Hide cursor
        
        driver = webdriver.Chrome(options=chrome_options)
        
        try:
            while self.running and len(self.selected_files) > 0:
                # Choose random file
                current_file = random.choice(self.selected_files)
                
                # Load the file
                driver.get(f"file:///{current_file}")
                
                # Add click event listener to exit fullscreen
                driver.execute_script("""
                    document.addEventListener('click', function() {
                        window.close();
                    });
                """)
                
                # Wait for 30 seconds
                time.sleep(30)
                
            driver.quit()
            self.running = False
            
        except Exception as e:
            print(f"Error: {e}")
            driver.quit()
            self.running = False
            
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    viewer = HTMLViewer()
    viewer.run()