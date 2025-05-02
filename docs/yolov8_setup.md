# YOLOv8 TFLite Model Setup (Local Export)

This document describes how to set up a YOLOv8 TFLite model for obstacle detection using the local export script (`scripts/setup_yolov8.py`). This method requires the `ultralytics` library to be installed in your environment and exports the model directly from the source `.pt` file.

## Prerequisites

- Python 3.8+
- `pip` (Python package installer)
- Git (for cloning the repository)
- An internet connection (for downloading the base `.pt` model and dependencies if needed)

## Setup Script (`scripts/setup_yolov8.py`)

The script automates the process of exporting a YOLOv8 model to the TFLite format suitable for the autonomous mower project.

### Functionality

1.  **Detects Repository Root:** Finds the project's root directory (where the `.git` folder is located) to ensure paths are handled correctly.
2.  **Parses Arguments:** Takes command-line arguments to specify the model size (`--model`), output directory (`--output`), image size (`--imgsz`), quantization options (`--fp16` or `--int8`), and calibration dataset (`--data` for INT8).
3.  **Installs Dependencies (Optional):** The script includes a function (`install_dependencies`) to check for and install required Python packages (`ultralytics`, `opencv-python`, `numpy`, `pillow`). This step is commented out by default, assuming the user manages their Python environment. It can be uncommented if needed.
4.  **Exports Model:**
    - Loads the specified pre-trained YOLOv8 model (`.pt` file) using the `ultralytics` library (downloads it automatically if not found locally).
    - Exports the model to TFLite format (`.tflite`) with the specified image size and quantization.
    - Handles FP16 (`--fp16`) and INT8 (`--int8`) quantization. INT8 requires a dataset YAML file (`--data`) for calibration (e.g., `coco128.yaml`). If `--int8` is used without `--data`, `ultralytics` might use a default dataset, potentially leading to suboptimal results.
    - Locates the exported `.tflite` file (usually saved by `ultralytics` in the current working directory or a subdirectory) and moves it to the designated output directory (defaults to `<repo_root>/models/`).
5.  **Saves Label Map:** Creates a `coco_labels.txt` file containing the standard COCO object detection labels in the output directory.
6.  **Updates Environment File (`.env`):** Modifies the `.env` file in the repository root:
    - Sets `YOLO_MODEL_PATH` to the relative path (from repo root) of the exported `.tflite` model.
    - Sets `YOLO_LABEL_PATH` to the relative path of the `coco_labels.txt` file.
    - Ensures `USE_YOLOV8=True` is present and set.
    - **Comments out** potentially conflicting older model path variables (like `OBSTACLE_MODEL_PATH`, `LABEL_MAP_PATH`, `TPU_DETECTION_MODEL`, `DETECTION_MODEL`) to avoid conflicts.

### Usage

Navigate to the repository root directory in your terminal and run the script:

```bash
# Ensure your Python environment with 'ultralytics' is active
python scripts/setup_yolov8.py [OPTIONS]
```

**Options:**

- `--model {yolov8n,yolov8s,yolov8m}`: Select the YOLOv8 model size. (Default: `yolov8n`)
- `--output <PATH>`: Specify the directory to save the model and label file. (Default: `<repo_root>/models/`)
- `--imgsz <SIZE>`: Input image size for the exported model. (Default: `640`)
- `--fp16`: Export using FP16 (half-precision floating-point) quantization.
- `--int8`: Export using INT8 (8-bit integer) quantization. Offers potentially faster inference and smaller model size.
- `--data <YAML_PATH>`: Path to the dataset configuration file (e.g., `coco128.yaml`) used for INT8 calibration. **Recommended if `--int8` is used.**

**Examples:**

1.  **Export YOLOv8n (default) with FP32 to `models/` directory:**

    ```bash
    python scripts/setup_yolov8.py
    ```

2.  **Export YOLOv8s with FP16 quantization:**

    ```bash
    python scripts/setup_yolov8.py --model yolov8s --fp16
    ```

3.  **Export YOLOv8n with INT8 quantization using `coco128.yaml`:**

    ```bash
    # Ensure coco128.yaml is accessible relative to where you run the script
    # or provide an absolute path.
    python scripts/setup_yolov8.py --int8 --data coco128.yaml
    ```

4.  **Export YOLOv8m to a custom directory `custom_models/` with image size 320:**

    ```bash
    python scripts/setup_yolov8.py --model yolov8m --output custom_models --imgsz 320
    ```

## After Running the Script

1.  **Verify Files:** Check the specified output directory (e.g., `models/`) for the `.tflite` model file (e.g., `yolov8n_float16.tflite`) and `coco_labels.txt`.
2.  **Verify `.env`:** Open the `.env` file in the repository root. Confirm that `YOLO_MODEL_PATH`, `YOLO_LABEL_PATH`, and `USE_YOLOV8=True` are set correctly and that old model path variables are commented out (prefixed with `#`).
3.  **Target Device:** Ensure the `tflite-runtime` package is installed on the target device (e.g., the Raspberry Pi). The setup script **does not** install `tflite-runtime`.

    ```bash
    # On the Raspberry Pi (example)
    pip install tflite-runtime
    ```

## Troubleshooting

- **`ultralytics` not found:** Ensure you have installed the package in the Python environment you are using to run the script (`pip install ultralytics`).
- **INT8 Calibration Error:** If INT8 export fails due to dataset issues:
  - Ensure the `--data` path points to a valid YAML file accessible by the script.
  - Ensure the corresponding dataset images are available if needed by `ultralytics` (it might try to download them).
- **File Not Found After Export:** The script tries to locate the exported `.tflite` file based on the `ultralytics` export function's return value and common naming patterns. If it still fails:
  - Check the script's console output for messages from the `ultralytics` export process (it might indicate the exact save location).
  - Manually search your current working directory and potential subdirectories (like `yolov8n_export/`) for the `.tflite` file and move it to the `models/` directory.
  - Manually update the `.env` file with the correct relative path.
- **Permissions Errors (pip):** If uncommenting the dependency installer, `pip install` might require `sudo` or the `--user` flag on Linux if not in a virtual environment. The script attempts `--break-system-packages`, but manual installation might be needed.
- **`.env` File Issues:** Ensure the script has write permissions for the `.env` file in the repository root.
