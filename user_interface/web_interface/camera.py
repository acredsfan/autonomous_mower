import cv2
import os
import logging

logging.basicConfig(filename='main.log', level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s')

class SingletonCamera:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SingletonCamera, cls).__new__(cls)
            cls._instance.init_camera()
        return cls._instance

    def init_camera(self):
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            logging.error("Failed to open camera at index 0.")
            self.cap = None

    def get_frame(self):
        if self.cap is None:
            logging.error("Camera capture is not initialized.")
            return None
        try:
            ret, frame = self.cap.read()
            if not ret:
                logging.error("cap.read() returned False. Unable to grab frame.")
                # Log additional debug information if needed
                logging.debug(f"cap.read() return value: {ret}")
                logging.debug(f"cap.isOpened(): {self.cap.isOpened()}")
                # If you want to log the entire stack trace, uncomment the following line:
                logging.error("Stack Trace:", exc_info=True)
                return None
            return frame
        except Exception as e:
            logging.error(f"Exception occurred while reading frame: {e}")
            # Log the stack trace for the exception
            logging.error(traceback.format_exc())
            return None

    def __del__(self):
        if self.cap is not None:
            self.cap.release()

# Test the SingletonCamera
if __name__ == "__main__":
    cam1 = SingletonCamera()
    frame = cam1.get_frame()
    if frame is not None:
        cv2.imwrite("test_frame.jpg", frame)
    else:
        logging.error("Failed to get frame.")