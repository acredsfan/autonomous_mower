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

The installation script automatically handles Python version compatibility and Coral library installation.

**Automatic Installation (Recommended):**
Run the main installation script, which will automatically:
- Set up Python 3.9 virtual environment (always, regardless of system Python)
- Install all required dependencies in the correct order
- Handle NumPy version compatibility automatically
- Provide comprehensive error diagnostics

```bash
./install_requirements.sh
```

**Important Notes about the Installation Process:**
- **Always uses Python 3.9 virtual environment** - This follows Google's official recommendations for maximum compatibility
- **Automatic dependency management** - Installs NumPy, TFLite, and PyCoral in the correct order to avoid compatibility issues
- **Version compatibility handling** - Ensures compatible NumPy versions to prevent import errors
- **Better error diagnostics** - Provides detailed error messages if installation fails

**Using the Coral Environment:**
After installation, activate the Coral environment when running Coral-dependent code:
```bash
# Activate the Coral environment (includes comprehensive diagnostics)
source ~/activate-coral-env.sh

# Run your mower code that uses Coral
python your_script.py

# The environment will remain active for that terminal session
# Deactivate with: deactivate
```

**Testing the Installation:**
After installation, you can test the Coral setup:
```bash
# Run the comprehensive test script
./test_coral_installation.sh

# Or manually test
source ~/activate-coral-env.sh
python -c "import pycoral.utils.edgetpu; print('Coral TPU ready!')"
```

# Run your mower code that uses Coral
python your_script.py

# The environment will remain active for that terminal session
```

**Manual Installation (Advanced Users):**
If you wish to set up the Coral environment manually, follow the official Coral documentation. The recommended approach is to always use a Python 3.9 virtual environment, even if your system Python is newer. See:

- [Official Google Coral Python API](https://coral.ai/docs/edgetpu/api-intro/)
- [PyCoral Installation Guide](https://coral.ai/docs/edgetpu/api-intro/#install-pycoral)

**Do not install PyCoral into system Python 3.10+!**
sudo python3 -m pip install --break-system-packages \
    --extra-index-url https://google-coral.github.io/py-repo/ \
    pycoral~=2.0
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

## Using Coral TPU with Python 3.10+ Systems

If your system has Python 3.10 or higher, the installation script will have created a separate Python 3.9 environment for Coral compatibility.

### Running the Mower with Coral Support

**Option 1: Activate the environment manually**
```bash
# Activate the Coral environment
source ~/activate-coral-env.sh

# Run the mower (from the project directory)
python -m mower.main_controller

# Or run any other Coral-dependent scripts
python scripts/test_coral_detection.py
```

**Option 2: Use the activation script in your service files**
If you're running the mower as a systemd service, update your service file to activate the Coral environment:
```bash
# Edit your service file
sudo nano /etc/systemd/system/mower.service

# Update the ExecStart line to include environment activation:
ExecStart=/bin/bash -c 'source /home/pi/activate-coral-env.sh && python -m mower.main_controller'
```

### Development and Testing

When developing or testing Coral-related features:
```bash
# Always activate the Coral environment first
source ~/activate-coral-env.sh

# Verify PyCoral is available
python -c "import pycoral.utils.edgetpu; print('PyCoral is working!')"

# Run your tests
pytest tests/test_coral_detection.py
```

### Environment Details

The Coral environment includes:
- Python 3.9.18 (or latest 3.9.x)
- PyCoral 2.0+ (installed via Coral's pip repository)
- TensorFlow Lite Runtime
- NumPy, Pillow, and other dependencies
- All Edge TPU runtime libraries

The environment is located at: `~/.coral-python-env/`

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
