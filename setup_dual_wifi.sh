#!/bin/bash

# ============================================================================
# Dual Wi-Fi Setup Script for Autonomous Mower
# ============================================================================
# This script configures dual Wi-Fi interfaces on Raspberry Pi for the
# autonomous mower project. It supports loading configuration from .env files
# and provides interactive prompts with sensible defaults.
#
# USAGE:
#   sudo ./setup_dual_wifi.sh
#
# PREREQUISITES:
#   - Raspberry Pi with Raspberry Pi OS (Bookworm recommended)
#   - Two Wi-Fi interfaces (wlan0 and wlan1) or USB Wi-Fi adapter
#   - sudo privileges
#   - Optional: .env file with configuration defaults
#
# FEATURES:
#   ✅ Loads defaults from .env file if available
#   ✅ Interactive configuration with validation
#   ✅ Dual Wi-Fi interface setup (wlan0 as fallback, wlan1 as primary)
#   ✅ Automatic failover with Python watchdog service
#   ✅ Proper network priority configuration
#   ✅ Configuration backup and recovery
#   ✅ Comprehensive error handling and logging
#   ✅ Systemd service integration
#
# CONFIGURATION (.env file support):
#   DEFAULT_SSID_MAIN="Your_Primary_WiFi_SSID"
#   DEFAULT_PASS_MAIN="Your_primary_wifi_password"
#   DEFAULT_SSID_FALLBACK="Your_Secondary_WiFi_SSID"
#   DEFAULT_PASS_FALLBACK="your_secondary_wifi_password"
#   DEFAULT_COUNTRY="US"
#   DEFAULT_GATEWAY_MAIN="192.168.1.1"
#   DEFAULT_GATEWAY_FALLBACK="192.168.50.1"
#
# To use .env configuration:
#   1. Copy .env.example to .env: cp .env.example .env
#   2. Edit the dual Wi-Fi variables in .env file
#   3. Run this script - it will use your .env values as defaults
#
# POST-INSTALLATION:
#   - System will require reboot to activate changes
#   - Wi-Fi watchdog service will start automatically
#   - Check status: sudo systemctl status wifi-watchdog
#   - View logs: sudo journalctl -u wifi-watchdog -f
#   - Manual logs: /var/log/wifi_watchdog.log
#
# TROUBLESHOOTING:
#   - Ensure both Wi-Fi interfaces exist: ip link show
#   - Check service status: sudo systemctl status wifi-watchdog
#   - Restart service: sudo systemctl restart wifi-watchdog
#   - View configuration: cat /etc/wpa_supplicant/wpa_supplicant.conf
#   - Test connectivity: ping -I wlan0 google.com
#
# AUTHOR: Autonomous Mower Project
# VERSION: 2.0
# UPDATED: May 2025
# ============================================================================

set -e  # Exit on any error

# Script directory and project root detection
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="${SCRIPT_DIR}"

# Global variable to track configuration source
CONFIG_SOURCE="hardcoded defaults"
ENV_FILE_PATH="${PROJECT_ROOT}/.env"

# Load environment variables from .env file if it exists
load_env_config() {
    if [[ -f "$ENV_FILE_PATH" ]]; then
        echo "Loading dual Wi-Fi configuration from .env file..."
        CONFIG_SOURCE=".env file ($ENV_FILE_PATH)"
        
        # Validate .env file format and load environment variables
        local loaded_vars=0
        local failed_vars=0
        
        while IFS= read -r line; do
            # Skip comments and empty lines
            [[ "$line" =~ ^[[:space:]]*# ]] && continue
            [[ -z "${line// }" ]] && continue
            
            # Export the variable if it's a valid assignment
            if [[ "$line" =~ ^[A-Za-z_][A-Za-z0-9_]*= ]]; then
                # Safely export the variable with error handling
                if export "$line" 2>/dev/null; then
                    ((loaded_vars++))
                else
                    echo "⚠ Warning: Failed to load variable: $line"
                    ((failed_vars++))
                fi
            fi
        done < <(grep -v '^[[:space:]]*#' "$ENV_FILE_PATH" | grep -v '^[[:space:]]*$')
        
        echo "✓ Environment configuration loaded ($loaded_vars variables)"
        if [[ $failed_vars -gt 0 ]]; then
            echo "⚠ Warning: $failed_vars variables failed to load from .env file"
        fi
    else
        echo "⚠ No .env file found at $ENV_FILE_PATH"
        echo "  Using hardcoded defaults. Consider creating .env file from .env.example"
        CONFIG_SOURCE="hardcoded defaults"
    fi
}

# Load configuration
load_env_config

# ============================================================================
# CONFIGURATION - Default values with .env file support
# ============================================================================
# These variables can be overridden by setting them in a .env file in the
# project root. The script will load values from .env first, then fall back
# to these defaults if not specified.
#
# .env file variables supported:
#   DEFAULT_SSID_MAIN         - Primary Wi-Fi network SSID (wlan1)
#   DEFAULT_PASS_MAIN         - Primary Wi-Fi network password
#   DEFAULT_SSID_FALLBACK     - Fallback Wi-Fi network SSID (wlan0)
#   DEFAULT_PASS_FALLBACK     - Fallback Wi-Fi network password
#   DEFAULT_COUNTRY           - Two-letter ISO country code (e.g., US, GB)
#   DEFAULT_GATEWAY_MAIN      - Gateway IP for primary Wi-Fi (wlan1)
#   DEFAULT_GATEWAY_FALLBACK  - Gateway IP for fallback Wi-Fi (wlan0)
#
# Example .env entries:
#   DEFAULT_SSID_MAIN="MyHomeWiFi"
#   DEFAULT_PASS_MAIN="mySecurePassword123"
#   DEFAULT_SSID_FALLBACK="MobileHotspot"
#   DEFAULT_PASS_FALLBACK="hotspotPassword"
#   DEFAULT_COUNTRY="US"
#   DEFAULT_GATEWAY_MAIN="192.168.1.1"
#   DEFAULT_GATEWAY_FALLBACK="192.168.50.1"
# ============================================================================

DEFAULT_SSID_MAIN="${DEFAULT_SSID_MAIN:-Your_Primary_WiFi_SSID}"
DEFAULT_PASS_MAIN="${DEFAULT_PASS_MAIN:-Your_primary_wifi_password}"
DEFAULT_SSID_FALLBACK="${DEFAULT_SSID_FALLBACK:-Your_Secondary_WiFi_SSID}"
DEFAULT_PASS_FALLBACK="${DEFAULT_PASS_FALLBACK:-your_secondary_wifi_password}"
DEFAULT_COUNTRY="${DEFAULT_COUNTRY:-US}"
DEFAULT_GATEWAY_MAIN="${DEFAULT_GATEWAY_MAIN:-192.168.50.1}"  # Main Wi-Fi gateway (for wlan1)
DEFAULT_GATEWAY_FALLBACK="${DEFAULT_GATEWAY_FALLBACK:-192.168.50.1}"  # Fallback Wi-Fi gateway (for wlan0)

# Validation functions
validate_env_config() {
    local has_meaningful_config=false
    
    # Check if any of the default values have been overridden from .env
    if [[ "$DEFAULT_SSID_MAIN" != "Your_Primary_WiFi_SSID" || 
          "$DEFAULT_SSID_FALLBACK" != "Your_Secondary_WiFi_SSID" || 
          "$DEFAULT_PASS_MAIN" != "Your_primary_wifi_password" || 
          "$DEFAULT_PASS_FALLBACK" != "your_secondary_wifi_password" ]]; then
        has_meaningful_config=true
    fi
    
    # If no meaningful configuration and no .env file exists, suggest creating one
    if [[ "$has_meaningful_config" == false && ! -f "$ENV_FILE_PATH" ]]; then
        echo ""
        echo "💡 TIP: You can pre-configure Wi-Fi settings by creating a .env file."
        echo "   Copy .env.example to .env and edit the dual Wi-Fi settings:"
        echo "   cp .env.example .env"
        echo "   # Then edit the following variables in .env:"
        echo "   # DEFAULT_SSID_MAIN=\"YourWiFiNetwork\""
        echo "   # DEFAULT_PASS_MAIN=\"YourWiFiPassword\""
        echo "   # DEFAULT_SSID_FALLBACK=\"YourBackupWiFi\""
        echo "   # DEFAULT_PASS_FALLBACK=\"YourBackupPassword\""
        echo "   # DEFAULT_COUNTRY=\"US\""
        echo "   # DEFAULT_GATEWAY_MAIN=\"192.168.1.1\""
        echo "   # DEFAULT_GATEWAY_FALLBACK=\"192.168.50.1\""
        echo ""
    elif [[ "$has_meaningful_config" == true ]]; then
        echo "✓ Using pre-configured Wi-Fi settings from .env file"
        echo ""
    fi
}

validate_ip() {
    local ip=$1
    if [[ $ip =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$ ]]; then
        IFS='.' read -ra ADDR <<< "$ip"
        for i in "${ADDR[@]}"; do
            if [[ $i -gt 255 ]]; then
                return 1
            fi
        done
        return 0
    fi
    return 1
}

validate_country_code() {
    local code=$1
    if [[ ${#code} -eq 2 && "$code" =~ ^[A-Z]{2}$ ]]; then
        return 0
    fi
    return 1
}

validate_ssid() {
    local ssid=$1
    if [[ ${#ssid} -gt 0 && ${#ssid} -le 32 ]]; then
        return 0
    fi
    return 1
}

# Display configuration summary
display_config_summary() {
    echo ""
    echo "============================================================================"
    echo "                          CONFIGURATION SUMMARY"
    echo "============================================================================"
    echo "Configuration source: ${CONFIG_SOURCE}"
    echo ""
    echo "Main Wi-Fi (wlan1 - Primary):"
    echo "  SSID: ${DEFAULT_SSID_MAIN}"
    echo "  Gateway: ${DEFAULT_GATEWAY_MAIN}"
    echo ""
    echo "Fallback Wi-Fi (wlan0 - Secondary):"
    echo "  SSID: ${DEFAULT_SSID_FALLBACK}"
    echo "  Gateway: ${DEFAULT_GATEWAY_FALLBACK}"
    echo ""
    echo "Country Code: ${DEFAULT_COUNTRY}"
    echo ""
    echo "Note: Default passwords are hidden for security."
    echo "============================================================================"
    echo ""
}

# Interactive configuration with validation
configure_wifi_settings() {
    echo "Starting Dual Wi-Fi Setup..."
    echo "You will be prompted for configuration values. Press Enter to accept the default."
    echo ""
    
    # Validate environment configuration and provide helpful tips
    validate_env_config
    
    # Display current configuration
    display_config_summary
    
    # Main Wi-Fi SSID
    while true; do
        read -p "Enter the SSID for your main Wi-Fi network [default: ${DEFAULT_SSID_MAIN}]: " SSID_MAIN
        SSID_MAIN=${SSID_MAIN:-$DEFAULT_SSID_MAIN}
        if validate_ssid "$SSID_MAIN"; then
            break
        else
            echo "⚠ Error: SSID must be 1-32 characters long. Please try again."
        fi
    done
    
    # Main Wi-Fi Password
    read -s -p "Enter the password for your main Wi-Fi network (input hidden) [default: ${DEFAULT_PASS_MAIN}]: " PASS_MAIN
    echo
    PASS_MAIN=${PASS_MAIN:-$DEFAULT_PASS_MAIN}
    
    # Fallback Wi-Fi SSID
    while true; do
        read -p "Enter the SSID for your fallback Wi-Fi network [default: ${DEFAULT_SSID_FALLBACK}]: " SSID_FALLBACK
        SSID_FALLBACK=${SSID_FALLBACK:-$DEFAULT_SSID_FALLBACK}
        if validate_ssid "$SSID_FALLBACK"; then
            break
        else
            echo "⚠ Error: SSID must be 1-32 characters long. Please try again."
        fi
    done
    
    # Fallback Wi-Fi Password
    read -s -p "Enter the password for your fallback Wi-Fi network (input hidden) [default: ${DEFAULT_PASS_FALLBACK}]: " PASS_FALLBACK
    echo
    PASS_FALLBACK=${PASS_FALLBACK:-$DEFAULT_PASS_FALLBACK}
    
    # Country Code
    while true; do
        read -p "Enter your two-letter ISO country code (e.g., US, GB) [default: ${DEFAULT_COUNTRY}]: " COUNTRY
        COUNTRY=${COUNTRY:-$DEFAULT_COUNTRY}
        COUNTRY=$(echo "$COUNTRY" | tr '[:lower:]' '[:upper:]')  # Convert to uppercase
        if validate_country_code "$COUNTRY"; then
            break
        else
            echo "⚠ Error: Country code must be exactly 2 uppercase letters (e.g., US, GB). Please try again."
        fi
    done
    
    # Main Gateway IP
    while true; do
        read -p "Enter the gateway IP for your main Wi-Fi (wlan1) [default: ${DEFAULT_GATEWAY_MAIN}]: " GATEWAY_MAIN
        GATEWAY_MAIN=${GATEWAY_MAIN:-$DEFAULT_GATEWAY_MAIN}
        if validate_ip "$GATEWAY_MAIN"; then
            break
        else
            echo "⚠ Error: Please enter a valid IP address (e.g., 192.168.1.1). Please try again."
        fi
    done
    
    # Fallback Gateway IP
    while true; do
        read -p "Enter the gateway IP for your fallback Wi-Fi (wlan0) [default: ${DEFAULT_GATEWAY_FALLBACK}]: " GATEWAY_FALLBACK
        GATEWAY_FALLBACK=${GATEWAY_FALLBACK:-$DEFAULT_GATEWAY_FALLBACK}
        if validate_ip "$GATEWAY_FALLBACK"; then
            break
        else
            echo "⚠ Error: Please enter a valid IP address (e.g., 192.168.1.1). Please try again."
        fi
    done
    
    echo ""  # Add blank line for readability
}

# Execute configuration
configure_wifi_settings

# ============================================================================
# Wi-Fi Configuration Implementation
# ============================================================================

# Error handling function
handle_error() {
    local exit_code=$1
    local line_number=$2
    echo "❌ Error: Command failed with exit code $exit_code at line $line_number"
    echo "Please check the error above and try again."
    exit $exit_code
}

# Set up error trapping
trap 'handle_error $? $LINENO' ERR

# Confirmation prompt
confirm_configuration() {
    echo "============================================================================"
    echo "                      FINAL CONFIGURATION REVIEW"
    echo "============================================================================"
    echo "Main Wi-Fi (Primary - wlan1):"
    echo "  SSID: $SSID_MAIN"
    echo "  Gateway: $GATEWAY_MAIN"
    echo "  Priority: 2 (Higher)"
    echo ""
    echo "Fallback Wi-Fi (Secondary - wlan0):"
    echo "  SSID: $SSID_FALLBACK"
    echo "  Gateway: $GATEWAY_FALLBACK"
    echo "  Priority: 1 (Lower)"
    echo ""
    echo "Country: $COUNTRY"
    echo "============================================================================"
    echo ""
    read -p "Proceed with this configuration? (y/N): " confirm
    if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
        echo "Configuration cancelled by user."
        exit 0
    fi
}

# Backup existing configuration
backup_existing_config() {
    echo "🔄 Creating backup of existing configuration..."
    local backup_dir="/tmp/wifi_backup_$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$backup_dir"
    
    if [[ -f /etc/wpa_supplicant/wpa_supplicant.conf ]]; then
        sudo cp /etc/wpa_supplicant/wpa_supplicant.conf "$backup_dir/"
        echo "✓ Backed up wpa_supplicant.conf to $backup_dir"
    fi
    
    if [[ -f /etc/dhcpcd.conf ]]; then
        sudo cp /etc/dhcpcd.conf "$backup_dir/"
        echo "✓ Backed up dhcpcd.conf to $backup_dir"
    fi
    
    echo "ℹ Backup location: $backup_dir"
}

# Validate system requirements
check_system_requirements() {
    echo "🔍 Checking system requirements..."
    
    # Check if running as root or with sudo
    if [[ $EUID -eq 0 ]]; then
        echo "⚠ Warning: Running as root. This script should be run with sudo, not as root user."
    fi
    
    # Check if Wi-Fi interfaces exist
    if ! ip link show wlan0 &>/dev/null; then
        echo "❌ Error: wlan0 interface not found. Please ensure Wi-Fi hardware is connected."
        exit 1
    fi
    
    if ! ip link show wlan1 &>/dev/null; then
        echo "⚠ Warning: wlan1 interface not found. Dual Wi-Fi setup requires two Wi-Fi interfaces."
        echo "This setup will work with single interface fallback, but dual interface features will be limited."
    fi
    
    echo "✓ System requirements validated"
}

# Main configuration execution
main_configuration() {
    confirm_configuration
    check_system_requirements
    backup_existing_config
    
    # 1. Set global wpa_supplicant config with multiple networks
    echo "🔧 Creating global wpa_supplicant.conf..."
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
    echo "✓ wpa_supplicant.conf created successfully"

    # 2. Cleanup dhcpcd.conf to avoid conflicts
    echo "🔧 Cleaning up dhcpcd.conf..."
    sudo sed -i '/denyinterfaces wlan0/d' /etc/dhcpcd.conf || true
    sudo sed -i '/denyinterfaces wlan1/d' /etc/dhcpcd.conf || true
    echo "✓ dhcpcd.conf cleaned up"

    # 3. Restart networking to apply changes
    echo "🔄 Restarting networking services..."
    sudo systemctl restart dhcpcd || echo "⚠ Warning: Failed to restart dhcpcd"
    sudo wpa_cli -i wlan0 reconfigure &>/dev/null || echo "ℹ wlan0 reconfigure: interface may not be ready"
    sudo wpa_cli -i wlan1 reconfigure &>/dev/null || echo "ℹ wlan1 reconfigure: interface may not be ready"    echo "✓ Networking services restarted"

    # 4. Create the Wi-Fi watchdog script for failover
    echo "🔧 Creating Wi-Fi watchdog script..."
    sudo tee /usr/local/bin/wifi_watchdog.py > /dev/null <<EOF
#!/usr/bin/env python3
"""
Wi-Fi Failover Watchdog for Autonomous Mower

This script monitors the primary Wi-Fi connection and automatically
switches to the fallback connection if the primary fails.
It follows the autonomous mower project's coding standards.
"""
import subprocess
import time
import logging
import sys
from pathlib import Path

# Configuration
PRIMARY_IFACE = "wlan1"
SECONDARY_IFACE = "wlan0"
PRIMARY_GATEWAY = "$GATEWAY_MAIN"
SECONDARY_GATEWAY = "$GATEWAY_FALLBACK"
PING_HOST = PRIMARY_GATEWAY
FAIL_THRESHOLD = 3
PING_INTERVAL = 5
LOG_FILE = "/var/log/wifi_watchdog.log"

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


def ping(host, iface):
    """
    Ping a host through a specific interface.
    
    Args:
        host (str): Host to ping
        iface (str): Network interface to use
        
    Returns:
        bool: True if ping successful, False otherwise
    """
    try:
        subprocess.check_output(
            ["ping", "-I", iface, "-c", "1", "-W", "2", host],
            stderr=subprocess.DEVNULL
        )
        return True
    except subprocess.CalledProcessError:
        return False
    except Exception as e:
        logger.error(f"Unexpected error during ping: {e}")
        return False


def set_default_route(primary=True):
    """
    Set the default network route.
    
    Args:
        primary (bool): True to use primary interface, False for secondary
    """
    try:
        # Remove existing default routes
        subprocess.call(["ip", "route", "del", "default"], 
                       stderr=subprocess.DEVNULL)
        
        if primary:
            subprocess.call([
                "ip", "route", "add", "default", "via", PRIMARY_GATEWAY, 
                "dev", PRIMARY_IFACE, "metric", "100"
            ])
            subprocess.call([
                "ip", "route", "add", "default", "via", SECONDARY_GATEWAY, 
                "dev", SECONDARY_IFACE, "metric", "200"
            ])
            logger.info(f"Switched to primary interface ({PRIMARY_IFACE})")
        else:
            subprocess.call([
                "ip", "route", "add", "default", "via", SECONDARY_GATEWAY, 
                "dev", SECONDARY_IFACE, "metric", "100"
            ])
            subprocess.call([
                "ip", "route", "add", "default", "via", PRIMARY_GATEWAY, 
                "dev", PRIMARY_IFACE, "metric", "200"
            ])
            logger.info(f"Switched to fallback interface ({SECONDARY_IFACE})")
            
    except Exception as e:
        logger.error(f"Error setting default route: {e}")


def main():
    """Main watchdog loop."""
    logger.info("Wi-Fi Watchdog started")
    logger.info(f"Primary: {PRIMARY_IFACE} ({PRIMARY_GATEWAY})")
    logger.info(f"Secondary: {SECONDARY_IFACE} ({SECONDARY_GATEWAY})")
    
    fail_count = 0
    primary_active = True
    
    while True:
        try:
            if ping(PING_HOST, PRIMARY_IFACE):
                if not primary_active:
                    set_default_route(primary=True)
                    primary_active = True
                fail_count = 0
            else:
                fail_count += 1
                logger.warning(f"Primary interface ping failed ({fail_count}/{FAIL_THRESHOLD})")
                
                if fail_count >= FAIL_THRESHOLD and primary_active:
                    logger.error("Primary interface failed, switching to fallback")
                    set_default_route(primary=False)
                    primary_active = False
                    
            time.sleep(PING_INTERVAL)
            
        except KeyboardInterrupt:
            logger.info("Wi-Fi Watchdog stopped by user")
            break
        except Exception as e:
            logger.error(f"Unexpected error in watchdog loop: {e}")
            time.sleep(PING_INTERVAL)


if __name__ == "__main__":
    main()
EOF

    sudo chmod +x /usr/local/bin/wifi_watchdog.py
    echo "✓ Wi-Fi watchdog script created"

    # 5. Set up systemd service for the watchdog
    echo "🔧 Setting up watchdog systemd service..."
    sudo tee /etc/systemd/system/wifi-watchdog.service > /dev/null <<EOF
[Unit]
Description=Wi-Fi Failover Watchdog for Autonomous Mower
After=network-online.target
Wants=network-online.target
Documentation=https://github.com/username/autonomous_mower

[Service]
Type=simple
ExecStart=/usr/local/bin/wifi_watchdog.py
Restart=always
RestartSec=5
User=root
StandardOutput=journal
StandardError=journal

# Security settings
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/log

[Install]
WantedBy=multi-user.target
EOF

    sudo systemctl daemon-reload
    sudo systemctl enable wifi-watchdog.service
    echo "✓ Wi-Fi watchdog service configured and enabled"
}

# Final completion and reboot prompt
complete_setup() {
    echo ""
    echo "============================================================================"
    echo "                         SETUP COMPLETED SUCCESSFULLY!"
    echo "============================================================================"
    echo "✅ Dual Wi-Fi configuration has been set up with the following features:"
    echo ""
    echo "🔹 Primary Wi-Fi (wlan1): $SSID_MAIN"
    echo "🔹 Fallback Wi-Fi (wlan0): $SSID_FALLBACK"
    echo "🔹 Automatic failover with watchdog service"
    echo "🔹 Configuration backup created"
    echo "🔹 Systemd service enabled for automatic startup"
    echo ""
    echo "ℹ️  The system needs to be rebooted to apply all changes."
    echo "ℹ️  After reboot, the Wi-Fi watchdog will automatically start."
    echo "ℹ️  You can check the watchdog status with: sudo systemctl status wifi-watchdog"
    echo "ℹ️  View logs with: sudo journalctl -u wifi-watchdog -f"
    echo "============================================================================"
    echo ""
    
    read -p "🔄 Reboot now to apply changes? (y/N): " REBOOT_NOW
    if [[ "$REBOOT_NOW" =~ ^[Yy]$ ]]; then
        echo "🔄 Rebooting system..."
        sleep 2
        sudo reboot
    else
        echo "⚠️  Please reboot manually when ready to activate the dual Wi-Fi configuration."
        echo "💡 Run 'sudo reboot' to apply all changes."
    fi
}

# ============================================================================
# MAIN EXECUTION
# ============================================================================

# Execute main configuration
main_configuration

# Complete setup
complete_setup

echo "🎉 Dual Wi-Fi setup script completed successfully!"
echo "📋 For troubleshooting, check logs at: /var/log/wifi_watchdog.log"
