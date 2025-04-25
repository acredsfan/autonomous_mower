"""
Image processing optimization module for obstacle detection.

This module provides tools for optimizing image processing algorithms
used in obstacle detection to improve performance and reduce resource usage.
"""

import time
import functools
import numpy as np
import cv2
from typing import List, Dict, Any, Optional, Tuple, Callable

from mower.obstacle_detection.obstacle_detector import ObstacleDetector
from mower.utilities.logger_config import LoggerConfig

# Initialize logger
logger = LoggerConfig.get_logger(__name__)


class ImageProcessingOptimizer:
    """
    Optimizer for image processing algorithms used in obstacle detection.

    This class provides methods for optimizing image processing algorithms
    by implementing caching, downsampling, region of interest selection,
    and other performance improvements.
    """

    def __init__(self, obstacle_detector: ObstacleDetector):
        """
        Initialize the image processing optimizer.

        Args:
            obstacle_detector: The obstacle detector to optimize
        """
        self.obstacle_detector = obstacle_detector
        self.frame_cache = {}
        self.detection_cache = {}
        self.last_frame = None
        self.last_frame_hash = None
        self.frame_change_threshold = 0.05  # 5% change threshold

        # Configuration parameters
        self.enable_downsampling = True
        self.downsampling_factor = 0.5  # Reduce image size by 50%
        self.enable_roi = True  # Region of Interest processing
        self.roi_top_margin = 0.3  # Ignore top 30% of image (usually sky)
        self.enable_frame_skipping = True
        self.frame_skip_count = 0
        self.max_frame_skip = 2  # Process every 3rd frame at most

        # Apply optimizations
        self._apply_optimizations()

        logger.info("Image processing optimizer initialized")

    def _apply_optimizations(self):
        """Apply optimizations to the obstacle detector."""
        # Apply caching to expensive methods
        self._apply_caching()

        # Apply image preprocessing optimizations
        self._apply_preprocessing_optimizations()

        # Apply ML optimizations
        self._apply_ml_optimizations()

        logger.info("Applied optimizations to obstacle detector")

    def _apply_caching(self):
        """Apply caching to expensive methods."""
        # Cache the detect_obstacles method
        original_detect_obstacles = self.obstacle_detector.detect_obstacles

        @functools.wraps(original_detect_obstacles)
        def cached_detect_obstacles(frame=None):
            # If no frame is provided, use the camera
            if frame is None:
                return original_detect_obstacles(frame)

            # Check if the frame is similar to the last frame
            if self.enable_frame_skipping and self._is_similar_to_last_frame(frame):
                self.frame_skip_count += 1
                if self.frame_skip_count <= self.max_frame_skip:
                    logger.debug(
                        f"Skipping frame {self.frame_skip_count} (similar to previous)")
                    return self.detection_cache.get('last_detection', [])
            else:
                self.frame_skip_count = 0
                self._update_last_frame(frame)

            # Create a cache key based on the frame
            frame_hash = self._compute_frame_hash(frame)

            # Check if the detection is already cached
            if frame_hash in self.detection_cache:
                logger.debug(f"Using cached detection for frame {frame_hash}")
                return self.detection_cache[frame_hash]

            # Apply preprocessing optimizations if enabled
            if self.enable_downsampling or self.enable_roi:
                frame = self._preprocess_frame(frame)

            # Detect obstacles
            start_time = time.time()
            detections = original_detect_obstacles(frame)
            detection_time = time.time() - start_time

            # Cache the detection
            self.detection_cache[frame_hash] = detections
            self.detection_cache['last_detection'] = detections

            # Limit cache size
            if len(self.detection_cache) > 20:  # Keep only the 20 most recent detections
                # Remove oldest entries (except 'last_detection')
                keys_to_remove = sorted(
                    [k for k in self.detection_cache.keys() if k !=
                     'last_detection'],
                    key=lambda k: self.detection_cache[k].get('timestamp', 0)
                )[:len(self.detection_cache) - 20]
                for key in keys_to_remove:
                    del self.detection_cache[key]

            logger.debug(
                f"Obstacle detection took {detection_time:.4f} seconds")
            return detections

        # Replace the original method with the cached version
        self.obstacle_detector.detect_obstacles = cached_detect_obstacles

        # Cache the detect_drops method
        original_detect_drops = self.obstacle_detector.detect_drops

        @functools.wraps(original_detect_drops)
        def cached_detect_drops(frame=None):
            # If no frame is provided, use the camera
            if frame is None:
                return original_detect_drops(frame)

            # Create a cache key based on the frame
            frame_hash = self._compute_frame_hash(frame)
            cache_key = f"drops_{frame_hash}"

            # Check if the detection is already cached
            if cache_key in self.detection_cache:
                logger.debug(
                    f"Using cached drop detection for frame {frame_hash}")
                return self.detection_cache[cache_key]

            # Apply preprocessing optimizations if enabled
            if self.enable_downsampling or self.enable_roi:
                frame = self._preprocess_frame(frame)

            # Detect drops
            start_time = time.time()
            detections = original_detect_drops(frame)
            detection_time = time.time() - start_time

            # Cache the detection
            self.detection_cache[cache_key] = detections

            logger.debug(f"Drop detection took {detection_time:.4f} seconds")
            return detections

        # Replace the original method with the cached version
        self.obstacle_detector.detect_drops = cached_detect_drops

        logger.info("Applied caching optimizations")

    def _compute_frame_hash(self, frame) -> str:
        """
        Compute a hash for a frame to use as a cache key.

        Args:
            frame: The frame to hash

        Returns:
            A string hash of the frame
        """
        # Downsample the frame for faster hashing
        small_frame = cv2.resize(frame, (32, 32))

        # Convert to grayscale
        gray = cv2.cvtColor(small_frame, cv2.COLOR_BGR2GRAY)

        # Compute average pixel value in 4x4 blocks
        blocks = np.reshape(gray, (8, 4, 8, 4)).mean(axis=(1, 3))

        # Create a hash from the blocks
        block_hash = hash(blocks.tobytes())

        return f"frame_{block_hash}"

    def _is_similar_to_last_frame(self, frame) -> bool:
        """
        Check if a frame is similar to the last processed frame.

        Args:
            frame: The frame to check

        Returns:
            True if the frame is similar to the last frame, False otherwise
        """
        if self.last_frame is None:
            return False

        # Downsample both frames for faster comparison
        current_small = cv2.resize(frame, (32, 32))
        last_small = cv2.resize(self.last_frame, (32, 32))

        # Convert to grayscale
        current_gray = cv2.cvtColor(current_small, cv2.COLOR_BGR2GRAY)
        last_gray = cv2.cvtColor(last_small, cv2.COLOR_BGR2GRAY)

        # Calculate absolute difference
        diff = cv2.absdiff(current_gray, last_gray)

        # Calculate percentage of changed pixels
        changed_pixels = np.count_nonzero(diff > 25)  # Threshold for change
        total_pixels = current_gray.size
        change_percent = changed_pixels / total_pixels

        return change_percent < self.frame_change_threshold

    def _update_last_frame(self, frame):
        """
        Update the last processed frame.

        Args:
            frame: The frame to store
        """
        self.last_frame = frame.copy()
        self.last_frame_hash = self._compute_frame_hash(frame)

    def _preprocess_frame(self, frame):
        """
        Preprocess a frame to optimize processing.

        Args:
            frame: The frame to preprocess

        Returns:
            The preprocessed frame
        """
        # Apply downsampling if enabled
        if self.enable_downsampling:
            h, w = frame.shape[:2]
            new_h, new_w = int(
                h * self.downsampling_factor), int(w * self.downsampling_factor)
            frame = cv2.resize(frame, (new_w, new_h))

        # Apply region of interest if enabled
        if self.enable_roi:
            h, w = frame.shape[:2]
            roi_y = int(h * self.roi_top_margin)
            frame = frame[roi_y:, :]

        return frame

    def _apply_preprocessing_optimizations(self):
        """Apply image preprocessing optimizations."""
        # Optimize the _detect_obstacles_opencv method
        original_detect_opencv = self.obstacle_detector._detect_obstacles_opencv

        @functools.wraps(original_detect_opencv)
        def optimized_detect_opencv(frame):
            try:
                # Convert to grayscale
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

                # Apply Gaussian blur with larger kernel for better noise reduction
                blurred = cv2.GaussianBlur(gray, (7, 7), 0)

                # Use adaptive thresholding instead of Canny for better edge detection
                thresh = cv2.adaptiveThreshold(
                    blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                    cv2.THRESH_BINARY_INV, 11, 2
                )

                # Apply morphological operations to clean up the image
                kernel = np.ones((5, 5), np.uint8)
                thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)
                thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

                # Find contours
                contours, _ = cv2.findContours(
                    thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
                )

                # Filter contours by size and shape
                detected_objects = []
                min_area = 1000

                for contour in contours:
                    area = cv2.contourArea(contour)
                    if area > min_area:
                        # Calculate bounding box
                        x, y, w, h = cv2.boundingRect(contour)

                        # Calculate aspect ratio
                        aspect_ratio = float(w) / h if h > 0 else 0

                        # Filter out very elongated shapes (likely not obstacles)
                        if 0.3 < aspect_ratio < 3.0:
                            detected_objects.append({
                                'name': 'obstacle',
                                # Normalize score
                                'score': min(1.0, area / 10000),
                                'type': 'opencv',
                                'box': [x, y, w, h]
                            })

                return detected_objects

            except Exception as e:
                logger.error(f"Error in optimized OpenCV detection: {e}")
                # Fall back to original method
                return original_detect_opencv(frame)

        # Replace the original method with the optimized version
        self.obstacle_detector._detect_obstacles_opencv = optimized_detect_opencv

        logger.info("Applied preprocessing optimizations")

    def _apply_ml_optimizations(self):
        """Apply ML-based detection optimizations."""
        # Optimize the _detect_obstacles_ml method
        original_detect_ml = self.obstacle_detector._detect_obstacles_ml

        @functools.wraps(original_detect_ml)
        def optimized_detect_ml(frame):
            try:
                # Check if ML detection is really needed
                # If OpenCV detection finds nothing, we can skip ML detection in some cases
                opencv_detections = self.obstacle_detector._detect_obstacles_opencv(
                    frame)

                # If no objects detected by OpenCV and not every frame needs ML processing
                if not opencv_detections and self.frame_skip_count > 0:
                    logger.debug(
                        "Skipping ML detection (no OpenCV detections)")
                    return []

                # Proceed with optimized ML detection
                return original_detect_ml(frame)

            except Exception as e:
                logger.error(f"Error in optimized ML detection: {e}")
                # Fall back to original method
                return original_detect_ml(frame)

        # Replace the original method with the optimized version
        self.obstacle_detector._detect_obstacles_ml = optimized_detect_ml

        logger.info("Applied ML optimizations")

    def clear_caches(self):
        """Clear all caches."""
        self.frame_cache.clear()
        self.detection_cache.clear()
        self.last_frame = None
        self.last_frame_hash = None
        self.frame_skip_count = 0
        logger.info("Cleared all caches")


def optimize_obstacle_detector(detector: ObstacleDetector) -> ObstacleDetector:
    """
    Optimize an obstacle detector for better performance.

    Args:
        detector: The obstacle detector to optimize

    Returns:
        The optimized obstacle detector
    """
    optimizer = ImageProcessingOptimizer(detector)
    return detector


def benchmark_obstacle_detector(detector: ObstacleDetector, iterations: int = 5) -> Dict[str, Any]:
    """
    Benchmark an obstacle detector's performance.

    Args:
        detector: The obstacle detector to benchmark
        iterations: Number of iterations to run

    Returns:
        Dictionary with benchmark results
    """
    logger.info(f"Benchmarking obstacle detector for {iterations} iterations")

    # Get a test frame
    from mower.hardware.camera_instance import capture_frame
    frame = capture_frame()

    if frame is None:
        logger.error("Failed to capture frame for benchmarking")
        return {}

    # Benchmark detect_obstacles
    detect_times = []
    for i in range(iterations):
        start_time = time.time()
        detections = detector.detect_obstacles(frame)
        end_time = time.time()
        detect_times.append(end_time - start_time)

    # Benchmark detect_drops
    drop_times = []
    for i in range(iterations):
        start_time = time.time()
        drops = detector.detect_drops(frame)
        end_time = time.time()
        drop_times.append(end_time - start_time)

    # Calculate statistics
    detect_avg = np.mean(detect_times)
    detect_std = np.std(detect_times)
    detect_min = np.min(detect_times)
    detect_max = np.max(detect_times)

    drop_avg = np.mean(drop_times)
    drop_std = np.std(drop_times)
    drop_min = np.min(drop_times)
    drop_max = np.max(drop_times)

    results = {
        'detect_obstacles': {
            'avg_time': detect_avg,
            'std_time': detect_std,
            'min_time': detect_min,
            'max_time': detect_max,
            'times': detect_times
        },
        'detect_drops': {
            'avg_time': drop_avg,
            'std_time': drop_std,
            'min_time': drop_min,
            'max_time': drop_max,
            'times': drop_times
        }
    }

    logger.info(f"Obstacle detection benchmark results:")
    logger.info(f"  Average time: {detect_avg:.4f} seconds")
    logger.info(f"  Standard deviation: {detect_std:.4f} seconds")
    logger.info(f"  Min/Max time: {detect_min:.4f}/{detect_max:.4f} seconds")

    logger.info(f"Drop detection benchmark results:")
    logger.info(f"  Average time: {drop_avg:.4f} seconds")
    logger.info(f"  Standard deviation: {drop_std:.4f} seconds")
    logger.info(f"  Min/Max time: {drop_min:.4f}/{drop_max:.4f} seconds")

    return results


def compare_obstacle_detectors(
    original_detector: ObstacleDetector,
    optimized_detector: ObstacleDetector,
    iterations: int = 5
) -> Dict[str, Any]:
    """
    Compare the performance of two obstacle detectors.

    Args:
        original_detector: The original obstacle detector
        optimized_detector: The optimized obstacle detector
        iterations: Number of iterations to run

    Returns:
        Dictionary with comparison results
    """
    logger.info(f"Comparing obstacle detectors for {iterations} iterations")

    # Benchmark original detector
    original_results = benchmark_obstacle_detector(
        original_detector, iterations)

    # Benchmark optimized detector
    optimized_results = benchmark_obstacle_detector(
        optimized_detector, iterations)

    # Calculate improvement for obstacle detection
    original_detect_avg = original_results['detect_obstacles']['avg_time']
    optimized_detect_avg = optimized_results['detect_obstacles']['avg_time']
    detect_improvement = (original_detect_avg -
                          optimized_detect_avg) / original_detect_avg * 100

    # Calculate improvement for drop detection
    original_drop_avg = original_results['detect_drops']['avg_time']
    optimized_drop_avg = optimized_results['detect_drops']['avg_time']
    drop_improvement = (original_drop_avg -
                        optimized_drop_avg) / original_drop_avg * 100

    comparison = {
        'original': original_results,
        'optimized': optimized_results,
        'detect_improvement_percent': detect_improvement,
        'drop_improvement_percent': drop_improvement
    }

    logger.info(f"Performance comparison results:")
    logger.info(
        f"  Original obstacle detection time: {original_detect_avg:.4f} seconds")
    logger.info(
        f"  Optimized obstacle detection time: {optimized_detect_avg:.4f} seconds")
    logger.info(f"  Obstacle detection improvement: {detect_improvement:.2f}%")
    logger.info(
        f"  Original drop detection time: {original_drop_avg:.4f} seconds")
    logger.info(
        f"  Optimized drop detection time: {optimized_drop_avg:.4f} seconds")
    logger.info(f"  Drop detection improvement: {drop_improvement:.2f}%")

    return comparison


def run_optimization_benchmark():
    """Run a benchmark to compare original and optimized obstacle detectors."""
    logger.info("Running obstacle detection optimization benchmark")

    # Create original obstacle detector
    from mower.obstacle_detection.obstacle_detector import get_obstacle_detector
    original_detector = get_obstacle_detector()

    # Create optimized obstacle detector
    optimized_detector = get_obstacle_detector()
    optimize_obstacle_detector(optimized_detector)

    # Compare detectors
    results = compare_obstacle_detectors(original_detector, optimized_detector)

    return results


if __name__ == "__main__":
    run_optimization_benchmark()
