import cv2
import os
import logging

class SingletonCamera:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SingletonCamera, cls).__new__(cls)
            cls._instance.init_camera()
        return cls._instance

    def init_camera(self):
        available_indices = [i for i in range(10) if cv2.VideoCapture(i).read()[0]]
        for index in available_indices:
            self.cap = cv2.VideoCapture(index)
            if self.cap.isOpened():
                logging.info(f"Camera successfully opened at index {index}.")
                return
            self.cap = None

        if self.cap is None:
            logging.error("Failed to open any available cameras.")

    def get_frame(self):
        if self.cap is None:
            return None

        try:
            ret, frame = self.cap.read()
            if not ret:
                logging.error("Failed to grab frame.")
                return None
            return frame
        except Exception as e:
            logging.error(f"Exception while reading frame: {e}")
            return None

    def __del__(self):
        if self.cap is not None:
            self.cap.release()

# Initialize logging
logging.basicConfig(level=logging.INFO)

# Test the SingletonCamera
if __name__ == "__main__":
    cam1 = SingletonCamera()
    frame = cam1.get_frame()
    if frame is not None:
        cv2.imwrite("test_frame.jpg", frame)
    else:
        logging.error("Failed to get frame.")