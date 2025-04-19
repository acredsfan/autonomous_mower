/**
 * Autonomous Mower - Mowing Pattern Visualization
 * 
 * This script provides visualization of different mowing patterns
 * and coverage areas for the autonomous mower.
 */

// Global variables
let map;
let boundaryLayer;
let patternLayer;
let homeMarker;
let currentPattern = 'PARALLEL';
let currentSettings = {
    spacing: 0.5,
    angle: 0,
    overlap: 0.1
};
let boundaryPoints = [];
let patternPath = [];
let isSatelliteView = false;

// Map layers
let osmLayer;
let satelliteLayer;

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initMap();
    loadBoundaryAndSettings();
    
    // Update connection status
    if (typeof updateMapConnectionStatus === 'function') {
        updateMapConnectionStatus();
    }
});

/**
 * Initialize the map with Leaflet
 */
function initMap() {
    // Initialize the map
    map = L.map('map').setView([0, 0], 18); // Default view, will be updated
    
    // Add the OpenStreetMap tile layer
    osmLayer = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 22,
        attribution: '© OpenStreetMap contributors'
    }).addTo(map);
    
    // Add satellite layer (not added by default)
    satelliteLayer = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
        maxZoom: 22,
        attribution: 'Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community'
    });
    
    // Initialize layers for boundary and pattern
    boundaryLayer = new L.FeatureGroup();
    patternLayer = new L.FeatureGroup();
    map.addLayer(boundaryLayer);
    map.addLayer(patternLayer);
    
    // Toggle satellite/street view
    document.getElementById('toggle-satellite').addEventListener('click', function() {
        if (isSatelliteView) {
            map.removeLayer(satelliteLayer);
            osmLayer.addTo(map);
            this.innerHTML = '<i class="fas fa-satellite"></i> Toggle Satellite';
        } else {
            map.removeLayer(osmLayer);
            satelliteLayer.addTo(map);
            this.innerHTML = '<i class="fas fa-map"></i> Toggle Street';
        }
        isSatelliteView = !isSatelliteView;
    });
}

/**
 * Load boundary and settings from the server
 */
function loadBoundaryAndSettings() {
    // Load boundary points
    sendCommand('get_area', {}, function(response) {
        if (response.success && response.data && response.data.boundary_points) {
            boundaryPoints = response.data.boundary_points;
            displayBoundary(boundaryPoints);
            
            // Center map on boundary
            if (boundaryPoints.length > 0) {
                const bounds = L.latLngBounds(boundaryPoints.map(p => [p.lat, p.lng]));
                map.fitBounds(bounds);
            }
            
            // Load home location
            sendCommand('get_home', {}, function(homeResponse) {
                if (homeResponse.success && homeResponse.location) {
                    displayHomeLocation(homeResponse.location);
                }
            });
            
            // Generate initial pattern
            generatePattern(currentPattern, currentSettings);
        } else {
            showAlert('No mowing area defined. Please define an area first.', 'warning');
        }
    });
    
    // Load current settings
    sendCommand('get_settings', {}, function(response) {
        if (response.success && response.data && response.data.mowing) {
            const mowing = response.data.mowing;
            
            // Update current settings
            currentPattern = mowing.pattern || 'PARALLEL';
            currentSettings = {
                spacing: mowing.spacing || 0.5,
                angle: mowing.angle || 0,
                overlap: mowing.overlap || 0.1
            };
            
            // Update UI
            document.querySelector(`.pattern-card[data-pattern="${currentPattern}"]`)?.classList.add('active');
            
            const spacingInput = document.getElementById('patternSpacing');
            const angleInput = document.getElementById('patternAngle');
            const overlapInput = document.getElementById('patternOverlap');
            
            if (spacingInput) {
                spacingInput.value = currentSettings.spacing;
                document.getElementById('spacingValue').textContent = currentSettings.spacing + 'm';
            }
            
            if (angleInput) {
                angleInput.value = currentSettings.angle;
                document.getElementById('angleValue').textContent = currentSettings.angle + '°';
            }
            
            if (overlapInput) {
                overlapInput.value = currentSettings.overlap;
                document.getElementById('overlapValue').textContent = Math.round(currentSettings.overlap * 100) + '%';
            }
            
            // Generate pattern with loaded settings
            generatePattern(currentPattern, currentSettings);
        }
    });
}

/**
 * Display the boundary on the map
 * 
 * @param {Array} points - Array of {lat, lng} objects
 */
function displayBoundary(points) {
    // Clear previous boundary
    boundaryLayer.clearLayers();
    
    if (points.length < 3) return;
    
    // Create polygon from points
    const polygon = L.polygon(points.map(p => [p.lat, p.lng]), {
        color: 'var(--grass-dark)',
        fillColor: 'var(--grass-pale)',
        fillOpacity: 0.2,
        weight: 3
    });
    
    boundaryLayer.addLayer(polygon);
    
    // Calculate and display area
    const area = calculatePolygonArea(points);
    document.getElementById('totalArea').textContent = area.toFixed(1) + ' m²';
}

/**
 * Display home location on the map
 * 
 * @param {Object} location - {lat, lng} object
 */
function displayHomeLocation(location) {
    if (homeMarker) {
        map.removeLayer(homeMarker);
    }
    
    homeMarker = L.marker([location.lat, location.lng], {
        icon: L.divIcon({
            className: 'home-marker',
            html: '<i class="fas fa-home"></i>',
            iconSize: [30, 30],
            iconAnchor: [15, 15]
        })
    }).addTo(map);
}

/**
 * Generate and display a mowing pattern
 * 
 * @param {string} patternType - Type of pattern (PARALLEL, SPIRAL, etc.)
 * @param {Object} settings - Pattern settings (spacing, angle, overlap)
 */
function generatePattern(patternType, settings) {
    // Clear previous pattern
    patternLayer.clearLayers();
    
    if (boundaryPoints.length < 3) {
        showAlert('No mowing area defined. Please define an area first.', 'warning');
        return;
    }
    
    // Update current pattern and settings
    currentPattern = patternType;
    currentSettings = settings;
    
    // Request pattern from server
    sendCommand('generate_pattern', {
        pattern_type: patternType,
        settings: settings
    }, function(response) {
        if (response.success && response.path) {
            displayPattern(response.path, response.coverage || 0);
        } else {
            // If server-side generation fails, use client-side generation
            const path = generateClientSidePattern(patternType, settings, boundaryPoints);
            displayPattern(path, calculateCoverage(path, boundaryPoints));
        }
    });
}

/**
 * Generate a pattern on the client side (fallback if server doesn't support it)
 * 
 * @param {string} patternType - Type of pattern
 * @param {Object} settings - Pattern settings
 * @param {Array} boundary - Boundary points
 * @returns {Array} Generated path
 */
function generateClientSidePattern(patternType, settings, boundary) {
    // Convert boundary to array of [lat, lng] arrays
    const boundaryArray = boundary.map(p => [p.lat, p.lng]);
    
    // Get bounding box of boundary
    const bounds = L.latLngBounds(boundaryArray);
    const center = bounds.getCenter();
    const width = bounds.getEast() - bounds.getWest();
    const height = bounds.getNorth() - bounds.getSouth();
    
    // Generate path based on pattern type
    let path = [];
    
    switch (patternType) {
        case 'PARALLEL':
            path = generateParallelPattern(boundaryArray, settings, center, width, height);
            break;
        case 'SPIRAL':
            path = generateSpiralPattern(boundaryArray, settings, center);
            break;
        case 'ZIGZAG':
            path = generateZigzagPattern(boundaryArray, settings, center, width, height);
            break;
        case 'CHECKERBOARD':
            path = generateCheckerboardPattern(boundaryArray, settings, center, width, height);
            break;
        case 'DIAMOND':
            path = generateDiamondPattern(boundaryArray, settings, center, width, height);
            break;
        case 'WAVES':
            path = generateWavesPattern(boundaryArray, settings, center, width, height);
            break;
        case 'CONCENTRIC':
            path = generateConcentricPattern(boundaryArray, settings, center);
            break;
        default:
            path = generateParallelPattern(boundaryArray, settings, center, width, height);
    }
    
    return path;
}

/**
 * Generate a parallel pattern
 */
function generateParallelPattern(boundary, settings, center, width, height) {
    const path = [];
    const angle = settings.angle * (Math.PI / 180); // Convert to radians
    const spacing = settings.spacing * (1 - settings.overlap);
    
    // Calculate number of lines needed to cover the area
    const diagonal = Math.sqrt(width * width + height * height);
    const numLines = Math.ceil(diagonal / spacing) + 2; // Add extra lines to ensure coverage
    
    // Calculate start and end points for each line
    for (let i = -numLines / 2; i < numLines / 2; i++) {
        // Calculate offset from center
        const offset = i * spacing;
        
        // Calculate start and end points of the line
        const start = [
            center.lat + Math.sin(angle) * offset - Math.cos(angle) * diagonal / 2,
            center.lng - Math.cos(angle) * offset - Math.sin(angle) * diagonal / 2
        ];
        
        const end = [
            center.lat + Math.sin(angle) * offset + Math.cos(angle) * diagonal / 2,
            center.lng - Math.cos(angle) * offset + Math.sin(angle) * diagonal / 2
        ];
        
        // Add to path
        path.push(start);
        path.push(end);
        
        // If not the last line, add a connecting segment
        if (i < numLines / 2 - 1) {
            path.push(end);
            path.push([
                center.lat + Math.sin(angle) * (offset + spacing) + Math.cos(angle) * diagonal / 2,
                center.lng - Math.cos(angle) * (offset + spacing) + Math.sin(angle) * diagonal / 2
            ]);
        }
    }
    
    return path;
}

/**
 * Generate a spiral pattern
 */
function generateSpiralPattern(boundary, settings, center) {
    const path = [];
    const spacing = settings.spacing * (1 - settings.overlap);
    
    // Calculate maximum radius based on boundary
    let maxRadius = 0;
    for (const point of boundary) {
        const dx = point[0] - center.lat;
        const dy = point[1] - center.lng;
        const distance = Math.sqrt(dx * dx + dy * dy);
        maxRadius = Math.max(maxRadius, distance);
    }
    
    // Generate spiral
    const numTurns = Math.ceil(maxRadius / spacing);
    const angleStep = Math.PI / 36; // 5 degrees in radians
    
    // Start at center
    path.push([center.lat, center.lng]);
    
    // Generate spiral points
    for (let angle = 0; angle <= numTurns * 2 * Math.PI; angle += angleStep) {
        const radius = (angle / (2 * Math.PI)) * spacing;
        const x = center.lat + radius * Math.cos(angle);
        const y = center.lng + radius * Math.sin(angle);
        path.push([x, y]);
    }
    
    return path;
}

/**
 * Generate a zigzag pattern
 */
function generateZigzagPattern(boundary, settings, center, width, height) {
    const path = [];
    const angle = settings.angle * (Math.PI / 180); // Convert to radians
    const spacing = settings.spacing * (1 - settings.overlap);
    
    // Calculate rotated width and height
    const rotatedWidth = Math.abs(width * Math.cos(angle)) + Math.abs(height * Math.sin(angle));
    const rotatedHeight = Math.abs(width * Math.sin(angle)) + Math.abs(height * Math.cos(angle));
    
    // Calculate number of lines needed
    const numLines = Math.ceil(rotatedHeight / spacing) + 2;
    
    // Generate zigzag pattern
    let goingRight = true;
    
    for (let i = -numLines / 2; i < numLines / 2; i++) {
        // Calculate offset from center
        const offset = i * spacing;
        
        // Calculate start and end points based on direction
        let start, end;
        
        if (goingRight) {
            start = [
                center.lat + Math.sin(angle) * offset - Math.cos(angle) * rotatedWidth / 2,
                center.lng - Math.cos(angle) * offset - Math.sin(angle) * rotatedWidth / 2
            ];
            
            end = [
                center.lat + Math.sin(angle) * offset + Math.cos(angle) * rotatedWidth / 2,
                center.lng - Math.cos(angle) * offset + Math.sin(angle) * rotatedWidth / 2
            ];
        } else {
            start = [
                center.lat + Math.sin(angle) * offset + Math.cos(angle) * rotatedWidth / 2,
                center.lng - Math.cos(angle) * offset + Math.sin(angle) * rotatedWidth / 2
            ];
            
            end = [
                center.lat + Math.sin(angle) * offset - Math.cos(angle) * rotatedWidth / 2,
                center.lng - Math.cos(angle) * offset - Math.sin(angle) * rotatedWidth / 2
            ];
        }
        
        // Add to path
        path.push(start);
        path.push(end);
        
        // Toggle direction for next line
        goingRight = !goingRight;
    }
    
    return path;
}

/**
 * Generate a checkerboard pattern
 */
function generateCheckerboardPattern(boundary, settings, center, width, height) {
    const path = [];
    const angle = settings.angle * (Math.PI / 180);
    const spacing = settings.spacing * (1 - settings.overlap);
    
    // First generate horizontal lines
    const horizontalPath = generateParallelPattern(boundary, settings, center, width, height);
    path.push(...horizontalPath);
    
    // Then generate vertical lines (perpendicular to horizontal)
    const verticalSettings = {
        ...settings,
        angle: (settings.angle + 90) % 360
    };
    const verticalPath = generateParallelPattern(boundary, verticalSettings, center, width, height);
    path.push(...verticalPath);
    
    return path;
}

/**
 * Generate a diamond pattern
 */
function generateDiamondPattern(boundary, settings, center, width, height) {
    const path = [];
    const spacing = settings.spacing * (1 - settings.overlap);
    
    // Calculate maximum radius based on boundary
    let maxRadius = 0;
    for (const point of boundary) {
        const dx = point[0] - center.lat;
        const dy = point[1] - center.lng;
        const distance = Math.sqrt(dx * dx + dy * dy);
        maxRadius = Math.max(maxRadius, distance);
    }
    
    // Generate concentric diamonds
    const numDiamonds = Math.ceil(maxRadius / spacing);
    
    for (let i = 1; i <= numDiamonds; i++) {
        const radius = i * spacing;
        
        // Diamond points (clockwise from top)
        const top = [center.lat + radius, center.lng];
        const right = [center.lat, center.lng + radius];
        const bottom = [center.lat - radius, center.lng];
        const left = [center.lat, center.lng - radius];
        
        // Add diamond to path
        path.push(top);
        path.push(right);
        path.push(bottom);
        path.push(left);
        path.push(top);
        
        // Connect to next diamond if not the last one
        if (i < numDiamonds) {
            path.push([center.lat + (i + 1) * spacing, center.lng]);
        }
    }
    
    return path;
}

/**
 * Generate a waves pattern
 */
function generateWavesPattern(boundary, settings, center, width, height) {
    const path = [];
    const angle = settings.angle * (Math.PI / 180);
    const spacing = settings.spacing * (1 - settings.overlap);
    
    // Calculate rotated width and height
    const rotatedWidth = Math.abs(width * Math.cos(angle)) + Math.abs(height * Math.sin(angle));
    const rotatedHeight = Math.abs(width * Math.sin(angle)) + Math.abs(height * Math.cos(angle));
    
    // Calculate number of lines needed
    const numLines = Math.ceil(rotatedHeight / spacing) + 2;
    
    // Wave parameters
    const amplitude = spacing * 2;
    const frequency = 2 * Math.PI / rotatedWidth;
    
    for (let i = -numLines / 2; i < numLines / 2; i++) {
        // Calculate base offset from center
        const baseOffset = i * spacing;
        
        // Generate wave points
        const numPoints = 50; // Number of points per wave
        const points = [];
        
        for (let j = 0; j <= numPoints; j++) {
            const x = -rotatedWidth / 2 + j * (rotatedWidth / numPoints);
            const y = baseOffset + amplitude * Math.sin(frequency * x);
            
            // Rotate point
            const rotatedX = center.lat + x * Math.cos(angle) - y * Math.sin(angle);
            const rotatedY = center.lng + x * Math.sin(angle) + y * Math.cos(angle);
            
            points.push([rotatedX, rotatedY]);
        }
        
        // Add wave to path
        path.push(...points);
        
        // Connect to next wave if not the last one
        if (i < numLines / 2 - 1) {
            const lastPoint = points[points.length - 1];
            const nextWaveStart = [
                center.lat + (-rotatedWidth / 2) * Math.cos(angle) - ((i + 1) * spacing) * Math.sin(angle),
                center.lng + (-rotatedWidth / 2) * Math.sin(angle) + ((i + 1) * spacing) * Math.cos(angle)
            ];
            path.push(lastPoint);
            path.push(nextWaveStart);
        }
    }
    
    return path;
}

/**
 * Generate a concentric pattern
 */
function generateConcentricPattern(boundary, settings, center) {
    const path = [];
    const spacing = settings.spacing * (1 - settings.overlap);
    
    // Calculate maximum radius based on boundary
    let maxRadius = 0;
    for (const point of boundary) {
        const dx = point[0] - center.lat;
        const dy = point[1] - center.lng;
        const distance = Math.sqrt(dx * dx + dy * dy);
        maxRadius = Math.max(maxRadius, distance);
    }
    
    // Generate concentric circles
    const numCircles = Math.ceil(maxRadius / spacing);
    
    for (let i = 1; i <= numCircles; i++) {
        const radius = i * spacing;
        const numPoints = Math.max(20, Math.floor(2 * Math.PI * radius / spacing));
        const angleStep = 2 * Math.PI / numPoints;
        
        // Generate circle points
        const circlePoints = [];
        for (let angle = 0; angle < 2 * Math.PI; angle += angleStep) {
            const x = center.lat + radius * Math.cos(angle);
            const y = center.lng + radius * Math.sin(angle);
            circlePoints.push([x, y]);
        }
        
        // Close the circle
        circlePoints.push(circlePoints[0]);
        
        // Add circle to path
        path.push(...circlePoints);
        
        // Connect to next circle if not the last one
        if (i < numCircles) {
            path.push(circlePoints[0]);
            path.push([
                center.lat + (i + 1) * spacing,
                center.lng
            ]);
        }
    }
    
    return path;
}

/**
 * Display a mowing pattern on the map
 * 
 * @param {Array} path - Array of [lat, lng] points
 * @param {number} coverage - Coverage percentage (0-100)
 */
function displayPattern(path, coverage) {
    // Clear previous pattern
    patternLayer.clearLayers();
    
    if (!path || path.length === 0) return;
    
    // Create polyline from path
    const polyline = L.polyline(path, {
        color: 'var(--grass-medium)',
        weight: 3,
        opacity: 0.8,
        dashArray: '5, 5'
    });
    
    patternLayer.addLayer(polyline);
    
    // Store path for calculations
    patternPath = path;
    
    // Calculate and display statistics
    updatePatternStatistics(path, coverage);
}

/**
 * Update pattern statistics display
 * 
 * @param {Array} path - The mowing path
 * @param {number} coverage - Coverage percentage
 */
function updatePatternStatistics(path, coverage) {
    // Calculate path length
    const pathLength = calculatePathLength(path);
    document.getElementById('pathLength').textContent = pathLength.toFixed(1) + ' m';
    
    // Update coverage display
    const coveragePercent = Math.round(coverage * 100);
    document.getElementById('coveragePercent').textContent = coveragePercent + '%';
    document.getElementById('coverageProgress').style.width = coveragePercent + '%';
    
    // Calculate estimated time (assuming 0.5 m/s speed)
    const speed = 0.5; // m/s
    const timeSeconds = pathLength / speed;
    const timeMinutes = timeSeconds / 60;
    document.getElementById('estimatedTime').textContent = timeMinutes.toFixed(1) + ' min';
    
    // Estimate battery usage (rough estimate)
    const batteryPerHour = 20; // % per hour
    const batteryUsage = (timeMinutes / 60) * batteryPerHour;
    document.getElementById('batteryUsage').textContent = batteryUsage.toFixed(1) + '%';
    
    // Calculate efficiency (coverage per meter)
    const area = calculatePolygonArea(boundaryPoints);
    const efficiency = (coverage * area) / pathLength;
    document.getElementById('efficiency').textContent = efficiency.toFixed(2) + ' m²/m';
}

/**
 * Calculate the length of a path
 * 
 * @param {Array} path - Array of [lat, lng] points
 * @returns {number} Path length in meters
 */
function calculatePathLength(path) {
    if (!path || path.length < 2) return 0;
    
    let length = 0;
    for (let i = 1; i < path.length; i++) {
        const p1 = L.latLng(path[i-1][0], path[i-1][1]);
        const p2 = L.latLng(path[i][0], path[i][1]);
        length += p1.distanceTo(p2);
    }
    
    return length;
}

/**
 * Calculate the area of a polygon
 * 
 * @param {Array} points - Array of {lat, lng} objects
 * @returns {number} Area in square meters
 */
function calculatePolygonArea(points) {
    if (!points || points.length < 3) return 0;
    
    // Convert to Leaflet latLngs
    const latLngs = points.map(p => L.latLng(p.lat, p.lng));
    
    // Use Leaflet's geodesic area calculation
    return L.GeometryUtil.geodesicArea(latLngs);
}

/**
 * Calculate coverage percentage of a path within a boundary
 * 
 * @param {Array} path - Array of [lat, lng] points
 * @param {Array} boundary - Array of {lat, lng} objects
 * @returns {number} Coverage percentage (0-1)
 */
function calculateCoverage(path, boundary) {
    // This is a simplified calculation
    // In a real implementation, this would use a more sophisticated algorithm
    
    // For now, we'll use a rough estimate based on path length and area
    const pathLength = calculatePathLength(path);
    const area = calculatePolygonArea(boundary);
    
    // Estimate coverage based on path length and spacing
    const coverage = Math.min(1.0, (pathLength * currentSettings.spacing) / area);
    
    return coverage;
}

/**
 * Update the mowing pattern
 * 
 * @param {string} patternType - The pattern type to use
 */
function updateMowingPattern(patternType) {
    generatePattern(patternType, currentSettings);
}

/**
 * Apply pattern settings
 * 
 * @param {Object} settings - The settings to apply
 */
function applyPatternSettings(settings) {
    generatePattern(currentPattern, settings);
}

// Make functions available globally
window.updateMowingPattern = updateMowingPattern;
window.applyPatternSettings = applyPatternSettings;