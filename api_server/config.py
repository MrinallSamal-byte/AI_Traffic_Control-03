#!/usr/bin/env python3
"""
Secure Configuration Management
Handles environment variables, secrets, and configuration validation
"""

import os
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

@dataclass
class DatabaseConfig:
    """Database configuration"""
    host: str
    port: int
    database: str
    user: str
    password: str
    
    @classmethod
    def from_env(cls) -> 'DatabaseConfig':
        return cls(
            host=os.getenv('DB_HOST', 'localhost'),
            port=int(os.getenv('DB_PORT', 5432)),
            database=os.getenv('DB_NAME', 'transport_system'),
            user=os.getenv('DB_USER', 'admin'),
            password=os.getenv('DB_PASSWORD', 'password')
        )
    
    @property
    def connection_string(self) -> str:
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"

@dataclass
class RedisConfig:
    """Redis configuration"""
    host: str
    port: int
    password: Optional[str] = None
    
    @classmethod
    def from_env(cls) -> 'RedisConfig':
        return cls(
            host=os.getenv('REDIS_HOST', 'localhost'),
            port=int(os.getenv('REDIS_PORT', 6379)),
            password=os.getenv('REDIS_PASSWORD')
        )

@dataclass
class KafkaConfig:
    """Kafka configuration"""
    bootstrap_servers: list
    
    @classmethod
    def from_env(cls) -> 'KafkaConfig':
        servers = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
        return cls(
            bootstrap_servers=servers.split(',')
        )

@dataclass
class BlockchainConfig:
    """Blockchain configuration"""
    rpc_url: str
    contract_address: Optional[str] = None
    
    @classmethod
    def from_env(cls) -> 'BlockchainConfig':
        return cls(
            rpc_url=os.getenv('BLOCKCHAIN_RPC_URL', 'http://localhost:8545'),
            contract_address=os.getenv('BLOCKCHAIN_CONTRACT_ADDRESS')
        )

@dataclass
class SecurityConfig:
    """Security configuration"""
    jwt_secret_key: str
    jwt_expires_seconds: int
    admin_password: str
    operator_password: str
    rate_limit_enabled: bool
    
    @classmethod
    def from_env(cls) -> 'SecurityConfig':
        return cls(
            jwt_secret_key=os.getenv('JWT_SECRET_KEY', ''),
            jwt_expires_seconds=int(os.getenv('JWT_ACCESS_TOKEN_EXPIRES', 3600)),
            admin_password=os.getenv('ADMIN_PASSWORD', 'admin123'),
            operator_password=os.getenv('OPERATOR_PASSWORD', 'operator123'),
            rate_limit_enabled=os.getenv('RATE_LIMIT_ENABLED', 'true').lower() == 'true'
        )

class AppConfig:
    """Main application configuration"""
    
    def __init__(self):
        # Load environment variables
        load_dotenv()
        
        self.environment = os.getenv('ENVIRONMENT', 'development')
        self.debug = os.getenv('DEBUG', 'false').lower() == 'true'
        self.host = os.getenv('HOST', '0.0.0.0')
        self.port = int(os.getenv('PORT', 5000))
        
        # Component configurations
        self.database = DatabaseConfig.from_env()
        self.redis = RedisConfig.from_env()
        self.kafka = KafkaConfig.from_env()
        self.blockchain = BlockchainConfig.from_env()
        self.security = SecurityConfig.from_env()
        
        # Validate configuration
        self._validate_config()
    
    def _validate_config(self):
        """Validate configuration and log warnings"""
        warnings = []
        
        # Security validations
        if not self.security.jwt_secret_key:
            warnings.append("JWT_SECRET_KEY not set - using generated key")
        
        if self.security.admin_password == 'admin123':
            warnings.append("Using default admin password - change in production!")
        
        if self.security.operator_password == 'operator123':
            warnings.append("Using default operator password - change in production!")
        
        if self.database.password == 'password':
            warnings.append("Using default database password - change in production!")
        
        # Environment validations
        if self.environment == 'production' and self.debug:
            warnings.append("Debug mode enabled in production environment!")
        
        # Log warnings
        for warning in warnings:
            logger.warning(f"Configuration warning: {warning}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary (excluding sensitive data)"""
        return {
            'environment': self.environment,
            'debug': self.debug,
            'host': self.host,
            'port': self.port,
            'database': {
                'host': self.database.host,
                'port': self.database.port,
                'database': self.database.database,
                'user': self.database.user
                # password excluded for security
            },
            'redis': {
                'host': self.redis.host,
                'port': self.redis.port
                # password excluded for security
            },
            'kafka': {
                'bootstrap_servers': self.kafka.bootstrap_servers
            },
            'blockchain': {
                'rpc_url': self.blockchain.rpc_url,
                'contract_address': self.blockchain.contract_address
            },
            'security': {
                'jwt_expires_seconds': self.security.jwt_expires_seconds,
                'rate_limit_enabled': self.security.rate_limit_enabled
                # secrets excluded for security
            }
        }

# Global configuration instance
config = AppConfig()