import pygame
import math
import sys
import json
import os
import toml
import imageio
import numpy as np
from tkinter import filedialog, Tk

# Initialize Tkinter for file dialogs (hide the main window)
root_tk = Tk()
root_tk.withdraw()

# Constants
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
BG_COLOR = (30, 30, 30)
GRID_COLOR = (50, 50, 50)
TEXT_COLOR = (200, 200, 200)
SELECTED_COLOR = (255, 255, 0)
PIVOT_COLOR = (0, 255, 0)
BONE_LINE_COLOR = (255, 100, 100)
TIMELINE_HEIGHT = 100
TIMELINE_BG = (20, 20, 20)

class Bone:
    def __init__(self, name, image_path=None, parent=None):
        self.name = name
        self.image_path = image_path
        self.original_image = None
        self.image = None
        
        if image_path and os.path.exists(image_path):
            try:
                self.original_image = pygame.image.load(image_path).convert_alpha()
                self.image = self.original_image
            except Exception as e:
                print(f"Error loading image: {e}")
        
        # Hierarchy
        self.parent = parent
        self.children = []
        if parent:
            parent.children.append(self)

        # Transform (Local Space)
        self.x = 0.0
        self.y = 0.0
        self.rotation = 0.0 # Degrees
        self.scale_x = 1.0
        self.scale_y = 1.0
        
        # Pivot (Relative to Image Top-Left)
        self.pivot_x = 0.0
        self.pivot_y = 0.0
        
        if self.image:
            self.pivot_x = self.image.get_width() / 2.0
            self.pivot_y = self.image.get_height() / 2.0

    def get_world_transform(self):
        """
        Calculates the world position and rotation.
        Returns (x, y, rotation_degrees, scale_x, scale_y)
        """
        if self.parent:
            px, py, prot, psx, psy = self.parent.get_world_transform()
            
            # 1. Apply Parent Scaling to local position
            lx = self.x * psx
            ly = self.y * psy
            
            # 2. Rotate local position by parent rotation
            rad = math.radians(prot)
            cos_a = math.cos(rad)
            sin_a = math.sin(rad)
            
            wx = px + (lx * cos_a - ly * sin_a)
            wy = py + (lx * sin_a + ly * cos_a)
            
            return wx, wy, prot + self.rotation, psx * self.scale_x, psy * self.scale_y
        else:
            return self.x, self.y, self.rotation, self.scale_x, self.scale_y

    def draw(self, surface, draw_bones=True, selected_bone=None):
        wx, wy, wrot, wsx, wsy = self.get_world_transform()
        
        selected = (self == selected_bone)

        # Draw Image
        if self.image:
            # Rotate and Scale image
            # Note: Pygame rotation is destructive if not careful, so we rotate the original
            # For simplicity in this tool, we use rotozoom or transform.rotate
            
            # Scale first
            if abs(wsx - 1.0) > 0.01 or abs(wsy - 1.0) > 0.01:
                w = int(self.original_image.get_width() * abs(wsx))
                h = int(self.original_image.get_height() * abs(wsy))
                scaled_img = pygame.transform.scale(self.original_image, (max(1, w), max(1, h)))
            else:
                scaled_img = self.original_image
                
            rotated_img = pygame.transform.rotate(scaled_img, -wrot) # Pygame rotates CCW
            
            # Calculate offset due to pivot rotation
            # We need to transform the pivot point to world space to know where to center the image
            
            # Vector from (0,0) of image to Pivot
            piv_x = self.pivot_x * wsx
            piv_y = self.pivot_y * wsy
            
            # Rotate this vector
            rad = math.radians(wrot)
            cos_a = math.cos(rad)
            sin_a = math.sin(rad)
            
            rot_piv_x = piv_x * cos_a - piv_y * sin_a
            rot_piv_y = piv_x * sin_a + piv_y * cos_a
            
            # The Draw position is WorldPos - RotatedPivot + (RectCorrection)
            rect = rotated_img.get_rect()
            rect.center = (wx + (rect.width/2 - rot_piv_x) - rect.width/2, 
                           wy + (rect.height/2 - rot_piv_y) - rect.height/2)
            
            surface.blit(rotated_img, rect.topleft)
            
            if selected and draw_bones:
                pygame.draw.rect(surface, SELECTED_COLOR, rect, 1)

        # Draw Bone Structure (Visual debug lines)
        if draw_bones:
            # Draw line to parent
            if self.parent:
                px, py, _, _, _ = self.parent.get_world_transform()
                pygame.draw.line(surface, BONE_LINE_COLOR, (px, py), (wx, wy), 2)
            
            # Draw Node Point
            color = SELECTED_COLOR if selected else (100, 100, 255)
            pygame.draw.circle(surface, color, (int(wx), int(wy)), 5)
            
            # Draw Pivot
            if selected:
                # Visual representation of pivot isn't separate from world pos in this model
                # because world pos IS the pivot location.
                # But for image-relative pivot editing:
                pass

        for child in self.children:
            child.draw(surface, draw_bones, selected_bone=selected_bone)

def get_bone_at_pos(bone, mx, my):
    # Simple distance check to bone origin (pivot)
    wx, wy, _, _, _ = bone.get_world_transform()
    dist = math.hypot(wx - mx, wy - my)
    if dist < 10:
        return bone
    
    # Recursive check
    for child in bone.children:
        found = get_bone_at_pos(child, mx, my)
        if found:
            return found
    return None

# -----------------------------------------------------------------------------
# Animation System
# -----------------------------------------------------------------------------

class Keyframe:
    def __init__(self, time, data):
        self.time = time
        self.data = data # Dict of bone_name -> {x, y, rot, sx, sy}

class Animation:
    def __init__(self):
        self.keyframes = [] # Sorted by time
        self.duration = 2.0 # Seconds
        self.loop = True

    def add_keyframe(self, time, root_bone):
        data = {}
        
        def capture(bone):
            data[bone.name] = {
                'x': bone.x, 'y': bone.y, 'rot': bone.rotation,
                'sx': bone.scale_x, 'sy': bone.scale_y
            }
            for child in bone.children:
                capture(child)
        
        capture(root_bone)
        
        # Remove existing keyframe at same time (approx)
        self.keyframes = [k for k in self.keyframes if abs(k.time - time) > 0.01]
        self.keyframes.append(Keyframe(time, data))
        self.keyframes.sort(key=lambda k: k.time)

    def apply(self, time, root_bone):
        if not self.keyframes:
            return

        # Find surrounding keyframes
        prev_k = self.keyframes[0]
        next_k = self.keyframes[-1]
        
        for k in self.keyframes:
            if k.time <= time:
                prev_k = k
            if k.time >= time:
                next_k = k
                break
        
        # Interpolate
        t = 0.0
        if next_k.time != prev_k.time:
            t = (time - prev_k.time) / (next_k.time - prev_k.time)
        
        def apply_bone(bone):
            if bone.name in prev_k.data and bone.name in next_k.data:
                p = prev_k.data[bone.name]
                n = next_k.data[bone.name]
                
                bone.x = p['x'] + (n['x'] - p['x']) * t
                bone.y = p['y'] + (n['y'] - p['y']) * t
                
                # Shortest angle interpolation
                diff = n['rot'] - p['rot']
                while diff < -180: diff += 360
                while diff > 180: diff -= 360
                bone.rotation = p['rot'] + diff * t
                
                bone.scale_x = p['sx'] + (n['sx'] - p['sx']) * t
                bone.scale_y = p['sy'] + (n['sy'] - p['sy']) * t
            
            for child in bone.children:
                apply_bone(child)
                
        apply_bone(root_bone)

def load_scene_from_toml(filepath):
    try:
        data = toml.load(filepath)
    except Exception as e:
        print(f"Error loading TOML: {e}")
        return None, None

    # 1. Build Bones
    # We need a map to resolve parents
    bone_map = {}
    bones_data = data.get('bones', [])
    
    # First pass: Create all bone objects
    for b_data in bones_data:
        name = b_data.get('name', 'Unknown')
        img_path = b_data.get('image')
        bone = Bone(name, img_path)
        
        bone.x = b_data.get('x', 0.0)
        bone.y = b_data.get('y', 0.0)
        bone.rotation = b_data.get('rotation', 0.0)
        bone.scale_x = b_data.get('scale_x', 1.0)
        bone.scale_y = b_data.get('scale_y', 1.0)
        
        if 'pivot_x' in b_data: bone.pivot_x = b_data['pivot_x']
        if 'pivot_y' in b_data: bone.pivot_y = b_data['pivot_y']
        
        bone_map[name] = bone

    # Second pass: Link parents
    root_bone = None
    for b_data in bones_data:
        name = b_data.get('name')
        parent_name = b_data.get('parent')
        bone = bone_map[name]
        
        if parent_name:
            if parent_name in bone_map:
                parent = bone_map[parent_name]
                bone.parent = parent
                parent.children.append(bone)
            else:
                print(f"Warning: Parent '{parent_name}' not found for '{name}'")
        else:
            # If multiple roots exist, the last one wins, or we handle it. 
            # For this simple tool, assume one root or pick the first one found.
            if root_bone is None:
                root_bone = bone
    
    if not root_bone and bone_map:
        # Fallback if no explicit root (no parent) is defined, just pick one
        root_bone = list(bone_map.values())[0]

    # 2. Load Animations
    animation = Animation()
    meta = data.get('meta', {})
    animation.duration = meta.get('duration', 2.0)
    
    anim_data = data.get('animations', {})
    keyframes_data = anim_data.get('keyframes', [])
    
    for k_data in keyframes_data:
        time = k_data.get('time', 0.0)
        bone_states = k_data.get('bones', {})
        
        # Construct keyframe data dict
        kf_data = {}
        for bone_name, state in bone_states.items():
            # Fill missing with defaults or current if possible. 
            # The Apply logic expects keys to exist.
            # We should grab default values from the bind pose (the bone object itself)
            # if they aren't in the keyframe, BUT apply logic handles partials strictly?
            # Actually my apply logic: "if bone.name in prev_k.data and bone.name in next_k.data"
            # So we must ensure data is comprehensive or update the system.
            # For now, let's trust the TOML or use defaults.
            
            # Better: Get the bind pose from the bone_map
            if bone_name in bone_map:
                b = bone_map[bone_name]
                kf_data[bone_name] = {
                    'x': state.get('x', b.x),
                    'y': state.get('y', b.y),
                    'rot': state.get('rotation', b.rotation),
                    'sx': state.get('scale_x', b.scale_x),
                    'sy': state.get('scale_y', b.scale_y)
                }
        
        # Add Keyframe manually to avoid capturing current state
        animation.keyframes.append(Keyframe(time, kf_data))
    
    animation.keyframes.sort(key=lambda k: k.time)
    
    return root_bone, animation

def save_scene_to_toml(filepath, root_bone, animation):
    data = {
        "meta": {
            "duration": animation.duration,
            "loop": animation.loop
        },
        "bones": [],
        "animations": {
            "keyframes": []
        }
    }

    # 1. Flatten Bones
    def collect_bones(bone):
        b_data = {
            "name": bone.name,
            "x": float(bone.x),
            "y": float(bone.y),
            "rotation": float(bone.rotation),
            "scale_x": float(bone.scale_x),
            "scale_y": float(bone.scale_y),
            "pivot_x": float(bone.pivot_x),
            "pivot_y": float(bone.pivot_y)
        }
        if bone.parent:
            b_data["parent"] = bone.parent.name
        if bone.image_path:
            # Try to keep path relative if possible
            try:
                rel = os.path.relpath(bone.image_path, start=os.getcwd())
                if not rel.startswith(".."):
                    b_data["image"] = rel
                else:
                    b_data["image"] = bone.image_path
            except ValueError:
                b_data["image"] = bone.image_path
        
        data["bones"].append(b_data)
        for child in bone.children:
            collect_bones(child)
            
    collect_bones(root_bone)
    
    # 2. Keyframes
    for k in animation.keyframes:
        k_data = {
            "time": float(k.time),
            "bones": {}
        }
        for b_name, state in k.data.items():
            # Ensure floats for clean TOML
            k_data["bones"][b_name] = {k: float(v) for k, v in state.items()}
            
        data["animations"]["keyframes"].append(k_data)
        
    try:
        with open(filepath, "w") as f:
            toml.dump(data, f)
        print(f"Saved scene to {filepath}")
    except Exception as e:
        print(f"Error saving TOML: {e}")

def render_scene(surface, root_bone, camera_pan, selected_bone, mode, time_info=None, draw_bones=True):
    """
    Draws the entire scene to the provided surface.
    time_info: tuple (current_time, duration) for drawing timeline
    """
    surface.fill(BG_COLOR)
    
    # Grid
    grid_sz = 50
    off_x = camera_pan[0] % grid_sz
    off_y = camera_pan[1] % grid_sz
    w, h = surface.get_size()
    
    for i in range(0, w, grid_sz):
        pygame.draw.line(surface, GRID_COLOR, (i + off_x - grid_sz, 0), (i + off_x - grid_sz, h - TIMELINE_HEIGHT))
    for i in range(0, h - TIMELINE_HEIGHT, grid_sz):
        pygame.draw.line(surface, GRID_COLOR, (0, i + off_y - grid_sz), (w, i + off_y - grid_sz))

    # Draw Skeleton
    # HACK: Temporarily modify root pos for drawing
    orig_root_x, orig_root_y = root_bone.x, root_bone.y
    root_bone.x += camera_pan[0]
    root_bone.y += camera_pan[1]
    
    def recursive_draw(bone):
        bone.draw(surface, draw_bones, selected_bone=selected_bone)
        # Highlight pivot if selected
        if bone == selected_bone and mode == "PIVOT" and draw_bones:
            wx, wy, _, _, _ = bone.get_world_transform()
            pygame.draw.line(surface, PIVOT_COLOR, (wx-10, wy), (wx+10, wy), 2)
            pygame.draw.line(surface, PIVOT_COLOR, (wx, wy-10), (wx, wy+10), 2)
            
    recursive_draw(root_bone)
    
    # Restore root
    root_bone.x = orig_root_x
    root_bone.y = orig_root_y
    
    # UI Overlay (Timeline)
    if time_info:
        curr, dur = time_info
        pygame.draw.rect(surface, TIMELINE_BG, (0, h - TIMELINE_HEIGHT, w, TIMELINE_HEIGHT))
        
        # Playhead
        if dur > 0:
            ph_x = (curr / dur) * w
            pygame.draw.line(surface, (255, 0, 0), (ph_x, h - TIMELINE_HEIGHT), (ph_x, h), 2)

def export_gif(filepath, root_bone, animation):
    print(f"Starting GIF export to {filepath}...")
    frames = []
    fps = 30
    duration = animation.duration
    total_frames = int(duration * fps)
    
    # Create a temporary surface for rendering
    # We exclude the timeline for the export, usually desirable? 
    # Or we can keep it. Let's keep the whole screen for now for simplicity, 
    # or maybe crop the timeline? Let's crop the timeline out.
    
    render_w = SCREEN_WIDTH
    render_h = SCREEN_HEIGHT - TIMELINE_HEIGHT
    surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT)) # Render full then subsurf
    
    # Center camera for export? Or use current camera?
    # Using current camera is best so user can frame the shot.
    # We need to pass the camera_pan from main, but we don't have it here.
    # We'll assume a default or passed in. 
    # Actually, let's just update the function signature to accept camera_pan.
    pass 

def export_gif_with_camera(filepath, root_bone, animation, camera_pan):
    frames = []
    fps = 30
    duration = animation.duration
    steps = int(duration * fps)
    
    print(f"Exporting {steps} frames to {filepath}...")
    
    temp_screen = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    
    for i in range(steps):
        t = (i / fps)
        animation.apply(t, root_bone)
        
        # Render without UI selection highlights and without bones
        render_scene(temp_screen, root_bone, camera_pan, None, "NONE", time_info=None, draw_bones=False)
        
        # Capture - We crop out the timeline at the bottom
        view = pygame.surfarray.array3d(temp_screen)
        # Rotate because surfarray is transposed (width, height, 3) -> (height, width, 3)
        view = view.transpose([1, 0, 2])
        
        # Crop height
        view = view[:SCREEN_HEIGHT-TIMELINE_HEIGHT, :, :]
        
        frames.append(view)
        
        if i % 10 == 0:
            print(f"Rendered frame {i}/{steps}")

    print("Saving GIF...")
    try:
        imageio.mimsave(filepath, frames, fps=fps, loop=0)
        print("Done!")
    except Exception as e:
        print(f"Error saving GIF: {e}")

# -----------------------------------------------------------------------------
# Main Editor
# -----------------------------------------------------------------------------

def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Skeleton Animator")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont('Arial', 14)

    # State
    camera_pan = [SCREEN_WIDTH//2, SCREEN_HEIGHT//2]
    
    root_bone = Bone("Root")
    root_bone.x = 0
    root_bone.y = 0
    
    selected_bone = root_bone
    
    # Modes: SELECT, MOVE, ROTATE, PIVOT
    mode = "SELECT" 
    show_bones = True
    
    animation = Animation()
    current_time = 0.0
    is_playing = False
    
    running = True
    dragging = False
    last_mouse_pos = (0, 0)
    
    # Unique ID counter
    bone_counter = 1

    while running:
        dt = clock.tick(60) / 1000.0 # Delta time in seconds
        mx, my = pygame.mouse.get_pos()
        
        # --- Event Handling ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                
                # Modes
                elif event.key == pygame.K_q: mode = "SELECT"
                elif event.key == pygame.K_w: mode = "MOVE"
                elif event.key == pygame.K_e: mode = "ROTATE"
                elif event.key == pygame.K_r: mode = "PIVOT"
                
                # View Options
                elif event.key == pygame.K_b: show_bones = not show_bones

                # Actions
                elif event.key == pygame.K_l: # Load Image as Child
                    filepath = filedialog.askopenfilename(filetypes=[("Images", "*.png;*.jpg;*.jpeg;*.bmp")])
                    if filepath:
                        new_bone = Bone(f"Bone_{bone_counter}", filepath, parent=selected_bone)
                        bone_counter += 1
                        selected_bone = new_bone
                        # Default position to slightly offset so it's visible
                        selected_bone.x = 50
                
                elif event.key == pygame.K_n: # New Empty Bone
                    new_bone = Bone(f"Bone_{bone_counter}", parent=selected_bone)
                    bone_counter += 1
                    selected_bone = new_bone
                    selected_bone.x = 50
                
                elif event.key == pygame.K_DELETE or event.key == pygame.K_BACKSPACE:
                    if selected_bone and selected_bone.parent: # Cannot delete root
                        p = selected_bone.parent
                        p.children.remove(selected_bone)
                        selected_bone = p
                
                elif event.key == pygame.K_SPACE:
                    is_playing = not is_playing
                
                elif event.key == pygame.K_k:
                    animation.add_keyframe(current_time, root_bone)
                    print(f"Keyframe added at {current_time:.2f}s")
                
                # Save/Load
                elif event.key == pygame.K_o: # Load TOML
                    filepath = filedialog.askopenfilename(filetypes=[("TOML Config", "*.toml")])
                    if filepath:
                        new_root, new_anim = load_scene_from_toml(filepath)
                        if new_root:
                            root_bone = new_root
                            animation = new_anim
                            selected_bone = root_bone
                            print(f"Loaded scene from {filepath}")

                elif event.key == pygame.K_s and (pygame.key.get_mods() & pygame.KMOD_CTRL):
                    filepath = filedialog.asksaveasfilename(defaultextension=".toml", filetypes=[("TOML Config", "*.toml")])
                    if filepath:
                        save_scene_to_toml(filepath, root_bone, animation)

                # Export GIF
                elif event.key == pygame.K_x:
                    filepath = filedialog.asksaveasfilename(defaultextension=".gif", filetypes=[("GIF Image", "*.gif")])
                    if filepath:
                        export_gif_with_camera(filepath, root_bone, animation, camera_pan)

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1: # Left Click
                    # Check if clicking timeline
                    if my > SCREEN_HEIGHT - TIMELINE_HEIGHT:
                        ratio = mx / SCREEN_WIDTH
                        current_time = ratio * animation.duration
                        if not is_playing:
                            animation.apply(current_time, root_bone)
                        dragging = "TIMELINE"
                    else:
                        # Check if clicking a bone node
                        world_mx = mx - camera_pan[0]
                        world_my = my - camera_pan[1]
                        clicked = get_bone_at_pos(root_bone, world_mx, world_my)
                        if clicked:
                            selected_bone = clicked
                            dragging = "BONE"
                        else:
                            dragging = "CAMERA"
                elif event.button == 3: # Right Click
                    pass
                elif event.button == 4: # Scroll Up
                    if selected_bone and mode == "ROTATE":
                        selected_bone.rotation += 5
                elif event.button == 5: # Scroll Down
                    if selected_bone and mode == "ROTATE":
                        selected_bone.rotation -= 5

            elif event.type == pygame.MOUSEBUTTONUP:
                dragging = False

            elif event.type == pygame.MOUSEMOTION:
                dx = mx - last_mouse_pos[0]
                dy = my - last_mouse_pos[1]
                
                if dragging == "TIMELINE":
                    ratio = max(0, min(1, mx / SCREEN_WIDTH))
                    current_time = ratio * animation.duration
                    if not is_playing:
                        animation.apply(current_time, root_bone)
                
                elif dragging == "CAMERA":
                    camera_pan[0] += dx
                    camera_pan[1] += dy
                
                elif dragging == "BONE" and selected_bone:
                    if mode == "MOVE":
                        # Simple screen space to local space translation is complex with hierarchy rotation.
                        # For this prototype, we just add delta to x/y directly, which works if parent rot is 0.
                        # To do it correctly, we need to rotate the delta vector by -parent_world_rotation.
                        
                        parent_rot = 0
                        if selected_bone.parent:
                            _, _, parent_rot, _, _ = selected_bone.parent.get_world_transform()
                        
                        rad = math.radians(-parent_rot)
                        local_dx = dx * math.cos(rad) - dy * math.sin(rad)
                        local_dy = dx * math.sin(rad) + dy * math.cos(rad)
                        
                        selected_bone.x += local_dx
                        selected_bone.y += local_dy
                        
                    elif mode == "ROTATE":
                        selected_bone.rotation += dx  # Drag X to rotate
                    
                    elif mode == "PIVOT":
                        # Move pivot, but compensate position so image stays still
                        # This is tricky math, for prototype just moving the raw values
                        selected_bone.pivot_x += dx
                        selected_bone.pivot_y += dy

        last_mouse_pos = (mx, my)

        # --- Update ---
        if is_playing:
            current_time += dt
            if current_time > animation.duration:
                current_time = 0
            animation.apply(current_time, root_bone)

        # --- Drawing ---
        render_scene(screen, root_bone, camera_pan, selected_bone, mode, (current_time, animation.duration), show_bones)
        
        # UI Overlay (Text only, timeline is handled in render_scene)
        # Re-draw timeline markers (keyframes) on top because render_scene handles base timeline
        for k in animation.keyframes:
            kx = (k.time / animation.duration) * SCREEN_WIDTH
            pygame.draw.circle(screen, (255, 255, 0), (int(kx), SCREEN_HEIGHT - TIMELINE_HEIGHT + 10), 5)

        # Info Text
        infos = [
            f"Mode: {mode} (Q,W,E,R) | Bones: {'ON' if show_bones else 'OFF'} (B)",
            f"Selected: {selected_bone.name}",
            f"Time: {current_time:.2f} / {animation.duration:.2f}",
            "Controls: L=Load Img, N=New Node, Del=Delete, Space=Play, K=Keyframe",
            "Save: Ctrl+S | Open: O | Export GIF: X",
            "Mouse: Left Drag to Edit, Left Click to Select"
        ]
        
        y_off = 10
        for line in infos:
            surf = font.render(line, True, TEXT_COLOR)
            screen.blit(surf, (10, y_off))
            y_off += 20

        pygame.display.flip()

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
