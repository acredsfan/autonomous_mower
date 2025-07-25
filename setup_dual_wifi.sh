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
# Usage: sudo ./setup_dual_wifi_networkmanager.sh [--test-mode]
#
# Options:
#   --test-mode    Run in test mode (skip hardware checks for development/testing)
#
# Author: Autonomous Mower Project
# License: Project License
# ============================================================================

set -euo pipefail  # Exit on error, undefined vars, pipe failures

# Script execution mode
TEST_MODE=false

# Check for test mode flag
for arg in "$@"; do
    case $arg in
        --test-mode)
            TEST_MODE=true
            shift
            ;;
        *)
            ;;
    esac
done

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

    if [[ "$TEST_MODE" == true ]]; then
        NETWORK_MANAGER="networkmanager"
        log_info "TEST MODE: Using NetworkManager as default"
        return 0
    fi

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
    # set -x
    local env_files_to_check=(".env" ".env.local" ".env.example")
    local loaded_successfully=false
    ENV_FILE_PATH="" # Reset global ENV_FILE_PATH

    log_info "Attempting to load environment configuration..."

    for env_file_candidate in "${env_files_to_check[@]}"; do
        if [ -f "$env_file_candidate" ]; then
            if [ -s "$env_file_candidate" ]; then # Check if file is not empty
                ENV_FILE_PATH="$env_file_candidate"
                log_info "Found environment file: $ENV_FILE_PATH" # User sees this
                CONFIG_SOURCE="$ENV_FILE_PATH"

                local wifi_var_count=0
                # Temporarily store loaded values before assigning to DEFAULT_ vars
                local temp_ssid_main="" temp_pass_main="" temp_ssid_fallback="" temp_pass_fallback=""
                local temp_country="" temp_gateway_main="" temp_gateway_fallback=""

                # Read the file
                while IFS= read -r line || [[ -n "$line" ]]; do
                    # Skip comments and empty lines
                    [[ -z "$line" ]] && continue
                    [[ $line =~ ^[[:space:]]*# ]] && continue
                    
                    # Check if line contains '='
                    if [[ ! "$line" =~ = ]]; then
                        continue
                    fi
                    
                    # Split key and value safely
                    key="${line%%=*}"
                    value="${line#*=}"
                    
                    # Trim whitespace from key
                    key=$(echo "$key" | xargs)
                    
                    # Skip if key is empty after trimming
                    [[ -z "$key" ]] && continue
                    
                    # Process value if it exists
                    if [[ -n "$value" ]]; then
                        # Remove inline comments and trim
                        value=$(echo "$value" | sed 's/#.*//' | xargs)
                        # Remove quotes
                        value=${value#\"} 
                        value=${value%\"} 
                        value=${value#\'} 
                        value=${value%\'} 
                    fi

                    # Skip empty keys again after xargs
                    [[ -z "$key" ]] && continue
                    # Skip if value is empty after processing
                    [[ -z "$value" ]] && continue

                    # log_info "Processing key: '$key', value: '$value'" # Uncomment for deep debugging
                    case "$key" in
                        (DEFAULT_SSID_MAIN) temp_ssid_main="$value"; wifi_var_count=$((wifi_var_count + 1)) ;;
                        (DEFAULT_PASS_MAIN) temp_pass_main="$value"; wifi_var_count=$((wifi_var_count + 1)) ;;
                        (DEFAULT_SSID_FALLBACK) temp_ssid_fallback="$value"; wifi_var_count=$((wifi_var_count + 1)) ;;
                        (DEFAULT_PASS_FALLBACK) temp_pass_fallback="$value"; wifi_var_count=$((wifi_var_count + 1)) ;;
                        (DEFAULT_COUNTRY) temp_country="$value"; wifi_var_count=$((wifi_var_count + 1)) ;;
                        (DEFAULT_GATEWAY_MAIN) temp_gateway_main="$value"; wifi_var_count=$((wifi_var_count + 1)) ;;
                        (DEFAULT_GATEWAY_FALLBACK) temp_gateway_fallback="$value"; wifi_var_count=$((wifi_var_count + 1)) ;;
                    esac
                done < "$ENV_FILE_PATH"

                log_info "Finished reading $ENV_FILE_PATH. Wi-Fi variables found in file: $wifi_var_count."

                if [ "$wifi_var_count" -gt 0 ]; then
                    # Update DEFAULT_ variables if values were found
                    [ -n "$temp_ssid_main" ] && DEFAULT_SSID_MAIN="$temp_ssid_main"
                    [ -n "$temp_pass_main" ] && DEFAULT_PASS_MAIN="$temp_pass_main"
                    [ -n "$temp_ssid_fallback" ] && DEFAULT_SSID_FALLBACK="$temp_ssid_fallback"
                    [ -n "$temp_pass_fallback" ] && DEFAULT_PASS_FALLBACK="$temp_pass_fallback"
                    [ -n "$temp_country" ] && DEFAULT_COUNTRY="$temp_country"
                    [ -n "$temp_gateway_main" ] && DEFAULT_GATEWAY_MAIN="$temp_gateway_main"
                    [ -n "$temp_gateway_fallback" ] && DEFAULT_GATEWAY_FALLBACK="$temp_gateway_fallback"

                    log_info "Successfully processed $wifi_var_count variables from $ENV_FILE_PATH."
                    loaded_successfully=true
                else
                    log_warn "Environment file $ENV_FILE_PATH was read, but no recognized dual Wi-Fi variables were found or values were empty."
                    ((ENV_LOAD_FAILURES++))
                fi
                break # Exit loop once a file is successfully processed or attempted
            else
                log_warn "Found environment file $env_file_candidate, but it is empty. Skipping."
            fi
        fi
    done

    if [[ "$loaded_successfully" == true ]]; then
        log_info "Configuration will be based on $CONFIG_SOURCE."
    else
        log_warn "No .env file with Wi-Fi variables processed successfully. Using built-in default Wi-Fi settings."
        CONFIG_SOURCE="built-in defaults"
        # Ensure ENV_LOAD_FAILURES is incremented if no file was ever found or all were empty/failed
        if [ -z "$ENV_FILE_PATH" ]; then # If no file was even found
             ((ENV_LOAD_FAILURES++))
        fi
    fi

    # Always assign to operational variables from the (potentially updated) DEFAULT_ variables
    SSID_MAIN="$DEFAULT_SSID_MAIN"
    PASS_MAIN="$DEFAULT_PASS_MAIN"
    SSID_FALLBACK="$DEFAULT_SSID_FALLBACK"
    PASS_FALLBACK="$DEFAULT_PASS_FALLBACK"
    COUNTRY="$DEFAULT_COUNTRY"
    GATEWAY_MAIN="$DEFAULT_GATEWAY_MAIN"
    GATEWAY_FALLBACK="$DEFAULT_GATEWAY_FALLBACK"

    # Log final values being used (except passwords)
    log_info "Effective Main SSID: $SSID_MAIN, Gateway: $GATEWAY_MAIN"
    log_info "Effective Fallback SSID: $SSID_FALLBACK, Gateway: $GATEWAY_FALLBACK"
    log_info "Effective Country: $COUNTRY"
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

    if [[ "$TEST_MODE" == true ]]; then
        log_info "Running in TEST MODE - skipping hardware checks"
        return 0
    fi

    # Check if running with sudo
    if [[ $EUID -ne 0 ]]; then
        log_error "❌ This script must be run with sudo privileges"
        log_error "Please run: sudo $0 $@"
        exit 1
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
    echo "Configuration values were loaded from: ${CONFIG_SOURCE}"
    echo ""

    validate_env_config
    display_config_summary

    # Ask for overall confirmation first
    read -p "Are all these settings correct? (Y/n): " overall_confirm
    
    if [[ ! "$overall_confirm" =~ ^[Nn]$ ]]; then
        # User confirmed all settings are correct
        SSID_MAIN="$DEFAULT_SSID_MAIN"
        PASS_MAIN="$DEFAULT_PASS_MAIN"
        SSID_FALLBACK="$DEFAULT_SSID_FALLBACK"
        PASS_FALLBACK="$DEFAULT_PASS_FALLBACK"
        COUNTRY="$DEFAULT_COUNTRY"
        GATEWAY_MAIN="$DEFAULT_GATEWAY_MAIN"
        GATEWAY_FALLBACK="$DEFAULT_GATEWAY_FALLBACK"
        
        # Just verify passwords were set
        echo ""
        read -p "Have you set the main Wi-Fi password in the .env file? (Y/n): " pass_confirm
        if [[ "$pass_confirm" =~ ^[Nn]$ ]]; then
            read -s -p "Enter the password for your main Wi-Fi network (input hidden): " PASS_MAIN
            echo
        fi
        
        read -p "Have you set the fallback Wi-Fi password in the .env file? (Y/n): " pass_confirm
        if [[ "$pass_confirm" =~ ^[Nn]$ ]]; then
            read -s -p "Enter the password for your fallback Wi-Fi network (input hidden): " PASS_FALLBACK
            echo
        fi
    else
        # User wants to change some settings - go through them one by one
        echo ""
        echo "Let's review each setting individually..."
        echo ""
        
        # Main Wi-Fi SSID
        while true; do
            echo "Main Wi-Fi SSID is currently: ${DEFAULT_SSID_MAIN}"
            read -p "Is this correct? (Y/n): " confirm
            if [[ "$confirm" =~ ^[Nn]$ ]]; then
                read -p "Enter the correct SSID for your main Wi-Fi network: " SSID_MAIN
                if validate_ssid "$SSID_MAIN"; then
                    break
                else
                    echo "⚠ Error: SSID must be 1-32 characters long. Please try again."
                fi
            else
                SSID_MAIN="$DEFAULT_SSID_MAIN"
                break
            fi
        done

        # Main Wi-Fi Password
        read -p "Do you need to update the main Wi-Fi password? (y/N): " confirm
        if [[ "$confirm" =~ ^[Yy]$ ]]; then
            read -s -p "Enter the password for your main Wi-Fi network (input hidden): " PASS_MAIN
            echo
        else
            PASS_MAIN="$DEFAULT_PASS_MAIN"
        fi

        # Fallback Wi-Fi SSID
        while true; do
            echo "Fallback Wi-Fi SSID is currently: ${DEFAULT_SSID_FALLBACK}"
            read -p "Is this correct? (Y/n): " confirm
            if [[ "$confirm" =~ ^[Nn]$ ]]; then
                read -p "Enter the correct SSID for your fallback Wi-Fi network: " SSID_FALLBACK
                if validate_ssid "$SSID_FALLBACK"; then
                    break
                else
                    echo "⚠ Error: SSID must be 1-32 characters long. Please try again."
                fi
            else
                SSID_FALLBACK="$DEFAULT_SSID_FALLBACK"
                break
            fi
        done

        # Fallback Wi-Fi Password
        read -p "Do you need to update the fallback Wi-Fi password? (y/N): " confirm
        if [[ "$confirm" =~ ^[Yy]$ ]]; then
            read -s -p "Enter the password for your fallback Wi-Fi network (input hidden): " PASS_FALLBACK
            echo
        else
            PASS_FALLBACK="$DEFAULT_PASS_FALLBACK"
        fi

        # Country Code
        while true; do
            echo "Country code is currently: ${DEFAULT_COUNTRY}"
            read -p "Is this correct? (Y/n): " confirm
            if [[ "$confirm" =~ ^[Nn]$ ]]; then
                read -p "Enter your two-letter ISO country code (e.g., US, GB): " COUNTRY
                COUNTRY=$(echo "$COUNTRY" | tr '[:lower:]' '[:upper:]')
                if validate_country_code "$COUNTRY"; then
                    break
                else
                    echo "⚠ Error: Country code must be exactly 2 uppercase letters (e.g., US, GB). Please try again."
                fi
            else
                COUNTRY="$DEFAULT_COUNTRY"
                break
            fi
        done

        # Main Gateway IP
        while true; do
            echo "Main Wi-Fi gateway IP is currently: ${DEFAULT_GATEWAY_MAIN}"
            read -p "Is this correct? (Y/n): " confirm
            if [[ "$confirm" =~ ^[Nn]$ ]]; then
                read -p "Enter the correct gateway IP for your main Wi-Fi (wlan1): " GATEWAY_MAIN
                if validate_ip "$GATEWAY_MAIN"; then
                    break
                else
                    echo "⚠ Error: Please enter a valid IP address (e.g., 192.168.1.1). Please try again."
                fi
            else
                GATEWAY_MAIN="$DEFAULT_GATEWAY_MAIN"
                break
            fi
        done

        # Fallback Gateway IP
        while true; do
            echo "Fallback Wi-Fi gateway IP is currently: ${DEFAULT_GATEWAY_FALLBACK}"
            read -p "Is this correct? (Y/n): " confirm
            if [[ "$confirm" =~ ^[Nn]$ ]]; then
                read -p "Enter the correct gateway IP for your fallback Wi-Fi (wlan0): " GATEWAY_FALLBACK
                if validate_ip "$GATEWAY_FALLBACK"; then
                    break
                else
                    echo "⚠ Error: Please enter a valid IP address (e.g., 192.168.4.1). Please try again."
                fi
            else
                GATEWAY_FALLBACK="$DEFAULT_GATEWAY_FALLBACK"
                break
            fi
        done
    fi
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

        # Create main Wi-Fi connection (wlan1, higher priority)
    log_info "Creating main Wi-Fi connection for wlan1 (SSID: $SSID_MAIN)..."
    nmcli connection add type wifi con-name "mower-main" \
        ifname wlan1 \
        ssid "$SSID_MAIN" -- wifi-sec.key-mgmt wpa-psk wifi-sec.psk "$PASS_MAIN" \
        connection.autoconnect yes connection.autoconnect-priority 10 \
        ipv4.route-metric 100 ipv4.method auto ipv6.method ignore

    # Create fallback Wi-Fi connection (wlan0, lower priority)
    log_info "Creating fallback Wi-Fi connection for wlan0 (SSID: $SSID_FALLBACK)..."
    nmcli connection add type wifi con-name "mower-fallback" \
        ifname wlan0 \
        ssid "$SSID_FALLBACK" -- wifi-sec.key-mgmt wpa-psk wifi-sec.psk "$PASS_FALLBACK" \
        connection.autoconnect yes connection.autoconnect-priority 5 \
        ipv4.route-metric 200 ipv4.method auto ipv6.method ignore

    # Set country code in NetworkManager config
    log_info "Configuring country code and Wi-Fi powersave settings..."
    sudo mkdir -p /etc/NetworkManager/conf.d
    sudo tee /etc/NetworkManager/conf.d/99-mower-wifi-settings.conf > /dev/null <<EOF

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
    sudo rm /etc/NetworkManager/system-connections/preconfigured.nmconnection
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
    log_info "MAIN: Starting script execution"
    log_info "MAIN: Calling load_env_config"
    load_env_config
    log_info "MAIN: load_env_config completed"
    log_info "MAIN: Calling detect_network_manager"
    detect_network_manager
    log_info "MAIN: detect_network_manager completed. NETWORK_MANAGER is $NETWORK_MANAGER"
    log_info "MAIN: Calling check_system_requirements"
    check_system_requirements
    log_info "MAIN: check_system_requirements completed"

    # Interactive configuration
    log_info "MAIN: Calling configure_wifi_settings"
    configure_wifi_settings
    log_info "MAIN: configure_wifi_settings completed"
    log_info "MAIN: Calling confirm_configuration"
    confirm_configuration
    log_info "MAIN: confirm_configuration completed"

    # Execute configuration
    log_info "MAIN: Calling main_configuration"
    main_configuration
    log_info "MAIN: main_configuration completed"

    # Test and display results
    log_info "MAIN: Calling test_connectivity"
    test_connectivity
    log_info "MAIN: test_connectivity completed"
    log_info "MAIN: Calling display_completion_summary"
    display_completion_summary
    log_info "MAIN: display_completion_summary completed"

    log_info "Dual Wi-Fi setup completed successfully!"
}

# Execute main function
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
