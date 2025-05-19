

# Suppress matplotlib Axes3D warning globally
import logging
from pathlib import Path
import subprocess
import argparse
import sys
import warnings
warnings.filterwarnings(
    "ignore",
    message=(
        "Unable to import Axes3D. This may be due to multiple versions of "
        "Matplotlib"
    ),
    category=UserWarning,
)

# --- Hard Version Check for Export Compatibility ---
REQUIRED_TF_VERSION = "2.14"
REQUIRED_FLATBUFFERS_VERSION = "23."


def ensure_required_versions():
    import importlib
    import sys
    import subprocess
    import os
    
    # Add restart counter to prevent infinite loops
    max_restarts = 2
    restart_count = int(os.environ.get('YOLO_RESTART_COUNT', '0'))
    if restart_count > max_restarts:
        print("Error: Maximum number of restarts reached. Please check your environment setup.")
        print(f"Current TensorFlow version: {tf_ver if 'tf_ver' in locals() else 'Not installed'}")
        print(f"Current FlatBuffers version: {flatbuffers_ver if 'flatbuffers_ver' in locals() else 'Not installed'}")
        sys.exit(1)
        
    tf_ver = None
    flatbuffers_ver = None
    
    # Check current versions
    try:
        tf_mod = importlib.import_module("tensorflow")
        tf_ver = getattr(tf_mod, "__version__", None)
    except ImportError:
        pass
    try:
        fb_mod = importlib.import_module("flatbuffers")
        flatbuffers_ver = getattr(fb_mod, "__version__", None)
    except ImportError:
        pass

    # Track if any version actually changes
    version_changed = False

    # Only install if missing or wrong version
    if tf_ver is None or not tf_ver.startswith(REQUIRED_TF_VERSION):
        print(f"Auto-downgrading TensorFlow to {REQUIRED_TF_VERSION}...")
        result = subprocess.run([
            sys.executable, "-m", "pip", "install",
            f"tensorflow=={REQUIRED_TF_VERSION}.*",
            "--break-system-packages"
        ], capture_output=True, text=True)
        if result.returncode != 0:
            print("Failed to install TensorFlow:", result.stderr)
            print("Please try installing manually: "
                  f"pip install 'tensorflow=={REQUIRED_TF_VERSION}.*' --break-system-packages")
            sys.exit(1)
        version_changed = True
        
        # Re-import to verify installation
        try:
            tf_mod = importlib.import_module("tensorflow")
            tf_ver = getattr(tf_mod, "__version__", None)
        except ImportError:
            tf_ver = None

    if flatbuffers_ver is None or not flatbuffers_ver.startswith(REQUIRED_FLATBUFFERS_VERSION):
        print(f"Auto-downgrading FlatBuffers to {REQUIRED_FLATBUFFERS_VERSION}...")
        result = subprocess.run([
            sys.executable, "-m", "pip", "install",
            f"flatbuffers=={REQUIRED_FLATBUFFERS_VERSION}*",
            "--break-system-packages"
        ], capture_output=True, text=True)
        if result.returncode != 0:
            print("Failed to install FlatBuffers:", result.stderr)
            print("Please try installing manually: "
                  f"pip install 'flatbuffers=={REQUIRED_FLATBUFFERS_VERSION}*' --break-system-packages")
            sys.exit(1)
        version_changed = True
        
        # Re-import to verify installation
        try:
            fb_mod = importlib.import_module("flatbuffers")
            flatbuffers_ver = getattr(fb_mod, "__version__", None)
        except ImportError:
            flatbuffers_ver = None

    # Only restart if a version was actually changed and not already correct
    if version_changed and restart_count < max_restarts:
        # Double-check that the versions are now correct before restarting
        tf_ok = tf_ver is not None and tf_ver.startswith(REQUIRED_TF_VERSION)
        fb_ok = flatbuffers_ver is not None and flatbuffers_ver.startswith(
            REQUIRED_FLATBUFFERS_VERSION
        )
        
        if tf_ok and fb_ok:
            print("Versions are now correct. No restart needed.")
        else:
            print("Restarting script to use correct TensorFlow/FlatBuffers versions...")
            os.environ['YOLO_RESTART_COUNT'] = str(restart_count + 1)
            try:
                os.execv(sys.executable, [sys.executable] + sys.argv)
            except Exception as e:
                print(f"Failed to restart script: {e}")
                print("Please run the script again manually.")
                sys.exit(1)
    elif version_changed:
        print("Warning: Version correction attempted but maximum restarts reached.")
        print(f"TensorFlow version: {tf_ver}")
        print(f"FlatBuffers version: {flatbuffers_ver}")
        print("Continuing with current versions, but some features might not work as expected.")
    # If no version changed, continue as normal

# Ensure correct versions before anything else


ensure_required_versions()
#
#!/usr/bin/env python3  # noqa: E265
"""
YOLOv8 TFLite Model Setup Script for Autonomous Mower (Revised for Export)

This script:
1. Exports the appropriate YOLOv8 model to TFLite format locally.
2. Saves the corresponding COCO label map.
3. Sets up the environment variables.
4. Updates configuration files.
5. Ensures dependencies are installed.

# Usage:
#   python3 setup_yolov8.py [--model yolov8n|yolov8s|yolov8m][--imgsz 640]
#   [--fp16 | --int8]
  [--data path/to/coco.yaml]
"""

# import os


def enforce_export_version_requirements():
    import importlib

    missing = []
    tf_ver = None
    flatbuffers_ver = None

    try:
        tf_mod = importlib.import_module("tensorflow")
        tf_ver = getattr(tf_mod, "__version__", None)
    except ImportError:
        missing.append("tensorflow")

    try:
        fb_mod = importlib.import_module("flatbuffers")
        flatbuffers_ver = getattr(fb_mod, "__version__", None)
    except ImportError:
        missing.append("flatbuffers")

    if missing:
        for pkg in missing:
            logging.error(
                f"Required package '{pkg}' is not installed or importable."
            )
            logging.error(
                f"Install it with: pip install '{pkg}'"
            )
        logging.error(
            "Could not determine TensorFlow or FlatBuffers version. "
            "Please ensure both are installed."
        )
        sys.exit(1)

    if not tf_ver or not tf_ver.startswith(REQUIRED_TF_VERSION):
        logging.error(
            f"TensorFlow {REQUIRED_TF_VERSION}.x is required for YOLOv8 TFLite export. "
            f"Found: {tf_ver}. Please downgrade: "
            "pip install 'tensorflow==2.14.*'"
        )
        sys.exit(1)
    if not flatbuffers_ver or not flatbuffers_ver.startswith(
            REQUIRED_FLATBUFFERS_VERSION):
        logging.error(
            f"FlatBuffers 23.x is required for YOLOv8 TFLite export. "
            f"Found: {flatbuffers_ver}. Please downgrade: "
            "pip install 'flatbuffers==23.*'"
        )
        sys.exit(1)
    logging.info(
        f"TensorFlow {tf_ver} and FlatBuffers {flatbuffers_ver} "
        "are compatible for export."
    )


# --- Add necessary imports ---
try:
    enforce_export_version_requirements()
    from ultralytics import YOLO
except ImportError:
    print(
        "Error: 'ultralytics' package not found. Please install it: "
        "pip install ultralytics"
    )
    sys.exit(1)

# --- Configure Logging ---
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# --- COCO Label Map Content ---
COCO_LABELS = """person
bicycle
car
motorcycle
airplane
bus
train
truck
boat
traffic light
fire hydrant
stop sign
parking meter
bench
bird
cat
dog
horse
sheep
cow
elephant
bear
zebra
giraffe
backpack
umbrella
handbag
tie
suitcase
frisbee
skis
snowboard
sports ball
kite
baseball bat
baseball glove
skateboard
surfboard
tennis racket
bottle
wine glass
cup
fork
knife
spoon
bowl
banana
apple
sandwich
orange
broccoli
carrot
hot dog
pizza
donut
cake
chair
couch
potted plant
bed
dining table
toilet
tv
laptop
mouse
remote
keyboard
cell phone
microwave
oven
toaster
sink
refrigerator
book
clock
vase
scissors
teddy bear
hair drier
toothbrush""".splitlines()


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Set up YOLOv8 TFLite model via local export for obstacle detection"
    )
    parser.add_argument(
        "--model",
        choices=["yolov8n", "yolov8s", "yolov8m"],
        default="yolov8n",
        help="YOLOv8 model size (default: yolov8n)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output directory for model and label files (default: models/)",
    )
    parser.add_argument(
        "--imgsz",
        type=int,
        default=640,
        help="Input image size for export (default: 640)",
    )
    quant_group = parser.add_mutually_exclusive_group()
    quant_group.add_argument(
        "--fp16",
        action="store_true",
        help="Export using FP16 quantization (recommended start)",
    )
    quant_group.add_argument(
        "--int8",
        action="store_true",
        help="Export using INT8 quantization (requires --data)",
    )
    parser.add_argument(
        "--data",
        type=str,
        default=None,  # e.g., 'coco128.yaml'
        help="Path to dataset YAML for INT8 calibration (required if --int8)",
    )
    return parser.parse_args()


def get_repo_root():
    """Get the root directory of the repository."""
    current = Path.cwd().absolute()
    while current != current.parent:
        if (current / ".git").exists():
            return current
        current = current.parent
    return Path.cwd().absolute()


def install_dependencies():
    """Install required Python packages."""
    logging.info("Checking and installing dependencies...")
    # Ensure 'ultralytics' is installed first if not already checked
    required = [
        "ultralytics",  # Added dependency
        "tflite-runtime",  # For the target Pi environment
        "opencv-python",
        "pillow",
        "numpy",
        # 'requests', 'tqdm' might not be needed for export, review dependencies
    ]
    installed_count = 0
    for package in required:
        try:
            # Using --break-system-packages might be needed on some systems
            # Consider adding error handling for pip itself
            subprocess.check_call(
                [
                    sys.executable,
                    "-m",
                    "pip",
                    "install",
                    package,
                    "--break-system-packages",
                    "--quiet",
                ]
            )
            logging.info(f"✓ {package} installed/verified.")
            installed_count += 1
        except subprocess.CalledProcessError:
            logging.warning(
                f"× Failed to install {package} via pip. Please install manually.")
        except FileNotFoundError:
            logging.error(
                "× Failed to run pip. Is Python/pip configured correctly in your PATH?")
            return False  # Critical failure
    return installed_count > 0


def export_yolov8_model(model_name: str, output_dir: Path, export_args: dict):
    """
    Exports the specified YOLOv8 model to TFLite format locally.
    """
    try:
        pt_model_name = f"{model_name}.pt"
        logging.info(f"Loading base model: {pt_model_name}...")
        model = YOLO(pt_model_name)  # Downloads.pt if needed

        logging.info(
            f"Exporting {model_name} to TFLite with args: {export_args}...")
        output_dir.mkdir(parents=True, exist_ok=True)

        # --- Perform the export ---
        # The export function might save the file in the CWD or a subfolder.
        # It might return the path, or None, depending on version/format.
        export_result = model.export(**export_args)
        logging.info(f"Ultralytics export function returned: {export_result}")

        # --- Determine expected filename ---
        quant_suffix = "_float16" if export_args.get("half") else "_float32"
        if export_args.get("int8"):
            # Naming convention for INT8 TFLite might vary.
            # Check Ultralytics docs/output.
            # Common patterns: _int8.tflite, _full_integer_quant.tflite
            quant_suffix = "_int8"  # Adjust if needed based on actual output
        expected_filename = f"{model_name}{quant_suffix}.tflite"
        target_model_path = output_dir / expected_filename

        # --- Locate the exported file ---
        # Strategy: Check common locations and move to target output dir.
        found_path = None
        # 1. Check if export_result is the direct path
        if (
            isinstance(export_result, (str, Path))
            and Path(export_result).is_file()
            and Path(export_result).name.endswith(".tflite")
        ):
            potential_path = Path(export_result)
            if potential_path.exists():
                found_path = potential_path
        # 2. Check current working directory for expected name
        if not found_path and (Path.cwd() / expected_filename).exists():
            found_path = Path.cwd() / expected_filename
        # 3. Check for common export subdirectories (Ultralytics might create these)
        # Add more patterns if needed based on observed behavior

        # 4. Fallback: Glob for any matching TFLite file in CWD if specific
        # name fails
        if not found_path:
            possible_files = list(Path.cwd().glob(f"{model_name}*.tflite"))
            if possible_files:
                found_path = possible_files[0]  # Take the first match
                logging.warning(
                    f"Found model via glob search: "
                    f"{found_path}. This may not be the expected file."
                )

        # --- Move file and return path ---
        if found_path:
            try:
                # Ensure target directory exists before renaming
                target_model_path.parent.mkdir(parents=True, exist_ok=True)
                found_path.rename(target_model_path)
                logging.info(
                    f"Successfully exported and moved model to: {target_model_path}")
                return target_model_path
            except OSError as e:
                logging.error(
                    f"Error moving exported file {found_path} to "
                    f"{target_model_path}: {e}")
                # Attempt to copy if rename fails (e.g., different filesystems)
                try:
                    import shutil

                    shutil.copy2(found_path, target_model_path)
                    logging.info(
                        f"Successfully copied model to: {target_model_path} "
                        f"(rename failed)"
                    )
                    # Optionally remove original if copy succeeds
                    # found_path.unlink()
                    return target_model_path
                except Exception as copy_e:
                    logging.error(
                        f"Failed to copy file after rename failed: {copy_e}")
                    return None
        else:
            logging.error(
                f"Export process finished, but the expected TFLite file "
                f"('{expected_filename}' or similar) "
                "was not found in standard locations."
            )
            return None

    except Exception as e:
        logging.error(
            f"Error during model export for {model_name}: {e}",
            exc_info=True)
        # Consider adding checks for specific common errors
        if "Dataset 'None' not found" in str(e) and export_args.get("int8"):
            logging.error(
                "INT8 export requires the '--data' argument specifying a calibration "
                "dataset YAML.")
        return None


def save_label_map(output_dir: Path):
    """Saves the COCO label map to the specified directory."""
    labelmap_path = output_dir / "coco_labels.txt"
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        with open(labelmap_path, "w") as f:
            for label in COCO_LABELS:
                f.write(label + "\n")
        logging.info(f"COCO label map saved to {labelmap_path}")
        return labelmap_path
    except IOError as e:
        logging.error(f"Failed to save label map to {labelmap_path}: {e}")
        return None


def update_env_file(model_path: Path, labelmap_path: Path):
    """Update.env file with YOLOv8 paths."""
    repo_root = get_repo_root()
    env_file = repo_root / ".env"
    logging.info(f"Updating environment variables in: {env_file}")

    lines = []
    updated_model = False
    updated_label = False
    updated_flag = False

    if env_file.exists():
        with open(env_file, "r") as f:
            lines = f.readlines()

    # Process existing lines or prepare to add new ones
    output_lines = []
    for line in lines:
        stripped_line = line.strip()
        if stripped_line.startswith("YOLOV8_MODEL_PATH="):
            output_lines.append(f"YOLOV8_MODEL_PATH={model_path}\n")
            updated_model = True
        elif stripped_line.startswith("LABEL_MAP_PATH="):
            output_lines.append(f"LABEL_MAP_PATH={labelmap_path}\n")
            updated_label = True
        elif stripped_line.startswith("USE_YOLOV8="):
            output_lines.append("USE_YOLOV8=True\n")
            updated_flag = True
        elif stripped_line.startswith("# YOLOv8 configuration"):
            # Keep comment line if it exists
            output_lines.append(line)
        elif stripped_line:  # Keep other non-empty lines
            output_lines.append(line)

    # Add missing entries
    if not updated_model or not updated_label or not updated_flag:
        # Add header if no YOLOv8 config was found before
        if not any(line.strip() == "# YOLOv8 configuration"
                   for line in output_lines):
            output_lines.append("\n# YOLOv8 configuration\n")
        if not updated_model:
            output_lines.append(f"YOLOV8_MODEL_PATH={model_path}\n")
        if not updated_label:
            output_lines.append(f"LABEL_MAP_PATH={labelmap_path}\n")
        if not updated_flag:
            output_lines.append("USE_YOLOV8=True\n")

    # Write updated content back to file
    try:
        with open(env_file, "w") as f:
            f.writelines(output_lines)
        logging.info(f"Successfully updated {env_file}")
    except IOError as e:
        logging.error(f"Failed to write updated.env file: {e}")


def main():
    """Main entry point."""
    args = parse_args()

    logging.info(f"Setting up YOLOv8 {args.model} via local export...")

    # Determine output directory
    repo_root = get_repo_root()
    output_dir = args.output if args.output else repo_root / "models"
    output_dir = output_dir.resolve()  # Ensure absolute path

    # Install dependencies
    if not install_dependencies():
        logging.error("Dependency installation failed. Exiting.")
        sys.exit(1)

    # Prepare export arguments
    export_args = {
        "format": "tflite",
        "imgsz": args.imgsz,
        "nms": False,
    }  # NMS=False recommended
    if args.fp16:
        export_args["half"] = True
        logging.info("Configured for FP16 export.")
    elif args.int8:
        if not args.data:
            logging.error(
                "INT8 export requires '--data' argument "
                "specifying calibration dataset YAML."
            )
            sys.exit(1)
        export_args["int8"] = True
        export_args["data"] = args.data
        logging.info(f"Configured for INT8 export using data: {args.data}")
    else:
        # Default to FP32 if neither --fp16 nor --int8 is specified
        export_args["half"] = False
        export_args["int8"] = False
        logging.info("Configured for FP32 export (default).")

    # Export model
    model_path = export_yolov8_model(args.model, output_dir, export_args)

    # Save label map
    labelmap_path = save_label_map(output_dir)

    if model_path and labelmap_path:
        # Update environment variables
        update_env_file(model_path, labelmap_path)

        logging.info("\n✓ YOLOv8 setup via export complete!")
        logging.info("Model exported to: %s", model_path)
        logging.info("Label map saved to: %s", labelmap_path)
        logging.info("Environment variables updated.")
        logging.info(
            "\nYou can now use the exported YOLOv8 TFLite model for obstacle detection."
        )
        logging.info(
            "The obstacle detector should automatically use "
            "YOLOv8 if configured via.env."
        )
        logging.info("\nTo verify application integration, run:")
        print(  # Use print for user-facing command
            '  python -c "from mower.obstacle_detection.obstacle_detector '
            "import get_obstacle_detector; "
            "detector = get_obstacle_detector(); "
            "print('YOLOv8 enabled:', "
            'detector.yolov8_detector is not None)"'
        )
    else:
        logging.error("\n× YOLOv8 setup via export failed.")
        logging.error("Please check the error messages above and try again.")
        sys.exit(1)


if __name__ == "__main__":
    main()
