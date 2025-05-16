#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fleet management module for the autonomous mower.

This module provides functionality to manage multiple mowers from a single
interface, track their status, and coordinate their operations. It helps users
who have multiple mowers to manage them efficiently.

Key features:
- Register and manage multiple mowers
- Monitor mower status and location
- Coordinate mowing schedules and zones
- Distribute workload among mowers
- Centralized maintenance tracking
- Fleet-wide updates and configuration
- Collision avoidance between mowers

Example usage:
    # Initialize the fleet manager
    fleet_manager = FleetManager()

# Register mowers
fleet_manager.register_mower("mower1", "192.168.1.101", "Mower 1")
fleet_manager.register_mower("mower2", "192.168.1.102", "Mower 2")

# Get status of all mowers
status = fleet_manager.get_fleet_status()

# Assign mowing zones
fleet_manager.assign_zone("mower1", "front_yard")
fleet_manager.assign_zone("mower2", "back_yard")

# Start mowing operation for all mowers
fleet_manager.start_fleet_operation()
"""

import json
import os
import uuid
from datetime import datetime
from enum import Enum, auto
from typing import Dict, List, Optional, Any
import threading

from mower.utilities.logger_config import LoggerConfigInfo as LoggerConfig

# Configure logging
logger = LoggerConfig.get_logger(__name__)


class MowerStatus(Enum):
    """Status of a mower in the fleet."""

    OFFLINE = auto()  # Mower is not connected
    IDLE = auto()  # Mower is connected but not mowing
    MOWING = auto()  # Mower is actively mowing
    CHARGING = auto()  # Mower is charging
    RETURNING = auto()  # Mower is returning to charging station
    ERROR = auto()  # Mower has an error
    MAINTENANCE = auto()  # Mower is in maintenance mode


class MowerInfo:
    """Information about a mower in the fleet."""

    def __init__(
        self,
        mower_id: str,
        address: str,
        name: str,
        api_key: Optional[str] = None,
    ):
        """
        Initialize mower information.

        Args:
            mower_id: Unique identifier for the mower.
            address: IP address or hostname of the mower.
            name: Human-readable name for the mower.
            api_key: API key for authenticating with the mower.
        """
        self.mower_id = mower_id
        self.address = address
        self.name = name
        self.api_key = api_key

        # Status information
        self.status = MowerStatus.OFFLINE
        self.battery_level = 0.0
        self.position = {"latitude": 0.0, "longitude": 0.0}
        self.last_seen = None
        self.current_zone = None
        self.error_message = None

        # Operation information
        self.total_runtime = 0.0
        self.total_distance = 0.0
        self.total_area = 0.0
        self.current_operation_start = None

        # Maintenance information
        self.next_maintenance = None
        self.maintenance_items = []

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "mower_id": self.mower_id,
            "address": self.address,
            "name": self.name,
            "api_key": self.api_key,
            "status": self.status.name if self.status else None,
            "battery_level": self.battery_level,
            "position": self.position,
            "last_seen": (
                self.last_seen.isoformat() if self.last_seen else None
            ),
            "current_zone": self.current_zone,
            "error_message": self.error_message,
            "total_runtime": self.total_runtime,
            "total_distance": self.total_distance,
            "total_area": self.total_area,
            "current_operation_start": (
                self.current_operation_start.isoformat()
                if self.current_operation_start
                else None
            ),
            "next_maintenance": (
                self.next_maintenance.isoformat()
                if self.next_maintenance
                else None
            ),
            "maintenance_items": self.maintenance_items,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MowerInfo":
        """Create from dictionary after deserialization."""
        mower = cls(
            mower_id=data["mower_id"],
            address=data["address"],
            name=data["name"],
            api_key=data.get("api_key"),
        )

        # Restore status information
        if data.get("status"):
            mower.status = MowerStatus[data["status"]]
        mower.battery_level = data.get("battery_level", 0.0)
        mower.position = data.get(
            "position", {"latitude": 0.0, "longitude": 0.0}
        )
        if data.get("last_seen"):
            mower.last_seen = datetime.fromisoformat(data["last_seen"])
        mower.current_zone = data.get("current_zone")
        mower.error_message = data.get("error_message")

        # Restore operation information
        mower.total_runtime = data.get("total_runtime", 0.0)
        mower.total_distance = data.get("total_distance", 0.0)
        mower.total_area = data.get("total_area", 0.0)
        if data.get("current_operation_start"):
            mower.current_operation_start = datetime.fromisoformat(
                data["current_operation_start"]
            )

        # Restore maintenance information
        if data.get("next_maintenance"):
            mower.next_maintenance = datetime.fromisoformat(
                data["next_maintenance"]
            )
        mower.maintenance_items = data.get("maintenance_items", [])

        return mower


class Zone:
    """Mowing zone information."""

    def __init__(
        self,
        zone_id: str,
        name: str,
        boundaries: List[Dict[str, float]],
        area: float,
        priority: int = 1,
    ):
        """
        Initialize zone information.

        Args:
            zone_id: Unique identifier for the zone.
            name: Human-readable name for the zone.
            boundaries: List of GPS coordinates defining the zone boundary.
            area: Area of the zone in square meters.
            priority: Priority level (1-5, where 1 is highest).
        """
        self.zone_id = zone_id
        self.name = name
        self.boundaries = boundaries
        self.area = area
        self.priority = priority

        # Status information
        self.last_mowed = None
        self.assigned_mower = None
        self.mowing_frequency_days = 7  # Default to weekly
        self.mowing_schedule = []  # List of scheduled mowing times

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "zone_id": self.zone_id,
            "name": self.name,
            "boundaries": self.boundaries,
            "area": self.area,
            "priority": self.priority,
            "last_mowed": (
                self.last_mowed.isoformat() if self.last_mowed else None
            ),
            "assigned_mower": self.assigned_mower,
            "mowing_frequency_days": self.mowing_frequency_days,
            "mowing_schedule": self.mowing_schedule,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Zone":
        """Create from dictionary after deserialization."""
        zone = cls(
            zone_id=data["zone_id"],
            name=data["name"],
            boundaries=data["boundaries"],
            area=data["area"],
            priority=data.get("priority", 1),
        )

        # Restore status information
        if data.get("last_mowed"):
            zone.last_mowed = datetime.fromisoformat(data["last_mowed"])
        zone.assigned_mower = data.get("assigned_mower")
        zone.mowing_frequency_days = data.get("mowing_frequency_days", 7)
        zone.mowing_schedule = data.get("mowing_schedule", [])

        return zone


class FleetManager:
    """
    Fleet manager for autonomous mowers.

    This class provides methods to manage multiple mowers, track their status,
    and coordinate their operations.
    """

    def __init__(self, data_file: Optional[str] = None):
        """
        Initialize the fleet manager.

        Args:
            data_file: Path to the data file for storing fleet data.
                If None, a default path will be used.
        """
        self.data_file = data_file or os.path.expanduser(
            "~/.mower/fleet.json"
        )
        self.mowers: Dict[str, MowerInfo] = {}
        self.zones: Dict[str, Zone] = {}
        self.last_save_time = 0
        self.polling_interval = 60  # seconds
        self.polling_thread = None
        self.stop_polling = threading.Event()

        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(self.data_file), exist_ok=True)

        # Load existing data if available
        self.load()

    def register_mower(
        self,
        mower_id: str,
        address: str,
        name: str,
        api_key: Optional[str] = None,
    ) -> bool:
        """
        Register a mower with the fleet.

        Args:
            mower_id: Unique identifier for the mower.
            address: IP address or hostname of the mower.
            name: Human-readable name for the mower.
            api_key: API key for authenticating with the mower.

        Returns:
            bool: True if the mower was registered, False if it already exists.
        """
        if mower_id in self.mowers:
            logger.warning(f"Mower '{mower_id}' already registered")
            return False

        self.mowers[mower_id] = MowerInfo(
            mower_id=mower_id,
            address=address,
            name=name,
            api_key=api_key,
        )

        logger.info(f"Registered mower '{mower_id}' at {address}")
        self.save()
        return True

    def remove_mower(self, mower_id: str) -> bool:
        """
        Remove a mower from the fleet.

        Args:
            mower_id: Unique identifier for the mower.

        Returns:
            bool: True if the mower was removed, False if it doesn't exist.
        """
        if mower_id not in self.mowers:
            logger.warning(f"Mower '{mower_id}' not found")
            return False

        # Remove mower from any assigned zones
        for zone in self.zones.values():
            if zone.assigned_mower == mower_id:
                zone.assigned_mower = None

        del self.mowers[mower_id]
        logger.info(f"Removed mower '{mower_id}'")
        self.save()
        return True

    def add_zone(
        self,
        name: str,
        boundaries: List[Dict[str, float]],
        area: float,
        priority: int = 1,
    ) -> str:
        """
        Add a mowing zone.

        Args:
            name: Human-readable name for the zone.
            boundaries: List of GPS coordinates defining the zone boundary.
            area: Area of the zone in square meters.
            priority: Priority level (1-5, where 1 is highest).

        Returns:
            str: Unique identifier for the zone.
        """
        zone_id = str(uuid.uuid4())
        self.zones[zone_id] = Zone(
            zone_id=zone_id,
            name=name,
            boundaries=boundaries,
            area=area,
            priority=priority,
        )

        logger.info(f"Added zone '{name}' with ID {zone_id}")
        self.save()
        return zone_id

    def remove_zone(self, zone_id: str) -> bool:
        """
        Remove a mowing zone.

        Args:
            zone_id: Unique identifier for the zone.

        Returns:
            bool: True if the zone was removed, False if it doesn't exist.
        """
        if zone_id not in self.zones:
            logger.warning(f"Zone '{zone_id}' not found")
            return False

        del self.zones[zone_id]
        logger.info(f"Removed zone '{zone_id}'")
        self.save()
        return True

    def assign_zone(self, mower_id: str, zone_id: str) -> bool:
        """
        Assign a mower to a zone.

        Args:
            mower_id: Unique identifier for the mower.
            zone_id: Unique identifier for the zone.

        Returns:
            bool: True if the assignment was successful, False otherwise.
        """
        if mower_id not in self.mowers:
            logger.warning(f"Mower '{mower_id}' not found")
            return False

        if zone_id not in self.zones:
            logger.warning(f"Zone '{zone_id}' not found")
            return False

        # Check if the zone is already assigned to another mower
        for z_id, zone in self.zones.items():
            if zone.assigned_mower == mower_id and z_id != zone_id:
                # Unassign the mower from the other zone
                zone.assigned_mower = None

        self.zones[zone_id].assigned_mower = mower_id
        logger.info(f"Assigned mower '{mower_id}' to zone '{zone_id}'")
        self.save()
        return True

    def unassign_zone(self, zone_id: str) -> bool:
        """
        Unassign a mower from a zone.

        Args:
            zone_id: Unique identifier for the zone.

        Returns:
            bool: True if the unassignment was successful, False otherwise.
        """
        if zone_id not in self.zones:
            logger.warning(f"Zone '{zone_id}' not found")
            return False

        self.zones[zone_id].assigned_mower = None
        logger.info(f"Unassigned mower from zone '{zone_id}'")
        self.save()
        return True

    def get_mower_status(self, mower_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the status of a mower.

        Args:
            mower_id: Unique identifier for the mower.

        Returns:
            Optional[Dict[str, Any]]: Status information, or None if the mower doesn't exist.
        """
        if mower_id not in self.mowers:
            logger.warning(
                f"Mower '{mower_id}' not found"
            )
            return None

        mower = self.mowers[mower_id]

        # Try to update the status from the mower
        self._update_mower_status(mower)

        return {
            "mower_id": mower.mower_id,
            "name": mower.name,
            "status": mower.status.name,
            "battery_level": mower.battery_level,
            "position": mower.position,
            "last_seen": (
                mower.last_seen.isoformat() if mower.last_seen else None
            ),
            "current_zone": mower.current_zone,
            "error_message": mower.error_message,
            "total_runtime": mower.total_runtime,
            "total_distance": mower.total_distance,
            "total_area": mower.total_area,
            "current_operation_start": (
                mower.current_operation_start.isoformat()
                if mower.current_operation_start
                else None
            ),
            "next_maintenance": (
                mower.next_maintenance.isoformat()
                if mower.next_maintenance
                else None
            ),
            "maintenance_items": mower.maintenance_items,
        }

    def get_fleet_status(self) -> Dict[str, Dict[str, Any]]:
        """
        Get the status of all mowers in the fleet.

        Returns:
            Dict[str, Dict[str, Any]]: Status information for all mowers.
        """
        status = {}
        for mower_id in self.mowers:
            status[mower_id] = self.get_mower_status(mower_id)
        return status

    def get_zone_info(self, zone_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a zone.

        Args:
            zone_id: Unique identifier for the zone.

        Returns:
            Optional[Dict[str, Any]]: Zone information, or None if the zone doesn't exist.
        """
        if zone_id not in self.zones:
            logger.warning(
                f"Zone '{zone_id}' not found"
            )
            return None

        zone = self.zones[zone_id]
        return {
            "zone_id": zone.zone_id,
            "name": zone.name,
            "boundaries": zone.boundaries,
            "area": zone.area,
            "priority": zone.priority,
            "last_mowed": (
                zone.last_mowed.isoformat() if zone.last_mowed else None
            ),
            "assigned_mower": zone.assigned_mower,
            "mowing_frequency_days": zone.mowing_frequency_days,
            "mowing_schedule": zone.mowing_schedule,
        }

    def get_all_zones(self) -> Dict[str, Dict[str, Any]]:
        """
        Get information about all zones.

        Returns:
            Dict[str, Dict[str, Any]]: Information for all zones.
        """
        zones = {}
        for zone_id in self.zones:
            zones[zone_id] = self.get_zone_info(zone_id)
        return zones

    def start_mower(
        self, mower_id: str, zone_id: Optional[str] = None
    ) -> bool:
        """
        Start a mower.

        Args:
            mower_id: Unique identifier for the mower.
            zone_id: Optional zone to mow. If None, the mower's assigned zone will be used.

        Returns:
            bool: True if the mower was started,
            False otherwise.
        """
        if mower_id not in self.mowers:
            logger.warning(f"Mower '{mower_id}' not found")
            return False

        mower = self.mowers[mower_id]

        # Determine the zone to mow
        if zone_id is not None:
            if zone_id not in self.zones:
                logger.warning(f"Zone '{zone_id}' not found")
                return False
            target_zone = zone_id
        else:
            # Find the mower's assigned zone
            target_zone = None
            for z_id, zone in self.zones.items():
                if zone.assigned_mower == mower_id:
                    target_zone = z_id
                    break

            if target_zone is None:
                logger.warning(f"Mower '{mower_id}' has no assigned zone")
                return False

        # Try to start the mower
        try:
            # In a real implementation, this would send a command to the mower
            # For now, we'll just update the status
            mower.status = MowerStatus.MOWING
            mower.current_zone = target_zone
            mower.current_operation_start = datetime.now()
            mower.last_seen = datetime.now()
            mower.error_message = None

            logger.info(f"Started mower '{mower_id}' in zone '{target_zone}'")
            self.save()
            return True
        except Exception as e:
            logger.error(f"Error starting mower '{mower_id}': {e}")
            return False

    def stop_mower(self, mower_id: str) -> bool:
        """
        Stop a mower.

        Args:
            mower_id: Unique identifier for the mower.

        Returns:
            bool: True if the mower was stopped, False otherwise.
        """
        if mower_id not in self.mowers:
            logger.warning(f"Mower '{mower_id}' not found")
            return False

        mower = self.mowers[mower_id]

        # Try to stop the mower
        try:
            # In a real implementation, this would send a command to the mower
            # For now, we'll just update the status
            if mower.status == MowerStatus.MOWING:
                # Update runtime and other stats
                if mower.current_operation_start:
                    runtime = (
                        datetime.now() - mower.current_operation_start
                    ).total_seconds() / 3600  # hours
                    mower.total_runtime += runtime

                    # Estimate distance and area based on runtime
                    # In a real implementation, this would come from the mower
                    mower.total_distance += (
                        runtime * 0.5
                    )  # km (assuming 0.5 km/h)
                    mower.total_area += (
                        runtime * 100
                    )  # m² (assuming 100 m²/h)

                # Update zone information
                if mower.current_zone and mower.current_zone in self.zones:
                    self.zones[mower.current_zone].last_mowed = datetime.now()

            mower.status = MowerStatus.IDLE
            mower.current_operation_start = None
            mower.last_seen = datetime.now()

            logger.info(f"Stopped mower '{mower_id}'")
            self.save()
            return True
        except Exception as e:
            logger.error(f"Error stopping mower '{mower_id}': {e}")
            return False

    def start_fleet_operation(self) -> Dict[str, bool]:
        """
        Start all mowers in the fleet.

        Returns:
            Dict[str, bool]: Results for each mower (True if started, False otherwise).
        """
        results = {}
        for mower_id in self.mowers:
            results[mower_id] = self.start_mower(mower_id)
        return results

    def stop_fleet_operation(self) -> Dict[str, bool]:
        """
        Stop all mowers in the fleet.

        Returns:
            Dict[str, bool]: Results for each mower (True if stopped, False otherwise).
        """
        results = {}
        for mower_id in self.mowers:
            results[mower_id] = self.stop_mower(mower_id)
        return results

    def _update_mower_status(self, mower: MowerInfo) -> None:
        """
        Update the status of a mower.

        Args:
            mower: Mower information object.
        """
        try:
            # In a real implementation, this would query the mower's API
            # For now, we'll just simulate some status updates

            # Simulate a connection to the mower
            # In a real implementation, this would be an HTTP request
            connected = True  # Simulate a successful connection

            if connected:
                # Update last seen time
                mower.last_seen = datetime.now()

                # Simulate battery discharge during operation
                if mower.status == MowerStatus.MOWING:
                    # Decrease battery level by 1% per 10 minutes of operation
                    if mower.current_operation_start:
                        hours_running = (
                            datetime.now() - mower.current_operation_start
                        ).total_seconds() / 3600
                        battery_decrease = hours_running * 6  # 6% per hour
                        mower.battery_level = max(
                            0, mower.battery_level - battery_decrease
                        )

                # Simulate battery charging when idle or charging
                elif mower.status in (MowerStatus.IDLE, MowerStatus.CHARGING):
                    # Increase battery level by 10% per hour
                    if mower.last_seen:
                        hours_since_last = (
                            datetime.now() - mower.last_seen
                        ).total_seconds() / 3600
                        battery_increase = (
                            hours_since_last * 10
                        )  # 10% per hour
                        mower.battery_level = min(
                            100, mower.battery_level + battery_increase
                        )
        except Exception as e:
            logger.error(f"Error updating mower status: {e}")

    def save(self) -> None:
        """Save fleet data to file."""
        data = {
            "mowers": {
                mower_id: mower.to_dict()
                for mower_id, mower in self.mowers.items()
            },
            "zones": {
                zone_id: zone.to_dict()
                for zone_id, zone in self.zones.items()
            },
        }

        try:
            with open(self.data_file, "w") as f:
                json.dump(data, f, indent=2)
            logger.debug(f"Saved fleet data to {self.data_file}")
        except Exception as e:
            logger.error(f"Error saving fleet data: {e}")

    def load(self) -> bool:
        """
        Load fleet data from file.

        Returns:
            bool: True if data was loaded successfully, False otherwise.
        """
        if not os.path.exists(self.data_file):
            logger.info(f"Fleet data file {self.data_file} not found")
            return False

        try:
            with open(self.data_file, "r") as f:
                data = json.load(f)

            # Load mowers
            self.mowers = {}
            for mower_id, mower_data in data.get("mowers", {}).items():
                self.mowers[mower_id] = MowerInfo.from_dict(mower_data)

            # Load zones
            self.zones = {}
            for zone_id, zone_data in data.get("zones", {}).items():
                self.zones[zone_id] = Zone.from_dict(zone_data)

            logger.info(f"Loaded fleet data from {self.data_file}")
            return True
        except Exception as e:
            logger.error(f"Error loading fleet data: {e}")
            return False
