import cv2
import logging

logging.basicConfig(level=logging.DEBUG)

try:
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Couldn't open the camera.")
    else:
        ret, frame = cap.read()
        if ret:
            cv2.imshow('Test Frame', frame)
            cv2.waitKey(0)
        else:
            print("Error: Couldn't read a frame from the camera.")
finally:
    cap.release()
    cv2.destroyAllWindows()