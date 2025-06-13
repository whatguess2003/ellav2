"""
Audio utilities for OpenAI Realtime API
Handles conversion between different audio formats for streaming
"""

import base64
import struct
import logging

logger = logging.getLogger(__name__)

def float_to_16bit_pcm(float32_array):
    """
    Convert float32 audio samples to 16-bit PCM bytes
    
    Args:
        float32_array: Array of float32 samples (range -1.0 to 1.0)
        
    Returns:
        bytes: 16-bit PCM audio data in little-endian format
    """
    try:
        # Clamp values to valid range [-1.0, 1.0]
        clipped = [max(-1.0, min(1.0, x)) for x in float32_array]
        
        # Convert to 16-bit signed integers and pack as bytes
        pcm16 = b''.join(struct.pack('<h', int(x * 32767)) for x in clipped)
        
        return pcm16
    except Exception as e:
        logger.error(f"Error converting float32 to PCM16: {e}")
        return b''

def base64_encode_audio(float32_array):
    """
    Convert float32 audio to base64-encoded 16-bit PCM for OpenAI Realtime API
    
    Args:
        float32_array: Array of float32 samples
        
    Returns:
        str: Base64-encoded 16-bit PCM audio data
    """
    try:
        pcm_bytes = float_to_16bit_pcm(float32_array)
        encoded = base64.b64encode(pcm_bytes).decode('ascii')
        return encoded
    except Exception as e:
        logger.error(f"Error encoding audio to base64: {e}")
        return ""

def pcm16_to_base64(pcm16_bytes):
    """
    Directly encode 16-bit PCM bytes to base64
    
    Args:
        pcm16_bytes: Raw 16-bit PCM audio bytes
        
    Returns:
        str: Base64-encoded audio data
    """
    try:
        encoded = base64.b64encode(pcm16_bytes).decode('ascii')
        return encoded
    except Exception as e:
        logger.error(f"Error encoding PCM16 to base64: {e}")
        return ""

def base64_to_pcm16(base64_audio):
    """
    Decode base64 audio data back to 16-bit PCM bytes
    
    Args:
        base64_audio: Base64-encoded audio string
        
    Returns:
        bytes: Raw 16-bit PCM audio data
    """
    try:
        pcm_bytes = base64.b64decode(base64_audio.encode('ascii'))
        return pcm_bytes
    except Exception as e:
        logger.error(f"Error decoding base64 audio: {e}")
        return b''

def create_audio_append_event(audio_data):
    """
    Create an OpenAI Realtime API input_audio_buffer.append event
    
    Args:
        audio_data: Either float32 array or base64-encoded string
        
    Returns:
        dict: Event object ready to send to OpenAI
    """
    try:
        if isinstance(audio_data, str):
            # Already base64 encoded
            base64_audio = audio_data
        else:
            # Convert float32 to base64
            base64_audio = base64_encode_audio(audio_data)
        
        return {
            "type": "input_audio_buffer.append",
            "audio": base64_audio
        }
    except Exception as e:
        logger.error(f"Error creating audio append event: {e}")
        return {"type": "input_audio_buffer.append", "audio": ""}

def create_audio_commit_event():
    """
    Create an OpenAI Realtime API input_audio_buffer.commit event
    
    Returns:
        dict: Event object to commit the audio buffer
    """
    return {"type": "input_audio_buffer.commit"}

def create_audio_clear_event():
    """
    Create an OpenAI Realtime API input_audio_buffer.clear event
    
    Returns:
        dict: Event object to clear the audio buffer
    """
    return {"type": "input_audio_buffer.clear"}

# Audio format validation
def validate_audio_format(sample_rate=24000, channels=1, format_type="pcm16"):
    """
    Validate audio format against OpenAI Realtime API requirements
    
    Args:
        sample_rate: Audio sample rate (should be 24000 Hz)
        channels: Number of audio channels (should be 1 - mono)
        format_type: Audio format (should be "pcm16")
        
    Returns:
        bool: True if format is valid for OpenAI Realtime API
    """
    if sample_rate != 24000:
        logger.warning(f"Sample rate {sample_rate} Hz not optimal for OpenAI (recommended: 24000 Hz)")
        return False
    
    if channels != 1:
        logger.warning(f"Channel count {channels} not supported by OpenAI (must be mono - 1 channel)")
        return False
    
    if format_type.lower() != "pcm16":
        logger.warning(f"Format {format_type} not supported by OpenAI (must be pcm16)")
        return False
    
    return True 