function move(direction) {
    fetch('/move', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ direction: direction }),
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
        const mowDays = document.getElementById('mow-days').value;
        const mowHours = document.getElementById('mow-hours').value;
        // Get other settings inputs here

        saveSettings(mowDays, mowHours);
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
    var image = document.getElementById('camera_feed');
    image.src = 'data:image/jpeg;base64,' + data.frame;
});

// Request a new frame every 500ms (or whatever interval you prefer)
setInterval(function() {
    socket.emit('request_frame');
}, 500);