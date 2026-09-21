// CloudFront Function for Security Headers
// This function adds security headers to responses and handles basic security checks

function handler(event) {
    var request = event.request;
    var response = event.response;
    var headers = response.headers;

    // Add security headers
    headers['strict-transport-security'] = { value: 'max-age=31536000; includeSubDomains; preload' };
    headers['x-content-type-options'] = { value: 'nosniff' };
    headers['x-frame-options'] = { value: 'DENY' };
    headers['x-xss-protection'] = { value: '1; mode=block' };
    headers['referrer-policy'] = { value: 'strict-origin-when-cross-origin' };
    
    // Content Security Policy for ActiveLog
    headers['content-security-policy'] = { 
        value: "default-src 'self' 'unsafe-inline' 'unsafe-eval' *.activelog.com; " +
               "img-src 'self' data: *.activelog.com *.amazonaws.com; " +
               "connect-src 'self' *.activelog.com wss: ws:; " +
               "font-src 'self' fonts.googleapis.com fonts.gstatic.com; " +
               "style-src 'self' 'unsafe-inline' fonts.googleapis.com; " +
               "script-src 'self' 'unsafe-inline' 'unsafe-eval' *.activelog.com"
    };

    // Add feature policy headers
    headers['permissions-policy'] = { 
        value: 'geolocation=(), microphone=(), camera=(), payment=(), usb=()' 
    };

    // Add custom headers for ActiveLog
    headers['x-powered-by'] = { value: 'ActiveLog Platform' };
    headers['x-version'] = { value: '1.0.0' };
    
    // Add cache control for different content types
    var uri = request.uri;
    
    if (uri.includes('/static/') || uri.includes('/assets/')) {
        // Long cache for static assets
        headers['cache-control'] = { value: 'public, max-age=31536000, immutable' };
    } else if (uri.includes('/api/')) {
        // Short cache for API responses
        headers['cache-control'] = { value: 'public, max-age=300' };
    } else if (uri === '/sw.js' || uri === '/manifest.json') {
        // No cache for service worker and manifest
        headers['cache-control'] = { value: 'no-cache, no-store, must-revalidate' };
    }

    // Add CORS headers for API requests
    if (request.method === 'OPTIONS' || uri.includes('/api/')) {
        headers['access-control-allow-origin'] = { value: '*' };
        headers['access-control-allow-methods'] = { value: 'GET, POST, PUT, DELETE, OPTIONS' };
        headers['access-control-allow-headers'] = { value: 'Content-Type, Authorization, X-Requested-With' };
        headers['access-control-max-age'] = { value: '86400' };
    }

    // Handle preflight requests
    if (request.method === 'OPTIONS') {
        return {
            statusCode: 200,
            statusDescription: 'OK',
            headers: headers
        };
    }

    return response;
}