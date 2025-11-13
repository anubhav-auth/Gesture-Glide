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

        # --- FIX 3.1: Handle null screen resolution ---
        # Get values from config. They might be 'null' (None).
        conf_screen_width = config.cursor_control.get('screen_width')
        conf_screen_height = config.cursor_control.get('screen_height')

        cursor_controller = CursorController(
            # Pass None to trigger auto-detection in the controller
            screen_width=conf_screen_width,
            screen_height=conf_screen_height,
            smoothing_filter=config.cursor_control['smoothing_filter']
        )
        # --- END FIX ---
        
        gesture_detector = GestureDetector(config.gesture_detection)
        mouse_actions = MouseActions()
        
        # Initialize the core logic handler
        core_logic = GestureCoreLogic(
            config, hand_tracker, cursor_controller, gesture_detector, mouse_actions
        )
        
        print("✓ All components initialized")
        print("\n📷 Starting video capture...")
        print("Press ESC to exit\n")
        
        # --- FIX: Use the WebcamStream class, not cv2.VideoCapture ---
        cap = WebcamStream(src=0).start()
        # --- END FIX ---
        
        is_paused = False
        frame_count = 0
        
        while True:
            # Read the latest frame from the stream
            # This now correctly returns an ndarray (frame) or None
            frame = cap.read()
            if frame is None:
                continue
            
            # This now works, as 'frame' is an ndarray
            frame_copy = frame.copy()
            h, w, _ = frame_copy.shape

            # --- FIX 3.2: Process logic based on pause state ---
            if not is_paused:
                # 1. Process the frame (detect)
                # This now works, as 'frame' is an ndarray
                gesture, landmarks, cursor_pos = core_logic.process_frame(frame)
                
                # 2. Execute actions (Fix for single-threaded mode)
                if cursor_pos:
                    core_logic._execute_actions(gesture, cursor_pos[0], cursor_pos[1])
            else:
                # If paused, stop detecting and executing
                # We set these to None so visualization stops
                gesture, landmarks, cursor_pos = None, None, None
            # --- END FIX ---
            
            # 3. Draw visualizations
            display_frame = core_logic.draw_visualizations(
                frame_copy, gesture, landmarks, cursor_pos
            )

            # Show FPS
            if config.visualization['show_performance_metrics']:
                 frame_count += 1
                 text = f"Frame: {frame_count}"
                 cv2.putText(display_frame, text, (10, 60),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                           tuple(config.visualization['text_color']), 1)
            
            # --- FIX 3.2: Show "PAUSED" overlay ---
            if is_paused:
                text = "PAUSED (Press 'p' to resume)"
                text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 1, 2)[0]
                text_x = (w - text_size[0]) // 2
                text_y = (h + text_size[1]) // 2
                
                cv2.rectangle(display_frame, (text_x - 10, text_y - text_size[1] - 10), (text_x + text_size[0] + 10, text_y + 10), (0, 0, 0), -1)
                cv2.putText(display_frame, text, (text_x, text_y),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            # --- END FIX ---

            cv2.imshow("GestureGlide - Press ESC to Exit", display_frame)
            
            # --- FIX 3.2: Add 'p' key to toggle pause ---
            key = cv2.waitKey(1) & 0xFF
            
            if key == 27: # Check for ESC key
                print("\n✋ Exiting GestureGlide...")
                break
            elif key == ord('p'): # Check for pause key
                is_paused = not is_paused
                print(f"\nGesture control PAUSED: {is_paused}")
                
        cap.stop()


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