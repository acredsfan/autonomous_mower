/**
 * Autonomous Mower - Helper Functions
 *
 * This file contains helper functions for improved error handling,
 * user feedback, and contextual help throughout the application.
 */

// Enhanced alert system with different types and auto-dismissal
window.AlertSystem = window.AlertSystem || {
    // Alert container ID
    containerId: 'alertsContainer',

    // Default duration for alerts in milliseconds
    defaultDuration: 5000,

    // Show an alert message
    show: function(message, type = 'info', duration = this.defaultDuration) {
        const container = document.getElementById(this.containerId);
        if (!container) {
            console.error('Alert container not found. Create a div with id "alertsContainer".');
            return;
        }

        // Create alert ID
        const alertId = 'alert_' + Date.now();

        // Create alert element
        const alertElement = document.createElement('div');
        alertElement.id = alertId;
        alertElement.className = `alert alert-${type} d-flex justify-between align-center`;

        // Add icon based on type
        let icon = 'info-circle';
        if (type === 'success') icon = 'check-circle';
        if (type === 'warning') icon = 'exclamation-triangle';
        if (type === 'danger') icon = 'exclamation-circle';

        // Set alert content
        alertElement.innerHTML = `
            <div class="alert-icon"><i class="fas fa-${icon}"></i></div>
            <div class="alert-message">${message}</div>
            <button type="button" class="btn-close" onclick="this.parentElement.remove();">
                <i class="fas fa-times"></i>
            </button>
        `;

        // Add to container
        container.appendChild(alertElement);

        // Add animation class
        setTimeout(() => {
            alertElement.classList.add('show');
        }, 10);

        // Auto-dismiss if duration is set
        if (duration > 0) {
            setTimeout(() => {
                this.dismiss(alertId);
            }, duration);
        }

        return alertId;
    },

    // Show a success alert
    success: function(message, duration = this.defaultDuration) {
        return this.show(message, 'success', duration);
    },

    // Show an info alert
    info: function(message, duration = this.defaultDuration) {
        return this.show(message, 'info', duration);
    },

    // Show a warning alert
    warning: function(message, duration = this.defaultDuration) {
        return this.show(message, 'warning', duration);
    },

    // Show an error alert
    error: function(message, duration = this.defaultDuration) {
        return this.show(message, 'danger', duration);
    },

    // Dismiss an alert by ID
    dismiss: function(alertId) {
        const alertElement = document.getElementById(alertId);
        if (alertElement) {
            alertElement.classList.remove('show');
            setTimeout(() => {
                if (alertElement.parentNode) {
                    alertElement.parentNode.removeChild(alertElement);
                }
            }, 300);
        }
    },

    // Dismiss all alerts
    dismissAll: function() {
        const container = document.getElementById(this.containerId);
        if (container) {
            const alerts = container.querySelectorAll('.alert');
            alerts.forEach(alert => {
                this.dismiss(alert.id);
            });
        }
    }
};

// Enhanced form validation
const FormValidator = {
    // Validate a form
    validate: function(formId) {
        const form = document.getElementById(formId);
        if (!form) {
            console.error(`Form with ID "${formId}" not found.`);
            return false;
        }

        let isValid = true;
        const errorMessages = [];

        // Get all form elements
        const elements = form.elements;

        // Check each element
        for (let i = 0; i < elements.length; i++) {
            const element = elements[i];

            // Skip buttons, hidden fields, etc.
            if (element.type === 'submit' || element.type === 'button' || element.type === 'hidden') {
                continue;
            }

            // Check required fields
            if (element.hasAttribute('required') && !element.value.trim()) {
                isValid = false;
                this.markInvalid(element, 'This field is required');
                errorMessages.push(`${element.name || 'Field'} is required`);
                continue;
            }

            // Check min/max for number inputs
            if (element.type === 'number') {
                const value = parseFloat(element.value);
                if (!isNaN(value)) {
                    if (element.hasAttribute('min') && value < parseFloat(element.getAttribute('min'))) {
                        isValid = false;
                        this.markInvalid(element, `Minimum value is ${element.getAttribute('min')}`);
                        errorMessages.push(`${element.name || 'Field'} must be at least ${element.getAttribute('min')}`);
                    }

                    if (element.hasAttribute('max') && value > parseFloat(element.getAttribute('max'))) {
                        isValid = false;
                        this.markInvalid(element, `Maximum value is ${element.getAttribute('max')}`);
                        errorMessages.push(`${element.name || 'Field'} must be at most ${element.getAttribute('max')}`);
                    }
                }
            }

            // Check pattern for text inputs
            if ((element.type === 'text' || element.type === 'email' || element.type === 'tel') &&
                element.hasAttribute('pattern') && element.value.trim()) {
                const pattern = new RegExp(element.getAttribute('pattern'));
                if (!pattern.test(element.value)) {
                    isValid = false;
                    this.markInvalid(element, element.getAttribute('data-error-message') || 'Invalid format');
                    errorMessages.push(`${element.name || 'Field'} has an invalid format`);
                }
            }

            // Check email format
            if (element.type === 'email' && element.value.trim()) {
                const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
                if (!emailPattern.test(element.value)) {
                    isValid = false;
                    this.markInvalid(element, 'Invalid email address');
                    errorMessages.push('Invalid email address');
                }
            }

            // If valid, mark as valid
            if (element.classList.contains('is-invalid')) {
                this.markValid(element);
            }
        }

        // Show error message if form is invalid
        if (!isValid && errorMessages.length > 0) {
            AlertSystem.error('Please correct the following errors: ' + errorMessages.join(', '));
        }

        return isValid;
    },

    // Mark a field as invalid
    markInvalid: function(element, message) {
        element.classList.add('is-invalid');
        element.classList.remove('is-valid');

        // Add error message
        let feedbackElement = element.nextElementSibling;
        if (!feedbackElement || !feedbackElement.classList.contains('invalid-feedback')) {
            feedbackElement = document.createElement('div');
            feedbackElement.className = 'invalid-feedback';
            element.parentNode.insertBefore(feedbackElement, element.nextSibling);
        }

        feedbackElement.textContent = message;
    },

    // Mark a field as valid
    markValid: function(element) {
        element.classList.remove('is-invalid');
        element.classList.add('is-valid');

        // Remove error message
        const feedbackElement = element.nextElementSibling;
        if (feedbackElement && feedbackElement.classList.contains('invalid-feedback')) {
            feedbackElement.remove();
        }
    },

    // Reset form validation
    reset: function(formId) {
        const form = document.getElementById(formId);
        if (!form) {
            console.error(`Form with ID "${formId}" not found.`);
            return;
        }

        // Reset all form elements
        const elements = form.elements;
        for (let i = 0; i < elements.length; i++) {
            const element = elements[i];
            element.classList.remove('is-invalid', 'is-valid');

            // Remove error messages
            const feedbackElement = element.nextElementSibling;
            if (feedbackElement && feedbackElement.classList.contains('invalid-feedback')) {
                feedbackElement.remove();
            }
        }
    }
};

// Contextual help system
const ContextualHelp = {
    // Show a tooltip with help text
    showTooltip: function(element, message) {
        // Create tooltip if it doesn't exist
        let tooltip = document.getElementById('contextual-tooltip');
        if (!tooltip) {
            tooltip = document.createElement('div');
            tooltip.id = 'contextual-tooltip';
            tooltip.className = 'contextual-tooltip';
            document.body.appendChild(tooltip);

            // Add styles if not in CSS
            if (!document.getElementById('contextual-tooltip-styles')) {
                const style = document.createElement('style');
                style.id = 'contextual-tooltip-styles';
                style.textContent = `
                    .contextual-tooltip {
                        position: absolute;
                        background-color: #333;
                        color: white;
                        padding: 8px 12px;
                        border-radius: 4px;
                        font-size: 14px;
                        max-width: 250px;
                        z-index: 9999;
                        opacity: 0;
                        transition: opacity 0.3s;
                        pointer-events: none;
                    }

                    .contextual-tooltip::after {
                        content: '';
                        position: absolute;
                        top: 100%;
                        left: 50%;
                        margin-left: -5px;
                        border-width: 5px;
                        border-style: solid;
                        border-color: #333 transparent transparent transparent;
                    }

                    .contextual-tooltip.show {
                        opacity: 1;
                    }

                    .help-icon {
                        display: inline-block;
                        width: 16px;
                        height: 16px;
                        background-color: #6c757d;
                        color: white;
                        border-radius: 50%;
                        text-align: center;
                        line-height: 16px;
                        font-size: 12px;
                        cursor: help;
                        margin-left: 5px;
                    }
                `;
                document.head.appendChild(style);
            }
        }

        // Position tooltip above the element
        const rect = element.getBoundingClientRect();
        tooltip.style.left = (rect.left + rect.width / 2 - 125) + 'px'; // Center tooltip
        tooltip.style.top = (rect.top - 40) + 'px'; // Position above element

        // Set message and show tooltip
        tooltip.textContent = message;
        tooltip.classList.add('show');

        // Hide tooltip after 3 seconds
        setTimeout(() => {
            tooltip.classList.remove('show');
        }, 3000);
    },

    // Add help icons to elements with data-help attribute
    init: function() {
        document.querySelectorAll('[data-help]').forEach(element => {
            // Create help icon if it doesn't exist
            if (!element.nextElementSibling || !element.nextElementSibling.classList.contains('help-icon')) {
                const helpIcon = document.createElement('span');
                helpIcon.className = 'help-icon';
                helpIcon.innerHTML = '?';
                helpIcon.title = 'Click for help';

                // Add click handler
                helpIcon.addEventListener('click', function(e) {
                    e.preventDefault();
                    ContextualHelp.showTooltip(this, element.getAttribute('data-help'));
                });

                // Add after element
                element.parentNode.insertBefore(helpIcon, element.nextSibling);
            }
        });
    }
};

// Enhanced error handling for API calls
const ApiHandler = {
    // Send a command to the server with improved error handling
    sendCommand: function(command, params = {}, callback = null) {
        // Show loading indicator
        const loadingId = AlertSystem.info('Processing request...', 0);

        // Send command
        fetch('/api/' + command, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(params)
        })
        .then(response => {
            // Check if response is OK
            if (!response.ok) {
                throw new Error(`Server returned ${response.status}: ${response.statusText}`);
            }
            return response.json();
        })
        .then(data => {
            // Hide loading indicator
            AlertSystem.dismiss(loadingId);

            // Handle success
            if (data.success) {
                if (data.message) {
                    AlertSystem.success(data.message);
                }

                // Call callback if provided
                if (callback) {
                    callback(data);
                }
            } else {
                // Handle error
                const errorMessage = data.error || 'Unknown error occurred';
                AlertSystem.error(errorMessage);

                // Call callback with error
                if (callback) {
                    callback(data);
                }
            }
        })
        .catch(error => {
            // Hide loading indicator
            AlertSystem.dismiss(loadingId);

            // Handle network or parsing error
            AlertSystem.error('Error: ' + error.message);

            // Call callback with error
            if (callback) {
                callback({success: false, error: error.message});
            }
        });
    },

    // Get data from the server with improved error handling
    getData: function(endpoint, callback = null) {
        // Show loading indicator
        const loadingId = AlertSystem.info('Loading data...', 0);

        // Send request
        fetch('/api/' + endpoint)
        .then(response => {
            // Check if response is OK
            if (!response.ok) {
                throw new Error(`Server returned ${response.status}: ${response.statusText}`);
            }
            return response.json();
        })
        .then(data => {
            // Hide loading indicator
            AlertSystem.dismiss(loadingId);

            // Handle success
            if (data.success) {
                // Call callback if provided
                if (callback) {
                    callback(data);
                }
            } else {
                // Handle error
                const errorMessage = data.error || 'Unknown error occurred';
                AlertSystem.error(errorMessage);

                // Call callback with error
                if (callback) {
                    callback(data);
                }
            }
        })
        .catch(error => {
            // Hide loading indicator
            AlertSystem.dismiss(loadingId);

            // Handle network or parsing error
            AlertSystem.error('Error: ' + error.message);

            // Call callback with error
            if (callback) {
                callback({success: false, error: error.message});
            }
        });
    }
};

// Initialize helper systems when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Initialize contextual help
    ContextualHelp.init();

    // Add styles for alerts if not already in CSS
    if (!document.getElementById('alert-system-styles')) {
        const style = document.createElement('style');
        style.id = 'alert-system-styles';
        style.textContent = `
            #alertsContainer {
                position: fixed;
                top: 20px;
                right: 20px;
                z-index: 9999;
                max-width: 350px;
            }

            .alert {
                margin-bottom: 10px;
                padding: 15px;
                border-radius: 4px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                opacity: 0;
                transform: translateX(50px);
                transition: opacity 0.3s, transform 0.3s;
            }

            .alert.show {
                opacity: 1;
                transform: translateX(0);
            }

            .alert-icon {
                margin-right: 10px;
            }

            .alert-message {
                flex: 1;
            }

            .btn-close {
                background: none;
                border: none;
                color: inherit;
                font-size: 16px;
                cursor: pointer;
                opacity: 0.7;
            }

            .btn-close:hover {
                opacity: 1;
            }

            .is-invalid {
                border-color: var(--accent-red) !important;
            }

            .is-valid {
                border-color: var(--accent-green) !important;
            }

            .invalid-feedback {
                color: var(--accent-red);
                font-size: 0.875rem;
                margin-top: 0.25rem;
            }
        `;
        document.head.appendChild(style);
    }

    // Create alerts container if it doesn't exist
    if (!document.getElementById('alertsContainer')) {
        const alertsContainer = document.createElement('div');
        alertsContainer.id = 'alertsContainer';
        document.body.appendChild(alertsContainer);
    }
});

// Replace the global showAlert function with the enhanced version
window.showAlert = function(message, type = 'info', duration = 5000) {
    return AlertSystem.show(message, type, duration);
};

// Replace the global sendCommand function with the enhanced version
window.sendCommand = function(command, params = {}, callback = null) {
    return ApiHandler.sendCommand(command, params, callback);
};
