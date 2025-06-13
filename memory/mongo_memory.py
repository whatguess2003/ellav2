from pymongo import MongoClient
import os
from datetime import datetime

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB", "ella_db")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

mongo_client = MongoClient(MONGO_URI)
db = mongo_client[MONGO_DB]

def store_sticky_context(guest_id, context):
    db.sticky.update_one({"guest_id": guest_id}, {"$set": context}, upsert=True)

def get_sticky_context(guest_id):
    return db.sticky.find_one({"guest_id": guest_id}) or {}

def log_intent(thread_id, intent_type):
    thread = db.threads.find_one({"thread_id": thread_id})
    if thread and "intents" in thread:
        next_number = len(thread["intents"]) + 1
    else:
        next_number = 1
    intent_id = f"{thread_id}_intent_{intent_type}_{next_number}"
    db.threads.update_one(
        {"thread_id": thread_id},
        {"$push": {"intents": {
            "intent_id": intent_id,
            "type": intent_type,
            "timestamp": datetime.utcnow().isoformat()
        }}},
        upsert=True
    )
    return intent_id

def update_biography(guest_id, bio_fields):
    db.guests.update_one(
        {"guest_id": guest_id},
        {"$set": {f"biography.{k}": v for k, v in bio_fields.items()}},
        upsert=True
    )

def update_slot_history(db, guest_id, slot, value):
    """Append a new value with timestamp to the slot history for a guest."""
    bio = db.guests.find_one({"guest_id": guest_id}, {"biography": 1}) or {}
    history = bio.get("biography", {}).get(slot, [])
    if not any(entry["value"] == value for entry in history):
        history.append({"value": value, "timestamp": datetime.datetime.utcnow().isoformat()})
        db.guests.update_one(
            {"guest_id": guest_id},
            {"$set": {f"biography.{slot}": history}},
            upsert=True
        )


def get_latest_biography(db, guest_id):
    """Return a dict of the latest value for each slot for a guest."""
    bio = db.guests.find_one({"guest_id": guest_id}, {"biography": 1}) or {}
    biography = bio.get("biography", {})
    latest = {}
    for slot, history in biography.items():
        if isinstance(history, list) and history:
            latest[slot] = history[-1]["value"]
        elif isinstance(history, dict) and "value" in history:
            latest[slot] = history["value"]
        else:
            latest[slot] = history
    return latest


def get_slot_history(db, guest_id, slot):
    """Return the full history list for a slot for a guest."""
    bio = db.guests.find_one({"guest_id": guest_id}, {"biography": 1}) or {}
    return bio.get("biography", {}).get(slot, []) 

def get_latest_thread_id_for_guest(guest_id):
    """Return the latest thread_id for a guest, or None if not found."""
    # thread_id format: {guest_id}_thread_{timestamp}
    doc = db.threads.find_one(
        {"thread_id": {"$regex": f"^{guest_id}_thread_"}},
        sort=[("thread_id", -1)]
    )
    return doc["thread_id"] if doc and "thread_id" in doc else None

# === PERSISTENT GUEST PROFILE SYSTEM ===

def store_persistent_preference(guest_id, preference_type, value, confidence_score=1.0):
    """
    Store critical preferences that should NEVER be forgotten.
    
    Args:
        guest_id: Guest identifier
        preference_type: Type of preference (smoking, accessibility, dietary, etc.)
        value: The preference value
        confidence_score: How confident we are about this preference (0.0-1.0)
    """
    timestamp = datetime.utcnow().isoformat()
    
    # Update or create persistent preference
    db.persistent_profiles.update_one(
        {"guest_id": guest_id},
        {
            "$set": {
                f"critical_preferences.{preference_type}": {
                    "value": value,
                    "confidence": confidence_score,
                    "first_mentioned": timestamp,
                    "last_confirmed": timestamp,
                    "mention_count": 1
                },
                "last_updated": timestamp
            },
            "$setOnInsert": {
                "created_at": timestamp
            }
        },
        upsert=True
    )
    
    print(f"🔒 PERSISTENT PREFERENCE STORED: {guest_id} -> {preference_type}: {value}")

def update_persistent_preference(guest_id, preference_type, new_value=None, increment_mentions=True):
    """Update an existing persistent preference (e.g., when mentioned again)."""
    timestamp = datetime.utcnow().isoformat()
    
    update_ops = {
        "$set": {
            f"critical_preferences.{preference_type}.last_confirmed": timestamp,
            "last_updated": timestamp
        }
    }
    
    if new_value is not None:
        update_ops["$set"][f"critical_preferences.{preference_type}.value"] = new_value
    
    if increment_mentions:
        update_ops["$inc"] = {f"critical_preferences.{preference_type}.mention_count": 1}
    
    db.persistent_profiles.update_one(
        {"guest_id": guest_id},
        update_ops
    )

def get_persistent_profile(guest_id):
    """Get all persistent preferences for a guest."""
    profile = db.persistent_profiles.find_one({"guest_id": guest_id})
    if not profile:
        return {}
    
    return profile.get("critical_preferences", {})

def detect_critical_preferences(guest_message):
    """
    Use LLM to detect critical preferences that should be stored permanently.
    
    Returns:
        dict: Dictionary of detected critical preferences
    """
    from langchain_openai import ChatOpenAI
    import json
    
    # Only run detection if message might contain critical preferences
    message_lower = guest_message.lower()
    trigger_words = [
        'smoking', 'non-smoking', 'smoke', 'vape',
        'wheelchair', 'accessible', 'disability', 'mobility',
        'halal', 'kosher', 'vegetarian', 'vegan', 'allergic', 'allergy',
        'always need', 'never', 'must have', 'require', 'essential',
        'medical', 'condition', 'special needs'
    ]
    
    if not any(word in message_lower for word in trigger_words):
        return {}
    
    llm = ChatOpenAI(openai_api_key=OPENAI_API_KEY, model="gpt-4o", temperature=0.0)
    
    detection_prompt = f"""Analyze this guest message for CRITICAL PREFERENCES that should NEVER be forgotten: "{guest_message}"

Detect preferences in these categories and return ONLY a JSON object:

{{
  "smoking": "smoking" or "non-smoking" or null,
  "accessibility": "wheelchair accessible" or "hearing impaired" or "visual impaired" or null,
  "dietary": "halal" or "kosher" or "vegetarian" or "vegan" or null,
  "allergies": "specific allergy description" or null,
  "medical_needs": "description of medical requirements" or null,
  "room_requirements": "specific room needs that never change" or null
}}

RULES:
- Only extract PERMANENT preferences that guest would expect you to remember forever
- Ignore temporary requests like "tonight I want a quiet room"
- Return null for categories not mentioned
- Be conservative - only extract if very confident
- Return only the JSON object"""

    try:
        response = llm.invoke([{"role": "user", "content": detection_prompt}])
        response_content = response.content.strip()
        
        # Clean up response
        if response_content.startswith('```json'):
            response_content = response_content.replace('```json', '').replace('```', '').strip()
        elif response_content.startswith('```'):
            response_content = response_content.replace('```', '').strip()
        
        detected = json.loads(response_content)
        
        # Filter out null values
        critical_prefs = {k: v for k, v in detected.items() if v is not None}
        
        if critical_prefs:
            print(f"🎯 CRITICAL PREFERENCES DETECTED: {critical_prefs}")
        
        return critical_prefs
        
    except Exception as e:
        print(f"⚠️ CRITICAL PREFERENCE DETECTION FAILED: {e}")
        return {}

def process_guest_message_for_critical_preferences(guest_id, message):
    """
    Process a guest message to detect and store critical preferences.
    This should be called for every guest message.
    """
    detected_prefs = detect_critical_preferences(message)
    
    for pref_type, value in detected_prefs.items():
        # Check if we already have this preference
        existing_profile = get_persistent_profile(guest_id)
        
        if pref_type in existing_profile:
            # Update existing preference
            update_persistent_preference(guest_id, pref_type, value)
        else:
            # Store new critical preference
            store_persistent_preference(guest_id, pref_type, value, confidence_score=0.9)

def get_critical_preferences_for_search(guest_id):
    """
    Get critical preferences formatted for hotel search filters.
    
    Returns:
        dict: Filters that should ALWAYS be applied to hotel searches
    """
    profile = get_persistent_profile(guest_id)
    search_filters = {}
    
    if profile.get('smoking'):
        search_filters['smoking_policy'] = profile['smoking']['value']
    
    if profile.get('accessibility'):
        search_filters['accessibility_features'] = profile['accessibility']['value']
    
    if profile.get('dietary'):
        search_filters['dietary_options'] = profile['dietary']['value']
    
    # Add other critical filters as needed
    
    return search_filters 