import pygame
import math
import os
from constants import *
import easing
from easing import EASING_FUNCTIONS, EASING_DEFAULT

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
        
        # Size in pixels (actual display size, not scale)
        if self.original_image:
            self.base_width = float(self.original_image.get_width())
            self.base_height = float(self.original_image.get_height())
            self.size_x = self.base_width
            self.size_y = self.base_height
        else:
            self.base_width = 100.0 # Default visual size for non-image bones
            self.base_height = 100.0
            self.size_x = 100.0
            self.size_y = 100.0
        
        # Pivot point: 0 = middle, -(size/2) = top-left, +(size/2) = bottom-right
        self.pivot_x = 0.0
        self.pivot_y = 0.0
        
        # Color for timeline and bone node visualization
        self.color = (100, 150, 255)  # Default blue
        
        # Opacity
        self.alpha = 255.0
        
        # Drawing Order
        self.z_index = 0

    def get_world_transform(self):
        """
        Calculates the world position and rotation.
        Returns (x, y, rotation_degrees, scale_x, scale_y)
        """
        # Calculate Local Scale Ratio
        local_scale_x = 1.0
        local_scale_y = 1.0
        
        # Ensure base_width/height exist (handle legacy objects at runtime)
        if not hasattr(self, 'base_width'):
            if self.original_image:
                self.base_width = float(self.original_image.get_width())
                self.base_height = float(self.original_image.get_height())
            else:
                self.base_width = 1.0
                self.base_height = 1.0

        if self.base_width > 0: local_scale_x = self.size_x / self.base_width
        if self.base_height > 0: local_scale_y = self.size_y / self.base_height
        

        if self.parent:
            px, py, prot, psx, psy = self.parent.get_world_transform()
            
            # Local position IS scaled by parent scale
            lx = self.x * psx
            ly = self.y * psy
            
            # Rotate local position by parent rotation
            rad = math.radians(prot)
            cos_a = math.cos(rad)
            sin_a = math.sin(rad)
            
            wx = px + (lx * cos_a - ly * sin_a)
            wy = py + (lx * sin_a + ly * cos_a)
            
            # Return cumulative scale
            return wx, wy, prot + self.rotation, local_scale_x * psx, local_scale_y * psy
        else:
            return self.x, self.y, self.rotation, local_scale_x, local_scale_y

    def draw_image(self, surface):
        wx, wy, wrot, scale_x, scale_y = self.get_world_transform()
        
        if self.original_image:
            # Reconstruct target pixel size from scale
            w = int(abs(scale_x * self.base_width))
            h = int(abs(scale_y * self.base_height))
            
            if w > 0 and h > 0:
                scaled_img = pygame.transform.scale(self.original_image, (w, h))
            else:
                scaled_img = self.original_image
                
            rotated_img = pygame.transform.rotate(scaled_img, -wrot) # Pygame rotates CCW
            
            # Calculate offset due to pivot rotation
            # self.pivot_x is in pixels (relative to base image).
            # When we scale the image, the pivot moves too.
            scaled_piv_x = self.pivot_x * abs(scale_x)
            scaled_piv_y = self.pivot_y * abs(scale_y)
            
            rad = math.radians(wrot)
            cos_a = math.cos(rad)
            sin_a = math.sin(rad)
            
            rot_piv_x = scaled_piv_x * cos_a - scaled_piv_y * sin_a
            rot_piv_y = scaled_piv_x * sin_a + scaled_piv_y * cos_a
            
            # Position = world pos - rotated pivot + rect correction
            rect = rotated_img.get_rect()
            rect.center = (wx + (rect.width/2 - rot_piv_x) - rect.width/2, 
                           wy + (rect.height/2 - rot_piv_y) - rect.height/2)
            
            if self.alpha < 255:
                rotated_img.set_alpha(int(self.alpha))
            
            surface.blit(rotated_img, rect.topleft)

    def draw_debug_elements(self, surface, selected_bone=None, mode="SELECT"):
        wx, wy, _, _, _ = self.get_world_transform()
        selected = (self == selected_bone)

        # Draw Bone Structure (Visual debug lines)
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

            # Highlight pivot if selected and in PIVOT mode
            if mode == "PIVOT":
                pygame.draw.line(surface, PIVOT_COLOR, (wx-10, wy), (wx+10, wy), 2)
                pygame.draw.line(surface, PIVOT_COLOR, (wx, wy-10), (wx, wy+10), 2)
                

class Keyframe:
    def __init__(self, time, bone_name, state, easing_type=EASING_DEFAULT):
        self.time = time
        self.bone_name = bone_name
        self.state = state # {x, y, rot, sx, sy}
        self.easing_type = easing_type # Easing function to use from this keyframe to the next

class Animation:
    def __init__(self):
        self.keyframes = [] # List of per-bone keyframes, sorted by time
        self.duration = 2.0 # Seconds
        self.loop = True

    def add_keyframe(self, time, bone, easing_type=EASING_DEFAULT):
        """Add a keyframe for a specific bone"""
        state = {
            'x': bone.x, 'y': bone.y, 'rot': bone.rotation,
            'size_x': bone.size_x, 'size_y': bone.size_y,
            'alpha': bone.alpha
        }
        
        # Remove existing keyframe for this bone at same time (approx)
        self.keyframes = [k for k in self.keyframes if not (k.bone_name == bone.name and abs(k.time - time) < 0.01)]
        self.keyframes.append(Keyframe(time, bone.name, state, easing_type))
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
                next_k = bone_kfs[0] # Initialize to first keyframe

                # Find the actual prev_k and next_k
                found_next = False
                for i, k in enumerate(bone_kfs):
                    if k.time <= time:
                        prev_k = k
                    if k.time > time:
                        next_k = k
                        found_next = True
                        break
                
                # If time is past the last keyframe, handle looping
                if not found_next:
                    if self.loop:
                        if len(bone_kfs) > 1: # Only loop if there's more than one keyframe
                            # Find the first keyframe for next_k
                            next_k = bone_kfs[0]
                            # Adjust prev_k to be the last keyframe, and total duration as segment length
                            prev_k = bone_kfs[-1]
                            segment_duration = self.duration - prev_k.time + next_k.time # Duration from last to first
                            t_in_segment = (time - prev_k.time) if time >= prev_k.time else (self.duration - prev_k.time + time)
                            t_normalized = t_in_segment / segment_duration if segment_duration > 0 else 0
                        else: # Only one keyframe, clamp to it.
                            t_normalized = 0.0
                            prev_k = bone_kfs[0]
                            next_k = bone_kfs[0]
                    else:
                        # Clamp to last keyframe
                        t_normalized = 1.0
                        prev_k = bone_kfs[-1]
                        next_k = bone_kfs[-1]
                else: # Time is between prev_k and next_k
                    segment_duration = next_k.time - prev_k.time
                    t_normalized = (time - prev_k.time) / segment_duration if segment_duration > 0 else 0


                # Apply easing function
                easer_func = easing.EASING_FUNCTIONS.get(prev_k.easing_type, easing.linear) # Easing applies FROM prev_k TO next_k
                eased_t = easer_func(t_normalized)
                
                p = prev_k.state
                n = next_k.state
                
                bone.x = p['x'] + (n['x'] - p['x']) * eased_t
                bone.y = p['y'] + (n['y'] - p['y']) * eased_t
                
                # Shortest angle interpolation
                diff = n['rot'] - p['rot']
                while diff < -180: diff += 360
                while diff > 180: diff -= 360
                bone.rotation = p['rot'] + diff * eased_t
                
                # Handle size (with backward compatibility for old 'sx', 'sy' keys)
                p_size_x = p.get('size_x', p.get('sx', 1.0))
                p_size_y = p.get('size_y', p.get('sy', 1.0))
                n_size_x = n.get('size_x', n.get('sx', 1.0))
                n_size_y = n.get('size_y', n.get('sy', 1.0))
                bone.size_x = p_size_x + (n_size_x - p_size_x) * eased_t
                bone.size_y = p_size_y + (n_size_y - p_size_y) * eased_t
                
                # Handle alpha (backward compatibility: if missing, default to 255)
                p_alpha = p.get('alpha', 255.0)
                n_alpha = n.get('alpha', 255.0)
                bone.alpha = p_alpha + (n_alpha - p_alpha) * eased_t
            
            for child in bone.children:
                apply_bone(child)
                
        apply_bone(root_bone)

# Helper Functions
def get_bone_at_pos(bone, mx, my, camera_pan, camera_zoom):
    # Transform mouse to world space
    # Screen = (World + Pan) * Zoom
    # World = (Screen / Zoom) - Pan
    
    # But wait, our render logic is:
    # Bone World Pos is calculated from root.
    # Root is temporarily offset by pan and scaled by zoom during render.
    # So actual bone world pos (wx, wy) returned by get_world_transform() IS the screen position if we apply the same temporary mods to root.
    
    # To avoid modifying root permanently or passing zoom everywhere, let's do hit test in "Screen Space".
    # We need the bone's screen position.
    
    # Let's use a recursive search that replicates the render transform logic?
    # Or simpler: Inverse transform the mouse into the "un-zoomed, un-panned" root local space?
    # That's hard because of hierarchy.
    
    # Alternative: The Bone.get_world_transform() returns values relative to the ROOT's parent (World Origin).
    # In main, root_bone.x/y are 0,0.
    # Camera pan is added to root_bone.x/y during render.
    
    # Let's calculate the bone's position as if it were rendered, then check distance.
    
    # We can pass the modified root transform down?
    
    # Let's stick to the previous simple method but account for the camera view transform.
    # The mouse (mx, my) is on screen.
    # The bone (bx, by) is in world space.
    # ScreenPos = (BoneWorldPos + CameraPan) * CameraZoom ? No, pan is usually translation, then zoom is scale.
    # Usually: Screen = (World - Camera) * Zoom + Center.
    # Our implementation: root_bone.x += camera_pan.
    
    # Let's look at render_scene implementation below.
    pass

def get_bone_at_pos_recursive(bone, target_pos, threshold=10):
    wx, wy, _, _, _ = bone.get_world_transform()
    dist = math.hypot(wx - target_pos[0], wy - target_pos[1])
    if dist < threshold:
        return bone
    for child in bone.children:
        found = get_bone_at_pos_recursive(child, target_pos, threshold)
        if found: return found
    return None

def get_bone_at_pos(root_bone, mx, my, camera_pan, camera_zoom):
    # Inverse Camera Transform: Calculate Mouse position in World Space
    # Screen = (World + Pan) * Zoom
    # World = (Screen / Zoom) - Pan
    
    world_mx = (mx / camera_zoom) - camera_pan[0]
    world_my = (my / camera_zoom) - camera_pan[1]
    
    # Threshold in World Space
    # Screen Threshold = 15 px
    # World Threshold = 15 / Zoom
    world_threshold = 15 / camera_zoom
    
    return get_bone_at_pos_recursive(root_bone, (world_mx, world_my), world_threshold)

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
        kx = TIMELINE_LEFT_MARGIN + (k.time / duration) * (SCREEN_WIDTH - TIMELINE_LEFT_MARGIN)
        
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
