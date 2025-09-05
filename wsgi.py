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

print(f"📁 Template folder: {template_dir}")
print(f"📁 Templates exist: {os.path.exists(template_dir)}")
print(f"📄 index.html exists: {os.path.exists(os.path.join(template_dir, 'index.html'))}")

# This will be replaced with the Flask app from speech_translator.py if it loads
app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)

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

# Load SocketIO components and integrate with our Flask app
translator = None
socketio = None
has_socketio = False

try:
    # Import the SocketIO instance from speech_translator
    from speech_translator import socketio as imported_socketio, translator as imported_translator, app as speech_app

    # Replace our Flask app with the one from speech_translator that has all routes registered
    app = speech_app

    # Reconfigure the Flask app for Railway template paths
    app.template_folder = template_dir
    app.static_folder = static_dir

    print("✅ SocketIO app and routes loaded successfully")
    print("🎯 Using Flask app from speech_translator.py")

    # Set the global variables
    translator = imported_translator
    socketio = imported_socketio
    has_socketio = socketio is not None

    # Add health and status routes if not present
    if not hasattr(app, 'view_functions') or 'health' not in app.view_functions:
        @app.route('/health')
        def health_check():
            return {'status': 'healthy', 'port': port, 'railway': is_railway}, 200

    if not hasattr(app, 'view_functions') or 'status' not in app.view_functions:
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

except ImportError as e:
    print(f"⚠️  SocketIO import failed: {e}")
    print("🚨 Using basic Flask app (limited features)")
    has_socketio = False
except Exception as e:
    print(f"⚠️  SocketIO setup failed: {e}")
    translator = None
    socketio = None
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
        # Add missing routes if not using SocketIO app
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
    
        app.run(host='0.0.0.0', port=port, debug=False)