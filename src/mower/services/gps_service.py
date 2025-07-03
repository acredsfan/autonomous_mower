import threading
from mower.navigation.gps import GpsPosition, GpsLatestPosition
from mower.utilities.logger_config import LoggerConfigInfo

class GpsService:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(GpsService, cls).__new__(cls)
                cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.logger = LoggerConfigInfo.get_logger(__name__)
        self.gps_position = None
        self.gps_latest_position = None
        self._thread = None
        self._stop_event = threading.Event()
        self._initialized = True

    def start(self, serial_port="/dev/ttyACM0"):
        if self._thread and self._thread.is_alive():
            self.logger.warning("GPS service already running.")
            return

        self.gps_position = GpsPosition(serial_port=serial_port)
        self.gps_latest_position = GpsLatestPosition(self.gps_position)
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        self.logger.info("GPS service started.")

    def _run(self):
        try:
            self.gps_position.start()
            while not self._stop_event.is_set():
                # Perform any periodic checks or updates here
                self._stop_event.wait(1)
        except Exception as e:
            self.logger.error(f"Error in GPS service: {e}")

    def shutdown(self):
        if self._stop_event.is_set():
            self.logger.warning("GPS service already stopped.")
            return

        self._stop_event.set()
        if self._thread:
            self._thread.join()
        self.gps_position = None
        self.gps_latest_position = None
        self.logger.info("GPS service stopped.")

    def get_position(self):
        if self.gps_position:
            return self.gps_position.get_latest_position()
        return None

    def get_metadata(self):
        if self.gps_position:
            return self.gps_position.get_latest_metadata()
        return None
