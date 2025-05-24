#!/bin/bash

# Script to install system-level dependencies for the Raspberry Pi project

echo "Updating package lists..."
sudo apt-get update

echo "Installing core hardware communication libraries..."
sudo apt-get install -y \
    i2c-tools \
    python3-smbus \
    python3-rpi.gpio \
    minicom \
    python3-serial

echo "Installing Picamera2 stack and dependencies..."
# Ensure the system is up-to-date before installing camera stack
sudo apt-get upgrade -y
sudo apt-get install -y \
    libcamera-apps \
    python3-libcamera \
    python3-kmsvdr \
    python3-picamera2

echo "Installing OpenCV dependencies (runtime and some build tools)..."
# Note: opencv-python is usually installed via pip.
# These are provided for system-wide availability or if building from source.
sudo apt-get install -y \
    libopencv-core-dev \
    libopencv-imgproc-dev \
    libopencv-highgui-dev \
    libopencv-videoio-dev \
    libgtk-3-dev \
    libatlas-base-dev \
    gfortran \
    libhdf5-dev \
    libhdf5-serial-dev \
    libqtgui4 \
    libqtwebkit4 \
    libqt4-test \
    python3-opencv

echo "Installing common Python build tools and other utilities..."
sudo apt-get install -y \
    build-essential \
    python3-dev \
    python3-pip \
    python3-setuptools \
    python3-wheel \
    git \
    cmake \
    pkg-config \
    curl \
    wget

echo "Installing other system libraries based on requirements.txt..."
sudo apt-get install -y \
    libsystemd-dev \
    libudev-dev \
    gpsd \
    libgps-dev \
    libgirepository1.0-dev \
    libcairo2-dev

echo "Setting up Coral EdgeTPU dependencies..."
echo "IMPORTANT: The following steps add the Coral package repository and install libedgetpu1-std."
echo "Refer to the official Coral documentation for the latest instructions: https://coral.ai/software/#debian-packages"

# Add Coral package repository
echo "deb https://packages.cloud.google.com/apt coral-edgetpu-stable main" | sudo tee /etc/apt/sources.list.d/coral-edgetpu.list
curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key add -

# Update package lists again after adding new repository
sudo apt-get update

# Install EdgeTPU runtime
# Use libedgetpu1-std for standard performance, or libedgetpu1-max for maximum performance (higher power consumption)
# Choose one:
sudo apt-get install -y libedgetpu1-std
# OR
# sudo apt-get install -y libedgetpu1-max

# python3-tflite-runtime and pycoral are typically installed via pip as per requirements.txt
# but you can check for system packages if preferred:
# sudo apt-get install -y python3-tflite-runtime # (May not always be available or up-to-date)

echo "All specified system dependencies installation commands have been listed."
echo "Please review the script and run it on your Raspberry Pi."
echo "Remember to handle the libedgetpu choice (std vs max) as per your needs."
