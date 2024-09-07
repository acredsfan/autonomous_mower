import cv2
import numpy as np
import threading
import logging
from queue import Queue, Empty
import tflite_runtime.interpreter as tflite

logging.basicConfig(filename='main.log', level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s')

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
            if not self.frame_queue.empty():
                try:
                    self.frame_queue.get_nowait()
                except Empty:
                    pass
            self.frame_queue.put(frame)

    def get_frame(self):
        try:
            return self.frame_queue.get(timeout=0.1)
        except Empty:
            logging.info("Frame queue is empty")
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
            logging.info("Camera released successfully.")

class CameraProcessor:
    def __init__(self):
        self.camera = SingletonCamera()
        try:
            self.obstacle_interpreter = tflite.Interpreter(
                model_path="/home/pi/autonomous_mower/obstacle_detection/lite-model_qat_mobilenet_v2_retinanet_256_1.tflite")
            self.obstacle_interpreter.allocate_tensors()
            self.surface_interpreter = tflite.Interpreter(
                model_path="/home/pi/autonomous_mower/obstacle_detection/surface_type_model.tflite")
            self.surface_interpreter.allocate_tensors()
        except (FileNotFoundError, ValueError) as e:
            logging.error(f"Failed to initialize TFLite interpreters: {e}")

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
        processed_image = self.preprocess_image(image, target_size=(224, 224))
        self.surface_interpreter.set_tensor(self.surface_input_details[0]['index'], processed_image)
        self.surface_interpreter.invoke()
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
        results = self.classify_obstacle()
        if results:
            logging.info(f"Obstacle detected: {results}")
            return True
        else:
            return False

    def detect_dropoff(self):
        """
        Detect potential drop-offs using edge detection and contour analysis.
        Returns True if a drop-off is suspected, otherwise False.
        """
        image = self.camera.get_frame()
        if image is None:
            logging.warning("No frame available for drop-off detection.")
            return False

        # Convert to grayscale and apply Gaussian blur
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)

        # Use Canny edge detection
        edges = cv2.Canny(blurred, 50, 150)

        # Find contours in the edged image
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        dropoff_detected = False

        for contour in contours:
            # Approximate the contour to simplify it
            peri = cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, 0.02 * peri, True)

            # Check if the contour is large enough to be a potential drop-off
            if cv2.contourArea(contour) > 500:  # This value can be adjusted based on testing
                # Analyze contour shape and area; sharp downward edges may indicate a drop-off
                x, y, w, h = cv2.boundingRect(approx)
                aspect_ratio = w / float(h)

                # Simple heuristic: elongated shapes with a low aspect ratio could indicate a drop-off
                if aspect_ratio < 0.5 or aspect_ratio > 2.0:
                    dropoff_detected = True
                    logging.info(f"Potential drop-off detected at location: x={x}, y={y}, width={w}, height={h}")

        if dropoff_detected:
            logging.info("Drop-off detected!")
        else:
            logging.info("No drop-offs detected.")
        
        return dropoff_detected
    
# Singleton accessor function
camera_instance = SingletonCamera()  # Ensures the camera is initialized once

def get_camera_instance():
    """Accessor function to get the SingletonCamera instance."""
    return camera_instance

# Example usage
if __name__ == "__main__":
    camera_processor = CameraProcessor()
    while True:
        dropoff_detected = camera_processor.detect_dropoff()
        print(f"Drop-off detected: {dropoff_detected}")