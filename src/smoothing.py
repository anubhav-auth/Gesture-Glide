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
