"""
GestureGlide - Complete Core Module Implementation
All modules in one file for easy deployment and modification
"""

import cv2
import mediapipe as mp
import numpy as np
import yaml
import logging
import pyautogui
from pathlib import Path
from typing import Tuple, Optional, Dict, Any
from collections import deque
import time

# ==================== CONFIGURATION MANAGEMENT ====================

class Config:
    """Load and manage configuration from YAML file"""
    
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = Path(config_path)
        self.config = self._load_config()
    
    def _load_config(self) -> Dict:
        """Load configuration from YAML file"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")
        
        with open(self.config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def __getitem__(self, key):
        return self.config[key]
    
    def get(self, key, default=None):
        return self.config.get(key, default)
    
    @property
    def hand_tracking(self):
        return self.config['hand_tracking']
    
    @property
    def cursor_control(self):
        return self.config['cursor_control']
    
    @property
    def gesture_detection(self):
        return self.config['gesture_detection']
    
    @property
    def performance(self):
        return self.config['performance']
    
    @property
    def visualization(self):
        return self.config['visualization']
    
    @property
    def system(self):
        return self.config['system']
    
    @property
    def advanced(self):
        return self.config['advanced']


# ==================== LOGGING ====================

def setup_logging(config: Config):
    """Setup logging based on configuration"""
    log_level = config.system.get('log_level', 'INFO')
    log_file = config.system.get('log_file', '')
    
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, log_level))
    
    # Console handler
    console = logging.StreamHandler()
    console.setLevel(getattr(logging, log_level))
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console.setFormatter(formatter)
    logger.addHandler(console)
    
    # File handler (optional)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(getattr(logging, log_level))
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)


# ==================== HAND TRACKING ====================

class HandTracker:
    """MediaPipe-based hand landmark detection"""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Initialize MediaPipe
        mp_hands = mp.solutions.hands
        self.hands = mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=config.hand_tracking['max_num_hands'],
            min_detection_confidence=config.hand_tracking['detection_confidence'],
            min_tracking_confidence=config.hand_tracking['tracking_confidence'],
            model_complexity=config.hand_tracking['model_complexity']
        )
        
        self.logger.info("HandTracker initialized")
    
    def detect(self, frame: np.ndarray) -> Tuple[Optional[np.ndarray], Optional[str], float]:
        """Detect hand landmarks in frame
        
        Returns:
            landmarks: 21x3 array of hand landmarks or None
            handedness: 'Right' or 'Left' or None
            confidence: Detection confidence score
        """
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.hands.process(rgb_frame)
        
        if results.multi_hand_landmarks and results.multi_handedness:
            landmarks = np.array([
                [lm.x, lm.y, lm.z] 
                for lm in results.multi_hand_landmarks[0].landmark
            ])
            handedness = results.multi_handedness[0].classification[0].label
            confidence = results.multi_handedness[0].classification[0].score
            
            return landmarks, handedness, confidence
        
        return None, None, 0.0


# ==================== CURSOR CONTROL ====================

class KalmanFilter1D:
    """Simple 1D Kalman filter for smoothing"""
    
    def __init__(self, process_noise=0.01, measurement_noise=4.0):
        self.process_noise = process_noise
        self.measurement_noise = measurement_noise
        self.value = None
        self.error = 1.0
    
    def filter(self, measurement: float) -> float:
        """Apply Kalman filter to measurement"""
        if self.value is None:
            self.value = measurement
            return measurement
        
        # Predict
        prediction = self.value
        prediction_error = self.error + self.process_noise
        
        # Update
        kalman_gain = prediction_error / (prediction_error + self.measurement_noise)
        self.value = prediction + kalman_gain * (measurement - prediction)
        self.error = (1 - kalman_gain) * prediction_error
        
        return self.value


class CursorController:
    """Control cursor position based on hand landmarks"""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Get screen resolution
        screen_width, screen_height = pyautogui.size()
        self.screen_width = screen_width
        self.screen_height = screen_height
        
        # Initialize smoothing filter
        filter_type = config.cursor_control['smoothing_filter']
        if filter_type == 'kalman':
            self.filter_x = KalmanFilter1D(
                process_noise=config.cursor_control['kalman_process_noise'],
                measurement_noise=config.cursor_control['kalman_measurement_noise']
            )
            self.filter_y = KalmanFilter1D(
                process_noise=config.cursor_control['kalman_process_noise'],
                measurement_noise=config.cursor_control['kalman_measurement_noise']
            )
        else:
            self.filter_x = MovingAverageFilter(config.cursor_control['moving_average_window'])
            self.filter_y = MovingAverageFilter(config.cursor_control['moving_average_window'])
        
        self.logger.info(f"CursorController initialized: {screen_width}x{screen_height}")
    
    def update_position(self, landmarks: np.ndarray) -> Tuple[int, int]:
        """Update cursor position based on middle finger tip (landmark 12)"""
        
        # Middle finger tip is landmark 12
        middle_finger = landmarks[12]
        
        # Normalize to screen coordinates
        x_norm = middle_finger[0]
        y_norm = middle_finger[1]
        
        # Invert Y (camera Y increases downward, screen Y increases downward too)
        x = x_norm * self.screen_width
        y = y_norm * self.screen_height
        
        # Apply smoothing filter
        x_smooth = self.filter_x.filter(x)
        y_smooth = self.filter_y.filter(y)
        
        # Clamp to screen bounds
        x_clamped = max(0, min(int(x_smooth), self.screen_width - 1))
        y_clamped = max(0, min(int(y_smooth), self.screen_height - 1))
        
        return x_clamped, y_clamped


class MovingAverageFilter:
    """Moving average filter for smoothing"""
    
    def __init__(self, window_size: int = 5):
        self.window_size = window_size
        self.values = deque(maxlen=window_size)
    
    def filter(self, value: float) -> float:
        """Apply moving average filter"""
        self.values.append(value)
        return sum(self.values) / len(self.values) if self.values else value


# ==================== GESTURE DETECTION ====================

class GestureDetector:
    """Detect hand gestures using landmark distances and state machine"""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Gesture state machine
        self.gesture_state = "IDLE"
        self.gesture_timers = {}
        self.last_landmarks = None
        self.pinch_history = deque(maxlen=10)
        
        self.logger.info("GestureDetector initialized")
    
    def detect(self, landmarks: np.ndarray) -> Optional[str]:
        """Detect gesture from landmarks
        
        Returns:
            Gesture type or None if no gesture detected
        """
        
        # Calculate key distances
        thumb_index_dist = self._distance(landmarks[4], landmarks[8])
        index_middle_dist = self._distance(landmarks[8], landmarks[12])
        middle_ring_dist = self._distance(landmarks[12], landmarks[16])
        three_finger_dist = max(index_middle_dist, middle_ring_dist, thumb_index_dist)
        
        gesture = None
        
        # Check for pinch gestures
        config_thresholds = self.config.gesture_detection
        min_thresh = config_thresholds['pinch_threshold_min']
        max_thresh = config_thresholds['pinch_threshold_max']
        
        # Left click (index-middle pinch)
        if index_middle_dist < min_thresh:
            gesture = self._debounce_gesture("LEFT_CLICK", 
                                            config_thresholds['click_debounce_ms'])
        
        # Right click (middle-ring pinch)
        elif middle_ring_dist < min_thresh:
            gesture = self._debounce_gesture("RIGHT_CLICK",
                                            config_thresholds['click_debounce_ms'])
        
        # Middle click (three-finger pinch)
        elif three_finger_dist < config_thresholds['three_finger_pinch_min']:
            gesture = self._debounce_gesture("MIDDLE_CLICK",
                                            config_thresholds['click_debounce_ms'])
        
        # Drag detection
        if thumb_index_dist < min_thresh and self._is_hand_moving(landmarks):
            gesture = self._debounce_gesture("DRAG_MOVE",
                                            config_thresholds['drag_debounce_ms'])
        
        # Zoom detection
        if thumb_index_dist < min_thresh:
            current_pinch = thumb_index_dist
            self.pinch_history.append(current_pinch)
            
            if len(self.pinch_history) > 1:
                pinch_delta = abs(self.pinch_history[-1] - self.pinch_history[0])
                zoom_delta = config_thresholds['zoom_distance_delta_cm']
                
                if pinch_delta > zoom_delta:
                    if self.pinch_history[-1] > self.pinch_history[0]:
                        gesture = "ZOOM_OUT"
                    else:
                        gesture = "ZOOM_IN"
        
        self.last_landmarks = landmarks
        return gesture
    
    def _distance(self, point1: np.ndarray, point2: np.ndarray) -> float:
        """Calculate Euclidean distance between two 3D points"""
        return np.linalg.norm(point1 - point2)
    
    def _debounce_gesture(self, gesture: str, debounce_ms: int) -> Optional[str]:
        """Apply debouncing to gesture detection"""
        current_time = time.time() * 1000  # Convert to ms
        
        if gesture not in self.gesture_timers:
            self.gesture_timers[gesture] = current_time
            return gesture
        
        if current_time - self.gesture_timers[gesture] > debounce_ms:
            self.gesture_timers[gesture] = current_time
            return gesture
        
        return None
    
    def _is_hand_moving(self, landmarks: np.ndarray) -> bool:
        """Check if hand is moving (for drag detection)"""
        if self.last_landmarks is None:
            return False
        
        movement = np.linalg.norm(landmarks[12] - self.last_landmarks[12])
        return movement > 0.05  # Threshold in normalized coordinates


# ==================== MOUSE ACTIONS ====================

class MouseActions:
    """Inject mouse events using PyAutoGUI"""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.drag_active = False
    
    def move_cursor(self, x: int, y: int):
        """Move cursor to position"""
        pyautogui.moveTo(x, y, duration=0)
    
    def left_click(self):
        """Perform left click"""
        pyautogui.click(button='left')
        self.logger.debug("Left click")
    
    def right_click(self):
        """Perform right click"""
        pyautogui.click(button='right')
        self.logger.debug("Right click")
    
    def middle_click(self):
        """Perform middle click"""
        pyautogui.click(button='middle')
        self.logger.debug("Middle click")
    
    def start_drag(self, x: int, y: int):
        """Start drag operation"""
        pyautogui.mouseDown(button='left')
        self.drag_active = True
        self.logger.debug(f"Drag started at ({x}, {y})")
    
    def drag_to(self, x: int, y: int):
        """Continue drag to position"""
        if self.drag_active:
            pyautogui.moveTo(x, y, duration=0)
    
    def end_drag(self):
        """End drag operation"""
        if self.drag_active:
            pyautogui.mouseUp(button='left')
            self.drag_active = False
            self.logger.debug("Drag ended")
    
    def scroll(self, delta: int):
        """Scroll (positive = up, negative = down)"""
        pyautogui.scroll(delta)
        self.logger.debug(f"Scroll: {delta}")


# ==================== UTILITY FUNCTIONS ====================

def get_screen_size() -> Tuple[int, int]:
    """Get screen resolution"""
    width, height = pyautogui.size()
    return width, height


def draw_hand_skeleton(frame: np.ndarray, landmarks: np.ndarray, 
                       config: Config) -> np.ndarray:
    """Draw hand skeleton overlay on frame"""
    
    if not config.visualization['show_hand_skeleton']:
        return frame
    
    h, w, _ = frame.shape
    
    # Connection indices for hand skeleton
    connections = [
        (0, 1), (1, 2), (2, 3), (3, 4),  # Thumb
        (0, 5), (5, 6), (6, 7), (7, 8),  # Index
        (0, 9), (9, 10), (10, 11), (11, 12),  # Middle
        (0, 13), (13, 14), (14, 15), (15, 16),  # Ring
        (0, 17), (17, 18), (18, 19), (19, 20),  # Pinky
        (5, 9), (9, 13), (13, 17),  # Palm connections
    ]
    
    skeleton_color = tuple(config.visualization['skeleton_color'])
    landmark_size = config.visualization['landmark_size']
    
    # Draw connections
    for start_idx, end_idx in connections:
        start = (int(landmarks[start_idx][0] * w), int(landmarks[start_idx][1] * h))
        end = (int(landmarks[end_idx][0] * w), int(landmarks[end_idx][1] * h))
        cv2.line(frame, start, end, skeleton_color, 2)
    
    # Draw landmarks
    if config.visualization['show_landmarks']:
        for lm in landmarks:
            x, y = int(lm[0] * w), int(lm[1] * h)
            cv2.circle(frame, (x, y), landmark_size, skeleton_color, -1)
    
    return frame
