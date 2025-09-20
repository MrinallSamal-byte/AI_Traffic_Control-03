#!/usr/bin/env python3
"""
Enhanced Authentication and Authorization Module
Supports JWT tokens, role-based access control, and secure configuration
"""

import os
import hashlib
import secrets
from datetime import datetime, timedelta
from functools import wraps
from typing import Dict, List, Optional, Any

from flask import request, jsonify, current_app
from flask_jwt_extended import (
    JWTManager, create_access_token, jwt_required, 
    get_jwt_identity, get_jwt, verify_jwt_in_request
)
import logging

logger = logging.getLogger(__name__)

class SecurityConfig:
    """Secure configuration management"""
    
    def __init__(self):
        self.jwt_secret_key = self._get_jwt_secret()
        self.admin_password = self._get_admin_password()
        self.operator_password = self._get_operator_password()
        self.token_expires = int(os.getenv('JWT_ACCESS_TOKEN_EXPIRES', 3600))
        
    def _get_jwt_secret(self) -> str:
        """Get JWT secret key from environment or generate secure default"""
        secret = os.getenv('JWT_SECRET_KEY')
        if not secret:
            logger.warning("JWT_SECRET_KEY not set, generating random key")
            secret = secrets.token_urlsafe(32)
        return secret
    
    def _get_admin_password(self) -> str:
        """Get admin password from environment"""
        password = os.getenv('ADMIN_PASSWORD', 'admin123')
        if password == 'admin123':
            logger.warning("Using default admin password - change in production!")
        return password
    
    def _get_operator_password(self) -> str:
        """Get operator password from environment"""
        password = os.getenv('OPERATOR_PASSWORD', 'operator123')
        if password == 'operator123':
            logger.warning("Using default operator password - change in production!")
        return password

class UserManager:
    """User management with role-based access control"""
    
    def __init__(self, config: SecurityConfig):
        self.config = config
        self.users = self._initialize_users()
        self.roles = {
            'admin': {
                'permissions': ['read', 'write', 'delete', 'admin'],
                'endpoints': ['*']  # All endpoints
            },
            'operator': {
                'permissions': ['read', 'write'],
                'endpoints': [
                    '/telemetry/ingest',
                    '/driver_score',
                    '/toll/charge',
                    '/stream/telemetry',
                    '/metrics/json'
                ]
            },
            'viewer': {
                'permissions': ['read'],
                'endpoints': [
                    '/health',
                    '/metrics/json',
                    '/stream/telemetry'
                ]
            }
        }
    
    def _initialize_users(self) -> Dict[str, Dict[str, Any]]:
        """Initialize user database"""
        return {
            'admin': {
                'password_hash': self._hash_password(self.config.admin_password),
                'role': 'admin',
                'active': True,
                'created_at': datetime.utcnow().isoformat()
            },
            'operator': {
                'password_hash': self._hash_password(self.config.operator_password),
                'role': 'operator',
                'active': True,
                'created_at': datetime.utcnow().isoformat()
            }
        }
    
    def _hash_password(self, password: str) -> str:
        """Hash password with salt"""
        salt = secrets.token_hex(16)
        password_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        return f"{salt}:{password_hash.hex()}"
    
    def verify_password(self, password: str, password_hash: str) -> bool:
        """Verify password against hash"""
        try:
            salt, stored_hash = password_hash.split(':')
            password_hash_check = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
            return stored_hash == password_hash_check.hex()
        except Exception as e:
            logger.error(f"Password verification error: {e}")
            return False
    
    def authenticate_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate user credentials"""
        user = self.users.get(username)
        if not user or not user.get('active', False):
            return None
        
        if self.verify_password(password, user['password_hash']):
            return {
                'username': username,
                'role': user['role'],
                'permissions': self.roles[user['role']]['permissions']
            }
        
        return None
    
    def has_permission(self, username: str, permission: str) -> bool:
        """Check if user has specific permission"""
        user = self.users.get(username)
        if not user:
            return False
        
        role = user['role']
        return permission in self.roles.get(role, {}).get('permissions', [])
    
    def can_access_endpoint(self, username: str, endpoint: str) -> bool:
        """Check if user can access specific endpoint"""
        user = self.users.get(username)
        if not user:
            return False
        
        role = user['role']
        allowed_endpoints = self.roles.get(role, {}).get('endpoints', [])
        
        # Admin has access to all endpoints
        if '*' in allowed_endpoints:
            return True
        
        # Check exact match or pattern match
        return any(
            endpoint == allowed or endpoint.startswith(allowed.rstrip('*'))
            for allowed in allowed_endpoints
        )

# Global instances
security_config = SecurityConfig()
user_manager = UserManager(security_config)

def init_auth(app):
    """Initialize authentication for Flask app"""
    app.config['JWT_SECRET_KEY'] = security_config.jwt_secret_key
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(seconds=security_config.token_expires)
    
    jwt = JWTManager(app)
    
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return jsonify({'error': 'Token has expired'}), 401
    
    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return jsonify({'error': 'Invalid token'}), 401
    
    @jwt.unauthorized_loader
    def missing_token_callback(error):
        return jsonify({'error': 'Authorization token required'}), 401
    
    return jwt

def require_permission(permission: str):
    """Decorator to require specific permission"""
    def decorator(f):
        @wraps(f)
        @jwt_required()
        def decorated_function(*args, **kwargs):
            username = get_jwt_identity()
            
            if not user_manager.has_permission(username, permission):
                logger.warning(f"Permission denied: {username} lacks {permission}")
                return jsonify({'error': 'Insufficient permissions'}), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def require_role(role: str):
    """Decorator to require specific role"""
    def decorator(f):
        @wraps(f)
        @jwt_required()
        def decorated_function(*args, **kwargs):
            username = get_jwt_identity()
            user = user_manager.users.get(username)
            
            if not user or user['role'] != role:
                logger.warning(f"Role denied: {username} is not {role}")
                return jsonify({'error': f'Role {role} required'}), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def require_endpoint_access():
    """Decorator to check endpoint access"""
    def decorator(f):
        @wraps(f)
        @jwt_required()
        def decorated_function(*args, **kwargs):
            username = get_jwt_identity()
            endpoint = request.endpoint or request.path
            
            if not user_manager.can_access_endpoint(username, endpoint):
                logger.warning(f"Endpoint access denied: {username} cannot access {endpoint}")
                return jsonify({'error': 'Access denied to this endpoint'}), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def rate_limit_by_user(max_requests: int = 100, window_seconds: int = 60):
    """Rate limiting decorator by authenticated user"""
    from collections import defaultdict
    import time
    
    user_requests = defaultdict(list)
    
    def decorator(f):
        @wraps(f)
        @jwt_required()
        def decorated_function(*args, **kwargs):
            username = get_jwt_identity()
            now = time.time()
            
            # Clean old requests
            user_requests[username] = [
                req_time for req_time in user_requests[username]
                if now - req_time < window_seconds
            ]
            
            # Check rate limit
            if len(user_requests[username]) >= max_requests:
                logger.warning(f"Rate limit exceeded for user: {username}")
                return jsonify({'error': 'Rate limit exceeded'}), 429
            
            # Add current request
            user_requests[username].append(now)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def create_token(username: str) -> str:
    """Create JWT token for user"""
    user = user_manager.users.get(username)
    if not user:
        raise ValueError(f"User {username} not found")
    
    additional_claims = {
        'role': user['role'],
        'permissions': user_manager.roles[user['role']]['permissions']
    }
    
    return create_access_token(
        identity=username,
        additional_claims=additional_claims
    )

def get_current_user() -> Optional[Dict[str, Any]]:
    """Get current authenticated user info"""
    try:
        verify_jwt_in_request()
        username = get_jwt_identity()
        claims = get_jwt()
        
        return {
            'username': username,
            'role': claims.get('role'),
            'permissions': claims.get('permissions', [])
        }
    except Exception:
        return None