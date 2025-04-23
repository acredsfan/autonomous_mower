#!/bin/bash

# Exit on error
set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

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

# Function to validate Raspberry Pi hardware
validate_hardware() {
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
        print_error "I2C interface not enabled. Please enable it using raspi-config"
        exit 1
    fi

    if ! ls /dev/ttyAMA* >/dev/null 2>&1; then
        print_error "Serial interface not enabled. Please enable it using raspi-config"
        exit 1
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
}

# Main installation starts here
print_info "Starting installation with safety checks..."

# Validate hardware first
validate_hardware

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
sudo apt-get update && sudo apt-get full-upgrade -y && sudo apt autoremove -y
check_command "Updating package list and performing full upgrade" || exit 1

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
    python3-gdal \
    certbot \
    ddclient
check_command "Installing system packages" || exit 1

# Set PYTHONPATH to include our src directory
export PYTHONPATH=/home/pi/autonomous_mower/src:$PYTHONPATH

# Ensure PYTHONPATH includes the src directory
export PYTHONPATH=$PYTHONPATH:$(pwd)/src

echo "PYTHONPATH set to include src directory."

# Upgrade pip
print_info "Upgrading pip..."
sudo python3 -m pip install --break-system-packages --upgrade pip
check_command "Upgrading pip" || exit 1

# Install main package and dependencies
print_info "Installing Python package and dependencies..."
sudo python3 -m pip install --break-system-packages --no-cache-dir -e .
check_command "Installing main package" || exit 1

# Install additional packages
print_info "Installing additional packages..."
sudo python3 -m pip install --break-system-packages --no-cache-dir \
    utm \
    adafruit-circuitpython-bme280 \
    adafruit-circuitpython-bno08x \
    barbudor-circuitpython-ina3221 \
    adafruit-circuitpython-vl53l0x \
    RPi.GPIO \
    picamera2
check_command "Installing additional packages" || exit 1

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
    sudo pip3 install GDAL==$(gdal-config --version) --break-system-packages --global-option=build_ext --global-option="-I/usr/include/gdal"
    check_command "Installing GDAL" || exit 1

    # Now install Coral dependencies
    print_info "Installing Coral Python packages..."
    sudo pip3 install -e ".[coral]" --break-system-packages
    check_command "Installing Coral dependencies" || exit 1

    # Create models directory with proper permissions
    print_info "Setting up models directory..."
    mkdir -p src/mower/obstacle_detection/models
    check_command "Creating models directory" || exit 1

    # Download model files
    print_info "Downloading model files..."
    wget -O src/mower/obstacle_detection/models/detect_edgetpu.tflite \
        https://github.com/google-coral/test_data/raw/master/ssd_mobilenet_v2_coco_quant_postprocess_edgetpu.tflite
    check_command "Downloading Edge TPU model" || exit 1

    wget -O src/mower/obstacle_detection/models/detect.tflite \
        https://github.com/google-coral/test_data/raw/master/ssd_mobilenet_v2_coco_quant_postprocess.tflite
    check_command "Downloading standard model" || exit 1

    wget -O src/mower/obstacle_detection/models/labelmap.txt \
        https://raw.githubusercontent.com/google-coral/test_data/master/coco_labels.txt
    check_command "Downloading label map" || exit 1

    print_info "Coral TPU setup complete!"
    print_info "Notes:"
    print_info "1. Using standard performance mode for thermal stability"
    print_info "2. To switch to max performance mode: sudo apt-get install libedgetpu1-max"
    print_info "3. After connecting USB Accelerator, run: sudo udevadm trigger"
fi

# Create necessary directories
print_info "Creating necessary directories..."
mkdir -p logs
mkdir -p data
mkdir -p config
check_command "Creating config directory" || exit 1

# Set proper permissions
print_info "Setting directory permissions..."
chmod 755 logs data config
check_command "Setting directory permissions" || exit 1

# Set up service log directory
print_info "Setting up service log directory..."
sudo mkdir -p /var/log/autonomous-mower
sudo chown -R $(whoami):$(whoami) /var/log/autonomous-mower
sudo chmod 755 /var/log/autonomous-mower
check_command "Setting up service log directory" || exit 1

# Setup watchdog before systemd service
print_info "Setting up watchdog service (required for autonomous-mower.service)..."
setup_watchdog
check_command "Setting up watchdog" || exit 1

# Verify watchdog is running
if ! systemctl is-active --quiet watchdog.service; then
    print_error "Watchdog service failed to start. Please check system logs."
    exit 1
fi

# --- Add Systemd Service Setup ---
print_info "Setting up systemd service..."
SERVICE_FILE="autonomous-mower.service"
SYSTEMD_DIR="/etc/systemd/system"

if [ -f "$SERVICE_FILE" ]; then
    print_info "Copying $SERVICE_FILE to $SYSTEMD_DIR..."
    sudo cp "$SERVICE_FILE" "$SYSTEMD_DIR/"
    check_command "Copying service file" || exit 1

    print_info "Reloading systemd daemon..."
    sudo systemctl daemon-reload
    check_command "Reloading systemd daemon" || exit 1

    print_info "Enabling $SERVICE_FILE to start on boot..."
    sudo systemctl enable "$SERVICE_FILE"
    check_command "Enabling service" || exit 1

    print_success "Systemd service '$SERVICE_FILE' installed and enabled."

    # Start the service
    print_info "Starting the service..."
    sudo systemctl start "$SERVICE_FILE"
    check_command "Starting service" || exit 1

    # Verify the service is running with no errors
    print_info "Verifying the service is running with no errors..."
    sudo systemctl status "$SERVICE_FILE"
    if [ $? -ne 0 ]; then
        print_error "Service failed to start. Please check the logs."
        sudo systemctl stop "$SERVICE_FILE"
        exit 1
    fi

    print_info "You can manage the service using:"
    print_info "  sudo systemctl start $SERVICE_FILE"
    print_info "  sudo systemctl stop $SERVICE_FILE"
    print_info "  sudo systemctl status $SERVICE_FILE"
else
    print_warning "$SERVICE_FILE not found. Skipping systemd setup."
fi
# --- End Systemd Service Setup ---

# Configure hardware interfaces
print_info "Configuring hardware interfaces..."
# Enable I2C
if ! grep -q "i2c-dev" /etc/modules; then
    echo "i2c-dev" >> /etc/modules
fi

# Enable serial port
if ! grep -q "enable_uart=1" /boot/config.txt; then
    echo "enable_uart=1" >> /boot/config.txt
fi

# Enable camera
if ! grep -q "start_x=1" /boot/config.txt; then
    echo "start_x=1" >> /boot/config.txt
fi

# Set up watchdog
print_info "Setting up watchdog..."
if ! grep -q "bcm2835_wdt" /etc/modules; then
    echo "bcm2835_wdt" >> /etc/modules
fi

# Success message
print_success "Installation completed successfully!"

# Run interactive setup wizard automatically
print_info "Running interactive setup wizard..."
python3 setup_wizard.py

# Remove trap and exit successfully
trap - EXIT
exit 0
