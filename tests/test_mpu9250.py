import time
from mpu9250_jmdev.registers import *
from mpu9250_jmdev.mpu_9250 import MPU9250

mpu = MPU9250(
    address_ak=AK8963_ADDRESS, 
    address_mpu_master=0x69,  # In 0x69 Address
    bus=1,  
    gfs=GFS_1000, 
    afs=AFS_8G, 
    mfs=AK8963_BIT_16, 
    mode=AK8963_MODE_C100HZ
)

mpu.configure()

while True:
    print("Accelerometer", mpu.readAccelerometerMaster())
    print("Gyroscope", mpu.readGyroscopeMaster())
    print("Magnetometer", mpu.readMagnetometerMaster())
    print("Temperature", mpu.readTemperatureMaster())

    time.sleep(1)
