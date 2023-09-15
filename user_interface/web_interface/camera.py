import cv2

class VideoCamera(object):
    def __init__(self):
        # Use OpenCV to capture from Raspberry Pi camera module
        self.cap = cv2.VideoCapture('v4l2src device=/dev/video0 ! videoconvert ! appsink', cv2.CAP_GSTREAMER)

    def __del__(self):
        if hasattr(self, 'cap'):
            self.cap.release()

    def get_frame(self):
        success, image = self.cap.read()
        # We are using Motion JPEG, but OpenCV defaults to capture raw images,
        # so we must encode it into JPEG in order to correctly display the
        # video stream.
        if image is not None:
            ret, jpeg = cv2.imencode('.jpg', image)
            return jpeg.tobytes()