# ============================================================================
# HAND TRACKING
# ============================================================================

import mediapipe as mp
import logging
import cv2
import numpy as np
from typing import Tuple, Optional


class HandTracker:
    """MediaPipe-based hand tracking"""
    
    def __init__(self, detection_confidence: float = 0.7, 
                 tracking_confidence: float = 0.7,
                 model_complexity: int = 0,
                 max_num_hands: int = 1):
        self.logger = logging.getLogger(__name__)
        
        mp_hands = mp.solutions.hands
        self.hands = mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=max_num_hands,
            min_detection_confidence=detection_confidence,
            min_tracking_confidence=tracking_confidence,
            model_complexity=model_complexity
        )
        self.logger.info("HandTracker initialized")
    
    def detect(self, frame: np.ndarray) -> Tuple[Optional[np.ndarray], Optional[str], float]:
        """Detect hand landmarks"""
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.hands.process(rgb_frame)
        
        if results.multi_hand_landmarks and results.multi_handedness:
            landmarks = np.array([
                [lm.x, lm.y, lm.z] 
                for lm in results.multi_hand_landmarks[0].landmark
            ])
            handedness = results.multi_handedness[0].classification[0].label
            confidence = results.multi_handedness[0].classification[0].score
            return landmarks, handedness, confidence
        
        return None, None, 0.0