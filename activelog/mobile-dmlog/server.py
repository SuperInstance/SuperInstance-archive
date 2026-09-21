#!/usr/bin/env python3
"""
DMLog Mobile App Server
Serves the mobile app and provides sync endpoints
"""

from flask import Flask, send_from_directory, jsonify, request
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app)

# Serve static files
@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/<path:filename>')
def static_files(filename):
    return send_from_directory('.', filename)

# Mobile sync endpoint
@app.route('/api/mobile-sync', methods=['POST'])
def mobile_sync():
    data = request.json
    
    # In a real implementation, this would:
    # 1. Validate the data
    # 2. Save to database
    # 3. Return updated data from server
    
    return jsonify({
        'status': 'success',
        'message': 'Data synced successfully',
        'timestamp': data.get('timestamp')
    })

# Health check
@app.route('/api/health')
def health():
    return jsonify({
        'status': 'healthy',
        'service': 'dmlog-mobile',
        'version': '1.0.0'
    })

if __name__ == '__main__':
    import sys
    port = 8080
    if len(sys.argv) > 1 and sys.argv[1] == '--port' and len(sys.argv) > 2:
        port = int(sys.argv[2])
    else:
        port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=True)