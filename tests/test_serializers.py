import unittest
from unittest.mock import patch, MagicMock
import sys
import os
import tempfile

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from serializers import load_scene_from_toml, save_scene_to_toml
from engine import Bone

class TestSerializers(unittest.TestCase):
    
    @patch('pygame.image.load')
    def test_load_scene(self, mock_load):
        # Mock image load to return a surface with get_width/height
        mock_surface = MagicMock()
        mock_surface.get_width.return_value = 100
        mock_surface.get_height.return_value = 100
        mock_surface.convert_alpha.return_value = mock_surface
        mock_load.return_value = mock_surface
        
        # Create a temp TOML file
        toml_content = """
[[bones]]
name = "Body"
x = 0.0
y = 0.0
rotation = 0.0
size_x = 100.0
size_y = 100.0
pivot_x = 0.0
pivot_y = 0.0
alpha = 255.0
color = [ 255, 100, 100,]
image = "assets/torso.png"

[[bones]]
name = "Head"
x = 0.0
y = -50.0
rotation = 0.0
size_x = 50.0
size_y = 50.0
parent = "Body"

[meta]
duration = 5.0
loop = true
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as tmp:
            tmp.write(toml_content)
            tmp_path = tmp.name
            
        try:
            root, anim = load_scene_from_toml(tmp_path)
            
            # Verify Root
            self.assertEqual(root.name, "Body")
            self.assertEqual(root.x, 0.0)
            self.assertEqual(root.size_x, 100.0)
            
            # Verify Child
            self.assertEqual(len(root.children), 1)
            child = root.children[0]
            self.assertEqual(child.name, "Head")
            self.assertEqual(child.parent, root)
            self.assertEqual(child.y, -50.0)
            
            # Verify Meta
            self.assertEqual(anim.duration, 5.0)
            self.assertTrue(anim.loop)
            
        finally:
            os.remove(tmp_path)

if __name__ == '__main__':
    unittest.main()
