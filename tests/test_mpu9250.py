import os
import sys
import time
import smbus

from imusensor.MPU9250 import MPU9250

address = 0x68
bus = smbus.SMBus(1)
imu = MPU9250.MPU9250(bus, address)

def readSensor():
	try:
		imu.readSensor()
	except Exception as e:
		print("Error reading sensor:", e)
		return None
	return imu.AccelVals, imu.GyroVals, imu.MagVals

def computeOrientation():
	try:
		imu.computeOrientation()
	except Exception as e:
		print("Error computing orientation:", e)
		return None
	return imu.roll, imu.pitch, imu.yaw

def main():
	while True:
		accel, gyro, mag = readSensor()
		roll, pitch, yaw = computeOrientation()

		print ("Accel x: {0} ; Accel y : {1} ; Accel z : {2}".format(accel[0], accel[1], accel[2]))
		print ("Gyro x: {0} ; Gyro y : {1} ; Gyro z : {2}".format(gyro[0], gyro[1], gyro[2]))
		print ("Mag x: {0} ; Mag y : {1} ; Mag z : {2}".format(mag[0], mag[1], mag[2]))
		print ("roll: {0} ; pitch : {1} ; yaw : {2}".format(roll, pitch, yaw))
		time.sleep(0.1)

if __name__ == "__main__":
	main()