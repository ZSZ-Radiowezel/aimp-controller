import logging
import requests
from typing import Optional, Dict, Any, List
from .decorators import log_errors
from .exceptions import APIConnectionError
from flask import Flask, request, jsonify
from threading import Thread
from typing import Callable
from .aimp_controller import AimpController
from config import AUDIO_DEVICE_NAME

logger = logging.getLogger(__name__)

class CommandServer:
    def __init__(self, port: int = 5050):
        self.app = Flask(__name__)
        self.port = port
        self.command_handler = ["play", "pause", "next"]
        self.aimp_controller = AimpController()
        # Endpoint do odbierania komend
        @self.app.route('/command', methods=['POST'])
        def handle_command():
            try:
                data = request.get_json()
                command = data.get('ToDO')
                if command and self.command_handler:
                    self._handle_command(command)
                    return jsonify({'status': 'success'})
                return jsonify({'status': 'error', 'message': 'Invalid command'}), 400
            except Exception as e:
                logger.error(f"Error handling command: {e}")
                return jsonify({'status': 'error', 'message': str(e)}), 500

    def _handle_command(self, command: str):
        """Handle incoming command."""
        if not self.aimp_controller:
            logger.error("AIMP controller not initialized")
            return

        logger.info(f"Received command: {command}")
        try:
            if command == 'play':
                self.aimp_controller.play_song()
            elif command == 'pause':
                self.aimp_controller.pause_song()
            elif command == 'next':
                self.aimp_controller.skip_song()
            else:
                logger.warning(f"Unknown command: {command}")
        except Exception as e:
            logger.error(f"Error executing command {command}: {e}")
        
    def start(self):
        """Start server in a separate thread."""
        def run():
            self.app.run(host='0.0.0.0', port=self.port)
        
        Thread(target=run, daemon=True).start()
        logger.info(f"Command server started on port {self.port}")

    def set_command_handler(self, handler: Callable):
        """Set handler function for incoming commands."""
        self.command_handler = handler


class RequestManager:
    def __init__(self, backend_url: str, admin_url: str):
        self.backend_url = backend_url
        self.admin_url = admin_url
        
    @log_errors
    def fetch_songs_from_backend(self) -> Optional[List[Dict[str, Any]]]:
        """Fetch songs from backend with retries."""
        for attempt in range(3):
            try:
                response = requests.get(f"{self.backend_url}/voting/songs-to-play")
                if response.status_code == 200:
                    return response.json()
            except Exception as e:
                logger.error(f"Attempt {attempt + 1} failed: {e}")
        return None
        
    # @log_errors
    # def get_admin_command(self) -> Optional[str]:
    #     """Get command from admin panel."""
    #     try:
    #         response = requests.get(f'{self.admin_url}/get')
    #         if response.status_code == 200:
    #             return response.json().get('ToDo')
    #     except Exception as e:
    #         #logger.error(f"Error getting admin command: {e}")
    #         pass
    #     return None

    @log_errors
    def _handle_command(self, command: str):
        """Handle incoming command."""
        if not self.aimp_controller:
            logger.error("AIMP controller not initialized")
            return

        logger.info(f"Received command: {command}")
        try:
            if command == 'play':
                self.aimp_controller.play_song()
            elif command == 'pause':
                self.aimp_controller.pause_song()
            elif command == 'next':
                self.aimp_controller.skip_song()
            else:
                logger.warning(f"Unknown command: {command}")
        except Exception as e:
            logger.error(f"Error executing command {command}: {e}")
        
    @log_errors
    def post_playing_song(self, track_info: Dict[str, str]) -> bool:
        """Post currently playing song info."""
        data = {
            "SongId": track_info['title'],
            "Duration": track_info['duration']
        }
        headers = {'Content-Type': 'application/json'}
        
        for attempt in range(3):
            try:
                response = requests.post(
                    f"{self.backend_url}/voting/playing-song",
                    json=data,
                    headers=headers
                )
                if response.status_code == 200:
                    return True
            except Exception as e:
                logger.error(f"Attempt {attempt + 1} failed: {e}")
        return False