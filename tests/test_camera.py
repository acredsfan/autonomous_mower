import cv2

try:
    # cap = cv2.VideoCapture(1)  # Change the number to test other devices
    cap = cv2.VideoCapture('v4l2src device=/dev/video0 ! videoconvert ! appsink', cv2.CAP_GSTREAMER)

    ret, frame = cap.read()

    if ret:
        cv2.imwrite('test_image.jpg', frame)
        print('Image captured successfully.')
    else:
        print('Failed to capture image')
        
    cap.release()

except KeyboardInterrupt:
    print('Aborted by user (Ctrl + C).')