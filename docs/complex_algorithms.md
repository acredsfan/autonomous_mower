# Complex Algorithms Documentation

This document provides detailed documentation for the complex algorithms used in the Autonomous Mower project.

## Path Planning Algorithms

### Coverage Path Planning

The coverage path planning algorithm is responsible for generating efficient paths that cover the entire mowing area. The algorithm uses a cellular decomposition approach to divide the mowing area into cells and then generates a path that visits each cell.

#### Algorithm Overview

```python
def generate_coverage_path(boundary, no_go_zones, cell_size):
    """
    Generate a coverage path for the mowing area.
    
    Args:
        boundary (List[Point]): List of points defining the boundary of the mowing area
        no_go_zones (List[List[Point]]): List of polygons defining no-go zones
        cell_size (float): Size of each cell in meters
        
    Returns:
        List[Point]: List of points defining the coverage path
    """
    # 1. Decompose the mowing area into cells
    cells = decompose_area(boundary, no_go_zones, cell_size)
    
    # 2. Create a graph where each cell is a node
    graph = create_cell_graph(cells)
    
    # 3. Find an optimal path through the graph (TSP)
    cell_path = solve_tsp(graph)
    
    # 4. Convert the cell path to a continuous path
    continuous_path = convert_to_continuous_path(cell_path)
    
    return continuous_path
```

#### Cellular Decomposition

The cellular decomposition algorithm divides the mowing area into cells of a specified size. The algorithm handles complex boundaries and no-go zones by:

1. Creating a grid of cells covering the entire area
2. Determining which cells are inside the boundary
3. Removing cells that intersect with no-go zones
4. Merging adjacent cells when possible to reduce the number of turns

```python
def decompose_area(boundary, no_go_zones, cell_size):
    """
    Decompose the mowing area into cells.
    
    Args:
        boundary (List[Point]): List of points defining the boundary
        no_go_zones (List[List[Point]]): List of polygons defining no-go zones
        cell_size (float): Size of each cell in meters
        
    Returns:
        List[Cell]: List of cells covering the mowing area
    """
    # 1. Find the bounding box of the boundary
    min_x, min_y, max_x, max_y = get_bounding_box(boundary)
    
    # 2. Create a grid of cells
    cells = []
    for x in range(min_x, max_x, cell_size):
        for y in range(min_y, max_y, cell_size):
            cell = Cell(x, y, cell_size)
            cells.append(cell)
    
    # 3. Filter cells that are outside the boundary
    cells = [cell for cell in cells if is_cell_in_boundary(cell, boundary)]
    
    # 4. Filter cells that intersect with no-go zones
    cells = [cell for cell in cells if not cell_intersects_no_go_zones(cell, no_go_zones)]
    
    # 5. Merge adjacent cells when possible
    cells = merge_adjacent_cells(cells)
    
    return cells
```

#### Traveling Salesman Problem (TSP)

To find an optimal path through the cells, we solve a variant of the Traveling Salesman Problem. We use a modified nearest neighbor algorithm with backtracking to find a path that minimizes the total distance traveled.

```python
def solve_tsp(graph):
    """
    Solve the Traveling Salesman Problem to find an optimal path through the cells.
    
    Args:
        graph (Dict[Cell, List[Cell]]): Graph where each cell is connected to its neighbors
        
    Returns:
        List[Cell]: Ordered list of cells defining the path
    """
    # 1. Start from the cell closest to the charging station
    start_cell = find_closest_cell_to_charging_station(graph.keys())
    
    # 2. Use nearest neighbor algorithm with backtracking
    path = [start_cell]
    unvisited = set(graph.keys()) - {start_cell}
    
    while unvisited:
        current = path[-1]
        neighbors = graph[current]
        
        # Find the nearest unvisited neighbor
        nearest = None
        min_dist = float('inf')
        
        for neighbor in neighbors:
            if neighbor in unvisited:
                dist = distance(current, neighbor)
                if dist < min_dist:
                    min_dist = dist
                    nearest = neighbor
        
        if nearest:
            path.append(nearest)
            unvisited.remove(nearest)
        else:
            # Backtrack if no unvisited neighbors
            backtrack_to = None
            for i in range(len(path) - 2, -1, -1):
                for neighbor in graph[path[i]]:
                    if neighbor in unvisited:
                        backtrack_to = i
                        break
                if backtrack_to is not None:
                    break
            
            if backtrack_to is not None:
                path = path[:backtrack_to + 1]
            else:
                # If no backtracking is possible, find the nearest unvisited cell
                current = path[-1]
                nearest = None
                min_dist = float('inf')
                
                for cell in unvisited:
                    dist = distance(current, cell)
                    if dist < min_dist:
                        min_dist = dist
                        nearest = cell
                
                path.append(nearest)
                unvisited.remove(nearest)
    
    return path
```

#### Path Optimization

After generating the initial path, we apply several optimization techniques to improve efficiency:

1. **Smoothing**: Remove unnecessary turns and zigzags
2. **Shortcutting**: Skip cells that are already covered by nearby paths
3. **Direction Optimization**: Minimize the number of direction changes

```python
def optimize_path(path, boundary, no_go_zones):
    """
    Optimize the coverage path to improve efficiency.
    
    Args:
        path (List[Point]): Initial coverage path
        boundary (List[Point]): Boundary of the mowing area
        no_go_zones (List[List[Point]]): No-go zones
        
    Returns:
        List[Point]: Optimized coverage path
    """
    # 1. Smooth the path to remove unnecessary turns
    path = smooth_path(path)
    
    # 2. Apply shortcuts where possible
    path = apply_shortcuts(path, boundary, no_go_zones)
    
    # 3. Optimize direction changes
    path = optimize_directions(path)
    
    return path
```

### Obstacle Avoidance

The obstacle avoidance algorithm is responsible for generating paths around detected obstacles. The algorithm uses a combination of potential fields and vector field histograms to navigate around obstacles while maintaining progress toward the goal.

#### Algorithm Overview

```python
def avoid_obstacle(current_position, goal_position, obstacles, safety_margin):
    """
    Generate a path around obstacles to reach the goal.
    
    Args:
        current_position (Point): Current position of the mower
        goal_position (Point): Goal position
        obstacles (List[Obstacle]): List of detected obstacles
        safety_margin (float): Safety margin around obstacles in meters
        
    Returns:
        List[Point]: Path around obstacles to the goal
    """
    # 1. Create a potential field
    potential_field = create_potential_field(current_position, goal_position, obstacles, safety_margin)
    
    # 2. Generate a path through the potential field
    path = follow_potential_field(current_position, goal_position, potential_field)
    
    # 3. Smooth the path
    path = smooth_path(path)
    
    return path
```

#### Potential Field

The potential field algorithm creates a field where:
- The goal position has an attractive force
- Obstacles have repulsive forces
- The mower follows the gradient of the field to navigate around obstacles

```python
def create_potential_field(current_position, goal_position, obstacles, safety_margin):
    """
    Create a potential field for obstacle avoidance.
    
    Args:
        current_position (Point): Current position of the mower
        goal_position (Point): Goal position
        obstacles (List[Obstacle]): List of detected obstacles
        safety_margin (float): Safety margin around obstacles in meters
        
    Returns:
        PotentialField: Potential field for navigation
    """
    # 1. Create an empty potential field
    field = PotentialField()
    
    # 2. Add attractive force toward the goal
    field.add_attractive_force(goal_position, strength=1.0)
    
    # 3. Add repulsive forces around obstacles
    for obstacle in obstacles:
        field.add_repulsive_force(obstacle.position, 
                                  radius=obstacle.radius + safety_margin,
                                  strength=2.0)
    
    return field
```

#### Vector Field Histogram

The vector field histogram algorithm divides the surrounding area into sectors and evaluates the obstacle density in each sector. It then selects the sector with the lowest obstacle density that is closest to the goal direction.

```python
def select_direction(current_position, goal_position, obstacles, safety_margin):
    """
    Select the best direction to move based on obstacle density.
    
    Args:
        current_position (Point): Current position of the mower
        goal_position (Point): Goal position
        obstacles (List[Obstacle]): List of detected obstacles
        safety_margin (float): Safety margin around obstacles in meters
        
    Returns:
        float: Direction angle in radians
    """
    # 1. Divide the surrounding area into sectors
    num_sectors = 72  # 5-degree sectors
    sectors = [0] * num_sectors
    
    # 2. Calculate obstacle density for each sector
    for obstacle in obstacles:
        distance = calculate_distance(current_position, obstacle.position)
        if distance < obstacle.radius + safety_margin:
            angle = calculate_angle(current_position, obstacle.position)
            sector_index = int((angle * 180 / math.pi) / (360 / num_sectors))
            
            # Add obstacle density inversely proportional to distance
            sectors[sector_index] += 1 / max(0.1, distance - obstacle.radius)
    
    # 3. Calculate goal direction
    goal_angle = calculate_angle(current_position, goal_position)
    goal_sector = int((goal_angle * 180 / math.pi) / (360 / num_sectors))
    
    # 4. Find the sector with lowest density closest to goal direction
    best_sector = goal_sector
    min_cost = float('inf')
    
    for i in range(num_sectors):
        # Calculate cost based on obstacle density and distance from goal direction
        density_cost = sectors[i]
        direction_cost = min(abs(i - goal_sector), num_sectors - abs(i - goal_sector)) / (num_sectors / 2)
        total_cost = density_cost + 0.5 * direction_cost
        
        if total_cost < min_cost:
            min_cost = total_cost
            best_sector = i
    
    # 5. Convert sector back to angle
    best_angle = (best_sector * (360 / num_sectors)) * (math.pi / 180)
    
    return best_angle
```

## Image Processing for Obstacle Detection

The image processing algorithm for obstacle detection uses computer vision techniques to identify obstacles in camera images. The algorithm combines traditional computer vision with machine learning for robust obstacle detection.

### Algorithm Overview

```python
def detect_obstacles_in_image(image, model):
    """
    Detect obstacles in a camera image.
    
    Args:
        image (Image): Camera image
        model (Model): Trained machine learning model for object detection
        
    Returns:
        List[Obstacle]: List of detected obstacles with position and size
    """
    # 1. Preprocess the image
    preprocessed = preprocess_image(image)
    
    # 2. Apply traditional computer vision for initial detection
    cv_detections = detect_with_cv(preprocessed)
    
    # 3. Apply machine learning model for refined detection
    ml_detections = detect_with_ml(preprocessed, model)
    
    # 4. Merge and filter detections
    detections = merge_detections(cv_detections, ml_detections)
    
    # 5. Convert detections to obstacle objects
    obstacles = []
    for detection in detections:
        position = calculate_position(detection)
        size = calculate_size(detection)
        confidence = detection.confidence
        
        if confidence > 0.7:  # Only include high-confidence detections
            obstacles.append(Obstacle(position, size))
    
    return obstacles
```

### Traditional Computer Vision

The traditional computer vision approach uses color segmentation, edge detection, and contour analysis to identify potential obstacles.

```python
def detect_with_cv(image):
    """
    Detect obstacles using traditional computer vision techniques.
    
    Args:
        image (Image): Preprocessed camera image
        
    Returns:
        List[Detection]: List of potential obstacle detections
    """
    # 1. Convert to HSV color space for better color segmentation
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    
    # 2. Create masks for different obstacle types (e.g., green for plants)
    # Exclude grass colors to focus on non-grass objects
    lower_green = np.array([35, 50, 50])
    upper_green = np.array([85, 255, 255])
    grass_mask = cv2.inRange(hsv, lower_green, upper_green)
    
    # Invert to get non-grass areas
    non_grass_mask = cv2.bitwise_not(grass_mask)
    
    # 3. Apply morphological operations to clean up the mask
    kernel = np.ones((5, 5), np.uint8)
    non_grass_mask = cv2.morphologyEx(non_grass_mask, cv2.MORPH_OPEN, kernel)
    non_grass_mask = cv2.morphologyEx(non_grass_mask, cv2.MORPH_CLOSE, kernel)
    
    # 4. Find contours in the mask
    contours, _ = cv2.findContours(non_grass_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # 5. Filter contours by size and shape
    detections = []
    for contour in contours:
        area = cv2.contourArea(contour)
        if area > 500:  # Minimum area threshold
            x, y, w, h = cv2.boundingRect(contour)
            aspect_ratio = float(w) / h
            
            # Filter out very elongated shapes (likely not obstacles)
            if 0.3 < aspect_ratio < 3.0:
                center = (x + w // 2, y + h // 2)
                size = max(w, h)
                detections.append(Detection(center, size, 0.5))  # 0.5 confidence for CV detections
    
    return detections
```

### Machine Learning Detection

The machine learning approach uses a trained object detection model (e.g., YOLO, SSD) to identify obstacles with high precision.

```python
def detect_with_ml(image, model):
    """
    Detect obstacles using a machine learning model.
    
    Args:
        image (Image): Preprocessed camera image
        model (Model): Trained machine learning model
        
    Returns:
        List[Detection]: List of obstacle detections
    """
    # 1. Prepare the image for the model
    input_tensor = prepare_input(image, model.input_shape)
    
    # 2. Run inference
    outputs = model.predict(input_tensor)
    
    # 3. Process the outputs
    detections = []
    for output in outputs:
        # Parse model-specific output format
        # This example assumes YOLO-style output
        boxes = output[:, :4]  # x, y, width, height
        scores = output[:, 4]  # confidence scores
        
        for i, score in enumerate(scores):
            if score > 0.3:  # Minimum confidence threshold
                x, y, w, h = boxes[i]
                center = (int(x), int(y))
                size = max(int(w), int(h))
                detections.append(Detection(center, size, float(score)))
    
    return detections
```

### Sensor Fusion

The sensor fusion algorithm combines data from multiple sensors (camera, ultrasonic, LiDAR) to improve obstacle detection accuracy.

```python
def fuse_sensor_data(camera_obstacles, ultrasonic_obstacles, lidar_obstacles):
    """
    Fuse obstacle data from multiple sensors.
    
    Args:
        camera_obstacles (List[Obstacle]): Obstacles detected by camera
        ultrasonic_obstacles (List[Obstacle]): Obstacles detected by ultrasonic sensors
        lidar_obstacles (List[Obstacle]): Obstacles detected by LiDAR
        
    Returns:
        List[Obstacle]: Fused list of obstacles
    """
    # 1. Create a grid representation of the environment
    grid = OccupancyGrid(resolution=0.1)  # 10cm resolution
    
    # 2. Add camera obstacles to the grid
    for obstacle in camera_obstacles:
        grid.add_obstacle(obstacle, weight=0.7)  # Camera has medium weight
    
    # 3. Add ultrasonic obstacles to the grid
    for obstacle in ultrasonic_obstacles:
        grid.add_obstacle(obstacle, weight=0.5)  # Ultrasonic has lower weight
    
    # 4. Add LiDAR obstacles to the grid
    for obstacle in lidar_obstacles:
        grid.add_obstacle(obstacle, weight=0.9)  # LiDAR has highest weight
    
    # 5. Extract fused obstacles from the grid
    fused_obstacles = grid.extract_obstacles(threshold=0.6)  # Minimum confidence threshold
    
    return fused_obstacles
```

## Conclusion

These complex algorithms form the core of the Autonomous Mower's intelligence. The path planning algorithms ensure efficient coverage of the mowing area, while the obstacle detection and avoidance algorithms ensure safe operation. The combination of traditional computer vision, machine learning, and sensor fusion provides robust obstacle detection in various environmental conditions.

The algorithms are designed to be modular and configurable, allowing for easy tuning and adaptation to different mowing environments. The plugin architecture allows for the integration of custom algorithms for specific use cases.