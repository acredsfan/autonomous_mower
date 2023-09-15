import cv2
import logging
import time

# Initialize logging
logging.basicConfig(filename='UI.log', level=logging.DEBUG)

class VideoCamera(object):
    def __init__(self):
        # Use OpenCV to capture from Raspberry Pi camera module
        try:
            self.cap = cv2.VideoCapture('v4l2src device=/dev/video0 ! videoconvert ! appsink', cv2.CAP_GSTREAMER)
        except Exception as e:
            print(f"Failed to initialize camera: {e}")
        pass

    def __del__(self):
        self.cap.release()
        cv2.destroyAllWindows()
        
    def get_frame(self):
        success, image = self.cap.read()
        if image is not None:
            ret, jpeg = cv2.imencode('.jpg', image)
            return jpeg.tobytes()
        return None