from datetime import timedelta, datetime
from time import sleep
import os
import shutil
import logging
from random import choice
from typing import List, Optional
from moviepy.editor import AudioFileClip
from .decorators import log_errors, handle_exceptions
from .exceptions import PlaylistUpdateError
import os
from typing import List
from .decorators import handle_exceptions
from config import PLAYED_SONGS_FILE
import logging
from config import (
    AUDIO_FOLDER_PATH,
    AUDIO_FOLDER_TEMP_PATH,
    BLACKLISTED_SONGS,
    PLAYED_SONGS_FILE
)

logger = logging.getLogger(__name__)

class PlaylistManager:
    def __init__(self, aimp_controller, youtube_downloader, text_analyzer, 
                 transcript_api, sentiment_api, request_manager):
        self.aimp_controller = aimp_controller
        self.youtube_downloader = youtube_downloader
        self.text_analyzer = text_analyzer
        self.transcript_api = transcript_api
        self.sentiment_api = sentiment_api
        self.request_manager = request_manager

    def _clear_temp_folder(self):
        """Clear all files from temp audio folder."""
        if os.path.exists(AUDIO_FOLDER_TEMP_PATH):
            for file in os.listdir(AUDIO_FOLDER_TEMP_PATH):
                file_path = os.path.join(AUDIO_FOLDER_TEMP_PATH, file)
                try:
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                except Exception as e:
                    logger.error(f"Error removing temp file {file}: {e}")

    # @log_errors
    # def update_playlist(self):
    #     """Update playlist with songs from backend."""
    #     self.aimp_controller.prepare_for_update()
    #     self._clear_temp_folder()  # Clear temp folder before starting
        
    #     playlist_data = self.request_manager.fetch_songs_from_backend()
    #     if playlist_data:
    #         self._process_playlist_data(playlist_data)
    #     else:
    #         logger.warning("Falling back to local playlist update")
    #         self.update_playlist_local()
            
    def _process_playlist_data(self, playlist_data: List[dict]):
        """Process playlist data and add valid songs."""
        valid_songs = []
        for song in playlist_data:
            if self._process_song(song['url']):
                valid_songs.append(song)
                
        if valid_songs:
            self._update_playlist_duration(valid_songs)
            
    @log_errors
    def update_playlist(self):
        """Update playlist with songs from backend."""
        try:
            # Przygotuj AIMP i wyczyść temp folder
            self.aimp_controller.prepare_for_update()
            self._clear_temp_folder()
            
            # Pobierz dane z backendu
            playlist_data = self.request_manager.fetch_songs_from_backend()
            total_duration = timedelta()
            
            if playlist_data:
                # Przetwórz piosenki z backendu
                valid_songs = []
                for song in playlist_data:
                    if self._process_song(song['url']):
                        valid_songs.append(song)
                        duration = timedelta(seconds=self._parse_duration(song['duration']))
                        total_duration += duration
            
            # Jeśli całkowity czas jest za krótki lub nie ma piosenek z backendu,
            # uzupełnij lokalnymi piosenkami
            while total_duration < timedelta(minutes=55):
                song_path = self._get_random_local_song()
                if not song_path:
                    break
                
                duration = self._get_song_duration(song_path)
                if duration:
                    total_duration += duration
                logger.info(f"Added local song {song_path} to playlist, total duration: {total_duration}")
            
            logger.info(f"Final playlist duration: {total_duration}")
            
        except Exception as e:
            logger.error(f"Error updating playlist: {e}")

    @log_errors
    def _process_song(self, url: str) -> bool:
        """Process a single song."""
        try:
            from pytubefix import extract
            video_id = extract.video_id(url)
            
            # Sprawdź blacklistę przed pobraniem
            blacklisted_songs = self._get_blacklisted_songs()
            for blacklisted_song in blacklisted_songs:
                if video_id in blacklisted_song:
                    logger.info(f"Song with video_id {video_id} is blacklisted - skipping download")
                    return False
                
            # Jeśli nie jest na blackliście, kontynuuj pobieranie
            download_result = self.youtube_downloader.download_song(url)
            if not download_result:
                return False
            
            temp_path, is_cached = download_result
            basename = os.path.basename(temp_path)

            # Sprawdź czy piosenka była już odtworzona
            if basename in self.get_played_songs():
                logger.info(f"Song {basename} already played")
                if os.path.exists(temp_path) and not is_cached:
                    os.remove(temp_path)
                return False

            # Sprawdź czy piosenka już istnieje w folderze audio
            existing_path = os.path.join(AUDIO_FOLDER_PATH, basename)
            if os.path.exists(existing_path):
                logger.info(f"Song {basename} already exists in audio folder")
                # Jeśli plik jest w temp, usuń go (bo mamy już w audio)
                if os.path.exists(temp_path) and not is_cached:
                    os.remove(temp_path)
                self.aimp_controller.add_song_to_playlist(existing_path)
                self.add_to_played_songs(basename)
                return True

            # Get and analyze lyrics
            lyrics = self.transcript_api.analyze_audio(temp_path)
            print(lyrics)
            if not lyrics:
                self._add_to_blacklist(basename)
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                logger.info(f"No lyrics found for {basename}")
                return False
            
            # Analyze text content
            analysis_result = self.text_analyzer.analyze_text(lyrics)
            if not analysis_result['is_acceptable']:
                self._add_to_blacklist(basename)
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                logger.info(f"Text analysis failed for {basename}, {analysis_result['profanity_result']}")
                return False
            
            # Analyze sentiment and check if safe for radio
            sentiment_result = self.sentiment_api.analyze_sentiment(lyrics)
            if not sentiment_result:
                self._add_to_blacklist(basename)
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                logger.info(f"No sentiment result for {basename}")
                return False
            
            # Check if song is safe for radio
            if sentiment_result.get('is_safe_for_radio', False):
                # If safe for radio, move to final location and add to playlist
                final_path = os.path.join(AUDIO_FOLDER_PATH, basename)
                try:
                    shutil.move(temp_path, final_path)
                    self.aimp_controller.add_song_to_playlist(final_path)
                    self.add_to_played_songs(basename)
                    logger.info(f"Successfully processed and added song: {basename}")
                    return True
                except Exception as e:
                    logger.error(f"Error moving files for {basename}: {e}")
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                    return False
            else:
                # If not safe for radio, add to blacklist and remove temp file
                logger.info(f"Song {basename} rejected. Reason: {sentiment_result.get('explanation', 'Unknown')}")
                self._add_to_blacklist(basename)
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                return False
        except Exception as e:
            logger.error(f"Error processing song: {e}")
            return False

    def _add_to_blacklist(self, basename: str):
        """Add song to blacklist if not already present."""
        try:
            # Wczytaj obecną blacklistę
            blacklisted_songs = self._get_blacklisted_songs()
            
            # Sprawdź czy piosenka już jest na liście
            if basename not in blacklisted_songs:
                with open(BLACKLISTED_SONGS, 'a', encoding='utf-8') as f:
                    f.write(f"{basename}\n")
                logger.info(f"Added {basename} to blacklist")
            else:
                logger.debug(f"Song {basename} already in blacklist - skipping")
        except Exception as e:
            logger.error(f"Error adding to blacklist: {e}")
            
    def _get_blacklisted_songs(self) -> List[str]:
        """Get list of blacklisted songs."""
        try:
            if not os.path.exists(BLACKLISTED_SONGS):
                with open(BLACKLISTED_SONGS, 'w', encoding='utf-8') as f:
                    f.write('')
                return []
                
            with open(BLACKLISTED_SONGS, 'r', encoding='utf-8') as f:
                return [line.strip() for line in f if line.strip()]
        except Exception as e:
            logger.error(f"Error reading blacklisted songs: {e}")
            return []



    @log_errors
    def _update_playlist_duration(self, data):
        """Update playlist duration to meet minimum threshold."""
        total_duration = timedelta(seconds=sum(
            self._parse_duration(song['duration']) for song in data
        ))

        while total_duration < timedelta(minutes=5):
            total_duration = self._time_calc(total_duration)

        logger.info(f"Updated playlist duration: {total_duration}")

    @log_errors
    def update_playlist_local(self):
        """Update playlist from local files."""
        self.aimp_controller.prepare_for_update()
        total_duration = timedelta()
        
        while total_duration < timedelta(minutes=5):
            song_path = self._get_random_local_song()
            if not song_path:
                break
                
            duration = self._get_song_duration(song_path)
            if duration:
                total_duration += duration
                self.aimp_controller.add_song_to_playlist(song_path)
                
        logger.info(f"Local playlist updated, total duration: {total_duration}")

    def _time_calc(self, time1_obj: timedelta) -> timedelta:
        """Calculate the sum of a given time with a random song duration."""
        time2_obj = self._get_song_duration(self._get_random_local_song())
        return time1_obj + time2_obj if time2_obj else time1_obj
        
    @log_errors
    def _get_random_local_song(self) -> Optional[str]:
        """Fetch a random song that hasn't been played."""
        files_list = os.listdir(AUDIO_FOLDER_PATH)
        logger.debug(f"Available files: {files_list}")
        
        while files_list:
            random_song = choice(files_list)
            logger.debug(f"Randomly selected song: {random_song}")
            played_songs = self.get_played_songs()
            logger.debug(f"Played songs: {played_songs}")
            
            if random_song not in played_songs:
                self.add_to_played_songs(random_song)
                full_path = os.path.join(AUDIO_FOLDER_PATH, random_song)
                self.aimp_controller.add_song_to_playlist(full_path)
                return full_path
                
        logger.warning("No unplayed songs available.")
        return None
        
    @log_errors
    def _get_song_duration(self, song_path: str) -> Optional[timedelta]:
        """Get duration of a song."""
        if not song_path:
            return None
            
        try:
            audio = AudioFileClip(song_path)
            duration = timedelta(seconds=audio.duration)
            audio.close()
            logger.debug(f"Song duration: {duration}")
            return duration
        except Exception as e:
            logger.error(f"Error calculating duration for {song_path}: {e}")
            return None

    @staticmethod
    def _parse_duration(duration_str: str) -> int:
        """Parse duration string to seconds."""
        try:
            duration_obj = datetime.strptime(duration_str, "%H:%M:%S") - datetime.strptime("00:00:00", "%H:%M:%S")
            return int(duration_obj.total_seconds())
        except ValueError as e:
            logger.error(f"Invalid duration format: {e}")
            return 0

    @handle_exceptions
    def add_to_played_songs(self, basename: str) -> None:
        """Add song to played songs file."""
        try:
            with open(PLAYED_SONGS_FILE, 'a', encoding='utf-8') as f:
                f.write(f"{basename}\n")
            logger.debug(f"Added {basename} to played songs")
        except Exception as e:
            logger.error(f"Error adding to played songs: {e}")

    @handle_exceptions
    def get_played_songs(self) -> List[str]:
        """Get list of played songs."""
        try:
            if not os.path.exists(PLAYED_SONGS_FILE):
                with open(PLAYED_SONGS_FILE, 'w', encoding='utf-8') as f:
                    f.write('')
                return []
                
            with open(PLAYED_SONGS_FILE, 'r', encoding='utf-8') as f:
                return [line.strip() for line in f if line.strip()]
        except Exception as e:
            logger.error(f"Error reading played songs: {e}")
            return []