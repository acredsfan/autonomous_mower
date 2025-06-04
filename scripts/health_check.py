import os
import sys

# Ensure the script can find modules from the 'src' directory
# when run from the project root.
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)


def check_import(module_name, class_name=None, is_optional=False, import_note=""):
    """
    Attempts to import a module or a class from a module and prints status.
    """
    full_name = module_name
    if class_name:
        full_name = f"{module_name}.{class_name}"

    print(f"Checking: {full_name}{import_note} ... ", end="")
    try:
        module = __import__(module_name, fromlist=[class_name] if class_name else [])
        if class_name:
            actual_class = getattr(module, class_name)
            # For some hardware classes, instantiation might try to access hardware.
            # We'll try a basic instantiation if it's a common pattern,
            # but mostly focus on importability.
            if class_name in [
                "GPIOManager",
                "BNO085Sensor",
                "INA3221Sensor",
                "VL53L0XSensors",
                "RoboHATDriver",
                "BladeController",
            ]:
                print(f"(Class {class_name} imported, attempting basic instantiation...) ", end="")
                # Wrap instantiation in its own try-except for hardware errors
                try:
                    _ = actual_class()
                    print("SUCCESS (imported and instantiated)")
                except Exception as e:
                    print(f"PARTIAL SUCCESS (imported, but instantiation failed: {type(e).__name__} - {e})")
            elif class_name == "ObstacleDetector":
                # ObstacleDetector requires a resource_manager argument
                print(f"(Class {class_name} imported, skipping instantiation as it requires args) ", end="")
                print("SUCCESS (imported)")
            else:
                print("SUCCESS (imported)")
        else:
            print("SUCCESS (imported)")
        return True
    except ImportError as e:
        if is_optional:
            print(f"NOT FOUND (optional: {e})")
        else:
            print(f"FAILED (ImportError: {e})")
        return False
    except ModuleNotFoundError as e:
        if is_optional:
            print(f"NOT FOUND (optional: {e})")
        else:
            print(f"FAILED (ModuleNotFoundError: {e})")
        return False
    except RuntimeError as e:
        if is_optional:
            print(f"RUNTIME ERROR (optional: {e})")
        else:
            print(f"FAILED (RuntimeError: {e})")
        return False
    except Exception as e:  # Catch any other exceptions during import/init
        if is_optional:
            print(f"ERROR (optional: {type(e).__name__} - {e})")
        else:
            print(f"FAILED ({type(e).__name__} - {e})")
        return False


def main():
    print("--- Starting Basic Health Check ---")
    print(f"Project Root: {PROJECT_ROOT}")
    print(f"Source Directory (added to path): {SRC_DIR}\n")

    checks = [
        ("mower.main_controller", "ResourceManager", False, ""),
        ("mower.hardware.gpio_manager", "GPIOManager", False, ""),
        ("mower.hardware.imu", "BNO085Sensor", False, ""),
        ("mower.hardware.ina3221", "INA3221Sensor", False, ""),
        ("mower.hardware.tof", "VL53L0XSensors", False, ""),
        ("mower.hardware.robohat", "RoboHATDriver", False, ""),
        ("mower.hardware.blade_controller", "BladeController", False, ""),
        ("mower.hardware.camera_instance", "get_camera_instance", False, ""),
        ("mower.obstacle_detection.obstacle_detector", "ObstacleDetector", False, ""),
        ("tflite_runtime.interpreter", "Interpreter", False, " (as TFLiteInterpreter)"),
        ("pycoral.utils.edgetpu", "EdgeTpuManager", True, " (optional)"),
    ]

    all_passed = True
    for module, class_obj, optional, note in checks:
        if not check_import(module, class_obj, optional, note):
            if not optional:
                all_passed = False

    print("\n--- Health Check Summary ---")
    if all_passed:
        print("All critical modules imported successfully (or instantiated where attempted).")
        print(
            "Note: For hardware-related modules, successful import/instantiation does not guarantee full hardware functionality, only that the Python code is accessible and parsable."
        )
    else:
        print("Some critical module checks failed. Please review the errors above.")

    print("Health check finished.")


if __name__ == "__main__":
    main()
