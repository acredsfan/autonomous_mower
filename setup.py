# setup.py
from setuptools import setup, find_packages

setup(
    name='autonomous_mower',
    version='0.1.0',
    packages=find_packages(where='src'),
    package_dir={'': 'src'},
    install_requires=[
        # Hardware interfaces
        'smbus2',
        'pyserial>=3.5',
        'RPi.GPIO>=0.7.0;platform_machine!="x86_64"',  # GPIO for Raspberry Pi
        'gpiozero;platform_machine!="x86_64"',  # High-level GPIO
        'gpiod',
        'pigpio;platform_machine!="x86_64"',  # Advanced GPIO
        
        # Sensors and modules
        'adafruit-circuitpython-bme280',  # Environmental sensor
        'adafruit-circuitpython-vl53l0x',  # Time-of-flight sensor
        'adafruit-circuitpython-tca9548a',  # I2C multiplexer
        'adafruit-circuitpython-bno08x',  # IMU sensor
        'barbudor-circuitpython-ina3221',  # Power monitoring
        'mpu9250-jmdev',  # Alternative IMU
        'neopixel',  # LED control
        
        # Navigation and positioning
        'pynmea2>=1.18.0',  # NMEA parsing for GPS
        'pyubx2',  # u-blox GPS parser
        'utm',  # UTM coordinate conversion
        'geopy>=2.1.0',  # Geo calculations
        'shapely>=1.7.1',  # Geometric operations
        'rtree',  # Spatial indexing
        'networkx',  # Graph operations for pathfinding
        'pathfinding',  # Path planning algorithms
        
        # Vision and ML
        'numpy>=1.19.0',  # Numerical processing
        'opencv-python-headless>=4.5.1',  # Lighter OpenCV variant for headless systems
        'imutils',  # OpenCV utilities
        'tflite-runtime>=2.5.0;platform_machine!="x86_64"',  # For Raspberry Pi
        'tensorflow>=2.5.0;platform_machine=="x86_64"',  # For x86 systems (development)
        'picamera2;platform_machine!="x86_64"',  # Raspberry Pi camera
        'pillow>=8.2.0',  # Image processing
        
        # Web interface
        'flask>=2.0.0',  # Web framework
        'flask-socketio>=5.0.0',  # Real-time communication
        'flask-cors',  # Cross-origin resource sharing
        'gunicorn',  # WSGI HTTP server
        'eventlet',  # Concurrent networking
        
        # Utilities
        'python-dotenv',  # Environment variables
        'easydict',  # Easy dictionary access
        'scipy>=1.6.0',  # Scientific computing
        'psutil>=5.8.0',  # System monitoring
        'requests',  # HTTP requests
        'paho-mqtt',  # MQTT client
        'pyngrok',  # Ngrok integration
        'readchar',  # Reading characters from terminal
        'gpsd-py3',  # GPSD interface
        'PyYAML>=6.0',  # YAML parsing
        'schedule',  # Job scheduling
        'humanize',  # Human-readable output
    ],
    extras_require={
        'dev': [
            'pytest>=6.2.5',
            'black>=21.5b2',
            'flake8>=3.9.2',
            'mypy>=0.812',
            'pytest-cov',
            'bandit',  # Security linting
            'pre-commit',  # Pre-commit hooks
            'sphinx',  # Documentation
        ],
        'coral': [
            'pycoral>=2.0.0',  # Google Coral Edge TPU support
        ],
        'simulation': [
            'pygame>=2.0.1',  # For visualization
            'matplotlib>=3.5.0',  # For plotting
        ],
        'remote': [
            'ngrok',  # Remote tunnel
            'zeroconf',  # Service discovery
        ],
    },
    entry_points={
        'console_scripts': [
            'autonomous_mower=mower.main_controller:main',
        ],
    },
    author='Aaron Link',
    author_email='acredsfan@gmail.com',
    description='Raspberry Pi Powered Autonomous Mower Project',
    url='https://github.com/acredsfan/autonomous_mower',
    classifiers=[
        'Programming Language :: Python :: 3',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.9',
)
