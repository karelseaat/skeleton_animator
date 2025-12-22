import pygame
import sys
import math
from tkinter import filedialog, Tk

# Local Modules
from constants import *
from engine import Bone, Animation, render_scene, get_bone_at_pos, get_keyframe_at_pos, get_flat_bone_list, Keyframe
from serializers import (
    load_scene_from_toml, 
    save_scene_to_toml, 
    save_scene_to_json, 
    save_scene_to_godot, 
    save_scene_to_spine_json, 
    save_scene_to_standalone_python
)
from exporters import (
    export_gif_with_camera,
    export_video,
    export_sprite_sheet
)
from easing import EASING_NAMES
from history import HistoryManager, TransformBoneCommand, AddOrReplaceKeyframeCommand, DeleteKeyframeCommand, ChangeEasingCommand

# Initialize Tkinter for file dialogs (hide the main window)
root_tk = Tk()
root_tk.withdraw()

# Map Intensity Suffix -> Color
EASING_INTENSITY_COLORS = {
    "linear": (200, 200, 200), # Gray
    "quad":   (255, 255, 0),   # Yellow
    "cubic":  (255, 150, 0),   # Orange
    "quart":  (255, 50, 50),   # Red
    "quint":  (200, 0, 255),   # Purple
}

def draw_keyframe_marker(surface, x, y, fill_color, easing_type):
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
        pygame.draw.circle(surface, fill_color, (int(x), int(y)), size)
        pygame.draw.circle(surface, border_color, (int(x), int(y)), size + 2, 2) # Border is 2px wider
        
    elif easing_type.startswith("in_out_"):
        # Diamond
        points = [
            (x, y - size - 1),
            (x + size + 1, y),
            (x, y + size + 1),
            (x - size - 1, y)
        ]
        pygame.draw.polygon(surface, fill_color, points)
        pygame.draw.polygon(surface, border_color, points, 2)
        
    elif easing_type.startswith("in_"):
        # Triangle pointing Right >
        points = [
            (x - size + 1, y - size - 1),
            (x + size + 1, y),
            (x - size + 1, y + size + 1)
        ]
        pygame.draw.polygon(surface, fill_color, points)
        pygame.draw.polygon(surface, border_color, points, 2)
        
    elif easing_type.startswith("out_"):
        # Triangle pointing Left <
        points = [
            (x + size - 1, y - size - 1),
            (x - size - 1, y),
            (x + size - 1, y + size + 1)
        ]
        pygame.draw.polygon(surface, fill_color, points)
        pygame.draw.polygon(surface, border_color, points, 2)
    else: # Fallback to Circle
        pygame.draw.circle(surface, fill_color, (int(x), int(y)), size)
        pygame.draw.circle(surface, border_color, (int(x), int(y)), size + 2, 2) # Border is 2px wider

def get_bone_state(bone):
    return {
        'x': bone.x, 'y': bone.y,
        'rotation': bone.rotation,
        'size_x': bone.size_x, 'size_y': bone.size_y,
        'pivot_x': bone.pivot_x, 'pivot_y': bone.pivot_y,
        'z_index': bone.z_index
    }

def main():
    pygame.init()
    # Adjust screen width for the properties panel
    screen = pygame.display.set_mode((SCREEN_WIDTH + PROPERTIES_PANEL_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Skeleton Animator")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont('Arial', 14)
    font_header = pygame.font.SysFont('Arial', 16, bold=True)
    font_small = pygame.font.SysFont('Arial', 10)
    font_title = pygame.font.SysFont('Arial', 24, bold=True)
    font_help = pygame.font.SysFont('Arial', 16) # Smaller help font

    # State
    camera_pan = [SCREEN_WIDTH//2, SCREEN_HEIGHT//2]
    camera_zoom = 1.0
    
    root_bone = Bone("Root")
    root_bone.x = 0
    root_bone.y = 0
    
    selected_bone = root_bone
    
    # Background Image State
    bg_image = None
    
    # Modes: SELECT, MOVE, ROTATE, PIVOT, SCALE
    mode = "SELECT" 
    show_bones = True
    show_help = False # Help overlay state
    
    animation = Animation()
    current_time = 0.0
    is_playing = False
    
    history = HistoryManager()
    
    running = True
    dragging = False
    dragging_keyframe = None
    selected_keyframe = None
    last_mouse_pos = (0, 0)
    drag_start_bone_state = None
    
    # Property Editing State
    # Index maps to properties in editable_props list
    focused_prop_idx = 0 
    editable_props = ["x", "y", "rotation", "size_x", "size_y", "pivot_x", "pivot_y", "z_index"]
    
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
                    if show_help:
                        show_help = False
                    else:
                        running = False
                
                elif event.key == pygame.K_h: # Toggle Help
                    show_help = not show_help

                # Undo / Redo
                elif event.key == pygame.K_z and (pygame.key.get_mods() & pygame.KMOD_CTRL):
                    if pygame.key.get_mods() & pygame.KMOD_SHIFT: # Ctrl+Shift+Z for Redo
                        history.redo()
                    else: # Ctrl+Z for Undo
                        history.undo()
                    # Apply animation state after undo/redo
                    animation.apply(current_time, root_bone)
                elif event.key == pygame.K_y and (pygame.key.get_mods() & pygame.KMOD_CTRL): # Ctrl+Y for Redo
                    history.redo()
                    animation.apply(current_time, root_bone)


                # Modes
                elif event.key == pygame.K_q: mode = "SELECT"
                elif event.key == pygame.K_w: mode = "MOVE"
                elif event.key == pygame.K_e: mode = "ROTATE"
                elif event.key == pygame.K_r: mode = "PIVOT"
                elif event.key == pygame.K_s: mode = "SCALE" # Scale Mode
                
                # View Options
                elif event.key == pygame.K_b: show_bones = not show_bones

                # Animation Duration
                elif event.key == pygame.K_COMMA: # < (Shift+,)
                    if animation.duration > 0.1: animation.duration -= 0.1
                elif event.key == pygame.K_PERIOD: # > (Shift+.)
                    animation.duration += 0.1

                # Actions
                elif event.key == pygame.K_l: 
                    if pygame.key.get_mods() & pygame.KMOD_SHIFT: # Shift+L: Load Background
                        filepath = filedialog.askopenfilename(filetypes=[("Images", "*.png;*.jpg;*.jpeg;*.bmp")])
                        if filepath:
                            try:
                                bg_image = pygame.image.load(filepath).convert_alpha()
                                print(f"Loaded background image: {filepath}")
                            except Exception as e:
                                print(f"Error loading background: {e}")
                    else: # L: Load Bone Image
                        filepath = filedialog.askopenfilename(filetypes=[("Images", "*.png;*.jpg;*.jpeg;*.bmp")])
                        if filepath:
                            new_bone = Bone(f"Bone_{bone_counter}", filepath, parent=selected_bone)
                            bone_counter += 1
                            selected_bone = new_bone
                            selected_bone.x = 50
                            # TODO: Add command for adding/deleting bones
                
                elif event.key == pygame.K_n: # New Empty Bone
                    new_bone = Bone(f"Bone_{bone_counter}", parent=selected_bone)
                    bone_counter += 1
                    selected_bone = new_bone
                    selected_bone.x = 50
                    # TODO: Add command for adding/deleting bones
                
                elif event.key == pygame.K_c: # Cycle Easing Type
                    if selected_keyframe:
                        old_easing = selected_keyframe.easing_type
                        current_idx = EASING_NAMES.index(old_easing)
                        next_idx = (current_idx + 1) % len(EASING_NAMES)
                        selected_keyframe.easing_type = EASING_NAMES[next_idx]
                        
                        history.push(ChangeEasingCommand(selected_keyframe, old_easing, selected_keyframe.easing_type))
                        print(f"Keyframe easing changed to: {selected_keyframe.easing_type}")
                
                # Property Panel Navigation
                elif event.key == pygame.K_TAB:
                    direction = -1 if (pygame.key.get_mods() & pygame.KMOD_SHIFT) else 1
                    focused_prop_idx = (focused_prop_idx + direction) % len(editable_props)
                
                # Property Modification (Arrows)
                elif event.key == pygame.K_UP or event.key == pygame.K_DOWN:
                    if selected_bone:
                        old_state = get_bone_state(selected_bone)
                        
                        prop_name = editable_props[focused_prop_idx]
                        delta = 1.0 if event.key == pygame.K_UP else -1.0
                        
                        if pygame.key.get_mods() & pygame.KMOD_SHIFT:
                            delta *= 10.0
                        
                        if prop_name in ["size_x", "size_y"]:
                            delta *= 0.1 # Slower for scale
                        elif prop_name == "z_index":
                            delta = 1 if event.key == pygame.K_UP else -1 # Integer steps
                        
                        curr_val = getattr(selected_bone, prop_name)
                        new_val = curr_val + delta
                        
                        if prop_name == "z_index":
                            setattr(selected_bone, prop_name, int(new_val))
                        else:
                            setattr(selected_bone, prop_name, new_val)
                            
                        new_state = get_bone_state(selected_bone)
                        # Push command only if something changed
                        if any(new_state[key] != old_state[key] for key in new_state):
                            history.push(TransformBoneCommand(selected_bone, old_state, new_state))

                elif event.key == pygame.K_LEFTBRACKET: # [
                    if selected_bone:
                        old_state = get_bone_state(selected_bone)
                        selected_bone.z_index -= 1
                        new_state = get_bone_state(selected_bone)
                        history.push(TransformBoneCommand(selected_bone, old_state, new_state))
                elif event.key == pygame.K_RIGHTBRACKET: # ]
                    if selected_bone:
                        old_state = get_bone_state(selected_bone)
                        selected_bone.z_index += 1
                        new_state = get_bone_state(selected_bone)
                        history.push(TransformBoneCommand(selected_bone, old_state, new_state))

                elif event.key == pygame.K_DELETE or event.key == pygame.K_BACKSPACE:
                    if selected_keyframe:
                        history.push(DeleteKeyframeCommand(animation, selected_keyframe))
                        # The command's execute method handles removal
                        # For now, manually remove it and let command just store it.
                        animation.keyframes.remove(selected_keyframe)
                        selected_keyframe = None
                    elif selected_bone and selected_bone.parent:
                        # TODO: Add command for adding/deleting bones
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
                
                elif event.key == pygame.K_SPACE:
                    is_playing = not is_playing
                
                elif event.key == pygame.K_k:
                    if selected_bone:
                        kf_easing = selected_keyframe.easing_type if selected_keyframe else EASING_NAMES[0]
                        
                        state = {
                            'x': selected_bone.x, 'y': selected_bone.y, 'rot': selected_bone.rotation,
                            'sx': selected_bone.size_x, 'sy': selected_bone.size_y
                        }
                        new_kf = Keyframe(current_time, selected_bone.name, state, kf_easing)
                        
                        # Check for existing keyframe to be replaced
                        replaced_kf = None
                        for k in animation.keyframes:
                            if k.bone_name == selected_bone.name and abs(k.time - current_time) < 0.01:
                                replaced_kf = k
                                break
                        
                        command = AddOrReplaceKeyframeCommand(animation, new_kf, replaced_kf)
                        command.execute() # Execute the command which adds/replaces and sorts
                        history.push(command)
                        
                        selected_keyframe = new_kf # Select the newly added/replaced keyframe
                        print(f"Keyframe added/replaced for '{selected_bone.name}' at {current_time:.2f}s")
                
                # Save/Load keys...
                elif event.key == pygame.K_o: # Load TOML
                    filepath = filedialog.askopenfilename(filetypes=[("TOML Config", "*.toml")])
                    if filepath:
                        new_root, new_anim = load_scene_from_toml(filepath)
                        if new_root:
                            root_bone = new_root
                            animation = new_anim
                            selected_bone = root_bone
                            # Reset history on load
                            history = HistoryManager()
                            print(f"Loaded scene from {filepath}")

                elif event.key == pygame.K_s and (pygame.key.get_mods() & pygame.KMOD_CTRL):
                    filepath = filedialog.asksaveasfilename(defaultextension=".toml", filetypes=[("TOML Config", "*.toml")])
                    if filepath:
                        save_scene_to_toml(filepath, root_bone, animation)

                # Export Formats
                elif event.key == pygame.K_j:
                    filepath = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON File", "*.json")])
                    if filepath: save_scene_to_json(filepath, root_bone, animation)

                elif event.key == pygame.K_g:
                    filepath = filedialog.asksaveasfilename(defaultextension=".tscn", filetypes=[("Godot Scene", "*.tscn")])
                    if filepath: save_scene_to_godot(filepath, root_bone, animation)
                        
                elif event.key == pygame.K_u:
                    filepath = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("Spine JSON", "*.json")])
                    if filepath: save_scene_to_spine_json(filepath, root_bone, animation)

                elif event.key == pygame.K_p:
                    filepath = filedialog.asksaveasfilename(defaultextension=".py", filetypes=[("Python Script", "*.py")])
                    if filepath: save_scene_to_standalone_python(filepath, root_bone, animation)

                # Export Media
                elif event.key == pygame.K_x:
                    filepath = filedialog.asksaveasfilename(defaultextension=".gif", filetypes=[("GIF Image", "*.gif")])
                    if filepath: export_gif_with_camera(filepath, root_bone, animation, camera_pan)
                
                elif event.key == pygame.K_v:
                    filepath = filedialog.asksaveasfilename(defaultextension=".mp4", filetypes=[("MP4 Video", "*.mp4")])
                    if filepath: export_video(filepath, root_bone, animation, camera_pan)
                
                elif event.key == pygame.K_y:
                    filepath = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG Image", "*.png")])
                    if filepath: export_sprite_sheet(filepath, root_bone, animation, camera_pan)

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1: # Left Click
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
                        selected_keyframe = None
                        clicked = get_bone_at_pos(root_bone, mx, my, camera_pan, camera_zoom)
                        if clicked:
                            selected_bone = clicked
                            dragging = "BONE"
                            # Capture state for Undo on drag
                            drag_start_bone_state = get_bone_state(selected_bone)
                        else:
                            dragging = "CAMERA"
                            last_mouse_pos = (mx, my) # Reset for accurate delta
                elif event.button == 3: # Right Click
                    clicked_kf = get_keyframe_at_pos(animation, mx, my, animation.duration, root_bone)
                    if clicked_kf:
                        history.push(DeleteKeyframeCommand(animation, clicked_kf))
                        # For DeleteKeyframeCommand, its execute method will perform the actual removal.
                        # We just push the command and let it manage the state.
                        command = DeleteKeyframeCommand(animation, clicked_kf)
                        command.execute() # Remove it
                        history.push(command) # Push the executed command
                        selected_keyframe = None # Deselect deleted keyframe
                elif event.button == 4 or event.button == 5: # Mouse Wheel Zoom
                    zoom_factor = 1.1 if event.button == 4 else 1/1.1 # Scroll up (4) or down (5)
                    
                    old_zoom = camera_zoom
                    new_zoom = max(0.1, min(5.0, camera_zoom * zoom_factor))
                    
                    # Calculate new pan to keep world position under mouse
                    camera_pan[0] = camera_pan[0] + (mx / new_zoom) - (mx / old_zoom)
                    camera_pan[1] = camera_pan[1] + (my / new_zoom) - (my / old_zoom)
                    
                    camera_zoom = new_zoom

            elif event.type == pygame.MOUSEBUTTONUP:
                if dragging == "BONE" and selected_bone:
                    current_state = get_bone_state(selected_bone)
                    if drag_start_bone_state and current_state != drag_start_bone_state:
                        # Push Undo command for bone transform if state changed
                        history.push(TransformBoneCommand(selected_bone, drag_start_bone_state, current_state))
                
                dragging = False
                dragging_keyframe = None
                drag_start_bone_state = None

            elif event.type == pygame.MOUSEMOTION:
                dx = mx - last_mouse_pos[0]
                dy = my - last_mouse_pos[1]
                
                if dragging == "KEYFRAME" and dragging_keyframe and animation.duration > 0:
                    ratio = max(0, min(1, mx / SCREEN_WIDTH))
                    new_time = ratio * animation.duration
                    
                    # Store previous state for Undo/Redo if we move a keyframe
                    # This is tricky as moving keyframe is a continuous action
                    # For MVP, we won't make a command for every frame drag of KF
                    # But if we were to, it would be a "MoveKeyframeCommand"
                    
                    # For now, let's just update the time.
                    # Undo/Redo of keyframe movement is more complex and usually involves a single command for the full drag.
                    # Leaving it out for this step.
                    dragging_keyframe.time = new_time
                    animation.keyframes.sort(key=lambda k: k.time)
                
                elif dragging == "TIMELINE":
                    ratio = max(0, min(1, mx / SCREEN_WIDTH))
                    current_time = ratio * animation.duration
                    if not is_playing:
                        animation.apply(current_time, root_bone)
                
                elif dragging == "CAMERA":
                    camera_pan[0] += dx / camera_zoom
                    camera_pan[1] += dy / camera_zoom
                
                elif dragging == "BONE" and selected_bone:
                    if mode == "MOVE":
                        parent_rot = 0
                        if selected_bone.parent:
                            _, _, parent_rot, _, _ = selected_bone.parent.get_world_transform()
                        
                        world_dx = dx / camera_zoom
                        world_dy = dy / camera_zoom
                        
                        rad = math.radians(-parent_rot)
                        local_dx = world_dx * math.cos(rad) - world_dy * math.sin(rad)
                        local_dy = world_dx * math.sin(rad) + world_dy * math.cos(rad)
                        
                        selected_bone.x += local_dx
                        selected_bone.y += local_dy
                        
                    elif mode == "ROTATE":
                        selected_bone.rotation += dx  # Rotate sensitivity usually constant
                    
                    elif mode == "PIVOT":
                        selected_bone.pivot_x += dx / camera_zoom
                        selected_bone.pivot_y += dy / camera_zoom
                        
                    elif mode == "SCALE": # Dragging adjusts Scale
                        # Drag X -> Scale X, Drag Y -> Scale Y
                        # Scale Factor: Moving right/up increases, left/down decreases
                        sens = 0.01
                        selected_bone.size_x += dx * sens
                        selected_bone.size_y -= dy * sens # Y is inverted on screen

        last_mouse_pos = (mx, my)

        # --- Update ---
        if is_playing:
            current_time += dt
            if current_time > animation.duration:
                current_time = 0
            animation.apply(current_time, root_bone)

        # --- Drawing ---
        main_scene_surface = screen.subsurface((0, 0, SCREEN_WIDTH, SCREEN_HEIGHT))
        render_scene(main_scene_surface, root_bone, camera_pan, camera_zoom, selected_bone, mode, (current_time, animation.duration), show_bones, bg_image)
        
        # Draw Properties Panel
        panel_rect = pygame.Rect(SCREEN_WIDTH, 0, PROPERTIES_PANEL_WIDTH, SCREEN_HEIGHT)
        pygame.draw.rect(screen, (50, 50, 60), panel_rect)
        pygame.draw.rect(screen, (80, 80, 90), panel_rect, 2)

        panel_offset_x = SCREEN_WIDTH + 10
        panel_offset_y = 15
        line_height = 22

        # -- STATUS SECTION --
        status_header = font_header.render("STATUS", True, (180, 180, 255))
        screen.blit(status_header, (panel_offset_x, panel_offset_y))
        panel_offset_y += line_height + 5

        status_lines = [
            f"Mode: {mode}",
            f"Time: {current_time:.2f} / {animation.duration:.2f}s",
            f"Zoom: {camera_zoom:.1f}x",
            "Press H for Help"
        ]
        for line in status_lines:
            surf = font.render(line, True, TEXT_COLOR)
            screen.blit(surf, (panel_offset_x, panel_offset_y))
            panel_offset_y += line_height
        
        panel_offset_y += 10
        pygame.draw.line(screen, (80, 80, 90), (panel_offset_x, panel_offset_y), (SCREEN_WIDTH + PROPERTIES_PANEL_WIDTH - 10, panel_offset_y), 1)
        panel_offset_y += 15

        # -- SELECTION --
        sel_header = font_header.render("SELECTION (Tab / Arrows)", True, (180, 180, 255))
        screen.blit(sel_header, (panel_offset_x, panel_offset_y))
        panel_offset_y += line_height + 5

        if selected_bone:
            selected_kfs = animation.get_keyframes_for_bone(selected_bone.name)
            current_easing = "N/A"
            if selected_keyframe:
                current_easing = selected_keyframe.easing_type

            prop_display_values = {
                "name": selected_bone.name,
                "x": selected_bone.x,
                "y": selected_bone.y,
                "rotation": selected_bone.rotation,
                "size_x": selected_bone.size_x,
                "size_y": selected_bone.size_y,
                "pivot_x": selected_bone.pivot_x,
                "pivot_y": selected_bone.pivot_y,
                "z_index": selected_bone.z_index,
            }

            prop_labels = {
                "x": "X", "y": "Y", "rotation": "Rot",
                "size_x": "Scale X", "size_y": "Scale Y",
                "pivot_x": "Pivot X", "pivot_y": "Pivot Y",
                "z_index": "Z-Index"
            }

            # Render Name separately
            name_surf = font.render(f"Name: {prop_display_values['name']}", True, TEXT_COLOR)
            screen.blit(name_surf, (panel_offset_x, panel_offset_y))
            panel_offset_y += line_height

            for i, prop_name in enumerate(editable_props):
                display_value = prop_display_values[prop_name]
                label = prop_labels[prop_name]
                
                format_str = ".1f"
                if "scale" in prop_name: format_str = ".2f"
                elif "z_index" == prop_name: format_str = "d"
                
                prop_line = f"{label}: {display_value:{format_str}}"
                
                color = TEXT_COLOR
                prefix = ""
                if i == focused_prop_idx: # Highlight focused property
                    color = SELECTED_COLOR
                    prefix = "> "
                
                surf = font.render(prefix + prop_line, True, color)
                screen.blit(surf, (panel_offset_x, panel_offset_y))
                panel_offset_y += line_height

            panel_offset_y += 10
            
            # Animation Info
            anim_header = font_header.render("ANIMATION", True, (180, 180, 255))
            screen.blit(anim_header, (panel_offset_x, panel_offset_y))
            panel_offset_y += line_height + 5
            
            anim_lines = [
                f"Keyframes: {len(selected_kfs)}",
                f"Easing: {current_easing} (C)"
            ]
            for line in anim_lines:
                surf = font.render(line, True, TEXT_COLOR)
                screen.blit(surf, (panel_offset_x, panel_offset_y))
                panel_offset_y += line_height

        else:
            no_selection_surf = font.render("No bone selected", True, (150, 150, 150))
            screen.blit(no_selection_surf, (panel_offset_x, panel_offset_y))
        
        # UI Overlay (Timeline) - RESTORED TIMELINE VISUALIZATION
        if animation.duration > 0:
            flat_bones = get_flat_bone_list(root_bone)
            bone_row_map = {b.name: i for i, b in enumerate(flat_bones)}
            
            row_height = 15
            base_ky = SCREEN_HEIGHT - TIMELINE_HEIGHT + 25
            
            # Draw track labels (Bone names) and colored bars
            for b in flat_bones:
                row_idx = bone_row_map[b.name]
                ky = base_ky + (row_idx * row_height)
                
                # Name
                name_surf = font_small.render(b.name, True, (100, 100, 100))
                screen.blit(name_surf, (5, ky - 5))
                
                # Draw bone-colored track bar
                track_rect = pygame.Rect(60, ky - row_height / 2 + 1, SCREEN_WIDTH - 60, row_height - 2)
                # Darker version of bone color for background
                dark_color = (max(0, b.color[0] - 100), max(0, b.color[1] - 100), max(0, b.color[2] - 100))
                pygame.draw.rect(screen, dark_color, track_rect, 0) 
                # Border in bone color
                pygame.draw.rect(screen, b.color, track_rect, 1)

            # Draw keyframes with track spacing and special markers
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
                
                fill_color = bone_obj.color if bone_obj else (100, 150, 255) # Fill with bone color
                
                # Draw marker based on easing type using the helper function
                draw_keyframe_marker(screen, kx, ky, fill_color, k.easing_type)
                
                # Draw selection box around selected keyframe
                if selected_keyframe == k:
                    pygame.draw.rect(screen, SELECTED_COLOR, (int(kx) - 12, int(ky) - 12, 24, 24), 2)

        # Help Overlay
        if show_help:
            full_w = SCREEN_WIDTH + PROPERTIES_PANEL_WIDTH
            overlay = pygame.Surface((full_w, SCREEN_HEIGHT))
            overlay.set_alpha(230) # Slightly darker
            overlay.fill((20, 20, 20))
            screen.blit(overlay, (0, 0))
            
            # Split Help into columns
            col1_x = 50
            col2_x = full_w // 2 + 20
            start_y = 50
            line_h = 25
            
            title_surf = font_title.render("HELP & CONTROLS", True, (255, 255, 255))
            screen.blit(title_surf, (full_w//2 - title_surf.get_width()//2, 20))
            
            col1_texts = [
                "GENERAL",
                "  H: Toggle This Help",
                "  Mouse Wheel: Zoom Camera",
                "  < / >: Adjust Animation Duration",
                "  Ctrl+Z: Undo",
                "  Ctrl+Y: Redo",
                "",
                "MODES",
                "  Q: Select Mode",
                "  W: Move Mode",
                "  E: Rotate Mode",
                "  R: Pivot Mode",
                "  S: Scale Mode",
                "",
                "BONE MANIPULATION",
                "  Mouse Drag: Move/Rotate/Pivot/Scale",
                "  [ / ]: Change Z-Index (Draw Order)",
                "  Shift+L: Load Background Reference",
                "  L: Load Image (Child)",
                "  N: New Empty Bone",
                "  Del: Delete Bone",
            ]
            
            col2_texts = [
                "PROPERTY PANEL",
                "  Tab: Cycle Focused Property",
                "  Up/Down: Adjust Value",
                "  Shift+Up/Down: Adjust Faster",
                "",
                "ANIMATION",
                "  Space: Play / Pause",
                "  K: Add Keyframe",
                "  C: Cycle Easing Type (for selected)",
                "  Timeline Drag: Scrub time",
                "  Right Click Keyframe: Delete",
                "",
                "SAVE / EXPORT",
                "  Ctrl+S: Quick Save",
                "  O: Open",
                "  J: Export JSON",
                "  G: Export Godot",
                "  U: Export Spine",
                "  P: Export Python Script",
                "  X: Export GIF",
                "  V: Export Video",
                "  Y: Export Sprite Sheet",
            ]
            
            # Draw Col 1
            curr_y = start_y
            for line in col1_texts:
                color = (200, 200, 255) if line.strip() and not line.startswith(" ") else (200, 200, 200)
                surf = font_help.render(line, True, color)
                screen.blit(surf, (col1_x, curr_y))
                curr_y += line_h
                
            # Draw Col 2
            curr_y = start_y
            for line in col2_texts:
                color = (200, 200, 255) if line.strip() and not line.startswith(" ") else (200, 200, 200)
                surf = font_help.render(line, True, color)
                screen.blit(surf, (col2_x, curr_y))
                curr_y += line_h

        pygame.display.flip()

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()