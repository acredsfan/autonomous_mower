"""Test YOLOv8 TFLite model inference."""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import numpy as np
import tflite_runtime.interpreter as tflite  # type: ignore
from PIL import Image


def run_inference_test(model_path: str, image_path: str, input_size: int) -> None:
    """Run a simple inference against the supplied model and image."""
    interpreter = tflite.Interpreter(model_path=model_path)
    interpreter.allocate_tensors()

    input_details = interpreter.get_input_details()[0]
    output_details = interpreter.get_output_details()[0]

    img = Image.open(image_path).resize((input_size, input_size))
    img_rgb = img.convert("RGB")
    input_data = np.expand_dims(img_rgb, axis=0).astype(input_details["dtype"])

    interpreter.set_tensor(input_details["index"], input_data)

    start = time.time()
    interpreter.invoke()
    output_data = interpreter.get_tensor(output_details["index"])
    end = time.time()

    print(f"Inference completed in {end - start:.2f}s. Output shape: {output_data.shape}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test YOLOv8 TFLite model inference.")
    parser.add_argument("-m", "--model", required=True, help="Path to the .tflite model file.")
    parser.add_argument("-i", "--image", required=True, help="Path to the test image file.")
    parser.add_argument("-s", "--size", type=int, default=640, help="Input image size.")
    args = parser.parse_args()

    run_inference_test(args.model, args.image, args.size)
