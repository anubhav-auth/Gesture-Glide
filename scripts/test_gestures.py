import cv2

class InteractiveGestureTest:
    """Interactive gesture testing tool"""
    
    def __init__(self):
        self.gesture_counts = {}
    
    def run_test(self):
        """Run interactive gesture test"""
        print("👋 GestureGlide Interactive Gesture Test")
        print("=" * 50)
        print("\nPerform gestures in front of camera.")
        print("Press ESC to exit.\n")
        
        cap = cv2.VideoCapture(0)
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Display frame
            cv2.imshow("Gesture Test", frame)
            
            if cv2.waitKey(1) & 0xFF == 27:  # ESC
                break
        
        cap.release()
        cv2.destroyAllWindows()
        
if __name__ == "__main__":
    test = InteractiveGestureTest()
    test.run_test()