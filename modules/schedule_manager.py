import schedule
import logging
from typing import Any, Callable
from .decorators import log_errors
from config import (
    PLAYLIST_UPDATE_TIMES,
    DEVICE_START_TIMES,
    DEVICE_STOP_TIMES,
    AUDIO_DEVICE_NAME
)

logger = logging.getLogger(__name__)

class ScheduleManager:
    def __init__(self, playlist_manager, aimp_controller):
        self.playlist_manager = playlist_manager
        self.aimp_controller = aimp_controller
        
    @log_errors
    def setup_schedules(self):
        """Setup all scheduled tasks."""
        # Playlist updates
        for time_str in PLAYLIST_UPDATE_TIMES:
            schedule.every().day.at(f"{time_str}:00").do(
                self.playlist_manager.update_playlist
            )

        # Device control
        for stop_time in DEVICE_STOP_TIMES:
            schedule.every().day.at(f"{stop_time}:00").do(
                self.aimp_controller.stop_audio_device, 
                device=AUDIO_DEVICE_NAME
            )

        for start_time in DEVICE_START_TIMES:
            schedule.every().day.at(f"{start_time}:00").do(
                self.aimp_controller.start_audio_device
            )
            schedule.every().day.at(f"{start_time}:00").do(
                self.aimp_controller.play_song
            )

        # Cleanup
        schedule.every().day.at("07:44:00").do(
            self.aimp_controller.clear_played_songs
        )

        logger.info("All schedules have been set up")