import toml
import json
import os
import math
from engine import Bone, Animation, Keyframe, get_flat_bone_list
from easing import EASING_DEFAULT

def load_scene_from_toml(filepath):
    try:
        data = toml.load(filepath)
    except Exception as e:
        print(f"Error loading TOML: {e}")
        return None, None

    # 1. Build Bones
    bone_map = {}
    bones_data = data.get('bones', [])
    
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
            if root_bone is None:
                root_bone = bone
    
    if not root_bone and bone_map:
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
                easing_type = state.get('easing', EASING_DEFAULT) # Load easing type
                animation.keyframes.append(Keyframe(time, bone_name, kf_state, easing_type))
    
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
        # Include easing type
        kf_state_data = {key: float(v) for key, v in k.state.items()}
        kf_state_data['easing'] = k.easing_type
        keyframes_by_time[k.time]["bones"][k.bone_name] = kf_state_data
    
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
    
    # 2. Keyframes - Group per-bone keyframes by time
    keyframes_by_time = {}
    for k in animation.keyframes:
        if k.time not in keyframes_by_time:
            keyframes_by_time[k.time] = {"time": float(k.time), "bones": {}}
        kf_state_data = {key: float(v) for key, v in k.state.items()}
        kf_state_data['easing'] = k.easing_type # Include easing type
        keyframes_by_time[k.time]["bones"][k.bone_name] = kf_state_data
    
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
    
    try:
        with open(filepath, "w") as f:
            # 1. Header & Resources
            f.write('[gd_scene load_steps=100 format=3]\n\n')
            
            # Collect external resources (images)
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
                    
                    if not os.path.isabs(path_str) and not path_str.startswith("res://"):
                         final_path = f"res://{path_str}"
                    else:
                         final_path = path_str
                         
                    img_res_map[b.image_path] = (res_id_counter, final_path)
                    f.write(f"[ext_resource type='Texture2D' path='{final_path}' id='{res_id_counter}_tex']")
                    res_id_counter += 1
            
            f.write('\n')

            # 2. Animation Resource
            anim_id = f"{res_id_counter}_anim"
            f.write(f'[sub_resource type="Animation" id="{anim_id}"]')
            f.write(f'length = {animation.duration}')
            if animation.loop:
                f.write('loop_mode = 1\n')
            
            # Animation Tracks
            track_idx = 0
            
            for b in flat_bones:
                kfs = animation.get_keyframes_for_bone(b.name)
                if not kfs: continue
                
                kfs.sort(key=lambda x: x.time)
                
                node_path = f"Skeleton2D/{b.name}"
                
                # --- Position Track ---
                f.write(f'tracks/{track_idx}/type = "value"\n')
                f.write(f'tracks/{track_idx}/imported = false\n')
                f.write(f'tracks/{track_idx}/enabled = true\n')
                f.write(f'tracks/{track_idx}/path = NodePath("{node_path}:position")\n')
                f.write(f'tracks/{track_idx}/interp = 1 # Linear\n')
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
            f.write('[node name="Skeleton2D" type="Skeleton2D" parent="."]')
            
            def write_bone_node(bone, parent_path="Skeleton2D"):
                f.write(f'[node name="{bone.name}" type="Bone2D" parent="{parent_path}"]\n')
                f.write(f'position = Vector2({bone.x}, {bone.y})\n')
                f.write(f'rotation = {math.radians(bone.rotation):.4f}\n')
                f.write(f'scale = Vector2({bone.scale_x}, {bone.scale_y})\n')
                f.write(f'rest = Transform2D({bone.scale_x}, 0, 0, {bone.scale_y}, {bone.x}, {bone.y})\n\n')
                
                if bone.image_path and bone.image_path in img_res_map:
                     res_id = img_res_map[bone.image_path][0]
                     f.write(f'[node name="Sprite_{bone.name}" type="Sprite2D" parent="{parent_path}/{bone.name}"]\n')
                     f.write(f'texture = ExtResource("{res_id}_tex")\n')
                     
                     if bone.original_image:
                         w, h = bone.original_image.get_width(), bone.original_image.get_height()
                         ox = (w / 2.0) - bone.pivot_x
                         oy = (h / 2.0) - bone.pivot_y
                         f.write(f'offset = Vector2({ox}, {oy})\n\n')
                
                for child in bone.children:
                    write_bone_node(child, f"{parent_path}/{bone.name}")

            write_bone_node(root_bone)
            f.write('[node name="AnimationPlayer" type="AnimationPlayer" parent="."]')
            f.write('libraries = { "": SubResource("AnimLib_1") }\n')

        print(f"Saved Godot scene to {filepath}")
    except Exception as e:
        print(f"Error saving Godot scene: {e}")

def save_scene_to_spine_json(filepath, root_bone, animation):
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
        
        b_data["x"] = b.x
        b_data["y"] = b.y
        b_data["rotation"] = b.rotation
        b_data["scaleX"] = b.scale_x
        b_data["scaleY"] = b.scale_y
        
        spine_data["bones"].append(b_data)
        
        # 2. Slots & Attachments
        if b.image_path:
            slot_name = f"{b.name}_slot"
            att_name = b.name
            
            spine_data["slots"].append({
                "name": slot_name,
                "bone": b.name,
                "attachment": att_name
            })
            
            img_filename = os.path.basename(b.image_path)
            img_name_no_ext = os.path.splitext(img_filename)[0]
            
            att_data = {
                "path": img_name_no_ext,
                "x": 0, "y": 0, "scaleX": 1, "scaleY": 1, "rotation": 0,
                "width": 100, "height": 100
            }
            
            if b.original_image:
                 w = b.original_image.get_width()
                 h = b.original_image.get_height()
                 att_data["width"] = w
                 att_data["height"] = h
                 att_data["x"] = (w / 2.0) - b.pivot_x
                 att_data["y"] = -((h / 2.0) - b.pivot_y) # Flip Y
            
            spine_data["skins"][0]["attachments"].setdefault(slot_name, {{}})[att_name] = att_data

    # 3. Animations
    anim_bones = {}
    
    for b in flat_bones:
        kfs = animation.get_keyframes_for_bone(b.name)
        if not kfs: continue
        kfs.sort(key=lambda x: x.time)
        
        timelines = {}
        translate_keys = []
        rotate_keys = []
        scale_keys = []
        
        for k in kfs:
            t = k.time
            translate_keys.append({ "time": t, "x": k.state['x'], "y": -k.state['y'] })
            rotate_keys.append({ "time": t, "angle": k.state['rot'] })
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
    script_content = """import pygame
import math
import sys
import os

# --- Configuration ---
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
BG_COLOR = (30, 30, 30)

# Easing functions for animation
def linear(t): return t
def ease_in_quad(t): return t * t
def ease_out_quad(t): return 1 - (1 - t) * (1 - t)
def ease_in_out_quad(t): return 2 * t * t if t < 0.5 else 1 - (-2 * t + 2) * (-2 * t + 2) / 2
def ease_in_cubic(t): return t * t * t
def ease_out_cubic(t): return 1 - pow(1 - t, 3)
def ease_out_cubic(t): return 1 - pow(1 - t, 3)
def ease_in_out_cubic(t): return 4 * t * t * t if t < 0.5 else 1 - pow(-2 * t + 2, 3) / 2
def ease_in_quart(t): return t * t * t * t
def ease_out_quart(t): return 1 - pow(1 - t, 4)
def ease_in_out_quart(t): return 8 * t * t * t * t if t < 0.5 else 1 - pow(-2 * t + 2, 4) / 2
def ease_in_quint(t): return t * t * t * t * t
def ease_out_quint(t): return 1 - pow(1 - t, 5)
def ease_in_out_quint(t): return 16 * t * t * t * t * t if t < 0.5 else 1 - pow(-2 * t + 2, 5) / 2

EASING_FUNCTIONS = {
    "linear": linear, "in_quad": ease_in_quad, "out_quad": ease_out_quad, "in_out_quad": ease_in_out_quad,
    "in_cubic": ease_in_cubic, "out_cubic": ease_out_cubic, "in_out_cubic": ease_in_out_cubic,
    "in_quart": ease_in_quart, "out_quart": ease_out_quart, "in_out_quart": ease_in_out_quart,
    "in_quint": ease_in_quint, "out_quint": ease_out_quint, "in_out_quint": ease_in_out_quint,
}
EASING_DEFAULT = "linear" # Default easing if not specified

DATA = __DATA_PLACEHOLDER__

# --- Engine Classes ---
class Bone:
    def __init__(self, name, image_path=None, parent=None):
        self.name = name
        self.image = None
        if image_path and os.path.exists(image_path):
            try:
                self.image = pygame.image.load(image_path).convert_alpha()
            except Exception as e:
                print(f"Error loading {image_path}: {e}")
        self.parent = parent
        self.children = []
        if parent: self.children.append(self)
        
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

class Keyframe:
    def __init__(self, time, bone_name, state, easing='linear'):
        self.time = time
        self.bone_name = bone_name
        self.state = state
        self.easing = easing

class Animation:
    def __init__(self):
        self.keyframes = []
        self.duration = 2.0
        self.loop = True

    def apply(self, time, root_bone):
        if not self.keyframes: return
        
        bone_map = {}
        def map_bones(b):
            bone_map[b.name] = b
            for c in b.children: map_bones(c)
        map_bones(root_bone)

        for bone_name, b in bone_map.items():
            bone_kfs = [k for k in self.keyframes if k['bone'] == bone_name]
            if not bone_kfs: continue
            
            bone_kfs.sort(key=lambda x: x['time'])
            
            prev_k = bone_kfs[0]
            next_k = bone_kfs[0]

            found_next = False
            for k in bone_kfs:
                if k['time'] <= time: prev_k = k
                if k['time'] > time: 
                    next_k = k
                    found_next = True
                    break
            
            if not found_next:
                if self.loop:
                    if len(bone_kfs) > 1:
                        next_k = bone_kfs[0]
                        prev_k = bone_kfs[-1]
                        segment_duration = self.duration - prev_k['time'] + next_k['time']
                        t_in_segment = (time - prev_k['time']) if time >= prev_k['time'] else (self.duration - prev_k['time'] + time)
                        t_normalized = t_in_segment / segment_duration if segment_duration > 0 else 0
                    else:
                        t_normalized = 0.0
                        prev_k = bone_kfs[0]
                        next_k = bone_kfs[0]
                else:
                    t_normalized = 1.0
                    prev_k = bone_kfs[-1]
                    next_k = bone_kfs[-1]
            else:
                segment_duration = next_k['time'] - prev_k['time']
                t_normalized = (time - prev_k['time']) / segment_duration if segment_duration > 0 else 0

            easer_func = EASING_FUNCTIONS.get(prev_k['easing'], EASING_FUNCTIONS[EASING_DEFAULT])
            eased_t = easer_func(t_normalized)
            
            p = prev_k['state']
            n = next_k['state']
            
            b.x = p['x'] + (n['x'] - p['x']) * eased_t
            b.y = p['y'] + (n['y'] - p['y']) * eased_t
            
            diff = n['rot'] - p['rot']
            while diff < -180: diff += 360
            while diff > 180: diff -= 360
            b.rotation = p['rot'] + diff * eased_t
            
            b.scale_x = p['sx'] + (n['sx'] - p['sx']) * eased_t
            b.scale_y = p['sy'] + (n['sy'] - p['sy']) * eased_t

# --- Setup ---
def load_scene(data):
    bone_map = {}
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
            root_bone = bone_map[name] 
            
    if not root_bone and bone_map: root_bone = list(bone_map.values())[0]
    
    # Animation
    anim = Animation()
    anim.duration = data['meta'].get('duration', 2.0)
    anim.loop = data['meta'].get('loop', True)
    
    for k_data in data['animations']['keyframes']:
        time = k_data['time']
        for b_name, state in k_data['bones'].items():
            kf = {
                'time': time,
                'bone': b_name,
                'state': {
                    'x': state.get('x', 0), 'y': state.get('y', 0),
                    'rot': state.get('rot', 0),
                    'sx': state.get('sx', 1), 'sy': state.get('sy', 1)
                },
                'easing': state.get('easing', 'linear')
            }
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
""".replace("__DATA_PLACEHOLDER__", json.dumps(data, indent=4))
    try:
        with open(filepath, "w") as f:
            f.write(script_content)
        print(f"Saved Standalone Python script to {filepath}")
    except Exception as e:
        print(f"Error saving Standalone Python: {e}")
