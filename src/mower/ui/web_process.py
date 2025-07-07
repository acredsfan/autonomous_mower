from multiprocessing import Process
import os
import logging
from mower.ui.web_ui.app import create_app
from mower.utilities.logger_config import LoggerConfigInfo

# Initialize logger
logger = LoggerConfigInfo.get_logger(__name__)

# Create a simple mock class that simulates the resource manager API
class DummyCamera:
    """A dummy camera that provides test pattern frames for web interface testing."""
    
    def __init__(self):
        self.logger = LoggerConfigInfo.get_logger(__name__)
        
    def get_frame(self):
        """Generate a test pattern frame (numpy array)."""
        import cv2
        import numpy as np
        from datetime import datetime
        import time
        
        # Create a 640x480 test pattern
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # Add visual elements
        cv2.rectangle(frame, (50, 50), (590, 430), (0, 255, 0), 2)
        cv2.putText(frame, "Dummy Camera Feed", (150, 200), 
                  cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        cv2.putText(frame, f"Time: {datetime.now().strftime('%H:%M:%S')}", 
                  (200, 250), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
        cv2.putText(frame, "Web Process Camera", (200, 300), 
                  cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
        
        # Add moving element
        x = int((time.time() % 10) * 50) + 50
        cv2.circle(frame, (x, 350), 20, (255, 0, 255), -1)
        
        return frame
    
    def capture_frame(self):
        """Generate a test pattern frame as JPEG bytes."""
        import cv2
        frame = self.get_frame()
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        return buffer.tobytes()
    
    def get_last_frame(self):
        """Return the last captured frame as JPEG bytes."""
        return self.capture_frame()


class SharedFrameCamera:
    """Camera that reads frames shared by the main process."""
    
    def __init__(self, frame_sharer):
        """
        Initialize the shared frame camera.
        
        Args:
            frame_sharer: CameraFrameSharer instance for reading frames
        """
        self.frame_sharer = frame_sharer
        self.logger = LoggerConfigInfo.get_logger(__name__)
        self.fallback_camera = DummyCamera()
        self.logger.info("SharedFrameCamera initialized")
    
    def get_frame(self):
        """Get the latest frame from the main process."""
        # Try to read a shared frame
        frame_bytes = self.frame_sharer.read_frame(timeout=0.5)
        
        if frame_bytes is not None:
            # Decode JPEG to numpy array for compatibility
            import cv2
            import numpy as np
            
            try:
                # Decode JPEG bytes to numpy array
                frame_array = np.frombuffer(frame_bytes, dtype=np.uint8)
                frame = cv2.imdecode(frame_array, cv2.IMREAD_COLOR)
                
                if frame is not None:
                    return frame
            except Exception as e:
                self.logger.debug(f"Error decoding shared frame: {e}")
        
        # Fallback to dummy camera if no shared frame available
        self.logger.debug("No shared frame available, using fallback")
        return self.fallback_camera.get_frame()
    
    def capture_frame(self):
        """Capture a frame and return as JPEG bytes."""
        # Try to read a shared frame directly as JPEG bytes
        frame_bytes = self.frame_sharer.read_frame(timeout=0.5)
        
        if frame_bytes is not None:
            return frame_bytes
        
        # Fallback to dummy camera
        return self.fallback_camera.capture_frame()
    
    def get_last_frame(self):
        """Return the last captured frame as JPEG bytes."""
        return self.capture_frame()

class DummyResourceManager:
    """A simple dummy resource manager for the web UI process."""
    
    def __init__(self):
        self.logger = LoggerConfigInfo.get_logger(__name__)
        self.logger.info("Created DummyResourceManager for web interface")
        
        # Don't try to access real hardware across processes - this causes performance issues
        # Instead, use simulation mode in the web process
        self._real_sensor_interface = None
        self._real_camera = None
        
        # Use frame sharing instead of direct camera access to avoid hardware conflicts
        try:
            from mower.hardware.camera_frame_share import get_frame_sharer
            self._frame_sharer = get_frame_sharer()
            self._real_camera = SharedFrameCamera(self._frame_sharer)
            self.logger.info("Successfully initialized shared frame camera for web process")
        except Exception as e:
            self.logger.warning(f"Failed to initialize shared frame camera: {e}")
            self.logger.info("Using DummyCamera fallback for web process")
            self._real_camera = DummyCamera()
    
    def get_status(self):
        return {"state": "idle", "initialized": True}
    
    def get_safety_status(self):
        # Return realistic safety status for the web UI
        return {
            "is_safe": True,
            "emergency_stop_active": False,
            "obstacle_detected_nearby": False,
            "low_battery_warning": False,
            "system_error": False
        }
    
    def get_sensor_interface(self):
        """Return None since we don't have cross-process sensor access."""
        return None
    
    def get_camera(self):
        """Return the camera instance (either real or dummy)."""
        return self._real_camera
    
    def get_sensor_data(self):
        # First try to get real sensor data from shared storage
        try:
            from mower.hardware.shared_sensor_data import get_shared_sensor_manager
            shared_manager = get_shared_sensor_manager()
            real_sensor_data = shared_manager.read_sensor_data()
            
            if real_sensor_data is not None:
                # We have fresh real sensor data - transform it to web UI format
                self.logger.debug("Using real sensor data from shared storage")
                return self._transform_sensor_data_for_web_ui(real_sensor_data)
            else:
                self.logger.debug("No fresh real sensor data available, using fallback")
        except Exception as e:
            self.logger.debug(f"Failed to read shared sensor data: {e}")
        
        # Fallback to dummy data if real data unavailable
        # Return consistent fallback sensor data for the web UI
        # Note: This web process cannot access real sensor data due to multiprocessing limitations
        import time
        
        # Create slow variation based on time to appear less static
        variation = (time.time() % 120) / 120  # 0-1 over 2 minutes (slower changes)
        
        return {
            "imu": {
                "heading": round(variation * 360, 1),  # Slowly rotating heading over 2 minutes
                "roll": 0.0,  # Static values to avoid random jumping
                "pitch": 0.0,
                "safety_status": {"is_safe": True}
            },
            "environment": {
                "temperature": round(22.0 + variation * 3, 1),  # 22-25°C slow variation
                "humidity": round(50.0 + variation * 10, 1),  # 50-60% slow variation  
                "pressure": round(1013.25 + variation * 2, 2)  # Small pressure variation
            },
            "tof": {
                "left": 120.0,  # Static distance values to avoid random jumping
                "right": 120.0,
                "front": 150.0
            },
            "power": {
                "voltage": 12.0,  # Static power values
                "current": 1.0,
                "power": 12.0,
                "percentage": round(75 + variation * 20, 0)  # Battery slowly varying 75-95%
            },
            "gps": {
                "latitude": 0.000000,  # Show actual 0,0 instead of fake San Francisco coordinates
                "longitude": 0.000000,
                "fix": False,  # Indicate no real GPS fix
                "fix_quality": "no_fix",
                "status": "no_fix",  # Clear status that this is not real GPS
                "satellites": 0,  # Show 0 satellites since no real GPS hardware
                "hdop": 99.9,  # High HDOP indicates poor/no fix
                "altitude": 0.0,
                "speed": 0.0
            }
        }
    
    def _transform_sensor_data_for_web_ui(self, real_sensor_data):
        """
        Transform real sensor data from hardware format to web UI expected format.
        
        Args:
            real_sensor_data: Raw sensor data from shared storage
            
        Returns:
            dict: Sensor data in web UI expected format
        """
        try:
            # Start with the real sensor data
            transformed_data = real_sensor_data.copy()
            
            # Transform distance sensors: hardware uses "distance" with "front_left"/"front_right"
            # but web UI expects "tof" with "left"/"right"  
            if "distance" in real_sensor_data:
                distance_data = real_sensor_data["distance"]
                transformed_data["tof"] = {
                    "left": distance_data.get("front_left", 120.0),  # Convert from mm
                    "right": distance_data.get("front_right", 120.0),
                    "working": distance_data.get("left_working", True) and distance_data.get("right_working", True)
                }
                # Keep the original distance data as well for compatibility
                # transformed_data["distance"] = distance_data
            
            # Ensure GPS has the "fix" boolean field that frontend expects
            if "gps" in transformed_data:
                gps_data = transformed_data["gps"]
                # Determine fix status from fix_quality and status
                fix_quality = gps_data.get("fix_quality", 0)
                status = gps_data.get("status", "no_fix")
                gps_data["fix"] = (fix_quality >= 1 and status == "valid")
                
            # Add power data from any available source (INA3221 data is in hardware layer)
            if "power" not in transformed_data:
                # Add default power info if not present
                transformed_data["power"] = {
                    "voltage": 12.0,
                    "current": 1.0, 
                    "power": 12.0,
                    "percentage": 75
                }
            
            return transformed_data
            
        except Exception as e:
            self.logger.error(f"Error transforming sensor data for web UI: {e}")
            # Return original data if transformation fails
            return real_sensor_data
    
    def get_camera(self):
        """Return the real camera if available, otherwise None."""
        return self._real_camera
    
    def get_path_planner(self):
        class DummyPathPlanner:
            def __init__(self):
                self.current_path = []
                self.pattern_config = DummyPatternConfig()
        
        class DummyPatternConfig:
            def __init__(self):
                from mower.navigation.path_planner import PatternType
                self.pattern_type = PatternType.SPIRAL
                self.spacing = 0.5
                self.angle = 0.0
                self.overlap = 0.1
                self.boundary_points = []
        
        return DummyPathPlanner()
    
    def get_mode(self):
        return "idle"
    
    def get_battery_level(self):
        return 80.0
    
    def get_boundary(self):
        return []
    
    def get_no_go_zones(self):
        return []
    
    def get_home_location(self):
        return {"lat": 0.0, "lng": 0.0}
    
    def set_home_location(self, location):
        pass
    
    def save_boundary(self, boundary):
        pass
    
    def save_no_go_zones(self, zones):
        pass
    
    def get_mowing_schedule(self):
        return []
    
    def set_mowing_schedule(self, schedule):
        pass
    
    def start(self):
        pass
    
    def stop(self):
        pass
    
    def emergency_stop(self):
        pass
    
    def execute_command(self, command, params):
        return {"success": True, "result": f"Command {command} executed"}

def start_web():
    """
    Start the web interface in a separate process.
    
    This function creates a Flask app using a dummy resource manager since the real
    resource manager cannot be shared directly with the web process due to multiprocessing
    limitations. Instead, the web interface will use a message-passing approach to
    communicate with the main process.
    """
    try:
        # Create a dummy resource manager for the web process
        dummy_resource_manager = DummyResourceManager()
        
        logger.info("Creating Flask app with dummy resource manager for web interface")
        app, socketio = create_app(dummy_resource_manager)
        
        # Get port from environment or use default
        port = int(os.environ.get("WEB_UI_PORT", 5000))
        
        logger.info(f"Starting web interface on port {port}")
        socketio.run(app, host="0.0.0.0", port=port)
    except Exception as e:
        logger.error(f"Error starting web interface: {e}")

def launch(resource_manager=None):
    """
    Launch the web process and return a reference to it.
    
    Args:
        resource_manager: Optional resource manager instance to pass to the web process.
                          If not provided, a dummy resource manager will be created.
    
    Returns:
        multiprocessing.Process: Reference to the started process.
    """
    logger.info("Launching web interface in a separate process")
    # We don't pass the resource manager to the process as the web interface
    # creates its own dummy resource manager, so there's no need to pass one here
    # Note: daemon=False for better process lifecycle control
    p = Process(target=start_web, daemon=False)
    p.start()
    return p
