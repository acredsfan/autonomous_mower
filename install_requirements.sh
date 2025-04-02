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

# Check for required commands
for cmd in python3 pip3 git wget; do
    if ! command_exists "$cmd"; then
        print_error "$cmd is required but not installed"
        exit 1
    fi
done

# Install system dependencies
print_info "Installing system dependencies..."
sudo apt-get update
sudo apt-get install -y \
    gdal-bin \
    libgdal-dev \
    python3-gdal \
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
    curl

# Create and activate virtual environment
print_info "Setting up virtual environment..."
if [ -d "venv" ]; then
    print_info "Removing existing virtual environment..."
    rm -rf venv
fi

python3 -m venv venv
source venv/bin/activate

# Upgrade pip and install wheel
print_info "Upgrading pip and installing wheel..."
pip install --upgrade pip wheel setuptools

# Install numpy first to avoid conflicts
print_info "Installing numpy..."
pip install "numpy<2.0.0"

# Install the project with all dependencies
print_info "Installing project dependencies..."
if ! pip install --use-pep517 -e .; then
    print_error "Failed to install project with dependencies"
    print_info "Attempting to install dependencies one by one..."
    
    # Install core dependencies
    pip install "flask>=2.0.0,<3.0.0"
    pip install "flask-socketio>=5.1.0,<6.0.0"
    pip install "geopy>=2.1.0,<3.0.0"
    pip install "imutils>=0.5.4"
    pip install "networkx>=2.6.0"
    pip install "opencv-python-headless>=4.5.1,<5.0.0"
    pip install "pathfinding>=1.0.0"
    pip install "pillow>=8.2.0,<9.0.0"
    pip install "pyserial>=3.5,<4.0.0"
    pip install "python-dotenv>=0.19.0,<1.0.0"
    pip install "rtree>=1.0.0"
    pip install "shapely>=1.7.1,<2.0.0"
    pip install "tensorflow>=2.12.0,<2.13.0"
fi

# Ask if user wants to install Coral TPU support
read -p "Do you want to install Coral TPU support? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_info "Installing Coral TPU support..."
    
    # Install GDAL Python package first
    pip install GDAL==$(gdal-config --version) --global-option=build_ext --global-option="-I/usr/include/gdal"
    
    # Now install Coral dependencies
    pip install --use-pep517 -e ".[coral]"
    
    # Create models directory with proper permissions
    print_info "Setting up models directory..."
    sudo mkdir -p models
    sudo chown $USER:$USER models
    
    # Download model files
    print_info "Downloading model files..."
    if ! download_model "https://github.com/google-coral/test_data/raw/master/ssd_mobilenet_v2_coco_quant_postprocess.tflite" "models/detect.tflite"; then
        print_error "Failed to download detect.tflite"
    fi
    
    if ! download_model "https://github.com/google-coral/test_data/raw/master/ssd_mobilenet_v2_coco_quant_postprocess_edgetpu.tflite" "models/detect_edgetpu.tflite"; then
        print_error "Failed to download detect_edgetpu.tflite"
    fi
    
    if ! download_model "https://raw.githubusercontent.com/google-coral/test_data/master/coco_labels.txt" "models/labelmap.txt"; then
        print_error "Failed to download labelmap.txt"
    fi
    
    # Verify model files
    if [ -f "models/detect.tflite" ] && [ -f "models/detect_edgetpu.tflite" ] && [ -f "models/labelmap.txt" ]; then
        print_success "All model files downloaded successfully"
    else
        print_error "Some model files are missing"
    fi
fi

# Add user to required groups
print_info "Adding user to required groups..."
sudo usermod -a -G gpio,i2c,dialout,video $USER

# Enable I2C and Serial interfaces
print_info "Enabling I2C and Serial interfaces..."
sudo raspi-config nonint do_i2c 0
sudo raspi-config nonint do_serial 0

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    print_info "Creating .env file..."
    cp .env.example .env
    print_info "Please edit .env with your specific settings"
fi

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
