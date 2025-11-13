# ============================================================================
# GESTURE DETECTOR TESTS
# ============================================================================

import pytest
import numpy as np
import logging

# Import dependencies needed by the module under test
from src.utils import euclidean_distance
# Fix import path
from src.gesture_detector import GestureDetector

# Mock fixtures for testing
@pytest.fixture
def sample_landmarks():
    """Generate sample hand landmarks"""
    # Create a more structured array for predictable distances
    landmarks = np.zeros((21, 3))
    # Place landmarks far apart
    landmarks[4] = np.array([0, 0, 0])  # Thumb
    landmarks[8] = np.array([10, 10, 10])  # Index
    landmarks[12] = np.array([20, 20, 20]) # Middle
    landmarks[16] = np.array([30, 30, 30]) # Ring
    return landmarks


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

class TestGestureDetector:
    """Test gesture recognition"""
    
    def test_gesture_detector_initialization(self):
        """Test GestureDetector initialization"""
        gd = GestureDetector()
        assert gd.pinch_threshold_min == 2.0
        assert gd.pinch_threshold_max == 3.0
    
    def test_no_gesture_detected(self, sample_landmarks):
        """Test no gesture when fingers apart"""
        gd = GestureDetector()
        
        # Landmarks are already far apart from the fixture
        gesture = gd.detect(sample_landmarks)
        assert gesture is None