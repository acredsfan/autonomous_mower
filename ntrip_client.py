#!/usr/bin/env python3
"""
NTRIP Client for ZED-F9P RTK GPS
================================

This script connects to an NTRIP server, receives RTCM corrections,
and forwards them to the ZED-F9P GPS module for RTK positioning.

@hardware_interface ZED-F9P GPS module via UART/USB
@gpio_pin_usage N/A - uses serial communication
"""

import os
import sys
import time
import socket
import base64
import threading
from typing import Optional
from dotenv import load_dotenv
import logging

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Load environment variables
load_dotenv()

from mower.hardware.serial_port import SerialPort
from mower.utilities.logger_config import LoggerConfigInfo

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    handlers=[logging.FileHandler('logs/mower.log'), logging.StreamHandler()])

logger = LoggerConfigInfo.get_logger(__name__)

class NTRIPClient:
    """
    NTRIP client that receives RTK corrections and sends them to GPS module.
    """
    
    def __init__(self, 
                 server: str, 
                 port: int, 
                 username: str, 
                 password: str, 
                 mountpoint: str,
                 gps_port: str,
                 gps_baud: int = 115200,
                 debug: bool = False):
        """
        Initialize NTRIP client.
        
        Args:
            server: NTRIP server hostname/IP
            port: NTRIP server port
            username: NTRIP username
            password: NTRIP password
            mountpoint: NTRIP mountpoint
            gps_port: GPS serial port
            gps_baud: GPS baud rate
            debug: Enable debug output
        """
        self.server = server
        self.port = port
        self.username = username
        self.password = password
        self.mountpoint = mountpoint
        self.gps_port = gps_port
        self.gps_baud = gps_baud
        self.debug = debug
        
        self.ntrip_socket: Optional[socket.socket] = None
        self.gps_serial: Optional[SerialPort] = None
        self.running = False
        self.stats = {
            'rtcm_messages': 0,
            'bytes_received': 0,
            'bytes_sent_to_gps': 0,
            'connection_errors': 0
        }

    def connect_ntrip(self, gga_sentence: str) -> bool:
        """
        Connect to NTRIP server.
        """
        try:
            print(f"Connecting to NTRIP server {self.server}:{self.port}...")
            self.ntrip_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.ntrip_socket.settimeout(10)
            self.ntrip_socket.connect((self.server, self.port))

            # Create HTTP request with authentication
            credentials = f"{self.username}:{self.password}"
            auth_string = base64.b64encode(credentials.encode()).decode()

            request = (f"GET /{self.mountpoint} HTTP/1.1\r\n"
                       f"Host: {self.server}:{self.port}\r\n"
                       f"User-Agent: NTRIP_PythonClient/1.0\r\n"
                       f"Authorization: Basic {auth_string}\r\n"
                       f"Connection: close\r\n\r\n")

            if self.debug:
                print("--- Sending NTRIP Request ---")
                print(request)
                print("-----------------------------")

            self.ntrip_socket.sendall(request.encode())

            # Read response
            response = self.ntrip_socket.recv(4096).decode(errors='ignore')

            if "ICY 200 OK" in response or "HTTP/1.1 200 OK" in response:
                print("✓ NTRIP connection successful")
                if self.debug:
                    print(f"Server response: {response}")

                # After successful connection, send GGA sentence to start RTCM stream
                print(f"Sending GGA sentence to start stream: {gga_sentence}")
                gga_with_crlf = gga_sentence + "\r\n"
                self.ntrip_socket.sendall(gga_with_crlf.encode())

                return True
            else:
                print(f"✗ NTRIP connection failed. Server response:\n{response}")
                return False

        except Exception as e:
            print(f"✗ NTRIP connection error: {e}")
            self.stats['connection_errors'] += 1
            return False

    def connect_gps(self) -> bool:
        """
        Connect to GPS module.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            if self.debug:
                print(f"Connecting to GPS at {self.gps_port}...")
            
            self.gps_serial = SerialPort(self.gps_port, baudrate=self.gps_baud, timeout=1.0)
            self.gps_serial.start()
            
            print("✓ GPS connection successful")
            return True
            
        except Exception as e:
            print(f"✗ GPS connection error: {e}")
            return False

    def receive_rtcm_data(self):
        """
        Receive RTCM data from NTRIP server and forward to GPS.
        """
        print("Starting RTCM data relay...")
        
        buffer = b''
        last_stats_time = time.time()
        
        try:
            while self.running:
                try:
                    # Receive data from NTRIP server
                    data = self.ntrip_socket.recv(1024)
                    
                    if not data:
                        print("✗ NTRIP connection lost")
                        break
                    
                    buffer += data
                    self.stats['bytes_received'] += len(data)
                    
                    # Process RTCM messages in buffer
                    while len(buffer) >= 3:
                        # Look for RTCM3 message start (0xD3)
                        if buffer[0] != 0xD3:
                            buffer = buffer[1:]  # Skip byte
                            continue
                        
                        # Get message length from header
                        if len(buffer) < 3:
                            break
                            
                        msg_length = ((buffer[1] & 0x03) << 8) | buffer[2]
                        total_length = msg_length + 6  # Header (3) + Data + CRC (3)
                        
                        if len(buffer) < total_length:
                            break  # Wait for complete message
                        
                        # Extract complete RTCM message
                        rtcm_message = buffer[:total_length]
                        buffer = buffer[total_length:]
                        
                        # Send to GPS
                        if self.gps_serial:
                            success = self.gps_serial.write(rtcm_message.decode('latin-1'))
                            if success:
                                self.stats['bytes_sent_to_gps'] += len(rtcm_message)
                                self.stats['rtcm_messages'] += 1
                                
                                if self.debug:
                                    msg_type = (rtcm_message[3] << 4) | (rtcm_message[4] >> 4)
                                    print(f"[DEBUG] RTCM {msg_type}: {len(rtcm_message)} bytes")
                    
                    # Print statistics every 10 seconds
                    if time.time() - last_stats_time > 10:
                        self.print_statistics()
                        last_stats_time = time.time()
                        
                except socket.timeout:
                    continue
                except Exception as e:
                    print(f"Error receiving RTCM data: {e}")
                    self.stats['connection_errors'] += 1
                    time.sleep(1)
                    
        except KeyboardInterrupt:
            print("\\nStopping RTCM relay...")

    def print_statistics(self):
        """Print current statistics."""
        print(f"Stats: RTCM msgs: {self.stats['rtcm_messages']}, "
              f"RX: {self.stats['bytes_received']} bytes, "
              f"TX: {self.stats['bytes_sent_to_gps']} bytes, "
              f"Errors: {self.stats['connection_errors']}")

    def get_gga_sentence(self) -> Optional[str]:
        """
        Connect to the GPS and retrieve a single NMEA GGA sentence.
        """
        print("Attempting to get GGA sentence from GPS...")
        temp_gps_serial = None
        try:
            # Temporarily connect to the GPS to get a GGA sentence
            temp_gps_serial = SerialPort(self.gps_port, baudrate=self.gps_baud, timeout=2.0)
            temp_gps_serial.start()
            start_time = time.time()
            while time.time() - start_time < 15:  # Try for 15 seconds
                line = temp_gps_serial.read_line()
                # Debug: log the type and value of what is returned
                logger.debug(f"Raw line from GPS: type={type(line)}, value={line}")
                # If line is a tuple (timestamp, nmea_line), extract nmea_line
                if isinstance(line, tuple) and len(line) == 2:
                    nmea_line = line[1]
                else:
                    nmea_line = line
                if nmea_line and isinstance(nmea_line, str) and nmea_line.startswith("$GPGGA"):
                    print(f"✓ Found GGA: {nmea_line.strip()}")
                    return nmea_line.strip()
            print("✗ Timed out waiting for a GGA sentence from the GPS.")
            return None
        except Exception as e:
            print(f"✗ Error getting GGA from GPS: {e}")
            return None
        finally:
            if temp_gps_serial:
                try:
                    temp_gps_serial.stop()
                except Exception as e:
                    print(f"Error stopping temporary GPS serial port: {e}")

    def run(self):
        """
        Main run loop for NTRIP client.
        """
        print("NTRIP RTK Client Starting...")
        print("=" * 40)

        # 1. Get GGA sentence from the GPS first
        gga_sentence = self.get_gga_sentence()
        if not gga_sentence:
            print("✗ Cannot proceed without a GGA sentence. Exiting.")
            return False

        # Add detailed logging for raw GPS data
        logger.debug(f"Raw GPS data received: {gga_sentence}")

        # Fix the 'tuple' object error in GGA sentence retrieval
        if isinstance(gga_sentence, tuple):
            gga_sentence = gga_sentence[0]  # Extract the actual string if it's a tuple

        # Validate that gga_sentence is a string
        if not isinstance(gga_sentence, str):
            logger.error(f"Invalid GGA sentence format: {gga_sentence}")
            raise ValueError("Expected a string for GGA sentence")

        # Log the validated GGA sentence
        logger.debug(f"Validated GGA sentence: {gga_sentence}")

        # 2. Now, connect to the NTRIP server
        print(f"NTRIP Server: {self.server}:{self.port}")
        print(f"Mountpoint: {self.mountpoint}")
        if not self.connect_ntrip(gga_sentence):
            return False
        
        # 3. Connect to GPS for writing data
        if not self.connect_gps():
            return False
        
        self.running = True
        try:
            self.receive_rtcm_data()
        finally:
            self.cleanup()
        
        return True

    def cleanup(self):
        """Clean up connections."""
        self.running = False
        
        if self.ntrip_socket:
            try:
                self.ntrip_socket.close()
            except:
                pass
        
        if self.gps_serial:
            try:
                self.gps_serial.stop()
            except:
                pass
        
        print("\\nFinal Statistics:")
        self.print_statistics()


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="NTRIP Client for RTK GPS")
    parser.add_argument('--server', type=str,
                       default=os.getenv('NTRIP_URL', '156.63.133.115'),
                       help='NTRIP server hostname/IP')
    parser.add_argument('--port', type=int,
                       default=int(os.getenv('NTRIP_PORT', '2101')),
                       help='NTRIP server port')
    parser.add_argument('--username', type=str,
                       default=os.getenv('NTRIP_USER', 'AaronLink1'),
                       help='NTRIP username')
    parser.add_argument('--password', type=str,
                       default=os.getenv('NTRIP_PASS', 'RobotMower'),
                       help='NTRIP password')
    parser.add_argument('--mountpoint', type=str,
                       default=os.getenv('NTRIP_MOUNTPOINT', 'ODOT_G_R_E_C_RTX_RTCM3'),
                       help='NTRIP mountpoint')
    parser.add_argument('--gps-port', type=str,
                       default=os.getenv('GPS_SERIAL_PORT', '/dev/ttyACM0'),
                       help='GPS serial port')
    parser.add_argument('--gps-baud', type=int,
                       default=int(os.getenv('GPS_BAUD_RATE', '115200')),
                       help='GPS baud rate')
    parser.add_argument('--debug', action='store_true',
                       help='Enable debug output')
    
    args = parser.parse_args()
    
    # Create and run NTRIP client
    client = NTRIPClient(
        server=args.server,
        port=args.port,
        username=args.username,
        password=args.password,
        mountpoint=args.mountpoint,
        gps_port=args.gps_port,
        gps_baud=args.gps_baud,
        debug=args.debug
    )
    
    client.run()


if __name__ == "__main__":
    main()
