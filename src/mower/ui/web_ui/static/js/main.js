// Constants
const DEFAULT_LAT = 39.095657;
const DEFAULT_LNG = -84.515959;
const FETCH_INTERVAL = 1000;

// Global variables
let areaCoordinates = [];
let homeLocation = null;
let map;
let areaPolygon = null;
let homeLocationMarker = null;
let robotMarker = null;
let mapId;
let objDetIp = null;
let apiKey;
let pathPolyline = null;
let defaultCoordinates = {lat: DEFAULT_LAT, lng: DEFAULT_LNG}; // Use the constants

// Function to fetch sensor data
function fetchSensorData() {
    fetch('/get_sensor_data')
        .then(response => response.json())
        .then(updateSensorDisplay)
        .catch((error) => console.error('Error fetching sensor data:', error));
}

setInterval(fetchSensorData, FETCH_INTERVAL);

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
        'right_distance': `Right Distance: ${data.right_distance}`
    };
    for (const [id, text] of Object.entries(elements)) {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = text;
        }
    }
}

// Function to save settings for mowing days and hours
function saveSettings(mowDays, mowHours, patternType) {
    fetch('/save_settings', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({mowDays, mowHours, patternType})
    })
    .then(response => response.json())
        .then(data => alert('Settings saved successfully.'))
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

// Function to handle form submission
function handleFormSubmission() {
    const mowDays = document.querySelectorAll('input[name="mowDays"]:checked');
    const mowHours = document.querySelectorAll('input[name="mowHours"]:checked');
    const patternType = document.getElementById('patternType').value;
    const selectedDays = Array.from(mowDays).map(input => input.value);
    const selectedHours = Array.from(mowHours).map(input => input.value);
    saveSettings(selectedDays, selectedHours, patternType);
}

document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('settings-form');
    if (form) {
        form.addEventListener('submit', (event) => {
            event.preventDefault();
            handleFormSubmission();
        });
    }
});

// Function to load the Google Maps script
function loadMapScript(apiKey, mapId) {
    const script = document.createElement('script');
    script.src = `https://maps.googleapis.com/maps/api/js?key=${apiKey}&v=beta&map_ids=${mapId}&libraries=drawing,marker`;
    script.type = 'module';
    script.setAttribute('loading', 'async');
    script.onload = initMap;  // Ensure the initMap function is called correctly
    document.head.appendChild(script);
}

window.addEventListener('load', () => {
    Promise.all([
        fetch('/get_google_maps_api_key').then(response => response.json()),
        fetch('/get_map_id').then(response => response.json())
    ]).then(([keyData, mapIdData]) => {
        apiKey = keyData.api_key;
        mapId = mapIdData.map_id;
        if (!apiKey) {
            console.error('API key not found or invalid.');
            return;
        }
        loadMapScript(apiKey, mapId);
    }).catch(error => console.error('Error fetching API key or Map ID:', error));

    document.getElementById('confirm-area-button')?.addEventListener('click', saveMowingArea);
    document.getElementById('confirm-home-button')?.addEventListener('click', saveHomeLocation);
});

// Function to initialize map
async function initMap() {
    const { Map: GoogleMap } = await google.maps.importLibrary("maps");
    const { AdvancedMarkerElement, PinElement } = await google.maps.importLibrary("marker");
    const { DrawingManager } = await google.maps.importLibrary("drawing");

    let coordinates = await fetch('/get_default_coordinates')
        .then(response => response.json())
        .catch(() => ({lat: DEFAULT_LAT, lng: DEFAULT_LNG}));

    coordinates.lat = parseFloat(coordinates.lat);
    coordinates.lng = parseFloat(coordinates.lng);

    if (isNaN(coordinates.lat) || isNaN(coordinates.lng)) {
        coordinates = {lat: DEFAULT_LAT, lng: DEFAULT_LNG};
    }

    map = new GoogleMap(document.getElementById('map'), {
        zoom: 20,
        center: coordinates,
        mapTypeId: 'satellite',
        mapId
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
    drawingManager.setMap(map);

    const pinBackground = new PinElement({background: "#00a1e0"});
    const robotPin = new PinElement({background: "#FF0000"});

    homeLocationMarker = new AdvancedMarkerElement({
        map,
        position: homeLocation || coordinates,
        gmpDraggable: true,
        title: "Robot Home Location - Drag to Change.",
        content: pinBackground.element
    });

    robotMarker = new AdvancedMarkerElement({
        map,
        position: coordinates,
        title: 'Robot Current Position',
        content: robotPin.element
    });
}