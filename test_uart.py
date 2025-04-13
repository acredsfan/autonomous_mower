import serial
import time

SERIAL_PORT = "/dev/ttyACM1"  # Update as needed
BAUD_RATE = 115200


def send_test_signals():
    try:
        with serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1) as ser:
            print(f"Connected to {SERIAL_PORT} at {BAUD_RATE} baud.")

            # Use 10-character strings like "1500, 1500"
            test_data = [
                (1500, 1500),
                (1600, 1500),
                (1400, 1500),
                (1500, 1600),
                (1500, 1400),
                (1600, 1600),
                (1400, 1400),
                (1500, 1500),
            ]

            for steering, throttle in test_data:
                # IMPORTANT: No '\r' in the string, just 10 characters "1500,
                # 1500"
                command_str = f"{steering}, {throttle}"  # e.g. "1500, 1500"
                ser.write(command_str.encode())

                print(f"Sent: {command_str}")

                # Optionally, you can read any echo or prints from
                # rp2040_code.py
                time.sleep(0.5)
                response = ser.read_all().decode().strip()
                if response:
                    print(f"Received: {response}")
                else:
                    print("No response received.")

    except serial.SerialException as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    send_test_signals()
