# Code for the camera processing module
# Uses OpenCV to detect obstacles and calculate the distance to them

#IMPORTS
import cv2
import numpy as np

class CameraProcessor:

    import cv2
import numpy as np
import tensorflow as tf

# Load pre-trained MobileNetV2 model + higher level layers
model = tf.keras.applications.MobileNetV2(weights='imagenet', input_shape=(224, 224, 3))

def preprocess_image(image):
    # Resize the image to (224, 224) that MobileNetV2 expects
    image = cv2.resize(image, (224, 224))
    
    # Convert the BGR image to RGB
    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    
    # Normalize to [0,1]
    image = image / 255.0
    
    # Expand dimensions to fit the model input shape
    image = np.expand_dims(image, axis=0)
    
    return image

def classify_obstacle(image):
    processed_image = preprocess_image(image)
    
    # Get model predictions
    predictions = model.predict(processed_image)
    
    # Decode predictions to class labels and get the label with the highest probability
    label = tf.keras.applications.mobilenet_v2.decode_predictions(predictions)[0][0][1]
    
    return label


    # def __init__(self, resolution=(640, 480), framerate=30):
    #     self.resolution = resolution
    #     self.framerate = framerate
    #     self.camera = cv2.VideoCapture('v4l2src device=/dev/video0 ! videoconvert ! appsink', cv2.CAP_GSTREAMER)
    #     self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, resolution[0])
    #     self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, resolution[1])
    #     self.camera.set(cv2.CAP_PROP_FPS, framerate)

    # def capture_frame(self):
    #     ret, frame = self.camera.read()
    #     if not ret:
    #         raise Exception("Failed to capture frame from the camera.")
    #     return frame

    # def detect_obstacles(self, frame):
    #     # Preprocess the image
    #     gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    #     blurred_frame = cv2.GaussianBlur(gray_frame, (5, 5), 0)

    #     # Detect edges
    #     edges = cv2.Canny(blurred_frame, 50, 150)

    #     # Find contours
    #     contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    #     obstacles = []
    #     for contour in contours:
    #         # Filter contours based on size, shape, or other features
    #         if cv2.contourArea(contour) > 1000:
    #             x, y, w, h = cv2.boundingRect(contour)
    #             obstacles.append((x, y, w, h))

    #     return obstacles

    # def process_frame(self):
    #     frame = self.capture_frame()
    #     obstacles = self.detect_obstacles(frame)
    #     return obstacles

    # def close(self):
    #     self.camera.release()

# Example usage
if __name__ == "__main__":
    # Read an example image from your camera
    cap = cv2.VideoCapture(0)  # Use 0 for default camera
    ret, frame = cap.read()
    
    if ret:
        obstacle_label = classify_obstacle(frame)
        print(f"Detected obstacle type: {obstacle_label}")
    
    cap.release()

