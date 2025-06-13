import redis
import os
import json
import time

# Railway automatically provides REDIS_URL when Redis service is added
REDIS_URL = os.getenv("REDIS_URL")
if not REDIS_URL:
    error_msg = """
    ❌ REDIS_URL environment variable not found.
    
    🔧 To fix this in Railway Dashboard:
    1. Go to Railway Dashboard → Your Project → Web Service
    2. Click "Variables" tab
    3. Add: REDIS_URL = ${{Redis.REDIS_URL}}
    
    📋 Make sure you have:
    - Added Redis service to your Railway project
    - Redis service is running and healthy
    - Web service can reference Redis service variables
    """
    print(error_msg)
    raise ValueError("REDIS_URL environment variable not found. Please add Redis service to Railway project.")

try:
    redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)
    # Test connection
    redis_client.ping()
    print(f"✅ Redis connected successfully via Railway")
except Exception as e:
    print(f"❌ Redis connection failed: {e}")
    print(f"🔧 Check Railway Redis service status and variables")
    raise

# ============================================================================
# BASIC STORAGE
# ============================================================================

def store_summary(guest_id, summary):
    redis_client.set(f"summary:{guest_id}", summary)

def get_summary(guest_id):
    return redis_client.get(f"summary:{guest_id}")

# ============================================================================
# DIALOG HISTORY
# ============================================================================

def append_dialog_turn(thread_id, role, content):
    """Append a dialog turn to Redis. Returns True if summarization should be triggered."""
    key = f"dialog:{thread_id}"
    print(f"[REDIS][append] thread_id={thread_id} key={key} role={role}")
    
    entry = json.dumps({"role": role, "content": content, "timestamp": time.time()})
    redis_client.rpush(key, entry)
    
    # Check if we're at the limit (before trimming)
    current_turns = redis_client.llen(key)
    should_summarize = current_turns >= 15
    
    # Keep only the last 15 turns
    redis_client.ltrim(key, -15, -1)
    
    return should_summarize

def get_all_dialog_turns(thread_id):
    """Get ALL dialog turns before trimming (for summarization)."""
    key = f"dialog:{thread_id}"
    entries = redis_client.lrange(key, 0, -1)
    return [json.loads(e) for e in entries]

def get_dialog_history(thread_id, limit=15):
    """Get recent dialog history from Redis using thread_id as the key."""
    key = f"dialog:{thread_id}"
    print(f"[REDIS][get] thread_id={thread_id} key={key} limit={limit}")
    entries = redis_client.lrange(key, -limit, -1)
    return [json.loads(e) for e in entries]

def get_full_context(guest_id):
    """Get both summary and recent dialog for complete context."""
    summary = get_summary(guest_id)
    thread_id = f"{guest_id}_chat_thread"
    recent_dialog = get_dialog_history(thread_id)
    
    context = {
        'summary': summary,
        'recent_turns': len(recent_dialog),
        'has_history': bool(summary or recent_dialog)
    }
    
    if summary:
        print(f"📚 CONTEXT: {guest_id} has summary + {len(recent_dialog)} recent turns")
    
    return context

# ============================================================================
# STREAMLINED SEARCH SESSION - 6 CRITICAL SLOTS ONLY
# ============================================================================

def store_search_session(guest_id, city, check_in, check_out, adults, room_type=None, preferences=None):
    """Store ONLY critical search slots: city, check_in, check_out, adults, room_type, preferences"""
    session_data = {
        'city': city,
        'check_in': check_in,
        'check_out': check_out, 
        'adults': adults,
        'room_type': room_type,  # e.g. "Deluxe King", "Superior Twin"
        'preferences': preferences,  # e.g. "pool view", "near KLCC"
        'timestamp': time.time()
    }
    
    redis_client.set(f"search_session:{guest_id}", json.dumps(session_data))
    print(f"💾 SEARCH SESSION: {guest_id} → {city}, {check_in}, {adults} adults" + 
          (f", {room_type}" if room_type else "") + 
          (f", {preferences}" if preferences else ""))

def get_search_session(guest_id):
    """Get the current search session with critical slots only."""
    session_data = redis_client.get(f"search_session:{guest_id}")
    if session_data:
        data = json.loads(session_data)
        print(f"📋 SESSION RETRIEVED: {guest_id} → {data.get('city')}, {data.get('check_in')}, {data.get('adults')} adults")
        return data
    return None

def has_search_session(guest_id):
    """Check if guest has an active search session."""
    return redis_client.exists(f"search_session:{guest_id}") > 0

def update_search_session(guest_id, **updates):
    """Update specific critical slots in search session"""
    current_session = get_search_session(guest_id) or {}
    
    # Only allow critical slots
    allowed_slots = {'city', 'check_in', 'check_out', 'adults', 'room_type', 'preferences'}
    filtered_updates = {k: v for k, v in updates.items() if k in allowed_slots}
    
    if filtered_updates:
        current_session.update(filtered_updates)
        current_session['timestamp'] = time.time()
        redis_client.set(f"search_session:{guest_id}", json.dumps(current_session))
        print(f"🔄 SESSION UPDATED: {guest_id} → {filtered_updates}")

def clear_search_session(guest_id):
    """Clear the search session (when guest starts a new search)."""
    redis_client.delete(f"search_session:{guest_id}")
    print(f"🗑️ SESSION CLEARED: {guest_id}")

def should_invalidate_session(guest_id, new_city=None, new_check_in=None):
    """Check if session should be invalidated due to context change."""
    current_session = get_search_session(guest_id)
    if not current_session:
        return False  # No session to invalidate
    
    if new_city and new_city.lower() != current_session.get('city', '').lower():
        print(f"🗑️ INVALIDATING: City changed from {current_session.get('city')} to {new_city}")
        return True
        
    if new_check_in and new_check_in != current_session.get('check_in'):
        print(f"🗑️ INVALIDATING: Date changed from {current_session.get('check_in')} to {new_check_in}")
        return True
        
    return False

def store_search_session_with_invalidation(guest_id, city, check_in, check_out, adults, room_type=None, preferences=None):
    """Store search session with automatic invalidation of old sessions."""
    # Check if we should invalidate existing session
    if should_invalidate_session(guest_id, new_city=city, new_check_in=check_in):
        clear_search_session(guest_id)
    
    # Store new session
    store_search_session(guest_id, city, check_in, check_out, adults, room_type, preferences) 