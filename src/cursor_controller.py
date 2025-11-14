# src/cursor_controller.py
import logging
import time
import math
import platform
import re
import subprocess
from typing import Any, Optional, Tuple

import numpy as np

LOGGER_NAME = "src.cursor_controller"

# Preferred: screeninfo
try:
    from screeninfo import get_monitors  # pip install screeninfo
except Exception:
    get_monitors = None

# Fallback mouse control
try:
    import pyautogui
    pyautogui.FAILSAFE = False
except Exception:
    pyautogui = None

from src.smoothing import KalmanFilter1D, MovingAverageFilter, EMAFilter1D


class CursorController:
    """
    Multi-monitor aware, dynamic, and high-sensitivity cursor controller.

    - Absolute mode: normalized → full virtual desktop. 
    - Relative mode: mouse-like deltas with sensitivity, acceleration, deadzone, and EMA stabilization.
    - Dynamic layout refresh: re-detects monitors periodically to follow OS display changes.
    - Linux guard: normalizes negative origins so pointer can reach all screens on common X/Wayland stacks.
    """

    def __init__(
        self,
        # New-style dims
        screen_width: Optional[int] = None,
        screen_height: Optional[int] = None,
        # Legacy compatibility
        screenwidth: Optional[int] = None,
        screenheight: Optional[int] = None,
        smoothing_filter: str = "kalman",
        # Optional explicit origin (rare)
        origin_x: Optional[int] = None,
        origin_y: Optional[int] = None,
        # Config bundle (optional)
        config: Optional[dict] = None,
        logger: Optional[logging.Logger] = None,
        **kwargs,
    ) -> None:
        self.logger = logger or logging.getLogger(LOGGER_NAME)
        self._os = platform.system()

        w = screen_width if screen_width is not None else screenwidth
        h = screen_height if screen_height is not None else screenheight
        if w is None or h is None or origin_x is None or origin_y is None:
            ox, oy, vw, vh, offx, offy = self._detect_virtual_screen()
        else:
            ox, oy, vw, vh = int(origin_x), int(origin_y), int(w), int(h)
            offx, offy = 0, 0

        # Public attributes
        self.origin_x = int(ox)
        self.origin_y = int(oy)
        self.screen_width = int(vw)
        self.screen_height = int(vh)

        # Internal offsets to normalize negative origins on platforms that dislike them (Linux)
        self._coord_offset_x = int(offx)
        self._coord_offset_y = int(offy)

        # Camera/log info (unchanged behavior)
        self.camera_width = 640.0
        self.camera_height = 480.0
        self.camera_aspect = self.camera_width / self.camera_height
        self.screen_aspect = (self.screen_width / self.screen_height) if self.screen_height else 1.0

        map_w, map_h, off_x, off_y = self._aspect_map_for_logs()
        self.logger.info("CursorController initialized: %dx%d (origin %d,%d, offset %d,%d)",
                         self.screen_width, self.screen_height, self.origin_x, self.origin_y,
                         self._coord_offset_x, self._coord_offset_y)
        self.logger.info("Aspect correction: Screen=%.2f, Cam=%.2f", self.screen_aspect, self.camera_aspect)
        self.logger.info("Mapping: Scale=(%d, %d), Offset=(%d, %d)", map_w, map_h, off_x, off_y)

        cc = (config or {}).get("cursor_control", {}) if config else {}

        # Final position filter
        if str(smoothing_filter).lower() == "kalman":
            pn = cc.get("kalman_process_noise", 0.1)
            mn = cc.get("kalman_measurement_noise", 4.0)
            self.filter_x = KalmanFilter1D(process_noise=pn, measurement_noise=mn)
            self.filter_y = KalmanFilter1D(process_noise=pn, measurement_noise=mn)
        else:
            win = cc.get("moving_average_window", 5)
            self.filter_x = MovingAverageFilter(window_size=win)
            self.filter_y = MovingAverageFilter(window_size=win)

        # Control mode and sensitivity defaults tuned higher to reduce hand travel
        mode = str(cc.get("control_mode", "relative")).lower()
        self.use_relative = (mode == "relative")
        self.sensitivity = float(cc.get("sensitivity", 2.4))          # higher base gain
        self.acceleration = float(cc.get("acceleration", 1.5))        # stronger accel
        self.accel_exponent = float(cc.get("accel_exponent", 1.4))
        self.max_gain = float(cc.get("max_gain", 8.0))
        self.low_speed_threshold = float(cc.get("low_speed_threshold", 0.15))
        self.low_speed_boost = float(cc.get("low_speed_boost", 0.55)) # keeps fine control
        self.deadz = float(cc.get("deadzone_norm", 0.006))            # suppress micro jitter
        self.speed_multiplier = float(cc.get("speed_multiplier", cc.get("speed", 1.0)))

        # EMA stabilizer on deltas
        self.stabilizer_enabled = bool(cc.get("stabilizer_enabled", True))
        self.stabilizer_alpha = float(cc.get("stabilizer_alpha", 0.25))
        self._ema_dx = EMAFilter1D(self.stabilizer_alpha) if self.stabilizer_enabled else None
        self._ema_dy = EMAFilter1D(self.stabilizer_alpha) if self.stabilizer_enabled else None

        # Dynamic re-detect interval (seconds)
        self._refresh_secs = float(cc.get("display_refresh_seconds", 5.0))
        self._last_detect_ts = 0.0

        # Relative state
        self._last_norm_x: Optional[float] = None
        self._last_norm_y: Optional[float] = None
        self._last_abs_x: Optional[float] = None
        self._last_abs_y: Optional[float] = None
        self._last_ts: Optional[float] = None

    # ---------- public API ----------

    def update_position(self, landmarks: np.ndarray) -> Tuple[int, int]:
        # Periodically re-detect display layout to follow OS changes without restart
        self._maybe_refresh_virtual_screen()  # cheap when interval not elapsed

        middle = landmarks[12]
        nx = 1.0 - float(middle[0])  # flip X for natural movement
        ny = float(middle[1])

        if not self.use_relative:
            x_abs, y_abs = self._map_normalized_to_screen(nx, ny)
            x_s = self.filter_x.filter(x_abs)
            y_s = self.filter_y.filter(y_abs)
            x_c, y_c = self._clip_to_bounds(int(x_s), int(y_s))
            self._seed_relative_state(nx, ny, x_c, y_c)
            return x_c, y_c

        now = time.perf_counter()
        if self._last_norm_x is None or self._last_norm_y is None:
            x0, y0 = self._current_pointer_or_center()
            self._seed_relative_state(nx, ny, x0, y0)
            return x0, y0

        dt = max(1e-3, (now - (self._last_ts or now)))
        dx_n = nx - self._last_norm_x
        dy_n = ny - self._last_norm_y

        # Deadzone
        if abs(dx_n) < self.deadz:
            dx_n = 0.0
        if abs(dy_n) < self.deadz:
            dy_n = 0.0

        if dx_n == 0.0 and dy_n == 0.0:
            if self._last_abs_x is None or self._last_abs_y is None:
                x0, y0 = self._current_pointer_or_center()
                self._seed_relative_state(nx, ny, x0, y0)
                return x0, y0
            return int(self._last_abs_x), int(self._last_abs_y)

        speed_norm = math.hypot(dx_n, dy_n) / dt

        gain = self.sensitivity
        if self.acceleration > 0.0:
            gain *= (1.0 + self.acceleration * (speed_norm ** self.accel_exponent))
        if speed_norm < self.low_speed_threshold:
            gain *= self.low_speed_boost
        gain *= self.speed_multiplier
        gain = min(self.max_gain, max(0.1, gain))

        sx = (self.screen_width - 1)
        sy = (self.screen_height - 1)
        dx_px = dx_n * sx * gain
        dy_px = dy_n * sy * gain

        if self._ema_dx is not None:
            dx_px = self._ema_dx.filter(dx_px)
        if self._ema_dy is not None:
            dy_px = self._ema_dy.filter(dy_px)

        base_x = self._last_abs_x if self._last_abs_x is not None else (self.origin_x + self.screen_width // 2)
        base_y = self._last_abs_y if self._last_abs_y is not None else (self.origin_y + self.screen_height // 2)
        x_abs = float(base_x) + dx_px
        y_abs = float(base_y) + dy_px

        x_s = self.filter_x.filter(x_abs)
        y_s = self.filter_y.filter(y_abs)
        x_c, y_c = self._clip_to_bounds(int(x_s), int(y_s))

        self._last_norm_x, self._last_norm_y = nx, ny
        self._last_abs_x, self._last_abs_y = float(x_c), float(y_c)
        self._last_ts = now
        return x_c, y_c

    def map_normalized_to_screen(self, nx: float, ny: float) -> Tuple[int, int]:
        return self._map_normalized_to_screen(nx, ny)

    def move_to_normalized(self, nx: float, ny: float) -> None:
        if pyautogui is None:
            raise RuntimeError("pyautogui is required for cursor movement but is not available")
        x, y = self._map_normalized_to_screen(nx, ny)
        pyautogui.moveTo(x, y)

    # ---------- internals ----------

    def _maybe_refresh_virtual_screen(self) -> None:
        now = time.perf_counter()
        if (now - self._last_detect_ts) < self._refresh_secs:
            return
        self._last_detect_ts = now
        ox, oy, vw, vh, offx, offy = self._detect_virtual_screen()
        # Only update if changed (avoid extra log noise)
        if (ox != self.origin_x) or (oy != self.origin_y) or (vw != self.screen_width) or (vh != self.screen_height) or \
           (offx != self._coord_offset_x) or (offy != self._coord_offset_y):
            self.origin_x, self.origin_y = int(ox), int(oy)
            self.screen_width, self.screen_height = int(vw), int(vh)
            self._coord_offset_x, self._coord_offset_y = int(offx), int(offy)
            self.logger.info("Display layout refreshed: %dx%d origin %d,%d offset %d,%d",
                             self.screen_width, self.screen_height, self.origin_x, self.origin_y,
                             self._coord_offset_x, self._coord_offset_y)
            # Re-clamp last positions
            if self._last_abs_x is not None and self._last_abs_y is not None:
                xc, yc = self._clip_to_bounds(int(self._last_abs_x), int(self._last_abs_y))
                self._last_abs_x, self._last_abs_y = float(xc), float(yc)

    def _seed_relative_state(self, nx: float, ny: float, x_abs: int, y_abs: int) -> None:
        self._last_norm_x = float(nx)
        self._last_norm_y = float(ny)
        self._last_abs_x = float(x_abs)
        self._last_abs_y = float(y_abs)
        self._last_ts = time.perf_counter()
        if self._ema_dx is not None:
            self._ema_dx.reset(0.0)
        if self._ema_dy is not None:
            self._ema_dy.reset(0.0)
        if hasattr(self.filter_x, "reset"):
            try:
                self.filter_x.reset()
            except TypeError:
                pass
        if hasattr(self.filter_y, "reset"):
            try:
                self.filter_y.reset()
            except TypeError:
                pass
        self.filter_x.filter(float(x_abs))
        self.filter_y.filter(float(y_abs))

    def _current_pointer_or_center(self) -> Tuple[int, int]:
        if pyautogui is not None:
            try:
                pos = pyautogui.position()
                return int(pos.x), int(pos.y)
            except Exception:
                pass
        return (self.origin_x + self.screen_width // 2, self.origin_y + self.screen_height // 2)

    def _map_normalized_to_screen(self, nx: float, ny: float) -> Tuple[int, int]:
        nx = min(1.0, max(0.0, float(nx)))
        ny = min(1.0, max(0.0, float(ny)))
        # Apply Linux normalization offsets to ensure non-negative coordinates where needed
        x = self.origin_x + int(round(nx * (self.screen_width - 1))) + self._coord_offset_x
        y = self.origin_y + int(round(ny * (self.screen_height - 1))) + self._coord_offset_y
        return self._clip_to_bounds(x, y)

    def _clip_to_bounds(self, x: int, y: int) -> Tuple[int, int]:
        min_x = self.origin_x + self._coord_offset_x
        min_y = self.origin_y + self._coord_offset_y
        max_x = self.origin_x + self._coord_offset_x + self.screen_width - 1
        max_y = self.origin_y + self._coord_offset_y + self.screen_height - 1
        x = min(max_x, max(min_x, x))
        y = min(max_y, max(min_y, y))
        return x, y

    def _detect_virtual_screen(self) -> Tuple[int, int, int, int, int, int]:
        """
        Returns (origin_x, origin_y, width, height, offset_x, offset_y).
        offset_x/offset_y are applied to normalize negative origins on Linux.
        """
        # 1) screeninfo (best cross-platform with x,y per monitor)
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
                    offx, offy = self._normalize_offsets_for_os(ox, oy)
                    try:
                        layout = "; ".join([f"{m.name or 'mon'} @{m.x},{m.y} {m.width}x{m.height}" for m in mons])
                    except Exception:
                        layout = f"{len(mons)} monitors"
                    self.logger.info("Detected virtual desktop: origin=%d,%d size=%dx%d | %s", ox, oy, w, h, layout)
                    return ox, oy, w, h, offx, offy
            except Exception:
                pass

        # 2) OS-specific fallbacks
        sysname = self._os

        # Windows: use virtual screen metrics
        if sysname == "Windows":
            try:
                import ctypes as _ctypes  
                _windll: Any = getattr(_ctypes, "windll", None)  
                if _windll is not None:
                    user32 = _windll.user32
                    SM_XVIRTUALSCREEN = 76  
                    SM_YVIRTUALSCREEN = 77  
                    SM_CXVIRTUALSCREEN = 78  
                    SM_CYVIRTUALSCREEN = 79  
                    ox = int(user32.GetSystemMetrics(SM_XVIRTUALSCREEN))  
                    oy = int(user32.GetSystemMetrics(SM_YVIRTUALSCREEN))  
                    w = int(user32.GetSystemMetrics(SM_CXVIRTUALSCREEN))  
                    h = int(user32.GetSystemMetrics(SM_CYVIRTUALSCREEN))  
                    return ox, oy, w, h, 0, 0  
            except Exception:
                pass

        # Linux: parse xrandr when available (captures top/left layouts)
        if sysname == "Linux":
            try:
                out = subprocess.run(["xrandr", "--current"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=1.5)
                txt = out.stdout
                # Lines like: "HDMI-1 connected primary 1920x1080+0+0 ..."
                # or "DP-1 connected 2560x1440+1920-200 ..."
                rects = []
                for line in txt.splitlines():
                    if " connected" in line and ("+" in line) and ("x" in line):
                        m = re.search(r"(\d+)x(\d+)\+(-?\d+)\+(-?\d+)", line)
                        if m:
                            w0, h0, x0, y0 = map(int, m.groups())
                            rects.append((x0, y0, w0, h0))
                if rects:
                    min_x = min(x for x, y, w0, h0 in rects)
                    min_y = min(y for x, y, w0, h0 in rects)
                    max_x = max(x + w0 for x, y, w0, h0 in rects)
                    max_y = max(y + h0 for x, y, w0, h0 in rects)
                    ox, oy = int(min_x), int(min_y)
                    w = int(max_x - min_x)
                    h = int(max_y - min_y)
                    offx, offy = self._normalize_offsets_for_os(ox, oy)
                    return ox, oy, w, h, offx, offy
            except Exception:
                pass

        # 3) pyautogui primary/virtual size as last resort
        if pyautogui is not None:
            try:
                sz = pyautogui.size()
                return 0, 0, int(sz.width), int(sz.height), 0, 0
            except Exception:
                pass

        # Conservative default
        return 0, 0, 1920, 1080, 0, 0

    def _normalize_offsets_for_os(self, ox: int, oy: int) -> Tuple[int, int]:
        """
        On Linux (X11/Wayland), some stacks don't accept negative global coords via high-level libs.
        Apply a positive offset so all cursor positions are >= 0, preserving full reach.
        """
        if self._os == "Linux" and (ox < 0 or oy < 0):
            return -ox, -oy
        return 0, 0

    def _aspect_map_for_logs(self) -> Tuple[int, int, int, int]:
        if self.screen_aspect >= self.camera_aspect:
            map_h = self.screen_height
            map_w = int(round(self.camera_aspect * map_h))
            off_x = int((self.screen_width - map_w) / 2)
            off_y = 0
        else:
            map_w = self.screen_width
            map_h = int(round(map_w / self.camera_aspect))
            off_x = 0
            off_y = int((self.screen_height - map_h) / 2)
        return map_w, map_h, off_x, off_y
