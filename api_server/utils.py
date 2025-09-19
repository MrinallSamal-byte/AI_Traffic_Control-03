"""Utility functions for API server."""

import os
import logging
from functools import wraps
from flask import request, jsonify
from pydantic import BaseModel, ValidationError
import uuid


def validate_json(model_class: BaseModel):
    """Decorator to validate JSON input using Pydantic models."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                json_data = request.get_json()
                if json_data is None:
                    return jsonify({'error': 'Invalid JSON'}), 400
                
                # Validate using Pydantic model
                validated_data = model_class(**json_data)
                request.validated_data = validated_data
                return f(*args, **kwargs)
                
            except ValidationError as e:
                return jsonify({
                    'error': 'Validation failed',
                    'details': e.errors()
                }), 400
            except Exception as e:
                logging.error(f"Validation error: {e}")
                return jsonify({'error': 'Invalid request'}), 400
        
        return decorated_function
    return decorator


def generate_correlation_id():
    """Generate correlation ID for request tracing."""
    return str(uuid.uuid4())


def get_config(key: str, default=None):
    """Get configuration from environment variables."""
    return os.getenv(key, default)


def setup_logging():
    """Setup structured logging."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )