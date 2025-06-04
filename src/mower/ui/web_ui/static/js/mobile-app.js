/**
 * Autonomous Mower Web Interface - Mobile App Support
 *
 * Provides functionality for Progressive Web App (PWA) features
 * and mobile-specific optimizations for the autonomous mower control interface.
 */

// Mobile app configuration
const mobileAppConfig = {
    enablePWA: true,
    enableTouchGestures: true,
    enableVibration: true,
    enableFullscreen: true,
    vibrationDuration: 50
};

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    initializeMobileApp();
    setupMobileEventListeners();
    setupInstallPrompt();
});

/**
 * Initialize mobile app features
 */
function initializeMobileApp() {
    // Add mobile-specific class to body for CSS targeting
    if (isMobileDevice()) {
        document.body.classList.add('mobile-device');

        // Add viewport meta tag if not present
        if (!document.querySelector('meta[name="viewport"]')) {
            const viewportMeta = document.createElement('meta');
            viewportMeta.name = 'viewport';
            viewportMeta.content = 'width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no';
            document.head.appendChild(viewportMeta);
        }

        // Add mobile app banner if not already present
        if (!document.getElementById('mobile-app-banner') && mobileAppConfig.enablePWA) {
            createAppInstallBanner();
        }
    }

    // Add manifest link if not present
    if (mobileAppConfig.enablePWA && !document.querySelector('link[rel="manifest"]')) {
        const manifestLink = document.createElement('link');
        manifestLink.rel = 'manifest';
        manifestLink.href = '/static/manifest.json';
        document.head.appendChild(manifestLink);

        // Create manifest.json if it doesn't exist
        createManifestFile();
    }

    // Register service worker for PWA if supported
    if (mobileAppConfig.enablePWA && 'serviceWorker' in navigator) {
        navigator.serviceWorker.register('/static/js/service-worker.js')
            .then(registration => {
                console.log('Service Worker registered with scope:', registration.scope);
            })
            .catch(error => {
                console.error('Service Worker registration failed:', error);
            });
    }
}

/**
 * Set up mobile-specific event listeners
 */
function setupMobileEventListeners() {
    if (!isMobileDevice()) return;

    // Enable touch gestures if configured
    if (mobileAppConfig.enableTouchGestures) {
        setupTouchGestures();
    }

    // Add vibration feedback to buttons
    if (mobileAppConfig.enableVibration && 'vibrate' in navigator) {
        document.querySelectorAll('button, .btn').forEach(button => {
            button.addEventListener('click', () => {
                navigator.vibrate(mobileAppConfig.vibrationDuration);
            });
        });
    }

    // Handle orientation changes
    window.addEventListener('orientationchange', handleOrientationChange);

    // Handle fullscreen mode
    if (mobileAppConfig.enableFullscreen) {
        setupFullscreenMode();
    }

    // Prevent zooming on double tap
    document.addEventListener('dblclick', function(e) {
        e.preventDefault();
    });
}

/**
 * Set up touch gestures for mobile control
 */
function setupTouchGestures() {
    let touchStartX = 0;
    let touchStartY = 0;
    let touchEndX = 0;
    let touchEndY = 0;

    // Track touch start position
    document.addEventListener('touchstart', function(e) {
        touchStartX = e.changedTouches[0].screenX;
        touchStartY = e.changedTouches[0].screenY;
    }, false);

    // Track touch end position and determine gesture
    document.addEventListener('touchend', function(e) {
        touchEndX = e.changedTouches[0].screenX;
        touchEndY = e.changedTouches[0].screenY;
        handleGesture();
    }, false);

    // Handle the gesture
    function handleGesture() {
        const deltaX = touchEndX - touchStartX;
        const deltaY = touchEndY - touchStartY;
        const minSwipeDistance = 50;

        // Determine if it's a horizontal or vertical swipe
        if (Math.abs(deltaX) > Math.abs(deltaY)) {
            // Horizontal swipe
            if (Math.abs(deltaX) > minSwipeDistance) {
                if (deltaX > 0) {
                    // Right swipe - show sidebar
                    document.getElementById('sidebar').classList.add('show');
                } else {
                    // Left swipe - hide sidebar
                    document.getElementById('sidebar').classList.remove('show');
                }
            }
        } else {
            // Vertical swipe - could be used for scrolling or other actions
            if (Math.abs(deltaY) > minSwipeDistance) {
                if (deltaY < 0) {
                    // Swipe up - could trigger an action
                    // For example, show quick controls
                    const quickControls = document.querySelector('.quick-controls');
                    if (quickControls) {
                        quickControls.classList.toggle('show');
                    }
                }
            }
        }
    }

    // Add pull-to-refresh functionality
    let refreshStartY = 0;
    let refreshing = false;

    document.addEventListener('touchstart', function(e) {
        refreshStartY = e.touches[0].clientY;
    });

    document.addEventListener('touchmove', function(e) {
        const y = e.touches[0].clientY;
        const pullDistance = y - refreshStartY;

        // Only activate pull-to-refresh at the top of the page
        if (window.scrollY === 0 && pullDistance > 70 && !refreshing) {
            refreshing = true;

            // Show refresh indicator
            const refreshIndicator = document.createElement('div');
            refreshIndicator.id = 'refresh-indicator';
            refreshIndicator.innerHTML = '<i class="fas fa-sync-alt fa-spin"></i> Refreshing...';
            refreshIndicator.style.cssText = `
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                background-color: var(--grass-medium);
                color: white;
                text-align: center;
                padding: 10px;
                z-index: 9999;
            `;
            document.body.appendChild(refreshIndicator);

            // Refresh data
            if (typeof socket !== 'undefined') {
                socket.emit('request_data', { type: 'all' });
            }

            // Remove indicator after 1 second
            setTimeout(() => {
                if (refreshIndicator.parentNode) {
                    refreshIndicator.parentNode.removeChild(refreshIndicator);
                }
                refreshing = false;
            }, 1000);
        }
    });
}

/**
 * Handle orientation changes
 */
function handleOrientationChange() {
    // Update UI based on orientation
    const orientation = window.orientation;

    if (orientation === 90 || orientation === -90) {
        // Landscape mode
        document.body.classList.add('landscape');
        document.body.classList.remove('portrait');
    } else {
        // Portrait mode
        document.body.classList.add('portrait');
        document.body.classList.remove('landscape');
    }

    // Adjust UI elements based on orientation
    adjustUIForOrientation();
}

/**
 * Adjust UI elements based on current orientation
 */
function adjustUIForOrientation() {
    const isLandscape = document.body.classList.contains('landscape');

    // Adjust control panel layout
    const controlPanel = document.querySelector('.control-panel');
    if (controlPanel) {
        if (isLandscape) {
            controlPanel.classList.add('landscape-layout');
        } else {
            controlPanel.classList.remove('landscape-layout');
        }
    }

    // Adjust map size
    const mapContainer = document.querySelector('.map-container');
    if (mapContainer) {
        if (isLandscape) {
            mapContainer.style.height = '70vh';
        } else {
            mapContainer.style.height = '50vh';
        }
    }
}

/**
 * Set up fullscreen mode for mobile
 */
function setupFullscreenMode() {
    // Add fullscreen toggle button
    const header = document.querySelector('.header');
    if (header) {
        const fullscreenBtn = document.createElement('button');
        fullscreenBtn.className = 'fullscreen-toggle';
        fullscreenBtn.innerHTML = '<i class="fas fa-expand"></i>';
        fullscreenBtn.style.cssText = `
            background: none;
            border: none;
            color: white;
            font-size: 1.2rem;
            cursor: pointer;
            padding: 0.5rem;
        `;

        fullscreenBtn.addEventListener('click', toggleFullscreen);
        header.querySelector('.header-content').appendChild(fullscreenBtn);
    }
}

/**
 * Toggle fullscreen mode
 */
function toggleFullscreen() {
    if (!document.fullscreenElement) {
        document.documentElement.requestFullscreen().catch(err => {
            console.error(`Error attempting to enable fullscreen: ${err.message}`);
        });
    } else {
        if (document.exitFullscreen) {
            document.exitFullscreen();
        }
    }
}

/**
 * Set up PWA install prompt
 */
function setupInstallPrompt() {
    let deferredPrompt;

    window.addEventListener('beforeinstallprompt', (e) => {
        // Prevent Chrome 67 and earlier from automatically showing the prompt
        e.preventDefault();
        // Stash the event so it can be triggered later
        deferredPrompt = e;

        // Show the install button
        showInstallButton(deferredPrompt);
    });

    // Handle app installed event
    window.addEventListener('appinstalled', () => {
        // Hide the install button
        const installButton = document.getElementById('pwa-install-button');
        if (installButton) {
            installButton.style.display = 'none';
        }

        // Log the installation
        console.log('PWA was installed');

        // Show a notification
        if (typeof showNotification === 'function') {
            showNotification('App Installed', 'The Autonomous Mower app has been installed successfully!', 'success');
        }
    });
}

/**
 * Show the PWA install button
 *
 * @param {Event} deferredPrompt - The beforeinstallprompt event
 */
function showInstallButton(deferredPrompt) {
    // Create install button if it doesn't exist
    if (!document.getElementById('pwa-install-button')) {
        const installButton = document.createElement('button');
        installButton.id = 'pwa-install-button';
        installButton.className = 'btn btn-primary';
        installButton.innerHTML = '<i class="fas fa-download"></i> Install App';
        installButton.style.cssText = `
            position: fixed;
            bottom: 20px;
            right: 20px;
            z-index: 9998;
            padding: 10px 15px;
            border-radius: 30px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
        `;

        installButton.addEventListener('click', async () => {
            // Show the install prompt
            deferredPrompt.prompt();
            // Wait for the user to respond to the prompt
            const { outcome } = await deferredPrompt.userChoice;
            // We've used the prompt, and can't use it again, so clear it
            deferredPrompt = null;

            // Hide the button regardless of outcome
            installButton.style.display = 'none';
        });

        document.body.appendChild(installButton);
    }
}

/**
 * Create app install banner
 */
function createAppInstallBanner() {
    // Only show on iOS devices that can't use the install prompt
    if (isIOSDevice() && !isInStandaloneMode()) {
        const banner = document.createElement('div');
        banner.id = 'mobile-app-banner';
        banner.className = 'mobile-app-banner';
        banner.innerHTML = `
            <div class="banner-content">
                <div class="banner-icon">
                    <i class="fas fa-mobile-alt"></i>
                </div>
                <div class="banner-text">
                    <strong>Add to Home Screen</strong>
                    <span>Install this app on your device</span>
                </div>
            </div>
            <button class="banner-close">&times;</button>
        `;

        // Add styles
        const style = document.createElement('style');
        style.textContent = `
            .mobile-app-banner {
                position: fixed;
                bottom: 0;
                left: 0;
                right: 0;
                background-color: white;
                padding: 12px 16px;
                box-shadow: 0 -2px 10px rgba(0, 0, 0, 0.1);
                z-index: 9997;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }

            .banner-content {
                display: flex;
                align-items: center;
            }

            .banner-icon {
                font-size: 24px;
                margin-right: 12px;
                color: var(--grass-medium);
            }

            .banner-text {
                display: flex;
                flex-direction: column;
            }

            .banner-text strong {
                font-size: 16px;
            }

            .banner-text span {
                font-size: 14px;
                color: #666;
            }

            .banner-close {
                background: none;
                border: none;
                font-size: 24px;
                color: #999;
                cursor: pointer;
            }
        `;

        document.head.appendChild(style);
        document.body.appendChild(banner);

        // Add close button functionality
        banner.querySelector('.banner-close').addEventListener('click', () => {
            banner.style.display = 'none';
            // Remember that the user closed the banner
            localStorage.setItem('app_banner_closed', 'true');
        });

        // Don't show if user has closed it before
        if (localStorage.getItem('app_banner_closed') === 'true') {
            banner.style.display = 'none';
        }
    }
}

/**
 * Create manifest.json file for PWA
 */
function createManifestFile() {
    // This function would typically be handled server-side
    // Here we're just logging what would be in the manifest
    console.log('PWA manifest should contain:', {
        "name": "Autonomous Mower",
        "short_name": "Mower",
        "description": "Control your autonomous lawn mower",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#ffffff",
        "theme_color": "#2e5c1e",
        "icons": [
            {
                "src": "/static/images/icon-192.png",
                "sizes": "192x192",
                "type": "image/png"
            },
            {
                "src": "/static/images/icon-512.png",
                "sizes": "512x512",
                "type": "image/png"
            }
        ]
    });
}

/**
 * Check if the current device is a mobile device
 *
 * @returns {boolean} True if the device is mobile
 */
function isMobileDevice() {
    return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent) ||
           (window.innerWidth <= 768);
}

/**
 * Check if the current device is an iOS device
 *
 * @returns {boolean} True if the device is iOS
 */
function isIOSDevice() {
    return /iPad|iPhone|iPod/.test(navigator.userAgent) && !window.MSStream;
}

/**
 * Check if the app is running in standalone mode (installed PWA)
 *
 * @returns {boolean} True if in standalone mode
 */
function isInStandaloneMode() {
    return (window.matchMedia('(display-mode: standalone)').matches) ||
           (window.navigator.standalone) ||
           document.referrer.includes('android-app://');
}

/**
 * Update mobile app settings
 *
 * @param {Object} settings - New mobile app settings
 */
function updateMobileAppSettings(settings) {
    Object.assign(mobileAppConfig, settings);
}

// Make functions available globally
window.updateMobileAppSettings = updateMobileAppSettings;
