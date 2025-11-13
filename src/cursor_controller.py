# ============================================================================
# CURSOR CONTROL
# ============================================================================

import logging
import numpy as np
from typing import Tuple, Optional

from src.utils import get_screen_size
from src.smoothing import KalmanFilter1D, MovingAverageFilter


class CursorController:
    """Cursor position control and smoothing"""
    
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
        
        self.logger.info(f"CursorController initialized: {self.screen_width}x{self.screen_height}")
    
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