"""
UART Test Script for Autonomous Mower.

This script performs UART communication tests with the mower's hardware.
It sends commands and reads responses to verify that the UART interface
is working correctly.
"""

import time
import serial

SERIAL_PORT = "/dev/ttyACM1"
BAUD_RATE = 115200


def main():
    """
    Main function to test UART communication with the mower hardware.

    Establishes a serial connection and sends test commands to verify
    the connection is working properly.
    """
    try:
        with serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1) as ser:
            print(f"Connected to {SERIAL_PORT}.")

            # 1) Disable real RC on the RP2040
            ser.write(b"rc=disable\r")
            time.sleep(0.2)
            print("Sent 'rc=disable'")
            resp = ser.read_all().decode().strip()
            if resp:
                print("RP2040 said:", resp)

            # 2) Send servo lines
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
            for st, th in test_data:
                line = f"{st}, {th}\r\n"
                ser.write(line.encode())
                print("Sent:", line.strip())
                time.sleep(0.4)
                resp = ser.read_all().decode().strip()
                if resp:
                    print("Got back:", resp)

            # 3) Re-enable real RC
            ser.write(b"rc=enable\r")
            print("Sent 'rc=enable'")
            time.sleep(0.5)
            resp = ser.read_all().decode().strip()
            if resp:
                print("RP2040 said:", resp)

            # Now any new lines you send for servo pulses won't be used
            # if the RP2040 is looking at real RC pins again.

    except serial.SerialException as e:
        print("Error opening port:", e)


if __name__ == "__main__":
    main()
