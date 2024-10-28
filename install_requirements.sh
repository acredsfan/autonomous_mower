#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# Step 1: Install system dependencies via apt-get
echo "Installing system dependencies..."
sudo apt-get update
sudo apt-get install -y libatlas-base-dev libhdf5-dev libhdf5-serial-dev \
                        python3-dev python3-pip i2c-tools gpsd gpsd-clients \
                        python3-gps python3-libgpiod libportaudio2 \
                        libportaudiocpp0 portaudio19-dev gpiod \

echo "System dependencies installed successfully."

# Step 2: Create and activate a virtual environment
echo "Creating virtual environment..."
python3 -m venv venv --system-site-packages

echo "Virtual environment created."

# Activate the virtual environment
source venv/bin/activate

echo "Virtual environment activated."

# Step 3: Upgrade pip
pip install --upgrade pip

# Step 4: Install Python packages using setup.py
echo "Installing Python packages..."
pip install -e .

echo "Python packages installed successfully."

# Step 5: Deactivate the virtual environment
deactivate

echo "Setup complete."
