#!/usr/bin/env python3
"""
Simple test to verify the Flask app can start without API keys
Used by Railway for health checks during deployment
"""
import os
import sys
from flask import Flask

# Simple test app for health checks
test_app = Flask(__name__)

@test_app.route('/')
def health_check():
    return {'status': 'building', 'message': 'App is starting up'}

if __name__ == "__main__":
    port = int(os.getenv('PORT', 8080))
    test_app.run(host='0.0.0.0', port=port, debug=False)