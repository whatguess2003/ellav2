#!/usr/bin/env python3
"""
Most basic Python web test for Azure
"""

import os
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler

class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = '{"status": "healthy", "message": "Basic Python server working"}'
            self.wfile.write(response.encode())
        else:
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            response = f'<h1>Basic Python Test</h1><p>Python {sys.version}</p><p>Port: {os.getenv("PORT", "unknown")}</p>'
            self.wfile.write(response.encode())

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8001))
    server = HTTPServer(('0.0.0.0', port), SimpleHandler)
    print(f"Starting basic server on port {port}")
    server.serve_forever() 