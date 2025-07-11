// Ensure alertsContainer exists for notifications
document.addEventListener('DOMContentLoaded', function() {
    if (!document.getElementById('alertsContainer')) {
        console.log('Creating alerts container');
        const alertsContainer = document.createElement('div');
        alertsContainer.id = 'alertsContainer';
        alertsContainer.style.position = 'fixed';
        alertsContainer.style.top = '20px';
        alertsContainer.style.right = '20px';
        alertsContainer.style.zIndex = '9999';
        alertsContainer.style.maxWidth = '400px';
        document.body.appendChild(alertsContainer);
    }
});

// Global variables for drawing tools
// Avoid declaring 'map' as it conflicts with mowing-patterns.js
window.mapDrawingManager = window.mapDrawingManager || null;
var currentPolygon = null; // To keep track of the currently drawn/displayed polygon
var mapLoaded = false; // Track if the map is loaded

/**
 * Sets up the Google Maps Drawing Manager on the map.
 * This function is used to initialize or re-initialize the drawing capabilities.
 * @param {Object} mapInstance - The Google Maps instance to attach drawing tools to
 */
function setupDrawingManager(mapInstance) {
    // If no map instance provided, use window.map as fallback
    mapInstance = mapInstance || window.map;

    if (!mapInstance) {
        console.error('No map instance available for drawing manager');
        return;
    }

    mapDrawingManager = new google.maps.drawing.DrawingManager({
        drawingMode: null, // Initially not drawing
        drawingControl: true,
        drawingControlOptions: {
            position: google.maps.ControlPosition.TOP_CENTER,
            drawingModes: [
                google.maps.drawing.OverlayType.POLYGON
            ]
        },
        polygonOptions: {
            fillColor: '#4CAF50',
            fillOpacity: 0.3,
            strokeWeight: 2,
            strokeColor: '#4CAF50',
            clickable: false,
            editable: true, // Allow editing after drawing
            zIndex: 1
        }
    });
    mapDrawingManager.setMap(mapInstance);

    // Event listener for when a polygon is completed
    google.maps.event.addListener(mapDrawingManager, 'polygoncomplete', function(event) {
        if (currentPolygon) {
            currentPolygon.setMap(null); // Remove previous polygon from map
        }
        currentPolygon = event.overlay;
        currentPolygon.setEditable(true); // Make the newly drawn polygon editable

        const path = currentPolygon.getPath();
        const coordinates = [];
        for (let i = 0; i < path.getLength(); i++) {
            const latLng = path.getAt(i);
            coordinates.push({ lat: latLng.lat(), lng: latLng.lng() });
        }

        console.log('Polygon completed. Coordinates:', coordinates);
        saveBoundary(coordinates);

        // After completing a polygon, set mode back to navigation (null)
        mapDrawingManager.setDrawingMode(null);
    });
}

/**
 * Initializes the Google Map and DrawingManager.
 * This function is called by the Google Maps API script callback.
 */
function initMap() {
    // Check if we've already loaded this function to prevent duplicate initialization
    if (mapLoaded) {
        console.log('Map already initialized, skipping duplicate initialization');
        return;
    }

    if (typeof google === 'undefined' || typeof google.maps === 'undefined') {
        console.error('Google Maps API not loaded.');
        const mapDiv = document.getElementById('map');
        if (mapDiv) {
            mapDiv.innerHTML = `
                <div class="alert alert-danger" role="alert">
                    <h4>Error: Google Maps API did not load</h4>
                    <p>This is likely due to a missing or invalid API key.</p>
                    <p>To fix this issue:</p>
                    <ol>
                        <li>Create a .env file in the project root directory if not already present</li>
                        <li>Add your Google Maps API key: <code>GOOGLE_MAPS_API_KEY=your_key_here</code></li>
                        <li>Restart the mower service: <code>sudo systemctl restart mower.service</code></li>
                    </ol>
                    <p>You can get a Google Maps API key from the <a href="https://developers.google.com/maps/documentation/javascript/get-api-key" target="_blank">Google Cloud Console</a>.</p>
                </div>
            `;
            // Add a helpful command to check status
            const checkCommand = document.createElement('div');
            checkCommand.className = 'mt-3';
            checkCommand.innerHTML = `
                <p>To check if your API key is properly configured, you can run:</p>
                <pre>cd /home/pi/autonomous_mower && python3 test_web_ui.py --check-api-key</pre>
            `;
            mapDiv.appendChild(checkCommand);
        }
        return;
    }

    // Set flag that we're initializing
    mapLoaded = true;

    // Check if map is already initialized by mowing-patterns.js
    if (window.map) {
        console.log('Using existing map from window.map');
        // Just initialize our map-specific functionality
        setupDrawingManager(window.map);
        // Load any existing boundary
        loadAndDrawBoundary(window.map);
        // Setup UI event listeners
        setupMapUIEventListeners(window.map);
        return;
    }

    // Default map center based on data attributes or fallback
    const mapElement = document.getElementById('map');
    const initialLat = parseFloat(mapElement?.dataset.initialLat) || 0;
    const initialLng = parseFloat(mapElement?.dataset.initialLng) || 0;
    const defaultCenter = { lat: initialLat, lng: initialLng };

    window.map = new google.maps.Map(mapElement, {
        center: defaultCenter,
        zoom: 18,
        mapTypeId: 'roadmap', // Default to roadmap, user can toggle satellite
        mapTypeControl: true,
        mapTypeControlOptions: {
            style: google.maps.MapTypeControlStyle.HORIZONTAL_BAR,
            position: google.maps.ControlPosition.TOP_RIGHT,
            mapTypeIds: ['roadmap', 'satellite', 'hybrid', 'terrain']
        },
        fullscreenControl: true,
        streetViewControl: true,
        zoomControl: true
    });

    // Initialize Drawing Manager
    setupDrawingManager(window.map);

    // Event listener for when a polygon is completed
    google.maps.event.addListener(mapDrawingManager, 'polygoncomplete', function(event) {
        if (currentPolygon) {
            currentPolygon.setMap(null); // Remove previous polygon from map
        }
        currentPolygon = event.overlay;
        currentPolygon.setEditable(true); // Make the newly drawn polygon editable

        const path = currentPolygon.getPath();
        const coordinates = [];
        for (let i = 0; i < path.getLength(); i++) {
            const latLng = path.getAt(i);
            coordinates.push({ lat: latLng.lat(), lng: latLng.lng() });
        }

        console.log('Polygon completed. Coordinates:', coordinates);
        saveBoundary(coordinates);

        // After completing a polygon, set mode back to navigation (null)
        mapDrawingManager.setDrawingMode(null);
    });

    // Load any existing boundary when the map initializes
    loadAndDrawBoundary();

    // Setup UI event listeners for map controls
    setupMapUIEventListeners();
}

/**
 * Sets up event listeners for map control UI elements.
 */
function setupMapUIEventListeners() {
    const drawBoundaryButton = document.getElementById('draw-boundary');
    if (drawBoundaryButton) {
        drawBoundaryButton.addEventListener('click', function() {
            if (mapDrawingManager) {
                if (currentPolygon) {
                    currentPolygon.setMap(null); // Clear current polygon from map
                    currentPolygon = null;       // Release reference
                }
                mapDrawingManager.setDrawingMode(google.maps.drawing.OverlayType.POLYGON);
                showAlert('Drawing mode activated. Click on the map to start drawing your yard boundary.', 'info', 5000);
            }
        });
    }

    const clearAllButton = document.getElementById('clear-all');
    if (clearAllButton) {
        clearAllButton.addEventListener('click', function() {
            if (currentPolygon) {
                currentPolygon.setMap(null);
                currentPolygon = null;
            }
            // Optionally, also clear from backend by saving an empty boundary
            saveBoundary([]);
            showAlert('Cleared current boundary from map. Saved empty boundary to backend.', 'info');
        });
    }

    const saveMapChangesButton = document.getElementById('save-map-changes');
    if(saveMapChangesButton) {
        saveMapChangesButton.addEventListener('click', function() {
            if (currentPolygon) {
                const path = currentPolygon.getPath();
                const coordinates = [];
                for (let i = 0; i < path.getLength(); i++) {
                    const latLng = path.getAt(i);
                    coordinates.push({ lat: latLng.lat(), lng: latLng.lng() });
                }
                saveBoundary(coordinates);
            } else {
                showAlert('No boundary drawn to save.', 'warning');
            }
        });
    }

    const toggleSatelliteButton = document.getElementById('toggle-satellite');
    if (toggleSatelliteButton) {
        toggleSatelliteButton.addEventListener('click', function() {
            // Use window.map as the source of truth
            if (window.map) {
                const currentTypeId = window.map.getMapTypeId();
                const newTypeId = currentTypeId === 'roadmap' ? 'satellite' : 'roadmap';
                window.map.setMapTypeId(newTypeId);

                // Update button text
                const icon = currentTypeId === 'roadmap' ? 'fa-map' : 'fa-satellite';
                const text = currentTypeId === 'roadmap' ? 'Toggle Street' : 'Toggle Satellite';
                this.innerHTML = `<i class="fas ${icon}"></i> ${text}`;
            }
        });
    }

    // Address Search
    const searchAddressButton = document.getElementById('search-address');
    const addressInput = document.getElementById('address-input');
    if (searchAddressButton && addressInput) {
        searchAddressButton.addEventListener('click', function() {
            const address = addressInput.value;
            if (address) {
                geocodeAddress(address);
            }
        });
        addressInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                const address = addressInput.value;
                if (address) {
                    geocodeAddress(address);
                }
            }
        });
    }
}

/**
 * Geocodes an address and centers the map on its location.
 * @param {string} address The address to geocode.
 */
function geocodeAddress(address) {
    const geocoder = new google.maps.Geocoder();
    geocoder.geocode({ 'address': address }, function(results, status) {
        if (status === 'OK') {
            const mapObj = window.map;
            if (mapObj) {
                mapObj.setCenter(results[0].geometry.location);
                mapObj.setZoom(17); // Zoom in closer for addresses
            }
            // Optionally, place a marker
            // new google.maps.Marker({
            //     map: map,
            //     position: results[0].geometry.location
            // });
            showAlert('Address found and map centered.', 'success');
        } else {
            showAlert('Geocode was not successful for the following reason: ' + status, 'danger');
            console.error('Geocode error: ' + status);
        }
    });
}


/**
 * Loads existing boundary data from the backend and draws it on the map.
 */
/**
 * Loads boundary data from the server and draws it on the map
 * @param {Object} mapInstance - Optional map instance parameter
 */
function loadAndDrawBoundary(mapInstance) {
    // If no map instance provided, use window.map as fallback
    mapInstance = mapInstance || window.map;

    if (!mapInstance) {
        console.error('No map instance available for boundary drawing');
        return;
    }

    fetch('/api/get-area') // Uses existing endpoint from app.py
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok: ' + response.statusText);
            }
            return response.json();
        })
        .then(data => {
            if (data.success && data.data && data.data.boundary_points && data.data.boundary_points.length > 0) {
                const coordinates = data.data.boundary_points;
                if (currentPolygon) {
                    currentPolygon.setMap(null); // Clear existing polygon
                }
                currentPolygon = new google.maps.Polygon({
                    paths: coordinates,
                    strokeColor: '#4CAF50',
                    strokeOpacity: 0.8,
                    strokeWeight: 2,
                    fillColor: '#4CAF50',
                    fillOpacity: 0.3,
                    editable: true, // Allow editing of loaded polygon
                    map: mapInstance
                });

                // Adjust map to fit the loaded polygon
                const bounds = new google.maps.LatLngBounds();
                coordinates.forEach(coord => bounds.extend(new google.maps.LatLng(coord.lat, coord.lng)));
                mapInstance.fitBounds(bounds);

                // Add listeners for edits if polygon is editable
                if (currentPolygon.getEditable()) {
                    google.maps.event.addListener(currentPolygon.getPath(), 'set_at', function() {
                        // Called when a vertex is moved.
                        console.log('Polygon vertex moved (set_at)');
                        // Auto-save on edit, or rely on "Save Map Changes" button
                        // For now, rely on button or new drawing to save.
                    });
                    google.maps.event.addListener(currentPolygon.getPath(), 'insert_at', function() {
                        // Called when a vertex is added.
                        console.log('Polygon vertex added (insert_at)');
                    });

                    console.log('Successfully loaded and drew boundary with', coordinates.length, 'points');
                }

            } else if (data.success && (!data.data || !data.data.boundary_points || data.data.boundary_points.length === 0)) {
                console.log('No existing boundary found or boundary is empty.');
            } else {
                console.error('Failed to load boundary:', data.error || 'Unknown error');
                // showAlert('Could not load existing boundary: ' + (data.error || 'Unknown error'), 'warning');
            }
        })
        .catch(error => {
            console.error('Error fetching boundary:', error);
            // showAlert('Error fetching boundary: ' + error.message, 'danger');
        });
}

/**
 * Saves the boundary coordinates to the backend.
 * @param {Array<Object>} coordinates Array of {lat, lng} objects.
 */
function saveBoundary(coordinates) {
    fetch('/api/save-area', { // Uses existing endpoint from app.py
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ coordinates: coordinates }),
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showAlert('Boundary saved successfully!', 'success');
            // Reload and draw the boundary to ensure it's the one from the server
            // and to clear any temporary drawing overlays.
            loadAndDrawBoundary();
        } else {
            showAlert('Failed to save boundary: ' + (data.error || 'Unknown error'), 'danger');
            console.error('Failed to save boundary:', data.error);
        }
    })
    .catch(error => {
        showAlert('Error saving boundary: ' + error.message, 'danger');
        console.error('Error saving boundary:', error);
    });
}

// Make initMap globally available for the Google Maps callback
window.initMap = initMap;

// Helper function to show alerts (assuming showAlert is defined in main.js or similar)
// If not, define a simple version or integrate properly.
if (typeof showAlert !== 'function') {
    function showAlert(message, type = 'info', duration = 3000) {
        console.log(`Alert (${type}): ${message}`);
        // Simple fallback if a proper showAlert isn't available:
        const alertsContainer = document.getElementById('alertsContainer');
        if (alertsContainer) {
            const alertId = "map_alert_" + Date.now();
            const alertHtml = `
                <div id="${alertId}" class="alert alert-${type} d-flex justify-between align-center" style="padding: 10px; margin-bottom: 10px; border: 1px solid #ccc; border-radius: 4px;">
                    <div>${message}</div>
                    <button type="button" class="btn-close" onclick="this.parentElement.remove();" style="background: none; border: none; font-size: 1.2em; cursor: pointer;">&times;</button>
                </div>
            `;
            alertsContainer.insertAdjacentHTML("beforeend", alertHtml);
            if (duration > 0) {
                setTimeout(() => {
                    const alertElement = document.getElementById(alertId);
                    if (alertElement) alertElement.remove();
                }, duration);
            }
        } else if (type === 'danger' || type === 'error') {
            // Fallback to browser alert for critical errors if no alerts container exists
            alert(`Error: ${message}`);
        }
    }
}

// Fallback sendCommand function if helper.js fails to load
if (typeof sendCommand !== 'function') {
    console.log('Adding fallback sendCommand function');
    window.sendCommand = function(command, params = {}, callback = null) {
        console.log(`Sending command: ${command}`, params);
        // Show a temporary loading message
        showAlert(`Processing command: ${command}...`, 'info', 1000);

        fetch('/api/' + command, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(params)
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`Server returned ${response.status}: ${response.statusText}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                console.log(`Command ${command} succeeded:`, data);
                if (data.message) {
                    showAlert(data.message, 'success');
                }
            } else {
                console.error(`Command ${command} failed:`, data);
                showAlert(`Command failed: ${data.error || 'Unknown error'}`, 'danger');
            }

            if (callback) {
                callback(data);
            }
        })
        .catch(error => {
            console.error('Error sending command:', error);
            showAlert(`Error: ${error.message}`, 'danger');
            if (callback) {
                callback({success: false, error: error.message});
            }
        });
    };
}

// Ensure setupMapUIEventListeners is called if initMap was already called by Google API
// before this script fully parsed (less likely with defer, but good practice).
if (typeof google !== 'undefined' && typeof google.maps !== 'undefined' && window.map) {
    // If map is already initialized, but perhaps event listeners weren't set up
    // because this script loaded after initMap ran.
    // This situation needs careful handling if initMap itself has async parts.
    console.log('Map already initialized, setting up UI event listeners');
    setupMapUIEventListeners(window.map);
}

// Attach listeners once the DOM is ready if map already exists
document.addEventListener('DOMContentLoaded', function() {
    if (window.map && typeof setupMapUIEventListeners === 'function') {
        setupMapUIEventListeners(window.map);
    }
});
