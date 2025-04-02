# setup.py
from setuptools import setup, find_packages

setup(
    name="autonomous_mower",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "flask>=2.0.0,<3.0.0",
        "flask-socketio>=5.1.0,<6.0.0",
        "geopy>=2.1.0,<3.0.0",
        "imutils>=0.5.4",
        "networkx>=2.6.0",
        "opencv-python-headless>=4.5.1,<5.0.0",
        "pathfinding>=1.0.0",
        "pillow>=8.2.0,<9.0.0",
        "pyserial>=3.5,<4.0.0",
        "python-dotenv>=0.19.0,<1.0.0",
        "rtree>=1.0.0",
        "shapely>=1.7.1,<2.0.0",
        "tensorflow>=2.12.0,<2.13.0",
        "numpy<2.0.0",  # Constraint to avoid conflicts
        "colorama>=0.4.4",  # For colored terminal output
        "watchdog>=2.1.0",  # For file system monitoring
    ],
    extras_require={
        "coral": [
            "pycoral>=0.2.0,<0.3.0",
            "tflite-runtime>=2.5.0",
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
        "dev": [
            "pytest>=6.2.0",
            "black>=21.5b2",
            "flake8>=3.9.0",
            "mypy>=0.910",
            "pytest-cov>=2.12.0",
            "pytest-mock>=3.6.1",
            "pytest-asyncio>=0.15.1",
            "pytest-timeout>=1.4.2",
            "pytest-xdist>=2.4.0",
            "coverage>=6.0",
            "tox>=3.24.0",
            "sphinx>=4.2.0",
            "sphinx-rtd-theme>=0.5.2",
            "pre-commit>=2.15.0",
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
