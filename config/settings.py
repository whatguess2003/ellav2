import os

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB", "ella_db")
***REMOVED*** = "***REMOVED***proj-1ReH_PyPpVc_UFF6SCPyg7T59uvPv91uihlbGBqicVyDAaRTllYW4jnwuZ1O3XaW7h-nBRKrw5T3BlbkFJjlYtdw1YXtTDzdF3oANBE40ciUnHV90oVsEEwHKkQHzYlNUfjNhVv_8YHckZF5NlBbzgkMDY0A"
ELEVENLABS_API_KEY = "sk_9de7f5a914c9f2097c3977171d6f669be63f4106d46558f1"
ELEVENLABS_VOICE_ID = "UcqZLa941Kkt8ZhEEybf"
# Replace with your key 

# ========== FINE-TUNED MODEL CONFIGURATION ==========
# Replace with your fine-tuned model ID when available
# Format: "gpt-4o-mini-2024-07-18:ft-[org]:ella-hotel-assistant-v1:[id]"
ELLA_FINETUNED_MODEL = "ft:gpt-4o-mini-2024-07-18:inapsolutions:ella-demo-v1:BexmNtfD"

# When you complete fine-tuning, update to something like:
# ELLA_FINETUNED_MODEL = "gpt-4o-mini-2024-07-18:ft-your-org:ella-hotel-assistant-v1:abc123def"

# Model configuration for different use cases
MODEL_CONFIG = {
    # Main voice assistant model (using plain gpt-4o-mini)
    "voice_assistant": "gpt-4o-realtime-preview-2024-12-17",
    
    # Chat assistant model (using plain gpt-4o-mini)
    "chat_assistant": "gpt-4.1-mini",
    
    # Function execution model (using plain gpt-4o-mini)
    "function_execution": "gpt-4.1-nano",

}
