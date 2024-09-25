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
        body: JSON.stringify({ mowDays: mowDays, mowHours: mowHours }),
    })
    .then(response => response.json())
    .then(data => console.log(data))
    .catch((error) => console.error('Error:', error));
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
            
            // Convert selected values to arrays
            const selectedDays = Array.from(mowDays).map(input => input.value);
            const selectedHours = Array.from(mowHours).map(input => input.value);

            saveSettings(selectedDays, selectedHours);  // Trigger save settings
        });
    }
});

// Function to load the Google Maps script
function loadMapScript(apiKey, mapId) {
    const script = document.createElement('script');
    script.src = `https://maps.googleapis.com/maps/api/js?key=${apiKey}&v=beta&map_ids=${mapId}`;
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
        apiKey = keyData.api_key;  // Ensure this matches the key in your JSON response
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

    google.maps.event.addListener(drawingManager, 'overlaycomplete', function (event) {
        const polygon = event.overlay;
        areaCoordinates = polygon.getPath().getArray().map(coord => ({
            lat: coord.lat(),
            lng: coord.lng()
        }));
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
            if (data.length > 0) {
                areaPolygon = new google.maps.Polygon({
                    paths: data,
                    editable: true
                });
                areaPolygon.setMap(map);
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

// Function to draw the path
function drawPath(coordinates) {
    const path = new google.maps.Polyline({
        path: coordinates,
        geodesic: true,
        strokeColor: '#0000FF',
        strokeOpacity: 1.0,
        strokeWeight: 2
    });
    path.setMap(map);
}

// Socket.IO setup
var socket = io();

window.addEventListener('load', function () {
    let obj_det_ip;
    fetch('/get_obj_det_ip').then(response => response.json())
        .then(data => {
            obj_det_ip = data.object_detection_ip; // Extract the IP address
            socket.emit('video_connection', { ip: obj_det_ip });

            const videoFeedElement = document.getElementById('video_feed');
            if (videoFeedElement) {
                videoFeedElement.src = `http://${obj_det_ip}:5000/video_feed`;
            } else {
                console.error('Element with id "video_feed" not found.');
            }
        })
        .catch(error => {
            console.error('Error fetching object detection IP:', error);
        });

    socket.on('video_connection', function (data) {
        console.log('Connected to object detection server');
    });
});
