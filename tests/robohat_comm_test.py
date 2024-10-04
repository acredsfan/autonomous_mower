import serial

ser = serial.Serial('/dev/ttyS0', 115200, timeout=1)
ser.write(b'1500, 1500\r')
ser.close()
