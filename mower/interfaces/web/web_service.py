"""
Web Service

This service provides a web interface for monitoring and controlling
the autonomous mower system with real-time updates via WebSockets.
"""

import asyncio
import json
import logging
import time
import uuid
from typing import Dict, Any, Optional, Set
from dataclasses import asdict

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import uvicorn

from mower.core.communication.base_service import BaseService, ServiceMessage
from mower.config.settings import SystemConfig


logger = logging.getLogger(__name__)


class WebSocketManager:
    """Manages WebSocket connections."""
    
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
    
    async def connect(self, websocket: WebSocket):
        """Accept new WebSocket connection."""
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        """Remove WebSocket connection."""
        self.active_connections.discard(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")
    
    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients."""
        if not self.active_connections:
            return
        
        disconnected = set()
        for websocket in self.active_connections:
            try:
                await websocket.send_json(message)
            except Exception:
                disconnected.add(websocket)
        
        # Remove disconnected clients
        for ws in disconnected:
            self.active_connections.discard(ws)
    
    async def send_to_client(self, websocket: WebSocket, message: dict):
        """Send message to specific client."""
        try:
            await websocket.send_json(message)
        except Exception:
            self.active_connections.discard(websocket)


class WebService(BaseService):
    """Web interface service with FastAPI and WebSockets."""
    
    def __init__(self, service_name: str = "web", config: Optional[SystemConfig] = None):
        """Initialize web service."""
        super().__init__(service_name, config)
        
        # FastAPI application
        self.app = FastAPI(title="Autonomous Mower Control", version="3.0.0")
        self.websocket_manager = WebSocketManager()
        
        # Service state cache
        self.cached_status = {
            "motor_control": {},
            "sensor": {},
            "vision": {},
            "navigation": {},
            "system": {}
        }
        
        # Request tracking
        self.pending_requests: Dict[str, dict] = {}
        
        # Setup routes
        self._setup_routes()
        
        # Register message handlers
        self.register_message_handler("command_response", self.handle_command_response)
        self.register_message_handler("mission_response", self.handle_mission_response)
        self.register_message_handler("pattern_response", self.handle_pattern_response)
    
    def _setup_routes(self):
        """Setup FastAPI routes."""
        
        @self.app.get("/", response_class=HTMLResponse)
        async def get_index():
            """Serve main web interface."""
            return """
            <!DOCTYPE html>
            <html>
            <head>
                <title>Autonomous Mower Control</title>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1">
                <style>
                    body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
                    .container { max-width: 1200px; margin: 0 auto; }
                    .card { background: white; padding: 20px; margin: 10px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
                    .header { background: #2c5d31; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; text-align: center; }
                    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
                    .status { padding: 10px; border-radius: 4px; margin: 5px 0; }
                    .status.healthy { background: #d4edda; color: #155724; }
                    .status.unhealthy { background: #f8d7da; color: #721c24; }
                    .controls { display: flex; gap: 10px; flex-wrap: wrap; }
                    button { padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; font-size: 14px; }
                    .btn-primary { background: #007bff; color: white; }
                    .btn-success { background: #28a745; color: white; }
                    .btn-warning { background: #ffc107; color: black; }
                    .btn-danger { background: #dc3545; color: white; }
                    button:hover { opacity: 0.8; }
                    .motor-controls { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
                    input[type="range"] { width: 100%; }
                    .connection-status { position: fixed; top: 10px; right: 10px; padding: 10px; border-radius: 4px; font-weight: bold; }
                    .connected { background: #28a745; color: white; }
                    .disconnected { background: #dc3545; color: white; }
                    #log { height: 200px; overflow-y: scroll; background: #f8f9fa; padding: 10px; border: 1px solid #dee2e6; border-radius: 4px; font-family: monospace; font-size: 12px; }
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>🚜 Autonomous Mower Control Panel</h1>
                        <p>Real-time monitoring and control system</p>
                    </div>
                    
                    <div class="connection-status" id="connectionStatus">
                        Connecting...
                    </div>
                    
                    <div class="grid">
                        <!-- System Status -->
                        <div class="card">
                            <h3>System Status</h3>
                            <div id="systemStatus">
                                <div class="status" id="overallStatus">System: Unknown</div>
                                <div class="status" id="safetyStatus">Safety: Unknown</div>
                                <div class="status" id="motorStatus">Motors: Unknown</div>
                                <div class="status" id="sensorStatus">Sensors: Unknown</div>
                                <div class="status" id="visionStatus">Vision: Unknown</div>
                                <div class="status" id="navigationStatus">Navigation: Unknown</div>
                            </div>
                        </div>
                        
                        <!-- Manual Control -->
                        <div class="card">
                            <h3>Manual Control</h3>
                            <div class="motor-controls">
                                <div>
                                    <label>Steering: <span id="steeringValue">0</span></label>
                                    <input type="range" id="steering" min="-100" max="100" value="0">
                                </div>
                                <div>
                                    <label>Throttle: <span id="throttleValue">0</span></label>
                                    <input type="range" id="throttle" min="-100" max="100" value="0">
                                </div>
                                <div>
                                    <label>Blade: <span id="bladeValue">0</span></label>
                                    <input type="range" id="blade" min="0" max="100" value="0">
                                </div>
                            </div>
                            <div class="controls">
                                <button class="btn-primary" onclick="sendMotorCommand()">Send Command</button>
                                <button class="btn-warning" onclick="stopMotors()">Stop Motors</button>
                                <button class="btn-danger" onclick="emergencyStop()">Emergency Stop</button>
                            </div>
                        </div>
                        
                        <!-- Mission Control -->
                        <div class="card">
                            <h3>Mission Control</h3>
                            <div id="missionStatus">
                                <p>Status: <span id="missionState">Idle</span></p>
                                <p>Progress: <span id="missionProgress">0%</span></p>
                                <p>Waypoint: <span id="currentWaypoint">0/0</span></p>
                            </div>
                            <div class="controls">
                                <button class="btn-success" onclick="startTestMission()">Start Test Mission</button>
                                <button class="btn-warning" onclick="stopMission()">Stop Mission</button>
                                <button class="btn-primary" onclick="generatePattern()">Generate Pattern</button>
                            </div>
                        </div>
                        
                        <!-- Sensor Data -->
                        <div class="card">
                            <h3>Sensor Data</h3>
                            <div id="sensorData">
                                <p>GPS: <span id="gpsPosition">No fix</span></p>
                                <p>Heading: <span id="heading">0°</span></p>
                                <p>Speed: <span id="speed">0.0 m/s</span></p>
                                <p>Battery: <span id="battery">0%</span></p>
                                <p>Obstacle: <span id="obstacle">Clear</span></p>
                                <p>Tilt: <span id="tilt">0°</span></p>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Activity Log -->
                    <div class="card">
                        <h3>Activity Log</h3>
                        <div id="log"></div>
                        <button class="btn-primary" onclick="clearLog()">Clear Log</button>
                    </div>
                </div>
                
                <script>
                    let ws = null;
                    let connectionStatus = document.getElementById('connectionStatus');
                    let logElement = document.getElementById('log');
                    
                    function connectWebSocket() {
                        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                        const wsUrl = `${protocol}//${window.location.host}/ws`;
                        
                        ws = new WebSocket(wsUrl);
                        
                        ws.onopen = function() {
                            connectionStatus.textContent = 'Connected';
                            connectionStatus.className = 'connection-status connected';
                            log('WebSocket connected');
                        };
                        
                        ws.onclose = function() {
                            connectionStatus.textContent = 'Disconnected';
                            connectionStatus.className = 'connection-status disconnected';
                            log('WebSocket disconnected');
                            setTimeout(connectWebSocket, 3000);
                        };
                        
                        ws.onerror = function(error) {
                            log('WebSocket error: ' + error);
                        };
                        
                        ws.onmessage = function(event) {
                            const data = JSON.parse(event.data);
                            handleWebSocketMessage(data);
                        };
                    }
                    
                    function handleWebSocketMessage(data) {
                        if (data.type === 'status_update') {
                            updateStatus(data.services);
                        } else if (data.type === 'sensor_data') {
                            updateSensorData(data.data);
                        } else if (data.type === 'log') {
                            log(data.message);
                        }
                    }
                    
                    function updateStatus(services) {
                        // Update system status indicators
                        updateStatusElement('motorStatus', 'Motors', services.motor_control);
                        updateStatusElement('sensorStatus', 'Sensors', services.sensor);
                        updateStatusElement('visionStatus', 'Vision', services.vision);
                        updateStatusElement('navigationStatus', 'Navigation', services.navigation);
                        
                        // Update mission status
                        if (services.navigation) {
                            document.getElementById('missionState').textContent = services.navigation.mode || 'Idle';
                            document.getElementById('missionProgress').textContent = (services.navigation.progress_percent || 0).toFixed(1) + '%';
                            document.getElementById('currentWaypoint').textContent = `${services.navigation.waypoint_index || 0}/${services.navigation.total_waypoints || 0}`;
                        }
                    }
                    
                    function updateStatusElement(elementId, name, serviceData) {
                        const element = document.getElementById(elementId);
                        if (serviceData && serviceData.state === 'running') {
                            element.textContent = `${name}: Online`;
                            element.className = 'status healthy';
                        } else {
                            element.textContent = `${name}: Offline`;
                            element.className = 'status unhealthy';
                        }
                    }
                    
                    function updateSensorData(data) {
                        if (data.fusion) {
                            const fusion = data.fusion;
                            document.getElementById('gpsPosition').textContent = `${fusion.position_lat?.toFixed(6) || 0}, ${fusion.position_lon?.toFixed(6) || 0}`;
                            document.getElementById('heading').textContent = (fusion.heading_degrees || 0).toFixed(1) + '°';
                            document.getElementById('speed').textContent = (fusion.speed_mps || 0).toFixed(1) + ' m/s';
                            document.getElementById('battery').textContent = (fusion.battery_level || 0).toFixed(1) + '%';
                            document.getElementById('obstacle').textContent = fusion.obstacle_distance_mm > 1000 ? 'Clear' : 'Detected';
                            document.getElementById('tilt').textContent = (fusion.tilt_degrees || 0).toFixed(1) + '°';
                        }
                    }
                    
                    function log(message) {
                        const timestamp = new Date().toLocaleTimeString();
                        logElement.innerHTML += `[${timestamp}] ${message}<br>`;
                        logElement.scrollTop = logElement.scrollHeight;
                    }
                    
                    function clearLog() {
                        logElement.innerHTML = '';
                    }
                    
                    // Control functions
                    function sendMotorCommand() {
                        const steering = parseInt(document.getElementById('steering').value);
                        const throttle = parseInt(document.getElementById('throttle').value);
                        const blade = parseInt(document.getElementById('blade').value);
                        
                        if (ws && ws.readyState === WebSocket.OPEN) {
                            ws.send(JSON.stringify({
                                type: 'motor_command',
                                data: { steering, throttle, blade }
                            }));
                            log(`Motor command: S=${steering}, T=${throttle}, B=${blade}`);
                        }
                    }
                    
                    function stopMotors() {
                        if (ws && ws.readyState === WebSocket.OPEN) {
                            ws.send(JSON.stringify({
                                type: 'stop_motors'
                            }));
                            log('Stop motors command sent');
                        }
                    }
                    
                    function emergencyStop() {
                        if (ws && ws.readyState === WebSocket.OPEN) {
                            ws.send(JSON.stringify({
                                type: 'emergency_stop'
                            }));
                            log('EMERGENCY STOP activated');
                        }
                    }
                    
                    function startTestMission() {
                        if (ws && ws.readyState === WebSocket.OPEN) {
                            ws.send(JSON.stringify({
                                type: 'start_mission',
                                data: {
                                    name: 'Test Mission',
                                    waypoints: [
                                        { latitude: 40.7128, longitude: -74.0060, speed: 1.0, action: 'move' },
                                        { latitude: 40.7130, longitude: -74.0058, speed: 1.0, action: 'mow' },
                                        { latitude: 40.7132, longitude: -74.0056, speed: 1.0, action: 'mow' }
                                    ]
                                }
                            }));
                            log('Test mission started');
                        }
                    }
                    
                    function stopMission() {
                        if (ws && ws.readyState === WebSocket.OPEN) {
                            ws.send(JSON.stringify({
                                type: 'stop_mission'
                            }));
                            log('Mission stopped');
                        }
                    }
                    
                    function generatePattern() {
                        if (ws && ws.readyState === WebSocket.OPEN) {
                            ws.send(JSON.stringify({
                                type: 'generate_pattern',
                                data: {
                                    boundary_points: [
                                        [40.7128, -74.0060],
                                        [40.7140, -74.0060],
                                        [40.7140, -74.0050],
                                        [40.7128, -74.0050]
                                    ],
                                    pattern_type: 'lines'
                                }
                            }));
                            log('Pattern generation requested');
                        }
                    }
                    
                    // Update slider displays
                    document.getElementById('steering').oninput = function() {
                        document.getElementById('steeringValue').textContent = this.value;
                    };
                    document.getElementById('throttle').oninput = function() {
                        document.getElementById('throttleValue').textContent = this.value;
                    };
                    document.getElementById('blade').oninput = function() {
                        document.getElementById('bladeValue').textContent = this.value;
                    };
                    
                    // Initialize
                    connectWebSocket();
                    
                    // Request status updates every 2 seconds
                    setInterval(function() {
                        if (ws && ws.readyState === WebSocket.OPEN) {
                            ws.send(JSON.stringify({ type: 'get_status' }));
                        }
                    }, 2000);
                </script>
            </body>
            </html>
            """
        
        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            """WebSocket endpoint for real-time updates."""
            await self.websocket_manager.connect(websocket)
            try:
                while True:
                    data = await websocket.receive_json()
                    await self._handle_websocket_message(websocket, data)
            except WebSocketDisconnect:
                self.websocket_manager.disconnect(websocket)
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                self.websocket_manager.disconnect(websocket)
    
    async def service_initialize(self) -> bool:
        """Initialize web service components."""
        try:
            logger.info("Web service initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Web service initialization failed: {e}")
            return False
    
    async def service_loop(self) -> None:
        """Main web service loop."""
        try:
            # Start FastAPI server
            config = uvicorn.Config(
                self.app,
                host=self.config.services.web_host,
                port=self.config.services.web_port,
                log_level="info"
            )
            server = uvicorn.Server(config)
            
            # Run server
            await server.serve()
            
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Web service loop error: {e}")
    
    async def service_cleanup(self) -> None:
        """Cleanup web service."""
        try:
            logger.info("Web service cleanup complete")
            
        except Exception as e:
            logger.error(f"Web service cleanup error: {e}")
    
    async def _handle_websocket_message(self, websocket: WebSocket, data: dict) -> None:
        """Handle incoming WebSocket message."""
        try:
            message_type = data.get("type")
            
            if message_type == "get_status":
                await self._send_status_update(websocket)
            
            elif message_type == "motor_command":
                await self._handle_motor_command(data.get("data", {}))
            
            elif message_type == "stop_motors":
                await self._handle_stop_motors()
            
            elif message_type == "emergency_stop":
                await self._handle_emergency_stop()
            
            elif message_type == "start_mission":
                await self._handle_start_mission(data.get("data", {}))
            
            elif message_type == "stop_mission":
                await self._handle_stop_mission()
            
            elif message_type == "generate_pattern":
                await self._handle_generate_pattern(data.get("data", {}))
            
            else:
                logger.warning(f"Unknown WebSocket message type: {message_type}")
                
        except Exception as e:
            logger.error(f"WebSocket message handling error: {e}")
    
    async def _send_status_update(self, websocket: Optional[WebSocket] = None) -> None:
        """Send status update to client(s)."""
        try:
            # Collect status from all services
            services_status = {}
            
            for service_name in ["motor_control", "sensor", "vision", "navigation"]:
                health = await self.get_service_health(service_name)
                if health:
                    services_status[service_name] = asdict(health)
                else:
                    services_status[service_name] = {"state": "unknown"}
            
            # Get sensor data
            sensor_data = {}
            if self.redis_client:
                sensor_data_str = await self.redis_client.get("service:sensor:data")
                if sensor_data_str:
                    sensor_data = json.loads(sensor_data_str)
            
            message = {
                "type": "status_update",
                "services": services_status,
                "timestamp": time.time()
            }
            
            if websocket:
                await self.websocket_manager.send_to_client(websocket, message)
            else:
                await self.websocket_manager.broadcast(message)
            
            # Send sensor data separately
            if sensor_data:
                sensor_message = {
                    "type": "sensor_data",
                    "data": sensor_data,
                    "timestamp": time.time()
                }
                if websocket:
                    await self.websocket_manager.send_to_client(websocket, sensor_message)
                else:
                    await self.websocket_manager.broadcast(sensor_message)
            
        except Exception as e:
            logger.error(f"Status update error: {e}")
    
    async def _handle_motor_command(self, data: dict) -> None:
        """Handle motor command from web interface."""
        try:
            correlation_id = str(uuid.uuid4())
            self.pending_requests[correlation_id] = {"type": "motor_command", "timestamp": time.time()}
            
            await self.send_message(
                "motor_control",
                "set_motors",
                data,
                correlation_id
            )
            
            await self.websocket_manager.broadcast({
                "type": "log",
                "message": f"Motor command sent: {data}"
            })
            
        except Exception as e:
            logger.error(f"Motor command error: {e}")
    
    async def _handle_stop_motors(self) -> None:
        """Handle stop motors command."""
        try:
            await self.send_message("motor_control", "stop_motors", {})
            
            await self.websocket_manager.broadcast({
                "type": "log",
                "message": "Stop motors command sent"
            })
            
        except Exception as e:
            logger.error(f"Stop motors error: {e}")
    
    async def _handle_emergency_stop(self) -> None:
        """Handle emergency stop command."""
        try:
            await self.send_message("motor_control", "emergency_stop", {})
            
            await self.websocket_manager.broadcast({
                "type": "log",
                "message": "EMERGENCY STOP activated"
            })
            
        except Exception as e:
            logger.error(f"Emergency stop error: {e}")
    
    async def _handle_start_mission(self, data: dict) -> None:
        """Handle start mission command."""
        try:
            correlation_id = str(uuid.uuid4())
            self.pending_requests[correlation_id] = {"type": "start_mission", "timestamp": time.time()}
            
            await self.send_message(
                "navigation",
                "start_mission",
                data,
                correlation_id
            )
            
            await self.websocket_manager.broadcast({
                "type": "log",
                "message": f"Mission started: {data.get('name', 'Unknown')}"
            })
            
        except Exception as e:
            logger.error(f"Start mission error: {e}")
    
    async def _handle_stop_mission(self) -> None:
        """Handle stop mission command."""
        try:
            await self.send_message("navigation", "stop_mission", {})
            
            await self.websocket_manager.broadcast({
                "type": "log",
                "message": "Mission stop requested"
            })
            
        except Exception as e:
            logger.error(f"Stop mission error: {e}")
    
    async def _handle_generate_pattern(self, data: dict) -> None:
        """Handle generate pattern command."""
        try:
            correlation_id = str(uuid.uuid4())
            self.pending_requests[correlation_id] = {"type": "generate_pattern", "timestamp": time.time()}
            
            await self.send_message(
                "navigation",
                "generate_pattern",
                data,
                correlation_id
            )
            
            await self.websocket_manager.broadcast({
                "type": "log",
                "message": "Pattern generation requested"
            })
            
        except Exception as e:
            logger.error(f"Generate pattern error: {e}")
    
    async def handle_command_response(self, message: ServiceMessage) -> None:
        """Handle command response from services."""
        try:
            if message.correlation_id in self.pending_requests:
                request_info = self.pending_requests.pop(message.correlation_id)
                
                await self.websocket_manager.broadcast({
                    "type": "log",
                    "message": f"Command response: {message.data.get('message', 'OK')}"
                })
        
        except Exception as e:
            logger.error(f"Command response handling error: {e}")
    
    async def handle_mission_response(self, message: ServiceMessage) -> None:
        """Handle mission response from navigation service."""
        try:
            await self.websocket_manager.broadcast({
                "type": "log",
                "message": f"Mission: {message.data.get('message', 'Response received')}"
            })
        
        except Exception as e:
            logger.error(f"Mission response handling error: {e}")
    
    async def handle_pattern_response(self, message: ServiceMessage) -> None:
        """Handle pattern response from navigation service."""
        try:
            if message.data.get("success"):
                waypoints = message.data.get("waypoints", [])
                await self.websocket_manager.broadcast({
                    "type": "log",
                    "message": f"Pattern generated: {len(waypoints)} waypoints"
                })
            else:
                await self.websocket_manager.broadcast({
                    "type": "log",
                    "message": f"Pattern generation failed: {message.data.get('message', 'Unknown error')}"
                })
        
        except Exception as e:
            logger.error(f"Pattern response handling error: {e}")


# Service entry point
def main():
    """Main entry point for web service."""
    from mower.core.communication.base_service import run_service
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger.info("Starting Web Service")
    run_service(WebService, "web")


if __name__ == "__main__":
    main()
