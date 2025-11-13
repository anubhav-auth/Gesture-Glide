# src/hand_tracker.py
import logging
from typing import Any, Dict, Optional, Tuple, List

import cv2
import numpy as np

try:
    import mediapipe as mp
except ImportError:  # Graceful degradation if mediapipe isn't installed
    mp = None  # type: ignore[assignment]

class HandTracker:
    """
    MediaPipe-based hand tracker.
    Can be constructed with a Config-like object (having a 'system'/'hand_tracking' section)
    or with explicit constructor parameters.
    """
    def __init__(
        self,
        config_or_detection_confidence: Any = 0.7,
        tracking_confidence: float = 0.7,
        model_complexity: int = 0,
        max_num_hands: int = 1,
    ) -> None:
        self.logger = logging.getLogger(__name__)

        # Support "HandTracker(config)" OR explicit numeric args
        if isinstance(config_or_detection_confidence, (int, float)):
            detection_confidence = float(config_or_detection_confidence)
        else:
            # Config-like; be robust to both snake_case and camelcase keys
            cfg: Any = config_or_detection_confidence
            hand_cfg: Dict[str, Any] = {}
            if hasattr(cfg, "hand_tracking"):
                hand_cfg = getattr(cfg, "hand_tracking")  # type: ignore[assignment]
            elif hasattr(cfg, "handtracking"):
                hand_cfg = getattr(cfg, "handtracking")  # type: ignore[assignment]
            elif isinstance(cfg, dict) and "hand_tracking" in cfg:
                hand_cfg = cfg["hand_tracking"]  # type: ignore[assignment]
            detection_confidence = float(hand_cfg.get("detection_confidence", 0.7))
            tracking_confidence = float(hand_cfg.get("tracking_confidence", 0.7))
            model_complexity = int(hand_cfg.get("model_complexity", 0))
            max_num_hands = int(hand_cfg.get("max_num_hands", 1))

        if mp is None:
            self.logger.warning("mediapipe not available; HandTracker disabled")
            self._hands = None
            return

        # Use the public API that Pylance recognizes
        mp_hands = mp.solutions.hands  # type: ignore[attr-defined]
        self._hands = mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=max_num_hands,
            min_detection_confidence=detection_confidence,
            min_tracking_confidence=tracking_confidence,
            model_complexity=model_complexity,
        )
        self.logger.info(f"HandTracker initialized (max_num_hands={max_num_hands})")

    def detect(self, frame: np.ndarray) -> List[Tuple[np.ndarray, np.ndarray, str, float]]:
        """
        Detect one or more hands and return a list of tuples:
        - image_landmarks: np.ndarray of shape (21, 3) in normalized image coordinates
        - world_landmarks: np.ndarray of shape (21, 3) in real-world meters
        - handedness: "Left" or "Right"
        - confidence: score for the classified hand
        """
        if self._hands is None:
            return []

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self._hands.process(rgb)
        
        # Updated list to hold the new tuple structure
        detected_hands: List[Tuple[np.ndarray, np.ndarray, str, float]] = []
        
        # Ensure all required data is present
        if results.multi_hand_landmarks and results.multi_handedness and results.multi_hand_world_landmarks:
            for hand_landmarks, hand_world_landmarks, handedness_data in zip(
                results.multi_hand_landmarks,
                results.multi_hand_world_landmarks, # <-- Get world landmarks
                results.multi_handedness
            ):
                # 1. Image landmarks (for cursor/visualization)
                lm_list = hand_landmarks.landmark
                image_landmarks = np.array([[lm.x, lm.y, lm.z] for lm in lm_list], dtype=np.float32)
                
                # 2. World landmarks (for gesture detection)
                world_lm_list = hand_world_landmarks.landmark
                world_landmarks = np.array([[lm.x, lm.y, lm.z] for lm in world_lm_list], dtype=np.float32)

                # 3. Handedness and confidence
                handedness = handedness_data.classification[0].label
                confidence = float(handedness_data.classification[0].score)
                
                # Append both sets of landmarks
                detected_hands.append((image_landmarks, world_landmarks, handedness, confidence))

        return detected_hands
    def close(self) -> None:
        if self._hands is not None:
            self._hands.close()