class AudioProcessingError(Exception):
    """Raised when there's an error processing audio files."""
    pass

class PlaylistUpdateError(Exception):
    """Raised when there's an error updating the playlist."""
    pass

class APIConnectionError(Exception):
    """Raised when there's an error connecting to external APIs."""
    pass

class TextAnalysisError(Exception):
    """Raised when there's an error during text analysis."""
    pass