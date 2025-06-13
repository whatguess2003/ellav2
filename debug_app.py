#!/usr/bin/env python3
"""
Debug version of ELLA app for Railway testing
"""

from fastapi import FastAPI
from fastapi.responses import JSONResponse
import os

# Initialize FastAPI app
app = FastAPI(title="ELLA Debug", version="1.0.0")

@app.get("/")
async def root():
    """Simple root endpoint"""
    return JSONResponse({
        "message": "ELLA Debug App is running!",
        "port": os.getenv("PORT", "not set"),
        "status": "healthy"
    })

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return JSONResponse({
        "status": "healthy",
        "service": "ella-debug",
        "port": os.getenv("PORT", "not set")
    })

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    print(f"Starting debug app on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port) 