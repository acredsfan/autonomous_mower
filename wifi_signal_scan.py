import subprocess
import re
from dotenv import load_dotenv, find_dotenv
import os
import csv

# Load environment variables from .env file
load_dotenv(find_dotenv())

def get_wifi_networks_to_scan():
    networks = os.getenv('Wifi_Networks_to_Scan')
    if networks and networks.lower() != 'all':
        # Split the networks string by commas, strip surrounding quotes and spaces
        return [network.strip().strip('"') for network in networks.split('","')]
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

def write_to_csv(networks, filename='wifi_scan_results.csv'):
    # Define the CSV file headers
    headers = ['SSID', 'Signal Level (dBm)']

    # Write the results to a CSV file
    with open(filename, mode='w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=headers)
        writer.writeheader()
        for network in networks:
            writer.writerow(network)

if __name__ == "__main__":
    # Get the list of ESSIDs to scan from the .env file
    selected_essids = get_wifi_networks_to_scan()

    # Scan the WiFi networks
    networks = scan_wifi(selected_essids)

    # Print the results to the console
    for network in networks:
        print(f"SSID: {network['SSID']}, Signal Level: {network['Signal Level (dBm)']} dBm")

    # Write the results to a CSV file
    write_to_csv(networks)

