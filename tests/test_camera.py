import cv2
import signal

# Function to handle timeout
def timeout_handler(signum, frame):
    print("Timeout reached while trying to access the camera.")
    raise TimeoutError

# Setup the signal to trigger timeout
signal.signal(signal.SIGALRM, timeout_handler)

def test_camera_with_gstreamer():
    # GStreamer pipeline for accessing the camera via libcamera
    pipeline = (
        "libcamerasrc ! "
        "video/x-raw,width=640,height=480,framerate=30/1 ! "
        "videoconvert ! appsink"
    )

    # Set a timeout of 10 seconds
    signal.alarm(10)

    try:
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
    except TimeoutError:
        print("Failed to capture a frame within the timeout period.")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        # Properly release the capture and set the alarm off
        cap.release()
        signal.alarm(0)  # Disable the alarm

if __name__ == "__main__":
    test_camera_with_gstreamer()
