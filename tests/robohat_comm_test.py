import serial
import time

ser = serial.Serial('/dev/serial0', 115200, timeout=1)
time.sleep(2)  # Wait for the serial connection to initialize

test_command = b'1500, 1500\r'
ser.write(test_command)
print(f"Sent: {test_command}")

ser.close()
