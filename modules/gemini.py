import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import base64
import json
import logging
from typing import Optional, Dict, Any
from .decorators import handle_exceptions, log_errors

logger = logging.getLogger(__name__)

class BaseGeminiAPI:
    def __init__(self, api_key: str, model: str, prompt: str):
        self.api_key = api_key
        self.model = model
        self.prompt = prompt
        self.model_instance = None
        self._init_model()
        
    @handle_exceptions
    def _init_model(self):
        """Initialize the Gemini model."""
        genai.configure(api_key=self.api_key)
        print(self.prompt)
        self.model_instance = genai.GenerativeModel(self.model, system_instruction=self.prompt)
        
    def _get_safety_settings(self):
        """Get default safety settings."""
        return {
            category: HarmBlockThreshold.BLOCK_NONE
            for category in HarmCategory
        }
        
    def _convert_audio_to_base64(self, audio_path: str) -> Optional[str]:
        """Convert audio file to base64 string."""
        try:
            with open(audio_path, 'rb') as audio_file:
                audio_bytes = audio_file.read()
                base64_audio = base64.b64encode(audio_bytes).decode('utf-8')
                return base64_audio
        except Exception as e:
            logger.error(f"Error converting audio to base64: {e}")
            return None


class TranscriptAPI(BaseGeminiAPI):
    @log_errors
    def analyze_audio(self, audio_path: str) -> Optional[str]:
        """Analyze audio file and return transcript."""
        if not self.model_instance:
            logger.error("Model not initialized")
            return None
            
        base64_audio = self._convert_audio_to_base64(audio_path)
        if not base64_audio:
            return None
        try:
            response = self._generate_response(base64_audio, audio_path)
            logger.info(f"Generated response: {response.text[:20]}")
            return response.text if response else None
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return None
        
    @handle_exceptions
    def _generate_response(self, base64_audio: str, audio_path: str):
        """Generate response from Gemini model for audio transcript."""

        mime_type = "audio/mp3" if audio_path.endswith(".mp3") else "audio/webm"
        for attempt in range(3):
            try:
                response = self.model_instance.generate_content(
                [
                    {"text": "."},
                    {"mime_type": mime_type, "data": base64_audio}
                ],
                safety_settings={
                    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE
                }
            )
                if response and response.text:
                    return response
                logger.warning(f"Empty response on attempt {attempt + 1}")
            except Exception as e:
                logger.error(f"Error on attempt {attempt + 1}: {e}")
                
        return None


class SentimentAPI(BaseGeminiAPI):
    @log_errors
    def analyze_sentiment(self, text: str) -> Optional[Dict[str, Any]]:
        """Analyze sentiment of given text."""
        if not self.model_instance:
            logger.error("Model not initialized")
            return None
            
        response = self._generate_response(text)
        return self._parse_response(response) if response else None
        
    @handle_exceptions
    def _generate_response(self, text: str):
        """Generate response from Gemini model for sentiment analysis."""
        
        for attempt in range(3):
            try:
                response = self.model_instance.generate_content(text)
                if response and response.text:
                    return response
                logger.warning(f"Empty response on attempt {attempt + 1}")
            except Exception as e:
                logger.error(f"Error on attempt {attempt + 1}: {e}")
                
        return None
        
    @handle_exceptions
    def _parse_response(self, response) -> Optional[Dict[str, Any]]:
        """Parse the response from Gemini model."""
        try:
            # Extract JSON from response text
            json_str = response.text.strip()
            if '{' in json_str and '}' in json_str:
                json_str = json_str[json_str.find('{'):json_str.rfind('}')+1]
                result = json.loads(json_str)
                
                # Validate response structure
                if 'sentiment' in result and 'confidence' in result:
                    logger.info(f"Parsed response: {result}")
                    return {
                        'is_safe_for_radio': result['is_safe_for_radio'],
                        'confidence': float(result['confidence']),
                        'raw_response': result
                    }
                else:
                    logger.warning("Invalid response structure")
                    return None
            else:
                logger.warning("No JSON found in response")
                return None
                
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing JSON content: {e}")
            return None
        except Exception as e:
            logger.error(f"Error processing response: {e}")
            return None


    def _validate_response(self, response_dict: Dict) -> bool:
        """Validate the structure of the response dictionary."""
        required_keys = {'sentiment', 'confidence'}
        if not all(key in response_dict for key in required_keys):
            logger.warning(f"Missing required keys in response. Found: {response_dict.keys()}")
            return False
            
        try:
            sentiment = str(response_dict['sentiment']).lower()
            confidence = float(response_dict['confidence'])
            
            if sentiment not in {'positive', 'negative', 'neutral'}:
                logger.warning(f"Invalid sentiment value: {sentiment}")
                return False
                
            if not (0 <= confidence <= 1):
                logger.warning(f"Confidence out of range: {confidence}")
                return False
                
            return True
            
        except (ValueError, TypeError) as e:
            logger.error(f"Error validating response values: {e}")
            return False