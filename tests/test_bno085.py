import time
import board
import busio
from adafruit_bno08x import (
    BNO_REPORT_ACCELEROMETER,
    BNO_REPORT_GYROSCOPE,
    BNO_REPORT_MAGNETOMETER,
    BNO_REPORT_ROTATION_VECTOR,
)
from adafruit_bno08x.i2c import BNO08X_I2C

i2c = busio.I2C(board.SCL, board.SDA)
bno = BNO08X_I2C(i2c, address=0x4B)  # Specify the address here

bno.enable_feature(BNO_REPORT_ACCELEROMETER)
bno.enable_feature(BNO_REPORT_GYROSCOPE)
bno.enable_feature(BNO_REPORT_MAGNETOMETER)
bno.enable_feature(BNO_REPORT_ROTATION_VECTOR)

error_threshold = 3  # Set how many consecutive errors are needed before reporting
error_counts = {
    "KeyError": 0,
    "IndexError": 0,
    "OtherError": 0
}


while True:
    try:
        time.sleep(1)
        print("Acceleration:")
        accel_x, accel_y, accel_z = bno.acceleration  # pylint:disable=no-member
        print("X: %0.6f  Y: %0.6f Z: %0.6f  m/s^2" % (accel_x, accel_y, accel_z))
        print("")

        print("Gyro:")
        gyro_x, gyro_y, gyro_z = bno.gyro  # pylint:disable=no-member
        print("X: %0.6f  Y: %0.6f Z: %0.6f rads/s" % (gyro_x, gyro_y, gyro_z))
        print("")

        print("Magnetometer:")
        mag_x, mag_y, mag_z = bno.magnetic  # pylint:disable=no-member
        print("X: %0.6f  Y: %0.6f Z: %0.6f uT" % (mag_x, mag_y, mag_z))
        print("")

        print("Rotation Vector Quaternion:")
        quat_i, quat_j, quat_k, quat_real = bno.quaternion  # pylint:disable=no-member
        print(
            "I: %0.6f  J: %0.6f K: %0.6f  Real: %0.6f" % (quat_i, quat_j, quat_k, quat_real)
        )
        print("")

        error_counts = {key: 0 for key in error_counts}

    except KeyError as e:
        error_counts["KeyError"] += 1
        if error_counts["KeyError"] >= error_threshold:
            print(f"Consecutive KeyError encountered: {e}")
            # Optionally reset the counter after logging
            error_counts["KeyError"] = 0

    except IndexError as e:
        error_counts["IndexError"] += 1
        if error_counts["IndexError"] >= error_threshold:
            print(f"Consecutive IndexError encountered: {e}")
            # Optionally reset the counter after logging
            error_counts["IndexError"] = 0

    except Exception as e:
        error_counts["OtherError"] += 1
        if error_counts["OtherError"] >= error_threshold:
            print(f"Consecutive unexpected error encountered: {e}")
            # Optionally reset the counter after logging
            error_counts["OtherError"] = 0