import os

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB", "ella_db")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "UcqZLa941Kkt8ZhEEybf")
# Replace with your key 

# ========== FINE-TUNED MODEL CONFIGURATION ==========
# Replace with your fine-tuned model ID when available
# Format: "gpt-4o-mini-2024-07-18:ft-[org]:ella-hotel-assistant-v1:[id]"
ELLA_FINETUNED_MODEL = os.getenv("ELLA_FINETUNED_MODEL", "ft:gpt-4o-mini-2024-07-18:inapsolutions:ella-demo-v1:BexmNtfD")

# When you complete fine-tuning, update to something like:
# ELLA_FINETUNED_MODEL = "gpt-4o-mini-2024-07-18:ft-your-org:ella-hotel-assistant-v1:abc123def"

# Model configuration for different use cases
MODEL_CONFIG = {
    # Main voice assistant model (using plain gpt-4o-mini)
    "voice_assistant": "gpt-4o",
    
    # Chat assistant model (using plain gpt-4o-mini)
    "chat_assistant": "gpt-4o-mini",
    
    # Function execution model (using plain gpt-4o-mini)
    "function_execution": "gpt-4o",
    
    # Prediction model (using plain gpt-4o-mini)
    "prediction": "gpt-4o",
    
    # Ultra-fast responses (using plain gpt-4o-mini)
    "ultra_fast": "gpt-4o"
}
