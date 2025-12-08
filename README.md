# Skeleton Animator

A Python-based 2D skeletal animation tool with keyframe animation, easing functions, and multiple export formats.

## Features

*   **Hierarchical Skeleton**: Create parent-child relationships for bones.
*   **Keyframe Animation**: Animate position, rotation, and scale over time.
*   **Easing Functions**: smooth out animations with Linear, Quad, Cubic, Quart, and Quint easing types.
*   **Visual Timeline**: Color-coded bone tracks and shape-coded keyframes for easy reading.
*   **Interactive Properties Panel**: Fine-tune values numerically.
*   **Export Options**: Save as JSON, Godot (`.tscn`), Spine JSON, or a standalone Python script.
*   **Media Export**: Export animations as GIF, MP4 Video, or Sprite Sheets.

## Setup

1.  **Create a Virtual Environment**:
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

2.  **Install Dependencies**:
    ```bash
    pip install pygame-ce imageio imageio-ffmpeg numpy toml
    ```

3.  **Run the Tool**:
    ```bash
    python main.py
    ```

## Controls

### General
*   **`H`**: Toggle Help Overlay
*   **`Space`**: Play / Pause Animation
*   **`Mouse Wheel`**: Zoom Camera (centered on cursor)
*   **`Middle Click Drag`**: Pan Camera (or drag background)

### Modes
*   **`Q`**: **Select Mode** (Click to select bones)
*   **`W`**: **Move Mode** (Drag to move bone relative to parent)
*   **`E`**: **Rotate Mode** (Drag horizontally to rotate)
*   **`R`**: **Pivot Mode** (Adjust pivot point)

### Editing
*   **`L`**: Load an image (creates a child of the selected bone)
*   **`N`**: Create a new empty bone (child of selected)
*   **`Delete` / `Backspace`**: Delete selected bone (and its children)
*   **`[` / `]`**: Change Z-Index (Draw Order) of selected bone

### Animation
*   **`K`**: Add Keyframe at current time
*   **`C`**: Cycle Easing Type for the selected keyframe
*   **`<` / `>`** (`Shift+,` / `Shift+.`): Adjust Animation Duration (+/- 0.1s)
*   **`Click Keyframe`**: Select Keyframe (Yellow border)
*   **`Drag Keyframe`**: Move Keyframe in time
*   **`Right Click Keyframe`**: Delete Keyframe

### Properties Panel (Right Side)
*   **`Tab`**: Cycle focus through editable properties (X, Y, Rot, Scale, etc.)
*   **`Up` / `Down`**: Adjust the focused property value
*   **`Shift + Up/Down`**: Adjust value faster (10x)

### Save / Export
*   **`Ctrl + S`**: Quick Save (`.toml`)
*   **`O`**: Open (`.toml`)
*   **`J`**: Export JSON
*   **`G`**: Export Godot Scene (`.tscn`)
*   **`U`**: Export Spine JSON
*   **`P`**: Export Standalone Python Script
*   **`X`**: Export GIF
*   **`V`**: Export MP4 Video
*   **`Y`**: Export Sprite Sheet (`.png`)

## Visual Guide

*   **Keyframe Shapes**:
    *   **Circle**: Linear
    *   **Triangle Right**: Ease In
    *   **Triangle Left**: Ease Out
    *   **Diamond**: Ease In/Out
*   **Keyframe Colors**: Border color indicates intensity (Gray=Linear, Yellow=Quad, Orange=Cubic, Red=Quart, Purple=Quint).