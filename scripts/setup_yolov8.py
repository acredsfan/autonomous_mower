
# Suppress matplotlib Axes3D warning globally
import importlib.util
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
if importlib.util.find_spec("matplotlib") is None:
    pass  # matplotlib not available; suppress Axes3D warning if needed

# --- Hard Version Check for Export Compatibility ---
REQUIRED_TF_VERSION = "2.14"
REQUIRED_FLATBUFFERS_VERSION = "23."


def get_installed_version(package_name):
    """Get the installed version of a package using pip show."""
    try:
        result = subprocess.run([
            sys.executable, "-m", "pip", "show", package_name
        ], capture_output=True, text=True)
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if line.startswith('Version:'):
                    return line.split(':', 1)[1].strip()
    except Exception:
        pass
    return None


def ensure_required_versions():
    import sys
    import subprocess
    # Check current installed versions using pip (not module imports)
    tf_ver = get_installed_version("tensorflow")
    flatbuffers_ver = get_installed_version("flatbuffers")
    installations_needed = []

    # Check TensorFlow version
    if tf_ver is None:
        print("TensorFlow not found - installing...")
        tf_install_spec = f"tensorflow=={REQUIRED_TF_VERSION}.*"
        installations_needed.append(("tensorflow", tf_install_spec))
    elif not tf_ver.startswith(REQUIRED_TF_VERSION):
        print(
            f"TensorFlow {tf_ver} found, downgrading to {REQUIRED_TF_VERSION}...")
        tf_install_spec = f"tensorflow=={REQUIRED_TF_VERSION}.*"
        installations_needed.append(("tensorflow", tf_install_spec))
    else:
        print(f"TensorFlow {tf_ver} is compatible.")

    # Check FlatBuffers version
    if flatbuffers_ver is None:
        print("FlatBuffers not found - installing...")
        fb_install_spec = f"flatbuffers=={REQUIRED_FLATBUFFERS_VERSION}*"
        installations_needed.append(("flatbuffers", fb_install_spec))
    elif not flatbuffers_ver.startswith(REQUIRED_FLATBUFFERS_VERSION):
        print(f"FlatBuffers {flatbuffers_ver} found, downgrading to "
              f"{REQUIRED_FLATBUFFERS_VERSION}...")
        fb_install_spec = f"flatbuffers=={REQUIRED_FLATBUFFERS_VERSION}*"
        installations_needed.append(("flatbuffers", fb_install_spec))
    else:
        print(f"FlatBuffers {flatbuffers_ver} is compatible.")

    # Install packages if needed
    if installations_needed:
        for package_name, install_spec in installations_needed:
            print(f"Installing {install_spec}...")
            result = subprocess.run([
                sys.executable, "-m", "pip", "install",
                install_spec,
                "--break-system-packages"
            ], capture_output=True, text=True)
            if result.returncode != 0:
                print(f"Failed to install {package_name}: {result.stderr}")
                sys.exit(1)

        # Verify installations
        print("Verifying installations...")
        tf_ver_new = get_installed_version("tensorflow")
        flatbuffers_ver_new = get_installed_version("flatbuffers")

        if tf_ver_new and tf_ver_new.startswith(REQUIRED_TF_VERSION):
            print(f"✓ TensorFlow {tf_ver_new} installed successfully")
        else:
            print(
                f"✗ TensorFlow installation verification failed: {tf_ver_new}")
            sys.exit(1)

        if (flatbuffers_ver_new and
                flatbuffers_ver_new.startswith(REQUIRED_FLATBUFFERS_VERSION)):
            print(
                f"✓ FlatBuffers {flatbuffers_ver_new} installed successfully")
        else:
            print(f"✗ FlatBuffers installation verification failed: "
                  f"{flatbuffers_ver_new}")
            sys.exit(1)

        print("All required versions installed. Restarting script with new packages...")
        # Restart the script to pick up new package versions
        import os
        os.execv(sys.executable, [sys.executable] + sys.argv)
    else:
        print("All required package versions are already satisfied.")


# !/usr/bin/env python3
"""
YOLOv8 TFLite Model Setup Script for Autonomous Mower (Revised for Export)

This script:
1. Exports the appropriate YOLOv8 model to TFLite format locally.
2. Saves the corresponding COCO label map.
3. Sets up the environment variables.
4. Updates configuration files.
5. Ensures dependencies are installed.

Usage:
  python3 setup_yolov8.py [--model yolov8n|yolov8s|yolov8m][--imgsz 640]
  [--fp16 | --int8]
  [--data path/to/coco.yaml]
"""


# --- Add necessary imports ---
try:
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
        help=(
            "Output directory for model and label files "
            "(default: <repo_root>/models/)"
        ),
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
    # Fallback if not in a git repo (e.g., running script directly)
    logging.warning(
        "Could not find .git directory. Assuming current directory is root."
    )
    return Path.cwd().absolute()


def install_dependencies():
    """Install required Python packages."""
    logging.info("Checking and installing dependencies...")
    # Ensure 'ultralytics' is installed first if not already checked
    required = [
        "ultralytics",
        # "tflite-runtime",  # Optional here, needed on target device
        "opencv-python",
        "pillow",
        "numpy",
    ]
    installed_count = 0
    for package in required:
        try:
            # Using --break-system-packages might be needed on some systems
            subprocess.check_call(
                [
                    sys.executable,
                    "-m",
                    "pip",
                    "install",
                    package,
                    "--break-system-packages",  # May be needed on Linux
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
                "× Failed to run pip. Is Python/pip configured correctly?")
            return False  # Critical failure
    return installed_count > 0


def export_yolov8_model(model_name: str, output_dir: Path, export_args: dict):
    """
    Exports the specified YOLOv8 model to TFLite format locally.
    """
    try:
        pt_model_name = f"{model_name}.pt"
        logging.info(f"Loading base model: {pt_model_name}...")
        model = YOLO(pt_model_name)  # Downloads .pt if needed

        logging.info(
            f"Exporting {model_name} to TFLite with args: {export_args}...")
        output_dir.mkdir(parents=True, exist_ok=True)

        # Determine expected filename based on export args
        quant_suffix = ""
        if export_args.get("half"):  # Check for FP16
            quant_suffix = "_float16"
        elif export_args.get("int8"):  # Check for INT8
            quant_suffix = "_int8"
        # Default is FP32, ultralytics might add _float32

        # Run export (it might save file relative to CWD)
        export_result_path_str = model.export(**export_args)
        logging.info(
            f"Ultralytics export function returned: "
            f"{export_result_path_str}"
        )

        # --- Locate the exported file ---
        found_path = None
        expected_filename = ""
        if (
            export_result_path_str
            and Path(export_result_path_str).is_file()
            and Path(export_result_path_str).name.endswith(".tflite")
        ):
            found_path = Path(export_result_path_str)
            expected_filename = found_path.name  # Use the actual name
            logging.info(
                f"Located exported model at: {found_path}"
            )
        else:
            # Fallback search if the return value wasn't helpful
            logging.warning(
                "Export function did not return a valid path. Searching...")
            # Try common patterns
            possible_filenames = [
                f"{model_name}{quant_suffix}.tflite",
                f"{model_name}_float32.tflite",  # If FP32 adds suffix
                f"{model_name}.tflite",  # If no suffix added
            ]
            search_dirs = [Path.cwd(), Path.cwd() / f"{model_name}_export"]

            for sdir in search_dirs:
                if not sdir.is_dir():
                    continue
                for fname in possible_filenames:
                    potential_path = sdir / fname
                    if potential_path.is_file():
                        found_path = potential_path
                        expected_filename = fname
                        logging.info(
                            f"Found exported model at: {found_path}"
                        )
                        break
                if found_path:
                    break

        # --- Move file to target output dir ---
        if found_path:
            target_model_path = output_dir / expected_filename
            try:
                output_dir.mkdir(parents=True, exist_ok=True)
                found_path.rename(target_model_path)
                logging.info(
                    f"Moved exported model to: {target_model_path}"
                )
                return target_model_path
            except OSError as e:
                logging.error(
                    f"Failed to move model from {found_path} to "
                    f"{target_model_path}: {e}"
                )
                return None  # Indicate failure
        else:
            logging.error(
                f"Could not locate the exported TFLite file for {model_name}. "
                "Export might have failed or saved to an unexpected "
                "location."
            )
            return None

    except Exception as e:
        logging.error(
            f"Error during model export for {model_name}: {e}",
            exc_info=True
        )
        # FlatBuffers/TensorFlow/onnx2tf version bug detection
        if ("Builder.EndVector() missing 1 required positional argument" in str(
                e) or "EndVector()" in str(e)):
            logging.error(
                "\n❌ TFLite export failed due to a known incompatibility "
                "between TensorFlow, FlatBuffers, and onnx2tf.\n"
                "Try downgrading TensorFlow to 2.14.x and FlatBuffers to 23.x, "
                "and ensure onnx2tf is >=1.26.0.\n"
                "See: https://github.com/onnx/onnx-tensorflow/issues/1682 "
                "and Ultralytics export docs.\n")
        if "Dataset 'None' not found" in str(e) and export_args.get("int8"):
            logging.error(
                "INT8 quantization requires a dataset. "
                "Please provide --data path/to/coco.yaml"
            )
        return None


def save_label_map(output_dir: Path):
    """Saves the COCO label map to the specified directory."""
    labelmap_path = output_dir / "coco_labels.txt"
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        with open(labelmap_path, "w") as f:
            f.write("\n".join(COCO_LABELS))
        logging.info(
            f"COCO label map saved to {labelmap_path}"
        )
        return labelmap_path
    except IOError as e:
        logging.error(f"Failed to save label map to {labelmap_path}: {e}")
        return None


def update_env_file(model_path: Path, labelmap_path: Path):
    """Update .env file with YOLOv8 paths relative to repo root."""
    repo_root = get_repo_root()
    env_file = repo_root / ".env"
    logging.info(f"Updating environment variables in: {env_file}")

    # Make paths relative to the repo root for portability
    try:
        relative_model_path = model_path.relative_to(repo_root)
        relative_label_path = labelmap_path.relative_to(repo_root)
    except ValueError:
        logging.warning(
            f"Model/Label paths ({model_path}, {labelmap_path}) are outside "
            f"the repo root ({repo_root}). Using absolute paths in .env."
        )
        relative_model_path = model_path
        relative_label_path = labelmap_path

    # Use forward slashes for paths in .env
    model_path_str = str(relative_model_path).replace("\\", "/")
    label_path_str = str(relative_label_path).replace("\\", "/")

    lines = []
    updated_model = False
    updated_label = False
    updated_flag = False
    yolo_section_exists = False

    if env_file.exists():
        with open(env_file, "r") as f:
            lines = f.readlines()

    output_lines = []
    for line in lines:
        stripped_line = line.strip()
        # Check for YOLOv8 specific lines
        if stripped_line.startswith(
                "YOLO_MODEL_PATH="):  # Changed from YOLOV8_
            output_lines.append(f"YOLO_MODEL_PATH={model_path_str}\n")
            updated_model = True
            yolo_section_exists = True
        # Changed from LABEL_MAP_
        elif stripped_line.startswith("YOLO_LABEL_PATH="):
            output_lines.append(f"YOLO_LABEL_PATH={label_path_str}\n")
            updated_label = True
            yolo_section_exists = True
        elif stripped_line.startswith("USE_YOLOV8="):
            output_lines.append("USE_YOLOV8=True\n")
            updated_flag = True
            yolo_section_exists = True
        elif stripped_line == "# YOLOv8 configuration":  # Keep header
            output_lines.append(line)
            yolo_section_exists = True
        # Check for old/conflicting lines to comment out
        elif (
            stripped_line.startswith("OBSTACLE_MODEL_PATH=") or
            stripped_line.startswith("LABEL_MAP_PATH=") or  # Old name
            stripped_line.startswith("TPU_DETECTION_MODEL=") or
            stripped_line.startswith("DETECTION_MODEL=")
        ):
            # Comment out old/conflicting model paths if not already commented
            if not stripped_line.startswith("#"):  # Check if already commented
                output_lines.append(f"# {line.strip()}\n")  # Comment out
            else:
                output_lines.append(line)  # Keep already commented
        else:
            # Keep other lines as they are
            output_lines.append(line)

    # Add missing entries if needed
    if not yolo_section_exists:
        output_lines.append("\n# YOLOv8 configuration\n")
    if not updated_model:
        output_lines.append(f"YOLO_MODEL_PATH={model_path_str}\n")
    if not updated_label:
        output_lines.append(f"YOLO_LABEL_PATH={label_path_str}\n")
    if not updated_flag:
        output_lines.append("USE_YOLOV8=True\n")

    # Write updated content back to file
    try:
        with open(env_file, "w") as f:
            f.writelines(output_lines)
        logging.info(f"Successfully updated {env_file}")
    except IOError as e:
        logging.error(f"Failed to write updated {env_file}: {e}")


def main():
    """Main entry point."""
    args = parse_args()

    # --- Ensure required package versions are installed ---
    try:
        ensure_required_versions()
    except Exception as e:
        logging.error(f"Version check/installation failed: {e}")
        sys.exit(1)

    logging.info(f"--- Starting YOLOv8 {args.model} TFLite Setup ---")

    # Determine output directory
    repo_root = get_repo_root()
    output_dir = args.output if args.output else repo_root / "models"
    output_dir = output_dir.resolve()  # Ensure absolute path
    logging.info(f"Repository root detected: {repo_root}")
    #     sys.exit(1)
    # logging.info("Dependencies checked/installed.")

    # --- Prepare Export Arguments ---
    export_args = {
        "format": "tflite",
        "imgsz": args.imgsz,
        "nms": False,  # NMS=False recommended for TFLite export
    }
    quant_type = "FP32 (default)"
    if args.fp16:
        export_args["half"] = True
        quant_type = "FP16"
    elif args.int8:
        export_args["int8"] = True
        quant_type = "INT8"
        if args.data:
            export_args["data"] = args.data
            logging.info(f"Using calibration data: {args.data}")
        else:
            logging.warning(
                "INT8 quantization enabled without explicit --data. "
                "Ultralytics might use a default dataset (e.g., coco128.yaml)."
            )
    logging.info(
        f"Preparing export for {args.model} with image size {args.imgsz} "
        f"and quantization {quant_type}."  # Corrected typo
    )

    # --- Export Model ---
    logging.info("Starting model export...")
    model_path = export_yolov8_model(args.model, output_dir, export_args)
    if not model_path:
        logging.error("Model export failed. See previous errors.")
        sys.exit(1)  # Exit if export failed
    logging.info(f"Model export successful: {model_path}")

    # --- Save Label Map ---
    logging.info("Saving COCO label map...")  # Corrected typo
    labelmap_path = save_label_map(output_dir)
    if not labelmap_path:
        logging.error("Failed to save label map.")
        logging.warning("Proceeding without label map update in .env")
    else:
        logging.info(f"Label map saved successfully: {labelmap_path}")

    # --- Update Environment File ---
    if model_path and labelmap_path:
        logging.info("Updating .env file...")
        update_env_file(model_path, labelmap_path)
    elif model_path:
        logging.warning(
            "Skipping .env update because label map saving failed.")
    else:
        # This case shouldn't be reached due to sys.exit(1) earlier
        logging.warning("Skipping .env update because model export failed.")

    # --- Final Summary ---
    logging.info("--- YOLOv8 Setup Summary ---")  # Corrected typo
    if model_path:
        logging.info(f"  Model Path: {model_path}")
    else:
        logging.error("  Model Path: FAILED")  # Corrected typo

    if labelmap_path:
        logging.info(f"  Label Map Path: {labelmap_path}")
    else:
        logging.warning("  Label Map Path: FAILED (or skipped)")

    if model_path and labelmap_path:  # Corrected typo
        logging.info(f"  .env file updated at: {repo_root / '.env'}")
        logging.info("\n✓ YOLOv8 setup process completed successfully!")
        logging.info(  # Corrected typo
            "  Ensure 'tflite-runtime' is installed on the target device.")
    else:
        logging.error("\n× YOLOv8 setup process finished with errors.")
        sys.exit(1)


if __name__ == "__main__":
    main()
