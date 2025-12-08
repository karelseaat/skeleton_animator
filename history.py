import copy

class Command:
    def execute(self):
        pass
    def undo(self):
        pass

class HistoryManager:
    def __init__(self):
        self.undo_stack = []
        self.redo_stack = []
        self.max_history = 50 # Limit history to prevent excessive memory use

    def push(self, command):
        self.undo_stack.append(command)
        self.redo_stack.clear() # New action clears redo history
        if len(self.undo_stack) > self.max_history:
            self.undo_stack.pop(0) # Remove oldest command
        print(f"Action pushed: {type(command).__name__}")

    def undo(self):
        if not self.undo_stack:
            print("Nothing to undo.")
            return
        command = self.undo_stack.pop()
        command.undo()
        self.redo_stack.append(command)
        print(f"Undid: {type(command).__name__}")

    def redo(self):
        if not self.redo_stack:
            print("Nothing to redo.")
            return
        command = self.redo_stack.pop()
        command.execute()
        self.undo_stack.append(command)
        print(f"Redid: {type(command).__name__}")

# --- Concrete Commands ---

class TransformBoneCommand(Command):
    """Handles Move, Rotate, Scale, Pivot, Z-index changes for a single bone"""
    def __init__(self, bone, old_state, new_state):
        self.bone = bone
        self.old_state = old_state # dict of {x, y, rot, sx, sy, px, py, z_index}
        self.new_state = new_state

    def execute(self):
        self._apply_state(self.new_state)

    def undo(self):
        self._apply_state(self.old_state)

    def _apply_state(self, state):
        self.bone.x = state['x']
        self.bone.y = state['y']
        self.bone.rotation = state['rotation']
        self.bone.scale_x = state['scale_x']
        self.bone.scale_y = state['scale_y']
        self.bone.pivot_x = state['pivot_x']
        self.bone.pivot_y = state['pivot_y']
        self.bone.z_index = state['z_index']

class AddOrReplaceKeyframeCommand(Command):
    """Adds a new keyframe, or replaces an existing one at the same time/bone"""
    def __init__(self, animation, new_keyframe, replaced_keyframe=None):
        self.animation = animation
        self.new_keyframe = new_keyframe
        self.replaced_keyframe = replaced_keyframe # The keyframe that was replaced, if any

    def execute(self):
        # Remove any existing keyframe for this bone at the new_keyframe's time
        self.animation.keyframes = [k for k in self.animation.keyframes 
                                    if not (k.bone_name == self.new_keyframe.bone_name and abs(k.time - self.new_keyframe.time) < 0.01)]
        self.animation.keyframes.append(self.new_keyframe)
        self.animation.keyframes.sort(key=lambda k: k.time)

    def undo(self):
        # Remove the new keyframe
        self.animation.keyframes = [k for k in self.animation.keyframes if k is not self.new_keyframe]
        # Restore the replaced keyframe if any
        if self.replaced_keyframe:
            self.animation.keyframes.append(self.replaced_keyframe)
            self.animation.keyframes.sort(key=lambda k: k.time)

class DeleteKeyframeCommand(Command):
    """Deletes a keyframe"""
    def __init__(self, animation, keyframe_to_delete):
        self.animation = animation
        self.keyframe_to_delete = keyframe_to_delete

    def execute(self):
        if self.keyframe_to_delete in self.animation.keyframes:
            self.animation.keyframes.remove(self.keyframe_to_delete)

    def undo(self):
        self.animation.keyframes.append(self.keyframe_to_delete)
        self.animation.keyframes.sort(key=lambda k: k.time)

class ChangeEasingCommand(Command):
    """Changes the easing type of a keyframe"""
    def __init__(self, keyframe, old_easing, new_easing):
        self.keyframe = keyframe
        self.old_easing = old_easing
        self.new_easing = new_easing

    def execute(self):
        self.keyframe.easing_type = self.new_easing

    def undo(self):
        self.keyframe.easing_type = self.old_easing