#!/usr/bin/env python3
"""
Azure App Service Entry Point
Azure expects app.py by default, so this imports our main application
"""

from main import app

if __name__ == "__main__":
    import uvicorn
    import os
    
    # Use Azure's PORT environment variable, fallback to 8000
    port = int(os.getenv("PORT", 8000))
    
    print("Starting ELLA via app.py entry point...")
    uvicorn.run(app, host="0.0.0.0", port=port) 