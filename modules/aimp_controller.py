import os
import subprocess
import threading
import time
from time import sleep
import logging
import pyaimp
from typing import Optional, Dict
from .decorators import ensure_connected, handle_exceptions
from config import (
    MAIN_AUDIO_DEVICE_NAME, 
    AIMP_VOLUME_INCREMENT, 
    AIMP_MAX_VOLUME, 
    PLAYED_SONGS_FILE,
    AIMP_PLAYLIST_PATH
)

logger = logging.getLogger(__name__)

class AimpController:
    def __init__(self):
        self.command = "aimp"
        self.client = None
        self.current_volume = AIMP_MAX_VOLUME
        
    @handle_exceptions
    def get_current_track_info(self) -> Optional[Dict[str, str]]:
        """Get information about currently playing track."""
        if not self.client:
            return None
            
        try:
            info = self.client.get_current_track_info()
            return {
                'title': info.get('title', ''),
                'duration': info.get('duration', '00:00:00')
            }
        except Exception as e:
            logger.error(f"Error getting track info: {e}")
            return None
    
    @handle_exceptions
    def start_aimp(self) -> None:
        """Start AIMP in a separate thread."""
        thread = threading.Thread(target=self.run_aimp)
        thread.start()
        time.sleep(3)  # Wait for AIMP to initialize
        self.connect_to_aimp()
    
    def run_aimp(self) -> None:
        """Launch AIMP process."""
        subprocess.run(self.command)
    
    @handle_exceptions
    def connect_to_aimp(self) -> None:
        """Connect to AIMP client."""
        self.client = pyaimp.Client()
        self.client.stop()  # Ensure player is stopped upon connection
    
    @handle_exceptions
    def aimp_quit(self) -> None:
        """Quit AIMP client."""
        if self.client:
            self.client.quit()
            self.client = None
    
    @ensure_connected
    def add_song_to_playlist(self, song_path: str) -> None:
        """Add a song to the active playlist."""
        self.client.add_to_active_playlist(song_path)
    
    @ensure_connected
    def play_song(self) -> None:
        """Play the current song."""
        self.client.play()
    
    @ensure_connected
    def pause_song(self) -> None:
        """Pause the current song."""
        self.client.pause()
    
    @ensure_connected
    def skip_song(self) -> None:
        """Skip to the next song."""
        self.client.next()
    
    @handle_exceptions
    def stop_audio_device(self, device: str) -> None:
        """Gradually reduce volume of the specified audio device."""
        volume = self.current_volume
        while volume > 0:
            volume = max(0, volume - AIMP_VOLUME_INCREMENT)
            subprocess.run(f'nircmd setsysvolume {volume} "{device}"')
        self.current_volume = 0
    
    @handle_exceptions
    def start_audio_device(self) -> None:
        """Gradually increase volume of the main audio device."""
        subprocess.run(f'nircmd setsysvolume 0 "{MAIN_AUDIO_DEVICE_NAME}"')
        volume = 0
        while volume < AIMP_MAX_VOLUME:
            volume = min(AIMP_MAX_VOLUME, volume + AIMP_VOLUME_INCREMENT)
            subprocess.run(f'nircmd setsysvolume {volume} "{MAIN_AUDIO_DEVICE_NAME}"')
        self.current_volume = AIMP_MAX_VOLUME
    
    @handle_exceptions
    def clear_played_songs(self) -> None:
        """Clear the played songs file."""
        with open(PLAYED_SONGS_FILE, 'w', encoding='utf-8') as f:
            f.write('')
    
    @handle_exceptions
    def handle_command(self, command: str) -> None:
        """Handle commands from admin panel."""
        command_handlers = {
            "Play": self.play_song,
            "Pause": self.pause_song,
            "Skip": self.skip_song
        }
        
        handler = command_handlers.get(command)
        if handler:
            handler()

    @handle_exceptions
    def prepare_for_update(self) -> None:
        """Prepare AIMP for playlist update."""
        try:
            self.connect_to_aimp()
            self.stop_audio_device(MAIN_AUDIO_DEVICE_NAME)
            self.aimp_quit()
            sleep(2)
            
            # Czyścimy TYLKO pliki playlist, nie ruszamy plików audio
            if os.path.exists(AIMP_PLAYLIST_PATH):
                for file in os.listdir(AIMP_PLAYLIST_PATH):
                    if file.endswith('.aimppl4'):  # upewnij się że usuwasz tylko pliki playlist
                        try:
                            os.remove(os.path.join(AIMP_PLAYLIST_PATH, file))
                            logger.debug(f"Removed playlist file: {file}")
                        except Exception as e:
                            logger.error(f"Error removing playlist file {file}: {e}")
            
            # Restart AIMP
            self.start_aimp()
            sleep(1)
            self.connect_to_aimp()
            
            logger.info("AIMP prepared for update")
        except Exception as e:
            logger.error(f"Error preparing AIMP for update: {e}")
            raise

    @handle_exceptions
    def clear_playlist_files(self) -> None:
        """Clear all playlist files."""
        if os.path.exists(AIMP_PLAYLIST_PATH):
            for file in os.listdir(AIMP_PLAYLIST_PATH):
                try:
                    os.remove(os.path.join(AIMP_PLAYLIST_PATH, file))
                    logger.debug(f"Removed playlist file: {file}")
                except Exception as e:
                    logger.error(f"Error removing playlist file {file}: {e}")
