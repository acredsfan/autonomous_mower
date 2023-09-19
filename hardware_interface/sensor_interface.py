#IMPORTS
import smbus2 as smbus
import board
from adafruit_bme280 import basic as adafruit_bme280
import adafruit_vl53l0x
from mpu9250_jmdev.registers import *
from mpu9250_jmdev.mpu_9250 import MPU9250
from barbudor_ina3221.full import *
import RPi.GPIO as GPIO
import busio
import time
import logging
import numpy as np

import navigation_system.path_planning as pp

# Initialize logging
logging.basicConfig(filename='sensors.log', level=logging.DEBUG)

class SensorInterface:
    def __init__(self):
        # Import GRID_SIZE from path_planning.py
        self.GRID_SIZE = pp.GRID_SIZE
        self.MUX_ADDRESS = 0x70  # Replace with your multiplexer's I2C address if different
        self.bus = smbus.SMBus(1)
        self.i2c = busio.I2C(board.SCL, board.SDA)
        self.obstacle_data = np.zeros(self.GRID_SIZE)
        try:
            self.i2c = busio.I2C(board.SCL, board.SDA)
        except Exception as e:
            print(f"Error during I2C initialization: {e}")
        try:
            self.select_mux_channel(3)
            self.bme280 = adafruit_bme280.Adafruit_BME280_I2C(self.i2c, address=0x76)
        except Exception as e:
            print(f"Error during BME280 initialization: {e}")

        try:          
            self.mpu = MPU9250(
                address_ak=AK8963_ADDRESS, 
                address_mpu_master=MPU9050_ADDRESS_69, # In 0x69 Address
                address_mpu_slave=None, 
                bus=1,
                gfs=GFS_1000, 
                afs=AFS_8G, 
                mfs=AK8963_BIT_16, 
                mode=AK8963_MODE_C100HZ)
        except Exception as e:
            print(f"Error during MPU9250 initialization: {e}")
        try:
            self.select_mux_channel(2)
            self.ina3221 = INA3221(self.i2c)
            self.ina3221.enable_channel(1)
            self.ina3221.enable_channel(3)
        except Exception as e:
            print(f"Error during INA3221 initialization: {e}")
        try:
            # change this to match the location's pressure (hPa) at sea level
            self.bme280.sea_level_pressure = 1013.25
            self.previous_acceleration = [0, 0, 0]  # previous acceleration values for x, y, z
            self.previous_time = time.time()  # time when the previous acceleration was measured
            self.speed = [0, 0, 0]  # current speed for x, y, z
        except Exception as e:
            print(f"Error during initialization: {e}")

        # GPIO for Sensor 1 shutdown pin
        self.right_shutdown = 23
        # GPIO for Sensor 2 shutdown pin
        self.left_shutdown = 22

        GPIO.setwarnings(False)

        # Setup GPIO for shutdown pins on each VL53L0X
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.right_shutdown, GPIO.OUT)
        GPIO.setup(self.left_shutdown, GPIO.OUT)

        # Set all shutdown pins low to turn off each VL53L0X
        GPIO.output(self.right_shutdown, GPIO.LOW)
        GPIO.output(self.left_shutdown, GPIO.LOW)

        # Keep all low for 500 ms or so to make sure they reset
        time.sleep(0.50)

        # Create VL53L0X objects
        try:
            self.select_mux_channel(6)  # Assuming channel 6 for the right sensor
            self.vl53l0x_right = adafruit_vl53l0x.VL53L0X(self.i2c, address=0x29)
        except Exception as e:
            print(f"Error during VL53L0X right sensor initialization: {e}")

        try:
            self.select_mux_channel(7)  # Assuming channel 7 for the left sensor
            self.vl53l0x_left = adafruit_vl53l0x.VL53L0X(self.i2c, address=0x2A)
        except Exception as e:
            print(f"Error during VL53L0X left sensor initialization: {e}")

    # FUNCTIONS
    def select_mux_channel(self, channel):
        """Select the specified channel on the TCA9548A I2C multiplexer."""
        if 0 <= channel <= 7:
            try:
                self.bus.write_byte(self.MUX_ADDRESS, 1 << channel)
            except Exception as e:
                print(f"Error during multiplexer channel selection: {e}")
        else:
            raise ValueError("Multiplexer channel must be an integer between 0 and 7.")

    def init_hall_effect_sensors(self):
        try:
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(self.HALL_EFFECT_SENSOR_1, GPIO.IN)
            GPIO.setup(self.HALL_EFFECT_SENSOR_2, GPIO.IN)
        except Exception as e:
            print(f"Error during hall effect sensor initialization: {e}")

    def init_sensors(self):
        """Initialize all sensors."""
        try:
            # Initialize MPU9250
            self.mpu.configure()  # Apply the settings to the registers.
            print("MPU9250 initialized.")

            # Initialize hall effect sensors
            self.init_hall_effect_sensors()
        except Exception as e:
            print(f"Error during sensor initialization: {e}")

    def read_bme280(self):
        """Read BME280 sensor data."""
        try:
            self.i2c = busio.I2C(board.SCL, board.SDA)
            self.select_mux_channel(3)
            self.bme280 = adafruit_bme280.Adafruit_BME280_I2C(self.i2c, address=0x76)
            temperature_f = self.bme280.temperature * 9 / 5 + 32
            return {
                'temperature_c': round(self.bme280.temperature, 1),
                'temperature_f': round(temperature_f, 1),
                'humidity': round(self.bme280.humidity, 1),
                'pressure': round(self.bme280.pressure, 1)
            }
        except Exception as e:
            print(f"Error during BME280 read: {e}")

def read_vl53l0x_left(self):
    """Read VL53L0X ToF sensor data."""
    try:
        self.vl53l0x_left.start_continuous()
        distance = self.vl53l0x_left.range
        if distance > 0:
            return distance
        else:
            return -1  # Error
    except Exception as e:
        self.vl53l0x_left.stop_continuous()
        print(f"Error during VL53L0X left read: {e}")

def read_vl53l0x_right(self):
    """Read VL53L0X ToF sensor data."""
    try:
        self.vl53l0x_right.start_continuous()
        distance = self.vl53l0x_right.range
        if distance > 0:
            return distance
        else:
            return -1  # Error
    except Exception as e:
        self.vl53l0x_right.stop_continuous()
        print(f"Error during VL53L0X right read: {e}")

    def read_mpu9250_compass(self):
        """Read MPU9250 compass data."""
        try:
            self.mpu.configure()
            return self.mpu.readMagnetometerMaster()
        except Exception as e:
            print(f"Error during MPU9250 compass read: {e}")

    def read_mpu9250_gyro(self):
        """Read MPU9250 gyro data."""
        try:
            self.mpu.configure()
            return self.mpu.readGyroscopeMaster()
        except Exception as e:
            print(f"Error during MPU9250 gyro read: {e}")

    def read_mpu9250_accel(self):
        """Read MPU9250 accelerometer data."""
        try:
            self.mpu.configure()
            return self.mpu.readAccelerometerMaster()
        except Exception as e:
            print(f"Error during MPU9250 accelerometer read: {e}")

    def read_ina3221(self, channel):
        """Read INA3221 power monitor data."""
        try:
            self.select_mux_channel(2)
            if channel in [1, 3]:
                Voltage = round(self.ina3221.bus_voltage(channel), 2)
                Shunt_Voltage = round(self.ina3221.shunt_voltage(channel), 2)
                Current = round(self.ina3221.current(channel), 2)
                sensor_data = {"bus_voltage": Voltage, "current": Current, 'shunt_voltage': Shunt_Voltage}
                
                if channel == 3:  # if channel 3 is selected
                    # SLA battery charge level
                    Charge_Level = round((Voltage - 11.5) / (13.5 - 11.5) * 100, 1)  # rounded to 1 decimal place
                    sensor_data["charge_level"] = f"{Charge_Level}%"  # add Charge_Level to the return dictionary as a percentage
                    
                return sensor_data
            else:
                raise ValueError("Invalid INA3221 channel. Please use 1 or 3.")
        except Exception as e:
            print(f"Error during INA3221 read: {e}")

    def update_obstacle_data(self, tof_left, tof_right, compass_data):
        """
        Update the obstacle_data grid based on ToF and compass data.
        """
        # Process ToF data to get obstacle distances
        left_distance = self.read_vl53l0x_left()
        right_distance = self.read_vl53l0x_right()

        # Use compass data to get the direction
        direction = self.read_mpu9250_compass()

        # Convert compass direction to grid coordinates
        dx, dy = 0, 0
        if 0 <= direction < 90:
            dx, dy = 1, 1
        elif 90 <= direction < 180:
            dx, dy = -1, 1
        elif 180 <= direction < 270:
            dx, dy = -1, -1
        elif 270 <= direction < 360:
            dx, dy = 1, -1

        # Update the obstacle_data grid based on distances and direction
        # Assuming the mower is at the center of the grid
        center_x, center_y = GRID_SIZE[0] // 2, GRID_SIZE[1] // 2

        # Update for left sensor
        if left_distance < 15:  # Assuming 50 is the threshold distance in cm
            self.obstacle_data[center_x + dx][center_y + dy] = 1  # Mark as obstacle

        # Update for right sensor
        if right_distance < 15:
            self.obstacle_data[center_x - dx][center_y - dy] = 1  # Mark as obstacle

    def get_obstacle_data(self):
        return self.obstacle_data

    def calculate_speed(self):
        """Calculate speed based on accelerometer data."""
        try:
            current_acceleration = self.read_mpu9250_accel()
            current_time = time.time()
            time_difference = current_time - self.previous_time

            for i in range(3):
                # Calculate speed using the formula speed = initial speed + acceleration * time.
                # Convert from m/s^2 to mi/hr.
                self.speed[i] += (current_acceleration[i] + self.previous_acceleration[i]) / 2 * time_difference * 3600 / 1609.34

            self.previous_acceleration = current_acceleration
            self.previous_time = current_time

            return self.speed
        except Exception as e:
            print(f"Error during speed calculation: {e}")

    def ideal_mowing_conditions(self):
        attempts = 0
        while attempts < 20:
            try:
                bme280_data = self.read_bme280()
                if bme280_data is not None:
                    if bme280_data['humidity'] > 90:
                        return False
                    if bme280_data['temperature_f'] > 90:
                        return False
                    if bme280_data['temperature_f'] < 35:
                        return False
                    if bme280_data['pressure'] < 1000:
                        return False
                    return True
                else:
                    print("Sensor data is not available. Retrying...")
                    time.sleep(5)  # Wait for 5 seconds before retrying
                    attempts += 1

            except Exception as e:
                print(f"Error during checking mowing conditions: {e}")
                return False

        print("Sensor data is not available after 20 attempts. Returning False.")
        return False

# At the end of sensor_interface.py
sensor_interface = SensorInterface()