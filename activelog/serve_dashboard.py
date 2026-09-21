#!/usr/bin/env python3
import http.server
import socketserver
import os

os.chdir(os.path.expanduser("~/activelog"))
PORT = 8090

Handler = http.server.SimpleHTTPRequestHandler

with socketserver.TCPServer(("", PORT), Handler) as httpd:
    print(f"Beta Dashboard running at: http://localhost:{PORT}/beta_dashboard.html")
    httpd.serve_forever()
