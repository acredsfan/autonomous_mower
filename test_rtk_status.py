#!/usr/bin/env python3
"""
RTK GPS Status Verification Script for ZED-F9P
==============================================

This script verifies that RTK corrections are working properly on the ZED-F9P GPS module.
It checks for:
1. RTK correction reception
2. Fix quality improvements (from GPS to RTK FLOAT to RTK FIXED)
3. Accuracy improvements
4. NTRIP connection status

@hardware_interface ZED-F9P GPS module via UART/USB
@gpio_pin_usage N/A - uses serial communication
"""

import os
import sys
import time
import re
from typing import Dict, Optional, Tuple
from dotenv import load_dotenv

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Load environment variables
load_dotenv()

from mower.hardware.serial_port import SerialPort, SerialLineReader
from mower.utilities.logger_config import LoggerConfigInfo

logger = LoggerConfigInfo.get_logger(__name__)

class RTKStatusChecker:
    """
    Checks RTK GPS status and verifies correction reception.
    """
    
    def __init__(self, port: str, baudrate: int = 115200, debug: bool = False):
        """
        Initialize RTK status checker.
        
        Args:
            port: Serial port for GPS (e.g., '/dev/ttyACM0')
            baudrate: Baud rate for GPS communication
            debug: Enable debug output
        """
        self.port = port
        self.baudrate = baudrate
        self.debug = debug
        self.serial_port = None
        self.line_reader = None
        
        # RTK status tracking
        self.rtk_stats = {
            'gga_messages': 0,
            'rmc_messages': 0,
            'gsa_messages': 0,
            'gsv_messages': 0,
            'rtk_messages': 0,
            'fix_qualities': {},
            'satellites_used': [],
            'hdop_values': [],
            'accuracy_estimates': [],
            'rtk_age_values': [],
            'rtk_ratio_values': []
        }
        
        # Fix quality mappings for GGA messages
        self.fix_quality_map = {
            '0': 'No Fix',
            '1': 'GPS Fix',
            '2': 'DGPS Fix', 
            '3': 'PPS Fix',
            '4': 'RTK Fixed',
            '5': 'RTK Float',
            '6': 'Estimated',
            '7': 'Manual',
            '8': 'Simulation'
        }

    def connect(self) -> bool:
        """
        Connect to GPS module.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            self.serial_port = SerialPort(self.port, baudrate=self.baudrate, timeout=1.0)
            self.serial_port.start()
            self.line_reader = SerialLineReader(self.serial_port, debug=self.debug)
            logger.info(f"Connected to GPS at {self.port} ({self.baudrate} baud)")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to GPS: {e}")
            return False

    def disconnect(self):
        """Disconnect from GPS module."""
        if self.line_reader:
            self.line_reader.shutdown()
        if self.serial_port:
            self.serial_port.stop()

    def parse_gga_message(self, nmea_line: str) -> Optional[Dict]:
        """
        Parse GPGGA message for RTK status.
        
        Args:
            nmea_line: NMEA sentence string
            
        Returns:
            Dictionary with parsed GGA data or None
        """
        try:
            parts = nmea_line.split(',')
            if len(parts) < 15 or not parts[0].endswith('GGA'):
                return None
            
            # Extract relevant fields
            time_utc = parts[1]
            lat = parts[2]
            lat_dir = parts[3]
            lon = parts[4]
            lon_dir = parts[5]
            fix_quality = parts[6]
            satellites_used = parts[7]
            hdop = parts[8]
            altitude = parts[9]
            geoid_height = parts[11]
            rtk_age = parts[13]  # Age of RTK corrections
            rtk_station_id = parts[14].split('*')[0]  # RTK station ID
            
            return {
                'time_utc': time_utc,
                'latitude': lat,
                'lat_dir': lat_dir,
                'longitude': lon,
                'lon_dir': lon_dir,
                'fix_quality': fix_quality,
                'satellites_used': int(satellites_used) if satellites_used else 0,
                'hdop': float(hdop) if hdop else 0.0,
                'altitude': float(altitude) if altitude else 0.0,
                'geoid_height': float(geoid_height) if geoid_height else 0.0,
                'rtk_age': float(rtk_age) if rtk_age else None,
                'rtk_station_id': rtk_station_id if rtk_station_id else None
            }
            
        except (ValueError, IndexError) as e:
            if self.debug:
                print(f"[DEBUG] GGA parse error: {e}")
            return None

    def parse_gsa_message(self, nmea_line: str) -> Optional[Dict]:
        """
        Parse GPGSA message for DOP values.
        
        Args:
            nmea_line: NMEA sentence string
            
        Returns:
            Dictionary with parsed GSA data or None
        """
        try:
            parts = nmea_line.split(',')
            if len(parts) < 18 or not parts[0].endswith('GSA'):
                return None
            
            fix_mode = parts[1]  # M = Manual, A = Automatic
            fix_type = parts[2]  # 1 = No fix, 2 = 2D, 3 = 3D
            pdop = parts[15]     # Position DOP
            hdop = parts[16]     # Horizontal DOP
            vdop = parts[17].split('*')[0]  # Vertical DOP
            
            return {
                'fix_mode': fix_mode,
                'fix_type': int(fix_type) if fix_type else 0,
                'pdop': float(pdop) if pdop else 0.0,
                'hdop': float(hdop) if hdop else 0.0,
                'vdop': float(vdop) if vdop else 0.0
            }
            
        except (ValueError, IndexError) as e:
            if self.debug:
                print(f"[DEBUG] GSA parse error: {e}")
            return None

    def update_statistics(self, nmea_line: str):
        """
        Update RTK statistics from NMEA message.
        
        Args:
            nmea_line: NMEA sentence string
        """
        if 'GGA' in nmea_line:
            self.rtk_stats['gga_messages'] += 1
            gga_data = self.parse_gga_message(nmea_line)
            
            if gga_data:
                fix_quality = gga_data['fix_quality']
                fix_name = self.fix_quality_map.get(fix_quality, f'Unknown ({fix_quality})')
                
                # Track fix quality distribution
                if fix_name not in self.rtk_stats['fix_qualities']:
                    self.rtk_stats['fix_qualities'][fix_name] = 0
                self.rtk_stats['fix_qualities'][fix_name] += 1
                
                # Track satellite count and HDOP
                if gga_data['satellites_used'] > 0:
                    self.rtk_stats['satellites_used'].append(gga_data['satellites_used'])
                if gga_data['hdop'] > 0:
                    self.rtk_stats['hdop_values'].append(gga_data['hdop'])
                
                # Track RTK-specific data
                if gga_data['rtk_age'] is not None:
                    self.rtk_stats['rtk_age_values'].append(gga_data['rtk_age'])
                    self.rtk_stats['rtk_messages'] += 1
                
                # Calculate accuracy estimate from HDOP
                if gga_data['hdop'] > 0:
                    # Rough accuracy estimate: HDOP * 5 meters (typical for GPS)
                    accuracy_est = gga_data['hdop'] * 5.0
                    self.rtk_stats['accuracy_estimates'].append(accuracy_est)
        
        elif 'RMC' in nmea_line:
            self.rtk_stats['rmc_messages'] += 1
            
        elif 'GSA' in nmea_line:
            self.rtk_stats['gsa_messages'] += 1
            
        elif 'GSV' in nmea_line:
            self.rtk_stats['gsv_messages'] += 1

    def print_current_status(self, gga_data: Dict):
        """
        Print current RTK status.
        
        Args:
            gga_data: Parsed GGA message data
        """
        fix_quality = gga_data['fix_quality']
        fix_name = self.fix_quality_map.get(fix_quality, f'Unknown ({fix_quality})')
        
        # Determine RTK status
        if fix_quality == '4':
            rtk_status = "🟢 RTK FIXED"
        elif fix_quality == '5':
            rtk_status = "🟡 RTK FLOAT"
        elif fix_quality == '1':
            rtk_status = "🔴 GPS Only"
        else:
            rtk_status = f"⚪ {fix_name}"
        
        # Calculate accuracy estimate
        accuracy_est = gga_data['hdop'] * 5.0 if gga_data['hdop'] > 0 else 0
        
        print(f"Status: {rtk_status} | "
              f"Sats: {gga_data['satellites_used']:2d} | "
              f"HDOP: {gga_data['hdop']:4.1f} | "
              f"Acc: ~{accuracy_est:.1f}m", end="")
        
        if gga_data['rtk_age'] is not None:
            print(f" | RTK Age: {gga_data['rtk_age']:4.1f}s", end="")
        
        print()

    def print_statistics(self):
        """Print comprehensive RTK statistics."""
        print("\n" + "="*50)
        print("RTK GPS STATISTICS SUMMARY")
        print("="*50)
        
        # Message counts
        print(f"NMEA Messages Received:")
        print(f"  GGA (Position): {self.rtk_stats['gga_messages']}")
        print(f"  RMC (Recommended): {self.rtk_stats['rmc_messages']}")
        print(f"  GSA (DOP): {self.rtk_stats['gsa_messages']}")
        print(f"  GSV (Satellites): {self.rtk_stats['gsv_messages']}")
        print(f"  RTK Messages: {self.rtk_stats['rtk_messages']}")
        
        # Fix quality distribution
        print(f"\nFix Quality Distribution:")
        for fix_type, count in self.rtk_stats['fix_qualities'].items():
            percentage = (count / max(self.rtk_stats['gga_messages'], 1)) * 100
            print(f"  {fix_type}: {count} ({percentage:.1f}%)")
        
        # Satellite and accuracy stats
        if self.rtk_stats['satellites_used']:
            sat_avg = sum(self.rtk_stats['satellites_used']) / len(self.rtk_stats['satellites_used'])
            sat_min = min(self.rtk_stats['satellites_used'])
            sat_max = max(self.rtk_stats['satellites_used'])
            print(f"\nSatellite Count: Min={sat_min}, Max={sat_max}, Avg={sat_avg:.1f}")
        
        if self.rtk_stats['hdop_values']:
            hdop_avg = sum(self.rtk_stats['hdop_values']) / len(self.rtk_stats['hdop_values'])
            hdop_min = min(self.rtk_stats['hdop_values'])
            hdop_max = max(self.rtk_stats['hdop_values'])
            print(f"HDOP Values: Min={hdop_min:.1f}, Max={hdop_max:.1f}, Avg={hdop_avg:.1f}")
        
        if self.rtk_stats['accuracy_estimates']:
            acc_avg = sum(self.rtk_stats['accuracy_estimates']) / len(self.rtk_stats['accuracy_estimates'])
            acc_min = min(self.rtk_stats['accuracy_estimates'])
            acc_max = max(self.rtk_stats['accuracy_estimates'])
            print(f"Est. Accuracy: Min={acc_min:.1f}m, Max={acc_max:.1f}m, Avg={acc_avg:.1f}m")
        
        if self.rtk_stats['rtk_age_values']:
            age_avg = sum(self.rtk_stats['rtk_age_values']) / len(self.rtk_stats['rtk_age_values'])
            age_min = min(self.rtk_stats['rtk_age_values'])
            age_max = max(self.rtk_stats['rtk_age_values'])
            print(f"RTK Correction Age: Min={age_min:.1f}s, Max={age_max:.1f}s, Avg={age_avg:.1f}s")
        
        # RTK Assessment
        print(f"\nRTK ASSESSMENT:")
        rtk_percentage = (self.rtk_stats['rtk_messages'] / max(self.rtk_stats['gga_messages'], 1)) * 100
        
        if 'RTK Fixed' in self.rtk_stats['fix_qualities']:
            fixed_percentage = (self.rtk_stats['fix_qualities']['RTK Fixed'] / max(self.rtk_stats['gga_messages'], 1)) * 100
            print(f"✓ RTK Fixed Solutions: {fixed_percentage:.1f}% of readings")
        
        if 'RTK Float' in self.rtk_stats['fix_qualities']:
            float_percentage = (self.rtk_stats['fix_qualities']['RTK Float'] / max(self.rtk_stats['gga_messages'], 1)) * 100
            print(f"⚠ RTK Float Solutions: {float_percentage:.1f}% of readings")
        
        if rtk_percentage > 0:
            print(f"✓ RTK Corrections Active: {rtk_percentage:.1f}% of readings")
        else:
            print(f"✗ No RTK corrections detected")
        
        # Recommendations
        print(f"\nRECOMMENDATIONS:")
        if 'RTK Fixed' in self.rtk_stats['fix_qualities']:
            print("✓ RTK is working well!")
        elif 'RTK Float' in self.rtk_stats['fix_qualities']:
            print("⚠ RTK Float detected - check base station distance and signal quality")
        elif rtk_percentage > 0:
            print("⚠ RTK corrections received but not achieving fixed solution")
        else:
            print("✗ No RTK corrections - check NTRIP configuration and internet connection")

    def monitor_rtk_status(self, duration: int = 60):
        """
        Monitor RTK status for specified duration.
        
        Args:
            duration: Monitoring duration in seconds
        """
        print(f"Monitoring RTK GPS status for {duration} seconds...")
        print(f"Port: {self.port} | Baud: {self.baudrate}")
        print("-" * 70)
        
        start_time = time.time()
        last_status_time = 0
        
        try:
            while time.time() - start_time < duration:
                # Read GPS data
                lines = self.line_reader.run()
                
                for timestamp, nmea_line in lines:
                    if self.debug:
                        print(f"[DEBUG] {nmea_line}")
                    
                    # Update statistics
                    self.update_statistics(nmea_line)
                    
                    # Print status updates for GGA messages
                    if 'GGA' in nmea_line:
                        gga_data = self.parse_gga_message(nmea_line)
                        if gga_data and time.time() - last_status_time > 1.0:
                            self.print_current_status(gga_data)
                            last_status_time = time.time()
                
                time.sleep(0.1)  # Small delay to prevent excessive CPU usage
                
        except KeyboardInterrupt:
            print("\nMonitoring interrupted by user")
        
        # Print final statistics
        self.print_statistics()


def main():
    """Main function to run RTK status check."""
    import argparse
    
    parser = argparse.ArgumentParser(description="RTK GPS Status Verification Tool")
    parser.add_argument('--port', type=str, 
                       default=os.getenv('GPS_SERIAL_PORT', '/dev/ttyACM0'),
                       help='GPS serial port (default from .env)')
    parser.add_argument('--baud', type=int,
                       default=int(os.getenv('GPS_BAUD_RATE', '115200')),
                       help='GPS baud rate (default from .env)')
    parser.add_argument('--duration', type=int, default=60,
                       help='Monitoring duration in seconds (default: 60)')
    parser.add_argument('--debug', action='store_true',
                       help='Enable debug output')
    
    args = parser.parse_args()
    
    print("RTK GPS Status Verification")
    print("=" * 30)
    
    # Check if GPS port exists
    if not os.path.exists(args.port):
        print(f"✗ GPS port {args.port} does not exist")
        print("Available ports:")
        for port in ['/dev/ttyACM0', '/dev/ttyACM1', '/dev/ttyUSB0', '/dev/ttyUSB1']:
            if os.path.exists(port):
                print(f"  {port}")
        return
    
    # Initialize RTK checker
    rtk_checker = RTKStatusChecker(args.port, args.baud, args.debug)
    
    if not rtk_checker.connect():
        return
    
    try:
        rtk_checker.monitor_rtk_status(args.duration)
    finally:
        rtk_checker.disconnect()


if __name__ == "__main__":
    main()
