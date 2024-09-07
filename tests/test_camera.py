import cv2

def test_camera_with_gstreamer():
    # GStreamer pipeline for accessing the camera via libcamera
    pipeline = "libcamerasrc ! video/x-raw,width=640,height=480,framerate=30/1 ! videoconvert ! appsink"

    # Open the camera with the GStreamer pipeline
    cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
    
    if not cap.isOpened():
        print("Unable to open camera using GStreamer pipeline.")
        return

    # Try reading a frame from the camera
    ret, frame = cap.read()
    if ret:
        print("Camera detected, frame captured successfully using GStreamer.")
        cv2.imwrite('camera_test_gstreamer.jpg', frame)
    else:
        print("Failed to capture a frame from the camera using GStreamer.")
    
    # Release the camera resource
    cap.release()

if __name__ == "__main__":
    test_camera_with_gstreamer()

