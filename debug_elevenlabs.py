#!/usr/bin/env python3
"""
Debug script to test ElevenLabs in Railway deployment
"""

import os
import json

def debug_elevenlabs():
    """Debug ElevenLabs installation and API key"""
    print("🧪 Railway ElevenLabs Debug Test")
    print("=" * 50)

    # Check API key
    api_key = os.getenv('ELEVEN_LABS_API_KEY')
    if api_key:
        print(f"✅ ELEVEN_LABS_API_KEY: Present ({len(api_key)} chars)")
        masked = api_key[:8] + "..." + api_key[-4:] if len(api_key) > 12 else "***"
        print(f"🔑 Masked key: {masked}")
    else:
        print("❌ ELEVEN_LABS_API_KEY: Missing")
        return

    # Check library import
    try:
        import elevenlabs
        print(f"✅ ElevenLabs library imported: {elevenlabs.__version__}")
    except ImportError as e:
        print(f"❌ ElevenLabs import failed: {e}")
        return
    except Exception as e:
        print(f"❌ ElevenLabs error: {e}")
        return

    # Check client initialization
    try:
        from elevenlabs import ElevenLabs
        client = ElevenLabs(api_key=api_key)
        print("✅ ElevenLabs client initialized")
    except Exception as e:
        print(f"❌ ElevenLabs client failed: {e}")
        return

    # Test TTS generation
    try:
        print("🎤 Testing TTS generation...")
        audio = client.text_to_speech.convert(
            text="Hello world test",
            voice_id="1SM7GgM6IMuvQlz2BwM3",
            model_id="eleven_turbo_v2_5",
            output_format="mp3_22050_32"
        )
        audio_bytes = b''.join(chunk for chunk in audio) if hasattr(audio, '__iter__') else audio
        print(f"✅ TTS generation successful: {len(audio_bytes)} bytes")
        return True
    except Exception as e:
        print(f"❌ TTS generation failed: {e}")
        return False

if __name__ == "__main__":
    result = debug_elevenlabs()
    print("\n📊 Test Result:", "PASS" if result else "FAIL")