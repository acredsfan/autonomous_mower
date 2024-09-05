import board
import digitalio
import time

# Define GPIO pins connected to the XSHUT pins of each VL53L0X sensor
XSHUT_1 = digitalio.DigitalInOut(board.D22)  # Change D17 to the GPIO pin connected to the first sensor's XSHUT
XSHUT_2 = digitalio.DigitalInOut(board.D23)  # Change D27 to the GPIO pin connected to the second sensor's XSHUT

# Configure the XSHUT pins as outputs
XSHUT_1.direction = digitalio.Direction.OUTPUT
XSHUT_2.direction = digitalio.Direction.OUTPUT

def reset_sensor(xshut_pin):
    """
    Resets a VL53L0X sensor by toggling its XSHUT pin.
    
    :param xshut_pin: DigitalInOut object connected to the sensor's XSHUT pin
    """
    xshut_pin.value = False  # Pull XSHUT low to turn off the sensor
    time.sleep(0.1)          # Short delay to ensure the sensor is fully powered down
    xshut_pin.value = True   # Pull XSHUT high to power the sensor back up
    time.sleep(0.1)          # Wait for the sensor to initialize
    print(f"Sensor reset complete on GPIO pin {xshut_pin.pin}.")

# Reset both sensors
reset_sensor(XSHUT_1)  # Reset the first sensor
# report the reset status
print("Sensor 1 reset complete")

reset_sensor(XSHUT_2)  # Reset the second sensor
# report the reset status
print("Sensor 2 reset complete")