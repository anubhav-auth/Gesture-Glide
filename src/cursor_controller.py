# ============================================================================
# CURSOR CONTROL
# ============================================================================

import logging
import numpy as np
from typing import Tuple, Optional

from src.utils import get_screen_size
from src.smoothing import KalmanFilter1D, MovingAverageFilter


class CursorController:
    """Cursor position control and smoothing with aspect-ratio correction"""
    
    def __init__(self, screen_width: Optional[int] = None, 
                 screen_height: Optional[int] = None,
                 smoothing_filter: str = "kalman"):
        self.logger = logging.getLogger(__name__)
        
        if screen_width is None or screen_height is None:
            screen_width_detected, screen_height_detected = get_screen_size()
            screen_width = screen_width if screen_width is not None else screen_width_detected
            screen_height = screen_height if screen_height is not None else screen_height_detected

        
        self.screen_width = screen_width
        self.screen_height = screen_height
        
        if smoothing_filter == "kalman":
            self.filter_x = KalmanFilter1D()
            self.filter_y = KalmanFilter1D()
        else:
            self.filter_x = MovingAverageFilter()
            self.filter_y = MovingAverageFilter()
            
        # --- FIX 2.1: Aspect Ratio Correction ---
        # Camera resolution is hard-coded to 640x480 in main.py
        self.camera_width = 640.0
        self.camera_height = 480.0
        self.camera_aspect = self.camera_width / self.camera_height
        self.screen_aspect = self.screen_width / self.screen_height
        
        self.scale_x = 0.0
        self.scale_y = 0.0
        self.offset_x = 0.0
        self.offset_y = 0.0
        
        if self.screen_aspect > self.camera_aspect:
            # Screen is wider than camera (pillarbox)
            # Map full height, calculate width based on height
            self.scale_y = self.screen_height
            self.offset_y = 0
            
            map_width = self.screen_height * self.camera_aspect
            self.scale_x = map_width
            self.offset_x = (self.screen_width - map_width) / 2
        
        else:
            # Screen is taller than camera (letterbox)
            # Map full width, calculate height based on width
            self.scale_x = self.screen_width
            self.offset_x = 0
            
            map_height = self.screen_width / self.camera_aspect
            self.scale_y = map_height
            self.offset_y = (self.screen_height - map_height) / 2

        self.logger.info(f"CursorController initialized: {self.screen_width}x{self.screen_height}")
        self.logger.info(f"Aspect correction: Screen={self.screen_aspect:.2f}, Cam={self.camera_aspect:.2f}")
        self.logger.info(f"Mapping: Scale=({self.scale_x:.0f}, {self.scale_y:.0f}), Offset=({self.offset_x:.0f}, {self.offset_y:.0f})")

    
    def update_position(self, landmarks: np.ndarray) -> Tuple[int, int]:
        """Update cursor position from middle finger with aspect ratio correction"""
        # Middle finger is landmark 12
        middle_finger_norm = landmarks[12]
        
        # Invert X-axis. Most webcams mirror the image.
        # This makes moving your hand to your physical right move the cursor right.
        x_norm_flipped = 1.0 - middle_finger_norm[0]
        y_norm = middle_finger_norm[1]
        
        # Apply aspect-ratio correct scaling and offset
        x = x_norm_flipped * self.scale_x + self.offset_x
        y = y_norm * self.scale_y + self.offset_y
        
        x_smooth = self.filter_x.filter(x)
        y_smooth = self.filter_y.filter(y)
        
        # Clamp to screen dimensions
        x_clamped = max(0, min(int(x_smooth), self.screen_width - 1))
        y_clamped = max(0, min(int(y_smooth), self.screen_height - 1))
        
        return x_clamped, y_clamped