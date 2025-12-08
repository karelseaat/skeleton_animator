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
KEYFRAME_COLOR = (255, 200, 0)
TIMELINE_HEIGHT = 150
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
        
        # Color for timeline and bone node visualization
        self.color = (100, 150, 255)  # Default blue

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
                pygame.draw.line(surface, self.color, (px, py), (wx, wy), 2)
            
            # Draw Node Point - always use bone's color
            pygame.draw.circle(surface, self.color, (int(wx), int(wy)), 5)
            
            # Draw selection box and crosshair if selected
            if selected:
                pygame.draw.rect(surface, SELECTED_COLOR, (int(wx) - 12, int(wy) - 12, 24, 24), 2)
                pygame.draw.line(surface, PIVOT_COLOR, (int(wx)-8, int(wy)), (int(wx)+8, int(wy)), 1)
                pygame.draw.line(surface, PIVOT_COLOR, (int(wx), int(wy)-8), (int(wx), int(wy)+8), 1)

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

def get_flat_bone_list(root_bone):
    bones = []
    def _collect(b):
        bones.append(b)
        for c in b.children:
            _collect(c)
    if root_bone:
        _collect(root_bone)
    return bones

def get_keyframe_at_pos(animation, mx, my, duration, root_bone):
    """Find a keyframe near the timeline position (using per-bone tracks)"""
    if duration <= 0 or my < SCREEN_HEIGHT - TIMELINE_HEIGHT or my > SCREEN_HEIGHT:
        return None
    
    flat_bones = get_flat_bone_list(root_bone)
    bone_row_map = {b.name: i for i, b in enumerate(flat_bones)}
    
    closest_keyframe = None
    closest_distance = float('inf')
    
    row_height = 15
    base_ky = SCREEN_HEIGHT - TIMELINE_HEIGHT + 25 # Top margin for timeline
    
    for k in animation.keyframes:
        kx = (k.time / duration) * SCREEN_WIDTH
        
        # Determine Y based on bone track
        row_idx = bone_row_map.get(k.bone_name, 0)
        ky = base_ky + (row_idx * row_height)
        
        # Calculate distance in 2D
        dist_x = abs(mx - kx)
        dist_y = abs(my - ky)
        
        # Use circular click radius
        dist = (dist_x ** 2 + dist_y ** 2) ** 0.5
        
        if dist < 10 and dist < closest_distance:  # Click radius
            closest_distance = dist
            closest_keyframe = k
    
    return closest_keyframe

# -----------------------------------------------------------------------------
# Animation System
# -----------------------------------------------------------------------------

class Keyframe:
    def __init__(self, time, bone_name, state):
        self.time = time
        self.bone_name = bone_name
        self.state = state # {x, y, rot, sx, sy}

class Animation:
    def __init__(self):
        self.keyframes = [] # List of per-bone keyframes, sorted by time
        self.duration = 2.0 # Seconds
        self.loop = True

    def add_keyframe(self, time, bone):
        """Add a keyframe for a specific bone"""
        state = {
            'x': bone.x, 'y': bone.y, 'rot': bone.rotation,
            'sx': bone.scale_x, 'sy': bone.scale_y
        }
        
        # Remove existing keyframe for this bone at same time (approx)
        self.keyframes = [k for k in self.keyframes if not (k.bone_name == bone.name and abs(k.time - time) < 0.01)]
        self.keyframes.append(Keyframe(time, bone.name, state))
        self.keyframes.sort(key=lambda k: k.time)
    
    def get_keyframes_for_bone(self, bone_name):
        """Get all keyframes for a specific bone"""
        return [k for k in self.keyframes if k.bone_name == bone_name]

    def apply(self, time, root_bone):
        if not self.keyframes:
            return

        def apply_bone(bone):
            bone_kfs = self.get_keyframes_for_bone(bone.name)
            if bone_kfs:
                # Find surrounding keyframes for this bone
                prev_k = bone_kfs[0]
                next_k = bone_kfs[-1]
                
                for k in bone_kfs:
                    if k.time <= time:
                        prev_k = k
                    if k.time >= time:
                        next_k = k
                        break
                
                # Interpolate
                t = 0.0
                if next_k.time != prev_k.time:
                    t = (time - prev_k.time) / (next_k.time - prev_k.time)
                
                p = prev_k.state
                n = next_k.state
                
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
        
        # Load color if specified
        if 'color' in b_data:
            color_data = b_data['color']
            if isinstance(color_data, list) and len(color_data) >= 3:
                bone.color = tuple(int(c) for c in color_data[:3])
        
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
        
        # Create per-bone keyframes
        for bone_name, state in bone_states.items():
            if bone_name in bone_map:
                b = bone_map[bone_name]
                kf_state = {
                    'x': state.get('x', b.x),
                    'y': state.get('y', b.y),
                    'rot': state.get('rotation', b.rotation),
                    'sx': state.get('scale_x', b.scale_x),
                    'sy': state.get('scale_y', b.scale_y)
                }
                animation.keyframes.append(Keyframe(time, bone_name, kf_state))
    
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
            "pivot_y": float(bone.pivot_y),
            "color": list(bone.color)
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
    
    # 2. Keyframes - Group per-bone keyframes by time
    keyframes_by_time = {}
    for k in animation.keyframes:
        if k.time not in keyframes_by_time:
            keyframes_by_time[k.time] = {"time": float(k.time), "bones": {}}
        keyframes_by_time[k.time]["bones"][k.bone_name] = {key: float(v) for key, v in k.state.items()}
    
    for k_data in sorted(keyframes_by_time.values(), key=lambda x: x["time"]):
        data["animations"]["keyframes"].append(k_data)
        
    try:
        with open(filepath, "w") as f:
            toml.dump(data, f)
        print(f"Saved scene to {filepath}")
    except Exception as e:
        print(f"Error saving TOML: {e}")

def save_scene_to_json(filepath, root_bone, animation):
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

    def collect_bones(bone):
        b_data = {
            "name": bone.name,
            "x": float(bone.x),
            "y": float(bone.y),
            "rotation": float(bone.rotation),
            "scale_x": float(bone.scale_x),
            "scale_y": float(bone.scale_y),
            "pivot_x": float(bone.pivot_x),
            "pivot_y": float(bone.pivot_y),
            "color": list(bone.color)
        }
        if bone.parent:
            b_data["parent"] = bone.parent.name
        if bone.image_path:
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
    
    keyframes_by_time = {}
    for k in animation.keyframes:
        if k.time not in keyframes_by_time:
            keyframes_by_time[k.time] = {"time": float(k.time), "bones": {}}
        keyframes_by_time[k.time]["bones"][k.bone_name] = {key: float(v) for key, v in k.state.items()}
    
    for k_data in sorted(keyframes_by_time.values(), key=lambda x: x["time"]):
        data["animations"]["keyframes"].append(k_data)

    try:
        with open(filepath, "w") as f:
            json.dump(data, f, indent=4)
        print(f"Saved JSON export to {filepath}")
    except Exception as e:
        print(f"Error saving JSON: {e}")

def save_scene_to_godot(filepath, root_bone, animation):
    # Export as a Godot 4 .tscn file
    # This is a basic implementation and might need tweaking for complex setups
    
    try:
        with open(filepath, "w") as f:
            # 1. Header & Resources
            f.write('[gd_scene load_steps=100 format=3]\n\n')
            
            # Collect external resources (images)
            # Map image path to resource ID
            # Godot paths usually need to be "res://..." but we will use relative paths for now
            # or assume the .tscn is in the project root.
            
            flat_bones = get_flat_bone_list(root_bone)
            img_res_map = {}
            res_id_counter = 1
            
            for b in flat_bones:
                if b.image_path and b.image_path not in img_res_map:
                    # Try to make path relative
                    try:
                        rel = os.path.relpath(b.image_path, start=os.getcwd())
                        path_str = rel.replace("\\", "/") # Godot uses forward slashes
                    except:
                        path_str = b.image_path
                    
                    # Assume assets are in project folder. 
                    # If using absolute paths, Godot might complain.
                    # We'll prefix with res:// if it looks like a local relative path
                    if not os.path.isabs(path_str) and not path_str.startswith("res://"):
                         final_path = f"res://{path_str}"
                    else:
                         final_path = path_str
                         
                    img_res_map[b.image_path] = (res_id_counter, final_path)
                    f.write(f'[ext_resource type="Texture2D" path="{final_path}" id="{res_id_counter}_tex"]\n')
                    res_id_counter += 1
            
            f.write('\n')

            # 2. Animation Resource
            anim_id = f"{res_id_counter}_anim"
            f.write(f'[sub_resource type="Animation" id="{anim_id}"]\n')
            f.write(f'length = {animation.duration}\n')
            if animation.loop:
                f.write('loop_mode = 1\n')
            
            # Animation Tracks
            # We need to export tracks for each bone: position, rotation, scale
            # Godot Node paths will be "Skeleton2D/BoneName"
            
            track_idx = 0
            
            for b in flat_bones:
                # Get keyframes for this bone
                kfs = animation.get_keyframes_for_bone(b.name)
                if not kfs: continue
                
                # Sort by time
                kfs.sort(key=lambda x: x.time)
                
                node_path = f"Skeleton2D/{b.name}"
                
                # --- Position Track ---
                f.write(f'tracks/{track_idx}/type = "value"\n')
                f.write(f'tracks/{track_idx}/imported = false\n')
                f.write(f'tracks/{track_idx}/enabled = true\n')
                f.write(f'tracks/{track_idx}/path = NodePath("{node_path}:position")\n')
                f.write(f'tracks/{track_idx}/interp = 1\n') # Linear
                f.write(f'tracks/{track_idx}/loop_wrap = true\n')
                
                times = ", ".join([str(k.time) for k in kfs])
                values = ", ".join([f"Vector2({k.state['x']}, {k.state['y']})" for k in kfs])
                
                f.write(f'tracks/{track_idx}/keys = {{\n')
                f.write(f'"times": PackedFloat32Array({times}),\n')
                f.write(f'"transitions": PackedFloat32Array({", ".join(["1"] * len(kfs))}),\n')
                f.write(f'"update": 0,\n')
                f.write(f'"values": [{values}]\n')
                f.write(f'}}\n')
                track_idx += 1
                
                # --- Rotation Track ---
                f.write(f'tracks/{track_idx}/type = "value"\n')
                f.write(f'tracks/{track_idx}/path = NodePath("{node_path}:rotation")\n')
                f.write(f'tracks/{track_idx}/interp = 1\n')
                f.write(f'tracks/{track_idx}/keys = {{\n')
                f.write(f'"times": PackedFloat32Array({times}),\n')
                f.write(f'"transitions": PackedFloat32Array({", ".join(["1"] * len(kfs))}),\n')
                f.write(f'"update": 0,\n')
                # Convert degrees to radians for Godot
                rot_values = ", ".join([f"{math.radians(k.state['rot']):.4f}" for k in kfs])
                f.write(f'"values": [{rot_values}]\n')
                f.write(f'}}\n')
                track_idx += 1
                
                # --- Scale Track ---
                f.write(f'tracks/{track_idx}/type = "value"\n')
                f.write(f'tracks/{track_idx}/path = NodePath("{node_path}:scale")\n')
                f.write(f'tracks/{track_idx}/interp = 1\n')
                f.write(f'tracks/{track_idx}/keys = {{\n')
                f.write(f'"times": PackedFloat32Array({times}),\n')
                f.write(f'"transitions": PackedFloat32Array({", ".join(["1"] * len(kfs))}),\n')
                f.write(f'"update": 0,\n')
                scale_values = ", ".join([f"Vector2({k.state['sx']}, {k.state['sy']})" for k in kfs])
                f.write(f'"values": [{scale_values}]\n')
                f.write(f'}}\n')
                track_idx += 1

            f.write(f'[sub_resource type="AnimationLibrary" id="AnimLib_1"]\n')
            f.write(f'_data = {{ "default": SubResource("{anim_id}") }}\n\n')

            # 3. Nodes
            f.write('[node name="SceneRoot" type="Node2D"]\n\n')
            
            f.write('[node name="Skeleton2D" type="Skeleton2D" parent="."]\n\n')
            
            # We need to reconstruct hierarchy recursively
            def write_bone_node(bone, parent_path="Skeleton2D"):
                f.write(f'[node name="{bone.name}" type="Bone2D" parent="{parent_path}"]\n')
                f.write(f'position = Vector2({bone.x}, {bone.y})\n')
                f.write(f'rotation = {math.radians(bone.rotation):.4f}\n')
                f.write(f'scale = Vector2({bone.scale_x}, {bone.scale_y})\n')
                # Rest pose is important for Godot skeletons
                f.write(f'rest = Transform2D({bone.scale_x}, 0, 0, {bone.scale_y}, {bone.x}, {bone.y})\n\n')
                
                # Sprite
                if bone.image_path and bone.image_path in img_res_map:
                     res_id = img_res_map[bone.image_path][0]
                     f.write(f'[node name="Sprite_{bone.name}" type="Sprite2D" parent="{parent_path}/{bone.name}"]\n')
                     f.write(f'texture = ExtResource("{res_id}_tex")\n')
                     
                     # Calculate Offset
                     # Godot center is (0,0). Our pivot is (px, py) relative to top-left.
                     # We need to shift sprite so that (px, py) aligns with (0,0)
                     if bone.original_image:
                         w, h = bone.original_image.get_width(), bone.original_image.get_height()
                         ox = (w / 2.0) - bone.pivot_x
                         oy = (h / 2.0) - bone.pivot_y
                         f.write(f'offset = Vector2({ox}, {oy})\n\n')
                
                for child in bone.children:
                    write_bone_node(child, f"{parent_path}/{bone.name}")

            write_bone_node(root_bone)
            
            # Animation Player
            f.write('[node name="AnimationPlayer" type="AnimationPlayer" parent="."]\n')
            f.write('libraries = { "": SubResource("AnimLib_1") }\n')

        print(f"Saved Godot scene to {filepath}")
    except Exception as e:
        print(f"Error saving Godot scene: {e}")
        import traceback
        traceback.print_exc()

def save_scene_to_spine_json(filepath, root_bone, animation):
    # Basic Spine JSON export
    spine_data = {
        "skeleton": { "hash": "generated", "spine": "3.8", "width": 0, "height": 0, "images": "./assets/" },
        "bones": [],
        "slots": [],
        "skins": [ { "name": "default", "attachments": {} } ],
        "animations": { "animation": {} }
    }
    
    flat_bones = get_flat_bone_list(root_bone)
    
    # 1. Bones
    for b in flat_bones:
        b_data = { "name": b.name }
        if b.parent:
            b_data["parent"] = b.parent.name
        
        # Spine bones are relative to parent. Our Bone.x/y/rot are also relative.
        # We can export the 'rest' pose here.
        # For this tool, the current values (at whatever time frame we are at, 
        # or ideally time 0) are used. 
        # Best practice: Force apply time 0 before export or use a stored rest pose.
        # We'll use the current values in the object, assuming user is at a "setup" frame or satisfied.
        
        b_data["x"] = b.x
        b_data["y"] = b.y
        b_data["rotation"] = b.rotation
        b_data["scaleX"] = b.scale_x
        b_data["scaleY"] = b.scale_y
        # b_data["length"] = 100 # Visual length, maybe calculate from image?
        
        spine_data["bones"].append(b_data)
        
        # 2. Slots & Attachments
        if b.image_path:
            slot_name = f"{b.name}_slot"
            att_name = b.name
            
            # Add Slot
            spine_data["slots"].append({
                "name": slot_name,
                "bone": b.name,
                "attachment": att_name
            })
            
            # Add Attachment to Skin
            # Try to get filename only for attachment name
            img_filename = os.path.basename(b.image_path)
            # Remove extension
            img_name_no_ext = os.path.splitext(img_filename)[0]
            
            att_data = {
                "path": img_name_no_ext, # Spine appends .png
                "x": 0, "y": 0, "scaleX": 1, "scaleY": 1, "rotation": 0,
                "width": 100, "height": 100
            }
            
            # Adjust offset based on pivot
            # In Spine, attachment x/y is relative to bone.
            # Our pivot is relative to top-left of image.
            if b.original_image:
                 w = b.original_image.get_width()
                 h = b.original_image.get_height()
                 att_data["width"] = w
                 att_data["height"] = h
                 
                 # Center of image is w/2, h/2.
                 # Pivot is at px, py.
                 # We want the Bone (0,0) to be at the pivot.
                 # So the image center is at (w/2 - px, h/2 - py) relative to bone.
                 att_data["x"] = (w / 2.0) - b.pivot_x
                 att_data["y"] = (h / 2.0) - b.pivot_y
                 # Y-axis might be flipped in Spine? Spine Y is up. Pygame Y is down.
                 # We might need to flip Y.
                 att_data["y"] = -att_data["y"]
            
            spine_data["skins"][0]["attachments"][slot_name] = {
                att_name: att_data
            }

    # 3. Animations
    anim_bones = {}
    
    for b in flat_bones:
        kfs = animation.get_keyframes_for_bone(b.name)
        if not kfs: continue
        kfs.sort(key=lambda x: x.time)
        
        timelines = {}
        
        # Translate
        translate_keys = []
        rotate_keys = []
        scale_keys = []
        
        for k in kfs:
            t = k.time
            # Spine Y is Up, Pygame is Down. Negate Y translation.
            translate_keys.append({ "time": t, "x": k.state['x'], "y": -k.state['y'] })
            rotate_keys.append({ "time": t, "angle": k.state['rot'] }) # Rot might need negation too?
            scale_keys.append({ "time": t, "x": k.state['sx'], "y": k.state['sy'] })
            
        timelines["translate"] = translate_keys
        timelines["rotate"] = rotate_keys
        timelines["scale"] = scale_keys
        
        anim_bones[b.name] = timelines
        
    spine_data["animations"]["animation"]["bones"] = anim_bones
    
    try:
        with open(filepath, "w") as f:
            json.dump(spine_data, f, indent=4)
        print(f"Saved Spine JSON to {filepath}")
    except Exception as e:
        print(f"Error saving Spine JSON: {e}")

def save_scene_to_standalone_python(filepath, root_bone, animation):
    # Serialize data first
    data = {
        "meta": { "duration": animation.duration, "loop": animation.loop },
        "bones": [],
        "animations": { "keyframes": [] }
    }

    def collect_bones(bone):
        b_data = {
            "name": bone.name,
            "x": float(bone.x), "y": float(bone.y),
            "rotation": float(bone.rotation),
            "scale_x": float(bone.scale_x), "scale_y": float(bone.scale_y),
            "pivot_x": float(bone.pivot_x), "pivot_y": float(bone.pivot_y)
        }
        if bone.parent: b_data["parent"] = bone.parent.name
        if bone.image_path:
             try:
                rel = os.path.relpath(bone.image_path, start=os.getcwd())
                if not rel.startswith(".."): b_data["image"] = rel
                else: b_data["image"] = bone.image_path
             except ValueError: b_data["image"] = bone.image_path
        data["bones"].append(b_data)
        for child in bone.children: collect_bones(child)
            
    collect_bones(root_bone)
    
    keyframes_by_time = {}
    for k in animation.keyframes:
        if k.time not in keyframes_by_time:
            keyframes_by_time[k.time] = {"time": float(k.time), "bones": {}}
        keyframes_by_time[k.time]["bones"][k.bone_name] = {key: float(v) for key, v in k.state.items()}
    for k_data in sorted(keyframes_by_time.values(), key=lambda x: x["time"]):
        data["animations"]["keyframes"].append(k_data)

    # Template
    script_content = f'''import pygame
import math
import sys
import os

# --- Configuration ---
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
BG_COLOR = (30, 30, 30)
DATA = {json.dumps(data, indent=4)}

# --- Engine Classes ---
class Bone:
    def __init__(self, name, image_path=None, parent=None):
        self.name = name
        self.image = None
        if image_path and os.path.exists(image_path):
            try:
                self.image = pygame.image.load(image_path).convert_alpha()
            except Exception as e:
                print(f"Error loading {{image_path}}: {{e}}")
        self.parent = parent
        self.children = []
        if parent: parent.children.append(self)
        
        # Transform
        self.x = 0.0
        self.y = 0.0
        self.rotation = 0.0
        self.scale_x = 1.0
        self.scale_y = 1.0
        self.pivot_x = 0.0
        self.pivot_y = 0.0
        
        if self.image:
            self.pivot_x = self.image.get_width() / 2.0
            self.pivot_y = self.image.get_height() / 2.0

    def get_world_transform(self):
        if self.parent:
            px, py, prot, psx, psy = self.parent.get_world_transform()
            lx = self.x * psx
            ly = self.y * psy
            rad = math.radians(prot)
            cos_a = math.cos(rad)
            sin_a = math.sin(rad)
            wx = px + (lx * cos_a - ly * sin_a)
            wy = py + (lx * sin_a + ly * cos_a)
            return wx, wy, prot + self.rotation, psx * self.scale_x, psy * self.scale_y
        else:
            return self.x, self.y, self.rotation, self.scale_x, self.scale_y

    def draw(self, surface):
        wx, wy, wrot, wsx, wsy = self.get_world_transform()
        if self.image:
            if abs(wsx - 1.0) > 0.01 or abs(wsy - 1.0) > 0.01:
                w = int(self.image.get_width() * abs(wsx))
                h = int(self.image.get_height() * abs(wsy))
                scaled = pygame.transform.scale(self.image, (max(1, w), max(1, h)))
            else:
                scaled = self.image
            rotated = pygame.transform.rotate(scaled, -wrot)
            
            # Pivot calc
            piv_x = self.pivot_x * wsx
            piv_y = self.pivot_y * wsy
            rad = math.radians(wrot)
            cos_a = math.cos(rad)
            sin_a = math.sin(rad)
            rot_piv_x = piv_x * cos_a - piv_y * sin_a
            rot_piv_y = piv_x * sin_a + piv_y * cos_a
            
            rect = rotated.get_rect()
            rect.center = (wx + (rect.width/2 - rot_piv_x) - rect.width/2, 
                           wy + (rect.height/2 - rot_piv_y) - rect.height/2)
            surface.blit(rotated, rect.topleft)
        
        for child in self.children:
            child.draw(surface)

class Animation:
    def __init__(self):
        self.keyframes = []
        self.duration = 2.0
        self.loop = True

    def apply(self, time, root_bone):
        if not self.keyframes: return
        
        # Flatten hierarchy for easy access
        bone_map = {{}}
        def map_bones(b):
            bone_map[b.name] = b
            for c in b.children: map_bones(c)
        map_bones(root_bone)

        for bone_name, b in bone_map.items():
            # Find keyframes for this bone
            bone_kfs = [k for k in self.keyframes if k['bone'] == bone_name]
            if not bone_kfs: continue
            
            bone_kfs.sort(key=lambda x: x['time'])
            
            # Find surrounding
            prev_k = bone_kfs[0]
            next_k = bone_kfs[-1]
            
            for k in bone_kfs:
                if k['time'] <= time: prev_k = k
                if k['time'] >= time: 
                    next_k = k
                    break
            
            t = 0.0
            if next_k['time'] != prev_k['time']:
                t = (time - prev_k['time']) / (next_k['time'] - prev_k['time'])
            
            p = prev_k['state']
            n = next_k['state']
            
            b.x = p['x'] + (n['x'] - p['x']) * t
            b.y = p['y'] + (n['y'] - p['y']) * t
            
            diff = n['rot'] - p['rot']
            while diff < -180: diff += 360
            while diff > 180: diff -= 360
            b.rotation = p['rot'] + diff * t
            
            b.scale_x = p['sx'] + (n['sx'] - p['sx']) * t
            b.scale_y = p['sy'] + (n['sy'] - p['sy']) * t

# --- Setup ---
def load_scene(data):
    bone_map = {{}}
    root_bone = None
    
    # Bones
    for b_data in data['bones']:
        name = b_data['name']
        img = b_data.get('image')
        bone = Bone(name, img)
        bone.x = b_data.get('x', 0)
        bone.y = b_data.get('y', 0)
        bone.rotation = b_data.get('rotation', 0)
        bone.scale_x = b_data.get('scale_x', 1)
        bone.scale_y = b_data.get('scale_y', 1)
        if 'pivot_x' in b_data: bone.pivot_x = b_data['pivot_x']
        if 'pivot_y' in b_data: bone.pivot_y = b_data['pivot_y']
        bone_map[name] = bone
    
    # Hierarchy
    for b_data in data['bones']:
        name = b_data['name']
        parent_name = b_data.get('parent')
        if parent_name and parent_name in bone_map:
            bone_map[name].parent = bone_map[parent_name]
            bone_map[parent_name].children.append(bone_map[name])
        elif not root_bone:
            root_bone = bone_map[name] # First orphan is root
            
    if not root_bone and bone_map: root_bone = list(bone_map.values())[0]
    
    # Animation
    anim = Animation()
    anim.duration = data['meta'].get('duration', 2.0)
    anim.loop = data['meta'].get('loop', True)
    
    for k_data in data['animations']['keyframes']:
        time = k_data['time']
        for b_name, state in k_data['bones'].items():
            kf = {{
                'time': time,
                'bone': b_name,
                'state': {{
                    'x': state.get('x', 0), 'y': state.get('y', 0),
                    'rot': state.get('rot', 0),
                    'sx': state.get('sx', 1), 'sy': state.get('sy', 1)
                }}
            }}
            anim.keyframes.append(kf)
            
    return root_bone, anim

# --- Main ---
def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Skeleton Animation Playback")
    clock = pygame.time.Clock()
    
    root_bone, animation = load_scene(DATA)
    
    # Center root
    if root_bone:
        root_bone.x += SCREEN_WIDTH // 2
        root_bone.y += SCREEN_HEIGHT // 2
        
    running = True
    current_time = 0.0
    
    while running:
        dt = clock.tick(60) / 1000.0
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT: running = False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE: running = False

        current_time += dt
        if current_time > animation.duration:
            if animation.loop: current_time = 0
            else: current_time = animation.duration
            
        if root_bone:
            animation.apply(current_time, root_bone)
        
        screen.fill(BG_COLOR)
        if root_bone: root_bone.draw(screen)
        pygame.display.flip()

    pygame.quit()

if __name__ == "__main__":
    main()
'''
    try:
        with open(filepath, "w") as f:
            f.write(script_content)
        print(f"Saved Standalone Python script to {filepath}")
    except Exception as e:
        print(f"Error saving Standalone Python: {e}")


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
        
        # Draw time markers with vertical lines
        if dur > 0:
            # Calculate time interval (0.1, 0.2, 0.5, 1.0 depending on duration)
            if dur <= 1.0:
                time_interval = 0.1
            elif dur <= 2.0:
                time_interval = 0.25
            elif dur <= 5.0:
                time_interval = 0.5
            else:
                time_interval = 1.0
            
            time_marker = 0
            while time_marker <= dur + 0.01:  # Small epsilon for floating point
                x = (time_marker / dur) * w
                
                # Major tick (full height)
                pygame.draw.line(surface, (100, 100, 100), (x, h - TIMELINE_HEIGHT), (x, h - TIMELINE_HEIGHT + 15), 1)
                
                # Time label for major ticks
                if time_marker % 1.0 < 0.01 or time_marker % 1.0 > 0.99:  # Every 1 second
                    font_small = pygame.font.SysFont('Arial', 10)
                    time_text = font_small.render(f'{time_marker:.1f}s', True, (150, 150, 150))
                    surface.blit(time_text, (int(x) - 10, h - TIMELINE_HEIGHT + 16))
                
                time_marker += time_interval
        
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

def capture_animation_frames(root_bone, animation, camera_pan, fps=30):
    frames = []
    duration = animation.duration
    steps = int(duration * fps)
    
    # Store original state to restore later
    # We should really deep copy or something, but for now we just re-apply current time at end?
    # Actually, we can't easily capture "current state" of the whole tree without a deep copy method.
    # But since we only modify x/y/rot/scale, we can just save the current time variable from main loop 
    # but we don't have access to it here. 
    # We will just proceed and let the main loop re-apply the correct time next frame.
    
    print(f"Capturing {steps} frames...")
    
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

# -----------------------------------------------------------------------------
# Main Editor
# -----------------------------------------------------------------------------

def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Skeleton Animator")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont('Arial', 14)
    font_small = pygame.font.SysFont('Arial', 10)

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
    dragging_keyframe = None
    selected_keyframe = None
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
                    if selected_keyframe:
                        animation.keyframes.remove(selected_keyframe)
                        print(f"Deleted keyframe for '{selected_keyframe.bone_name}' at {selected_keyframe.time:.2f}s")
                        selected_keyframe = None
                    elif selected_bone and selected_bone.parent: # Cannot delete root
                        # Delete all keyframes associated with this bone and its children
                        def get_bone_names_to_delete(bone):
                            names = {bone.name}
                            for child in bone.children:
                                names.update(get_bone_names_to_delete(child))
                            return names
                        
                        bone_names = get_bone_names_to_delete(selected_bone)
                        animation.keyframes = [k for k in animation.keyframes if k.bone_name not in bone_names]
                        
                        p = selected_bone.parent
                        p.children.remove(selected_bone)
                        selected_bone = p
                        print(f"Deleted bone and {len(bone_names)} keyframe tracks")
                
                elif event.key == pygame.K_SPACE:
                    is_playing = not is_playing
                
                elif event.key == pygame.K_k:
                    animation.add_keyframe(current_time, selected_bone)
                    print(f"Keyframe added for '{selected_bone.name}' at {current_time:.2f}s")
                
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

                # Export Formats
                elif event.key == pygame.K_j: # Export JSON
                    filepath = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON File", "*.json")])
                    if filepath:
                        save_scene_to_json(filepath, root_bone, animation)

                elif event.key == pygame.K_g: # Export Godot
                    filepath = filedialog.asksaveasfilename(defaultextension=".tscn", filetypes=[("Godot Scene", "*.tscn")])
                    if filepath:
                        save_scene_to_godot(filepath, root_bone, animation)
                        
                elif event.key == pygame.K_u: # Export Spine JSON
                    filepath = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("Spine JSON", "*.json")])
                    if filepath:
                        save_scene_to_spine_json(filepath, root_bone, animation)

                elif event.key == pygame.K_p: # Export Standalone Python
                    filepath = filedialog.asksaveasfilename(defaultextension=".py", filetypes=[("Python Script", "*.py")])
                    if filepath:
                        save_scene_to_standalone_python(filepath, root_bone, animation)

                # Export GIF / Video / Sheet
                elif event.key == pygame.K_x:
                    filepath = filedialog.asksaveasfilename(defaultextension=".gif", filetypes=[("GIF Image", "*.gif")])
                    if filepath:
                        export_gif_with_camera(filepath, root_bone, animation, camera_pan)
                
                elif event.key == pygame.K_v: # Export Video
                    filepath = filedialog.asksaveasfilename(defaultextension=".mp4", filetypes=[("MP4 Video", "*.mp4")])
                    if filepath:
                        export_video(filepath, root_bone, animation, camera_pan)
                
                elif event.key == pygame.K_h: # Export Sprite Sheet
                    filepath = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG Image", "*.png")])
                    if filepath:
                        export_sprite_sheet(filepath, root_bone, animation, camera_pan)

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1: # Left Click
                    # Check if clicking timeline
                    if my > SCREEN_HEIGHT - TIMELINE_HEIGHT:
                        clicked_kf = get_keyframe_at_pos(animation, mx, my, animation.duration, root_bone)
                        if clicked_kf:
                            selected_keyframe = clicked_kf
                            dragging = "KEYFRAME"
                            dragging_keyframe = clicked_kf
                        else:
                            selected_keyframe = None
                            ratio = mx / SCREEN_WIDTH
                            current_time = ratio * animation.duration
                            if not is_playing:
                                animation.apply(current_time, root_bone)
                            dragging = "TIMELINE"
                    else:
                        # Check if clicking a bone node
                        selected_keyframe = None
                        world_mx = mx - camera_pan[0]
                        world_my = my - camera_pan[1]
                        clicked = get_bone_at_pos(root_bone, world_mx, world_my)
                        if clicked:
                            selected_bone = clicked
                            dragging = "BONE"
                        else:
                            dragging = "CAMERA"
                elif event.button == 3: # Right Click - Delete keyframe from timeline
                    clicked_kf = get_keyframe_at_pos(animation, mx, my, animation.duration, root_bone)
                    if clicked_kf:
                        animation.keyframes.remove(clicked_kf)
                        if selected_keyframe == clicked_kf:
                            selected_keyframe = None
                        print(f"Deleted keyframe for '{clicked_kf.bone_name}' at {clicked_kf.time:.2f}s")
                elif event.button == 4: # Scroll Up
                    if selected_bone and mode == "ROTATE":
                        selected_bone.rotation += 5
                elif event.button == 5: # Scroll Down
                    if selected_bone and mode == "ROTATE":
                        selected_bone.rotation -= 5

            elif event.type == pygame.MOUSEBUTTONUP:
                if dragging == "BONE" and selected_bone and mode != "PIVOT":
                    # Auto-key on release if we were moving/rotating a bone
                    animation.add_keyframe(current_time, selected_bone)
                    print(f"Auto-keyed change for '{selected_bone.name}' at {current_time:.2f}s")
                
                dragging = False
                dragging_keyframe = None

            elif event.type == pygame.MOUSEMOTION:
                dx = mx - last_mouse_pos[0]
                dy = my - last_mouse_pos[1]
                
                if dragging == "KEYFRAME" and dragging_keyframe and animation.duration > 0:
                    # Drag keyframe to new time
                    ratio = max(0, min(1, mx / SCREEN_WIDTH))
                    new_time = ratio * animation.duration
                    dragging_keyframe.time = new_time
                    animation.keyframes.sort(key=lambda k: k.time)
                
                elif dragging == "TIMELINE":
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
        # Re-draw timeline markers (per-bone keyframes) on top because render_scene handles base timeline
        if animation.duration > 0:
            flat_bones = get_flat_bone_list(root_bone)
            bone_row_map = {b.name: i for i, b in enumerate(flat_bones)}
            
            row_height = 15
            base_ky = SCREEN_HEIGHT - TIMELINE_HEIGHT + 25
            
            # Draw track labels (Bone names)
            for b in flat_bones:
                row_idx = bone_row_map[b.name]
                ky = base_ky + (row_idx * row_height)
                name_surf = font_small.render(b.name, True, (100, 100, 100))
                screen.blit(name_surf, (5, ky - 5))
                # Optional: Draw faint horizontal track line
                pygame.draw.line(screen, (40, 40, 40), (60, ky), (SCREEN_WIDTH, ky), 1)

            # Draw keyframes with track spacing
            for k in animation.keyframes:
                kx = (k.time / animation.duration) * SCREEN_WIDTH
                
                # Determine Y based on bone track
                row_idx = bone_row_map.get(k.bone_name, 0)
                ky = base_ky + (row_idx * row_height)
                
                # Get bone's color
                bone_obj = None
                for b in flat_bones:
                    if b.name == k.bone_name:
                        bone_obj = b
                        break
                
                color = bone_obj.color if bone_obj else (100, 150, 255)
                
                pygame.draw.circle(screen, color, (int(kx), int(ky)), 5)
                
                # Draw selection box around selected keyframe
                if selected_keyframe == k:
                    pygame.draw.rect(screen, SELECTED_COLOR, (int(kx) - 12, int(ky) - 12, 24, 24), 2)

        # Info Text
        selected_kfs = animation.get_keyframes_for_bone(selected_bone.name)
        infos = [
            f"Mode: {mode} (Q,W,E,R) | Bones: {'ON' if show_bones else 'OFF'} (B)",
            f"Selected: {selected_bone.name} | Keyframes: {len(selected_kfs)}",
            f"Time: {current_time:.2f} / {animation.duration:.2f}",
            "Controls: L=Load Img, N=New Node, Del=Delete, Space=Play, K=Keyframe (for selected bone)",
            "Timeline: Left Drag Keyframe to Move, Right Click to Delete",
            "Save: Ctrl+S | Open: O | JSON: J | Godot: G | Spine: U | Standalone: P",
            "Export Media: GIF: X | Video: V | Sheet: H"
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
