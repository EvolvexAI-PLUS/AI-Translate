#!/usr/bin/env python3
"""
Enhanced Speech Service with Google STT + Gemini Translation
Separates STT (synchronous chunks) from Translation (batched processing)
"""

import os
import asyncio
import json
import threading
import time
from typing import Dict, List, Optional, Callable, Tuple
import base64
import numpy as np
import io
import wave
from google.cloud import speech
from google.api_core.exceptions import GoogleAPIError
# google.auth.exceptions as ga_exceptions removed - not used in current implementation
import nltk
from nltk.tokenize import sent_tokenize
import google.generativeai as genai
from dotenv import load_dotenv
import queue

# Load environment variables
load_dotenv()

class SpeechToTextService:
    """Google STT Service for synchronous audio transcription"""

    def __init__(self):
        self.client = None
        self.sample_rate = 16000
        self.recognition_config = None

    def initialize(self):
        """Initialize Google STT client synchronously"""
        try:
            # Check for Google Cloud credentials from individual environment variables (Railway)
            google_cloud_type = os.getenv('type')
            google_cloud_project_id = os.getenv('project_id')
            google_app_creds_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')

            if google_cloud_type and google_cloud_project_id:
                # Reconstruct credentials from individual Railway environment variables
                try:
                    credentials_info = {
                        "type": os.getenv('type', 'service_account'),
                        "project_id": os.getenv('project_id'),
                        "private_key_id": os.getenv('private_key_id'),
                        "private_key": os.getenv('private_key'),
                        "client_email": os.getenv('client_email'),
                        "client_id": os.getenv('client_id'),
                        "auth_uri": os.getenv('auth_uri', 'https://accounts.google.com/o/oauth2/auth'),
                        "token_uri": os.getenv('token_uri', 'https://oauth2.googleapis.com/token'),
                        "auth_provider_x509_cert_url": os.getenv('auth_provider_x509_cert_url'),
                        "client_x509_cert_url": os.getenv('client_x509_cert_url'),
                        "universe_domain": os.getenv('universe_domain', 'googleapis.com')
                    }

                    from google.oauth2 import service_account
                    credentials = service_account.Credentials.from_service_account_info(credentials_info)
                    print("✅ Using Google Cloud credentials from RAILWAY individual environment variables")
                    print(f"📋 Project ID: {credentials_info['project_id']}")
                    print(f"📋 Client Email: {credentials_info['client_email']}")
                except Exception as e:
                    print(f"❌ Failed to create credentials from Railway environment variables: {e}")
                    print("📕 Required environment variables: type, project_id, private_key_id, private_key, client_email")
                    credentials = None
            elif google_app_creds_path:
                # Use file path credentials (local development)
                print(f"📁 Using Google Cloud credentials from file: {google_app_creds_path}")
                credentials = None  # Let google.auth auto-detect from file
            else:
                print("⚠️  No Google Cloud credentials found - trying auto-detection")
                credentials = None

            # Initialize client with credentials if available
            if credentials:
                self.client = speech.SpeechClient(credentials=credentials)
                print("✅ Google STT client initialized with explicit Railway credentials")
            else:
                self.client = speech.SpeechClient()
                print("✅ Google STT client initialized (credentials auto-detected)")

            # Configure recognition settings
            self.recognition_config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=self.sample_rate,
                language_code="ar-SA",  # Primary Arabic
                alternative_language_codes=["en-US"],  # Fallback English
                enable_automatic_punctuation=True,
                enable_word_time_offsets=True,
            )
            print("✅ Google STT client initialized with Arabic/English support")
        except Exception as e:
            print(f"❌ Failed to initialize Google STT: {e}")
            print("📋 Environment variables check:")
            print(f"📋 type present: {bool(os.getenv('type'))}")
            print(f"📋 project_id present: {bool(os.getenv('project_id'))}")
            print(f"📋 GOOGLE_APPLICATION_CREDENTIALS present: {bool(os.getenv('GOOGLE_APPLICATION_CREDENTIALS'))}")
            self.client = None

    def convert_audio_to_wav(self, audio_np: np.ndarray) -> bytes:
        """Convert numpy float32 array to WAV bytes for Google STT"""
        if audio_np is None or len(audio_np) == 0:
            return b''

        # Convert float32 (-1 to 1) to int16 (clipped and scaled)
        audio_int16 = np.clip(audio_np * 32767, -32767, 32767).astype(np.int16)

        # Create WAV buffer in memory
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, 'wb') as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # int16 = 2 bytes
            wav_file.setframerate(self.sample_rate)
            wav_file.setnframes(len(audio_int16))
            wav_file.writeframes(audio_int16.tobytes())

        return wav_buffer.getvalue()

    def transcribe_audio_chunk(self, audio_np: np.ndarray) -> Tuple[str, str]:
        """
        Transcribe audio chunk using Google STT
        Returns: (transcription_text, detected_language)
        """
        try:
            if not self.client or audio_np is None or len(audio_np) == 0:
                return "", ""

            # Convert to WAV format
            wav_bytes = self.convert_audio_to_wav(audio_np)
            if not wav_bytes:
                return "", ""

            # Create audio content
            audio = speech.RecognitionAudio(content=wav_bytes)

            # Perform recognition
            response = self.client.recognize(config=self.recognition_config, audio=audio)

            if response.results and response.results[0].alternatives:
                result = response.results[0]
                transcript = result.alternatives[0].transcript.strip()
                language = result.language_code

                print(f"🎯 Google STT: '{transcript}' (language: {language})")
                return transcript, language
            else:
                return "", ""

        except Exception as e:
            print(f"❌ Google STT error: {e}")
            return "", ""

class EnhancedSpeechTranslator:
    """Enhanced translator that accepts text input and manages translation queue"""

    def __init__(self):
        self.translation_queue = asyncio.Queue()
        self.processing_results = {}
        self.genai_client = None
        self.nltk_initialized = False

        # Initialize Gemini
        genai_api_key = os.getenv('GOOGLE_API_KEY')
        if genai_api_key:
            genai.configure(api_key=genai_api_key)
            self.genai_client = genai.GenerativeModel('gemini-2.5-flash')
            print("✅ Gemini client initialized for translations")
        else:
            print("⚠️  GOOGLE_API_KEY not found - translation features disabled")

        # Initialize NLTK for sentence detection
        try:
            nltk.download('punkt', quiet=True)
            self.nltk_initialized = True
            print("✅ NLTK initialized for sentence detection")
        except Exception as e:
            print(f"⚠️  NLTK initialization failed: {e}")

    def add_transcription(self, text: str, is_final: bool, source_lang: str = "ar"):
        """Add transcription to translation queue"""
        if is_final and text.strip():
            self.translation_queue.put_nowait({
                "text": text,
                "source_lang": source_lang,
                "timestamp": time.time()
            })

    async def process_translation_queue(self) -> Optional[Dict]:
        """Process next translation from queue"""
        try:
            if self.translation_queue.empty():
                return None

            # Get next transcription
            item = self.translation_queue.get_nowait()
            text = item["text"]
            source_lang = item["source_lang"]

            if not text or not self.genai_client:
                return None

            # Determine target language (handle Arabic dialects)
            is_arabic = source_lang.startswith("ar") if source_lang else False
            normalized_source = "ar" if is_arabic else "en"
            target_lang = "en" if is_arabic else ("ar" if source_lang.startswith("en") else "en")

            # Generate translation using Gemini
            prompt = f"""
            Translate the following text from {normalized_source} to {target_lang}.
            Provide only the translated text without any additional explanations or notes.
            Text to translate: "{text}"
            """

            response = await asyncio.to_thread(
                self.genai_client.generate_content,
                prompt
            )

            translated_text = response.text.strip()

            result = {
                "original_text": text,
                "translated_text": translated_text,
                "source_language": source_lang,
                "target_language": target_lang,
                "confidence": 1.0  # Could be enhanced with Gemini confidence
            }

            return result

        except Exception as e:
            print(f"❌ Translation processing error: {e}")
            return None

class RealTimeTranslationSystem:
    """Synchronous system integrating STT and Translation services"""

    def __init__(self):
        self.stt_service = SpeechToTextService()
        self.translator = None  # Will be initialized with Gemini
        self.is_running = False

        # Initialize Gemini directly
        genai_api_key = os.getenv('GOOGLE_API_KEY')
        if genai_api_key:
            genai.configure(api_key=genai_api_key)
            self.translator = genai.GenerativeModel('gemini-2.5-flash')
            print("✅ Gemini translator initialized")
        else:
            print("⚠️  GOOGLE_API_KEY not found - translation features disabled")

        # Initialize ElevenLabs for TTS
        self.elevenlabs_client = None
        elevenlabs_api_key = os.getenv('ELEVEN_LABS_API_KEY')
        if elevenlabs_api_key:
            try:
                from elevenlabs import ElevenLabs
                self.elevenlabs_client = ElevenLabs(api_key=elevenlabs_api_key)
                print("✅ ElevenLabs TTS initialized")
            except Exception as e:
                print(f"⚠️ ElevenLabs TTS failed: {e}")

        # gTTS fallback
        self.gtts_available = False
        try:
            from gtts import gTTS
            self.gtts_available = True
            print("✅ gTTS fallback initialized")
        except:
            print("⚠️ gTTS fallback not available")

    def initialize(self):
        """Initialize the entire system synchronously"""
        try:
            print("🔄 Initializing Google STT...")
            self.stt_service.initialize()
            print("✅ Google STT initialized")

            print("🔄 Initializing Gemini translator...")
            genai_api_key = os.getenv('GOOGLE_API_KEY')
            print(f"🔑 Gemini API key detected: {'Yes' if genai_api_key else 'No'}")
            if genai_api_key:
                print(f"🔑 API key prefix: {genai_api_key[:10]}...")
                try:
                    print("🔗 Configuring Gemini API...")
                    genai.configure(api_key=genai_api_key)
                    print("✅ Gemini API configured")

                    print("🤖 Initializing Gemini model...")
                    self.translator = genai.GenerativeModel('gemini-2.5-flash')
                    print("✅ Gemini model initialized")

                    # Test API connectivity
                    print("🧪 Testing Gemini API connection...")
                    test_response = self.translator.generate_content("Hello")
                    print(f"✅ Gemini API test successful (response length: {len(test_response.text.strip())} chars)")
                    print(f"🧪 Test response: '{test_response.text.strip()}'")

                except Exception as e:
                    print(f"❌ Gemini initialization failed: {e}")
                    print(f"❌ Error type: {type(e).__name__}")
                    self.translator = None

            print("🔄 Initializing ElevenLabs...")
            elevenlabs_api_key = os.getenv('ELEVEN_LABS_API_KEY')
            print(f"🔑 ElevenLabs API key detected: {'Yes' if elevenlabs_api_key else 'No'}")
            if elevenlabs_api_key:
                try:
                    from elevenlabs import ElevenLabs
                    self.elevenlabs_client = ElevenLabs(api_key=elevenlabs_api_key)
                    print("✅ ElevenLabs initialized")
                except Exception as e:
                    print(f"❌ ElevenLabs initialization failed: {e}")
                    self.elevenlabs_client = None

            print("🔄 Checking gTTS availability...")
            try:
                from gtts import gTTS
                self.gtts_available = True
                print("✅ gTTS available")
            except Exception as e:
                print(f"⚠️ gTTS not available: {e}")
                self.gtts_available = False

            self.is_running = True
            print("🎯 Real-time translation system initialized")
            return True
        except Exception as e:
            print(f"❌ System initialization failed: {e}")
            print(f"❌ Error type: {type(e).__name__}")
            return False

    def transcribe_and_translate(self, audio_np: np.ndarray) -> Tuple[str, str, str, str]:
        """
        Complete pipeline: STT → Translation → TTS
        Returns: (transcribed_text, translated_text, source_lang, target_lang)
        """
        if not self.is_running:
            return "", "", "", ""

        try:
            # Step 1: Transcribe using Google STT
            transcript, source_lang = self.stt_service.transcribe_audio_chunk(audio_np)

            if not transcript:
                return "", "", "", ""

            # Step 2: Translate using Gemini (handle Arabic dialects)
            is_arabic = source_lang.startswith("ar") if source_lang else False
            normalized_source = "ar" if is_arabic else "en"
            target_lang = "en" if is_arabic else ("ar" if source_lang.startswith("en") else "en")

            if self.translator:
                prompt = f"""
                Translate the following text from {normalized_source} to {target_lang}.
                Provide only the translated text without any additional explanations or notes.
                Text to translate: "{transcript}"
                """

                response = self.translator.generate_content(prompt)
                translated_text = response.text.strip()
                print(f"🎯 Translation: '{transcript}' ({source_lang}) → '{translated_text}' ({target_lang})")
            else:
                translated_text = transcript  # No translation available

            return transcript, translated_text, source_lang, target_lang

        except Exception as e:
            print(f"❌ Pipeline error: {e}")
            return "", "", "", ""

    def _generate_tts(self, text: str, language: str) -> bytes:
        """Generate TTS with ElevenLabs primary + gTTS fallback"""
        try:
            # Try ElevenLabs first
            if self.elevenlabs_client:
                try:
                    print(f"🎤 ElevenLabs TTS for: '{text}' in {language}")

                    voice_map = {
                        'en': '21m00Tcm4TlvDq8ikWAM',  # Rachel (English)
                        'ar': '21m00Tcm4TlvDq8ikWAM'   # Rachel (works for both)
                    }

                    voice_id = voice_map.get(language, voice_map['en'])

                    audio_generator = self.elevenlabs_client.text_to_speech.convert(
                        text=text,
                        voice_id=voice_id,
                        model_id="eleven_turbo_v2_5",
                        output_format="mp3_22050_32"
                    )

                    audio_bytes = b''
                    for chunk in audio_generator:
                        audio_bytes += chunk

                    if audio_bytes:
                        print(f"✅ ElevenLabs TTS: {len(audio_bytes)} bytes")
                        return audio_bytes
                    else:
                        raise Exception("Empty audio data")

                except Exception as e:
                    print(f"⚠️ ElevenLabs TTS failed: {e}")

            # Fallback to gTTS
            if self.gtts_available:
                try:
                    print(f"🎵 gTTS fallback for: '{text}' in {language}")
                    from gtts import gTTS
                    import io

                    tts_lang = 'en' if language == 'en' else 'ar'
                    tts = gTTS(text=text, lang=tts_lang, slow=False)
                    audio_buffer = io.BytesIO()
                    tts.write_to_fp(audio_buffer)
                    audio_bytes = audio_buffer.getvalue()

                    print(f"✅ gTTS: {len(audio_bytes)} bytes")
                    return audio_bytes

                except Exception as e:
                    print(f"❌ gTTS failed: {e}")

            # Final fallback
            print("❌ All TTS services failed")
            return b''

        except Exception as e:
            print(f"❌ TTS error: {e}")
            return b''

    def stop_system(self):
        """Stop the translation system"""
        self.is_running = False
        print("🛑 Real-time translation system stopped")

# Global system instance
translation_system = RealTimeTranslationSystem()

def init_translation_system():
    """Initialize the entire translation system synchronously"""
    return translation_system.initialize()

if __name__ == "__main__":
    # Test the system
    init_translation_system()