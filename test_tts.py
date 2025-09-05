#!/usr/bin/env python3
"""
Test script to debug TTS issues in Railway deployment
"""

import os
import requests
import json
import base64
import numpy as np

def test_tts_logs():
    """Test TTS generation and check logs"""

    # Generate test audio data
    audio_samples = np.random.randn(16000).astype(np.float32) * 0.01
    audio_bytes = audio_samples.tobytes()

    print(f"🎤 Testing TTS with {len(audio_bytes)} bytes of audio data")
    print(f"📊 Audio shape: {audio_samples.shape}")
    print(f"🎼 Audio sample values: min={audio_samples.min():.4f}, max={audio_samples.max():.4f}")

    try:
        # Make request to Railway deployment
        url = "https://ai-translate-ai-translator.up.railway.app/translate"
        headers = {
            'Content-Type': 'application/octet-stream',
            'User-Agent': 'TTS-Test/1.0'
        }

        print(f"🌐 Making POST request to: {url}")

        response = requests.post(url, data=audio_bytes, headers=headers, timeout=30)

        print(f"📡 Response status: {response.status_code}")
        print(f"⏱️ Response time: {response.elapsed.total_seconds()}s")

        if response.status_code == 200:
            result = response.json()
            print("✅ Request successful:")
            print(json.dumps(result, indent=2, ensure_ascii=False))

            # Check audio data
            audio_data = result.get('audio_data', '')
            if audio_data:
                audio_bytes_len = len(audio_data)
                print(f"🎵 Audio data length: {audio_bytes_len} characters")
                print(f"📦 Decoded audio length: {len(base64.b64decode(audio_data))} bytes")
            else:
                print("❌ No audio data in response")

        else:
            print(f"❌ Request failed: {response.status_code}")
            print(f"📄 Error response: {response.text}")

    except Exception as e:
        print(f"💥 Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_tts_logs()