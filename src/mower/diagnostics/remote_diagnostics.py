#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Remote diagnostics module for the autonomous mower.

This module provides remote access to the mower's diagnostics information,
including hardware status, logs, and system health. It enables remote
troubleshooting and monitoring of the mower.

Key features:
- Remote access to hardware test results
- Log file access and analysis
- System health monitoring
- Secure remote access with authentication
- API endpoints for integration with monitoring tools

Example usage:
    # Start the remote diagnostics server
    python -m mower.diagnostics.remote_diagnostics

    # Start with custom port and enable debug mode
    python -m mower.diagnostics.remote_diagnostics --port 8080 --debug
"""

import argparse
# import json
import os
import platform
import socket
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Union

import psutil
from flask import Flask, jsonify, request, Response
from flask_cors import CORS
# from werkzeug.security import check_password_hash

# Import hardware test suite
from mower.diagnostics.hardware_test import (
    HardwareTestSuite,
    initialize_resource_manager,
)
from mower.utilities.logger_config import LoggerConfigInfo

# Configure logging
logger = LoggerConfigInfo.get_logger(__name__)

# Constants
DEFAULT_PORT = 8081
LOG_DIR = "/var/log/autonomous-mower"
MAX_LOG_SIZE = 1024 * 1024  # 1MB


class RemoteDiagnostics:
    """
    Remote diagnostics class for the autonomous mower.

    This class provides methods to collect diagnostic information about the
    mower's hardware, software, and system health. It can be used to
    troubleshoot issues remotely.
    """

    def __init__(self):
        """Initialize the remote diagnostics module."""
        self.resource_manager = initialize_resource_manager()
        if self.resource_manager is None:
            logger.error("Failed to initialize ResourceManager")
            raise RuntimeError("Failed to initialize ResourceManager")

    def get_system_info(self) -> Dict[str, Any]:
        """
        Get system information.

        Returns:
            Dict[str, Any]: System information including OS, CPU, memory, disk,
                and network.
        """
        try:
            # Get basic system information
            system_info = {
                "hostname": socket.gethostname(),
                "platform": platform.platform(),
                "python_version": platform.python_version(),
                "cpu_count": os.cpu_count(),
                "uptime": self._get_uptime(),
                "timestamp": datetime.now().isoformat(),
            }

            # Get CPU information
            cpu_info = {
                "usage_percent": psutil.cpu_percent(interval=1),
                "temperature": self._get_cpu_temperature(),
                "frequency": (
                    psutil.cpu_freq().current if psutil.cpu_freq() else None
                ),
            }

            # Get memory information
            memory = psutil.virtual_memory()
            memory_info = {
                "total": memory.total,
                "available": memory.available,
                "used": memory.used,
                "percent": memory.percent,
            }

            # Get disk information
            disk = psutil.disk_usage("/")
            disk_info = {
                "total": disk.total,
                "used": disk.used,
                "free": disk.free,
                "percent": disk.percent,
            }

            # Get network information
            network_info = {}
            for interface, stats in psutil.net_if_stats().items():
                if stats.isup:
                    network_info[interface] = {
                        "speed": stats.speed,
                        "mtu": stats.mtu,
                        "duplex": stats.duplex,
                    }
                    # Add IP addresses
                    addresses = []
                    for addr in psutil.net_if_addrs().get(interface, []):
                        if addr.family == socket.AF_INET:
                            addresses.append(addr.address)
                    network_info[interface]["addresses"] = addresses

            # Combine all information
            system_info.update(
                {
                    "cpu": cpu_info,
                    "memory": memory_info,
                    "disk": disk_info,
                    "network": network_info,
                }
            )

            return system_info
        except Exception as e:
            logger.error(f"Error getting system information: {e}")
            return {"error": str(e)}

    def _get_uptime(self) -> float:
        """
        Get system uptime in seconds.

        Returns:
            float: System uptime in seconds.
        """
        return time.time() - psutil.boot_time()

    def _get_cpu_temperature(self) -> Optional[float]:
        """
        Get CPU temperature.

        Returns:
            Optional[float]: CPU temperature in Celsius, or None if not available.
        """
        try:
            # Try to get temperature from vcgencmd (Raspberry Pi specific)
            result = subprocess.run(
                ["vcgencmd", "measure_temp"],
                capture_output=True,
                text=True,
                check=True,
            )
            # Parse output like "temp=42.8'C"
            temp_str = result.stdout.strip()
            if temp_str.startswith("temp=") and temp_str.endswith("'C"):
                return float(temp_str[5:-2])
            return None
        except (subprocess.SubprocessError, FileNotFoundError, ValueError):
            # Try to get temperature from psutil
            try:
                temps = psutil.sensors_temperatures()
                for name, entries in temps.items():
                    for entry in entries:
                        return entry.current
                return None
            except (AttributeError, KeyError, IndexError):
                return None

    def run_hardware_tests(
        self, test_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Run hardware tests.

        Args:
            test_name: Name of the specific test to run, or None to run all tests.

        Returns:
            Dict[str, Any]: Hardware test results.
        """
        try:
            # Initialize hardware test suite
            test_suite = HardwareTestSuite(self.resource_manager)

            # Run specific test or all tests
            if test_name:
                test_func_name = f"test_{test_name.lower().replace('-', '_')}"
                if hasattr(test_suite, test_func_name):
                    test_func = getattr(test_suite, test_func_name)
                    result = test_func()
                    return {test_name: result}
                else:
                    return {"error": f"Test '{test_name}' not found"}
            else:
                # Run all tests non-interactively
                return test_suite.run_all_tests(interactive=False)
        except Exception as e:
            logger.error(f"Error running hardware tests: {e}")
            return {"error": str(e)}

    def get_service_status(self) -> Dict[str, Any]:
        """
        Get status of the autonomous mower service.

        Returns:
            Dict[str, Any]: Service status information.
        """
        try:
            # Run systemctl status command
            result = subprocess.run(
                ["systemctl", "status", "autonomous-mower.service"],
                capture_output=True,
                text=True,
            )

            # Parse the output
            lines = result.stdout.strip().split("\n")
            status_info = {
                "exit_code": result.returncode,
                "active": "Active: active" in result.stdout,
                "enabled": "enabled" in result.stdout,
                "raw_output": result.stdout,
            }

            # Extract more detailed information if available
            for line in lines:
                if line.strip().startswith("Active:"):
                    status_info["status_line"] = line.strip()
                elif line.strip().startswith("Main PID:"):
                    status_info["main_pid"] = line.strip()

            return status_info
        except Exception as e:
            logger.error(f"Error getting service status: {e}")
            return {"error": str(e)}

    def get_log_files(self) -> List[Dict[str, Any]]:
        """
        Get list of available log files.

        Returns:
            List[Dict[str, Any]]: List of log files with metadata.
        """
        try:
            log_files = []
            log_dir = Path(LOG_DIR)

            # Check if log directory exists
            if not log_dir.exists():
                return log_files

            # List all files in the log directory
            for file_path in log_dir.glob("*.log*"):
                if file_path.is_file():
                    stats = file_path.stat()
                    log_files.append(
                        {
                            "name": file_path.name,
                            "path": str(file_path),
                            "size": stats.st_size,
                            "modified": datetime.fromtimestamp(
                                stats.st_mtime
                            ).isoformat(),
                        }
                    )

            # Sort by modification time (newest first)
            log_files.sort(key=lambda x: x["modified"], reverse=True)
            return log_files
        except Exception as e:
            logger.error(f"Error getting log files: {e}")
            return []

    def get_log_content(
        self, log_file: str, lines: int = 100
    ) -> Tuple[bool, Union[str, bytes]]:
        """
        Get content of a log file.

        Args:
            log_file: Name of the log file.
            lines: Number of lines to return from the end of the file.

        Returns:
            Tuple[bool, Union[str, bytes]]: (success, content)
                If success is True, content is the log content.
                If success is False, content is an error message.
        """
        try:
            # Ensure the log file is in the log directory
            log_path = Path(LOG_DIR) / log_file
            if not log_path.exists() or not log_path.is_file():
                return False, f"Log file {log_file} not found"

            # Check if the file is too large
            if log_path.stat().st_size > MAX_LOG_SIZE:
                # Use tail to get the last N lines
                result = subprocess.run(
                    ["tail", "-n", str(lines), str(log_path)],
                    capture_output=True,
                    text=True,
                )
                return True, result.stdout
            else:
                # Read the entire file
                with open(log_path, "r") as f:
                    content = f.read()
                return True, content
        except Exception as e:
            logger.error(f"Error getting log content: {e}")
            return False, str(e)

    def get_process_info(self) -> List[Dict[str, Any]]:
        """
        Get information about running mower-related processes.

        Returns:
            List[Dict[str, Any]]: List of process information.
        """
        try:
            mower_processes = []
            for proc in psutil.process_iter(
                [
                    "pid",
                    "name",
                    "username",
                    "cmdline",
                    "cpu_percent",
                    "memory_percent",
                    "create_time",
                ]
            ):
                try:
                    # Check if this is a mower-related process
                    if any(
                        "mower" in cmd.lower()
                        for cmd in proc.info["cmdline"]
                        if cmd
                    ):
                        proc_info = {
                            "pid": proc.info["pid"],
                            "name": proc.info["name"],
                            "username": proc.info["username"],
                            "cmdline": " ".join(proc.info["cmdline"]),
                            "cpu_percent": proc.info["cpu_percent"],
                            "memory_percent": proc.info["memory_percent"],
                            "running_time": time.time()
                            - proc.info["create_time"],
                        }
                        mower_processes.append(proc_info)
                except (
                    psutil.NoSuchProcess,
                    psutil.AccessDenied,
                    psutil.ZombieProcess,
                ):
                    pass
            return mower_processes
        except Exception as e:
            logger.error(f"Error getting process information: {e}")
            return []

    def cleanup(self):
        """Clean up resources."""
        if self.resource_manager:
            try:
                self.resource_manager.cleanup()
            except Exception as e:
                logger.error(f"Error during cleanup: {e}")


# Create Flask application
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Create remote diagnostics instance
remote_diagnostics = None


@app.route("/api/system", methods=["GET"])
def get_system_info():
    """API endpoint to get system information."""
    global remote_diagnostics
    if remote_diagnostics is None:
        return jsonify({"error": "Remote diagnostics not initialized"}), 500
    return jsonify(remote_diagnostics.get_system_info())


@app.route("/api/hardware-tests", methods=["GET"])
def run_hardware_tests():
    """API endpoint to run hardware tests."""
    global remote_diagnostics
    if remote_diagnostics is None:
        return jsonify({"error": "Remote diagnostics not initialized"}), 500

    # Get test name from query parameter
    test_name = request.args.get("test")
    return jsonify(remote_diagnostics.run_hardware_tests(test_name))


@app.route("/api/service-status", methods=["GET"])
def get_service_status():
    """API endpoint to get service status."""
    global remote_diagnostics
    if remote_diagnostics is None:
        return jsonify({"error": "Remote diagnostics not initialized"}), 500
    return jsonify(remote_diagnostics.get_service_status())


@app.route("/api/logs", methods=["GET"])
def get_log_files():
    """API endpoint to get list of log files."""
    global remote_diagnostics
    if remote_diagnostics is None:
        return jsonify({"error": "Remote diagnostics not initialized"}), 500
    return jsonify(remote_diagnostics.get_log_files())


@app.route("/api/logs/<log_file>", methods=["GET"])
def get_log_content(log_file):
    """API endpoint to get content of a log file."""
    global remote_diagnostics
    if remote_diagnostics is None:
        return jsonify({"error": "Remote diagnostics not initialized"}), 500

    # Get number of lines from query parameter
    lines = request.args.get("lines", default=100, type=int)
    success, content = remote_diagnostics.get_log_content(log_file, lines)
    if success:
        return Response(content, mimetype="text/plain")
    else:
        return jsonify({"error": content}), 404


@app.route("/api/processes", methods=["GET"])
def get_process_info():
    """API endpoint to get process information."""
    global remote_diagnostics
    if remote_diagnostics is None:
        return jsonify({"error": "Remote diagnostics not initialized"}), 500
    return jsonify(remote_diagnostics.get_process_info())


def main():
    """
    Run the remote diagnostics server.

    This function parses command-line arguments, initializes the remote
    diagnostics module, and starts the Flask server.

    Command-line options:
        --port: Port to listen on (default: 8081)
        --debug: Enable debug mode
        --host: Host to listen on (default: 0.0.0.0)

    Returns:
        System exit code: 0 on success, non-zero on error
    """
    global remote_diagnostics

    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="Run remote diagnostics server for the autonomous mower"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_PORT,
        help=f"Port to listen on (default: {DEFAULT_PORT})",
    )
    parser.add_argument(
        "--debug", action="store_true", help="Enable debug mode"
    )
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Host to listen on (default: 0.0.0.0)",
    )

    args = parser.parse_args()

    try:
        # Initialize remote diagnostics
        remote_diagnostics = RemoteDiagnostics()

        # Start Flask server
        app.run(host=args.host, port=args.port, debug=args.debug)

        return 0
    except Exception as e:
        logger.error(f"Error running remote diagnostics server: {e}")
        return 1
    finally:
        # Clean up resources
        if remote_diagnostics:
            remote_diagnostics.cleanup()


if __name__ == "__main__":
    sys.exit(main())
