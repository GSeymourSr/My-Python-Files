import pygame
import math
import random
import colorsys
import os          # NEW: For folder management
import shutil      # NEW: For deleting old images
import subprocess  # NEW: For running FFmpeg

# --- Initialization ---
pygame.init()
screen_info = pygame.display.Info()
# NOTE: For rendering, sometimes Fullscreen is annoying. 
# You can change this to a fixed size (e.g., (1920, 1080)) if you prefer.
screen = pygame.display.set_mode((screen_info.current_w, screen_info.current_h), pygame.FULLSCREEN | pygame.SRCALPHA)
width, height = screen.get_size()
pygame.display.set_caption("Trimodal Hyperspirals")
pygame.mouse.set_visible(False)

# --- Utility Functions (Shared or Generic) ---
def hsv_to_rgb(h, s, v):
    return tuple(round(i * 255) for i in colorsys.hsv_to_rgb(h, s, v))

def rotate_3d(x, y, z, angle_x, angle_y, angle_z):
    cos_x, sin_x = math.cos(angle_x), math.sin(angle_x)
    y_rot_x, z_rot_x = y * cos_x - z * sin_x, y * sin_x + z * cos_x
    y, z = y_rot_x, z_rot_x
    cos_y, sin_y = math.cos(angle_y), math.sin(angle_y)
    x_rot_y, z_rot_y = x * cos_y + z * sin_y, -x * sin_y + z * cos_y
    x, z = x_rot_y, z_rot_y
    cos_z, sin_z = math.cos(angle_z), math.sin(angle_z)
    x_rot_z, y_rot_z = x * cos_z - y * sin_z, x * sin_z + y * cos_z
    return x_rot_z, y_rot_z, z

# --- Projection for Modern and Classic Newspirals1 Mode ---
def project_3d_to_2d_modern_classic(x, y, z, fov, current_width, current_height):
    if fov + z <= 1: return None, 1.0
    perspective_scale = fov / (fov + z)
    screen_x = int(x * perspective_scale + current_width / 2)
    screen_y = int(y * perspective_scale + current_height / 2)
    return (screen_x, screen_y), perspective_scale

# --- Palettes for Modern and Classic Newspirals1 Mode ---
_r_palette_val = 0 # Temp global for palette access to r
def get_modern_classic_palette_color(palette_name, t):
    global _r_palette_val
    # Simplified list for brevity, can be expanded as before
    if palette_name == "neon": return hsv_to_rgb(t % 1, 1, 1)
    elif palette_name == "pastel": return hsv_to_rgb((t * 0.5) % 1, 0.5, 1)
    elif palette_name == "fire": hue = 0.05 + 0.15 * (0.5 + 0.5 * math.sin(t * math.pi * 2)); return hsv_to_rgb(hue % 1.0, 1, 1)
    elif palette_name == "cool": hue = 0.5 + 0.2 * (0.5 + 0.5 * math.sin(t * math.pi * 2)); return hsv_to_rgb(hue % 1.0, 0.8, 1)
    elif palette_name == "rainbow": return hsv_to_rgb(t % 1, 1, 1)
    elif palette_name == "cyberpunk":
        hb = 0.8 if math.sin(t*5)>0 else 0.5; hue=(hb+math.sin(t*3)*0.1)%1; sat=0.9+0.1*math.sin(t*7); val=0.8+0.2*math.sin(t*10); return hsv_to_rgb(hue,sat,val)
    elif palette_name == "toxic": hue=(0.25+0.1*math.sin(t*5))%1; sat=1; val=0.8+0.2*math.sin(t*3); return hsv_to_rgb(hue,sat,val)
    elif palette_name == "ice": hue=0.55+0.05*math.sin(t*2); sat=0.3+0.2*math.sin(t*3); val=1; return hsv_to_rgb(hue,sat,val)
    elif palette_name == "bubblegum": hue=(0.9+0.05*math.sin(t*3))%1; sat=0.6+0.1*math.sin(t*2); val=1; return hsv_to_rgb(hue,sat,val)
    elif palette_name == "monochrome": v_osc=0.5+0.5*math.sin(t*5); v=int(50+205*v_osc); return(v,v,v)
    elif palette_name == "aurora":
        h1,h2=(0.33+0.1*math.sin(t*2))%1,(0.75+0.1*math.sin(t*2.5+1))%1; c1=hsv_to_rgb(h1,0.9,0.8+0.2*math.sin(t*5)); c2=hsv_to_rgb(h2,0.7,0.7+0.3*math.sin(t*6)); mix=0.5+0.5*math.sin(t*math.pi)
        return tuple(int(c1[i]*mix+c2[i]*(1-mix)) for i in range(3))
    elif palette_name == "nebula":
        h=(0.7+0.2*math.sin(t*1.5))%1; s=0.8+0.2*math.sin(t*3); v=0.6+0.4*math.sin(t*5+_r_palette_val*0.001); return hsv_to_rgb(h,s,v)
    elif palette_name == "lava_flow":
        hue = 0.02 + 0.08 * (0.5 + 0.5 * math.sin(t * math.pi * 1.5 + _r_palette_val * 0.002)) # Reds, oranges
        sat = 0.9 + 0.1 * math.sin(t*3)
        val = 0.7 + 0.3 * math.sin(t*4)
        return hsv_to_rgb(hue % 1.0, sat, val)
    elif palette_name == "deep_space":
        h = (0.65 + 0.15 * math.sin(t * 0.8 + _r_palette_val * 0.0005)) % 1.0 # Dark blues, purples
        s = 0.7 + 0.2 * math.sin(t*1.2)
        v = 0.2 + 0.4 * math.sin(t*2.0 + math.pi/2) # Darker, pulsing
        return hsv_to_rgb(h,s,v)
    else: return (255,255,255)

# --- GPT1_ORIGINAL MODE Specific Functions ---
def project_3d_to_2d_gpt1_original(x, y, z, fov, current_width, current_height): # Matched gpt1.py's signature
    if fov + z <= 1: return None, 1.0 # Basic check
    factor = fov / (fov + z)
    return (int(x * factor + current_width / 2), int(y * factor + current_height / 2)), factor

def get_gpt1_original_palette_color(name, t):
    # Palettes from gpt1.py, plus some new ones in its style
    if name == "neon": return hsv_to_rgb(t % 1, 1, 1)
    elif name == "pastel": return hsv_to_rgb((t * 0.5) % 1, 0.5, 1)
    elif name == "fire": return hsv_to_rgb((t * 0.2 + 0.05) % 1, 1, 1)
    elif name == "cool": return hsv_to_rgb((t * 0.3 + 0.6) % 1, 0.7, 1)
    elif name == "rainbow": return hsv_to_rgb((t + math.sin(t * 2)) % 1, 1, 1)
    elif name == "cyberpunk": return hsv_to_rgb((t * 0.8) % 1, 1, 0.9 + 0.1 * math.sin(t * 10))
    elif name == "toxic": return hsv_to_rgb((0.25 + 0.05 * math.sin(t * 5)) % 1, 1, 1)
    elif name == "ice": return hsv_to_rgb(0.55 + 0.05 * math.sin(t * 2), 0.4, 1)
    elif name == "bubblegum": return hsv_to_rgb((0.9 + 0.05 * math.sin(t * 3)) % 1, 0.5, 1)
    elif name == "monochrome": v = int(127 + 127 * math.sin(t * 5)); return (v, v, v)
    elif name == "electric_dream": hue = (t * 0.7 + math.sin(t*3)*0.1)%1; sat=1; val=0.8+0.2*math.cos(t*7); return hsv_to_rgb(hue,sat,val)
    elif name == "forest_glade": hue = (0.3 + 0.1 * math.sin(t*2))%1; sat=0.7+0.2*math.sin(t*4); val=0.6+0.3*math.sin(t*1); return hsv_to_rgb(hue,sat,val)
    elif name == "candy_shop": hue = (random.choice([0.05, 0.15, 0.6, 0.85]) + t*0.1)%1; sat=0.8; val=1; return hsv_to_rgb(hue,sat,val)
    else: return (255, 255, 255)

def generate_gpt1_original_single_config(): # Helper for list generation
    palettes = ["neon", "pastel", "fire", "cool", "rainbow", "cyberpunk", "toxic", "ice", 
                "bubblegum", "monochrome", "electric_dream", "forest_glade", "candy_shop"]
    return {
        'num_arms': random.randint(2, 10), 'rotation_speed': random.uniform(0.2, 1.5),
        'color_shift': random.uniform(0.01, 0.05), 'arm_width': random.randint(2, 6), # This is base_size for gpt1
        'spiral_tightness': random.uniform(15, 100), 'direction': random.choice([-1, 1]),
        'z_scale': random.uniform(60, 180), 'z_speed': random.uniform(0.5, 2), # Controls z-wave frequency and speed
        'palette': random.choice(palettes), 'distortion': random.uniform(0, 30),
        'shape_type': random.choice(['circle', 'square', 'cross']), # gpt1 shapes
        'glow': random.choice([True, False]), 'fade': random.randint(10, 40), # fade per layer
        'fov_gpt1': random.uniform(80, 150) # Specific FOV for this mode
    }

def generate_gpt1_original_config_list(num_layers=None):
    if num_layers is None: num_layers = random.randint(1,3)
    return [generate_gpt1_original_single_config() for _ in range(num_layers)]

def generate_gpt1_original_mode_params(num_layers_override=None):
    gpt1_configs_list = generate_gpt1_original_config_list(num_layers_override)
    # Determine overall fade_alpha for the mode from its internal configs
    fade_alpha = min(cfg.get('fade', 25) for cfg in gpt1_configs_list) if gpt1_configs_list else 25
    return {
        'is_gpt1_original_mode': True,
        'gpt1_configs': gpt1_configs_list,
        'fade_alpha': fade_alpha
    }

def draw_gpt1_original_mode_visuals(surface, time, params):
    global width, height
    gpt1_configs = params['gpt1_configs']
    max_radius = math.hypot(width, height) / 2 # As in gpt1.py

    for i, cfg in enumerate(gpt1_configs):
        num_arms = cfg['num_arms']; speed = cfg['rotation_speed']; color_shift = cfg['color_shift']
        arm_base_size = cfg['arm_width']; tightness = cfg['spiral_tightness']; direction = cfg['direction']
        z_wave_freq_scale = cfg['z_scale']; z_wave_speed = cfg['z_speed']; palette = cfg['palette']
        distortion = cfg['distortion']; shape_type = cfg['shape_type']; glow = cfg['glow']
        fov = cfg.get('fov_gpt1', 100)

        # gpt1 used 'step' based on arm_width. This is density.
        # arm_segment_length equiv for this mode.
        segment_density = max(1, arm_base_size * 2) # Denser for smaller base sizes

        for r in range(0, int(max_radius), segment_density):
            cfg_time = time + i * 0.5 # Per-layer time offset from gpt1
            angle = r / tightness + cfg_time * speed * direction
            # Z calculation from gpt1.py (sine wave along radius, plus overall sine wave)
            z = math.sin(r / z_wave_freq_scale + cfg_time * z_wave_speed) * 150 + math.sin(cfg_time + i) * 50

            for j in range(num_arms):
                a = angle + j * 2 * math.pi / num_arms
                x_3d = r * math.cos(a)
                y_3d = r * math.sin(a)

                if distortion > 0: # Distortion from gpt1.py
                    x_3d += math.sin(y_3d * 0.05 + cfg_time * 2) * distortion
                    y_3d += math.sin(x_3d * 0.05 + cfg_time * 2) * distortion

                projection_result, _ = project_3d_to_2d_gpt1_original(x_3d, y_3d, z, fov, width, height)
                if projection_result is None: continue
                px, py = projection_result
                
                # Color from gpt1.py palette
                c = get_gpt1_original_palette_color(palette, (r / max_radius + cfg_time * color_shift) % 1)
                
                # Size from gpt1.py (base size modified by z)
                current_size = max(1, int(arm_base_size * (1 + z / 300)))

                if 0 <= px < width and 0 <= py < height:
                    if glow and current_size > 1:
                        try:
                            # Simple glow for gpt1 style
                            glow_s = pygame.Surface((current_size * 4, current_size * 4), pygame.SRCALPHA)
                            pygame.draw.circle(glow_s, (*c, 40), (current_size*2, current_size*2), current_size*2)
                            surface.blit(glow_s, (px-current_size*2, py-current_size*2), special_flags=pygame.BLEND_RGBA_ADD)
                        except pygame.error: pass


                    if shape_type == 'circle': pygame.draw.circle(surface, c, (px, py), current_size)
                    elif shape_type == 'square': pygame.draw.rect(surface, c, (px-current_size//2, py-current_size//2, current_size, current_size))
                    elif shape_type == 'cross':
                        pygame.draw.line(surface, c, (px - current_size, py), (px + current_size, py), max(1, current_size//3+1))
                        pygame.draw.line(surface, c, (px, py - current_size), (px, py + current_size), max(1, current_size//3+1))

# --- CLASSIC NEWSPIRALS1 MODE Specific Functions ---
def generate_classic_mode_params():
    # ... (Content from previous version, unchanged) ...
    global width, height # Access current screen dimensions
    params = {
        'is_classic_mode': True, 'num_arms': random.randint(2, 15),
        'arm_segment_length': random.randint(4, 15),'spiral_tightness': random.uniform(10, 150),
        'direction': random.choice([-1, 1]),'rotation_speed': random.uniform(0.05, 1.5),
        'z_amplitude': random.uniform(100, 400),'z_frequency': random.uniform(50, 500),
        'z_speed': random.uniform(0.1, 2.0),'z_offset_amplitude': random.uniform(0, 100),
        'z_offset_speed': random.uniform(0.1, 3.0),'color_shift_speed': random.uniform(0.01, 0.2),
        'classic_color_mode': random.choice(['hue_radius', 'hue_time', 'full_spectrum_pulsing']),
        'saturation_base': random.uniform(0.7, 1.0),'saturation_pulse_freq': random.uniform(0.1, 2.0),
        'value_base': random.uniform(0.8, 1.0),'value_z_factor': random.uniform(-0.4, 0.1),
        'base_size': random.uniform(5, 25),'size_z_scaling': random.uniform(-0.3, 0.5),
        'shape_type': random.choice(['circle', 'square', 'line', 'circle']),
        'line_thickness': random.uniform(1, 4),'fov': random.uniform(200, 400),
        'camera_rotate_speed_x': random.uniform(-0.3, 0.3),'camera_rotate_speed_y': random.uniform(-0.3, 0.3),
        'camera_rotate_speed_z': random.uniform(-0.2, 0.2),'fade_alpha': random.randint(5, 30)
    }
    if params['shape_type'] == 'line': params['line_thickness'] = random.uniform(1.5, 6)
    else: params['base_size'] = random.uniform(8, 30)
    return params

def draw_classic_mode_visuals(surface, time, params, classic_last_points):
    # ... (Content from previous version, uses project_3d_to_2d_modern_classic) ...
    global width, height 
    max_radius = math.sqrt(width**2 + height**2) / 1.5 
    num_arms=params['num_arms']; rotation_speed=params['rotation_speed']; color_shift_speed=params['color_shift_speed']
    arm_segment_length=params['arm_segment_length']; spiral_tightness=params['spiral_tightness']; direction=params['direction']
    z_amplitude=params['z_amplitude']; z_frequency=params['z_frequency']; z_speed=params['z_speed']
    base_size_param=params['base_size']; size_z_scaling=params['size_z_scaling']; fov=params['fov']
    shape_type=params['shape_type']; classic_color_mode=params['classic_color_mode']; saturation_base=params['saturation_base']
    saturation_pulse_freq=params['saturation_pulse_freq']; value_base=params['value_base']; value_z_factor=params['value_z_factor']
    camera_rotate_speed_x=params['camera_rotate_speed_x']; camera_rotate_speed_y=params['camera_rotate_speed_y']
    camera_rotate_speed_z=params['camera_rotate_speed_z']; line_thickness=params['line_thickness']
    z_offset_amplitude=params['z_offset_amplitude']; z_offset_speed=params['z_offset_speed']
    cam_angle_x=time*camera_rotate_speed_x; cam_angle_y=time*camera_rotate_speed_y; cam_angle_z=time*camera_rotate_speed_z
    global_z_offset=math.sin(time*z_offset_speed)*z_offset_amplitude
    for r_classic in range(0,int(max_radius),arm_segment_length):
        if r_classic==0 and shape_type=='line': continue
        base_angle=(r_classic/spiral_tightness)+(time*rotation_speed*direction)
        z=math.sin(r_classic/z_frequency+time*z_speed)*z_amplitude+global_z_offset
        for arm in range(num_arms):
            arm_angle=base_angle+arm*(2*math.pi/num_arms); x_3d=r_classic*math.cos(arm_angle); y_3d=r_classic*math.sin(arm_angle)
            rotated_x,rotated_y,rotated_z=rotate_3d(x_3d,y_3d,z,cam_angle_x,cam_angle_y,cam_angle_z)
            projection_result,perspective_scale=project_3d_to_2d_modern_classic(rotated_x,rotated_y,rotated_z,fov,width,height)
            if projection_result is None: classic_last_points[arm]=None; continue
            projected_x,projected_y=projection_result
            if classic_color_mode=='hue_radius': hue=(r_classic/max_radius+time*color_shift_speed)%1.0
            elif classic_color_mode=='hue_time': hue=(time*color_shift_speed)%1.0
            elif classic_color_mode=='full_spectrum_pulsing': hue=(arm/num_arms+r_classic/(max_radius*2)+time*color_shift_speed)%1.0
            else: hue=(r_classic/max_radius+time*color_shift_speed)%1.0
            saturation=saturation_base+math.sin(time*saturation_pulse_freq)*(1-saturation_base)*0.8; saturation=max(0.1,min(1.0,saturation))
            value_z_effect=rotated_z*value_z_factor/z_amplitude if z_amplitude else 0; value=value_base-value_z_effect; value=max(0.1,min(1.0,value))
            color=hsv_to_rgb(hue,saturation,value)
            z_scale_mod=1.0-(rotated_z*size_z_scaling/z_amplitude) if z_amplitude else 1.0
            size=base_size_param*perspective_scale*max(0.1,z_scale_mod); size=max(1,int(size))
            if shape_type=='circle': pygame.draw.circle(surface,color,(projected_x,projected_y),max(1,size//2))
            elif shape_type=='square': rect=pygame.Rect(projected_x-size//2,projected_y-size//2,size,size); pygame.draw.rect(surface,color,rect)
            elif shape_type=='line':
                 last_point=classic_last_points.get(arm)
                 if last_point: pygame.draw.line(surface,color,last_point,(projected_x,projected_y),max(1,int(line_thickness*perspective_scale)))
                 classic_last_points[arm]=(projected_x,projected_y)

# --- MODERN MODE Specific Functions ---
def generate_modern_config():
    # ... (Content from previous version, palettes list updated) ...
    palettes = ["neon","pastel","fire","cool","rainbow","cyberpunk","toxic","ice","bubblegum","monochrome",
                "aurora","nebula","lava_flow","deep_space"] # Added new ones
    color_modes = ['palette_based', 'dynamic_hsv_radius', 'dynamic_hsv_time', 'dynamic_hsv_full_spectrum']
    shape_types = ['circle', 'square', 'cross', 'line', 'triangle', 'circle', 'square']
    cfg = {
        'is_classic_mode': False, 'is_gpt1_original_mode': False, # Ensure flags are clear
        'num_arms': random.randint(1,15),'arm_segment_length': random.randint(4,22),
        'spiral_tightness': random.uniform(15,250),'direction': random.choice([-1,1]),
        'rotation_speed': random.uniform(0.03,1.2),'z_amplitude': random.uniform(30,600),
        'z_frequency': random.uniform(25,700),'z_speed': random.uniform(0.05,2.8),
        'global_z_offset_amplitude': random.uniform(0,180),'global_z_offset_speed': random.uniform(0.08,2.5),
        'camera_rotate_speed_x': random.uniform(-0.3,0.3),'camera_rotate_speed_y': random.uniform(-0.3,0.3),
        'camera_rotate_speed_z': random.uniform(-0.2,0.2),'color_mode': random.choice(color_modes),
        'palette_name': random.choice(palettes),'color_shift_speed': random.uniform(0.003,0.2),
        'saturation_base': random.uniform(0.5,1.0),'saturation_pulse_freq': random.uniform(0.03,1.8),
        'value_base': random.uniform(0.6,1.0),'value_z_factor': random.uniform(-0.6,0.3),
        'shape_type': random.choice(shape_types),'base_size': random.uniform(2,22),
        'size_z_scaling': random.uniform(-0.5,0.7),'line_thickness': random.uniform(0.5,6),
        'fov': random.uniform(120,500),'distortion': random.uniform(0,30) if random.random()<0.35 else 0,
        'glow': random.choice([True,False,False,False]),'fade_alpha': random.randint(6,40),
        'time_offset_per_layer': random.uniform(0.05,1.0)
    }
    if cfg['shape_type']=='line': cfg['glow']=False
    if cfg['shape_type']=='triangle': cfg['base_size']=random.uniform(5,25)
    return cfg

def draw_modern_mode_visuals(surface, global_time, configs, all_last_points):
    # ... (Content from previous version, uses project_3d_to_2d_modern_classic and get_modern_classic_palette_color) ...
    # Note: uses _r_palette_val for palette access to r
    global width, height, _r_palette_val
    max_render_radius = math.hypot(width,height)/1.7
    active_cfg_for_camera=configs[0]; cam_angle_x=global_time*active_cfg_for_camera['camera_rotate_speed_x']
    cam_angle_y=global_time*active_cfg_for_camera['camera_rotate_speed_y']; cam_angle_z=global_time*active_cfg_for_camera['camera_rotate_speed_z']
    global_z_offset_val=math.sin(global_time*active_cfg_for_camera['global_z_offset_speed'])*active_cfg_for_camera['global_z_offset_amplitude']
    for cfg_idx,cfg in enumerate(configs):
        cfg_time=global_time+cfg_idx*cfg.get('time_offset_per_layer',0.3)
        layer_last_points=all_last_points.setdefault(cfg_idx,{})
        num_arms=cfg['num_arms']; rotation_speed=cfg['rotation_speed']; spiral_tightness=cfg['spiral_tightness']
        direction=cfg['direction']; z_amplitude=cfg['z_amplitude']; z_frequency=cfg['z_frequency']
        z_speed=cfg['z_speed']; distortion=cfg.get('distortion',0); shape_type=cfg['shape_type']
        glow=cfg.get('glow',False); fov=cfg['fov']; color_mode=cfg['color_mode']
        palette_name=cfg.get('palette_name','neon'); color_shift_speed=cfg['color_shift_speed']
        saturation_base=cfg['saturation_base']; saturation_pulse_freq=cfg['saturation_pulse_freq']
        value_base=cfg['value_base']; value_z_factor=cfg['value_z_factor']; base_size=cfg['base_size']
        size_z_scaling=cfg['size_z_scaling']; line_thickness=cfg.get('line_thickness',2)
        arm_segment_length=cfg['arm_segment_length']
        for r_iter in range(0,int(max_render_radius),arm_segment_length):
            r=float(r_iter); _r_palette_val = r # Set for palette
            if r==0 and shape_type=='line': continue
            base_angle=(r/spiral_tightness)+(cfg_time*rotation_speed*direction)
            current_z=math.sin(r/z_frequency+cfg_time*z_speed)*z_amplitude+global_z_offset_val
            for arm_idx in range(num_arms):
                arm_angle=base_angle+arm_idx*(2*math.pi/num_arms); x_3d=r*math.cos(arm_angle); y_3d=r*math.sin(arm_angle)
                if distortion>0:
                    dist_val=distortion/(1.0+r*0.005)
                    x_3d_dist=x_3d+math.sin(y_3d/(50.0+dist_val*2)+cfg_time*1.5)*dist_val
                    y_3d_dist=y_3d+math.sin(x_3d/(50.0+dist_val*2)+cfg_time*1.5)*dist_val
                    x_3d,y_3d=x_3d_dist,y_3d_dist
                rot_x,rot_y,rot_z=rotate_3d(x_3d,y_3d,current_z,cam_angle_x,cam_angle_y,cam_angle_z)
                projection_result,perspective_scale=project_3d_to_2d_modern_classic(rot_x,rot_y,rot_z,fov,width,height)
                if projection_result is None: layer_last_points[arm_idx]=None; continue
                px,py=projection_result; color_calc_time=cfg_time
                if color_mode=='palette_based': palette_t=(r/max_render_radius+color_calc_time*color_shift_speed)%1.0; color=get_modern_classic_palette_color(palette_name,palette_t)
                else:
                    if color_mode=='dynamic_hsv_radius': hue=(r/max_render_radius+color_calc_time*color_shift_speed)%1.0
                    elif color_mode=='dynamic_hsv_time': hue=(color_calc_time*color_shift_speed)%1.0
                    elif color_mode=='dynamic_hsv_full_spectrum': hue=(arm_idx/num_arms+r/(max_render_radius*1.5)+color_calc_time*color_shift_speed)%1.0
                    else: hue=(r/max_render_radius+color_calc_time*color_shift_speed)%1.0
                    saturation=saturation_base+math.sin(color_calc_time*saturation_pulse_freq+r*0.005)*(1-saturation_base)*0.7; saturation=max(0.05,min(1.0,saturation))
                    norm_rot_z=rot_z/(z_amplitude+abs(global_z_offset_val)+100); value_z_effect=norm_rot_z*value_z_factor
                    value=value_base-value_z_effect; value=max(0.05,min(1.0,value)); color=hsv_to_rgb(hue,saturation,value)
                z_scale_mod=1.0-(rot_z*size_z_scaling/(z_amplitude+1.0)) if z_amplitude else 1.0
                current_size=base_size*perspective_scale*max(0.05,z_scale_mod); current_size=max(1,int(current_size))
                if 0<=px<width and 0<=py<height:
                    if glow and current_size>2:
                        try:
                            glow_radius=current_size*1.5; glow_surface=pygame.Surface((glow_radius*2,glow_radius*2),pygame.SRCALPHA)
                            pygame.draw.circle(glow_surface,(*color,random.randint(25,55)),(glow_radius,glow_radius),glow_radius)
                            surface.blit(glow_surface,(px-glow_radius,py-glow_radius),special_flags=pygame.BLEND_RGBA_ADD)
                        except pygame.error: pass
                    if shape_type=='circle': pygame.draw.circle(surface,color,(px,py),max(1,current_size//2))
                    elif shape_type=='square': pygame.draw.rect(surface,color,(px-current_size//2,py-current_size//2,current_size,current_size))
                    elif shape_type=='cross':
                        l_thick=max(1,int(line_thickness*perspective_scale*0.5+current_size*0.1)); h_size=current_size//2
                        pygame.draw.line(surface,color,(px-h_size,py),(px+h_size,py),l_thick); pygame.draw.line(surface,color,(px,py-h_size),(px,py+h_size),l_thick)
                    elif shape_type=='triangle':
                        s=current_size; angle_offset=random.uniform(0,math.pi*2) if r_iter<arm_segment_length*2 else math.atan2(py-(height/2),px-(width/2))
                        points=[(px+s*math.cos(angle_offset),py+s*math.sin(angle_offset)),(px+s*math.cos(angle_offset+2*math.pi/3),py+s*math.sin(angle_offset+2*math.pi/3)),(px+s*math.cos(angle_offset+4*math.pi/3),py+s*math.sin(angle_offset+4*math.pi/3))]
                        pygame.draw.polygon(surface,color,points)
                    elif shape_type=='line':
                        last_point=layer_last_points.get(arm_idx)
                        if last_point: pygame.draw.line(surface,color,last_point,(px,py),max(1,int(line_thickness*perspective_scale)))
                        layer_last_points[arm_idx]=(px,py)

# --- Config Dispatcher ---
def reset_configs(num_layers_override=None, force_mode=None):
    rand_choice = random.random()
    if force_mode == "modern" or (force_mode is None and rand_choice < 0.6): # ~60% Modern
        print("SWITCHING TO MODERN MODE")
        num_layers = num_layers_override if num_layers_override is not None else random.randint(1, 4)
        return [generate_modern_config() for _ in range(num_layers)]
    elif force_mode == "classic" or (force_mode is None and rand_choice < 0.8): # ~20% Classic (0.6 to 0.8)
        print("SWITCHING TO CLASSIC NEWSPIRALS1 MODE")
        return [generate_classic_mode_params()]
    else: # ~20% GPT1 Original
        print("SWITCHING TO GPT1 ORIGINAL MODE")
        return [generate_gpt1_original_mode_params(num_layers_override)]


# --- Main Visualizer Dispatcher ---
def master_visualizer(surface, global_time, active_configs, all_last_points):
    if not active_configs: return # Should not happen if reset_configs is robust

    # Dispatch to the correct drawing function based on flags in the first config
    first_config = active_configs[0]

    if first_config.get('is_classic_mode'):
        classic_points_for_layer = all_last_points.setdefault(0, {}) # Classic mode is effectively layer 0
        draw_classic_mode_visuals(surface, global_time, first_config, classic_points_for_layer)
    elif first_config.get('is_gpt1_original_mode'):
        # gpt1_original mode manages its own layers internally and doesn't use all_last_points
        draw_gpt1_original_mode_visuals(surface, global_time, first_config)
    else: # Default to Modern Mode
        draw_modern_mode_visuals(surface, global_time, active_configs, all_last_points)

# --- Main Loop ---
def main():
    global width, height, screen, _r_palette_val

    # =========================================================================
    # === RENDER CONFIGURATION (CHANGE THESE IF YOU WANT) ===
    # =========================================================================
    RENDER_MODE = False        # Set to False to run normally (interactive mode)
    FPS = 30                  # The target FPS of the output video
    DURATION_SECONDS = 30     # How long the video should be (in seconds)
    OUTPUT_FOLDER = "video_output"
    OUTPUT_FILE = "Final_Hyperspiral.mp4"
    # =========================================================================

    # --- Setup Rendering Environment ---
    frame_count = 0
    total_frames = FPS * DURATION_SECONDS
    
    if RENDER_MODE:
        # Create/Clean the output directory
        if os.path.exists(OUTPUT_FOLDER):
            try:
                shutil.rmtree(OUTPUT_FOLDER)
            except Exception as e:
                print(f"Warning: Could not clear folder {OUTPUT_FOLDER}. {e}")
        
        if not os.path.exists(OUTPUT_FOLDER):
            os.makedirs(OUTPUT_FOLDER)
            
        print(f"\n--- STARTING RENDER MODE ---")
        print(f"Target Video Length: {DURATION_SECONDS}s")
        print(f"Total Frames to Render: {total_frames}")
        print(f"Output Folder: {os.path.abspath(OUTPUT_FOLDER)}")
        print("Please wait... The window may appear slow. This is normal.")
        print("----------------------------\n")

    clock = pygame.time.Clock()
    trail_surface = pygame.Surface((width, height), pygame.SRCALPHA)

    spiral_configs = reset_configs()
    current_fade_alpha = spiral_configs[0]['fade_alpha']
    trail_surface.fill((0, 0, 0, current_fade_alpha))
    
    start_time_sim = pygame.time.get_ticks()
    last_parameter_reset_time = 0 # Modified for consistency in render mode
    parameter_reset_interval_ms = random.randint(8000, 15000)

    all_last_points_for_lines = {} 

    running = True
    while running:
        # 1. Event Handling
        for event in pygame.event.get():
            if event.type == pygame.QUIT: running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE: running = False
                # Disable interactive controls during rendering to avoid glitches
                if not RENDER_MODE:
                    if event.key == pygame.K_SPACE or event.key == pygame.K_r:
                        print("User forced parameter refresh.")
                        spiral_configs = reset_configs()
                        all_last_points_for_lines.clear()
                        last_parameter_reset_time = pygame.time.get_ticks()
                        parameter_reset_interval_ms = random.randint(8000, 15000)

        # 2. Time Calculation (The Key to Smooth Rendering)
        if RENDER_MODE:
            # Fake the time based on the frame count
            elapsed_sim_time_sec = frame_count / FPS
            current_time_ms = elapsed_sim_time_sec * 1000
        else:
            # Use real system time
            current_time_ms = pygame.time.get_ticks()
            elapsed_sim_time_sec = (current_time_ms - start_time_sim) / 1000.0

        # 3. Logic Updates
        if current_time_ms - last_parameter_reset_time >= parameter_reset_interval_ms:
            print(f"Automatic parameter refresh at {elapsed_sim_time_sec:.1f}s.")
            spiral_configs = reset_configs()
            all_last_points_for_lines.clear() 
            last_parameter_reset_time = current_time_ms
            parameter_reset_interval_ms = random.randint(8000, 15000)

        current_fade_alpha = spiral_configs[0]['fade_alpha']

        # 4. Drawing
        trail_surface.fill((0, 0, 0, current_fade_alpha))
        master_visualizer(trail_surface, elapsed_sim_time_sec, spiral_configs, all_last_points_for_lines)
        screen.blit(trail_surface, (0, 0))
        pygame.display.flip()
        
        # 5. Render / Clock Tick
        if RENDER_MODE:
            # Save the frame
            filename = os.path.join(OUTPUT_FOLDER, f"frame_{frame_count:05d}.png")
            pygame.image.save(screen, filename)
            
            frame_count += 1
            
            if frame_count % 30 == 0:
                print(f"Rendering: {int((frame_count/total_frames)*100)}% ({frame_count}/{total_frames})")
            
            if frame_count >= total_frames:
                print("--- RENDER FINISHED. STARTING VIDEO COMPILATION ---")
                running = False # Exit the loop
        else:
            clock.tick(60)
    
    pygame.quit()
    
    # 6. Automated Video Compilation
    if RENDER_MODE:
        try:
            print("Compiling video with FFmpeg... (Do not close)")
            
            # Construct the FFmpeg command
            # -framerate: Input FPS
            # -i: Input file pattern
            # -c:v libx264: Video codec
            # -pix_fmt yuv420p: Pixel format for compatibility
            # -crf 17: High quality (lower is better quality)
            
            cmd = [
                'ffmpeg', '-y',
                '-framerate', str(FPS),
                '-i', os.path.join(OUTPUT_FOLDER, 'frame_%05d.png'),
                '-c:v', 'libx264',
                '-pix_fmt', 'yuv420p',
                '-crf', '17',
                '-preset', 'fast',
                OUTPUT_FILE
            ]
            
            # Run the command and hide the popup window on Windows
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                
            subprocess.run(cmd, check=True, startupinfo=startupinfo)
            
            print(f"SUCCESS! Video saved as: {os.path.abspath(OUTPUT_FILE)}")
            
            # Clean up images
            print("Cleaning up temporary images...")
            shutil.rmtree(OUTPUT_FOLDER)
            print("Done.")
            
            # Open the video
            if os.name == 'nt':
                os.startfile(OUTPUT_FILE)
                
        except FileNotFoundError:
            print("\nERROR: FFmpeg not found!")
            print("The images were saved in 'video_output', but the video could not be made.")
            print("Please install FFmpeg and add it to your PATH.")
        except Exception as e:
            print(f"\nERROR during video compilation: {e}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"An error occurred: {e}")
        input("Press Enter to close...")