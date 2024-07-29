import subprocess
import re
from dotenv import load_dotenv, find_dotenv
import os
import csv

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
        print(result.stdout)

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
            current_network['Signal Level (dBm)'] = int(signal_match.group(1))

        if channel_match:
            current_network['Channel'] = int(channel_match.group(1))
            
        if frequency_match:
            current_network['Frequency (GHz)'] = float(frequency_match.group(1))  # Store as float

        if signal_quality_match:
            current_network['Signal Quality'] = signal_quality_match.group(1)
        
        if bssid_match:
            current_network['BSSID'] = bssid_match.group(1)

        if current_network.get('SSID') and current_network.get('Signal Level (dBm)'):
            if selected_essids == 'all' or current_network['SSID'] in selected_essids:
                networks.append(current_network)
            current_network = {}

    print(f"Filtered networks: {networks}")
    return networks


def write_to_csv(networks, filename='wifi_scan_results.csv'):
    if not networks:
        print("No networks to write to CSV.")
        return

    # Ensure all networks have the same keys
    all_keys = set().union(*(network.keys() for network in networks))
    for network in networks:
        for key in all_keys:
            network.setdefault(key, None)

    with open(filename, mode='w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=all_keys)  # Use all keys as headers
        writer.writeheader()
        writer.writerows(networks)

    print(f"Results written to {filename}")


if __name__ == "__main__":
    selected_essids = get_wifi_networks_to_scan()

    if selected_essids:
        networks = scan_wifi(selected_essids)
        write_to_csv(networks)
    else:
        print("No valid WiFi networks to scan. Please check the .env file.")