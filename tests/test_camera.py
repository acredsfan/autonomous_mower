import cv2


def test_camera_access():
    # Try to open the default camera index (usually 0)
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Unable to open the camera.")
        return

    # Try reading a frame from the camera
    ret, frame = cap.read()
    if ret:
        print("Camera detected, frame captured successfully.")
        # Save the captured frame to verify
        cv2.imwrite('camera_test.jpg', frame)
    else:
        print("Failed to capture a frame from the camera.")

    # Release the camera resource
    cap.release()


if __name__ == "__main__":
    test_camera_access()
