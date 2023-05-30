import cv2

class VideoCamera(object):
    def __init__(self):
        # Using OpenCV to capture from device 0. If you have trouble capturing
        # from a webcam, comment the line below out and use a video file
        # instead.
        self.capture_width = 640
        self.capture_height = 480
        self.display_width = 640
        self.display_height = 480
        self.framerate = 90

        self.gstreamer_pipeline = (
            f"nvarguscamerasrc ! video/x-raw(memory:NVMM), "
            f"width=(int){self.capture_width}, height=(int){self.capture_height}, "
            f"format=(string)NV12, framerate=(fraction){self.framerate}/1 ! "
            f"nvvidconv flip-method=0 ! video/x-raw, width=(int){self.display_width}, height=(int){self.display_height}, format=(string)BGRx ! "
            f"videoconvert ! video/x-raw, format=(string)BGR ! appsink"
        )

        self.video = cv2.VideoCapture(self.gstreamer_pipeline, cv2.CAP_GSTREAMER)
    
    def __del__(self):
        self.video.release()
    
    def get_frame(self):
        success, image = self.video.read()
        # We are using Motion JPEG, but OpenCV defaults to capture raw images,
        # so we must encode it into JPEG in order to correctly display the
        # video stream.
        ret, jpeg = cv2.imencode('.jpg', image)
        return jpeg.tobytes()
