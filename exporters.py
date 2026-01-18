import pygame
import imageio
import math
import numpy as np
from renderer import Renderer
from constants import *

def capture_animation_frames(root_bone, animation, camera_pan, fps=30):
    frames = []
    duration = animation.duration
    steps = int(duration * fps)
    
    print(f"Capturing {steps} frames...")
    
    temp_screen = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    renderer = Renderer(temp_screen)
    
    for i in range(steps):
        t = (i / fps)
        animation.apply(t, root_bone)
        
        # Render without UI selection highlights and without bones
        renderer.render_scene(root_bone, camera_pan, 1.0, None, "NONE", time_info=None, draw_bones=False)
        
        # Capture - We crop out the timeline at the bottom
        view = pygame.surfarray.array3d(temp_screen)
        # Rotate because surfarray is transposed (width, height, 3) -> (height, width, 3)
        view = view.transpose([1, 0, 2])
        
        # Crop height
        view = view[:SCREEN_HEIGHT-TIMELINE_HEIGHT, :, :]
        
        frames.append(view)
        
    return frames

def export_gif_with_camera(filepath, root_bone, animation, camera_pan):
    frames = capture_animation_frames(root_bone, animation, camera_pan)
    print("Saving GIF...")
    try:
        imageio.mimsave(filepath, frames, fps=30, loop=0)
        print("Done!")
    except Exception as e:
        print(f"Error saving GIF: {e}")

def export_video(filepath, root_bone, animation, camera_pan):
    frames = capture_animation_frames(root_bone, animation, camera_pan)
    print("Saving Video (MP4)...")
    try:
        # Quality 5-9 roughly, 10 is huge.
        imageio.mimsave(filepath, frames, fps=30, quality=7) 
        print("Done!")
    except Exception as e:
        print(f"Error saving Video: {e}")
        print("Ensure you have ffmpeg installed or the imageio-ffmpeg plugin.")

def export_sprite_sheet(filepath, root_bone, animation, camera_pan):
    frames = capture_animation_frames(root_bone, animation, camera_pan)
    if not frames:
        return

    print("Generating Sprite Sheet...")
    
    # Frame dimensions
    frame_h, frame_w, _ = frames[0].shape
    count = len(frames)
    
    # Calculate grid size (approx square)
    cols = math.ceil(math.sqrt(count))
    rows = math.ceil(count / cols)
    
    sheet_w = cols * frame_w
    sheet_h = rows * frame_h
    
    sheet_surf = pygame.Surface((sheet_w, sheet_h))
    
    for i, frame_arr in enumerate(frames):
        # Convert numpy array back to surface
        # surfarray.make_surface expects (width, height, 3)
        # our frame_arr is (height, width, 3), so we transpose back
        transposed = frame_arr.transpose([1, 0, 2])
        f_surf = pygame.surfarray.make_surface(transposed)
        
        r = i // cols
        c = i % cols
        
        sheet_surf.blit(f_surf, (c * frame_w, r * frame_h))
        
    try:
        pygame.image.save(sheet_surf, filepath)
        print(f"Saved Sprite Sheet to {filepath}")
    except Exception as e:
        print(f"Error saving Sprite Sheet: {e}")
