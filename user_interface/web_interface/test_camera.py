import cv2

# Try different indices
for i in range(0, 10):
    cap = cv2.VideoCapture(i)
    if cap.read()[0]:
        print(f'Camera detected at index {i}')
        ret, frame = cap.read()
        cv2.imwrite(f'camera_test_{i}.jpg', frame)
        cap.release()
    else:
        print(f'No camera detected at index {i}')