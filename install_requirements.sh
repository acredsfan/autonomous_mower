#!/bin/bash

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

# Function to validate Raspberry Pi hardware
validate_hardware() {
    # Check if running on Raspberry Pi
    if ! grep -q "Raspberry Pi" /proc/cpuinfo; then
        print_error "This script must be run on a Raspberry Pi"
        exit 1
    }

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
    if ! vcgencmd get_camera | grep -q "supported=1"; then
        print_warning "Camera module not detected"
        read -p "Continue anyway? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
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

# Check if running as root
if [ "$EUID" -eq 0 ]; then 
    print_error "Please do not run this script as root"
    exit 1
fi

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

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    print_info "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Define path to venv pip
VENV_PIP="./venv/bin/pip"

# Upgrade pip and install wheel using venv pip
print_info "Upgrading pip and installing wheel in venv..."
$VENV_PIP install --upgrade pip
$VENV_PIP install wheel

# Install system dependencies
print_info "Installing system dependencies..."
sudo apt-get update
sudo apt-get install -y \
    libatlas-base-dev \
    libhdf5-dev \
    python3-dev \
    python3-pip \
    i2c-tools \
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

# Install Python package in editable mode with all dependencies into venv
print_info "Installing Python package and dependencies into venv..."
# Use --upgrade flag to force checking/installing dependencies
$VENV_PIP install --no-cache-dir --upgrade -e .

# Explicitly install packages that might be missed by editable install
print_info "Explicitly installing potentially missed packages..."
$VENV_PIP install --no-cache-dir "utm"
$VENV_PIP install --no-cache-dir "adafruit-circuitpython-bme280"
$VENV_PIP install --no-cache-dir "adafruit-circuitpython-bno08x"
$VENV_PIP install --no-cache-dir "barbudor-circuitpython-ina3221"
$VENV_PIP install --no-cache-dir "adafruit-circuitpython-vl53l0x"
$VENV_PIP install --no-cache-dir "RPi.GPIO"
$VENV_PIP install --no-cache-dir "picamera2"

# Ask if user wants to install Coral TPU support
read -p "Do you want to install Coral TPU support? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_info "Installing Coral TPU support..."
    
    # Add Coral repository and install Edge TPU runtime
    print_info "Installing Edge TPU runtime..."
    echo "deb https://packages.cloud.google.com/apt coral-edgetpu-stable main" | sudo tee /etc/apt/sources.list.d/coral-edgetpu.list
    curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key add -
    sudo apt-get update
    
    # Install standard version for thermal stability
    sudo apt-get install -y libedgetpu1-std
    
    # Set up udev rules for USB access
    print_info "Setting up USB access rules..."
    echo 'SUBSYSTEM=="usb",ATTRS{idVendor}=="1a6e",ATTRS{idProduct}=="089a",MODE="0666"' | sudo tee /etc/udev/rules.d/99-coral-tpu.rules
    sudo udevadm control --reload-rules && sudo udevadm trigger
    
    # Install GDAL Python package first using venv pip
    $VENV_PIP install GDAL==$(gdal-config --version) --global-option=build_ext --global-option="-I/usr/include/gdal"
    
    # Now install Coral dependencies using venv pip
    print_info "Installing Coral Python packages..."
    $VENV_PIP install -e ".[coral]"
    
    # Create models directory with proper permissions
    print_info "Setting up models directory..."
    mkdir -p src/mower/obstacle_detection/models
    
    # Download model files
    print_info "Downloading model files..."
    wget -O src/mower/obstacle_detection/models/detect_edgetpu.tflite \
        https://github.com/google-coral/test_data/raw/master/ssd_mobilenet_v2_coco_quant_postprocess_edgetpu.tflite
    wget -O src/mower/obstacle_detection/models/detect.tflite \
        https://github.com/google-coral/test_data/raw/master/ssd_mobilenet_v2_coco_quant_postprocess.tflite
    wget -O src/mower/obstacle_detection/models/labelmap.txt \
        https://raw.githubusercontent.com/google-coral/test_data/master/coco_labels.txt
    
    print_info "Coral TPU setup complete!"
    print_info "Notes:"
    print_info "1. Using standard performance mode for thermal stability"
    print_info "2. To switch to max performance mode: sudo apt-get install libedgetpu1-max"
    print_info "3. After connecting USB Accelerator, run: sudo udevadm trigger"
fi

# Create necessary directories
print_info "Creating necessary directories..."
mkdir -p data
mkdir -p logs

# Set up environment file if it doesn't exist
if [ ! -f .env ]; then
    print_info "Creating .env file from template..."
    cp .env.example .env
    print_info "Please update .env with your configuration"
fi

# Add user to required groups
print_info "Adding user to required groups..."
sudo usermod -a -G gpio,i2c,dialout,video $USER

# Enable I2C and Serial interfaces
print_info "Enabling I2C and Serial interfaces..."
sudo raspi-config nonint do_i2c 0
sudo raspi-config nonint do_serial 0

# Set up systemd service
print_info "Setting up systemd service..."
# Get the absolute path of the project directory
PROJECT_DIR=$(pwd)

# Use the updated service file configuration (using venv python)
print_info "Using updated service file configuration..."
sudo cp autonomous-mower.service /etc/systemd/system/

# Ensure project directory has correct permissions
print_info "Ensuring correct project directory permissions..."
sudo chown -R $USER:$USER "$PROJECT_DIR"
sudo chmod -R 755 "$PROJECT_DIR"

# Reload systemd and enable the service
print_info "Reloading systemd and enabling service..."
sudo systemctl daemon-reload
sudo systemctl enable autonomous-mower.service

# Start the service and check status
print_info "Starting service and checking status..."
sudo systemctl start autonomous-mower.service
sleep 5 # Give service a few seconds to start
sudo systemctl status autonomous-mower.service

# Add safety features
setup_watchdog
setup_emergency_stop

# Create data directories with proper permissions
print_info "Creating data directories..."
mkdir -p data/logs
mkdir -p data/backups
chmod 755 data
chmod 755 data/logs
chmod 755 data/backups

# Setup log rotation
print_info "Setting up log rotation..."
sudo tee /etc/logrotate.d/autonomous-mower << EOF
/var/log/autonomous-mower.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 644 $USER $USER
}
EOF

print_success "Installation complete with safety features!"
print_info "Please review the following:"
print_info "1. Test emergency stop button functionality"
print_info "2. Verify watchdog is working: systemctl status watchdog"
print_info "3. Check all sensor connections"
print_info "4. Review logs in /var/log/autonomous-mower.log"
print_info "5. Test the mower in a safe, enclosed area first"
