import logging
import requests
from typing import Optional, Dict, Any, List
from flask import Flask, request, jsonify
from threading import Thread
from typing import Callable

logger = logging.getLogger(__name__)

class CommandServer:
    def __init__(self, port: int = 5000):
        self.app = Flask(__name__)
        self.port = port
        self.command_handler: Optional[Callable] = None
        
        # Endpoint do odbierania komend
        @self.app.route('/command', methods=['POST'])
        def handle_command():
            try:
                data = request.get_json()
                command = data.get('ToDO')
                if command and self.command_handler:
                    self.command_handler(command)
                    return jsonify({'status': 'success'})
                return jsonify({'status': 'error', 'message': 'Invalid command'}), 400
            except Exception as e:
                logger.error(f"Error handling command: {e}")
                return jsonify({'status': 'error', 'message': str(e)}), 500

    def start(self):
        """Start server in a separate thread."""
        def run():
            self.app.run(host='0.0.0.0', port=self.port)
        
        Thread(target=run, daemon=True).start()
        logger.info(f"Command server started on port {self.port}")

    def set_command_handler(self, handler: Callable):
        """Set handler function for incoming commands."""
        self.command_handler = handler


def handle_test_command(command: str):
    """Test function to handle commands."""
    print(f"Received command: {command}")
    logger.info(f"Test handler received command: {command}")


if __name__ == "__main__":
    # Konfiguracja loggera
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Tworzenie i uruchamianie serwera
    server = CommandServer(port=5000)
    server.set_command_handler(handle_test_command)
    server.start()
    
    print("Server is running. Send POST requests to http://localhost:5000/command")
    print("Example command:")
    print('curl -X POST http://localhost:5000/command -H "Content-Type: application/json" -d \'{"ToDO": "play"}\'')
    
    # Utrzymuj program działający
    try:
        while True:
            input()
    except KeyboardInterrupt:
        print("\nShutting down...")