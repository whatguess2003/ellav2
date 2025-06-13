#!/usr/bin/env python3
"""
ELLA Hotel Assistant - Guest-Facing Chat Server
READ-ONLY access to media and database (except booking confirmations)
Deployed: 2025-06-13 03:55 UTC
"""

from fastapi import FastAPI, Request, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from chat_assistant import get_chat_agent
from core.guest_id import get_guest_id
from memory.redis_memory import append_dialog_turn, get_dialog_history
import json
import os
from pathlib import Path
from typing import Optional, List
import uuid
import mimetypes
from datetime import datetime

# WhatsApp Business API integration
try:
    from whatsapp_business_api import WhatsAppBusinessAPI
    WHATSAPP_INTEGRATION_AVAILABLE = True
    whatsapp_api = WhatsAppBusinessAPI()
    print("✅ WhatsApp Business API integration loaded")
except ImportError as e:
    print(f"⚠️ WhatsApp Business API not available: {e}")
    WHATSAPP_INTEGRATION_AVAILABLE = False
    whatsapp_api = None

# Initialize FastAPI app
app = FastAPI(title="ELLA Hotel Assistant", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create media directories (if needed)
media_storage_path = Path("media_storage")
media_storage_path.mkdir(exist_ok=True)

# Initialize READ-ONLY media tools for ELLA
try:
    from chat_assistant.chat_tools.media_sharer import search_hotel_media, guest_search_hotel_media
    MEDIA_TOOLS_AVAILABLE = True
    print("ELLA: Enhanced file-based media system initialized successfully")
except ImportError as e:
    print(f"ELLA: Media tools not available: {e}")
    MEDIA_TOOLS_AVAILABLE = False

# Initialize the chat agent
ella_agent = get_chat_agent()

# Request/Response models
class MessageRequest(BaseModel):
    content: str
    guest_id: Optional[str] = None

class BridgeMessageRequest(BaseModel):
    guest_id: str
    message: str
    sender: str = "assistant"  # Who is sending the message
    source: str = "voice_bridge"  # Where it came from

class MessageResponse(BaseModel):
    message: str
    guest_id: str
    type: str = "agent_response"

@app.get("/")
async def root():
    """ELLA API Root endpoint"""
    return JSONResponse({
        "message": "ELLA Hotel Assistant API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "message": "/message",
            "webhook": "/webhook"
        }
    })

@app.get("/guest")
async def guest_interface():
    """Guest API endpoint"""
    return JSONResponse({
        "message": "ELLA Guest API",
        "status": "available"
    })

@app.post("/message", response_model=MessageResponse)
async def process_message(request: MessageRequest):
    """
    Process chat messages through ELLA's unified agent.
    Handles hotel search, booking, and general conversation.
    READ-ONLY access except for booking confirmations.
    """
    try:
        # Use provided guest_id or generate one
        guest_id = request.guest_id or get_guest_id()
        
        # Process message through unified agent
        result = ella_agent.handle_message(request.content, guest_id)
        
        return MessageResponse(
            message=result["message"],
            guest_id=guest_id,
            type="ella_response"
        )
        
    except Exception as e:
        print(f"ELLA Error processing message: {e}")
        return MessageResponse(
            message="Maaf, ada masalah dengan sistem. Cuba lagi nanti.",
            guest_id=request.guest_id or "unknown",
            type="error"
        )

@app.post("/bridge/send_message")
async def bridge_send_message(request: BridgeMessageRequest):
    """
    Bridge endpoint for voice server to send messages to chat interface
    This enables real-time communication between voice and chat servers
    """
    try:
        print(f"ELLA BRIDGE: Received message from {request.source} for {request.guest_id}")
        
        # Add the message to the chat thread
        chat_thread_id = f"{request.guest_id}_chat_thread"
        append_dialog_turn(chat_thread_id, request.sender, request.message)
        
        # Get updated conversation history
        chat_history = get_dialog_history(chat_thread_id)
        
        print(f"ELLA BRIDGE: Message successfully added to chat thread")
        print(f"ELLA BRIDGE: Chat thread now has {len(chat_history)} messages")
        
        return {
            "success": True,
            "message": "Message successfully bridged to chat",
            "guest_id": request.guest_id,
            "chat_thread_length": len(chat_history),
            "bridged_message_preview": request.message[:50] + "..." if len(request.message) > 50 else request.message
        }
        
    except Exception as e:
        print(f"ELLA BRIDGE ERROR: {e}")
        raise HTTPException(status_code=500, detail=f"Bridge error: {str(e)}")

@app.post("/bridge/initiate_chat")
async def initiate_chat_from_voice(request: BridgeMessageRequest):
    """
    Initiate chat conversation after voice handoff
    ELLA proactively starts the chat conversation with context from voice call
    """
    try:
        print(f"🎯 ELLA CHAT INITIATION: Starting chat for {request.guest_id} from {request.source}")
        
        # Add ELLA's initiation message to chat thread
        chat_thread_id = f"{request.guest_id}_chat_thread"
        append_dialog_turn(chat_thread_id, "assistant", request.message)
        
        # Log the handoff
        print(f"🎯 ELLA CHAT INITIATION: ELLA said: {request.message}")
        
        return {
            "success": True,
            "message": "Chat conversation initiated by ELLA",
            "guest_id": request.guest_id,
            "ella_initiated": True,
            "initiation_message": request.message
        }
        
    except Exception as e:
        print(f"🎯 ELLA CHAT INITIATION ERROR: {e}")
        raise HTTPException(status_code=500, detail=f"Chat initiation error: {str(e)}")

@app.get("/api/chat/check_initiation/{guest_id}")
async def check_chat_initiation(guest_id: str):
    """
    Check if ELLA has initiated a chat conversation for this guest
    Used by chat.html to detect and display ELLA-initiated messages
    """
    try:
        chat_thread_id = f"{guest_id}_chat_thread"
        chat_history = get_dialog_history(chat_thread_id)
        
        # Check if the last message is from assistant (ELLA initiated)
        if chat_history and chat_history[-1]["role"] == "assistant":
            latest_message = chat_history[-1]
            return {
                "ella_initiated": True,
                "message": latest_message["content"],
                "timestamp": latest_message.get("timestamp"),
                "total_messages": len(chat_history)
            }
        
        return {
            "ella_initiated": False,
            "total_messages": len(chat_history)
        }
        
    except Exception as e:
        print(f"🎯 CHAT INITIATION CHECK ERROR: {e}")
        return {"ella_initiated": False, "error": str(e)}

@app.post("/api/simulate/voice_handoff")
async def simulate_voice_handoff():
    """
    Simulate voice-to-chat handoff for demonstration
    Creates a realistic scenario where ELLA initiates chat after voice call
    """
    try:
        # Get current guest_id
        guest_id = get_guest_id()
        
        # Simulate ELLA initiating chat after voice call
        handoff_message = """Hi! I'm continuing our conversation from the voice call. 

You mentioned you need a hotel in KL for this weekend. I can help you find the perfect place and show you photos, handle booking, and even generate a confirmation PDF.

To get started, could you tell me:
• How many people will be staying?
• Any specific preferences? (luxury, budget, pool, spa, etc.)

I'll search and show you the best options! 🏨"""

        # Add ELLA's initiation message to chat thread
        chat_thread_id = f"{guest_id}_chat_thread"
        append_dialog_turn(chat_thread_id, "assistant", handoff_message)
        
        return {
            "success": True,
            "message": "Voice-to-chat handoff simulated successfully",
            "guest_id": guest_id,
            "ella_initiated": True,
            "scenario": "Hotel search continuation from voice call",
            "next_step": "Open chat.html to see ELLA's initiation message",
            "chat_url": "/static/chat.html"
        }
        
    except Exception as e:
        print(f"🎯 VOICE HANDOFF SIMULATION ERROR: {e}")
        raise HTTPException(status_code=500, detail=f"Simulation error: {str(e)}")

@app.get("/bridge/status/{guest_id}")
async def bridge_status(guest_id: str):
    """
    Get bridge status and conversation counts for a guest
    """
    try:
        voice_thread_id = f"{guest_id}_voice_thread"
        chat_thread_id = f"{guest_id}_chat_thread"
        
        voice_history = get_dialog_history(voice_thread_id)
        chat_history = get_dialog_history(chat_thread_id)
        
        return {
            "guest_id": guest_id,
            "voice_messages": len(voice_history),
            "chat_messages": len(chat_history),
            "last_voice_message": voice_history[-1] if voice_history else None,
            "last_chat_message": chat_history[-1] if chat_history else None,
            "bridge_status": "active"
        }
        
    except Exception as e:
        print(f"ELLA BRIDGE STATUS ERROR: {e}")
        raise HTTPException(status_code=500, detail=f"Status error: {str(e)}")

@app.get("/api/guest-id")
async def get_guest_id_endpoint():
    """Get consistent guest_id from backend system"""
    guest_id = get_guest_id()
    return {
        "guest_id": guest_id,
        "source": "core.guest_id",
        "consistent": True
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy", 
        "service": "ella_guest_assistant",
        "access_level": "READ_ONLY",
        "capabilities": {
            "guest_chat": True,
            "hotel_search": True,
            "booking_confirmation": True,  # Only write access ELLA has
            "media_viewing": MEDIA_TOOLS_AVAILABLE,
            "media_upload": False,  # Moved to LEON
            "whatsapp_integration": WHATSAPP_INTEGRATION_AVAILABLE
        }
    }

# 📱 WHATSAPP BUSINESS API WEBHOOK ENDPOINTS

@app.get("/webhook")
async def verify_whatsapp_webhook(request: Request):
    """Verify webhook for WhatsApp Business API setup"""
    import os
    WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "ella_verify_token_2024")
    
    mode = request.query_params.get('hub.mode')
    token = request.query_params.get('hub.verify_token')
    challenge = request.query_params.get('hub.challenge')
    
    print(f"🔍 WhatsApp webhook verification: mode={mode}, token={token}, challenge={challenge}")
    print(f"🔍 Expected token: {WHATSAPP_VERIFY_TOKEN}")
    
    if mode == 'subscribe' and token == WHATSAPP_VERIFY_TOKEN:
        print("✅ WhatsApp webhook verified successfully")
        return challenge
    else:
        print("❌ WhatsApp webhook verification failed")
        print(f"❌ Mode check: {mode == 'subscribe'}, Token check: {token == WHATSAPP_VERIFY_TOKEN}")
        raise HTTPException(status_code=403, detail="Webhook verification failed")

@app.post("/webhook")
async def whatsapp_webhook(request: Request):
    """WhatsApp Business API webhook endpoint"""
    try:
        webhook_data = await request.json()
        
        if not webhook_data:
            raise HTTPException(status_code=400, detail="No JSON data")
        
        print("📱 WhatsApp webhook received:")
        print(f"📱 Data: {webhook_data}")
        
        # For now, just acknowledge the webhook
        # TODO: Process webhook through WhatsApp API handler when integration is ready
        if WHATSAPP_INTEGRATION_AVAILABLE and whatsapp_api:
            result = await whatsapp_api.process_webhook(webhook_data)
            return {"status": "ok", "result": result}
        else:
            print("📱 WhatsApp integration not available, acknowledging webhook")
            return {"status": "ok", "message": "Webhook received"}
        
    except Exception as e:
        print(f"❌ WhatsApp webhook error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# 📸 READ-ONLY MEDIA ENDPOINTS FOR GUESTS

@app.get("/media/{file_id}")
async def serve_media_to_guest(file_id: str):
    """Serve media files to guests (READ-ONLY)"""
    try:
        # Check if it's a demo file
        if file_id.startswith("demo_"):
            # Demo files are served from static/demo-photos directory
            return {"message": "Demo photo", "url": f"/static/demo-photos/{file_id}.jpg"}
        
        # Check database for real file (READ-ONLY)
        if MEDIA_TOOLS_AVAILABLE:
            import sqlite3
            with sqlite3.connect("ella.db") as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT local_path, cloud_url, original_name, file_type 
                    FROM production_media_files 
                    WHERE file_id = ? AND is_public = 1
                """, (file_id,))
                
                result = cursor.fetchone()
                if result:
                    local_path, cloud_url, original_name, file_type = result
                    
                    # Log guest access (analytics only)
                    cursor.execute("""
                        INSERT INTO media_analytics (file_id, event_type, user_id, metadata)
                        VALUES (?, 'guest_view', 'ella_guest', '{"source": "ella"}')
                    """, (file_id,))
                    conn.commit()
                    
                    # Serve from cloud if available
                    if cloud_url:
                        return RedirectResponse(url=cloud_url)
                    
                    # Serve from local file
                    if local_path and os.path.exists(local_path):
                        return FileResponse(
                            local_path,
                            media_type=file_type,
                            filename=original_name
                        )
        
        raise HTTPException(status_code=404, detail="Media file not found")
        
    except Exception as e:
        print(f"ELLA Media serving error: {e}")
        raise HTTPException(status_code=500, detail="Error serving media")

# 📄 BOOKING CONFIRMATION PDF ENDPOINTS (ELLA'S ONLY WRITE ACCESS)

@app.get("/booking-confirmation/{booking_reference}")
async def serve_booking_confirmation(booking_reference: str):
    """Generate and serve booking confirmation PDF (ELLA's booking write access)"""
    try:
        # Get booking data from database
        from chat_assistant.chat_tools.booking_tools.booking_management import booking_manager
        booking_result = booking_manager.get_booking_status(booking_reference)
        
        if not booking_result['success']:
            raise HTTPException(status_code=404, detail="Booking not found")
        
        booking_data = booking_result
        
        # Generate temporary PDF
        try:
            from chat_assistant.chat_tools.booking_tools.pdf_generator import EllaPDFGenerator
            
            # Try to get existing local file first
            generator = EllaPDFGenerator()
            local_file = generator.get_local_file_path(booking_reference, "booking_confirmation")
            
            if local_file and os.path.exists(local_file):
                # Serve existing local file
                print(f"ELLA: Serving existing PDF: {local_file}")
                return FileResponse(
                    local_file,
                    media_type="application/pdf",
                    filename=f"Booking_Confirmation_{booking_reference}.pdf",
                    headers={
                        "Content-Disposition": f"inline; filename=Booking_Confirmation_{booking_reference}.pdf"
                    }
                )
            
            # Generate new temporary PDF if no local file exists
            from chat_assistant.chat_tools.booking_tools.pdf_generator import generate_temp_booking_pdf
            
            # Prepare data for PDF generation
            booking_pdf_data = {
                'booking_reference': booking_reference,
                'hotel_name': booking_data['hotel_name'],
                'room_name': booking_data['room_name'],
                'guest_name': booking_data['guest_name'],
                'guest_email': booking_data['guest_email'] or 'N/A',
                'guest_phone': booking_data['guest_phone'] or 'N/A',
                'check_in_date': booking_data['check_in_date'],
                'check_out_date': booking_data['check_out_date'],
                'nights': booking_data['nights'],
                'rooms_booked': booking_data['rooms_booked'],
                'total_price': booking_data['total_price'],
                'special_requests': booking_data['special_requests'],
                'hotel_location': booking_data['hotel_location'],
                'hotel_address': booking_data['hotel_address'],
                'hotel_phone': booking_data['hotel_phone'],
                'currency': booking_data.get('currency', 'RM')
            }
            
            # Generate temporary PDF
            temp_pdf_path = generate_temp_booking_pdf(booking_pdf_data)
            print(f"ELLA: Generated PDF for {booking_reference}: {temp_pdf_path}")
            
            # Create a custom response that deletes the file after serving
            def cleanup_after_response():
                try:
                    if os.path.exists(temp_pdf_path):
                        os.unlink(temp_pdf_path)
                        print(f"ELLA: Cleaned up PDF after serving: {temp_pdf_path}")
                except Exception as e:
                    print(f"ELLA: Failed to cleanup PDF: {e}")
            
            # Return PDF with cleanup
            import asyncio
            from fastapi import BackgroundTasks
            
            # Schedule cleanup after response
            background_tasks = BackgroundTasks()
            background_tasks.add_task(cleanup_after_response)
            
            return FileResponse(
                temp_pdf_path,
                media_type="application/pdf",
                filename=f"Booking_Confirmation_{booking_reference}.pdf",
                headers={
                    "Content-Disposition": f"inline; filename=Booking_Confirmation_{booking_reference}.pdf"
                },
                background=background_tasks
            )
            
        except ImportError:
            raise HTTPException(status_code=503, detail="PDF generation not available")
        except Exception as pdf_error:
            print(f"ELLA PDF generation error: {pdf_error}")
            raise HTTPException(status_code=500, detail="Error generating PDF")
        
    except Exception as e:
        print(f"ELLA PDF serving error: {e}")
        raise HTTPException(status_code=500, detail="Error serving booking confirmation")

@app.get("/invoice/{booking_reference}")
async def serve_invoice(booking_reference: str):
    """Generate and serve invoice PDF"""
    try:
        from chat_assistant.chat_tools.booking_tools.booking_management import booking_manager
        from chat_assistant.chat_tools.booking_tools.pdf_generator import EllaPDFGenerator
        
        booking_result = booking_manager.get_booking_status(booking_reference)
        if not booking_result['success']:
            raise HTTPException(status_code=404, detail="Booking not found")
        
        # Try to get existing local file first
        generator = EllaPDFGenerator()
        local_file = generator.get_local_file_path(booking_reference, "invoice")
        
        if local_file and os.path.exists(local_file):
            return FileResponse(
                local_file,
                media_type="application/pdf",
                filename=f"Invoice_{booking_reference}.pdf",
                headers={"Content-Disposition": f"inline; filename=Invoice_{booking_reference}.pdf"}
            )
        
        # Generate new invoice if no local file exists
        pdf_path = generator.generate_invoice(booking_result)
        
        return FileResponse(
            pdf_path,
            media_type="application/pdf",
            filename=f"Invoice_{booking_reference}.pdf",
            headers={"Content-Disposition": f"inline; filename=Invoice_{booking_reference}.pdf"}
        )
        
    except Exception as e:
        print(f"ELLA Invoice serving error: {e}")
        raise HTTPException(status_code=500, detail="Error serving invoice")

@app.get("/payment-receipt/{booking_reference}")
async def serve_payment_receipt(booking_reference: str):
    """Generate and serve payment receipt PDF"""
    try:
        from chat_assistant.chat_tools.booking_tools.booking_management import booking_manager
        from chat_assistant.chat_tools.booking_tools.pdf_generator import EllaPDFGenerator
        
        booking_result = booking_manager.get_booking_status(booking_reference)
        if not booking_result['success']:
            raise HTTPException(status_code=404, detail="Booking not found")
        
        # Try to get existing local file first
        generator = EllaPDFGenerator()
        local_file = generator.get_local_file_path(booking_reference, "payment_receipt")
        
        if local_file and os.path.exists(local_file):
            return FileResponse(
                local_file,
                media_type="application/pdf",
                filename=f"Receipt_{booking_reference}.pdf",
                headers={"Content-Disposition": f"inline; filename=Receipt_{booking_reference}.pdf"}
            )
        
        # Generate new receipt with default payment data
        payment_data = {
            **booking_result,
            'transaction_id': f"TXN-{booking_reference}-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            'amount_paid': booking_result['total_price'],
            'payment_method': 'Credit Card',
            'payment_date': datetime.now().strftime('%d %B %Y'),
            'payment_status': 'COMPLETED'
        }
        
        pdf_path = generator.generate_payment_receipt(payment_data)
        
        return FileResponse(
            pdf_path,
            media_type="application/pdf",
            filename=f"Receipt_{booking_reference}.pdf",
            headers={"Content-Disposition": f"inline; filename=Receipt_{booking_reference}.pdf"}
        )
        
    except Exception as e:
        print(f"ELLA Receipt serving error: {e}")
        raise HTTPException(status_code=500, detail="Error serving payment receipt")

@app.get("/cancellation/{booking_reference}")
async def serve_cancellation_confirmation(booking_reference: str):
    """Generate and serve cancellation confirmation PDF"""
    try:
        from chat_assistant.chat_tools.booking_tools.booking_management import booking_manager
        from chat_assistant.chat_tools.booking_tools.pdf_generator import EllaPDFGenerator
        
        booking_result = booking_manager.get_booking_status(booking_reference)
        if not booking_result['success']:
            raise HTTPException(status_code=404, detail="Booking not found")
        
        # Try to get existing local file first
        generator = EllaPDFGenerator()
        local_file = generator.get_local_file_path(booking_reference, "cancellation_confirmation")
        
        if local_file and os.path.exists(local_file):
            return FileResponse(
                local_file,
                media_type="application/pdf",
                filename=f"Cancellation_{booking_reference}.pdf",
                headers={"Content-Disposition": f"inline; filename=Cancellation_{booking_reference}.pdf"}
            )
        
        # Generate new cancellation confirmation with default data
        cancellation_data = {
            **booking_result,
            'cancellation_reason': 'Guest request',
            'cancelled_by': 'Guest',
            'refund_amount': booking_result['total_price'],
            'refund_status': 'PROCESSING',
            'refund_method': 'Original payment method'
        }
        
        pdf_path = generator.generate_cancellation_confirmation(cancellation_data)
        
        return FileResponse(
            pdf_path,
            media_type="application/pdf",
            filename=f"Cancellation_{booking_reference}.pdf",
            headers={"Content-Disposition": f"inline; filename=Cancellation_{booking_reference}.pdf"}
        )
        
    except Exception as e:
        print(f"ELLA Cancellation serving error: {e}")
        raise HTTPException(status_code=500, detail="Error serving cancellation confirmation")

@app.get("/api/booking/{booking_reference}/pdf")
async def get_booking_pdf_info(booking_reference: str):
    """Get information about booking confirmation PDF availability"""
    try:
        # Check if booking exists
        from chat_assistant.chat_tools.booking_tools.booking_management import booking_manager
        booking_result = booking_manager.get_booking_status(booking_reference)
        
        if booking_result['success']:
            # Check if PDF generation is available
            try:
                from chat_assistant.chat_tools.booking_tools.pdf_generator import generate_temp_booking_pdf
                pdf_available = True
            except ImportError:
                pdf_available = False
            
            return {
                "booking_exists": True,
                "booking_reference": booking_reference,
                "pdf_available": pdf_available,
                "download_url": f"/booking-confirmation/{booking_reference}" if pdf_available else None,
                "booking_status": booking_result['booking_status'],
                "hotel_name": booking_result['hotel_name'],
                "guest_name": booking_result['guest_name'],
                "message": "PDF will be generated on-demand when downloaded" if pdf_available else "PDF generation not available"
            }
        else:
            return {
                "booking_exists": False,
                "booking_reference": booking_reference,
                "message": "Booking not found"
            }
            
    except Exception as e:
        print(f"ELLA PDF info error: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving PDF information")

# 📸 READ-ONLY MEDIA API FOR GUESTS

@app.get("/api/photos/hotel/{hotel_name}")
async def get_hotel_photos_api(hotel_name: str, category: Optional[str] = None):
    """API endpoint to get hotel photos (READ-ONLY for guests)"""
    try:
        if not MEDIA_TOOLS_AVAILABLE:
            return {"error": "Media tools not available", "photos": []}
        
        result = search_hotel_media(hotel_name, category or "")
        return {"photos": result}
        
    except Exception as e:
        print(f"ELLA Hotel photos API error: {e}")
        return {"error": str(e), "photos": []}

@app.get("/api/photos/room/{hotel_name}/{room_type}")
async def get_room_photos_api(hotel_name: str, room_type: str):
    """API endpoint to get room photos (READ-ONLY for guests)"""
    try:
        if not MEDIA_TOOLS_AVAILABLE:
            return {"error": "Media tools not available", "photos": []}
        
        result = search_hotel_media(hotel_name, f"{room_type} room photos", "room_interior", "", False, 5)
        return {"photos": result}
        
    except Exception as e:
        print(f"ELLA Room photos API error: {e}")
        return {"error": str(e), "photos": []}

# 🚫 REMOVED: Media upload endpoint - Now exclusive to LEON
# @app.post("/api/media/upload") - MOVED TO LEON

@app.get("/api/stats")
async def get_ella_stats():
    """Get system statistics"""
    try:
        import sqlite3
        with sqlite3.connect("ella.db") as conn:
            cursor = conn.cursor()
            
            # Count of various entities
            stats = {
                "hotels": cursor.execute("SELECT COUNT(*) FROM hotels").fetchone()[0],
                "bookings": cursor.execute("SELECT COUNT(*) FROM bookings").fetchone()[0],
                "room_types": cursor.execute("SELECT COUNT(*) FROM room_types").fetchone()[0],
                "service": "ella_guest_assistant",
                "access_level": "READ_ONLY"
            }
            
            return stats
            
    except Exception as e:
        print(f"ELLA Stats error: {e}")
        return {
            "error": "Could not fetch stats",
            "service": "ella_guest_assistant"
        }

# ==========================================
# DASHBOARD API ENDPOINTS
# Consolidated from dashboard_api.py for unified backend
# ==========================================

@app.get("/api/dashboard/hotels")
async def get_dashboard_hotels():
    """Get all hotels for dashboard"""
    try:
        import sqlite3
        with sqlite3.connect("ella.db") as conn:
            cursor = conn.cursor()
            
            hotels = cursor.execute("""
                SELECT property_id, hotel_name, location, star_rating, description
                FROM hotels
                ORDER BY hotel_name
            """).fetchall()
            
            hotels_list = []
            for hotel in hotels:
                hotels_list.append({
                    "property_id": hotel[0],
                    "hotel_name": hotel[1],
                    "location": hotel[2],
                    "star_rating": hotel[3],
                    "description": hotel[4]
                })
            
            return {
                "success": True,
                "hotels": hotels_list
            }
    except Exception as e:
        print(f"Dashboard hotels error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/dashboard/hotels/{property_id}")
async def get_dashboard_hotel_details(property_id: str):
    """Get detailed hotel info with room types and analytics"""
    try:
        import sqlite3
        from datetime import datetime, timedelta
        
        with sqlite3.connect("ella.db") as conn:
            cursor = conn.cursor()
            
            # Get hotel details
            hotel = cursor.execute("""
                SELECT * FROM hotels WHERE property_id = ?
            """, (property_id,)).fetchone()
            
            if not hotel:
                raise HTTPException(status_code=404, detail="Hotel not found")
            
            # Get room types
            room_types = cursor.execute("""
                SELECT * FROM room_types WHERE property_id = ?
                ORDER BY room_name
            """, (property_id,)).fetchall()
            
            # Calculate analytics
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)
            
            bookings = cursor.execute("""
                SELECT COUNT(*), SUM(CAST(total_amount AS REAL))
                FROM bookings 
                WHERE property_id = ? AND created_at >= ?
            """, (property_id, start_date.isoformat())).fetchone()
            
            # Get total rooms for occupancy calculation
            total_rooms = cursor.execute("""
                SELECT SUM(CAST(total_rooms AS INTEGER)) FROM room_types WHERE property_id = ?
            """, (property_id,)).fetchone()[0] or 0
            
            # Get current occupancy (simplified calculation)
            occupied_rooms = cursor.execute("""
                SELECT COUNT(*) FROM rooms 
                WHERE property_id = ? AND room_status = 'OCCUPIED'
            """, (property_id,)).fetchone()[0] or 0
            
            occupancy_rate = (occupied_rooms / total_rooms) if total_rooms > 0 else 0
            
            # Get recent bookings
            recent_bookings = cursor.execute("""
                SELECT b.*, rt.room_name
                FROM bookings b
                LEFT JOIN room_types rt ON b.room_type_id = rt.room_type_id
                WHERE b.property_id = ?
                ORDER BY b.created_at DESC
                LIMIT 10
            """, (property_id,)).fetchall()
            
            # Format response
            hotel_data = {
                "property_id": hotel[0],
                "hotel_name": hotel[1],
                "location": hotel[2],
                "star_rating": hotel[3],
                "description": hotel[4]
            }
            
            room_types_data = []
            for rt in room_types:
                room_types_data.append({
                    "room_type_id": rt[0],
                    "property_id": rt[1],
                    "room_name": rt[2],
                    "bed_type": rt[3],
                    "max_occupancy": rt[4],
                    "base_price_per_night": rt[5],
                    "room_size_sqm": rt[6],
                    "view_type": rt[7],
                    "total_rooms": rt[8]
                })
            
            recent_bookings_data = []
            for booking in recent_bookings:
                recent_bookings_data.append({
                    "booking_id": booking[0],
                    "booking_reference": booking[1],
                    "guest_name": booking[2],
                    "check_in_date": booking[4],
                    "check_out_date": booking[5],
                    "booking_status": booking[7],
                    "total_amount": booking[8],
                    "room_name": booking[-1]
                })
            
            analytics_data = {
                "bookings": {
                    "total": bookings[0] or 0
                },
                "revenue": {
                    "total": bookings[1] or 0,
                    "average_per_booking": (bookings[1] / bookings[0]) if bookings[0] and bookings[1] else 0
                },
                "occupancy": {
                    "rate": occupancy_rate,
                    "occupied_rooms": occupied_rooms,
                    "total_rooms": total_rooms
                }
            }
            
            return {
                "success": True,
                "hotel": hotel_data,
                "room_types": room_types_data,
                "analytics": analytics_data,
                "recent_bookings": recent_bookings_data
            }
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"Dashboard hotel details error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/dashboard/hotels/{property_id}/rooms")
async def get_dashboard_hotel_rooms(property_id: str, room_status: str = None):
    """Get all rooms for a hotel with optional status filter"""
    try:
        import sqlite3
        
        with sqlite3.connect("ella.db") as conn:
            cursor = conn.cursor()
            
            hotel = cursor.execute("""
                SELECT hotel_name FROM hotels WHERE property_id = ?
            """, (property_id,)).fetchone()
            
            if not hotel:
                raise HTTPException(status_code=404, detail="Hotel not found")
            
            # Build query with optional status filter
            query = """
                SELECT r.*, rt.room_name, rt.bed_type, rt.max_occupancy, rt.room_size_sqm,
                       ra.guest_name, ra.check_in_date, ra.check_out_date, ra.assignment_status,
                       ra.checked_in_at, b.booking_id, b.booking_status
                FROM rooms r
                LEFT JOIN room_types rt ON r.room_type_id = rt.room_type_id
                LEFT JOIN room_assignments ra ON r.room_id = ra.room_id 
                    AND ra.assignment_status IN ('ASSIGNED', 'CHECKED_IN')
                    AND ra.check_in_date <= date('now') 
                    AND ra.check_out_date > date('now')
                LEFT JOIN bookings b ON ra.booking_id = b.booking_id
                WHERE r.property_id = ?
            """
            params = [property_id]
            
            if room_status:
                query += " AND r.room_status = ?"
                params.append(room_status)
                
            query += " ORDER BY r.floor, r.room_number"
            
            rooms = cursor.execute(query, params).fetchall()
            
            # Organize rooms by floor for better display
            rooms_by_floor = {}
            rooms_list = []
            
            for room in rooms:
                room_data = {
                    "room_id": room[0],
                    "property_id": room[1],
                    "room_type_id": room[2],
                    "room_number": room[3],
                    "floor": room[4],
                    "room_status": room[5],
                    "is_active": room[6],
                    "maintenance_notes": room[7],
                    "last_cleaned": room[8],
                    "room_name": room[11],
                    "bed_type": room[12],
                    "max_occupancy": room[13],
                    "room_size_sqm": room[14],
                    "guest_name": room[15],
                    "check_in_date": room[16],
                    "check_out_date": room[17],
                    "assignment_status": room[18],
                    "checked_in_at": room[19],
                    "booking_id": room[20],
                    "booking_status": room[21]
                }
                rooms_list.append(room_data)
                
                # Group by floor
                floor = str(room[4])
                if floor not in rooms_by_floor:
                    rooms_by_floor[floor] = []
                rooms_by_floor[floor].append(room_data)
            
            return {
                "success": True,
                "rooms": rooms_list,
                "rooms_by_floor": rooms_by_floor,
                "total_rooms": len(rooms_list)
            }
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"Dashboard rooms error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/dashboard/hotels/{property_id}/pending-checkins")
async def get_pending_checkins(property_id: str, date: str = None):
    """Get bookings that need room assignment or check-in"""
    try:
        import sqlite3
        from datetime import datetime
        
        if not date:
            date = datetime.now().strftime('%Y-%m-%d')
        
        with sqlite3.connect("ella.db") as conn:
            cursor = conn.cursor()
            
            # Get bookings for today that need attention
            query = """
                SELECT DISTINCT b.*, rt.room_name, ra.room_id, r.room_number, ra.checked_in_at
                FROM bookings b
                LEFT JOIN room_types rt ON b.room_type_id = rt.room_type_id
                LEFT JOIN room_assignments ra ON b.booking_id = ra.booking_id
                LEFT JOIN rooms r ON ra.room_id = r.room_id
                WHERE b.property_id = ? 
                AND b.booking_status = 'CONFIRMED'
                AND b.check_in_date <= ?
                AND b.check_out_date > ?
                ORDER BY b.check_in_date, b.guest_name
            """
            
            pending_checkins = cursor.execute(query, (property_id, date, date)).fetchall()
            
            checkins_list = []
            for checkin in pending_checkins:
                checkins_list.append({
                    "booking_id": checkin[0],
                    "booking_reference": checkin[1],
                    "guest_name": checkin[2],
                    "room_type_id": checkin[3],
                    "check_in_date": checkin[4],
                    "check_out_date": checkin[5],
                    "num_adults": checkin[6],
                    "booking_status": checkin[7],
                    "total_amount": checkin[8],
                    "room_name": checkin[10],
                    "room_id": checkin[11],
                    "room_number": checkin[12],
                    "checked_in_at": checkin[13]
                })
            
            return {
                "success": True,
                "pending_checkins": checkins_list,
                "date": date,
                "count": len(checkins_list)
            }
            
    except Exception as e:
        print(f"Dashboard pending checkins error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/dashboard/hotels/{property_id}/assign-room")
async def assign_room_to_booking(property_id: str, assignment_data: dict):
    """Assign a specific room to a booking"""
    try:
        import sqlite3
        
        booking_id = assignment_data.get('booking_id')
        room_id = assignment_data.get('room_id')
        
        if not booking_id or not room_id:
            raise HTTPException(status_code=400, detail="booking_id and room_id are required")
        
        with sqlite3.connect("ella.db") as conn:
            cursor = conn.cursor()
            
            # Verify booking exists
            booking = cursor.execute("""
                SELECT * FROM bookings WHERE booking_id = ? AND property_id = ?
            """, (booking_id, property_id)).fetchone()
            
            if not booking:
                raise HTTPException(status_code=404, detail="Booking not found")
            
            # Verify room exists and is available
            room = cursor.execute("""
                SELECT * FROM rooms WHERE room_id = ? AND property_id = ?
            """, (room_id, property_id)).fetchone()
            
            if not room:
                raise HTTPException(status_code=404, detail="Room not found")
            
            # Check if room is already assigned for these dates
            existing_assignment = cursor.execute("""
                SELECT * FROM room_assignments 
                WHERE room_id = ? 
                AND assignment_status IN ('ASSIGNED', 'CHECKED_IN')
                AND ((check_in_date <= ? AND check_out_date > ?) 
                     OR (check_in_date < ? AND check_out_date >= ?))
            """, (room_id, booking[4], booking[4], booking[5], booking[5])).fetchone()
            
            if existing_assignment:
                raise HTTPException(status_code=400, detail="Room is already assigned for these dates")
            
            # Create room assignment
            cursor.execute("""
                INSERT INTO room_assignments 
                (booking_id, room_id, property_id, guest_name, check_in_date, check_out_date)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (booking_id, room_id, property_id, booking[2], booking[4], booking[5]))
            
            # Update room status to reserved
            cursor.execute("""
                UPDATE rooms SET room_status = 'RESERVED' WHERE room_id = ?
            """, (room_id,))
            
            conn.commit()
            
            return {"success": True, "message": "Room assigned successfully"}
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"Dashboard assign room error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/dashboard/hotels/{property_id}/check-in")
async def check_in_guest_to_room(property_id: str, checkin_data: dict):
    """Check in a guest to their assigned room"""
    try:
        import sqlite3
        
        booking_id = checkin_data.get('booking_id')
        
        if not booking_id:
            raise HTTPException(status_code=400, detail="booking_id is required")
        
        with sqlite3.connect("ella.db") as conn:
            cursor = conn.cursor()
            
            # Get the room assignment
            assignment = cursor.execute("""
                SELECT ra.*, b.guest_name, r.room_number
                FROM room_assignments ra
                JOIN bookings b ON ra.booking_id = b.booking_id
                JOIN rooms r ON ra.room_id = r.room_id
                WHERE ra.booking_id = ? AND ra.property_id = ?
                AND ra.assignment_status = 'ASSIGNED'
            """, (booking_id, property_id)).fetchone()
            
            if not assignment:
                raise HTTPException(status_code=404, detail="Room assignment not found")
            
            # Update assignment as checked in
            cursor.execute("""
                UPDATE room_assignments 
                SET assignment_status = 'CHECKED_IN', checked_in_at = CURRENT_TIMESTAMP
                WHERE booking_id = ? AND property_id = ?
            """, (booking_id, property_id))
            
            # Update room status to occupied
            cursor.execute("""
                UPDATE rooms 
                SET room_status = 'OCCUPIED'
                WHERE room_id = ?
            """, (assignment[2]))  # room_id
            
            # Update booking status
            cursor.execute("""
                UPDATE bookings 
                SET booking_status = 'CHECKED_IN'
                WHERE booking_id = ?
            """, (booking_id,))
            
            conn.commit()
            
            return {
                "success": True, 
                "message": f"Guest {assignment[4]} checked in to room {assignment[-1]}"
            }
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"Dashboard check-in error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/dashboard/hotels/{property_id}/analytics")
async def get_dashboard_analytics(property_id: str, days: int = 30):
    """Get analytics data for dashboard"""
    try:
        import sqlite3
        from datetime import datetime, timedelta
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        with sqlite3.connect("ella.db") as conn:
            cursor = conn.cursor()
            
            # Bookings analytics
            bookings_data = cursor.execute("""
                SELECT COUNT(*), SUM(CAST(total_amount AS REAL))
                FROM bookings 
                WHERE property_id = ? AND created_at >= ?
            """, (property_id, start_date.isoformat())).fetchone()
            
            # Room occupancy
            total_rooms = cursor.execute("""
                SELECT SUM(CAST(total_rooms AS INTEGER)) FROM room_types WHERE property_id = ?
            """, (property_id,)).fetchone()[0] or 0
            
            occupied_rooms = cursor.execute("""
                SELECT COUNT(*) FROM rooms 
                WHERE property_id = ? AND room_status = 'OCCUPIED'
            """, (property_id,)).fetchone()[0] or 0
            
            occupancy_rate = (occupied_rooms / total_rooms) if total_rooms > 0 else 0
            
            analytics = {
                "bookings": {
                    "total": bookings_data[0] or 0,
                    "period_days": days
                },
                "revenue": {
                    "total": bookings_data[1] or 0,
                    "average_per_booking": (bookings_data[1] / bookings_data[0]) if bookings_data[0] and bookings_data[1] else 0,
                    "period_days": days
                },
                "occupancy": {
                    "rate": occupancy_rate,
                    "occupied_rooms": occupied_rooms,
                    "total_rooms": total_rooms
                }
            }
            
            return {
                "success": True,
                "analytics": analytics,
                "property_id": property_id,
                "period": f"{days} days"
            }
            
    except Exception as e:
        print(f"Dashboard analytics error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/dashboard/hotels/{property_id}/inventory-calendar")
async def get_inventory_calendar(property_id: str, start_date: str, days: int = 30):
    """Get inventory calendar data"""
    try:
        import sqlite3
        from datetime import datetime, timedelta
        
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        dates = [(start_dt + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(days)]
        
        with sqlite3.connect("ella.db") as conn:
            cursor = conn.cursor()
            
            # Get room types
            room_types = cursor.execute("""
                SELECT * FROM room_types WHERE property_id = ?
                ORDER BY room_name
            """, (property_id,)).fetchall()
            
            room_types_data = []
            for rt in room_types:
                room_types_data.append({
                    "room_type_id": rt[0],
                    "room_name": rt[2],
                    "bed_type": rt[3],
                    "total_rooms": rt[8],
                    "base_price_per_night": rt[5]
                })
            
            # For now, return simplified inventory data
            # In a real system, this would include availability and pricing per date
            inventory_data = {}
            for room_type in room_types_data:
                inventory_data[room_type["room_type_id"]] = {}
                for date in dates:
                    inventory_data[room_type["room_type_id"]][date] = {
                        "available_rooms": room_type["total_rooms"],
                        "current_price": room_type["base_price_per_night"]
                    }
            
            return {
                "success": True,
                "room_types": room_types_data,
                "inventory_data": inventory_data,
                "dates": dates,
                "days": days,
                "start_date": start_date
            }
            
    except Exception as e:
        print(f"Dashboard inventory calendar error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/dashboard/hotels/{property_id}/bookings-calendar")
async def get_bookings_calendar(property_id: str, start_date: str, days: int = 30):
    """Get bookings calendar data"""
    try:
        import sqlite3
        from datetime import datetime, timedelta
        
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        dates = [(start_dt + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(days)]
        
        with sqlite3.connect("ella.db") as conn:
            cursor = conn.cursor()
            
            # Get room types
            room_types = cursor.execute("""
                SELECT * FROM room_types WHERE property_id = ?
                ORDER BY room_name
            """, (property_id,)).fetchall()
            
            room_types_data = []
            for rt in room_types:
                room_types_data.append({
                    "room_type_id": rt[0],
                    "room_name": rt[2],
                    "bed_type": rt[3],
                    "total_rooms": rt[8],
                    "base_price_per_night": rt[5]
                })
            
            # Get bookings for date range
            end_date = (start_dt + timedelta(days=days)).strftime('%Y-%m-%d')
            bookings = cursor.execute("""
                SELECT b.*, rt.room_name
                FROM bookings b
                JOIN room_types rt ON b.room_type_id = rt.room_type_id
                WHERE b.property_id = ?
                AND ((b.check_in_date <= ? AND b.check_out_date > ?)
                     OR (b.check_in_date < ? AND b.check_out_date >= ?))
                ORDER BY b.check_in_date
            """, (property_id, end_date, start_date, end_date, start_date)).fetchall()
            
            # Organize bookings by room type and date
            bookings_by_room_and_date = {}
            for booking in bookings:
                room_name = booking[-1]
                if room_name not in bookings_by_room_and_date:
                    bookings_by_room_and_date[room_name] = {}
                
                # Add booking to all dates it covers
                booking_start = datetime.strptime(booking[4], '%Y-%m-%d')
                booking_end = datetime.strptime(booking[5], '%Y-%m-%d')
                
                for date in dates:
                    date_dt = datetime.strptime(date, '%Y-%m-%d')
                    if booking_start <= date_dt < booking_end:
                        if date not in bookings_by_room_and_date[room_name]:
                            bookings_by_room_and_date[room_name][date] = []
                        
                        bookings_by_room_and_date[room_name][date].append({
                            "booking_id": booking[0],
                            "booking_reference": booking[1],
                            "guest_name": booking[2],
                            "check_in_date": booking[4],
                            "check_out_date": booking[5],
                            "num_adults": booking[6],
                            "booking_status": booking[7],
                            "total_amount": booking[8]
                        })
            
            return {
                "success": True,
                "room_types": room_types_data,
                "bookings_by_room_and_date": bookings_by_room_and_date,
                "dates": dates,
                "days": days,
                "start_date": start_date
            }
            
    except Exception as e:
        print(f"Dashboard bookings calendar error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    import os
    
    # Use Azure's PORT environment variable, fallback to 8001 for local
    port = int(os.getenv("PORT", 8001))
    
    print("Starting ELLA Unified PMS API Server...")
    print("Unified backend for both guest chat and dashboard interfaces")
    print("Guest chat: READ-ONLY search and booking system")
    print("Dashboard: Full PMS management capabilities")
    print(f"Guest interface: http://localhost:{port}")
    print(f"Dashboard interface: http://localhost:{port}/static/leon_dashboard.html")
    uvicorn.run(app, host="0.0.0.0", port=port) 