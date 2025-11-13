# scripts/benchmark.py
#!/usr/bin/env python3
import time
import logging
import sys

import cv2
import psutil

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PerformanceBenchmark:
    def __init__(self) -> None:
        self.metrics = {
            "fps": 0.0,
            "latency_ms": 0.0,
            "cpu_percent": 0.0,
            "mem_mb": 0.0,
        }

        # Optional hands processor using public API
        self.hands_processor = None
        try:
            import mediapipe as mp  # noqa: F401
            self._mp_hands = mp.solutions.hands  # type: ignore[attr-defined]
            self.hands_processor = self._mp_hands.Hands(
                static_image_mode=False,
                max_num_hands=1,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5,
                model_complexity=0,
            )
            logger.info("MediaPipe hands processor initialized")
        except Exception:
            self._mp_hands = None
            self.hands_processor = None
            logger.warning("mediapipe not available; benchmark will skip hand processing")

    def run(self, duration_seconds: int = 30) -> None:
        print("\nGestureGlide Performance Benchmark")
        print("-" * 50)
        print(f"Running for {duration_seconds} seconds...")

        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            logger.error("Failed to open webcam.")
            return

        process = psutil.Process()
        start_time = time.time()
        total_frame_time_ms = 0.0
        frame_count = 0

        try:
            while time.time() - start_time < duration_seconds:
                ok, frame = cap.read()
                if not ok:
                    break

                t0 = time.time()
                # Optional processing
                if self.hands_processor is not None:
                    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    _ = self.hands_processor.process(rgb)
                # Simulate minimum work if no processor available
                total_frame_time_ms += (time.time() - t0) * 1000.0
                frame_count += 1

            elapsed = time.time() - start_time
            if elapsed > 0:
                self.metrics["fps"] = frame_count / elapsed
            if frame_count > 0:
                self.metrics["latency_ms"] = total_frame_time_ms / frame_count

            self.metrics["cpu_percent"] = process.cpu_percent(interval=0.1)
            self.metrics["mem_mb"] = process.memory_info().rss / (1024 * 1024)
        finally:
            cap.release()
            if self.hands_processor is not None:
                self.hands_processor.close()

        self._print_results()

    def _print_results(self) -> None:
        print("\nBenchmark Results")
        print("-" * 50)
        print(f"Average FPS        : {self.metrics['fps']:.1f}")
        print(f"Avg frame latency  : {self.metrics['latency_ms']:.1f} ms")
        print(f"CPU Usage          : {self.metrics['cpu_percent']:.1f}%")
        print(f"Memory Usage       : {self.metrics['mem_mb']:.1f} MB")
        print("-" * 50)

def main() -> int:
    duration = 30
    if len(sys.argv) > 1:
        try:
            duration = int(sys.argv[1])
        except ValueError:
            logger.warning("Usage: python scripts/benchmark.py [duration_seconds]")
    PerformanceBenchmark().run(duration_seconds=duration)
    return 0

if __name__ == "__main__":
    sys.exit(main())
