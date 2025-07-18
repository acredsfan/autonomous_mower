"""
Sensor types and data structures for the autonomous mower.

This module defines the core data structures used by the sensor system,
including sensor readings and related types. It provides compatibility
with both the legacy sensor interface and the new async sensor manager.
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional, Union
from datetime import datetime


@dataclass
class SensorReading:
    """
    Represents a sensor reading with metadata.
    
    This class provides a wrapper around raw sensor data to include
    timestamps and status information. It's designed to be compatible
    with both legacy and async sensor interfaces.
    """
    
    value: Any
    timestamp: Optional[datetime] = None
    status: str = "ok"
    source: str = "unknown"
    
    def __post_init__(self):
        """Set default timestamp if not provided."""
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any], source: str = "async_sensor") -> "SensorReading":
        """
        Create a SensorReading from a dictionary.
        
        Args:
            data: Dictionary containing sensor data
            source: Source identifier for the reading
            
        Returns:
            SensorReading instance
        """
        return cls(
            value=data,
            timestamp=datetime.now(),
            status="ok",
            source=source
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert SensorReading to dictionary format.
        
        Returns:
            Dictionary representation of the sensor reading
        """
        return {
            "value": self.value,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "status": self.status,
            "source": self.source
        }


# Type aliases for compatibility
SensorData = Dict[str, Union[SensorReading, Any]]
RawSensorData = Dict[str, Any]
