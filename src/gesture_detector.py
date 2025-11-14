# src/gesture_detector.py
import time
import math
import logging
from dataclasses import dataclass
from typing import Dict, Optional, Sequence

# Landmark indices (MediaPipe Hands)
INDEX_TIP = 8
MIDDLE_TIP = 12
RING_TIP = 16

@dataclass
class _PinchState:
    is_pinched: bool = False
    last_click_ts: float = 0.0
    press_started_ts: float = 0.0
    ema_baseline: Optional[float] = None  # adaptive "open" distance
    ema_dist: Optional[float] = None      # smoothed current distance

class GestureDetector:
    """
    Pinch detection with:
    - EMA smoothing of distances
    - Adaptive per-user baseline when fingers are open
    - Hysteresis (separate in/out thresholds on the distance ratio)
    - Time debouncing for clean edge-triggered click events
    Emits: "LEFT_CLICK", "RIGHT_CLICK", "MIDDLE_CLICK" or None
    """
    def __init__(
        self,
        config: Optional[dict] = None,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        self.log = logger or logging.getLogger(__name__)
        cfg = config or {}

        gd = (cfg.get("gesture_detection") or {})
        # Debounce between clicks
        self.click_debounce_ms: int = int(gd.get("click_debounce_ms", 120))
        # Minimum time finger distance must remain closed before we accept a pinch edge
        self.min_press_ms: int = int(gd.get("drag_hold_threshold_ms", 60))
        # EMA smoothing factor (lower -> more smoothing)
        self.ema_alpha: float = float(gd.get("ema_alpha", 0.25))
        # Hysteresis on distance ratio
        # Pinch when ratio <= in_ratio, release when ratio >= out_ratio
        self.in_ratio: float = float(gd.get("pinch_in_ratio", 0.35))
        self.out_ratio: float = float(gd.get("pinch_out_ratio", 0.55))
        # Ignore trivial closings (avoid clicks if there's still a visible gap)
        self.min_close_ratio: float = float(gd.get("min_close_ratio", 0.25))

        # Internal states per pinch pair
        self.left = _PinchState()
        self.right = _PinchState()
        # Middle-click = both left and right pairs pinched at the same time
        self.middle_last_ts: float = 0.0
        self.middle_debounce_ms: int = int(gd.get("click_debounce_ms", 120))

        # Distance floor for baseline updates (ignore very small/noisy distances)
        self._baseline_update_floor = 0.03

        # Log one-time summary
        self.log.info(
            "GestureDetector initialized with EMA=%.2f, in_ratio=%.2f, out_ratio=%.2f, debounce=%dms",
            self.ema_alpha, self.in_ratio, self.out_ratio, self.click_debounce_ms
        )

    def detect(self, landmarks: Sequence[Sequence[float]]) -> Optional[str]:
        """
        landmarks: iterable of 21 points [x, y, z?] in normalized [0..1]
        Returns one of: "LEFT_CLICK", "RIGHT_CLICK", "MIDDLE_CLICK", or None
        """
        now = time.perf_counter()

        # Pair distances
        d_left = self._pair_distance(landmarks, INDEX_TIP, MIDDLE_TIP)
        d_right = self._pair_distance(landmarks, MIDDLE_TIP, RING_TIP)

        # Smooth and update baselines
        ratio_left = self._update_state_and_ratio(self.left, d_left)
        ratio_right = self._update_state_and_ratio(self.right, d_right)

        # Update pinch booleans with hysteresis
        self._update_pinch_boolean(self.left, ratio_left)
        self._update_pinch_boolean(self.right, ratio_right)

        # Middle click: both pinched on the same edge transition
        # Fire once per combined transition, with its own debounce
        middle_candidate = self.left.is_pinched and self.right.is_pinched
        if middle_candidate and (now - self.middle_last_ts) * 1000.0 >= self.middle_debounce_ms:
            # Only treat as a middle click if both pairs are meaningfully closed
            if (ratio_left is not None and ratio_right is not None
                and ratio_left <= self.min_close_ratio
                and ratio_right <= self.min_close_ratio):
                self.middle_last_ts = now
                # Reset per-pair click timestamps to avoid double-firing
                self.left.last_click_ts = now
                self.right.last_click_ts = now
                return "MIDDLE_CLICK"

        # Edge-triggered left/right clicks with time debounce
        left_click = self._edge_click(self.left, ratio_left, now)
        if left_click:
            return "LEFT_CLICK"

        right_click = self._edge_click(self.right, ratio_right, now)
        if right_click:
            return "RIGHT_CLICK"

        return None

    # ---------- internals ----------

    @staticmethod
    def _pair_distance(landmarks: Sequence[Sequence[float]], i: int, j: int) -> float:
        xi, yi = landmarks[i][0], landmarks[i][1]
        xj, yj = landmarks[j][0], landmarks[j][1]
        dx = xi - xj
        dy = yi - yj
        return math.hypot(dx, dy)

    def _ema(self, prev: Optional[float], value: float) -> float:
        if prev is None:
            return value
        a = self.ema_alpha
        return a * value + (1.0 - a) * prev

    def _update_state_and_ratio(self, st: _PinchState, dist: float) -> Optional[float]:
        # Smooth the raw distance
        st.ema_dist = self._ema(st.ema_dist, dist)

        # Maintain an "open-hand" baseline when clearly not pinched
        # Only raise baseline from sufficiently large, stable distances
        if st.ema_dist is not None:
            if st.ema_baseline is None:
                st.ema_baseline = max(st.ema_dist, self._baseline_update_floor)
            else:
                # Update baseline only when not pinched and distance is larger than current baseline
                if not st.is_pinched and st.ema_dist >= max(st.ema_baseline, self._baseline_update_floor):
                    st.ema_baseline = self._ema(st.ema_baseline, st.ema_dist)

        # Compute distance ratio vs baseline
        if st.ema_baseline is None or st.ema_baseline <= 1e-6:
            return None
        return max(0.0, min(2.0, (st.ema_dist or dist) / st.ema_baseline))

    def _update_pinch_boolean(self, st: _PinchState, ratio: Optional[float]) -> None:
        if ratio is None:
            return
        # Hysteresis thresholds
        if st.is_pinched:
            if ratio >= self.out_ratio:
                st.is_pinched = False
                st.press_started_ts = 0.0
        else:
            # Require ratio below both in_ratio and a stricter "visible close" guard
            if ratio <= min(self.in_ratio, self.min_close_ratio):
                st.is_pinched = True
                st.press_started_ts = time.perf_counter()

    def _edge_click(self, st: _PinchState, ratio: Optional[float], now: float) -> bool:
        if ratio is None:
            return False
        # Rising edge: became pinched and held for min_press_ms
        if st.is_pinched and st.press_started_ts > 0:
            held_ms = (now - st.press_started_ts) * 1000.0
            since_last_ms = (now - st.last_click_ts) * 1000.0
            if held_ms >= self.min_press_ms and since_last_ms >= self.click_debounce_ms:
                # One-shot click on edge, then block re-fire until release
                st.last_click_ts = now
                # Prevent multiple clicks during the same hold
                st.press_started_ts = 0.0
                return True
        return False