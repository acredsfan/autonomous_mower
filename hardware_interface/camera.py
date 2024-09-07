import cv2
import threading
import logging
from queue import Queue, Empty
import numpy as np
import tflite_runtime.interpreter as tflite

logging.basicConfig(filename='main.log', level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s')

class SingletonCamera:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(SingletonCamera, cls).__new__(cls)
                cls._instance.init_camera()
        return cls._instance

    def init_camera(self):
        self.frame_queue = Queue(maxsize=1)
        self.cap = cv2.VideoCapture(0)
        self.running = True
        self.read_thread = threading.Thread(target=self.update, daemon=True)
        self.read_thread.start()

    def update(self):
        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                logging.warning("Failed to read frame from camera")
                continue
            # Replace old frame with new one
            if not self.frame_queue.empty():
                try:
                    self.frame_queue.get_nowait()  # Discard the old frame
                except Empty:
                    pass
            self.frame_queue.put(frame)

    def get_frame(self):
        try:
            # Return the latest frame without blocking
            return self.frame_queue.get(timeout=0.1)
        except Empty:
            logging.warning("Frame queue is empty")
            return None

    def stop_camera(self):
        self.running = False
        self.read_thread.join()
        self.cap.release()

    def __del__(self):
        self.stop_camera()

    def cleanup(self):
        if self.cap is not None:
            self.cap.release()
            print("Camera released successfully.")

class CameraProcessor:
    def __init__(self):
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
        image = cv2.resize(image, target_size)
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        image = image / 255.0
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
        image = self.camera.get_frame()  # Get the latest frame
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