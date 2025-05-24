#!/usr/bin/env python3
"""
BIST Profiling Web Application Entry Point

This script starts the Flask application.
"""

import os
import sys
from pathlib import Path

print("Starting BIST Profiling Web Application...")

# Flask environment variable
if not os.environ.get('FLASK_ENV'):
    os.environ['FLASK_ENV'] = 'development'

# Get port setting
port = int(os.environ.get('PORT', 5000))

# Create application
from src.app import create_app
app = create_app()

# Run application
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=port, debug=True) 