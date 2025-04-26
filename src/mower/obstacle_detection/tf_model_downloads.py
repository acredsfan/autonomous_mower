# download_and_convert_model.py

import argparse
import logging

import kagglehub
import tensorflow as tf

logging.basicConfig(level=logging.INFO)


def download_model():
    logging.info("Downloading the model using kagglehub...")
    # Download the model using kagglehub
    model_path = kagglehub.model_download(
        "google/mobilenet-v2/tensorFlow2/100-224-classification"
    )
    logging.info(f"Model downloaded to {model_path}")
    return model_path


def convert_model(saved_model_dir, tflite_model_path):
    logging.info("Converting the model to TFLite format...")
    converter = tf.lite.TFLiteConverter.from_saved_model(saved_model_dir)
    # Optional: Set optimizations
    converter.optimizations = [tf.lite.Optimize.DEFAULT]
    try:
        tflite_model = converter.convert()
        with open(tflite_model_path, "wb") as f:
            f.write(tflite_model)
        logging.info(f"TFLite model saved to {tflite_model_path}")
    except Exception as e:
        logging.error(f"Model conversion failed: {e}")


def main(output_path):
    # Download the model
    saved_model_dir = download_model()
    # Convert and save the model
    convert_model(saved_model_dir, output_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Download and convert model to TFLite."
    )
    parser.add_argument(
        "--output_path",
        type=str,
        required=True,
        help="The output path for the converted TFLite model.",
    )
    args = parser.parse_args()
    main(args.output_path)
