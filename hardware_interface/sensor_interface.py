#IMPORTS
import smbus2 as smbus
import board
from adafruit_bme280 import basic as adafruit_bme280
import VL53L0X
from mpu9250_jmdev.registers import *
from mpu9250_jmdev.mpu_9250 import MPU9250
from barbudor_ina3221.full import *
import RPi.GPIO as GPIO
import busio
import time

class SensorInterface:
    def __init__(self):
        self.MUX_ADDRESS = 0x70  # Replace with your multiplexer's I2C address if different
        self.bus = smbus.SMBus(1)
        self.i2c = busio.I2C(board.SCL, board.SDA)
        try:
            self.select_mux_channel(3)
            self.bme280 = adafruit_bme280.Adafruit_BME280_I2C(self.i2c)
            self.vl53l0x_right = VL53L0X.VL53L0X(tca9548a_num=6, tca9548a_addr=0x70)
            self.vl53l0x_left = VL53L0X.VL53L0X(tca9548a_num=7, tca9548a_addr=0x70)
            self.vl53l0x_right.open()
            self.vl53l0x_left.open()
            self.mpu = MPU9250(
                address_ak=AK8963_ADDRESS, 
                address_mpu_master=MPU9050_ADDRESS_69, # In 0x69 Address
                address_mpu_slave=None, 
                bus=1,
                gfs=GFS_1000, 
                afs=AFS_8G, 
                mfs=AK8963_BIT_16, 
                mode=AK8963_MODE_C100HZ)
            self.select_mux_channel(2)
            self.ina3221 = INA3221(self.i2c)
            self.ina3221.enable_channel(1)
            self.ina3221.enable_channel(3)
            self.HALL_EFFECT_SENSOR_1 = 17  # Replace with the correct GPIO pin number for sensor 1
            self.HALL_EFFECT_SENSOR_2 = 18  # Replace with the correct GPIO pin number for sensor 2
            # change this to match the location's pressure (hPa) at sea level
            self.bme280.sea_level_pressure = 1013.25
            self.previous_acceleration = [0, 0, 0]  # previous acceleration values for x, y, z
            self.previous_time = time.time()  # time when the previous acceleration was measured
            self.speed = [0, 0, 0]  # current speed for x, y, z
        except Exception as e:
            print(f"Error during initialization: {e}")

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

             # Initialize Left TOF sensor
            self.vl53l0x_left.start_ranging(VL53L0X.Vl53l0xAccuracyMode.BETTER)

            # Initialize Right TOF sensor
            self.vl53l0x_right.start_ranging(VL53L0X.Vl53l0xAccuracyMode.BETTER)

            # Initialize hall effect sensors
            self.init_hall_effect_sensors()
        except Exception as e:
            print(f"Error during sensor initialization: {e}")




    def read_bme280(self):
        """Read BME280 sensor data."""
        try:
            self.select_mux_channel(3)
            self.i2c = busio.I2C(board.SCL, board.SDA)
            self.bme280 = adafruit_bme280.Adafruit_BME280_I2C(self.i2c)
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
            return self.vl53l0x_left.get_distance()
        except Exception as e:
            print(f"Error during VL53L0X left read: {e}")

    def read_vl53l0x_right(self):
        """Read VL53L0X ToF sensor data."""
        try:
            return self.vl53l0x_right.get_distance()
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


    def read_hall_effect_sensors(self):
        try:
            sensor_1_state = GPIO.input(self.HALL_EFFECT_SENSOR_1)
            sensor_2_state = GPIO.input(self.HALL_EFFECT_SENSOR_2)

            return sensor_1_state, sensor_2_state
        except Exception as e:
            print(f"Error during hall effect sensor read: {e}")

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
        # Check for high humidity
        try:
            bme280_data = self.read_bme280()
            if bme280_data['humidity'] > 90:
                return False

            # Check for high temperature
            if bme280_data['temperature'] > 30:
                return False

            # Check for low temperature
            if bme280_data['temperature'] < 1:
                return False

            # Check for low pressure
            if bme280_data['pressure'] < 1000:
                return False
        except Exception as e:
            print(f"Error during checking mowing conditions: {e}")

        # Return True if all conditions are met
        return True
    
# At the end of sensor_interface.py
sensor_interface = SensorInterface()
