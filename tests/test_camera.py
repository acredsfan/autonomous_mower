import cv2

cap = cv2.VideoCapture(0) # 0 for the default camera

ret, frame = cap.read()
if ret:
    cv2.imwrite('test_image.jpg', frame)

cap.release()