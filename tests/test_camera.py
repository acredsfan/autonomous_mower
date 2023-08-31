import cv2
import logging

logging.basicConfig(level=logging.DEBUG)
cap = None  # Initialize outside try block

try:
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Couldn't open the camera.")
    else:
        ret, frame = cap.read()
        if ret:
            #cv2.imshow('Test Frame', frame)
            cv2.waitKey(0)
        else:
            print("Error: Couldn't read a frame from the camera.")
except KeyboardInterrupt:
    print("Interrupted.")
except Exception as e:
    print(f"An error occurred: {e}")
finally:
    if cap:
        cap.release()
    cv2.destroyAllWindows()