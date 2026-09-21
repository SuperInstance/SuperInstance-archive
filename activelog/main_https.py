from http.server import HTTPServer, BaseHTTPRequestHandler
import ssl
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
        if self.path == '/':
            # Serve the index.html file
            try:
                with open('index.html', 'r') as f:
                    content = f.read()
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(content.encode())
            except FileNotFoundError:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b'index.html not found')
        elif self.path == '/api/entries':
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

# HTTPS server setup
port = int(os.environ.get('PORT', 8443))
print(f"Starting PersonalLog HTTPS API on port {port}...")
PersonalLogHandler.load_entries()
print(f"Loaded {len(PersonalLogHandler.entries)} existing entries")

# Create HTTPS server
httpd = HTTPServer(('0.0.0.0', port), PersonalLogHandler)

# Configure SSL
context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
context.load_cert_chain('ssl/server.crt', 'ssl/server.key')
httpd.socket = context.wrap_socket(httpd.socket, server_side=True)

print(f"HTTPS server running on https://0.0.0.0:{port}")
httpd.serve_forever()