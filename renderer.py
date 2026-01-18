import pygame
from constants import *
from engine import get_flat_bone_list

# Map Intensity Suffix -> Color
EASING_INTENSITY_COLORS = {
    "linear": (200, 200, 200), # Gray
    "quad":   (255, 255, 0),   # Yellow
    "cubic":  (255, 150, 0),   # Orange
    "quart":  (255, 50, 50),   # Red
    "quint":  (200, 0, 255),   # Purple
}

class Renderer:
    def __init__(self, screen):
        # Initialized renderer
        self.screen = screen
        self.font = pygame.font.SysFont('Arial', 14)
        self.font_small = pygame.font.SysFont('Arial', 10)
        self.font_header = pygame.font.SysFont('Arial', 16, bold=True)
        self.font_title = pygame.font.SysFont('Arial', 24, bold=True)
        self.font_help = pygame.font.SysFont('Arial', 16)

    def draw_keyframe_marker(self, x, y, fill_color, easing_type):
        """
        Draws a keyframe marker.
        Shape = Direction (Linear=Circle, In=TriRight, Out=TriLeft, InOut=Diamond)
        Border Color = Intensity (Quad, Cubic, Quart, Quint)
        """
        size = 5 # Make it a bit smaller for border
        
        # 1. Determine Intensity Color
        border_color = EASING_INTENSITY_COLORS["linear"] # Default
        
        if "quint" in easing_type: border_color = EASING_INTENSITY_COLORS["quint"]
        elif "quart" in easing_type: border_color = EASING_INTENSITY_COLORS["quart"]
        elif "cubic" in easing_type: border_color = EASING_INTENSITY_COLORS["cubic"]
        elif "quad" in easing_type: border_color = EASING_INTENSITY_COLORS["quad"]
        
        # 2. Draw Shape based on Direction
        if easing_type == "linear":
            # Just a simple circle for linear, no extra border ring unless it's selected (handled elsewhere)
            pygame.draw.circle(self.screen, fill_color, (int(x), int(y)), size)
            # Only draw border if it's NOT the default gray (meaning it has some special intensity, though linear usually doesn't)
            if border_color != EASING_INTENSITY_COLORS["linear"]:
                 pygame.draw.circle(self.screen, border_color, (int(x), int(y)), size + 2, 2)
            
        elif easing_type.startswith("in_out_"):
            # Diamond
            points = [
                (x, y - size - 1),
                (x + size + 1, y),
                (x, y + size + 1),
                (x - size - 1, y)
            ]
            pygame.draw.polygon(self.screen, fill_color, points)
            pygame.draw.polygon(self.screen, border_color, points, 2)
            
        elif easing_type.startswith("in_"):
            # Triangle pointing Right >
            points = [
                (x - size + 1, y - size - 1),
                (x + size + 1, y),
                (x - size + 1, y + size + 1)
            ]
            pygame.draw.polygon(self.screen, fill_color, points)
            pygame.draw.polygon(self.screen, border_color, points, 2)
            
        elif easing_type.startswith("out_"):
            # Triangle pointing Left <
            points = [
                (x + size - 1, y - size - 1),
                (x - size - 1, y),
                (x + size - 1, y + size + 1)
            ]
            pygame.draw.polygon(self.screen, fill_color, points)
            pygame.draw.polygon(self.screen, border_color, points, 2)
        else: # Fallback to Circle
            pygame.draw.circle(self.screen, fill_color, (int(x), int(y)), size)
            pygame.draw.circle(self.screen, border_color, (int(x), int(y)), size + 2, 2) # Border is 2px wider

    def render_scene(self, root_bone, camera_pan, camera_zoom, selected_bone, mode, time_info=None, draw_bones=True, background_image=None):
        """
        Draws the entire scene to the provided surface.
        time_info: tuple (current_time, duration) for drawing timeline
        """
        main_surface = self.screen.subsurface((0, 0, SCREEN_WIDTH, SCREEN_HEIGHT))
        main_surface.fill(BG_COLOR)
        
        # Draw Reference Background (World Space)
        if background_image:
            # Calculate screen position for background (0,0 world)
            bg_x = camera_pan[0] * camera_zoom
            bg_y = camera_pan[1] * camera_zoom
            
            orig_w = background_image.get_width()
            orig_h = background_image.get_height()
            new_w = int(orig_w * camera_zoom)
            new_h = int(orig_h * camera_zoom)
            
            # Only draw if reasonable size
            if new_w > 0 and new_h > 0:
                scaled_bg = pygame.transform.scale(background_image, (new_w, new_h))
                main_surface.blit(scaled_bg, (bg_x, bg_y))
        
        # Grid
        grid_sz = int(50 * camera_zoom)
        if grid_sz < 10: grid_sz = 10 # Prevent infinite loop or dense grid
        
        # Grid Offset needs to scale too
        off_x = (camera_pan[0] * camera_zoom) % grid_sz
        off_y = (camera_pan[1] * camera_zoom) % grid_sz
        
        w, h = main_surface.get_size()
        
        for i in range(0, w, grid_sz):
            pygame.draw.line(main_surface, GRID_COLOR, (i + off_x - grid_sz, 0), (i + off_x - grid_sz, h - TIMELINE_HEIGHT))
        for i in range(0, h - TIMELINE_HEIGHT, grid_sz):
            pygame.draw.line(main_surface, GRID_COLOR, (0, i + off_y - grid_sz), (w, i + off_y - grid_sz))

        # HACK: Temporarily modify root pos for drawing to apply Camera Transform
        orig_x, orig_y = root_bone.x, root_bone.y
        orig_size_x, orig_size_y = root_bone.size_x, root_bone.size_y
        
        # Apply Pan and Zoom
        root_bone.x = (root_bone.x + camera_pan[0]) * camera_zoom
        root_bone.y = (root_bone.y + camera_pan[1]) * camera_zoom
        # NOTE: We now multiply size by zoom, which effectively scales the entire hierarchy
        # because get_world_transform converts size -> scale factor.
        root_bone.size_x *= camera_zoom
        root_bone.size_y *= camera_zoom
        
        
        # First Pass: Draw all images sorted by z_index
        flat_bones = get_flat_bone_list(root_bone)
        # Sort bones by z_index (ascending)
        flat_bones.sort(key=lambda b: b.z_index)
        
        for bone in flat_bones:
            bone.draw_image(main_surface)

        # Second Pass: Draw all debug elements (bone lines, nodes, pivots) on top
        if draw_bones:
            def recursive_draw_debug(bone):
                bone.draw_debug_elements(main_surface, selected_bone=selected_bone, mode=mode)
                for child in bone.children:
                    recursive_draw_debug(child)
            recursive_draw_debug(root_bone)
        
        # Restore root
        root_bone.x = orig_x
        root_bone.y = orig_y
        root_bone.size_x = orig_size_x
        root_bone.size_y = orig_size_y
        
        # UI Overlay (Timeline Background & Ticks)
        if time_info:
            curr, dur = time_info
            pygame.draw.rect(main_surface, TIMELINE_BG, (0, h - TIMELINE_HEIGHT, w, TIMELINE_HEIGHT))
            
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
                    # Account for left margin
                    x = TIMELINE_LEFT_MARGIN + (time_marker / dur) * (w - TIMELINE_LEFT_MARGIN)
                    
                    # Major tick (full height)
                    pygame.draw.line(main_surface, (100, 100, 100), (x, h - TIMELINE_HEIGHT), (x, h - TIMELINE_HEIGHT + 15), 1)
                    
                    # Time label for major ticks
                    if time_marker % 1.0 < 0.01 or time_marker % 1.0 > 0.99:  # Every 1 second
                        time_text = self.font_small.render(f'{time_marker:.1f}s', True, (150, 150, 150))
                        main_surface.blit(time_text, (int(x) - 10, h - TIMELINE_HEIGHT + 16))
                    
                    time_marker += time_interval
            
            # Playhead
            if dur > 0:
                ph_x = TIMELINE_LEFT_MARGIN + (curr / dur) * (w - TIMELINE_LEFT_MARGIN)
                pygame.draw.line(main_surface, (255, 0, 0), (ph_x, h - TIMELINE_HEIGHT), (ph_x, h), 2)
