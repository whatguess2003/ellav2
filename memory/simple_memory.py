#!/usr/bin/env python3
"""
Simple in-memory fallback for Redis when Redis is not available
Used for Railway deployment where Redis is not configured
"""

import json
import time
from typing import List, Dict, Optional

# In-memory storage (will reset on app restart)
memory_store = {}
dialog_store = {}

def append_dialog_turn(thread_id: str, role: str, content: str) -> bool:
    """Append a dialog turn to memory. Returns True if summarization should be triggered."""
    key = f"dialog:{thread_id}"
    
    if key not in dialog_store:
        dialog_store[key] = []
    
    entry = json.dumps({
        "role": role,
        "content": content,
        "timestamp": time.time()
    })
    
    dialog_store[key].append(entry)
    
    # Keep only last 15 entries
    if len(dialog_store[key]) > 15:
        dialog_store[key] = dialog_store[key][-15:]
    
    print(f"[MEMORY][append] thread_id={thread_id} role={role} total_turns={len(dialog_store[key])}")
    
    # Trigger summarization every 10 turns
    return len(dialog_store[key]) % 10 == 0

def get_dialog_history(thread_id: str, limit: int = 10) -> List[Dict]:
    """Get recent dialog history from memory using thread_id as the key."""
    key = f"dialog:{thread_id}"
    
    if key not in dialog_store:
        return []
    
    entries = dialog_store[key][-limit:] if limit > 0 else dialog_store[key]
    
    history = []
    for entry in entries:
        try:
            parsed = json.loads(entry)
            history.append(parsed)
        except json.JSONDecodeError:
            continue
    
    print(f"[MEMORY][get] thread_id={thread_id} returned {len(history)} entries")
    return history

def get_full_context(thread_id: str) -> List[Dict]:
    """Get full dialog context from memory."""
    return get_dialog_history(thread_id, limit=-1)

def get_all_dialog_turns(thread_id: str) -> List[Dict]:
    """Get all dialog turns for a thread."""
    return get_full_context(thread_id)

def store_summary(guest_id: str, summary: str):
    """Store conversation summary in memory."""
    memory_store[f"summary:{guest_id}"] = summary
    print(f"[MEMORY][summary] Stored summary for {guest_id}")

def get_summary(guest_id: str) -> Optional[str]:
    """Get conversation summary from memory."""
    return memory_store.get(f"summary:{guest_id}")

def store_search_session(guest_id: str, session_data: Dict):
    """Store search session data in memory."""
    memory_store[f"search_session:{guest_id}"] = json.dumps(session_data)
    print(f"[MEMORY][search] Stored search session for {guest_id}")

def get_search_session(guest_id: str) -> Optional[Dict]:
    """Get search session data from memory."""
    data = memory_store.get(f"search_session:{guest_id}")
    if data:
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            return None
    return None

def has_search_session(guest_id: str) -> bool:
    """Check if guest has an active search session."""
    return f"search_session:{guest_id}" in memory_store

def update_search_session(guest_id: str, updates: Dict):
    """Update existing search session with new data."""
    current_session = get_search_session(guest_id) or {}
    current_session.update(updates)
    store_search_session(guest_id, current_session)

def clear_search_session(guest_id: str):
    """Clear search session for guest."""
    key = f"search_session:{guest_id}"
    if key in memory_store:
        del memory_store[key]
        print(f"[MEMORY][search] Cleared search session for {guest_id}")

def store_search_session_with_invalidation(guest_id: str, session_data: Dict):
    """Store search session with invalidation logic."""
    store_search_session(guest_id, session_data)

def track_search_preference(guest_id: str, preference: str):
    """Track guest search preferences."""
    key = f"preferences:{guest_id}"
    if key not in memory_store:
        memory_store[key] = []
    
    prefs = memory_store[key]
    if preference not in prefs:
        prefs.append(preference)
        memory_store[key] = prefs[-10:]  # Keep last 10 preferences

def get_guest_preferences(guest_id: str) -> List[str]:
    """Get guest preferences."""
    return memory_store.get(f"preferences:{guest_id}", [])

print("✅ Simple memory system initialized (Redis fallback)") 