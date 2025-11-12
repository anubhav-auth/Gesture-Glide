#!/usr/bin/env python3
"""
GestureGlide - Quick Start Script
Simplified entry point for immediate testing
"""

import sys
import os
from pathlib import Path

# Add project to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import cv2
import logging
from src.core_modules import (
    Config, setup_logging, HandTracker, CursorController,
    GestureDetector, MouseActions, draw_hand_skeleton, get_screen_size
)

def main():
    """Quick start application"""
    
    # Setup
    print("🚀 GestureGlide - Quick Start")
    print("=" * 50)
    
    # Check config file
    config_path = "config.yaml"
    if not Path(config_path).exists():
        print("❌ config.yaml not found!")
        print("Please copy resources/sample_config.yaml to config.yaml")
        return
    
    # Initialize
    try:
        config = Config(config_path)
        setup_logging(config)
        logger = logging.getLogger(__name__)
        
        print("✓ Configuration loaded")
        print(f"✓ Screen size: {get_screen_size()}")
        
        # Initialize components
        hand_tracker = HandTracker(config)
        cursor_controller = CursorController(config)
        gesture_detector = GestureDetector(config)
        mouse_actions = MouseActions(config)
        
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
        
        frame_count = 0
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            frame_count += 1
            
            # Detect hand landmarks
            landmarks, handedness, confidence = hand_tracker.detect(frame)
            
            display_frame = frame.copy()
            
            if landmarks is not None and confidence > config.hand_tracking['detection_confidence']:
                # Update cursor
                cursor_x, cursor_y = cursor_controller.update_position(landmarks)
                
                # Detect gesture
                gesture = gesture_detector.detect(landmarks)
                
                # Execute action
                if gesture is None or gesture == "CURSOR_MOVE":
                    mouse_actions.move_cursor(cursor_x, cursor_y)
                elif gesture == "LEFT_CLICK":
                    mouse_actions.left_click()
                    print(f"🖱️  Left Click")
                elif gesture == "RIGHT_CLICK":
                    mouse_actions.right_click()
                    print(f"🖱️  Right Click")
                elif gesture == "MIDDLE_CLICK":
                    mouse_actions.middle_click()
                    print(f"🖱️  Middle Click")
                elif gesture == "DRAG_MOVE":
                    mouse_actions.drag_to(cursor_x, cursor_y)
                elif gesture == "ZOOM_IN":
                    mouse_actions.scroll(5)
                    print(f"🔍 Zoom In")
                elif gesture == "ZOOM_OUT":
                    mouse_actions.scroll(-5)
                    print(f"🔍 Zoom Out")
                
                # Draw hand skeleton
                display_frame = draw_hand_skeleton(display_frame, landmarks, config)
                
                # Draw gesture indicator
                if gesture and config.visualization['show_gesture_indicators']:
                    text = f"Gesture: {gesture}"
                    cv2.putText(display_frame, text, (10, 30),
                              cv2.FONT_HERSHEY_SIMPLEX, 1,
                              tuple(config.visualization['text_color']), 2)
                
                # Draw cursor reference
                if config.visualization['show_cursor_position']:
                    cv2.circle(display_frame, (cursor_x % 640, cursor_y % 480), 
                             5, (0, 255, 0), -1)
            
            # Show FPS
            if frame_count % 30 == 0 and config.visualization['show_performance_metrics']:
                text = f"Frame: {frame_count}"
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
