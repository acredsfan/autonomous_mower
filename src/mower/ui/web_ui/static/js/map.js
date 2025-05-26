// Global variables for map and drawing tools
var map;
var drawingManager;
var currentPolygon = null; // To keep track of the currently drawn/displayed polygon

/**
 * Initializes the Google Map and DrawingManager.
 * This function is called by the Google Maps API script callback.
 */
function initMap() {
    if (typeof google === 'undefined' || typeof google.maps === 'undefined') {
        console.error('Google Maps API not loaded.');
        const mapDiv = document.getElementById('map');
        if (mapDiv) {
            mapDiv.innerHTML = '<div class="alert alert-danger" role="alert">Error: Google Maps API did not load. Please check your API key and internet connection.</div>';
        }
        return;
    }

    // Default map center (e.g., a generic location, can be updated later)
    const defaultCenter = { lat: 40.7128, lng: -74.0060 }; // New York

    map = new google.maps.Map(document.getElementById('map'), {
        center: defaultCenter,
        zoom: 8, // Adjust zoom as needed
        mapTypeId: 'roadmap' // Default to roadmap, user can toggle satellite
    });

    // Initialize Drawing Manager
    drawingManager = new google.maps.drawing.DrawingManager({
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
    drawingManager.setMap(map);

    // Event listener for when a polygon is completed
    google.maps.event.addListener(drawingManager, 'polygoncomplete', function(event) {
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
        drawingManager.setDrawingMode(null);
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
            if (drawingManager) {
                if (currentPolygon) {
                    currentPolygon.setMap(null); // Clear current polygon from map
                    currentPolygon = null;       // Release reference
                }
                drawingManager.setDrawingMode(google.maps.drawing.OverlayType.POLYGON);
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
            if (map) {
                const currentTypeId = map.getMapTypeId();
                map.setMapTypeId(currentTypeId === 'roadmap' ? 'satellite' : 'roadmap');
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
            map.setCenter(results[0].geometry.location);
            map.setZoom(17); // Zoom in closer for addresses
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
function loadAndDrawBoundary() {
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
                    map: map
                });

                // Adjust map to fit the loaded polygon
                const bounds = new google.maps.LatLngBounds();
                coordinates.forEach(coord => bounds.extend(new google.maps.LatLng(coord.lat, coord.lng)));
                map.fitBounds(bounds);
                
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
        const alertsContainer = document.getElementById('alertsContainer'); // Assuming from main.js
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
        }
    }
}

// Ensure setupMapUIEventListeners is called if initMap was already called by Google API
// before this script fully parsed (less likely with defer, but good practice).
if (typeof google !== 'undefined' && typeof google.maps !== 'undefined' && map) {
    // If map is already initialized, but perhaps event listeners weren't set up
    // because this script loaded after initMap ran.
    // This situation needs careful handling if initMap itself has async parts.
    // For now, assuming initMap will call setupMapUIEventListeners.
}
