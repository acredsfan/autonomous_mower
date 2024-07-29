import subprocess
import re
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

def get_wifi_networks_to_scan():
    networks = os.getenv('Wifi_Networks_to_Scan')
    if networks and networks.lower() != 'all':
        return networks.split(',')
    else:
        return 'all'

def scan_wifi(selected_essids):
    # Run the iwlist scan command
    result = subprocess.run(['sudo', 'iwlist', 'wlan0', 'scan'], capture_output=True, text=True)
    networks = []

    # Regular expressions to match ESSID and Signal level
    essid_re = re.compile(r'ESSID:"(.+)"')
    signal_re = re.compile(r'Signal level=(-?\d+) dBm')

    lines = result.stdout.split('\n')
    for line in lines:
        essid_match = essid_re.search(line)
        signal_match = signal_re.search(line)

        if essid_match and signal_match:
            essid = essid_match.group(1)
            signal_level = int(signal_match.group(1))
            if selected_essids == 'all' or essid in selected_essids:
                networks.append({'SSID': essid, 'Signal Level (dBm)': signal_level})

    return networks

if __name__ == "__main__":
    # Get the list of ESSIDs to scan from the .env file
    selected_essids = get_wifi_networks_to_scan()

    networks = scan_wifi(selected_essids)
    for network in networks:
        print(f"SSID: {network['SSID']}, Signal Level: {network['Signal Level (dBm)']} dBm")

