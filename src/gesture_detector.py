# ============================================================================
# GESTURE DETECTION
# ============================================================================

import time
import logging
import numpy as np
from collections import deque
from typing import Optional, Dict, Any

from src.utils import euclidean_distance


class GestureDetector:
    """Gesture recognition state machine"""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the gesture detector with configuration.
        
        Args:
            config: The 'gesture_detection' section of the config.yaml file.
        """
        self.logger = logging.getLogger(__name__)

        # --- FIX: Convert config 'cm' values to 'meters' to match world landmarks ---
        CM_TO_METERS = 0.01

        # Load thresholds and convert to meters
        self.pinch_thresh = config.get('pinch_threshold_min', 2.0) * CM_TO_METERS
        self.three_finger_pinch_thresh = config.get('three_finger_pinch_min', 2.5) * CM_TO_METERS
        
        # Load timings
        self.click_debounce_ms = config.get('click_debounce_ms', 100)
        self.drag_hold_ms = config.get('drag_hold_threshold_ms', 200)
        self.zoom_debounce_ms = config.get('zoom_debounce_ms', 50)
        self.scroll_debounce_ms = config.get('scroll_debounce_ms', 100)

        # Load deltas and convert to meters
        self.zoom_delta = config.get('zoom_distance_delta_cm', 1.5) * CM_TO_METERS
        
        # Use a real-world Y-delta (in meters) for scrolling
        # 0.03 meters (3cm) is a reasonable default for a swipe.
        self.scroll_delta_y = 0.03
        self.scroll_delta_x = 0.03

        # State machine
        self.gesture_timers: dict[str, float] = {}
        self.last_landmarks: Optional[np.ndarray] = None
        
        # Drag state: "RELEASED" -> "HELD" (pinch down) -> "DRAGGING"
        self.drag_state = "RELEASED" 
        self.drag_start_time = 0.0
        
        # Last known distances for delta calculations
        self.last_zoom_dist = 0.0
        self.last_scroll_y = 0.0
        self.last_scroll_x = 0.0

        self.logger.info(f"GestureDetector initialized (Real-world Pinch Thresh: {self.pinch_thresh:.4f}m)")
        
    def _is_ready(self, gesture: str, debounce_ms: int) -> bool:
        """Check if debounce time has passed for a gesture"""
        current_time_ms = time.time() * 1000
        last_time = self.gesture_timers.get(gesture, 0)
        if (current_time_ms - last_time) > debounce_ms:
            self.gesture_timers[gesture] = current_time_ms
            return True
        return False

    def detect(self, landmarks: np.ndarray) -> Optional[str]:
        """Detect gesture from landmarks"""
        
        # --- Calculate Distances ---
        # (Landmark indices from MediaPipe)
        thumb_tip = landmarks[4]
        index_tip = landmarks[8]
        middle_tip = landmarks[12]
        ring_tip = landmarks[16]

        # Distances for gestures
        thumb_index_dist = euclidean_distance(thumb_tip, index_tip)
        index_middle_dist = euclidean_distance(index_tip, middle_tip)
        middle_ring_dist = euclidean_distance(middle_tip, ring_tip)
        
        # For 3-finger pinch, check both pairs
        all_three_pinch = (
            index_middle_dist < self.three_finger_pinch_thresh and
            middle_ring_dist < self.three_finger_pinch_thresh
        )

        # For 2-finger scroll, get average X and Y position
        current_scroll_y = (index_tip[1] + middle_tip[1]) / 2.0
        current_scroll_x = (index_tip[0] + middle_tip[0]) / 2.0  # <-- ADDED
        
        current_time_ms = time.time() * 1000
        gesture: Optional[str] = None

        # --- State Machine & Gesture Logic ---

        # 1. Check for Drag state (Thumb + Index)
        is_drag_pinch = thumb_index_dist < self.pinch_thresh
        
        if self.drag_state == "RELEASED":
            if is_drag_pinch:
                # User just pinched, start timer for drag
                self.drag_state = "HELD"
                self.drag_start_time = current_time_ms
        
        elif self.drag_state == "HELD":
            if not is_drag_pinch:
                # User released before drag hold time. This might be a Zoom.
                self.drag_state = "RELEASED"
                if self.last_landmarks is not None:
                    zoom_delta = thumb_index_dist - self.last_zoom_dist
                    if abs(zoom_delta) > self.zoom_delta and self._is_ready("ZOOM", self.zoom_debounce_ms):
                        # Pinching closer = Zoom In
                        gesture = "ZOOM_IN" if zoom_delta < 0 else "ZOOM_OUT"
                self.last_zoom_dist = thumb_index_dist
                
            elif (current_time_ms - self.drag_start_time) > self.drag_hold_ms:
                # Hold time elapsed, start dragging
                self.drag_state = "DRAGGING"
                gesture = "DRAG_START"
        
        elif self.drag_state == "DRAGGING":
            if not is_drag_pinch:
                # User released, end drag
                self.drag_state = "RELEASED"
                gesture = "DRAG_END"
            else:
                # User is still dragging
                gesture = "DRAG_MOVE"

        # 2. If not dragging, check for other click/scroll gestures
        if self.drag_state != "DRAGGING" and gesture is None:
            
            # --- Middle Click (3-Finger Pinch) ---
            if all_three_pinch:
                if self._is_ready("MIDDLE_CLICK", self.click_debounce_ms):
                    gesture = "MIDDLE_CLICK"
            
            # --- Right Click (Middle + Ring) ---
            elif middle_ring_dist < self.pinch_thresh:
                if self._is_ready("RIGHT_CLICK", self.click_debounce_ms):
                    gesture = "RIGHT_CLICK"

            # --- Left Click (Index + Middle) ---
            elif index_middle_dist < self.pinch_thresh:
                    if self._is_ready("LEFT_CLICK", self.click_debounce_ms):
                        gesture = "LEFT_CLICK"
            
            # --- Scroll (Vertical/Horizontal 2-Finger Swipe) ---  <-- MODIFIED BLOCK
            else:
                # Only check for scroll if no other pinch is active
                if self.last_landmarks is not None:
                    scroll_y_delta = current_scroll_y - self.last_scroll_y
                    scroll_x_delta = current_scroll_x - self.last_scroll_x
                    
                    # Prioritize vertical scroll
                    if abs(scroll_y_delta) > self.scroll_delta_y and self._is_ready("SCROLL", self.scroll_debounce_ms):
                        gesture = "SCROLL_DOWN" if scroll_y_delta > 0 else "SCROLL_UP"
                    # Else, check for horizontal scroll
                    elif abs(scroll_x_delta) > self.scroll_delta_x and self._is_ready("SCROLL", self.scroll_debounce_ms):
                        gesture = "SCROLL_RIGHT" if scroll_x_delta > 0 else "SCROLL_LEFT"
                
        # Update "last known" values for next frame's delta calculation
        if not is_drag_pinch:
             # Only update zoom baseline when not pinching
            self.last_zoom_dist = thumb_index_dist
       
        self.last_scroll_y = current_scroll_y
        self.last_scroll_x = current_scroll_x  # <-- ADDED
        self.last_landmarks = landmarks
        
        return gesture