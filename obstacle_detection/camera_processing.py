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

# Example usage
if __name__ == "__main__":
    # Read an example image from your camera
    cap = cv2.VideoCapture(0)  # Use 0 for default camera
    ret, frame = cap.read()
    
    if ret:
        obstacle_label = classify_obstacle(frame)
        print(f"Detected obstacle type: {obstacle_label}")
    
    cap.release()

