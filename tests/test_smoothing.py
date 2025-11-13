# ============================================================================
# SMOOTHING FILTER TESTS
# ============================================================================
import pytest
import numpy as np
import logging

# Fix import path
from src.smoothing import KalmanFilter1D, MovingAverageFilter

# Mock fixtures for testing
@pytest.fixture
def sample_landmarks():
    """Generate sample hand landmarks"""
    return np.random.rand(21, 3)


@pytest.fixture
def config_fixture(tmp_path):
    """Create temporary config for testing"""
    config_file = tmp_path / "test_config.yaml"
    config_content = """
hand_tracking:
  detection_confidence: 0.7
  tracking_confidence: 0.7
  model_complexity: 0
  max_num_hands: 1

cursor_control:
  screen_width: 1920
  screen_height: 1080
  smoothing_filter: "kalman"
  speed_multiplier: 1.0

gesture_detection:
  pinch_threshold_min: 2.0
  pinch_threshold_max: 3.0
  click_debounce_ms: 100

performance:
  target_fps: 30
  use_gpu: false
"""
    config_file.write_text(config_content)
    return str(config_file)


class TestSmoothingFilters:
    """Test cursor smoothing filters"""
    
    def test_kalman_filter_initialization(self):
        """Test Kalman filter initialization"""
        kf = KalmanFilter1D(process_noise=0.01, measurement_noise=4.0)
        assert kf.value is None
        assert kf.error == 1.0
    
    def test_kalman_filter_first_measurement(self):
        """Test first measurement pass-through"""
        kf = KalmanFilter1D()
        result = kf.filter(100.0)
        assert result == 100.0
        assert kf.value == 100.0
    
    def test_kalman_filter_convergence(self):
        """Test filter convergence"""
        kf = KalmanFilter1D(process_noise=0.01, measurement_noise=4.0)
        
        result = 0.0 # Init
        # Feed consistent values
        for _ in range(10):
            result = kf.filter(50.0)
        
        # Should converge to input value
        assert abs(result - 50.0) < 2.0
    
    def test_moving_average_filter(self):
        """Test moving average filter"""
        maf = MovingAverageFilter(window_size=3)
        
        assert maf.filter(10.0) == 10.0
        assert maf.filter(20.0) == 15.0
        assert maf.filter(30.0) == 20.0