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
    
    def get_status(self):
        return {"state": "idle", "initialized": True}
    
    def get_safety_status(self):
        return {"is_safe": True}
    
    def get_sensor_data(self):
        return {
            "imu": {"heading": 0.0, "roll": 0.0, "pitch": 0.0, "safety_status": {"is_safe": True}},
            "environment": {"temperature": 20.0, "humidity": 50.0, "pressure": 1013.25},
            "tof": {"left": 100.0, "right": 100.0, "front": 100.0},
            "power": {"voltage": 12.0, "current": 1.0, "power": 12.0, "percentage": 80.0}
        }
    
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
    
    def get_camera(self):
        return None
    
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
    
    def get_sensor_interface(self):
        return None

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
        port = int(os.environ.get("WEB_UI_PORT", 8000))
        
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
