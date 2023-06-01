import cv2
from camera import VideoCamera

def test_video_camera():
    camera = VideoCamera()
    success, frame = camera.video.read()

    if not success:
        print("Failed to read frame from camera.")
        return

    ret, jpeg = cv2.imencode('.jpg', frame)

    if not ret:
        print("Failed to encode frame as JPEG.")
        return

    # Display the frame to ensure it's captured correctly
    cv2.imshow("Frame", frame)
    cv2.waitKey(0)  # Wait for any key press
    cv2.destroyAllWindows()

if __name__ == "__main__":
    test_video_camera()
