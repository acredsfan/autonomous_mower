import numpy as np
import threading
import logging
from queue import Queue, Empty
import tflite_runtime.interpreter as tflite
import time
import cv2  # Only used for display and utility functions, not for detection

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
        # Close any existing capture object
        if self.cap is not None:
            self.cap.release()
            logging.info("Releasing previous camera capture.")
        
        # Attempt to reopen the camera
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
            self.running = False  # Stop the camera update thread if initialization fails

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

            # Discard the old frame if the queue is full
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
            # Load TFLite models
            self.obstacle_interpreter = tflite.Interpreter(
                model_path="/path/to/efficientdet-lite0.tflite")
            self.obstacle_interpreter.allocate_tensors()
            self.surface_interpreter = tflite.Interpreter(
                model_path="/home/pi/autonomous_mower/obstacle_detection/surface_type_model.tflite")
            self.surface_interpreter.allocate_tensors()
        except (FileNotFoundError, ValueError) as e:
            logging.error(f"Failed to initialize TFLite interpreters: {e}")

        # Input and output details
        self.obstacle_input_details = self.obstacle_interpreter.get_input_details()
        self.obstacle_output_details = self.obstacle_interpreter.get_output_details()
        self.surface_input_details = self.surface_interpreter.get_input_details()
        self.surface_output_details = self.surface_interpreter.get_output_details()

    def preprocess_image(self, image, target_size=(224, 224)):
        """Preprocess the image for the TFLite model."""
        image = cv2.resize(image, target_size)
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        image = image / 255.0
        image = np.expand_dims(image, axis=0).astype(np.float32)
        return image

    def classify_surface(self, image):
        """Classify the surface to determine if it's likely grass."""
        processed_image = self.preprocess_image(image, target_size=(224, 224))
        self.surface_interpreter.set_tensor(self.surface_input_details[0]['index'], processed_image)
        self.surface_interpreter.invoke()
        output_data = self.surface_interpreter.get_tensor(self.surface_output_details[0]['index'])
        probability_of_grass = output_data[0][0]
        return probability_of_grass > 0.5

    def classify_obstacle(self):
        """Classify objects in the frame using the obstacle detection model."""
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
        """Process the results from the TFLite model to extract detected objects."""
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
        results = self.classify_obstacle()
        if results:
            logging.info(f"Obstacle detected: {results}")
            return True
        else:
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
        dropoff_detected = camera_processor.detect_obstacle()
        print(f"Drop-off detected: {dropoff_detected}")