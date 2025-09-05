import os
print("🚀 Starting AI Translator on Railway...")

try:
    from speech_translator import socketio, app
    print("✅ App imported successfully")

    port = int(os.getenv('PORT', 8000))
    print(f"📡 Starting on port {port}")

    socketio.run(
        app,
        host="0.0.0.0",
        port=port,
        debug=False,
        allow_unsafe_werkzeug=False,
        log=False
    )

except Exception as e:
    print(f"❌ Failed to start app: {e}")
    print("Check if API keys are set in Railway environment variables")
    exit(1)