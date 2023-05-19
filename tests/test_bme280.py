from hardware_interface.sensor_interface import SensorInterface
import time

def test_bme280():
    sensor_interface = SensorInterface()

    # Allow some time for sensor to initialize
    time.sleep(1)

    # Read and print BME280 data for 10 times
    for _ in range(10):
        bme280_data = sensor_interface.read_bme280()
        print(f"Temperature: {bme280_data['temperature']} C")
        print(f"Humidity: {bme280_data['humidity']} %")
        print(f"Pressure: {bme280_data['pressure']} hPa")
        time.sleep(2)

if __name__ == "__main__":
    test_bme280()
