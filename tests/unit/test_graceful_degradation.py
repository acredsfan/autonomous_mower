"""
Unit tests for GracefulDegradationController.

Tests the graceful degradation functionality including:
- Sensor failure handling
- Fallback strategy activation
- Sensor fusion logic
- Recovery mechanisms
"""

import asyncio
import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from mower.utilities.graceful_degradation import (
    GracefulDegradationController,
    SensorFusion,
    FallbackStrategy,
    DegradationState,
    DegradationLevel,
    SensorType
)


class TestSensorFusion:
    """Test cases for SensorFusion class"""
    
    @pytest.fixture
    def sensor_fusion(self):
        """Create a SensorFusion instance for testing"""
        return SensorFusion()
    
    @pytest.mark.asyncio
    async def test_fuse_gps_imu_with_good_gps(self, sensor_fusion):
        """Test GPS/IMU fusion when GPS is available"""
        gps_data = {
            "latitude": 40.7128,
            "longitude": -74.0060,
            "altitude": 10.0,
            "course": 45.0,
            "fix_quality": 4
        }
        imu_data = {
            "heading": 50.0,
            "roll": 2.0,
            "pitch": 1.0
        }
        
        result = await sensor_fusion.fuse_gps_imu(gps_data, imu_data)
        
        assert result["source"] == "gps"
        assert result["confidence"] == 1.0
        assert result["position"]["latitude"] == 40.7128
        assert result["position"]["longitude"] == -74.0060
        assert result["heading"] == 45.0
    
    @pytest.mark.asyncio
    async def test_fuse_gps_imu_with_no_gps(self, sensor_fusion):
        """Test GPS/IMU fusion when GPS is unavailable"""
        gps_data = None
        imu_data = {
            "heading": 50.0,
            "roll": 2.0,
            "pitch": 1.0
        }
        
        result = await sensor_fusion.fuse_gps_imu(gps_data, imu_data)
        
        assert result["source"] == "imu_dead_reckoning"
        assert result["confidence"] == 0.6
        assert result["heading"] == 50.0
    
    @pytest.mark.asyncio
    async def test_fuse_camera_tof_both_available(self, sensor_fusion):
        """Test camera/ToF fusion when both sensors are available"""
        camera_data = {
            "obstacles": [
                {"type": "tree", "distance": 2.5, "direction": "front"}
            ],
            "min_distance": 2.5
        }
        tof_data = {
            "distances": {
                "front": 2.4,
                "left": 5.0,
                "right": 3.0
            }
        }
        
        result = await sensor_fusion.fuse_camera_tof(camera_data, tof_data)
        
        assert result["source"] == "camera_tof_fusion"
        assert result["confidence"] == 0.9
        assert len(result["obstacles"]) >= 1
        assert result["safe_distance"] == 2.4  # Min of camera and ToF
    
    @pytest.mark.asyncio
    async def test_fuse_camera_tof_camera_only(self, sensor_fusion):
        """Test camera/ToF fusion with camera only"""
        camera_data = {
            "obstacles": [
                {"type": "rock", "distance": 1.5, "direction": "front"}
            ],
            "min_distance": 1.5
        }
        tof_data = None
        
        result = await sensor_fusion.fuse_camera_tof(camera_data, tof_data)
        
        assert result["source"] == "camera_only"
        assert result["confidence"] == 0.7
        assert len(result["obstacles"]) == 1
        assert result["safe_distance"] == 1.5
    
    @pytest.mark.asyncio
    async def test_fuse_camera_tof_tof_only(self, sensor_fusion):
        """Test camera/ToF fusion with ToF only"""
        camera_data = None
        tof_data = {
            "distances": {
                "front": 0.8,
                "left": 2.0,
                "right": 0.5
            }
        }
        
        result = await sensor_fusion.fuse_camera_tof(camera_data, tof_data)
        
        assert result["source"] == "tof_only"
        assert result["confidence"] == 0.6
        assert len(result["obstacles"]) == 2  # front and right < 1.0m
        assert result["safe_distance"] == 0.5


class TestFallbackStrategy:
    """Test cases for FallbackStrategy class"""
    
    def test_strategy_applicability(self):
        """Test strategy applicability logic"""
        strategy = FallbackStrategy(
            name="test_strategy",
            sensor_types=[SensorType.GPS, SensorType.IMU],
            fallback_sensors=[SensorType.CAMERA],
            degradation_level=DegradationLevel.MODERATE,
            enabled_functions=["basic_nav"],
            disabled_functions=["precision_nav"]
        )
        
        # Should apply when GPS fails
        assert strategy.is_applicable({SensorType.GPS})
        
        # Should apply when IMU fails
        assert strategy.is_applicable({SensorType.IMU})
        
        # Should apply when both fail
        assert strategy.is_applicable({SensorType.GPS, SensorType.IMU})
        
        # Should not apply when only camera fails
        assert not strategy.is_applicable({SensorType.CAMERA})


class TestDegradationState:
    """Test cases for DegradationState class"""
    
    def test_duration_calculation(self):
        """Test duration calculation"""
        state = DegradationState()
        
        # No start time - should return None
        assert state.get_duration() is None
        
        # Set start time
        state.start_time = datetime.now() - timedelta(minutes=5)
        duration = state.get_duration()
        
        assert duration is not None
        assert duration.total_seconds() >= 300  # At least 5 minutes


class TestGracefulDegradationController:
    """Test cases for GracefulDegradationController class"""
    
    @pytest_asyncio.fixture
    async def controller(self):
        """Create a controller instance for testing"""
        controller = GracefulDegradationController()
        yield controller
        await controller.stop_monitoring()
    
    @pytest.mark.asyncio
    async def test_initialization(self, controller):
        """Test controller initialization"""
        assert controller._state.level == DegradationLevel.NORMAL
        assert len(controller._strategies) > 0  # Should have default strategies
        assert not controller._running
    
    @pytest.mark.asyncio
    async def test_strategy_registration(self, controller):
        """Test custom strategy registration"""
        strategy = FallbackStrategy(
            name="custom_strategy",
            sensor_types=[SensorType.POWER],
            fallback_sensors=[],
            degradation_level=DegradationLevel.MINOR,
            enabled_functions=["low_power_mode"],
            disabled_functions=["high_power_functions"]
        )
        
        controller.register_strategy(strategy)
        
        assert "custom_strategy" in controller._strategies
        assert controller._strategies["custom_strategy"] == strategy
    
    @pytest.mark.asyncio
    async def test_monitoring_lifecycle(self, controller):
        """Test monitoring start/stop lifecycle"""
        assert not controller._running
        
        await controller.start_monitoring()
        assert controller._running
        assert controller._monitoring_task is not None
        
        await controller.stop_monitoring()
        assert not controller._running
    
    @pytest.mark.asyncio
    async def test_sensor_failure_handling(self, controller):
        """Test sensor failure handling"""
        # Mock callback to track events
        events = []
        
        def mock_callback(data):
            events.append(data)
        
        controller.register_callback("strategy_activated", mock_callback)
        
        # Simulate GPS failure
        await controller.handle_sensor_failure(SensorType.GPS, {"error": "signal_lost"})
        
        # Should activate GPS fallback strategy
        assert SensorType.GPS in controller._state.failed_sensors
        assert controller._state.level != DegradationLevel.NORMAL
        assert len(controller._state.active_strategies) > 0
        
        # Should have notified callback
        assert len(events) > 0
        assert events[0]["strategy"] in controller._strategies
    
    @pytest.mark.asyncio
    async def test_sensor_recovery_handling(self, controller):
        """Test sensor recovery handling"""
        # First cause a failure
        await controller.handle_sensor_failure(SensorType.GPS, {"error": "signal_lost"})
        assert SensorType.GPS in controller._state.failed_sensors
        
        # Then recover
        await controller.handle_sensor_recovery(SensorType.GPS)
        assert SensorType.GPS not in controller._state.failed_sensors
    
    @pytest.mark.asyncio
    async def test_multiple_sensor_failures(self, controller):
        """Test handling of multiple sensor failures"""
        # Fail GPS first
        await controller.handle_sensor_failure(SensorType.GPS, {"error": "signal_lost"})
        initial_level = controller._state.level
        
        # Fail IMU as well
        await controller.handle_sensor_failure(SensorType.IMU, {"error": "calibration_failed"})
        
        # Should escalate degradation level
        assert len(controller._state.failed_sensors) == 2
        assert SensorType.GPS in controller._state.failed_sensors
        assert SensorType.IMU in controller._state.failed_sensors
        
        # Should activate more severe strategy
        final_level = controller._state.level
        # Critical level should be more severe than initial
        if initial_level != DegradationLevel.CRITICAL:
            assert final_level.value != initial_level.value
    
    @pytest.mark.asyncio
    async def test_function_enablement_logic(self, controller):
        """Test function enablement/disablement logic"""
        # Normal operation - all functions enabled
        assert controller.is_function_enabled("any_function")
        
        # Simulate failure to activate strategy
        await controller.handle_sensor_failure(SensorType.GPS, {"error": "signal_lost"})
        
        # Check that functions are properly enabled/disabled
        enabled_functions = controller.get_enabled_functions()
        disabled_functions = controller.get_disabled_functions()
        
        assert len(enabled_functions) > 0
        assert len(disabled_functions) > 0
        
        # Test specific function checks
        for func in enabled_functions:
            assert controller.is_function_enabled(func)
        
        for func in disabled_functions:
            assert not controller.is_function_enabled(func)
    
    @pytest.mark.asyncio
    async def test_return_to_normal(self, controller):
        """Test return to normal operation"""
        # Mock callback to track events
        events = []
        
        def mock_callback(data):
            events.append(("normal_restored", data))
        
        controller.register_callback("normal_operation_restored", mock_callback)
        
        # Cause failure
        await controller.handle_sensor_failure(SensorType.GPS, {"error": "signal_lost"})
        assert controller._state.level != DegradationLevel.NORMAL
        
        # Recover
        await controller.handle_sensor_recovery(SensorType.GPS)
        
        # Should return to normal
        assert controller._state.level == DegradationLevel.NORMAL
        assert len(controller._state.active_strategies) == 0
        assert len(controller._state.failed_sensors) == 0
        
        # Should have notified callback
        normal_events = [e for e in events if e[0] == "normal_restored"]
        assert len(normal_events) > 0
    
    @pytest.mark.asyncio
    async def test_fused_data_methods(self, controller):
        """Test fused data retrieval methods"""
        gps_data = {"latitude": 40.0, "longitude": -74.0, "fix_quality": 3}
        imu_data = {"heading": 45.0}
        
        nav_data = await controller.get_fused_navigation_data(gps_data, imu_data)
        assert "position" in nav_data
        assert "confidence" in nav_data
        assert "source" in nav_data
        
        camera_data = {"obstacles": [], "min_distance": 5.0}
        tof_data = {"distances": {"front": 4.0}}
        
        obstacle_data = await controller.get_fused_obstacle_data(camera_data, tof_data)
        assert "obstacles" in obstacle_data
        assert "confidence" in obstacle_data
        assert "source" in obstacle_data
    
    @pytest.mark.asyncio
    async def test_status_reporting(self, controller):
        """Test comprehensive status reporting"""
        # Normal status
        status = controller.get_status()
        assert status["degradation_level"] == DegradationLevel.NORMAL.value
        assert status["confidence_score"] == 1.0
        assert len(status["failed_sensors"]) == 0
        
        # Degraded status
        await controller.handle_sensor_failure(SensorType.GPS, {"error": "test"})
        
        status = controller.get_status()
        assert status["degradation_level"] != DegradationLevel.NORMAL.value
        assert status["confidence_score"] < 1.0
        assert len(status["failed_sensors"]) > 0
        assert "gps" in status["failed_sensors"]
    
    @pytest.mark.asyncio
    async def test_callback_error_handling(self, controller):
        """Test that callback errors don't break the controller"""
        def failing_callback(data):
            raise RuntimeError("Callback failed")
        
        controller.register_callback("strategy_activated", failing_callback)
        
        # Should not raise exception despite failing callback
        await controller.handle_sensor_failure(SensorType.GPS, {"error": "test"})
        
        # Controller should still work
        assert SensorType.GPS in controller._state.failed_sensors


if __name__ == "__main__":
    pytest.main([__file__])