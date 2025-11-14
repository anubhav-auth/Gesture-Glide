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
from src.core_logic import GestureCoreLogic 
import time


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
        
        # NEW: Pass the config object (dict) to the constructors
        self.cursor_controller = CursorController(
            config=self.config.config 
        )
        self.gesture_detector = GestureDetector(
            config=self.config.config
        )
        self.mouse_actions = MouseActions()
        
        # Initialize the core logic handler
        self.core_logic = GestureCoreLogic(
            self.config, self.hand_tracker, self.cursor_controller, 
            self.gesture_detector, self.mouse_actions
        )
        
        # Communication queues
        max_q_depth = self.config.advanced.get('max_queue_depth', 2)
        self.process_queue = queue.Queue(maxsize=max_q_depth)
        self.display_queue = queue.Queue(maxsize=max_q_depth)
        self.action_queue = queue.Queue(maxsize=max_q_depth)
        
        # Thread control
        self.running = False
        self.threads = []
        self.is_paused = False
        
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
        frame_skip = self.config.performance.get('frame_skip', 1)
        
        try:
            while self.running:
                ret, frame = cap.read()
                if not ret:
                    time.sleep(0.01) # Wait for camera
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
                
                # Use core logic to process frame (DOES NOT execute actions)
                gesture, landmarks, cursor_pos = self.core_logic.process_frame(frame)
                
                # Put the resulting action into the mouse action queue
                if gesture or cursor_pos:
                    try:
                        self.action_queue.put((gesture, cursor_pos), block=False)
                    except queue.Full:
                        pass # Drop action if mouse thread is lagging

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
    
    def mouse_action_thread(self):
        """Executes mouse actions from the action queue"""
        self.logger.info("Mouse action thread started")
        
        try:
            while self.running:
                if self.is_paused:
                    time.sleep(0.1) # Sleep to avoid busy-waiting
                    continue
                
                try:
                    # Get the action bundle
                    gesture, cursor_pos = self.action_queue.get(timeout=1)
                except queue.Empty:
                    continue
                
                # Use core logic to execute the (blocking) mouse action
                if cursor_pos:
                    self.core_logic._execute_actions(gesture, cursor_pos[0], cursor_pos[1])
                
        except Exception as e:
            self.logger.error(f"Error in mouse action thread: {e}", exc_info=True)
        finally:
            self.logger.info("Mouse action thread stopped")
    
    def display_thread(self):
        """Display video with overlay visualization"""
        self.logger.info("Display thread started")
        
        fps_counter = 0
        last_time = cv2.getTickCount()
        fps = 0
        
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
                
                h, w, _ = display_frame.shape
                
                # Show performance metrics
                if self.config.visualization['show_performance_metrics']:
                    fps_counter += 1
                    if (cv2.getTickCount() - last_time) / cv2.getTickFrequency() > 1.0:
                        fps = fps_counter
                        fps_counter = 0
                        last_time = cv2.getTickCount()
                        
                    cv2.putText(display_frame, f"FPS: {fps}", 
                              (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, 
                              tuple(self.config.visualization['text_color']), 1)
                
                # Show "PAUSED" overlay
                if self.is_paused:
                    text = "PAUSED (Press 'p' to resume)"
                    text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 1, 2)[0]
                    text_x = (w - text_size[0]) // 2
                    text_y = (h + text_size[1]) // 2
                    
                    cv2.rectangle(display_frame, (text_x - 10, text_y - text_size[1] - 10), (text_x + text_size[0] + 10, text_y + 10), (0, 0, 0), -1)
                    cv2.putText(display_frame, text, (text_x, text_y),
                                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

                cv2.imshow("GestureGlide", display_frame)
                
                key = cv2.waitKey(1) & 0xFF
                
                if key == 27: # Check for quit key (ESC)
                    self.running = False
                elif key == ord('p'): # Check for pause key
                    self.is_paused = not self.is_paused
                    self.logger.info(f"Gesture control PAUSED: {self.is_paused}")
                
        except Exception as e:
            self.logger.error(f"Error in display thread: {e}", exc_info=True)
        finally:
            cv2.destroyAllWindows()
            self.logger.info("Display thread stopped")
            self.running = False # Signal other threads to stop
            
            
    def run(self):
        """Start the application"""
        self.logger.info("Starting GestureGlide")
        self.running = True
        
        try:
            if self.config.performance['enable_multithreading']:
                capture = threading.Thread(target=self.capture_thread, daemon=True)
                process = threading.Thread(target=self.process_thread, daemon=True)
                mouse_actions = threading.Thread(target=self.mouse_action_thread, daemon=True)
                display = threading.Thread(target=self.display_thread) # Display must be non-daemon
                
                self.threads = [capture, process, mouse_actions, display]
                
                capture.start()
                process.start()
                mouse_actions.start()
                display.start()
                
                # Wait for the display thread to finish (it exits on ESC)
                display.join()
                
            else:
                self.logger.warning("Running in single-threaded mode (use quickstart.py)")
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
            
            if not self.is_paused:
                gesture, landmarks, cursor_pos = self.core_logic.process_frame(frame)
                if cursor_pos:
                    self.core_logic._execute_actions(gesture, cursor_pos[0], cursor_pos[1])
            else:
                gesture, landmarks, cursor_pos = None, None, None

            display_frame = self.core_logic.draw_visualizations(
                frame.copy(), gesture, landmarks, cursor_pos
            )
            
            cv2.imshow("GestureGlide (Single-Threaded)", display_frame)
            key = cv2.waitKey(1) & 0xFF
            if key == 27:
                self.running = False
            elif key == ord('p'):
                self.is_paused = not self.is_paused
        
        cap.release()
        cv2.destroyAllWindows()

def main():
    """Application entry point"""
    app = GestureGlideApp("config.yaml")
    app.run()

if __name__ == "__main__":
    main()