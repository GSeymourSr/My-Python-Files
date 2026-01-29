import os
import sys
import threading
import subprocess
import pygame
import tkinter as tk
from tkinter import filedialog, messagebox
from datetime import datetime

# ==================================================
# APP CONFIG
# ==================================================
APP_TITLE = "VIDEO Factory v2"
DEFAULT_RES = (1280, 720)
BASE_NAME = "Render"

# ==================================================
# FFmpeg PIPE
# ==================================================
class FFmpegPipe:
    def __init__(self, size, fps, output_path):
        self.size = size
        self.fps = fps
        self.output_path = output_path
        self.proc = None

    def start(self):
        # Ensure ffmpeg is accessible in system path
        cmd = [
            "ffmpeg", "-y",
            "-f", "rawvideo",
            "-pix_fmt", "rgb24",
            "-s", f"{self.size[0]}x{self.size[1]}",
            "-r", str(self.fps),
            "-i", "-",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-crf", "17",
            "-pix_fmt", "yuv420p",
            self.output_path
        ]
        # On Windows, preventing a console window for ffmpeg might be desired,
        # but for debugging keep defaults or redirect stderr.
        self.proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stderr=subprocess.DEVNULL
        )

    def write(self, data):
        if self.proc:
            self.proc.stdin.write(data)

    def close(self):
        if self.proc:
            try:
                self.proc.stdin.close()
                self.proc.wait()
            except:
                pass

# ==================================================
# VIRTUAL TIME ENGINE
# ==================================================
class VirtualTime:
    def __init__(self, fps):
        self.fps = fps
        self.ms_per_frame = 1000 / fps
        self.time = 0

    def hijack(self):
        # Capture the instance of VirtualTime so the nested class can see it
        vt_instance = self

        def fake_get_ticks():
            return int(vt_instance.time)

        class FakeClock:
            def tick(self, fps=0):
                # Return the fixed time step defined in VirtualTime
                return int(vt_instance.ms_per_frame)
            
            def get_fps(self):
                return vt_instance.fps

        # Override Pygame time functions
        pygame.time.get_ticks = fake_get_ticks
        pygame.time.Clock = FakeClock

    def advance(self):
        self.time += self.ms_per_frame

# ==================================================
# SCRIPT WRAPPER
# ==================================================
def run_wrapped_script(
    script_path, fps, duration, preview,
    output_dir, status_label, stop_flag
):
    total_frames = fps * duration

    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output_path = os.path.join(
        output_dir, f"{BASE_NAME}_{timestamp}.mp4"
    )

    # Initialize Pygame in Headless or Preview mode
    pygame.init()
    flags = 0 if preview else pygame.HIDDEN
    
    # Note: We rely on the user script using this specific screen surface
    # or calling pygame.display.set_mode themselves.
    screen = pygame.display.set_mode(DEFAULT_RES, flags)
    pygame.display.set_caption(APP_TITLE)

    # Setup Virtual Time
    vtime = VirtualTime(fps)
    vtime.hijack()

    # Start FFmpeg
    encoder = FFmpegPipe(DEFAULT_RES, fps, output_path)
    encoder.start()

    # --- inject globals for wrapped script ---
    # We pass 'screen' so if the script uses it directly, it works.
    globals_dict = {
        "__file__": script_path,
        "__name__": "__main__",
        "pygame": pygame,
        "screen": screen
    }

    status_label.config(text="Running script...")

    try:
        # 1. Load the user script
        with open(script_path, "r", encoding="utf-8") as f:
            code = compile(f.read(), script_path, "exec")

        # 2. Execute the user script
        # NOTE: If the user script contains an infinite loop (while True), 
        # execution will stay here and NOT reach the render loop below 
        # unless the user script is specifically designed to run frame-by-frame.
        # This wrapper captures frames if the script draws and exits, 
        # or if we modify how the loop works (advanced injection).
        # For now, we execute as requested.
        exec(code, globals_dict)

        # 3. Explicit Render Loop (Fallback/Post-Process)
        # If the user script just defines variables/functions, this loop runs.
        for frame in range(total_frames):
            if stop_flag["stop"]:
                break

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    stop_flag["stop"] = True

            if preview:
                pygame.display.flip()

            # Capture Frame
            try:
                # Ensure we capture whatever is currently on the display
                s = pygame.display.get_surface()
                if s:
                    frame_bytes = pygame.image.tostring(s, "RGB")
                    encoder.write(frame_bytes)
            except Exception as e:
                print(f"Frame capture error: {e}")

            vtime.advance()

            if frame % fps == 0:
                status_label.config(
                    text=f"Frame {frame}/{total_frames}"
                )

    except Exception as e:
        # This catches errors in the user script
        messagebox.showerror("Render/Script Error", str(e))
        print(e)

    finally:
        encoder.close()
        pygame.quit()

    status_label.config(text=f"Done: {output_path}")
    try:
        os.startfile(os.path.abspath(output_path))
    except:
        pass

# ==================================================
# GUI
# ==================================================
def main():
    root = tk.Tk()
    root.title(APP_TITLE)
    root.geometry("520x420")
    root.resizable(False, False)

    stop_flag = {"stop": False}
    render_thread = {"t": None}
    script_path = tk.StringVar()

    # --- File Picker ---
    def choose_script():
        path = filedialog.askopenfilename(
            title="Select Pygame Script",
            filetypes=[("Python Files", "*.py")]
        )
        if path:
            script_path.set(path)

    tk.Label(root, text="Pygame Script").pack()
    tk.Entry(root, textvariable=script_path, width=55).pack()
    tk.Button(root, text="Browse", command=choose_script).pack(pady=5)

    # --- FPS ---
    tk.Label(root, text="FPS").pack()
    fps_var = tk.IntVar(value=60)
    tk.Entry(root, textvariable=fps_var).pack()

    # --- Duration ---
    tk.Label(root, text="Duration (seconds)").pack()
    dur_var = tk.IntVar(value=10)
    tk.Entry(root, textvariable=dur_var).pack()

    # --- Preview ---
    preview_var = tk.BooleanVar(value=True)
    tk.Checkbutton(root, text="Live Preview", variable=preview_var).pack()

    # --- Output Folder ---
    output_dir = tk.StringVar(value="renders")

    def choose_output():
        path = filedialog.askdirectory()
        if path:
            output_dir.set(path)

    tk.Label(root, text="Output Folder").pack()
    tk.Entry(root, textvariable=output_dir, width=55).pack()
    tk.Button(root, text="Browse", command=choose_output).pack(pady=5)

    status_label = tk.Label(root, text="Idle")
    status_label.pack(pady=10)

    # --- Controls ---
    def start_render():
        if not script_path.get():
            messagebox.showerror("Error", "No script selected")
            return

        if render_thread["t"] and render_thread["t"].is_alive():
            return

        stop_flag["stop"] = False

        render_thread["t"] = threading.Thread(
            target=run_wrapped_script,
            args=(
                script_path.get(),
                fps_var.get(),
                dur_var.get(),
                preview_var.get(),
                output_dir.get(),
                status_label,
                stop_flag
            ),
            daemon=True
        )
        render_thread["t"].start()

    def stop_render():
        stop_flag["stop"] = True
        status_label.config(text="Stopping...")

    tk.Button(root, text="Start Render", command=start_render).pack(pady=5)
    tk.Button(root, text="Stop Render", command=stop_render).pack()

    root.mainloop()

# ==================================================
# ENTRY
# ==================================================
if __name__ == "__main__":
    main()