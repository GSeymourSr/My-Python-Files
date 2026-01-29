import os
import time
from tkinter import Tk, filedialog

def embed_files():
    # Open file dialog for user to select multiple files
    Tk().withdraw()  # Hide the root window
    file_paths = filedialog.askopenfilenames(title="Select HTML, CSS, and JS files")
    
    if not file_paths:
        print("No files selected.")
        return
    
    # Separate files by type
    html_file = next((f for f in file_paths if f.endswith('.html')), None)
    css_files = [f for f in file_paths if f.endswith('.css')]
    js_files = [f for f in file_paths if f.endswith('.js')]
    
    if not html_file:
        print("No HTML file selected. Please select at least one HTML file.")
        return
    
    output_dir = os.path.dirname(html_file)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(output_dir, f"combined_{timestamp}.html")
    
    try:
        # Read HTML file
        with open(html_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # Embed CSS files
        css_content = "".join([f"<style>{open(f, 'r', encoding='utf-8').read()}</style>" for f in css_files])
        html_content = html_content.replace('</head>', f'{css_content}\n</head>')
        
        # Embed JavaScript files
        js_content = "".join([f"<script>{open(f, 'r', encoding='utf-8').read()}</script>" for f in js_files])
        html_content = html_content.replace('</body>', f'{js_content}\n</body>')
        
        # Write the output file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"Successfully created {output_file}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    embed_files()
