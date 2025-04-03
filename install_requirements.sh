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

# Create and activate virtual environment
print_info "Setting up virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Upgrade pip and install wheel
print_info "Upgrading pip and installing wheel..."
pip install --upgrade pip
pip install wheel

# Install system dependencies
print_info "Installing system dependencies..."
sudo apt-get update
sudo apt-get install -y \
    libatlas-base-dev \
    libhdf5-dev \
    libhdf5-serial-dev \
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

# Install Python package in editable mode with all dependencies
print_info "Installing Python package and dependencies..."
pip install -e .

# Download model files
print_info "Downloading model files..."
mkdir -p models
download_model "https://github.com/google-coral/test_data/raw/master/ssd_mobilenet_v2_coco_quant_postprocess.tflite" "models/detect.tflite"
download_model "https://github.com/google-coral/test_data/raw/master/ssd_mobilenet_v2_coco_quant_postprocess_edgetpu.tflite" "models/detect_edgetpu.tflite"
download_model "https://raw.githubusercontent.com/google-coral/test_data/master/coco_labels.txt" "models/labelmap.txt"

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
# Replace the placeholder in the service file
sed -i "s|/home/pi/autonomous_mower|$PROJECT_DIR|g" autonomous-mower.service

# Copy service file to systemd directory
sudo cp autonomous-mower.service /etc/systemd/system/

# Create log files with proper permissions
sudo touch /var/log/autonomous-mower.log
sudo touch /var/log/autonomous-mower.error.log
sudo chown $USER:$USER /var/log/autonomous-mower.log
sudo chown $USER:$USER /var/log/autonomous-mower.error.log

# Reload systemd and enable the service
sudo systemctl daemon-reload
sudo systemctl enable autonomous-mower.service

print_success "Installation complete!"
print_info "Please log out and log back in for group changes to take effect"
print_info "The mower service will start automatically on boot"
print_info "You can check the service status with: sudo systemctl status autonomous-mower"
print_info "View logs with: journalctl -u autonomous-mower"
