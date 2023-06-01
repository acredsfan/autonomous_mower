import cv2
from camera import VideoCamera

def test_video_camera():
    try:
        camera = VideoCamera()
    except Exception as e:
        print("Failed to initialize VideoCamera. Error: ", str(e))
        return

    try:
        success, frame = camera.video.read()
    except Exception as e:
        print("Failed to read frame from camera. Error: ", str(e))
        return

    if not success:
        print("Failed to read frame from camera.")
        return

    try:
        ret, jpeg = cv2.imencode('.jpg', frame)
    except Exception as e:
        print("Failed to encode frame as JPEG. Error: ", str(e))
        return

    if not ret:
        print("Failed to encode frame as JPEG.")
        return

    # Display the frame to ensure it's captured correctly
    try:
        cv2.imshow("Frame", frame)
        cv2.waitKey(0)  # Wait for any key press
        cv2.destroyAllWindows()
    except Exception as e:
        print("Failed to display frame. Error: ", str(e))
        return

if __name__ == "__main__":
    test_video_camera()