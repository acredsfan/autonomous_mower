#!/bin/bash

# CONFIGURATION
DEFAULT_SSID_MAIN="Your_Primary_WiFi_SSID"
DEFAULT_PASS_MAIN="Your_primary_wifi_password"
DEFAULT_SSID_FALLBACK="Your_Secondary_WiFi_SSID"
DEFAULT_PASS_FALLBACK="your_secondary_wifi_password"
DEFAULT_COUNTRY="US"
DEFAULT_GATEWAY_MAIN="192.168.50.1" # Main Wi-Fi gateway (for wlan1)
DEFAULT_GATEWAY_FALLBACK="192.168.50.1" # Fallback Wi-Fi gateway (for wlan0)

echo "Starting Dual Wi-Fi Setup..."
echo "You will be prompted for configuration values. Press Enter to accept the default."

read -p "Enter the SSID for your main Wi-Fi network (e.g., MyHomeWiFi) [default: ${DEFAULT_SSID_MAIN}]: " SSID_MAIN
SSID_MAIN=${SSID_MAIN:-$DEFAULT_SSID_MAIN}
read -s -p "Enter the password for your main Wi-Fi network (input will be hidden) [default: ${DEFAULT_PASS_MAIN}]: " PASS_MAIN
echo
PASS_MAIN=${PASS_MAIN:-$DEFAULT_PASS_MAIN}
read -p "Enter the SSID for your fallback Wi-Fi network (e.g., MyGuestWiFi) [default: ${DEFAULT_SSID_FALLBACK}]: " SSID_FALLBACK
SSID_FALLBACK=${SSID_FALLBACK:-$DEFAULT_SSID_FALLBACK}
read -s -p "Enter the password for your fallback Wi-Fi network (input will be hidden) [default: ${DEFAULT_PASS_FALLBACK}]: " PASS_FALLBACK
echo
PASS_FALLBACK=${PASS_FALLBACK:-$DEFAULT_PASS_FALLBACK}
read -p "Enter your two-letter ISO country code (e.g., US, GB) [default: ${DEFAULT_COUNTRY}]: " COUNTRY
COUNTRY=${COUNTRY:-$DEFAULT_COUNTRY}
read -p "Enter the gateway IP for your main Wi-Fi (wlan1) [default: ${DEFAULT_GATEWAY_MAIN}]: " GATEWAY_MAIN
GATEWAY_MAIN=${GATEWAY_MAIN:-$DEFAULT_GATEWAY_MAIN}
read -p "Enter the gateway IP for your fallback Wi-Fi (wlan0) [default: ${DEFAULT_GATEWAY_FALLBACK}]: " GATEWAY_FALLBACK
GATEWAY_FALLBACK=${GATEWAY_FALLBACK:-$DEFAULT_GATEWAY_FALLBACK}

echo # Add a blank line for readability

# 1. Set global wpa_supplicant config with multiple networks
echo "Creating global wpa_supplicant.conf..."
sudo tee /etc/wpa_supplicant/wpa_supplicant.conf > /dev/null <<EOF
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1
country=$COUNTRY

network={
    ssid="$SSID_MAIN"
    psk="$PASS_MAIN"
    priority=2
}

network={
    ssid="$SSID_FALLBACK"
    psk="$PASS_FALLBACK"
    priority=1
}
EOF

# 2. Cleanup dhcpcd.conf to avoid conflicts
echo "Cleaning up dhcpcd.conf..."
sudo sed -i '/denyinterfaces wlan0/d' /etc/dhcpcd.conf
sudo sed -i '/denyinterfaces wlan1/d' /etc/dhcpcd.conf

# 3. Restart networking to apply changes
echo "Restarting networking services..."
sudo systemctl restart dhcpcd
sudo wpa_cli -i wlan0 reconfigure || true
sudo wpa_cli -i wlan1 reconfigure || true

# 4. Create the Wi-Fi watchdog script for failover
echo "Creating watchdog script..."
sudo tee /usr/local/bin/wifi_watchdog.py > /dev/null <<EOF
#!/usr/bin/env python3
import subprocess
import time

PRIMARY_IFACE = "wlan1"
SECONDARY_IFACE = "wlan0"
PRIMARY_GATEWAY = "$GATEWAY_MAIN"
SECONDARY_GATEWAY = "$GATEWAY_FALLBACK"
PING_HOST = PRIMARY_GATEWAY
FAIL_THRESHOLD = 3
PING_INTERVAL = 5

def ping(host, iface):
    try:
        subprocess.check_output(
            ["ping", "-I", iface, "-c", "1", "-W", "2", host],
            stderr=subprocess.DEVNULL
        )
        return True
    except subprocess.CalledProcessError:
        return False

def set_default_route(primary=True):
    subprocess.call(["ip", "route", "del", "default"])
    if primary:
        subprocess.call(["ip", "route", "add", "default", "via", PRIMARY_GATEWAY, "dev", PRIMARY_IFACE, "metric", "100"])
        subprocess.call(["ip", "route", "add", "default", "via", SECONDARY_GATEWAY, "dev", SECONDARY_IFACE, "metric", "200"])
    else:
        subprocess.call(["ip", "route", "add", "default", "via", SECONDARY_GATEWAY, "dev", SECONDARY_IFACE, "metric", "100"])
        subprocess.call(["ip", "route", "add", "default", "via", PRIMARY_GATEWAY, "dev", PRIMARY_IFACE, "metric", "200"])

fail_count = 0
primary_active = True

while True:
    if ping(PING_HOST, PRIMARY_IFACE):
        if not primary_active:
            set_default_route(primary=True)
            primary_active = True
        fail_count = 0
    else:
        fail_count += 1
        if fail_count >= FAIL_THRESHOLD and primary_active:
            set_default_route(primary=False)
            primary_active = False
    time.sleep(PING_INTERVAL)
EOF

sudo chmod +x /usr/local/bin/wifi_watchdog.py

# 5. Set up systemd service for the watchdog
echo "Setting up watchdog service..."
sudo tee /etc/systemd/system/wifi-watchdog.service > /dev/null <<EOF
[Unit]
Description=Wi-Fi Failover Watchdog
After=network-online.target
Wants=network-online.target

[Service]
ExecStart=/usr/local/bin/wifi_watchdog.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable wifi-watchdog.service

# 6. Done
echo "Setup complete! Reboot to apply changes. Reboot now? (y/n)"
read REBOOT_NOW
if [[ "\$REBOOT_NOW" == "y" || "\$REBOOT_NOW" == "Y" ]]; then
    echo "Rebooting..."
    sudo reboot
else
    echo "Please reboot manually when ready."
fi

echo "Dual Wi-Fi setup script completed."
