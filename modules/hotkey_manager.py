import keyboard
import logging
from .decorators import log_errors

logger = logging.getLogger(__name__)

class HotkeyManager:
    def __init__(self, playlist_manager, aimp_controller):
        self.playlist_manager = playlist_manager
        self.aimp_controller = aimp_controller
        self._setup_hotkeys()

    def _setup_hotkeys(self):
        """Setup all hotkey bindings."""
        self.hotkey_mappings = {
            'p': self.aimp_controller.stop_audio_device,
            's': self.aimp_controller.start_audio_device,
            'u': self.playlist_manager.update_playlist,
            'l': self.playlist_manager.update_playlist_local,
            'z': self.aimp_controller.play_song
        }

    @log_errors
    def start_hotkey_listener(self):
        """Start listening for hotkeys."""
        for key, callback in self.hotkey_mappings.items():
            keyboard.add_hotkey(key, callback)
        
        # Print available commands
        print("\nAvailable commands:")
        print("Press u to update playlist")
        print("Press l to update playlist locally (from disk)")
        print("Press p to mute sound device")
        print("Press s to unmute sound device")
        print("Press z to play song")
        print("Press Ctrl + C to exit\n")

        keyboard.wait()