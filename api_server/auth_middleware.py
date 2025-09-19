#!/usr/bin/env python3
"""
Authentication Middleware - JWT and role-based access control
"""

from functools import wraps
from flask import request, jsonify, g
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity, get_jwt
import psycopg2
from psycopg2.extras import RealDictCursor
import logging

logger = logging.getLogger(__name__)

# Role definitions
ROLES = {
    'admin': ['read', 'write', 'delete', 'manage_users', 'manage_system'],
    'operator': ['read', 'write', 'manage_tolls'],
    'user': ['read', 'write_own']
}

def get_db_connection():
    """Get database connection"""
    return psycopg2.connect(
        host='localhost',
        port=5432,
        database='transport_system',
        user='admin',
        password='password'
    )

def get_user_role(user_id):
    """Get user role from database"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("SELECT role FROM users WHERE user_id = %s", (user_id,))
        result = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        return result['role'] if result else 'user'
        
    except Exception as e:
        logger.error(f"Error getting user role: {e}")
        return 'user'

def require_auth(f):
    """Decorator to require authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            verify_jwt_in_request()
            user_id = get_jwt_identity()
            g.current_user_id = user_id
            g.current_user_role = get_user_role(user_id)
            return f(*args, **kwargs)
        except Exception as e:
            return jsonify({'error': 'Authentication required'}), 401
    
    return decorated_function

def require_role(required_permissions):
    """Decorator to require specific role permissions"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                verify_jwt_in_request()
                user_id = get_jwt_identity()
                user_role = get_user_role(user_id)
                
                # Check if user has required permissions
                user_permissions = ROLES.get(user_role, [])
                
                if isinstance(required_permissions, str):
                    required_permissions_list = [required_permissions]
                else:
                    required_permissions_list = required_permissions
                
                has_permission = any(perm in user_permissions for perm in required_permissions_list)
                
                if not has_permission:
                    return jsonify({'error': 'Insufficient permissions'}), 403
                
                g.current_user_id = user_id
                g.current_user_role = user_role
                return f(*args, **kwargs)
                
            except Exception as e:
                return jsonify({'error': 'Authentication required'}), 401
        
        return decorated_function
    return decorator

def require_admin(f):
    """Decorator to require admin role"""
    return require_role(['manage_system'])(f)

def require_operator(f):
    """Decorator to require operator or admin role"""
    return require_role(['manage_tolls', 'manage_system'])(f)

def check_resource_ownership(resource_type, resource_id, user_id):
    """Check if user owns the resource"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        if resource_type == 'vehicle':
            cursor.execute(
                "SELECT user_id FROM vehicles WHERE vehicle_id = %s",
                (resource_id,)
            )
        elif resource_type == 'user':
            cursor.execute(
                "SELECT user_id FROM users WHERE user_id = %s",
                (resource_id,)
            )
        else:
            return False
        
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        return result and result['user_id'] == user_id
        
    except Exception as e:
        logger.error(f"Error checking resource ownership: {e}")
        return False

def require_ownership_or_role(resource_type, required_permissions):
    """Decorator to require resource ownership or specific role"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                verify_jwt_in_request()
                user_id = get_jwt_identity()
                user_role = get_user_role(user_id)
                
                # Extract resource ID from URL parameters
                resource_id = kwargs.get('vehicle_id') or kwargs.get('user_id')
                
                # Check if user owns the resource
                owns_resource = check_resource_ownership(resource_type, resource_id, user_id)
                
                # Check if user has required role permissions
                user_permissions = ROLES.get(user_role, [])
                has_role_permission = any(perm in user_permissions for perm in required_permissions)
                
                if not (owns_resource or has_role_permission):
                    return jsonify({'error': 'Access denied'}), 403
                
                g.current_user_id = user_id
                g.current_user_role = user_role
                return f(*args, **kwargs)
                
            except Exception as e:
                return jsonify({'error': 'Authentication required'}), 401
        
        return decorated_function
    return decorator

class AuditLogger:
    """Audit logging for sensitive actions"""
    
    @staticmethod
    def log_action(user_id, action, resource_type, resource_id, details=None):
        """Log audit event"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO audit_logs (
                    user_id, action, resource_type, resource_id, 
                    details, timestamp
                ) VALUES (%s, %s, %s, %s, %s, NOW())
            """, (user_id, action, resource_type, resource_id, details))
            
            conn.commit()
            cursor.close()
            conn.close()
            
        except Exception as e:
            logger.error(f"Audit logging failed: {e}")

def audit_action(action, resource_type):
    """Decorator to audit sensitive actions"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            result = f(*args, **kwargs)
            
            # Log the action after successful execution
            try:
                user_id = getattr(g, 'current_user_id', None)
                resource_id = kwargs.get('vehicle_id') or kwargs.get('user_id') or 'unknown'
                
                AuditLogger.log_action(
                    user_id=user_id,
                    action=action,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    details=f"Function: {f.__name__}"
                )
            except Exception as e:
                logger.error(f"Audit logging error: {e}")
            
            return result
        
        return decorated_function
    return decorator

# Rate limiting decorator
from collections import defaultdict
import time

request_counts = defaultdict(list)

def rate_limit(max_requests=100, window_seconds=3600):
    """Rate limiting decorator"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Get client identifier (user ID or IP)
            client_id = getattr(g, 'current_user_id', request.remote_addr)
            
            now = time.time()
            window_start = now - window_seconds
            
            # Clean old requests
            request_counts[client_id] = [
                req_time for req_time in request_counts[client_id] 
                if req_time > window_start
            ]
            
            # Check rate limit
            if len(request_counts[client_id]) >= max_requests:
                return jsonify({'error': 'Rate limit exceeded'}), 429
            
            # Add current request
            request_counts[client_id].append(now)
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator