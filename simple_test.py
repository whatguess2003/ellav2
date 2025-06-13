#!/usr/bin/env python3
"""
Simple FastAPI test for Azure deployment
Minimal dependencies to test if Azure can run Python web apps
"""

from fastapi import FastAPI
import os
import sys

app = FastAPI(title="ELLA Simple Test")

@app.get("/")
async def root():
    return {
        "message": "ELLA Simple Test is running!",
        "python_version": sys.version,
        "port": os.getenv("PORT", "unknown"),
        "status": "healthy"
    }

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "ella-simple-test",
        "python_version": sys.version,
        "environment": "azure"
    }

@app.get("/test")
async def test():
    return {
        "message": "Test endpoint working",
        "imports_working": True,
        "fastapi_version": "working"
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8001))
    print(f"Starting simple test server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port) 