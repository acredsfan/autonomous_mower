#!/usr/bin/env python3
"""
Test runner for the autonomous mower system.
"""

import sys
import logging
import subprocess
from pathlib import Path
import click

logger = logging.getLogger(__name__)


@click.command()
@click.option('--unit', is_flag=True, help='Run unit tests only')
@click.option('--integration', is_flag=True, help='Run integration tests only')
@click.option('--hardware', is_flag=True, help='Run hardware tests (requires actual hardware)')
@click.option('--coverage', is_flag=True, help='Generate coverage report')
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
@click.option('--fast', is_flag=True, help='Skip slow tests')
def main(unit, integration, hardware, coverage, verbose, fast):
    """Run tests for the autonomous mower system."""
    
    # Configure logging
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format='%(levelname)s: %(message)s')
    
    base_path = Path(__file__).parent.parent.parent
    
    # Build pytest command
    cmd = [sys.executable, "-m", "pytest"]
    
    # Add test directories based on options
    if unit:
        cmd.append("mower/tests/unit")
    elif integration:
        cmd.append("mower/tests/integration")
    elif hardware:
        cmd.append("mower/tests/hardware")
    else:
        cmd.append("mower/tests")
    
    # Add pytest options
    if verbose:
        cmd.append("-v")
    
    if coverage:
        cmd.extend(["--cov=mower", "--cov-report=html", "--cov-report=term"])
    
    if fast:
        cmd.extend(["-m", "not slow"])
    
    # Add markers for hardware tests
    if not hardware:
        cmd.extend(["-m", "not hardware"])
    
    try:
        logger.info("Running autonomous mower tests...")
        logger.info(f"Command: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, cwd=base_path)
        
        if result.returncode == 0:
            logger.info("✓ All tests passed!")
            if coverage:
                logger.info("Coverage report generated in htmlcov/")
        else:
            logger.error("✗ Some tests failed")
            sys.exit(result.returncode)
            
    except KeyboardInterrupt:
        logger.info("Tests cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error running tests: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
