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
    document.getElementById('bme280').textContent = `BME280: ${data.bme280}`;
    document.getElementById('accel').textContent = `Accelerometer: ${data.accel}`;
    document.getElementById('compass').textContent = `Compass: ${data.compass}`;
    document.getElementById('gyro').textContent = `Gyroscope: ${data.gyro}`;
    document.getElementById('quaternion').textContent = `Quaternion: ${data.quaternion}`;
    document.getElementById('speed').textContent = `Speed: ${data.speed}`;
    document.getElementById('heading').textContent = `Heading: ${data.heading}`;
    document.getElementById('pitch').textContent = `Pitch: ${data.pitch}`;
    document.getElementById('roll').textContent = `Roll: ${data.roll}`;
    document.getElementById('solar').textContent = `Solar: ${data.solar}`;
    document.getElementById('battery').textContent = `Battery: ${data.battery}`;
    document.getElementById('battery_charge').textContent = `Battery Charge: ${data.battery_charge}`;
    document.getElementById('left_distance').textContent = `Left Distance: ${data.left_distance}`;
    document.getElementById('right_distance').textContent = `Right Distance: ${data.right_distance}`;
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
let homeMarker = null;
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

    // Use google.maps.InfoWindow instead of InfoWindow
    const infoWindow = new google.maps.InfoWindow();

    // Use google.maps.Marker instead of AdvancedMarkerElement
    const draggableMarker = new google.maps.Marker({
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

    google.maps.event.addListener(map, 'click', function (event) {
        if (homeMarker) {
            homeMarker.setMap(null);
        }
        homeLocation = { lat: event.latLng.lat(), lng: event.latLng.lng() };
        homeMarker = new google.maps.Marker({
            position: homeLocation,
            map: map,
            title: 'Home Location'
        });
        document.getElementById('confirm-home-button').disabled = false;
    });

    // Load saved data
    loadSavedData();
}

// Save the mowing area
function saveMowingArea() {
    fetch('/save-mowing-area', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ mowingAreaCoordinates: areaCoordinates })
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
                homeMarker = new google.maps.Marker({
                    position: homeLocation,
                    map: map,
                    title: 'Home Location'
                });
            }
        })
        .catch(error => console.error('Error loading home location:', error));
}

window.addEventListener('load', function () {
    let apiKey;
    let mapId;
    Promise.all([
        fetch('/get_google_maps_api_key').then(response => response.json()),
        fetch('/get_map_id').then(response => response.json())
    ]).then(([apiKeyData, mapIdData]) => {
        apiKey = apiKeyData.GOOGLE_MAPS_API_KEY;
        mapId = mapIdData.map_id;
        loadMapScript(apiKey, mapId);
    }).catch(error => console.error('Error fetching data:', error));

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
    document.head.appendChild(script);
}

// function to get and draw the path on the map, if no path is available, it will not show anything
function getPathAndDraw() {
    fetch('/get_path')
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

socket.on('update_frame', function(data) {
    var image = document.getElementById('video_feed');
    image.src = 'data:image/jpeg;base64,' + data.frame;
});

// Request a new frame every 500ms (or whatever interval you prefer)
setInterval(function() {
    socket.emit('request_frame');  // Request a frame every 500ms
}, 500);