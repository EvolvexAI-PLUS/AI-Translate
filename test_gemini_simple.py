#!/usr/bin/env python3
"""
Simple test script for Gemini 2.5 Flash API
Tests basic connectivity and response generation
"""

import os
from dotenv import load_dotenv
import google.generativeai as genai

def test_gemini_api():
    """Test Gemini API connectivity with a simple prompt"""

    try:
        # Load environment variables
        load_dotenv()
        print("🔄 Loading environment variables...")

        # Get API key
        api_key = os.getenv('GOOGLE_API_KEY')
        if not api_key:
            print("❌ GOOGLE_API_KEY not found in environment")
            return False

        print(f"🔑 Found API key (starts with: {api_key[:15]}...)")

        # Configure Gemini
        print("🔗 Configuring Gemini API...")
        genai.configure(api_key=api_key)

        # Create model
        print("🤖 Creating Gemini 2.5 Flash model...")
        model = genai.GenerativeModel('gemini-2.5-flash')

        # Test API call
        print("🧪 Testing API call with simple prompt...")
        test_prompt = "Say hello in French and English. Keep it very short."

        response = model.generate_content(test_prompt)

        if response and response.text:
            print("✅ Gemini API test successful!")
            print(f"📝 Response: {response.text.strip()}")
            print(f"📊 Response length: {len(response.text.strip())} characters")
            return True
        else:
            print("❌ Empty response from Gemini API")
            return False

    except Exception as e:
        print(f"❌ Gemini API test failed: {e}")
        print(f"❌ Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 Starting Gemini API Test")
    success = test_gemini_api()
    if success:
        print("✅ Test passed - Gemini 2.5 Flash is working!")
    else:
        print("❌ Test failed - Check API key, network, or model name")
        exit(1)