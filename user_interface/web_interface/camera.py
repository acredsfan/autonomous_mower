import cv2
import threading
import logging
from queue import Queue, Empty

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
            if not self.frame_queue.empty():
                try:
                    self.frame_queue.get_nowait()  # Discard any old frame
                except Empty:
                    pass
            self.frame_queue.put(frame)

    def get_frame(self):
        if self.frame_queue.empty():
            logging.warning("Frame queue is empty")
            return None
        return self.frame_queue.get()

    def stop_camera(self):
        self.running = False
        self.read_thread.join()
        self.cap.release()

    def __del__(self):
        self.stop_camera()


# # Test the SingletonCamera
# if __name__ == "__main__":
#     cam1 = SingletonCamera()
#     frame = cam1.get_frame()
#     if frame is not None:
#         cv2.imwrite("test_frame.jpg", frame)
#     else:
#         logging.error("Failed to get frame.")