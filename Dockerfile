# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libatlas-base-dev \
    libhdf5-dev \
    libhdf5-serial-dev \
    python3-dev \
    python3-pip \
    i2c-tools \
    gpsd \
    gpsd-clients \
    python3-gps \
    python3-libgpiod \
    libportaudio2 \
    libportaudiocpp0 \
    portaudio19-dev \
    python3-picamera2\
    wget \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Copy project files to the container
COPY . /app/

# Create necessary directories
RUN mkdir -p /app/src/mower/config/models

# Download the TensorFlow model
RUN wget -q https://storage.googleapis.com/tfhub-lite-models/tensorflow/lite-model/mobilenet_v2_1.0_224/1/metadata/1.tflite -O /app/src/mower/config/models/mobilenet_v2_1.0_224.tflite

# Install Python dependencies using setup.py
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -e .

# Expose necessary ports
EXPOSE 5000 8080

# Define environment variable for Flask
ENV FLASK_APP=mower.main_controller:main

# Entry point to run the application
CMD ["python", "-m", "mower.main_controller"]
