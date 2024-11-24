from modules.aimp_controller import AimpController
from modules.youtube_downloader import YoutubeDownloader
from modules.playlist_manager import PlaylistManager
from modules.hotkey_manager import HotkeyManager
from modules.request_manager import RequestManager, CommandServer
from modules.text_analysis import TextAnalyzer
from modules.gemini import TranscriptAPI, SentimentAPI
from modules.schedule_manager import ScheduleManager
from modules.utils import load_prompts, ensure_directories_exist

from config import (
    GEMINI_API_KEY, 
    GEMINI_MODEL,
    URL_BACKEND,
    URL_ADMINPAGE,
    BASE_DIR
)

import threading
import time
import schedule
import logging
from logging_config import setup_logging

print(BASE_DIR)

setup_logging()
logger = logging.getLogger(__name__)

def initialize_components():
    """Initialize all required components."""
    try:
        # Ensure all required directories exist
        ensure_directories_exist()
        
        # Initialize APIs and analyzers
        prompt_sentiment, prompt_transcript = load_prompts()
        text_analyzer = TextAnalyzer()
        text_analyzer.initialize()
        
        transcript_api = TranscriptAPI(
            api_key=GEMINI_API_KEY, 
            model=GEMINI_MODEL, 
            prompt=prompt_transcript
        )
        sentiment_api = SentimentAPI(
            api_key=GEMINI_API_KEY, 
            model=GEMINI_MODEL, 
            prompt=prompt_sentiment
        )
        
        # Initialize core components
        aimp_controller = AimpController()
        youtube_downloader = YoutubeDownloader()
        request_manager = RequestManager(URL_BACKEND, URL_ADMINPAGE)
        
        aimp_controller.clear_played_songs()

        server = CommandServer(port=5050) 
        server.set_command_handler(aimp_controller.handle_command)
        server.start()
        
        # Initialize playlist manager with dependencies
        playlist_manager = PlaylistManager(
            aimp_controller=aimp_controller,
            youtube_downloader=youtube_downloader,
            text_analyzer=text_analyzer,
            transcript_api=transcript_api,
            sentiment_api=sentiment_api,
            request_manager=request_manager
        )
        
        # Initialize managers
        schedule_manager = ScheduleManager(playlist_manager, aimp_controller)
        hotkey_manager = HotkeyManager(playlist_manager, aimp_controller)
        
        logger.info("All components initialized successfully")
        return (
            playlist_manager, 
            aimp_controller, 
            request_manager, 
            hotkey_manager,
            schedule_manager
        )
    except Exception as e:
        logger.error(f"Error during initialization: {e}")
        raise

def run_schedule():
    """Run scheduled tasks."""
    while True:
        try:
            schedule.run_pending()
            time.sleep(5)
        except Exception as e:
            logger.error(f"Error in schedule loop: {e}")

def main():
    try:
        # Initialize all components
        (playlist_manager, 
         aimp_controller, 
         request_manager, 
         hotkey_manager,
         schedule_manager) = initialize_components()
        
        # Setup schedules
        schedule_manager.setup_schedules()
        
        # Start AIMP
        aimp_controller.start_aimp()
        
        # Start threads
        hotkey_thread = threading.Thread(
            target=hotkey_manager.start_hotkey_listener, 
            daemon=True,
            name="HotkeyThread"
        )
        schedule_thread = threading.Thread(
            target=run_schedule,
            daemon=True,
            name="ScheduleThread"
        )
        
        hotkey_thread.start()
        schedule_thread.start()
        
        logger.info("Application started successfully")
        print("\nRadio system started successfully!")
        print("Use the following hotkeys to control the system:")
        print("u - Update playlist from backend")
        print("l - Update playlist from local files")
        print("p - Stop audio device")
        print("s - Start audio device")
        print("z - Play current song")
        print("Press Ctrl+C to exit\n")
        
        # Main loop
        previous_title = None
        while True:
            time.sleep(3)
            try:
                # Handle current track info
                current_track = aimp_controller.get_current_track_info()
                if current_track and current_track['title'] != previous_title:
                    previous_title = current_track['title']
                    request_manager.post_playing_song(current_track)
                    
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                
    except KeyboardInterrupt:
        logger.info("Shutting down gracefully...")
        print("\nShutting down gracefully...")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise
    finally:
        # Cleanup code could go here
        pass

if __name__ == "__main__":
    main()