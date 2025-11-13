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
from typing import Optional, Tuple

from src.config import Config
from src.utils import setup_logging
from src.hand_tracker import HandTracker
from src.cursor_controller import CursorController
from src.gesture_detector import GestureDetector
from src.mouse_actions import MouseActions
from src.core_logic import GestureCoreLogic # <-- Import new logic class

class GestureGlideApp:
    """Main application class orchestrating all components"""
    
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize GestureGlide application
        
        Args:
            config_path: Path to configuration file
        """
        if not Path(config_path).exists():
            if Path("../config.yaml").exists():
                config_path = "../config.yaml"
            else:
                logging.error(f"Config file not found: {config_path}")
                sys.exit(1)

        self.config = Config(config_path)
        setup_logging(
            log_level=self.config.system.get('log_level', 'INFO'),
            log_file=self.config.system.get('log_file')
        )

        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.hand_tracker = HandTracker(self.config)
        self.cursor_controller = CursorController(
            screen_width=self.config.cursor_control.get('screen_width'),
            screen_height=self.config.cursor_control.get('screen_height'),
            smoothing_filter=self.config.cursor_control.get('smoothing_filter', 'kalman')
        )
        self.gesture_detector = GestureDetector(self.config.gesture_detection) # Use Fix #1
        self.mouse_actions = MouseActions()
        
        # Initialize the core logic handler
        self.core_logic = GestureCoreLogic(
            self.config, self.hand_tracker, self.cursor_controller, 
            self.gesture_detector, self.mouse_actions
        )
        
        # Communication queues
        # process_queue: Holds raw frames for the process_thread
        self.process_queue = queue.Queue(maxsize=self.config.advanced['max_queue_depth'])
        # display_queue: Holds processed (frame, gesture, landmarks) for display_thread
        self.display_queue = queue.Queue(maxsize=self.config.advanced['max_queue_depth'])
        
        # Thread control
        self.running = False
        self.threads = []
        
        self.logger.info("GestureGlide application initialized")
    
    def capture_thread(self):
        """Capture video frames from webcam"""
        self.logger.info("Capture thread started")
        cap = cv2.VideoCapture(0)
        
        if not cap.isOpened():
            self.logger.error("Failed to open webcam")
            self.running = False
            return
        
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
                    # Put raw frame into the processing queue
                    self.process_queue.put(frame, block=True, timeout=1)
                except queue.Full:
                    pass  # Drop frame if process queue is full
                    
        finally:
            cap.release()
            self.logger.info("Capture thread stopped")
    
    def process_thread(self):
        """Process frames: detect hands, recognize gestures, update cursor"""
        self.logger.info("Process thread started")
        
        try:
            while self.running:
                try:
                    frame = self.process_queue.get(timeout=1)
                except queue.Empty:
                    continue
                
                # Use core logic to process frame and execute actions
                gesture, landmarks, cursor_pos = self.core_logic.process_frame(frame)
                
                # Put the original frame + processed data into the display queue
                try:
                    display_bundle = (frame, gesture, landmarks, cursor_pos)
                    self.display_queue.put(display_bundle, block=False)
                except queue.Full:
                    pass # Drop display frame if display is lagging
                
        except Exception as e:
            self.logger.error(f"Error in process thread: {e}", exc_info=True)
        finally:
            self.logger.info("Process thread stopped")
    
    def display_thread(self):
        """Display video with overlay visualization"""
        self.logger.info("Display thread started")
        
        fps_counter = 0
        last_time = cv2.getTickCount()
        
        try:
            while self.running:
                try:
                    # Get the bundled frame and metadata
                    frame, gesture, landmarks, cursor_pos = self.display_queue.get(timeout=1)
                except queue.Empty:
                    continue
                
                # Use core logic to draw visualizations
                display_frame = self.core_logic.draw_visualizations(
                    frame, gesture, landmarks, cursor_pos
                )
                
                # Show performance metrics
                if self.config.visualization['show_performance_metrics']:
                    fps_counter += 1
                    if (cv2.getTickCount() - last_time) / cv2.getTickFrequency() > 1.0:
                        fps = fps_counter
                        fps_counter = 0
                        last_time = cv2.getTickCount()
                    else:
                        fps = fps_counter # Show running count
                        
                    cv2.putText(display_frame, f"FPS: {fps}", 
                              (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, 
                              tuple(self.config.visualization['text_color']), 1)
                
                cv2.imshow("GestureGlide", display_frame)
                
                # Check for quit key (ESC)
                if cv2.waitKey(1) & 0xFF == 27:
                    self.running = False
                
        except Exception as e:
            self.logger.error(f"Error in display thread: {e}", exc_info=True)
        finally:
            cv2.destroyAllWindows()
            self.logger.info("Display thread stopped")
    
    def run(self):
        """Start the application"""
        self.logger.info("Starting GestureGlide")
        self.running = True
        
        try:
            if self.config.performance['enable_multithreading']:
                capture = threading.Thread(target=self.capture_thread, daemon=True)
                process = threading.Thread(target=self.process_thread, daemon=True)
                display = threading.Thread(target=self.display_thread) # Display must be non-daemon
                
                self.threads = [capture, process, display]
                
                capture.start()
                process.start()
                display.start()
                
                # Wait for the display thread to finish (it exits on ESC)
                display.join()
                
            else:
                self.logger.warning("Running in single-threaded mode (use quickstart.py)")
                # Fallback to single-threaded logic (now in quickstart)
                self.run_single_threaded_fallback()
        
        except KeyboardInterrupt:
            self.logger.info("Keyboard interrupt received")
        finally:
            self.running = False
            # Wait for daemon threads to exit
            for thread in self.threads:
                if thread.is_alive() and thread.daemon:
                    thread.join(timeout=1)
            self.logger.info("GestureGlide stopped")
    
    def run_single_threaded_fallback(self):
        """Fallback for single-threaded mode (quickstart.py is preferred)"""
        cap = cv2.VideoCapture(0)
        while self.running and cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            
            gesture, landmarks, cursor_pos = self.core_logic.process_frame(frame)
            display_frame = self.core_logic.draw_visualizations(
                frame.copy(), gesture, landmarks, cursor_pos
            )
            
            cv2.imshow("GestureGlide (Single-Threaded)", display_frame)
            if cv2.waitKey(1) & 0xFF == 27:
                self.running = False
        
        cap.release()
        cv2.destroyAllWindows()

def main():
    """Application entry point"""
    app = GestureGlideApp("config.yaml")
    app.run()

if __name__ == "__main__":
    main()