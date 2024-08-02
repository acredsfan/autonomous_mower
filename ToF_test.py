import time
import board
import busio
import adafruit_vl53l0x

def initialize_sensor(i2c, address):
    sensor = adafruit_vl53l0x.VL53L0X(i2c)
    sensor.set_address(address)
    return sensor

def main():
    # Initialize I2C bus
    i2c = busio.I2C(board.SCL, board.SDA)

    # Initialize the first VL53L0X sensor with address 0x29 (default)
    try:
        print("Initializing first VL53L0X sensor at address 0x29...")
        sensor1 = initialize_sensor(i2c, 0x29)
        print("First VL53L0X sensor initialized successfully!")
    except Exception as e:
        print("Failed to initialize the first VL53L0X sensor:", e)
        return

    # Initialize the second VL53L0X sensor with address 0x30
    try:
        print("Initializing second VL53L0X sensor at address 0x30...")
        sensor2 = initialize_sensor(i2c, 0x30)
        print("Second VL53L0X sensor initialized successfully!")
    except Exception as e:
        print("Failed to initialize the second VL53L0X sensor:", e)
        return

    # Read and print distance data from both sensors
    try:
        while True:
            try:
                distance1 = sensor1.range
                print(f"Sensor 1 Distance: {distance1} mm")
            except Exception as e:
                print("Error reading from sensor 1:", e)
                
            try:
                distance2 = sensor2.range
                print(f"Sensor 2 Distance: {distance2} mm")
            except Exception as e:
                print("Error reading from sensor 2:", e)

            time.sleep(1)
    except KeyboardInterrupt:
        print("Exiting...")
    except Exception as e:
        print("Error reading VL53L0X data:", e)

if __name__ == "__main__":
    main()
