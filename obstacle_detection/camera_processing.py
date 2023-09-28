# Code for the camera processing module
# Uses OpenCV to detect obstacles and calculate the distance to them

# IMPORTS
import cv2
import numpy as np
import tflite_runtime.interpreter as tflite
from user_interface.web_interface.camera import SingletonCamera
import logging

# Initialize logging
logging.basicConfig(filename='main.log', level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s')

class CameraProcessor:
    # Initialize the TFLite interpreter
    interpreter = tflite.Interpreter(model_path="/home/pi/autonomous_mower/obstacle_detection/lite-model_qat_mobilenet_v2_retinanet_256_1.tflite")
    interpreter.allocate_tensors()
    # Initialize Camera
    camera = SingletonCamera()
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

    def classify_obstacle(self, image):  # Added 'self'
        processed_image = self.preprocess_image(image)  # Call static method

        # Run inference
        self.interpreter.set_tensor(self.input_details[0]['index'], processed_image)  # Added 'self'
        self.interpreter.invoke()  # Added 'self'

        # Get the detection results
        detection_boxes = self.interpreter.get_tensor(self.output_details[0]['index'])  # Added 'self'
        detection_classes = self.interpreter.get_tensor(self.output_details[1]['index'])  # Added 'self'
        detection_scores = self.interpreter.get_tensor(self.output_details[2]['index'])  # Added 'self'

        # Process the results
        label = self.process_results(detection_boxes, detection_classes, detection_scores)  # Added 'self'
        
        return label

    def process_results(self, detection_boxes, detection_classes, detection_scores):
        # Assuming a threshold of 0.5 for detection
        threshold = 0.5
        detected_objects = []

        for i in range(len(detection_scores[0])):
            if detection_scores[0][i] > threshold:
                # Get the class and bounding box
                class_id = int(detection_classes[0][i])
                box = detection_boxes[0][i]

                # You can map the class_id to a label if you have a mapping
                # For example, if class_id 1 is 'tree', 2 is 'rock', etc.
                label = f'Class {class_id}'  # Replace this with actual label mapping

                detected_objects.append({'label': label, 'box': box})

        return detected_objects

# Example usage
if __name__ == "__main__":
    camera_processor = CameraProcessor()  # Create an instance
    cap = cv2.VideoCapture(0)
    ret, frame = cap.read()
    
    if ret:
        obstacle_label = camera_processor.classify_obstacle(frame)  # Use the instance to call the method
        print(f"Detected obstacle type: {obstacle_label}")
    
    cap.release()