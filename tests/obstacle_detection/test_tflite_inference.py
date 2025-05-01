import numpy as np
import tflite_runtime.interpreter as tflite  # Use the runtime interpreter
from PIL import Image
import time
import argparse


def run_inference_test(model_path, image_path, input_size_wh):
    """Loads a TFLite model and runs inference on a test image."""

    # --- Load Model ---
    print(f"Loading model: {model_path}")
    try:
        interpreter = tflite.Interpreter(model_path=model_path)
        interpreter.allocate_tensors()  # Crucial step
    except Exception as e:
        print(f"Error loading model or allocating tensors: {e}")
        return

    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()
    print("Model Input Details:", input_details)
    print("Model Output Details:", output_details)

    # --- Validate Input Shape ---
    try:
        input_shape = input_details[
            "shape"
        ]  # Expected shape (e.g., [1, height, width, 3])
        input_type = input_details["dtype"]  # Expected type (e.g., float32, uint8)
        print(f"Expected input shape: {input_shape}, type: {input_type}")

        # Check if expected shape matches specified input size
        # Shape is usually [batch, height, width, channels]
        expected_height, expected_width = input_shape, input_shape
        if expected_height != input_size_wh or expected_width != input_size_wh:
            print(
                f"Warning: Model expected input size ({expected_height}x{expected_width}) "
                f"differs from specified input size ({input_size_wh}x{input_size_wh}). "
                f"Using model's expected size for preprocessing."
            )
            input_size_wh = (expected_width, expected_height)

    except (IndexError, KeyError) as e:
        print(f"Error parsing input details: {e}")
        return

    # --- Prepare Input Image ---
    print(f"Loading and preparing image: {image_path}")
    try:
        img = Image.open(image_path).resize(input_size_wh)  # Resize to W, H
        img_rgb = img.convert("RGB")
        input_data = np.expand_dims(img_rgb, axis=0)  # Add batch dimension

        # Normalize based on model input type
        if np.issubdtype(input_type, np.float32):
            input_data = input_data.astype(np.float32) / 255.0
            print("Normalized input to  for float32 model.")
        elif np.issubdtype(input_type, np.uint8):
            input_data = input_data.astype(np.uint8)
            print("Using uint8 input for quantized model.")
        else:
            print(
                f"Warning: Unsupported input dtype {input_type}. Assuming no normalization needed."
            )
            input_data = input_data.astype(input_type)

        interpreter.set_tensor(input_details["index"], input_data)

    except FileNotFoundError:
        print(f"Error: Test image not found at {image_path}")
        return
    except Exception as e:
        print(f"Error preparing input image: {e}")
        return

    # --- Run Inference ---
    print("Running inference...")
    start_time = time.time()
    try:
        interpreter.invoke()
    except Exception as e:
        print(f"Error during interpreter invocation: {e}")
        return
    end_time = time.time()
    inference_time = end_time - start_time
    print(f"Inference successful! Time: {inference_time:.4f} seconds")

    # --- Get Output ---
    # Output tensor structure depends heavily on the export configuration (e.g., NMS included or not)
    # Example: YOLOv8 often outputs a tensor like [batch, 84, num_proposals] where 84 = 4 (box) + 80 (classes)
    # Or it could be multiple output tensors. Check output_details.
    try:
        output_data = interpreter.get_tensor(output_details["index"])
        print(f"Output tensor shape: {output_data.shape}")
        # Print a small sample of the output for inspection
        print(
            "Sample output data (first proposal, first 10 values):",
            output_data[0, :10, 0] if output_data.ndim == 3 else output_data[0, :10],
        )

        print("\nBasic inference test complete.")
        print(
            "Next steps involve implementing code to parse this output tensor, apply score thresholding, and perform Non-Maximum Suppression (NMS) if not included in the model."
        )

    except Exception as e:
        print(f"Error getting or printing output tensor: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test YOLOv8 TFLite model inference.")
    parser.add_argument(
        "-m", "--model", required=True, help="Path to the.tflite model file."
    )
    parser.add_argument(
        "-i", "--image", required=True, help="Path to the test image file."
    )
    parser.add_argument(
        "-s",
        "--size",
        type=int,
        default=640,
        help="Input image size (square) used during export (e.g., 640).",
    )
    args = parser.parse_args()

    run_inference_test(args.model, args.image, (args.size, args.size))
