"""
BIST Profiling Application Configuration

This file defines configuration settings for different environments.
"""

import os
from datetime import timedelta

class Config:
    """Base configuration class."""
    # Flask settings
    SECRET_KEY = os.environ.get('SECRET_KEY', 'bist_profiling_secret_key_change_in_production')
    DEBUG = False
    TESTING = False
    
    # Database settings
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # API settings
    API_KEY = os.environ.get('API_KEY', 'bist_profiling_api_key')
    API_SECRET = os.environ.get('API_SECRET', 'bist_profiling_secret_key_change_in_production')
    TOKEN_EXPIRY = 3600  # 1 hour
    
    # CORS settings
    CORS_ORIGINS = os.environ.get('ALLOWED_ORIGINS', '*')
    
    # Security settings
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=30)
    
    # Rate limiting settings
    RATE_LIMIT = 60  # Number of requests
    RATE_PERIOD = 60  # Duration in seconds (1 minute)

class DevelopmentConfig(Config):
    """Development environment configuration."""
    DEBUG = True
    SESSION_COOKIE_SECURE = False
    
    @staticmethod
    def init_app(app):
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(app.instance_path, 'bist_profiling_dev.db')

class TestingConfig(Config):
    """Test environment configuration."""
    TESTING = True
    DEBUG = True
    SESSION_COOKIE_SECURE = False
    PRESERVE_CONTEXT_ON_EXCEPTION = False
    
    @staticmethod
    def init_app(app):
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(app.instance_path, 'bist_profiling_test.db')

class ProductionConfig(Config):
    """Production environment configuration."""
    
    # Security settings
    SECRET_KEY = os.environ.get('SECRET_KEY') or os.urandom(24).hex()
    API_KEY = os.environ.get('API_KEY') or os.urandom(16).hex()
    API_SECRET = os.environ.get('API_SECRET') or os.urandom(24).hex()
    
    # Performance settings
    SQLALCHEMY_POOL_SIZE = 10
    SQLALCHEMY_MAX_OVERFLOW = 20
    SQLALCHEMY_POOL_TIMEOUT = 30
    SQLALCHEMY_POOL_RECYCLE = 1800
    
    # Rate limiting settings - More restrictive for production environment
    RATE_LIMIT = 30
    RATE_PERIOD = 60
    
    @staticmethod
    def init_app(app):
        db_url = os.environ.get('DATABASE_URL')
        if db_url:
            app.config['SQLALCHEMY_DATABASE_URI'] = db_url
        else:
            app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(app.instance_path, 'bist_profiling_prod.db')

# Environment selection
config_by_name = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig
}

# Determine active configuration
def get_config():
    env = os.environ.get('FLASK_ENV', 'development')
    return config_by_name[env] 