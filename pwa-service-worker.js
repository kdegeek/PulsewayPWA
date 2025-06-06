// sw.js - Service Worker for Pulseway PWA
const CACHE_NAME = 'pulseway-dashboard-v1.0.0';
const STATIC_CACHE = 'pulseway-static-v1.0.0';
const API_CACHE = 'pulseway-api-v1.0.0';

// Files to cache for offline functionality
const STATIC_FILES = [
    '/',
    '/index.html',
    '/manifest.json',
    '/icon-192.png',
    '/icon-512.png',
    '/devices.html',
    '/scripts.html',
    '/notifications.html',
    '/settings.html'
];

// API endpoints to cache
const API_ENDPOINTS = [
    '/api/devices/stats',
    '/api/notifications',
    '/api/devices'
];

// Install event - cache static files
self.addEventListener('install', event => {
    console.log('[SW] Installing service worker');
    
    event.waitUntil(
        Promise.all([
            caches.open(STATIC_CACHE).then(cache => {
                console.log('[SW] Caching static files');
                return cache.addAll(STATIC_FILES);
            }),
            caches.open(API_CACHE).then(cache => {
                console.log('[SW] Preparing API cache');
                return Promise.resolve();
            })
        ])
    );
    
    // Force activation of new service worker
    self.skipWaiting();
});

// Activate event - clean up old caches
self.addEventListener('activate', event => {
    console.log('[SW] Activating service worker');
    
    event.waitUntil(
        caches.keys().then(cacheNames => {
            return Promise.all(
                cacheNames.map(cacheName => {
                    if (cacheName !== STATIC_CACHE && cacheName !== API_CACHE) {
                        console.log('[SW] Deleting old cache:', cacheName);
                        return caches.delete(cacheName);
                    }
                })
            );
        })
    );
    
    // Take control of all pages
    self.clients.claim();
});

// Fetch event - serve cached content when offline
self.addEventListener('fetch', event => {
    const { request } = event;
    const url = new URL(request.url);
    
    // Handle API requests
    if (url.pathname.startsWith('/api/')) {
        event.respondWith(handleApiRequest(request));
        return;
    }
    
    // Handle static files
    event.respondWith(handleStaticRequest(request));
});

// Handle API requests with cache-first strategy for GET, network-only for others
async function handleApiRequest(request) {
    const cache = await caches.open(API_CACHE);
    
    // For non-GET requests, always try network first
    if (request.method !== 'GET') {
        try {
            const response = await fetch(request);
            return response;
        } catch (error) {
            // Return error response for failed POST/PUT/DELETE
            return new Response(
                JSON.stringify({ error: 'Network error', offline: true }),
                { 
                    status: 503,
                    headers: { 'Content-Type': 'application/json' }
                }
            );
        }
    }
    
    try {
        // Try network first for fresh data
        const response = await fetch(request);
        
        if (response.ok) {
            // Cache successful responses
            cache.put(request, response.clone());
        }
        
        return response;
    } catch (error) {
        // Network failed, try cache
        console.log('[SW] Network failed, trying cache for:', request.url);
        const cachedResponse = await cache.match(request);
        
        if (cachedResponse) {
            // Add offline indicator to cached API responses
            const data = await cachedResponse.json();
            data._offline = true;
            data._cachedAt = cachedResponse.headers.get('date');
            
            return new Response(JSON.stringify(data), {
                status: 200,
                headers: { 'Content-Type': 'application/json' }
            });
        }
        
        // No cache available
        return new Response(
            JSON.stringify({ 
                error: 'No network connection and no cached data available',
                offline: true 
            }),
            { 
                status: 503,
                headers: { 'Content-Type': 'application/json' }
            }
        );
    }
}

// Handle static files with cache-first strategy
async function handleStaticRequest(request) {
    const cache = await caches.open(STATIC_CACHE);
    
    // Try cache first
    const cachedResponse = await cache.match(request);
    if (cachedResponse) {
        return cachedResponse;
    }
    
    try {
        // Cache miss, try network
        const response = await fetch(request);
        
        if (response.ok) {
            cache.put(request, response.clone());
        }
        
        return response;
    } catch (error) {
        // Network failed and no cache
        console.log('[SW] Failed to fetch:', request.url);
        
        // Return offline page for navigation requests
        if (request.mode === 'navigate') {
            const offlinePage = await cache.match('/index.html');
            return offlinePage || new Response('Offline', { status: 503 });
        }
        
        return new Response('Resource not available', { status: 503 });
    }
}

// Handle push notifications
self.addEventListener('push', event => {
    console.log('[SW] Push received:', event);
    
    let data = {};
    if (event.data) {
        try {
            data = event.data.json();
        } catch (e) {
            data = { title: 'Pulseway Alert', body: event.data.text() };
        }
    }
    
    const options = {
        title: data.title || 'Pulseway Dashboard',
        body: data.body || 'New notification received',
        icon: '/icon-192.png',
        badge: '/icon-192.png',
        tag: data.tag || 'general',
        data: data,
        actions: [
            {
                action: 'view',
                title: 'View Details'
            },
            {
                action: 'dismiss',
                title: 'Dismiss'
            }
        ],
        vibrate: data.priority === 'critical' ? [200, 100, 200] : [100],
        requireInteraction: data.priority === 'critical'
    };
    
    // Add urgency styling based on priority
    if (data.priority === 'critical') {
        options.badge = '/icon-critical.png';
        options.silent = false;
    }
    
    event.waitUntil(
        self.registration.showNotification(options.title, options)
    );
});

// Handle notification clicks
self.addEventListener('notificationclick', event => {
    console.log('[SW] Notification clicked:', event);
    
    event.notification.close();
    
    const action = event.action;
    const data = event.notification.data;
    
    if (action === 'dismiss') {
        return;
    }
    
    // Default action or 'view' action
    const urlToOpen = data.url || '/';
    
    event.waitUntil(
        clients.matchAll({ type: 'window', includeUncontrolled: true })
            .then(clientList => {
                // Check if app is already open
                for (const client of clientList) {
                    if (client.url.includes(urlToOpen) && 'focus' in client) {
                        return client.focus();
                    }
                }
                
                // Open new window
                if (clients.openWindow) {
                    return clients.openWindow(urlToOpen);
                }
            })
    );
});

// Handle notification close
self.addEventListener('notificationclose', event => {
    console.log('[SW] Notification closed:', event);
    
    // Track dismissal analytics if needed
    const data = event.notification.data;
    if (data && data.trackDismissal) {
        // Send analytics
        fetch('/api/analytics/notification-dismissed', {
            method: 'POST',
            body: JSON.stringify({ notificationId: data.id }),
            headers: { 'Content-Type': 'application/json' }
        }).catch(() => {
            // Ignore analytics errors
        });
    }
});

// Background sync for offline actions
self.addEventListener('sync', event => {
    console.log('[SW] Background sync:', event.tag);
    
    if (event.tag === 'device-refresh') {
        event.waitUntil(refreshDeviceData());
    } else if (event.tag === 'script-execution') {
        event.waitUntil(syncPendingScriptExecutions());
    }
});

// Refresh device data in background
async function refreshDeviceData() {
    try {
        const response = await fetch('/api/devices/stats');
        if (response.ok) {
            const cache = await caches.open(API_CACHE);
            cache.put('/api/devices/stats', response.clone());
            
            // Notify all clients of updated data
            const clients = await self.clients.matchAll();
            clients.forEach(client => {
                client.postMessage({
                    type: 'DATA_UPDATED',
                    endpoint: '/api/devices/stats'
                });
            });
        }
    } catch (error) {
        console.log('[SW] Background sync failed:', error);
    }
}

// Sync pending script executions when back online
async function syncPendingScriptExecutions() {
    try {
        // Get pending executions from IndexedDB
        const pendingExecutions = await getPendingExecutions();
        
        for (const execution of pendingExecutions) {
            try {
                const response = await fetch('/api/scripts/execute', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(execution.data)
                });
                
                if (response.ok) {
                    await removePendingExecution(execution.id);
                }
            } catch (error) {
                console.log('[SW] Failed to sync execution:', error);
            }
        }
    } catch (error) {
        console.log('[SW] Background sync failed:', error);
    }
}

// Helper functions for IndexedDB operations
async function getPendingExecutions() {
    // Implementation would use IndexedDB to store pending actions
    return [];
}

async function removePendingExecution(id) {
    // Implementation would remove from IndexedDB
    return Promise.resolve();
}