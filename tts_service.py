"""
TTS (Text-to-Speech) service client for generating audio notifications.
"""

import os
import requests
from typing import Optional, Tuple
import logging

# Get logger for this module
logger = logging.getLogger(__name__)

# Get TTS service URL from environment variable, default to container name
TTS_SERVICE_URL = os.getenv('TTS_SERVICE_URL', 'http://tts-service:5000')

# Timeout constants (in seconds)
TTS_SYNTHESIS_TIMEOUT = 30
TTS_HEALTH_CHECK_TIMEOUT = 5


def synthesize_speech(text: str, language: str = 'de') -> Tuple[bool, Optional[bytes], str]:
    """
    Synthesize speech from text using the TTS service.
    
    Args:
        text: Text to convert to speech
        language: Language code (default: 'de' for German)
        
    Returns:
        Tuple of (success: bool, audio_data: Optional[bytes], error_message: str)
    """
    try:
        # Make request to TTS service
        response = requests.post(
            f'{TTS_SERVICE_URL}/api/tts',
            json={
                'text': text,
                'language': language
            },
            timeout=TTS_SYNTHESIS_TIMEOUT
        )
        
        if response.status_code == 200:
            logger.info(f"TTS synthesis successful for text: {text[:50]}...")
            return True, response.content, ""
        else:
            error_msg = f"TTS service returned status code {response.status_code}"
            logger.error(error_msg)
            return False, None, error_msg
            
    except requests.exceptions.ConnectionError as e:
        error_msg = f"Error connecting to TTS service: {str(e)}"
        logger.error(error_msg)
        return False, None, error_msg
    except requests.exceptions.Timeout as e:
        error_msg = f"TTS service request timed out: {str(e)}"
        logger.error(error_msg)
        return False, None, error_msg
    except Exception as e:
        error_msg = f"Unexpected error in TTS synthesis: {str(e)}"
        logger.error(error_msg)
        return False, None, error_msg


def check_tts_service_health() -> bool:
    """
    Check if the TTS service is available and responding.
    
    Returns:
        True if service is healthy, False otherwise
    """
    try:
        response = requests.get(f'{TTS_SERVICE_URL}/api/health', timeout=TTS_HEALTH_CHECK_TIMEOUT)
        is_healthy = response.status_code == 200
        if is_healthy:
            logger.info("TTS service is healthy")
        else:
            logger.warning(f"TTS service health check failed with status {response.status_code}")
        return is_healthy
    except requests.exceptions.RequestException as e:
        logger.error(f"TTS service health check failed: {str(e)}")
        return False


def get_tts_service_info() -> dict:
    """
    Get information about the configured TTS service.
    
    Returns:
        Dictionary with TTS service configuration
    """
    return {
        'service_url': TTS_SERVICE_URL,
        'is_healthy': check_tts_service_health()
    }
