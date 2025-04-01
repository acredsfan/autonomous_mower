# Google Coral TPU Setup Guide

This guide will help you set up the Google Coral USB Accelerator for improved object detection performance on your autonomous mower.

## Benefits of the Coral TPU
- Up to 10x faster inference for obstacle detection
- Lower CPU usage, freeing resources for other processes
- Better real-time performance for safety-critical detections
- Lower power consumption for longer battery life

## Hardware Requirements
- Google Coral USB Accelerator
- USB 3.0 port (recommended) or USB 2.0 port
- Autonomous mower hardware platform
- 5V power supply with sufficient amperage (the TPU can draw up to 500mA)

## Installation Instructions

### Step 1: Physical Connection
1. Power off your autonomous mower system
2. Connect the Coral USB Accelerator to an available USB port
3. Ensure the device is securely connected

### Step 2: Install Software Dependencies
The system automatically detects the Coral device and will use it if available, but you need to install the required libraries.

For Raspberry Pi or Debian-based systems:

```bash
# Add the Coral repository
echo "deb https://packages.cloud.google.com/apt coral-edgetpu-stable main" | sudo tee /etc/apt/sources.list.d/coral-edgetpu.list
curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key add -
sudo apt-get update

# Install the Edge TPU runtime and Python libraries
sudo apt-get install libedgetpu1-std python3-pycoral

# Install the TensorFlow Lite Runtime
pip3 install tflite-runtime

# Install the PyCoral library
pip3 install pycoral
```

For other systems, please refer to the [official Coral documentation](https://coral.ai/docs/accelerator/get-started/).

### Step 3: Download Models

The system needs both CPU and TPU models to work properly (TPU for acceleration, CPU as fallback).

1. Create a models directory if it doesn't exist:
```bash
mkdir -p models
```

2. Download a compatible TFLite model and its Edge TPU version:
```bash
# Example for downloading MobileNet SSD v2 model
curl -O https://github.com/google-coral/test_data/raw/master/ssd_mobilenet_v2_coco_quant_postprocess.tflite
curl -O https://github.com/google-coral/test_data/raw/master/ssd_mobilenet_v2_coco_quant_postprocess_edgetpu.tflite

# Rename to match our expected filenames
mv ssd_mobilenet_v2_coco_quant_postprocess.tflite models/detect.tflite
mv ssd_mobilenet_v2_coco_quant_postprocess_edgetpu.tflite models/detect_edgetpu.tflite

# Download a label map
curl -O https://raw.githubusercontent.com/google-coral/test_data/master/coco_labels.txt
mv coco_labels.txt models/labelmap.txt
```

### Step 4: Configure Environment Variables

Update your `.env` file with the following settings:

```
ML_MODEL_PATH=./models
DETECTION_MODEL=detect.tflite
TPU_DETECTION_MODEL=detect_edgetpu.tflite
LABEL_MAP_PATH=./models/labelmap.txt
MIN_CONF_THRESHOLD=0.5
```

### Step 5: Verify Installation

1. Start the mower software
2. Check the log for messages indicating the TPU was found and initialized
3. You should see a message like: "Found X Edge TPU device(s). Using hardware acceleration."

## Troubleshooting

### TPU Not Detected
- Verify the TPU is properly connected
- Check system logs for USB errors: `dmesg | grep USB`
- Ensure user has permissions to access the device:
  ```bash
  sudo usermod -aG plugdev $USER
  ```
  (Log out and back in after running this command)

### Permission Errors
- If you encounter permission errors, try:
  ```bash
  sudo chmod 666 /dev/bus/usb/<bus>/<device>
  ```
  Replace `<bus>` and `<device>` with the values from `lsusb` output.

### Coral Device Overheating
- The Coral TPU can get warm during operation. This is normal.
- If it becomes too hot to touch, ensure proper ventilation and consider adding a small heatsink.

### Installation Failed
- Verify your OS version is compatible with the Coral software
- Try reinstalling the libraries:
  ```bash
  pip3 uninstall tflite-runtime pycoral
  pip3 install --upgrade tflite-runtime pycoral
  ```

## Performance Tuning

For best performance:
- Use USB 3.0 ports if available
- Keep the TPU clean and well-ventilated
- Adjust the confidence threshold in `.env` for your specific needs
- Consider reducing camera resolution if detection speed is critical

## Additional Resources
- [Official Coral USB Accelerator Documentation](https://coral.ai/docs/accelerator/get-started/)
- [TensorFlow Lite Models for Coral](https://coral.ai/models/)
- [Edge TPU Model Compiler](https://coral.ai/docs/edgetpu/compiler/) 