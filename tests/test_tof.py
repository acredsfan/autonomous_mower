import board
import busio
import adafruit_tca9548a
import adafruit_vl53l0x

# Initialize I2C bus and sensor.
i2c = busio.I2C(board.SCL, board.SDA)

# Initialize TCA9548A multiplexer
tca = adafruit_tca9548a.TCA9548A(i2c, address=0x70)

# Initialize VL53L0X on channel 6 and 7 of TCA9548A
vl53_left = adafruit_vl53l0x.VL53L0X(tca[6])
vl53_right = adafruit_vl53l0x.VL53L0X(tca[7])

# Set shutdown pins
vl53_left._shutdown_pin = 22
vl53_right._shutdown_pin = 23

# Function to read distance
def read_distance(sensor, name):
    try:
        print(f"{name} Distance: {sensor.range}mm")
    except Exception as e:
        print(f"Error reading {name}: {e}")

# Main loop will read the range and print it every second.
while True:
    read_distance(vl53_left, "Left Sensor")
    read_distance(vl53_right, "Right Sensor")