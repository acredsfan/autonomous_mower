# Autonomous Mower Agent Instructions

## Project Overview
This is an autonomous lawn mower built on a microservices architecture using Redis for communication. The system runs on Raspberry Pi with custom hardware integration.

## Key Commands

### Build & Test
- `python -m pytest` - Run all tests
- `python -m pytest mower/tests/unit/` - Run unit tests only
- `python -m pytest test_phase2_integration.py` - Run integration tests
- `python -m mypy mower/` - Type checking
- `python -m black mower/` - Code formatting

### Service Management
- `python -m mower.tools.launcher start` - Start all microservices
- `python -m mower.tools.launcher stop` - Stop all services
- `python -m mower.tools.launcher status` - Check service status
- `sudo systemctl start autonomous-mower-v3` - Start via systemd
- `sudo systemctl status autonomous-mower-v3` - Check systemd status

### Installation & Setup
- `sudo python3 mower/tools/setup.py` - Install system dependencies and setup
- `pip install -r requirements.txt` - Install Python dependencies
- `sudo systemctl start redis-server` - Start Redis (required)

### Development
- Web interface: `http://mower-ip:8080`
- Redis CLI: `redis-cli` (for debugging message queues)
- Hardware simulation: Add `--simulation` flag to launcher

## Architecture
- **Microservices**: Motor Control, Sensor, Vision, Navigation, Web Service, Mission Controller
- **Communication**: Redis pub/sub and message queues
- **Hardware Abstraction**: HAL layer for RoboHAT and sensor interfaces
- **Safety**: Multi-layer safety system with emergency stops
- **Configuration**: YAML-based configuration in `mower/config/`

## Important Files
- `mower/core/communication/base_service.py` - Base class for all services
- `mower/core/hal/hardware_manager.py` - Hardware abstraction layer
- `mower/tools/launcher.py` - Service management
- `mower/config/config.yaml` - Main configuration
- `deployment/autonomous-mower-v3.service` - Systemd service file

## Hardware
- **Serial Port**: `/dev/ttyACM1` (RoboHAT)
- **Protocol**: `PWM,steering,throttle\r`
- **I2C Sensors**: BME280, INA3221, ToF sensors
- **Camera**: USB/CSI camera for vision processing

## Code Style
- Use type hints throughout
- Follow existing patterns in `mower/core/`
- Services inherit from `BaseService`
- Use Redis for all inter-service communication
- Hardware access only through HAL layer

## Documentation and Workspace Hygiene
- Keep User and Developer documentation up to date at all times
- Clean up temporary or unused code to ensure the Workspace is tidy and easy to navigate
- Use consistent naming conventions and formatting throughout the codebase
