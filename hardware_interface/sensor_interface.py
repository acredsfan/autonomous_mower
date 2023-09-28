#IMPORTS
import smbus2 as smbus
import board
from adafruit_bme280 import basic as adafruit_bme280
import adafruit_vl53l0x
import adafruit_tca9548a
from mpu9250_jmdev.registers import *
from mpu9250_jmdev.mpu_9250 import MPU9250
import barbudor_ina3221.full as INA3221
import RPi.GPIO as GPIO
import busio
import time
import logging
import numpy as np
from constants import GRID_SIZE
import digitalio
import threading

# Initialize logging
logging.basicConfig(filename='main.log', level=logging.DEBUG)


class SensorInterface:
    def __init__(self):
        self.init_common_attributes()
        self.init_sensors()
        self.start_update_thread()  # Separate method to start the thread

    def start_update_thread(self):
        self.update_thread = threading.Thread(target=self.update_sensors)
        self.update_thread.start()
        
    def init_common_attributes(self):
        self.sensor_data_lock = threading.Lock()
        self.update_thread = threading.Thread(target=self.update_sensors)
        self.update_thread.start()
        self.GRID_SIZE = GRID_SIZE
        self.MUX_ADDRESS = 0x70
        self.bus = smbus.SMBus(1)
        self.i2c = busio.I2C(board.SCL, board.SDA)
        self.obstacle_data = np.zeros(self.GRID_SIZE)
        self.tca = adafruit_tca9548a.TCA9548A(self.i2c, address=0x70)
        self.shutdown_pins = [22, 23]
        self.sensor_data = {}

    def init_i2c(self):
        try:
            return busio.I2C(board.SCL, board.SDA)
        except Exception as e:
            print(f"Error during I2C initialization: {e}")
            return None

    def init_sensor(self, sensor_name, init_func, *args, **kwargs):
        try:
            return init_func(*args, **kwargs)
        except Exception as e:
            print(f"Error during {sensor_name} initialization: {e}")
            return None

    def init_sensors(self):
        try:
            self.select_mux_channel(3)
            self.bme280 = self.init_sensor("BME280", adafruit_bme280.Adafruit_BME280_I2C, self.i2c, address=0x76)
            self.mpu = self.init_sensor("MPU9250", MPU9250, address_ak=AK8963_ADDRESS, address_mpu_master=MPU9050_ADDRESS_69, bus=1, gfs=GFS_1000, afs=AFS_8G, mfs=AK8963_BIT_16, mode=AK8963_MODE_C100HZ)
            self.select_mux_channel(2)
            self.ina3221 = self.init_sensor("INA3221", INA3221.INA3221, self.i2c)
            self.vl53l0x_right = self.init_sensor("VL53L0X right sensor", adafruit_vl53l0x.VL53L0X, self.tca[6])
            self.vl53l0x_left = self.init_sensor("VL53L0X left sensor", adafruit_vl53l0x.VL53L0X, self.tca[7])
            self.mpu.configure()  # Apply the settings to the registers.
        except Exception as e:
            print(f"Error during sensor initialization: {e}")

    # FUNCTIONS
    def update_sensors(self):
        while True:
            with self.sensor_data_lock:
                self.sensor_data['ToF_Right'] = self.read_vl53l0x_right
                self.sensor_data['ToF_Left'] = self.read_vl53l0x_left
                self.sensor_data['compass'] = self.read_mpu9250_compass
                self.sensor_data['gyro'] = self.read_mpu9250_gyro
                self.sensor_data['accel'] = self.read_mpu9250_accel
                self.sensor_data['bme280'] = self.read_bme280
                self.sensor_data['solar'] = self.read_ina3221(1)
                self.sensor_data['battery'] = self.read_ina3221(3)
            time.sleep(0.5)
               
    def reset_sensors(self):
        for pin_num in self.shutdown_pins:
            pin = digitalio.DigitalInOut(getattr(board, f"D{pin_num}"))
            pin.direction = digitalio.Direction.OUTPUT
            pin.value = False
        time.sleep(0.05)
        for pin_num in self.shutdown_pins:
            pin = digitalio.DigitalInOut(getattr(board, f"D{pin_num}"))
            pin.direction = digitalio.Direction.OUTPUT
            pin.value = True
        time.sleep(0.05)

    def select_mux_channel(self, channel):
        """Select the specified channel on the TCA9548A I2C multiplexer."""
        if 0 <= channel <= 7:
            try:
                self.bus.write_byte(self.MUX_ADDRESS, 1 << channel)
            except Exception as e:
                print(f"Error during multiplexer channel selection: {e}")
        else:
            raise ValueError("Multiplexer channel must be an integer between 0 and 7.")

    def read_bme280(self):
        """Read BME280 sensor data."""
        try:
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
            distance = self.vl53l0x_left.range
            if distance > 0:
                return distance
            else:
                return -1  # Error
        except Exception as e:
            print(f"Error during VL53L0X left read: {e}")

    def read_vl53l0x_right(self):
        """Read VL53L0X ToF sensor data."""
        try:
            distance = self.vl53l0x_right.range
            if distance > 0:
                return distance
            else:
                return -1  # Error
        except Exception as e:
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
        left_distance = self.sensor_data['ToF_Left']
        right_distance = self.sensor_data['ToF_Right']

        # Use compass data to get the direction
        direction = self.sensor_data['compass']

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
        with self.sensor_data_lock:
            return self.obstacle_data

    def calculate_speed(self):
        """Calculate speed based on accelerometer data."""
        try:
            current_acceleration = self.sensor_data['accel']
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
                bme280_data = self.sensor_data['bme280']
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

sensor_interface = SensorInterface()