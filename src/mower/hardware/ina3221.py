# FROZEN_DRIVER – do not edit (see .github/copilot-instructions.md)
# Simple, static-method-only INA3221 interface with exponential backoff for reliability
import time
import board
import busio
from adafruit_ina3221 import INA3221

class INA3221Sensor:
    # Class-level cache for reduced bus chatter
    _last_valid_samples = {}
    _last_read_times = {}
    _cache_duration = 2.0  # seconds
    
    @staticmethod
    def init_ina3221():
        try:
            i2c = busio.I2C(board.SCL, board.SDA)
            sensor = INA3221(i2c, enable=[0, 1, 2])
            return sensor
        except Exception:
            return None

    @staticmethod
    def read_ina3221(sensor, channel: int):
        # User API is 1-based, hardware is 0-based
        if sensor is None:
            return {}
        if not isinstance(channel, int) or channel not in [1, 2, 3]:
            return {}
            
        # Check cache first to reduce I2C bus load
        cache_key = f"channel_{channel}"
        current_time = time.monotonic()
        
        if (cache_key in INA3221Sensor._last_valid_samples and
            cache_key in INA3221Sensor._last_read_times and
            current_time - INA3221Sensor._last_read_times[cache_key] < INA3221Sensor._cache_duration):
            # Return cached value
            return INA3221Sensor._last_valid_samples[cache_key]
            
        ch = channel - 1
        max_attempts = 3
        
        for attempt in range(max_attempts):
            try:
                bus_voltage = sensor[ch].bus_voltage
                shunt_voltage = sensor[ch].shunt_voltage
                current = sensor[ch].current
                
                result = {
                    "bus_voltage": round(bus_voltage, 2),
                    "shunt_voltage": round(shunt_voltage, 2),
                    "current": round(current, 2),
                }
                
                # Cache successful read
                INA3221Sensor._last_valid_samples[cache_key] = result
                INA3221Sensor._last_read_times[cache_key] = current_time
                
                return result
                
            except Exception as e:
                if attempt < max_attempts - 1:
                    # Exponential backoff: 0.05s, 0.1s, 0.2s
                    backoff_time = 0.05 * (2 ** attempt)
                    time.sleep(backoff_time)
                # On final attempt, fall through to return cached or empty dict
                    
        # Return cached value if available, otherwise empty dict
        if cache_key in INA3221Sensor._last_valid_samples:
            return INA3221Sensor._last_valid_samples[cache_key]
        return {}


if __name__ == "__main__":
    # Example usage
    sensor = INA3221Sensor.init_ina3221()
    # Initialize the INA3221 sensor
    print("Initializing INA3221 sensor...")
    sensor = INA3221Sensor.init_ina3221()
    # Read data from each channel
    print("Reading data from INA3221 sensor...")
    if sensor:
        ch1_data = INA3221Sensor.read_ina3221(sensor, 1)
        print(ch1_data)
        ch2_data = INA3221Sensor.read_ina3221(sensor, 2)
        print(ch2_data)
        ch3_data = INA3221Sensor.read_ina3221(sensor, 3)
        print(ch3_data)

    else:
        print("INA3221 sensor initialization failed.")
