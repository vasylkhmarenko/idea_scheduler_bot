"""Voice message processing using Google Speech-to-Text."""

import os
import logging
from pathlib import Path
from google.cloud import speech
from google.oauth2 import service_account

logger = logging.getLogger(__name__)

# Service account for Speech-to-Text
SERVICE_ACCOUNT_FILE = Path(__file__).parent / 'voicetask-488210-6dfb51af8f1a.json'


def get_speech_client():
    """Create authenticated Speech-to-Text client."""
    credentials = service_account.Credentials.from_service_account_file(
        str(SERVICE_ACCOUNT_FILE)
    )
    return speech.SpeechClient(credentials=credentials)


def transcribe_voice(audio_content: bytes, language_code: str = "en-US") -> str | None:
    """
    Transcribe voice audio to text.

    Args:
        audio_content: Raw audio bytes (OGG Opus format from Telegram)
        language_code: BCP-47 language code (default: en-US)

    Returns:
        Transcribed text or None if transcription failed
    """
    try:
        client = get_speech_client()

        audio = speech.RecognitionAudio(content=audio_content)
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.OGG_OPUS,
            sample_rate_hertz=48000,  # Telegram voice messages use 48kHz
            language_code=language_code,
        )

        response = client.recognize(config=config, audio=audio)

        if not response.results:
            logger.warning("No transcription results returned")
            return None

        # Combine all transcription results
        transcript = " ".join(
            result.alternatives[0].transcript
            for result in response.results
            if result.alternatives
        )

        return transcript.strip() if transcript else None

    except Exception as e:
        logger.error(f"Speech-to-text error: {e}")
        return None
