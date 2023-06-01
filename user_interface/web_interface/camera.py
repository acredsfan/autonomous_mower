import cv2  

class VideoCamera(object):  
    def __init__(self):  
        # Use OpenCV to caputure from Raspberry Pi camera module  
        self.video = cv2.VideoCapture(0)  

    def __del__(self):   
        if hasattr(self, 'video'):  
        self.video.release()  

    def get_frame(self):  
        success, image = self.video.read()  
        # We are using Motion JPEG, but OpenCV defaults to capture raw images,  
        # so we must encode it into JPEG in order to correctly display the  
        # video stream.  
        ret, jpeg = cv2.imencode('.jpg', image)  
        return jpeg.tobytes()