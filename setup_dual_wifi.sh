#!/bin/bash

# ============================================================================
# Dual Wi-Fi Setup Script for Autonomous Mower - NetworkManager Compatible
# ============================================================================
#
# This script sets up dual Wi-Fi interfaces (wlan0 and wlan1) with automatic
# failover capability. It supports both NetworkManager (modern Pi OS) and
# dhcpcd (legacy Pi OS) network management systems.
#
# Compatible with: Raspberry Pi OS Bookworm+ (NetworkManager) and older (dhcpcd)
# Hardware: Raspberry Pi 4B/5 with dual Wi-Fi capability
# Project: autonomous_mower
#
# Usage: sudo ./setup_dual_wifi_networkmanager.sh
#
# Author: Autonomous Mower Project
# License: Project License
# ============================================================================

set -euo pipefail  # Exit on error, undefined vars, pipe failures

# Global configuration tracking
CONFIG_SOURCE="defaults"
ENV_FILE_PATH=""
ENV_LOAD_FAILURES=0
NETWORK_MANAGER=""

# Default configuration values (will be overridden by .env if available)
DEFAULT_SSID_MAIN="YourMainWiFi"
DEFAULT_PASS_MAIN="YourMainPassword"
DEFAULT_SSID_FALLBACK="YourFallbackWiFi"
DEFAULT_PASS_FALLBACK="YourFallbackPassword"
DEFAULT_COUNTRY="US"
DEFAULT_GATEWAY_MAIN="192.168.1.1"
DEFAULT_GATEWAY_FALLBACK="192.168.4.1"

# Configuration variables to be set during setup
SSID_MAIN=""
PASS_MAIN=""
SSID_FALLBACK=""
PASS_FALLBACK=""
COUNTRY=""
GATEWAY_MAIN=""
GATEWAY_FALLBACK=""

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

# Enhanced logging with timestamps
log_info() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') [INFO] $1"
}

log_warn() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') [WARN] $1" >&2
}

log_error() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') [ERROR] $1" >&2
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# ============================================================================
# NETWORK MANAGER DETECTION
# ============================================================================

detect_network_manager() {
    log_info "Detecting network manager..."

    if systemctl is-active --quiet NetworkManager 2>/dev/null; then
        NETWORK_MANAGER="networkmanager"
        log_info "✓ NetworkManager detected and active"
    elif systemctl is-active --quiet dhcpcd 2>/dev/null; then
        NETWORK_MANAGER="dhcpcd"
        log_info "✓ dhcpcd detected and active"
    elif systemctl list-units --type=service | grep -q NetworkManager; then
        NETWORK_MANAGER="networkmanager"
        log_warn "NetworkManager installed but not active, will attempt to use it"
    elif systemctl list-units --type=service | grep -q dhcpcd; then
        NETWORK_MANAGER="dhcpcd"
        log_warn "dhcpcd installed but not active, will attempt to use it"
    else
        log_error "❌ Could not detect NetworkManager or dhcpcd"
        log_error "This script requires either NetworkManager or dhcpcd for network management"
        exit 1
    fi

    log_info "Using network manager: $NETWORK_MANAGER"
}

# ============================================================================
# ENVIRONMENT CONFIGURATION LOADING
# ============================================================================

load_env_config() {
    local env_files=(".env" ".env.local" ".env.example")
    local loaded=false

    log_info "Loading environment configuration..."

    for env_file in "${env_files[@]}"; do
        if [[ -f "$env_file" ]]; then
            log_info "Found environment file: $env_file"
            ENV_FILE_PATH="$env_file"

            # Load and count valid Wi-Fi variables
            local wifi_var_count=0
            while IFS='=' read -r key value; do
                # Skip comments and empty lines
                [[ $key =~ ^[[:space:]]*# ]] && continue
                [[ -z "$key" ]] && continue

                # Remove leading/trailing whitespace and quotes
                key=$(echo "$key" | xargs)
                value=$(echo "$value" | xargs | sed 's/^["'\'']\|["'\'']$//g')

                # Load dual Wi-Fi specific variables
                case "$key" in
                    DUAL_WIFI_SSID_MAIN) DEFAULT_SSID_MAIN="$value"; ((wifi_var_count++)) ;;
                    DUAL_WIFI_PASS_MAIN) DEFAULT_PASS_MAIN="$value"; ((wifi_var_count++)) ;;
                    DUAL_WIFI_SSID_FALLBACK) DEFAULT_SSID_FALLBACK="$value"; ((wifi_var_count++)) ;;
                    DUAL_WIFI_PASS_FALLBACK) DEFAULT_PASS_FALLBACK="$value"; ((wifi_var_count++)) ;;
                    DUAL_WIFI_COUNTRY) DEFAULT_COUNTRY="$value"; ((wifi_var_count++)) ;;
                    DUAL_WIFI_GATEWAY_MAIN) DEFAULT_GATEWAY_MAIN="$value"; ((wifi_var_count++)) ;;
                    DUAL_WIFI_GATEWAY_FALLBACK) DEFAULT_GATEWAY_FALLBACK="$value"; ((wifi_var_count++)) ;;
                esac
            done < "$env_file"

            if [[ $wifi_var_count -gt 0 ]]; then
                CONFIG_SOURCE="$env_file ($wifi_var_count variables loaded)"
                loaded=true
                log_info "✓ Loaded $wifi_var_count dual Wi-Fi variables from $env_file"
                break
            else
                log_warn "⚠ $env_file found but contains no dual Wi-Fi variables"
                ((ENV_LOAD_FAILURES++))
            fi
        fi
    done

    if [[ "$loaded" != true ]]; then
        CONFIG_SOURCE="built-in defaults (no .env file found)"
        log_warn "⚠ No .env file with dual Wi-Fi configuration found, using defaults"
        ((ENV_LOAD_FAILURES++))
    fi
}

# ============================================================================
# VALIDATION FUNCTIONS
# ============================================================================

validate_ip() {
    local ip=$1
    if [[ $ip =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$ ]]; then
        local IFS='.'
        local -a octets=($ip)
        for octet in "${octets[@]}"; do
            if ((octet > 255)); then
                return 1
            fi
        done
        return 0
    fi
    return 1
}

validate_country_code() {
    local country=$1
    if [[ ${#country} -eq 2 && $country =~ ^[A-Z]{2}$ ]]; then
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

# ============================================================================
# CONFIGURATION DISPLAY AND VALIDATION
# ============================================================================

display_config_summary() {
    echo ""
    echo "============================================================================"
    echo "                    DUAL WI-FI CONFIGURATION SUMMARY"
    echo "============================================================================"
    echo "Configuration source: ${CONFIG_SOURCE}"
    echo "Network manager: ${NETWORK_MANAGER}"
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
    echo "Note: Passwords are hidden for security."
    echo "============================================================================"
    echo ""
}

validate_env_config() {
    local warnings=0

    # Check for default/placeholder values that likely need configuration
    if [[ "$DEFAULT_SSID_MAIN" == "YourMainWiFi" || "$DEFAULT_SSID_MAIN" == "your_main_wifi" ]]; then
        log_warn "⚠ Main Wi-Fi SSID appears to be a placeholder value"
        ((warnings++))
    fi

    if [[ "$DEFAULT_SSID_FALLBACK" == "YourFallbackWiFi" || "$DEFAULT_SSID_FALLBACK" == "your_fallback_wifi" ]]; then
        log_warn "⚠ Fallback Wi-Fi SSID appears to be a placeholder value"
        ((warnings++))
    fi

    if [[ $ENV_LOAD_FAILURES -gt 0 && $warnings -gt 0 ]]; then
        echo ""
        echo "💡 TIP: Create a .env file with your Wi-Fi settings:"
        echo "   cp .env.example .env"
        echo "   nano .env  # Edit with your actual Wi-Fi credentials"
        echo ""
    fi
}

# ============================================================================
# SYSTEM REQUIREMENTS AND CHECKS
# ============================================================================

check_system_requirements() {
    log_info "Checking system requirements..."

    # Check if running with sudo
    if [[ $EUID -eq 0 ]]; then
        log_warn "Running as root. This script should be run with sudo, not as root user."
    fi

    # Check required commands based on network manager
    if [[ "$NETWORK_MANAGER" == "networkmanager" ]]; then
        if ! command_exists nmcli; then
            log_error "❌ nmcli command not found. NetworkManager is required."
            exit 1
        fi
    elif [[ "$NETWORK_MANAGER" == "dhcpcd" ]]; then
        if ! command_exists wpa_cli; then
            log_error "❌ wpa_cli command not found. wpa_supplicant is required."
            exit 1
        fi
    fi

    # Check Wi-Fi interfaces
    if ! ip link show wlan0 &>/dev/null; then
        log_error "❌ wlan0 interface not found. Please ensure Wi-Fi hardware is connected."
        exit 1
    fi

    if ! ip link show wlan1 &>/dev/null; then
        log_warn "⚠ wlan1 interface not found. Dual Wi-Fi setup requires two Wi-Fi interfaces."
        log_warn "This setup will work with single interface fallback, but dual interface features will be limited."
    fi

    log_info "✓ System requirements validated"
}

# ============================================================================
# INTERACTIVE CONFIGURATION
# ============================================================================

configure_wifi_settings() {
    echo "Starting Dual Wi-Fi Setup for Network Manager: $NETWORK_MANAGER"
    echo "You will be prompted for configuration values. Press Enter to accept the default."
    echo ""

    validate_env_config
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
        COUNTRY=$(echo "$COUNTRY" | tr '[:lower:]' '[:upper:]')
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
            echo "⚠ Error: Please enter a valid IP address (e.g., 192.168.4.1). Please try again."
        fi
    done
}

confirm_configuration() {
    echo ""
    echo "============================================================================"
    echo "                        FINAL CONFIGURATION"
    echo "============================================================================"
    echo "Network Manager: $NETWORK_MANAGER"
    echo ""
    echo "Main Wi-Fi (wlan1):"
    echo "  SSID: $SSID_MAIN"
    echo "  Gateway: $GATEWAY_MAIN"
    echo ""
    echo "Fallback Wi-Fi (wlan0):"
    echo "  SSID: $SSID_FALLBACK"
    echo "  Gateway: $GATEWAY_FALLBACK"
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

# ============================================================================
# BACKUP FUNCTIONS
# ============================================================================

backup_existing_config() {
    log_info "Creating backup of existing configuration..."
    local backup_dir="/tmp/wifi_backup_$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$backup_dir"

    if [[ "$NETWORK_MANAGER" == "dhcpcd" ]]; then
        if [[ -f /etc/wpa_supplicant/wpa_supplicant.conf ]]; then
            sudo cp /etc/wpa_supplicant/wpa_supplicant.conf "$backup_dir/"
            log_info "✓ Backed up wpa_supplicant.conf to $backup_dir"
        fi

        if [[ -f /etc/dhcpcd.conf ]]; then
            sudo cp /etc/dhcpcd.conf "$backup_dir/"
            log_info "✓ Backed up dhcpcd.conf to $backup_dir"
        fi
    elif [[ "$NETWORK_MANAGER" == "networkmanager" ]]; then
        # Backup NetworkManager connections
        if [[ -d /etc/NetworkManager/system-connections ]]; then
            sudo cp -r /etc/NetworkManager/system-connections "$backup_dir/" 2>/dev/null || true
            log_info "✓ Backed up NetworkManager connections to $backup_dir"
        fi
    fi

    log_info "ℹ Backup location: $backup_dir"
}

# ============================================================================
# NETWORKMANAGER CONFIGURATION
# ============================================================================

configure_networkmanager() {
    log_info "Configuring dual Wi-Fi with NetworkManager..."

    # Remove existing mower connections if they exist
    nmcli connection delete "mower-main" 2>/dev/null || true
    nmcli connection delete "mower-fallback" 2>/dev/null || true

    # Create main Wi-Fi connection (higher priority)
    log_info "Creating main Wi-Fi connection (wlan1)..."
    nmcli connection add type wifi con-name "mower-main" \
        ifname wlan1 ssid "$SSID_MAIN" \
        wifi-sec.key-mgmt wpa-psk wifi-sec.psk "$PASS_MAIN" \
        connection.autoconnect yes connection.autoconnect-priority 10 \
        ipv4.method auto ipv6.method ignore

    # Create fallback Wi-Fi connection (lower priority)
    log_info "Creating fallback Wi-Fi connection (wlan0)..."
    nmcli connection add type wifi con-name "mower-fallback" \
        ifname wlan0 ssid "$SSID_FALLBACK" \
        wifi-sec.key-mgmt wpa-psk wifi-sec.psk "$PASS_FALLBACK" \
        connection.autoconnect yes connection.autoconnect-priority 5 \
        ipv4.method auto ipv6.method ignore

    # Set country code in NetworkManager
    if [[ -f /etc/NetworkManager/conf.d/wifi-country.conf ]]; then
        sudo rm /etc/NetworkManager/conf.d/wifi-country.conf
    fi

    sudo mkdir -p /etc/NetworkManager/conf.d
    sudo tee /etc/NetworkManager/conf.d/wifi-country.conf > /dev/null <<EOF
[device]
wifi.scan-rand-mac-address=no

[main]
plugins=keyfile

[keyfile]
unmanaged-devices=none

[connection]
wifi.powersave=2

[wifi]
country=$COUNTRY
EOF

    # Restart NetworkManager to apply changes
    log_info "Restarting NetworkManager..."
    sudo systemctl restart NetworkManager
    sleep 5

    # Attempt to connect to the main network
    log_info "Attempting to connect to main Wi-Fi..."
    nmcli connection up "mower-main" || log_warn "Failed to connect to main Wi-Fi initially"

    log_info "✓ NetworkManager configuration complete"
}

# ============================================================================
# DHCPCD CONFIGURATION (Legacy)
# ============================================================================

configure_dhcpcd() {
    log_info "Configuring dual Wi-Fi with dhcpcd (legacy mode)..."

    # Create wpa_supplicant configuration
    log_info "Creating wpa_supplicant.conf..."
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

    # Clean up dhcpcd.conf
    log_info "Updating dhcpcd.conf..."
    sudo sed -i '/denyinterfaces wlan0/d' /etc/dhcpcd.conf 2>/dev/null || true
    sudo sed -i '/denyinterfaces wlan1/d' /etc/dhcpcd.conf 2>/dev/null || true

    # Restart services
    log_info "Restarting networking services..."
    sudo systemctl restart dhcpcd || log_warn "Failed to restart dhcpcd"
    sudo wpa_cli -i wlan0 reconfigure &>/dev/null || log_warn "wlan0 reconfigure failed"
    sudo wpa_cli -i wlan1 reconfigure &>/dev/null || log_warn "wlan1 reconfigure failed"

    log_info "✓ dhcpcd configuration complete"
}

# ============================================================================
# WATCHDOG SCRIPT CREATION
# ============================================================================

create_watchdog_script() {
    log_info "Creating NetworkManager-aware Wi-Fi watchdog script..."

    sudo tee /usr/local/bin/wifi_watchdog_nm.py > /dev/null <<EOF
#!/usr/bin/env python3
"""
NetworkManager-Aware Wi-Fi Failover Watchdog for Autonomous Mower

This script monitors Wi-Fi connectivity and manages failover between
primary and fallback connections using NetworkManager when available,
falling back to manual route management for dhcpcd systems.

Compatible with both NetworkManager and dhcpcd network managers.
Follows the autonomous mower project's coding standards.
"""
import subprocess
import time
import logging
import sys
from typing import Optional, Tuple

# Configuration
PING_HOST = "8.8.8.8"  # Google DNS for connectivity testing
PING_INTERVAL = 30     # Seconds between connectivity checks
FAIL_THRESHOLD = 3     # Failed pings before switching interfaces
LOG_LEVEL = logging.INFO

# Interface configuration (matches setup script)
PRIMARY_IFACE = "wlan1"
SECONDARY_IFACE = "wlan0"
PRIMARY_GATEWAY = "$GATEWAY_MAIN"
SECONDARY_GATEWAY = "$GATEWAY_FALLBACK"
PRIMARY_CONNECTION = "mower-main"
SECONDARY_CONNECTION = "mower-fallback"

# Logging setup
logging.basicConfig(
    level=LOG_LEVEL,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/var/log/wifi-watchdog.log')
    ]
)
logger = logging.getLogger(__name__)


def detect_network_manager() -> str:
    """Detect which network manager is active."""
    try:
        result = subprocess.run(['systemctl', 'is-active', 'NetworkManager'],
                              capture_output=True, text=True)
        if result.returncode == 0:
            return 'networkmanager'
    except Exception:
        pass

    try:
        result = subprocess.run(['systemctl', 'is-active', 'dhcpcd'],
                              capture_output=True, text=True)
        if result.returncode == 0:
            return 'dhcpcd'
    except Exception:
        pass

    return 'unknown'


def ping_host(host: str, interface: Optional[str] = None) -> bool:
    """
    Test connectivity by pinging a host.

    Args:
        host (str): Host to ping
        interface (str, optional): Interface to use for ping

    Returns:
        bool: True if ping successful, False otherwise
    """
    try:
        cmd = ['ping', '-c', '1', '-W', '3', host]
        if interface:
            cmd.extend(['-I', interface])

        result = subprocess.run(cmd, capture_output=True)
        return result.returncode == 0
    except Exception as e:
        logger.error(f"Error pinging {host}: {e}")
        return False


def get_active_connection(interface: str) -> Optional[str]:
    """Get the active NetworkManager connection for an interface."""
    try:
        result = subprocess.run([
            'nmcli', '-t', '-f', 'DEVICE,CONNECTION',
            'device', 'status'
        ], capture_output=True, text=True)

        for line in result.stdout.strip().split('\n'):
            if line.startswith(f"{interface}:"):
                connection = line.split(':')[1]
                return connection if connection != '--' else None
        return None
    except Exception as e:
        logger.error(f"Error getting active connection for {interface}: {e}")
        return None


def switch_networkmanager_connection(primary: bool) -> bool:
    """
    Switch between primary and secondary connections using NetworkManager.

    Args:
        primary (bool): True to switch to primary, False for secondary

    Returns:
        bool: True if switch successful, False otherwise
    """
    try:
        if primary:
            target_connection = PRIMARY_CONNECTION
            target_interface = PRIMARY_IFACE
            # Disconnect secondary first
            subprocess.run(['nmcli', 'connection', 'down', SECONDARY_CONNECTION],
                         capture_output=True)
        else:
            target_connection = SECONDARY_CONNECTION
            target_interface = SECONDARY_IFACE
            # Disconnect primary first
            subprocess.run(['nmcli', 'connection', 'down', PRIMARY_CONNECTION],
                         capture_output=True)

        # Connect to target
        result = subprocess.run([
            'nmcli', 'connection', 'up', target_connection,
            'ifname', target_interface
        ], capture_output=True, text=True)

        if result.returncode == 0:
            logger.info(f"Switched to {'primary' if primary else 'secondary'} connection ({target_connection})")
            return True
        else:
            logger.error(f"Failed to switch to {target_connection}: {result.stderr}")
            return False

    except Exception as e:
        logger.error(f"Error switching NetworkManager connection: {e}")
        return False


def set_manual_route(primary: bool) -> bool:
    """
    Set routes manually for dhcpcd systems.

    Args:
        primary (bool): True to use primary interface, False for secondary

    Returns:
        bool: True if route set successfully, False otherwise
    """
    try:
        # Remove existing default routes
        subprocess.run(['ip', 'route', 'del', 'default'],
                      stderr=subprocess.DEVNULL)

        if primary:
            subprocess.run([
                'ip', 'route', 'add', 'default', 'via', PRIMARY_GATEWAY,
                'dev', PRIMARY_IFACE, 'metric', '100'
            ])
            subprocess.run([
                'ip', 'route', 'add', 'default', 'via', SECONDARY_GATEWAY,
                'dev', SECONDARY_IFACE, 'metric', '200'
            ])
            logger.info(f"Set manual route to primary interface ({PRIMARY_IFACE})")
        else:
            subprocess.run([
                'ip', 'route', 'add', 'default', 'via', SECONDARY_GATEWAY,
                'dev', SECONDARY_IFACE, 'metric', '100'
            ])
            subprocess.run([
                'ip', 'route', 'add', 'default', 'via', PRIMARY_GATEWAY,
                'dev', PRIMARY_IFACE, 'metric', '200'
            ])
            logger.info(f"Set manual route to secondary interface ({SECONDARY_IFACE})")

        return True

    except Exception as e:
        logger.error(f"Error setting manual route: {e}")
        return False


def main():
    """Main watchdog loop with NetworkManager awareness."""
    network_manager = detect_network_manager()
    logger.info(f"Wi-Fi Watchdog started with {network_manager} network manager")
    logger.info(f"Primary: {PRIMARY_IFACE} ({PRIMARY_GATEWAY})")
    logger.info(f"Secondary: {SECONDARY_IFACE} ({SECONDARY_GATEWAY})")

    fail_count = 0
    primary_active = True

    while True:
        try:
            # Test connectivity
            connectivity_ok = ping_host(PING_HOST)

            if connectivity_ok:
                # Reset fail count on successful ping
                if fail_count > 0:
                    logger.info("Connectivity restored")
                    fail_count = 0

                # If we're on secondary and connectivity is good, try to switch back to primary
                if not primary_active and network_manager == 'networkmanager':
                    logger.info("Attempting to switch back to primary connection")
                    if switch_networkmanager_connection(primary=True):
                        primary_active = True

            else:
                fail_count += 1
                logger.warning(f"Connectivity check failed ({fail_count}/{FAIL_THRESHOLD})")

                if fail_count >= FAIL_THRESHOLD:
                    if primary_active:
                        logger.error("Primary connection failed, switching to fallback")
                        if network_manager == 'networkmanager':
                            success = switch_networkmanager_connection(primary=False)
                        else:
                            success = set_manual_route(primary=False)

                        if success:
                            primary_active = False
                        fail_count = 0  # Reset counter after switch attempt
                    else:
                        logger.error("Both connections appear to be failing")

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

    sudo chmod +x /usr/local/bin/wifi_watchdog_nm.py
    log_info "✓ NetworkManager-aware watchdog script created"
}

# ============================================================================
# SYSTEMD SERVICE SETUP
# ============================================================================

create_systemd_service() {
    log_info "Setting up watchdog systemd service..."

    sudo tee /etc/systemd/system/wifi-watchdog.service > /dev/null <<EOF
[Unit]
Description=NetworkManager-Aware Wi-Fi Failover Watchdog for Autonomous Mower
After=network-online.target
Wants=network-online.target
Documentation=https://github.com/username/autonomous_mower

[Service]
Type=simple
ExecStart=/usr/local/bin/wifi_watchdog_nm.py
Restart=always
RestartSec=10
User=root
StandardOutput=journal
StandardError=journal

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ReadWritePaths=/var/log

[Install]
WantedBy=multi-user.target
EOF

    # Reload systemd and enable the service
    sudo systemctl daemon-reload
    sudo systemctl enable wifi-watchdog.service

    log_info "✓ Watchdog service created and enabled"
    log_info "To start the service: sudo systemctl start wifi-watchdog"
    log_info "To check status: sudo systemctl status wifi-watchdog"
}

# ============================================================================
# MAIN CONFIGURATION EXECUTION
# ============================================================================

main_configuration() {
    backup_existing_config

    if [[ "$NETWORK_MANAGER" == "networkmanager" ]]; then
        configure_networkmanager
    elif [[ "$NETWORK_MANAGER" == "dhcpcd" ]]; then
        configure_dhcpcd
    else
        log_error "❌ Unsupported network manager: $NETWORK_MANAGER"
        exit 1
    fi

    create_watchdog_script
    create_systemd_service
}

# ============================================================================
# STATUS AND TESTING
# ============================================================================

test_connectivity() {
    log_info "Testing connectivity..."

    sleep 10  # Allow time for connections to establish

    if ping -c 3 8.8.8.8 >/dev/null 2>&1; then
        log_info "✓ Internet connectivity test passed"
    else
        log_warn "⚠ Internet connectivity test failed"
        log_warn "This may be temporary. Check your network settings."
    fi

    if [[ "$NETWORK_MANAGER" == "networkmanager" ]]; then
        log_info "NetworkManager connection status:"
        nmcli connection show --active
    fi
}

display_completion_summary() {
    echo ""
    echo "============================================================================"
    echo "                    DUAL WI-FI SETUP COMPLETE"
    echo "============================================================================"
    echo "Network Manager: $NETWORK_MANAGER"
    echo "Main Connection: $SSID_MAIN (wlan1) - Priority 10"
    echo "Fallback Connection: $SSID_FALLBACK (wlan0) - Priority 5"
    echo ""
    echo "Services created:"
    echo "✓ Wi-Fi watchdog: /usr/local/bin/wifi_watchdog_nm.py"
    echo "✓ Systemd service: wifi-watchdog.service (enabled)"
    echo ""
    echo "Management commands:"
    if [[ "$NETWORK_MANAGER" == "networkmanager" ]]; then
        echo "• Check connections: nmcli connection show"
        echo "• Switch manually: nmcli connection up mower-main"
        echo "• Monitor: nmcli device wifi"
    else
        echo "• Check status: wpa_cli status"
        echo "• Scan networks: wpa_cli scan && wpa_cli scan_results"
    fi
    echo "• Watchdog status: sudo systemctl status wifi-watchdog"
    echo "• View logs: sudo journalctl -u wifi-watchdog -f"
    echo ""
    echo "Next steps:"
    echo "1. Start the watchdog: sudo systemctl start wifi-watchdog"
    echo "2. Test failover by moving between networks"
    echo "3. Monitor logs for proper operation"
    echo "============================================================================"
}

# ============================================================================
# MAIN SCRIPT EXECUTION
# ============================================================================

main() {
    echo ""
    echo "============================================================================"
    echo "        NetworkManager-Compatible Dual Wi-Fi Setup for Autonomous Mower"
    echo "============================================================================"
    echo ""

    # Load environment and detect network manager
    load_env_config
    detect_network_manager
    check_system_requirements

    # Interactive configuration
    configure_wifi_settings
    confirm_configuration

    # Execute configuration
    main_configuration

    # Test and display results
    test_connectivity
    display_completion_summary

    log_info "Dual Wi-Fi setup completed successfully!"
}

# Execute main function
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
