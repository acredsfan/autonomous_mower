#!/bin/bash

# Exit on error
set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Global variable to collect messages for the end
POST_INSTALL_MESSAGES=""
CONFIG_TXT_FOUND_BY_ENABLE_FUNC=false

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

# Function to cleanup on script failure
cleanup() {
    print_info "Cleaning up..."
    exit 1
}

# Set trap for cleanup
trap cleanup EXIT

# Function to find the target config.txt file
get_config_txt_target() {
    local CONFIG_TXT_NEW="/boot/firmware/config.txt"
    local CONFIG_TXT_OLD="/boot/config.txt"
    if [ -f "$CONFIG_TXT_NEW" ]; then
        echo "$CONFIG_TXT_NEW"
    elif [ -f "$CONFIG_TXT_OLD" ]; then
        echo "$CONFIG_TXT_OLD"
    else
        # Return empty string if not found, let callers handle it
        echo ""
    fi
}

# Function to attempt to enable I2C and Serial interfaces
enable_required_interfaces() {
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
    # This message is always relevant if using primary UART for GPS
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
    local CONFIG_TXT_TARGET_FOR_MSG=$(get_config_txt_target) # Get config path for messages

    # Check if running on Raspberry Pi
    if ! grep -q "Raspberry Pi" /proc/cpuinfo; then
        print_error "This script must be run on a Raspberry Pi"
        exit 1
    fi

    # Check Pi model and memory
    PI_MODEL=$(tr -d '\0' < /proc/device-tree/model)
    if [[ ! "$PI_MODEL" =~ "Raspberry Pi 4" ]]; then
        print_warning "This software is optimized for Raspberry Pi 4B 4GB or better"
        print_warning "Current model: $PI_MODEL"
        read -p "Continue anyway? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi

    # Check available memory
    TOTAL_MEM=$(free -m | awk '/^Mem:/{print $2}')
    if [ "$TOTAL_MEM" -lt 3500 ]; then
        print_warning "Recommended minimum RAM is 4GB, current: ${TOTAL_MEM}MB"
        read -p "Continue anyway? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi

    # Check for required interfaces
    if ! ls /dev/i2c* >/dev/null 2>&1; then
        if $CONFIG_TXT_FOUND_BY_ENABLE_FUNC; then
            print_warning "I2C interface (/dev/i2c*) not detected. Auto-configuration was attempted. A REBOOT is likely required."
            if [ -n "$CONFIG_TXT_TARGET_FOR_MSG" ]; then
                POST_INSTALL_MESSAGES+="[WARNING] I2C interface was not active after configuration attempt. Ensure it is enabled in $CONFIG_TXT_TARGET_FOR_MSG and /etc/modules, then reboot.\\n"
            else
                POST_INSTALL_MESSAGES+="[WARNING] I2C interface was not active after configuration attempt (config.txt not found by script). Ensure it is enabled manually and /etc/modules updated, then reboot.\\n"
            fi
        else
            print_error "I2C interface not enabled. Please enable it using raspi-config and reboot."
            exit 1
        fi
    else
        print_success "I2C interface (/dev/i2c*) detected."
    fi

    if ! (ls /dev/ttyAMA0 >/dev/null 2>&1 || ls /dev/serial0 >/dev/null 2>&1); then
        if $CONFIG_TXT_FOUND_BY_ENABLE_FUNC; then
            print_warning "Primary UART (/dev/ttyAMA0 or /dev/serial0) not detected. Auto-configuration was attempted. A REBOOT is likely required."
            if [ -n "$CONFIG_TXT_TARGET_FOR_MSG" ]; then
                POST_INSTALL_MESSAGES+="[WARNING] Primary UART was not active after configuration attempt. Ensure it is enabled in $CONFIG_TXT_TARGET_FOR_MSG (and serial console disabled for GPS use), then reboot.\\n"
            else
                POST_INSTALL_MESSAGES+="[WARNING] Primary UART was not active after configuration attempt (config.txt not found by script). Ensure it is enabled manually (and serial console disabled for GPS use), then reboot.\\n"
            fi
        else
            print_error "Serial interface not enabled. Please enable it using raspi-config (and disable serial console if using for GPS) and reboot."
            exit 1
        fi
    else
        print_success "Primary UART (/dev/ttyAMA0 or /dev/serial0) detected."
    fi

    # Check for camera module
    if ! ls /dev/video* >/dev/null 2>&1; then
        print_warning "No camera devices found in /dev/video*"
        print_warning "This could mean:"
        print_warning "1. Camera module is not connected"
        print_warning "2. Camera module is not enabled"
        print_warning "3. Using a newer Pi OS where camera appears differently"
        read -p "Continue anyway? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    else
        print_info "Camera device(s) found: $(ls /dev/video*)"
    fi

    # Additional camera check using libcamera-still
    if command_exists libcamera-still; then
        print_info "Testing camera with libcamera-still..."
        if ! timeout 2 libcamera-still --immediate --timeout 1 -o /dev/null 2>/dev/null; then
            print_warning "libcamera-still test failed. Camera might not be working."
            read -p "Continue anyway? (y/n) " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                exit 1
            fi
        else
            print_success "Camera test with libcamera-still succeeded"
        fi
    fi
}

# Function to setup an additional UART
setup_additional_uart() {
    print_info "Setting up additional UART (UART2)..."
    # Note: dtoverlay=uart2 typically uses GPIOs 0, 1 (TXD2, RXD2) and 2, 3 (CTS2, RTS2).
    # These pins might conflict with other interfaces like I2C0 or specific camera functions
    # depending on the Raspberry Pi model and configuration.
    # Verify pinouts and potential conflicts for your specific setup.
    # Other options for additional UARTs include uart3, uart4, uart5 with different GPIO assignments.
    local DTOVERLAY_ENTRY="dtoverlay=uart2"
    local CONFIG_TXT_NEW="/boot/firmware/config.txt"
    local CONFIG_TXT_OLD="/boot/config.txt"
    local CONFIG_TXT_TARGET=""

    if [ -f "$CONFIG_TXT_NEW" ]; then
        CONFIG_TXT_TARGET="$CONFIG_TXT_NEW"
    elif [ -f "$CONFIG_TXT_OLD" ]; then
        CONFIG_TXT_TARGET="$CONFIG_TXT_OLD"
    else
        print_error "Boot configuration file (config.txt) not found at $CONFIG_TXT_NEW or $CONFIG_TXT_OLD."
        print_warning "Skipping additional UART setup."
        return 1
    fi

    print_info "Target boot configuration file: $CONFIG_TXT_TARGET"

    if sudo grep -q "^${DTOVERLAY_ENTRY}" "$CONFIG_TXT_TARGET"; then
        print_info "UART2 overlay ('${DTOVERLAY_ENTRY}') already exists in $CONFIG_TXT_TARGET."
    else
        print_info "Backing up $CONFIG_TXT_TARGET to ${CONFIG_TXT_TARGET}.bak_uart_setup..."
        sudo cp "$CONFIG_TXT_TARGET" "${CONFIG_TXT_TARGET}.bak_uart_setup_$(date +%Y%m%d_%H%M%S)"
        if [ $? -ne 0 ]; then
            print_error "Failed to backup $CONFIG_TXT_TARGET. Aborting UART setup."
            return 1
        fi

        print_info "Adding '${DTOVERLAY_ENTRY}' to $CONFIG_TXT_TARGET..."
        echo "${DTOVERLAY_ENTRY}" | sudo tee -a "$CONFIG_TXT_TARGET" > /dev/null
        if [ $? -ne 0 ]; then
            print_error "Failed to add '${DTOVERLAY_ENTRY}' to $CONFIG_TXT_TARGET."
            print_warning "You may need to add it manually."
            return 1
        else
            print_success "Successfully added '${DTOVERLAY_ENTRY}' to $CONFIG_TXT_TARGET."
            print_warning "A REBOOT is required for the UART2 changes to take effect."
        fi
    fi
}

# Function to setup watchdog
setup_watchdog() {
    print_info "Setting up hardware watchdog..."
    sudo modprobe bcm2835_wdt
    echo "bcm2835_wdt" | sudo tee -a /etc/modules
    sudo apt-get install -y watchdog
    # Configure watchdog
    sudo sed -i 's/#max-load-1/max-load-1/' /etc/watchdog.conf
    sudo sed -i 's/#watchdog-device/watchdog-device/' /etc/watchdog.conf
    echo "watchdog-timeout = 15" | sudo tee -a /etc/watchdog.conf
    sudo systemctl enable watchdog
    sudo systemctl start watchdog
}

# Function to setup emergency stop
setup_emergency_stop() {
    # Ask if the user wants to set up a physical emergency stop button
    echo ""
    echo "The emergency stop button is an optional hardware component."
    echo "It provides a physical button to immediately stop all operations."
    echo "If not installed, emergency stop functionality is still available through the web interface."
    echo ""
    read -p "Do you want to configure a physical emergency stop button? (y/n): " setup_estop
    
    if [[ $setup_estop =~ ^[Yy]$ ]]; then
        print_info "Setting up emergency stop button..."
        # Add udev rule for GPIO access
        echo 'SUBSYSTEM=="gpio", KERNEL=="gpiochip*", GROUP="gpio", MODE="0660"' | sudo tee /etc/udev/rules.d/99-gpio.rules
        echo 'SUBSYSTEM=="input", GROUP="input", MODE="0660"' | sudo tee -a /etc/udev/rules.d/99-gpio.rules
        
        # Configure GPIO7 for emergency stop
        echo "7" | sudo tee /sys/class/gpio/export
        echo "in" | sudo tee /sys/class/gpio/gpio7/direction
        echo "both" | sudo tee /sys/class/gpio/gpio7/edge
        sudo chown -R root:gpio /sys/class/gpio/gpio7
        sudo chmod -R 770 /sys/class/gpio/gpio7
        
        sudo udevadm control --reload-rules && sudo udevadm trigger
        
        print_info "Emergency stop button configured on GPIO7"
        print_info "Please connect emergency stop button between GPIO7 and GND"
        print_info "Button should be normally closed (NC) for fail-safe operation"
        
        # Update config file with use_physical_emergency_stop = true
        if [ -f "config/config.json" ]; then
            python3 -c "
import json
config_file = 'config/config.json'
with open(config_file, 'r') as f:
    config = json.load(f)
if 'safety' not in config:
    config['safety'] = {}
config['safety']['use_physical_emergency_stop'] = True
with open(config_file, 'w') as f:
    json.dump(config, f, indent=4)
"
        fi
    else
        print_info "Skipping physical emergency stop button configuration."
        print_info "Emergency stop functionality will be available through the web interface only."
        
        # Update config file with use_physical_emergency_stop = false
        if [ -f "config/config.json" ]; then
            python3 -c "
import json
config_file = 'config/config.json'
with open(config_file, 'r') as f:
    config = json.load(f)
if 'safety' not in config:
    config['safety'] = {}
config['safety']['use_physical_emergency_stop'] = False
with open(config_file, 'w') as f:
    json.dump(config, f, indent=4)
"
        fi
    fi
}

# Function to setup YOLOv8 models
setup_yolov8() {
    print_info "Setting up YOLOv8 for obstacle detection..."

    # Check for and install ultralytics if not present
    print_info "Checking for ultralytics package..."
    if ! python3 -m pip show ultralytics > /dev/null 2>&1; then
        print_info "ultralytics package not found. Installing (this may take a few minutes)..."
        
        print_info "Attempting to remove system-installed sympy to avoid conflicts..."
        if dpkg -s python3-sympy &> /dev/null; then
            sudo apt-get remove -y python3-sympy
            # check_command will use $? from the sudo apt-get command
            if check_command "Removing python3-sympy"; then
                print_info "python3-sympy removed successfully."
                # Clean up dependencies that are no longer needed
                print_info "Running apt autoremove after sympy removal..."
                sudo apt-get autoremove -y
                check_command "Running apt autoremove" || print_warning "apt autoremove encountered an issue, but proceeding."
            else
                print_warning "Failed to remove python3-sympy. Installation of ultralytics might still face issues."
            fi
        else
            print_info "python3-sympy not found via apt, proceeding with pip install."
        fi
        
        python3 -m pip install --break-system-packages --root-user-action=ignore --upgrade --upgrade-strategy eager ultralytics
        check_command "Installing ultralytics package" || { print_error "Ultralytics installation failed."; return 1; } # Return if install fails
        print_success "ultralytics package installed successfully."
    else
        print_success "ultralytics package already installed."
    fi

    # Pre-install dependencies for TFLite export to avoid issues within the ultralytics script
    print_info "Pre-installing TFLite export dependencies for ultralytics..."
    python3 -m pip install --break-system-packages --root-user-action=ignore \
        "tf_keras" \
        "sng4onnx>=1.0.1" \
        "onnx_graphsurgeon>=0.3.26" \
        "ai-edge-litert>=1.2.0" \
        "onnx>=1.12.0" \
        "onnx2tf==1.27.0" \
        "onnxslim>=0.1.46" \
        "onnxruntime"
    check_command "Installing TFLite export dependencies" || { print_warning "Failed to pre-install some TFLite export dependencies. YOLOv8 setup might encounter issues."; }

    # Ensure numpy version is compatible with TensorFlow after ultralytics installation
    print_info "Ensuring numpy version compatibility for TensorFlow..."
    python3 -m pip install --break-system-packages --root-user-action=ignore "numpy>=1.26.0,<2.2.0"
    check_command "Adjusting numpy version for TensorFlow compatibility" || { print_warning "Failed to adjust numpy. TensorFlow might have issues."; }
    
    # Create models directory if it doesn't exist
    mkdir -p src/mower/obstacle_detection/models
    check_command "Creating models directory" || exit 1
    
    # Run the setup script
    print_info "Running YOLOv8 setup script..."
    python3 scripts/setup_yolov8.py --model yolov8n
    check_command "Setting up YOLOv8 models" || exit 1
    
    # Verify installation
    if [ -f src/mower/obstacle_detection/models/yolov8n.tflite ]; then
        print_success "YOLOv8 model successfully downloaded"
    else
        print_warning "YOLOv8 model not found. Setup may have failed."
        read -p "Continue anyway? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
}

# Function to install all dependencies and set up the environment
setup_environment() {
    print_info "Installing system dependencies..."
    sudo apt-get update && sudo apt-get install -y \
        python3 python3-pip python3-venv \
        libatlas-base-dev libopenjp2-7 libtiff5 \
        i2c-tools git

    print_info "Setting up Python virtual environment..."
    python3 -m venv venv
    source venv/bin/activate

    print_info "Installing Python dependencies..."
    pip install --upgrade pip
    pip install -r requirements.txt

    print_info "Configuring GPIO permissions..."
    echo 'SUBSYSTEM=="gpio", KERNEL=="gpiochip*", GROUP="gpio", MODE="0660"' | sudo tee /etc/udev/rules.d/99-gpio.rules
    sudo udevadm control --reload-rules && sudo udevadm trigger

    print_success "Environment setup complete."
}

# Main installation starts here
print_info "Starting installation with safety checks..."

# Attempt to enable I2C and Serial if not already enabled
enable_required_interfaces

# Validate hardware first
validate_hardware

# Setup additional UART
setup_additional_uart

# Check Python version
if ! command_exists python3; then
    print_error "Python 3 is not installed"
    exit 1
fi

# Check pip version
if ! command_exists pip3; then
    print_error "pip3 is not installed"
    exit 1
fi

# Install system dependencies
print_info "Installing system dependencies..."
sudo apt-get update && sudo apt-get upgrade -y && sudo apt autoremove -y
check_command "Updating package list" || exit 1

sudo apt-get install -y \
    python3-pip \
    python3-dev \
    python3-setuptools \
    python3-wheel \
    i2c-tools \
    git \
    libatlas-base-dev \
    libhdf5-dev \
    gpsd \
    gpsd-clients \
    python3-gps \
    python3-libgpiod \
    libportaudio2 \
    libportaudiocpp0 \
    portaudio19-dev \
    python3-picamera2 \
    wget \
    gnupg \
    curl \
    gdal-bin \
    libgdal-dev \
    python3-gdal
check_command "Installing system packages" || exit 1

# Set PYTHONPATH to include our src directory
export PYTHONPATH=/home/pi/autonomous_mower/src:$PYTHONPATH

# Upgrade pip
print_info "Upgrading pip..."
python3 -m pip install --break-system-packages --root-user-action=ignore --upgrade pip
check_command "Upgrading pip" || exit 1

# Install main package and dependencies
print_info "Installing Python package and dependencies..."
python3 -m pip install --break-system-packages --root-user-action=ignore --no-cache-dir -e .
check_command "Installing main package" || exit 1

# Install additional packages
print_info "Installing additional packages..."
python3 -m pip install --break-system-packages --root-user-action=ignore --no-cache-dir \
    utm \
    adafruit-circuitpython-bme280 \
    adafruit-circuitpython-bno08x \
    barbudor-circuitpython-ina3221 \
    adafruit-circuitpython-vl53l0x \
    RPi.GPIO \
    picamera2 \
    opencv-python \
    pillow \
    numpy \
    requests \
    tqdm
check_command "Installing additional packages" || exit 1

# Set up YOLOv8 models
echo -ne "${YELLOW}Do you want to install YOLOv8 models for improved obstacle detection? (y/n) ${NC}"
read -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_info "Setting up YOLOv8 for obstacle detection..."
    
    # Check for installation directory
    mkdir -p src/mower/obstacle_detection/models
    check_command "Creating models directory" || exit 1
    
    # Use the download script instead of the problematic setup_yolov8.py
    print_info "Downloading YOLOv8 model (this avoids TensorFlow conversion issues)..."
    python3 scripts/download_yolov8.py --model yolov8n
    check_command "Downloading YOLOv8 model" || exit 1
    
    # Download COCO label map if not present
    COCO_LABELS_PATH="src/mower/obstacle_detection/models/coco_labels.txt"
    if [ ! -f "$COCO_LABELS_PATH" ]; then
        print_info "Downloading COCO label map for YOLOv8..."
        wget -O "$COCO_LABELS_PATH" \
            "https://raw.githubusercontent.com/google-coral/test_data/master/coco_labels.txt"
        check_command "Downloading COCO label map" || exit 1
    else
        print_info "COCO label map already present."
    fi
    
    # Verify installation
    if [ -f src/mower/obstacle_detection/models/yolov8n.tflite ]; then
        print_success "YOLOv8 model successfully downloaded"
    else
        print_warning "YOLOv8 model not found. Setup may have failed."
        read -p "Continue anyway? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
fi

# Ask if user wants to install Coral TPU support
read -p "Do you want to install Coral TPU support? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_info "Installing Coral TPU support..."
    
    # Check if Coral TPU is connected
    if ! lsusb | grep -q "1a6e:089a"; then
        print_warning "Coral TPU not detected. Please connect the device and try again."
        read -p "Continue anyway? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
    
    # Add Coral repository and install Edge TPU runtime
    print_info "Installing Edge TPU runtime..."
    echo "deb https://packages.cloud.google.com/apt coral-edgetpu-stable main" | sudo tee /etc/apt/sources.list.d/coral-edgetpu.list
    check_command "Adding Coral repository" || exit 1
    
    curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key add -
    check_command "Adding Coral GPG key" || exit 1
    
    sudo apt-get update
    check_command "Updating package list for Coral" || exit 1
    
    # Install standard version for thermal stability
    sudo apt-get install -y libedgetpu1-std
    check_command "Installing Edge TPU runtime" || exit 1
    
    # Set up udev rules for USB access
    print_info "Setting up USB access rules..."
    echo 'SUBSYSTEM=="usb",ATTRS{idVendor}=="1a6e",ATTRS{idProduct}=="089a",MODE="0666"' | sudo tee /etc/udev/rules.d/99-coral-tpu.rules
    check_command "Setting up udev rules" || exit 1
    
    sudo udevadm control --reload-rules && sudo udevadm trigger
    check_command "Reloading udev rules" || exit 1
    
    # Install GDAL Python package first
    sudo pip3 install GDAL==$(gdal-config --version) --break-system-packages --root-user-action=ignore --global-option=build_ext --global-option="-I/usr/include/gdal"
    check_command "Installing GDAL" || exit 1
    
    # Now install Coral dependencies
    print_info "Installing Coral Python packages..."
    sudo pip3 install -e ".[coral]" --break-system-packages --root-user-action=ignore
    check_command "Installing Coral Python packages" || exit 1
fi

# Setup watchdog
read -p "Do you want to setup hardware watchdog for improved reliability? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    setup_watchdog
fi

# Setup emergency stop
read -p "Do you want to setup a physical emergency stop button (connected to GPIO7)? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    setup_emergency_stop
else
    print_info "Skipping physical emergency stop button setup."
    print_info "The system will be configured to run without a physical emergency stop button."
    POST_INSTALL_MESSAGES+="[INFO] Physical emergency stop button was not set up. The system has been configured to run without it.\n"
    POST_INSTALL_MESSAGES+="[INFO] You can still trigger an emergency stop through the software interface.\n"
fi

# Final check for pyserial to ensure it's correctly installed for the editable package
print_info "Ensuring pyserial is correctly installed for the project..."
python3 -m pip install --break-system-packages --root-user-action=ignore "pyserial>=3.5"
check_command "Verifying/Installing pyserial" || print_warning "pyserial installation/verification failed. The main application might have issues."

print_success "Installation and setup complete."

if [ -n "$POST_INSTALL_MESSAGES" ]; then
    echo -e "\\n${YELLOW}--- Important Post-Installation Notes ---${NC}"
    # Use printf for better handling of multi-line messages and escape sequences
    printf "%b" "${YELLOW}$(echo -e "$POST_INSTALL_MESSAGES" | sed 's/^/  /')${NC}\\n"
fi

print_info "Please reboot the system for all changes to take effect."

# Clear the EXIT trap on successful completion
trap - EXIT
exit 0
