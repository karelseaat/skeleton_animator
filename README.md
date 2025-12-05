# Skeleton Animator

A simple Python-based 2D skeletal animation tool.

## Setup

1.  **Create a Virtual Environment**:
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

2.  **Install Dependencies**:
    ```bash
    pip install pygame-ce
    ```

3.  **Run the Tool**:
    ```bash
    python main.py
    ```

## Controls

*   **Mode Switching**:
    *   `Q`: **Select Mode** (Click to select bones)
    *   `W`: **Move Mode** (Drag to move bone relative to parent)
    *   `E`: **Rotate Mode** (Drag horizontally to rotate)
    *   `R`: **Pivot Mode** (Adjust pivot point)

*   **Editing**:
    *   `L`: Load an image (creates a child of the selected bone)
    *   `N`: Create a new empty bone (child of selected)
    *   `Delete` / `Backspace`: Delete selected bone (and its children)
    *   `Click`: Select a bone (or the background to move camera)

*   **Animation**:
    *   `Space`: Play / Pause animation
    *   `K`: Add Keyframe at current time
    *   `Timeline Click/Drag`: Scrub through time
