"""
Inter-process communication for commands between web UI and main controller.

This module provides a file-based command queue system to allow the web UI process
to send commands to the main controller process for hardware control.
"""

import json
import os
import time
import threading
from pathlib import Path
from typing import Dict, Any, Optional, Callable
from mower.utilities.logger_config import LoggerConfigInfo

logger = LoggerConfigInfo.get_logger(__name__)

class CommandQueue:
    """File-based command queue for inter-process communication."""
    
    def __init__(self, queue_file: str = "/home/pi/autonomous_mower/ipc_command_queue.json"):
        """
        Initialize the command queue.
        
        Args:
            queue_file: Path to the command queue file
        """
        self.queue_file = Path(queue_file)
        self._lock = threading.Lock()
        
    def send_command(self, command: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Send a command to the main controller process.
        
        Args:
            command: Command name
            params: Command parameters
            
        Returns:
            Command result or timeout error
        """
        params = params or {}
        command_id = str(int(time.time() * 1000000))  # Microsecond timestamp as ID
        
        command_data = {
            "id": command_id,
            "command": command,
            "params": params,
            "timestamp": time.time(),
            "status": "pending"
        }
        
        try:
            # Write command to queue file
            with self._lock:
                self._write_command(command_data)
            
            logger.info(f"Command sent: {command} (ID: {command_id})")
            
            # Wait for response with timeout
            response = self._wait_for_response(command_id, timeout=5.0)
            
            if response:
                logger.info(f"Command response received: {command} -> {response}")
                return response
            else:
                logger.warning(f"Command timeout: {command} (ID: {command_id})")
                return {"success": False, "error": "Command timeout - main controller may not be processing commands"}
                
        except Exception as e:
            logger.error(f"Error sending command {command}: {e}")
            return {"success": False, "error": f"IPC error: {str(e)}"}
    
    def _write_command(self, command_data: Dict[str, Any]):
        """Write command to the queue file atomically."""
        try:
            # Read existing commands
            commands = []
            if self.queue_file.exists():
                try:
                    with open(self.queue_file, 'r') as f:
                        content = f.read().strip()
                        if content:
                            commands = json.loads(content)
                except (json.JSONDecodeError, IOError):
                    # File corrupted or empty, start fresh
                    commands = []
            
            # Add new command
            commands.append(command_data)
            
            # Keep only recent commands (last 100)
            commands = commands[-100:]
            
            # Write atomically
            temp_file = self.queue_file.with_suffix('.tmp')
            with open(temp_file, 'w') as f:
                json.dump(commands, f)
            temp_file.replace(self.queue_file)
            
        except Exception as e:
            logger.error(f"Error writing command to queue: {e}")
            raise
    
    def _wait_for_response(self, command_id: str, timeout: float = 5.0) -> Optional[Dict[str, Any]]:
        """Wait for command response with timeout."""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                if self.queue_file.exists():
                    with open(self.queue_file, 'r') as f:
                        content = f.read().strip()
                        if content:
                            commands = json.loads(content)
                            
                            # Find our command
                            for cmd in commands:
                                if cmd.get("id") == command_id and cmd.get("status") != "pending":
                                    return {
                                        "success": cmd.get("status") == "completed",
                                        "result": cmd.get("result"),
                                        "error": cmd.get("error"),
                                        "message": cmd.get("message")
                                    }
            except (json.JSONDecodeError, IOError):
                pass
            
            time.sleep(0.1)  # Check every 100ms
        
        return None


class CommandProcessor:
    """Process commands from the queue in the main controller."""
    
    def __init__(self, command_handler: Callable[[str, Dict[str, Any]], Dict[str, Any]], 
                 queue_file: str = "/home/pi/autonomous_mower/ipc_command_queue.json"):
        """
        Initialize the command processor.
        
        Args:
            command_handler: Function to execute commands (typically ResourceManager.execute_command)
            queue_file: Path to the command queue file
        """
        self.command_handler = command_handler
        self.queue_file = Path(queue_file)
        self._lock = threading.Lock()
        self._running = False
        self._thread = None
        
    def start(self):
        """Start the command processing thread."""
        if self._running:
            return
            
        self._running = True
        self._thread = threading.Thread(target=self._process_loop, daemon=True)
        self._thread.start()
        logger.info("Command processor started")
        
    def stop(self):
        """Stop the command processing thread."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        logger.info("Command processor stopped")
        
    def _process_loop(self):
        """Main processing loop."""
        while self._running:
            try:
                self._process_pending_commands()
                time.sleep(0.1)  # Check every 100ms
            except Exception as e:
                logger.error(f"Error in command processing loop: {e}")
                time.sleep(1.0)  # Wait longer on error
                
    def _process_pending_commands(self):
        """Process any pending commands in the queue."""
        if not self.queue_file.exists():
            return
            
        try:
            with self._lock:
                with open(self.queue_file, 'r') as f:
                    content = f.read().strip()
                    if not content:
                        return
                        
                commands = json.loads(content)
                updated = False
                
                for cmd in commands:
                    if cmd.get("status") == "pending":
                        # Process this command
                        result = self._execute_command(cmd)
                        cmd["status"] = "completed" if result.get("success") else "failed"
                        cmd["result"] = result.get("result")
                        cmd["error"] = result.get("error") 
                        cmd["message"] = result.get("message")
                        cmd["processed_time"] = time.time()
                        updated = True
                        
                        logger.info(f"Processed command: {cmd['command']} -> {result}")
                
                # Write back updated commands if any were processed
                if updated:
                    temp_file = self.queue_file.with_suffix('.tmp')
                    with open(temp_file, 'w') as f:
                        json.dump(commands, f)
                    temp_file.replace(self.queue_file)
                    
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Error processing command queue: {e}")
            
    def _execute_command(self, cmd: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single command."""
        try:
            command = cmd.get("command")
            params = cmd.get("params", {})
            
            logger.info(f"Executing command: {command} with params: {params}")
            result = self.command_handler(command, params)
            
            if not isinstance(result, dict):
                result = {"success": True, "result": result}
                
            return result
            
        except Exception as e:
            logger.error(f"Error executing command {cmd.get('command')}: {e}")
            return {"success": False, "error": str(e)}


# Global instances for easy access
_command_queue = None
_command_processor = None

def get_command_queue() -> CommandQueue:
    """Get the global command queue instance."""
    global _command_queue
    if _command_queue is None:
        _command_queue = CommandQueue()
    return _command_queue

def get_command_processor(command_handler: Callable[[str, Dict[str, Any]], Dict[str, Any]]) -> CommandProcessor:
    """Get the global command processor instance."""
    global _command_processor
    if _command_processor is None:
        _command_processor = CommandProcessor(command_handler)
    return _command_processor
