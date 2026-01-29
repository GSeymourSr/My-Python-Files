import pygame
import random
import math
import os
import textwrap
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from datetime import datetime
from dataclasses import dataclass
from typing import List, Literal

# MoviePy Imports
from moviepy.editor import (
    VideoClip, AudioFileClip, concatenate_audioclips, 
    VideoFileClip, ImageClip, CompositeVideoClip, concatenate_videoclips, vfx
)
import moviepy.audio.fx.all as afx

# ==========================================
# 1. CONFIGURATION & PHYSICS ENGINE
# ==========================================
@dataclass
class PhysicsConfig:
    """Settings for the Floating/Physics Scenes"""
    max_sprites: int = 15
    spawn_interval: float = 1.0
    
    # Physics
    min_speed: float = 3.0
    max_speed: float = 9.0
    min_size: int = 150
    max_size: int = 400
    
    # Movement Control
    enable_rotation: bool = True
    movement_mode: str = "Random"  # Options: Random, Left->Right, Right->Left, Top->Down, Bottom->Up
    
    width: int = 1920
    height: int = 1080

class SpriteObj:
    """A single floating image with directional logic."""
    def __init__(self, image, config: PhysicsConfig):
        self.original_image = image
        self.w, self.h = config.width, config.height
        self.config = config
        
        # 1. Determine Position and Velocity based on Mode
        speed = random.uniform(config.min_speed, config.max_speed)
        
        if config.movement_mode == "Left->Right":
            self.x = -300
            self.y = random.randint(0, self.h)
            self.vx = speed
            self.vy = random.uniform(-1, 1) # Slight drift
        elif config.movement_mode == "Right->Left":
            self.x = self.w + 300
            self.y = random.randint(0, self.h)
            self.vx = -speed
            self.vy = random.uniform(-1, 1)
        elif config.movement_mode == "Top->Down":
            self.x = random.randint(0, self.w)
            self.y = -300
            self.vx = random.uniform(-1, 1)
            self.vy = speed
        elif config.movement_mode == "Bottom->Up":
            self.x = random.randint(0, self.w)
            self.y = self.h + 300
            self.vx = random.uniform(-1, 1)
            self.vy = -speed
        else: # Random (Bounce/Chaos)
            if random.choice([True, False]):
                self.x = random.choice([-200, self.w + 200])
                self.y = random.randint(0, self.h)
            else:
                self.x = random.randint(0, self.w)
                self.y = random.choice([-200, self.h + 200])
            
            target = (random.randint(0, self.w), random.randint(0, self.h))
            dx = target[0] - self.x
            dy = target[1] - self.y
            dist = math.hypot(dx, dy)
            self.vx = (dx / dist) * speed if dist > 0 else 0
            self.vy = (dy / dist) * speed if dist > 0 else 0

        # 2. Rotation Logic
        self.angle = 0
        if config.enable_rotation:
            self.rot_speed = random.uniform(-3.0, 3.0)
        else:
            self.rot_speed = 0
        
        self.image = self.original_image
        self.rect = self.image.get_rect(center=(int(self.x), int(self.y)))

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.angle += self.rot_speed
        
        if self.config.enable_rotation and self.rot_speed != 0:
            self.image = pygame.transform.rotate(self.original_image, self.angle)
        else:
            self.image = self.original_image
            
        self.rect = self.image.get_rect(center=(int(self.x), int(self.y)))

class FloatingSceneEngine:
    """Generates frames for the 'Floating Images' scenes."""
    def __init__(self, config: PhysicsConfig, bg_path, fg_paths):
        self.config = config
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        pygame.init()
        self.screen = pygame.display.set_mode((config.width, config.height))
        
        # Load BG
        self.bg_surf = None
        if bg_path:
            try:
                bg = pygame.image.load(bg_path).convert()
                self.bg_surf = pygame.transform.scale(bg, (config.width, config.height))
            except: pass
            
        # Load FGs
        self.fg_images = []
        for p in fg_paths:
            try:
                self.fg_images.append(pygame.image.load(p).convert_alpha())
            except: pass
            
        self.sprites = []
        self.last_spawn = -999

    def get_frame(self, t):
        # Draw BG
        if self.bg_surf:
            self.screen.blit(self.bg_surf, (0, 0))
        else:
            self.screen.fill((20, 20, 20))

        # Spawn
        if self.fg_images and (t - self.last_spawn >= self.config.spawn_interval):
            if len(self.sprites) < self.config.max_sprites:
                img = random.choice(self.fg_images)
                size = random.randint(self.config.min_size, self.config.max_size)
                scaled = pygame.transform.smoothscale(img, (size, size))
                self.sprites.append(SpriteObj(scaled, self.config))
                self.last_spawn = t

        # Update
        for s in self.sprites[:]:
            s.update()
            self.screen.blit(s.image, s.rect)
            # Kill if far off screen
            if (s.x < -400 or s.x > self.config.width + 400 or 
                s.y < -400 or s.y > self.config.height + 400):
                self.sprites.remove(s)
                
        return pygame.surfarray.array3d(self.screen).transpose([1, 0, 2])

# ==========================================
# 2. GUI APPLICATION
# ==========================================
class GregsMovieMaker:
    def __init__(self, root):
        self.root = root
        self.root.title("Greg Seymour AI Movie Maker Pro v3.0")
        self.root.geometry("1100x800")
        
        self.timeline_items = [] # Stores sequence of events
        self.audio_files = []
        
        self._setup_styles()
        self._build_ui()

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("Header.TLabel", font=("Helvetica", 20, "bold"), foreground="#2C3E50")
        style.configure("Sub.TLabel", font=("Helvetica", 12, "bold"))
        style.configure("BigBtn.TButton", font=("Helvetica", 12, "bold"), padding=10)

    def _build_ui(self):
        # Title
        ttk.Label(self.root, text="🎥 GREG SEYMOUR AI MOVIE MAKER", style="Header.TLabel").pack(pady=10)

        # Main Notebook
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(expand=True, fill='both', padx=10, pady=5)
        
        # Tabs
        self.tab_timeline = ttk.Frame(self.notebook)
        self.tab_physics = ttk.Frame(self.notebook)
        self.tab_audio = ttk.Frame(self.notebook)
        self.tab_help = ttk.Frame(self.notebook)
        
        self.notebook.add(self.tab_timeline, text="1. Storyboard & Timeline")
        self.notebook.add(self.tab_physics, text="2. Floating Scene Options")
        self.notebook.add(self.tab_audio, text="3. Background Music")
        self.notebook.add(self.tab_help, text="4. HELP / INSTRUCTIONS")

        self._build_timeline_tab()
        self._build_physics_tab()
        self._build_audio_tab()
        self._build_help_tab()
        
        # Bottom Render Bar
        frame_bot = ttk.Frame(self.root)
        frame_bot.pack(fill='x', padx=20, pady=20)
        
        self.btn_render = ttk.Button(frame_bot, text="🎬 RENDER FINAL MOVIE", style="BigBtn.TButton", command=self.render_movie)
        self.btn_render.pack(fill='x')
        self.status_var = tk.StringVar()
        ttk.Label(frame_bot, textvariable=self.status_var, font=("Arial", 10, "italic")).pack(pady=5)

    # ---------------- TAB 1: TIMELINE ----------------
    def _build_timeline_tab(self):
        f = self.tab_timeline
        
        # Left Side: Controls
        left_panel = ttk.LabelFrame(f, text="Add Scenes to Movie")
        left_panel.pack(side='left', fill='y', padx=10, pady=10)
        
        ttk.Label(left_panel, text="Step 1: Choose Scene Type", style="Sub.TLabel").pack(pady=10)
        
        # Buttons to add types
        ttk.Button(left_panel, text="+ Add Slideshow (Images)", command=self.add_slideshow_dialog).pack(fill='x', pady=5)
        ttk.Button(left_panel, text="+ Add Full Video", command=self.add_video_dialog).pack(fill='x', pady=5)
        ttk.Button(left_panel, text="+ Add Floating Overlay Scene", command=self.add_floating_dialog).pack(fill='x', pady=5)
        
        ttk.Separator(left_panel, orient='horizontal').pack(fill='x', pady=20)
        
        ttk.Button(left_panel, text="Remove Selected", command=self.remove_timeline_item).pack(fill='x', pady=5)
        ttk.Button(left_panel, text="Clear All", command=self.clear_timeline).pack(fill='x', pady=5)

        # Right Side: The List
        right_panel = ttk.LabelFrame(f, text="Movie Sequence (Top plays first)")
        right_panel.pack(side='right', fill='both', expand=True, padx=10, pady=10)
        
        self.timeline_list = tk.Listbox(right_panel, font=("Courier", 11))
        self.timeline_list.pack(fill='both', expand=True, padx=5, pady=5)

    def _refresh_listbox(self):
        self.timeline_list.delete(0, tk.END)
        for idx, item in enumerate(self.timeline_items):
            desc = f"{idx+1}. [{item['type'].upper()}] "
            if item['type'] == 'slideshow':
                desc += f"{len(item['files'])} images | {item['duration']}s | Trans: {item['transition']}"
            elif item['type'] == 'video':
                rev = " [REVERSED]" if item.get('reverse') else ""
                desc += f"{os.path.basename(item['file'])}{rev}"
            elif item['type'] == 'floating':
                desc += f"Duration: {item['duration']}s | BG: {os.path.basename(item['bg']) if item['bg'] else 'Solid'}"
            self.timeline_list.insert(tk.END, desc)

    # ---------------- TAB 2: PHYSICS ----------------
    def _build_physics_tab(self):
        f = self.tab_physics
        ttk.Label(f, text="Global Settings for 'Floating Overlay' Scenes", style="Sub.TLabel").pack(pady=10)
        
        self.phys_vars = {
            'spin': tk.BooleanVar(value=True),
            'direction': tk.StringVar(value="Random"),
            'spawn_rate': tk.DoubleVar(value=0.5),
            'speed': tk.DoubleVar(value=5.0),
            'max_count': tk.IntVar(value=20)
        }
        
        # Movement Mode
        grp_move = ttk.LabelFrame(f, text="Movement Control")
        grp_move.pack(fill='x', padx=20, pady=5)
        
        ttk.Label(grp_move, text="Movement Direction:").pack(side='left', padx=10)
        modes = ["Random", "Left->Right", "Right->Left", "Top->Down", "Bottom->Up"]
        ttk.OptionMenu(grp_move, self.phys_vars['direction'], modes[0], *modes).pack(side='left', padx=10)
        
        ttk.Checkbutton(grp_move, text="Enable Spinning/Rotation", variable=self.phys_vars['spin']).pack(side='left', padx=20)

        # Sliders
        grp_phys = ttk.LabelFrame(f, text="Speed & Density")
        grp_phys.pack(fill='x', padx=20, pady=5)
        
        def add_slider(parent, txt, var, min_v, max_v):
            frame = ttk.Frame(parent)
            frame.pack(fill='x', pady=5)
            ttk.Label(frame, text=txt, width=20).pack(side='left')
            ttk.Scale(frame, from_=min_v, to=max_v, variable=var).pack(side='left', fill='x', expand=True, padx=5)
            ttk.Label(frame, text="Low ------ High").pack(side='right')

        add_slider(grp_phys, "Movement Speed", self.phys_vars['speed'], 1.0, 15.0)
        add_slider(grp_phys, "Spawn Rate", self.phys_vars['spawn_rate'], 0.1, 2.0)
        add_slider(grp_phys, "Max Images on Screen", self.phys_vars['max_count'], 5, 50)

    # ---------------- TAB 3: AUDIO ----------------
    def _build_audio_tab(self):
        f = self.tab_audio
        ttk.Label(f, text="Background Music Playlist", style="Sub.TLabel").pack(pady=10)
        
        self.audio_list = tk.Listbox(f, height=10)
        self.audio_list.pack(fill='both', expand=True, padx=20)
        
        btn_frame = ttk.Frame(f)
        btn_frame.pack(pady=10)
        
        def add_music():
            files = filedialog.askopenfilenames(filetypes=[("Audio", "*.mp3 *.wav *.m4a")])
            for file in files:
                self.audio_files.append(file)
                self.audio_list.insert(tk.END, os.path.basename(file))
        
        def clear_music():
            self.audio_files.clear()
            self.audio_list.delete(0, tk.END)

        ttk.Button(btn_frame, text="Add Music Files", command=add_music).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Clear Playlist", command=clear_music).pack(side='left', padx=5)

    # ---------------- TAB 4: HELP ----------------
    def _build_help_tab(self):
        f = self.tab_help
        
        help_text = """
        GREG SEYMOUR AI MOVIE MAKER - USER MANUAL
        ===========================================
        
        HOW TO USE THE TIMELINE (Tab 1):
        --------------------------------
        This program works like a video editor. You add "Scenes" to the list, 
        and they will play one after another.
        
        1. SLIDESHOW MODE:
           - Choose a folder of images.
           - Set how long each image stays on screen.
           - Choose a transition (Fade, Crossfade, or None).
           
        2. VIDEO MODE:
           - Select a video file (mp4, mov).
           - "Reverse Playback": Check this to play the video backwards!
           
        3. FLOATING OVERLAY MODE:
           - This is the special Greg Seymour effect.
           - Select a Background Image.
           - Select a Folder of "Sprites" (Floating numbers, logos, etc).
           - These images will float around based on settings in Tab 2.
           
        PHYSICS SETTINGS (Tab 2):
        -------------------------
        - Movement Direction: Make numbers fly Left, Right, Up, Down, or Random.
        - Enable Spinning: Uncheck this if you want numbers to stay upright.
        - Speed: How fast they fly.
        
        AUDIO (Tab 3):
        --------------
        - Add music tracks here. They will loop automatically to fit the length 
          of your total movie.
          
        RENDERING:
        ----------
        - Click "RENDER FINAL MOVIE" at the bottom.
        - Be patient! Video processing takes time.
        """
        
        txt = scrolledtext.ScrolledText(f, font=("Consolas", 10), padx=20, pady=20)
        txt.insert(tk.END, help_text)
        txt.config(state='disabled') # Read only
        txt.pack(fill='both', expand=True)

    # ==========================================
    # DIALOGS
    # ==========================================
    def add_slideshow_dialog(self):
        files = filedialog.askopenfilenames(title="Select Images for Slideshow", filetypes=[("Images", "*.jpg *.png *.jpeg")])
        if not files: return
        
        # Simple Dialog
        top = tk.Toplevel(self.root)
        top.title("Slideshow Settings")
        
        tk.Label(top, text="Duration per Image (sec):").pack()
        dur_var = tk.DoubleVar(value=3.0)
        tk.Entry(top, textvariable=dur_var).pack()
        
        tk.Label(top, text="Transition:").pack()
        trans_var = tk.StringVar(value="Crossfade")
        ttk.OptionMenu(top, trans_var, "Crossfade", "Crossfade", "FadeIn/Out", "None").pack()
        
        def confirm():
            self.timeline_items.append({
                'type': 'slideshow',
                'files': files,
                'duration': dur_var.get(),
                'transition': trans_var.get()
            })
            self._refresh_listbox()
            top.destroy()
            
        tk.Button(top, text="Add to Timeline", command=confirm).pack(pady=10)

    def add_video_dialog(self):
        file = filedialog.askopenfilename(title="Select Video", filetypes=[("Video", "*.mp4 *.mov *.avi")])
        if not file: return
        
        top = tk.Toplevel(self.root)
        top.title("Video Settings")
        
        rev_var = tk.BooleanVar(value=False)
        tk.Checkbutton(top, text="Play Video in Reverse (Backwards)?", variable=rev_var).pack(pady=20, padx=20)
        
        def confirm():
            self.timeline_items.append({
                'type': 'video',
                'file': file,
                'reverse': rev_var.get()
            })
            self._refresh_listbox()
            top.destroy()
            
        tk.Button(top, text="Add to Timeline", command=confirm).pack(pady=10)

    def add_floating_dialog(self):
        top = tk.Toplevel(self.root)
        top.title("Floating Scene Setup")
        
        # BG
        bg_path = tk.StringVar()
        tk.Button(top, text="Select Background Image", command=lambda: bg_path.set(filedialog.askopenfilename())).pack(fill='x')
        lbl_bg = tk.Label(top, text="No BG selected (will use black)")
        lbl_bg.pack()
        
        # FG
        fg_files = []
        def get_fg():
            f = filedialog.askopenfilenames(title="Select Floating Sprites")
            if f: 
                fg_files.extend(f)
                lbl_fg.config(text=f"{len(fg_files)} sprites selected")
        
        tk.Button(top, text="Select Floating Images (Numbers/Logos)", command=get_fg).pack(fill='x')
        lbl_fg = tk.Label(top, text="0 sprites selected")
        lbl_fg.pack()
        
        tk.Label(top, text="Scene Duration (seconds):").pack()
        dur = tk.IntVar(value=10)
        tk.Entry(top, textvariable=dur).pack()
        
        def confirm():
            if not fg_files: return
            self.timeline_items.append({
                'type': 'floating',
                'bg': bg_path.get(),
                'fg': fg_files,
                'duration': dur.get()
            })
            self._refresh_listbox()
            top.destroy()
            
        tk.Button(top, text="Add to Timeline", command=confirm).pack(pady=10)

    def remove_timeline_item(self):
        sel = self.timeline_list.curselection()
        if sel:
            del self.timeline_items[sel[0]]
            self._refresh_listbox()

    def clear_timeline(self):
        self.timeline_items.clear()
        self._refresh_listbox()

    # ==========================================
    # RENDER LOGIC
    # ==========================================
    def render_movie(self):
        if not self.timeline_items:
            messagebox.showerror("Error", "Timeline is empty!")
            return
            
        out_path = filedialog.asksaveasfilename(defaultextension=".mp4", filetypes=[("MP4", "*.mp4")])
        if not out_path: return

        self.btn_render.config(state='disabled')
        self.status_var.set("Initializing Render Engine...")
        self.root.update()

        try:
            final_clips = []
            
            # --- 1. PROCESS TIMELINE ---
            for i, item in enumerate(self.timeline_items):
                self.status_var.set(f"Processing Scene {i+1}/{len(self.timeline_items)} ({item['type']})...")
                self.root.update()
                
                if item['type'] == 'slideshow':
                    # Create Image Clips
                    slide_clips = []
                    for img_path in item['files']:
                        clip = ImageClip(img_path).set_duration(item['duration'])
                        clip = clip.resize(height=1080) # Normalize height
                        # Center on 1920x1080 background
                        clip = CompositeVideoClip([clip.set_position("center")], size=(1920,1080))
                        
                        if item['transition'] == "Crossfade":
                            clip = clip.crossfadein(0.5)
                        elif item['transition'] == "FadeIn/Out":
                            clip = clip.fadein(0.5).fadeout(0.5)
                        slide_clips.append(clip)
                    
                    # Combine slides
                    final_clips.append(concatenate_videoclips(slide_clips, method="compose"))

                elif item['type'] == 'video':
                    vid = VideoFileClip(item['file'])
                    vid = vid.resize(height=1080)
                    # Center
                    vid = CompositeVideoClip([vid.set_position("center")], size=(1920,1080))
                    
                    if item.get('reverse'):
                        self.status_var.set(f"Reversing video (this takes time)...")
                        self.root.update()
                        vid = vid.fx(vfx.time_mirror) # Play backwards
                    
                    final_clips.append(vid)

                elif item['type'] == 'floating':
                    # Prepare Config from GUI Vars
                    p_conf = PhysicsConfig(
                        max_sprites=self.phys_vars['max_count'].get(),
                        spawn_interval=self.phys_vars['spawn_rate'].get(),
                        min_speed=self.phys_vars['speed'].get(),
                        max_speed=self.phys_vars['speed'].get() + 4.0,
                        enable_rotation=self.phys_vars['spin'].get(),
                        movement_mode=self.phys_vars['direction'].get()
                    )
                    
                    engine = FloatingSceneEngine(p_conf, item['bg'], item['fg'])
                    float_clip = VideoClip(make_frame=engine.get_frame, duration=item['duration'])
                    final_clips.append(float_clip)

            # --- 2. CONCATENATE VISUALS ---
            self.status_var.set("Stitching scenes together...")
            final_video = concatenate_videoclips(final_clips, method="compose")

            # --- 3. ADD AUDIO ---
            if self.audio_files:
                self.status_var.set("Processing Audio...")
                audio_clips_list = []
                cur_dur = 0
                target_dur = final_video.duration
                
                # Loop audio list until full
                while cur_dur < target_dur:
                    for af in self.audio_files:
                        if cur_dur >= target_dur: break
                        ac = AudioFileClip(af)
                        audio_clips_list.append(ac)
                        cur_dur += ac.duration
                
                if audio_clips_list:
                    comp_audio = concatenate_audioclips(audio_clips_list).set_duration(target_dur)
                    comp_audio = afx.audio_fadeout(comp_audio, 3)
                    final_video = final_video.set_audio(comp_audio)

            # --- 4. EXPORT ---
            self.status_var.set("Rendering Final MP4 (Check Console for Progress)...")
            self.root.update()
            
            final_video.write_videofile(out_path, fps=24, codec='libx264', audio_codec='aac')
            
            messagebox.showinfo("Success", "Movie Rendered Successfully!")
            self.status_var.set("Ready.")

        except Exception as e:
            import traceback
            traceback.print_exc()
            messagebox.showerror("Render Error", f"An error occurred:\n{str(e)}")
            self.status_var.set("Error.")
        finally:
            self.btn_render.config(state='normal')

if __name__ == "__main__":
    root = tk.Tk()
    app = GregsMovieMaker(root)
    root.mainloop()