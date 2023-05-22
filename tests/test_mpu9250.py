# MPU6050 9-DoF Example Printout
import time
from mpu9250_jmdev.registers import *
from mpu9250_jmdev.mpu_9250 import MPU9250

mpu = MPU9250(
    address_ak=AK8963_ADDRESS, 
    address_mpu_master=MPU9050_ADDRESS_69, # Master has 0x68 Address
    address_mpu_slave=MPU9050_ADDRESS_69, # Slave has 0x68 Address
    bus=1, 
    gfs=GFS_1000, 
    afs=AFS_8G, 
    mfs=AK8963_BIT_16, 
    mode=AK8963_MODE_C100HZ)

mpu.configure() # Apply the settings to the registers.

while True:
   
    print("|.....MPU9250 in 0x68 I2C Bus - Master.....|")
    print("Accelerometer", mpu.readAccelerometerMaster())
    print("Gyroscope", mpu.readGyroscopeMaster())
    print("Magnetometer", mpu.readMagnetometerMaster())
    print("Temperature", mpu.readTemperatureMaster())
    print("\n")

    print("|.....MPU9250 in 0x68 I2C Bus - Slave in 0x68 auxiliary sensor address.....|")
    print("Accelerometer", mpu.readAccelerometerSlave())
    print("Gyroscope", mpu.readGyroscopeSlave())
    print("Temperature", mpu.readTemperatureSlave())
    print("\n")

    time.sleep(1)