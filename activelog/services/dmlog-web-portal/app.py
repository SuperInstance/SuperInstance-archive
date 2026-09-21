#!/usr/bin/env python3
"""
DMLog Web Portal - Cloud Accessible D&D Beyond Clone
Web version with login system for Max and Casey
"""

from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash, make_response
import os
import sqlite3
import json
import random
from datetime import datetime, timedelta
import requests
import hashlib
import time
from functools import wraps
import qrcode
import io
import base64

# Import production config if available
try:
    from production_config import *
    PRODUCTION_MODE = True
except ImportError:
    PRODUCTION_MODE = False
    SECRET_KEY = 'dmlog-web-portal-secret-2025'
    SECURITY_HEADERS = {}
    MAX_LOGIN_ATTEMPTS = 5
    LOGIN_LOCKOUT_MINUTES = 15

app = Flask(__name__)
app.secret_key = SECRET_KEY

# Database setup
DB_PATH = "/tmp/dmlog_web_portal.db"
# Use internal IP for backend to allow external access
BACKEND_URL = "http://172.22.219.126:8099"

def init_database():
    """Initialize web portal database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS web_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            display_name TEXT,
            last_login TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Insert Max and Casey
    cursor.execute("""
        INSERT OR REPLACE INTO web_users (username, password, display_name)
        VALUES 
        ('Max', 'Snow', 'Max - Dungeon Master'),
        ('Casey', 'Snow', 'Casey - Player')
    """)
    
    # Session tracking
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS web_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            session_id TEXT,
            login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()

# Initialize database on startup
init_database()

# Security middleware
@app.after_request
def add_security_headers(response):
    """Add security headers to all responses"""
    if PRODUCTION_MODE and SECURITY_HEADERS:
        for header, value in SECURITY_HEADERS.items():
            response.headers[header] = value
    return response

# Rate limiting storage
login_attempts = {}

def is_rate_limited(ip_address):
    """Check if IP address is rate limited for login attempts"""
    current_time = time.time()
    if ip_address in login_attempts:
        attempts = login_attempts[ip_address]
        # Clean old attempts
        attempts = [attempt for attempt in attempts if current_time - attempt < LOGIN_LOCKOUT_MINUTES * 60]
        login_attempts[ip_address] = attempts
        
        if len(attempts) >= MAX_LOGIN_ATTEMPTS:
            return True
    return False

def record_login_attempt(ip_address):
    """Record a failed login attempt"""
    current_time = time.time()
    if ip_address not in login_attempts:
        login_attempts[ip_address] = []
    login_attempts[ip_address].append(current_time)

def get_backend_data(endpoint):
    """Get data from mobile backend API"""
    try:
        response = requests.get(f"{BACKEND_URL}{endpoint}", timeout=5)
        if response.status_code == 200:
            return response.json()
        return {}
    except:
        return {}

@app.route('/')
def home():
    """Home page - redirect to login if not logged in"""
    if 'username' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Simple login page with rate limiting"""
    client_ip = request.environ.get('HTTP_X_REAL_IP', request.remote_addr)
    
    if request.method == 'POST':
        # Check rate limiting
        if is_rate_limited(client_ip):
            flash(f'Too many failed attempts. Please wait {LOGIN_LOCKOUT_MINUTES} minutes.', 'error')
            return render_template('login.html'), 429
        
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Basic input validation
        if not username or not password:
            flash('Username and password are required', 'error')
            return render_template('login.html')
        
        # Validate credentials
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT username, display_name FROM web_users 
            WHERE username = ? AND password = ?
        """, (username, password))
        
        user = cursor.fetchone()
        
        if user:
            session['username'] = user[0]
            session['display_name'] = user[1]
            session['login_time'] = datetime.now().isoformat()
            session['client_ip'] = client_ip
            
            # Update last login
            cursor.execute("""
                UPDATE web_users SET last_login = ? WHERE username = ?
            """, (datetime.now().isoformat(), username))
            
            # Log session
            cursor.execute("""
                INSERT INTO web_sessions (username, session_id)
                VALUES (?, ?)
            """, (username, request.cookies.get('session')))
            
            conn.commit()
            conn.close()
            
            flash(f'Welcome {user[1]}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            # Record failed attempt
            record_login_attempt(client_ip)
            conn.close()
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """Logout and clear session"""
    username = session.get('username', 'Unknown')
    session.clear()
    flash(f'Goodbye {username}!', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    """Main D&D Beyond clone dashboard"""
    if 'username' not in session:
        return redirect(url_for('login'))
    
    # Get data from backend
    sample_character = get_backend_data('/sample/character')
    spells_data = get_backend_data('/spells/search?query=')
    stats = get_backend_data('/stats')
    
    return render_template('dashboard.html', 
                         user=session,
                         character=sample_character,
                         spells=spells_data.get('spells', [])[:6],  # First 6 spells
                         stats=stats)

@app.route('/characters')
def characters():
    """Characters page"""
    if 'username' not in session:
        return redirect(url_for('login'))
    
    sample_character = get_backend_data('/sample/character')
    return render_template('characters.html', user=session, character=sample_character)

@app.route('/spells')
def spells():
    """Spells page"""
    if 'username' not in session:
        return redirect(url_for('login'))
    
    query = request.args.get('query', '')
    level = request.args.get('level', '')
    
    endpoint = f'/spells/search?query={query}'
    if level:
        endpoint += f'&level={level}'
    
    spells_data = get_backend_data(endpoint)
    return render_template('spells.html', 
                         user=session, 
                         spells=spells_data.get('spells', []),
                         query=query,
                         level=level)

@app.route('/dice')
def dice():
    """Dice roller page"""
    if 'username' not in session:
        return redirect(url_for('login'))
    
    return render_template('dice.html', user=session)

@app.route('/campaigns')
def campaigns():
    """Campaigns page"""
    if 'username' not in session:
        return redirect(url_for('login'))
    
    return render_template('campaigns.html', user=session)

@app.route('/voice')
def voice():
    """Voice control page"""
    if 'username' not in session:
        return redirect(url_for('login'))
    
    return render_template('voice.html', user=session)

@app.route('/mobile-instructions')
def mobile_instructions():
    """Mobile app setup instructions"""
    if 'username' not in session:
        return redirect(url_for('login'))
    
    # Get the current tunnel URL from request headers or set a default
    base_url = request.headers.get('Host', 'localhost:8105')
    mobile_url = f"exp://exp.host/@dmlog/{base_url}"
    
    return render_template('mobile_instructions.html', user=session, mobile_url=mobile_url)

@app.route('/mobile-qr')
def mobile_qr():
    """Mobile QR codes for both platforms"""
    if 'username' not in session:
        return redirect(url_for('login'))
    
    return render_template('mobile_qr_codes.html', user=session)

@app.route('/qr-code')
def generate_qr_code():
    """Generate QR code for mobile app"""
    if 'username' not in session:
        return redirect(url_for('login'))
    
    # Get the current host to generate proper mobile URL
    base_url = request.headers.get('Host', 'localhost:8105')
    
    # Use the public tunnel URL for the mobile app
    expo_url = "exp://dmlog-expo.loca.lt"
    
    # Generate QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(expo_url)
    qr.make(fit=True)
    
    # Create QR code image
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Convert to base64 for embedding
    img_buffer = io.BytesIO()
    img.save(img_buffer, format='PNG')
    img_buffer.seek(0)
    
    response = make_response(img_buffer.getvalue())
    response.headers['Content-Type'] = 'image/png'
    return response

# API Routes for web interface
@app.route('/api/roll-dice')
def api_roll_dice():
    """Roll dice via API"""
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    sides = request.args.get('sides', 20, type=int)
    count = request.args.get('count', 1, type=int)
    
    dice_data = get_backend_data(f'/dice/roll/{sides}?count={count}')
    
    if dice_data:
        return jsonify(dice_data)
    else:
        # Fallback local dice rolling
        results = [random.randint(1, sides) for _ in range(count)]
        return jsonify({
            'dice': f'{count}d{sides}',
            'results': results,
            'total': sum(results),
            'timestamp': datetime.now().isoformat()
        })

@app.route('/api/voice-command', methods=['POST'])
def api_voice_command():
    """Process voice command"""
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    command_text = request.json.get('command_text', '')
    
    # Send to backend
    try:
        response = requests.post(f"{BACKEND_URL}/voice/command", 
                               json={
                                   'command_text': command_text,
                                   'user_id': session['username'],
                                   'confidence': 1.0
                               },
                               timeout=5)
        
        if response.status_code == 200:
            return response.json()
    except:
        pass
    
    # Fallback response
    return jsonify({
        'success': True,
        'response': f'Web version heard: "{command_text}". Use the mobile app for full voice features!'
    })

if __name__ == '__main__':
    port = int(os.getenv('PORT', 8100))
    print(f"🌐 Starting DMLog Web Portal on port {port}")
    print(f"📱 Access at: http://localhost:{port}")
    print(f"👥 Users: Max/Snow, Casey/Snow")
    print(f"🎲 Backend: {BACKEND_URL}")
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=True
    )