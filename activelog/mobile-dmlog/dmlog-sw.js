// DMLog Mobile Service Worker
// Provides offline functionality and caching

const CACHE_NAME = 'dmlog-mobile-v1.0.0';
const urlsToCache = [
    '/',
    '/index.html',
    '/dmlog-mobile.js',
    '/manifest.json',
    // Add other static assets
];

// Install event - cache resources
self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then((cache) => {
                return cache.addAll(urlsToCache);
            })
    );
    self.skipWaiting();
});

// Fetch event - serve from cache when offline
self.addEventListener('fetch', (event) => {
    event.respondWith(
        caches.match(event.request)
            .then((response) => {
                // Return cached version or fetch from network
                return response || fetch(event.request);
            }
            .catch(() => {
                // If both cache and network fail, return offline page
                if (event.request.destination === 'document') {
                    return caches.match('/index.html');
                }
            })
        )
    );
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames.map((cacheName) => {
                    if (cacheName !== CACHE_NAME) {
                        return caches.delete(cacheName);
                    }
                })
            );
        })
    );
});

// Background sync for when app comes back online
self.addEventListener('sync', (event) => {
    if (event.tag === 'background-sync') {
        event.waitUntil(doBackgroundSync());
    }
});

async function doBackgroundSync() {
    // Sync data with DMLog backend when connection is restored
    try {
        const response = await fetch('/api/mobile-sync', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                type: 'background-sync',
                timestamp: new Date().toISOString()
            })
        });
        
        if (response.ok) {
            console.log('Background sync completed');
        }
    } catch (error) {
        console.log('Background sync failed:', error);
    }
}