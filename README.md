# Autonomous Mower Project

A sophisticated autonomous robotic mower system designed for precise lawn care with advanced navigation, obstacle avoidance, and remote management capabilities.

## Overview

This project implements a complete control system for an autonomous lawn mower robot, featuring:

- GPS-based navigation and path planning
- Computer vision for obstacle detection
- Inertial measurement for orientation tracking
- Web-based remote control interface
- Comprehensive sensor integration
- Safety monitoring and emergency handling
- Autonomous operation with scheduled mowing

## Features

- Autonomous navigation using GPS and IMU
- Path planning based on defined boundaries
- Obstacle detection and avoidance using ultrasonic sensors
- Visual obstacle detection via camera
- **NEW: Hardware-accelerated machine learning with Google Coral TPU**
- Web-based control interface
- Real-time status monitoring
- Diagnostic and calibration tools
- Scheduling capabilities

## System Architecture

The autonomous mower is built around a modular architecture with the following core components:

### Hardware Components
- **Central Processing Unit**: Raspberry Pi 4 (4GB+ recommended)
- **Motor Control**: RoboHAT motor driver
- **Navigation**: GPS module for position tracking
- **Orientation**: BNO085 IMU for heading and attitude
- **Obstacle Detection**: 
  - VL53L0X Time-of-Flight distance sensors
  - Camera module for computer vision
- **Environmental Sensing**:
  - BME280 temperature/humidity/pressure sensor
  - INA3221 power monitoring
- **Connectivity**: WiFi/Ethernet for remote monitoring

### Software Architecture
- **Main Controller**: Central coordination system (`main_controller.py`)
- **Resource Manager**: Dependency injection for hardware access
- **Path Planning**: Efficient mowing path generation
- **Navigation**: Position tracking and movement control
- **Obstacle Avoidance**: Real-time detection and navigation
- **Web Interface**: Browser-based monitoring and control
- **Safety Systems**: Multi-layered monitoring and fail-safes

## Installation

### Prerequisites
- Raspberry Pi 4 (or compatible single-board computer)
- Python 3.9+ with pip
- Required hardware components (see Hardware Components)
- Internet connection for package installation

### Setup Instructions

1. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/autonomous_mower.git
   cd autonomous_mower
   ```

2. **Set up a virtual environment**:
   ```bash
   # Create a virtual environment
   python3 -m venv venv --system-site-packages
   
   # Activate the virtual environment
   source venv/bin/activate
   
   # Upgrade pip within the virtual environment
   pip install --upgrade pip
   ```

3. **Install dependencies**:
   ```bash
   # Install the project and its dependencies
   pip install -e .
   
   # For Coral TPU support (optional)
   pip install -e ".[coral]"
   ```

4. **Hardware setup**:
   - Connect all hardware components according to the [wiring diagram](docs/wiring_diagram.pdf)
   - Ensure correct power supply for motors and electronics
   - Mount sensors in appropriate positions on the mower chassis

5. **Configuration**:
   - Copy the example configuration:
     ```bash
     cp .env.example .env
     ```
   - Edit `.env` with your specific settings (GPS port, motor pins, etc.)
   - Set up your mowing area using the web interface

6. **Run the system**:
   ```bash
   # Make sure the virtual environment is activated
   source venv/bin/activate  # If not already activated
   
   # Run the main controller
   python -m mower.main_controller
   ```

7. **For easy startup, create a shell script**:
   ```bash
   echo '#!/bin/bash
   cd "$(dirname "$0")"
   source venv/bin/activate
   python -m mower.main_controller
   ' > start_mower.sh
   
   chmod +x start_mower.sh
   ```
   Now you can start the mower with `./start_mower.sh`

### Alternative: Use the Installation Script

For a guided installation process with all dependencies:

```bash
# Make the installation script executable
chmod +x install_requirements.sh

# Run the installation script
./install_requirements.sh
```

This script will:
- Install system dependencies
- Ask if you want to install Coral TPU support
- Set up a virtual environment
- Install Python packages
- Configure environment variables

### Docker Installation

For containerized deployment:

1. **Build the Docker image**:
   ```bash
   docker build -t autonomous_mower .
   ```

2. **Run with hardware access**:
   ```bash
   docker run --privileged -p 8080:8080 -v /dev:/dev autonomous_mower
   ```

## Usage Guide

### Web Interface

The mower can be controlled through a web interface available at `http://[mower-ip]:8080`:

- **Dashboard**: View system status, battery level, and sensor readings
- **Control Panel**: Manual control and operation mode selection
- **Map View**: GPS position tracking and path visualization
- **Settings**: Configure mowing areas, schedules, and parameters

### Operation Modes

The mower supports several operational modes:

1. **Manual Control**: Direct control via the web interface
2. **Scheduled Operation**: Automatic mowing according to configured schedule
3. **Single Mow**: Complete one mowing cycle and return to dock
4. **Return to Home**: Navigate back to charging station

### Customizing Mowing Areas

1. Access the web interface and navigate to the Map view
2. Use the drawing tools to define the mowing boundaries
3. Mark exclusion zones for areas to avoid (flower beds, obstacles)
4. Save the configuration, which will be used for autonomous operation

## Troubleshooting

### Common Issues

#### System Won't Start
- **Check power supply**: Ensure adequate power to all components
- **Verify connections**: Confirm all hardware is properly connected
- **Check logs**: Examine `logs/mower.log` for error messages
- **GPIO conflicts**: Ensure no conflicts in GPIO pin assignments

#### Navigation Problems
- **Poor GPS signal**: Place the mower in an open area with clear sky view
- **IMU calibration**: Run the calibration procedure in a flat area
- **Compass interference**: Keep the mower away from large metal objects

#### Motor Issues
- **Motors not moving**: Check motor driver connections and power
- **Erratic movement**: Verify motor controller configuration
- **Wheel slippage**: Adjust speed parameters for terrain conditions

#### Web Interface Issues
- **Can't connect**: Verify network connection and port forwarding
- **Blank page**: Check browser compatibility (use Chrome or Firefox)
- **No data updates**: Verify WebSocket connection is not blocked

### Diagnostic Tools

The system includes several diagnostic tools:

- **Hardware Test**: `python -m mower.diagnostics.hardware_test`
- **Sensor Test**: `python -m mower.diagnostics.sensor_test`
- **Motor Test**: `python -m mower.diagnostics.motor_test`
- **GPS Test**: `python -m mower.diagnostics.gps_test`

## Development and Contribution

### Project Structure
```
autonomous_mower/
├── src/
│   └── mower/
│       ├── hardware/        # Hardware interfaces
│       ├── navigation/      # Path planning and navigation
│       ├── obstacle_detection/ # Obstacle avoidance
│       ├── ui/              # User interfaces
│       │   └── web_ui/     # Web interface
│       └── utilities/       # Helper functions
├── config/                  # Configuration files
├── logs/                    # Log output
├── docs/                    # Documentation
└── tests/                   # Unit and integration tests
```

### Development Environment Setup

1. **Set up a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install in development mode**:
   ```bash
   pip install -e ".[dev]"
   ```

3. **Run tests**:
   ```bash
   pytest
   ```

### Contribution Guidelines

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests to ensure functionality
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

Please follow the [coding standards](docs/coding_standards.md) and include appropriate tests.

## Safety Considerations

The autonomous mower is a powerful machine with moving parts. Always:

- Test in a controlled environment before deployment
- Keep children and pets away during operation
- Monitor initial operation to ensure proper function
- Install physical safety features (bump sensors, blade guards)
- Use the emergency stop function when necessary


## Acknowledgments

- Thanks to all contributors who have helped develop this project, especially @TCIII.
- Special thanks to the open-source communities whose libraries made this possible
- Inspired by various autonomous robotics projects and commercial mowing solutions

## Contact

For questions, support, or contributions, please open an issue on the GitHub repository or contact the maintainers directly.

## Hardware Acceleration

The mower now supports the Google Coral USB Accelerator for enhanced obstacle detection performance:

- **10x faster inference** for real-time obstacle detection
- Lower CPU usage and power consumption
- Improved safety with faster detection of people, animals, and obstacles
- Automatic fallback to CPU if Coral device is not available

See the [Coral TPU Setup Guide](docs/coral_setup.md) for installation and configuration instructions.