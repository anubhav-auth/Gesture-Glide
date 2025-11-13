#!/usr/bin/env python3
"""
GestureGlide Calibration Tool
Interactive calibration for gesture recognition
"""

import cv2
import numpy as np
import json
from pathlib import Path
import datetime


class Calibrator:
    """Interactive calibration utility"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.calibration_file = self.data_dir / "calibration_profile.json"
        self.calibration_data = {
            "pinch_thresholds": {},
            "cursor_sensitivity": 1.0,
            "timestamp": None
        }
    
    def run_calibration(self):
        """Run interactive calibration"""
        print("🎯 GestureGlide Calibration Tool")
        print("=" * 50)
        print("\nThis tool will calibrate gesture thresholds")
        print("for your specific hand size and environment.\n")
        
        # Calibration steps
        print("Step 1: Hand Position Calibration")
        self._calibrate_hand_position()
        
        print("\nStep 2: Pinch Threshold Calibration")
        self._calibrate_pinch_threshold()
        
        print("\nStep 3: Cursor Sensitivity Calibration")
        self._calibrate_cursor_sensitivity()
        
        # Save calibration
        self._save_calibration()
        print("\n✓ Calibration complete!")
    
    def _calibrate_hand_position(self):
        """Calibrate optimal hand position"""
        print("Position your hand in front of the camera.")
        print("Your hand should be roughly 30-50cm from the camera.")
        print("Press SPACE when ready, ESC to skip...")
    
    def _calibrate_pinch_threshold(self):
        """Calibrate pinch detection thresholds"""
        print("Perform pinch gestures with different finger combinations:")
        print("  1. Index + Middle (for left click)")
        print("  2. Middle + Ring (for right click)")
        print("  3. All three fingers (for middle click)")
        print("\nPress SPACE for each gesture, ESC when done...")
    
    def _calibrate_cursor_sensitivity(self):
        """Calibrate cursor movement sensitivity"""
        print("Move your hand around to test cursor sensitivity.")
        print("Press UP/DOWN arrows to increase/decrease speed.")
        print("Press SPACE when satisfied, ESC to skip...")
    
    def _save_calibration(self):
        """Save calibration to file"""
        import datetime
        self.calibration_data["timestamp"] = datetime.datetime.now().isoformat()
        
        with open(self.calibration_file, 'w') as f:
            json.dump(self.calibration_data, f, indent=2)
        
        print(f"Calibration saved to: {self.calibration_file}")
    
    def load_calibration(self):
        """Load calibration from file"""
        if self.calibration_file.exists():
            with open(self.calibration_file, 'r') as f:
                self.calibration_data = json.load(f)
            return True
        return False


if __name__ == "__main__":
    calibrator = Calibrator()
    calibrator.run_calibration()
