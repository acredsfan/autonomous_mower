#!/usr/bin/env python3
"""
System Launcher

This script launches all microservices for the autonomous mower system
in the correct order with proper dependency management.
"""

import asyncio
import logging
import signal
import sys
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from pathlib import Path
import subprocess
import click

# Add mower package to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from mower.config.settings import get_config


logger = logging.getLogger(__name__)


@dataclass
class ServiceConfig:
    """Service configuration."""
    name: str
    module: str
    priority: int  # Lower numbers start first
    required: bool = True
    restart_on_failure: bool = True


class ServiceManager:
    """Manages multiple microservices."""
    
    def __init__(self):
        """Initialize service manager."""
        self.config = get_config()
        self.processes: Dict[str, subprocess.Popen] = {}
        self.running = False
        self.shutdown_event = asyncio.Event()
        
        # Define services in startup order
        self.services = [
            ServiceConfig("motor_control", "mower.services.motor.motor_service", 1, True),
            ServiceConfig("sensor", "mower.services.sensor.sensor_service", 2, True),
            ServiceConfig("vision", "mower.services.vision.vision_service", 3, False),
            ServiceConfig("navigation", "mower.services.navigation.navigation_service", 4, True),
            ServiceConfig("mission_controller", "mower.coordination.mission_controller", 5, True),
            ServiceConfig("web", "mower.interfaces.web.modern_web_interface", 6, False),
        ]
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, initiating shutdown")
        self.shutdown_event.set()
    
    async def start_all_services(self) -> bool:
        """Start all services in order."""
        logger.info("Starting autonomous mower services...")
        
        # Sort services by priority
        sorted_services = sorted(self.services, key=lambda s: s.priority)
        
        for service in sorted_services:
            if not await self._start_service(service):
                if service.required:
                    logger.error(f"Failed to start required service {service.name}")
                    await self._stop_all_services()
                    return False
                else:
                    logger.warning(f"Optional service {service.name} failed to start")
            
            # Wait a bit between service starts
            await asyncio.sleep(2)
        
        logger.info("All services started successfully")
        self.running = True
        return True
    
    async def _start_service(self, service: ServiceConfig) -> bool:
        """Start a single service."""
        logger.info(f"Starting {service.name} service...")
        
        try:
            # Start service process
            cmd = [sys.executable, "-m", service.module]
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env={**dict(subprocess.os.environ), "PYTHONPATH": str(Path.cwd())}
            )
            
            # Give service time to start
            await asyncio.sleep(1)
            
            # Check if process is still running
            if process.poll() is None:
                self.processes[service.name] = process
                logger.info(f"✓ {service.name} service started (PID: {process.pid})")
                return True
            else:
                # Process died immediately
                stdout, stderr = process.communicate()
                logger.error(f"✗ {service.name} service failed to start")
                logger.error(f"STDOUT: {stdout.decode()}")
                logger.error(f"STDERR: {stderr.decode()}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to start {service.name}: {e}")
            return False
    
    async def monitor_services(self) -> None:
        """Monitor services and restart if needed."""
        while self.running and not self.shutdown_event.is_set():
            for service in self.services:
                if service.name in self.processes:
                    process = self.processes[service.name]
                    
                    # Check if process is still running
                    if process.poll() is not None:
                        logger.warning(f"Service {service.name} has stopped")
                        
                        if service.restart_on_failure and self.running:
                            logger.info(f"Restarting {service.name}...")
                            del self.processes[service.name]
                            await self._start_service(service)
                        else:
                            logger.info(f"Not restarting {service.name}")
            
            # Wait before next check
            try:
                await asyncio.wait_for(self.shutdown_event.wait(), timeout=5.0)
                break  # Shutdown requested
            except asyncio.TimeoutError:
                continue  # Continue monitoring
    
    async def _stop_all_services(self) -> None:
        """Stop all services gracefully."""
        logger.info("Stopping all services...")
        
        # Stop services in reverse order
        sorted_services = sorted(self.services, key=lambda s: s.priority, reverse=True)
        
        for service in sorted_services:
            if service.name in self.processes:
                await self._stop_service(service.name)
        
        logger.info("All services stopped")
    
    async def _stop_service(self, service_name: str) -> None:
        """Stop a single service gracefully."""
        if service_name not in self.processes:
            return
        
        process = self.processes[service_name]
        logger.info(f"Stopping {service_name} service...")
        
        try:
            # Send SIGTERM
            process.terminate()
            
            # Wait for graceful shutdown
            try:
                await asyncio.wait_for(
                    asyncio.create_task(self._wait_for_process(process)),
                    timeout=10.0
                )
                logger.info(f"✓ {service_name} stopped gracefully")
            except asyncio.TimeoutError:
                # Force kill if not responsive
                logger.warning(f"Force killing {service_name}")
                process.kill()
                await self._wait_for_process(process)
            
            del self.processes[service_name]
            
        except Exception as e:
            logger.error(f"Error stopping {service_name}: {e}")
    
    async def _wait_for_process(self, process: subprocess.Popen) -> None:
        """Wait for process to terminate."""
        while process.poll() is None:
            await asyncio.sleep(0.1)
    
    async def run(self) -> None:
        """Run the service manager."""
        try:
            # Start all services
            if not await self.start_all_services():
                logger.error("Failed to start services")
                return
            
            # Monitor services
            await self.monitor_services()
            
        except Exception as e:
            logger.error(f"Service manager error: {e}")
        finally:
            # Cleanup
            self.running = False
            await self._stop_all_services()
    
    def get_status(self) -> Dict[str, Any]:
        """Get status of all services."""
        status = {
            "running": self.running,
            "services": {}
        }
        
        for service in self.services:
            if service.name in self.processes:
                process = self.processes[service.name]
                status["services"][service.name] = {
                    "running": process.poll() is None,
                    "pid": process.pid,
                    "required": service.required
                }
            else:
                status["services"][service.name] = {
                    "running": False,
                    "pid": None,
                    "required": service.required
                }
        
        return status


@click.group()
def cli():
    """Autonomous Mower System Launcher."""
    pass


@cli.command()
@click.option('--log-level', default='INFO', help='Logging level')
@click.option('--simulation', is_flag=True, help='Run in simulation mode')
def start(log_level: str, simulation: bool):
    """Start all microservices."""
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger.info("🚜 Starting Autonomous Mower System")
    
    # Set simulation mode if requested
    if simulation:
        config = get_config()
        config.simulation_mode = True
        logger.info("Running in simulation mode")
    
    # Run service manager
    manager = ServiceManager()
    
    try:
        asyncio.run(manager.run())
    except KeyboardInterrupt:
        logger.info("Shutdown requested by user")
    except Exception as e:
        logger.error(f"System error: {e}")
        sys.exit(1)


@cli.command()
@click.argument('service_name')
def start_service(service_name: str):
    """Start a specific service."""
    
    logging.basicConfig(level=logging.INFO)
    
    manager = ServiceManager()
    service = next((s for s in manager.services if s.name == service_name), None)
    
    if not service:
        logger.error(f"Unknown service: {service_name}")
        sys.exit(1)
    
    async def run_single():
        await manager._start_service(service)
        await manager.shutdown_event.wait()
        await manager._stop_service(service_name)
    
    try:
        asyncio.run(run_single())
    except KeyboardInterrupt:
        logger.info(f"{service_name} stopped by user")


@cli.command()
def status():
    """Show status of all services."""
    
    # This would check service status via Redis or process monitoring
    logger.info("Service status checking not implemented in launcher")
    logger.info("Use 'mower status' command instead")


@cli.command()
def stop():
    """Stop all services."""
    
    logger.info("Stopping services via system signals...")
    
    # Send SIGTERM to all mower processes
    try:
        subprocess.run(["pkill", "-TERM", "-f", "mower.services"], check=False)
        subprocess.run(["pkill", "-TERM", "-f", "mower.coordination"], check=False)
        subprocess.run(["pkill", "-TERM", "-f", "mower.interfaces"], check=False)
        
        time.sleep(2)
        
        # Force kill if still running
        subprocess.run(["pkill", "-KILL", "-f", "mower.services"], check=False)
        subprocess.run(["pkill", "-KILL", "-f", "mower.coordination"], check=False)
        subprocess.run(["pkill", "-KILL", "-f", "mower.interfaces"], check=False)
        
        logger.info("Services stopped")
        
    except Exception as e:
        logger.error(f"Error stopping services: {e}")


def main():
    """Main entry point."""
    cli()


if __name__ == "__main__":
    main()
