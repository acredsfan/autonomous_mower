
import time
import board
from mpu9250 import MPU9250

i2c = board.I2C()
sensor = MPU9250(i2c)

#Get the address of the MPU9250
print("MPU9250 detected at: ", [hex(i) for i in sensor.whoami])

while True:
    print(sensor.acceleration)
    print(sensor.gyro)
    print(sensor.magnetic)
    print(sensor.temperature)

    time.sleep_ms(1000)

