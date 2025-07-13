/**
 * Autonomous Mower Web Interface JavaScript
 *
 * Manages the WebSocket connection, real-time updates, and UI interactions
 * for the autonomous mower control interface.
 */

// Initialize socket connection when the document is ready
let socket;
let isConnected = false;
let reconnectAttempts = 0;
const MAX_RECONNECT_ATTEMPTS = 5;
const RECONNECT_DELAY = 3000; // 3 seconds

// Store for system state
const systemState = {
  battery: {
    voltage: 0,
    percentage: 0,
    charging: false,
  },
  gps: {
    satellites: 0,
    fix: false,
    latitude: 0,
    longitude: 0,
  },
  imu: {
    heading: 0,
    roll: 0,
    pitch: 0,
  },
  motors: {
    leftSpeed: 0,
    rightSpeed: 0,
    bladeSpeed: 0,
  },
  status: {
    mowerState: "IDLE",
    errorMessage: "",
    currentAction: "",
    autonomousMode: false,
  },
  sensors: {
    temperature: 0,
    humidity: 0,
    pressure: 0,
    leftDistance: 0,
    rightDistance: 0,
  },
  position: {
    currentPosition: [0, 0],
    homePosition: [0, 0],
    waypoints: [],
  },
  units: {
    temperature: localStorage.getItem('temperatureUnit') || 'celsius',
    distance: localStorage.getItem('distanceUnit') || 'metric'
  }
};

// Helper function to format sensor values (handles N/A)
function formatSensorValue(value, format = 'number', unit = '') {
  if (value === "N/A" || value === null || value === undefined || isNaN(value)) {
    return "N/A";
  }

  if (format === 'number') {
    return `${Number(value).toFixed(1)}${unit}`;
  } else if (format === 'integer') {
    return `${Math.round(Number(value))}${unit}`;
  }

  return `${value}${unit}`;
}

// Unit conversion functions
function normalizeToCelsius(temp) {
  let value = parseFloat(temp);
  if (typeof temp === 'string' && temp.toUpperCase().includes('F')) {
    value = (parseFloat(temp) - 32) * 5/9;
  } else if (value > 60) {
    value = (value - 32) * 5/9;
  }
  return value;
}

function convertTemperature(celsius, unit) {
  const base = normalizeToCelsius(celsius);
  if (unit === 'fahrenheit') {
    return {
      value: (base * 9/5) + 32,
      unit: '°F'
    };
  }
  return {
    value: base,
    unit: '°C'
  };
}

function convertDistance(mm, unit) {
  if (unit === 'imperial') {
    return {
      value: mm * 0.0393701, // mm to inches
      unit: 'in'
    };
  }
  return {
    value: mm / 10, // mm to cm for metric
    unit: 'cm'
  };
}

// Safely parse numbers from backend values
function parseNumber(value, fallback = null) {
  const num = parseFloat(value);
  return isNaN(num) ? fallback : num;
}

// Load user preferences
function loadUserPreferences() {
  systemState.units.temperature = localStorage.getItem('temperatureUnit') || 'celsius';
  systemState.units.distance = localStorage.getItem('distanceUnit') || 'metric';

  // Update UI to reflect preferences
  const tempRadios = document.querySelectorAll('input[name="temperature_units"]');
  tempRadios.forEach(radio => {
    if (radio.value === systemState.units.temperature) {
      radio.checked = true;
    }
  });

  const distRadios = document.querySelectorAll('input[name="distance_units"]');
  distRadios.forEach(radio => {
    if (radio.value === systemState.units.distance) {
      radio.checked = true;
    }
  });

  // Update all unit labels
  updateUnitLabels();
}

// Save user preferences
function saveUserPreferences() {
  localStorage.setItem('temperatureUnit', systemState.units.temperature);
  localStorage.setItem('distanceUnit', systemState.units.distance);
}

// Update all unit labels throughout the interface
function updateUnitLabels() {
  const tempUnit = systemState.units.temperature === 'fahrenheit' ? '°F' : '°C';
  const distUnit = systemState.units.distance === 'imperial' ? 'in' : 'cm';

  // Update main sensor reading labels
  const tempLabel = document.querySelector('.sensor-label[data-unit="temperature"]');
  if (tempLabel) tempLabel.textContent = `Temperature (${tempUnit})`;

  const leftDistLabel = document.querySelector('.sensor-label[data-unit="left-distance"]');
  if (leftDistLabel) leftDistLabel.textContent = `Left Distance (${distUnit})`;

  const rightDistLabel = document.querySelector('.sensor-label[data-unit="right-distance"]');
  if (rightDistLabel) rightDistLabel.textContent = `Right Distance (${distUnit})`;

  // Update other temperature displays
  const elements = document.querySelectorAll('[data-temp-unit]');
  elements.forEach(element => {
    const currentText = element.textContent;
    if (currentText.includes('°C') || currentText.includes('°F')) {
      // Update existing temperature display
      const value = currentText.replace(/[°CF]/g, '');
      element.textContent = value + tempUnit;
    }
  });

  // Update chart labels if they exist
  const chartTempLabel = document.querySelector('[data-chart-temp-label]');
  if (chartTempLabel) chartTempLabel.textContent = `Temperature (${tempUnit})`;

  // Re-apply sensor data with new units if available
  if (window.lastSensorData) {
    updateSensorData(window.lastSensorData);
  }
}

// Initialize when DOM is ready
document.addEventListener("DOMContentLoaded", function () {
  loadUserPreferences();
  initializeUI();
  setupEventListeners();
});

setupSocketConnection();

/**
 * Initialize the UI components and set default values
 */
function initializeUI() {
  updateConnectionStatus(false);

  // Initialize language selector
  initializeLanguageSelector();

  // Initialize theme selector
  initializeThemeSelector();

  // Initialize any charts or visualizations
  if (typeof initializeCharts === "function") {
    initializeCharts();
  }

  // Initialize map if on map page (guard against duplicate init)
  if (typeof initializeMap === "function") {
    try {
      initializeMap();
    } catch (e) {
      console.warn("Map initialization skipped (already initialized or error):", e);
    }
  }

  // Initialize joystick if on control page
  if (typeof initializeJoystick === "function") {
    initializeJoystick();
  }

  // Show a welcome message in the alerts container
  showAlert("System initializing. Connecting to mower...", "info");
}

/**
 * Set up the Socket.IO connection to the server
 */
function setupSocketConnection() {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const socketUrl = `${protocol}//${window.location.host}`;

  // Initialize socket connection with enhanced configuration for Cloudflare tunnels
  socket = io({ 
    transports: ['polling', 'websocket'],
    upgrade: true,
    rememberUpgrade: false,
    timeout: 10000,
    forceNew: true,
    withCredentials: true,
    extraHeaders: {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Credentials': 'true'
    }
  });

  // Connection established
  socket.on("connect", function () {
    isConnected = true;
    reconnectAttempts = 0;
    updateConnectionStatus(true);
    showAlert("Connected to mower system", "success", 3000);

    // Request initial data
    socket.emit("request_data", { type: "all" });
  });

  // Connection lost
  socket.on("disconnect", function () {
    isConnected = false;
    updateConnectionStatus(false);
    showAlert("Connection lost. Attempting to reconnect...", "warning");

    attemptReconnect();
  });

  // Handle errors with enhanced logging for Cloudflare tunnel issues
  socket.on("connect_error", function (error) {
    isConnected = false;
    updateConnectionStatus(false);
    console.error("Connection error:", error);
    console.error("Error type:", error.type);
    console.error("Error description:", error.description);
    
    // Enhanced error messages for common Cloudflare tunnel issues
    let errorMessage = "Connection error: " + error.message;
    if (error.type === 'TransportError' && window.location.hostname.includes('cloudflareaccess.com')) {
      errorMessage = "Cloudflare Access authentication issue. Please refresh the page.";
    } else if (error.description && error.description.includes('CORS')) {
      errorMessage = "CORS error through tunnel. Connection may be blocked by authentication.";
    }
    
    showAlert(errorMessage, "danger");
    attemptReconnect();
  });

  // Handle system status updates
  socket.on("status_update", function (data) {
    updateSystemStatus(data);
  });

  // Handle sensor data updates
  socket.on("sensor_data", function (data) {
    // console.log("Received sensor data:", data);
    updateSensorData(data);
  });

  // Handle position updates
  socket.on("position_update", function (data) {
    updatePositionData(data);
  });

  // Handle command responses
  socket.on("command_response", function (data) {
    handleCommandResponse(data);
  });

  // Handle alert messages from server
  socket.on("alert", function (data) {
    showAlert(data.message, data.type, data.duration);
  });
}

/**
 * Attempt to reconnect after connection loss
 */
function attemptReconnect() {
  if (reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
    showAlert(
      "Maximum reconnection attempts reached. Please refresh the page.",
      "danger"
    );
    return;
  }

  reconnectAttempts++;

  setTimeout(function () {
    if (!isConnected) {
      socket.connect();
      showAlert(
        `Reconnection attempt ${reconnectAttempts}/${MAX_RECONNECT_ATTEMPTS}...`,
        "info"
      );
    }
  }, RECONNECT_DELAY * reconnectAttempts);
}

/**
 * Set up event listeners for UI elements
 */
function setupEventListeners() {
  // Quick controls in the sidebar
  const startMowingBtn = document.getElementById("startMowingBtn");
  const stopMowingBtn = document.getElementById("stopMowingBtn");
  const returnHomeBtn = document.getElementById("returnHomeBtn");

  if (startMowingBtn) {
    startMowingBtn.addEventListener("click", function () {
      sendCommand("start_mowing");
    });
  }

  if (stopMowingBtn) {
    stopMowingBtn.addEventListener("click", function () {
      sendCommand("stop");
    });
  }

  if (returnHomeBtn) {
    returnHomeBtn.addEventListener("click", function () {
      sendCommand("return_home");
    });
  }

  // Unit preference controls
  const tempRadios = document.querySelectorAll('input[name="temperature_units"]');
  tempRadios.forEach(radio => {
    radio.addEventListener('change', function() {
      if (this.checked) {
        systemState.units.temperature = this.value;
        saveUserPreferences();
        updateUnitLabels(); // Update labels immediately
        // Trigger UI refresh with new units
        if (window.lastSensorData) {
          updateSensorData(window.lastSensorData);
        }
      }
    });
  });

  const distRadios = document.querySelectorAll('input[name="distance_units"]');
  distRadios.forEach(radio => {
    radio.addEventListener('change', function() {
      if (this.checked) {
        systemState.units.distance = this.value;
        saveUserPreferences();
        updateUnitLabels(); // Update labels immediately
        // Trigger UI refresh with new units
        if (window.lastSensorData) {
          updateSensorData(window.lastSensorData);
        }
      }
    });
  });

  // Set up page-specific event listeners
  setupPageSpecificListeners();
}

/**
 * Set up event listeners specific to the current page
 */
function setupPageSpecificListeners() {
  // Control page buttons
  const controlButtons = document.querySelectorAll(".control-btn");
  if (controlButtons.length > 0) {
    controlButtons.forEach((button) => {
      button.addEventListener("click", function () {
        const command = this.dataset.command;
        const params = this.dataset.params
          ? JSON.parse(this.dataset.params)
          : {};
        sendCommand(command, params);
      });
    });
  }

  // Settings form
  const settingsForm = document.getElementById("settingsForm");
  if (settingsForm) {
    settingsForm.addEventListener("submit", function (e) {
      e.preventDefault();
      const formData = new FormData(this);
      const settings = {};

      for (const [key, value] of formData.entries()) {
        settings[key] = value;
      }

      sendCommand("update_settings", settings);
    });
  }
}

/**
 * Send a command to the server
 *
 * @param {string} command - The command to send
 * @param {Object} params - Optional parameters for the command
 */
function sendCommand(command, params = {}) {
  if (!isConnected) {
    console.error("Cannot send command - not connected:", command, params);
    showAlert("Cannot send command: Not connected to the server", "danger");
    return;
  }

  console.log("Sending command through SocketIO:", command, params);
  console.log("Current connection transport:", socket.io.engine.transport.name);
  console.log("Socket connected:", socket.connected);
  showAlert(`Sending command: ${command}`, "info", 2000);

  try {
    socket.emit("control_command", {
      command: command,
      params: params,
    });
    console.log("Command emitted successfully:", command);
    
    // Add response listener for debugging
    socket.off('command_response'); // Remove previous listener
    socket.on('command_response', function(response) {
      console.log("Command response received:", response);
      if (response.success) {
        showAlert(`Command ${response.command} succeeded: ${response.message || 'OK'}`, "success", 3000);
      } else {
        console.error("Command failed:", response);
        showAlert(`Command ${response.command} failed: ${response.error}`, "danger", 5000);
      }
    });
    
  } catch (error) {
    console.error("Error emitting command:", error);
    showAlert("Error sending command: " + error.message, "danger");
  }
}

/**
 * Update the connection status indicator
 *
 * @param {boolean} connected - Whether the system is connected
 */
function updateConnectionStatus(connected) {
  const statusIndicator = document.getElementById("connectionStatus");
  const statusText = document.getElementById("connectionText");

  if (statusIndicator && statusText) {
    if (connected) {
      statusIndicator.className = "status-indicator status-online";
      statusText.textContent = "Connected";
    } else {
      statusIndicator.className = "status-indicator status-offline";
      statusText.textContent = "Disconnected";
    }
  }
}

/**
 * Update the system status display with new data
 *
 * @param {Object} data - Status data from the server
 */
function updateSystemStatus(data) {
  // Update our internal state
  Object.assign(systemState.status, data);

  // Update battery status display
  if (data.battery !== undefined) {
    Object.assign(systemState.battery, data.battery);
    const batteryDisplay = document.getElementById("batteryDisplay");
    const batteryStatus = document.getElementById("batteryStatus");
    const batteryVoltageElem = document.getElementById("batteryVoltage");
    const chargingStatusElem = document.getElementById("chargingStatus");
    const pct = Math.round(parseFloat(systemState.battery.percentage) || 0);
    if (batteryDisplay) batteryDisplay.textContent = `${pct}%`;
    if (batteryStatus) batteryStatus.textContent = `${pct}%`;
    if (batteryVoltageElem) {
      const bvNum = parseNumber(systemState.battery.voltage);
      if (bvNum != null) batteryVoltageElem.textContent = `${bvNum.toFixed(1)} V`;
    }
    if (chargingStatusElem) chargingStatusElem.innerHTML = systemState.battery.charging ? '<i class="fas fa-bolt"></i>' : '';
    // Color coding
    if (batteryDisplay) {
      if (pct < 20) batteryDisplay.className = "text-danger";
      else if (pct < 40) batteryDisplay.className = "text-warning";
      else batteryDisplay.className = "";
    }
  }

  // Update mower state
  if (data.state !== undefined) {
    const mowerStateElem = document.getElementById("mowerStateDisplay");
    const mowerStatusElem = document.getElementById("mowerStatus");
    const formattedState = formatRobotState(data.state);
    if (mowerStateElem) {
      mowerStateElem.textContent = formattedState;
      if (data.state === "ERROR" || data.state === "EMERGENCY_STOP") mowerStateElem.className = "text-danger";
      else if (data.state === "MOWING" || data.state === "AVOIDING") mowerStateElem.className = "text-success";
      else mowerStateElem.className = "";
    }
    if (mowerStatusElem) mowerStatusElem.textContent = formattedState;
  }

  // Update GPS status display
  if (data.gps !== undefined) {
    Object.assign(systemState.gps, data.gps);
    const gpsStatusElem = document.getElementById("gpsStatusDisplay");
    const gpsStatusSidebar = document.getElementById("gpsStatus");
    const satCountElem = document.getElementById("satelliteCount");
    const statusText = systemState.gps.fix ? `${systemState.gps.satellites} satellites` : 'No fix';
    if (gpsStatusElem) {
      gpsStatusElem.textContent = statusText;
      gpsStatusElem.className = systemState.gps.fix ? (systemState.gps.satellites >= 4 ? "text-success" : "text-warning") : "text-danger";
    }
    if (gpsStatusSidebar) gpsStatusSidebar.textContent = statusText;
    if (satCountElem) satCountElem.textContent = `${systemState.gps.satellites} satellites`;
  }

  // Update additional status elements if they exist
  updateAdditionalStatusElements();
}

/**
 * Format robot state enum values into user-friendly strings
 *
 * @param {string} state - Robot state from the server
 * @returns {string} User-friendly state description
 */
function formatRobotState(state) {
  const stateMap = {
    IDLE: "Idle",
    INITIALIZING: "Starting Up",
    MANUAL_CONTROL: "Manual Control",
    MOWING: "Mowing",
    AVOIDING: "Avoiding Obstacle",
    RETURNING_HOME: "Returning Home",
    DOCKED: "Docked",
    ERROR: "Error",
    EMERGENCY_STOP: "Emergency Stop",
  };

  return stateMap[state] || state;
}

/**
 * Update any additional status elements that may be page-specific
 */
function updateAdditionalStatusElements() {
  // Current action display
  const currentActionElement = document.getElementById("currentAction");
  if (currentActionElement && systemState.status.currentAction) {
    currentActionElement.textContent = systemState.status.currentAction;
  }

  // Error message display
  const errorMessageElement = document.getElementById("errorMessage");
  if (errorMessageElement) {
    if (systemState.status.errorMessage) {
      errorMessageElement.textContent = systemState.status.errorMessage;
      errorMessageElement.parentElement.style.display = "block";
    } else {
      errorMessageElement.parentElement.style.display = "none";
    }
  }

  // Mode indicator (Autonomous/Manual)
  const modeIndicator = document.getElementById("modeIndicator");
  if (modeIndicator) {
    modeIndicator.textContent = systemState.status.autonomousMode
      ? "Autonomous"
      : "Manual";
    modeIndicator.className = systemState.status.autonomousMode
      ? "text-success"
      : "text-warning";
  }
}

/**
 * Update sensor data displays with new data
 *
 * @param {Object} data - Sensor data from the server
 */
function updateSensorData(data) {
  try {
    // Store last sensor data for unit conversions
    window.lastSensorData = data;
    // Update battery and solar from sensor data
    if (data.power) {
      const power = data.power;

      // Update battery data
      systemState.battery.voltage = parseNumber(power.bus_voltage ?? power.voltage);
      systemState.battery.percentage = parseNumber(power.percentage, 0);
      systemState.battery.charging = power.charging || false;

      // Update battery UI (sidebar and dashboard)
      const dashPct = Math.round(systemState.battery.percentage);
      const bd = document.getElementById("batteryDisplay");
      const bs = document.getElementById("batteryStatus");
      const bv = document.getElementById("batteryVoltage");
      const bc = document.getElementById("batteryCurrent");
      const ch = document.getElementById("chargingStatus");

      if (bd) bd.textContent = `${dashPct}%`;
      if (bs) bs.textContent = `${dashPct}%`;
      if (bv) {
        const bvNum = parseNumber(power);
        if (bvNum != null) bv.textContent = `${bvNum.toFixed(1)} V`;
      }
      if (bc && power.current != null && power.current !== "N/A") {
        const curr = parseNumber(power.current);
        if (curr != null) bc.textContent = `${Math.abs(curr).toFixed(1)} A`;
      }
      if (ch) ch.innerHTML = systemState.battery.charging ? '<i class="fas fa-bolt"></i>' : '';

      // Update solar panel data
      const svd = document.getElementById("solarVoltageDisplay");
      const sc = document.getElementById("solarCurrent");
      const sp = document.getElementById("solarPower");

      if (svd && power.solar_voltage != null && power.solar_voltage !== "N/A") {
        const sv = parseNumber(power.solar_voltage);
        if (sv != null) svd.textContent = `${sv.toFixed(1)} V`;
      }
      if (sc && power.solar_current != null && power.solar_current !== "N/A") {
        const scurr = parseNumber(power.solar_current);
        if (scurr != null) sc.textContent = `${scurr.toFixed(1)} A`;
      }
      if (sp && power.solar_power != null && power.solar_power !== "N/A") {
        const spw = parseNumber(power.solar_power);
        if (spw != null) sp.textContent = `${spw.toFixed(1)} W`;
      }
    }
    // Update GPS from sensor data
    if (data.gps) {
      const gps = data.gps;
      systemState.gps.latitude = gps.latitude;
      systemState.gps.longitude = gps.longitude;
      systemState.gps.satellites = gps.satellites;
      // Determine fix status - valid GPS should show coordinates
      systemState.gps.fix = gps.fix && gps.status && gps.status.toLowerCase() === 'valid';
      // Update GPS UI (sidebar and dashboard)
      const dashGps = document.getElementById("gpsStatusDisplay");
      const sideGps = document.getElementById("gpsStatus");
      const sc = document.getElementById("satelliteCount");
      const statusText = systemState.gps.fix ? `${systemState.gps.satellites} satellites` : 'No fix';
      if (dashGps) dashGps.textContent = statusText;
      if (sideGps) sideGps.textContent = statusText;
      if (sc) sc.textContent = `${systemState.gps.satellites} satellites`;

      // Update coordinate display from GPS data
      const latElement = document.getElementById("position_latitude");
      const lngElement = document.getElementById("position_longitude");
      if (latElement && lngElement && systemState.gps.fix) {
        latElement.textContent = Number(systemState.gps.latitude).toFixed(6);
        lngElement.textContent = Number(systemState.gps.longitude).toFixed(6);
      } else if (latElement && lngElement) {
        latElement.textContent = "0.000000";
        lngElement.textContent = "0.000000";
      }

      // Update map with GPS coordinates if we have a valid fix
      if (systemState.gps.fix && typeof updateMap === "function") {
        const mapData = {
          currentPosition: [systemState.gps.latitude, systemState.gps.longitude]
        };
        updateMap(mapData);
      }
    }
    // Update our internal state for other top-level sensor properties
    if (data && typeof data === 'object') {
      Object.assign(systemState.sensors, data);
    } else {
      console.warn('Received invalid sensor data:', data);
      return;
    }

    // Update temperature from environment sensor data
    if (data.environment && data.environment.temperature !== undefined) {
      document.querySelectorAll('#sensor_temperature').forEach(tempElement => {
        if (data.environment.temperature === 'N/A') {
          tempElement.textContent = 'N/A';
        } else {
          const temp = convertTemperature(data.environment.temperature, systemState.units.temperature);
          tempElement.textContent = formatSensorValue(temp.value, 'number', temp.unit);
        }
      });
    }

    // Update humidity from environment sensor data
    if (data.environment && data.environment.humidity !== undefined) {
      document.querySelectorAll('#sensor_humidity').forEach(humidityElement => {
        humidityElement.textContent = formatSensorValue(data.environment.humidity, 'number', '%');
      });
    }

    // Update pressure from environment sensor data
    if (data.environment && data.environment.pressure !== undefined) {
        const pressureElement = document.getElementById("sensor_pressure");
        if (pressureElement) {
            pressureElement.textContent = formatSensorValue(data.environment.pressure, 'number', ' hPa');
        }
    }

  } catch (err) {
    console.error('Error processing environment sensor data:', err);
  }

  // Process ToF (Time of Flight) distance sensor data
  try {
    if (data.tof) {
      const tof = data.tof;

      // Update left distance sensor
      const leftDistElement = document.getElementById("sensor_leftDistance");
      if (leftDistElement && tof.left !== undefined) {
        if (tof.left === "N/A") {
          leftDistElement.textContent = "N/A";
        } else {
          const dist = convertDistance(tof.left, systemState.units.distance);
          leftDistElement.textContent = formatSensorValue(dist.value, 'number', ` ${dist.unit}`);
        }
      }

      // Update right distance sensor
      const rightDistElement = document.getElementById("sensor_rightDistance");
      if (rightDistElement && tof.right !== undefined) {
        if (tof.right === "N/A") {
          rightDistElement.textContent = "N/A";
        } else {
          const dist = convertDistance(tof.right, systemState.units.distance);
          rightDistElement.textContent = formatSensorValue(dist.value, 'number', ` ${dist.unit}`);
        }
      }
    }
  } catch (err) {
    console.error('Error processing ToF sensor data:', err);
  } // Update IMU data if available
  if (data.imu) {
    Object.assign(systemState.imu, data.imu);

    const headingElement = document.getElementById("sensor_heading");
    if (headingElement) {
      headingElement.textContent = `${Math.round(systemState.imu.heading)}°`;
    }

    const rollElement = document.getElementById("sensor_roll");
    if (rollElement) {
      rollElement.textContent = `${systemState.imu.roll.toFixed(1)}°`;
    }

    const pitchElement = document.getElementById("sensor_pitch");
    if (pitchElement) {
      pitchElement.textContent = `${systemState.imu.pitch.toFixed(1)}°`;
    }

    // Update safety status if available
    if (data.imu.safety_status) {
      updateSafetyStatus(data.imu.safety_status);
    }
  }

  // Update motor data if available
  if (data.motors) {
    Object.assign(systemState.motors, data.motors);

    const leftSpeedElement = document.getElementById("motor_left");
    if (leftSpeedElement) {
      leftSpeedElement.textContent = `${Math.round(
        systemState.motors.leftSpeed * 100
      )}%`;
    }

    const rightSpeedElement = document.getElementById("motor_right");
    if (rightSpeedElement) {
      rightSpeedElement.textContent = `${Math.round(
        systemState.motors.rightSpeed * 100
      )}%`;
    }

    const bladeSpeedElement = document.getElementById("motor_blade");
    if (bladeSpeedElement) {
      bladeSpeedElement.textContent = `${Math.round(
        systemState.motors.bladeSpeed * 100
      )}%`;
    }
  }
}

function updateSafetyStatus(status) {
  // Update overall safety status
  const overallStatus = document.getElementById("overallSafetyStatus");
  if (overallStatus) {
    if (status.is_safe) {
      overallStatus.innerHTML =
        '<i class="fas fa-check-circle text-success"></i> Safe';
    } else {
      overallStatus.innerHTML =
        '<i class="fas fa-exclamation-triangle text-danger"></i> Warning';
    }
  }

  // Update tilt status
  const tiltStatus = document.getElementById("tiltStatus");
  if (tiltStatus) {
    if (status.tilt_ok) {
      tiltStatus.innerHTML =
        '<i class="fas fa-check-circle text-success"></i> Normal';
    } else {
      tiltStatus.innerHTML =
        '<i class="fas fa-exclamation-triangle text-danger"></i> Excessive Tilt';
    }
  }

  // Update impact status
  const impactStatus = document.getElementById("impactStatus");
  if (impactStatus) {
    if (!status.impact_detected) {
      impactStatus.innerHTML =
        '<i class="fas fa-check-circle text-success"></i> No Impact';
    } else {
      impactStatus.innerHTML =
        '<i class="fas fa-exclamation-triangle text-danger"></i> Impact Detected';
    }
  }

  // Update acceleration status
  const accelStatus = document.getElementById("accelerationStatus");
  if (accelStatus) {
    if (status.acceleration_ok) {
      accelStatus.innerHTML =
        '<i class="fas fa-check-circle text-success"></i> Normal';
    } else {
      accelStatus.innerHTML =
        '<i class="fas fa-exclamation-triangle text-danger"></i> Abnormal';
    }
  }

  // Update last event message
  const lastEvent = document.getElementById("lastSafetyEvent");
  if (lastEvent && status.messages && status.messages.length > 0) {
    lastEvent.textContent = status.messages[status.messages.length - 1];
    // Add timestamp to the message
    const timestamp = new Date().toLocaleTimeString();
    lastEvent.textContent += ` (${timestamp})`;
  }

  // If any safety condition is violated, show alert
  if (!status.is_safe) {
    showSafetyAlert(status.messages);
  }
}

function showSafetyAlert(messages) {
  const alertContainer = document.getElementById("alertContainer");
  if (!alertContainer) return;

  const alertDiv = document.createElement("div");
  alertDiv.className = "alert alert-danger alert-dismissible fade show";
  alertDiv.role = "alert";

  const messageHtml = messages.map((msg) => `<div>${msg}</div>`).join("");
  alertDiv.innerHTML = `
        <strong>Safety Alert!</strong>
        ${messageHtml}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;

  alertContainer.appendChild(alertDiv);

  // Remove alert after 5 seconds
  setTimeout(() => {
    alertDiv.remove();
  }, 5000);
}

/**
 * Update position data and map displays
 *
 * @param {Object} data - Position data from the server
 */
function updatePositionData(data) {
  try {
    // Log the data for debugging
    console.log("Received position update:", data);

    // Update our internal state if data is valid
    if (data && typeof data === 'object') {
      Object.assign(systemState.position, data);
    } else {
      console.warn('Received invalid position data:', data);
      return;
    }

    // Update position display elements
    const latElement = document.getElementById("position_latitude");
    const lngElement = document.getElementById("position_longitude");

    if (latElement && lngElement && data.currentPosition) {
      latElement.textContent = Number(data.currentPosition[0]).toFixed(6);
      lngElement.textContent = Number(data.currentPosition[1]).toFixed(6);
    }

    // Update map if it exists and the updateMap function is available
    if (typeof updateMap === "function" && data.currentPosition) {
      console.log("Updating map with position data");
      updateMap(data);
    } else if (data.currentPosition) {
      console.log("updateMap function not available, but position data received");
    }
  } catch (err) {
    console.error('Error processing position data:', err);
  }
}

/**
 * Handle responses to commands sent to the server
 *
 * @param {Object} data - Response data from the server
 */
function handleCommandResponse(data) {
  console.log("Received command response:", data);
  
  if (data.success) {
    console.log("Command executed successfully:", data.command);
    showAlert(data.message || "Command executed successfully", "success", 3000);
  } else {
    console.error("Command failed:", data.command, data.error || data.message);
    showAlert(data.message || "Command failed", "danger");
  }

  // If the command was a settings update, show success message
  if (data.command === "update_settings" && data.success) {
    showAlert("Settings updated successfully", "success", 3000);
  }

  if (data.command === "save_settings" && data.success) {
    showAlert("Settings saved successfully!", "success");
  }

  // If we need to refresh the page after a command
  if (data.refresh) {
    setTimeout(function () {
      window.location.reload();
    }, 1500);
  }
}

/**
 * Initialize the language selector dropdown
 */
function initializeLanguageSelector() {
  // Get language dropdown elements
  const languageDropdown = document.getElementById("languageDropdown");
  const languageMenu = document.getElementById("languageMenu");
  const currentLanguageText = document.getElementById("currentLanguage");

  if (!languageDropdown || !languageMenu || !currentLanguageText) {
    return; // Elements not found
  }

  // Fetch supported languages from the server
  fetch("/api/languages")
    .then((response) => response.json())
    .then((data) => {
      if (data.success && data.languages) {
        // Clear existing menu items
        languageMenu.innerHTML = "";

        // Add language options to the dropdown
        data.languages.forEach((lang) => {
          const langItem = document.createElement("a");
          langItem.href = `/language/${lang.code}?next=${window.location.pathname}`;
          langItem.className = "dropdown-item";
          langItem.textContent = lang.name;

          // Mark current language as active
          if (lang.code === data.current) {
            langItem.classList.add("active");
            currentLanguageText.textContent = lang.name;
          }

          languageMenu.appendChild(langItem);
        });

        // Toggle dropdown on click
        languageDropdown.addEventListener("click", function (e) {
          e.preventDefault();
          languageMenu.classList.toggle("show");
        });

        // Close dropdown when clicking outside
        document.addEventListener("click", function (e) {
          if (!languageDropdown.contains(e.target)) {
            languageMenu.classList.remove("show");
          }
        });
      }
    })
    .catch((error) => {
      console.error("Error fetching languages:", error);
    });
}

/**
 * Initialize the theme selector dropdown
 */
function initializeThemeSelector() {
  const themeDropdown = document.getElementById("themeDropdown");
  const themeMenu = document.getElementById("themeMenu");
  const currentThemeText = document.getElementById("currentTheme");
  const htmlElement = document.documentElement;

  if (!themeDropdown || !themeMenu || !currentThemeText) {
    return; // Elements not found
  }

  const setTheme = (theme) => {
    htmlElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
    currentThemeText.textContent = theme.charAt(0).toUpperCase() + theme.slice(1);

    // Update active class
    themeMenu.querySelectorAll('.dropdown-item').forEach(item => {
      if (item.dataset.theme === theme) {
        item.classList.add('active');
      } else {
        item.classList.remove('active');
      }
    });
  };

  // Set initial theme
  const savedTheme = localStorage.getItem('theme') || 'light';
  setTheme(savedTheme);

  // Dropdown functionality
  themeDropdown.addEventListener("click", function (e) {
    e.preventDefault();
    themeMenu.classList.toggle("show");
  });

  document.addEventListener("click", function (e) {
    if (!themeDropdown.contains(e.target)) {
      themeMenu.classList.remove("show");
    }
  });

  // Theme selection
  themeMenu.addEventListener('click', (e) => {
    e.preventDefault();
    const theme = e.target.dataset.theme;
    if (theme) {
      setTheme(theme);
      themeMenu.classList.remove('show');
    }
  });
}

/**
 * Display an alert message to the user
 *
 * @param {string} message - The message to display
 * @param {string} type - Alert type: 'success', 'info', 'warning', or 'danger'
 * @param {number} duration - Optional duration in ms before auto-hiding (0 for persistent)
 */
function showAlert(message, type = "info", duration = 0) {
  const alertsContainer = document.getElementById("alertsContainer");
  if (!alertsContainer) return;

  const alertId = "alert_" + Date.now();
  const alertHtml = `
        <div id="${alertId}" class="alert alert-${type} d-flex justify-between align-center">
            <div>${message}</div>
            <button type="button" class="btn-close" onclick="this.parentElement.remove();">
                <i class="fas fa-times"></i>
            </button>
        </div>
    `;

  alertsContainer.insertAdjacentHTML("beforeend", alertHtml);

  // Auto-hide the alert after duration (if not 0)
  if (duration > 0) {
    setTimeout(function () {
      const alertElement = document.getElementById(alertId);
      if (alertElement) {
        alertElement.remove();
      }
    }, duration);
  }
}
