#!/usr/bin/env python3
"""
ELLA Voice Hotel Assistant Server - Clean Implementation
Fixed all import and startup issues
"""

import asyncio
import json
import logging
import time
import uuid
import os
from typing import Optional, Dict

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import redis.asyncio as redis
from openai import AsyncOpenAI

# Import our functions and config
from .functions import search_hotels, get_hotel_details, get_room_types, check_availability, check_booking_status, initiate_chat_handoff
from .config import (
    REDIS_CONFIG, VOICE_MODEL, INSTRUCTIONS, 
    VOICE_SETTINGS, REALTIME_VOICE_FUNCTIONS, AUDIO_CONFIG, TURN_DETECTION_CONFIG,
    PERFORMANCE_CONFIG, QUICK_RESPONSES, SEARCH_CONFIG, get_guest_id
)

# Environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Setup
app = FastAPI(title="ELLA Voice Hotel", version="2.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# Clients
openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)
redis_client = redis.Redis(**REDIS_CONFIG)

# Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Active connections
connections: Dict[str, WebSocket] = {}

class TokenRequest(BaseModel):
    session_id: Optional[str] = None

def get_guest_id():
    return f"guest_{str(uuid.uuid4())[:8]}"

@app.get("/voice/health")
async def health():
    return {
        "status": "healthy",
        "model": VOICE_MODEL,
        "voice": VOICE_SETTINGS,
        "openai_configured": bool(OPENAI_API_KEY)
    }

@app.post("/voice/ephemeral-token")
async def create_token(request: TokenRequest):
    try:
        session = await openai_client.beta.realtime.sessions.create(
            model=VOICE_MODEL,
            modalities=["text", "audio"],
            instructions=INSTRUCTIONS,
            voice=VOICE_SETTINGS,
            input_audio_format=AUDIO_CONFIG["input_audio_format"],
            output_audio_format=AUDIO_CONFIG["output_audio_format"],
            input_audio_transcription=AUDIO_CONFIG["input_audio_transcription"],
            turn_detection=TURN_DETECTION_CONFIG,
            tools=REALTIME_VOICE_FUNCTIONS,
            tool_choice="auto",
            temperature=0.8,
            max_response_output_tokens=4096
        )
        
        return {
            "ephemeral_key": session.client_secret,
            "session_id": session.id,
            "model": VOICE_MODEL
        }
    except Exception as e:
        logger.error(f"Token creation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

FUNCTIONS = {
    "search_hotels": search_hotels,
    "get_hotel_details": get_hotel_details,
    "get_room_types": get_room_types,
    "check_availability": check_availability,
    "check_booking_status": check_booking_status,
    "initiate_chat_handoff": initiate_chat_handoff
}

@app.websocket("/voice/realtime_hotel")
async def realtime_hotel(websocket: WebSocket, guest_id: str = None):
    if not guest_id:
        guest_id = get_guest_id()
    
    await websocket.accept()
    connection_id = f"{guest_id}_{int(time.time())}"
    connections[connection_id] = websocket
    
    logger.info(f"[VOICE] Guest {guest_id} connected")
    
    try:
        async with openai_client.beta.realtime.connect(model=VOICE_MODEL) as connection:
            # Configure session
            await connection.session.update(session={
                "modalities": ["text", "audio"],
                "instructions": INSTRUCTIONS,
                "voice": VOICE_SETTINGS,
                "input_audio_format": AUDIO_CONFIG["input_audio_format"],
                "output_audio_format": AUDIO_CONFIG["output_audio_format"],
                "input_audio_transcription": AUDIO_CONFIG["input_audio_transcription"],
                "turn_detection": TURN_DETECTION_CONFIG,
                "tools": REALTIME_VOICE_FUNCTIONS,
                "tool_choice": "auto",
                "temperature": 0.8,
                "max_response_output_tokens": 4096
            })
            
            logger.info(f"[VOICE] Session configured for {guest_id}")
            
            async def handle_client():
                try:
                    while True:
                        message = await websocket.receive_text()
                        data = json.loads(message)
                        
                        if data.get("type") == "input_audio_buffer.append":
                            await connection.input_audio_buffer.append(audio=data.get("audio", ""))
                        elif data.get("type") == "input_audio_buffer.commit":
                            await connection.input_audio_buffer.commit()
                        elif data.get("type") == "response.create":
                            await connection.response.create()
                        elif data.get("type") == "conversation.item.create":
                            await connection.conversation.item.create(item=data.get("item", {}))
                        
                except WebSocketDisconnect:
                    logger.info(f"[VOICE] Client {guest_id} disconnected")
                except Exception as e:
                    logger.error(f"[VOICE] Client error: {e}")
            
            async def handle_openai():
                try:
                    async for event in connection:
                        # Handle function calls
                        if event.type == "response.output_item.done":
                            # Check if this is a function call
                            if hasattr(event, 'item') and event.item.type == "function_call":
                                func_name = event.item.name
                                args = json.loads(event.item.arguments)
                                
                                if func_name in FUNCTIONS:
                                    logger.info(f"[FUNCTION] Executing {func_name}")
                                    args["guest_id"] = guest_id
                                    
                                    try:
                                        result = FUNCTIONS[func_name](**args)
                                        await connection.conversation.item.create(item={
                                            "type": "function_call_output",
                                            "call_id": event.item.call_id,
                                            "output": json.dumps(result)
                                        })
                                        await connection.response.create()
                                    except Exception as e:
                                        logger.error(f"[FUNCTION] Error: {e}")
                                        await connection.conversation.item.create(item={
                                            "type": "function_call_output",
                                            "call_id": event.item.call_id,
                                            "output": json.dumps({"error": str(e)})
                                        })
                        
                        # Forward event to client
                        try:
                            # Handle audio events specially to extract actual audio data
                            if event.type == "response.audio.delta":
                                # Extract the actual audio data but keep original event type
                                audio_data = {
                                    "type": "response.audio.delta",
                                    "delta": event.delta if hasattr(event, 'delta') else ""
                                }
                                await websocket.send_text(json.dumps(audio_data))
                            elif event.type == "response.text.delta":
                                # Extract text data but keep original event type
                                text_data = {
                                    "type": "response.text.delta", 
                                    "delta": event.delta if hasattr(event, 'delta') else ""
                                }
                                await websocket.send_text(json.dumps(text_data))
                            elif event.type == "input_audio_buffer.speech_started":
                                await websocket.send_text(json.dumps({"type": "input_audio_buffer.speech_started"}))
                            elif event.type == "input_audio_buffer.speech_stopped":
                                await websocket.send_text(json.dumps({"type": "input_audio_buffer.speech_stopped"}))
                            elif event.type == "response.done":
                                await websocket.send_text(json.dumps({"type": "response.done"}))
                            else:
                                # Forward other events as-is
                                event_data = {
                                    "type": event.type,
                                    "event": event.model_dump() if hasattr(event, 'model_dump') else str(event)
                                }
                                await websocket.send_text(json.dumps(event_data))
                        except Exception as e:
                            logger.error(f"[VOICE] Send error: {e}")
                            break
                            
                except Exception as e:
                    logger.error(f"[VOICE] OpenAI error: {e}")
            
            # Run both handlers
            await asyncio.gather(handle_client(), handle_openai(), return_exceptions=True)
            
    except Exception as e:
        logger.error(f"[VOICE] Connection error: {e}")
    finally:
        if connection_id in connections:
            del connections[connection_id]
        logger.info(f"[VOICE] Cleaned up {guest_id}")

@app.websocket("/voice/realtime_chat")
async def realtime_chat(websocket: WebSocket, guest_id: str = None):
    """Alias for realtime_hotel endpoint - what the client expects"""
    await realtime_hotel(websocket, guest_id)

if __name__ == "__main__":
    logger.info("🚀 Starting ELLA Voice Hotel Server")
    uvicorn.run(app, host="0.0.0.0", port=8004, log_level="info") 