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

# Function to print info messages
print_info() {
    echo -e "${YELLOW}INFO: $1${NC}"
}

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to download a model file with retries
download_model() {
    local url=$1
    local output=$2
    local max_retries=3
    local retry_count=0
    
    while [ $retry_count -lt $max_retries ]; do
        if wget -q "$url" -O "$output"; then
            print_success "Downloaded $output"
            return 0
        fi
        retry_count=$((retry_count + 1))
        print_error "Failed to download $output (attempt $retry_count/$max_retries)"
        sleep 2
    done
    return 1
}

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

print_success "Installation complete!"
print_info "Please log out and log back in for group changes to take effect"
print_info "The mower service will start automatically on boot"
print_info "You can check the service status with: sudo systemctl status autonomous-mower"
print_info "View logs with: journalctl -u autonomous-mower"
