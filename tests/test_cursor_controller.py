# ============================================================================
# CURSOR CONTROLLER TESTS
# ============================================================================

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
