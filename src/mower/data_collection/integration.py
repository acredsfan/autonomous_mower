"""
Integration module for the data collection feature.

This module handles the initialization of data collection components
and their integration with the mower's main components.
"""

import logging
import os
import subprocess
from typing import Any

from flask import Flask

from mower.data_collection.collector import DataCollector
from mower.ui.web_ui.data_collection_controller import DataCollectionController, datacollection_bp

logger = logging.getLogger(__name__)


def integrate_data_collection(app: Flask, mower: Any) -> bool:
    """
    Integrate data collection components with the mower and web UI.

    Args:
        app: The Flask application
        mower: The mower instance

    Returns:
        bool: True if integration was successful, False otherwise
    """
    try:
        # Check if mower has resource_manager attribute or is the resource_manager itself
        if hasattr(mower, 'resource_manager'):
            resource_manager = mower.resource_manager
        else:
            # If not, assume mower is the resource_manager itself
            resource_manager = mower
        
        # Check if ResourceManager is initialized and has necessary methods
        if not hasattr(resource_manager, 'get_config_manager'):
            logger.warning("ResourceManager not fully initialized. Using default configuration.")
            # Use default values when resources aren't available
            camera = None
            path_planner = None
            config_manager = None
        else:
            # Try to get components if available
            try:
                camera = resource_manager.get_camera()
            except Exception as e:
                logger.warning(f"Failed to get camera: {e}")
                camera = None
                
            try:
                path_planner = resource_manager.get_path_planner()
            except Exception as e:
                logger.warning(f"Failed to get path planner: {e}")
                path_planner = None
                
            try:
                config_manager = resource_manager.get_config_manager()
            except Exception as e:
                logger.warning(f"Failed to get config manager: {e}")
                config_manager = None

        # Create the data collection base directory if it doesn't exist
        default_storage_path = "data/collected_images"
        if config_manager:
            try:
                storage_path = config_manager.get_config("data_collection", {}).get("storage_path", default_storage_path)
            except Exception as e:
                logger.warning(f"Failed to get storage path from config: {e}")
                storage_path = default_storage_path
        else:
            storage_path = default_storage_path
            
        # Check if storage path is writable before proceeding
        try:
            os.makedirs(storage_path, exist_ok=True)
            # Test if directory is writable
            test_file = os.path.join(storage_path, '.write_test')
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)
            logger.info(f"Data collection storage path verified: {storage_path}")
        except (OSError, PermissionError) as e:
            logger.error(f"Data collection storage path not writable ({storage_path}): {e}")
            logger.warning("Data collection blueprint disabled due to storage issues")
            return False

        # Create data collector instance
        data_collector = DataCollector(path_planner, config_manager)

        # Store the data collector instance on the mower for access
        mower.data_collector = data_collector

        # Initialize the web controller and register the blueprint
        DataCollectionController(data_collector)

        # Register the blueprint with the Flask app
        app.register_blueprint(datacollection_bp)

        # Create static routes for accessing saved images
        # This makes the collected images accessible via the web UI
        if app.static_folder:
            data_directory = os.path.join(app.static_folder, "data")
            if not os.path.exists(data_directory):
                os.makedirs(data_directory, exist_ok=True)

            # Create a symlink to the images directory if it's not already in
            # static
            images_symlink = os.path.join(data_directory, "collected_images")
            if not os.path.exists(images_symlink) and storage_path:
                try:
                    # If this is an absolute path, it will symlink properly
                    # If it's a relative path, make it relative to the app root
                    if not os.path.isabs(storage_path):
                        abs_storage_path = os.path.join(os.path.dirname(app.root_path), storage_path)
                    else:
                        abs_storage_path = storage_path

                    # Create parent directory if it doesn't exist
                    os.makedirs(os.path.dirname(images_symlink), exist_ok=True)

                    # Create symlink on systems that support it
                    if os.name != "nt":  # Not Windows
                        os.symlink(abs_storage_path, images_symlink)
                    else:
                        # Windows requires a different approach
                        try:
                            # Try to create a directory junction on Windows
                            subprocess.run(["mklink", "/J", images_symlink, abs_storage_path], shell=True, check=True)
                        except (ImportError, subprocess.SubprocessError):
                            logger.warning(
                                "Could not create symlink on Windows. " "Images may not be accessible via the web UI."
                            )
                except Exception as e:
                    logger.warning(f"Failed to create symlink to images: {e}")
                    logger.warning("Images may not be accessible via the web UI")

        logger.info("Data collection components integrated successfully")
        return True

    except Exception as e:
        logger.error(f"Failed to integrate data collection: {e}")
        return False
