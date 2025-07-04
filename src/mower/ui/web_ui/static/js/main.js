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
};

// Initialize when DOM is ready
document.addEventListener("DOMContentLoaded", function () {
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

  // Initialize socket connection using HTTP polling transport to avoid WebSocket frame errors
  socket = io({ transports: ['polling'] });

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

  // Handle errors
  socket.on("connect_error", function (error) {
    isConnected = false;
    updateConnectionStatus(false);
    console.error("Connection error:", error);
    showAlert("Connection error: " + error.message, "danger");

    attemptReconnect();
  });

  // Handle system status updates
  socket.on("status_update", function (data) {
    updateSystemStatus(data);
  });

  // Handle sensor data updates
  socket.on("sensor_data", function (data) {
    console.log("Received sensor data:", data);
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
    showAlert("Cannot send command: Not connected to the server", "danger");
    return;
  }

  showAlert(`Sending command: ${command}`, "info", 2000);

  socket.emit("control_command", {
    command: command,
    params: params,
  });
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
    const batteryVoltageElem = document.getElementById("batteryVoltage");
    const chargingStatusElem = document.getElementById("chargingStatus");
    const pct = Math.round(systemState.battery.percentage || 0);
    if (batteryDisplay) batteryDisplay.textContent = `${pct}%`;
    if (batteryVoltageElem && systemState.battery.voltage != null) batteryVoltageElem.textContent = `${systemState.battery.voltage.toFixed(1)} V`;
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
    if (mowerStateElem) {
      mowerStateElem.textContent = formatRobotState(data.state);
      if (data.state === "ERROR" || data.state === "EMERGENCY_STOP") mowerStateElem.className = "text-danger";
      else if (data.state === "MOWING" || data.state === "AVOIDING") mowerStateElem.className = "text-success";
      else mowerStateElem.className = "";
    }
  }

  // Update GPS status display
  if (data.gps !== undefined) {
    Object.assign(systemState.gps, data.gps);
    const gpsStatusElem = document.getElementById("gpsStatusDisplay");
    const satCountElem = document.getElementById("satelliteCount");
    if (gpsStatusElem) {
      if (systemState.gps.fix) {
        gpsStatusElem.textContent = `${systemState.gps.satellites} satellites`;
        gpsStatusElem.className = systemState.gps.satellites >= 4 ? "text-success" : "text-warning";
      } else {
        gpsStatusElem.textContent = "No fix";
        gpsStatusElem.className = "text-danger";
      }
    }
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
    // Update battery from sensor data
    if (data.power) {
      const power = data.power;
      systemState.battery.voltage = power.voltage;
      systemState.battery.percentage = power.percentage || 0;
      systemState.battery.charging = power.charging || false;
      // Update battery UI (sidebar and dashboard)
      const dashPct = Math.round(systemState.battery.percentage);
      const bd = document.getElementById("batteryDisplay");
      const bsv = document.getElementById("batteryStatus");
      const bv = document.getElementById("batteryVoltage");
      const ch = document.getElementById("chargingStatus");
      if (bd) bd.textContent = `${dashPct}%`;
      if (bsv) bsv.textContent = `${dashPct}%`;
      if (bv && systemState.battery.voltage != null) bv.textContent = `${systemState.battery.voltage.toFixed(1)} V`;
      if (ch) ch.innerHTML = systemState.battery.charging ? '<i class="fas fa-bolt"></i>' : '';
    }
    // Update GPS from sensor data
    if (data.gps) {
      const gps = data.gps;
      systemState.gps.latitude = gps.latitude;
      systemState.gps.longitude = gps.longitude;
      systemState.gps.satellites = gps.satellites;
      // Determine fix status
      systemState.gps.fix = gps.status && gps.status.toLowerCase() !== 'simulated';
      // Update GPS UI (sidebar and dashboard)
      const dashGps = document.getElementById("gpsStatusDisplay");
      const sideGps = document.getElementById("gpsStatus");
      const sc = document.getElementById("satelliteCount");
      const statusText = systemState.gps.fix ? `${systemState.gps.satellites} satellites` : 'No fix';
      if (dashGps) dashGps.textContent = statusText;
      if (sideGps) sideGps.textContent = statusText;
      if (sc) sc.textContent = `${systemState.gps.satellites} satellites`;
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
      const tempElement = document.getElementById("sensor_temperature");
      if (tempElement) {
        tempElement.textContent = `${Number(data.environment.temperature).toFixed(1)}°C`;
      }
    }
    
    // Update humidity from environment sensor data
    if (data.environment && data.environment.humidity !== undefined) {
        const humidityElement = document.getElementById("sensor_humidity");
        if (humidityElement) {
            humidityElement.textContent = `${Number(data.environment.humidity).toFixed(1)}%`;
        }
    }

    // Update pressure from environment sensor data
    if (data.environment && data.environment.pressure !== undefined) {
        const pressureElement = document.getElementById("sensor_pressure");
        if (pressureElement) {
            pressureElement.textContent = `${Number(data.environment.pressure).toFixed(1)} hPa`;
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
        leftDistElement.textContent = `${Number(tof.left).toFixed(1)} cm`;
      }

      // Update right distance sensor
      const rightDistElement = document.getElementById("sensor_rightDistance");
      if (rightDistElement && tof.right !== undefined) {
        rightDistElement.textContent = `${Number(tof.right).toFixed(1)} cm`;
      }

      // Update front distance sensor if available
      const frontDistElement = document.getElementById("sensor_frontDistance");
      if (frontDistElement && tof.front !== undefined) {
        frontDistElement.textContent = `${Number(tof.front).toFixed(1)} cm`;
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
  if (data.success) {
    showAlert(data.message || "Command executed successfully", "success", 3000);
  } else {
    showAlert(data.message || "Command failed", "danger");
  }

  // If the command was a settings update, show success message
  if (data.command === "update_settings" && data.success) {
    showAlert("Settings updated successfully", "success", 3000);
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
