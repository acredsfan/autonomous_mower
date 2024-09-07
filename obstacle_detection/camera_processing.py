import cv2
import numpy as np
import tflite_runtime.interpreter as tflite

import logging

# Initialize logging
logging.basicConfig(filename='main.log', level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s')

class CameraProcessor:
    def __init__(self):
        from user_interface.web_interface.camera import SingletonCamera
        self.camera = SingletonCamera()
        # Initialize the TFLite interpreter for obstacle detection
        self.obstacle_interpreter = tflite.Interpreter(model_path="/home/pi/autonomous_mower/obstacle_detection/lite-model_qat_mobilenet_v2_retinanet_256_1.tflite")
        self.obstacle_interpreter.allocate_tensors()
        # Initialize the TFLite interpreter for surface type classification
        self.surface_interpreter = tflite.Interpreter(model_path="/home/pi/autonomous_mower/obstacle_detection/surface_type_model.tflite")
        self.surface_interpreter.allocate_tensors()

        # Get input and output details for both models
        self.obstacle_input_details = self.obstacle_interpreter.get_input_details()
        self.obstacle_output_details = self.obstacle_interpreter.get_output_details()
        self.surface_input_details = self.surface_interpreter.get_input_details()
        self.surface_output_details = self.surface_interpreter.get_output_details()

    @staticmethod
    def preprocess_image(image, target_size=(224, 224)):
        # Resize the image to target size (default is 224x224)
        image = cv2.resize(image, target_size)
        # Convert the BGR image to RGB
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        # Normalize to [0,1]
        image = image / 255.0
        # Expand dimensions to fit the model input shape
        image = np.expand_dims(image, axis=0)
        return image

    def classify_surface(self, image):
        processed_image = self.preprocess_image(image, target_size=(224, 224))  # Ensure this matches your model's input size
        self.surface_interpreter.set_tensor(self.surface_input_details[0]['index'], processed_image)
        self.surface_interpreter.invoke()
        # Assuming the output is a single float representing the probability of being on grass
        output_data = self.surface_interpreter.get_tensor(self.surface_output_details[0]['index'])
        probability_of_grass = output_data[0][0]
        return probability_of_grass > 0.5  # Returns True if the surface is likely grass

    def classify_obstacle(self):
        image = self.camera.get_frame()
        if image is None:
            logging.warning("No frame available for obstacle detection.")
            return None

        if self.classify_surface(image):
            logging.info("Surface classified as grass, proceeding with obstacle detection.")
            processed_image = self.preprocess_image(image)
            self.obstacle_interpreter.set_tensor(self.obstacle_input_details[0]['index'], processed_image)
            self.obstacle_interpreter.invoke()
            detection_boxes = self.obstacle_interpreter.get_tensor(self.obstacle_output_details[0]['index'])
            detection_classes = self.obstacle_interpreter.get_tensor(self.obstacle_output_details[1]['index'])
            detection_scores = self.obstacle_interpreter.get_tensor(self.obstacle_output_details[2]['index'])
            label = self.process_results(detection_boxes, detection_classes, detection_scores)
            return label
        else:
            logging.info("Surface not classified as grass, will not mow this area.")
            return None

    def process_results(self, detection_boxes, detection_classes, detection_scores):
        threshold = 0.5
        detected_objects = []
        for i in range(len(detection_scores[0])):
            if detection_scores[0][i] > threshold:
                class_id = int(detection_classes[0][i])
                box = detection_boxes[0][i]
                label = f'Class {class_id}'  # Replace with actual label mapping
                detected_objects.append({'label': label, 'box': box})
        return detected_objects
    
    def detect_obstacle(self):
        """
        Detect obstacles using the classify_obstacle method.
        Returns True if an obstacle is detected, otherwise False.
        """
        results = self.classify_obstacle()
        if results:
            logging.info(f"Obstacle detected: {results}")
            return True
        else:
            #logging.info("No obstacles detected.")
            return False

# Example usage
if __name__ == "__main__":
    camera_processor = CameraProcessor()
    while True:
        print(camera_processor.classify_obstacle())