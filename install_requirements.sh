#!/bin/bash

# Exit on error
set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# -----------------  Host detection  -----------------
IS_PI=false
if [[ -f /proc/device-tree/model ]] && grep -q "Raspberry Pi" /proc/device-tree/model; then
    IS_PI=true
fi

# Global variable to collect messages for the end
POST_INSTALL_MESSAGES=""
CONFIG_TXT_FOUND_BY_ENABLE_FUNC=false


# Non-interactive mode flag
NON_INTERACTIVE=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -y|--yes|--non-interactive)
            NON_INTERACTIVE=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  -y, --yes, --non-interactive    Run in non-interactive mode (auto-answer yes to all prompts)"
            echo "  -h, --help                      Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use -h or --help for usage information"
            exit 1
            ;;
    esac
done

# Checkpoint functionality
CHECKPOINT_FILE=".install_checkpoints"

# Function to mark a step as completed
mark_step_completed() {
    local step_name="$1"
    # Ensure checkpoint file is writable
    touch "$CHECKPOINT_FILE" 2>/dev/null || {
        print_warning "Cannot write to checkpoint file $CHECKPOINT_FILE. Using /tmp/install_checkpoints instead."
        CHECKPOINT_FILE="/tmp/.install_checkpoints"
        touch "$CHECKPOINT_FILE"
    }
    echo "$step_name=$(date '+%Y-%m-%d %H:%M:%S')" >> "$CHECKPOINT_FILE"
}

# Function to check if a step is completed
is_step_completed() {
    local step_name="$1"
    [ -f "$CHECKPOINT_FILE" ] && grep -q "^$step_name=" "$CHECKPOINT_FILE"
}

# Function to get checkpoint status
get_checkpoint_status() {
    local step_name="$1"
    if [ -f "$CHECKPOINT_FILE" ]; then
        grep "^$step_name=" "$CHECKPOINT_FILE" | cut -d'=' -f2
    else
        echo ""
    fi
}

# Function to list completed steps
list_completed_steps() {
    if [ -f "$CHECKPOINT_FILE" ]; then
        print_info "Previously completed installation steps:"
        while IFS='=' read -r step timestamp; do
            echo -e "  ${GREEN}✓${NC} $step (completed: $timestamp)"
        done < "$CHECKPOINT_FILE"
        echo ""
    fi
}

# Function to prompt user to skip completed step
prompt_skip_completed() {
    local step_name="$1"
    local description="$2"

    if is_step_completed "$step_name"; then
        local completion_time=$(get_checkpoint_status "$step_name")
        print_info "$description appears to be already completed (completed: $completion_time)"
        prompt_user "Skip this step?" "Y" "Y/n"
        if [[ ! $REPLY =~ ^[Nn]$ ]]; then
            print_info "Skipping $description..."
            return 0  # Skip step
        else
            print_info "Re-running $description..."
            return 1  # Don't skip step
        fi
    fi
    return 1  # Don't skip step
}

# Function to auto-detect completed installations
auto_detect_completed_steps() {
    print_info "Auto-detecting completed installation steps..."



    # Check system packages
    if command_exists i2c-detect && command_exists gpsd && ! is_step_completed "system_packages"; then
        mark_step_completed "system_packages"
        print_info "✓ Detected installed system packages"
    fi

    # Check PYTHONPATH setup
    if grep -q "PYTHONPATH.*src" "$HOME/.bashrc" 2>/dev/null && ! is_step_completed "pythonpath_setup"; then
        mark_step_completed "pythonpath_setup"
        print_info "✓ Detected PYTHONPATH configuration"
    fi

    # Check YOLOv8 models
    if [ -f "models/yolov8n.pt" ] || [ -f "models/detect.tflite" ]; then
        if ! is_step_completed "yolov8_setup"; then
            mark_step_completed "yolov8_setup"
            print_info "✓ Detected YOLOv8 models"
        fi
    fi

    # Check Coral TPU (now looks for Python 3.9 virtual environment)
    local coral_env_dir="$HOME/.coral-python-env"
    if [ -f "/etc/apt/sources.list.d/coral-edgetpu.list" ] && [ -d "$coral_env_dir" ] && [ -f "$coral_env_dir/bin/python" ]; then
        # Test if PyCoral is available in the Coral environment
        if "$coral_env_dir/bin/python" -c "import pycoral" 2>/dev/null; then
            if ! is_step_completed "coral_tpu_setup"; then
                mark_step_completed "coral_tpu_setup"
                print_info "✓ Detected Coral TPU installation (Python 3.9 virtual environment)"
            fi
        fi
    fi

    # Check watchdog
    if systemctl is-enabled --quiet watchdog 2>/dev/null && [ -f "/etc/watchdog.conf" ]; then
        if ! is_step_completed "hardware_watchdog"; then
            mark_step_completed "hardware_watchdog"
            print_info "✓ Detected hardware watchdog setup"
        fi
    fi

    # Check systemd service
    if systemctl is-enabled --quiet autonomous-mower 2>/dev/null; then
        if ! is_step_completed "systemd_service"; then
            mark_step_completed "systemd_service"
            print_info "✓ Detected systemd service installation"
        fi
    fi
}

# Function to print error messages
print_error() {
    echo -e "${RED}ERROR: $1${NC}"
}

# Function to print success messages
print_success() {
    echo -e "${GREEN}SUCCESS: $1${NC}"
}

# Function to print warning messages
print_warning() {
    echo -e "${YELLOW}WARNING: $1${NC}"
}

# Function to print info messages
print_info() {
    echo -e "${YELLOW}INFO: $1${NC}"
}

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check if a command succeeded
check_command() {
    if [ $? -ne 0 ]; then
        print_error "Command failed: $1"
        return 1
    fi
    return 0
}

# Function to prompt user with support for non-interactive mode
prompt_user() {
    local prompt_text="$1"
    local default_answer="${2:-y}"  # Default to 'y' if not specified
    local options="${3:-y/n}"       # Default options format

    if [ "$NON_INTERACTIVE" = true ]; then
        echo -e "${YELLOW}${prompt_text} (${options}) [NON-INTERACTIVE: defaulting to '${default_answer}']${NC}"
        REPLY="$default_answer"
        return 0
    fi

    read -p "${prompt_text} (${options}) " -n 1 -r; echo
    return 0
}

# Function to prompt user for selection with support for non-interactive mode
prompt_selection() {
    local prompt_text="$1"
    local default_choice="${2:-1}"  # Default choice if not specified

    if [ "$NON_INTERACTIVE" = true ]; then
        echo -e "${YELLOW}${prompt_text} [NON-INTERACTIVE: defaulting to '${default_choice}']${NC}"
        choice="$default_choice"
        return 0
    fi

    read -p "${prompt_text} " choice
    return 0
}

# Function to prompt for continuation (Enter to continue)
prompt_continue() {
    local prompt_text="${1:-Press Enter to continue...}"

    if [ "$NON_INTERACTIVE" = true ]; then
        echo -e "${YELLOW}${prompt_text} [NON-INTERACTIVE: continuing automatically]${NC}"
        return 0
    fi

    read -p "${prompt_text}" -r
    return 0
}

# Function to find the target config.txt file
get_config_txt_target() {
    # Return empty string for non-Pi systems
    if [ "$IS_PI" = false ]; then
        echo ""
        return
    fi

    local CONFIG_TXT_NEW="/boot/firmware/config.txt"
    local CONFIG_TXT_OLD="/boot/config.txt"
    if [ -f "$CONFIG_TXT_NEW" ]; then
        echo "$CONFIG_TXT_NEW"
    elif [ -f "$CONFIG_TXT_OLD" ]; then
        echo "$CONFIG_TXT_OLD"
    else
        echo ""
    fi
}

# Function to attempt to enable I2C and Serial interfaces
enable_required_interfaces() {
    if [ "$IS_PI" = false ]; then
        print_warning "Non-Raspberry Pi system detected. Skipping hardware interface configuration."
        print_info "Hardware interfaces (I2C, UART) are Pi-specific and will be skipped for testing environments."
        return 0
    fi

    print_info "Checking and attempting to enable required hardware interfaces (I2C, Primary UART)..."
    local CONFIG_TXT_TARGET=$(get_config_txt_target)
    local CHANGES_MADE_CONFIG=false
    local CHANGES_MADE_MODULES=false

    if [ -z "$CONFIG_TXT_TARGET" ]; then
        print_error "Boot configuration file (config.txt) not found. Cannot automatically enable interfaces."
        POST_INSTALL_MESSAGES+="[WARNING] config.txt not found. Please ensure I2C and Serial (UART) are enabled manually via raspi-config and /etc/modules.\\n"
        CONFIG_TXT_FOUND_BY_ENABLE_FUNC=false
        return
    fi
    CONFIG_TXT_FOUND_BY_ENABLE_FUNC=true

    # --- Enable I2C ---
    if ! ls /dev/i2c* >/dev/null 2>&1; then
        print_info "I2C interface not detected (/dev/i2c*). Attempting to configure..."
        if ! sudo grep -q -E "^\\s*dtparam=i2c_arm=on" "$CONFIG_TXT_TARGET"; then
            print_info "Adding 'dtparam=i2c_arm=on' to $CONFIG_TXT_TARGET"
            echo "" | sudo tee -a "$CONFIG_TXT_TARGET" > /dev/null
            echo "dtparam=i2c_arm=on" | sudo tee -a "$CONFIG_TXT_TARGET" > /dev/null
            CHANGES_MADE_CONFIG=true
        else
            print_info "'dtparam=i2c_arm=on' already present in $CONFIG_TXT_TARGET."
        fi
        if ! grep -q -E "^\\s*i2c-dev" /etc/modules; then
            print_info "Adding 'i2c-dev' to /etc/modules for persistent loading."
            echo "i2c-dev" | sudo tee -a /etc/modules > /dev/null
            CHANGES_MADE_MODULES=true
        else
            print_info "'i2c-dev' already present in /etc/modules."
        fi
        if ! lsmod | grep -q "^i2c_dev"; then
            print_info "Attempting to load i2c-dev module now..."
            sudo modprobe i2c-dev
        fi
    else
        print_success "I2C interface (/dev/i2c*) already detected as active."
    fi

    # --- Enable Primary UART (for GPS on ttyAMA0/serial0) ---
    if ! (ls /dev/ttyAMA0 >/dev/null 2>&1 || ls /dev/serial0 >/dev/null 2>&1); then
        print_info "Primary UART (/dev/ttyAMA0 or /dev/serial0) not detected. Attempting to configure..."
        if ! sudo grep -q -E "^\\s*enable_uart=1" "$CONFIG_TXT_TARGET"; then
            print_info "Adding 'enable_uart=1' to $CONFIG_TXT_TARGET (for primary UART)."
            echo "" | sudo tee -a "$CONFIG_TXT_TARGET" > /dev/null
            echo "enable_uart=1" | sudo tee -a "$CONFIG_TXT_TARGET" > /dev/null
            CHANGES_MADE_CONFIG=true
        else
            print_info "'enable_uart=1' already present in $CONFIG_TXT_TARGET."
        fi
    else
        print_success "Primary UART (/dev/ttyAMA0 or /dev/serial0) already detected as active."
    fi

    if $CHANGES_MADE_CONFIG || $CHANGES_MADE_MODULES; then
        POST_INSTALL_MESSAGES+="[INFO] Hardware interfaces (I2C/Primary UART) have been configured in $CONFIG_TXT_TARGET and/or /etc/modules. A REBOOT is required for these changes to fully take effect.\\n"
    fi
    POST_INSTALL_MESSAGES+="[IMPORTANT] If using the primary UART (/dev/ttyAMA0 or /dev/serial0, typically for GPS):\\n"
    POST_INSTALL_MESSAGES+="  Ensure the Linux serial console is DISABLED over this port.\\n"
    POST_INSTALL_MESSAGES+="  Use 'sudo raspi-config':\\n"
    POST_INSTALL_MESSAGES+="    -> Interface Options\\n"
    POST_INSTALL_MESSAGES+="    -> Serial Port\\n"
    POST_INSTALL_MESSAGES+="      -> Would you like a login shell to be accessible over serial? Select <No>\\n"
    POST_INSTALL_MESSAGES+="      -> Would you like the serial port hardware to be enabled? Select <Yes>\\n"
    POST_INSTALL_MESSAGES+="  A reboot will be required after making these changes in raspi-config.\\n"
}

# Function to validate Raspberry Pi hardware
validate_hardware() {
    local CONFIG_TXT_TARGET_FOR_MSG=$(get_config_txt_target)

    if [ "$IS_PI" = false ]; then
        print_warning "Non-Raspberry Pi system detected. Skipping Pi-specific hardware validation."
        print_info "Hardware validation is Pi-specific and will be skipped for testing environments."
        return 0
    fi

    if ! grep -q "Raspberry Pi" /proc/cpuinfo; then
        print_error "This script must be run on a Raspberry Pi"
        exit 1
    fi

    PI_MODEL=$(tr -d '\0' < /proc/device-tree/model)
    if [[ ! "$PI_MODEL" =~ "Raspberry Pi 4" ]]; then # Simplified check, adjust as needed        print_warning "This software is optimized for Raspberry Pi 4B 4GB or better. Current model: $PI_MODEL"
        prompt_user "Continue anyway?" "n" "y/n"
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then exit 1; fi
    fi

    TOTAL_MEM=$(free -m | awk '/^Mem:/{print $2}')
    if [ "$TOTAL_MEM" -lt 3500 ]; then # Approx 3.5GB        print_warning "Recommended minimum RAM is 4GB, current: ${TOTAL_MEM}MB"
        prompt_user "Continue anyway?" "n" "y/n"
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then exit 1; fi
    fi

    if ! ls /dev/i2c* >/dev/null 2>&1; then
        if $CONFIG_TXT_FOUND_BY_ENABLE_FUNC; then # enable_required_interfaces was run
            print_warning "I2C interface (/dev/i2c*) not detected. Auto-configuration was attempted. A REBOOT is likely required."
            # Message already added by enable_required_interfaces if changes were made
        else # enable_required_interfaces didn't run or failed to find config.txt
            print_error "I2C interface not enabled and auto-configuration could not be performed (config.txt not found). Please enable it using raspi-config and reboot."
            exit 1
        fi
    else
        print_success "I2C interface (/dev/i2c*) detected."
    fi

    if ! (ls /dev/ttyAMA0 >/dev/null 2>&1 || ls /dev/serial0 >/dev/null 2>&1); then
         if $CONFIG_TXT_FOUND_BY_ENABLE_FUNC; then
            print_warning "Primary UART (/dev/ttyAMA0 or /dev/serial0) not detected. Auto-configuration was attempted. A REBOOT is likely required."
        else
            print_error "Serial interface not enabled and auto-configuration could not be performed (config.txt not found). Please enable it using raspi-config (and disable serial console if using for GPS) and reboot."
            exit 1
        fi
    else
        print_success "Primary UART (/dev/ttyAMA0 or /dev/serial0) detected."
    fi

    if command_exists libcamera-still; then
        print_info "Verifying camera presence with libcamera-still..."
        if timeout 5 libcamera-still --list-cameras | grep -q "Available cameras"; then
            print_success "Camera detected by libcamera-still."
            print_info "Testing camera capture..."
            if timeout 5 libcamera-still --immediate --timeout 1 -o /dev/null; then # Removed 2>/dev/null to see errors
                print_success "Camera capture test succeeded."
            else                print_warning "libcamera-still capture test failed. Camera might not be working correctly or is misconfigured."
                POST_INSTALL_MESSAGES+="[WARNING] libcamera-still capture test failed. Check camera connection and configuration (e.g., /boot/firmware/config.txt for overlays like 'camera_auto_detect=1').\\n"
                prompt_user "Continue installation despite camera test failure?" "n" "y/n"
                if [[ ! $REPLY =~ ^[Yy]$ ]]; then exit 1; fi
            fi        else
            print_warning "No camera detected by libcamera-still. Ensure camera is connected and enabled (e.g., via raspi-config or in /boot/config.txt or /boot/firmware/config.txt)."
            POST_INSTALL_MESSAGES+="[WARNING] No camera detected by libcamera-still. Ensure camera is connected and enabled. Obstacle detection with camera will not work.\\n"
            prompt_user "Continue installation without a camera?" "n" "y/n"
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then exit 1; fi
        fi
    elif ls /dev/video* >/dev/null 2>&1; then
        print_info "Legacy camera device(s) found: $(ls /dev/video*). Consider using libcamera stack."
        POST_INSTALL_MESSAGES+="[INFO] Legacy camera device(s) found. For best results with Pi OS Bookworm and later, ensure you are using the libcamera stack and 'python3-picamera2'.\\n"
    else
        print_warning "No camera devices found (neither libcamera nor /dev/video*)."
        POST_INSTALL_MESSAGES+="[WARNING] No camera devices found. Obstacle detection with camera will not work.\\n"
        prompt_user "Continue installation without a camera?" "n" "y/n"
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then exit 1; fi
    fi
}

# Function to setup an additional UART
setup_additional_uart() {
    if [ "$IS_PI" = false ]; then
        print_warning "Non-Raspberry Pi system detected. Skipping additional UART configuration."
        print_info "Additional UART configuration is Pi-specific and will be skipped for testing environments."
        return 0
    fi

    print_info "Setting up additional UART (UART2)..."
    local DTOVERLAY_ENTRY="dtoverlay=uart2"
    local CONFIG_TXT_TARGET=$(get_config_txt_target)

    print_info "Disabling bluetooth..."
    local DTOVERLAY_ENTRY="dtoverlay=disable-bt"
    local CONFIG_TXT_TARGET=$(get_config_txt_target)

    if [ -z "$CONFIG_TXT_TARGET" ]; then
        print_error "Boot configuration file (config.txt) not found. Skipping additional UART setup."
        POST_INSTALL_MESSAGES+="[WARNING] config.txt not found. Additional UART (UART2) was not configured.\\n"
        return 1
    fi

    print_info "Target boot configuration file: $CONFIG_TXT_TARGET"

    if sudo grep -q "^${DTOVERLAY_ENTRY}" "$CONFIG_TXT_TARGET"; then
        print_info "UART2 overlay ('${DTOVERLAY_ENTRY}') already exists in $CONFIG_TXT_TARGET."
    else
        print_info "Backing up $CONFIG_TXT_TARGET to ${CONFIG_TXT_TARGET}.bak_uart_setup_$(date +%Y%m%d_%H%M%S)..."
        sudo cp "$CONFIG_TXT_TARGET" "${CONFIG_TXT_TARGET}.bak_uart_setup_$(date +%Y%m%d_%H%M%S)"
        check_command "Backing up $CONFIG_TXT_TARGET" || return 1

        print_info "Adding '${DTOVERLAY_ENTRY}' to $CONFIG_TXT_TARGET..."
        echo "" | sudo tee -a "$CONFIG_TXT_TARGET" > /dev/null
        echo "${DTOVERLAY_ENTRY}" | sudo tee -a "$CONFIG_TXT_TARGET" > /dev/null
        check_command "Adding '${DTOVERLAY_ENTRY}' to $CONFIG_TXT_TARGET" || {
            print_warning "Failed to add '${DTOVERLAY_ENTRY}' to $CONFIG_TXT_TARGET. You may need to add it manually."
            return 1
        }
        print_success "Successfully added '${DTOVERLAY_ENTRY}' to $CONFIG_TXT_TARGET."
        POST_INSTALL_MESSAGES+="[INFO] UART2 overlay added to $CONFIG_TXT_TARGET. A REBOOT is required for this change to take effect.\\n"
    fi
}

# Function to setup watchdog
setup_watchdog() {
    print_info "Setting up hardware watchdog..."

    # Run diagnostics first
    diagnose_watchdog_hardware

    # Check if we're on a Raspberry Pi first using global IS_PI variable
    if [ "$IS_PI" = true ]; then
        print_info "Detected Raspberry Pi hardware."
    else
        print_warning "Non-Raspberry Pi system detected. Hardware watchdog may not be available."
        print_info "Installing watchdog package for compatibility, but hardware features will be limited."
    fi

    # Install watchdog package
    if ! command -v watchdog >/dev/null 2>&1; then
        print_info "Installing watchdog package..."
        if sudo apt-get update && sudo apt-get install -y watchdog; then
            print_info "Watchdog package installed successfully."
        else
            print_error "Failed to install watchdog package."
            return 1
        fi
    else
        print_info "Watchdog package already installed."
    fi

    # Try to load watchdog module if on Raspberry Pi
    if [ "$IS_PI" = true ]; then
        print_info "Loading Raspberry Pi watchdog module..."
        if sudo modprobe bcm2835_wdt 2>/dev/null; then
            print_info "bcm2835_wdt module loaded successfully."

            # Add to /etc/modules for persistence
            if ! grep -q "^bcm2835_wdt" /etc/modules; then
                echo "bcm2835_wdt" | sudo tee -a /etc/modules > /dev/null
                print_info "Added bcm2835_wdt to /etc/modules for persistence."
            fi
        else
            print_warning "Failed to load bcm2835_wdt module. Watchdog may not function."
        fi
    fi

    # Check if hardware watchdog device is available
    if [ ! -e /dev/watchdog ]; then
        print_warning "Hardware watchdog device /dev/watchdog not found."
        if [ "$IS_PI" = true ]; then
            print_warning "This may indicate a problem with the Raspberry Pi watchdog setup."

            # Check and fix boot configuration
            local CONFIG_TXT_TARGET=$(get_config_txt_target)
            if [ -n "$CONFIG_TXT_TARGET" ]; then
                print_info "Checking boot configuration for watchdog settings..."

                if ! grep -q "dtparam=watchdog=on" "$CONFIG_TXT_TARGET" 2>/dev/null; then
                    print_info "Watchdog not enabled in boot config. Adding dtparam=watchdog=on..."

                    # Backup config.txt
                    sudo cp "$CONFIG_TXT_TARGET" "${CONFIG_TXT_TARGET}.bak_watchdog_$(date +%Y%m%d_%H%M%S)"

                    # Add watchdog parameter
                    echo "" | sudo tee -a "$CONFIG_TXT_TARGET" > /dev/null
                    echo "# Enable hardware watchdog" | sudo tee -a "$CONFIG_TXT_TARGET" > /dev/null
                    echo "dtparam=watchdog=on" | sudo tee -a "$CONFIG_TXT_TARGET" > /dev/null

                    print_success "Added dtparam=watchdog=on to $CONFIG_TXT_TARGET"
                    POST_INSTALL_MESSAGES+="[IMPORTANT] Watchdog enabled in boot config. A REBOOT is required for hardware watchdog to become available.\\n"
                    POST_INSTALL_MESSAGES+="[INFO] After reboot, you can manually configure the watchdog service with: sudo systemctl enable watchdog && sudo systemctl start watchdog\\n"
                else
                    print_info "Watchdog is enabled in boot config but device not found."
                    print_warning "This may require a reboot to take effect, or there might be a hardware issue."
                    POST_INSTALL_MESSAGES+="[INFO] Watchdog is enabled in config but device not available. Try rebooting.\\n"
                fi
            else
                print_warning "Could not locate boot configuration file to enable watchdog."
                POST_INSTALL_MESSAGES+="[WARNING] Could not automatically enable watchdog. Manually add 'dtparam=watchdog=on' to /boot/config.txt and reboot.\\n"
            fi
        else
            print_warning "Hardware watchdog not available on this system. This is normal for non-Raspberry Pi systems."
        fi
        
        print_warning "Skipping watchdog service setup due to missing hardware device."
        POST_INSTALL_MESSAGES+="[INFO] Watchdog service setup skipped - hardware device not available.\\n"
        return 0
    fi

    print_info "Hardware watchdog device found at /dev/watchdog."

    # Backup original watchdog.conf if it exists and no backup exists
    if [ -f /etc/watchdog.conf ] && [ ! -f /etc/watchdog.conf.backup ]; then
        if sudo cp /etc/watchdog.conf /etc/watchdog.conf.backup; then
            print_info "Backed up original /etc/watchdog.conf"
        else
            print_warning "Failed to backup /etc/watchdog.conf"
        fi
    fi

    # Configure watchdog.conf
    print_info "Configuring watchdog settings..."

    # Set watchdog device
    if sudo grep -q "^#watchdog-device" /etc/watchdog.conf 2>/dev/null; then
        sudo sed -i 's|^#watchdog-device\s*=\s*/dev/watchdog|watchdog-device = /dev/watchdog|' /etc/watchdog.conf
        print_info "Uncommented watchdog-device in /etc/watchdog.conf."
    elif ! sudo grep -q "^watchdog-device" /etc/watchdog.conf 2>/dev/null; then
        echo "watchdog-device = /dev/watchdog" | sudo tee -a /etc/watchdog.conf > /dev/null
        print_info "Added watchdog-device to /etc/watchdog.conf."
    fi

    # Set max load threshold
    if sudo grep -q "^#max-load-1" /etc/watchdog.conf 2>/dev/null; then
        sudo sed -i 's|^#max-load-1\s*=\s*24|max-load-1 = 24|' /etc/watchdog.conf
        print_info "Uncommented max-load-1 in /etc/watchdog.conf."
    elif ! sudo grep -q "^max-load-1" /etc/watchdog.conf 2>/dev/null; then
        echo "max-load-1 = 24" | sudo tee -a /etc/watchdog.conf > /dev/null
        print_info "Added max-load-1 to /etc/watchdog.conf."
    fi

    # Set watchdog timeout
    if ! sudo grep -q "^watchdog-timeout" /etc/watchdog.conf 2>/dev/null; then
        echo "watchdog-timeout = 15" | sudo tee -a /etc/watchdog.conf > /dev/null
        print_info "Added watchdog-timeout = 15 to /etc/watchdog.conf."
    else
        sudo sed -i 's|^watchdog-timeout\s*=.*|watchdog-timeout = 15|' /etc/watchdog.conf
        print_info "Set watchdog-timeout to 15 seconds in /etc/watchdog.conf."
    fi

    # Validate watchdog configuration file
    print_info "Validating watchdog configuration..."
    local config_valid=true
    
    # Check if watchdog.conf exists and has required settings
    if [ -f /etc/watchdog.conf ]; then
        if grep -q "^watchdog-device" /etc/watchdog.conf; then
            print_info "✓ Watchdog device configured in /etc/watchdog.conf"
        else
            print_warning "⚠ Watchdog device not found in /etc/watchdog.conf"
            config_valid=false
        fi
        
        if grep -q "^watchdog-timeout" /etc/watchdog.conf; then
            print_info "✓ Watchdog timeout configured in /etc/watchdog.conf"
        else
            print_warning "⚠ Watchdog timeout not found in /etc/watchdog.conf"
        fi
        
        if $config_valid; then
            print_info "Watchdog configuration validation passed."
        else
            print_warning "Watchdog configuration has some issues but proceeding with service setup..."
        fi
    else
        print_error "Watchdog configuration file /etc/watchdog.conf not found!"
        return 1
    fi
      # Stop any existing watchdog service to avoid conflicts
    if sudo systemctl is-active --quiet watchdog 2>/dev/null; then
        print_info "Stopping existing watchdog service..."
        sudo systemctl stop watchdog 2>/dev/null || true
        sleep 2
    fi

    # Disable first to clear any stale state
    if sudo systemctl is-enabled --quiet watchdog 2>/dev/null; then
        print_info "Disabling watchdog service to clear any stale state..."
        sudo systemctl disable watchdog 2>/dev/null || true
        sleep 1
    fi

    # Reload systemd daemon to ensure clean state
    print_info "Reloading systemd daemon..."
    sudo systemctl daemon-reload

    # Enable watchdog service with better error handling
    print_info "Enabling watchdog service..."
    local enable_output
    local enable_attempts=0
    local max_enable_attempts=3

    while [ $enable_attempts -lt $max_enable_attempts ]; do
        enable_attempts=$((enable_attempts + 1))
        print_info "Enable attempt $enable_attempts of $max_enable_attempts..."

        enable_output=$(sudo systemctl enable watchdog 2>&1)
        local enable_result=$?

        if [ $enable_result -eq 0 ]; then
            print_info "Watchdog service enabled successfully."
            break
        else
            print_warning "Enable attempt $enable_attempts failed (exit code: $enable_result)"
            print_warning "Enable output: $enable_output"

            if [ $enable_attempts -lt $max_enable_attempts ]; then
                print_info "Retrying in 2 seconds..."
                sleep 2
                # Try to reload systemd again
                sudo systemctl daemon-reload
            else
                print_error "Failed to enable watchdog service after $max_enable_attempts attempts"
                print_error "Final enable output: $enable_output"

                # Check if it's a SysV init issue
                if echo "$enable_output" | grep -q "systemd-sysv-install"; then
                    print_warning "Detected SysV init conflict. Attempting alternative approach..."

                    # Try manual symlink approach
                    if sudo ln -sf /lib/systemd/system/watchdog.service /etc/systemd/system/multi-user.target.wants/watchdog.service 2>/dev/null; then
                        print_info "Created manual service symlink."
                        sudo systemctl daemon-reload
                        enable_result=0
                        break
                    fi
                fi

                return 1
            fi
        fi
    done
      # Start watchdog service with detailed error handling and retry logic
    print_info "Starting watchdog service..."
    local start_output
    local start_attempts=0
    local max_start_attempts=3

    while [ $start_attempts -lt $max_start_attempts ]; do
        start_attempts=$((start_attempts + 1))
        print_info "Start attempt $start_attempts of $max_start_attempts..."

        # Ensure device is ready
        if [ -e /dev/watchdog ]; then
            print_info "Watchdog device /dev/watchdog is available."
        else
            print_warning "Watchdog device not available, waiting..."
            sleep 2
        fi

        start_output=$(sudo systemctl start watchdog 2>&1)
        local start_result=$?

        if [ $start_result -eq 0 ]; then
            print_success "Watchdog service started successfully."
            # Verify service is actually running after successful start
            if [ $start_result -eq 0 ]; then
                sleep 3
                if sudo systemctl is-active --quiet watchdog; then
                    print_success "Watchdog service is running and active."

                    # Show brief status
                    local status_brief
                    status_brief=$(sudo systemctl status watchdog --no-pager -l | head -10)
                    print_info "Watchdog service status:\n$status_brief"
                else
                    print_warning "Watchdog service was started but is not currently active."
                    print_info "Checking service status for more details..."

                    local full_status
                    full_status=$(sudo systemctl status watchdog --no-pager -l || true)
                    print_warning "Full service status:\n$full_status"

                    local recent_logs
                    recent_logs=$(sudo journalctl -u watchdog --no-pager -l --since "5 minutes ago" || true)
                    print_warning "Recent service logs:\n$recent_logs"
                fi
            fi
            break
        else
            print_warning "Start attempt $start_attempts failed (exit code: $start_result)"
            print_warning "Start output: $start_output"

            # Handle specific "Job canceled" issue
            if echo "$start_output" | grep -q -i "canceled\|cancelled"; then
                print_warning "Detected job cancellation. This is often due to timing issues."
                print_info "Attempting to resolve by resetting service state..."

                # Reset the service state
                sudo systemctl reset-failed watchdog 2>/dev/null || true
                sudo systemctl daemon-reload
                sleep 2

                if [ $start_attempts -lt $max_start_attempts ]; then
                    print_info "Retrying start in 3 seconds..."
                    sleep 3
                    continue
                fi
            elif echo "$start_output" | grep -q -i "device\|hardware\|/dev/watchdog"; then
                print_warning "Hardware device issue detected."
                if [ ! -e /dev/watchdog ]; then
                    print_error "Watchdog device /dev/watchdog is missing."
                    break
                fi
            fi

            if [ $start_attempts -lt $max_start_attempts ]; then
                print_info "Retrying in 2 seconds..."
                sleep 2
            else
                print_error "Failed to start watchdog service after $max_start_attempts attempts"
                print_error "Final start output: $start_output"

                # Get detailed information about why it failed
                print_info "Checking service status for error details..."
                local detailed_status
                detailed_status=$(sudo systemctl status watchdog --no-pager -l || true)
                print_error "Detailed service status:\n$detailed_status"

                # Check recent logs
                print_info "Checking recent service logs..."
                local error_logs
                error_logs=$(sudo journalctl -u watchdog --no-pager -l --since "5 minutes ago" || true)
                print_error "Recent error logs:\n$error_logs"
                  # Check if the issue is due to hardware not being available
                if echo "$start_output" | grep -q -i "device\|hardware\|/dev/watchdog"; then
                    print_warning "The error appears to be related to hardware watchdog availability."
                    print_warning "This is common on systems without proper watchdog hardware support."
                    print_info "You can manually check hardware support with: ls -la /dev/watchdog*"
                fi

                # Offer graceful degradation
                print_warning "Watchdog service failed to start. The system will continue without hardware watchdog protection."
                print_info "You can manually start the watchdog later with: sudo systemctl start watchdog"
                POST_INSTALL_MESSAGES+="[WARNING] Hardware watchdog service failed to start. System will run without watchdog protection. Check logs with 'sudo journalctl -u watchdog' for details.\\n"

                # Don't return 1 here to allow installation to continue
                print_info "Continuing installation without watchdog service..."
                return 0
            fi
        fi
    done

    print_success "Hardware watchdog setup completed successfully."
    print_info "Watchdog will monitor system health and reboot if the system becomes unresponsive."
}

# Function to diagnose watchdog hardware support
diagnose_watchdog_hardware() {
    print_info "Diagnosing watchdog hardware support..."

    # Check for Raspberry Pi detection using global IS_PI variable
    if [ "$IS_PI" = true ]; then
        print_info "✓ Raspberry Pi detected"
    else
        print_warning "⚠ Non-Raspberry Pi system detected. Hardware watchdog features will be limited."
        return 0
    fi

    # Check for watchdog device
    if [ -e /dev/watchdog ]; then
        print_info "✓ Hardware watchdog device found: /dev/watchdog"
        ls -la /dev/watchdog* 2>/dev/null || true
    else
        print_warning "⚠ No watchdog device found at /dev/watchdog"
    fi

    # Check for watchdog module
    if lsmod | grep -q bcm2835_wdt; then
        print_info "✓ bcm2835_wdt module is loaded"
    else
        print_warning "⚠ bcm2835_wdt module is not loaded"
    fi

    # Check /etc/modules
    if grep -q "^bcm2835_wdt" /etc/modules 2>/dev/null; then
        print_info "✓ bcm2835_wdt is in /etc/modules"
    else
        print_warning "⚠ bcm2835_wdt not found in /etc/modules"
    fi

    # Check boot config
    local CONFIG_TXT_TARGET=$(get_config_txt_target)
    if [ -n "$CONFIG_TXT_TARGET" ]; then
        if grep -q "dtparam=watchdog=on" "$CONFIG_TXT_TARGET" 2>/dev/null; then
            print_info "✓ Watchdog enabled in boot config"
        else
            print_warning "⚠ Watchdog not explicitly enabled in boot config"
        fi
    fi
}

# Function to setup physical emergency stop
setup_emergency_stop() {
    if ! command_exists python3; then
        print_error "python3 command not found. Cannot configure emergency stop."
        return 1
    fi
    if [ -z "$CONFIG_JSON_PATH" ]; then
        print_error "CONFIG_JSON_PATH shell variable is not set. Cannot configure emergency stop."
        return 1
    fi

    # Export for the Python script
    export CONFIG_JSON_PATH

    python3 - <<EOF
import json
import os
import sys

config_file_path = os.environ.get('CONFIG_JSON_PATH')

if not config_file_path:
    print("Error: CONFIG_JSON_PATH environment variable is not set.", file=sys.stderr)
    sys.exit(1)

config = {}
if os.path.exists(config_file_path):
    try:
        with open(config_file_path, 'r') as f:
            config = json.load(f)
    except json.JSONDecodeError:
        print(f"Warning: Could not decode JSON from {config_file_path}. Initializing with an empty configuration.", file=sys.stderr)
        config = {}
    except Exception as e:
        print(f"Error reading {config_file_path}: {e}", file=sys.stderr)
        sys.exit(1) # Exit Python script with an error
else:
    print(f"Info: Config file {config_file_path} not found. Creating a new one.")
    # config is already initialized as {}

if 'safety' not in config:
    config['safety'] = {}

config['safety']['use_physical_emergency_stop'] = True
config['safety']['emergency_stop_gpio_pin'] = 7 # BCM pin 7 for emergency stop

try:
    with open(config_file_path, 'w') as f:
        json.dump(config, f, indent=4)
    print(f'Updated {config_file_path} to enable physical e-stop.')
except IOError as e:
    print(f"Error writing to {config_file_path}: {e}", file=sys.stderr)
    sys.exit(1) # Exit Python script with an error
except Exception as e:
    print(f"An unexpected error occurred while writing {config_file_path}: {e}", file=sys.stderr)
    sys.exit(1) # Exit Python script with an error
EOF
    local python_exit_status=$?
    if [ $python_exit_status -ne 0 ]; then
        print_error "Python script failed to configure emergency stop (exit code: $python_exit_status)."
        return 1 # Return error from shell function
    fi
    return 0
}

# Function to skip physical emergency stop configuration
skip_physical_emergency_stop() {
    if ! command_exists python3; then
        print_error "python3 command not found. Cannot configure emergency stop."
        return 1
    fi
    if [ -z "$CONFIG_JSON_PATH" ]; then
        print_error "CONFIG_JSON_PATH shell variable is not set. Cannot configure emergency stop."
        return 1
    fi

    # Export for the Python script
    export CONFIG_JSON_PATH

    python3 - <<EOF
import json
import os
import sys

config_file_path = os.environ.get('CONFIG_JSON_PATH')

if not config_file_path:
    print("Error: CONFIG_JSON_PATH environment variable is not set.", file=sys.stderr)
    sys.exit(1)

config = {}
if os.path.exists(config_file_path):
    try:
        with open(config_file_path, 'r') as f:
            config = json.load(f)
    except json.JSONDecodeError:
        print(f"Warning: Could not decode JSON from {config_file_path}. Initializing with an empty configuration.", file=sys.stderr)
        config = {}
    except Exception as e:
        print(f"Error reading {config_file_path}: {e}", file=sys.stderr)
        sys.exit(1) # Exit Python script with an error
else:
    print(f"Info: Config file {config_file_path} not found. Creating a new one.")
    # config is already initialized as {}

if 'safety' not in config:
    config['safety'] = {}

config['safety']['use_physical_emergency_stop'] = False
# No need to explicitly remove 'emergency_stop_gpio_pin', can leave it if it exists

try:
    with open(config_file_path, 'w') as f:
        json.dump(config, f, indent=4)
    print(f'Updated {config_file_path} to disable physical e-stop.')
except IOError as e:
    print(f"Error writing to {config_file_path}: {e}", file=sys.stderr)
    sys.exit(1) # Exit Python script with an error
except Exception as e:
    print(f"An unexpected error occurred while writing {config_file_path}: {e}", file=sys.stderr)
    sys.exit(1) # Exit Python script with an error
EOF
    local python_exit_status=$?
    if [ $python_exit_status -ne 0 ]; then
        print_error "Python script failed to disable emergency stop (exit code: $python_exit_status)."
        return 1 # Return error from shell function
    fi
    return 0
}


# Function to setup YOLOv8 models (system-wide, no venv)
setup_yolov8() {
    print_info "Setting up YOLOv8 for obstacle detection..."
    local PYTHON_CMD="python3"
    local PIP_CMD="pip3"

    print_info "Checking for ultralytics package (using $PIP_CMD)..."
    if ! "$PYTHON_CMD" -m pip show ultralytics > /dev/null 2>&1; then
        print_info "ultralytics package not found. Installing..."
        if dpkg -s python3-sympy &> /dev/null; then
            print_info "System python3-sympy detected. Consider removing it ('sudo apt-get remove python3-sympy') if ultralytics has issues."
        fi
        "$PIP_CMD" install --break-system-packages --upgrade --upgrade-strategy eager "ultralytics>=8.1.0"
        check_command "Installing ultralytics package" || { print_error "Ultralytics installation failed."; return 1; }
    else
        print_success "ultralytics package already installed."
        "$PIP_CMD" install --break-system-packages --upgrade "ultralytics>=8.1.0"
    fi

    print_info "Pre-installing/checking TFLite export dependencies for ultralytics (using $PIP_CMD)..."
    "$PIP_CMD" install --break-system-packages \
        "tf_keras" "sng4onnx>=1.0.1" "onnx_graphsurgeon>=0.3.26" "ai-edge-litert>=1.2.0" \
        "onnx>=1.15.0" "onnx2tf>=1.17.0" "onnxslim>=0.1.46" "onnxruntime>=1.16.0"
    check_command "Installing/checking TFLite export dependencies" || print_warning "Failed to install/check some TFLite export dependencies."

    mkdir -p src/mower/obstacle_detection/models
    check_command "Creating models directory src/mower/obstacle_detection/models" || return 1

    print_info "Running YOLOv8 setup script (scripts/setup_yolov8.py using $PYTHON_CMD)..."
    if [ -f "scripts/setup_yolov8.py" ]; then
        "$PYTHON_CMD" scripts/setup_yolov8.py --model yolov8n
        check_command "Setting up YOLOv8 models via script" || {
            print_error "YOLOv8 model setup script failed."
            POST_INSTALL_MESSAGES+="[ERROR] YOLOv8 model setup script failed.\\n"
            return 1
        }
    else
        print_error "scripts/setup_yolov8.py not found."
        POST_INSTALL_MESSAGES+="[ERROR] scripts/setup_yolov8.py not found. YOLOv8 models not configured.\\n"
        return 1
    fi

    if [ -f "src/mower/obstacle_detection/models/yolov8n_float32.tflite" ] || [ -f "src/mower/obstacle_detection/models/yolov8n.tflite" ]; then
        print_success "YOLOv8 TFLite model found."
    else
        print_warning "Default YOLOv8 TFLite model not found. Check script output."
        POST_INSTALL_MESSAGES+="[WARNING] Default YOLOv8 TFLite model not found after setup.\\n"
    fi
    print_success "YOLOv8 setup function completed."
}


# Function to install Python dependencies system-wide
install_python_dependencies() {
    print_info "Installing Python dependencies system-wide..."
    local PIP_CMD="pip3"
    if ! command_exists "$PIP_CMD"; then
        print_error "pip3 not found. Please install python3-pip."
        return 1
    fi

    print_info "Upgrading pip..."
    "$PIP_CMD" install --break-system-packages --upgrade pip
    check_command "Upgrading pip" || return 1

    print_info "Installing Python dependencies from requirements.txt..."
    if [ -f "requirements.txt" ]; then
        # Avoid uninstall errors for distutils packages shipped by apt
        "$PIP_CMD" install --break-system-packages --ignore-installed -r requirements.txt
        check_command "Installing dependencies from requirements.txt" || return 1
    else
        print_error "requirements.txt not found."
        return 1
    fi

    print_info "Installing project in editable mode..."
    "$PIP_CMD" install --break-system-packages -e .
    check_command "Installing project in editable mode" || return 1

    print_success "Python dependencies installed system-wide."
}

setup_mower_service() {
    print_info "Setting up autonomous mower system service..."

    local PROJECT_ROOT_DIR
    PROJECT_ROOT_DIR=$(pwd)
    local SERVICE_TEMPLATE_FILE="scripts/autonomous-mower.service.template"
    local SERVICE_FILE_NAME="autonomous-mower.service"
    local GENERATED_SERVICE_FILE="/tmp/$SERVICE_FILE_NAME"

    # Get current user for service configuration
    local CURRENT_USER
    CURRENT_USER=$(whoami)


    # Use system-wide mower executable (installed by pip3 install -e .)
    local MOWER_EXECUTABLE_PATH="$(command -v mower)"
    if [ -z "$MOWER_EXECUTABLE_PATH" ]; then
        print_error "System-wide 'mower' executable not found. Ensure 'pip3 install -e .' was successful."
        POST_INSTALL_MESSAGES+="[ERROR] Cannot install service: System-wide 'mower' executable missing.\\n"
        POST_INSTALL_MESSAGES+="[INFO] Run the script again or manually install with 'pip3 install -e .'.\\n"
        return 1
    fi

    print_info "Service will run as user: $CURRENT_USER"
    print_info "Mower executable path: $MOWER_EXECUTABLE_PATH"
    print_info "Project root directory: $PROJECT_ROOT_DIR"
    print_info "Generating service file from template '$SERVICE_TEMPLATE_FILE'..."

    # Generate service file with proper user substitution
    sed -e "s|{{PROJECT_ROOT_DIR}}|$PROJECT_ROOT_DIR|g" \
        -e "s|{{MOWER_EXECUTABLE_PATH}}|$MOWER_EXECUTABLE_PATH|g" \
        -e "s|User=pi|User=$CURRENT_USER|g" \
        -e "s|Group=pi|Group=$CURRENT_USER|g" \
        "$SERVICE_TEMPLATE_FILE" > "$GENERATED_SERVICE_FILE"

    if [ $? -ne 0 ]; then
        print_error "Failed to generate service file from template"
        return 1
    fi
    print_info "Installing generated service file to /etc/systemd/system/$SERVICE_FILE_NAME..."
    if ! sudo cp "$GENERATED_SERVICE_FILE" "/etc/systemd/system/$SERVICE_FILE_NAME"; then
        print_error "Failed to copy service file to /etc/systemd/system/"
        rm -f "$GENERATED_SERVICE_FILE"
        return 1
    fi

    if ! sudo chmod 644 "/etc/systemd/system/$SERVICE_FILE_NAME"; then
        print_error "Failed to set service file permissions"
        return 1
    fi

    # Clean up temporary file
    rm -f "$GENERATED_SERVICE_FILE"

    print_info "Reloading systemd daemon..."
    if ! sudo systemctl daemon-reload; then
        print_error "Failed to reload systemd daemon"
        return 1
    fi

    print_info "Enabling autonomous mower service to start on boot..."
    if ! sudo systemctl enable "$SERVICE_FILE_NAME"; then
        print_error "Failed to enable autonomous mower service"
        print_error "You may need to enable it manually with: sudo systemctl enable $SERVICE_FILE_NAME"
        return 1
    fi

    # Verify service installation
    if systemctl is-enabled --quiet "$SERVICE_FILE_NAME" 2>/dev/null; then
        print_success "Autonomous mower service has been installed and enabled successfully!"
        POST_INSTALL_MESSAGES+="[SUCCESS] Autonomous mower service installed and enabled.\\n"
        POST_INSTALL_MESSAGES+="[INFO] Service will start automatically on system boot.\\n"
        POST_INSTALL_MESSAGES+="[INFO] Use 'sudo systemctl status $SERVICE_FILE_NAME' to check service status.\\n"
        POST_INSTALL_MESSAGES+="[INFO] Use 'sudo systemctl start $SERVICE_FILE_NAME' to start service now.\\n"
        POST_INSTALL_MESSAGES+="[INFO] Use 'sudo systemctl stop $SERVICE_FILE_NAME' to stop service.\\n"
    else
        print_warning "Service was copied but may not be properly enabled"
        POST_INSTALL_MESSAGES+="[WARNING] Service installation may not be complete. Check with 'systemctl status $SERVICE_FILE_NAME'.\\n"
    fi
}


# Function to check if Python version is 3.10 or higher (kept for backwards compatibility)
# Note: Coral TPU now always uses Python 3.9 virtual environment regardless of system Python version
is_python_version_incompatible_with_coral() {
    local python_version
    python_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    if (( $(echo "$python_version >= 3.10" | bc -l 2>/dev/null || echo "0") )); then
        return 0  # True: version is incompatible (3.10+)
    else
        return 1  # False: version is compatible (<3.10)
    fi
}

# Function to install pyenv for managing Python versions
install_pyenv() {
    print_info "Installing pyenv for Python version management..."
    
    # Install dependencies for building Python and Coral TPU support
    print_info "Installing build dependencies..."
    sudo apt-get update
    sudo apt-get install -y make build-essential libssl-dev zlib1g-dev \
        libbz2-dev libreadline-dev libsqlite3-dev wget curl llvm \
        libncursesw5-dev xz-utils tk-dev libxml2-dev libxmlsec1-dev \
        libffi-dev liblzma-dev pkg-config libhdf5-dev libatlas-base-dev \
        libopenblas-dev liblapack-dev
    
    # Install pyenv
    if [ ! -d "$HOME/.pyenv" ]; then
        print_info "Cloning pyenv repository..."
        curl https://pyenv.run | bash
        
        # Add pyenv to PATH for current session
        export PYENV_ROOT="$HOME/.pyenv"
        [[ -d $PYENV_ROOT/bin ]] && export PATH="$PYENV_ROOT/bin:$PATH"
        eval "$(pyenv init -)"
        
        # Add pyenv to shell profile
        {
            echo 'export PYENV_ROOT="$HOME/.pyenv"'
            echo '[[ -d $PYENV_ROOT/bin ]] && export PATH="$PYENV_ROOT/bin:$PATH"'
            echo 'eval "$(pyenv init -)"'
        } >> "$HOME/.bashrc"
        
        print_success "pyenv installed successfully"
    else
        print_info "pyenv already installed"
        # Ensure pyenv is available in current session
        export PYENV_ROOT="$HOME/.pyenv"
        [[ -d $PYENV_ROOT/bin ]] && export PATH="$PYENV_ROOT/bin:$PATH"
        eval "$(pyenv init -)"
    fi
}

# Function to setup Python 3.9 virtual environment for Coral TPU
setup_coral_python_env() {
    local coral_env_dir="$HOME/.coral-python-env"
    local python_version="3.9.18"  # Latest stable 3.9.x
    
    print_info "Setting up Python 3.9 environment for Coral TPU..."
    
    # Ensure pyenv is available
    export PYENV_ROOT="$HOME/.pyenv"
    [[ -d $PYENV_ROOT/bin ]] && export PATH="$PYENV_ROOT/bin:$PATH"
    eval "$(pyenv init -)"
    
    # Install Python 3.9 if not already installed
    if ! pyenv versions --bare | grep -q "^$python_version\$"; then
        print_info "Installing Python $python_version via pyenv (this may take 10-15 minutes)..."
        pyenv install "$python_version"
        check_command "Installing Python $python_version" || {
            print_error "Failed to install Python $python_version"
            return 1
        }
    else
        print_info "Python $python_version already installed"
    fi
    
    # Create virtual environment for Coral
    if [ ! -d "$coral_env_dir" ]; then
        print_info "Creating Coral Python environment..."
        "$HOME/.pyenv/versions/$python_version/bin/python" -m venv "$coral_env_dir"
        check_command "Creating Coral virtual environment" || {
            print_error "Failed to create Coral virtual environment"
            return 1
        }
    else
        print_info "Coral Python environment already exists"
    fi
    
    # Activate the environment and install Coral dependencies
    print_info "Installing Coral dependencies in Python 3.9 environment..."
    source "$coral_env_dir/bin/activate"
    
    # Upgrade pip, wheel, and setuptools first
    print_info "Upgrading build tools..."
    python -m pip install --upgrade pip wheel setuptools
    
    # Install Coral TPU runtime (system packages must be installed first)
    print_info "Installing Edge TPU runtime packages..."
    if [ ! -f "/etc/apt/sources.list.d/coral-edgetpu.list" ]; then
        echo "deb https://packages.cloud.google.com/apt coral-edgetpu-stable main" | sudo tee /etc/apt/sources.list.d/coral-edgetpu.list
        curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key add -
        sudo apt-get update
    fi
    
    # Install system-level Edge TPU runtime
    sudo apt-get install -y libedgetpu1-std
    check_command "Installing Edge TPU runtime" || {
        print_error "Failed to install Edge TPU runtime"
        deactivate
        return 1
    }
    
    # Critical: Install dependencies in specific order to avoid PyCoral import errors
    print_info "Installing dependencies with strict version compatibility..."
    
    # Step 1: Install NumPy first with a version known to work with PyCoral
    print_info "Uninstalling any previous numpy, tflite-runtime, pycoral..."
    python -m pip uninstall -y numpy tflite-runtime pycoral || true
    print_info "Installing NumPy 2.3.0 (known compatible version)..."
    python -m pip install "numpy==2.3.0"
    check_command "Installing compatible NumPy" || {
        print_error "Failed to install compatible NumPy version"
        deactivate
        return 1
    }
    
    # Step 2: Install other base dependencies 
    print_info "Installing other base dependencies..."
    python -m pip install "pillow>=8.0.0,<10.0.0" "setuptools>=50.0.0,<69.0.0"
    check_command "Installing base dependencies" || {
        print_error "Failed to install base dependencies"
        deactivate
        return 1
    }
    
    # Step 3: Install TFLite runtime (must be before PyCoral)
    print_info "Installing TensorFlow Lite runtime..."
    python -m pip install "tflite-runtime==2.14.0"
    check_command "Installing TFLite runtime" || {
        print_error "Failed to install TFLite runtime"
        deactivate
        return 1
    }
    
    # Step 4: Verify NumPy installation before PyCoral
    print_info "Verifying NumPy installation..."
    python -c "
import numpy as np
import sys
print(f'NumPy version: {np.__version__}')
print(f'NumPy location: {np.__file__}')
# Test array operations to ensure NumPy is working
arr = np.array([1, 2, 3])
print(f'NumPy test array: {arr}')
print('NumPy verification successful')
" || {
        print_error "NumPy verification failed"
        deactivate
        return 1
    }
    
    # Step 5: Install PyCoral with explicit dependency handling
    print_info "Installing PyCoral with strict dependencies..."
    # Use --no-deps to prevent pip from upgrading NumPy
    python -m pip install --no-deps --extra-index-url https://google-coral.github.io/py-repo/ "pycoral==2.0.0"
    check_command "Installing PyCoral (no-deps)" || {
        print_error "Failed to install PyCoral"
        deactivate
        return 1
    }
    
    # Step 6: Install remaining PyCoral dependencies manually
    print_info "Installing PyCoral dependencies manually..."
    python -m pip install "six>=1.15.0"
    check_command "Installing PyCoral dependencies" || {
        print_error "Failed to install PyCoral dependencies"
        deactivate
        return 1
    }
    
    # Enhanced diagnostic test with better error reporting
    print_info "Testing PyCoral installation with comprehensive diagnostics..."
    if python -c "
import sys
import os
print(f'============ Coral Environment Diagnostics ============')
print(f'Python executable: {sys.executable}')
print(f'Python version: {sys.version}')
print(f'Python path: {sys.path}')
print()

# Test NumPy with detailed error reporting
print('Testing NumPy...')
try:
    import numpy as np
    print(f'✓ NumPy version: {np.__version__} (location: {np.__file__})')
    # Test array operations
    test_arr = np.array([1, 2, 3])
    print(f'✓ NumPy array operations working: {test_arr.sum()}')
except Exception as e:
    print(f'✗ NumPy test failed: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test TFLite runtime
print()
print('Testing TensorFlow Lite runtime...')
try:
    import tflite_runtime as tflite
    print(f'✓ TFLite runtime version: {tflite.__version__} (location: {tflite.__file__})')
except Exception as e:
    print(f'✗ TFLite runtime test failed: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test PyCoral import with detailed diagnostics
print()
print('Testing PyCoral import...')
try:
    import pycoral
    print(f'✓ PyCoral base import successful (location: {pycoral.__file__})')
    
    # Test EdgeTPU utilities specifically
    import pycoral.utils.edgetpu as edgetpu_utils
    print(f'✓ PyCoral EdgeTPU utils import successful')
    
    # Test actual EdgeTPU functionality
    print('Testing EdgeTPU detection...')
    interpreters = edgetpu_utils.list_edge_tpus()
    print(f'✓ EdgeTPU detection successful: Found {len(interpreters)} TPU(s)')
    
    if interpreters:
        for i, interpreter in enumerate(interpreters):
            print(f'  TPU {i}: {interpreter}')
    else:
        print('  No EdgeTPU devices detected (this is normal if no hardware is connected)')
    
except Exception as e:
    print(f'✗ PyCoral test failed: {e}')
    print(f'Error type: {type(e).__name__}')
    import traceback
    traceback.print_exc()
    
    # Additional diagnostics for common issues
    print()
    print('=== Additional Diagnostics ===')
    try:
        import numpy as np
        print(f'NumPy _ARRAY_API available: {hasattr(np, \"_ARRAY_API\")}')
    except:
        pass
        
    print('Checking for libedgetpu...')
    libedgetpu_paths = [
        '/usr/lib/aarch64-linux-gnu/libedgetpu.so.1',
        '/usr/lib/arm-linux-gnueabihf/libedgetpu.so.1',
        '/usr/lib/x86_64-linux-gnu/libedgetpu.so.1'
    ]
    for path in libedgetpu_paths:
        if os.path.exists(path):
            print(f'✓ Found libedgetpu at: {path}')
            break
    else:
        print('✗ libedgetpu not found in standard locations')
    
    sys.exit(1)

print()
print('============ All Tests Passed ============')
"; then
        print_success "✓ PyCoral installed and working in Python 3.9 environment"
        
        # Create activation script for easy access
        cat > "$HOME/activate-coral-env.sh" << 'EOF'
#!/bin/bash
# Activate the Coral Python 3.9 environment
source "$HOME/.coral-python-env/bin/activate"
echo "========================================="
echo "Coral Python 3.9 environment activated"
echo "========================================="
echo "Python version: $(python --version)"
echo "NumPy version: $(python -c 'import numpy; print(numpy.__version__)' 2>/dev/null || echo 'Not available')"
echo "TFLite runtime: $(python -c 'import tflite_runtime; print("Available")' 2>/dev/null || echo 'Not available')"
echo "PyCoral status: $(python -c 'import pycoral.utils.edgetpu; print("Available")' 2>/dev/null || echo 'Not available')"
echo "Edge TPUs detected: $(python -c 'import pycoral.utils.edgetpu; print(len(pycoral.utils.edgetpu.list_edge_tpus()))' 2>/dev/null || echo 'Unknown')"
echo "========================================="
echo "Environment ready for Coral TPU development"
echo "Deactivate with: deactivate"
echo "========================================="
EOF
        chmod +x "$HOME/activate-coral-env.sh"
        
        print_info "Created activation script: ~/activate-coral-env.sh"
        POST_INSTALL_MESSAGES+="[SUCCESS] Coral TPU environment set up with Python 3.9\\n"
        POST_INSTALL_MESSAGES+="[INFO] Use 'source ~/activate-coral-env.sh' to activate Coral environment\\n"
        POST_INSTALL_MESSAGES+="[INFO] Coral environment location: $coral_env_dir\\n"
    else
        print_error "PyCoral installation failed"
        deactivate
        return 1
    fi
    
    deactivate
    return 0
}

# Function to test Coral TPU installation in the dedicated environment
test_coral_installation() {
    local coral_env_dir="$HOME/.coral-python-env"
    
    if [ ! -d "$coral_env_dir" ]; then
        print_error "Coral Python environment not found"
        return 1
    fi
    
    print_info "Testing Coral TPU installation..."
    
    # Test in the dedicated environment
    source "$coral_env_dir/bin/activate"
    
    # Test PyCoral import
    if python -c "import pycoral.utils.edgetpu; print('✓ PyCoral import successful')"; then
        print_success "PyCoral is working in the dedicated environment"
        
        # Test hardware detection
        if lsusb | grep -q "1a6e:089a"; then
            print_success "✓ Coral USB Accelerator detected"
            # Test actual TPU access
            if python -c "
from pycoral.utils import edgetpu
try:
    interpreters = edgetpu.list_edge_tpus()
    if interpreters:
        print(f'✓ Found {len(interpreters)} Coral TPU(s)')
    else:
        print('⚠ No Coral TPU detected (may need udev trigger)')
except Exception as e:
    print(f'⚠ Coral TPU access error: {e}')
"; then
                print_success "Coral TPU hardware test completed"
            fi
        else
            print_warning "No Coral USB Accelerator detected via lsusb"
            print_info "If you have a Coral TPU, ensure it's connected and run: sudo udevadm trigger"
        fi
    else
        print_error "PyCoral import failed in dedicated environment"
        deactivate
        return 1
    fi
    
    deactivate
    return 0
}

# Function to show available installation features
show_available_features() {
    echo ""
    print_info "Available installation features:"
    echo ""
    echo "  Core System:"
    echo "    1.  Hardware Interfaces (I2C, UART, Camera validation)"
    echo "    2.  Additional UART (UART2 setup)"
    echo "    3.  System Packages (i2c-tools, gpsd, etc.)"
    echo "    4.  PYTHONPATH Configuration"
    echo "    5.  Python Dependencies (from requirements.txt)"
    echo ""
    echo "  Computer Vision & AI:"
    echo "    7.  YOLOv8 Models (obstacle detection)"
    echo "    8.  Coral TPU Support (Edge TPU acceleration)"
    echo ""
    echo "  System Integration:"
    echo "    9.  Hardware Watchdog (system reliability)"
    echo "    10. Emergency Stop Button (GPIO7 safety)"
    echo "    11. Systemd Service (auto-startup)"
    echo ""
}

# Function to install specific feature by number
install_specific_feature() {
    local feature_num="$1"

    case "$feature_num" in
        1)
            print_info "Installing Hardware Interfaces..."
            enable_required_interfaces
            validate_hardware
            mark_step_completed "hardware_interfaces"
            ;;
        2)
            print_info "Installing Additional UART..."
            setup_additional_uart
            mark_step_completed "additional_uart"
            ;;
        3)
            print_info "Installing System Packages..."
            print_info "Updating package lists and installing essential system dependencies..."
            sudo apt-get update && sudo apt-get upgrade -y && sudo apt-get autoremove -y
            check_command "Updating package list and upgrading system" || return 1

            # Base packages for all systems
            local base_packages=(
                "python3-pip" "python3-dev" "python3-setuptools" "python3-wheel"
                "git" "libatlas-base-dev" "libhdf5-dev"
                "libportaudio2" "libportaudiocpp0" "portaudio19-dev"
                "build-essential" "pkg-config"
                "wget" "curl" "gnupg"
                "gdal-bin" "libgdal-dev" "python3-gdal"
            )

            # Pi-specific packages
            local pi_packages=(
                "i2c-tools"
                "gpsd" "gpsd-clients" "python3-gps"
                "python3-libgpiod"
                "python3-picamera2"
            )

            # Install base packages
            print_info "Installing base system packages..."
            sudo apt-get install -y "${base_packages[@]}"
            check_command "Installing base system packages" || return 1

            # Install Pi-specific packages only on Raspberry Pi
            if [ "$IS_PI" = true ]; then
                print_info "Installing Raspberry Pi specific packages..."
                sudo apt-get install -y "${pi_packages[@]}"
                check_command "Installing Pi-specific packages" || print_warning "Some Pi-specific packages may have failed to install"
            else
                print_info "Skipping Pi-specific packages on non-Pi system."
            fi

            print_success "Essential system dependencies installed."
            mark_step_completed "system_packages"
            ;;
        4)
            print_info "Installing PYTHONPATH Configuration..."
            PROJECT_ROOT_DIR_FOR_PYTHONPATH=$(pwd)
            BASHRC_FILE="$HOME/.bashrc"

            # Use appropriate shell config file for current user
            if [ "$IS_PI" = false ]; then
                print_info "Non-Pi system detected. Setting up PYTHONPATH for current user: $USER"
            else
                print_info "Setting up permanent PYTHONPATH in $BASHRC_FILE to include ${PROJECT_ROOT_DIR_FOR_PYTHONPATH}/src..."
            fi

            if ! grep -q "PYTHONPATH.*${PROJECT_ROOT_DIR_FOR_PYTHONPATH}/src" "$BASHRC_FILE" 2>/dev/null; then
                echo "" >> "$BASHRC_FILE"
                echo "# Autonomous Mower Python Path" >> "$BASHRC_FILE"
                echo "export PYTHONPATH=\"${PROJECT_ROOT_DIR_FOR_PYTHONPATH}/src:\${PYTHONPATH}\"" >> "$BASHRC_FILE"
                print_success "Added PYTHONPATH to $BASHRC_FILE."
                POST_INSTALL_MESSAGES+="[INFO] PYTHONPATH updated in $BASHRC_FILE. Source it or re-login.\\n"
            else
                print_info "PYTHONPATH already configured in $BASHRC_FILE."
            fi
            mark_step_completed "pythonpath_setup"
            ;;
        5)
            print_info "Installing Python Dependencies..."
            install_python_dependencies
            mark_step_completed "python_dependencies"
            ;;
        6)
            # Option 6 is reserved/skipped in the current implementation
            print_warning "Option 6 is not currently implemented."
            print_info "This slot is reserved for future features."
            return 0
            ;;
        7)
            print_info "Installing YOLOv8 Models..."
            setup_yolov8
            mark_step_completed "yolov8_setup"
            ;;
        8)
            print_info "Installing Coral TPU Support..."
            CORAL_INSTALLED_OK=false
            if ! lsusb | grep -q -E "1a6e:089a|18d1:9302"; then
                print_warning "Coral TPU not detected via lsusb. Ensure it's connected."
                POST_INSTALL_MESSAGES+="[WARNING] Coral TPU not detected. If you have one, ensure it's connected.\\n"
                prompt_user "Continue Coral TPU software installation anyway?" "n" "y/n"
                if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                    print_info "Skipping Coral TPU software installation."
                    return 0
                else
                    print_info "Proceeding with Coral software installation despite no device detected."
                    CORAL_INSTALLED_OK=true
                fi
            else
                CORAL_INSTALLED_OK=true
            fi

            if $CORAL_INSTALLED_OK; then
                print_info "Setting up Coral TPU with Python 3.9 virtual environment..."
                print_info "Following official Coral documentation: Always use Python 3.9 for best compatibility."
                
                # Install pyenv if needed
                install_pyenv
                check_command "Installing pyenv" || {
                    print_error "Failed to install pyenv"
                    POST_INSTALL_MESSAGES+="[ERROR] Failed to install pyenv for Python 3.9 environment.\\n"
                    return 1
                }
                
                # Set up Python 3.9 environment for Coral (official recommendation)
                setup_coral_python_env
                check_command "Setting up Coral Python 3.9 environment" || {
                    print_error "Failed to set up Coral Python 3.9 environment"
                    POST_INSTALL_MESSAGES+="[ERROR] Failed to set up Python 3.9 environment for Coral.\\n"
                    return 1
                }
                
                print_success "Coral TPU support installed in Python 3.9 environment"
                POST_INSTALL_MESSAGES+="[SUCCESS] Coral TPU installed in Python 3.9 environment.\\n"
                POST_INSTALL_MESSAGES+="[INFO] Use 'source ~/activate-coral-env.sh' to activate Coral environment.\\n"
                POST_INSTALL_MESSAGES+="[INFO] See docs/coral_setup.md for usage instructions.\\n"
            fi
            print_success "Coral TPU support setup attempted."
            mark_step_completed "coral_tpu_setup"
            ;;
        9)
            print_info "Installing Hardware Watchdog..."
            setup_watchdog
            mark_step_completed "hardware_watchdog"
            ;;
        10)
            print_info "Installing Emergency Stop Button..."
            setup_emergency_stop
            mark_step_completed "emergency_stop"
            ;;
        11)
            print_info "Installing Systemd Service..."
            setup_mower_service
            mark_step_completed "systemd_service"
            ;;
        *)
            print_error "Invalid feature number: $feature_num"
            return 1
            ;;
    esac
}

# Function to show installation mode menu
show_installation_menu() {
    echo ""
    echo "==============================================================================="
    print_info "         Autonomous Mower Installation Script"
    echo "==============================================================================="
    echo ""

    # Show current status if checkpoints exist
    if [ -f "$CHECKPOINT_FILE" ]; then
        print_info "Current Installation Status:"
        list_completed_steps
        echo ""
    fi

    echo "Installation Modes:"
    echo ""
    echo "  1. Fresh Installation (install everything from scratch)"
    echo "  2. Continue Installation (resume where you left off)"
    echo "  3. Specific Feature Installation (install individual components)"
    echo "  4. Show Installation Status (view current progress)"
    echo "  5. Exit"
    echo ""
}

# Function to handle specific feature installation menu
handle_specific_feature_menu() {
    while true; do
        show_available_features
        echo ""
        prompt_selection "Enter feature number to install (1-11), 'a' for all remaining, or 'q' to return to main menu:" "a"

        case "$choice" in
            [1-9])
                install_specific_feature "$choice"
                if [ $? -eq 0 ]; then
                    print_success "Feature $choice installation completed."
                else
                    print_error "Feature $choice installation failed."
                fi
                echo ""
                prompt_continue "Press Enter to continue..."
                ;;
            10|11)
                install_specific_feature "$choice"
                if [ $? -eq 0 ]; then
                    print_success "Feature $choice installation completed."
                else
                    print_error "Feature $choice installation failed."
                fi
                echo ""                ;;
            a|A)
                print_info "Installing all remaining features..."
                run_full_installation
                break
                ;;
            q|Q)
                break
                ;;
            *)
                print_error "Invalid choice. Please enter a number 1-11, 'a', or 'q'."
                ;;
        esac
    done
}

# Function to run the full installation logic
run_full_installation() {
    # Auto-detect completed steps if not starting fresh
    if [ -f "$CHECKPOINT_FILE" ]; then
        auto_detect_completed_steps
    fi

    if ! command_exists python3; then
        print_error "Python 3 is not installed. Please install Python 3 (>=3.9) and try again."
        exit 1
    fi

    if ! command_exists pip3; then
        print_error "pip3 is not installed system-wide. Please install python3-pip."
        exit 1
    fi
    print_success "Basic system checks (python3) passed."

    list_completed_steps

    if ! prompt_skip_completed "hardware_interfaces" "Hardware interfaces configuration"; then
        enable_required_interfaces
        validate_hardware
        mark_step_completed "hardware_interfaces"
    fi
    prompt_user "Do you want to attempt to set up an additional UART (UART2 on primary GPIOs)?" "y" "y/n"
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        if ! prompt_skip_completed "additional_uart" "Additional UART setup"; then
            setup_additional_uart
            mark_step_completed "additional_uart"
        fi
    else
        print_info "Skipping additional UART setup."
    fi

    if ! prompt_skip_completed "system_packages" "System packages installation"; then
        print_info "Updating package lists and installing essential system dependencies..."
        sudo apt-get update && sudo apt-get upgrade -y && sudo apt-get autoremove -y
        check_command "Updating package list and upgrading system" || exit 1

        # Base packages for all systems
        local base_packages=(
            "python3-pip" "python3-dev" "python3-setuptools" "python3-wheel"
            "git" "libatlas-base-dev" "libhdf5-dev"
            "libportaudio2" "libportaudiocpp0" "portaudio19-dev"
            "wget" "curl" "gnupg" "bc"
            "gdal-bin" "libgdal-dev" "python3-gdal"
        )

        # Pi-specific packages
        local pi_packages=(
            "i2c-tools"
            "gpsd" "gpsd-clients" "python3-gps"
            "python3-libgpiod"
            "python3-picamera2"
        )

        # Install base packages
        print_info "Installing base system packages..."
        sudo apt-get install -y "${base_packages[@]}"
        check_command "Installing base system packages" || exit 1

        # Install Pi-specific packages only on Raspberry Pi
        if [ "$IS_PI" = true ]; then
            print_info "Installing Raspberry Pi specific packages..."
            sudo apt-get install -y "${pi_packages[@]}"
            check_command "Installing Pi-specific packages" || print_warning "Some Pi-specific packages may have failed to install"
        else
            print_info "Skipping Pi-specific packages (i2c-tools, gpsd, python3-libgpiod, python3-picamera2) on non-Pi system."
            POST_INSTALL_MESSAGES+="[INFO] Pi-specific hardware packages were skipped on non-Pi system.\\n"
        fi

        print_success "Essential system dependencies installed."
        mark_step_completed "system_packages"
    fi

    # PYTHONPATH setup - see note in original code about editable installs
    if ! prompt_skip_completed "pythonpath_setup" "PYTHONPATH configuration"; then
        PROJECT_ROOT_DIR_FOR_PYTHONPATH=$(pwd)
        BASHRC_FILE="$HOME/.bashrc"

        # Use appropriate shell config file for current user
        if [ "$IS_PI" = false ]; then
            print_info "Non-Pi system detected. Setting up PYTHONPATH for current user: $USER"
        else
            print_info "Setting up permanent PYTHONPATH in $BASHRC_FILE to include ${PROJECT_ROOT_DIR_FOR_PYTHONPATH}/src..."
        fi

        if ! grep -q "PYTHONPATH.*${PROJECT_ROOT_DIR_FOR_PYTHONPATH}/src" "$BASHRC_FILE" 2>/dev/null; then
            echo "" >> "$BASHRC_FILE"
            echo "# Autonomous Mower Python Path" >> "$BASHRC_FILE"
            echo "export PYTHONPATH=\"${PROJECT_ROOT_DIR_FOR_PYTHONPATH}/src:\${PYTHONPATH}\"" >> "$BASHRC_FILE"
            print_success "Added PYTHONPATH to $BASHRC_FILE."
            POST_INSTALL_MESSAGES+="[INFO] PYTHONPATH updated in $BASHRC_FILE. Source it or re-login.\\n"
        else
            print_info "PYTHONPATH already configured in $BASHRC_FILE."
        fi
        mark_step_completed "pythonpath_setup"
    fi

    if ! prompt_skip_completed "python_dependencies" "Python dependencies installation"; then
        install_python_dependencies
        mark_step_completed "python_dependencies"
    fi

    prompt_user "Do you want to install/configure YOLOv8 models?" "y" "y/n"
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        if ! prompt_skip_completed "yolov8_setup" "YOLOv8 models installation"; then
            setup_yolov8
            mark_step_completed "yolov8_setup"
        fi
    else
        print_info "Skipping YOLOv8 model setup."
        POST_INSTALL_MESSAGES+="[INFO] YOLOv8 model setup was skipped.\\n"
    fi

    prompt_user "Do you want to install Coral TPU support (requires Coral USB Accelerator)?" "y" "y/n"
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        if ! prompt_skip_completed "coral_tpu_setup" "Coral TPU support installation"; then
            print_info "Installing Coral TPU support..."
            CORAL_INSTALLED_OK=false
            if ! lsusb | grep -q -E "1a6e:089a|18d1:9302"; then
                print_warning "Coral TPU not detected via lsusb. Ensure it's connected."
                POST_INSTALL_MESSAGES+="[WARNING] Coral TPU not detected. If you have one, ensure it's connected.\\n"
                prompt_user "Continue Coral TPU software installation anyway?" "n" "y/n"
                if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                    print_info "Skipping Coral TPU software installation."
                else
                    print_info "Proceeding with Coral software installation despite no device detected."
                    CORAL_INSTALLED_OK=true
                fi
            else
                CORAL_INSTALLED_OK=true
            fi

            if $CORAL_INSTALLED_OK; then
                print_info "Setting up Coral TPU with Python 3.9 virtual environment..."
                print_info "Following official Coral documentation: Always use Python 3.9 for best compatibility."
                
                # Install pyenv if needed
                install_pyenv
                check_command "Installing pyenv" || {
                    print_error "Failed to install pyenv"
                    POST_INSTALL_MESSAGES+="[ERROR] Failed to install pyenv for Python 3.9 environment.\\n"
                    return 1
                }
                
                # Set up Python 3.9 environment for Coral (official recommendation)
                setup_coral_python_env
                check_command "Setting up Coral Python 3.9 environment" || {
                    print_error "Failed to set up Coral Python 3.9 environment"
                    POST_INSTALL_MESSAGES+="[ERROR] Failed to set up Python 3.9 environment for Coral.\\n"
                    return 1
                }
                
                print_success "Coral TPU support installed in Python 3.9 environment"
                POST_INSTALL_MESSAGES+="[SUCCESS] Coral TPU installed in Python 3.9 environment.\\n"
                POST_INSTALL_MESSAGES+="[INFO] Use 'source ~/activate-coral-env.sh' to activate Coral environment.\\n"
                POST_INSTALL_MESSAGES+="[INFO] See docs/coral_setup.md for usage instructions.\\n"
            fi
            print_success "Coral TPU support setup attempted."
            mark_step_completed "coral_tpu_setup"
        fi
    else
        print_info "Skipping Coral TPU support installation."
    fi
    prompt_user "Do you want to setup the hardware watchdog?" "y" "y/n"
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        if ! prompt_skip_completed "hardware_watchdog" "Hardware watchdog setup"; then
            setup_watchdog
            mark_step_completed "hardware_watchdog"
        fi
    else
        print_info "Skipping hardware watchdog setup."
    fi

    prompt_user "Do you want to setup a physical emergency stop button (GPIO7)?" "y" "y/n"
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        if ! prompt_skip_completed "emergency_stop" "Emergency stop button setup"; then
            setup_emergency_stop
            mark_step_completed "emergency_stop"
        fi
    else
        if ! prompt_skip_completed "emergency_stop_skip" "Emergency stop button disable"; then
            skip_physical_emergency_stop
            mark_step_completed "emergency_stop_skip"
        fi
    fi

    prompt_user "Do you want to install and enable the systemd service for automatic startup?" "y" "y/n"
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        if ! prompt_skip_completed "systemd_service" "Systemd service installation"; then
            setup_mower_service
            mark_step_completed "systemd_service"
        fi
    else
        print_info "Skipping systemd service installation."
        POST_INSTALL_MESSAGES+="[INFO] Systemd service not installed. Configure manually if needed.\\n"
    fi
    print_success "Full installation completed successfully."

    # Add host-specific completion messages
    if [ "$IS_PI" = false ]; then
        POST_INSTALL_MESSAGES+="[INFO] Installation completed on non-Raspberry Pi system. Pi-specific hardware features were skipped.\\n"
        POST_INSTALL_MESSAGES+="[IMPORTANT] The autonomous mower application requires actual Raspberry Pi hardware to function fully.\\n"
        POST_INSTALL_MESSAGES+="[INFO] For development/testing purposes, you can run: python -m src.mower.main_controller --dry-run\\n"
    fi

    POST_INSTALL_MESSAGES+="[SUCCESS] Full installation completed successfully.\\n"
    return 0
}

# Function to show installation summary and cleanup checkpoints on success
show_installation_summary() {
    echo ""
    print_info "Installation Summary:"
    echo ""

    if [ -f "$CHECKPOINT_FILE" ]; then
        local total_steps=0
        local completed_steps=0

        # Count total possible steps
        local all_steps=("hardware_interfaces" "additional_uart" "system_packages" "pythonpath_setup" "python_dependencies" "yolov8_setup" "coral_tpu_setup" "hardware_watchdog" "emergency_stop" "emergency_stop_skip" "systemd_service")
        total_steps=${#all_steps[@]}

        # Count completed steps
        for step in "${all_steps[@]}"; do
            if is_step_completed "$step"; then
                ((completed_steps++))
            fi
        done

        echo -e "  ${GREEN}Completed steps: $completed_steps/$total_steps${NC}"
        echo ""

        # Show completed steps
        print_info "Completed installation steps:"
        while IFS='=' read -r step timestamp; do
            echo -e "  ${GREEN}✓${NC} $step (completed: $timestamp)"
        done < "$CHECKPOINT_FILE"
    fi
}

# Function to cleanup checkpoints on successful completion
cleanup_checkpoints() {
    if [ -f "$CHECKPOINT_FILE" ]; then
        print_info "Installation completed successfully. Cleaning up checkpoint file..."
        mv "$CHECKPOINT_FILE" "${CHECKPOINT_FILE}.completed.$(date '+%Y%m%d_%H%M%S')"
        print_success "Checkpoint file archived for reference."
    fi
}

# --- Main Installation Logic ---
print_info "Starting Autonomous Mower installation script..."

# Show host detection status
if [ "$IS_PI" = true ]; then
    print_info "✓ Raspberry Pi system detected - full hardware support available"
else
    print_warning "⚠ Non-Raspberry Pi system detected"
    print_info "  This installation will skip Pi-specific hardware features:"
    print_info "  - I2C/UART interface configuration"
    print_info "  - Hardware watchdog setup"
    print_info "  - Pi-specific system packages (gpsd, i2c-tools, python3-picamera2, etc.)"
    print_info "  - Boot configuration changes (config.txt modifications)"
    print_info "  This is suitable for development/testing but the mower will only run properly on Pi hardware."
    echo ""
fi

# Show non-interactive mode message if enabled
if [ "$NON_INTERACTIVE" = true ]; then
    print_info "Running in non-interactive mode - all prompts will default to 'yes'"
fi

# Main installation menu loop
while true; do
    show_installation_menu

    prompt_selection "Please select an installation mode (1-5):" "1"

    case "$choice" in
        1)
            print_info "Starting fresh installation..."
            if [ -f "$CHECKPOINT_FILE" ]; then
                print_warning "Removing existing checkpoint file for fresh installation..."
                rm -f "$CHECKPOINT_FILE"
            fi
            run_full_installation
            print_success "Fresh installation completed."
            show_installation_summary
            cleanup_checkpoints
            break
            ;;
        2)
            if [ -f "$CHECKPOINT_FILE" ]; then
                print_info "Continuing previous installation..."
                run_full_installation
            else
                print_info "No previous installation found. Starting fresh installation..."
                run_full_installation
            fi
            print_success "Installation completed."
            show_installation_summary
            cleanup_checkpoints
            break
            ;;
        3)
            print_info "Entering specific feature installation mode..."
            handle_specific_feature_menu
            # Don't break here - return to main menu after specific features
            ;;
        4)
            echo ""
            if [ -f "$CHECKPOINT_FILE" ]; then
                list_completed_steps

                # Show uncompleted features
                echo ""
                print_info "Features not yet installed:"
        local all_features=("hardware_interfaces" "additional_uart" "system_packages" "pythonpath_setup" "python_dependencies" "yolov8_setup" "coral_tpu_setup" "hardware_watchdog" "emergency_stop" "emergency_stop_skip" "systemd_service")
                local uncompleted=()

                for feature in "${all_features[@]}"; do
                    if ! is_step_completed "$feature"; then                        uncompleted+=("$feature")
                    fi
                done

                if [ ${#uncompleted[@]} -eq 0 ]; then
                    print_success "All features appear to be installed!"
                else
                    for feature in "${uncompleted[@]}"; do
                        echo -e "  ${YELLOW}○${NC} $feature"
                    done
                fi
            else
                print_info "No installation has been started yet."
            fi
            echo ""
            prompt_continue "Press Enter to continue..."
            ;;
        5)
            print_info "Exiting installation script."
            exit 0
            ;;
        *)
            print_error "Invalid choice. Please enter a number between 1 and 5."
            echo ""
            prompt_continue "Press Enter to continue..."
            ;;
    esac
done

print_success "Installation and setup process complete."

show_installation_summary
cleanup_checkpoints

if [ -n "$POST_INSTALL_MESSAGES" ]; then
    echo -e "\\n${YELLOW}--- Important Post-Installation Notes ---${NC}"
    printf "%b" "${YELLOW}$(echo -e "$POST_INSTALL_MESSAGES" | sed 's/^/  /')${NC}\\n"
fi

print_info "A REBOOT is highly recommended for all changes to take full effect."
prompt_user "Reboot now?" "y" "y/n"
if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_info "Rebooting system..."
    sudo reboot
else
    print_info "Please reboot manually when convenient."
fi
exit 0
