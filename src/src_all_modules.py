"""
GestureGlide - Complete Source Code Package
All modules for production deployment
"""

# ============================================================================
# UTILITY FUNCTIONS & HELPERS
# ============================================================================

import logging
import numpy as np
import cv2
from pathlib import Path
from typing import Tuple
import pyautogui


def setup_logging(log_level: str = "INFO", log_file: str = None):
    """Setup logging configuration"""
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, log_level))
    
    # Console handler
    console = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console.setFormatter(formatter)
    logger.addHandler(console)
    
    # File handler (optional)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)


def get_screen_size() -> Tuple[int, int]:
    """Get screen resolution"""
    return pyautogui.size()


def euclidean_distance(point1: np.ndarray, point2: np.ndarray) -> float:
    """Calculate Euclidean distance between two 3D points"""
    return np.linalg.norm(point1 - point2)


def draw_landmarks(frame: np.ndarray, landmarks: np.ndarray, 
                  color: Tuple = (0, 255, 0), radius: int = 4) -> np.ndarray:
    """Draw hand landmarks on frame"""
    h, w, _ = frame.shape
    for lm in landmarks:
        x, y = int(lm[0] * w), int(lm[1] * h)
        cv2.circle(frame, (x, y), radius, color, -1)
    return frame


def draw_hand_connections(frame: np.ndarray, landmarks: np.ndarray,
                         color: Tuple = (255, 0, 0)) -> np.ndarray:
    """Draw hand skeleton connections"""
    connections = [
        (0, 1), (1, 2), (2, 3), (3, 4),
        (0, 5), (5, 6), (6, 7), (7, 8),
        (0, 9), (9, 10), (10, 11), (11, 12),
        (0, 13), (13, 14), (14, 15), (15, 16),
        (0, 17), (17, 18), (18, 19), (19, 20),
    ]
    
    h, w, _ = frame.shape
    for start, end in connections:
        p1 = (int(landmarks[start][0] * w), int(landmarks[start][1] * h))
        p2 = (int(landmarks[end][0] * w), int(landmarks[end][1] * h))
        cv2.line(frame, p1, p2, color, 2)
    
    return frame


# ============================================================================
# SMOOTHING FILTERS
# ============================================================================

from collections import deque


class KalmanFilter1D:
    """1D Kalman filter for coordinate smoothing"""
    
    def __init__(self, process_noise: float = 0.01, measurement_noise: float = 4.0):
        self.process_noise = process_noise
        self.measurement_noise = measurement_noise
        self.value = None
        self.error = 1.0
    
    def filter(self, measurement: float) -> float:
        """Apply Kalman filter"""
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
    
    def reset(self):
        """Reset filter state"""
        self.value = None
        self.error = 1.0


class MovingAverageFilter:
    """Moving average filter"""
    
    def __init__(self, window_size: int = 5):
        self.window_size = window_size
        self.values = deque(maxlen=window_size)
    
    def filter(self, value: float) -> float:
        """Apply moving average"""
        self.values.append(value)
        return sum(self.values) / len(self.values) if self.values else value
    
    def reset(self):
        """Reset filter state"""
        self.values.clear()


# ============================================================================
# HAND TRACKING
# ============================================================================

import mediapipe as mp


class HandTracker:
    """MediaPipe-based hand tracking"""
    
    def __init__(self, detection_confidence: float = 0.7, 
                 tracking_confidence: float = 0.7,
                 model_complexity: int = 0,
                 max_num_hands: int = 1):
        self.logger = logging.getLogger(__name__)
        
        mp_hands = mp.solutions.hands
        self.hands = mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=max_num_hands,
            min_detection_confidence=detection_confidence,
            min_tracking_confidence=tracking_confidence,
            model_complexity=model_complexity
        )
        self.logger.info("HandTracker initialized")
    
    def detect(self, frame: np.ndarray) -> Tuple:
        """Detect hand landmarks"""
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


# ============================================================================
# CURSOR CONTROL
# ============================================================================

class CursorController:
    """Cursor position control and smoothing"""
    
    def __init__(self, screen_width: int = None, screen_height: int = None,
                 smoothing_filter: str = "kalman"):
        self.logger = logging.getLogger(__name__)
        
        if screen_width is None or screen_height is None:
            screen_width, screen_height = get_screen_size()
        
        self.screen_width = screen_width
        self.screen_height = screen_height
        
        if smoothing_filter == "kalman":
            self.filter_x = KalmanFilter1D()
            self.filter_y = KalmanFilter1D()
        else:
            self.filter_x = MovingAverageFilter()
            self.filter_y = MovingAverageFilter()
        
        self.logger.info(f"CursorController initialized: {screen_width}x{screen_height}")
    
    def update_position(self, landmarks: np.ndarray) -> Tuple[int, int]:
        """Update cursor position from middle finger"""
        middle_finger = landmarks[12]
        
        x = middle_finger[0] * self.screen_width
        y = middle_finger[1] * self.screen_height
        
        x_smooth = self.filter_x.filter(x)
        y_smooth = self.filter_y.filter(y)
        
        x_clamped = max(0, min(int(x_smooth), self.screen_width - 1))
        y_clamped = max(0, min(int(y_smooth), self.screen_height - 1))
        
        return x_clamped, y_clamped


# ============================================================================
# GESTURE DETECTION
# ============================================================================

import time


class GestureDetector:
    """Gesture recognition state machine"""
    
    def __init__(self, pinch_threshold_min: float = 2.0,
                 pinch_threshold_max: float = 3.0,
                 click_debounce_ms: int = 100):
        self.logger = logging.getLogger(__name__)
        
        self.pinch_threshold_min = pinch_threshold_min
        self.pinch_threshold_max = pinch_threshold_max
        self.click_debounce_ms = click_debounce_ms
        
        self.gesture_timers = {}
        self.last_landmarks = None
        self.pinch_history = deque(maxlen=10)
    
    def detect(self, landmarks: np.ndarray) -> str:
        """Detect gesture from landmarks"""
        
        thumb_index_dist = euclidean_distance(landmarks[4], landmarks[8])
        index_middle_dist = euclidean_distance(landmarks[8], landmarks[12])
        middle_ring_dist = euclidean_distance(landmarks[12], landmarks[16])
        
        gesture = None
        
        # Check pinch gestures
        if index_middle_dist < self.pinch_threshold_min:
            gesture = self._debounce("LEFT_CLICK")
        elif middle_ring_dist < self.pinch_threshold_min:
            gesture = self._debounce("RIGHT_CLICK")
        elif thumb_index_dist < self.pinch_threshold_min:
            gesture = self._debounce("DRAG_MOVE")
        
        self.last_landmarks = landmarks
        return gesture
    
    def _debounce(self, gesture: str) -> str:
        """Apply debouncing to gesture"""
        current_time = time.time() * 1000
        
        if gesture not in self.gesture_timers:
            self.gesture_timers[gesture] = current_time
            return gesture
        
        if current_time - self.gesture_timers[gesture] > self.click_debounce_ms:
            self.gesture_timers[gesture] = current_time
            return gesture
        
        return None


# ============================================================================
# MOUSE ACTIONS
# ============================================================================

class MouseActions:
    """Mouse event injection"""
    
    def __init__(self):
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
        """Scroll (positive=up, negative=down)"""
        pyautogui.scroll(delta)
        self.logger.debug(f"Scroll: {delta}")
