#!/usr/bin/env python3
"""
CORS Middleware for React Frontend Integration
"""

from flask_cors import CORS

def setup_cors(app):
    """Setup CORS for React frontend"""
    CORS(app, 
         origins=["http://localhost:3000", "http://127.0.0.1:3000"],
         methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
         allow_headers=["Content-Type", "Authorization"],
         supports_credentials=True)
    
    return app