import os

# Configuration
port = int(os.getenv('PORT', 5001))
is_railway = bool(os.getenv('RAILWAY_ENVIRONMENT'))

print(f"🚀 Starting AI Translator on Railway (Port: {port})")

# Create minimal Flask app for health checks
from flask import Flask
app = Flask(__name__)

@app.route('/')
def home():
    return {'status': 'healthy', 'port': port, 'railway': is_railway}, 200

@app.route('/health')
def health_check():
    return {'status': 'healthy', 'port': port, 'railway': is_railway}, 200

# Try to load SocketIO app if possible
app_loaded = False

try:
    from speech_translator import socketio, translator
    print("✅ SocketIO app loaded successfully")
    app_loaded = True
except Exception as e:
    print(f"⚠️  SocketIO app failed to load: {e}")
    print("🚨 Using minimal Flask app (health checks will work)")

if __name__ == "__main__":
    if app_loaded:
        print("🎯 Starting SocketIO application")
        socketio.run(
            app,
            host="0.0.0.0",
            port=port,
            debug=False,
            allow_unsafe_werkzeug=False,
            log=False,
            use_reloader=False
        )
    else:
        print("🔄 Starting Flask app")
        app.run(host='0.0.0.0', port=port, debug=False)