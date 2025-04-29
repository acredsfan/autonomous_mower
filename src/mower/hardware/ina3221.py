import barbudor_ina3221.full as INA3221  # Ensure `barbudor_ina3221` is installed

from mower.utilities.logger_config import LoggerConfigInfo as LoggerConfig

# Initialize logger
logging = LoggerConfig.get_logger(__name__)


class INA3221Sensor:

    @staticmethod
    def init_ina3221(i2c):
        try:
            sensor = INA3221.INA3221(i2c)
            logger.info("INA3221 initialized successfully.")
            return sensor
        except Exception as e:
            logger.error(f"Error initializing INA3221: {e}")
            return None

    @staticmethod
    def read_ina3221(sensor, channel):
        try:
            if channel in [1, 3]:
                Voltage = round(sensor.bus_voltage(channel), 1)
                Shunt_Voltage = round(sensor.shunt_voltage(channel), 1)
                Current = round(sensor.current(channel), 1)
                sensor_data = {
                    "bus_voltage": Voltage,
                    "current": Current,
                    "shunt_voltage": Shunt_Voltage,
                }
                if channel == 3:
                    Charge_Level = round(
                        (Voltage - 11.2) / (14.6 - 11.2) * 100, 1
                    )
                    sensor_data["charge_level"] = f"{Charge_Level}%"
                return sensor_data
            else:
                raise ValueError(
                    "Invalid INA3221 channel. Please use 1 or 3."
                )
        except Exception as e:
            logging.error(f"Error reading INA3221 data: {e}")
            return {}

    """Function to determine the battery state of charge
    for a 12.8V 20Ah lithium-ion battery.
    Variables may need to be changed based on the
    battery chemistry of the battery being used."""

    @staticmethod
    def battery_charge(sensor):
        try:
            Voltage = round(sensor.bus_voltage(3), 2)
            Charge_Level = round((Voltage - 11.5) / (13.5 - 11.5) * 100, 1)
            return f"{Charge_Level}%"
        except Exception as e:
            logging.error(f"Error reading battery charge level: {e}")
            return "Error"


if __name__ == "__main__":
    # Initialize the INA3221 sensor
    ina3221_sensor = INA3221Sensor()
    ina3221 = ina3221_sensor.init_ina3221(i2c)  # Pass the required `i2c` argument
    print(ina3221_sensor.read_ina3221(ina3221, 1))
    print(ina3221_sensor.read_ina3221(ina3221, 3))
    print(ina3221_sensor.battery_charge(ina3221))
