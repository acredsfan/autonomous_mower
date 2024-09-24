function fetchSensorData() {
    fetch('/get_sensor_data')
        .then(response => response.json())
        .then(data => {
            console.log(data);
            // Display data on the webpage if necessary
            updateSensorDisplay(data);
        })
        .catch((error) => console.error('Error fetching sensor data:', error));
}

// Call the function at regular intervals, e.g., every 1 seconds
setInterval(fetchSensorData, 1000);

function updateSensorDisplay(data) {
    const elements = {
        'bme280': `BME280: ${JSON.stringify(data.bme280)}`,
        'accel': `Accelerometer: ${JSON.stringify(data.accel)}`,
        'compass': `Compass: ${JSON.stringify(data.compass)}`,
        'gyro': `Gyroscope: ${JSON.stringify(data.gyro)}`,
        'quaternion': `Quaternion: ${JSON.stringify(data.quaternion)}`,
        'speed': `Speed: ${data.speed}`,
        'heading': `Heading: ${data.heading}`,
        'pitch': `Pitch: ${data.pitch}`,
        'roll': `Roll: ${data.roll}`,
        'solar': `Solar: ${JSON.stringify(data.solar)}`,
        'battery': `Battery: ${JSON.stringify(data.battery)}`,
        'battery_charge': `Battery Charge: ${data.battery_charge}`,
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

let areaCoordinates = [];
let homeLocation = null;
let map;
let areaPolygon = null;
let draggableMarker = null;  // Changed from homeMarker
let robotMarker = null;
let mapId = null;

// Initialize map
function initMap() {
    const defaultCoordinates = { lat: 39.03856, lng: -84.21473 };
    const mapOptions = {
        zoom: 25,
        center: defaultCoordinates,
        mapTypeId: 'satellite',
        tilt: 0,
        disableDefaultUI: true,
    };
    map = new google.maps.Map(document.getElementById('map'), mapOptions);

    const drawingManager = new google.maps.drawing.DrawingManager({
        drawingMode: google.maps.drawing.OverlayType.POLYGON,
        drawingControl: true,
        drawingControlOptions: {
            position: google.maps.ControlPosition.TOP_CENTER,
            drawingModes: [google.maps.drawing.OverlayType.POLYGON]
        }
    });
    drawingManager.setMap(map);

    // Use google.maps.InfoWindow for displaying info
    const infoWindow = new google.maps.InfoWindow();

    // Initialize the draggable marker for home location
    draggableMarker = new google.maps.marker.AdvancedMarkerElement({
        map: map,
        position: defaultCoordinates,
        draggable: true,
        title: "Drag to Robot's Home Location.",
    });

    draggableMarker.addListener("dragend", (event) => {
        homeLocation = { lat: event.latLng.lat(), lng: event.latLng.lng() };
        infoWindow.setContent(`Home Location: ${homeLocation.lat}, ${homeLocation.lng}`);
        infoWindow.open(map, draggableMarker);
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
}

// Function to update the robot's position
function updateRobotPosition() {
    fetch('/api/gps')
        .then(response => response.json())
        .then(data => {
            if (data.latitude && data.longitude) {
                const position = { lat: data.latitude, lng: data.longitude };
                if (robotMarker) {
                    robotMarker.setPosition(position);
                } else {
                    robotMarker = new google.maps.marker.AdvancedMarkerElement({
                        position: position,
                        map: map,
                        icon: {
                            path: google.maps.SymbolPath.CIRCLE,
                            scale: 6,
                            fillColor: "#FF0000",     // Red color for the robot
                            fillOpacity: 1,
                            strokeWeight: 2,
                            strokeColor: "#FFFFFF"    // White border
                        },
                        title: 'Robot Position'
                    });
                }
            } else {
                console.error('No GPS data available');
            }
        })
        .catch(error => console.error('Error fetching robot position:', error));
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
            if (data.lat && data.lng) {
                homeLocation = { lat: data.lat, lng: data.lng };
                if (draggableMarker) {
                    draggableMarker.setPosition(homeLocation);
                } else {
                    // If for some reason draggableMarker doesn't exist
                    draggableMarker = new google.maps.marker.AdvancedMarkerElement({
                        map: map,
                        position: homeLocation,
                        draggable: true,
                        title: "Drag to Robot's Home Location.",
                    });
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

window.addEventListener('load', function () {
    let apiKey;
    let mapId;
    Promise.all([
        fetch('/get_google_maps_api_key').then(response => response.json()),
        fetch('/get_map_id').then(response => {
            if (response.ok) {
                return response.json();
            } else {
                // If map_id is not found, return null
                return null;
            }
        }),
    ]).then(([keyData, idData]) => {
        apiKey = keyData.GOOGLE_MAPS_API_KEY;
        mapId = idData ? idData.map_id : null;
        loadMapScript(apiKey, mapId);
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

function loadMapScript(apiKey, mapId) {
    const script = document.createElement('script');
    script.src = `https://maps.googleapis.com/maps/api/js?key=${apiKey}&callback=initMap&libraries=drawing${mapId ? `&map_ids=${mapId}` : ''}`;
    script.defer = true;
    script.async = true;
    document.head.appendChild(script);
}

// function to get and draw the path on the map, if no path is available, it will not show anything
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


function drawPath(coordinates) {
    var path = new google.maps.Polyline({
        path: coordinates,
        geodesic: true,
        strokeColor: '#0000FF',
        strokeOpacity: 1.0,
        strokeWeight: 2
    });
    path.setMap(map);
}

// Call this function when you want to update the path
getPathAndDraw();

var socket = io();

window.addEventListener('load', function () {
    let obj_det_ip;
    fetch('/get_obj_det_ip').then(response => response.json())
        .then(data => {
            obj_det_ip = data;
            socket.emit('connect', { ip: obj_det_ip });
        });

    socket.on('connect', function (data) {
        console.log('Connected to object detection server');
    }
    );
    const videoFeedElement = document.getElementById('video_feed');
    videoFeedElement.src = `http://${obj_det_ip}:5000/video_feed`;
});