#!/usr/bin/env python3
"""
Autonomous Mower Setup Tool

This script provides an easy way to set up and configure the autonomous mower system.
"""

import os
import sys
import subprocess
import shutil
import logging
from pathlib import Path
from typing import Optional, List
import click
import yaml

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


class SetupError(Exception):
    """Setup-related error."""
    pass


class MowerSetup:
    """Autonomous mower setup manager."""
    
    def __init__(self, base_path: Optional[Path] = None):
        """Initialize setup manager.
        
        Args:
            base_path: Base installation path (defaults to current directory)
        """
        self.base_path = base_path or Path.cwd()
        self.config_path = self.base_path / "mower" / "config" / "config.yaml"
        self.service_path = Path("/etc/systemd/system/autonomous-mower-v3.service")
        
        # System requirements
        self.required_packages = [
            "redis-server",
            "python3-pip",
            "python3-venv",
            "git"
        ]
        
        # Python requirements for Raspberry Pi
        self.rpi_packages = [
            "python3-gpiozero",
            "python3-picamera2",
            "i2c-tools"
        ]
    
    def check_system_requirements(self) -> bool:
        """Check if system meets requirements."""
        logger.info("Checking system requirements...")
        
        # Check if running on Linux
        if os.name != 'posix':
            logger.error("This system requires Linux (Raspberry Pi OS recommended)")
            return False
        
        # Check Python version
        if sys.version_info < (3, 9):
            logger.error("Python 3.9 or higher is required")
            return False
        
        # Check if running as root (needed for GPIO access)
        if os.geteuid() != 0:
            logger.warning("Some features require root access. Consider running with sudo.")
        
        logger.info("✓ System requirements check passed")
        return True
    
    def install_system_packages(self, skip_packages: bool = False) -> bool:
        """Install required system packages."""
        if skip_packages:
            logger.info("Skipping system package installation")
            return True
        
        logger.info("Installing system packages...")
        
        try:
            # Update package list
            subprocess.run(["sudo", "apt", "update"], check=True, capture_output=True)
            
            # Install required packages
            packages_to_install = self.required_packages.copy()
            
            # Add Raspberry Pi specific packages if detected
            if self._is_raspberry_pi():
                packages_to_install.extend(self.rpi_packages)
                logger.info("Detected Raspberry Pi - installing additional packages")
            
            cmd = ["sudo", "apt", "install", "-y"] + packages_to_install
            subprocess.run(cmd, check=True)
            
            logger.info("✓ System packages installed successfully")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to install system packages: {e}")
            return False
    
    def setup_python_environment(self) -> bool:
        """Set up Python virtual environment and install dependencies."""
        logger.info("Setting up Python environment...")
        
        try:
            # Install Python dependencies using --break-system-packages for Raspberry Pi
            pip_cmd = [sys.executable, "-m", "pip", "install", "--break-system-packages", "-r", "requirements.txt"]
            subprocess.run(pip_cmd, cwd=self.base_path, check=True)
            
            logger.info("✓ Python environment set up successfully")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to set up Python environment: {e}")
            return False
    
    def configure_redis(self) -> bool:
        """Configure Redis server."""
        logger.info("Configuring Redis...")
        
        try:
            # Start and enable Redis service
            subprocess.run(["sudo", "systemctl", "start", "redis-server"], check=True)
            subprocess.run(["sudo", "systemctl", "enable", "redis-server"], check=True)
            
            # Test Redis connection
            subprocess.run(["redis-cli", "ping"], check=True, capture_output=True)
            
            logger.info("✓ Redis configured successfully")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to configure Redis: {e}")
            return False
    
    def create_configuration(self, interactive: bool = True) -> bool:
        """Create system configuration."""
        logger.info("Creating system configuration...")
        
        try:
            # Ensure config directory exists
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Copy template files if they don't exist
            self._setup_template_files()
            
            # Create default configuration manually
            config = {
                'hardware': {
                    'robohat_port': '/dev/ttyACM1',
                    'gps_port': '/dev/ttyUSB0',
                    'max_speed': 50,
                    'simulation_mode': not self._is_raspberry_pi()
                },
                'safety': {
                    'command_timeout': 2.0,
                    'emergency_stop_enabled': True,
                    'max_consecutive_failures': 3
                },
                'services': {
                    'web_port': 8080,
                    'redis_host': 'localhost',
                    'redis_port': 6379
                },
                'logging': {
                    'level': 'INFO',
                    'file': 'logs/mower.log'
                }
            }
            
            if interactive:
                config = self._interactive_config(config)
            
            # Detect hardware configuration
            if self._is_raspberry_pi():
                config['hardware']['robohat_port'] = self._detect_robohat_port()
                config['hardware']['gps_port'] = self._detect_gps_port()
            else:
                config['hardware']['simulation_mode'] = True
                logger.info("Non-Raspberry Pi detected - enabling simulation mode")
            
            # Save configuration
            with open(self.config_path, 'w') as f:
                yaml.dump(config, f, default_flow_style=False)
            
            logger.info(f"✓ Configuration saved to {self.config_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create configuration: {e}")
            return False
    
    def setup_systemd_service(self, enable_service: bool = True) -> bool:
        """Set up systemd service for automatic startup."""
        logger.info("Setting up systemd service...")
        
        try:
            service_content = f"""[Unit]
Description=Autonomous Mower System
After=network.target redis.service
Wants=redis.service

[Service]
Type=exec
User=pi
Group=pi
WorkingDirectory={self.base_path}
ExecStart={sys.executable} -m mower.tools.launcher start
Restart=always
RestartSec=10
Environment=PYTHONPATH={self.base_path}

# Resource limits
MemoryLimit=1G
CPUQuota=80%

# Security settings
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths={self.base_path}/data {self.base_path}/logs

[Install]
WantedBy=multi-user.target
"""
            
            # Write service file
            with open(self.service_path, 'w') as f:
                f.write(service_content)
            
            # Reload systemd and enable service
            subprocess.run(["sudo", "systemctl", "daemon-reload"], check=True)
            
            if enable_service:
                subprocess.run(["sudo", "systemctl", "enable", "autonomous-mower-v3"], check=True)
                logger.info("✓ Systemd service enabled for automatic startup")
            else:
                logger.info("✓ Systemd service created (not enabled)")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to set up systemd service: {e}")
            return False
    
    def create_data_directories(self) -> bool:
        """Create necessary data directories."""
        logger.info("Creating data directories...")
        
        try:
            directories = [
                self.base_path / "data",
                self.base_path / "logs",
                self.base_path / "data" / "maps",
                self.base_path / "data" / "missions",
                Path("/home/pi/mower_data"),
            ]
            
            for directory in directories:
                directory.mkdir(parents=True, exist_ok=True)
                # Set proper permissions
                os.chmod(directory, 0o755)
            
            logger.info("✓ Data directories created")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create data directories: {e}")
            return False
    
    def run_tests(self) -> bool:
        """Run system tests to verify installation."""
        logger.info("Running system tests...")
        
        try:
            # Run basic tests
            test_cmd = [sys.executable, "-m", "pytest", "mower/tests/unit", "-v"]
            result = subprocess.run(test_cmd, cwd=self.base_path, capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info("✓ System tests passed")
                return True
            else:
                logger.error(f"System tests failed:\n{result.stdout}\n{result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to run tests: {e}")
            return False
    
    def _is_raspberry_pi(self) -> bool:
        """Check if running on Raspberry Pi."""
        try:
            with open('/proc/cpuinfo', 'r') as f:
                return 'Raspberry Pi' in f.read()
        except:
            return False
    
    def _detect_robohat_port(self) -> str:
        """Detect RoboHAT serial port."""
        possible_ports = ["/dev/ttyACM0", "/dev/ttyACM1", "/dev/ttyUSB0", "/dev/ttyUSB1"]
        
        for port in possible_ports:
            if Path(port).exists():
                logger.info(f"Detected RoboHAT port: {port}")
                return port
        
        logger.warning("Could not detect RoboHAT port, using default")
        return "/dev/ttyACM1"
    
    def _detect_gps_port(self) -> str:
        """Detect GPS serial port."""
        possible_ports = ["/dev/ttyUSB0", "/dev/ttyUSB1", "/dev/ttyAMA0", "/dev/ttyS0"]
        
        for port in possible_ports:
            if Path(port).exists():
                logger.info(f"Detected GPS port: {port}")
                return port
        
        logger.warning("Could not detect GPS port, using default")
        return "/dev/ttyUSB0"
    
    def _interactive_config(self, config):
        """Interactive configuration setup."""
        logger.info("Starting interactive configuration...")
        
        # Hardware configuration
        if click.confirm("Configure hardware settings?", default=True):
            max_speed = click.prompt("Maximum speed (0-100)", default=config['hardware']['max_speed'], type=int)
            if 0 <= max_speed <= 100:
                config['hardware']['max_speed'] = max_speed
        
        # Safety configuration
        if click.confirm("Configure safety settings?", default=True):
            timeout = click.prompt("Command timeout (seconds)", default=config['safety']['command_timeout'], type=float)
            if timeout > 0:
                config['safety']['command_timeout'] = timeout
        
        # Web interface
        if click.confirm("Configure web interface?", default=True):
            port = click.prompt("Web interface port", default=config['services']['web_port'], type=int)
            if 1024 <= port <= 65535:
                config['services']['web_port'] = port
        
        return config
    
    def _setup_template_files(self) -> None:
        """Copy template files to create user configuration if they don't exist."""
        logger.info("Setting up configuration from templates...")
        
        templates = [
            ('mower/config/config.yaml.template', 'mower/config/config.yaml'),
            ('config/boundary.json.template', 'config/boundary.json'),
            ('config/home_location.json.template', 'config/home_location.json')
        ]
        
        for template_path, target_path in templates:
            template_file = self.base_path / template_path
            target_file = self.base_path / target_path
            
            # Create target directory if it doesn't exist
            target_file.parent.mkdir(parents=True, exist_ok=True)
            
            if template_file.exists() and not target_file.exists():
                shutil.copy2(template_file, target_file)
                logger.info(f"✓ Created {target_path} from template")
                
                # Warn about sensitive configuration
                if 'config.yaml' in str(target_path):
                    logger.warning("⚠️  IMPORTANT: Edit mower/config/config.yaml to add your Google Maps API key!")
                elif 'boundary.json' in str(target_path) or 'home_location.json' in str(target_path):
                    logger.warning(f"⚠️  IMPORTANT: Edit {target_path} to set your actual location!")


@click.command()
@click.option('--skip-packages', is_flag=True, help='Skip system package installation')
@click.option('--skip-tests', is_flag=True, help='Skip running tests')
@click.option('--no-service', is_flag=True, help='Do not set up systemd service')
@click.option('--non-interactive', is_flag=True, help='Run without interactive prompts')
@click.option('--base-path', type=click.Path(), help='Base installation path')
def main(skip_packages: bool, skip_tests: bool, no_service: bool, 
         non_interactive: bool, base_path: Optional[str]):
    """Set up the autonomous mower system."""
    
    logger.info("🚜 Autonomous Mower Setup")
    logger.info("=" * 50)
    
    try:
        # Initialize setup manager
        setup_path = Path(base_path) if base_path else Path.cwd()
        setup = MowerSetup(setup_path)
        
        # Check system requirements
        if not setup.check_system_requirements():
            raise SetupError("System requirements not met")
        
        # Install system packages
        if not setup.install_system_packages(skip_packages):
            raise SetupError("Failed to install system packages")
        
        # Set up Python environment
        if not setup.setup_python_environment():
            raise SetupError("Failed to set up Python environment")
        
        # Configure Redis
        if not setup.configure_redis():
            raise SetupError("Failed to configure Redis")
        
        # Create configuration
        if not setup.create_configuration(not non_interactive):
            raise SetupError("Failed to create configuration")
        
        # Create data directories
        if not setup.create_data_directories():
            raise SetupError("Failed to create data directories")
        
        # Set up systemd service
        if not no_service:
            if not setup.setup_systemd_service():
                logger.warning("Failed to set up systemd service (continuing anyway)")
        
        # Run tests
        if not skip_tests:
            if not setup.run_tests():
                logger.warning("Some tests failed (installation may still be functional)")
        
        logger.info("")
        logger.info("🎉 Setup completed successfully!")
        logger.info("")
        logger.info("Next steps:")
        logger.info("1. Review configuration: mower/config/config.yaml")
        logger.info("2. Test the system: mower-test")
        logger.info("3. Start the service: sudo systemctl start autonomous-mower-v3")
        logger.info("4. Check status: mower-status")
        logger.info("")
        
    except SetupError as e:
        logger.error(f"Setup failed: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Setup cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
