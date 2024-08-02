import time
import board
from digitalio import DigitalInOut
from adafruit_vl53l0x import VL53L0X

# Declare the singleton variable for the default I2C bus
i2c = board.I2C()  # Uses board.SCL and board.SDA

# Declare the digital output pins connected to the "SHDN" pin on each VL53L0X sensor
xshut = [
    DigitalInOut(board.D22),
    DigitalInOut(board.D23),
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

# Now change the addresses of the VL53L0X sensors
for i, power_pin in enumerate(xshut):
    # Turn on the VL53L0X to allow hardware check
    power_pin.value = True
    # Instantiate the VL53L0X sensor on the I2C bus & insert it into the "vl53" list
    vl53.insert(i, VL53L0X(i2c))  # Also performs VL53L0X hardware check

    # Start continuous mode
    vl53[i].start_continuous()

    # No need to change the address of the last VL53L0X sensor
    if i < len(xshut) - 1:
        # Default address is 0x29. Change that to something else
        vl53[i].set_address(0x30 + i)  # Address assigned should NOT be already in use

# There is a helpful list of pre-designated I2C addresses for various I2C devices at
# https://learn.adafruit.com/i2c-addresses/the-list
# According to this list 0x30-0x34 are available, although the list may be incomplete.
# In the python REPL, you can scan for all I2C devices that are attached and determine
# their addresses using:
#   >>> import board
#   >>> i2c = board.I2C()  # uses board.SCL and board.SDA
#   >>> if i2c.try_lock():
#   >>>     [hex(x) for x in i2c.scan()]
#   >>>     i2c.unlock()

def detect_range(count=5):
    """Take count=5 samples"""
    while count:
        for index, sensor in enumerate(vl53):
            print(f"Sensor {index + 1} Range: {sensor.range}mm")
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
