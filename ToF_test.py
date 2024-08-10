import time
import board
from digitalio import DigitalInOut
from adafruit_vl53l0x import VL53L0X

# Declare the singleton variable for the default I2C bus
i2c = board.I2C()  # Uses board.SCL and board.SDA

# Declare the digital output pins connected to the "SHDN" pin on each VL53L0X sensor
xshut = [
    DigitalInOut(board.D22), #Left
    DigitalInOut(board.D23), #Right
    # Add more VL53L0X sensors by defining their SHDN pins here
]

# Make sure these pins are a digital output, not a digital input
for power_pin in xshut:
    power_pin.switch_to_output(value=False)
    # These pins are active when Low, meaning:
    #   if the output signal is LOW, then the VL53L0X sensor is off.
    #   if the output signal is HIGH, then the VL53L0X sensor is on.
# All VL53L0X sensors are now off

# Initialize a list to be used for the array of VL53L0X sensors
vl53 = []

# Turn on one sensor at a time and set its address
for i, power_pin in enumerate(xshut):
    # Turn on the VL53L0X to allow hardware check
    power_pin.value = True
    time.sleep(0.1)  # Delay for the sensor to power up
    
    # Instantiate the VL53L0X sensor on the I2C bus & insert it into the "vl53" list
    sensor = VL53L0X(i2c)
    sensor.start_continuous()
    vl53.append(sensor)  # Also performs VL53L0X hardware check

    # No need to change the address of the last VL53L0X sensor
    if i < len(xshut) - 1:
        # Default address is 0x29. Change that to something else
        new_address = 0x30 + i  # Address assigned should NOT be already in use
        sensor.set_address(new_address)
        power_pin.value = False  # Turn off the sensor after changing the address
        time.sleep(0.1)  # Delay to ensure proper shutdown

# Power up all sensors again with their new addresses
for power_pin in xshut:
    power_pin.value = True
time.sleep(0.1)  # Delay for all sensors to power up

# Confirm addresses by re-initializing sensors with new addresses
for i, power_pin in enumerate(xshut):
    address = 0x29 if i == 0 else 0x30 + (i - 1)
    sensor = VL53L0X(i2c, address=address)
    vl53[i] = sensor

def detect_range(count=5):
    """Take count=5 samples"""
    while count:
        for index, sensor in enumerate(vl53):
            print(f"Sensor {index + 1} Range: {sensor.range} mm")
        time.sleep(1.0)
        count -= 1

def stop_continuous():
    """This is not required if you use XSHUT to reset the sensor.
    Unless if you want to save some energy
    """
    for sensor in vl53:
        sensor.stop_continuous()

if __name__ == "__main__":
    detect_range()
    stop_continuous()
else:
    print(
        "Multiple VL53L0X sensors' addresses are assigned properly\n"
        "Execute detect_range() to read each sensor's range readings.\n"
        "When you are done with readings, execute stop_continuous()\n"
        "to stop the continuous mode."
    )
