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