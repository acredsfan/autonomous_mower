import serial  # type:ignore
import time

SERIAL_PORT = "/dev/Serial0"
BAUD_RATE = 115200


def read_response(ser, timeout=1.0):
    """Read a line from serial with timeout, return as string."""
    ser.timeout = timeout
    try:
        resp = ser.readline().decode(errors="ignore").strip()
        return resp
    except Exception:
        return ""


def main():
    try:
        with serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1) as ser:
            print(f"Connected to {SERIAL_PORT}.")

            # 1) Disable real RC on the RP2040
            ser.write(b"rc=disable\r")
            print("Sent 'rc=disable'")
            resp = read_response(ser)
            if resp:
                print("RP2040 said:", resp)
            else:
                print("No response from RP2040.")

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
            for (st, th) in test_data:
                line = f"{st}, {th}\r\n"
                ser.write(line.encode())
                print("Sent:", line.strip())
                resp = read_response(ser)
                if resp:
                    print("Got back:", resp)
                else:
                    print("No response for servo command.")
                time.sleep(0.4)

            # 3) Re-enable real RC
            ser.write(b"rc=enable\r")
            print("Sent 'rc=enable'")
            resp = read_response(ser)
            if resp:
                print("RP2040 said:", resp)
            else:
                print("No response from RP2040.")

    except serial.SerialException as e:
        print("Error opening port:", e)


if __name__ == "__main__":
    main()
