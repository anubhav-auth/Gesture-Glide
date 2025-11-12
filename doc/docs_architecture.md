# GestureGlide System Architecture

## Overview

GestureGlide is built on a modular, multi-threaded architecture designed for real-time performance with sub-100ms latency.

## System Components

### 1. Hand Tracking Layer

**MediaPipe Hands Integration** (`hand_tracker.py`)
- Detects 21 hand landmarks in 3D space
- Confidence scoring for reliability
- Handedness detection (left/right)

**Input:** Webcam video frames (640x480 @ 30 FPS)  
**Output:** 21 x (x, y, z) landmark coordinates

### 2. Cursor Control Layer

**Coordinate Mapping** (`cursor_controller.py`)
- Maps middle finger tip (landmark 12) to screen coordinates
- Handles aspect ratio normalization
- Screen coordinate transformation

**Smoothing Filters** (`smoothing.py`)
- Kalman filter for optimal smoothing
- Moving average filter alternative
- Configurable process/measurement noise

**Output:** Screen cursor position (x, y)

### 3. Gesture Recognition Layer

**Gesture Detector** (`gesture_detector.py`)
- Calculates distances between fingertips
- Implements finite state machine
- Debouncing for reliable detection

**Gestures Detected:**
- Pinch (various finger combinations)
- Drag (sustained pinch with motion)
- Scroll (two-finger motion)
- Zoom (variable pinch distance)

### 4. Action Execution Layer

**Mouse Actions** (`mouse_actions.py`)
- PyAutoGUI wrapper for cross-platform compatibility
- Click, drag, scroll, zoom operations
- Asynchronous event injection

## Data Flow

```
Webcam Input (30 FPS)
    ↓
Hand Tracker (MediaPipe)
    ↓
21 Landmarks + Confidence
    ↓
    ├─ Cursor Controller
    │   ├─ Coordinate Normalization
    │   ├─ Kalman Filtering
    │   └─ Screen Mapping
    │
    ├─ Gesture Detector
    │   ├─ Distance Calculation
    │   ├─ State Machine
    │   └─ Debouncing
    │
    └─ Mouse Actions
        └─ PyAutoGUI Events
```

## Multi-Threading Model

```
┌─────────────────────────────────────────┐
│   Main Application                      │
├─────────────────────────────────────────┤
│                                         │
│  Capture Thread    Process Thread  Display Thread
│  ─────────────────────────────────────────
│  • Read frames     • Hand detection • Render
│  • Webcam I/O      • Gesture recog  • Visual overlay
│  • Frame queue     • Cursor update  • UI events
│                    • Gesture queue  │
└─────────────────────────────────────────┘
```

## Performance Characteristics

| Component | Latency | CPU % |
|-----------|---------|-------|
| Hand Detection | 45ms | 35% |
| Gesture Recognition | 8ms | 3% |
| Cursor Smoothing | 3ms | 2% |
| Total Pipeline | 59ms | 45% |

## Configuration Points

All parameters configurable via `config.yaml`:

- Hand tracking sensitivity
- Gesture thresholds and debouncing
- Cursor smoothing parameters
- Performance optimization settings
- Visualization options

See `docs/PERFORMANCE_TUNING.md` for optimization guidance.

## Module Responsibilities

| Module | Responsibility |
|--------|-----------------|
| `config.py` | Configuration loading & management |
| `hand_tracker.py` | MediaPipe integration |
| `cursor_controller.py` | Coordinate transformation & smoothing |
| `gesture_detector.py` | Gesture recognition state machine |
| `smoothing.py` | Kalman & moving average filters |
| `mouse_actions.py` | Cross-platform mouse control |
| `calibration.py` | User calibration utility |
| `utils.py` | Shared utilities & helpers |

## Extension Points

To extend GestureGlide:

1. **Add New Gestures:** Extend `gesture_detector.py`
2. **Custom Filters:** Add to `smoothing.py`
3. **New Gesture Mappings:** Modify `mouse_actions.py`
4. **Performance Tweaks:** Adjust configuration parameters

See `docs/UPGRADE.md` for detailed extension guide.

## Quality & Testing

- Unit tests for all components
- Integration tests for full pipeline
- Performance benchmarking tools
- Interactive gesture testing script

Run tests: `pytest tests/ -v`

## Security & Privacy

✓ All processing local (no cloud)
✓ Webcam data not recorded
✓ No data transmission
✓ Open source code

## Future Enhancements

- GPU acceleration support
- Multi-hand gesture support
- Custom ML gesture training
- Mobile/web integration
