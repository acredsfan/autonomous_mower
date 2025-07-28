"""
Sensor Service

This service handles all sensor data collection, fusion, and publishing.
It provides real-time sensor data to other services and the safety system.
"""

import asyncio
import json
import logging
import time
import math
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from enum import Enum

from mower.core.communication.base_service import BaseService, ServiceMessage
from mower.core.hal.hardware_manager import get_hardware_manager, HardwareManager
from mower.core.safety.safety_system import get_safety_system, SafetySystem
from mower.config.settings import SystemConfig


logger = logging.getLogger(__name__)


@dataclass
class GPSData:
    """GPS sensor data."""
    latitude: float = 0.0
    longitude: float = 0.0
    altitude: float = 0.0
    fix_quality: int = 0
    satellites: int = 0
    hdop: float = 99.9
    timestamp: float = 0.0


@dataclass
class IMUData:
    """IMU sensor data."""
    acceleration_x: float = 0.0
    acceleration_y: float = 0.0
    acceleration_z: float = 0.0
    gyroscope_x: float = 0.0
    gyroscope_y: float = 0.0
    gyroscope_z: float = 0.0
    magnetometer_x: float = 0.0
    magnetometer_y: float = 0.0
    magnetometer_z: float = 0.0
    temperature: float = 0.0
    timestamp: float = 0.0


@dataclass
class ToFData:
    """Time of Flight sensor data."""
    distance_mm: int = 0
    status: str = "unknown"
    timestamp: float = 0.0


@dataclass
class BatteryData:
    """Battery monitoring data."""
    voltage: float = 0.0
    current: float = 0.0
    power: float = 0.0
    percentage: float = 0.0
    temperature: float = 0.0
    timestamp: float = 0.0


@dataclass
class SensorFusion:
    """Fused sensor data."""
    position_lat: float = 0.0
    position_lon: float = 0.0
    heading_degrees: float = 0.0
    tilt_degrees: float = 0.0
    speed_mps: float = 0.0
    obstacle_distance_mm: int = 9999
    battery_level: float = 0.0
    system_safe: bool = False
    timestamp: float = 0.0


class SensorService(BaseService):
    """Sensor data collection and fusion service."""
    
    def __init__(self, service_name: str = "sensor", config: Optional[SystemConfig] = None):
        """Initialize sensor service."""
        super().__init__(service_name, config)
        
        # Hardware and safety systems
        self.hardware_manager: Optional[HardwareManager] = None
        self.safety_system: Optional[SafetySystem] = None
        
        # Sensor data storage
        if (config and config.simulation_mode) or (self.config and self.config.simulation_mode):
            # Initialize with simulation values
            self.gps_data = GPSData(
                latitude=40.7128,
                longitude=-74.0060,
                altitude=10.0,
                fix_quality=1,
                satellites=8,
                hdop=1.2,
                timestamp=time.time()
            )
            logger.info("Initialized GPS with simulation coordinates: 40.7128, -74.0060")
        else:
            self.gps_data = GPSData()
            logger.info("Initialized GPS with default (zero) coordinates")
        self.imu_data = IMUData()
        self.tof_data = ToFData()
        self.battery_data = BatteryData()
        self.fusion_data = SensorFusion()
        
        # Data history for filtering
        self.gps_history: List[GPSData] = []
        self.imu_history: List[IMUData] = []
        self.max_history = 10
        
        # Performance tracking
        self.sensor_read_count = 0
        self.fusion_count = 0
        self.last_publish_time = 0.0
        
        # Sensor reading intervals
        self.gps_interval = 1.0  # 1Hz
        self.imu_interval = 0.1  # 10Hz
        self.tof_interval = 0.2  # 5Hz
        self.battery_interval = 5.0  # 0.2Hz
        self.fusion_interval = 0.1  # 10Hz
        self.publish_interval = 0.5  # 2Hz
        
        # Last read timestamps
        self.last_gps_read = 0.0
        self.last_imu_read = 0.0
        self.last_tof_read = 0.0
        self.last_battery_read = 0.0
        self.last_fusion = 0.0
    
    async def service_initialize(self) -> bool:
        """Initialize sensor service components."""
        try:
            # Initialize hardware manager
            self.hardware_manager = get_hardware_manager(self.config, self.config.simulation_mode)
            if not self.hardware_manager.initialize_all():
                logger.error("Failed to initialize hardware manager")
                return False
            
            # Initialize safety system connection
            self.safety_system = get_safety_system(self.config)
            
            logger.info("Sensor service initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Sensor service initialization failed: {e}")
            return False
    
    async def service_loop(self) -> None:
        """Main sensor service loop."""
        try:
            while not self.shutdown_event.is_set():
                current_time = time.time()
                
                # Read sensors based on their intervals
                if current_time - self.last_gps_read >= self.gps_interval:
                    await self._read_gps()
                    self.last_gps_read = current_time
                
                if current_time - self.last_imu_read >= self.imu_interval:
                    await self._read_imu()
                    self.last_imu_read = current_time
                
                if current_time - self.last_tof_read >= self.tof_interval:
                    await self._read_tof()
                    self.last_tof_read = current_time
                
                if current_time - self.last_battery_read >= self.battery_interval:
                    await self._read_battery()
                    self.last_battery_read = current_time
                
                # Perform sensor fusion
                if current_time - self.last_fusion >= self.fusion_interval:
                    await self._perform_fusion()
                    self.last_fusion = current_time
                
                # Publish data
                if current_time - self.last_publish_time >= self.publish_interval:
                    await self._publish_sensor_data()
                    self.last_publish_time = current_time
                
                # Update safety system
                if self.safety_system:
                    self.safety_system.monitor.update_sensor_time()
                
                await asyncio.sleep(0.05)  # 20Hz main loop
                
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Sensor service loop error: {e}")
    
    async def service_cleanup(self) -> None:
        """Cleanup sensor service."""
        try:
            # Cleanup hardware
            if self.hardware_manager:
                self.hardware_manager.cleanup_all()
            
            logger.info("Sensor service cleanup complete")
            
        except Exception as e:
            logger.error(f"Sensor service cleanup error: {e}")
    
    async def _read_gps(self) -> None:
        """Read GPS sensor data."""
        try:
            if self.config.simulation_mode:
                # Simulate GPS data with some movement
                base_lat = 40.7128
                base_lon = -74.0060
                offset = math.sin(time.time() * 0.1) * 0.0001
                
                self.gps_data = GPSData(
                    latitude=base_lat + offset,
                    longitude=base_lon + offset * 0.5,
                    altitude=10.0 + offset * 100,
                    fix_quality=1,
                    satellites=8,
                    hdop=1.2,
                    timestamp=time.time()
                )
                logger.debug(f"GPS simulation: {self.gps_data.latitude:.6f}, {self.gps_data.longitude:.6f}")
            else:
                # Read from real GPS hardware
                try:
                    # Try to read from hardware GPS
                    if hasattr(self, '_gps_serial') and self._gps_serial:
                        if self._gps_serial.in_waiting > 0:
                            line = self._gps_serial.readline().decode('ascii', errors='ignore').strip()
                            if line.startswith('$GPGGA') or line.startswith('$GNGGA'):
                                # Parse NMEA sentence
                                parts = line.split(',')
                                if len(parts) > 6 and parts[2] and parts[4]:
                                    lat = float(parts[2][:2]) + float(parts[2][2:]) / 60.0
                                    if parts[3] == 'S':
                                        lat = -lat
                                    lon = float(parts[4][:3]) + float(parts[4][3:]) / 60.0
                                    if parts[5] == 'W':
                                        lon = -lon
                                    
                                    self.gps_data.latitude = lat
                                    self.gps_data.longitude = lon
                                    self.gps_data.fix_quality = int(parts[6]) if parts[6] else 0
                                    self.gps_data.satellites = int(parts[7]) if parts[7] else 0
                                    self.gps_data.hdop = float(parts[8]) if parts[8] else 99.9
                                    self.gps_data.timestamp = time.time()
                    else:
                        # Initialize GPS serial connection
                        try:
                            import serial
                            self._gps_serial = serial.Serial('/dev/ttyAMA0', 9600, timeout=0.1)
                        except Exception as e:
                            logger.error(f"GPS serial init error: {e}")
                            self._gps_serial = None
                
                except Exception as e:
                    logger.debug(f"GPS hardware read error: {e}")
                
                # Fallback to default coordinates if no GPS fix
                if self.gps_data.fix_quality == 0:
                    # Use last known coordinates or default to current location  
                    if self.gps_data.latitude == 0.0:
                        self.gps_data.latitude = 40.7128  # Default to NYC
                        self.gps_data.longitude = -74.0060
                self.gps_data.timestamp = time.time()
            
            # Add to history for filtering
            self.gps_history.append(self.gps_data)
            if len(self.gps_history) > self.max_history:
                self.gps_history.pop(0)
            
            self.sensor_read_count += 1
            
        except Exception as e:
            logger.error(f"GPS read error: {e}")
    
    async def _read_imu(self) -> None:
        """Read IMU sensor data."""
        try:
            if self.config.simulation_mode:
                # Simulate IMU data with realistic values
                self.imu_data = IMUData(
                    acceleration_x=0.1 + math.sin(time.time()) * 0.05,
                    acceleration_y=0.2 + math.cos(time.time()) * 0.05,
                    acceleration_z=9.8 + math.sin(time.time() * 0.5) * 0.1,
                    gyroscope_x=math.sin(time.time() * 0.2) * 0.1,
                    gyroscope_y=math.cos(time.time() * 0.3) * 0.1,
                    gyroscope_z=math.sin(time.time() * 0.1) * 0.05,
                    magnetometer_x=0.3 + math.sin(time.time() * 0.1) * 0.1,
                    magnetometer_y=0.4 + math.cos(time.time() * 0.1) * 0.1,
                    magnetometer_z=-0.5 + math.sin(time.time() * 0.05) * 0.1,
                    temperature=25.0 + math.sin(time.time() * 0.01) * 2.0,
                    timestamp=time.time()
                )
            else:
                # Read from real IMU hardware
                # This would integrate with the actual IMU module
                self.imu_data.timestamp = time.time()
            
            # Add to history for filtering
            self.imu_history.append(self.imu_data)
            if len(self.imu_history) > self.max_history:
                self.imu_history.pop(0)
            
            self.sensor_read_count += 1
            
        except Exception as e:
            logger.error(f"IMU read error: {e}")
    
    async def _read_tof(self) -> None:
        """Read dual Time of Flight sensor data."""
        try:
            if self.config.simulation_mode:
                # Simulate ToF data with varying distance
                base_distance = 1500
                variation = math.sin(time.time() * 0.3) * 300
                
                self.tof_data = ToFData(
                    distance_mm=int(base_distance + variation),
                    status="valid",
                    timestamp=time.time()
                )
            else:
                # Read from real dual ToF hardware
                try:
                    if not hasattr(self, '_tof_sensors'):
                        # Initialize ToF sensors
                        import board
                        import busio
                        import digitalio
                        import adafruit_vl53l0x
                        
                        # Setup GPIO for dual sensors
                        left_xshut = digitalio.DigitalInOut(getattr(board, 'D22'))
                        right_xshut = digitalio.DigitalInOut(getattr(board, 'D23'))
                        left_xshut.direction = digitalio.Direction.OUTPUT
                        right_xshut.direction = digitalio.Direction.OUTPUT
                        
                        # Reset and configure
                        left_xshut.value = False
                        right_xshut.value = False
                        time.sleep(0.01)
                        
                        # Initialize I2C and left sensor
                        i2c = busio.I2C(board.SCL, board.SDA)
                        left_xshut.value = True
                        time.sleep(0.01)
                        
                        left_tof = adafruit_vl53l0x.VL53L0X(i2c, address=0x29)
                        
                        # Enable right sensor  
                        right_xshut.value = True
                        time.sleep(0.01)
                        right_tof = adafruit_vl53l0x.VL53L0X(i2c, address=0x30)
                        
                        self._tof_sensors = {
                            'left': left_tof,
                            'right': right_tof
                        }
                        logger.info("Dual ToF sensors initialized successfully")
                    
                    # Read from both sensors
                    left_distance = self._tof_sensors['left'].range
                    right_distance = self._tof_sensors['right'].range
                    
                    # Use the minimum distance for safety
                    min_distance = min(left_distance, right_distance)
                    
                    self.tof_data = ToFData(
                        distance_mm=min_distance,
                        status="valid" if min_distance > 0 else "error",
                        timestamp=time.time()
                    )
                    
                    logger.debug(f"ToF readings: Left={left_distance}mm, Right={right_distance}mm, Min={min_distance}mm")
                    
                except Exception as e:
                    logger.error(f"ToF hardware read error: {e}")
                    # Keep existing value or set safe default
                    self.tof_data.timestamp = time.time()
            
            self.sensor_read_count += 1
            
        except Exception as e:
            logger.error(f"ToF read error: {e}")
    
    async def _read_battery(self) -> None:
        """Read battery monitoring data."""
        try:
            if self.config.simulation_mode:
                # Simulate battery data with slow discharge
                base_voltage = 12.6
                discharge_rate = time.time() * 0.0001
                
                self.battery_data = BatteryData(
                    voltage=base_voltage - discharge_rate,
                    current=2.5 + math.sin(time.time() * 0.1) * 0.5,
                    power=0.0,  # Will be calculated
                    percentage=max(0, 100 - discharge_rate * 1000),
                    temperature=25.0 + math.sin(time.time() * 0.01) * 3.0,
                    timestamp=time.time()
                )
                self.battery_data.power = self.battery_data.voltage * self.battery_data.current
            else:
                # Read from real battery monitoring hardware
                # This would integrate with the actual battery monitor
                self.battery_data.timestamp = time.time()
            
            self.sensor_read_count += 1
            
        except Exception as e:
            logger.error(f"Battery read error: {e}")
    
    async def _perform_fusion(self) -> None:
        """Perform sensor fusion to create unified state estimate."""
        try:
            current_time = time.time()
            
            # Basic sensor fusion - in production this would be more sophisticated
            
            # Position from GPS (with basic filtering)
            if self.gps_history:
                # Simple moving average for GPS
                recent_gps = self.gps_history[-3:] if len(self.gps_history) >= 3 else self.gps_history
                avg_lat = sum(g.latitude for g in recent_gps) / len(recent_gps)
                avg_lon = sum(g.longitude for g in recent_gps) / len(recent_gps)
                
                self.fusion_data.position_lat = avg_lat
                self.fusion_data.position_lon = avg_lon
            
            # Heading from magnetometer (simplified)
            if self.imu_data.timestamp > 0:
                heading_rad = math.atan2(self.imu_data.magnetometer_y, self.imu_data.magnetometer_x)
                self.fusion_data.heading_degrees = math.degrees(heading_rad) % 360
                
                # Tilt from accelerometer
                tilt_rad = math.atan2(
                    math.sqrt(self.imu_data.acceleration_x**2 + self.imu_data.acceleration_y**2),
                    self.imu_data.acceleration_z
                )
                self.fusion_data.tilt_degrees = math.degrees(tilt_rad)
            
            # Speed calculation (simplified - would use GPS velocity in production)
            if len(self.gps_history) >= 2:
                prev_gps = self.gps_history[-2]
                curr_gps = self.gps_history[-1]
                time_diff = curr_gps.timestamp - prev_gps.timestamp
                
                if time_diff > 0:
                    # Simplified distance calculation
                    lat_diff = curr_gps.latitude - prev_gps.latitude
                    lon_diff = curr_gps.longitude - prev_gps.longitude
                    distance = math.sqrt(lat_diff**2 + lon_diff**2) * 111000  # Rough conversion to meters
                    self.fusion_data.speed_mps = distance / time_diff
            
            # Obstacle detection from ToF
            self.fusion_data.obstacle_distance_mm = self.tof_data.distance_mm
            
            # Battery level
            self.fusion_data.battery_level = self.battery_data.percentage
            
            # System safety assessment
            safe_conditions = [
                self.fusion_data.tilt_degrees < self.config.safety.max_tilt_angle,
                self.battery_data.voltage > self.config.safety.low_battery_threshold,
                self.tof_data.distance_mm > 300,  # At least 30cm clearance
                current_time - self.gps_data.timestamp < 10.0,  # Recent GPS fix
                current_time - self.imu_data.timestamp < 2.0,   # Recent IMU data
            ]
            
            self.fusion_data.system_safe = all(safe_conditions)
            self.fusion_data.timestamp = current_time
            
            self.fusion_count += 1
            
        except Exception as e:
            logger.error(f"Sensor fusion error: {e}")
    
    async def _publish_sensor_data(self) -> None:
        """Publish sensor data to Redis for other services."""
        try:
            # Publish individual sensor data
            sensor_data = {
                "gps": asdict(self.gps_data),
                "imu": asdict(self.imu_data),
                "tof": asdict(self.tof_data),
                "battery": asdict(self.battery_data),
                "fusion": asdict(self.fusion_data)
            }
            
            if self.redis_client:
                # Publish to sensor data stream
                await self.redis_client.xadd(
                    "sensor:data",
                    {"data": json.dumps(sensor_data)}
                )
                
                # Also store latest data with TTL
                await self.redis_client.setex(
                    f"service:{self.service_name}:data",
                    10,  # 10 second TTL
                    json.dumps(sensor_data)
                )
                
                # Publish status
                status = {
                    "sensor_reads": self.sensor_read_count,
                    "fusion_cycles": self.fusion_count,
                    "gps_fix_quality": self.gps_data.fix_quality,
                    "gps_satellites": self.gps_data.satellites,
                    "system_safe": self.fusion_data.system_safe,
                    "battery_voltage": self.battery_data.voltage,
                    "obstacle_distance": self.tof_data.distance_mm
                }
                
                await self.redis_client.setex(
                    f"service:{self.service_name}:status",
                    5,  # 5 second TTL
                    json.dumps(status)
                )
        
        except Exception as e:
            logger.error(f"Error publishing sensor data: {e}")


# Service entry point
def main():
    """Main entry point for sensor service."""
    from mower.core.communication.base_service import run_service
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger.info("Starting Sensor Service")
    run_service(SensorService, "sensor")


if __name__ == "__main__":
    main()
