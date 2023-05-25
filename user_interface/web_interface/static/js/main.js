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
    fetch('stop-mowing', {
        method: 'POST',
    })
    .then(response => response.json())
    .then(data => console.log(data))
    .catch((error) => console.error('Error:', error));
}

const fs = require('fs');

function saveMowingArea(coordinates) {
    // Convert the coordinates to a JSON string
    var data = JSON.stringify(coordinates);
    
    // Create a Blob object with the data
    var blob = new Blob([data], {type: 'application/json'});
    
    // Create a URL for the Blob object
    var url = URL.createObjectURL(blob);
    
    // Create a link element
    var a = document.createElement('a');
    a.download = 'user_polygon.json';
    a.href = url;
    
    // Append the link to the body
    document.body.appendChild(a);
    
    // Simulate a click on the link
    a.click();
    
    // Remove the link from the body
    document.body.removeChild(a);
}


document.addEventListener('DOMContentLoaded', (event) => {
    document.getElementById('settings-form').addEventListener('submit', function (event) {
        event.preventDefault();
    
        const mowDays = document.getElementById('mow-days').value;
        const mowHours = document.getElementById('mow-hours').value;
        // Get other settings inputs here
    
        saveSettings(mowDays, mowHours);
    });
});

function saveSettings(mowDays, mowHours) {
    fetch('save_settings', {
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

function initMap() {
    var map = new google.maps.Map(document.getElementById('map'), {
        zoom: 20,
        tilt: 0,
        view: 'satellite',
        center: {lat: 39.038542, lng: -84.214696}
    });

    var drawingManager = new google.maps.drawing.DrawingManager({
        drawingMode: google.maps.drawing.OverlayType.POLYGON,
        drawingControl: true,
        drawingControlOptions: {
            position: google.maps.ControlPosition.TOP_CENTER,
            drawingModes: ['polygon']
        }
    });
    drawingManager.setMap(map);

    google.maps.event.addListener(drawingManager, 'polygoncomplete', function(polygon) {
        var path = polygon.getPath();
        var coordinates = [];
        for (var i = 0; i < path.getLength(); i++) {
            var lat = path.getAt(i).lat();
            var lng = path.getAt(i).lng();
            coordinates.push({lat: lat, lng: lng});
        }
        console.log(coordinates);
        // Send coordinates to server
        // ...
    });
}

var submitBtn = document.getElementById('confirm-button');
submitBtn.addEventListener('click', function() {
    console.log('Submit button clicked');
    // Send coordinates to server
    // ...
});