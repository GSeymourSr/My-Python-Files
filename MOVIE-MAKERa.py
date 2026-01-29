import pygame
import random
import math
import os
import numpy as np
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime
from dataclasses import dataclass
from moviepy.editor import VideoClip, AudioFileClip, concatenate_audioclips, VideoFileClip
import moviepy.audio.fx.all as afx

# ==========================================
# 1. CONFIGURATION DATACLASS
# ==========================================
@dataclass
class RenderConfig:
    """Holds all animation and rendering settings."""
    width: int = 1920
    height: int = 1080
    fps: int = 30
    duration: int = 60
    
    # Animation Settings
    max_sprites: int = 15
    spawn_interval: float = 1.5  # Seconds between spawns
    bg_interval: float = 5.0     # Seconds between background changes
    
    # Physics Settings
    min_speed: float = 2.0
    max_speed: float = 8.0
    min_size: int = 150
    max_size: int = 400
    min_rot: float = -3.0
    max_rot: float = 3.0

# ==========================================
# 2. VISUAL ENGINE
# ==========================================
class SpriteObj:
    """A single floating image with physics."""
    def __init__(self, image, config: RenderConfig):
        self.original_image = image
        self.w, self.h = config.width, config.height
        
        # Start off-screen
        if random.choice([True, False]):
            start_x = random.choice([-200, self.w + 200])
            start_y = random.randint(0, self.h)
        else:
            start_x = random.randint(0, self.w)
            start_y = random.choice([-200, self.h + 200])

        self.x, self.y = float(start_x), float(start_y)
        target = (random.randint(0, self.w), random.randint(0, self.h))
        
        # Calculate velocity
        speed = random.uniform(config.min_speed, config.max_speed)
        dx = target[0] - self.x
        dy = target[1] - self.y
        dist = math.hypot(dx, dy)
        self.vx = (dx / dist) * speed if dist > 0 else 0
        self.vy = (dy / dist) * speed if dist > 0 else 0
        
        # Rotation
        self.angle = 0
        self.rot_speed = random.uniform(config.min_rot, config.max_rot)
        
        self.image = self.original_image
        self.rect = self.image.get_rect(center=(int(self.x), int(self.y)))

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.angle += self.rot_speed
        
        self.image = pygame.transform.rotate(self.original_image, self.angle)
        self.rect = self.image.get_rect(center=(int(self.x), int(self.y)))

class RenderEngine:
    def __init__(self, config: RenderConfig, bg_files, fg_files):
        self.config = config
        
        # Headless Pygame
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        pygame.init()
        self.screen = pygame.display.set_mode((config.width, config.height))
        
        # Load Assets
        self.bg_assets = self._load_backgrounds(bg_files)
        self.fg_images = self._load_foregrounds(fg_files)
        
        self.sprites = []
        self.current_bg = None # The dictionary object of the current BG
        self.bg_start_time = 0 # When the current BG started appearing
        self.last_bg_switch = -config.bg_interval # trigger immediately
        self.last_spawn_time = -config.spawn_interval # trigger immediately

    def _load_backgrounds(self, file_paths):
        """Loads both Images and Videos as background assets."""
        assets = []
        for path in file_paths:
            ext = os.path.splitext(path)[1].lower()
            try:
                if ext in ['.mp4', '.mov', '.avi', '.mkv']:
                    # It is a video
                    clip = VideoFileClip(path)
                    # Resize video to fit screen, no audio needed for BG
                    clip = clip.resize(newsize=(self.config.width, self.config.height)).without_audio()
                    assets.append({'type': 'video', 'data': clip, 'path': path})
                else:
                    # It is an image
                    img = pygame.image.load(path).convert_alpha()
                    img = pygame.transform.scale(img, (self.config.width, self.config.height))
                    assets.append({'type': 'image', 'data': img, 'path': path})
            except Exception as e:
                print(f"Skipping bad BG file {path}: {e}")
        return assets

    def _load_foregrounds(self, file_paths):
        imgs = []
        for path in file_paths:
            try:
                img = pygame.image.load(path).convert_alpha()
                imgs.append(img)
            except Exception as e:
                print(f"Skipping bad FG image {path}: {e}")
        return imgs

    def get_frame(self, t):
        """Called by MoviePy at time `t` (seconds)."""
        
        # 1. Background Switching Logic
        if self.bg_assets and (t - self.last_bg_switch >= self.config.bg_interval):
            self.current_bg = random.choice(self.bg_assets)
            self.last_bg_switch = t
            self.bg_start_time = t

        # 2. Draw Background
        if self.current_bg:
            if self.current_bg['type'] == 'image':
                # Standard Image Blit
                self.screen.blit(self.current_bg['data'], (0, 0))
            elif self.current_bg['type'] == 'video':
                # Video Logic
                clip = self.current_bg['data']
                # Calculate local time in video (looping)
                local_t = (t - self.bg_start_time) % clip.duration
                
                # Get frame from MoviePy (returns Numpy array [H, W, 3])
                frame_np = clip.get_frame(local_t)
                
                # Convert to Pygame Surface
                # MoviePy is Y,X (Rows, Cols), Pygame needs X,Y (Cols, Rows) -> swapaxes
                video_surf = pygame.surfarray.make_surface(frame_np.swapaxes(0, 1))
                self.screen.blit(video_surf, (0, 0))
        else:
            self.screen.fill((30, 30, 30))

        # 3. Spawn Sprites Logic
        if self.fg_images and len(self.sprites) < self.config.max_sprites:
            if t - self.last_spawn_time >= self.config.spawn_interval:
                self._spawn_sprite()
                self.last_spawn_time = t

        # 4. Update & Draw Sprites
        for sprite in self.sprites[:]:
            sprite.update()
            self.screen.blit(sprite.image, sprite.rect)
            
            # Remove if out of bounds (padding of 300px)
            if (sprite.x > self.config.width + 300 or sprite.x < -300 or 
                sprite.y > self.config.height + 300 or sprite.y < -300):
                self.sprites.remove(sprite)

        # 5. Return Numpy Array for MoviePy output
        return pygame.surfarray.array3d(self.screen).transpose([1, 0, 2])

    def _spawn_sprite(self):
        img = random.choice(self.fg_images)
        size = random.randint(self.config.min_size, self.config.max_size)
        scaled = pygame.transform.smoothscale(img, (size, size))
        self.sprites.append(SpriteObj(scaled, self.config))

    def close(self):
        """Clean up video clips to free memory."""
        for asset in self.bg_assets:
            if asset['type'] == 'video':
                try:
                    asset['data'].close()
                except:
                    pass

# ==========================================
# 3. AUDIO HANDLER
# ==========================================
def prepare_audio(audio_files, target_duration):
    if not audio_files: return None
    
    clips = []
    current_duration = 0
    random.shuffle(audio_files) # Shuffle playlist
    
    # Loop tracks until duration is met
    while current_duration < target_duration:
        for f in audio_files:
            if current_duration >= target_duration: break
            try:
                clip = AudioFileClip(f)
                clips.append(clip)
                current_duration += clip.duration
            except Exception as e:
                print(f"Skipped bad audio file {f}: {e}")
                
    if not clips: return None
    
    final_audio = concatenate_audioclips(clips)
    final_audio = final_audio.set_duration(target_duration)
    final_audio = afx.audio_fadeout(final_audio, 3) # Smooth fadeout at end
    return final_audio

# ==========================================
# 4. GUI - GREG SEYMOUR AI MOVIE MAKER
# ==========================================
class AssetManager:
    """Helper to manage file/folder lists in the UI."""
    def __init__(self, listbox):
        self.listbox = listbox
        self.files = set()

    def add_files(self, exts):
        files = filedialog.askopenfilenames(filetypes=[("Media", exts)])
        for f in files:
            if f not in self.files:
                self.files.add(f)
                self.listbox.insert(tk.END, os.path.basename(f))

    def add_folder(self, exts):
        folder = filedialog.askdirectory()
        if not folder: return
        for f in os.listdir(folder):
            if any(f.lower().endswith(ext.replace("*","")) for ext in exts):
                path = os.path.join(folder, f)
                if path not in self.files:
                    self.files.add(path)
                    self.listbox.insert(tk.END, f)

    def clear(self):
        self.files.clear()
        self.listbox.delete(0, tk.END)

class MovieMakerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Greg Seymour AI Movie Maker Pro v2.1")
        self.root.geometry("850x650")
        
        # Set Theme
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TButton", font=("Arial", 10, "bold"))
        style.configure("Title.TLabel", font=("Helvetica", 18, "bold"), foreground="#2C3E50")
        
        # Title
        ttk.Label(root, text="🎥 GREG SEYMOUR AI MOVIE MAKER", style="Title.TLabel").pack(pady=15)

        # Notebook (Tabs)
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(expand=True, fill='both', padx=10, pady=5)
        
        self.tab_assets = ttk.Frame(self.notebook)
        self.tab_settings = ttk.Frame(self.notebook)
        self.tab_output = ttk.Frame(self.notebook)
        
        self.notebook.add(self.tab_assets, text="1. Assets & Media")
        self.notebook.add(self.tab_settings, text="2. Animation Settings")
        self.notebook.add(self.tab_output, text="3. Output & Render")

        self._build_assets_tab()
        self._build_settings_tab()
        self._build_output_tab()

    def _build_assets_tab(self):
        # 3 Columns for Backgrounds, Foregrounds, Audio
        frame = ttk.Frame(self.tab_assets)
        frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # UPDATED: Added video extensions to Backgrounds
        self.bg_mgr = self._create_asset_column(frame, 0, "Backgrounds (Img/Video)", 
                                              ('.jpg', '.png', '.jpeg', '.mp4', '.mov', '.avi'))
        self.fg_mgr = self._create_asset_column(frame, 1, "Floating Sprites", ('.png', '.gif'))
        self.aud_mgr = self._create_asset_column(frame, 2, "Audio / Music", ('.mp3', '.wav', '.m4a'))

    def _create_asset_column(self, parent, col, title, exts):
        f = ttk.LabelFrame(parent, text=title)
        f.grid(row=0, column=col, sticky="nsew", padx=5)
        parent.grid_columnconfigure(col, weight=1)
        
        lb = tk.Listbox(f, height=15)
        lb.pack(fill='both', expand=True, padx=5, pady=5)
        mgr = AssetManager(lb)
        
        btn_frame = ttk.Frame(f)
        btn_frame.pack(fill='x', padx=5, pady=5)
        
        # Helper to format extensions for display/usage
        formatted_exts = " ".join(exts)
        
        ttk.Button(btn_frame, text="+ Files", command=lambda: mgr.add_files(formatted_exts)).pack(side='left', expand=True, fill='x')
        ttk.Button(btn_frame, text="+ Folder", command=lambda: mgr.add_folder(exts)).pack(side='left', expand=True, fill='x')
        ttk.Button(btn_frame, text="Clear", command=mgr.clear).pack(side='left', expand=True, fill='x')
        return mgr

    def _build_settings_tab(self):
        f = ttk.Frame(self.tab_settings)
        f.pack(fill='both', expand=True, padx=20, pady=20)
        
        self.vars = {
            'max_sprites': tk.IntVar(value=15),
            'spawn_rate': tk.DoubleVar(value=1.5),
            'bg_rate': tk.DoubleVar(value=5.0),
            'speed_min': tk.DoubleVar(value=2.0),
            'speed_max': tk.DoubleVar(value=8.0),
            'size_min': tk.IntVar(value=100),
            'size_max': tk.IntVar(value=300),
            'fps': tk.IntVar(value=30),
            'duration': tk.IntVar(value=60)
        }
        
        row = 0
        def add_slider(label, var, from_, to, res):
            nonlocal row
            ttk.Label(f, text=label).grid(row=row, column=0, sticky='w', pady=5)
            val_lbl = ttk.Label(f, text=str(var.get()))
            val_lbl.grid(row=row, column=2, padx=10)
            
            def update_lbl(val):
                val_lbl.config(text=f"{float(val):.1f}" if isinstance(var, tk.DoubleVar) else str(int(float(val))))
                
            scale = ttk.Scale(f, from_=from_, to=to, variable=var, command=update_lbl)
            scale.grid(row=row, column=1, sticky='ew', padx=10)
            row += 1

        f.columnconfigure(1, weight=1)
        add_slider("Total Video Duration (seconds):", self.vars['duration'], 5, 300, 1)
        add_slider("Video FPS (Frames per second):", self.vars['fps'], 15, 60, 1)
        ttk.Separator(f, orient='horizontal').grid(row=row, columnspan=3, sticky='ew', pady=10); row+=1
        add_slider("Max Images on Screen:", self.vars['max_sprites'], 1, 100, 1)
        add_slider("Spawn Interval (Seconds):", self.vars['spawn_rate'], 0.1, 5.0, 0.1)
        add_slider("Background Change Interval (Seconds):", self.vars['bg_rate'], 1.0, 30.0, 0.5)
        ttk.Separator(f, orient='horizontal').grid(row=row, columnspan=3, sticky='ew', pady=10); row+=1
        add_slider("Min Size (Pixels):", self.vars['size_min'], 50, 500, 1)
        add_slider("Max Size (Pixels):", self.vars['size_max'], 50, 800, 1)
        add_slider("Min Speed:", self.vars['speed_min'], 0.1, 15.0, 0.1)
        add_slider("Max Speed:", self.vars['speed_max'], 0.1, 20.0, 0.1)

    def _build_output_tab(self):
        f = ttk.Frame(self.tab_output)
        f.pack(fill='both', expand=True, padx=30, pady=30)
        
        self.out_dir = tk.StringVar()
        self.out_name = tk.StringVar(value="gregs_movie")
        
        # Directory Selection
        ttk.Label(f, text="Save To Directory:").pack(anchor='w')
        dir_frame = ttk.Frame(f)
        dir_frame.pack(fill='x', pady=5)
        ttk.Entry(dir_frame, textvariable=self.out_dir).pack(side='left', fill='x', expand=True)
        ttk.Button(dir_frame, text="Browse", command=lambda: self.out_dir.set(filedialog.askdirectory())).pack(side='right')
        
        # Filename
        ttk.Label(f, text="Base Filename (Timestamp will be added automatically):").pack(anchor='w', pady=(20, 0))
        ttk.Entry(f, textvariable=self.out_name, font=("Arial", 12)).pack(fill='x', pady=5)
        
        # Render Button
        self.btn_render = tk.Button(f, text="🎬 RENDER MOVIE 🎬", bg="#E74C3C", fg="white", 
                                    font=("Helvetica", 16, "bold"), command=self.render)
        self.btn_render.pack(pady=40, ipadx=20, ipady=15)
        
        self.status_lbl = ttk.Label(f, text="", font=("Arial", 10, "italic"))
        self.status_lbl.pack()

    def render(self):
        if not self.out_dir.get():
            messagebox.showerror("Error", "Please select an output directory.")
            return
        if not self.bg_mgr.files and not self.fg_mgr.files:
            messagebox.showerror("Error", "Please add at least some images/videos in the Assets tab.")
            return

        # Disable UI during render
        self.btn_render.config(state='disabled', text="RENDERING... CHECK CONSOLE")
        self.status_lbl.config(text="Processing engine... Do not close window.")
        self.root.update()

        engine = None
        try:
            # Create Config
            config = RenderConfig(
                fps=self.vars['fps'].get(),
                duration=self.vars['duration'].get(),
                max_sprites=self.vars['max_sprites'].get(),
                spawn_interval=self.vars['spawn_rate'].get(),
                bg_interval=self.vars['bg_rate'].get(),
                min_size=self.vars['size_min'].get(),
                max_size=self.vars['size_max'].get(),
                min_speed=self.vars['speed_min'].get(),
                max_speed=self.vars['speed_max'].get()
            )

            # Setup Engine
            engine = RenderEngine(config, list(self.bg_mgr.files), list(self.fg_mgr.files))
            
            # Setup MoviePy Clip
            clip = VideoClip(make_frame=engine.get_frame, duration=config.duration)
            
            # Process Audio
            if self.aud_mgr.files:
                audio_clip = prepare_audio(list(self.aud_mgr.files), config.duration)
                if audio_clip:
                    clip = clip.set_audio(audio_clip)

            # Timestamp Logic to prevent overwrites
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            base_name = self.out_name.get().replace(".mp4", "")
            final_filename = f"{base_name}_{timestamp}.mp4"
            final_path = os.path.join(self.out_dir.get(), final_filename)

            # Render
            clip.write_videofile(final_path, fps=config.fps, codec='libx264', audio_codec='aac')
            
            messagebox.showinfo("Success!", f"Movie Rendered Successfully!\nSaved to: {final_path}")

        except Exception as e:
            import traceback
            traceback.print_exc()
            messagebox.showerror("Rendering Error", str(e))
        finally:
            if engine:
                engine.close()
            self.btn_render.config(state='normal', text="🎬 RENDER MOVIE 🎬")
            self.status_lbl.config(text="")

if __name__ == "__main__":
    root = tk.Tk()
    app = MovieMakerGUI(root)
    root.mainloop()