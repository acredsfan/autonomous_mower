# __init__.py

from ...hardware_interface.camera import SingletonCamera

# Create a controlled accessor for SingletonCamera
_camera_instance = None

def get_singleton_camera():
    global _camera_instance
    if _camera_instance is None:
        _camera_instance = SingletonCamera()  # Only create it when first accessed
    return _camera_instance

__all__ = ['get_singleton_camera']