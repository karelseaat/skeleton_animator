import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from serializers import load_scene_from_toml
from engine import Bone

class TestVisualVerification(unittest.TestCase):
    
    @patch('pygame.image.load')
    def test_character_animation_transforms(self, mock_load):
        # Mock image to return a 100x100 surface
        # This matches the default base_width/height I set in engine.py for non-image bones,
        # but here we are simulating images loading successfully.
        mock_surface = MagicMock()
        mock_surface.get_width.return_value = 100
        mock_surface.get_height.return_value = 100
        mock_surface.convert_alpha.return_value = mock_surface
        mock_load.return_value = mock_surface
        
        filepath = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "animations", "character_animation.toml")
        
        if not os.path.exists(filepath):
            self.skipTest(f"Animation file not found: {filepath}")
            
        print(f"\nTesting file: {filepath}")
        root, anim = load_scene_from_toml(filepath)
        
        # 1. Verify Root (Body)
        # In TOML: size_x = 60.0
        # Mock Image: width = 100
        # Expected Scale = 60 / 100 = 0.6
        wx, wy, rot, sx, sy = root.get_world_transform()
        
        print(f"Root ('{root.name}'): Pos=({wx},{wy}), Scale=({sx},{sy})")
        
        self.assertAlmostEqual(sx, 0.6, delta=0.01, msg="Root scale should be ~0.6 (60/100)")
        
        # 2. Verify Child (LeftArm)
        # In TOML: x = -40.0, y = 30.0
        # Parent Scale X is 0.6, Scale Y is 1.2
        # Expected World X = 0 + (-40 * 0.6) = -24.0
        # Expected World Y = 0 + (30 * 1.2) = 36.0
        
        left_arm = next((b for b in root.children if b.name == "LeftArm"), None)
        self.assertIsNotNone(left_arm)
        
        lax, lay, larot, lasx, lasy = left_arm.get_world_transform()
        print(f"Child ('{left_arm.name}'): WorldPos=({lax},{lay})")
        
        self.assertAlmostEqual(lax, -24.0, delta=1.0, msg="LeftArm X should be scaled by parent")
        self.assertAlmostEqual(lay, 36.0, delta=1.0, msg="LeftArm Y should be scaled by parent")
        
        # If the bug was present (overlapping), lax would be ~0 (-40 * 0.01 = -0.4)
        if abs(lax) < 1.0:
            print("!!! DETECTED COLLAPSED GEOMETRY (Overlapping bug) !!!")
        else:
            print("Geometry appears spread out correctly.")

if __name__ == '__main__':
    unittest.main()
