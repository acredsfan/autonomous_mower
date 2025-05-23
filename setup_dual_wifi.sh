#!/bin/bash

# CONFIGURATION
SSID_FAST="Your_Primary_WiFi_SSID"
PASS_FAST="Your_primary_wifi_password"
SSID_SLOW="Your_Secondary_WiFi_SSID"
PASS_SLOW="your_secondary_wifi_password"
COUNTRY="US"
GATEWAY_FAST="192.168.50.1" # Replace with your primary Wi-Fi gateway
GATEWAY_SLOW="192.168.60.1" # Replace with your secondary Wi-Fi gateway

echo "Setting up dual Wi-Fi configuration..."

# 1. Set country code
echo "Setting regulatory domain..."
echo "country=$COUNTRY" | sudo tee /etc/wpa_supplicant/wpa_supplicant.conf > /dev/null

# 2. Write WPA configs
echo "Creating wpa_supplicant configs..."
sudo tee /etc/wpa_supplicant/wpa_supplicant-wlan0.conf > /dev/null <<EOF
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1
country=$COUNTRY

network={
    ssid="$SSID_SLOW"
    psk="$PASS_SLOW"
}
EOF

sudo tee /etc/wpa_supplicant/wpa_supplicant-wlan1.conf > /dev/null <<EOF
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1
country=$COUNTRY

network={
    ssid="$SSID_FAST"
    psk="$PASS_FAST"
}
EOF

# 3. Configure interfaces
echo "Configuring interfaces..."
sudo mkdir -p /etc/network/interfaces.d

sudo tee /etc/network/interfaces.d/wlan0 > /dev/null <<EOF
auto wlan0
iface wlan0 inet dhcp
    wpa-conf /etc/wpa_supplicant/wpa_supplicant-wlan0.conf
EOF

sudo tee /etc/network/interfaces.d/wlan1 > /dev/null <<EOF
auto wlan1
iface wlan1 inet dhcp
    wpa-conf /etc/wpa_supplicant/wpa_supplicant-wlan1.conf
EOF

# 4. Update dhcpcd.conf to stop interference
echo "Updating dhcpcd config..."
sudo sed -i '/denyinterfaces wlan/d' /etc/dhcpcd.conf
echo "denyinterfaces wlan0" | sudo tee -a /etc/dhcpcd.conf > /dev/null
echo "denyinterfaces wlan1" | sudo tee -a /etc/dhcpcd.conf > /dev/null

# 5. Install watchdog script
echo "Creating watchdog script..."
sudo tee /usr/local/bin/wifi_watchdog.py > /dev/null <<EOF
#!/usr/bin/env python3
import subprocess
import time

WLAN1_GATEWAY = "$GATEWAY_FAST"
WLAN0_GATEWAY = "$GATEWAY_SLOW"
PING_INTERFACE = "wlan1"
FALLBACK_INTERFACE = "wlan0"
PING_HOST = WLAN1_GATEWAY
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

def set_route(primary=True):
    subprocess.call(["ip", "route", "del", "default"])
    if primary:
        subprocess.call(["ip", "route", "add", "default", "via", WLAN1_GATEWAY, "dev", PING_INTERFACE, "metric", "100"])
        subprocess.call(["ip", "route", "add", "default", "via", WLAN0_GATEWAY, "dev", FALLBACK_INTERFACE, "metric", "200"])
    else:
        subprocess.call(["ip", "route", "add", "default", "via", WLAN0_GATEWAY, "dev", FALLBACK_INTERFACE, "metric", "100"])
        subprocess.call(["ip", "route", "add", "default", "via", WLAN1_GATEWAY, "dev", PING_INTERFACE, "metric", "200"])

fail_count = 0
primary_active = True

while True:
    if ping(PING_HOST, PING_INTERFACE):
        if not primary_active:
            set_route(primary=True)
            primary_active = True
        fail_count = 0
    else:
        fail_count += 1
        if fail_count >= FAIL_THRESHOLD and primary_active:
            set_route(primary=False)
            primary_active = False
    time.sleep(PING_INTERVAL)
EOF

sudo chmod +x /usr/local/bin/wifi_watchdog.py

# 6. Create systemd service
echo "Setting up systemd service..."
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

# 7. Enable service
echo "Enabling watchdog..."
sudo systemctl daemon-reexec
sudo systemctl enable wifi-watchdog.service

# 8. Done!
echo "Setup complete. Reboot Now? (y/n)"
read REBOOT_NOW
if [[ "$REBOOT_NOW" == "y" || "$REBOOT_NOW" == "Y" ]]; then
    echo "Rebooting..."
    sudo reboot
else
    echo "Please reboot your system to apply changes."
fi
echo "Dual Wi-Fi setup script completed."