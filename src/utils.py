# src/utils.py
import logging
from typing import Optional, Tuple
import cv2
import numpy as np


# MediaPipe hand landmark connections (21 landmarks, indices 0-20)
HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),  # Thumb
    (0, 5), (5, 6), (6, 7), (7, 8),  # Index finger
    (0, 9), (9, 10), (10, 11), (11, 12),  # Middle finger
    (0, 13), (13, 14), (14, 15), (15, 16),  # Ring finger
    (0, 17), (17, 18), (18, 19), (19, 20),  # Pinky
    (5, 9), (9, 13), (13, 17)  # Palm connections
]


def setup_logging(log_level: str = "INFO", log_file: Optional[str] = None) -> logging.Logger:
    """
    Configure root logging once with optional file handler.
    - log_level: "DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL"
    - log_file: path to file or None to disable file logging
    """
    logger = logging.getLogger()
    # Avoid duplicate handlers if called multiple times
    if not logger.handlers:
        level = getattr(logging, log_level.upper(), logging.INFO)
        logger.setLevel(level)

        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

        console = logging.StreamHandler()
        console.setFormatter(formatter)
        logger.addHandler(console)

        if log_file:
            try:
                file_handler = logging.FileHandler(log_file)
                file_handler.setFormatter(formatter)
                logger.addHandler(file_handler)
            except Exception as e:
                logger.warning(f"Failed to attach file handler: {e}")

    else:
        # If handlers exist, still honor a level change
        level = getattr(logging, log_level.upper(), logging.INFO)
        logger.setLevel(level)

    return logger


def get_screen_size() -> Tuple[int, int]:
    """Return the primary screen resolution as (width, height)."""
    try:
        import pyautogui
        size = pyautogui.size()
        return (int(size.width), int(size.height))
    except Exception:
        # Safe fallback when GUI is not available (e.g., headless CI)
        return (1920, 1080)


def euclidean_distance(point1, point2) -> float:
    """Compute Euclidean distance between two 3D points or arrays."""
    try:
        import numpy as np
        p1 = np.asarray(point1, dtype=float)
        p2 = np.asarray(point2, dtype=float)
        return float(np.linalg.norm(p1 - p2))
    except Exception:
        # Minimal fallback if numpy is unavailable for some reason
        x1, y1, *rest1 = point1
        x2, y2, *rest2 = point2
        z1 = rest1[0] if rest1 else 0.0
        z2 = rest2[0] if rest2 else 0.0
        dx = float(x1) - float(x2)
        dy = float(y1) - float(y2)
        dz = float(z1) - float(z2)
        return (dx * dx + dy * dy + dz * dz) ** 0.5


def draw_hand_connections(
    frame: np.ndarray, 
    landmarks: np.ndarray, 
    color: Tuple[int, int, int] = (0, 255, 255),
    thickness: int = 2
) -> None:
    """
    Draw lines connecting hand landmarks to form the hand skeleton.
    
    Args:
        frame: The image frame to draw on (modified in-place)
        landmarks: Array of shape (21, 2) or (21, 3) with landmark coordinates
        color: BGR color tuple for the connection lines
        thickness: Line thickness in pixels
    """
    if landmarks is None or len(landmarks) < 21:
        return
    
    h, w = frame.shape[:2]
    
    # Convert normalized coordinates to pixel coordinates if needed
    points = []
    for landmark in landmarks:
        if landmark[0] <= 1.0 and landmark[1] <= 1.0:
            # Normalized coordinates
            x = int(landmark[0] * w)
            y = int(landmark[1] * h)
        else:
            # Already pixel coordinates
            x = int(landmark[0])
            y = int(landmark[1])
        points.append((x, y))
    
    # Draw connections between landmarks
    for connection in HAND_CONNECTIONS:
        start_idx, end_idx = connection
        if start_idx < len(points) and end_idx < len(points):
            start_point = points[start_idx]
            end_point = points[end_idx]
            cv2.line(frame, start_point, end_point, color, thickness, lineType=cv2.LINE_AA)


def draw_landmarks(
    frame: np.ndarray,
    landmarks: np.ndarray,
    color: Tuple[int, int, int] = (0, 0, 255),
    radius: int = 4
) -> None:
    """
    Draw circles at each hand landmark position.
    
    Args:
        frame: The image frame to draw on (modified in-place)
        landmarks: Array of shape (21, 2) or (21, 3) with landmark coordinates
        color: BGR color tuple for the landmark circles
        radius: Radius of circles in pixels
    """
    if landmarks is None or len(landmarks) == 0:
        return
    
    h, w = frame.shape[:2]
    
    for landmark in landmarks:
        if landmark[0] <= 1.0 and landmark[1] <= 1.0:
            # Normalized coordinates
            x = int(landmark[0] * w)
            y = int(landmark[1] * h)
        else:
            # Already pixel coordinates
            x = int(landmark[0])
            y = int(landmark[1])
        
        cv2.circle(frame, (x, y), radius, color, -1, lineType=cv2.LINE_AA)


__all__ = [
    "setup_logging", 
    "get_screen_size", 
    "euclidean_distance",
    "draw_hand_connections",
    "draw_landmarks",
    "HAND_CONNECTIONS"
]
