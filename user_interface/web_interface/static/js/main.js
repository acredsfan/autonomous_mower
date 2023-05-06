function move(direction) {
    fetch('url_to_your_flask_route', {
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
    fetch('url_to_your_flask_route', {
        method: 'POST',
    })
    .then(response => response.json())
    .then(data => console.log(data))
    .catch((error) => console.error('Error:', error));
}

function stopMowing() {
    fetch('url_to_your_flask_route', {
        method: 'POST',
    })
    .then(response => response.json())
    .then(data => console.log(data))
    .catch((error) => console.error('Error:', error));
}

function saveMowingArea(coordinates) {
    fetch('url_to_your_flask_route', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ coordinates: coordinates }),
    })
    .then(response => response.json())
    .then(data => console.log(data))
    .catch((error) => console.error('Error:', error));
}


document.getElementById('settings-form').addEventListener('submit', function (event) {
    event.preventDefault();

    const mowDays = document.getElementById('mow-days').value;
    const mowHours = document.getElementById('mow-hours').value;
    // Get other settings inputs here

    saveSettings(mowDays, mowHours);
});

function saveSettings(mowDays, mowHours) {
    fetch('url_to_your_flask_route', {
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

