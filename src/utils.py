# ============================================================================
# UTILITY FUNCTIONS & HELPERS
# ============================================================================

import logging
import numpy as np
import cv2
from pathlib import Path
from typing import Tuple
import pyautogui


def setup_logging(log_level: str = "INFO", log_file: str = None):
    """Setup logging configuration"""
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, log_level))
    
    # Console handler
    console = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console.setFormatter(formatter)
    logger.addHandler(console)
    
    # File handler (optional)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)


def get_screen_size() -> Tuple[int, int]:
    """Get screen resolution"""
    return pyautogui.size()


def euclidean_distance(point1: np.ndarray, point2: np.ndarray) -> float:
    """Calculate Euclidean distance between two 3D points"""
    return np.linalg.norm(point1 - point2)


def draw_landmarks(frame: np.ndarray, landmarks: np.ndarray, 
                  color: Tuple = (0, 255, 0), radius: int = 4) -> np.ndarray:
    """Draw hand landmarks on frame"""
    h, w, _ = frame.shape
    for lm in landmarks:
        x, y = int(lm[0] * w), int(lm[1] * h)
        cv2.circle(frame, (x, y), radius, color, -1)
    return frame


def draw_hand_connections(frame: np.ndarray, landmarks: np.ndarray,
                         color: Tuple = (255, 0, 0)) -> np.ndarray:
    """Draw hand skeleton connections"""
    connections = [
        (0, 1), (1, 2), (2, 3), (3, 4),
        (0, 5), (5, 6), (6, 7), (7, 8),
        (0, 9), (9, 10), (10, 11), (11, 12),
        (0, 13), (13, 14), (14, 15), (15, 16),
        (0, 17), (17, 18), (18, 19), (19, 20),
    ]
    
    h, w, _ = frame.shape
    for start, end in connections:
        p1 = (int(landmarks[start][0] * w), int(landmarks[start][1] * h))
        p2 = (int(landmarks[end][0] * w), int(landmarks[end][1] * h))
        cv2.line(frame, p1, p2, color, 2)
    
    return frame
