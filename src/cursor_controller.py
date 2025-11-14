# src/cursor_controller.py
import logging
from typing import Optional, Tuple

import numpy as np

# Keep the logger name consistent with existing logs
LOGGER_NAME = "src.cursor_controller"

# Optional screen enumeration for multi-monitor bounds
try:
    from screeninfo import get_monitors  # pip install screeninfo
except Exception:
    get_monitors = None

# Fallback to pyautogui.size() if screeninfo is not available
try:
    import pyautogui
    pyautogui.FAILSAFE = False
except Exception:
    pyautogui = None

# Reuse existing smoothing filters
from src.smoothing import KalmanFilter1D, MovingAverageFilter


class CursorController:
    """
    Backward-compatible cursor mapper and smoother.

    - Accepts legacy constructor params used by main.py/tests (e.g., smoothing_filter).
    - Provides update_position(landmarks) as before, so process thread doesn’t crash.
    - Auto-detects the full virtual desktop across multi-monitor layouts and clamps to reach all edges.
    """

    def __init__(
        self,
        # New-style names
        screen_width: Optional[int] = None,
        screen_height: Optional[int] = None,
        # Legacy names (some code may pass these)
        screenwidth: Optional[int] = None,
        screenheight: Optional[int] = None,
        # Kept for compatibility with main.py/config
        smoothing_filter: str = "kalman",
        # Optional origin (may be negative on extended desktops)
        origin_x: Optional[int] = None,
        origin_y: Optional[int] = None,
        logger: Optional[logging.Logger] = None,
        config: Optional[dict] = None,
        **kwargs,
    ) -> None:
        self.logger = logger or logging.getLogger(LOGGER_NAME)

        # Resolve provided dimensions first
        w = screen_width if screen_width is not None else screenwidth
        h = screen_height if screen_height is not None else screenheight

        # Detect full virtual desktop if anything is missing
        if w is None or h is None or origin_x is None or origin_y is None:
            ox, oy, vw, vh = self._detect_virtual_screen()
        else:
            ox, oy, vw, vh = int(origin_x), int(origin_y), int(w), int(h)

        self.origin_x = int(ox)
        self.origin_y = int(oy)
        self.screen_width = int(vw)
        self.screen_height = int(vh)

        # Smoothing filters (same behavior as original)
        if str(smoothing_filter).lower() == "kalman":
            self.filter_x = KalmanFilter1D()
            self.filter_y = KalmanFilter1D()
        else:
            self.filter_x = MovingAverageFilter()
            self.filter_y = MovingAverageFilter()

        # Keep prior aspect logs for continuity (camera often set 640x480 in main)
        self.camera_width = 640.0
        self.camera_height = 480.0
        self.camera_aspect = self.camera_width / self.camera_height
        self.screen_aspect = (self.screen_width / self.screen_height) if self.screen_height else 1.0

        # For compatibility with prior logs; mapping now uses full-fill, but we log the old calc
        if self.screen_aspect > self.camera_aspect:
            # Pillarbox case (screen wider than camera)
            map_w = self.screen_height * self.camera_aspect
            map_h = self.screen_height
            off_x = (self.screen_width - map_w) / 2
            off_y = 0
        else:
            # Letterbox case (screen taller than camera)
            map_w = self.screen_width
            map_h = self.screen_width / self.camera_aspect
            off_x = 0
            off_y = (self.screen_height - map_h) / 2

        # Logs mirror existing format so you’ll see consistent lines
        self.logger.info("CursorController initialized: %dx%d", self.screen_width, self.screen_height)
        self.logger.info("Aspect correction: Screen=%.2f, Cam=%.2f", self.screen_aspect, self.camera_aspect)
        self.logger.info("Mapping: Scale=(%d, %d), Offset=(%d, %d)", int(map_w), int(map_h), int(off_x), int(off_y))

    # ---------- public API (backward-compatible) ----------

    def update_position(self, landmarks: np.ndarray) -> Tuple[int, int]:
        """
        Compute smoothed, clamped screen coordinates from normalized landmarks.

        - Uses the middle finger tip (index 12) as before.
        - Mirrors X so rightward hand movement moves cursor right, matching original behavior.
        - Maps to the full virtual desktop bounds (multi-monitor safe) and clamps to edges.
        """
        middle = landmarks[12]  # [x, y, z?] in [0,1]
        x_norm_flipped = 1.0 - float(middle[0])
        y_norm = float(middle[1])

        # Map to virtual desktop
        x_abs, y_abs = self._map_normalized_to_screen(x_norm_flipped, y_norm)

        # Smooth
        x_s = self.filter_x.filter(x_abs)
        y_s = self.filter_y.filter(y_abs)

        # Clamp
        x_c = self._clamp_x(int(x_s))
        y_c = self._clamp_y(int(y_s))
        return x_c, y_c

    # ---------- internals ----------

    def _map_normalized_to_screen(self, nx: float, ny: float) -> Tuple[int, int]:
        nx = min(1.0, max(0.0, nx))
        ny = min(1.0, max(0.0, ny))
        x = self.origin_x + int(round(nx * (self.screen_width - 1)))
        y = self.origin_y + int(round(ny * (self.screen_height - 1)))
        return self._clip_to_bounds(x, y)

    def _clip_to_bounds(self, x: int, y: int) -> Tuple[int, int]:
        return self._clamp_x(x), self._clamp_y(y)

    def _clamp_x(self, x: int) -> int:
        min_x = self.origin_x
        max_x = self.origin_x + self.screen_width - 1
        return min(max_x, max(min_x, x))

    def _clamp_y(self, y: int) -> int:
        min_y = self.origin_y
        max_y = self.origin_y + self.screen_height - 1
        return min(max_y, max(min_y, y))

    def _detect_virtual_screen(self) -> Tuple[int, int, int, int]:
        """
        Returns (origin_x, origin_y, width, height) of the full virtual desktop.
        Prefers screeninfo (captures negative origins) and falls back to pyautogui.size().
        """
        if get_monitors:
            try:
                mons = get_monitors()
                if mons:
                    min_x = min(m.x for m in mons)
                    min_y = min(m.y for m in mons)
                    max_x = max(m.x + m.width for m in mons)
                    max_y = max(m.y + m.height for m in mons)
                    ox, oy = int(min_x), int(min_y)
                    w, h = int(max_x - min_x), int(max_y - min_y)
                    try:
                        layout = "; ".join([f"{m.name or 'mon'} @{m.x},{m.y} {m.width}x{m.height}" for m in mons])
                    except Exception:
                        layout = f"{len(mons)} monitors"
                    self.logger.info("Detected virtual desktop: origin=%d,%d size=%dx%d | %s", ox, oy, w, h, layout)
                    return ox, oy, w, h
            except Exception:
                # Fall through to pyautogui
                pass

        if pyautogui is not None:
            size = pyautogui.size()
            return 0, 0, int(size.width), int(size.height)

        # Conservative default
        return 0, 0, 1920, 1080
