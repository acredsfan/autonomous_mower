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
    cap = cv2.VideoCapture(0)
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SingletonCamera, cls).__new__(cls)
            import os
            if not os.path.exists('/dev/video0'):
                logging.error("Camera at /dev/video0 not found.")
            cls._instance.cap = cv2.VideoCapture(0)  # Initialize camera here
        return cls._instance
    def get_frame(self):
        try:
            print("Trying to read a frame...")  # Debugging line
            ret, frame = self.cap.read()
            if ret:
                print("Frame read successfully.")  # Debugging line
                ret, jpeg = cv2.imencode('.jpg', frame)
                return jpeg.tobytes()
            else:
                print("Failed to grab frame.")  # Debugging line
                return None
        except Exception as e:
            print(f"An exception occurred: {e}")  # Debugging line
            return None
        
    def __del__(self):
        self.cap.release()
    
# Initialize the camera instance
camera_instance = SingletonCamera()