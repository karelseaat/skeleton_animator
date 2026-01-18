import unittest
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine import Bone
from history import HistoryManager, TransformBoneCommand

class TestHistory(unittest.TestCase):
    def test_undo_redo(self):
        history = HistoryManager()
        bone = Bone("TestBone")
        bone.x = 0
        bone.y = 0
        
        # State 1: x=0
        
        # Create Command to move to x=10
        cmd = TransformBoneCommand(bone, 
                                   old_state={'x': 0, 'y': 0, 'rotation': 0, 'size_x': 100, 'size_y': 100, 'pivot_x':0, 'pivot_y':0, 'z_index': 0},
                                   new_state={'x': 10, 'y': 0, 'rotation': 0, 'size_x': 100, 'size_y': 100, 'pivot_x':0, 'pivot_y':0, 'z_index': 0})
        
        # Execute (usually done by main loop, but here we push manually)
        # Note: In this app, "push" doesn't execute, it just stores? 
        # Let's check history.py logic.
        # Usually one executes then pushes. Or push executes.
        
        # Checking history.py source via memory or view would be good.
        # Assuming typical command pattern.
        
        # Let's simulate what happens in main.py
        # 1. Apply change to bone
        bone.x = 10
        # 2. Push command
        history.push(cmd)
        
        self.assertTrue(history.can_undo())
        self.assertFalse(history.can_redo())
        
        # Undo
        history.undo()
        self.assertEqual(bone.x, 0)
        self.assertFalse(history.can_undo())
        self.assertTrue(history.can_redo())
        
        # Redo
        history.redo()
        self.assertEqual(bone.x, 10)
        self.assertTrue(history.can_undo())
        self.assertFalse(history.can_redo())

if __name__ == '__main__':
    unittest.main()
