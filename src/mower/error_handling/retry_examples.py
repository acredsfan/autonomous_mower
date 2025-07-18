"""
Examples of using retry policy engine with various strategies.

This module demonstrates how to use the retry policy engine with different
backoff strategies for handling transient failures in external dependencies,
network operations, and hardware interactions.
"""

import asyncio
import logging
import random
import time
from typing import Any, Dict, Optional

import aiohttp
import requests

from mower.error_handling.retry_policy import (
    RetryPolicy,
    RetryPolicyEngine,
    RetryStrategy,
    get_retry_policy_engine,
    i2c_retry,
    network_retry,
    sensor_retry,
    with_retry,
)

logger = logging.getLogger(__name__)


class ExampleNetworkClient:
    """
    Example network client demonstrating retry policy usage.
    
    This class shows how to apply retry decorators to network operations
    that may fail due to connectivity issues, timeouts, or server errors.
    """
    
    def __init__(self, base_url: str = "https://api.example.com"):
        self.base_url = base_url
        self.session = requests.Session()
    
    @network_retry(max_attempts=3, base_delay=1.0)
    def get_data(self, endpoint: str) -> Dict[str, Any]:
        """
        Get data from API with network retry decorator.
        
        Args:
            endpoint: API endpoint
            
        Returns:
            Dict[str, Any]: API response data
            
        Raises:
            ConnectionError: If connection fails after retries
        """
        url = f"{self.base_url}/{endpoint}"
        logger.info(f"Fetching data from {url}")
        
        # Simulate intermittent network failures
        if random.random() < 0.6:  # 60% failure rate for demonstration
            raise ConnectionError(f"Failed to connect to {url}")
        
        # Simulate successful response
        return {
            "status": "success",
            "data": {
                "id": random.randint(1, 1000),
                "name": f"Item {random.randint(1, 100)}",
                "timestamp": time.time()
            }
        }
    
    @with_retry(
        max_attempts=4,
        strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
        base_delay=0.5,
        expected_exceptions=(ConnectionError, TimeoutError)
    )
    def post_data(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Post data to API with custom retry decorator.
        
        Args:
            endpoint: API endpoint
            data: Data to post
            
        Returns:
            Dict[str, Any]: API response data
            
        Raises:
            ConnectionError: If connection fails after retries
        """
        url = f"{self.base_url}/{endpoint}"
        logger.info(f"Posting data to {url}")
        
        # Simulate intermittent network failures with decreasing probability
        failure_chance = 0.8 - (0.2 * getattr(self, "_retry_count", 0))
        if random.random() < failure_chance:
            # Track retry count for demonstration
            self._retry_count = getattr(self, "_retry_count", 0) + 1
            raise ConnectionError(f"Failed to connect to {url}")
        
        # Reset retry count on success
        self._retry_count = 0
        
        # Simulate successful response
        return {
            "status": "success",
            "id": random.randint(1000, 9999)
        }
    
    async def async_get_data(self, endpoint: str) -> Dict[str, Any]:
        """
        Get data from API asynchronously with retry policy.
        
        Args:
            endpoint: API endpoint
            
        Returns:
            Dict[str, Any]: API response data
        """
        url = f"{self.base_url}/{endpoint}"
        logger.info(f"Async fetching data from {url}")
        
        # Get retry policy engine and use named policy
        engine = get_retry_policy_engine()
        
        # Use the execute_async method with the "network" policy
        try:
            return await engine.execute_async(
                self._async_get_impl,
                endpoint,
                policy_name="network"
            )
        except Exception as e:
            logger.error(f"Failed to fetch data after retries: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    async def _async_get_impl(self, endpoint: str) -> Dict[str, Any]:
        """Implementation of async get request."""
        url = f"{self.base_url}/{endpoint}"
        
        # Simulate network request with potential failures
        await asyncio.sleep(0.1)  # Simulate network latency
        
        if random.random() < 0.6:  # 60% failure rate
            raise ConnectionError(f"Failed to connect to {url}")
        
        return {
            "status": "success",
            "data": {
                "id": random.randint(1, 1000),
                "name": f"Item {random.randint(1, 100)}",
                "timestamp": time.time()
            }
        }


class ExampleSensorReader:
    """
    Example sensor reader demonstrating retry policy for hardware operations.
    """
    
    def __init__(self, sensor_id: str = "example_sensor"):
        self.sensor_id = sensor_id
        self.error_rate = 0.5  # 50% error rate initially
        self.consecutive_errors = 0
    
    @sensor_retry(max_attempts=3, base_delay=0.1)
    def read_sensor(self) -> Dict[str, Any]:
        """
        Read sensor data with retry policy.
        
        Returns:
            Dict[str, Any]: Sensor reading
            
        Raises:
            IOError: If sensor reading fails after retries
        """
        logger.info(f"Reading sensor {self.sensor_id}")
        
        # Simulate sensor reading with potential failures
        if random.random() < self.error_rate:
            self.consecutive_errors += 1
            # Simulate different error types
            error_type = random.choice([IOError, ValueError, TimeoutError])
            raise error_type(f"Failed to read from sensor {self.sensor_id}")
        
        # Success - decrease error rate slightly to simulate "warming up"
        self.error_rate = max(0.1, self.error_rate - 0.1)
        self.consecutive_errors = 0
        
        # Simulate successful reading
        return {
            "sensor_id": self.sensor_id,
            "timestamp": time.time(),
            "value": random.uniform(20.0, 30.0),
            "unit": "C"
        }
    
    @i2c_retry(max_attempts=5, base_delay=0.02)
    def calibrate_sensor(self) -> bool:
        """
        Calibrate sensor with I2C retry policy.
        
        Returns:
            bool: True if calibration successful
            
        Raises:
            IOError: If calibration fails after retries
        """
        logger.info(f"Calibrating sensor {self.sensor_id}")
        
        # Simulate calibration with potential I2C bus issues
        if random.random() < 0.4:  # 40% failure rate
            raise IOError(f"I2C bus error during calibration of {self.sensor_id}")
        
        logger.info(f"Sensor {self.sensor_id} calibrated successfully")
        return True


def demonstrate_retry_policy_usage():
    """
    Demonstrate retry policy usage with examples.
    
    This function shows how to use the retry policy engine with different
    strategies and configurations.
    """
    logger.info("Starting retry policy demonstration")
    
    # Configure retry policy engine with default policies
    engine = get_retry_policy_engine()
    engine.load_from_config({
        "retry_policies": {
            "default": {
                "max_attempts": 3,
                "strategy": "exponential_backoff",
                "base_delay": 1.0,
                "max_delay": 60.0,
                "jitter": True
            },
            "network": {
                "max_attempts": 5,
                "strategy": "exponential_backoff",
                "base_delay": 1.0,
                "max_delay": 30.0,
                "jitter": True
            },
            "sensor": {
                "max_attempts": 3,
                "strategy": "linear_backoff",
                "base_delay": 0.1,
                "max_delay": 1.0,
                "jitter": True
            },
            "i2c": {
                "max_attempts": 5,
                "strategy": "exponential_backoff",
                "base_delay": 0.02,
                "max_delay": 0.5,
                "jitter": True
            }
        }
    })
    
    # Example 1: Network client with retry decorators
    logger.info("\n=== Example 1: Network Client with Retry Decorators ===")
    client = ExampleNetworkClient()
    
    # Try to get data - will retry on failure
    try:
        data = client.get_data("users")
        logger.info(f"Got data: {data}")
    except Exception as e:
        logger.error(f"Failed to get data after retries: {e}")
    
    # Try to post data - will retry with exponential backoff
    try:
        response = client.post_data("items", {"name": "New Item"})
        logger.info(f"Posted data: {response}")
    except Exception as e:
        logger.error(f"Failed to post data after retries: {e}")
    
    # Example 2: Sensor reader with retry policy
    logger.info("\n=== Example 2: Sensor Reader with Retry Policy ===")
    sensor = ExampleSensorReader()
    
    # Try to read sensor multiple times
    for i in range(3):
        try:
            reading = sensor.read_sensor()
            logger.info(f"Sensor reading {i+1}: {reading}")
        except Exception as e:
            logger.error(f"Failed to read sensor after retries: {e}")
        
        time.sleep(0.5)
    
    # Try to calibrate sensor
    try:
        calibrated = sensor.calibrate_sensor()
        logger.info(f"Sensor calibration {'successful' if calibrated else 'failed'}")
    except Exception as e:
        logger.error(f"Failed to calibrate sensor after retries: {e}")
    
    # Example 3: Manual retry policy usage
    logger.info("\n=== Example 3: Manual Retry Policy Usage ===")
    
    # Create custom retry policy
    custom_policy = RetryPolicy(
        max_attempts=4,
        strategy=RetryStrategy.FIBONACCI_BACKOFF,
        base_delay=0.5,
        max_delay=5.0,
        jitter=True,
        on_retry=lambda attempt, exc, delay: logger.info(
            f"Retry callback: attempt {attempt}, delay {delay:.2f}s, error: {exc}"
        )
    )
    
    # Function to retry
    def unreliable_operation(success_rate: float = 0.3) -> str:
        """Unreliable operation that fails sometimes."""
        if random.random() > success_rate:
            raise RuntimeError("Operation failed randomly")
        return "Operation succeeded"
    
    # Execute with retry policy
    result = custom_policy.execute(unreliable_operation, success_rate=0.3)
    
    if result.success:
        logger.info(f"Operation succeeded after {result.attempts} attempts")
        logger.info(f"Total delay: {result.total_delay:.2f}s")
    else:
        logger.error(f"Operation failed after {result.attempts} attempts")
        logger.error(f"Last error: {result.exception}")
    
    # Example 4: Async retry policy usage
    logger.info("\n=== Example 4: Async Retry Policy Usage ===")
    
    async def run_async_demo():
        # Try async get data with retry
        data = await client.async_get_data("users")
        logger.info(f"Async got data: {data}")
        
        # Create custom async retry policy
        async_policy = RetryPolicy(
            max_attempts=3,
            strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
            base_delay=0.2,
            jitter=True
        )
        
        # Async function to retry
        async def unreliable_async_operation():
            await asyncio.sleep(0.1)
            if random.random() < 0.7:  # 70% failure rate
                raise ConnectionError("Async operation failed")
            return "Async operation succeeded"
        
        # Execute with async retry policy
        result = await async_policy.execute_async(unreliable_async_operation)
        
        if result.success:
            logger.info(f"Async operation succeeded after {result.attempts} attempts")
        else:
            logger.error(f"Async operation failed after {result.attempts} attempts")
    
    # Run async demo
    asyncio.run(run_async_demo())
    
    logger.info("\nRetry policy demonstration completed")


if __name__ == "__main__":
    # Configure logging for demonstration
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)8s] %(message)s (%(filename)s:%(lineno)d)'
    )
    
    demonstrate_retry_policy_usage()