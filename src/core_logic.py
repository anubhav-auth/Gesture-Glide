# src/core_logic.py
import logging
import cv2
import numpy as np
from typing import Optional, Tuple, List, Dict, Any

from src.config import Config
from src.hand_tracker import HandTracker
from src.cursor_controller import CursorController
from src.gesture_detector import GestureDetector
from src.mouse_actions import MouseActions
from src.utils import draw_hand_connections, draw_landmarks

class GestureCoreLogic:
    """
    Holds the shared logic for processing frames, detecting gestures,
    executing actions, and drawing visualizations.
    """
    def __init__(
        self,
        config: Config,
        hand_tracker: HandTracker,
        cursor_controller: CursorController,
        gesture_detector: GestureDetector,
        mouse_actions: MouseActions
    ):
        self.logger = logging.getLogger(__name__)
        self.config = config
        self.hand_tracker = hand_tracker
        self.cursor_controller = cursor_controller
        self.gesture_detector = gesture_detector
        self.mouse_actions = mouse_actions

    def _execute_actions(self, gesture: Optional[str], cursor_x: int, cursor_y: int):
        """Maps gestures to mouse actions."""
        if gesture is None or gesture == "CURSOR_MOVE":
            self.mouse_actions.move_cursor(cursor_x, cursor_y)
        elif gesture == "LEFT_CLICK":
            self.mouse_actions.left_click()
        elif gesture == "RIGHT_CLICK":
            self.mouse_actions.right_click()
        elif gesture == "MIDDLE_CLICK":
            self.mouse_actions.middle_click()
        elif gesture == "DRAG_START":
            self.mouse_actions.start_drag(cursor_x, cursor_y)
        elif gesture == "DRAG_MOVE":
            self.mouse_actions.drag_to(cursor_x, cursor_y)
        elif gesture == "DRAG_END":
            self.mouse_actions.end_drag()
        elif gesture == "ZOOM_IN":
            self.mouse_actions.scroll(5)  # Scroll up
        elif gesture == "ZOOM_OUT":
            self.mouse_actions.scroll(-5)  # Scroll down
        elif gesture == "SCROLL_UP":
            self.mouse_actions.scroll(3)
        elif gesture == "SCROLL_DOWN":
            self.mouse_actions.scroll(-3)
        
        if gesture:
             self.logger.debug(f"Executed gesture: {gesture}")

    def process_frame(self, frame: np.ndarray) -> Tuple[Optional[str], Optional[np.ndarray], Optional[Tuple[int, int]]]:
        """
        Processes a single frame:
        1. Detects hands
        2. Processes gestures for the primary hand
        3. Executes mouse actions
        Returns (gesture, landmarks, cursor_pos) for visualization.
        """
        gesture_out: Optional[str] = None
        landmarks_out: Optional[np.ndarray] = None
        cursor_pos_out: Optional[Tuple[int, int]] = None

        detected_hands = self.hand_tracker.detect(frame)
        
        # Process the first hand that meets the confidence threshold
        hand_processed = False
        for landmarks, handedness, confidence in detected_hands:
            if not hand_processed and confidence > self.config.hand_tracking['detection_confidence']:
                hand_processed = True

                cursor_x, cursor_y = self.cursor_controller.update_position(landmarks)
                gesture = self.gesture_detector.detect(landmarks)
                
                self._execute_actions(gesture, cursor_x, cursor_y)

                # Store outputs for visualization
                gesture_out = gesture
                landmarks_out = landmarks
                cursor_pos_out = (cursor_x, cursor_y)

        return gesture_out, landmarks_out, cursor_pos_out

    def draw_visualizations(
        self, 
        frame: np.ndarray, 
        gesture: Optional[str], 
        landmarks: Optional[np.ndarray], 
        cursor_pos: Optional[Tuple[int, int]]
    ) -> np.ndarray:
        """Draws all visualizations onto the frame."""
        
        # Draw hand skeleton
        if landmarks is not None and self.config.visualization['show_hand_skeleton']:
            try:
                skeleton_color = tuple(self.config.visualization['skeleton_color'])
                landmark_color = tuple(self.config.visualization['text_color'])
                landmark_size = self.config.visualization['landmark_size']
                
                draw_hand_connections(frame, landmarks, color=skeleton_color)
                draw_landmarks(frame, landmarks, color=landmark_color, radius=landmark_size)
            except Exception as e:
                self.logger.warning(f"Failed to draw skeleton: {e}")
        
        # Draw gesture indicator
        if gesture and self.config.visualization['show_gesture_indicators']:
            text = f"Gesture: {gesture}"
            cv2.putText(frame, text, (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 1,
                        tuple(self.config.visualization['text_color']), 2)

        # Draw cursor reference
        if cursor_pos and self.config.visualization['show_cursor_position']:
            # Draw a circle on the video feed (clamped to feed size)
            h, w, _ = frame.shape
            feed_x = cursor_pos[0] % w
            feed_y = cursor_pos[1] % h
            cv2.circle(frame, (feed_x, feed_y), 5, (0, 255, 0), -1)

        return frame