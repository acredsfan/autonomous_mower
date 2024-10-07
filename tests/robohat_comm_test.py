import serial
import time

ser = serial.Serial('/dev/serial0', 115200, timeout=1)
time.sleep(2)  # Wait for the serial connection to initialize

test_command = b'1500, 1500\r'
test_command_2 = b'1600, 1600\r'
test_command_3 = b'1400, 1400\r'
ser.write(test_command)
print(f"Sent: {test_command}")
time.sleep(2)
ser.write(test_command_2)
print(f"Sent: {test_command_2}")
time.sleep(2)
ser.write(test_command_3)
print(f"Sent: {test_command_3}")
time.sleep(2)
ser.write(test_command)
print(f"Sent: {test_command}")

ser.close()
