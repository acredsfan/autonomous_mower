"""
Camera test module for testing and configuring the camera system.

This module provides functions for testing the camera system of the autonomous
mower, including capturing images, testing streaming capabilities, and checking
camera settings. It can be run as a standalone script or the functions can be
imported and used in other modules.

Usage:
    python -m mower.diagnostics.camera_test

The module will capture and display images from the camera and allow testing
of different camera settings and resolutions.
"""

import time
import sys
import argparse
from typing import Optional, Tuple
import threading
import http.server
import socketserver
from pathlib import Path

from mower.utilities.logger_config import LoggerConfigInfo as LoggerConfig
from mower.main_controller import ResourceManager

try:
    import cv2
    import numpy as np
except ImportError:
    print("Error: OpenCV not installed. Please install with:")
    print("pip install opencv-python")
    sys.exit(1)

# Initialize logger
logging = LoggerConfig.get_logger(__name__)


def capture_test_image(
    resource_manager: ResourceManager, save_path: Optional[str] = None
) -> Optional[np.ndarray]:
    """
    Capture a test image from the camera.

    Args:
        resource_manager: An instance of ResourceManager.
        save_path: Optional path to save the captured image.

    Returns:
        The captured image as a NumPy array, or None if capture failed.
    """
    try:
        camera = resource_manager.get_camera()
        if camera is None:
            logging.error("Failed to get camera instance")
            return None

        print("Capturing test image...")
        frame = camera.capture_frame()

        if frame is None or frame.size == 0:
            logging.error("Failed to capture image")
            return None

        print(f"Image captured: {frame.shape[1]}x{frame.shape[0]} pixels")

        if save_path:
            cv2.imwrite(save_path, frame)
            print(f"Image saved to: {save_path}")

        return frame

    except Exception as e:
        logging.error(f"Error capturing test image: {e}")
        return None


def display_image(
    image: np.ndarray, window_name: str = "Camera Test"
) -> None:
    """
    Display an image in a window.

    Args:
        image: The image to display as a NumPy array.
        window_name: The name of the window.
    """
    try:
        cv2.imshow(window_name, image)
        print("Press any key to close the image window.")
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    except Exception as e:
        logging.error(f"Error displaying image: {e}")


def start_stream_test(
    resource_manager: ResourceManager,
    resolution: Tuple[int, int] = (640, 480),
    port: int = 8090,
    duration: int = 30,
) -> bool:
    """
    Start a test stream server to view camera feed.

    Args:
        resource_manager: An instance of ResourceManager.
        resolution: Tuple of (width, height) for the stream resolution.
        port: Port number for the HTTP stream server.
        duration: Duration in seconds to run the stream.

    Returns:
        True if the stream was started successfully, False otherwise.
    """
    try:
        camera = resource_manager.get_camera()
        if camera is None:
            logging.error("Failed to get camera instance")
            return False

        # Create a directory for stream files
        stream_dir = Path("./camera_test_stream")
        stream_dir.mkdir(exist_ok=True)

        # Create an HTML file for the stream
        html_path = stream_dir / "index.html"
        with open(html_path, "w") as f:
            f.write(
                """
            <!DOCTYPE html>
            <html>
            <head>
                <title>Camera Test Stream</title>
                <meta name="viewport" content="width=device-width, \
initial-scale=1">
                <style>
                    body {
                        font-family: Arial, sans-serif;
                        margin: 0;
                        padding: 20px;
                        text-align: center;
                    }
                    img { max-width: 100%; border: 1px solid #ddd; }
                    .container { max-width: 800px; margin: 0 auto; }
                    h1 { color: #333; }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>Camera Test Stream</h1>
                    <img src="stream.jpg" id="stream">
                    <p>This image updates automatically every second.</p>
                </div>
                <script>
                    // Reload the image every second
                    setInterval(function() {
                        var img = document.getElementById('stream');
                        img.src = 'stream.jpg?t=' + new Date().getTime();
                    }, 1000);
                </script>
            </body>
            </html>
            """
            )

        # Create a class to handle HTTP requests
        class StreamHandler(http.server.SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=str(stream_dir), **kwargs)

        # Start the HTTP server in a separate thread
        server = socketserver.TCPServer(("", port), StreamHandler)
        server_thread = threading.Thread(target=server.serve_forever)
        server_thread.daemon = True
        server_thread.start()

        print(f"Stream server started at http://localhost:{port}")
        print(f"Stream will run for {duration} seconds.")
        print("Access the stream from a web browser using the URL above.")

        # Start time for duration tracking
        start_time = time.time()

        # Main loop to update the stream image
        try:
            while time.time() - start_time < duration:
                frame = camera.capture_frame()
                if frame is not None:
                    # Resize frame if needed
                    if resolution != (frame.shape[1], frame.shape[0]):
                        frame = cv2.resize(frame, resolution)

                    # Save frame to the stream directory
                    cv2.imwrite(str(stream_dir / "stream.jpg"), frame)

                time.sleep(0.1)

        finally:
            # Shutdown the server
            server.shutdown()
            server.server_close()
            print("Stream server stopped.")

        return True

    except Exception as e:
        logging.error(f"Error starting stream test: {e}")
        return False


def test_camera_settings(resource_manager: ResourceManager) -> bool:
    """
    Test different camera settings to find optimal configuration.

    Args:
        resource_manager: An instance of ResourceManager.

    Returns:
        True if the test completed successfully, False otherwise.
    """
    try:
        camera = resource_manager.get_camera()
        if camera is None:
            logging.error("Failed to get camera instance")
            return False

        print("\n===== CAMERA SETTINGS TEST =====")
        print("This test will try different camera settings and")
        print("capture images with each configuration.")
        input("Press Enter to start the test or Ctrl+C to cancel...")

        # Create a directory for test images
        test_dir = Path("./camera_test_settings")
        test_dir.mkdir(exist_ok=True)

        # Default settings
        default_brightness = 50
        default_contrast = 50

        # Test parameters to try
        brightness_values = [30, 50, 70]
        contrast_values = [40, 50, 60]

        print("\nTesting brightness settings...")
        for brightness in brightness_values:
            try:
                camera.set_property(cv2.CAP_PROP_BRIGHTNESS, brightness)
                print(f"Setting brightness to {brightness}")
                frame = camera.capture_frame()
                if frame is not None:
                    file_path = str(test_dir / f"brightness_{brightness}.jpg")
                    cv2.imwrite(file_path, frame)
                    print(f"Saved to {file_path}")
            except Exception as e:
                print(f"Error setting brightness to {brightness}: {e}")

        # Reset to default
        camera.set_property(cv2.CAP_PROP_BRIGHTNESS, default_brightness)

        print("\nTesting contrast settings...")
        for contrast in contrast_values:
            try:
                camera.set_property(cv2.CAP_PROP_CONTRAST, contrast)
                print(f"Setting contrast to {contrast}")
                frame = camera.capture_frame()
                if frame is not None:
                    file_path = str(test_dir / f"contrast_{contrast}.jpg")
                    cv2.imwrite(file_path, frame)
                    print(f"Saved to {file_path}")
            except Exception as e:
                print(f"Error setting contrast to {contrast}: {e}")

        # Reset to default
        camera.set_property(cv2.CAP_PROP_CONTRAST, default_contrast)

        print("\nCamera settings test completed.")
        print(f"Test images saved to {test_dir}")

        return True

    except Exception as e:
        logging.error(f"Error testing camera settings: {e}")
        return False


def main():
    """
    Run the camera test module from the command line.

    Command-line options:
        --capture: Capture and display a test image
        --save PATH: Save the captured image to the specified path
        --stream: Start a test stream server
        --settings: Test different camera settings
    """
    parser = argparse.ArgumentParser(
        description="Camera testing and configuration"
    )
    parser.add_argument(
        "--capture",
        action="store_true",
        help="Capture and display a test image",
    )
    parser.add_argument(
        "--save",
        type=str,
        help="Save the captured image to the specified path",
    )
    parser.add_argument(
        "--stream", action="store_true", help="Start a test stream server"
    )
    parser.add_argument(
        "--port", type=int, default=8090, help="Port for the stream server"
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=30,
        help="Duration in seconds for the stream",
    )
    parser.add_argument(
        "--settings",
        action="store_true",
        help="Test different camera settings",
    )

    args = parser.parse_args()

    # If no arguments, default to capture
    if not any([args.capture, args.stream, args.settings]):
        args.capture = True

    resource_manager = ResourceManager()

    if args.capture:
        image = capture_test_image(resource_manager, args.save)
        if image is not None and not args.save:
            display_image(image)

    if args.stream:
        start_stream_test(
            resource_manager, port=args.port, duration=args.duration
        )

    if args.settings:
        test_camera_settings(resource_manager)


if __name__ == "__main__":
    main()
