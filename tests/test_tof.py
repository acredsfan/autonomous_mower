# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import time
import VL53L0X

try:
    # Create a VL53L0X object for device on TCA9548A bus 1
    tof_right = VL53L0X.VL53L0X(tca9548a_num=6, tca9548a_addr=0x70)
    # Create a VL53L0X object for device on TCA9548A bus 2
    tof_left = VL53L0X.VL53L0X(tca9548a_num=7, tca9548a_addr=0x70)
    tof_right.open()
    tof_left.open()

    # Start ranging on TCA9548A bus 1
    tof_right.start_ranging(VL53L0X.Vl53l0xAccuracyMode.BETTER)
    # Start ranging on TCA9548A bus 2
    tof_left.start_ranging(VL53L0X.Vl53l0xAccuracyMode.BETTER)

    timing = tof_right.get_timing()
    if timing < 20000:
        timing = 20000
    print("Timing %d ms" % (timing/1000))

    for count in range(1, 5):
        # Get distance from VL53L0X  on TCA9548A bus 1
        distance = tof_right.get_distance()
        if distance > 0:
            print("1: %d mm, %d cm, %d" % (distance, (distance/10), count))

        # Get distance from VL53L0X  on TCA9548A bus 2
        distance = tof_left.get_distance()
        if distance > 0:
            print("2: %d mm, %d cm, %d" % (distance, (distance/10), count))

        time.sleep(timing/1000000.00)

    tof_right.stop_ranging()
    tof_left.stop_ranging()

    tof_right.close()
    tof_left.close()
    

except KeyboardInterrupt:
    # Code will reach here when a keyboard interrupt (Ctrl+C) is detected
    print("Program stopped by the user")
