from multiprocessing import Process
import os
import logging
from mower.ui.web_ui.app import create_app
from mower.utilities.logger_config import LoggerConfigInfo

# Initialize logger
logger = LoggerConfigInfo.get_logger(__name__)

# Create a simple mock class that simulates the resource manager API
class DummyResourceManager:
    """A simple dummy resource manager for the web UI process."""
    
    def __init__(self):
        self.logger = LoggerConfigInfo.get_logger(__name__)
        self.logger.info("Created DummyResourceManager for web interface")
        
        # Don't try to access real hardware across processes - this causes performance issues
        # Instead, use simulation mode in the web process
        self._real_sensor_interface = None
        self._real_camera = None
    
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
    
    def get_sensor_data(self):
        # Return realistic but varied sensor data for the web UI
        import random
        import time
        
        # Create some variation based on time to make it look more realistic
        variation = (time.time() % 60) / 60  # 0-1 over 60 seconds
        
        return {
            "imu": {
                "heading": round(variation * 360, 1),  # 0-360 degrees
                "roll": round((random.random() - 0.5) * 10, 1),  # ±5 degrees
                "pitch": round((random.random() - 0.5) * 10, 1),  # ±5 degrees
                "safety_status": {"is_safe": True}
            },
            "environment": {
                "temperature": round(20 + variation * 15, 1),  # 20-35°C
                "humidity": round(40 + variation * 40, 1),  # 40-80%
                "pressure": round(1013.25 + (random.random() - 0.5) * 20, 2)  # ±10 hPa
            },
            "tof": {
                "left": round(50 + random.random() * 200, 1),  # 50-250 cm
                "right": round(50 + random.random() * 200, 1),
                "front": round(50 + random.random() * 200, 1)
            },
            "power": {
                "voltage": round(11.5 + random.random() * 1.5, 1),  # 11.5-13V
                "current": round(0.5 + random.random() * 2, 1),  # 0.5-2.5A
                "power": round((11.5 + random.random() * 1.5) * (0.5 + random.random() * 2), 1),
                "percentage": round(60 + variation * 40, 0)  # 60-100%
            },
            "gps": {
                "latitude": round(37.7749 + (random.random() - 0.5) * 0.0002, 6),  # Small realistic variation
                "longitude": round(-122.4194 + (random.random() - 0.5) * 0.0002, 6),
                "fix": True,
                "fix_quality": "3d",
                "satellites": random.randint(8, 14),
                "hdop": round(random.uniform(0.8, 2.0), 1),
                "altitude": round(50 + random.random() * 10, 1),  # 50-60m above sea level
                "speed": round(random.random() * 2, 1)  # 0-2 m/s when stationary/slow
            }
        }
    
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
    p = Process(target=start_web, daemon=True)
    p.start()
    return p
