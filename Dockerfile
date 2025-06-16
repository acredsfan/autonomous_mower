# Use an official Python runtime as a parent image

# Use a Raspberry Pi OS Bookworm (armv7) base image for Pi 4B compatibility

# Use Raspberry Pi OS Bookworm 64-bit (arm64) as base for Pi 4B/5 compatibility
FROM arm64v8/python:3.11-bookworm

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1


# Install system dependencies for Raspberry Pi robotics (arm64)
RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    udev \
    python3.11 \
    python3.11-venv \
    python3.11-dev \
    python3-smbus \
    i2c-tools \
    python3-blinka \
    libgpiod2 \
    libatlas-base-dev \
    libffi-dev \
    libssl-dev \
    libjpeg-dev \
    zlib1g-dev \
    libopenjp2-7 \
    libtiff5 \
    libavformat-dev \
    libswscale-dev \
    libavcodec-dev \
    libqtgui4 \
    libqt4-test \
    libilmbase-dev \
    libopenexr-dev \
    libgstreamer1.0-0 \
    libgstreamer-plugins-base1.0-0 \
    pkg-config \
    git \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Ensure python3 points to python3.11
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1
RUN python3 --version


# (Optional) Set up Coral repository and install Edge TPU runtime (armv7)
RUN echo "deb https://packages.cloud.google.com/apt coral-edgetpu-stable main" | \
    tee /etc/apt/sources.list.d/coral-edgetpu.list && \
    curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key add - && \
    apt-get update && \
    apt-get install -y libedgetpu1-std && \
    rm -rf /var/lib/apt/lists/*


# Set work directory to project root
WORKDIR /home/pi/autonomous_mower

# Copy project files to the container
COPY . /home/pi/autonomous_mower/

# Create necessary directories
RUN mkdir -p /home/pi/autonomous_mower/models

# Download the TensorFlow models (if not present)
RUN wget -q https://github.com/google-coral/test_data/raw/master/ssd_mobilenet_v2_coco_quant_postprocess.tflite -O /home/pi/autonomous_mower/models/detect.tflite
RUN wget -q https://github.com/google-coral/test_data/raw/master/ssd_mobilenet_v2_coco_quant_postprocess_edgetpu.tflite -O /home/pi/autonomous_mower/models/detect_edgetpu.tflite
RUN wget -q https://raw.githubusercontent.com/google-coral/test_data/master/coco_labels.txt -O /home/pi/autonomous_mower/models/labelmap.txt


# Install Python dependencies using requirements.txt and setup.py
RUN python3 -m pip install --upgrade pip
RUN python3 -m pip install --no-cache-dir -r requirements.txt
RUN python3 -m pip install --no-cache-dir -e .
RUN python3 -m pip install --no-cache-dir adafruit-blinka


# Expose necessary ports for Web UI and API
EXPOSE 5000 8080


# Set environment variables for Flask and models
ENV FLASK_APP=src/mower/main_controller:main
ENV ML_MODEL_PATH=/home/pi/autonomous_mower/models
ENV DETECTION_MODEL=detect.tflite
ENV TPU_DETECTION_MODEL=detect_edgetpu.tflite
ENV LABEL_MAP_PATH=/home/pi/autonomous_mower/models/labelmap.txt
ENV MIN_CONF_THRESHOLD=0.5

# Entry point to run the application (update path for new project structure)
CMD ["python3", "-m", "src.mower.main_controller"]
