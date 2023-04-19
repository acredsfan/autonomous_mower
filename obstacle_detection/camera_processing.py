# Code for the camera processing module
# Uses OpenCV to detect obstacles and calculate the distance to them

#IMPORTS
import cv2
import numpy as np

class CameraProcessor:
    def __init__(self, resolution=(640, 480), framerate=30):
        self.resolution = resolution
        self.framerate = framerate
        self.camera = cv2.VideoCapture(0)
        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, resolution[0])
        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, resolution[1])
        self.camera.set(cv2.CAP_PROP_FPS, framerate)

    def capture_frame(self):
        ret, frame = self.camera.read()
        if not ret:
            raise Exception("Failed to capture frame from the camera.")
        return frame

    def detect_obstacles(self, frame):
        # Preprocess the image
        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blurred_frame = cv2.GaussianBlur(gray_frame, (5, 5), 0)

        # Detect edges
        edges = cv2.Canny(blurred_frame, 50, 150)

        # Find contours
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        obstacles = []
        for contour in contours:
            # Filter contours based on size, shape, or other features
            if cv2.contourArea(contour) > 1000:
                x, y, w, h = cv2.boundingRect(contour)
                obstacles.append((x, y, w, h))

        return obstacles

    def process_frame(self):
        frame = self.capture_frame()
        obstacles = self.detect_obstacles(frame)
        return obstacles

    def close(self):
        self.camera.release()

if __name__ == "__main__":
    camera_processor = CameraProcessor()

    try:
        while True:
            obstacles = camera_processor.process_frame()
            print("Detected obstacles:", obstacles)

    except KeyboardInterrupt:
        print("Stopping camera processing...")

    finally:
        camera_processor.close()