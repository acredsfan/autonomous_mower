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

function saveMowingArea(coordinates) {
    // Make an AJAX POST request to the server to save the mowing area
    $.ajax({
        url: '/save-mowing-area',
        type: 'POST',
        data: JSON.stringify(coordinates),
        contentType: 'application/json; charset=utf-8',
        dataType: 'json',
        success: function(response) {
            console.log('Mowing area saved:', response);
        },
        error: function(xhr, status, error) {
            console.error('Error saving mowing area:', error);
        }
    });
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
    document.getElementById('settings-form').addEventListener('submit', function (event) {
        event.preventDefault();

        const mowDays = document.getElementById('mow-days').value;
        const mowHours = document.getElementById('mow-hours').value;
        // Get other settings inputs here

        saveSettings(mowDays, mowHours);
    });
});

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

    var coordinates = [];

    google.maps.event.addListener(drawingManager, 'polygoncomplete', function(polygon) {
        var path = polygon.getPath();
        coordinates.length = 0;  // Clear the array
        for (var i = 0; i < path.getLength(); i++) {
            var lat = path.getAt(i).lat();
            var lng = path.getAt(i).lng();
            coordinates.push({lat: lat, lng: lng});
        }
        console.log(coordinates);
        // Send coordinates to server
        // ...
    });

    var submitBtn = document.getElementById('confirm-button');
    submitBtn.addEventListener('click', function() {
        console.log('Submit button clicked');
        // Now the click listener has access to the coordinates array
        saveMowingArea(coordinates);
    });
}