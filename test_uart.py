import serial
import time

# Configuration
SERIAL_PORT = "/dev/ttyACM1"  # Update this to match your setup
BAUD_RATE = 115200


def send_test_signals():
    try:
        # Open the serial port
        with serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1) as ser:
            print(f"Connected to {SERIAL_PORT} at {BAUD_RATE} baud.")

            # Test data: steering and throttle values
            test_data = [
                (1500, 1500),  # Neutral
                (1600, 1500),  # Slight right
                (1400, 1500),  # Slight left
                (1500, 1600),  # Forward
                (1500, 1400),  # Reverse
                (1600, 1600),  # Forward-right
                (1400, 1400),  # Reverse-left
                (1500, 1500),  # Back to neutral
            ]

            for steering, throttle in test_data:
                # Format the data as expected by code.py
                command = f"{steering}, {throttle}\r\n"
                ser.write(command.encode())
                print(f"Sent: {command.strip()}")

                # Wait for a response (if any)
                response = ser.readline().decode().strip()
                if response:
                    print(f"Received: {response}")
                else:
                    print("No response received.")

                # Delay between commands
                time.sleep(1)

    except serial.SerialException as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    send_test_signals()
