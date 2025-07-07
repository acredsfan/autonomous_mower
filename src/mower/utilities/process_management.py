"""
Process management utilities for the autonomous mower service.

This module provides functions to manage process lifecycle, detect port conflicts,
and ensure clean startup/shutdown of multiprocess applications.

@author: GitHub Copilot
@hardware_interface: None (utility functions only)
"""

import socket
import psutil
import os
import signal
import logging
import time
from typing import List, Tuple, Optional


# Initialize logger
logger = logging.getLogger(__name__)


def is_port_available(port: int, host: str = 'localhost') -> bool:
    """
    Check if a TCP port is available for binding.
    
    Args:
        port: Port number to check
        host: Host address to check (default: localhost)
        
    Returns:
        bool: True if port is available, False if in use
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1)
            result = sock.connect_ex((host, port))
            return result != 0  # Port is available if connection fails
    except Exception as e:
        logger.warning(f"Error checking port {port} availability: {e}")
        return False


def find_processes_using_port(port: int) -> List[Tuple[int, str]]:
    """
    Find all processes currently using a specific TCP port.
    
    Args:
        port: Port number to check
        
    Returns:
        List[Tuple[int, str]]: List of (PID, command_line) tuples for processes using the port
    """
    processes = []
    
    try:
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                # Get network connections for this process
                connections = proc.connections(kind='inet')
                for conn in connections:
                    if conn.laddr.port == port and conn.status == psutil.CONN_LISTEN:
                        cmd_line = ' '.join(proc.info['cmdline']) if proc.info['cmdline'] else proc.info['name']
                        processes.append((proc.info['pid'], cmd_line))
                        break
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                # Process might have disappeared or we don't have permission
                continue
                
    except Exception as e:
        logger.error(f"Error finding processes using port {port}: {e}")
        
    return processes


def cleanup_stale_processes(port: int, service_name: str = "mower", 
                          exclude_current: bool = True) -> List[int]:
    """
    Clean up stale processes that may be using a port from previous service runs.
    
    Args:
        port: Port number to clean up
        service_name: Service name to match in process command lines
        exclude_current: If True, exclude processes with current PID or parent PID
        
    Returns:
        List[int]: List of PIDs that were terminated
    """
    current_pid = os.getpid()
    current_ppid = os.getppid()
    terminated_pids = []
    
    # Find processes using the port
    port_processes = find_processes_using_port(port)
    
    for pid, cmd_line in port_processes:
        # Skip current process and its parent
        if exclude_current and (pid == current_pid or pid == current_ppid):
            logger.info(f"Skipping current process PID {pid}: {cmd_line}")
            continue
            
        # Check if this looks like our service
        if service_name.lower() in cmd_line.lower():
            logger.warning(f"Found stale {service_name} process PID {pid}: {cmd_line}")
            
            try:
                # Try graceful termination first
                os.kill(pid, signal.SIGTERM)
                time.sleep(2)
                
                # Check if process is still running
                if psutil.pid_exists(pid):
                    logger.warning(f"Process {pid} did not terminate gracefully, using SIGKILL")
                    os.kill(pid, signal.SIGKILL)
                    time.sleep(1)
                    
                terminated_pids.append(pid)
                logger.info(f"Successfully terminated stale process PID {pid}")
                
            except (ProcessLookupError, psutil.NoSuchProcess):
                # Process already gone
                logger.info(f"Process PID {pid} already terminated")
            except PermissionError:
                logger.error(f"Permission denied terminating process PID {pid}")
            except Exception as e:
                logger.error(f"Error terminating process PID {pid}: {e}")
        else:
            logger.info(f"Process PID {pid} on port {port} doesn't match service '{service_name}': {cmd_line}")
    
    return terminated_pids


def validate_startup_environment(port: int, service_name: str = "mower") -> bool:
    """
    Validate the startup environment and clean up any conflicts.
    
    Args:
        port: Port that needs to be available for the service
        service_name: Name of the service for process matching
        
    Returns:
        bool: True if environment is ready for startup, False if issues remain
    """
    logger.info(f"Validating startup environment for {service_name} service on port {port}")
    
    # Check if port is available
    if is_port_available(port):
        logger.info(f"Port {port} is available for service startup")
        return True
    
    logger.warning(f"Port {port} is in use, attempting to clean up stale processes")
    
    # Try to clean up stale processes
    terminated_pids = cleanup_stale_processes(port, service_name)
    
    if terminated_pids:
        logger.info(f"Cleaned up {len(terminated_pids)} stale processes: {terminated_pids}")
        
        # Wait a moment for cleanup to complete
        time.sleep(3)
        
        # Check port availability again
        if is_port_available(port):
            logger.info(f"Port {port} is now available after cleanup")
            return True
        else:
            logger.error(f"Port {port} still in use after cleanup attempt")
            return False
    else:
        # Port in use but no stale processes found
        logger.error(f"Port {port} in use by non-{service_name} processes")
        port_processes = find_processes_using_port(port)
        for pid, cmd_line in port_processes:
            logger.error(f"  PID {pid}: {cmd_line}")
        return False


def get_process_tree_info(pid: Optional[int] = None) -> dict:
    """
    Get information about the current process tree.
    
    Args:
        pid: Process ID to analyze (default: current process)
        
    Returns:
        dict: Process tree information including PID, PPID, children, etc.
    """
    if pid is None:
        pid = os.getpid()
        
    info = {
        'pid': pid,
        'ppid': os.getppid(),
        'children': [],
        'command': 'unknown'
    }
    
    try:
        proc = psutil.Process(pid)
        info['command'] = ' '.join(proc.cmdline()) if proc.cmdline() else proc.name()
        info['children'] = [child.pid for child in proc.children()]
        info['status'] = proc.status()
        info['create_time'] = proc.create_time()
        
    except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
        logger.warning(f"Could not get process info for PID {pid}: {e}")
        
    return info
