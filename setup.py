# setup.py
from setuptools import setup, find_packages

setup(
    name='autonomous_mower',
    version='0.1.0',
    packages=find_packages(where='src'),
    package_dir={'': 'src'},
    install_requires=[
        'smbus2',
        'pyserial',
        'numpy>=1.19.0',
        'adafruit-circuitpython-bme280',
        'adafruit-circuitpython-vl53l0x',
        'easydict',
        'barbudor-circuitpython-ina3221',
        'mpu9250-jmdev',
        'python-dotenv',
        'imutils',
        'pathfinding',
        'shapely>=1.7.1',
        'networkx',
        'rtree',
        'tflite-runtime>=2.5.0;platform_machine!="x86_64"',  # For Raspberry Pi
        'tensorflow>=2.5.0;platform_machine=="x86_64"',  # For x86 systems (development)
        'flask-socketio>=5.0.0',
        'opencv-contrib-python',
        'gpsd-py3',
        'adafruit-circuitpython-tca9548a',
        'gunicorn',
        'eventlet',
        'flask-cors',
        'donkeycar',
        'pynmea2>=1.18.0',
        'requests',
        'pyubx2',
        'adafruit-circuitpython-bno08x',
        'utm',
        'neopixel',
        'readchar',
        'paho-mqtt',
        'gpiod',
        'pyngrok',
        'picamera2',
        'scipy>=1.6.0',
        'pillow>=8.2.0',
        'geopy>=2.1.0',
        'psutil>=5.8.0',
    ],
    extras_require={
        'dev': [
            'pytest>=6.2.5',
            'black>=21.5b2',
            'flake8>=3.9.2',
            'mypy>=0.812',
        ],
        'coral': [
            'pycoral>=2.0.0',  # Google Coral Edge TPU support
        ],
        'simulation': [
            'pygame>=2.0.1',
        ],
    },
    entry_points={
        'console_scripts': [
            'autonomous_mower=mower.mower:main',
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
    python_requires='>=3.6',
)
