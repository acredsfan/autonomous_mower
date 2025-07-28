#!/usr/bin/env python3
"""
Main CLI entry point for the autonomous mower system.
"""

import sys
import logging
from pathlib import Path
import click

# Add mower package to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from mower.config.settings import get_config
from mower.core.hal.hardware_manager import initialize_hardware, cleanup_hardware
from mower.core.safety.safety_system import initialize_safety, shutdown_safety


logger = logging.getLogger(__name__)


@click.group()
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
@click.option('--config', '-c', type=click.Path(exists=True), help='Configuration file path')
@click.pass_context
def cli(ctx, verbose, config):
    """Autonomous Mower System CLI."""
    # Configure logging
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Store configuration path in context
    ctx.ensure_object(dict)
    ctx.obj['config_path'] = config
    ctx.obj['verbose'] = verbose


@cli.command()
@click.option('--simulation', is_flag=True, help='Run in simulation mode')
@click.pass_context
def start(ctx, simulation):
    """Start the mower system."""
    try:
        config = get_config()
        if simulation:
            config.simulation_mode = True
        
        logger.info("Starting autonomous mower system...")
        logger.info(f"Simulation mode: {config.simulation_mode}")
        
        # Initialize hardware
        if not initialize_hardware(config, config.simulation_mode):
            logger.error("Failed to initialize hardware")
            sys.exit(1)
        
        # Initialize safety system
        if not initialize_safety(config):
            logger.error("Failed to initialize safety system")
            cleanup_hardware()
            sys.exit(1)
        
        logger.info("✓ System started successfully")
        logger.info("Press Ctrl+C to stop")
        
        # Keep running until interrupted
        try:
            import time
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        
    except Exception as e:
        logger.error(f"Failed to start system: {e}")
        sys.exit(1)
    finally:
        logger.info("Shutting down system...")
        shutdown_safety()
        cleanup_hardware()
        logger.info("System shutdown complete")


@cli.command()
@click.pass_context
def stop(ctx):
    """Stop the mower system."""
    try:
        import subprocess
        result = subprocess.run(
            ["sudo", "systemctl", "stop", "autonomous-mower"],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            logger.info("✓ System stopped")
        else:
            logger.error(f"Failed to stop system: {result.stderr}")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Error stopping system: {e}")
        sys.exit(1)


@cli.command()
@click.pass_context
def status(ctx):
    """Show system status."""
    try:
        config = get_config()
        
        # Check hardware status
        from mower.core.hal.hardware_manager import get_hardware_manager
        hw_manager = get_hardware_manager(config, config.simulation_mode)
        hw_manager.initialize_all()
        
        hw_status = hw_manager.get_system_status()
        
        click.echo("=== Autonomous Mower System Status ===")
        click.echo(f"Simulation Mode: {hw_status['simulation']}")
        click.echo(f"System Healthy: {hw_status['healthy']}")
        click.echo()
        
        click.echo("Component Status:")
        for name, status in hw_status['components'].items():
            status_icon = "✓" if status['healthy'] else "✗"
            click.echo(f"  {status_icon} {name}: {'Healthy' if status['healthy'] else 'Unhealthy'}")
        
        # Check safety status
        from mower.core.safety.safety_system import get_safety_system
        safety_system = get_safety_system(config)
        safety_system.initialize()
        
        safety_status = safety_system.get_status()
        
        click.echo()
        click.echo("Safety Status:")
        click.echo(f"  State: {safety_status['safety_state']}")
        click.echo(f"  Emergency Stop: {'Active' if safety_status['emergency_stop_active'] else 'Inactive'}")
        click.echo(f"  Safe to Operate: {safety_status['safe_to_operate']}")
        
        # Cleanup
        hw_manager.cleanup_all()
        safety_system.shutdown()
        
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        sys.exit(1)


@cli.command()
@click.option('--steering', type=int, default=0, help='Steering value (-100 to 100)')
@click.option('--throttle', type=int, default=0, help='Throttle value (-100 to 100)')
@click.option('--blade', type=int, default=0, help='Blade speed (0 to 100)')
@click.option('--duration', type=float, default=1.0, help='Command duration in seconds')
@click.pass_context
def test_motors(ctx, steering, throttle, blade, duration):
    """Test motor control."""
    try:
        config = get_config()
        config.simulation_mode = True  # Force simulation for safety
        
        logger.info("Testing motor control (simulation mode)...")
        
        # Initialize hardware
        from mower.core.hal.hardware_manager import get_hardware_manager
        hw_manager = get_hardware_manager(config, True)
        hw_manager.initialize_all()
        
        # Initialize safety
        from mower.core.safety.safety_system import get_safety_system
        safety_system = get_safety_system(config)
        safety_system.initialize()
        
        if not safety_system.is_safe_to_operate():
            logger.error("System not safe to operate")
            sys.exit(1)
        
        # Send motor command
        with hw_manager.safe_operation():
            success = hw_manager.motor_controller.set_motors(steering, throttle, blade)
            
            if success:
                logger.info(f"Motor command sent: steering={steering}, throttle={throttle}, blade={blade}")
                
                import time
                time.sleep(duration)
                
                # Stop motors
                hw_manager.motor_controller.stop_all_motors()
                logger.info("Motors stopped")
            else:
                logger.error("Failed to send motor command")
        
        # Cleanup
        hw_manager.cleanup_all()
        safety_system.shutdown()
        
    except Exception as e:
        logger.error(f"Motor test failed: {e}")
        sys.exit(1)


@cli.command()
@click.pass_context
def emergency_stop(ctx):
    """Trigger emergency stop."""
    try:
        config = get_config()
        
        from mower.core.safety.safety_system import get_safety_system
        safety_system = get_safety_system(config)
        safety_system.initialize()
        
        safety_system.emergency_stop("Manual emergency stop from CLI")
        logger.info("✓ Emergency stop triggered")
        
        safety_system.shutdown()
        
    except Exception as e:
        logger.error(f"Failed to trigger emergency stop: {e}")
        sys.exit(1)


@cli.command()
@click.pass_context
def clear_emergency(ctx):
    """Clear emergency stop."""
    try:
        config = get_config()
        
        from mower.core.safety.safety_system import get_safety_system
        safety_system = get_safety_system(config)
        safety_system.initialize()
        
        if safety_system.clear_emergency_stop():
            logger.info("✓ Emergency stop cleared")
        else:
            logger.warning("Could not clear emergency stop (hardware may still be active)")
        
        safety_system.shutdown()
        
    except Exception as e:
        logger.error(f"Failed to clear emergency stop: {e}")
        sys.exit(1)


def main():
    """Main entry point."""
    cli()


if __name__ == "__main__":
    main()
