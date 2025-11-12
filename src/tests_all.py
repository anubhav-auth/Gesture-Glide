"""
GestureGlide - Test Suite
Unit and integration tests for all components
"""

import pytest
import numpy as np
import logging

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


# ============================================================================
# UTILITY TESTS
# ============================================================================

class TestUtils:
    """Test utility functions"""
    
    def test_euclidean_distance(self):
        """Test distance calculation"""
        from src_all_modules import euclidean_distance
        p1 = np.array([0, 0, 0])
        p2 = np.array([3, 4, 0])
        distance = euclidean_distance(p1, p2)
        assert abs(distance - 5.0) < 0.01
    
    def test_distance_same_points(self):
        """Test distance for identical points"""
        from src_all_modules import euclidean_distance
        p1 = np.array([1, 2, 3])
        p2 = np.array([1, 2, 3])
        distance = euclidean_distance(p1, p2)
        assert distance < 0.001


# ============================================================================
# SMOOTHING FILTER TESTS
# ============================================================================

class TestSmoothingFilters:
    """Test cursor smoothing filters"""
    
    def test_kalman_filter_initialization(self):
        """Test Kalman filter initialization"""
        from src_all_modules import KalmanFilter1D
        kf = KalmanFilter1D(process_noise=0.01, measurement_noise=4.0)
        assert kf.value is None
        assert kf.error == 1.0
    
    def test_kalman_filter_first_measurement(self):
        """Test first measurement pass-through"""
        from src_all_modules import KalmanFilter1D
        kf = KalmanFilter1D()
        result = kf.filter(100.0)
        assert result == 100.0
        assert kf.value == 100.0
    
    def test_kalman_filter_convergence(self):
        """Test filter convergence"""
        from src_all_modules import KalmanFilter1D
        kf = KalmanFilter1D(process_noise=0.01, measurement_noise=4.0)
        
        # Feed consistent values
        for _ in range(10):
            result = kf.filter(50.0)
        
        # Should converge to input value
        assert abs(result - 50.0) < 2.0
    
    def test_moving_average_filter(self):
        """Test moving average filter"""
        from src_all_modules import MovingAverageFilter
        maf = MovingAverageFilter(window_size=3)
        
        assert maf.filter(10.0) == 10.0
        assert maf.filter(20.0) == 15.0
        assert maf.filter(30.0) == 20.0


# ============================================================================
# CURSOR CONTROLLER TESTS
# ============================================================================

class TestCursorController:
    """Test cursor control"""
    
    def test_cursor_controller_initialization(self):
        """Test CursorController initialization"""
        from src_all_modules import CursorController
        cc = CursorController(screen_width=1920, screen_height=1080)
        assert cc.screen_width == 1920
        assert cc.screen_height == 1080
    
    def test_cursor_position_update(self, sample_landmarks):
        """Test cursor position update"""
        from src_all_modules import CursorController
        cc = CursorController(screen_width=1920, screen_height=1080)
        
        # Middle finger is landmark 12
        sample_landmarks[12] = np.array([0.5, 0.5, 0.0])
        
        x, y = cc.update_position(sample_landmarks)
        
        # Should map to approximate screen center
        assert 900 < x < 1000
        assert 490 < y < 590
    
    def test_cursor_position_clamping(self, sample_landmarks):
        """Test cursor position is clamped to screen"""
        from src_all_modules import CursorController
        cc = CursorController(screen_width=1920, screen_height=1080)
        
        # Set middle finger outside bounds
        sample_landmarks[12] = np.array([1.5, 1.5, 0.0])
        
        x, y = cc.update_position(sample_landmarks)
        
        # Should be clamped to screen bounds
        assert 0 <= x < 1920
        assert 0 <= y < 1080


# ============================================================================
# GESTURE DETECTOR TESTS
# ============================================================================

class TestGestureDetector:
    """Test gesture recognition"""
    
    def test_gesture_detector_initialization(self):
        """Test GestureDetector initialization"""
        from src_all_modules import GestureDetector
        gd = GestureDetector()
        assert gd.pinch_threshold_min == 2.0
        assert gd.pinch_threshold_max == 3.0
    
    def test_no_gesture_detected(self, sample_landmarks):
        """Test no gesture when fingers apart"""
        from src_all_modules import GestureDetector
        gd = GestureDetector()
        
        # Set fingers far apart
        sample_landmarks[4] = np.array([0, 0, 0])  # Thumb
        sample_landmarks[8] = np.array([1, 1, 1])  # Index
        
        gesture = gd.detect(sample_landmarks)
        assert gesture is None or gesture == "CURSOR_MOVE"


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestIntegration:
    """Integration tests for full pipeline"""
    
    def test_full_pipeline(self, sample_landmarks):
        """Test full gesture recognition pipeline"""
        from src_all_modules import CursorController, GestureDetector
        
        cc = CursorController(screen_width=1920, screen_height=1080)
        gd = GestureDetector()
        
        # Update cursor position
        x, y = cc.update_position(sample_landmarks)
        assert isinstance(x, int) and isinstance(y, int)
        
        # Detect gesture
        gesture = gd.detect(sample_landmarks)
        assert gesture is None or isinstance(gesture, str)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
