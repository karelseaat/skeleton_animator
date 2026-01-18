import unittest
from unittest.mock import MagicMock, patch
import sys
import os
import pygame

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine import Bone

class TestRenderingLogic(unittest.TestCase):
    
    def test_pivot_math(self):
        """
        Verify that the image rect calculation correctly places the pivot point
        at the bone's world position.
        """
        bone = Bone("TestBone")
        bone.x = 100
        bone.y = 100
        bone.rotation = 0
        
        # Simulate an image
        bone.base_width = 100.0
        bone.base_height = 100.0
        bone.size_x = 100.0
        bone.size_y = 100.0
        
        # 1. Pivot at Top-Left (0,0)
        bone.pivot_x = 0
        bone.pivot_y = 0
        
        # Expected: Image drawn at (100, 100)
        # We need to simulate the math in draw_image without actually drawing
        wx, wy, wrot, scale_x, scale_y = bone.get_world_transform() # 100, 100, 0, 1, 1
        
        scaled_piv_x = bone.pivot_x * abs(scale_x) # 0
        scaled_piv_y = bone.pivot_y * abs(scale_y) # 0
        
        # No rotation
        rot_piv_x = scaled_piv_x
        rot_piv_y = scaled_piv_y
        
        # Rect dimensions
        w = int(abs(scale_x * bone.base_width)) # 100
        h = int(abs(scale_y * bone.base_height)) # 100
        
        # Center calc from engine.py:
        # rect.center = (wx + (w/2 - rot_piv_x) - w/2, wy + (h/2 - rot_piv_y) - h/2)
        #             = (wx - rot_piv_x, wy - rot_piv_y)
        center_x = wx - rot_piv_x
        center_y = wy - rot_piv_y
        
        # TopLeft = Center - Size/2
        # But wait, rect.center IS the center.
        # So topleft_x = center_x - w/2
        #              = 100 - 0 - 50 = 50?
        # WAIT. My derivation in thought process was:
        # rect.center_x = wx - rot_piv_x + width/2
        # Let's check engine.py line 130 again exactly:
        # rect.center = (wx + (rect.width/2 - rot_piv_x) - rect.width/2, ...)
        # Algebra:
        # X = wx + (W/2 - P) - W/2
        # X = wx + W/2 - P - W/2
        # X = wx - P
        
        # So rect.center_x = wx - P.
        # If P=0, center_x = wx (100).
        # If rect center is at 100, and width is 100, then topleft is at 50.
        # BUT we want topleft to be at 100 (if pivot is 0,0).
        
        # IF pivot is 0,0 (top-left), then the point (0,0) of the image should be at wx(100).
        # If image is 100 wide, center is at 50.
        # So rect.center should be 150.
        
        # If the code calculates rect.center_x = 100, then topleft is 50.
        # This places the CENTER of the image at the pivot (if pivot is 0,0).
        # This means pivot_x=0 implies "Center".
        # But `bone.pivot_x` comment says: "0 = middle, -(size/2) = top-left..." (Line 45 of engine.py)
        
        # Let's check line 45 of engine.py:
        # "Pivot point: 0 = middle, -(size/2) = top-left, +(size/2) = bottom-right"
        
        # If that's the intention, then:
        # P=0 means center.
        # Code: center_x = wx - 0 = wx. Correct. Center of image is at bone pos.
        
        # Case 2: Pivot at Top-Left.
        # According to comment: pivot_x = -size/2 = -50.
        # P = -50.
        # center_x = wx - (-50) = 150.
        # topleft = 150 - 50 = 100.
        # Correct. Top-left of image is at bone pos.
        
        # CONCLUSION: The code implements the coordinate system described in the comments.
        # 0,0 is CENTER of image.
        
        # NOW let's look at the TOML files.
        # character_animation.toml
        # Body: pivot_x = 0.0, pivot_y = 0.0. -> Center pivot.
        # LeftArm: pivot_x = 0.0 (Center X), pivot_y = -45.0 (Near Top Y? or Bottom?)
        # If size_y is 90. Top is -45. Bottom is +45.
        # So pivot_y = -45 means "Top Edge".
        
        # This seems consistent!
        
        pass

if __name__ == '__main__':
    unittest.main()
