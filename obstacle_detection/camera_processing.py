# Code for the camera processing module
# Uses OpenCV to detect obstacles and calculate the distance to them

# IMPORTS
import cv2
import numpy as np
import tflite_runtime.interpreter as tflite

class CameraProcessor:
    # Initialize the TFLite interpreter
    interpreter = tflite.Interpreter(model_path="lite-model_qat_mobilenet_v2_retinanet_256_1.tflite")
    interpreter.allocate_tensors()

    # Get input and output details
    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()

    def preprocess_image(image):
        # Resize the image to (224, 224)
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
        
        # Run inference
        interpreter.set_tensor(input_details[0]['index'], processed_image)
        interpreter.invoke()

        # Get the detection results
        detection_boxes = interpreter.get_tensor(output_details[0]['index'])
        detection_classes = interpreter.get_tensor(output_details[1]['index'])
        detection_scores = interpreter.get_tensor(output_details[2]['index'])

        # Process the results (you'll need to implement this part)
        label = process_results(detection_boxes, detection_classes, detection_scores)
        
        return label

# Implement this function to handle the detection results
def process_results(detection_boxes, detection_classes, detection_scores):
    # Your code here to process the results and return the label
    pass

# Example usage
if __name__ == "__main__":
    # Read an example image from your camera
    cap = cv2.VideoCapture(0)  # Use 0 for default camera
    ret, frame = cap.read()
    
    if ret:
        obstacle_label = classify_obstacle(frame)
        print(f"Detected obstacle type: {obstacle_label}")
    
    cap.release()