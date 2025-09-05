import os

# Configuration
port = int(os.getenv('PORT', 5001))
is_railway = bool(os.getenv('RAILWAY_ENVIRONMENT'))

print(f"🚀 Starting AI Translator on Railway (Port: {port})")

# Always create Flask app with templates enabled
from flask import Flask, render_template, send_from_directory
import os

# Define template and static folder paths
template_dir = os.path.join(os.path.dirname(__file__), 'templates')
static_dir = os.path.join(os.path.dirname(__file__), 'static')

app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)

print(f"📁 Template folder: {template_dir}")
print(f"📁 Static folder: {static_dir}")
print(f"📁 Templates exist: {os.path.exists(template_dir)}")
print(f"📄 index.html exists: {os.path.exists(os.path.join(template_dir, 'index.html'))}")

@app.route('/')
def index():
    try:
        return render_template('index.html')
    except Exception as e:
        print(f"❌ Template render error: {e}")
        return f"""
        <html><body>
        <h1 style="color: red;">AI Translator - Template Error</h1>
        <p>Error loading template: {str(e)}</p>
        <p>Template directory: {template_dir}</p>
        <p>Index file exists: {os.path.exists(os.path.join(template_dir, 'index.html'))}</p>
        </body></html>
        """, 500

@app.route('/health')
def health_check():
    return {'status': 'healthy', 'port': port, 'railway': is_railway}, 200

@app.route('/status')
def status():
    return {
        'status': 'running' if (translator is not None) else 'no_translator',
        'socketio': has_socketio,
        'templates': os.path.exists(template_dir),
        'index_html': os.path.exists(os.path.join(template_dir, 'index.html')),
        'port': port,
        'railway': is_railway
    }, 200

# Try to load SocketIO components
try:
    from speech_translator import socketio, translator
    print("✅ SocketIO app loaded successfully")
    has_socketio = True
except Exception as e:
    print(f"⚠️  SocketIO app failed to load: {e}")
    socketio = None
    translator = None
    has_socketio = False

if __name__ == "__main__":
    if has_socketio:
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
        print("🔄 Starting basic Flask app")
        app.run(host='0.0.0.0', port=port, debug=False)