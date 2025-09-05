import google.generativeai as genai
import os
import numpy as np
import threading
from typing import Tuple
from dotenv import load_dotenv
from flask import Flask, request, jsonify, render_template
from flask_socketio import SocketIO, emit, disconnect
import io
import base64
import wave
try:
    # Import elevenlabs with proper error handling for Railway compatibility
    try:
        from elevenlabs import ElevenLabs
        ELEVENLABS_AVAILABLE = True
    except ImportError:
        # Try alternative import methods
        try:
            from elevenlabs.client import ElevenLabs
            ELEVENLABS_AVAILABLE = True
        except ImportError:
            try:
                import elevenlabs
                ElevenLabs = elevenlabs.ElevenLabs
                ELEVENLABS_AVAILABLE = True
            except ImportError:
                print("⚠️  ElevenLabs library not available - TTS features will be disabled")
                ElevenLabs = None
                ELEVENLABS_AVAILABLE = False
except ImportError:
    # Try alternative import for different versions
    try:
        from elevenlabs.client import ElevenLabs
    except ImportError:
        # For very old versions
        try:
            import elevenlabs
            ElevenLabs = elevenlabs.ElevenLabs
        except ImportError:
            ElevenLabs = None

# Import gTTS for fallback - works reliably on Railway
try:
    from gtts import gTTS
    GTTS_AVAILABLE = True
    print("✅ gTTS imported successfully - available as fallback TTS")
except ImportError:
    GTTS_AVAILABLE = False
    print("⚠️  gTTS import failed - no fallback TTS available")
    gTTS = None
import threading
import time
import numpy as np

class SpeechTranslator:
    def __init__(self, gemini_api_key: str = None):
        """
        Initialize the Speech Translator using Gemini 2.5 Flash for direct audio processing.
        """
        load_dotenv()  # Load environment variables from .env file

        gemini_api_key = gemini_api_key or os.getenv('GOOGLE_API_KEY')
        if not gemini_api_key:
            print("⚠️  WARNING: GOOGLE_API_KEY not found - App will run but AI features disabled")
            self.google_api_available = False
        else:
            try:
                genai.configure(api_key=gemini_api_key)
                print("✅ Gemini 2.5 Flash initialized successfully")
                self.google_api_available = True
            except Exception as e:
                print(f"❌ Gemini API Error: {e}")
                self.google_api_available = False

        # Initialize ElevenLabs for high-quality, low-latency TTS
        elevenlabs_api_key = os.getenv('ELEVEN_LABS_API_KEY')

        print(f"🔍 ELEVEN_LABS_API_KEY status: {'Present' if elevenlabs_api_key else 'Missing'}")
        print(f"🔍 ELEVENLABS_AVAILABLE: {ELEVENLABS_AVAILABLE}")
        print("🌐 Railway deployment startup - checking ElevenLabs...")

        if not ELEVENLABS_AVAILABLE:
            print("❌ ElevenLabs library import failed - TTS features will be disabled")
            self.elevenlabs_api_available = False
        elif not elevenlabs_api_key:
            print("⚠️  WARNING: ELEVEN_LABS_API_KEY not found - TTS features disabled")
            print("💡 For Railway deployment: ensure ELEVEN_LABS_API_KEY is set in your project's environment variables")
            self.elevenlabs_api_available = False
        else:
            try:
                # Mask the API key in logs for security
                masked_key = elevenlabs_api_key[:8] + '...' + elevenlabs_api_key[-4:] if len(elevenlabs_api_key) > 12 else '***'
                print(f"🔑 ElevenLabs API Key loaded: {masked_key}")
                self.elevenlabs_client = ElevenLabs(api_key=elevenlabs_api_key)
                print("✅ ElevenLabs Flash v2.5 TTS initialized successfully")
                self.elevenlabs_api_available = True
                print("🎯 TTS Stack: ElevenLabs (Primary) + gTTS (Fallback)" if GTTS_AVAILABLE else "🎯 TTS Stack: ElevenLabs (Primary) - No fallback available")
            except Exception as e:
                print(f"❌ ElevenLabs API Error: {e}")
                self.elevenlabs_api_available = False

        self.source_language = None

        # Initialize caching for repeated phrases
        from collections import OrderedDict
        self.translation_cache = OrderedDict()
        self.cache_max_size = 50
        self.cache_ttl = 300  # 5 minutes cache TTL
        import time
        self.cache_timestamps = {}

    def _convert_audio_to_wav(self, audio_np: np.ndarray) -> bytes:
        """Convert numpy float32 array to WAV bytes that Gemini can process."""
        # Convert float32 (-1 to 1) to int16 (clipped and scaled)
        audio_int16 = np.clip(audio_np * 32767, -32767, 32767).astype(np.int16)

        # Create WAV buffer in memory
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, 'wb') as wav_file:
            # Parameters for 16kHz mono
            nchannels = 1
            sampwidth = 2  # int16 = 2 bytes
            framerate = 16000
            nframes = len(audio_int16)

            # Set WAV parameters
            wav_file.setnchannels(nchannels)
            wav_file.setsampwidth(sampwidth)
            wav_file.setframerate(framerate)
            wav_file.setnframes(nframes)

            # Write audio data
            wav_file.writeframes(audio_int16.tobytes())

        return wav_buffer.getvalue()

    def process_audio_with_gemini(self, audio_np: np.ndarray) -> Tuple[str, str, str]:
        """
        Process audio directly with Gemini 2.5 Flash.
        Returns: detected_language, transcribed_text, translated_text
        """
        try:
            # Convert audio to WAV format
            wav_bytes = self._convert_audio_to_wav(audio_np)

            print(f"Processing {len(wav_bytes)} bytes of WAV audio with Gemini...")

            # Use Gemini 2.5 Flash with multimodal capabilities
            model = genai.GenerativeModel('gemini-2.0-flash-exp')

            # Process audio with Gemini using direct bytes
            prompt = """Analyze this audio file and provide:
            1. The detected language (2-letter code)
            2. The transcribed text
            3. Translate to the opposite language (if Arabic, translate to English; if other languages, translate to Arabic)

            Return ONLY a JSON object like this: {"language": "ar", "transcription": "...", "translation": "..."}

            Do NOT add any explanation or additional text."""

            # Use Gemini's generate_content with raw audio data
            file_data = {
                'mime_type': 'audio/wav',
                'data': wav_bytes
            }

            response = model.generate_content([file_data, prompt])

            # Parse JSON response
            response_text = response.text.strip()
            print(f"Gemini response: {response_text}")

            # Simple JSON parsing (assuming Gemini follows instructions)
            if response_text.startswith('{') and response_text.endswith('}'):
                try:
                    # Basic JSON parsing
                    result = eval(response_text.replace('true', 'True').replace('false', 'False'))

                    detected_lang = result.get('language', 'unknown')
                    transcribed_text = result.get('transcription', '').strip()
                    translated_text = result.get('translation', '').strip()

                    # Fallback translation logic
                    if detected_lang not in ['ar', 'en']:
                        # If detected language is not Arabic or English, translate to English
                        if translated_text and detected_lang != 'en':
                            pass  # Keep Gemini's translation
                        else:
                            translated_text = transcribed_text  # No translation needed for English input

                    return detected_lang, transcribed_text, translated_text

                except Exception as e:
                    print(f"Failed to parse Gemini response: {e}")

            # Fallback: try to extract info from text response
            lines = [line.strip() for line in response_text.split('\n') if line.strip()]
            detected_lang = 'unknown'
            transcribed_text = ''
            translated_text = ''

            for line in lines:
                if line.startswith('{"language":'):
                    try:
                        result = eval(line)
                        detected_lang = result.get('language', 'unknown')
                        transcribed_text = result.get('transcription', '')
                        translated_text = result.get('translation', '')
                        break
                    except:
                        continue

            if not transcribed_text and response_text:
                # Fallback: assume the entire response is the transcription
                transcribed_text = response_text.strip()

            return detected_lang, transcribed_text, translated_text

        except Exception as e:
            print(f"Gemini audio processing error: {e}")
            return "", "", ""

    def _get_cache_key(self, text: str, target_lang: str) -> str:
        """Generate cache key for translation cache"""
        import hashlib
        key = f"{text.lower().strip()}:{target_lang}"
        return hashlib.md5(key.encode()).hexdigest()[:16]

    def _cleanup_cache(self):
        """Remove expired cache entries and enforce max size"""
        import time
        current_time = time.time()

        # Remove expired entries
        expired_keys = [k for k, v in self.cache_timestamps.items() if current_time - v > self.cache_ttl]

        for k in expired_keys:
            self.translation_cache.pop(k, None)
            self.cache_timestamps.pop(k, None)

        # Enforce max size
        while len(self.translation_cache) > self.cache_max_size:
            oldest_key = next(iter(self.translation_cache))
            self.translation_cache.pop(oldest_key, None)
            self.cache_timestamps.pop(oldest_key, None)

    def _cache_translation(self, text: str, target_lang: str, translation: str):
        """Cache a translation result"""
        import time
        cache_key = self._get_cache_key(text, target_lang)
        self.translation_cache[cache_key] = translation
        self.cache_timestamps[cache_key] = time.time()
        self._cleanup_cache()

    def _get_cached_translation(self, text: str, target_lang: str) -> str:
        """Get cached translation if available and not expired"""
        import time
        cache_key = self._get_cache_key(text, target_lang)
        translation = self.translation_cache.get(cache_key)
        if translation:
            # Check if expired
            timestamp = self.cache_timestamps.get(cache_key)
            if timestamp and time.time() - timestamp <= self.cache_ttl:
                print(f"Using cached translation for: {text}")
                return translation
            else:
                # Expired, remove from cache
                self.translation_cache.pop(cache_key, None)
                self.cache_timestamps.pop(cache_key, None)
        return None

    def _generate_tts(self, text: str, language: str) -> bytes:
        """Generate TTS with ElevenLabs primary + gTTS fallback for Railway compatibility"""
        try:
            # Try ElevenLabs first (higher quality, faster)
            if (hasattr(self, 'elevenlabs_client') and self.elevenlabs_client and
                self.elevenlabs_api_available):
                try:
                    print(f"🎤 Trying ElevenLabs TTS for: '{text}' in {language}")

                    # Map language to appropriate ElevenLabs male voice IDs
                    voice_map = {
                        'en': '21m00Tcm4TlvDq8ikWAM',  # Rachel (female) - clear English voice
                        'ar': '21m00Tcm4TlvDq8ikWAM'   # Rachel - can handle Arabic too
                    }

                    voice_id = voice_map.get(language, voice_map['en'])

                    audio_generator = self.elevenlabs_client.text_to_speech.convert(
                        text=text,
                        voice_id=voice_id,
                        model_id="eleven_turbo_v2_5",
                        output_format="mp3_22050_32"
                    )

                    # Convert to bytes
                    audio_bytes = b''
                    chunk_count = 0
                    for chunk in audio_generator:
                        audio_bytes += chunk
                        chunk_count += 1

                    if len(audio_bytes) > 0:
                        print(f"✅ ElevenLabs TTS generated: {len(audio_bytes)} bytes in {chunk_count} chunks")
                        return audio_bytes
                    else:
                        print("⚠️ ElevenLabs returned empty audio data - falling back to gTTS")
                        raise Exception("Empty audio data")

                except Exception as e:
                    print(f"⚠️ ElevenLabs TTS failed: {e} - trying gTTS fallback")

            # Fallback to gTTS (reliable on Railway)
            if GTTS_AVAILABLE and gTTS:
                try:
                    print(f"🎵 Using gTTS fallback for: '{text}' in {language}")

                    # Map language codes for gTTS
                    tts_lang = 'en' if language == 'en' else 'ar'

                    tts = gTTS(text=text, lang=tts_lang, slow=False)
                    audio_buffer = io.BytesIO()
                    tts.write_to_fp(audio_buffer)
                    audio_bytes = audio_buffer.getvalue()

                    print(f"✅ gTTS generated: {len(audio_bytes)} bytes")
                    return audio_bytes

                except Exception as gtts_error:
                    print(f"❌ gTTS backup also failed: {gtts_error}")

            # Final fallback - return empty (will show error to user)
            print("❌ All TTS services failed - no audio will be generated")
            return b''

        except Exception as e:
            print(f"❌ TTS error: {e}")
            return b''



    def translate_text(self, text: str, target_lang: str = "en") -> str:
        """
        Translate text to target language using Gemini Flash 2.5.
        """
        if not text.strip():
            return ""

        model = genai.GenerativeModel(
            'gemini-2.5-flash',
            system_instruction="You are a professional translator. Provide only the translated text, nothing else. Do not add any explanations, notes, or additional content."
        )
        prompt = f"Translate the following text to {target_lang}:\n\n{text}"
        response = model.generate_content(prompt)
        translated_text = response.text.strip()

        print(f"Translated text: {translated_text}")
        return translated_text

    def text_to_speech(self, text: str, lang: str = "en"):
        """
        Convert translated text to speech using gTTS in a background thread.
        """
        if not text.strip():
            print("No text to speak.")
            return

        # Run TTS in background thread to not block next recording
        threading.Thread(target=self._tts_worker, args=(text, lang), daemon=True).start()

    def _tts_worker(self, text: str, lang: str):
        """Legacy TTS method - now uses ElevenLabs for consistency"""
        try:
            # Use TTS with ElevenLabs + gTTS fallback
            audio_bytes = self._generate_tts(text, lang)
            if audio_bytes:
                # Save and play the audio
                import tempfile
                import subprocess
                with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as temp_file:
                    temp_file.write(audio_bytes)
                    temp_file.flush()
                    print(f"Playing ElevenLabs audio in background...")
                    subprocess.call(['afplay', temp_file.name])  # macOS specific
                    os.unlink(temp_file.name)
        except Exception as e:
            print(f"TTS error: {e}")

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'real-time-translation-secret-key')

# No CORS restrictions - removed for Docker/Simplified deployment
print("🌐 CORS removed - simplified configuration for Docker on port 8080")
allowed_origins = "*"

socketio = SocketIO(
    app,
    cors_allowed_origins="*",  # Allow all origins for WebSocket connections
    ping_timeout=60,
    ping_interval=25,
    async_mode=None  # Use standard mode for Railway compatibility
)

# Global translator instance
translator = None

# Global streaming audio buffer for accumulating chunks
streaming_buffer = []
streaming_audio_data = b''
streaming_last_processed = time.time()
streaming_threshold_samples = 16000 * 2  # 2 seconds at 16kHz

try:
    translator = SpeechTranslator()  # Now uses only Gemini 2.5 Flash for everything
    print("🎙️ SpeechTranslator initialized successfully")
except Exception as e:
    print(f"⚠️ SpeechTranslator initialization failed: {e}")
    print("🚨 This might cause API-related features to fail")
    translator = None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/debug-tts')
def debug_tts():
    """Debug endpoint to test TTS generation directly"""
    if translator is None:
        return jsonify({'error': 'Translator not initialized'})

    test_text = "Hello world"
    print(f"🔍 Debug TTS test with text: '{test_text}'")

    try:
        audio_bytes = translator._generate_tts(test_text, "en")
        result = {
            'test_text': test_text,
            'audio_generated': len(audio_bytes) > 0,
            'audio_bytes': len(audio_bytes),
            'audio_base64_length': len(base64.b64encode(audio_bytes).decode()) if audio_bytes else 0,
            'elevenlabs_available': translator.elevenlabs_api_available,
            'has_client': hasattr(translator, 'elevenlabs_client') and translator.elevenlabs_client is not None,
            'gtts_available': GTTS_AVAILABLE,
            'tts_fallback_available': GTTS_AVAILABLE,
            'tts_service_used': 'gtts' if len(audio_bytes) > 0 and not translator.elevenlabs_api_available else 'elevenlabs'
        }
        import json
        print(f"🔍 Debug result: {json.dumps(result, indent=2)}")
        return jsonify(result)
    except Exception as e:
        print(f"❌ Debug TTS error: {e}")
        return jsonify({'error': str(e)})

@app.route('/status')
def get_status():
    if translator is None:
        return jsonify({
            'status': 'running',
            'models_loaded': {
                'gemini': 'not_initialized',
                'elevenlabs': 'not_initialized'
            },
            'cache_size': 0,
            'initialization_error': True
        })

    return jsonify({
        'status': 'running',
        'models_loaded': {
            'gemini': '2.5-flash' if translator.google_api_available else 'not_configured',
            'elevenlabs': 'flash-v2.5' if translator.elevenlabs_api_available else 'not_configured',
            'gtts': 'available' if GTTS_AVAILABLE else 'not_available'
        },
        'cache_size': len(translator.translation_cache) if hasattr(translator, 'translation_cache') else 0,
        'debug_info': {
            'elevenlabs_initialized': translator.elevenlabs_api_available,
            'elevenlabs_client_exists': hasattr(translator, 'elevenlabs_client') and translator.elevenlabs_client is not None,
            'py_version': __import__('sys').version.split()[0],
            'timestamp': __import__('time').time()
        }
    })

# WebSocket event handlers for real-time streaming
@socketio.on('connect')
def handle_connect():
    print('Client connected to WebSocket')
    emit('status', {'message': 'Connected to real-time streaming server'})

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected from WebSocket')

@socketio.on('start_streaming')
def handle_start_streaming():
    global streaming_buffer, streaming_audio_data, streaming_last_processed
    print('Client started WebSocket streaming mode')
    # Reset streaming buffers
    streaming_buffer = []
    streaming_audio_data = b''
    streaming_last_processed = time.time()
    emit('streaming_started', {'message': 'Real-time WebSocket streaming active'})

@socketio.on('audio_chunk')
def handle_audio_chunk(data):
    """Handle real-time audio chunks from WebSocket client - accumulate and process"""
    global streaming_buffer, streaming_audio_data, streaming_last_processed, streaming_threshold_samples

    try:
        # Check if translator is available
        if translator is None:
            emit('error', {'message': 'Translator not initialized. Check API keys.'})
            return

        # Decode the base64 audio data
        if 'audio' in data:
            print(f"📥 Received streaming audio chunk: {len(data['audio'])} chars")
            # Convert base64 audio chunk to float32 array
            audio_bytes = base64.b64decode(data['audio'])
            audio_np = np.frombuffer(audio_bytes, dtype=np.float32).copy()
            print(f"🔧 Decoded audio chunk: {len(audio_np)} samples")

            # Accumulate audio data
            if len(streaming_buffer) == 0:
                streaming_buffer = audio_np.tolist()
            else:
                streaming_buffer.extend(audio_np.tolist())

            print(f"📊 Streaming buffer now: {len(streaming_buffer)} samples")

            # Convert accumulated data to numpy array for processing
            streaming_audio_data = np.array(streaming_buffer, dtype=np.float32)

            # Process only if we have enough data and it's been a while since last processing
            current_time = time.time()
            has_enough_data = len(streaming_buffer) >= streaming_threshold_samples
            time_since_last_processed = current_time - streaming_last_processed

            if has_enough_data and time_since_last_processed > 1.5:  # Process every 1.5 seconds
                print(f"📊 Processing accumulated streaming audio: {len(streaming_audio_data)} samples")

                # Process with Gemini for transcription and translation
                detected_lang, transcribed_text, translated_text = translator.process_audio_with_gemini(streaming_audio_data)

                # Generate TTS if we have translation
                audio_base64 = ""
                if translated_text:
                    print(f"🎤 Generating TTS for streaming translation: '{translated_text}'")
                    audio_bytes = translator._generate_tts(translated_text, "ar" if detected_lang == "en" else "en")
                    audio_base64 = base64.b64encode(audio_bytes).decode()

                # Send real-time result back to client via WebSocket
                if transcribed_text or translated_text:
                    emit('translation_result', {
                        'original_language': detected_lang,
                        'transcribed_text': transcribed_text,
                        'translated_language': "ar" if detected_lang == "en" else "en",
                        'translated_text': translated_text,
                        'audio_data': audio_base64,
                        'streaming': True,
                        'timestamp': time.time()
                    })

                    print(f"✅ Streaming result sent: {transcribed_text} → {translated_text}")

                # Reset for next processing window
                streaming_last_processed = current_time
                streaming_buffer = []
                streaming_audio_data = b''

            else:
                # Send status update indicating buffering
                if len(streaming_buffer) > 0:
                    buffer_seconds = len(streaming_buffer) / 16000
                    emit('streaming_status', {
                        'message': f'Buffering audio... {buffer_seconds:.1f}s recorded',
                        'buffer_size': len(streaming_buffer),
                        'timestamp': time.time()
                    })

    except Exception as e:
        print(f"WebSocket audio processing error: {e}")
        emit('error', {'message': f'Processing error: {str(e)}'})

@socketio.on('stop_streaming')
def handle_stop_streaming():
    global streaming_buffer, streaming_audio_data, streaming_last_processed
    print('Client stopped WebSocket streaming mode')
    print(f'Final audio buffer size: {len(streaming_buffer)} samples')

    # Process any remaining audio before stopping
    if len(streaming_buffer) > 0:
        try:
            # Convert accumulated data to numpy array
            streaming_audio_data = np.array(streaming_buffer, dtype=np.float32)
            print(f"📊 Processing final streaming audio: {len(streaming_audio_data)} samples")

            # Process with Gemini
            detected_lang, transcribed_text, translated_text = translator.process_audio_with_gemini(streaming_audio_data)

            # Generate TTS if we have translation
            audio_base64 = ""
            if translated_text:
                audio_bytes = translator._generate_tts(translated_text, "ar" if detected_lang == "en" else "en")
                audio_base64 = base64.b64encode(audio_bytes).decode()

            # Send final result
            emit('translation_result', {
                'original_language': detected_lang,
                'transcribed_text': transcribed_text,
                'translated_language': "ar" if detected_lang == "en" else "en",
                'translated_text': translated_text,
                'audio_data': audio_base64,
                'streaming': False,
                'final_result': True,
                'timestamp': time.time()
            })

        except Exception as e:
            print(f"Error processing final streaming audio: {e}")

    # Reset streaming buffers
    streaming_buffer = []
    streaming_audio_data = b''
    streaming_last_processed = time.time()

    emit('streaming_stopped', {'message': 'Real-time WebSocket streaming stopped'})

@app.route('/translate', methods=['POST'])
def translate_audio():
    try:
        # Check if translator is initialized
        if translator is None:
            return jsonify({
                'error': 'Translator not initialized. App is starting up.',
                'initialization_error': True
            }), 503

        # Get audio data from request (raw float32 buffer)
        audio_data = request.data

        if not audio_data:
            return jsonify({'error': 'No audio data received'}), 400

        if len(audio_data) < 1600:  # Minimum 100ms at 16kHz (4 bytes per sample)
            return jsonify({'error': 'Audio data too short. Please record longer.'}), 400

        if len(audio_data) > 500000:  # Maximum ~30 seconds at 16kHz
            return jsonify({'error': 'Audio data too long. Please record shorter clips.'}), 400

        if len(audio_data) % 4 != 0:  # Float32 = 4 bytes per sample
            return jsonify({'error': f'Invalid audio data size: {len(audio_data)} bytes (must be multiple of 4)'}), 400

        # Convert to numpy array with proper error handling
        try:
            audio_np = np.frombuffer(audio_data, dtype=np.float32).copy()
            print(f"Received audio data: {len(audio_np)} samples ({len(audio_data)} bytes)")
        except Exception as convert_error:
            return jsonify({'error': f'Audio data conversion failed: {str(convert_error)}'}), 400

        # Basic voice activity detection - trim leading/trailing silence
        if len(audio_np) > 16000:  # Minimum 1 second of audio
            # Find first non-silence sample (energy above threshold)
            threshold = np.percentile(np.abs(audio_np), 10)  # Dynamic threshold
            if threshold < 0.01:  # Minimum threshold
                threshold = 0.01

            # Trim leading silence
            silence_mask = np.abs(audio_np) < threshold
            first_speech_idx = np.where(~silence_mask)[0]
            if len(first_speech_idx) > 0:
                start_idx = max(0, first_speech_idx[0] - 1600)  # Include 100ms before
                audio_np = audio_np[start_idx:]

        print(f"Processing audio with {len(audio_np)} samples...")

        # Process audio directly with Gemini (transcription + translation)
        if not translator.google_api_available:
            return jsonify({
                'error': 'Google Gemini API not configured. Please set GOOGLE_API_KEY in Railway environment variables.',
                'setup_instructions': 'Add GOOGLE_API_KEY to Railway project variables. Get key from https://aistudio.google.com/app/apikey'
            }), 500

        detected_lang, transcribed_text, translated_text = translator.process_audio_with_gemini(audio_np)

        if not transcribed_text:
            return jsonify({'error': 'No speech detected'}), 200

        # Determine target language based on detected language
        translated_lang = "en" if detected_lang == "ar" else "ar"

        # Generate high-quality audio with TTS (ElevenLabs + gTTS fallback)
        if translated_text:
            audio_bytes = translator._generate_tts(translated_text, translated_lang)
            if len(audio_bytes) == 0:
                print("⚠️ ElevenLabs TTS returned empty audio data")
            else:
                print(f"📦 Generated audio: {len(audio_bytes)} bytes")
        else:
            audio_bytes = b''  # Empty audio if TTS not available
            if not translator.elevenlabs_api_available:
                print("❌ TTS not available - ElevenLabs API not configured")
            else:
                print("ℹ️ No translated text to generate audio for")

        # Convert to base64 for client
        audio_base64 = base64.b64encode(audio_bytes).decode()
        print(f"🔧 Base64 audio length: {len(audio_base64)} characters")

        print(f"✅ Translated: '{transcribed_text}' → '{translated_text}'")

        return jsonify({
            'original_language': detected_lang,
            'transcribed_text': transcribed_text,
            'translated_language': translated_lang,
            'translated_text': translated_text,
            'audio_data': audio_base64
        })

    except Exception as e:
        print(f"Error processing audio: {e}")
        return jsonify({'error': f'Processing failed: {str(e)}'}), 500

if __name__ == "__main__":
    # Use environment variables for Railway deployment
    port = int(os.getenv('PORT', 8080))
    debug = os.getenv('FLASK_ENV') == 'development'

    socketio.run(
        app,
        debug=debug,
        host='0.0.0.0',
        port=port,
        allow_unsafe_werkzeug=debug  # Only enable in development
    )