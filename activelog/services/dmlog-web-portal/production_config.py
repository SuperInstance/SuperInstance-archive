#!/usr/bin/env python3
"""
Production configuration for DMLog Web Portal
Secure settings for public internet access
"""

import os
import secrets

# Generate secure session key
SECRET_KEY = os.getenv('FLASK_SECRET_KEY', secrets.token_hex(32))

# Security headers
SECURITY_HEADERS = {
    'X-Frame-Options': 'DENY',
    'X-Content-Type-Options': 'nosniff',
    'X-XSS-Protection': '1; mode=block',
    'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
    'Content-Security-Policy': "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'"
}

# Rate limiting
RATE_LIMIT_ENABLED = True
MAX_REQUESTS_PER_MINUTE = 60
MAX_LOGIN_ATTEMPTS = 5
LOGIN_LOCKOUT_MINUTES = 15

# Session configuration
SESSION_TIMEOUT_HOURS = 8
SESSION_COOKIE_SECURE = False  # Set to True if using HTTPS
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'

# Database configuration
DATABASE_BACKUP_ENABLED = True
DATABASE_BACKUP_INTERVAL_HOURS = 6

# Logging configuration
LOG_LEVEL = 'INFO'
LOG_FILE = '/tmp/dmlog_web_portal.log'
LOG_MAX_SIZE_MB = 50
LOG_BACKUP_COUNT = 5

# Network configuration
ALLOWED_HOSTS = ['*']  # In production, restrict to specific domains
CORS_ORIGINS = ['*']   # In production, restrict to specific origins

# Feature flags
ENABLE_DEBUG_ROUTES = False
ENABLE_ADMIN_PANEL = True
ENABLE_API_DOCS = True

# External services
BACKEND_TIMEOUT_SECONDS = 10
RETRY_ATTEMPTS = 3

print("🔒 Production configuration loaded")
print(f"🔑 Secret key: {SECRET_KEY[:16]}...")
print(f"🛡️ Security headers: {len(SECURITY_HEADERS)} enabled")
print(f"⏱️ Rate limiting: {MAX_REQUESTS_PER_MINUTE} req/min")