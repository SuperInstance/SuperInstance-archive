from http.server import HTTPServer, BaseHTTPRequestHandler
import json
from datetime import datetime
import os

class PersonalLogHandler(BaseHTTPRequestHandler):
    entries = []
    entries_file = 'entries.json'
    
    @classmethod
    def load_entries(cls):
        try:
            if os.path.exists(cls.entries_file):
                with open(cls.entries_file, 'r') as f:
                    cls.entries = json.load(f)
        except (json.JSONDecodeError, IOError):
            cls.entries = []
    
    @classmethod
    def save_entries(cls):
        try:
            with open(cls.entries_file, 'w') as f:
                json.dump(cls.entries, f, indent=2)
        except IOError:
            pass
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def do_GET(self):
        if self.path == '/api/entries':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(self.entries).encode())
    
    def do_POST(self):
        if self.path == '/api/entry':
            length = int(self.headers['Content-Length'])
            data = json.loads(self.rfile.read(length))
            entry = {
                'id': len(self.entries) + 1,
                'timestamp': datetime.now().isoformat(),
                'text': data.get('text', ''),
                'audio': data.get('audio', None)
            }
            self.entries.append(entry)
            self.save_entries()
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(entry).encode())

port = int(os.environ.get('PORT', 8000))
print(f"Starting PersonalLog API on port {port}...")
PersonalLogHandler.load_entries()
print(f"Loaded {len(PersonalLogHandler.entries)} existing entries")
HTTPServer(('0.0.0.0', port), PersonalLogHandler).serve_forever()
