import unittest
import sys
import os
import pygame

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine import Bone

class TestBone(unittest.TestCase):
    def test_bone_initialization(self):
        bone = Bone("TestBone")
        self.assertEqual(bone.name, "TestBone")
        self.assertEqual(bone.x, 0)
        self.assertEqual(bone.y, 0)
        self.assertEqual(bone.rotation, 0)
        
    def test_hierarchy_transforms(self):
        # Root
        root = Bone("Root")
        root.x = 100
        root.y = 100
        # Set base/size explicitly to avoid scale issues if defaults change
        root.base_width = 100
        root.base_height = 100
        root.size_x = 100
        root.size_y = 100
        
        # Child
        child = Bone("Child", parent=root)
        child.x = 50
        child.y = 0
        child.base_width = 100
        child.base_height = 100
        child.size_x = 100
        child.size_y = 100
        
        # Test Root Transform
        wx, wy, rot, sx, sy = root.get_world_transform()
        self.assertEqual(wx, 100)
        self.assertEqual(wy, 100)
        
        # Test Child Transform (should be relative to parent)
        cx, cy, crot, csx, csy = child.get_world_transform()
        self.assertEqual(cx, 150) # 100 + 50
        self.assertEqual(cy, 100) # 100 + 0
        
    def test_rotation_transform(self):
        root = Bone("Root")
        root.x = 0
        root.y = 0
        root.rotation = 90
        # Set base/size explicitly
        root.base_width = 100
        root.base_height = 100
        root.size_x = 100
        root.size_y = 100
        
        child = Bone("Child", parent=root)
        child.x = 10
        child.y = 0
        child.base_width = 100
        child.base_height = 100
        child.size_x = 100
        child.size_y = 100
        
        # With root rotated 90 degrees (clockwise in pygame usually? need to check math)
        # engine.py:
        # rad = math.radians(prot)
        # wx = px + (lx * cos_a - ly * sin_a)
        # wy = py + (lx * sin_a + ly * cos_a)
        # If prot=90, cos=0, sin=1.
        # wx = 0 + (10 * 0 - 0 * 1) = 0
        # wy = 0 + (10 * 1 + 0 * 0) = 10
        
        cx, cy, crot, csx, csy = child.get_world_transform()
        self.assertAlmostEqual(cx, 0, places=5)
        self.assertAlmostEqual(cy, 10, places=5)
        self.assertEqual(crot, 90)

if __name__ == '__main__':
    unittest.main()
