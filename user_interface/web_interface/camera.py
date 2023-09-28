import cv2
import logging
import time
"""
SingletonCamera class to initialize camera and get frames.

This class implements the Singleton design pattern to ensure only one 
camera object is initialized. 

The __new__ method checks if an instance already exists, and if not creates
one by calling super().__new__ and initializing the VideoCapture object 
with index 0.

The get_frame() method reads a frame from the VideoCapture object and 
returns it.

So this class encapsulates initializing the camera resource and retrieving
frames in a thread-safe singleton way.

Attributes:
    _instance (SingletonCamera): Static instance of the singleton.

Methods:
    __new__(): Creates singleton instance if none exists yet.
    get_frame(): Gets next video frame from camera.
"""
# Initialize logging
logging.basicConfig(filename='main.log', level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s')
 
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