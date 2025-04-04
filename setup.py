# setup.py
from setuptools import setup, find_packages

setup(
    name="autonomous_mower",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "flask>=3.0.2,<4.0.0",
        "flask-socketio>=5.3.6,<6.0.0",
        "geopy>=2.4.1,<3.0.0",
        "imutils>=0.5.4,<0.6.0",
        "networkx>=3.2.1,<4.0.0",
        "opencv-python-headless>=4.9.0.80,<5.0.0",
        "pathfinding>=1.0.0,<2.0.0",
        "pillow>=11.0.0",
        "pyserial>=3.5,<4.0.0",
        "python-dotenv>=1.0.1,<2.0.0",
        "rtree>=1.0.1,<2.0.0",
        "shapely>=2.0.2,<3.0.0",
        "tensorflow>=2.15.0,<2.16.0",
        "numpy>=1.26.4,<2.0.0",
        "colorama>=0.4.6,<0.5.0",
        "watchdog>=3.0.0,<4.0.0",
        "pynmea2>=1.18.0,<2.0.0",
        "gpsd-py3>=0.3.0,<0.4.0",
        "libgpiod>=0.2.0,<0.3.0",
        "utm>=0.7.0,<0.8.0",
        "adafruit-circuitpython-bme280>=2.6.4,<3.0.0",
    ],
    extras_require={
        "coral": [
            "pycoral>=2.0.0,<3.0.0",
            "tflite-runtime>=2.14.0",
        ],
        "ddns": [
            "requests>=2.31.0,<3.0.0",
            "schedule>=1.2.1,<2.0.0",
        ],
        "cloudflare": [
            "cloudflare>=2.8.15,<3.0.0",
            "cryptography>=42.0.2,<43.0.0",
        ],
        "ssl": [
            "certbot>=2.8.0,<3.0.0",
            "cryptography>=42.0.2,<43.0.0",
        ],
        "dev": [
            "pytest>=8.0.0,<9.0.0",
            "black>=24.1.1,<25.0.0",
            "flake8>=7.0.0,<8.0.0",
            "mypy>=1.8.0,<2.0.0",
            "pytest-cov>=4.1.0,<5.0.0",
            "pytest-mock>=3.12.0,<4.0.0",
            "pytest-asyncio>=0.23.5,<0.24.0",
            "pytest-timeout>=2.2.0,<3.0.0",
            "pytest-xdist>=3.5.0,<4.0.0",
            "coverage>=7.4.1,<8.0.0",
            "tox>=4.15.0,<5.0.0",
            "sphinx>=7.2.6,<8.0.0",
            "sphinx-rtd-theme>=2.0.0,<3.0.0",
            "pre-commit>=3.6.0,<4.0.0",
        ],
    },
    python_requires=">=3.9",
    entry_points={
        "console_scripts": [
            "mower=mower.main_controller:main",
            "mower-test=mower.diagnostics.hardware_test:main",
            "mower-calibrate=mower.diagnostics.imu_calibration:main",
            "mower-logs=mower.utilities.logging_config:view_logs",
        ],
    },
    author="Your Name",
    author_email="your.email@example.com",
    description="An autonomous lawn mower control system",
    long_description=open("README.md").read(),
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
