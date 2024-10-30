import time
import os
from mower.hardware.serial_port import SerialPort
from adafruit_bno08x.uart import BNO08X_UART
from src.mower.hardware.imu import BNO085Sensor
from dotenv import load_dotenv

load_dotenv()

IMU_SERIAL_PORT = os.getenv('IMU_SERIAL_PORT', '/dev/ttyAMA2')
IMU_BAUDRATE = int(os.getenv('IMU_BAUD_RATE', '3000000'))

imu_serial_port = SerialPort(port=IMU_SERIAL_PORT, baudrate=IMU_BAUDRATE)

try:
    # Start the serial port
    imu_serial_port.start()
    print(f"IMU_SERIAL_PORT: {IMU_SERIAL_PORT}")
    print("Serial port initialized.")
    print("Initializing BNO085 sensor...")

    # Initialize BNO085 sensor
    sensor = BNO08X_UART(imu_serial_port.ser)
    BNO085Sensor.enable_features(sensor)
    print("BNO085 sensor initialized and features enabled.")

    # Get readings every second for 30 seconds
    for _ in range(30):
        accel_data = BNO085Sensor.read_bno085_accel(sensor)
        gyro_data = BNO085Sensor.read_bno085_gyro(sensor)
        mag_data = BNO085Sensor.read_bno085_magnetometer(sensor)
        quaternion = BNO085Sensor.calculate_quaternion(sensor)
        heading = BNO085Sensor.calculate_heading(sensor)
        pitch = BNO085Sensor.calculate_pitch(sensor)
        roll = BNO085Sensor.calculate_roll(sensor)
        speed = BNO085Sensor.calculate_speed(sensor)

        # Print sensor data
        print(f"Accelerometer: {accel_data}")
        print(f"Gyroscope: {gyro_data}")
        print(f"Magnetometer: {mag_data}")
        print(f"Quaternion: {quaternion}")
        print(f"Heading: {heading}")
        print(f"Pitch: {pitch}")
        print(f"Roll: {roll}")
        print(f"Speed: {speed}")

        # Wait for 1 second before the next reading
        time.sleep(1)

except Exception as e:
    print(f"An error occurred: {e}")

finally:
    # Cleanup sensor and stop the serial port
    BNO085Sensor.cleanup(sensor)
    imu_serial_port.stop()
    print("IMU SerialPort stopped.")
