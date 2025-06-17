import os
import platform
import threading
import time
from typing import Any, Tuple

import serial
import serial.tools.list_ports
from dotenv import load_dotenv

from mower.utilities.logger_config import LoggerConfigInfo

# Load environment variables from .env file in repository root
load_dotenv()


logger = LoggerConfigInfo.get_logger(__name__)


GPS_PORT = os.getenv("GPS_SERIAL_PORT")
GPS_BAUDRATE = int(os.getenv("GPS_BAUD_RATE", "9600"))
IMU_SERIAL_PORT = os.getenv("IMU_SERIAL_PORT")
IMU_BAUDRATE = int(os.getenv("IMU_BAUD_RATE", "3000000"))


class SerialPort:
    """
    Wrapper for serial port connect/read/write.
    Use this rather than raw pyserial api.
    It provides a layer that automatically
    catches exceptions and encodes/decodes
    between bytes and str.
    It also provides a layer of indirection
    so that we can mock this for testing.
    """

    _instance = None

    def __init__(
        self,
        port: str,
        baudrate: int,
        bits: int = 8,
        parity: str = "N",
        stop_bits: int = 1,
        charset: str = "ascii",
        timeout: float = 0.1,
        receiver_buffer_size: int = 2048,  # Added for compatibility with IMU
    ):
        self.port = port
        self.baudrate = baudrate
        self.bits = bits
        self.parity = parity
        self.stop_bits = stop_bits
        self.charset = charset
        self.timeout = timeout
        self.receiver_buffer_size = receiver_buffer_size
        self.ser = None
        self.data_buffer = ""  # ADDED: Buffer for incomplete lines

    def start(self):
        logger.debug(f"Attempting to open serial port {self.port}...")
        try:
            self.ser = serial.Serial(
                self.port,
                self.baudrate,
                self.bits,
                self.parity,
                self.stop_bits,
                timeout=self.timeout,
            )
            # Set buffer size if supported (Linux only)
            if hasattr(self.ser, "set_buffer_size"):
                try:
                    self.ser.set_buffer_size(rx_size=self.receiver_buffer_size)
                except Exception as e:
                    logger.warning(f"Could not set serial buffer size: {e}")
            logger.info(f"Successfully opened serial port {self.ser.name}")  # Changed to info
        except serial.SerialException as e:  # Catch specific serial exception
            logger.error(f"SerialException opening port {self.port}: {e}")
            self.ser = None  # Ensure ser is None on failure
            # Re-raise or handle as appropriate for the application startup
            # For now, let's re-raise to make startup failure explicit
            raise
        except Exception as e:
            logger.error(f"Unexpected error opening serial port {self.port}: {e}")
            self.ser = None
            raise
        return self

    def stop(self):
        if self.ser is not None and self.ser.is_open:  # Check if open
            logger.debug(f"Closing serial port {self.port}")
            try:
                sp = self.ser
                self.ser = None
                sp.close()
                logger.info(f"Closed serial port {self.port}")
            except serial.SerialException as e:
                logger.error(f"SerialException closing port {self.port}: {e}")
            except Exception as e:
                logger.error(f"Unexpected error closing serial port {self.port}: {e}")
        elif self.ser is None:
            logger.debug(f"Serial port {self.port} was already None, nothing to close.")
        else:  # Not None but not open
            logger.debug(f"Serial port {self.port} was not open, nothing to close.")
        return self

    @staticmethod
    def is_mac():
        return "Darwin" == platform.system()

    def buffered(self) -> int:
        """
        return: the number of buffered characters
        """
        if self.ser is None or not self.ser.is_open:
            return 0

        # ser.in_waiting is always zero on mac, so act like we are buffered
        if SerialPort.is_mac():
            return 1

        try:
            return self.ser.in_waiting
        except serial.serialutil.SerialException:
            return 0

    def clear(self):
        """
        Clear the serial read buffer
        """
        try:
            if self.ser is not None and self.ser.is_open:
                self.ser.reset_input_buffer()
        except serial.serialutil.SerialException:
            pass
        return self

    def readBytes(self, count: int = 0) -> Tuple[bool, bytes]:
        """
        if there are characters waiting,
        then read them from the serial port
        bytes: number of bytes to read
        return: tuple of
                bool: True if count bytes were available to read,
                      false if not enough bytes were available
                bytes: bytes string if count bytes read (may be blank),
                       blank if count bytes are not available
        """
        if self.ser is None or not self.ser.is_open:
            logger.warning(f"Attempted to read from closed/uninitialized port {self.port}")
            return (False, b"")  # Return empty bytes if port not open

        try:
            waiting = self.buffered() >= count
            if waiting:
                input_bytes = self.ser.read(count)
                return (waiting, input_bytes)
            return (False, b"")
        except (serial.serialutil.SerialException, TypeError):
            logger.warning("Failed reading bytes from serial port")
            return (False, b"")

    def read(self, count: int = 0) -> Tuple[bool, str]:
        ok, bytestring = self.readBytes(count)
        try:
            return (ok, bytestring.decode(self.charset))
        except UnicodeDecodeError:
            return (False, "")

    # RENAMED from readln to read_line
    def read_line(self) -> Tuple[bool, str]:
        """
        if there are characters waiting,
        then read a line from the serial port.
        This will block until end-of-line can be read.
        The end-of-line is included in the return value.
        return: tuple of
                bool: True if line was read, false if not
                str: line if read (may be blank),
                     blank if not read
        """
        if self.ser is None or not self.ser.is_open:
            logger.warning(f"Attempted to readline from closed/uninitialized port {self.port}")
            return (False, "")  # Return empty string if port not open

        try:
            # Use built-in readline with timeout
            line = self.ser.readline()
            if line:
                decoded_line = line.decode(self.charset, errors="ignore")
                return (True, decoded_line)
            return (False, "")

        except (serial.serialutil.SerialException, TypeError, UnicodeDecodeError) as e:
            logger.warning(f"Failed reading line from serial port {self.port}: {e}")
            return (False, "")

    def get_parsed_data(self, parser_function) -> Tuple[bool, Any]:
        """Reads a line and parses it using the provided function."""
        # Changed from self.readln
        success, line = self.read_line()
        if success and line:
            try:
                parsed_data = parser_function(line)
                return True, parsed_data
            except Exception as e:
                logger.error(f"Error parsing line '{line.strip()}': {e}")
                return False, None
        return False, None

    def write(self, data: str) -> bool:
        """
        Write a string to the serial port.
        Ensures the data is encoded to bytes before writing.
        """
        if self.ser is not None and self.ser.is_open:
            try:
                # Encode the data to bytes using the configured charset
                encoded_data = data.encode(self.charset)
                self.ser.write(encoded_data)
                return True
            except (serial.serialutil.SerialException, TypeError) as e:
                logger.warning(f"Can't write to serial port {self.port}: {e}")
        return False


class SerialLineReader:
    """
    Donkeycar part for reading lines from a serial port
    """

    _instance = None

    def __init__(self, serial: SerialPort, max_lines: int = 0, debug: bool = False):
        self.serial = serial
        self.max_lines = max_lines
        self.debug = debug
        self.lines = []
        self.lock = threading.Lock()
        self.running = True
        self._open()
        self.clear()

    def _open(self):
        with self.lock:
            self.serial.start().clear()

    def _close(self):
        with self.lock:
            self.serial.stop()

    def clear(self):
        with self.lock:
            self.lines = []
            self.serial.clear()

    @staticmethod
    def is_mac():
        return "Darwin" == platform.system()

    def _readline(self) -> str:
        if self.lock.acquire(blocking=False):
            try:
                if SerialLineReader.is_mac() or (self.serial.buffered() > 0):
                    success, buffer = self.serial.read_line()
                    if success and buffer:
                        return buffer.strip()
            except Exception as e:
                if self.debug:
                    logger.error(f"Error in _readline: {e}")
            finally:
                self.lock.release()
        return None

    def run(self):
        if self.running:
            lines = []
            line = self._readline()
            while line is not None:
                lines.append((time.time(), line.strip()))
                if self.max_lines is None or self.max_lines == 0 or len(lines) < self.max_lines:
                    line = self._readline()
                else:
                    break
            return lines
        return []

    def run_threaded(self):
        if not self.running:
            return []

        with self.lock:
            lines = self.lines
            self.lines = []
            return lines

    def update(self):
        buffered_lines = []
        while self.running:
            line = self._readline()
            if line:
                buffered_lines.append((time.time(), line.strip()))
            if buffered_lines:
                if self.lock.acquire(blocking=False):
                    try:
                        self.lines += buffered_lines
                        buffered_lines = []
                    finally:
                        self.lock.release()
            time.sleep(0.01)  # Small delay to prevent excessive CPU usage

    def shutdown(self):
        self.running = False
        self._close()


if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-s",
        "--serial",
        type=str,
        required=True,
        help="Serial port address, like '/dev/tty.usbmodem1411'",
    )
    parser.add_argument(
        "-b",
        "--baudrate",
        type=int,
        default=9600,
        help="Serial port baud rate.",
    )
    parser.add_argument(
        "-t",
        "--timeout",
        type=float,
        default=0.5,
        help="Serial port timeout in seconds.",
    )
    parser.add_argument(
        "-sp",
        "--samples",
        type=int,
        default=5,
        help="Number of samples per read cycle; 0 for unlimited.",
    )
    parser.add_argument("-th", "--threaded", action="store_true", help="run in threaded mode.")
    parser.add_argument("-db", "--debug", action="store_true", help="Enable extra logging")
    args = parser.parse_args()

    if args.samples < 0:
        print("Samples per read cycle," "greater than zero OR zero for unlimited")
        parser.print_help()
        sys.exit(0)

    if args.timeout <= 0:
        print("Timeout must be greater than zero")
        parser.print_help()
        sys.exit(0)

    update_thread = None
    reader = None

    try:
        serial_port = SerialPort(args.serial, baudrate=args.baudrate, timeout=args.timeout)
        line_reader = SerialLineReader(serial_port, max_lines=args.samples, debug=args.debug)

        if args.threaded:
            update_thread = threading.Thread(target=line_reader.update, args=())
            update_thread.start()

        def read_lines():
            if args.threaded:
                return line_reader.run_threaded()
            else:
                return line_reader.run()

        while line_reader.running:
            readings = read_lines()
            if readings:
                for line in readings:
                    print(line)
    finally:
        if line_reader:
            line_reader.shutdown()
        if update_thread is not None:
            update_thread.join()  # wait for thread to end
