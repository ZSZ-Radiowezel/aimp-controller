import re
from typing import Dict, Set, Optional
from langdetect import detect
from ahocorasick import Automaton
import logging
from .decorators import handle_exceptions
from .exceptions import TextAnalysisError

logger = logging.getLogger(__name__)

class TextAnalyzer:
    def __init__(self):
        self.profanity_pl_automaton = Automaton()
        self.profanity_en_automaton = Automaton()
        self.emoji_unicode_ranges = self._create_emoji_unicode_ranges()
        self.initialized = False
        
    def initialize(self) -> None:
        """Initialize the analyzer with profanity dictionaries."""
        try:
            self._load_words_into_automaton("wulgaryzmy_pl.txt", self.profanity_pl_automaton)
            self._load_words_into_automaton("wulgaryzmy_en.txt", self.profanity_en_automaton)
            self.initialized = True
        except Exception as e:
            logger.error(f"Failed to initialize TextAnalyzer: {e}")
            raise TextAnalysisError("Initialization failed")

    @handle_exceptions
    def analyze_text(self, text: str) -> Dict:
        """Analyze text for profanity and prepare it for sentiment analysis."""
        if not self.initialized:
            raise TextAnalysisError("TextAnalyzer not initialized")
            
        text = self.del_emoji(text)
        profanity_result = self.analyze_profanity(text)
        
        return {
            'text_clean': text,
            'profanity_result': profanity_result,
            'is_acceptable': self._is_text_acceptable(profanity_result)
        }

    def _is_text_acceptable(self, profanity_result: str) -> bool:
        """Determine if text is acceptable based on profanity analysis."""
        return profanity_result in [
            "6 swear words or less",
            "Lyrics go to NLP model"
        ]

    @staticmethod
    def _create_emoji_unicode_ranges() -> Set[int]:
        """Create a set of Unicode ranges for emojis and special characters."""
        ranges = [
            (0x1F600, 0x1F64F),  # emoticons
            (0x1F300, 0x1F5FF),  # symbols & pictographs
            (0x1F680, 0x1F6FF),  # transport & map symbols
            (0x1F1E0, 0x1F1FF),  # flags (iOS)
            (0x2702, 0x27B0),
            (0x24C2, 0x1F251),
            (0x1F926, 0x1F937),
            (0x10000, 0x10FFFF),
            (0x2640, 0x2642),
            (0x2600, 0x2B55),
            (0x200d, 0x200d),
            (0x23cf, 0x23cf),
            (0x23e9, 0x23e9),
            (0x231a, 0x231a),
            (0xfe0f, 0xfe0f),
            (0x3030, 0x3030)
        ]
        return {code_point for start, end in ranges for code_point in range(start, end + 1)}

    def del_emoji(self, text: str) -> str:
        """Remove emojis from text."""
        return ''.join(char for char in text if ord(char) not in self.emoji_unicode_ranges)

    @handle_exceptions
    def analyze_profanity(self, text: str) -> str:
        """Analyze text for profanity in both Polish and English."""
        text_lower = text.lower()
        
        profanity_pl = self._count_occurrences(text_lower, self.profanity_pl_automaton)
        profanity_en = self._count_occurrences(text_lower, self.profanity_en_automaton)
        
        total_count = sum(profanity_pl.values()) + sum(profanity_en.values())
        
        if total_count == 0:
            return "Lyrics go to NLP model"
        elif total_count <= 6 and not profanity_pl:
            return "6 swear words or less"
        else:
            return "Too many swear words"

    def _count_occurrences(self, text: str, automaton: Automaton) -> Dict[str, int]:
        """Count occurrences of profane words using Aho-Corasick algorithm."""
        counts = {}
        for end_index, word in automaton.iter(text):
            start_index = end_index - len(word) + 1
            if self._is_whole_word(text, start_index, end_index):
                counts[word] = counts.get(word, 0) + 1
        return counts

    @staticmethod
    def _is_whole_word(text: str, start: int, end: int) -> bool:
        """Check if the matched word is a whole word."""
        before = text[start - 1] if start > 0 else ' '
        after = text[end + 1] if end < len(text) - 1 else ' '
        return not (before.isalnum() or after.isalnum())

    def _load_words_into_automaton(self, filename: str, automaton: Automaton) -> None:
        """Load words from file into Aho-Corasick automaton."""
        try:
            with open(filename, "r", encoding='utf-8') as file:
                for line in file:
                    word = line.strip().lower()
                    automaton.add_word(word, word)
            automaton.make_automaton()
        except Exception as e:
            logger.error(f"Error loading profanity file {filename}: {e}")
            raise