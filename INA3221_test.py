import time
import board
import busio
from barbudor_ina3221.full import INA3221, DeviceRangeError

def main():
    # Initialize I2C bus and sensor
    i2c = busio.I2C(board.SCL, board.SDA)
    ina = INA3221(i2c)

    # Check connection
    try:
        print("Checking INA3221 connection...")
        # This reads from the first channel to ensure the sensor is connected
        _ = ina.bus_voltage(1)
        print("INA3221 connected successfully!")
    except Exception as e:
        print("Failed to connect to INA3221:", e)
        return

    # Read and print voltage and current data from all channels
    try:
        while True:
            for channel in range(1, 4):
                try:
                    bus_voltage = ina.bus_voltage(channel)
                    shunt_voltage = ina.shunt_voltage(channel)
                    current = ina.current(channel)
                    print(f"Channel {channel}:")
                    print(f"  Bus Voltage: {bus_voltage:.2f} V")
                    print(f"  Shunt Voltage: {shunt_voltage:.2f} mV")
                    print(f"  Current: {current:.2f} mA")
                except DeviceRangeError as e:
                    # Current measurement out of range, e.g. due to an open circuit
                    print(f"Channel {channel}: Current out of range")
            time.sleep(1)
    except KeyboardInterrupt:
        print("Exiting...")
    except Exception as e:
        print("Error reading INA3221 data:", e)

if __name__ == "__main__":
    main()
