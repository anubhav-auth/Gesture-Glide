#!/usr/bin/env python3
"""
GestureGlide - Benchmark & Performance Tools
"""

import time
import cv2
import psutil
import numpy as np


class PerformanceBenchmark:
    """Performance benchmarking tool"""
    
    def __init__(self):
        self.metrics = {
            "fps": 0,
            "latency": 0,
            "cpu_usage": 0,
            "memory_usage": 0
        }
    
    def run_benchmark(self, duration_seconds: int = 60):
        """Run performance benchmark"""
        print("🚀 GestureGlide Performance Benchmark")
        print("=" * 50)
        print(f"Running for {duration_seconds} seconds...\n")
        
        frame_count = 0
        start_time = time.time()
        process = psutil.Process()
        
        cap = cv2.VideoCapture(0)
        
        while time.time() - start_time < duration_seconds:
            ret, frame = cap.read()
            if not ret:
                break
            
            frame_time_start = time.time()
            # Process frame (simplified)
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame_time = (time.time() - frame_time_start) * 1000
            
            frame_count += 1
            
            # Update metrics
            elapsed = time.time() - start_time
            self.metrics["fps"] = frame_count / elapsed
            self.metrics["latency"] = frame_time
            self.metrics["cpu_usage"] = process.cpu_percent()
            self.metrics["memory_usage"] = process.memory_info().rss / 1024 / 1024
        
        cap.release()
        self._print_results()
    
    def _print_results(self):
        """Print benchmark results"""
        print("\n📊 Benchmark Results:")
        print("-" * 50)
        print(f"Average FPS:     {self.metrics['fps']:.1f}")
        print(f"Latency:         {self.metrics['latency']:.1f} ms")
        print(f"CPU Usage:       {self.metrics['cpu_usage']:.1f}%")
        print(f"Memory Usage:    {self.metrics['memory_usage']:.1f} MB")
        print("-" * 50)
        
        # Status indicators
        status = []
        if self.metrics['fps'] >= 25:
            status.append("✓ FPS acceptable")
        else:
            status.append("✗ FPS low")
        
        if self.metrics['latency'] < 100:
            status.append("✓ Latency good")
        else:
            status.append("✗ Latency high")
        
        if self.metrics['cpu_usage'] < 70:
            status.append("✓ CPU usage acceptable")
        else:
            status.append("✗ CPU usage high")
        
        for s in status:
            print(s)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "benchmark":
        benchmark = PerformanceBenchmark()
        benchmark.run_benchmark()
    else:
        test = InteractiveGestureTest()
        test.run_test()
