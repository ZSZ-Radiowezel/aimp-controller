import os

# API Keys
GEMINI_API_KEY = "."
GEMINI_MODEL = "gemini-1.5-flash"

# URLs
URL_BACKEND = "http://127.0.0.1:5000"
URL_ADMINPAGE = "http://your_admin_url"

# File Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AUDIO_FOLDER_PATH = os.path.join(BASE_DIR, "audio")
AUDIO_FOLDER_TEMP_PATH = os.path.join(BASE_DIR, "audio_temp")
AIMP_PLAYLIST_PATH = os.path.join(os.environ['USERPROFILE'], 'AppData', 'Roaming', 'AIMP', 'PLS')
PLAYED_SONGS_FILE = os.path.join(BASE_DIR, "played_songs.txt")
BLACKLISTED_SONGS = os.path.join(BASE_DIR, "blacklisted_songs.txt")
PROMPT_SENTIMENT = os.path.join(BASE_DIR, "prompts", "sentiment_prompt.txt")
PROMPT_TRANSCRIPTION = os.path.join(BASE_DIR, "prompts", "transcription_prompt.txt")

# Audio Device Settings
AUDIO_DEVICE_NAME = "HDTV" # korytarz "Miks Stereo"
MAIN_AUDIO_DEVICE_NAME = "HDTV" # Świetlica
AIMP_VOLUME_INCREMENT = 750
AIMP_MAX_VOLUME = 65535

# Schedule Times
PLAYLIST_UPDATE_TIMES = ["07:45","08:40", "09:35", "10:30", "11:25", "12:25", "13:20", "14:15","15:10"]
DEVICE_START_TIMES = ["07:50","08:45", "09:40", "10:35", "11:30", "12:30", "13:25", "14:20","15:15"]
DEVICE_STOP_TIMES = ["08:00", "08:55", "09:50", "10:45", "11:45", "12:40", "13:35", "14:30","15:25"]