import subprocess
import re
from dotenv import load_dotenv, find_dotenv
import os
import csv
import math
import time
from navigation_system.gps import GpsPosition
from donkeycar.parts.serial_port import SerialPort

# Load environment variables from .env file
load_dotenv(find_dotenv())

def get_wifi_networks_to_scan():
    networks = os.getenv("Wifi_Networks_to_Scan")
    if networks:
        print(f"Raw Wifi_Networks_to_Scan: {networks}")
        if networks.lower() != "all":
            # Split by comma, handle spaces and quotes, and remove empty strings
            return [network.strip().strip('"') for network in networks.split(",") if network.strip()]
        else:
            return "all"
    else:
        print("Wifi_Networks_to_Scan not found or empty in the .env file.")
        return None

def get_current_connection():
    essid_result = subprocess.run(["iwgetid", "-r"], capture_output=True, text=True)
    bssid_result = subprocess.run(["iwconfig", "wlan0"], capture_output=True, text=True)
    
    essid_re = re.compile(r'(.+)')
    bssid_re = re.compile(r'Access Point: ([0-9A-Fa-f:]{17})')

    current_essid = essid_result.stdout.strip()
    current_bssid = None

    for line in bssid_result.stdout.split('\n'):
        bssid_match = bssid_re.search(line)
        if bssid_match:
            current_bssid = bssid_match.group(1).strip()

    # Debug prints to verify current connection details
    print(f"Current ESSID: {current_essid}")
    print(f"Current BSSID: {current_bssid}")

    return current_essid, current_bssid

def scan_wifi(selected_essids):
    result = subprocess.run(["sudo", "iwlist", "wlan0", "scan"], capture_output=True, text=True)
    networks = []

    essid_re = re.compile(r'ESSID:"(.+)"')
    signal_re = re.compile(r'Signal level=(-?\d+) dBm')
    channel_re = re.compile(r'Channel:(\d+)')
    frequency_re = re.compile(r'Frequency:(\d+\.?\d*) GHz')  # Match frequency with decimal
    signal_quality_re = re.compile(r'Quality=(\d+/\d+)')
    bssid_re = re.compile(r'Address: ([0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2})')

    if result.returncode != 0:
        print(f"Error running iwlist: {result.stderr}")
        return networks
    else:
        print(f"Successfully ran iwlist.")

    current_network = {}
    for line in result.stdout.split('\n'):
        essid_match = essid_re.search(line)
        signal_match = signal_re.search(line)
        channel_match = channel_re.search(line)
        frequency_match = frequency_re.search(line)
        signal_quality_match = signal_quality_re.search(line)
        bssid_match = bssid_re.search(line)

        if essid_match:
            current_network['SSID'] = essid_match.group(1).strip()

        if signal_match:
            current_network['Signal Level'] = int(signal_match.group(1))

        if channel_match:
            current_network['Channel'] = int(channel_match.group(1))
            
        if frequency_match:
            current_network['Frequency'] = float(frequency_match.group(1))  # Store as float

        if signal_quality_match:
            current_network['Signal Quality'] = signal_quality_match.group(1)
        
        if bssid_match:
            current_network['BSSID'] = bssid_match.group(1)

        if current_network.get('SSID') and current_network.get('Signal Level'):
            if selected_essids == 'all' or current_network['SSID'] in selected_essids:
                networks.append(current_network)
            current_network = {}

    # Print ESSID of filtered networks removing duplicate names
    print(f"Filtered networks: {set([network['SSID'] for network in networks])}")
    return networks

def write_to_csv(networks, current_essid, current_bssid, gps_position, filename='wifi_scan_results.csv'):
    if not networks:
        print("No networks to write to CSV.")
        return

    # Define the order of the fields
    field_order = ['SSID', 'BSSID', 'Frequency', 'Channel', 'Signal Quality', 'Signal Level', 'Connected', 'Latitude', 'Longitude', 'UTM Easting', 'UTM Northing']

    # Add the 'Connected' field to each network
    for network in networks:
        if network['SSID'] == current_essid and network['BSSID'] == current_bssid:
            network['Connected'] = 'Yes'
        else:
            network['Connected'] = 'No'

        # Fetch current GPS position
        timestamp, utm_easting, utm_northing, latitude, longitude = get_current_gps_position(gps_position)
        if utm_easting and utm_northing:
            network['Latitude'] = latitude
            network['Longitude'] = longitude
            network['UTM Easting'] = utm_easting
            network['UTM Northing'] = utm_northing

    # Load existing data if the file exists
    existing_data = []
    if os.path.exists(filename):
        with open(filename, mode='r') as file:
            reader = csv.DictReader(file)
            existing_data = list(reader)

    # Update or append new data
    for network in networks:
        updated = False
        for i, existing_network in enumerate(existing_data):
            distance = math.sqrt((float(network['UTM Easting']) - float(existing_network['UTM Easting']))**2 + 
                                 (float(network['UTM Northing']) - float(existing_network['UTM Northing']))**2)
            if distance < 3.0:
                existing_data[i] = network
                updated = True
                break
        if not updated:
            existing_data.append(network)

    # Write updated data to CSV
    with open(filename, mode='w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=field_order)
        writer.writeheader()
        writer.writerows(existing_data)

    print(f"Results written to {filename}")

def get_current_gps_position(gps_position):
    position = gps_position.run()
    if position:
        timestamp, utm_easting, utm_northing, latitude, longitude = position
        return timestamp, utm_easting, utm_northing, latitude, longitude
    return None, None, None, None

if __name__ == "__main__":
    selected_essids = get_wifi_networks_to_scan()

    if selected_essids:
        current_essid, current_bssid = get_current_connection()
        
        # Initialize GPS Position
        serial_port = SerialPort(os.getenv('GPS_SERIAL_PORT'), baudrate=115200, timeout=0.5)
        gps_position = GpsPosition(serial_port, os.getenv('POINTPERFECT_USER'), os.getenv('POINTPERFECT_PASS'), os.getenv('POINTPERFECT_URL'), os.getenv('POINTPERFECT_MOUNTPOINT'), debug=True)
        
        try:
            while True:
                networks = scan_wifi(selected_essids)
                write_to_csv(networks, current_essid, current_bssid, gps_position)
                time.sleep(10)  # Adjust the sleep time as needed
        except KeyboardInterrupt:
            print("Terminating...")
        finally:
            gps_position.shutdown()
    else:
        print("No valid WiFi networks to scan. Please check the .env file.")