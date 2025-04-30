/**
 * Autonomous Mower - Mowing Pattern Visualization
 *
 * This script provides visualization of different mowing patterns
 * and coverage areas for the autonomous mower.
 */

// Global variables
let map;
let drawingManager;
let boundaryLayer;
let patternLayer;
let noGoZones = [];
let homeMarker;
let geocoder;
let currentPattern = "PARALLEL";
let currentSettings = {
  spacing: 0.5,
  angle: 0,
  overlap: 0.1,
};
let boundaryPoints = [];
let patternPath = [];
let isSatelliteView = false;
let isDrawingMode = false;
let currentDrawingMode = null;

// Initialize when DOM is loaded
document.addEventListener("DOMContentLoaded", function () {
  initMap();
  loadBoundaryAndSettings();
  initMapControls();

  // Update connection status
  if (typeof updateMapConnectionStatus === "function") {
    updateMapConnectionStatus();
  }
});

/**
 * Initialize the map with Google Maps
 */
function initMap() {
  // Default center (will be updated with boundary data)
  const defaultCenter = { lat: 37.7749, lng: -122.4194 }; // San Francisco as default

  // Initialize geocoder for address searches
  geocoder = new google.maps.Geocoder();

  // Initialize the map - default to satellite view
  map = new google.maps.Map(document.getElementById("map"), {
    zoom: 18,
    center: defaultCenter,
    mapTypeId: google.maps.MapTypeId.SATELLITE, // Default to satellite view
    mapTypeControl: true,
    mapTypeControlOptions: {
      style: google.maps.MapTypeControlStyle.HORIZONTAL_BAR,
      position: google.maps.ControlPosition.TOP_RIGHT,
      mapTypeIds: [
        google.maps.MapTypeId.ROADMAP,
        google.maps.MapTypeId.SATELLITE,
        google.maps.MapTypeId.HYBRID,
        google.maps.MapTypeId.TERRAIN,
      ],
    },
    streetViewControl: false,
    fullscreenControl: true,
  });

  // Set satellite view flag
  isSatelliteView = true;

  // Update button text to reflect current state
  document.getElementById("toggle-satellite").innerHTML =
    '<i class="fas fa-map"></i> Toggle Street';

  // Initialize the drawing manager for polygon drawing
  drawingManager = new google.maps.drawing.DrawingManager({
    drawingMode: null,
    drawingControl: false,
    polygonOptions: {
      editable: true,
      strokeColor: "#689F38",
      strokeOpacity: 1.0,
      strokeWeight: 3,
      fillColor: "#8BC34A",
      fillOpacity: 0.2,
    },
    markerOptions: {
      icon: {
        path: google.maps.SymbolPath.CIRCLE,
        scale: 10,
        fillColor: "#4285F4",
        fillOpacity: 1,
        strokeColor: "#FFFFFF",
        strokeWeight: 2,
      },
    },
  });

  drawingManager.setMap(map);

  // Initialize arrays to store boundary and pattern paths
  boundaryLayer = [];
  patternLayer = [];

  // Event listener for when polygon drawing is complete
  google.maps.event.addListener(
    drawingManager,
    "polygoncomplete",
    function (polygon) {
      // After polygon is drawn, exit drawing mode
      drawingManager.setDrawingMode(null);
      isDrawingMode = false;

      if (currentDrawingMode === "boundary") {
        // Clear existing boundary
        clearBoundary();
        boundaryLayer.push(polygon);

        // Extract points from polygon
        boundaryPoints = [];
        const path = polygon.getPath();
        for (let i = 0; i < path.getLength(); i++) {
          const point = path.getAt(i);
          boundaryPoints.push({
            lat: point.lat(),
            lng: point.lng(),
          });
        }

        // Listen for changes in the polygon
        google.maps.event.addListener(path, "set_at", updateBoundaryPoints);
        google.maps.event.addListener(path, "insert_at", updateBoundaryPoints);

        // Calculate and display area
        const area = calculatePolygonArea(boundaryPoints);
        document.getElementById("totalArea").textContent =
          area.toFixed(1) + " m²";

        // Generate pattern based on new boundary
        generatePattern(currentPattern, currentSettings);
      } else if (currentDrawingMode === "nogo") {
        // Add to no-go zones
        noGoZones.push(polygon);

        // Set different color for no-go zones
        polygon.setOptions({
          strokeColor: "#FF0000",
          fillColor: "#FF0000",
        });
      }
    }
  );

  // Event listener for marker placement (home location)
  google.maps.event.addListener(
    drawingManager,
    "markercomplete",
    function (marker) {
      // Set home marker
      if (homeMarker) {
        homeMarker.setMap(null);
      }
      homeMarker = marker;

      // Exit drawing mode
      drawingManager.setDrawingMode(null);
      isDrawingMode = false;
    }
  );

  // Toggle satellite/street view
  document
    .getElementById("toggle-satellite")
    .addEventListener("click", function () {
      if (isSatelliteView) {
        map.setMapTypeId(google.maps.MapTypeId.ROADMAP);
        this.innerHTML = '<i class="fas fa-satellite"></i> Toggle Satellite';
      } else {
        map.setMapTypeId(google.maps.MapTypeId.SATELLITE);
        this.innerHTML = '<i class="fas fa-map"></i> Toggle Street';
      }
      isSatelliteView = !isSatelliteView;
    });
}

/**
 * Update boundary points when the polygon is edited
 */
function updateBoundaryPoints() {
  if (boundaryLayer.length === 0) return;

  const polygon = boundaryLayer[0];
  const path = polygon.getPath();

  boundaryPoints = [];
  for (let i = 0; i < path.getLength(); i++) {
    const point = path.getAt(i);
    boundaryPoints.push({
      lat: point.lat(),
      lng: point.lng(),
    });
  }

  // Update area calculation
  const area = calculatePolygonArea(boundaryPoints);
  document.getElementById("totalArea").textContent = area.toFixed(1) + " m²";

  // Regenerate pattern
  generatePattern(currentPattern, currentSettings);
}

/**
 * Initialize map control buttons
 */
function initMapControls() {
  // Draw boundary button
  document
    .getElementById("draw-boundary")
    .addEventListener("click", function () {
      currentDrawingMode = "boundary";
      startDrawingMode(google.maps.drawing.OverlayType.POLYGON);
    });

  // Draw no-go zone button
  document.getElementById("draw-nogo").addEventListener("click", function () {
    currentDrawingMode = "nogo";
    startDrawingMode(google.maps.drawing.OverlayType.POLYGON);
  });

  // Set home location button
  document.getElementById("set-home").addEventListener("click", function () {
    currentDrawingMode = "home";
    startDrawingMode(google.maps.drawing.OverlayType.MARKER);
  });

  // Clear all button
  document.getElementById("clear-all").addEventListener("click", function () {
    clearBoundary();
    clearNoGoZones();
    clearHomeLocation();
    boundaryPoints = [];
    document.getElementById("totalArea").textContent = "-- m²";
    // Clear pattern
    clearPattern();
  });

  // Address search button
  document
    .getElementById("search-address")
    .addEventListener("click", function () {
      const address = document.getElementById("address-input").value;
      if (address) {
        geocodeAddress(address);
      }
    });

  // Also allow pressing Enter in the input field
  document
    .getElementById("address-input")
    .addEventListener("keypress", function (e) {
      if (e.key === "Enter") {
        const address = this.value;
        if (address) {
          geocodeAddress(address);
        }
      }
    });

  // Save map changes button
  document
    .getElementById("save-map-changes")
    .addEventListener("click", function () {
      saveMapChanges();
    });
}

/**
 * Start drawing mode on the map
 */
function startDrawingMode(drawingMode) {
  // Exit any current drawing mode
  drawingManager.setDrawingMode(null);

  // Set new drawing mode
  drawingManager.setDrawingMode(drawingMode);
  isDrawingMode = true;
}

/**
 * Clear the yard boundary
 */
function clearBoundary() {
  for (let i = 0; i < boundaryLayer.length; i++) {
    boundaryLayer[i].setMap(null);
  }
  boundaryLayer = [];
}

/**
 * Clear all no-go zones
 */
function clearNoGoZones() {
  for (let i = 0; i < noGoZones.length; i++) {
    noGoZones[i].setMap(null);
  }
  noGoZones = [];
}

/**
 * Clear home location marker
 */
function clearHomeLocation() {
  if (homeMarker) {
    homeMarker.setMap(null);
    homeMarker = null;
  }
}

/**
 * Clear the pattern layer
 */
function clearPattern() {
  for (let i = 0; i < patternLayer.length; i++) {
    patternLayer[i].setMap(null);
  }
  patternLayer = [];
  patternPath = [];
}

/**
 * Geocode an address and center the map on it
 */
function geocodeAddress(address) {
  geocoder.geocode({ address: address }, function (results, status) {
    if (status === "OK") {
      map.setCenter(results[0].geometry.location);
      map.setZoom(18); // Zoom in to show the property

      // Show a temporary marker at the address
      const marker = new google.maps.Marker({
        map: map,
        position: results[0].geometry.location,
        animation: google.maps.Animation.DROP,
      });

      // Remove marker after a few seconds
      setTimeout(() => {
        marker.setMap(null);
      }, 3000);

      showAlert(
        "Address found! You can now draw your yard boundary.",
        "success"
      );
    } else {
      showAlert("Geocode was not successful: " + status, "warning");
    }
  });
}

/**
 * Save all map changes (boundary, no-go zones, home location)
 */
function saveMapChanges() {
  // Save boundary
  if (boundaryPoints.length >= 3) {
    sendCommand(
      "save_area",
      { coordinates: boundaryPoints },
      function (response) {
        if (response.success) {
          showAlert("Yard boundary saved successfully!", "success");
        } else {
          showAlert(
            "Failed to save yard boundary: " +
              (response.error || "Unknown error"),
            "danger"
          );
        }
      }
    );
  } else {
    showAlert("Please draw a valid yard boundary before saving.", "warning");
    return;
  }

  // Save home location
  if (homeMarker) {
    const homeLocation = {
      lat: homeMarker.getPosition().lat(),
      lng: homeMarker.getPosition().lng(),
    };

    sendCommand("set_home", { location: homeLocation }, function (response) {
      if (response.success) {
        showAlert("Home location saved successfully!", "success");
      } else {
        showAlert(
          "Failed to save home location: " +
            (response.error || "Unknown error"),
          "danger"
        );
      }
    });
  }

  // Save no-go zones
  if (noGoZones.length > 0) {
    const zones = noGoZones.map((zone) => {
      const path = zone.getPath();
      const points = [];
      for (let i = 0; i < path.getLength(); i++) {
        points.push({
          lat: path.getAt(i).lat(),
          lng: path.getAt(i).lng(),
        });
      }
      return points;
    });

    sendCommand("save_no_go_zones", { zones: zones }, function (response) {
      if (response.success) {
        showAlert("No-go zones saved successfully!", "success");
      } else {
        showAlert(
          "Failed to save no-go zones: " + (response.error || "Unknown error"),
          "danger"
        );
      }
    });
  }
}

/**
 * Load boundary and settings from the server
 */
function loadBoundaryAndSettings() {
  // Load boundary points
  sendCommand("get_area", {}, function (response) {
    if (response.success && response.data && response.data.boundary_points) {
      boundaryPoints = response.data.boundary_points;
      displayBoundary(boundaryPoints);

      // Center map on boundary
      if (boundaryPoints.length > 0) {
        const bounds = new google.maps.LatLngBounds();
        boundaryPoints.forEach((p) => {
          bounds.extend({ lat: parseFloat(p.lat), lng: parseFloat(p.lng) });
        });
        map.fitBounds(bounds);
      }

      // Generate initial pattern
      generatePattern(currentPattern, currentSettings);
    }
  });

  // Load home location
  sendCommand("get_home", {}, function (response) {
    if (response.success && response.location) {
      displayHomeLocation(response.location);
    }
  });

  // Load no-go zones
  sendCommand("get_boundary", {}, function (response) {
    if (response.success && response.no_go_zones) {
      displayNoGoZones(response.no_go_zones);
    }
  });

  // Load current settings
  sendCommand("get_settings", {}, function (response) {
    if (response.success && response.data && response.data.mowing) {
      const mowing = response.data.mowing;

      // Update current settings
      currentPattern = mowing.pattern || "PARALLEL";
      currentSettings = {
        spacing: mowing.spacing || 0.5,
        angle: mowing.angle || 0,
        overlap: mowing.overlap || 0.1,
      };

      // Update UI
      document
        .querySelector(`.pattern-card[data-pattern="${currentPattern}"]`)
        ?.classList.add("active");

      const spacingInput = document.getElementById("patternSpacing");
      const angleInput = document.getElementById("patternAngle");
      const overlapInput = document.getElementById("patternOverlap");

      if (spacingInput) {
        spacingInput.value = currentSettings.spacing;
        document.getElementById("spacingValue").textContent =
          currentSettings.spacing + "m";
      }

      if (angleInput) {
        angleInput.value = currentSettings.angle;
        document.getElementById("angleValue").textContent =
          currentSettings.angle + "°";
      }

      if (overlapInput) {
        overlapInput.value = currentSettings.overlap;
        document.getElementById("overlapValue").textContent =
          Math.round(currentSettings.overlap * 100) + "%";
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
  clearBoundary();

  if (!points || points.length < 3) return;

  // Convert points to Google Maps LatLng objects
  const path = points.map((p) => {
    return {
      lat: typeof p.lat === "number" ? p.lat : parseFloat(p.lat),
      lng: typeof p.lng === "number" ? p.lng : parseFloat(p.lng),
    };
  });

  // Create polygon from points
  const polygon = new google.maps.Polygon({
    paths: path,
    strokeColor: "#689F38",
    strokeOpacity: 1.0,
    strokeWeight: 3,
    fillColor: "#8BC34A",
    fillOpacity: 0.2,
    map: map,
    editable: true,
  });

  // Add to boundary layer
  boundaryLayer.push(polygon);

  // Add listeners for boundary editing
  google.maps.event.addListener(
    polygon.getPath(),
    "set_at",
    updateBoundaryPoints
  );
  google.maps.event.addListener(
    polygon.getPath(),
    "insert_at",
    updateBoundaryPoints
  );

  // Fit map to boundary
  const bounds = new google.maps.LatLngBounds();
  path.forEach((point) => bounds.extend(point));
  map.fitBounds(bounds);

  // Calculate and display area
  const area = calculatePolygonArea(points);
  document.getElementById("totalArea").textContent = area.toFixed(1) + " m²";
}

/**
 * Display no-go zones on the map
 *
 * @param {Array} zones - Array of arrays of {lat, lng} objects
 */
function displayNoGoZones(zones) {
  // Clear previous no-go zones
  clearNoGoZones();

  if (!zones || zones.length === 0) return;

  zones.forEach((zonePoints) => {
    if (zonePoints.length < 3) return;

    // Convert points to Google Maps LatLng objects
    const path = zonePoints.map((p) => {
      return {
        lat: typeof p.lat === "number" ? p.lat : parseFloat(p.lat),
        lng: typeof p.lng === "number" ? p.lng : parseFloat(p.lng),
      };
    });

    // Create polygon for no-go zone
    const polygon = new google.maps.Polygon({
      paths: path,
      strokeColor: "#FF0000",
      strokeOpacity: 1.0,
      strokeWeight: 2,
      fillColor: "#FF0000",
      fillOpacity: 0.3,
      map: map,
      editable: true,
    });

    // Add to no-go zones array
    noGoZones.push(polygon);
  });
}

/**
 * Display home location on the map
 *
 * @param {Object} location - {lat, lng} object
 */
function displayHomeLocation(location) {
  if (homeMarker) {
    homeMarker.setMap(null);
  }

  // Create a marker for home
  homeMarker = new google.maps.Marker({
    position: {
      lat:
        typeof location.lat === "number"
          ? location.lat
          : parseFloat(location.lat),
      lng:
        typeof location.lng === "number"
          ? location.lng
          : parseFloat(location.lng),
    },
    map: map,
    icon: {
      path: google.maps.SymbolPath.CIRCLE,
      scale: 10,
      fillColor: "#4285F4",
      fillOpacity: 1,
      strokeColor: "#FFFFFF",
      strokeWeight: 2,
    },
    title: "Home Location",
    draggable: true, // Allow the home marker to be draggable
  });
}

/**
 * Generate and display a mowing pattern
 *
 * @param {string} patternType - Type of pattern (PARALLEL, SPIRAL, etc.)
 * @param {Object} settings - Pattern settings (spacing, angle, overlap)
 */
function generatePattern(patternType, settings) {
  // Clear previous pattern
  for (let i = 0; i < patternLayer.length; i++) {
    patternLayer[i].setMap(null);
  }
  patternLayer = [];

  if (boundaryPoints.length < 3) {
    showAlert(
      "No mowing area defined. Please define an area first.",
      "warning"
    );
    return;
  }

  // Update current pattern and settings
  currentPattern = patternType;
  currentSettings = settings;

  // Request pattern from server
  sendCommand(
    "generate_pattern",
    {
      pattern_type: patternType,
      settings: settings,
    },
    function (response) {
      if (response.success && response.path) {
        displayPattern(response.path, response.coverage || 0);
      } else {
        // If server-side generation fails, use client-side generation
        const path = generateClientSidePattern(
          patternType,
          settings,
          boundaryPoints
        );
        displayPattern(path, calculateCoverage(path, boundaryPoints));
      }
    }
  );
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
  const boundaryArray = boundary.map((p) => [p.lat, p.lng]);

  // Get bounding box of boundary using Google Maps
  const bounds = new google.maps.LatLngBounds();
  boundary.forEach((p) => {
    bounds.extend({
      lat: typeof p.lat === "number" ? p.lat : parseFloat(p.lat),
      lng: typeof p.lng === "number" ? p.lng : parseFloat(p.lng),
    });
  });

  // Calculate center and dimensions
  const northEast = bounds.getNorthEast();
  const southWest = bounds.getSouthWest();
  const center = {
    lat: (northEast.lat() + southWest.lat()) / 2,
    lng: (northEast.lng() + southWest.lng()) / 2,
  };
  const width = northEast.lng() - southWest.lng();
  const height = northEast.lat() - southWest.lat();

  // Generate path based on pattern type
  let path = [];

  switch (patternType) {
    case "PARALLEL":
      path = generateParallelPattern(
        boundaryArray,
        settings,
        center,
        width,
        height
      );
      break;
    case "SPIRAL":
      path = generateSpiralPattern(boundaryArray, settings, center);
      break;
    case "ZIGZAG":
      path = generateZigzagPattern(
        boundaryArray,
        settings,
        center,
        width,
        height
      );
      break;
    case "CHECKERBOARD":
      path = generateCheckerboardPattern(
        boundaryArray,
        settings,
        center,
        width,
        height
      );
      break;
    case "DIAMOND":
      path = generateDiamondPattern(
        boundaryArray,
        settings,
        center,
        width,
        height
      );
      break;
    case "WAVES":
      path = generateWavesPattern(
        boundaryArray,
        settings,
        center,
        width,
        height
      );
      break;
    case "CONCENTRIC":
      path = generateConcentricPattern(boundaryArray, settings, center);
      break;
    default:
      path = generateParallelPattern(
        boundaryArray,
        settings,
        center,
        width,
        height
      );
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
      center.lat + Math.sin(angle) * offset - (Math.cos(angle) * diagonal) / 2,
      center.lng - Math.cos(angle) * offset - (Math.sin(angle) * diagonal) / 2,
    ];

    const end = [
      center.lat + Math.sin(angle) * offset + (Math.cos(angle) * diagonal) / 2,
      center.lng - Math.cos(angle) * offset + (Math.sin(angle) * diagonal) / 2,
    ];

    // Add to path
    path.push(start);
    path.push(end);

    // If not the last line, add a connecting segment
    if (i < numLines / 2 - 1) {
      path.push(end);
      path.push([
        center.lat +
          Math.sin(angle) * (offset + spacing) +
          (Math.cos(angle) * diagonal) / 2,
        center.lng -
          Math.cos(angle) * (offset + spacing) +
          (Math.sin(angle) * diagonal) / 2,
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
  const rotatedWidth =
    Math.abs(width * Math.cos(angle)) + Math.abs(height * Math.sin(angle));
  const rotatedHeight =
    Math.abs(width * Math.sin(angle)) + Math.abs(height * Math.cos(angle));

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
        center.lat +
          Math.sin(angle) * offset -
          (Math.cos(angle) * rotatedWidth) / 2,
        center.lng -
          Math.cos(angle) * offset -
          (Math.sin(angle) * rotatedWidth) / 2,
      ];

      end = [
        center.lat +
          Math.sin(angle) * offset +
          (Math.cos(angle) * rotatedWidth) / 2,
        center.lng -
          Math.cos(angle) * offset +
          (Math.sin(angle) * rotatedWidth) / 2,
      ];
    } else {
      start = [
        center.lat +
          Math.sin(angle) * offset +
          (Math.cos(angle) * rotatedWidth) / 2,
        center.lng -
          Math.cos(angle) * offset +
          (Math.sin(angle) * rotatedWidth) / 2,
      ];

      end = [
        center.lat +
          Math.sin(angle) * offset -
          (Math.cos(angle) * rotatedWidth) / 2,
        center.lng -
          Math.cos(angle) * offset -
          (Math.sin(angle) * rotatedWidth) / 2,
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
function generateCheckerboardPattern(
  boundary,
  settings,
  center,
  width,
  height
) {
  const path = [];
  const angle = settings.angle * (Math.PI / 180);
  const spacing = settings.spacing * (1 - settings.overlap);

  // First generate horizontal lines
  const horizontalPath = generateParallelPattern(
    boundary,
    settings,
    center,
    width,
    height
  );
  path.push(...horizontalPath);

  // Then generate vertical lines (perpendicular to horizontal)
  const verticalSettings = {
    ...settings,
    angle: (settings.angle + 90) % 360,
  };
  const verticalPath = generateParallelPattern(
    boundary,
    verticalSettings,
    center,
    width,
    height
  );
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
  const rotatedWidth =
    Math.abs(width * Math.cos(angle)) + Math.abs(height * Math.sin(angle));
  const rotatedHeight =
    Math.abs(width * Math.sin(angle)) + Math.abs(height * Math.cos(angle));

  // Calculate number of lines needed
  const numLines = Math.ceil(rotatedHeight / spacing) + 2;

  // Wave parameters
  const amplitude = spacing * 2;
  const frequency = (2 * Math.PI) / rotatedWidth;

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
        center.lat +
          (-rotatedWidth / 2) * Math.cos(angle) -
          (i + 1) * spacing * Math.sin(angle),
        center.lng +
          (-rotatedWidth / 2) * Math.sin(angle) +
          (i + 1) * spacing * Math.cos(angle),
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
    const numPoints = Math.max(
      20,
      Math.floor((2 * Math.PI * radius) / spacing)
    );
    const angleStep = (2 * Math.PI) / numPoints;

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
      path.push([center.lat + (i + 1) * spacing, center.lng]);
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
  for (let i = 0; i < patternLayer.length; i++) {
    patternLayer[i].setMap(null);
  }
  patternLayer = [];

  if (!path || path.length === 0) return;

  // Convert path to Google Maps LatLng objects
  const googlePath = path.map((point) => {
    return new google.maps.LatLng(
      typeof point[0] === "number" ? point[0] : parseFloat(point[0]),
      typeof point[1] === "number" ? point[1] : parseFloat(point[1])
    );
  });

  // Create polyline from path
  const polyline = new google.maps.Polyline({
    path: googlePath,
    strokeColor: "#8BC34A", // grass-medium color
    strokeWeight: 3,
    strokeOpacity: 0.8,
    icons: [
      {
        icon: {
          path: "M 0,-1 0,1",
          strokeOpacity: 1,
          scale: 3,
        },
        offset: "0",
        repeat: "10px",
      },
    ],
    map: map,
  });

  // Add to pattern layer
  patternLayer.push(polyline);

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
  document.getElementById("pathLength").textContent =
    pathLength.toFixed(1) + " m";

  // Update coverage display
  const coveragePercent = Math.round(coverage * 100);
  document.getElementById("coveragePercent").textContent =
    coveragePercent + "%";
  document.getElementById("coverageProgress").style.width =
    coveragePercent + "%";

  // Calculate estimated time (assuming 0.5 m/s speed)
  const speed = 0.5; // m/s
  const timeSeconds = pathLength / speed;
  const timeMinutes = timeSeconds / 60;
  document.getElementById("estimatedTime").textContent =
    timeMinutes.toFixed(1) + " min";

  // Estimate battery usage (rough estimate)
  const batteryPerHour = 20; // % per hour
  const batteryUsage = (timeMinutes / 60) * batteryPerHour;
  document.getElementById("batteryUsage").textContent =
    batteryUsage.toFixed(1) + "%";

  // Calculate efficiency (coverage per meter)
  const area = calculatePolygonArea(boundaryPoints);
  const efficiency = (coverage * area) / pathLength;
  document.getElementById("efficiency").textContent =
    efficiency.toFixed(2) + " m²/m";
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
    const p1 = new google.maps.LatLng(
      typeof path[i - 1][0] === "number"
        ? path[i - 1][0]
        : parseFloat(path[i - 1][0]),
      typeof path[i - 1][1] === "number"
        ? path[i - 1][1]
        : parseFloat(path[i - 1][1])
    );
    const p2 = new google.maps.LatLng(
      typeof path[i][0] === "number" ? path[i][0] : parseFloat(path[i][0]),
      typeof path[i][1] === "number" ? path[i][1] : parseFloat(path[i][1])
    );

    // Calculate distance using the haversine formula
    length += google.maps.geometry.spherical.computeDistanceBetween(p1, p2);
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

  // Convert to Google Maps LatLng objects
  const latLngs = points.map((p) => {
    return new google.maps.LatLng(
      typeof p.lat === "number" ? p.lat : parseFloat(p.lat),
      typeof p.lng === "number" ? p.lng : parseFloat(p.lng)
    );
  });

  // Use Google Maps geometry library to calculate area
  return google.maps.geometry.spherical.computeArea(latLngs);
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
