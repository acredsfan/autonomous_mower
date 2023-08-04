import cv2

# Define the GStreamer pipeline
pipeline = (
    "v4l2src device=/dev/video0 ! "
    "videoconvert ! "
    "appsink"
)

# Open the camera using the defined pipeline
cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)

try:
    ret, frame = cap.read()

    if ret:
        cv2.imwrite('test_image.jpg', frame)
        print('Image captured successfully.')
    else:
        print('Failed to capture image')

    cap.release()

except KeyboardInterrupt:
    print('Aborted by user (Ctrl + C).')