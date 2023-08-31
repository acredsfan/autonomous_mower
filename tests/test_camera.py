import cv2

# Initialize the camera
cap = cv2.VideoCapture(0)

# Check if the camera opened successfully
if not cap.isOpened():
    print("Error: Could not open camera.")
    exit()

# Capture a single frame
ret, frame = cap.read()

# Save the frame as a JPEG file
if ret:
    cv2.imwrite("captured_frame.jpg", frame)
else:
    print("Error: Could not read frame.")

# Release the camera
cap.release()