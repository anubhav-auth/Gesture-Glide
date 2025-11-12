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
