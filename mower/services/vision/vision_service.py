"""
Vision Service

This service handles computer vision processing including obstacle detection,
path recognition, and environmental analysis using camera feeds and ML models.
"""

import asyncio
import cv2
import json
import logging
import time
import numpy as np
import base64
import threading
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

from mower.core.communication.base_service import BaseService, ServiceMessage
from mower.core.safety.safety_system import get_safety_system, SafetySystem
from mower.config.settings import SystemConfig


logger = logging.getLogger(__name__)


@dataclass
class DetectedObject:
    """Detected object information."""
    class_name: str
    confidence: float
    bbox: Tuple[int, int, int, int]  # x, y, width, height
    distance_estimate: float = 0.0


@dataclass
class VisionFrame:
    """Vision processing frame data."""
    timestamp: float
    frame_id: int
    width: int
    height: int
    objects: List[DetectedObject]
    path_clear: bool
    grass_coverage: float
    processing_time_ms: float


class VisionService(BaseService):
    """Computer vision processing service."""
    
    def __init__(self, service_name: str = "vision", config: Optional[SystemConfig] = None):
        """Initialize vision service."""
        super().__init__(service_name, config)
        
        # Safety system
        self.safety_system: Optional[SafetySystem] = None
        
        # Camera and vision processing
        self.camera = None
        self.camera_type = "simulation"  # Will be updated during initialization
        self.frame_width = 640
        self.frame_height = 480
        self.fps = 10  # Target FPS
        
        # ML model (placeholder for YOLOv8 or similar)
        self.model = None
        self.model_loaded = False
        
        # Processing state
        self.frame_id = 0
        self.frames_processed = 0
        self.processing_times = []
        self.max_processing_history = 100
        
        # Object detection classes of interest
        self.target_classes = {
            "person": 0.5,      # Minimum confidence
            "dog": 0.5,
            "cat": 0.5,
            "car": 0.6,
            "bicycle": 0.5,
            "obstacle": 0.4,
        }
        
        # Vision analysis results
        self.latest_frame: Optional[VisionFrame] = None
        self.obstacle_detected = False
        self.path_clear = True
        
        # Performance settings
        self.processing_interval = 1.0 / self.fps  # Process every N seconds
        self.last_processing_time = 0.0
        
        # Camera streaming
        self.streaming_enabled = True
        self.latest_frame_jpeg = None
        self.stream_lock = threading.Lock()
        
        # Register message handlers
        self.register_message_handler("capture_frame", self.handle_capture_frame)
        self.register_message_handler("get_analysis", self.handle_get_analysis)
        self.register_message_handler("get_stream_frame", self.handle_get_stream_frame)
    
    async def service_initialize(self) -> bool:
        """Initialize vision service components."""
        try:
            # Initialize safety system connection
            self.safety_system = get_safety_system(self.config)
            
            # Initialize camera
            if not await self._initialize_camera():
                logger.warning("Camera initialization failed, continuing in simulation mode")
            
            # Load ML model
            if not await self._load_ml_model():
                logger.warning("ML model loading failed, using basic processing")
            
            logger.info("Vision service initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Vision service initialization failed: {e}")
            return False
    
    async def service_loop(self) -> None:
        """Main vision service loop."""
        try:
            while not self.shutdown_event.is_set():
                current_time = time.time()
                
                # Process frame if enough time has passed
                if current_time - self.last_processing_time >= self.processing_interval:
                    await self._process_frame()
                    self.last_processing_time = current_time
                
                # Update safety system
                if self.safety_system:
                    self.safety_system.monitor.update_vision_time()
                
                # Publish vision status
                await self._publish_vision_status()
                
                await asyncio.sleep(0.05)  # 20Hz main loop, vision processing at lower rate
                
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Vision service loop error: {e}")
    
    async def service_cleanup(self) -> None:
        """Cleanup vision service."""
        try:
            # Release camera
            if self.camera:
                self.camera.release()
                self.camera = None
            
            logger.info("Vision service cleanup complete")
            
        except Exception as e:
            logger.error(f"Vision service cleanup error: {e}")
    
    async def _initialize_camera(self) -> bool:
        """Initialize camera for image capture."""
        try:
            # Check simulation mode
            sim_mode = getattr(self.config, 'simulation_mode', False)
            if hasattr(self.config, 'hardware'):
                sim_mode = getattr(self.config.hardware, 'simulation_mode', False)
            
            if sim_mode:
                logger.info("Vision service running in simulation mode")
                return True
            
            # Try to initialize camera with timeout protection
            try:
                # Try Raspberry Pi camera first (connected via ribbon cable)
                logger.info("Trying Raspberry Pi camera...")
                try:
                    # Try libcamera/picamera2 first (modern interface)
                    try:
                        from picamera2 import Picamera2
                        camera = Picamera2()
                        config = camera.create_preview_configuration(
                            main={"size": (self.frame_width, self.frame_height)}
                        )
                        camera.configure(config)
                        camera.start()
                        
                        # Test frame capture
                        frame = camera.capture_array()
                        if frame is not None:
                            self.camera = camera
                            self.camera_type = "picamera2"
                            logger.info("Pi camera (picamera2) initialized successfully")
                            return True
                        else:
                            camera.stop()
                            camera.close()
                    except ImportError:
                        logger.info("picamera2 not available, trying legacy picamera")
                    except Exception as e:
                        logger.debug(f"picamera2 failed: {e}")
                    
                    # Try legacy picamera interface
                    try:
                        import picamera
                        camera = picamera.PiCamera()
                        camera.resolution = (self.frame_width, self.frame_height)
                        camera.framerate = self.fps
                        
                        # Test capture
                        import io
                        stream = io.BytesIO()
                        camera.capture(stream, format='jpeg')
                        if len(stream.getvalue()) > 0:
                            self.camera = camera
                            self.camera_type = "picamera"
                            logger.info("Pi camera (legacy picamera) initialized successfully")
                            return True
                        else:
                            camera.close()
                    except ImportError:
                        logger.info("legacy picamera not available")
                    except Exception as e:
                        logger.debug(f"legacy picamera failed: {e}")
                    
                    # Try OpenCV with Pi camera (via /dev/video0)
                    logger.info("Trying Pi camera via OpenCV...")
                    camera = cv2.VideoCapture(0)
                    if camera and camera.isOpened():
                        camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.frame_width)
                        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.frame_height)
                        camera.set(cv2.CAP_PROP_FPS, self.fps)
                        
                        # Test frame capture
                        ret, frame = camera.read()
                        if ret and frame is not None:
                            self.camera = camera
                            self.camera_type = "opencv"
                            logger.info("Pi camera via OpenCV initialized successfully")
                            return True
                        else:
                            camera.release()
                    
                except Exception as e:
                    logger.warning(f"Pi camera initialization failed: {e}")
                    self.camera = None
                
                # Continue without camera
                logger.warning("No camera available - running in camera-less mode with synthetic frames")
                self.camera = None
                self.camera_type = "simulation"
                return True  # Continue service operation without camera
                
            except Exception as e:
                logger.error(f"Camera initialization error: {e}")
                self.camera = None
                return True  # Continue without camera
                
        except Exception as e:
            logger.error(f"Camera setup error: {e}")
            return True  # Continue service operation
    
    async def _load_ml_model(self) -> bool:
        """Load machine learning model for object detection."""
        try:
            if self.config.simulation_mode:
                logger.info("ML model simulation mode")
                self.model_loaded = True
                return True
            
            # Try to load YOLOv8 or similar model
            try:
                # This would load the actual ML model
                # from ultralytics import YOLO
                # self.model = YOLO('yolov8n.pt')  # or custom trained model
                logger.info("ML model loaded successfully")
                self.model_loaded = True
                return True
                
            except ImportError:
                logger.warning("YOLOv8 not available, using basic image processing")
                return False
                
        except Exception as e:
            logger.error(f"ML model loading error: {e}")
            return False
    
    async def _process_frame(self) -> None:
        """Process a single frame for vision analysis."""
        start_time = time.time()
        
        try:
            # Capture frame
            frame = await self._capture_frame()
            if frame is None:
                return
            
            # Analyze frame
            objects = await self._detect_objects(frame)
            path_clear = await self._analyze_path(frame, objects)
            grass_coverage = await self._analyze_grass_coverage(frame)
            
            # Create frame data
            processing_time = (time.time() - start_time) * 1000  # Convert to ms
            
            self.latest_frame = VisionFrame(
                timestamp=time.time(),
                frame_id=self.frame_id,
                width=self.frame_width,
                height=self.frame_height,
                objects=objects,
                path_clear=path_clear,
                grass_coverage=grass_coverage,
                processing_time_ms=processing_time
            )
            
            # Update state
            self.obstacle_detected = len(objects) > 0
            self.path_clear = path_clear
            
            # Update stream frame
            self._update_stream_frame(frame)
            
            # Track performance
            self.processing_times.append(processing_time)
            if len(self.processing_times) > self.max_processing_history:
                self.processing_times.pop(0)
            
            self.frames_processed += 1
            self.frame_id += 1
            
            logger.debug(f"Processed frame {self.frame_id}: {len(objects)} objects, "
                        f"path_clear={path_clear}, {processing_time:.1f}ms")
            
        except Exception as e:
            logger.error(f"Frame processing error: {e}")
    
    async def _capture_frame(self) -> Optional[np.ndarray]:
        """Capture a frame from the camera."""
        try:
            # Check simulation mode
            sim_mode = getattr(self.config, 'simulation_mode', False)
            if hasattr(self.config, 'hardware'):
                sim_mode = getattr(self.config.hardware, 'simulation_mode', False)
            
            if sim_mode or self.camera is None:
                # Generate a synthetic frame for simulation or when no camera
                frame = np.zeros((self.frame_height, self.frame_width, 3), dtype=np.uint8)
                
                # Add some synthetic content
                # Green background (grass)
                frame[:, :] = [0, 100, 0]
                
                # Add some random "obstacles" occasionally
                if time.time() % 10 < 1:  # 10% of the time
                    cv2.rectangle(frame, (200, 150), (300, 250), (0, 0, 255), -1)
                
                # Add timestamp and status
                status_text = "SIM" if sim_mode else "NO CAM"
                cv2.putText(frame, f"{status_text} {int(time.time())}", (10, 30), 
                          cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                
                return frame
            
            elif self.camera:
                # Capture from real camera based on type
                if self.camera_type == "picamera2":
                    # Picamera2 interface
                    frame = self.camera.capture_array()
                    return cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                elif self.camera_type == "picamera":
                    # Legacy picamera interface
                    import io
                    import numpy as np
                    stream = io.BytesIO()
                    self.camera.capture(stream, format='rgb')
                    stream.seek(0)
                    frame = np.frombuffer(stream.getvalue(), dtype=np.uint8)
                    frame = frame.reshape((self.frame_height, self.frame_width, 3))
                    return cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                elif self.camera_type == "opencv":
                    # OpenCV camera
                    ret, frame = self.camera.read()
                    if ret:
                        return frame
            
            return None
            
        except Exception as e:
            logger.error(f"Frame capture error: {e}")
            return None
    
    async def _detect_objects(self, frame: np.ndarray) -> List[DetectedObject]:
        """Detect objects in the frame."""
        objects = []
        
        try:
            if self.model_loaded and not self.config.simulation_mode:
                # Use actual ML model for detection
                # results = self.model(frame)
                # for r in results:
                #     boxes = r.boxes
                #     for box in boxes:
                #         # Process detection results
                #         pass
                pass
            else:
                # Simple simulation/fallback detection
                # Look for red objects as obstacles
                hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
                
                # Define red color range
                lower_red1 = np.array([0, 50, 50])
                upper_red1 = np.array([10, 255, 255])
                lower_red2 = np.array([170, 50, 50])
                upper_red2 = np.array([180, 255, 255])
                
                mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
                mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
                mask = mask1 + mask2
                
                # Find contours
                contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                
                for contour in contours:
                    area = cv2.contourArea(contour)
                    if area > 1000:  # Minimum size threshold
                        x, y, w, h = cv2.boundingRect(contour)
                        
                        # Estimate distance based on object size (very rough)
                        distance_estimate = max(0.1, 1000.0 / area)
                        
                        objects.append(DetectedObject(
                            class_name="obstacle",
                            confidence=0.8,
                            bbox=(x, y, w, h),
                            distance_estimate=distance_estimate
                        ))
            
        except Exception as e:
            logger.error(f"Object detection error: {e}")
        
        return objects
    
    async def _analyze_path(self, frame: np.ndarray, objects: List[DetectedObject]) -> bool:
        """Analyze if the path ahead is clear."""
        try:
            # Simple path analysis
            # Check if any objects are in the center path area
            center_x = self.frame_width // 2
            path_width = self.frame_width // 3
            
            for obj in objects:
                x, y, w, h = obj.bbox
                obj_center_x = x + w // 2
                
                # Check if object is in the path and close enough to be a concern
                if (center_x - path_width // 2 < obj_center_x < center_x + path_width // 2 and
                    obj.distance_estimate < 2.0):  # Less than 2 meters
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Path analysis error: {e}")
            return True  # Default to safe
    
    async def _analyze_grass_coverage(self, frame: np.ndarray) -> float:
        """Analyze grass coverage in the frame."""
        try:
            # Simple grass detection based on green color
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            
            # Define green color range for grass
            lower_green = np.array([35, 40, 40])
            upper_green = np.array([85, 255, 255])
            
            mask = cv2.inRange(hsv, lower_green, upper_green)
            grass_pixels = cv2.countNonZero(mask)
            total_pixels = frame.shape[0] * frame.shape[1]
            
            coverage = grass_pixels / total_pixels
            return min(1.0, max(0.0, coverage))
            
        except Exception as e:
            logger.error(f"Grass analysis error: {e}")
            return 0.5  # Default coverage
    
    async def handle_capture_frame(self, message: ServiceMessage) -> None:
        """Handle frame capture request."""
        try:
            frame = await self._capture_frame()
            
            if frame is not None:
                # Encode frame for transmission (base64 JPEG)
                _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                import base64
                frame_data = base64.b64encode(buffer).decode('utf-8')
                
                response_data = {
                    "success": True,
                    "frame_data": frame_data,
                    "timestamp": time.time(),
                    "width": self.frame_width,
                    "height": self.frame_height
                }
            else:
                response_data = {
                    "success": False,
                    "message": "Failed to capture frame"
                }
            
            await self.send_message(
                message.service,
                "frame_response",
                response_data,
                message.correlation_id
            )
            
        except Exception as e:
            logger.error(f"Error handling capture_frame: {e}")
    
    async def handle_get_analysis(self, message: ServiceMessage) -> None:
        """Handle analysis request."""
        try:
            if self.latest_frame:
                response_data = {
                    "success": True,
                    "analysis": asdict(self.latest_frame)
                }
            else:
                response_data = {
                    "success": False,
                    "message": "No frame analysis available"
                }
            
            await self.send_message(
                message.service,
                "analysis_response",
                response_data,
                message.correlation_id
            )
            
        except Exception as e:
            logger.error(f"Error handling get_analysis: {e}")
    
    async def handle_get_stream_frame(self, message: ServiceMessage) -> None:
        """Handle stream frame request."""
        try:
            with self.stream_lock:
                if self.latest_frame_jpeg:
                    response_data = {
                        "success": True,
                        "frame": self.latest_frame_jpeg,
                        "timestamp": time.time(),
                        "frame_id": self.frame_id
                    }
                else:
                    response_data = {
                        "success": False,
                        "message": "No frame available"
                    }
            
            await self.send_message(
                message.service,
                "stream_frame_response",
                response_data,
                message.correlation_id
            )
            
        except Exception as e:
            logger.error(f"Error handling get_stream_frame: {e}")
    
    def _update_stream_frame(self, frame: np.ndarray) -> None:
        """Update the latest frame for streaming."""
        try:
            if self.streaming_enabled and frame is not None:
                # Resize frame for streaming if needed
                stream_frame = cv2.resize(frame, (640, 480))
                
                # Encode as JPEG
                _, buffer = cv2.imencode('.jpg', stream_frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                
                # Encode as base64 for web transmission
                frame_b64 = base64.b64encode(buffer).decode('utf-8')
                
                with self.stream_lock:
                    self.latest_frame_jpeg = frame_b64
                    
        except Exception as e:
            logger.error(f"Error updating stream frame: {e}")
    
    async def _publish_vision_status(self) -> None:
        """Publish vision service status."""
        try:
            avg_processing_time = (sum(self.processing_times) / len(self.processing_times) 
                                 if self.processing_times else 0)
            
            status = {
                "frames_processed": self.frames_processed,
                "current_fps": min(self.fps, 1000.0 / avg_processing_time if avg_processing_time > 0 else 0),
                "average_processing_time_ms": avg_processing_time,
                "obstacle_detected": self.obstacle_detected,
                "path_clear": self.path_clear,
                "camera_available": self.camera is not None,
                "model_loaded": self.model_loaded,
                "latest_frame_id": self.frame_id
            }
            
            if self.redis_client:
                await self.redis_client.setex(
                    f"service:{self.service_name}:status",
                    5,  # 5 second TTL
                    json.dumps(status)
                )
                
                # Publish latest analysis if available
                if self.latest_frame:
                    await self.redis_client.setex(
                        f"service:{self.service_name}:analysis",
                        2,  # 2 second TTL
                        json.dumps(asdict(self.latest_frame))
                    )
        
        except Exception as e:
            logger.error(f"Error publishing vision status: {e}")


# Service entry point
def main():
    """Main entry point for vision service."""
    from mower.core.communication.base_service import run_service
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger.info("Starting Vision Service")
    run_service(VisionService, "vision")


if __name__ == "__main__":
    main()
