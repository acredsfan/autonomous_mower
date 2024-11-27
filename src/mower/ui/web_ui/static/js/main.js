// main.js

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
let apiKey;
let pathPolyline = null;
let defaultCoordinates = {lat: DEFAULT_LAT, lng: DEFAULT_LNG};

// Function to fetch sensor data
function fetchSensorData() {
    fetch('/get_sensor_data')
        .then(response => response.json())
        .then(updateSensorDisplay)
        .catch(error => console.error('Error fetching sensor data:', error));
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
        .catch(error => console.error('Error:', error));
}

// Function to update areaCoordinates when the polygon's path changes
function updateAreaCoordinates() {
    if (areaPolygon) {
        areaCoordinates = areaPolygon.getPath().getArray().map(coord => ({
            lat: coord.lat(),
            lng: coord.lng()
        }));
        console.log('Updated areaCoordinates:', areaCoordinates);
        saveMowingArea();
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
        form.addEventListener('submit', event => {
            event.preventDefault();
            handleFormSubmission();
        });
    }
});

// Function to load the Google Maps script
function loadMapScript(apiKey, mapId) {
    const script = document.createElement('script');
    script.src = `https://maps.googleapis.com/maps/api/js?key=${apiKey}&v=beta&map_ids=${mapId}&libraries=drawing`;
    script.type = 'module';
    script.setAttribute('loading', 'async');
    script.onload = initMap;
    document.head.appendChild(script);
}

window.addEventListener('load', () => {
    Promise.all([
        fetch('/get_google_maps_api_key').then(response => response.json()),
        fetch('/get_map_id').then(response => response.json())
    ])
        .then(([keyData, mapIdData]) => {
            apiKey = keyData.api_key;
            mapId = mapIdData.map_id;
            if (!apiKey) {
                console.error('API key not found or invalid.');
                return;
            }
            loadMapScript(apiKey, mapId);
        })
        .catch(error => console.error('Error fetching API key or Map ID:', error));
});

// Function to initialize map
async function initMap() {
    const {Map: GoogleMap} = await google.maps.importLibrary('maps');
    const {DrawingManager} = await google.maps.importLibrary('drawing');

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
        drawingMode: null,
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

    // Fetch existing data
    const [polygonCoords, homeLoc, plannedPath] = await Promise.all([
        fetchMowingAreaPolygon(),
        fetchHomeLocation(),
        fetchPlannedPath()
    ]);

    // Display mowing area polygon
    if (polygonCoords.length > 0) {
        areaPolygon = new google.maps.Polygon({
            paths: polygonCoords,
            map: map,
            editable: true
    });
        areaCoordinates = polygonCoords;
        attachPolygonListeners(areaPolygon);
    }

    // Display home location marker
    if (homeLoc) {
        homeLocation = homeLoc;
    } else {
        homeLocation = coordinates;
    }

    homeLocationMarker = new google.maps.Marker({
        map: map,
        position: homeLocation,
        draggable: true,
        title: 'Robot Home Location - Drag to Change.',
        icon: {
            path: google.maps.SymbolPath.BACKWARD_CLOSED_ARROW,
            scale: 5,
            fillColor: '#00a1e0',
            fillOpacity: 1,
            strokeWeight: 1
        }
    });

    homeLocationMarker.addListener('dragend', function () {
        homeLocation = {
            lat: homeLocationMarker.getPosition().lat(),
            lng: homeLocationMarker.getPosition().lng()
        };
        saveHomeLocation();
    });

    // Display robot marker
    robotMarker = new google.maps.Marker({
        map: map,
        position: coordinates,
        title: 'Robot Current Position',
        icon: {
            path: google.maps.SymbolPath.CIRCLE,
            scale: 5,
            fillColor: '#FF0000',
            fillOpacity: 1,
            strokeWeight: 0
        }
    });

    // Display planned path
    if (plannedPath && plannedPath.length > 0) {
        const pathCoordinates = plannedPath.map(point => ({
            lat: point.lat,
            lng: point.lon
        }));
        pathPolyline = new google.maps.Polyline({
            path: pathCoordinates,
            geodesic: true,
            strokeColor: '#FF0000',
            strokeOpacity: 1.0,
            strokeWeight: 2,
            map: map
        });
    }

    // Update robot position periodically
    setInterval(async () => {
        const robotPosition = await fetchRobotPosition();
        if (robotPosition) {
            robotMarker.setPosition(robotPosition);
        }
    }, FETCH_INTERVAL);

    // Handle overlay complete events
    google.maps.event.addListener(drawingManager, 'overlaycomplete', function (event) {
        if (event.type === 'polygon') {
            if (areaPolygon) {
                areaPolygon.setMap(null);
            }
            areaPolygon = event.overlay;
            areaPolygon.setEditable(true);
            areaCoordinates = areaPolygon.getPath().getArray().map(coord => ({
                lat: coord.lat(),
                lng: coord.lng()
            }));
            attachPolygonListeners(areaPolygon);
            saveMowingArea();
        } else if (event.type === 'marker') {
            if (homeLocationMarker) {
                homeLocationMarker.setMap(null);
            }
            const position = event.overlay.getPosition();
            homeLocation = {
                lat: position.lat(),
                lng: position.lng()
            };
            homeLocationMarker = new google.maps.Marker({
                map: map,
                position: homeLocation,
                draggable: true,
                title: 'Robot Home Location - Drag to Change.',
                icon: {
                    path: google.maps.SymbolPath.BACKWARD_CLOSED_ARROW,
                    scale: 5,
                    fillColor: '#00a1e0',
                    fillOpacity: 1,
                    strokeWeight: 1
                }
            });
            homeLocationMarker.addListener('dragend', function () {
                homeLocation = {
                    lat: homeLocationMarker.getPosition().lat(),
                    lng: homeLocationMarker.getPosition().lng()
                };
                saveHomeLocation();
            });
            saveHomeLocation();
            event.overlay.setMap(null); // Remove the temporary marker
        }
    });
}

// Fetch functions
function fetchMowingAreaPolygon() {
    return fetch('/api/mowing-area')
        .then(response => response.json())
        .then(data => data.polygon || [])
        .catch(error => {
            console.error('Error fetching mowing area polygon:', error);
            return [];
        });
}

function fetchHomeLocation() {
    return fetch('/api/home-location')
        .then(response => response.json())
        .then(data => data.location)
        .catch(error => {
            console.error('Error fetching home location:', error);
            return null;
        });
}

function fetchPlannedPath() {
    return fetch('/api/planned-path')
        .then(response => response.json())
        .catch(error => {
            console.error('Error fetching planned path:', error);
            return [];
    });
}

function fetchRobotPosition() {
    return fetch('/api/robot-position')
        .then(response => response.json())
        .then(data => {
            if (data.lat && data.lon) {
                return {lat: data.lat, lng: data.lon};
            } else {
                console.error('Invalid robot position data:', data);
                return null;
            }
        })
        .catch(error => {
            console.error('Error fetching robot position:', error);
            return null;
        });
}

// Save functions
function saveMowingArea() {
    fetch('/api/mowing-area', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({polygon: areaCoordinates})
    })
        .then(response => response.json())
        .then(data => {
            console.log('Mowing area saved successfully');
            // Update planned path
            fetchPlannedPath().then(plannedPath => {
                if (pathPolyline) {
                    pathPolyline.setMap(null);
                }
                if (plannedPath && plannedPath.length > 0) {
                    const pathCoordinates = plannedPath.map(point => ({
                        lat: point.lat,
                        lng: point.lon
                    }));
                    pathPolyline = new google.maps.Polyline({
                        path: pathCoordinates,
                        geodesic: true,
                        strokeColor: '#FF0000',
                        strokeOpacity: 1.0,
                        strokeWeight: 2,
                        map: map
                    });
                }
            });
        })
        .catch(error => console.error('Error saving mowing area:', error));
}

function saveHomeLocation() {
    fetch('/api/home-location', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({location: homeLocation})
    })
        .then(response => response.json())
        .then(data => {
            console.log('Home location saved successfully');
        })
        .catch(error => console.error('Error saving home location:', error));
}
