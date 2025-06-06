// Core application logic

/**
 * Sets up a WebSocket connection and registers handlers for different message types.
 * @param {string[]} subscribeEvents - An array of event types to subscribe to.
 * @param {Object.<string, function>} messageHandlers - An object mapping message types to handler functions.
 *                                                     Example: { 'STATS_UPDATE': handleStatsUpdate, 'DEVICE_UPDATE': handleDeviceUpdate }
 * @param {function} [onOpen] - Optional callback function to execute when the WebSocket connection is opened.
 * @param {function} [onClose] - Optional callback function to execute when the WebSocket connection is closed.
 * @param {function} [onError] - Optional callback function to execute when a WebSocket error occurs.
 */
function setupWebSocket(subscribeEvents, messageHandlers, onOpen, onClose, onError) {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;
    let ws;

    function connect() {
        ws = new WebSocket(wsUrl);

        ws.onopen = function() {
            console.log('WebSocket connected');
            if (subscribeEvents && subscribeEvents.length > 0) {
                ws.send(JSON.stringify({
                    type: 'SUBSCRIBE',
                    events: subscribeEvents
                }));
            }
            if (onOpen && typeof onOpen === 'function') {
                onOpen(ws);
            }
        };

        ws.onmessage = function(event) {
            try {
                const data = JSON.parse(event.data);
                if (data.type && messageHandlers[data.type] && typeof messageHandlers[data.type] === 'function') {
                    messageHandlers[data.type](data);
                } else {
                    console.log('Received unhandled WebSocket message type or no handler:', data.type, data);
                }
            } catch (e) {
                console.error('Error parsing WebSocket message or in handler:', e, event.data);
            }
        };

        ws.onclose = function() {
            console.log('WebSocket disconnected, attempting to reconnect in 5 seconds...');
            if (onClose && typeof onClose === 'function') {
                onClose();
            }
            setTimeout(connect, 5000); // Attempt to reconnect after 5 seconds
        };

        ws.onerror = function(error) {
            console.error('WebSocket error:', error);
            if (onError && typeof onError === 'function') {
                onError(error);
            }
            // Note: onclose will usually be called after onerror, so reconnection is handled there.
        };
    }

    connect(); // Initial connection attempt
}

// PWA Service Worker Registration (from index.html, good candidate for app.js)
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => { // Ensure page is loaded before registering SW
        navigator.serviceWorker.register('/pwa-service-worker.js')
            .then(registration => {
                console.log('PWA Service Worker registered successfully:', registration);
            })
            .catch(error => {
                console.error('PWA Service Worker registration failed:', error);
            });
    });
}

// Online/Offline status handling (from index.html)
// This could be exposed via an event system or callbacks if other parts of the app need to react.
// For now, it directly manipulates a banner if it exists.
function handleOnlineStatus() {
    const offlineBanner = document.getElementById('offlineBanner'); // Assumes an element with this ID exists
    if (offlineBanner) {
        if (navigator.onLine) {
            offlineBanner.classList.remove('show');
            console.log('Application is online.');
        } else {
            offlineBanner.classList.add('show');
            console.log('Application is offline.');
        }
    }
}

window.addEventListener('online', handleOnlineStatus);
window.addEventListener('offline', handleOnlineStatus);
// Initial check
if (document.readyState === 'complete' || document.readyState === 'interactive') {
    handleOnlineStatus();
} else {
    window.addEventListener('DOMContentLoaded', handleOnlineStatus);
}
