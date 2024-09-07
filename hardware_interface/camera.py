import numpy as np
import threading
import logging
from queue import Queue, Empty
import tflite_runtime.interpreter as tflite
import time
import cv2  # Only used for display and utility functions, not for detection
from dotenv import load_dotenv
import os

load_dotenv
PATH_TO_OBJECT_DETECTION_MODEL = os.getenv("OBSTACLE_MODEL_PATH")

logging.basicConfig(
    filename='main.log', 
    level=logging.DEBUG, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
)

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
        """Initialize the camera and start the update thread."""
        self.frame_queue = Queue(maxsize=1)
        self.cap = cv2.VideoCapture(0)  # Try opening the default camera
        self.running = True
        self.read_thread = threading.Thread(target=self.update, daemon=True)
        self.read_thread.start()

        # Check if the camera opened successfully
        if not self.cap.isOpened():
            logging.error("Failed to open the camera. Retrying...")
            self.reinitialize_camera()

    def reinitialize_camera(self):
        """Reinitialize the camera if it fails."""
        if self.cap is not None:
            self.cap.release()
            logging.info("Releasing previous camera capture.")
        
        attempts = 0
        while attempts < 5 and not self.cap.isOpened():
            self.cap = cv2.VideoCapture(0)
            if self.cap.isOpened():
                logging.info("Camera reinitialized successfully.")
                break
            attempts += 1
            logging.warning(f"Reinitialization attempt {attempts} failed. Retrying...")
            time.sleep(1)

        if not self.cap.isOpened():
            logging.error("Failed to reinitialize the camera after multiple attempts.")
            self.running = False

    def update(self):
        """Continuously read frames from the camera and add them to the queue."""
        while self.running:
            if not self.cap.isOpened():
                logging.warning("Camera is not open. Attempting reinitialization.")
                self.reinitialize_camera()
                continue

            ret, frame = self.cap.read()
            if not ret:
                logging.warning("Failed to read frame from camera. Attempting reinitialization.")
                self.reinitialize_camera()
                continue

            if not self.frame_queue.empty():
                try:
                    self.frame_queue.get_nowait()
                except Empty:
                    pass
            
            self.frame_queue.put(frame)

    def get_frame(self):
        """Get the latest frame from the queue."""
        try:
            return self.frame_queue.get(timeout=0.1)
        except Empty:
            logging.info("Frame queue is empty")
            return None

    def stop_camera(self):
        """Stop the camera and release resources."""
        self.running = False
        if self.read_thread.is_alive():
            self.read_thread.join()
        if self.cap is not None:
            self.cap.release()
            logging.info("Camera released successfully.")

    def __del__(self):
        self.stop_camera()

    def cleanup(self):
        """Clean up camera resources."""
        if self.cap is not None:
            self.cap.release()
            logging.info("Camera released successfully.")

class CameraProcessor:
    def __init__(self):
        self.camera = SingletonCamera()
        try:
            # Load the MobileNetV2 model for both object detection and surface classification
            self.interpreter = tflite.Interpreter(
                model_path="/path/to/mobilenet_v2.tflite")  # Update the path to your MobileNetV2 model
            self.interpreter.allocate_tensors()
        except (FileNotFoundError, ValueError) as e:
            logging.error(f"Failed to initialize TFLite interpreter: {e}")

        # Input and output details
        self.input_details = self.interpreter.get_input_details()
        self.output_details = self.interpreter.get_output_details()

    def preprocess_image(self, image, target_size=(224, 224)):
        """Preprocess the image for the TFLite model."""
        image = cv2.resize(image, target_size)
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        image = image / 255.0
        image = np.expand_dims(image, axis=0).astype(np.float32)
        return image

    def detect_objects(self, image):
        """Run object detection and surface classification using MobileNetV2."""
        processed_image = self.preprocess_image(image)
        self.interpreter.set_tensor(self.input_details[0]['index'], processed_image)
        self.interpreter.invoke()
        detection_boxes = self.interpreter.get_tensor(self.output_details[0]['index'])
        detection_classes = self.interpreter.get_tensor(self.output_details[1]['index'])
        detection_scores = self.interpreter.get_tensor(self.output_details[2]['index'])
        return self.process_results(detection_boxes, detection_classes, detection_scores)

    def process_results(self, detection_boxes, detection_classes, detection_scores):
        """Process the results from the TFLite model to extract detected objects and surfaces."""
        threshold = 0.5
        detected_objects = []
        for i in range(len(detection_scores[0])):
            if detection_scores[0][i] > threshold:
                class_id = int(detection_classes[0][i])
                box = detection_boxes[0][i]
                label = f'Class {class_id}'  # Replace with actual label mapping if available
                detected_objects.append({'label': label, 'box': box})
        return detected_objects

    def detect_obstacle(self):
        """Detect if any obstacles are present."""
        image = self.camera.get_frame()
        if image is None:
            logging.warning("No frame available for detection.")
            return False

        results = self.detect_objects(image)
        if results:
            logging.info(f"Obstacle detected: {results}")
            return True
        else:
            logging.info("No obstacles detected.")
            return False

# Singleton accessor function
camera_instance = SingletonCamera()  # Ensures the camera is initialized once

def get_camera_instance():
    """Accessor function to get the SingletonCamera instance."""
    return camera_instance

# Example usage
if __name__ == "__main__":
    camera_processor = CameraProcessor()
    while True:
        obstacle_detected = camera_processor.detect_obstacle()
        print(f"Obstacle detected: {obstacle_detected}")