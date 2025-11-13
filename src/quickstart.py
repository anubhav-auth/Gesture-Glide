#!/usr/bin/env python3
"""
GestureGlide - Quick Start Script
Simplified entry point for immediate testing.
This script is single-threaded.
"""

import sys
import os
from pathlib import Path
from typing import Optional
import numpy as np
import threading

# Add project to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import cv2
import logging
from src.config import Config
from src.hand_tracker import HandTracker
from src.cursor_controller import CursorController
from src.gesture_detector import GestureDetector
from src.mouse_actions import MouseActions
from src.core_logic import GestureCoreLogic 
from src.utils import setup_logging, get_screen_size

class WebcamStream:
    """
    A simple class to run cv2.VideoCapture in a dedicated thread.
    This prevents stale frames from the camera buffer.
    """
    def __init__(self, src=0):
        self.cap = cv2.VideoCapture(src)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.cap.set(cv2.CAP_PROP_FPS, 30)
        
        self.ret, self.frame = self.cap.read()
        self.running = False
        self.lock = threading.Lock()
        
    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._update, daemon=True)
        self.thread.start()
        return self
        
    def _update(self):
        while self.running:
            ret, frame = self.cap.read()
            if ret:
                with self.lock:
                    self.frame = frame
    
    def read(self) -> Optional[np.ndarray]:
        with self.lock:
            if self.frame is None:
                return None
            return self.frame.copy()
            
    def stop(self):
        self.running = False
        if self.thread.is_alive():
            self.thread.join(timeout=1)
        self.cap.release()

def main():
    """Quick start application"""
    
    # Setup
    print("🚀 GestureGlide - Quick Start")
    print("=" * 50)
    
    # Check config file
    config_path = "config.yaml"
    if not Path(config_path).exists():
        if Path("../config.yaml").exists():
             config_path = "../config.yaml"
        else:
            print("❌ config.yaml not found!")
            print("Please ensure config.yaml is in the project root.")
            return

    # Initialize
    try:
        config = Config(config_path)
        setup_logging(config.system.get('log_level', 'INFO'), config.system.get('log_file'))
        logger = logging.getLogger(__name__)
        
        print(f"✓ Configuration loaded from {config_path}")
        print(f"✓ Screen size: {get_screen_size()}")
        
        # Initialize components
        hand_tracker = HandTracker(config)
        cursor_controller = CursorController(
            screen_width=config.cursor_control['screen_width'],
            screen_height=config.cursor_control['screen_height'],
            smoothing_filter=config.cursor_control['smoothing_filter']
        )
        gesture_detector = GestureDetector(config.gesture_detection) # Use Fix #1
        mouse_actions = MouseActions()
        
        # Initialize the core logic handler
        core_logic = GestureCoreLogic(
            config, hand_tracker, cursor_controller, gesture_detector, mouse_actions
        )
        
        print("✓ All components initialized")
        print("\n📷 Starting video capture...")
        print("Press ESC to exit\n")
        
        # Capture video
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("❌ Failed to open webcam!")
            return
        
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_FPS, 30)
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # --- Refactored Logic ---
            # 1. Process the frame (detect, act)
            gesture, landmarks, cursor_pos = core_logic.process_frame(frame)
            
            # 2. Draw visualizations
            display_frame = core_logic.draw_visualizations(
                frame.copy(), gesture, landmarks, cursor_pos
            )
            # --- End Refactored Logic ---

            # Show FPS
            if config.visualization['show_performance_metrics']:
                 # Simple FPS calculation
                text = f"Frame: {int(cap.get(cv2.CAP_PROP_POS_FRAMES))}"
                cv2.putText(display_frame, text, (10, 60),
                          cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                          tuple(config.visualization['text_color']), 1)
            
            cv2.imshow("GestureGlide - Press ESC to Exit", display_frame)
            
            # Check for ESC key
            if cv2.waitKey(1) & 0xFF == 27:
                print("\n✋ Exiting GestureGlide...")
                break
        
        cap.release()
        cv2.destroyAllWindows()
        print("👋 GestureGlide stopped")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())