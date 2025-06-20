# FROZEN_DRIVER – do not edit (see .github/copilot-instructions.md)
# Simple, static-method-only INA3221 interface for compatibility and reliability
import board
import busio
from adafruit_ina3221 import INA3221

class INA3221Sensor:
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
        ch = channel - 1
        try:
            bus_voltage = sensor[ch].bus_voltage
            shunt_voltage = sensor[ch].shunt_voltage
            current = sensor[ch].current
            return {
                "bus_voltage": round(bus_voltage, 2),
                "shunt_voltage": round(shunt_voltage, 2),
                "current": round(current, 2),
            }
        except Exception:
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
