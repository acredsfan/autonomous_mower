import serial  # type:ignore
import time

SERIAL_PORT = "/dev/serial0"   # GPIO14/15 hardware UART
BAUD_RATE = 115200


def read_response(ser, timeout=1.0):
    ser.timeout = timeout
    try:
        return ser.readline().decode(errors="ignore").strip()
    except Exception:
        return ""


def main():
    try:
        with serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1) as ser:
            print(f"Connected to {SERIAL_PORT}.")
            ser.write(b"rc=disable\r")
            print("Sent 'rc=disable'")
            print("RP2040 said:", read_response(ser) or "<no resp>")

            test_data = [
                (1500, 1500), (1600, 1500), (1400, 1500),
                (1500, 1600), (1500, 1400), (1600, 1600),
                (1400, 1400), (1500, 1500),
            ]
            for st, th in test_data:
                line = f"{st},{th}\r\n"
                ser.write(line.encode())
                print("Sent:", line.strip())
                print("Got   :", read_response(ser) or "<no resp>")
                time.sleep(0.4)

            ser.write(b"rc=enable\r")
            print("Sent 'rc=enable'")
            print("RP2040 said:", read_response(ser) or "<no resp>")

    except serial.SerialException as e:
        print("Error opening port:", e)


if __name__ == "__main__":
    main()
