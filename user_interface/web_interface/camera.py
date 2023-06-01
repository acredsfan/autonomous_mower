# import cv2  

# class VideoCamera(object):
#     def __init__(self):
#         # Use OpenCV to caputure from Raspberry Pi camera module  
#         self.cap = cv2.VideoCapture(0)

#     def __del__(self):   
#         if hasattr(self, 'cap'):  
#             self.cap.release()  

#     def get_frame(self):  
#         success, image = self.cap.read()  
#         # We are using Motion JPEG, but OpenCV defaults to capture raw images,  
#         # so we must encode it into JPEG in order to correctly display the  
#         # video stream.  
#         ret, jpeg = cv2.imencode('.jpg', image)  
#         return jpeg.tobytes()
    
from picamera import PiCamera

class VideoCamera(object):
    def __init__(self):
        # Use the PiCamera class to capture from Raspberry Pi camera module  
        self.camera = PiCamera()

    def __del__(self):   
        if hasattr(self, 'camera'):  
            self.camera.close()  

    def get_frame(self):  
        # Capture a frame from the camera
        frame = self.camera.capture()
        # Convert the frame to a JPEG image
        jpeg = frame.to_jpeg()
        # Return the JPEG image
        return jpeg