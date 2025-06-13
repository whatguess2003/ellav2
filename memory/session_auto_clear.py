#!/usr/bin/env python3
"""
Session Auto-Clear Module
Handles automatic clearing of stale search sessions based on time passage and date changes.
"""

import redis
import os
import json
import time
from datetime import datetime, timezone, timedelta

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)

def is_session_stale(session_data):
    """Check if a session has become stale due to time passage."""
    if not session_data or 'timestamp' not in session_data or 'check_in' not in session_data:
        return True
    
    session_timestamp = session_data['timestamp']
    check_in_date = session_data['check_in']
    current_time = time.time()
    current_date = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    
    # Rule 1: Sessions older than 24 hours are stale
    session_age_hours = (current_time - session_timestamp) / 3600
    if session_age_hours > 24:
        print(f"⏰ STALE SESSION: {session_age_hours:.1f} hours old (>24h)")
        return True
    
    # Rule 2: If check-in date is in the past, session is stale
    if check_in_date < current_date:
        print(f"⏰ STALE SESSION: Check-in date {check_in_date} is in the past (today: {current_date})")
        return True
    
    # Rule 3: If session was created for "today" but it's now a different day
    session_date = datetime.fromtimestamp(session_timestamp, timezone.utc).strftime('%Y-%m-%d')
    if check_in_date == session_date and check_in_date != current_date:
        print(f"⏰ STALE SESSION: 'Today' session created on {session_date}, but today is {current_date}")
        return True
    
    return False

def get_search_session_with_auto_clear(guest_id):
    """Get search session with automatic staleness checking and clearing."""
    session_data = redis_client.get(f"search_session:{guest_id}")
    if session_data:
        data = json.loads(session_data)
        
        # Check if session is stale and should be auto-cleared
        if is_session_stale(data):
            print(f"⏰ SESSION AUTO-CLEARED for {guest_id}: Session became stale")
            redis_client.delete(f"search_session:{guest_id}")
            return None
            
        print(f"📋 SEARCH SESSION RETRIEVED for {guest_id}: {data['city']}, {data['check_in']}, {data['adults']} adults")
        return data
    return None

def cleanup_stale_sessions():
    """Cleanup all stale sessions across all guests (maintenance function)."""
    pattern = "search_session:*"
    stale_count = 0
    
    try:
        for key in redis_client.scan_iter(match=pattern):
            session_data = redis_client.get(key)
            if session_data:
                data = json.loads(session_data)
                if is_session_stale(data):
                    redis_client.delete(key)
                    stale_count += 1
                    guest_id = key.replace("search_session:", "")
                    print(f"🧹 CLEANUP: Removed stale session for {guest_id}")
    except Exception as e:
        print(f"❌ Session cleanup error: {e}")
    
    if stale_count > 0:
        print(f"🧹 CLEANUP COMPLETE: Removed {stale_count} stale sessions")
    
    return stale_count

def get_session_with_relative_date_check(guest_id, user_message=""):
    """Get session with check for relative date mismatches."""
    session = get_search_session_with_auto_clear(guest_id)
    if not session:
        return None
    
    current_date = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    user_message_lower = user_message.lower()
    
    # If user says "harini" but session has different date, auto-clear for refresh
    if 'harini' in user_message_lower or 'today' in user_message_lower:
        if session['check_in'] != current_date:
            print(f"🔄 AUTO-REFRESH: User said 'harini' but session has {session['check_in']}, clearing for refresh")
            redis_client.delete(f"search_session:{guest_id}")
            return None
    
    # If user says "esok" but session doesn't have tomorrow's date, auto-clear
    elif 'esok' in user_message_lower or 'tomorrow' in user_message_lower:
        tomorrow_date = (datetime.now(timezone.utc) + timedelta(days=1)).strftime('%Y-%m-%d')
        if session['check_in'] != tomorrow_date:
            print(f"🔄 AUTO-REFRESH: User said 'esok' but session has {session['check_in']}, clearing for refresh")
            redis_client.delete(f"search_session:{guest_id}")
            return None
    
    # If user says "lusa" but session doesn't have day-after-tomorrow's date, auto-clear
    elif 'lusa' in user_message_lower:
        day_after_tomorrow = (datetime.now(timezone.utc) + timedelta(days=2)).strftime('%Y-%m-%d')
        if session['check_in'] != day_after_tomorrow:
            print(f"🔄 AUTO-REFRESH: User said 'lusa' but session has {session['check_in']}, clearing for refresh")
            redis_client.delete(f"search_session:{guest_id}")
            return None
    
    return session

def schedule_daily_cleanup():
    """Schedule daily cleanup of stale sessions (for background task)."""
    return cleanup_stale_sessions()

if __name__ == "__main__":
    # Test the auto-clear functionality
    print("🧪 Testing Session Auto-Clear Functionality")
    print("=" * 50)
    
    stale_count = cleanup_stale_sessions()
    print(f"Found and cleaned {stale_count} stale sessions") 