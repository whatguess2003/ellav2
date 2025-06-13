#!/usr/bin/env python3
"""
Ella Hotel Assistant - Configuration Settings
All API keys, database paths, and system configurations
"""

import os

# Database Configuration
DATABASE_PATH = os.getenv("DATABASE_PATH", "ella_hotel_assistant.db")

# OpenAI Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# AWS Configuration
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "")
AWS_REGION = os.getenv("AWS_REGION", "ap-southeast-1")
AWS_BUCKET_NAME = os.getenv("AWS_BUCKET_NAME", "ella-hotel-media")

# WhatsApp Business API Configuration
WHATSAPP_ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
WHATSAPP_BUSINESS_ACCOUNT_ID = os.getenv("WHATSAPP_BUSINESS_ACCOUNT_ID", "")
WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "ella_verify_token_2024")
WHATSAPP_API_VERSION = os.getenv("WHATSAPP_API_VERSION", "v22.0")

# Multi-Agent System Configuration
MAX_AGENT_ITERATIONS = 8
MAX_RESPONSE_TOKENS = 800

# File Paths
MEDIA_STORAGE_PATH = "media_storage"
TEMP_DOWNLOAD_PATH = "temp_downloads"

# System Configuration
DEBUG_MODE = True
LOG_LEVEL = "INFO"

# Hotel Search Configuration
DEFAULT_SEARCH_RADIUS = 50  # km
MAX_SEARCH_RESULTS = 10

# Booking Configuration
BOOKING_TIMEOUT_MINUTES = 15
PAYMENT_WINDOW_MINUTES = 30

# Media Configuration
MAX_MEDIA_SIZE_MB = 100
SUPPORTED_IMAGE_FORMATS = [".jpg", ".jpeg", ".png"]
SUPPORTED_VIDEO_FORMATS = [".mp4", ".mov"]
SUPPORTED_DOCUMENT_FORMATS = [".pdf", ".doc", ".docx"]

# Rate Limiting
MAX_REQUESTS_PER_MINUTE = 60
MAX_MEDIA_UPLOADS_PER_DAY = 100

# Security
SESSION_TIMEOUT_MINUTES = 60
MAX_FAILED_ATTEMPTS = 5

print("⚙️ Settings loaded successfully")
print(f"📱 WhatsApp Phone Number ID: {WHATSAPP_PHONE_NUMBER_ID}")
print(f"🔑 WhatsApp API: {'✅ Configured' if WHATSAPP_ACCESS_TOKEN else '❌ Not configured'}")
print(f"🤖 OpenAI API: {'✅ Configured' if OPENAI_API_KEY else '❌ Not configured'}")
print(f"☁️ AWS S3 Bucket: {AWS_BUCKET_NAME}") 