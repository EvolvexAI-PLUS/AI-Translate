import os
from speech_translator import socketio, app

if __name__ == "__main__":
    port = int(os.getenv('PORT', 8000))
    socketio.run(
        app,
        host="0.0.0.0",
        port=port,
        debug=False,
        allow_unsafe_werkzeug=False
    )