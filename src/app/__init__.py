"""
BIST Financial Profiling Flask Application
"""

from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from pathlib import Path
import os
import logging
from logging.handlers import RotatingFileHandler
import datetime
from flask_migrate import Migrate
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import warnings

# Database object
db = SQLAlchemy()
migrate = Migrate()

# Flask-limiter uyarısını gizle (development ortamında normal)
warnings.filterwarnings("ignore", message="Using the in-memory storage for tracking rate limits")

def create_app(test_config=None):
    """Flask application factory"""
    # Create application
    app = Flask(__name__, instance_relative_config=True)
    
    # Configure logging system
    configure_logging(app)
    app.logger.info("Starting application...")
    
    # Load Config class
    from src.app.config import get_config
    config_class = get_config()
    app.config.from_object(config_class)
    
    # Call Config's custom init method (for database URI)
    if hasattr(config_class, 'init_app'):
        config_class.init_app(app)
    
    # Load environment variables
    load_environment_variables(app)
    
    # Test configuration
    if test_config is not None:
        # If test configuration exists, use it
        app.config.from_mapping(test_config)
    
    # Make sure instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass
    
    # CORS configuration
    CORS(app, origins=["http://localhost:3000", "http://127.0.0.1:3000"])
    
    # Initialize database
    db.init_app(app)
    migrate.init_app(app, db)
    
    # Rate limiter
    limiter = Limiter(
        key_func=get_remote_address,
        default_limits=["60 per minute"]
    )
    limiter.init_app(app)
    
    # Import database models and ensure table creation
    from src.app.models import Stock, Cluster, PriceHistory
    with app.app_context():
        # Create all tables
        db.create_all()
        
        # Populate database on first run (if table is empty)
        if db.session.query(Cluster).count() == 0:
            app.logger.info("Database empty, loading real data...")
            try:
                # Load real data
                from src.data.load_real_data import load_all_real_data
                load_all_real_data()
                app.logger.info("Real data loaded successfully.")
            except Exception as e:
                # Use default data in case of error
                app.logger.error(f"Error loading real data: {str(e)}")
                app.logger.info("Loading default data...")
                from src.app.default_data import create_default_clusters
                create_default_clusters(db.session)
                app.logger.info("Default data loaded.")
    
    # Register blueprints
    from src.app.routes import main_bp
    app.register_blueprint(main_bp)
    
    # Register API blueprint
    from src.app.api import api_bp
    app.register_blueprint(api_bp, url_prefix='/api')
    
    # Global error handling
    register_error_handlers(app)
    
    return app

def configure_logging(app):
    """Configure logging system"""
    # Create log directory
    if not os.path.exists('logs'):
        os.mkdir('logs')
    
    # Handler for log file
    file_handler = RotatingFileHandler('logs/bist_profiling.log', maxBytes=10240, backupCount=10)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.INFO)
    
    # Handler for console
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
    
    # Add handlers to application logger
    app.logger.addHandler(file_handler)
    app.logger.addHandler(console_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info('BIST Profiling application startup')

def register_error_handlers(app):
    """Register global error handling functions"""
    @app.errorhandler(404)
    def not_found_error(error):
        return jsonify({'error': 'Resource not found'}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500
    
    @app.errorhandler(400)
    def bad_request_error(error):
        return jsonify({'error': 'Bad request'}), 400
    
    @app.errorhandler(429)
    def ratelimit_handler(e):
        return jsonify({'error': 'Rate limit exceeded'}), 429

def load_environment_variables(app):
    """Load environment variables"""
    # Check if dotenv is installed and load
    try:
        from dotenv import load_dotenv
        dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')
        load_dotenv(dotenv_path)
        app.logger.info("Environment variables loaded from .env file")
    except ImportError:
        app.logger.warning("python-dotenv not found, environment variables will be loaded from system environment")
    
    # Transfer environment variables to configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', app.config['SECRET_KEY'])
    app.config['API_KEY'] = os.environ.get('API_KEY', 'bist_profiling_api_key')
    app.config['API_SECRET'] = os.environ.get('API_SECRET', 'bist_profiling_secret_key_change_in_production')
    app.config['ENVIRONMENT'] = os.environ.get('FLASK_ENV', 'development') 