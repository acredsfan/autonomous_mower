"""
Configuration schema for retry policies in main_config.json.

This module provides the JSON schema for retry policies configuration
that can be added to the main_config.json file.
"""

import json
from typing import Dict, Any

# JSON schema for retry policies configuration
RETRY_POLICY_SCHEMA = {
    "type": "object",
    "properties": {
        "retry_policies": {
            "type": "object",
            "description": "Configuration for retry policies used throughout the application",
            "properties": {
                "default": {
                    "type": "object",
                    "description": "Default retry policy used when no specific policy is specified",
                    "properties": {
                        "max_attempts": {
                            "type": "integer",
                            "description": "Maximum number of attempts (including first attempt)",
                            "minimum": 1,
                            "default": 3
                        },
                        "strategy": {
                            "type": "string",
                            "description": "Backoff strategy to use",
                            "enum": [
                                "fixed_delay",
                                "linear_backoff",
                                "exponential_backoff",
                                "fibonacci_backoff",
                                "random_backoff"
                            ],
                            "default": "exponential_backoff"
                        },
                        "base_delay": {
                            "type": "number",
                            "description": "Base delay in seconds",
                            "minimum": 0.0,
                            "default": 1.0
                        },
                        "max_delay": {
                            "type": "number",
                            "description": "Maximum delay in seconds",
                            "minimum": 0.0,
                            "default": 60.0
                        },
                        "jitter": {
                            "type": "boolean",
                            "description": "Whether to add random jitter to delay",
                            "default": True
                        },
                        "jitter_factor": {
                            "type": "number",
                            "description": "Factor for jitter (0.0-1.0)",
                            "minimum": 0.0,
                            "maximum": 1.0,
                            "default": 0.1
                        }
                    },
                    "required": ["max_attempts", "strategy", "base_delay"]
                },
                "network": {
                    "type": "object",
                    "description": "Retry policy for network operations",
                    "properties": {
                        "max_attempts": {"type": "integer", "minimum": 1, "default": 5},
                        "strategy": {
                            "type": "string",
                            "enum": [
                                "fixed_delay",
                                "linear_backoff",
                                "exponential_backoff",
                                "fibonacci_backoff",
                                "random_backoff"
                            ],
                            "default": "exponential_backoff"
                        },
                        "base_delay": {"type": "number", "minimum": 0.0, "default": 1.0},
                        "max_delay": {"type": "number", "minimum": 0.0, "default": 30.0},
                        "jitter": {"type": "boolean", "default": True},
                        "jitter_factor": {"type": "number", "minimum": 0.0, "maximum": 1.0, "default": 0.2}
                    }
                },
                "sensor": {
                    "type": "object",
                    "description": "Retry policy for sensor operations",
                    "properties": {
                        "max_attempts": {"type": "integer", "minimum": 1, "default": 3},
                        "strategy": {
                            "type": "string",
                            "enum": [
                                "fixed_delay",
                                "linear_backoff",
                                "exponential_backoff",
                                "fibonacci_backoff",
                                "random_backoff"
                            ],
                            "default": "linear_backoff"
                        },
                        "base_delay": {"type": "number", "minimum": 0.0, "default": 0.1},
                        "max_delay": {"type": "number", "minimum": 0.0, "default": 1.0},
                        "jitter": {"type": "boolean", "default": True},
                        "jitter_factor": {"type": "number", "minimum": 0.0, "maximum": 1.0, "default": 0.1}
                    }
                },
                "i2c": {
                    "type": "object",
                    "description": "Retry policy for I2C operations",
                    "properties": {
                        "max_attempts": {"type": "integer", "minimum": 1, "default": 5},
                        "strategy": {
                            "type": "string",
                            "enum": [
                                "fixed_delay",
                                "linear_backoff",
                                "exponential_backoff",
                                "fibonacci_backoff",
                                "random_backoff"
                            ],
                            "default": "exponential_backoff"
                        },
                        "base_delay": {"type": "number", "minimum": 0.0, "default": 0.02},
                        "max_delay": {"type": "number", "minimum": 0.0, "default": 0.5},
                        "jitter": {"type": "boolean", "default": True},
                        "jitter_factor": {"type": "number", "minimum": 0.0, "maximum": 1.0, "default": 0.05}
                    }
                },
                "gps": {
                    "type": "object",
                    "description": "Retry policy for GPS operations",
                    "properties": {
                        "max_attempts": {"type": "integer", "minimum": 1, "default": 3},
                        "strategy": {
                            "type": "string",
                            "enum": [
                                "fixed_delay",
                                "linear_backoff",
                                "exponential_backoff",
                                "fibonacci_backoff",
                                "random_backoff"
                            ],
                            "default": "fixed_delay"
                        },
                        "base_delay": {"type": "number", "minimum": 0.0, "default": 5.0},
                        "max_delay": {"type": "number", "minimum": 0.0, "default": 5.0},
                        "jitter": {"type": "boolean", "default": False}
                    }
                }
            },
            "required": ["default"]
        }
    }
}


# Default configuration for retry policies
DEFAULT_RETRY_CONFIG = {
    "retry_policies": {
        "default": {
            "max_attempts": 3,
            "strategy": "exponential_backoff",
            "base_delay": 1.0,
            "max_delay": 60.0,
            "jitter": True,
            "jitter_factor": 0.1
        },
        "network": {
            "max_attempts": 5,
            "strategy": "exponential_backoff",
            "base_delay": 1.0,
            "max_delay": 30.0,
            "jitter": True,
            "jitter_factor": 0.2
        },
        "sensor": {
            "max_attempts": 3,
            "strategy": "linear_backoff",
            "base_delay": 0.1,
            "max_delay": 1.0,
            "jitter": True,
            "jitter_factor": 0.1
        },
        "i2c": {
            "max_attempts": 5,
            "strategy": "exponential_backoff",
            "base_delay": 0.02,
            "max_delay": 0.5,
            "jitter": True,
            "jitter_factor": 0.05
        },
        "gps": {
            "max_attempts": 3,
            "strategy": "fixed_delay",
            "base_delay": 5.0,
            "max_delay": 5.0,
            "jitter": False
        }
    }
}


def get_retry_config_schema() -> Dict[str, Any]:
    """
    Get the JSON schema for retry policies configuration.
    
    Returns:
        Dict[str, Any]: JSON schema
    """
    return RETRY_POLICY_SCHEMA


def get_default_retry_config() -> Dict[str, Any]:
    """
    Get the default retry policies configuration.
    
    Returns:
        Dict[str, Any]: Default configuration
    """
    return DEFAULT_RETRY_CONFIG


def generate_retry_config_json() -> str:
    """
    Generate JSON string for default retry configuration.
    
    Returns:
        str: JSON string
    """
    return json.dumps(DEFAULT_RETRY_CONFIG, indent=2)


if __name__ == "__main__":
    # Print default retry configuration as JSON
    print(generate_retry_config_json())