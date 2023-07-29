import cv2

cap = cv2.VideoCapture(0)  # Change the number to test other devices

ret, frame = cap.read()

if ret:
    cv2.imwrite('test_image.jpg', frame)
else:
    print('Failed to capture image')

cap.release()