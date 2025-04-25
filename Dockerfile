# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    udev \
    python3-smbus \
    i2c-tools \
    python3-blinka \
    libgpiod2 \
    && rm -rf /var/lib/apt/lists/*

# Set up Coral repository and install Edge TPU runtime
RUN echo "deb https://packages.cloud.google.com/apt coral-edgetpu-stable main" | \
    tee /etc/apt/sources.list.d/coral-edgetpu.list && \
    curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key add - && \
    apt-get update && \
    apt-get install -y libedgetpu1-std && \
    rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Copy project files to the container
COPY . /app/

# Create necessary directories
RUN mkdir -p /app/models

# Download the TensorFlow models
RUN wget -q https://github.com/google-coral/test_data/raw/master/ssd_mobilenet_v2_coco_quant_postprocess.tflite -O /app/models/detect.tflite
RUN wget -q https://github.com/google-coral/test_data/raw/master/ssd_mobilenet_v2_coco_quant_postprocess_edgetpu.tflite -O /app/models/detect_edgetpu.tflite
RUN wget -q https://raw.githubusercontent.com/google-coral/test_data/master/coco_labels.txt -O /app/models/labelmap.txt

# Install Python dependencies using setup.py
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -e .
RUN pip install --no-cache-dir -e ".[coral]"
RUN pip install --no-cache-dir adafruit-blinka

# Expose necessary ports
EXPOSE 5000 8080

# Define environment variable for Flask
ENV FLASK_APP=mower.main_controller:main

# Set environment variables for models
ENV ML_MODEL_PATH=/app/models
ENV DETECTION_MODEL=detect.tflite
ENV TPU_DETECTION_MODEL=detect_edgetpu.tflite
ENV LABEL_MAP_PATH=/app/models/labelmap.txt
ENV MIN_CONF_THRESHOLD=0.5

# Entry point to run the application
CMD ["python", "-m", "mower.main_controller"]
