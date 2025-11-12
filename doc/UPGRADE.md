# GestureGlide Upgrade & Modification Guide

## Overview

GestureGlide is designed with modularity in mind, allowing you to extend, modify, and upgrade components easily. This guide covers adding features, modifying behavior, and upgrading to new versions.

## Modifying Existing Features

### 1. Adjusting Gesture Thresholds

**Simple Approach - Configuration Only:**

Edit `config.yaml` without code changes:
```yaml
gesture_detection:
  pinch_threshold_min: 1.8  # Adjust for different hand sizes
  pinch_threshold_max: 3.0
  click_debounce_ms: 100    # Debounce timing
```

### 2. Adding New Gesture Types

**Step 1: Define Gesture in Gesture Detector**

Edit `src/gesture_detector.py`:
```python
class GestureDetector:
    # Add new gesture state
    GESTURE_TYPES = {
        "LEFT_CLICK": 1,
        "RIGHT_CLICK": 2,
        "SWIPE_LEFT": 3,  # NEW GESTURE
        "SWIPE_RIGHT": 4, # NEW GESTURE
    }
    
    def detect_swipe_gesture(self, landmarks):
        """Detect horizontal swipe gestures"""
        # Calculate finger velocity from landmark deltas
        index_tip = landmarks[8]
        middle_tip = landmarks[12]
        
        # Track motion direction
        if index_tip[0] - middle_tip[0] > 50:  # Moving right
            return "SWIPE_RIGHT"
        elif middle_tip[0] - index_tip[0] > 50:  # Moving left
            return "SWIPE_LEFT"
        
        return None
```

**Step 2: Handle in Mouse Actions**

Edit `src/mouse_actions.py`:
```python
class MouseActions:
    def handle_gesture(self, gesture_type):
        """Handle gesture-specific actions"""
        if gesture_type == "SWIPE_LEFT":
            self.swipe_left()
        elif gesture_type == "SWIPE_RIGHT":
            self.swipe_right()
    
    def swipe_left(self):
        """Perform back/previous navigation"""
        # Send Alt+Left for browser back
        pyautogui.hotkey('alt', 'left')
    
    def swipe_right(self):
        """Perform forward/next navigation"""
        # Send Alt+Right for browser forward
        pyautogui.hotkey('alt', 'right')
```

**Step 3: Update Main Application**

Edit `src/main.py` to call new gesture handler:
```python
if gesture == "SWIPE_LEFT":
    self.mouse_actions.swipe_left()
elif gesture == "SWIPE_RIGHT":
    self.mouse_actions.swipe_right()
```

### 3. Changing Cursor Mapping

**Modify Screen Coordinate Mapping:**

Edit `src/cursor_controller.py`:
```python
def normalize_coordinates(self, landmarks):
    """Customize coordinate transformation"""
    
    # Get middle finger tip (landmark 12)
    middle_finger = landmarks[12]
    
    # Custom mapping: inverse Y-axis (upside-down display)
    x = middle_finger[0] * self.screen_width
    y = (1 - middle_finger[1]) * self.screen_height  # INVERTED
    
    return x, y
```

### 4. Adding Custom Filters

**Implement New Smoothing Filter:**

Edit `src/smoothing.py`:
```python
class ExponentialMovingAverage:
    """Exponential moving average filter"""
    
    def __init__(self, alpha=0.3):
        self.alpha = alpha
        self.last_value = None
    
    def filter(self, value):
        if self.last_value is None:
            self.last_value = value
            return value
        
        self.last_value = self.alpha * value + (1 - self.alpha) * self.last_value
        return self.last_value
```

**Use in Cursor Controller:**
```python
# In config.yaml
cursor_control:
  smoothing_filter: "exponential_moving_average"
  
# In cursor_controller.py
if self.config.cursor_control['smoothing_filter'] == 'exponential_moving_average':
    self.filter = ExponentialMovingAverage()
```

## Adding New Features

### 1. Multi-Hand Gestures

**Extend Hand Tracker:**

```python
# src/hand_tracker.py
def detect_dual_hands(self, frame):
    """Detect and return both hands"""
    results = self.hands.process(frame)
    
    if results.multi_hand_landmarks:
        return results.multi_hand_landmarks, results.handedness
    return None, None
```

**Add Dual-Hand Gesture Detection:**

```python
# src/gesture_detector.py
def detect_pinch_gesture_dual_hands(self, landmarks_left, landmarks_right):
    """Detect simultaneous pinch with both hands"""
    
    left_pinch = self.calculate_pinch_distance(
        landmarks_left[8], landmarks_left[12]
    )
    right_pinch = self.calculate_pinch_distance(
        landmarks_right[8], landmarks_right[12]
    )
    
    if left_pinch < 2.0 and right_pinch < 2.0:
        return "DUAL_HAND_PINCH"
    
    return None
```

### 2. Voice Feedback

**Add Audio Confirmation:**

```python
# src/audio_feedback.py
import pyttsx3

class AudioFeedback:
    def __init__(self):
        self.engine = pyttsx3.init()
    
    def gesture_confirmed(self, gesture_type):
        """Provide audio feedback for gestures"""
        self.engine.say(f"Gesture: {gesture_type}")
        self.engine.runAndWait()
```

**Integrate in Main:**
```python
# src/main.py
self.audio = AudioFeedback()

if gesture in ["LEFT_CLICK", "RIGHT_CLICK"]:
    self.audio.gesture_confirmed(gesture)
```

### 3. Gesture Recording & Playback

**Record User Gestures:**

```python
# src/gesture_recorder.py
import pickle

class GestureRecorder:
    def __init__(self):
        self.recording = False
        self.gestures = []
    
    def start_recording(self):
        self.recording = True
        self.gestures = []
    
    def record_gesture(self, landmarks, gesture_type):
        if self.recording:
            self.gestures.append({
                'landmarks': landmarks,
                'type': gesture_type,
                'timestamp': time.time()
            })
    
    def save_recording(self, filename):
        with open(filename, 'wb') as f:
            pickle.dump(self.gestures, f)
    
    def load_recording(self, filename):
        with open(filename, 'rb') as f:
            return pickle.load(f)
```

### 4. Machine Learning-Based Custom Gestures

**Train Custom Gesture Classifier:**

```python
# scripts/train_custom_gesture.py
import numpy as np
from sklearn.ensemble import RandomForestClassifier
import pickle

def train_gesture_model(gesture_recordings):
    """Train classifier on recorded gestures"""
    
    X = []
    y = []
    
    for recording in gesture_recordings:
        # Extract features from landmarks
        features = extract_landmark_features(recording['landmarks'])
        X.append(features)
        y.append(recording['type'])
    
    model = RandomForestClassifier(n_estimators=100)
    model.fit(X, y)
    
    with open('models/custom_gesture_model.pkl', 'wb') as f:
        pickle.dump(model, f)

def extract_landmark_features(landmarks):
    """Extract statistical features from landmarks"""
    landmarks = np.array(landmarks)
    
    return np.concatenate([
        landmarks.mean(axis=0),      # Mean position
        landmarks.std(axis=0),       # Variance
        landmarks.max(axis=0),       # Max position
        landmarks.min(axis=0),       # Min position
    ])
```

## Upgrading to Newer Versions

### 1. Update Dependencies

```bash
# Backup current working version
pip freeze > requirements_backup.txt

# Update all packages
pip install --upgrade -r requirements.txt

# If issues arise, revert
pip install -r requirements_backup.txt
```

### 2. MediaPipe Version Update

```bash
# Check current version
pip show mediapipe

# Update to latest
pip install --upgrade mediapipe

# Verify compatibility
python -c "import mediapipe as mp; print(mp.__version__)"
```

**Breaking Changes to Watch:**
- Hand landmark indices may change
- Confidence score ranges may differ
- Model accuracy/speed trade-offs

### 3. Configuration Migration

**Backup Before Updating:**
```bash
cp config.yaml config.yaml.v1_backup
```

**After Major Version Update:**
- Review new config options in `resources/sample_config.yaml`
- Manually merge changes into your `config.yaml`
- Test with new version

### 4. Database/Data Migration

If upgrading with data persistence:

```python
# Migration script
import json

def migrate_calibration_v1_to_v2(old_file):
    """Migrate calibration format"""
    with open(old_file, 'r') as f:
        old_data = json.load(f)
    
    new_data = {
        'version': '2.0',
        'timestamp': datetime.now().isoformat(),
        'thresholds': {
            'pinch_min': old_data.get('pinch_threshold', 2.0),
            'pinch_max': old_data.get('pinch_max', 3.0),
        },
        'user_profile': old_data.get('user_data', {}),
    }
    
    with open('data/calibration_profile.json', 'w') as f:
        json.dump(new_data, f, indent=2)
```

## Performance Optimization

### 1. Profile and Optimize Hot Paths

```python
# scripts/profile_performance.py
import cProfile
import pstats

def profile_application():
    profiler = cProfile.Profile()
    profiler.enable()
    
    # Run application
    app = GestureGlideApp()
    app.run()
    
    profiler.disable()
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')
    stats.print_stats(20)  # Top 20 functions
```

### 2. Memory Optimization

**Reduce Memory Footprint:**
```python
# src/gesture_detector.py

# BEFORE: Store full history
self.gesture_history = []  # Can grow unbounded

# AFTER: Use fixed-size deque
from collections import deque
self.gesture_history = deque(maxlen=100)  # Max 100 items
```

### 3. Vectorize Operations

```python
# BEFORE: Python loops
distances = []
for i in range(len(landmarks)):
    dist = math.sqrt((landmarks[i][0] - center[0])**2 + 
                     (landmarks[i][1] - center[1])**2)
    distances.append(dist)

# AFTER: NumPy vectorization
import numpy as np
landmarks = np.array(landmarks)
distances = np.linalg.norm(landmarks - center, axis=1)
```

## Testing Modifications

### 1. Unit Tests for Changes

```python
# tests/test_new_gesture.py
import pytest
from src.gesture_detector import GestureDetector

def test_swipe_left_detection():
    detector = GestureDetector()
    
    # Create mock landmarks for left swipe
    landmarks = create_mock_landmarks_swipe_left()
    gesture = detector.detect(landmarks)
    
    assert gesture == "SWIPE_LEFT"
```

### 2. Integration Tests

```bash
# Run full test suite
pytest tests/ -v

# Run specific test
pytest tests/test_new_gesture.py::test_swipe_left_detection -v

# Generate coverage report
pytest --cov=src --cov-report=html
```

### 3. Manual Testing

```bash
# Test interactive gesture recognition
python scripts/test_gestures.py

# Benchmark performance
python scripts/benchmark.py
```

## Troubleshooting Modifications

### Issue: Modified Code Causes Crashes

1. Check logs: `tail -f gestureglide.log`
2. Run tests: `pytest tests/`
3. Revert changes: `git checkout <file>`
4. Debug incrementally

### Issue: Performance Degradation After Modification

1. Profile: `python scripts/profile_performance.py`
2. Check memory: `python -m memory_profiler scripts/profile_performance.py`
3. Identify bottleneck
4. Optimize hot path

## Version Control & Deployment

### Git Workflow

```bash
# Create feature branch
git checkout -b feature/new-gesture-type

# Make changes and commit
git add .
git commit -m "Add new swipe gesture detection"

# Create pull request
git push origin feature/new-gesture-type
```

### Deployment Checklist

- [ ] All tests passing
- [ ] Configuration validated
- [ ] Documentation updated
- [ ] Performance benchmarked
- [ ] Backwards compatibility verified
- [ ] Backup of previous version
- [ ] Changelog updated

## Getting Help

- Review `docs/ARCHITECTURE.md` for system design
- Check `docs/API.md` for API reference
- See `SETUP.md` for environment setup
- Consult `MAINTENANCE.md` for operation issues
