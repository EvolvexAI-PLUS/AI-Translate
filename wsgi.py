import os
print("🚀 Starting AI Translator on Railway...")

# Check Railway environment
is_railway = os.getenv('RAILWAY_ENVIRONMENT')
print(f"🚂 Railway Environment: {is_railway}")

try:
    from speech_translator import socketio, app
    print("✅ App and SocketIO imported successfully")

    port = int(os.getenv('PORT', 8000))
    print(f"📡 Starting on port {port}")

    # Simple health check before SocketIO startup
    @app.route('/health')
    def health_check():
        return {'status': 'healthy', 'port': port, 'railway': bool(is_railway)}, 200

    # Use Railway-specific configuration
    if is_railway:
        print("🎊 Running in Railway environment")
        socketio.run(
            app,
            host="0.0.0.0",
            port=port,
            debug=False,
            allow_unsafe_werkzeug=False,
            log=False
        )
    else:
        print("🏠 Running locally")
        socketio.run(
            app,
            host="0.0.0.0",
            port=port,
            debug=False,
            allow_unsafe_werkzeug=False,
            log=False
        )

except Exception as e:
    import traceback
    print(f"❌ Failed to start app: {e}")
    print(traceback.format_exc())
    print("🔧 Check Railway environment variables")
    print("📝 Required: GOOGLE_API_KEY, ELEVEN_LABS_API_KEY")
    exit(1)