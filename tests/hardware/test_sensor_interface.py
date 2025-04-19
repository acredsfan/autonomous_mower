"""
Tests for the EnhancedSensorInterface class.

This module tests the functionality of the EnhancedSensorInterface class in
hardware/sensor_interface.py, including:
1. Initialization of the sensor interface
2. Starting and stopping the sensor interface
3. Reading sensor data
4. Error handling and recovery
5. Thread safety
"""

import pytest
import threading
import time
from unittest.mock import MagicMock, patch, call

from mower.hardware.sensor_interface import (
    EnhancedSensorInterface, SensorStatus, get_sensor_interface
)


class TestEnhancedSensorInterface:
    """Tests for the EnhancedSensorInterface class."""

    @patch("mower.hardware.sensor_interface.busio.I2C")
    def test_initialization(self, mock_i2c):
        """Test initialization of the sensor interface."""
        # Create an EnhancedSensorInterface instance
        sensor_interface = EnhancedSensorInterface()
        
        # Verify that the I2C bus was initialized
        mock_i2c.assert_called_once()
        
        # Verify that the sensor data dictionary was initialized
        assert sensor_interface.sensor_data == {}
        assert sensor_interface._data == {}
        
        # Verify that the error thresholds were initialized
        assert sensor_interface._error_thresholds == {
            'bme280': 3,
            'bno085': 3,
            'ina3221': 3,
            'vl53l0x': 3
        }
        
        # Verify that the sensor status dictionary was initialized
        assert 'bme280' in sensor_interface._sensor_status
        assert 'bno085' in sensor_interface._sensor_status
        assert 'ina3221' in sensor_interface._sensor_status
        assert 'vl53l0x' in sensor_interface._sensor_status
        
        # Verify that the stop event was initialized
        assert isinstance(sensor_interface._stop_event, threading.Event)
        assert not sensor_interface._stop_event.is_set()
        
        # Verify that the sensors dictionary was initialized
        assert sensor_interface._sensors == {
            'bme280': None,
            'bno085': None,
            'ina3221': None,
            'vl53l0x': None
        }
        
        # Verify that the locks were initialized
        assert isinstance(sensor_interface._locks['i2c'], threading.Lock)
        assert isinstance(sensor_interface._locks['data'], threading.Lock)
        assert isinstance(sensor_interface._locks['status'], threading.Lock)

    @patch("mower.hardware.sensor_interface.busio.I2C")
    @patch("mower.hardware.sensor_interface.BME280Sensor")
    @patch("mower.hardware.sensor_interface.BNO085Sensor")
    @patch("mower.hardware.sensor_interface.INA3221Sensor")
    @patch("mower.hardware.sensor_interface.VL53L0XSensors")
    @patch("mower.hardware.sensor_interface.threading.Thread")
    def test_start(
        self, mock_thread, mock_vl53l0x, mock_ina3221, mock_bno085, mock_bme280, mock_i2c
    ):
        """Test starting the sensor interface."""
        # Create an EnhancedSensorInterface instance
        sensor_interface = EnhancedSensorInterface()
        
        # Mock the _init_sensor_with_retry method
        sensor_interface._init_sensor_with_retry = MagicMock(return_value=True)
        
        # Call start
        sensor_interface.start()
        
        # Verify that _init_sensor_with_retry was called for each sensor
        assert sensor_interface._init_sensor_with_retry.call_count == 4
        
        # Verify that the monitoring threads were started
        assert mock_thread.call_count == 2
        mock_thread.return_value.start.assert_called()

    @patch("mower.hardware.sensor_interface.busio.I2C")
    def test_cleanup(self, mock_i2c):
        """Test cleaning up the sensor interface."""
        # Create an EnhancedSensorInterface instance
        sensor_interface = EnhancedSensorInterface()
        
        # Mock the _monitoring_thread and _update_thread
        sensor_interface._monitoring_thread = MagicMock()
        sensor_interface._update_thread = MagicMock()
        sensor_interface._monitoring_thread.is_alive.return_value = True
        sensor_interface._update_thread.is_alive.return_value = True
        
        # Mock the _cleanup_sensors method
        sensor_interface._cleanup_sensors = MagicMock()
        
        # Call cleanup
        sensor_interface.cleanup()
        
        # Verify that the stop event was set
        assert sensor_interface._stop_event.is_set()
        
        # Verify that the threads were joined
        sensor_interface._monitoring_thread.join.assert_called_once()
        sensor_interface._update_thread.join.assert_called_once()
        
        # Verify that _cleanup_sensors was called
        sensor_interface._cleanup_sensors.assert_called_once()

    @patch("mower.hardware.sensor_interface.busio.I2C")
    def test_get_sensor_data(self, mock_i2c):
        """Test getting sensor data."""
        # Create an EnhancedSensorInterface instance
        sensor_interface = EnhancedSensorInterface()
        
        # Set some test data
        test_data = {
            'temperature': 25.0,
            'humidity': 50.0,
            'pressure': 1013.25,
            'heading': 0.0,
            'roll': 0.0,
            'pitch': 0.0,
            'left_distance': 100.0,
            'right_distance': 100.0
        }
        sensor_interface._data = test_data
        
        # Get the sensor data
        data = sensor_interface.get_sensor_data()
        
        # Verify that the correct data was returned
        assert data == test_data
        
        # Verify that the returned data is a copy
        assert data is not sensor_interface._data

    @patch("mower.hardware.sensor_interface.busio.I2C")
    def test_get_sensor_status(self, mock_i2c):
        """Test getting sensor status."""
        # Create an EnhancedSensorInterface instance
        sensor_interface = EnhancedSensorInterface()
        
        # Get the sensor status
        status = sensor_interface.get_sensor_status()
        
        # Verify that the correct status was returned
        assert 'bme280' in status
        assert 'bno085' in status
        assert 'ina3221' in status
        assert 'vl53l0x' in status
        
        # Verify that the returned status is a copy
        assert status is not sensor_interface._sensor_status

    @patch("mower.hardware.sensor_interface.busio.I2C")
    def test_is_safe_to_operate(self, mock_i2c):
        """Test checking if it's safe to operate."""
        # Create an EnhancedSensorInterface instance
        sensor_interface = EnhancedSensorInterface()
        
        # Set all critical sensors to working
        sensor_interface._sensor_status['bno085'].working = True
        sensor_interface._sensor_status['vl53l0x'].working = True
        
        # Check if it's safe to operate
        assert sensor_interface.is_safe_to_operate() is True
        
        # Set one critical sensor to not working
        sensor_interface._sensor_status['bno085'].working = False
        
        # Check if it's safe to operate
        assert sensor_interface.is_safe_to_operate() is False

    @patch("mower.hardware.sensor_interface.busio.I2C")
    def test_init_sensor_with_retry(self, mock_i2c):
        """Test initializing a sensor with retry logic."""
        # Create an EnhancedSensorInterface instance
        sensor_interface = EnhancedSensorInterface()
        
        # Create a mock initializer that succeeds on the second attempt
        mock_initializer = MagicMock(side_effect=[None, MagicMock()])
        
        # Call _init_sensor_with_retry
        result = sensor_interface._init_sensor_with_retry('test_sensor', mock_initializer)
        
        # Verify that the initializer was called twice
        assert mock_initializer.call_count == 2
        
        # Verify that the sensor was initialized
        assert sensor_interface._sensors['test_sensor'] is not None
        
        # Verify that the sensor status was updated
        assert sensor_interface._sensor_status['test_sensor'].working is True
        assert sensor_interface._sensor_status['test_sensor'].error_count == 0
        assert sensor_interface._sensor_status['test_sensor'].last_error is None
        
        # Verify that the function returned True
        assert result is True
        
        # Create a mock initializer that always fails
        mock_initializer = MagicMock(side_effect=Exception("Test error"))
        
        # Call _init_sensor_with_retry
        result = sensor_interface._init_sensor_with_retry('test_sensor', mock_initializer)
        
        # Verify that the initializer was called three times (max retries)
        assert mock_initializer.call_count == 3
        
        # Verify that the sensor status was updated
        assert sensor_interface._sensor_status['test_sensor'].working is False
        assert sensor_interface._sensor_status['test_sensor'].error_count > 0
        assert sensor_interface._sensor_status['test_sensor'].last_error is not None
        
        # Verify that the function returned False
        assert result is False

    @patch("mower.hardware.sensor_interface.busio.I2C")
    def test_handle_sensor_error(self, mock_i2c):
        """Test handling sensor errors."""
        # Create an EnhancedSensorInterface instance
        sensor_interface = EnhancedSensorInterface()
        
        # Call _handle_sensor_error
        sensor_interface._handle_sensor_error('test_sensor', Exception("Test error"))
        
        # Verify that the sensor status was updated
        assert sensor_interface._sensor_status['test_sensor'].working is False
        assert sensor_interface._sensor_status['test_sensor'].error_count == 1
        assert sensor_interface._sensor_status['test_sensor'].last_error == "Test error"

    @patch("mower.hardware.sensor_interface.get_sensor_interface")
    def test_get_sensor_interface(self, mock_get_sensor_interface):
        """Test the get_sensor_interface function."""
        # Call get_sensor_interface
        sensor_interface = get_sensor_interface()
        
        # Verify that get_sensor_interface was called
        mock_get_sensor_interface.assert_called_once()
        
        # Verify that the correct sensor interface was returned
        assert sensor_interface is mock_get_sensor_interface.return_value


class TestSensorInterfaceThreadSafety:
    """Tests for thread safety in the EnhancedSensorInterface class."""

    @patch("mower.hardware.sensor_interface.busio.I2C")
    def test_thread_safety(self, mock_i2c):
        """Test thread safety of the sensor interface."""
        # Create an EnhancedSensorInterface instance
        sensor_interface = EnhancedSensorInterface()
        
        # Define a function that updates sensor data
        def update_data():
            for i in range(100):
                with sensor_interface._locks['data']:
                    sensor_interface._data['test'] = i
                time.sleep(0.001)
        
        # Define a function that reads sensor data
        def read_data():
            for i in range(100):
                data = sensor_interface.get_sensor_data()
                # Verify that we get a consistent view of the data
                if 'test' in data:
                    assert isinstance(data['test'], int)
                time.sleep(0.001)
        
        # Create and start threads
        threads = []
        for i in range(5):
            threads.append(threading.Thread(target=update_data))
            threads.append(threading.Thread(target=read_data))
        
        for thread in threads:
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()