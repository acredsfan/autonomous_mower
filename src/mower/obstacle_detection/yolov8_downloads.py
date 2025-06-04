# Suppress matplotlib Axes3D warning globally
import logging
import sys
import warnings
from pathlib import Path

warnings.filterwarnings(
    "ignore",
    message=("Unable to import Axes3D. This may be due to multiple versions of " "Matplotlib"),
    category=UserWarning,
)

"""
YOLOv8 TFLite Model Setup Script for Autonomous Mower (Documentation Only)

This script no longer attempts to convert YOLOv8 models to TFLite on Raspberry Pi
(Bookworm, Python 3.11+) because TensorFlow export is not supported on this platform.

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

# Script Behavior
This script now only checks for the presence of the YOLOv8 TFLite model and
label map. If either is missing, it logs a clear error and exits. No
conversion or export is attempted.
"""

REQUIRED_MODEL = Path("models/yolov8n_float32.tflite")
REQUIRED_LABELS = Path("models/coco_labels.txt")

if not REQUIRED_MODEL.exists() or not REQUIRED_LABELS.exists():
    logging.error("\nYOLOv8 TFLite model or label map not found.")
    logging.error(
        "Please follow the instructions in this script to export " "the model on a supported PC and copy it to your Pi."
    )
    sys.exit(1)

logging.info("YOLOv8 TFLite model and label map found. Setup complete.")
