/**
 * Autonomous Mower Web Interface - Notifications System
 * 
 * Provides enhanced real-time notifications and status updates
 * for the autonomous mower control interface.
 */

// Notification system configuration
const notificationConfig = {
    enableSound: true,
    enableDesktopNotifications: true,
    notificationDuration: 5000,
    maxNotifications: 5,
    soundVolume: 0.5
};

// Notification queue
let notificationQueue = [];
let activeNotifications = 0;

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    initializeNotifications();
    setupNotificationListeners();
});

/**
 * Initialize the notification system
 */
function initializeNotifications() {
    // Create notification container if it doesn't exist
    if (!document.getElementById('notification-center')) {
        const notificationCenter = document.createElement('div');
        notificationCenter.id = 'notification-center';
        notificationCenter.className = 'notification-center';
        document.body.appendChild(notificationCenter);
        
        // Add styles if not already in CSS
        if (!document.getElementById('notification-styles')) {
            const style = document.createElement('style');
            style.id = 'notification-styles';
            style.textContent = `
                .notification-center {
                    position: fixed;
                    top: 20px;
                    right: 20px;
                    z-index: 9999;
                    display: flex;
                    flex-direction: column;
                    align-items: flex-end;
                    max-width: 350px;
                }
                
                .notification {
                    background-color: white;
                    border-radius: 4px;
                    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
                    margin-bottom: 10px;
                    padding: 15px;
                    width: 100%;
                    display: flex;
                    align-items: flex-start;
                    transform: translateX(120%);
                    transition: transform 0.3s ease;
                    overflow: hidden;
                }
                
                .notification.show {
                    transform: translateX(0);
                }
                
                .notification-icon {
                    margin-right: 12px;
                    font-size: 20px;
                }
                
                .notification-content {
                    flex: 1;
                }
                
                .notification-title {
                    font-weight: bold;
                    margin-bottom: 5px;
                }
                
                .notification-message {
                    font-size: 14px;
                }
                
                .notification-close {
                    background: none;
                    border: none;
                    color: #999;
                    cursor: pointer;
                    font-size: 16px;
                    padding: 0;
                    margin-left: 10px;
                }
                
                .notification-progress {
                    position: absolute;
                    bottom: 0;
                    left: 0;
                    height: 3px;
                    background-color: rgba(0, 0, 0, 0.1);
                    width: 100%;
                }
                
                .notification-progress-bar {
                    height: 100%;
                    width: 100%;
                    background-color: var(--grass-medium);
                    transition: width linear;
                }
                
                .notification-info .notification-icon {
                    color: var(--accent-blue);
                }
                
                .notification-success .notification-icon {
                    color: var(--accent-green);
                }
                
                .notification-warning .notification-icon {
                    color: var(--accent-yellow);
                }
                
                .notification-danger .notification-icon {
                    color: var(--accent-red);
                }
                
                @media (max-width: 576px) {
                    .notification-center {
                        left: 10px;
                        right: 10px;
                        max-width: none;
                    }
                }
            `;
            document.head.appendChild(style);
        }
    }
    
    // Request permission for desktop notifications
    if (notificationConfig.enableDesktopNotifications && 'Notification' in window) {
        if (Notification.permission !== 'granted' && Notification.permission !== 'denied') {
            Notification.requestPermission();
        }
    }
    
    // Create audio elements for notification sounds
    if (notificationConfig.enableSound) {
        const sounds = {
            info: 'data:audio/mp3;base64,SUQzBAAAAAAAI1RTU0UAAAAPAAADTGF2ZjU4Ljc2LjEwMAAAAAAAAAAAAAAA//tQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAASW5mbwAAAA8AAAASAAAeMwAUFBQUFCgUFBQUFDMzMzMzM0dHR0dHR1tbW1tbW2ZmZmZmZnp6enp6eoODg4ODg5eXl5eXl6ysrKysrMHBwcHBwdXV1dXV1erq6urq6v////8AAAAATGF2YzU4LjEzAAAAAAAAAAAAAAAAJAX/LAAAAAAAAAAA',
            success: 'data:audio/mp3;base64,SUQzBAAAAAAAI1RTU0UAAAAPAAADTGF2ZjU4Ljc2LjEwMAAAAAAAAAAAAAAA//tQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAASW5mbwAAAA8AAAASAAAeMwAUFBQUFCgUFBQUFDMzMzMzM0dHR0dHR1tbW1tbW2ZmZmZmZnp6enp6eoODg4ODg5eXl5eXl6ysrKysrMHBwcHBwdXV1dXV1erq6urq6v////8AAAAATGF2YzU4LjEzAAAAAAAAAAAAAAAAJAX/LAAAAAAAAAAA',
            warning: 'data:audio/mp3;base64,SUQzBAAAAAAAI1RTU0UAAAAPAAADTGF2ZjU4Ljc2LjEwMAAAAAAAAAAAAAAA//tQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAASW5mbwAAAA8AAAASAAAeMwAUFBQUFCgUFBQUFDMzMzMzM0dHR0dHR1tbW1tbW2ZmZmZmZnp6enp6eoODg4ODg5eXl5eXl6ysrKysrMHBwcHBwdXV1dXV1erq6urq6v////8AAAAATGF2YzU4LjEzAAAAAAAAAAAAAAAAJAX/LAAAAAAAAAAA',
            danger: 'data:audio/mp3;base64,SUQzBAAAAAAAI1RTU0UAAAAPAAADTGF2ZjU4Ljc2LjEwMAAAAAAAAAAAAAAA//tQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAASW5mbwAAAA8AAAASAAAeMwAUFBQUFCgUFBQUFDMzMzMzM0dHR0dHR1tbW1tbW2ZmZmZmZnp6enp6eoODg4ODg5eXl5eXl6ysrKysrMHBwcHBwdXV1dXV1erq6urq6v////8AAAAATGF2YzU4LjEzAAAAAAAAAAAAAAAAJAX/LAAAAAAAAAAA'
        };
        
        for (const [type, src] of Object.entries(sounds)) {
            if (!document.getElementById(`notification-sound-${type}`)) {
                const audio = document.createElement('audio');
                audio.id = `notification-sound-${type}`;
                audio.src = src;
                audio.volume = notificationConfig.soundVolume;
                document.body.appendChild(audio);
            }
        }
    }
}

/**
 * Set up event listeners for notifications
 */
function setupNotificationListeners() {
    // Listen for socket.io events if available
    if (typeof socket !== 'undefined') {
        // System status updates
        socket.on('status_update', function(data) {
            if (data.state === 'ERROR' || data.state === 'EMERGENCY_STOP') {
                showNotification('System Alert', data.errorMessage || 'System entered error state', 'danger');
            } else if (data.state === 'MOWING') {
                showNotification('Status Update', 'Mower has started mowing', 'info');
            } else if (data.state === 'RETURNING_HOME') {
                showNotification('Status Update', 'Mower is returning to home position', 'info');
            } else if (data.state === 'DOCKED') {
                showNotification('Status Update', 'Mower has docked successfully', 'success');
            }
            
            // Battery alerts
            if (data.battery && data.battery.percentage < 20 && !data.battery.charging) {
                showNotification('Low Battery', `Battery level is ${Math.round(data.battery.percentage)}%`, 'warning');
            }
        });
        
        // Safety alerts
        socket.on('safety_alert', function(data) {
            showNotification('Safety Alert', data.message, 'danger');
        });
        
        // Maintenance reminders
        socket.on('maintenance_reminder', function(data) {
            showNotification('Maintenance Reminder', data.message, 'warning');
        });
        
        // Weather alerts
        socket.on('weather_alert', function(data) {
            showNotification('Weather Alert', data.message, 'warning');
        });
    }
}

/**
 * Show a notification
 * 
 * @param {string} title - The notification title
 * @param {string} message - The notification message
 * @param {string} type - Notification type: 'info', 'success', 'warning', or 'danger'
 * @param {number} duration - Duration in ms before auto-hiding (0 for persistent)
 */
function showNotification(title, message, type = 'info', duration = notificationConfig.notificationDuration) {
    // Add to queue if too many active notifications
    if (activeNotifications >= notificationConfig.maxNotifications) {
        notificationQueue.push({ title, message, type, duration });
        return;
    }
    
    activeNotifications++;
    
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    
    // Set icon based on type
    let icon = 'info-circle';
    if (type === 'success') icon = 'check-circle';
    if (type === 'warning') icon = 'exclamation-triangle';
    if (type === 'danger') icon = 'exclamation-circle';
    
    notification.innerHTML = `
        <div class="notification-icon">
            <i class="fas fa-${icon}"></i>
        </div>
        <div class="notification-content">
            <div class="notification-title">${title}</div>
            <div class="notification-message">${message}</div>
        </div>
        <button class="notification-close">
            <i class="fas fa-times"></i>
        </button>
        <div class="notification-progress">
            <div class="notification-progress-bar"></div>
        </div>
    `;
    
    // Add to notification center
    const notificationCenter = document.getElementById('notification-center');
    notificationCenter.appendChild(notification);
    
    // Show notification with animation
    setTimeout(() => {
        notification.classList.add('show');
    }, 10);
    
    // Play sound if enabled
    if (notificationConfig.enableSound) {
        const audio = document.getElementById(`notification-sound-${type}`);
        if (audio) {
            audio.currentTime = 0;
            audio.play().catch(e => console.log('Error playing notification sound:', e));
        }
    }
    
    // Show desktop notification if enabled and permission granted
    if (notificationConfig.enableDesktopNotifications && 
        'Notification' in window && 
        Notification.permission === 'granted') {
        const desktopNotification = new Notification('Autonomous Mower', {
            body: `${title}: ${message}`,
            icon: '/static/images/logo.png'
        });
        
        // Close desktop notification after 5 seconds
        setTimeout(() => {
            desktopNotification.close();
        }, 5000);
    }
    
    // Set up progress bar animation if duration > 0
    if (duration > 0) {
        const progressBar = notification.querySelector('.notification-progress-bar');
        progressBar.style.transition = `width ${duration}ms linear`;
        
        // Start progress bar animation
        setTimeout(() => {
            progressBar.style.width = '0%';
        }, 10);
        
        // Remove notification after duration
        setTimeout(() => {
            removeNotification(notification);
        }, duration);
    }
    
    // Set up close button
    const closeButton = notification.querySelector('.notification-close');
    closeButton.addEventListener('click', function() {
        removeNotification(notification);
    });
}

/**
 * Remove a notification and process queue
 * 
 * @param {HTMLElement} notification - The notification element to remove
 */
function removeNotification(notification) {
    notification.classList.remove('show');
    
    // Remove after animation completes
    setTimeout(() => {
        if (notification.parentNode) {
            notification.parentNode.removeChild(notification);
        }
        
        activeNotifications--;
        
        // Process next notification in queue if any
        if (notificationQueue.length > 0) {
            const next = notificationQueue.shift();
            showNotification(next.title, next.message, next.type, next.duration);
        }
    }, 300);
}

/**
 * Update notification settings
 * 
 * @param {Object} settings - New notification settings
 */
function updateNotificationSettings(settings) {
    Object.assign(notificationConfig, settings);
    
    // Update sound volume if changed
    if (settings.soundVolume !== undefined) {
        document.querySelectorAll('audio[id^="notification-sound-"]').forEach(audio => {
            audio.volume = settings.soundVolume;
        });
    }
}

// Make functions available globally
window.showNotification = showNotification;
window.updateNotificationSettings = updateNotificationSettings;