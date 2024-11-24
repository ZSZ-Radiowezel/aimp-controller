from datetime import datetime, timedelta
import logging
import os
from typing import Tuple, Optional
from moviepy.editor import AudioFileClip
from .decorators import log_errors
from config import (
    PROMPT_SENTIMENT,
    PROMPT_TRANSCRIPTION,
    BLACKLISTED_SONGS,
    PLAYED_SONGS_FILE
)

logger = logging.getLogger(__name__)

@log_errors
def load_prompts() -> Tuple[str, str]:
    """Load prompt templates for sentiment and transcription analysis."""
    try:
        with open(PROMPT_TRANSCRIPTION, 'r', encoding='utf-8') as file:
            prompt_t = file.read()

        with open(PROMPT_SENTIMENT, 'r', encoding='utf-8') as file:
            prompt_s = file.read()
        
        return prompt_s, prompt_t
    except FileNotFoundError as e:
        logger.error(f"Prompt file not found: {e}")
        raise
    except Exception as e:
        logger.error(f"Error loading prompts: {e}")
        raise

@log_errors
def get_song_length(audio_file: str) -> Optional[timedelta]:
    """Get the duration of an audio file."""
    if not audio_file:
        logger.warning("No audio file provided")
        return None
        
    try:
        audio = AudioFileClip(audio_file)
        duration = timedelta(seconds=audio.duration)
        audio.close()
        logger.debug(f"Song duration: {duration}")
        return duration
    except Exception as e:
        logger.error(f"Error calculating duration for {audio_file}: {e}")
        return None

@log_errors
def parse_duration(duration_str: str) -> int:
    """Parse a duration string in HH:MM:SS format to total seconds."""
    try:
        duration_obj = datetime.strptime(duration_str, "%H:%M:%S") - datetime.strptime("00:00:00", "%H:%M:%S")
        return int(duration_obj.total_seconds())
    except ValueError as e:
        logger.error(f"Invalid duration format: {e}")
        return 0

@log_errors
def handle_rejected_song(downloaded_song: Optional[str], basename: str, reason: str) -> None:
    """Handle rejected songs by removing them and updating blacklist."""
    if downloaded_song and os.path.exists(downloaded_song):
        try:
            os.remove(downloaded_song)
            logger.info(f"Removed rejected song file: {downloaded_song}")
        except Exception as e:
            logger.error(f"Error removing rejected song file: {e}")

    try:
        with open(BLACKLISTED_SONGS, 'a', encoding='utf-8') as f:
            f.write(f"{basename}\n")
        logger.info(f"Added {basename} to blacklist. Reason: {reason}")
    except Exception as e:
        logger.error(f"Error updating blacklist: {e}")

@log_errors
def ensure_directories_exist() -> None:
    """Ensure all required directories exist."""
    directories = [
        os.path.dirname(BLACKLISTED_SONGS),
        os.path.dirname(PLAYED_SONGS_FILE),
        "logs",
        "audio",
        "audio_temp",
    ]
    
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)
            logger.info(f"Created directory: {directory}")