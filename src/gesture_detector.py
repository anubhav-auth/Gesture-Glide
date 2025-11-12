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