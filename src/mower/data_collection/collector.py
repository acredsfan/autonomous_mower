"""
DataCollector module for autonomous mower.

This module handles the automated collection of images for AI model fine-tuning.
It implements functionality for autonomous roaming and image capture with metadata.
"""
import logging
import os
import time
import uuid
from datetime import datetime
from typing import Dict, Optional, Any

import cv2

from mower.config_management.config_manager import ConfigManager
from mower.hardware.camera_instance import CameraInstance
from mower.navigation.path_planner import PathPlanner, PatternType
from mower.hardware.sensor_types import SensorReading

logger = logging.getLogger(__name__)


class DataCollector:
    """DataCollector handles autonomous data collection for AI model training.

    This class provides functionality to roam around and capture images with
    appropriate metadata for later use in model fine-tuning.
    """

    def __init__(
        self,
        camera: CameraInstance,
        path_planner: PathPlanner,
        config_manager: ConfigManager,
    ):
        """Initialize the DataCollector.

        Args:
            camera: Instance of CameraInstance used to capture images
            path_planner: Instance of PathPlanner for navigation
            config_manager: Instance of ConfigManager for configuration access
        """
        self.camera = camera
        self.path_planner = path_planner
        self.config_manager = config_manager

        # Load configuration
        self.config = self._load_config()

        # Set up image storage directory
        self.base_storage_path = self.config.get(
            "storage_path", "data/collected_images")
        self.current_session_path = None

        # Collection state
        self.is_collecting = False
        self.current_session_id = None
        self.images_collected = 0
        self.collection_start_time = None
        self.image_interval = self.config.get("image_interval", 5)  # seconds
        self.last_image_time = 0

        # Ensure storage directory exists
        os.makedirs(self.base_storage_path, exist_ok=True)

        logger.info("DataCollector initialized")

    def _load_config(self) -> Dict:
        """Load data collection configuration"""
        try:
            dc_config = self.config_manager.get_config("data_collection", {})
            return {
                "storage_path": dc_config.get(
                    "storage_path", "data/collected_images"),
                "image_interval": dc_config.get(
                    "image_interval", 5),
                "max_images": dc_config.get(
                    "max_images", 1000),
                "collection_pattern": dc_config.get(
                    "collection_pattern", "PARALLEL"),
                "image_quality": dc_config.get(
                    "image_quality", 95),
                "save_metadata": dc_config.get(
                    "save_metadata", True),
                "resolution": dc_config.get(
                    "resolution", (640, 480)),
            }
        except Exception as e:
            logger.error(f"Failed to load data collection config: {e}")
            # Default configuration
            return {
                "storage_path": "data/collected_images",
                "image_interval": 5,
                "max_images": 1000,
                "collection_pattern": "PARALLEL",
                "image_quality": 95,
                "save_metadata": True,
                "resolution": (640, 480),
            }

    def start_collection(self, session_name: Optional[str] = None) -> str:
        """
        Start collecting data.

        Args:
            session_name: Optional name for the collection session

        Returns:
            session_id: UUID of the started session
        """
        if self.is_collecting:
            logger.warning("Data collection already in progress")
            return self.current_session_id

        # Generate session ID and create directory
        self.current_session_id = str(uuid.uuid4())
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if session_name:
            dir_name = f"{timestamp}_{session_name}_{self.current_session_id[:8]}"
        else:
            dir_name = f"{timestamp}_{self.current_session_id[:8]}"

        self.current_session_path = os.path.join(
            self.base_storage_path, dir_name)
        os.makedirs(
            self.current_session_path,
            exist_ok=True)        # Reset counters
        self.images_collected = 0
        self.collection_start_time = time.time()
        self.last_image_time = 0
        self.is_collecting = True

        # Configure path planning pattern
        pattern_name = self.config.get("collection_pattern", "PARALLEL")

        try:
            # Generate a path with the selected pattern
            self.path_planner.generate_pattern(
                pattern_name,
                {
                    "spacing": 1.0,
                    "angle": 0.0,
                    "overlap": 0.1
                }
            )
        except (AttributeError, ValueError) as e:
            logger.warning(
                f"Pattern {pattern_name} not found, using PARALLEL: {e}")

            # Fall back to PARALLEL pattern
            self.path_planner.generate_pattern(
                "PARALLEL",
                {
                    "spacing": 1.0,
                    "angle": 0.0,
                    "overlap": 0.1
                }
            )

        # Create session metadata file
        self._save_session_metadata()

        logger.info(
            f"Started data collection session {self.current_session_id}"
        )
        return self.current_session_id
    
    def stop_collection(self) -> Dict[str, Any]:
        """
        Stop the current data collection session.

        Returns:
            Dict containing session statistics
        """
        if not self.is_collecting:
            logger.warning("No data collection session in progress")
            return {"status": "not_running"}

        self.is_collecting = False

        # Calculate statistics
        current_time = time.time()
        duration = 0.0
        if self.collection_start_time is not None:
            duration = current_time - self.collection_start_time

        stats = {
            "session_id": self.current_session_id,
            "images_collected": self.images_collected,
            "duration_seconds": duration,
            "path": self.current_session_path,
            "status": "completed"
        }

        # Update session metadata with completion info
        self._update_session_metadata(stats)

        logger.info(
            f"Stopped data collection session {self.current_session_id}")
        return stats

    def process(
            self, sensor_data: Optional[Dict[str, SensorReading]] = None) -> bool:
        """
        Process one iteration of data collection.
        Should be called regularly from the main control loop.

        Args:
            sensor_data: Optional current sensor readings

        Returns:
            bool: True if an image was collected, False otherwise
        """
        if not self.is_collecting:
            return False

        current_time = time.time()
        time_since_last_image = current_time - self.last_image_time

        # Check if it's time to capture an image
        if time_since_last_image >= self.image_interval:
            self.capture_image(sensor_data)
            self.last_image_time = current_time
            return True

        return False

    def capture_image(
            self,
            sensor_data: Optional[Dict[str, SensorReading]] = None
    ) -> Optional[str]:
        """
        Capture and save an image with metadata.

        Args:
            sensor_data: Optional current sensor readings

        Returns:
            str: Path to saved image or None if capture failed
        """
        if not self.is_collecting:
            logger.warning("Cannot capture image: collection not in progress")
            return None

        try:            # Check if max images reached
            max_images = self.config.get("max_images", 1000)
            if self.images_collected >= max_images:
                logger.info(
                    f"Reached maximum number of images ({max_images}), "
                    f"stopping collection")
                self.stop_collection()
                return None

            # Capture image
            frame = self.camera.capture_frame()
            if frame is None:
                logger.error("Failed to capture frame from camera")
                return None            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            image_index = str(self.images_collected).zfill(6)
            filename = f"img_{image_index}_{timestamp}.jpg"

            # Check if session path is valid
            if self.current_session_path is None:
                logger.error("Current session path is None, cannot save image")
                return None

            filepath = os.path.join(
                self.current_session_path,
                filename)            # Save image
            try:
                quality = self.config.get("image_quality", 95)
                # Check if frame is bytes (JPEG) or numpy array (raw frame)
                if isinstance(frame, bytes):
                    # If it's already JPEG bytes, write directly to file
                    with open(filepath, 'wb') as f:
                        f.write(frame)
                    success = True
                else:
                    # If it's a numpy array, use cv2.imwrite
                    success = cv2.imwrite(
                        filepath, frame,
                        [int(cv2.IMWRITE_JPEG_QUALITY),
                         quality])

                if not success:
                    logger.error(f"Failed to save image to {filepath}")
                    return None
            except Exception as e:
                logger.error(f"Error saving image: {e}")
                return None

            # Save metadata if configured
            if self.config.get("save_metadata", True):
                metadata_path = filepath.replace(".jpg", ".json")
                self._save_image_metadata(metadata_path, sensor_data)

            # Update counter
            self.images_collected += 1

            logger.debug(f"Captured image {self.images_collected}: {filepath}")
            return filepath

        except Exception as e:
            logger.error(f"Error capturing image: {e}")
            return None

    def _save_image_metadata(
            self, metadata_path: str,
            sensor_data: Optional[Dict[str, SensorReading]] = None) -> None:
        """
        Save metadata for a captured image.

        Args:
            metadata_path: Path to save the metadata JSON file
            sensor_data: Optional sensor data to include
        """
        import json

        metadata = {
            "timestamp": datetime.now().isoformat(),
            "image_index": self.images_collected,
            "session_id": self.current_session_id,
        }

        # Add sensor data if available
        if sensor_data:
            sensor_meta = {}
            for sensor_name, reading in sensor_data.items():
                # Convert sensor readings to serializable format
                if isinstance(reading, SensorReading):
                    sensor_meta[sensor_name] = {
                        "value": reading.value,
                        "timestamp": reading.timestamp,
                        "status": reading.status
                    }
            metadata["sensor_data"] = sensor_meta

        # Add GPS coordinates if available in sensor data
        if sensor_data and "gps" in sensor_data:
            try:
                gps_reading = sensor_data["gps"]
                if hasattr(gps_reading, "value") and gps_reading.value:
                    metadata["gps"] = gps_reading.value
            except (KeyError, AttributeError):
                pass

        try:
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save metadata: {e}")

    def _save_session_metadata(self) -> None:
        """Save metadata for the current collection session"""
        import json

        if not self.current_session_path:
            logger.error("No current session path")
            return

        metadata_path = os.path.join(
            self.current_session_path,
            "session_info.json")

        metadata = {
            "session_id": self.current_session_id,
            "start_time": datetime.now().isoformat(),
            "pattern": self.config.get("collection_pattern", "PARALLEL"),
            "image_interval": self.image_interval,
            "max_images": self.config.get("max_images", 1000),
            "resolution": self.config.get("resolution", (640, 480)),
        }

        try:
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save session metadata: {e}")

    def _update_session_metadata(self, stats: Dict[str, Any]) -> None:
        """
        Update session metadata with completion information.

        Args:
            stats: Dictionary of session statistics
        """
        import json

        if not self.current_session_path:
            logger.error("No current session path")
            return

        metadata_path = os.path.join(
            self.current_session_path,
            "session_info.json")

        try:
            # Read existing metadata
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)

            # Update with completion info
            metadata.update({
                "end_time": datetime.now().isoformat(),
                "images_collected": stats["images_collected"],
                "duration_seconds": stats["duration_seconds"],
                "status": "completed"
            })

            # Write updated metadata
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)

        except Exception as e:
            logger.error(f"Failed to update session metadata: {e}")

    def get_session_status(self) -> Dict[str, Any]:
        """
        Get the status of the current collection session.

        Returns:
            Dict containing session status
        """
        if not self.is_collecting:
            return {"status": "not_running"}

        current_time = time.time()
        duration = 0.0
        if self.collection_start_time is not None:
            duration = current_time - self.collection_start_time

        return {
            "status": "running",
            "session_id": self.current_session_id,
            "images_collected": self.images_collected,
            "duration_seconds": duration,
            "session_path": self.current_session_path,
            "pattern": self.config.get("collection_pattern", "PARALLEL"),
            "image_interval": self.image_interval
        }

    def set_image_interval(self, interval: float) -> None:
        """
        Set the interval between image captures.

        Args:
            interval: Time in seconds between captures
        """
        if interval < 0.1:
            logger.warning(
                f"Image interval too small ({interval}s), setting to 0.1s")
            interval = 0.1

        self.image_interval = interval
        logger.debug(f"Image interval set to {interval}s")

    def change_collection_pattern(self, pattern_name: str) -> bool:
        """
        Change the pattern used for data collection navigation.

        Args:
            pattern_name: Name of the pattern to use (must be a valid PatternType enum)

        Returns:
            bool: True if pattern was changed successfully
        """
        try:
            # Check if pattern is valid
            getattr(PatternType, pattern_name)  # Validate pattern name

            # Generate a path with the selected pattern
            self.path_planner.generate_pattern(
                pattern_name,
                {
                    "spacing": 1.0,
                    "angle": 0.0,
                    "overlap": 0.1
                }
            )

            # Update configuration
            self.config["collection_pattern"] = pattern_name

            logger.info(f"Collection pattern changed to {pattern_name}")
            return True

        except (AttributeError, ValueError) as e:
            logger.error(f"Failed to change pattern: {e}")
            return False
