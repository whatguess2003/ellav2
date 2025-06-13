# core/guest_id.py

def get_guest_id(phone_number=None, platform=None):
    """
    Generate guest ID with cross-platform context sharing support
    
    Args:
        phone_number: Phone number for cross-platform sharing (e.g., "60175353792")
        platform: Platform identifier ("whatsapp", "voice", "web")
    
    Returns:
        str: Guest ID that can be shared across platforms
    """
    if phone_number:
        # Use phone number directly for cross-platform context sharing
        # Same guest calling and messaging will have same context
        return phone_number
    
    # Fallback to platform-specific IDs for anonymous users
    if platform == "web":
        return "guest_web_anonymous"
    elif platform == "voice":
        import uuid
        return f"guest_voice_{str(uuid.uuid4())[:8]}"
    else:
        # Default fallback
        return "guest_anonymous"

def extract_phone_from_guest_id(guest_id):
    """
    Extract phone number from guest_id if it contains one
    
    Args:
        guest_id: Guest ID that might contain a phone number
        
    Returns:
        str or None: Phone number if found, None otherwise
    """
    # If guest_id is already a phone number (digits only)
    if guest_id.isdigit() and len(guest_id) >= 10:
        return guest_id
    
    # Extract from formatted IDs like "whatsapp_60175353792"
    if "_" in guest_id:
        parts = guest_id.split("_")
        for part in parts:
            if part.isdigit() and len(part) >= 10:
                return part
    
    return None

def is_cross_platform_guest(guest_id):
    """
    Check if guest_id supports cross-platform context sharing
    
    Args:
        guest_id: Guest ID to check
        
    Returns:
        bool: True if guest can share context across platforms
    """
    return extract_phone_from_guest_id(guest_id) is not None