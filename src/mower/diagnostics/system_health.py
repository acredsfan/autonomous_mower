#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
System health monitoring and self-diagnostics for the autonomous mower.

This module provides functionality to monitor the health of the mower's hardware
and software components, detect issues, and provide diagnostic information. It
helps users identify and resolve problems with the mower.

Key features:
- Monitor CPU, memory, disk, and network usage
- Check hardware component status
- Monitor battery health and charging status
- Detect software issues and service failures
- Generate health reports
- Trigger alerts for critical issues
- Provide recommendations for resolving issues

Example usage:
    # Run a full system health check
    python -m mower.diagnostics.system_health --full

    # Check specific components
    python -m mower.diagnostics.system_health --check hardware

    # Monitor system health continuously
    python -m mower.diagnostics.system_health --monitor
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import psutil

# Import hardware test suite
from mower.diagnostics.hardware_test import initialize_resource_manager
from mower.utilities.logger_config import LoggerConfigInfo

# Configure logging
logger = LoggerConfigInfo.get_logger(__name__)

# Constants
HEALTH_CHECK_INTERVAL = 300  # 5 minutes
CRITICAL_CPU_THRESHOLD = 90  # percentage
CRITICAL_MEMORY_THRESHOLD = 90  # percentage
CRITICAL_DISK_THRESHOLD = 90  # percentage
CRITICAL_TEMPERATURE_THRESHOLD = 80  # Celsius
LOW_BATTERY_THRESHOLD = 20  # percentage
HEALTH_REPORT_DIR = "/var/log/autonomous-mower/health"
MAX_HEALTH_REPORTS = 50  # Maximum number of health reports to keep


class SystemHealth:
    """
    System health monitoring and self-diagnostics for the autonomous mower.

    This class provides methods to monitor the health of the mower's hardware
    and software components, detect issues, and provide diagnostic information.
    """

    def __init__(self):
        """Initialize the system health monitor."""
        self.resource_manager = initialize_resource_manager()
        if self.resource_manager is None:
            logger.error("Failed to initialize ResourceManager")
            raise RuntimeError("Failed to initialize ResourceManager")

        # Create health report directory
        os.makedirs(HEALTH_REPORT_DIR, exist_ok=True)

        # Initialize health status
        self.health_status = {
            "timestamp": datetime.now().isoformat(),
            "system": self._check_system_health(),
            "hardware": {},
            "software": {},
            "issues": [],
            "recommendations": [],
        }

    def _check_system_health(self) -> Dict[str, Any]:
        """
        Check system health (CPU, memory, disk, temperature).

        Returns:
            Dict[str, Any]: System health information.
        """
        try:
            # Get CPU information
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_temp = self._get_cpu_temperature()
            cpu_freq = psutil.cpu_freq()
            cpu_freq_current = cpu_freq.current if cpu_freq else None

            # Get memory information
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_available_mb = memory.available / (1024 * 1024)

            # Get disk information
            disk = psutil.disk_usage("/")
            disk_percent = disk.percent
            disk_free_gb = disk.free / (1024 * 1024 * 1024)

            # Get uptime
            uptime_seconds = time.time() - psutil.boot_time()
            uptime_days = uptime_seconds / (60 * 60 * 24)

            # Check for issues
            issues = []
            if cpu_percent > CRITICAL_CPU_THRESHOLD:
                issues.append(f"Critical CPU usage: {cpu_percent}%")
            if memory_percent > CRITICAL_MEMORY_THRESHOLD:
                issues.append(f"Critical memory usage: {memory_percent}%")
            if disk_percent > CRITICAL_DISK_THRESHOLD:
                issues.append(f"Critical disk usage: {disk_percent}%")
            if cpu_temp is not None and cpu_temp > CRITICAL_TEMPERATURE_THRESHOLD:
                issues.append(f"Critical CPU temperature: {cpu_temp}°C")

            # Create system health report
            system_health = {
                "cpu": {
                    "usage_percent": cpu_percent,
                    "temperature": cpu_temp,
                    "frequency_mhz": cpu_freq_current,
                    "status": (
                        "critical"
                        if cpu_percent > CRITICAL_CPU_THRESHOLD
                        else "warning" if cpu_percent > 70 else "ok"
                    ),
                },
                "memory": {
                    "usage_percent": memory_percent,
                    "available_mb": memory_available_mb,
                    "status": (
                        "critical"
                        if memory_percent > CRITICAL_MEMORY_THRESHOLD
                        else "warning" if memory_percent > 70 else "ok"
                    ),
                },
                "disk": {
                    "usage_percent": disk_percent,
                    "free_gb": disk_free_gb,
                    "status": (
                        "critical"
                        if disk_percent > CRITICAL_DISK_THRESHOLD
                        else "warning" if disk_percent > 70 else "ok"
                    ),
                },
                "uptime": {
                    "seconds": uptime_seconds,
                    "days": uptime_days,
                },
                "issues": issues,
            }

            # Add overall status
            if any(issue.startswith("Critical") for issue in issues):
                system_health["status"] = "critical"
            elif issues:
                system_health["status"] = "warning"
            else:
                system_health["status"] = "ok"

            return system_health
        except Exception as e:
            logger.error(f"Error checking system health: {e}")
            return {
                "status": "error",
                "error": str(e),
            }

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

    def check_hardware_health(self) -> Dict[str, Any]:
        """
        Check hardware component health.

        Returns:
            Dict[str, Any]: Hardware health information.
        """
        try:
            hardware_health = {}
            issues = []

            # Check IMU
            try:
                imu = self.resource_manager.get_imu_sensor()
                if imu and imu.read():
                    hardware_health["imu"] = {"status": "ok"}
                else:
                    hardware_health["imu"] = {
                        "status": "error",
                        "error": "IMU not available or not returning data",
                    }
                    issues.append("IMU sensor not available or not returning data")
            except Exception as e:
                hardware_health["imu"] = {"status": "error", "error": str(e)}
                issues.append(f"IMU sensor error: {str(e)}")

            # Check GPS
            try:
                gps = self.resource_manager.get_gps()
                if gps and gps.get_position():
                    hardware_health["gps"] = {"status": "ok"}
                else:
                    hardware_health["gps"] = {
                        "status": "warning",
                        "error": "GPS not available or no fix",
                    }
                    issues.append("GPS not available or not getting a fix")
            except Exception as e:
                hardware_health["gps"] = {"status": "error", "error": str(e)}
                issues.append(f"GPS error: {str(e)}")

            # Check battery
            try:
                power_monitor = self.resource_manager.get_power_monitor()
                if power_monitor:
                    battery_percent = power_monitor.get_battery_percentage()
                    status = "ok"
                    if battery_percent < LOW_BATTERY_THRESHOLD:
                        status = "critical"
                        issues.append(f"Low battery: {battery_percent}%")
                    elif battery_percent < 30:
                        status = "warning"
                        issues.append(f"Battery level low: {battery_percent}%")

                    hardware_health["battery"] = {
                        "status": status,
                        "percent": battery_percent,
                    }
                else:
                    hardware_health["battery"] = {
                        "status": "error",
                        "error": "Battery monitor not available",
                    }
                    issues.append("Battery monitor not available")
            except Exception as e:
                hardware_health["battery"] = {
                    "status": "error",
                    "error": str(e),
                }
                issues.append(f"Battery monitor error: {str(e)}")

            # Check motors and other components
            for component, getter in [
                ("motors", "get_motor_controller"),
                ("blade", "get_blade_controller"),
                ("camera", "get_camera"),
            ]:
                try:
                    if hasattr(self.resource_manager, getter):
                        controller = getattr(self.resource_manager, getter)()
                        if controller:
                            hardware_health[component] = {"status": "ok"}
                        else:
                            hardware_health[component] = {
                                "status": "error",
                                "error": f"{component} controller not available",
                            }
                            issues.append(f"{component} controller not available")
                except Exception as e:
                    hardware_health[component] = {
                        "status": "error",
                        "error": str(e),
                    }
                    issues.append(f"{component} error: {str(e)}")

            # Add overall status
            if any(
                component.get("status") == "critical"
                for component in hardware_health.values()
            ):
                hardware_health["status"] = "critical"
            elif any(
                component.get("status") == "error"
                for component in hardware_health.values()
            ):
                hardware_health["status"] = "error"
            elif any(
                component.get("status") == "warning"
                for component in hardware_health.values()
            ):
                hardware_health["status"] = "warning"
            else:
                hardware_health["status"] = "ok"

            # Update health status
            self.health_status["hardware"] = hardware_health
            self.health_status["issues"].extend(issues)

            return hardware_health
        except Exception as e:
            logger.error(f"Error checking hardware health: {e}")
            return {"status": "error", "error": str(e)}

    def check_software_health(self) -> Dict[str, Any]:
        """
        Check software component health.

        Returns:
            Dict[str, Any]: Software health information.
        """
        try:
            software_health = {}
            issues = []

            # Check mower service status
            try:
                result = subprocess.run(
                    ["systemctl", "is-active", "autonomous-mower.service"],
                    capture_output=True,
                    text=True,
                )
                service_active = result.stdout.strip() == "active"

                if service_active:
                    software_health["mower_service"] = {
                        "status": "ok",
                        "active": True,
                    }
                else:
                    software_health["mower_service"] = {
                        "status": "critical",
                        "active": False,
                        "error": "Service not running",
                    }
                    issues.append("Mower service not running")
            except Exception as e:
                software_health["mower_service"] = {
                    "status": "error",
                    "error": str(e),
                }
                issues.append(f"Error checking mower service: {str(e)}")

            # Check for recent crashes in logs
            try:
                log_dir = Path("/var/log/autonomous-mower")
                if log_dir.exists():
                    error_count = 0
                    crash_count = 0

                    # Check error log
                    error_log = log_dir / "error.log"
                    if error_log.exists():
                        # Count errors in the last 24 hours
                        yesterday = datetime.now() - timedelta(days=1)
                        yesterday_str = yesterday.strftime("%Y-%m-%d")

                        with open(error_log, "r") as f:
                            for line in f:
                                if yesterday_str in line and (
                                    "ERROR" in line or "CRITICAL" in line
                                ):
                                    error_count += 1
                                if "Traceback" in line or "Exception" in line:
                                    crash_count += 1

                    if crash_count > 0:
                        software_health["logs"] = {
                            "status": "critical",
                            "error_count": error_count,
                            "crash_count": crash_count,
                            "error": f"Found {crash_count} crashes in logs",
                        }
                        issues.append(f"Found {crash_count} crashes in logs")
                    elif error_count > 10:
                        software_health["logs"] = {
                            "status": "warning",
                            "error_count": error_count,
                            "crash_count": crash_count,
                            "error": f"High number of errors: {error_count}",
                        }
                        issues.append(f"High number of errors in logs: {error_count}")
                    else:
                        software_health["logs"] = {
                            "status": "ok",
                            "error_count": error_count,
                            "crash_count": crash_count,
                        }
                else:
                    software_health["logs"] = {
                        "status": "warning",
                        "error": "Log directory not found",
                    }
                    issues.append("Log directory not found")
            except Exception as e:
                software_health["logs"] = {"status": "error", "error": str(e)}
                issues.append(f"Error checking logs: {str(e)}")

            # Add overall status
            if any(
                component.get("status") == "critical"
                for component in software_health.values()
            ):
                software_health["status"] = "critical"
            elif any(
                component.get("status") == "error"
                for component in software_health.values()
            ):
                software_health["status"] = "error"
            elif any(
                component.get("status") == "warning"
                for component in software_health.values()
            ):
                software_health["status"] = "warning"
            else:
                software_health["status"] = "ok"

            # Update health status
            self.health_status["software"] = software_health
            self.health_status["issues"].extend(issues)

            return software_health
        except Exception as e:
            logger.error(f"Error checking software health: {e}")
            return {"status": "error", "error": str(e)}

    def generate_recommendations(self) -> List[str]:
        """
        Generate recommendations based on detected issues.

        Returns:
            List[str]: List of recommendations.
        """
        recommendations = []
        issues = self.health_status["issues"]  # System recommendations
        if any("Critical CPU usage" in issue for issue in issues):
            recommendations.append(
                "Reduce CPU load by disabling non-essential services or "
                "reducing sensor polling frequency"
            )
        if any("Critical memory usage" in issue for issue in issues):
            recommendations.append(
                "Free up memory by restarting the mower service or the entire system"
            )
        if any("Critical disk usage" in issue for issue in issues):
            recommendations.append(
                "Free up disk space by removing old logs or unnecessary files"
            )
        if any("Critical CPU temperature" in issue for issue in issues):
            recommendations.append(
                "Improve cooling or reduce CPU load to lower temperature"
            )

        # Hardware recommendations
        if any("IMU sensor" in issue for issue in issues):
            recommendations.append("Check IMU sensor connections and configuration")
        if any("GPS not" in issue for issue in issues):
            recommendations.append(
                "Move to an area with better GPS reception or check GPS antenna"
            )
        if any("Low battery" in issue for issue in issues):
            recommendations.append("Charge the mower battery immediately")
        if any("Battery level low" in issue for issue in issues):
            recommendations.append("Consider charging the mower soon")
        if any("Motor controller" in issue for issue in issues):
            recommendations.append(
                "Check motor controller connections and configuration"
            )
        if any("Blade controller" in issue for issue in issues):
            recommendations.append(
                "Check blade controller connections and configuration"
            )
        if any("Camera" in issue for issue in issues):
            recommendations.append(
                "Check camera connections and configuration"
            )  # Software recommendations
        if any("Mower service not running" in issue for issue in issues):
            recommendations.append(
                "Start the mower service with: "
                "sudo systemctl start autonomous-mower.service"
            )
        if any("crashes in logs" in issue for issue in issues):
            recommendations.append(
                "Check error logs for crash details and consider updating software"
            )
        if any("High number of errors" in issue for issue in issues):
            recommendations.append(
                "Review error logs to identify and fix recurring issues"
            )

        # Update health status
        self.health_status["recommendations"] = recommendations

        return recommendations

    def run_full_health_check(self) -> Dict[str, Any]:
        """
        Run a full health check on all components.

        Returns:
            Dict[str, Any]: Complete health status report.
        """
        # Reset health status
        self.health_status = {
            "timestamp": datetime.now().isoformat(),
            "system": self._check_system_health(),
            "hardware": {},
            "software": {},
            "issues": [],
            "recommendations": [],
        }

        # Check hardware health
        self.check_hardware_health()

        # Check software health
        self.check_software_health()

        # Generate recommendations
        self.generate_recommendations()

        # Determine overall status
        if (
            self.health_status["system"].get("status") == "critical"
            or self.health_status["hardware"].get("status") == "critical"
            or self.health_status["software"].get("status") == "critical"
        ):
            self.health_status["status"] = "critical"
        elif (
            self.health_status["system"].get("status") == "error"
            or self.health_status["hardware"].get("status") == "error"
            or self.health_status["software"].get("status") == "error"
        ):
            self.health_status["status"] = "error"
        elif (
            self.health_status["system"].get("status") == "warning"
            or self.health_status["hardware"].get("status") == "warning"
            or self.health_status["software"].get("status") == "warning"
        ):
            self.health_status["status"] = "warning"
        else:
            self.health_status["status"] = "ok"

        # Save health report
        self._save_health_report()

        return self.health_status

    def _save_health_report(self) -> None:
        """Save the current health report to a file."""
        try:
            # Create a filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"health_report_{timestamp}.json"
            filepath = os.path.join(HEALTH_REPORT_DIR, filename)

            # Save the report
            with open(filepath, "w") as f:
                json.dump(self.health_status, f, indent=2)

            logger.info(f"Health report saved to {filepath}")

            # Clean up old reports
            self._cleanup_old_reports()
        except Exception as e:
            logger.error(f"Error saving health report: {e}")

    def _cleanup_old_reports(self) -> None:
        """Remove old health reports to stay within the maximum limit."""
        try:
            # List all health reports
            reports = []
            for filename in os.listdir(HEALTH_REPORT_DIR):
                if filename.startswith("health_report_") and filename.endswith(".json"):
                    filepath = os.path.join(HEALTH_REPORT_DIR, filename)
                    reports.append((filepath, os.path.getmtime(filepath)))

            # Sort by modification time (newest first)
            reports.sort(key=lambda x: x[1], reverse=True)

            # Remove oldest reports
            if len(reports) > MAX_HEALTH_REPORTS:
                for filepath, _ in reports[MAX_HEALTH_REPORTS:]:
                    os.remove(filepath)
                    logger.info(f"Removed old health report: {filepath}")
        except Exception as e:
            logger.error(f"Error cleaning up old health reports: {e}")

    def monitor_health(
        self, interval: int = HEALTH_CHECK_INTERVAL, callback=None
    ) -> None:
        """
        Monitor system health continuously.

        Args:
            interval: Time between health checks in seconds.
            callback: Function to call with health status after each check.
        """
        try:
            logger.info(f"Starting health monitoring with interval {interval} seconds")
            while True:
                # Run a full health check
                health_status = self.run_full_health_check()

                # Call the callback function if provided
                if callback:
                    callback(health_status)

                # Log critical issues
                if health_status["status"] == "critical":
                    logger.critical(
                        f"Critical health issues detected: {health_status['issues']}"
                    )
                elif health_status["status"] == "error":
                    logger.error(f"Health errors detected: {health_status['issues']}")
                elif health_status["status"] == "warning":
                    logger.warning(
                        f"Health warnings detected: {health_status['issues']}"
                    )
                else:
                    logger.info("System health is OK")

                # Wait for the next check
                time.sleep(interval)
        except KeyboardInterrupt:
            logger.info("Health monitoring stopped by user")
        except Exception as e:
            logger.error(f"Error in health monitoring: {e}")


def main():
    """
    Run the system health monitor from the command line.

    This function parses command-line arguments and runs the system health
    monitor accordingly.

    Command-line options:
        --full: Run a full health check
        --check: Check specific components (system, hardware, software)
        --monitor: Monitor system health continuously
        --interval: Time between health checks in seconds (default: 300)
        --output: Output format (text, json)

    Returns:
        System exit code: 0 on success, non-zero on error
    """
    parser = argparse.ArgumentParser(
        description="System health monitoring for the autonomous mower"
    )

    # Create a mutually exclusive group for the main actions
    action_group = parser.add_mutually_exclusive_group(required=True)
    action_group.add_argument(
        "--full",
        action="store_true",
        help="Run a full health check",
    )
    action_group.add_argument(
        "--check",
        choices=["system", "hardware", "software"],
        help="Check specific components",
    )
    action_group.add_argument(
        "--monitor",
        action="store_true",
        help="Monitor system health continuously",
    )

    # Additional options
    parser.add_argument(
        "--interval",
        type=int,
        default=HEALTH_CHECK_INTERVAL,
        help=(
            f"Time between health checks in seconds (default: "
            f"{HEALTH_CHECK_INTERVAL})"
        ),
    )
    parser.add_argument(
        "--output",
        choices=["text", "json"],
        default="text",
        help=("Output format (default: text)"),
    )

    args = parser.parse_args()

    try:
        # Initialize the system health monitor
        health_monitor = SystemHealth()

        # Process the command
        if args.full:
            # Run a full health check
            health_status = health_monitor.run_full_health_check()

            # Output the results
            if args.output == "json":
                print(json.dumps(health_status, indent=2))
            else:
                print("\n" + "=" * 80)
                print(
                    f"AUTONOMOUS MOWER HEALTH REPORT - "
                    f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                )
                print(
                    f"Overall Status: {health_status.get('status', 'unknown').upper()}"
                )
                print("\nIssues:")
                for issue in health_status.get("issues", []):
                    print(f"  - {issue}")
                print("\nRecommendations:")
                for recommendation in health_status.get("recommendations", []):
                    print(f"  - {recommendation}")
                print("=" * 80)

            return 0

        elif args.check:
            # Check specific components
            if args.check == "system":
                result = health_monitor._check_system_health()
            elif args.check == "hardware":
                result = health_monitor.check_hardware_health()
            elif args.check == "software":
                result = health_monitor.check_software_health()

            # Output the results
            if args.output == "json":
                print(json.dumps(result, indent=2))
            else:
                print("\n" + "=" * 80)
                print(
                    (
                        f"AUTONOMOUS MOWER {args.check.upper()} HEALTH"
                        f" CHECK - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    )
                )
                print("=" * 80)
                print(f"Status: {result.get('status', 'unknown').upper()}")
                if "issues" in result:
                    print("\nIssues:")
                    for issue in result["issues"]:
                        print(f"  - {issue}")
                print("=" * 80)

            return 0

        elif args.monitor:
            # Monitor system health continuously
            health_monitor.monitor_health(interval=args.interval)
            return 0

    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
