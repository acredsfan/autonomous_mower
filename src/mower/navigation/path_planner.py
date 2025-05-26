"""
Path planning module for autonomous mower.

This
different mowing patterns and learning-based optimization.
"""

import json
import os # Added for environment variables
import requests # Added for API calls
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any # Added Dict and Any

import numpy as np

from mower.utilities.logger_config import LoggerConfigInfo

# Initialize logger
logger = LoggerConfigInfo.get_logger(__name__)

# --- Google Maps API Key Handling ---
GOOGLE_MAPS_API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY")
ELEVATION_API_URL = "https://maps.googleapis.com/maps/api/elevation/json"

if not GOOGLE_MAPS_API_KEY:
    logger.warning(
        "GOOGLE_MAPS_API_KEY environment variable not found. "
        "Elevation data will not be fetched. Path planning may be suboptimal."
    )
# --- End Google Maps API Key Handling ---


class PatternType(Enum):
    """Types of mowing patterns."""

    PARALLEL = auto()
    SPIRAL = auto()
    ZIGZAG = auto()
    CHECKERBOARD = auto()
    DIAMOND = auto()
    WAVES = auto()
    CONCENTRIC = auto()
    CUSTOM = auto()


@dataclass
class PatternConfig:
    """Configuration for mowing patterns."""

    pattern_type: PatternType
    spacing: float  # Distance between passes in meters
    angle: float  # Angle of pattern in degrees
    overlap: float  # Overlap between passes (0-1)
    start_point: Tuple[float, float]  # Starting point (lat, lon)
    boundary_points: List[Tuple[float, float]]  # Boundary points


@dataclass
class LearningConfig:
    """Configuration for learning-based optimization."""

    learning_rate: float = 0.1
    discount_factor: float = 0.9
    exploration_rate: float = 0.2
    memory_size: int = 1000
    batch_size: int = 32
    update_frequency: int = 100
    model_path: str = "models/pattern_planner.json"


class PathPlanner:
    """
    Advanced path planner with pattern generation and learning capabilities.
    """

    def __init__(
        self,
        pattern_config: PatternConfig,
        learning_config: Optional[LearningConfig] = None,
        resource_manager=None,
    ):
        """Initialize the path planner."""
        self.pattern_config = pattern_config
        self.learning_config = learning_config or LearningConfig()
        self.resource_manager = resource_manager
        self.current_path = []
        self.completed_areas = set()
        self.obstacles = []

        # Learning components
        self.q_table = {}
        self.memory = []
        self.step_count = 0

        # Load learned model if available
        if learning_config:
            self._load_model()

    def generate_path(self) -> List[Tuple[float, float]]:
        """Generate mowing path based on pattern type."""
        try:
            # If learning is enabled, use it to select pattern
            if (
                self.learning_config
                and np.random.random() < self.learning_config.exploration_rate
            ):
                self.pattern_config.pattern_type = np.random.choice(
                    list(
                        PatternType))
            elif self.learning_config:
                state = self._get_current_state()
                self.pattern_config.pattern_type = self._get_best_action(state)

            # Generate path based on selected pattern
            path = self._generate_pattern_path()

            # If learning is enabled, update based on path quality
            # if self.learning_config and path:
            state = self._get_current_state()
            # Fetch elevation data for the generated path
            elevation_data = None
            if path: # Only fetch if a path was generated
                elevation_data = get_elevation_for_path(path)

            reward = self._calculate_reward(path, elevation_data)
            self._update_q_table(
                 state, self.pattern_config.pattern_type, reward)
            self._store_experience(
                  state, self.pattern_config.pattern_type, reward)

            if self.step_count % self.learning_config.update_frequency == 0:
                 self._update_model()

            self.step_count += 1

            return path

        except ValueError as e:
            logger.error("Error generating path - value error: %s", e)
            return []
        except KeyError as e:
            logger.error("Error generating path - missing key: %s", e)
            return []
        except (TypeError, AttributeError) as e:
            logger.error("Error generating path - type error: %s", e)
            return []

    def _generate_pattern_path(self) -> List[Tuple[float, float]]:
        """Generate path based on selected pattern type."""
        try:
            pattern_generators = {
                PatternType.PARALLEL: self._generate_parallel_path,
                PatternType.SPIRAL: self._generate_spiral_path,
                PatternType.ZIGZAG: self._generate_zigzag_path,
                PatternType.CHECKERBOARD: self._generate_checkerboard_path,
                PatternType.DIAMOND: self._generate_diamond_path,
                PatternType.WAVES: self._generate_waves_path,
                PatternType.CONCENTRIC: self._generate_concentric_path,
                PatternType.CUSTOM: self._generate_custom_path, }

            generator = pattern_generators.get(
                self.pattern_config.pattern_type)
            if not generator:
                logger.error(
                    "Unknown pattern type: %s",
                    self.pattern_config.pattern_type)
                return []

            return generator()

        except ValueError as e:
            logger.error("Error generating pattern path - value error: %s", e)
            return []
        except KeyError as e:
            logger.error("Error generating pattern path - key error: %s", e)
            return []
        except (TypeError, AttributeError) as e:
            logger.error("Error generating pattern path: %s", e)
            return []

    def _generate_parallel_path(self) -> List[Tuple[float, float]]:
        """Generate parallel mowing pattern."""
        try:
            boundary = np.array(self.pattern_config.boundary_points)

            # Calculate pattern direction vector
            angle_rad = np.radians(self.pattern_config.angle)
            direction = np.array([np.cos(angle_rad), np.sin(angle_rad)])

            # Project boundary points onto pattern direction
            proj = np.dot(boundary, direction)
            min_proj, max_proj = np.min(proj), np.max(proj)

            # Calculate number of passes
            width = max_proj - min_proj
            spacing = self.pattern_config.spacing * \
                (1 - self.pattern_config.overlap)
            num_passes = int(np.ceil(width / spacing))

            # Generate pass lines
            path = []
            for i in range(num_passes):
                offset = min_proj + i * spacing
                line_start = offset * direction
                line_end = line_start + width * direction

                # Find intersection points with boundary
                intersections = self._find_boundary_intersections(
                    line_start, line_end, boundary
                )
                if intersections:
                    path.extend(intersections)

            return path

        except ValueError as e:
            logger.error("Error generating parallel path - value error: %s", e)
            return []
        except (TypeError, IndexError) as e:
            logger.error(
                "Error generating parallel path - type/index error: %s", e)
            return []
        except Exception as e:
            logger.error("Unexpected error generating parallel path: %s", e)
            return []

    def _generate_spiral_path(self) -> List[Tuple[float, float]]:
        """Generate spiral mowing pattern."""
        try:
            boundary = np.array(self.pattern_config.boundary_points)

            # Calculate center point
            center = np.mean(boundary, axis=0)

            # Calculate maximum radius
            radii = np.linalg.norm(boundary - center, axis=1)
            max_radius = np.max(radii)

            # Generate spiral points
            path = []
            r = self.pattern_config.spacing
            while r < max_radius:
                # Calculate points on spiral
                theta = np.linspace(
                    0,
                    2 * np.pi,
                    int(2 * np.pi * r / self.pattern_config.spacing),
                )
                x = center[0] + r * np.cos(theta)
                y = center[1] + r * np.sin(theta)

                # Add points to path
                path.extend(zip(x, y))

                # Increase radius
                r += self.pattern_config.spacing * (
                    1 - self.pattern_config.overlap)

            return path

        except ValueError as e:
            logger.error("Error generating spiral path - value error: %s", e)
            return []
        except (TypeError, IndexError) as e:
            logger.error(
                "Error generating spiral path - type/index error: %s", e)
            return []
        except (RuntimeError, AttributeError) as e:
            logger.error("Error generating spiral path - runtime error: %s", e)
            return []

    def _generate_zigzag_path(self) -> List[Tuple[float, float]]:
        """Generate zigzag mowing pattern."""
        try:
            boundary = np.array(self.pattern_config.boundary_points)

            # Calculate pattern direction vector
            angle_rad = np.radians(self.pattern_config.angle)
            direction = np.array([np.cos(angle_rad), np.sin(angle_rad)])

            # Project boundary points onto pattern direction
            proj = np.dot(boundary, direction)
            min_proj, max_proj = np.min(proj), np.max(proj)

            # Calculate number of passes
            width = max_proj - min_proj
            spacing = self.pattern_config.spacing * \
                (1 - self.pattern_config.overlap)
            num_passes = int(np.ceil(width / spacing))

            # Generate zigzag points
            path = []
            for i in range(num_passes):
                offset = min_proj + i * spacing
                if i % 2 == 0:
                    # Forward pass
                    line_start = offset * direction
                    line_end = line_start + width * direction
                else:
                    # Backward pass
                    line_end = offset * direction
                    line_start = line_end + width * direction

                # Find intersection points with boundary
                intersections = self._find_boundary_intersections(
                    line_start, line_end, boundary
                )

                if intersections:
                    path.extend(intersections)

            return path

        except ValueError as e:
            logger.error("Error generating zigzag path - value error: %s", e)
            return []
        except (TypeError, IndexError) as e:
            logger.error(
                "Error generating zigzag path - type/index error: %s", e)
            return []
        except (RuntimeError, AttributeError) as e:
            logger.error("Error generating zigzag path - runtime error: %s", e)
            return []

    def _generate_checkerboard_path(self) -> List[Tuple[float, float]]:
        """Generate checkerboard mowing pattern."""
        try:
            # Generate horizontal stripes
            self.pattern_config.angle = 0
            horizontal = self._generate_parallel_path()

            # Generate vertical stripes
            self.pattern_config.angle = 90
            vertical = self._generate_parallel_path()

            # Combine paths
            return horizontal + vertical

        except ValueError as e:
            logger.error(
                "Error generating checkerboard path - value error: %s", e)
            return []
        except (TypeError, IndexError) as e:
            logger.error(
                "Error generating checkerboard path - type/index error: %s", e)
            return []
        except (RuntimeError, AttributeError) as e:
            logger.error(
                "Error generating checkerboard path - runtime error: %s", e)
            return []

    def _generate_diamond_path(self) -> List[Tuple[float, float]]:
        """Generate diamond mowing pattern."""
        try:
            # Generate diagonal stripes in both directions
            self.pattern_config.angle = 45
            diagonal1 = self._generate_parallel_path()

            self.pattern_config.angle = 135
            diagonal2 = self._generate_parallel_path()

            # Combine paths
            return diagonal1 + diagonal2

        except ValueError as e:
            logger.error("Error generating diamond path - value error: %s", e)
            return []
        except (TypeError, IndexError) as e:
            logger.error(
                "Error generating diamond path - type/index error: %s", e)
            return []
        except (RuntimeError, AttributeError) as e:
            logger.error(
                "Error generating diamond path - runtime error: %s", e)
            return []

    def _generate_waves_path(self) -> List[Tuple[float, float]]:
        """Generate wave mowing pattern."""
        try:
            boundary = np.array(self.pattern_config.boundary_points)

            # Calculate bounding box
            min_x = np.min(boundary[:, 0])
            max_x = np.max(boundary[:, 0])
            min_y = np.min(boundary[:, 1])
            max_y = np.max(boundary[:, 1])

            # Generate wave points
            path = []
            y = min_y
            wave_length = self.pattern_config.spacing * 4
            amplitude = self.pattern_config.spacing

            while y <= max_y:
                x_points = np.linspace(min_x, max_x, 100)
                y_points = y + amplitude * np.sin(
                    2 * np.pi * x_points / wave_length)

                # Add points that fall within boundary
                for x, wave_y in zip(x_points, y_points):
                    point = np.array([x, wave_y])
                    if self._point_in_polygon(point, boundary):
                        path.append((x, wave_y))

                y += self.pattern_config.spacing

            return path

        except ValueError as e:
            logger.error("Error generating waves path - value error: %s", e)
            return []
        except (TypeError, IndexError) as e:
            logger.error(
                "Error generating waves path - type/index error: %s", e)
            return []
        except (RuntimeError, AttributeError) as e:
            logger.error("Error generating waves path - runtime error: %s", e)
            return []

    def _generate_concentric_path(self) -> List[Tuple[float, float]]:
        """Generate concentric mowing pattern."""
        try:
            boundary = np.array(self.pattern_config.boundary_points)

            # Calculate center point
            center = np.mean(boundary, axis=0)

            # Calculate maximum radius
            radii = np.linalg.norm(boundary - center, axis=1)
            max_radius = np.max(radii)

            # Generate concentric circles
            path = []
            r = max_radius
            while r > self.pattern_config.spacing:
                # Generate circle points
                theta = np.linspace(
                    0,
                    2 * np.pi,
                    int(2 * np.pi * r / self.pattern_config.spacing),
                )
                x = center[0] + r * np.cos(theta)
                y = center[1] + r * np.sin(theta)

                # Add points that fall within boundary
                for px, py in zip(x, y):
                    point = np.array([px, py])
                    if self._point_in_polygon(point, boundary):
                        path.append((px, py))

                r -= self.pattern_config.spacing * (
                    1 - self.pattern_config.overlap)

            return path

        except ValueError as e:
            logger.error(
                "Error generating concentric path - value error: %s", e)
            return []
        except (TypeError, IndexError) as e:
            logger.error(
                "Error generating concentric path - type/index error: %s", e)
            return []
        except (RuntimeError, AttributeError) as e:
            logger.error(
                "Error generating concentric path - runtime error: %s", e)
            return []

    def _generate_custom_path(self) -> List[Tuple[float, float]]:
        """Generate custom mowing pattern."""
        # This can be extended for custom patterns
        # For now, default to parallel pattern
        return self._generate_parallel_path()

    def _find_boundary_intersections(
        self, start: np.ndarray, end: np.ndarray, boundary: np.ndarray
    ) -> List[Tuple[float, float]]:
        """Find intersection points of line with boundary."""
        try:
            intersections = []

            # Check each boundary segment
            for i in range(len(boundary)):
                p1 = boundary[i]
                p2 = boundary[(i + 1) % len(boundary)]

                # Find intersection point
                intersection = self._line_intersection(start, end, p1, p2)
                if intersection is not None:
                    intersections.append(tuple(intersection))

            # Sort intersections by distance from start
            if intersections:
                intersections.sort(
                    key=lambda p: np.linalg.norm(
                        np.array(p) - start))

            return intersections

        except ValueError as e:
            logger.error(
                "Error finding boundary intersections - value error: %s", e)
            return []
        except (TypeError, IndexError) as e:
            logger.error(
                "Error finding boundary intersections - type/index error: %s", e)
            return []
        except (RuntimeError, AttributeError) as e:
            logger.error(
                "Error finding boundary intersections - runtime error: %s", e)
            return []

    def _line_intersection(
        self, p1: np.ndarray, p2: np.ndarray, p3: np.ndarray, p4: np.ndarray
    ) -> Optional[np.ndarray]:
        """Find intersection point of two lines."""
        try:
            # Calculate line parameters
            A1 = p2[1] - p1[1]
            B1 = p1[0] - p2[0]
            C1 = A1 * p1[0] + B1 * p1[1]

            A2 = p4[1] - p3[1]
            B2 = p3[0] - p4[0]
            C2 = A2 * p3[0] + B2 * p3[1]

            # Calculate determinant
            det = A1 * B2 - A2 * B1

            if det == 0:
                return None  # Lines are parallel

            # Calculate intersection point
            x = (B2 * C1 - B1 * C2) / det
            y = (A1 * C2 - A2 * C1) / det

            # Check if intersection is within line segments
            if (
                min(p1[0], p2[0]) <= x <= max(p1[0], p2[0])
                and min(p1[1], p2[1]) <= y <= max(p1[1], p2[1])
                and min(p3[0], p4[0]) <= x <= max(p3[0], p4[0])
                and min(p3[1], p4[1]) <= y <= max(p3[1], p4[1])
            ):
                return np.array([x, y])

            return None

        except ValueError as e:
            logger.error(
                "Error calculating line intersection - value error: %s", e)
            return None
        except (TypeError, IndexError) as e:
            logger.error(
                "Error calculating line intersection - type/index error: %s", e)
            return None
        except (ZeroDivisionError, RuntimeError) as e:
            logger.error(
                "Error calculating line intersection - runtime error: %s", e)
            return None

    def _point_in_polygon(
            self,
            point: np.ndarray,
            polygon: np.ndarray) -> bool:
        """Check if a point is inside a polygon."""
        x, y = point
        n = len(polygon)
        inside = False

        j = n - 1
        for i in range(n):
            if ((polygon[i, 1] > y) != (polygon[j, 1] > y)) and (
                x
                < (polygon[j, 0] - polygon[i, 0])
                * (y - polygon[i, 1])
                / (polygon[j, 1] - polygon[i, 1])
                + polygon[i, 0]
            ):
                inside = not inside
            j = i

        return inside

    def update_obstacle_map(
            self, obstacles: List[Tuple[float, float]]) -> None:
        """Update the obstacle map."""
        self.obstacles = obstacles

    def _get_current_state(self) -> str:
        """Get current state representation for learning."""
        try:
            # Convert boundary points to string representation
            boundary_str = "_".join(
                f"{x:.2f},{y:.2f}" for x, y in self.pattern_config.boundary_points
            )

            # Include other relevant state information
            state = (
                f"boundary_{boundary_str}_"
                f"spacing_{self.pattern_config.spacing:.2f}_"
                f"angle_{self.pattern_config.angle:.2f}"
            )

            return state
        except Exception as e:
            logger.error(f"Error getting current state: {e}")
            return "default_state"

    def _get_best_action(self, state: str) -> PatternType:
        """Get best action for current state."""
        try:
            if state not in self.q_table:
                return PatternType.PARALLEL  # Default action

            # Get action with highest Q-value
            q_values = self.q_table[state]
            return max(q_values.items(), key=lambda x: x[1])[0]
        except Exception as e:
            logger.error(f"Error getting best action: {e}")
            return PatternType.PARALLEL

    def _calculate_reward(
        self, path: List[Tuple[float, float]], elevation_data: Optional[List[float]] = None
    ) -> float:
        """Calculate reward for generated path, optionally considering elevation."""
        try:
            if not path:
                return -1.0  # Penalty for invalid path

            # Calculate path efficiency metrics
            total_distance = self._calculate_path_distance(path)
            coverage = self._calculate_coverage(path)
            smoothness = self._calculate_smoothness(path)

            # Base reward
            reward = (
                0.4 * (1.0 / (total_distance + 1e-6))  # Efficiency (add epsilon to avoid division by zero)
                + 0.4 * coverage  # Coverage
                + 0.2 * smoothness  # Smoothness
            )

            # Elevation penalty
            if elevation_data and len(elevation_data) == len(path) and len(path) > 1:
                elevation_penalty = 0.0
                max_slope_penalty = 0.0
                for i in range(len(path) - 1):
                    elevation_diff = elevation_data[i+1] - elevation_data[i]
                    distance_segment = np.linalg.norm(np.array(path[i+1]) - np.array(path[i]))
                    if distance_segment > 1e-6: # Avoid division by zero for very short segments
                        slope = elevation_diff / distance_segment
                        # Penalize upward slopes more
                        if elevation_diff > 0:
                            elevation_penalty += elevation_diff * 0.01 # Example penalty factor
                        # Penalize very steep slopes (e.g., > 20%)
                        if abs(slope) > 0.20:
                             max_slope_penalty += (abs(slope) - 0.20) * 0.1 # Example penalty factor
                
                reward -= elevation_penalty
                reward -= max_slope_penalty
                logger.debug(f"Elevation penalty applied: {elevation_penalty}, Max slope penalty: {max_slope_penalty}")

            return max(0.0, min(1.0, reward))
        except Exception as e:
            logger.error(f"Error calculating reward: {e}")
            return 0.0

    def _calculate_path_distance(
            self, path: List[Tuple[float, float]]) -> float:
        """Calculate total distance of path."""
        try:
            if len(path) < 2:
                return float("inf")

            total_distance = 0.0
            for i in range(len(path) - 1):
                p1 = np.array(path[i])
                p2 = np.array(path[i + 1])
                total_distance += np.linalg.norm(p2 - p1)

            return total_distance
        except Exception as e:
            logger.error(f"Error calculating path distance: {e}")
            return float("inf")

    def _calculate_coverage(self, path: List[Tuple[float, float]]) -> float:
        """Calculate area coverage of path."""
        try:
            if not path:
                return 0.0

            # Convert path to numpy array
            path_array = np.array(path)

            # Calculate convex hull of path points
            from scipy.spatial import ConvexHull

            hull = ConvexHull(path_array)

            # Calculate area of convex hull
            area = hull.volume

            # Calculate total area of boundary
            boundary_array = np.array(self.pattern_config.boundary_points)
            boundary_hull = ConvexHull(boundary_array)
            total_area = boundary_hull.volume

            return min(1.0, area / total_area)
        except Exception as e:
            logger.error(f"Error calculating coverage: {e}")
            return 0.0

    def _calculate_smoothness(self, path: List[Tuple[float, float]]) -> float:
        """Calculate smoothness of path."""
        try:
            if len(path) < 3:
                return 1.0

            # Calculate angles between consecutive segments
            angles = []
            for i in range(len(path) - 2):
                p1 = np.array(path[i])
                p2 = np.array(path[i + 1])
                p3 = np.array(path[i + 2])

                v1 = p2 - p1
                v2 = p3 - p2

                # Calculate angle between vectors
                cos_angle = np.dot(
                    v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
                angle = np.arccos(np.clip(cos_angle, -1.0, 1.0))
                angles.append(angle)

            # Calculate average angle deviation from straight line
            avg_angle = np.mean(angles)
            smoothness = 1.0 - (avg_angle / np.pi)

            return max(0.0, min(1.0, smoothness))
        except Exception as e:
            logger.error(f"Error calculating smoothness: {e}")
            return 0.0

    def _update_q_table(
            self,
            state: str,
            action: PatternType,
            reward: float) -> None:
        """Update Q-table with new experience."""
        try:
            if state not in self.q_table:
                self.q_table[state] = {pattern: 0.0 for pattern in PatternType}

            # Get current Q-value
            current_q = self.q_table[state][action]

            # Calculate new Q-value
            next_state = self._get_current_state()
            max_next_q = max(
                self.q_table.get(
                    next_state,
                    {}).values(),
                default=0.0)
            new_q = current_q + self.learning_config.learning_rate * (
                reward + self.learning_config.discount_factor * max_next_q - current_q)

            # Update Q-table
            self.q_table[state][action] = new_q
        except Exception as e:
            logger.error(f"Error updating Q-table: {e}")

    def _store_experience(
            self,
            state: str,
            action: PatternType,
            reward: float) -> None:
        """Store experience in replay buffer."""
        try:
            experience = {
                "state": state,
                "action": action,
                "reward": reward,
                "next_state": self._get_current_state(),
            }

            self.memory.append(experience)

            # Maintain memory size limit
            if len(self.memory) > self.learning_config.memory_size:
                self.memory.pop(0)
        except Exception as e:
            logger.error(f"Error storing experience: {e}")

    def _update_model(self) -> None:
        """Update model using experience replay."""
        try:
            if len(self.memory) < self.learning_config.batch_size:
                return

            # Sample random batch from memory
            batch = np.random.choice(
                self.memory,
                size=self.learning_config.batch_size,
                replace=False,
            )

            # Update Q-table for each experience in batch
            for experience in batch:
                self._update_q_table(
                    experience["state"],
                    experience["action"],
                    experience["reward"],
                )

            # Save updated model
            self._save_model()
        except Exception as e:
            logger.error(f"Error updating model: {e}")

    def _save_model(self) -> None:
        """Save current model to file."""
        try:
            model_path = Path(self.learning_config.model_path)
            model_path.parent.mkdir(parents=True, exist_ok=True)

            # Convert Q-table to serializable format
            q_table_serializable = {
                state: {pattern.name: value for pattern, value in actions.items()}
                for state, actions in self.q_table.items()
            }

            # Save model data
            model_data = {
                "q_table": q_table_serializable,
                "step_count": self.step_count,
            }

            with open(model_path, "w") as f:
                json.dump(model_data, f)
        except Exception as e:
            logger.error(f"Error saving model: {e}")

    def _load_model(self) -> None:
        """Load model from file."""
        try:
            model_path = Path(self.learning_config.model_path)
            if not model_path.exists():
                return

            with open(model_path, "r") as f:
                model_data = json.load(f)

            # Convert serialized Q-table back to original format
            self.q_table = {
                state: {
                    PatternType[pattern_name]: value
                    for pattern_name, value in actions.items()
                }
                for state, actions in model_data["q_table"].items()
            }

            self.step_count = model_data.get("step_count", 0)
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            self.q_table = {}
            self.step_count = 0

    def _get_model_output_shapes(self):
        """Get model output shapes for prediction."""
        return [(1, 10)]  # Example output shape

    def generate_pattern(
        self, pattern_type_str: str, settings: dict
    ) -> List[Tuple[float, float]]:
        """
        Generate a mowing pattern based on the given pattern type and settings.

        Args:
            pattern_type_str: String representation of the pattern type
            settings: Dictionary of pattern settings (spacing, angle, overlap)

        Returns:
            List of (lat, lng) coordinates representing the path
        """
        try:
            # Convert string pattern type to enum
            try:
                pattern_type = PatternType[pattern_type_str.upper()]
            except (KeyError, AttributeError):
                logger.error(f"Invalid pattern type: {pattern_type_str}")
                return []

            # Save original pattern config
            original_config = self.pattern_config

            # Create new pattern config with the requested settings
            new_config = PatternConfig(
                pattern_type=pattern_type,
                spacing=settings.get("spacing", 0.5),
                angle=settings.get("angle", 0),
                overlap=settings.get("overlap", 0.1),
                start_point=original_config.start_point,
                boundary_points=original_config.boundary_points,
            )

            # Apply the new config
            self.pattern_config = new_config

            # Generate the path
            path = self._generate_pattern_path()

            # Store the path
            self.current_path = path

            # Restore original config
            self.pattern_config = original_config

            return path

        except Exception as e:
            logger.error(f"Error in generate_pattern: {e}")
            return []

    def set_boundary_points(self, boundary_points) -> bool:
        """
        Set the boundary points for the path planner.

        Args:
            boundary_points: List of boundary points [(lat, lon), ...]

        Returns:
            bool: True if boundary points are set successfully, False otherwise
        """
        try:
            # Validate boundary points format
            if not all(
                isinstance(point, (tuple, list)) and len(point) == 2
                for point in boundary_points
            ):
                logger.error("Invalid boundary points format")
                return False

            # Update boundary points in pattern config
            self.pattern_config.boundary_points = [
                (float(lat), float(lon)) for lat, lon in boundary_points
            ]

            logger.info(
                f"Boundary points updated: {self.pattern_config.boundary_points}"
            )
            return True
        except Exception as e:
            logger.error(f"Error setting boundary points: {e}")
            return False


# --- Elevation API Function ---
def get_elevation_for_path(
    path_coordinates: List[Tuple[float, float]]
) -> Optional[List[float]]:
    """
    Fetches elevation data for a given path from Google Maps Elevation API.

    Args:
        path_coordinates: A list of (latitude, longitude) tuples.

    Returns:
        A list of elevation values (in meters) corresponding to the path coordinates,
        or None if an error occurs or the API key is missing.
    """
    if not GOOGLE_MAPS_API_KEY:
        logger.warning(
            "Cannot fetch elevation data: GOOGLE_MAPS_API_KEY is not set."
        )
        return None

    if not path_coordinates:
        return []

    # API allows multiple points separated by '|'. Max URL length is a concern for very long paths.
    # For simplicity, this example sends all points in one request.
    # Consider batching for paths with >50-100 points (approx, depends on URL length).
    # Max locations per request is 512.
    max_locations_per_request = 512
    all_elevations: List[float] = []

    for i in range(0, len(path_coordinates), max_locations_per_request):
        batch_coordinates = path_coordinates[i:i + max_locations_per_request]
        locations_str = "|".join([f"{lat},{lon}" for lat, lon in batch_coordinates])
        params = {"locations": locations_str, "key": GOOGLE_MAPS_API_KEY}

        try:
            response = requests.get(ELEVATION_API_URL, params=params, timeout=10) # Added timeout
            response.raise_for_status()  # Raises an HTTPError for bad responses (4XX or 5XX)
            data = response.json()

            if data["status"] == "OK":
                batch_elevations = [result["elevation"] for result in data["results"]]
                all_elevations.extend(batch_elevations)
            elif data["status"] == "OVER_QUERY_LIMIT":
                logger.error(
                    "Google Maps Elevation API: Query limit exceeded. "
                    "Consider reducing request frequency or upgrading your plan."
                )
                return None # Potentially return partial data or handle differently
            elif data["status"] == "REQUEST_DENIED":
                logger.error(
                    "Google Maps Elevation API: Request denied. "
                    "Check your API key and ensure the Elevation API is enabled."
                )
                return None
            elif data["status"] == "INVALID_REQUEST":
                logger.error(
                    f"Google Maps Elevation API: Invalid request. Locations: {locations_str}, Error: {data.get('error_message', '')}"
                )
                return None
            else: # UNKNOWN_ERROR or other statuses
                logger.error(
                    f"Google Maps Elevation API: Error - {data['status']}. "
                    f"Error message: {data.get('error_message', '')}"
                )
                return None

        except requests.exceptions.Timeout:
            logger.error("Google Maps Elevation API: Request timed out.")
            return None
        except requests.exceptions.HTTPError as http_err:
            err_response_text = http_err.response.text if http_err.response is not None else "No response body"
            logger.error(f"Google Maps Elevation API: HTTP error occurred: {http_err} - {err_response_text}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Google Maps Elevation API: Request failed: {e}")
            return None
        except KeyError:
            logger.error("Google Maps Elevation API: Invalid response format from API.")
            return None
        except json.JSONDecodeError:
            logger.error("Google Maps Elevation API: Could not decode JSON response.")
            return None
            
    if len(all_elevations) == len(path_coordinates):
        return all_elevations
    else:
        logger.error(
            "Mismatch between number of requested coordinates and received elevations."
        )
        return None
# --- End Elevation API Function ---
