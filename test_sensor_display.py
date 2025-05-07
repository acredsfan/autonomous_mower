#!/usr/bin/env python3
"""
Test script for sensor data display in the autonomous mower.

This script directly tests the sensor classes to verify they can
provide data consistently across different platforms (Linux/Windows).
It can also be used to test the web UI sensor display by running alongside
the web UI server.

Usage:
    python test_sensor_display.py [--web-test]

    --web-test: Opens a simple test interface to help verify web UI sensor display
"""

from mower.hardware.imu import BNO085Sensor
from mower.hardware.tof import VL53L0XSensors
import os
import sys
import json
import time
import platform
import argparse
import threading
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler

# Add the project's src directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

# Import the sensor classes


class TestHTTPHandler(BaseHTTPRequestHandler):
    """Simple HTTP handler for web UI test mode"""

    def do_GET(self):
        """Handle GET requests"""
        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(self.get_test_html().encode())
        else:
            self.send_response(404)
            self.end_headers()

    def get_test_html(self):
        """Return HTML for the test page"""
        css = """
            body {
                font-family: Arial, sans-serif;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
            }
            .card {
                border: 1px solid #ddd;
                border-radius: 5px;
                padding: 15px;
                margin-bottom: 15px;
            }
            h1, h2 { color: #333; }
            table { width: 100%; border-collapse: collapse; }
            th, td {
                padding: 8px;
                text-align: left;
                border-bottom: 1px solid #ddd;
            }
            th { background-color: #f2f2f2; }
            .instructions {
                background-color: #f8f9fa;
                padding: 15px;
                border-left: 4px solid #007bff;
            }
            .step { margin-bottom: 10px; }
            .highlight { background-color: yellow; font-weight: bold; }
        """

        steps = [
            "<b>Step 1:</b> Keep this test script running in the terminal",
            "<b>Step 2:</b> In a separate terminal, start the web UI server with:",
            "<b>Step 3:</b> Open the web UI in a browser and navigate to the " +
            '<span class="highlight">Diagnostics</span> tab',
            "<b>Step 4:</b> Compare the values shown below with what appears in the " +
            "web UI's Diagnostics tab",
            "<b>Step 5:</b> If the values in the web UI match the ones below, " +
            "the sensor display issue is fixed!",
        ]

        steps_html = "\n".join(
            [f'<div class="step">{step} </div>'for step in steps])

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Sensor Test Helper</title>
            <style>
                {css}
            </style>
        </head>
        <body>
            <h1>Autonomous Mower Sensor Test Helper</h1>

            <div class="card instructions">
                <h2>Test Instructions</h2>
                {steps_html}
                <div class="step">
                    <pre>python -m mower.ui.web_ui.app</pre>
                </div>
            </div>

            <h2>Test Results</h2>
            <div class="card">
                <p><b>Platform:</b> {platform.system()}</p>
                <p>
                    Refresh this page to see the latest sensor values being
                    generated.
                </p>

                <h3>Sensor Values</h3>
                <p>These are the values that should appear in the web UI:</p>

                <h4>ToF Distance Sensors:</h4>
                <table id="tofTable">
                    <tr>
                        <th>Sensor</th>
                        <th>Value</th>
                        <th>Web UI Element ID</th>
                    </tr>
                    <!-- Values will be filled in by the test script -->
                </table>

                <h4>IMU Data:</h4>
                <table id="imuTable">
                    <tr>
                        <th>Sensor</th>
                        <th>Value</th>
                        <th>Web UI Element ID</th>
                    </tr>
                    <!-- Values will be filled in by the test script -->
                </table>
            </div>
        </body>
        </html>
        """
        return html


def web_test_mode():
    """Run a simple web server to help test integration with the web UI"""
    # Start HTTP server to provide test instructions
    server_address = ("", 8000)
    httpd = HTTPServer(server_address, TestHTTPHandler)
    print("Starting test helper web server on http://localhost:8000")
    print("Please keep this running and follow the instructions on the web page")

    # Open browser automatically
    webbrowser.open("http://localhost:8000")

    # Start server in a separate thread so we can also display sensor values
    server_thread = threading.Thread(target=httpd.serve_forever)
    server_thread.daemon = True
    server_thread.start()


def main():
    """Main function"""
    # Parse arguments
    parser = argparse.ArgumentParser(
        description="Test sensor data for the autonomous mower"
    )
    parser.add_argument(
        "--web-test", action="store_true", help="Run in web testing mode"
    )
    # Parse args but we don't use the result directly
    parser.parse_args()

    print("=== Autonomous Mower Sensor Test ===")
    print(f"Platform: {platform.system()}")
    print("Initializing sensors...")

    # Initialize the sensor objects
    tof_sensor = VL53L0XSensors()
    imu_sensor = BNO085Sensor()

    # Test loop
    try:
        while True:
            # Clear screen (works on both Windows and Unix-like systems)
            os.system("cls" if platform.system() == "Windows" else "clear")

            print("=== Autonomous Mower Sensor Test ===")
            print(f"Platform: {platform.system()}")

            # Display hardware detection status
            hw_tof = "Available" if tof_sensor.is_hardware_available else "Simulated"
            hw_imu = "Available" if imu_sensor.is_hardware_available else "Simulated"
            print(f"Hardware detection: ToF={hw_tof}, IMU={hw_imu}")

            # Get ToF data
            tof_data = tof_sensor.get_distances()
            print("\n--- ToF Distance Sensors (Front-mounted) ---")
            print(f"Left: {tof_data['left']:.1f} mm")
            print(f"Right: {tof_data['right']:.1f} mm")

            # Get IMU data
            heading = imu_sensor.get_heading()
            roll = imu_sensor.get_roll()
            pitch = imu_sensor.get_pitch()
            safety = imu_sensor.get_safety_status()

            print("\n--- IMU Data ---")
            print(f"Heading: {heading:.1f}°")
            print(f"Roll: {roll:.1f}°")
            print(f"Pitch: {pitch:.1f}°")

            print("\n--- Safety Status ---")
            for status, value in safety.items():
                status_text = status.replace("_", " ").title()
                status_indicator = "⚠️ WARNING" if value else "✓ OK"
                print(f"{status_text}: {status_indicator}")
            # Create full sensor data structure like the web UI would receive
            sensor_data = {
                "imu": {
                    "heading": heading,
                    "roll": roll,
                    "pitch": pitch,
                    "safety_status": safety,
                },
                "tof": {"left": tof_data["left"], "right": tof_data["right"]},
            }

            print("\n--- Raw JSON Data ---")
            print(json.dumps(sensor_data, indent=2))
            print("\nPress Ctrl+C to exit...")

            time.sleep(1)

    except KeyboardInterrupt:
        print("\nTest stopped by user")
    except Exception as e:
        print(f"\nError: {e}")


if __name__ == "__main__":
    main()
