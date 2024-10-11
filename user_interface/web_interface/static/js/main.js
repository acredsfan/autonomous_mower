// Global variables
let areaCoordinates = [];
let homeLocation = null;
let map;
let areaPolygon = null;
let homeLocationMarker = null;
let robotMarker = null;
let mapId;
let defaultCoordinates = null;
let obj_det_ip = null;
let apiKey;
let pathPolyline = null;

// Function to fetch sensor data
function fetchSensorData() {
    fetch('/get_sensor_data')
        .then(response => response.json())
        .then(data => {
            //console.log(data);
            // Display data on the webpage if necessary
            updateSensorDisplay(data);
        })
        .catch((error) => console.error('Error fetching sensor data:', error));
}

// Call the function at regular intervals, e.g., every 1 second
setInterval(fetchSensorData, 1000);

// Function to update sensor display
function updateSensorDisplay(data) {
    const elements = {
        'battery_voltage': `Battery Voltage: ${data.battery_voltage}`,
        'battery_current': `Battery Current: ${data.battery_current}`,
        'battery_charge': `Battery Charge: ${data.battery_charge_level}`,
        'solar_voltage': `Solar Voltage: ${data.solar_voltage}`,
        'solar_current': `Solar Current: ${data.solar_current}`,
        'speed': `Speed: ${data.speed}`,
        'heading': `Heading: ${data.heading}`,
        'pitch': `Pitch: ${data.pitch}`,
        'roll': `Roll: ${data.roll}`,
        'temperature': `Temperature: ${data.temperature}`,
        'humidity': `Humidity: ${data.humidity}`,
        'pressure': `Pressure: ${data.pressure}`,
        'left_distance': `Left Distance: ${data.left_distance}`,
        'right_distance': `Right Distance: ${data.right_distance}`,
    };
    for (const [id, text] of Object.entries(elements)) {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = text;
        }
    }
}

// Save settings for mowing days and hours
function saveSettings(mowDays, mowHours) {
    fetch('/save_settings', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            mowDays: mowDays,
            mowHours: mowHours,
            patternType: patternType
         }),
    })
    .then(response => response.json())
    .then(data => console.log(data))
    .catch((error) => console.error('Error:', error));
}

// Function to update areaCoordinates when the polygon's path changes
function updateAreaCoordinates() {
    if (areaPolygon) {
        areaCoordinates = areaPolygon.getPath().getArray().map(coord => ({
            lat: coord.lat(),
            lng: coord.lng()
        }));
        console.log('Updated areaCoordinates:', areaCoordinates);
    }
}

// Function to attach listeners to a polygon's path
function attachPolygonListeners(polygon) {
    const path = polygon.getPath();
    path.addListener('set_at', updateAreaCoordinates);
    path.addListener('insert_at', updateAreaCoordinates);
    path.addListener('remove_at', updateAreaCoordinates);
}

// Event listener for DOMContentLoaded
document.addEventListener('DOMContentLoaded', (event) => {
    const form = document.getElementById('settings-form');
    if (form) {
        console.log(form);
        form.addEventListener('submit', function (event) {
            event.preventDefault();
            const mowDays = document.querySelectorAll('input[name="mowDays"]:checked');
            const mowHours = document.querySelectorAll('input[name="mowHours"]:checked');
            const patternType = document.querySelector('input[name="patternType"]:checked').value;
            
            // Convert selected values to arrays
            const selectedDays = Array.from(mowDays).map(input => input.value);
            const selectedHours = Array.from(mowHours).map(input => input.value);

            saveSettings(selectedDays, selectedHours, patternType);  // Trigger save settings
        });
    }
});

// Function to load the Google Maps script
function loadMapScript(apiKey, mapId) {
    const script = document.createElement('script');
    script.src = `https://maps.googleapis.com/maps/api/js?key=${apiKey}&v=beta&map_ids=${mapId}&libraries=drawing,marker`;
    script.type = 'module'; // Use module type
    script.setAttribute('loading', 'async');
    script.onload = () => {
        initMap();
    };
    document.head.appendChild(script);
}

// Event listener for window load
window.addEventListener('load', function () {
    let apiKey;

    Promise.all([
        fetch('/get_google_maps_api_key').then(response => response.json()),
        fetch('/get_map_id').then(response => response.json()),
    ]).then(([keyData, mapIdData]) => {
        apiKey = keyData.api_key;
        mapId = mapIdData.map_id;
        
        if (!apiKey) {
            console.error('API key not found or invalid.');
            return;
        }

        loadMapScript(apiKey, mapId);
    }).catch(error => {
        console.error('Error fetching API key or Map ID:', error);
    });

    const confirmAreaButton = document.getElementById('confirm-area-button');
    if (confirmAreaButton) {
        confirmAreaButton.addEventListener('click', saveMowingArea);
    }

    const confirmHomeButton = document.getElementById('confirm-home-button');
    if (confirmHomeButton) {
        confirmHomeButton.addEventListener('click', saveHomeLocation);
    }
});

// Initialize map
async function initMap() {
    // Import required libraries
    const { Map: GoogleMap } = await google.maps.importLibrary("maps");
    const { AdvancedMarkerElement, PinElement } = await google.maps.importLibrary("marker");
    const { DrawingManager } = await google.maps.importLibrary("drawing");

    const defaultCoordinates = await fetch('/get_default_coordinates')
    .then(response => response.json())
    .catch(error => {
        console.error('Error fetching default coordinates:', error);
        return { lat: 39.095657, lng: -84.515959 }; // Fallback coordinates
    });

    // Parse lat and lng to numbers
    defaultCoordinates.lat = parseFloat(defaultCoordinates.lat);
    defaultCoordinates.lng = parseFloat(defaultCoordinates.lng);

    // Validate the defaultCoordinates
    if (typeof defaultCoordinates.lat !== 'number' || isNaN(defaultCoordinates.lat) ||
        typeof defaultCoordinates.lng !== 'number' || isNaN(defaultCoordinates.lng)) {
        console.error('Invalid default coordinates:', defaultCoordinates);
        defaultCoordinates = { lat: 39.095657, lng: -84.515959 }; // Fallback coordinates
    }

    // Initialize the map
    map = new GoogleMap(document.getElementById('map'), {
        zoom: 20, 
        center: defaultCoordinates,
        mapTypeId: 'satellite',
        mapId: mapId, // Use the global mapId variable
    });

    const drawingManager = new DrawingManager({
        drawingMode: google.maps.drawing.OverlayType.POLYGON,
        drawingControl: true,
        drawingControlOptions: {
            position: google.maps.ControlPosition.TOP_CENTER,
            drawingModes: [
                google.maps.drawing.OverlayType.POLYGON,
                google.maps.drawing.OverlayType.MARKER
            ]
        }
    });

    // Attach the DrawingManager to the map
    drawingManager.setMap(map);

    // Use google.maps.InfoWindow for displaying info
    const infoWindow = new google.maps.InfoWindow();

    // Create PinElement for the home marker
    const pinBackground = new PinElement({
        background: "#00a1e0" // Blue color for the home marker
    });

    // Create PinElement for the robot marker
    const robotPin = new PinElement({
        background: "#FF0000" // Red color for the robot
    });

    // Initialize the draggable marker for home location
    homeLocationMarker = new AdvancedMarkerElement({
        map: map,
        position: homeLocation || defaultCoordinates,
        gmpDraggable: true,
        title: "Robot Home Location - Drag to Change.",
        content: pinBackground.element,
    });

    // Initialize the robot marker
    robotMarker = new AdvancedMarkerElement({
        map: map,
        position: defaultCoordinates,
        title: 'Robot Current Position',
        content: robotPin.element,
    });
    
    // Attach the event listener to the homeLocationMarker
    homeLocationMarker.addListener("dragend", (event) => {
        homeLocation = { lat: event.latLng.lat(), lng: event.latLng.lng() };
        infoWindow.setContent(`Home Location: ${homeLocation.lat}, ${homeLocation.lng}`);
        infoWindow.open(map, homeLocationMarker); // Open the info window on the homeLocationMarker
        document.getElementById('confirm-home-button').disabled = false;
    });

    // Attach listener for when a new polygon is drawn
    google.maps.event.addListener(drawingManager, 'overlaycomplete', function (event) {
        // Remove the previous polygon if it exists
        if (areaPolygon) {
            areaPolygon.setMap(null);
        }

        // Assign the new polygon to areaPolygon
        areaPolygon = event.overlay;

        // Update areaCoordinates with the new polygon's path
        areaCoordinates = areaPolygon.getPath().getArray().map(coord => ({
            lat: coord.lat(),
            lng: coord.lng()
        }));

        console.log('Initial areaCoordinates:', areaCoordinates);

        // Attach listeners to detect future edits
        attachPolygonListeners(areaPolygon);

        // Enable the "Confirm Area" button
        document.getElementById('confirm-area-button').disabled = false;
    });

    // Load saved data
    loadSavedData();

    // Start updating the robot's position
    updateRobotPosition();
    setInterval(updateRobotPosition, 1000); // Update every 1 second

    // Get and draw the path
    getPathAndDraw();
}

// Function to update the robot's position
async function updateRobotPosition() {
    try {
        const response = await fetch('/api/gps');
        const data = await response.json();

        // Validate the GPS data
        if (typeof data.latitude === 'number' && typeof data.longitude === 'number') {
            const position = { lat: data.latitude, lng: data.longitude };
            if (robotMarker) {
                robotMarker.position = position;
            } else {
                // Create a PinElement for the robot marker
                const robotPin = new PinElement({
                    background: "#FF0000" // Red color for the robot
                });
                robotMarker = new AdvancedMarkerElement({
                    map: map,
                    position: position,
                    title: 'Robot Current Position',
                    content: robotPin.element,
                });
            }
        } else {
            console.error('Invalid GPS data:', data);
        }
    } catch (error) {
        console.error('Error fetching robot position:', error);
    }
}

// Load saved data from the server
function loadSavedData() {
    fetch('/get-mowing-area')
        .then(response => response.json())
        .then(data => {
            if (Array.isArray(data) && data.length > 0) {
                // Remove the existing polygon if it exists
                if (areaPolygon) {
                    areaPolygon.setMap(null);
                }

                // Create a new polygon with the saved coordinates
                areaPolygon = new google.maps.Polygon({
                    paths: data,
                    editable: true,
                    draggable: false, // Make the polygon itself draggable if needed
                    fillColor: '#FF0000',
                    fillOpacity: 0.35,
                    strokeColor: '#FF0000',
                    strokeOpacity: 0.8,
                    strokeWeight: 2
                });

                // Add the polygon to the map
                areaPolygon.setMap(map);

                // Update areaCoordinates with the loaded polygon's path
                areaCoordinates = areaPolygon.getPath().getArray().map(coord => ({
                    lat: coord.lat(),
                    lng: coord.lng()
                }));

                console.log('Loaded areaCoordinates:', areaCoordinates);

                // Attach listeners to detect future edits
                attachPolygonListeners(areaPolygon);
            }
        })
        .catch(error => console.error('Error loading mowing area:', error));

    fetch('/get-home-location')
        .then(response => response.json())
        .then(data => {
            if (typeof data.lat === 'number' && typeof data.lng === 'number') {
                homeLocation = { lat: data.lat, lng: data.lng };
                if (homeLocationMarker) {
                    homeLocationMarker.position = homeLocation;
                } else {
                    // If for some reason homeLocationMarker doesn't exist
                    const pinBackground = new PinElement({
                        background: "#00a1e0" // Blue color for the home marker
                    });
                    homeLocationMarker = new AdvancedMarkerElement({
                        map: map,
                        position: homeLocation,
                        gmpDraggable: true,
                        title: "Robot Home Location - Drag to Change.",
                        content: pinBackground.element,
                    });
                    homeLocationMarker.setMap(map);
                }
            }
        })
        .catch(error => console.error('Error loading home location:', error));
}

// Save the mowing area
function saveMowingArea() {
    if (areaCoordinates.length === 0) {
        alert('No mowing area defined.');
        return;
    }

    fetch('/save-mowing-area', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(areaCoordinates)
    })
    .then(response => response.json())
    .then(() => alert('Mowing area saved successfully.'))
    .catch(error => console.error('Error:', error));
}

// Save the home location
function saveHomeLocation() {
    if (!homeLocation) {
        alert('Please select a home location.');
        return;
    }
    fetch('/save-home-location', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(homeLocation)
    })
    .then(response => response.json())
    .then(() => alert('Home location saved successfully.'))
    .catch(error => console.error('Error:', error));
}

// Function to get and draw the path on the map
function getPathAndDraw() {
    fetch('/get-path')
        .then(response => response.json())
        .then(data => {
            if (data.path) {
                drawPath(data.path);
            }
        })
        .catch(error => console.error('Error fetching path:', error));
}

// Function to draw the path on the map
function drawPath(coordinates) {
    // Remove existing path if any
    if (pathPolyline) {
        pathPolyline.setMap(null);
    }

    // Create a new polyline for the path
    pathPolyline = new google.maps.Polyline({
        path: coordinates.map(coord => ({ lat: coord[1], lng: coord[0] })), // Convert to lat/lng
        geodesic: true,
        strokeColor: '#0000FF',
        strokeOpacity: 1.0,
        strokeWeight: 2
    });

    // Set the polyline on the map
    pathPolyline.setMap(map);
}

// Socket.IO setup
var socket = io();

//Setup /video_feed endpoint
async function setVideoFeed() {
    const videoFeedElement = document.getElementById('video_feed');
    if (videoFeedElement) {
        videoFeedElement.src = '/video_feed'; // This will fetch from the updated route in app.py
    } else {
        console.error('Element with id "video_feed" not found.');
    }
}

window.addEventListener('load', setVideoFeed);


// Add event listener for the "Check Polygon Points" button
const checkPolygonButton = document.getElementById('check-polygon-button');
if (checkPolygonButton) {
    checkPolygonButton.addEventListener('click', checkPolygonPoints);
}

function checkPolygonPoints() {
    fetch('/check-polygon-points', {
        method: 'POST',
    })
    .then(response => response.json())
    .then(data => alert(data.message))
    .catch(error => console.error('Error:', error));
}

// Handle incoming messages (if any)
socket.on('message', function(data) {
    console.log(data.data);
});

// JavaScript functions for controlling the robot
function move(direction) {
    let steering = 0;
    let throttle = 0;

    switch (direction) {
        case 'forward':
            throttle = 1; // Full forward
            break;
        case 'backward':
            throttle = -1; // Full backward
            break;
        case 'left':
            steering = -1; // Full left
            break;
        case 'right':
            steering = 1; // Full right
            break;
        case 'stop':
            throttle = 0;
            steering = 0;
            break;
        default:
            throttle = 0;
            steering = 0;
    }

    fetch('/control', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            steering: steering,
            throttle: throttle
        }),
    })
    .then(response => {
        if (!response.ok) {
            console.error('Server error:', response.status);
            return response.text().then(text => {
                console.error('Error text:', text);
                throw new Error('Server error');
            });
        }
        return response.json();
    })
    .then(data => console.log(data))
    .catch((error) => console.error('Error:', error));
}

function toggleBlades(state) {
    fetch('/toggle_blades', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ state: state }),
    })
    .then(response => response.json())
    .then(data => alert(data.message))
    .catch((error) => console.error('Error:', error));
}

function startMowing() {
    fetch('/start-mowing', {
        method: 'POST',
    })
    .then(response => response.json())
    .then(data => alert(data.message))
    .catch((error) => console.error('Error:', error));
}

function stopMowing() {
    fetch('/stop-mowing', {
        method: 'POST',
    })
    .then(response => response.json())
    .then(data => alert(data.message))
    .catch((error) => console.error('Error:', error));
}

