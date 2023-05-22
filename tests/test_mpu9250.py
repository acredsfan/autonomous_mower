import time
from mpu9250_jmdev.registers import *
from mpu9250_jmdev.mpu_9250 import MPU9250

# Initialize the MPU9250 sensor
mpu = MPU9250(
    address_ak=AK8963_ADDRESS, 
    address_mpu_master=MPU9250_ADDRESS_69, # In 0x68 Address
    bus=1,  # SDA and SCL are connected to GPIO2 and GPIO3 respectively, which correspond to I2C bus 1 on Raspberry Pi
    gfs=GFS_1000, 
    afs=AFS_8G, 
    mfs=AK8963_BIT_16, 
    mode=AK8963_MODE_C100HZ
)

mpu.configure()  # Apply the settings to the registers

print("MPU9250 id: " + hex(mpu.whoami))

while True:
    print("Accelerometer", mpu.readAccelerometerMaster())
    print("Gyroscope", mpu.readGyroscopeMaster())
    print("Magnetometer", mpu.readMagnetometerMaster())
    print("Temperature", mpu.readTemperatureMaster())

    time.sleep(1)  # Sleep for 1 second
