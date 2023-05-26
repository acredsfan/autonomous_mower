import time
from VL53L0X import VL53L0X
from smbus2 import SMBus, i2c_msg

# I2C multiplexer address
MUX_ADDRESS = 0x70

# ToF sensor addresses on the multiplexer
TOF_RIGHT_CHANNEL = 0
TOF_LEFT_CHANNEL = 1

# I2C bus number (usually 1 for Raspberry Pi)
I2C_BUS = 1

def select_channel(channel):
    bus = SMBus(I2C_BUS)
    msg = i2c_msg.write(MUX_ADDRESS, [1 << channel])
    bus.i2c_rdwr(msg)
    bus.close()

def read_sensor(channel):
    select_channel(channel)
    tof = VL53L0X(i2c_bus=I2C_BUS, i2c_address=0x29)
    success = tof.start_ranging(vl53l0x.Vl53l0xAccuracyMode.BETTER)
    if not success:
        print("Error starting ranging")
        return None
    distance = tof.get_distance() # This is in millimeters
    tof.stop_ranging()
    return distance / 25.4  # Convert to inches

while True:
    distance_right = read_sensor(TOF_RIGHT_CHANNEL)
    print(f"Right ToF Sensor Distance: {distance_right} inches")
    time.sleep(0.1)  # You can adjust this delay as needed

    distance_left = read_sensor(TOF_LEFT_CHANNEL)
    print(f"Left ToF Sensor Distance: {distance_left} inches")
    time.sleep(0.1)  # You can adjust this delay as needed
