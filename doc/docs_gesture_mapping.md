# GestureGlide - Gesture Mapping Reference

## Standard Gesture Mappings

### Click Operations

| Gesture | Fingers | Threshold (cm) | Debounce (ms) | Action |
|---------|---------|---|---|---|
| **Left Click** | Index + Middle | 2.0-3.0 | 100 | Single click |
| **Right Click** | Middle + Ring | 2.0-3.0 | 100 | Context menu |
| **Middle Click** | Index + Middle + Ring | 2.5-3.5 | 100 | Open in new tab |

### Movement Operations

| Gesture | Fingers | Threshold | Duration | Action |
|---------|---------|---|---|---|
| **Cursor Move** | Middle finger tip | N/A | Continuous | Track position |
| **Drag & Drop** | Thumb + Index | 2.0-3.0 | >200ms hold | Drag objects |

### Scroll Operations

| Gesture | Fingers | Motion | Action |
|---------|---------|--------|--------|
| **Scroll Down** | Index + Middle | Downward swipe | Scroll page down |
| **Scroll Up** | Index + Middle | Upward swipe | Scroll page up |
| **Scroll Left** | Index + Middle | Leftward swipe | Scroll left |
| **Scroll Right** | Index + Middle | Rightward swipe | Scroll right |

### Zoom Operations

| Gesture | Fingers | Motion | Threshold | Action |
|---------|---------|--------|---|---|
| **Zoom In** | Thumb + Index | Pinch outward | >1.5cm increase | Zoom in |
| **Zoom Out** | Thumb + Index | Pinch inward | >1.5cm decrease | Zoom out |

## Configuration Examples

### Sensitive for Small Hands
```yaml
gesture_detection:
  pinch_threshold_min: 1.5
  pinch_threshold_max: 2.5
  click_debounce_ms: 100
```

### Loose for Large Hands
```yaml
gesture_detection:
  pinch_threshold_min: 2.5
  pinch_threshold_max: 3.5
  click_debounce_ms: 100
```

### Conservative (Few False Positives)
```yaml
gesture_detection:
  pinch_threshold_min: 2.2
  pinch_threshold_max: 2.8
  click_debounce_ms: 150
```

### Aggressive (Responsive)
```yaml
gesture_detection:
  pinch_threshold_min: 1.8
  pinch_threshold_max: 3.0
  click_debounce_ms: 80
```

## Custom Gesture Mapping

To create custom gesture mappings:

1. Define gesture in `gesture_detector.py`
2. Add detection logic using landmark distances
3. Map to action in `mouse_actions.py`
4. Test with `scripts/test_gestures.py`

Example:
```python
# In gesture_detector.py
def detect_pinky_thumb_pinch(self, landmarks):
    """Detect pinky-thumb pinch"""
    dist = self.distance(landmarks[4], landmarks[20])
    if dist < self.threshold:
        return "PINKY_THUMB_PINCH"
    return None

# In mouse_actions.py
def handle_pinky_thumb_pinch(self):
    """Custom action for pinky-thumb pinch"""
    pyautogui.hotkey('alt', 'tab')  # Switch windows
```

## Advanced Gesture Combinations

For complex gesture combinations:

1. Use multi-step state machine
2. Track gesture sequence timing
3. Define combination patterns
4. Set hold/release thresholds

See `docs/UPGRADE.md` for implementation details.

## Troubleshooting Gesture Recognition

**Gesture not detected:**
- Lower threshold values
- Increase debounce time
- Run calibration

**False positives:**
- Raise threshold values
- Decrease debounce time
- Improve lighting

**Inconsistent detection:**
- Check hand visibility
- Verify lighting conditions
- Calibrate for your hand size
