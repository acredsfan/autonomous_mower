#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to print error messages
print_error() {
    echo -e "\033[1;31mError: $1\033[0m"
}

# Function to print success messages
print_success() {
    echo -e "\033[1;32mSuccess: $1\033[0m"
}

# Function to print info messages
print_info() {
    echo -e "\033[1;34mInfo: $1\033[0m"
}

# Step 1: Install system dependencies via apt-get
print_info "Installing system dependencies..."
sudo apt-get update
sudo apt-get install -y \
    python3-dev \
    python3-pip \
    python3-venv \
    python3-setuptools \
    python3-wheel \
    python3-gpiozero \
    python3-libgpiod \
    python3-picamera2 \
    python3-opencv \
    python3-serial \
    python3-smbus \
    python3-rpi.gpio \
    i2c-tools \
    gpsd \
    gpsd-clients \
    python3-gps \
    gpiod \
    libgpiod-dev \
    libportaudio2 \
    libportaudiocpp0 \
    portaudio19-dev \
    curl \
    gnupg

print_success "System dependencies installed successfully."

# Step 2: Enable I2C and Serial interfaces if not already enabled
print_info "Enabling I2C and Serial interfaces..."
if ! grep -q "^dtparam=i2c_arm=on" /boot/config.txt; then
    echo "dtparam=i2c_arm=on" | sudo tee -a /boot/config.txt
fi

if ! grep -q "^enable_uart=1" /boot/config.txt; then
    echo "enable_uart=1" | sudo tee -a /boot/config.txt
fi

# Step 3: Check if user wants to install Coral dependencies
read -p "Do you want to install Google Coral Edge TPU support? (y/n) " install_coral
if [[ $install_coral == "y" || $install_coral == "Y" ]]; then
    print_info "Installing Coral dependencies..."
    echo "deb https://packages.cloud.google.com/apt coral-edgetpu-stable main" | sudo tee /etc/apt/sources.list.d/coral-edgetpu.list
    curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key add -
    sudo apt-get update
    sudo apt-get install -y libedgetpu1-std
    
    print_success "Coral dependencies installed."
    
    # Create models directory and download sample models
    mkdir -p models
    wget -q https://github.com/google-coral/test_data/raw/master/ssd_mobilenet_v2_coco_quant_postprocess.tflite -O models/detect.tflite
    wget -q https://github.com/google-coral/test_data/raw/master/ssd_mobilenet_v2_coco_quant_postprocess_edgetpu.tflite -O models/detect_edgetpu.tflite
    wget -q https://raw.githubusercontent.com/google-coral/test_data/master/coco_labels.txt -O models/labelmap.txt
    
    print_success "Downloaded sample models to the 'models' directory."
    
    # Flag to install Coral extras
    coral_flag=true
fi

# Step 4: Remove existing virtual environment if it exists
if [ -d "venv" ]; then
    print_info "Removing existing virtual environment..."
    rm -rf venv
fi

# Step 5: Create a new virtual environment
print_info "Creating new virtual environment..."
python3 -m venv venv --system-site-packages

# Step 6: Activate the virtual environment
source venv/bin/activate

print_success "Virtual environment activated."

# Step 7: Upgrade pip and install wheel
print_info "Upgrading pip and installing wheel..."
pip install --upgrade pip
pip install --upgrade wheel setuptools

# Step 8: Install numpy first to avoid conflicts
print_info "Installing numpy..."
pip install "numpy<2.0.0"

# Step 9: Install Python packages using setup.py with error handling
print_info "Installing Python packages..."
if ! pip install -e .; then
    print_error "Failed to install main package. Attempting to fix dependencies..."
    
    # Try installing with --no-deps first
    pip install --no-deps -e .
    
    # Then install dependencies one by one
    pip install flask-socketio>=5.1.0
    pip install flask>=2.0.0
    pip install geopy>=2.1.0
    pip install imutils
    pip install networkx
    pip install opencv-python-headless>=4.5.1
    pip install pathfinding
    pip install pillow>=8.2.0
    pip install pyserial>=3.5
    pip install python-dotenv>=0.19.0
    pip install rtree
    pip install shapely>=1.7.1
    
    # Install TensorFlow last to avoid conflicts
    pip install tensorflow>=2.5.0
fi

# Install Coral extras if requested
if [[ $coral_flag == true ]]; then
    print_info "Installing Coral Python libraries..."
    pip install -e ".[coral]"
fi

print_success "Python packages installed successfully."

# Step 10: Set up environment variables
if [ ! -f .env ]; then
    print_info "Creating .env file from example..."
    cp .env.example .env
    
    # Update model paths in .env if Coral support was installed
    if [[ $coral_flag == true ]]; then
        # Get absolute path
        models_path=$(realpath ./models)
        
        # Update .env with the correct paths
        sed -i "s|ML_MODEL_PATH=.*|ML_MODEL_PATH=$models_path|g" .env
        sed -i "s|DETECTION_MODEL=.*|DETECTION_MODEL=detect.tflite|g" .env
        sed -i "s|TPU_DETECTION_MODEL=.*|TPU_DETECTION_MODEL=detect_edgetpu.tflite|g" .env
        sed -i "s|LABEL_MAP_PATH=.*|LABEL_MAP_PATH=$models_path/labelmap.txt|g" .env
        
        print_success "Updated model paths in .env file."
    fi
fi

# Step 11: Create necessary directories
mkdir -p logs
mkdir -p config

# Step 12: Add user to required groups
print_info "Adding user to required groups..."
sudo usermod -a -G gpio,i2c,dialout,video $USER

# Step 13: Deactivate the virtual environment
deactivate

print_success "Setup complete."
print_info "Please reboot your Raspberry Pi for all changes to take effect."
print_info "After reboot, activate the virtual environment with 'source venv/bin/activate' and run 'python -m mower.main_controller'"
