import cv2

try:
    # Change this to the path of your camera
    camera_path = '/dev/video0'

    # Create a VideoCapture object
    cap = cv2.VideoCapture(camera_path)

    # Check if the camera opened successfully
    if not cap.isOpened():
        print(f"Error opening camera at {camera_path}")
    else:
        print(f"Successfully opened camera at {camera_path}")

        # Capture a single frame
        ret, frame = cap.read()

        # Check if the frame was captured successfully
        if ret:
            print("Frame captured successfully")
            cv2.imshow('Frame', frame)
            cv2.waitKey(0)
        else:
            print("Failed to capture frame")

        # Release the VideoCapture object
        cap.release()
        cv2.destroyAllWindows()

except KeyboardInterrupt:
    print('Aborted by user (Ctrl + C).')

import cv2