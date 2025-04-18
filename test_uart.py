import serial  # type:ignore
import time

SERIAL_PORT = "/dev/serial0"
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

            test_data = [
                (1500, 1500), (1600, 1500), (1400, 1500),
                (1500, 1600), (1500, 1400), (1600, 1600),
                (1400, 1400), (1500, 1500),
            ]
            for st, th in test_data:
                # Format: 4 digits, comma, space, 4 digits, CRLF
                line = f"{st:04d}, {th:04d}\r\n"
                ser.write(line.encode())
                print("Sent:", line.strip())
                print("Got   :", read_response(ser) or "<no resp>")
                time.sleep(0.4)

    except serial.SerialException as e:
        print("Error opening port:", e)


if __name__ == "__main__":
    main()
