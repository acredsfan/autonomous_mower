# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

# import time
# import VL53L0X
# import RPi.GPIO as GPIO

# try:

#     # GPIO for Sensor 1 shutdown pin
#     right_shutdown = 23
#     # GPIO for Sensor 2 shutdown pin
#     left_shutdown = 22

#     GPIO.setwarnings(False)

#     # Setup GPIO for shutdown pins on each VL53L0X
#     GPIO.setmode(GPIO.BCM)
#     GPIO.setup(right_shutdown, GPIO.OUT)
#     GPIO.setup(left_shutdown, GPIO.OUT)

#     # Set all shutdown pins low to turn off each VL53L0X
#     GPIO.output(right_shutdown, GPIO.LOW)
#     GPIO.output(left_shutdown, GPIO.LOW)

#     # Keep all low for 500 ms or so to make sure they reset
#     time.sleep(0.50)

#     # Create a VL53L0X object for device on TCA9548A bus 1
#     tof_right = VL53L0X.VL53L0X(tca9548a_num=6, tca9548a_addr=0x70)
#     # Create a VL53L0X object for device on TCA9548A bus 2
#     tof_left = VL53L0X.VL53L0X(tca9548a_num=7, tca9548a_addr=0x70)
#     tof_right.open()
#     tof_left.open()

#     # Start ranging on TCA9548A bus 1
#     GPIO.output(right_shutdown, GPIO.HIGH)
#     time.sleep(0.50)
#     tof_right.start_ranging(VL53L0X.Vl53l0xAccuracyMode.BETTER)
#     # Start ranging on TCA9548A bus 2
#     GPIO.output(left_shutdown, GPIO.HIGH)
#     time.sleep(0.50)
#     tof_left.start_ranging(VL53L0X.Vl53l0xAccuracyMode.BETTER)

#     timing = tof_right.get_timing()
#     if timing < 20000:
#         timing = 20000
#     print("Timing %d ms" % (timing/1000))

#     for count in range(1, 5):
#         # Get distance from VL53L0X  on TCA9548A bus 1
#         distance = tof_right.get_distance()
#         if distance > 0:
#             print("right: %d mm, %d cm, %d" % (distance, (distance/10), count))
#         else:
#             print("%d - ERROR" % 1)

#         # Get distance from VL53L0X  on TCA9548A bus 2
#         distance = tof_left.get_distance()
#         if distance > 0:
#             print("left: %d mm, %d cm, %d" % (distance, (distance/10), count))
#         else:
#             print("%d - ERROR" % 2)

#         time.sleep(timing/1000000.00)

#     tof_right.stop_ranging()
#     GPIO.output(right_shutdown, GPIO.LOW)
#     tof_left.stop_ranging()
#     GPIO.output(left_shutdown, GPIO.LOW)

#     tof_right.close()
#     tof_left.close()


# except KeyboardInterrupt:
#     # Code will reach here when a keyboard interrupt (Ctrl+C) is detected
#     print("Program stopped by the user")


import smbus
import time
import VL53L0X

# Initialize the I2C bus and the multiplexer.
bus = smbus.SMBus(1)
multiplexer_address = 0x70

# Define a function to select a channel on the multiplexer.
def select_channel(channel):
    if channel > 7:
        return
    bus.write_byte(multiplexer_address, 1<<channel)

# Create two instances of the VL53L0X sensor.
sensor1 = VL53L0X.VL53L0X(i2c_address=0x29)
sensor2 = VL53L0X.VL53L0X(i2c_address=0x29)

# Select channel 0 on the multiplexer and initialize the first sensor.
select_channel(6)
sensor1.open()
sensor1.start_ranging(VL53L0X.VL53L0X_BETTER_ACCURACY_MODE)

# Select channel 1 on the multiplexer and initialize the second sensor.
select_channel(7)
sensor2.open()
sensor2.start_ranging(VL53L0X.VL53L0X_BETTER_ACCURACY_MODE)

while True:
    # Select channel 0 and read from the first sensor.
    select_channel(6)
    distance1 = sensor1.get_distance()
    print("Distance on sensor 1: %d mm" % distance1)

    # Select channel 1 and read from the second sensor.
    select_channel(7)
    distance2 = sensor2.get_distance()
    print("Distance on sensor 2: %d mm" % distance2)

    time.sleep(1)
