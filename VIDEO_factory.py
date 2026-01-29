import tkinter as tk
from tkinter import filedialog, simpledialog, messagebox
import os
import shutil
import subprocess
import sys
import asyncio

# ==========================================
# CONFIGURATION
# ==========================================
FPS = 60
TEMP_FOLDER = "temp_render_frames"
OUTPUT_FILENAME = "Final_Render.mp4"

# ==========================================
# 1. FFMPEG VIDEO BUILDER
# ==========================================
def build_video_ffmpeg(source_folder, output_file):
    print(f"--- BUILDING VIDEO FROM {source_folder} ---")
    if not os.path.exists(source_folder) or not os.listdir(source_folder):
        return False

    cmd = [
        'ffmpeg', '-y',
        '-framerate', str(FPS),
        '-i', os.path.join(source_folder, 'frame_%05d.png'),
        '-c:v', 'libx264',
        '-pix_fmt', 'yuv420p',
        '-crf', '17',       
        '-preset', 'ultrafast', 
        output_file
    ]

    try:
        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        subprocess.run(cmd, check=True, startupinfo=startupinfo)
        return True
    except Exception as e:
        messagebox.showerror("FFmpeg Error", f"Is FFmpeg installed?\n{e}")
        return False

# ==========================================
# 2. PYTHON ENGINE (With Time Freeze)
# ==========================================
def process_python_file(file_path, duration):
    print("--- MODE: PYTHON TIME-FREEZE RENDER ---")
    
    with open(file_path, "r") as f:
        original_code = f.read()

    total_frames = duration * FPS
    abs_temp = os.path.abspath(TEMP_FOLDER).replace("\\", "/")

    # --- THE HIJACK CODE ---
    # This overwrites Pygame's time functions.
    # It forces the script to think exactly 16.6ms passes every frame.
    hijack_code = f"""
import pygame
import os
import sys
import shutil

# --- INJECTED RENDERER & TIME WARP ---
_R_DIR = r"{abs_temp}"
_R_MAX = {total_frames}
_R_CNT = 0
_R_VIRTUAL_TIME = 0     # The fake clock
_R_MS_PER_FRAME = 1000 / {FPS}  # 16.666 ms

if os.path.exists(_R_DIR): 
    try: shutil.rmtree(_R_DIR)
    except: pass
if not os.path.exists(_R_DIR): os.makedirs(_R_DIR)

print(f"\\n--- RENDERING STARTED ({{_R_MAX}} Frames) ---")

# 1. HIJACK THE CLOCK (pygame.time.get_ticks)
def _fake_get_ticks():
    return int(_R_VIRTUAL_TIME)

# 2. HIJACK THE DELTA TIME (clock.tick)
# Even if your script asks to wait, we just return 16ms and don't wait.
class _FakeClock:
    def tick(self, fps=0):
        return int(_R_MS_PER_FRAME)
    def get_fps(self):
        return {FPS}
    def get_time(self):
        return int(_R_MS_PER_FRAME)
    def get_rawtime(self):
        return int(_R_MS_PER_FRAME)

# 3. HIJACK THE DISPLAY FLIP
_orig_flip = pygame.display.flip
_orig_update = pygame.display.update

def _hijacked_flip():
    global _R_CNT, _R_VIRTUAL_TIME
    try:
        screen = pygame.display.get_surface()
        if screen:
            # Save the frame
            pygame.image.save(screen, os.path.join(_R_DIR, f"frame_{{_R_CNT:05d}}.png"))
            
            # Advance the fake clock ONLY after a frame is saved
            _R_CNT += 1
            _R_VIRTUAL_TIME += _R_MS_PER_FRAME
            
            if _R_CNT % 60 == 0: 
                print(f"Rendered: {{_R_CNT}}/{{_R_MAX}} (Sim Time: {{_R_VIRTUAL_TIME/1000:.1f}}s)")
            
            if _R_CNT >= _R_MAX:
                print("--- RENDER COMPLETE ---")
                pygame.quit()
                sys.exit()
    except Exception as e:
        pass
    # We do NOT call original flip, to save rendering time on screen (optional)
    # But usually good to keep it so you see progress, but it might flicker.
    _orig_flip()

# APPLY THE PATCHES
pygame.time.get_ticks = _fake_get_ticks
pygame.time.Clock = _FakeClock
pygame.time.wait = lambda x: None # Disable waiting
pygame.time.delay = lambda x: None # Disable delays
pygame.display.flip = _hijacked_flip
pygame.display.update = _hijacked_flip
# -------------------------
"""
    
    final_code = hijack_code + "\n" + original_code
    temp_script = os.path.join(os.path.dirname(file_path), "_temp_render_job.py")
    
    with open(temp_script, "w") as f:
        f.write(final_code)

    try:
        subprocess.run([sys.executable, temp_script], check=True)
        if build_video_ffmpeg(TEMP_FOLDER, OUTPUT_FILENAME):
            messagebox.showinfo("Success", f"Video Saved:\n{os.path.abspath(OUTPUT_FILENAME)}")
            os.startfile(os.path.abspath(OUTPUT_FILENAME))
    except subprocess.CalledProcessError:
        messagebox.showerror("Error", "Script crashed or finished early.")
    finally:
        if os.path.exists(temp_script): os.remove(temp_script)
        if os.path.exists(TEMP_FOLDER): shutil.rmtree(TEMP_FOLDER)

# ==========================================
# 3. HTML ENGINE (Keep as is)
# ==========================================
async def run_playwright_capture(url, duration):
    from playwright.async_api import async_playwright
    print("--- MODE: HTML TIME-WARP CAPTURE ---")
    abs_temp = os.path.abspath(TEMP_FOLDER)
    if os.path.exists(abs_temp): shutil.rmtree(abs_temp)
    os.makedirs(abs_temp)
    total_frames = duration * FPS
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={'width': 1920, 'height': 1080})
        
        # HTML Time Warp Injection
        await page.add_init_script("""
            const _FPS = 60;
            let _virtualTime = 0;
            window.Date.now = () => _virtualTime;
            window.performance.now = () => _virtualTime;
            window._callbacks = [];
            window.requestAnimationFrame = (cb) => {
                window._callbacks.push(cb);
                return Math.random();
            };
            window._nextFrame = () => {
                _virtualTime += (1000 / _FPS);
                const callbacks = window._callbacks;
                window._callbacks = [];
                callbacks.forEach(cb => cb(_virtualTime));
            };
        """)
        
        await page.goto(url)
        await page.wait_for_timeout(1000)
        
        for i in range(total_frames):
            path = os.path.join(abs_temp, f"frame_{i:05d}.png")
            await page.screenshot(path=path)
            await page.evaluate("window._nextFrame()")
            if i % 30 == 0: print(f"Captured: {i}/{total_frames}")

        await browser.close()
        return True

def process_html_file(file_path, duration):
    url = f"file:///{file_path.replace(os.sep, '/')}"
    try:
        asyncio.run(run_playwright_capture(url, duration))
        if build_video_ffmpeg(TEMP_FOLDER, OUTPUT_FILENAME):
            messagebox.showinfo("Success", f"HTML Video Saved:\n{os.path.abspath(OUTPUT_FILENAME)}")
            os.startfile(os.path.abspath(OUTPUT_FILENAME))
    except Exception as e:
        messagebox.showerror("Error", f"HTML Capture Failed: {e}")
    finally:
        if os.path.exists(TEMP_FOLDER): shutil.rmtree(TEMP_FOLDER)

# ==========================================
# MAIN GUI
# ==========================================
def main():
    root = tk.Tk()
    root.withdraw()
    file_path = filedialog.askopenfilename(
        title="Select Python or HTML File",
        filetypes=[("Code Files", "*.py;*.html;*.htm")]
    )
    if not file_path: return
    duration = simpledialog.askinteger("Settings", "Duration (seconds):", initialvalue=10)
    if not duration: return

    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".py":
        process_python_file(file_path, duration)
    elif ext in [".html", ".htm"]:
        process_html_file(file_path, duration)
    else:
        messagebox.showerror("Error", "Unsupported file type")

if __name__ == "__main__":
    main()