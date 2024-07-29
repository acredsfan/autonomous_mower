import board
import busio

# Initialize I2C bus
i2c = busio.I2C(board.SCL, board.SDA)

# Check if I2C bus is locked
while not i2c.try_lock():
    pass

# Scan for devices
devices = i2c.scan()

# Print device addresses
print("I2C devices found:", [hex(device) for device in devices])

# Unlock I2C bus
i2c.unlock()
