# src/mower/hardware/sensor_types.py
from dataclasses import dataclass, field
from datetime import datetime  # Using datetime for timestamp as it's common
from typing import Any, Optional


@dataclass
class SensorReading:
    value: Any
    timestamp: datetime = field(default_factory=datetime.now)
    status: Optional[str] = None
    # Adding optional error and sensor_name fields based on typical usage patterns
    # and how it's used in collector.py's _save_image_metadata
    error: Optional[str] = None
    sensor_name: Optional[str] = None
