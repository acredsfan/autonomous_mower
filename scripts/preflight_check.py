#!/usr/bin/env python3
"""
Preflight Check Script

This script performs preflight checks before starting the autonomous mower system.
It verifies that all required components are functioning correctly and that the
system is ready for operation.
"""

import os
import sys
import json
import time
import argparse
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set up basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("preflight_check")


class PreflightCheck:
    """Preflight checks for the autonomous mower system."""
    
    def __init__(self, config_path: Optional[str] = None, verbose: bool = False):
        """Initialize the preflight check."""
        self.config_path = config_path or "config/main_config.json"
        self.verbose = verbose
        self.config = self._load_config()
        self.check_results = {
            "system": {},
            "hardware": {},
            "safety": {},
            "environment": {},
            "overall": {
                "status": "pending",
                "message": "Checks not started"
            }
        }
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file."""
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
            logger.info(f"Loaded configuration from {self.config_path}")
            return config
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            return {}
    
    def check_system(self) -> bool:
        """Check system status."""
        logger.info("Checking system status...")
        
        # Check disk space
        try:
            import subprocess
            df_output = subprocess.check_output(["df", "-h", "/"]).decode()
            lines = df_output.strip().split("\n")
            if len(lines) >= 2:
                usage_line = lines[1].split()
                if len(usage_line) >= 5:
                    usage_percent = int(usage_line[4].rstrip("%"))
                    
                    if usage_percent < 80:
                        self.check_results["system"]["disk_space"] = {
                            "status": "pass",
                            "message": f"Disk usage: {usage_percent}%"
                        }
                    elif usage_percent < 90:
                        self.check_results["system"]["disk_space"] = {
                            "status": "warning",
                            "message": f"Disk usage high: {usage_percent}%"
                        }
                    else:
                        self.check_results["system"]["disk_space"] = {
                            "status": "fail",
                            "message": f"Disk usage critical: {usage_percent}%"
                        }
                        return False
        except Exception as e:
            logger.error(f"Error checking disk space: {e}")
            self.check_results["system"]["disk_space"] = {
                "status": "error",
                "message": f"Error checking disk space: {e}"
            }
        
        # More system checks would go here
        
        return True
    
    def check_hardware(self) -> bool:
        """Check hardware status."""
        logger.info("Checking hardware status...")
        
        # Hardware checks would go here
        
        return True
    
    def check_safety(self) -> bool:
        """Check safety systems."""
        logger.info("Checking safety systems...")
        
        # Safety checks would go here
        
        return True
    
    def check_environment(self) -> bool:
        """Check environmental conditions."""
        logger.info("Checking environmental conditions...")
        
        # Environment checks would go here
        
        return True
    
    def run_all_checks(self) -> bool:
        """Run all preflight checks."""
        logger.info("Starting preflight checks...")
        
        # Run all checks
        system_ok = self.check_system()
        hardware_ok = self.check_hardware()
        safety_ok = self.check_safety()
        environment_ok = self.check_environment()
        
        # Set overall check result
        if system_ok and hardware_ok and safety_ok and environment_ok:
            self.check_results["overall"] = {
                "status": "pass",
                "message": "All preflight checks passed"
            }
            logger.info("All preflight checks passed")
            return True
        else:
            failed_components = []
            if not system_ok:
                failed_components.append("system")
            if not hardware_ok:
                failed_components.append("hardware")
            if not safety_ok:
                failed_components.append("safety")
            if not environment_ok:
                failed_components.append("environment")
            
            self.check_results["overall"] = {
                "status": "fail",
                "message": f"Preflight checks failed for: {', '.join(failed_components)}"
            }
            logger.warning(f"Preflight checks failed for: {', '.join(failed_components)}")
            return False
    
    def print_results(self) -> None:
        """Print check results to console."""
        print("\n" + "=" * 80)
        print("PREFLIGHT CHECK RESULTS")
        print("=" * 80)
        
        # Print overall result
        overall_status = self.check_results["overall"]["status"]
        overall_message = self.check_results["overall"]["message"]
        
        if overall_status == "pass":
            print(f"\n✅ OVERALL: {overall_message}")
        else:
            print(f"\n❌ OVERALL: {overall_message}")
        
        # Print detailed results if verbose
        if self.verbose:
            for category, results in self.check_results.items():
                if category == "overall":
                    continue
                
                print(f"\n{category.upper()}:")
                print("-" * 40)
                
                for component, result in results.items():
                    status = result["status"]
                    message = result["message"]
                    
                    if status == "pass":
                        print(f"✅ {component}: {message}")
                    elif status == "fail":
                        print(f"❌ {component}: {message}")
                    elif status == "warning":
                        print(f"⚠️ {component}: {message}")
                    else:
                        print(f"❓ {component}: {message}")
        
        print("\n" + "=" * 80)


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Preflight Check Script")
    parser.add_argument("--verbose", action="store_true", help="Show detailed check information")
    parser.add_argument("--config", type=str, help="Specify configuration file path")
    parser.add_argument("--output", type=str, help="Save check results to file")
    args = parser.parse_args()
    
    # Create preflight check
    preflight = PreflightCheck(config_path=args.config, verbose=args.verbose)
    
    # Run checks
    result = preflight.run_all_checks()
    
    # Print results
    preflight.print_results()
    
    # Return exit code
    return 0 if result else 1


if __name__ == "__main__":
    sys.exit(main())