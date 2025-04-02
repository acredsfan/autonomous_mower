# setup.py
from setuptools import setup, find_packages

setup(
    name='autonomous_mower',
    version='0.1.0',
    packages=find_packages(where='src'),
    package_dir={'': 'src'},
    install_requires=[
        'pyserial>=3.5',
        'numpy>=1.19.0',
        'opencv-python-headless>=4.5.1',
        'imutils',
        'tensorflow>=2.5.0',  # For development environment
        'pillow>=8.2.0',
        'flask>=2.0.0',
        'flask-socketio>=5.1.0',
        'python-dotenv>=0.19.0',
        'geopy>=2.1.0',
        'shapely>=1.7.1',
        'rtree',
        'networkx',
        'pathfinding',
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
