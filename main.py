"""
GestureGlide - Main Application Entry Point
Coordinates multi-threaded architecture for real-time hand gesture control
"""

import cv2
import threading
import queue
import logging
import sys
import numpy as np
from pathlib import Path

from src.config import Config
from src.hand_tracker import HandTracker
from src.cursor_controller import CursorController
from src.gesture_detector import GestureDetector
from src.mouse_actions import MouseActions
from src.utils import setup_logging, get_screen_size


class GestureGlideApp:
    """Main application class orchestrating all components"""
    
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize GestureGlide application
        
        Args:
            config_path: Path to configuration file
        """
        self.config = Config(config_path)
        setup_logging(self.config)
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.hand_tracker = HandTracker(self.config)
        self.cursor_controller = CursorController(self.config)
        self.gesture_detector = GestureDetector(self.config)
        self.mouse_actions = MouseActions(self.config)
        
        # Communication queues
        self.frame_queue = queue.Queue(maxsize=self.config.advanced['max_queue_depth'])
        self.gesture_queue = queue.Queue(maxsize=100)
        
        # Thread control
        self.running = False
        self.threads = []
        
        # Performance metrics
        self.frame_count = 0
        self.fps_counter = 0
        
        self.logger.info("GestureGlide application initialized")
    
    def capture_thread(self):
        """Capture video frames from webcam"""
        self.logger.info("Capture thread started")
        cap = cv2.VideoCapture(0)
        
        if not cap.isOpened():
            self.logger.error("Failed to open webcam")
            self.running = False
            return
        
        # Set camera resolution
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_FPS, 30)
        
        frame_skip_counter = 0
        frame_skip = self.config.performance['frame_skip']
        
        try:
            while self.running:
                ret, frame = cap.read()
                if not ret:
                    continue
                
                frame_skip_counter += 1
                if frame_skip_counter < frame_skip:
                    continue
                frame_skip_counter = 0
                
                try:
                    self.frame_queue.put(frame, block=False)
                except queue.Full:
                    pass  # Drop oldest frame if queue full
                    
        finally:
            cap.release()
            self.logger.info("Capture thread stopped")
    
    def process_thread(self):
        """Process frames: detect hands, recognize gestures, update cursor"""
        self.logger.info("Process thread started")
        
        try:
            while self.running:
                try:
                    frame = self.frame_queue.get(timeout=1)
                except queue.Empty:
                    continue
                
                # Detect hand landmarks
                landmarks, handedness, confidence = self.hand_tracker.detect(frame)
                
                if landmarks is not None and confidence > self.config.hand_tracking['detection_confidence']:
                    # Update cursor position based on middle finger
                    cursor_x, cursor_y = self.cursor_controller.update_position(landmarks)
                    
                    # Detect gestures
                    gesture = self.gesture_detector.detect(landmarks)
                    
                    # Update cursor on screen
                    if gesture is None or gesture == "CURSOR_MOVE":
                        self.mouse_actions.move_cursor(cursor_x, cursor_y)
                    
                    # Process gesture-specific actions
                    if gesture == "LEFT_CLICK":
                        self.mouse_actions.left_click()
                    elif gesture == "RIGHT_CLICK":
                        self.mouse_actions.right_click()
                    elif gesture == "MIDDLE_CLICK":
                        self.mouse_actions.middle_click()
                    elif gesture == "DRAG_START":
                        self.mouse_actions.start_drag(cursor_x, cursor_y)
                    elif gesture == "DRAG_MOVE":
                        self.mouse_actions.drag_to(cursor_x, cursor_y)
                    elif gesture == "DRAG_END":
                        self.mouse_actions.end_drag()
                    elif gesture == "ZOOM_IN":
                        self.mouse_actions.scroll(5)  # Scroll up
                    elif gesture == "ZOOM_OUT":
                        self.mouse_actions.scroll(-5)  # Scroll down
                    elif gesture == "SCROLL_UP":
                        self.mouse_actions.scroll(3)
                    elif gesture == "SCROLL_DOWN":
                        self.mouse_actions.scroll(-3)
                    
                    try:
                        self.gesture_queue.put(gesture, block=False)
                    except queue.Full:
                        pass
                
                self.frame_count += 1
                
        except Exception as e:
            self.logger.error(f"Error in process thread: {e}")
        finally:
            self.logger.info("Process thread stopped")
    
    def display_thread(self):
        """Display video with overlay visualization"""
        self.logger.info("Display thread started")
        
        try:
            while self.running:
                try:
                    frame = self.frame_queue.get(timeout=1)
                except queue.Empty:
                    continue
                
                # Display frame with hand skeleton overlay
                display_frame = frame.copy()
                
                # Get current gesture from queue
                current_gesture = None
                try:
                    current_gesture = self.gesture_queue.get_nowait()
                except queue.Empty:
                    pass
                
                # Draw gesture indicator
                if self.config.visualization['show_gesture_indicators'] and current_gesture:
                    cv2.putText(display_frame, f"Gesture: {current_gesture}", 
                              (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, 
                              tuple(self.config.visualization['text_color']), 2)
                
                # Show performance metrics
                if self.config.visualization['show_performance_metrics']:
                    fps = cv2.getTickFrequency() / (cv2.getTickCount() - self.fps_counter)
                    cv2.putText(display_frame, f"FPS: {fps:.1f}", 
                              (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, 
                              tuple(self.config.visualization['text_color']), 1)
                
                cv2.imshow("GestureGlide", display_frame)
                
                # Check for quit key (ESC)
                if cv2.waitKey(1) & 0xFF == 27:
                    self.running = False
                
        except Exception as e:
            self.logger.error(f"Error in display thread: {e}")
        finally:
            cv2.destroyAllWindows()
            self.logger.info("Display thread stopped")
    
    def run(self):
        """Start the application"""
        self.logger.info("Starting GestureGlide")
        self.running = True
        
        try:
            # Create and start threads
            if self.config.performance['enable_multithreading']:
                capture = threading.Thread(target=self.capture_thread, daemon=True)
                process = threading.Thread(target=self.process_thread, daemon=True)
                display = threading.Thread(target=self.display_thread, daemon=True)
                
                capture.start()
                process.start()
                display.start()
                
                self.threads = [capture, process, display]
                
                # Wait for threads
                for thread in self.threads:
                    thread.join()
            else:
                # Single-threaded mode
                self.logger.warning("Running in single-threaded mode (not recommended)")
                self.run_single_threaded()
        
        except KeyboardInterrupt:
            self.logger.info("Keyboard interrupt received")
        except Exception as e:
            self.logger.error(f"Error in main loop: {e}")
        finally:
            self.running = False
            self.logger.info("GestureGlide stopped")
    
    def run_single_threaded(self):
        """Single-threaded execution (fallback mode)"""
        cap = cv2.VideoCapture(0)
        
        while self.running and cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            
            landmarks, _, confidence = self.hand_tracker.detect(frame)
            if landmarks is not None and confidence > self.config.hand_tracking['detection_confidence']:
                cursor_x, cursor_y = self.cursor_controller.update_position(landmarks)
                gesture = self.gesture_detector.detect(landmarks)
                
                if gesture is None or gesture == "CURSOR_MOVE":
                    self.mouse_actions.move_cursor(cursor_x, cursor_y)
            
            cv2.imshow("GestureGlide", frame)
            if cv2.waitKey(1) & 0xFF == 27:
                break
        
        cap.release()
        cv2.destroyAllWindows()


def main():
    """Application entry point"""
    app = GestureGlideApp("config.yaml")
    app.run()


if __name__ == "__main__":
    main()
