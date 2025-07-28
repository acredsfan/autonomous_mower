#!/usr/bin/env python3
"""
YOLOv8 TFLite Model Setup Script for Autonomous Mower

IMPORTANT: This script has been updated because the YOLOv8 export functionality
has been removed from the codebase. 

The original yolov8_downloads.py file contained only documentation explaining
that TensorFlow export is not supported on Raspberry Pi (Bookworm, Python 3.11+).

---

# How to Use YOLOv8 Models for Obstacle Detection

1. **Export the YOLOv8 model to TFLite format on a supported PC:**
   - Use a Linux or Windows PC (x86_64) with Python 3.9 or 3.10.
   - Install the required packages:
     ```sh
     pip install ultralytics tensorflow==2.14.* flatbuffers==23.*
     ```
   - Download the YOLOv8 PyTorch model (e.g., yolov8n.pt) from Ultralytics.
   - Export to TFLite:
     ```sh
     yolo export model=yolov8n.pt format=tflite imgsz=640 nms=False
     ```
   - The exported file will be named `yolov8n_float32.tflite` (or similar).

2. **Copy the exported `.tflite` model and label map to your Raspberry Pi:**
   - Place the `.tflite` file in the `models/` directory of your mower project.
   - Place the label map (e.g., `imagenet_labels.txt` or
     `coco_labels.txt`) in the same directory.

3. **Update your `.env` file:**
   - Add or update these lines:
     ```
     # YOLOv8 configuration
     YOLOV8_MODEL_PATH=models/yolov8n_float32.tflite
     LABEL_MAP_PATH=models/coco_labels.txt
     USE_YOLOV8=True
     ```

4. **Restart the mower software.**
   - The obstacle detector will automatically use the YOLOv8 TFLite model if
     configured.

---

## Troubleshooting
- If you see errors about TensorFlow or FlatBuffers versions, ensure you did
  the export on a supported PC, not on the Pi.
- If the model or label map is missing, download or export them as described
  above.
- For more details, see the project documentation or ask for help in the
  project forums.

---

This script now only checks for the presence of the required model files
and provides setup instructions if they are missing.
"""

import os
import sys
from pathlib import Path


def main():
    """Check for YOLOv8 model files and provide setup instructions."""
    
    # Define required files
    models_dir = Path("models")
    required_model = models_dir / "yolov8n_float32.tflite"
    required_labels = models_dir / "coco_labels.txt"
    
    # Alternative model files that might exist
    alternative_models = [
        models_dir / "yolov8s_float32.tflite",
        models_dir / "yolov8m_float32.tflite",
        models_dir / "pi_model_float32.tflite"
    ]
    
    print("YOLOv8 Model Setup Checker")
    print("=" * 50)
    
    # Check if models directory exists
    if not models_dir.exists():
        print(f"❌ Models directory '{models_dir}' does not exist.")
        print("   Please create it and add your YOLOv8 TFLite model files.")
        sys.exit(1)
    
    # Check for required model
    model_found = False
    if required_model.exists():
        print(f"✅ Found YOLOv8 model: {required_model}")
        model_found = True
    else:
        # Check for alternative models
        for alt_model in alternative_models:
            if alt_model.exists():
                print(f"✅ Found alternative YOLOv8 model: {alt_model}")
                model_found = True
                break
    
    if not model_found:
        print(f"❌ No YOLOv8 TFLite model found in {models_dir}")
        print("   Expected files:")
        print(f"   - {required_model}")
        for alt in alternative_models:
            print(f"   - {alt}")
    
    # Check for labels
    if required_labels.exists():
        print(f"✅ Found label map: {required_labels}")
    else:
        print(f"❌ Label map not found: {required_labels}")
    
    # Check environment configuration
    env_file = Path(".env")
    if env_file.exists():
        print(f"✅ Found environment file: {env_file}")
        
        # Check for YOLOv8 configuration
        with open(env_file, 'r') as f:
            env_content = f.read()
            
        if "YOLOV8_MODEL_PATH" in env_content:
            print("✅ YOLOv8 model path configured in .env")
        else:
            print("⚠️  YOLOv8 model path not configured in .env")
            
        if "USE_YOLOV8" in env_content:
            print("✅ YOLOv8 usage flag found in .env")
        else:
            print("⚠️  YOLOv8 usage flag not set in .env")
    else:
        print(f"⚠️  Environment file not found: {env_file}")
    
    print("\n" + "=" * 50)
    
    if model_found and required_labels.exists():
        print("🎉 YOLOv8 setup appears to be complete!")
        print("   Your obstacle detection system should be ready to use YOLOv8.")
        sys.exit(0)
    else:
        print("❌ YOLOv8 setup is incomplete.")
        print("\n📋 Setup Instructions:")
        print("   1. Export YOLOv8 model to TFLite on a PC (see documentation above)")
        print("   2. Copy the .tflite file to the models/ directory")
        print("   3. Copy the label map (coco_labels.txt) to the models/ directory")
        print("   4. Update your .env file with the model configuration")
        print("   5. Restart the mower software")
        print("\n   For detailed instructions, see the documentation in this script.")
        sys.exit(1)


if __name__ == "__main__":
    main()