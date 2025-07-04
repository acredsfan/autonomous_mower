"""
Setup script for the autonomous_mower package.

This script defines the package metadata, dependencies, and entry points for
command-line scripts. It uses setuptools to allow for pip installation and
dependency management.
"""

from setuptools import find_packages, setup

setup(
    name="autonomous_mower",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "numpy>=1.22.0",
        "opencv-python>=4.8.1.78",
        "pillow>=10.3.0",
        "pyyaml>=5.4.1",
        "python-dotenv>=0.19.0",
        "smbus2>=0.5.0",
        "RPi.GPIO>=0.7.0",
        "adafruit-circuitpython-mpu6050>=1.1.9",
        "flask>=3.0.0",
        "flask-socketio>=5.5.1",
        "geopy>=2.1.0",
        "imutils>=0.5.4",
        "networkx>=2.6.0",
        "pathfinding>=1.0.0",
        "pyserial>=3.5",
        "rtree>=1.0.0",
        "shapely>=2.0.7",
        # "tensorflow>=2.13.0",  # Removed for Raspberry Pi OS Lite compatibility.
        # Use tflite-runtime instead.
        "colorama>=0.4.4",
        "watchdog>=5.0.0",
        "psutil>=5.9.0",
        "py3nvml>=0.2.7",
        "pyudev>=0.24.3",
        "systemd-python>=234",
        "python-daemon>=3.0.1",
        "supervisor>=4.2.5",
        "prometheus_client>=0.17.0",
        "pynmea2>=1.18.0",
        "gpsd-py3>=0.3.0",
        "utm>=0.7.0",
        "adafruit-circuitpython-bme280>=3.0.0",
        "adafruit-circuitpython-bno08x>=1.0.0",
        "adafruit-circuitpython-ina3221>=1.0.0",
        "adafruit-circuitpython-vl53l0x>=3.0.0",
        "picamera2>=0.3.12",
        "certifi>=2024.7.4",
    ],
    extras_require={
        "coral": [
            "tflite-runtime>=2.5.0",
        ],
        "yolo": [
            "ultralytics>=8.1.0",
            "onnx>=1.15.0",
            "onnxruntime>=1.16.0",
        ],
        "ddns": [
            "requests>=2.26.0",
            "schedule>=1.1.0",
        ],
        "cloudflare": [
            "cloudflare>=2.8.0",
            "cryptography>=3.4.0",
        ],
        "ssl": [
            "certbot>=1.12.0",
            "cryptography>=3.4.0",
        ],
        "safety": [
            "safety>=3.2.14",
            "bandit>=1.7.5",
            "pyOpenSSL>=23.0.0",
            "certifi>=2023.7.22",
        ],
        "monitoring": [
            "prometheus_client>=0.17.0",
            "grafana-api-client>=2.3.0",
            "statsd>=4.0.1",
        ],
        "dev": [
            "pytest>=8.3.5",
            "black>=24.3.0",
            "flake8>=3.9.2",
            "mypy>=0.910",
            "pytest-cov>=4.1.0",
            "pytest-mock>=3.12.0",
            "pytest-asyncio>=0.23.5",
            "pytest-timeout>=2.2.0",
            "pytest-xdist>=3.6.1",
            "coverage>=7.4.1",
            "tox>=4.15.0",
            "sphinx>=7.4.7",
            "sphinx-rtd-theme>=2.0.0",
            "pre-commit>=3.6.0",
            "safety>=2.3.0",
            "bandit>=1.7.5",
        ],
    },
    python_requires=">=3.9",
    entry_points={
        "console_scripts": [
            "mower=mower.main_controller:main",
            "mower-test=mower.diagnostics.hardware_test:main",
            "mower-calibrate=mower.diagnostics.imu_calibration:main",
            "mower-logs=mower.utilities.logging_config:view_logs",
            "mower-monitor=mower.diagnostics.system_monitor:main",
            "mower-safety=mower.diagnostics.safety_check:main",
        ],
    },
    author="Your Name",
    author_email="your.email@example.com",
    description="An autonomous lawn mower control system",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/autonomous_mower",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Scientific/Engineering :: Robotics",
    ],
)
