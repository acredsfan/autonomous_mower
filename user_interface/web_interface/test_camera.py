import cv2

# Try different indices
for i in range(0, 10):
    cap = cv2.VideoCapture(i)
    if cap.read()[0]:
        print(f'Camera detected at index {i}')
        cap.release()
    else:
        print(f'No camera detected at index {i}')