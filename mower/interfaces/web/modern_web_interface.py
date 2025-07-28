"""
Modern Web Interface
 
A modern, responsive web interface for the autonomous mower with Google Maps integration,
camera streaming, and advanced zone management.
"""

import asyncio
import json
import logging
import time
from typing import Dict, Any, Optional, List
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

from mower.core.communication.base_service import BaseService, ServiceMessage
from mower.config.settings import SystemConfig

logger = logging.getLogger(__name__)


class ModernWebService(BaseService):
    """Modern web interface service with advanced features."""
    
    def __init__(self, service_name: str = "web", config: Optional[SystemConfig] = None):
        """Initialize modern web service."""
        super().__init__(service_name, config)
        
        self.app = FastAPI(title="Autonomous Mower Control", version="2.0.0")
        self.active_connections: List[WebSocket] = []
        
        # Zone storage
        self.zones_file = Path("data/zones.json")
        self.zones_file.parent.mkdir(exist_ok=True)
        self.zones = self._load_zones()
        
        self._setup_routes()
        
        # Register message handlers
        self.register_message_handler("zone_update", self.handle_zone_update)
    
    def _setup_routes(self):
        """Setup FastAPI routes."""
        
        @self.app.get("/", response_class=HTMLResponse)
        async def get_index():
            """Serve modern web interface."""
            return self._get_modern_interface()
        
        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            await self._handle_websocket(websocket)
        
        @self.app.get("/api/status")
        async def get_status():
            """Get system status."""
            return await self._get_system_status()
        
        @self.app.get("/api/camera/stream")
        async def get_camera_stream():
            """Get camera stream frame."""
            return await self._get_camera_frame()
        
        @self.app.get("/api/zones")
        async def get_zones():
            """Get all zones."""
            return {"zones": self.zones}
        
        @self.app.post("/api/zones")
        async def save_zones(request: Request):
            """Save zones."""
            data = await request.json()
            self.zones = data.get("zones", {})
            self._save_zones()
            return {"success": True}
        
        @self.app.post("/api/motor/command")
        async def motor_command(request: Request):
            """Send motor command."""
            data = await request.json()
            await self._handle_motor_command(data)
            return {"success": True}
        
        @self.app.post("/api/mission/start")
        async def start_mission(request: Request):
            """Start mission."""
            data = await request.json()
            await self._handle_start_mission(data)
            return {"success": True}
        
        @self.app.post("/api/mission/stop")
        async def stop_mission():
            """Stop mission."""
            await self._handle_stop_mission()
            return {"success": True}
        
        @self.app.post("/api/emergency_stop")
        async def emergency_stop():
            """Emergency stop."""
            await self._handle_emergency_stop()
            return {"success": True}
    
    def _get_modern_interface(self) -> str:
        """Generate modern web interface HTML."""
        # Get API key from config
        api_key = getattr(self.config.services, 'google_maps_api_key', '')
        
        html_template = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Autonomous Mower Control</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css" rel="stylesheet">
    <style>
        :root {
            --primary-color: #2c5d31;
            --secondary-color: #4a8f5a;
            --success-color: #28a745;
            --warning-color: #ffc107;
            --danger-color: #dc3545;
            --dark-bg: #1a1a1a;
            --card-bg: #ffffff;
            --text-muted: #6c757d;
        }
        
        body {
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            min-height: 100vh;
        }
        
        .navbar {
            background: var(--primary-color) !important;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        .navbar-brand {
            font-weight: bold;
            font-size: 1.5rem;
        }
        
        .card {
            border: none;
            border-radius: 15px;
            box-shadow: 0 8px 25px rgba(0,0,0,0.1);
            transition: transform 0.2s ease, box-shadow 0.2s ease;
            background: var(--card-bg);
        }
        
        .card:hover {
            transform: translateY(-2px);
            box-shadow: 0 12px 35px rgba(0,0,0,0.15);
        }
        
        .card-header {
            background: var(--primary-color);
            color: white;
            border-radius: 15px 15px 0 0 !important;
            font-weight: 600;
        }
        
        .status-indicator {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            display: inline-block;
            margin-right: 8px;
        }
        
        .status-healthy { background-color: var(--success-color); }
        .status-warning { background-color: var(--warning-color); }
        .status-error { background-color: var(--danger-color); }
        
        .control-panel {
            background: white;
            border-radius: 15px;
            padding: 20px;
        }
        
        .joystick-container {
            position: relative;
            width: 200px;
            height: 200px;
            margin: 20px auto;
        }
        
        .btn-modern {
            border-radius: 25px;
            padding: 10px 25px;
            font-weight: 600;
            border: none;
            transition: all 0.3s ease;
        }
        
        .btn-modern:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0,0,0,0.2);
        }
        
        .camera-feed {
            border-radius: 15px;
            overflow: hidden;
            background: #000;
            position: relative;
        }
        
        .camera-feed img {
            width: 100%;
            height: auto;
            display: block;
        }
        
        .map-container {
            height: 400px;
            border-radius: 15px;
            overflow: hidden;
            border: 2px solid #dee2e6;
        }
        
        .zone-controls {
            display: flex;
            gap: 10px;
            margin-bottom: 15px;
            flex-wrap: wrap;
        }
        
        .connection-status {
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 1050;
            padding: 10px 15px;
            border-radius: 25px;
            font-weight: 600;
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
        }
        
        .connected {
            background: var(--success-color);
            color: white;
        }
        
        .disconnected {
            background: var(--danger-color);
            color: white;
        }
        
        .metric-card {
            text-align: center;
            padding: 20px;
            border-radius: 15px;
            background: white;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }
        
        .metric-value {
            font-size: 2.5rem;
            font-weight: bold;
            color: var(--primary-color);
        }
        
        .metric-label {
            color: var(--text-muted);
            font-size: 0.9rem;
        }
        
        @media (max-width: 768px) {
            .joystick-container {
                width: 150px;
                height: 150px;
            }
            
            .map-container {
                height: 300px;
            }
        }
    </style>
</head>
<body>
    <!-- Navigation -->
    <nav class="navbar navbar-expand-lg navbar-dark">
        <div class="container-fluid">
            <a class="navbar-brand" href="#">
                <i class="bi bi-robot"></i> Autonomous Mower
            </a>
            <div class="navbar-nav ms-auto">
                <span class="navbar-text">
                    <i class="bi bi-wifi"></i> <span id="connectionStatus">Connecting...</span>
                </span>
            </div>
        </div>
    </nav>

    <div class="container-fluid mt-4">
        <!-- Connection Status -->
        <div class="connection-status" id="connectionIndicator">
            <i class="bi bi-wifi"></i> Connecting...
        </div>

        <div class="row">
            <!-- System Status -->
            <div class="col-xl-3 col-lg-4 col-md-6 mb-4">
                <div class="card h-100">
                    <div class="card-header">
                        <i class="bi bi-activity"></i> System Status
                    </div>
                    <div class="card-body">
                        <div class="row g-3">
                            <div class="col-6">
                                <div class="metric-card">
                                    <div class="metric-value" id="batteryLevel">--</div>
                                    <div class="metric-label">Battery %</div>
                                </div>
                            </div>
                            <div class="col-6">
                                <div class="metric-card">
                                    <div class="metric-value" id="motorTemp">--</div>
                                    <div class="metric-label">Temp °C</div>
                                </div>
                            </div>
                        </div>
                        <hr>
                        <div id="serviceStatus">
                            <div class="d-flex justify-content-between align-items-center mb-2">
                                <span>Motors</span>
                                <span><i class="status-indicator status-healthy"></i>Online</span>
                            </div>
                            <div class="d-flex justify-content-between align-items-center mb-2">
                                <span>Sensors</span>
                                <span><i class="status-indicator status-healthy"></i>Online</span>
                            </div>
                            <div class="d-flex justify-content-between align-items-center mb-2">
                                <span>Vision</span>
                                <span><i class="status-indicator status-healthy"></i>Online</span>
                            </div>
                            <div class="d-flex justify-content-between align-items-center">
                                <span>Navigation</span>
                                <span><i class="status-indicator status-healthy"></i>Online</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Camera Feed -->
            <div class="col-xl-4 col-lg-8 col-md-6 mb-4">
                <div class="card h-100">
                    <div class="card-header">
                        <i class="bi bi-camera-video"></i> Live Camera Feed
                    </div>
                    <div class="card-body p-0">
                        <div class="camera-feed">
                            <img id="cameraStream" src="data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjQwIiBoZWlnaHQ9IjQ4MCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iNjQwIiBoZWlnaHQ9IjQ4MCIgZmlsbD0iIzMzMzMzMyIvPjx0ZXh0IHg9IjMyMCIgeT0iMjQwIiBmb250LXNpemU9IjE4IiBmaWxsPSIjY2NjY2NjIiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBkeT0iLjNlbSI+Q2FtZXJhIE9mZmxpbmU8L3RleHQ+PC9zdmc+" alt="Camera Feed">
                        </div>
                        <div class="p-3">
                            <small class="text-muted">
                                <i class="bi bi-info-circle"></i> 
                                <span id="cameraInfo">Waiting for camera feed...</span>
                            </small>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Manual Control -->
            <div class="col-xl-5 col-lg-12 mb-4">
                <div class="card h-100">
                    <div class="card-header">
                        <i class="bi bi-joystick"></i> Manual Control
                    </div>
                    <div class="card-body">
                        <div class="row">
                            <div class="col-md-6">
                                <div class="control-panel">
                                    <h6 class="mb-3">Motor Controls</h6>
                                    <div class="mb-3">
                                        <label class="form-label">Steering: <span id="steeringValue">0</span></label>
                                        <input type="range" class="form-range" id="steering" min="-100" max="100" value="0">
                                    </div>
                                    <div class="mb-3">
                                        <label class="form-label">Throttle: <span id="throttleValue">0</span></label>
                                        <input type="range" class="form-range" id="throttle" min="-100" max="100" value="0">
                                    </div>
                                    <div class="mb-3">
                                        <label class="form-label">Blade Speed: <span id="bladeValue">0</span>%</label>
                                        <input type="range" class="form-range" id="blade" min="0" max="100" value="0">
                                    </div>
                                </div>
                            </div>
                            <div class="col-md-6">
                                <div class="d-grid gap-2">
                                    <button class="btn btn-primary btn-modern" onclick="sendMotorCommand()">
                                        <i class="bi bi-send"></i> Send Command
                                    </button>
                                    <button class="btn btn-warning btn-modern" onclick="stopMotors()">
                                        <i class="bi bi-stop"></i> Stop Motors
                                    </button>
                                    <button class="btn btn-danger btn-modern" onclick="emergencyStop()">
                                        <i class="bi bi-exclamation-triangle"></i> Emergency Stop
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <div class="row">
            <!-- Map & Zones -->
            <div class="col-lg-8 mb-4">
                <div class="card">
                    <div class="card-header d-flex justify-content-between align-items-center">
                        <span><i class="bi bi-map"></i> Yard Map & Zones</span>
                        <div class="btn-group" role="group">
                            <button class="btn btn-sm btn-outline-light" onclick="setMapMode('boundary')">
                                <i class="bi bi-bounding-box"></i> Boundary
                            </button>
                            <button class="btn btn-sm btn-outline-light" onclick="setMapMode('nogo')">
                                <i class="bi bi-x-circle"></i> No-Go
                            </button>
                            <button class="btn btn-sm btn-outline-light" onclick="setMapMode('home')">
                                <i class="bi bi-house"></i> Home
                            </button>
                        </div>
                    </div>
                    <div class="card-body p-0">
                        <div class="zone-controls p-3">
                            <button class="btn btn-success btn-sm btn-modern" onclick="saveZones()">
                                <i class="bi bi-save"></i> Save Zones
                            </button>
                            <button class="btn btn-warning btn-sm btn-modern" onclick="clearCurrentZone()">
                                <i class="bi bi-trash"></i> Clear Current
                            </button>
                            <span class="badge bg-info ms-2" id="mapModeIndicator">Select Mode</span>
                        </div>
                        <div id="map" class="map-container"></div>
                    </div>
                </div>
            </div>

            <!-- Mission Control -->
            <div class="col-lg-4 mb-4">
                <div class="card">
                    <div class="card-header">
                        <i class="bi bi-play-circle"></i> Mission Control
                    </div>
                    <div class="card-body">
                        <div class="mission-status mb-3">
                            <h6>Current Status</h6>
                            <div class="d-flex justify-content-between">
                                <span>State:</span>
                                <span id="missionState" class="badge bg-secondary">Idle</span>
                            </div>
                            <div class="d-flex justify-content-between mt-2">
                                <span>Progress:</span>
                                <span id="missionProgress">0%</span>
                            </div>
                        </div>
                        
                        <div class="d-grid gap-2">
                            <button class="btn btn-success btn-modern" onclick="startMowing()">
                                <i class="bi bi-play"></i> Start Mowing
                            </button>
                            <button class="btn btn-primary btn-modern" onclick="returnHome()">
                                <i class="bi bi-house"></i> Return Home
                            </button>
                            <button class="btn btn-warning btn-modern" onclick="stopMission()">
                                <i class="bi bi-pause"></i> Pause Mission
                            </button>
                        </div>

                        <hr>
                        <div class="quick-patterns">
                            <h6>Quick Patterns</h6>
                            <div class="d-grid gap-1">
                                <button class="btn btn-outline-primary btn-sm" onclick="generatePattern('lines')">
                                    <i class="bi bi-grid-3x3"></i> Parallel Lines
                                </button>
                                <button class="btn btn-outline-primary btn-sm" onclick="generatePattern('spiral')">
                                    <i class="bi bi-arrow-clockwise"></i> Spiral
                                </button>
                                <button class="btn btn-outline-primary btn-sm" onclick="generatePattern('perimeter')">
                                    <i class="bi bi-square"></i> Perimeter First
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Activity Log -->
        <div class="row">
            <div class="col-12 mb-4">
                <div class="card">
                    <div class="card-header d-flex justify-content-between align-items-center">
                        <span><i class="bi bi-list-ul"></i> Activity Log</span>
                        <button class="btn btn-sm btn-outline-light" onclick="clearLog()">
                            <i class="bi bi-trash"></i> Clear
                        </button>
                    </div>
                    <div class="card-body">
                        <div id="activityLog" style="height: 200px; overflow-y: auto; font-family: 'Courier New', monospace; font-size: 0.9rem;">
                            <div class="text-muted">System ready. Waiting for commands...</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Scripts -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script async defer src="https://maps.googleapis.com/maps/api/js?key={{google_maps_api_key}}&libraries=drawing&callback=initMap"></script>
    
    <script>
        // Global variables
        let ws = null;
        let map = null;
        let drawingManager = null;
        let currentMapMode = null;
        let mowerMarker = null;
        let mowerPosition = { lat: 40.7128, lng: -74.0060 };
        let zones = {
            boundary: [],
            noGo: [],
            home: null
        };
        
        // Initialize everything when page loads
        document.addEventListener('DOMContentLoaded', function() {
            connectWebSocket();
            setupControlListeners();
            // Map will be initialized by Google Maps callback
        });
        
        // WebSocket Connection
        function connectWebSocket() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}/ws`;
            
            ws = new WebSocket(wsUrl);
            
            ws.onopen = function(event) {
                updateConnectionStatus(true);
                log('Connected to mower system');
                requestStatus();
            };
            
            ws.onmessage = function(event) {
                handleWebSocketMessage(JSON.parse(event.data));
            };
            
            ws.onclose = function(event) {
                updateConnectionStatus(false);
                log('Disconnected from mower system');
                // Attempt to reconnect after 3 seconds
                setTimeout(connectWebSocket, 3000);
            };
            
            ws.onerror = function(error) {
                log('WebSocket error: ' + error);
            };
        }
        
        function handleWebSocketMessage(data) {
            switch(data.type) {
                case 'status':
                    updateStatus(data.data);
                    break;
                case 'camera_frame':
                    updateCameraFeed(data.data);
                    break;
                case 'mission_update':
                    updateMissionStatus(data.data);
                    break;
                case 'log':
                    log(data.message);
                    break;
            }
        }
        
        function updateConnectionStatus(connected) {
            const indicator = document.getElementById('connectionIndicator');
            const status = document.getElementById('connectionStatus');
            
            if (connected) {
                indicator.className = 'connection-status connected';
                indicator.innerHTML = '<i class="bi bi-wifi"></i> Connected';
                status.textContent = 'Connected';
            } else {
                indicator.className = 'connection-status disconnected';
                indicator.innerHTML = '<i class="bi bi-wifi-off"></i> Disconnected';
                status.textContent = 'Disconnected';
            }
        }
        
        function updateStatus(status) {
            // Update battery and temperature
            document.getElementById('batteryLevel').textContent = Math.round(status.battery_level || 0);
            document.getElementById('motorTemp').textContent = Math.round(status.motor_temp || 0);
            
            // Update GPS position
            if (status.latitude && status.longitude) {
                mowerPosition = { lat: status.latitude, lng: status.longitude };
                updateMowerPosition();
            }
            
            // Update service status indicators
            const services = ['Motors', 'Sensors', 'Vision', 'Navigation'];
            services.forEach(service => {
                // Implementation for service status updates
            });
        }
        
        function updateCameraFeed(frameData) {
            if (frameData && frameData.frame) {
                const img = document.getElementById('cameraStream');
                img.src = 'data:image/jpeg;base64,' + frameData.frame;
                document.getElementById('cameraInfo').textContent = 
                    `Frame ${frameData.frame_id} - ${new Date().toLocaleTimeString()}`;
            }
        }
        
        function updateMissionStatus(mission) {
            document.getElementById('missionState').textContent = mission.state || 'Idle';
            document.getElementById('missionProgress').textContent = `${mission.progress || 0}%`;
        }
        
        // Google Maps Integration
        function initMap() {
            map = new google.maps.Map(document.getElementById('map'), {
                zoom: 18,
                center: mowerPosition,
                mapTypeId: 'satellite',
                disableDefaultUI: true,
                zoomControl: true,
                mapTypeControl: true,
                streetViewControl: false,
                fullscreenControl: true
            });
            
            // Create mower position marker
            mowerMarker = new google.maps.Marker({
                position: mowerPosition,
                map: map,
                title: 'Mower Location',
                icon: {
                    path: google.maps.SymbolPath.CIRCLE,
                    scale: 10,
                    fillColor: '#ff4444',
                    fillOpacity: 1,
                    strokeColor: '#ffffff',
                    strokeWeight: 2
                }
            });
            
            drawingManager = new google.maps.drawing.DrawingManager({
                drawingControl: false,
                drawingMode: null,
                polygonOptions: {
                    fillColor: '#00ff00',
                    fillOpacity: 0.3,
                    strokeColor: '#00ff00',
                    strokeWeight: 2,
                    editable: true
                },
                circleOptions: {
                    fillColor: '#ff0000',
                    fillOpacity: 0.3,
                    strokeColor: '#ff0000',
                    strokeWeight: 2,
                    editable: true
                }
            });
            
            drawingManager.setMap(map);
            
            // Load existing zones
            loadZones();
            
            log('Map initialized successfully');
        }
        
        function setMapMode(mode) {
            currentMapMode = mode;
            const indicator = document.getElementById('mapModeIndicator');
            
            switch(mode) {
                case 'boundary':
                    drawingManager.setDrawingMode(google.maps.drawing.OverlayType.POLYGON);
                    drawingManager.setOptions({
                        polygonOptions: {
                            fillColor: '#00ff00',
                            fillOpacity: 0.3,
                            strokeColor: '#00ff00',
                            strokeWeight: 2,
                            editable: true
                        }
                    });
                    indicator.textContent = 'Drawing Boundary';
                    indicator.className = 'badge bg-success ms-2';
                    break;
                case 'nogo':
                    drawingManager.setDrawingMode(google.maps.drawing.OverlayType.POLYGON);
                    drawingManager.setOptions({
                        polygonOptions: {
                            fillColor: '#ff0000',
                            fillOpacity: 0.3,
                            strokeColor: '#ff0000',
                            strokeWeight: 2,
                            editable: true
                        }
                    });
                    indicator.textContent = 'Drawing No-Go Zone';
                    indicator.className = 'badge bg-danger ms-2';
                    break;
                case 'home':
                    drawingManager.setDrawingMode(google.maps.drawing.OverlayType.MARKER);
                    indicator.textContent = 'Setting Home Location';
                    indicator.className = 'badge bg-primary ms-2';
                    break;
            }
            
            log(`Map mode set to: ${mode}`);
        }
        
        function updateMowerPosition() {
            if (mowerMarker && map) {
                mowerMarker.setPosition(mowerPosition);
                // Optionally recenter map on mower position
                // map.setCenter(mowerPosition);
            }
        }
        
        // Control functions
        function setupControlListeners() {
            // Slider value updates
            document.getElementById('steering').oninput = function() {
                document.getElementById('steeringValue').textContent = this.value;
            };
            document.getElementById('throttle').oninput = function() {
                document.getElementById('throttleValue').textContent = this.value;
            };
            document.getElementById('blade').oninput = function() {
                document.getElementById('bladeValue').textContent = this.value;
            };
        }
        
        function sendMotorCommand() {
            const steering = parseInt(document.getElementById('steering').value);
            const throttle = parseInt(document.getElementById('throttle').value);
            const blade = parseInt(document.getElementById('blade').value);
            
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({
                    type: 'motor_command',
                    data: { steering, throttle, blade }
                }));
                log(`Motor command sent: S=${steering}, T=${throttle}, B=${blade}`);
            }
        }
        
        function stopMotors() {
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({ type: 'stop_motors' }));
                log('Motors stopped');
            }
        }
        
        function emergencyStop() {
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({ type: 'emergency_stop' }));
                log('🚨 EMERGENCY STOP ACTIVATED');
            }
        }
        
        function startMowing() {
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({
                    type: 'start_mission',
                    data: { type: 'mowing', zones: zones }
                }));
                log('Mowing mission started');
            }
        }
        
        function returnHome() {
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({
                    type: 'return_home',
                    data: { home: zones.home }
                }));
                log('Returning to home location');
            }
        }
        
        function stopMission() {
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({ type: 'stop_mission' }));
                log('Mission stopped');
            }
        }
        
        function generatePattern(type) {
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({
                    type: 'generate_pattern',
                    data: { pattern_type: type, boundary: zones.boundary }
                }));
                log(`Generated ${type} pattern`);
            }
        }
        
        // Zone management
        function saveZones() {
            fetch('/api/zones', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ zones: zones })
            }).then(response => response.json())
              .then(data => {
                  if (data.success) {
                      log('Zones saved successfully');
                  }
              });
        }
        
        function loadZones() {
            fetch('/api/zones')
                .then(response => response.json())
                .then(data => {
                    zones = data.zones || zones;
                    // Draw zones on map
                    log('Zones loaded');
                });
        }
        
        function clearCurrentZone() {
            if (currentMapMode) {
                zones[currentMapMode] = currentMapMode === 'home' ? null : [];
                log(`Cleared ${currentMapMode} zone`);
            }
        }
        
        // Utility functions
        function requestStatus() {
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({ type: 'get_status' }));
            }
        }
        
        function log(message) {
            const logElement = document.getElementById('activityLog');
            const timestamp = new Date().toLocaleTimeString();
            logElement.innerHTML += `<div class="text-muted">[${timestamp}] ${message}</div>`;
            logElement.scrollTop = logElement.scrollHeight;
        }
        
        function clearLog() {
            document.getElementById('activityLog').innerHTML = '';
        }
        
        // Auto-update camera feed
        setInterval(() => {
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({ type: 'get_camera_frame' }));
            }
        }, 1000);
        
        // Auto-update status
        setInterval(requestStatus, 5000);
    </script>
</body>
</html>'''
        
        # Replace API key placeholder
        return html_template.replace('{{google_maps_api_key}}', api_key)
    
    async def service_initialize(self) -> bool:
        """Initialize web service components."""
        try:
            logger.info("Modern web service initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Modern web service initialization failed: {e}")
            return False
    
    async def service_loop(self) -> None:
        """Main web service loop."""
        try:
            config = uvicorn.Config(
                self.app,
                host=self.config.services.web_host,
                port=self.config.services.web_port,
                log_level="info"
            )
            server = uvicorn.Server(config)
            await server.serve()
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Modern web service loop error: {e}")
    
    async def service_cleanup(self) -> None:
        """Cleanup web service."""
        try:
            for connection in self.active_connections:
                await connection.close()
            logger.info("Modern web service cleanup complete")
        except Exception as e:
            logger.error(f"Modern web service cleanup error: {e}")
    
    async def _handle_websocket(self, websocket: WebSocket):
        """Handle WebSocket connections."""
        await websocket.accept()
        self.active_connections.append(websocket)
        
        try:
            while True:
                data = await websocket.receive_text()
                message = json.loads(data)
                await self._handle_websocket_message(websocket, message)
        except WebSocketDisconnect:
            self.active_connections.remove(websocket)
    
    async def _handle_websocket_message(self, websocket: WebSocket, data: dict):
        """Handle incoming WebSocket message."""
        try:
            message_type = data.get("type")
            
            if message_type == "get_status":
                await self._send_status_update(websocket)
            elif message_type == "get_camera_frame":
                await self._send_camera_frame(websocket)
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
            elif message_type == "return_home":
                await self._handle_return_home(data.get("data", {}))
            elif message_type == "generate_pattern":
                await self._handle_generate_pattern(data.get("data", {}))
                
        except Exception as e:
            logger.error(f"WebSocket message handling error: {e}")
    
    async def _send_status_update(self, websocket: WebSocket):
        """Send system status update."""
        try:
            # Get system status from Redis
            if self.redis_client:
                status_data = await self.redis_client.get("system:status")
                if status_data:
                    status = json.loads(status_data)
                else:
                    status = {"state": "unknown", "battery_level": 0}
                
                # Get GPS location from sensor data
                sensor_data = await self.redis_client.get("service:sensor:data")
                if sensor_data:
                    sensor_info = json.loads(sensor_data)
                    gps_data = sensor_info.get("gps", {})
                    status["latitude"] = gps_data.get("latitude", 40.7128)
                    status["longitude"] = gps_data.get("longitude", -74.0060)
                    status["gps_fix"] = gps_data.get("fix_quality", 0) > 0
                else:
                    # Default location (NYC) if no sensor data
                    status["latitude"] = 40.7128
                    status["longitude"] = -74.0060
                    status["gps_fix"] = False
            else:
                status = {"state": "disconnected", "battery_level": 0, "latitude": 40.7128, "longitude": -74.0060, "gps_fix": False}
            
            await websocket.send_text(json.dumps({
                "type": "status",
                "data": status
            }))
        except Exception as e:
            logger.error(f"Error sending status update: {e}")
    
    async def _send_camera_frame(self, websocket: WebSocket):
        """Send camera frame."""
        try:
            # Get frame directly from vision service status in Redis
            if self.redis_client:
                # Try to get the latest frame from vision service
                vision_status = await self.redis_client.get("service:vision:status")
                if vision_status:
                    status_data = json.loads(vision_status)
                    
                    # For simulation mode, generate a simple frame
                    if self.config.simulation_mode:
                        import base64
                        import cv2
                        import numpy as np
                        
                        # Create a simple simulation frame
                        frame = np.zeros((480, 640, 3), dtype=np.uint8)
                        frame[:, :] = [0, 100, 0]  # Green background
                        
                        # Add timestamp and status info
                        cv2.putText(frame, f"SIMULATION - Frame {status_data.get('latest_frame_id', 0)}", 
                                  (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                        cv2.putText(frame, f"FPS: {status_data.get('current_fps', 0):.1f}", 
                                  (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                        cv2.putText(frame, f"Battery: 85%", 
                                  (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                        
                        # Add some random "movement"
                        import time
                        t = time.time()
                        x = int(320 + 50 * np.sin(t * 0.5))
                        y = int(240 + 30 * np.cos(t * 0.3))
                        cv2.circle(frame, (x, y), 20, (0, 0, 255), -1)
                        cv2.putText(frame, "MOWER", (x-25, y+5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
                        
                        # Encode as JPEG
                        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                        frame_b64 = base64.b64encode(buffer).decode('utf-8')
                        
                        await websocket.send_text(json.dumps({
                            "type": "camera_frame",
                            "data": {
                                "success": True,
                                "frame": frame_b64,
                                "timestamp": time.time(),
                                "frame_id": status_data.get('latest_frame_id', 0)
                            }
                        }))
                    else:
                        # For real hardware, request frame from vision service
                        await self.send_message("vision", "get_stream_frame", {})
                        
        except Exception as e:
            logger.error(f"Error sending camera frame: {e}")
    
    async def _handle_motor_command(self, data: dict):
        """Handle motor command."""
        try:
            await self.send_message("motor_control", "motor_command", data)
        except Exception as e:
            logger.error(f"Error handling motor command: {e}")
    
    async def _handle_stop_motors(self):
        """Handle stop motors command."""
        try:
            await self.send_message("motor_control", "stop_motors", {})
        except Exception as e:
            logger.error(f"Error handling stop motors: {e}")
    
    async def _handle_emergency_stop(self):
        """Handle emergency stop."""
        try:
            await self.send_message("mission_controller", "emergency_stop", {})
        except Exception as e:
            logger.error(f"Error handling emergency stop: {e}")
    
    async def _handle_start_mission(self, data: dict):
        """Handle start mission."""
        try:
            await self.send_message("mission_controller", "start_mission", data)
        except Exception as e:
            logger.error(f"Error handling start mission: {e}")
    
    async def _handle_stop_mission(self):
        """Handle stop mission."""
        try:
            await self.send_message("mission_controller", "stop_mission", {})
        except Exception as e:
            logger.error(f"Error handling stop mission: {e}")
    
    async def _handle_return_home(self, data: dict):
        """Handle return home."""
        try:
            await self.send_message("navigation", "return_home", data)
        except Exception as e:
            logger.error(f"Error handling return home: {e}")
    
    async def _handle_generate_pattern(self, data: dict):
        """Handle pattern generation."""
        try:
            await self.send_message("navigation", "generate_pattern", data)
        except Exception as e:
            logger.error(f"Error handling pattern generation: {e}")
    
    async def _get_system_status(self):
        """Get system status via API."""
        try:
            if self.redis_client:
                status_data = await self.redis_client.get("system:status")
                if status_data:
                    return json.loads(status_data)
            return {"state": "unknown", "services_online": {}}
        except Exception as e:
            logger.error(f"Error getting system status: {e}")
            return {"error": str(e)}
    
    async def _get_camera_frame(self):
        """Get camera frame via API."""
        try:
            await self.send_message("vision", "get_stream_frame", {})
            # In a real implementation, wait for response
            return {"success": True, "message": "Frame requested"}
        except Exception as e:
            logger.error(f"Error getting camera frame: {e}")
            return {"error": str(e)}
    
    def _load_zones(self) -> dict:
        """Load zones from file."""
        try:
            if self.zones_file.exists():
                with open(self.zones_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading zones: {e}")
        
        return {
            "boundary": [],
            "noGo": [],
            "home": None
        }
    
    def _save_zones(self):
        """Save zones to file."""
        try:
            with open(self.zones_file, 'w') as f:
                json.dump(self.zones, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving zones: {e}")
    
    async def handle_zone_update(self, message: ServiceMessage):
        """Handle zone updates from other services."""
        try:
            zone_data = message.data
            zone_type = zone_data.get("type")
            if zone_type in self.zones:
                self.zones[zone_type] = zone_data.get("data")
                self._save_zones()
                
                # Broadcast to connected websockets
                for websocket in self.active_connections:
                    try:
                        await websocket.send_text(json.dumps({
                            "type": "zone_update",
                            "data": zone_data
                        }))
                    except:
                        pass  # Connection might be closed
                        
        except Exception as e:
            logger.error(f"Error handling zone update: {e}")


async def main():
    """Main entry point for modern web service."""
    import sys
    from pathlib import Path
    
    # Add mower package to path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
    
    from mower.config.settings import get_config
    
    config = get_config()
    service = ModernWebService("web", config)
    
    await service.run()


if __name__ == "__main__":
    asyncio.run(main())
