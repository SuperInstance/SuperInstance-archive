from http.server import HTTPServer, BaseHTTPRequestHandler
import json
from datetime import datetime

class PersonalLogHandler(BaseHTTPRequestHandler):
    entries = []
    
    def do_GET(self):
        if self.path == '/api/entries':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(self.entries).encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_POST(self):
        if self.path == '/api/entry':
            length = int(self.headers['Content-Length'])
            data = json.loads(self.rfile.read(length))
            entry = {
                'id': len(self.entries) + 1,
                'timestamp': datetime.now().isoformat(),
                'text': data.get('text', '')
            }
            self.entries.append(entry)
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(entry).encode())

print("Starting PersonalLog API on port 8000...")
HTTPServer(('0.0.0.0', 8000), PersonalLogHandler).serve_forever()
