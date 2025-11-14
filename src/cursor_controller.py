# src/cursor_controller.py
import logging
from typing import Optional, Tuple

# Prefer the legacy logger name for continuity in logs
_LOGGER_NAME = "src.cursorcontroller"

try:
    from screeninfo import get_monitors  # pip install screeninfo
except Exception:
    get_monitors = None

try:
    import pyautogui
    pyautogui.FAILSAFE = False
except Exception:
    pyautogui = None


class CursorController:
    """
    Map normalized [0..1] hand coordinates to absolute OS pixels over the FULL
    virtual desktop (all monitors combined). Backward-compatible with older
    constructor parameters and attribute names used elsewhere in the app.
    """

    def __init__(
        self,
        # Legacy names kept for compatibility with tests and main.py
        screenwidth: Optional[int] = None,
        screenheight: Optional[int] = None,
        # Optional origin for virtual desktop (usually 0,0; may be negative on some OS layouts)
        origin_x: Optional[int] = None,
        origin_y: Optional[int] = None,
        # Kept for compatibility; smoothing is handled upstream or ignored here
        smoothing_filter: Optional[str] = None,
        # Optional extras that main/config might pass; safely ignored if unused
        logger: Optional[logging.Logger] = None,
        config: Optional[dict] = None,
        camera_aspect: Optional[float] = None,
        speed_multiplier: Optional[float] = None,
        **kwargs,
    ) -> None:
        # Use a stable logger name to match previous log output
        self.log = logger or logging.getLogger(_LOGGER_NAME)

        # Detect the combined virtual desktop if not provided
        if screenwidth is None or screenheight is None or origin_x is None or origin_y is None:
            ox, oy, w, h = self._detect_virtual_screen()
        else:
            ox, oy, w, h = int(origin_x), int(origin_y), int(screenwidth), int(screenheight)

        # Backward-compatible public attributes (legacy names without underscores)
        self.origin_x = int(ox)
        self.origin_y = int(oy)
        self.screenwidth = int(w)
        self.screenheight = int(h)

        # Optional: preserve “aspect correction” logs for continuity, but default to full fill mapping
        self._screen_ar = (self.screenwidth / self.screenheight) if self.screenheight else 1.0
        self._cam_ar = float(camera_aspect) if camera_aspect and camera_aspect > 0 else 4.0 / 3.0

        # Aspect-correct letterbox/pillarbox was causing unreachable edges before; default to fill
        self._aspect_mode = "fill"  # alternatives: "letterbox", "pillarbox"
        # Compute scale/offset used only for logging and potential future modes
        if self._aspect_mode == "fill":
            map_w, map_h = self.screenwidth, self.screenheight
            off_x, off_y = 0, 0
        else:
            # Example pillarbox when screen AR > cam AR (kept for reference)
            if self._screen_ar >= self._cam_ar:
                map_h = self.screenheight
                map_w = int(round(self._cam_ar * map_h))
                off_x = int((self.screenwidth - map_w) / 2)
                off_y = 0
            else:
                map_w = self.screenwidth
                map_h = int(round(map_w / self._cam_ar))
                off_x = 0
                off_y = int((self.screenheight - map_h) / 2)

        self.log.info(
            "CursorController initialized %dx%d",
            self.screenwidth, self.screenheight
        )
        self.log.info("Aspect correction: Screen=%.2f, Cam=%.2f", self._screen_ar, self._cam_ar)
        self.log.info("Mapping: Scale=%d,%d, Offset=%d,%d", map_w, map_h, off_x, off_y)

        # Store a no-op of smoothing_filter for compatibility
        self._smoothing_filter_name = str(smoothing_filter).lower() if smoothing_filter else None
        self._speed_multiplier = float(speed_multiplier) if speed_multiplier else 1.0
        self._config = config or {}

    # ---------- public API ----------

    def map_normalized_to_screen(self, nx: float, ny: float) -> Tuple[int, int]:
        """
        Clamp normalized coordinates to [0..1], map to absolute virtual desktop pixels,
        and clip to the full bounds so every corner is reachable.
        """
        nx = min(1.0, max(0.0, float(nx)))
        ny = min(1.0, max(0.0, float(ny)))

        # Full-fill mapping to the entire virtual desktop
        x = self.origin_x + int(round(nx * (self.screenwidth - 1)))
        y = self.origin_y + int(round(ny * (self.screenheight - 1)))
        return self._clip_to_bounds(x, y)

    def move_to_normalized(self, nx: float, ny: float) -> None:
        """
        Move the OS cursor to the given normalized position across the full virtual desktop.
        """
        if pyautogui is None:
            raise RuntimeError("pyautogui is required for cursor movement but is not available")
        x, y = self.map_normalized_to_screen(nx, ny)
        pyautogui.moveTo(x, y)

    def move_with_landmarks(self, landmarks, landmark_index: int = 12) -> None:
        """
        Convenience: use a landmark (default middle finger tip idx=12) to position the cursor.
        """
        nx = float(landmarks[landmark_index][0])
        ny = float(landmarks[landmark_index][1])
        self.move_to_normalized(nx, ny)

    # ---------- internals ----------

    def _detect_virtual_screen(self) -> Tuple[int, int, int, int]:
        """
        Returns (origin_x, origin_y, width, height) of the full virtual desktop.
        Prefers screeninfo for multi-monitor layouts; falls back to pyautogui.size().
        """
        # screeninfo captures per-monitor rectangles with potential negative origins
        if get_monitors:
            mons = get_monitors()
            if mons:
                min_x = min(m.x for m in mons)
                min_y = min(m.y for m in mons)
                max_x = max(m.x + m.width for m in mons)
                max_y = max(m.y + m.height for m in mons)
                ox = int(min_x)
                oy = int(min_y)
                w = int(max_x - min_x)
                h = int(max_y - min_y)
                self._log_layout(mons, ox, oy, w, h)
                return ox, oy, w, h

        # Fallback: primary screen only
        if pyautogui is not None:
            size = pyautogui.size()
            return 0, 0, int(size.width), int(size.height)

        # Last resort defaults
        return 0, 0, 1920, 1080

    def _clip_to_bounds(self, x: int, y: int) -> Tuple[int, int]:
        min_x = self.origin_x
        min_y = self.origin_y
        max_x = self.origin_x + self.screenwidth - 1
        max_y = self.origin_y + self.screenheight - 1
        x = min(max_x, max(min_x, x))
        y = min(max_y, max(min_y, y))
        return x, y

    def _log_layout(self, mons, ox: int, oy: int, w: int, h: int) -> None:
        try:
            layout = "; ".join([f"{m.name or 'mon'} @{m.x},{m.y} {m.width}x{m.height}" for m in mons])
        except Exception:
            layout = f"{len(mons)} monitors"
        self.log.info("Detected virtual desktop: origin=%d,%d size=%dx%d | %s", ox, oy, w, h, layout)
