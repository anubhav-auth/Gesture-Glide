# src/smoothing.py
from collections import deque

class KalmanFilter1D:
    def __init__(self, process_noise: float = 0.1, measurement_noise: float = 4.0):
        self.process_noise = float(process_noise)
        self.measurement_noise = float(measurement_noise)
        self.estimate = None
        self.error_cov = 1.0

    def filter(self, measurement: float) -> float:
        if self.estimate is None:
            self.estimate = float(measurement)
            self.error_cov = 1.0
            return self.estimate
        # Predict
        pred_estimate = self.estimate
        pred_error_cov = self.error_cov + self.process_noise
        # Update
        K = pred_error_cov / (pred_error_cov + self.measurement_noise)
        self.estimate = pred_estimate + K * (measurement - pred_estimate)
        self.error_cov = (1.0 - K) * pred_error_cov
        return self.estimate

    def reset(self, value: float | None = None):
        self.estimate = float(value) if value is not None else None
        self.error_cov = 1.0


class MovingAverageFilter:
    def __init__(self, window_size: int = 5):
        self.window_size = max(1, int(window_size))
        self.buffer = deque(maxlen=self.window_size)
        self._sum = 0.0

    def filter(self, x: float) -> float:
        if len(self.buffer) == self.buffer.maxlen:
            self._sum -= self.buffer[0]
        self.buffer.append(float(x))
        self._sum += float(x)
        return self._sum / len(self.buffer)

    def reset(self):
        self.buffer.clear()
        self._sum = 0.0


class EMAFilter1D:
    """
    Exponential moving average stabilizer for low-latency jitter reduction.
    alpha in (0,1]; lower alpha = stronger smoothing.
    """
    def __init__(self, alpha: float = 0.25):
        self.alpha = float(alpha)
        self._value = None

    def filter(self, x: float) -> float:
        x = float(x)
        if self._value is None:
            self._value = x
        else:
            a = self.alpha
            self._value = a * x + (1.0 - a) * self._value
        return self._value

    def reset(self, value: float | None = None):
        self._value = float(value) if value is not None else None
