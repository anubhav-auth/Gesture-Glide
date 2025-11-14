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
        
        # Track drag state locally
        self.drag_active = False

    def _execute_actions(self, gesture: Optional[str], cursor_x: int, cursor_y: int):
        """Maps gestures to mouse actions."""
        
        # ALWAYS move cursor
        self.mouse_actions.move_cursor(cursor_x, cursor_y)

        if gesture:
             self.logger.debug(f"Received gesture: {gesture}")

        if gesture == "LEFT_CLICK":
            self.mouse_actions.left_click()
        elif gesture == "RIGHT_CLICK":
            self.mouse_actions.right_click()
        elif gesture == "MIDDLE_CLICK":
            self.mouse_actions.middle_click()
        
        # Note: The new GestureDetector doesn't emit drag/scroll/zoom.
        # This logic is kept as a placeholder if you extend the detector.
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


    def process_frame(self, frame: np.ndarray) -> Tuple[Optional[str], Optional[np.ndarray], Optional[Tuple[int, int]]]:
        """
        Processes a single frame:
        1. Detects hands
        2. Processes gestures and cursor for the primary hand
        Returns (gesture, landmarks, cursor_pos) for visualization.
        """
        gesture_out: Optional[str] = None
        landmarks_out: Optional[np.ndarray] = None
        cursor_pos_out: Optional[Tuple[int, int]] = None

        detected_hands = self.hand_tracker.detect(frame)
        
        hand_processed = False
        # Unpack the tuple from hand_tracker
        for image_landmarks, world_landmarks, handedness, confidence in detected_hands:
            
            # Process the first hand that meets the confidence threshold
            if not hand_processed and confidence > self.config.hand_tracking['detection_confidence']:
                hand_processed = True

                # 1. Cursor uses 2D image landmarks
                cursor_x, cursor_y = self.cursor_controller.update_position(image_landmarks)
                
                # 2. Gesture detection also uses 2D image landmarks
                # --- FIX: Convert ndarray to list to satisfy type checker ---
                gesture = self.gesture_detector.detect(image_landmarks.tolist())
                # --- END FIX ---
                
                # Store outputs for visualization and action queue
                gesture_out = gesture
                landmarks_out = image_landmarks # Pass 2D landmarks for drawing
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

        # Draw cursor reference (relative to video feed)
        if cursor_pos and self.config.visualization['show_cursor_position']:
            h, w, _ = frame.shape
            try:
                # Get virtual desktop origin and size
                screen_w = self.cursor_controller.screen_width
                screen_h = self.cursor_controller.screen_height
                origin_x = self.cursor_controller.origin_x + self.cursor_controller._coord_offset_x
                origin_y = self.cursor_controller.origin_y + self.cursor_controller._coord_offset_y

                # Map global cursor pos back to a 0-1 range
                norm_x = (cursor_pos[0] - origin_x) / (screen_w or 1)
                norm_y = (cursor_pos[1] - origin_y) / (screen_h or 1)
                
                # Map normalized pos to frame size
                feed_x = int(norm_x * w)
                feed_y = int(norm_y * h)

                cv2.circle(frame, (feed_x, feed_y), 5, (0, 255, 0), -1)
            except Exception as e:
                 self.logger.warning(f"Failed to draw cursor position: {e}")


        return frame