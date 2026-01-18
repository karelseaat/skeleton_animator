import sys
import os

# Asset Dimensions (width, height)
# head.png: 40x40
# robot_joint.png: 40x40
# limb.png: 20x70
# snake_body.png: 40x30
# spider_leg_upper.png: 10x60
# spider_leg_lower.png: 8x50
# robot_claw.png: 40x60
# robot_base.png: 80x40
# snake_tail.png: 40x30
# spider_body.png: 80x80
# torso.png: 50x100
# snake_head.png: 60x60
# robot_arm_segment.png: 30x120

# We will regenerate the TOML files using these dimensions as the default 'size'.
# Pivots will be set to reasonable defaults:
# - Limbs/Arms/Legs: Top-Center (pivot_y = -height/2 + margin)
# - Body/Head: Center (pivot_x=0, pivot_y=0)

ASSETS = {
    "assets/torso.png": (50, 100),
    "assets/limb.png": (20, 70),
    "assets/head.png": (40, 40),
    "assets/robot_joint.png": (40, 40),
    "assets/robot_claw.png": (40, 60),
    "assets/robot_base.png": (80, 40),
    "assets/robot_arm_segment.png": (30, 120),
    "assets/spider_body.png": (80, 80),
    "assets/spider_leg_upper.png": (10, 60),
    "assets/spider_leg_lower.png": (8, 50),
}

# Template for human_frontal
human_bones = [
    # Hips (Joint)
    {"name": "Hips", "image": "assets/robot_joint.png", "x": 0, "y": 100, "parent": None},
    # Body (Torso) - Pivot at bottom to rotate around hips? No, hips is parent. 
    # If Hips is at 100. Body is child.
    # Body pivot should be at Hips location.
    # Torso is 50x100. Center is 0,0. Bottom is +50.
    # So pivot_y should be +40 (near bottom).
    {"name": "Body", "image": "assets/torso.png", "x": 0, "y": -20, "parent": "Hips", "pivot_y": 40},
    
    # Head - Pivot at bottom (neck)
    {"name": "Head", "image": "assets/head.png", "x": 0, "y": -60, "parent": "Body", "pivot_y": 20},
    
    # Left Arm
    # Limb is 20x70. Top is -35.
    {"name": "UpperArm_L", "image": "assets/limb.png", "x": -35, "y": -40, "parent": "Body", "pivot_y": -30, "rot": 10},
    {"name": "LowerArm_L", "image": "assets/limb.png", "x": 0, "y": 60, "parent": "UpperArm_L", "pivot_y": -30, "rot": -5},
    
    # Right Arm
    {"name": "UpperArm_R", "image": "assets/limb.png", "x": 35, "y": -40, "parent": "Body", "pivot_y": -30, "rot": -10},
    {"name": "LowerArm_R", "image": "assets/limb.png", "x": 0, "y": 60, "parent": "UpperArm_R", "pivot_y": -30, "rot": 5},
    
    # Left Leg
    {"name": "UpperLeg_L", "image": "assets/limb.png", "x": -20, "y": 10, "parent": "Hips", "pivot_y": -30},
    {"name": "LowerLeg_L", "image": "assets/limb.png", "x": 0, "y": 60, "parent": "UpperLeg_L", "pivot_y": -30},
    {"name": "Foot_L", "image": "assets/robot_claw.png", "x": 0, "y": 60, "parent": "LowerLeg_L", "pivot_y": -25, "rot": 0},

    # Right Leg
    {"name": "UpperLeg_R", "image": "assets/limb.png", "x": 20, "y": 10, "parent": "Hips", "pivot_y": -30},
    {"name": "LowerLeg_R", "image": "assets/limb.png", "x": 0, "y": 60, "parent": "UpperLeg_R", "pivot_y": -30},
    {"name": "Foot_R", "image": "assets/robot_claw.png", "x": 0, "y": 60, "parent": "LowerLeg_R", "pivot_y": -25},
]

robotic_bones = [
    {"name": "Base", "image": "assets/robot_base.png", "x": 0, "y": 200, "parent": None},
    {"name": "Joint1", "image": "assets/robot_joint.png", "x": 0, "y": -20, "parent": "Base"},
    # Arm Segment 30x120. Pivot at bottom (+50)
    {"name": "Arm1", "image": "assets/robot_arm_segment.png", "x": 0, "y": 0, "parent": "Joint1", "pivot_y": 50, "rot": -45},
    {"name": "Joint2", "image": "assets/robot_joint.png", "x": 0, "y": -110, "parent": "Arm1"}, # Top of arm
    {"name": "Arm2", "image": "assets/robot_arm_segment.png", "x": 0, "y": 0, "parent": "Joint2", "pivot_y": 50, "rot": 90},
    {"name": "Claw", "image": "assets/robot_claw.png", "x": 0, "y": -110, "parent": "Arm2", "pivot_y": 30},
]

spider_bones = [
    {"name": "Body", "image": "assets/spider_body.png", "x": 0, "y": 0, "parent": None},
    # Legs (Upper 10x60, Lower 8x50). Pivot Upper at +30 (Body connection), Pivot Lower at +25
    {"name": "Leg_L1_Upper", "image": "assets/spider_leg_upper.png", "x": -30, "y": -20, "parent": "Body", "pivot_y": 25, "rot": -30},
    {"name": "Leg_L1_Lower", "image": "assets/spider_leg_lower.png", "x": 0, "y": -55, "parent": "Leg_L1_Upper", "pivot_y": 20, "rot": 45},
    
    {"name": "Leg_R1_Upper", "image": "assets/spider_leg_upper.png", "x": 30, "y": -20, "parent": "Body", "pivot_y": 25, "rot": 30},
    {"name": "Leg_R1_Lower", "image": "assets/spider_leg_lower.png", "x": 0, "y": -55, "parent": "Leg_R1_Upper", "pivot_y": 20, "rot": -45},
]

def generate_toml(filename, bones, duration=2.0):
    lines = []
    for b in bones:
        w, h = ASSETS.get(b['image'], (100, 100))
        lines.append("[[bones]]")
        lines.append(f'name = "{b["name"]}"')
        lines.append(f'x = {b["x"]}.0')
        lines.append(f'y = {b["y"]}.0')
        lines.append(f'rotation = {b.get("rot", 0)}.0')
        lines.append(f'size_x = {w}.0')
        lines.append(f'size_y = {h}.0')
        lines.append(f'pivot_x = {b.get("pivot_x", 0)}.0')
        lines.append(f'pivot_y = {b.get("pivot_y", 0)}.0')
        lines.append('alpha = 255.0')
        
        # Cycle colors based on index or hash
        colors = [
            [255, 100, 100], # Red
            [100, 255, 100], # Green
            [100, 100, 255], # Blue
            [255, 255, 100], # Yellow
            [255, 100, 255], # Magenta
            [100, 255, 255], # Cyan
            [255, 150, 50],  # Orange
            [150, 50, 255],  # Purple
        ]
        color = colors[abs(hash(b["name"])) % len(colors)]
        lines.append(f'color = {color}')
        
        if b['parent']:
            lines.append(f'parent = "{b["parent"]}"')
        lines.append(f'image = "{b["image"]}"')
        lines.append("")
        
    lines.append("[meta]")
    lines.append(f"duration = {duration}")
    lines.append("loop = true")
    lines.append("")
    lines.append("[animations]")
    
    # Generate one keyframe at time 0 to lock initial pose
    lines.append("[[animations.keyframes]]")
    lines.append("time = 0.0")
    for b in bones:
        lines.append(f'[animations.keyframes.bones.{b["name"]}]')
        lines.append(f'rot = {b.get("rot", 0)}.0')
        # We can add a simple movement keyframe later, but this fixes the static pose
        
    with open(f"animations/{filename}", "w") as f:
        f.write("\n".join(lines))
    print(f"Generated {filename}")

if __name__ == "__main__":
    generate_toml("human_frontal.toml", human_bones)
    generate_toml("robotic_arm.toml", robotic_bones)
    generate_toml("spider_walk.toml", spider_bones)
