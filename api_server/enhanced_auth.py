#!/usr/bin/env python3
"""
Enhanced Authentication System with JWT and Certificate-based Authentication
"""

import os
import jwt
import bcrypt
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from functools import wraps
from flask import request, jsonify, current_app
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity, get_jwt
import logging
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
import base64
import hashlib

logger = logging.getLogger(__name__)

class EnhancedAuthManager:
    """Enhanced authentication manager with multiple auth methods"""
    
    def __init__(self, app=None):
        self.app = app
        self.jwt_manager = None
        self.users_db = {}
        self.device_certificates = {}
        self.api_keys = {}
        self.revoked_tokens = set()
        
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize authentication with Flask app"""
        self.app = app
        
        # JWT Configuration
        app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', secrets.token_urlsafe(32))
        app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=24)
        app.config['JWT_ALGORITHM'] = 'HS256'
        
        self.jwt_manager = JWTManager(app)
        
        # JWT callbacks
        @self.jwt_manager.token_in_blocklist_loader
        def check_if_token_revoked(jwt_header, jwt_payload):
            jti = jwt_payload['jti']
            return jti in self.revoked_tokens
        
        @self.jwt_manager.expired_token_loader
        def expired_token_callback(jwt_header, jwt_payload):
            return jsonify({'error': 'Token has expired'}), 401
        
        @self.jwt_manager.invalid_token_loader
        def invalid_token_callback(error):
            return jsonify({'error': 'Invalid token'}), 401
        
        @self.jwt_manager.unauthorized_loader
        def missing_token_callback(error):
            return jsonify({'error': 'Authorization token required'}), 401
        
        # Initialize default users and certificates
        self._initialize_default_data()
        
        logger.info("Enhanced authentication system initialized")
    
    def _initialize_default_data(self):
        """Initialize default users, devices, and API keys"""
        # Default users
        self.users_db = {
            'admin': {
                'password_hash': bcrypt.hashpw('admin123'.encode(), bcrypt.gensalt()).decode(),
                'role': 'admin',
                'permissions': ['read', 'write', 'admin'],
                'created_at': datetime.utcnow().isoformat(),
                'active': True
            },
            'operator': {
                'password_hash': bcrypt.hashpw('operator123'.encode(), bcrypt.gensalt()).decode(),
                'role': 'operator',
                'permissions': ['read', 'write'],
                'created_at': datetime.utcnow().isoformat(),
                'active': True
            },
            'viewer': {
                'password_hash': bcrypt.hashpw('viewer123'.encode(), bcrypt.gensalt()).decode(),
                'role': 'viewer',
                'permissions': ['read'],
                'created_at': datetime.utcnow().isoformat(),
                'active': True
            }
        }
        
        # Generate default API keys
        self.api_keys = {
            'device_api_key_001': {
                'name': 'Device API Key 001',
                'permissions': ['telemetry_ingest'],
                'device_id': 'DEVICE_12345678',
                'created_at': datetime.utcnow().isoformat(),
                'active': True,
                'rate_limit': 1000  # requests per minute
            },
            'ml_service_key': {
                'name': 'ML Service API Key',
                'permissions': ['read', 'ml_predict'],
                'service_name': 'ml_services',
                'created_at': datetime.utcnow().isoformat(),
                'active': True,
                'rate_limit': 5000
            }
        }
        
        # Generate device certificates
        self._generate_device_certificates()
    
    def _generate_device_certificates(self):
        """Generate self-signed certificates for device authentication"""
        try:
            # Generate CA private key
            ca_private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048
            )
            
            # Generate device certificates
            device_ids = ['DEVICE_12345678', 'DEVICE_87654321', 'DEVICE_11111111']
            
            for device_id in device_ids:
                # Generate device private key
                device_private_key = rsa.generate_private_key(
                    public_exponent=65537,
                    key_size=2048
                )
                
                # Create certificate
                subject = issuer = x509.Name([
                    x509.NameAttribute(x509.NameOID.COUNTRY_NAME, "US"),
                    x509.NameAttribute(x509.NameOID.STATE_OR_PROVINCE_NAME, "CA"),
                    x509.NameAttribute(x509.NameOID.LOCALITY_NAME, "San Francisco"),
                    x509.NameAttribute(x509.NameOID.ORGANIZATION_NAME, "Smart Transport"),
                    x509.NameAttribute(x509.NameOID.COMMON_NAME, device_id),
                ])
                
                cert = x509.CertificateBuilder().subject_name(
                    subject
                ).issuer_name(
                    issuer
                ).public_key(
                    device_private_key.public_key()
                ).serial_number(
                    x509.random_serial_number()
                ).not_valid_before(
                    datetime.utcnow()
                ).not_valid_after(
                    datetime.utcnow() + timedelta(days=365)
                ).add_extension(
                    x509.SubjectAlternativeName([
                        x509.DNSName(f"{device_id.lower()}.transport.local"),
                    ]),
                    critical=False,
                ).sign(ca_private_key, hashes.SHA256())
                
                # Store certificate info
                cert_pem = cert.public_bytes(serialization.Encoding.PEM)
                private_key_pem = device_private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption()
                )
                
                self.device_certificates[device_id] = {
                    'certificate': cert_pem.decode(),
                    'private_key': private_key_pem.decode(),
                    'fingerprint': hashlib.sha256(cert_pem).hexdigest(),
                    'valid_from': cert.not_valid_before.isoformat(),
                    'valid_until': cert.not_valid_after.isoformat(),
                    'active': True
                }
            
            logger.info(f"Generated certificates for {len(device_ids)} devices")
            
        except Exception as e:
            logger.error(f"Failed to generate device certificates: {e}")
    
    def authenticate_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate user with username/password"""
        user = self.users_db.get(username)
        if not user or not user.get('active'):
            return None
        
        if bcrypt.checkpw(password.encode(), user['password_hash'].encode()):
            return {
                'username': username,
                'role': user['role'],
                'permissions': user['permissions']
            }
        
        return None
    
    def authenticate_api_key(self, api_key: str) -> Optional[Dict[str, Any]]:
        """Authenticate using API key"""
        key_info = self.api_keys.get(api_key)
        if not key_info or not key_info.get('active'):
            return None
        
        return {
            'api_key': api_key,
            'name': key_info['name'],
            'permissions': key_info['permissions'],
            'device_id': key_info.get('device_id'),
            'service_name': key_info.get('service_name'),
            'rate_limit': key_info.get('rate_limit', 100)
        }
    
    def authenticate_certificate(self, cert_data: str) -> Optional[Dict[str, Any]]:
        """Authenticate using client certificate"""
        try:
            # Parse certificate
            cert = x509.load_pem_x509_certificate(cert_data.encode())
            
            # Calculate fingerprint
            cert_der = cert.public_bytes(serialization.Encoding.DER)
            fingerprint = hashlib.sha256(cert_der).hexdigest()
            
            # Find matching device certificate
            for device_id, cert_info in self.device_certificates.items():
                if cert_info['fingerprint'] == fingerprint and cert_info.get('active'):
                    # Check certificate validity
                    now = datetime.utcnow()
                    if cert.not_valid_before <= now <= cert.not_valid_after:
                        return {
                            'device_id': device_id,
                            'auth_method': 'certificate',
                            'fingerprint': fingerprint,
                            'permissions': ['telemetry_ingest', 'device_status']
                        }
            
            return None
            
        except Exception as e:
            logger.error(f"Certificate authentication failed: {e}")
            return None
    
    def create_access_token(self, identity: str, additional_claims: Dict[str, Any] = None) -> str:
        """Create JWT access token"""
        claims = additional_claims or {}
        return create_access_token(identity=identity, additional_claims=claims)
    
    def revoke_token(self, jti: str):
        """Revoke a JWT token"""
        self.revoked_tokens.add(jti)
        logger.info(f"Token revoked: {jti}")
    
    def create_api_key(self, name: str, permissions: List[str], **kwargs) -> str:
        """Create new API key"""
        api_key = secrets.token_urlsafe(32)
        
        self.api_keys[api_key] = {
            'name': name,
            'permissions': permissions,
            'created_at': datetime.utcnow().isoformat(),
            'active': True,
            **kwargs
        }
        
        logger.info(f"Created API key: {name}")
        return api_key
    
    def revoke_api_key(self, api_key: str):
        """Revoke an API key"""
        if api_key in self.api_keys:
            self.api_keys[api_key]['active'] = False
            logger.info(f"API key revoked: {api_key}")

# Global auth manager instance
auth_manager = EnhancedAuthManager()

def init_enhanced_auth(app):
    """Initialize enhanced authentication with Flask app"""
    auth_manager.init_app(app)
    return auth_manager

def multi_auth_required(permissions: List[str] = None):
    """Decorator for multiple authentication methods"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            auth_info = None
            
            # Try JWT authentication first
            auth_header = request.headers.get('Authorization', '')
            if auth_header.startswith('Bearer '):
                try:
                    token = auth_header.split(' ')[1]
                    payload = jwt.decode(
                        token, 
                        current_app.config['JWT_SECRET_KEY'], 
                        algorithms=[current_app.config['JWT_ALGORITHM']]
                    )
                    
                    # Check if token is revoked
                    if payload.get('jti') not in auth_manager.revoked_tokens:
                        auth_info = {
                            'method': 'jwt',
                            'identity': payload.get('sub'),
                            'permissions': payload.get('permissions', []),
                            'role': payload.get('role')
                        }
                except jwt.InvalidTokenError:
                    pass
            
            # Try API key authentication
            if not auth_info:
                api_key = request.headers.get('X-API-Key') or request.args.get('api_key')
                if api_key:
                    key_info = auth_manager.authenticate_api_key(api_key)
                    if key_info:
                        auth_info = {
                            'method': 'api_key',
                            'identity': key_info.get('device_id') or key_info.get('service_name'),
                            'permissions': key_info['permissions'],
                            'api_key_info': key_info
                        }
            
            # Try certificate authentication
            if not auth_info:
                cert_header = request.headers.get('X-Client-Cert')
                if cert_header:
                    # Decode base64 certificate
                    try:
                        cert_data = base64.b64decode(cert_header).decode()
                        cert_info = auth_manager.authenticate_certificate(cert_data)
                        if cert_info:
                            auth_info = {
                                'method': 'certificate',
                                'identity': cert_info['device_id'],
                                'permissions': cert_info['permissions'],
                                'cert_info': cert_info
                            }
                    except Exception as e:
                        logger.error(f"Certificate decoding failed: {e}")
            
            # Check if authentication succeeded
            if not auth_info:
                return jsonify({'error': 'Authentication required'}), 401
            
            # Check permissions
            if permissions:
                user_permissions = auth_info.get('permissions', [])
                if not any(perm in user_permissions for perm in permissions):
                    return jsonify({'error': 'Insufficient permissions'}), 403
            
            # Add auth info to request context
            request.auth_info = auth_info
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator

def require_permission(permission: str):
    """Decorator to require specific permission"""
    return multi_auth_required([permission])

def require_role(role: str):
    """Decorator to require specific role (JWT only)"""
    def decorator(f):
        @wraps(f)
        @multi_auth_required()
        def decorated_function(*args, **kwargs):
            auth_info = getattr(request, 'auth_info', {})
            if auth_info.get('role') != role:
                return jsonify({'error': f'Role {role} required'}), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def get_current_user():
    """Get current authenticated user info"""
    return getattr(request, 'auth_info', None)

# Rate limiting decorator
def rate_limit_by_auth(max_requests: int = 100, window_seconds: int = 60):
    """Rate limiting based on authentication identity"""
    from collections import defaultdict
    import time
    
    request_counts = defaultdict(list)
    
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            auth_info = getattr(request, 'auth_info', {})
            identity = auth_info.get('identity', request.remote_addr)
            
            # Get rate limit from auth info if available
            if 'api_key_info' in auth_info:
                max_reqs = auth_info['api_key_info'].get('rate_limit', max_requests)
            else:
                max_reqs = max_requests
            
            now = time.time()
            
            # Clean old requests
            request_counts[identity] = [
                req_time for req_time in request_counts[identity]
                if now - req_time < window_seconds
            ]
            
            # Check rate limit
            if len(request_counts[identity]) >= max_reqs:
                return jsonify({
                    'error': 'Rate limit exceeded',
                    'limit': max_reqs,
                    'window_seconds': window_seconds
                }), 429
            
            # Add current request
            request_counts[identity].append(now)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

if __name__ == "__main__":
    # Test the authentication system
    from flask import Flask
    
    app = Flask(__name__)
    auth_manager = init_enhanced_auth(app)
    
    # Test user authentication
    user_info = auth_manager.authenticate_user('admin', 'admin123')
    print(f"User auth test: {user_info}")
    
    # Test API key authentication
    api_key_info = auth_manager.authenticate_api_key('device_api_key_001')
    print(f"API key auth test: {api_key_info}")
    
    # Test certificate info
    device_certs = list(auth_manager.device_certificates.keys())
    print(f"Device certificates: {device_certs}")
    
    print("Enhanced authentication system test completed")