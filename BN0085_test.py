import time
import board
import busio
from adafruit_bno08x import BNO08X_I2C

def main():
    # Initialize I2C bus and sensor
    i2c = busio.I2C(board.SCL, board.SDA)
    bno = BNO08X_I2C(i2c)

    # Check connection
    try:
        print("Checking BNO085 connection...")
        bno.begin_calibration()
        print("BNO085 connected successfully!")
    except Exception as e:
        print("Failed to connect to BNO085:", e)
        return

    # Read and print orientation data
    try:
        while True:
            quat = bno.quaternion
            print("Quaternion: w={}, x={}, y={}, z={}".format(quat[0], quat[1], quat[2], quat[3]))
            time.sleep(1)
    except KeyboardInterrupt:
        print("Exiting...")
    except Exception as e:
        print("Error reading BNO085 data:", e)

if __name__ == "__main__":
    main()
