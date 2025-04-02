#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# Step 1: Install system dependencies via apt-get
echo "Installing system dependencies..."
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

echo "System dependencies installed successfully."

# Step 2: Enable I2C and Serial interfaces if not already enabled
echo "Enabling I2C and Serial interfaces..."
if ! grep -q "^dtparam=i2c_arm=on" /boot/config.txt; then
    echo "dtparam=i2c_arm=on" | sudo tee -a /boot/config.txt
fi

if ! grep -q "^enable_uart=1" /boot/config.txt; then
    echo "enable_uart=1" | sudo tee -a /boot/config.txt
fi

# Step 3: Check if user wants to install Coral dependencies
read -p "Do you want to install Google Coral Edge TPU support? (y/n) " install_coral
if [[ $install_coral == "y" || $install_coral == "Y" ]]; then
    echo "Installing Coral dependencies..."
    echo "deb https://packages.cloud.google.com/apt coral-edgetpu-stable main" | sudo tee /etc/apt/sources.list.d/coral-edgetpu.list
    curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key add -
    sudo apt-get update
    sudo apt-get install -y libedgetpu1-std
    
    echo "Coral dependencies installed."
    
    # Create models directory and download sample models
    mkdir -p models
    wget -q https://github.com/google-coral/test_data/raw/master/ssd_mobilenet_v2_coco_quant_postprocess.tflite -O models/detect.tflite
    wget -q https://github.com/google-coral/test_data/raw/master/ssd_mobilenet_v2_coco_quant_postprocess_edgetpu.tflite -O models/detect_edgetpu.tflite
    wget -q https://raw.githubusercontent.com/google-coral/test_data/master/coco_labels.txt -O models/labelmap.txt
    
    echo "Downloaded sample models to the 'models' directory."
    
    # Flag to install Coral extras
    coral_flag=true
fi

# Step 4: Create and activate a virtual environment
echo "Creating virtual environment..."
python3 -m venv venv --system-site-packages

echo "Virtual environment created."

# Activate the virtual environment
source venv/bin/activate

echo "Virtual environment activated."

# Step 5: Upgrade pip
pip install --upgrade pip

# Step 6: Install Python packages using setup.py
echo "Installing Python packages..."
pip install -e .

# Install Coral extras if requested
if [[ $coral_flag == true ]]; then
    echo "Installing Coral Python libraries..."
    pip install -e ".[coral]"
fi

echo "Python packages installed successfully."

# Step 7: Set up environment variables
if [ ! -f .env ]; then
    echo "Creating .env file from example..."
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
        
        echo "Updated model paths in .env file."
    fi
fi

# Step 8: Create necessary directories
mkdir -p logs
mkdir -p config

# Step 9: Add user to required groups
echo "Adding user to required groups..."
sudo usermod -a -G gpio,i2c,dialout,video $USER

# Step 10: Deactivate the virtual environment
deactivate

echo "Setup complete."
echo "Please reboot your Raspberry Pi for all changes to take effect."
echo "After reboot, activate the virtual environment with 'source venv/bin/activate' and run 'python -m mower.main_controller'"
