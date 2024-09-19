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


// Call the function at regular intervals, e.g., every 5 seconds
setInterval(fetchSensorData, 5000);

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

//get GOOGLE_MAPS_API_KEY from config.json
fetch('/get_google_maps_api_key')
    .then(response => response.json())
    .then(data => {
        console.log(data);
        loadScript(data.GOOGLE_MAPS_API_KEY);
    })
    .catch((error) => console.error('Error fetching Google Maps API key:', error));

function loadScript() {
    const script = document.createElement('script');
    script.src = `https://maps.googleapis.com/maps/api/js?key=YOUR_GOOGLE_MAPS_API_KEY&callback=initMap&libraries=drawing`;
    script.defer = true;
    document.head.appendChild(script);
}

function move(direction) {
    fetch('/control', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ steering: getSteering(direction), throttle: getThrottle(direction) }),
    })
    .then(response => response.json())
    .then(data => console.log(data))
    .catch((error) => console.error('Error:', error));
}

function getSteering(direction) {
    switch (direction) {
        case 'left':
            return -1;
        case 'right':
            return 1;
        case 'stop':
            return 0;
        default:
            return 0;
    }
}

function getThrottle(direction) {
    switch (direction) {
        case 'forward':
            return 1;
        case 'backward':
            return -1;
        case 'stop':
            return 0;
        default:
            return 0;
    }
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
    .then(data => console.log(data))
    .catch((error) => console.error('Error:', error));
}

function startMowing() {
    fetch('/start-mowing', {
        method: 'POST',
    })
    .then(response => response.json())
    .then(data => console.log(data))
    .catch((error) => console.error('Error:', error));
}

function stopMowing() {
    fetch('/stop-mowing', {
        method: 'POST',
    })
    .then(response => response.json())
    .then(data => console.log(data))
    .catch((error) => console.error('Error:', error));
}


function saveMowingArea(mowingAreaCoordinates) {
    // Make an AJAX POST request to the server to save the mowing area as an polygon array
    fetch('/save-mowing-area', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ mowingAreaCoordinates: mowingAreaCoordinates }),
    })
    .then(response => response.json())
    .then(data => console.log(data))
    .catch((error) => console.error('Error:', error));
}

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
    console.log(form); // Log the form element to check if it exists
    form.addEventListener('submit', function (event) {
        event.preventDefault();  // Prevent page reload
        const mowDays = document.querySelectorAll('input[name="mowDays"]:checked');
        const mowHours = document.querySelectorAll('input[name="mowHours"]:checked');
        
        // Convert selected values to arrays
        const selectedDays = Array.from(mowDays).map(input => input.value);
        const selectedHours = Array.from(mowHours).map(input => input.value);

        saveSettings(selectedDays, selectedHours);  // Trigger save settings
    });
});


let map;
let coordinates = [];

function initMap() {
    map = new google.maps.Map(document.getElementById('map'), {
        zoom: 20,
        tilt: 0,
        mapTypeId: 'satellite',
        center: {lat: 39.038542, lng: -84.214696}
    });

    const drawingManager = new google.maps.drawing.DrawingManager({
        drawingMode: google.maps.drawing.OverlayType.POLYGON,
        drawingControl: true,
        drawingControlOptions: {
            position: google.maps.ControlPosition.TOP_CENTER,
            drawingModes: [google.maps.drawing.OverlayType.POLYGON]
        }
    });

    drawingManager.setMap(map);

    google.maps.event.addListener(drawingManager, 'polygoncomplete', function(polygon) {
        const path = polygon.getPath();
        coordinates.length = 0;  // Clear the array
        for (let i = 0; i < path.getLength(); i++) {
            const lat = path.getAt(i).lat();
            const lng = path.getAt(i).lng();
            coordinates.push({lat: lat, lng: lng});
        }
        console.log(coordinates);
        // Save coordinates to server
        saveMowingArea(coordinates);
    });

    const submitBtn = document.getElementById('confirm-button');
    console.log(submitBtn); // Log the button element to check if it exists
    submitBtn.addEventListener('click', function() {
        console.log('Submit button clicked');
        // Now the click listener has access to the coordinates array
        saveMowingArea(coordinates);
    });
}

function getAndDrawMowingArea() {
    fetch('/get-mowing-area', {
        method: 'GET',
    })
    .then(response => response.json())
    .then(data => {
        drawMowingArea(data);
    })
    .catch((error) => console.error('Error:', error));
}

function drawMowingArea(coordinates) {
    var polygon = new google.maps.Polygon({
        paths: coordinates,
        strokeColor: '#FF0000',
        strokeOpacity: 0.8,
        strokeWeight: 2,
        fillColor: '#FF0000',
        fillOpacity: 0.35,
        editable: true
    });
    polygon.setMap(map);
    google.maps.event.addListener(polygon.getPath(), 'set_at', function() {
        updateMowingArea(polygon);
    });
    google.maps.event.addListener(polygon.getPath(), 'insert_at', function() {
        updateMowingArea(polygon);
    });
}

function updateMowingArea(polygon) {
    var path = polygon.getPath();
    coordinates.length = 0;  // Clear the array
    for (var i = 0; i < path.getLength(); i++) {
        var lat = path.getAt(i).lat();
        var lng = path.getAt(i).lng();
        coordinates.push({lat: lat, lng: lng});
    }
    console.log(coordinates);
    // Save the new coordinates to the server
    saveMowingArea(coordinates);
}

function getPathAndDraw() {
    fetch('/get-path', {
        method: 'GET',
    })
    .then(response => response.json())
    .then(data => {
        drawPath(data);
    })
    .catch((error) => console.error('Error:', error));
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

window.addEventListener('load', function() {
    loadScript();
    getAndDrawMowingArea();
});

var socket = io.connect('http://' + document.domain + ':' + location.port);

socket.on('update_frame', function(data) {
    var image = document.getElementById('video_feed');
    image.src = 'data:image/jpeg;base64,' + data.frame;
});

// Request a new frame every 500ms (or whatever interval you prefer)
setInterval(function() {
    socket.emit('request_frame');  // Request a frame every 500ms
}, 500);
