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

# --- Fixtures for Mock Data ---

@pytest.fixture
def gesture_config() -> dict:
    """
    Provides a mock gesture_detection config dictionary.
    The thresholds are in 'cm' as defined in config.yaml.
    The detector class will internally convert them.
    """
    config = {
        'pinch_threshold_min': 2.0,
        'three_finger_pinch_min': 2.5,
        'click_debounce_ms': 100,
        'drag_hold_threshold_ms': 200,
        'zoom_debounce_ms': 50,
        'scroll_debounce_ms': 100,
        'zoom_distance_delta_cm': 1.5,
        'scroll_distance_threshold_px': 50
    }
    return config

@pytest.fixture
def neutral_hand() -> np.ndarray:
    """
    Generates mock landmarks for a hand with all fingers apart.
    Coordinates are normalized (0.0 - 1.0).
    """
    landmarks = np.zeros((21, 3))
    # Set key landmarks far apart (normalized coords)
    landmarks[4] = np.array([0.1, 0.1, 0])  # Thumb Tip
    landmarks[8] = np.array([0.3, 0.5, 0])  # Index Tip
    landmarks[12] = np.array([0.4, 0.5, 0]) # Middle Tip
    landmarks[16] = np.array([0.5, 0.5, 0]) # Ring Tip
    return landmarks

@pytest.fixture
def left_click_pinch(neutral_hand: np.ndarray) -> np.ndarray:
    """ Simulates a left click (Index + Middle pinch) """
    # Move Middle tip very close to Index tip
    # Distance < 0.05 (which is 2cm / 40cm scale factor)
    neutral_hand[12] = np.array([0.31, 0.5, 0]) 
    return neutral_hand

@pytest.fixture
def right_click_pinch(neutral_hand: np.ndarray) -> np.ndarray:
    """ Simulates a right click (Middle + Ring pinch) """
    # Move Ring tip very close to Middle tip
    neutral_hand[16] = np.array([0.41, 0.5, 0])
    return neutral_hand

@pytest.fixture
def middle_click_pinch(neutral_hand: np.ndarray) -> np.ndarray:
    """ Simulates a middle click (Index + Middle + Ring pinch) """
    # Move Middle close to Index
    neutral_hand[12] = np.array([0.31, 0.5, 0])
    # Move Ring close to Middle
    neutral_hand[16] = np.array([0.32, 0.5, 0])
    return neutral_hand

@pytest.fixture
def drag_pinch(neutral_hand: np.ndarray) -> np.ndarray:
    """ Simulates a drag pinch (Thumb + Index) """
    # Move Index tip very close to Thumb tip
    neutral_hand[8] = np.array([0.11, 0.1, 0])
    return neutral_hand


# --- Test Class ---

class TestGestureDetector:
    """Test gesture recognition"""
    
    def test_gesture_detector_initialization(self, gesture_config: dict):
        """Test GestureDetector initialization with the new config dict"""
        gd = GestureDetector(gesture_config)
        # Test if it correctly calculates the normalized threshold
        # 2.0cm / 40.0 scale_factor = 0.05
        assert abs(gd.pinch_thresh - 0.05) < 0.001
        assert gd.click_debounce_ms == 100
    
    def test_no_gesture_detected(self, gesture_config: dict, neutral_hand: np.ndarray):
        """Test no gesture when fingers are apart"""
        gd = GestureDetector(gesture_config)
        gesture = gd.detect(neutral_hand)
        assert gesture is None

    def test_left_click_detected(self, gesture_config: dict, left_click_pinch: np.ndarray):
        """Test positive case for left click gesture"""
        gd = GestureDetector(gesture_config)
        gesture = gd.detect(left_click_pinch)
        assert gesture == "LEFT_CLICK"

    def test_right_click_detected(self, gesture_config: dict, right_click_pinch: np.ndarray):
        """Test positive case for right click gesture"""
        gd = GestureDetector(gesture_config)
        gesture = gd.detect(right_click_pinch)
        assert gesture == "RIGHT_CLICK"

    def test_middle_click_detected(self, gesture_config: dict, middle_click_pinch: np.ndarray):
        """Test positive case for middle click gesture"""
        gd = GestureDetector(gesture_config)
        gesture = gd.detect(middle_click_pinch)
        assert gesture == "MIDDLE_CLICK"
    
    def test_drag_pinch_detected(self, gesture_config: dict, drag_pinch: np.ndarray):
        """
        Test that a drag pinch is correctly identified.
        Note: This only tests the *first* frame of a drag (the "HELD" state).
        Testing the full "DRAGGING" state requires mocking time, which is more complex.
        """
        gd = GestureDetector(gesture_config)
        gesture = gd.detect(drag_pinch)
        # On the first frame, no gesture is returned, but the state is set to "HELD"
        assert gesture is None
        assert gd.drag_state == "HELD"