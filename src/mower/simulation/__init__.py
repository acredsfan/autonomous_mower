"""
Simulation package for the autonomous mower.

This package provides simulation capabilities for testing the autonomous mower
without requiring physical hardware. It includes simulated versions of all
hardware components and a virtual world environment for testing navigation,
obstacle avoidance, and other features.
"""

import os
import logging
from typing import Dict, Any, Optional, List, Tuple, Union, Type

# Check if simulation mode is enabled via environment variable
SIMULATION_ENABLED = os.environ.get('USE_SIMULATION', 'False').lower() in ('true', '1', 'yes')

# Get the simulation mode from configuration if available
try:
    from mower.config_management import get_config
    SIMULATION_ENABLED = get_config('use_simulation', SIMULATION_ENABLED)
except ImportError:
    # If config_management is not available, use the environment variable
    pass

# Configure logging
logger = logging.getLogger(__name__)

def enable_simulation():
    """Enable simulation mode globally."""
    global SIMULATION_ENABLED
    SIMULATION_ENABLED = True
    logger.info("Simulation mode enabled")
    
    # Update configuration if available
    try:
        from mower.config_management import set_config
        set_config('use_simulation', True)
    except ImportError:
        pass

def disable_simulation():
    """Disable simulation mode globally."""
    global SIMULATION_ENABLED
    SIMULATION_ENABLED = False
    logger.info("Simulation mode disabled")
    
    # Update configuration if available
    try:
        from mower.config_management import set_config
        set_config('use_simulation', False)
    except ImportError:
        pass

def is_simulation_enabled():
    """Check if simulation mode is enabled."""
    return SIMULATION_ENABLED