"""
Unit tests for configuration management.
"""

import pytest
import tempfile
import yaml
from pathlib import Path

from mower.config.settings import (
    SystemConfig, HardwareConfig, SafetyConfig, ServicesConfig,
    ConfigManager
)


@pytest.mark.unit
class TestSystemConfig:
    """Test system configuration classes."""
    
    def test_default_config_creation(self):
        """Test creating config with defaults."""
        config = SystemConfig()
        
        assert config.hardware.robohat_port == "/dev/ttyACM1"
        assert config.hardware.max_speed == 50
        assert config.safety.command_timeout == 5.0
        assert config.services.web_port == 8080
        assert config.environment == "production"
        assert config.simulation_mode == False
    
    def test_custom_config_creation(self):
        """Test creating config with custom values."""
        hardware = HardwareConfig(
            robohat_port="/dev/ttyUSB0",
            max_speed=30
        )
        
        safety = SafetyConfig(
            command_timeout=3.0,
            max_tilt_angle=20.0
        )
        
        config = SystemConfig(
            hardware=hardware,
            safety=safety,
            simulation_mode=True
        )
        
        assert config.hardware.robohat_port == "/dev/ttyUSB0"
        assert config.hardware.max_speed == 30
        assert config.safety.command_timeout == 3.0
        assert config.safety.max_tilt_angle == 20.0
        assert config.simulation_mode == True
    
    def test_hardware_config_validation(self):
        """Test hardware config validation."""
        # Valid ranges
        config = HardwareConfig(
            steering_range=(-100, 100),
            throttle_range=(-50, 50)
        )
        assert config.steering_range == (-100, 100)
        
        # Invalid range (min >= max)
        with pytest.raises(ValueError):
            HardwareConfig(steering_range=(100, -100))
        
        # Invalid range (not tuple of 2)
        with pytest.raises(ValueError):
            HardwareConfig(steering_range=(0, 50, 100))


@pytest.mark.unit
class TestConfigManager:
    """Test configuration manager."""
    
    def test_config_file_loading(self):
        """Test loading configuration from file."""
        # Create temporary config file
        config_data = {
            'hardware': {
                'robohat_port': '/dev/ttyTest',
                'max_speed': 25
            },
            'safety': {
                'command_timeout': 2.0
            },
            'simulation_mode': True
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_path = Path(f.name)
        
        try:
            manager = ConfigManager(config_path)
            config = manager.load_config()
            
            assert config.hardware.robohat_port == '/dev/ttyTest'
            assert config.hardware.max_speed == 25
            assert config.safety.command_timeout == 2.0
            assert config.simulation_mode == True
            
        finally:
            config_path.unlink()
    
    def test_config_file_missing(self):
        """Test behavior when config file is missing."""
        non_existent_path = Path("/non/existent/config.yaml")
        manager = ConfigManager(non_existent_path)
        
        # Should load defaults when file doesn't exist
        config = manager.load_config()
        assert config.hardware.robohat_port == "/dev/ttyACM1"
        assert config.safety.command_timeout == 5.0
    
    def test_config_merging(self):
        """Test configuration merging."""
        manager = ConfigManager()
        
        base_config = {
            'hardware': {
                'robohat_port': '/dev/ttyACM1',
                'max_speed': 50
            },
            'safety': {
                'command_timeout': 5.0
            }
        }
        
        override_config = {
            'hardware': {
                'max_speed': 30
            },
            'simulation_mode': True
        }
        
        merged = manager._merge_configs(base_config, override_config)
        
        assert merged['hardware']['robohat_port'] == '/dev/ttyACM1'  # From base
        assert merged['hardware']['max_speed'] == 30  # From override
        assert merged['safety']['command_timeout'] == 5.0  # From base
        assert merged['simulation_mode'] == True  # From override
    
    def test_config_saving(self):
        """Test saving configuration to file."""
        config = SystemConfig(
            simulation_mode=True,
            hardware=HardwareConfig(max_speed=25)
        )
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            config_path = Path(f.name)
        
        try:
            manager = ConfigManager(config_path)
            manager.save_config(config)
            
            # Verify file was created and contains correct data
            assert config_path.exists()
            
            with open(config_path, 'r') as f:
                saved_data = yaml.safe_load(f)
            
            assert saved_data['simulation_mode'] == True
            assert saved_data['hardware']['max_speed'] == 25
            
        finally:
            if config_path.exists():
                config_path.unlink()
    
    def test_config_reload(self):
        """Test configuration reloading."""
        config_data = {
            'hardware': {'max_speed': 30},
            'simulation_mode': True
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_path = Path(f.name)
        
        try:
            manager = ConfigManager(config_path)
            
            # Load initial config
            config1 = manager.load_config()
            assert config1.hardware.max_speed == 30
            
            # Modify file
            config_data['hardware']['max_speed'] = 40
            with open(config_path, 'w') as f:
                yaml.dump(config_data, f)
            
            # Reload should pick up changes
            config2 = manager.reload_config()
            assert config2.hardware.max_speed == 40
            
        finally:
            config_path.unlink()


@pytest.mark.unit
def test_config_validation_edge_cases():
    """Test configuration validation edge cases."""
    
    # Test empty ranges
    with pytest.raises(ValueError):
        HardwareConfig(steering_range=())
    
    # Test single value range
    with pytest.raises(ValueError):
        HardwareConfig(steering_range=(50,))
    
    # Test equal min/max
    with pytest.raises(ValueError):
        HardwareConfig(steering_range=(50, 50))
    
    # Test negative port numbers
    config = ServicesConfig(web_port=-1)
    # This should be valid as pydantic will handle validation
    
    # Test very large timeout values
    config = SafetyConfig(command_timeout=1000.0)
    assert config.command_timeout == 1000.0
