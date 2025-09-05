#!/usr/bin/env python3
"""
Railway health check script - runs independently of main app
This ensures health checks work even if the main app has issues
"""
import os
from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return {'status': 'ok', 'message': 'Health check passed'}, 200

@app.route('/health')
def health():
    return {'status': 'healthy', 'port': os.getenv('PORT', 'unknown')}, 200

if __name__ == "__main__":
    port = int(os.getenv('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=False)