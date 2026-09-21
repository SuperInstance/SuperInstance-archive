import os
from flask import Flask, render_template, request, jsonify
import json
from datetime import datetime
import random

app = Flask(__name__)

# Get port from environment variable, default to 8002
PORT = int(os.environ.get('PORT', 8002))

# Data storage
SESSIONS_FILE = 'sessions.json'
CHARACTERS_FILE = 'characters.json'

def load_data(filename):
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            return json.load(f)
    return []

def save_data(filename, data):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/health')
def health():
    return jsonify({'status': 'healthy', 'service': 'dmlog-session-logger', 'port': PORT})

@app.route('/sessions', methods=['GET', 'POST'])
def sessions():
    if request.method == 'GET':
        sessions = load_data(SESSIONS_FILE)
        return jsonify(sessions)
    
    elif request.method == 'POST':
        data = request.get_json()
        sessions = load_data(SESSIONS_FILE)
        
        new_session = {
            'id': len(sessions) + 1,
            'title': data.get('title', f"Session {len(sessions) + 1}"),
            'notes': data.get('notes', ''),
            'timestamp': datetime.now().isoformat(),
            'date': data.get('date', datetime.now().strftime('%Y-%m-%d'))
        }
        
        sessions.append(new_session)
        save_data(SESSIONS_FILE, sessions)
        
        return jsonify(new_session)

@app.route('/roll/<dice>')
def roll_dice(dice):
    try:
        if 'd' in dice.lower():
            num_dice, sides = dice.lower().split('d')
            num_dice = int(num_dice) if num_dice else 1
            sides = int(sides)
            
            rolls = [random.randint(1, sides) for _ in range(num_dice)]
            total = sum(rolls)
            
            return jsonify({
                'dice': dice,
                'rolls': rolls,
                'total': total
            })
        else:
            return jsonify({'error': 'Invalid dice format. Use format like "2d6" or "d20"'})
    except ValueError:
        return jsonify({'error': 'Invalid dice format'})

@app.route('/characters', methods=['GET', 'POST'])
def characters():
    if request.method == 'GET':
        characters = load_data(CHARACTERS_FILE)
        return jsonify(characters)
    
    elif request.method == 'POST':
        data = request.get_json()
        characters = load_data(CHARACTERS_FILE)
        
        new_character = {
            'id': len(characters) + 1,
            'name': data.get('name', ''),
            'class': data.get('class', ''),
            'level': data.get('level', 1),
            'hp': data.get('hp', 0),
            'notes': data.get('notes', ''),
            'created': datetime.now().isoformat()
        }
        
        characters.append(new_character)
        save_data(CHARACTERS_FILE, characters)
        
        return jsonify(new_character)

if __name__ == '__main__':
    os.makedirs('templates', exist_ok=True)
    print(f"Starting DMLog Session Logger on port {PORT}")
    app.run(host='0.0.0.0', port=PORT, debug=True)