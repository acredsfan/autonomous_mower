"""
Utility module for Google Coral TPU integration in the autonomous mower project.

This module provides functions for detecting and utilizing the Google Coral Edge TPU
accelerator for machine learning inference. It includes fallbacks for systems
without the Coral hardware or when the pycoral library is not installed.

Key functions:
- is_coral_detected(): Checks if a Coral Edge TPU device is connected and accessible
- get_interpreter_creator(): Returns the appropriate interpreter creation function

This implementation allows the system to use the Coral accelerator when available,
while gracefully falling back to CPU inference when it's not.
"""

import logging
import os

# Configure logging
from mower.utilities.logger_config import LoggerConfigInfo as LoggerConfig
logging = LoggerConfig.get_logger(__name__)

# Try to import Coral libraries, with graceful fallback if not available
try:
    from pycoral.utils import edgetpu
    from pycoral.adapters import common
    coral_available = True
    logging.info("Coral libraries successfully imported")
except ImportError:
    logging.warning("Coral libraries not available. Falling back to CPU inference only.")
    coral_available = False
    
    # Define dummy classes for compatibility when pycoral isn't installed
    class edgetpu:
        @staticmethod
        def list_edge_tpus():
            return []
            
        @staticmethod
        def make_interpreter(*args, **kwargs):
            raise ImportError("pycoral library not installed")
    
    class common:
        @staticmethod
        def input_size(*args):
            return (0, 0)


def is_coral_detected() -> bool:
    """
    Checks if a Coral Edge TPU device is detected and available.
    
    This function attempts to list available Edge TPU devices
    and determines if at least one is present and accessible.
    
    Returns:
        bool: True if at least one Edge TPU is detected, False otherwise
        
    Note:
        Returns False if pycoral library is not installed.
    """
    if not coral_available:
        return False
        
    try:
        devices = edgetpu.list_edge_tpus()
        logging.info(f"Detected Edge TPUs: {devices}")
        return len(devices) > 0
    except Exception as e:
        # Catch potential exceptions if runtime/drivers have issues
        logging.error(f"Error checking for Edge TPU devices: {e}")
        return False


def get_interpreter_creator(use_coral: bool = False):
    """
    Returns an appropriate function for creating TensorFlow Lite interpreters.
    
    Args:
        use_coral: Whether to attempt using Coral Edge TPU if available
        
    Returns:
        function: A function that creates an interpreter when called with a model path
        
    The returned function has the signature:
        fn(model_path: str) -> tflite.Interpreter
    """
    if use_coral and is_coral_detected() and coral_available:
        logging.info("Using Coral Edge TPU for model inference")
        return edgetpu.make_interpreter
    else:
        # Import tflite_runtime only when needed for CPU inference
        import tflite_runtime.interpreter as tflite
        logging.info("Using CPU for model inference")
        return tflite.Interpreter 