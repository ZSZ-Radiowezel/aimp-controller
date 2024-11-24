import os
import time
import logging
from typing import Optional, Tuple
from pytubefix import YouTube, extract
from .decorators import handle_exceptions
from config import AUDIO_FOLDER_TEMP_PATH, AUDIO_FOLDER_PATH

logger = logging.getLogger(__name__)

class YoutubeDownloader:
    def __init__(self):
        self.download_path = AUDIO_FOLDER_TEMP_PATH
        self.cache_path = AUDIO_FOLDER_PATH
        
        # Create directories if they don't exist
        os.makedirs(self.download_path, exist_ok=True)
        os.makedirs(self.cache_path, exist_ok=True)
    
    @handle_exceptions
    def download_song(self, url: str) -> Optional[Tuple[str, bool]]:
        """Download song from YouTube or return from cache."""
        video_id = extract.video_id(url)
        
        # Check cache first
        cached_file = self._check_cache(video_id)
        if cached_file:
            logger.info(f"Found cached file: {cached_file}")
            return cached_file, True
            
        # Download if not cached
        return self._perform_download(url, video_id)
        
    def _check_cache(self, video_id: str) -> Optional[str]:
        """Check if song exists in cache."""
        for filename in os.listdir(self.cache_path):
            if video_id in filename:
                return os.path.join(self.cache_path, filename)
        return None
        
    def _perform_download(self, url: str, video_id: str) -> Optional[Tuple[str, bool]]:
        """Perform actual download from YouTube."""
        try:
            video = YouTube(url)
            stream = self._get_best_audio_stream(video)
            if not stream:
                logger.error("No suitable audio stream found")
                return None
                
            filename = f"{video_id}{self._get_extension(stream)}"
            output_path = os.path.join(self.download_path, filename)
            
            logger.info(f"Downloading {url} to {output_path}")
            stream.download(output_path=self.download_path, filename=filename)
            time.sleep(3)  # Wait for file to be ready
            
            return output_path, False
            
        except Exception as e:
            logger.error(f"Download failed: {e}")
            return None
            
    @staticmethod
    def _get_best_audio_stream(video: YouTube):
        """Get best available audio stream."""
        for mime_type in ["audio/webm", "audio/mp3"]:
            stream = video.streams.filter(mime_type=mime_type).first()
            if stream:
                return stream
        return None
        
    @staticmethod
    def _get_extension(stream) -> str:
        """Get appropriate file extension based on stream type."""
        return ".webm" if stream.mime_type == "audio/webm" else ".mp3"