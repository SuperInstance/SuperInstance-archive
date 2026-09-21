/**
 * Advanced Service Worker for ActiveLog Optimization
 * Handles caching, offline functionality, background sync, and push notifications
 */

const CACHE_NAME = 'activelog-v1.2.0';
const CACHE_VERSION = '1.2.0';
const STATIC_CACHE = `${CACHE_NAME}-static`;
const DYNAMIC_CACHE = `${CACHE_NAME}-dynamic`;
const API_CACHE = `${CACHE_NAME}-api`;
const IMAGE_CACHE = `${CACHE_NAME}-images`;

// Cache configuration
const CACHE_CONFIG = {
  maxEntries: {
    static: 100,
    dynamic: 50,
    api: 200,
    images: 500
  },
  maxAge: {
    static: 365 * 24 * 60 * 60, // 1 year
    dynamic: 30 * 24 * 60 * 60, // 30 days
    api: 5 * 60, // 5 minutes
    images: 30 * 24 * 60 * 60 // 30 days
  }
};

// URLs to cache on install
const STATIC_ASSETS = [
  '/',
  '/static/js/bundle.js',
  '/static/css/main.css',
  '/static/media/icons.woff2',
  '/manifest.json',
  '/favicon.ico',
  '/offline.html',
  '/images/fallback.jpg'
];

// API endpoints that should be cached
const API_ENDPOINTS = [
  '/api/user/profile',
  '/api/files/recent',
  '/api/settings',
  '/api/navigation/bookmarks'
];

// Routes that should work offline
const OFFLINE_FALLBACKS = {
  '/': '/offline.html',
  '/files': '/offline.html',
  '/search': '/offline.html'
};

/**
 * Service Worker Installation
 */
self.addEventListener('install', (event) => {
  console.log('🔧 Service Worker installing...');
  
  event.waitUntil(
    Promise.all([
      caches.open(STATIC_CACHE).then((cache) => {
        console.log('📦 Caching static assets');
        return cache.addAll(STATIC_ASSETS);
      }),
      skipWaiting()
    ])
  );
});

/**
 * Service Worker Activation
 */
self.addEventListener('activate', (event) => {
  console.log('🚀 Service Worker activating...');
  
  event.waitUntil(
    Promise.all([
      // Clean up old caches
      cleanupOldCaches(),
      // Claim all clients immediately
      clients.claim(),
      // Initialize background sync
      initializeBackgroundSync()
    ])
  );
});

/**
 * Fetch Event Handler - Main caching logic
 */
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const { url, method, destination } = request;
  
  // Only handle GET requests
  if (method !== 'GET') {
    return;
  }

  // Determine caching strategy based on request type
  if (isStaticAsset(url)) {
    event.respondWith(cacheFirst(request, STATIC_CACHE));
  } else if (isAPIRequest(url)) {
    event.respondWith(networkFirst(request, API_CACHE));
  } else if (isImageRequest(request)) {
    event.respondWith(cacheFirst(request, IMAGE_CACHE));
  } else if (isNavigationRequest(request)) {
    event.respondWith(networkFirstWithFallback(request));
  } else {
    event.respondWith(staleWhileRevalidate(request, DYNAMIC_CACHE));
  }
});

/**
 * Background Sync for offline actions
 */
self.addEventListener('sync', (event) => {
  console.log('🔄 Background sync triggered:', event.tag);
  
  if (event.tag === 'file-upload') {
    event.waitUntil(syncFileUploads());
  } else if (event.tag === 'api-requests') {
    event.waitUntil(syncApiRequests());
  } else if (event.tag === 'user-actions') {
    event.waitUntil(syncUserActions());
  }
});

/**
 * Push Notifications
 */
self.addEventListener('push', (event) => {
  console.log('📢 Push notification received');
  
  let notificationData = {};
  
  if (event.data) {
    try {
      notificationData = event.data.json();
    } catch (e) {
      notificationData = {
        title: 'ActiveLog',
        body: event.data.text() || 'New notification',
        icon: '/images/notification-icon.png',
        badge: '/images/badge.png'
      };
    }
  }
  
  const options = {
    body: notificationData.body,
    icon: notificationData.icon || '/images/notification-icon.png',
    badge: notificationData.badge || '/images/badge.png',
    vibrate: [100, 50, 100],
    data: notificationData.data,
    actions: notificationData.actions || [
      { action: 'open', title: 'Open' },
      { action: 'dismiss', title: 'Dismiss' }
    ],
    requireInteraction: notificationData.requireInteraction || false,
    tag: notificationData.tag || 'general'
  };
  
  event.waitUntil(
    self.registration.showNotification(notificationData.title || 'ActiveLog', options)
  );
});

/**
 * Notification Click Handler
 */
self.addEventListener('notificationclick', (event) => {
  console.log('🖱️ Notification clicked:', event.action);
  
  event.notification.close();
  
  const { action, notification } = event;
  const { data } = notification;
  
  if (action === 'open' || !action) {
    const urlToOpen = data?.url || '/';
    
    event.waitUntil(
      clients.matchAll({ type: 'window', includeUncontrolled: true })
        .then((clientList) => {
          // Check if window is already open
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
  }
});

/**
 * Message Handler for client communication
 */
self.addEventListener('message', (event) => {
  const { type, payload } = event.data;
  
  switch (type) {
    case 'SKIP_WAITING':
      self.skipWaiting();
      break;
      
    case 'GET_CACHE_SIZE':
      getCacheSize().then((size) => {
        event.ports[0].postMessage({ type: 'CACHE_SIZE', payload: size });
      });
      break;
      
    case 'CLEAR_CACHE':
      clearSpecificCache(payload.cacheName).then(() => {
        event.ports[0].postMessage({ type: 'CACHE_CLEARED', payload: payload.cacheName });
      });
      break;
      
    case 'PRELOAD_ROUTES':
      preloadRoutes(payload.routes);
      break;
      
    case 'UPDATE_CACHE_CONFIG':
      updateCacheConfig(payload);
      break;
  }
});

// ============================================================================
// CACHING STRATEGIES
// ============================================================================

/**
 * Cache First Strategy - For static assets
 */
async function cacheFirst(request, cacheName) {
  try {
    const cache = await caches.open(cacheName);
    const cachedResponse = await cache.match(request);
    
    if (cachedResponse) {
      // Update cache in background if resource is stale
      if (isStale(cachedResponse, CACHE_CONFIG.maxAge.static)) {
        fetchAndCache(request, cache);
      }
      return cachedResponse;
    }
    
    const networkResponse = await fetch(request);
    
    if (networkResponse.ok) {
      cache.put(request, networkResponse.clone());
    }
    
    return networkResponse;
  } catch (error) {
    console.error('Cache first failed:', error);
    return await getFallbackResponse(request);
  }
}

/**
 * Network First Strategy - For API requests
 */
async function networkFirst(request, cacheName) {
  try {
    const networkResponse = await fetch(request);
    
    if (networkResponse.ok) {
      const cache = await caches.open(cacheName);
      
      // Clone response before caching
      const responseClone = networkResponse.clone();
      
      // Add cache headers for TTL
      const responseWithHeaders = new Response(responseClone.body, {
        status: responseClone.status,
        statusText: responseClone.statusText,
        headers: {
          ...responseClone.headers,
          'sw-cached': Date.now().toString(),
          'sw-ttl': CACHE_CONFIG.maxAge.api.toString()
        }
      });
      
      cache.put(request, responseWithHeaders);
      
      // Clean up old entries
      await cleanupCache(cache, CACHE_CONFIG.maxEntries.api);
    }
    
    return networkResponse;
  } catch (error) {
    console.log('Network first falling back to cache:', error.message);
    
    const cache = await caches.open(cacheName);
    const cachedResponse = await cache.match(request);
    
    if (cachedResponse && !isStale(cachedResponse, CACHE_CONFIG.maxAge.api)) {
      return cachedResponse;
    }
    
    return await getFallbackResponse(request);
  }
}

/**
 * Stale While Revalidate Strategy - For dynamic content
 */
async function staleWhileRevalidate(request, cacheName) {
  const cache = await caches.open(cacheName);
  const cachedResponse = await cache.match(request);
  
  const fetchPromise = fetch(request).then((networkResponse) => {
    if (networkResponse.ok) {
      cache.put(request, networkResponse.clone());
      cleanupCache(cache, CACHE_CONFIG.maxEntries.dynamic);
    }
    return networkResponse;
  }).catch(() => cachedResponse || getFallbackResponse(request));
  
  return cachedResponse || fetchPromise;
}

/**
 * Network First with Fallback - For navigation requests
 */
async function networkFirstWithFallback(request) {
  try {
    const networkResponse = await fetch(request);
    
    if (networkResponse.ok) {
      const cache = await caches.open(DYNAMIC_CACHE);
      cache.put(request, networkResponse.clone());
      return networkResponse;
    }
    
    throw new Error(`Network response not ok: ${networkResponse.status}`);
  } catch (error) {
    console.log('Navigation request failed, serving fallback:', error.message);
    
    // Try to serve from cache first
    const cache = await caches.open(DYNAMIC_CACHE);
    const cachedResponse = await cache.match(request);
    
    if (cachedResponse) {
      return cachedResponse;
    }
    
    // Serve appropriate offline fallback
    const url = new URL(request.url);
    const fallbackPath = OFFLINE_FALLBACKS[url.pathname] || '/offline.html';
    
    return caches.match(fallbackPath) || getFallbackResponse(request);
  }
}

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

/**
 * Check if URL is a static asset
 */
function isStaticAsset(url) {
  return /\.(js|css|woff|woff2|ttf|eot|ico|png|jpg|jpeg|gif|svg|webp|avif)(\?.*)?$/.test(url);
}

/**
 * Check if URL is an API request
 */
function isAPIRequest(url) {
  return url.includes('/api/') || API_ENDPOINTS.some(endpoint => url.includes(endpoint));
}

/**
 * Check if request is for an image
 */
function isImageRequest(request) {
  return request.destination === 'image' || 
         /\.(png|jpg|jpeg|gif|svg|webp|avif|bmp)(\?.*)?$/.test(request.url);
}

/**
 * Check if request is a navigation request
 */
function isNavigationRequest(request) {
  return request.mode === 'navigate';
}

/**
 * Check if cached response is stale
 */
function isStale(response, maxAge) {
  const cachedTime = response.headers.get('sw-cached');
  if (!cachedTime) return false;
  
  const age = Date.now() - parseInt(cachedTime);
  return age > maxAge * 1000;
}

/**
 * Fetch and cache resource in background
 */
async function fetchAndCache(request, cache) {
  try {
    const response = await fetch(request);
    if (response.ok) {
      cache.put(request, response.clone());
    }
  } catch (error) {
    console.log('Background fetch failed:', error);
  }
}

/**
 * Get fallback response for failed requests
 */
async function getFallbackResponse(request) {
  if (isImageRequest(request)) {
    return caches.match('/images/fallback.jpg');
  }
  
  if (isNavigationRequest(request)) {
    return caches.match('/offline.html');
  }
  
  return new Response('Service Unavailable', {
    status: 503,
    statusText: 'Service Unavailable',
    headers: { 'Content-Type': 'text/plain' }
  });
}

/**
 * Clean up old cache entries
 */
async function cleanupCache(cache, maxEntries) {
  const keys = await cache.keys();
  
  if (keys.length > maxEntries) {
    const entriesToDelete = keys.slice(0, keys.length - maxEntries);
    await Promise.all(entriesToDelete.map(key => cache.delete(key)));
  }
}

/**
 * Clean up all old caches
 */
async function cleanupOldCaches() {
  const cacheNames = await caches.keys();
  const oldCaches = cacheNames.filter(name => 
    name.startsWith('activelog-') && !name.includes(CACHE_VERSION)
  );
  
  await Promise.all(oldCaches.map(name => caches.delete(name)));
  console.log(`🗑️ Cleaned up ${oldCaches.length} old caches`);
}

/**
 * Get total cache size
 */
async function getCacheSize() {
  const cacheNames = await caches.keys();
  let totalSize = 0;
  
  for (const name of cacheNames) {
    const cache = await caches.open(name);
    const keys = await cache.keys();
    
    for (const key of keys) {
      const response = await cache.match(key);
      if (response) {
        const blob = await response.blob();
        totalSize += blob.size;
      }
    }
  }
  
  return totalSize;
}

/**
 * Clear specific cache
 */
async function clearSpecificCache(cacheName) {
  return caches.delete(cacheName);
}

/**
 * Preload routes for faster navigation
 */
async function preloadRoutes(routes) {
  const cache = await caches.open(DYNAMIC_CACHE);
  
  const preloadPromises = routes.map(async (route) => {
    try {
      const response = await fetch(route);
      if (response.ok) {
        await cache.put(route, response);
      }
    } catch (error) {
      console.log(`Failed to preload route ${route}:`, error);
    }
  });
  
  await Promise.all(preloadPromises);
  console.log(`📦 Preloaded ${routes.length} routes`);
}

// ============================================================================
// BACKGROUND SYNC
// ============================================================================

/**
 * Initialize background sync
 */
async function initializeBackgroundSync() {
  try {
    await self.registration.sync.register('api-requests');
    console.log('🔄 Background sync initialized');
  } catch (error) {
    console.log('Background sync not supported:', error);
  }
}

/**
 * Sync file uploads
 */
async function syncFileUploads() {
  try {
    const db = await openIndexedDB();
    const pendingUploads = await getStoredData(db, 'pendingUploads');
    
    for (const upload of pendingUploads) {
      try {
        const formData = new FormData();
        formData.append('file', upload.file);
        formData.append('metadata', JSON.stringify(upload.metadata));
        
        const response = await fetch('/api/files/upload', {
          method: 'POST',
          body: formData
        });
        
        if (response.ok) {
          await removeStoredData(db, 'pendingUploads', upload.id);
          console.log('✅ File upload synced:', upload.filename);
        }
      } catch (error) {
        console.log('❌ File upload failed:', error);
      }
    }
  } catch (error) {
    console.log('Sync file uploads failed:', error);
  }
}

/**
 * Sync API requests
 */
async function syncApiRequests() {
  try {
    const db = await openIndexedDB();
    const pendingRequests = await getStoredData(db, 'pendingRequests');
    
    for (const request of pendingRequests) {
      try {
        const response = await fetch(request.url, {
          method: request.method,
          headers: request.headers,
          body: request.body
        });
        
        if (response.ok) {
          await removeStoredData(db, 'pendingRequests', request.id);
          console.log('✅ API request synced:', request.url);
        }
      } catch (error) {
        console.log('❌ API request failed:', error);
      }
    }
  } catch (error) {
    console.log('Sync API requests failed:', error);
  }
}

/**
 * Sync user actions
 */
async function syncUserActions() {
  try {
    const db = await openIndexedDB();
    const pendingActions = await getStoredData(db, 'pendingActions');
    
    for (const action of pendingActions) {
      try {
        // Process different types of user actions
        await processUserAction(action);
        await removeStoredData(db, 'pendingActions', action.id);
        console.log('✅ User action synced:', action.type);
      } catch (error) {
        console.log('❌ User action failed:', error);
      }
    }
  } catch (error) {
    console.log('Sync user actions failed:', error);
  }
}

// ============================================================================
// INDEXED DB UTILITIES
// ============================================================================

/**
 * Open IndexedDB for offline storage
 */
function openIndexedDB() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open('ActiveLogOffline', 1);
    
    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve(request.result);
    
    request.onupgradeneeded = (event) => {
      const db = event.target.result;
      
      if (!db.objectStoreNames.contains('pendingUploads')) {
        db.createObjectStore('pendingUploads', { keyPath: 'id' });
      }
      
      if (!db.objectStoreNames.contains('pendingRequests')) {
        db.createObjectStore('pendingRequests', { keyPath: 'id' });
      }
      
      if (!db.objectStoreNames.contains('pendingActions')) {
        db.createObjectStore('pendingActions', { keyPath: 'id' });
      }
    };
  });
}

/**
 * Get stored data from IndexedDB
 */
function getStoredData(db, storeName) {
  return new Promise((resolve, reject) => {
    const transaction = db.transaction([storeName], 'readonly');
    const store = transaction.objectStore(storeName);
    const request = store.getAll();
    
    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve(request.result);
  });
}

/**
 * Remove stored data from IndexedDB
 */
function removeStoredData(db, storeName, id) {
  return new Promise((resolve, reject) => {
    const transaction = db.transaction([storeName], 'readwrite');
    const store = transaction.objectStore(storeName);
    const request = store.delete(id);
    
    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve();
  });
}

/**
 * Process user action based on type
 */
async function processUserAction(action) {
  switch (action.type) {
    case 'bookmark':
      return fetch('/api/bookmarks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(action.data)
      });
      
    case 'settings_update':
      return fetch('/api/settings', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(action.data)
      });
      
    case 'file_operation':
      return fetch(`/api/files/${action.operation}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(action.data)
      });
      
    default:
      throw new Error(`Unknown action type: ${action.type}`);
  }
}

console.log('🚀 ActiveLog Service Worker loaded successfully');