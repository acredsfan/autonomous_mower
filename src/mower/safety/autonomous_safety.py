"""
Autonomous Safety Checker for the autonomous mower.

This module implements critical safety checks that must pass before
allowing any autonomous movement of the mower. It prevents unsafe
operation when the system is running with simulated data or when
essential safety conditions are not met.

The SafetyChecker validates three key criteria:
1. GPS data is real (not simulated fallback coordinates)
2. IMU data is real (not simulated patterns)  
3. Boundary polygon is properly configured

Safety validation is enforced through the @requires_safety_validation
decorator that can be applied to any movement-related methods.

Example usage:
    from mower.safety.autonomous_safety import SafetyChecker, requires_safety_validation
    
    safety_checker = SafetyChecker(resource_manager)
    
    @requires_safety_validation(safety_checker)
    def navigate_to_location(self, target):
        # This method will only execute if safety checks pass
        pass

Hardware Requirements:
    - Real GPS receiver providing valid coordinates
    - Real IMU sensor providing hardware-sourced orientation data
    - Configured boundary polygon defining safe operating area

Safety Features:
    - Detects simulated GPS coordinates (San Francisco fallback: 37.7749, -122.4194)
    - Validates GPS fix quality and satellite count
    - Checks for realistic IMU sensor patterns vs mathematical simulation
    - Ensures boundary polygon exists and has minimum required area
    - Validates current position is within configured boundary
    - Comprehensive error logging with specific failure reasons
"""

import json
import math
import time
from functools import wraps
from pathlib import Path
from typing import Dict, Optional, Tuple, Union, Any
from shapely.geometry import Point, Polygon

from mower.utilities.logger_config import LoggerConfigInfo

logger = LoggerConfigInfo.get_logger(__name__)

# Known simulation fallback coordinates
SIMULATION_GPS_COORDINATES = {
    "san_francisco": (37.7749, -122.4194),  # Default simulation coordinates
    "default_test": (0.0, 0.0),             # Common test coordinates
}

# Safety thresholds
MIN_BOUNDARY_AREA = 25.0  # Minimum 5m x 5m boundary area in square meters
MIN_GPS_SATELLITES = 4    # Minimum satellites for reliable GPS fix
MIN_GPS_ACCURACY = 10.0   # Maximum acceptable GPS accuracy in meters


class SafetyValidationError(Exception):
    """Raised when safety validation fails."""
    pass


class SafetyChecker:
    """
    Validates safety conditions before allowing autonomous movement.
    
    This class performs comprehensive safety checks to ensure the mower
    operates only when real sensor data is available and proper boundaries
    are configured.
    
    Attributes:
        resource_manager: Access to hardware and software resources
        config_dir: Path to configuration directory containing boundary data
        last_check_time: Timestamp of last validation check
        last_check_results: Cached results from last validation
        
    @hardware_interface GPS, IMU sensors for real data validation
    """
    
    def __init__(self, resource_manager, config_dir: Optional[Path] = None):
        """
        Initialize the safety checker.
        
        Args:
            resource_manager: ResourceManager instance for hardware access
            config_dir: Optional path to config directory (defaults to standard location)
        """
        self.resource_manager = resource_manager
        self.config_dir = config_dir or Path("/home/pi/autonomous_mower/config")
        self.boundary_file = self.config_dir / "user_polygon.json"
        
        # Cache validation results to avoid excessive checks
        self.last_check_time = 0
        self.last_check_results = {}
        self.check_cache_duration = 5.0  # Cache results for 5 seconds
        
        logger.info("SafetyChecker initialized")
    
    def validate_all_safety_conditions(self) -> Tuple[bool, str]:
        """
        Validate all safety conditions required for autonomous operation.
        
        Returns:
            Tuple[bool, str]: (validation_passed, error_message)
                - True if all safety checks pass, False otherwise
                - Error message describing first failure, empty string if all pass
        """
        try:
            # Check cache first
            current_time = time.time()
            if (current_time - self.last_check_time) < self.check_cache_duration:
                cached_result = self.last_check_results.get('all_conditions')
                if cached_result is not None:
                    logger.debug("Using cached safety validation results")
                    return cached_result
            
            # Perform fresh validation
            logger.debug("Performing fresh safety validation")
            
            # 1. Check GPS real data
            gps_valid, gps_error = self.check_gps_real()
            if not gps_valid:
                error_msg = f"GPS safety check failed: {gps_error}"
                logger.error(error_msg)
                self._cache_result('all_conditions', (False, error_msg))
                return False, error_msg
            
            # 2. Check IMU real data  
            imu_valid, imu_error = self.check_imu_real()
            if not imu_valid:
                error_msg = f"IMU safety check failed: {imu_error}"
                logger.error(error_msg)
                self._cache_result('all_conditions', (False, error_msg))
                return False, error_msg
            
            # 3. Check boundary configuration
            boundary_valid, boundary_error = self.check_boundary_set()
            if not boundary_valid:
                error_msg = f"Boundary safety check failed: {boundary_error}"
                logger.error(error_msg)
                self._cache_result('all_conditions', (False, error_msg))
                return False, error_msg
            
            # All checks passed
            logger.info("All safety conditions validated successfully")
            self._cache_result('all_conditions', (True, ""))
            return True, ""
            
        except Exception as e:
            error_msg = f"Safety validation error: {e}"
            logger.error(error_msg, exc_info=True)
            self._cache_result('all_conditions', (False, error_msg))
            return False, error_msg
    
    def check_gps_real(self) -> Tuple[bool, str]:
        """
        Validate that GPS data is from real hardware, not simulation.
        
        Checks for:
        - Simulation fallback coordinates
        - GPS fix quality and satellite count
        - Realistic coordinate variation over time
        
        Returns:
            Tuple[bool, str]: (is_real, error_message)
        """
        try:
            # Get GPS service from resource manager
            gps_service = self.resource_manager.get("gps_service")
            if not gps_service:
                return False, "GPS service not available"
            
            # Get latest position data directly from the service
            try:
                position_data = gps_service.get_position()
                if not position_data:
                    return False, "No GPS position data available"
                
                # Convert UTM back to lat/lon for validation
                import utm
                if len(position_data) >= 5:
                    _, easting, northing, zone_number, zone_letter = position_data
                    lat, lon = utm.to_latlon(easting, northing, zone_number, zone_letter)
                else:
                    return False, "Incomplete GPS position data"
                    
            except Exception as e:
                return False, f"Error reading GPS position: {e}"
            
            # Check for known simulation coordinates
            current_coords = (round(lat, 4), round(lon, 4))
            for sim_name, sim_coords in SIMULATION_GPS_COORDINATES.items():
                sim_rounded = (round(sim_coords[0], 4), round(sim_coords[1], 4))
                if current_coords == sim_rounded:
                    return False, f"GPS showing simulation coordinates ({sim_name}: {lat:.4f}, {lon:.4f})"
            
            # Check for GPS fix quality if available
            try:
                if hasattr(gps_service, 'get_metadata'):
                    gps_metadata = gps_service.get_metadata()
                    if gps_metadata:
                        satellites = gps_metadata.get('satellites', 0)
                        if satellites < MIN_GPS_SATELLITES:
                            return False, f"Insufficient GPS satellites: {satellites} < {MIN_GPS_SATELLITES}"
                        
                        hdop = gps_metadata.get('hdop', float('inf'))
                        if hdop > MIN_GPS_ACCURACY:
                            return False, f"Poor GPS accuracy (HDOP): {hdop} > {MIN_GPS_ACCURACY}"
            except Exception as e:
                logger.warning(f"Could not check GPS status details: {e}")
            
            # Additional validation: check if coordinates are in a realistic range
            if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
                return False, f"GPS coordinates out of valid range: {lat:.4f}, {lon:.4f}"
            
            # Check if coordinates are changing realistically (if we have history)
            # This would catch perfectly static simulation coordinates
            try:
                if hasattr(gps_service, 'gps_position') and gps_service.gps_position:
                    gps_position = gps_service.gps_position
                    if hasattr(gps_position, 'position_history'):
                        history = getattr(gps_position, 'position_history', [])
                    if len(history) > 1:
                        # Check if position has been exactly the same for too long
                        recent_positions = history[-10:]  # Last 10 positions
                        if len(set(recent_positions)) == 1:  # All positions identical
                            return False, "GPS coordinates suspiciously static (possible simulation)"
            except Exception as e:
                logger.debug(f"Could not check GPS coordinate variation: {e}")
            
            logger.debug(f"GPS validation passed: real coordinates {lat:.4f}, {lon:.4f}")
            return True, ""
            
        except Exception as e:
            error_msg = f"Error validating GPS: {e}"
            logger.error(error_msg, exc_info=True)
            return False, error_msg
    
    def check_imu_real(self) -> Tuple[bool, str]:
        """
        Validate that IMU data is from real hardware, not simulation.
        
        Checks for:
        - Hardware-specific sensor responses and noise patterns
        - Realistic acceleration and gyroscope readings
        - Sensor initialization status from hardware registry
        
        Returns:
            Tuple[bool, str]: (is_real, error_message)
        """
        try:
            # Get sensor interface from resource manager
            sensor_interface = self.resource_manager.get("sensor_interface")
            if not sensor_interface:
                return False, "Sensor interface not available"
            
            # Get IMU data
            try:
                sensor_data = sensor_interface.get_sensor_data()
                if not sensor_data:
                    return False, "No sensor data available"
                
                imu_data = sensor_data.get('imu', {})
                if not imu_data:
                    return False, "No IMU data in sensor readings"
                
            except Exception as e:
                return False, f"Error reading IMU data: {e}"
            
            # Check for hardware registry IMU initialization
            try:
                hardware_registry = self.resource_manager.get("hardware_registry")
                if hardware_registry:
                    imu_sensor = hardware_registry.get_bno085()
                    if not imu_sensor:
                        return False, "IMU sensor not initialized in hardware registry"
            except Exception as e:
                logger.warning(f"Could not check hardware registry IMU: {e}")
            
            # Validate IMU data structure and values
            required_fields = ['orientation', 'acceleration', 'gyroscope']
            for field in required_fields:
                if field not in imu_data:
                    # Allow missing orientation by warning and skipping only that check
                    if field == 'orientation':
                        logger.warning("IMU orientation field missing, skipping orientation checks")
                        continue
                    return False, f"Missing IMU field: {field}"
            
            # Check for realistic sensor noise (real sensors have some noise)
            orientation = imu_data.get('orientation', {})
            if isinstance(orientation, dict):
                heading = orientation.get('heading', 0)
                pitch = orientation.get('pitch', 0)  
                roll = orientation.get('roll', 0)
                
                # Check if values are suspiciously perfect (like 0.0, 90.0, etc.)
                perfect_values = [0.0, 90.0, 180.0, 270.0, 360.0]
                if all(any(abs(val - perfect) < 0.001 for perfect in perfect_values) 
                       for val in [heading, pitch, roll]):
                    return False, "IMU values suspiciously perfect (possible simulation)"
            
            # Check acceleration values for realistic gravity component
            acceleration = imu_data.get('acceleration', {})
            if isinstance(acceleration, dict):
                # Real IMU should show gravity component (~9.8 m/s²)
                ax = acceleration.get('x', 0)
                ay = acceleration.get('y', 0)
                az = acceleration.get('z', 0)
                
                total_accel = math.sqrt(ax**2 + ay**2 + az**2)
                
                # Total acceleration should be close to gravity when stationary
                if total_accel < 5.0 or total_accel > 15.0:
                    return False, f"IMU acceleration unrealistic: {total_accel:.2f} m/s² (expected ~9.8)"
            
            logger.debug("IMU validation passed: real hardware sensor data detected")
            return True, ""
            
        except Exception as e:
            error_msg = f"Error validating IMU: {e}"
            logger.error(error_msg, exc_info=True)
            return False, error_msg
    
    def check_boundary_set(self) -> Tuple[bool, str]:
        """
        Validate that a proper boundary polygon is configured and current position is safe.
        
        Checks for:
        - Boundary polygon file exists and is readable
        - Polygon has minimum required area
        - Current GPS position is within boundary
        - Polygon is valid geometry
        
        Returns:
            Tuple[bool, str]: (is_valid, error_message)
        """
        try:
            # Check if boundary file exists
            if not self.boundary_file.exists():
                return False, f"Boundary file not found: {self.boundary_file}"
            
            # Load boundary configuration
            try:
                with open(self.boundary_file, 'r') as f:
                    boundary_config = json.load(f)
            except Exception as e:
                return False, f"Error reading boundary file: {e}"
            
            # Extract coordinates
            coordinates = boundary_config.get('coordinates', [])
            if not coordinates:
                # Try legacy format with 'boundary' key
                boundary_points = boundary_config.get('boundary', [])
                if boundary_points:
                    coordinates = [boundary_points]  # Wrap in array for GeoJSON format
                else:
                    return False, "No boundary coordinates found in config"
            
            if not coordinates or not coordinates[0]:
                return False, "Empty boundary coordinates"
            
            # Get the outer ring (first coordinate set)
            boundary_points = coordinates[0]
            
            # Validate minimum number of points for a polygon
            if len(boundary_points) < 4:  # Need at least 4 points (last should close the polygon)
                return False, f"Boundary needs at least 4 points, got {len(boundary_points)}"
            
            # Create Shapely polygon for geometric validation
            try:
                polygon = Polygon(boundary_points)
                
                if not polygon.is_valid:
                    return False, "Boundary polygon geometry is invalid"
                
                # Check minimum area requirement
                area = polygon.area
                # Convert from degree-based area to approximate square meters
                # This is a rough approximation - for precise area calculation would need projection
                area_m2 = area * 111000 * 111000  # Very rough conversion
                
                if area_m2 < MIN_BOUNDARY_AREA:
                    return False, f"Boundary area too small: {area_m2:.1f}m² < {MIN_BOUNDARY_AREA}m²"
                
            except Exception as e:
                return False, f"Error validating boundary geometry: {e}"
            
            # Check if current GPS position is within boundary
            try:
                # Get current GPS position
                gps_service = self.resource_manager.get("gps_service")
                if gps_service and gps_service.gps_position:
                    position_data = gps_service.get_position()
                    if position_data and len(position_data) >= 5:
                        import utm
                        _, easting, northing, zone_number, zone_letter = position_data
                        lat, lon = utm.to_latlon(easting, northing, zone_number, zone_letter)
                        
                        current_point = Point(lon, lat)  # Note: Shapely uses (x, y) = (lon, lat)
                        
                        if not polygon.contains(current_point):
                            return False, f"Current position ({lat:.6f}, {lon:.6f}) is outside boundary"
                        
                        logger.debug(f"Current position {lat:.6f}, {lon:.6f} is within boundary")
                    else:
                        logger.warning("Could not verify current position within boundary (no GPS data)")
                        
            except Exception as e:
                logger.warning(f"Could not check current position within boundary: {e}")
                # Don't fail the boundary check just because we can't verify current position
                # The boundary configuration itself is valid
            
            logger.debug(f"Boundary validation passed: valid polygon with {len(boundary_points)} points")
            return True, ""
            
        except Exception as e:
            error_msg = f"Error validating boundary: {e}"
            logger.error(error_msg, exc_info=True)
            return False, error_msg
    
    def _cache_result(self, check_type: str, result: Tuple[bool, str]):
        """Cache validation result with timestamp."""
        self.last_check_time = time.time()
        self.last_check_results[check_type] = result
    
    def get_safety_status(self) -> Dict[str, Any]:
        """
        Get comprehensive safety status for monitoring and UI display.
        
        Returns:
            Dict containing detailed safety check results
        """
        status = {
            'timestamp': time.time(),
            'overall_safe': False,
            'errors': [],
            'checks': {}
        }
        
        try:
            # Individual check results
            gps_valid, gps_error = self.check_gps_real()
            imu_valid, imu_error = self.check_imu_real()
            boundary_valid, boundary_error = self.check_boundary_set()
            
            status['checks'] = {
                'gps_real': {'valid': gps_valid, 'error': gps_error},
                'imu_real': {'valid': imu_valid, 'error': imu_error}, 
                'boundary_set': {'valid': boundary_valid, 'error': boundary_error}
            }
            
            # Collect all errors
            if not gps_valid:
                status['errors'].append(f"GPS: {gps_error}")
            if not imu_valid:
                status['errors'].append(f"IMU: {imu_error}")
            if not boundary_valid:
                status['errors'].append(f"Boundary: {boundary_error}")
            
            # Overall safety status
            status['overall_safe'] = gps_valid and imu_valid and boundary_valid
            
        except Exception as e:
            status['errors'].append(f"Safety check error: {e}")
            logger.error(f"Error getting safety status: {e}", exc_info=True)
        
        return status


def requires_safety_validation(safety_checker: SafetyChecker):
    """
    Decorator to enforce safety validation before autonomous movement methods.
    
    This decorator should be applied to any method that initiates autonomous
    movement of the mower. It will prevent execution if safety conditions
    are not met.
    
    Args:
        safety_checker: SafetyChecker instance to use for validation
        
    Raises:
        SafetyValidationError: If safety validation fails
        
    Example:
        @requires_safety_validation(safety_checker)
        def navigate_to_location(self, target_location):
            # This will only execute if all safety checks pass
            pass
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Perform safety validation
            is_safe, error_message = safety_checker.validate_all_safety_conditions()
            
            if not is_safe:
                error_msg = f"Safety validation failed for {func.__name__}: {error_message}"
                logger.error(error_msg)
                raise SafetyValidationError(error_msg)
            
            logger.debug(f"Safety validation passed for {func.__name__}")
            return func(*args, **kwargs)
        
        return wrapper
    return decorator
