"""
Virtual world model for simulation.

This module provides a virtual world model for simulating the autonomous mower's
environment. It includes representations of the robot's position and orientation,
the environment (terrain, obstacles, etc.), and methods for updating and querying
the world state.
"""

import logging
import math
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

# Configure logging
logger = logging.getLogger(__name__)


class Vector2D:
    """
    2D vector class for position and velocity.
    """

    def __init__(self, x: float = 0.0, y: float = 0.0):
        """
        Initialize a 2D vector.

        Args:
            x: X coordinate
            y: Y coordinate
        """
        self.x = float(x)
        self.y = float(y)

    def __add__(self, other: "Vector2D") -> "Vector2D":
        """Add two vectors."""
        return Vector2D(self.x + other.x, self.y + other.y)

    def __sub__(self, other: "Vector2D") -> "Vector2D":
        """Subtract two vectors."""
        return Vector2D(self.x - other.x, self.y - other.y)

    def __mul__(self, scalar: float) -> "Vector2D":
        """Multiply vector by scalar."""
        return Vector2D(self.x * scalar, self.y * scalar)

    def __truediv__(self, scalar: float) -> "Vector2D":
        """Divide vector by scalar."""
        return Vector2D(self.x / scalar, self.y / scalar)

    def __repr__(self) -> str:
        """String representation of vector."""
        return f"Vector2D({self.x:.2f}, {self.y:.2f})"

    def magnitude(self) -> float:
        """Get the magnitude (length) of the vector."""
        return math.sqrt(self.x * self.x + self.y * self.y)

    def normalize(self) -> "Vector2D":
        """Get a normalized (unit) vector in the same direction."""
        mag = self.magnitude()
        if mag == 0:
            return Vector2D(0, 0)
        return Vector2D(self.x / mag, self.y / mag)

    def dot(self, other: "Vector2D") -> float:
        """Calculate the dot product with another vector."""
        return self.x * other.x + self.y * other.y

    def distance_to(self, other: "Vector2D") -> float:
        """Calculate the distance to another vector."""
        return (other - self).magnitude()

    def angle(self) -> float:
        """Get the angle of the vector in radians."""
        return math.atan2(self.y, self.x)

    def rotate(self, angle_rad: float) -> "Vector2D":
        """
        Rotate the vector by the given angle in radians.

        Args:
            angle_rad: Angle in radians to rotate by (positive is counterclockwise)

        Returns:
            Vector2D: Rotated vector
        """
        cos_angle = math.cos(angle_rad)
        sin_angle = math.sin(angle_rad)
        return Vector2D(
            self.x * cos_angle - self.y * sin_angle,
            self.x * sin_angle + self.y * cos_angle,
        )

    def to_tuple(self) -> Tuple[float, float]:
        """Convert to tuple (x, y)."""
        return (self.x, self.y)


class Obstacle:
    """
    Representation of an obstacle in the virtual world.
    """ def __init__(
        self,
        position: Vector2D,
        radius: float,
        height: float=0.0,
        obstacle_type: str="generic",
    ):
        """
        Initialize an obstacle.

        Args:
            position: Position of the obstacle
            radius: Radius of the obstacle
            height: Height of the obstacle (0.0 for flat obstacles)
            obstacle_type: Type of obstacle (e.g., "rock", "tree", "wall")
        """
        self.position = position
        self.radius = radius
        self.height = height
        self.obstacle_type = obstacle_type

    def __repr__(self) -> str:
        """String representation of obstacle."""
        return (
            f"Obstacle({self.position}, r={self.radius:.2f}, "
            f"h={self.height:.2f}, type={self.obstacle_type})"
        )

    def contains_point(self, point: Vector2D) -> bool:
        """
        Check if the obstacle contains the given point.

        Args:
            point: Point to check

        Returns:
            bool: True if the obstacle contains the point, False otherwise
        """
        return self.position.distance_to(point) <= self.radius

    def distance_to(self, point: Vector2D) -> float:
        """
        Calculate the distance from the obstacle to the given point.

        Args:
            point: Point to calculate distance to

        Returns:
            float: Distance from the obstacle to the point (negative if inside)
        """
        distance = self.position.distance_to(point) - self.radius
        return distance


class Terrain:
    """
    Representation of the terrain in the virtual world.
    """

    def __init__(self, width: float, height: float, resolution: float = 0.1):
        """
        Initialize the terrain.

        Args:
            width: Width of the terrain in meters
            height: Height of the terrain in meters
            resolution: Resolution of the terrain grid in meters
        """
        self.width = width
        self.height = height
        self.resolution = resolution

        # Create a grid for the terrain
        self.grid_width = int(width / resolution)
        self.grid_height = int(height / resolution)

        # Initialize terrain height map (flat by default)
        self.height_map = np.zeros((self.grid_width, self.grid_height))

        # Initialize terrain type map (grass by default)
        self.type_map = np.zeros(
            (self.grid_width, self.grid_height), dtype=np.int32
        )

    def get_height(self, position: Vector2D) -> float:
        """
        Get the height of the terrain at the given position.

        Args:
            position: Position to get height at

        Returns:
            float: Height of the terrain at the position
        """
        # Convert position to grid coordinates
        grid_x = int(position.x / self.resolution)
        grid_y = int(position.y / self.resolution)

        # Clamp to grid bounds
        grid_x = max(0, min(grid_x, self.grid_width - 1))
        grid_y = max(0, min(grid_y, self.grid_height - 1))

        return self.height_map[grid_x, grid_y]

    def get_slope(self, position: Vector2D) -> Tuple[float, float]:
        """
        Get the slope of the terrain at the given position.

        Args:
            position: Position to get slope at

        Returns:
            Tuple[float, float]: Slope in x and y directions (radians)
        """
        # Convert position to grid coordinates
        grid_x = int(position.x / self.resolution)
        grid_y = int(position.y / self.resolution)

        # Clamp to grid bounds
        grid_x = max(0, min(grid_x, self.grid_width - 2))
        grid_y = max(0, min(grid_y, self.grid_height - 2))

        # Calculate slope in x and y directions
        slope_x = math.atan2(
            self.height_map[grid_x + 1, grid_y]
            - self.height_map[grid_x, grid_y],
            self.resolution,
        )
        slope_y = math.atan2(
            self.height_map[grid_x, grid_y + 1]
            - self.height_map[grid_x, grid_y],
            self.resolution,
        )

        return (slope_x, slope_y)

    def get_type(self, position: Vector2D) -> int:
        """
        Get the type of terrain at the given position.

        Args:
            position: Position to get type at

        Returns:
            int: Type of terrain at the position (0 = grass, 1 = dirt, etc.)
        """
        # Convert position to grid coordinates
        grid_x = int(position.x / self.resolution)
        grid_y = int(position.y / self.resolution)

        # Clamp to grid bounds
        grid_x = max(0, min(grid_x, self.grid_width - 1))
        grid_y = max(0, min(grid_y, self.grid_height - 1))

        return self.type_map[grid_x, grid_y]

    def set_height(self, position: Vector2D, height: float) -> None:
        """
        Set the height of the terrain at the given position.

        Args:
            position: Position to set height at
            height: Height to set
        """
        # Convert position to grid coordinates
        grid_x = int(position.x / self.resolution)
        grid_y = int(position.y / self.resolution)

        # Clamp to grid bounds
        grid_x = max(0, min(grid_x, self.grid_width - 1))
        grid_y = max(0, min(grid_y, self.grid_height - 1))

        self.height_map[grid_x, grid_y] = height

    def set_type(self, position: Vector2D, terrain_type: int) -> None:
        """
        Set the type of terrain at the given position.

        Args:
            position: Position to set type at
            terrain_type: Type to set (0 = grass, 1 = dirt, etc.)
        """
        # Convert position to grid coordinates
        grid_x = int(position.x / self.resolution)
        grid_y = int(position.y / self.resolution)

        # Clamp to grid bounds
        grid_x = max(0, min(grid_x, self.grid_width - 1))
        grid_y = max(0, min(grid_y, self.grid_height - 1))

        self.type_map[grid_x, grid_y] = terrain_type


class Robot:
    """
    Representation of the robot in the virtual world.
    """

    # The Robot class has many attributes to accurately simulate physical state.
    # This is intentional for simulation fidelity.
    def __init__(
        self, position: Vector2D = Vector2D(0, 0), heading: float = 0.0
    ):
        """
        Initialize the robot.

        Args:
            position: Initial position of the robot
            heading: Initial heading of the robot in radians (0 = east, pi/2 = north)
        """
        self.position = position
        self.heading = heading
        self.velocity = Vector2D(0, 0)
        self.angular_velocity = 0.0
        self.blade_running = False
        self.blade_speed = 0.0
        self.battery_voltage = 12.5  # Volts
        self.battery_current = 0.0  # Amps
        # Left and right motor speeds (-1.0 to 1.0)
        self.motor_speeds = [0.0, 0.0]

        # Physical properties
        self.width = 0.5  # meters
        self.length = 0.7  # meters
        self.height = 0.3  # meters
        self.mass = 15.0  # kg
        self.max_speed = 1.0  # m/s
        self.max_angular_velocity = math.pi / 2  # rad/s

    def __repr__(self) -> str:
        """String representation of robot."""
        return f"Robot(pos={
            self.position}, heading={
            self.heading: .2f} rad, vel={
            self.velocity}) "

    def update(self, dt: float) -> None:
        """
        Update the robot's state based on elapsed time.

        Args:
            dt: Elapsed time in seconds
        """
        # Update position based on velocity
        self.position += self.velocity * dt

        # Update heading based on angular velocity
        self.heading += self.angular_velocity * dt

        # Normalize heading to [0, 2*pi)
        # Update battery state based on motor and blade usage
        self.heading = self.heading % (2 * math.pi)
        self._update_battery()

    def _update_battery(self) -> None:
        """
        Update the battery state based on motor and blade usage.
        """
        # Calculate current draw based on motor speeds and blade
        # 2A per motor at full speed
        motor_current = sum(abs(speed) for speed in self.motor_speeds) * 2.0
        blade_current = self.blade_speed * 5.0  # 5A at full speed

        self.battery_current = motor_current + blade_current

        # Simple battery model: voltage drops with current draw and time
        # In a real battery, this would be more complex
        voltage_drop = self.battery_current * 0.1  # 0.1V drop per amp
        self.battery_voltage = max(10.0, 12.5 - voltage_drop)

    def set_motor_speeds(self, left: float, right: float) -> None:
        """
        Set the motor speeds.

        Args:
            left: Left motor speed (-1.0 to 1.0)
            right: Right motor speed (-1.0 to 1.0)
        """
        # Clamp motor speeds to valid range
        self.motor_speeds[0] = max(-1.0, min(1.0, left))
        self.motor_speeds[1] = max(-1.0, min(1.0, right))

        # Calculate linear and angular velocity from motor speeds
        # For a differential drive robot:
        # - If both motors are the same speed, the robot moves straight
        # - If the motors are different speeds, the robot turns
        linear_speed = (
            (self.motor_speeds[0] + self.motor_speeds[1])
            / 2.0
            * self.max_speed
        )
        angular_speed = (
            (self.motor_speeds[1] - self.motor_speeds[0])
            / self.width
            * self.max_speed
        )

        # Set velocity based on heading and linear speed
        self.velocity = Vector2D(
            linear_speed * math.cos(self.heading),
            linear_speed * math.sin(self.heading),
        )

        # Set angular velocity
        self.angular_velocity = angular_speed

    def set_blade_state(self, running: bool, speed: float = 1.0) -> None:
        """
        Set the blade state.

        Args:
            running: Whether the blade is running
            speed: Blade speed (0.0 to 1.0)
        """
        self.blade_running = running
        self.blade_speed = max(0.0, min(1.0, speed)) if running else 0.0


class VirtualWorld:
    """
    Virtual world model for simulation.
    """

    # The VirtualWorld class has many attributes to support simulation
    # features.
    def __init__(self, width: float = 100.0, height: float = 100.0):
        """
        Initialize the virtual world.

        Args:
            width: Width of the world in meters
            height: Height of the world in meters
        """
        self.width = width
        self.height = height
        self.robot = Robot()
        self.terrain = Terrain(width, height)
        self.obstacles: List[Obstacle] = []
        self.time = 0.0
        self.last_update_time = time.time()
        self._lock = threading.RLock()

    def update(self, dt: Optional[float] = None) -> None:
        """
        Update the world state based on elapsed time.

        Args:
            dt: Elapsed time in seconds (if None, uses real elapsed time)
        """
        with self._lock:
            current_time = time.time()
            if dt is None:
                dt = current_time - self.last_update_time

            # Update robot
            self.robot.update(dt)

            # Check for collisions with obstacles
            self._handle_collisions()

            # Update world time
            self.time += dt
            self.last_update_time = current_time

    def _handle_collisions(self) -> None:
        """Handle collisions between the robot and obstacles."""
        for obstacle in self.obstacles:
            # Calculate distance from robot center to obstacle
            distance = obstacle.distance_to(self.robot.position)

            # If robot is colliding with obstacle, move it out
            if distance < 0:
                # Calculate direction from obstacle to robot
                direction = (
                    self.robot.position - obstacle.position
                ).normalize()

                # Move robot out of obstacle
                self.robot.position = obstacle.position + direction * (
                    obstacle.radius + 0.01
                )

                # Stop robot's movement in the collision direction
                dot_product = self.robot.velocity.dot(direction)
                if dot_product < 0:
                    # Robot is moving toward obstacle, stop it
                    self.robot.velocity = (
                        self.robot.velocity - direction * dot_product
                    )

    def add_obstacle(
        self,
        position: Vector2D,
        radius: float,
        height: float = 0.0,
        obstacle_type: str = "generic",
    ) -> None:
        """
        Add an obstacle to the world.

        Args:
            position: Position of the obstacle
            radius: Radius of the obstacle
            height: Height of the obstacle (0.0 for flat obstacles)
            obstacle_type: Type of obstacle (e.g., "rock", "tree", "wall")
        """
        with self._lock:
            self.obstacles.append(
                Obstacle(position, radius, height, obstacle_type)
            )

    def clear_obstacles(self) -> None:
        """Clear all obstacles from the world."""
        with self._lock:
            self.obstacles.clear()

    def get_obstacles_in_range(
        self, position: Vector2D, max_range: float
    ) -> List[Obstacle]:
        """
        Get all obstacles within the given range of the position.

        Args:
            position: Position to check from
            max_range: Maximum range to check

        Returns:
            List[Obstacle]: List of obstacles within range
        """
        with self._lock:
            return [
                obstacle
                for obstacle in self.obstacles
                if position.distance_to(obstacle.position)
                <= max_range + obstacle.radius
            ]

    def get_distance_to_nearest_obstacle(
        self,
        position: Vector2D,
        direction: Vector2D,
        max_range: float = float("inf"),
    ) -> Tuple[float, Optional[Obstacle]]:
        """
        Get the distance to the nearest obstacle in the given direction.

        Args:
            position: Position to check from
            direction: Direction to check in
            max_range: Maximum range to check        Returns:
            Tuple[float, Optional[Obstacle]]: Distance to nearest obstacle and the obstacle itself
                (or max_range, None if no obstacle found)
        """
        with self._lock:
            # Normalize direction
            direction = direction.normalize()

            # Check each obstacle
            min_distance = max_range
            nearest_obstacle = None

            for obstacle in self.obstacles:
                # Vector from position to obstacle
                to_obstacle = obstacle.position - position

                # Project onto direction
                projection = to_obstacle.dot(direction)

                # Skip if obstacle is behind us
                if projection <= 0:
                    continue

                # Calculate perpendicular distance
                perpendicular = (
                    to_obstacle - direction * projection
                ).magnitude()

                # Skip if obstacle is too far to the side
                if perpendicular > obstacle.radius:
                    continue

                # Calculate distance to edge of obstacle
                distance = projection - math.sqrt(
                    obstacle.radius**2 - perpendicular**2
                )

                # Update if this is the nearest obstacle
                if distance < min_distance:
                    min_distance = distance
                    nearest_obstacle = obstacle

            return min_distance, nearest_obstacle

    def get_robot_state(self) -> Dict[str, Any]:
        """
        Get the current state of the robot.

        Returns:
            Dict[str, Any]: Dictionary containing the robot state
        """
        with self._lock:
            return {
                "position": self.robot.position.to_tuple(),
                "heading": self.robot.heading,
                "velocity": self.robot.velocity.to_tuple(),
                "angular_velocity": self.robot.angular_velocity,
                "blade_running": self.robot.blade_running,
                "blade_speed": self.robot.blade_speed,
                "battery_voltage": self.robot.battery_voltage,
                "battery_current": self.robot.battery_current,
                "motor_speeds": self.robot.motor_speeds.copy(),
            }

    def set_robot_position(
        self, position: Vector2D, heading: float = None
    ) -> None:
        """
        Set the robot's position and optionally heading.

        Args:
            position: New position for the robot
            heading: New heading for the robot in radians (if None, keeps current heading)
        """
        with self._lock:
            self.robot.position = position
            if heading is not None:
                self.robot.heading = heading

    def set_robot_motor_speeds(self, left: float, right: float) -> None:
        """
        Set the robot's motor speeds.

        Args:
            left: Left motor speed (-1.0 to 1.0)
            right: Right motor speed (-1.0 to 1.0)
        """
        with self._lock:
            self.robot.set_motor_speeds(left, right)

    def set_robot_blade_state(
        self, running: bool, speed: float = 1.0
    ) -> None:
        """
        Set the robot's blade state.

        Args:
            running: Whether the blade is running
            speed: Blade speed (0.0 to 1.0)
        """
        with self._lock:
            self.robot.set_blade_state(running, speed)


# Singleton instance of the virtual world
# _world_instance is intentionally not PEP8-compliant to indicate internal
# singleton use.
_world_instance = None  # Using underscore prefix for internal use


def get_world_instance() -> VirtualWorld:
    """
    Get the singleton instance of the virtual world.

    Returns:
        VirtualWorld: The virtual world instance
    """
    # Use of 'global' is required for singleton pattern in this context.
    global _world_instance
    if _world_instance is None:
        _world_instance = VirtualWorld()
    return _world_instance


def reset_world() -> None:
    """Reset the virtual world to its initial state."""
    # Use of 'global' is required for singleton pattern in this context.
    global _world_instance
    _world_instance = VirtualWorld()
