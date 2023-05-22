# MPU6050 9-DoF Example Printout

import time
from mpu9250_jmdev.registers import *
from mpu9250_jmdev.mpu_9250 import MPU9250

# Initialize the MPU9250 module.
mpu = MPU9250(
    address_ak=AK8963_ADDRESS, 
    address_mpu_master=MPU9050_ADDRESS_69,  # In 0x69 Address
    address_mpu_slave=None, 
    bus=1,
    gfs=GFS_1000, 
    afs=AFS_8G, 
    mfs=AK8963_BIT_16, 
    mode=AK8963_MODE_C100HZ)

# Apply the settings to the registers.
mpu.configure()
mpu.calibrate()

# Loop to print sensor data.
while True:
    print("Accelerometer", mpu.readAccelerometerMaster())
    print("Gyroscope", mpu.readGyroscopeMaster())
    print("Magnetometer", mpu.readMagnetometerMaster())
    print("Temperature", (mpu.readTemperatureMaster()*1.8)+32)
    time.sleep(1)