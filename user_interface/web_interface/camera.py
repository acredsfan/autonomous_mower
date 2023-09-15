import cv2
import logging
import time

# Initialize logging
logging.basicConfig(filename='UI.log', level=logging.DEBUG)
 
class SingletonCamera:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SingletonCamera, cls).__new__(cls)
            cls._instance.cap = cv2.VideoCapture(0)  # Initialize camera here
        return cls._instance

    def get_frame(self):
        ret, frame = self.cap.read()
        return frame if ret else None