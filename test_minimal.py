#!/usr/bin/env python3
"""
Minimal FastAPI test - no external dependencies
"""

try:
    from fastapi import FastAPI
    app = FastAPI()
    
    @app.get("/")
    def root():
        return {"message": "Minimal FastAPI works!", "status": "success"}
    
    @app.get("/health")
    def health():
        return {"status": "healthy", "app": "minimal-test"}
        
except ImportError:
    # Fallback to basic HTTP server if FastAPI not available
    import json
    from http.server import HTTPServer, BaseHTTPRequestHandler
    
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = {"message": "Basic Python works!", "path": self.path}
            self.wfile.write(json.dumps(response).encode())
    
    if __name__ == "__main__":
        import os
        port = int(os.getenv("PORT", 8000))
        server = HTTPServer(('0.0.0.0', port), Handler)
        server.serve_forever()

if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port) 