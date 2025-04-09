#!/bin/bash

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}[+]${NC} $1"
}

print_error() {
    echo -e "${RED}[!]${NC} $1"
}

print_info() {
    echo -e "${YELLOW}[*]${NC} $1"
}

# Check if script is run as root
if [ "$EUID" -eq 0 ]; then 
    print_error "Please do not run as root"
    exit 1
fi

# 1. Install Edge TPU runtime
print_status "Installing Edge TPU runtime..."
echo "deb https://packages.cloud.google.com/apt coral-edgetpu-stable main" | sudo tee /etc/apt/sources.list.d/coral-edgetpu.list
curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key add -
sudo apt-get update
sudo apt-get install -y libedgetpu1-std

# 2. Install Python packages
print_status "Installing Python packages..."
pip install --no-cache-dir -e ".[coral]"

# 3. Set up udev rules for USB access
print_status "Setting up udev rules..."
echo 'SUBSYSTEM=="usb",ATTRS{idVendor}=="1a6e",ATTRS{idProduct}=="089a",MODE="0666"' | sudo tee /etc/udev/rules.d/99-coral-tpu.rules
sudo udevadm control --reload-rules && sudo udevadm trigger

# 4. Download models if they don't exist
print_status "Checking/downloading models..."
MODELS_DIR="src/mower/obstacle_detection/models"
mkdir -p "$MODELS_DIR"

if [ ! -f "$MODELS_DIR/detect_edgetpu.tflite" ]; then
    print_info "Downloading Edge TPU model..."
    wget -O "$MODELS_DIR/detect_edgetpu.tflite" \
        "https://github.com/google-coral/test_data/raw/master/ssd_mobilenet_v2_coco_quant_postprocess_edgetpu.tflite"
fi

if [ ! -f "$MODELS_DIR/detect.tflite" ]; then
    print_info "Downloading CPU fallback model..."
    wget -O "$MODELS_DIR/detect.tflite" \
        "https://github.com/google-coral/test_data/raw/master/ssd_mobilenet_v2_coco_quant_postprocess.tflite"
fi

if [ ! -f "$MODELS_DIR/labelmap.txt" ]; then
    print_info "Downloading label map..."
    wget -O "$MODELS_DIR/labelmap.txt" \
        "https://raw.githubusercontent.com/google-coral/test_data/master/coco_labels.txt"
fi

# 5. Verify installation
print_status "Verifying installation..."
if lsusb | grep -q "1a6e:089a"; then
    print_status "Coral USB Accelerator detected"
else
    print_info "Coral USB Accelerator not detected. Please connect it and run: sudo udevadm trigger"
fi

print_status "Installation complete!"
print_info "Notes:"
print_info "1. Using standard performance mode for thermal stability"
print_info "2. To switch to max performance, run: sudo apt-get install libedgetpu1-max"
print_info "3. After connecting the USB Accelerator, run: sudo udevadm trigger"
print_info "4. Check logs for any detection performance issues before considering max performance mode" 