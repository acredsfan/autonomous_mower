import smbus2 as smbus
import board
from adafruit_bme280 import basic as adafruit_bme280
import adafruit_vl53l0x
from adafruit_bno08x.i2c import BNO08X_I2C
import adafruit_bno08x
import barbudor_ina3221.full as INA3221
import gpiod
import busio
import time
import logging
import threading

# Initialize logging
logging.basicConfig(filename='/home/pi/autonomous_mower/main.log', level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s')

class SensorInterface:
    def __init__(self):
        self.sensor_data_lock = threading.Lock()
        self.sensor_data = {}
        self.init_common_attributes()
        self.init_sensors()
        # Wait for init_sensor() to finish
        time.sleep(3)
        # Start update thread after init_sensors() completes
        self.start_update_thread()

    def start_update_thread(self):
        self.update_thread = threading.Thread(target=self.update_sensors)
        self.update_thread.start()

    def init_common_attributes(self):
        self.GRID_SIZE = GRID_SIZE
        self.bus = smbus.SMBus(1)
        self.i2c = busio.I2C(board.SCL, board.SDA)
        self.shutdown_pins = [22, 23]
        self.interrupt_pins = [6, 12]
        self.sensor_data = {}
        self.init_gpio()

    def init_gpio(self):
        self.chip = gpiod.Chip('gpiochip0')
        self.shutdown_lines = [self.chip.get_line(pin) for pin in self.shutdown_pins]
        self.interrupt_lines = [self.chip.get_line(pin) for pin in self.interrupt_pins]

        for line in self.shutdown_lines:
            line.request(consumer='shutdown', type=gpiod.LINE_REQ_DIR_OUT)
            line.set_value(1)

        for line in self.interrupt_lines:
            line.request(consumer='interrupt', type=gpiod.LINE_REQ_EV_FALLING_EDGE)

    def init_i2c(self):
        try:
            return busio.I2C(board.SCL, board.SDA)
        except Exception as e:
            logging.error(f"Error during I2C initialization: {e}")
            return None

    def init_sensor(self, sensor_name, init_func, *args, **kwargs):
        try:
            sensor = init_func(*args, **kwargs)
            logging.debug(f"{sensor_name} initialized successfully.")
            return sensor
        except Exception as e:
            logging.error(f"Error during {sensor_name} initialization: {e}")
            return None

    def init_sensors(self):
        self.bme280 = self.init_sensor("BME280", adafruit_bme280.Adafruit_BME280_I2C, self.i2c, address=0x76)
        self.bno085 = self.init_sensor("BNO085", BNO08X_I2C, self.i2c)
        self.ina3221 = self.init_sensor("INA3221", INA3221.INA3221, self.i2c)

        if self.bme280 is None:
            logging.error("Failed to initialize BME280 sensor")
        if self.bno085 is None:
            logging.error("Failed to initialize BNO085 sensor")
        if self.ina3221 is None:
            logging.error("Failed to initialize INA3221 sensor")

        # Initialize VL53L0X sensors and change their I2C addresses
        self.reset_sensors()  # Ensure sensors are in known state

        self.vl53l0x_left = self.init_sensor("VL53L0X left sensor", adafruit_vl53l0x.VL53L0X, self.i2c)
        if self.vl53l0x_left:
            self.vl53l0x_left.set_address(0x30)  # New address for the left sensor
        else:
            logging.error("Failed to initialize VL53L0X left sensor")

        time.sleep(0.1)

        self.vl53l0x_right = self.init_sensor("VL53L0X right sensor", adafruit_vl53l0x.VL53L0X, self.i2c)
        if self.vl53l0x_right:
            self.vl53l0x_right.set_address(0x31)  # New address for the right sensor
        else:
            logging.error("Failed to initialize VL53L0X right sensor")

        # Setup GPIO1 interrupt handling
        for line in self.interrupt_lines:
            line.event_read()  # Clear any existing events
            threading.Thread(target=self.monitor_interrupts, args=(line,)).start()

    def monitor_interrupts(self, line):
        while True:
            event = line.event_wait(sec=1)
            if event:
                event = line.event_read()
                if event.type == gpiod.LineEvent.FALLING_EDGE:
                    if line == self.interrupt_lines[0]:
                        self.handle_interrupt_left()
                    elif line == self.interrupt_lines[1]:
                        self.handle_interrupt_right()

    def handle_interrupt_left(self):
        logging.info("Interrupt from left VL53L0X sensor")
        self.sensor_data['ToF_Left'] = self.read_vl53l0x_left()

    def handle_interrupt_right(self):
        logging.info("Interrupt from right VL53L0X sensor")
        self.sensor_data['ToF_Right'] = self.read_vl53l0x_right()

    def update_sensors(self):
        while True:
            with self.sensor_data_lock:
                self.sensor_data['compass'] = self.read_bno085_compass()
                self.sensor_data['gyro'] = self.read_bno085_gyro()
                self.sensor_data['accel'] = self.read_bno085_accel()
                self.sensor_data['bme280'] = self.read_bme280()
                self.sensor_data['solar'] = self.read_ina3221(1)
                self.sensor_data['battery'] = self.read_ina3221(3)
            time.sleep(1.0)

    def reset_sensors(self):
        for line in self.shutdown_lines:
            line.set_value(0)
        time.sleep(0.05)
        for line in self.shutdown_lines:
            line.set_value(1)
        time.sleep(0.05)

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
            logging.error(f"Error during BME280 read: {e}")
            return {}

    def read_vl53l0x_left(self):
        """Read VL53L0X ToF sensor data."""
        try:
            distance = self.vl53l0x_left.range
            if distance > 0:
                return distance
            else:
                return -1  # Error
        except Exception as e:
            logging.error(f"Error during VL53L0X left read: {e}")
            return -1

    def read_vl53l0x_right(self):
        """Read VL53L0X ToF sensor data."""
        try:
            distance = self.vl53l0x_right.range
            if distance > 0:
                return distance
            else:
                return -1  # Error
        except Exception as e:
            logging.error(f"Error during VL53L0X right read: {e}")
            return -1

    def read_bno085_compass(self):
        """Read BNO085 compass data."""
        try:
            quaternion = self.bno085.quaternion
            return quaternion  # Example format
        except Exception as e:
            logging.error(f"Error during BNO085 compass read: {e}")
            return ()

    def read_bno085_gyro(self):
        """Read BNO085 gyro data."""
        try:
            gyro = self.bno085.gyro
            return gyro  # Example format
        except Exception as e:
            logging.error(f"Error during BNO085 gyro read: {e}")
            return ()

    def read_bno085_accel(self):
        """Read BNO085 accelerometer data."""
        try:
            accel = self.bno085.acceleration
            return accel  # Example format
        except Exception as e:
            logging.error(f"Error during BNO085 accelerometer read: {e}")
            return ()

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
            logging.error(f"Error during INA3221 read: {e}")
            return {}

    def update_obstacle_data(self, tof_left, tof_right, compass_data):
        """
        Update the obstacle_data grid based on ToF and compass data.
        """
        left_distance = self.sensor_data['ToF_Left']
        right_distance = self.sensor_data['ToF_Right']
        direction = self.sensor_data['compass']

        dx, dy = 0, 0
        if 0 <= direction < 90:
            dx, dy = 1, 1
        elif 90 <= direction < 180:
            dx, dy = -1, 1
        elif 180 <= direction < 270:
            dx, dy = -1, -1
        elif 270 <= direction < 360:
            dx, dy = 1, -1

        center_x, center_y = GRID_SIZE[0] // 2, GRID_SIZE[1] // 2

        if left_distance < 15:
            self.obstacle_data[center_x + dx][center_y + dy] = 1

        if right_distance < 15:
            self.obstacle_data[center_x - dx][center_y - dy] = 1

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
                self.speed[i] += (current_acceleration[i] + self.previous_acceleration[i]) / 2 * time_difference * 3600 / 1609.34

            self.previous_acceleration = current_acceleration
            self.previous_time = current_time

            return self.speed
        except Exception as e:
            logging.error(f"Error during speed calculation: {e}")
            return []

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
                    logging.warning("Sensor data is not available. Retrying...")
                    time.sleep(5)
                    attempts += 1
            except Exception as e:
                logging.error(f"Error during checking mowing conditions: {e}")
                return False

        logging.error("Sensor data is not available after 20 attempts. Returning False.")
        return False

    def cleanup(self):
        self.reset_sensors()
        self.bus.deinit()
        self.vl53l0x_left.stop_ranging()
        self.vl53l0x_right.stop_ranging()
        self.bno085.close()
        self.bme280.deinit()
        self.ina3221.deinit()
        logging.info("Sensors deinitialized.")

sensor_interface = SensorInterface()