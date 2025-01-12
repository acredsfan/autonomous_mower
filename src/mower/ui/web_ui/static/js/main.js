// Modernized JavaScript with Fixes

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
const defaultCoordinates = {lat: DEFAULT_LAT, lng: DEFAULT_LNG};

// Utility function for fetch requests with error handling
async function fetchWithLogging(url, options = {}) {
    try {
        const response = await fetch(url, options);
        if (!response.ok) {
            console.error(`Error fetching ${url}: ${response.statusText}`);
            throw new Error(`HTTP error! Status: ${response.status}`);
        }
        return response.json();
    } catch (error) {
        console.error(`Fetch failed for ${url}:`, error);
        return null; // Return null to handle gracefully
    }
}

// Function to fetch sensor data
async function fetchSensorData() {
    const data = await fetchWithLogging('/get_sensor_data');
    if (data) updateSensorDisplay(data);
}

setInterval(fetchSensorData, FETCH_INTERVAL);

// Function to update sensor display
function updateSensorDisplay(data) {
    const elements = {
        battery_voltage: `Battery Voltage: ${data.battery_voltage}`,
        battery_current: `Battery Current: ${data.battery_current}`,
        battery_charge: `Battery Charge: ${data.battery_charge_level}`,
        solar_voltage: `Solar Voltage: ${data.solar_voltage}`,
        solar_current: `Solar Current: ${data.solar_current}`,
        speed: `Speed: ${data.speed}`,
        heading: `Heading: ${data.heading}`,
        pitch: `Pitch: ${data.pitch}`,
        roll: `Roll: ${data.roll}`,
        temperature: `Temperature: ${data.temperature}`,
        humidity: `Humidity: ${data.humidity}`,
        pressure: `Pressure: ${data.pressure}`,
        left_distance: `Left Distance: ${data.left_distance}`,
        right_distance: `Right Distance: ${data.right_distance}`
    };
    for (const [id, text] of Object.entries(elements)) {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = text;
        }
    }
}

// Function to save settings for mowing days and hours
async function saveSettings(mowDays, mowHours, patternType) {
    const response = await fetchWithLogging('/save_settings', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({mowDays, mowHours, patternType})
    });
    if (response) alert('Settings saved successfully.');
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

window.addEventListener('load', async () => {
    const [keyData, mapIdData] = await Promise.all([
        fetchWithLogging('/get_google_maps_api_key'),
        fetchWithLogging('/get_map_id')
    ]);

    if (keyData && mapIdData) {
        apiKey = keyData.api_key;
        mapId = mapIdData.map_id;
        if (apiKey) loadMapScript(apiKey, mapId);
        else console.error('API key not found or invalid.');
    }
});

// Function to initialize map
async function initMap() {
    const {Map: GoogleMap, DrawingManager} = await google.maps.importLibrary(['maps', 'drawing']);

    const coordinates = await fetchWithLogging('/get_default_coordinates') || defaultCoordinates;
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
            drawingModes: ['polygon', 'marker']
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
    homeLocation = homeLoc || coordinates;
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
    homeLocationMarker.addListener('dragend', saveHomeLocation);

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

    // Update robot position periodically
    setInterval(async () => {
        const robotPosition = await fetchRobotPosition();
        if (robotPosition) robotMarker.setPosition(robotPosition);
    }, FETCH_INTERVAL);
}

// Fetch functions
async function fetchMowingAreaPolygon() {
    const data = await fetchWithLogging('/api/mowing-area');
    return data ? data.polygon : [];
}

async function fetchHomeLocation() {
    const data = await fetchWithLogging('/api/home-location');
    return data ? data.location : null;
}

async function fetchPlannedPath() {
    const data = await fetchWithLogging('/api/planned-path');
    return data || [];
}

async function fetchRobotPosition() {
    const data = await fetchWithLogging('/api/robot-position');
    if (data?.lat && data?.lon) {
        return {lat: data.lat, lng: data.lon};
    } else {
        console.error('Invalid robot position data:', data);
        return null;
    }
}

// Save functions
async function saveMowingArea() {
    const response = await fetchWithLogging('/api/mowing-area', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({polygon: areaCoordinates})
    });
    if (response) {
        console.log('Mowing area saved successfully');
        const plannedPath = await fetchPlannedPath();
        if (pathPolyline) pathPolyline.setMap(null);
        if (plannedPath.length > 0) {
            const pathCoordinates = plannedPath.map(point => ({lat: point.lat, lng: point.lon}));
            pathPolyline = new google.maps.Polyline({
                path: pathCoordinates,
                geodesic: true,
                strokeColor: '#FF0000',
                strokeOpacity: 1.0,
                strokeWeight: 2,
                map: map
            });
        }
    }
}

async function saveHomeLocation() {
    const response = await fetchWithLogging('/api/home-location', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({location: homeLocation})
    });
    if (response) console.log('Home location saved successfully');
}
