# ============================================================================
# UTILITY TESTS
# ============================================================================
import pytest
import numpy as np
import logging

# Fix import path
from src.utils import euclidean_distance

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


class TestUtils:
    """Test utility functions"""
    
    def test_euclidean_distance(self):
        """Test distance calculation"""
        p1 = np.array([0, 0, 0])
        p2 = np.array([3, 4, 0])
        distance = euclidean_distance(p1, p2)
        assert abs(distance - 5.0) < 0.01
    
    def test_distance_same_points(self):
        """Test distance for identical points"""
        p1 = np.array([1, 2, 3])
        p2 = np.array([1, 2, 3])
        distance = euclidean_distance(p1, p2)
        assert distance < 0.001