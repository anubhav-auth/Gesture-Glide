# ============================================================================
# MOUSE ACTIONS
# ============================================================================

import logging
import pyautogui

class MouseActions:
    """Mouse event injection"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.drag_active = False
    
    def move_cursor(self, x: int, y: int):
        """Move cursor to position"""
        pyautogui.moveTo(x, y, duration=0)
    
    def left_click(self):
        """Perform left click"""
        pyautogui.click(button='left')
        self.logger.debug("Left click")
    
    def right_click(self):
        """Perform right click"""
        pyautogui.click(button='right')
        self.logger.debug("Right click")
    
    def middle_click(self):
        """Perform middle click"""
        pyautogui.click(button='middle')
        self.logger.debug("Middle click")
    
    def start_drag(self, x: int, y: int):
        """Start drag operation"""
        pyautogui.mouseDown(button='left')
        self.drag_active = True
        self.logger.debug(f"Drag started at ({x}, {y})")
    
    def drag_to(self, x: int, y: int):
        """Continue drag to position"""
        if self.drag_active:
            pyautogui.moveTo(x, y, duration=0)
    
    def end_drag(self):
        """End drag operation"""
        if self.drag_active:
            pyautogui.mouseUp(button='left')
            self.drag_active = False
            self.logger.debug("Drag ended")
    
    def scroll(self, delta: int):
        """Scroll (positive=up, negative=down)"""
        pyautogui.scroll(delta)
        self.logger.debug(f"Scroll: {delta}")
        
    def hscroll(self, delta: int):
        """Scroll horizontally (positive=right, negative=left)"""
        pyautogui.hscroll(delta)
        self.logger.debug(f"HScroll: {delta}")
